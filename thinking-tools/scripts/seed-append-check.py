#!/usr/bin/env python3
"""build-spec Seed append guard — PreToolUse decider.

Reads a PreToolUse payload on stdin and prints a deny reason to stdout when the edit
APPENDS work-log prose to a build-spec Seed. Silence means allow: every unclear case
(unreadable file, missing field, unknown tool) falls through to allow, because a guard
that blocks what it cannot read gets turned off.

**Appending is the signal, not the date.** A Seed legitimately cites a decision date inside
a rationale it REPLACES ("2026-09-16 사용자 결정"). What rots the file is the edit that keeps
every prior word intact and hangs a new dated note off the end. Measured on a real Seed
(recruiting-dashboard.yaml: 999 lines, 18 commits, near-monotonic growth) whose constraint
rationales had turned into commit messages — "(2026-09-17 requirement-gap-reviewer 발견·수정)
첫 구현은 ... 빠뜨렸었다 ... 바로잡았고 ... 단위 테스트 4케이스로 확인".

So the test is two-part: the old text survives whole inside the new text (nothing replaced,
only added), AND the added part reads like a work log. A refine round adding a genuinely new
constraint passes both halves of the file untouched and carries no log vocabulary, so it is
allowed — spec growth is fine, spec journaling is not.

**The template is the key allowlist (#767).** The structural-growth exemption above looks at
the shape of the added text, never at its key names, so `status: in_progress` (top level) or
an indented `status: done` inside a constraint item rode through as "growth". Now an edit to
an existing Seed may introduce only key paths that templates/SEED_SPEC.yaml defines at that
position; keys the file already carried are never flagged, so old Seeds with custom keys keep
working. If the template cannot be read the key check is skipped (fail open).

**Ids are never deleted, duplicated or reused (seed-relations-graph/constraint-3).** Other Seeds'
`relations.refines` point at a parent's constraints[].id / success_criteria[].id, so an edit that
makes an id present before the edit vanish would silently orphan those edges. A dropped
requirement keeps its id and has its entry rewritten; a new one takes the next unused number.
Also denied: an edit that introduces a duplicate item id, and one that adds `constraint-N` /
`acceptance-N` while the Seed still carries the legacy `cN` / `acN` with that number (or vice
versa). Ids follow reference/identifiers.md; a legacy Seed stays protected as plain strings, and
its ids are renamed only by `scripts/seed-id-migrate.py <seed> --apply` - a hand rename shows up
here as a vanished id and is denied with that pointer. Same template-path exemption as the key check.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SEED_MARKERS = ("skill: build-spec", "generated_by: thinking-tools/build-spec")

# Vocabulary that only shows up when a session is recording what it did. Deliberately
# narrow: "진행 중" is out because a real Seed names a KPI tile "진행 중인 지원건", and
# bare "구현"/"확인" are out because specs describe implementation and verification as
# requirements. What is left is past-tense reporting and review provenance.
LOG_SIGNALS = re.compile(
    r"20\d\d-\d\d-\d\d"
    r"|(?:구현|배포|작업|수정|반영|검증|정정|재확인|확인|테스트)\s*(?:완료|했|됐|끝)"
    r"|이번 라운드|첫 구현|미구현|발견·수정|리뷰 발견|requirement-gap|code-review"
)


# A new list item or a new key is spec GROWTH — a refine round adding constraint c18, or a
# field the template defines. Those legitimately carry a provenance date ("확정한다(2026-09-16
# 사용자 결정)"), and denying them would make the guard fire on exactly the edit build-spec's
# refine mode is supposed to make. What is left — added prose that continues a value already
# there — is the journaling shape. Structural growth is exempt from the log-signal check only:
# foreign_keys() in decide() already guarantees its keys are template-defined, so this regex no
# longer has to judge key names.
STRUCTURAL_START = re.compile(r"^\s*(?:-\s+[\w-]+:|[A-Za-z_][\w-]*:)")


# ponytail: prefix check only — an append that leads with a new list item and trails a log
# line rides through. Structural YAML diffing is the upgrade if that shape ever shows up.
def is_structural_growth(added: str) -> bool:
    return bool(STRUCTURAL_START.match(added.lstrip("\n")))


_KEY_LINE = re.compile(r"^(\s*)(-\s+)?([A-Za-z_][\w-]*):(?:\s|$)")
_DASH_LINE = re.compile(r"^(\s*)-(?:\s|$)")
_INLINE_COMMENT = re.compile(r"(?:^|\s+)#.*$")


def _walk_keys(text: str):
    """Yield (key path, rest of the line after `key:`) for every real key of a YAML document.

    "[]" in a path = a list item. Read by indentation alone. Minimal on purpose (no PyYAML): it
    only has to tell "a key at this position" from "text inside a scalar", so block scalars and
    plain multi-line scalars are skipped.
    """
    stack: list[tuple[int, str]] = []
    scalar: tuple[int, bool] | None = None  # (key column, is block scalar)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue
        indent = len(line) - len(line.lstrip())
        is_item = _DASH_LINE.match(line) is not None
        if scalar is not None:
            col, block = scalar
            if indent > col and (block or not is_item):
                continue
            scalar = None
        m = _KEY_LINE.match(line)
        if is_item:
            while stack and (stack[-1][0] > indent or (stack[-1][0] == indent and stack[-1][1] == "[]")):
                stack.pop()
            stack.append((indent, "[]"))
        elif m:
            while stack and stack[-1][0] >= indent:
                stack.pop()
        if not m:
            continue
        col = len(m.group(1)) + len(m.group(2) or "")
        stack.append((col, m.group(3)))
        rest = line[m.end():]
        yield tuple(name for _, name in stack), rest
        value = _INLINE_COMMENT.sub("", rest).strip()
        if value:
            scalar = (col, value[0] in "|>")


def key_paths(text: str) -> set[tuple[str, ...]]:
    """Key paths of a YAML document ("[]" = a list item); see _walk_keys."""
    return {path for path, _ in _walk_keys(text)}


_ID_VALUE = re.compile(r"""^\s*["']?([\w-]+)""")
_ID_SECTIONS = ("constraints", "success_criteria")


def item_id_list(text: str) -> list[tuple[str, str]]:
    """(section, id) of every constraints[] / success_criteria[] item, in file order.

    Walks the same structure as key_paths, so an `id:` line inside a block scalar or a nested
    mapping/list under an item is not mistaken for an item id.
    """
    out: list[tuple[str, str]] = []
    for path, rest in _walk_keys(text):
        if len(path) == 3 and path[0] in _ID_SECTIONS and path[1:] == ("[]", "id"):
            m = _ID_VALUE.match(rest)
            if m:
                out.append((path[0], m.group(1)))
    return out


def item_ids(text: str) -> set[str]:
    """`id:` values of constraints[] and success_criteria[] items (the item's own id key only)."""
    return {i for _, i in item_id_list(text)}


def missing_ids(existing: str, result: str) -> list[str]:
    """Ids the existing Seed holds that the edited text no longer does."""
    return sorted(item_ids(existing) - item_ids(result))


# Same rule as seed-relations.py canonical_id (kept here so the hook imports nothing but stdlib):
# `c3` -> `constraint-3`, `ac2` -> `acceptance-2`; the number is kept.
_LEGACY = re.compile(r"^(c|ac)(\d+)$")
_LEGACY_KIND = {"c": "constraint", "ac": "acceptance"}


def canonical(item_id: str) -> str:
    m = _LEGACY.match(item_id)
    return f"{_LEGACY_KIND[m.group(1)]}-{m.group(2)}" if m else item_id


def new_duplicates(existing: str, result: str) -> list[str]:
    """Ids that occur more than once across constraints/success_criteria in the result and did not before."""
    def dups(text: str) -> set[str]:
        # One namespace across constraints and success_criteria, like seed-relations.py.
        seen: set[str] = set()
        out: set[str] = set()
        for _, i in item_id_list(text):
            if i in seen:
                out.add(i)
            seen.add(i)
        return out
    return sorted(dups(result) - dups(existing))


def new_reused_numbers(existing: str, result: str) -> list[str]:
    """Canonical ids the result carries in both the legacy and the new form (and did not before)."""
    def mixed(text: str) -> dict[str, set[str]]:
        groups: dict[str, set[str]] = {}
        for _, i in item_id_list(text):
            groups.setdefault(canonical(i), set()).add(i)
        return {c: ids for c, ids in groups.items() if len(ids) > 1}
    before = mixed(existing)
    return sorted(c for c in mixed(result) if c not in before)


# The template documents blindspots' item fields only in a comment (its default is `[]`).
_COMMENT_ONLY_PATHS = {("blindspots", "[]", "area"), ("blindspots", "[]", "question")}
_TEMPLATE = Path(__file__).resolve().parent.parent / "skills/build-spec/templates/SEED_SPEC.yaml"
_template_paths_cache: set[tuple[str, ...]] | None = None


def template_paths() -> set[tuple[str, ...]] | None:
    """Key paths a Seed may hold, or None when the template cannot be read (check skipped)."""
    global _template_paths_cache
    if _template_paths_cache is None:
        try:
            text = _TEMPLATE.read_text(encoding="utf-8")
        except OSError:
            return None
        _template_paths_cache = key_paths(text) | _COMMENT_ONLY_PATHS
    return _template_paths_cache


def result_text(tool: str, ti: dict, existing: str) -> str | None:
    """The file content after this edit, or None when it cannot be determined."""
    if tool == "Write":
        return ti.get("content") or ""
    if tool != "Edit":
        return None
    old, new = ti.get("old_string") or "", ti.get("new_string") or ""
    if not old or old not in existing:
        return None
    return existing.replace(old, new) if ti.get("replace_all") else existing.replace(old, new, 1)


def foreign_keys(existing: str, result: str) -> list[str]:
    """Dotted names of keys this edit introduces that the template does not define."""
    allowed = template_paths()
    if allowed is None:
        return []
    added = key_paths(result) - key_paths(existing) - allowed
    return sorted(".".join(p).replace(".[]", "[]") for p in added)


def is_template_path(path: str) -> bool:
    # Suffix, not `== _TEMPLATE`: the hook runs this script from the installed plugin cache while
    # the template being edited lives in a repo checkout, so the two absolute paths differ.
    return os.path.normpath(path).replace(os.sep, "/").endswith("skills/build-spec/templates/SEED_SPEC.yaml")


def is_seed_path(path: str) -> bool:
    # Suffix only. A `specs/` component is the convention, not the identity — next-goal's Input
    # contract never names a directory, only a Seed the session or an issue points at, so a Seed
    # at docs/seed-x.yaml is the same file with the same failure. reads_as_seed() below decides.
    return path.endswith((".yaml", ".yml"))


def reads_as_seed(text: str) -> bool:
    return any(m in text[:4000] for m in SEED_MARKERS)


def added_text(tool: str, ti: dict, existing: str) -> str:
    """The text this edit adds while preserving everything already there ('' = not an append)."""
    if tool == "Edit":
        old, new = ti.get("old_string") or "", ti.get("new_string") or ""
    elif tool == "Write":
        old, new = existing, ti.get("content") or ""
        old = old.rstrip()
    else:
        return ""
    if not old or old not in new or len(new) <= len(old):
        return ""
    # Align at the edge the edit actually grew from. `replace(old, "", 1)` drops the FIRST
    # occurrence, which is the wrong span when old repeats in new, and then both the
    # structural test and the signal scan read text this edit never added.
    if new.startswith(old):
        return new[len(old):]
    if new.endswith(old):
        return new[: -len(old)]
    return new.replace(old, "", 1)


def _id_number_reason(path: str, existing: str, result: str) -> str:
    """Deny reason for a duplicate id or a reused number the edit introduces, else ''."""
    dup = new_duplicates(existing, result)
    if dup:
        return (
            f"Seed에 같은 item id가 두 번 생기게 하려고 했어요 ({os.path.basename(path)}: {', '.join(dup)}). "
            "id는 constraints/success_criteria를 통틀어 하나뿐이어야 해요 — 새 요구사항은 아직 안 쓴 다음 번호를 쓰세요."
        )
    reused = new_reused_numbers(existing, result)
    if reused:
        return (
            f"이미 쓴 번호를 다른 형태로 다시 쓰려고 했어요 ({os.path.basename(path)}: {', '.join(reused)}). "
            "이 Seed에는 같은 번호의 옛 id(c<N>/ac<N>)와 새 id(constraint-<N>/acceptance-<N>)가 함께 있게 돼요 — "
            "번호는 재사용하지 말고 아직 안 쓴 다음 번호를 쓰세요. 옛 id는 `scripts/seed-id-migrate.py <seed> --apply`로 옮겨요."
        )
    return ""


def decide(payload: dict, read_file=None) -> str:
    """Return a deny reason, or '' to allow."""
    read_file = read_file or _read_file
    tool = payload.get("tool_name") or ""
    if tool not in ("Edit", "Write"):
        return ""
    ti = payload.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path or not is_seed_path(path):
        return ""
    if not os.path.isabs(path):
        path = os.path.join(payload.get("cwd") or "", path)
    existing = read_file(path)
    if not existing and tool == "Write" and not is_template_path(path):
        # New file: only the id-number checks apply (no baseline for vanish/keys/log).
        content = ti.get("content") or ""
        return _id_number_reason(path, "", content) if reads_as_seed(content) else ""
    if not existing or not reads_as_seed(existing):
        return ""
    result = result_text(tool, ti, existing)
    lost = missing_ids(existing, result) if result is not None and not is_template_path(path) else []
    if lost:
        after = item_ids(result)
        renamed = [i for i in lost if canonical(i) != i and canonical(i) in after]
        hint = ""
        if renamed:
            hint = (
                f" ({', '.join(f'{i}→{canonical(i)}' for i in renamed)}) 이름을 바꾸려던 거라면 손으로 고치지 말고 "
                "`scripts/seed-id-migrate.py <seed> --apply`로만 바꾸세요 — 그 스크립트가 이 Seed와 자식 Seed의 "
                "relations.refines를 함께 옮겨요."
            )
        return (
            f"Seed의 id를 지우려고 했어요 ({os.path.basename(path)}: {', '.join(lost)}). "
            "item id는 다른 Seed의 relations.refines가 가리키니까 지우거나 바꾸면 안 돼요 — "
            "빠진 요구사항도 id는 두고 그 항목의 내용만 고쳐 쓰고, 새 요구사항은 아직 안 쓴 다음 번호를 쓰세요."
            + hint
        )
    if result is not None and not is_template_path(path):
        reason = _id_number_reason(path, existing, result)
        if reason:
            return reason
    # The template defines the allowlist, so widening it must not be judged against itself.
    keys = foreign_keys(existing, result) if result is not None and not is_template_path(path) else []
    if keys:
        return (
            f"Seed 템플릿에 없는 키를 추가하려고 했어요 ({os.path.basename(path)}: {', '.join(keys)}). "
            "Seed는 templates/SEED_SPEC.yaml이 정의한 필드만 가져요 — 진행·완료 상태는 Seed가 아니라 "
            "이슈에 남기고, 새 필드가 정말 필요하면 템플릿부터 넓히세요."
        )
    added = added_text(tool, ti, existing)
    if not added or is_structural_growth(added) or not LOG_SIGNALS.search(added):
        return ""
    snippet = " ".join(added.split())[:120]
    return (
        f"Seed 스펙에 작업 기록을 덧붙이려고 했어요 ({os.path.basename(path)}). "
        "Seed는 기능 명세지 작업 로그가 아니에요 — 사실이 틀렸으면 그 필드의 값을 교체하고, "
        "진행·완료·리뷰 발견 기록은 이 레포가 이미 쓰는 이슈나 대장 문서에 남기세요. "
        f'덧붙이려던 내용: "{snippet}"'
    )


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


SEED_HEAD = "skill: build-spec\nspec_version: 1\nconstraints:\n"
SEED_ITEM = SEED_HEAD + "  - id: constraint-1\n    type: technical\n    description: 기존 제약.\n    hard: true\n    rationale: 기존 근거.\n"
SEED_ITEM_BODY = SEED_ITEM[len(SEED_HEAD):]
SEED_COMPACT = SEED_HEAD + "- id: constraint-1\n  type: technical\n  description: 기존 제약.\n  hard: true\n  rationale: 기존 근거.\n"
SEED_LEGACY = SEED_ITEM.replace("constraint-1", "c1")
SEED_LEGACY_AC = SEED_LEGACY + "success_criteria:\n  - id: ac1\n    description: 관찰 가능한 결과.\n"
SEED_CUSTOM = SEED_ITEM + "custom_note: x\n"
SEED_BLOCK = (
    SEED_HEAD + "  - id: constraint-1\n    type: technical\n    description: Config is required.\n    hard: true\n"
    "    rationale: |\n      Example API config:\n      id: customer_id\n"
)


def _self_test() -> int:
    seed = lambda _: SEED_HEAD  # noqa: E731 — every path reads as a Seed unless a case says otherwise
    item = lambda _: SEED_ITEM  # noqa: E731 — a Seed that already holds constraint constraint-1
    cases = [
        (
            "dated note appended to a rationale",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "노출 실패 모드가 과다 노출이 되면 안 된다.",
                "new_string": "노출 실패 모드가 과다 노출이 되면 안 된다. (2026-09-17 구현 중 확인) HM 행은 이번 라운드 구현하지 않는다.",
            }}, seed, True,
        ),
        (
            "rationale REPLACED, date preserved inside it",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "매체는 GAS 웹앱으로 확정한다 (2026-09-14 결정).",
                "new_string": "매체는 Apps Script 웹앱으로 확정한다 (2026-09-16 사용자 결정).",
            }}, seed, False,
        ),
        (
            "new constraint appended, no work-log vocabulary",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "constraints:\n",
                "new_string": "constraints:\n  - id: constraint-18\n    description: 역할 필터는 deny-by-default다.\n",
            }}, seed, False,
        ),
        (
            "new constraint carrying a provenance date (structural growth)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  - id: constraint-1\n",
                "new_string": "  - id: constraint-1\n  - id: constraint-2\n    rationale: 매체는 GAS로 확정한다(2026-09-16 사용자 결정).\n",
            }}, seed, False,
        ),
        (
            "CHANGELOG header comment prepended",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "skill: build-spec",
                "new_string": "skill: build-spec\n# 6.0.0 (2026-09-17) — V3/V4 라운드, 구현 완료",
            }}, seed, True,
        ),
        (
            "yaml that is not a Seed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/ci/pipeline.yaml",
                "old_string": "jobs:",
                "new_string": "jobs: # 2026-09-17 수정 완료",
            }}, lambda _: "jobs:\n  build:\n", False,
        ),
        (
            "a Seed kept outside specs/ is still guarded",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/seed-x.yaml",
                "old_string": "a",
                "new_string": "a (2026-09-17 반영 완료)",
            }}, seed, True,
        ),
        (
            "non-yaml file with Seed-looking content",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.md",
                "old_string": "a",
                "new_string": "a (2026-09-17 반영 완료)",
            }}, seed, False,
        ),
        (
            "Write that appends a work log to an existing Seed",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/specs/x.yaml",
                "content": SEED_HEAD + "# 2026-09-18 V4 화면 구현 완료\n",
            }}, seed, True,
        ),
        (
            "deletion, not an append",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "기존 문장 (2026-09-17 정정했다)",
                "new_string": "기존 문장",
            }}, seed, False,
        ),
        (
            "unreadable file falls open",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "a",
                "new_string": "a (2026-09-17 완료했다)",
            }}, lambda _: "", False,
        ),
        (
            "unrelated tool",
            {"tool_name": "Bash", "tool_input": {"command": "echo hi"}}, seed, False,
        ),
        # --- template key allowlist (#767) ---
        (
            "top-level status: added (the #767 repro shape)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "skill: build-spec\nspec_version: 1",
                "new_string": "skill: build-spec\nspec_version: 1\nstatus: in_progress",
            }}, item, True,
        ),
        (
            "indented status: inside a constraint item",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    hard: true\n",
                "new_string": "    hard: true\n    status: done\n",
            }}, item, True,
        ),
        (
            "Write that rewrites the Seed adding a top-level status:",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "content": SEED_ITEM + "status: in_progress\n",
            }}, item, True,
        ),
        (
            "relations: block with the template's shape is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nrelations:\n  parent: docs/specs/p.yaml\n"
                              "  refines: [constraint-1]\n  depends_on: []\n  children: []\n",
            }}, item, False,
        ),
        (
            "relations.status is still a foreign key",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nrelations:\n  parent: null\n  status: done\n",
            }}, item, True,
        ),
        (
            "issues: block with source/tracking is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nissues:\n  source: \"#792\"\n  tracking: [\"#800\"]\n",
            }}, item, False,
        ),
        (
            "issues.status is still a foreign key",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nissues:\n  source: null\n  status: done\n",
            }}, item, True,
        ),
        (
            "relations.link_reason is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nrelations:\n  parent: docs/specs/p.yaml\n"
                              "  refines: [constraint-1]\n  link_reason: 부모가 비워 둔 인증 경로를 정한다.\n",
            }}, item, False,
        ),
        # --- id invariance (seed-relations-graph/constraint-3) ---
        (
            "deleting the constraint-1 item is denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": SEED_ITEM_BODY,
                "new_string": "",
            }}, item, True,
        ),
        (
            "renumbering constraint-1 to constraint-2 is denied (constraint-1 vanished)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  - id: constraint-1\n",
                "new_string": "  - id: constraint-2\n",
            }}, item, True,
        ),
        (
            "Write that drops a success_criteria id is denied",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "content": SEED_ITEM,
            }}, lambda _: SEED_ITEM + "success_criteria:\n  - id: acceptance-1\n    description: 관찰 가능한 결과.\n", True,
        ),
        (
            "rewriting constraint-1's description while keeping the id is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "description: 기존 제약.",
                "new_string": "description: 고쳐 쓴 제약.",
            }}, item, False,
        ),
        (
            "adding a new constraint-2 while keeping constraint-1 is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: constraint-2\n    description: 새 제약.\n",
            }}, item, False,
        ),
        (
            "the same constraint-1 deletion on the template path is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml",
                "old_string": "  - id: constraint-1\n    type: technical|resource|legal|temporal|other\n",
                "new_string": "",
            }}, lambda _: _TEMPLATE.read_text(encoding="utf-8"), False,
        ),
        (
            "adding a key to the Seed template itself is allowed (path-scoped exemption)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml",
                "old_string": "blindspots: []",
                "new_string": "status: draft\n\nblindspots: []",
            }}, lambda _: _TEMPLATE.read_text(encoding="utf-8"), False,
        ),
        (
            "same edit on a non-template Seed path still denies",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "blindspots: []",
                "new_string": "status: draft\n\nblindspots: []",
            }}, lambda _: _TEMPLATE.read_text(encoding="utf-8"), True,
        ),
        (
            "new constraint-2 item with every template field",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: constraint-2\n    type: legal\n    description: 새 제약.\n"
                              "    hard: false\n    rationale: 새 근거.\n",
            }}, item, False,
        ),
        (
            "template field the file lacks: blindspots with an item",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nblindspots:\n  - area: x\n    question: y\n",
            }}, item, False,
        ),
        (
            "template field the file lacks: refine_generation",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "skill: build-spec\nspec_version: 1",
                "new_string": "skill: build-spec\nspec_version: 1\nrefine_generation: 1",
            }}, item, False,
        ),
        (
            "compact sequence (dash at the parent column) gains a new item",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  rationale: 기존 근거.\n",
                "new_string": "  rationale: 기존 근거.\n- id: constraint-2\n  type: other\n  description: 새 제약.\n"
                              "  hard: true\n  rationale: 새 근거.\n",
            }}, lambda _: SEED_COMPACT, False,
        ),
        (
            "existing non-template key keeps working when its value changes",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "custom_note: x",
                "new_string": "custom_note: y",
            }}, lambda _: SEED_CUSTOM, False,
        ),
        # --- id lookalikes inside scalars are not item ids ---
        (
            "editing an `id:` line inside a block scalar is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "      id: customer_id\n",
                "new_string": "      identifier: customer_id\n",
            }}, lambda _: SEED_BLOCK, False,
        ),
        (
            "renumbering the real constraint-1 of a Seed with a block scalar is still denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  - id: constraint-1\n",
                "new_string": "  - id: constraint-2\n",
            }}, lambda _: SEED_BLOCK, True,
        ),
        (
            "deleting the whole constraint-1 item (block scalar and all) is still denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": SEED_BLOCK[len(SEED_HEAD):],
                "new_string": "",
            }}, lambda _: SEED_BLOCK, True,
        ),
        # --- legacy Seeds stay protected as plain strings ---
        (
            "legacy: deleting c1 is denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": SEED_LEGACY[len(SEED_HEAD):],
                "new_string": "",
            }}, lambda _: SEED_LEGACY, True,
        ),
        (
            "legacy: rewriting c1's description is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "description: 기존 제약.",
                "new_string": "description: 고쳐 쓴 제약.",
            }}, lambda _: SEED_LEGACY, False,
        ),
        (
            "legacy: hand rename c1 -> constraint-1 is denied (no edit-path exemption)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  - id: c1\n",
                "new_string": "  - id: constraint-1\n",
            }}, lambda _: SEED_LEGACY, True,
        ),
        (
            "legacy: adding the next number c2 is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: c2\n    description: 새 제약.\n",
            }}, lambda _: SEED_LEGACY, False,
        ),
        (
            "legacy: Write that drops ac1 is denied",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml", "content": SEED_LEGACY,
            }}, lambda _: SEED_LEGACY_AC, True,
        ),
        # --- duplicate and reused numbers ---
        (
            "new: adding a second constraint-1 is denied (duplicate)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: constraint-1\n    description: 중복.\n",
            }}, item, True,
        ),
        (
            "legacy: adding a second c1 is denied (duplicate)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: c1\n    description: 중복.\n",
            }}, lambda _: SEED_LEGACY, True,
        ),
        (
            "same id in constraints and success_criteria is a duplicate (one namespace)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\nsuccess_criteria:\n  - id: constraint-1\n    description: 다른 목록.\n",
            }}, item, True,
        ),
        (
            "legacy Seed gains constraint-1 beside c1 (reused number) is denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: constraint-1\n    description: 번호 재사용.\n",
            }}, lambda _: SEED_LEGACY, True,
        ),
        (
            "new Seed gains c1 beside constraint-1 (reused number) is denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: c1\n    description: 번호 재사용.\n",
            }}, item, True,
        ),
        (
            "legacy Seed gains acceptance-1 beside ac1 (reused number) is denied",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    description: 관찰 가능한 결과.\n",
                "new_string": "    description: 관찰 가능한 결과.\n  - id: acceptance-1\n    description: 번호 재사용.\n",
            }}, lambda _: SEED_LEGACY_AC, True,
        ),
        (
            "legacy Seed gains constraint-2 (next unused number, new form) is allowed",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "    rationale: 기존 근거.\n",
                "new_string": "    rationale: 기존 근거.\n  - id: constraint-2\n    description: 새 제약.\n",
            }}, lambda _: SEED_LEGACY, False,
        ),
        # --- Write that creates a new Seed: id-number checks only ---
        (
            "new Seed with duplicate ids is denied",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/new.yaml",
                "content": SEED_ITEM + "  - id: constraint-1\n    description: 중복.\n",
            }}, lambda _: "", True,
        ),
        (
            "new Seed with c1 beside constraint-1 is denied",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/new.yaml",
                "content": SEED_ITEM + "  - id: c1\n    description: 재사용.\n",
            }}, lambda _: "", True,
        ),
        (
            "new clean Seed is allowed",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/new.yaml", "content": SEED_ITEM,
            }}, lambda _: "", False,
        ),
        (
            "new Seed with a custom key and a dated note is not judged (id checks only)",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/docs/specs/new.yaml",
                "content": SEED_ITEM + "status: x\n# 2026-09-18 구현 완료\n",
            }}, lambda _: "", False,
        ),
        (
            "new file that is not a Seed is ignored",
            {"tool_name": "Write", "tool_input": {
                "file_path": "/r/ci/p.yaml", "content": "jobs:\n  - id: c1\n  - id: c1\n",
            }}, lambda _: "", False,
        ),
    ]
    failed = 0
    # Span alignment (no verdict flips here — both spans carry the same words — so the span
    # itself is what gets pinned): a repeated old_string must not make `added` a middle slice.
    spans = [
        ("prepend", {"old_string": "근거 A", "new_string": "머리말 근거 A"}, "머리말 "),
        ("append", {"old_string": "근거 A", "new_string": "근거 A 꼬리말"}, " 꼬리말"),
        ("repeat, aligned at the tail", {"old_string": "근거 A", "new_string": "머리 근거 A 근거 A"}, "머리 근거 A "),
    ]
    for name, ti, want in spans:
        got = added_text("Edit", ti, "")
        if got != want:
            failed += 1
            print(f"FAIL: span {name} — expected [{want}], got [{got}]", file=sys.stderr)
    # key_paths pinned directly: scalar bodies must not read as keys, and both list layouts
    # (indented and compact) must land on the same path.
    key_checks = [
        ("block scalar body is not a key",
         "goal:\n  statement: >-\n    long text\n    next-goal: foo\n  clarity_score: 1\n",
         {("goal",), ("goal", "statement"), ("goal", "clarity_score")}),
        ("plain multi-line scalar continuation is not a key",
         "context:\n  backlog_scan: first line\n    next-goal: foo\n  dependencies: []\n",
         {("context",), ("context", "backlog_scan"), ("context", "dependencies")}),
        ("compact sequence path",
         "constraints:\n- id: constraint-1\n  hard: true\n- id: constraint-2\nnext: 1\n",
         {("constraints",), ("constraints", "[]", "id"), ("constraints", "[]", "hard"), ("next",)}),
        ("indented sequence path",
         "constraints:\n  - id: constraint-1\n    hard: true\n",
         {("constraints",), ("constraints", "[]", "id"), ("constraints", "[]", "hard")}),
    ]
    for name, text, want in key_checks:
        got = key_paths(text)
        if got != want:
            failed += 1
            print(f"FAIL: key_paths {name} — expected {sorted(want)}, got {sorted(got)}", file=sys.stderr)
    id_checks = [
        ("real item ids", "constraints:\n  - id: constraint-1\n  - id: constraint-2\nsuccess_criteria:\n  - id: acceptance-1\n", {"constraint-1", "constraint-2", "acceptance-1"}),
        ("literal |- scalar body", "constraints:\n  - id: constraint-1\n    rationale: |-\n      id: x1\n", {"constraint-1"}),
        ("folded > scalar body", "constraints:\n  - id: constraint-1\n    rationale: >\n      id: x1\n      - id: x2\n", {"constraint-1"}),
        ("nested mapping under an item", "constraints:\n  - id: constraint-1\n    meta:\n      id: x1\n", {"constraint-1"}),
        ("nested list under an item", "constraints:\n  - id: constraint-1\n    refs:\n      - id: x1\n", {"constraint-1"}),
        ("legacy ids read as plain strings", "constraints:\n  - id: c1\nsuccess_criteria:\n  - id: ac1\n", {"c1", "ac1"}),
        ("quoted ids", "constraints:\n  - id: \"constraint-1\"\n  - id: 'constraint-2'\n", {"constraint-1", "constraint-2"}),
        ("real id after a block scalar ends", "constraints:\n  - id: constraint-1\n    rationale: |\n      id: x1\n  - id: constraint-2\n", {"constraint-1", "constraint-2"}),
        ("id key after a block scalar dedent in the same item", "constraints:\n  - rationale: |\n      id: x1\n    id: constraint-1\n", {"constraint-1"}),
        ("compact sequence", "constraints:\n- id: constraint-1\n  rationale: |\n    id: x1\n- id: constraint-2\n", {"constraint-1", "constraint-2"}),
        ("other top-level keys are ignored", "constraints:\n  - id: constraint-1\nblindspots:\n  - id: b1\ncontext:\n  id: z\n", {"constraint-1"}),
    ]
    for name, text, want in id_checks:
        got = item_ids(text)
        if got != want:
            failed += 1
            print(f"FAIL: item_ids {name} — expected {sorted(want)}, got {sorted(got)}", file=sys.stderr)
    foreign_checks = [
        ("names the offending paths", SEED_ITEM,
         SEED_ITEM.replace("    hard: true\n", "    hard: true\n    status: done\n") + "status: x\n",
         ["constraints[].status", "status"]),
        ("existing custom key is never flagged", SEED_CUSTOM, SEED_CUSTOM.replace("x", "y"), []),
    ]
    for name, before, after, want in foreign_checks:
        got = foreign_keys(before, after)
        if got != want:
            failed += 1
            print(f"FAIL: foreign_keys {name} — expected {want}, got {got}", file=sys.stderr)
    for name, payload, reader, want_deny in cases:
        got = bool(decide(payload, read_file=reader))
        if got != want_deny:
            failed += 1
            print(f"FAIL: {name} — expected deny={want_deny}, got deny={got}", file=sys.stderr)
    migrate_hint = "seed-id-migrate.py <seed> --apply"
    reason_checks = [
        ("hand rename carries the migration pointer", {"tool_name": "Edit", "tool_input": {
            "file_path": "/r/docs/specs/x.yaml", "old_string": "  - id: c1\n",
            "new_string": "  - id: constraint-1\n"}}, SEED_LEGACY, migrate_hint, True),
        ("a plain deletion carries no rename hint", {"tool_name": "Edit", "tool_input": {
            "file_path": "/r/docs/specs/x.yaml", "old_string": SEED_LEGACY[len(SEED_HEAD):],
            "new_string": ""}}, SEED_LEGACY, migrate_hint, False),
        ("reused number points at the migration script", {"tool_name": "Edit", "tool_input": {
            "file_path": "/r/docs/specs/x.yaml", "old_string": "    rationale: 기존 근거.\n",
            "new_string": "    rationale: 기존 근거.\n  - id: constraint-1\n    description: x.\n"}},
         SEED_LEGACY, "constraint-1", True),
    ]
    for name, payload, text, needle, want in reason_checks:
        got = needle in decide(payload, read_file=lambda _, t=text: t)
        if got != want:
            failed += 1
            print(f"FAIL: reason {name}", file=sys.stderr)
    total = len(reason_checks) + len(cases) + len(spans) + len(key_checks) + len(id_checks) + len(foreign_checks)
    if failed:
        print(f"FAIL: {failed}/{total} seed-append-check case(s) failed", file=sys.stderr)
        return 1
    print(f"OK: all {total} seed-append-check self-test cases passed")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    reason = decide(payload)
    if reason:
        print(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
