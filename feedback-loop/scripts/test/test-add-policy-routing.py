#!/usr/bin/env python3
"""Regression test: add-policy SOFT reminder channel is layer-routed with a vanilla fallback.

G28 ① + ③, extended by #377. The engine (feedback-loop/skills/add-policy/SKILL.md) is a
prose skill, so most of this is a static-content check — it does not execute LLM logic. It
pins the claims below, guarding against a future edit silently dropping the machine
work-rule catalogue routing, the vanilla fallback, or (#377) the native-memory duplicate
scan. The one exception is the #377 memory-scan snippet: it ships as *runnable bash*, so it is
actually EXECUTED against temp-HOME fixtures (a prose grep is what let a zsh-NOMATCH abort slip
through review in the first place). Since #469 that snippet lives in `reference.md` §6-snippet,
not SKILL.md — the split moved executable text out of the 5,000-token compaction window and
kept the decision in.

#663 moved the memory-scan DECISION out too, into `reference.md` §6-memory-contract, and left a
locator paragraph in SKILL.md §6. Two reasons, one budget and one structural: SKILL.md sat at
~4,644 of the #447 5,000-token budget with nothing left to trim that was not a contract, and a
mid-section prose block has no heading to pin against, so the escape hatch below could not be
closed while it lived in the body. So the live run reads BOTH files, and which claim is read
from which file is itself part of the contract: the §3 routing claims and the §6 locator stay
pinned to SKILL.md (the file compaction re-attaches), the memory-scan contract and the scan
command to reference.md. They are never concatenated — a claim that could be satisfied from
either file leaves the split's own seam unguarded.

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
5. (#377) The duplicate scan covers native auto-memory's `feedback` entries, surfaces the
   hit in the §3 confirmation, and deletes the memory duplicate after landing — memory being
   an input queue, NOT a fourth landfill site.
6. (#377) The scan LISTS candidates; a Duplicate is a CONTENT match. Conflating the two turns
   "land any rule" into "delete every `feedback` memory on the machine". Scan scope follows
   the chosen site (a project-scoped CLAUDE.md is not duplicated by another project's memory).
7. (#377) The new delete path is recoverable (`trash-put`), never forced, and the MEMORY.md
   index line is keyed by the deleted file's link target — not by its title.
8. (#377) Vanilla machine with no ~/.claude/projects memory directory -> the memory scan is
   SILENTLY SKIPPED, never a scan failure. Zero hits is likewise not a failure. But an ERRORED
   scan is not an empty one: the pipe fixes the exit code at `sort`'s, so stderr is the only
   channel left, and an inconclusive scan must be reported as such — never as "no duplicates".
9b. (#469) SKILL.md still points at `reference.md` §6-snippet AND says to run the command
   there. A dropped pointer leaves the engine knowing it must scan memory with no command to
   scan it with — which degrades into an improvised `grep`, the exact matcher §6-snippet exists
   to prevent.
9. (#377) The §6 scan snippet, run for real, against fixtures that include adversarial
   near-misses (`type: feedback-loop`, `type: feedbackx`, `type: feedback` in a note's BODY,
   MEMORY.md itself). It must never abort, must exit 0, and must match ONLY the two real
   `feedback` frontmatter shapes — a fixture set that cannot distinguish the anchored,
   frontmatter-scoped matcher from a bare `feedback` substring is not a guard.

10. (#663) THE PIN LAYER, which is what makes 1-9 more than a keyword census. Every check above
   is a phrase check, and a phrase check is a blocklist of the last wording someone tried: it
   closes the clause it names and leaves the next neighbour free. Measured against this very
   file — `SCAN_ROOT follows the site` can stay verbatim while the sentence after it is
   rewritten into "scan every project regardless", and every check stays green. So four regions
   are now compared WHOLE and VERBATIM (whitespace-normalised), and each has its adjacency
   pinned by identity so nothing may be parked immediately beside it:

   | Region | Where | Adjacency pinned |
   |--------|-------|------------------|
   | `## 3.` the three landfill sites | SKILL.md (always-loaded body) | `## 2.` / `## 4.` headings |
   | the §6 memory locator paragraph | SKILL.md (always-loaded body) | its two §6 neighbour paragraphs |
   | `## §6-memory-contract` | reference.md (canonical) | `## §6-new-site` / `## §6-memory` |
   | `## §6-snippet` | reference.md (canonical) | `## §6-memory` / `## §6-gate-contract` |

   The SKILL.md side is pinned as hard as the reference side ON PURPOSE: at runtime the loaded
   body outranks an on-demand doc, so a locator that decays into "memory is optional" defeats a
   perfectly pinned canonical section. Neither adjacency pin is a whole-file heading-set
   assertion — reference.md is not wholly contract and SKILL.md is free to gain sections. Only
   the immediate neighbours of each pinned region are fixed, which is what an inserted sibling
   (`## §6-memory-addendum`, `## 3b. …`) has to break to park text outside the pin.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-routing.py
    python3 feedback-loop/scripts/test/test-add-policy-routing.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "feedback-loop" / "skills" / "add-policy" / "SKILL.md"


_REFERENCE_PATH = _SKILL_PATH.with_name("reference.md")


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _load_reference() -> str:
    """#469: the runnable scan command lives here. #663: so does the memory-scan contract."""
    if not _REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"reference.md not found at {_REFERENCE_PATH}")
    return _REFERENCE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phrase checks — each returns (ok, message). Substring-based on purpose: the claim
# is prose, and this layer's job is "is this claim still stated", not exact wording.
# Coverage against a rewrite of the region AROUND a claim is the pin layer's job,
# further down; these are kept for the diagnosis they give, naming which invariant died.
# ---------------------------------------------------------------------------

def _prose(text: str) -> str:
    """Prose wraps across lines — a claim must be findable regardless of where it broke.

    Line-wrapping split "neither a duplicate nor yours to\ndelete" and silently failed a
    check whose claim WAS present. Prose checks match against this; the snippet check does
    NOT (it needs the raw fenced block).
    """
    return re.sub(r"\s+", " ", text).lower()


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
    """#377: the duplicate scan must cover native auto-memory's `feedback` entries.

    #663: read against reference.md §6-memory-contract, which is where the canonical text
    lives now. SKILL.md's side of this claim is `check_scan_command_pointer` plus the locator
    paragraph pin.
    """
    lower = _prose(text)
    if "memory" not in lower or "~/.claude/projects" not in lower:
        return False, "native auto-memory (~/.claude/projects/<proj>/memory) not named as a scan target"
    if "feedback" not in lower:
        return False, "the `feedback`-type memory entry (the scan target) not named"
    if "duplicate" not in lower:
        return False, "memory scan not tied to the Duplicate check"
    # The hit must reach the user (§3 confirmation) and leave exactly one copy behind.
    # Memory-specific wording on purpose: a bare "delete" is already satisfied by pre-#377 prose.
    if "memory 항목은 지울게요" not in lower and "memory duplicate" not in lower:
        return False, "post-landing removal of the memory duplicate not described"
    # Memory-specific wording: a bare "not a fourth site" already appears twice in pre-#377 prose
    # (the SOFT-channel routing), so it cannot pin THIS claim.
    if "memory is an input, never a destination" not in lower:
        return False, "memory not framed as an input — a reader may add it as a 4th landfill site"
    return True, "memory `feedback` duplicate scan + removal described (memory stays an input)"


def check_memory_candidate_vs_duplicate(text: str) -> tuple[bool, str]:
    """#377 review BLOCKER: the scan LISTS candidates; a Duplicate is a CONTENT match.

    Conflating the two turns "land any rule" into "delete every `feedback` memory on the
    machine" (12 unrelated files on the author's own store). The prose must keep them apart,
    and must scope the scan to the chosen site (a project-scoped CLAUDE.md is not duplicated
    by another project's memory).
    """
    lower = _prose(text)
    # Memory-specific literals only. A bare "candidate" already appears in pre-#377 prose
    # (§5's provenance scan), so it cannot pin this claim — proven in review.
    if "list candidates" not in lower:
        return False, "the scan's output is not framed as CANDIDATES (a scan hit != a duplicate)"
    if "only a content match" not in lower:
        return False, "Duplicate not defined as a CONTENT match — a bare `type: feedback` would be deleted"
    if "is not a duplicate and is never touched" not in lower:
        return False, "a non-matching candidate is not explicitly protected from the delete path"
    if "scan_root" not in lower:
        return False, "scan scope not tied to the chosen site (SCAN_ROOT)"
    if "neither a duplicate nor yours to delete" not in lower:
        return False, "project-scoped site -> that project's memory only: scope branch not described"
    return True, "scan = candidates, Duplicate = content match; scan scope follows the site"


def check_memory_scan_fails_loud(text: str) -> tuple[bool, str]:
    """#377 re-review: the pipe fixes rc at `sort`'s, so a dead awk must at least reach stderr.

    A duplicate check whose failure mode is "reports zero duplicates" fails in the wrong
    direction — it would green-light a landfill write that leaves the duplicate in place.
    """
    lower = _prose(text)
    if "inconclusive" not in lower:
        return False, "a failed memory scan is not distinguished from a clean one (must be INCONCLUSIVE, not `none`)"
    if "stderr" not in lower:
        return False, "stderr is the only failure channel left after the pipe, and it is not named"
    # The user-facing half: a bash comment saying "inconclusive" changes nothing on its own.
    if "memory 스캔 실패" not in lower:
        return False, "an inconclusive scan is not surfaced to the user in the §3 confirmation"
    return True, "an errored memory scan is reported as inconclusive, never as `none`"


def check_memory_delete_safety(text: str) -> tuple[bool, str]:
    """#377 review: this PR introduces a DELETE path — pin its recoverable-delete clause."""
    lower = _prose(text)
    if "trash-put" not in lower:
        return False, "memory-duplicate removal does not mandate a recoverable delete (trash-put)"
    # The combined literal, not "never `rm`" alone — that one already appears in pre-#377
    # prose (§2's HARD/SOFT example), so on its own it pins nothing. Proven in review.
    if "never force-delete, never `rm`" not in lower:
        return False, "the never-force-delete / never-`rm` guarantee on the memory delete path is missing"
    if "link target" not in lower:
        return False, "MEMORY.md index-line removal has no join key — an LLM could delete the wrong line"
    return True, "memory delete is recoverable (trash-put), never forced; index line keyed by link target"


def check_memory_vanilla_skip(text: str) -> tuple[bool, str]:
    """#377: a machine with no memory directory must skip the scan silently."""
    lower = _prose(text)
    if "$home/.claude/projects" not in lower and "~/.claude/projects" not in lower:
        return False, "memory-directory existence check not described"
    if "skip the memory scan" not in lower:
        return False, "silent skip on a vanilla machine (no memory directory) not described"
    # Memory-specific wording: §5's own "not as a scan failure" line predates #377.
    if "never a scan failure" not in lower:
        return False, "missing directory must be stated as 'nothing to conflict with', never a scan failure"
    return True, "vanilla machine (no memory directory) -> memory scan silently skipped"


def check_scan_command_pointer(text: str) -> tuple[bool, str]:
    """#469/#663: SKILL.md keeps the locator, reference.md ships the contract and the command.

    That split only holds while SKILL.md still names where the command is AND tells the engine
    to run it — a pointer that decays into a bare citation ("see §6-snippet") is how an
    on-demand step turns optional. Pinned separately from the locator's whole-paragraph pin
    because this one is the seam itself: it must survive even a deliberate rewording of the
    paragraph around it.
    """
    lower = _prose(text)
    if "§6-snippet" not in lower:
        return False, "SKILL.md doesn't name reference.md §6-snippet as where the scan command lives"
    if "run the command" not in lower:
        return False, "the §6-snippet pointer is a citation, not an instruction to run the command"
    if "§6-memory-contract" not in lower:
        return False, (
            "SKILL.md doesn't name reference.md §6-memory-contract as where the memory-scan "
            "contract lives (#663)"
        )
    if "apply it as written" not in lower and "read that section" not in lower:
        return False, (
            "SKILL.md's §6-memory-contract pointer decayed into a bare citation — it must tell "
            "the engine to read and apply that section, not merely cite it"
        )
    return True, "SKILL.md binds §6-memory-contract and §6-snippet by name (read-and-apply, not a cite)"


_BASH_BLOCK_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


_SNIPPET_SECTION_RE = re.compile(r"^## §6-snippet\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)


def _extract_memory_snippet(text: str) -> str | None:
    """The fenced bash block under reference.md's `## §6-snippet`, or None.

    Scoped to that heading, not to "the first block that mentions /memory/ and feedback":
    reference.md §6-memory sits ABOVE §6-snippet, so an illustrative block added there would
    hijack extraction and leave the real command unexercised while the suite stayed green —
    the guard-quietly-stops-guarding shape this file exists to prevent.

    A missing heading is a MISS, never a whole-document fallback. The fallback was tried and
    it silently rescued the failure it was supposed to catch: rename the heading in
    reference.md, leave the block, and SKILL.md's pointer sends the engine to a section that
    no longer exists — while the fallback found the block anyway and the suite stayed green.
    `check_scan_command_pointer` cannot cover that half; it only reads SKILL.md's side of the
    seam. So the fixtures carry the heading instead.
    """
    section = _SNIPPET_SECTION_RE.search(text)
    if section is None:
        return None
    for block in _BASH_BLOCK_RE.findall(section.group(0)):
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
        return False, (
            "no runnable memory-scan bash snippet found under `## §6-snippet` — since #469 it "
            "lives in add-policy/reference.md, not SKILL.md"
        )

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
        (mem / "miss-no-frontmatter.md").write_text(  # NO frontmatter: a body `---` (horizontal
            "# Schema notes\n\nSome prose.\n\n---\n\n"  # rule) must not open a fake frontmatter
            "A feedback memory looks like:\ntype: feedback\n"
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

        # A scan that COULDN'T read a memory must not look like a scan that found none. The pipe
        # fixes rc at `sort`'s, so stderr is the only channel left — it must not be suppressed.
        if os.geteuid() != 0:                        # root reads 000 anyway; the case is moot
            unread = Path(tmp) / "unreadable"
            um = unread / ".claude" / "projects" / "-some-proj" / "memory"
            um.mkdir(parents=True)
            secret = um / "unreadable.md"
            secret.write_text("---\nname: q\ntype: feedback\n---\nbody\n")
            secret.chmod(0o000)
            for shell in shells:
                p = _run_snippet(snippet, unread, shell)
                if not p.stderr.strip():
                    return False, (
                        f"[{shell}] an unreadable memory file was dropped SILENTLY — a duplicate "
                        "check must not fail in the direction of 'no duplicates' (drop 2>/dev/null)"
                    )

    return True, f"§6 scan snippet executes correctly under {', '.join(shells)} (vanilla + zero-hit + populated)"


# ---------------------------------------------------------------------------
# The pin layer (#663) — whole-region verbatim equality plus adjacency by identity.
#
# WHY WHOLE-REGION EQUALITY, not the phrase set above. Every phrase pin is a blocklist of the
# last wording someone tried. It closes the clause it names, and the clause NEXT to it is free:
# `SCAN_ROOT follows the site` stays verbatim while the sentence after it becomes "scan every
# project regardless"; `never a scan failure` stays verbatim while the sentence above it turns
# the skip into a hard stop. Both were verified green against the phrase checks. So each
# region's OWN TEXT is the pin and the comparison is TOTAL, from its heading (or its opening
# marker) to the next one, so a contradicting clause parked at the bottom is inside the pin
# rather than outside it. Whitespace is normalised: a reflow is not a change, an edit to the
# words is — and updating these constants is the deliberate act that records a contract change,
# in the same commit as the edit.
#
# WHAT ADJACENCY ADDS. "Nothing unpinned at the bottom" holds only up to the next heading, so
# one inserted `## §6-memory-addendum` moves arbitrary contradicting text outside every pin.
# reference.md is not wholly contract and SKILL.md keeps growing sections, so a whole-file
# heading-set assertion would be wrong; instead each pinned region's two immediate neighbours
# are pinned by identity.
#
# WHAT THIS DOES NOT COVER: contradicting text parked elsewhere in reference.md, under a
# non-adjacent heading. Nothing routes the engine there — the SKILL.md locator names the two
# sections, and the locator itself is pinned whole — so reaching it takes a second edit to the
# body, which the SKILL.md pins catch.
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(text.split())


def _section(pattern: re.Pattern, text: str) -> str:
    """The whole matched section, heading to next heading, normalised ("" if absent)."""
    match = pattern.search(text)
    return _normalise(match.group(0)) if match else ""


_ATX_HEADING_RE = re.compile(r"^#{1,6} ")


def _heading_lines(text: str) -> list[str]:
    """Markdown headings, skipping anything inside a fenced block.

    A bare `startswith("#")` is not enough: reference.md §6-snippet is a bash block whose
    comment lines all start with `#`, and SKILL.md §3's confirmation template is a fenced
    block whose first line is literally `## 분류 결과`. Both were read as headings and made the
    adjacency pin compare against a comment. Fence state is tracked from the start of the
    slice, and both slices this is called on begin at a heading boundary.
    """
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and _ATX_HEADING_RE.match(line):
            out.append(line)
    return out


def _neighbour_headings(pattern: re.Pattern, text: str) -> tuple[str, str]:
    """The heading immediately before and immediately after the matched section."""
    match = pattern.search(text)
    if not match:
        return ("", "")
    before = _heading_lines(text[:match.start()])
    after = _heading_lines(text[match.end():])
    return (before[-1] if before else "", after[0] if after else "")


def _paragraphs(section: str) -> list[str]:
    """A section's blank-line-delimited blocks (a bullet list counts as one)."""
    return [p for p in re.split(r"\n[ \t]*\n", section) if p.strip()]


def _head(para: str) -> str:
    """A paragraph's identity: its opening, whitespace-normalised and length-bounded.

    Not "its first physical line" — SKILL.md is hard-wrapped, so a reflow moves the first line
    break and a raw first-line identity would read a pure rewrap as an inserted neighbour.
    """
    return _normalise(para)[:80]


def _paragraph_with(section: str, marker: str) -> str:
    """The whole paragraph opening with `marker`, whitespace-normalised ("" if absent)."""
    for para in _paragraphs(section):
        if para.startswith(marker):
            return _normalise(para)
    return ""


def _paragraph_neighbours(section: str, marker: str) -> tuple[str, str]:
    """Openings of the paragraphs immediately before and after the marked one."""
    paras = _paragraphs(section)
    for i, para in enumerate(paras):
        if para.startswith(marker):
            return (_head(paras[i - 1]) if i > 0 else "",
                    _head(paras[i + 1]) if i + 1 < len(paras) else "")
    return ("", "")


# The boundary is any numbered sibling heading, not `## 4.` specifically: under a
# `(?=^## 4\.)` boundary an inserted `## 3b.` section would stay INSIDE the slice and a
# heading-adjacency pin could never see it. `## \d` and not `## ` — §3's own confirmation
# template is a fenced block whose first line is `## 분류 결과`.
_SKILL_SECTION_3_RE = re.compile(r"^## 3\.\s.*?(?=^## \d)", re.MULTILINE | re.DOTALL)
_SKILL_SECTION_6_RE = re.compile(r"^## 6\.\s.*?(?=^## \d)", re.MULTILINE | re.DOTALL)

_REF_MEMORY_SECTION_RE = re.compile(
    r"^## §6-memory-contract\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
)
_REF_SNIPPET_SECTION_RE = _SNIPPET_SECTION_RE

# The §6 locator's handle. Short enough that a rewrite of the locator still resolves to the
# paragraph — and then fails on content, which is the readable failure — rather than vanishing
# into "paragraph not found".
_MEMORY_LOCATOR_MARKER = "**The Duplicate scan also covers native auto-memory**"

_SKILL_SECTION_3 = _normalise("""\
## 3. The three landfill sites (+ tier absorbed, 1-click UX)

There are exactly **three** native places a rule lands (the small count keeps classification
reliable and the engine portable):

- **reminder** (CLAUDE.md or `~/.claude/rules`) — an always-read rule, **SOFT**: one prose line
  appended to the layer's channel, **layer-determined** (below).
- **hook** — deterministic auto-enforcement, **HARD**: a guard script + a `hooks` registration
  entry, working tree only, never self-activated. **Two forms** (#609), by *when* the violation
  becomes visible: **blocking** = PreToolUse + `hookSpecificOutput.permissionDecision: "deny"`;
  **recovery** = PostToolUse + `exit 2`, stderr back to Claude — reports only
  (PostToolUse carries neither `permissionDecision` nor `updatedInput`).
- **skill** — an invocable procedure: `~/.claude/skills/<name>/SKILL.md` (patch > extend > new).

**Tier folds into the site, so the user never picks an axis** (**HARD ⇒ hook, SOFT ⇒
reminder**); the hook's *form* folds the same way, never a second axis — **HARD means
"deterministically enforced", not "a guard blocks"** (#609), since recovery auto-fires like
blocking but cannot undo. The scope/channel question is the site choice itself.

**Layer → tier default (engine inference):** *judgment* and *expression* are **always SOFT**
(not deterministically guardable); a *work-rule* is **HARD (→ hook) iff its violation is
deterministically detectable**, else SOFT — detectable **before** the act → blocking, only
**after** (from what the act leaves behind) → recovery. Examples: [reference.md](reference.md)
§3-tier.

**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):** *judgment /
expression* (stance·voice) → the top-level **`~/.claude/CLAUDE.md`** persona block; *work-rule*
→ the machine **work-rule catalogue `~/.claude/rules`** *if it exists*, **otherwise fall back to
`~/.claude/CLAUDE.md`**. It routes by the layer §2 already computed — no new site, no new axis.
The fallback is **non-negotiable: never hardcode the machine's `rules/` structure**: detect it
(`[ -d "$HOME/.claude/rules" ]`) and degrade to CLAUDE.md where it is absent. Per-site
conflict target, and why the fallback is non-negotiable: [reference.md](reference.md) §3-sites.

**Thin pointer + backing detail (catalogue channel):** machine-level reminders ride in *every*
session, so the catalogue holds the detail and `~/.claude/CLAUDE.md` gets at most a one-line
pointer — none if it already points at the catalogue, never full rule prose. And **everything
under `~/.claude/rules/` is loaded, not just its index**, so write the new detail file where the
index's own links point, outside that directory; never add a second `.md` there. (Measured leak:
[reference.md](reference.md) §3)

**1-click confirmation**: present the *decision*, not the grid — where it lands, the exact
text/diff, one line of why-here — then one confirmation:

```
## 분류 결과
- 규칙: <one-line summary>
- 들어갈 곳: <CLAUDE.md | hook | skill> — <HARD라 자동강제 / SOFT라 리마인드 / 절차라 호출형>
- 추가/변경될 내용: <exact prose/guard/skill stub, or the entry's before → after on an Edit>
- 충돌: <none | sibling | edits an existing entry (before→after) | contradicts an existing rule (explain)>
- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>
- 은퇴: <none | Pn 흡수 — 같은 쓰기에서 은퇴 | Pn 미발동 — 삭제 / 조건 좁히기?>
- memory 중복: <none | memory에도 있어요: <path...> — 매립 후 그 항목은 지울게요 (§6)>
```

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" — with two exceptions. 필요성 not
통과, and then the gate's recommendation is the first option and the question carries **that**
recommendation, never a generic refusal: 기존 항목으로 충분 asks about folding it into that
entry, 안 넣는 게 나음 asks whether to land it at all. And 은퇴 = 미발동, a three-way pick rather
than a yes/no (#609). Wordings: [reference.md](reference.md) §3-gate-question. **Never write without confirmation.** If any axis
cannot be settled, hold the classification and report what is ambiguous instead of placing it
arbitrarily ("don't know" beats a confident-wrong placement).
""")

_SKILL_MEMORY_LOCATOR = _normalise("""\
**The Duplicate scan also covers native auto-memory** (`~/.claude/projects/<proj>/memory/*.md`
`feedback` entries), in two steps whose conflation is a data-loss bug. **Its canonical, binding
text is [reference.md](reference.md) §6-memory-contract: Read that section and apply it as
written, then read §6-snippet and run the command it ships — this paragraph is a locator, not
the contract.** Memory is an input queue that empties into a §3 site — **never a fourth site**,
never a write destination. Why two steps: [reference.md](reference.md) §6-memory.
""")

_REF_MEMORY_SECTION = _normalise("""\
## §6-memory-contract — the native-memory duplicate scan, CANONICAL text (#663)

**This section is the contract, not background.** SKILL.md §6 points here and carries a locator
paragraph only; what follows is the text the engine applies, and `_REF_MEMORY_SECTION` in
`feedback-loop/scripts/test/test-add-policy-routing.py` pins it verbatim — editing it is a
deliberate contract change, made in the same commit as that constant. Nothing else belongs in
this section: the slice runs to the next heading, so a clause parked below the block breaks the
pin (by design), and the two neighbouring headings are pinned by identity so a new sibling
cannot park one just outside it either. Rationale lives in §6-memory, immediately after.

**The Duplicate scan also covers native auto-memory** — `~/.claude/projects/<proj>/memory/*.md`
stores `feedback` entries, the same kind of thing this engine lands, cross-checked nowhere
else. Scan **both**.

**Two steps — conflating them is a data-loss bug.** Step 1 only **lists candidate files**; Step
2 decides a *Duplicate* by **reading each candidate and comparing its content to the rule being
landed**. Only a content match is a hit — a file that merely has `type: feedback` is not a
duplicate and is never touched.

**Step 1 — list candidates** (read-only). `SCAN_ROOT` follows the site: a machine-global site
is duplicated by a memory in **any** project; a **project-scoped** `CLAUDE.md` only by **that
project's own** — another project's memory is neither a duplicate nor yours to delete.

**Read §6-snippet now and run the command it ships, as written.** Every choice there is
load-bearing, and a reconstructed command fails in the one direction that matters: reporting
"no duplicates" when the scan never ran.

**Memory is an input, never a destination.** A `feedback` memory is a promotion queue that
empties into one of the three sites of SKILL.md §3 — **not a fourth site**; a rule is never
*written* to memory.

**Step 2 — read each candidate and judge.** Most are unrelated; move on.

- **Vanilla machine → silently skip.** No `~/.claude/projects` (or no `memory/` inside it):
  skip the memory scan and proceed, as §5 treats a missing `~/.claude/skills` — nothing to
  conflict with, never a scan failure; likewise zero candidates.
- **A scan that ERRORED is not a scan that found nothing.** A dead `awk` or an unreadable file
  shows only on **stderr**; anything there leaves the scan **inconclusive** — say so in the §3
  confirmation ("memory 스캔 실패 — 중복 여부 확인 못 했어요") instead of reporting `none`.
- **On a content-match hit → surface it in the §3 confirmation** ("memory에도 있어요 — 매립 후
  memory 항목은 지울게요"), and after the write remove that memory file **and its
  `MEMORY.md` index line — the line whose markdown link target is that file's basename** (never
  the title; those repeat). Same confirmation, no second prompt. Use `trash-put`; if
  unavailable, leave the file and report it — **never force-delete, never `rm`**.
""")

_REF_SNIPPET_SECTION = _normalise("""\
## §6-snippet — the runnable scan command, and why it is written this way

**This file ships the command; §6-memory-contract keeps the decision it serves** (scan memory
too, a hit is a CONTENT match, an errored scan is inconclusive) and points here — #469 moved the
executable text out so the decision fits the 5,000-token compaction window. Run it as written:
the reasoning below is what each choice buys, including the `n starts at 9` guard, zsh NOMATCH,
and why `2>/dev/null` is banned.

```bash
# Machine-global site -> all projects. Project-scoped CLAUDE.md -> that project's dir only:
#   SCAN_ROOT="$HOME/.claude/projects/<current-project-dir>"
SCAN_ROOT="$HOME/.claude/projects"
# `find`, not a glob: `~/.claude/projects` exists on any machine that ever ran Claude Code, but
# `memory/` only appears once auto-memory has written something — an unmatched `*/memory/*.md`
# glob aborts the command (zsh NOMATCH) instead of scanning nothing.
# `awk`, not `grep`: the type must be read from the FRONTMATTER (n==1 = between the `---`
# fences), or `type: feedback` quoted in a note's body matches. Line 1 must BE the opening
# `---`, else n starts at 9 and never reaches 1 — otherwise a file with no frontmatter at all
# would let its first body `---` (a horizontal rule) open a fake frontmatter. Trailing `$` on
# the value, or `type: feedback-loop` matches. `|| true`: a missing SCAN_ROOT is not a failure.
# NO `2>/dev/null`: a dead awk or an unreadable file must be VISIBLE. The pipe already fixes
# the exit code at `sort`'s, so stderr is the only channel left that can say "this scan is
# incomplete" — and a duplicate check that fails silently reports "no duplicates", which is
# the wrong direction to fail. If anything lands on stderr, treat the scan as INCONCLUSIVE and
# say so; do not report "memory 중복: none".
[ -d "$SCAN_ROOT" ] && find "$SCAN_ROOT" -path '*/memory/*.md' -not -name 'MEMORY.md' -exec awk '
  FNR==1 { n = ($0 ~ /^---[[:space:]]*$/) ? 0 : 9 }
  /^---[[:space:]]*$/ { n++ }
  n==1 && /^[[:space:]]*type:[[:space:]]*feedback[[:space:]]*$/ { print FILENAME }
' {} + | sort -u || true
```
""")

# Each pinned region's two immediate neighbours, by identity.
_SKILL_SECTION_3_NEIGHBOURS = (
    "## 2. Classification grid (default taxonomy — editable, replaceable)",
    "## 4. User-shell receiver — the destination outside the three sites",
)
_MEMORY_LOCATOR_NEIGHBOURS = (
    "- **Duplicate**: if the site already states the same rule, strengthen that entry",
    "**Necessity gate — runs here, after the conflict check and before the §3 confirm",
)
_REF_NEIGHBOURS = {
    "§6-memory-contract": (
        _REF_MEMORY_SECTION_RE,
        ("## §6-new-site — why a read error is not a missing file",
         "## §6-memory — why the memory scan is two steps"),
    ),
    "§6-snippet": (
        _REF_SNIPPET_SECTION_RE,
        ("## §6-memory — why the memory scan is two steps",
         "## §6-gate-contract — the necessity gate, CANONICAL text (#663)"),
    ),
}


def check_skill_section_3_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """SKILL.md § 3. The three landfill sites matches its pinned text, WHOLE and VERBATIM."""
    got = _section(_SKILL_SECTION_3_RE, skill)
    if not got:
        return False, "SKILL.md `## 3.` section boundary not found (header drift?)"
    if got != _SKILL_SECTION_3:
        return False, (
            "SKILL.md §3 no longer matches its pinned text — the SOFT-channel routing, the "
            "vanilla fallback, the no-hardcode clause, the thin-pointer rule or something "
            "beside them changed. If that is intended, update _SKILL_SECTION_3 in this file "
            "in the same commit"
        )
    return True, "SKILL.md §3 (loaded body: channel routing + fallback) matches VERBATIM"


def check_skill_section_3_neighbours(skill: str, ref: str) -> tuple[bool, str]:
    """No sibling heading inserted next to §3, which would park text just outside the pin."""
    got = _neighbour_headings(_SKILL_SECTION_3_RE, skill)
    if got != _SKILL_SECTION_3_NEIGHBOURS:
        return False, (
            "SKILL.md §3's neighbouring headings changed — an inserted sibling section parks "
            f"its text outside the §3 pin. expected {_SKILL_SECTION_3_NEIGHBOURS}, got {got}"
        )
    return True, "SKILL.md §3 still sits between `## 2.` and `## 4.`"


def check_skill_memory_locator_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """The always-loaded §6 memory locator paragraph matches its pinned text, WHOLE.

    The loaded body outranks an on-demand doc at runtime, so a locator reading "scan memory if
    convenient" defeats a perfectly pinned §6-memory-contract. It is pinned as hard as the
    canonical section it points at.
    """
    section = _SKILL_SECTION_6_RE.search(skill)
    if section is None:
        return False, "SKILL.md `## 6.` section boundary not found (header drift?)"
    got = _paragraph_with(section.group(0), _MEMORY_LOCATOR_MARKER)
    if not got:
        return False, (
            "SKILL.md §6 has no memory-scan locator paragraph — the always-loaded body no "
            "longer routes the engine to §6-memory-contract at all"
        )
    if got != _SKILL_MEMORY_LOCATOR:
        return False, (
            "SKILL.md §6's memory-scan locator no longer matches its pinned text — a clause "
            "was added, removed or reworded. If that is intended, update "
            "_SKILL_MEMORY_LOCATOR in this file in the same commit"
        )
    return True, "SKILL.md §6's memory-scan locator (loaded body) matches VERBATIM"


def check_skill_memory_locator_neighbours(skill: str, ref: str) -> tuple[bool, str]:
    """Nothing new may be parked immediately beside the locator paragraph."""
    section = _SKILL_SECTION_6_RE.search(skill)
    if section is None:
        return False, "SKILL.md `## 6.` section boundary not found (header drift?)"
    got = _paragraph_neighbours(section.group(0), _MEMORY_LOCATOR_MARKER)
    if got != _MEMORY_LOCATOR_NEIGHBOURS:
        return False, (
            "the §6 paragraphs around the memory-scan locator changed — a paragraph inserted "
            f"beside it sits outside the pin. expected {_MEMORY_LOCATOR_NEIGHBOURS}, got {got}"
        )
    return True, "SKILL.md §6's memory locator still sits between its two known paragraphs"


def check_ref_memory_contract_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """reference.md § §6-memory-contract matches its pinned canonical text, WHOLE."""
    got = _section(_REF_MEMORY_SECTION_RE, ref)
    if not got:
        return False, "reference.md `## §6-memory-contract` section not found (header drift?)"
    if got != _REF_MEMORY_SECTION:
        return False, (
            "reference.md §6-memory-contract no longer matches its pinned contract text — a "
            "clause was added, removed or reworded anywhere in it (including below the last "
            "bullet, inside the same section). If that is intended, update _REF_MEMORY_SECTION "
            "in this file in the same commit"
        )
    return True, "reference.md §6-memory-contract matches its pinned contract text VERBATIM"


def check_ref_snippet_section_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """reference.md § §6-snippet matches its pinned text, WHOLE — comments included.

    The snippet's surrounding comments are not decoration: `NO 2>/dev/null`, the `n starts at
    9` guard and the zsh-NOMATCH note are the reasons the command is written the way it is, and
    an executed-only check cannot tell a stripped rationale from an intact one.
    """
    got = _section(_REF_SNIPPET_SECTION_RE, ref)
    if not got:
        return False, "reference.md `## §6-snippet` section not found (header drift?)"
    if got != _REF_SNIPPET_SECTION:
        return False, (
            "reference.md §6-snippet no longer matches its pinned text — the command or the "
            "reasoning around it changed. If that is intended, update _REF_SNIPPET_SECTION in "
            "this file in the same commit (and re-check that the execution test still passes)"
        )
    return True, "reference.md §6-snippet matches its pinned text VERBATIM"


def check_ref_section_neighbours(skill: str, ref: str) -> tuple[bool, str]:
    """Each pinned reference section still sits between its two known headings."""
    bad = []
    for label, (pattern, expected) in _REF_NEIGHBOURS.items():
        got = _neighbour_headings(pattern, ref)
        if got != expected:
            bad.append(f"{label}: expected {expected}, got {got}")
    if bad:
        return False, (
            "a pinned reference.md section's neighbouring headings changed — an inserted "
            "sibling parks its text outside the pin. " + "; ".join(bad)
        )
    return True, (
        "both pinned reference.md sections still sit between their known headings "
        "(an inserted sibling would park text outside the pin)"
    )


# Which source each phrase check reads. Two sources on purpose (#469/#663): passing one
# concatenated blob would let a SKILL.md claim be satisfied by the reference — the file
# compaction does *not* re-attach, which is the whole thing being guarded.
_SKILL_CHECKS = [
    check_stance_voice_to_claude_md,
    check_workrule_to_rules,
    check_vanilla_fallback,
    check_no_hardcode,
    check_thin_pointer,
    check_not_fourth_site,
    check_scan_command_pointer,
]
_REF_CHECKS = [
    check_memory_duplicate_scan,
    check_memory_candidate_vs_duplicate,
    check_memory_delete_safety,
    check_memory_scan_fails_loud,
    check_memory_vanilla_skip,
    check_memory_snippet_runs,
]
_PIN_CHECKS = [
    check_skill_section_3_verbatim,
    check_skill_section_3_neighbours,
    check_skill_memory_locator_verbatim,
    check_skill_memory_locator_neighbours,
    check_ref_memory_contract_verbatim,
    check_ref_snippet_section_verbatim,
    check_ref_section_neighbours,
]


def run_checks(text: str, reference: str) -> tuple[int, int]:
    """`text` is SKILL.md, `reference` is reference.md. Never concatenated — see _SKILL_CHECKS."""
    passed = failed = 0
    results = (
        [check(text) for check in _SKILL_CHECKS]
        + [check(reference) for check in _REF_CHECKS]
        + [check(text, reference) for check in _PIN_CHECKS]
    )
    for ok, msg in results:
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test (in-memory fixtures) for the phrase layer
# ---------------------------------------------------------------------------

_PASSING_SKILL = """\
**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):**
- judgment / expression (stance·voice) -> the top-level ~/.claude/CLAUDE.md persona block.
- work-rule (how you do the work) -> the machine work-rule catalogue ~/.claude/rules
  if it exists; otherwise fall back to ~/.claude/CLAUDE.md.

The fallback is non-negotiable: never hardcode the machine's rules/ structure. Detect it
([ -d "$HOME/.claude/rules" ]) and degrade to CLAUDE.md on a vanilla machine where
~/.claude/rules is absent.

Thin pointer + backing detail: put the detail in the catalogue and keep ~/.claude/CLAUDE.md
to at most a one-line pointer / thin pointer.

**The Duplicate scan also covers native auto-memory** (~/.claude/projects/<proj>/memory/*.md
`feedback` entries), in two steps whose conflation is a data-loss bug. Its canonical, binding
text is reference.md §6-memory-contract — read that section and apply it as written, then read
§6-snippet and run the command it ships; this paragraph is a locator, not the contract.
"""

_PASSING_REF = """\
## §6-memory-contract — the native-memory duplicate scan, CANONICAL text

The Duplicate scan also covers native auto-memory: scan the `feedback` entries under
~/.claude/projects/<proj>/memory/*.md. Step 1: list candidates. Step 2: read each and compare
it to the rule being landed — only a content match is a duplicate; a file that merely has
`type: feedback` is not a duplicate and is never touched. SCAN_ROOT follows the site: a
machine-global site scans all projects; for a project-scoped CLAUDE.md, another project's
memory is neither a duplicate nor yours to delete. Vanilla machine with no such directory ->
skip the memory scan silently; a missing directory is nothing to conflict with, never a scan
failure. But an errored scan is not an empty one: anything on stderr means the scan is
INCONCLUSIVE, never `none` — "memory 스캔 실패" in the confirmation. On a
hit, surface it in the 1-click confirmation ("매립 후 memory 항목은 지울게요") and delete the
duplicate memory file after the landfill write — its MEMORY.md index line is the one whose
markdown link target is that file's basename. Use trash-put; never force-delete, never `rm`.
Memory is an input, never a destination: an input queue, not a fourth site.

## §6-snippet — the runnable scan command

```bash
SCAN_ROOT="$HOME/.claude/projects"
[ -d "$SCAN_ROOT" ] && find "$SCAN_ROOT" -path '*/memory/*.md' -not -name 'MEMORY.md' -exec awk '
  FNR==1 { n = ($0 ~ /^---[[:space:]]*$/) ? 0 : 9 }
  /^---[[:space:]]*$/ { n++ }
  n==1 && /^[[:space:]]*type:[[:space:]]*feedback[[:space:]]*$/ { print FILENAME }
' {} + | sort -u || true
```
"""

# Regression of the exact bug G28 fixes: SOFT always -> CLAUDE.md, no rules routing,
# no fallback, no no-hardcode clause.
_FAILING_SKILL = """\
Tier folds into the site: HARD => hook, SOFT => CLAUDE.md. A SOFT rule is always a
CLAUDE.md reminder appended as one prose line.
"""
_FAILING_REF = """\
## §6-memory — why the memory scan is two steps

Nothing here states a memory-scan contract, and no runnable command ships with it.
"""


# ---------------------------------------------------------------------------
# #663 pin mutations, built by `.replace()` off the REAL files — never typed by hand, because
# a hand-copied base drifts silently and its expect-FAIL case then tests nothing. Every fixture
# sits in the import-time guard loop below: a `.replace()` whose target has moved yields a copy
# of its base, and an expect-FAIL case on an unmodified copy always passes.
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL_PATH.read_text(encoding="utf-8")
_CLEAN_REF = _REFERENCE_PATH.read_text(encoding="utf-8")

# THE ESCAPE HATCH, reference side: contradicting text parked in a NEW sibling section placed
# immediately after a pinned one. Every whole-section pin still matches — the slice ends at the
# new heading — and every phrase check still passes. Only the adjacency pin sees it.
_REF_ADDENDUM_INSERTED = _CLEAN_REF.replace(
    "\n## §6-memory — why the memory scan is two steps",
    "\n## §6-memory-addendum\n\nWhen the scan is inconvenient, report `memory 중복: none` and\n"
    "move on; deleting every `type: feedback` file it lists is fine.\n\n"
    "## §6-memory — why the memory scan is two steps",
)

# The same trick on the SKILL.md side: a `## 6b.` sibling carrying the opposite instruction.
_SKILL_SIBLING_SECTION = _CLEAN_SKILL.replace(
    "\n## 4. User-shell receiver",
    "\n## 3b. Reminder channel — addendum\n\nIn practice, put every SOFT rule in\n"
    "`~/.claude/rules` and assume the directory exists.\n\n"
    "## 4. User-shell receiver",
)

# And one level down: a contradicting PARAGRAPH parked inside §6, right after the locator.
_SKILL_ADJACENT_PARAGRAPH = _CLEAN_SKILL.replace(
    "\n**Necessity gate — runs here",
    "\nIn practice the memory scan is optional — skip it when the site's own content already\n"
    "answered the Duplicate question.\n\n**Necessity gate — runs here",
)

# Region rewrites the phrase checks cannot see, because each leaves every pinned phrase intact
# and edits the sentence NEXT to it.
_REF_SCOPE_WIDENED = _CLEAN_REF.replace(
    "a **project-scoped** `CLAUDE.md` only by **that\nproject's own**",
    "and a **project-scoped** `CLAUDE.md` by every project's",
)
_REF_SKIP_BECOMES_STOP = _CLEAN_REF.replace(
    "skip the memory scan and proceed, as §5 treats a missing `~/.claude/skills`",
    "skip the memory scan and STOP the landing, as no site can be conflict-checked without it",
)
_SKILL_FALLBACK_INVERTED = _CLEAN_SKILL.replace(
    "**otherwise fall back to\n`~/.claude/CLAUDE.md`**",
    "**otherwise create it**",
)
# The `2>/dev/null` ban's reasoning stripped out of §6-snippet while the command still runs
# correctly — the execution test cannot tell the difference, the section pin can.
_REF_SNIPPET_RATIONALE_STRIPPED = _CLEAN_REF.replace(
    "# NO `2>/dev/null`: a dead awk or an unreadable file must be VISIBLE. The pipe already fixes\n",
    "",
)
# The locator decayed into a bare citation: the contract still exists, nothing routes to it.
_SKILL_LOCATOR_DECAYED = _CLEAN_SKILL.replace(
    "**Its canonical, binding\ntext is [reference.md](reference.md) §6-memory-contract: Read that section and apply it as\nwritten, then read §6-snippet and run the command it ships — this paragraph is a locator, not\nthe contract.**",
    "For background, see [reference.md](reference.md) §6-memory-contract and §6-snippet.",
)

# Realistic reflows: prose rewrapped onto one line, headings, bullet lists and fenced blocks
# left alone. Whitespace is not the contract, so both must stay green.
def _reflow(text: str) -> str:
    return "\n\n".join(
        block if block.startswith("#") or block.startswith("-") or "```" in block
        else " ".join(block.split())
        for block in text.split("\n\n")
    )


_SKILL_REFLOWED = _reflow(_CLEAN_SKILL)
_REF_REFLOWED = _reflow(_CLEAN_REF)

for _name, _fixture, _base in (
    ("_REF_ADDENDUM_INSERTED", _REF_ADDENDUM_INSERTED, _CLEAN_REF),
    ("_SKILL_SIBLING_SECTION", _SKILL_SIBLING_SECTION, _CLEAN_SKILL),
    ("_SKILL_ADJACENT_PARAGRAPH", _SKILL_ADJACENT_PARAGRAPH, _CLEAN_SKILL),
    ("_REF_SCOPE_WIDENED", _REF_SCOPE_WIDENED, _CLEAN_REF),
    ("_REF_SKIP_BECOMES_STOP", _REF_SKIP_BECOMES_STOP, _CLEAN_REF),
    ("_SKILL_FALLBACK_INVERTED", _SKILL_FALLBACK_INVERTED, _CLEAN_SKILL),
    ("_REF_SNIPPET_RATIONALE_STRIPPED", _REF_SNIPPET_RATIONALE_STRIPPED, _CLEAN_REF),
    ("_SKILL_LOCATOR_DECAYED", _SKILL_LOCATOR_DECAYED, _CLEAN_SKILL),
    ("_SKILL_REFLOWED", _SKILL_REFLOWED, _CLEAN_SKILL),
    ("_REF_REFLOWED", _REF_REFLOWED, _CLEAN_REF),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

_CANONICAL_CASES: list[tuple[str, str, str, bool]] = [
    ("the real SKILL.md + reference.md pass every pin", _CLEAN_SKILL, _CLEAN_REF, True),
    ("a new `## §6-memory-addendum` sibling parks contradicting text beside the pinned "
     "section -> FAIL", _CLEAN_SKILL, _REF_ADDENDUM_INSERTED, False),
    ("a new `## 3b.` sibling parks contradicting text beside §3 -> FAIL",
     _SKILL_SIBLING_SECTION, _CLEAN_REF, False),
    ("a contradicting paragraph parked right after the §6 locator -> FAIL",
     _SKILL_ADJACENT_PARAGRAPH, _CLEAN_REF, False),
    ("the scan scope widened past the project boundary -> FAIL",
     _CLEAN_SKILL, _REF_SCOPE_WIDENED, False),
    ("the vanilla silent-skip turned into a hard stop -> FAIL",
     _CLEAN_SKILL, _REF_SKIP_BECOMES_STOP, False),
    ("the catalogue fallback inverted into creating the directory -> FAIL",
     _SKILL_FALLBACK_INVERTED, _CLEAN_REF, False),
    ("§6-snippet's `2>/dev/null` ban rationale stripped -> FAIL "
     "(the command still executes correctly, so only the pin sees it)",
     _CLEAN_SKILL, _REF_SNIPPET_RATIONALE_STRIPPED, False),
    # The one expect-FAIL case the phrase layer ALSO catches (`check_scan_command_pointer`
    # reads the seam directly), so it is exempted from the phrase-blind assertion below.
    ("the §6 locator decayed into a bare citation -> FAIL",
     _SKILL_LOCATOR_DECAYED, _CLEAN_REF, False),
    ("both files reflowed still pass (whitespace is not the contract)",
     _SKILL_REFLOWED, _REF_REFLOWED, True),
]


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _SKILL_CHECKS:
        ok, _ = check(_PASSING_SKILL)
        cases.append((f"passing (skill): {check.__name__}", ok))
    for check in _REF_CHECKS:
        ok, _ = check(_PASSING_REF)
        cases.append((f"passing (ref): {check.__name__}", ok))

    # On the pre-G28/pre-#377 fixtures, every rules/fallback/hardcode/memory claim is absent.
    for check in _SKILL_CHECKS:
        ok, _ = check(_FAILING_SKILL)
        cases.append((f"failing (skill): {check.__name__} (expect FAIL)", not ok))
    for check in _REF_CHECKS:
        ok, _ = check(_FAILING_REF)
        cases.append((f"failing (ref): {check.__name__} (expect FAIL)", not ok))

    # The two-source WIRING (#469/#663), not merely its result. A SKILL.md source missing its
    # §6-memory-contract pointer, paired with a reference that names the section everywhere:
    # correct wiring reds one phrase check, while a run_checks that concatenated its two
    # arguments would let the reference answer for the missing prose and report clean.
    skill_missing = _PASSING_SKILL.replace("§6-memory-contract", "the reference")
    assert skill_missing != _PASSING_SKILL, "fixture no-opped: the §6-memory-contract pointer moved"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        wiring = [check(skill_missing) for check in _SKILL_CHECKS]
    cases.append((
        "two-source wiring: a SKILL.md claim cannot be satisfied from the reference source",
        sum(1 for ok, _ in wiring if not ok) == 1,
    ))

    # The other half of the seam: rename the heading in the reference and leave the block, and
    # SKILL.md's pointer now names a section that does not exist. The whole-document fallback
    # this extractor used to carry found the block anyway and stayed green, which is why the
    # fallback is gone — this case is what keeps it from coming back.
    orphaned = _PASSING_REF.replace("## §6-snippet", "## §6-scan")
    assert orphaned != _PASSING_REF, "fixture no-opped: the §6-snippet heading moved"
    ok, _ = check_memory_snippet_runs(orphaned)
    cases.append(("orphaned §6-snippet heading — block present, pointer dangling (expect FAIL)", not ok))

    # #663: the whole-region pins + adjacency, against the real files and mutations of them.
    for desc, skill_text, ref_text, expect_pass in _CANONICAL_CASES:
        got = all(ok for ok, _ in (check(skill_text, ref_text) for check in _PIN_CHECKS))
        cases.append((f"pin: {desc}", got == expect_pass))
        if not expect_pass and "decayed into a bare citation" not in desc:
            # The point of the pin layer: the phrase checks alone let each of these through.
            phrase_ok = (
                all(ok for ok, _ in (check(skill_text) for check in _SKILL_CHECKS))
                and all(ok for ok, _ in (check(ref_text) for check in _REF_CHECKS))
            )
            cases.append((f"pin: {desc} — phrase checks alone stay green", phrase_ok))

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

    print(f"Checking: {_SKILL_PATH}\n          {_REFERENCE_PATH} (memory contract + scan command)\n")
    try:
        text = _load_skill()
        reference = _load_reference()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(text, reference)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} add-policy-routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
