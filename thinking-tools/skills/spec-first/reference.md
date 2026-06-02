# Spec First — Reference

## 1. Ambiguity Scoring Rubric (A1 — Y/N Checklist)

For each dimension, evaluate after receiving the user's answer. Mark Y/N and write a one-line rationale for each item. clarity = Y_count / total_questions.

### Goal Clarity (4 questions)

| # | Question | Y if... |
|---|----------|---------|
| G1 | 단일 문장으로 목표를 표현할 수 있나? | Goal can be stated in one sentence without "and/or" ambiguity |
| G2 | 목표가 측정 가능하거나 관찰 가능한가? | User described a state that can be verified as achieved |
| G3 | 목표의 주요 수혜자(사용자/시스템)가 명확한가? | At least one clear beneficiary identified |
| G4 | "왜"를 설명할 수 있나 (동기 이해 가능)? | Underlying motivation stated or inferable |

### Constraint Clarity (3 questions)

| # | Question | Y if... |
|---|----------|---------|
| C1 | 최소 1개의 hard constraint가 명시됐나? | At least one non-negotiable limit stated (tech stack, deadline, budget, legal) |
| C2 | hard / soft constraint 구분이 가능한가? | User differentiated "must have" vs "nice to have" |
| C3 | 제약의 근거를 이해할 수 있나? | Reason for each major constraint is stated or inferable |

### Success Criteria (4 questions)

| # | Question | Y if... |
|---|----------|---------|
| S1 | 최소 1개의 verifiable acceptance criterion이 있나? | At least one criterion with observable outcome |
| S2 | "성공"의 범위가 명확한가 (what is in/out)? | Clear boundary between success and partial success |
| S3 | 성공 기준이 목표와 직접 연결되나? | Criteria would actually validate the goal |
| S4 | 측정 방법 또는 관찰 방법이 제시됐나? | How to check if criterion is met is inferable |

### Context Clarity (3 questions, brownfield only)

| # | Question | Y if... |
|---|----------|---------|
| X1 | 기존 스택/시스템과의 통합 포인트가 파악됐나? | Integration surface described (API, database, module) |
| X2 | 기존 코드의 어느 부분에 영향을 주는지 알 수 있나? | Affected components or files identified |
| X3 | 기존 의존성·제약과 새 기능의 충돌 가능성 검토됐나? | Potential conflicts acknowledged or ruled out |

---

## 2. Scoring Calibration Notes

- Never assign 0.0 (no answer means unknown, not impossible) or 1.0 (always some residual ambiguity).
- Floor values are hard gates — even if overall Ambiguity ≤ 0.20, a dimension below its floor blocks the gate.
- For `--quick` mode: evaluate G1-G4 only; gate = Goal ≥ 0.75 (skip other dimensions).
- If user provides a very detailed answer covering multiple dimensions at once: score all relevant dimensions simultaneously.

---

## 3. Brownfield Repo Files Detection List

In order of precedence for context injection:

1. `README.md` — project overview, purpose
2. `CLAUDE.md` or `AGENTS.md` — AI operating context (high signal)
3. `plugin.json` or `package.json` — name, version, description, keywords
4. `pyproject.toml` — Python project metadata
5. `requirements.txt` — dependency signal
6. `Cargo.toml` — Rust project
7. `go.mod` — Go project

Extract: project name, description, key dependencies, notable constraints.
Inject as Phase 1 context prefix: "현재 프로젝트: {name} — {description}. 주요 의존성: {deps}."

---

## 4. Dimension Weight Table

| Dimension | Greenfield | Brownfield | Floor |
|-----------|-----------|-----------|-------|
| Goal | 0.40 | 0.34 | 0.75 |
| Constraint | 0.30 | 0.26 | 0.65 |
| Success | 0.30 | 0.25 | 0.70 |
| Context | — | 0.15 | 0.60 |

Brownfield weights sum to 1.00: 0.34 + 0.26 + 0.25 + 0.15 = 1.00.
