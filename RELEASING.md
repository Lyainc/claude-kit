# Releasing claude-kit

claude-kit ships **lockstep**: every plugin shares one version, published together
under a single tag `vX.Y.Z`. Releases are cut manually from the GitHub Actions tab — no
tag-pushing, no release-please. This document is the source of truth for the version
policy and the release procedure.

## Version policy (lockstep)

- **One version for the whole marketplace.** `thinking-tools`, `obsidian-vault-manager`,
  `vault-bridge`, and `feedback-loop` always carry the same version, mirrored in the
  root `marketplace.json` `version` and every `plugins[].version`. Lockstep is enforced
  **at `bump-version.py` call time** (the next release writes all manifests to one
  version), not at plugin introduction — a newly added marketplace plugin may carry its
  own initial version (e.g. `feedback-loop` started at `0.1.0`) until the next release
  absorbs it.
- **One tag per release**: `vX.Y.Z`. Plugin-scoped tags are not used.
- **SemVer is judged across the whole repo**, not per plugin: pick the bump that matches
  the *largest* change shipped in the release.
  - **major** (`X`) — any breaking change in any plugin, or a marketplace-wide policy
    shift (e.g. a renamed/removed plugin, a changed install command).
  - **minor** (`Y`) — new user-facing capability (`feat`) with no breaking change.
  - **patch** (`Z`) — fixes only (`fix`, internal `refactor`/`perf`, docs, chores).
- Because it's lockstep, a change to one plugin still advances the version of all four.
  That's the accepted trade-off for a single coherent marketplace version (the
  alternative — per-plugin independent versions — was rejected; see the discussion in
  PR history). The GitHub Release notes still break the changes down **per plugin**, so
  readers can see exactly which plugin moved.

`plugin.json` is the source of truth for each plugin's `version` (plus `description`,
`keywords`); `marketplace.json` is **derived** and kept in sync by
`scripts/check-version-sync.py` (a CI block guard). The release workflow writes the new
version into all manifests at once via `scripts/bump-version.py`, so they can never
diverge across a release.

## Cutting a release

1. **Make sure `main` is green** — the `Plugin Validation` workflow must be passing on
   the commit you intend to release.
2. **Actions → Release → Run workflow.** Fill in:
   - **version** — the new SemVer, no leading `v` (e.g. `3.0.0`).
   - **dry_run** — leave **checked** for the first run.
   - **prerelease** — check only for pre-release tags (`-rc.1`, `-beta.1`, …).
3. **Review the dry-run.** The workflow renders the full release notes to the run's
   **Summary** without writing anything — no commit, no tag, no release. Read the
   per-plugin sections and confirm the version bump is right.
4. **Run again with dry_run unchecked.** The workflow then:
   - bumps every `plugin.json` + `marketplace.json` to the version (`bump-version.py`),
   - commits `chore(release): vX.Y.Z` and pushes it to `main`,
   - tags `vX.Y.Z` and pushes the tag,
   - builds the notes (curated per-plugin sections + GitHub's native "What's Changed")
     and publishes the GitHub Release.

> First lockstep release: the plugins currently carry mixed versions
> (`2.2.1` / `0.19.0` / `0.5.0`). The first run of this workflow aligns them all to the
> version you enter — there is no separate "alignment" step to do by hand. `3.0.0` is
> the suggested starting point (clears the highest existing version and signals the
> policy change), but any SemVer above `2.2.1` works.

## How release notes are built

The curated top half of the notes comes from `scripts/gen-release-notes.py`, which reads
the Conventional Commits since the previous tag. Good commit messages → good notes.

**Commit type → notes category** (per plugin section):

| Commit type | Section |
|---|---|
| `feat:` | **Added** |
| `fix:` | **Fixed** |
| `refactor:`, `perf:` | **Changed** |
| `feat!:` / `fix!:` / `BREAKING CHANGE:` footer | **Breaking Changes** |
| `docs:`, `chore:`, `test:`, `ci:`, `build:`, `style:` | omitted from curated notes (still in "What's Changed") |

**Commit → plugin mapping**: a commit lands in a plugin's section based on the files it
touched (`thinking-tools/...` → the thinking-tools section). Commits touching only shared
infra (`scripts/`, `.github/`, `docs/`, root files) land in a final
**Repository / infrastructure** section. A commit spanning several plugins appears under
each — so keep commits scoped to one plugin where practical.

Below the curated sections, the workflow appends GitHub's native **What's Changed** (the
full PR list + new contributors), so nothing is lost even if a commit type is omitted
above.

## Manual fallback

If the workflow can't run (Actions outage, etc.), the same steps by hand from a clean
`main`:

```bash
VERSION=3.0.0
PREV=$(git describe --tags --abbrev=0)

python3 scripts/bump-version.py "$VERSION"
python3 scripts/check-version-sync.py            # must be clean
git commit -am "chore(release): v$VERSION"
git push origin main
git tag "v$VERSION" && git push origin "v$VERSION"

python3 scripts/gen-release-notes.py --version "$VERSION" --from "$PREV" > notes.md
gh release create "v$VERSION" --title "v$VERSION" \
  --notes-file notes.md --generate-notes
```

Here `--notes-file` is prepended above GitHub's auto-generated What's Changed
(`--generate-notes`) — this prepend behavior is **gh CLI 2.x**; other majors may order
the two blocks differently, so pin/verify the gh version if the layout matters. The
workflow merges the two via the `generate-notes` API instead —
so the **dry-run preview shows the exact final notes** (`--generate-notes` only runs when
a release is actually created) and so the `---` divider between the curated sections and
What's Changed is under our control.
