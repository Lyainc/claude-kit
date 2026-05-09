# Transcript 01 — Flag System Robustness

## Participants
Moderator, Optimistic Practitioner, Critical Practitioner, PKM Expert, Architecture Expert, Performance Expert, Data Integrity Expert

## Briefing

**[Optimistic Practitioner]**: 플래그는 대규모 볼트에서 필수. 1000개 노트 중 800개가 clean이면 스캔 비용 80% 절감. tree-hash로 invalidation도 결정론적.

**[Critical Practitioner]**: tree-hash 계산이 실제로 싸지 않음. 800개 파일 해싱해야 skip 판정 가능. "스캔 안 하려고 스캔"하는 역설. frontmatter에 `audit_clean_hash` 심으면 자기 무효화 루프 위험.

## Q&A

**[Data Integrity Expert]**: (1) 해시 소스에서 frontmatter 자기필드 제외. mtime+size 조합이면 충분. `find -newer .audit-state/LAST_SCAN`이면 hash 자체 불필요. (2) frontmatter는 사용자 실수로 덮일 위험. sidecar 권장: `.obsidian/audit-state.json`.

**[PKM Expert]**: Obsidian 사용자는 frontmatter 오염 싫어함. dataview 쿼리 오염, MOC 노출 시 보기 안 좋음. sidecar가 PKM 관행 부합. `_index.md`는 예외 허용.

**[Architecture Expert]**: 플래그 시스템을 독립 모듈로. `vault-audit`, `inbox-review`, 향후 스킬이 공통 조회/무효화.

**[Performance Expert]**: mtime 필터면 10만 노트도 1초 내. 핵심은 "변경된 것만 읽기". 외부 도구가 mtime 뭉개는 경우만 `--force` 대비.

## Dialectic

- Thesis: frontmatter + tree-hash
- Antithesis: sidecar + mtime
- Synthesis: Sidecar `.obsidian/audit-state.json` + mtime 필터 기본, `_index.md` 병기 허용, `--force` 옵션

## Conclusion

**결론**: Sidecar 저장 + mtime 변경 감지 채택. 자기참조 해시 루프 회피, Obsidian 관행 존중.
