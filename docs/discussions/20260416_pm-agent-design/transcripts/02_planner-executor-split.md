# Transcript 02 — Planner/Executor 분리의 효과와 함정

**[Moderator]**: MECE 분리의 실제 성능·안전 이득 논의.

**[LLM Orchestration Expert]**: 분리 효과 3가지:
1. Planner opus — 분석 구간에만 고비용 지출
2. Executor sonnet — 스펙 기계 적용
3. Self-approval 금지 원칙 자연 구현 (서로 다른 에이전트)
4. Context 수명 분리 — planner 오염 없이 executor 작업

**[Project Manager]**: Agile 시니어-주니어 패턴과 유사. 다만 **핸드오프 인터페이스 명세화** 필수.

**[Knowledge Management Expert]**: artifact 형식 제안 —
```yaml
changes:
  - action: write | edit | frontmatter_patch
    path: ~/vault/...
    content | patch: ...
```
Executor는 의미 판단 없이 기계 처리.

**[Optimistic Practitioner]**: OMC의 기존 executor(sonnet) 재사용 가능. planner만 신규 구현.

**[Critical Practitioner]**: OMC executor가 vault 컨벤션(파일명·frontmatter·wiki-link)을 자동 준수하지 않음. 전용 executor 또는 vault-aware 래퍼 필요.

**[Plugin Architecture Expert]**: artifact 포맷을 **재사용 가능한 스키마**로 정의(JSON Schema 또는 구조화 MD). 나중에 executor 교체가 쉬워짐.

**[LLM Orchestration]**: 함정 — planner → executor만으론 부족. **Verifier(제3)** 필요. MECE 3축: Plan → Execute → Verify. OMC verifier 재사용 가능.

**[PM]**: 합의. 추가로 artifact 생성 전 AskUserQuestion 승인 단계.

**[Moderator]**: 정리 — (a) 3층 구조(planner/executor/verifier), (b) 핸드오프 구조화 Markdown, (c) 사용자 승인 포인트 2회(전략·개별), (d) Executor는 OMC 재사용 + vault adapter preamble.

**전원 합의.**

**결론**: 3층 구조 채택. planner만 신규, executor/verifier는 OMC 재사용.
