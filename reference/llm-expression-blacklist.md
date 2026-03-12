# AI Writing Tropes Reference

Shared reference for detecting AI-generated writing patterns.
Formerly "LLM Expression Blacklist" — expanded to cover structural, tonal, and compositional tropes.

## Table of Contents

- [Clustering Principle](#clustering-principle)
- [Category A: Word Choice](#category-a-word-choice)
- [Category B: Sentence Structure](#category-b-sentence-structure)
- [Category C: Paragraph Structure](#category-c-paragraph-structure)
- [Category D: Tone Markers](#category-d-tone-markers)
- [Category E: Formatting Signals](#category-e-formatting-signals)
- [Category F: Composition Tics](#category-f-composition-tics)
- [Sentence Length Guidelines](#sentence-length-guidelines)
- [General Rules](#general-rules)

---

## Clustering Principle

A single trope is acceptable — most also appear in human writing.
The AI signal emerges from **clustering**:

| Threshold | Signal Level |
|-----------|-------------|
| 1 trope per 1000 words | Normal |
| 3+ tropes per 1000 words | Suspicious |
| 5+ tropes per 1000 words | Strong AI signal |
| 3+ tropes within 10 lines | Hotspot (strong AI signal) |

Severity weighting for density calculation:

- **High**: weight 3 — strong AI signal even in isolation
- **Medium**: weight 2 — AI signal when clustered
- **Low**: weight 1 — AI signal only at high frequency

---

## Category A: Word Choice

### A1. Magic Adverbs (High)

Adverbs that add false depth without real meaning.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "quietly" | Remove or specify how | `/\bquietly\b/i` |
| "deeply" | Remove or specify depth | `/\bdeeply\b/i` |
| "fundamentally" | Remove or specify what changed | `/\bfundamentally\b/i` |
| "remarkably" | Remove or show evidence | `/\bremarkably\b/i` |
| "arguably" | Remove or cite the argument | `/\barguably\b/i` |
| "effectively" | Remove or specify effect | `/\beffectively\b/i` |
| "successfully" | Remove (redundant with result) | `/\bsuccessfully\b/i` |

Why AI signal: LLMs use these to simulate nuance without committing to specifics.

### A2. Delve and Friends (High)

Corporate/formal verbs that LLMs overuse.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "delve" | "explore", "examine", "look at" | `/\bdelve\b/i` |
| "utilize" | "use" | `/\butilize\b/i` |
| "leverage" | "use" | `/\bleverage\b/i` |
| "robust" | Specify quality or remove | `/\brobust\b/i` |
| "streamline" | "simplify", "speed up" | `/\bstreamline\b/i` |
| "harness" | "use", "apply" | `/\bharness\b/i` |
| "facilitate" | "help", "enable" | `/\bfacilitate\b/i` |
| "comprehensive" | Specify scope or remove | `/\bcomprehensive\b/i` |
| "seamless" | Specify how or remove | `/\bseamless\b/i` |
| "holistic" | Specify scope | `/\bholistic\b/i` |
| "cutting-edge" | Specify innovation or remove | `/\bcutting-edge\b/i` |
| "state-of-the-art" | Specify what makes it so | `/\bstate-of-the-art\b/i` |

Why AI signal: Humans rarely reach for these words; LLMs treat them as "smart-sounding" defaults.

### A3. Grandiose Nouns (Medium)

Abstract nouns that inflate importance without adding information.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "tapestry" | Describe the actual structure | `/\btapestry\b/i` |
| "landscape" (non-literal) | "field", "area", "space" | Context check |
| "paradigm" | Describe the actual model | `/\bparadigm\b/i` |
| "synergy" | Specify the collaboration | `/\bsynergy\b/i` |
| "ecosystem" (non-literal) | "system", "community" | Context check |
| "framework" (non-technical) | "approach", "structure" | Context check |
| "paradigm shift" | Describe the actual change | `/\bparadigm shift\b/i` |

Why AI signal: LLMs use grand nouns to make mundane descriptions sound profound.

### A4. Serves-As Dodge (Medium)

Using indirect verbs to avoid direct statements.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "serves as" | "is" | `/\bserves as\b/i` |
| "stands as" | "is" | `/\bstands as\b/i` |
| "marks" (a milestone/shift) | "is" | Context check |
| "represents" (abstract) | "is" | Context check |

Why AI signal: LLMs dodge direct "is/are" statements to sound more sophisticated.

**Examples**:

- "This serves as a reminder" → "This is a reminder"
- "The release stands as a milestone" → "The release is a milestone"

### A5. Korean Expressions (High/Medium)

Korean LLM expressions to detect and replace.

#### Mandatory Removal/Revision

| Expression | Alternative | Severity |
|------------|-------------|----------|
| "매우 중요한" | "핵심적인" or remove | High |
| "다양한 방법으로" | 구체적 방법 명시 or remove | High |
| "효과적으로" | Remove or specify effect | High |
| "성공적으로 달성" | "달성" | High |
| "심층적으로 분석" | "분석" | Medium |
| "폭넓게 활용" | "활용" | Medium |
| "~하는 것이 중요합니다" | 직접 서술 | High |
| "~를 통해" (과다 사용) | 구체적 수단 명시 | Medium |
| "기반으로" (과다 사용) | 구체적 근거 명시 | Medium |
| "최적화" (비기술적) | 구체적 개선 내용 | Medium |
| "혁신적인" | 구체적 혁신 내용 | High |
| "획기적인" | 구체적 변화 명시 | High |
| "원활한" | 구체적 상태 명시 | Medium |
| "체계적인" | 구체적 방법 명시 | Medium |
| "종합적인" | 범위 명시 or remove | Medium |

#### Weak Patterns

| Pattern | Alternative | Severity |
|---------|-------------|----------|
| "~라고 할 수 있습니다" | 직접 서술 | Medium |
| "~인 것으로 보입니다" | 직접 서술 or 근거 명시 | Medium |
| "~할 필요가 있습니다" | "~해야 합니다" or 직접 지시 | Medium |
| "~하는 것이 바람직합니다" | 직접 권고 | Medium |
| "일반적으로 말해서" | Remove or cite source | Low |

#### Overused Connectors (Vary Usage)

| Connector | Alternatives |
|-----------|-------------|
| "따라서" | "그래서", "이에", "결국" |
| "그러므로" | "때문에", "덕분에" |
| "하지만" | "그러나", "반면", "다만" |
| "또한" | "그리고", "더불어", "아울러" |

### A6. English Expressions (High/Medium)

English LLM expressions beyond A1-A4 categories.

#### Mandatory Removal/Revision

| Expression | Alternative | Severity |
|------------|-------------|----------|
| "very important" | "critical" or remove | High |
| "various ways" | Specify methods or remove | High |
| "in-depth analysis" | "analysis" | Medium |
| "widely utilized" | "used" | Medium |
| "It is important to..." | Direct statement | High |
| "In order to..." | "To..." | Medium |
| "implement" (non-technical) | "do", "make", "create" | Medium |

#### Weak Openers

| Pattern | Alternative | Severity |
|---------|-------------|----------|
| "It should be noted that..." | State directly | High |
| "It is worth mentioning..." | State directly | High |
| "It goes without saying..." | Remove entirely | High |
| "Needless to say..." | Remove entirely | Medium |
| "As we all know..." | Remove or cite source | Medium |
| "Interestingly enough..." | State the fact | Medium |

#### Hedging Expressions (Use Sparingly)

| Expression | When Acceptable | Severity |
|------------|-----------------|----------|
| "perhaps" | Genuine uncertainty | Low |
| "maybe" | Offering options | Low |
| "somewhat" | Quantified context | Low |
| "relatively" | With comparison | Low |

---

## Category B: Sentence Structure

### B1. Negative Parallelism (High)

"It's not X — it's Y" pattern. Creates false drama through negation-contrast.

| Pattern | Detection |
|---------|-----------|
| "It's not X — it's Y" | `/it'?s not .{3,30}—.{3,30}/i` |
| "This isn't about X. It's about Y." | `/isn'?t about .+\. It'?s about/i` |
| "Not X. But Y." | `/^Not .+\. But /m` |

**Examples**:

- "It's not just a tool — it's a platform" → "It is a platform"
- "It's not bold. It's backwards." → "It is backwards."

Why AI signal: LLMs overuse this for rhetorical emphasis. Humans occasionally use it; LLMs make it a default.

### B2. Dramatic Countdown (High)

"Not X. Not Y. Just Z." pattern. Builds artificial suspense.

| Pattern | Detection |
|---------|-----------|
| "Not X. Not Y. Just Z." | `/^Not .+\.\s*Not .+\.\s*(Just\|Only)/m` |
| "No X. No Y. Just Z." | `/^No .+\.\s*No .+\.\s*(Just\|Only)/m` |

**Examples**:

- "Not faster. Not cheaper. Just better." → "It is better."
- "No hype. No gimmicks. Just results." → "It delivers results."

### B3. Rhetorical Q&A (High)

Self-answering question pattern: "The X? A Y."

| Pattern | Detection |
|---------|-----------|
| "The X? A Y." | `/\?\s*\n?\s*[A-Z].{2,20}\./` |
| "What does this mean? It means..." | `/What does .+\?\s*(It means\|This means)/i` |

**Examples**:

- "The result? Unprecedented growth." → "This led to unprecedented growth."
- "The takeaway? Start now." → Rewrite as direct statement.

### B4. Anaphora Abuse (Medium)

3+ consecutive sentences starting with the same word.

| Pattern | Detection |
|---------|-----------|
| Same word starts 3+ lines | Check first token of 3+ consecutive sentences |

**Examples**:

- "We built... We tested... We shipped... We learned..." → Vary sentence openers.

### B5. Tricolon Abuse (Medium)

Mechanical rule-of-three: three parallel items that create artificial rhythm.

| Pattern | Detection |
|---------|-----------|
| Three parallel phrases | Semicolon or comma-separated triples with similar structure |

**Examples**:

- "Fast, reliable, and scalable." → Specific and relevant descriptors only.
- "Plan. Build. Deploy." → Use only when structure genuinely fits.

### B6. Worth Noting (Medium)

Meta-commentary that adds no information.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "It's worth noting" | State the fact directly | `/it'?s worth noting/i` |
| "Importantly" | Remove | `/^Importantly,/m` |
| "Interestingly" | Remove | `/^Interestingly,/m` |
| "Notably" | Remove | `/^Notably,/m` |
| "Significantly" | Remove | `/^Significantly,/m` |

### B7. Superficial Analyses (Low)

"-ing" constructions used to fake analytical depth.

| Pattern | Detection |
|---------|-----------|
| "highlighting..." | `/,?\s*highlighting\b/i` |
| "reflecting..." | `/,?\s*reflecting\b/i` |
| "contributing to..." | `/,?\s*contributing to\b/i` |
| "underscoring..." | `/,?\s*underscoring\b/i` |
| "demonstrating..." | `/,?\s*demonstrating\b/i` |

Why AI signal: LLMs append these to make statements sound analytical without adding substance.

### B8. False Ranges (Low)

"From X to Y" without actual spectrum data.

| Pattern | Detection |
|---------|-----------|
| "from X to Y" (vague) | `/from .{3,30} to .{3,30}/i` — flag if no data follows |

**Examples**:

- "From healthcare to finance" → List specific examples if relevant.

### B9. Gerund Fragment Litany (Medium)

Verb-less gerund sentences in sequence.

| Pattern | Detection |
|---------|-----------|
| 3+ consecutive gerund phrases | `/^[A-Z]\w+ing .+\.$/m` — check for 3+ in sequence |

**Examples**:

- "Building trust. Fostering innovation. Driving change." → Convert to complete sentences.

---

## Category C: Paragraph Structure

### C1. Short Punchy Fragments (High)

3+ consecutive paragraphs of <10 words each. Creates artificial dramatic pacing.

| Pattern | Detection |
|---------|-----------|
| 3+ consecutive short paragraphs | Count words per paragraph; flag 3+ consecutive <10-word paragraphs |

**Examples**:

- "This changes everything.\n\nAnd it starts now.\n\nNo turning back." → Combine into one substantive paragraph.

### C2. Listicle in Trench Coat (Medium)

Prose disguised as a list using "The first/second/third" structure.

| Pattern | Detection |
|---------|-----------|
| "The first..." → "The second..." → "The third..." | `/The (first\|second\|third\|fourth)\b/i` in consecutive paragraphs |

**Examples**:

- "The first challenge is... The second challenge is... The third challenge is..." → Use an actual numbered list, or restructure.

---

## Category D: Tone Markers

### D1. False Suspense (High)

Phrases that manufacture drama or intrigue.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "Here's the kicker" | State the point directly | `/here'?s the kicker/i` |
| "Here's the thing" | Remove | `/here'?s the thing/i` |
| "Here's where it gets interesting" | Remove | `/here'?s where it gets/i` |
| "But here's the catch" | State the caveat directly | `/but here'?s the catch/i` |
| "And that's where things get tricky" | Remove | `/that'?s where .+ get/i` |

### D2. Patronizing Analogies (Medium)

Unnecessary simplification through analogy.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "Think of it as..." | Explain directly | `/think of it as/i` |
| "It's like..." (forced analogy) | Explain directly | Context check |
| "Imagine you're..." | Explain directly | `/imagine you'?re/i` |

### D3. Imagine a World (Medium)

Utopian future framing to inflate stakes.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "Imagine a world where..." | State the benefit directly | `/imagine a world/i` |
| "Picture this:" | Remove framing | `/picture this:/i` |
| "What if we could..." | Describe actual capabilities | `/what if we could/i` |

### D4. False Vulnerability (Low)

Manufactured authenticity through confessional tone.

| Pattern | Detection |
|---------|-----------|
| "I'll be honest..." | `/I'?ll be honest/i` |
| "Can I be real for a moment?" | `/can I be real/i` |
| "Here's what I actually think" | `/what I actually think/i` |

Why AI signal: LLMs simulate vulnerability to appear more human. Low severity — humans do this too.

### D5. Truth is Simple (Medium)

Claiming clarity without providing evidence.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "The reality is simpler" | Prove it with evidence | `/the reality is (simpler\|clear\|straightforward)/i` |
| "History is clear" | Cite the history | `/history is clear/i` |
| "The truth is" | Remove | `/the truth is/i` |
| "The answer is simple" | Show why it's simple | `/the answer is simple/i` |

### D6. Stakes Inflation (High)

Exaggerated importance claims without evidence.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "fundamentally reshape" | Describe specific change | `/fundamentally reshape/i` |
| "define the next era" | Describe specific impact | `/define the next era/i` |
| "game-changer" | Describe specific advantage | `/game-?changer/i` |
| "revolutionary" | Describe specific innovation | `/\brevolutionary\b/i` |
| "unprecedented" | Provide comparison | `/\bunprecedented\b/i` |
| "transformative" | Describe specific transformation | `/\btransformative\b/i` |

### D7. Let's Break Down (Medium)

Meta-commentary about explaining, instead of just explaining.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "Let's break this down" | Just explain | `/let'?s break .+ down/i` |
| "Let's unpack" | Just explain | `/let'?s unpack/i` |
| "Let's explore" | Just explain | `/let'?s explore/i` |
| "Let's dive in" | Just start | `/let'?s dive in/i` |

### D8. Vague Attributions (Medium)

Citations without sources.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "Experts argue" | Name the experts or cite | `/experts (argue\|say\|suggest\|believe)/i` |
| "Studies show" | Cite the studies | `/studies (show\|suggest\|indicate)/i` |
| "Industry reports suggest" | Cite the reports | `/industry reports/i` |
| "Research indicates" | Cite the research | `/research (indicates\|suggests\|shows)/i` |

### D9. Invented Concept Labels (Low)

Made-up terms that sound academic.

| Pattern | Detection |
|---------|-----------|
| "the X paradox" (novel term) | `/the \w+ paradox/i` — verify if established |
| "the X trap" (novel term) | `/the \w+ trap/i` — verify if established |
| "the X effect" (novel term) | `/the \w+ effect/i` — verify if established |

Why AI signal: LLMs coin terms to simulate original thought. Low severity — verify whether the term is established before flagging.

---

## Category E: Formatting Signals

### E1. Em-Dash Addiction (High)

Excessive em-dash usage. Humans typically use 2-3 per document; LLMs use 20+.

| Metric | Threshold | Detection |
|--------|-----------|-----------|
| Em-dashes per document | >10 in <2000 words | Count `—` and `--` occurrences |
| Em-dashes per paragraph | >2 per paragraph | Flag paragraphs with 3+ |

### E2. Bold-First Bullets (High)

Every list item starts with a bold keyword followed by explanation.

| Pattern | Detection |
|---------|-----------|
| `- **Keyword**: explanation` for all items | Check if >80% of list items start with `**...**` |

**Examples**:

- "- **Speed**: Fast processing\n- **Scale**: Large capacity\n- **Cost**: Affordable pricing" → Use bold selectively, not on every item.

### E3. Unicode Decoration (Medium)

Non-standard keyboard characters used for visual flair.

| Character | Alternative | Detection |
|-----------|-------------|-----------|
| → (arrow) | "->" or rewrite | `/→/` |
| Smart quotes "" '' | Standard quotes | `/[\u201C\u201D\u2018\u2019]/` |
| • (bullet) | Standard `-` or `*` | `/•/` |

Why AI signal: LLMs insert unicode characters that humans rarely type from keyboard.

---

## Category F: Composition Tics

### F1. Fractal Summaries (High)

Summary → body → summary pattern repeated at every level (document, section, subsection).

| Pattern | Detection |
|---------|-----------|
| Intro restates conclusion | Compare first and last paragraphs of each section for similarity |
| Section summary + subsection summaries | Check if each heading is followed by a summary paragraph |

### F2. Dead Metaphor (Medium)

A single metaphor repeated 5+ times throughout the document.

| Pattern | Detection |
|---------|-----------|
| Same metaphor word 5+ times | Track metaphor keywords; flag if same one appears 5+ times |

**Examples**:

- "building blocks" used 8 times → Use once, then refer directly.

### F3. Historical Analogy Stacking (Medium)

Multiple company/historical examples listed to prove a point.

| Pattern | Detection |
|---------|-----------|
| 3+ company names in sequence | Check for Apple, Google, Uber, Airbnb, Netflix, Spotify etc. in consecutive sentences |

**Examples**:

- "Like Uber disrupted taxis, Airbnb disrupted hotels, and Netflix disrupted TV..." → One example is enough.

### F4. One-Point Dilution (High)

A single argument restated in 5+ different ways without adding new information.

| Pattern | Detection |
|---------|-----------|
| High semantic similarity across paragraphs | Compare paragraph embeddings; flag if 3+ paragraphs say the same thing |

### F5. Content Duplication (High)

Near-identical paragraphs or sections appearing multiple times.

| Pattern | Detection |
|---------|-----------|
| Repeated sentences/paragraphs | Check for sentences appearing 2+ times (excluding headings, code blocks) |

### F6. Signposted Conclusion (Medium)

Explicit conclusion markers that are unnecessary.

| Expression | Alternative | Detection |
|------------|-------------|-----------|
| "In conclusion" | Remove or just conclude | `/in conclusion/i` |
| "To sum up" | Remove | `/to sum up/i` |
| "In summary" | Remove | `/in summary/i` |
| "To summarize" | Remove | `/to summarize/i` |
| "All in all" | Remove | `/all in all/i` |

### F7. Despite Its Challenges (Medium)

Acknowledging a problem then immediately pivoting to optimism without resolution.

| Pattern | Detection |
|---------|-----------|
| "Despite X, Y remains promising" | `/despite .+, .+ (remains\|continues\|is still)/i` |
| "While X is challenging, Y" | `/while .+ (challenging\|difficult), .+ (promising\|exciting)/i` |
| "Challenges exist, but" | `/challenges exist.+but/i` |

Why AI signal: LLMs default to optimistic conclusions even when the analysis doesn't support them.

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

1. **High** — Strong AI signal even in isolation (negative parallelism, em-dash addiction, stakes inflation)
2. **Medium** — AI signal when clustered (tricolon, patronizing analogies, dead metaphor)
3. **Low** — AI signal only at high frequency (superficial analyses, unicode decoration, false ranges)

---

## Usage

This reference is used by:

- `skills/doc-concretize` - Phase 5 basic quality check
- `skills/doc-polish` - Layer 2 Linguistic analysis (6-category trope detection + density scoring)

When detecting these patterns, always provide:

1. The trope name and category (e.g., "B1. Negative Parallelism")
2. Location (line number or context)
3. Suggested alternative
4. Severity level (High/Medium/Low)
