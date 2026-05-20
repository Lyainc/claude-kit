---
status: frozen
frozen_at: 2026-04-19
tracking_continued_in: thinking-tools/docs/improvement-matrix.md
note: "본 문서는 토론 시점 스냅샷. 진행 상태는 매트릭스 참조."
---

# Analysis — Ouroboros 통합 아이디어 및 thinking-tools 개선안

**Date**: 2026-04-19
**Status**: frozen (idea-level analysis snapshot)
**Trigger**: 사용자가 `thinking-tools/unknown-discovery`와 [Q00/ouroboros](https://github.com/Q00/ouroboros) 심층 비교 요청. 이후 파생된 두 개의 추가 질문이 본격적 개선 논의로 확장됨.

---

## 1. 맥락 (Conversation Genesis)

세 개의 질문이 순차적으로 제기되었음:

1. `/unknown-discovery` vs Ouroboros 심층 비교
2. unknown-discovery를 발전시킬 아이디어 + Ouroboros 경량 버전을 thinking-tools에 포함시키는 방법
3. 그 외 thinking-tools 스킬·에이전트 개선 아이디어 + Ralph 루프를 OMC와 결합해 재현 가능한지 여부

본 문서는 대화에서 도출된 아이디어를 **아이디어 레벨**로 정리함. 구체적 실행 계획은 `dev-plan.md` 참조.

---

## 2. unknown-discovery vs Ouroboros — 핵심 비교

### 2.1 결론

같은 "Socratic 인터뷰" 외피를 쓰고 있지만 목적·아키텍처·출력물이 완전히 다른 도구. 겹치는 것처럼 느껴지나 실제로는 **보완재**에 가까움.

### 2.2 비교 표

| 축 | unknown-discovery | Ouroboros |
|----|-------------------|-----------|
| 목적 | 기존 계획의 blind spot 발굴 (진단/비판) | 모호한 아이디어를 검증된 코드베이스로 (생성/구축) |
| 범위 | Interview 1단계 | Interview → Seed → Execute → Evaluate → Evolve 5단계 루프 |
| 배포 형태 | Markdown skill 1개 | Python 3.12+ 패키지 + MCP 서버 + 플러그인 |
| 상태 관리 | 대화 내 STATE 블록 (옵션으로 MD 저장) | SQLAlchemy + aiosqlite 이벤트 소싱, 세션 간 복원 |
| 점수 체계 | 4-영역 × 0-100% 규칙 기반 자가채점 | LLM 채점(temp 0.1) × 3-4 차원 Ambiguity 0.0-1.0 |
| 종료 게이트 | Depth ≥ 65% + 포화 감지 | Ambiguity ≤ 0.2 + 차원별 floor + 연속 2회 달성 |
| 질문 생성 | 영역별 고정 패턴 + Challenge Modes (Inverter/Outsider/Pre-mortem) | LLM 생성, 5개 내부 perspective |
| 코드베이스 인지 | 없음 (순수 대화) | Brownfield explorer, PATH 1a 자동 확정 |
| 출력물 | 사람이 읽는 Discovery Report | 기계가 소비하는 immutable YAML Seed spec |
| 후속 단계 | 사용자에게 반환 (expert-panel 연계 옵션) | Double Diamond 실행 → 3-stage 평가 → 진화 루프 |
| 비용 | 0 (추론 외 인프라 없음) | LLM 호출비 + 인프라 (PAL Router 티어링으로 완화) |
| 철학 | 부정적 Socratic ("무엇이 빠졌는가") | 구성적 Socratic ("무엇을 만들 것인가") |

### 2.3 핵심 관찰

- **점수의 성질이 정반대**: unknown-discovery Depth는 *탐색이 충분한지*를 측정, Ouroboros Ambiguity는 *명세가 단단한지*를 측정. 외형은 비슷한 gate지만 의미가 다름.
- **구조적 겹침은 인터뷰 표면뿐**: 4 Core Area (Assumptions/Trade-offs/Edge Cases/Blindspots)는 Ouroboros 4차원 (Goal/Constraint/Success/Context)과 발상이 유사하지만, 전자는 *리스크 영역*이고 후자는 *명세 차원*.
- **Challenge Modes는 unknown-discovery의 차별점**: Inverter/Outsider/Pre-mortem을 인터뷰 타임라인상 특정 라운드에 자동 주입하는 구조는 Ouroboros Contrarian 페르소나보다 타이밍 측면에서 더 정교함.

### 2.4 언제 뭘 쓰나

- **기존 기획·결정·코드 검토**: unknown-discovery 한 번이면 충분. 가볍고 하루 안에 종료.
- **제로부터 스펙 + 실제 빌드**: Ouroboros가 적합. 인터뷰만 떼어 쓰면 오버엔지니어링.
- **둘 다 유용한 흐름**: Ouroboros `interview`로 Seed → `/unknown-discovery`로 Seed 구멍 점검 → 수정 후 `run`. 이론상 가능하나 실제 파이프라인 사례는 부재.

---

## 3. unknown-discovery 발전 아이디어

### 3.1 현재 구조의 약한 고리

| 이슈 | 내용 |
|------|------|
| 자가채점 편향 | Depth 점수를 LLM이 스스로 평가 → "65% 찍고 넘어가자" 유혹 |
| 코드베이스 블라인드 | "마이크로서비스 전환 검토"라고 해도 실제 repo 미열람 |
| 발견 우선순위 수치 부재 | Critical/Important는 감각 판정, 벤치마킹 불가 |
| Challenge Modes 1회성 | Ouroboros Contrarian은 always-on, 현재는 타이밍 주입만 |
| 출력이 기계 비친화적 | Markdown Report가 후속 스킬 파싱에 애매 |

### 3.2 개선안 (우선순위 순)

1. **Seed frontmatter 출력** — Discovery Report 상단에 YAML로 `findings: [{id, priority, impact, likelihood, rationale, action}]` 블록. 기계 소비 가능.
2. **Codebase grounding 옵션** — `--with-repo <path>` 플래그. Phase 0에서 `plugin.json`, `pyproject.toml`, `README.md`만 훑어 질문 패턴에 주입. 저비용 고효과.
3. **LLM-scored Depth** (temp 0.1) — 규칙 기반 채점을 LLM 채점으로 교체, 점수 근거 기록. 단, LLM이 점수 일관성을 유지 못하면 진행 꼬임 리스크 존재.
4. **Contrarian track 상시 주입** — Core 4와 별개로 매 영역 완료 후 1Q "이 발견을 반증할 근거는?" 추가. Challenge Modes는 그대로 유지.
5. **Impact × Likelihood 수치화** — Critical 라벨을 `impact(1-5) × likelihood(1-5) ≥ 15`로 정의.
6. **Gap-check 반복** — Phase 2 이후 발견 목록을 자기 입력으로 1라운드 재질문 (Ouroboros Evolve의 mini 버전).
7. **세션 간 복원 기본값화** — 현재 옵션인 파일 저장을 기본 동작으로 전환.

**가성비 최고는 1·2·4**. 3번은 리스크 있음.

---

## 4. Ouroboros 경량 버전 in thinking-tools

### 4.1 전제

OMC에는 이미 `deep-interview` 스킬이 존재함 (Ouroboros-inspired, mathematical ambiguity gating, `deep-interview → ralplan → autopilot` 파이프라인). OMC 레이어에서는 이미 landed.

thinking-tools에 별도로 넣을 이유:
- thinking-tools는 OMC 없이도 쓸 수 있는 **독립 마켓플레이스 플러그인**이므로 vendor-neutral 버전 필요
- OMC deep-interview는 파이프라인 지향(실행까지), thinking-tools는 **사고 도구** 지향이므로 *spec만 뽑고 끝*인 버전이 제자리

### 4.2 경량 버전 설계 — 신규 스킬 `spec-first` (가칭)

| 포함 | 제외 |
|------|------|
| Socratic 인터뷰 + 4차원 Ambiguity 채점 (Goal/Constraint/Success/Context) | Seed 실행 엔진 (Execute phase) |
| Ambiguity ≤ 0.2 gate + 차원별 floor | 3-stage Evaluate gate |
| YAML Seed spec 출력 (`docs/specs/{slug}.yaml`) | Evolve 루프의 수학적 convergence |
| Brownfield 감지 (repo 루트 manifest만) | LiteLLM 어댑터, PAL Router, 이벤트 소싱 |
| Double Diamond 나레이션 (Discover/Define 단계 체크인) | Double Diamond 자동 분해 |

### 4.3 unknown-discovery와의 MECE

- `unknown-discovery`: **기존 계획 검토** (진단, destructive)
- `spec-first`: **모호한 아이디어를 명세로** (생성, constructive)
- 둘은 겹치지 않음. 연쇄 가능: spec-first → unknown-discovery (뽑은 Seed의 구멍 점검)

### 4.4 구현 비용 감각

SKILL.md 하나 + 채점 루브릭 + YAML 템플릿. 약 300-500줄 Markdown. Python 런타임이나 MCP 서버 없이 `AskUserQuestion` + `Write`만으로 Ouroboros Interview 가치의 **70-80%** 이전 가능.

### 4.5 경고

"경량 버전"을 만들다 보면 자꾸 기능을 더 넣고 싶어짐. Ambiguity 게이트 하나만 핵심 가치이고, 나머지(멀티모델 합의, Ralph 루프, drift 감지)는 **얻을 수 없는 것들**이 Ouroboros의 Python 패키지 이유. 선을 분명히 긋지 않으면 또 하나의 Ouroboros 재구현이 되어버림.

---

## 5. Ralph 루프 재평가 — OMC 결합 시나리오

### 5.1 사용자의 지적

"멀티모델이나 drift 감지는 외부 인프라 필요라 치더라도, **Ralph 루프는 OMC와 결합하면 가능하지 않냐**"는 질문. 초기 분석에서 이 가능성을 과소평가했음.

### 5.2 재평가 결과

맞음. Ralph의 핵심은 "iterate with verification until converged"이고 이는 OMC의 `ralph` 스킬로 위임 가능. thinking-tools는 spec을 만들고, OMC는 반복 실행을 맡는 구조.

### 5.3 Ouroboros 기능별 실현 가능성 재정리

| Ouroboros 기능 | thinking-tools 단독 | OMC 결합 시 |
|---------------|-------------------|------------|
| Interview + Ambiguity gate | ✅ | ✅ |
| Seed spec 생성 | ✅ | ✅ |
| Double Diamond 실행 분해 | ⚠️ 나레이션만 | ✅ autopilot이 처리 |
| **Ralph 루프 (verification까지)** | ❌ | **✅ omc:ralph로 위임** |
| Multi-Model Consensus | ❌ 단일 LLM | ⚠️ omc:ccg로 근사 |
| Ontology 수렴 감지 (0.95) | ❌ | ⚠️ omc:ralph verifier loop으로 근사 |
| Drift 측정 (3요소 가중) | ❌ | ❌ (외부 엔진 필요) |

### 5.4 통합 설계

```
thinking-tools/spec-first (vendor-neutral 코어)
  ├── Phase 1-3: Interview → Ambiguity gate → Seed YAML
  └── Phase 4 (conditional): OMC detected?
        ├── YES: Seed를 OMC PRD 포맷으로 변환 후 omc:ralph 핸드오프
        │        → Ralph가 verifier loop 돌며 AC 통과까지 반복
        └── NO: Seed YAML 파일로만 출력, 사용자에게 "다음 단계는 직접" 안내
```

### 5.5 Ouroboros Evolve의 경량 근사

완전한 ontology 수렴(유사도 0.95)은 Python 엔진 없이 불가. 단, 다음 루프로 90% 유사 근사 가능:

```
Loop:
  1. spec-first로 Seed v(n) 생성
  2. omc:ralph로 실행 → 실행 중 드러난 모호성/누락 artifact로 기록
  3. spec-first --refine <Seed v(n)> <execution-log> → Seed v(n+1)
  4. Ambiguity(Seed v(n+1)) - Ambiguity(Seed v(n)) < ε → 수렴, 종료
```

Ontology 비교가 아닌 ambiguity 수렴을 기준으로 함. 수학적으로는 다르지만 실용적으로는 동일한 효과.

### 5.6 벤더 중립성 유지 원칙

- thinking-tools 스킬은 OMC를 **hard-require하지 않음**
- OMC 감지 시 기능 증폭, 없으면 기본값 (Seed까지)
- 확장 포인트: `--handoff-format=omc|openclaw|custom`

---

## 6. 기타 thinking-tools 스킬·에이전트 개선 아이디어

### 6.1 즉시 고쳐야 할 버그

**`agents/thinking-facilitator.md`의 `skills:` frontmatter에 `adversarial-review`가 누락**되어 있음. Decision Tree와 Signal Keywords 표에도 없음. 라우팅 에이전트가 이 스킬의 존재를 인지하지 못함.

### 6.2 스킬별 개선안

**diverse-sampling**
- 확률값 calibration 미검증 — LLM probability의 실제 선호도 반영 약함
- 중복 필터 부재 — k개 중 의미적으로 유사한 게 섞이면 다양성 기법 의미 상실
- Tournament 모드 — Ouroboros Evolve 차용, `--tournament`: k 생성 → top 2 선택 → mutate → 다시 k

**doc-concretize**
- Verify 단계가 자가검증 (같은 컨텍스트) — 별도 세션 verifier 위임 권장 (OMC `verifier` 에이전트 활용 가능)
- WebFetch가 옵션 — 사실 기반 문서에서는 강제여야 함, `--fact-heavy` 모드 플래그
- Quick Mode 임계값 800자가 임의적 — 문서 유형(spec/report/blog/readme) 기반 분기 권장

**doc-polish**
- `--fix` 직접 적용이 위험 — `--diff-preview` 모드 추가 (승인 후 적용)
- llm-expression-blacklist 유지보수 부담 — AI 문체 진화에 따라 정적 룰셋 노후화, 주기적 갱신 프로세스 필요
- Voice preservation 모드 부재 — reference 문서 voice 학습 후 deviation 경고

**expert-panel**
- 모든 전문가가 같은 LLM 세션 = 구조적 groupthink — 각 expert를 sub-agent로 spawn 시 완화 (temperature variation, separate context)
- Tie-break confidence가 self-reported — 같은 모델이 자기 confidence를 정직하게 매길 이유 없음. adversarial-review의 Judge 분리 패턴 도입
- Transcript 필수 생성 = 토큰 비용 — 짧은 세션에 `--brief` 플래그

**adversarial-review**
- Judge와 Attacker가 같은 모델·컨텍스트 — 스킬 자체에서 경고하지만 분리 보장 없음, sub-agent spawn 명시화
- Round-5 고정 — defense 압도적일 때 조기 종료 조건 부재, 초기 3라운드 평균 delta 낮으면 종료
- 공격 템플릿 정적 — 도메인별 attack bank 추가 시 날카로워짐
- unknown-discovery와 미연결 — Critical 발견의 claim 자동 변환 연계 부재

**thought-chain**
- adversarial-review 미포함 — 현재: discovery → panel → concretize → polish. 개선: **discovery → adversarial-review → panel → concretize → polish**
- Stage 1 empty 시 조기 종료 없음
- 완전 직렬 실행 — 부분 결과로 Stage 2 준비 파이프라이닝 여지

**thinking-facilitator 에이전트**
- Decision Tree가 flat keyword match — 복합 의도 감지 불가 ("대안 생성하고 각각 공격해줘" → diverse-sampling + adversarial-review)
- adversarial-review 미등록 (6.1 참조)

### 6.3 공통 개선 축

| 축 | 현재 | 개선 |
|----|------|------|
| 출력 포맷 | Markdown 서사체 | YAML frontmatter + MD body (기계 파싱) |
| STATE 블록 | 스킬마다 포맷 상이 | 공통 스키마로 통일 |
| 자가검증 | 모든 스킬이 self-check | 독립 verifier 패스 표준화 |
| 스킬 간 데이터 전달 | 자연어 중계 | 구조화된 handoff 프로토콜 |

---

## 7. 미결정 이슈 (Open Questions)

| # | 이슈 | 현재 의견 |
|---|------|----------|
| Q1 | `spec-first` 스킬명 확정 | 후보: spec-first, seed-crystallize, crystallize. 결정 필요. |
| Q2 | unknown-discovery와 spec-first를 별도 스킬로 vs 모드 플래그(`--mode=discover\|spec`)로 통합 | 별도 권장 (overloading 회피) |
| Q3 | OMC 감지 로직 | `ls ~/.claude/plugins/oh-my-claudecode` 체크로 시작, 개선은 추후 |
| Q4 | Seed YAML vs OMC PRD JSON 매핑 스펙 | 상세 필드 매핑 정의 필요 |
| Q5 | LLM-scored Depth 도입 시 fallback | 규칙 기반 점수를 secondary로 유지할지 |
| Q6 | thinking-facilitator adversarial-review 등록이 breaking change인지 | 신규 등록이므로 breaking 아님, 즉시 적용 가능 |
| Q7 | `--evolve` 루프 상한 | Ouroboros는 30 generations. 경량 버전은? (3-5 권장) |

---

## 8. Action 후보 요약

구체적 작업 계획은 `dev-plan.md`로 분리. 본 문서는 아이디어 수준 분석에 한정.

- **Phase A (Quick Win)**: thinking-facilitator 버그 수정 + unknown-discovery YAML frontmatter 추가
- **Phase B (Core)**: `spec-first` 신규 스킬 개발 + OMC ralph 핸드오프
- **Phase C (Expansion)**: 기타 스킬 개선 (`adversarial-review` Judge 분리 등)
- **Phase D (Integration)**: thought-chain 재구성 + 공통 YAML 출력 포맷 표준화
