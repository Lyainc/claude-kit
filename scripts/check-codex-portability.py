#!/usr/bin/env python3
"""Check the Codex manifests and the 19-skill portability contract."""
import argparse
import json
from pathlib import Path

PLUGINS = {
    "thinking-tools": {
        "adversarial-review", "build-spec", "diverse-sampling", "doc-concretize",
        "doc-polish", "expert-panel", "issue-raise", "next-goal", "unknown-discovery",
    },
    "obsidian-vault-manager": {"audit", "base"},
    "vault-bridge": {"vault-commit", "vault-link", "vault-manifest-refresh", "vault-save", "wiki"},
    "feedback-loop": {"add-policy", "distill", "retro"},
}
UNSUPPORTED = set()
PORTABLE_MARKER = "## Codex Portability"
UNSUPPORTED_MARKER = "## Codex Availability"


# Four identical copies can still all regress to the pre-#827 chat-only contract.
QUESTION_RULES = {
    "native preference": (
        "use the available Codex native user-input tool before plain chat",
    ),
    "asynchronous reply gate": (
        "request_user_input_async", "only queues the question",
        "pending until the actual user reply arrives",
        "continue only independent work meanwhile",
    ),
    "mode and purpose restrictions": (
        "Otherwise use `request_user_input` only when available and permitted",
        "current-mode and purpose restrictions",
        "never invent a tool or switch modes to enable it",
    ),
    "independent choices": (
        "If multi-select or the number of options is unsupported",
        "use separate short questions or a free-text question accepting item IDs",
        "never silently turn independent keep/dismiss choices into a single-choice decision",
        "or drop choices to fit a limit",
    ),
    "prior answers and non-answers": (
        "Reuse explicit prior answers and approvals",
        "Tool acceptance, preselected options", "elapsed time are not user answers or approval",
        "missing/empty replies",
        "a skip is never an answer or approval and never advances a gate",
    ),
    "unavailable-tool fallback": (
        "If no native tool is usable", "normal user turn",
        "wait for the actual reply", "required unanswered questions pending",
        "never claim the interview completed",
    ),
}

# feedback-loop's individual overrides are covered by its plugin-local regression test.
# Each entry: (section start marker, section end marker or None, required phrases).
QUESTION_OVERRIDES = {
    "thinking-tools/skills/issue-raise/SKILL.md": (
        PORTABLE_MARKER, "\n## ",
        ("approval gate before `gh issue create`; use its native question path",),
    ),
    "vault-bridge/skills/vault-commit/SKILL.md": (
        "**Option C", "**Option D",
        (
            "Codex: ask a free-text question per [the portability contract](../../reference/codex-portability.md)",
            "An empty or missing reply keeps the commit pending: no `git commit`, no auto-generated message",
            "Claude Code: do NOT call AskUserQuestion here",
            "on Claude Code only, an empty reply falls back to the auto-generated message",
            'Never run `git commit -m ""`',
        ),
    ),
}

# Safety is independent of abbreviation; rules must be present in their owning section.
NEXT_GOAL_SECTIONS = {
    "skill": "## Phase 2 — Condition",
    "safety": "## Source safety",
    "abbreviation": "## Abbreviation",
}
NEXT_GOAL_CONDITION_RULES = {
    "source-less fallback": ("skill", (
        "source-less `session`/`backlog`: full problem, state, resume point, files and criteria",
        "Never create a source just for brevity",
    )),
    "versioned source pointers": ("skill", (
        "Seed path+committed full SHA, or issue repository+number+observed `updatedAt`",
        "unverifiable pins use full text",
    )),
    "source safety independent of abbreviation": ("skill", (
        "Source safety (all lengths)",
        "current metadata-first eligibility and version checks",
        "changed/unavailable sources hold application pending confirmation",
        "Surface selected criteria and baseline changes",
        "Pins never authorize historical/excluded requirements",
    )),
    "inline evaluator contract": ("skill", (
        "all caller checks/options/scoring caveats",
        "a verified check/exit 0; unknown checks stay unknown",
        "independent review/base/round cap",
        "protections, Git permissions, unresolved facts, turn/time cap",
        "any unmet item means incomplete",
    )),
    "optional lossless abbreviation": ("abbreviation", (
        "Use a pointer only when it is shorter without losing meaning",
        "Preserve **all** caller-mandated checks, not one representative check",
        "scoring caveats and cost/publication flags are not expendable background",
        "Do not add commit/push/PR authority because work is proposed",
    )),
    "independent bounded review": ("skill", (
        "one independent requirement-gap review of the explicit diff/base and requirements",
        "Cap rounds separately from turns/time across tools and replacement agents",
        "Infrastructure failure consumes the attempt", "never retry elsewhere",
    )),
    "stop remains incomplete": ("skill", (
        "reaching it means stop with unmet conditions and resume point, never completion",
    )),
    "metadata and source comparison before application": ("safety", (
        "Apply this whether the condition is full or abbreviated",
        "`seed-relations.py metadata <path> --json` before reading any requirement body",
        "apply current lifecycle, eligibility, withdrawals and parent-impact gates",
        "Compare the current Seed with the pinned tree",
        "retrieve the issue's current body/state/`updatedAt` from the named repository",
        "If the source changed, closed, became unavailable or ineligible, hold requirement application pending user confirmation",
    )),
    "criteria and progress visible after gates": ("safety", (
        "After these gates pass, print selected criteria verbatim",
        "`seed-relations.py read <path> --json` or the verified issue body",
        "`git log <baseline>..HEAD` and relevant working-tree changes",
    )),
}


def check_next_goal_condition(skill: str, reference: str) -> list[str]:
    sections = {
        name: (skill if name == "skill" else reference).partition(heading)[2].split("\n## ", 1)[0]
        for name, heading in NEXT_GOAL_SECTIONS.items()
    }
    normalized = {source: " ".join(text.split()) for source, text in sections.items()}
    return [
        f"thinking-tools/next-goal: missing condition rule: {label}"
        for label, (source, phrases) in NEXT_GOAL_CONDITION_RULES.items()
        if any(phrase not in normalized[source] for phrase in phrases)
    ]


def check_question_override(path: str, text: str) -> list[str]:
    start, end, phrases = QUESTION_OVERRIDES[path]
    normalized = " ".join(text.split())
    begin = normalized.find(start)
    if begin < 0:
        return [f"{path}: missing override section: {start}"]
    rest = normalized[begin + len(start):]
    stop = rest.find(end.strip()) if end else -1
    section = rest if stop < 0 else rest[:stop]
    return [
        f"{path}: missing question override: {phrase}"
        for phrase in phrases if phrase not in section
    ]


def check_question_contract(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [
        f"missing question rule: {label}"
        for label, phrases in QUESTION_RULES.items()
        if any(phrase not in normalized for phrase in phrases)
    ]


def question_self_test() -> int:
    lines = {label: " ".join(phrases) for label, phrases in QUESTION_RULES.items()}
    fixture = "\n".join(lines.values())
    cases = [("complete question contract passes", not check_question_contract(fixture))]
    for label, line in lines.items():
        cases.append((f"loss of {label} fails", bool(check_question_contract(fixture.replace(line, "")))))
    cases.append(("legacy chat-only contract fails", bool(check_question_contract(
        "For AskUserQuestion, ask a normal user-facing question and wait for the answer."))))
    cases.append(("weakened async gate fails", bool(check_question_contract(fixture.replace(
        "pending until the actual user reply arrives", "complete once submitted")))))
    cases.append(("option-count adaptation loss fails", bool(check_question_contract(fixture.replace(
        "or the number of options ", "")))))
    cases.append(("line wrapping preserves the contract", not check_question_contract(
        fixture.replace(" ", "\n"))))
    overrides = {
        path: f"intro\n{start}\n" + "\n".join(phrases) + (f"\n{end.strip()}\ntail" if end else "")
        for path, (start, end, phrases) in QUESTION_OVERRIDES.items()
    }
    cases.append(("complete individual question overrides pass", not any(
        check_question_override(path, text) for path, text in overrides.items())))
    for path, (start, end, phrases) in QUESTION_OVERRIDES.items():
        for phrase in phrases:
            cases.append((f"loss of {path}: {phrase} fails", bool(
                check_question_override(path, overrides[path].replace(phrase, "")))))
        stray = f"{start}\n{end.strip()}\n" + "\n".join(phrases)
        cases.append((f"{path}: phrases outside the section fail", bool(
            check_question_override(path, stray))))
    for phrase in (
        "continue only independent work meanwhile", "missing/empty replies",
        "or drop choices to fit a limit",
    ):
        cases.append((f"loss of '{phrase}' fails", bool(check_question_contract(
            fixture.replace(phrase, "")))))
    condition_lines = {label: " ".join(phrases) for label, (_, phrases) in NEXT_GOAL_CONDITION_RULES.items()}
    condition = {"skill": "", "reference": ""}
    for source, heading in NEXT_GOAL_SECTIONS.items():
        condition["skill" if source == "skill" else "reference"] += heading + "\n" + "\n".join(
            condition_lines[label] for label, (owner, _) in NEXT_GOAL_CONDITION_RULES.items() if owner == source
        ) + "\n"
    cases.append(("complete next-goal condition passes", not check_next_goal_condition(**condition)))
    for label, (source, _) in NEXT_GOAL_CONDITION_RULES.items():
        owner = "skill" if source == "skill" else "reference"
        changed = {**condition, owner: condition[owner].replace(condition_lines[label], "")}
        cases.append((f"next-goal loss of {label} fails", bool(check_next_goal_condition(**changed))))
    for source, before, after in (
        ("skill", "full problem, state, resume point, files and criteria", "short pointer"),
        ("skill", "committed full SHA", "latest version"),
        ("skill", "observed `updatedAt`", "read time"),
        ("skill", "any unmet item means incomplete", "unmet items may still complete"),
        ("skill", "Cap rounds separately from turns/time", "Cap turns only"),
        ("reference", "before reading any requirement body", "after reading the body"),
        ("reference", "hold requirement application pending user confirmation", "apply the latest scope"),
        ("reference", "After these gates pass, print selected criteria verbatim", "Record a file name"),
    ):
        changed = {**condition, source: condition[source].replace(before, after)}
        cases.append((f"next-goal weakened '{before}' fails", bool(check_next_goal_condition(**changed))))
    wrapped = {source: "\n".join(line if line.startswith("## ") else line.replace(" ", "\n")
                                        for line in text.splitlines())
               for source, text in condition.items()}
    cases.append(("next-goal line wrapping preserves the condition", not check_next_goal_condition(**wrapped)))
    outside = {source: text.replace("\n", "\n## Other\n", 1) for source, text in condition.items()}
    cases.append(("next-goal phrases outside their sections fail", bool(check_next_goal_condition(**outside))))
    crossed = {**condition, "reference": condition["reference"].replace("## Source safety", "## Abbreviation", 1)}
    cases.append(("abbreviation cannot supply the independent source safety gate", bool(check_next_goal_condition(**crossed))))
    for label, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    if not all(ok for _, ok in cases):
        return 1
    print(f"OK: all {len(cases)} Codex native-question self-test cases passed")
    return 0


def check(root: Path) -> list[str]:
    errors = []
    expected = {(plugin, skill) for plugin, skills in PLUGINS.items() for skill in skills}
    marketplace_path = root / ".agents/plugins/marketplace.json"
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Codex marketplace is unreadable ({exc})")
    else:
        marketplace_contract = {
            entry.get("name"): {
                "source": entry.get("source"),
                "policy": entry.get("policy"),
                "category": entry.get("category"),
            }
            for entry in marketplace.get("plugins", [])
        }
        expected_marketplace = {
            plugin: {
                "source": {"source": "local", "path": f"./{plugin}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
            for plugin in PLUGINS
        }
        if marketplace_contract != expected_marketplace:
            errors.append("Codex marketplace must expose the four official plugin contracts")
    discovered = {
        (plugin, path.parent.name)
        for plugin in PLUGINS
        for path in (root / plugin / "skills").glob("*/SKILL.md")
    }
    if discovered != expected:
        missing = sorted(expected - discovered)
        extra = sorted(discovered - expected)
        if missing:
            errors.append(f"unclassified skills missing from disk: {missing}")
        if extra:
            errors.append(f"unclassified skills missing from the inventory: {extra}")
    reference = None
    visited_overrides = set()
    for plugin, skills in PLUGINS.items():
        manifest_path = root / plugin / ".codex-plugin" / "plugin.json"
        claude_path = root / plugin / ".claude-plugin" / "plugin.json"
        contract_path = root / plugin / "reference" / "codex-portability.md"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            claude = json.loads(claude_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{plugin}: unreadable manifest ({exc})")
            continue
        if manifest.get("name") != plugin or manifest.get("name") != claude.get("name"):
            errors.append(f"{plugin}: Codex name is not lockstep")
        if manifest.get("version") != claude.get("version"):
            errors.append(f"{plugin}: Codex version is not lockstep")
        if manifest.get("skills") != "./skills/":
            errors.append(f"{plugin}: Codex skills path must be ./skills/")
        try:
            contract = contract_path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"{plugin}: missing Codex portability contract")
            continue
        errors.extend(f"{plugin}: {error}" for error in check_question_contract(contract))
        if reference is None:
            reference = contract
        elif contract != reference:
            errors.append(f"{plugin}: portability contract differs from the common contract")
        for skill in skills:
            path = root / plugin / "skills" / skill / "SKILL.md"
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(f"{plugin}/{skill}: missing SKILL.md")
                continue
            key = (plugin, skill)
            if key in UNSUPPORTED:
                if UNSUPPORTED_MARKER not in text or "Unsupported in Codex:" not in text:
                    errors.append(f"{plugin}/{skill}: missing explicit Codex unsupported contract")
                continue
            if PORTABLE_MARKER not in text or "../../reference/codex-portability.md" not in text:
                errors.append(f"{plugin}/{skill}: missing Codex adapter")
            relative_path = path.relative_to(root).as_posix()
            if relative_path in QUESTION_OVERRIDES:
                visited_overrides.add(relative_path)
                errors.extend(check_question_override(relative_path, text))
    errors.extend(
        f"{path}: question override key never checked (unknown or unsupported skill)"
        for path in sorted(set(QUESTION_OVERRIDES) - visited_overrides)
    )
    next_goal = root / "thinking-tools/skills/next-goal/SKILL.md"
    issue_raise = root / "thinking-tools/skills/issue-raise/SKILL.md"
    if next_goal.is_file():
        text = next_goal.read_text(encoding="utf-8")
        try:
            condition_reference = next_goal.with_name("reference.md").read_text(encoding="utf-8")
        except OSError:
            errors.append("thinking-tools/next-goal: missing condition reference")
        else:
            errors.extend(check_next_goal_condition(text, condition_reference))
        if ("one plain `GOAL` paragraph" not in text or "never a `/goal` fence" not in text
                or "Do not load Claude runtime details in Codex." not in text
                or "no nested Claude Skill call" not in text):
            errors.append("thinking-tools/next-goal: missing Codex direct-output contract")
        if ("caller's Git completion contract" not in text
                or "exclusion does not by itself exclude local commits" not in text):
            errors.append("thinking-tools/next-goal: missing caller Git completion contract")
    if issue_raise.is_file() and "approval gate before `gh issue create`" not in issue_raise.read_text(encoding="utf-8"):
        errors.append("thinking-tools/issue-raise: missing Codex approval contract")
    retro = root / "feedback-loop/skills/retro/SKILL.md"
    if retro.is_file():
        text = retro.read_text(encoding="utf-8")
        if ("Claude hook telemetry is unavailable in Codex." not in text
                or "current conversation's observable waste" not in text
                or "require user confirmation before `gh issue create`" not in text):
            errors.append("feedback-loop/retro: missing Codex conversation-waste contract")
    distill = root / "feedback-loop/skills/distill/SKILL.md"
    if distill.is_file():
        text = distill.read_text(encoding="utf-8")
        if ("never `~/.claude`" not in text
                or "continue with `add-policy`'s Codex storage" not in text
                or "separate one-click confirmation" not in text):
            errors.append("feedback-loop/distill: missing Codex persistence handoff contract")
    add_policy = root / "feedback-loop/skills/add-policy/SKILL.md"
    if add_policy.is_file():
        text = add_policy.read_text(encoding="utf-8")
        if ("CODEX_ROOT=\"${CODEX_HOME:-$HOME/.codex}\"" not in text
                or "$CODEX_ROOT/AGENTS.md" not in text
                or "$HOME/.agents/skills/<name>/SKILL.md" not in text
                or "$CODEX_ROOT/hooks.json" not in text
                or "never silently grant trust." not in text):
            errors.append("feedback-loop/add-policy: missing safe Codex storage contract")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return question_self_test()
    errors = check(args.root.resolve())
    if errors:
        print("FAIL: Codex portability")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("OK: Codex portability clean — 19 skills classified (19 supported, 0 unsupported)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
