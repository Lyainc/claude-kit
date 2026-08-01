# thinking-tools

Claude Code용 **사고 도구 스킬 플러그인**. 분석, 문서 작성, 품질 검증을 위한 8개 스킬과 1개 에이전트를 제공합니다.

## 설치

```bash
claude plugin install thinking-tools@Lyainc-claude-kit
```

## 포함된 에이전트

| Agent | Model | Description |
| --- | --- | --- |
| `thinking-facilitator` | — | Auto-route requests to the optimal thinking skill |

## 포함된 스킬

| Skill | Description | Triggers |
| --- | --- | --- |
| `diverse-sampling` | Generate diverse responses using Verbalized Sampling | 브레인스토밍, 다양한 아이디어, 대안 제시 |
| `doc-concretize` | Transform abstract concepts into structured docs (Writer) | 문서화, 구체화, 체계적 정리 |
| `doc-polish` | Validate and improve existing MD docs — 3-layer QA (Editor) | 검사해줘, 다듬어줘, polish, lint |
| `expert-panel` | Expert panel discussions with dialectical analysis | expert panel, design review, 전문가 토론 |
| `unknown-discovery` | Discover blind spots through Socratic interviews | 맹점, 놓친 것, blind spot, 심층 인터뷰 |
| `adversarial-review` | Stress-test claims with 1:1 attack rounds and Survival Score | 반증, 공격, 검증, adversarial review, 주장 반박 |
| `build-spec` | Crystallize vague ideas into machine-readable Seed specs via Socratic interview + Ambiguity gating | 스펙 구체화, build spec, seed 스펙, 모호함 해소 |
| `completion-condition` | Pick the next session's cohesive unit, then render it as a `/goal`-evaluable condition | 완료조건, 다음 세션 목표, START-PROMPT, next goal |

## 문제 해결

**설치 후 적용 안됨**: Claude Code 재시작 필요

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 라이선스

MIT
