---
name: capture
description: "Quick memo capture. Saves immediately to Inbox and outputs file path only. Example: '/capture API changes from today's meeting'"
model: haiku
allowed-tools: Read Write Bash
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Save the content of `$ARGUMENTS` to `~/vault/inbox/` immediately, without confirmation.

## Rules

When formatting the body or frontmatter, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, comments, and YAML properties.

1. Filename: `capture-YYYY-MM-DD-{slug}.md`. `{slug}` is 2–4 kebab-case words from the topic or extracted title.
2. Frontmatter (text capture):
   ```yaml
   ---
   created: YYYY-MM-DD
   tags:
     - capture
     - {topic-keyword}
   type: capture
   ---
   ```
3. Write `$ARGUMENTS` as the body.
   - If `$ARGUMENTS` starts with `http://` or `https://`, follow the **URL Capture** section instead.
4. **Directory validation**: Create `~/vault/inbox/` with `mkdir -p` if missing.
5. **Duplicate detection**: If a file with the same date and slug exists, append `-v2`, `-v3`, etc.
6. **Save immediately without confirmation.** This is the core behavior.
7. Output only the saved file path. No follow-up questions.

## URL Capture

When `$ARGUMENTS` starts with `http://` or `https://`:

**Step 1 — Defuddle parse**

1. Store `URL="$ARGUMENTS"`.
2. Check for Defuddle: `command -v defuddle`.
3. Detect a timeout helper using the same pattern as `../../reference/obsidian-cli.md` (`timeout` → `gtimeout` → none); store as `$DEFUDDLE_TO`.
4. Run `${DEFUDDLE_TO:+$DEFUDDLE_TO 15} defuddle parse "$URL" --md`; capture stdout in `$DEFUDDLE_OUT` and exit code in `$DEFUDDLE_RC`.

**Step 2 — Title extraction**

If Defuddle succeeded (`$DEFUDDLE_RC == 0`):
- Extract first H1: `TITLE=$(printf '%s' "$DEFUDDLE_OUT" | grep -m1 '^# ' | sed 's/^# //')`.
- Escape YAML double quotes: `TITLE=$(printf '%s' "$TITLE" | sed 's/"/\\"/g')`.
- Build `{slug}`: lowercase the title, replace spaces with hyphens, strip characters outside `[a-z0-9-]`, take the first 5 words (split on `-`). If the slug is empty or shorter than 2 characters (e.g. non-ASCII title fully stripped), fall back to URL-path derivation and leave `$TITLE` empty.
- If no H1 found: derive `{slug}` from the last 2–3 path segments of `$URL`; leave `$TITLE` empty.

If Defuddle is missing, fails, or times out (exit 124):
- Derive `{slug}` from the URL path. Leave `$TITLE` empty.
- Do not install anything. Jump to Step 4 (bare URL body).

**Step 3 — Frontmatter**

```yaml
---
created: YYYY-MM-DD
tags:
  - capture
  - web
type: capture
source: url-capture
url: "<original URL>"
title: "<extracted H1 title — omit this line entirely if $TITLE is empty>"
---
```

Quote the `url` and `title` values in YAML to handle special characters safely.

**Step 4 — Body**

- Defuddle succeeded: the full `$DEFUDDLE_OUT` content (including the H1 heading if present).
- Defuddle failed or unavailable: the bare URL as the only body line.

The "save immediately" behavior MUST hold regardless of Defuddle outcome.
