# Transcript 05 — `_index` 스키마 확장이 Obsidian/워크플로에 부담인가

**[Moderator]**: `_index.md` 프런트매터 4 필드 → 8+ 필드 확장. UX/워크플로 부담 검증.

**[Knowledge Management Expert]**: Obsidian Properties가 YAML을 네이티브 UI로 편집. 배열 필드는 multi-select UI로 표시. Dataview 궁합도 최고. UX 부담 낮음.

**[Critical Practitioner]**: 필드 수 2배는 체감적. 옵션 필드라도 빈 섹션이 누적되면 지저분. 신규 프로젝트 생성 시 부담.

**[Project Manager]**: 필드 수보다 **생명주기 명시**가 핵심. 제안 — `_index`에 필드별 "언제 채우는가" 문서화:
- 생성 시점(5 필수): created, tags, type, status, domain
- 첫 세션 후(자동): last_session
- vault-link 연결 후: vault_link_source
- note 승격 후: absorbs
- 작업 중: related_notes
- opt-in: auto_capture

**[Optimistic Practitioner]**: PM 제안 따르면 한 번에 모두 채울 필요 없음. 점진 enrichment.

**[DX/Tooling Expert]**: vault-bridge가 신규 `_index` 생성 시 **기본 템플릿 최소 필드**만, 나머지는 스킬·감사가 append. 사용자가 YAML 직접 쓸 필요 없음.

**[LLM Orchestration Expert]**: 배열 필드(특히 absorbs, related_notes) 비대 위험. 100개 absorb 시 YAML 300줄. **사이즈 상한 + overflow 전략** 필요.

**[KM]**: 100개 absorbs는 비정상. 프로젝트가 너무 커졌다는 의미론적 신호. 감사가 "split project" 경고 발하는 게 맞음. **기술적 상한보다 의미론적 경고**가 낫다.

**[PM]**: KM 동의. 감사가 경고 책임.

**[Moderator]**: 정리: (a) 필드 생명주기 Binding plan 문서화, (b) 기본 템플릿 5개 필수 필드만, (c) 배열 overflow는 감사의 의미론적 경고, (d) Dataview 쿼리 예시로 실사용 패턴 검증.

**전원 합의.**

**결론**: 합의. 생명주기 + 최소 템플릿 + 의미론적 경고 조합.
