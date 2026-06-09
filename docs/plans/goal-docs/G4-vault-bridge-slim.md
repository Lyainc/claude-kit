---
goal_id: G4
title: vault-bridge 슬림화 — haiku read + gated write + 결정론 hooks
issues: [104]
wave: 3
depends_on: [G2]
recommended_model: sonnet
status: ready
work_type: feature-full
created: 2026-06-03
---

# G4 — vault-bridge 슬림화 — haiku read + gated write + 결정론 hooks

## 배경 / 목적

vault-bridge는 원래 "haiku 순수 딜리버리" 레이어로 설계됐지만, 자체 pre-write-guard(Write Role Contract)가 서브에이전트 vault write를 차단하는 구조 때문에 write는 구조적으로 메인컨텍스트 전용이에요. 즉 "haiku 딜리버리"라는 초기 직관은 **read에만 성립**하고, write는 위임 불가예요.

이 불일치를 명시적으로 수용하는 게 이 묶음의 핵심이에요. 저작 책임(session-note·handoff·plan-doc 작성)을 ② 출력 레이어(G2)로 evict하고, vault-bridge는 세 역할로만 남아요:

1. **vault-searcher** — haiku read 전용 에이전트 (현행 유지)
2. **메인컨텍스트 write primitive** — 슬래시 명령이 직접 Write 도구를 실행 (user-initiated)
3. **결정론 hooks** — Stop·SessionEnd·SessionStart·PreToolUse (LLM 호출 없는 shell scripts)

"haiku 딜리버리 = read 전용, write = 메인(Write Role Contract)" 비대칭을 agent 정의·CLAUDE.md·plugin.json description에 명문화하는 게 이 작업의 가치예요. 슬래시 명령 이름(`/save-session`, `/handoff`, `/save-plan-doc` 등)은 보존해요 — compose-via-② → deliver 패턴으로 UX 연속성 확보.

## 포함 이슈

- #104: refactor: slim vault-bridge to haiku-read + gated-write + hooks — 저작 책임 evict, `/save-session`·`/handoff` 동작 유지, vault-bridge test-* 회귀 green 보장

## 완료 조건 (Definition of Done)

- [ ] `vault-searcher.md` description에 "read-only; write = main context (Write Role Contract)" 비대칭이 명시돼 있어요
- [ ] `plugin.json` description에 "haiku read-only vault-searcher + main-context write primitives + deterministic hooks" 구조가 반영돼 있어요
- [ ] CLAUDE.md(루트) `vault-bridge Hooks & Commands` 섹션에 Write Role Contract 비대칭이 명시적으로 문서화돼 있어요
- [ ] `/save-session` 명령 파일이 ② 출력 레이어에서 저작 책임을 흡수한 레시피를 참조하거나 인라인으로 포함해요 (G2 완료 후 연결)
- [ ] `/handoff` 명령 파일이 저작 단계를 메인컨텍스트 전용으로 명시해요 (vault-searcher 위임 없음)
- [ ] `/save-plan-doc` 명령 파일이 저작 단계를 메인컨텍스트 전용으로 명시해요
- [ ] `pre-write-guard.sh`의 Write Role Contract 기본값이 `enforce`로 유지돼 있어요 (현행 유지 확인)
- [ ] vault-searcher가 write 요청을 받으면 `/save-session` 또는 `/save-plan-doc` slash command로 리다이렉트하는 예시가 보존돼 있어요
- [ ] 슬래시 명령 이름 6개 모두 보존: `/save-session`, `/handoff`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`, `/save-plan-doc`
- [ ] vault-bridge 회귀 테스트 9개 전부 green:
  ```bash
  python3 vault-bridge/scripts/test/test-discover.py
  python3 vault-bridge/scripts/test/test-manifest-type-optin.py
  python3 vault-bridge/scripts/test/test-pre-access-guard.py
  python3 vault-bridge/scripts/test/test-pre-write-guard.py
  python3 vault-bridge/scripts/test/test-vault-commit-message.py
  python3 vault-bridge/scripts/test/test-manifest-promotion.py
  python3 vault-bridge/scripts/test/test-vault-path.py
  bash vault-bridge/scripts/test/test-stop-check.sh
  bash vault-bridge/scripts/test/test-handoff-guard.sh
  ```
- [ ] shell hook syntax 통과:
  ```bash
  bash -n vault-bridge/hooks/stop-check.sh
  bash -n vault-bridge/hooks/session-end-pre.sh
  bash -n vault-bridge/hooks/session-start-manifest.sh
  bash -n vault-bridge/hooks/pre-access-guard.sh
  bash -n vault-bridge/hooks/pre-write-guard.sh
  ```
- [ ] plugin.json JSON 유효성 통과:
  ```bash
  python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null
  ```
- [ ] marketplace.json과 plugin.json의 version·description·keywords 동기화 확인

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| `/save-session` 저작 레시피 위치 | A) `session-note-recipe.md` 보존 (vault-bridge 내 in-place) / B) 별도 출력 플러그인으로 이전 후 참조 | **A — ADR 확정** | G3 #102 ADR이 출력 레이어를 **분산·in-place**로 확정 → 이전할 별도 플러그인 없음. recipe는 vault-bridge(boundary line 26 = ③ 딜리버리) 내 `session` ③ 딜리버리 어댑터 구현부로 잔류, 어댑터 귀속 라벨링만 추가 |
| Write Role Contract 기본값 | `warn` vs `enforce` | `enforce` 유지 | pre-write-guard.sh 현행이 `enforce`; 슬림화 목표와 정합. 이완하면 서브에이전트 write 차단 의미 퇴색 |
| vault-searcher description 길이 | 현행 상세 유지 vs 핵심만 남기기 | 핵심 보존 + 비대칭 명시 추가 | read-only 비대칭이 신규 독자에게 명확해야 함. 기존 예시·모드 설명 축약하면 오해 위험 |
| G4 착수 시점 | G2(#100)+G3 ADR 확정 후 vs 그 전 | **#100 CLOSED + G3 #102 ADR 후** | ② 물리 구조(분산·in-place)가 ADR로 확정돼야 recipe 처리 방향이 정해짐. #100 CLOSED + ADR 확정으로 게이트 해제 |
| `session-note-recipe.md` 잔존 여부 | 이전 후 삭제 vs vault-bridge 내 보존 | **보존 — ADR 정합** | ADR 분산·in-place라 이전 대상 자체가 없음. 삭제 시 `/save-session` 진입점이 깨짐(dangling). vault-bridge 내 유지 + ③ 딜리버리 어댑터 라벨링이 드리프트 없는 정답 |

**게이트 조건 (해제됨)**: G2(#100 — goal-doc 스펙·출력 어댑터 *계약*)는 CLOSED. ② 출력 레이어 물리 구조는 G3 #102 ADR이 **분산·in-place**로 확정 → recipe를 이전할 별도 출력 플러그인이 없음. 따라서 S2/S3는 '이전·삭제'가 아니라 **'in-place ③ 딜리버리 어댑터 라벨링'**으로 실행해요(vault-bridge = boundary line 26 ③ 딜리버리; `/save-session`=③ 운반, `/handoff`=vault 비경유). (이 goal-doc은 2026-06-03 작성으로 ADR(06-04)보다 하루 앞서, 원안 쟁점표는 '② 단일 흡수'를 가정했었음 — 위 표는 ADR 반영해 교정함.)

## 슬라이스 순서

1. **S1 비대칭 명문화** → 바인딩: `executor` (sonnet) | 대상 파일: `vault-bridge/agents/vault-searcher.md`, `vault-bridge/.claude-plugin/plugin.json`, `CLAUDE.md` | 산출: "haiku = read-only, write = main context (Write Role Contract)" 비대칭을 description·문서에 명시 | 검증: `python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null`; vault-searcher.md grep으로 "Write Role Contract" 또는 "read-only" 포함 확인

2. **S2 슬래시 명령 ③ 딜리버리 어댑터 명문화** → 바인딩: `executor` (sonnet) | 대상 파일: `vault-bridge/commands/save-session.md`, `vault-bridge/commands/handoff.md`, `vault-bridge/commands/save-plan-doc.md` | 산출: 각 명령 파일이 자신의 어댑터 귀속(`/save-session`=`session` ③ 딜리버리 row #5 / `/handoff`=`handoff` row #4·vault 비경유)을 명시 + 저작 단계 = 메인컨텍스트 전용(Write Role Contract) 명문화. recipe는 in-place 유지(이전 없음)라 Step 1 로드 경로는 그대로 — ③ 딜리버리 어댑터 구현부임을 라벨링만 추가 | 검증: 각 명령 파일에 vault-searcher 위임 코드가 없음을 grep으로 확인

3. **S3 session-note-recipe.md in-place 라벨링** → 바인딩: `executor` (sonnet) | 대상 파일: `vault-bridge/reference/session-note-recipe.md` | 산출: recipe를 `session` ③ 딜리버리 어댑터 구현부로 in-place 라벨링(G3 #102 ADR 분산·in-place 정합) — **이전·삭제 없음**(삭제 시 `/save-session` 진입점이 dangling). | 검증: grep -r "session-note-recipe" vault-bridge/ 로 참조 유효성 확인 (save-session.md 진입점 링크 유지)

4. **S4 회귀 테스트 풀 실행** → 바인딩: `verifier` (sonnet) | 대상 파일: `vault-bridge/scripts/test/test-*.py`, `vault-bridge/scripts/test/test-*.sh` | 산출: 9개 테스트 전부 exit 0; hook bash -n 전부 통과 | 검증: 아래 E2E 자가검증 명령 블록 전체 실행

5. **S5 버전 범프 + marketplace 동기화** → 바인딩: `executor` (sonnet) | 대상 파일: `vault-bridge/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | 산출: `version` 범프 (minor: 기능적 변경 없음, 명문화·참조 업데이트), description·keywords 동기화 | 검증: `python3 -m json.tool` 양쪽 통과; version·description·keywords 일치 확인

6. **S6 code-review** → 바인딩: `code-reviewer` (sonnet) | 대상 파일: S1-S5 변경 전체 diff | 산출: [CRITICAL] 이슈 없음 확인; Write Role Contract 약화·슬래시 명령 이름 변경·dangling reference 없음 검토 | 검증: reviewer ACCEPT 또는 REVISE 후 재작업

## E2E 자가검증

```bash
# 1. JSON 유효성
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null && echo "plugin.json OK"
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"

# 2. Shell hook syntax
bash -n vault-bridge/hooks/stop-check.sh && echo "stop-check OK"
bash -n vault-bridge/hooks/session-end-pre.sh && echo "session-end-pre OK"
bash -n vault-bridge/hooks/session-start-manifest.sh && echo "session-start-manifest OK"
bash -n vault-bridge/hooks/pre-access-guard.sh && echo "pre-access-guard OK"
bash -n vault-bridge/hooks/pre-write-guard.sh && echo "pre-write-guard OK"

# 3. vault-bridge 회귀 테스트 (9개 전부)
python3 vault-bridge/scripts/test/test-discover.py
python3 vault-bridge/scripts/test/test-manifest-type-optin.py
python3 vault-bridge/scripts/test/test-pre-access-guard.py
python3 vault-bridge/scripts/test/test-pre-write-guard.py
python3 vault-bridge/scripts/test/test-vault-commit-message.py
python3 vault-bridge/scripts/test/test-manifest-promotion.py
python3 vault-bridge/scripts/test/test-vault-path.py
bash vault-bridge/scripts/test/test-stop-check.sh
bash vault-bridge/scripts/test/test-handoff-guard.sh

# 4. 비대칭 명문화 확인
grep -q "read-only\|Write Role Contract\|read only" vault-bridge/agents/vault-searcher.md \
  && echo "vault-searcher read-only marker OK"
grep -q "Write Role Contract\|main.context write\|main context" vault-bridge/.claude-plugin/plugin.json \
  && echo "plugin.json contract marker OK"

# 5. 슬래시 명령 이름 보존 확인 (6개)
for cmd in save-session handoff vault-link vault-manifest-refresh vault-commit save-plan-doc; do
  [ -f "vault-bridge/commands/${cmd}.md" ] && echo "${cmd}.md OK" || echo "MISSING: ${cmd}.md"
done

# 6. dangling reference 없음 (session-note-recipe.md 정리 후)
# S3 완료 후에만 실행
grep -r "session-note-recipe" vault-bridge/commands/ vault-bridge/agents/ 2>/dev/null \
  && echo "WARNING: dangling recipe refs found" || echo "no dangling refs OK"
```

**통과 기준**: 모든 명령 exit 0, `MISSING:` 출력 없음, `FAIL` 출력 없음, `WARNING:` 출력 없음 (S3 완료 후).

## 의존성 / 순서 주의

- **게이트 (해제됨)**: ② 출력 레이어 물리 구조가 G3 #102 ADR(분산·in-place, PR #139 머지)로 확정 → recipe를 이전할 별도 출력 플러그인이 없어요. 그래서 S2·S3는 '이전·정리'가 아니라 in-place ③ 딜리버리 어댑터 라벨링이라 dangling 위험 자체가 없어요. G2(#100)는 CLOSED.
- **wave=3 병렬성**: G4는 G3(출력 레이어 구조)의 ADR 결과에만 논리 의존하고 thinking-tools 코드는 안 건드려요. #102 ADR이 이미 완료라 게이트 풀림.
- **의존 범위**: S1(비대칭 명문화)은 독립 선행. S2·S3는 G3 #102 ADR이 확정한 출력 레이어 분산·in-place 결과에 정합 — recipe를 vault-bridge(③ 딜리버리) 내에 in-place로 라벨링(이전·삭제 없음).
- **breaking change 없음**: 슬래시 명령 이름 보존·Write Role Contract 유지·vault-searcher read-only 유지로 사용자 워크플로우 변경 없어요. major 범프 불필요, minor 범프면 충분해요.
- **크로스청크 게이트**: G2(#100 CLOSED) 머지됨 → G4 PR은 base=main으로 생성 가능. chained PR 불필요.
