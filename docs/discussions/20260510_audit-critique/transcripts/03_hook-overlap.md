# Transcript — Topic 3: Hook Responsibility Overlap (P1 #6, #7)

**Date**: 2026-05-10
**Topic**: `plan-doc-sync.sh` ↔ `session-end-pre.sh` integration

---

## Round 1 — Briefing

**[Optimistic Practitioner]**: 두 훅을 직접 읽어보면 책임 중복이 명백해요. `plan-doc-sync.sh`(161줄)와 `session-end-pre.sh`(176줄) 양쪽이 .vault-link auto_capture 파싱 + vault_path 추출 + plan-doc 후보 스캔을 거의 동일하게 해요. 통합은 P1 정당해요.

**[Critical Practitioner]**: 잠깐, 두 훅이 실제로 책임이 동일한 게 아니에요. plan-doc-sync.sh는 systemMessage 발화(사용자에게 안내)가 본업이고, session-end-pre.sh는 JSON state 산출(다음 prompt 단계 입력)이 본업이에요. 출력 채널이 달라요.

## Round 1 — Q&A

**[Plugin Architecture Specialist]**: 정확한 지적이에요. 그런데 session-end-pre.sh가 이미 `plan_docs.candidates` 배열을 JSON에 담아요(82~92줄). 그럼 SessionEnd prompt가 그 candidates를 읽어서 systemMessage 역할까지 직접 하면 plan-doc-sync.sh는 SessionEnd 경로에서 완전히 제거 가능해요. 보고서 P1 #7이 정확히 그걸 제안해요.

**[Pragmatic Maintainer]**: 한 가지 우려. plan-doc-sync.sh는 1-ask guard(`asked_flag`)를 가지고 있어요(110~124줄). 통합 시 이 가드 로직을 prompt 또는 pre-hook으로 옮겨야 하는데, plugin.json prompt 안에 이미 `touch plan-doc-asked` 라인이 있어요. 이미 통합 부분이 진행 중인 상태에서 plan-doc-sync.sh가 잔존한다는 거예요. 이건 P1보다 기술 부채로 P0 격상 후보예요.

**[Token Economics Critic]**: hook 통합은 토큰 절감과 무관하지만, 매 SessionEnd마다 두 번 fork되는 python3 호출이 있어요. 측정해보면 SessionEnd당 ~200ms + 메모리 중복. 사용자 체감보다 시스템 부하 관점이에요.

## Round 1 — Dialectic

**Thesis**: P1 #7은 GO, 효과 명확.

**Antithesis** (Pragmatic): P1보다 P0 격상 권고. 이미 SessionEnd prompt가 plan-doc-asked touch까지 진행 중이라 plan-doc-sync.sh의 SessionEnd 경로는 데드 코드 위험.

**Synthesis** (Plugin Architecture): plan-doc-sync.sh의 SessionEnd 경로 제거를 P0로 격상. PostToolUse(DEBUG) 모드는 보존(`VAULT_BRIDGE_PLAN_DOC_DEBUG=1`). plan-doc-syncer.py의 `--discover` 호출자는 session-end-pre.sh로 이전.

## 결론

P0 #1~#5 외에 신규 P0 #6: plan-doc-sync.sh SessionEnd 경로 제거 추가. P1 #6(SessionEnd prompt 압축)은 P0 #6 완료 후 진행.

**합의 도달.**
