# Unresolved Issues — claude-kit Audit Critique

**Date**: 2026-05-10
**Source**: Expert panel discussion on `plan-2026-05-10-plugin-architecture-audit.md`

The following items could not be resolved during the panel and require additional data collection or stakeholder input before action.

---

## U1 — Token Compression Denominator

**Status**: Resolved (2026-05-10, retrospective in `session-2026-05-10-audit-p0-execution.md`)

**Resolution**: Denominator clarified as **(a) description-layer subset** (vault-searcher.md frontmatter + 3 plugin.json description + thinking-tools 7 SKILL frontmatter ≈ 4~5KB). Against the full system prompt, real impact is <5% — motivation reframed from "token savings" to "routing-signal clarity + readability".

**Verified by P0 #1 measurement**:
- vault-searcher description: 1432 → 635 chars (-56% on the description-layer subset)
- critique's 1247-char estimate was 185 chars under actual

**Original issue**: The audit's "30~40% token compression" claim did not specify the denominator. Two plausible interpretations:
- (a) Description-layer subset (vault-searcher.md + plugin.json + thinking-tools SKILL frontmatters ≈ 4~5KB) → 30~40% plausible
- (b) Full system prompt → likely <5%

**Owner**: audit author (resolved by retrospective)

---

## U2 — thinking-tools Trigger Statistics

**Status**: No data

**Issue**: Audit P0 #2 proposes capping trigger phrases at "KR 4 + EN 3" without empirical basis for those numbers. Korean verb-ending diversity may require >4 patterns to maintain routing accuracy.

**Required data**:
- Per-skill trigger phrase hit counts from ralph/ultrawork logs
- Routing accuracy before/after cap (a/b comparison)
- Frequency distribution of unique user phrasings per skill

**Blocks**: P2 #2 (demoted from P0)

**Owner**: dogfood instrumentation

---

## U3 — External-Project User Ratio

**Status**: No data

**Issue**: vault-searcher Mode 4 separation strategy (slash vs reference extract) depends on the proportion of vault-bridge users who do NOT have obsidian-vault-manager installed. The audit explicitly flags this as a missing data point.

**Concern**: If `/vault-write` becomes a separate slash command, ambient auto-firing ("MUST BE USED PROACTIVELY") is lost. For external-project users this may be a UX regression.

**Required data**:
- Telemetry: marketplace install ratio of vault-bridge alone vs vault-bridge + OVM
- Vault Mode 4 invocation patterns from external project sessions

**Blocks**: P3 (Mode 4 slash separation)

**Owner**: install analytics (if available)

---

## U4 — `pre-access-guard.sh` Invocation Load

**Status**: No measurement

**Issue**: Hook fires on every Read/Grep/Glob via PreToolUse. Per-call cost: jq×2 + python3 realpath ≈ ~150ms estimated. Session totals could reach 15+ seconds (100 calls).

**Required measurement**:
- Per-call ms (actual, not estimated)
- Average call count per session
- Whether systemMessage caps (N=1,5,10) are sufficient or whether the hook itself should be bypassed after N

**Blocks**: P1 #12 implementation specifics

**Owner**: hook profiling

---

## U5 — manifest.json Cache Hit Rate

**Status**: No measurement

**Issue**: vault-searcher Mode 2/3 use a 24h-TTL manifest cache. If vault changes are frequent, the staleness fall-through path (`manifest_generated_at < file_mtime`) may invalidate the cache on every query, making it net cost rather than benefit.

**Required measurement**:
- Cache hit ratio (Mode 2/3 invocations using manifest vs falling through)
- Distribution of (file mtime - manifest_generated_at) per query
- Median time spent on manifest-first vs full-scan path

**Blocks**: P2 #N4

**Owner**: vault-searcher instrumentation

---

## U6 — capture Skill LLM-Call Frequency

**Status**: Demotion was contested but data missing

**Issue**: Audit P1 #10 proposes hybridizing capture skill (slash entry + scripts/capture.sh body) for "LLM call savings". Panel demoted to P2 because the actual LLM-call frequency for capture is unknown.

**Required data**:
- Capture invocation count per session
- Per-invocation token cost (current LLM path)
- Estimated savings if shell-routed

**Blocks**: P2 #10 (demoted from P1)

**Owner**: usage analytics

---

## Resolution Strategy

| ID | Recommended next action | ETA |
|---|---|---|
| U1 | Update audit with explicit denominator | This week |
| U2 | Set up trigger logging in ralph/ultrawork | 2 weeks |
| U3 | Check marketplace install metadata | Depends on availability |
| U4 | Profile hook with `time` wrapper for 1 session | 1 day |
| U5 | Add hit/miss counter to vault-searcher Mode 2/3 | 1 week |
| U6 | Count capture invocations from existing transcripts | 1 day |

---

*6 unresolved items · 4 require new instrumentation · 2 require existing-data analysis*
