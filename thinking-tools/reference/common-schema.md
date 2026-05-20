# Thinking-Tools — Common Output Schema

All thinking-tools skills that produce structured output files should include this YAML frontmatter block. This enables machine parsing, inter-skill chaining, and vault metadata.

## Schema

```yaml
---
skill: <skill-name>           # e.g., spec-first, unknown-discovery, adversarial-review
version: <skill-version>      # from SKILL.md frontmatter
generated: <ISO-date>         # YYYY-MM-DD
input:
  target: <topic or project name>
  options: []                 # CLI flags used, e.g., ["--quick", "--with-repo ."]
output:
  type: <report|spec|review|plan|document>
  structure: <schema-ref>     # path to the output template used
# skill-specific fields below this line
---
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill` | string | Yes | Skill name (kebab-case) |
| `version` | string | Yes | Skill version at time of generation |
| `generated` | string | Yes | ISO date string |
| `input.target` | string | Yes | What was analyzed or crystallized |
| `input.options` | array | No | Flags/options used in this run |
| `output.type` | enum | Yes | One of: report, spec, review, plan, document |
| `output.structure` | string | No | Relative path to the template used |

## Per-Skill Extensions

### spec-first

```yaml
ambiguity:
  overall: <0.0-1.0>
  gate_passed: <true|false>
```

### unknown-discovery

```yaml
depth: <weighted_avg_pct>
findings_count:
  critical: <N>
  important: <N>
  nice_to_have: <N>
```

### adversarial-review

```yaml
claims_tested: <N>
verdicts:
  survived: <N>
  collapsed: <N>
  pending: <N>
```

### expert-panel

```yaml
topics_discussed: <N>
consensus_reached: <N>
dissenting_views: <N>
```

## Usage

In each skill's output template file, reference this schema:

```markdown
<!-- Output conforms to thinking-tools/reference/common-schema.md -->
```

Skill-specific frontmatter fields come after the common block, extending it rather than replacing it.

## Versioning

- Schema version is implicit in this document's git history.
- Breaking changes require a version bump in the `schema_version` sub-field (not yet required at v1).
- Additive fields (new skill extensions) are non-breaking.
