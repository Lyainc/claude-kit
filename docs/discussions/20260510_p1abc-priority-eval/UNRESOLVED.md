# Unresolved Issues

**Date**: 2026-05-10

---

## 보류 사항

없음. 3 토픽 모두 만장일치 합의 도달.

---

## 후속 인터뷰가 필요한 *결정점* (보류 아님, 다음 단계용)

이 항목들은 패널 합의에 의존하지 않는 *구체 설계 결정*이라 별도 deep-interview 후보:

### P1a 표면 결정 (deep-interview 권장)

cheatsheet를 어디에 박을지:
- `/omc-cheatsheet` 슬래시 커맨드
- SessionStart hook 1회 hint
- AGENTS.md 한 섹션
- vault에 `.cheatsheet.md`로 저장

각 표면별 trade-off 정리는 패널이 안 다룸 — Deep Dive 단계에서.

### P1a drift mitigation 메커니즘

명령어 frontmatter에서 자동 추출하는 빌드 스크립트:
- 추출 시점 (CI? pre-commit hook? 수동?)
- 출력 포맷 (markdown table? YAML? 슬래시 인자?)
- 검증 방법 (cheatsheet에 있는 명령어가 실제 plugin에 존재하는지)

### P1c 박을 위치

alias/preset을 어디에 둘지:
- zsh dotfile (env-bound risk)
- Claude Code settings (사용자 settings, plugin 제어 불가)
- plugin 안 (새 메커니즘 설계 필요)

trade-off 명시 필요. 현재는 "결정 안 됨" 상태.

---

*Held items: 0 · Decision points for Deep Dive: 3*
