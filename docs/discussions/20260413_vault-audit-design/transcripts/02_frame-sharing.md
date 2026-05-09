# Transcript 02 — Frame Sharing (inbox-review vs vault-audit)

## Briefing

**[Optimistic Practitioner]**: SCAN/PROPOSE/CONFIRM 3단 파이프라인은 본질적으로 같은 구조. 유지보수 단일화.

**[Critical Practitioner]**: 두 작업 시간/의도 특성 다름. inbox-review = 초단기·분류, vault-audit = 장시간·검출·수정. 한 프레임 강제는 전형적 잘못된 DRY.

## Q&A

**[UX Expert]**: 사용자 심성모형 다름. inbox = "들어온 것 처리"(능동), audit = "방치된 것 점검"(수동). 같은 UI로 묶으면 혼란.

**[Architecture Expert]**: 공유할 것은 프레임 아닌 프리미티브. `scanner`, `proposer`, `confirmer`, `audit-state`를 OVM 내부 라이브러리로. 스킬 UX는 독립.

**[PKM Expert]**: Logseq/Roam/Reflect 모두 inbox와 audit을 별도 명령으로 유지. 통합 시도는 실패 사례.

## Dialectic

- Thesis: 한 프레임 공유
- Antithesis: 완전 분리
- Synthesis: 로직 공유(프리미티브) + UX 분리. 질감은 출력 포맷(evidence, 진행률) 표준화로 달성.

## Conclusion

**결론**: 프레임 강제 통합 반대. 공통 프리미티브 추출, 출력 형식 표준화로 일관성 확보.
