# Expert Panel Discussion - Detailed Reference

Detailed procedures and rules reference document. Referenced from SKILL.md.

## Table of Contents

- [Phase 0: Discussion Preparation (Detailed)](#phase-0-discussion-preparation-detailed)
- [Phase 1: Topic Round Progression (Detailed)](#phase-1-topic-round-progression-detailed)
- [Phase 2: Record Management (Detailed)](#phase-2-record-management-detailed)
- [Phase 3: Moderator Authority (Detailed)](#phase-3-moderator-authority-detailed)
- [Output Structure](#output-structure)
- [Troubleshooting](#troubleshooting)
- [Moderator Checklist](#moderator-checklist)

---

## Phase 0: Discussion Preparation (Detailed)

### 1. Target Analysis

- Comprehend the entire provided document/code/proposal
- Identify key sections and decision points
- Establish discussion priorities

### 2. Participant Composition

- Confirm user-specified expert panel
- Define each expert's perspective and evaluation criteria
- Establish roles for 2 practitioners (pro/con)

**Expert Persona Enhancement Principles**:

Each expert must **think like an actual specialist** in that field, not just represent a "viewpoint":

1. **Core Mechanisms**: Statements based on operating principles and technical constraints of the field
   - Example: LLM expert -> attention mechanism, Security expert -> attack vectors, Legal expert -> statutes

2. **Measurable Metrics**: Quantitative figures, performance benchmarks, risk assessments
   - Example: Performance expert -> O(n) complexity, Security expert -> CVSS score, UX expert -> click count

3. **Precedents/Cases**: Past success/failure cases, industry best practices, case law
   - Example: "2023 X incident", "Y project failure case", "Z legal precedent"

**Driving Rigorous Debate**:
- Demand concrete evidence: "What data supports this claim?", "What cases exist?"
- Present counterexamples: "What about situation X?", "Under condition Y?"
- Make trade-offs explicit: "What do we give up to gain this?"

**Statement Intensity**: Proportional to certainty of evidence (strong opposition = clear precedent, weak agreement = conditional)

### 3. Topic Segmentation

- Divide entire agenda into independent topics
- Identify dependencies between topics
- Determine discussion sequence

**Output**: Discussion agenda (topics, participants, sequence)

---

## Phase 1: Topic Round Progression (Detailed)

### History Reference Rules

- At topic start: Review previous topic conclusions, examine relevance to current topic
- During discussion: Cite relevant conclusions when arguments contradict previous agreements
- When going off-track: Moderator references original document and previous conclusions to return to core issues

### Step 1.1: Practitioner Briefing

**Optimistic Practitioner (Feasibility Advocate)**:
- Explain core content of the topic
- Present expected benefits and advantages
- **Evidence based on implementation experience**: "In the last project, this approach improved X by Y%"
- **Specific figures**: "Implementable within 3 weeks", "Cost reduction of Y amount"
- **Practical feasibility**: "Fully achievable with current team capabilities"

**Critical Practitioner (Risk Identifier)**:
- **Cite past failure cases**: "Project A in 2023 failed using this approach"
- **Specific risk figures**: "N% probability of failure", "M hours increase in technical debt"
- **Potential problem scenarios**: "If user does X, error Y occurs"
- **Alternative approach suggestions**: Not just opposition but "Instead, if we do this..."

**Important**: Practitioners argue with **field experience and data**, not abstract pro/con positions.

### Step 1.2: Expert Q&A

```
[Expert A, B, C, ...]
- Questions from each expert's perspective
- Practitioner responses
- Additional clarification
```

### Step 1.3: Dialectical Discussion

```
Thesis: Optimistic practitioner's position
Antithesis: Critical practitioner + expert rebuttals
Synthesis: Attempt to derive compromise
```

### Step 1.4: Consensus or Deferral

**When consensus is reached**:

- Moderator summarizes agreed content
- Confirm unanimous agreement
- Declare topic closure

**When consensus is not possible**:

- Acknowledge structural limitations -> Record as unresolved issue
- Or request user intervention (fact-check/decision needed)

**Practitioner Compromise**:

- Optimistic practitioner: Propose compromise when opposing arguments prevail
- Critical practitioner: Propose compromise when supporting arguments prevail
- Both sides yield within reason, but end discussion if structural limitations exist

**Discussion Termination Conditions**:

- Consensus reached (1 or fewer dissenting)
- Moderator judges no progress in discussion
- Structural limitations acknowledged -> Transfer to unresolved issues

---

## Phase 2: Record Management (Detailed)

### Storage Rules

**Storage Location**: `docs/discussions/` folder in project root

```
{project-root}/
└── docs/
    └── discussions/
        └── {YYYYMMDD}_{discussion-name}/
            ├── SUMMARY.md              # Final summary
            ├── UNRESOLVED.md           # Unresolved issues
            └── transcripts/
                ├── 01_{topic-name}.md  # Per-topic transcript
                ├── 02_{topic-name}.md
                └── ...
```

**File Naming Rules**:

- Folder name: `{YYYYMMDD}_{discussion-name}` (e.g., `20241224_api-design-review`)
- Transcript: `{number}_{topic-name}.md` (e.g., `01_authentication.md`)
- Numbering starts from 01, assigned in discussion order

### Transcript Format

```markdown
## [Topic Name] Transcript

### Round 1: Briefing

**[Optimistic Practitioner]**: ...
**[Critical Practitioner]**: ...

### Round 2: Q&A

**[Expert A]**: Question...
**[Optimistic Practitioner]**: Response...

### Round 3: Discussion

**[Critical Practitioner]**: Rebuttal...
**[Expert B]**: Additional opinion...

### Conclusion

**[Moderator]**: Agreed content... / Deferral reason...
```

### Summary Format

```markdown
## Discussion Summary

### Agreed Items

| Topic | Conclusion | Rationale |
|-------|------------|-----------|
| ...   | ...        | ...       |

### Unresolved Issues

| Topic | Reason | Required Action |
|-------|--------|-----------------|
| ...   | ...    | ...             |

### Improvement Recommendations

- ...
```

---

## Phase 3: Moderator Authority (Detailed)

### Discussion Suspension Conditions

1. **Fact-check needed**: Cannot proceed without objective fact verification
2. **Opinion deadlock**: Both sides at an impasse, external judgment needed
3. **Scope deviation**: Discussion has strayed from core topic

### Actions Upon Suspension

```
[Moderator]
Temporarily suspending the discussion.

**Suspension Reason**: [Fact-check needed / Decision needed / Scope adjustment needed]
**Required Information**: [Specific request to user]
**Resumption Condition**: [Direction after information is provided]
```

### Unresolved Issue Recording Format

```markdown
## Unresolved Issues Log

### Issue #1: [Title]

- **Topic**: ...
- **Contention**: ...
- **Positions**: ...
- **Deferral Reason**: [Structural limitation / Insufficient information / Opinion conflict]
- **Recommended Action**: ...
```

---

## Output Structure

### Output Format During Discussion

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 TOPIC [N]: [Topic Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎤 [Role]: Statement content...

---
[Next speaker]
---

✅ CONCLUSION: [Agreed content or deferral status]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Discussion stuck in infinite loop on a topic | Moderator judges no progress, force-closes, records as unresolved issue |
| Emotional conflict between practitioners | Moderator reorganizes arguments, reframes based on objective facts |
| Expert opinions too conflicting | Make each position's preconditions explicit, attempt conditional consensus |

---

## Moderator Checklist

Verify before ending discussion:

- [ ] All topics discussed or explicitly deferred
- [ ] Unanimous agreement confirmed on agreed items
- [ ] Unresolved issues list completed
- [ ] No missing transcripts
- [ ] Next-step action items organized
