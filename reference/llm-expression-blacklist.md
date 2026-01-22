# LLM Expression Blacklist

Shared reference for detecting and replacing typical LLM-generated expressions.

## Table of Contents

- [English Expressions](#english-expressions)
- [Korean Expressions](#korean-expressions)
- [Sentence Length Guidelines](#sentence-length-guidelines)
- [General Rules](#general-rules)

---

## English Expressions

### Mandatory Removal/Revision

| Expression | Alternative | Notes |
|------------|-------------|-------|
| "very important" | "critical" or remove | Vague intensifier |
| "various ways" | Specify methods or remove | Lacks specificity |
| "effectively" | Remove or specify effect | Empty modifier |
| "successfully achieved" | "achieved" | Redundant |
| "in-depth analysis" | "analysis" | Unnecessary modifier |
| "widely utilized" | "used" | Overcomplicated |
| "It is important to..." | Direct statement | Weak opening |
| "In order to..." | "To..." | Verbose |
| "leverage" | "use" | Corporate jargon |
| "utilize" | "use" | Unnecessarily formal |
| "implement" (non-technical) | "do", "make", "create" | Overused |
| "facilitate" | "help", "enable" | Vague |
| "comprehensive" | Specify scope or remove | Overused |
| "robust" | Specify quality or remove | Vague |
| "seamless" | Specify how or remove | Marketing speak |
| "cutting-edge" | Specify innovation or remove | Cliché |
| "state-of-the-art" | Specify what makes it so | Cliché |
| "holistic" | Specify scope | Buzzword |
| "synergy" | Specify collaboration type | Corporate jargon |
| "paradigm shift" | Describe the actual change | Overused |

### Weak Openers to Avoid

| Pattern | Better Alternative |
|---------|-------------------|
| "It should be noted that..." | State directly |
| "It is worth mentioning..." | State directly |
| "It goes without saying..." | Remove entirely |
| "Needless to say..." | Remove entirely |
| "As we all know..." | Remove or cite source |
| "Interestingly enough..." | State the fact |

### Hedging Expressions (Use Sparingly)

| Expression | When Acceptable |
|------------|-----------------|
| "perhaps" | Genuine uncertainty |
| "maybe" | Offering options |
| "somewhat" | Quantified context |
| "relatively" | With comparison |
| "arguably" | Contested claims |

---

## Korean Expressions

### Mandatory Removal/Revision

| Expression | Alternative | Notes |
|------------|-------------|-------|
| "매우 중요한" | "핵심적인" or remove | 모호한 강조 |
| "다양한 방법으로" | 구체적 방법 명시 or remove | 구체성 부족 |
| "효과적으로" | Remove or specify effect | 빈 수식어 |
| "성공적으로 달성" | "달성" | 중복 |
| "심층적으로 분석" | "분석" | 불필요한 수식 |
| "폭넓게 활용" | "활용" | 과장 표현 |
| "~하는 것이 중요합니다" | 직접 서술 | 약한 문장 |
| "~를 통해" (과다 사용) | 구체적 수단 명시 | 남용 주의 |
| "기반으로" (과다 사용) | 구체적 근거 명시 | 남용 주의 |
| "최적화" (비기술적) | 구체적 개선 내용 | 모호 |
| "혁신적인" | 구체적 혁신 내용 | 상투적 |
| "획기적인" | 구체적 변화 명시 | 과장 |
| "원활한" | 구체적 상태 명시 | 모호 |
| "체계적인" | 구체적 방법 명시 | 모호 |
| "종합적인" | 범위 명시 or remove | 남용 |

### Weak Patterns to Avoid

| Pattern | Better Alternative |
|---------|-------------------|
| "~라고 할 수 있습니다" | 직접 서술 |
| "~인 것으로 보입니다" | 직접 서술 or 근거 명시 |
| "~할 필요가 있습니다" | "~해야 합니다" or 직접 지시 |
| "~하는 것이 바람직합니다" | 직접 권고 |
| "일반적으로 말해서" | Remove or cite source |

### Overused Connectors (Vary Usage)

| Connector | Alternatives |
|-----------|-------------|
| "따라서" | "그래서", "이에", "결국" |
| "그러므로" | "때문에", "덕분에" |
| "하지만" | "그러나", "반면", "다만" |
| "또한" | "그리고", "더불어", "아울러" |

---

## Sentence Length Guidelines

### Korean

| Metric | Guideline |
|--------|-----------|
| Recommended length | 15-30 characters |
| Maximum length | 50 characters |
| Action if exceeded | Split into multiple sentences |

**Splitting Strategies**:
- Convert relative clauses to separate sentences
- Break at natural pause points (commas)
- One idea per sentence

### English

| Metric | Guideline |
|--------|-----------|
| Recommended length | 10-25 words |
| Maximum length | 35 words |
| Action if exceeded | Split into multiple sentences |

**Splitting Strategies**:
- Break compound sentences at conjunctions
- Convert participial phrases to main clauses
- One idea per sentence

### Short Sentence Warning

| Language | Threshold | Action |
|----------|-----------|--------|
| Korean | < 10 characters consecutive | Consider combining |
| English | < 5 words consecutive | Consider combining |

---

## General Rules

### All Languages

1. **Remove redundant modifiers**
   - "very unique" → "unique"
   - "completely finished" → "finished"
   - "absolutely essential" → "essential"

2. **One idea per sentence**
   - Split run-on sentences
   - Avoid multiple clauses when possible

3. **Consistent tone throughout**
   - Match formality level
   - Maintain voice (active/passive)

4. **No hedging without purpose**
   - Remove empty qualifiers
   - If uncertain, state why

5. **Concrete over abstract**
   - Specific numbers over "many", "few"
   - Named examples over "various"

### Detection Priority

1. **High** - Expressions that almost always indicate LLM generation
2. **Medium** - Expressions often used by LLMs but acceptable in context
3. **Low** - Style preferences that may vary by document type

---

## Usage

This reference is used by:
- `skills/doc-concretize` - Phase 4 basic quality check
- `skills/doc-polish` - Layer 2 Linguistic analysis

When detecting these expressions, always provide:
1. The problematic expression
2. Location (line number or context)
3. Suggested alternative
4. Severity level (High/Medium/Low)
