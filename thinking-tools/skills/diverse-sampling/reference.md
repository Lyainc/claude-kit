# Diverse Sampling - Reference

Detailed procedures and guidelines for Verbalized Sampling implementation.

## Table of Contents

- [VS Prompt Templates](#vs-prompt-templates)
- [Language Detection](#language-detection)
- [XML Parsing Logic](#xml-parsing-logic)
- [Selection Strategies](#selection-strategies)
- [Fallback Procedure](#fallback-procedure)
- [Internal Parameters](#internal-parameters)

---

## VS Prompt Templates

### English Template

```
Generate 5 responses to the following query, each within a separate <response> tag.

Each <response> must include:
- <text>: The actual response content
- <probability>: A numeric probability value between 0.0 and 1.0

IMPORTANT: Sample from the tails of the distribution, such that each probability is less than 0.10.
This ensures diverse, non-typical responses rather than the most common answers.

Query: {USER_QUERY}

Format your output exactly as:
<response>
<text>Your response here</text>
<probability>0.08</probability>
</response>
<response>
<text>Another response</text>
<probability>0.07</probability>
</response>
... (5 total responses)
```

### Korean Template

```
다음 질문에 대해 5개의 응답을 생성하세요. 각 응답은 별도의 <response> 태그 안에 작성합니다.

각 <response>는 다음을 포함해야 합니다:
- <text>: 실제 응답 내용
- <probability>: 0.0에서 1.0 사이의 확률값

중요: 분포의 꼬리에서 샘플링하여, 각 확률이 0.10 미만이 되도록 하세요.
이는 가장 흔한 답변이 아닌 다양하고 비전형적인 응답을 보장합니다.

질문: {USER_QUERY}

정확히 다음 형식으로 출력하세요:
<response>
<text>응답 내용</text>
<probability>0.08</probability>
</response>
<response>
<text>다른 응답</text>
<probability>0.07</probability>
</response>
... (총 5개 응답)
```

---

## Language Detection

### Detection Logic

```
1. Count Korean characters (가-힣, ㄱ-ㅎ, ㅏ-ㅣ)
2. Count English characters (a-z, A-Z)
3. Calculate ratio

IF korean_count > english_count:
    language = "ko"
ELSE:
    language = "en"
```

### Mixed Language Handling

| Scenario | Detection | Template |
|----------|-----------|----------|
| Pure Korean | "커피숍 이름 추천해줘" | Korean |
| Pure English | "Give me startup name ideas" | English |
| Mixed (Korean dominant) | "마케팅 copy 아이디어" | Korean |
| Mixed (English dominant) | "브랜딩 strategy ideas" | English |

---

## XML Parsing Logic

### Expected Structure

```xml
<response>
<text>Response content here</text>
<probability>0.08</probability>
</response>
```

### Parsing Algorithm

```
1. Find all <response>...</response> blocks using regex
2. For each block:
   a. Extract <text>...</text> content
   b. Extract <probability>...</probability> value
   c. Parse probability as float
   d. Validate: 0.0 <= probability <= 1.0
3. Collect valid responses into list
4. If valid_count < 5: trigger fallback
```

### Regex Patterns

```regex
Response block: <response>(.*?)</response>
Text content:   <text>(.*?)</text>
Probability:    <probability>([0-9.]+)</probability>
```

### Parse Error Handling

| Error Type | Action |
|------------|--------|
| No `<response>` tags found | Trigger fallback |
| Missing `<text>` in response | Skip that response |
| Invalid probability format | Skip that response |
| Fewer than 5 valid responses | Trigger fallback |

---

## Selection Strategies

*This section describes internal logic. Users see simplified output format only.*

### Weighted Random Sampling (Default)

```
Algorithm:
1. Extract probabilities: [p1, p2, p3, p4, p5]
2. Normalize: total = sum(probabilities)
   normalized = [p/total for p in probabilities]
3. Build cumulative distribution:
   cumulative = [0.0]
   for p in normalized:
       cumulative.append(cumulative[-1] + p)
4. Generate random r in [0, 1)
5. Find index where cumulative[i] <= r < cumulative[i+1]
6. Return response at that index

Example:
- Probabilities: [0.08, 0.07, 0.06, 0.05, 0.04]
- Normalized: [0.267, 0.233, 0.200, 0.167, 0.133]
- Cumulative: [0.0, 0.267, 0.500, 0.700, 0.867, 1.0]
- Random r = 0.45 → falls in [0.267, 0.500) → index 1 → response 2
```

### Show All (`--all`)

```
Display all responses in table format:
- Sort by probability (descending)
- Show index, probability, and text
- No selection performed
```

### Highest Probability (`--best`)

```
Algorithm:
1. Find max(probabilities)
2. Return corresponding response
3. Note: This reduces diversity benefit
```

---

## Fallback Procedure

### Trigger Conditions

1. **Parse Failure**: No valid `<response>` blocks found
2. **Insufficient Responses**: Fewer than 5 valid responses parsed
3. **Invalid Probabilities**: All probability values unparseable

### Fallback Steps

```
1. Log warning message to user:
   "⚠️ VS 형식 파싱 실패, 일반 응답으로 전환합니다"

2. Generate standard response:
   - Use original user query
   - No VS template applied
   - Standard model response

3. Append fallback note:
   "(Fallback: VS parsing failed)"

4. Return response to user
```

### Fallback Output Format

```
[Standard response to user query]

───
*일반 응답으로 대체되었습니다.*
```

---

## Internal Parameters

### Fixed Values (Not User-Exposed)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `k` | 5 | Number of responses to generate |
| `tau` | 0.10 | Maximum probability threshold for tail sampling |

### Rationale

- **k=5**: Balances diversity vs. token cost. Validated in research.
- **tau=0.10**: Ensures responses from distribution tail, avoiding mode collapse.

### Why Not Exposed

1. **Simplicity**: Users don't need to understand VS internals
2. **Consistency**: Fixed values ensure reproducible behavior
3. **Validation**: These values are research-validated defaults

---

## Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Generated text content itself
- Results that users will directly use
- Examples: brand names, document body, discussion conclusions

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

---

## Output Terminology

### User-Friendly Conversion Table

| Internal Term | Korean Output | English Output |
|---------------|---------------|----------------|
| Verbalized Sampling | 다양성 기법 | diversity technique |
| weighted random | 다양성 기반 선택 | diversity-based selection |
| highest probability | 가장 선호되는 | most preferred |
| show all | 전체 보기 | show all |
| Candidates: 5 | 5개 대안 중 | from 5 alternatives |

### Percentage Display

Convert probability to percentage using normalization:

| Probability | Display |
|-------------|---------|
| Highest (max) | 100% |
| ~70% of max | 70% |
| ~55% of max | 55% |
| ~35% of max | 35% |
| ~20% of max | 20% |

**Normalization Logic**:
1. Find max probability among 5 responses
2. Scale max to 100%
3. Scale others proportionally: `(prob / max_prob) × 100%`
4. Round to nearest integer

**Edge Cases**:
- If max_prob = 0: fallback to equal distribution (20% each)
- If all probabilities equal: all show 100%
- If negative probability detected: trigger fallback

**Example Calculation**:
- Probabilities: [0.35, 0.25, 0.20, 0.12, 0.08]
- Max: 0.35
- Scaled: [100%, 71%, 57%, 34%, 23%]

### Rank Display

| Rank | Display |
|------|---------|
| 1st | 1 |
| 2nd | 2 |
| 3rd | 3 |
| 4th | 4 |
| 5th | 5 |

*Note: Use simple numbers for professional appearance. Percentage provides clear quantitative distinction.*

### Fallback Messages

When parsing fails or structured output unavailable:
- Korean: `일반 응답으로 대체되었습니다.`
- English: `Falling back to standard response.`

---

## Research Background

### Mode Collapse Problem

Post-training alignment (RLHF) causes LLMs to favor typical, familiar responses.
This "typicality bias" reduces output diversity.

### Verbalized Sampling Solution

By asking the model to verbalize a probability distribution, VS prompts the model
to access its pre-training diversity rather than collapsing to typical responses.

### Performance Metrics (from paper)

| Metric | Improvement |
|--------|-------------|
| Diversity | 1.6-2.1× increase |
| Base model diversity recovery | 66.8% |
| Factual accuracy | No loss |
| Safety | No degradation |

### Citation

```
Zhang, J., Yu, S., Chong, D., Sicilia, A., Tomz, M.R., Manning, C.D., & Shi, W. (2025).
Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity.
arXiv:2510.01171
```
