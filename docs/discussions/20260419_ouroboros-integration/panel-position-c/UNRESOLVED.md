# Unresolved — Position C 검증 패널

**Date**: 2026-04-19

3개 주요 토픽 모두 합의 도달. 다만 다음 파생 이슈는 **구현 착수 전 결정 필요**:

## U1. improvement-matrix.md의 W 섹션 가시성

- 합의: W(약점) 섹션은 contributor 전용, M(방향성) 섹션은 user + contributor
- **결정 필요**: 같은 파일 내 섹션 분리로 충분한가, 아니면 W 항목을 별도 파일(`thinking-tools/docs/internal/weaknesses.md`)로 분리해야 하는가?
- 권고(Plugin Expert): 같은 파일 + 헤더에 청자 명시. 분리 시 동기화 비용.
- 결정 시점: improvement-matrix.md 초안 작성 직전.

## U2. 분기별 리뷰 자동화 여부

- 합의: `next_review: 2026-07-19` frontmatter 명시
- **결정 필요**: 리뷰 알림을 (a) GitHub Action으로 자동 issue 생성, (b) 수동, (c) Calendar 연동 중 어느 것?
- 권고(OSS Maintainer): GitHub Action이 가장 가벼움 (`actions/github-script`로 issue 자동 생성)
- 결정 시점: matrix 첫 분기 리뷰(2026-07-19) 도래 전 1개월.

## U3. dev-plan Phase D를 매트릭스가 아닌 별도 spinoff 문서로 분리하는 옵션

- Critical Practitioner 대안 제안: `docs/discussions/20260419_ouroboros-integration/phase-d-spinoff.md`
- 다수 패널 의견: 매핑 표만 명시하면 spinoff 불필요
- **결정 필요**: 향후 Phase D 항목이 5개 이상 추가되면 spinoff 검토 (현재는 6개)
- 결정 시점: dev-plan v0.2.0 (Phase 항목 변경 시) 또는 Phase D 작업 착수 시.

## U4. 다른 플러그인(OVM, vault-bridge)의 improvement-matrix

- 합의: 지금은 thinking-tools 단일 파일로 충분. 빈 매트릭스 3개 만들지 않음 (Plugin Expert 권고).
- **결정 필요**: OVM 또는 vault-bridge에 동등한 매트릭스가 필요해지는 트리거 시점은?
- 권고: 각 플러그인의 비-trivial 개선안이 3건 이상 누적될 때 신설.
- 결정 시점: 누적 시점 도래 시 즉시.

## U5. CHANGELOG.md 트리거 자동화

- 합의: matrix 항목 진척 시 CHANGELOG 동시 갱신
- **결정 필요**: 강제 메커니즘 — (a) PR 템플릿 체크박스, (b) pre-commit hook, (c) 명시 안 함 (수동 신뢰)
- 권고(Critical): 체크박스 (가장 가벼움)
- 결정 시점: 첫 matrix 항목 resolution PR 직전.
