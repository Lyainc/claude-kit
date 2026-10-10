#!/usr/bin/env python3
"""Check copied deployment units, one at a time, without developer state (#817).

This is a deterministic package check, not a native runtime/LLM invocation.
Reference scope is documented in docs/VALIDATION.md; --self-test pins its boundary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGINS = ("thinking-tools", "obsidian-vault-manager", "vault-bridge", "feedback-loop")
SURFACES = ("skills", "reference", "templates", "hooks", "agents")
ROOT_PATH = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?[\"']?/([\w./-]+)")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
TICK = re.compile(r"`([^`\n]+)`")
BINDING = re.compile(
    r"\b(read|apply|load|follow|see|binding|canonical|contract|schema|source of truth)\b",
    re.IGNORECASE,
)
BACKGROUND = re.compile(r"\b(history|historical|background|rationale|lineage)\b", re.IGNORECASE)
READ_CONTEXT = re.compile(r"\b(read|apply|load|follow|see)\b[^`\n]*$", re.IGNORECASE)
CONSUMER_FILES = {"CLAUDE.md", "AGENTS.md", "README.md"}


def clause(line, start, end):
    """Classify the reference's own clause, not a neighboring history pointer."""
    left = max((line.rfind(separator, 0, start) for separator in (";", "·", ",")), default=-1)
    right = min((index for separator in (";", "·", ",")
                 for index in [line.find(separator, end)] if index != -1), default=len(line))
    return line[left + 1:right]


def references(text):
    """Yield (line, path, anchor) for scoped package references, not output paths.

    Explicit plugin-root paths bind even in shell fences. Relative Markdown links
    bind unless explicitly historical/background. Backticks require a read/apply
    context and a known package surface or local .md filename. Consumer paths,
    variable outputs, optional cross-plugin calls and URLs are not local assets.
    """
    text = re.sub(r"<!--.*?-->", lambda match: "\n" * match.group(0).count("\n"),
                  text, flags=re.DOTALL)
    for number, line in enumerate(text.splitlines(), 1):
        for match in ROOT_PATH.finditer(line):
            yield number, match.group(1), "root"
        for match in LINK.finditer(line):
            path = match.group(1).split("#", 1)[0]
            if (not path or re.match(r"[\w+.-]+:", path)
                    or path.startswith(("/", "~", "{", "docs/"))
                    or BACKGROUND.search(clause(line, match.start(), match.end()))):
                continue
            if path.endswith(".md"):
                yield number, path, "file"
        if not BINDING.search(line):
            continue
        for match in TICK.finditer(line):
            context = clause(line, match.start(), match.end())
            if BACKGROUND.search(context):
                continue
            path = match.group(1).split("#", 1)[0]
            if ("$" in path or "{" in path or " " in path or path.startswith(".") and "/" not in path
                    or path in CONSUMER_FILES):
                continue
            stripped = re.sub(r"^(?:\.\./|\./)+", "", path)
            if (stripped.split("/", 1)[0] in SURFACES
                    or (path.startswith(("../", "./"))
                        and READ_CONTEXT.search(line[:match.start()]))
                    or ("/" not in path and path.endswith(".md")
                        and READ_CONTEXT.search(line[:match.start()]))):
                yield number, path, "local"


def reference_errors(package):
    errors = []
    count = 0
    sources = [package / "plugin.json", package / ".claude-plugin/plugin.json"]
    for surface in SURFACES:
        sources.extend(sorted((package / surface).rglob("*")))
    for source in sources:
        if source.suffix not in (".md", ".sh", ".json") or not source.is_file():
            continue
        # Examples/rationale are illustrative, not executable read contracts.
        if "examples" in source.parts or source.name in ("examples.md", "rationale.md"):
            continue
        for line, raw, anchor in references(source.read_text(encoding="utf-8")):
            count += 1
            candidates = [package / raw] if anchor == "root" else [source.parent / raw]
            if anchor == "local" and raw.split("/", 1)[0] in SURFACES:
                candidates.append(package / raw)
            # This worker is passed the bundled expert-panel skill directory;
            # its literal read names are relative to that explicit input.
            if (source.relative_to(package).as_posix() == "agents/expert-panel-worker.md"
                    and raw in ("SKILL.md", "reference.md")):
                candidates = [package / "skills/expert-panel" / raw]
            resolved = [p.resolve() for p in candidates]
            inside = [p for p in resolved if package.resolve() in p.parents]
            if not any(p.exists() for p in inside):
                errors.append(f"{source.relative_to(package)}:{line}: {raw} "
                              "does not resolve inside deployed package")
    return count, errors


def self_test():
    cases = [
        ('Read [contract](../../reference/missing.md)', ["../../reference/missing.md"]),
        ('Read `reference/missing.md` before continuing.', ["reference/missing.md"]),
        ('bash "${CLAUDE_PLUGIN_ROOT}/scripts/missing.sh"', ["scripts/missing.sh"]),
        ('Read `fix.md` and apply it.', ["fix.md"]),
        ('Canonical [policy](../../../docs/policy.md)', ["../../../docs/policy.md"]),
        ('Historical [design](../../../docs/design.md)', []),
        ('Background [rationale](../../../docs/rationale.md)', []),
        ('Read [binding](missing.md); background [history](old.md)', ["missing.md"]),
        ('Read [binding](missing.md), historical [history](old.md)', ["missing.md"]),
        ('Read `../../../docs/policy.md`; background [history](old.md)', ["../../../docs/policy.md"]),
        ('Read `reference/required.md` · background `reference/old.md`', ["reference/required.md"]),
        ('Write `docs/specs/new.md` then read `{output_path}`.', []),
        ('Save [output](docs/specs/new.md) in the consumer project.', []),
        ('Read `~/vault/notes/topic.md` and `CLAUDE.md` in the consumer project.',
         []),
        ('Read a `.md` file and save `docs/specs/output.md`.', []),
        ('Canonical text: `agent.md` points here.', []),
        ('"${CLAUDE_PLUGIN_ROOT}"/hooks/check.sh', ["hooks/check.sh"]),
        ('If available, invoke `vault-bridge:vault-save`.', []),
        ('See [API](https://example.com/api.md) and [section](#section).', []),
        ('<!-- Read [missing](missing.md) -->', []),
    ]
    for text, expected in cases:
        got = [path for _, path, _ in references(text)]
        assert got == expected, (text, got, expected)
    with tempfile.TemporaryDirectory(prefix="plugin-reference-self-test-") as directory:
        root = Path(directory) / "package"
        skill = root / "skills" / "demo"
        skill.mkdir(parents=True)
        (skill / "reference.md").write_text("present", encoding="utf-8")
        body = skill / "SKILL.md"
        body.write_text("Read `reference.md`", encoding="utf-8")
        assert not reference_errors(root)[1]
        body.write_text('Read "${CLAUDE_PLUGIN_ROOT}/reference/missing.md"', encoding="utf-8")
        assert reference_errors(root)[1]
        body.write_text("Read [binding](../../../outside.md)", encoding="utf-8")
        (root.parent / "outside.md").touch()
        # An existing file outside the package must still fail containment.
        assert reference_errors(root)[1]
    print(f"OK: {len(cases)} reference classification cases + containment mutation")


def run_case(label, command, env, cwd, expected=0, payload=None):
    result = subprocess.run(command, env=env, cwd=cwd, capture_output=True,
                            text=True, timeout=45, input=payload)
    print(f"  {label}: exit={result.returncode}; stdout={result.stdout.strip()[:1200]!r}; "
          f"stderr={result.stderr.strip()[:1200]!r}")
    if len(result.stdout.strip()) > 1200 or len(result.stderr.strip()) > 1200:
        print("    (log preview shortened; assertions inspect complete output)")
    assert result.returncode == expected, (label, result.returncode, expected)
    return result


def isolated_environment(root, package):
    for name in ("home", "cwd", "bin", "tmp", "config"):
        (root / name).mkdir()
    # Executable-only PATH: no repo, user bin directory, neighboring plugin or
    # inherited configuration. Python runs with an empty module search override.
    for tool in ("bash", "sh", "git", "gh", "jq", "sed", "awk", "dirname", "date",
                 "mkdir", "cat", "mv", "find", "sort", "head", "wc", "grep", "tr", "seq"):
        executable = shutil.which(tool)
        if executable:
            (root / "bin" / tool).symlink_to(Path(executable).resolve())
    (root / "bin" / "python3").symlink_to(Path(sys.executable).resolve())
    env = {
        "HOME": str(root / "home"), "PATH": str(root / "bin"),
        "TMPDIR": str(root / "tmp"), "XDG_CONFIG_HOME": str(root / "config"),
        "GH_CONFIG_DIR": str(root / "config" / "gh"), "GH_PROMPT_DISABLED": "1",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CEILING_DIRECTORIES": str(root), "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "", "CLAUDE_PLUGIN_ROOT": str(package), "LC_ALL": "C",
    }
    return env


def zero_backlog(root):
    """Successful zero is a deterministic API fixture, never a live GH claim."""
    stub_dir = root / "api-fixture"
    stub_dir.mkdir()
    stub = stub_dir / "gh"
    stub.write_text("#!/bin/sh\nif [ \"$1 $2\" = 'issue list' ]; then\n"
                    "  printf '[]\\n'\nelse\n  exit 1\nfi\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub_dir


def exercise(name, root, package, env):
    cwd = root / "cwd"
    py = str(root / "bin" / "python3")
    bash = str(root / "bin" / "bash")
    git = run_case("no git repository", ["git", "rev-parse", "--show-toplevel"],
                   env, cwd, 128)
    assert "not a git repository" in git.stderr
    if (root / "bin" / "gh").exists():
        auth = run_case("no GH authentication (real CLI)", ["gh", "auth", "status"],
                        env, cwd, 1)
        assert "not logged" in auth.stderr.lower() or "not logged" in auth.stdout.lower()
    else:
        print("  no GH authentication: CLI absent; no live auth claim")
    if name == "feedback-loop":
        result = run_case("CWD fallback with no telemetry", [py, str(package / "scripts/report.py"),
                          "--format=json", "--since=all"], env, cwd)
        assert "No events matched" in result.stdout
        result = run_case("backlog unavailable", [bash, str(package / "scripts/gh-issues-cache.sh"),
                          "get"], env, cwd, 1)
        assert "[gh-issues-cache FAILED]" in result.stdout and result.stdout.strip() != "[]"
        success_env = dict(env, PATH=str(zero_backlog(root)) + os.pathsep + env["PATH"])
        result = run_case("successful zero backlog (API fixture)",
                          [bash, str(package / "scripts/gh-issues-cache.sh"), "get"], success_env, cwd)
        assert json.loads(result.stdout) == []
        events = cwd / ".claude-kit/telemetry/events"
        events.mkdir(parents=True)
        stamp = run_case("no-repo telemetry stamp", [bash, str(package / "scripts/retro-telemetry.sh"),
                         "stamp"], dict(env, CLAUDE_KIT_TELEMETRY="1"), cwd)
        assert stamp.stdout.strip().isdigit()
        run_case("log event without repository", [bash, str(package / "scripts/event-logger.sh"),
                 "skill_invoke_start"], dict(env, CLAUDE_KIT_TELEMETRY="1"), cwd,
                 payload=json.dumps({"session_id": "isolated", "tool_input": {"skill": "retro"}}))
        result = run_case("report real locally logged event", [py, str(package / "scripts/report.py"),
                          "--format=json", "--since=all"], env, cwd)
        assert json.loads(result.stdout)["total"] == 1
    elif name == "thinking-tools":
        result = run_case("backlog unavailable", [py, str(package / "scripts/backlog-prefilter.py"),
                          "--intent", "isolated plugin"], env, cwd)
        assert "[backlog-scan SKIPPED]" in result.stdout
        result = run_case("no consumer template", [py, str(package / "scripts/issue-template.py"),
                          "--list", "--json"], env, cwd, 1)
        assert json.loads(result.stdout) == []
        templates = cwd / ".github/ISSUE_TEMPLATE"
        templates.mkdir(parents=True)
        (templates / "bug.md").write_text("---\nname: Bug\n---\n## Problem\n## Expected\n",
                                         encoding="utf-8")
        result = run_case("consumer template without Git", [py, str(package / "scripts/issue-template.py"),
                          "--list", "--json"], env, cwd)
        assert len(json.loads(result.stdout)) == 1
    elif name == "obsidian-vault-manager":
        result = run_case("manifest unavailable", [py, str(package / "scripts/manifest-summary.py")],
                          env, cwd, 3)
        assert not result.stdout and "manifest unusable" in result.stderr
        vault = root / "fixture-vault"
        fixture_env = dict(env, OVM_FIXTURE_DIR=str(vault), VAULT_BRIDGE_VAULT_ROOT=str(vault))
        run_case("existing OVM fixture generator", [bash, str(package / "scripts/test/gen-fixture.sh")],
                 fixture_env, cwd)
        result = run_case("existing vault, missing manifest", [py, str(package / "scripts/manifest-summary.py")],
                          fixture_env, cwd, 3)
        assert not result.stdout and "manifest unusable" in result.stderr
        result = run_case("frontmatter scan of generated fixture", [bash,
                          str(package / "scripts/ovm-primitives.sh"), "scan-frontmatter", str(vault)],
                          fixture_env, cwd)
        assert len(json.loads(result.stdout)) >= 200
        manifest = vault / ".vault-bridge/manifest.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"file_count": 0, "generated_at": "fixture"}), encoding="utf-8")
        result = run_case("genuine zero manifest", [py, str(package / "scripts/manifest-summary.py"),
                          str(manifest)], fixture_env, cwd)
        assert json.loads(result.stdout)["file_count"] == 0
    else:
        result = run_case("no vault startup", [bash, str(package / "hooks/session-start-manifest.sh")],
                          env, cwd)
        assert "systemMessage" in json.loads(result.stdout)
        assert not (root / "home/vault").exists()
        command = [py, str(package / "scripts/manifest-keyword-candidates.py"), "isolation"]
        result = run_case("manifest unavailable", command, env, cwd, 3)
        assert not result.stdout and "manifest unusable" in result.stderr
        vault = root / "home/vault"
        (vault / ".obsidian").mkdir(parents=True)
        (vault / "notes").mkdir()
        run_case("generate empty-vault manifest", [py, str(package / "scripts/generate-manifest.py")],
                 env, cwd)
        result = run_case("successful zero candidates", command, env, cwd)
        assert json.loads(result.stdout)["candidate_count"] == 0
        (vault / "notes/isolation.md").write_text(
            "---\ntype: note\ncreated: 2026-01-01\ntags: [isolation]\n"
            "status: raw\nprovenance: fixture\n---\n# Isolation\nA package fixture.\n", encoding="utf-8")
        run_case("generate populated-vault manifest", [py, str(package / "scripts/generate-manifest.py")],
                 env, cwd)
        result = run_case("normal matching candidate", command, env, cwd)
        assert json.loads(result.stdout)["candidate_count"] == 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package", type=Path, help="Check only scoped references of one deployed package")
    args = parser.parse_args()
    if args.package:
        if (not args.package.is_dir()
                or not all((args.package / manifest).is_file()
                           for manifest in ("plugin.json", ".claude-plugin/plugin.json"))):
            print("FAIL: package directory and both plugin manifests are required", file=sys.stderr)
            return 1
        count, errors = reference_errors(args.package)
        print(f"{count} scoped references; {len(errors)} failures")
        for error in errors:
            print(error)
        return 1 if errors else 0
    self_test()
    if args.self_test:
        return 0
    failures = []
    for name in PLUGINS:
        with tempfile.TemporaryDirectory(prefix="isolated-plugin-") as directory:
            root = Path(directory).resolve()
            package = root / name
            shutil.copytree(args.root / name, package, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            print(f"{name}: standalone copy {package}")
            env = isolated_environment(root, package)
            count, errors = reference_errors(package)
            print(f"  static packaged reference existence: {count} scoped references; {len(errors)} failures")
            failures.extend(f"{name}: {error}" for error in errors)
            for error in errors:
                print(f"  FAIL {error}")
            broken = package / "skills" / "isolation-probe"
            broken.mkdir()
            (broken / "SKILL.md").write_text('Read [required](../../reference/injected-missing.md)',
                                           encoding="utf-8")
            assert any("injected-missing.md" in error for error in reference_errors(package)[1])
            checker = root / "check-isolated-plugins.py"
            shutil.copyfile(__file__, checker)
            mutation = run_case("injected missing binding reference", [str(root / "bin/python3"),
                                str(checker), "--package", str(package)], env, root / "cwd", 1)
            assert "injected-missing.md" in mutation.stdout
            (broken / "SKILL.md").unlink()
            broken.rmdir()
            try:
                exercise(name, root, package, env)
            except (AssertionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                failures.append(f"{name}: execution failed: {error}")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"Copied-package deterministic validation: {'FAIL' if failures else 'PASS'}; "
          "native install/discovery and guidance invocation: UNVERIFIED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
