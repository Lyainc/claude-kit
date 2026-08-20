# Seed 대조 채점 지시문 — 요구사항 갭 리뷰용

`thinking-tools:code-reviewer` 에이전트(#564)가 #593에서 삭제되며 남긴 자유형 지시문. 격리 단일
패스 에이전트를 다시 만드는 대신, build-spec Seed(`docs/specs/*.yaml`)가 있는 diff의 요구사항 갭
리뷰(next-goal L2 — Seed를 아는 fresh-context 서브에이전트가 맡는 갈래, correctness를 보는
네이티브 `/code-review`가 아니다)를 돌릴 때 프롬프트에 아래 지시를 그대로 덧붙여 Seed 대조 채점을
얹는다 — 그 리뷰 자체 기능은 아니고, 호출부가 매번 붙이는 자유형 지시다.

## 지시문

```
diff를 Seed `<Seed 경로>`와 대조해 채점해줘:

1. Seed의 constraints[] 중 hard: true 항목이 diff에서 위반됐는지 확인한다.
2. Seed의 success_criteria[] 각 항목을 3상태로 판정한다:
   - 충족 — diff가 명시적으로 만족시킨다. finding으로 리포트하지 않는다.
   - 미충족 — diff가 위반하거나 구현하지 않았다. blocking 후보다.
   - diff로 판단 불가 — 스크립트 종료 코드·스모크 테스트 등 실행 기반 기준이라 diff만으로는
     확인할 수 없다. 리포트는 하되 blocking으로 승격하지 않는다.
3. hard 제약 위반 또는 success_criteria 미충족만 blocking으로 취급한다. diff로 판단 불가와
   그 외 발견은 참고용으로만 리포트한다.
```

이 3상태 판정은 2상태(충족/미충족)로는 실행 기반 기준이 매번 미충족=차단으로 잘못 승격되거나,
조용히 무시되는 두 실패 모드를 피하려는 것이다(원 설계 rationale, `docs/specs/thinking-tools-code-reviewer.yaml` c10 참고).
