# TOPIC 1: 연결 메커니즘의 근본 선택

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing

**[Optimistic Practitioner]**: 심볼릭의 매력은 "CWD에서 바로 보임" 하나. 포인터 파일은 IDE/Finder에서 문서를 직접 못 엽니다.

**[Critical Practitioner]**: 직접 본다 = 직접 오염된다. 편의성이 곧 사고 경로입니다.

## Q&A

**[Knowledge Management Expert]**: 부분 노출이 치명적입니다. vault의 wikilink는 vault 루트를 전제로 해석됩니다. `20_Projects/foo/`만 심볼릭 노출하면 `[[api-design]]` 같은 링크는 전부 깨집니다. 프로젝트 폴더는 vault에서 자족적이지 않다는 게 핵심.

**[LLM Orchestration Expert]**: 컨텍스트 경제 관점 3중 손실 — Claude Code Glob/ripgrep/CLAUDE.md 재귀 탐색이 심볼릭 구분 못 함. haiku 라우팅 파괴 × opus 컨텍스트 오염 × 비용 증가.

**[Security Expert]**: `.gitignore` 단일 방어선. `git add -f`, IDE 트래킹, pre-commit `find` 루프 하나로 뚫립니다. 비가역.

**[DX/Tooling Expert]**: macOS에 read-only bind mount 프리미티브 없음. FUSE는 과다. 실현 가능 대안 3개:
- A. Pointer file `.vault-link`
- B. On-demand read projection (세션 한정 캐시)
- C. 문화적 분리 — 문서 vault, 코드 repo

## Dialectic

**Thesis** (심볼릭 유지): 없음. 유지 의견 0.

**Antithesis** (대안 채택): 패널 전원.

**Synthesis**: A를 MVP 기본, C를 가이드라인, B는 별도 토픽에서 재평가.

## 결론

심볼릭 링크 방식 전면 폐기. Pointer file(A) 채택. 문화 가이드(C) 병기. Projection(B)은 TOPIC 4에서 필요성 재검토.
