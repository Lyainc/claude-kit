# claude-kit

Claude Code용 **스킬 플러그인 마켓플레이스**. 독립적인 플러그인들을 하나의 저장소에서 관리합니다.

## 플러그인 목록

### [thinking-tools](thinking-tools/)

분석, 문서 작성, 품질 검증을 위한 사고 도구 스킬 플러그인.

```bash
claude plugin install thinking-tools@Lyainc-claude-kit
```

| Skill | Description |
| --- | --- |
| `diverse-sampling` | Verbalized Sampling 기반 다양한 응답 생성 |
| `doc-concretize` | 추상적 개념을 구조화된 문서로 변환 |
| `doc-polish` | 마크다운 문서 3-layer QA 검증 |
| `expert-panel` | 변증법적 전문가 패널 토론 |
| `unknown-discovery` | 반복 인터뷰를 통한 맹점 발견 |

### [obsidian-vault-manager](obsidian-vault-manager/)

Obsidian vault 지식 관리 플러그인. 에이전트 + 6개 스킬.

```bash
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `vault-knowledge-manager` (agent) | 메인 에이전트 — 노트 생성, MOC 관리, 프로젝트 추적 |
| `vault-file-organizer` (agent) | 경량 subagent — 파일 이동, 이름 변경, 아카이브 |
| `capture` / `note` / `project` | 노트 캡처, 생성, 프로젝트 관리 스킬 |
| `inbox-review` / `wrapup` / `context` | Inbox 정리, 세션 마무리, 맥락 로드 스킬 |

## 기존 claude-kit 사용자 마이그레이션

기존 `claude-kit` 플러그인이 `thinking-tools`로 이름이 변경되었습니다.

```bash
# 1. 기존 플러그인 제거
claude plugin uninstall claude-kit

# 2. 새 이름으로 재설치
claude plugin install thinking-tools@Lyainc-claude-kit
```

스킬 이름과 트리거는 동일하므로 사용법 변경은 없습니다.

## 문제 해결

**설치 후 적용 안됨**: Claude Code 재시작 필요

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 개발

개발자 가이드는 [CLAUDE.md](CLAUDE.md) 참조.

## 라이선스

MIT
