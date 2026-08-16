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

Run: python3 vault-bridge/scripts/test/test-manifest-candidates.py
  -> "OK: all N manifest-candidate checks passed" (exit 0) / "FAILED: ..." (exit 1).
"""
import json
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
# budget, so the contract prose moved to reference/manifest-recall.md and the agent body
# keeps a pointer. The pins FOLLOW the prose: they read the reference doc, which is now
# canonical, plus the pointer that makes it binding from the agent's side.
# ---------------------------------------------------------------------------

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

# The #305 wiki-staleness hedge, moved to reference/wiki-staleness.md by the same #663 split.
# It was the one block whose pin did not follow it, and an unpinned region is one that can be
# deleted with the whole suite green (#609 measured exactly that).
_STALENESS_HEDGE = _normalise("""
When you return a wiki page's content, mention its `verified:` age alongside it
""")

_STALENESS_MTIME = _normalise("""
Prefer `verified:` over the file's raw modification date.
""")

_STALENESS_UNKNOWN = _normalise("""
don't invent a date; say the age is unknown instead of silently omitting the hedge
""")


def static_checks(agent_text: str, ref_text: str, staleness_text: str) -> list:
    """(condition, description) for every static guard over the agent + its canonical contract."""
    ref = _normalise(ref_text)
    stale = _normalise(staleness_text)
    return [
        ("manifest-domain-candidates.py" in agent_text,
         "vault-searcher.md Mode 2 invokes manifest-domain-candidates.py"),
        ("manifest-keyword-candidates.py" in agent_text,
         "vault-searcher.md Mode 3 invokes manifest-keyword-candidates.py"),
        ('Read `{vault_root}/.vault-bridge/manifest.json`' not in agent_text,
         "vault-searcher.md no longer `Read`s the raw manifest directly (#523)"),
        ("#523" in agent_text,
         "vault-searcher.md references #523 at the fixed call sites"),
        # The candidate_count truncation-observability contract — canonical copy (#663).
        (_TRUNCATION_CONTRACT in ref,
         "manifest-recall.md carries the candidate_count truncation-observability contract"),
        (_TRUNCATION_FALLBACK in ref,
         "manifest-recall.md pins the full-scan fallthrough as the response to truncation"),
        # The Mode 2 step 2c ranking contract — canonical copy (#663).
        (_RANKING_CONTRACT in ref,
         "manifest-recall.md carries the `type: wiki` tiebreaker-only ranking contract"),
        (_RANKING_SELECT in ref,
         "manifest-recall.md pins the top-5 candidate selection"),
        # The #305 wiki-staleness hedge — canonical copy (#663).
        (_STALENESS_HEDGE in stale,
         "wiki-staleness.md carries the `verified:` hedge obligation"),
        (_STALENESS_MTIME in stale,
         "wiki-staleness.md pins `verified:` over mtime (a checkout resets mtimes)"),
        (_STALENESS_UNKNOWN in stale,
         "wiki-staleness.md pins unknown-age over an invented date for legacy pages"),
        # ...and the pointers that make each canonical copy binding from the agent side.
        # Pinned by the SECTION name, not the bare path: `reference/manifest-recall.md`
        # already appeared twice as a #523 rationale citation, so a path-only check stays
        # true even after both binding pointers are deleted.
        ("reference/manifest-recall.md" in agent_text,
         "vault-searcher.md still names the reference/manifest-recall.md path"),
        ("§ The truncation-check invariant" in agent_text,
         "vault-searcher.md points at manifest-recall.md § The truncation-check invariant"),
        ("§ Candidate ranking order" in agent_text,
         "vault-searcher.md points at manifest-recall.md § Candidate ranking order"),
        ("reference/wiki-staleness.md" in agent_text,
         "vault-searcher.md points at reference/wiki-staleness.md for the #305 hedge"),
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

# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of
# its base, and an expect-FAIL case on an unmodified copy would then be testing nothing.
for _name, _fixture, _base in (
    ("_REF_WEAK_TRUNCATION", _REF_WEAK_TRUNCATION, _CLEAN_REF),
    ("_REF_WIKI_OVERRIDE", _REF_WIKI_OVERRIDE, _CLEAN_REF),
    ("_REF_NO_FALLBACK", _REF_NO_FALLBACK, _CLEAN_REF),
    ("_REF_NO_SELECT", _REF_NO_SELECT, _CLEAN_REF),
    ("_AGENT_NO_POINTER", _AGENT_NO_POINTER, _CLEAN_AGENT),
    ("_AGENT_POINTER_DECAYED", _AGENT_POINTER_DECAYED, _CLEAN_AGENT),
    ("_AGENT_NO_STALENESS_POINTER", _AGENT_NO_STALENESS_POINTER, _CLEAN_AGENT),
    ("_STALENESS_NO_HEDGE", _STALENESS_NO_HEDGE, _CLEAN_STALENESS),
    ("_STALENESS_NO_MTIME", _STALENESS_NO_MTIME, _CLEAN_STALENESS),
    ("_STALENESS_INVENTS_DATE", _STALENESS_INVENTS_DATE, _CLEAN_STALENESS),
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
        ("agent body no longer points at the canonical contract -> FAIL",
         _AGENT_NO_POINTER, _CLEAN_REF, _CLEAN_STALENESS, False),
        # The pointers decay to the pre-#663 rationale citation, which a path-only check
        # cannot distinguish from a binding read-and-apply pointer.
        ("binding pointers decayed into background citations -> FAIL",
         _AGENT_POINTER_DECAYED, _CLEAN_REF, _CLEAN_STALENESS, False),
        ("canonical #305 hedge obligation deleted -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_NO_HEDGE, False),
        ("canonical `verified:`-over-mtime clause deleted -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_NO_MTIME, False),
        ("canonical unknown-age rule weakened into an invented date -> FAIL",
         _CLEAN_AGENT, _CLEAN_REF, _STALENESS_INVENTS_DATE, False),
        ("agent body no longer points at the staleness contract -> FAIL",
         _AGENT_NO_STALENESS_POINTER, _CLEAN_REF, _CLEAN_STALENESS, False),
        # whitespace is not the contract: reflowing the canonical paragraphs still passes
        ("reflowed reference docs still pass (whitespace is not the contract)",
         _CLEAN_AGENT, _normalise(_CLEAN_REF), _normalise(_CLEAN_STALENESS), True),
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
