#!/usr/bin/env python3
"""Vault-absent guard contract (#697, #645 B1) — a vault-writing skill must ABORT, never `mkdir`.

vault-bridge's established contract is **vault directory missing = do nothing**:
`hooks/pre-write-guard.sh:52-54` and `hooks/session-start-manifest.sh` both exit 0 on
`[ ! -d "$VAULT_ROOT" ]`. The skills that write into the vault used to do the opposite —
`mkdir -p` the target unconditionally — so on a machine with no vault the first call
materialised a **ghost vault**: the user sees a printed path and reads it as success, but
`session-start-manifest.sh` already exited for that session, so the new vault never receives a
manifest and every later manifest-dependent path (recall, DEDUP) degrades silently.

The two failure directions this pins, per skill:
  - the guard's EXISTENCE (a `-d` check reaching the user with a stop, not a create), and
  - the absence of an unconditional vault-root `mkdir` anywhere in the body.

Both directions are needed. A body can keep a perfectly worded guard paragraph and still carry a
`mkdir -p ~/vault/...` two steps below it; a body can also drop the guard while keeping no mkdir
at all and silently regain the create through a reworded step. Neither check alone sees both.

Run: python3 vault-bridge/scripts/test/test-vault-absent-guard.py
  -> "OK: all N vault-absent-guard checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (mutated copies of the REAL skill bodies, no writes):
  python3 vault-bridge/scripts/test/test-vault-absent-guard.py --self-test
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Every skill in this plugin that writes files into the vault. `/wiki` joined the list when its
# deployment unit moved OVM -> vault-bridge (#645); the guard contract is per-writer, so a new
# vault-writing skill adds a row here rather than growing its own test file.
WRITERS = {
    "vault-save": ROOT / "skills" / "vault-save" / "SKILL.md",
    "wiki": ROOT / "skills" / "wiki" / "SKILL.md",
}

errors: list[str] = []


def check(cond: bool, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


# --- direction 1: the guard exists and stops -------------------------------------------
#
# Matched as a conjunction of three independent properties rather than one verbatim sentence:
# the two skills word the guard differently (one resolves `{vault_root}` first, the other uses
# `$VAULT_ROOT`), and a verbatim pin across both would force their prose to converge for no
# contract reason. Each property below is separately necessary — see the FAIL messages.
_DASH_D_RE = re.compile(r"\[\s*!?\s*-d\s")          # a shell directory test on the vault root
_ISSUE_RE = re.compile(r"#697|#645")                 # traceable to the deciding issue
_STOP_WORDS_RE = re.compile(
    r"stop without writing|stop, without writing|abort|멈췄어요|중단", re.IGNORECASE)
_NEVER_MKDIR_RE = re.compile(r"[Nn]ever `?mkdir`? the vault root")

# The guard's own numbered step, marker to the next step/heading. The stop-word check runs
# against THIS slice, not the whole body, because a stop word anywhere else is not evidence
# about this branch — and one such word sits two steps below in wiki/SKILL.md, inside the
# sentence "this warns, it does not abort" describing the exit-3 branch (#645 B2). Searching
# the whole body let that sentence, which asserts the OPPOSITE, report the check as satisfied.
_GUARD_BLOCK_RE = re.compile(
    r"^\d+\. \*\*Vault-absent guard\b.*?(?=^\d+\. |^#{1,6} |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _guard_block(text: str) -> str:
    """The vault-absent guard step's own text ("" when the guard is gone entirely)."""
    m = _GUARD_BLOCK_RE.search(text)
    return m.group(0) if m else ""

# --- direction 2: no unconditional vault-root create ------------------------------------
#
# The literal defect this pins is `mkdir` against a HARDCODED vault path — `mkdir -p ~/vault/wiki/`
# (the #645 B1 text) and `mkdir -p {vault_root}` (the #697 text). Those bypass the resolved root
# entirely, so no guard anywhere in the body can have covered them, and `-p` silently creates the
# root along the way.
#
# `mkdir -p "$VAULT_ROOT/wiki"` is deliberately NOT matched: `$VAULT_ROOT` only holds a value
# because the guard block resolved and tested it, so that form is the guard's own output, not a
# bypass of it. No regex can tell "this mkdir is guarded" from "this one isn't" — that half of the
# contract is what direction 1's checks carry, which is why both directions are needed.
_ROOT_MKDIR_RE = re.compile(
    r"mkdir\s+(?:-\w+\s+)*[\"']?(?:~/vault|\$HOME/vault|\{vault_root\})")


def guard_checks(bodies: dict) -> list:
    """Static pins for the vault-absent guard, as (ok, description) pairs.

    Split out of main() so --self-test runs the identical checks against mutated copies of the
    real skill bodies.
    """
    out = []
    for name, text in sorted(bodies.items()):
        guard = _guard_block(text)
        out += [
            (bool(guard),
             f"{name}: the vault-absent guard step is present at all"),
            (bool(_DASH_D_RE.search(guard)),
             f"{name}: the guard tests the vault directory with `[ -d ... ]` before writing"),
            (bool(_STOP_WORDS_RE.search(guard)),
             f"{name}: the vault-absent branch STOPS (aborts) instead of creating"),
            (bool(_NEVER_MKDIR_RE.search(guard)),
             f"{name}: the guard states the vault root is never `mkdir`ed"),
            (bool(_ISSUE_RE.search(guard)),
             f"{name}: the guard cites its deciding issue (#697 / #645)"),
            (not _ROOT_MKDIR_RE.search(text),
             f"{name}: body carries NO unconditional `mkdir` of the vault root "
             f"(the #697 ghost-vault defect itself)"),
        ]
    return out


# ---------------------------------------------------------------------------
# Mutation fixtures, built by `.replace()` off the REAL bodies. The no-op guard below catches a
# fixture whose target string has drifted: a fixture identical to its base is an expect-FAIL case
# testing nothing (same discipline as test-manifest-reads.py).
# ---------------------------------------------------------------------------

_CLEAN = {name: path.read_text(encoding="utf-8") for name, path in WRITERS.items()}


def _mutate(name: str, old: str, new: str) -> dict:
    """A copy of the clean body set with one skill's body mutated."""
    bodies = dict(_CLEAN)
    bodies[name] = bodies[name].replace(old, new)
    return bodies


# The guard deleted outright and the original defect restored — the #697 regression itself.
_SAVE_GHOST_RESTORED = _mutate(
    "vault-save",
    "3. **Vault-absent guard (#697)",
    "3. `mkdir -p {vault_root}` then write. **Removed guard (#697)")
# Every stop/abort word removed, so the guard branch no longer says what to DO on a missing
# vault. Mutating only the English clause is not enough — the Korean user message repeats the
# abort ("멈췄어요"), so a half-mutation leaves the body still correctly saying "stop" and the
# check still correctly passing. The regression this models is the whole branch going soft.
_SAVE_STOP_SOFTENED = dict(_CLEAN)
_SAVE_STOP_SOFTENED["vault-save"] = _STOP_WORDS_RE.sub(
    "create it and continue", _SAVE_STOP_SOFTENED["vault-save"])
_WIKI_GHOST_RESTORED = _mutate(
    "wiki", "0. **Vault-absent guard", "0. `mkdir -p ~/vault/wiki/`. **Removed guard")
_WIKI_NEVER_MKDIR_DELETED = _mutate(
    "wiki", "Never `mkdir` the vault root", "Create the vault root as needed")

_CASES = [
    ("clean skill bodies pass every guard check", _CLEAN, True),
    ("vault-save regains the unconditional vault mkdir -> FAIL (the #697 defect)",
     _SAVE_GHOST_RESTORED, False),
    ("vault-save's abort softened into create-and-continue -> FAIL",
     _SAVE_STOP_SOFTENED, False),
    ("wiki regains the unconditional `mkdir -p ~/vault/wiki/` -> FAIL (#645 B1)",
     _WIKI_GHOST_RESTORED, False),
    ("wiki drops the 'never mkdir the vault root' clause -> FAIL",
     _WIKI_NEVER_MKDIR_DELETED, False),
]

for _name, _fixture, _ in _CASES:
    if _fixture is _CLEAN:
        continue
    _drifted = [k for k in _CLEAN if _fixture[k] != _CLEAN[k]]
    assert _drifted, f"fixture {_name!r} is identical to its base — its .replace() no-opped"


def _self_test() -> int:
    cases = []
    for desc, bodies, expect_pass in _CASES:
        results = guard_checks(bodies)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {n}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main() -> int:
    missing = [f"{n}: {p}" for n, p in WRITERS.items() if not p.is_file()]
    for m in missing:
        check(False, f"skill body exists ({m})")
    if missing:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1

    for ok, desc in guard_checks(
        {n: p.read_text(encoding="utf-8") for n, p in WRITERS.items()}
    ):
        check(ok, desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all vault-absent-guard checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (mutated copies of the real skill bodies)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
