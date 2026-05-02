# Unresolved Issues — Master Plan 검증 패널

**Date**: 2026-04-16

## U1. Autosync 스냅샷의 `source_commit` 획득 실패 시 폴백

**Context**: TOPIC 4 권고 #10에서 vault 스냅샷의 frontmatter에 `source_commit` 필수 지정 합의. 그러나 다음 경우 commit hash 부재:

- 원본 파일이 git untracked 상태
- 원본 파일이 스테이징만 되고 commit 전
- 프로젝트가 git 리포가 아님
- dirty working tree의 unstaged 변경

**Candidate Policies**:
- A. 저장 거부 (strict) — UX 저하
- B. `source_commit: "uncommitted@{ISO8601}"` 식 플레이스홀더 — 추적성 타협
- C. 파일 전체 hash(sha256) 대체 — 완전성 보존, 비교는 가능
- D. 저장은 허용하되 frontmatter에 `source_stale_risk: true` 경고 플래그

**Decision Needed Before**: Autosync W8 P1 구현 착수

**Recommended Owner**: Autosync plan 작성자

---

## U2. (참고) Binding plan 내 4건 + Autosync plan 내 5건

이 미해결들은 패널에서 **심화 검토 대상**으로 별도 지정함. 개별 워크스트림 착수 직전 `/expert-panel` 또는 `/unknown-discovery` 재소집 권고.

### Binding plan 미해결
- `promoted_to_project` 단일/다중 → 패널 합의: **단일값 + also_related_projects 배열** (권고 #9로 해소됨, 명시 필요)
- Project archive 시 관련 note 메타 유지 정책
- `auto_capture` 기본값 (권고: false/opt-in — 패널 합의)
- Dataview/Templater 연동 — 권고 #10에 부분 흡수

### Autosync plan 미해결
- 같은 파일 다중 편집 시 어느 버전 제안
- 모노레포 다중 `.vault-link` 라우팅
- 민감 파일 필터링 — `.gitignore` 재활용이 충분한지
- Hook 실행 순서 및 다른 hook과의 충돌
- 역방향 sync (vault → repo) 의도적 out-of-scope 유지

---

## Status

**즉시 결정 필요**: U1 1건
**워크스트림 착수 직전 재논의**: U2 하위 9건
