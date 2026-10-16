#!/usr/bin/env python3
"""Read-only Seed lifecycle validation (#814): check <seed> [--before file] [--json].

Approvals and evidence locations are represented, never authenticated by this checker.
Unsupported YAML fails visibly; no YAML code, aliases or tags are executed.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path

SHA = re.compile(r'^[0-9a-fA-F]{40}$')
KEY = re.compile(r'^([A-Za-z_][\w-]*):(?:\s+(.*))?$')

class FormatError(ValueError):
    pass


def comment(text):
    quote, escaped = None, False
    for i, ch in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\' and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"" and (i == 0 or text[i-1] in ' [,{'):
            quote = ch
        elif ch == '#' and (i == 0 or text[i-1].isspace()):
            return text[:i].rstrip()
    if quote:
        raise FormatError('unclosed quoted scalar')
    return text.rstrip()


def scalar(text):
    text = comment(text.strip())
    if not text or text in ('null','Null','NULL','~'):
        return None
    if text.startswith('"'):
        try:
            return json.loads(text)
        except ValueError as exc:
            raise FormatError('invalid quoted scalar') from exc
    if text.startswith("'"):
        return text[1:-1].replace("''", "'")
    if text.startswith('['):
        if not text.endswith(']'):
            raise FormatError('unclosed flow sequence')
        parts, start, quote, escaped = [], 1, None, False
        for i,ch in enumerate(text[1:-1],1):
            if quote:
                if escaped:
                    escaped = False
                elif ch == '\\' and quote == '"':
                    escaped = True
                elif ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch in '[{}]':
                raise FormatError('nested flow containers unsupported; use block YAML')
            elif ch == ',':
                parts.append(text[start:i]); start = i+1
        parts.append(text[start:-1])
        if quote or (any(not p.strip() for p in parts) and text[1:-1].strip()):
            raise FormatError('malformed flow sequence')
        return [scalar(p) for p in parts if p.strip()]
    if text == '{}':
        return {}
    if text.startswith(('!','&','*','{',']')):
        raise FormatError('tags, aliases, anchors and flow mappings unsupported')
    if text in ('true','false'):
        return text == 'true'
    if re.fullmatch(r'[0-9]+',text):
        return int(text)
    return text


def parse_block(inline, body):
    """Parse a Seed block separated by the existing seed-relations mapping reader."""
    inline = comment(inline.strip())
    meaningful = []
    literal_indent = None
    for line in body:
        indent = len(line)-len(line.lstrip(' '))
        if literal_indent is not None and indent > literal_indent:
            meaningful.append(line)
            continue
        if line.strip():
            literal_indent = None
        if not line.strip() or line.lstrip().startswith('#') or line.strip() in ('---','...'):
            continue
        meaningful.append(line)
        match = KEY.match(line.strip()[2:] if line.strip().startswith('- ') else line.strip())
        if match and (match.group(2) or '').startswith(('|','>')):
            literal_indent = indent+2 if line.strip().startswith('- ') else indent
    if inline:
        if inline[0] in '|>':
            return '\n'.join(l.strip() for l in meaningful)
        if meaningful:
            raise FormatError('inline value also has nested body')
        return scalar(inline)
    if not meaningful:
        return None
    if any('\t' in l[:len(l)-len(l.lstrip())] for l in meaningful):
        raise FormatError('tabs in indentation unsupported')
    lines = [(len(l)-len(l.lstrip(' ')),l.strip()) for l in meaningful]

    def block(pos, indent):
        seq = lines[pos][1].startswith('- ')
        out = [] if seq else {}
        while pos < len(lines) and lines[pos][0] == indent:
            content = lines[pos][1]
            if seq != content.startswith('- '):
                raise FormatError('mixed mapping and sequence')
            if seq:
                text = content[2:]
                end = pos+1
                while end < len(lines) and lines[end][0] > indent:
                    end += 1
                if KEY.match(text):
                    chunk = [' '*(indent+2)+text] + [' '*i+t for i,t in lines[pos+1:end]]
                    out.append(parse_block('',chunk))
                elif end != pos+1:
                    raise FormatError('nested scalar sequence item unsupported')
                else:
                    out.append(scalar(text))
                pos = end; continue
            match = KEY.match(content)
            if not match:
                raise FormatError('unsupported mapping line: '+content)
            k,value = match.group(1),comment(match.group(2) or '')
            if k in out:
                raise FormatError('duplicate key: '+k)
            pos += 1; end = pos
            while end < len(lines) and (lines[end][0] > indent or
                    (not value and lines[end][0] == indent and lines[end][1].startswith('- '))):
                end += 1
            if value.startswith(('|','>')):
                out[k] = '\n'.join(t for _,t in lines[pos:end]); pos = end
            elif pos < end:
                if value:
                    if any(KEY.match(t) or t.startswith('- ') for _,t in lines[pos:end]):
                        raise FormatError('scalar '+k+' contains a nested structure')
                    out[k] = scalar(value+' '+' '.join(t for _,t in lines[pos:end])); pos = end
                else:
                    out[k],pos = block(pos,lines[pos][0])
                    if pos != end:
                        raise FormatError('invalid indentation under '+k)
            else:
                out[k] = scalar(value)
        return out,pos
    result,end = block(0,lines[0][0])
    if end != len(lines):
        raise FormatError('invalid indentation')
    return result


def text(v):
    return isinstance(v,str) and bool(v.strip())


def strings(v,name,errors,required=False):
    if not isinstance(v,list) or any(not text(x) for x in v):
        errors.append(name+' must be a list of nonempty strings'); return []
    if required and not v:
        errors.append(name+' must not be empty')
    if len(set(v)) != len(v):
        errors.append(name+' contains duplicates')
    return v


def record(v,fields,name,errors):
    if not isinstance(v,dict):
        errors.append(name+' must be a mapping'); return {}
    if set(v) != set(fields):
        errors.append(name+' fields must be '+', '.join(fields))
    return v


def path(v):
    p = v.split(':',1)[-1] if text(v) else ''
    return p.endswith(('.yaml','.yml')) and not p.startswith('/') and '..' not in p.split('/')


def validate(seed,root=None):
    errors,own = list(seed.format_errors),set(seed.item_map)
    if seed.duplicate_ids:
        errors.append('item IDs must be unique')
    lc = seed.lifecycle
    if lc is not None:
        lc = record(lc,('state','outcome','reason','approved_by','evidence','withdrawn'),'lifecycle',errors)
        state,outcome = lc.get('state'),lc.get('outcome')
        if state not in ('active','paused','closed'):
            errors.append('lifecycle.state must be active, paused or closed')
        if (state in ('active','paused') and outcome is not None) or (state == 'closed' and outcome not in ('completed','discontinued')):
            errors.append('only closed lifecycle has completed/discontinued outcome')
        for k in ('reason','approved_by'):
            if not text(lc.get(k)):
                errors.append('lifecycle.'+k+' must be nonempty')
        ev = record(lc.get('evidence'),('commit','items'),'lifecycle.evidence',errors)
        commit = ev.get('commit')
        if commit is not None and (not isinstance(commit,str) or not SHA.fullmatch(commit)):
            errors.append('evidence.commit must be a full Git SHA or null')
        evidenced,withdrawn = set(),set()
        for name,rows,seen in (('evidence.items',ev.get('items'),evidenced),('withdrawn',lc.get('withdrawn'),withdrawn)):
            if not isinstance(rows,list):
                errors.append(name+' must be a list'); continue
            for row in rows:
                row = record(row,('id','refs') if name == 'evidence.items' else ('id','reason'),name+'[]',errors)
                iid = row.get('id')
                if not isinstance(iid,str) or iid not in own:
                    errors.append(name+' references undefined item: '+str(iid))
                elif iid in seen:
                    errors.append(name+' repeats item: '+iid)
                else:
                    seen.add(iid)
                if name == 'evidence.items':
                    strings(row.get('refs'),'evidence refs',errors,True)
                elif not text(row.get('reason')):
                    errors.append('withdrawal reason must be nonempty')
        if evidenced & withdrawn:
            errors.append('withdrawn items cannot count as completion evidence')
        if own and withdrawn == own and outcome != 'discontinued':
            errors.append('all-withdrawn Seed must be closed/discontinued')
        if outcome == 'completed':
            if not commit:
                errors.append('completed lifecycle requires evidence.commit')
            if not own-withdrawn:
                errors.append('completed lifecycle requires nonwithdrawn requirements')
            if own-withdrawn-evidenced:
                errors.append('completed lifecycle lacks evidence for: '+', '.join(sorted(own-withdrawn-evidenced)))
        if commit and isinstance(commit,str) and SHA.fullmatch(commit) and root:
            try:
                p = subprocess.run(['git','-C',str(root),'cat-file','-t',commit],capture_output=True,text=True,timeout=30)
                if p.returncode or p.stdout.strip() != 'commit':
                    errors.append('evidence commit unavailable: '+commit)
            except (OSError,subprocess.TimeoutExpired):
                errors.append('evidence commit unavailable: '+commit)
    r = seed.relations_data
    structured = seed.relations_version in (2,3)
    if any(k in r for k in ('refines_map','provenance','replaces','transfers')) and not structured:
        errors.append('structured relations require version 2 or 3')
    if seed.relations_version is not None and not structured:
        errors.append('relations.version must be 2 or 3 when recorded')
    if seed.relations_version == 3:
        if 'refines_map' in r:
            errors.append('relations.refines_map is not used in version 3')
        if seed.parent:
            if not seed.refines:
                errors.append('version 3 relations.refines must name at least one parent acceptance when a parent is set')
            elif any(not seed.is_acceptance_id(i) for i in seed.refines):
                errors.append('version 3 relations.refines must contain only acceptance ids')
    if structured or lc is not None:
        if not seed.parent and (seed.refines or r.get('refines_map') or getattr(seed,'link_reason',None)):
            errors.append('relations.refines, refines_map and link_reason require a parent')
        for name in ('refines','children','depends_on','replaces'):
            vals = strings(r.get(name,[]),'relations.'+name,errors)
            if name == 'depends_on':
                # `path.yaml#acceptance-1` names one item of the predecessor (#885).
                if any('#' in v and not v.split('#',1)[1].strip() for v in vals):
                    errors.append('relations.depends_on item fragment must not be empty')
                vals = [v.split('#',1)[0] for v in vals]
            if name != 'refines' and any(not path(v) for v in vals):
                errors.append('relations.'+name+' must name exact Seed files')
        if r.get('parent') is not None and not path(r['parent']):
            errors.append('relations.parent must be an exact Seed file or null')
        for name,fields in (('refines_map',('parent_item','child_items')),('provenance',('seed','commit','items')),('transfers',('seed','items'))):
            rows = r.get(name,[])
            if not isinstance(rows,list):
                errors.append('relations.'+name+' must be a list'); continue
            seen = set()
            for row in rows:
                row = record(row,fields,'relations.'+name+'[]',errors)
                if name == 'refines_map':
                    src = row.get('parent_item')
                    if not isinstance(src,str) or src not in seed.refines:
                        errors.append('refines_map.parent_item must exist in refines')
                    elif src in seen:
                        errors.append('refines_map repeats parent_item')
                    else:
                        seen.add(src)
                    ids = strings(row.get('child_items'),'refines_map.child_items',errors,True)
                else:
                    if not path(row.get('seed')):
                        errors.append(name+'.seed must name an exact Seed file')
                    ids = strings(row.get('items'),name+'.items',errors,True)
                    if name == 'provenance' and (not isinstance(row.get('commit'),str) or not SHA.fullmatch(row['commit'])):
                        errors.append('provenance.commit must be a full Git SHA')
                if name != 'provenance' and set(ids)-own:
                    errors.append(name+' references undefined own items: '+', '.join(sorted(set(ids)-own)))
    return errors


def child_blockers(after,reader,rel):
    """Same-repo child-edge children of `after` (at repo path `rel`) that are not closed."""
    errors = []
    exact = after.relations_version in (2,3) or after.lifecycle is not None
    self_res = reader.resolve_quiet((None,rel),exact)
    for c in after.children:
        loc = reader.norm(c,None)
        if loc[0] is not None:
            continue  # another repo's child is not judged here
        ld = reader.load(loc,exact)
        name = ld.loc[1] if ld.loc else loc[1]
        if ld.seed is None:
            errors.append('parent completion requires a readable child; unreadable: '+name)
            continue
        child = ld.seed
        back = reader.resolve_quiet(reader.norm(child.parent,None),exact) if child.parent else None
        if back != self_res or not child.is_child_edge():
            continue  # reference edges and unrelated listings never block
        state = child.lifecycle.get('state') if isinstance(child.lifecycle,dict) else None
        if state != 'closed':
            errors.append('parent cannot close while child is not closed: '+name+' ('+str(state or 'unknown')+')')
    return errors


def prior_parent_provenance(before,after,rd):
    """An independent transition or relink must pin the previous parent as actually resolved."""
    exact = before.relations_version in (2,3) or before.lifecycle is not None
    if rd is None:
        if not exact:
            return ['previous legacy parent needs a repository reader to resolve; pin the resolved file in provenance']
        loc = (None,posixpath.normpath(before.parent.strip().lstrip('/')))
    else:
        loc,err = rd.resolve(rd.norm(before.parent,None),exact)
        if err:
            return [f'previous legacy parent cannot be resolved ({err}); pin the actually resolved file in provenance']
    norm = (lambda v: rd.norm(v,None)) if rd else (lambda v: (None,posixpath.normpath(v.strip().lstrip('/'))))
    rows = after.relations_data.get('provenance') if isinstance(after.relations_data,dict) else None
    for row in rows if isinstance(rows,list) else []:
        if (isinstance(row,dict) and path(row.get('seed')) and norm(row['seed']) == loc and
                isinstance(row.get('commit'),str) and SHA.fullmatch(row['commit']) and
                isinstance(row.get('items'),list) and set(before.refines) <= set(row['items'])):
            return []
    return [f'reparent or independent transition must pin previous parent {loc[1]} with its full commit and refined items '
            + str(sorted(before.refines)) + ' in relations.provenance']


def kept_provenance(before,after,rd=None):
    """A pinned provenance row is history: later edits keep its seed and commit, and its items only grow.
    Correcting a wrongly pinned row is a represented user-approved change, like any other transition."""
    def rows(seed):
        r = seed.relations_data.get('provenance') if isinstance(seed.relations_data,dict) else None
        return [x for x in r if isinstance(x,dict)] if isinstance(r,list) else []
    def key(v):
        if not isinstance(v,str) or not v.strip():
            return v
        return rd.norm(v,None) if rd else (None,posixpath.normpath(v.strip().lstrip('/')))
    def items(row):
        return {i for i in row['items'] if isinstance(i,str)} if isinstance(row.get('items'),list) else set()
    old,new = before.lifecycle,after.lifecycle
    if (isinstance(old,dict) and isinstance(new,dict) and text(new.get('approved_by')) and text(new.get('reason'))
            and new.get('approved_by') != old.get('approved_by')):
        return []
    kept = rows(after)
    return [f'relations.provenance row {row.get("seed")}@{row.get("commit")} items {sorted(items(row))} was dropped or rewritten; '
            'pinned provenance is append-only unless a new user approval and reason correct it'
            for row in rows(before)
            if not any(key(k.get('seed')) == key(row.get('seed')) and k.get('commit') == row.get('commit')
                       and items(row) <= items(k) for k in kept)]


def transition(before,after,reader=None,rel=None):
    """Validate before -> after. `reader`/`rel` (a seed-relations Reader and the repo-relative
    path of `after`) enable the parent-completion rule; without them it is skipped."""
    errors = []
    old,new = before.lifecycle,after.lifecycle
    if isinstance(old,dict) and old.get('state') == 'closed':
        if before.semantic != after.semantic:
            errors.append('closed Seed is immutable; create a new Seed with provenance')
        return errors
    if reader is not None and rel is not None and isinstance(new,dict) and new.get('state') == 'closed' and new.get('outcome') == 'completed':
        errors += child_blockers(after,reader,rel)
    changed = old != new or before.parent != after.parent
    if changed and (not isinstance(new,dict) or not text(new.get('approved_by')) or not text(new.get('reason'))):
        errors.append('lifecycle/withdrawal/reparent change requires represented user approval and reason')
    if changed and isinstance(old,dict) and isinstance(new,dict) and new.get('approved_by') == old.get('approved_by'):
        errors.append('transition requires a new explicit approval reference')
    # Only a child edge composed its parent; dropping a version 2 reference edge pins nothing.
    if before.parent and before.parent != after.parent and before.is_child_edge():
        errors += prior_parent_provenance(before,after,reader)
    errors += kept_provenance(before,after,reader)
    if old != new and before.requirements != after.requirements:
        errors.append('lifecycle transition must preserve original requirement contents and IDs')
    rows = old.get('withdrawn',[]) if isinstance(old,dict) else []
    if isinstance(rows,list) and any(before.requirements.get(r.get('id')) != after.requirements.get(r.get('id')) for r in rows if isinstance(r,dict)):
        errors.append('withdrawn requirement contents and IDs must be preserved')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['check']); parser.add_argument('seed')
    parser.add_argument('--before'); parser.add_argument('--json',action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('seed_relations',Path(__file__).with_name('seed-relations.py'))
    sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)
    try:
        seed = sr.parse_seed(Path(args.seed).read_text(encoding='utf-8')); root = sr.find_root(args.seed)
        errors = validate(seed,root)+sr.validate_provenance(sr.Reader(root),seed,None)
        if args.before:
            before = sr.parse_seed(Path(args.before).read_text(encoding='utf-8'))
            rel = os.path.relpath(os.path.realpath(args.seed),root).replace(os.sep,'/')
            errors += validate(before,root)+transition(before,seed,sr.Reader(root),rel)
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        errors = [str(exc)]
    print(json.dumps({'valid':not errors,'errors':errors},ensure_ascii=False) if args.json else
          '\n'.join('INVALID: '+e for e in errors) if errors else 'OK: lifecycle valid')
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
