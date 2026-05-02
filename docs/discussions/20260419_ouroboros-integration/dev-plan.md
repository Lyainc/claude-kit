# Development Plan — Ouroboros 통합 + thinking-tools 개선

**Date**: 2026-04-19
**Based on**: [`analysis.md`](./analysis.md)
**Status**: Draft (pending review)
**Target**: thinking-tools plugin (`thinking-tools/`)

---

## 0. 스코프와 목표

### 0.1 In-Scope

- thinking-tools 플러그인 내 스킬·에이전트 개선
- 신규 스킬 `spec-first` 개발 (Ouroboros 경량 버전)
- OMC `ralph`와의 선택적 핸드오프 설계
- 공통 출력 포맷(YAML frontmatter) 표준화

### 0.2 Out-of-Scope

- Ouroboros 본체 통합 또는 포크
- Python 런타임 의존 기능 (멀티모델 합의, drift 측정)
- OMC hard-dependency (thinking-tools는 stand-alone 유지)
- OVM·vault-bridge 플러그인 변경

### 0.3 성공 기준

- thinking-tools 단독 사용자에게 spec-first 워크플로우 제공
- OMC 병행 사용자에게 `spec-first → ralph` 자동 체인 옵션 제공
- 기존 스킬 모든 호환성 유지 (breaking change 없음)
- 신규 스킬 평균 1일 내 ramp-up (기존 스킬 학습 곡선 유지)

---

## 1. Phase 구분

| Phase | 주제 | 기간 감각 | 산출 |
|-------|------|---------|------|
| A | Quick Win (버그 + 핵심 enhancement) | 0.5일 | v0.x.1 패치 릴리스 |
| B | Core Feature (`spec-first` 신규 스킬) | 2-3일 | v0.(x+1).0 마이너 릴리스 |
| C | OMC 통합 (`--with-ralph`) | 1일 | v0.(x+1).1 패치 릴리스 |
| D | Expansion (타 스킬 개선) | 3-5일 | v0.(x+2).0 |
| E | Integration (thought-chain 재편 + 포맷 표준화) | 2일 | v0.(x+3).0 |

Phase 간 의존성: **A → B → C (B의 Seed 포맷이 C의 PRD 변환 입력)**; D·E는 A 이후 언제든 병행 가능.

---

## 2. Phase A — Quick Win

### A1. `thinking-facilitator.md` 버그 수정

**문제**: `skills:` frontmatter에 `adversarial-review` 누락, Decision Tree·Signal Keywords 표에도 없음.

**작업**:
- `agents/thinking-facilitator.md` frontmatter `skills:` 리스트에 `adversarial-review` 추가
- Decision Tree에 분기 추가:
  ```
  ├── Claim attack/survival verdict? ────────────▶ adversarial-review
  │   (반증, 공격, steelman, survival score)
  ```
- Signal Keywords 표에 `adversarial-review` 행 추가
- Multi-Skill Detection 예시 갱신

**검증**: "이 주장을 공격해줘" 입력 시 facilitator가 adversarial-review를 라우팅 옵션으로 표시하는지 수동 확인.

**Effort**: < 30분

### A2. `unknown-discovery` Seed frontmatter 출력

**문제**: Discovery Report가 Markdown 서사체라 기계 파싱 어려움, 후속 스킬 체이닝 비친화적.

**작업**:
- `skills/unknown-discovery/templates/DISCOVERY_REPORT.md` 상단에 YAML frontmatter 블록 추가:
  ```yaml
  ---
  target: <name>
  domain: <tech|biz|creative>
  maturity: <idea|plan|execution>
  depth: <weighted_avg_pct>
  questions: <count>
  findings:
    - id: f1
      priority: critical|important|nice-to-have
      category: assumption|blindspot|trade-off|edge-case|dependency
      title: <short title>
      impact: <1-5>
      likelihood: <1-5>
      rationale: <one sentence>
      action: <recommended action>
  ---
  ```
- `SKILL.md` Phase 3 지침 갱신: 리포트 생성 시 frontmatter 선행 작성

**검증**: `/unknown-discovery` 실행 후 생성 리포트가 YAML 파싱 가능한지 확인.

**Effort**: 1-2시간

### A3. `unknown-discovery` Codebase grounding (옵션)

**문제**: 순수 대화 인터뷰라 repo 맥락 반영 불가.

**작업**:
- `SKILL.md` Prerequisites에 `--with-repo <path>` 플래그 추가
- Phase 0에 조건부 단계: 플래그 지정 시 repo 루트의 `README.md`, `plugin.json`, `pyproject.toml`, `package.json` 중 존재하는 파일 Read → Context Analysis에 반영
- `allowed-tools`에 `Read Glob` 추가

**검증**: `/unknown-discovery --with-repo .` 실행 시 Phase 0 요약에 repo 정보 반영되는지 확인.

**Effort**: 2-3시간

### A4. Phase A 릴리스

- `thinking-tools/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` version bump
- CHANGELOG.md 엔트리 추가
- 커밋 분할: 버그 수정(A1), enhancement(A2+A3)

---

## 3. Phase B — `spec-first` 신규 스킬

### B1. 스킬 디렉토리 스캐폴딩

**경로**: `thinking-tools/skills/spec-first/`

**파일**:
- `SKILL.md` (본체)
- `reference.md` (채점 루브릭 상세)
- `examples.md` (워크플로우 데모)
- `templates/SEED_SPEC.yaml` (출력 템플릿)
- `templates/INTERVIEW_STATE.md` (STATE 블록 포맷)

### B2. SKILL.md 핵심 구조

```markdown
---
name: spec-first
description: |
  Crystallize vague ideas into machine-readable Seed specs via Socratic
  interview and Ambiguity gating. Vendor-neutral Ouroboros-style workflow.

  Trigger when user mentions: spec-first, seed 생성, 명세 만들기, 
  requirements crystallize, vague idea, 모호한 아이디어 구체화.

  Skip for: reviewing existing plans (use unknown-discovery), 
  brainstorming (use diverse-sampling).
allowed-tools: AskUserQuestion Read Write Glob
---
```

### B3. Phase 구성 (SKILL.md 본문)

| Phase | 작업 |
|-------|------|
| 0 — Context | 도메인 분기 (greenfield/brownfield) + repo 감지 (optional) |
| 1 — Interview Loop | 4차원 질문 (Goal/Constraint/Success/Context) + Ambiguity 채점 |
| 2 — Gate Check | Ambiguity ≤ 0.2 + 차원별 floor 통과 확인 |
| 3 — Seed Emit | YAML Seed spec 파일 출력 (`docs/specs/{slug}.yaml`) |
| 4 — Handoff (optional) | OMC 감지 시 ralph 체인 옵션 제시 |

### B4. Ambiguity 채점 로직

**4차원 가중치** (greenfield 기본):

| Dimension | Weight | Floor |
|-----------|--------|-------|
| Goal Clarity | 0.40 | 0.75 |
| Constraint Clarity | 0.30 | 0.65 |
| Success Criteria | 0.30 | 0.70 |
| Context Clarity (brownfield) | 0.15 재분배 | 0.60 |

**Gate 공식**: `Ambiguity = 1 - Σ(clarity_i × weight_i)` ≤ 0.2 + **모든 차원 floor 이상** + 연속 2회 임계값 달성.

**채점 방식**:
- 매 답변 후 LLM이 4차원에 대해 0.0-1.0 점수 + 근거 기록 (temp 0.1 효과를 SKILL.md 지시로 근사)
- 채점 결과를 STATE 블록에 누적

### B5. Seed YAML 출력 스키마

```yaml
# templates/SEED_SPEC.yaml
---
spec_version: 1
created: <ISO-date>
target: <idea/project name>
domain: <tech|biz|creative|custom>
maturity: <idea|plan|execution>

goal:
  statement: <single-sentence goal>
  clarity_score: <0.0-1.0>

constraints:
  - id: c1
    type: technical|resource|legal|temporal
    description: <...>
    hard: true|false

success_criteria:
  - id: ac1
    description: <...>
    verifiable: true|false
    measurable_via: <metric or observation>

context:
  existing_stack: [<optional, brownfield>]
  dependencies: [<optional>]

ambiguity:
  overall: <0.0-1.0>
  breakdown:
    goal: <0.0-1.0>
    constraint: <0.0-1.0>
    success: <0.0-1.0>
    context: <0.0-1.0>

metadata:
  interview_rounds: <count>
  questions_asked: <count>
  generated_by: thinking-tools/spec-first
---
```

### B6. examples.md에 데모 2개

- Example 1 (Greenfield Tech): "task CLI를 만들고 싶어" → interview → Ambiguity 0.65 → 0.18 → Seed 생성
- Example 2 (Brownfield): "이 repo에 알림 기능 추가" → `--with-repo .` → Context 차원 포함 → Seed 생성

### B7. MECE 경계 명시

SKILL.md 상단에 `## MECE Positioning` 섹션:

| Skill | Mode | When |
|-------|------|------|
| unknown-discovery | 기존 계획 검토 (diagnostic) | Plan/idea 이미 존재 |
| **spec-first** | **모호 아이디어 → 명세 (constructive)** | **Plan 없음** |
| diverse-sampling | 창의적 대안 생성 | 여러 방향 탐색 |
| expert-panel | 결정 평가 (consensus) | 옵션 존재 |
| adversarial-review | 주장 반증 테스트 | Claim 존재 |

### B8. `plugin.json` 갱신

- `keywords`에 `spec-first`, `seed`, `ambiguity-gate` 추가
- `marketplace.json` 동기화 + version bump

---

## 4. Phase C — OMC 통합 (`spec-first --with-ralph`)

### C1. OMC 감지 로직

SKILL.md Phase 4에 추가:

```markdown
### Phase 4: Handoff (Optional)

**OMC Detection**:
- Check: `ls ~/.claude/plugins/cache/omc/oh-my-claudecode` exists
- If present AND user passed `--with-ralph`: offer chain to omc:ralph
- Otherwise: emit Seed file and exit
```

### C2. Seed → PRD 변환 매핑

| Seed YAML | OMC `prd.json` |
|-----------|----------------|
| `goal.statement` | `title` |
| `success_criteria[].description` | `user_stories[].acceptance_criteria[]` |
| `constraints[]` | `user_stories[].constraints[]` |
| `target` (slug) | `project_name` |

변환 로직은 SKILL.md에 의사코드로 명시 (실제 변환은 Claude가 수행).

### C3. Handoff 호출 패턴

```markdown
After Seed emission:
1. AskUserQuestion: "OMC ralph로 실행 반복을 이어갈까요?"
   Options: [네, ralph로], [Seed만 저장하고 종료]
2. If yes: 
   a. Convert Seed → prd.json format
   b. Write prd.json to .omc/specs/
   c. Invoke /oh-my-claudecode:ralph with --no-prd flag (Seed 기반 PRD 재사용)
```

### C4. `--evolve N` 플래그 (선택, Phase C 후반)

Ouroboros Evolve 경량 근사:
- ralph 실행 후 실행 로그·artifact 수집
- `spec-first --refine <old-seed> <execution-log>` 재호출 → Seed v(n+1)
- Ambiguity 차분 < ε 시 수렴 종료
- 상한: 3-5 generations (설정 가능)

### C5. 벤더 중립성 체크리스트

- [ ] `--with-ralph` 없으면 OMC 미사용
- [ ] OMC 미설치 환경에서 기본 워크플로우 정상 동작
- [ ] `--handoff-format` 플래그로 다른 포맷 확장 가능 (`openclaw`, `custom`)

---

## 5. Phase D — 기타 스킬 개선

### D1. `diverse-sampling`

| 작업 | 설명 | Effort |
|------|------|--------|
| D1a | Pairwise 유사도 필터 (의미 중복 탐지) | 2h |
| D1b | `--tournament` 모드 (k 생성 → top 2 → mutate 반복) | 4h |
| D1c | Probability calibration 검증 or 제거 결정 | 1h (결정) |

### D2. `doc-concretize`

| 작업 | 설명 | Effort |
|------|------|--------|
| D2a | Phase 4 Self-Critique를 외부 verifier 에이전트 호출로 대체 (OMC verifier 옵션) | 3h |
| D2b | `--fact-heavy` 모드 (WebFetch 강제) | 1h |
| D2c | Quick Mode 기준을 길이 대신 문서 유형 기반으로 전환 | 2h |

### D3. `doc-polish`

| 작업 | 설명 | Effort |
|------|------|--------|
| D3a | `--diff-preview` 모드 (승인 후 적용) | 3h |
| D3b | Voice preservation 모드 (reference 문서 기반 deviation 감지) | 1-2일 |
| D3c | llm-expression-blacklist 갱신 프로세스 문서화 | 2h |

### D4. `expert-panel`

| 작업 | 설명 | Effort |
|------|------|--------|
| D4a | 전문가별 sub-agent spawn (parallel, temperature variation) | 1일 |
| D4b | Judge 분리 패턴 (tie-break confidence 독립 평가) | 4h |
| D4c | `--brief` 플래그 (transcript 생략) | 1h |

### D5. `adversarial-review`

| 작업 | 설명 | Effort |
|------|------|--------|
| D5a | Judge를 sub-agent로 명시 spawn | 4h |
| D5b | 조기 종료 조건 (초기 3라운드 평균 delta 기반) | 2h |
| D5c | 도메인별 attack bank 추가 (security/biz/perf 등) | 1-2일 |
| D5d | `unknown-discovery` Critical 발견 자동 변환 → claim 입력 | 4h |

### D6. `thinking-facilitator` 에이전트

| 작업 | 설명 | Effort |
|------|------|--------|
| D6a | 복합 의도 감지 (2+ 스킬 조합 시그널) | 4h |
| D6b | `spec-first` 추가 등록 (Phase B 완료 후) | 30분 |

---

## 6. Phase E — Integration

### E1. `thought-chain` 재구성

**현재**: discovery → panel → concretize → polish

**개선**: 
- 기본: discovery → **adversarial-review** → panel → concretize → polish
- 옵션: `--with-spec-first`로 spec-first → discovery → ... 체인

**작업**:
- SKILL.md 파이프라인 그림 갱신
- Stage 매핑 테이블 갱신
- Stage 1 empty 시 조기 종료 조건 추가

**Effort**: 4h

### E2. 공통 출력 포맷 표준화

모든 스킬에 공통 YAML frontmatter 규약:

```yaml
---
skill: <skill-name>
version: <skill-version>
generated: <ISO-date>
input:
  target: <...>
  options: [...]
output:
  type: <report|spec|plan|...>
  structure: <schema-ref>
# ... skill-specific fields below
---
```

**작업**:
- 각 스킬의 템플릿 파일에 frontmatter 추가
- `thinking-tools/reference/common-schema.md` 문서 생성
- SKILL.md들에서 이 스키마 참조

**Effort**: 1일

### E3. STATE 블록 포맷 통일

현재 스킬마다 STATE 블록 포맷 상이. 공통 스키마 정의:

```
<!-- STATE:CHECKPOINT -->
skill: <name>
phase: <phase-id>
progress: <json>
<!-- /STATE -->
```

**작업**:
- 공통 스키마 문서화
- 레거시 포맷 호환 규칙 유지 (각 스킬의 compaction 복원 규칙 참조)

**Effort**: 4-6h

---

## 7. 의존성 그래프

```
Phase A ──┬──▶ Phase B ──▶ Phase C
          │         
          └──▶ Phase D (병행 가능)
                    │
                    ▼
                 Phase E
```

Phase A는 다른 모든 Phase의 전제 (YAML frontmatter 표준 확립).
Phase B·C는 순차.
Phase D는 Phase A 이후 병행 가능.
Phase E는 B·D 모두 완료 후.

---

## 8. 리스크 & 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| LLM 자가채점 일관성 부족 (B4) | spec-first 게이트 오작동 | STATE 블록에 근거 기록, 사용자 수동 보정 옵션 |
| OMC 버전 호환성 (C) | `ralph` 명세 변경 시 매핑 깨짐 | 감지 로직에 OMC 버전 체크 추가, fallback 메시지 |
| Sub-agent spawning 비용 (D4a) | expert-panel 토큰 소비 급증 | `--brief` 기본값화 + sub-agent 선택적 |
| YAML 스키마 migration (E2) | 기존 사용자 템플릿 깨짐 | v1 스키마로 시작, 하위 호환 1버전 유지 |
| Facilitator 라우팅 복잡도 (D6a) | 복합 의도 오라우팅 | AskUserQuestion fallback 강제 |

---

## 9. 버저닝 & 릴리스 전략

- **Phase A**: patch (bug + minor enhancement)
- **Phase B**: minor (new skill)
- **Phase C**: patch (additive feature)
- **Phase D**: minor (각 스킬 업그레이드 시)
- **Phase E**: minor (breaking 아님, additive)

각 Phase 완료 시:
1. `thinking-tools/.claude-plugin/plugin.json` version bump
2. `.claude-plugin/marketplace.json` 동기화
3. CHANGELOG.md 엔트리
4. git commit (`feat(thinking-tools): ...` 또는 `fix(thinking-tools): ...`)

---

## 10. 검증 전략

각 Phase 완료 시:

| Phase | 검증 방법 |
|-------|----------|
| A | 기존 스킬 전체 수동 실행 + thinking-facilitator 라우팅 테스트 |
| B | spec-first 워크플로우 2개 예제(greenfield/brownfield) 완주 |
| C | OMC 설치/미설치 환경 각각에서 spec-first 실행 |
| D | 개선된 스킬별로 before/after 동일 입력 비교 |
| E | thought-chain 4-stage 파이프라인 완주 + YAML 출력 파싱 검증 |

**공통**: `python3 -m json.tool` / YAML lint 로 출력물 포맷 검증 자동화.

---

## 11. 미결정 (dev-plan 레벨)

| # | 항목 | 논의 필요 |
|---|------|----------|
| P1 | `spec-first` 최종 스킬명 | 후보 확정 (spec-first / seed-crystallize / crystallize) |
| P2 | `--evolve` 상한 기본값 | 3 vs 5 |
| P3 | Phase E2 YAML 스키마 주도자 | spec-first 스키마를 기준으로? |
| P4 | D4a sub-agent spawn이 Claude Code 플랫폼별 호환성에 미치는 영향 | 테스트 필요 |
| P5 | OMC 감지 경로 고정 (`~/.claude/plugins/cache/omc/...`) 외 대안 | env var 지원 여부 |

---

## 12. 다음 액션

1. [ ] 본 dev-plan 리뷰 (사용자 승인)
2. [ ] P1-P5 미결정 항목 결정
3. [ ] Phase A 착수 (브랜치 `feature/thinking-tools-ouroboros-phase-a`)
4. [ ] `thinking-facilitator` 버그 수정 PR 제출
