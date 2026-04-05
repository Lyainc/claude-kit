# obsidian-vault-manager

Claude Code용 **Obsidian vault 지식 관리 플러그인**. 에이전트 + 6개 스킬로 vault를 체계적으로 관리합니다.

## 설치

```bash
# 마켓플레이스 설치
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

## 포함된 에이전트

| Agent | Model | Description |
| --- | --- | --- |
| `vault-knowledge-manager` | Sonnet | 메인 에이전트 — 노트 생성, MOC 관리, 프로젝트 추적 |
| `vault-file-organizer` | Haiku | 경량 subagent — 파일 이동, 이름 변경, 아카이브 |

## 포함된 스킬

| Skill | Description |
| --- | --- |
| `capture` | 즉시 Inbox에 메모 저장 (`/capture 내용`) |
| `note` | 새 노트 생성 + MOC 연결 (`/note 주제`) |
| `project` | 프로젝트 디렉토리 생성 (`/project 이름`) |
| `inbox-review` | Inbox 파일 일괄 정리 |
| `wrapup` | 세션 요약 + 변경 내역 정리 |
| `context` | 도메인 맥락 로드 (Explore fork) |

## 사전 요구사항

- `~/vault/` 경로에 Obsidian vault가 존재해야 합니다
- macOS 환경 (vault 검색에 `mdfind` 사용)

## 아키텍처

자세한 설계 문서는 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.

## 라이선스

MIT
