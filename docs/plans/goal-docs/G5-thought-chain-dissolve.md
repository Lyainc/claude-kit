---
goal_id: G5
title: thought-chain dissolve (BREAKING)
issues: [105]
wave: 4
depends_on: [G2, G3]
recommended_model: opus
status: gated
created: 2026-06-03
---

# G5 — thought-chain dissolve (BREAKING)

## 배경 / 목적

`thought-chain`은 고정 4단계 파이프라인(unknown-discovery → expert-panel → doc-concretize → doc-polish)을 하드코딩한 오케스트레이션 스킬이에요. 레이어 재설계(`docs/discussions/20260602_claude-kit-layer-redesign/`)에서 합의된 비전은 이 고정 시퀀스를 `/goal` 자율진행의 **슬라이스별 스킬 바인딩**으로 대체하는 거예요. goal-doc의 슬라이스 순서가 thought-chain의 4단계를 supersede하거든요 — goal-doc이 더 일반적이고(임의 스킬 시퀀스), thought-chain은 그 경직된 부분집합이라서요.

핵심은 이게 **조건부 dissolve**라는 점이에요. SUMMARY.md C-3에서 CT(critic) 1인이 "풀 분석 한 방"(discover→debate→concretize→polish를 한 번에) 편의 손실을 우려해서 조건부로만 동의했어요. UNRESOLVED.md U-4가 그 미해결 조건을 명시해요: **goal-doc 레시피가 동등 편의를 입증해야 dissolve 확정**, 미입증 시 thought-chain을 얇은 goal-doc 템플릿 별칭(thin alias)으로 잔존시키는 절충이에요.

그래서 이 goal은 "thought-chain을 무조건 지운다"가 아니라 "편의 동등성(Convenience Test, CT)을 먼저 측정하고, 그 결과에 따라 full removal 또는 thin alias 잔존을 결정한다"예요. breaking change이므로 CHANGELOG 마이그레이션 노트 + major 범프가 필수고요.

이 goal은 G2(goal-doc 포맷·슬라이스 바인딩 스펙)와 G3(doc-concretize/doc-polish 출력 레이어 이동)에 의존해요. goal-doc 포맷이 없으면 후계 레시피를 쓸 수 없고, doc-concretize/doc-polish가 이동하지 않으면 thought-chain이 가리키는 Stage 3·4 링크가 깨지거든요.

## 포함 이슈

- #105: `refactor!: dissolve thought-chain into goal-doc recipe (BREAKING)` — 고정 4단계 thought-chain을 goal-doc 슬라이스-스킬 바인딩이 supersede. CT 편의 동등성 검증 후 제거 또는 thin alias 잔존 결정. CHANGELOG 마이그레이션 노트 + major 범프. deps=#100(G2), #103(G3).

## 완료 조건 (Definition of Done)

**A. Convenience Test (CT) 측정 — dissolve 방식 결정의 전제**
- [ ] thought-chain이 유일하게 제공하던 3대 편의(`thinking-tools/docs/thought-chain-rationale.md` 기준)를 goal-doc 레시피가 동등 제공하는지 항목별로 판정한 CT 결과 문서가 존재한다:
  - (1) Checkpoint UX — 각 단계 후 continue/stop/re-run 확인
  - (2) Partial pipelines — skip/start (이미 있는 산출물로 중간 진입)
  - (3) Inter-stage handoff contract — discovery 발견 → panel 토픽, panel 합의 → concretize 입력
- [ ] CT 판정 결과(PASS = full removal / FAIL = thin alias 잔존)가 이 goal-doc의 "쟁점과 트레이드오프"에 기록되고, 선택된 경로의 슬라이스만 실행된다.

**B-PASS. CT PASS 시 — full removal**
- [ ] `thinking-tools/skills/thought-chain/` 디렉토리 전체 제거(SKILL.md, reference.md, reference/pipeline-examples.md)
- [ ] thought-chain의 4단계 편의를 재현하는 "full analysis" goal-doc 레시피(템플릿)가 `thinking-tools/` 또는 G2 출력 레이어 산출물 안에 존재하고, 마이그레이션 노트가 이를 가리킨다

**B-ALIAS. CT FAIL 시 — thin alias 잔존**
- [ ] `thinking-tools/skills/thought-chain/SKILL.md`가 자체 오케스트레이션 로직(체크포인트·deepen·mid-stop·partial pipeline)을 제거하고, goal-doc "full analysis" 레시피를 호출하는 얇은 별칭(≤ ~40줄)으로 축소된다
- [ ] reference.md / reference/pipeline-examples.md 중 alias에 불필요한 분량은 제거하거나 goal-doc 레시피 문서로 이관한다

**C. 공통 — 참조 정합 + 매니페스트 + 마이그레이션 (양 경로 공통)**
- [ ] `thinking-facilitator.md`의 thought-chain 참조 갱신: skills frontmatter, decision tree(`Comprehensive analysis needed? → thought-chain`), signal-keyword 표, "3+ skills detected → propose thought-chain" 분기 — removal 시 goal-doc 레시피로 라우팅 재작성, alias 시 alias 사양 반영
- [ ] `README.md`(루트 30행), `thinking-tools/README.md`(26행) thought-chain 행 갱신/제거
- [ ] `CLAUDE.md` 11행 "사고 도구 스킬 8개" 카운트 및 스킬 목록 갱신(removal 시 8→7)
- [ ] `telemetry/plugin-map.json` thought-chain 엔트리 갱신/제거
- [ ] `thinking-tools/docs/thought-chain-rationale.md`, `thinking-tools/docs/improvement-matrix.md`(W5행) 갱신 — rationale 문서는 dissolve 결정·CT 결과 반영하도록 재작성하거나 archive로 이동
- [ ] `thinking-tools/.claude-plugin/plugin.json` ↔ `.claude-plugin/marketplace.json` **major 범프**(2.0.0 → 3.0.0), removal 시 `keywords`에서 `thought-chain` 제거, `description` 스킬 카운트(8→7) 동기화 — Version Sync Rule(version·description·keywords 양쪽 동일) 준수
- [ ] `CHANGELOG.md`에 `⚠ BREAKING CHANGES` 섹션 추가 — thought-chain dissolve 사유 + 마이그레이션 경로("기존 thought-chain 호출 → goal-doc full-analysis 레시피로 대체") 명시, 기존 CHANGELOG의 BREAKING 노트 포맷과 일관

**D. 회귀 게이트 (전부 green)**
- [ ] trigger-regression: `check-trigger-regression.py origin/main`에서 removal된 trigger가 의도된 것임을 명시(removal은 hard-gate 아님 — reviewer 확인). CLAUDE.md-mandated trigger(예: expert-panel `다양한 관점에서 평가해줘`)는 절대 미손상
- [ ] JSON 유효성: plugin.json + marketplace.json `python3 -m json.tool` 통과
- [ ] SKILL.md 잔존 파일(alias 경로) frontmatter 유효 — `claude plugin validate`(설치 환경)
- [ ] code-reviewer/verifier 별도 패스 승인 (self-approval 금지)

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| **dissolve 방식** (이 goal의 핵심 게이트) | A) full removal · B) thin alias 잔존 | **CT 측정 결과에 종속** (Leaning A) | C-3·U-4가 명시한 조건부 합의. CT PASS면 A(중복 제거·표면 축소), FAIL이면 B(편의 후퇴 방지). 측정 없이 A를 강행하면 CT dissent를 무시하는 것 |
| **CT 통과 기준** | 3개 편의 전부 동등 / 과반(2/3) / 핵심(handoff contract)만 | **3개 전부 동등 시에만 PASS** | rationale 문서가 "These features would have to be duplicated"라며 3개를 모두 unique value로 명시. 부분 충족은 편의 후퇴 → alias가 안전 |
| **체크포인트 UX 동등성** | goal-doc 슬라이스 경계 = 자연 체크포인트로 충분 / 부족 | **G2 스펙 확인 필요 (Uncertain)** | goal-doc의 슬라이스 순서·E2E 자가검증이 단계 경계를 만들지만, thought-chain의 continue/stop/re-run·3회 deepen cap·friction prompt와 동등한지는 G2 산출물(`/goal` parse/exec 인터페이스)에 달림 |
| **major 범프 폭** | thinking-tools만 / 전체 마켓플레이스 | **thinking-tools plugin + marketplace 엔트리만** | breaking은 thinking-tools 한정. Version Sync Rule은 plugin.json↔marketplace.json 엔트리 동기화만 요구 |
| **alias 잔존 시 trigger 처리** | trigger 유지 / 제거 | **유지(alias 경로)** | alias가 살아있으면 `종합 분석`·`full analysis pipeline` trigger도 살아야 사용자 진입점이 보존됨. trigger-regression이 removal을 잡아줌 |

> **게이트 조건 (status: gated)**: 이 goal은 ① G2 완료(goal-doc 포맷 + 슬라이스-스킬 바인딩 + `/goal` parse/exec 인터페이스 확정) ② G3 완료(doc-concretize/doc-polish 출력 레이어 이동, thought-chain Stage 3·4 링크 대상 이동) ③ S1의 CT 측정 완료 — 이 셋이 충족되기 전엔 S2 이후를 착수하지 않아요. G2 미완 시 "full analysis" 후계 레시피를 작성할 기준 포맷이 없고, G3 미완 시 thought-chain 참조 갱신이 잘못된 경로를 가리키거든요.

## 슬라이스 순서

1. **S1 Convenience Test 측정** → 바인딩: `expert-panel` (또는 메인 컨텍스트 분석) | 대상 파일: 없음(분석 산출), 결과는 이 goal-doc "쟁점과 트레이드오프" + CT 결과 노트에 기록 | 산출: thought-chain 3대 편의(checkpoint·partial·handoff)를 G2 goal-doc 레시피가 동등 제공하는지 항목별 PASS/FAIL 판정 | 검증: 3개 항목 전부 판정됨 + dissolve 경로(removal vs alias) 결정됨. **이 슬라이스 결과가 S2의 분기를 결정**

2. **S2 후계 레시피 작성** → 바인딩: `doc-concretize` (이동 후 출력 레이어 위치) | 대상 파일: `thinking-tools/`의 "full-analysis" goal-doc 레시피/템플릿(G2 포맷 준수) | 산출: discover→debate→concretize→polish를 goal-doc 슬라이스 순서로 재현하는 레시피 — CHANGELOG 마이그레이션 노트가 가리킬 대상 | 검증: G2 goal-doc 스키마(완료조건·쟁점·슬라이스 순서·E2E 자가검증) 준수, 4개 스킬 바인딩 명시

3. **S3-PASS 또는 S3-ALIAS (S1 결과에 따라 택1)** → 바인딩: `executor` |
   - **S3-PASS** (CT PASS): 대상 파일: `thinking-tools/skills/thought-chain/` 전체 삭제 | 산출: 디렉토리 제거 | 검증: 경로 부재 확인
   - **S3-ALIAS** (CT FAIL): 대상 파일: `thinking-tools/skills/thought-chain/SKILL.md`(thin alias로 축소), `reference.md`·`reference/pipeline-examples.md`(잉여분 정리) | 산출: goal-doc 레시피 호출 별칭 | 검증: 오케스트레이션 로직 제거 확인, frontmatter 유효

4. **S4 참조 정합 갱신** → 바인딩: `executor` | 대상 파일: `thinking-tools/agents/thinking-facilitator.md`, `README.md`, `thinking-tools/README.md`, `CLAUDE.md`, `telemetry/plugin-map.json`, `thinking-tools/docs/thought-chain-rationale.md`, `thinking-tools/docs/improvement-matrix.md` | 산출: 모든 thought-chain 참조가 선택된 경로(removal→레시피 라우팅 / alias→별칭)와 일관 | 검증: `grep -rIn "thought-chain"`로 잔존 참조가 전부 의도된 것인지 확인

5. **S5 매니페스트 major 범프 + 동기화** → 바인딩: `executor` | 대상 파일: `thinking-tools/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | 산출: version 2.0.0→3.0.0, removal 시 keywords에서 thought-chain 제거 + description 카운트 동기화 | 검증: Version Sync Rule(version·description·keywords 양쪽 동일) + JSON valid

6. **S6 CHANGELOG 마이그레이션 노트** → 바인딩: `doc-concretize` 또는 `executor` | 대상 파일: `CHANGELOG.md` | 산출: `⚠ BREAKING CHANGES` 섹션 — dissolve 사유 + 마이그레이션 경로(thought-chain → goal-doc full-analysis 레시피) | 검증: 기존 CHANGELOG BREAKING 노트 포맷과 일관, 마이그레이션 경로가 S2 레시피를 정확히 가리킴

7. **S7 회귀 게이트 + 리뷰** → 바인딩: `verifier` + `code-reviewer` | 대상 파일: 없음(검증) | 산출: 아래 E2E 자가검증 전부 green + 별도 리뷰 패스 승인 | 검증: trigger-regression diff 확인(removal 의도성), JSON valid, CLAUDE.md-mandated trigger 보존, self-approval 금지

## E2E 자가검증

```bash
# 1. JSON 유효성 (major 범프 후)
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "plugin.json OK"
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"

# 2. Version Sync Rule — plugin.json과 marketplace 엔트리의 version·description·keywords 일치 확인
python3 - <<'PY'
import json
p = json.load(open("thinking-tools/.claude-plugin/plugin.json"))
m = next(x for x in json.load(open(".claude-plugin/marketplace.json"))["plugins"] if x["name"]=="thinking-tools")
assert p["version"] == m["version"] == "3.0.0", (p["version"], m["version"])
assert p["description"] == m["description"]
assert p["keywords"] == m["keywords"]
print("version sync OK:", p["version"])
PY

# 3. trigger-regression — self-test 먼저, 그 다음 origin/main 대비 diff
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 9 self-test cases passed
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# removal 경로: thought-chain trigger(종합 분석, 전체 파이프라인 등) 제거가 보고됨 — 의도된 것이므로 reviewer가 ack.
# CLAUDE.md-mandated trigger(expert-panel "다양한 관점에서 평가해줘")는 절대 미손상이어야 함.

# 4. 잔존 참조 전수 확인 — 갱신 안 된 thought-chain 참조가 없는지
grep -rIn "thought-chain" --include="*.md" --include="*.json" --include="*.py" . | grep -v "docs/discussions/" | grep -v "docs/plans/" | grep -v "CHANGELOG.md"
# removal 경로: 위 출력에 코드/매니페스트/라우팅 참조가 남으면 미완. (discussions/plans/CHANGELOG는 역사 기록이므로 제외)
# alias 경로: skills/thought-chain/ + facilitator alias 참조만 남아야 함.

# 5. removal 경로 한정 — 디렉토리 부재 확인
test ! -d thinking-tools/skills/thought-chain && echo "thought-chain removed" || echo "thought-chain dir still present (alias path expects this)"

# 6. SKILL.md frontmatter 유효성 (설치 환경에서)
# claude plugin validate

# 7. 다른 스킬 회귀 없음 — 스킬 파일 카운트 (removal 시 8→7)
find thinking-tools/skills -name "SKILL.md" | sort
```

- **통과 기준**:
  - JSON 둘 다 OK, Version Sync 스크립트 `version sync OK: 3.0.0` 출력
  - trigger-regression self-test 9/9 통과, origin/main diff에서 thought-chain trigger removal만 보고되고 expert-panel `다양한 관점에서 평가해줘` 등 mandated trigger는 미손상
  - grep 전수 확인에서 갱신 누락된 코드/매니페스트/라우팅 참조 0건 (역사 기록 제외)
  - removal 경로: `thought-chain removed` + SKILL.md 7개 / alias 경로: SKILL.md 8개 유지 + thought-chain SKILL.md가 thin alias
  - CHANGELOG `⚠ BREAKING CHANGES` 섹션이 마이그레이션 경로(goal-doc full-analysis 레시피)를 정확히 가리킴
  - code-reviewer/verifier 별도 패스 승인 (동일 active context self-approval 금지)

## 의존성 / 순서 주의

- **선행 goal (hard deps)**:
  - **G2 (#100, LINCHPIN)**: goal-doc 포맷 + 슬라이스-스킬 바인딩 표기법 + `/goal` parse/exec 인터페이스. 이게 확정돼야 S1 CT 측정의 기준(체크포인트·partial·handoff를 goal-doc이 어떻게 표현하는가)과 S2 후계 레시피의 포맷이 정해져요. UNRESOLVED.md가 U-3을 "최우선 — thought-chain 전부 여기 의존"으로 명시.
  - **G3 (#103)**: doc-concretize/doc-polish가 출력 레이어로 이동. thought-chain Stage 3(doc-concretize)·Stage 4(doc-polish) 링크 대상이 이동하므로, S2 레시피와 S4 참조 갱신이 새 경로를 가리켜야 해요. G3 미완 시 깨진 링크를 만들게 돼요.
- **크로스청크 게이트**: status=gated. S1(CT 측정) 완료 전엔 S3 이후(실제 dissolve)를 착수하지 않아요 — S1 결과가 removal/alias 분기를 결정하므로 순서 역전 금지.
- **착수 조건**: G2·G3 머지 + origin/main 갱신 후 시작. trigger-regression diff가 origin/main 기준이므로, 시작 전 `git fetch origin`으로 base를 최신화하세요.
- **breaking change 주의**: major 범프(2.0.0→3.0.0)는 thinking-tools 사용자에게 영향. CHANGELOG 마이그레이션 노트가 기존 호출자(`종합 분석`·full pipeline 트리거 사용자)에게 goal-doc 레시피 대체 경로를 명확히 안내해야 해요.
- **PR 관례**: 커밋 영어 Conventional Commits(`refactor!:` 또는 `feat!:` — breaking), PR 설명 한국어, 재설계 spec(`docs/discussions/20260602_claude-kit-layer-redesign/SUMMARY.md` C-3, UNRESOLVED.md U-4) 참조.
