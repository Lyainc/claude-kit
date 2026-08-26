---
name: vault-save
description: "The single entry for putting reference material into the vault (~/vault/) — replaces the retired /capture and /note. Anything worth pulling back out while planning later: web clippings, papers, analyses, brainstorms, early plans, study notes, meeting memos. Saves immediately with no confirmation and prints the path. Destination is mechanical, by authorship: source text taken as-is (URL, pasted original, session dump) → sources/, prose you wrote → notes/. No status field and no promotion gate — the vault is a reference warehouse, so selection happens on retrieval, not at the entrance (v5 §5). KR triggers: '볼트에 저장', '메모해줘', '이거 저장해줘', '자료 저장', '받아적어줘', '클리핑 저장', '노트로 정리', '인박스에 저장'. EN triggers: 'save to vault', 'vault save', 'capture this', 'quick memo', 'save this link', 'jot this down', 'write up a note'. Examples: '/vault-save https://example.com/article', '/vault-save 오늘 회의에서 나온 API 변경점'. Routing: domain knowledge compiled for AI recall is /wiki (obsidian-vault-manager, A layer); a repo-bound design decision goes to a GitHub issue, not the vault (v5 §10)."
allowed-tools: Write Bash Glob
model: haiku  # kept: mechanical write only, no LLM judgment — merges /capture + /note (#448, #480)
effort: low
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Save `$ARGUMENTS` into `{vault_root}` immediately, without a confirmation prompt, then print only the saved path.

This skill runs in the main context. Never delegate the write to a subagent — the vault-bridge
Write Role Contract denies subagent vault writes (`hooks/pre-write-guard.sh`).

## Destination

The split is **authorship, not quality**. Nothing here judges whether the material is good enough
to keep; that judgment happens when you go looking for it again.

| Input | Folder | `type:` | Filename |
|-------|--------|---------|----------|
| Source text taken as-is — a URL, a pasted article/paper/excerpt, a raw session dump | `{vault_root}/sources/` | `capture` | `capture-YYYY-MM-DD-{slug}.md` |
| Prose you wrote — analysis, brainstorm, early plan, study note, meeting memo | `{vault_root}/notes/` | `note` | `{slug}.md` |
| `--type decision {topic}` — an explicit decision record | `{vault_root}/notes/` | `decision` | `decision-YYYY-MM-DD-{slug}.md` |
| `--type discussion {topic}` — a thinking-tools session artifact (expert-panel SUMMARY/UNRESOLVED, adversarial-review result, unknown-discovery report) | `{vault_root}/wiki/` | `discussion` | `{slug}.md` (no date prefix) |

- `{slug}`: 2–4 kebab-case words from the topic or the extracted title.
- Unsure which side? If the text would survive unchanged without you, it is source → `sources/`.
- `--type decision` is KEEP, confirmed (#477 item 2, 2026-08-04) — for non-repo-bound decisions
  only (e.g. a personal tool choice). A **repo-bound** design decision belongs in a GitHub issue,
  not here (v5 §10) — say so and stop rather than writing one.
- `--type discussion` is the one case that writes to `wiki/` (#586 c1) — the content is an AI
  compilation, not raw authorship, so it belongs with the rest of the A-layer even though it
  reads as history rather than fact (vault-discussion-history-wiring Seed, #586). Filename carries
  no date prefix — `wiki/`'s naming convention is evergreen kebab slugs, same as any other page
  there (`pre-write-guard.sh`); the date lives only in `created:`.

## Frontmatter

```yaml
---
created: YYYY-MM-DD
type: capture|note|decision|discussion
tags:
  - {type}
  - {topic-keyword}
provenance: "{where this came from — URL, session topic, conversation, book, meeting}"
---
```

- **`provenance` is required on every file.** There is no gate at the entrance, so being able to
  trace a file back to its origin is the whole defense at retrieval time (v5 §5, #480). Never
  write a file without it; if the origin is genuinely just "this conversation", say that.
- **No `status:` field.** The `raw→draft→evergreen→archived` machine and the promotion gate are
  abolished (v5 §5/§6, #480). Do not write `status:` and do not offer to promote anything.
- URL saves add `url:` and, when an H1 was extracted, `title:` (see below). Quote both values.
- `type: discussion` keeps rejected alternatives and the assumptions behind them in the body, not
  just the conclusion — a one-line verdict doesn't answer "was this still valid" or "what didn't
  we know yet" later (#586 c4/c5). Link related `wiki/` pages with `[[wikilinks]]` in the body
  (see Procedure below) rather than a dedicated frontmatter field.

## Procedure

1. Resolve `{vault_root}` with Bash — priority order `VAULT_BRIDGE_VAULT_ROOT` (env override) >
   `VAULT_BRIDGE_VAULT_PATH` (userConfig) > `~/vault` (default), same chain as
   `hooks/pre-write-guard.sh`:
   ```bash
   _vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
   [ -z "$_vr" ] && _vr="$HOME/vault"
   echo "${_vr/#\~/$HOME}"
   ```
2. Parse `$ARGUMENTS`: strip a leading `--type decision` or `--type discussion` flag if present;
   the rest is the content or URL.
3. **Vault-absent guard (#697) — check `{vault_root}` exists BEFORE creating anything.** If
   `[ -d "{vault_root}" ]` is false, **stop without writing** and tell the user in Korean that no
   vault was found at that path and where to configure one (`VAULT_BRIDGE_VAULT_ROOT`, or the
   `VAULT_BRIDGE_VAULT_PATH` plugin setting) — e.g. "`{vault_root}`에 볼트가 없어서 저장을
   멈췄어요. 볼트 경로를 `VAULT_BRIDGE_VAULT_ROOT`(환경변수)나 플러그인 설정
   `VAULT_BRIDGE_VAULT_PATH`로 지정해 주세요." Never `mkdir` the vault root itself.

   This is the same contract the rest of vault-bridge already keeps — `hooks/pre-write-guard.sh`
   and `hooks/session-start-manifest.sh` both treat a missing vault directory as "do nothing".
   Creating it here would produce a vault nobody knows about, and because
   `session-start-manifest.sh` already exited for this session, that vault never receives a
   manifest — every later manifest-dependent path (recall, dedup) then degrades silently.

   Only once the vault root exists, `mkdir -p` the target sub-directory (`sources/`, `notes/`,
   `wiki/`) before writing.
4. If the content starts with `http://` or `https://`, follow **URL capture** below; otherwise
   write the content as the body verbatim (keep the user's own wording — do not summarize).
5. Filename collision — use Glob over the target folder to see whether the same stem already
   exists, and if it does, append `-v2`, `-v3`, … automatically. This is a mechanical uniqueness
   guarantee, not a content check.
6. Write the file. For `--type decision`, structure the body as `## 문제` / `## 선택지` /
   `## 결정` / `## 근거`. `--type discussion` has no fixed structure — write whatever the caller
   already composed (SUMMARY/UNRESOLVED, adversarial-review verdicts, unknown-discovery findings)
   verbatim, same as a plain note.
7. Output the saved path. No follow-up questions, no summary of what was saved.

Use `[[wikilinks]]` for internal vault references and Markdown links for external URLs.

## URL capture

**Step 1 — Defuddle parse**

1. Store `URL="$ARGUMENTS"`.
2. Check for Defuddle: `command -v defuddle`. Do not install anything if it is missing.
3. Detect a timeout helper (`timeout` → `gtimeout` → none); store as `$DEFUDDLE_TO`.
4. Run `${DEFUDDLE_TO:+$DEFUDDLE_TO 15} defuddle parse "$URL" --md`; capture stdout in
   `$DEFUDDLE_OUT` and the exit code in `$DEFUDDLE_RC`.

**Step 2 — Title and slug**

If Defuddle succeeded (`$DEFUDDLE_RC == 0`):
- Extract the first H1: `TITLE=$(printf '%s' "$DEFUDDLE_OUT" | grep -m1 '^# ' | sed 's/^# //')`.
- Escape YAML double quotes: `TITLE=$(printf '%s' "$TITLE" | sed 's/"/\\"/g')`.
- Build `{slug}`: lowercase the title, spaces → hyphens, strip anything outside `[a-z0-9-]`, take
  the first 4 hyphen-separated words. If the slug ends up empty or shorter than 2 characters (a
  non-ASCII title stripped to nothing), fall back to the URL path and leave `$TITLE` empty.
- No H1 found: derive `{slug}` from the last 2–3 path segments of `$URL`; leave `$TITLE` empty.

If Defuddle is missing, fails, or times out (exit 124): derive `{slug}` from the URL path, leave
`$TITLE` empty, and write the bare URL as the only body line.

**Step 3 — Frontmatter and body**

```yaml
---
created: YYYY-MM-DD
type: capture
tags:
  - capture
  - web
provenance: "url-capture"
url: "<original URL>"
title: "<extracted H1 — omit this line entirely when $TITLE is empty>"
---
```

Body: the full `$DEFUDDLE_OUT` (including its H1) on success, the bare URL otherwise.

## Rules

- **Save immediately, without confirmation.** This is the core behavior — friction at the entrance
  is what killed the previous two entries (#477).
- Write `provenance:` on every file; never write `status:`.
- Save immediately regardless of the Defuddle outcome.
- Output the saved path only.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders.
- Never write to `{vault_root}/wiki/` except for `--type discussion` — every other type stays out
  of `/wiki`'s (obsidian-vault-manager) A layer.
