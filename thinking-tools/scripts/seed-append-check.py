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
"""

import json
import os
import re
import sys

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
# there — is the journaling shape.
STRUCTURAL_START = re.compile(r"^\s*(?:-\s+[\w-]+:|[A-Za-z_][\w-]*:)")


# ponytail: prefix check only — an append that leads with a new list item and trails a log
# line rides through. Structural YAML diffing is the upgrade if that shape ever shows up.
def is_structural_growth(added: str) -> bool:
    return bool(STRUCTURAL_START.match(added.lstrip("\n")))


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
    if not existing or not reads_as_seed(existing):
        return ""
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


def _self_test() -> int:
    seed = lambda _: SEED_HEAD  # noqa: E731 — every path reads as a Seed unless a case says otherwise
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
                "new_string": "constraints:\n  - id: c18\n    description: 역할 필터는 deny-by-default다.\n",
            }}, seed, False,
        ),
        (
            "new constraint carrying a provenance date (structural growth)",
            {"tool_name": "Edit", "tool_input": {
                "file_path": "/r/docs/specs/x.yaml",
                "old_string": "  - id: c1\n",
                "new_string": "  - id: c1\n  - id: c2\n    rationale: 매체는 GAS로 확정한다(2026-09-16 사용자 결정).\n",
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
    for name, payload, reader, want_deny in cases:
        got = bool(decide(payload, read_file=reader))
        if got != want_deny:
            failed += 1
            print(f"FAIL: {name} — expected deny={want_deny}, got deny={got}", file=sys.stderr)
    if failed:
        print(f"FAIL: {failed}/{len(cases)} seed-append-check case(s) failed", file=sys.stderr)
        return 1
    print(f"OK: all {len(cases) + len(spans)} seed-append-check self-test cases passed")
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
