# claude-kit goal-docs — 열린 이슈 청킹 맵

> 작성일: 2026-06-03 · 소스: 열린 이슈 30건(#94~#130) · Epic 추적: #108

현재 열린 이슈 30건을 **의존성 · 응집도 · 병렬성** 기준으로 12개 실행 단위(goal-doc)로 청킹했어요. 각 `G{n}-*.md`는 Claude Code `/goal` 스킬에 그대로 넣을 수 있는 자기완결 실행 계획이고, **완료 조건 · 쟁점/트레이드오프 · 슬라이스 순서(스킬·에이전트 바인딩) · E2E 자가검증**을 담고 있어요.

핵심 통찰은 Epic #108이 적어둔 그대로예요 — **진짜 미지수는 #100(goal-doc 스펙) 하나로 수렴하고, 나머지는 신규 빌드가 아니라 검증·재배치**예요. 그리고 OVM audit · Bases · thinking-tools 클러스터는 redesign 스파인과 **직교**라 즉시 병렬 착수가 가능해요.

## 청크 일람

| Goal | 문서 | 이슈 | Wave | 모델 | 상태 |
|------|------|------|------|------|------|
| **G1** 재설계 경계 확정 | [G1-redesign-boundary](G1-redesign-boundary.md) | #99 | 1 · foundation | opus | ready |
| **G2** goal-doc 스펙 + 출력 어댑터 계약 | [G2-goal-doc-output-contract](G2-goal-doc-output-contract.md) | #100 #101 #111 | 2 · **LINCHPIN** | opus | ready |
| **G3** 출력 레이어 물리 구조 | [G3-output-layer-structure](G3-output-layer-structure.md) | #102 #103 #124 | 3 | opus | ready |
| **G4** vault-bridge 슬림화 | [G4-vault-bridge-slim](G4-vault-bridge-slim.md) | #104 | 3 · ∥G3 | sonnet | ready |
| **G5** thought-chain dissolve (BREAKING) | [G5-thought-chain-dissolve](G5-thought-chain-dissolve.md) | #105 | 4 | opus | ready |
| **G6** workflow-harness + 3-tier 규칙 | [G6-workflow-harness-rules](G6-workflow-harness-rules.md) | #122 #125 | 4 · ∥G5 | opus | ready |
| **G7** retro 스킬 + telemetry meta | [G7-retro-telemetry](G7-retro-telemetry.md) | #123 #121 | 5 | sonnet | gated(G6) |
| **G8** OVM audit 결정론 검사 4종 | [G8-ovm-audit-deterministic](G8-ovm-audit-deterministic.md) | #126 #128 #129 #130 | 독립 | sonnet | ready |
| **G9** OVM audit vocabulary + tag 추론 | [G9-ovm-audit-vocabulary](G9-ovm-audit-vocabulary.md) | #119 #127 | 독립 · 게이트 | sonnet | gated(#119) |
| **G10** Obsidian Bases 뷰 | [G10-obsidian-bases](G10-obsidian-bases.md) | #118 | 독립 | sonnet | ready |
| **G11** thinking-tools 품질 + stale 청소 | [G11-thinking-tools-quality](G11-thinking-tools-quality.md) | #106 #107 #120 #110 | 독립 | sonnet | ready |
| **G12** backlog/deferred 게이트 추적 | [G12-backlog-gates](G12-backlog-gates.md) | #94 #113 #114 #115 #117 | 게이트 · 착수금지 | haiku | gated |

> #108은 Epic 추적 이슈라 goal-doc 대상에서 제외했어요 — 이 청킹 맵 자체가 #108을 갱신하는 격이에요.

## 의존성 그래프 · 웨이브

```
Wave 1   G1 (#99 경계 A · foundation)
            │
Wave 2   G2 (#100/#101/#111 · LINCHPIN, ralplan consensus 권장)
            ├──────────────┬───────────────┐
Wave 3   G3 (#102/#103/#124)            G4 (#104, ∥G3)
            │                               │
Wave 4   G5 (#105 BREAKING)   G6 (#122/#125, ∥G5)
                                            │
Wave 5                                   G7 (#123/#121)

스파인과 직교 (언제든 병렬):  G8 · G9 · G10 · G11
착수 금지 (결정 게이트):       G12
```

- **G2가 단일 linchpin** — G3·G4·G5·G6·G7이 전부 여기에 의존해요. G2의 goal-doc 스펙이 확정돼야 하류가 안정돼요.
- **독립 클러스터(G8~G11)는 G1~G7 진행과 무관하게 바로 착수 가능**해요. 손이 비면 여기부터 병렬로 돌리는 게 처리량에 유리해요.

## 권장 실행 순서

1. **G1** → **G2**(linchpin, consensus 게이트) 를 직렬로 먼저 굳혀요.
2. G2 머지 후 **G3 ∥ G4 ∥ G6** 병렬, 이어서 **G5**(G3 의존), **G7**(G6 의존).
3. 위와 **병행해서** 독립 클러스터 **G8 · G10 · G11** 를 아무 때나 투입. **G9 · G12**는 게이트 해제 후.

## 게이트 요약 (착수 전 결정 필요)

| Goal | 게이트 조건 |
|------|-------------|
| G2 | ralplan consensus 권장 (linchpin이라 합의 후 착수) |
| G7 | G6(#122 workflow-harness 플러그인) 머지 완료 |
| G9 | #119(E9) backlog 라벨 해제 결정 — E9 vocabulary 기준이 #127 tag 추론의 선행 |
| G12 | 전부 backlog/deferred — 각 항목 해제 조건은 [G12-backlog-gates](G12-backlog-gates.md) 참조 |

## `/goal` 사용법

각 문서는 `/goal` 입력으로 바로 쓸 수 있어요. 예:

```
/goal docs/plans/goal-docs/G8-ovm-audit-deterministic.md
```

문서 안의 **슬라이스 순서**가 실행 단위 분해 + 스킬/에이전트 바인딩이고, **E2E 자가검증** 블록이 에이전트가 스스로 돌려 완료를 확인하는 명령이에요. 대부분 기존 테스트(`check-trigger-regression.py`, `audit-validate.py --dod`, `vault-bridge/scripts/test/*.py`, `json.tool`)를 재사용해요.
