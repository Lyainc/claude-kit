# ⑤ 검증 게이트 체인 — 4지점 게이트 명세 (커밋·슬라이스·푸시·완료)

**Issue**: #134 · **Epic**: #172(⑤ self-hosting 부트스트랩) → #108(⑤ 실행 트랙)
**Status**: design · **Created**: 2026-06-09
**선행**: #122(thin 하네스 — 게이트 오케스트레이션 주체) · #132(`docs/design/omc-to-native-substrate.md` §4.2 Gap-INV·§5 P4) · #133(`docs/design/execution-skill-inventory.md` — quality/critique 스킬 판정) · #123(`feedback-loop/skills/retro/SKILL.md` — retro 로직, #217로 이전) · #183(`dev-harness/scripts/invariant_guard.py` — `check_isolated_critique` enforce, #217로 이전)
**소비처**: slice-router 스킬(#183 — SKILL.md `Phase 3 — ENFORCE`가 게이트 ② 발동 절차) · ⑤ 실행 루프 dogfood(P4 feature-dev goal-doc e2e)

> **갱신 (2026-06-29 CUT) — 이 문서는 역사 기록이에요.** 여기서 오케스트레이션 주체로 삼은 slice-router·goal-doc 루프는 전량 철회됐어요 — 단일 출처는 `docs/design/claude-kit-boundary.md` §1 + #282/#283. 4지점 게이트가 실제로 엮던 개별 enforce 로직(invariant_guard·retro 등)은 각자 제자리(#217 이관분 포함)에서 유효하지만, 이 문서가 명세한 "goal-doc 루프 안에서 언제 발동"이라는 오케스트레이션 그림 자체는 더 이상 실행되지 않아요.

> **이 문서는 게이트의 *오케스트레이션*만 명세해요 — 게이트 *수단*은 재정의하지 않아요.**
> 4지점 게이트가 호출하는 실제 enforce 로직·스킬 정의는 모두 기존 자산에 있고, 이 문서는 그걸 "언제·어디서·어떤 조건으로" 발동할지만 엮어요(thin orchestration). 단일 출처:
> - 슬라이스 critique enforce = `dev-harness/scripts/invariant_guard.py` `check_isolated_critique` (#183, #217로 이전)
> - quality 스킬 정의 = `docs/design/execution-skill-inventory.md` §1·§3 (#133)
> - retro 로직 = `feedback-loop/skills/retro/SKILL.md` (#123, #217로 이전)
> - 헌법 규칙 = `docs/design/claude-kit-boundary.md` §5 (CON-1/CON-3/CON-5)
>
> 게이트 수단을 여기서 다시 정의하면 drift가 나요. 아래는 전부 *참조*예요.

---

## 0. 위치와 방향 (strangler P4 · native-delegation 우선)

게이트 체인은 strangler 경로(`omc-to-native-substrate.md` §5)의 **P4 — 스킬 바인딩 + 게이트 체인**에 정확히 놓여요. P2(라우터·#183)·P3(invariant enforce·#183)·P5(retro·#123)가 이미 자리잡은 상태에서, 이 문서는 그 조각들을 **실행 루프의 4개 시점에 게이트로 배치**하는 오케스트레이션 명세예요. #172 epic(⑤ self-hosting 부트스트랩)의 마지막 미완분 — 닫으면 epic 종결.

**thin 원칙(substrate §4)**: 게이트 체인은 새 enforce 엔진을 짓지 않아요. native(git hooks·Claude Code hooks·CI)와 기존 자산(#183 invariant_guard·#133 인벤토리·#123 retro)을 먼저 매핑하고, 하네스는 그 위에 **"발동 시점 + 적용 조건 + scope 처리"** 만 얹어요. native가 못 하는 의미 판정(이 critique가 격리됐나·이 reviewer가 author와 같나)은 이미 #183이 enforce하니, 게이트 체인은 그걸 슬라이스 루프에 *연결*만 해요.

---

## 1. 4지점 게이트 — 마스터 표

| # | 시점 | 게이트 | 발동 조건(트리거) | native 우선 | 기존 자산(재정의 금지) | 하네스 역할 | 분류 |
|---|------|--------|------------------|-------------|----------------------|------------|------|
| ① | **커밋 단위** | 프리커밋 린터 | `git commit` 시점(커밋마다) | git `pre-commit` hook · Claude Code PreToolUse(Bash `git commit`) hook | docs/VALIDATION.md 결정적 스크립트군 (`check-version-sync.py`·`check-ci-coverage.py`·`invariant_guard.py validate`·`bash -n`) | 권장 린터 세트 매핑만(설치는 프로젝트) | **opt-in 정책** |
| ② | **슬라이스 단위** | fresh-eyes critique + 셀프 검증 | feature-full 라우트의 critique 슬라이스 진입 직전(slice-router **SKILL.md** `Phase 3 — ENFORCE` 절차) | native Agent(별도 컨텍스트 spawn, N3) | `invariant_guard.check_isolated_critique`(CON-3) + `check_new_file_only`(CON-1 셀프 검증) (#183) | active agent가 critique를 별도 Agent로 spawn + 게이트 절차에서 `check_isolated_critique` 호출(판정 로직 재구현 0) | **헌법(CON-3) — 조건부 immutable** |
| ③ | **푸시 직전** | quality 스킬(린터보다 큰 단위) | `git push` 시점(opt-in) / CI(push·PR) | git `pre-push` hook · CI(`validate.yml`·`claude-code-review.yml`) | #133 quality 인벤토리(code-reviewer·verifier=native / doc-polish=② / adversarial-review·expert-panel=①) | payload별 인벤토리 스킬 소환만(quality 신설 0) | **opt-in 정책** |
| ④ | **완료 후** | retro 자동 호출 | goal 완료조건 충족(`/goal` auto-clear) 또는 푸시 통과 후 | — (retro는 스킬) | retro 스킬(#123) — 트리거 + 2갈래 scope | retro 트리거만(로직은 #123 소유) | **자동 트리거(내부 user-confirmed)** |

`→` 실행 흐름: 커밋(①, N회) → 슬라이스 경계(②, feature-full critique마다) → 푸시(③, 1회) → 완료(④, 1회). 같은 goal-doc 루프 안에서 ①은 여러 번, ②는 critique 슬라이스 수만큼, ③④는 루프 끝에 한 번씩 발동돼요.

---

## 2. 게이트 분류 — opt-in 정책 vs 헌법 게이트 (핵심)

#134 원칙은 "게이트는 강제가 아니라 제공/권장 — opt-in"인데, 동시에 "CON-3 격리 critique가 슬라이스 게이트의 근거"예요. 이 둘은 **충돌이 아니라 중첩**이에요. 분류를 섞으면 헌법(immutable)을 opt-out으로 오해하거나, 자율 영역(프리커밋)을 강제로 오해해요. 세 범주로 분리해요.

### 2.1 opt-in 정책 게이트 — ①③ (프로젝트 자율)

프리커밋(①)·프리푸시(③)는 **프로젝트 자율성 영역**이에요(adversarial Scope 반박 수용 — 모든 레포에 git hook을 강제하면 자율 침해). 그래서:

- **제공/권장**이지 강제 아님. 하네스는 "이 검증을 커밋/푸시 게이트로 걸면 좋다"는 권장 세트를 매핑할 뿐, git hook 설치 여부는 프로젝트가 결정해요.
- **현재 상태가 정상 디폴트**: 이 레포 `.git/hooks/`엔 활성 `pre-commit`/`pre-push`가 없어요(`pre-commit.sample`/`pre-push.sample`만 — 게이트 ①③ 미설치). 미설치가 opt-in 미선택 상태 — 정상이에요. (게이트와 무관한 `post-checkout`/`post-commit`은 활성이라 디렉토리 전체가 sample-only인 건 아니에요. 또 `.git/hooks/`는 clone별 로컬 상태라 레포 불변식이 아니에요 — 게이트 ①③은 그래서 *권장*이지 보장이 아니에요.) CI(`validate.yml`)가 push·PR에서 동일 검증을 항상 돌리므로, 로컬 hook을 안 걸어도 안전망은 유지돼요.
- override 경로: 프로젝트가 hook을 설치(opt-in)하거나 안 함(default). 정책 tier(`rule-tiers.md` §1 — project-local)로 강도 조절.

### 2.2 헌법 게이트 — ② (조건부 immutable)

슬라이스 critique(②)의 근거는 **CON-3(self-approval 금지 — reviewer ≠ author)**, 헌법이라 어느 tier·kill switch로도 끌 수 없어요(`rule-tiers.md` §2 안전판 4 — Kill Switch "헌법은 끌 수 없음"). 하지만 "강제"의 정확한 의미는:

> **게이트 ②는 *적용 대상*에 한해 immutable이고, 적용 대상의 범위는 work_type이 결정해요.**

- critique 슬라이스를 가진 work_type은 **feature-full뿐**이에요(`slice_router.py` `_SLICE_SEQUENCES` — feature-full만 critique 슬라이스 보유). decision-only·doc-only·bug-light엔 critique 슬라이스 자체가 없어서 **격리를 적용할 대상이 없어요**(강제할 게 없음 ≠ opt-out).
- feature-full 루프를 실행하기로 *선택한 순간*, 그 안의 critique는 별도 Agent 컨텍스트로 격리되고(reviewer ≠ author) 이건 양보 불가예요. active agent가 `check_isolated_critique(route_plan)`를 호출해 author 바인딩과 겹치는 critique 바인딩을 발견하면 **STOP** — 게이트가 통과를 막아요(slice-router SKILL.md `Phase 3 — ENFORCE` 절차가 이 호출을 명세).
- **중첩 구조**: *게이트 체인 전체를 채택*하는 건 opt-in(§2.1), 그러나 *채택 후 feature-full critique의 격리*는 헌법이라 immutable. 바깥 껍질은 opt-in, 안쪽 헌법 핵은 불변 — 이 두 층을 혼동하면 안 돼요.

### 2.3 자동 트리거 게이트 — ④ (트리거 자동 · 내부 user-confirmed)

retro(④)는 goal 완료 후 *자동으로 트리거*되지만, retro 내부의 모든 부수효과(승격·이슈 발행·규칙 추가)는 **user-confirmed gate**예요(retro SKILL.md "Silent ... is FORBIDDEN"). 즉 발동은 자동, 행위는 확인 게이트. 이 게이트는 "막는" 게 아니라 "회고를 여는" 트리거라 ①②③과 성격이 달라요.

---

## 3. 게이트별 상세 명세 + native/기존 매핑 (Acceptance 2)

### 3.1 게이트 ① — 커밋 단위 프리커밋 린터

**목적**: 커밋마다 빠른 결정적 검증으로 깨진 상태가 히스토리에 들어가는 걸 막아요.

| 항목 | 내용 |
|------|------|
| native 우선 | git `pre-commit` hook(프로젝트 설치) 또는 Claude Code PreToolUse hook(Bash matcher `git commit` — 메인 컨텍스트 커밋 직전). CON-2(결정적 훅·턴당 LLM 0) 정합 — 셸 스크립트만. |
| 기존 자산(매핑) | docs/VALIDATION.md의 **결정적·경량** 스크립트만: JSON validity(`python3 -m json.tool`), `check-version-sync.py`(drift block), `invariant_guard.py validate <goal-doc>`(INV-4), `invariant_guard.py --self-test`, `bash -n hooks/*.sh`. |
| 하네스 역할 | "프리커밋 게이트엔 이 경량 세트"를 권장 매핑. 무거운 fixture 테스트(audit DoD·gen-fixture)는 ③/CI로 미뤄요 — 커밋마다 돌리기엔 느려서. |
| opt-in | YES. 프로젝트가 hook 설치 안 하면 CI(`validate.yml`)가 동일 검증을 push·PR에서 커버. |

> 분배 원칙: **커밋 게이트 = 빠른 결정적 체크**(초 단위), **푸시/CI 게이트 = 무거운 fixture·통합**(분 단위). 같은 스크립트라도 비용에 따라 시점을 나눠요.

### 3.2 게이트 ② — 슬라이스 단위 fresh-eyes critique + 셀프 검증

**목적**: 슬라이스가 자기 산출을 자기가 승인하지 못하게(CON-3) + 산출이 헌법 불변을 깨지 않는지(CON-1) 슬라이스 경계마다 확인해요.

| 항목 | 내용 |
|------|------|
| native 우선 | native Agent(별도 컨텍스트 spawn, substrate §2 N3). reviewer 소환은 native Workflow verify 스테이지 / Agent. |
| 기존 자산(매핑) | `invariant_guard.check_isolated_critique(route_plan)` — critique 바인딩이 spec/impl(author) 바인딩과 disjoint인지 판정(CON-3). qualifier 안에 author를 숨긴 self-approval도 차단. **셀프 검증**: `check_new_file_only`(CON-1 — 산출이 기존 파일 덮어쓰는지). 둘 다 #183이 enforce 완료. |
| 하네스 역할 | 발동 지점 = slice-router **SKILL.md** `Phase 3 — ENFORCE` 절차(`dev-harness/skills/slice-router/SKILL.md:98`). 절차를 수행하는 **active agent**가 critique 슬라이스를 **별도 Agent 컨텍스트**로 spawn하고, delegate 전에 `check_isolated_critique(route_plan)`를 호출해 통과시켜요. 겹치면 STOP. **판정 로직 재구현 0** — 게이트 체인은 *언제 호출할지*만 명세하고, 판정은 전부 #183 `invariant_guard`. |
| 코드 seam (중요) | `slice_router.py`의 `route()`는 **plan만 생성**해요 — `parse_goal_doc`/`validate_goal_doc`만 import하고 `check_isolated_critique`는 **호출하지 않아요**(스크립트 자동 wiring이 아님). 그 호출은 plan을 *소비*하는 쪽(SKILL.md Phase 3 절차를 도는 active agent, 또는 PreToolUse 핸들러)이 수행해요 — 즉 **게이트 ②는 게이트 체인 자신의 오케스트레이션 책임**이지 라우터 스크립트에 이미 박힌 자동 호출이 아니에요. (`route()` 도크스트링도 "does not summon reviewers"라고 명시 — 라우터는 결정 라이브러리, 게이트는 소비자.) |
| 발동 조건 | feature-full 라우트에서만(critique 슬라이스 보유 work_type). §2.2 참조. |

> native 한계(substrate §2 N3): 서브에이전트의 *중간* critique 과정은 호출자에게 안 보여요(최종 메시지만 반환). 그래서 격리 enforce는 *과정 감시*가 아니라 schema 구조화 출력(N1)으로 *결과 계약*을 검증하는 형태 — `check_isolated_critique`는 route_plan의 바인딩 집합을 검사하지 실행 중 컨텍스트를 추적하지 않아요. 이게 native-위임 경계의 실측 형태예요.

### 3.3 게이트 ③ — 푸시 직전 quality 스킬

**목적**: 린터보다 큰 단위(설계 일관성·중복·회귀)를 푸시 전에 한 번 훑어요.

| 항목 | 내용 |
|------|------|
| native 우선 | git `pre-push` hook(opt-in) · CI(`validate.yml` validate+audit-dod job, push·PR 트리거 · `claude-code-review.yml` PR 자동 리뷰). |
| 기존 자산(매핑) | #133 §1·§3 quality 인벤토리 — **payload 타입별 분기**: 코드 diff → native `code-reviewer`/`verifier`(C3 ✅), md → `doc-polish`(②), claim/설계 → `adversarial-review`/`expert-panel`(①). |
| 하네스 역할 | 푸시 직전 payload 타입을 보고 인벤토리의 적합 스킬을 소환만. **전용 quality 스킬 신설 0** — §4 참조. |
| opt-in | YES(로컬 pre-push). 단 CI는 항상 — 푸시 후 PR에서 `validate.yml`이 강제 게이트(예: `check-ci-coverage.py --strict`는 BLOCK). |

### 3.4 게이트 ④ — 완료 후 retro 자동 호출

**목적**: 루프를 닫고(measure→improve), 낭비를 탐색해 이슈화해요.

| 항목 | 내용 |
|------|------|
| native 우선 | — (retro는 ⑤ 하네스 스킬). 트리거 시점은 `/goal` 완료조건 충족(auto-clear) 또는 ③ 푸시 통과 후. |
| 기존 자산(매핑) | retro 스킬(#123) — COLLECT→PROMOTE→OUTPUT→BUDGET 파이프라인 전체. 트리거 키워드(`회고`/`retro`/`낭비 탐색`/…). |
| 하네스 역할 | **트리거만**. 게이트 ④는 "푸시 통과 후 retro를 발동"하는 연결선이고, retro의 모든 로직(승격 임계 재확인·dedup·예산·2갈래 scope)은 #123 소유. **재구현 0**. |
| 내부 게이트 | retro 자체가 user-confirmed(승격·이슈·규칙 전부 명시 확인). silent 금지. |

> #134 본문 "retro 자동 호출 = #123 retro를 푸시 통과 후 트리거(트리거만, retro 로직은 #123)"를 그대로 구현. 게이트 체인은 retro를 *부르는* 한 줄이지 retro를 *다시 쓰는* 게 아니에요.

---

## 4. quality 스킬 인벤토리 공유 (Acceptance 3 — 중복 정의 금지)

게이트 ③의 quality는 **새 스킬이 아니에요.** #133 인벤토리(`execution-skill-inventory.md` §1·§3)가 이미 판정했어요:

> quality(큰 단위 품질) = **REUSE + NATIVE (NEW 미정당)** — 코드=code-reviewer(native), md=doc-polish(②), 평가=adversarial-review/expert-panel(①)이 공간을 덮음. 전용 quality 신설은 **3자 중복 리스크**라 현재 미정당.

게이트 체인의 quality 정의는 이 판정과 **단일 출처를 공유**해요:

- 게이트 ③은 인벤토리의 **기존 스킬을 payload별로 소환**할 뿐, quality라는 새 스킬·새 정의를 만들지 않아요.
- 만약 미래에 게이트 ③ dogfood에서 "code-reviewer+doc-polish+adversarial-review로 안 덮이는 gap"이 *입증*되면, 그때 #133이 NEW로 재판정해요(게이트 체인이 아니라 인벤토리가 소유). 게이트 체인은 그 gap을 *발견·보고*하는 입력일 뿐, 스킬을 정의하는 출처가 아니에요.
- 즉 **이 문서는 quality 스킬을 정의하지 않아요** — #133을 참조만 하고, "게이트 ③에서 인벤토리를 이렇게 호출한다"는 *사용 규약*만 명세해요. 중복 정의 0.

---

## 5. scope 처리 정책 + retro 2갈래 (Acceptance 1 후반)

### 5.1 scope 처리 — 흡수 vs 분리 (silent drop 금지)

게이트(특히 ②의 셀프 검증·④의 낭비 탐색) 도중 *현재 scope 밖의 문제*를 발견하면, 다음 결정 트리를 따라요. **어느 경로든 흔적을 남겨요 — silent drop은 금지**(헌법적 정직성).

```
구현/검증 중 문제 발견
  ├─ 현재 goal-doc의 work_type·슬라이스 scope 안에 들어가고 작은가?
  │     └─ YES → 즉시 흡수 (현재 슬라이스/goal-doc에서 수정)
  └─ scope 밖이거나 별도 작업 단위인가?
        └─ YES → 새 이슈로 분리 (§5.2 2갈래 분류로 라우팅)
                 silent drop 절대 금지 — 흡수도 분리도 아니면 최소한 보고
```

- **흡수 기준**: 현재 슬라이스에서 곁다리로 고칠 수 있고, work_type 경계를 안 넘으면 흡수. (예: doc-only 작업 중 같은 문서의 오타·링크 깨짐.)
- **분리 기준**: 별도 도메인이거나, 흡수 시 현재 slice scope가 흐려지면 새 이슈. (예: doc 작업 중 발견한 하네스 스크립트 버그.)
- **silent drop 금지**: 발견을 무시하고 넘어가는 건 금지. 흡수·분리·최소 보고 셋 중 하나는 반드시.

### 5.2 retro 낭비 탐색 2갈래 (정책 origin #134 · 구현 소유 retro #123)

게이트 ④ retro의 낭비 탐색은 발견을 **2갈래 scope**로 분기해 이슈화해요. **역할 분리(순환 아님)**: 이 2갈래 정책의 *정의 origin*은 **#134(이 문서)** 예요(#134 이슈 본문 "하네스 레벨 → 하네스 이슈, 로컬 레포 레벨 → 로컬 이슈"가 명시). **retro(#123)는 그걸 *구현·실행 소유*** 해요(Phase 1 step 3 `scope: harness | local` 분류 + Phase 3 OUTPUT action 분기). retro SKILL.md가 자신을 "mirrors #134's 2-branch waste split"이라 부르는 것과 이 방향이 정합 — **정책 origin = #134, mechanism owner = retro**로 갈리니 "State each rule once" 위반 아니에요. §5.1의 새 이슈 분리도 *같은 taxonomy*를 써요:

| scope | 의미 | 라우팅 |
|-------|------|--------|
| **harness** | 워크플로우·툴콜·토큰 낭비(하네스/툴링 레벨) | 하네스 이슈 |
| **local** | 이 레포 고유 낭비(로컬 레포 레벨) | 로컬 이슈 |

- 두 갈래를 **절대 섞지 않아요** — 하네스 낭비를 로컬 이슈로 넣으면 추적이 깨져요(retro SKILL.md "never conflate them").
- §5.1의 scope 분리(흡수 못 하는 발견 → 새 이슈)도 이 2갈래로 라우팅해요 — 게이트 체인 전체에서 "새 이슈는 harness냐 local이냐"는 단일 기준.
- 발동: retro Phase 3 OUTPUT의 action 브랜치(`gh issue create`, 사용자 확인 후). retro가 소유한 로직 그대로.

---

## 6. 오케스트레이션 — 실행 루프 타임라인

4지점이 같은 feature-full goal-doc 루프 안에서 어떻게 엮이는지:

```
/goal 시작 (goal-doc 라우팅 — slice-router VALIDATE→ROUTE)
   │
   ├─ [슬라이스: spec] ──commit──▶ ① 프리커밋 린터(opt-in)
   │
   ├─ [슬라이스: impl] ──commit──▶ ① 프리커밋 린터(opt-in)
   │
   ├─ [슬라이스: critique] ─────▶ ② 격리 critique 게이트  ← SKILL.md Phase 3 ENFORCE 절차
   │        (active agent: 별도 Agent spawn · check_isolated_critique(plan) 호출 · CON-3 immutable)
   │
   ├─ git push ───────────────▶ ③ quality 게이트(opt-in 로컬 / CI 강제)
   │        (#133 인벤토리 payload별 소환)
   │
   └─ /goal 완료조건 충족 ──────▶ ④ retro 트리거(자동)
            (retro #123 — 2갈래 낭비 탐색 · user-confirmed)

   (decision-only / doc-only / bug-light 루프: ②(critique 슬라이스) 없음 — ①③④만, 그마저 ①③은 opt-in)
```

- 게이트 ②의 발동 지점은 slice-router **SKILL.md**의 `Phase 3 — ENFORCE` 절차예요(§3.2 코드 seam 참조) — 게이트 체인은 새 지점을 만들지 않고, plan을 소비하는 active agent가 그 절차를 critique 슬라이스마다 도는 걸로 명세해요. 라우터 스크립트(`route()`)는 plan만 만들지 게이트를 자동 호출하지 않아요.
- ①은 슬라이스마다(커밋 N회), ②는 critique 슬라이스마다, ③④는 루프 끝 1회.
- decision-only/doc-only/bug-light 루프엔 ②(critique 슬라이스)가 없어요(§2.2) — ①③④만 해당하고 그마저 ①③은 opt-in.

---

## 7. Acceptance 추적

| #134 Acceptance | 충족 위치 |
|-----------------|----------|
| `gate-chain.md`: 4지점 게이트 + 발동 조건 + opt-in 경로 + scope 처리 정책 + retro 2갈래 이슈 분리 | §1(마스터 표 — 시점·발동조건·opt-in) + §2(opt-in/헌법 분류) + §3(게이트별 발동조건) + §5.1(scope 처리) + §5.2(retro 2갈래) |
| 각 게이트 수단이 native/기존(#122 critique, #123 retro)으로 매핑 | §1·§3 각 게이트의 "native 우선" + "기존 자산(매핑)" 행 — ②=`check_isolated_critique`(#183), ④=retro(#123), ①=docs/VALIDATION.md 결정적 스크립트군, ③=#133 인벤토리+CI |
| quality 스킬 정의는 스킬 인벤토리와 공유(중복 정의 금지) | §4 — #133 §1·§3 판정 그대로 참조, 게이트 ③은 사용 규약만, quality 스킬 신설·재정의 0 |

**헌법 정합**: CON-1(②셀프 검증 `check_new_file_only`)·CON-3(②격리 critique `check_isolated_critique`)·CON-5(전 게이트가 leaf 자산을 *읽고·호출*만, 역방향 의존 0 — retro·slice-router 모두 단방향) — `claude-kit-boundary.md` §5 단일 출처 참조, 재정의 없음.

**thin 정합**: 4지점 게이트 전부 기존 자산(native + #183 + #133 + #123)에 매핑되고, 이 문서가 추가하는 건 "발동 시점·적용 조건·scope 라우팅" 오케스트레이션뿐 — 새 enforce 엔진·새 스킬 0(substrate §4 thin 원칙).

---

**참조**: `docs/design/omc-to-native-substrate.md`(§4.2 Gap-INV·§5 P4 게이트 체인 위치) · `docs/design/execution-skill-inventory.md`(§1·§3 quality 판정) · `docs/design/claude-kit-boundary.md`(§5 CON-1/3/5) · `docs/design/rule-tiers.md`(§1 tier·§2 안전판 4 Kill Switch — 헌법 immutable) · `dev-harness/skills/slice-router/SKILL.md`(`Phase 3 — ENFORCE` 절차 — 게이트 ② 발동 명세) · `dev-harness/scripts/invariant_guard.py`(`check_isolated_critique`·`check_new_file_only` — 판정 로직) · `dev-harness/scripts/slice_router.py`(`route()` — plan 생성만, 게이트 비호출) · `feedback-loop/skills/retro/SKILL.md`(#123 2갈래 scope 구현 소유) · `.github/workflows/validate.yml`(CI 게이트) · #122/#123/#132/#133/#172/#183.
