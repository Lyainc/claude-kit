# G18 S1 — 발견↔매립 경계 명세 (feature-full spec_artifact)

> **역할**: feature-full.js(#201) 워크플로의 `spec_artifact`. S2 impl(executor)이 이걸
> implementation contract로 삼아 `feedback-loop/skills/distill/SKILL.md`를 재구조화해요.
> **방향 단일출처**: consensus 게이트 verdict(C1~C7, `G18-distill-role-split.md` "쟁점과
> 트레이드오프 > consensus 게이트 verdict" 섹션). 이 spec은 그 verdict를 *distill SKILL.md
> 재구조화 청사진*으로 번역해요(중복 최소 — verdict가 근거, 이 문서가 실행 지시).

## 1. distill 출력 계약 — 자연어 제안 객체 (C2)

distill의 산출 = 매립 엔진(G19, add-policy lineage)이 소비할 **자연어 제안**. shape는 직렬
스키마가 아니라 **산문(shape category)**이고, 다음 필수정보를 담아요 — *직렬 필드 구조·format은
소비자(G19) 생길 때 확정*(C2: 지금 프리징하면 검증할 소비자가 없어 YAGNI):

- **무엇을 (what)**: 재사용 절차 기법 한 줄 — 규칙/기법의 내용.
- **왜 (why)**: 안 캡처하면 뭐가 손해인가 — 재사용 가치. (add-policy §5 엔트리 템플릿 What/Why 역산.)
- **세션 근거 (provenance context)**: 어느 세션 패턴에서 반복 관찰됐나.
- **inviolability 판단 (C4)**: 기존 스킬 X를 patch하는 제안이면 X가 user-authored(불가침)인가 —
  이 판단은 **발견 측 책임**이고, 매립 엔진이 덮어쓰면 안 되는지를 제안 객체가 운반.

distill은 격자 슬롯(layer/scope/tier/channel)을 **채우지 않아요** — 매립 엔진이 자연어를 받아
분류를 *자기가* 재실행해요(add-policy §1/§2). 슬롯을 미리 채우면 매립 분류 책임을 침범(C5).

## 2. Phase별 책임 식별표 (발견 잔류 / 매립 이관 / 면 분할)

| Phase | 현재 동작 | G18 후 귀속 | 근거 |
|-------|----------|------------|------|
| 1 SCAN | 후보 식별 + anti-capture 필터 | **발견 잔류** | "무엇을"의 판단 |
| 2 PRIORITIZE | patch>extend>reference>new 매립지 판단 | **매립 이관(명세상)** — transition 동안 잠정 유지 + 매립 책임 마킹 | "어디에" = 매립(T2, add-policy §3 배치 규칙) |
| 3 GATE | AskUserQuestion(기법 + action + target) | **면 분할** — "이 제안 넘길까"=발견 잔류 / "action+target 확인"=매립 결정(G19 1클릭) | C5 |
| 4 WRITE | 실제 Edit/Write | **매립 이관** — transition 봉인표식 달고 잠정 유지, G19 흡수 시 제거 | T1(a)·C6 |
| 5 SELF-CHECK | 작성 검증 | **면 분할** — 산물검증(frontmatter 파싱 등)=매립 / 자리검증("읽히는 자리 맞나")=발견 씨앗 | C3, SUMMARY §5(c) |
| provenance/inviolability | Phase 4 내부 | **판단=발견 잔류**(제안 객체 운반) / 마커 기계적 write=매립 | C4 (안전 불변식) |

## 3. distill SKILL.md 재구조화 청사진 (S2가 따를 것)

### 3.1 새 경계 섹션 추가 — sentinel anchor (C1)

`## Pipeline: SCAN → ...` 앞에 발견↔매립 경계 섹션을 추가. **두 sentinel 앵커 필수**(E2E 가드 C1
가 이 둘을 grep으로 확인 — 리팩터됨 vs 무변화를 구분):
- 섹션 제목/마커에 리터럴 `DISCOVER-LANDFILL-BOUNDARY`
- 본문에 리터럴 `landfill responsibility`

영어 body(language policy). 골자(S2가 다듬되 두 앵커·명제는 보존):

```markdown
## Discovery ↔ landfill boundary (DISCOVER-LANDFILL-BOUNDARY)

distill is the DISCOVERY half of the recursive-improvement loop (#251): it judges
*what* is a class-level reusable technique and emits a **natural-language proposal**
(what / why / session-provenance / inviolability judgment — §"output contract").
Deciding *where and how* to embed — placement classification (patch>extend>reference>
new) and authoring — is the **landfill responsibility** of the general engine (G19,
add-policy lineage), NOT distill. The proposal is the engine's input interface; distill
never fills the classification grid (the engine re-runs that itself).

During the transition (G19 not yet built) distill provisionally retains WRITE behind a
sealed marker (Phase 4) so discovery stays non-regressing until the landfill engine
absorbs it. This is a *managed* transition, not the terminus (C6).
```

### 3.2 Phase별 마킹 (§2 표대로)

- **Phase 2**: "placement decision = landfill responsibility (G19); provisionally retained
  during transition" 주석. 로직은 그대로(코드 이관은 G19 — T2).
- **Phase 3 GATE**: "이 제안을 넘길까"(발견 게이트, 잔류) vs "action(patch/extend/new) + target
  확인"(매립 결정 — G19 1클릭 게이트로 이관 표시) 면 분할 명시(C5). transition 동안은 잠정 동거 OK.
- **Phase 4 WRITE**: 봉인표식 추가 — 예: `> PROVISIONAL (transition): WRITE is landfill
  responsibility; G19 removes it once the engine absorbs authoring (C6).` G19의 명시 제거 대상화.
- **Phase 5 SELF-CHECK**: 산물검증("frontmatter parses, name kebab, body non-empty" → 매립
  부속) vs 자리검증("is this the place that actually gets read?" → 발견 씨앗, SUMMARY §5(c)
  매립후검증의 출발점) 면 분할 명시(C3). 자리검증 발상은 발견 쪽에 보존.

### 3.3 안전 불변식 보존 (C4 — 절대 손실 금지)

현재 Phase 4의 `provenance: distilled` 마커 + "user-authored skills are inviolable / never
overwrite" 규칙을 재저작 중 **떨구지 않아요**. inviolability *판단*("이 스킬 건드려도 되나")은
발견 측에 명시(제안 객체가 운반), 마커의 기계적 *write*만 매립 표시. 리터럴 `inviolable` /
`user-authored` 토큰이 SKILL.md에 잔존해야 E2E (2c) 통과 — 안전 불변식 회귀 차단.

### 3.4 trigger 보존 (C7)

`description`의 trigger 문구('증류', 'distill' 등) 보존 필수(#251 발견 시작점). description을
바꾸면 marketplace 동기화 필요(`check-version-sync.py --fix`). E2E (2b)가 결정적 확인.

### 3.5 비퇴행 (T1·DoD)

distill은 제안 단계까지 비퇴행 — WRITE 잠정 유지라 사용자가 distill 호출 시 기존처럼 동작해요.
단 경계 섹션이 "제안이 1차 산출, WRITE는 transition"임을 명시해서, 명세상 발견/매립이 갈린 상태.
순수 가감: 경계 섹션·마킹 추가로 단기엔 byte가 늘지만(critic 지적), 이건 *명세상* 분리고 코드
제거(얇아짐)는 G19가 WRITE를 흡수할 때 — "얇게"는 G18 완료가 아니라 루프 완성 시점의 약속.

## 4. S2 완료 검증 = G18 §E2E 자가검증 블록

(1) frontmatter stdlib 파싱 / (2) sentinel 앵커 2개 / (2b) trigger / (2c) inviolability /
(3) language-policy / (4) type-optin / (5) version-sync. **전부 통과해야 S2 완료.**

## 5. S3 격리 critique 입력 (CON-3)

S2 산출(distill SKILL.md diff)을 **별도 컨텍스트 reviewer**가 검토 — 경계 정합(발견/매립이
깨끗이 갈렸나) + distill 비퇴행 + 안전 불변식 보존 + CON-3/CON-5 정합. **VERDICT: APPROVE 필요**.
REJECT면 S2 fix 라운드. verdict는 G18 "consensus 게이트 verdict" 섹션 아래 S3 항목으로 기록.
