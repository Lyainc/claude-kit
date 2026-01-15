---
name: diverse-sampling

description: |
  DEPRECATED: This skill has been migrated to the plugin version at /skills/diverse-sampling/.
  The repository root is now a Claude Code plugin. Install with: claude plugin add ./claude-kit

  Generate diverse responses using Verbalized Sampling (VS) technique to overcome mode collapse.
  Produces multiple alternative outputs with probability distribution, then selects based on strategy.

  Use when creative diversity is needed: brainstorming, ideation, alternative solutions,
  creative writing, synthetic data generation, or exploring multiple perspectives.

  Trigger when user mentions: 다양한 아이디어, 브레인스토밍, 대안 제시, 여러 관점, 창의적 답변,
  diverse ideas, brainstorming, alternatives, multiple options,
  or explicitly: "/diverse-sampling", "VS 기법으로", "verbalized sampling으로".

  Skip for: factual questions, code debugging, single correct answer tasks, precise calculations.
---

# Diverse Sampling

Verbalized Sampling 기법을 활용한 다양성 향상 스킬.

## Migration Notice

이 스킬은 플러그인 버전으로 마이그레이션되었습니다.

**플러그인 위치**: `/skills/diverse-sampling/`

**설치 방법**:
```bash
claude plugin add ./claude-kit
```

## Core Workflow (Summary)

1. **Phase 0: Preparation** — 호출 유형 판단 (Explicit/Implicit) + 언어 감지
2. **Phase 1: VS Generation** — 5개 응답 + 확률 분포 생성
3. **Phase 2: Selection** — Weighted random / --all / --best
4. **Phase 3: Output** — 선택된 응답 출력 + Fallback 처리

## Options

| Option | Description |
|--------|-------------|
| (default) | Weighted random sampling → 1개 출력 |
| `--all` | 5개 전체 표시 |
| `--best` | 최고 확률 선택 |

## References

- **Full documentation**: See `/skills/diverse-sampling/SKILL.md`
- **Detailed procedures**: See `/skills/diverse-sampling/reference.md`
- **Examples**: See `/skills/diverse-sampling/examples.md`
- **Research paper**: [arXiv:2510.01171](https://arxiv.org/abs/2510.01171)

## Quick Start

```
User: "/diverse-sampling 스타트업 이름 아이디어"

→ Phase 0: Explicit trigger → proceed, Korean detected
→ Phase 1: VS 프롬프트로 5개 응답 생성
→ Phase 2: Weighted random sampling
→ Phase 3: 선택된 응답 출력

Output: "NexaFlow - 다음 단계로의 흐름을 의미"
```
