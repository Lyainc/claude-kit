# TOPIC 2: AskUserQuestion 기반 UX (P2)

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing
**[UX/DX Expert]**: 이번 세션 flow 추적 — mode 선택·저장 확인이 plain text 대화로 진행됨. AskUserQuestion 미사용 → 자유 텍스트 파싱 부담, 버튼 클릭의 확정성 부재.

## Q&A
**[Claude Code Platform Expert]**: AskUserQuestion은 3~5개 이산 선택에 적합. mode 3개, save/edit/cancel 3개 — 완벽한 케이스.

**[Optimistic Practitioner]**: 수정 요청 단계는 "어느 부분?" 옵션화 어려움. 자유 텍스트 남아야 함.

**[UX/DX Expert]**: 하이브리드. 이산 선택 = AskUserQuestion, 자유 지시 = plain text. 수정도 2단계: "어느 섹션?"(옵션) → 섹션 수정 지시(자유).

**[Critical Practitioner]**: skill body에 **금지 예시와 권장 예시 병기**. "`record/handoff/quick 중 골라주세요`" 같은 plain text 질문을 anti-pattern으로 박음.

**[Plugin Architecture Expert]**: 강제 메커니즘은 skill instruction 레벨만. hook으로 "plain text 질문" 탐지 어려움 — 비용 대비 효과 낮음. 문서 강제 + 리뷰 의존.

## Dialectic
**Thesis**: 모든 상호작용 AskUserQuestion 강제.
**Antithesis**: 자유 텍스트가 필요한 지점 존재.
**Synthesis**: 이산 선택만 강제, 자유 지시 유지, skill body에 anti-pattern 명시.

## 결론
- 이산 선택(mode, save/edit/cancel, 섹션 고르기) → AskUserQuestion 강제
- 자유 지시(수정 내용, 커스텀 태그) → plain text
- save-session skill body에 금지/권장 예시 명시
- Hook 검증 포기 (문서 + 리뷰 의존)
