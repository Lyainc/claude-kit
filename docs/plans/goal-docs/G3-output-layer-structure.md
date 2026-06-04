---
goal_id: G3
title: 출력 레이어 물리 구조 결정·실행
issues: [102, 103, 124]
wave: 3
depends_on: [G2]
recommended_model: opus
status: ready
created: 2026-06-03
---

# G3 — 출력 레이어 물리 구조 결정·실행

## 배경 / 목적

claude-kit 레이어 재설계(2026-06-02 전문가 패널, `docs/discussions/20260602_claude-kit-layer-redesign/`)에서 ②(결정화·출력) 레이어를 분리하기로 합의했어요. 근데 **이게 새 물리 플러그인이 되어야 하는지, 아니면 논리적 계약(분산)으로만 남는지**가 미결(U-2 = #102)이고, 그 결정이 doc-concretize/doc-polish의 행선지(U-1 = #103)와 diverse-sampling Mode B의 크로스플러그인 호출 경로(#124)를 줄줄이 게이트하고 있어요.

이 묶음의 응집 근거는 **단일 결정의 폭포 효과**예요. #102 ADR이 출력 레이어의 물리 형태를 정하면 → #103이 그 형태대로 concretize/polish를 배치하고 → #124가 #103 이후 확정된 경로로 Mode B 하위호출을 연결해요. 세 이슈는 의존 사슬(#102 → #103 → #124)이라 한 goal-doc에서 순차 실행해야 중간 상태가 일관돼요.

**핵심 잠정 판단** (SUMMARY C-5 + UNRESOLVED U-2): 출력 레이어 = **논리적 계약(분산)** 우세. graphify(글로벌 스킬)·OVM note·spec-first goal-doc이 이미 각자 위치에 있어서, 새 단일 플러그인은 중복 + 이동 비용만 늘려요. thin 2-스킬 "doc-tools" 플러그인 신설은 SUMMARY C-2에서 명시 금지됐고요.

## 포함 이슈

- #102: decide: output layer = single plugin vs distributed (U-2) — 단일 신설 플러그인 vs 논리적 계약(분산) ADR 기록. doc-concretize/polish 행선지(#103)의 게이트.
- #103: refactor: relocate doc-concretize/doc-polish to output layer — #102 결정 후 비대칭 반영(concretize=구조화 저작 인지 코어 보존, polish=md 린트). thought-chain 파이프라인 ref 갱신 + 매니페스트 동기화 + trigger-regression green.
- #124: refactor(diverse-sampling): add Mode B enhance with doc-concretize subcall — Mode A(현행 VS 탐색 유지) + Mode B(enhance — mode collapse 회피 작성 엔진, doc-concretize 하위호출, factual 단답 제외). Mode B 호출 경로는 #103 행선지 확정 후 결정.

## 완료 조건 (Definition of Done)

**#102 — ADR** (완료 2026-06-04, PR #139 — `docs/design/output-layer-structure-adr.md`)
- [x] `docs/design/output-layer-structure-adr.md` 작성: 단일 플러그인 vs 분산 결정 + 근거. → **분산(논리 계약)** 채택.
- [x] 결정에 다음 근거를 명시: (a) graphify/OVM note/spec-first goal-doc이 이미 분산 자산이라는 사실, (b) thin 2-스킬 플러그인 금지 제약(SUMMARY C-2), (c) concretize=인지 코어 / polish=린트 비대칭, (d) 이동 비용 vs 응집 가치 트레이드오프. (load-bearing 근거=C-2, ADR §2)
- [x] ADR이 #103의 concretize/polish 행선지를 **명시적으로 지정**(어느 플러그인/디렉토리에 안착하는지)해야 #103 게이트가 풀림. → **in-place reframe(thinking-tools 잔류)**, ADR §2.5.
- [x] ADR을 `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md`의 U-2/U-1 항목에서 참조하도록 링크 갱신(또는 RESOLVED 표시). → U-2/U-1 RESOLVED 표기 완료.

**#103 — concretize/polish 배치** (Acceptance: 스킬 이동 + thought-chain 링크 유효 + trigger-regression green + 매니페스트 동기화)
- [ ] #102 ADR이 지정한 행선지대로 doc-concretize/doc-polish 배치(이동 또는 in-place reframe). concretize의 재귀적 구체화 인지 코어는 보존, polish는 md 린트로 역할 명확화.
- [ ] thought-chain 파이프라인 ref 전부 유효: `thinking-tools/skills/thought-chain/SKILL.md`의 doc-concretize/doc-polish 상대경로 링크(현재 line 195의 `../doc-concretize/SKILL.md`, `../doc-polish/SKILL.md` 등)가 새 위치를 가리켜 깨지지 않음.
- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` → "no trigger removals" (exit 0). 행선지가 다른 플러그인이면 해당 플러그인의 trigger도 동일 검증.
- [ ] 매니페스트 동기화(Version Sync Rule): 영향받는 `plugin.json`↔`marketplace.json`의 version/description/keywords 일치. concretize/polish가 thinking-tools를 떠나면 thinking-tools keywords에서 제거 + 스킬 카운트(현재 "8 skills") 갱신, 목적지 플러그인 keywords에 추가.
- [ ] `python3 -m json.tool` 로 영향받는 모든 plugin.json + marketplace.json 유효성 통과.
- [ ] README 갱신: 루트 `README.md` line 26-27, `thinking-tools/README.md` line 22-23의 doc-concretize/doc-polish 항목이 새 위치를 반영(이동 시).

**#124 — diverse-sampling Mode A/B** (Acceptance: 5개 항목)
- [ ] Mode A(Explore): 기존 VS 워크플로 회귀 없음 — trigger-regression green.
- [ ] Mode B(Enhance): `thinking-tools/skills/diverse-sampling/SKILL.md`에 doc-concretize 하위호출 경로 명시 + factual 단답 제외 조건 동작. 하위호출 경로는 #103 행선지 확정값 사용.
- [ ] SKILL.md frontmatter `description` 업데이트: Mode A/B 구분 + Mode B 트리거 문자열("글로 발전시켜줘", "더 구체적으로 작성해줘", "enhance", "작성 다양성") 포함.
- [ ] SKILL.md 본문 수정: `Invocation Detection`에 Mode B 트리거 섹션, `Core Workflow` Phase 0에 Mode 판별 스텝, `Use Case Boundaries`에 Mode별 적용 범위, `Tool Usage`에 doc-concretize 하위호출 명시.
- [ ] diverse-sampling `allowed-tools`에 `Skill` 추가(현재 `AskUserQuestion`만 있어서 하위호출 불가).
- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` green — 새 Mode B 트리거 추가는 removal이 아니므로 통과해야 함. self-test도 green: `python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test` → "all 9 self-test cases passed".
- [ ] **(#124 Acceptance 5)** Mode B doc-concretize 하위호출 경로가 S2(#103)에서 확정된 행선지를 가리키고 placeholder/TODO/`<경로>` 잔존이 없음 — #103 머지 후 경로 업데이트 완료. (S3 E2E grep으로 독립 검증, 아래 E2E 5b)

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| #102: 출력 레이어 물리 형태 | (a) 새 단일 플러그인 / (b) 논리적 계약=분산 | **(b) 분산** | graphify·OVM note·spec-first goal-doc이 이미 분산 자산. 새 플러그인은 중복+이동 비용. thin 2-스킬 플러그인 금지(C-2). SUMMARY C-5 만장일치 "신설 최소화". |
| #103: concretize/polish 행선지 (U-1, **#102 ADR이 확정해야 풀리는 게이트**) | (a) in-place reframe(thinking-tools 잔류, 역할만 재정의) / (b) 분산 이동(concretize→출력저작, polish→lint 표면) / (c) OVM fold | **(a) in-place reframe leaning** | 분산이 "논리적 계약"이면 물리 이동 불필요 — 출력 어댑터 계약을 만족하면 위치는 thinking-tools여도 됨. 이동은 thought-chain 링크·매니페스트·README 표면을 다 건드려 회귀 위험↑, 가치↓. 단 ADR이 이동을 지정하면 (b) 따름. polish의 OVM fold는 도메인 불일치(U-1) 우려. |
| #103: 비대칭 처리 | concretize/polish를 같은 칸에 vs 갈라서 | **갈라서** | C-2 비대칭 확정: concretize=구조화 저작(인지 코어), polish=순수 md 린트. 페어링 깨짐 비용은 있으나 한 칸 근거 약함(U-1). |
| #124: Mode B 크로스플러그인 호출 | #103이 (a) in-place면 intra-plugin 호출 / (b) 이동이면 cross-plugin 호출 | **#103 결과 종속** | #103이 in-place reframe이면 diverse-sampling→doc-concretize는 thinking-tools 내부 Skill 호출이라 #124의 "크로스플러그인 의존" 우려가 소멸. 이동이면 cross-plugin 경로로 명시. → **#124는 #103 머지 후 경로 확정**(이슈 본문 Deps 명시). |
| #124: Mode B 적용 경계 | 전 작성 태스크 vs factual 제외 | **factual 단답 제외** | mode collapse 회피는 창의·개방형 작성에서만 가치. factual 질문·단답은 Mode A의 Use Case Boundaries Exclude 목록과 동일 원칙 재사용. |

**게이트 조건 요약**: #103은 #102 ADR이 행선지를 명시하기 전엔 착수 불가. #124 Mode B 하위호출 경로 라인은 #103 머지 전엔 placeholder, 머지 후 실제 경로로 확정. 순서 위반 시 thought-chain 링크가 중간 상태에서 깨지거나 #124가 잘못된 경로를 박제할 위험.

## 슬라이스 순서

1. **S1 #102 ADR 작성** → 바인딩: `expert-panel`(트레이드오프 정리) → `doc-concretize`(ADR 본문 저작) → `doc-polish`(린트) | 대상 파일: `docs/design/output-layer-structure-adr.md` (신규), `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md`(U-2/U-1 RESOLVED 링크) | 산출: 단일 vs 분산 결정 + 근거 + concretize/polish 행선지 명시 | 검증: ADR이 #103 행선지를 1곳으로 확정했는지 리뷰(`code-reviewer`).

2. **S2 #103 concretize/polish 배치** → 바인딩: `executor`(파일 이동/reframe + 매니페스트 동기화 + 링크 갱신), 검증 `code-reviewer` | 대상 파일: ADR 지정 행선지에 따라 — `thinking-tools/skills/doc-concretize/`, `thinking-tools/skills/doc-polish/`(in-place면 SKILL.md description reframe만; 이동이면 디렉토리 + `thinking-tools/.claude-plugin/plugin.json` keywords + `.claude-plugin/marketplace.json` + `thinking-tools/skills/thought-chain/SKILL.md` 링크(line 6,39,76,80,85,90,126-127,149-150,162-167,187-189,195) + `README.md`(L26-27) + `thinking-tools/README.md`(L22-23)) | 산출: 배치 완료 + thought-chain 링크 유효 + 매니페스트 동기 | 검증: S2 자가검증 블록(trigger-regression + json.tool + 링크 grep).

3. **S3 #124 diverse-sampling Mode A/B** → 바인딩: `executor`(SKILL.md 수정), 검증 `code-reviewer` + `verifier` | 대상 파일: `thinking-tools/skills/diverse-sampling/SKILL.md`(frontmatter description + allowed-tools에 Skill 추가 + Invocation Detection Mode B + Core Workflow Phase 0 Mode 판별 + Use Case Boundaries Mode별 + Tool Usage doc-concretize 하위호출), 필요시 `reference.md`/`examples.md` | 산출: Mode A 회귀 없음 + Mode B 하위호출 경로(=S2 확정 경로) + factual 제외 | 검증: S3 자가검증 블록(trigger-regression self-test + origin/main).

4. **S4 통합 검증·매니페스트 최종 동기** → 바인딩: `verifier` | 대상 파일: 변경된 모든 plugin.json/marketplace.json/README | 산출: 전체 green | 검증: E2E 자가검증 블록 전부 실행.

## E2E 자가검증

```bash
# 1. trigger-regression (self-test + origin/main diff) — #103 + #124 공통
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# 기대: OK: all 9 self-test cases passed
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# 기대: RESULT: no trigger removals. (exit 0)

# 2. 매니페스트 JSON 유효성 (이동 시 영향받는 모든 파일)
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "thinking-tools plugin.json OK"
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"

# 3. Version Sync 확인 — plugin.json ↔ marketplace.json version/description/keywords 일치
python3 - <<'PY'
import json
p = json.load(open('thinking-tools/.claude-plugin/plugin.json'))
m = next(x for x in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if x['name']=='thinking-tools')
assert p['version']==m['version'], f"version mismatch {p['version']} vs {m['version']}"
assert p['description']==m['description'], "description mismatch"
assert p['keywords']==m['keywords'], "keywords mismatch"
print("version sync OK:", p['version'])
PY

# 4. thought-chain 링크 무결성 — concretize/polish 참조 경로가 실재하는지
python3 - <<'PY'
import os, re
sk = 'thinking-tools/skills/thought-chain/SKILL.md'
base = os.path.dirname(sk)
txt = open(sk).read()
broken = []
for rel in re.findall(r'\]\((\.\.[^)]+SKILL\.md)\)', txt):
    if not os.path.exists(os.path.normpath(os.path.join(base, rel))):
        broken.append(rel)
print("broken thought-chain links:", broken or "NONE")
assert not broken, "thought-chain has broken concretize/polish links"
PY

# 5. diverse-sampling Mode B 게이트 확인 (#124)
grep -q "Skill" thinking-tools/skills/diverse-sampling/SKILL.md && echo "Skill in diverse-sampling: present" || echo "WARN: Skill tool not yet added"
grep -iq "Mode B\|enhance" thinking-tools/skills/diverse-sampling/SKILL.md && echo "Mode B section: present" || echo "WARN: Mode B not yet added"

# 5b. Mode B 하위호출 경로 확정 확인 (#124 Acceptance 5 — #103 머지 후 placeholder 미잔존)
grep -nE 'placeholder|TODO|FIXME|<경로>' thinking-tools/skills/diverse-sampling/SKILL.md && echo "WARN: Mode B 경로 placeholder 잔존 — #103 행선지로 갱신 필요" || echo "Mode B 하위호출 경로 확정됨 (path-confirmed)"

# 6. ADR 존재 + 행선지 명시 (#102 게이트)
test -f docs/design/output-layer-structure-adr.md && echo "ADR present" || echo "WARN: ADR missing"

# 7. (claude plugin validate 가능 환경이면) 전체 스펙 검증
# claude plugin validate
```

- 통과 기준: (1) self-test 9 cases pass + no trigger removals, (2) 모든 JSON 유효, (3) version sync 3필드 일치, (4) thought-chain broken links = NONE, (5) #124 적용 후 Skill tool + Mode B 섹션 present + Mode B 하위호출 경로 path-confirmed(placeholder 미잔존), (6) #102 적용 후 ADR present + 행선지 1곳 확정. 하나라도 실패 시 해당 슬라이스로 돌아가 반복.

## 의존성 / 순서 주의

- **선행 goal**: G2(depends_on). G2 산출물(출력 어댑터 계약/매핑표 등)이 #102 ADR의 "분산이 어떤 계약으로 묶이나"의 입력이에요. G2 미완 시 ADR 근거가 비어요.
- **청크 내부 순서(엄격)**: #102 ADR → #103 배치 → #124 Mode B. 역순·병렬 금지.
  - #103은 #102 ADR이 행선지를 1곳으로 명시하기 **전엔 착수 불가**(게이트). ADR이 "in-place reframe"이면 #103은 description reframe만, "이동"이면 디렉토리+매니페스트+링크 전체.
  - #124 Mode B의 doc-concretize 하위호출 경로 라인은 #103 머지 **후** 확정값으로 작성. #103 전엔 placeholder. (이슈 #124 본문 Deps: "#103 머지 후 경로 업데이트 확인" 명시.)
- **크로스청크 게이트**: thought-chain 전면 해체(dissolve, SUMMARY A7)는 이 G3 범위 **밖**. 여기선 링크 유효성만 유지하고 dissolve는 별도 goal(U-3 goal-doc 스펙 + U-4 편의 손실 입증 선행)에서 처리해요. G3에서 thought-chain을 건드리는 범위는 concretize/polish 경로 ref 갱신으로 한정.
- **착수 조건**: G2 머지 + `origin/main` 최신 fetch(trigger-regression 비교 기준). 시작 전 `git fetch origin main` 권장.
- **회귀 안전망**: 각 슬라이스 후 trigger-regression을 돌려 트리거 누락을 조기 포착. CLAUDE.md 명시 — "char-count check does NOT catch dropped triggers; ALWAYS run trigger-regression when slimming descriptions." description을 만질 때(특히 S2 reframe, S3 Mode B) 반드시 실행.
