# 미해결 이슈

## 1. Frontmatter LLM skim 비용·지연
**상황**: Mode 4 artifact filing 시 type 분류·tag 추론을 위해 본문 skim 필요.
**리스크**: 매번 LLM 호출 시 지연. haiku 경유라 비용은 작지만, 연속 호출 시 누적.
**제안 방향**:
- 1차: rule-based (파일 크기, 헤더 패턴, `.vault-link` 기반 프로젝트 태그 자동)
- 2차: 불확실 시에만 LLM skim
- AskUserQuestion으로 사용자 최종 확인
**보류 사유**: 실제 artifact 유형 분포를 측정한 뒤 정책 결정.

## 2. SessionEnd hook의 AskUserQuestion 불가
**상황**: vault-bridge의 SessionEnd hook은 사용자 부재 상황에서 auto-save 안전망 역할.
**리스크**: AskUserQuestion 강제 정책과 충돌 — 사용자가 이미 세션 종료한 상태에서 질문 불가.
**제안 방향**:
- SessionEnd는 예외로 AskUserQuestion 생략, quick 모드 고정 + 경고 로그
- 또는 `.vault-bridge.local.yml`에 사용자 선호 모드 사전 설정
**보류 사유**: save-session skill 리팩터와 함께 일괄 설계.

## 3. OVM 자동 호출 금지 원칙의 UX 마찰
**상황**: bridge가 `30_Notes/` 쓰기 필요 시 "OVM 경유해주세요" 안내만 제공 (이전 vault-project-link 패널 결론).
**리스크**: 사용자가 "그냥 넣어줘" 요청 시 OVM 명시 호출 번거로움. 매번 안내 읽는 것도 UX 저하.
**제안 방향**:
- 현행 원칙 유지 (plugin 독립성 > UX 편의)
- 또는 `/vault-write` slash command가 내부에서 "bridge or OVM 위임" 라우팅 담당
**보류 사유**: slash command 설계와 함께 후속 패널에서 재평가.

## 4. 경계 테스트 자동화
**상황**: 쓰기 범위·덮어쓰기 금지·OVM 경계를 수동 테스트로만 검증.
**리스크**: 리그레션 감지 늦음. 플러그인 manifest나 agent description 변경 시 사일런트 실패.
**제안 방향**: 간단한 bats/shell 스크립트로 5케이스 자동 검증 (inbox 신규 / project 신규 / notes 거부 / 덮어쓰기 거부 / 실패→에러 포맷).
**보류 사유**: 테스트 인프라 전반과 함께 설계 필요.
