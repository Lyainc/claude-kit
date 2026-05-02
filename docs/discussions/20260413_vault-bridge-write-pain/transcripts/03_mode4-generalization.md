# TOPIC 3: Mode 4 일반화 — artifact filing (P3)

**상태**: 합의 (만장일치)
**라운드**: 1

## Briefing
**[Optimistic Practitioner]**: 이번 세션 `docs/discussions/20260413_vault-project-link/` 6개 파일이 repo에만 존재. vault 편입 시 MOC 검색 가능.

**[Knowledge Management Expert]**: **일부**만 가치. transcripts 4개는 raw → noise. SUMMARY·UNRESOLVED만 편입 가치. 자동 감지 위험.

## Q&A
**[Critical Practitioner]**: hook 자동 감지 = inbox 범람. 메인 생성 파일 전부 흐르면 재앙.

**[UX/DX Expert]**: **명시 요청만** 처리. "이 문서 vault에 넣어줘" → skim → frontmatter 추천 → AskUserQuestion 경로 확정.

**[Plugin Architecture Expert]**: scope 경계:
- ✅ frontmatter 생성 / 파일명 컨벤션 / 경로 제안 / 쓰기
- ❌ 내용 재구성 / MOC 업데이트 / wikilink 자동 삽입 (OVM 책임, backref 제안만)

**[Knowledge Management Expert]**: frontmatter tag 추론 — `.vault-link` 있으면 프로젝트명 자동(rule-based). 도메인 태그는 제안 후 확인. LLM skim 남용 금지.

**[Critical Practitioner]**: Mode 번호 증식 금지. Mode 4를 **"vault write (session + artifact)"**로 일반화, 서브플로우 분기.

## Dialectic
**Thesis**: 자동 감지 + 새 Mode 5.
**Antithesis**: 명시 요청 + Mode 4 일반화.
**Synthesis**: 명시 요청만, Mode 4 내부 서브플로우.

## 결론
- Mode 4 역할 확장: "session note" → "vault write (session + artifact)"
- 자동 감지 금지, 명시 요청만
- bridge scope = frontmatter+경로+쓰기 / OVM scope = 내용·MOC·wikilink
- 새 Mode 번호 없음, 기존 4-mode 유지
- frontmatter는 rule-based 우선, LLM skim 보조
