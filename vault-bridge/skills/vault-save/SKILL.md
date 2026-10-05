---
name: vault-save
description: "Save requested reference material to the configured Obsidian vault: source text/URLs/session dumps to sources/, authored prose to notes/. Use wiki for compiled domain knowledge, add-policy for behavioral rules, and issue-raise for repository work proposals. A generic save request needs an established vault destination; explicit file paths/formats win. KR triggers: '볼트에 저장', '자료 저장', '클리핑 저장', '인박스에 저장'. EN triggers: 'save to vault', 'vault save', 'save this link to the vault'. Examples: '/vault-save https://example.com/article', '/vault-save 오늘 회의에서 나온 API 변경점'."
allowed-tools: Write Bash Glob Read
model: haiku  # kept: mechanical write only, no LLM judgment — merges /capture + /note (#448, #480)
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Invoke for an explicit vault-save request or an established vault destination. A generic
“save this” with an explicit different path or format is ordinary file work. Once invoked, save
`$ARGUMENTS` into `{vault_root}` immediately, without a confirmation prompt, then print only the saved path.

This skill runs in the main context. Never delegate the write to a subagent — the vault-bridge
Write Role Contract denies subagent vault writes (`hooks/pre-write-guard.sh`).

## Destination

The split is **authorship, not quality** (`reference.md` §Destination notes).

| Input | Folder | `type:` | Filename |
|-------|--------|---------|----------|
| Source text taken as-is — a URL, a pasted article/paper/excerpt, a raw session dump | `{vault_root}/sources/` | `capture` | `capture-YYYY-MM-DD-{slug}.md` |
| Prose you wrote — analysis, brainstorm, early plan, study note, meeting memo | `{vault_root}/notes/` | `note` | `{slug}.md` |
| `--type decision {topic}` — an explicit decision record | `{vault_root}/notes/` | `decision` | `decision-YYYY-MM-DD-{slug}.md` |
| `--type discussion {topic}` — a thinking-tools session artifact (expert-panel SUMMARY/UNRESOLVED, adversarial-review result, unknown-discovery report) | `{vault_root}/wiki/` | `discussion` | `{slug}.md` (no date prefix) |

- `{slug}`: 2–4 kebab-case words from the topic or title. Unsure? Text that would survive unchanged without you is source → `sources/`.
- `--type decision` is for non-repo-bound decisions only. A **repo-bound** design decision belongs in a GitHub issue (v5 §10) — say so and stop rather than writing one.
- `--type discussion` is the one case that writes to `wiki/` (#586); no date prefix in the filename (the date lives only in `created:`).

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

- **`provenance` is required on every file** (v5 §5, #480); never write a file without it. If the origin is just "this conversation", say that.
- **No `status:` field**; do not offer to promote anything (v5 §5/§6, #480).
- URL saves add `url:` and, when an H1 was extracted, `title:` (see below). Quote both values.
- `type: discussion` keeps rejected alternatives and their assumptions in the body (#586); link related `wiki/` pages with `[[wikilinks]]`. More: `reference.md` §Frontmatter notes.

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
   `vault_path` plugin setting) — e.g. "`{vault_root}`에 볼트가 없어서 저장을
   멈췄어요. 볼트 경로를 `VAULT_BRIDGE_VAULT_ROOT`(환경변수)나 플러그인 설정
   `vault_path`로 지정해 주세요." Never `mkdir` the vault root itself.

   Rationale: `reference.md` §Procedure step 3.

   Root exists but `[ -d "{vault_root}/.obsidian" ]` is false → warn once, continue (#763): "`{vault_root}`에 `.obsidian/`이 없어 Obsidian 볼트가 아닐 수 있어요. 다른 경로라면 `VAULT_BRIDGE_VAULT_ROOT` 환경변수나 플러그인 설정 `vault_path`로 지정해 주세요."

   Once the root exists, `mkdir -p` the target sub-directory before writing.
4. If the content starts with `http://` or `https://`, follow **URL capture** below; otherwise
   write the content as the body verbatim (keep the user's own wording — do not summarize).
5. Filename collision — use Glob over the target folder; if the stem exists, append `-v2`, `-v3`, … automatically (mechanical uniqueness, not a content check).
6. Write the file. For `--type decision`, structure the body as `## 문제` / `## 선택지` /
   `## 결정` / `## 근거`. `--type discussion` has no fixed structure — write whatever the caller
   already composed (SUMMARY/UNRESOLVED, adversarial-review verdicts, unknown-discovery findings)
   verbatim, same as a plain note.
7. Output the saved path only. No follow-up questions or summary.

Use `[[wikilinks]]` for internal vault references, Markdown links for external URLs.

## URL capture

**Step 1 — Defuddle parse**

1. Store `URL="$ARGUMENTS"`.
2. Check for Defuddle: `command -v defuddle`. Do not install anything if it is missing.
3. Timeout helper (`timeout` → `gtimeout` → none) → `$DEFUDDLE_TO`.
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

- **Save immediately, without confirmation** (#477; `reference.md` §Rules).
- Write `provenance:` on every file; never write `status:`.
- Save immediately regardless of the Defuddle outcome; output the saved path only.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders.
- Never write to `{vault_root}/wiki/` except for `--type discussion` (#645).
