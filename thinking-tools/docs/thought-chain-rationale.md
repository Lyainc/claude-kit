# Why `thought-chain` Exists

> Status: Keep (re-evaluate if monthly usage drops below 1 invocation)
> Last review: 2026-04-13

## The question

`thinking-facilitator` already auto-routes requests to the right skill. Why keep a separate `thought-chain` skill that *also* calls multiple skills in sequence?

## The answer: router vs. orchestrator

`thinking-facilitator` and `thought-chain` sit on **different axes**.

| Axis | `thinking-facilitator` (agent) | `thought-chain` (skill) |
|------|-------------------------------|-------------------------|
| Role | **Router** — pick one skill | **Orchestrator** — run four skills in sequence |
| Surface | Every thinking-tools request | Only "comprehensive analysis" requests |
| Output | Delegate + return | Chained report spanning all four stages |
| Unique features | Signal-keyword decision tree | **Checkpoints** between stages, `--skip` / `--start` flags for partial pipelines |

The facilitator's decision tree (`agents/thinking-facilitator.md:48`) itself points at thought-chain:

```
├── Comprehensive analysis needed? ──▶ thought-chain
│   (end-to-end, full pipeline)
```

So the facilitator *is* aware that some requests need a pipeline, and it **delegates that pipeline to `thought-chain`** rather than running one itself. That separation is deliberate:

- Facilitator stays small (pure routing logic, no state across stages).
- Thought-chain owns the sequential contract: discovery → panel → concretize → polish.
- Each stage skill remains independently invocable.

## What `thought-chain` uniquely provides

These features would have to be duplicated inside the facilitator if thought-chain were removed:

1. **Checkpoint UX** — After each stage, ask the user "continue / stop / re-run?" so a 20-minute pipeline doesn't steamroll past a finding the user wants to re-examine.
2. **Partial pipelines** — `--skip discovery` (already have findings from elsewhere), `--start concretize` (already debated, just document). Makes the pipeline resumable across sessions or after manual work.
3. **Inter-stage handoff contract** — Discovery's Critical/Important findings become panel topics; panel consensus becomes concretize input. That data flow is a first-class concern here, not buried in agent branches.

## When it would earn removal

Delete thought-chain when **both** are true:

1. Usage: fewer than ~1 invocation per month for 3 consecutive months.
2. Facilitator's "3+ signals detected" branch never needs the pipeline path (i.e., users always prefer manually stepping through skills).

Until then, the cost of maintaining one small skill file is lower than reimplementing checkpoints + partial pipelines inside the facilitator.

## See also

- `skills/thought-chain/SKILL.md` — pipeline stages, checkpoint format, flag reference
- `agents/thinking-facilitator.md` — routing decision tree and signal-keyword table
