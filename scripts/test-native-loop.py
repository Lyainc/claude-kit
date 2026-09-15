#!/usr/bin/env python3
"""Opt-in fresh native runtime scenario check; writes only its disposable fixture and records.

Run: python3 scripts/test-native-loop.py codex|claude --records /tmp/<new-directory>
This calls the configured model. No model/effort override, production writes, push or issue create.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def audit_events(runtime, events):
    commands, edits, pending = [], [], {}
    for index, event in enumerate(events):
        item = event.get('item', {})
        if runtime == 'codex' and event.get('type') == 'item.completed':
            if item.get('type') == 'command_execution':
                commands.append((index, item['command'], item.get('exit_code')))
            elif item.get('type') == 'file_change':
                edits.extend((index, Path(change['path']).name) for change in item.get('changes', []))
        elif runtime == 'claude':
            for block in event.get('message', {}).get('content', []):
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    data = block.get('input', {})
                    if block.get('name') == 'Bash':
                        pending[block['id']] = data.get('command', '')
                    elif block.get('name') in ['Edit', 'Write']:
                        edits.append((index, Path(data.get('file_path', '')).name))
                elif block.get('type') == 'tool_result' and block.get('tool_use_id') in pending:
                    commands.append((index, pending.pop(block['tool_use_id']), int(block.get('is_error', False))))
    checks = {name: [(i, code) for i, command, code in commands
                    for _ in re.finditer(r'\bpython(?:3)?\s+check_' + name + r'\.py\b', command)]
              for name in ['small', 'bundle', 'failure']}
    assert [code for _, code in checks['small']] == [0], 'Small check missing or repeated'
    assert [code for _, code in checks['bundle']] == [0], 'Bundle check missing or repeated'
    failure = checks['failure']
    assert len(failure) == 2 and failure[0][1] not in [None, 0] and failure[1][1] == 0, 'Failure/recovery evidence missing or repeated'
    clamp_edits = [i for i, path in edits if path == 'clamp.py']
    assert clamp_edits and all(failure[0][0] < i < failure[1][0] for i in clamp_edits), 'Clamp changed before observed failure'
    assert checks['small'][0][0] < checks['bundle'][0][0] < failure[0][0], 'Scenario order changed'
    collectors = {}
    # Allow quoted or unquoted script paths, but never count a cat/read of the collector.
    for stage in ['risk', 'sweep']:
        collectors[stage] = [(i, code) for i, command, code in commands for _ in re.finditer(
            r'session-close-collect\.sh[\"\'\s]*\s' + stage + r'\b', command)]
        assert len(collectors[stage]) == 1 and collectors[stage][0][1] == 0, f'{stage} collector missing or repeated'
    assert failure[1][0] < collectors['risk'][0][0] < collectors['sweep'][0][0], 'Collector stage order changed'
    return {'checks': checks, 'collectors': collectors, 'clamp_edits': clamp_edits}


def run(runtime, records):
    records.mkdir(parents=True, exist_ok=False)
    repo = records / 'fixture'
    repo.mkdir()
    files = {
        'greet.py': 'def greet(name):\n    return f"Hello, {name}"\n',
        'ranges.py': 'def parse_range(text):\n    raise NotImplementedError\n',
        'pairs.py': 'def parse_pairs(text):\n    raise NotImplementedError\n',
        'clamp.py': 'def clamp(value, low, high):\n    return min(low, max(high, value))\n',
        'check_small.py': 'from greet import greet\nassert greet("  Ada  ") == "Hello, Ada"\nprint("SMALL_PASS")\n',
        'check_bundle.py': '''from ranges import parse_range
from pairs import parse_pairs
assert parse_range(" 2:4 ") == [2, 3, 4]
assert parse_pairs(" a = 1 , b = 2 ") == {"a": "1", "b": "2"}
for call in [lambda: parse_range("4:2"), lambda: parse_range("a:2"),
             lambda: parse_pairs("a=1,a=2"), lambda: parse_pairs("=1")]:
    try: call()
    except ValueError: pass
    else: raise AssertionError("invalid input accepted")
print("BUNDLE_PASS")
''',
        'check_failure.py': 'from clamp import clamp\nassert clamp(5, 0, 10) == 5\nassert clamp(-1, 0, 10) == 0\nassert clamp(12, 0, 10) == 10\nprint("RECOVERY_PASS")\n',
    }
    for name, body in files.items():
        (repo / name).write_text(body)
    for cmd in [['git', 'init', '-q'], ['git', 'add', '.'],
                ['git', '-c', 'user.name=Loop Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'test: establish disposable loop fixture']]:
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    prompt = '''Run these five representative scenarios in this disposable repository in order.
This request authorizes fixture edits and relevant checks here only. Never write production
repositories/settings, create issues/PRs, push, merge, delete branches, or use network tools.
Use your installed native user instructions, thinking-tools and feedback-loop skills, and
session-close. Keep configured model/effort. Do not read the other runtime's workflow.
1. Small valid work: greet.py must strip surrounding whitespace; run check_small.py once after
   fixing it. Work directly; this is one trivial change.
2. Independent bundle: implement ranges.py parse_range("start:end") as an inclusive integer list,
   rejecting reversed/malformed ranges with ValueError; implement pairs.py parse_pairs as comma
   separated key=value strings, stripping whitespace and rejecting empty/duplicate keys or
   malformed entries. The two files are independent bounded tasks; choose native delegation
   only when available and beneficial, keeping concurrent work isolated according to your
   installed policy. Run check_bundle.py once after both implementations.
3. Failed validation then correction: run check_failure.py BEFORE changing clamp.py, retain the
   failure evidence, fix the actual min/max order, then run it once to prove recovery. Do not
   repeat passing small/bundle checks without a relevant change.
4. No valuable follow-up: invoke installed next-goal with all known candidates being formatting
   and wording nits. The supplied open-backlog comparison set is complete and empty for this
   fixture, chain depth 1, no remote, no intervening issue creation. Do not fetch another pool.
   Return its no-worthwhile-goal result. Run distill for only this session's techniques: default
   competent behavior and a single occurrence are not reusable candidates. Run retro on observed
   waste; one deliberately requested failed fixture check is evidence of recovery, not waste.
   Finally inspect add-policy's native site branch for a proposed deterministic blocking rule,
   reporting its approval and activation gates; do not land or activate anything.
5. Run installed session-close against this fixture only, using the existing collector directly.
   There are no PRs, no worked/affected issue, no authorized outward write or cleanup, and the
   next-goal outcome from stage 4 remains valid. Report local-only/uncommitted risk honestly,
   preserve everything, and reuse the no-goal result without a second candidate search.
Read the selected next-goal SKILL.md and session-close runtime reference through their final
lines, retrieving missing ranges if a tool preview truncates. At the end report SCENARIOS_PASS,
the actual final sentence of next-goal SKILL.md, the runtime reference path, scenario outcomes,
any unavailable native capabilities, and tool/check/delegation repetition counts. No final diff
review is needed for this disposable test; the production changes have a separate review gate.
'''
    (records / 'prompt.txt').write_text(prompt)
    if runtime == 'codex':
        cmd = ['codex', 'exec', '--ephemeral', '--sandbox', 'workspace-write', '--json', '-C', str(repo), prompt]
    else:
        cmd = ['claude', '-p', '--no-session-persistence', '--output-format', 'stream-json', '--verbose',
               '--permission-mode', 'acceptEdits', '--allowedTools', 'Read', 'Write', 'Edit', 'Bash', 'Agent', 'Skill', '--', prompt]
    started = time.time()
    with (records / 'events.jsonl').open('w') as out, (records / 'stderr.txt').open('w') as err:
        proc = subprocess.run(cmd, cwd=repo, stdout=out, stderr=err)
    events = []
    for line in (records / 'events.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    if runtime == 'codex':
        replies = [e['item']['text'] for e in events if e.get('type') == 'item.completed'
                   and e.get('item', {}).get('type') == 'agent_message']
    else:
        replies = [e.get('result', '') for e in events if e.get('type') == 'result']
    final = replies[-1] if replies else ''
    body_proof = 'The paragraph and any caller report must not print the pick twice.' in final
    scenario_proof = 'SCENARIOS_PASS' in final and body_proof and f'{runtime}.md' in final
    event_proof = audit_events(runtime, events) if proc.returncode == 0 else None
    checks = {}
    for name in ['small', 'bundle', 'failure']:
        p = subprocess.run(['python3', f'check_{name}.py'], cwd=repo, capture_output=True, text=True)
        checks[name] = {'exit': p.returncode, 'output': p.stdout + p.stderr}
    # Independent artifact audit is outside the model's in-session repetition count.
    summary = {'runtime': runtime, 'exit': proc.returncode, 'seconds': round(time.time()-started, 2),
               'scenario_proof': scenario_proof, 'body_tail_proof': body_proof, 'final_response': final,
               'event_proof': event_proof,
               'artifact_checks': checks, 'records': str(records), 'events_sha256':
               hashlib.sha256((records / 'events.jsonl').read_bytes()).hexdigest()}
    (records / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False))
    assert proc.returncode == 0 and scenario_proof and all(c['exit'] == 0 for c in checks.values()), 'Native scenario incomplete; inspect records'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', choices=['codex', 'claude'])
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--audit-only', action='store_true', help='Check existing event evidence without another model call')
    args = parser.parse_args()
    if args.audit_only:
        events = [json.loads(line) for line in (args.records / 'events.jsonl').read_text().splitlines()]
        print(json.dumps(audit_events(args.runtime, events)))
    else:
        run(args.runtime, args.records.resolve())
