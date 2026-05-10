# Transcript — Topic 4: thinking-tools Trigger Cap (P0 #2)

**Date**: 2026-05-10
**Topic**: "KR 4 + EN 3" trigger cap quantitative basis

---

## Round 1 — Briefing

**[Optimistic Practitioner]**: 트리거 키워드 폭발은 실측됩니다. 7개 SKILL description에 한국어 5~10개 + 영어 5~8개씩 들어있어 합계 ~5KB. cap 적용은 합리적이에요.

**[Critical Practitioner]**: "KR 4 + EN 3"이라는 숫자의 근거가 보고서에 없어요. 왜 5+4가 아니고 3+2가 아닌가? 임의 수치예요.

## Round 1 — Q&A

**[DX/UX Engineer]**: 실제로 자동 라우팅에서 트리거가 작동하려면 사용자 발화 어휘 다양성을 커버해야 해요. 한국어는 동사 어미 변형(-해줘/-하고 싶어/-할까)이 풍부해서 4개로는 부족할 가능성이 있어요. 데이터 없이 4로 자르는 건 라우팅 적중률 회귀 위험.

**[Pragmatic Maintainer]**: 미해결 항목 #2 "thinking-tools 트리거 통계 — ralph/ultrawork 로그 활용 가능성"이 있어요. 통계 수집 후 결정하는 게 맞아요. 임의 cap은 dogfood 회귀를 만들어요.

**[Token Economics Critic]**: 5KB → 2KB 절감 추정도 수상해요. EN 3개 cap 시 한 트리거 평균 길이 12자라면 7개 skill × 5개 절감 × 12자 = 420자, KR도 비슷. 실제 절감은 ~1KB 수준으로 보고서가 과대 추정한 가능성.

**[Plugin Architecture Specialist]**: 더 근본적인 문제. 라우팅 충돌(concretize↔polish, expert↔adversarial)은 trigger 개수 문제가 아니라 trigger 품질 문제예요. cap을 줄여도 충돌은 그대로일 수 있어요. P0 #4(라우팅 충돌 패치)와 P0 #2(trigger cap)는 분리해서 봐야 해요.

## Round 1 — Dialectic

**Thesis**: cap 적용으로 description 다이어트.

**Antithesis** (DX/UX, Pragmatic, Token Economics, Architecture): cap 임계값 무근거 + 충돌 해소와 무관 + 절감량 과대 추정.

**Synthesis** (Plugin Architecture): P0 #2(trigger cap)를 P2로 강등, dogfood 데이터 수집 후 결정. P0 #4(라우팅 충돌 패치)는 GO — 이건 trigger 개수가 아니라 trigger phrase 명시화로 해결되는 문제이고 즉시 효과 명확.

## 결론

P0 #2(trigger cap) 강등 → P2. P0 #4(라우팅 패치)는 GO 유지.

**합의 도달.**
