#!/usr/bin/env python3
"""Regression test: add-policy SOFT reminder channel is layer-routed with a vanilla fallback.

G28 ① + ③, extended by #377. The engine (feedback-loop/skills/add-policy/SKILL.md) is a
prose skill, so most of this is a static-content check — it does not execute LLM logic. It
pins the claims below, guarding against a future edit silently dropping the machine
work-rule catalogue routing, the vanilla fallback, or (#377) the native-memory duplicate
scan. The one exception is the #377 memory-scan snippet: SKILL.md ships that as *runnable
bash*, so it is actually EXECUTED against temp-HOME fixtures (a prose grep is what let a
zsh-NOMATCH abort slip through review in the first place).

Checks 2 (vanilla fallback) + 3 (no-hardcode/detect) ARE the #300 acceptance sign-off:
the engine is prose with no runtime code path, so "does it degrade on a vanilla machine
where ~/.claude/rules is absent" is guaranteed by proving the SKILL.md instructs the
detect-then-fall-back branch — not by simulating `[ -d ]` (that would test bash, not the
engine). This static guard is the durable form of that verification.

The pinned claims:

1. The SOFT reminder channel is routed by LAYER (both branches described):
   - stance/voice (judgment/expression) -> ~/.claude/CLAUDE.md
   - work-rule -> ~/.claude/rules
2. Vanilla fallback: ~/.claude/rules ABSENT -> CLAUDE.md fallback (both states covered).
3. No-hardcode clause: the machine rules/ structure is DETECTED, never hardcoded.
4. Thin pointer + backing detail when the catalogue channel is used.
5. (#377) §6's duplicate scan covers native auto-memory's `feedback` entries, surfaces the
   hit in the §3 confirmation, and deletes the memory duplicate after landing — memory being
   an input queue, NOT a fourth landfill site.
6. (#377) The scan LISTS candidates; a Duplicate is a CONTENT match. Conflating the two turns
   "land any rule" into "delete every `feedback` memory on the machine". Scan scope follows
   the chosen site (a project-scoped CLAUDE.md is not duplicated by another project's memory).
7. (#377) The new delete path is recoverable (`trash-put`), never forced, and the MEMORY.md
   index line is keyed by the deleted file's link target — not by its title.
8. (#377) Vanilla machine with no ~/.claude/projects memory directory -> the memory scan is
   SILENTLY SKIPPED, never a scan failure. Zero hits is likewise not a failure.
9. (#377) The §6 scan snippet, run for real, against fixtures that include adversarial
   near-misses (`type: feedback-loop`, `type: feedbackx`, `type: feedback` in a note's BODY,
   MEMORY.md itself). It must never abort, must exit 0, and must match ONLY the two real
   `feedback` frontmatter shapes — a fixture set that cannot distinguish the anchored,
   frontmatter-scoped matcher from a bare `feedback` substring is not a guard.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-routing.py
    python3 feedback-loop/scripts/test/test-add-policy-routing.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "feedback-loop" / "skills" / "add-policy" / "SKILL.md"


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Checks — each returns (ok, message). Substring-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
# ---------------------------------------------------------------------------

def check_stance_voice_to_claude_md(text: str) -> tuple[bool, str]:
    """stance/voice must be routed to ~/.claude/CLAUDE.md."""
    lower = text.lower()
    if "stance" not in lower and "judgment" not in lower:
        return False, "stance/voice (judgment) layer not mentioned in routing"
    if "~/.claude/claude.md" not in lower:
        return False, "~/.claude/CLAUDE.md not named as the stance/voice channel"
    return True, "stance/voice -> ~/.claude/CLAUDE.md routing present"


def check_workrule_to_rules(text: str) -> tuple[bool, str]:
    """work-rule must be routed to the ~/.claude/rules catalogue."""
    lower = text.lower()
    if "~/.claude/rules" not in lower:
        return False, "~/.claude/rules catalogue not named as the work-rule channel"
    if "work-rule" not in lower:
        return False, "work-rule layer not mentioned in routing"
    return True, "work-rule -> ~/.claude/rules routing present"


def check_vanilla_fallback(text: str) -> tuple[bool, str]:
    """Absent rules/ must fall back to CLAUDE.md (vanilla portability)."""
    lower = text.lower()
    has_fallback = "fall back" in lower or "fallback" in lower
    has_absent = "absent" in lower or "if it exists" in lower or "vanilla" in lower
    if not (has_fallback and has_absent):
        return False, (
            "vanilla fallback not described — need both a fallback and the "
            "rules-absent / vanilla condition"
        )
    return True, "vanilla fallback (rules absent -> CLAUDE.md) described"


def check_no_hardcode(text: str) -> tuple[bool, str]:
    """The machine rules/ structure must be detected, never hardcoded."""
    lower = text.lower()
    if "never hardcode" not in lower and "not hardcode" not in lower and "no hardcode" not in lower:
        return False, "no-hardcode clause ('never hardcode the machine's rules/ structure') missing"
    if "[ -d" not in text and "detect" not in lower:
        return False, "detection mechanism ([ -d \"$HOME/.claude/rules\" ] / detect) not described"
    return True, "no-hardcode + detect-the-catalogue clause present"


def check_thin_pointer(text: str) -> tuple[bool, str]:
    """Thin pointer + backing detail must be described for the catalogue channel."""
    lower = text.lower()
    if "thin pointer" not in lower and "one-line pointer" not in lower:
        return False, "thin-pointer routing not described"
    if "detail" not in lower:
        return False, "backing detail (catalogue holds the detail) not described"
    return True, "thin pointer + backing detail described"


def check_not_fourth_site(text: str) -> tuple[bool, str]:
    """The routing must be framed as a channel mapping, NOT a fourth landfill site."""
    lower = text.lower()
    if "not a fourth site" not in lower and "no new site" not in lower:
        return False, (
            "routing not framed as 'not a fourth site' — a future reader may mistake "
            "the rules channel for a new landfill site"
        )
    return True, "routing framed as a channel mapping, not a fourth site"


def check_memory_duplicate_scan(text: str) -> tuple[bool, str]:
    """#377: the duplicate scan must cover native auto-memory's `feedback` entries."""
    lower = text.lower()
    if "memory" not in lower or "~/.claude/projects" not in lower:
        return False, "native auto-memory (~/.claude/projects/<proj>/memory) not named as a scan target"
    if "feedback" not in lower:
        return False, "the `feedback`-type memory entry (the scan target) not named"
    if "duplicate" not in lower:
        return False, "memory scan not tied to the Duplicate check"
    # The hit must reach the user (§3 confirmation) and leave exactly one copy behind.
    # Memory-specific wording on purpose: a bare "delete" is already satisfied by pre-#377 prose.
    if "memory 항목은 지울게요" not in text and "memory duplicate" not in lower:
        return False, "post-landing removal of the memory duplicate not described"
    # Memory-specific wording: a bare "not a fourth site" already appears twice in pre-#377 prose
    # (the SOFT-channel routing), so it cannot pin THIS claim.
    if "memory is an input, never a destination" not in lower:
        return False, "memory not framed as an input — a reader may add it as a 4th landfill site"
    return True, "memory `feedback` duplicate scan + removal described (memory stays an input)"


def check_memory_candidate_vs_duplicate(text: str) -> tuple[bool, str]:
    """#377 review BLOCKER: the grep LISTS candidates; a Duplicate is a CONTENT match.

    Conflating the two turns "land any rule" into "delete every `feedback` memory on the
    machine" (12 unrelated files on the author's own store). The prose must keep them apart,
    and must scope the scan to the chosen site (a project-scoped CLAUDE.md is not duplicated
    by another project's memory).
    """
    lower = text.lower()
    if "candidate" not in lower:
        return False, "the scan's output is not framed as CANDIDATES (a grep hit != a duplicate)"
    if "only a content match" not in lower:
        return False, "Duplicate not defined as a CONTENT match — a bare `type: feedback` would be deleted"
    if "scan_root" not in lower:
        return False, "scan scope not tied to the chosen site (SCAN_ROOT)"
    if "project-scoped" not in lower:
        return False, "project-scoped site -> that project's memory only: scope branch not described"
    return True, "grep = candidates, Duplicate = content match; scan scope follows the site"


def check_memory_delete_safety(text: str) -> tuple[bool, str]:
    """#377 review: this PR introduces a DELETE path — pin its recoverable-delete clause."""
    lower = text.lower()
    if "trash-put" not in lower:
        return False, "memory-duplicate removal does not mandate a recoverable delete (trash-put)"
    if "never force-delete" not in lower or "never `rm`" not in lower:
        return False, "the never-force-delete / never-`rm` guarantee on the memory delete path is missing"
    if "link target" not in lower:
        return False, "MEMORY.md index-line removal has no join key — an LLM could delete the wrong line"
    return True, "memory delete is recoverable (trash-put), never forced; index line keyed by link target"


def check_memory_vanilla_skip(text: str) -> tuple[bool, str]:
    """#377: a machine with no memory directory must skip the scan silently."""
    lower = text.lower()
    if "$home/.claude/projects" not in lower and "~/.claude/projects" not in lower:
        return False, "memory-directory existence check not described"
    if "skip the memory scan" not in lower:
        return False, "silent skip on a vanilla machine (no memory directory) not described"
    # Memory-specific wording: §5's own "not as a scan failure" line predates #377.
    if "never a scan failure" not in lower:
        return False, "missing directory must be stated as 'nothing to conflict with', never a scan failure"
    return True, "vanilla machine (no memory directory) -> memory scan silently skipped"


_BASH_BLOCK_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def _extract_memory_snippet(text: str) -> str | None:
    """The one fenced bash block in SKILL.md that scans the memory directory."""
    for block in _BASH_BLOCK_RE.findall(text):
        if "/memory/" in block and "feedback" in block:
            return block
    return None


def _run_snippet(snippet: str, home: Path, shell: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [shell, "-c", snippet],
        env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )


def check_memory_snippet_runs(text: str) -> tuple[bool, str]:
    """#377: EXECUTE the §6 scan snippet — prose alone can't catch an aborting glob.

    Three fixture HOMEs, under every shell available (the skill's snippet runs in whatever
    shell the Bash tool uses — zsh on macOS, bash in CI — and an unmatched glob aborts under
    zsh but not bash, so both must be exercised where present).
    """
    snippet = _extract_memory_snippet(text)
    if snippet is None:
        return False, "no runnable memory-scan bash snippet found in SKILL.md §6"

    shells = [s for s in ("/bin/bash", "/bin/zsh", "/bin/sh") if Path(s).exists() or shutil.which(s)]
    if not shells:
        # Never pass vacuously: "could not verify" is a failure, not a skip. Python is running,
        # so /bin/sh exists in any environment this test can be invoked from.
        return False, "no shell available to execute the snippet — cannot verify, so cannot pass"

    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty"                                  # no ~/.claude at all
        (empty / ".claude").mkdir(parents=True)
        no_mem = Path(tmp) / "no-mem"                                # projects/, but no memory/
        (no_mem / ".claude" / "projects" / "-some-proj").mkdir(parents=True)
        full = Path(tmp) / "full"                                    # a populated memory store
        mem = full / ".claude" / "projects" / "-some-proj" / "memory"
        mem.mkdir(parents=True)
        # Two real `feedback` shapes: a top-level `type:` and one nested under `metadata:`.
        (mem / "hit-nested.md").write_text(
            "---\nname: x\nmetadata:\n  node_type: memory\n  type: feedback\n---\nbody\n"
        )
        (mem / "hit-toplevel.md").write_text("---\nname: y\ntype: feedback\n---\nbody\n")
        # Adversarial near-misses. Without these, a bare `feedback` substring match passes this
        # check as happily as the real anchored, frontmatter-scoped one (proven in review).
        (mem / "miss-other-type.md").write_text("---\nname: z\nmetadata:\n  type: project\n---\nbody\n")
        (mem / "miss-prefix.md").write_text("---\nname: a\ntype: feedback-loop\n---\nbody\n")
        (mem / "miss-suffix.md").write_text("---\nname: b\ntype: feedbackx\n---\nbody\n")
        (mem / "miss-body.md").write_text(          # frontmatter says project; BODY quotes the type
            "---\nname: c\ntype: project\n---\nAn example entry looks like:\ntype: feedback\n"
        )
        (mem / "MEMORY.md").write_text(             # the index is not itself a memory
            "---\ntype: feedback\n---\n- [x](hit-toplevel.md) — hook\n"
        )

        for shell in shells:
            for label, home in (("no ~/.claude/projects", empty), ("projects/ but no memory/", no_mem)):
                p = _run_snippet(snippet, home, shell)
                if p.returncode != 0 or p.stdout.strip() or p.stderr.strip():
                    return False, (
                        f"[{shell}] vanilla case ({label}) did not skip silently — "
                        f"rc={p.returncode} stdout={p.stdout.strip()!r} stderr={p.stderr.strip()!r}"
                    )

            p = _run_snippet(snippet, full, shell)
            found = {Path(line).name for line in p.stdout.split() if line}
            if found != {"hit-nested.md", "hit-toplevel.md"}:
                return False, (
                    f"[{shell}] populated case: expected exactly the two `feedback` frontmatter "
                    f"shapes, got {sorted(found)} (rc={p.returncode}, stderr={p.stderr.strip()!r})"
                )
            # Zero hits is a normal result, not a failure: an LLM reads the exit code.
            if p.returncode != 0:
                return False, f"[{shell}] populated case exited {p.returncode} — a hit must not look like a failure"

        empty_mem = Path(tmp) / "empty-mem"          # memory/ exists, but nothing `feedback` in it
        em = empty_mem / ".claude" / "projects" / "-some-proj" / "memory"
        em.mkdir(parents=True)
        (em / "only-project.md").write_text("---\nname: p\ntype: project\n---\nbody\n")
        for shell in shells:
            p = _run_snippet(snippet, empty_mem, shell)
            if p.returncode != 0 or p.stdout.strip():
                return False, (
                    f"[{shell}] zero-hit case must exit 0 with no output (it is not a failure) — "
                    f"rc={p.returncode} stdout={p.stdout.strip()!r}"
                )

    return True, f"§6 scan snippet executes correctly under {', '.join(shells)} (vanilla + zero-hit + populated)"


_CHECKS = [
    check_stance_voice_to_claude_md,
    check_workrule_to_rules,
    check_vanilla_fallback,
    check_no_hardcode,
    check_thin_pointer,
    check_not_fourth_site,
    check_memory_duplicate_scan,
    check_memory_candidate_vs_duplicate,
    check_memory_delete_safety,
    check_memory_vanilla_skip,
    check_memory_snippet_runs,
]


def run_checks(text: str) -> tuple[int, int]:
    passed = failed = 0
    for check in _CHECKS:
        ok, msg = check(text)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test (in-memory fixtures)
# ---------------------------------------------------------------------------

_PASSING = """\
**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):**
- judgment / expression (stance·voice) -> the top-level ~/.claude/CLAUDE.md persona block.
- work-rule (how you do the work) -> the machine work-rule catalogue ~/.claude/rules
  if it exists; otherwise fall back to ~/.claude/CLAUDE.md.

The fallback is non-negotiable: never hardcode the machine's rules/ structure. Detect it
([ -d "$HOME/.claude/rules" ]) and degrade to CLAUDE.md on a vanilla machine where
~/.claude/rules is absent.

Thin pointer + backing detail: put the detail in the catalogue and keep ~/.claude/CLAUDE.md
to at most a one-line pointer / thin pointer.

The Duplicate scan also covers native auto-memory: scan the `feedback` entries under
~/.claude/projects/<proj>/memory/*.md. Step 1 lists CANDIDATES; step 2 reads each and
compares it to the rule being landed — only a content match is a duplicate. SCAN_ROOT
follows the site: a machine-global site scans all projects, a project-scoped CLAUDE.md
scans that project's memory only. Vanilla machine with no such directory ->
skip the memory scan silently; a missing directory is nothing to conflict with,
never a scan failure. On a
hit, surface it in the 1-click confirmation ("매립 후 memory 항목은 지울게요") and delete the
duplicate memory file after the landfill write — its MEMORY.md index line is the one whose
markdown link target is that file's basename. Use trash-put; never force-delete, never `rm`.
Memory is an input, never a destination: an input queue, not a fourth site.

```bash
SCAN_ROOT="$HOME/.claude/projects"
[ -d "$SCAN_ROOT" ] && find "$SCAN_ROOT" -path '*/memory/*.md' -not -name 'MEMORY.md' -exec awk '
  FNR==1 { n=0 }
  /^---[[:space:]]*$/ { n++ }
  n==1 && /^[[:space:]]*type:[[:space:]]*feedback[[:space:]]*$/ { print FILENAME }
' {} + 2>/dev/null | sort -u || true
```
"""

# Regression of the exact bug G28 fixes: SOFT always -> CLAUDE.md, no rules routing,
# no fallback, no no-hardcode clause.
_FAILING = """\
Tier folds into the site: HARD => hook, SOFT => CLAUDE.md. A SOFT rule is always a
CLAUDE.md reminder appended as one prose line.
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    # On the pre-G28/pre-#377 fixture, every rules/fallback/hardcode/memory claim is absent.
    for check in _CHECKS:
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s): {failed}")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        return _self_test()

    print(f"Checking: {_SKILL_PATH}\n")
    try:
        text = _load_skill()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(text)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} add-policy-routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
