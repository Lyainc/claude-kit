# Expert Panel SUMMARY — claude-kit Master Plan 통합 검증

**Date**: 2026-04-16
**Target**: `~/vault/20_Projects/claude-kit/project-2026-04-16-master-plan.md` + `plan-2026-04-16-note-project-binding.md` + `plan-2026-04-16-plan-doc-autosync.md`
**Panel**: Moderator, Optimistic Practitioner, Critical Practitioner, Project Manager (필수), Knowledge Management Expert (필수), DX/Tooling Expert, LLM Orchestration Expert

## Topics & Consensus

| # | Topic | Outcome |
|---|-------|---------|
| 1 | 워크스트림 W0–W8 의존성 및 우선순위 | 조건부 합의 (MVP 분해 + W3 선행 + W4 흡수) |
| 2 | 중복/통폐합 결정 합리성 | 합의 (프런트매터 필드 분리, workstream 필드 도입) |
| 3 | Note-Project Binding 옵션 C 건전성 | 합의 (필드 의미 명문화, Dataview 예시 보강) |
| 4 | plan-doc-autosync W0 의존 + 안전장치 | 조건부 합의 (실시간 모드 제외, 스냅샷 메타 필수) |
| 5 | `_index` 스키마 확장 부담 | 합의 (생명주기 명시, 최소 템플릿, 의미론적 경고) |

합의 실패 0건. 모든 토픽 3라운드 이내 수렴.

## Action Items (우선순위별)

### P0 (즉시 반영)

1. **W0 MVP 분해**: Master Plan §4에 "단일 vault + v1 스키마 고정" 선행 릴리스 조항 추가. Unresolved 3건(다중 vault/CI/스키마 버전) 중 1건만 V2로 지연 가능.
2. **W3 선행 병렬 트랙 지정**: adversarial-review를 팀 모멘텀 유지용 최우선 병렬 착수.
3. **Autosync 초기 릴리스 범위 축소**: PostToolUse 실시간 모드 제거, SessionEnd + `/save-plan-doc` 만.
4. **Autosync 스냅샷 메타 필수화**: `source_path`, `source_commit`, `captured_at` 3개 필드.
5. **`_index` 생명주기 문서화**: Binding plan에 "어느 시점에 어떤 필드가 채워지나" 섹션 추가.

### P1 (단기 반영)

6. **W4 vault-lint를 W2 Phase B 빠른 티어로 흡수**: 독립 워크스트림에서 제거.
7. **프런트매터 `consolidates` 분리**: `references_active` + `supersedes_archived` 로.
8. **신규 plan에 `workstream: W*` 필수 필드 규약 신설**.
9. **`promoted_to_project`(단일) + `also_related_projects`(배열) 분리** — Binding plan.
10. **Binding plan에 field dictionary + Dataview 쿼리 예시 섹션 추가**.
11. **`.vault-link`에 `autosync_paths` 프로젝트별 override 필드 추가** — W0 + Autosync 공동.
12. **project 스킬 기본 템플릿 최소화**: 5개 필수 필드만, 나머지 점진 enrichment.

## Key Risks Identified

- **Critical path concentration on W0**: 다수 워크스트림(W1/W7/W8)이 W0 단일 블로커에 의존. MVP 분해로 완화.
- **Notification fatigue (Autosync)**: AskUserQuestion 과다 발화 위험. 세션당 1회 제한으로 완화.
- **Field dictionary gap**: `absorbs`/`related_notes`/`promoted_to_project`/`also_related_projects` 의미 구분이 사용자에게 불명확. 명문화 필요.
- **Snapshot stale tracking**: vault 쪽 스냅샷의 원본 동기 상태 추적 메커니즘이 초안에 부재. 메타 3필드로 최소 해결.

## Unresolved (see UNRESOLVED.md)

- Autosync 스냅샷의 `source_commit` 획득 불가 시 폴백 정책 (untracked 파일 등)

## Files Referenced

- `~/vault/20_Projects/claude-kit/project-2026-04-16-master-plan.md`
- `~/vault/20_Projects/claude-kit/plan-2026-04-16-note-project-binding.md`
- `~/vault/20_Projects/claude-kit/plan-2026-04-16-plan-doc-autosync.md`
- `~/vault/20_Projects/claude-kit/project-2026-04-13-vault-audit-plan.md`
- `~/vault/20_Projects/claude-kit/plan-2026-04-13-vault-bridge-write-improvements.md`
- `~/vault/00_Inbox/session-2026-04-13.md` (W0 설계 원본)
