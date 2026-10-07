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
7. (#768) The opt-in delegated mode is declared as a third bullet, the compose line names
   위임 vs 격리 as the one excepted pair (citation/inline combinations stay allowed), and
   reference.md § Delegated execution keeps its clause pins (alternative paths, no worker-spawned
   experts, no independent-review label, one re-request then failure, inline stays default).

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
_WORKER_PATH = _REPO_ROOT / "thinking-tools" / "agents" / "expert-panel-worker.md"


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
    """The canonical modes (incl. the opt-in delegated mode) must be declared."""
    names = {m["name"] for m in modes}
    # COUPLED to the bold mode labels in expert-panel/SKILL.md "## Execution Modes"
    # (the `- **격리 실행** (...)` / `- **요약 출력** (...)` / `- **위임 실행** (...)` bullets). If a mode is
    # intentionally renamed there, update this set too — otherwise this gate silently
    # stops checking that mode (a rename without an update here is a false-OK).
    required = {"격리 실행", "요약 출력", "위임 실행"}
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


def check_delegated_isolated_exclusive(text: str) -> tuple[bool, str]:
    """위임 vs 격리 is declared as an EXCEPTION to silent composition (#768); the rest stay allowed."""
    compose = _find_compose_line(text)
    # Order-insensitive on the pair, but `except` must introduce it: a bare mention of both
    # modes would also pass if the line merely listed them as composing.
    excepted = re.search(r"except\s+(위임\s+vs\s+격리|격리\s+vs\s+위임)", compose)
    if not excepted:
        return False, (
            "compose line does not declare 위임 vs 격리 as an exception "
            "('except 위임 vs 격리') — the two paths must not compose silently"
        )
    if "citation" not in compose.lower() or "inline" not in compose.lower():
        return False, "compose line dropped citation grounding / inline path while adding the exception"
    return True, "compose line excepts 위임 vs 격리 and keeps citation/inline combinations"


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
_ROLE_CONTRACT_SECTION_RE = re.compile(
    r"^## Role Contract\b.*?(?=^#{2,4} |\Z)",
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

Isolated execution replaces the simulated pass with real multi-turn **exchanges** inside a topic's single
Q&A/Rebuttal step (SKILL.md Phase 1 step 3). An "exchange" is one synchronous
fan-out across all experts (not per-expert) — it is NOT a separate discussion cycle. The loop runs **1
independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)**, capped at 3 exchanges total,
once per topic — there is no outer topic-round loop around it.

**Orchestrator vs. Moderator**: in isolated mode the mechanical work — spawning experts,
assembling per-expert prompt packets, writing the practitioner review, relaying between exchanges,
and judging the stop condition — is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator
subagent. The Moderator subagent stays visibility-limited (position summaries and the practitioner review only) and is spawned
only for Synthesis/Conclusion. This keeps the Moderator Visibility Contract intact: the
orchestrator already holds every statement, so it is the one allowed to summarize and relay.

**Exchange loop**:

1. **E1 — Independent** (anchoring-free): the orchestrator spawns each expert as a separate
   subagent with the topic + briefing only. No expert sees another's statement. Each E1 spawn is a fresh, non-fork subagent, so it inherits none of the parent's debate history. The orchestrator
   collects all statements.
2. **E2/E3 — Rebuttal**: the orchestrator re-spawns all experts **in parallel**, each receiving a
   packet of — (a) its own prior-exchange position (a re-spawned subagent is stateless; without
   this it cannot "hold/defend"), (b) a *summary* of the other experts' **prior-exchange**
   statements (never within-exchange statements — parallel re-spawn means no expert sees another's
   current-exchange turn, preserving anti-anchoring), and (c) the re-applied **Anti-conformity
   directive** (defined at the top of SKILL.md § Phase 1: Topic Rounds), and (d) the practitioner
   review (implementation and failure review), which the orchestrator writes once after E1 from
   the E1 statements — it is neither a spawn nor an exchange. Each expert then (a)
   holds and defends, (b) rebuts a specific point with new evidence, or (c) revises.

**Exchange records (restore source)**: the moment an expert's statement is collected, the
orchestrator Writes it — before touching STATE — to
`{discussion-dir}/_exchanges/t{n}-e{i}-{expert-id}.md` (`{discussion-dir}` =
`docs/discussions/{YYYYMMDD}_{name}/`; the topic briefing goes to `t{n}-briefing.md` and the
practitioner review to `t{n}-review.md`), then adds
the expert to `Collected` and advances `Rebuttal`. These are internal restore records, not the
user-facing transcript: they are written in every isolated session, including summary-only,
which skips only the Phase 2 transcripts. STATE holds only the counters, the collected-expert
set, and the `Records` directory — never statement prose. Restore rules: [STATE Block 복원
상세](#state-block-복원-상세).

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
position summaries to compute Synthesis → Conclusion. Stopping — by the cap or by *no new argument* — is not itself a verdict: the outcome follows SKILL.md § Topic Conclusion.
Each position summary carries the expert's final position, evidence source, conditions, objection
reason and vote; the practitioner review goes with them, the full Q&A never does. The Moderator is
the independent final reviewer: it may set `held:evidence` but never changes a vote, re-runs the
loop, or adds experts.

**Degenerate cases**:

- An expert subagent that fails, returns empty, or returns no final text at all is retried once; on
  a second failure the exchange proceeds with the remaining experts (recorded in the exchange records — never silently dropped).
  A subagent that returns only idle notifications and no final text after one re-request counts as
  unavailable and takes this same fallback (#647) — never wait on it further.
- If fewer than 3 valid experts remain after those retries, the loop stops for that topic: no
  further exchange and no vote, and the topic is `held:quorum` (SKILL.md § Topic Conclusion).
  One or zero remaining experts never produce a consensus or a synthesis.
- An expert added mid-discussion (see Expert Selection Guide) first runs a catch-up E1 independent
  statement, then joins from the next rebuttal exchange.

**Cost**: per topic, `(exchanges × experts)` expert subagents — `exchanges` = 1 (independent) +
1–2 (rebuttal), i.e. up to `3 × experts` when both rebuttal exchanges run, fewer when early-stop
fires — plus 1 Moderator subagent for Synthesis. The practitioner review is written by the
orchestrator and adds no subagent.
Every expert run is a new spawn (a re-spawned subagent is stateless), so on this path runs and
spawns are equal: at most `3N` expert spawns + 1 Moderator per topic for N experts. Counted
separately, never folded into that ceiling: **added experts** (a mid-added expert costs 1
catch-up E1 plus each later exchange it joins), **retries** (at most 1 extra spawn per failed
expert per exchange), and **restore** (re-collecting only the experts whose records are
missing — never a whole exchange whose records survive).
**Recovery cost**: if Phase 2 produces only a
compressed final message or a content-free sign-off (e.g. due to context pressure), the user must
re-request the full record — add one full-panel context reload to the effective cost. This
recovery overhead is avoided by the inline SUMMARY path (lightweight sessions) and by the full
3-file output (multi-topic sessions). Choose isolated mode when independence and genuine turn
exchange matter more than speed — inline mode stays the default for quick reviews.
""")

# #793: who runs the panel, who synthesizes, and what the practitioners are. Pinned whole for
# the same reason as the exchange loop: a one-word flip ("never vote" -> "vote") would pass any
# clause pin that sat a sentence away.
_ROLE_CONTRACT_SECTION = _normalise("""\
## Role Contract

**Canonical text (#793).** SKILL.md § Participants points here; this section is the binding
contract for who runs the panel, who synthesizes, and what the practitioners are. Its whole text
— heading to the next heading — is pinned VERBATIM by `_ROLE_CONTRACT_SECTION` in
`thinking-tools/scripts/test/test-mode-compose.py`; editing it is a deliberate contract change and
updates that constant in the same commit (a reflow is free).

- **Facilitator** — whoever runs the panel: the main context in inline and isolated mode (the
  *orchestrator* of the exchange-loop contract). It selects experts, prepares inputs, writes the
  neutral briefing and the practitioner review, spawns and relays (isolated), keeps the records,
  judges *no new argument*, and ends the exchange loop only by the stop conditions. Fact requests
  and decisions go to the user through it; a mid-discussion expert is only *proposed* by it and
  needs the user's explicit yes. It never ends a topic outside the stop conditions and
  SKILL.md § Topic Conclusion.
- **Moderator** — the final synthesis role only; no vote, no facilitation power. In isolated mode
  it is a separate subagent spawned once per topic after the loop stops, the independent final
  reviewer: it receives each expert's final position summary (position, evidence source,
  conditions, objection reason, vote) plus the practitioner review — never the full Q&A. In inline
  mode the facilitator writes the synthesis under the Moderator label with the same
  [Synthesis Checklist](#synthesis-checklist) and never calls it an independent review. Either
  way the Moderator checks unsupported evidence and omissions and may set `held:evidence`, but
  never changes an expert's vote, re-runs the loop past its cap, or adds experts.
- **Optimistic Practitioner / Critical Practitioner** — required review perspectives, not
  separate agents and not participants: the facilitator writes them, and no extra agent is spawned
  by default. The Optimistic Practitioner gives the **implementation review** (minimal viable
  plan, resources, prerequisites, rollout order, how success is checked); the Critical
  Practitioner gives the **failure review** (failure scenarios, operating burden, stop/abort
  conditions, recovery, alternatives). They never vote and never count toward quorum — only the
  selected domain experts do.

**Order per topic**: (1) a neutral facts-and-constraints briefing by the facilitator, with no
pro/con framing; (2) the experts' independent statements; (3) Q&A/Rebuttal, opened by the
practitioner review written after the independent statements; (4) dialectic; (5) conclusion. The
review adds no exchange: in isolated mode it rides in the E2/E3 packets. Inline independence is a
prompt-level contract only; isolated E1 enforces it by input boundary.

**Evidence honesty**: a claim is a fact with its source, an assumption, an estimate, or a
verification plan, and is labeled as such. Never invent anecdotes, improvement rates, failure
probabilities, dates or projects, and never present simulated roles as verified facts or
independent runs. The final output carries the conclusion, evidence, implementation plan,
failure and stop conditions, dissent, and unresolved items.

---
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
| Perspective balance | Carried by the tags themselves — a topic with strategy vocabulary matches `product-strategy-expert`. Never top up the panel because the selection *looks* implementation-heavy: "is this implementation-focused" is an LLM judgment, and one applied inconsistently makes two runs of one topic emit different `adhoc:{n}` (#423) |
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
_SKILL_CONCLUSION_SECTION_RE = re.compile(
    r"^### Topic Conclusion\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)
_SKILL_SELECTION_SECTION_RE = re.compile(
    r"^### Expert Selection Guide\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)

# #750: these three loaded-body constants were re-pinned to the compact SKILL.md sections (same
# whole-section verbatim comparison) when SKILL.md shrank under Codex's 8,000-byte invoked-skill
# limit; the long forms stay canonical in reference.md, whose own pins are unchanged.
_SKILL_ISOLATED_SECTION = _normalise("""\
### Isolated Execution: Rebuttal Exchanges

Isolated mode runs **1 independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)** in a topic's Q&A/Rebuttal step, capped at 3 exchanges total.

**Orchestrator vs. Moderator**: spawning experts, assembling packets, relaying between exchanges, and judging the stop condition is done by the **parent orchestrator**, NOT by the Moderator subagent, which sees final position summaries and the practitioner review only and is spawned only for Synthesis/Conclusion.

**Apply § Isolated execution: exchange-loop contract in [reference.md](reference.md) as written — that section is the binding contract** for packets, exchange records, stop conditions (2-rebuttal cap, *no new argument* test), degenerate cases and **Cost**. Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone.
""")

_SKILL_CONCLUSION_SECTION = _normalise("""\
### Topic Conclusion

Each topic ends in exactly one outcome after the rebuttal stage stops:

1. **Consensus** — unanimity allowing up to 1 minority dissent → `consensus-reached`.
2. **Weighted vote** (no consensus): each valid expert votes High = 3, Medium = 2, Low = 1 points; `margin` = the top option's points minus the runner-up's. `margin ≥ 2` → the top option wins, `tie-broken`. `margin = 1` → `tie-broken`, and SUMMARY.md marks the winner "Conditional — requires validation".
3. **Hold** — no winner is invented: `held:tie` when `margin = 0`, `held:evidence` when the Moderator judges the deciding claims unverifiable without facts the user must supply ([Phase 3](#phase-3-authority)), `held:quorum` when fewer than 3 valid experts remain after retries — then no vote runs at all. A held topic is never recorded as `tie-broken` or Conditional.

SUMMARY.md records the outcome, vote breakdown and dissent; held topics also go to UNRESOLVED.md with the reason; STATE `Topic-status`, SUMMARY.md and UNRESOLVED.md name the same outcome.
""")

_SKILL_SELECTION_SECTION = _normalise("""\
### Expert Selection Guide

**Apply § Expert Selection Guide: what the Selection Rule enforces in [reference.md](reference.md) as written — that section is the binding contract** for panel size (3–5) and the ban on topping up a panel that merely *looks* implementation-heavy (#423). This paragraph is a locator, not a summary you may act from alone.

**When to add experts mid-discussion**: for an uncovered domain, the facilitator may propose an expert — **user confirmation required**, asked via AskUserQuestion and recorded in `adhoc:{n}`; without an explicit yes the rule's output stands.
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
    "§ Role Contract": (
        _ROLE_CONTRACT_SECTION_RE,
        ("## Table of Contents", "## Phase 0: 토론 준비 (상세)"),
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
        (_section(_ROLE_CONTRACT_SECTION_RE, ref_text) == _ROLE_CONTRACT_SECTION,
         "reference.md § Role Contract matches VERBATIM"),
        (_section(_SELECTION_GUIDE_SECTION_RE, ref_text) == _SELECTION_GUIDE_SECTION,
         "reference.md § Expert Selection Guide matches VERBATIM"),
        (_section(_SKILL_ISOLATED_SECTION_RE, skill_text) == _SKILL_ISOLATED_SECTION,
         "SKILL.md § Isolated Execution: Rebuttal Exchanges (loaded body) matches VERBATIM"),
        (_section(_SKILL_SELECTION_SECTION_RE, skill_text) == _SKILL_SELECTION_SECTION,
         "SKILL.md § Expert Selection Guide (loaded body) matches VERBATIM"),
        (_section(_SKILL_CONCLUSION_SECTION_RE, skill_text) == _SKILL_CONCLUSION_SECTION,
         "SKILL.md § Topic Conclusion (loaded body) matches VERBATIM"),
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
        (_normalise("There is no outer topic-round repeat") in skill,
         "SKILL.md pins one cycle per topic (no topic-round repeat)"),
        (_normalise("`held:tie` when `margin = 0`") in skill,
         "SKILL.md pins a margin-0 vote as held:tie, never a winner"),
        (_normalise("`held:quorum` when fewer than 3 valid experts remain after retries") in skill,
         "SKILL.md pins held:quorum below 3 valid experts"),
        (_normalise("an expert with no record is never counted as done by inference") in skill,
         "SKILL.md restore invariant: no completion by inference"),
        (_normalise("orchestrator Writes it — before touching STATE") in ref,
         "reference.md pins record-before-STATE ordering"),
        (_normalise("Never mark an expert, an exchange, or a topic complete from a counter alone.") in ref,
         "reference.md restore: no completion from a counter"),
        (_normalise("One or zero remaining experts never produce a consensus or a synthesis.") in ref,
         "reference.md pins no consensus from 1 or 0 experts"),
        (_normalise("Counted separately, never folded into that ceiling") in ref,
         "reference.md cost keeps retries/added/restore outside the 3N ceiling"),
        (_normalise("outside votes and quorum") in skill,
         "SKILL.md keeps the practitioners outside votes and quorum (#793)"),
        (_normalise("independent subagent only in isolated mode") in skill,
         "SKILL.md calls the Moderator independent only in isolated mode (#793)"),
        (_normalise("(1) **Briefing**: neutral facts and constraints, no pro/con") in skill,
         "SKILL.md keeps the briefing neutral, before the independent statements (#793)"),
        (_normalise("not separate agents") in skill,
         "SKILL.md keeps the practitioners from being spawned as agents (#793)"),
        (_normalise("a topic ends only via stop conditions and Topic Conclusion") in skill
         and _normalise("never alters votes, re-runs or adds experts") in skill,
         "SKILL.md Phase 3 gives no force-close and no vote/re-run power to the Moderator (#793)"),
        (_normalise("Apply reference.md § Role Contract (binding)") in skill,
         "SKILL.md binds the Role Contract by section name (#793)"),
        # --- the seam: the pointers that make the canonical copies binding ---
        (_POINTER_EXCHANGE_LOOP in skill,
         "SKILL.md binds the exchange-loop contract by section name (read-and-apply, not a cite)"),
        (_POINTER_SELECTION_GUIDE in skill,
         "SKILL.md binds the Expert Selection Guide by section name (read-and-apply, not a cite)"),
    ]


# --- #768: delegated execution (opt-in worker path) ------------------------------------
# Clause pins, not a whole-section pin: the section carries measured-cost prose that will be
# reworded once #768 reports, so only the invariants that keep the two paths from blending are
# pinned, each with its own diagnosis.
_DELEGATED_SECTION_RE = re.compile(
    r"^#### Delegated execution \(위임 실행\).*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)


def delegated_reference_checks(skill_text: str, ref_text: str) -> list[tuple[bool, str]]:
    """Guards over reference.md § Delegated execution and the SKILL.md pointer that binds it (#768)."""
    section = _section(_DELEGATED_SECTION_RE, ref_text)
    skill = _normalise(skill_text)
    return [
        (bool(section), "reference.md has the '#### Delegated execution (위임 실행)' section"),
        (_normalise("alternative paths, never combined") in section,
         "reference.md § Delegated execution: isolated and delegated are alternative paths, never combined"),
        (_normalise("a worker never spawns experts") in section,
         "reference.md § Delegated execution: a worker never spawns experts (no nested subagents)"),
        (_normalise("요약 출력 and citation grounding compose with either path") in section,
         "reference.md § Delegated execution: 요약 출력 and citation grounding compose with either path"),
        (_normalise("the synthesis is never labeled an independent review") in section,
         "reference.md § Delegated execution: the synthesis is never labeled an independent review"),
        (_normalise("re-request it once; if the reply still lacks it, report the delegated run as failed") in section,
         "reference.md § Delegated execution: one re-request, then the run is reported failed"),
        (_normalise("The inline path stays the default") in section,
         "reference.md § Delegated execution: the inline path stays the default (opt-in only)"),
        (_normalise("Apply reference.md § Delegated execution") in skill,
         "SKILL.md binds the delegated-execution section by name (read-and-apply, not a cite)"),
        # The loaded body outranks reference.md: a bullet saying "SUMMARY only" made the caller drop
        # the 진행 기록 in a live 2026-10-07 run even with the relay rule in reference.md (#768).
        (_normalise("relay its SUMMARY + 진행 기록") in skill,
         "SKILL.md 위임 실행 bullet tells the caller to relay the 진행 기록 with the SUMMARY"),
        (_normalise("The 진행 기록 is kept under 요약 출력 too; it is the caller's only way to audit the procedure.") in section,
         "reference.md § Delegated execution: the return carries a 진행 기록, kept under 요약 출력 too"),
        (_normalise("relay the SUMMARY marked `절차 확인 불가` rather than presenting the procedure as verified") in section,
         "reference.md § Delegated execution: a missing 진행 기록 is re-requested once, then marked 절차 확인 불가"),
    ]


# The worker's panel never leaves its context, so its return is the only audit trail: the 2026-10-07
# n=1 run returned a SUMMARY with no text block anywhere in the worker transcript, and nothing showed
# whether the independent statements, practitioner review or rebuttals happened (#768). These pin
# the trail's required items inside the worker's Final Response Contract, not elsewhere in the file.
_WORKER_CONTRACT_RE = re.compile(r"^## Final Response Contract\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
_WORKER_TRAIL_ITEMS = (
    ("진행 기록 (한 컨텍스트 시뮬레이션, 독립 실행 아님)", "the 진행 기록 section, labeled as one context's simulation"),
    ("kept even under 요약 출력", "the 진행 기록 survives 요약 출력"),
    ("`[{Expert} — independent] {position} — {key reason}`", "each expert's independent statement gist"),
    ("one 실행안 line and one 실패 line (no vote)", "the practitioner review, non-voting"),
    ("`반박: {0|1|2}회`", "the rebuttal count, capped at 2"),
    ("(`2회 상한` or `새 논점 없음: {why}`)", "the rebuttal stop reason"),
)


def worker_audit_checks(worker_text: str) -> list[tuple[bool, str]]:
    """The worker's Final Response Contract requires an auditable 진행 기록 (#768)."""
    contract = _section(_WORKER_CONTRACT_RE, worker_text)
    return [(bool(contract), "expert-panel-worker.md has a '## Final Response Contract' section")] + [
        (_normalise(item) in contract, f"worker Final Response Contract requires {why}")
        for item, why in _WORKER_TRAIL_ITEMS
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
        check_delegated_isolated_exclusive(text),
    ] + reference_checks(text, ref_text) + delegated_reference_checks(text, ref_text) + worker_audit_checks(
        _WORKER_PATH.read_text(encoding="utf-8"))

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
- **위임 실행** ("위임해서", "워커에게 맡겨"): opt-in; one worker runs the panel.

Modes compose silently with each other and citation grounding (see Citation Contract), except 위임 vs 격리; Phase 2 then picks the inline-summary path or files.

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
Topic: 1/2 | Phase: 1
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
# --- #793: the role contract ---
# Practitioners turned into voters, inflating every tally and quorum.
_REF_PRACTITIONERS_VOTE = _CLEAN_REF.replace(
    "They never vote and never count toward quorum", "They vote and count toward quorum")
_SKILL_PRACTITIONERS_VOTE = _CLEAN_SKILL.replace("outside votes and quorum", "voting members")
# The loaded body turns the briefing back into pro/con framing before E1.
_SKILL_FRAMED_BRIEFING = _CLEAN_SKILL.replace(
    "(1) **Briefing**: neutral facts and constraints, no pro/con", "(1) **Briefing** by the practitioners (pro/con)")
# The loaded body spawns the practitioners as agents.
_SKILL_PRACTITIONER_AGENTS = _CLEAN_SKILL.replace("not separate agents", "spawned as separate agents")
# The loaded body hands force-close back to the Moderator.
_SKILL_MODERATOR_FORCE_CLOSE = _CLEAN_SKILL.replace(
    "a topic ends only via stop conditions and Topic Conclusion", "the Moderator may force-close a topic")
# The Moderator allowed to overrule the experts it summarizes.
_REF_MODERATOR_REVOTES = _CLEAN_REF.replace(
    "never changes an expert's vote", "may change an expert's vote")
# The practitioner review turned into an extra exchange, breaking the 3N ceiling.
_REF_REVIEW_IS_EXCHANGE = _CLEAN_REF.replace(
    "it is neither a spawn nor an exchange", "it runs as one more exchange")

# --- the ALWAYS-LOADED body corrupted to contradict the canonical section it points at ---
# All four of these were verified green before the body sections were pinned whole.
_SKILL_NO_CAP = _CLEAN_SKILL.replace("capped at 3 exchanges total", "with no fixed cap")
_SKILL_MODERATOR_ORCHESTRATES = _CLEAN_SKILL.replace(
    "NOT by the Moderator subagent", "by the Moderator subagent")
_SKILL_PANEL_SIZE_WIDENED = _CLEAN_SKILL.replace("panel size (3–5)", "panel size (3–9)")
_SKILL_LOCATOR_CAVEAT_DELETED = _CLEAN_SKILL.replace(
    " Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone.", "")

# --- #783: one cycle per topic, held outcomes never invent a winner, restore trusts records ---
# The always-loaded body flips back to a repeat cycle.
_SKILL_ROUNDS_BACK = _CLEAN_SKILL.replace(
    "There is no outer topic-round repeat", "Each topic may repeat up to 3 rounds")
# A margin-0 vote turned into a winner instead of a hold.
_SKILL_TIE_WINS = _CLEAN_SKILL.replace(
    "`held:tie` when `margin = 0`", "`tie-broken` when `margin = 0`")
# The quorum hold deleted: fewer than 3 experts would proceed to a vote.
_SKILL_QUORUM_DROPPED = _CLEAN_SKILL.replace(
    "`held:quorum` when fewer than 3 valid experts remain after retries — then no vote runs at all", "")
# Restore allowed to count an expert as done with no record on disk.
_SKILL_INFER_DONE = _CLEAN_SKILL.replace(
    "an expert with no record is never counted as done by inference",
    "an expert with no record may be counted as done")
# Record ordering flipped: STATE first, so a crash between the two loses the statement.
_REF_STATE_BEFORE_RECORD = _CLEAN_REF.replace(
    "orchestrator Writes it — before touching STATE",
    "orchestrator Writes it — after updating STATE")
# The counter-only completion ban deleted from the restore procedure.
_REF_INFER_DONE = _CLEAN_REF.replace(
    "Never mark an expert, an exchange, or a topic complete from a counter alone.", "")
# Quorum loss rewritten so the survivors go on to a consensus.
_REF_QUORUM_PROCEEDS = _CLEAN_REF.replace(
    "One or zero remaining experts never produce a consensus or a synthesis.",
    "The remaining experts proceed to consensus as usual.")
# Retries/added experts/restore folded back into the 3N ceiling.
_REF_RETRIES_FOLDED = _CLEAN_REF.replace(
    "Counted\nseparately, never folded into that ceiling", "Included in that ceiling")

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
    " The Moderator subagent stays visibility-limited (position summaries and the practitioner review only) and is spawned\nonly for Synthesis/Conclusion.", "")
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
    "(recorded in the exchange records — never silently dropped)", "(dropped)")
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

# --- #768: delegated execution ---
# The compose line loses the exception: 위임 and 격리 would compose silently (nested spawning).
_SKILL_NO_EXCEPTION = _CLEAN_SKILL.replace("except 위임 vs 격리", "including 위임 and 격리")
# The two paths flipped into a combination.
_REF_PATHS_COMPOSE = _CLEAN_REF.replace("alternative paths, never combined", "paths that combine freely")
# The worker allowed to spawn per-expert subagents.
_REF_WORKER_SPAWNS = _CLEAN_REF.replace("a worker never spawns experts", "a worker spawns experts")
# The single-context synthesis dressed up as an independent review.
_REF_SYNTHESIS_INDEPENDENT = _CLEAN_REF.replace(
    "the synthesis is never labeled an independent review", "the synthesis is labeled an independent review")
# The delegated bullet removed from the loaded body: a required mode goes missing.
_SKILL_NO_DELEGATED_BULLET = re.sub(r"^- \*\*위임 실행\*\*.*\n", "", _CLEAN_SKILL, flags=re.MULTILINE)
# A delegated trigger colliding with an existing one: ambiguous routing.
_SKILL_DELEGATED_COLLISION = _CLEAN_SKILL.replace('("위임해서",', '("엄격하게",')

# A realistic reflow: every paragraph rewrapped onto one line, headings left where they are
# (an editor rewraps prose, it does not fold a `####` into the paragraph above it — and the
# section slices are heading-delimited, so folding the headings away would test the slicer,
# not the pin).
_REF_REFLOWED = "\n\n".join(
    block if block.startswith("#") else " ".join(block.split())
    for block in _CLEAN_REF.split("\n\n")
)

_CLEAN_WORKER = _WORKER_PATH.read_text(encoding="utf-8")
# The audit trail dropped from the worker contract, or its rebuttal count un-capped.
_WORKER_NO_TRAIL = _CLEAN_WORKER.replace("진행 기록 (한 컨텍스트 시뮬레이션, 독립 실행 아님)", "진행 메모")
_WORKER_TRAIL_UNCAPPED = _CLEAN_WORKER.replace("`반박: {0|1|2}회`", "`반박: {n}회`")
_WORKER_TRAIL_OPTIONAL_IN_SUMMARY = _CLEAN_WORKER.replace("kept even\n  under 요약 출력", "skipped\n  under 요약 출력")
# The loaded bullet back to "SUMMARY only", which made a live caller drop the trail.
_SKILL_BULLET_SUMMARY_ONLY = _CLEAN_SKILL.replace("relay its SUMMARY + 진행 기록", "returns SUMMARY only")
# The caller allowed to present a SUMMARY without its trail as verified.
_REF_TRAIL_UNCHECKED = _CLEAN_REF.replace(
    "relay the SUMMARY marked `절차 확인 불가` rather than presenting the procedure as verified",
    "relay the SUMMARY as is")
# The trail made optional under summary-only output.
_REF_TRAIL_DROPPED_IN_SUMMARY = _CLEAN_REF.replace(
    "The 진행 기록 is kept under 요약 출력 too;", "The 진행 기록 is skipped under 요약 출력;")

for _name, _fixture, _base in (
    ("_REF_REFLOWED", _REF_REFLOWED, _CLEAN_REF),
    ("_WORKER_NO_TRAIL", _WORKER_NO_TRAIL, _CLEAN_WORKER),
    ("_WORKER_TRAIL_UNCAPPED", _WORKER_TRAIL_UNCAPPED, _CLEAN_WORKER),
    ("_WORKER_TRAIL_OPTIONAL_IN_SUMMARY", _WORKER_TRAIL_OPTIONAL_IN_SUMMARY, _CLEAN_WORKER),
    ("_REF_TRAIL_UNCHECKED", _REF_TRAIL_UNCHECKED, _CLEAN_REF),
    ("_SKILL_BULLET_SUMMARY_ONLY", _SKILL_BULLET_SUMMARY_ONLY, _CLEAN_SKILL),
    ("_REF_TRAIL_DROPPED_IN_SUMMARY", _REF_TRAIL_DROPPED_IN_SUMMARY, _CLEAN_REF),
    ("_SKILL_NO_EXCEPTION", _SKILL_NO_EXCEPTION, _CLEAN_SKILL),
    ("_REF_PATHS_COMPOSE", _REF_PATHS_COMPOSE, _CLEAN_REF),
    ("_REF_WORKER_SPAWNS", _REF_WORKER_SPAWNS, _CLEAN_REF),
    ("_REF_SYNTHESIS_INDEPENDENT", _REF_SYNTHESIS_INDEPENDENT, _CLEAN_REF),
    ("_SKILL_NO_DELEGATED_BULLET", _SKILL_NO_DELEGATED_BULLET, _CLEAN_SKILL),
    ("_SKILL_DELEGATED_COLLISION", _SKILL_DELEGATED_COLLISION, _CLEAN_SKILL),
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
    ("_SKILL_ROUNDS_BACK", _SKILL_ROUNDS_BACK, _CLEAN_SKILL),
    ("_SKILL_TIE_WINS", _SKILL_TIE_WINS, _CLEAN_SKILL),
    ("_SKILL_QUORUM_DROPPED", _SKILL_QUORUM_DROPPED, _CLEAN_SKILL),
    ("_SKILL_INFER_DONE", _SKILL_INFER_DONE, _CLEAN_SKILL),
    ("_REF_STATE_BEFORE_RECORD", _REF_STATE_BEFORE_RECORD, _CLEAN_REF),
    ("_REF_INFER_DONE", _REF_INFER_DONE, _CLEAN_REF),
    ("_REF_QUORUM_PROCEEDS", _REF_QUORUM_PROCEEDS, _CLEAN_REF),
    ("_REF_RETRIES_FOLDED", _REF_RETRIES_FOLDED, _CLEAN_REF),
    ("_REF_PRACTITIONERS_VOTE", _REF_PRACTITIONERS_VOTE, _CLEAN_REF),
    ("_SKILL_PRACTITIONERS_VOTE", _SKILL_PRACTITIONERS_VOTE, _CLEAN_SKILL),
    ("_REF_MODERATOR_REVOTES", _REF_MODERATOR_REVOTES, _CLEAN_REF),
    ("_SKILL_FRAMED_BRIEFING", _SKILL_FRAMED_BRIEFING, _CLEAN_SKILL),
    ("_SKILL_PRACTITIONER_AGENTS", _SKILL_PRACTITIONER_AGENTS, _CLEAN_SKILL),
    ("_SKILL_MODERATOR_FORCE_CLOSE", _SKILL_MODERATOR_FORCE_CLOSE, _CLEAN_SKILL),
    ("_REF_REVIEW_IS_EXCHANGE", _REF_REVIEW_IS_EXCHANGE, _CLEAN_REF),
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
    ("loaded body allows a repeat topic-round cycle -> FAIL",
     _SKILL_ROUNDS_BACK, _CLEAN_REF, False),
    ("loaded body records a margin-0 vote as a winner -> FAIL",
     _SKILL_TIE_WINS, _CLEAN_REF, False),
    ("loaded body drops the held:quorum rule -> FAIL",
     _SKILL_QUORUM_DROPPED, _CLEAN_REF, False),
    ("loaded body lets restore infer completion without a record -> FAIL",
     _SKILL_INFER_DONE, _CLEAN_REF, False),
    ("record written after the STATE update -> FAIL",
     _CLEAN_SKILL, _REF_STATE_BEFORE_RECORD, False),
    ("restore no-completion-from-a-counter rule deleted -> FAIL",
     _CLEAN_SKILL, _REF_INFER_DONE, False),
    ("quorum loss rewritten to proceed to consensus -> FAIL",
     _CLEAN_SKILL, _REF_QUORUM_PROCEEDS, False),
    ("retries/added/restore folded into the 3N ceiling -> FAIL",
     _CLEAN_SKILL, _REF_RETRIES_FOLDED, False),
    ("practitioners made voters in the Role Contract -> FAIL",
     _CLEAN_SKILL, _REF_PRACTITIONERS_VOTE, False),
    ("loaded body makes the practitioners voting members -> FAIL",
     _SKILL_PRACTITIONERS_VOTE, _CLEAN_REF, False),
    ("loaded body frames the briefing pro/con -> FAIL",
     _SKILL_FRAMED_BRIEFING, _CLEAN_REF, False),
    ("loaded body spawns the practitioners as agents -> FAIL",
     _SKILL_PRACTITIONER_AGENTS, _CLEAN_REF, False),
    ("loaded body gives the Moderator force-close -> FAIL",
     _SKILL_MODERATOR_FORCE_CLOSE, _CLEAN_REF, False),
    ("Moderator allowed to change an expert's vote -> FAIL",
     _CLEAN_SKILL, _REF_MODERATOR_REVOTES, False),
    ("practitioner review run as an extra exchange -> FAIL",
     _CLEAN_SKILL, _REF_REVIEW_IS_EXCHANGE, False),
    ("compose line without the `except 위임 vs 격리` clause -> FAIL",
     _SKILL_NO_EXCEPTION, _CLEAN_REF, False),
    ("delegated and isolated paths declared combinable -> FAIL",
     _CLEAN_SKILL, _REF_PATHS_COMPOSE, False),
    ("delegated worker allowed to spawn experts -> FAIL",
     _CLEAN_SKILL, _REF_WORKER_SPAWNS, False),
    ("delegated synthesis labeled an independent review -> FAIL",
     _CLEAN_SKILL, _REF_SYNTHESIS_INDEPENDENT, False),
    ("delegated bullet removed from the loaded body -> FAIL",
     _SKILL_NO_DELEGATED_BULLET, _CLEAN_REF, False),
    ("delegated trigger colliding with an existing trigger -> FAIL",
     _SKILL_DELEGATED_COLLISION, _CLEAN_REF, False),
    ("위임 실행 bullet says SUMMARY only (trail dropped by the caller) -> FAIL",
     _SKILL_BULLET_SUMMARY_ONLY, _CLEAN_REF, False),
    ("caller relays a trail-less SUMMARY as verified -> FAIL",
     _CLEAN_SKILL, _REF_TRAIL_UNCHECKED, False),
    ("delegated 진행 기록 made optional under 요약 출력 -> FAIL",
     _CLEAN_SKILL, _REF_TRAIL_DROPPED_IN_SUMMARY, False),
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

    ok, _ = check_delegated_isolated_exclusive(_PASSING_FIXTURE)
    cases.append(("passing: 위임 vs 격리 excepted in compose line", ok))

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

    ok, _ = check_delegated_isolated_exclusive(_FAILING_FIXTURE)
    cases.append(("failing: 위임 vs 격리 exception absent (expect FAIL)", not ok))

    # --- #663: corrupt the CANONICAL text in reference.md, the guards must still FAIL ---
    # --- #768: the delegated-mode guards run beside them (declaration, compose line, trigger
    # collision, delegated reference clauses), so every mutation is judged by the full set ---
    for desc, skill_text, ref_text, expect_pass in _CANONICAL_CASES:
        modes = _extract_declared_modes(_extract_execution_modes_block(skill_text))
        got = (
            all(cond for cond, _ in reference_checks(skill_text, ref_text))
            and all(cond for cond, _ in delegated_reference_checks(skill_text, ref_text))
            and check_modes_declared(modes)[0]
            and check_no_trigger_collision(modes)[0]
            and check_delegated_isolated_exclusive(skill_text)[0]
        )
        cases.append((f"canonical: {desc}", got == expect_pass))

    # --- #768: the worker's audit trail, judged on the worker file itself ---
    cases.append(("worker: clean contract carries the 진행 기록 items",
                  all(ok for ok, _ in worker_audit_checks(_CLEAN_WORKER))))
    for desc, worker_text in (("진행 기록 section dropped", _WORKER_NO_TRAIL),
                              ("rebuttal count un-capped", _WORKER_TRAIL_UNCAPPED),
                              ("trail made optional under 요약 출력", _WORKER_TRAIL_OPTIONAL_IN_SUMMARY)):
        cases.append((f"worker: {desc} -> FAIL", not all(ok for ok, _ in worker_audit_checks(worker_text))))

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
