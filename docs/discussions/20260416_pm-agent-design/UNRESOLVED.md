# Unresolved — PM Agent Design 패널

**Date**: 2026-04-16

모든 주요 토픽 합의 도달. 다음 항목은 **구현 착수 전 결정 필요**한 파생 이슈:

## U1. 핸드오프 artifact 스키마 세부

- JSON Schema vs 구조화 Markdown (frontmatter + changes codeblock) 최종 선택
- 권고(패널): 구조화 Markdown (사람·LLM 모두 가독)
- 결정 필요: schema 버저닝 방식 (`artifact_schema: v1` 필드)

## U2. vault adapter preamble 위치

- Option 1: `/plan-consolidate` skill 본문 상단에 인라인
- Option 2: 별도 `plan-orchestrator/reference/vault-adapter.md` 로 분리 후 skill에서 로드
- 권고: Option 2 (재사용 · 테스트 용이)

## U3. Planner의 AskUserQuestion 시점

- 옵션 A: 감사 리포트 직후 (통합 방향 승인)
- 옵션 B: artifact 생성 직후 (개별 변경 승인)
- 옵션 C: 둘 다
- 권고: 옵션 C. A는 전략 승인, B는 안전 게이트.

## U4. Verifier 기준

- OMC verifier 그대로 쓸 경우, vault 컨벤션 검증 로직은 누가 제공?
- 옵션: verifier 호출 시 preamble로 컨벤션 체크리스트 주입
- 결정 필요

## U5. marketplace 세트 설치 UX

- `claude-kit-suite` 메타 플러그인을 만들어 4개 동시 설치
- vs `marketplace.json`에 "권장 세트" 주석만
- 현재 marketplace.json 스펙에서 세트 설치가 가능한지 확인 필요 (Claude Code 버전 의존)

## U6. plan-orchestrator 플러그인 명명

- 대안: `claude-kit-pm`, `plan-orchestrator`, `project-orchestrator`, `pm-suite`
- 사용자 결정 필요

---

## Referred to Future Panels

- V2 전용 executor/verifier 분화 여부 — MVP 3개월 운영 후 재검토
- AI 기반 plan 감사(중복 탐지 heuristic) 고도화 — 초기 heuristic이 정착한 뒤
