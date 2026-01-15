---
name: doc-concretize

description: |
  DEPRECATED: This skill has been migrated to the plugin version at /skills/doc-concretize/.
  The repository root is now a Claude Code plugin. Install with: claude plugin add ./claude-kit

  Transform abstract concepts into concrete, well-structured documentation
  through step-by-step recursive writing with verification at each step.

  Use when the user requests documentation of abstract ideas, strategies,
  or concepts requiring structured concretization (expected output > 800 characters).

  Trigger when user mentions: 구체화, 문서화, 체계적 정리, 개념 정리, 아이디어 문서화, 전략 문서, 글로 정리,
  or requests: "이 개념을 문서로 정리해줘", "아이디어를 체계적으로 구체화해줘",
  "전략을 상세 문서로 작성해줘", "비전을 실행 가능한 계획으로 풀어줘".

  Skip for: simple definitions, "짧게"/"간단히"/"briefly" requests, or already-structured content.
---

# Document Concretization

추상적 개념을 구체적이고 구조화된 문서로 변환하는 스킬.

## Migration Notice

이 스킬은 플러그인 버전으로 마이그레이션되었습니다.

**플러그인 위치**: `/skills/doc-concretize/`

**설치 방법**:
```bash
claude plugin add ./claude-kit
```

## Core Workflow (Summary)

1. **Phase 1: Segmentation** — 입력 분석 → 3-7개 의미 단위로 분할
2. **Phase 2: Recursive Build** — Build → Verify → Reflect 사이클
3. **Phase 3: Final Review** — Self-critique + adversarial check
4. **Phase 4: Polish** — Grammar, style, blacklist expression 제거

## References

- **Full documentation**: See `/skills/doc-concretize/SKILL.md`
- **Detailed procedures**: See `/skills/doc-concretize/reference.md`
- **Examples**: See `/skills/doc-concretize/examples.md`

## Quick Start

```
User: "우리 서비스의 핵심 가치를 문서로 정리해줘.
       고객 중심, 빠른 실행, 투명성이 중요해."

→ Phase 1: 3개 세그먼트로 분할 (고객 중심 / 빠른 실행 / 투명성)
→ Phase 2: 각 세그먼트 작성 + 검증
→ Phase 3: 전체 리뷰 + 비판적 검토
→ Phase 4: 문법/스타일 다듬기
→ Output: 구조화된 핵심 가치 문서 (~1,500자)
```
