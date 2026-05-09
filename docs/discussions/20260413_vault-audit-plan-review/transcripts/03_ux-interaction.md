# Transcript 03 — UX (AskUserQuestion, Progress, Flag Visibility)

## Briefing
- [Optimistic] AskUserQuestion은 구조화된 인터랙션
- [Critical] 남발 시 오히려 답답

## Q&A
- [UX] 세션당 ≤ 3회 원칙. Q1 bulk, Q2 ambiguous 상위 N개, Q3 apply 확인. 진행률 Total 변경 금지, 이슈 카운터 분리.
- [Architecture] 스킬 시작 시 요약 출력 (clean/dirty/untracked 수치). `--reset-flags`, `status <path>` 커맨드.
- [DevEx] 프로젝트 루트는 frontmatter 병기 허용(인간 가독성), 일반 노트는 sidecar만.
- [Security] `--reset-flags` 무차별 삭제 방지 → 확인 프롬프트.

## Dialectic
- Thesis: 매 단계 AskUserQuestion
- Antithesis: 최소화
- Synthesis: ≤ 3회, ambiguous 상위 N개, 시작 요약, reset-flags 확인

## Conclusion
계획서 반영: UX 규칙 섹션(≤3회/상위 N), 진행률 포맷, 시작 요약 형식, CLI 옵션 세트, reset-flags 확인.
