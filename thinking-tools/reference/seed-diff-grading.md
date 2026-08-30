# Seed 대조 채점 지시문 — 요구사항 갭 리뷰용

`thinking-tools:code-reviewer` 에이전트(#564)가 #593에서 삭제되며 남긴 자유형 지시문.

요구사항 갭 리뷰의 기본 방법론(요구 출처 확립·3상태 판정·severity·기존 결함 분리)은 #706에서
`thinking-tools:requirement-gap-reviewer` 에이전트 본문으로 옮겨갔고, Seed 유무와 무관하게
`subagent_type` 하나로 도달한다. **이 문서는 그 위에 얹는 Seed 특수화다** — build-spec
Seed(`docs/specs/*.yaml`)가 있는 diff를 그 에이전트로 리뷰할 때, 같은 3상태를 Seed의
`constraints[]`·`success_criteria[]`에 대고 채점하도록 프롬프트에 아래 지시를 덧붙인다.
Seed가 없으면 붙이지 않아도 방법론은 이미 도달해 있다. 3상태 판정 어휘의 단일 소스는
그 에이전트 본문 §2이고, 아래 지시문은 이름을 새로 만들지 않고 거기서 빌려 쓴다.

## 지시문

```
diff를 Seed `<Seed 경로>`와 대조해 채점해줘:

1. Seed의 constraints[] 중 hard: true 항목이 diff에서 위반됐는지 확인한다.
2. Seed의 success_criteria[] 각 항목을 3상태로 판정한다:
   - 충족 — diff가 명시적으로 만족시킨다. finding으로 리포트하지 않는다.
   - 미충족 — diff가 위반하거나 구현하지 않았다. blocking 후보다.
   - 산출물로 판단 불가 — 스크립트 종료 코드·스모크 테스트 등 실행 기반 기준이라 diff만으로는
     확인할 수 없다. 리포트는 하되 blocking으로 승격하지 않는다.
3. hard 제약 위반 또는 success_criteria 미충족만 blocking으로 취급한다. 산출물로 판단 불가와
   그 외 발견은 참고용으로만 리포트한다.
```

이 3상태 판정은 2상태(충족/미충족)로는 실행 기반 기준이 매번 미충족=차단으로 잘못 승격되거나,
조용히 무시되는 두 실패 모드를 피하려는 것이다(원 설계 rationale, `docs/specs/thinking-tools-code-reviewer.yaml` c10 참고).
