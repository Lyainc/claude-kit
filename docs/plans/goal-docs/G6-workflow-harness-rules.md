---
goal_id: G6
title: ⑤ 하네스 플러그인 신설 + 3-tier 규칙 시스템
issues: [122, 125]
wave: 4
depends_on: [G1, G2]
recommended_model: opus
status: gated
work_type: feature-full
created: 2026-06-03
---

# G6 — ⑤ 하네스 플러그인 신설 + 3-tier 규칙 시스템

> **⛔ SUPERSEDED (#217 + 현재값 재배치).** 이 계획은 실행 전 대체됐어요 — `status: gated`로 G1/G2 게이트를
> 대기하던 사이 ⑤ 트랙이 [`G14`](G14-self-hosting-bootstrap.md)(scaffold + retro)와
> [`G16`](G16-harness-router-invariant.md)(4종 라우터 + invariant)로 재편됐고, #217이 ⑤ 하네스를
> **dev-harness**(개발 거버넌스)/**feedback-loop**(자기개선)로 분리했어요. 이 문서의 거버넌스 산출물(엔진·라우터·규칙·invariant)은
> dev-harness로 안착해서 본문 플러그인 이름을 현재값으로 갱신했어요. 단, "## 포함 이슈"의 `feat(workflow-harness):`는
> 실제 #122 이슈 제목 인용이라 보존해요. 현재 실재 상태·산출물 위치는 G14/G16 배너를 참조하세요.

## 배경 / 목적

claude-kit 레이어 재설계(`docs/discussions/20260602_claude-kit-layer-redesign/`)의 옵션 A 합의에 따르면, claude-kit은 ①인지·②출력·③딜리버리·④지식베이스만 소유하고 ⑤실행은 지금까지 OMC가 담당했어요. D1은 "OMC 완전 제거 + 자체 단일화"에서 **native substrate 기반 경량 하네스 + strangler 점진 대체**로 재정의됐어요(2026-06-03). Claude Code 네이티브(dynamic Workflow, /goal, agents, hooks)를 substrate로 한 thin 레이어로 OMC를 점진 흡수하고, 자체 빌드는 native가 못 채우는 gap(헌법 invariant enforcement 등)에 한정해요. native가 강해질수록 매몰비용이 아니라 수혜고, 이 묶음이 그 ⑤실행 레이어의 첫 구현체예요.

> 방향 근거: 이 native-substrate 방향은 `docs/adversarial-review/2026-06-03-harness-ownership.md`에서 strong-form(전면 OMC 자체 대체 = 옵션 B)이 기각된 뒤 채택된 narrow path예요. 선행·세부는 신설 이슈로 분리돼요 — **#132**(OMC→native substrate 매핑 + strangler 경로 = #122 thin 레이어 범위 확정의 선행), **#133**(⑤ 실행 스킬 인벤토리 — spec/impl/critique 별도 + debug/quality/issue, native 우선 판정), **#134**(검증 게이트 체인 — 프리커밋/슬라이스 critique/프리푸시 quality/retro).

두 이슈를 한 묶음으로 두는 응집 근거예요:
- **#122**가 `/goal` 루프 엔진(goal-doc parse/exec, 슬라이스 진행, 훅 트리거)과 D11 4종 슬라이스→스킬 바인딩 라우터를 만들어요.
- **#125**의 3-tier 규칙 병합 지점이 바로 그 goal-doc 파싱 단계거든요. 규칙 시스템이 붙을 *런타임 표면*이 #122에서 생기니까, 엔진과 규칙 레이어를 같은 wave에서 짜야 인터페이스가 어긋나지 않아요.
- 둘 다 D5 헌법(constitution)을 시행 지점으로 공유해요. #122는 불변 규칙(new-file-only·격리critique·self-approval금지·goal-doc스키마·단방향)을 시행하고, #125는 그 헌법 항목을 "어느 tier도 override 불가"로 못박아요.

핵심 제약: **leaf 플러그인(thinking-tools, obsidian-vault-manager, vault-bridge) 직접 수정 금지.** harness→leaf 단방향 의존만 허용해요(D2 격리). harness는 CC 전용 구현이고 leaf는 vendor-neutral로 남겨야 하거든요.

## 포함 이슈

- **#122**: feat(workflow-harness): new plugin for layer ⑤ execution engine — ⑤실행 레이어 신규 플러그인. Claude Code 네이티브(/goal·Workflow·agents·hooks)를 substrate로 한 경량 오케스트레이션 레이어. `/goal` 루프 + D11 4종 슬라이스 라우터 + D2 격리 + D5 헌법 시행 지점. **native 위임 우선** — OMC를 strangler 점진 대체하고 자체 빌드는 native가 못 채우는 gap에 한정(from-scratch 자체 엔진 아님). native가 강해질수록 매몰비용이 아니라 수혜.
- **#125**: design: 3-tier rule system + guardrails for claude-kit — 3-tier 규칙(default/user-global/project-local) + 병합 우선순위(project>user-global>default) + 안전판 4종(확인게이트·근거첨부·stale재검토·끄기스위치). 헌법/정책 *목록*은 #99 단일 출처 참조만.

## 완료 조건 (Definition of Done)

### #122 Acceptance (엔진)
- [ ] `dev-harness/.claude-plugin/plugin.json` 작성, `.claude-plugin/marketplace.json`에 신규 플러그인 항목 등록(`source: ./dev-harness/`)
- [ ] `/goal` 루프 엔진(스킬 또는 슬래시 커맨드): goal-doc parse → 슬라이스 진행 → 결과 훅 트리거 흐름 구현
- [ ] D11 4종 슬라이스→스킬 바인딩 라우터:
  - 기능개발 full = spec → impl → critique 전체 슬라이스(각각 별도 스킬). impl은 native agents 위임/스킬 인벤토리(#133) 우선 판정 — native·기존 leaf로 충분하면 신설 안 함, 못 채우는 gap만 thin하게(예시 바인딩: impl=executor, critique=code-reviewer/verifier)
  - 버그수정 경량 = goal-doc 생략, debug 슬라이스 직행
  - 의사결정 = 실행 없음(expert-panel/adversarial-review 산출만)
  - 문서작성 = 출력 전용(doc-concretize/doc-polish/spec-first 바인딩)
- [ ] D5 헌법 불변 규칙 시행 로직 포함: new-file-only · 격리 critique(authoring≠review) · self-approval 금지 · goal-doc 스키마 검증 · 단방향 의존 불변
- [ ] leaf 플러그인 3종 디렉토리에 변경 없음(diff로 증명) — harness→leaf 단방향만
- [ ] 통합 테스트: 슬라이스 바인딩 라우팅 4종 케이스 전부 커버하는 회귀 테스트(`dev-harness/scripts/test/test-slice-router.py`)

### #125 Acceptance (규칙)
- [ ] `docs/design/rule-tiers.md`: 3-tier 구조 + 병합 우선순위(project > user-global > default) + 충돌 해소 규칙
- [ ] 안전판 4종 발동 조건 명세(각각 끄기 가능 여부 포함, **헌법 항목은 끄기 불가** 명시)
  - 확인 게이트: 규칙 추가는 자동 *후보*까지, 확정은 사용자(silent 등록 금지)
  - 근거 첨부: 각 user-rule에 관찰 근거(E8 `detail`에 refs_in 붙이는 패턴 재사용)
  - stale 재검토: 규칙 M일 미검토 시 warning(OVM audit stale 패턴 재사용)
  - 끄기 스위치: user-rule 전체/부분 비활성 경로(헌법 항목 제외)
- [ ] tier 경로 확정: user-global = vault `type: rule` 노트(읽기는 vault-searcher haiku 경유), project-local = `.claude/dev-harness.local.md`(plugin-settings 패턴)
- [ ] 헌법/정책 *목록*은 #99 `## Design Principles` 참조만 — 이 묶음에서 재정의 금지(단일 출처)
- [ ] goal-doc(#100)에 "적용 tier 선언"(default만 / +user / +project) 필드 연결 지점 명시 — 병합은 goal-doc 파싱 단계

### 공통 검증 게이트 (CLAUDE.md Validation 섹션 실제 명령)
- [ ] `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` 통과
- [ ] `python3 -m json.tool dev-harness/.claude-plugin/plugin.json > /dev/null` 통과
- [ ] `bash -n dev-harness/hooks/*.sh`(훅이 생긴 경우) 통과
- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` — leaf 트리거 제거 0건(leaf 무수정 증명)
- [ ] 신규 라우터 회귀 테스트 4종 케이스 전부 통과
- [ ] (해당 시) Version Sync Rule: plugin.json ↔ marketplace.json의 version/description/keywords 동기화

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| **착수 게이트** | (a) 지금 착수 (b) G1+G2(=#99 경계, #100 goal-doc spec) 완료 후 | **(b) 게이트** | #100이 LINCHPIN. goal-doc 스키마 없이 parse/exec 구현 불가. status=gated 유지, G1·G2 머지 후 ready 전환 |
| **`/goal` 엔진 형태** | (a) 슬래시 커맨드 (b) SKILL.md 스킬 (c) 둘 다(커맨드=엔트리, 스킬=레시피) | **(c)** | vault-bridge 패턴(`disable-model-invocation: true` 커맨드 + reference recipe) 검증됨. 커맨드가 contract surface, 스킬이 실행 본문 |
| **parse/exec 주체** | (a) Claude Code 네이티브 `/goal`·Workflow에 위임 + OMC 공존 (b) dev-harness가 from-scratch 자체 파싱·실행 엔진 | **(a) native 위임 우선, gap만 thin하게 자체** | 단기는 네이티브 `/goal`·Workflow + OMC 공존, 장기는 native substrate 위 경량 하네스가 strangler로 점진 흡수. **native 위임 우선** — 자체 빌드는 native가 못 채우는 gap(헌법 invariant enforcement 등)에 한정. 동작 중인 OMC 전면 교체(from-scratch 엔진)는 lock-in 실측 증거 0건 + native supersession 매몰비용으로 기각(adversarial strong-form 기각). 어떤 capability를 native가 대체/위임하고 무엇이 gap인지는 #132 substrate 매핑이 선행 확정 |
| **3-tier 병합 시점** | (a) goal-doc 파싱 단계 (b) 슬라이스 실행 직전 매번 | **(a)** | #125 본문이 "병합 지점 = goal-doc 파싱 단계"로 명시. 매 슬라이스 재병합은 비용·비결정성 증가 |
| **user-global 규칙 읽기** | (a) harness가 직접 vault read (b) vault-searcher(haiku) 경유 | **(b)** | #125 명시 + vault-bridge pre-access-guard가 직접 접근에 warning 발생. read-only haiku 경유가 비용·정책 양쪽 부합 |
| **헌법 끄기** | (a) 강제 불가(코드 레벨 차단) (b) 경고만 | **(a) 차단** | D5 "헌법 불변". 끄기 스위치는 user-rule(정책)에만, 헌법은 어느 tier도 override·disable 불가 |
| **라우터 테스트 형태** | (a) 실제 슬라이스 실행 e2e (b) 라우팅 결정만 검증하는 단위 테스트 | **(b)** | leaf/LLM 실행은 비결정적. test-discover.py처럼 *결정 로직*(input 워크타입 → 바인딩 시퀀스)만 hermetic하게 검증. 실제 실행은 수동 dogfood |

**미해결 질문 (G1/G2 결과 대기)**:
- D5 헌법/정책 *항목 목록*의 확정 형태 = #99(G1) `## Design Principles`에 의존. 본 doc은 시행 *메커니즘*만 다루고 목록은 참조.
- goal-doc 스키마의 정확한 필드(특히 "적용 tier 선언" 필드명·enum) = #100(G2) 결과에 의존. 슬라이스 S3는 G2 스키마 확정 전 착수 불가.

## 슬라이스 순서

순서는 의존 기반이에요. S1~S2(엔진 골격)는 G1·G2 머지 직후 착수, S3(규칙 병합)는 G2의 goal-doc 스키마 확정이 hard 전제예요.

1. **S1 플러그인 스캐폴드 + 마켓 등록** → 바인딩: `executor` | 대상 파일: `dev-harness/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `dev-harness/README.md` | 산출: 빈 플러그인 골격 + 마켓 항목 | 검증: `python3 -m json.tool` 양쪽 통과, Version Sync(version/description/keywords 동기화)

2. **S2 `/goal` 루프 엔진 + D11 4종 라우터** → 바인딩: `executor`(model=opus) | 대상 파일: `dev-harness/commands/goal.md`(엔트리, `disable-model-invocation: true`), `dev-harness/skills/goal-loop/SKILL.md`(레시피 본문), `dev-harness/reference/slice-routing.md`(4종 워크타입→바인딩 표) | 산출: goal-doc parse → 슬라이스 진행 → 훅 트리거 흐름 + 4종 라우터 | 검증: 슬라이스 라우팅 단위 테스트(S6에서 작성)

3. **S3 3-tier 규칙 병합 + tier 선언 연결** → 바인딩: `executor` | 대상 파일: `docs/design/rule-tiers.md`(설계), `dev-harness/reference/rule-merge.md`(병합 알고리즘 default←user-global←project), goal-doc 파서에 "적용 tier 선언" 필드 hook | 산출: 우선순위 병합 + #100 tier 선언 필드 연결 지점 | 전제: **G2(#100) goal-doc 스키마 확정** | 검증: 병합 우선순위 단위 테스트(project가 user-global을 덮고, 둘 다 default를 덮는지)

4. **S4 안전판 4종 + 헌법 시행** → 바인딩: `executor` | 대상 파일: `dev-harness/reference/guardrails.md`(4종 발동 조건), `docs/design/rule-tiers.md`(안전판 섹션 보강), 헌법 차단 로직(끄기 불가 enforce) | 산출: 확인게이트·근거첨부·stale재검토·끄기스위치 명세 + 헌법 override/disable 차단 | 전제: **G1(#99) Design Principles** 헌법/정책 목록 참조 가능해야 함 | 검증: 헌법 항목 disable 시도 → 차단 케이스 테스트

5. **S5 D2 격리 + D5 단방향 불변 검증 지점** → 바인딩: `executor` | 대상 파일: `dev-harness/reference/isolation-contract.md`(harness=CC전용, leaf=vendor-neutral, 단방향 명세), leaf 무수정 가드(테스트 또는 문서 체크) | 산출: harness→leaf 단방향 명문화 + leaf 역참조 금지 검증 | 검증: leaf 디렉토리 git diff 0줄 + trigger-regression 제거 0건

6. **S6 통합 테스트 작성 (4종 라우팅)** → 바인딩: `executor` + `verifier` | 대상 파일: `dev-harness/scripts/test/test-slice-router.py`, `dev-harness/scripts/test/test-rule-merge.py` | 산출: test-discover.py 스타일 hermetic 회귀 테스트 — 4종 워크타입(full/버그경량/의사결정/문서) 입력 → 기대 바인딩 시퀀스, 3-tier 병합 우선순위 케이스 | 검증: `OK: all cases passed` 출력, exit 0

7. **S7 격리 critique 패스** → 바인딩: `code-reviewer` → `verifier` | 대상 파일: 전체 변경분 + 신규 테스트 | 산출: D5 self-approval 금지 준수(저작과 리뷰 분리), [CRITICAL] 지적 사항 처리 | 검증: 리뷰어 evidence 수집, 전 테스트 재실행 통과

8. **S8 문서 정합 + CLAUDE.md Validation 갱신** → 바인딩: `doc-polish` | 대상 파일: `CLAUDE.md`(Validation 섹션에 신규 테스트 명령 추가, Directory Structure에 dev-harness 추가), `AGENTS.md`(parity 미러), `docs/codex-claude-parity.md` | 산출: 신규 플러그인·테스트 명령 문서 반영 | 검증: doc-polish lint 통과, 테스트 명령 복붙 실행 가능

## E2E 자가검증

```bash
cd /Users/Lyainc/dev/prj/claude-kit

# 1) JSON 유효성 — 신규 플러그인 + 마켓 (CLAUDE.md Validation 섹션)
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace OK"
python3 -m json.tool dev-harness/.claude-plugin/plugin.json > /dev/null && echo "plugin OK"

# 2) 신규 라우터/병합 회귀 테스트 4종 (S6 산출, test-discover.py 패턴)
python3 dev-harness/scripts/test/test-slice-router.py   # Expected: OK: all cases passed (>=4 cases: full/bug-light/decision/doc)
python3 dev-harness/scripts/test/test-rule-merge.py     # Expected: OK: all cases passed (project>user-global>default + 헌법 disable 차단)

# 3) leaf 무수정 증명 — 트리거 제거 0건 (CLAUDE.md Validation 섹션, 실재 명령)
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test   # Expected: OK: all 9 self-test cases passed
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main   # Expected: 제거 0건 (leaf 디렉토리 무변경)

# 4) leaf 플러그인 디렉토리 git diff 0줄 (D2 단방향 격리 증명)
git diff --stat origin/main -- thinking-tools/ obsidian-vault-manager/ vault-bridge/ | tail -1   # Expected: 변경 없음

# 5) 훅이 생긴 경우 셸 문법 (CLAUDE.md Validation 섹션 패턴)
ls dev-harness/hooks/*.sh >/dev/null 2>&1 && bash -n dev-harness/hooks/*.sh && echo "hooks syntax OK" || echo "no hooks (skip)"

# 6) 기존 leaf 회귀가 안 깨졌는지 회귀(스모크)
python3 vault-bridge/scripts/test/test-discover.py 2>&1 | tail -1   # Expected: OK: all cases passed
```

- **통과 기준**: (1) JSON 양쪽 valid · (2) 라우터·병합 테스트 모두 `OK: all cases passed`, exit 0, 4종 워크타입 + 3-tier 우선순위 + 헌법 disable 차단 케이스 포함 · (3) trigger-regression 제거 0건 · (4) leaf 3종 디렉토리 diff 0줄 · (5) 훅 문법 통과(또는 훅 없음) · (6) 기존 leaf 회귀 통과. 하나라도 실패 시 S7 격리 critique로 회귀 후 반복.

## 의존성 / 순서 주의

- **wave=4, ∥G5** — G5와 병렬 가능하나 둘 다 G1·G2 의존.
- **depends_on=[G1, G2] (hard gate)**:
  - **G1(#99 경계 A + Design Principles)**: harness↔leaf 단방향 경계와 헌법/정책 *목록*의 단일 출처. S4(헌법 시행)·S5(격리)가 이 목록을 *참조*해야 하므로 G1 머지 전 착수 불가. 본 doc은 목록을 **재정의하지 않고 참조만** 해요(#125 Acceptance 강제 조항).
  - **G2(#100 goal-doc spec, LINCHPIN)**: goal-doc 스키마 + 슬라이스 바인딩 표기 + parse/exec 인터페이스. 이게 없으면 S2(엔진)·S3(tier 선언 필드 연결) 구현 불가. **status=gated** 유지, G2 머지 직후 ready 전환.
- **신설 이슈 연계(native-substrate 방향)**:
  - **#132 (OMC→native substrate 매핑 + strangler 경로, 선행 권장)**: 어떤 OMC capability를 native(/goal·Workflow·agents·hooks)가 대체/위임하고 무엇이 gap으로 남는지 확정해야 #122 thin 레이어(S2 엔진·S5 격리) 범위가 정해져요. native가 이미 제공하는 걸 자체 빌드하지 않도록 게이트 역할.
  - **#133 (⑤ 실행 스킬 인벤토리)**: D11 4종 라우터의 기능개발 full = spec → impl → critique 각 단계의 구체 스킬 귀속(재사용/native위임/신설)을 확정. S2 라우터 바인딩이 이 인벤토리와 정합해야 해요.
  - **#134 (검증 게이트 체인)**: 프리커밋 린터·슬라이스 critique·프리푸시 quality·retro 자동 게이트를 harness가 오케스트레이션. S5 격리 critique invariant가 슬라이스 게이트로 쓰여요.
- **크로스청크 게이트**: #105(thought-chain dissolve)가 goal-doc 레시피 바인딩 표기를 확정한 뒤 harness가 그 레시피의 런타임이 됨(#122 비고). #105가 본 wave 밖이면 thought-chain 흡수는 본 doc 범위에서 제외하고, 라우터는 generic 4종 워크타입까지만 커버.
- **착수 조건 체크리스트**: ① `docs/plans/goal-docs/G1-*.md` 머지됨 → Design Principles 목록 참조 가능 ② `docs/plans/goal-docs/G2-*.md` 머지됨 → goal-doc 스키마·tier 선언 필드명 확정 ③ 두 조건 충족 시 본 doc front-matter `status: gated → ready` 전환 후 S1 착수.
- **leaf 무수정 불변**: 어떤 슬라이스도 thinking-tools/obsidian-vault-manager/vault-bridge 디렉토리를 수정하지 않아요. 필요하면 harness 측에서 leaf를 *호출*만 해요(단방향). 위반 시 E2E 검증 (4)에서 잡힘.
