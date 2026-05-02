# 프로젝트-볼트 연결 메커니즘 설계 — 전문가 패널 요약

**날짜**: 2026-04-13
**패널**: Moderator, Optimistic Practitioner, Critical Practitioner, Knowledge Management Expert, DX/Tooling Expert, Security Expert, LLM Orchestration Expert
**토픽 수**: 4 (모두 합의)

## 최종 합의안

### 1. 심볼릭 링크 폐기
초안 아이디어였던 `~/dev/{project}/vault → ~/vault/20_Projects/{project}` 심볼릭은 다음 이유로 전면 기각:
- **wikilink/MOC 파괴**: 부분 노출로 vault 내부 링크 해석 불가
- **라우팅 우회**: Glob/ripgrep/CLAUDE.md 재귀 탐색이 심볼릭을 구분 못 해 vault-searcher(haiku) 라우팅 파괴, opus 컨텍스트 오염, 비용 증가
- **유출 비가역성**: `.gitignore` 단일 방어선, 실수 1회로 vault 원문이 repo에 커밋되면 되돌릴 수 없음
- **macOS 프리미티브 부재**: read-only bind mount 불가, FUSE는 과다

### 2. 채택 방식: Pointer file 3층 구조

**Layer A — `.vault-link` pointer file (MVP, 필수)**
```yaml
# .vault-link (committed)
vault_path: 20_Projects/claude-kit
```
- `.vault-link.local` (gitignored) 으로 사용자별 override 지원
- vault-searcher가 CWD에서 상위로 upward discovery (git-like)
- 경로 해석 실패 시 `20_Projects/` 하위 유사도 기반 제안 recovery

**Layer B — On-demand projection (스코프 아웃)**
- IDE에서 vault 문서를 파일로 열고 싶다는 욕구는 Obsidian 창 띄우면 해결
- 필요해지면 나중에 추가, MVP 제외

**Layer C — 문화 가이드라인 (README 문서화)**
- 문서 작업은 vault에서 (Obsidian)
- 코드 작업은 repo에서 (IDE)
- vault-searcher는 "읽기 브릿지"이지 "통합 환경"이 아님

### 3. vault-bridge 책임 경계
| 항목 | 소유 | 비고 |
|------|------|------|
| 포인터 소비 (자동 스코프) | vault-bridge | vault-searcher 내부 로직 |
| `/vault-link` slash command | vault-bridge | init / status / fix |
| read-only 캐시 디렉토리 | vault-bridge | projection 도입 시 |
| vault 프로젝트 폴더 생성 | obsidian-vault-manager | 사용자에게 안내만, 암묵 호출 금지 |
| 심볼릭 생성 | (없음) | 기각 |
| repo `.gitignore` 수정 | (없음) | 제안만, 강제 금지 |

## 권장 구현 순서

1. vault-searcher에 `.vault-link` upward discovery + 자동 스코프 로드 추가
2. `.vault-link.local` override 지원
3. `/vault-link init` slash command (대화형 vault 경로 선택, 유사도 제안 포함)
4. `/vault-link status` (현재 링크 상태 진단)
5. `/vault-link fix` (경로 깨짐 복구)
6. README에 문화 가이드 추가 (문서/코드 분리 원칙)

## 액션 아이템

- [ ] `vault-bridge/agents/vault-searcher.md`: `.vault-link` 자동 스코프 로직 명세 추가
- [ ] `vault-bridge/commands/vault-link.md`: 신규 slash command 정의
- [ ] `vault-bridge/README.md`: 포인터 파일 포맷 + 문화 가이드 섹션
- [ ] `CLAUDE.md`: vault 라우팅 규칙에 포인터 파일 언급 추가
- [ ] `.gitignore` 기본 제안 템플릿 작성 (`.vault-link.local`, `.vault-cache/`)

## 합의 상태
- TOPIC 1 (메커니즘 선택): 만장일치 합의
- TOPIC 2 (포인터 설계): 만장일치 합의
- TOPIC 3 (책임 경계): 만장일치 합의
- TOPIC 4 (projection 재평가): 만장일치 합의 (스코프 아웃)

---
*4개 토픽 논의 완료 · 4개 합의, 0개 보류 · 미해결 2건은 UNRESOLVED.md 참조*
