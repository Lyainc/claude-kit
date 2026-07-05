# Build Spec — Tech Domain Question Bank

Use these as the basis for Phase 1 interview questions in technical projects.
Select the most relevant question per dimension per round. Adapt to user's specific context.

## Goal Clarity

- 이 도구/기능/시스템이 해결하려는 핵심 문제가 무엇인가요?
- 기존에 이 문제를 어떻게 해결하고 있나요? 무엇이 부족했나요?
- 이 기능의 주요 사용자는 누구인가요? (개발자, 엔드유저, 시스템?)
- 이것이 완성되면 어떤 워크플로우가 바뀌나요?
- 가장 핵심 기능 하나만 고른다면 무엇인가요?

## Constraint Clarity

- 기술 스택이나 언어 제약이 있나요? (예: Python 3.10+, Node 18+)
- 실행 환경 제약이 있나요? (서버, 클라이언트, CLI, 브라우저, 모바일)
- 성능 요구사항이 있나요? (응답시간, 처리량, 메모리 상한)
- 보안 또는 컴플라이언스 제약이 있나요?
- 일정이나 팀 규모 제약이 있나요?
- 외부 의존성(API, 라이브러리, 서드파티 서비스) 제약이 있나요?

## Success Criteria

- 어떤 테스트가 통과하면 이 기능이 완성됐다고 할 수 있나요?
- 최소 기능 요건(MVP)을 정의한다면 어떻게 되나요?
- 성능 기준이 있나요? (예: p95 응답시간 < 200ms)
- 기존 기능을 깨뜨리지 않아야 하는 범위는 어디까지인가요?
- 사용자가 "이거 잘 된다"고 느끼는 순간은 언제인가요?

## Context Clarity (brownfield)

- 어느 모듈/파일/서비스에 이 기능을 추가할 예정인가요?
- 기존 데이터베이스 스키마나 API 계약에 영향을 주나요?
- 기존 코드베이스에서 재사용할 수 있는 부분이 있나요?
- 이 변경이 다른 팀의 코드나 서비스에 영향을 주나요?
- 기존 테스트 스위트와 통합해야 하나요?
