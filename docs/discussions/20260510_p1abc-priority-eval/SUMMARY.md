# P1a/b/c 자동화 후보 비용/가치 평가 — Expert Panel

**Date**: 2026-05-10
**Context**: 직전 unknown-discovery 결과(타깃 = 본인 future self, 매일 막힘 3대 지점) 기반 우선순위 평가
**Panel**: Moderator + Optimistic Practitioner + Critical Practitioner + Claude Code Platform Expert + Plugin Maintenance Expert + Cognitive Ergonomics Expert

---

## 평가 대상

| 카테고리 | 본인 매일 막힘 지점 |
|---|---|
| **P1a · 명령어 cheatsheet** | 명령어 이름/플래그/순서를 자주 까먹음 |
| **P1b · hook 자동화 누락 영역** | 자동화 가능한 어귀에 매번 수동 개입 |
| **P1c · 인자/옵션 디폴트·프리셋** | 자주 쓰는데 매번 같은 인자·옵션 입력 |

---

## 합의 사항

### 1. 진행 순서 — P1a → P1b → P1c (만장일치)

근거 3중 일치:
- **포괄성**: P1a가 까먹음 4종(존재/이름/인자/순서) 중 (1)(2)(3) cover. P1c는 (3)만.
- **자기 모순 회피**: P1a 없이 P1c부터 가면 "본인이 만든 alias도 까먹는" 자기참조 함정.
- **흡수 그래프**: 우선순위 P1a → P1b → P1c는 흡수 root부터 leaf 순. P1a = fallback contract, P1b = optimization, P1c = micro-optimization.

### 2. 비용 순서 — P1c < P1a < P1b (cumulative)

| 카테고리 | 주요 실패 모드 | mitigation |
|---|---|---|
| P1a | drift (명령어 갱신과 cheatsheet 갱신 분리) | 명령어 frontmatter에서 자동 추출 |
| P1b | silent failure (hook 잘못 발화 시 작업 중단) | systemMessage 가시성 강제 디폴트, exit 0 log-only 기본 |
| P1c | env-bound (다른 머신에서 깨짐) | repo commit + setup script |

P1b 진행 시 P1a 비용도 함께 증가 (hook 카탈로그 cheatsheet 포함 필요).

### 3. 흡수 ≠ 가치 (만장일치)

P1b의 강한 흡수력은 *우선순위 정당화*가 아니라 *역할 분리*에 활용.
- P1a = 항상 fallback 가능한 명시 경로
- P1b = 자주 쓰는 패턴의 자동화 layer
- P1c = cheatsheet 위 thin layer

P1b 단독 의존은 *공급망 risk*. P1b 깨져도 P1a로 회복 가능한 구조 필수.

---

## 권고 (Action Items)

### P1a — 명령어 cheatsheet (즉시 착수 가능)

- 모든 명령어/슬래시/스킬을 표 형태로 정리. 카테고리: 자주 쓰는 명령어 / 플래그·옵션 / 워크플로 단계
- **drift mitigation 필수**: 명령어 description frontmatter에서 자동 추출하는 빌드 스크립트. 수동 갱신 금지
- 표면 결정: `/omc-cheatsheet` 슬래시 vs SessionStart hook 1회 hint vs AGENTS.md 한 섹션 — Deep Dive 후속 인터뷰 필요

### P1b — hook 자동화 누락 영역 (P1a 후)

- 본인이 *반복 수동 개입*하는 곳을 1주간 관찰 후 hook화 후보 식별
- 가시성 디폴트 강제: 모든 hook은 fired 시 systemMessage로 알림. opt-in으로 silent 전환
- P1a 카탈로그에 hook도 등재

### P1c — 인자/옵션 디폴트·프리셋 (P1b 후)

- P1a + P1b로 흡수되지 않은 잔여 영역만 alias화
- 박을 위치 결정 필요 (zsh / Claude Code settings / plugin 안 — 각 trade-off 다름)

---

## 핵심 Insight

진행 순서, 비용 순서, 흡수 그래프 — 세 독립 차원이 *동일 결론*에 수렴. P1a → P1b → P1c는 우연 일치가 아니라 **fundamental layer부터 쌓아 올리는 자연스러운 sequence**.

---

## 다음 단계 후보

- **Deep Dive (deep-interview)**: P1a 구체 설계 — 표면(슬래시/hook/AGENTS.md) 결정, frontmatter 자동 추출 스크립트 명세, drift 검증 방법.
- **Action Plan**: P1a 실행 계획을 task 분해 후 executor 위임.
- **Skip P1b/P1c 단계로 진행**: P1a 완성 후 본인 사용 패턴 관찰 — *실제* hook 후보 식별 후 P1b 재평가.

───
*3 토픽 논의 완료 · 3개 합의, 0개 보류 · Phase 2 documentation complete*
