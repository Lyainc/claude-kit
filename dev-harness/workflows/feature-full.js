/**
 * feature-full.js — feature-full route DELEGATE carrier (#201).
 *
 * Structurally enforces CON-3 (no self-approval) by splitting impl and critique
 * into SEPARATE agent() calls. The authoring context cannot approve its own output
 * because each stage is a fresh, isolated subagent context (substrate §4.2 N3).
 *
 * Design constraints (reference only — never redefine here):
 *   - impl agentType: executor  (#133 §1 NATIVE verdict)
 *   - critique agentType by payload (#133 §2):
 *       diff  → code-reviewer (native)
 *       claim → null = default isolated subagent applying adversarial-review methodology
 *               (adversarial-review is a ① leaf SKILL, not an agentType; isolation
 *                comes from the separate agent() call, not the agentType label)
 *   - critique output contract: schema VERDICT_SCHEMA (substrate §4.2 N3 — only the
 *     final message returns; verify via structured output contract, not process surveillance)
 *   - plan is passed VERBATIM to prevent goal-drift (anti-drift anchor)
 *   - spec slice runs in MAIN context first (AskUserQuestion cannot run in a workflow
 *     subagent); its artifact path is passed via args.spec_artifact
 *   - user-confirmed cost gate lives in SKILL.md Phase 4, NOT in this script
 *   - gate-chain §3.2 (gate ② means): INV-4 + Phase 3 ENFORCE already ran before
 *     this script is invoked — the script asserts it was handed a routed plan,
 *     does not re-validate
 *   - CON-1..5 single source: docs/design/claude-kit-boundary.md §5
 *
 * Execution model: Workflow scripts are TOP-LEVEL BODIES, not exported functions —
 * the runtime injects agent()/phase()/log()/args as globals and runs the body in an
 * async context (top-level await/return are the documented convention). A `node
 * --check` as plain ESM therefore rejects the top-level return; the hermetic
 * validity gates are the Python static checks in scripts/test/test-invariant.py.
 *
 * Args contract (passed as Workflow()'s args input — exposed here as the global `args`):
 *   plan              {object}  — verbatim slice_router.py JSON routing plan
 *                                  (work_type === "feature-full", route === "spec→impl→critique")
 *   goal_doc_path     {string}  — path to the goal-doc markdown file
 *   spec_artifact     {string}  — path to the spec artifact produced by the spec slice
 *                                  in MAIN context (spec-first interview output)
 *   critique_payload  {string}  — "diff" (default) | "claim"
 *                                  diff  = code change review (code-reviewer)
 *                                  claim = design/claim review (adversarial-review methodology)
 *   impl_agent_type   {string?} — override for impl agentType (e.g. "oh-my-claudecode:executor")
 *   critique_agent_type {string?} — override for critique agentType (e.g. "oh-my-claudecode:code-reviewer")
 *
 * Returns:
 *   { goal_id, impl_report, verdict }
 *   REJECT handling (fix→re-critique loop) belongs to the outer /goal loop, not this script.
 *
 * NEVER use Date.now() / Math.random() / argless new Date() — breaks resume.
 * meta must be a PURE literal (statically checkable).
 */

// ── Workflow meta (PURE literal — MUST be the first statement: the Workflow
//    runtime rejects scripts where `export const meta` is preceded by any other
//    statement, dogfood-confirmed 2026-06-10) ──────────────────────────────────

export const meta = {
  name: "feature-full",
  description: "feature-full route DELEGATE carrier — impl→critique as separate agent() stages, CON-3 structural",
  phases: [
    {
      title: "Impl",
      detail: "Executor agent implements the goal-doc impl slice and runs verifications",
    },
    {
      title: "Critique",
      detail: "Isolated critique agent reviews impl output; cannot be the same context that authored (CON-3)",
    },
  ],
};

// ── Module constants (statically checkable literals — A4 test parses these) ──

// #133 §1: impl = NATIVE executor agent
const IMPL_AGENT_TYPE = "executor";

// #133 §2: critique agentType by payload type.
// null = default isolated subagent instructed to apply adversarial-review methodology
// (adversarial-review is a ① leaf SKILL, not an agentType; isolation is structural
//  via the separate agent() call — the null value signals "no agentType override needed")
const CRITIQUE_AGENT_TYPE_BY_PAYLOAD = { diff: "code-reviewer", claim: null };

// INV-2/3 output contract (substrate §4.2 N3): critique result verified via schema,
// not process surveillance (process is opaque — only the final message returns).
const VERDICT_SCHEMA = {
  type: "object",
  properties: {
    verdict: {
      type: "string",
      enum: ["APPROVE", "REJECT"],
      description: "APPROVE = impl output meets the goal-doc DoD; REJECT = blocking findings remain",
    },
    findings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          severity: {
            type: "string",
            enum: ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
          },
          file: { type: "string", description: "repo-relative path, omit if not file-specific" },
          title: { type: "string" },
          detail: { type: "string" },
        },
        required: ["severity", "title", "detail"],
      },
    },
    summary: {
      type: "string",
      description: "one-paragraph narrative summary of the critique verdict",
    },
  },
  required: ["verdict", "findings", "summary"],
};

// IMPL_REPORT schema — returned by the impl stage
const IMPL_REPORT_SCHEMA = {
  type: "object",
  properties: {
    files_changed: {
      type: "array",
      items: { type: "string" },
      description: "repo-relative paths of every file created or modified",
    },
    tests: {
      type: "array",
      items: {
        type: "object",
        properties: {
          cmd: { type: "string" },
          pass: { type: "boolean" },
          output_tail: { type: "string" },
        },
        required: ["cmd", "pass"],
      },
    },
    notes: {
      type: "string",
      description: "design decisions, deferred items, anything the critique should know",
    },
  },
  required: ["files_changed", "tests"],
};

// ── Script body (top-level — the Workflow runtime injects agent()/phase()/log()/args) ──

// args may arrive as a JSON-ENCODED STRING depending on the caller surface
// (dogfood-confirmed 2026-06-10: the tool-call layer can deliver the args input
// as one string). Normalize with a parse only — verbatim semantics preserved,
// no reshaping. An unparseable string still fails fast at the contract guard.
let input = args;
if (typeof input === "string") {
  try {
    input = JSON.parse(input);
  } catch (err) {
    throw new Error(
      "feature-full.js: args arrived as a non-JSON string. Pass the args object " +
      "(plan / goal_doc_path / spec_artifact / critique_payload) or its JSON encoding. " +
      `Parse error: ${err.message}`
    );
  }
}

// ── Guard: validate args ──────────────────────────────────────────────────────

if (!input || !input.plan) {
  throw new Error(
    "feature-full.js: args.plan is required. " +
    "This script must be invoked by slice-router Phase 4 DELEGATE after " +
    "INV-4 validation (Phase 1) and ENFORCE (Phase 3) have already passed."
  );
}

const plan = input.plan;

if (plan.work_type !== "feature-full") {
  throw new Error(
    `feature-full.js: args.plan.work_type must be "feature-full", got "${plan.work_type}". ` +
    "The script consumes a routed plan; route the goal-doc through slice_router.py first."
  );
}

if (plan.route !== "spec→impl→critique") {
  throw new Error(
    `feature-full.js: args.plan.route must be "spec→impl→critique", got "${plan.route}". ` +
    "Only the feature-full route is handled by this script."
  );
}

if (!input.spec_artifact) {
  throw new Error(
    "feature-full.js: args.spec_artifact is required. " +
    "Run the spec slice (spec-first interview) in MAIN context first, then pass its artifact path here. " +
    "AskUserQuestion cannot run inside a workflow subagent."
  );
}

// Resolve agentType overrides (registry-qualified names for some environments).
// An empty-string override is normalized to "unset" — "" must read as "use the
// default", never as a silent way to drop the agentType while looking explicit.
const implOverride = input.impl_agent_type || undefined;
const critiqueOverride =
  input.critique_agent_type === undefined || input.critique_agent_type === ""
    ? undefined
    : input.critique_agent_type;

const resolvedImplType = implOverride || IMPL_AGENT_TYPE;
const critiquePayload = input.critique_payload || "diff";

if (!Object.prototype.hasOwnProperty.call(CRITIQUE_AGENT_TYPE_BY_PAYLOAD, critiquePayload)) {
  throw new Error(
    `feature-full.js: args.critique_payload must be "diff" or "claim", got "${critiquePayload}".`
  );
}

const defaultCritiqueType = CRITIQUE_AGENT_TYPE_BY_PAYLOAD[critiquePayload];
const resolvedCritiqueType = critiqueOverride !== undefined
  ? critiqueOverride
  : defaultCritiqueType;

// CON-3 runtime belt: the script's own spawn parameters must be disjoint.
// (INV-4 + check_isolated_critique already ran in Phase 3 ENFORCE before this script
//  is invoked — this assert judges the script's OWN parameter structure, not the plan.)
if (resolvedCritiqueType !== null && resolvedImplType === resolvedCritiqueType) {
  throw new Error(
    `feature-full.js CON-3 violation: impl agentType "${resolvedImplType}" equals ` +
    `critique agentType "${resolvedCritiqueType}". The critique stage must be a DIFFERENT ` +
    "agent context than the impl stage (no self-approval). " +
    "Use a different agentType or leave critique_agent_type unset for the claim payload."
  );
}

// ── Phase 1: Impl ─────────────────────────────────────────────────────────────
// A single executor agent() call. The verbatim plan JSON is embedded as the
// anti-drift anchor so the impl agent cannot reinterpret the routing decision.
// (#133 §1 NATIVE executor, substrate §4.2 N3 isolated context)

phase("Impl");
log(`impl 슬라이스 실행 중 — ${plan.goal_id || "goal"} (agentType: ${resolvedImplType})`);

const implPrompt = [
  "You are the IMPL slice for the feature-full workflow (#201).",
  "",
  "## Anti-drift anchor (verbatim routing plan — do not reinterpret)",
  "```json",
  JSON.stringify(plan, null, 2),
  "```",
  "",
  `## Goal-doc path\n${input.goal_doc_path}`,
  "",
  `## Spec artifact (produced by the spec slice in main context)\n${input.spec_artifact}`,
  "",
  "## Instructions",
  "1. Read the goal-doc at the path above. Implement EXACTLY the impl slice described in",
  "   the 슬라이스 순서 section — nothing more, nothing less.",
  "2. Follow the spec artifact as the implementation contract.",
  "3. Run ALL verifications listed in the goal-doc's E2E 자가검증 section.",
  "4. Return a structured IMPL_REPORT: files_changed (repo-relative paths),",
  "   tests (each with cmd, pass, output_tail), and notes (design decisions,",
  "   deferred items, anything the critique stage should know).",
  "",
  "Do NOT run the spec slice (already done in main context).",
  "Do NOT run the critique slice (a separate isolated agent will do that).",
  "Do NOT commit, push, or create PRs — leave ALL changes in the working tree.",
  "The main context owns git. Committing breaks the isolated-critique premise",
  "(the critique reviews an uncommitted diff), and a push/PR is an unapproved",
  "outward-facing action. (#209: subagent git side-effect contract, rules/RULES.md §1.)",
  "Stay within the impl slice scope defined by the routing plan.",
].join("\n");

const implAgentOptions = { schema: IMPL_REPORT_SCHEMA };
if (resolvedImplType) {
  implAgentOptions.agentType = resolvedImplType;
}

const impl_report = await agent(implPrompt, implAgentOptions);

// agent() returns null on user skip or terminal API error (Workflow tool contract).
// Without this guard the critique prompt would embed the literal string "null" and
// produce a structurally meaningless verdict (PR #205 review P1-2).
if (!impl_report) {
  throw new Error(
    "feature-full.js: impl agent returned null (user abort or terminal API error). " +
    "Aborting — the critique stage requires a valid impl report."
  );
}

// ── Phase 2: Critique ─────────────────────────────────────────────────────────
// A SEPARATE agent() call — different agentType, fresh context.
// This is the structural CON-3 enforcement: the authoring context (Phase 1)
// cannot participate in the approval decision (Phase 2).
//
// For diff payload: code-reviewer native agent reviews the working-tree diff.
// For claim payload: default isolated subagent instructed to apply the
//   adversarial-review methodology (steelman→attack→survival score).
//   adversarial-review is a ① leaf SKILL, not an agentType — its carrier is
//   this isolated agent() call. (gate-chain §3.2, #133 §2)
//
// Output contract: schema VERDICT_SCHEMA enforces APPROVE|REJECT + findings.
// (substrate §4.2 N3: process surveillance impossible — only final message returns;
//  the schema IS the isolation proof for the caller.)

phase("Critique");
log(`격리 critique 실행 중 — payload: ${critiquePayload} (CON-3 별도 컨텍스트)`);

const critiqueMethodology = critiquePayload === "diff"
  ? [
      "Review the working-tree changes (run `git diff HEAD` or inspect modified files).",
      "Assess correctness, completeness against the goal-doc DoD, test coverage, and",
      "absence of regressions. Flag any violation of the constitutional invariants",
      "(CON-1 new-file-only vault writes, CON-3 no self-approval, CON-5 one-way deps).",
    ].join("\n")
  : [
      "Apply the adversarial-review methodology:",
      "  1. Steelman Construction — build the strongest version of the impl's claims.",
      "  2. Attack — challenge each claim across: logical validity, evidence sufficiency,",
      "     hidden assumptions, and goal-doc DoD completeness.",
      "  3. Survival Score — for each claim: survived / collapsed / pending.",
      "Return APPROVE only if all CRITICAL and HIGH findings are resolved.",
      "Return REJECT if any blocking finding remains.",
    ].join("\n");

const critiquePrompt = [
  "You are the isolated CRITIQUE slice for the feature-full workflow (#201, CON-3).",
  "You did NOT author the changes you are reviewing. Your role is adversarial review,",
  "not completion — find real problems, not cosmetic ones.",
  "",
  "## Anti-drift anchor (verbatim routing plan — do not reinterpret)",
  "```json",
  JSON.stringify(plan, null, 2),
  "```",
  "",
  `## Goal-doc path\n${input.goal_doc_path}`,
  "",
  "## Impl report (from the impl stage)",
  "```json",
  JSON.stringify(impl_report, null, 2),
  "```",
  "",
  `## Critique methodology (payload: ${critiquePayload})`,
  critiqueMethodology,
  "",
  "## Output contract",
  "Return a structured verdict: verdict (APPROVE|REJECT), findings (array of",
  "{severity CRITICAL|HIGH|MEDIUM|LOW, file?, title, detail}), summary (narrative).",
  "APPROVE = all DoD items met, no blocking findings.",
  "REJECT  = one or more CRITICAL or HIGH findings remain; the impl slice must fix them.",
].join("\n");

const critiqueAgentOptions = { schema: VERDICT_SCHEMA };
if (resolvedCritiqueType) {
  critiqueAgentOptions.agentType = resolvedCritiqueType;
}
// For claim payload with null agentType: no agentType field set — the Workflow
// runtime uses its default isolated subagent, which is instructed via the prompt
// to apply the adversarial-review methodology above.

const verdict = await agent(critiquePrompt, critiqueAgentOptions);

// Same null contract as the impl stage: a null verdict means the critique never
// happened — failing loudly beats returning { verdict: null } that a caller could
// misread as "no blocking findings" (PR #205 review P1-2 follow-on).
if (!verdict) {
  throw new Error(
    "feature-full.js: critique agent returned null (user abort or terminal API error). " +
    "Aborting — the route is incomplete without a VERDICT (CON-3 output contract)."
  );
}

// ── Return ────────────────────────────────────────────────────────────────────
// The active agent under /goal consumes this result.
// REJECT handling (fix-round → re-critique loop) belongs to the outer /goal loop.

return {
  // goal_id is label-only; a router-produced plan always carries it (INV-4 requires
  // it in frontmatter), but normalize a hand-built plan's absence to an explicit
  // null rather than a silent undefined (#206 N2).
  goal_id: plan.goal_id ?? null,
  impl_report,
  verdict,
};
