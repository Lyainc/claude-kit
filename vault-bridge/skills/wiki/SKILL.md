---
name: wiki
description: "Compile domain knowledge learned during work into a ~/vault/wiki/ page (the LLM wiki, A layer for AI recall). Gated, explicit compile — never always-on. Examples: '/wiki Defuddle CLI extracts the first H1 as the title', '이거 위키에 정리해줘', '방금 알아낸 거 wiki로 저장'. KR triggers: 'wiki에 정리', '위키 페이지로', '알아낸 거 저장', '도메인 지식 컴파일'. EN triggers: 'compile to wiki', 'save to wiki', 'add wiki page'."
allowed-tools: Read Write Bash AskUserQuestion
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, generated content, file contents) MUST be in Korean.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Compile the domain knowledge in `$ARGUMENTS` into a page under `~/vault/wiki/` (A layer, v5). Browsing is OVM `/base`, not this skill. Rationale and edge cases: [reference.md](reference.md), read at the section named in each phase.

**This is a gated, explicit compile action — never always-on.** Run inline in the main context — do NOT fork to a subagent (`pre-write-guard.sh` denies subagent vault writes per the Write Role Contract).

Follow `../../reference/obsidian-format.md` for body/frontmatter; prefer wikilinks.

Pipeline: SYNTHESIZE → U7 ROUTE → DEDUP → PLAN → WRITE. Do not collapse phases; route and dedup run BEFORE any write.

## Phase 1 — SYNTHESIZE

Turn `$ARGUMENTS` (plus session context) into self-contained, reusable **domain knowledge** a future model can act on — not a transcript dump or question. If `$ARGUMENTS` is empty or only a question, use AskUserQuestion to ask what is worth saving — do not invent content.

## Phase 2 — U7 ROUTE (v5 §10)

Destinations: GitHub issue / wiki / AGENTS.md. Redirect wording and mixed input: `reference.md` §Phase 2.

1. Repo-bound design decision? **Yes** → NO wiki page; tell the user in Korean it belongs in a GitHub issue and offer to create one (emission only). Stop for this fragment.
2. Else, useful in OTHER repos? **Yes** → DEDUP. **No** (this repo's structure) → NO wiki page; tell the user in Korean it belongs in `AGENTS.md` / deepinit. The skill never writes outside the vault.

**Mixed** → apply per fragment. State the routing decision briefly so the user can correct it.

## Phase 3 — DEDUP (compounding, not duplication)

0. **Vault-absent guard (#645 B1) — runs BEFORE the manifest read, and the order matters.**
   Resolve like `hooks/pre-write-guard.sh`: `VAULT_BRIDGE_VAULT_ROOT`
   (env override) > `VAULT_BRIDGE_VAULT_PATH` (userConfig) > `~/vault`:
   ```bash
   _vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
   [ -z "$_vr" ] && _vr="$HOME/vault"
   VAULT_ROOT="${_vr/#\~/$HOME}"
   if [ -d "$VAULT_ROOT" ]; then echo "$VAULT_ROOT"; [ -d "$VAULT_ROOT/.obsidian" ] || echo "VAULT_NO_OBSIDIAN"
   else echo "VAULT_ABSENT"; fi
   ```
   Each Bash call is its own shell: read the printed root and substitute it for every `$VAULT_ROOT` below.

   `VAULT_ABSENT` → **stop without writing anything.** Tell the user in Korean that no vault was
   found and where to configure one — e.g. "볼트가 없어서 wiki 컴파일을 멈췄어요. 볼트 경로를
   `VAULT_BRIDGE_VAULT_ROOT`(환경변수)나 플러그인 설정 `vault_path`로 지정해 주세요."
   **Never `mkdir` the vault root**, here or in Phase 5.

   `VAULT_NO_OBSIDIAN` → warn once, continue (#763): "`$VAULT_ROOT`에 `.obsidian/`이 없어 Obsidian 볼트가 아닐 수 있어요. 다른 경로라면 `VAULT_BRIDGE_VAULT_ROOT` 환경변수나 플러그인 설정 `vault_path`로 지정해 주세요."

1. Find existing same-topic pages (a topic with a page is **updated**, never duplicated). **Primary: the manifest**, matching `type:wiki` entries on title + tags. **Never `cat` the manifest** — the harness truncates large Bash output to a 2 KB preview, so a raw `cat` silently loses entries (#468; `reference.md` §Manifest read). Use the filter script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
   ```
   Exit 0 → parse stdout `{scanned, wiki_entries[]}` and match on title + tags.
   Exit 3 (manifest absent, unparseable, or malformed) → slug/filename fallback below (no raw retry). Also warn the user once in Korean (#645 B2), e.g. "manifest를 못 읽어서(`$VAULT_ROOT/.vault-bridge/manifest.json`) 슬러그 이름 매칭으로만
   중복을 확인해요. 같은 주제가 다른 슬러그로 있으면 못 잡을 수 있어요. `/vault-manifest-refresh`로
   다시 만들 수 있어요." This warns, it does not abort.

   **Fallback:** match by slug / filename:
   ```bash
   ls "$VAULT_ROOT/wiki/" 2>/dev/null
   ```
2. **Existing page** → Read it, plan an **update/merge** (keep it coherent, extend `provenance:`). Do NOT create a `-v2`.
   - **Lazy anchor check (#305)**: for a local-path `anchor:`, `stat` it and compare mtime to `verified:`; unchanged → skip re-deriving, changed → recompile. URL anchor: never fetch, always recompile. See `reference.md` §Lazy anchor check.
3. **No page** → plan a **new** page `$VAULT_ROOT/wiki/{slug}.md`; `{slug}` = 2–4 kebab-case words.
4. `-v2`/`-v3` only for a genuinely different topic colliding on slug.

## Phase 4 — PLAN

Show the user before writing: target path (**new** or **update**), frontmatter, and the compiled body (for an update, the merge result). Write only after confirmation.

**Frontmatter** (wiki page):
```yaml
---
created: YYYY-MM-DD
tags: [{domain}]              # at least one domain tag; no `wiki` literal needed, type carries it
type: wiki
anchor: <local path/URL>      # optional — only when this page's dominant claim traces to one checkable source; omit for source-free pages
verified: YYYY-MM-DD          # always written, auto-stamped to today on every write (new or update)
provenance: <one line: the query / exploration that produced this page; multiple updates joined with `; `>
---
```

- No `status:` field. On update, append to `provenance:` with the `; ` delimiter (`query-A; query-B`), single line, never overwrite. Field notes: `reference.md` §Phase 4.

## Phase 5 — WRITE

1. `mkdir -p "$VAULT_ROOT/wiki"` — the `wiki/` sub-directory only, because Phase 3 step 0 proved `$VAULT_ROOT` exists. **Never `mkdir` the vault root** (#645 B1).
2. **New**: write `$VAULT_ROOT/wiki/{slug}.md` with the frontmatter above; stamp `verified:` to today.
3. **Update**: rewrite with merged content and extended `provenance:`; preserve `created:`; stamp `verified:` to today either way.
4. Output only the file path and whether it was new or merged. No follow-up questions.

## Rules

- **Gated, explicit, main-context.** Never an always-on hook; never fork to a subagent (Write Role Contract).
- **U7 route first.** Repo-structure knowledge goes to AGENTS.md/deepinit, never wiki.
- **Compound, don't duplicate.** Same topic → update; `-v2` only for a slug collision between different topics.
- **Always write `provenance:`.** Every wiki page carries the exploration that produced it.
- **Always stamp `verified:` to today on write.** No exceptions, no schedule, no "re-verify" step (#305).
- **No `status:` on wiki pages.** A is outside the status machine.
- **Filename**: `{slug}.md`, lowercase kebab (`pre-write-guard.sh` convention).
- **Vault writes only inside `$VAULT_ROOT/wiki/`** — the root step 0 resolved, never a hardcoded `~/vault` (#613/#616; `reference.md` §Rules). Never touch repo files.
- AI recall is primary: plain markdown, no embedding/DB.
