# Thinking-Tools — Common Output Schema

All thinking-tools skills that produce structured output files should include this YAML frontmatter block. This enables machine parsing, inter-skill chaining, and vault metadata.

## Schema

```yaml
---
skill: <skill-name>           # e.g., build-spec, unknown-discovery, adversarial-review
schema_version: 1             # bump on breaking changes to this schema
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
| `schema_version` | int | Yes | Common-schema version this output conforms to (current: 1) |
| `version` | string | Yes | Skill version at time of generation |
| `generated` | string | Yes | ISO date string |
| `input.target` | string | Yes | What was analyzed or crystallized |
| `input.options` | array | No | Flags/options used in this run |
| `output.type` | enum | Yes | One of: report, spec, review, plan, document |
| `output.structure` | string | No | Relative path to the template used |

## Per-Skill Extensions

### build-spec

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
angle: <P-id|adhoc>           # Attacker domain angle — a personas.md entry ID
```

### expert-panel

```yaml
topics_discussed: <N>
consensus_reached: <N>
dissenting_views: <N>
```

## Usage

In each skill's output template file, reference this schema with a YAML comment
**inside** the frontmatter block (Markdown frontmatter parsers require `---` on
line 1, so an HTML comment above the block would be ignored):

```yaml
---
# Output conforms to thinking-tools/reference/common-schema.md
skill: <skill-name>
schema_version: 1
...
---
```

Skill-specific frontmatter fields come after the common block, extending it rather than replacing it.

## Versioning

- `schema_version` is required (current: `1`). All output templates MUST emit it.
- Breaking changes (renaming or removing required fields) bump `schema_version`.
- Additive fields (new skill extensions, new optional fields) are non-breaking and do not bump.
