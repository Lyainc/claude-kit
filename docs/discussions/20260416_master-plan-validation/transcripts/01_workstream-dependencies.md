# Transcript 01 — 워크스트림 W0–W8 의존성 및 우선순위

**[Moderator]**: 첫 토픽 시작. Master Plan §4의 워크스트림 순서와 의존성이 타당한지 검토. W0(.vault-link) 선행, W1/W7/W8이 의존, W3/W4/W5/W6 병렬 구조다.

**[Optimistic Practitioner]**: 의존 체인이 선형이라 계획으로서 명료하다. W0 → W1 → W2 → W3+ 병렬. Blocker 최소화 구조.

**[Critical Practitioner]**: W0이 critical path 단일 지점이다. Unresolved 3건(다중 vault, CI, 스키마 버전) 미해결 상태에서 W1/W7/W8이 모두 대기. W0 지연 = 전체 지연.

**[Project Manager]**: 동의. 실무 리스크. 완화책 3가지 제안:
1. W0을 MVP(단일 vault + v1 스키마 고정)로 분해해 선행 배포
2. W3(adversarial-review)는 의존 0이니 모멘텀 유지용 병렬 최우선 착수
3. W7의 `_index` 스키마 강화에서 `vault_link_source` 필드만 제외하면 W0 없이도 분리 진행 가능

**[Knowledge Management Expert]**: 추가 지적 — W4(LLM Wiki의 vault-lint)가 W2(audit)와 **기능 중복**. 둘 다 vault 무결성 검사. W4-lint를 W2 Phase B "빠른 티어(shell)"로 흡수하고, vault-audit는 "깊은 티어(LLM 포함)"로 역할 분리.

**[DX/Tooling Expert]**: 병렬 트랙이라 주장한 W3/W5/W6가 모두 vault-bridge 또는 OVM 수정 — 동시 PR 시 merge conflict 위험. "설계 병렬, 구현 직렬" 정도가 현실적.

**[LLM Orchestration Expert]**: W8이 W0과 W7.`auto_capture` 동시 의존. 더블 블로커. W8 P1(감지+리포트)은 `.vault-link` 없이도 "로컬 경로 그대로 미러링" convention으로 선행 가능. soft 의존화 여지.

**[Moderator]**: 정리: (a) W0 MVP 분해, (b) W3 선행 모멘텀 트랙, (c) W4 vault-lint를 W2에 흡수, (d) W7의 vault_link_source 필드만 분리.

**[Optimistic]**: 합의.
**[Critical]**: 합의.
**[PM]**: 합의.
**[KM]**: 합의.
**[DX]**: 합의.
**[LLM]**: 합의.

**결론**: 조건부 합의 (4개 수정 반영 전제).
