# Thinking-Tools — Identifier Convention

The one place that defines how thinking-tools names the items it generates and how it shows them
to a person. Skills, templates, scripts and tests follow this file; they do not restate it.

## Why

Short ids like `c1`, `ac1`, `P1` hide both the kind of the item and where it belongs. In a
consuming repository the same `P1` meant a task, a problem, an expert and a priority, and the
same `c1` exists in every Seed. An id has to say what it is; a person-facing reference also has
to say whose it is.

## Local id: `<kind>-<number>`

Inside its own source file an item carries a local id made of a spelled-out kind and a number:
`constraint-1`, `acceptance-2`, `finding-3`. Numbers start at 1 per kind per file and are never
reused: a withdrawn Seed item keeps its id and original content; withdrawal is recorded separately
under [the lifecycle contract](seed-lifecycle.md). A new item takes the next unused number.
Closed historical ids remain as recorded at the provenance commit.

Kinds this plugin generates, and their owners:

| Kind | Meaning | Owner |
|---|---|---|
| `constraint` | Seed `constraints[]` item | `skills/build-spec/templates/SEED_SPEC.yaml` |
| `acceptance` | Seed `success_criteria[]` item | `skills/build-spec/templates/SEED_SPEC.yaml` |
| `finding` | Discovery Report `findings[]` item | `skills/unknown-discovery/templates/DISCOVERY_REPORT.md` |
| `goal-check`, `constraint-check`, `success-check`, `context-check` | build-spec clarity rubric rows | `skills/build-spec/reference.md` §1 |
| `depth-check` | unknown-discovery Depth rubric rows | `skills/unknown-discovery/reference.md` |
| `segment` | doc-concretize final-check segment markers | `skills/doc-concretize/SKILL.md` |

Choose a kind from what the item actually is. Do not add a kind no generator emits, and do not
fold different kinds into one (a constraint is not a `feature`). Things that are better known by
a name than by a number use the name instead: expert personas use their role slug
(`security-expert`, see `reference/personas.md`), and a whole Seed is named by its file slug,
never by an abbreviation.

## Full identifier: `<affiliation>/<local-id> · <description>`

Whenever an item is referred to outside its own file — user-facing output, an issue body,
another document — write the full identifier:

```
dataflow-native-foundation/constraint-1 · DB 스키마 생성
```

- **Affiliation of a Seed item is always the Seed's file slug** without directory, extension
  or `-vN` suffix (`docs/specs/foo-v3.yaml` → `foo`), even when the Seed records
  `issues.source`. Several Seeds can come from one issue, so an issue number would not tell
  them apart; show the issue next to it instead (`… · DB 스키마 생성 (출처 #231)`).
- **Another repository's item** prefixes the coordinate: `owner/repo:foo/constraint-1`.
- An item defined in an issue body belongs to that issue: `issue-231/feature-23 · …`, or
  `owner/repo#231/feature-23` across repositories. Write it only for an issue that exists —
  never invent an issue number, URL or anchor; link the real source.
- Within one document that already names its affiliation, a readable short form is fine:
  `제약조건 1 · DB 스키마 생성`. Prefer the meaningful description over the bare id.

The full identifier is computed at display time. Source files store only the local id — never
the affiliation, never a second alias next to it. A `relations.refines` entry stores the
parent's local id (`refines: [constraint-3]`), because `relations.parent` already names the
affiliation. `scripts/seed-relations.py` `qualified_id()` is the code form of this rule.

## Legacy ids and migration

Seeds written before this convention use `c<N>` (constraints) and `ac<N>` (success criteria).
Readers keep accepting them — ids are compared as plain strings, so an unmigrated Seed still
walks and checks, and renders as a pick only when current lifecycle/eligibility permits it —
but compatibility reading is not migration:

- `seed-relations.py check` prints a `LEGACY` line for a Seed that still carries `c<N>`/`ac<N>`
  ids (informational, exit code unchanged), and a `refines` entry that does not resolve stays a
  `MISMATCH` with a migration hint.
- `scripts/seed-id-migrate.py` is the only rename path. It maps `c<N>` → `constraint-<N>` and
  `ac<N>` → `acceptance-<N>` (number kept, so no mapping table is needed), rewrites the named
  Seed and the `refines` of its local children together, verifies that every item's content and
  every relation survives, and is safe to re-run after a partial failure. Dry-run by default.
  Check the script's supported fields before using it on lifecycle/relations-v2 data; never
  rename frozen historical ids or rewrite pinned provenance as an incidental migration.
- The Seed edit guard (`hooks/seed-append-guard.sh`) still denies an id vanishing in an ordinary
  edit, including a hand-made rename, and points to the migration script instead.
- New Seeds use only the new form. Mixing `c1` and `constraint-1` for the same number in one
  Seed is a reused number and is refused.
