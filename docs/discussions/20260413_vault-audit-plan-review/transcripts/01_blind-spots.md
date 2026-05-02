# Transcript 01 — Blind Spots & Platform Compatibility

## Briefing
- [Optimistic] bash + python3 기본 탑재, 외부 의존 없음
- [Critical] Claude Code Bash tool 샌드박스/권한 승인 이슈, 긴 파이프라인 중단 가능성

## Q&A
- [DevEx] (1) `~/vault/.obsidian/`는 Obsidian 점유 영역 — workspace.json 경합 + git 노이즈. 대안 `~/vault/.ovm/`. (2) PyYAML은 기본 아님 → stdlib만 사용. (3) skill `allowed-tools` 선언 확인 필요.
- [Architecture] 스크립트 4~5개 대신 단일 `ovm-primitives.sh` + 서브커맨드 권장.
- [Data Integrity] `.ovm/` 동의, gitignore 권장.
- [Security] path-traversal 방어 필수.
- [Performance] 테스트 볼트 최소 300 노트 규모.

## Dialectic
- Thesis: 여러 스크립트 + `.obsidian/`
- Antithesis: 단일 스크립트 + `.ovm/`
- Synthesis: 단일 `ovm-primitives.sh` + `.ovm/` + stdlib + path 검증 + 합성 볼트 생성기

## Conclusion
계획서 반영: `scripts/ovm-primitives.sh` 단일 파일, sidecar `~/vault/.ovm/audit-state.json`, Python stdlib only, `scripts/test/gen-fixture.sh` 추가, 입력 검증 규칙 명시.
