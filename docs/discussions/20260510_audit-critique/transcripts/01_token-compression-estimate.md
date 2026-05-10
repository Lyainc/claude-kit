# Transcript — Topic 1: Token Compression Estimate (30~40%)

**Date**: 2026-05-10
**Topic**: Audit's "30~40% 토큰 압축" claim — denominator validity

---

## Round 1 — Briefing

**[Optimistic Practitioner]**: 보고서가 "상시 로드 컨텍스트 4~5KB" "세션당 ~600토큰 (vault-searcher description)" 같은 구체 수치를 제시해요. 측정 가능한 명세가 있는 셈이에요.

**[Critical Practitioner]**: "상시 로드"가 정확히 뭔지 정의가 빠져있어요. plugin description은 SessionStart에 한 번 로드되고, agent description은 에이전트 라우팅 결정 시점에만 로드돼요. SKILL.md description도 마찬가지로 항상 로드되는 게 아니에요. "상시"는 부정확한 표현이에요.

## Round 1 — Q&A

**[Token Economics Critic]**: Claude Code 시스템 프롬프트에는 모든 활성 plugin description, 모든 등록된 skill 트리거 description, 모든 등록된 agent description이 시스템 메시지로 포함돼요 — 이건 매 턴마다 캐시 키에 들어가요. 이 영역에 한정하면 보고서의 "상시 로드"는 정확해요. 단, 측정해본 적이 있는지가 핵심이에요.

**[Plugin Architecture Specialist]**: 검증해봤어요 — `vault-bridge/agents/vault-searcher.md:3` description 필드 실측 1,247자, `vault-bridge/.claude-plugin/plugin.json:4` description 757자. 합계 ~2KB. thinking-tools 7개 SKILL의 description 합산은 보고서 추정이지만 합리적이에요. 그러나 "30~40%"의 분모가 무엇인지 보고서가 명시 안 했어요. 분모가 "vault-bridge 단독 description 영역"이면 30~40%가 맞고, "전체 시스템 프롬프트"라면 5%도 안 돼요.

**[Critical Practitioner]**: 그게 핵심 결함이에요. 사용자가 "30~40% 압축"을 읽으면 전체 컨텍스트에 대한 영향으로 오해할 수 있어요. 실측 분모를 명시하지 않은 추정은 마케팅 수치예요.

## Round 1 — Dialectic

**Thesis** (Optimistic): description 영역만 따로 봐도 30~40% 절감은 의미 있는 경량화. 분모 모호성은 부차 문제.

**Antithesis** (Critical, Token Economics): 분모 미명시는 의사결정 왜곡을 만들어요. P0~P1 5개 액션을 다 해도 시스템 프롬프트 전체에서는 1~2% 수준일 가능성이 높아요. 노력 대비 효과가 작으면 우선순위 재배치가 필요해요.

**Synthesis** (Plugin Architecture): 보고서를 받아들이되 "description 영역 한정 30~40%, 시스템 프롬프트 전체 추정 ~3% 미만"으로 재명세. 그러면 P0 #1, #2의 가치는 절대 토큰량이 아니라 description 가독성 + 라우팅 정확도에서 나와요.

## 결론

보고서의 "30~40% 압축" 주장은 분모 명시 후에만 유효. 절감의 진짜 가치는 토큰보다 description 명료성·라우팅 정확도에 있음. P0 #1을 진행하되 동기를 "토큰"이 아닌 "라우팅 신호 노이즈 제거"로 재구성 권고.

**합의 도달.**
