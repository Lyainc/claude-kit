# Expert Panel Discussion - Detailed Reference

상세 절차 및 규칙 참조 문서. SKILL.md에서 참조됨.

## Table of Contents

- [Phase 0: 토론 준비 (상세)](#phase-0-토론-준비-상세)
- [Phase 1: 토픽별 라운드 진행 (상세)](#phase-1-토픽별-라운드-진행-상세)
- [STATE Block 복원 상세](#state-block-복원-상세)
- [Phase 2: 기록 관리 (상세)](#phase-2-기록-관리-상세)
- [Phase 3: 모더레이터 권한 (상세)](#phase-3-모더레이터-권한-상세)
- [Output Structure](#output-structure)
- [Troubleshooting](#troubleshooting)
- [Moderator Checklist](#moderator-checklist)
- [Procedure Detail](#procedure-detail)

---

## Phase 0: 토론 준비 (상세)

### 1. 대상 분석

- 제공된 문서/코드/기획안 전체 파악
- 주요 섹션 및 결정 포인트 식별
- 논의 우선순위 설정

### 2. 참여자 구성

- 유저가 지정한 전문가 집단 확인
- 각 전문가의 관점 및 평가 기준 정의
- 실무자 2인(찬성/반대) 역할 확립

**전문가 페르소나 강화 원칙**:

각 전문가는 단순 "관점"이 아니라 **해당 분야 전문가처럼 사고**해야 합니다:

1. **핵심 메커니즘**: 해당 분야의 작동 원리, 기술적 제약사항 기반 발언
   - 예: LLM 전문가 → attention mechanism, 보안 전문가 → 공격 벡터, 법률 전문가 → 법조항

2. **측정 가능한 지표**: 정량적 수치, 성능 기준, 위험도 평가
   - 예: 성능 전문가 → O(n) 복잡도, 보안 전문가 → CVSS 점수, UX 전문가 → 클릭 수

3. **선례/사례**: 과거 성공/실패 사례, 업계 모범 사례, 판례
   - 예: "2023년 X 사고", "Y 프로젝트 실패 사례", "Z 판례"

**역할 프롬프트 차별화 (다양성의 유일한 원천)**:

이 패널의 다양성은 **역할 프롬프트**에서만 나옵니다 — spawn 수나 temperature가 아닙니다 (근거: [다양성 원천](#다양성-원천-역할-프롬프트-vs-spawntemperature)). 따라서 각 역할 프롬프트는 다음 셋이 **서로 명확히 구별**되어야 합니다. 같은 3축을 같은 방식으로 적용하면 역할이 한 목소리로 붕괴(role collapse)합니다.

각 전문가를 구성할 때 셋을 명시적으로 분리해 정의하세요:

1. **고유 입장(stance)**: 이 역할이 기본적으로 무엇을 옹호/경계하는가. 다른 전문가와 출발 입장이 겹치면 안 됩니다.
   - 예: 보안 전문가 → "공격 표면 최소화" 우선 / 성능 전문가 → "지연·처리량" 우선 / UX 전문가 → "사용자 마찰 최소화" 우선

2. **고유 평가 기준(criteria)**: 무엇을 *측정*해 판단하는가. 위 "측정 가능한 지표" 축을 역할마다 **다른 지표**로 고정하세요.
   - 예: 보안 → CVSS·공격 벡터 수 / 성능 → p99 지연·O(n) 복잡도 / UX → task 완료율·클릭 수. 한 전문가가 다른 전문가의 지표로 논증하면 역할이 흐려집니다.

3. **고유 어조(voice)**: 발언의 결. 같은 결론도 다른 역할은 다른 화법으로 말합니다.
   - 예: 보안 → 위협 시나리오 단정조 / 성능 → 수치·벤치마크 인용조 / 법률 → 조항·판례 인용조 / UX → 사용자 행동 관찰조

**충돌 강제**: 두 전문가가 같은 결론에 너무 쉽게 동의하면, 모더레이터(또는 격리 모드의 오케스트레이터)는 각자의 *고유 기준*으로 그 결론을 재검증하도록 요구합니다 — 동의가 기준 일치가 아니라 conformity 수렴일 수 있기 때문입니다 (이것이 [Phase 1 anti-conformity directive](SKILL.md)와 격리 모드 early-stop의 "새 논점 없음" 판정의 근거예요).

**치열한 토론 유도**:
- 구체적 근거 요구: "이 주장의 데이터는?", "어떤 사례가 있나?"
- 반례 제시: "X 상황에서는?", "Y 조건일 때는?"
- 트레이드오프 명시: "이것을 얻으면 무엇을 포기하는가?"

**발언 강도**: 근거의 확실성에 비례 (강한 반대 = 명확한 선례, 약한 동의 = 조건부)

### 다양성 원천: 역할 프롬프트 vs spawn/temperature

이 패널이 mode collapse(모든 페르소나가 한 의견으로 수렴)를 피하는 메커니즘은 **차별화된 역할 프롬프트**입니다 — spawn 수를 늘리거나 sampling temperature를 올리는 게 아닙니다.

**근거 (ChatEval, Du et al. 2023 "multiagent debate")**:
- multi-agent debate에서 출력 다양성과 추론 품질의 향상은 *서로 다른 역할/페르소나 프롬프트*가 서로 다른 추론 경로를 강제하는 데서 나옵니다. 같은 프롬프트를 여러 번 돌리거나 temperature만 올리면 표면 어휘만 흔들릴 뿐, 추론 *구조*는 같은 mode로 수렴합니다 (lexical diversity ≠ reasoning diversity).
- 따라서 다양성에 대한 레버는 **역할 프롬프트의 차별화 강도** 하나입니다. 위 "역할 프롬프트 차별화" 원칙(고유 stance·criteria·voice)이 이 레버를 직접 구현합니다.

**기각된 대안 — full-spawn-default (모든 모드에서 역할마다 subagent를 항상 spawn)**:
- 이 옵션은 **채택하지 않습니다.** 볼트 리서치(D4a, `plan-2026-04-19-ouroboros-execution`) 결과 비용은 선형으로 증가(`exchanges × experts` subagent)하지만, 추론 다양성의 한계 이득은 차별화된 역할 프롬프트가 이미 확보한 수준 위로 거의 늘지 않습니다 (한계효용 체감).
- 따라서 격리(spawn) 모드는 **독립성·실제 턴 교환이 속도/비용보다 중요할 때만** 선택하는 옵트인으로 남습니다 (SKILL.md [Execution Modes] / [Isolated Execution: Rebuttal Exchanges] 참조). 기본은 inline 모드입니다.
- 요약: 다양성을 더 원하면 spawn을 늘리지 말고 **역할 프롬프트를 더 날카롭게 차별화**하세요.

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

### 3. 토픽 분할

- 전체 안건을 독립적 토픽으로 분할
- 토픽 간 의존성 파악
- 논의 순서 결정

**산출물**: 토론 아젠다 (topics, participants, sequence)

---

## Phase 1: 토픽별 라운드 진행 (상세)

### 히스토리 참조 규칙

- 토픽 시작 시: 이전 토픽 결론 요약 확인, 현재 토픽과의 연관성 검토
- 논의 중: 이전 합의와 모순되는 주장 발생 시 해당 결론 인용
- 방향 이탈 시: 모더레이터가 원본 문서 및 이전 결론 참조하여 본질로 복귀

### Step 1.1: 실무자 브리핑

**긍정적 실무자 (실현 가능성 옹호자)**:
- 해당 토픽의 핵심 내용 설명
- 기대 효과 및 장점 제시
- **구현 경험 기반 근거**: "지난 프로젝트에서 이 방식으로 X% 개선했습니다"
- **구체적 수치**: "3주 내 구현 가능", "비용 Y만큼 절감"
- **실무적 실현 가능성**: "현재 팀 역량으로 충분히 가능합니다"

**부정적 실무자 (리스크 식별자)**:
- **과거 실패 사례 인용**: "2023년 A 프로젝트가 이 방식으로 실패했습니다"
- **구체적 리스크 수치**: "장애 발생 확률 N%", "기술 부채 M 시간 증가"
- **잠재적 문제점 시나리오**: "사용자가 X 행동을 하면 Y 오류 발생"
- **대안적 접근법 제안**: 단순 반대가 아닌 "대신 이렇게 하면..."

**중요**: 실무자는 추상적 찬반이 아니라 **현장 경험과 데이터**로 논쟁합니다.

### Step 1.2: 전문가 질의응답 (Q&A / Rebuttal)

```
[전문가 A, B, C, ...]
- 각 전문가 관점에서 질문
- 실무자들의 응답
- 추가 clarification
```

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
assembling per-expert prompt packets, relaying between exchanges, and judging the stop condition —
is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator
subagent. The Moderator subagent stays visibility-limited (position summaries only) and is spawned
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
   directive** (defined at the top of SKILL.md § Phase 1: Topic Rounds). Each expert then (a)
   holds and defends, (b) rebuts a specific point with new evidence, or (c) revises.

**Exchange records (restore source)**: the moment an expert's statement is collected, the
orchestrator Writes it — before touching STATE — to
`{discussion-dir}/_exchanges/t{n}-e{i}-{expert-id}.md` (`{discussion-dir}` =
`docs/discussions/{YYYYMMDD}_{name}/`; the topic briefing goes to `t{n}-briefing.md`), then adds
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
fires — plus 1 Moderator subagent for Synthesis.
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

### Step 1.3: 변증법적 논의

```
정(Thesis): 긍정적 실무자 주장
반(Antithesis): 부정적 실무자 + 전문가 반론
합(Synthesis): 절충안 도출 시도
```

### Step 1.4: 합의 또는 보류

**합의 도달 시**:

- 모더레이터가 합의 내용 정리
- 전원 동의 확인
- 토픽 종료 선언

**합의 불가 시** (판정 규칙은 [SKILL.md § Topic Conclusion](SKILL.md#topic-conclusion)):

- 가중 투표로 승자가 있으면 `tie-broken` — 차이가 1점이면 SUMMARY.md에 조건부로 표시
- 동점(차이 0점) → `held:tie`, 근거 부족 → `held:evidence`, 유효 전문가 3명 미만 → `held:quorum` (투표 없음). 보류는 승자를 만들지 않고 UNRESOLVED.md에 사유와 함께 남김
- 팩트체크·의사결정이 필요하면 유저 개입 요청

**실무자 절충**:

- 긍정적 실무자: 반대 논거가 우세하다고 판단 시 절충안 제시
- 부정적 실무자: 찬성 논거가 우세하다고 판단 시 절충안 제시
- 양측 모두 합리적 선에서 양보하되, 구조적 한계면 논의 종료

**논의 종료 조건**:

- 합의 도달 (반대 1명 이하)
- 가중 투표 승자 확정 (`tie-broken`)
- 보류 (`held:tie` / `held:evidence` / `held:quorum`) → 미해결 이슈로 이관

---

## STATE Block 복원 상세

SKILL.md의 STATE Block Contract에서 참조됨 — 필드별 write/read 지점, 격리 모드의 다중 라운드 추적, compaction 복원 기본값을 정의한다. core rules는 [`../../reference/state-contract.md`](../../reference/state-contract.md) 참조. 블록 템플릿(아래)은 SKILL.md에서 이 섹션으로 옮겨졌다(#750, Codex 8,000-byte invoked-skill 한도). **이 섹션은 binding이다**: SKILL.md는 STATE를 쓰거나 복원하기 전에 이 섹션을 읽도록 지시하며, 템플릿·필드 의미·복원 기본값은 SKILL.md에 다시 적지 않는다. 압축된 격리 모드 세션을 재개하기 전에도 로드한다.

Template and load-bearing invariants, moved verbatim from the pre-#750 SKILL.md (the invariants are restated in compact form in SKILL.md § Phase 1 and in full under "Compaction restore fallback" below):

**STATE Block Contract**:

> **Core Rules**: See [../../reference/state-contract.md](../../reference/state-contract.md)

Never store thesis/antithesis/synthesis prose in the block — only the closed-enum status below;
dialectic prose lives in Phase 2 files (`docs/discussions/.../transcripts/`). This keeps the block bounded.

```
<!-- STATE:CHECKPOINT -->
Topic: {idx}/{total} | Phase: {0|1|2}
Mode: [isolated:{on|off}] [summary-only:{on|off}]
Backlog: {scanned|partial|skipped}
Personas: [{persona-id} ...] adhoc:{n}
Independent: {k}/{N}
Rebuttal: [t{n}:e{i}:{k}/{N}]
Collected: [t{n}:e{i}:{expert-id},...]
Records: {discussion-dir}/_exchanges/ | —
Topic-status: [t{n}:{pending|thesis-reached|antithesis-reached|synthesis-reached|consensus-reached|tie-broken|held:{tie|evidence|quorum}}] ...
Citation: [t{n}:{grounded|unverified|skipped}] ...
Votes: [t{n}:{expert}:{option}:{High|Medium|Low}] ...
Tie-break: [t{n}:margin:{n|—}] ...
<!-- /STATE -->
```

**Field semantics, exchange records, and compaction-restore defaults**: see [reference.md → STATE Block 복원 상세](reference.md) — load it before resuming a compacted isolated-mode session. Load-bearing invariants (kept here so restore is safe even before that load): in isolated mode the exchange records under `Records` are the source of truth for which experts finished an exchange — each record is written *before* `Collected`/`Rebuttal` are updated, so a record wins over a counter on any divergence, and an expert with no record is never counted as done by inference (re-collect it instead). `Rebuttal` locates the exchange and wins over `Independent`. On compaction, restore from the most recent STATE block, defaulting missing fields to the low-loss side — Mode flags → `off` (full output), Backlog → `skipped`, Citation → `skipped`, Topic-status → `pending`, Votes → no vote. A missing `Personas` field is recovered by re-running the Selection Rule on the same topic text — it is deterministic, so recomputation returns the identical set (ad-hoc personas are the exception: they are session-local, so recover those from the exchange records or transcript instead).

**Field write/read points**:
- `Backlog` (#524) — written once at Phase 0 step 2, before the panel is composed: `scanned` if `backlog-prefilter.py` returned a clean digest, `partial` if it prefixed the digest with `[backlog-scan PARTIAL]` (#561 — one side's `gh` fetch failed while the other rendered normally), `skipped` if it printed `[backlog-scan SKIPPED]` instead. Read at Phase 2 to decide the carried-over line (SKILL.md → Phase 2: Recording, the backlog-result line) — a session-level field, not per-topic (the scan runs once on the original topic text, before topic-splitting). Zero LLM cost: `backlog-prefilter.py` is a deterministic shell scan of the open+closed issue corpus, the same script `build-spec` Phase 0 uses (#489) — the corpus itself never enters context, only the budgeted digest does. The digest is fed to experts as grounding at the same status as the Citation Contract's vault excerpts (SKILL.md → Citation Contract): material an expert may cite or override, never a verdict the panel is bound to, since the point is to make an existing decision *visible* to the debate, not to pre-decide it.
- `Mode` — set at Phase 0 (mode detection); read at Phase 2 item 1 (transcript skip in summary-only mode).
- `Personas` — written at Phase 0 step 3 (the [`../../reference/personas.md`](../../reference/personas.md) Selection Rule) and re-written whenever the panel changes (a mid-discussion addition, a per-topic re-run). Pool IDs in ranked order plus `adhoc:{n}`; `adhoc:{n}` is required even at `0`, since a silent ad-hoc fallback is the failure this field exists to expose. On restore, a missing value is recomputed by re-running the rule on the same topic text — it is deterministic, so it returns the identical set; ad-hoc personas are session-local and recover from the transcript instead.
- `Independent` — updated during Phase 1 Independent Statements; `k==N` means collection complete (single format; no separate "complete" token). Inline mode only for restore; in isolated mode it is a mirror of `e1`.
- `Rebuttal` (isolated mode only) — topic `n`, exchange index `e{i}` (`e1` = independent, `e2`/`e3` = up to 2 rebuttal exchanges), and `{k}/{N}` experts collected in the current exchange — updated after each expert is collected, so `k` may be partial mid-exchange (e.g. `e1:1/3` after the first of three). Bounded counters only — never statement prose. Empty/omitted in inline mode. In isolated mode the `Rebuttal` cursor is the authoritative loop-position source — recorded in the STATE block in **all** modes (including isolated + summary-only, since it is not a transcript); `Independent` is the inline-mode tracker and only a redundant mirror at `e1`. On any divergence (e.g. a partial write interrupted by compaction), `Rebuttal` wins (it also distinguishes `e2`/`e3`).
- `Collected` (isolated mode only) — per topic and exchange, the ids of the experts whose exchange record has been Written. Updated right after each record Write, never before. It is a set, not a count, so a restore knows *which* experts to re-collect.
- `Records` (isolated mode only) — the `_exchanges/` directory holding the per-expert records; `—` in inline mode. Present in summary-only mode too.
- `Citation` — written per topic after the vault-searcher call attempt (or inline fallback). Three values: `grounded` = at least one expert cited a source for a numeric/factual claim; `unverified` = grounding *was available* (vault-searcher reachable, or an in-scope doc) and consulted, but no source was found / experts fell back to inline judgment despite availability; `skipped` = vault-searcher was *unavailable* (not installed / Agent call failed) so grounding was never attempted — inline fallback, behavior identical to pre-grounding. Read by the escalation signal: a topic with consensus AND `Citation: unverified` is escalated/deepened rather than marked easy; `grounded` and `skipped` never escalate (see SKILL.md → Citation Contract).
- `Votes` — per topic; populated only by the weighted vote of SKILL.md § Topic Conclusion, after the rebuttal loop stops without consensus. Empty for consensus topics and for `held:quorum` (no vote runs).
- `Tie-break` — per topic: the vote margin (top option minus runner-up); `—` when no vote ran.
- `Topic-status` — closed enum, exactly these 7 values; no free-text: `pending`, `thesis-reached`, `antithesis-reached`, `synthesis-reached`, `consensus-reached`, `tie-broken`, `held:{tie|evidence|quorum}`. `tie-broken` requires a single winning option (margin ≥ 1; a margin of 1 is marked Conditional in SUMMARY.md). A vote with margin 0 is `held:tie`, never `tie-broken`. Every `held` topic carries its reason and appears in UNRESOLVED.md.

**Loop position (isolated mode)**: each topic has one loop — the exchange loop — located by `Rebuttal: [t{n}:e{i}:{k}/{N}]` together with `Collected`. There is no topic-round counter: E1 runs once per topic and is not re-entered.

**Compaction restore fallback**: restore from the most recent STATE block. Defaults for missing fields —
Topic-status → `pending`; Votes → no vote; Independent → `0` (inline mode: re-collect, preserves anti-anchoring);
Mode flags → both `off` (full output — over-producing transcripts is safer than losing user content);
Citation → `skipped` (a missing citation state most often means grounding was never attempted this session — e.g. no vault-bridge — so defaulting to `skipped` avoids spuriously escalating every restored topic; if vault-searcher IS available this session, re-attempt grounding on the resumed topic instead of trusting the default);
Backlog → `skipped` (mirrors the `Citation` default — a missing value must not read as a clean scan; the script is zero-LLM-cost, so re-run it on the resumed topic text instead of trusting the default when a corpus is reachable this session).
In isolated mode the in-progress exchange is restored from the exchange records — not from the conversation, and not from transcripts (those are written only in Phase 2, and skipped entirely in summary-only mode). For topic `t{n}`:

1. List `Records` for `t{n}-*`. An expert with a record for an exchange is done for it — take its statement from the record, never re-collect it and never count it twice. An expert without a record is not done, even if `Collected` or `k` says it is.
2. Find the earliest exchange of the topic with a missing record. Re-spawn only its missing experts, with the packet that exchange used: topic + `t{n}-briefing.md` for `e1`; for `e2`/`e3`, the records of the exchange before it. Other experts' records from the same exchange never go into a packet.
3. Records of any later exchange were built from the lost statement, so discard them and re-collect that later exchange after step 2. If `t{n}-briefing.md` itself is missing, or the records directory is gone, restart the topic at `e1` with a fresh briefing.
4. If the retries leave fewer than 3 valid experts, the topic is `held:quorum`.

Never mark an expert, an exchange, or a topic complete from a counter alone.

---

## Phase 2: 기록 관리 (상세)

### 저장 규칙

**저장 위치**: 프로젝트 루트의 `docs/discussions/` 폴더 (로컬 워킹 드래프트 — canonical 기록 규칙은 [SKILL.md § Phase 2: Recording](SKILL.md#phase-2-recording) 참고).

```
{project-root}/
└── docs/
    └── discussions/
        └── {YYYYMMDD}_{discussion-name}/
            ├── SUMMARY.md              # 최종 요약본
            ├── UNRESOLVED.md           # 미해결 이슈
            └── transcripts/
                ├── 01_{topic-name}.md  # 토픽별 속기록
                ├── 02_{topic-name}.md
                └── ...
```

**파일명 규칙**:

- 폴더명: `{YYYYMMDD}_{discussion-name}` (예: `20241224_api-design-review`)
- 속기록: `{순번}_{topic-name}.md` (예: `01_authentication.md`)
- 순번은 01부터 시작, 논의 순서대로 부여

### 속기록 형식

```markdown
## [Topic Name] Transcript

### Briefing: 브리핑

**[긍정적 실무자]**: ...
**[부정적 실무자]**: ...

### Q&A: 질의응답

**[전문가 A]**: 질문...
**[긍정적 실무자]**: 응답...

### Dialectic: 논의

**[부정적 실무자]**: 반론...
**[전문가 B]**: 추가 의견...

### 결론

**[모더레이터]**: 합의 내용... / 보류 사유...
```

### 최종본 형식

```markdown
## Discussion Summary

### 합의된 사항

| 토픽 | 결론 | 근거 | 출처 / 인용 |
|------|------|------|------------|
| ... | ... | ... | ... |

### 미해결 이슈

| 토픽 | 사유 | 필요 조치 |
|------|------|----------|
| ... | ... | ... |

### 개선 권고사항

- ...
```

---

## Phase 3: 모더레이터 권한 (상세)

### 토론 중단 조건

1. **팩트체크 필요**: 객관적 사실 확인 없이 진행 불가
2. **의견 교착**: 양측 주장이 평행선, 외부 판단 필요
3. **범위 이탈**: 논의가 본질에서 벗어남

### 중단 시 행동

```
[모더레이터]
현재 토론을 잠시 중단합니다.

**중단 사유**: [팩트체크 필요 / 의사결정 필요 / 범위 조정 필요]
**필요 정보**: [구체적으로 유저에게 요청할 내용]
**재개 조건**: [정보 제공 후 진행 방향]
```

### 미해결 이슈 기록 형식

```markdown
## Unresolved Issues Log

### Issue #1: [제목]

- **토픽**: ...
- **쟁점**: ...
- **양측 입장**: ...
- **보류 사유**: [구조적 한계 / 정보 부족 / 의견 대립]
- **권고 조치**: ...
```

---

## Output Structure

### 토론 진행 중 출력 형식

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC [N]: [토픽명]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[역할]: 발언 내용...

---
[다음 발언자]
---

CONCLUSION: [합의 내용 또는 보류 상태]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Troubleshooting

| 문제 | 해결 |
|------|------|
| 토론이 특정 토픽에서 무한 루프 | 모더레이터가 논의 발전 없음 판단 시 강제 종료, 미해결 이슈로 기록 |
| 실무자 간 감정적 대립 | 모더레이터가 논점 재정리, 객관적 사실 기반으로 리프레이밍 |
| 전문가 의견이 너무 상충 | 각 입장의 전제 조건 명시, 조건부 합의 도출 시도 |

---

## Moderator Checklist

토론 종료 전 확인:

- [ ] 모든 토픽 논의 완료 또는 명시적 보류
- [ ] 합의 사항 전원 동의 확인
- [ ] 미해결 이슈 목록화 완료
- [ ] 속기록 누락 없음
- [ ] 다음 단계 액션 아이템 정리

---

## Output Format details

Split out of `SKILL.md` (#447) so the skill body fits the 5,000-token window
auto-compaction re-attaches. Read this section when formatting the panel output.

### Discussion Style

Use clean, professional formatting without emoji:

| Element | Format | Example |
|---------|--------|---------|
| Topic header | `### TOPIC N: {title}` | `### TOPIC 1: 인증 방식` |
| Speaker | `**[Role]**:` | `**[Optimistic Practitioner]**:` |
| Conclusion | `**결론**:` or `**결론**: 보류` | `**결론**: JWT + Refresh Token 방식 합의` |
| Footer | `───` + metadata | `*3개 토픽 논의 완료 · 2개 합의, 1개 보류*` |

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Generated text content itself
- Results that users will directly use
- Examples: brand names, document body, discussion conclusions

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

### Role Labels (English)

| Korean | English |
|--------|---------|
| 긍정적 실무자 | Optimistic Practitioner |
| 부정적 실무자 | Critical Practitioner |
| 모더레이터 | Moderator |
| 보안전문가 | Security Expert |
| 성능전문가 | Performance Expert |
| UX전문가 | UX Expert |
| (기타 도메인) | {Domain} Expert |

Pool-selected experts use the `Label` column of [../../reference/personas.md](../../reference/personas.md) verbatim; ad-hoc experts append ` (ad-hoc)`.

## References

- **Shared persona pool**: See [../../reference/personas.md](../../reference/personas.md)
- **Conversation examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder

## Quick Start

```
User: "이 API 설계 문서를 보안/성능/UX 전문가 관점에서 검토해줘"

→ Phase 0: 토픽 분할 (인증, 페이지네이션, 에러처리)
→ Phase 1: 각 토픽별 찬반 토론 진행
→ Phase 2: 합의사항 및 미해결 이슈 기록
→ Output: SUMMARY.md + transcripts/
```

---

## Procedure Detail

Step detail moved out of `SKILL.md` to fit Codex's 8,000-byte invoked-skill limit (#750). The text below is the pre-move SKILL.md prose, verbatim except that headings are demoted one level and in-page links now point at `SKILL.md`. Not repeated here because they are already canonical elsewhere: § Isolated execution: exchange-loop contract and § Expert Selection Guide (above), and the STATE template (§ STATE Block 복원 상세). § Topic Conclusion stays in `SKILL.md` (compact form, same rules). Read the matching subsection when its step is reached.

### Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: Korean by default (panel discussions use Korean)
  - If user writes in English → English output
  - Role labels: use English labels (see Role Labels table)

### Overview

Facilitate expert panel discussions where diverse specialists reach consensus through dialectical debate.

### Execution Modes

Express mode preferences in natural language — no flags needed:
- **격리 실행** ("엄격하게", "격리해서"): Each expert and Moderator spawned as separate Agent subagents (stronger isolation). Enables real multi-turn rebuttal — experts are re-spawned for each rebuttal exchange with prior-exchange statements injected, instead of one simulated pass (see [Isolated Execution: Rebuttal Exchanges](SKILL.md#isolated-execution-rebuttal-exchanges))
- **요약 출력** ("요약만", "transcript 없이"): Skip transcript generation; produce SUMMARY.md + UNRESOLVED.md only

All combinations compose silently — including any combination with citation grounding (see [Citation Contract](SKILL.md#citation-contract)) and the Phase 2 inline-summary path (see [Phase 2: Recording](SKILL.md#phase-2-recording)).

### Participants

#### Fixed (Always Present)

| Role | Stance | Distinct evaluation criteria | Voice |
|------|--------|------------------------------|-------|
| **Moderator** | Neutral facilitation (no position) | Open/close authority, fact-check requests, unresolved-issue tracking | Procedural, summarizing |
| **Optimistic Practitioner** | Advocates benefits + feasibility | Implementation experience, delivery numbers ("3주 내 가능", "X% 개선") | Forward-leaning, solution-first |
| **Critical Practitioner** | Identifies risk + limitations, proposes alternatives | Failure precedents, risk probabilities, tech-debt cost | Skeptical, evidence-demanding |

#### Variable (Selected from the shared pool)

| Role | Description |
|------|-------------|
| **Expert Panel** | 3–5 domain experts selected from [../../reference/personas.md](../../reference/personas.md) by that file's deterministic tag-matching Selection Rule — same topic text, same panel, every run |

Run the Selection Rule per topic in Phase 0 on the **user's original topic text** (title + statement
as submitted — the same input `adversarial-review` uses, which is what makes the two skills land on
the same entry) and record the resulting IDs in the STATE block
`Personas` field. The pool is a **default, not a closed list**: a topic matching no entry proceeds
with ad-hoc personas labeled `{Domain} Expert (ad-hoc)`, counted in `adhoc:{n}` so the fallback is
visible rather than silent. A user who names the experts explicitly overrides the rule — record
that as `adhoc:{n}` for any named expert absent from the pool.

**Important — role-prompt differentiation is the diversity source** (not extra spawns/temperature): every role needs a **distinct stance**, **distinct evaluation criteria**, and a **distinct voice** — pre-differentiated for variable roles by the shared pool ([personas.md](../../reference/personas.md)), so an ad-hoc persona is the only place this has to be authored per session. Easy agreement between roles may be conformity, not aligned evidence — re-validate against each role's own criteria (Anti-conformity directive, [Phase 1](SKILL.md#phase-1-topic-rounds)). Full rationale + the rejected full-spawn-default alternative: [reference.md](reference.md).

### Citation Contract

When an expert states a **numeric or factual claim** (statistics, performance figures, failure rates, legal citations, precedents), it must cite exactly one grounding source:

1. **Preferred**: call `vault-searcher` (Agent tool, Mode 3 — Keyword Search) once per topic to surface relevant past decisions or notes. Cache returned excerpts for reuse within the same topic — do NOT re-query per round. Search target: user's vault `notes/`, preferring `type: decision`.
2. **Fallback**: cite a named document or file already in scope via Read/Grep (e.g., a design doc the user provided for this session).
3. **Inline fallback**: if vault-searcher is unavailable / returns 0 relevant results / the Agent call fails or returns no response, fall back to the existing inline behavior — the expert states the claim as a domain judgment. Do NOT announce the fallback to the user; session behavior must look identical. A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further.

**Token budget**: vault-searcher call + section-only excerpts + max 3 results keeps this step within **~+1500 tokens** of per-topic overhead (mirrors the adversarial-review grounding budget precedent). Never re-query per rebuttal exchange, never request full notes.

**Citation-coverage escalation signal**: a consensus topic recorded `Citation: unverified` (grounding attempted, none found) escalates/deepens instead of being marked easy — catches false-consensus. Fires only on `unverified`, never on `skipped` (an unavailable vault-searcher must not make standalone sessions silently longer). Field semantics: [reference.md → STATE Block 복원 상세](reference.md).

**Note on full-spawn-default**: citation grounding is a verification purpose — sourcing evidence to ground claims. It does NOT increase expert diversity and does NOT conflict with the spawn≠diversity / full-spawn-default ADR (see [reference.md → 다양성 원천](reference.md)). The diversity lever remains role-prompt differentiation only; citation is orthogonal.

| Item | Rule |
|------|------|
| Principle | Unanimity (allows up to 1 minority dissent) |
| Moderator | No voting rights, facilitation authority only |
| Experts | Minimum 3 valid experts; below 3 the topic is held (see [Topic Conclusion](SKILL.md#topic-conclusion)) |
| Objection | 2+ experts objecting means no consensus — the topic goes to the weighted vote, never to a repeat cycle |

### Core Workflow

#### Phase 0: Preparation
1. Analyze the review target → split into topics
2. **Backlog prefilter scan (#524)**: use Bash to run the prefilter once, before any expert speaks, on the user's original topic text (before splitting):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{review target text}"
   ```
   `[backlog-scan SKIPPED]` output → record `Backlog: skipped`, carry that line verbatim into Phase 2. A `[backlog-scan PARTIAL]` prefix (#561 — one side's `gh` fetch failed while the other rendered normally) → record `Backlog: partial`, carry that line verbatim into Phase 2 too, and still give the rendered digest below it to every expert — PARTIAL means one side is unconfirmed, not that nothing rendered. Otherwise record `Backlog: scanned` and give the digest to every expert as grounding, same status as [Citation Contract](SKILL.md#citation-contract) sources — never a verdict the panel is bound to. Rationale + zero-cost note: [reference.md](reference.md).
3. Run the [personas.md](../../reference/personas.md) Selection Rule on each topic's text → panel composition (confirm with the user only when they asked to pick the experts themselves)
4. Generate discussion agenda

#### Phase 1: Topic Rounds

**Anti-conformity directive** (applied to every expert turn): "You are not required to reach the same conclusions as other panel members. Maintain your position if your domain evidence supports it."

For each topic (one cycle per topic — see Cycle Limits):
1. **Briefing**: Practitioners present pro/con perspectives
2. **Independent Statements**: Each expert generates a position statement independently — labeled **[{Expert} — independent]** — before seeing others' views. All independent statements are collected before any expert sees others' positions (prevents anchoring / echo chamber). In default (inline) mode this is best-effort via prompt contract; isolated execution mode enforces it mechanically via subagent context boundaries.
3. **Q&A / Rebuttal**: Experts question and rebut each other. Inline mode renders this as one simulated pass; isolated mode runs it as a real exchange loop — 1 independent exchange + up to 2 rebuttal exchanges (see [Isolated Execution: Rebuttal Exchanges](SKILL.md#isolated-execution-rebuttal-exchanges))
4. **Dialectic**: Thesis → Antithesis → Synthesis
5. **Conclusion**: consensus, vote result, or hold (see [Topic Conclusion](SKILL.md#topic-conclusion))

**Cycle Limits**:
- Each topic runs one cycle: independent statements once (E1), then at most 2 rebuttal exchanges (E2, E3). There is no outer topic-round repeat, and E1 is never re-collected for the same topic because a new round started — the only re-collection is a restore that lost E1 records ([reference.md → STATE Block 복원 상세](reference.md)).
- Inline mode simulates the same shape in one response: one independent pass, then at most 2 rebuttal passes.
- Early stop: the rebuttal loop may stop after any rebuttal exchange that adds no new argument, before the 2-rebuttal cap. Early stop ends the debate, not the decision — the topic still goes to [Topic Conclusion](SKILL.md#topic-conclusion), and stopping is never itself a consensus verdict.

#### Phase 2: Recording

After all topics are discussed, produce output according to session scope:

**Lightweight / single-topic sessions** (default path when none of the triggers below apply):
- Produce an **inline SUMMARY** in the current conversation — consensus items, recommendations, action items, unresolved issues. No files written.
- This is sufficient for quick, single-topic reviews and avoids unnecessary file I/O for routine use.

**Backlog scan carry-over (#524)**: state the Phase 0 backlog result in the output — the
`[backlog-scan SKIPPED]` line verbatim if skipped, else one line naming conflicts or a no-conflict
statement. An empty field is not a pass (mirrors `build-spec`'s `context.backlog_scan`, #489).

**Full 3-file generation** is required when ANY of the following apply:
- Session covers **multiple topics** (2+)
- User explicitly requests file output ("저장해줘", "파일로", "transcript 남겨줘", etc.)
- Unresolved issues are substantial enough to warrant a persistent UNRESOLVED.md record
- Session used isolated execution mode (real turn exchanges justify persistent transcripts)

When full generation is required, Write each of these three files:

1. **Raw transcripts**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{순번}_{topic}.md`
   - All statements recorded chronologically (template: `templates/TRANSCRIPT_TEMPLATE.md`)
   - **Skipped in summary output mode**

2. **Summary**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - Consensus items, recommendations, action items (template: `templates/SUMMARY_TEMPLATE.md`)

3. **Unresolved issues**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - Detailed record of held topics (template: `templates/UNRESOLVED_TEMPLATE.md`)

**`docs/discussions/` is a local working-draft location, not a canonical record** — whether it is git-tracked is project-specific (e.g. claude-kit gitignores it as of 2026-06-13, since GitHub issues are its canonical decision record). If the discussion is tied to a GitHub issue, propose also posting the SUMMARY as a comment on that issue with a `#N` backlink — with user confirmation before posting, since a comment on a shared issue is visible to others. That comment, once confirmed, is the durable, searchable record. The local files above remain useful as session-local working material either way.

Proceed to Phase 2 immediately after all topics are discussed. In the inline path, the inline SUMMARY replaces file generation — discussion does not end without some form of output.

**Note on summary output mode**: Item 1 (raw transcripts) is skipped. SUMMARY.md (item 2) and UNRESOLVED.md (item 3) are always generated regardless of mode when full generation is triggered.

#### Moderator Visibility Contract

- **Default**: Moderator receives expert position summaries only (full Q&A transcript blocked during synthesis)
- **Isolated execution mode**: Moderator spawned as separate Agent subagent; pass the final exchange's expert position summaries only as the subagent prompt (experts also spawned as subagents — see Execution Modes)
- **Rebuttal relay (isolated)**: between exchanges the **orchestrator** (not the Moderator subagent) assembles and forwards per-expert summary packets; the Moderator subagent is spawned only for Synthesis and still sees position summaries only (see [Isolated Execution: Rebuttal Exchanges](SKILL.md#isolated-execution-rebuttal-exchanges))

This prevents the Moderator from being anchored by the Q&A thread and ensures independent synthesis.

#### Phase 3: Moderator Authority
- Request information from user when fact-checking is needed
- Force-close discussion when no further progress is possible
- Record unresolved issues separately

### Output Format
#### Output Format details

Discussion style, the output-integrity principle (no invented citations, no emoji), the
Korean→English role-label table, and the Quick Start example live in
[reference.md](reference.md) — read it when writing the output files. Conversation examples:
[examples.md](examples.md); output templates: `templates/`.
