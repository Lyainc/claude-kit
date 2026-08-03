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

errors = []


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
    check("manifest-domain-candidates.py" in agent_text,
          "vault-searcher.md Mode 2 invokes manifest-domain-candidates.py")
    check("manifest-keyword-candidates.py" in agent_text,
          "vault-searcher.md Mode 3 invokes manifest-keyword-candidates.py")
    check('Read `{vault_root}/.vault-bridge/manifest.json`' not in agent_text,
          "vault-searcher.md no longer `Read`s the raw manifest directly (#523)")
    check("candidate_count" in agent_text,
          "vault-searcher.md documents the candidate_count truncation-observability contract")
    check("#523" in agent_text,
          "vault-searcher.md references #523 at the fixed call sites")

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print("\nOK: all manifest-candidate checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
