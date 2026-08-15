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
| Perspective balance | Carried by the tags themselves — a topic with strategy vocabulary matches `P9`. Never top up the panel because the selection *looks* implementation-heavy: "is this implementation-focused" is an LLM judgment, and one applied inconsistently makes two runs of one topic emit different `adhoc:{n}` (#423) |
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

**합의 불가 시**:

- 구조적 한계 인정 → 미해결 이슈로 기록
- 또는 유저 개입 요청 (팩트체크/의사결정 필요)

**실무자 절충**:

- 긍정적 실무자: 반대 논거가 우세하다고 판단 시 절충안 제시
- 부정적 실무자: 찬성 논거가 우세하다고 판단 시 절충안 제시
- 양측 모두 합리적 선에서 양보하되, 구조적 한계면 논의 종료

**논의 종료 조건**:

- 합의 도달 (반대 1명 이하)
- 모더레이터가 논의에 발전이 없다고 판단
- 구조적 한계 인정 → 미해결 이슈로 이관

---

## STATE Block 복원 상세

SKILL.md의 STATE Block Contract에서 참조됨 — 필드별 write/read 지점, 격리 모드의 다중 라운드 추적, compaction 복원 기본값을 정의한다. 블록 템플릿과 core rules는 SKILL.md / [`../../reference/state-contract.md`](../../reference/state-contract.md) 참조. 압축된 격리 모드 세션을 재개하기 전에 이 섹션을 로드한다.

**Field write/read points**:
- `Backlog` (#524) — written once at Phase 0 step 2, before the panel is composed: `scanned` if `backlog-prefilter.py` returned a clean digest, `partial` if it prefixed the digest with `[backlog-scan PARTIAL]` (#561 — one side's `gh` fetch failed while the other rendered normally), `skipped` if it printed `[backlog-scan SKIPPED]` instead. Read at Phase 2 to decide the carried-over line (SKILL.md → Phase 2: Recording, "Backlog scan carry-over") — a session-level field, not per-topic (the scan runs once on the original topic text, before topic-splitting). Zero LLM cost: `backlog-prefilter.py` is a deterministic shell scan of the open+closed issue corpus, the same script `build-spec` Phase 0 uses (#489) — the corpus itself never enters context, only the budgeted digest does. The digest is fed to experts as grounding at the same status as the Citation Contract's vault excerpts (SKILL.md → Citation Contract): material an expert may cite or override, never a verdict the panel is bound to, since the point is to make an existing decision *visible* to the debate, not to pre-decide it.
- `Mode` — set at Phase 0 (mode detection); read at Phase 2 item 1 (transcript skip in summary-only mode).
- `Personas` — written at Phase 0 step 3 (the [`../../reference/personas.md`](../../reference/personas.md) Selection Rule) and re-written whenever the panel changes (a mid-discussion addition, a per-topic re-run). Pool IDs in ranked order plus `adhoc:{n}`; `adhoc:{n}` is required even at `0`, since a silent ad-hoc fallback is the failure this field exists to expose. On restore, a missing value is recomputed by re-running the rule on the same topic text — it is deterministic, so it returns the identical set; ad-hoc personas are session-local and recover from the transcript instead.
- `Independent` — updated during Phase 1 Independent Statements; `k==N` means collection complete (single format; no separate "complete" token).
- `Rebuttal` (isolated mode only) — topic `n`, exchange index `e{i}` (`e1` = independent, `e2`/`e3` = up to 2 rebuttal exchanges), and `{k}/{N}` experts collected in the current exchange — updated after each expert is collected, so `k` may be partial mid-exchange (e.g. `e1:1/3` after the first of three). Bounded counters only — never statement prose. Empty/omitted in inline mode. In isolated mode the `Rebuttal` cursor is the authoritative loop-position source — recorded in the STATE block in **all** modes (including isolated + summary-only, since it is not a transcript); `Independent` is the inline-mode tracker and only a redundant mirror at `e1`. On any divergence (e.g. a partial write interrupted by compaction), `Rebuttal` wins (it also distinguishes `e2`/`e3`).
- `Citation` — written per topic after the vault-searcher call attempt (or inline fallback). Three values: `grounded` = at least one expert cited a source for a numeric/factual claim; `unverified` = grounding *was available* (vault-searcher reachable, or an in-scope doc) and consulted, but no source was found / experts fell back to inline judgment despite availability; `skipped` = vault-searcher was *unavailable* (not installed / Agent call failed) so grounding was never attempted — inline fallback, behavior identical to pre-grounding. Read by the escalation signal: a topic with consensus AND `Citation: unverified` is escalated/deepened rather than marked easy; `grounded` and `skipped` never escalate (see SKILL.md → Citation Contract).
- `Votes` — populated only by the Tie-Breaking Mechanism (after round 3); empty before tie-break.
- `Topic-status` — closed enum, exactly these 6 values; no free-text. `tie-broken` = resolved via the Tie-Breaking Mechanism (weighted vote always yields a winner; a margin < 2 is recorded as "Conditional" in SUMMARY.md but the status stays `tie-broken`). There is no separate `deadlock` value — the vote is total, so a topic never ends unresolved.

**Multi-round support (isolated mode) — verified**: the block tracks two nested loops, and isolated-mode multi-round debate is fully supported by them:
- *Outer loop* = topic rounds, located by `Round: {r}/3` (the 3-round ceiling — see SKILL.md → Round Limits).
- *Inner loop* = the isolated-mode exchange loop inside one round's Q&A/Rebuttal step, located by `Rebuttal: [t{n}:e{i}:{k}/{N}]`.

The `Rebuttal` cursor intentionally carries only topic index `t{n}` + exchange index `e{i}` — **not** the round index `r`. It does not need one: the exchange loop re-enters fresh at `e1` every new topic round (independent statements are re-collected per round, preserving anti-anchoring), so the pair `(Round={r}, Rebuttal=[t{n}:e{i}:…])` — both fields in the same STATE block — uniquely locates the loop position across rounds. On compaction restore, read `Round` for the topic-round position and `Rebuttal` for the in-progress exchange; together they resume multi-round isolated debate without ambiguity. (Single-round and inline modes use the same fields; inline simply leaves `Rebuttal` empty.)

**Compaction restore fallback**: restore from the most recent STATE block. Defaults for missing fields —
Topic-status → `pending`; Votes → treat as no-vote / no-consensus; Independent → `0` (re-collect, preserves anti-anchoring);
Mode flags → both `off` (full output — over-producing transcripts is safer than losing user content);
Citation → `skipped` (a missing citation state most often means grounding was never attempted this session — e.g. no vault-bridge — so defaulting to `skipped` avoids spuriously escalating every restored topic; if vault-searcher IS available this session, re-attempt grounding on the resumed topic instead of trusting the default);
Backlog → `skipped` (mirrors the `Citation` default — a missing value must not read as a clean scan; the script is zero-LLM-cost, so re-run it on the resumed topic text instead of trusting the default when a corpus is reachable this session).
In isolated mode the in-progress exchange is restored from the `Rebuttal` cursor — NOT from transcripts (those are written only in Phase 2, and skipped entirely in summary-only mode, so they do not exist mid-loop). When `Rebuttal` shows `e{i}` with `i>=2`, independent collection is already complete: do NOT apply the `Independent → 0` re-collect default above (that default applies only while the loop is still at `e1`) — re-running E1 would discard completed rebuttal progress. Conversely, when `Rebuttal` shows `e1`, independent collection is still in progress, so the `Independent → 0` re-collect default applies as usual — any partial e1 statements are re-collected from scratch, preserving anti-anchoring.

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
