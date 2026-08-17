#!/usr/bin/env python3
"""manifest-domain-candidates.py + manifest-keyword-candidates.py regression (#523, mirrors
#468's obsidian-vault-manager/scripts/test/test-manifest-reads.py).

vault-searcher.md used to `Read` .vault-bridge/manifest.json in full. The Read tool truncates
at a 2,000-line default cap; a real vault (180 entries / 3,338 pretty-printed lines) overflowed
it, and because generate-manifest.py sorts entries by `rel_path`, `wiki/` (alphabetically last)
landed 100% inside the truncated tail — every wiki/ entry silently vanished from the recall
candidate set, the opposite of the "wiki/ always included" contract (vault-searcher.md L94).

Three things must hold:
1. REPRODUCE: at real scale, a raw pretty-printed manifest read would in fact overflow a
   2,000-line cap and put 100% of wiki/ entries past it (pins the precondition, not just the fix).
2. FIX: both scripts read the manifest directly off disk (bypassing Read/Bash truncation) and
   return every wiki/ entry — no silent loss, at the scale the issue measured (39 wiki / 180
   total) and beyond.
3. OBSERVABLE: if a caller's downstream tool output ever truncates the script's own JSON
   response, that must surface as a detectable mismatch (parse failure or
   `len(candidates) != candidate_count`), never as a silently-smaller candidate list.
4. PINNED (#663): the truncation-check invariant and the candidate ranking order, whose
   canonical text moved to `reference/manifest-recall.md`, and the #305 wiki-staleness hedge,
   which moved to `reference/wiki-staleness.md`, still read THERE verbatim — pinned by
   WHOLE-SECTION equality (heading to next heading, whitespace-normalised) plus the identity
   of each pinned section's two neighbouring headings, so contradicting text can neither be
   parked at the bottom of a section nor inside a freshly inserted sibling. The always-loaded
   `agents/vault-searcher.md` locator sections are pinned the same way, by section name and
   read-and-apply wording rather than by the bare reference path.

Run: python3 vault-bridge/scripts/test/test-manifest-candidates.py
  -> "OK: all N manifest-candidate checks passed" (exit 0) / "FAILED: ..." (exit 1).
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DOMAIN_SCRIPT = _HERE.parent / "manifest-domain-candidates.py"
_KEYWORD_SCRIPT = _HERE.parent / "manifest-keyword-candidates.py"
_AGENT = _HERE.parent.parent / "agents" / "vault-searcher.md"
_REF = _HERE.parent.parent / "reference" / "manifest-recall.md"
_STALENESS = _HERE.parent.parent / "reference" / "wiki-staleness.md"

errors = []


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# Canonical contract text (#663). vault-searcher.md sat at ~4,990 of the #447 5,000-token
# budget, so the contract prose moved to reference/manifest-recall.md (truncation-check
# invariant, candidate ranking order) and reference/wiki-staleness.md (the #305 hedge), and
# the agent body keeps read-and-apply locators. The pins FOLLOW the prose: they read the
# reference docs, which are now canonical, plus the locators that make them binding.
#
# WHY WHOLE-SECTION EQUALITY, not a set of clause pins. Every partial anchor is a blocklist of
# the last wording someone tried, and it leaves the whole unpinned remainder of the section
# free — the ranking section's `status=active` ordering, the "never read a 0 as cold" caveat,
# and the script-unavailable fallback arm were all deletable with the old substring suite
# green. So the section's OWN TEXT is the pin and the comparison is TOTAL (same shape as
# `_EXCHANGE_LOOP_SECTION` in thinking-tools/scripts/test/test-mode-compose.py). Whitespace is
# normalised: a reflow is not a change, an edit to the words is — and updating these constants
# is the deliberate act that records a contract change, in the same commit as the edit.
#
# Each slice runs from its heading to the NEXT heading of equal-or-shallower depth, so a
# contradicting clause parked at the bottom of a section is inside the pin, not outside it.
#
# The agent body is pinned the same way: at runtime the always-loaded vault-searcher.md
# outranks an on-demand reference doc, so a locator that says "override" where the canonical
# section says "tiebreaker only" wins in practice against a perfectly pinned reference.
#
# The clause pins that survive are kept for DIAGNOSIS, not coverage — each names a distinct
# invariant, so the failure message says which one died instead of only "the section changed".
# ---------------------------------------------------------------------------


def _section_re(heading: str, depth: int) -> "re.Pattern[str]":
    """Heading line -> the whole section, stopping at the next heading of depth <= `depth`."""
    return re.compile(
        rf"^{re.escape(heading)}$.*?(?=^#{{1,{depth}}} |\Z)",
        re.MULTILINE | re.DOTALL,
    )


def _section(pattern: "re.Pattern[str]", text: str) -> str:
    """The whole named section, heading to next heading, whitespace-normalised ("" if absent)."""
    match = pattern.search(text)
    return _normalise(match.group(0)) if match else ""


def _neighbour_headings(pattern: "re.Pattern[str]", text: str) -> tuple:
    """The heading immediately before and immediately after the pinned section."""
    match = pattern.search(text)
    if not match:
        return ("", "")
    before = [ln for ln in text[:match.start()].splitlines() if ln.startswith("#")]
    after = [ln for ln in text[match.end():].splitlines() if ln.startswith("#")]
    return (before[-1] if before else "", after[0] if after else "")


_REF_TRUNCATION_RE = _section_re("## The truncation-check invariant", 2)
_REF_RANKING_RE = _section_re("## Candidate ranking order (Mode 2 step 2c)", 2)
_STALE_CONTRACT_RE = _section_re("## The contract", 2)
_STALE_MTIME_RE = _section_re("## Why `verified:` and not mtime", 2)
_STALE_LEGACY_RE = _section_re("## Legacy pages with no `verified:`", 2)
_AGENT_MANIFEST_FIRST_RE = _section_re("#### Manifest-First Protocol", 4)
_AGENT_RULES_RE = _section_re("## Rules", 2)


_REF_TRUNCATION_SECTION = _normalise("""\
## The truncation-check invariant

**Canonical text.** `vault-searcher.md` (Mode 2 step 2b, Mode 3 step 1) points here; this
section is the binding contract, and the agent must apply it as written. Its whole text —
heading to the next heading, so nothing unpinned may be parked at the bottom — is pinned
VERBATIM by `_REF_TRUNCATION_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`. Editing anything below is a deliberate
contract change and updates that constant in the same commit; a reflow is free (the comparison
is whitespace-normalised).

Even with the prefilter running out-of-context, a caller must never trust a candidate
list it cannot verify is complete: if the printed JSON fails to parse, or
`len(candidates) != candidate_count`, something still went wrong between the script and
the caller (a size limit on the Bash tool's own stdout capture, a truncated pipe, an
unexpected editor injection) — don't trust a partial set.

On any of those, log "manifest 후보 목록이 잘렸을 수 있어 전체 스캔으로 대체합니다." and fall
through to the standard full-scan path rather than silently searching a partial candidate
set. The same fallback applies when `python3` or the script is unavailable, or the script
exits 3 (manifest absent/unparseable) — which is distinct from a legitimately empty vault
(`candidate_count: 0`, exit 0), where there is nothing to fall back for.
""")

_REF_RANKING_SECTION = _normalise("""\
## Candidate ranking order (Mode 2 step 2c)

**Canonical text.** `vault-searcher.md` Mode 2 step 2c points here; this section is the
binding sort contract. Its whole text — heading to the next heading (here, end of file), so
nothing unpinned may be parked at the bottom — is pinned VERBATIM by `_REF_RANKING_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`. Editing anything below is a deliberate
contract change and updates that constant in the same commit; a reflow is free (the comparison
is whitespace-normalised).

Sort the returned candidates:

1. `status=active` first.
2. Then by the Question-Type Routing tier (`vault-searcher.md` § Question-Type Routing) —
   wiki candidates surface before notes/sources for a 정의/사실 질문, and vice versa for a
   경위/이력 질문; `type: discussion` counts as notes/sources-tier; no reordering for 분류 불가.
3. Then by the recall-weight signals already in the manifest entry: `recent_commits`
   descending — the count of git commits touching the file in the **last 7 days**, i.e.
   recent activity, not all-time work. It measures *writing*, never reads, and a vault left
   uncommitted for a week scores 0 everywhere — silent, not meaningful, so never read a 0 as
   "this page is cold".
4. Then `references_in` descending (cross-note wikilink weight).
5. Then `type: wiki` preferred — the A layer is the primary recall target, so a wiki page
   wins a tie over an equally-scored note. A *tiebreaker only*, never an override that
   buries a more relevant non-wiki hit.
6. Finally `mtime` descending as the last tiebreaker.

These signals are free: `generate-manifest.py`'s `_enrich` already populates them.

Then select the top ≤ 5 candidates by this priority.
""")

_STALE_CONTRACT_SECTION = _normalise("""\
## The contract

`type: wiki` pages carry `verified:` (last-touched date) and, when checkable, `anchor:`
(a source file/URL the dominant claim traces to). When you return a wiki page's content,
mention its `verified:` age alongside it — this is the only staleness signal a source-free
(no `anchor:`) page has, since nothing else flags it as possibly outdated.

Don't silently present an old, anchor-free wiki claim as current fact; a plain
"as of {verified}" note is enough to let the caller hedge.
""")

_STALE_MTIME_SECTION = _normalise("""\
## Why `verified:` and not mtime

Prefer `verified:` over the file's raw modification date. The vault is git-committed
(`/vault-commit`) and a clone/checkout resets filesystem mtimes to the checkout time, so
mtime can understate a page's real age while `verified:` (committed frontmatter) survives
that.
""")

_STALE_LEGACY_SECTION = _normalise("""\
## Legacy pages with no `verified:`

A legacy `type: wiki` page written before #305 may have no `verified:` field at all —
don't invent a date; say the age is unknown instead of silently omitting the hedge.
""")

# --- the ALWAYS-LOADED agent body, pinned the same way ---------------------------------

_AGENT_MANIFEST_FIRST_SECTION = _normalise("""\
#### Manifest-First Protocol

Before running the standard MOC search, attempt to use the vault manifest cache for efficient
targeted loading. This whole section is pinned VERBATIM by `_AGENT_MANIFEST_FIRST_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`: the always-loaded body outranks an
on-demand reference doc, so 2b/2c may not drift from the sections they point at.

1. **Check manifest existence**: `[ -f "{vault_root}/.vault-bridge/manifest.json" ]`
2. **If manifest exists**:
   a. Run the candidate prefilter via `manifest-domain-candidates.py` (never `Read` the raw
      manifest — why, #523: `${CLAUDE_PLUGIN_ROOT}/reference/manifest-recall.md`). Reads it
      untruncated, filters out of context:
      ```bash
      python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-domain-candidates.py" \\
        --domain "{domain}" --vault-path "{vault_path}" "{vault_root}/.vault-bridge/manifest.json"
      ```
      Applies `type == wiki` (always included — #272), `.vault-link` `vault_path`
      directory-scoped prefix, domain-keyword tag/workstream match, or `status == active`.
      Output: `{"candidate_count": N, "candidates": [...]}`.
   b. **Truncation check**: apply § The truncation-check invariant in
      `${CLAUDE_PLUGIN_ROOT}/reference/manifest-recall.md` — that section is the binding
      contract (parse failure or `len(candidates) != candidate_count` → fall through to the
      standard scan below).
   c. **Sort + select**: apply § Candidate ranking order in
      `${CLAUDE_PLUGIN_ROOT}/reference/manifest-recall.md` — that section is the binding
      sort contract (active → Question-Type Routing tier → `recent_commits` →
      `references_in` → `type: wiki` tiebreak → `mtime`, then top ≤ 5).
   d. Read only those specific files. Skip the MOC/grep scan entirely.
   e. **Staleness check**: if manifest `generated_at` is older than 24 hours OR any candidate file's actual `mtime` (via `stat`) is newer than the manifest's `generated_at`, fall through to standard scan below and log a warning: "manifest가 오래되었거나 변경 파일이 있어 전체 스캔으로 대체합니다."
3. **If manifest absent or staleness detected**: proceed with standard full-scan procedure below (graceful degradation — behavior identical to pre-manifest).
""")

_AGENT_RULES_SECTION = _normalise("""\
## Rules

- **Wiki staleness hedge (#305)**: when returning a `type: wiki` page's content, always hedge
  it with the page's `verified:` age — prefer `verified:` over the file's modification date (a
  git checkout resets mtimes, so mtime understates the real age), and if `verified:` is absent
  say the age is unknown rather than inventing one. `anchor:` is the source file/URL the page's
  dominant claim traces to; an anchor-free page has `verified:` as its only staleness signal.
  Apply § The contract in `${CLAUDE_PLUGIN_ROOT}/reference/wiki-staleness.md` as written — that
  section is the binding contract, this bullet is a locator.
- **Read-only (Write Role Contract)**: this agent does not have access to the Write tool, and vault writes are structurally main-context only. If the user requests a session summary, instruct them to invoke `/vault-save` (runs inline in main context, saves `type:capture` to `sources/` immediately — no draft/confirmation step). For compiled, AI-recall domain knowledge distilled from the session, point them to `/wiki` instead.
- Exclude `private` / `sensitive` tagged notes unless user explicitly requests them.
- When results are large, show top items and offer "더 보려면 알려주세요".

This whole section is pinned VERBATIM by `_AGENT_RULES_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`.
""")


# --- adjacency: a heading is otherwise the escape hatch ---------------------------------
#
# "Nothing unpinned may be parked at the bottom of a section" holds only up to the NEXT
# heading, so one inserted `## Addendum` moves arbitrary contradicting text outside every pin.
# manifest-recall.md is not wholly contract (it opens with the #523 defect write-up), so a
# whole-file heading-set assertion would be wrong; instead each pinned section's two
# NEIGHBOURING headings are pinned by identity, so an inserted sibling on either side reds.
# An empty string means "nothing on that side" — for the two sections that end their file,
# that pins the file-final position too, so an appended `## Addendum` also reds.
_NEIGHBOURS = {
    "manifest-recall.md § The truncation-check invariant": (
        "ref", _REF_TRUNCATION_RE,
        ("## `status == active` is unconditional, on purpose (for now)",
         "## Candidate ranking order (Mode 2 step 2c)"),
    ),
    "manifest-recall.md § Candidate ranking order": (
        "ref", _REF_RANKING_RE,
        ("## The truncation-check invariant", ""),
    ),
    "wiki-staleness.md § The contract": (
        "stale", _STALE_CONTRACT_RE,
        ("# vault-searcher — wiki staleness hedge (#305)",
         "## Why `verified:` and not mtime"),
    ),
    "wiki-staleness.md § Why `verified:` and not mtime": (
        "stale", _STALE_MTIME_RE,
        ("## The contract", "## Legacy pages with no `verified:`"),
    ),
    "wiki-staleness.md § Legacy pages with no `verified:`": (
        "stale", _STALE_LEGACY_RE,
        ("## Why `verified:` and not mtime", ""),
    ),
}


# --- clause pins kept for a readable diagnosis of one specific invariant each -----------

_TRUNCATION_CONTRACT = _normalise("""
a caller must never trust a candidate list it cannot verify is complete: if the printed JSON
fails to parse, or `len(candidates) != candidate_count`, something still went wrong between the
script and the caller
""")

_TRUNCATION_FALLBACK = _normalise("""
fall through to the standard full-scan path rather than silently searching a partial candidate
set
""")

_RANKING_CONTRACT = _normalise("""
Then `type: wiki` preferred — the A layer is the primary recall target, so a wiki page wins a
tie over an equally-scored note. A *tiebreaker only*, never an override that buries a more
relevant non-wiki hit.
""")

_RANKING_SELECT = _normalise("Then select the top ≤ 5 candidates by this priority.")

_STALENESS_HEDGE = _normalise("""
When you return a wiki page's content, mention its `verified:` age alongside it
""")

_STALENESS_MTIME = _normalise("""
Prefer `verified:` over the file's raw modification date.
""")

_STALENESS_UNKNOWN = _normalise("""
don't invent a date; say the age is unknown instead of silently omitting the hedge
""")

# The locators are pinned by SECTION NAME + the read-and-apply wording, never by the bare
# path: `reference/manifest-recall.md` is already cited twice in the body as a #523 rationale
# ("never `Read` the raw manifest — why, #523: ..."), so a path-only check stays green after
# every binding pointer has decayed into a citation.
_LOCATOR_TRUNCATION = _normalise("""
apply § The truncation-check invariant in `${CLAUDE_PLUGIN_ROOT}/reference/manifest-recall.md`
— that section is the binding contract
""")

_LOCATOR_RANKING = _normalise("""
apply § Candidate ranking order in `${CLAUDE_PLUGIN_ROOT}/reference/manifest-recall.md` — that
section is the binding sort contract
""")

_LOCATOR_STALENESS = _normalise("""
Apply § The contract in `${CLAUDE_PLUGIN_ROOT}/reference/wiki-staleness.md` as written — that
section is the binding contract
""")


def static_checks(agent_text: str, ref_text: str, staleness_text: str) -> list:
    """(condition, description) for every static guard over the agent + its canonical contract."""
    ref = _normalise(ref_text)
    stale = _normalise(staleness_text)
    agent = _normalise(agent_text)
    by_key = {"ref": ref_text, "stale": staleness_text}
    return [
        ("manifest-domain-candidates.py" in agent_text,
         "vault-searcher.md Mode 2 invokes manifest-domain-candidates.py"),
        ("manifest-keyword-candidates.py" in agent_text,
         "vault-searcher.md Mode 3 invokes manifest-keyword-candidates.py"),
        ('Read `{vault_root}/.vault-bridge/manifest.json`' not in agent_text,
         "vault-searcher.md no longer `Read`s the raw manifest directly (#523)"),
        ("#523" in agent_text,
         "vault-searcher.md references #523 at the fixed call sites"),
        # --- total: the whole section, verbatim ---
        (_section(_REF_TRUNCATION_RE, ref_text) == _REF_TRUNCATION_SECTION,
         "manifest-recall.md § The truncation-check invariant matches VERBATIM"),
        (_section(_REF_RANKING_RE, ref_text) == _REF_RANKING_SECTION,
         "manifest-recall.md § Candidate ranking order matches VERBATIM"),
        (_section(_STALE_CONTRACT_RE, staleness_text) == _STALE_CONTRACT_SECTION,
         "wiki-staleness.md § The contract matches VERBATIM"),
        (_section(_STALE_MTIME_RE, staleness_text) == _STALE_MTIME_SECTION,
         "wiki-staleness.md § Why `verified:` and not mtime matches VERBATIM"),
        (_section(_STALE_LEGACY_RE, staleness_text) == _STALE_LEGACY_SECTION,
         "wiki-staleness.md § Legacy pages with no `verified:` matches VERBATIM"),
        (_section(_AGENT_MANIFEST_FIRST_RE, agent_text) == _AGENT_MANIFEST_FIRST_SECTION,
         "vault-searcher.md § Manifest-First Protocol (loaded body) matches VERBATIM"),
        (_section(_AGENT_RULES_RE, agent_text) == _AGENT_RULES_SECTION,
         "vault-searcher.md § Rules (loaded body) matches VERBATIM"),
        # --- adjacency: no heading inserted on either side of a pinned section ---
    ] + [
        (_neighbour_headings(pattern, by_key[key]) == expected,
         f"{label} still sits between its two known headings "
         f"(an inserted sibling would park text outside the pin)")
        for label, (key, pattern, expected) in _NEIGHBOURS.items()
    ] + [
        # --- diagnostic: one named invariant each, so a failure says which one died ---
        (_TRUNCATION_CONTRACT in ref,
         "manifest-recall.md carries the candidate_count truncation-observability contract"),
        (_TRUNCATION_FALLBACK in ref,
         "manifest-recall.md pins the full-scan fallthrough as the response to truncation"),
        (_RANKING_CONTRACT in ref,
         "manifest-recall.md carries the `type: wiki` tiebreaker-only ranking contract"),
        (_RANKING_SELECT in ref,
         "manifest-recall.md pins the top-5 candidate selection"),
        (_STALENESS_HEDGE in stale,
         "wiki-staleness.md carries the `verified:` hedge obligation"),
        (_STALENESS_MTIME in stale,
         "wiki-staleness.md pins `verified:` over mtime (a checkout resets mtimes)"),
        (_STALENESS_UNKNOWN in stale,
         "wiki-staleness.md pins unknown-age over an invented date for legacy pages"),
        # --- the seam: the locators that make each canonical copy binding ---
        (_LOCATOR_TRUNCATION in agent,
         "vault-searcher.md binds § The truncation-check invariant by section name "
         "(read-and-apply, not a cite)"),
        (_LOCATOR_RANKING in agent,
         "vault-searcher.md binds § Candidate ranking order by section name "
         "(read-and-apply, not a cite)"),
        (_LOCATOR_STALENESS in agent,
         "vault-searcher.md binds wiki-staleness.md § The contract by section name "
         "(read-and-apply, not a cite)"),
        ("candidate_count" in agent_text,
         "vault-searcher.md still names candidate_count at the call sites"),
    ]


def check(cond: bool, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def run(script: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *[str(a) for a in args]],
        capture_output=True, text=True,
    )


def _note(path: str, type_: str = "note", **extra) -> dict:
    e = {
        "path": path, "type": type_, "title": path.rsplit("/", 1)[-1], "tags": ["x"],
        "summary": "s" * 200, "mtime": 0, "size_bytes": 1,
        "references_in": 0, "references_out": 0, "recent_commits": 0,
    }
    e.update(extra)
    return e


def _real_scale_manifest(wiki_count: int = 39, notes_count: int = 104, inbox_count: int = 28,
                          legacy_count: int = 9) -> dict:
    """Rebuild the exact scenario the issue measured on 2026-08-03 (~vault: 180 entries,
    39 wiki / 104 notes / 28 inbox / 9 .legacy), sorted alphabetically like generate-manifest.py's
    `sorted(md_files.items())` — `.legacy` < `inbox` < `notes` < `wiki` (#523 root cause)."""
    files = (
        [_note(f".legacy/l{i}.md") for i in range(legacy_count)]
        + [_note(f"inbox/i{i}.md") for i in range(inbox_count)]
        + [_note(f"notes/n{i}.md") for i in range(notes_count)]
        + [_note(f"wiki/w{i}.md", type_="wiki") for i in range(wiki_count)]
    )
    return {
        "generated_at": "2026-08-03T00:00:00+00:00",
        "vault_root": "/Users/x/vault",
        "schema_version": 4,
        "file_count": len(files),
        "files": files,
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # ---- 1. REPRODUCE: pin the precondition a raw Read used to hit ----

        # notes_count bumped from the issue's measured 104 to 130: this fixture's synthetic
        # entries pretty-print at ~14 lines each (vs. the real vault's measured ~18.6 —
        # real entries carry extra optional fields like status/workstream), so 104 alone
        # would leave the 2,000-line cutoff a couple of entries INTO the wiki/ block instead
        # of before it. 130 restores the margin the real vault's denser entries provided,
        # without changing the wiki_count(39) this repro is about.
        manifest = _real_scale_manifest(notes_count=130)
        pretty = json.dumps(manifest, ensure_ascii=False, indent=2)
        pretty_lines = pretty.count("\n") + 1
        check(pretty_lines > 2000,
              f"repro: real-scale manifest pretty-printed is {pretty_lines} lines "
              "(> Read tool's 2,000-line default cap)")

        truncated_head = "\n".join(pretty.splitlines()[:2000])
        wiki_in_truncated_head = truncated_head.count('"type": "wiki"')
        check(wiki_in_truncated_head == 0,
              "repro: a raw 2,000-line Read of the pretty-printed manifest contains "
              f"{wiki_in_truncated_head} wiki/ entries (confirms 100% loss pre-fix, since "
              "generate-manifest.py sorts wiki/ alphabetically last)")

        manifest_path = tmp / "manifest.json"
        manifest_path.write_text(pretty, encoding="utf-8")

        # ---- 2. FIX: manifest-domain-candidates.py recovers every wiki/ entry ----

        r = run(_DOMAIN_SCRIPT, "--domain", "nope", "--vault-path", "zzz-no-match", manifest_path)
        check(r.returncode == 0, "domain: real-scale manifest -> rc=0")
        out = json.loads(r.stdout) if r.returncode == 0 else {}
        wiki_paths = {c["path"] for c in out.get("candidates", []) if c.get("type") == "wiki"}
        check(len(wiki_paths) == 39,
              f"domain: all 39 wiki/ entries survive as candidates (got {len(wiki_paths)}) — "
              "the #523 fix, even with a domain/vault-path filter that matches nothing else")
        check(out.get("candidate_count") == len(out.get("candidates", [])),
              "domain: candidate_count matches the actual candidates array length")
        check(r.stdout.index('"candidate_count"') < r.stdout.index('"candidates"'),
              "domain: candidate_count is serialized before candidates (survives truncation first)")
        non_wiki_leaked = [c for c in out["candidates"] if c["type"] != "wiki"]
        check(non_wiki_leaked == [],
              "domain: a non-matching domain/vault-path/status pulls in no notes/inbox/.legacy noise")

        # status=active and vault-path prefix arms also work (not just the wiki-always arm)
        active_manifest = _real_scale_manifest(wiki_count=2, notes_count=3, inbox_count=0, legacy_count=0)
        active_manifest["files"].append(_note("notes/active-one.md", status="active"))
        active_path = tmp / "active.json"
        active_path.write_text(json.dumps(active_manifest), encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, "--domain", "", "--vault-path", "", active_path)
        out = json.loads(r.stdout)
        check(any(c["path"] == "notes/active-one.md" for c in out["candidates"]),
              "domain: status=active entries are selected even without a domain/path match")

        # comma-separated domains are split and OR'd, matching the standard-scan fallback's
        # documented "query each individually, merge results" handling (vault-searcher.md
        # Mode 2 standard procedure) instead of matching the whole joined string as one substring
        multi_domain_manifest = {
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 2, "schema_version": 4,
            "files": [_note("notes/backend.md", tags=["backend"]), _note("notes/frontend.md", tags=["frontend"])],
        }
        multi_path = tmp / "multi-domain.json"
        multi_path.write_text(json.dumps(multi_domain_manifest), encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, "--domain", "frontend, backend", "--vault-path", "", multi_path)
        out = json.loads(r.stdout)
        matched = {c["path"] for c in out["candidates"]}
        check(matched == {"notes/backend.md", "notes/frontend.md"},
              f"domain: comma-separated domains are OR'd individually, not matched as one joined "
              f"substring (got {matched})")

        # vault_path is a DIRECTORY-boundary prefix, not a raw string prefix — a sibling
        # directory that merely shares a string prefix (notes/api-legacy) must not leak into
        # a search scoped to notes/api.
        prefix_manifest = {
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 3, "schema_version": 4,
            "files": [
                _note("notes/api.md"),
                _note("notes/api/sub.md"),
                _note("notes/api-legacy/old.md"),
            ],
        }
        prefix_path = tmp / "prefix.json"
        prefix_path.write_text(json.dumps(prefix_manifest), encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, "--domain", "", "--vault-path", "notes/api", prefix_path)
        out = json.loads(r.stdout)
        matched = {c["path"] for c in out["candidates"]}
        check(matched == {"notes/api/sub.md"},
              f"domain: vault_path is a directory boundary — a genuine subpath "
              f"(notes/api/sub.md) matches but the sibling file (notes/api.md) and sibling "
              f"directory (notes/api-legacy/old.md) do NOT leak in (got {matched})")

        # workstream is a match arm alongside tags (pre-#523 contract listed both; the #523
        # rewrite must not silently drop workstream as a match criterion).
        workstream_manifest = {
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 1, "schema_version": 4,
            "files": [_note("notes/proj.md", workstream="claude-kit-migration")],
        }
        workstream_path = tmp / "workstream.json"
        workstream_path.write_text(json.dumps(workstream_manifest), encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, "--domain", "migration", "--vault-path", "", workstream_path)
        out = json.loads(r.stdout)
        check(any(c["path"] == "notes/proj.md" for c in out["candidates"]),
              "domain: a domain term matching only the workstream field still selects the entry")

        # ---- 3. FIX: manifest-keyword-candidates.py finds a keyword that only lives in wiki/ ----

        kw_manifest = _real_scale_manifest(wiki_count=39, notes_count=20, inbox_count=5, legacy_count=2)
        kw_manifest["files"].append(
            _note("wiki/graphql-federation.md", type_="wiki", title="GraphQL Federation Basics",
                  summary="how federated schemas compose across services")
        )
        kw_path = tmp / "kw.json"
        kw_path.write_text(json.dumps(kw_manifest), encoding="utf-8")
        r = run(_KEYWORD_SCRIPT, "graphql federation", kw_path)
        check(r.returncode == 0, "keyword: real-scale manifest -> rc=0")
        out = json.loads(r.stdout) if r.returncode == 0 else {}
        check(any(c["path"] == "wiki/graphql-federation.md" for c in out.get("candidates", [])),
              "keyword: a keyword that only matches a wiki/ page's title is found (#523: used "
              "to be unreachable because the wiki/ entry never survived the manifest read)")
        check(out.get("candidate_count") == len(out.get("candidates", [])),
              "keyword: candidate_count matches the actual candidates array length")

        r = run(_KEYWORD_SCRIPT, "no-such-keyword-anywhere", kw_path)
        out = json.loads(r.stdout)
        check(out == {"candidate_count": 0, "candidates": []},
              "keyword: no match -> empty candidate list with rc=0 (not a failure)")

        # ---- error handling: absent / unparseable manifest never reports a false empty ----

        missing = tmp / "missing.json"
        r = run(_DOMAIN_SCRIPT, missing)
        check(r.returncode == 3 and r.stdout == "", "domain: missing manifest -> rc=3, no stdout")
        r = run(_KEYWORD_SCRIPT, "x", missing)
        check(r.returncode == 3 and r.stdout == "", "keyword: missing manifest -> rc=3, no stdout")

        bad_json = tmp / "bad.json"
        bad_json.write_text("{not json", encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, bad_json)
        check(r.returncode == 3, "domain: unparseable JSON -> rc=3")
        r = run(_KEYWORD_SCRIPT, "x", bad_json)
        check(r.returncode == 3, "keyword: unparseable JSON -> rc=3")

        wrong_shape = tmp / "wrong-shape.json"
        wrong_shape.write_text(json.dumps({"files": "nope"}), encoding="utf-8")
        r = run(_DOMAIN_SCRIPT, wrong_shape)
        check(r.returncode == 3, "domain: files not a list -> rc=3")
        r = run(_KEYWORD_SCRIPT, "x", wrong_shape)
        check(r.returncode == 3, "keyword: files not a list -> rc=3")

        # ---- 4. OBSERVABLE: a truncated script response is detectable, never silent ----

        r = run(_DOMAIN_SCRIPT, "--domain", "nope", "--vault-path", "zzz", manifest_path)
        full_line = r.stdout.strip()
        cut = full_line[: len(full_line) // 2]  # simulate a downstream byte-cap truncation
        try:
            json.loads(cut)
            parse_failed = False
        except json.JSONDecodeError:
            parse_failed = True
        check(parse_failed,
              "observable: a mid-stream-truncated candidate response fails to parse as JSON — "
              "a caller checking this can never mistake it for a smaller-but-complete result")

        # Even a truncation that happens to leave valid (but incomplete) JSON behind must be
        # caught by the candidate_count / actual-length cross-check, not silently accepted.
        parsed = json.loads(full_line)
        forged_short = {"candidate_count": parsed["candidate_count"], "candidates": parsed["candidates"][:5]}
        check(forged_short["candidate_count"] != len(forged_short["candidates"]),
              "observable: candidate_count/actual-length cross-check flags a shortened-but-"
              "valid candidates array instead of accepting it as a real small result")

    # ---- static call-site guards: vault-searcher.md must use the scripts, never a raw Read ----

    agent_text = _AGENT.read_text(encoding="utf-8")
    ref_text = _REF.read_text(encoding="utf-8")
    staleness_text = _STALENESS.read_text(encoding="utf-8")
    for cond, desc in static_checks(agent_text, ref_text, staleness_text):
        check(cond, desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print("\nOK: all manifest-candidate checks passed")
    return 0


# ---------------------------------------------------------------------------
# Self-test: corrupt the CANONICAL contract text and prove the guards still FAIL (#663)
# ---------------------------------------------------------------------------

_CLEAN_AGENT = _AGENT.read_text(encoding="utf-8")
_CLEAN_REF = _REF.read_text(encoding="utf-8")
_CLEAN_STALENESS = _STALENESS.read_text(encoding="utf-8")

# Truncation observability weakened: the cross-check that catches a shortened-but-valid
# candidates array is replaced by one that can never fail.
_REF_WEAK_TRUNCATION = _CLEAN_REF.replace(
    "`len(candidates) != candidate_count`",
    "`len(candidates) < 0`",
    1,
)
# The wiki tiebreaker silently promoted into an override — the exact rewrite the verbatim
# pin exists to catch.
_REF_WIKI_OVERRIDE = _CLEAN_REF.replace(
    "A *tiebreaker only*, never an override that\n   buries a more relevant non-wiki hit.",
    "This overrides the match tier, so a wiki page always outranks a non-wiki hit.",
)
# The full-scan fallthrough deleted: truncation would be detected and then ignored.
_REF_NO_FALLBACK = _CLEAN_REF.replace(
    "fall\nthrough to the standard full-scan path rather than silently searching a partial candidate\nset.",
    "continue with whatever candidates arrived.",
)
# Top-5 selection dropped from the canonical sort contract.
_REF_NO_SELECT = _CLEAN_REF.replace(
    "Then select the top ≤ 5 candidates by this priority.", "")
# The agent body stops pointing at the canonical copy — the contract still exists, but
# nothing binds the agent to it.
_AGENT_NO_POINTER = _CLEAN_AGENT.replace("reference/manifest-recall.md", "reference/README.md")
# The two binding pointers decay into the bare #523 rationale citation that was already in the
# body before #663 — the contract still exists, nothing routes the agent to it at the step that
# needs it. A path-only pointer check cannot see this; the section-name pins can.
_AGENT_POINTER_DECAYED = _CLEAN_AGENT.replace(
    "apply § The truncation-check invariant in", "see (background) the notes in",
).replace(
    "apply § Candidate ranking order in", "see (background) the notes in",
)
# The #305 hedge obligation deleted from its canonical home.
_STALENESS_NO_HEDGE = _CLEAN_STALENESS.replace(
    "When you return a wiki page's content,\nmention its `verified:` age alongside it",
    "Mention the age if it seems useful",
)
# The mtime clause deleted: the exact regression the paragraph exists to forbid.
_STALENESS_NO_MTIME = _CLEAN_STALENESS.replace(
    "Prefer `verified:` over the file's raw modification date.",
    "Use whichever date is available.",
)
# Legacy pages: unknown-age hedge weakened into an invented date.
_STALENESS_INVENTS_DATE = _CLEAN_STALENESS.replace(
    "don't invent a date; say the age is unknown instead of silently omitting the hedge",
    "fall back to the file's modification date",
)
# The agent body stops pointing at the staleness contract at all.
_AGENT_NO_STALENESS_POINTER = _CLEAN_AGENT.replace(
    "reference/wiki-staleness.md", "reference/README.md")

# --- deletions the OLD substring suite let through: unpinned remainder of a pinned section ---
# `status=active` demoted from the top of the sort — the one signal that guarantees the
# in-progress note surfaces at all.
_REF_ACTIVE_DEMOTED = _CLEAN_REF.replace(
    "1. `status=active` first.", "1. `status=active` last.")
# The "a 0 is silent, not cold" caveat deleted, so an uncommitted vault reads as all-cold.
_REF_NO_ZERO_CAVEAT = _CLEAN_REF.replace(
    " It measures *writing*, never reads, and a vault left\n   uncommitted for a week scores 0 everywhere — silent, not meaningful, so never read a 0 as\n   \"this page is cold\".",
    "")
# The script-unavailable / exit-3 arm of the fallback deleted, along with the empty-vault
# distinction that keeps a legitimately empty result from triggering a full scan.
_REF_NO_SCRIPT_MISSING_ARM = _CLEAN_REF.replace(
    " The same fallback applies when `python3` or the script is unavailable, or the script\nexits 3 (manifest absent/unparseable) — which is distinct from a legitimately empty vault\n(`candidate_count: 0`, exit 0), where there is nothing to fall back for.",
    "")
# The anchor-free rationale deleted from the #305 hedge: the hedge survives as an unexplained
# nicety, so the next editor drops it as noise.
_STALENESS_NO_ANCHOR_RATIONALE = _CLEAN_STALENESS.replace(
    "Don't silently present an old, anchor-free wiki claim as current fact; a plain\n\"as of {verified}\" note is enough to let the caller hedge.",
    "")

# --- the ALWAYS-LOADED body corrupted to contradict the canonical section it points at ---
# All three were green under the old substring suite, which only checked that the agent
# NAMED the sections — never what the body said about them.
_AGENT_RANKING_AS_OVERRIDE = _CLEAN_AGENT.replace(
    "`type: wiki` tiebreak → `mtime`, then top ≤ 5",
    "`type: wiki` override → `mtime`, no cap")
_AGENT_TRUNCATION_IGNORED = _CLEAN_AGENT.replace(
    "(parse failure or `len(candidates) != candidate_count` → fall through to the\n      standard scan below)",
    "(proceed with whatever candidates arrived)")
_AGENT_MTIME_PREFERRED = _CLEAN_AGENT.replace(
    "prefer `verified:` over the file's modification date",
    "prefer the file's modification date over `verified:`")

# --- a heading used as an escape hatch: contradicting text parked in a NEW sibling section,
# immediately after the pinned one, so every whole-section pin still matches. The old
# substring checks all stayed green on exactly this shape.
_REF_ADDENDUM_INSERTED = _CLEAN_REF.replace(
    "\n## Candidate ranking order (Mode 2 step 2c)",
    "\n## Addendum\n\nA partial candidate set is fine in practice; skip the full-scan"
    " fallthrough.\n\n## Candidate ranking order (Mode 2 step 2c)")
# Same escape hatch at the END of the file, where the ranking section has no following
# heading to displace — the "" neighbour is what catches this one.
_REF_ADDENDUM_APPENDED = _CLEAN_REF + (
    "\n## Addendum\n\nIgnore the top-5 cap and let `type: wiki` override the match tier.\n")
_STALENESS_ADDENDUM_INSERTED = _CLEAN_STALENESS.replace(
    "\n## Why `verified:` and not mtime",
    "\n## Addendum\n\nThe hedge is optional when the page looks recent.\n"
    "\n## Why `verified:` and not mtime")

# A realistic reflow: every paragraph rewrapped onto one line, headings left where they are
# (an editor rewraps prose, it does not fold a `##` into the paragraph above it — and the
# section slices are heading-delimited, so folding the headings away would test the slicer,
# not the pin).
def _reflow(text: str) -> str:
    return "\n\n".join(
        block if block.startswith("#") else " ".join(block.split())
        for block in text.split("\n\n")
    )


_REF_REFLOWED = _reflow(_CLEAN_REF)
_STALENESS_REFLOWED = _reflow(_CLEAN_STALENESS)

# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of
# its base, and an expect-FAIL case on an unmodified copy would then be testing nothing.
for _name, _fixture, _base in (
    ("_REF_WEAK_TRUNCATION", _REF_WEAK_TRUNCATION, _CLEAN_REF),
    ("_REF_WIKI_OVERRIDE", _REF_WIKI_OVERRIDE, _CLEAN_REF),
    ("_REF_NO_FALLBACK", _REF_NO_FALLBACK, _CLEAN_REF),
    ("_REF_NO_SELECT", _REF_NO_SELECT, _CLEAN_REF),
    ("_REF_ACTIVE_DEMOTED", _REF_ACTIVE_DEMOTED, _CLEAN_REF),
    ("_REF_NO_ZERO_CAVEAT", _REF_NO_ZERO_CAVEAT, _CLEAN_REF),
    ("_REF_NO_SCRIPT_MISSING_ARM", _REF_NO_SCRIPT_MISSING_ARM, _CLEAN_REF),
    ("_REF_ADDENDUM_INSERTED", _REF_ADDENDUM_INSERTED, _CLEAN_REF),
    ("_REF_ADDENDUM_APPENDED", _REF_ADDENDUM_APPENDED, _CLEAN_REF),
    ("_REF_REFLOWED", _REF_REFLOWED, _CLEAN_REF),
    ("_AGENT_NO_POINTER", _AGENT_NO_POINTER, _CLEAN_AGENT),
    ("_AGENT_POINTER_DECAYED", _AGENT_POINTER_DECAYED, _CLEAN_AGENT),
    ("_AGENT_NO_STALENESS_POINTER", _AGENT_NO_STALENESS_POINTER, _CLEAN_AGENT),
    ("_AGENT_RANKING_AS_OVERRIDE", _AGENT_RANKING_AS_OVERRIDE, _CLEAN_AGENT),
    ("_AGENT_TRUNCATION_IGNORED", _AGENT_TRUNCATION_IGNORED, _CLEAN_AGENT),
    ("_AGENT_MTIME_PREFERRED", _AGENT_MTIME_PREFERRED, _CLEAN_AGENT),
    ("_STALENESS_NO_HEDGE", _STALENESS_NO_HEDGE, _CLEAN_STALENESS),
    ("_STALENESS_NO_MTIME", _STALENESS_NO_MTIME, _CLEAN_STALENESS),
    ("_STALENESS_INVENTS_DATE", _STALENESS_INVENTS_DATE, _CLEAN_STALENESS),
    ("_STALENESS_NO_ANCHOR_RATIONALE", _STALENESS_NO_ANCHOR_RATIONALE, _CLEAN_STALENESS),
    ("_STALENESS_ADDENDUM_INSERTED", _STALENESS_ADDENDUM_INSERTED, _CLEAN_STALENESS),
    ("_STALENESS_REFLOWED", _STALENESS_REFLOWED, _CLEAN_STALENESS),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


def self_test() -> int:
    cases = [
        ("clean agent + clean reference docs pass every static guard",
         _CLEAN_AGENT, _CLEAN_REF, _CLEAN_STALENESS, True),
        ("canonical truncation cross-check weakened -> FAIL",
         _CLEAN_AGENT, _REF_WEAK_TRUNCATION, _CLEAN_STALENESS, False),
        ("canonical wiki tiebreaker rewritten into an override -> FAIL",
         _CLEAN_AGENT, _REF_WIKI_OVERRIDE, _CLEAN_STALENESS, False),
        ("canonical full-scan fallthrough deleted -> FAIL",
         _CLEAN_AGENT, _REF_NO_FALLBACK, _CLEAN_STALENESS, False),
        ("canonical top-5 selection deleted -> FAIL",
         _CLEAN_AGENT, _REF_NO_SELECT, _CLEAN_STALENESS, False),
        # The next three were all green under the old substring suite — unpinned remainder
        # of a section whose named clauses were the only thing anchored.
        ("canonical sort demotes `status=active` off the top -> FAIL",
         _CLEAN_AGENT, _REF_ACTIVE_DEMOTED, _CLEAN_STALENESS, False),
        ("canonical `recent_commits` zero-is-silent caveat deleted -> FAIL",
         _CLEAN_AGENT, _REF_NO_ZERO_CAVEAT, _CLEAN_STALENESS, False),
        ("canonical script-unavailable / exit-3 fallback arm deleted -> FAIL",
         _CLEAN_AGENT, _REF_NO_SCRIPT_MISSING_ARM, _CLEAN_STALENESS, False),
        ("agent body no longer points at the canonical contract -> FAIL",
         _AGENT_NO_POINTER, _CLEAN_REF, _CLEAN_STALENESS, False),
        # The pointers decay to the pre-#663 rationale citation, which a path-only check
        # cannot distinguish from a binding read-and-apply pointer.
        ("binding pointers decayed into background citations -> FAIL",
         _AGENT_POINTER_DECAYED, _CLEAN_REF, _CLEAN_STALENESS, False),
        # The loaded body contradicting the canonical section it points at — the body wins at
        # runtime, so a perfectly pinned reference doc does not save it.
        ("loaded body turns the wiki tiebreak into an override and drops the top-5 cap -> FAIL",
         _AGENT_RANKING_AS_OVERRIDE, _CLEAN_REF, _CLEAN_STALENESS, False),
        ("loaded body drops the truncation fallthrough -> FAIL",
         _AGENT_TRUNCATION_IGNORED, _CLEAN_REF, _CLEAN_STALENESS, False),
        ("loaded body prefers mtime over `verified:` -> FAIL",
         _AGENT_MTIME_PREFERRED, _CLEAN_REF, _CLEAN_STALENESS, False),
        ("canonical #305 hedge obligation deleted -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_NO_HEDGE, False),
        ("canonical `verified:`-over-mtime clause deleted -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_NO_MTIME, False),
        ("canonical unknown-age rule weakened into an invented date -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_INVENTS_DATE, False),
        ("canonical anchor-free hedge rationale deleted -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_NO_ANCHOR_RATIONALE, False),
        ("agent body no longer points at the staleness contract -> FAIL",
         _AGENT_NO_STALENESS_POINTER, _CLEAN_REF, _CLEAN_STALENESS, False),
        # Adjacent-clause corruption: contradicting text parked in a brand-new sibling
        # heading, just outside every whole-section pin. The old substring suite passed all
        # three of these; the neighbour-heading identity pins are what red them now.
        ("a new `## Addendum` parks contradicting text right after the pinned "
         "truncation section -> FAIL",
         _CLEAN_AGENT, _REF_ADDENDUM_INSERTED, _CLEAN_STALENESS, False),
        ("a `## Addendum` appended after the file-final ranking section -> FAIL",
         _CLEAN_AGENT, _REF_ADDENDUM_APPENDED, _CLEAN_STALENESS, False),
        ("a new `## Addendum` parks contradicting text right after wiki-staleness.md "
         "§ The contract -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_ADDENDUM_INSERTED, False),
        # whitespace is not the contract: reflowing the canonical paragraphs still passes
        ("reflowed reference docs still pass (whitespace is not the contract)",
         _CLEAN_AGENT, _REF_REFLOWED, _STALENESS_REFLOWED, True),
    ]
    failed = 0
    for desc, agent_text, ref_text, staleness_text, expect_pass in cases:
        got = all(cond for cond, _ in static_checks(agent_text, ref_text, staleness_text))
        if got == expect_pass:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc} (expected {'pass' if expect_pass else 'fail'}, got "
                  f"{'pass' if got else 'fail'})")
            failed += 1
    if failed:
        print(f"\nFAILED: {failed} self-test case(s) failed")
        return 1
    print(f"\nOK: all {len(cases)} manifest-candidate self-test cases passed")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    raise SystemExit(main())
