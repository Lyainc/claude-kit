---
name: doc-concretize

description: |
  Transform abstract concepts into concrete, well-structured documentation
  through step-by-step recursive writing with verification at each step.

  Use when the user requests documentation of abstract ideas, strategies,
  or concepts requiring structured concretization (expected output > 800 Korean characters).

  Trigger when user mentions: 구체화, 문서화, 체계적 정리, 개념 정리, 아이디어 문서화, 전략 문서, 글로 정리,
  or requests: "이 개념을 문서로 정리해줘", "아이디어를 체계적으로 구체화해줘",
  "전략을 상세 문서로 작성해줘", "비전을 실행 가능한 계획으로 풀어줘".

  Skip for: simple definitions, "짧게"/"간단히" requests, or already-structured content.
---

# Document Concretization

추상적 개념을 단계적 재귀 작성과 검증을 통해 구체적 문서로 변환한다.

## Prerequisites

- 구체화할 추상적 개념 또는 아이디어
- (선택) 참조할 원본 문서 (문체 유지용)
- (선택) 특정 형식/구조 요청

## Core Workflow

### Phase 1: Segmentation

1. 입력 분석 → 핵심 의미 단위 식별 (3-7개 청크)
2. 논리적 순서 및 의존 관계 결정
3. 예상 분량 산정 → 800자 미만이면 일반 작성으로 전환
4. 원본 문서 있으면 문체 분석 및 기록

**State Tracking** (권장):
```json
{"segments": ["seg1", "seg2", ...], "current": 0, "style_ref": "user_doc.md"}
```

### Phase 2: Recursive Build

각 세그먼트마다 **Build → Verify → Reflect** 순환:

```
[Build]
1. 이전 섹션 컨텍스트 로드
2. 현재 섹션 초안 작성
   - 간결하고 직관적인 문장
   - 디테일 누락 없이

[Verify]
□ 이전 내용과 논리적 연결?
□ 모순 또는 중복 없음?
□ 톤앤매너 일관성?
□ 원본 문체 유지? (있을 경우)

[Reflect]
- 검증 실패 시: 수정 후 재검증 (최대 2회)
- 불확실한 부분: 마킹 후 진행
- 팩트체크 필요: AskUserQuestion 또는 WebFetch 호출
```

**Critical Issue** (사용자 승인 필요):
- 핵심 전제의 해석이 여러 가지 가능
- 상충하는 정보 발견
- 민감한 주장/판단 포함

### Phase 3: Final Review

1. **통독**: 전체 문서 처음부터 끝까지 검토
2. **Self-Critique**: "이 문서에서 잘못될 수 있는 것은?"
3. **의도 검증**: 원래 요청과의 정렬 확인
4. **누락 점검**: 핵심 내용 빠짐 없는지

### Phase 4: Polish

**맞춤법** (필수):
- 띄어쓰기, 맞춤법, 조사 오류 수정

**문체 다듬기**:
- LLM 특유 표현 제거: "매우", "정말", "확실히", "다양한" 남발
- 불필요한 수식어 축소
- 문장 길이 균형 (15-30자 권장)
- "~입니다/~습니다" 남용 시 "~다/~이다" 혼용

**원본 문체 유지** (참조 문서 있을 경우):
- 사용자 어투/문체 최대한 반영
- 톤 변경 필요 시 사용자 확인

## Tool Usage

| 도구 | 시점 | 예시 |
|------|------|------|
| AskUserQuestion | 모호한 개념 명확화, Critical Issue | "X와 Y 중 어느 의미인가요?" |
| WebFetch | 팩트체크 (수치, 인용, 외부 정보) | 통계 수치 검증 |

## Output

```
[완성된 문서]

---
<details>
<summary>작성 프로세스</summary>

- 분절: N개 섹션
- 검증 통과: N/N
- 수정 항목: (있으면)
- 문체 참조: (있으면)
</details>
```

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)

## Quick Start

```
User: "우리 서비스의 핵심 가치를 문서화해줘.
       고객 중심, 빠른 실행, 투명성이 중요해."

→ Phase 1: 3개 세그먼트 분절 (고객 중심 / 빠른 실행 / 투명성)
→ Phase 2: 각 세그먼트 재귀 작성 + 검증
→ Phase 3: 전체 흐름 검토, self-critique
→ Phase 4: 교정/교열
→ Output: 구조화된 핵심 가치 문서 (~1,500자)
```
