# claude-kit

Claude Code용 **스킬 플러그인**. 생산성 향상을 위한 4개의 스킬을 제공합니다.

## 설치

```bash
# 1. 마켓플레이스 등록
claude plugin marketplace add Lyainc/claude-kit

# 2. 플러그인 설치
claude plugin install claude-kit@Lyainc-claude-kit
```

## 포함된 스킬

| Skill              | Description                                          | Triggers                                 |
| ------------------ | ---------------------------------------------------- | ---------------------------------------- |
| `diverse-sampling` | Generate diverse responses using Verbalized Sampling | 브레인스토밍, 다양한 아이디어, 대안 제시 |
| `doc-concretize`   | Transform abstract concepts into structured docs     | 문서화, 구체화, 체계적 정리              |
| `expert-panel`     | Expert panel discussions with dialectical analysis   | expert panel, design review, 전문가 토론 |
| `unknown-discovery`| Discover blind spots through iterative interviews    | 맹점, 놓친 것, blind spot, 심층 인터뷰   |

## 문제 해결

**설치 후 적용 안됨**: Claude Code 재시작 필요

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 개발

개발자 가이드는 [CLAUDE.md](CLAUDE.md) 참조.

## 라이선스

MIT
