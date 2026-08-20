#!/usr/bin/env python3
"""test-judge-rubric-anchors.py — pins adversarial-review's Judge Rubric anchors (#610/#663).

WHY THIS EXISTS. #610 added 0–10 anchor definitions to the Judge Rubric so the scale stops
inflating ("without anchors, everything scores 85").

WHERE THE ANCHORS LIVE, and why it matters to what gets pinned. The **table is in the SKILL.md
body**, at the Judge Rubric, because that is the file loaded into context at scoring time: nothing
at runtime forces an on-demand read of a reference doc, and no test can observe whether one
happened, so a table parked behind a pointer would leave the scale unanchored exactly as before
#610 with the suite green. `reference/patterns.md` § Judge Rubric Anchors carries the framing the
table cannot state on its own — what the anchors judge, and how to score between two of them —
and the body's binding pointer routes to it (#663's split logic applies to the framing, not to the
operative scale).

Four things are pinned, and each fails differently if unpinned:

1. The anchor rows, verbatim in the SKILL.md body — the operative scale.
2. The framing in `reference/patterns.md`: the scoring OBJECT ("the defense") and the
   interpolation rule. Rewriting "the defense" into "the attack" inverts the polarity of every
   anchor row while all five row pins still match verbatim.
3. The "anchors are not a measurement" caveat in the SKILL.md body. It lives next to the
   arbitrary 50% start it qualifies; deleting it turns a display band back into a fake metric.
4. The body's BINDING pointer, pinned by SECTION name, not by the bare path. `reference/
   patterns.md` is already cited five other times in the body, so a path-only check stays true
   even after the Judge-step pointer is deleted — and a framing the Judge is never told to read
   means the polarity contract lands in name only.

The prose moved out of the body under the same #663 split (`reference/rationale.md`) is pinned
here too: always split, never trim, and a moved paragraph keeps its guard.

A second, independent contract lives in this same file since #691: the Phase 0.5 Vault Decision
Grounding procedure (the one-shot `vault-searcher` call's 5 step constraints and its
graceful-degrade fallback) moved out of the SKILL.md body into `reference/patterns.md § Vault
Decision Grounding Procedure`, the same shape as the #663 split above — SKILL.md keeps a
read-and-apply pointer, patterns.md carries the operative text, pinned whole-section so a blurred
step or a dropped fallback branch reds.

WHAT THESE PINS DO AND DO NOT COVER. The mechanism is whole-block / whole-section verbatim
equality (whitespace-normalised) plus a heading-set assertion on the file that is wholly contract.

Covered — the threat model, and the one #609 actually measured: silent loss or rewrite of the
contract text during ordinary editing. A trimmed head or tail sentence, a rewritten number, a
blurred anchor row, a pointer decaying into a citation, a clause appended inside a pinned region,
and a new sibling section in `rationale.md` all red.

NOT covered: contradicting prose parked in an unpinned region ADJACENT to a pinned one — the line
immediately above a block, the top of the following section, or anything under a non-contract
heading in the same file. Pins leak outward by exactly one step at whatever granularity they use;
clause pins leaked to the next clause, section pins to the next section, adjacency pins to one
line above. The only fixed point is whole-FILE verbatim equality.

# ponytail: the ceiling is whole-file equality, deliberately not taken — it makes every ordinary
# reflow of a SKILL.md a two-file commit, which costs more than the residual risk. Upgrade path if
# a real incident ever lands in an adjacent unpinned region: pin the whole file and accept the
# two-file commit, or move the contract out of the churny file entirely.

Usage:
    python3 thinking-tools/scripts/test/test-judge-rubric-anchors.py [--self-test]

Exit codes: 0 = clean, 1 = a pinned contract drifted.
"""
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SKILL = _HERE.parent.parent / "skills" / "adversarial-review" / "SKILL.md"
_PATTERNS = _SKILL.parent / "reference" / "patterns.md"
_RATIONALE = _SKILL.parent / "reference" / "rationale.md"

errors = []


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


def _reflow(text: str) -> str:
    """Join wrapped lines within each paragraph, keeping blank lines (and so headings) intact."""
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


def _section(text: str, heading: str, level: str = "## ") -> str:
    """Slice one heading's section, from the heading to the NEXT heading, normalised.

    Scoped by heading, in the shape of test-add-policy-necessity-gate.py's `_gate_block`: a copy
    of the same prose pasted into a neighbouring section is not the section being compared. The
    slice runs to the next heading of the same-or-shallower depth (or EOF) so nothing can be
    parked inside the pin's blind spot. Returns "" when the heading is gone, which reds as
    loudly as an edit.
    """
    end = "|".join(re.escape("#" * n + " ") for n in range(1, len(level)))
    match = re.search(
        rf"^{re.escape(level)}{re.escape(heading)}\s*$.*?(?=^(?:{re.escape(level)}|{end})|\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    return _normalise(match.group(0)) if match else ""


def _block(text: str, start_marker: str) -> str:
    """Slice from a bold in-body marker to the next heading of ANY depth, normalised.

    The SKILL.md contract blocks are not their own headings — `**Judge Rubric**` sits inside
    `### Phase 1`. Same idea as `_gate_block`'s `_GATE_START`: anchor on the block's own marker,
    end at the next heading so a clause parked below the block is inside the pin.
    """
    idx = text.find(start_marker)
    if idx == -1:
        return ""
    tail = text[idx:]
    end = re.search(r"^#{1,6} ", tail, re.MULTILINE)
    return _normalise(tail[: end.start()] if end else tail)


def _headings(text: str) -> list:
    """Every heading at EVERY depth, marker included, in document order.

    Level-agnostic on purpose (`test-mode-compose.py`'s `_neighbour_headings` does the same with
    `ln.startswith("#")`). A `## `-only enumeration left `# ` as a free escape hatch: an h1 wedged
    between two pinned sections is outside every slice AND invisible to a `## ` heading-set
    assertion, so arbitrary contradicting prose could be parked under it with the suite green.
    """
    return [h.strip() for h in re.findall(r"^(#{1,6} .+?)\s*$", text, re.MULTILINE)]


def _next_heading(text: str, heading: str) -> str:
    """The heading immediately after `heading` at ANY depth, or "" if missing / last."""
    found = _headings(text)
    if heading not in found:
        return ""
    idx = found.index(heading)
    return found[idx + 1] if idx + 1 < len(found) else ""


def _cited_sections(text: str) -> set:
    """Every `rationale.md § <name>` citation in the body, normalised, parens stripped.

    These were markdown links until the token budget forced plain text; nothing then checked that
    a cited name still matched a real heading, and two had silently lost their issue suffixes.
    """
    # One level of nesting allowed, because a heading may carry an issue suffix: the citation
    # `(… rationale.md § Attacker angle input (#423))` must yield the whole name, not stop at
    # the `)` of `(#423)` — that truncation is exactly the drift this check exists to catch.
    return set(re.findall(r"rationale\.md § ((?:[^()]|\([^()]*\))+)", _normalise(text)))


# ---------------------------------------------------------------------------
# The two CONTRACT BLOCKS in the SKILL.md body, pinned WHOLE. This is the one place the Judge
# actually reads at scoring time, and row-only pins left everything around the rows open: the
# caption could be flipped to "Score the attack against these anchors" (the byte-identical
# inversion in patterns.md reds via `_SCORING_OBJECT`, but here it passed), a sixth row could be
# appended, and "Anchors are advisory only." could be parked above the table — all green.
#
# The "SKILL.md bodies churn, so no whole-file equality" exemption still holds for the file, and
# does NOT hold for these two blocks: they are contracts that changed exactly once, in this
# commit. The body's header states which blocks are pinned and which are not.
# ---------------------------------------------------------------------------

_JUDGE_RUBRIC_START = "**Judge Rubric** (3 elements per round)"

# The role-label rule. It spent one round in rationale.md, which declares itself non-operative —
# an instruction parked there is an instruction the skill is told not to apply. Back in the body,
# and pinned there so it cannot drift out again unnoticed.
_ROLE_LABEL_RULE = _normalise("""
The fixed role labels — Attacker, Judge, Steelman Coach — are roles, not domain personas; they are
never selected from the pool and never change per topic
""")

# The Phase 0.5 ceiling. rationale.md used to restate the same figure, so the two could silently
# disagree with only the non-operative copy guarded; the restatement is gone and the body is now
# the sole source, pinned here.
_VAULT_BUDGET = _normalise("""
keeps this step within **≤ +1500 tokens** of Phase 1 overhead. Do not exceed this budget — never
re-query per round, never request full notes.
""")

_JUDGE_RUBRIC_BLOCK = _normalise("""
**Judge Rubric** (3 elements per round): Relevance (0–10), Substance (0–10), Completeness (0–10).
Score delta: 25–30 → +15%, 18–24 → +8%, 10–17 → 0%, 0–9 → −10% per dimension.
Score every element against these anchors — an unanchored 0–10 scale inflates until everything lands at 8 (#610):

| Score | Anchor |
|-------|--------|
| 0–2 | Non-answer: evasion, silence, or a reply that never reaches the attack |
| 3 | Restates the claim with no supporting evidence |
| 5 | Engages the point at issue, but brings no new evidence |
| 8 | Rebuts that specific point of the attack with concrete evidence |
| 10 | Dismantles the attack's own premise |

Before scoring each round, read and apply § Judge Rubric Anchors in
[reference/patterns.md](reference/patterns.md#judge-rubric-anchors) as written — that section is the
binding contract for **what** these anchors judge and how to score between two of them.
""")

_SURVIVAL_BLOCK = _normalise("""
### Survival Score

Weighted average of 4 dimension scores (each 0–100%):

```
Survival Score = (Logical Integrity × 0.30) + (Evidence × 0.25) + (Counter-resilience × 0.25) + (Scope Robustness × 0.20)
```

All dimensions start at 50%. Score updates after every Judge evaluation. Display as qualitative resilience band (탄탄/보통/취약) in STATE block.

The Judge Rubric anchors buy judging consistency; they do NOT make Survival Score a measurement — the 50% start is still arbitrary (#610). Read the score as a resilience band, never as a measured quantity.

Qualitative bands (mirroring verdict thresholds): **탄탄** (Survived, ≥60%) | **보통** (Pending, 26–59%) | **취약** (Collapsed, ≤25%)
""")

# The five rows keep their own pins on top of the block compare: each blurred anchor is a distinct
# failure mode, and "row 8 changed" is a better diagnostic than "the Judge Rubric block changed".
_ANCHOR_ROWS = [
    "| 0–2 | Non-answer: evasion, silence, or a reply that never reaches the attack |",
    "| 3 | Restates the claim with no supporting evidence |",
    "| 5 | Engages the point at issue, but brings no new evidence |",
    "| 8 | Rebuts that specific point of the attack with concrete evidence |",
    "| 10 | Dismantles the attack's own premise |",
]

# ---------------------------------------------------------------------------
# The framing in reference/patterns.md, pinned WHOLE. Sentence-level pins were tried here first
# and did not converge: extending each one to its paragraph's tail closed the trim from the right
# and left the mirror-image trim from the left green. Every partial anchor leaves a region for the
# next one, so the section's own text is the pin and the comparison is total (the pattern
# `_GATE_CONTRACT` in feedback-loop/scripts/test/test-add-policy-necessity-gate.py already uses).
# Whitespace is normalised: a reflow is not a change, an edit to the words is — and updating this
# constant is then the deliberate act of changing the contract, in the same commit.
# ---------------------------------------------------------------------------

_ANCHOR_FRAMING = _normalise("""
## Judge Rubric Anchors

**This section is a pinned contract, not background.** It is compared WHOLE and verbatim
(whitespace-normalised) against `_ANCHOR_FRAMING` in
`thinking-tools/scripts/test/test-judge-rubric-anchors.py`; the slice runs from this heading to the
next one, so nothing may be parked *inside* it — text placed after the next heading is outside the
pin, and only the immediate adjacency with § Judge Score Delta Mapping is separately guarded.
Editing this section is a deliberate contract change, made in the same commit as that constant.

**Canonical framing (#610).** The anchor table itself lives in `SKILL.md` Phase 1 § Judge Rubric —
in the loaded body, where the Judge actually scores, so no on-demand read stands between the Judge
and the scale. This section is the binding contract for the two things the table cannot state on
its own: what the anchors judge, and how to score between two of them. `SKILL.md` points here; the
Judge reads and applies it at the moment it scores a round.

**What is scored**: each of the three elements (Relevance, Substance, Completeness) is scored by
judging **the defense** against the attack it answers — never the attack, and never the claim in
the abstract. Inverting that object flips the meaning of every anchor row.

**Between anchors**: scores between two anchors interpolate (6–7 = more than engagement, short of a
concrete rebuttal). Anchor to the nearest description rather than inventing a new criterion for the
gap.

---
""")

# Kept as its OWN pin on top of the whole-section compare, because it is the one clause with a
# distinct failure mode worth a distinct diagnostic: flipping "the defense" to "the attack" inverts
# the polarity of all five anchor rows while every row still matches verbatim. The section compare
# would red too, but with a message that says only "the framing changed".
_SCORING_OBJECT = _normalise("""
each of the three elements (Relevance, Substance, Completeness) is scored by judging **the
defense** against the attack it answers — never the attack, and never the claim in the abstract
""")

# ---------------------------------------------------------------------------
# The #610 caveat — canonical copy in the SKILL.md body, next to the 50% start it qualifies.
# ---------------------------------------------------------------------------

_NOT_A_MEASUREMENT = _normalise("""
The Judge Rubric anchors buy judging consistency; they do NOT make Survival Score a measurement —
the 50% start is still arbitrary (#610).
""")

# ---------------------------------------------------------------------------
# The body's binding pointer at the Judge step. Pinned by section name + the read-and-apply verb,
# never by the path alone (the path appears five other times as an ordinary citation).
# ---------------------------------------------------------------------------

_POINTER = _normalise("""
Before scoring each round, read and apply § Judge Rubric Anchors in
[reference/patterns.md](reference/patterns.md#judge-rubric-anchors) as written — that section is the
binding contract for **what** these anchors judge and how to score between two of them.
""")

# ---------------------------------------------------------------------------
# Rationale moved out of the body by the same #663 split. Unpinned before the move (it was body
# prose no test read); pinned now, because that is what makes the move a split and not a trim.
#
# WHOLE-SECTION EQUALITY, for the same reason `_ANCHOR_FRAMING` above is. Sentence-level pins were
# tried across two review rounds: the first stopped at the headline clause and a tail trim passed;
# extending every pin to its paragraph's tail then let the mirror-image head trim pass — deleting
# a section's FIRST sentence (the roles-are-not-domain-personas rule, the #489 shell-scan clause)
# and rewriting `≤ +1500 tokens` into `≤ +15000 tokens` were all green. That does not converge one
# sentence at a time, so each section's own text is the pin, compared total, heading included.
# ---------------------------------------------------------------------------

_RATIONALE_SECTIONS = {
    "Attacker angle input (#423)": """
## Attacker angle input (#423)

The Steelman is model-authored, so selecting from it would make the angle vary run-to-run on one
claim (measured 2026-07-22, #423) and break the shared-input guarantee with `expert-panel`. The
domain does not change between a claim and its steelmanned form; only the framing does, and framing
is what shifted the selection.
""",
    # The RULE (labels never selected from the pool, never change per topic) went back to the
    # loaded body: rationale.md declares itself non-operative, so an instruction parked here is an
    # instruction the skill is told not to apply. Only the why stays.
    "Shared-pool contact point": """
## Shared-pool contact point

Both skills run the rule on that same original text and every cut starts at rank 1, so the two
point at the same pool entry for a given claim. (The rule itself — the fixed role labels are never
selected from the pool and never change per topic — stays in the loaded body, where the skill can
act on it.)
""",
    "Angle recovery after compaction": """
## Angle recovery after compaction

The Selection Rule's input is the submitted claim rather than the Steelman partly for this reason:
a compacted session may no longer hold the Steelman verbatim, while the original topic text is
recoverable.
""",
    "Single-claim cache sizing": """
## Single-claim cache sizing

The Phase 0.5 one-shot call is sized for the typical **single-claim** session. Reusing the first
claim's cache across later claims preserves the token budget at the cost of not surfacing
claim-specific decisions for subsequent claims.
""",
    "Backlog prefilter cost": """
## Backlog prefilter cost

The Phase 0 scan is one deterministic shell scan of the open+closed issue corpus (same script
`build-spec` Phase 0 uses, #489), separate from Phase 0.5's vault-searcher token budget.

A surfaced conflict is never a forced verdict, because the claim can still survive a known
conflict — it just cannot survive one the Attacker never saw.
""",
    "Standard-mode visibility is best-effort": """
## Standard-mode visibility is best-effort

Outside isolated execution mode the Role Visibility Contract is a prompt contract only: the LLM
shares full conversation history across personas. Isolated execution mode provides mechanical
isolation via subagent context boundaries.
""",
    "Backlog scan carry-over is not optional": """
## Backlog scan carry-over is not optional

Stating the Phase 0 result distinguishes "scanned, no conflict" from "never scanned", which mirrors
`build-spec`'s `context.backlog_scan` contract (#489).
""",
    "Why vault access is vault-searcher's alone": """
## Why vault access is vault-searcher's alone

Searching is vault-searcher's job (MECE boundary); critiquing is this skill's job.
""",
    "Why the auto-defender needs a quality floor": """
## Why the auto-defender needs a quality floor

The floor keeps Survival Score reflecting the claim's actual strength rather than an
under-motivated auto-defender's laziness.
""",
    "Why the export schema block is mandatory": """
## Why the export schema block is mandatory

The block lets a downstream skill read the verdict counts without parsing the prose body, so an
exported report without it is not machine-readable.
""",
    "Isolated-Judge fallback rendering (#433)": """
## Isolated-Judge fallback rendering (#433)

The one-line `[격리 판정 실패 — 자체 판정, 신뢰도 낮음]` note mirrors the isolated-fallback pattern
`build-spec`/`unknown-discovery` already use for their own gate-imminent scoring (#433): a
self-judged round and an isolated one differ in confidence and must not render identically.
""",
    "Automated Defense subagent isolation": """
## Automated Defense subagent isolation

An inline auto-defender shares context with the Attacker turn that just produced the attack, which
biases it toward a generic, half-hearted rebuttal; a dedicated subagent call removes that bias the
same way isolated Judge removes evaluation bias.
""",
    "Automated Defense cost": """
## Automated Defense cost

Unlike Phase 0.5's one-shot vault-searcher call, which carries an explicit token ceiling in the
body, 자동 방어 spawns a fresh Defender subagent every attack round — up to 5 rounds × N claims per session. No explicit
token ceiling is enforced here; the isolation guarantee is worth the added subagent calls since
자동 방어 is opt-in.
""",
}
_RATIONALE_SECTIONS = {k: _normalise(v) for k, v in _RATIONALE_SECTIONS.items()}

# Every heading the file may contain, at any depth: the pinned sections plus its own title. An h1
# was the hatch a `## `-only set assertion could not see.
_RATIONALE_HEADINGS = {f"## {k}" for k in _RATIONALE_SECTIONS} | {
    "# Adversarial Review — Design Rationale"
}

# The file-level framing states the pin regime itself: without it the next editor reads a pile of
# ordinary background and has no reason to expect a red. It sits BEFORE the first `## `, so no
# section slice covers it — it gets its own whole-block pin, title line to first heading.
_RATIONALE_PREAMBLE = _normalise("""
# Adversarial Review — Design Rationale

**Canonical text.** These paragraphs used to sit in `SKILL.md`; they moved here under #663 so the
skill body keeps headroom against the #447 token budget. Nothing was trimmed — the rules themselves
stay in the body, only their *why* lives here. This file is background reading for a human editor,
not an instruction the skill applies mid-run.

**Every `##` section below is a pinned contract, not background.** Each one is compared WHOLE and
verbatim (whitespace-normalised) against a constant in `_RATIONALE_SECTIONS`, in
`thinking-tools/scripts/test/test-judge-rubric-anchors.py`. The slice runs from the heading to the
NEXT heading, and a partial edit at either end — head sentence, tail sentence, or a rewritten
number — reds. The heading set is pinned too, at every depth, so a new section reds until someone
pins it. Editing any of this text is therefore a deliberate contract change, and the matching
constant is updated in the same commit. Sentence-level pins were tried first and did not converge:
each round closed one edge and exposed the next. What this still does NOT catch is contradicting
prose parked in an unpinned region next to a pinned one; only whole-file equality would, and that
was rejected as costing more than the residual risk.
""")


# ---------------------------------------------------------------------------
# Vault Decision Grounding Procedure (#691) — the second contract this file pins. SKILL.md's
# Phase 0.5 keeps only a read-and-apply pointer; the operative 5-step call spec and the
# graceful-degrade fallback moved to patterns.md, pinned whole-section (same shape as
# `_ANCHOR_FRAMING` above) so nothing may be parked or blurred inside it.
# ---------------------------------------------------------------------------

_VAULT_PROCEDURE_POINTER = _normalise("""
read and apply
[reference/patterns.md § Vault Decision Grounding Procedure](reference/patterns.md#vault-decision-grounding-procedure)
as written, the binding contract.
""")

_VAULT_PROCEDURE_SECTION = _normalise("""
## Vault Decision Grounding Procedure

Referenced from [SKILL.md § Phase 0.5](../SKILL.md) — read and apply this section as written; it
is the binding contract for the one-shot `vault-searcher` call and the fallback behavior, not
background.

**One-shot vault-searcher call** (Mode 3 — Keyword Search, via the Agent tool):
1. Call `vault-searcher` **exactly once per session** (not per round). Cache the returned excerpts and reuse them across rounds. In a multi-claim session the cache reflects the **first** finalized Steelman's keywords and is never re-queried; the relevance gate (step 5) drops any cached decision unrelated to a later claim (why: rationale.md § Single-claim cache sizing).
2. **Search target**: `notes/`, preferring `type: decision`. Tell vault-searcher to use the manifest `type` pre-filter when available, otherwise fall back to a `decision-` filename grep (this is vault-searcher's native Mode 3 behavior). Counter-scenario sourcing MAY additionally surface `status: archived` decisions as a secondary worst-case source — but ONLY those carrying an explicit failure/reversal signal (a non-empty `## 문제` section or a reversal note); a plain `archived` status can also mean "successfully completed and shelved", which is NOT a worst-case source.
3. **Query**: 2–3 core keywords distilled from the finalized Steelman.
4. **Result bound**: up to **3** relevant decisions. Instruct vault-searcher to excerpt **only** the `## 결정` / `## 근거` / `## 문제` sections (not the full note).
5. **Relevance gate**: drop any returned decision whose topic is not genuinely related to the claim — an irrelevant hit must not be used in any round.

**Graceful degrade** (no user notice, no broken experience):
- **≥ 1 relevant result** → vault-grounded mode: feed the excerpts into the Evidence Attack `{counter_evidence_or_missing_data}` slot (see § Evidence Attack sourcing above) when the Evidence vector comes up.
- **0 results / vault-bridge not installed / Agent call fails / no response** → transparently fall back to the existing generic Evidence Attack. Do **not** announce the fallback to the user; the session must look identical to the non-vault path. A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further.

---
""")


def static_checks(skill_text: str, patterns_text: str, rationale_text: str) -> list:
    """(condition, description) for every pinned contract."""
    skill = _normalise(skill_text)
    patterns = _normalise(patterns_text)
    # rationale_text is read only through _section()/_headings(), which slice the RAW text —
    # a pre-normalised copy would flatten the headings those two depend on.
    checks = [
        # Whole section, heading to next heading, equality — covers the framing, the scoring
        # object, the interpolation rule, and anything a future editor parks between them.
        (_section(patterns_text, "Judge Rubric Anchors") == _ANCHOR_FRAMING,
         "patterns.md § Judge Rubric Anchors matches its pinned text exactly (#610)"),
        # The polarity of the whole scale: every row describes a DEFENSE. Own pin, own message.
        (_SCORING_OBJECT in patterns,
         "patterns.md pins the scoring object — the defense, never the attack"),
        # A heading is otherwise the escape hatch: one line of `## ` moves arbitrary contradicting
        # text past the end of every slice. patterns.md is not wholly contract, so the narrow form
        # — the anchors section must still be immediately followed by the delta mapping it feeds.
        # NOT covered: a heading added elsewhere in patterns.md, and prose parked under any of its
        # other sections. Only this adjacency is guarded.
        (_next_heading(patterns_text, "## Judge Rubric Anchors") == "## Judge Score Delta Mapping",
         "patterns.md parks no new section between § Judge Rubric Anchors and § Judge Score "
         "Delta Mapping"),
        # The two SKILL.md contract blocks, whole — caption, table, and everything to the next
        # heading, so a flipped caption or an appended sixth row cannot hide beside the row pins.
        (_block(skill_text, _JUDGE_RUBRIC_START) == _JUDGE_RUBRIC_BLOCK,
         "SKILL.md **Judge Rubric** block matches its pinned text exactly (caption + table + "
         "pointer)"),
        (_section(skill_text, "Survival Score", "### ") == _SURVIVAL_BLOCK,
         "SKILL.md § Survival Score matches its pinned text exactly"),
    ]
    checks += [
        (_normalise(row) in skill, f"SKILL.md body pins the anchor row {row.split('|')[1].strip()}")
        for row in _ANCHOR_ROWS
    ]
    checks += [
        # The caveat #610 asked for, verbatim, in the loaded body.
        (_NOT_A_MEASUREMENT in skill,
         "SKILL.md keeps the anchors-are-not-a-measurement caveat next to the 50% start"),
        # ...and the pointer that makes the reference copy binding from the body side.
        (_POINTER in skill,
         "SKILL.md's Judge step reads-and-applies § Judge Rubric Anchors (binding, not a citation)"),
        ("§ Judge Rubric Anchors" in skill,
         "SKILL.md names the anchor SECTION, not just the patterns.md path"),
        # Prose relocated by the #663 split — the pins followed it, whole-section and total.
        # The preamble sits before the first `## `, outside every section slice, so it is pinned
        # whole on its own: title line through to the first heading.
        (_normalise(rationale_text.split("\n## ")[0]) == _RATIONALE_PREAMBLE,
         "rationale.md preamble matches its pinned text exactly (declares the pin regime)"),
        # rationale.md is WHOLLY contract, so the heading SET is pinned too, at every depth: a new
        # sibling section is a new unpinned region, and it reds until someone pins it.
        (set(_headings(rationale_text)) == _RATIONALE_HEADINGS,
         "rationale.md has exactly the pinned set of headings, at any depth — none added"),
        # Every citation the body makes into rationale.md resolves to a real heading. Cheap, and
        # it is the only thing guarding the markdown-link -> plain-text conversion.
        (all(f"## {name}" in _headings(rationale_text)
             for name in _cited_sections(skill_text)),
         "every `rationale.md § …` citation in SKILL.md resolves to a real heading"),
        # Operative rules that must live in the LOADED body, not in the non-operative reference.
        (_ROLE_LABEL_RULE in skill,
         "SKILL.md keeps the role-labels-never-from-the-pool rule in the loaded body"),
        # The Phase 0.5 ceiling: operative, in the body, and the only copy of the figure.
        (_VAULT_BUDGET in skill,
         "SKILL.md pins the Phase 0.5 ≤ +1500 token ceiling (sole copy of the figure)"),
        ("reference/rationale.md" in skill_text,
         "SKILL.md still routes to reference/rationale.md for the moved rationale"),
    ]
    checks += [
        (_section(rationale_text, heading) == pinned,
         f"rationale.md § {heading} matches its pinned text exactly")
        for heading, pinned in _RATIONALE_SECTIONS.items()
    ]
    checks += [
        # Vault Decision Grounding Procedure (#691): whole-section equality, same shape as
        # _ANCHOR_FRAMING — a blurred step or a dropped fallback branch reds.
        (_section(patterns_text, "Vault Decision Grounding Procedure") == _VAULT_PROCEDURE_SECTION,
         "patterns.md § Vault Decision Grounding Procedure matches its pinned text exactly (#691)"),
        (_next_heading(patterns_text, "## Vault Decision Grounding Procedure") == "## Judge Rubric Anchors",
         "patterns.md parks no new section between § Vault Decision Grounding Procedure and "
         "§ Judge Rubric Anchors"),
        (_VAULT_PROCEDURE_POINTER in skill,
         "SKILL.md's Phase 0.5 reads-and-applies § Vault Decision Grounding Procedure (binding, "
         "not a citation)"),
        ("§ Vault Decision Grounding Procedure" in skill_text,
         "SKILL.md names the Vault Decision Grounding Procedure SECTION, not just the patterns.md path"),
    ]
    return checks


def check(cond: bool, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def main() -> int:
    print("Judge Rubric anchors (#610) — pinned contract checks")
    for cond, desc in static_checks(
        _SKILL.read_text(encoding="utf-8"),
        _PATTERNS.read_text(encoding="utf-8"),
        _RATIONALE.read_text(encoding="utf-8"),
    ):
        check(cond, desc)
    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print("\nOK: Judge Rubric anchors, the not-a-measurement caveat, and the binding pointer "
          "are all pinned")
    return 0


# ---------------------------------------------------------------------------
# Self-test: corrupt the canonical text and prove the guards FAIL (#663)
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL.read_text(encoding="utf-8")
_CLEAN_PATTERNS = _PATTERNS.read_text(encoding="utf-8")
_CLEAN_RATIONALE = _RATIONALE.read_text(encoding="utf-8")

# The 8 anchor blurred back into an unanchored adjective — the exact inflation #610 removes.
_SKILL_BLURRED_8 = _CLEAN_SKILL.replace(
    "| 8 | Rebuts that specific point of the attack with concrete evidence |",
    "| 8 | A strong defense |",
)
# The top anchor deleted: the scale loses its ceiling and 8 becomes the new 10.
_SKILL_NO_10 = _CLEAN_SKILL.replace(
    "| 10 | Dismantles the attack's own premise |", "")
# The whole table lifted out of the loaded body and left only behind the pointer — the arrangement
# the reviewer rejected, because nothing at runtime forces the read and no test can observe it.
_SKILL_TABLE_GONE = _CLEAN_SKILL
for _row in _ANCHOR_ROWS:
    _SKILL_TABLE_GONE = _SKILL_TABLE_GONE.replace(_row, "")
# POLARITY INVERSION: the scoring object rewritten from the defense to the attack. Every anchor row
# still matches verbatim, and every row now means the opposite thing.
_PATTERNS_POLARITY_INVERTED = _CLEAN_PATTERNS.replace(
    "judging **the defense** against the attack it answers — never the attack, and never the claim in\nthe abstract",
    "judging **the attack** against the defense it drew — never the defense",
)
# The interpolation rule deleted: 4, 6, 7, 9 go back to being whatever the Judge feels.
_PATTERNS_NO_INTERPOLATION = _CLEAN_PATTERNS.replace(
    "**Between anchors**: scores between two anchors interpolate (6–7 = more than engagement, short of a\nconcrete rebuttal). Anchor to the nearest description rather than inventing a new criterion for the\ngap.",
    "",
)
# The section demoted to background reading — present, but no longer applied at scoring time.
_PATTERNS_NOT_BINDING = _CLEAN_PATTERNS.replace(
    "`SKILL.md` points here; the\nJudge reads and applies it at the moment it scores a round",
    "`SKILL.md` links here as background",
)
# The whole section renamed: the body's section-name pointer would dangle.
_PATTERNS_RENAMED = _CLEAN_PATTERNS.replace(
    "## Judge Rubric Anchors", "## Scoring Notes")
# The caveat deleted: the displayed band silently reads as a measured quantity again.
_SKILL_NO_CAVEAT = _CLEAN_SKILL.replace(
    "The Judge Rubric anchors buy judging consistency; they do NOT make Survival Score a "
    "measurement — the 50% start is still arbitrary (#610).",
    "",
)
# The caveat inverted — the failure mode #610 explicitly warns against.
_SKILL_CAVEAT_INVERTED = _CLEAN_SKILL.replace(
    "they do NOT make Survival Score a measurement — the 50% start is still arbitrary",
    "they make Survival Score a calibrated measurement",
)
# The binding pointer decays into a bare citation. The path survives, so a path-only check stays
# green while the Judge is never told to open the anchors.
_SKILL_POINTER_DECAYED = _CLEAN_SKILL.replace(
    "Before scoring each round, read and apply § Judge Rubric Anchors in",
    "For background see the anchor notes in",
)
# The pointer deleted outright.
_SKILL_NO_POINTER = _CLEAN_SKILL.replace("§ Judge Rubric Anchors", "the rubric notes")
# Moved rationale deleted from its new home — a trim wearing a split's clothes.
_RATIONALE_NO_ANGLE = _CLEAN_RATIONALE.replace(
    "The Steelman is model-authored", "The Steelman is authored elsewhere")
_RATIONALE_NO_COST = _CLEAN_RATIONALE.replace(
    "up to 5 rounds × N claims per session.", "as needed.")
# A PARTIAL trim from the RIGHT: only the trailing sentence of a moved paragraph goes. Pins that
# stopped at the headline clause stayed green here.
_RATIONALE_TAIL_TRIMMED = _CLEAN_RATIONALE.replace(
    " The\ndomain does not change between a claim and its steelmanned form; only the framing does, and framing\nis what shifted the selection.",
    "",
)
# The MIRROR IMAGE, from the LEFT: the section's first sentence — the roles-are-not-domain-personas
# rule — deleted, leaving the tail. Tail-extended pins stayed green here; section equality does not.
_RATIONALE_HEAD_TRIMMED = _CLEAN_RATIONALE.replace(
    "Both skills run the rule on that same original text and every cut starts at rank 1, so the two\npoint at the same pool entry for a given claim. ",
    "",
)
# Head trim in a second section, on the clause that carries the #489 provenance.
_RATIONALE_HEAD_TRIMMED_2 = _CLEAN_RATIONALE.replace(
    "The Phase 0 scan is one deterministic shell scan of the open+closed issue corpus (same script\n`build-spec` Phase 0 uses, #489), separate from Phase 0.5's vault-searcher token budget.\n\n",
    "",
)
# A NUMBER rewritten by one digit — no sentence added or removed, and a 10x wrong budget. This is
# the case no substring pin anchored on a phrase can see.
_RATIONALE_TOKEN_INFLATED = _CLEAN_RATIONALE.replace(
    "up to 5 rounds × N claims per session", "up to 50 rounds × N claims per session")
# A contradicting clause PARKED at the end of a section, touching none of the existing prose.
_RATIONALE_PARKED_CLAUSE = _CLEAN_RATIONALE.replace(
    "자동 방어 is opt-in.",
    "자동 방어 is opt-in. In practice, skip the subagent and answer inline when rounds get long.",
)
# The file-level framing that tells the next editor these sections are pinned at all.
_RATIONALE_NO_PREAMBLE = _CLEAN_RATIONALE.replace(
    "**Every `##` section below is a pinned contract, not background.**",
    "Some notes follow.",
)
# The preamble inverted while keeping the one sentence a substring pin used to anchor on.
_RATIONALE_PREAMBLE_INVERTED = _CLEAN_RATIONALE.replace(
    "Nothing was trimmed — the rules themselves\nstay in the body, only their *why* lives here.",
    "Feel free to trim these paragraphs.",
)
# A permissive clause appended to the preamble, editing nothing that was already there.
_RATIONALE_PREAMBLE_APPENDED = _CLEAN_RATIONALE.replace(
    "each round closed one edge and exposed the next.",
    "each round closed one edge and exposed the next. Sections may be freely edited without "
    "touching the test.",
)
# A NEW SIBLING SECTION: every existing pin still matches, and the contradiction lives in a region
# no slice reaches. This is the heading escape hatch the heading-SET assertion closes.
_RATIONALE_NEW_SECTION = _CLEAN_RATIONALE.rstrip() + (
    "\n\n## Addendum\n\nIn practice these rationales are advisory and may be ignored.\n"
)
# The same escape hatch in patterns.md, wedged between the anchors and the delta mapping they feed.
_PATTERNS_WEDGED_SECTION = _CLEAN_PATTERNS.replace(
    "## Judge Score Delta Mapping",
    "## Anchor Override\n\nIgnore the anchors when the defense feels strong.\n\n"
    "## Judge Score Delta Mapping",
    1,
)
# --- the h1 variants: same mutations one heading level up, invisible to a `## `-only scan --------
_PATTERNS_WEDGED_H1 = _CLEAN_PATTERNS.replace(
    "## Judge Score Delta Mapping",
    "# Anchor Override\n\nIgnore the anchors when the defense feels strong.\n\n"
    "## Judge Score Delta Mapping",
    1,
)
_RATIONALE_NEW_H1_MIDFILE = _CLEAN_RATIONALE.replace(
    "## Automated Defense cost",
    "# Addendum\n\nIn practice these rationales are advisory and may be ignored.\n\n"
    "## Automated Defense cost",
    1,
)
_RATIONALE_NEW_H1_EOF = _CLEAN_RATIONALE.rstrip() + (
    "\n\n# Addendum\n\nIn practice these rationales are advisory and may be ignored.\n"
)
# The operative rule demoted back OUT of the loaded body into the file that declares itself
# non-operative — the #663 defect this round reverted.
_SKILL_RULE_DEMOTED = _CLEAN_SKILL.replace(
    "The fixed role labels — Attacker, Judge,\nSteelman Coach — are roles, not domain personas; they are never selected from the pool and never\nchange per topic (why both skills land on the same entry: ",
    "(why the role labels are not drawn from it: ",
)
# The Phase 0.5 ceiling rewritten 10x in the body, where it is now the only copy.
_SKILL_BUDGET_INFLATED = _CLEAN_SKILL.replace("≤ +1500 tokens", "≤ +15000 tokens")
# A citation pointing at a heading that does not exist — the drift the plain-text conversion
# stopped anything from catching.
_SKILL_DANGLING_CITATION = _CLEAN_SKILL.replace(
    "rationale.md § Automated Defense cost", "rationale.md § Subagent cost")

# --- the three SKILL.md body mutations that row-only pins could not see -------------------
# Caption polarity flipped in the loaded body. patterns.md reds on the byte-identical inversion
# via `_SCORING_OBJECT`; here nothing saw it, and the Judge reads THIS file.
_SKILL_CAPTION_INVERTED = _CLEAN_SKILL.replace(
    "Score every element against these anchors", "Score the attack against these anchors")
# A sixth row appended: the scale gains an anchor nobody pinned.
_SKILL_SIXTH_ROW = _CLEAN_SKILL.replace(
    "| 10 | Dismantles the attack's own premise |",
    "| 10 | Dismantles the attack's own premise |\n| 9 | Anything that sounds confident |",
)
# The whole scale demoted one line above the table, every row untouched.
_SKILL_ADVISORY_CLAUSE = _CLEAN_SKILL.replace(
    "| Score | Anchor |", "Anchors are advisory only.\n\n| Score | Anchor |")
# The not-a-measurement caveat negated by an appended sentence rather than an edit.
_SKILL_CAVEAT_APPENDED = _CLEAN_SKILL.replace(
    "Read the score as a resilience band, never as a measured quantity.",
    "Read the score as a resilience band, never as a measured quantity. In practice it is "
    "calibrated enough to report as a percentage.",
)
# One of the newly moved paragraphs deleted outright.
_RATIONALE_NO_CACHE = _CLEAN_RATIONALE.replace(
    "preserves the token budget at the cost of not surfacing\nclaim-specific decisions for subsequent claims.",
    "is fine.",
)
# The body stops routing to the moved rationale at all.
_SKILL_NO_RATIONALE_LINK = _CLEAN_SKILL.replace("reference/rationale.md", "reference/patterns.md")

# --- Vault Decision Grounding Procedure (#691) mutations ---------------------------------
# The one-shot constraint loosened: re-querying per round is exactly the token-budget blowout
# the constraint exists to prevent.
_PATTERNS_VAULT_ONE_SHOT_DROPPED = _CLEAN_PATTERNS.replace(
    "Call `vault-searcher` **exactly once per session** (not per round).",
    "Call `vault-searcher` once per round.",
)
# Step 5 deleted: an irrelevant cached decision could be used as attack ammunition.
_PATTERNS_VAULT_RELEVANCE_GATE_DROPPED = _CLEAN_PATTERNS.replace(
    "5. **Relevance gate**: drop any returned decision whose topic is not genuinely related to "
    "the claim — an irrelevant hit must not be used in any round.\n\n",
    "",
)
# The heading escape hatch: a new sibling section wedged right before Judge Rubric Anchors.
_PATTERNS_VAULT_WEDGED_SECTION = _CLEAN_PATTERNS.replace(
    "## Judge Rubric Anchors",
    "## Vault Override\n\nIgnore the relevance gate if the attack needs ammunition.\n\n"
    "## Judge Rubric Anchors",
    1,
)
# The binding pointer decays into a background citation — the path/section name survive, so a
# path-only or name-only check stays green while nothing tells the model to actually apply it.
_SKILL_VAULT_POINTER_DECAYED = _CLEAN_SKILL.replace(
    "read and apply\n[reference/patterns.md § Vault Decision Grounding Procedure]",
    "for background, see\n[reference/patterns.md § Vault Decision Grounding Procedure]",
)
# The section name itself dropped from the body — the pointer no longer names what it binds.
_SKILL_VAULT_NO_SECTION_NAME = _CLEAN_SKILL.replace(
    "§ Vault Decision Grounding Procedure", "the vault grounding notes")

# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of its
# base, and an expect-FAIL case on an unmodified copy would then be testing nothing.
for _name, _fixture, _base in (
    ("_SKILL_BLURRED_8", _SKILL_BLURRED_8, _CLEAN_SKILL),
    ("_SKILL_NO_10", _SKILL_NO_10, _CLEAN_SKILL),
    ("_SKILL_TABLE_GONE", _SKILL_TABLE_GONE, _CLEAN_SKILL),
    ("_PATTERNS_POLARITY_INVERTED", _PATTERNS_POLARITY_INVERTED, _CLEAN_PATTERNS),
    ("_PATTERNS_NO_INTERPOLATION", _PATTERNS_NO_INTERPOLATION, _CLEAN_PATTERNS),
    ("_PATTERNS_NOT_BINDING", _PATTERNS_NOT_BINDING, _CLEAN_PATTERNS),
    ("_PATTERNS_RENAMED", _PATTERNS_RENAMED, _CLEAN_PATTERNS),
    ("_RATIONALE_TAIL_TRIMMED", _RATIONALE_TAIL_TRIMMED, _CLEAN_RATIONALE),
    ("_RATIONALE_HEAD_TRIMMED", _RATIONALE_HEAD_TRIMMED, _CLEAN_RATIONALE),
    ("_RATIONALE_HEAD_TRIMMED_2", _RATIONALE_HEAD_TRIMMED_2, _CLEAN_RATIONALE),
    ("_RATIONALE_TOKEN_INFLATED", _RATIONALE_TOKEN_INFLATED, _CLEAN_RATIONALE),
    ("_RATIONALE_PARKED_CLAUSE", _RATIONALE_PARKED_CLAUSE, _CLEAN_RATIONALE),
    ("_RATIONALE_NO_PREAMBLE", _RATIONALE_NO_PREAMBLE, _CLEAN_RATIONALE),
    ("_RATIONALE_PREAMBLE_INVERTED", _RATIONALE_PREAMBLE_INVERTED, _CLEAN_RATIONALE),
    ("_RATIONALE_PREAMBLE_APPENDED", _RATIONALE_PREAMBLE_APPENDED, _CLEAN_RATIONALE),
    ("_RATIONALE_NEW_SECTION", _RATIONALE_NEW_SECTION, _CLEAN_RATIONALE),
    ("_PATTERNS_WEDGED_SECTION", _PATTERNS_WEDGED_SECTION, _CLEAN_PATTERNS),
    ("_PATTERNS_WEDGED_H1", _PATTERNS_WEDGED_H1, _CLEAN_PATTERNS),
    ("_RATIONALE_NEW_H1_MIDFILE", _RATIONALE_NEW_H1_MIDFILE, _CLEAN_RATIONALE),
    ("_RATIONALE_NEW_H1_EOF", _RATIONALE_NEW_H1_EOF, _CLEAN_RATIONALE),
    ("_SKILL_RULE_DEMOTED", _SKILL_RULE_DEMOTED, _CLEAN_SKILL),
    ("_SKILL_BUDGET_INFLATED", _SKILL_BUDGET_INFLATED, _CLEAN_SKILL),
    ("_SKILL_DANGLING_CITATION", _SKILL_DANGLING_CITATION, _CLEAN_SKILL),
    ("_SKILL_CAPTION_INVERTED", _SKILL_CAPTION_INVERTED, _CLEAN_SKILL),
    ("_SKILL_SIXTH_ROW", _SKILL_SIXTH_ROW, _CLEAN_SKILL),
    ("_SKILL_ADVISORY_CLAUSE", _SKILL_ADVISORY_CLAUSE, _CLEAN_SKILL),
    ("_SKILL_CAVEAT_APPENDED", _SKILL_CAVEAT_APPENDED, _CLEAN_SKILL),
    ("_RATIONALE_NO_CACHE", _RATIONALE_NO_CACHE, _CLEAN_RATIONALE),
    ("_SKILL_NO_CAVEAT", _SKILL_NO_CAVEAT, _CLEAN_SKILL),
    ("_SKILL_CAVEAT_INVERTED", _SKILL_CAVEAT_INVERTED, _CLEAN_SKILL),
    ("_SKILL_POINTER_DECAYED", _SKILL_POINTER_DECAYED, _CLEAN_SKILL),
    ("_SKILL_NO_POINTER", _SKILL_NO_POINTER, _CLEAN_SKILL),
    ("_SKILL_NO_RATIONALE_LINK", _SKILL_NO_RATIONALE_LINK, _CLEAN_SKILL),
    ("_RATIONALE_NO_ANGLE", _RATIONALE_NO_ANGLE, _CLEAN_RATIONALE),
    ("_RATIONALE_NO_COST", _RATIONALE_NO_COST, _CLEAN_RATIONALE),
    ("_PATTERNS_VAULT_ONE_SHOT_DROPPED", _PATTERNS_VAULT_ONE_SHOT_DROPPED, _CLEAN_PATTERNS),
    ("_PATTERNS_VAULT_RELEVANCE_GATE_DROPPED", _PATTERNS_VAULT_RELEVANCE_GATE_DROPPED, _CLEAN_PATTERNS),
    ("_PATTERNS_VAULT_WEDGED_SECTION", _PATTERNS_VAULT_WEDGED_SECTION, _CLEAN_PATTERNS),
    ("_SKILL_VAULT_POINTER_DECAYED", _SKILL_VAULT_POINTER_DECAYED, _CLEAN_SKILL),
    ("_SKILL_VAULT_NO_SECTION_NAME", _SKILL_VAULT_NO_SECTION_NAME, _CLEAN_SKILL),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


def self_test() -> int:
    cases = [
        ("clean skill + reference docs pass every pin",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _CLEAN_RATIONALE, True),
        ("anchor 8 blurred into an unanchored adjective -> FAIL",
         _SKILL_BLURRED_8, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("top anchor (10) deleted from the scale -> FAIL",
         _SKILL_NO_10, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("anchor table lifted out of the loaded body -> FAIL",
         _SKILL_TABLE_GONE, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        # Every anchor row still matches verbatim here — only the object being scored flipped.
        ("scoring object inverted from the defense to the attack -> FAIL",
         _CLEAN_SKILL, _PATTERNS_POLARITY_INVERTED, _CLEAN_RATIONALE, False),
        ("between-anchors interpolation rule deleted -> FAIL",
         _CLEAN_SKILL, _PATTERNS_NO_INTERPOLATION, _CLEAN_RATIONALE, False),
        ("anchor section demoted from binding to background -> FAIL",
         _CLEAN_SKILL, _PATTERNS_NOT_BINDING, _CLEAN_RATIONALE, False),
        ("anchor section renamed, body pointer left dangling -> FAIL",
         _CLEAN_SKILL, _PATTERNS_RENAMED, _CLEAN_RATIONALE, False),
        ("not-a-measurement caveat deleted -> FAIL",
         _SKILL_NO_CAVEAT, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("not-a-measurement caveat inverted into a calibration claim -> FAIL",
         _SKILL_CAVEAT_INVERTED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        # A path-only pointer check cannot see this one: patterns.md is cited elsewhere in the body.
        ("binding pointer decayed into a background citation -> FAIL",
         _SKILL_POINTER_DECAYED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("body no longer names the anchor section -> FAIL",
         _SKILL_NO_POINTER, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("moved #423 rationale deleted from rationale.md -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NO_ANGLE, False),
        ("moved 자동 방어 cost note trimmed away -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NO_COST, False),
        ("moved single-claim cache tradeoff deleted -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NO_CACHE, False),
        # Both directions of a partial trim, the pair sentence-level pins could never close at once.
        ("only the trailing sentence of a moved paragraph trimmed -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_TAIL_TRIMMED, False),
        ("only the HEAD sentence of § Shared-pool contact point trimmed -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_HEAD_TRIMMED, False),
        ("only the HEAD sentence of § Backlog prefilter cost trimmed -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_HEAD_TRIMMED_2, False),
        # One digit, no sentence added or removed, a 10x wrong budget.
        ("a digit rewritten inside a pinned section (5 -> 50 rounds) -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_TOKEN_INFLATED, False),
        # Nothing existing edited — a contradicting clause simply parked at the section's end.
        ("contradicting clause parked at the end of a pinned section -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_PARKED_CLAUSE, False),
        ("file-level pinned-contract framing deleted -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NO_PREAMBLE, False),
        ("preamble rewritten to invite trimming -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_PREAMBLE_INVERTED, False),
        ("permissive clause appended to the preamble -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_PREAMBLE_APPENDED, False),
        # The heading escape hatch, both files: every existing pin still matches.
        ("new unpinned `## Addendum` section added to rationale.md -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NEW_SECTION, False),
        ("`## Anchor Override` wedged before § Judge Score Delta Mapping -> FAIL",
         _CLEAN_SKILL, _PATTERNS_WEDGED_SECTION, _CLEAN_RATIONALE, False),
        # The same three mutations one heading level up — a `## `-only scan saw none of them.
        ("`# Anchor Override` (h1) wedged before § Judge Score Delta Mapping -> FAIL",
         _CLEAN_SKILL, _PATTERNS_WEDGED_H1, _CLEAN_RATIONALE, False),
        ("`# Addendum` (h1) added mid-file to rationale.md -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NEW_H1_MIDFILE, False),
        ("`# Addendum` (h1) appended at rationale.md EOF -> FAIL",
         _CLEAN_SKILL, _CLEAN_PATTERNS, _RATIONALE_NEW_H1_EOF, False),
        # An operative rule demoted into the file that declares itself non-operative (#663).
        ("role-label rule demoted from the body into rationale.md -> FAIL",
         _SKILL_RULE_DEMOTED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("Phase 0.5 ≤ +1500 ceiling inflated 10x in the body -> FAIL",
         _SKILL_BUDGET_INFLATED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("body cites a rationale.md heading that does not exist -> FAIL",
         _SKILL_DANGLING_CITATION, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        # The three SKILL.md body mutations row-only pins could not see.
        ("anchor caption flipped to score the ATTACK in the loaded body -> FAIL",
         _SKILL_CAPTION_INVERTED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("sixth unpinned anchor row appended to the table -> FAIL",
         _SKILL_SIXTH_ROW, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("`Anchors are advisory only.` parked above the table -> FAIL",
         _SKILL_ADVISORY_CLAUSE, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("not-a-measurement caveat negated by an appended sentence -> FAIL",
         _SKILL_CAVEAT_APPENDED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("body stops routing to the moved rationale -> FAIL",
         _SKILL_NO_RATIONALE_LINK, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        # Vault Decision Grounding Procedure (#691): the second whole-section pin in this file.
        ("vault one-shot-per-session constraint loosened to per-round -> FAIL",
         _CLEAN_SKILL, _PATTERNS_VAULT_ONE_SHOT_DROPPED, _CLEAN_RATIONALE, False),
        ("vault relevance gate (step 5) deleted -> FAIL",
         _CLEAN_SKILL, _PATTERNS_VAULT_RELEVANCE_GATE_DROPPED, _CLEAN_RATIONALE, False),
        ("`## Vault Override` wedged before § Judge Rubric Anchors -> FAIL",
         _CLEAN_SKILL, _PATTERNS_VAULT_WEDGED_SECTION, _CLEAN_RATIONALE, False),
        ("vault procedure pointer decayed into a background citation -> FAIL",
         _SKILL_VAULT_POINTER_DECAYED, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        ("body drops the Vault Decision Grounding Procedure section name -> FAIL",
         _SKILL_VAULT_NO_SECTION_NAME, _CLEAN_PATTERNS, _CLEAN_RATIONALE, False),
        # Paragraph-level reflow (wrapped lines joined, blank-line structure kept — what a
        # re-wrap actually looks like). Collapsing headings away too would be a structural edit,
        # not a reflow, and the section slicer is right to red on that.
        ("reflowed sources still pass (whitespace is not the contract)",
         _reflow(_CLEAN_SKILL), _reflow(_CLEAN_PATTERNS), _reflow(_CLEAN_RATIONALE), True),
    ]
    failed = 0
    for desc, skill_text, patterns_text, rationale_text, expect_pass in cases:
        got = all(cond for cond, _ in static_checks(skill_text, patterns_text, rationale_text))
        if got == expect_pass:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc} (expected {'pass' if expect_pass else 'fail'}, "
                  f"got {'pass' if got else 'fail'})")
            failed += 1
    if failed:
        print(f"\nFAILED: {failed} self-test case(s) failed")
        return 1
    print(f"\nOK: all {len(cases)} judge-rubric-anchor self-test cases passed")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    raise SystemExit(main())
