---
created: 2026-05-17
tags: [claude-kit, vault-bridge, plan, remediation]
type: plan
status: active
---

# Structural Issue Remediation — §5.4 Protocol & /save-plan-doc Filter

## Background

두 이슈는 직전 세션의 vault plan status 검수에서 발견됐다. 분석·전문가 패널 합의를 거쳐 해결안이 확정됐으며, 이 문서는 구현 작업 계획이다.

## Issue 1: §5.4 Completion Protocol Simplification

### Root Cause
- `status: done` + `completed_on`을 master plan 본문과 spec frontmatter 양쪽에 유지하는 분산 상태 구조
- 이중 업데이트 프로토콜이 drift를 구조적으로 예정 → W1/W7/W8 등 8건 누락 발생

### Solution (Expert Panel Consensus)
spec frontmatter에 `implemented_in: [[project-2026-04-16-master-plan#Wn]]` 단일 필드로 교체.

- Master plan = 실행 상태 유일 SoT
- Spec = 불변 설계 문서 + 완료 포인터 (1필드)
- 완료 시 프로토콜: master plan 갱신 + spec에 `implemented_in` 한 줄 추가 (2곳 → 2액션, 단 `status/completed_on` 2필드 → 1필드)

### Implementation Tasks

**T1-1** master plan §5.4 프로토콜 텍스트 갱신 (vault)

**T1-2** done 워크스트림 spec 파일 frontmatter 일괄 수정 (vault):
- `status: done` 제거
- `completed_on: ...` 제거
- `implemented_in: [[project-2026-04-16-master-plan#Wn]]` 추가
- 대상: W0, W1, W2, W5, W7, W8, W10 spec 파일 (8건)

## Issue 2: /save-plan-doc Capture Filter Fix

### Root Cause
`DEFAULT_INCLUDE_PATTERNS`의 `"docs/discussions/**/*.md"` 패턴이 transcript, SUMMARY, UNRESOLVED를 포함한 모든 파일을 무차별 수집.
setup-wizard 설계 1건 → vault plan 8건 발생 (transcript 5 + SUMMARY/UNRESOLVED 2 + 실제 설계문서 1).

Frontmatter type 필터는 불가 — 실제 설계 문서 대부분이 YAML frontmatter 없음 (마크다운 bold 메타 사용).

### Solution (Expert Panel Consensus revised)
구조적 경로 필터: `docs/discussions/**/*.md` → `docs/discussions/*/*.md` (depth 3만).

- `transcripts/*.md` (depth 4): 자연 제외
- `SUMMARY.md`, `UNRESOLVED.md`: DEFAULT_EXCLUDE_PATTERNS 추가로 제외
- 설계 output (`analysis.md`, `dev-plan.md`, `plan.md`): depth 3, 자동 포함

### Implementation Tasks

**T2-1** `plan-doc-syncer.py`:
- `DEFAULT_INCLUDE_PATTERNS`: `"docs/discussions/**/*.md"` → `"docs/discussions/*/*.md"`
- `DEFAULT_EXCLUDE_PATTERNS`: `"*/SUMMARY.md"`, `"*/UNRESOLVED.md"` 추가

**T2-2** `save-plan-doc.md` Step 3 no-candidates 안내 문구에 discussions 필터 설명 추가

**T2-3** 기존 테스트 실행: `python3 vault-bridge/scripts/test/test-discover.py`

## Implementation Order

1. T2-1, T2-2 (코드 변경, 검증 가능)
2. T2-3 (테스트)
3. T1-1, T1-2 (vault 변경)
