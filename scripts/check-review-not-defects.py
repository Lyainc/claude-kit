#!/usr/bin/env python3
"""check-review-not-defects.py — `Review: not defects` entry drift guard (#689).

`docs/review-not-defects.md` is the one repo-level list of owner-judged false positives for reviewers. Each entry is a bullet block with labels
`**Pattern:**`, `**Why:**`, `**Anchor:**` (`path::symbol`) and `**Proof:**` (`test file::test name`).
This guard fails when a label is missing, the Anchor or Proof file is missing, or its Python
symbol is no longer defined (Anchor: module-level def/class/assignment; Proof: a `test_*` function), so a stale entry is fixed or deleted instead of rotting.

Usage:
    python3 scripts/check-review-not-defects.py [--root DIR] [--self-test]

Exit codes: 0 = clean. 1 = broken entry. 2 = usage error.
"""
import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile

LIST = "docs/review-not-defects.md"
LABELS = ("Pattern", "Why", "Anchor", "Proof")


LABEL_RE = re.compile(r"^(\s*)(-\s+)?\*\*(\w+):\*\*\s*(.*)$")


def parse_entries(text):
    """Return (entries, errors); entries are (first_line, {label: value}) for the list file."""
    entries, errors, cur, fence = [], [], None, False
    for no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = LABEL_RE.match(line)
        if not m or m.group(3) not in LABELS:
            continue
        bullet, label, value = m.group(2), m.group(3), m.group(4).strip()
        if label == "Pattern":
            if not bullet:
                errors.append(f"line {no}: **Pattern:** must start a bulleted entry (`- **Pattern:**`)")
                cur = None  # its labels must not attach to the previous entry
                continue
            cur = (no, {})
            entries.append(cur)
        elif cur is None:
            errors.append(f"line {no}: **{label}:** appears before any `- **Pattern:**` entry")
            continue
        if label in cur[1]:
            errors.append(f"line {no}: duplicate **{label}:** in the entry starting at line {cur[0]}")
            continue
        cur[1][label] = value
    return entries, errors


def _ref(value):
    m = re.search(r"`([^`]+)::([^`]+)`", value or "")
    return (m.group(1), m.group(2)) if m else None


def _read(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _symbol_defined(src, sym, proof=False):
    """Anchor: module-level def/class/assignment target named sym.
    Proof: a `test_*` function, module-level or a method of a module-level class."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    funcs = (ast.FunctionDef, ast.AsyncFunctionDef)
    if proof:
        if not sym.startswith("test_"):
            return False
        for node in tree.body:
            if isinstance(node, funcs) and node.name == sym:
                return True
            if isinstance(node, ast.ClassDef) and any(isinstance(n, funcs) and n.name == sym for n in node.body):
                return True
        return False
    for node in tree.body:
        if isinstance(node, funcs + (ast.ClassDef,)) and node.name == sym:
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if any(isinstance(n, ast.Name) and n.id == sym for n in ast.walk(t)):
                    return True
    return False


def _inside_root(root, rel):
    if os.path.isabs(rel):
        return False
    real_root = os.path.realpath(root)
    return os.path.realpath(os.path.join(real_root, rel)).startswith(real_root + os.sep)


def check(root):
    errors, count = [], 0
    text = _read(root, LIST)
    if text is None:
        return None, 0
    rel = LIST
    entries, perrs = parse_entries(text)
    errors += [f"{rel}:{e}" for e in perrs]
    for no, fields in entries:
        count += 1
        where = f"{rel}:{no}"
        present = [l for l in LABELS if fields.get(l)]
        missing = [l for l in LABELS if l not in present]
        if missing:
            errors.append(f"{where}: entry lacks label(s): {', '.join(missing)}")
        for label in ("Anchor", "Proof"):
            if label not in present:
                continue
            ref = _ref(fields[label])
            if not ref:
                errors.append(f"{where}: {label} must be `<repo-relative path>::<symbol>`")
                continue
            path, sym = ref
            if not _inside_root(root, path):
                errors.append(f"{where}: {label} path must be repo-relative and inside the repo: {path}")
                continue
            src = _read(root, path)
            if src is None:
                errors.append(f"{where}: {label} file missing: {path}")
            elif not path.endswith(".py"):
                errors.append(f"{where}: {label} {path}: only Python anchors/proofs are supported")
            elif not _symbol_defined(src, sym, label == "Proof"):
                errors.append(f"{where}: {label} symbol `{sym}` not defined in {path} "
                              f"({'a test_ function' if label == 'Proof' else 'a module-level symbol'} is required)")
    return errors, count


def self_test():
    entry = ("- **Pattern:** p\n  - **Why:** w\n"
             "  - **Anchor:** `src/a.py::foo`\n  - **Proof:** `test/t.py::test_foo`\n")
    good = {LIST: "# x\n\n" + entry, "src/a.py": "def foo():\n    pass\n",
            "test/t.py": "class T:\n    def test_foo(self):\n        pass\n"}
    cases = [
        ("good fixture passes", {}, None),
        ("removed anchor symbol", {"src/a.py": "def bar():\n    pass\n"}, "Anchor symbol `foo` not defined"),
        ("missing anchor file", {"src/a.py": None}, "Anchor file missing"),
        ("removed proof test", {"test/t.py": "pass\n"}, "Proof symbol `test_foo` not defined"),
        ("proof name only in a comment", {"test/t.py": "# test_foo\n"}, "Proof symbol `test_foo` not defined"),
        ("missing label", {LIST: "# x\n\n" + entry.replace("  - **Why:** w\n", "")}, "lacks label(s): Why"),
        ("non-Python anchor", {"src/a.py": None, "src/a.sh": "foo\n",
                               LIST: "# x\n\n" + entry.replace("a.py", "a.sh")},
         "only Python anchors/proofs are supported"),
        ("orphan label before any entry", {LIST: "# x\n\n  - **Why:** w\n" + entry},
         "before any `- **Pattern:**` entry"),
        ("duplicate label in one entry", {LIST: "# x\n\n" + entry + "  - **Why:** again\n"}, "duplicate **Why:**"),
        ("label inside fenced block ignored", {LIST: "# x\n\n" + entry + "\n```\n- **Pattern:** q\n  - **Why:** z\n```\n"}, None),
        ("non-bulleted Pattern", {LIST: "# x\n\n" + entry.replace("- **Pattern:**", "**Pattern:**")},
         "must start a bulleted entry"),
        ("non-test proof", {"test/t.py": "def helper():\n    pass\n"}, "Proof symbol `test_foo` not defined"),
        ("nested local-only anchor", {"src/a.py": "def outer():\n    def foo():\n        pass\n"},
         "Anchor symbol `foo` not defined"),
        ("parent-dir anchor path", {LIST: "# x\n\n" + entry.replace("src/a.py", "../a.py")},
         "Anchor path must be repo-relative"),
        ("absolute proof path", {LIST: "# x\n\n" + entry.replace("test/t.py", "/etc/t.py")},
         "Proof path must be repo-relative"),
    ]
    failures = []
    for desc, mutation, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            for rel, content in {**good, **mutation}.items():
                p = os.path.join(tmp, rel)
                if content is None:
                    continue
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w") as fh:
                    fh.write(content)
            errs, n = check(tmp)
        if expected is None:
            if errs or n != 1:
                failures.append(f"  {desc}: expected clean with 1 entry, got {errs} n={n}")
        elif not any(expected in e for e in errs):
            failures.append(f"  {desc}: expected error containing {expected!r}, got {errs}")
    if failures:
        print("FAIL: check-review-not-defects self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-review-not-defects self-test cases passed")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    root = a.root or subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                                    text=True).stdout.strip()
    if not root or not os.path.isdir(root):
        print("ERROR: cannot determine repository root", file=sys.stderr)
        return 2
    errors, n = check(root)
    if errors is None:
        print(f"ERROR: {LIST} not found under {root}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL: check-review-not-defects")
        print("\n".join("  " + e for e in errors))
        return 1
    print(f"OK: check-review-not-defects clean - {n} entry(ies) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
