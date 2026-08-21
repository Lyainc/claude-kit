#!/usr/bin/env python3
"""Report top events, outcome distribution, and weekly trend.

Phase 1 W2 deliverable. Skeleton here covers --top counts; the latency/trend
sections expand once we have a week of dogfooding data.

Usage:
    report.py [--since=Nd] [--plugin=NAME|all] [--event=NAME|all]
              [--top=N] [--format=table|json]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = SCRIPT_DIR.parent          # feedback-loop/
REPO_ROOT = PLUGIN_DIR.parent           # repo root (holds */skills/*/SKILL.md)


def resolve_events_dir() -> Path:
    """Events live in a user-writable dir, NOT the plugin install cache.

    Single shared rule (mirrors event-logger.sh + retro):
        ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR}/.claude-kit/telemetry/events}
    CLAUDE_PROJECT_DIR falls back to the git toplevel, then CWD (CLI / test
    invocation). Plain CWD alone reads the wrong dir when invoked from a
    subdirectory — the same slip that scattered write-side dirs across 5 subdirs.
    """
    env = os.environ.get("CLAUDE_KIT_TELEMETRY_DIR")
    if env:
        return Path(env)
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or _git_toplevel() or os.getcwd()
    return Path(proj) / ".claude-kit" / "telemetry" / "events"


def _git_toplevel() -> str | None:
    # Deliberately duplicated in validate-schema.py. feedback-loop scripts are
    # standalone entrypoints (CON-5 leaf-standalone) — no shared module exists to
    # import, and adding one for 10 lines would break that convention.
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


EVENTS_DIR = resolve_events_dir()

# Cost-per-MTok ($) by model, standard (non-intro, non-1h-TTL) API rates.
# cache_write = 1.25x input, cache_read = 0.1x input (5m TTL default) — the
# Anthropic prompt-caching multiplier convention (shared/prompt-caching.md
# "Economics"), not a per-model special case. Actual invoices may differ
# (discounts, plan tiers, intro pricing, 1h TTL) — this is sticker price only.
MODEL_PRICING = {
    "claude-fable-5":            {"input": 10.00, "output": 50.00, "cache_write": 12.50, "cache_read": 1.00},
    "claude-opus-5":             {"input": 5.00,  "output": 25.00, "cache_write": 6.25,  "cache_read": 0.50},
    "claude-sonnet-5":           {"input": 3.00,  "output": 15.00, "cache_write": 3.75,  "cache_read": 0.30},
    # Haiku 4.5's real runtime model ID carries a date suffix, unlike the other
    # three (#510 item 1 / #511) — keyed on the exact string the SessionStart
    # hook payload emits.
    "claude-haiku-4-5-20251001": {"input": 1.00,  "output": 5.00,  "cache_write": 1.25,  "cache_read": 0.10},
}


def _pricing_for(model: str | None) -> dict | None:
    """MODEL_PRICING lookup that tolerates a registered bare key being extended
    with a date suffix (#510 item 1) — e.g. 'claude-sonnet-5-20260601' against
    the registered 'claude-sonnet-5' — or a bracketed context-window variant
    (#650) — e.g. 'claude-opus-5[1m]', same pricing, different window. The
    bracket suffix is stripped before matching so both extension styles funnel
    through one exact/prefix check.
    """
    if not isinstance(model, str) or not model:
        return None
    base = re.sub(r"\[[^\]]*\]$", "", model)
    if base in MODEL_PRICING:
        return MODEL_PRICING[base]
    for key in sorted(MODEL_PRICING, key=len, reverse=True):
        if base.startswith(key + "-"):
            return MODEL_PRICING[key]
    return None

# meta key -> token-kind label used throughout the cost view.
_TOKEN_META_KEYS = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_creation_tokens": "cache_write",
    "cache_read_tokens": "cache_read",
}

# HONESTY BOUNDS — read before interpreting (mirrors rule-fire liveness above):
#  - token-count share and cost share are DIFFERENT rankings on the same data — cache
#    reads are ~94% of tokens but ~49% of cost, cache writes are ~5% of tokens but
#    ~32% of cost (measured, Sonnet 5, #499/#500). Never read one ranking as a stand-in
#    for the other.
#  - cost is priced per-event from that event's meta.model; an event with no model or
#    an unregistered model contributes to the token totals but NEVER to cost — there is
#    no estimated/blended rate. If zero events carry a priced model, the cost column is
#    omitted entirely rather than guessed.
#  - rates are official sticker price (see MODEL_PRICING comment) — not the actual bill.
_COST_CAVEAT = (
    "토큰 수 순위 ≠ 비용 순위(캐시읽기: 토큰 최대·비용 중간, 캐시쓰기: 토큰 최소·비용 상위권). "
    "비용은 event.meta.model이 있고 단가표에 등록된 이벤트에서만 계산 — 없으면 그 이벤트는 "
    "비용 열에서 제외(추정치로 채우지 않음). 단가는 공식 sticker price로 실제 청구액과 다를 수 있음."
)


def token_cost_view(events: list[dict]) -> dict:
    """Aggregate token counts and priced cost per kind (input/output/cache_write/cache_read).

    Token totals sum every event carrying a numeric token field, regardless of model.
    Cost is priced per-event against MODEL_PRICING using that event's meta.model; an
    event with no model or an unregistered model contributes to tokens but is excluded
    from cost — see _COST_CAVEAT. `cost` is None when no event could be priced at all.
    """
    tokens = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    cost = {"input": 0.0, "output": 0.0, "cache_write": 0.0, "cache_read": 0.0}
    priced_events = 0
    excluded_events = 0
    unpriced_models: set[str] = set()

    for e in events:
        meta = e.get("meta")
        if not isinstance(meta, dict):
            continue
        present = {
            kind: meta[key]
            for key, kind in _TOKEN_META_KEYS.items()
            if isinstance(meta.get(key), (int, float)) and not isinstance(meta.get(key), bool)
        }
        if not present:
            continue
        for kind, v in present.items():
            tokens[kind] += v

        model = meta.get("model")
        rates = _pricing_for(model)
        if rates is None:
            excluded_events += 1
            unpriced_models.add(model if isinstance(model, str) and model else "(model 없음)")
            continue
        priced_events += 1
        for kind, v in present.items():
            cost[kind] += v / 1_000_000 * rates[kind]

    return {
        "tokens": tokens,
        "cost": cost if priced_events > 0 else None,
        "priced_events": priced_events,
        "excluded_events": excluded_events,
        "unpriced_models": sorted(unpriced_models),
    }


# Stale threshold for lifecycle view (days since last use).
_STALE_DAYS = 14
# Bottom-N threshold for lifecycle view.
_BOTTOM_N = 5

# Interpretation guide — hardcoded per DoD.
_LIFECYCLE_CAVEAT = (
    "측정범위: claude-kit 레포 내 세션 기준 (telemetry Option A). "
    "집계 단위: 호출 1회(skill_invoke outcome=started) — 이벤트 수가 아님(#696)"
)
# NOTE: vault-bridge is deliberately NOT named here — it ships agents/commands/
# hooks but no skills/, so it can never appear in this skills-catalog view
# (isolated-critique LOW finding, 2026-06-10). OVM is the representative class.
_LIFECYCLE_GUIDE = (
    "해석 가이드: thinking-tools류(in-repo 사용 본질)의 never-fired는 죽은 표면 신호로 "
    "우선 해석하세요. OVM류(타 프로젝트 사용 주류)의 never-fired는 "
    "측정범위 밖 사용 가능성을 먼저 의심하세요."
)


def load_events(since_days: int | None = None):
    if not EVENTS_DIR.is_dir():
        return []
    cutoff = None
    if since_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
    events = []
    for path in sorted(EVENTS_DIR.glob("events-*.jsonl")):
        try:
            d = datetime.strptime(path.stem[len("events-"):], "%Y-%m-%d").date()
        except ValueError:
            continue
        if cutoff and d < cutoff:
            continue
        with path.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    return events


def parse_since(s: str | None) -> int | None:
    if not s or s == "all":
        return None
    if not s.endswith("d"):
        raise SystemExit("--since must be 'Nd' or 'all'")
    return int(s[:-1])


def collect_durations(events: list[dict]) -> list[float]:
    """Pull numeric meta.duration_ms values across events.

    Only events whose meta carries a non-null numeric duration_ms count. Events
    with empty meta, a null duration_ms (no timing datum), or a non-numeric value
    are skipped — so the latency stats reflect real timing samples only. bool is
    explicitly rejected (it is an int subclass in Python).
    """
    durations: list[float] = []
    for e in events:
        meta = e.get("meta")
        if not isinstance(meta, dict):
            continue
        d = meta.get("duration_ms")
        if isinstance(d, bool) or not isinstance(d, (int, float)):
            continue
        durations.append(float(d))
    return durations


def percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile (q in [0,1]) over a pre-sorted list.

    Nearest-rank avoids interpolation ambiguity and matches the "pick the
    sample at rank ceil(q*N)" definition used for small-N dogfooding data.
    """
    if not sorted_vals:
        raise ValueError("percentile of empty list")
    n = len(sorted_vals)
    rank = max(1, math.ceil(q * n))
    return sorted_vals[rank - 1]


def latency_stats(events: list[dict]) -> dict | None:
    """Return {count, p50, p95} over events carrying meta.duration_ms, or None.

    None signals "no timing samples" so callers can render a skip line rather
    than fabricating zeros.
    """
    durations = collect_durations(events)
    if not durations:
        return None
    durations.sort()
    return {
        "count": len(durations),
        "p50": percentile(durations, 0.50),
        "p95": percentile(durations, 0.95),
    }


def latency_by_event(events: list[dict]) -> dict[str, dict[str, float | int]]:
    """Per-event-type latency p50/p95, keyed by the logical `event` field.

    Buckets events by their `event` value (skill_invoke / agent_spawn / stop /
    ...) and runs latency_stats on each bucket. Only event types that carry at
    least one numeric meta.duration_ms sample appear in the result — a type with
    no timing samples is omitted entirely (latency_stats returns None), mirroring
    the overall-latency "no datum → skip" contract rather than fabricating zeros.

    This composes with the caller's --event filter for free: callers filter the
    events list before passing it in, so a one-type filter yields a single-bucket
    breakdown and the unfiltered list yields the full per-type split.
    """
    buckets: dict[str, list[dict]] = {}
    for e in events:
        buckets.setdefault(e.get("event", "?"), []).append(e)
    out: dict[str, dict] = {}
    for ev_type, bucket in buckets.items():
        stats = latency_stats(bucket)
        if stats is not None:
            out[ev_type] = stats
    return out


_VERSION_DIR_RE = re.compile(r"^\d+\.\d+\.\d+$")


def scan_skill_catalog(repo_root: Path | None = None) -> list[str]:
    """Return sorted list of '{plugin}:{skill}' identifiers from SKILL.md files.

    Glob pattern: <repo_root>/*/skills/*/SKILL.md (depth-2 only, no hidden dirs).
    plugin = first path component (e.g. 'thinking-tools').
    skill  = third path component (e.g. 'expert-panel').

    Plugin-cache installs (`cache/{marketplace}/{plugin}/{version}/scripts/...`)
    insert a semver version directory between the plugin name and its content,
    so <repo_root> (PLUGIN_DIR.parent) lands one level too deep for the pattern
    above — it matches `{version}/skills/*/SKILL.md` and the version string gets
    read as the plugin name (#522, e.g. `4.0.1:retro`), which then never matches
    a real `qualified_name` and the lifecycle view reports every skill
    never-fired. Detected by the first path component looking like a version;
    when it does, the scan retries one level up with an extra path segment for
    the version layer, skipping any version dir carrying a `.orphaned_at`
    marker (the cache keeps every version it ever installed, each still
    holding its own SKILL.md files — without this filter a skill retired in
    a later version keeps reappearing as permanently never-fired via its
    stale old-version copy, the same false signal #522 was written to kill,
    just relocated. Verified live: every plugin here has exactly one
    non-orphaned version).
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    catalog: set[str] = set()
    for skill_md in root.glob("*/skills/*/SKILL.md"):
        parts = skill_md.relative_to(root).parts
        # Expected: (plugin, 'skills', skill_name, 'SKILL.md') → 4 parts
        if len(parts) != 4:
            continue
        plugin, _, skill_name, _ = parts
        if _VERSION_DIR_RE.match(plugin):
            return _scan_cache_layout(root.parent)
        # Skip hidden directories
        if plugin.startswith("."):
            continue
        catalog.add(f"{plugin}:{skill_name}")
    return sorted(catalog)


def _scan_cache_layout(cache_root: Path) -> list[str]:
    """plugin/version/skills/skill_name/SKILL.md, one level above the repo-shape root.

    Skips any {plugin}/{version} dir marked `.orphaned_at` — the plugin manager
    keeps every version it ever installed, so an unfiltered scan would keep
    resurrecting skills retired in a newer version via their stale old-version
    SKILL.md.
    """
    catalog: set[str] = set()
    for skill_md in cache_root.glob("*/*/skills/*/SKILL.md"):
        parts = skill_md.relative_to(cache_root).parts
        # Expected: (plugin, version, 'skills', skill_name, 'SKILL.md') → 5 parts
        if len(parts) != 5:
            continue
        plugin, version, _, skill_name, _ = parts
        if plugin.startswith("."):
            continue
        if (cache_root / plugin / version / ".orphaned_at").exists():
            continue
        catalog.add(f"{plugin}:{skill_name}")
    return sorted(catalog)


def claude_kit_owned_names(repo_root: Path | None = None) -> set[str]:
    """Bare skill+agent names owned by a claude-kit plugin in this repo.

    Union of scan_skill_catalog()'s skill names (stripped of the 'plugin:'
    prefix) and every */agents/*.md stem. Used to classify a plugin=unknown
    event as a real attribution failure (name IS ours, map missed it) vs no
    attribution target existing at all (name isn't ours — native command,
    machine-level skill, built-in agent, or a plugin outside claude-kit; #664).
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    names = {qn.split(":", 1)[1] for qn in scan_skill_catalog(root)}
    # Detect the same plugin-cache layout scan_skill_catalog falls back to
    # (#522), so agents get globbed from the matching root.
    agents_root = root
    for skill_md in root.glob("*/skills/*/SKILL.md"):
        plugin = skill_md.relative_to(root).parts[0]
        if _VERSION_DIR_RE.match(plugin):
            agents_root = root.parent
        break
    if agents_root is root:
        for agent_md in root.glob("*/agents/*.md"):
            parts = agent_md.relative_to(root).parts
            if len(parts) == 3 and not parts[0].startswith("."):
                names.add(agent_md.stem)
    else:
        for agent_md in agents_root.glob("*/*/agents/*.md"):
            parts = agent_md.relative_to(agents_root).parts
            if len(parts) == 4 and not parts[0].startswith("."):
                names.add(agent_md.stem)
    return names


def classify_unknown(events: list[dict], repo_root: Path | None = None) -> dict:
    """Split plugin=unknown events into attribution_failure vs no_target (#664).

    attribution_failure: bare name IS a claude-kit-owned skill/agent (plugin-map.json
    missed it — a real drift bug, see test-plugin-map-drift.py).
    no_target: bare name isn't ours at all (native command, machine-level skill,
    built-in agent, or a plugin outside claude-kit) — "unknown" is correct here.
    """
    owned = claude_kit_owned_names(repo_root)
    unknown_events = [e for e in events if e.get("plugin") == "unknown"]
    attribution_failure = sum(1 for e in unknown_events if e.get("name") in owned)
    no_target = len(unknown_events) - attribution_failure
    return {
        "total_unknown": len(unknown_events),
        "attribution_failure": attribution_failure,
        "no_target": no_target,
    }


def skill_lifecycle_view(
    events: list[dict],
    catalog: list[str] | None = None,
    stale_days: int = _STALE_DAYS,
    bottom_n: int = _BOTTOM_N,
    since_days: int | None = None,
) -> dict:
    """Derive per-skill lifecycle signals from events vs. catalog.

    Returns a dict with keys:
      catalog        - full catalog list
      never_fired    - skills with 0 events in the window
      stale          - skills whose last event is > stale_days ago (excluding never-fired)
      stale_note     - non-None when the --since window is too short to ever
                       contain a stale event (the section would be inert)
      bottom         - bottom_n skills by count (excluding never-fired), sorted ascending
      caveat         - measurement-scope caveat string
      guide          - interpretation guide string

    Matching: event['qualified_name'] == '{plugin}:{skill}' (catalog format).
    Counts CALLS, not events: only skill_invoke events with outcome == 'started'
    count (#696). The harness emits exactly one started per invocation regardless
    of the skill; counting every skill_invoke event instead conflated call count
    with event count, since some skills (retro) log an extra non-started
    skill_invoke line (Phase-3 emit, retro-telemetry.sh) that inflated their
    count relative to skills without one. A non-empty qualified_name is required.
    Staleness (last_seen) still tracks any skill_invoke event regardless of
    outcome, so a call whose started/completion lines land in different
    --since day-file windows stays visible as recently-used even on a window
    where it can't register a full count.
    """
    if catalog is None:
        catalog = scan_skill_catalog()

    catalog_set = set(catalog)
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_days)

    # Collect last-seen timestamp and counts per qualified_name from skill_invoke events.
    # last_seen tracks ANY skill_invoke event (not just started): a call whose
    # 'started' line falls outside this --since window's day-file cutoff while
    # its 'success'/'error' line doesn't (a call straddling the UTC day
    # boundary — real for a long-running skill like retro) must still register
    # as recently used for staleness purposes, even though it can't count as a
    # complete call without its started line (#696 fresh-review finding).
    last_seen: dict[str, datetime] = {}
    counts: Counter[str] = Counter()
    for e in events:
        if e.get("event") != "skill_invoke":
            continue
        qn = e.get("qualified_name", "")
        if not qn or qn not in catalog_set:
            continue
        if e.get("outcome") == "started":
            counts[qn] += 1
        ts_raw = e.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if qn not in last_seen or ts > last_seen[qn]:
            last_seen[qn] = ts

    # 1. never-fired: in catalog but count == 0
    never_fired = sorted(s for s in catalog if counts[s] == 0)

    # 2. stale: has events but last seen > stale_days ago
    stale = sorted(
        s for s in catalog
        if counts[s] > 0 and s in last_seen and last_seen[s] < stale_cutoff
    )

    # A bounded --since window <= the stale threshold filters out every event old
    # enough to be stale BEFORE this view runs, so the section would render "(none)"
    # unconditionally. Surface that instead of silently hiding the one signal the
    # stale view exists for (isolated-critique MEDIUM finding, 2026-06-10).
    stale_note = None
    if since_days is not None and since_days <= stale_days:
        stale_note = (
            f"--since={since_days}d window cannot contain >{stale_days}d-old events; "
            "use --since=all or a window above the stale threshold"
        )

    # 3. bottom-N: skills with events, sorted by count ascending, top bottom_n
    fired = [(s, counts[s]) for s in catalog if counts[s] > 0]
    fired.sort(key=lambda x: (x[1], x[0]))
    bottom = fired[:bottom_n]

    return {
        "catalog": catalog,
        "never_fired": never_fired,
        "stale": stale,
        "stale_note": stale_note,
        "bottom": bottom,
        "caveat": _LIFECYCLE_CAVEAT,
        "guide": _LIFECYCLE_GUIDE,
    }


# Rule-fire liveness (G20 #258). HONESTY BOUNDS — read before interpreting:
#  - a fire = a guard CAUGHT a violation; it is NOT a compliance/adherence count.
#  - a perfectly-obeyed rule fires ZERO times, indistinguishable from a dead rule, so
#    0-fire is AMBIGUOUS (dead vs perfectly-internalized) — never read as "unfollowed".
#  - 0-fire rules are INVISIBLE here: telemetry only sees rules that fired >= 1 (there is
#    no landed-rule registry to diff against, unlike skills which have a SKILL.md catalog).
#    This view therefore never surfaces "inert" rules; it is an enforcement-LIVENESS tally
#    for rules that fired, nothing more. (consensus gate G1/G2, 2026-06-23.)
_RULE_FIRE_CAVEAT = (
    "rule_fire = enforcement liveness(위반이 잡힌 횟수)지 준수도 아님. "
    "0-fire는 telemetry에 안 보이고(레지스트리 미구현) 해석 불가(죽음/완벽내재화) — "
    "제거·재고려 신호로 쓰지 마세요. 측정범위: claude-kit 레포 내 세션 (Option A)."
)


# Liveness-type events (#491, extends G20 #258): these emit an enforcement/
# instrumentation heartbeat, not a real skill/agent/command invocation. Mixed into
# the general outcome distribution or Top N, a single noisy rule swamps real usage
# signal — rule_fire measured 52% of all events over a real 7d window (#491). Only
# rule_fire qualifies as of this writing: it is the sole VALID_EVENTS member whose
# outcome is a fire/catch signal rather than a start/success/error/blocked lifecycle
# state. Re-check VALID_EVENTS (validate-schema.py) before assuming this stays a
# one-element set.
LIVENESS_EVENTS = {"rule_fire"}


def rule_fire_view(events: list[dict]) -> dict[str, int]:
    """Per-rule_id fire counts from rule_fire events (enforcement liveness).

    Keyed by the rule identity the logger lifts into name/qualified_name
    (event-logger.sh rule_fire case: meta.rule_id -> name, so report's
    (plugin,event,name) `top` and this view both differentiate per rule rather
    than collapsing into one undifferentiated rule_fire bucket). Only rule_fire
    events count. See _RULE_FIRE_CAVEAT for the honesty bounds: this is a liveness
    tally, NOT a compliance measure, and 0-fire rules are structurally unobservable.
    """
    # One occurrence == one fire: this tally counts EVENTS, not meta.count (a
    # reserved/forward-provisioned key the liveness view does not consume). A fire
    # with no rule_id lands in "(unnamed rule)" — an honest catch-all (the reference
    # emitter always sets rule_id; anonymous fires under-specify, never over-claim).
    counts: Counter[str] = Counter()
    for e in events:
        if e.get("event") != "rule_fire":
            continue
        rid = e.get("name") or e.get("qualified_name") or "(unnamed rule)"
        counts[rid] += 1
    return dict(counts)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", default="7d", help="time window (e.g. '7d', 'all')")
    p.add_argument("--plugin", default="all")
    p.add_argument("--event", default="all")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--format", choices=("table", "json"), default="table")
    p.add_argument(
        "--top-include-liveness", action="store_true",
        help="include liveness events (rule_fire) in the Top N ranking "
             "(excluded by default, #491 — they drown out real usage signal)",
    )
    args = p.parse_args()

    since_days = parse_since(args.since)
    events = load_events(since_days)

    if args.plugin != "all":
        events = [e for e in events if e.get("plugin") == args.plugin]
    if args.event != "all":
        events = [e for e in events if e.get("event") == args.event]

    if not events:
        print(f"No events matched (since={args.since}, plugin={args.plugin}, event={args.event})")
        return 0

    # #491: liveness events (rule_fire) are enforcement heartbeats, not usage —
    # split them out before computing the outcome mix and Top N so a noisy rule
    # can't drown out real skill/agent/command signal. --top-include-liveness
    # restores the old undifferentiated behavior for Top N only; the outcome mix
    # always excludes them (they get their own liveness line below/in JSON).
    non_liveness = [e for e in events if e.get("event") not in LIVENESS_EVENTS]
    liveness_events = [e for e in events if e.get("event") in LIVENESS_EVENTS]
    top_source = events if args.top_include_liveness else non_liveness

    counts = Counter(
        (e.get("plugin", "?"), e.get("event", "?"), e.get("name", ""))
        for e in top_source
    )
    outcomes = Counter(e.get("outcome", "?") for e in non_liveness)
    liveness_by_event = Counter(e.get("event", "?") for e in liveness_events)
    plugin_unknown = sum(1 for e in events if e.get("plugin") == "unknown")
    unknown_ratio = plugin_unknown / len(events)
    unknown_split = classify_unknown(events)
    attribution_failure_ratio = unknown_split["attribution_failure"] / len(events)
    no_target_ratio = unknown_split["no_target"] / len(events)

    latency = latency_stats(events)
    latency_per_event = latency_by_event(events)

    lifecycle = skill_lifecycle_view(events, since_days=since_days)
    rule_fire_counts = rule_fire_view(events)
    token_cost = token_cost_view(events)

    if args.format == "json":
        payload = {
            "total": len(events),
            "since": args.since,
            "outcomes": dict(outcomes),
            # #491: liveness events (rule_fire) never appear in `outcomes` above —
            # they get their own line here so a reader can't misread "fired" as a
            # normal outcome share. Always an object; by_event is empty when
            # nothing fired this window (never omitted/null).
            "liveness": {
                "total": len(liveness_events),
                "by_event": dict(liveness_by_event),
            },
            "top_includes_liveness": args.top_include_liveness,
            "plugin_unknown_ratio": round(unknown_ratio, 4),
            "plugin_unknown": {
                "ratio": round(unknown_ratio, 4),
                "attribution_failure": unknown_split["attribution_failure"],
                "attribution_failure_ratio": round(attribution_failure_ratio, 4),
                "no_target": unknown_split["no_target"],
                "no_target_ratio": round(no_target_ratio, 4),
            },
            "latency": (
                {
                    "count": latency["count"],
                    "p50_ms": round(latency["p50"], 1),
                    "p95_ms": round(latency["p95"], 1),
                }
                if latency is not None
                else None
            ),
            "latency_by_event": {
                ev_type: {
                    "count": s["count"],
                    "p50_ms": round(s["p50"], 1),
                    "p95_ms": round(s["p95"], 1),
                }
                for ev_type, s in sorted(latency_per_event.items())
            },
            "top": [
                {"plugin": plg, "event": ev, "name": nm, "count": c}
                for (plg, ev, nm), c in counts.most_common(args.top)
            ],
            "lifecycle": {
                "caveat": lifecycle["caveat"],
                "never_fired": lifecycle["never_fired"],
                # #210 N1: never_fired is window-bounded; the label disambiguates
                # "absolutely never" (--since=all) from "no events in this window".
                "never_fired_label": (
                    "never-fired" if since_days is None
                    else f"no events in {args.since} window"
                ),
                "stale": lifecycle["stale"],
                "stale_note": lifecycle["stale_note"],
                "bottom": [
                    {"skill": s, "count": c} for s, c in lifecycle["bottom"]
                ],
                "guide": lifecycle["guide"],
            },
            # Rule-fire liveness: per-rule_id fire counts (enforcement, NOT compliance).
            # 0-fire rules are absent by construction (see _RULE_FIRE_CAVEAT); the caveat
            # ships alongside so a consumer never reads a fire count as an adherence rate.
            "rule_fire": rule_fire_counts,
            "rule_fire_caveat": _RULE_FIRE_CAVEAT if rule_fire_counts else None,
            # Token/cost view: token counts always present when any token data exists;
            # cost is null (with a reason) when no event could be priced. See
            # _COST_CAVEAT for why token-count share and cost share diverge.
            "token_cost": {
                "tokens": token_cost["tokens"],
                "cost": (
                    {k: round(v, 4) for k, v in token_cost["cost"].items()}
                    if token_cost["cost"] is not None else None
                ),
                "cost_omitted_reason": (
                    None if token_cost["cost"] is not None
                    else "priced 이벤트 0건 (model 없음 또는 미등록: "
                         f"{', '.join(token_cost['unpriced_models']) or '해당 없음'})"
                ),
                "excluded_events": token_cost["excluded_events"],
                "unpriced_models": token_cost["unpriced_models"],
            } if sum(token_cost["tokens"].values()) else None,
            "token_cost_caveat": _COST_CAVEAT if sum(token_cost["tokens"].values()) else None,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Total events: {len(events)} (since={args.since})")
    print(f"Outcomes: {dict(outcomes)}")
    # #491: liveness (rule_fire) is deliberately excluded from Outcomes above —
    # printed as its own line so it stays visible without dominating the mix.
    if liveness_events:
        print(f"Liveness (enforcement heartbeat, excluded from Outcomes above): "
              f"{len(liveness_events)} {dict(liveness_by_event)}")
    print(f"plugin=unknown ratio: {unknown_ratio:.1%} "
          f"(attribution failure: {attribution_failure_ratio:.1%}, "
          f"no attribution target: {no_target_ratio:.1%})")
    print()
    print("Latency p50/p95 (events with duration_ms only):")
    if latency is None:
        print("  (no events carry meta.duration_ms — nothing to report)")
    else:
        print(
            f"  n={latency['count']}  "
            f"p50={latency['p50']:.0f}ms  p95={latency['p95']:.0f}ms"
        )
        print("  by event type:")
        max_width = max((len(k) for k in latency_per_event), default=14)
        for ev_type, s in sorted(latency_per_event.items()):
            print(
                f"    {ev_type:<{max_width}} "
                f"n={s['count']:<4} "
                f"p50={s['p50']:.0f}ms  p95={s['p95']:.0f}ms"
            )
    print()
    if args.top_include_liveness:
        print(f"Top {args.top} (liveness events included, --top-include-liveness):")
    else:
        print(f"Top {args.top} (liveness events excluded — see --top-include-liveness):")
    for (plg, ev, nm), c in counts.most_common(args.top):
        label = f"{plg}:{ev}" + (f" ({nm})" if nm else "")
        print(f"  {c:>5}  {label}")
    print()
    print(f"Skill lifecycle ({lifecycle['caveat']}):")
    # #210 N1: "never-fired" is window-bounded — a skill that fired 10d ago still shows
    # under --since=7d. Say so in the label so it is not read as "never, ever fired":
    # only --since=all earns the absolute "never-fired"; a window says "no events in <w>".
    nf_label = "never-fired" if since_days is None else f"no events in {args.since} window"
    if lifecycle["never_fired"]:
        print(f"  {nf_label} ({len(lifecycle['never_fired'])}):")
        for s in lifecycle["never_fired"]:
            print(f"    {s}")
    else:
        print(f"  {nf_label}: (none)")
    if lifecycle["stale"]:
        print(f"  last-used > {_STALE_DAYS}d ({len(lifecycle['stale'])}):")
        for s in lifecycle["stale"]:
            print(f"    {s}")
    else:
        print(f"  last-used > {_STALE_DAYS}d: (none)")
    if lifecycle["stale_note"]:
        print(f"    ({lifecycle['stale_note']})")
    if lifecycle["bottom"]:
        print(f"  bottom-{_BOTTOM_N} (by count):")
        for s, c in lifecycle["bottom"]:
            print(f"    {c:>5}  {s}")
    else:
        print(f"  bottom-{_BOTTOM_N}: (none)")
    print(f"  {lifecycle['guide']}")
    # Rule-fire liveness — only render when something actually fired. The caveat is
    # printed INLINE with the counts (consensus gate G6) so a reader never sees a fire
    # tally without the "liveness != compliance, 0-fire is invisible/ambiguous" warning.
    if rule_fire_counts:
        print()
        print("Rule-fire liveness (enforcement, NOT compliance):")
        for rid, c in sorted(rule_fire_counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {c:>5}  {rid}")
        print(f"  ! {_RULE_FIRE_CAVEAT}")
    # Token/cost view — only render when some event carries token data. Token counts
    # and cost render SIDE BY SIDE (never one without the other) so the reader sees
    # both rankings on the same rows — showing only tokens is exactly the misreading
    # this view exists to prevent. The caveat prints inline, same pattern as rule-fire.
    total_tokens = sum(token_cost["tokens"].values())
    if total_tokens:
        print()
        print("Token/cost breakdown (종류별 토큰 수 vs 비용):")
        total_cost = sum(token_cost["cost"].values()) if token_cost["cost"] is not None else None
        for kind in ("input", "output", "cache_write", "cache_read"):
            tok = token_cost["tokens"][kind]
            tok_pct = (tok / total_tokens * 100) if total_tokens else 0.0
            if total_cost is not None:
                cost_val = token_cost["cost"][kind]
                cost_pct = (cost_val / total_cost * 100) if total_cost else 0.0
                cost_str = f"${cost_val:.4f} ({cost_pct:5.1f}%)"
            else:
                cost_str = "(생략)"
            print(f"  {kind:<12} tokens={tok:>10} ({tok_pct:5.1f}%)  cost={cost_str}")
        if token_cost["excluded_events"] and token_cost["cost"] is not None:
            print(
                f"  {'excluded':<12} events={token_cost['excluded_events']:>10}  "
                f"model 없음/미등록: {', '.join(token_cost['unpriced_models'])}"
            )
        if token_cost["cost"] is None:
            print(
                f"  ! 비용 열 생략: priced 이벤트 0건 (model 없음 또는 미등록: "
                f"{', '.join(token_cost['unpriced_models']) or '해당 없음'})"
            )
        print(f"  ! {_COST_CAVEAT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
