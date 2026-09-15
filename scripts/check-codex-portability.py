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
    next_goal = root / "thinking-tools/skills/next-goal/SKILL.md"
    issue_raise = root / "thinking-tools/skills/issue-raise/SKILL.md"
    if next_goal.is_file():
        text = next_goal.read_text(encoding="utf-8")
        if ("one plain `GOAL` paragraph" not in text or "never a `/goal` fence" not in text
                or "Do not load Claude runtime details in Codex." not in text
                or "no nested Claude Skill call" not in text):
            errors.append("thinking-tools/next-goal: missing Codex direct-output contract")
    if issue_raise.is_file() and "normal user turn before `gh issue create`" not in issue_raise.read_text(encoding="utf-8"):
        errors.append("thinking-tools/issue-raise: missing Codex approval contract")
    retro = root / "feedback-loop/skills/retro/SKILL.md"
    if retro.is_file():
        text = retro.read_text(encoding="utf-8")
        if ("Claude hook telemetry is unavailable in Codex." not in text
                or "current conversation's observable waste" not in text
                or "normal user confirmation before `gh issue create`" not in text):
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
    args = parser.parse_args()
    errors = check(args.root.resolve())
    if errors:
        print("FAIL: Codex portability")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("OK: Codex portability clean — 19 skills classified (19 supported, 0 unsupported)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
