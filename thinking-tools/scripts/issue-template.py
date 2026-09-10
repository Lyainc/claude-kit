#!/usr/bin/env python3
"""issue-template.py — issue-raise template discovery + heading extraction.

WHY: issue-raise used to name `.github/ISSUE_TEMPLATE/bug.md` and `feature.md` directly.
Those are *this* repo's filenames. GitHub's own scaffolding writes `bug_report.md` /
`feature_request.md`, modern repos ship `.yml` issue *forms* (no `## ` headings at all),
and the majority of repos ship no template. Each of those made the skill either pick a
nonexistent file or assemble an empty body. Discovery belongs in one place that reads what
is actually on disk, so SKILL.md can stop hardcoding names — the same call-time-read
principle Phase 0 already applies to headings.

Zero LLM cost, stdlib only (same philosophy as backlog-prefilter.py / check-heading-match.py).

Usage:
    issue-template.py --list [--root DIR] [--json]
    issue-template.py --headings <template path>
    issue-template.py --self-test

`--headings` prints the template's section list as `## ` lines, which is exactly the shape
check-heading-match.py's `--template` consumes — so a `.yml` form conforms through the same
guard as a `.md` template, with no second code path in the guard.

Exit codes:
    0 = ok (templates found, headings printed, or --self-test passed)
    1 = no template found (--list), or the template has no sections (--headings)
    2 = usage error / unreadable path
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# GitHub resolves issue templates from these three roots, in this order.
TEMPLATE_DIRS = (".github/ISSUE_TEMPLATE", "ISSUE_TEMPLATE", "docs/ISSUE_TEMPLATE")
# Legacy single-template locations, used only when no template directory exists.
LEGACY_FILES = (
    ".github/ISSUE_TEMPLATE.md",
    ".github/issue_template.md",
    "ISSUE_TEMPLATE.md",
    "docs/ISSUE_TEMPLATE.md",
)
# `config.yml` configures the chooser (blank_issues_enabled, contact links). Never a template.
NOT_A_TEMPLATE = {"config.yml", "config.yaml"}

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
# A trailing parenthetical carrying one of these marks the section optional. Language-open
# on purpose: this repo writes `(선택)`, GitHub's English scaffolds write `(optional)`.
OPTIONAL_WORDS = ("선택", "optional", "if applicable", "nice to have", "任意", "可选")
PAREN_TAIL_RE = re.compile(r"[(（]([^()（）]*)[)）]\s*$")

DEFECT_WORDS = ("bug", "defect", "crash", "error", "regression", "fix", "버그", "결함", "오류")
PROPOSAL_WORDS = (
    "feature", "enhancement", "proposal", "request", "idea", "improvement",
    "기능", "제안", "개선",
)


def _kind(*hints):
    """defect | proposal | other — from filename and frontmatter name/about text."""
    blob = " ".join(h for h in hints if h).lower()
    if any(w in blob for w in DEFECT_WORDS):
        return "defect"
    if any(w in blob for w in PROPOSAL_WORDS):
        return "proposal"
    return "other"


def is_optional(heading):
    tail = PAREN_TAIL_RE.search(heading)
    if not tail:
        return False
    return any(w in tail.group(1).lower() for w in OPTIONAL_WORDS)


def _scalar(raw):
    """Strip one layer of quotes from a YAML scalar. Not a YAML parser — see module ceiling."""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def _labels(raw):
    """`labels: bug` / `labels: [bug, triage]` / `labels: ["bug"]` → ['bug', 'triage']."""
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [_scalar(p) for p in v.split(",") if _scalar(p)]


def parse_md(text):
    """Markdown template → (meta, sections). Sections are ordered {name, optional}."""
    meta = {"title_prefix": "", "labels": [], "name": "", "about": ""}
    fm = FRONTMATTER_RE.match(text)
    if fm:
        block_key = None
        for line in fm.group(1).splitlines():
            if re.match(r"^\s*-\s", line) and block_key == "labels":
                meta["labels"].append(_scalar(line.split("-", 1)[1]))
                continue
            m = re.match(r"^([A-Za-z_-]+):(.*)$", line)
            if not m:
                continue
            key, raw = m.group(1).lower(), m.group(2)
            block_key = key if not raw.strip() else None
            if key == "title":
                meta["title_prefix"] = _scalar(raw)
            elif key == "labels" and raw.strip():
                meta["labels"] = _labels(raw)
            elif key in ("name", "about"):
                meta[key] = _scalar(raw)
    body = FRONTMATTER_RE.sub("", text, count=1)
    sections = [{"name": h, "optional": is_optional(h)} for h in HEADING_RE.findall(body)]
    return meta, sections


def parse_form(text):
    """GitHub issue *form* (.yml) → (meta, sections).

    ponytail: indentation scanner over the fixed issue-form schema, not a YAML parser —
    no PyYAML in this toolchain and the schema is a closed shape (top-level scalars plus a
    `body:` list of `type`/`attributes.label`/`validations.required`). A form using YAML
    anchors, multi-line folded labels, or flow mappings reads as fewer sections than it has;
    upgrade to a real parser only if such a form actually shows up.
    """
    meta = {"title_prefix": "", "labels": [], "name": "", "about": ""}
    sections = []
    in_body = False
    cur = None
    ctx = None  # 'attributes' | 'validations' — which sub-block the scanner is inside
    item_indent = None  # indentation of the body list's own `-` marker, set from the first item
    block_key = None  # top-level key currently open for a block-style YAML list (e.g. labels)

    def flush():
        if cur and cur.get("label") and cur.get("type") != "markdown":
            sections.append({"name": cur["label"], "optional": not cur.get("required", False)})

    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # A block-style top-level `labels:` list (`labels:\n  - bug\n  - triage` — valid
        # GitHub issue-form syntax, parse_md already supports it for .md via `block_key`).
        if not in_body and block_key == "labels" and re.match(r"^\s*-\s", line):
            meta["labels"].append(_scalar(line.split("-", 1)[1]))
            continue
        top = re.match(r"^([A-Za-z_-]+):(.*)$", line)
        if top:
            key, raw = top.group(1).lower(), top.group(2)
            if key == "body":
                in_body = True
                block_key = None
                continue
            in_body = False
            flush()
            cur = None
            block_key = key if not raw.strip() else None
            if key == "title":
                meta["title_prefix"] = _scalar(raw)
            elif key == "labels" and raw.strip():
                meta["labels"] = _labels(raw)
            elif key == "name":
                meta["name"] = _scalar(raw)
            elif key == "description":
                meta["about"] = _scalar(raw)
            continue
        if not in_body:
            continue
        item = re.match(r"^(\s*)-\s+(.*)$", line)
        # A nested list (dropdown/checkboxes `attributes.options:`) also uses `- `, but always
        # deeper-indented than the body list's own item marker — only THAT indentation starts
        # a new field; a deeper one is option content, not a sibling item.
        if item and (item_indent is None or len(item.group(1)) <= item_indent):
            if item_indent is None:
                item_indent = len(item.group(1))
            flush()
            cur = {}
            ctx = None
            line = "  " + item.group(2)  # a `- type: x` opener carries the first key inline
        if cur is None:
            continue
        kv = re.match(r"^\s*([A-Za-z_-]+):(.*)$", line)
        if not kv:
            continue
        key, raw = kv.group(1).lower(), kv.group(2)
        if key in ("attributes", "validations"):
            ctx = key
        elif key == "type":
            cur["type"] = _scalar(raw)
        elif key == "label" and ctx == "attributes":
            cur["label"] = _scalar(raw)
        elif key == "required" and ctx == "validations":
            cur["required"] = _scalar(raw).lower() == "true"
        elif key == "required" and ctx == "attributes":
            # checkboxes has no field-level validations block — GitHub puts `required:`
            # per-option under attributes.options[] instead (e.g. a mandatory Code of
            # Conduct checkbox). Any option required makes the whole field required.
            if _scalar(raw).lower() == "true":
                cur["required"] = True
    flush()
    return meta, sections


def parse(path):
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() in (".yml", ".yaml"):
        return parse_form(text)
    return parse_md(text)


def repo_root(start="."):
    """Templates live at the repo root, but a session's cwd is often a subdirectory —
    resolving from cwd would report 'no template' on a repo that has one."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return start


def find_templates(root="."):
    root = Path(root)
    found = []
    for d in TEMPLATE_DIRS:
        for p in sorted((root / d).glob("*")):
            if p.suffix.lower() not in (".md", ".yml", ".yaml"):
                continue
            if p.name.lower() in NOT_A_TEMPLATE:
                continue
            found.append(p)
        if found:
            break
    if not found:
        for f in LEGACY_FILES:
            if (root / f).is_file():
                found.append(root / f)
                break
    out = []
    for p in found:
        try:
            meta, sections = parse(p)
        except (OSError, UnicodeDecodeError):
            # A non-UTF-8 template (plausible for a Korean-authored repo, exactly the
            # portability case this script exists for) must not crash discovery for
            # every OTHER template — skip it like any other unreadable file.
            continue
        out.append(
            {
                "path": str(p),
                "kind": _kind(p.stem, meta["name"], meta["about"]),
                "name": meta["name"] or p.stem,
                "title_prefix": meta["title_prefix"],
                "labels": meta["labels"],
                "sections": sections,
            }
        )
    return out


NO_TEMPLATE = (
    "[issue-template NONE] 이 저장소엔 이슈 템플릿이 없어요 — 헤딩을 지어내지 말고 "
    "제목 + 평문 본문으로 쓰고, Phase 2.5(헤딩 대조)는 건너뛰세요."
)


def render(templates):
    if not templates:
        return NO_TEMPLATE
    lines = [f"[issue-template] {len(templates)}개 발견 — 종류를 보고 하나 고르세요."]
    for t in templates:
        opt = sum(1 for s in t["sections"] if s["optional"])
        lines.append(
            f"  {t['kind']:<8} {t['path']}  섹션 {len(t['sections'])}개"
            f"{f' (선택 {opt}개)' if opt else ''}"
        )
        if t["title_prefix"]:
            lines.append(f"           제목 접두어: {t['title_prefix']!r}")
        if t["labels"]:
            lines.append(f"           라벨: {', '.join(t['labels'])}")
    lines.append(
        "섹션 목록은 `--headings <path>`로 받아서 그대로 조립하고, 그 출력이 "
        "check-heading-match.py의 `--template` 입력이에요."
    )
    return "\n".join(lines)


def _write(base, rel, content=""):
    p = Path(base) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _discovery_checks():
    """find_templates()/repo_root() are the actual filesystem-facing behavior the branch's
    commit message claims is pinned (GitHub scaffold names, config.yml never a template,
    TEMPLATE_DIRS priority, LEGACY_FILES fallback, cwd-independent discovery) — self_test()
    otherwise only ever calls parse_md/parse_form/is_optional directly on in-memory strings,
    so none of find_templates()'s own glob/priority/exclusion logic was ever exercised."""
    cases = []
    bug_md = "---\nname: Bug\nabout: bug\ntitle: \"fix: \"\n---\n\n## 증상\n"

    with tempfile.TemporaryDirectory() as tmp:
        # GitHub's own scaffold filename (not this repo's `bug.md`) must be discovered.
        _write(tmp, ".github/ISSUE_TEMPLATE/bug_report.md", bug_md)
        found = find_templates(tmp)
        cases.append(("discover-github-scaffold-name",
                      [Path(t["path"]).name for t in found], ["bug_report.md"]))
        cases.append(("discover-github-scaffold-kind", found[0]["kind"] if found else None, "defect"))

    with tempfile.TemporaryDirectory() as tmp:
        # config.yml only configures the chooser — it must never be read as a template.
        _write(tmp, ".github/ISSUE_TEMPLATE/config.yml", "blank_issues_enabled: false\n")
        cases.append(("config-yml-is-not-a-template", find_templates(tmp), []))

    with tempfile.TemporaryDirectory() as tmp:
        # A non-UTF-8 template (plausible for a Korean-authored repo — exactly the
        # portability case this script targets) must be skipped, not crash discovery
        # for every other template in the same directory.
        _write(tmp, ".github/ISSUE_TEMPLATE/bug_report.md", bug_md)
        (Path(tmp) / ".github/ISSUE_TEMPLATE/legacy.md").write_bytes(
            "--- \nname: 옛날 버그\n---\n\n## 증상\n".encode("euc-kr")
        )
        found = find_templates(tmp)
        cases.append(("bad-encoding-template-skipped-not-crashed",
                      [Path(t["path"]).name for t in found], ["bug_report.md"]))

    with tempfile.TemporaryDirectory() as tmp:
        # A repo with no template directory or legacy file at all: empty, not a crash.
        cases.append(("no-template-dir-at-all", find_templates(tmp), []))

    with tempfile.TemporaryDirectory() as tmp:
        # TEMPLATE_DIRS priority: `.github/ISSUE_TEMPLATE` (checked first) wins over
        # `ISSUE_TEMPLATE` even though both exist — find_templates() breaks on first match.
        _write(tmp, ".github/ISSUE_TEMPLATE/bug.md", bug_md)
        _write(tmp, "ISSUE_TEMPLATE/other.md", bug_md)
        found = find_templates(tmp)
        cases.append(("template-dirs-priority-order",
                      [Path(t["path"]).parent.as_posix().replace(tmp, "") for t in found],
                      ["/.github/ISSUE_TEMPLATE"]))

    with tempfile.TemporaryDirectory() as tmp:
        # No TEMPLATE_DIRS present at all → falls back to a LEGACY_FILES single template.
        _write(tmp, ".github/ISSUE_TEMPLATE.md", bug_md)
        found = find_templates(tmp)
        cases.append(("legacy-file-fallback",
                      [Path(t["path"]).name for t in found], ["ISSUE_TEMPLATE.md"]))

    # cwd-independent discovery (#562's actual failure shape: a session sitting in a
    # subdirectory reported "no template" on a repo that has one) — repo_root() must resolve
    # to the real git toplevel from a nested cwd, not just wherever `start` happens to be.
    with tempfile.TemporaryDirectory() as tmp:
        real_tmp = str(Path(tmp).resolve())
        subprocess.run(["git", "init", "-q", real_tmp], check=True)
        nested = Path(real_tmp, "some", "nested", "dir")
        nested.mkdir(parents=True)
        got = repo_root(str(nested))
        cases.append(("repo-root-resolves-from-subdirectory", str(Path(got).resolve()), real_tmp))

    return cases


def self_test():
    cases = []
    cases.extend(_discovery_checks())
    md = """---
name: Bug
about: 버그 리포트
title: "fix: "
labels: bug
---

## 증상
## 환경 (선택)
"""
    meta, sec = parse_md(md)
    cases.append(("md-meta", (meta["title_prefix"], meta["labels"]), ("fix: ", ["bug"])))
    cases.append(
        ("md-sections", sec, [{"name": "증상", "optional": False},
                              {"name": "환경 (선택)", "optional": True}])
    )
    cases.append(("md-kind", _kind("bug_report", meta["name"], meta["about"]), "defect"))

    # GitHub's own English scaffold names + an `(optional)` marker: the case that used to
    # be unskippable because `(선택)` was the only marker the skill knew.
    en = "## Steps\n## Environment (optional)\n"
    cases.append(("en-optional", [s["optional"] for s in parse_md(en)[1]], [False, True]))
    cases.append(("en-kind", _kind("feature_request", "", ""), "proposal"))

    form = """name: Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: Thanks for reporting!
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us what you expected
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version
    validations:
      required: false
"""
    fmeta, fsec = parse_form(form)
    cases.append(("form-meta", (fmeta["title_prefix"], fmeta["labels"]),
                  ("[Bug]: ", ["bug", "triage"])))
    # `type: markdown` is presentation, never a section to assemble into.
    cases.append(
        ("form-sections", fsec, [{"name": "What happened?", "optional": False},
                                 {"name": "Version", "optional": True}])
    )
    cases.append(("form-kind", _kind("bug_report.yml", fmeta["name"], fmeta["about"]), "defect"))

    # A `dropdown`/`checkboxes` field's `attributes.options:` is itself a nested `- ` list,
    # deeper-indented than the body list's own item marker — it must not be misread as a new
    # sibling item, which would flush the field (losing `required`) before `validations:` is reached.
    form_options = """body:
  - type: dropdown
    id: priority
    attributes:
      label: Priority
      options:
        - Low
        - Medium
        - High
    validations:
      required: true
"""
    cases.append(
        ("form-nested-options", parse_form(form_options)[1],
         [{"name": "Priority", "optional": False}])
    )

    # checkboxes has no field-level `validations:` block at all — GitHub's real schema puts
    # `required:` per-option under `attributes.options[]` instead (a mandatory "I agree to the
    # Code of Conduct" checkbox is the canonical case). Any option required makes the field
    # required; a field with no required option stays optional.
    form_checkboxes = """body:
  - type: checkboxes
    id: coc
    attributes:
      label: Code of Conduct
      options:
        - label: "I agree to follow this project's Code of Conduct"
          required: true
  - type: checkboxes
    id: extra
    attributes:
      label: Nice to have
      options:
        - label: "Ping me for follow-up"
          required: false
"""
    cases.append(
        ("form-checkboxes-required", parse_form(form_checkboxes)[1],
         [{"name": "Code of Conduct", "optional": False},
          {"name": "Nice to have", "optional": True}])
    )

    # A block-style top-level `labels:` list (valid GitHub issue-form syntax, already
    # supported for .md via parse_md's `block_key`) must not be silently dropped for .yml.
    form_block_labels = """title: "[Bug]: "
labels:
  - bug
  - triage
body:
  - type: textarea
    id: what
    attributes:
      label: What happened?
    validations:
      required: true
"""
    cases.append(("form-block-style-labels", parse_form(form_block_labels)[0]["labels"],
                  ["bug", "triage"]))

    # A parenthetical that is not an optional marker must not read as optional.
    cases.append(("paren-not-optional", is_optional("환경 (Claude Code 버전)"), False))
    cases.append(("no-template", render([]), NO_TEMPLATE))

    failed = 0
    for name, got, want in cases:
        if got != want:
            failed += 1
            print(f"FAIL {name}\n  got:  {got}\n  want: {want}", file=sys.stderr)
    if failed:
        print(f"FAIL: {failed}/{len(cases)} issue-template self-test cases failed", file=sys.stderr)
        return 1
    print(f"OK: all {len(cases)} issue-template self-test cases passed")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--headings", metavar="PATH")
    ap.add_argument("--root", default=None, help="default: the git toplevel of the cwd")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.headings:
        try:
            _, sections = parse(args.headings)
        except (OSError, UnicodeDecodeError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        if not sections:
            print(
                f"ERROR: `{args.headings}`에서 섹션을 못 찾았어요 — 템플릿이 비었거나 "
                "이 스크립트가 못 읽는 모양이에요.",
                file=sys.stderr,
            )
            return 1
        for s in sections:
            print(f"## {s['name']}")
        return 0

    if args.list:
        templates = find_templates(args.root if args.root else repo_root())
        if args.json:
            print(json.dumps(templates, ensure_ascii=False, indent=2))
        else:
            print(render(templates))
        return 0 if templates else 1

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
