---
goal_id: G2
title: goal-doc 스펙 + 출력 어댑터 계약 + spec-first reconcile
issues: [100, 101, 111]
wave: 2
depends_on: [G1]
recommended_model: opus
status: gated
created: 2026-06-03
---

# G2 — goal-doc 스펙 + 출력 어댑터 계약 + spec-first reconcile

## 배경 / 목적

이 묶음은 레이어 재설계의 **linchpin**이에요. `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md`의 U-3가 "재설계의 가장 큰 미지수"로 명시돼 있고, 미해결 우선순위 1번이거든요. thought-chain dissolve(#105), ② 출력 레이어 조립(#103/#104), OMC↔claude-kit glue가 전부 여기에 의존해요.

세 이슈를 하나로 묶는 응집 근거:

- **#100**(goal-doc 스키마 + 슬라이스-스킬 바인딩 + parse/exec 인터페이스)이 정의하는 "슬라이스가 스킬을 호출한다"는 표기법은, **#101**(출력 어댑터 계약)이 정의하는 "어떤 출력 스킬이든 균일하게 호출하는 인터페이스" 없이는 공허해요. 바인딩 표기법과 그 표기법이 가리키는 호출 계약은 같은 설계의 앞뒷면이거든요.
- **#111**(spec-first reconcile)의 핵심 결정 — spec-first를 goal-doc 출력 스킬(②)로 재프레임할지 — 은 #100의 출력 매핑(`goal-doc=spec-first`)과 #101의 어댑터 매핑에 직접 박혀요. spec-first의 정체성·명명·포지셔닝을 여기서 못박지 않으면 #100/#101 매핑표에 빈칸이 생겨요.

가치의 핵심은 SUMMARY.md C-5가 말하듯 **신규 스킬이 아니라 균일한 출력 어댑터 계약**이에요. net-new는 ≤2개(아마 issue-authoring 정도)로 최소화하고, 나머지는 전부 기존 자산을 *조립*하는 계약을 쓰는 거예요.

**메타 (dogfooding)**: 지금 작성 중인 이 goal-doc 자체가 #100 스키마의 첫 레퍼런스 구현이에요. 작성하면서 발견한 유용한/불필요한 필드는 #100 스펙 권고에 그대로 반영해야 해요(아래 S1 참조).

## 포함 이슈

- **#100**: design: goal-doc format + slice-skill binding spec (LINCHPIN) — goal-doc 스키마(완료조건·쟁점/트레이드오프·슬라이스 순서·E2E 자가검증) + 슬라이스→스킬 바인딩 표기법 + parse/exec 인터페이스(OMC `/goal` vs claude-kit) 설계.
- **#101**: design: output-adapter contract + existing output-skill mapping — goal-doc 슬라이스가 어떤 출력 스킬이든 균일 호출하는 어댑터 계약 + 포맷×동작 매트릭스 + net-new gap(≤2) 식별.
- **#111**: reconcile: spec-first extraction open items vs layer redesign — spec-first 미해결 4건(명명·유사도구 웹검증·인터뷰 엔진 중복·플러그인 구조 실행)을 #100/#102에 명시 배정하거나 해소.

## 완료 조건 (Definition of Done)

#100 (Acceptance: "스키마 + 바인딩 표기 + parse/exec 인터페이스 결정된 spec doc"):
- [ ] goal-doc **스키마** spec doc 작성 — frontmatter 필드(goal_id, title, issues, wave, depends_on, recommended_model, status, created) + 본문 섹션 5종(배경/목적, 완료조건, 쟁점/트레이드오프, 슬라이스 순서, E2E 자가검증)의 의미·필수성·작성 규칙을 못박음.
- [ ] **슬라이스→스킬 바인딩 표기법** 확정 — 각 슬라이스가 `바인딩: <skill/agent>` 형태로 실행 주체를 명시하는 표기 규칙 + 기본 바인딩(spec-impl-critique / debug 등) 정의.
- [ ] **parse/exec 인터페이스** 결정 — 누가 goal-doc을 파싱·실행하는지(OMC `/goal` vs claude-kit) 명문화. 근거: Claude Code `/goal`은 session-scoped Stop hook이고 셸에서 mutate 불가 → 실행 주체는 in-session 액티브 에이전트, claude-kit은 goal-doc을 *생성*만 하는 leaf capability(경계 A 정합).
- [ ] 이 G2 goal-doc 자체를 dogfooding 레퍼런스로 인용하고, 작성 중 발견한 필드/패턴(예: `status: gated`의 게이트 표기, 쟁점 표의 backlog 처리)을 스펙 권고에 반영.

#101 (Acceptance: "계약 doc + 포맷×동작 매트릭스 + net-new gap 목록"):
- [ ] **출력 어댑터 계약 doc** 작성 — 슬라이스가 출력 스킬을 호출하는 균일 인터페이스(입력 계약: intent/format/payload/destination; 출력 계약: artifact path + 상태) 정의.
- [ ] **포맷×동작 매트릭스** 작성 — 매핑 확정: html=graphify, note=OVM note, goal-doc=spec-first, handoff=`/handoff`, session=`/save-session`, md저작=doc-concretize, md편집=doc-polish, issue=gh CLI.
- [ ] **net-new gap 목록**(≤2) 식별 — 기존 자산으로 못 채우는 출력만 골라냄(유력: issue-authoring). 신규 스킬 신설을 최소화한다는 C-5 만장일치 합의 준수.

#111 (Acceptance: "미해결 1~3 각각 해소 또는 #100/#102 배정 + 4는 standalone 시 실행 명시 / 분산·흡수 시 폐기 기록"):
- [ ] 미해결 **1 (명명)**: spec-first → build-spec 등 명명 결정 또는 #100(포지셔닝)/#102(구조)에 명시 배정.
- [ ] 미해결 **2 (유사도구 웹검증)**: spec-kit(GitHub)·Kiro(AWS)·ouroboros 대비 차별점 재검증(2025-08 cutoff 이후 변화 반영) 또는 명시 배정. 웹검증은 deep-research/document-specialist로 위임.
- [ ] 미해결 **3 (인터뷰 엔진 중복)**: unknown-discovery와 Socratic 로직 공통 추출 여부 결정 또는 #100/#102 배정.
- [ ] 미해결 **4 (플러그인 구조 실행)**: #102 결정에 게이트됨 — standalone 확정 시 실행 단계(plugin.json·marketplace.json 등록, 디렉토리, 버전 동기화) 명시 / 분산·흡수 결정 시 **명시적 폐기 기록**.

문서 무결성 (claude-kit Validation 섹션 기준 — 코드 변경 없는 설계 묶음이라 회귀 게이트가 핵심):
- [ ] spec-first SKILL.md description을 건드린 경우 trigger 회귀 없음: `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` (제거된 trigger가 의도적인지 리뷰어 확인).
- [ ] plugin.json/marketplace.json을 건드린 경우(미해결 4 standalone 실행 시) JSON 유효성 + version/description/keywords 3필드 동기화.

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| parse/exec 주체 (#100) | (a) OMC `/goal`이 파싱·실행 (b) claude-kit이 자체 실행 엔진 보유 | **(a)** | `/goal`은 session-scoped Stop hook — 셸에서 mutate 불가, 실행은 in-session 액티브 에이전트만 가능(ultragoal SKILL `Important_Limitations` 확인). 경계 A(claude-kit=leaf capability, OMC=⑤실행)와 정합. claude-kit이 실행 엔진을 가지면 OMC ⑤ 중복 + 버전 동기화 표면 폭발(C-1이 옵션 B를 기각한 바로 그 이유). |
| 출력 레이어 물리 구조 (#101↔#102) | (a) 단일 플러그인 (b) 논리적 계약(분산) | **(b) 잠정 — #102 게이트** | graphify·OVM·spec-first가 이미 각자 플러그인. 단일 신설은 중복+이동 비용(U-2 잠정 우세=분산). G2는 "논리적 계약(어댑터 인터페이스)"을 설계하되 물리 구조 확정은 #102(G3 wave)로 넘김. **#101 Acceptance는 #102 결정 없이도 충족 가능**(계약은 구조 독립적). |
| spec-first 명명/포지셔닝 (#111-1) | (a) build-spec로 개명 (b) 현 이름 유지 (c) goal-doc 출력 스킬로 흡수 | **결정 게이트 — #100/#102에 배정** | "spec-first"는 방법론 이름이라 동작·시점이 불명(#111-1 원문). 재설계에서 spec-first=goal-doc 출력 스킬(②). 명명 자체는 #100 포지셔닝 결정의 하류 — G2에서 "②의 goal-doc 산출 어댑터로 포지셔닝" 결정을 내리고, 물리적 개명/이동은 #102 결과에 게이트. |
| net-new 출력 스킬 개수 (#101) | (a) 0개(전부 조립) (b) 1~2개(issue-authoring 등) | **(b) ≤2, issue-authoring 후보** | C-5 만장일치 = "신설 최소화". gh CLI 매핑이 있으나 issue 본문 *저작*(템플릿·라벨·중복검출)은 빈틈. 단 net-new는 gap이 입증될 때만 — 무근거 신설 금지. |
| spec-first 분리 실행 시점 (#111-4) | (a) 지금 실행 (b) #102 결정까지 보류 | **(b) 보류** | #102가 "분산/흡수"로 결정하면 별도 플러그인 신설은 껍데기 → 폐기. 지금 분리하면 #102가 흡수 결정 시 되돌려야 함. G2는 폐기/실행 **조건**만 기록. |
| consensus 게이트 (메타) | (a) ralplan consensus 통과 후 실행 (b) 바로 실행 | **(a) — status: gated** | #100이 명시적으로 "ralplan consensus 게이트 권장". 이 goal-doc의 `status: gated`가 그 표식. linchpin이라 잘못된 스키마 결정이 하류 5개 청크를 오염시키므로 합의 게이트가 비용보다 이득. |

## 슬라이스 순서

1. **S1 dogfooding 스키마 추출** → 바인딩: 직접(메인 컨텍스트, 본 G2 작성 경험) | 대상 파일: (분석만, 산출은 S2) | 산출: 이 G2 goal-doc 작성 중 실제로 쓴 frontmatter 필드 + 본문 섹션 + `status: gated` 게이트 표기 + 쟁점 표의 backlog/게이트 처리 패턴의 목록 | 검증: 각 필드가 하류 실행에 실제 필요한지(없으면 정보 손실?) 자문. dogfooding이라 별도 도구 불필요.

2. **S2 goal-doc 스키마 spec doc 저작** → 바인딩: doc-concretize (구조화 저작) | 대상 파일: `docs/design/goal-doc-spec.md` (신규) | 산출: frontmatter 8필드 + 본문 5섹션 스키마 정의 + 슬라이스→스킬 바인딩 표기법 + 기본 바인딩 카탈로그 + parse/exec 인터페이스(주체=OMC `/goal`, claude-kit=생성 leaf) | 검증: S1 dogfooding 필드 전부 반영됐는지 체크리스트.

3. **S3 출력 어댑터 계약 + 매핑표 저작** → 바인딩: doc-concretize | 대상 파일: `docs/design/output-adapter-contract.md` (신규) | 산출: 균일 호출 인터페이스(intent/format/payload/destination → artifact path + status) + 포맷×동작 매트릭스(8매핑) + net-new gap 목록(≤2) | 검증: 8개 매핑이 전부 기존 자산(graphify/OVM note/spec-first/`/handoff`/`/save-session`/doc-concretize/doc-polish/gh)을 가리키는지 + gap이 ≤2개인지.

4. **S4 spec-first reconcile 결정 기록** → 바인딩: 직접(설계 결정) + 웹검증은 deep-research/document-specialist 위임 | 대상 파일: `docs/plans/spec-first-extraction-2026-06-02.md` (미해결 4건 갱신) + `docs/design/goal-doc-spec.md`(포지셔닝 반영) | 산출: 미해결 1~3 각각 해소/배정 + 4의 폐기/실행 조건 명문화 (#111 §2 웹검증은 spec-kit/Kiro 최신 비교) | 검증: #111 Acceptance 4항목 전부 체크 — 1~3 해소 또는 배정, 4 조건부 기록.

5. **S5 쟁점 검증 (선택, 게이트 전)** → 바인딩: expert-panel (다관점 평가) 또는 adversarial-review (parse/exec 결정 1:1 공격) | 대상 파일: (검토만) | 산출: parse/exec 주체 결정·출력 구조 분산 결정의 생존 여부 판정 | 검증: 합의 게이트 입력. linchpin이라 권장하나 시간 제약 시 ralplan consensus로 대체 가능.

6. **S6 설계 doc 품질 패스 + 회귀 게이트** → 바인딩: doc-polish (md 린트) + code-reviewer (설계 정합성) + verifier (회귀 명령 실행) | 대상 파일: S2/S3/S4 산출물 | 산출: 다듬어진 3개 doc + 회귀 통과 증거 | 검증: 아래 E2E 자가검증 블록.

## E2E 자가검증

```bash
# 1. 신규 설계 doc 3종 존재 확인
ls docs/design/goal-doc-spec.md docs/design/output-adapter-contract.md
ls docs/plans/spec-first-extraction-2026-06-02.md

# 2. trigger 회귀 — spec-first SKILL.md description을 건드렸다면 필수
#    (S4에서 spec-first 포지셔닝/명명을 만지면 description 변경 가능)
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 9 self-test cases passed
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# 제거된 trigger가 보고되면 의도적인지 리뷰어 확인 (CLAUDE.md 필수 trigger 복원)

# 3. JSON 유효성 — 미해결 4 standalone 실행으로 plugin.json/marketplace.json을 건드린 경우만
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace OK"
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "tt plugin OK"

# 4. 기존 회귀 스위트 무손상 확인 (설계 묶음이지만 인접 파일 오염 방지)
python3 vault-bridge/scripts/test/test-discover.py
# Expected: OK: all cases passed
python3 telemetry/scripts/validate-schema.py --self-test
# Expected: OK: self-test passed

# 5. 설계 doc 내부 정합성 — 매핑표 8행이 전부 존재하는지 (수동 grep 보조)
grep -E 'graphify|OVM|spec-first|handoff|save-session|doc-concretize|doc-polish|gh' \
  docs/design/output-adapter-contract.md | wc -l
# Expected: ≥8 (8개 매핑 전부 언급)
```

- 통과 기준:
  - 신규 doc 3종 모두 존재(`ls` 실패 0).
  - trigger 회귀 self-test 9/9 통과 + `origin/main` diff에서 의도하지 않은 trigger 제거 0건.
  - 건드린 JSON 파일 전부 `json.tool` 통과 + version/description/keywords 동기화(미해결 4 실행 시).
  - 인접 회귀 스위트(test-discover, telemetry self-test) 무손상.
  - output-adapter-contract.md에 8개 매핑 전부 명시(grep ≥8).
  - #100/#101/#111 Acceptance 체크리스트 100% (완료 조건 섹션과 1:1 대조).

## 의존성 / 순서 주의

- **선행 goal**: G1(#99 경계 A 선언 + W5 reframe). G1이 "claude-kit=①②③④ leaf, OMC=⑤실행" 경계를 명문화해야 G2의 parse/exec 결정(실행=OMC `/goal`, 생성=claude-kit)이 정합해요. G1 미완 시 G2 parse/exec 결정의 전제가 흔들려요.
- **크로스청크 게이트 (하류)**:
  - **#102 (G3 wave, 출력 레이어 단일 vs 분산)** ← G2의 출력 어댑터 계약을 입력으로 받음(#102 Deps=#101). G2는 *논리적 계약*만 확정하고 물리 구조는 #102로 넘김. spec-first 분리 실행(#111-4)도 #102 결정에 게이트.
  - **#103/#104 (② 출력 레이어 조립)** ← G2 어댑터 계약에 의존.
  - **#105 (thought-chain dissolve, BREAKING)** ← #100(goal-doc 스펙) + #103 의존. G2의 goal-doc 레시피가 thought-chain "풀 파이프라인" 편의를 동등 제공함을 입증해야 dissolve 확정(U-4 CT 조건). 미입증 시 thin alias 잔존.
- **착수 조건**: G1 완료 + ralplan consensus 게이트 통과(`status: gated` → `ready`). #100이 명시적으로 consensus 게이트를 권장하고, linchpin이라 스키마 결정 오류가 하류 5개 청크(#102/#103/#104/#105 + spec-first 분리)를 오염시키므로 합의 후 착수를 강제해요.
- **주의**: S4 #111 §2 웹검증은 2025-08 training cutoff 이후 spec-kit/Kiro 변화를 반영해야 하므로 반드시 실제 웹검색(deep-research / document-specialist) 위임 — 추측 금지.
