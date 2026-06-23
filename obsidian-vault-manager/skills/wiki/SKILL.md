---
name: wiki
description: "Compile domain knowledge learned during work into a ~/vault/wiki/ page — the LLM wiki (A layer), optimized for AI recall, not human reading. A gated, explicit compile action (never always-on): you invoke it when you've learned something worth keeping. Routes by the cross-repo test (U7) and compounds onto existing pages instead of duplicating. Examples: '/wiki Defuddle CLI extracts the first H1 as the title', '이거 위키에 정리해줘', '방금 알아낸 거 wiki로 저장'. KR triggers: 'wiki에 정리', '위키 페이지로', '알아낸 거 저장', '도메인 지식 컴파일'. EN triggers: 'compile to wiki', 'save to wiki', 'add wiki page'."
allowed-tools: Read Write Bash Glob
model: sonnet
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, generated content, file contents) MUST be in Korean.

Compile the domain knowledge in `$ARGUMENTS` into a page under `~/vault/wiki/` — the **A layer** of vault second-brain v5 (`docs/design/vault-second-brain-v5.md`). The wiki is plain-markdown knowledge written *for the model to read on the human's behalf*, not for human browsing. This skill is the **query-driven compounding** entry point: what you learned while working becomes a recall-able wiki page with near-zero friction.

**This is a gated, explicit compile action — never always-on.** The gate is the explicit invocation itself (v4 §9.1 "no always-on push" is preserved). Run inline in the main context — do NOT fork to a subagent (vault writes from subagents are blocked by the Write Role Contract; `pre-write-guard.sh` denies them).

When formatting body or frontmatter, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, comments, and YAML properties. Prefer wikilinks for internal vault references.

---

## Pipeline

```
SYNTHESIZE → U7 ROUTE → DEDUP → PLAN → WRITE
```

Do not collapse phases. The U7 route and dedup checks run BEFORE any write.

---

## Phase 1 — SYNTHESIZE

Turn `$ARGUMENTS` (and the relevant exploration context from the current session) into a self-contained piece of **domain knowledge** — a fact/model/lesson that is true and reusable, written so a future model can act on it without re-deriving. Not a transcript dump, not a question; a compiled answer.

If `$ARGUMENTS` is empty or only a question (no knowledge to compile), ask the user what they learned that's worth saving — do not invent content.

---

## Phase 2 — U7 ROUTE (the cross-repo gate)

Before writing, apply the single routing test (v5 §10):

**"Is this true / useful in OTHER repos too?"**

- **Yes** — repo-transcending *domain knowledge* (e.g. "Defuddle extracts the first H1 as the title", "Obsidian Bases `.base` files are YAML view definitions"). → proceed to DEDUP and write a wiki page.
- **No** — *this repo's structure* (where things live, this project's wiring). → **do NOT write a wiki page.** Redirect (emission only, no write): tell the user in Korean that this belongs in the repo's `AGENTS.md` / deepinit, not the cross-repo wiki — e.g. "이건 이 레포 구조라 wiki(레포 초월 도메인 지식)가 아니라 AGENTS.md/deepinit에 넣는 게 맞아요. 거기 추가할까요?" The skill never writes outside the vault.
- **Mixed** — split per fragment (one wiki page = one kind of knowledge). Write the cross-repo fragments to wiki; redirect the repo-structure fragments to AGENTS.md.

State the routing decision briefly before continuing, so the user can correct it.

---

## Phase 3 — DEDUP (compounding, not duplication)

The wiki *compounds* — a topic that already has a page is **updated**, never duplicated.

1. List existing wiki pages and match by slug / title / tags:
   ```bash
   ls ~/vault/wiki/ 2>/dev/null
   ```
   Optionally consult the manifest for title/summary matches:
   ```bash
   cat ~/vault/.vault-bridge/manifest.json 2>/dev/null   # match type:wiki entries on title/tags
   ```
2. **Existing page on the same topic** → plan an **update/merge**: integrate the new knowledge into the existing page (add/refine sections, keep it coherent) and extend the `provenance:` trail with the new originating query. Do NOT create a `-v2`.
3. **No existing page** → plan a **new** page `~/vault/wiki/{slug}.md`. `{slug}` = 2–4 kebab-case words from the topic.
4. A `-v2`/`-v3` suffix is ONLY for a genuinely *different* topic that collides on slug — never for the same topic (that's an update).

---

## Phase 4 — PLAN

Show the user, before writing:
- Target path (and whether it's a **new** page or an **update** to an existing one).
- Frontmatter.
- The compiled body (or, for an update, the merge result / the sections being added).

Then write after confirmation. (The compounding KB rewards one human glance — U3 contamination compounds, so the confirmation is the cheap defense, not friction for its own sake.)

**Frontmatter** (wiki page):
```yaml
---
created: YYYY-MM-DD
tags: [{domain}]              # at least one domain tag; no `wiki` literal needed, type carries it
type: wiki
provenance: <one line: the query / exploration that produced this page>
---
```

- **No `status:` field.** The status machine (raw→draft→evergreen) is the B layer's (human review). A is outside it (v5 §4.1) — wiki pages are AI-authored, provenance-tracked, not review-status pages.
- **`provenance:` is required and always written** — it records *which exploration produced this page* (U3 traceability: a bad synthesis can be traced back to its source). For an update, append the new originating query to the existing provenance rather than overwriting it.

---

## Phase 5 — WRITE

1. `mkdir -p ~/vault/wiki/` (directory guard).
2. **New page**: write `~/vault/wiki/{slug}.md` with the frontmatter above and the compiled body.
3. **Update**: rewrite the existing page with merged content and the extended `provenance:`. Preserve the original `created:` date; do not reset it.
4. Output only the created/updated file path and whether it was new or merged. No follow-up questions.

---

## Rules

- **Gated, explicit, main-context.** Never an always-on hook. Never fork to a subagent — vault writes must originate in the main context (Write Role Contract; `pre-write-guard.sh` blocks subagent writes).
- **U7 route first.** Repo-structure knowledge is redirected to AGENTS.md/deepinit, never written to wiki. The wiki holds only cross-repo domain knowledge.
- **Compound, don't duplicate.** Same topic → update the existing page. `-v2` is only for a slug collision between genuinely different topics.
- **Always write `provenance:`.** Every wiki page carries the exploration that produced it.
- **No `status:` on wiki pages.** A is outside the status machine.
- **Filename**: `{slug}.md`, lowercase kebab — matches the `wiki/` naming convention enforced by `pre-write-guard.sh`.
- **Vault writes only inside `~/vault/wiki/`.** This skill never touches repo files (AGENTS.md redirect is guidance, not a write).
- AI recall, not human reading: write for a future model to act on, plain markdown, no embedding/DB (constitution — file-over-app).
