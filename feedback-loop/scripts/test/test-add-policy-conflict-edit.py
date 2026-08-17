#!/usr/bin/env python3
"""Regression test: add-policy §6 conflict-check has an Edit bucket and a Supersede exit.

#303. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill, so this
is a static-content check — it does not execute LLM logic. It pins the claim that an
explicit "change this existing entry" request is its own conflict-check outcome
(Edit), distinct from Duplicate (strengthen) and Contradiction (refuse) — guarding
against a future edit silently collapsing Edit back into one of those two, which was
the exact gap #303 reported (an explicit edit request risked being misclassified as
Contradiction and refused, or only surfacing as a side effect of Duplicate).

#429 adds the other half. Every §6 verdict left the entry count flat — Contradiction
included, since it refuses the write rather than clearing anything — so the catalogue
was monotonically increasing (local-harness: 12 policies in 39 days, 1 removed, and
that one a by-product of a manual audit). Supersede is the exit path: a new rule that
makes an existing entry redundant absorbs and retires it in the SAME write, on the same
confirmation. Pinned here because it is a §6 verdict + a §3 confirmation field, exactly
what this suite already guards.

The pinned claims:

1. §6's conflict-check bullet list names "Edit" as its own outcome, distinct from
   Duplicate and Contradiction, and describes showing a before -> after diff of the
   existing entry rather than just new prose to add.
2. §3's 1-click confirmation template's 충돌 (conflict) field enumerates the edit
   outcome alongside none / sibling / contradiction, so the UX surface reflects it.
3. §6 names "Supersede" as its own outcome, retiring the redundant entry in the same
   write, and forbids reusing a retired number.
4. That retirement rides on the same single confirmation — never a second prompt.
5. §3's confirmation template carries the 은퇴 (retirement) field.
6. (#609) §6 names the never-fired retirement as its own outcome, offering BOTH choices
   (delete / narrow the firing condition) under the recommends-only ceiling and on the same
   confirmation, triggered by positive evidence only (never silence) and routing its delete
   through `trash-put`. Supersede only removes what a NEW rule absorbs, and
   `lint-catalogue.sh` caps the framing but deliberately not the row count, so without this an
   entry that was simply never needed has no exit at all.
7. (#609) §3's hook site names BOTH forms with the mechanism each actually has — blocking =
   PreToolUse + `permissionDecision`, recovery = PostToolUse + `exit 2`. Documenting recovery
   with PreToolUse fields would send every future recovery rule into a dead end.
8. (#609) the tier sentence defines HARD as "deterministically enforced", never "a guard
   blocks", while keeping `tier folds into the site`. Under the old definition recovery has no
   tier, and the engine must either add a second axis (breaking the 1-click UX) or push
   recovery rules back to the reminder site — the bug #609 was filed on.

#663 moved the Supersede verdict's CANONICAL text out of the SKILL.md body and into
`add-policy/reference.md` §6-supersede-contract, because §6 had every ≥300-char paragraph
pinned verbatim and the token budget (#447) had no escape hatch left that wasn't a trim. The
pin followed the text rather than being deleted (#609 measured what an unpinned region is
worth). So the live run reads BOTH files: the verdict against reference.md, §6's preamble, the
Edit bucket, the §3 template and the Supersede POINTER against SKILL.md. §6's preamble stays
pinned in the body — it is the section's own opening instruction and cannot be relocated.

9. (#663) ADJACENCY, both sides of the split. `_SUPERSEDE_CONTRACT` runs to the end of its
   bullet inside `## §6-supersede-contract`, so nothing unpinned may be parked below it — but
   that holds only up TO the next heading, and one inserted `## §6-supersede-addendum` moves
   arbitrary contradicting text outside every pin while the section still matches byte for byte.
   So the section's two NEIGHBOURING headings are pinned by identity. Not a whole-file
   heading-set assertion: reference.md is not wholly contract and stays free to gain sections.
10. (#663) The SKILL.md Supersede LOCATOR bullet is pinned WHOLE, with the same treatment one
   level down — its two neighbouring §6 verdict bullets by identity, and §6 itself between
   `## 5.` and `## 7.`. At runtime the always-loaded body outranks an on-demand doc, so a
   locator that decays into "retire it on a follow-up confirmation" defeats a perfectly pinned
   canonical section; and `check_supersede_verdict_named`'s substring checks close only the two
   clauses they name, leaving the rest of the bullet — and everything beside it — free.

KNOWN GAP (measured, not assumed). Verbatim-pinned across this suite and its siblings: §6's
preamble, the Supersede locator bullet and the necessity-gate locator (SKILL.md), the memory
locator and the index+detail paragraph (SKILL.md, pinned by test-add-policy-routing.py and
test-add-policy-index-detail.py), and the Supersede verdict, the gate block, §6-memory-contract
and §6-snippet (reference.md). What remains unpinned in §6 is the Duplicate / Edit / Unused
retirement / Contradiction / Sibling bullets, which the phrase checks here and in the sibling
suites cover claim-by-claim but not as regions: a contradicting clause added INSIDE one of those
bullets still passes. Closing it means pinning all of §6 verbatim, which buys little now that
every locator around those bullets is pinned and their adjacency with them — the Supersede
bullet's own neighbours are two of them, so neither can be deleted or reordered unseen. One line
that asserts the 1-click invariant outside every pin — SKILL.md's `## Rules` summary — is
unguarded for the same reason. Recorded so the coverage is a decision, not an assumption.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py
    python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py --self-test

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
_REFERENCE_PATH = _SKILL_PATH.with_name("reference.md")
# The reference file's own title line, used as the header-drift precondition: a fixture without
# it keeps the whole-document fallback the bare in-memory fixtures need.
_REFERENCE_TITLE = "# add-policy — reference"


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _load_reference() -> str:
    """#663: the Supersede verdict's canonical text lives here now, not in SKILL.md's body."""
    if not _REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"reference.md not found at {_REFERENCE_PATH}")
    return _REFERENCE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Checks — each returns (ok, message). Substring-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
# ---------------------------------------------------------------------------

# The §6 verdict bullets, and nothing else. The post-write self-check carries its own
# `- **Supersede**:` bullet, so a marker search over the whole document would silently retarget
# there if §6's bullet were deleted — reporting "doesn't retire in the same write" for a verdict
# that is missing outright. (That checklist sat in SKILL.md §8 when this scoping was added and
# moved to reference.md §8 in #469; the scoping still earns its place — the decoy would come
# back the moment anyone restates a verdict outside §6.) Fixtures are bare bullet fragments with
# no headers, so a document without the header pair falls back to itself.
_SECTION_6_RE = re.compile(r"^## 6\.\s.*?(?=^## 7\.\s)", re.MULTILINE | re.DOTALL)


def _verdict_scope(text: str) -> str:
    match = _SECTION_6_RE.search(text)
    return match.group(0) if match else text


# #663: the Supersede verdict's canonical text moved to reference.md, under its own heading. The
# scoping rationale carries over unchanged and is if anything more load-bearing here —
# reference.md §8's self-check checklist has its own `- **Supersede**:` bullet, so an unscoped
# marker search would silently retarget there the moment the verdict itself went missing.
_REF_SUPERSEDE_SECTION_RE = re.compile(
    r"^## §6-supersede-contract\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def _ref_supersede_scope(ref: str) -> str:
    match = _REF_SUPERSEDE_SECTION_RE.search(ref)
    return match.group(0) if match else ref


def _bullet_slice(text: str, marker: str) -> str | None:
    """Same slice as `_bullet_scope`, on the ORIGINAL text — the verbatim pin needs the case
    and punctuation intact, which the lower-cased scope throws away."""
    start = text.find(marker)
    if start == -1:
        return None
    nxt = text.find("\n- **", start + 1)
    return text[start:nxt] if nxt != -1 else text[start:]


def _normalise(text: str) -> str:
    """Collapse every run of whitespace, so a reflow reads as no change (#440)."""
    return " ".join(text.split())


def _states(text: str, phrase: str) -> bool:
    """True if `text` states `phrase`, ignoring how the prose happens to wrap.

    Same matcher as test-add-policy-necessity-gate.py, and for the same reason (#440): the
    files are hard-wrapped, so a reflow moves a line break into the middle of a phrase and a
    plain substring test reads the claim as deleted while it is still there.
    """
    core = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.search(rf"\b{core}\b", text, re.IGNORECASE) is not None


def _bullet_scope(lower: str, marker: str) -> str | None:
    """Slice `lower` from `marker` to the next top-level bullet (`\\n- **`), or
    +600 chars if there is no next bullet. None if `marker` isn't found. Scopes a
    claim check to one bullet's own text instead of the whole document, so an
    unrelated match elsewhere in the skill can't false-positive."""
    marker_pos = lower.find(marker)
    if marker_pos == -1:
        return None
    next_bullet = lower.find("\n- **", marker_pos + 1)
    return lower[marker_pos:next_bullet] if next_bullet != -1 else lower[marker_pos:marker_pos + 600]


# §6's PREAMBLE, pinned verbatim. Everything an engine reads before the verdict bullets — and
# therefore the cheapest place for a contradiction to land and the first place it takes effect.
# Review demonstrated it: "A verdict that *removes* an entry is destructive, so it is confirmed
# on its own second question, separately from the §3 addition", three lines above the Supersede
# bullet, passed every suite while granting the second prompt the bullet forbids. A pin only
# covers what it spans, so the span now includes the text above the bullets. The memory-scan
# mechanics further down §6 stay unpinned — test-add-policy-routing.py phrase-pins those.
_PREAMBLE_CONTRACT = """\
## 6. Conflict check (target = the landfill site's current rules + native auto-memory)

**New site**: check the target **exists** first (`[ -f "$TARGET" ]`, as §5 does for the skill
site). Never infer "missing" from a read *error* — that **overwrites existing content**. Absent
→ **`Write`**, not append; exists but unreadable → stop and report.
([reference.md](reference.md) §6-new-site)

Otherwise read the **current contents of the chosen site** first (read-only `Bash`/`Grep`):
that channel's own rules, or the existing hook matchers and guard scripts (so a new guard
doesn't fire on an event one already covers), or existing skills.
**If the site is an index+detail split, follow the index's links and read the detail files
too** — they may sit outside the indexed directory (§3), and scanning that directory alone
downgrades the check to a title comparison:
"""


# Any top-level bullet, not `- **Duplicate` specifically. What this fixes is FALSE FAILURES on
# benign refactors: renaming the first verdict to something that doesn't start with "Duplicate"
# (`- **Same rule**:`) or reordering the list so Edit comes first both made the old boundary
# miss and red CI. Naming one verdict in the boundary coupled the pin to a label that is free
# to change.
#
# It does NOT close the bullet-shaped decoy: a line beginning `- **` planted right after the
# pinned text ends the slice exactly where the old boundary did, `head` still equals the
# contract, and the check still passes. That case is the documented ceiling — see the KNOWN GAP
# block in the module docstring and the `ponytail:` note on `_PREAMBLE_DECOY_BULLET`. Anything
# below the first top-level bullet is outside this pin, by construction.
_FIRST_BULLET_RE = re.compile(r"^- \*\*", re.MULTILINE)


def check_conflict_preamble_verbatim(skill: str, ref: str = "") -> tuple[bool, str]:
    """§6's opening, up to the first verdict bullet, matches its pinned contract text."""
    text = skill
    if _SECTION_6_RE.search(text) is None:
        return False, "§6 section boundary not found (header drift?)"
    section = _verdict_scope(text)
    match = _FIRST_BULLET_RE.search(section)
    if match is None:
        return False, "§6 has no verdict bullets — the outcome list is missing"
    head, contract = _normalise(section[:match.start()]), _normalise(_PREAMBLE_CONTRACT)
    if head != contract:
        # Prefix-vs-equality split so the message says WHICH way it drifted: text inserted
        # between the pinned preamble and the bullets is not the same defect as an edit inside
        # the preamble, and only the second means the constant is out of date.
        # No attempt to say WHICH way it drifted. A clause inserted under the `## 6.` heading
        # and one inserted before the bullets both break contiguity without the contract
        # surviving as a substring, so any such branch guesses — and a wrong guess sends the
        # author to edit the wrong file. The message names both repairs instead.
        return False, (
            "§6's preamble no longer matches its pinned contract text — something above the "
            "first verdict bullet was added, removed or reworded, and that region is what an "
            "engine reads before any verdict. If the wording change is intended, update "
            "_PREAMBLE_CONTRACT in this file; if text was inserted, put it below the pinned "
            "region instead"
        )
    return True, "§6 preamble matches its pinned contract text verbatim"


def check_edit_bucket_named(skill: str, ref: str = "") -> tuple[bool, str]:
    """§6 must name Edit as its own conflict-check outcome, not folded into Duplicate."""
    text = skill
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**edit")
    if bullet_text is None:
        return False, "Edit is not named as its own §6 conflict-check outcome"
    if "before" not in bullet_text or "after" not in bullet_text:
        return False, "Edit outcome doesn't describe a before -> after diff"
    return True, "Edit named as a distinct §6 outcome with a before -> after diff"


def check_edit_distinct_from_contradiction(skill: str, ref: str = "") -> tuple[bool, str]:
    """Contradiction must be scoped to exclude an explicit edit request."""
    text = skill
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**contradiction")
    if bullet_text is None:
        return False, "Contradiction outcome missing entirely"
    if "not target" not in bullet_text and "not an explicit edit" not in bullet_text and "does not target" not in bullet_text:
        return False, (
            "Contradiction isn't scoped to exclude explicit-edit requests — an edit "
            "request could still be misclassified as a refusal"
        )
    return True, "Contradiction explicitly excludes requests that are an edit of that entry"

def check_confirmation_template_lists_edit(skill: str, ref: str = "") -> tuple[bool, str]:
    """§3's 충돌 confirmation field must enumerate the edit outcome."""
    text = skill
    field_pos = text.find("충돌:")
    if field_pos == -1:
        return False, "충돌 confirmation field missing from the §3 template"
    # Scope to the 충돌 field's own line, not text.split("충돌")[-1] (the whole
    # document tail from the LAST occurrence) — a second unrelated "충돌" mention
    # added anywhere later in the file would otherwise silently validate the wrong text.
    line_end = text.find("\n", field_pos)
    field_line = text[field_pos:line_end if line_end != -1 else len(text)].lower()
    if not re.search(r"\bedit", field_line):
        return False, "충돌 field doesn't enumerate the edit outcome"
    return True, "충돌 field enumerates the edit outcome"


# The retirement clause is pinned VERBATIM, not by pattern. Two review rounds showed why: a
# presence check passed "...ask the user to approve the retirement in a separate prompt of its
# own", and adding a negation pattern then passed "the absorption itself is never a separate
# prompt. The retirement, being destructive, gets its own confirmation question afterwards" —
# #429's rejected design restated, with the negation scoped to the wrong noun. Every pattern is
# a blocklist of the last wording someone tried, and the claim it guards is universal, so the
# contract text itself is the pin. Whitespace is normalised, so a reflow is not a change; an
# added, removed or reworded clause is, and updating this constant is then the deliberate act
# of changing the contract.
#
# ponytail: the ceiling is the bullet boundary — this pins what the verdict says and that
# nothing sits beside it, not what the rest of the skill says about it.
_SUPERSEDE_CONTRACT = """\
- **Supersede (the catalogue's exit path)**: if landing this rule makes an existing entry
  redundant — the new rule states the same obligation at a more general altitude, or the old
  entry's only remaining job is now done by a guard/skill that landed since — do not add a
  second entry. Absorb the old entry's distinguishing content **into the new one** and retire
  the old **in the same write**, so the catalogue never carries both. Show the retirement in the
  §3 confirmation as part of the diff (`Pn retired, absorbed into Pm`) — **never as a separate
  prompt**. **A retired number is never reused.** If the old entry says the same thing at the
  *same* altitude this is a Duplicate instead (strengthen it, add nothing); Supersede needs the
  old entry to have stopped earning its own line.
"""


def check_supersede_verdict_named(skill: str, ref: str) -> tuple[bool, str]:
    """#429: Supersede must be its own outcome, retiring the entry in the same write.

    #663 also pins the SEAM the split created: SKILL.md §6 must still LIST Supersede among its
    verdicts, NAME reference.md §6-supersede-contract, and tell the engine to apply it. A
    pointer that decays into a bare citation is how an on-demand step turns optional — the same
    failure mode test-add-policy-routing.py's `check_scan_command_pointer` guards for the
    §6-snippet split (#469).
    """
    skill_bullet = _bullet_slice(_verdict_scope(skill), "- **Supersede")
    if skill_bullet is None:
        return False, "SKILL.md §6 no longer lists Supersede among its conflict-check verdicts"
    if "§6-supersede-contract" not in skill_bullet:
        return False, (
            "SKILL.md's Supersede bullet doesn't name reference.md §6-supersede-contract as "
            "where the verdict's canonical text lives"
        )
    if not (_states(skill_bullet, "apply it as written")
            or _states(skill_bullet, "read that section")):
        return False, (
            "SKILL.md's Supersede pointer decayed into a bare citation — it must tell the "
            "engine to read and apply §6-supersede-contract, not merely cite it"
        )
    # `_bullet_slice`, not `_bullet_scope`: in the reference section the verdict is the LAST
    # bullet, and `_bullet_scope`'s 600-char fallback window cuts the contract short of its own
    # "never reused" clause. Slicing to the end of the scope is the same boundary the verbatim
    # pin uses, so the two checks read exactly the same span.
    raw = _bullet_slice(_ref_supersede_scope(ref), "- **Supersede")
    if raw is None:
        return False, "Supersede is not named as its own conflict-check outcome"
    bullet_text = raw.lower()
    if "retire" not in bullet_text:
        return False, "Supersede outcome doesn't retire the superseded entry"
    if "same write" not in bullet_text:
        return False, (
            "Supersede doesn't retire in the SAME write — a deferred retirement is how the "
            "catalogue ends up carrying both entries"
        )
    if "never reused" not in bullet_text and "never be reused" not in bullet_text:
        return False, "the retired-number-is-never-reused rule is missing"
    return True, "Supersede named as a distinct §6 outcome, retiring in the same write"


def check_supersede_bullet_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """#429: the whole canonical Supersede verdict matches its pinned contract text.

    This is what carries the 1-click invariant — the retirement never gets a prompt of its
    own — against a contradicting clause added *beside* the negation, which is how both
    pattern-based versions of this check were defeated. #663: the canonical copy is
    reference.md §6-supersede-contract, so the pin reads there.
    """
    if _REFERENCE_TITLE in ref and _REF_SUPERSEDE_SECTION_RE.search(ref) is None:
        return False, "§6-supersede-contract section boundary not found (header drift?)"
    bullet = _bullet_slice(_ref_supersede_scope(ref), "- **Supersede")
    if bullet is None:
        return False, "Supersede outcome missing entirely"
    if _normalise(bullet) != _normalise(_SUPERSEDE_CONTRACT):
        return False, (
            "reference.md §6-supersede-contract no longer matches its pinned contract text — a "
            "clause was added, removed or reworded (including below the bullet, inside the same "
            "section). If that is intended, update _SUPERSEDE_CONTRACT in this file in the same "
            "commit"
        )
    return True, "Supersede verdict matches its pinned contract text verbatim"


def check_confirmation_template_lists_retirement(skill: str, ref: str = "") -> tuple[bool, str]:
    """#429: §3's confirmation template must carry the 은퇴 field."""
    text = skill
    field_pos = text.find("은퇴:")
    if field_pos == -1:
        return False, "은퇴 confirmation field missing from the §3 template"
    # Same line-scoping as the 충돌 check: a later unrelated 은퇴 mention must not
    # validate the wrong text.
    line_end = text.find("\n", field_pos)
    field_line = text[field_pos:line_end if line_end != -1 else len(text)]
    if "none" not in field_line.lower():
        return False, "은퇴 field doesn't offer the no-retirement case"
    return True, "은퇴 field present in the §3 confirmation template"


def check_unused_retirement_verdict(text: str, _ref: str = "") -> tuple[bool, str]:
    """#609: the never-fired exit, with BOTH choices and the recommends-only ceiling.

    Supersede only removes an entry that a NEW rule absorbs, and `lint-catalogue.sh` caps
    the framing but deliberately not the row count — so without this verdict an entry that
    was simply never needed has no exit and the catalogue grows monotonically. Both halves
    are pinned: only offering `delete` turns a narrowing candidate into a removal, and
    dropping the recommends-only ceiling turns a suggestion into an automatic deletion —
    the one direction this engine must never fail in.
    """
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**unused retirement")
    if bullet_text is None:
        return False, "the never-fired retirement is not named as its own §6 outcome"
    if "delete" not in bullet_text:
        return False, "the delete choice is missing from the unused-retirement outcome"
    if "narrow" not in bullet_text:
        return False, "the narrow-the-firing-condition choice is missing (delete is not the only exit)"
    if "recommends only" not in bullet_text:
        return False, "unused retirement doesn't state the recommends-only ceiling — it could auto-delete"
    if "no second prompt" not in bullet_text:
        return False, "unused retirement doesn't ride the one confirmation (a second prompt breaks 1-click)"
    # The anti-silence guard (#609 review). reference.md §6-supersede already rejected
    # usage-based retirement because there is no firing telemetry; a trigger that reads
    # absence of output as non-firing re-opens it with the time window removed and the
    # inference intact, and cannot tell a never-needed rule from a young correct one.
    if "never silence" not in bullet_text and "not silence" not in bullet_text:
        return False, "unused retirement doesn't exclude silence — absence of evidence is not evidence"
    # The delete is irreversible, so the recovery route is part of the verdict, not a detail.
    if "trash-put" not in bullet_text:
        return False, "unused retirement doesn't route its delete through trash-put"
    return True, "unused retirement named with both choices, recommends-only, one confirmation, silence excluded, trash-put"



def check_hook_site_two_forms(text: str, _ref: str = "") -> tuple[bool, str]:
    """#609: §3's hook site names BOTH forms, each with the mechanism that actually exists.

    Before #609 the hook site was bound to blocking only, so a rule whose violation cannot be
    seen in the tool call's arguments but IS reconstructable from what the act leaves behind
    had no home and drifted to the reminder site (the intervention point the Harness-R1
    ablation measured as the second most costly to lose). The mechanisms are asymmetric and
    the asymmetry is the whole point, so both are pinned: PreToolUse is the only event that
    can deny, and PostToolUse can only report through exit 2 + stderr. A recovery form
    documented with PreToolUse fields would send every future recovery rule into a dead end.
    """
    # Scope to the hook SITE bullet. `description:` and the `## Rules` summary also say
    # "blocking or recovery" without any mechanism, so a first-occurrence search would read
    # the frontmatter and pass on a §3 that lost the split entirely.
    bullet = _bullet_scope(text.lower(), "- **hook**")
    if bullet is None:
        return False, "§3's hook site bullet not found"
    if "blocking" not in bullet or "recovery" not in bullet:
        return False, "§3's hook site does not name both the blocking and recovery forms"
    for form, event, field in (("blocking", "pretooluse", "permissiondecision"),
                               ("recovery", "posttooluse", "exit 2")):
        idx = bullet.find(form)
        window = bullet[idx:idx + 220]
        if event not in window:
            return False, f"the {form} form is not paired with {event}"
        if field not in window:
            return False, f"the {form} form does not name {field}"
    return True, "§3's hook site names blocking and recovery, each with its real mechanism"


def check_tier_does_not_mean_blocking(text: str, _ref: str = "") -> tuple[bool, str]:
    """#609: HARD means "deterministically enforced", never "a guard blocks".

    The recovery form auto-fires exactly like blocking and needs no confirmation, so it is an
    ordinary member of HARD — but only under the rewritten definition. If HARD reverts to
    meaning that a guard blocks, recovery becomes an exception with no tier, and the engine
    either invents a second axis (breaking `tier folds into the site`, add-policy's 1-click
    justification) or routes recovery rules back to the reminder site, which is the #609 bug.
    """
    lowered = " ".join(text.lower().split())
    if "tier folds into the site" not in lowered:
        return False, "the 1-click justification (`tier folds into the site`) is gone"
    if "hard ⇒ hook" not in lowered or "soft ⇒ reminder" not in lowered:
        return False, "the tier→site mapping no longer states HARD ⇒ hook / SOFT ⇒ reminder"
    if "deterministically enforced" not in lowered:
        return False, "HARD is not defined as `deterministically enforced` — recovery loses its tier"
    # The old definition may only survive as the thing being denied, never as the claim.
    for phrase in ('hard means "a guard blocks"', "hard means 'a guard blocks'"):
        if phrase in lowered:
            return False, "HARD is still defined as `a guard blocks` — recovery has no tier"
    return True, "HARD means deterministically enforced, and tier still folds into the site"


# ---------------------------------------------------------------------------
# Adjacency + the loaded-body locator (#663)
#
# The verbatim pins above are total over their slices and say nothing about what sits BESIDE
# them. Two escape hatches follow, and each gets an identity pin:
#
#   - reference.md: a new `## §6-supersede-addendum` heading right after §6-supersede-contract
#     parks contradicting text outside every pin while the section still matches byte for byte;
#   - SKILL.md: the always-loaded Supersede locator bullet, which at runtime OUTRANKS the
#     on-demand section it points at. `check_supersede_verdict_named` pins two of its clauses
#     and leaves the rest of the bullet — and both bullets next to it — free.
#
# Neither is a whole-file assertion. Only the immediate neighbours of each pinned region are
# fixed; both files stay free to grow elsewhere.
# ---------------------------------------------------------------------------

_ATX_HEADING_RE = re.compile(r"^#{1,6} ")


def _heading_lines(text: str) -> list[str]:
    """Markdown headings, skipping anything inside a fenced block.

    A bare `startswith("#")` is not enough: reference.md §6-snippet is a bash block whose
    comment lines all start with `#`, and SKILL.md §3's confirmation template is a fenced block
    whose first line is literally `## 분류 결과`. Both would be read as headings and make the
    adjacency pin compare against a comment.
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


def _head(text: str) -> str:
    """A block's identity: its opening, whitespace-normalised and length-bounded.

    Not "its first physical line" — SKILL.md is hard-wrapped, so a reflow moves the first line
    break and a raw first-line identity would read a pure rewrap as an inserted neighbour.
    """
    return _normalise(text)[:80]


def _verdict_bullets(section: str) -> list[str]:
    """§6's verdict bullets, sliced out of the one block that holds them.

    Scoped to that block rather than to the whole section: slicing the LAST bullet to the end
    of §6 would swallow the locator paragraphs that follow it, and then a rewrite of those
    paragraphs would read as a rewrite of the Sibling verdict.
    """
    block = next((p for p in _paragraphs(section) if p.startswith("- **")), "")
    if not block:
        return []
    return [f"- **{part}" if i else part
            for i, part in enumerate(block.split("\n- **"))]


def _bullet_neighbours(section: str, marker: str) -> tuple[str, str]:
    """Openings of the verdict bullets immediately before and after the marked one."""
    bullets = _verdict_bullets(section)
    for i, bullet in enumerate(bullets):
        if bullet.startswith(marker):
            return (_head(bullets[i - 1]) if i > 0 else "",
                    _head(bullets[i + 1]) if i + 1 < len(bullets) else "")
    return ("", "")


# `## \d` and not `## 7\.` specifically: under a `(?=^## 7\.)` boundary an inserted `## 6b.`
# section would stay INSIDE the slice, and no heading-adjacency pin could ever see it. Kept
# separate from `_SECTION_6_RE` above, whose fallback-to-whole-text behaviour the headerless
# bullet fixtures depend on.
_SKILL_SECTION_6_BOUNDED_RE = re.compile(r"^## 6\.\s.*?(?=^## \d)", re.MULTILINE | re.DOTALL)

_SUPERSEDE_MARKER = "- **Supersede (the catalogue's exit path)**"

_SKILL_SUPERSEDE_LOCATOR = _normalise("""\
- **Supersede (the catalogue's exit path)**: a rule that makes an existing entry redundant
  absorbs it and retires it in the **same write**, on the same confirmation — never a separate
  prompt. **Its canonical, binding text is [reference.md](reference.md) §6-supersede-contract —
  read that section and apply it as written; this bullet is a locator, not the contract.**
  Rationale: [reference.md](reference.md) §6-supersede.
""")

_SUPERSEDE_LOCATOR_NEIGHBOURS = (
    "- **Edit (explicit modification of an existing entry)**: if the request clearly ",
    "- **Unused retirement (the other exit, #609)**: absorption above is otherwise th",
)

_REF_SUPERSEDE_NEIGHBOURS = (
    "## §6-gate — why the necessity gate exists, and why it only recommends (#450)",
    "## §6-narrowing — one occurrence narrows the condition, and why there is no counter (#609)",
)

_SKILL_SECTION_6_NEIGHBOURS = (
    "## 5. Inviolability safety mechanism (the engine enforces it)",
    "## 7. Output contract",
)


def check_supersede_section_neighbours(skill: str, ref: str) -> tuple[bool, str]:
    """§6-supersede-contract still sits between its two known reference.md headings."""
    got = _neighbour_headings(_REF_SUPERSEDE_SECTION_RE, ref)
    if got != _REF_SUPERSEDE_NEIGHBOURS:
        return False, (
            "reference.md §6-supersede-contract's neighbouring headings changed — an inserted "
            "sibling section parks contradicting text just outside the pin while the section "
            f"itself still matches. expected {_REF_SUPERSEDE_NEIGHBOURS}, got {got}"
        )
    return True, "reference.md §6-supersede-contract still sits between its two known headings"


def check_skill_supersede_locator_verbatim(skill: str, ref: str = "") -> tuple[bool, str]:
    """The always-loaded SKILL.md Supersede locator bullet matches its pinned text, WHOLE."""
    section = _SKILL_SECTION_6_BOUNDED_RE.search(skill)
    if section is None:
        return False, "SKILL.md `## 6.` section boundary not found (header drift?)"
    bullet = next(
        (b for b in _verdict_bullets(section.group(0)) if b.startswith(_SUPERSEDE_MARKER)), ""
    )
    if not bullet:
        return False, (
            "SKILL.md §6 has no Supersede locator bullet — the always-loaded body no longer "
            "routes the engine to §6-supersede-contract at all"
        )
    if _normalise(bullet) != _SKILL_SUPERSEDE_LOCATOR:
        return False, (
            "SKILL.md §6's Supersede locator no longer matches its pinned text — a clause was "
            "added, removed or reworded. The loaded body outranks the on-demand contract at "
            "runtime, so this bullet is pinned as hard as the section it points at. If the "
            "change is intended, update _SKILL_SUPERSEDE_LOCATOR in this file in the same commit"
        )
    return True, "SKILL.md §6's Supersede locator (loaded body) matches VERBATIM"


def check_skill_supersede_locator_neighbours(skill: str, ref: str = "") -> tuple[bool, str]:
    """Nothing new may be parked immediately beside the locator bullet, or beside §6 itself."""
    section = _SKILL_SECTION_6_BOUNDED_RE.search(skill)
    if section is None:
        return False, "SKILL.md `## 6.` section boundary not found (header drift?)"
    got = _bullet_neighbours(section.group(0), _SUPERSEDE_MARKER)
    if got != _SUPERSEDE_LOCATOR_NEIGHBOURS:
        return False, (
            "the §6 verdict bullets around the Supersede locator changed — a bullet inserted "
            f"beside it sits outside the pin. expected {_SUPERSEDE_LOCATOR_NEIGHBOURS}, "
            f"got {got}"
        )
    headings = _neighbour_headings(_SKILL_SECTION_6_BOUNDED_RE, skill)
    if headings != _SKILL_SECTION_6_NEIGHBOURS:
        return False, (
            "SKILL.md §6's neighbouring headings changed — an inserted sibling section parks "
            f"its text outside the §6 slice. expected {_SKILL_SECTION_6_NEIGHBOURS}, "
            f"got {headings}"
        )
    return True, "SKILL.md §6's Supersede locator still sits between its known bullets and headings"


_CHECKS = [
    check_conflict_preamble_verbatim,
    check_edit_bucket_named,
    check_edit_distinct_from_contradiction,
    check_confirmation_template_lists_edit,
    check_supersede_verdict_named,
    check_supersede_bullet_verbatim,
    check_confirmation_template_lists_retirement,
    check_unused_retirement_verdict,
    check_hook_site_two_forms,
    check_tier_does_not_mean_blocking,
]

# Exercised against the REAL files and `.replace()` mutations of them: the in-memory fixtures
# above are bare bullet fragments with no `## 5.`/`## 7.` neighbours, so they cannot carry an
# identity pin.
_PIN_CHECKS = [
    check_supersede_section_neighbours,
    check_skill_supersede_locator_verbatim,
    check_skill_supersede_locator_neighbours,
]


def run_checks(skill: str, ref: str) -> tuple[int, int]:
    """`skill` is SKILL.md (§6's preamble, the Edit bucket, the §3 template, the Supersede
    pointer); `ref` is reference.md, where the Supersede verdict's canonical text lives since
    #663. Two sources on purpose, not one concatenated blob: a SKILL.md claim must not be
    satisfiable from the reference, or the split's own seam goes unguarded."""
    passed = failed = 0
    for check in _CHECKS + _PIN_CHECKS:
        ok, msg = check(skill, ref)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test (in-memory fixtures) — TWO sources since #663, mirroring the split: §6's preamble,
# the Edit bucket, the §3 template and the Supersede POINTER come from the SKILL.md side; the
# Supersede verdict's canonical text from the reference.md side.
# ---------------------------------------------------------------------------

# The pointer bullet as SKILL.md now carries it, kept as a constant so the decay fixtures below
# cannot silently no-op against a reworded copy.
_SUPERSEDE_POINTER = """\
- **Supersede (the catalogue's exit path)**: a rule that makes an existing entry redundant
  absorbs it and retires it in the **same write**, on the same confirmation — never a separate
  prompt. **Its canonical, binding text is [reference.md](reference.md) §6-supersede-contract —
  read that section and apply it as written; this bullet is a locator, not the contract.**
"""

_PASSING = """\
- **Duplicate**: if the site already states the same rule, strengthen that entry.
- **Edit (explicit modification of an existing entry)**: if the request clearly targets
  one existing entry and asks to change it, treat it as an in-place edit, not a new
  append. Show the entry's before → after text in the §3 confirmation.
%s- **Unused retirement (the other exit, #609)**: positive evidence only — the user says
  outright the entry never came up, never silence. Reminder-site entries only, never a
  user-authored skill. Surfaces
  in the §3 은퇴 field with two choices — delete it, or narrow its firing condition: same
  confirmation, no second prompt, recommends only, no answer means keep, `trash-put` never
  `rm`.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
- **Sibling**: link them with a one-line note.

## 분류 결과
- 충돌: <none | sibling of an existing rule | edits an existing entry (show before→after) | contradicts an existing rule (explain)>
- 은퇴: <none | Pn이 이 규칙에 흡수돼요 — 같은 쓰기에서 은퇴시킬게요>

- **hook** — deterministic auto-enforcement, **HARD**: a guard script + a `hooks` registration
  entry. **Two forms** (#609), by *when* the violation becomes visible: **blocking** =
  PreToolUse + `hookSpecificOutput.permissionDecision: "deny"`; **recovery** = PostToolUse +
  `exit 2`, stderr back to Claude — reports only.
- **skill** — an invocable procedure.

**Tier folds into the site, so the user never picks an axis** (**HARD ⇒ hook, SOFT ⇒
reminder**); the hook's *form* folds the same way — **HARD means "deterministically
enforced", not "a guard blocks"** (#609).
""" % _SUPERSEDE_POINTER

_PASSING_REF = (
    "## §6-supersede-contract — the Supersede verdict, CANONICAL text\n"
    "\n"
    "This section is the contract, not background.\n"
    "\n"
    + _SUPERSEDE_CONTRACT
    + "\n"
    "## §6-supersede — why the exit path is a §6 verdict\n"
)

# Regression of the exact bug #303 reports: only three outcomes, an explicit edit
# request has no first-class path and risks being refused as a Contradiction.
_FAILING = """\
- **Duplicate**: if the site already states the same rule, strengthen that entry
  instead of adding a second (DRY).
- **Contradiction**: if it conflicts with an existing rule, do NOT write — report the
  contradiction to the user and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>" rather than duplicating context.

## 분류 결과
- 충돌: <none | sibling of an existing rule | contradicts an existing rule (explain)>
"""
_FAILING_REF = """\
## §6-memory — why the memory scan is two steps

Nothing here states a Supersede verdict.
"""

# Regression of a narrower bug: the Edit bucket exists, but its own before -> after
# description was silently dropped, while "before"/"after" still appear elsewhere in
# the document as ordinary English (unrelated to the Edit outcome). The check must
# not be fooled by an unrelated match elsewhere in the file.
_EDIT_WITHOUT_BEFORE_AFTER = """\
Verify before writing to the target. After writing, verify the artifact deterministically.

- **Duplicate**: if the site already states the same rule, strengthen that entry.
- **Edit (explicit modification of an existing entry)**: if the request clearly targets
  one existing entry and asks to change it, treat it as an in-place edit, showing the
  entry's rewritten text in the §3 confirmation.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
- **Sibling**: link them with a one-line note.
"""

# Regression pin for the word-boundary fix (#320): a 충돌 line containing "expedited"
# has "edit" as a mid-word substring but doesn't name the edit outcome. The old bare
# substring check ("edit" in field_line) would false-positive-pass this.
_CONFIRMATION_FIELD_SUBSTRING_FALSE_POSITIVE = """\
## 분류 결과
- 충돌: <none | sibling of an existing rule | contradicts an existing rule (expedited review)>
"""


def _mutate(old: str, new: str) -> str:
    """_PASSING with `old` swapped for `new` — and it MUST actually swap something.

    A fixture built with a bare `_PASSING.replace(...)` whose target no longer matches is
    silently a COPY of _PASSING, so the "expect FAIL" case it backs starts passing and the
    mutation it was written to catch goes unguarded. That happened while landing #609: the
    bullet's wording changed and two fixtures became no-ops in the same edit. Fail loudly at
    import time instead.
    """
    mutated = _PASSING.replace(old, new)
    if mutated == _PASSING:
        raise AssertionError(
            "fixture mutation is a no-op — _PASSING no longer contains:\n" + old)
    return mutated


# #609: the never-fired exit offers ONLY delete — the mutation that turns a narrowing
# candidate into a removal, and the reason both choices are pinned rather than "an exit exists".
_UNUSED_DELETE_ONLY = _mutate(
    """two choices — delete it, or narrow its firing condition""",
    """one choice — delete it""",
)

# #609: the ceiling dropped, so the engine removes the entry itself. `add-policy` recommends;
# it never deletes on its own judgment.
_UNUSED_AUTO_DELETES = _mutate(
    """same
  confirmation, no second prompt, recommends only, no answer means keep,""",
    """the engine removes it in the same write.""",
)

# #609 review: the silence guard replaced by the usage threshold reference.md §6-supersede
# already rejected. With no firing telemetry this cannot separate "never needed" from "has
# not come up yet", so a young correct rule gets proposed for deletion.
_UNUSED_SILENCE_TRIGGER = _mutate(
    """positive evidence only — the user says
  outright the entry never came up, never silence.""",
    """it has not fired in months.""",
)

# #609 review: the irreversible half left un-routed. A delete that reaches for `rm` is the
# one failure this verdict cannot walk back (machine-rule P4).
_UNUSED_RM_DELETE = _mutate(
    """no answer means keep, `trash-put` never
  `rm`.""",
    "no answer means keep. Remove it with `rm`.",
)


# #609: the whole split reverted — one hook site, blocking only. Every rule detectable only
# after the fact drifts back to the reminder site, which is the bug the issue was filed on.
_SITE_NO_FORMS = _mutate(
    """**Two forms** (#609), by *when* the violation becomes visible: **blocking** =
  PreToolUse + `hookSpecificOutput.permissionDecision: "deny"`; **recovery** = PostToolUse +
  `exit 2`, stderr back to Claude — reports only.""",
    """PreToolUse + `hookSpecificOutput.permissionDecision: "deny"`.""",
)

# Both forms named, but recovery documented with the blocking mechanism — the dead end this
# check exists for, since PostToolUse carries no permissionDecision at all.
_SITE_RECOVERY_WRONG_EVENT = _mutate(
    """**recovery** = PostToolUse +
  `exit 2`, stderr back to Claude — reports only.""",
    """**recovery** = PreToolUse +
  `hookSpecificOutput.permissionDecision: "ask"`.""",
)

# The pre-#609 tier sentence restored: HARD means a guard blocks, so recovery has no tier and
# the engine must either invent a second axis or route recovery rules back to the reminder.
_SITE_TIER_MEANS_BLOCKS = _mutate(
    """**HARD means "deterministically
enforced", not "a guard blocks"** (#609).""",
    """**HARD means "a guard blocks"**.""",
)


# Supersede exists but defers the retirement to its own confirmation — the design #429
# explicitly rejects, because a second prompt is where a retirement gets skipped.
_SUPERSEDE_SECOND_PROMPT = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write**. Ask the user to confirm the retirement separately.
  **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""

# Supersede that only marks the old entry for later removal. The catalogue carries both
# until someone comes back, which is the monotonic growth #429 measured.
_SUPERSEDE_DEFERRED_WRITE = """\
- **Supersede**: if landing this rule makes an existing entry redundant, note that the old
  entry should be retired, never as a separate prompt. **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""


# The keywords are all present, but the claim is inverted: the retirement gets its own prompt.
# This is the mutation a presence-only check passes, which is what made the check vacuous.
_SUPERSEDE_INVERTED = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write**, shown in the §3 confirmation as part of the diff, and
  then ask the user to approve the retirement in a separate prompt of its own.
  **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""

# The phrase straddles a line break, exactly as it does in the hard-wrapped source. A plain
# substring check reads this as deleted (#440); it must read as stated.
_SUPERSEDE_WRAPPED = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write** — never as a separate
  prompt. **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""


# The mutation that defeated the negation pattern: the negation is scoped to the absorption,
# and the retirement gets its own confirmation anyway. Every keyword and a real negation are
# present; only the verbatim pin sees it. Since #663 it mutates the CANONICAL copy.
_SUPERSEDE_NEGATION_MISPLACED = _PASSING_REF.replace(
    "— **never as a separate\n  prompt**.",
    """— the absorption itself is
  never a separate prompt. The retirement, being destructive, gets its own confirmation
  question afterwards, and the engine waits for that second answer before deleting anything.""",
)

# The same contract with every line break moved. Whitespace is not the contract (#440), so this
# must still read as unchanged — the case that keeps the pin from failing on a pure reflow.
_SUPERSEDE_REFLOWED = _PASSING_REF.replace(
    _SUPERSEDE_CONTRACT, " ".join(_SUPERSEDE_CONTRACT.split())
)

# #663: the section-scoped slice runs to the end of the bullet, and the bullet is the last thing
# in `## §6-supersede-contract`, so non-bullet prose parked below it lands INSIDE the pin. This
# is the mutation the split made possible, and the case that proves it is covered.
_SUPERSEDE_TRAILING_CLAUSE = _PASSING_REF.replace(
    "\n## §6-supersede — why the exit path is a §6 verdict",
    "\nA verdict that *removes* an entry is destructive, so it is confirmed on its own second\n"
    "question, separately from the §3 addition.\n\n"
    "## §6-supersede — why the exit path is a §6 verdict",
)


# Every fixture above is a bare bullet fragment, so all of them take the fallback branch of the
# scope helpers. These two carry the headers, so the reference-side slice itself is tested here:
# reference.md §8's own `- **Supersede**:` bullet is the decoy the scoping exists for.
_REF_SECTIONS = """\
## §6-supersede-contract — the Supersede verdict, CANONICAL text

%s
## §6-supersede — why the exit path is a §6 verdict

## §8 — the per-site self-check checklist

- **Supersede**: the retired entry is gone from the index and no inbound link points at it.
"""

# The contract section holds the real verdict; §8's decoy sits after it. The scoped slice must
# read the contract section's.
_SCOPED_OK = _REF_SECTIONS % (_SUPERSEDE_CONTRACT + "\n")

# The verdict deleted, §8's decoy left in place. Without scoping the marker search retargets to
# §8 and the suite reports the wrong defect (or, worse, a near-miss it can rationalise).
_SCOPED_VERDICT_DELETED = _REF_SECTIONS % ""

assert _SCOPED_OK != _SCOPED_VERDICT_DELETED, "scoped fixtures collapsed to the same text"

# Heading drift on a document that IS the real reference file (it carries the title line), so
# the precondition must name the boundary instead of falling back to a whole-file match — where
# §8's decoy bullet would be the slice and the failure would be misreported.
_REF_HEADING_DRIFT = (_REFERENCE_TITLE + "\n\n" + _SCOPED_OK).replace(
    "## §6-supersede-contract —", "## §6 supersede contract —"
)


# The #663 seam, from the SKILL.md side: the pointer bullet is the only thing left in the body
# that reaches the contract, so its decay modes get fixtures of their own.
_POINTER_DROPPED = _PASSING.replace(
    "**Its canonical, binding text is [reference.md](reference.md) §6-supersede-contract —\n"
    "  read that section and apply it as written; this bullet is a locator, not the contract.**",
    "**A retired number is never reused.**",
)
_POINTER_BARE_CITATION = _PASSING.replace(
    "—\n  read that section and apply it as written; this bullet is a locator, not the contract.**",
    "(background reading).**",
)
_POINTER_BULLET_DELETED = _PASSING.replace(_SUPERSEDE_POINTER, "")


_PREAMBLE_OK = (
    _PREAMBLE_CONTRACT
    + "\n- **Duplicate**: if the site already states the same rule, strengthen that entry.\n"
    + _SUPERSEDE_POINTER
    + "\n\n## 7. Output contract\n"
)
# Review's round-3 mutation, verbatim: a second question granted above the bullets.
_PREAMBLE_CONTRADICTED = _PREAMBLE_OK.replace(
    "Otherwise read the",
    "A verdict that *removes* an entry is destructive, so it is confirmed on its own second\n"
    "question, separately from the §3 addition.\n\nOtherwise read the",
)
_PREAMBLE_REFLOWED = _PREAMBLE_OK.replace(
    _PREAMBLE_CONTRACT, " ".join(_PREAMBLE_CONTRACT.split())
)
# A clause slipped between the pinned preamble and the first bullet — the region a
# content-addressed end boundary used to surrender whenever anything bullet-shaped appeared
# above the real list. The contract-derived boundary must red it, and say WHERE it drifted.
#
# ponytail: a decoy that is itself a top-level bullet lands BELOW this boundary, in the
# unpinned verdict-list region, and passes. That is the documented ceiling (see the module
# docstring), not something this boundary can close — pinning it means pinning all of §6.
_PREAMBLE_DECOY_BULLET = _PREAMBLE_OK.replace(
    "- **Duplicate**:",
    "A verdict that *removes* an entry is confirmed on its own second question.\n\n"
    "- **Duplicate**:",
)
# The benign refactor with the same effect: the first bullet is renamed, not moved.
_PREAMBLE_SPLIT_BULLET = _PREAMBLE_OK.replace(
    "- **Duplicate**:", "- **Duplicate (same rule)**:"
)
# The other insertion point: directly under the `## 6.` heading, above the contract's first
# paragraph. Also an insertion, and it must not be reported as a stale constant.
_PREAMBLE_PREPENDED = _PREAMBLE_OK.replace(
    "**New site**:",
    "A verdict that *removes* an entry is confirmed on its own second question.\n\n"
    "**New site**:",
)


# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of its
# base, and an expect-FAIL case on a copy of the base would then be testing nothing.
for _name, _fixture, _base in (
    ("_SUPERSEDE_NEGATION_MISPLACED", _SUPERSEDE_NEGATION_MISPLACED, _PASSING_REF),
    ("_SUPERSEDE_REFLOWED", _SUPERSEDE_REFLOWED, _PASSING_REF),
    ("_SUPERSEDE_TRAILING_CLAUSE", _SUPERSEDE_TRAILING_CLAUSE, _PASSING_REF),
    ("_POINTER_DROPPED", _POINTER_DROPPED, _PASSING),
    ("_POINTER_BARE_CITATION", _POINTER_BARE_CITATION, _PASSING),
    ("_POINTER_BULLET_DELETED", _POINTER_BULLET_DELETED, _PASSING),
    ("_REF_HEADING_DRIFT", _REF_HEADING_DRIFT, _REFERENCE_TITLE + "\n\n" + _SCOPED_OK),
    ("_PREAMBLE_PREPENDED", _PREAMBLE_PREPENDED, _PREAMBLE_OK),
    ("_PREAMBLE_DECOY_BULLET", _PREAMBLE_DECOY_BULLET, _PREAMBLE_OK),
    ("_PREAMBLE_SPLIT_BULLET", _PREAMBLE_SPLIT_BULLET, _PREAMBLE_OK),
    ("_PREAMBLE_CONTRADICTED", _PREAMBLE_CONTRADICTED, _PREAMBLE_OK),
    ("_PREAMBLE_REFLOWED", _PREAMBLE_REFLOWED, _PREAMBLE_OK),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


# ---------------------------------------------------------------------------
# #663 adjacency mutations, built by `.replace()` off the REAL files rather than typed by hand:
# a hand-copied base drifts silently and its expect-FAIL case then tests nothing. Same guard
# loop as everything above.
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL_PATH.read_text(encoding="utf-8")
_CLEAN_REF = _REFERENCE_PATH.read_text(encoding="utf-8")

# THE ESCAPE HATCH the verbatim pin cannot close on its own: contradicting text parked in a NEW
# sibling section placed immediately after §6-supersede-contract. The bullet still matches byte
# for byte — the slice ends at the new heading — and every other check passes. This is #429's
# rejected design, reinstated from just outside the pin.
_REF_SUPERSEDE_ADDENDUM_INSERTED = _CLEAN_REF.replace(
    "\n## §6-narrowing — one occurrence narrows the condition",
    "\n## §6-supersede-addendum\n\nA verdict that *removes* an entry is destructive, so it is\n"
    "confirmed on its own second question, separately from the §3 addition.\n\n"
    "## §6-narrowing — one occurrence narrows the condition",
)

# The same trick on the always-loaded side: a new verdict bullet inserted right after the
# Supersede locator, and a whole sibling section right after §6.
_SKILL_ADJACENT_BULLET = _CLEAN_SKILL.replace(
    "\n- **Unused retirement (the other exit, #609)**",
    "\n- **Deferred retirement**: when the absorption is large, retire the old entry on a\n"
    "  follow-up confirmation instead.\n"
    "- **Unused retirement (the other exit, #609)**",
)
_SKILL_SIBLING_SECTION = _CLEAN_SKILL.replace(
    "\n## 7. Output contract",
    "\n## 6b. Conflict check — addendum\n\nA retirement is destructive, so confirm it on its\n"
    "own second question.\n\n## 7. Output contract",
)

# The locator itself corrupted while both substring anchors survive: it still names
# §6-supersede-contract and still says to apply it as written, so
# `check_supersede_verdict_named` stays green — the 1-click invariant is what dies.
_SKILL_LOCATOR_GRANTS_SECOND_PROMPT = _CLEAN_SKILL.replace(
    "absorbs it and retires it in the **same write**, on the same confirmation — never a separate\n  prompt.",
    "absorbs it and retires it in a follow-up write, on its own second confirmation.",
)
# The locator's caveat deleted: the bullet reads as a usable summary rather than a locator, so
# an engine acts from it and never opens the contract.
_SKILL_LOCATOR_CAVEAT_DELETED = _CLEAN_SKILL.replace(
    "; this bullet is a locator, not the contract.", ".",
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
    ("_REF_SUPERSEDE_ADDENDUM_INSERTED", _REF_SUPERSEDE_ADDENDUM_INSERTED, _CLEAN_REF),
    ("_SKILL_ADJACENT_BULLET", _SKILL_ADJACENT_BULLET, _CLEAN_SKILL),
    ("_SKILL_SIBLING_SECTION", _SKILL_SIBLING_SECTION, _CLEAN_SKILL),
    ("_SKILL_LOCATOR_GRANTS_SECOND_PROMPT", _SKILL_LOCATOR_GRANTS_SECOND_PROMPT, _CLEAN_SKILL),
    ("_SKILL_LOCATOR_CAVEAT_DELETED", _SKILL_LOCATOR_CAVEAT_DELETED, _CLEAN_SKILL),
    ("_SKILL_REFLOWED", _SKILL_REFLOWED, _CLEAN_SKILL),
    ("_REF_REFLOWED", _REF_REFLOWED, _CLEAN_REF),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

# (case, skill, ref, expect the PIN layer to pass, expect the pre-#663 check layer to pass)
_CANONICAL_CASES: list[tuple[str, str, str, bool, bool]] = [
    ("the real SKILL.md + reference.md pass every pin", _CLEAN_SKILL, _CLEAN_REF, True, True),
    ("a new `## §6-supersede-addendum` sibling grants the retirement its own prompt -> FAIL",
     _CLEAN_SKILL, _REF_SUPERSEDE_ADDENDUM_INSERTED, False, True),
    ("a new verdict bullet parked right after the Supersede locator -> FAIL",
     _SKILL_ADJACENT_BULLET, _CLEAN_REF, False, True),
    ("a new `## 6b.` sibling section parked right after §6 -> FAIL",
     _SKILL_SIBLING_SECTION, _CLEAN_REF, False, True),
    ("the loaded-body locator grants the retirement a second prompt -> FAIL",
     _SKILL_LOCATOR_GRANTS_SECOND_PROMPT, _CLEAN_REF, False, True),
    ("the loaded-body locator drops its `this is a locator` caveat -> FAIL",
     _SKILL_LOCATOR_CAVEAT_DELETED, _CLEAN_REF, False, True),
    ("both files reflowed still pass (whitespace is not the contract)",
     _SKILL_REFLOWED, _REF_REFLOWED, True, True),
]


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    # _PASSING/_FAILING are bare bullet fragments with no `## 6.`/`## 7.` headers, so the
    # §6-scoped preamble pin cannot run against them; it has its own headered fixtures below.
    bullet_checks = [c for c in _CHECKS if c is not check_conflict_preamble_verbatim]

    for check in bullet_checks:
        ok, _ = check(_PASSING, _PASSING_REF)
        cases.append((f"passing: {check.__name__}", ok))

    for check in bullet_checks:
        ok, _ = check(_FAILING, _FAILING_REF)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_edit_bucket_named(_EDIT_WITHOUT_BEFORE_AFTER)
    cases.append(("edit-without-before-after: check_edit_bucket_named (expect FAIL)", not ok))

    ok, _ = check_confirmation_template_lists_edit(_CONFIRMATION_FIELD_SUBSTRING_FALSE_POSITIVE)
    cases.append(("substring-false-positive: check_confirmation_template_lists_edit (expect FAIL)", not ok))

    ok, _ = check_supersede_verdict_named(_PASSING, _SUPERSEDE_SECOND_PROMPT)
    cases.append(("supersede-second-prompt: check_supersede_verdict_named (still OK)", ok))

    ok, _ = check_supersede_verdict_named(_PASSING, _SUPERSEDE_DEFERRED_WRITE)
    cases.append(("supersede-deferred-write: check_supersede_verdict_named (expect FAIL)", not ok))

    ok, _ = check_supersede_verdict_named(_PASSING, _SUPERSEDE_WRAPPED)
    cases.append(("supersede-wrapped: check_supersede_verdict_named (still OK)", ok))

    # #663: every one of these corrupts the CANONICAL copy, which is reference.md's.
    for name, fixture in (
        ("inverted", _SUPERSEDE_INVERTED),
        ("second-prompt", _SUPERSEDE_SECOND_PROMPT),
        ("deferred-write", _SUPERSEDE_DEFERRED_WRITE),
        ("negation-on-the-wrong-noun", _SUPERSEDE_NEGATION_MISPLACED),
        ("clause-parked-below-the-bullet", _SUPERSEDE_TRAILING_CLAUSE),
    ):
        ok, _ = check_supersede_bullet_verbatim(_PASSING, fixture)
        cases.append((f"reference.md supersede-{name}: check_supersede_bullet_verbatim (expect FAIL)", not ok))

    ok, _ = check_supersede_bullet_verbatim(_PASSING, _SUPERSEDE_REFLOWED)
    cases.append(("supersede-reflowed: check_supersede_bullet_verbatim (still OK)", ok))

    # The seam #663 created: SKILL.md's §6 must keep a live pointer at the canonical text.
    for name, skill_fixture in (
        ("pointer-dropped", _POINTER_DROPPED),
        ("pointer-bare-citation", _POINTER_BARE_CITATION),
        ("pointer-bullet-deleted", _POINTER_BULLET_DELETED),
    ):
        ok, _ = check_supersede_verdict_named(skill_fixture, _PASSING_REF)
        cases.append((f"{name}: check_supersede_verdict_named (expect FAIL)", not ok))

    ok, _ = check_unused_retirement_verdict(_UNUSED_DELETE_ONLY, _PASSING_REF)
    cases.append(("unused-delete-only: check_unused_retirement_verdict (expect FAIL)", not ok))
    ok, _ = check_unused_retirement_verdict(_UNUSED_AUTO_DELETES, _PASSING_REF)
    cases.append(("unused-auto-deletes: check_unused_retirement_verdict (expect FAIL)", not ok))
    ok, _ = check_supersede_bullet_verbatim(_UNUSED_AUTO_DELETES, _PASSING_REF)
    cases.append(("unused-auto-deletes: check_supersede_bullet_verbatim (still OK)", ok))
    ok, _ = check_unused_retirement_verdict(_UNUSED_SILENCE_TRIGGER, _PASSING_REF)
    cases.append(("unused-silence-trigger: check_unused_retirement_verdict (expect FAIL)", not ok))
    ok, _ = check_unused_retirement_verdict(_UNUSED_RM_DELETE, _PASSING_REF)
    cases.append(("unused-rm-delete: check_unused_retirement_verdict (expect FAIL)", not ok))

    ok, _ = check_hook_site_two_forms(_SITE_NO_FORMS, _PASSING_REF)
    cases.append(("site-no-forms: check_hook_site_two_forms (expect FAIL)", not ok))
    ok, _ = check_hook_site_two_forms(_SITE_RECOVERY_WRONG_EVENT, _PASSING_REF)
    cases.append(("site-recovery-wrong-event: check_hook_site_two_forms (expect FAIL)", not ok))
    ok, _ = check_tier_does_not_mean_blocking(_SITE_TIER_MEANS_BLOCKS, _PASSING_REF)
    cases.append(("site-tier-means-blocks: check_tier_does_not_mean_blocking (expect FAIL)", not ok))
    ok, _ = check_tier_does_not_mean_blocking(_SITE_NO_FORMS, _PASSING_REF)
    cases.append(("site-no-forms: check_tier_does_not_mean_blocking (still OK — tier wording intact)", ok))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_OK)
    cases.append(("preamble: check_conflict_preamble_verbatim (still OK)", ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_CONTRADICTED)
    cases.append(("preamble-grants-a-second-question: check_conflict_preamble_verbatim (expect FAIL)", not ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_DECOY_BULLET)
    cases.append(("preamble-clause-before-the-bullets (expect FAIL)", not ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_PREPENDED)
    cases.append(("preamble-clause-above-the-contract (expect FAIL)", not ok))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_SPLIT_BULLET)
    cases.append((
        "preamble-renamed-first-bullet: span must not shrink (still OK)", ok,
    ))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_REFLOWED)
    cases.append(("preamble-reflowed: check_conflict_preamble_verbatim (still OK)", ok))
    ok, _ = check_conflict_preamble_verbatim(_PASSING)
    cases.append(("preamble: headerless fixture reports the boundary (expect FAIL)", not ok))

    ok, _ = check_supersede_bullet_verbatim(_PASSING, _SCOPED_OK)
    cases.append(("scoped: check_supersede_bullet_verbatim reads the contract section's verdict (still OK)", ok))
    ok, msg = check_supersede_bullet_verbatim(_PASSING, _SCOPED_VERDICT_DELETED)
    cases.append(("scoped: verdict deleted must not retarget to §8's bullet (expect FAIL)",
                  (not ok) and "missing entirely" in msg))
    ok, msg = check_supersede_bullet_verbatim(_PASSING, _REF_HEADING_DRIFT)
    cases.append(("header-drift (§6-supersede-contract renamed): names the boundary (expect FAIL)",
                  (not ok) and "boundary not found" in msg))

    # #663: adjacency + the loaded-body locator, against the real files and mutations of them.
    # The second assertion per case is the point of the layer — every one of these is INVISIBLE
    # to the pre-#663 checks, verbatim `_SUPERSEDE_CONTRACT` pin included.
    for desc, skill_text, ref_text, expect_pin, expect_old in _CANONICAL_CASES:
        got = all(ok for ok, _ in (check(skill_text, ref_text) for check in _PIN_CHECKS))
        cases.append((f"pin: {desc}", got == expect_pin))
        old = all(ok for ok, _ in (check(skill_text, ref_text) for check in _CHECKS))
        cases.append((
            f"pin: {desc} — pre-#663 checks alone "
            f"{'stay green' if expect_old else 'also red'}",
            old == expect_old,
        ))

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

    print(f"Checking: {_SKILL_PATH}\n          {_REFERENCE_PATH} (Supersede contract, #663)\n")
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
    print(f"OK: all {passed} add-policy-conflict-edit checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
