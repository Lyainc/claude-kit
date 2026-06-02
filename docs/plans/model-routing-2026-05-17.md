---
created: 2026-05-17
tags: [plan, claude-kit, model-routing, cost-optimization]
type: plan
status: done
related:
  - docs/discussions/20260416_cost-optimization-panel/SUMMARY.md
  - docs/discussions/20260517_model-routing-redesign/SUMMARY.md
---

# Model Routing — claude-kit 스킬 모델 티어링

> **상태 (2026-06-03 갱신): ✅ 완료.** `1650ee6`(2026-05-17)이 8개 스킬에 `model:` frontmatter 적용. 이후 PR #84(05-26)가 project/inbox-review/archive 3개를 삭제했으나 frontmatter가 파일과 함께 사라진 것뿐 — 계획 무효화 아님. 살아남은 유효 타깃 5개 모두 계획값 일치(capture=haiku·audit=haiku·note=sonnet·doc-polish=sonnet·diverse-sampling=sonnet, +spec-first=sonnet 보너스). facilitator haiku 다운그레이드는 테스트 후 기각(sonnet 유지)으로 Phase 2 종료. 아래는 결정 기록(보존).

## 목적

claude-kit의 14개 스킬은 모델 지정이 없어 호출 세션 모델(주로 Opus)을 상속한다. mechanical한 스킬(capture 등)까지 Opus로 실행되는 것은 토큰 낭비다. 각 스킬이 요구하는 추론 깊이에 맞춰 모델 티어를 지정한다.

## 계보

| 단계 | 산출물 | 결과 |
|------|--------|------|
| 2026-04-16 | `20260416_cost-optimization-panel` | facilitator haiku 조건부 승인, vault-knowledge-manager 보류, context fork 유지 |
| 2026-05-10 | `plan-2026-05-10-skill-model-routing.md` (vault) | `context: fork + agent:` 위임 방식 — 의존성 이슈 6개로 백지화 |
| 2026-05-17 | `20260517_model-routing-redesign` expert-panel | fork-worthiness 2트랙 설계 — 전제 오류로 폐기 |
| 2026-05-17 | **본 문서** | `model:` frontmatter 직접 지정으로 확정 |

## 폐기 사유 — fork 기반 설계

2026-05-10 plan과 2026-05-17 expert-panel은 모두 **"SKILL.md에는 `model:` 필드가 없으므로, 스킬을 싼 모델로 실행하려면 싼 모델 에이전트로 `context: fork`하는 수밖에 없다"**는 전제 위에 세워졌다.

이 전제는 거짓이다. Claude Code 공식 문서(`https://code.claude.com/docs/en/skills.md`, "Frontmatter reference")가 SKILL.md frontmatter의 `model:` 필드를 명시한다:

> `model` — Model to use when this skill is active. The override applies for the rest of the current turn and is not saved to settings; the session model resumes on your next prompt. Accepts the same values as `/model`, or `inherit` to keep the active model.

따라서 fork PoC, fork-worthiness 분석, cross-plugin path BLOCKER, 측정 인프라가 전부 불필요하다.

## 메커니즘

- SKILL.md frontmatter에 `model:` 키 한 줄 추가
- `context: fork` 없이 메인 컨텍스트에서 해당 모델로 인라인 실행, 턴 종료 시 세션 모델로 자동 복귀
- 플러그인 스킬에도 동일 적용 (문서 "Where skills live" 표)
- 값: `haiku` / `sonnet` / `opus` 별칭 또는 `inherit`
- 가역적: 변경이 1줄이고 턴 단위 자동 복귀라 롤백은 라인 삭제

## 티어 배정

`model:`을 명시 추가하는 것은 haiku·sonnet 티어뿐. opus 티어는 필드 미추가(= 세션 모델 inherit) — sonnet 기본 사용자에게 Opus를 강제하지 않기 위함.

| 스킬 | 플러그인 | 티어 | 근거 |
|------|---------|------|------|
| capture | obsidian-vault-manager | haiku | 즉시 저장 + 경로 출력, 판단 없음 |
| vault-audit | obsidian-vault-manager | haiku | SCAN/CLASSIFY가 LLM=0·rule-based |
| note | obsidian-vault-manager | sonnet | 도메인 분류 + MOC 링킹 (조용한 실패 리스크) |
| project | obsidian-vault-manager | sonnet | 프로젝트 구조화·승격 판단 |
| inbox-review | obsidian-vault-manager | sonnet | 4단계 분류 파이프라인 + AskUserQuestion |
| archive | obsidian-vault-manager | sonnet | Home.md·MOC 구조 편집 |
| doc-polish | thinking-tools | sonnet | 3-layer 교정 (Editor 역할) |
| diverse-sampling | thinking-tools | sonnet | VS 기법이 구조화 프롬프트로 다양성을 확보 — sonnet 적정, opus 비용 불요 |
| doc-concretize | thinking-tools | opus (미추가) | 재귀적 심층 작성 |
| expert-panel | thinking-tools | opus (미추가) | 변증법적 심층 추론 |
| unknown-discovery | thinking-tools | opus (미추가) | 소크라테스식 심층 인터뷰 |
| thought-chain | thinking-tools | opus (미추가) | 파이프라인 오케스트레이션 + 단계 간 종합 |
| adversarial-review | thinking-tools | opus (미추가) | 1:1 공격·방어 심층 추론 |
| context | obsidian-vault-manager | 변경 없음 | 이미 `context: fork` — 2026-04-16 패널이 fork 유지 결정 |

## 변경 범위

**스킬 frontmatter (8개)**: capture·vault-audit → `model: haiku`; note·project·inbox-review·archive·doc-polish·diverse-sampling → `model: sonnet`

**메타데이터**: `claude-kit/CLAUDE.md`의 "SKILL.md Frontmatter" 섹션에 `model:` 필드 설명 추가; `obsidian-vault-manager`·`thinking-tools` plugin.json version bump + marketplace.json 동기화

## Phase 2 — facilitator (테스트 완료 — 미진행)

`thinking-tools/agents/thinking-facilitator.md`는 에이전트이므로 frontmatter `model:`이 이미 존재(`sonnet`). 2026-04-16 패널이 haiku 다운그레이드를 조건부 승인했고, 게이트는 경계케이스 10개 라우팅 정확도 ≥95%였다.

**테스트 결과 (2026-05-17)**: 10개 경계케이스 블라인드 라우팅 — haiku 7/10 (70%), sonnet 9/10 (90%). haiku는 게이트(95%)에 크게 미달했고, 부정형 무시(Case 8 — "전문가 토론 말고"를 무시하고 expert-panel 라우팅)·신호 오분류(Case 4 — unknown-discovery를 doc-polish로) 같은 결정적 오답을 냈다.

**판정**: facilitator는 `model: sonnet` 유지. haiku 다운그레이드 미진행, Phase 2 종료. 상세는 `20260517_model-routing-redesign/UNRESOLVED.md` Issue 3. 부수 발견(facilitator decision tree의 expert-panel↔thought-chain 미구분)은 같은 문서 Issue 5.

## 하지 않는 것

- **fork PoC / fork-worthiness 분석** — `model:` 필드가 답이므로 불필요
- **벤치마크·telemetry 스키마 변경** — 변경이 1줄 + 자동 복귀라 위험도가 낮음. telemetry는 기존대로 빈도만 수동 관찰
- **vault-knowledge-manager 다운그레이드** — 2026-04-16 패널이 "조용한 실패" 리스크로 보류. 새 근거 없으면 유지
- **context 스킬** — `context: fork`(agent: Explore)로 이미 forked 실행. 공식 문서상 forked 스킬의 실행 모델은 `agent` 타입이 결정하므로 스킬 레벨 `model:` 티어링이 그대로 적용되지 않는다. 2026-04-16 패널의 fork 유지 결정과도 일관 — 본 범위에서 제외, 필요 시 별도 재검토.

## 검증

**`model:` 필드 동작 전제**: SKILL.md frontmatter의 `model:` 필드는 Claude Code 공식 문서(`code.claude.com/docs/en/skills.md`, Frontmatter reference)에 명시돼 있으며 2026-05-17 WebFetch로 verbatim 확인했다. 단 — 인라인 모델 오버라이드의 *런타임 동작*(실제로 해당 모델로 실행되고 턴 종료 시 세션 모델로 복귀하는지)은 기계적으로 검증되지 않았다. 아래 검증 1~4는 frontmatter 유효성·기능 회귀 부재까지만 보장한다. 런타임 라우팅은 사용 중 관찰로 확인할 사안이다.

1. 기능 회귀 0 (기준: 기능 회귀 0 / 표현 회귀 허용) — 8개 스킬 각 1회 실행하여 정상 동작 확인. vault-audit는 `audit-validate.py --dod`로 9개 에러 타입 탐지 확인
2. JSON 유효성 — plugin.json ×2 + marketplace.json
3. 플러그인 회귀 — CLAUDE.md Validation 섹션 테스트 스크립트
4. telemetry 수동 관찰 — `report.py --top=10` 스킬 호출 분포
