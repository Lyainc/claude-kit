# Model Routing Redesign Expert Panel - Summary

**Date**: 2026-05-17
**Context**: `plan-2026-05-10-skill-model-routing.md` 백지화 후 재설계안의 전문가 검토. claude-kit 플러그인의 opus→sonnet/haiku 토큰 효율화.
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

## Background

원안(`plan-2026-05-10-skill-model-routing.md`)은 SKILL.md frontmatter에 `context: fork + agent:`를 추가해 skill을 싼 모델 에이전트로 위임하는 방식이었다. 세션 검토에서 6개 의존성 이슈가 발견됐고, 플러그인 업데이트(vault-searcher read-only 전환, telemetry 인프라 신설)로 원안 일부가 무효화됐다. 또한 2026-04-16 `cost-optimization-panel`이 이미 동일 주제를 다뤘음이 확인됐다.

재설계안의 5개 골자를 패널에서 검토했다.

---

## Decision Matrix

| # | Topic | Decision | 원안/재설계안 대비 |
|---|-------|----------|-------------------|
| 1 | 두 축 분리 (model tier vs fork) | 유효, 단 단위 재정의 | skill별 Tier → agent별 Tier |
| 2 | fork-worthiness 스코어링 | 입력 분포 기대값으로 보강 | capture "fork 불필요" → "always-fork-haiku 잠정" |
| 3 | 측정 gap (telemetry 토큰) | telemetry 무변경, 벤치마크 신설 | `meta.tokens` 추가안 기각 |
| 4 | 실행 순서 | 선형 Phase → 2트랙 병렬 | facilitator/fork-worthiness 트랙 분리 |
| 5 | plan 배치 | 독립 후속 plan | unified-dev-plan W5 편입 기각 |

---

## Consensus Items

### 1. 라우팅 단위는 skill이 아니라 에이전트

skill을 비-opus로 실행하는 수단은 `context: fork + agent:`뿐이다. skill에는 `model:` frontmatter가 없다. 따라서 실제 구조는 "skill→agent→model" 2단 매핑이며, 원안의 "skill→model" 직매핑(Tier H/S/O)은 존재하지 않는 수단을 가정한 것이다. 비용 제어점은 4개 에이전트로 수렴한다: vault-searcher, vault-file-organizer, vault-knowledge-manager, thinking-facilitator.

### 2. fork-worthiness는 입력 분포에 대한 기대값

fork 여부는 단일 스칼라가 아니라 입력 분포 함수다. capture는 URL 캡처 비율 p에 좌우된다 — 텍스트 메모는 fork 무가치, URL 캡처는 Defuddle 결과(수천 토큰)의 부모 context 오염 때문에 fork 가치가 높다. 조건부 fork(URL이면 fork)는 정적 frontmatter로 구현 불가. 잠정안은 always-fork to vault-file-organizer(haiku)이며, `p·G > (1-p)·C_o` 부등식을 측정으로 확인 후 확정.

### 3. telemetry 스키마 동결, 토큰 측정은 독립 벤치마크

telemetry에 `meta.tokens`를 추가하면 W1 Phase Gate(`validate-schema --since=7d` 0-change)와 충돌한다. 토큰 측정은 별도 고정입력 벤치마크로 한다 — 에이전트별 대표 입력 3-5개, opus vs 대상모델 A/B 실행, `/cost` 비교. 고정입력이라야 입력 크기 혼란변수가 제거돼 순수 모델 델타가 분리된다. fork-worthiness 입력값 = telemetry 빈도(기존) + 벤치마크 건당델타(신설).

### 4. 선형 Phase 폐기, 2트랙 병렬

| 트랙 | 내용 | 메커니즘 | 게이트 |
|------|------|---------|--------|
| A | facilitator sonnet→haiku | 축 A 단독 (`model:`) | 경계케이스 10개 ≥95% |
| B | fork-worthiness 라우팅 | 축 A+B (`context: fork`) | ① fork PoC → ② 측정 → ③ 적용 |

트랙 A는 측정 인프라와 동시 착수(2026-04-16 패널 기승인). 트랙 B의 첫 게이트는 커스텀 에이전트 fork PoC이며, 실패 시 트랙 B만 폐기되고 트랙 A는 무영향(fork 미사용).

### 5. 독립 후속 plan으로 작성

unified-dev-plan W5 편입 기각. 사유: 모델 라우팅은 unified plan W4 Phase Gate 산출물에 의존하는 downstream이고, 기능 추가가 아닌 비용 최적화이며, 직계 조상은 `20260416_cost-optimization-panel`이다. 위치는 `docs/plans/`, 헤더에 진입 의존성(unified-dev-plan W4 Phase Gate)과 계보를 명시.

---

## Action Items

| # | Action | 선행 의존성 | Status |
|---|--------|------------|--------|
| 1 | 커스텀 에이전트 fork PoC (`context: fork + agent: <plugin agent>` 동작 검증) | 없음 — 최선두 | Pending |
| 2 | facilitator `model: sonnet→haiku` + 경계케이스 10개 라우팅 테스트 | 없음 (트랙 A) | Pending |
| 3 | 고정입력 벤치마크 셋 구성 (에이전트별 대표 입력 3-5개) | 없음 | Pending |
| 4 | capture URL 캡처 비율 p 표본조사 | 없음 | Pending |
| 5 | agent별 Tier 재작성 + fork-worthiness 산출 | #1, #3, #4 | Blocked |
| 6 | 독립 후속 plan 문서 작성 (`docs/plans/`) | unified-dev-plan W4 Phase Gate | Blocked |

---

## Key Insights

1. **원안의 근본 결함은 메커니즘 오해**: `context: fork`를 "다운그레이드 수단"으로 썼으나, 실제로는 context 보호 장치다. fork는 모델 결정의 *부수효과*로 모델을 바꿀 뿐, 모델 제어의 1차 수단은 에이전트 `model:` frontmatter다.

2. **모델 다운그레이드는 2차 레버**: 2026-04-16 패널이 확인 — >150k context 누적과 91% subagent-heavy가 1차 비용 동인이다. fork를 *추가*하는 원안 메커니즘은 subagent-heavy를 악화시키며 2차 문제를 공격하는 자기모순 구조였다.

3. **측정 없이 정적 결정 불가**: capture fork-worthiness가 URL 비율에 좌우되는 사례가 보여주듯, 라우팅 결정의 핵심 변수는 측정값이다. 단 측정 수단은 telemetry(빈도)와 벤치마크(건당델타)로 분리돼야 한다.

4. **fork PoC가 트랙 B의 단일 실패점**: `context: fork`의 기존 사례는 `agent: Explore`(내장 에이전트)뿐이다. 커스텀 플러그인 에이전트 fork가 검증되지 않았고, 이것이 fork-worthiness 트랙 전체의 전제다.

---

*5개 토픽 논의 완료 -- 5개 합의 (단위 재정의 1, 보강 2, 구조 재편 2)*

---

## Addendum (2026-05-17) — 전제 정정

본 패널의 핵심 전제 — "SKILL.md에는 `model:` 필드가 없으므로 fork가 유일한 다운그레이드 수단" — 이 2026-05-17 Claude Code 공식 문서(`code.claude.com/docs/en/skills.md`, Frontmatter reference) 확인 결과 거짓으로 판명됐다.

SKILL.md frontmatter는 `model:` 필드를 직접 지원한다. `context: fork` 없이 인라인으로 모델을 오버라이드하며 턴 종료 시 세션 모델로 복귀한다.

따라서 본 패널의 5개 합의 중 fork 메커니즘에 의존하는 부분(Topic 1 라우팅 단위=에이전트, Topic 2 fork-worthiness 스코어링, Topic 4 2트랙 구조)은 무효다. 확정 설계는 `docs/plans/model-routing-2026-05-17.md` — 스킬별 `model:` 직접 지정 방식이다. 본 토론은 의사결정 trail로 보존하되, 실행 기준 문서는 해당 plan이다.
