# Vault Second Brain v4 — 세션 재개 프롬프트

> 작성일: 2026-05-26 · 갱신: 2026-05-28
> 용도: 다음 세션에서 이 작업을 이어갈 때 컨텍스트 복원용
> 사용법: 새 세션 시작 시 이 문서 내용을 그대로 프롬프트에 붙여넣거나, "@docs/plans/vault-second-brain-v4-resume.md 읽고 작업 이어가자"로 호출

---

## 진행 요약 (2026-05-28 갱신)

| PR | 항목 | 실제 PR | 상태 |
|---|---|---|---|
| PR 1 | vault-bridge 폴더 패턴 갱신 (`inbox/notes/assets`) | #83 | ✅ 2026-05-26 |
| PR 2 | OVM 7→3 스킬 정리 (`capture/note/audit`) | #84 | ✅ 2026-05-26 |
| PR 3 | Capture 강화 + Web Clipper 템플릿 | #85 | ✅ 2026-05-26 |
| **PR 4** | `/audit` Phase 1 (Steps 0-5, 분할 진행) | — | 부분 완료 |
| ↳ 4a | Phase 1 expansion — P0/P2 priority + manifest display | #86 | ✅ 2026-05-26 |
| ↳ 4b | Phase 2 stagnation — E6/E7 (P1) | #87 | ✅ 2026-05-27 |
| ↳ 4c | Step 0 — 시스템 메타 재계산 (manifest write-side) | #89 | ✅ 2026-05-28 |
| ↳ 4d | Step 3 — Promotion Candidate (P2, Step 0 의존) | — | ✅ 2026-05-28 |
| ↳ 4e | Step 4 — Git 활동 요약 (P3, 독립) | — | 대기 |
| PR 5 | `/vault-commit` 메시지 컨벤션 자동화 | — | 미완 (독립, 병렬 가능) |
| PR 6 | 마이그레이션 dogfood | — | 대기 (audit 완료 후) |
| PR 7 | README + onboarding v4 반영 | — | 마지막 |

**즉시 다음**: **PR 4e (Git 활동 요약)** 또는 **PR 5 (`/vault-commit` 컨벤션)** — 둘 다 독립, 병렬 진행 가능.

**병렬 가능**: PR 5 (`vault-commit` 컨벤션)는 audit과 독립 — 다른 세션에서 동시 진행 가능.

**Deferred**: Step 5 (Phase 2 패턴 추출)는 decision 노트 데이터 축적(3-6개월) 후 활성화.

---

## 컨텍스트

claude-kit 프로젝트(`/Users/Lyainc/dev/prj/claude-kit`, branch: `feat/stage4-sidecar`)에서 vault second brain 시스템을 **v4로 단순화하는 대규모 작업** 진행 중. 설계·마이그레이션 가이드는 두 문서로 확정됨. 다음 단계는 **구현 PR 시리즈**.

## 필수 선행 읽기 (순서대로)

1. `docs/design/vault-second-brain-v4.md` — 전체 설계 (413줄, 12 섹션)
2. `docs/plans/vault-second-brain-v4-migration.md` — 마이그레이션 가이드 (458줄, 10 섹션)
3. `CLAUDE.md` — 프로젝트 규칙·플러그인 구조·검증 명령

## 핵심 원칙 (가드레일 — 흔들리면 안 됨)

- **Cabinet/Brain 이중 모드**: 기본은 cabinet (Obsidian + git만 동작). `/audit`가 brain화 의식. 자동 push 없음.
- **type 옵트인**: `type:` 필드 있는 노트만 claude-kit 관리. 없으면 invisible. *사용자 파일 자동 변경 금지*.
- **Stand-alone**: Obsidian + Claude Code + git 외 의존 X. omc·graphify·llm-wiki·claude-mem 등 외부 플러그인 의존 추가 절대 금지.
- **미니멀**: 3 폴더 (`inbox/notes/assets`) + OVM 스킬 3개 (`capture/note/audit`) + Type 5개 (`capture/note/decision/session/plan`).
- **Recall이 핵심**: capture만 강화로는 brain 안 됨 (LLM Wiki 실패 교훈). `/audit`이 단일 brain 채널.
- **데이터 안전**: 마이그레이션은 옵트인, 충돌 시 `mv -n` + skip + 로그. 덮어쓰기 절대 금지.
- **시스템 메타는 manifest 전용**: 노트 frontmatter는 사용자가 정한 값만. `references_in/out`·`access_count`·`promotion_candidate`는 `manifest.json`에만.

## 구현 PR 시리즈

### PR 1 — vault-bridge 폴더 패턴 갱신 (#83, ✅ 2026-05-26)

**파일**:
- `vault-bridge/hooks/pre-write-guard.sh`: `00_Inbox` → `inbox`, `30_Notes` → `notes`, `90_Assets` → `assets`. 20_Projects·10_MOC·40_Resources·50_Archive 패턴 제거. type 없는 노트 통과.
- `vault-bridge/scripts/generate-manifest.py`:
  - `EXCLUDED_DIRS` 갱신 (제거된 폴더 처리)
  - **type 필터**: `type:` 필드 없으면 manifest entry 생성 X (옵트인)
  - **시스템 메타 추적**: `references_in` (in-bound wikilink 수), `references_out` (out-bound), `access_count` (git log `--follow` 기반), `promotion_candidate` 계산
- `vault-bridge/agents/vault-searcher.md`: 경로 갱신, Mode 1/2/3 출력 경계 명세 정비 (설계 §6.1)
- `vault-bridge/commands/save-session.md`, `save-plan-doc.md`: 저장 경로 갱신
- 회귀 테스트: `vault-bridge/scripts/test/*` 갱신 (`test-pre-write-guard.py` 등)

### PR 2 — OVM 7 → 3 스킬 정리 (#84, ✅ 2026-05-26)

**제거됨**: `project/`, `inbox-review/`, `context/`, `archive/`, `vault-audit/`
**유지·갱신**: `capture/` (inbox/ 경로), `note/` (notes/ 경로 + decision type + status machine), `audit/` (vault-audit 리네임, E1-E5 only)
**갱신**: `agents/vault-knowledge-manager.md` 3-skill, `vault-file-organizer.md` v4 경로, `plugin.json`·`marketplace.json` v0.13.0

**설계 대비 달라진 결정 (의도적)**:
- **decision type**: PR 2에서 `note` 스킬에 `--type decision` 플래그로 구현 (원래 미정이었던 부분 선결)
  - `notes/decision-YYYY-MM-DD-{slug}.md` 패턴; 4섹션 body 템플릿 (문제/선택지/결정/근거)
- **E6-E9 영구 제거**: vault-audit의 project-binding 검사(E6/E7/E8/derived)는 20_Projects/ 폴더가 v4에서 사라지므로 audit에 이월 없이 제거. PR 4에서 manifest-level 검사로 대체 예정
- **E3 regex**: `^\d{4}-\d{2}-` (year-month prefix 감지). 원래 `YYYY-MM-DD` full date를 가정했으나 fixture 파일명이 `2026-04-` 형식이었음. 더 관대한 패턴이 정확함
- **vault-file-organizer.md** v4 경로 업데이트 (PR 2 원래 스펙 밖이었으나 필요해서 포함)
- **vault-audit-rules.md**: E6-E9 섹션 제거, E3/E5 v4 경로 갱신
- **vault-audit error-taxonomy.md, measurement.md 삭제**: v3-only 참조 문서, v4에서 불필요
- **DoD 기준 갱신**: 9 타입(E1-E9) → 5 타입(E1-E5). 각 타입 seeded_detected=5, fp_on_clean=0 달성

### PR 3 — Capture 강화 + Web Clipper 템플릿 (#85, ✅ 2026-05-26)

- `obsidian-vault-manager/skills/capture/SKILL.md`:
  - 다중 URL 병렬 defuddle: `/capture url1 url2 url3`
  - 인자 없음 = `inbox/`의 `status: raw` 일괄 처리
  - type 전이 (capture → note) 명세 (설계 §5.2)
- `obsidian-vault-manager/reference/web-clipper-template.md` 신규 (설계 §5.1)

### PR 4 — `/audit` Phase 1 (sub-PR로 분할 진행)

원래 단일 PR로 계획됐으나 v4 §6.1 Step 별 점진 검증이 안전해 sub-PR로 분할. 4a/4b 완료, 4c~4e 미완.

**PR 4a — Phase 1 expansion** (#86, ✅ 2026-05-26)
- P0/P2 priority mapping + manifest summary (read-only `file_count` + `generated_at`)
- `PRIORITY_BY_TYPE` drift detector (`priority_mismatches` DoD 필드)
- E2 status-missing sub-fixture (10 = 5 base + 5 status-missing)

**PR 4b — Phase 2 stagnation** (#87, ✅ 2026-05-27)
- E6 `stale_inbox` (P1, inbox raw + created > 14d, type:session 자동 제외)
- E7 `stale_draft` (P1, notes draft + created > 30d, `_index.md` skip)
- `parse_created_date()` + 13-case 단위 테스트
- handoff SessionStart UX (resume.md compact display) — 같은 PR에 묶었으나 향후엔 분리

**PR 4c — Step 0: 시스템 메타 재계산** (#89, ✅ 2026-05-28)
- `vault-bridge/scripts/generate-manifest.py` write-side 확장:
  - `references_in` (해당 노트로 들어오는 wikilink 수)
  - `references_out` (해당 노트가 내보내는 wikilink 수)
  - `access_count` (`git log --follow` 기반 빈도)
  - `promotion_candidate` (Step 3에서 사용할 플래그)
- SCHEMA_VERSION=3 (pre-v3 manifests gracefully skipped by audit-validate)
- audit이 read-side에서 활용 — `read_manifest_summary`가 `promotion_candidate_count` 집계
- env vars: `VAULT_AUDIT_PROMOTION_REFS=3`, `VAULT_AUDIT_PROMOTION_ACCESS=5`

**PR 4d — Step 3: Promotion Candidate** (#90, ✅ 2026-05-28)
- 트리거: PR 4c가 manifest에 심은 `promotion_candidate: true` 엔트리를 audit-validate가 소비
- 스코프: `type: note` 또는 `type: decision`만 (§3.3 승격 자격, manifest가 이 필터 적용)
- `E8_promotion_candidate` (P2/Info) finding 추가 — `_promotion_candidates_from_manifest()` 헬퍼
- 출력: `refs_in={r}, access={a} (manual: status→evergreen)` 상세
- Phantom 가드: 매니페스트 stale 엔트리(파일 삭제됨) skip
- Fixture: ring-linker 3개 + access-target manifest patch → DoD `E8:2` / `fp:0`

**PR 4e — Step 4: Git 활동 요약** (독립, 작은 작업, P3)
- 지난 7일 vault 활동: commit 수, 추가/수정/archive 파일 카운트
- `git log --since="1 week ago" -- $VAULT_ROOT` 기반
- audit REPORT 헤더에 1-2줄 요약 추가 (정체/promotion 섹션과 분리)
- 의존 없음 — 4c/4d 진행과 병렬 가능

**Step 5 (Phase 2 패턴 추출)** — 데이터 축적 3-6개월 후 deferred. decision 노트가 임계 N 도달 시 활성. 현재 단계에선 비활성 유지.

### PR 5 — `/vault-commit` 메시지 컨벤션 (PR 1 후, 병렬 가능, ⏳)

- `vault-bridge/commands/vault-commit.md`:
  - status 전이 감지 → 자동 commit message
  - 형식: `note(promote): {file} {raw→draft}`, `decision(create): {file} - {problem}` 등 (설계 §4.2)

### PR 6 — 마이그레이션 dogfood (PR 1-5 후, ⏳)

- 우리 vault에 `docs/plans/vault-second-brain-v4-migration.md` 절차 실행
- `v4-migration-snapshot` git tag 필수
- 충돌·skip 로그 검토
- 결과·발견된 이슈는 capture 또는 decision 노트로 vault에 기록
- 발견된 문제는 PR 1-5 핫픽스

### PR 7 — README + onboarding (마지막, ⏳)

- claude-kit 루트 README v4 반영
- OVM README 신규 (3 스킬 워크플로우)
- vault-bridge README 갱신 (변경 명세)
- 신규 사용자 onboarding: `mkdir + git init + /vault-link + /capture` 5분 데모

## 작업 시 주의

1. **검증 우선**: vault-bridge 변경 후 `bash -n hooks/*.sh` + `python3 scripts/test/test-*.py` 실행. CLAUDE.md §Validation 참조.
2. **마이그레이션 dogfood 전 우리 vault git snapshot 필수**: `cd ~/vault && git add -A && git commit -m "snapshot" && git tag v4-migration-snapshot`
3. **type 옵트인 원칙 흔들리지 말 것** — 사용자 파일을 자동으로 변경하지 않음. 마이그레이션 스크립트가 `has_type()` 필터를 거치는지 매번 확인.
4. **외부 플러그인 의존 추가 금지** — omc·graphify·llm-wiki·claude-mem 등.
5. **critic 모드 유지** — 가드레일 위반 시 즉시 짚을 것. 사용자가 push해도 옵션 trade-off 명시.
6. **PR 단위 분리**: 한 commit/PR에 여러 PR 묶지 말 것. 회귀 추적 가능성 우선.

## 잔여 의심점 (구현 중 결정 필요)

설계 §11 표 10개 항목 참조. 특히:
- audit 호출 빈도 자연 유도 (README 가이드 톤)
- audit 출력 우선순위 (P0~P3 + 접힘 기본 UI/UX)
- 한국어 slug 변환 정책 (transliteration vs 한글 보존)
- Phase 2 트리거 N값 (dogfood 데이터 보고 결정, 3-6개월 후)

## 첫 액션 (세션 시작 시)

1. **이 문서 + 두 설계 문서 읽기** (위 §필수 선행 읽기)
2. `git log -10` + `git status`로 현재 상태 파악 (PR #90까지 머지된 상태인지 확인)
3. **다음 PR 선택** — 셋 다 독립이라 순서 자유:
   - **PR 4e** (Git 활동 요약, P3): audit REPORT 헤더에 지난 7일 commit/추가/수정 카운트 추가. 가장 작음.
   - **PR 5** (`/vault-commit` 컨벤션, P2): status 전이 감지 → 자동 commit message. 설계 §4.2 참조.
   - **PR 6** (마이그레이션 dogfood) 는 PR 4e + 5 후 진행 (작은 PR 먼저 모아두는 게 안전).
4. 변경 후 즉시 회귀 테스트 + 커밋 (CLAUDE.md §Validation 참조)
5. PR 단위 push, 다음 PR로 이동

**병렬 권고**: PR 4e와 PR 5는 서로 독립 — 다른 세션·브랜치에서 동시 진행 가능.

**과거 PR 분할 결정 기록**: PR 4를 sub-PR (4a~4e)로 분할한 것은 의도된 결정. 단일 큰 PR로 묶으면 회귀 추적이 어렵고 검증 단위가 모호해져요. Step 별 DoD를 명확히 떨어뜨려 진행하세요.

## 컨텍스트 압축 대비

이 작업은 *대규모*라 컨텍스트가 압축될 가능성 큼. 압축 후 재진입 시:
- 이 문서 (`docs/plans/vault-second-brain-v4-resume.md`)를 *반드시* 다시 읽기
- 위 §핵심 원칙 (가드레일) 다시 확인
- 진행한 PR 번호 확인 (`git log --oneline | grep -E "PR [0-9]"`)

## 관련 파일

- 설계: `docs/design/vault-second-brain-v4.md`
- 마이그레이션: `docs/plans/vault-second-brain-v4-migration.md`
- 토론 transcript: 이전 세션 (vault-bridge `/save-session`으로 저장됐다면 vault에 있을 것)
- 외부 검증: critic 토론 7라운드, document-specialist 외부 도구 4개 검토, critic 13개 빈틈 점검
