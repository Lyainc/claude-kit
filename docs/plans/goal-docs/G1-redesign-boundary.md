---
goal_id: G1
title: 재설계 경계 확정 — 경계 A 명문화 + W5 reframe
issues: [99]
wave: 1
depends_on: []
recommended_model: opus
status: ready
created: 2026-06-03
---

# G1 — 재설계 경계 확정 (경계 A 명문화 + W5 reframe)

## 배경 / 목적

claude-kit 레이어 재설계(Epic #108)의 **foundation goal**이에요. 2026-06-02 전문가 패널이 만장일치로 합의한 **경계 A** — claude-kit은 ①인지 ②결정화·출력 ③딜리버리 ④지식베이스를 소유하고, ⑤실행(doing/오케스트레이션)은 OMC(harness)가 담당한다 — 를 설계 문서에 명문화하는 게 목적이에요.

지금 문제는 이거예요. OMC glue 제거(커밋 `3784031`)로 플러그인이 self-contained가 됐는데, "왜 self-contained인지", "어디까지가 claude-kit 책임인지"를 적어둔 명시 섹션이 없어요. 경계가 암묵 지식으로만 분산돼 있으면 OMC 제거 이후 규칙 drift가 나거든요. 게다가 `thinking-tools/docs/improvement-matrix.md`의 W5는 "사고 도구가 OMC ralph와 단절 = weakness"라고 적어둬서, 합의된 경계 A와 정면으로 모순돼요. 경계 A에서 이 단절은 *버그가 아니라 의도된 design boundary*거든요.

이 goal-doc은 두 가지 가치를 가져요.
1. **단일 출처(single source of truth)** — 헌법(constitutional)/정책(policy) 규칙 목록을 `## Design Principles` 한 곳에 정의해요. CLAUDE.md operating_principles의 "State each rule once" 원칙대로, #125(3-tier 규칙 시스템)는 이 목록을 *참조만* 하고 재정의하지 않아요.
2. **후속 의존의 전제** — #100(goal-doc linchpin)·#101(출력 어댑터 계약) 등 모든 redesign 이슈가 "경계 A가 선언됐다"를 전제로 착수해요. 이게 wave=1 foundation인 이유예요.

순수 문서 작업이에요. **코드 동작 변화 없음** — SKILL.md description·훅·스크립트 로직은 건드리지 않아요.

## 포함 이슈

- #99: docs: declare claude-kit↔OMC boundary (A) and reframe W5 — 경계 A를 설계 doc에 명문화하고, improvement-matrix W5 라인을 의도적 design boundary로 reframe. foundation, deps 없음.

> 참고: #99 본문 acceptance는 2줄(경계 A 명시 + W5 reframe)이지만, 이슈 코멘트 2건에서 acceptance가 확장됐어요. 아래 완료 조건은 본문 + 코멘트 확장분을 모두 통합한 거예요.

## 완료 조건 (Definition of Done)

### A. 경계 A 명문화 (수평축 — 책임 분담)

- [ ] 새 설계 문서 `docs/design/claude-kit-boundary.md`에 `## Design Principles` 섹션을 둬요. 이 섹션이 헌법/정책 목록의 **단일 출처**임을 문서 상단에 명시해요.
- [ ] 5-레이어 모델 표를 실어요: ①인지(diverse-sampling·unknown-discovery·expert-panel·adversarial-review) ②결정화·출력(spec-first·doc-concretize·doc-polish·graphify·note·issue) ③딜리버리(vault-bridge) ④지식베이스(obsidian-vault-manager) ⑤실행(OMC 영역). claude-kit은 ①②③④만 소유, ⑤는 OMC.
- [ ] 의존 방향 명시: "claude-kit 스킬 = OMC가 호출하는 leaf capability". (B안 — 루프 전체 흡수 — 기각 근거: OMC 중복 + 버전 동기화·유지보수 표면 폭발) 한 줄 기록.

### B. vault 철학 병기 (수직축 — 코멘트 1 확장분)

- [ ] 경계 A 서술과 함께 vault 철학 단락을 병기해요: **"Assist, never replace"** + **file-over-app**. (근거: CLAUDE.md 전체에 user-initiated/Write Role/type opt-in 패턴이 *암묵적*으로만 분산돼 있고 명시 철학 섹션이 없음 → OMC 제거 시 drift 위험.)

### C. 단방향 의존 + 규율 범위 (코멘트 2, 결정 2 확장분)

- [ ] Boundary A 서술에 **단방향 의존** 명문화: "harness → leaf"만 허용, 역방향(leaf가 harness API/동작을 import·call·assume) 무조건 금지. leaf는 independently installable + harness-neutral by construction.
- [ ] **규율 범위(scope of "one-way")** 명시: 이 규칙은 harness↔leaf 경계에만 적용. leaf 내부 cognitive layer 간 호출(예: ①인지 스킬이 ②출력 스킬 호출 — diverse-sampling Mode B → doc-concretize)은 ordinary module dependency로 **허용**. (이게 issue-skill=②출력 leaf 귀속과 diverse-sampling Mode B 합성을 정당화하는 근거.)

### D. 헌법/정책 분리 블록 (코멘트 2, 결정 3 — 단일 출처 핵심)

- [ ] 같은 `## Design Principles` 섹션에 헌법/정책 분리 블록을 추가해요. 이 목록이 단일 출처 — #125는 참조만.
- [ ] **Constitutional rules (immutable — harness·config 어느 쪽도 override 불가)** 목록:
  - vault writes: new-file-only, user-initiated slash command only
  - deterministic hooks: zero per-turn LLM cost
  - self-approval: prohibited in the same active context
  - goal-doc schema: stable harness-neutral contract (#100)
  - dependency direction: harness → leaf only, no reverse (intra-leaf calls exempt)
- [ ] **Policy rules (harness-overridable / config-gated)** 목록:
  - `VAULT_BRIDGE_WRITE_CONTRACT` (warn / enforce / off)
  - `VAULT_BRIDGE_STRICT_NAMING` strictness
  - model routing defaults (haiku / sonnet / opus)
  - Stop hook closing-keyword list
  - `snapshot_export` / `snapshot_import` opt-in gates

### E. W5 reframe (improvement-matrix)

- [ ] `thinking-tools/docs/improvement-matrix.md:53`의 W5 라인을 reframe해요. "OMC ralph와 단절 = weakness" 프레이밍을 *의도적 design boundary*로 전환. ID 재활용 금지 governance 준수 — W5 ID·행 위치는 유지하고, `notes`/`설명`에 reframe 사유 + `docs/design/claude-kit-boundary.md` 경계 A 교차 참조를 기재. (resolved/wontfix가 아니라 의미 재정의이므로 status 처리는 reframe에 맞게 선택 — 행 삭제 금지.)
- [ ] reframe 후에도 W5의 affected skills(spec-first, thought-chain) 컬럼·Phase 매핑(C)은 보존하거나, 경계 A에 맞춰 의미가 바뀐 부분만 명시 갱신.

### F. 무결성 게이트 (코드 동작 변화 없음 증명)

- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` 실행 시 trigger 제거가 없음(W5 reframe은 SKILL.md description을 건드리지 않으므로 트리거 변화 0이 기대값).
- [ ] `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` 통과 (문서 작업이라 영향 없어야 정상).

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| `## Design Principles` 섹션을 어느 파일에 둘까 | (a) 새 `docs/design/claude-kit-boundary.md` / (b) 루트 `CLAUDE.md`에 직접 / (c) 기존 design doc에 fold | **(a) 새 design doc** | CLAUDE.md는 contributor 운영 가이드라 헌법/정책 *정의*의 안정 출처로는 변동성이 커요. design doc은 설계 산출물 컨벤션(`docs/design/*.md`)에 맞고, #125·#100이 안정 경로로 참조하기 좋아요. CLAUDE.md에는 1줄 포인터만 추가하는 게 깔끔해요. |
| W5를 resolve 처리할까 reframe만 할까 | (a) `status: resolved` + `resolved_in` / (b) reframe(의미 재정의, ID·행 유지) / (c) `wontfix` + supersedes | **(b) reframe** | W5는 "해결된 부채"가 아니라 "애초에 부채가 아니었다(의도된 경계)"예요. resolved는 "고쳤다"는 의미라 부정확하고, wontfix는 "안 고친다"라 뉘앙스가 또 달라요. governance가 ID 재활용을 금지하니 행은 유지하고 설명/notes만 reframe하는 게 맞아요. |
| 헌법 목록을 여기서 *완결*할까, #125에 일부 위임할까 | (a) 여기 단일 출처 완결 / (b) 분산 정의 | **(a) 단일 출처 완결** | 결정 3 + CLAUDE.md "State each rule once". 분산하면 drift·모순이 나요. #125는 (1) 3-tier 레이어 구조 + (2) 안전판 4종만 다루고 헌법/정책 *목록*은 여기를 참조해요. |
| goal-doc schema를 헌법에 넣는데 #100이 아직 미설계 | 헌법 항목으로 선언하되 spec은 forward-ref / 헌법에서 빼기 | **선언 + forward-ref** | 경계 A의 핵심이 "goal-doc = harness-neutral glue contract"예요. schema 세부는 #100 소관이지만, "stable harness-neutral contract여야 한다"는 *제약*은 foundation에서 못 박아야 #100이 그 제약 안에서 설계해요. (#100 → #99 의존의 실체.) |

**미해결 질문(open):** vault 철학 단락의 "file-over-app" 출처 표기 — kepano(Obsidian) 원전을 cite할지, claude-kit 내부 v4 설계(`docs/design/vault-second-brain-v4.md`)만 참조할지. 권장: 내부 v4 doc 참조 + 한 줄 origin 주석. 비차단(non-blocking) — 슬라이스 S2에서 작성자 재량.

## 슬라이스 순서

1. **S1 경계 doc 골격 + 경계 A·vault 철학** → 바인딩: `doc-concretize` (신규 구조화 저작) | 대상 파일: `docs/design/claude-kit-boundary.md`(신규) | 산출: 문서 헤더(상태·작성일·출처=`docs/discussions/20260602_claude-kit-layer-redesign/`) + `## Design Principles` 섹션 + 5-레이어 표 + 의존 방향 + B안 기각 1줄 + vault 철학 단락("Assist, never replace" + file-over-app) | 검증: DoD A·B 체크리스트 항목 충족, 문서가 self-contained하게 읽히는지.

2. **S2 단방향 의존 + 헌법/정책 분리 블록** → 바인딩: `doc-concretize` (S1 문서 이어쓰기) | 대상 파일: `docs/design/claude-kit-boundary.md` | 산출: 단방향 의존 + scope-of-one-way(intra-leaf 면제) 단락 + Constitutional/Policy 두 목록 블록(코멘트 2 원문 5+5 항목) + "이 섹션이 단일 출처, #125는 참조만" 명시 | 검증: DoD C·D 충족, 헌법 5항목·정책 5항목 누락 없음.

3. **S3 W5 reframe** → 바인딩: `executor` (정밀 1-라인 편집) | 대상 파일: `thinking-tools/docs/improvement-matrix.md` (라인 53) | 산출: W5 설명/notes를 "의도된 design boundary"로 reframe + `docs/design/claude-kit-boundary.md` 경계 A 교차 참조 삽입. ID·행 위치·affected skills 컬럼 보존(governance) | 검증: DoD E 충족, ID 재활용·행 삭제 없음, `git diff`가 라인 53(+필요시 notes)만 건드리는지.

4. **S4 CLAUDE.md 포인터 + 교차참조 연결** → 바인딩: `executor` | 대상 파일: 루트 `CLAUDE.md` (해당 시 `.claude/CLAUDE.md`는 건드리지 않음 — 운영 가이드 분리) | 산출: claude-kit↔OMC 경계의 단일 출처가 `docs/design/claude-kit-boundary.md`임을 1줄 포인터로 추가(중복 정의 금지, 참조만). #125·#100·#101이 참조할 안정 경로 확정 | 검증: 포인터가 *참조*이지 *재정의*가 아닌지(State each rule once), 깨진 상대경로 없는지.

5. **S5 리뷰 패스** → 바인딩: `code-reviewer` (문서 정합성·교차참조·governance) + 필요 시 `expert-panel`(경계 A 서술이 2026-06-02 합의를 왜곡 없이 반영하는지) | 대상 파일: 위 전부 | 산출: 헌법/정책 목록이 코멘트 2 원문과 1:1 대응하는지, W5 reframe이 경계 A와 모순 없는지, 단일 출처 위반(어딘가 재정의) 없는지 검토 의견 | 검증: self-approval 금지 — S1~S4 저작 컨텍스트와 분리된 리뷰 패스로 수행.

## E2E 자가검증

```bash
# 1. trigger-regression: W5 reframe이 SKILL.md description을 건드리지 않았음을 증명 (트리거 제거 0 기대)
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main

# 2. JSON 매니페스트 무결성 (문서 작업이라 영향 없어야 정상)
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "tt plugin.json OK"

# 3. 신규 경계 doc 존재 + 핵심 섹션·항목 존재 확인
test -f docs/design/claude-kit-boundary.md && echo "boundary doc exists"
grep -q "Design Principles" docs/design/claude-kit-boundary.md && echo "section present"
grep -qi "Assist, never replace" docs/design/claude-kit-boundary.md && echo "vault philosophy present"
grep -q "harness → leaf" docs/design/claude-kit-boundary.md && echo "one-way dependency present"
grep -qi "Constitutional rules" docs/design/claude-kit-boundary.md && echo "constitutional block present"
grep -qi "Policy rules" docs/design/claude-kit-boundary.md && echo "policy block present"

# 4. 헌법 5항목·정책 5항목 누락 검사 (코멘트 2 원문 키워드)
for k in "new-file-only" "deterministic hooks" "self-approval" "goal-doc schema" "dependency direction"; do
  grep -qi "$k" docs/design/claude-kit-boundary.md && echo "constitutional: $k OK" || echo "MISSING: $k"
done
for k in "VAULT_BRIDGE_WRITE_CONTRACT" "VAULT_BRIDGE_STRICT_NAMING" "model routing" "closing-keyword" "snapshot_"; do
  grep -qi "$k" docs/design/claude-kit-boundary.md && echo "policy: $k OK" || echo "MISSING: $k"
done

# 5. W5 reframe: 행 유지 + 경계 doc 교차참조 확인 (ID 재활용·행 삭제 금지)
grep -q "| W5 |" thinking-tools/docs/improvement-matrix.md && echo "W5 row preserved"

# 6. 단일 출처: CLAUDE.md는 포인터(참조)만 — 헌법 목록 *재정의* 없음 확인
grep -q "claude-kit-boundary.md" CLAUDE.md && echo "pointer added"
```

- 통과 기준: (1) trigger-regression self-test "OK: all 9 self-test cases passed" + origin/main diff에서 trigger 제거 0건. (2) 두 JSON 모두 OK. (3) 6개 grep 전부 present. (4) 헌법 5/정책 5 모두 "OK"(MISSING 0). (5) W5 행 보존. (6) CLAUDE.md 포인터 존재하되 헌법/정책 목록 본문은 boundary doc에만(CLAUDE.md에 5+5 목록 중복 없음 — 수동 확인). **코드 동작 변화 0** = 모든 변경이 `.md` 파일에 한정(`git diff --stat`로 `*.md` 외 변경 없음 확인).

## 의존성 / 순서 주의

- **선행 goal: 없음.** 이 goal-doc이 wave=1 foundation이에요. depends_on=[].
- **이 goal이 막고 있는 것(blocks):**
  - **#100 (goal-doc linchpin)** — "goal-doc = stable harness-neutral contract"라는 헌법 제약이 여기서 확정돼야 그 안에서 schema를 설계해요. #100의 deps에 #99.
  - **#101 (출력 어댑터 계약)** — ②출력 레이어 귀속(issue-skill=②, diverse-sampling Mode B 합성 허용)이 여기 단방향 규율 범위에 근거해요. #101의 deps에 #99.
  - **#125 (3-tier 규칙 시스템)** — 헌법/정책 *목록*을 여기 `## Design Principles`에서 참조해요. 재정의 금지. #125 acceptance에 "헌법/정책 목록은 #99 참조만"이 명시돼 있어요.
- **착수 조건:** 없음(즉시 착수 가능). 단 S5 리뷰 패스는 S1~S4 저작과 **분리된 컨텍스트**에서 수행 — CLAUDE.md "No self-approval in the same active context".
- **크로스청크 게이트:** 이 goal 완료가 wave=2 이상(#100/#101/#125) 착수의 게이트예요. 경계 A·헌법/정책 단일 출처가 머지되기 전에는 후속 redesign goal을 시작하지 않는 게 안전해요. 그래야 단일 출처가 흔들리지 않거든요.
