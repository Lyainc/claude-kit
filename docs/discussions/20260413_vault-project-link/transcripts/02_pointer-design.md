# TOPIC 2: Pointer file 설계

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing

**[Optimistic Practitioner]**: 파일명 `.vault-link`, YAML 한 줄. `vault_path: 20_Projects/claude-kit`.

**[Critical Practitioner]**: 필드 늘리면 포맷 논쟁 됩니다. MVP는 `vault_path` 단일 필드.

## Q&A

**[Security Expert]**: `.vault-link`를 git 커밋하면 vault 구조가 repo에 노출됩니다. `.vault-link` (committed) + `.vault-link.local` (gitignored, override) 이중 지원.

**[LLM Orchestration Expert]**: 발견 방식 — 명시적 로드 vs 자동 탐지 중 자동 탐지가 낫습니다. vault-searcher 호출 시 CWD에서 상위로 upward walk (git-like). 사용자 개입 0.

**[Knowledge Management Expert]**: vault 폴더 이동/리네임 시 깨집니다. 해석 실패 시 `20_Projects/` 하위 이름 유사도 기반 제안으로 recovery.

**[DX/Tooling Expert]**: 필드 확장 여지 (scope, read_only 등)는 후일. 지금 넣으면 YAGNI.

## Dialectic

**Thesis**: 최소 포맷 + 자동 discovery + recovery.
**Antithesis**: 확장 필드 미리 설계. 패널 거부 — YAGNI.
**Synthesis**: MVP는 `vault_path:` 단일 필드. 버전 필드는 추후 breaking change 발생 시 도입.

## 결론

- 파일: `.vault-link` (committed), `.vault-link.local` (gitignored, override)
- 필수 필드: `vault_path:` 한 줄
- Discovery: CWD에서 상위로 upward walk
- Recovery: 경로 해석 실패 시 `20_Projects/` 유사도 제안
