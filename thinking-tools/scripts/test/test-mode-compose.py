#!/usr/bin/env python3
"""Regression test: expert-panel mode combinations compose without contradiction.

Validates the SKILL.md claim "All combinations compose silently" by statically
parsing the SKILL.md mode-toggle declarations and asserting:

1. Every declared mode name appears in the Execution Modes section.
2. No two mode declarations share the same trigger phrase (no ambiguous routing).
3. Every mode name that appears in the "All combinations compose silently" line
   (or its extended footnote) is declared in Execution Modes.
4. Citation grounding is listed as composing silently with all other modes.
5. Phase 2 inline-summary path is referenced as composing silently.
6. (#663) The isolated-mode exchange-loop contract and the Expert Selection Guide, whose
   canonical text moved to reference.md, are still present THERE verbatim, and SKILL.md
   still binds each by section name with read-and-apply wording (not a bare citation).

This is a structural / static check — it does not execute any LLM logic.

Usage:
    python3 thinking-tools/scripts/test/test-mode-compose.py
    python3 thinking-tools/scripts/test/test-mode-compose.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "thinking-tools" / "skills" / "expert-panel" / "SKILL.md"
_REFERENCE_PATH = _REPO_ROOT / "thinking-tools" / "skills" / "expert-panel" / "reference.md"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _load_reference() -> str:
    if not _REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"reference.md not found at {_REFERENCE_PATH}")
    return _REFERENCE_PATH.read_text(encoding="utf-8")


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


def _extract_execution_modes_block(text: str) -> str:
    """Return the text of the ## Execution Modes section (up to next ##)."""
    m = re.search(r"^## Execution Modes\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def _extract_declared_modes(modes_block: str) -> list[dict]:
    """Parse each bullet in the Execution Modes section.

    Returns list of dicts with keys:
      - name: str  (the bold label, e.g. "격리 실행")
      - triggers: list[str]  (quoted phrases inside parentheses)
    """
    modes: list[dict] = []
    # Match lines like: - **격리 실행** ("phrase1", "phrase2"):
    for m in re.finditer(
        r"^- \*\*(.+?)\*\*\s*\((.+?)\):", modes_block, re.MULTILINE
    ):
        name = m.group(1).strip()
        raw_triggers = m.group(2)
        triggers = [t.strip().strip('"') for t in raw_triggers.split(",")]
        modes.append({"name": name, "triggers": triggers})
    return modes


def _find_compose_line(text: str) -> str:
    """Return the FIRST line containing the 'compose silently' declaration.

    First match only (not joined): joining lines would let separate mentions pass a
    single-string `in` test that no one line satisfies — a false positive.
    """
    for line in text.splitlines():
        if "compose silently" in line:
            return line.strip()
    return ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_modes_declared(modes: list[dict]) -> tuple[bool, str]:
    """At least the two canonical modes must be declared."""
    names = {m["name"] for m in modes}
    # COUPLED to the bold mode labels in expert-panel/SKILL.md "## Execution Modes"
    # (the `- **격리 실행** (...)` / `- **요약 출력** (...)` bullets). If a mode is
    # intentionally renamed there, update this set too — otherwise this gate silently
    # stops checking that mode (a rename without an update here is a false-OK).
    required = {"격리 실행", "요약 출력"}
    missing = required - names
    if missing:
        return False, f"Missing declared modes: {missing}"
    return True, f"All {len(modes)} mode(s) declared (incl. required: {required})"


def check_no_trigger_collision(modes: list[dict]) -> tuple[bool, str]:
    """No trigger phrase appears in two different modes."""
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for mode in modes:
        for trigger in mode["triggers"]:
            if trigger in seen:
                collisions.append(
                    f"'{trigger}' shared by '{seen[trigger]}' and '{mode['name']}'"
                )
            else:
                seen[trigger] = mode["name"]
    if collisions:
        return False, "Trigger collisions: " + "; ".join(collisions)
    return True, f"No trigger collisions across {len(seen)} trigger phrase(s)"


def check_compose_line_present(text: str) -> tuple[bool, str]:
    """The 'All combinations compose silently' declaration must exist."""
    compose = _find_compose_line(text)
    if not compose:
        return False, "'All combinations compose silently' declaration not found"
    return True, f"Compose declaration found: {compose[:120]}"


def check_citation_compose_referenced(text: str) -> tuple[bool, str]:
    """Citation grounding must be mentioned as composing silently."""
    compose = _find_compose_line(text)
    if "citation" not in compose.lower() and "Citation" not in compose:
        return False, (
            "Citation grounding not referenced in 'compose silently' line — "
            "add 'citation grounding' to the compose declaration"
        )
    return True, "Citation grounding referenced in compose declaration"


def check_inline_summary_compose_referenced(text: str) -> tuple[bool, str]:
    """Phase 2 inline-summary path must be mentioned as composing silently."""
    compose = _find_compose_line(text)
    if "inline" not in compose.lower() and "summary path" not in compose.lower() and "inline-summary" not in compose.lower():
        return False, (
            "Phase 2 inline-summary path not referenced in 'compose silently' line — "
            "add reference to inline SUMMARY path in the compose declaration"
        )
    return True, "Phase 2 inline-summary path referenced in compose declaration"


def check_citation_contract_section(text: str) -> tuple[bool, str]:
    """A ## Citation Contract section must exist."""
    if "## Citation Contract" not in text:
        return False, "'## Citation Contract' section not found in SKILL.md"
    return True, "'## Citation Contract' section present"


def check_citation_state_field(text: str) -> tuple[bool, str]:
    """Citation field must appear in the STATE block template."""
    if "Citation:" not in text:
        return False, "'Citation:' field not found in STATE block template"
    return True, "'Citation:' field present in STATE block"


def check_phase2_inline_path(text: str) -> tuple[bool, str]:
    """Phase 2 must describe the lightweight inline SUMMARY path."""
    if "inline SUMMARY" not in text:
        return False, "Phase 2 inline SUMMARY path not described in SKILL.md"
    return True, "Phase 2 inline SUMMARY path described"


# ---------------------------------------------------------------------------
# Canonical contract text (#663)
#
# expert-panel/SKILL.md sat at ~4,876 of the #447 5,000-token budget, so the isolated-mode
# exchange-loop contract and the Expert Selection Guide table moved to reference.md and the
# body keeps a read-and-apply pointer. The pins FOLLOW the prose: they read reference.md,
# which is now canonical, plus the pointers that make it binding from the SKILL.md side.
#
# WHY WHOLE-SECTION EQUALITY, not a set of clause pins. Three review rounds of clause pins
# each closed the clauses named and each left the next unpinned neighbour green after
# deletion: the E1 spawn, then packet (b)'s substance, then the Rotation row, then the
# premise flip `in parallel` -> `one after another` that leaves the pinned anti-anchoring
# sentence verbatim and false. Every partial anchor is a blocklist of the last wording
# someone tried and leaves a region for the next one, so the section's OWN TEXT is the pin
# and the comparison is TOTAL (same shape as `_GATE_CONTRACT` in
# feedback-loop/scripts/test/test-add-policy-necessity-gate.py). Whitespace is normalised:
# a reflow is not a change, an edit to the words is — and updating these constants is the
# deliberate act that records a contract change, in the same commit as the edit.
#
# Both slices run from the heading to the NEXT heading, so a contradicting clause parked at
# the bottom of the section is inside the pin, not outside it. They are section-SCOPED: a
# verbatim copy pasted into a neighbouring section is not what gets compared.
#
# The four clause pins that survive are kept for DIAGNOSIS, not coverage — each names a
# distinct polarity/premise flip, so the failure message says which invariant died instead
# of only "the section changed".
#
# The pointers are pinned by SECTION NAME + the read-and-apply wording, never by the bare
# path: `reference.md` is already cited half a dozen times in the body for rationale, so a
# path-only check stays green even after every binding pointer has decayed into a citation.
# ---------------------------------------------------------------------------

_EXCHANGE_LOOP_SECTION_RE = re.compile(
    r"^#### Isolated execution: exchange-loop contract\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)
_SELECTION_GUIDE_SECTION_RE = re.compile(
    r"^### Expert Selection Guide: what the Selection Rule enforces\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _section(pattern: re.Pattern, ref_text: str) -> str:
    """The whole named section, heading to next heading, whitespace-normalised ("" if absent)."""
    match = pattern.search(ref_text)
    return _normalise(match.group(0)) if match else ""


_EXCHANGE_LOOP_SECTION = _normalise("""\
#### Isolated execution: exchange-loop contract

**Canonical text (#663).** SKILL.md § Isolated Execution: Rebuttal Exchanges points here; this
section is the binding contract, not background, and the orchestrator must apply it as written.
Load it before running isolated mode. (Until #663 this text lived in the SKILL.md body, with a
condensed Korean restatement here; the two are now one copy.) Its whole text — heading to the
next heading, so nothing unpinned may be parked at the bottom — is pinned VERBATIM by
`_EXCHANGE_LOOP_SECTION` in `thinking-tools/scripts/test/test-mode-compose.py`. Editing anything
below is a deliberate contract change and updates that constant in the same commit; a reflow is
free (the comparison is whitespace-normalised).

In default (inline) mode, an entire topic — every persona's turns — is produced in one model
response: a *simulated* debate where a single model scripts all voices. It is fast, but it is not
a real turn exchange, and personas drift toward a single voice.

Isolated execution replaces the simulated pass with real multi-turn **exchanges** inside a single
topic round's Q&A/Rebuttal step (SKILL.md Phase 1 step 3). An "exchange" is one synchronous
fan-out across all experts (not per-expert) — it is NOT a topic round. The loop runs **1
independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)**, capped at 3 exchanges total —
independent of the 3 topic-round ceiling and its tie-break trigger.

**Orchestrator vs. Moderator**: in isolated mode the mechanical work — spawning experts,
assembling per-expert prompt packets, relaying between exchanges, and judging the stop condition —
is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator
subagent. The Moderator subagent stays visibility-limited (position summaries only) and is spawned
only for Synthesis/Conclusion. This keeps the Moderator Visibility Contract intact: the
orchestrator already holds every statement, so it is the one allowed to summarize and relay.

**Exchange loop**:

1. **E1 — Independent** (anchoring-free): the orchestrator spawns each expert as a separate
   subagent with the topic + briefing only. No expert sees another's statement. The orchestrator
   collects all statements.
2. **E2/E3 — Rebuttal**: the orchestrator re-spawns all experts **in parallel**, each receiving a
   packet of — (a) its own prior-exchange position (a re-spawned subagent is stateless; without
   this it cannot "hold/defend"), (b) a *summary* of the other experts' **prior-exchange**
   statements (never within-exchange statements — parallel re-spawn means no expert sees another's
   current-exchange turn, preserving anti-anchoring), and (c) the re-applied **Anti-conformity
   directive** (defined at the top of SKILL.md § Phase 1: Topic Rounds). Each expert then (a)
   holds and defends, (b) rebuts a specific point with new evidence, or (c) revises.

**Stop conditions** (whichever comes first):

- The exchange loop reaches the 2-rebuttal cap (e3 completed), or
- **No new argument**: comparing the latest exchange to the immediately prior one, *no expert*
  introduced a new point or a new rebuttal — a new point requires new evidence (data,
  counterexample, or precedent) or a new argument structure; a restated prior point does not
  count. The orchestrator makes this call — it needs the full per-expert statements, which the
  visibility-limited Moderator subagent cannot see. The test is *new arguments*, not *agreement*:
  an exchange where experts only echo growing agreement without new reasoning is
  convergence-by-conformity and also stops the loop. This guards against both runaway cost and
  false consensus.

After the loop stops, the orchestrator spawns the Moderator subagent with the final exchange's
position summaries to compute Synthesis → Conclusion.

**Degenerate cases**:

- An expert subagent that fails, returns empty, or returns no final text at all is retried once; on
  a second failure the exchange proceeds with the remaining experts (recorded in the transcript — never silently dropped).
  A subagent that returns only idle notifications and no final text after one re-request counts as
  unavailable and takes this same fallback (#647) — never wait on it further.
- An expert added mid-discussion (see Expert Selection Guide) first runs a catch-up E1 independent
  statement, then joins from the next rebuttal exchange.

**Cost**: per topic, `(exchanges × experts)` expert subagents — `exchanges` = 1 (independent) +
1–2 (rebuttal), i.e. up to `3 × experts` when both rebuttal exchanges run, fewer when early-stop
fires — plus 1 Moderator subagent for Synthesis. **Recovery cost**: if Phase 2 produces only a
compressed final message or a content-free sign-off (e.g. due to context pressure), the user must
re-request the full record — add one full-panel context reload to the effective cost. This
recovery overhead is avoided by the inline SUMMARY path (lightweight sessions) and by the full
3-file output (multi-topic sessions). Choose isolated mode when independence and genuine turn
exchange matter more than speed — inline mode stays the default for quick reviews.
""")

_SELECTION_GUIDE_SECTION = _normalise("""\
### Expert Selection Guide: what the Selection Rule enforces

**Canonical text (#663).** SKILL.md § Expert Selection Guide points here; this section is the
binding contract for panel composition, not background, and must be applied as written. Its
whole text — heading to the next heading, so nothing unpinned may be parked at the bottom — is
pinned VERBATIM by `_SELECTION_GUIDE_SECTION` in
`thinking-tools/scripts/test/test-mode-compose.py`. Editing anything below is a deliberate
contract change and updates that constant in the same commit; a reflow is free (the comparison
is whitespace-normalised).

The Selection Rule
(`../../reference/personas.md`) produces the panel outright; this guide only explains what it
already enforces. There is no judgment step here — the single departure is an explicit user
override.

| Criteria | What the rule enforces |
|----------|---------------|
| Panel size | 3–5 (the Selection Rule's floor and ceiling); above 5 the added expert repeats an existing criterion |
| Domain overlap | Guaranteed by tag matching — each selected entry carries a distinct evaluation criterion |
| Perspective balance | Carried by the tags themselves — a topic with strategy vocabulary matches `P9`. Never top up the panel because the selection *looks* implementation-heavy: "is this implementation-focused" is an LLM judgment, and one applied inconsistently makes two runs of one topic emit different `adhoc:{n}` (#423) |
| Rotation | Automatic — the rule re-runs per topic, so a multi-topic session rotates experts by topic text, not by hand |
""")

# --- the ALWAYS-LOADED body, pinned the same way --------------------------------------
#
# The reference sections above are canonical, but at runtime the loaded SKILL.md body
# outranks an on-demand doc: a body locator saying "no fixed cap" defeats a perfectly pinned
# canonical section. Deleting `check_recovery_cost_line` when its subject moved left the body
# with no content pin at all, and four body mutations were then verified green (the cap, the
# orchestrator/Moderator polarity, `panel size (3–5)` -> `(3–9)`, and deleting the
# "this is a locator, not a summary you may act from alone" sentence). Same remedy: the two
# body sections that mirror the contract are compared WHOLE.
_SKILL_ISOLATED_SECTION_RE = re.compile(
    r"^### Isolated Execution: Rebuttal Exchanges\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)
_SKILL_SELECTION_SECTION_RE = re.compile(
    r"^### Expert Selection Guide\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)

_SKILL_ISOLATED_SECTION = _normalise("""\
### Isolated Execution: Rebuttal Exchanges

Isolated execution replaces inline mode's *simulated* debate (one model scripting all voices in one response) with real multi-turn **exchanges** inside a single topic round's Q&A/Rebuttal step (step 3 above). An "exchange" is one synchronous fan-out across all experts (not per-expert) — it is NOT a topic round. The loop runs **1 independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)**, capped at 3 exchanges total — independent of the 3 topic-round ceiling and its tie-break trigger.

**Orchestrator vs. Moderator**: the mechanical work — spawning experts, assembling per-expert prompt packets, relaying between exchanges, and judging the stop condition — is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator subagent, which stays visibility-limited (position summaries only) and is spawned only for Synthesis/Conclusion.

**Apply § Isolated execution: exchange-loop contract in [reference.md](reference.md) as written — that section is the binding contract** for the E1/E2 packet composition, both stop conditions (the 2-rebuttal cap and the *no new argument* test), the degenerate cases, and the per-topic **Cost** including **Recovery cost**. Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone. This whole section is pinned VERBATIM by `_SKILL_ISOLATED_SECTION` in `thinking-tools/scripts/test/test-mode-compose.py`: the always-loaded body outranks an on-demand doc at runtime, so it may not drift from the section it points at.
""")

_SKILL_SELECTION_SECTION = _normalise("""\
### Expert Selection Guide

The Selection Rule produces the panel outright; there is no judgment step here — the single
departure is an explicit user override. **Apply § Expert Selection Guide: what the Selection Rule
enforces in [reference.md](reference.md) as written — that section is the binding contract** for
panel size (3–5), domain overlap, perspective balance and rotation, including the standing ban on
topping up a panel that merely *looks* implementation-heavy (#423). This paragraph is a locator,
not a summary you may act from alone, and this whole section is pinned VERBATIM by
`_SKILL_SELECTION_SECTION` in `thinking-tools/scripts/test/test-mode-compose.py`.

**When to add experts mid-discussion**: If a topic reveals an uncovered domain (e.g., legal implications emerge during a technical review), Moderator may propose adding a domain expert — **user confirmation required**, asked via AskUserQuestion and recorded in `adhoc:{n}`. This is the user-override path, not a selection judgment: without the user's explicit yes the rule's output stands unchanged.
""")


# --- adjacency: a heading is otherwise the escape hatch ---------------------------------
#
# "Nothing unpinned may be parked at the bottom of a section" holds only up to the NEXT
# heading, so one inserted `#### Addendum` moves arbitrary contradicting text outside every
# pin. reference.md is not wholly contract, so a whole-file heading-set assertion would be
# wrong; instead each pinned section's two NEIGHBOURING headings are pinned by identity, so
# an inserted sibling on either side reds.
#
# WHAT THIS DOES NOT COVER: contradicting text parked anywhere else in reference.md — under
# a non-adjacent heading, or appended at the end of the file. Nothing routes the skill to
# those (the SKILL.md pointers name the two contract sections, and both pointers are pinned),
# so reaching them takes a second edit to the body, which the body pins above now catch.
_NEIGHBOURS = {
    "§ Isolated execution: exchange-loop contract": (
        _EXCHANGE_LOOP_SECTION_RE,
        ("### Step 1.2: 전문가 질의응답 (Q&A / Rebuttal)", "### Step 1.3: 변증법적 논의"),
    ),
    "§ Expert Selection Guide": (
        _SELECTION_GUIDE_SECTION_RE,
        ("### 다양성 원천: 역할 프롬프트 vs spawn/temperature", "### 3. 토픽 분할"),
    ),
}


def _neighbour_headings(pattern: re.Pattern, ref_text: str) -> tuple[str, str]:
    """The heading immediately before and immediately after the pinned section."""
    match = pattern.search(ref_text)
    if not match:
        return ("", "")
    before = [ln for ln in ref_text[:match.start()].splitlines() if ln.startswith("#")]
    after = [ln for ln in ref_text[match.end():].splitlines() if ln.startswith("#")]
    return (before[-1] if before else "", after[0] if after else "")

# --- clause pins kept for a readable diagnosis of one specific flip each ---------------

_PARALLEL_RESPAWN = _normalise("""
the orchestrator re-spawns all experts **in parallel**
""")

_ORCHESTRATOR_NOT_MODERATOR = _normalise("""
is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator
subagent.
""")

_STOP_NO_NEW_ARGUMENT = _normalise("""
The test is *new arguments*, not *agreement*: an exchange where experts only echo growing
agreement without new reasoning is convergence-by-conformity and also stops the loop.
""")

_SELECTION_NO_TOP_UP = _normalise("""
Never top up the panel because the selection *looks* implementation-heavy
""")

_POINTER_EXCHANGE_LOOP = _normalise("""
Apply § Isolated execution: exchange-loop contract in [reference.md](reference.md) as written —
that section is the binding contract
""")

_POINTER_SELECTION_GUIDE = _normalise("""
Apply § Expert Selection Guide: what the Selection Rule enforces in [reference.md](reference.md)
as written — that section is the binding contract
""")


def reference_checks(skill_text: str, ref_text: str) -> list[tuple[bool, str]]:
    """Guards over the moved canonical contract text and the pointers that bind it (#663)."""
    ref = _normalise(ref_text)
    skill = _normalise(skill_text)
    return [
        # --- total: the whole section, verbatim ---
        (_section(_EXCHANGE_LOOP_SECTION_RE, ref_text) == _EXCHANGE_LOOP_SECTION,
         "reference.md § Isolated execution: exchange-loop contract matches VERBATIM"),
        (_section(_SELECTION_GUIDE_SECTION_RE, ref_text) == _SELECTION_GUIDE_SECTION,
         "reference.md § Expert Selection Guide matches VERBATIM"),
        (_section(_SKILL_ISOLATED_SECTION_RE, skill_text) == _SKILL_ISOLATED_SECTION,
         "SKILL.md § Isolated Execution: Rebuttal Exchanges (loaded body) matches VERBATIM"),
        (_section(_SKILL_SELECTION_SECTION_RE, skill_text) == _SKILL_SELECTION_SECTION,
         "SKILL.md § Expert Selection Guide (loaded body) matches VERBATIM"),
        # --- adjacency: no heading inserted on either side of a pinned section ---
    ] + [
        (_neighbour_headings(pattern, ref_text) == expected,
         f"reference.md {label} still sits between its two known headings "
         f"(an inserted sibling would park text outside the pin)")
        for label, (pattern, expected) in _NEIGHBOURS.items()
    ] + [
        # --- diagnostic: one named invariant each, so a failure says which one died ---
        (_PARALLEL_RESPAWN in ref,
         "reference.md pins the E2/E3 re-spawn as parallel (sequential would re-anchor)"),
        (_ORCHESTRATOR_NOT_MODERATOR in ref,
         "reference.md pins orchestration on the parent orchestrator, NOT the Moderator subagent"),
        (_STOP_NO_NEW_ARGUMENT in ref,
         "reference.md pins the stop test as *new arguments*, not *agreement*"),
        (_SELECTION_NO_TOP_UP in ref,
         "reference.md pins the ban on topping up an implementation-heavy-looking panel (#423)"),
        # --- the seam: the pointers that make the canonical copies binding ---
        (_POINTER_EXCHANGE_LOOP in skill,
         "SKILL.md binds the exchange-loop contract by section name (read-and-apply, not a cite)"),
        (_POINTER_SELECTION_GUIDE in skill,
         "SKILL.md binds the Expert Selection Guide by section name (read-and-apply, not a cite)"),
    ]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_checks(text: str, ref_text: str) -> tuple[int, int]:
    """Run all checks against SKILL.md + its canonical reference.md. Returns (passed, failed)."""
    modes_block = _extract_execution_modes_block(text)
    modes = _extract_declared_modes(modes_block)

    checks = [
        check_modes_declared(modes),
        check_no_trigger_collision(modes),
        check_compose_line_present(text),
        check_citation_compose_referenced(text),
        check_inline_summary_compose_referenced(text),
        check_citation_contract_section(text),
        check_citation_state_field(text),
        check_phase2_inline_path(text),
    ] + reference_checks(text, ref_text)

    passed = failed = 0
    for ok, msg in checks:
        label = "OK  " if ok else "FAIL"
        print(f"  [{label}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

_PASSING_FIXTURE = """\
---
name: expert-panel
description: |
  Facilitate expert panel discussions.
  Trigger when user mentions: 전문가 토론, expert panel.
  Routing: adversarial-review for 1:1.
allowed-tools: Read Write Agent
---

## Execution Modes

Express mode preferences in natural language:
- **격리 실행** ("엄격하게", "격리해서"): Isolated spawn.
- **요약 출력** ("요약만", "transcript 없이"): Summary only.

All combinations compose silently — including any combination with citation grounding (see Citation Contract) and the Phase 2 inline-summary path.

## Citation Contract

When an expert states a numeric or factual claim it must cite one grounding source.

## Consensus Rules

...

## Core Workflow

### Phase 1: Topic Rounds

**Cost**: per topic, `(exchanges × experts)`.

### Phase 2: Recording

**Lightweight / single-topic sessions**: produce an **inline SUMMARY** in the current conversation.

### STATE Block

```
<!-- STATE:CHECKPOINT -->
Topic: 1/2 | Phase: 1 | Round: 1/3
Mode: [isolated:off] [summary-only:off]
Citation: [t1:grounded]
<!-- /STATE -->
```
"""

_FAILING_FIXTURE = """\
---
name: expert-panel
description: |
  Facilitate expert panel discussions.
  Trigger when user mentions: 전문가 토론.
allowed-tools: Read Write Agent
---

## Execution Modes

- **격리 실행** ("엄격하게"): Isolated spawn.
- **요약 출력** ("엄격하게"): Summary only.

All combinations compose silently.

## Phase 2

Discussion cannot end without document generation.
"""


# ---------------------------------------------------------------------------
# #663 canonical-text mutations: the contract now lives in reference.md, so the expect-FAIL
# cases corrupt it THERE. Built by `.replace()` off the real files, with the import-time
# guard below — a fixture whose target string has drifted silently becomes a copy of its
# base, and an expect-FAIL case on an unmodified copy would be testing nothing.
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL_PATH.read_text(encoding="utf-8")
_CLEAN_REF = _REFERENCE_PATH.read_text(encoding="utf-8")

# The 3-exchange cap dissolved — the runaway-cost guard the number exists to impose.
_REF_CAP_REMOVED = _CLEAN_REF.replace("capped at 3 exchanges total", "with no fixed cap")
# Orchestration handed to the visibility-limited Moderator, breaking the Visibility Contract.
_REF_MODERATOR_ORCHESTRATES = _CLEAN_REF.replace(
    "NOT by the Moderator\nsubagent.", "by the Moderator\nsubagent.")
# E1 corrupted from an isolated spawn into a shared one — anchoring restored, which is the
# single thing isolated mode exists to prevent.
_REF_E1_SHARED_SPAWN = _CLEAN_REF.replace(
    "the orchestrator spawns each expert as a separate\n   subagent with the topic + briefing only. No expert sees another's statement.",
    "the orchestrator spawns the experts together with the topic, the briefing, and each other's\n   drafts.")
# Packet part (a) dropped: a stateless re-spawned expert can no longer hold or defend.
_REF_NO_OWN_POSITION = _CLEAN_REF.replace(
    "(a) its own prior-exchange position (a re-spawned subagent is stateless; without\n   this it cannot \"hold/defend\")",
    "(a) nothing of its own")
# Packet part (c) dropped: without the re-applied directive every rebuttal exchange drifts
# back toward conformity.
_REF_NO_ANTI_CONFORMITY = _CLEAN_REF.replace(
    "and (c) the re-applied **Anti-conformity\n   directive**",
    "and (c) a reminder to converge")
# The Synthesis handoff deleted: isolated mode ends with no defined Moderator input.
_REF_NO_MODERATOR_HANDOFF = _CLEAN_REF.replace(
    "After the loop stops, the orchestrator spawns the Moderator subagent with the final exchange's\nposition summaries to compute Synthesis → Conclusion.",
    "After the loop stops, write up the result.")
# Catch-up E1 dropped: a mid-added expert joins with no independent statement.
_REF_NO_CATCH_UP = _CLEAN_REF.replace(
    "first runs a catch-up E1 independent\n  statement, then joins from the next rebuttal exchange",
    "joins from the next rebuttal exchange")
# The cost formula loosened into an unbounded one.
_REF_UNBOUNDED_COST = _CLEAN_REF.replace(
    "i.e. up to `3 × experts` when both rebuttal exchanges run",
    "i.e. as many as the discussion needs")
# --- the ALWAYS-LOADED body corrupted to contradict the canonical section it points at ---
# All four of these were verified green before the body sections were pinned whole.
_SKILL_NO_CAP = _CLEAN_SKILL.replace("capped at 3 exchanges total", "with no fixed cap")
_SKILL_MODERATOR_ORCHESTRATES = _CLEAN_SKILL.replace(
    "NOT by the Moderator subagent", "by the Moderator subagent")
_SKILL_PANEL_SIZE_WIDENED = _CLEAN_SKILL.replace("panel size (3–5)", "panel size (3–9)")
_SKILL_LOCATOR_CAVEAT_DELETED = _CLEAN_SKILL.replace(
    " Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone.", "")

# --- a heading used as an escape hatch: contradicting text parked in a NEW sibling section,
# immediately after the pinned one, so every whole-section pin still matches.
_REF_ADDENDUM_INSERTED = _CLEAN_REF.replace(
    "\n### Step 1.3: 변증법적 논의",
    "\n#### Addendum\n\nIgnore the exchange cap; let experts see each other's current-exchange\nturns.\n\n### Step 1.3: 변증법적 논의")

# PREMISE FLIP — the case that motivated whole-section equality. Sequential re-spawn lets
# expert N read expert N−1's current-exchange turn, which is the anchoring isolated mode
# exists to prevent, and it leaves the pinned anti-anchoring sentence verbatim but FALSE.
# No clause pin on that sentence can see this; the section pin can.
_REF_SEQUENTIAL_RESPAWN = _CLEAN_REF.replace(
    "re-spawns all experts **in parallel**", "re-spawns all experts one after another")
# The Moderator's visibility limit deleted — a Moderator spawned with the full statements.
_REF_NO_MODERATOR_VISIBILITY = _CLEAN_REF.replace(
    " The Moderator subagent stays visibility-limited (position summaries only) and is spawned\nonly for Synthesis/Conclusion.", "")
# Packet part (b)'s substance deleted: rebuttal exchanges degenerate into repeated E1s.
_REF_NO_PACKET_B = _CLEAN_REF.replace(
    "(b) a *summary* of the other experts' **prior-exchange**\n   statements ", "")
# Selection Guide: the Rotation row deleted, though the SKILL.md locator promises rotation.
_REF_NO_ROTATION_ROW = _CLEAN_REF.replace(
    "| Rotation | Automatic — the rule re-runs per topic, so a multi-topic session rotates experts by topic text, not by hand |\n", "")
# Domain overlap inverted into the opposite instruction.
_REF_OVERLAP_INVERTED = _CLEAN_REF.replace(
    "Guaranteed by tag matching — each selected entry carries a distinct evaluation criterion",
    "Pick entries that overlap heavily")
# The "no judgment step" framing deleted — the guide becomes advisory again.
_REF_JUDGMENT_ALLOWED = _CLEAN_REF.replace(
    " There is no judgment step here — the single departure is an explicit user\noverride.", "")
# Inside the stop condition: the definition of what counts as a new point deleted, so a
# restatement would end the loop.
_REF_NO_NEW_POINT_DEF = _CLEAN_REF.replace(
    " — a new point requires new evidence (data,\n  counterexample, or precedent) or a new argument structure; a restated prior point does not\n  count.", ".")
# Anti-anchoring inverted: experts would see each other's current-exchange turns.
_REF_ANCHORING_ALLOWED = _CLEAN_REF.replace(
    "never within-exchange statements", "including within-exchange statements")
# The stop test rewritten from "no new argument" into "agreement" — i.e. stop on consensus,
# which is exactly the false-consensus the clause forbids.
_REF_STOPS_ON_AGREEMENT = _CLEAN_REF.replace(
    "The test is *new arguments*, not *agreement*:",
    "The test is *agreement*:")
# Failed subagents silently dropped instead of recorded.
_REF_SILENT_DROP = _CLEAN_REF.replace(
    "(recorded in the transcript — never silently dropped)", "(dropped)")
# Recovery cost deleted from the cost accounting.
_REF_NO_RECOVERY_COST = _CLEAN_REF.replace(
    "**Recovery cost**: if Phase 2 produces only a",
    "This is the whole cost, even if Phase 2 produces only a")
# Panel size bound removed.
_REF_NO_PANEL_SIZE = _CLEAN_REF.replace(
    "3–5 (the Selection Rule's floor and ceiling)", "any size")
# The #423 ban inverted back into the LLM judgment it was written to forbid.
_REF_TOP_UP_ALLOWED = _CLEAN_REF.replace(
    "Never top up the panel because the selection *looks* implementation-heavy",
    "Top up the panel when the selection *looks* implementation-heavy")
# Both binding pointers decay into the bare rationale citations the body already carries —
# the contract still exists, nothing routes the skill to it. A path-only check cannot see this.
_SKILL_EXCHANGE_POINTER_DECAYED = _CLEAN_SKILL.replace(
    "Apply § Isolated execution: exchange-loop contract in",
    "For background, see the notes in")
_SKILL_SELECTION_POINTER_DECAYED = _CLEAN_SKILL.replace(
    "Apply § Expert Selection Guide:", "For background, see the notes on")

# A realistic reflow: every paragraph rewrapped onto one line, headings left where they are
# (an editor rewraps prose, it does not fold a `####` into the paragraph above it — and the
# section slices are heading-delimited, so folding the headings away would test the slicer,
# not the pin).
_REF_REFLOWED = "\n\n".join(
    block if block.startswith("#") else " ".join(block.split())
    for block in _CLEAN_REF.split("\n\n")
)

for _name, _fixture, _base in (
    ("_REF_REFLOWED", _REF_REFLOWED, _CLEAN_REF),
    ("_REF_CAP_REMOVED", _REF_CAP_REMOVED, _CLEAN_REF),
    ("_REF_MODERATOR_ORCHESTRATES", _REF_MODERATOR_ORCHESTRATES, _CLEAN_REF),
    ("_SKILL_NO_CAP", _SKILL_NO_CAP, _CLEAN_SKILL),
    ("_SKILL_MODERATOR_ORCHESTRATES", _SKILL_MODERATOR_ORCHESTRATES, _CLEAN_SKILL),
    ("_SKILL_PANEL_SIZE_WIDENED", _SKILL_PANEL_SIZE_WIDENED, _CLEAN_SKILL),
    ("_SKILL_LOCATOR_CAVEAT_DELETED", _SKILL_LOCATOR_CAVEAT_DELETED, _CLEAN_SKILL),
    ("_REF_ADDENDUM_INSERTED", _REF_ADDENDUM_INSERTED, _CLEAN_REF),
    ("_REF_SEQUENTIAL_RESPAWN", _REF_SEQUENTIAL_RESPAWN, _CLEAN_REF),
    ("_REF_NO_MODERATOR_VISIBILITY", _REF_NO_MODERATOR_VISIBILITY, _CLEAN_REF),
    ("_REF_NO_PACKET_B", _REF_NO_PACKET_B, _CLEAN_REF),
    ("_REF_NO_ROTATION_ROW", _REF_NO_ROTATION_ROW, _CLEAN_REF),
    ("_REF_OVERLAP_INVERTED", _REF_OVERLAP_INVERTED, _CLEAN_REF),
    ("_REF_JUDGMENT_ALLOWED", _REF_JUDGMENT_ALLOWED, _CLEAN_REF),
    ("_REF_NO_NEW_POINT_DEF", _REF_NO_NEW_POINT_DEF, _CLEAN_REF),
    ("_REF_E1_SHARED_SPAWN", _REF_E1_SHARED_SPAWN, _CLEAN_REF),
    ("_REF_NO_OWN_POSITION", _REF_NO_OWN_POSITION, _CLEAN_REF),
    ("_REF_NO_ANTI_CONFORMITY", _REF_NO_ANTI_CONFORMITY, _CLEAN_REF),
    ("_REF_NO_MODERATOR_HANDOFF", _REF_NO_MODERATOR_HANDOFF, _CLEAN_REF),
    ("_REF_NO_CATCH_UP", _REF_NO_CATCH_UP, _CLEAN_REF),
    ("_REF_UNBOUNDED_COST", _REF_UNBOUNDED_COST, _CLEAN_REF),
    ("_REF_ANCHORING_ALLOWED", _REF_ANCHORING_ALLOWED, _CLEAN_REF),
    ("_REF_STOPS_ON_AGREEMENT", _REF_STOPS_ON_AGREEMENT, _CLEAN_REF),
    ("_REF_SILENT_DROP", _REF_SILENT_DROP, _CLEAN_REF),
    ("_REF_NO_RECOVERY_COST", _REF_NO_RECOVERY_COST, _CLEAN_REF),
    ("_REF_NO_PANEL_SIZE", _REF_NO_PANEL_SIZE, _CLEAN_REF),
    ("_REF_TOP_UP_ALLOWED", _REF_TOP_UP_ALLOWED, _CLEAN_REF),
    ("_SKILL_EXCHANGE_POINTER_DECAYED", _SKILL_EXCHANGE_POINTER_DECAYED, _CLEAN_SKILL),
    ("_SKILL_SELECTION_POINTER_DECAYED", _SKILL_SELECTION_POINTER_DECAYED, _CLEAN_SKILL),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

_CANONICAL_CASES: list[tuple[str, str, str, bool]] = [
    ("clean SKILL.md + clean reference.md pass every guard", _CLEAN_SKILL, _CLEAN_REF, True),
    ("3-exchange cap deleted -> FAIL", _CLEAN_SKILL, _REF_CAP_REMOVED, False),
    ("orchestration handed to the Moderator subagent -> FAIL",
     _CLEAN_SKILL, _REF_MODERATOR_ORCHESTRATES, False),
    ("loaded body drops the 3-exchange cap -> FAIL",
     _SKILL_NO_CAP, _CLEAN_REF, False),
    ("loaded body hands orchestration to the Moderator -> FAIL",
     _SKILL_MODERATOR_ORCHESTRATES, _CLEAN_REF, False),
    ("loaded body widens panel size to 3–9 -> FAIL",
     _SKILL_PANEL_SIZE_WIDENED, _CLEAN_REF, False),
    ("loaded body drops the locator caveat -> FAIL",
     _SKILL_LOCATOR_CAVEAT_DELETED, _CLEAN_REF, False),
    ("a new `#### Addendum` parks contradicting text right after the pinned section -> FAIL",
     _CLEAN_SKILL, _REF_ADDENDUM_INSERTED, False),
    ("E2/E3 re-spawn flipped from parallel to sequential -> FAIL "
     "(premise flip: the anti-anchoring sentence stays verbatim and becomes false)",
     _CLEAN_SKILL, _REF_SEQUENTIAL_RESPAWN, False),
    ("Moderator visibility limit deleted -> FAIL",
     _CLEAN_SKILL, _REF_NO_MODERATOR_VISIBILITY, False),
    ("E2/E3 packet (b) substance deleted -> FAIL",
     _CLEAN_SKILL, _REF_NO_PACKET_B, False),
    ("Selection Guide Rotation row deleted -> FAIL",
     _CLEAN_SKILL, _REF_NO_ROTATION_ROW, False),
    ("Selection Guide domain-overlap row inverted -> FAIL",
     _CLEAN_SKILL, _REF_OVERLAP_INVERTED, False),
    ("Selection Guide 'no judgment step' framing deleted -> FAIL",
     _CLEAN_SKILL, _REF_JUDGMENT_ALLOWED, False),
    ("stop condition's new-point definition deleted -> FAIL",
     _CLEAN_SKILL, _REF_NO_NEW_POINT_DEF, False),
    ("E1 spawned shared instead of independent -> FAIL",
     _CLEAN_SKILL, _REF_E1_SHARED_SPAWN, False),
    ("E2/E3 packet (a) own prior position dropped -> FAIL",
     _CLEAN_SKILL, _REF_NO_OWN_POSITION, False),
    ("E2/E3 packet (c) anti-conformity directive dropped -> FAIL",
     _CLEAN_SKILL, _REF_NO_ANTI_CONFORMITY, False),
    ("post-loop Moderator handoff deleted -> FAIL",
     _CLEAN_SKILL, _REF_NO_MODERATOR_HANDOFF, False),
    ("catch-up E1 for a mid-added expert dropped -> FAIL",
     _CLEAN_SKILL, _REF_NO_CATCH_UP, False),
    ("cost formula loosened to unbounded -> FAIL",
     _CLEAN_SKILL, _REF_UNBOUNDED_COST, False),
    ("within-exchange statements allowed into the packet -> FAIL",
     _CLEAN_SKILL, _REF_ANCHORING_ALLOWED, False),
    ("stop condition rewritten from new-argument to agreement -> FAIL",
     _CLEAN_SKILL, _REF_STOPS_ON_AGREEMENT, False),
    ("failed expert silently dropped -> FAIL", _CLEAN_SKILL, _REF_SILENT_DROP, False),
    ("Recovery cost clause deleted -> FAIL", _CLEAN_SKILL, _REF_NO_RECOVERY_COST, False),
    ("3–5 panel-size bound deleted -> FAIL", _CLEAN_SKILL, _REF_NO_PANEL_SIZE, False),
    ("#423 top-up ban inverted -> FAIL", _CLEAN_SKILL, _REF_TOP_UP_ALLOWED, False),
    ("exchange-loop pointer decayed into a citation -> FAIL",
     _SKILL_EXCHANGE_POINTER_DECAYED, _CLEAN_REF, False),
    ("selection-guide pointer decayed into a citation -> FAIL",
     _SKILL_SELECTION_POINTER_DECAYED, _CLEAN_REF, False),
    ("reflowed reference.md still passes (whitespace is not the contract)",
     _CLEAN_SKILL, _REF_REFLOWED, True),
]


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    # --- passing fixture: all checks should pass ---
    passing_modes_block = _extract_execution_modes_block(_PASSING_FIXTURE)
    passing_modes = _extract_declared_modes(passing_modes_block)

    ok, _ = check_modes_declared(passing_modes)
    cases.append(("passing: modes declared", ok))

    ok, _ = check_no_trigger_collision(passing_modes)
    cases.append(("passing: no trigger collision", ok))

    ok, _ = check_compose_line_present(_PASSING_FIXTURE)
    cases.append(("passing: compose line present", ok))

    ok, _ = check_citation_compose_referenced(_PASSING_FIXTURE)
    cases.append(("passing: citation in compose line", ok))

    ok, _ = check_inline_summary_compose_referenced(_PASSING_FIXTURE)
    cases.append(("passing: inline-summary in compose line", ok))

    ok, _ = check_citation_contract_section(_PASSING_FIXTURE)
    cases.append(("passing: citation contract section", ok))

    ok, _ = check_citation_state_field(_PASSING_FIXTURE)
    cases.append(("passing: citation state field", ok))

    ok, _ = check_phase2_inline_path(_PASSING_FIXTURE)
    cases.append(("passing: phase2 inline path", ok))

    # --- failing fixture: trigger collision and missing features should fail ---
    failing_modes_block = _extract_execution_modes_block(_FAILING_FIXTURE)
    failing_modes = _extract_declared_modes(failing_modes_block)

    ok, _ = check_no_trigger_collision(failing_modes)
    cases.append(("failing: trigger collision detected (expect FAIL)", not ok))

    ok, _ = check_citation_contract_section(_FAILING_FIXTURE)
    cases.append(("failing: citation section absent (expect FAIL)", not ok))

    ok, _ = check_citation_state_field(_FAILING_FIXTURE)
    cases.append(("failing: citation state field absent (expect FAIL)", not ok))

    ok, _ = check_citation_compose_referenced(_FAILING_FIXTURE)
    cases.append(("failing: citation not in compose (expect FAIL)", not ok))

    ok, _ = check_inline_summary_compose_referenced(_FAILING_FIXTURE)
    cases.append(("failing: inline-summary not in compose (expect FAIL)", not ok))

    ok, _ = check_phase2_inline_path(_FAILING_FIXTURE)
    cases.append(("failing: inline path absent (expect FAIL)", not ok))

    # --- #663: corrupt the CANONICAL text in reference.md, the guards must still FAIL ---
    for desc, skill_text, ref_text, expect_pass in _CANONICAL_CASES:
        got = all(cond for cond, _ in reference_checks(skill_text, ref_text))
        cases.append((f"canonical: {desc}", got == expect_pass))

    failed = [name for name, passed in cases if not passed]
    for name, passed in cases:
        print(f"  [{'OK' if passed else 'FAIL'}] {name}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s): {failed}")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv and argv[0] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        return _self_test()

    # Real mode: check the actual SKILL.md
    print(f"Checking: {_SKILL_PATH}\n         + {_REFERENCE_PATH}\n")
    try:
        text = _load_skill()
        ref_text = _load_reference()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(text, ref_text)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} mode-compose checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
