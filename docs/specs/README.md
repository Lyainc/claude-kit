# Specifications and Seeds

Compatibility baseline: **6.0.0** (`v6.0.0`,
`ac95e788018c9e1fc171bc432ac2505e2b41b4d7`). Reconciled against source
`4115e574a998d6f8276f275f8b31b35202ad97f6` (6.0.1), including the later
metadata-first intake and native-question safeguards. This is a source inventory,
not proof of installed plugin contents or live runtime behavior.

`version`, `generated`, and `created` in an existing Seed describe its original
authoring. They are preserved when correcting a contract; they are not rewritten
to the compatibility baseline. Constraint and acceptance IDs are also preserved.

All ten repository Seeds now carry explicit lifecycle decisions following the user's
request to refresh unknown states and fix diagnosed defects: **5 active, 4 paused,
1 closed/discontinued, 0 unknown, 0 completed**. Each Seed records the actual user
instruction, decision reason and selected source/test references. These references
are partial evidence; static contracts and fixtures do not prove live acceptance.
Rule and persona correction evidence pins implementation commit
`d4fe3b7cc463894682a7236be39d5fcdd8833d62`; incomplete or external-owner evidence
keeps `evidence.commit: null`. A pinned commit is not whole-Seed completion proof.
Follow [the lifecycle contract](../../thinking-tools/reference/seed-lifecycle.md)
when applying requirements or resuming paused work.

## Seed inventory

| Seed | Lifecycle | Current owner / remaining evidence |
|---|---|---|
| [build-spec-workflow-integration](build-spec-workflow-integration.yaml) | paused | Main-agent interview and `issue-raise`; acceptance-1–4 still need an approved real issue and authoring-session URL/body/backlog/STATE evidence |
| [claude-kit-work-rules](claude-kit-work-rules.yaml) | active | `rules/RULES.md` and repository guards; reminder correction is committed with regression coverage, full registered suite is unrun, and constraint-8 rule liveness remains partial |
| [expert-panel-delegated-mode](expert-panel-delegated-mode.yaml) | active | `expert-panel` and its worker; acceptance-1–2 need controlled total-cost/quality comparison and actual worker/relay/file traces |
| [obsidian-bases-custom-views](obsidian-bases-custom-views.yaml) | closed/completed | #762; natural-language and explicit filter/sort input, new-file safety and four workload views; verified commit and item evidence are in the Seed |
| [harness-doctor](harness-doctor.yaml) | paused | Optional external local-harness; a refined generation alone does not establish original completion or discontinuation |
| [harness-doctor-v2](harness-doctor-v2.yaml) | paused | External doctor; actual installed SessionStart behavior and full-target latency remain unverified |
| [seed-relations-graph](seed-relations-graph.yaml) | active | `seed-relations.py` and `seed-lifecycle.py`; acceptance-2/7/10 need actual consumer/predecessor/Refine traces beyond deterministic fixtures |
| [thinking-tools-code-reviewer](thinking-tools-code-reviewer.yaml) | closed/discontinued | Retired in #593; methodology moved to `requirement-gap-reviewer` with `seed-diff-grading.md`. This is retirement, not proof that acceptance-3–6 passed |
| [thinking-tools-persona-library](thinking-tools-persona-library.yaml) | active | Shared original-input selection in `reference/personas.md`; acceptance-2/3/5 need actual session STATE/off-pool/consumer comparisons; acceptance-6 documentation is corrected |
| [thinking-tools-ud-bs-boundary](thinking-tools-ud-bs-boundary.yaml) | active | `reference/ud-bs-boundary.md`; acceptance-2–3 need the current cross-session handoff, approval, feedback and skipped STATE traces |
| [vault-discussion-history-wiring](vault-discussion-history-wiring.yaml) | paused | `vault-save` capture and `manifest-recall.md`; external session-close handoff is absent, and actual 18-item migration/fresh-session recall is unverified |

## Diagnosed corrections and verification limits

The Stop reminder now includes Codex marketplace changes. Its five regression cases
exercise real Git status and nonblocking hook JSON, covering both marketplaces,
a governed script, a clean tree and an unrelated change. The test is registered in
[VALIDATION.md](../VALIDATION.md) and CI; coverage is 121/121. This verifies handler
behavior, not personal hook installation or a remote CI run.

The persona improvement matrix now uses the user's original topic input, pool-order
tie breaks and explicit ad-hoc fallback, matching `reference/personas.md`. The work-rule
coverage table now names `feedback-loop/scripts/` and the implemented `rule_fire`
schema/emitter/tally. Rule telemetry remains **partial**: zero-fire rules have no
registry and cannot be interpreted as dead or compliant. No new registry or runtime
engine is implied by this correction.

The expert-panel Seed's two folded scalar-list dependencies were re-encoded as
quoted single-line strings without changing their values, so the lifecycle reader
can validate its existing context. Requirements and item IDs were preserved.

External doctor regression checks recorded 226 passing assertions and one
infrastructure-affected failure: Finder Trash permissions prevented a temporary
payload deletion, so the missing-payload fixture did not form. This is not evidence
of a detector defect. A separate isolated clean fixture returned zero stdout/stderr
bytes, exit 0 and 59.056 ms without a budget skip; it is not full installed-machine
SessionStart latency proof. External source, installed copies and personal settings
were preserved.

No Seed is marked completed. Full registered-suite execution, real issue creation,
actual vault migration, fresh runtime interviews and installed-plugin behavior are
not established by this local diagnosis. Missing recorded `issues.source` fields
remain visible diagnostics; no issue association or approval was invented.

## Related design specifications

| Document | Role |
|---|---|
| [claude-kit-boundary](../design/claude-kit-boundary.md) | Architecture, ownership, dependency direction and constitutional rules |
| [output-adapter-contract](../design/output-adapter-contract.md) | Logical output mapping; retired router is not an implemented shared API |
| [output-layer-structure-adr](../design/output-layer-structure-adr.md) | Accepted distributed ownership decision; original comparison kept historical |
| [4-flow-catalog](../design/4-flow-catalog.md) | Logical user-facing view; external graphify is not bundled |
| [glossary](../design/glossary.md) | Identifier registry, including active and retired audit classifications |
| [vault-second-brain-v4](../design/vault-second-brain-v4.md) | Superseded design; retained conventions only, not a current execution procedure |
| [vault-second-brain-v5](../design/vault-second-brain-v5.md) | Current wiki/reference-store model, capture/compile distinction and deployment ownership |

The [Seed template](../../thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml),
[examples](../../thinking-tools/skills/build-spec/examples.md),
[common schema](../../thinking-tools/reference/common-schema.md),
[identifier convention](../../thinking-tools/reference/identifiers.md), and
[lifecycle contract](../../thinking-tools/reference/seed-lifecycle.md) govern new
authoring. The template is not an actual Seed and is not a lifecycle-check target.
The optional [Seed board](../../thinking-tools/mods/seed-board/README.md) is a
read-only Claude UI; its cache never owns lifecycle or candidate eligibility.

## Validate an amendment

Run metadata before reading the body. A failed lookup holds intake; unknown
lifecycle permits reference inspection, not automatic implementation selection.
Keep the prior file outside the repository for transition validation, then run:

```bash
uv run --no-project thinking-tools/scripts/seed-relations.py metadata docs/specs/<seed>.yaml --json
uv run --no-project thinking-tools/scripts/seed-lifecycle.py check docs/specs/<seed>.yaml --before <prior-file>
uv run --no-project thinking-tools/scripts/seed-relations.py check docs/specs/<seed>.yaml
```

Missing recorded issue references and legacy IDs are diagnostics to preserve and
investigate; do not invent links, rename IDs, migrate relations, or fabricate user
approval to make a report look clean. Use the relevant commands in
[VALIDATION.md](../VALIDATION.md) for behavioral checks. No new dependency, runtime
engine, release bump, or owner-controlled installation is required to amend these
documents.
