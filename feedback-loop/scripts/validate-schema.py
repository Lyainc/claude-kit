#!/usr/bin/env python3
"""Validate telemetry jsonl schema.

Phase 1 deliverable: detect required-field omissions, type errors, and
line-size approach to PIPE_BUF (which would force a lock strategy revisit).

Usage:
    validate-schema.py [--since=Nd] [--strict] [--self-test]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = SCRIPT_DIR.parent          # feedback-loop/


def resolve_events_dir() -> Path:
    """User-writable events dir (mirrors event-logger.sh + report.py):
        ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR}/.claude-kit/telemetry/events}
    """
    env = os.environ.get("CLAUDE_KIT_TELEMETRY_DIR")
    if env:
        return Path(env)
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or _git_toplevel() or os.getcwd()
    return Path(proj) / ".claude-kit" / "telemetry" / "events"


def _git_toplevel() -> str | None:
    # Deliberately duplicated in report.py. feedback-loop scripts are standalone
    # entrypoints (CON-5 leaf-standalone) — no shared module exists to import, and
    # adding one for 10 lines would break that convention.
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


EVENTS_DIR = resolve_events_dir()

REQUIRED_FIELDS = {
    "ts": str,
    "session_id": str,
    "cwd": str,
    "plugin": str,
    "event": str,
    "name": str,
    "qualified_name": str,
    "trigger": str,
    "outcome": str,
    "tool_use_id": str,
    "meta": dict,
}

VALID_EVENTS = {
    "skill_invoke", "agent_spawn", "command_run",
    "session_start", "session_end", "stop",
    # rule_fire — #216 c8 / #217: a work-rules guard firing (check-*.py violation
    # or task-end checklist reminder). feedback-loop OWNS this schema; work-rules
    # guards (scripts/*.sh) only EMIT to it (a data contract, never a code import — CON-5 safe).
    # meta is free-form per the envelope rule; conventional keys: rule_id (str),
    # severity ('hard'|'soft'), file (str), count (int). All optional.
    "rule_fire",
}

# Under --strict, a PostToolUse end event (skill_invoke/agent_spawn with a
# terminal outcome) is expected to carry at least a duration_ms datum in meta;
# an empty meta is surfaced as a (non-fatal) warning so a token/timing pipeline
# regression is visible. Only `success`/`error`/`blocked` outcomes are end
# events — `started` is the PreToolUse half and legitimately has empty meta.
META_EXPECTED_EVENTS = {"skill_invoke", "agent_spawn"}
END_OUTCOMES = {"success", "error", "blocked"}

# PIPE_BUF safety threshold. POSIX guarantees atomic O_APPEND for writes <=
# PIPE_BUF (4096 on macOS/Linux). We warn at 3500B to leave headroom; if we
# ever exceed, the lockless append strategy needs to be revisited.
PIPE_BUF_WARN_BYTES = 3500


def find_event_files(since_days: int | None) -> list[Path]:
    if not EVENTS_DIR.is_dir():
        return []
    files = sorted(EVENTS_DIR.glob("events-*.jsonl"))
    if since_days is None:
        return files
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
    return [p for p in files if _date_from_filename(p) >= cutoff]


def _date_from_filename(p: Path):
    stem = p.stem  # events-YYYY-MM-DD
    try:
        return datetime.strptime(stem[len("events-"):], "%Y-%m-%d").date()
    except ValueError:
        print(f"warning: skipping malformed event filename {p.name}", file=sys.stderr)
        return datetime.min.date()


def validate_line(raw: str, lineno: int, path: Path,
                  strict: bool = False) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one jsonl line.

    errors are hard schema violations (drive --strict exit code); warnings are
    advisory findings (empty-meta on end events) surfaced under --strict but
    never fatal — historical pre-token-instrumentation lines must not break the
    Phase Gate.
    """
    errors: list[str] = []
    warnings: list[str] = []
    line_bytes = len(raw.encode("utf-8"))
    if line_bytes > PIPE_BUF_WARN_BYTES:
        errors.append(
            f"{path.name}:{lineno} line size {line_bytes}B approaches PIPE_BUF "
            f"({PIPE_BUF_WARN_BYTES}B warn threshold) — revisit lock strategy"
        )

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}:{lineno} JSON parse error: {e.msg}")
        return errors, warnings

    if not isinstance(obj, dict):
        errors.append(f"{path.name}:{lineno} not a JSON object")
        return errors, warnings

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in obj:
            errors.append(f"{path.name}:{lineno} missing required field '{field}'")
            continue
        if not isinstance(obj[field], expected_type):
            errors.append(
                f"{path.name}:{lineno} field '{field}' has wrong type "
                f"(expected {expected_type.__name__}, got {type(obj[field]).__name__})"
            )

    if "event" in obj and obj["event"] not in VALID_EVENTS:
        errors.append(
            f"{path.name}:{lineno} event '{obj['event']}' not in {sorted(VALID_EVENTS)}"
        )

    if (strict
            and obj.get("event") in META_EXPECTED_EVENTS
            and obj.get("outcome") in END_OUTCOMES
            and isinstance(obj.get("meta"), dict)
            and not obj["meta"]):
        warnings.append(
            f"{path.name}:{lineno} empty meta on {obj['event']} "
            f"end event (expected duration_ms/token data)"
        )

    return errors, warnings


def run_self_test() -> int:
    # Synthesize valid + invalid lines and run validator inline.
    good = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "claude-kit",
        "event": "stop", "name": "", "qualified_name": "",
        "trigger": "auto", "outcome": "success",
        "tool_use_id": "", "meta": {},
    })
    # A populated meta (duration_ms + token counts) must validate cleanly:
    # inner meta keys are optional, only the `meta: dict` envelope is required.
    good_meta = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "vault-bridge",
        "event": "skill_invoke", "name": "vault-commit",
        "qualified_name": "vault-bridge:vault-commit",
        "trigger": "explicit", "outcome": "success",
        "tool_use_id": "toolu_01ABC",
        "meta": {
            "duration_ms": 1234,
            "input_tokens": 500,
            "output_tokens": 120,
            "cache_read_tokens": 42,
            "cache_creation_tokens": 17,
            "model": "claude-sonnet-5",
        },
    })
    # duration_ms may be null when timing is unavailable — still valid.
    good_meta_null = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "thinking-tools",
        "event": "agent_spawn", "name": "executor",
        "qualified_name": "executor",
        "trigger": "explicit", "outcome": "success",
        "tool_use_id": "toolu_02DEF",
        "meta": {"duration_ms": None},
    })
    # An end event with empty meta is clean by default but warns under --strict.
    empty_meta_end = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "vault-bridge",
        "event": "skill_invoke", "name": "vault-commit",
        "qualified_name": "vault-bridge:vault-commit",
        "trigger": "explicit", "outcome": "success",
        "tool_use_id": "toolu_03GHI", "meta": {},
    })
    # A stop event with a non-empty meta must validate cleanly AND must NOT trip
    # the empty-meta warning even under --strict — stop is outside
    # META_EXPECTED_EVENTS, so the empty-meta invariant simply never applies to
    # it. This case locks that. The schema itself places no constraint on which
    # keys a stop event's meta may carry (arbitrary keys shown here are
    # illustrative only) — in practice extract_stop_meta (event-logger.sh)
    # always emits {}, confirmed #168: real Stop payloads carry no usage/token
    # field at any key path.
    stop_populated_meta = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "claude-kit",
        "event": "stop", "name": "", "qualified_name": "",
        "trigger": "auto", "outcome": "success",
        "tool_use_id": "",
        "meta": {"example_key_a": 1500, "example_key_b": 300},
    })
    # A rule_fire event (G20 #258) must validate cleanly, including its outcome="fired"
    # (outcome is unconstrained for non-end events) and its conventional meta keys. This
    # locks the contract in self-test isolation so a future change that accidentally
    # constrained outcome to END_OUTCOMES for all events would be caught here, not just
    # by the integration round-trip.
    good_rule_fire = json.dumps({
        "ts": "2026-05-15T00:00:00Z",
        "session_id": "x", "cwd": "/", "plugin": "claude-kit",
        "event": "rule_fire", "name": "no-pyyaml", "qualified_name": "no-pyyaml",
        "trigger": "auto", "outcome": "fired",
        "tool_use_id": "",
        "meta": {"rule_id": "no-pyyaml", "severity": "hard", "file": "foo.py"},
    })
    bad = '{"ts":"x","event":"not-an-event"}'

    sp = Path("self-test.jsonl")
    good_errs, _ = validate_line(good, 1, sp)
    good_meta_errs, _ = validate_line(good_meta, 1, sp)
    good_rule_fire_errs, good_rule_fire_warns = validate_line(good_rule_fire, 1, sp, strict=True)
    good_meta_null_errs, _ = validate_line(good_meta_null, 1, sp)
    empty_lax_errs, empty_lax_warns = validate_line(empty_meta_end, 1, sp, strict=False)
    _, empty_strict_warns = validate_line(empty_meta_end, 1, sp, strict=True)
    stop_meta_errs, stop_meta_warns_lax = validate_line(
        stop_populated_meta, 1, sp, strict=False)
    _, stop_meta_warns_strict = validate_line(
        stop_populated_meta, 1, sp, strict=True)
    bad_errs, _ = validate_line(bad, 1, sp)

    if good_errs:
        print(f"FAIL: good line flagged: {good_errs}", file=sys.stderr)
        return 1
    if good_meta_errs:
        print(f"FAIL: good meta line flagged: {good_meta_errs}", file=sys.stderr)
        return 1
    if good_rule_fire_errs:
        print(f"FAIL: good rule_fire line flagged: {good_rule_fire_errs}", file=sys.stderr)
        return 1
    if good_rule_fire_warns:
        print(f"FAIL: rule_fire wrongly warned under --strict (not an end event): "
              f"{good_rule_fire_warns}", file=sys.stderr)
        return 1
    if good_meta_null_errs:
        print(f"FAIL: good null-duration meta line flagged: {good_meta_null_errs}",
              file=sys.stderr)
        return 1
    if empty_lax_errs or empty_lax_warns:
        print(f"FAIL: empty-meta end event flagged without --strict: "
              f"errs={empty_lax_errs} warns={empty_lax_warns}", file=sys.stderr)
        return 1
    if not empty_strict_warns:
        print("FAIL: empty-meta end event not warned under --strict", file=sys.stderr)
        return 1
    if stop_meta_errs:
        print(f"FAIL: stop populated-meta line flagged with errors: {stop_meta_errs}",
              file=sys.stderr)
        return 1
    if stop_meta_warns_lax:
        print(f"FAIL: stop populated-meta warned without --strict: {stop_meta_warns_lax}",
              file=sys.stderr)
        return 1
    if stop_meta_warns_strict:
        print("FAIL: stop event with non-empty meta wrongly triggered the empty-meta "
              f"warning under --strict: {stop_meta_warns_strict}", file=sys.stderr)
        return 1
    if not bad_errs:
        print("FAIL: bad line not flagged", file=sys.stderr)
        return 1
    print(f"OK: self-test passed ({len(bad_errs)} expected errors on bad line)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", help="time window: '7d', '30d', etc.", default=None)
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero on any violation")
    p.add_argument("--self-test", action="store_true",
                   help="run inline schema validator on synthetic input and exit")
    args = p.parse_args()

    if args.self_test:
        return run_self_test()

    since_days: int | None = None
    if args.since:
        if not args.since.endswith("d"):
            print("--since must be in form 'Nd' (days)", file=sys.stderr)
            return 2
        try:
            since_days = int(args.since[:-1])
        except ValueError:
            print(f"invalid --since: {args.since}", file=sys.stderr)
            return 2

    files = find_event_files(since_days)
    if not files:
        print(f"No event files in {EVENTS_DIR} (since_days={since_days})")
        return 0

    total_lines = 0
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for path in files:
        with path.open(encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                raw = raw.rstrip("\n")
                if not raw.strip():
                    continue
                total_lines += 1
                errs, warns = validate_line(raw, lineno, path, strict=args.strict)
                all_errors.extend(errs)
                all_warnings.extend(warns)

    print(f"Scanned {total_lines} lines across {len(files)} files")
    # Warnings (e.g. empty meta on end events) are advisory only — printed under
    # --strict but never affect the exit code, so historical pre-instrumentation
    # data does not break the Phase Gate.
    if all_warnings:
        print(f"Warnings: {len(all_warnings)}")
        for warn in all_warnings[:50]:
            print(f"  {warn}")
        if len(all_warnings) > 50:
            print(f"  ... and {len(all_warnings) - 50} more")
    if all_errors:
        print(f"Violations: {len(all_errors)}")
        for err in all_errors[:50]:
            print(f"  {err}")
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more")
        return 1 if args.strict else 0
    print("All schema checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
