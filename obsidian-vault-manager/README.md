# obsidian-vault-manager

Claude Code용 **Obsidian vault 지식 관리 플러그인**. 2개 에이전트 + 7개 스킬로 vault를 체계적으로 관리합니다.

## 설치

```bash
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
| `inbox-review` | Inbox 파일 일괄 정리 (분류/이동/삭제) |
| `context` | vault 내부 도메인 맥락 로드 (Explore fork) |
| `archive` | 완료 프로젝트 아카이브 + MOC/Home.md 정리 |
| `vault-daily` | 데일리 노트 생성 및 전일 리뷰 |

## vault-reader와의 관계

| 영역 | obsidian-vault-manager | vault-reader |
| --- | --- | --- |
| 사용 맥락 | vault 관리 세션 내부 | 외부 프로젝트에서 vault 접근 |
| 쓰기 범위 | 노트/MOC/프로젝트 전체 생성·수정·삭제 | 새 session-note 생성만 가능 |
| `context` vs `vault-searcher` | MOC 기반 도메인 로드 + `--exclude`/`--limit` 옵션 | MOC 기반 도메인 로드 (읽기 전용, 외부 접근용) |
| 세션 기록 | 해당 없음 (vault-reader의 session-note 사용) | session-note 생성 (과거 기록 + 미래 계획 통합) |

## 사전 요구사항

- `~/vault/` 경로에 Obsidian vault가 존재해야 합니다
- macOS 환경 권장 (vault 검색에 `mdfind` 사용, 미지원 시 `grep` fallback)

## 아키텍처

자세한 설계 문서는 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.

## 라이선스

MIT
