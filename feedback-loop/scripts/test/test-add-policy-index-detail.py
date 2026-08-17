#!/usr/bin/env python3
"""Regression test: add-policy §6 respects an existing index+detail split.

PR #340. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill,
so this is a static-content check — it does not execute LLM logic. It pins the
§6 clause added by #340: when the chosen landfill site already uses a thin
index + per-entry detail-file shape (e.g. a catalogue README.md -> policies/Pn.md),
add-policy must match that shape (one index row + a linked detail file) instead of
appending a new inline block, and must never invent this split on a site that
doesn't already use it. Guards against a future SKILL.md edit silently dropping
either half of that contract.

Scope (#440): the *instruction* is what must stay in §6. Naming the shape
elsewhere is expected — §3 resolves the index's link to place an entry, §8
verifies the written split — so those mentions are not leaks. And because
SKILL.md is hard-wrapped, claims are matched by phrase across whitespace, never
as contiguous substrings; a reflow must not read as a deletion.

#663 adds the pin layer the phrase checks above cannot carry. A phrase check
closes only the clause it names and leaves every neighbouring region free, so the
paragraph that carries this instruction is now compared WHOLE and VERBATIM
(whitespace-normalised), and its adjacency is pinned twice over:

- the paragraph's neighbouring §6 paragraphs are pinned by the identity of their
  first lines, so a contradicting paragraph slipped in beside it reds;
- §6 itself is pinned between `## 5.` and `## 7.`, so a new sibling heading
  (`## 6b. …`) — which would park arbitrary text just outside the §6 slice while
  every phrase check stayed green — reds too.

Neither is a whole-file heading-set assertion: SKILL.md is free to gain sections
elsewhere. Only the two headings around §6, and the two paragraphs around the
pinned one, are fixed.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-index-detail.py
    python3 feedback-loop/scripts/test/test-add-policy-index-detail.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "feedback-loop" / "skills" / "add-policy" / "SKILL.md"


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


# The boundary is ANY numbered sibling heading, not `## 7.` specifically (#663). Under the old
# `(?=^## 7\.)` boundary an inserted `## 6b.` section stayed INSIDE the slice, so a phrase check
# went on passing while contradicting text sat under a heading of its own. Ending at the next
# `## <digit>` makes that insertion visible to `check_section_6_neighbours` below, which pins the
# heading that must follow §6 by identity.
_SECTION_6_RE = re.compile(r"^## 6\.\s.*?(?=^## \d)", re.MULTILINE | re.DOTALL)


def _section_6_span(text: str) -> tuple[int, int] | None:
    """Where §6 starts and ends, or None if the header pair is not found."""
    match = _SECTION_6_RE.search(text)
    return match.span() if match else None


def _section_6(text: str) -> str:
    """Slice out just §6 (between the '## 6.' and '## 7.' headers)."""
    span = _section_6_span(text)
    return text[span[0]:span[1]] if span else ""


# ---------------------------------------------------------------------------
# Checks — each returns (ok, message). Phrase-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
#
# Every phrase is matched through `_states()`, which treats any run of
# whitespace as a word gap. A plain `in` test cannot do that job: SKILL.md is
# hard-wrapped, so reflowing a paragraph moves a line break into the middle of
# a phrase and the claim reads as deleted while it is still right there. That
# is what happened to `never invent this split` after 90a20d2.
# ---------------------------------------------------------------------------

def _states(text: str, phrase: str) -> bool:
    """True if `text` states `phrase`, ignoring how the prose happens to wrap.

    `\\s+` between words also enforces a boundary at every internal gap, so the
    only unguarded edges are the phrase's outer two — without `\\b` there,
    "index row" matched "re**index row**" and "detail file" matched
    "a **detail file**name". Every phrase checked here starts and ends with a
    word character, which is what makes `\\b` the right anchor for both edges.
    """
    core = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.search(rf"\b{core}\b", text, re.IGNORECASE) is not None


# The two phrases that carry the *instruction*. These are what must not float
# out of §6 — unlike the shape's mere name, which §3 (placement) and §8
# (post-write verification) both legitimately mention.
_INSTRUCTION_PHRASES = ("match that shape", "never invent this split")


def check_index_detail_shape_named(text: str) -> tuple[bool, str]:
    """The index+detail split shape must be named."""
    section = _section_6(text)
    if not _states(section, "index+detail split") and not _states(section, "index + detail split"):
        return False, "index+detail split shape not named in §6"
    return True, "index+detail split shape named"


def check_match_shape_instruction(text: str) -> tuple[bool, str]:
    """Must instruct matching the shape: an index row + a linked detail file, not a new inline block."""
    section = _section_6(text)
    if not _states(section, "match that shape"):
        return False, "'match that shape' instruction missing"
    if not _states(section, "index row") or not _states(section, "detail file"):
        return False, "index row + detail file pairing not described"
    if not _states(section, "inline block"):
        return False, "the inline-block alternative (what NOT to do) not named"
    return True, "match-shape instruction (index row + detail file, not inline block) present"


def check_never_invent_guard(text: str) -> tuple[bool, str]:
    """Must guard against inventing this split on a site that doesn't already use it."""
    if not _states(_section_6(text), "never invent this split"):
        return False, "'never invent this split' guard missing"
    return True, "never-invent-this-split guard present"


def check_scoped_to_section_6(text: str) -> tuple[bool, str]:
    """The §6 *instruction* must not float elsewhere (e.g. into §7's output contract).

    Naming the shape outside §6 is not a leak: §3 resolves the index's link to
    decide placement, and §8 verifies the written split (link resolves, no new
    `.md` in the loaded directory). Both are halves of the same contract, so
    only the instruction phrases are scoped here.
    """
    span = _section_6_span(text)
    if span is None or not text[span[0]:span[1]].strip():
        return False, "§6 section boundary not found (header drift?)"
    # Excised by span, not by `str.replace(section, ...)`: replace is
    # content-based, so a block that happened to repeat §6's text verbatim
    # elsewhere would be cut too, quietly changing what "outside §6" means.
    #
    # The sentinel is non-whitespace on purpose — removing §6 butts §5's tail
    # against §7's head, and `_states` spans whitespace, so a section ending in
    # "match that" before one starting with "shape" would read as a leak that
    # isn't there.
    outside_6 = text[:span[0]] + "\n<<§6 excised>>\n" + text[span[1]:]
    for phrase in _INSTRUCTION_PHRASES:
        if _states(outside_6, phrase):
            return False, f"§6 instruction ('{phrase}') leaked outside §6"
    return True, "§6 instruction correctly scoped to §6"


# ---------------------------------------------------------------------------
# Whole-paragraph pin + adjacency (#663)
#
# WHY WHOLE-PARAGRAPH EQUALITY, not the phrase set above. Every phrase pin is a blocklist of the
# last wording someone tried: it closes the clause it names and leaves the next neighbour free.
# `match that shape` and `never invent this split` can both stay verbatim while the sentence
# between them is rewritten into "…, but on a catalogue site add a new inline block instead" and
# the whole suite stays green. So the paragraph's OWN TEXT is the pin and the comparison is
# TOTAL. Whitespace is normalised — a reflow is not a change, an edit to the words is, and
# updating this constant is the deliberate act that records the change, in the same commit.
#
# The phrase checks above are kept for DIAGNOSIS, not coverage: each names one invariant, so a
# failure says which half died instead of only "the paragraph changed".
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(text.split())


def _paragraphs(section: str) -> list[str]:
    """§6's blank-line-delimited blocks. The bullet list is one block (bullets carry no blank
    line between them), which is exactly the granularity the adjacency pin wants."""
    return [p for p in re.split(r"\n[ \t]*\n", section) if p.strip()]


def _paragraph_with(section: str, marker: str) -> str:
    """The whole paragraph opening with `marker`, whitespace-normalised ("" if absent)."""
    for para in _paragraphs(section):
        if para.startswith(marker):
            return _normalise(para)
    return ""


def _head(para: str) -> str:
    """A paragraph's identity: its opening, whitespace-normalised.

    Normalised and length-bounded rather than "its first physical line" — the file is
    hard-wrapped, so a reflow moves the first line break and a raw first-line identity would
    read a pure rewrap as an inserted neighbour.
    """
    return _normalise(para)[:80]


def _paragraph_neighbours(section: str, marker: str) -> tuple[str, str]:
    """Openings of the paragraphs immediately before and after the marked one.

    The paragraph pin stops at its own blank line, so a contradicting paragraph parked beside it
    is outside every comparison. Pinning the two neighbours BY IDENTITY closes that: an inserted
    paragraph on either side changes one of them. Not a whole-section paragraph-list assertion —
    §6 stays free to change elsewhere; only the two immediate neighbours are fixed.
    """
    paras = _paragraphs(section)
    for i, para in enumerate(paras):
        if para.startswith(marker):
            return (_head(paras[i - 1]) if i > 0 else "",
                    _head(paras[i + 1]) if i + 1 < len(paras) else "")
    return ("", "")


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


# The paragraph's opening words, used as its handle. Short enough that a rewrite of the
# instruction itself still resolves to the paragraph (and then fails on content, which is the
# readable failure) rather than vanishing into "paragraph not found".
_SHAPE_MARKER = "For a new rule the engine appends"

_SHAPE_PARAGRAPH = _normalise("""\
For a new rule the engine appends in each site's **native form** (CLAUDE.md prose / a hook
script / a skill SKILL.md); an **Edit** rewrites the targeted entry in place. If the site's
content is already an index+detail split (one-line index rows linking to per-entry files, e.g.
`README.md` → `../policies/Pn.md`), match that shape — one terse index row plus its linked
detail file, not a new inline block — and **put the detail file where the existing ones live,
resolving the index's own link to find out**. Never invent this split on a site that doesn't
already use it. An **Edit** there rewrites **both** the index row and its detail file whenever
the change touches what the index claims.
""")

# The two paragraphs the shape instruction sits between, by the identity of their first lines.
_SHAPE_NEIGHBOURS = (
    "**Necessity gate — runs here, after the conflict check and before the §3 confirm",
    "",  # it is §6's last paragraph — anything appended below makes this non-empty
)

# The two headings §6 itself sits between. An inserted `## 6b.` sibling would end the §6 slice
# early and park its own text outside every pin; this is what sees it.
_SECTION_6_NEIGHBOURS = (
    "## 5. Inviolability safety mechanism (the engine enforces it)",
    "## 7. Output contract",
)


def check_shape_paragraph_verbatim(text: str) -> tuple[bool, str]:
    """The whole index+detail paragraph matches its pinned text, VERBATIM."""
    if _section_6_span(text) is None:
        return False, "§6 section boundary not found (header drift?)"
    para = _paragraph_with(_section_6(text), _SHAPE_MARKER)
    if not para:
        return False, (
            f"§6 has no paragraph opening with {_SHAPE_MARKER!r} — the index+detail write "
            "instruction is missing outright"
        )
    if para != _SHAPE_PARAGRAPH:
        return False, (
            "§6's index+detail paragraph no longer matches its pinned text — a clause was "
            "added, removed or reworded anywhere in it. If that is intended, update "
            "_SHAPE_PARAGRAPH in this file in the same commit"
        )
    return True, "§6's index+detail paragraph matches its pinned text verbatim"


def check_shape_paragraph_neighbours(text: str) -> tuple[bool, str]:
    """Nothing new may be parked immediately beside the pinned paragraph."""
    if _section_6_span(text) is None:
        return False, "§6 section boundary not found (header drift?)"
    got = _paragraph_neighbours(_section_6(text), _SHAPE_MARKER)
    if got != _SHAPE_NEIGHBOURS:
        return False, (
            "the §6 paragraphs around the index+detail instruction changed — a paragraph "
            f"inserted beside it sits outside the pin. expected {_SHAPE_NEIGHBOURS}, got {got}"
        )
    return True, "§6's index+detail paragraph still sits between its two known paragraphs"


def check_section_6_neighbours(text: str) -> tuple[bool, str]:
    """§6 still sits between `## 5.` and `## 7.` — no sibling heading inserted next to it."""
    got = _neighbour_headings(_SECTION_6_RE, text)
    if got != _SECTION_6_NEIGHBOURS:
        return False, (
            "§6's neighbouring headings changed — an inserted sibling section would park its "
            f"text outside the §6 slice every check here reads. expected "
            f"{_SECTION_6_NEIGHBOURS}, got {got}"
        )
    return True, "§6 still sits between `## 5.` and `## 7.` (no sibling heading inserted)"


_CHECKS = [
    check_index_detail_shape_named,
    check_match_shape_instruction,
    check_never_invent_guard,
    check_scoped_to_section_6,
]

# Exercised against the REAL SKILL.md and mutations of it (the in-memory fixtures above are
# bare §6 fragments with no `## 5.` neighbour, so they cannot carry an identity pin).
_PIN_CHECKS = [
    check_shape_paragraph_verbatim,
    check_shape_paragraph_neighbours,
    check_section_6_neighbours,
]


def run_checks(text: str) -> tuple[int, int]:
    passed = failed = 0
    for check in _CHECKS + _PIN_CHECKS:
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
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue; for a new rule it appends in each
site's native form, and for an Edit-classified rule it rewrites the targeted entry in
place instead. If the chosen site's current content is already an index+detail split
(a thin summary table/list of one-liners each linking to a per-entry file, e.g. a
catalogue README.md -> policies/Pn.md), match that shape — add one terse index row
plus its linked detail file, not a new inline block — so the always-loaded index
doesn't grow unbounded as entries accumulate. Never invent this split on a site that
doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# Regression of the pre-#340 SKILL.md: §6 says nothing about index+detail sites at all.
_FAILING = """\
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue; for a new rule it appends in each
site's native form, and for an Edit-classified rule it rewrites the targeted entry in
place instead — always conflict-checked against that site's present content.

## 7. Output contract

Some unrelated §7 content.
"""

# A clause present but leaked into §7 instead of §6 — must fail the scoping check.
_LEAKED = """\
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue.

## 7. Output contract

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.
"""

# Same claims as _PASSING, but every phrase straddles a line break. Hard-wrapped
# prose must still read as stating them — a plain substring test fails here, which
# is how 90a20d2's reflow made `never invent this split` look deleted.
_WRAPPED = """\
## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail
split, match that
shape — add one terse index
row plus its linked detail
file, not a new inline
block. Never invent
this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# One word off in each instruction phrase ("the"/"that", "that"/"this"). The
# claims are absent, but only just — this bounds how far `_states` may be
# loosened. Widen it to `.*` or drop a word from a phrase and this fixture is
# the case that goes red; every other fixture stays green.
_NEAR_MISS = """\
## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match the
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent that split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# Every checked phrase embedded in a longer word at one edge or the other:
# "reindex row", "shapeshift", "filename", "splitter". `\s+` alone guards the
# internal gaps, so these are the cases that need `\b` on the outer two edges.
_SUBSTRING_BAIT = """\
## 6. Conflict check (target = the landfill site's current rules)

Reindexing a reindex row is unrelated to any index+detail splitter, and the
match that shapeshifts is not the shape to match; a detail filename is not a
detail file, and never inventing this splitter is not the guard either.

## 7. Output contract

Some unrelated §7 content.
"""

# §9 quotes §6 verbatim, header line and all. Content-based excision would cut
# both copies and report no leak; a span excision cuts only the real §6 and sees
# the quoted instruction sitting outside it.
_SECTION_6_QUOTED_ELSEWHERE = """\
## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.

## 9. Appendix — the §6 rule, quoted

## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# §3 resolves the index link for placement and §8 verifies the written split.
# Both name the shape outside §6 without carrying the instruction — not a leak.
_NAMED_OUTSIDE_6 = """\
## 3. The three landfill sites

If the site is an index+detail split, follow the index's links and read the detail
files before deciding where the new entry goes.

## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.

## 8. Post-write self-check

On an index+detail split, also verify the link resolves and that the loaded
directory gained no new `.md`.
"""


# ---------------------------------------------------------------------------
# #663 pin mutations. Built by `.replace()` off the REAL SKILL.md, never typed by hand: a
# hand-copied base drifts silently and its expect-FAIL case starts testing nothing. The
# import-time guard below is what makes that loud — a `.replace()` whose target has moved
# yields a copy of the base, and an expect-FAIL case on an unmodified copy always passes.
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL_PATH.read_text(encoding="utf-8")

# THE ESCAPE HATCH the phrase checks could not close: a new sibling section parked immediately
# after §6, carrying the opposite instruction. The §6 slice now ends at `## 6b.`, so every
# phrase check reads the untouched §6 and passes; only the heading-adjacency pin sees it.
_SIBLING_SECTION_INSERTED = _CLEAN_SKILL.replace(
    "\n## 7. Output contract",
    "\n## 6b. Conflict check — addendum\n\nOn a catalogue site, append a new inline block\n"
    "instead, and introduce the index+detail shape wherever it would help.\n\n"
    "## 7. Output contract",
)

# The same trick one level down: a contradicting PARAGRAPH parked inside §6, immediately after
# the pinned one. It is outside the paragraph pin by construction; the paragraph-adjacency pin
# is what reds.
_ADJACENT_PARAGRAPH_INSERTED = _CLEAN_SKILL.replace(
    "\n## 7. Output contract",
    "\nOn a catalogue site, append a new inline block instead — the split above is a\n"
    "suggestion, not a requirement.\n\n## 7. Output contract",
)

# A clause rewritten INSIDE the paragraph, between the two phrase-pinned anchors, so both
# anchors survive verbatim and say nothing about the sentence that now contradicts them.
_PARAGRAPH_CLAUSE_REWRITTEN = _CLEAN_SKILL.replace(
    "match that shape — one terse index row plus its linked\ndetail file, not a new inline block —",
    "match that shape — or, if the index is already long, a new inline block —",
)

# The detail-file placement rule deleted: the split is matched, but the detail file lands inside
# the loaded directory, which is the measured leak reference.md §3 records.
_PLACEMENT_RULE_DELETED = _CLEAN_SKILL.replace(
    " and **put the detail file where the existing ones live,\nresolving the index's own link to find out**.",
    ".",
)

# A realistic reflow: every prose paragraph rewrapped onto one line, headings, bullet lists and
# fenced blocks left where they are. Whitespace is not the contract, so this must stay green.
_PARAGRAPH_REFLOWED = "\n\n".join(
    block if block.startswith("#") or block.startswith("-") or "```" in block
    else " ".join(block.split())
    for block in _CLEAN_SKILL.split("\n\n")
)

for _name, _fixture, _base in (
    ("_SIBLING_SECTION_INSERTED", _SIBLING_SECTION_INSERTED, _CLEAN_SKILL),
    ("_ADJACENT_PARAGRAPH_INSERTED", _ADJACENT_PARAGRAPH_INSERTED, _CLEAN_SKILL),
    ("_PARAGRAPH_CLAUSE_REWRITTEN", _PARAGRAPH_CLAUSE_REWRITTEN, _CLEAN_SKILL),
    ("_PLACEMENT_RULE_DELETED", _PLACEMENT_RULE_DELETED, _CLEAN_SKILL),
    ("_PARAGRAPH_REFLOWED", _PARAGRAPH_REFLOWED, _CLEAN_SKILL),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

_CANONICAL_CASES: list[tuple[str, str, bool]] = [
    ("the real SKILL.md passes every pin", _CLEAN_SKILL, True),
    ("a new `## 6b.` sibling section parks the opposite instruction beside §6 -> FAIL "
     "(every phrase check still passes)", _SIBLING_SECTION_INSERTED, False),
    ("a contradicting paragraph parked right after the pinned one -> FAIL",
     _ADJACENT_PARAGRAPH_INSERTED, False),
    ("a clause rewritten between the two phrase anchors -> FAIL",
     _PARAGRAPH_CLAUSE_REWRITTEN, False),
    ("the detail-file placement rule deleted -> FAIL", _PLACEMENT_RULE_DELETED, False),
    ("a whole-file reflow still passes (whitespace is not the contract)",
     _PARAGRAPH_REFLOWED, True),
]


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in (
        check_index_detail_shape_named,
        check_match_shape_instruction,
        check_never_invent_guard,
    ):
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_scoped_to_section_6(_LEAKED)
    cases.append(("leaked: check_scoped_to_section_6 (expect FAIL)", not ok))

    # Regression of the two ways this suite went red on a correct SKILL.md (#440).
    for check in _CHECKS:
        ok, _ = check(_WRAPPED)
        cases.append((f"hard-wrapped: {check.__name__}", ok))

    ok, _ = check_scoped_to_section_6(_NAMED_OUTSIDE_6)
    cases.append(("shape named in §3/§8 is not a leak: check_scoped_to_section_6", ok))

    # The other edge of the same fix: `_states` spans whitespace, and nothing
    # more. A one-word-off phrase must still read as absent.
    for check in (check_match_shape_instruction, check_never_invent_guard):
        ok, _ = check(_NEAR_MISS)
        cases.append((f"near-miss: {check.__name__} (expect FAIL)", not ok))

    # A verbatim copy of §6 elsewhere must not hide a leak (#442): span excision
    # cuts only the real §6, so the quoted instruction is still seen outside it.
    ok, _ = check_scoped_to_section_6(_SECTION_6_QUOTED_ELSEWHERE)
    cases.append(("§6 quoted elsewhere: check_scoped_to_section_6 (expect FAIL)", not ok))

    # Nor may a phrase match inside a longer word at either outer edge (#442).
    for check in (
        check_index_detail_shape_named,
        check_match_shape_instruction,
        check_never_invent_guard,
    ):
        ok, _ = check(_SUBSTRING_BAIT)
        cases.append((f"substring-bait: {check.__name__} (expect FAIL)", not ok))

    # #663: the whole-paragraph pin + both adjacency pins, against the real SKILL.md and
    # `.replace()` mutations of it. Every one of these passes the phrase checks above.
    for desc, skill_text, expect_pass in _CANONICAL_CASES:
        got = all(ok for ok, _ in (check(skill_text) for check in _PIN_CHECKS))
        cases.append((f"pin: {desc}", got == expect_pass))
        if not expect_pass:
            # The point of the pin layer: the OLD phrase-only suite lets each of these through.
            phrase_ok = all(ok for ok, _ in (check(skill_text) for check in _CHECKS))
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
    print(f"OK: all {passed} add-policy-index-detail checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
