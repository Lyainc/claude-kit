#!/usr/bin/env python3
"""Regression test: an agent-inferred rule candidate cannot reach the landfill unjudged (#459).

`add-policy` is designed NOT to re-judge whether a rule is worth keeping — its input contract
assumed every candidate arrived already judged (a user stated it, or `distill` ruled on it).
A third kind arrives in practice: one the AGENT inferred from watching the session. It looks
like a user one-liner, so it inherited the free pass and landed with no worth-keeping judgment
behind it. Measured over 2,245 telemetry events (2026-06-23 ~ 07-30): `add-policy` ran 8 times,
`distill` 2 — and 6 of the 8 came through no distill at all.

Three prose skills, so this is a static-content check on the live SKILL.md files (the same
shape as test-add-policy-routing.py). Pinned:

  1. add-policy §1 names the agent-inferred input as its own case, distinct from the two
     already-judged kinds.
  2. Its test is OBSERVABLE — point at the user's utterance in the transcript — not a
     re-judgment of the rule's merit. An unobservable criterion is what let this collapse
     into "treat it as user-stated" in the first place.
  3. The inferred case is BOUNCED to /distill, and the bounce runs BEFORE classification and
     the §6 conflict check (bouncing after them throws that work away).
  4. The "add-policy never re-judges what to keep" invariant is explicitly preserved —
     routing to the judge is not judging. Without this the fix reads as a contradiction of
     the skill's own boundary and the next editor reverts it.
  4b. §1 — the WHOLE section — matches its pinned text verbatim. It exempts the distill
     proposal from the bounce and nothing else: a proposal carries no user utterance stating
     the rule, so a bare binary returns it to the skill that sent it, while exempting "a user
     one-liner" alongside it re-opens the disguise path (an inferred candidate enters looking
     like one). The span is the section, not the gate paragraph, because a clause parked in
     §1's first paragraph re-opened it with the paragraph's own bytes untouched. §1 is what
     compaction re-attaches, so a carve-out in reference.md alone is not there when it applies.
  4c. `## Rules`' source-gate bullet matches its pinned text verbatim too — it is a
     compaction-critical anchor, and an exemption appended there contradicts §1 from inside
     the window while §1's pin stays green.
  5. add-policy's `## Rules` carries the gate (the compaction-critical anchor, #454).
  6. distill's DROP list carries the recurrence floor, worded as two SEPARATED points in the
     conversation, with one turn counting once — a single sighting is an instance, not a class.
  7. distill's DROP list carries the default-behavior filter.
  8. "already documented" has a CHECK procedure with a fixed, non-recursive target list, and
     says why it must live here (add-policy's §6 only ever scans the one site it chose).
  9. The recurrence floor is also in distill's `## Rules`, as a DROP condition.

(retro's own memory/rule output branches were removed entirely as pure pass-throughs, #639 —
there is no rule branch left in retro to pin a routing destination for.)

Usage:
    python3 feedback-loop/scripts/test/test-distill-gate-routing.py
    python3 feedback-loop/scripts/test/test-distill-gate-routing.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILLS = _REPO_ROOT / "feedback-loop" / "skills"
_ADD_POLICY = _SKILLS / "add-policy" / "SKILL.md"
_DISTILL = _SKILLS / "distill" / "SKILL.md"
_RETRO = _SKILLS / "retro" / "SKILL.md"


def _prose(text: str) -> str:
    """Collapse hard wrapping so a claim is findable wherever the line broke."""
    return re.sub(r"\s+", " ", text.lower())


def _normalise(text: str) -> str:
    """Whitespace-only collapse, case preserved — for the verbatim pin below (#440)."""
    return " ".join(text.split())


def _section(text: str, start: str, end_prefix: str = "\n## ") -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end_prefix, i + len(start))
    return text[i:] if j < 0 else text[i:j]


def _rules(text: str) -> str:
    return _section(text, "\n## Rules")


# --- add-policy -------------------------------------------------------------

def check_third_input_case(ap: str, di: str, re_: str) -> tuple[bool, str]:
    p = _prose(ap)
    if "inferred by the agent" not in p and "agent inferred" not in p:
        return False, "add-policy §1 does not name the agent-inferred candidate as an input case"
    if "third" not in p:
        return False, "the inferred candidate is not marked as a THIRD case distinct from the two judged kinds"
    return True, "add-policy §1 names the agent-inferred third input case"


def check_observable_test(ap: str, di: str, re_: str) -> tuple[bool, str]:
    p = _prose(ap)
    if "transcript" not in p:
        return False, "the source test is not anchored to the transcript"
    if "utterance" not in p:
        return False, "the test does not turn on pointing at the USER's own utterance"
    if "provenance" not in p:
        return False, "the gate is not framed as routing by provenance (source), not by merit"
    return True, "source test is observable (point at the user's utterance in the transcript)"


def check_bounce_to_distill_before_work(ap: str, di: str, re_: str) -> tuple[bool, str]:
    # Scoped to §1: "/distill", "before" and "conflict check" all appear elsewhere in the
    # document, so an unscoped search passes on the pre-#459 file and pins nothing.
    p = _prose(_section(ap, "## 1. Input contract"))
    if not p:
        return False, "add-policy §1 (Input contract) section not found"
    if "/distill" not in p:
        return False, "add-policy never names /distill as the bounce destination"
    if "before" not in p or "classification" not in p:
        return False, "the gate is not ordered BEFORE classification"
    if "conflict check" not in p:
        return False, "the gate is not ordered before the §6 conflict check (wasted work on a bounce)"
    return True, "inferred candidates bounce to /distill before classification + conflict check"


def check_never_rejudge_preserved(ap: str, di: str, re_: str) -> tuple[bool, str]:
    # Scoped to §1 for the same reason: the invariant is stated elsewhere already, and what
    # must be pinned is that it is restated WHERE the gate is introduced.
    p = _prose(_section(ap, "## 1. Input contract"))
    if not p:
        return False, "add-policy §1 (Input contract) section not found"
    if "re-judg" not in p and "rejudg" not in p:
        return False, "the never-re-judge invariant is not restated where the gate is introduced"
    if "judge" not in p:
        return False, "bouncing is not framed as routing to the judge"
    return True, "never-re-judge invariant preserved: the gate routes, it does not judge"


# The WHOLE source-gate paragraph, pinned VERBATIM — equality over the block, not a phrase
# search. Two review rounds put two opposite defects in this one paragraph: an unconditional
# binary bounced the distill proposal that retro → distill → add-policy sends (an infinite
# hand-off), and the fix for that widened the exemption to "a user one-liner" — which hands
# back the free pass #459 exists to revoke, since an agent-inferred candidate enters looking
# exactly like one (measured: 6 of 8 runs, `trigger: explicit` on every row). A presence check
# on "proposal proceeds" stayed GREEN on both the widened branch and on an inversion that kept
# the phrase and reversed the sentence around it. Every phrase pin is a blocklist of the last
# wording someone tried; this file's siblings already burned four of them, so the paragraph's
# own text is the pin and the comparison is total. Whitespace is normalised — a reflow is not
# a change (#440) — and updating this constant is the deliberate act of changing the contract,
# in the same commit.
#
# The span is the WHOLE of §1, not the source-gate paragraph alone. Anchored at the paragraph,
# a clause appended to §1's FIRST paragraph — "a candidate that plainly reflects the user's
# standing intent counts as a user one-liner and proceeds without further test" — passed every
# check with the pinned bytes untouched, and it sits in the input contract the engine reads
# immediately before applying the gate, inside the same compaction window. Same widening, same
# reason, as `_PREAMBLE_CONTRACT` in test-add-policy-conflict-edit.py.
_SOURCE_GATE_CONTRACT = """\
## 1. Input contract — what the engine accepts

The engine takes a rule in **natural language**: a **user one-liner**, or a **distill proposal
object** carrying *what*, *why*, *session provenance*, and an *inviolability judgment*. It
**re-runs the classification itself** on either — a proposal never arrives with the placement
pre-filled, so tier is inferred and **the inviolability judgment is enforced (§5), not
re-made**. ([reference.md](reference.md) §1)

**Source gate — the third input, and the one that must not land unjudged.** A candidate also
arrives **inferred by the agent**, which the two accepted kinds' free pass does not cover. Route
by **provenance**: a **distill proposal proceeds** — distill already judged it, and a proposal is
never bounced back to the skill that sent it. **Everything else, including anything that reads
like a user one-liner**, asks one question: **can you point at the user's own utterance stating
this rule in the transcript?** Yes → proceed. No → it is agent-inferred: **hand it to
`/distill`** — bouncing is not re-judging, it sends the candidate to the judge. Run it **before**
classification and the §6 conflict check, so a bounce wastes neither.
([reference.md](reference.md) §1-source)
"""


# `## Rules` is a compaction-critical anchor (#454) — it rides in front of the engine every
# session — and a summary is where a contradiction is cheapest to park: rewriting the bullet to
# "…unless it restates a standing user preference, which proceeds as a user one-liner" left the
# §1 pin untouched and every check green, because the Rules check only greps `source gate` and
# `/distill`. So THIS BULLET is pinned — and only it, deliberately. A whole-`## Rules` pin would
# red this suite on every unrelated policy bullet (the section carries nine, and #450/#429 each
# added one), which costs more in false reds than it buys: a NEW sibling bullet carrying the
# exemption still passes, and that is the pin strategy's ceiling, not an oversight. Two constants
# rather than one: §1 is the procedure, this is its summary, and they are edited for different
# reasons.
_RULES_GATE_CONTRACT = """\
- Source gate first (§1): a candidate the AGENT inferred — no user utterance to point at in
  the transcript — is bounced to `/distill` before classification, never landed. The engine
  still never re-judges what to keep; it routes the unjudged to the judge.
"""


def _rules_gate_bullet(text: str) -> str:
    """The `## Rules` bullet stating the source gate, or "" — from the heading, not the file.

    Scoped to `## Rules` for the same reason §1 is scoped: the claim is restated in §1, and a
    document-wide match would read the procedure and call the summary present.
    """
    rules = _rules(text)
    if rules.count("- Source gate first") != 1:
        return ""  # same decoy guard as _source_gate_block: one bullet, or no verdict
    i = rules.find("- Source gate first")
    if i == -1:
        return ""
    j = rules.find("\n- ", i)
    return (rules[i:j] if j != -1 else rules[i:]).strip()


def _source_gate_block(ap: str) -> str:
    """The whole of §1, or "" if the section or the gate paragraph inside it is missing.

    Scoped to §1 rather than the document: the gate is summarised in `## Rules` too, and a
    document-wide match would pass on the summary while the paragraph the engine executes
    was gone. Scoped to the whole section rather than the paragraph: see the constant.
    """
    if ap.count("## 1. Input contract") != 1:
        # A byte-identical decoy ABOVE the real section becomes the slice, and equality passes
        # against it while the section the engine reads is free to say anything. Exactly the
        # defect test-add-policy-conflict-edit.py records (a copy of the contract pasted into
        # §4 became the slice), so the count is the guard: one §1, or no verdict.
        return ""
    section = _section(ap, "## 1. Input contract")
    return section.strip() if "**Source gate" in section else ""


def check_proposal_not_bounced(ap: str, di: str, re_: str) -> tuple[bool, str]:
    """The source-gate paragraph matches its pinned contract text, exactly.

    What the equality carries: the distill proposal is exempt (a recognizable object, so
    recognizing one costs no judgment), and NOTHING else is — "user one-liner" is a claim
    about origin, which is what the transcript test decides, so exempting it re-opens the
    disguise path. The carve-out must live in §1 rather than in reference.md §1-source:
    after compaction §1 is what gets re-attached and the reference is not, so a clarification
    living only there is not in front of the engine when the test is applied.
    """
    if not _section(ap, "## 1. Input contract"):
        return False, "add-policy §1 (Input contract) section not found"
    block = _source_gate_block(ap)
    if not block:
        return False, "§1 has no source-gate paragraph"
    if _normalise(block) != _normalise(_SOURCE_GATE_CONTRACT):
        return False, (
            "§1 as a WHOLE no longer matches its pinned contract text — the pin spans the "
            "entire section, so the change may be anywhere in it, including the input-contract "
            "paragraph above the gate. If it is an exemption: widening past the distill "
            "proposal re-opens the free pass #459 revoked, narrowing to a bare binary bounces "
            "the proposal back to distill. If it is an ordinary edit (a citation, a typo, "
            "rewording), it is fine — update _SOURCE_GATE_CONTRACT in this file in the same "
            "commit. A pure reflow is not a change and will not reach here"
        )
    return True, "§1 (whole section) matches its pinned contract text verbatim"


def check_rules_bullet_verbatim(ap: str, di: str, re_: str) -> tuple[bool, str]:
    """`## Rules`' source-gate bullet matches its pinned text, exactly.

    Kept beside the presence check below, which names WHICH half went missing where this one
    only says the bullet changed. The equality is what stops an exemption being appended to
    the summary — the anchor that rides in front of the engine every session — while §1's
    pinned procedure sits underneath, untouched and contradicted.
    """
    if not _rules(ap):
        return False, "add-policy has no ## Rules section"
    bullet = _rules_gate_bullet(ap)
    if not bullet:
        return False, "`## Rules` has no source-gate bullet"
    if _normalise(bullet) != _normalise(_RULES_GATE_CONTRACT):
        return False, (
            "the `## Rules` source-gate bullet no longer matches its pinned text — an exemption "
            "added here contradicts §1 from inside the compaction window. If the change is "
            "intended, update _RULES_GATE_CONTRACT in this file in the same commit"
        )
    return True, "`## Rules` source-gate bullet matches its pinned text verbatim"


def check_gate_in_add_policy_rules(ap: str, di: str, re_: str) -> tuple[bool, str]:
    r = _prose(_rules(ap))
    if not r:
        return False, "add-policy has no ## Rules section"
    if "source gate" not in r:
        return False, "the source gate is missing from add-policy's ## Rules"
    if "/distill" not in r:
        return False, "add-policy's Rules do not name /distill as the bounce destination"
    return True, "source gate present in add-policy's ## Rules"


# --- distill ----------------------------------------------------------------

def check_recurrence_floor(ap: str, di: str, re_: str) -> tuple[bool, str]:
    p = _prose(di)
    if "separated points" not in p:
        return False, "distill's recurrence floor ('two or more separated points') missing"
    if "one turn" not in p and "inside one turn" not in p:
        return False, "the same-turn collapse rule (twice in one turn counts once) missing"
    if "instance" not in p or "class" not in p:
        return False, "the instance-vs-class rationale for the floor is missing"
    return True, "recurrence floor: two separated points, one turn counts once"


def check_default_behavior_filter(ap: str, di: str, re_: str) -> tuple[bool, str]:
    p = _prose(di)
    if "default behavior" not in p and "default behaviour" not in p:
        return False, "the default-behavior DROP filter is missing from distill"
    if "anyway" not in p:
        return False, "the filter does not state the test (a competent agent would do it anyway)"
    return True, "default-behavior DROP filter present"


def check_already_landed_procedure(ap: str, di: str, re_: str) -> tuple[bool, str]:
    p = _prose(di)
    if "~/.claude/rules/readme.md" not in p or "~/.claude/claude.md" not in p:
        return False, "the already-landed check has no fixed grep target list"
    if "project claude.md" not in p:
        return False, "the project CLAUDE.md is missing from the fixed target list"
    if "no recursive sweep" not in p and "not recursive" not in p:
        return False, "the scan is not bounded (a recursive sweep is not a fixed target list)"
    if "grep" not in p:
        return False, "the check has no mechanism — 'already documented' stays an assertion from memory"
    if "add-policy" not in p:
        return False, "why the pre-landing check must live here (add-policy scans only its chosen site) is missing"
    return True, "already-landed check has a bounded, fixed-target procedure and states why it lives here"


def check_floor_in_distill_rules(ap: str, di: str, re_: str) -> tuple[bool, str]:
    r = _prose(_rules(di))
    if not r:
        return False, "distill has no ## Rules section"
    if "recurrence floor" not in r:
        return False, "the recurrence floor is missing from distill's ## Rules"
    if "drop" not in r:
        return False, "the floor is not stated as a DROP condition in distill's Rules"
    return True, "recurrence floor present in distill's ## Rules as a DROP condition"


# retro's own memory/rule output branches were removed entirely as pure pass-throughs (#639),
# along with the checks that used to pin their routing here — there is no rule branch left in
# retro's SKILL.md to point anywhere.

_CHECKS = [
    check_third_input_case,
    check_observable_test,
    check_bounce_to_distill_before_work,
    check_never_rejudge_preserved,
    check_proposal_not_bounced,
    check_rules_bullet_verbatim,
    check_gate_in_add_policy_rules,
    check_recurrence_floor,
    check_default_behavior_filter,
    check_already_landed_procedure,
    check_floor_in_distill_rules,
]

# --- self-test fixtures -----------------------------------------------------
# The PASSING trio is a minimal restatement of every pinned claim; the FAILING trio is the
# pre-#459 shape (two input cases, four DROP filters). retro no longer figures into any check
# (its rule branch is gone, #639), so _PASS_RE/_FAIL_RE below only need to be non-empty strings
# to satisfy every check function's (ap, di, re_) signature.

_PASS_AP = """---
name: add-policy
---
%s
## Rules

%s""" % (_SOURCE_GATE_CONTRACT, _RULES_GATE_CONTRACT)

_FAIL_AP = """---
name: add-policy
---
## 1. Input contract
A user one-liner, or a distill proposal object. The engine re-runs the classification itself.

## Rules
- Classify, then place.
"""

_PASS_DI = """---
name: distill
---
### Phase 1 — SCAN
DROP if:
- seen once — the recurrence floor: observed at two or more separated points in the
  conversation. Twice inside one turn counts as one. A single sighting is an instance, not a class;
- default behavior — a competent agent would do it anyway;
- already landed — check with grep over a fixed list: ~/.claude/rules/README.md, the detail
  directory it links to, ~/.claude/CLAUDE.md, the project CLAUDE.md. No recursive sweep.
  add-policy's §6 only scans the one site it already chose.

## Rules
- The recurrence floor is a DROP condition: fewer than two separated points → drop it.
"""

_FAIL_DI = """---
name: distill
---
### Phase 1 — SCAN
DROP if:
- one-off narrative;
- environment-dependent workaround;
- negative tool claim;
- already documented — the procedure already lives in an existing skill or CLAUDE.md.

## Rules
- Procedural technique ONLY.
"""

_PASS_RE = """---
name: retro
description: "outputs (action→git issue / memory→vault capture / rule→distill handoff)"
---
| **규칙 (rule)** | validated patterns | surface a ready-to-run `/distill` invocation | off |

- **Rule**: surface a ready-to-run `/distill` invocation. The chain is retro → distill →
  add-policy: distill judges, then add-policy classifies and places.

## Rules
- Rule output is a `/distill` suggestion — never a rule-file `Edit`.
"""

_FAIL_RE = """---
name: retro
description: "outputs (action→git issue / memory→vault capture / rule→add-policy handoff)"
---
| **규칙 (rule)** | validated patterns | surface a ready-to-run `/add-policy` invocation | off |

- **Rule**: surface a ready-to-run `/add-policy` invocation — add-policy owns classification.

## Rules
- Rule output is an `/add-policy` suggestion — never a rule-file `Edit`.
"""


def run_checks(ap: str, di: str, re_: str) -> tuple[int, int]:
    passed = failed = 0
    for check in _CHECKS:
        ok, msg = check(ap, di, re_)
        print(f"  [{'OK' if ok else 'FAIL'}] {msg}", file=sys.stdout if ok else sys.stderr)
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    return passed, failed


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []
    for check in _CHECKS:
        ok, _ = check(_PASS_AP, _PASS_DI, _PASS_RE)
        cases.append((f"passing: {check.__name__}", ok))
    for check in _CHECKS:
        ok, _ = check(_FAIL_AP, _FAIL_DI, _FAIL_RE)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    # The three mutations review landed in this one paragraph, in the order they were found.
    # A phrase pin on "proposal proceeds" stayed green on all three; the verbatim pin must red
    # on each. Every fixture is asserted different from its base, so a .replace() that stops
    # matching becomes a failure rather than a silent copy of _PASS_AP.
    for label, mutated in (
        # 1. The unconditional binary: no exemption at all, so retro → distill → add-policy
        #    returns the proposal to the skill that sent it.
        ("bare binary — proposal bounced back to distill", _PASS_AP.replace(
            "a **distill proposal proceeds** — distill already judged it, and a proposal is\n"
            "never bounced back to the skill that sent it. **Everything else, including "
            "anything that reads\nlike a user one-liner**, asks",
            "every candidate asks",
        )),
        # 2. The over-wide fix: the free pass handed back on the path 6 of 8 measured runs take.
        ("exemption widened to a look-alike one-liner", _PASS_AP.replace(
            "a **distill proposal proceeds**",
            "anything you judge to be a user one-liner, or a **distill proposal**, proceeds",
        )),
        # 3. The phrase kept, the meaning inverted — what defeated the presence check.
        ("phrase kept, meaning inverted", _PASS_AP.replace(
            "and a proposal is\nnever bounced back to the skill that sent it",
            "though a proposal is\nbounced back to the skill that sent it all the same",
        )),
        # 4. Above the gate paragraph, inside §1: the boundary that a paragraph-anchored span
        #    left open. The gate's own bytes are untouched here.
        ("exemption parked in §1's first paragraph, above the gate", _PASS_AP.replace(
            "re-made**. ([reference.md](reference.md) §1)",
            "re-made**. ([reference.md](reference.md) §1) A candidate that plainly reflects the\n"
            "user's standing intent counts as a user one-liner and proceeds without further test.",
        )),
    ):
        assert mutated != _PASS_AP, f"fixture no-opped: {label}"
        ok, _ = check_proposal_not_bounced(mutated, _PASS_DI, _PASS_RE)
        cases.append((f"mutation: {label} (expect FAIL)", not ok))

    # The same attack against the summary anchor: §1 untouched, the exemption appended to the
    # `## Rules` bullet that rides in front of the engine every session.
    _MUT_RULES = _PASS_AP.replace(
        "still never re-judges what to keep; it routes the unjudged to the judge.",
        "still never re-judges what to keep — unless the candidate restates a standing user\n"
        "  preference, which proceeds as a user one-liner.",
    )
    assert _MUT_RULES != _PASS_AP, "fixture no-opped: the Rules bullet tail moved"
    ok, _ = check_rules_bullet_verbatim(_MUT_RULES, _PASS_DI, _PASS_RE)
    cases.append(("mutation: exemption appended to the `## Rules` bullet (expect FAIL)", not ok))

    # The decoy shape both pins are vulnerable to without a count guard: a byte-identical copy
    # ABOVE the corrupted one becomes the slice, equality passes against the decoy, and the text
    # the engine actually reads is free to say anything. Recorded in this directory already
    # (test-add-policy-conflict-edit.py, a copy of the contract pasted into §4).
    _DECOY_SECTION = _PASS_AP.replace(
        "## 1. Input contract",
        "## 1. Input contract" + _SOURCE_GATE_CONTRACT.split("## 1. Input contract", 1)[1]
        + "\n## 1. Input contract",
        1,
    )
    assert _DECOY_SECTION.count("## 1. Input contract") == 2, "decoy fixture did not duplicate §1"
    ok, _ = check_proposal_not_bounced(_DECOY_SECTION, _PASS_DI, _PASS_RE)
    cases.append(("decoy: a second `## 1.` section ahead of the real one (expect FAIL)", not ok))

    _DECOY_BULLET = _MUT_RULES.replace(
        "- Source gate first", _RULES_GATE_CONTRACT.strip() + "\n- Source gate first", 1
    )
    assert _DECOY_BULLET.count("- Source gate first") == 2, "decoy fixture did not duplicate it"
    ok, _ = check_rules_bullet_verbatim(_DECOY_BULLET, _PASS_DI, _PASS_RE)
    cases.append(("decoy: a clean `## Rules` bullet ahead of a corrupted one (expect FAIL)", not ok))

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

    try:
        ap, di, re_ = (p.read_text(encoding="utf-8") for p in (_ADD_POLICY, _DISTILL, _RETRO))
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(ap, di, re_)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} distill-gate-routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
