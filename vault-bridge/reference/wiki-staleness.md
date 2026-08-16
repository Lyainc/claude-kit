# vault-searcher — wiki staleness hedge (#305)

**Canonical text.** `vault-searcher.md` § Rules points here; this file is the binding
contract for how a `type: wiki` hit is presented, not background reading.

## The contract

`type: wiki` pages carry `verified:` (last-touched date) and, when checkable, `anchor:`
(a source file/URL the dominant claim traces to). When you return a wiki page's content,
mention its `verified:` age alongside it — this is the only staleness signal a source-free
(no `anchor:`) page has, since nothing else flags it as possibly outdated.

Don't silently present an old, anchor-free wiki claim as current fact; a plain
"as of {verified}" note is enough to let the caller hedge.

## Why `verified:` and not mtime

Prefer `verified:` over the file's raw modification date. The vault is git-committed
(`/vault-commit`) and a clone/checkout resets filesystem mtimes to the checkout time, so
mtime can understate a page's real age while `verified:` (committed frontmatter) survives
that.

## Legacy pages with no `verified:`

A legacy `type: wiki` page written before #305 may have no `verified:` field at all —
don't invent a date; say the age is unknown instead of silently omitting the hedge.
