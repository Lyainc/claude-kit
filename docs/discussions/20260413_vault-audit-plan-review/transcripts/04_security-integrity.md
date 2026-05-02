# Transcript 04 — Security & Data Integrity

## Briefing
- [Security] Mutating 작업 기본 dry-run, `--apply` 필요
- [Data Integrity] 롤백 메커니즘 — git vs non-git 분기

## Q&A
- [Data Integrity] git 볼트 → 단일 커밋 롤백. 비-git → `.ovm/backups/SESSION/` 원본 복사. `.git` 감지로 자동 분기.
- [DevEx] Sidecar 손상 graceful degradation: 파싱 실패 시 전체 재스캔, `.bak` 1회분 순환, `--reset-state`.
- [Architecture] 리네이밍 역참조 업데이트는 위험 → Phase B v1은 감지만, 실행은 별도.
- [Critical] Dry-run 기본이면 "실행 안 됨" 불만 가능 → 결과 확인 후 Q3로 승인 시 자동 apply.
- [Optimistic] plan → confirm → apply 흐름 표준적, 수용 가능.

## Dialectic
- Thesis: 바로 실행
- Antithesis: 항상 dry-run
- Synthesis: dry-run 디폴트 + Q3 승인 → apply, git/non-git 자동 분기, 리네이밍 감지만 v1

## Conclusion
계획서 반영: 기본 dry-run, `--apply`, 롤백 분기 메커니즘, sidecar `.bak` 순환 + fallback + `--reset-state`, 리네이밍 v1 감지 한정.
