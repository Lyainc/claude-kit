# Transcript — Topic 5: Cleanup-Critic Consistency + Missing Areas

**Date**: 2026-05-10
**Topic**: Apply same critic standard to audit itself + identify gaps

---

## Round 1 — Briefing

**[Critical Practitioner]**: 같은 날(2026-05-10) cleanup 세션에서 사용자가 7개 작업 후보 중 6개를 데이터 부재를 사유로 보류했어요. "vault-log: 6주 dogfood 회고 필요", "obsidian-bases: dogfood 후 재결정", "W10 Phase D: 사용 빈도 데이터 없음". 동일 기준을 본 감사 액션 플랜에 적용하면 P0~P1 12개 항목 중 몇 개가 살아남을지 의문이에요.

**[Optimistic Practitioner]**: 그건 부당한 비교예요. cleanup의 6개 보류는 신규 기능 추가 후보였고, 본 감사의 P0~P1은 기존 기술 부채 정리예요. 적용 기준이 달라야 해요.

## Round 1 — Q&A

**[Pragmatic Maintainer]**: 부분 동의해요. 기존 부채 정리도 effort/value 비율을 측정하긴 해야 해요. 이번 토론에서 P0 #2를 강등한 게 정확히 그 critic 적용이에요. 남은 P0 4개와 신규 P0 #6 모두 dogfood 데이터 없이도 진행 정당화 가능한지 한 번 더 점검해야 해요.

**[Plugin Architecture Specialist]**: 적용해볼게요.
- P0 #1 (vault-searcher description 압축): 실측 1247자 확인됨, 라우팅 충돌 5건 중 2건 해소. dogfood 불필요 — GO.
- P0 #3 (README 카운트 동기화): 단순 일관성 수정. GO.
- P0 #4 (라우팅 description 패치): 충돌이 본문에서 명시됨. GO.
- P0 #5 (facilitator 트리거 조건 명시): description 한 줄 추가. GO.
- 신규 P0 #6 (plan-doc-sync.sh SessionEnd 제거): 코드 중복 실측됨. GO.

**[DX/UX Engineer]**: 누락 영역 추가 발굴할게요.
1. slash command 명세 부재: `/vault-manifest-refresh`, `/vault-commit`, `/save-plan-doc` 같은 vault-bridge 명령을 README에서 발견 못 해요. 보고서가 thinking-tools 슬래시는 짚었는데 vault-bridge 슬래시는 누락.
2. kill switch 가시성: `VAULT_BRIDGE_DISABLE`, `VAULT_BRIDGE_STRICT_NAMING`, `VAULT_BRIDGE_PLAN_DOC_DEBUG` 등 환경변수가 코드에만 있고 README에 표 부재.
3. 에이전트 model 분포 검증 부재: vault-searcher만 haiku, 다른 vault-knowledge-manager는 sonnet 추정. 비용/성능 trade-off가 description에 표시되어 있지 않음.

**[Token Economics Critic]**: 누락 영역 추가.
4. PreToolUse 빈도 측정: pre-access-guard.sh가 매 Read/Grep/Glob마다 발화. 한 세션에 50~200회 호출 가능. 매 호출 jq×2 + python3 = ~150ms × 100회 = 15초 누적. 보고서가 systemMessage cap만 짚고 호출 자체의 부하는 누락.
5. manifest 캐시 TTL: vault-searcher Mode 2/3가 manifest.json을 24h 캐시 사용. 변경 빈번한 vault에선 stale fall-through가 매번 일어나 캐시 가치 0. 실측 cache hit rate가 보고서에 부재.

## Round 1 — Dialectic

**Thesis** (Optimistic): 본 감사는 기술부채 정리 성격이 강해 dogfood 기준 미적용 정당.

**Antithesis** (Critical, Pragmatic, DX/UX, Token Economics): 동일 critic 기준 적용 시 P0 #2는 이미 강등됨. 추가로 5개 누락 영역이 있어 보고서가 완전하지 않음.

**Synthesis** (Plugin Architecture):
- 본 감사 자체에 cleanup critic 적용 → 살아남는 P0: #1, #3, #4, #5, #6(신규).
- 추가 개선 후보 5건은 P2로 신규 등록.
- 보고서는 효과 있음. 단, 분모 명시 + cap 데이터 수집 + 누락 영역 보완 후에 완전체.

## 결론

감사 보고서는 유의미한 효과 있음. 단, P0 #2 강등 + P0 #6 신규 추가 + 5개 누락 영역 P2 등록 권고.

**합의 도달.**
