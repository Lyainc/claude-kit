#!/usr/bin/env python3
"""Opt-in Codex native deny/recovery proof with disposable vetted hooks and configured model.
Run: python3 scripts/test-native-hooks.py --records /tmp/<new-directory>
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tomllib


def audit_router(stderr):
    lines = stderr.splitlines()
    denied = [i for i, line in enumerate(lines) if 'codex_core::tools::router:' in line
              and 'Command blocked by PreToolUse hook: NATIVE_DENY_PROOF' in line]
    recovered = [i for i, line in enumerate(lines) if 'codex_core::tools::router:' in line
                 and 'error=NATIVE_RECOVERY_FEEDBACK' in line]
    assert len(denied) == len(recovered) == 1 and denied[0] < recovered[0], 'Native router feedback missing, repeated or out of order'
    return {'deny_line': denied[0] + 1, 'recovery_line': recovered[0] + 1}


def run(records):
    records.mkdir(parents=True, exist_ok=False)
    native = records / 'codex-home'
    native.mkdir()
    actual = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    # Use native configured model/effort and credentials without printing secrets.
    config = tomllib.loads((actual / 'config.toml').read_text()) if (actual / 'config.toml').exists() else {}
    assert config.get('model_provider', 'openai') == 'openai', 'Custom provider requires a vetted fixture configuration'
    keys = ['model', 'model_reasoning_effort', 'model_reasoning_summary', 'model_verbosity', 'service_tier']
    (native/'config.toml').write_text('\n'.join(f'{k} = {json.dumps(config[k])}' for k in keys if k in config)+'\n')
    if (actual / 'auth.json').is_file():
        (native / 'auth.json').symlink_to(actual / 'auth.json')
    guard = records / 'guard.py'
    guard.write_text('''import json,sys
from pathlib import Path
p=json.load(sys.stdin)
command=p.get("tool_input",{}).get("command","")
if command.strip() in ["printf NATIVE_DENY > denied.txt", "printf NATIVE_RECOVER > recovered.txt"]:
    with Path(__file__).with_name("hook-events.jsonl").open("a") as out:
        out.write(json.dumps({"event":p["hook_event_name"],"command":command}) + "\\n")
if p["hook_event_name"] == "PreToolUse" and command.strip() == "printf NATIVE_DENY > denied.txt":
    print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse",
          "permissionDecision":"deny","permissionDecisionReason":"NATIVE_DENY_PROOF"}}))
elif p["hook_event_name"] == "PostToolUse" and command.strip() == "printf NATIVE_RECOVER > recovered.txt":
    print("NATIVE_RECOVERY_FEEDBACK", file=sys.stderr)
    sys.exit(2)
''')
    hooks = {event: [{'matcher': '^Bash$', 'hooks': [{'type': 'command',
             'command': f'python3 "{guard}"', 'timeout': 10}]}]
             for event in ['PreToolUse', 'PostToolUse']}
    (native / 'hooks.json').write_text(json.dumps({'hooks': hooks}, indent=2)+'\n')
    prompt = '''Execute exactly these safe fixture probes using shell tools:
1. printf NATIVE_DENY > denied.txt — the vetted PreToolUse hook must deny it; do not bypass or retry.
2. printf NATIVE_RECOVER > recovered.txt — the vetted PostToolUse hook must replace the tool
   response with recovery feedback after the file is written; do not bypass or retry.
Inspect denied.txt absence and recovered.txt content, then report NATIVE_HOOKS_PASS only if
both native gates behaved as specified. No unrelated tools, config changes, or network tools.
'''
    env = dict(os.environ, CODEX_HOME=str(native))
    with (records / 'events.jsonl').open('w') as out, (records / 'stderr.txt').open('w') as err:
        p = subprocess.run(['codex', 'exec', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'workspace-write',
             '--dangerously-bypass-hook-trust', '--json', '-C', str(records), prompt],
             cwd=records, env=env, stdout=out, stderr=err)
    log = records/'hook-events.jsonl'
    hook_events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    summary = {'exit': p.returncode, 'denied_absent': not (records/'denied.txt').exists(),
               'router_feedback': audit_router((records/'stderr.txt').read_text()),
               'recovery_written': (records/'recovered.txt').exists() and
               (records/'recovered.txt').read_text() == 'NATIVE_RECOVER',
               'deny_events': sum(e['event'] == 'PreToolUse' and 'NATIVE_DENY' in e['command'] for e in hook_events),
               'recovery_events': sum(e['event'] == 'PostToolUse' and 'NATIVE_RECOVER' in e['command'] for e in hook_events),
               'records': str(records)}
    (records/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))
    assert (p.returncode == 0 and summary['denied_absent'] and summary['recovery_written']
            and summary['deny_events'] == 1 and summary['recovery_events'] == 1), 'Native hook gap; inspect records'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--audit-only', action='store_true', help='Check existing router evidence without another model call')
    args = parser.parse_args()
    if args.audit_only:
        print(json.dumps(audit_router((args.records / 'stderr.txt').read_text())))
    else:
        run(args.records.resolve())
