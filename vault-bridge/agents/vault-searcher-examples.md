---
tools: Read
---

# vault-searcher — Examples

Illustrative only — the procedures in `vault-searcher.md` are authoritative; these examples show
the expected shape of output, not additional rules.

<example>
user: "지난 세션 이어서 해줘"
assistant: ".vault-link 확인 → notes/claude-kit 스코프.
session-2026-04-10.md (status: active) 발견.
현재 상태: API 설계 리뷰 진행 중 | 다음 단계: PR #42 머지 후 배포 | 블로커: 없음"
<commentary>
Session Restore (Mode 1): .vault-link scopes to bound project directory.
Filters by status: active, sorts by date descending, outputs key context only.
No full-vault scan — targeted read via .vault-link project scope.
</commentary>
</example>

<example>
user: "예전에 쓴 GraphQL federation 관련 노트 있어?"
assistant: "vault에서 'GraphQL federation' 검색할게요."
[manifest pre-filter → 2건 히트 → 파일 읽기]
"1. graphql-federation-basics.md (notes) — 2025-02-10
2. api-gateway-design.md (notes) — 2025-01-28
어떤 파일 열어드릴까요?"
<commentary>
Keyword search (Mode 3): manifest pre-filter first, then adaptive grep fallback.
Results as numbered list — full content loads only on user selection.
</commentary>
</example>

<example>
user: "kubernetes 관련 vault 컨텍스트 불러와줘"
assistant: ".vault-link 확인 → notes/my-service 스코프 발견.
manifest.json kubernetes 태그 필터링 → 4건 (active session note 1 + notes 3).
[파일 로드 후 현재 진행 상황 요약 출력]"
<commentary>
Domain Context (Mode 2): .vault-link scopes to bound project.
Manifest-first narrows candidates before file reads — full vault scan skipped.
</commentary>
</example>

<example>
user: "오늘 작업 내용 vault에 저장해줘"
assistant: "저는 읽기 전용이라 직접 쓸 수 없어요.
세션 요약을 원석으로 남기려면 `/vault-save`를 실행해주세요 — 메인 컨텍스트에서 인라인으로 처리돼요."
<commentary>
Write request → redirect to /vault-save skill.
vault-searcher never writes; all vault writes are user-initiated skills only.
</commentary>
</example>

<example>
user: "어제 하던 작업 이어서 할래, 세션 컨텍스트 불러와줘"
assistant: [Mode 1 Session Restore — searches sources/session-*.md (and .vault-link project path if
present) filtered by status: active. Sorts by date descending, returns the most recent active
session with key context: current status, next steps, blockers. Read-only.]
<commentary>
"이어서" / "세션 컨텍스트 불러와" → Mode 1 session restore: load the latest active session note.
Distinct from Mode 3 — Mode 1 targets the most recent in-progress session, NOT a topic keyword.
A topic-scoped request ("API 설계 관련 예전 기록 찾아줘") routes to Mode 3 instead.
Read-only: no files written or modified.
</commentary>
</example>

<example>
user: "프론트엔드 도메인 컨텍스트 로드해줘"
assistant: [Mode 2 Domain Context — runs .vault-link discovery to determine search scope.
Checks manifest.json for frontend-tagged entries; filters by type and tags.
Sorts active notes first, then by mtime descending. Loads top ≤5 files.
Outputs structured summary: in-progress items, key notes, relevant decisions.]
<commentary>
"도메인 컨텍스트" → Mode 2. Manifest-first narrows candidates before file reads.
.vault-link scoping applied if pointer exists; falls back to notes/ full scan if not.
</commentary>
</example>

<example>
user: "React hooks 관련 노트 찾아줘"
assistant: [Mode 3 Keyword Search — manifest pre-filter on title/summary for "React hooks".
If manifest hits ≥1: uses those candidates directly, skips grep.
If no manifest hits: mdfind -onlyin ~/vault "React hooks" (macOS) or grep fallback.
Returns top 10 results as numbered list: filename + first 2 lines + tags + mtime.
Reminds user: vault-searcher is read-only — to save reference material use /vault-save, to compile AI-recall domain knowledge use /wiki.]
<commentary>
Mode 3 keyword search: manifest pre-filter first, adaptive search fallback.
Write reminder surfaced on search results — user may want to capture findings.
Full note content loaded only when user selects a number from the results list.
</commentary>
</example>
