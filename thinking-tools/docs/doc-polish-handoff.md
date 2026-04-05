# doc-polish Skill Design Handoff

doc-concretize와 doc-polish 스킬의 역할 분리 및 신규 스킬 설계 문서.

## 배경

### 문제 인식
- MD 파일 Lint 자동 수정 훅 검토 중 단독 스킬로는 임팩트 부족 판단
- doc-concretize Phase 4 "Polish"가 표현 품질 작업 포함 → 역할 중복 가능성
- 콘텐츠 생성과 표현 다듬기가 혼재된 구조

### 해결 방향
- doc-concretize: 콘텐츠 생성에 집중 (Writer)
- doc-polish: 표현 품질 검증/개선에 집중 (Editor)

---

## 핵심 분리 원칙

| | **doc-concretize** | **doc-polish** |
|---|---|---|
| **비유** | 작가 (Writer) | 편집자 (Editor) |
| **핵심 질문** | "무엇을 쓸 것인가?" | "어떻게 더 잘 표현할 것인가?" |
| **입력** | 추상적 아이디어/개념 | 기존 MD 문서 |
| **출력** | 구조화된 초안 | 검증/개선된 최종본 |
| **Focus** | 콘텐츠 생성, 논리 구조 | 표현 품질, 정확성, 일관성 |

---

## doc-concretize 개선 방향

### 현재 구조
```
Phase 1: Segmentation → Phase 2: Build → Phase 3: Review → Phase 4: Polish
```

### 개선 구조
```
Phase 1: Analysis → Phase 2: Structure → Phase 3: Build → Phase 4: Verify
                                                              ↓
                                                    (선택) doc-polish 연계
```

### Phase별 변경

| Phase | 현재 | 개선 |
|-------|------|------|
| 1 | Segmentation | **Concept Analysis** - 개념 분해 + 관계 매핑 |
| 2 | Recursive Build | **Structure Design** - 문서 아키텍처 설계 |
| 3 | Final Review | **Content Build** - 섹션별 작성 + 논리 검증 |
| 4 | Polish (제거) | **Completeness Check** - 누락/모순 최종 확인 |

### 제거 항목 (→ doc-polish로 이관)
- LLM Expression Blacklist
- Sentence Length Guidelines
- Language-Specific Polish rules
- 표현 수준의 Tone/Manner 조정

### 강화 항목
- **Concept decomposition**: 복잡한 개념을 원자 단위로 분해
- **Dependency mapping**: 개념 간 선후 관계 명시
- **Logical completeness**: 논리적 빈틈 탐지 강화
- **Argument structure**: 주장-근거-예시 구조 검증

---

## doc-polish 설계

### 핵심 역할
기존 문서의 **표현 품질 검증** 및 **자동 개선**

### 3-Layer 검증 구조

```
Layer 1: Mechanical (기계적)
   ├── Markdown Lint (자동 수정)
   ├── Link Validation (내부/외부)
   └── Code Block Syntax Check

Layer 2: Linguistic (언어적)
   ├── LLM Trace Detection (AI 흔적 탐지)
   ├── Term Consistency (용어 일관성)
   ├── Sentence Quality (길이, 복잡도)
   └── Tone Uniformity (톤 균일성)

Layer 3: Semantic (의미적)
   ├── Vague Claim Detection ("약 80%", "많은")
   ├── Outdated Info Flag (버전, 날짜)
   └── Missing Context Alert (설명 없는 전문용어)
```

### Layer 1: Mechanical (자동 수정)

| 기능 | 도구 | 동작 |
|------|------|------|
| Lint Fix | markdownlint --fix | 자동 수정 |
| Link Check | markdown-link-check | 깨진 링크 리포트 |
| Code Block | 언어 태그 검증 | 누락 시 추천 |

### Layer 2: Linguistic (탐지 + 제안)

| 기능 | 탐지 대상 | 출력 |
|------|----------|------|
| LLM Trace | "매우 중요한", "다양한 방법으로" 등 | 대체 표현 제안 |
| Term Consistency | "사용자/유저", "설정/구성" | 통일 후보 제시 |
| Sentence Length | 50자 초과 문장 | 분리 제안 |
| Tone Check | 존댓말/반말 혼용 | 불일치 위치 표시 |

### Layer 3: Semantic (경고)

| 기능 | 탐지 대상 | 출력 |
|------|----------|------|
| Vague Claims | "약", "대략", "수천 개" | 구체화 권고 |
| Outdated Info | 버전 번호, 연도 | 최신 여부 확인 요청 |
| Unexplained Terms | 정의 없는 약어/전문용어 | 설명 추가 권고 |

---

## 경계 명확화

| 구분 | doc-concretize | doc-polish |
|------|---------------|------------|
| **트리거** | "구체화해줘", "문서로 만들어줘" | "검사해줘", "다듬어줘", `/polish` |
| **입력 조건** | 추상적 개념/아이디어 | 기존 MD 파일 |
| **콘텐츠 변경** | ✅ 생성 | ❌ 보존 (표현만 수정) |
| **구조 변경** | ✅ 설계 | ❌ 보존 |
| **표현 품질** | 기본 수준 | ✅ 심층 검증/개선 |
| **외부 검증** | ❌ | ✅ 링크, 버전, 사실 |
| **자동 수정** | ❌ | ✅ (Lint, 용어) |

---

## 시너지 사용 예시

### 파이프라인 사용

```
사용자: "우리 서비스의 핵심 가치를 문서화해줘"

1. doc-concretize 실행
   → 개념 분석 → 구조 설계 → 콘텐츠 작성 → 완결성 검증
   → 출력: core-values.md (초안)

2. doc-polish 실행 (선택적)
   → Lint 수정 → LLM 흔적 제거 → 용어 통일 → 품질 리포트
   → 출력: core-values.md (최종본) + 변경 요약
```

### 독립 사용

```
[doc-concretize 단독]
사용자: "이 아이디어를 구체적인 기획서로 만들어줘"
→ 콘텐츠 생성에 집중, 표현 품질은 기본 수준

[doc-polish 단독]
사용자: "이 README.md 품질 검사해줘"
→ 기존 문서 검증/개선, 콘텐츠 변경 없음
```

---

## 구현 우선순위

### Phase 1: doc-polish 신규 구현
1. Layer 1 (Mechanical) - markdownlint 연동
2. Layer 2 (Linguistic) - LLM Trace Detection
3. Layer 3 (Semantic) - Vague Claim Detection

### Phase 2: doc-concretize 리팩토링
1. Phase 4 Polish 제거
2. Phase 1-3 강화 (Concept Analysis, Structure Design)
3. 공유 리소스 분리 (LLM Blacklist → common reference)

### 공유 리소스
- `reference/llm-expression-blacklist.md` - 양쪽에서 참조
- `reference/sentence-guidelines.md` - doc-polish 전용

---

## 레퍼런스

### 웹 자료
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks)
- [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli)
- [claude-code-quality-hook](https://github.com/dhofheinz/claude-code-quality-hook)

### 관련 파일
- `skills/doc-concretize/reference.md` - 현재 Phase 4 Polish 상세
- `skills/doc-concretize/SKILL.md` - 현재 스킬 정의
