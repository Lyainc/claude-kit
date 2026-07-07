# glossary.md — claude-kit identifier registry

Single authority for the identifier prefixes used across claude-kit docs and code.
Created per **#214** (identifier-system cleanup) to resolve the `U/P/W/D/C`
tracking-ID sprawl and the local↔global namespace collisions surfaced during #215.

> 한국어 메모 (사람 독자용): 식별자 두문자어의 단일 권위 문서예요. 새 prefix를
> 발명하기 전에 여기 먼저 등록하고, 추적 가치가 있는 항목이면 평행 체계를 새로
> 만들지 말고 GitHub 이슈 번호(`#N`)에 올라타세요.

This glossary **indexes**; it does not redefine. Each global code points to its own
canonical source — the single source of truth lives there, not here.

## 1. Global classification codes (registered — kept)

These name a *kind* of thing, are globally consistent, and are healthy. Keep them.

| Prefix | Meaning | Canonical source |
|--------|---------|------------------|
| `CON-N` | Constraint (boundary / architecture constraint) | `docs/design/claude-kit-boundary.md` |
| `POL-N` | Policy (constitutional / policy rule) | `docs/design/claude-kit-boundary.md` |
| `E1`–`E11` | Vault audit error type | `obsidian-vault-manager/reference/vault-audit-rules.md` |
| `GN` | Goal-doc ID (closed series, G1–G29 — retired concept, no new entries) | `docs/plans/goal-docs/` |

**Notation.** Each global code is written in its canonical form verbatim, including
the hyphen that is part of the prefix — `CON-2`, `POL-1` — while E/G-series
codes carry no hyphen: `E8`, `G16`.

## 2. Local tracking IDs (NOT globally registered — disciplined)

`U` / `P` / `W` / `D` / `C` and similar per-document running numbers — a discussion's
`UNRESOLVED.md` `U1, U2…`, the work-rules constraints `c1…c8` in #216 / `RULES.md`,
priority sub-tiers, strangler phases — are **local**: valid only inside the document
that defines them. They are **not** registered here and MUST NOT be treated as global
handles.

The discipline (per #214):

1. **Ride the existing global ID.** Anything worth tracking globally becomes a GitHub
   issue (`#N`). Do **not** invent a parallel global tracking scheme (`U/P/W/D/C`).
2. **Keep local IDs local.** A document's running number is valid only within that
   document. When cross-referencing from elsewhere, carry the source — `<file> §U1` —
   or promote the item to an issue. A bare `U1` in another file is a collision waiting
   to happen (it already happened: two `UNRESOLVED.md` files both define `U1`).
3. **No letter reuse across meanings.** `P` already collides three ways (strangler
   phase / priority sub-tier / deferred phase). Do not overload a letter; when order
   is the essence use a distinct phase prefix, otherwise a meaningful slug.
4. **Opaque number < meaningful slug.** Use a number only when sequence is the point.
5. **One notation, no hyphen drift.** Local IDs are written letter+digit with no
   separator: `C2` not `C-2`, `U1` not `U-1`, `c1` not `c-1`.

## 3. Maintaining this glossary

- Before introducing a **new global prefix**, register it in §1 here first.
- Do not change a classification code without updating its canonical source (§1).
- **Bulk renaming of existing notation** (e.g. normalizing legacy `C-2`→`C2` across
  the doc tree) is a **later slice** of #214 — it risks link breakage across many
  docs. This first slice is **glossary + new-document discipline only**;
  existing-notation normalization follows once this authority is in place.
