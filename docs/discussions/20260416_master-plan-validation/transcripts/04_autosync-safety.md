# Transcript 04 — plan-doc-autosync의 W0 의존과 안전장치

**[Moderator]**: PostToolUse/SessionEnd hook + AskUserQuestion + Dry-run + opt-in 4중 안전장치. 충분한가, W0 의존 구조는 타당한가.

**[LLM Orchestration Expert]**: 4중 안전장치 + 결정론 쉘 스크립트. Stop hook 교훈(LLM 루프) 반영. 원칙은 안전.

**[Critical Practitioner]**: 그러나 PostToolUse/SessionEnd가 매 턴 fire. false-positive 감지 리포트가 AskUserQuestion 과다 호출하면 **알람 피로**. 사용자가 "무조건 취소" 모드로 진입 → 자동화 무력화.

**[Project Manager]**: 경험 일치. 제안: SessionEnd 1회 일괄만. PostToolUse 실시간은 DEBUG 전용으로 영구 비공개 유지. **세션당 제안 상한 1회**.

**[Knowledge Management Expert]**: "단방향 스냅샷" 원칙은 옳다. 단 vault가 SSOT여야 지식이 쌓이는데 코드 리포의 `docs/plans/`가 진짜 원본이면 vault 스냅샷은 stale 위험. 메타로 박제 필요: `source_path`, `source_commit`, `captured_at`.

**[DX/Tooling Expert]**: 감지 경로 `docs/(discussions|design|plans)/**/*.md`가 모든 프로젝트에 통용되지 않음. 프로젝트마다 구조 상이. `.vault-link`에 `autosync_paths: [...]` 프로젝트별 override 허용.

**[Optimistic Practitioner]**: W0 의존 — Topic 1의 W0 MVP 분해 합의와 연결되면 해소.

**[LLM]**: `source_commit` 획득 불가 시(untracked, dirty tree 등) 폴백이 초안에 없음. 별도 미해결로 남길 것.

**[Moderator]**: 정리: (a) PostToolUse 실시간 모드 초기 릴리스 제외, (b) 스냅샷 메타 3필드 필수, (c) `.vault-link`에 `autosync_paths` 오버라이드, (d) 세션당 1회 제안 상한, (e) `source_commit` 폴백은 UNRESOLVED.md 등록.

**전원 합의.**

**결론**: 조건부 합의. 위 5개 수정 반영 전제. 폴백 정책은 별도 미해결.
