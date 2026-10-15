#!/usr/bin/env python3
"""Lifecycle, historical provenance and descendant gates regression fixtures (#814)."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-','_'),SCRIPTS/(name+'.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
sr = module('seed-relations')
guard = module('seed-append-check')
lc = sr.lifecycle


def dump(value,indent=0):
    pad = ' '*indent
    if isinstance(value,dict):
        lines = []
        for k,v in value.items():
            if isinstance(v,(dict,list)) and v:
                lines.append(pad+k+':'); lines.append(dump(v,indent+2))
            else:
                lines.append(pad+k+': '+json.dumps(v,ensure_ascii=False))
        return '\n'.join(lines)
    if isinstance(value,list):
        lines = []
        for v in value:
            if isinstance(v,dict):
                parts = dump(v,indent+2).splitlines()
                lines.append(pad+'- '+parts[0].lstrip()); lines.extend(parts[1:])
            else:
                lines.append(pad+'- '+json.dumps(v,ensure_ascii=False))
        return '\n'.join(lines)
    raise AssertionError(value)


def spec(state='active',outcome=None,withdrawn=(),parent=None,refines=(),mapping=(),children=(),version=2):
    obj = {'skill':'build-spec','target':'Fixture','goal':{'statement':'Short goal'},
           'constraints':[{'id':'constraint-1','description':'First original requirement'},
                          {'id':'constraint-2','description':'Second original requirement'}],
           'success_criteria':[{'id':'acceptance-1','description':'Observable result'}],
           'relations':{'version':2,'parent':parent,'refines':list(refines),'link_reason':'fixture' if parent else None,
                        'depends_on':[],'children':list(children),'refines_map':list(mapping),
                        'provenance':[],'replaces':[],'transfers':[]}}
    if version == 3 and not mapping:
        del obj['relations']['refines_map']  # version 3 no longer carries refines_map
    obj['relations']['version'] = version
    if state is not None:
        obj['lifecycle'] = {'state':state,'outcome':outcome,'reason':'User decision',
                            'approved_by':'user request message 1',
                            'evidence':{'commit':None,'items':[]},
                            'withdrawn':[{'id':i,'reason':'Scope changed'} for i in withdrawn]}
    return obj


def parse(obj):
    return sr.parse_seed(dump(obj)+'\n')


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='seed-lifecycle-')
        self.root = Path(self.tmp.name)
        (self.root/'docs/specs').mkdir(parents=True)
        self.rd = sr.Reader(str(self.root)); self.rd._self_repo = None
    def tearDown(self):
        self.tmp.cleanup()
    def write(self,name,obj):
        path = self.root/'docs/specs'/name
        path.write_text(dump(obj)+'\n',encoding='utf-8')
        self.rd = sr.Reader(str(self.root)); self.rd._self_repo = None  # drop cached reads
        return path
    def valid(self,obj):
        self.assertEqual(lc.validate(parse(obj)),[])
    def invalid(self,obj,needle):
        self.assertTrue(any(needle in e for e in lc.validate(parse(obj))),lc.validate(parse(obj)))

    def test_states_and_legacy_unknown(self):
        for state in ('active','paused'):
            self.valid(spec(state))
            self.assertEqual(sr.lifecycle_summary(parse(spec(state)))['state'],state)
        self.valid(spec('closed','discontinued'))
        old = spec(None); old['relations'] = {k:v for k,v in old['relations'].items() if k not in ('version','refines_map','provenance','replaces','transfers')}
        self.valid(old)
        self.assertEqual(sr.eligibility(self.rd,parse(old))['reason'],'unknown lifecycle')

    def test_invalid_combinations_and_authorization(self):
        for state,outcome in (('active','completed'),('paused','discontinued'),('closed',None),('draft',None)):
            self.assertTrue(lc.validate(parse(spec(state,outcome))))
        for field in ('reason','approved_by'):
            obj = spec(); obj['lifecycle'][field] = ''
            self.invalid(obj,field)
        obj = spec(); obj['lifecycle']['evidence']['commit'] = 'abc123'
        self.invalid(obj,'full Git SHA')

    def test_completion_requires_all_nonwithdrawn_items(self):
        obj = spec('closed','completed',withdrawn=['constraint-2'])
        obj['lifecycle']['evidence'] = {'commit':'a'*40,'items':[{'id':i,'refs':['code.py:2']} for i in ('constraint-1','acceptance-1')]}
        self.valid(obj)
        obj['lifecycle']['evidence']['items'].pop()
        self.invalid(obj,'lacks evidence')
        obj['relations']['transfers'] = [{'seed':'docs/specs/next.yaml','items':['acceptance-1']}]
        self.invalid(obj,'lacks evidence')

    def test_withdrawals_unique_and_original_ids(self):
        obj = spec(withdrawn=['missing'])
        self.invalid(obj,'undefined item')
        obj = spec(withdrawn=['constraint-1','constraint-1'])
        self.invalid(obj,'repeats item')
        ids = ['constraint-1','constraint-2','acceptance-1']
        self.invalid(spec(withdrawn=ids),'all-withdrawn')
        self.valid(spec('closed','discontinued',withdrawn=ids))
        obj = spec(); obj['lifecycle']['evidence']['items'] = [{'id':'constraint-1','refs':[]}]
        self.invalid(obj,'must not be empty')
        obj['lifecycle']['evidence']['items'] = [{'id':'constraint-1','refs':['a']},{'id':'constraint-1','refs':['b']}]
        self.invalid(obj,'repeats item')

    def test_transition_resume_and_reparent_require_new_approval(self):
        before,after = spec('paused'),spec()
        self.assertIn('new explicit approval', ' '.join(lc.transition(parse(before),parse(after))))
        after['lifecycle']['approved_by'] = 'user resume message 2'
        self.assertEqual(lc.transition(parse(before),parse(after)),[])
        before,after = spec(),spec(parent='docs/specs/new.yaml')
        self.assertTrue(lc.transition(parse(before),parse(after)))
        after['lifecycle']['approved_by'] = 'user reparent message 3'
        self.assertEqual(lc.transition(parse(before),parse(after)),[])

    def test_closed_immutable_semantic_only(self):
        before = spec('closed','discontinued')
        rendered = dump(before)+'\n'
        self.assertEqual(lc.transition(sr.parse_seed(rendered),sr.parse_seed('# extra comment\n'+rendered)),[])
        for field,value in (('state','active'),('outcome','completed'),('approved_by','changed'),('reason','changed')):
            after = copy.deepcopy(before); after['lifecycle'][field] = value
            self.assertTrue(lc.transition(parse(before),parse(after)))
        after = copy.deepcopy(before); after['constraints'][0]['description'] = 'changed'
        self.assertTrue(lc.transition(parse(before),parse(after)))

    def test_withdrawal_preserves_requirements(self):
        before,after = spec(),spec(withdrawn=['constraint-1'])
        after['lifecycle']['approved_by'] = 'user withdrawal message 2'
        self.assertEqual(lc.transition(parse(before),parse(after)),[])
        after['constraints'][0]['description'] = 'Dropped requirement'
        self.assertIn('preserve original', ' '.join(lc.transition(parse(before),parse(after))))
        before = spec(withdrawn=['constraint-1']); after = copy.deepcopy(before)
        after['constraints'][0]['description'] = 'changed'
        self.assertIn('withdrawn requirement', ' '.join(lc.transition(parse(before),parse(after))))

    def test_malformed_structures_fail_visible(self):
        raw = dump(spec())+'\n'
        for bad in (raw.replace('state: "active"','state: &alias active'),
                    raw.replace('withdrawn: []','withdrawn: {id: constraint-1}'),
                    raw.replace('state: "active"','state: "active"\n  state: "paused"'),
                    raw.replace('lifecycle:\n','lifecycle: []\n'),
                    raw.replace('children: []','children: [unclosed')):
            self.assertTrue(lc.validate(sr.parse_seed(bad)),bad)
        for value in (None,[],42):
            obj = spec(); obj['lifecycle']['evidence'] = value
            self.assertTrue(lc.validate(parse(obj)))

    def test_exact_generation_and_legacy_latest(self):
        closed = spec('closed','discontinued')
        self.write('parent.yaml',closed); self.write('parent-v2.yaml',spec())
        self.assertEqual(self.rd.load((None,'docs/specs/parent.yaml')).loc[1],'docs/specs/parent.yaml')
        old = spec(None); old['relations'] = {k:v for k,v in old['relations'].items() if k not in ('version','refines_map','provenance','replaces','transfers')}
        self.write('old.yaml',old); self.write('old-v2.yaml',spec())
        self.assertEqual(self.rd.load((None,'docs/specs/old.yaml')).loc[1],'docs/specs/old-v2.yaml')
        self.assertEqual(self.rd.load((None,'docs/specs/old.yaml'),True).loc[1],'docs/specs/old.yaml')
        child = spec(parent='docs/specs/old.yaml',refines=['constraint-1'])
        path = self.write('child.yaml',child)
        data = sr.walk(str(path)); node = next(n for n in data['nodes'] if n['relation']=='ancestor')
        self.assertEqual(node['key'],'docs/specs/old.yaml')

    def test_withdrawn_acceptance_holds_whole_child(self):
        for version in (2,3):
            with self.subTest(version=version):
                self.write('p.yaml',spec(withdrawn=['acceptance-1'],version=version))
                child = spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],version=version)
                gate = sr.eligibility(self.rd,parse(child))
                self.assertFalse(gate['eligible']); self.assertTrue(gate['review_required'])
                self.assertEqual(gate['reason'],'withdrawn parent acceptance; child review required')
                # The whole child is held; nothing is pruned item by item.
                self.assertEqual(gate['excluded_items'],sorted(parse(child).item_map))
        # Withdrawn parent constraints never hold a child that refines an unwithdrawn acceptance.
        self.write('p.yaml',spec(withdrawn=['constraint-1']))
        child = spec(parent='docs/specs/p.yaml',refines=['acceptance-1','constraint-1'])
        gate = sr.eligibility(self.rd,parse(child))
        self.assertTrue(gate['eligible']); self.assertFalse(gate['review_required'])
        self.assertEqual(gate['excluded_items'],[])
        # A withdrawn acceptance among several refined ids still holds the child.
        self.write('p.yaml',spec(withdrawn=['acceptance-1']))
        child = spec(parent='docs/specs/p.yaml',refines=['constraint-2','acceptance-1'])
        self.assertTrue(sr.eligibility(self.rd,parse(child))['review_required'])

    def test_version2_constraint_only_child_is_a_reference(self):
        whole = spec('closed','discontinued',withdrawn=['constraint-1','constraint-2','acceptance-1'])
        for parent in (whole,spec(withdrawn=['constraint-1']),spec(withdrawn=['acceptance-1'])):
            self.write('p.yaml',parent)
            for refines in (['constraint-1'],[]):
                child = spec(parent='docs/specs/p.yaml',refines=refines)
                self.assertFalse(parse(child).is_child_edge())
                gate = sr.eligibility(self.rd,parse(child))
                self.assertEqual((gate['eligible'],gate['review_required'],gate['reason']),(True,False,'active'))
        # Even a missing parent does not hold a reference edge.
        child = spec(parent='docs/specs/missing.yaml',refines=['constraint-1'])
        self.assertTrue(sr.eligibility(self.rd,parse(child))['eligible'])
        # Legacy ac<N> ids count as acceptance ids.
        self.assertTrue(sr.parse_seed('relations:\n  version: 2\n  parent: docs/specs/p.yaml\n  refines: [ac1]\n').is_child_edge())
        self.assertFalse(sr.parse_seed('relations:\n  version: 2\n  parent: docs/specs/p.yaml\n  refines: [c1]\n').is_child_edge())

    def test_whole_discontinued_child_review_and_full_graph(self):
        parent = spec('closed','discontinued',withdrawn=['constraint-1','constraint-2','acceptance-1'],children=['docs/specs/c.yaml'])
        child = spec(parent='docs/specs/p.yaml',refines=['acceptance-1'])
        self.write('p.yaml',parent); path = self.write('c.yaml',child)
        data = sr.walk(str(path)); self.assertEqual(len(data['nodes']),2)
        self.assertTrue(data['nodes'][0]['eligibility']['review_required'])
        self.assertEqual(data['nodes'][1]['item_desc'],{})
        fields = '\n'.join(sr.render_walk_text(data))
        for field in ('lifecycle_state=closed','eligible=false','review_required=true','excluded_items='):
            self.assertIn(field,fields)

    def test_withdrawal_marks_resumable_inactive_children_for_review(self):
        whole = spec('closed','discontinued',withdrawn=['constraint-1','constraint-2','acceptance-1'],children=['docs/specs/c.yaml'])
        partial = spec('closed','discontinued',withdrawn=['constraint-1'],children=['docs/specs/c.yaml'])
        partial_acceptance = spec('closed','discontinued',withdrawn=['acceptance-1'],children=['docs/specs/c.yaml'])
        for state,outcome in ((None,None),('paused',None),('closed','discontinued')):
            for parent,refines,review in ((whole,['acceptance-1'],True),(partial_acceptance,['acceptance-1'],True),(partial,['acceptance-1'],False)):
                with self.subTest(state=state,outcome=outcome,withdrawn=len(parent['lifecycle']['withdrawn']),refines=refines):
                    self.write('p.yaml',parent)
                    child = spec(state,outcome,parent='docs/specs/p.yaml',refines=refines)
                    path = self.write('c.yaml',child); before = path.read_bytes()
                    node = sr.walk(str(path))['nodes'][0]
                    self.assertFalse(node['eligibility']['eligible'])
                    # Closed children are finished history; only paused/unknown ones need review before resuming.
                    self.assertEqual(node['eligibility']['review_required'],review and state != 'closed')
                    self.assertEqual(path.read_bytes(),before)
                    self.assertEqual(node['lifecycle']['state'],state or 'unknown')

    def test_inactive_child_shares_parent_guards(self):
        child = spec('paused',parent='docs/specs/missing.yaml',refines=['acceptance-1'])
        gate = sr.eligibility(self.rd,parse(child))
        self.assertEqual(gate['reason'],'parent unavailable'); self.assertTrue(gate['review_required'])
        self.write('p.yaml',spec('closed','discontinued',withdrawn=['acceptance-1'],children=['docs/specs/c.yaml']))
        path = self.write('c.yaml',spec('paused',parent='docs/specs/p.yaml',refines=['acceptance-1']))
        gate = sr.walk(str(path))['nodes'][0]['eligibility']
        self.assertEqual(gate['reason'],'withdrawn parent acceptance; child review required'); self.assertTrue(gate['review_required'])
        # An unknown-lifecycle parent holds only automatic candidacy, not a paused child.
        self.write('p.yaml',spec(None,children=['docs/specs/c.yaml']))
        self.assertFalse(sr.walk(str(path))['nodes'][0]['eligibility']['review_required'])

    def test_missing_and_malformed_parent_hold(self):
        child = spec(parent='docs/specs/missing.yaml',refines=['acceptance-1'])
        self.assertEqual(sr.eligibility(self.rd,parse(child))['reason'],'parent unavailable')
        parent = spec(); parent['lifecycle']['approved_by'] = ''
        self.write('p.yaml',parent); child['relations']['parent'] = 'docs/specs/p.yaml'
        self.assertEqual(sr.eligibility(self.rd,parse(child))['reason'],'parent lifecycle invalid')

    def test_relations_validation(self):
        for name,row,needle in [('refines_map',{'parent_item':'missing','child_items':['constraint-1']},'exist in refines'),
                              ('transfers',{'seed':'docs/specs/t.yaml','items':['missing']},'undefined own'),
                              ('provenance',{'seed':'docs/specs/s.yaml','commit':'short','items':['constraint-1']},'full Git SHA')]:
            obj = spec(); obj['relations'][name] = [row]
            self.invalid(obj,needle)
        obj = spec(); obj['relations']['children'] = ['docs/specs/x']
        self.invalid(obj,'exact Seed')

    def test_independent_seed_cannot_keep_parent_item_references(self):
        self.valid(spec())
        linked = spec(); linked['relations']['link_reason'] = 'stale parent rationale'
        for obj in (spec(refines=['constraint-1']),
                    spec(mapping=[{'parent_item':'constraint-1','child_items':['constraint-2']}]),linked):
            self.invalid(obj,'require a parent')
            gate = sr.eligibility(self.rd,parse(obj))
            self.assertFalse(gate['eligible']); self.assertTrue(gate['review_required'])
            lines,code = sr.cmd_check(self.rd,'docs/specs/s.yaml',parse(obj))
            self.assertEqual(code,1); self.assertIn('require a parent',' '.join(lines))
        self.valid(spec(parent='docs/specs/p.yaml',refines=['constraint-1'],
                        mapping=[{'parent_item':'constraint-1','child_items':['constraint-2']}]))

    def test_partial_discontinued_and_grandchild_propagation(self):
        parent = spec('closed','discontinued',withdrawn=['constraint-1'],children=['docs/specs/c.yaml'])
        self.write('p.yaml',parent)
        unrelated = spec(parent='docs/specs/p.yaml',refines=['constraint-2'])
        self.assertTrue(sr.eligibility(self.rd,parse(unrelated))['eligible'])
        child = spec(parent='docs/specs/p.yaml',refines=['acceptance-1','constraint-2'])
        child['relations']['children'] = ['docs/specs/g.yaml']
        self.write('c.yaml',child)
        grandchild = spec(parent='docs/specs/c.yaml',refines=['acceptance-1'])
        gpath = self.write('g.yaml',grandchild)
        gate = sr.walk(str(gpath))['nodes'][0]['eligibility']
        # An ancestor's excluded items no longer propagate: only its review hold does.
        self.assertEqual(gate['excluded_items'],[])
        self.assertTrue(gate['eligible']); self.assertFalse(gate['review_required'])
        # When the middle Seed is held for a withdrawn acceptance, the grandchild is held too.
        self.write('p.yaml',spec('closed','discontinued',withdrawn=['acceptance-1'],children=['docs/specs/c.yaml']))
        gate = sr.walk(str(gpath))['nodes'][0]['eligibility']
        self.assertEqual(gate['reason'],'ancestor review required')
        self.assertFalse(gate['eligible']); self.assertTrue(gate['review_required'])

    def test_depends_on_item_fragment(self):
        # #885: `path.yaml#acceptance-1` names one predecessor item; an empty fragment is an error.
        ok = spec(version=3); ok['relations']['depends_on'] = ['docs/specs/a.yaml#acceptance-1']
        self.valid(ok)
        bad = spec(version=3); bad['relations']['depends_on'] = ['docs/specs/a.yaml#']
        self.invalid(bad,'relations.depends_on item fragment must not be empty')

    def test_version3_relations_validation(self):
        self.valid(spec(version=3))
        self.valid(spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],version=3))
        self.invalid(spec(parent='docs/specs/p.yaml',version=3),'at least one parent acceptance')
        self.invalid(spec(parent='docs/specs/p.yaml',refines=['constraint-1'],version=3),'only acceptance ids')
        self.invalid(spec(parent='docs/specs/p.yaml',refines=['acceptance-1','constraint-1'],version=3),'only acceptance ids')
        self.invalid(spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],version=3,
                          mapping=[{'parent_item':'acceptance-1','child_items':['constraint-1']}]),'not used in version 3')
        obj = spec(version=3); obj['relations']['refines_map'] = []
        self.invalid(obj,'not used in version 3')
        # Version 2 keeps its old validation, including refines_map format.
        self.valid(spec(parent='docs/specs/p.yaml',refines=['constraint-1']))
        self.invalid(spec(parent='docs/specs/p.yaml',refines=['constraint-1'],
                          mapping=[{'parent_item':'missing','child_items':['constraint-1']}]),'exist in refines')
        self.invalid(spec(version=4),'must be 2 or 3')
        gate = sr.eligibility(self.rd,parse(spec(parent='docs/specs/p.yaml',version=3)))
        self.assertEqual((gate['eligible'],gate['reason']),(False,'invalid lifecycle'))

    def completed_parent(self,children,approved='user completion message 9'):
        obj = spec('closed','completed',children=children)
        obj['lifecycle']['approved_by'] = approved
        obj['lifecycle']['evidence'] = {'commit':'a'*40,'items':[{'id':i,'refs':['code.py:1']} for i in ('constraint-1','constraint-2','acceptance-1')]}
        return obj

    def test_parent_completion_requires_closed_children(self):
        rel = 'docs/specs/p.yaml'
        before = parse(spec(children=['docs/specs/c.yaml']))
        after = parse(self.completed_parent(['docs/specs/c.yaml']))
        for version in (2,3):
            with self.subTest(version=version):
                for state,outcome,ok in (('active',None,False),('paused',None,False),(None,None,False),
                                         ('closed','discontinued',True),('closed','completed',True)):
                    self.write('c.yaml',spec(state,outcome,parent=rel,refines=['acceptance-1'],version=version))
                    errors = lc.transition(before,after,self.rd,rel)
                    self.assertEqual(errors == [],ok,(state,errors))
                    if not ok:
                        self.assertIn('docs/specs/c.yaml',errors[0])
                        self.assertIn(state or 'unknown',errors[0])
        # Without a reader (older callers) the child check is skipped.
        self.write('c.yaml',spec(parent=rel,refines=['acceptance-1']))
        self.assertEqual(lc.transition(before,after),[])
        # Only a completion is gated: staying open or discontinuing is not.
        self.assertEqual(lc.transition(before,parse(spec(children=['docs/specs/c.yaml'])),self.rd,rel),[])

    def test_parent_completion_ignores_reference_other_repo_and_unrelated_children(self):
        rel = 'docs/specs/p.yaml'
        before = parse(spec(children=['docs/specs/ref.yaml','docs/specs/empty.yaml','docs/specs/stray.yaml','acme/other:docs/specs/x.yaml']))
        after = parse(self.completed_parent(['docs/specs/ref.yaml','docs/specs/empty.yaml','docs/specs/stray.yaml','acme/other:docs/specs/x.yaml']))
        self.write('ref.yaml',spec(parent=rel,refines=['constraint-1']))
        self.write('empty.yaml',spec(parent=rel))
        # A listed child whose parent points elsewhere is not a child edge back to this Seed.
        self.write('stray.yaml',spec(parent='docs/specs/other.yaml',refines=['acceptance-1']))
        self.assertEqual(lc.transition(before,after,self.rd,rel),[])
        # An unreadable same-repo child blocks; the other-repo child never does.
        before = parse(spec(children=['docs/specs/gone.yaml']))
        errors = lc.transition(before,parse(self.completed_parent(['docs/specs/gone.yaml'])),self.rd,rel)
        self.assertTrue(errors and 'gone.yaml' in errors[0],errors)

    def test_closed_parent_with_open_child_still_validates(self):
        rel = 'docs/specs/p.yaml'
        closed = self.completed_parent(['docs/specs/c.yaml'])
        self.write('c.yaml',spec(parent=rel,refines=['acceptance-1']))
        self.assertEqual(lc.validate(parse(closed)),[])
        self.write('p.yaml',closed)
        self.assertEqual(lc.validate(parse(closed),str(self.root)),['evidence commit unavailable: '+'a'*40])
        # Re-judging an already closed Seed never applies the child rule.
        self.assertEqual(lc.transition(parse(closed),parse(closed),self.rd,rel),[])

    def test_cli_applies_parent_completion_rule(self):
        rel = 'docs/specs/p.yaml'
        self.write('c.yaml',spec(parent=rel,refines=['acceptance-1']))
        self.write('before.yaml',spec(children=['docs/specs/c.yaml']))
        obj = self.completed_parent(['docs/specs/c.yaml']); obj['lifecycle']['evidence']['commit'] = None
        path = self.write('p.yaml',obj)
        run = lambda: subprocess.run([sys.executable,str(SCRIPTS/'seed-lifecycle.py'),'check',str(path),
                                      '--before',str(self.root/'docs/specs/before.yaml'),'--json'],
                                     capture_output=True,text=True)
        out = json.loads(run().stdout)
        self.assertTrue(any('parent cannot close while child is not closed' in e for e in out['errors']),out)
        self.write('c.yaml',spec('closed','discontinued',parent=rel,refines=['acceptance-1']))
        out = json.loads(run().stdout)
        self.assertFalse(any('child' in e for e in out['errors']),out)

    def test_closed_literal_contents_are_immutable(self):
        raw = dump(spec('closed','discontinued')).replace('description: "First original requirement"',
              'description: |\n      # requirement content\n      actual text')
        before = sr.parse_seed(raw)
        after = sr.parse_seed(raw.replace('# requirement content','# changed requirement'))
        self.assertTrue(lc.transition(before,after))

    def test_exact_crossrepo_provenance_read(self):
        obj = spec(); obj['relations']['provenance'] = [{'seed':'acme/source:docs/specs/source.yaml','commit':'b'*40,'items':['constraint-1']}]
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        endpoints = []
        import base64
        def api(endpoint):
            endpoints.append(endpoint)
            if '/git/commits/' in endpoint:
                return {'sha':'b'*40},None
            return {'encoding':'base64','content':base64.b64encode(dump(spec()).encode()).decode()},None
        rd._gh_api = api
        self.assertEqual(sr.validate_provenance(rd,parse(obj),None),[])
        self.assertEqual(endpoints,['repos/acme/source/git/commits/'+'b'*40,
                                    'repos/acme/source/contents/docs/specs/source.yaml?ref='+'b'*40])

    def test_crossrepo_provenance_rejects_unconfirmed_commit(self):
        obj = spec(); obj['relations']['provenance'] = [{'seed':'acme/source:docs/specs/source.yaml','commit':'b'*40,'items':['constraint-1']}]
        for response,error in ((None,'not a commit'),({'sha':'c'*40},None),({},None)):
            with self.subTest(response=response):
                rd = sr.Reader(str(self.root)); rd._self_repo = None
                endpoints = []
                def api(endpoint,endpoints=endpoints,response=response,error=error):
                    endpoints.append(endpoint); return response,error
                rd._gh_api = api
                self.assertIn('historical source unavailable',' '.join(sr.validate_provenance(rd,parse(obj),None)))
                self.assertEqual(endpoints,['repos/acme/source/git/commits/'+'b'*40])

    def test_incoming_child_link_holds_even_duplicate_route(self):
        parent = spec('closed','discontinued',withdrawn=['constraint-1','constraint-2','acceptance-1'],children=['docs/specs/c.yaml'])
        child = spec(parent=None)
        start = spec(children=['docs/specs/p.yaml']); start['relations']['depends_on'] = ['docs/specs/c.yaml']
        parent['relations']['parent'] = 'docs/specs/s.yaml'
        self.write('p.yaml',parent); self.write('c.yaml',child); path = self.write('s.yaml',start)
        data = sr.walk(str(path))
        cnode = next(n for n in data['nodes'] if n['key']=='docs/specs/c.yaml')
        self.assertFalse(cnode['eligibility']['eligible'])
        self.assertTrue(cnode['eligibility']['review_required'])
        self.assertEqual(cnode['eligibility']['reason'],'incoming child relation invalid')
        self.assertTrue(data['dups'])

    def test_invalid_incoming_hold_reaches_grandchildren(self):
        parent = spec('closed','discontinued',withdrawn=['constraint-1','constraint-2','acceptance-1'],children=['docs/specs/c.yaml'])
        child = spec(children=['docs/specs/g.yaml'])
        grandchild = spec(parent='docs/specs/c.yaml',refines=['acceptance-1'])
        path = self.write('p.yaml',parent)
        self.write('c.yaml',child); self.write('g.yaml',grandchild)
        nodes = {n['key']:n for n in sr.walk(str(path))['nodes']}
        for name in ('c','g'):
            gate = nodes['docs/specs/'+name+'.yaml']['eligibility']
            self.assertFalse(gate['eligible']); self.assertTrue(gate['review_required'])
        self.assertEqual(nodes['docs/specs/g.yaml']['eligibility']['reason'],'ancestor review required')

    def test_unknown_ancestor_review_propagates_full_hold(self):
        parent = spec(None); parent['relations'] = {k:v for k,v in parent['relations'].items() if k not in ('version','refines_map','provenance','replaces','transfers')}; parent['relations']['children'] = ['docs/specs/c.yaml']
        child = spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],children=['docs/specs/g.yaml'])
        grandchild = spec(parent='docs/specs/c.yaml',refines=['acceptance-1'])
        self.write('p.yaml',parent); self.write('c.yaml',child); path = self.write('g.yaml',grandchild)
        gate = sr.walk(str(path))['nodes'][0]['eligibility']
        self.assertFalse(gate['eligible']); self.assertTrue(gate['review_required'])
        self.assertEqual(set(gate['excluded_items']),{'constraint-1','constraint-2','acceptance-1'})

    def test_transfers_and_replaces_require_matching_provenance(self):
        source = spec('closed','discontinued')
        source['relations']['transfers'] = [{'seed':'docs/specs/t.yaml','items':['constraint-1']}]
        self.write('s.yaml',source); self.write('t.yaml',spec())
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        lines,code = sr.cmd_check(rd,'docs/specs/s.yaml',parse(source))
        self.assertEqual(code,1); self.assertIn('destination lacks pinned provenance',' '.join(lines))
        target = spec(); target['relations']['replaces'] = ['docs/specs/s.yaml']
        lines,code = sr.cmd_check(rd,'docs/specs/t.yaml',parse(target))
        self.assertEqual(code,1); self.assertIn('without pinned provenance',' '.join(lines))
        target['relations']['provenance'] = [{'seed':'docs/specs/wrong.yaml','commit':'a'*40,'items':['constraint-1']}]
        self.write('t.yaml',target)
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        lines,code = sr.cmd_check(rd,'docs/specs/s.yaml',parse(source))
        self.assertEqual(code,1); self.assertIn('historical source unavailable',' '.join(lines))

    def test_malformed_transfer_fails_without_crash(self):
        obj = spec(); obj['relations']['transfers'] = [{'seed':'docs/specs/t.yaml','items':[{'unexpected':'value'}]}]
        self.write('t.yaml',spec())
        lines,code = sr.cmd_check(self.rd,'docs/specs/s.yaml',parse(obj))
        self.assertEqual(code,1); self.assertIn('nonempty strings',' '.join(lines))

    def test_metadata_body_omission_explicit_read(self):
        for state,outcome in ((None,None),('paused',None),('closed','discontinued')):
            with self.subTest(state=state):
                path = self.write('s.yaml',spec(state,outcome))
                before = path.read_bytes()
                for cmd in ('metadata','read'):
                    p = subprocess.run([sys.executable,str(SCRIPTS/'seed-relations.py'),cmd,str(path),'--json'],capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stderr)
                    data = json.loads(p.stdout)
                    self.assertEqual(data['title'],'Fixture'); self.assertEqual(data['goal'],'Short goal')
                    self.assertFalse(data['eligibility']['eligible'])
                    self.assertEqual('requirements' in data,cmd=='read')
                    if cmd == 'metadata':
                        self.assertNotIn('First original requirement',p.stdout)
                self.assertEqual(path.read_bytes(),before)

    def test_guard_lifecycle_and_journal(self):
        before,after = spec(),spec('paused')
        payload = {'tool_name':'Write','tool_input':{'file_path':str(self.root/'docs/specs/s.yaml'),'content':dump(after)}}
        self.assertIn('approval',guard.decide(payload,read_file=lambda _:dump(before)))
        after['lifecycle']['approved_by'] = 'user pause message 2'; payload['tool_input']['content'] = dump(after)
        self.assertEqual(guard.decide(payload,read_file=lambda _:dump(before)),'')
        after['constraints'][0]['description'] = 'changed'; payload['tool_input']['content'] = dump(after)
        self.assertIn('preserve original',guard.decide(payload,read_file=lambda _:dump(before)))
        payload['tool_input']['content'] = dump(before)+'\n# 2026-10-07 작업 완료\n'
        self.assertTrue(guard.decide(payload,read_file=lambda _:dump(before)))
        closed = spec('closed','discontinued'); after = copy.deepcopy(closed); after['lifecycle']['state']='active';after['lifecycle']['outcome']=None
        payload['tool_input']['content'] = dump(after)
        self.assertIn('immutable',guard.decide(payload,read_file=lambda _:dump(closed)))

    def test_historical_provenance_and_completed_record_pinned(self):
        # Create historical objects only in a disposable fixture repository.
        def git(*args,input=None):
            return subprocess.run(['git','-C',str(self.root),*args],input=input,capture_output=True,text=True,check=True).stdout.strip()
        git('init','-q'); git('config','user.name','Fixture'); git('config','user.email','fixture@example.invalid')
        source = spec(None); source['relations'] = {k:v for k,v in source['relations'].items() if k not in ('version','refines_map','provenance','replaces','transfers')}
        blob = git('hash-object','-w','--stdin',input=dump(source))
        tree = git('mktree',input='100644 blob '+blob+'\tsource.yaml\n')
        commit = git('commit-tree',tree,input='Historical fixture\n')
        self.root.joinpath('source.yaml').write_text('constraints:\n  - id: other\n')
        target = spec(); target['relations']['provenance'] = [{'seed':'source.yaml','commit':commit,'items':['constraint-1']}]
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        self.assertEqual(sr.validate_provenance(rd,parse(target),None),[])
        invalid = copy.deepcopy(target); invalid['relations']['provenance'][0]['commit'] = tree
        self.assertIn('not a commit object',' '.join(sr.validate_provenance(rd,parse(invalid),None)))
        target['relations']['provenance'][0]['items'] = ['other']
        self.assertIn('historical source lacks',' '.join(sr.validate_provenance(rd,parse(target),None)))
        target['relations']['provenance'][0]['commit'] = 'f'*40
        self.assertIn('unavailable',' '.join(sr.validate_provenance(rd,parse(target),None)))
        completed = spec('closed','completed')
        completed['lifecycle']['evidence'] = {'commit':commit,'items':[{'id':i,'refs':['source.yaml:1']} for i in ('constraint-1','constraint-2','acceptance-1')]}
        self.assertEqual(lc.validate(parse(completed),str(self.root)),[])
        git('update-ref','refs/heads/later',git('commit-tree',tree,'-p',commit,input='Later unrelated changes\n'))
        self.assertEqual(lc.validate(parse(completed),str(self.root)),[])
        completed['lifecycle']['evidence']['commit'] = 'f'*40
        self.assertIn('unavailable',' '.join(lc.validate(parse(completed),str(self.root))))

    def legacy(self,**kw):
        obj = spec(None,**kw)
        obj['relations'] = {k:v for k,v in obj['relations'].items() if k not in ('version','refines_map','provenance','replaces','transfers')}
        return obj

    def test_detach_and_relink_must_pin_previous_parent(self):
        # Independent transitions and relinks used to pass while dropping the previous parent.
        def git(*args,input=None):
            return subprocess.run(['git','-C',str(self.root),*args],input=input,capture_output=True,text=True,check=True).stdout.strip()
        git('init','-q'); git('config','user.name','Fixture'); git('config','user.email','fixture@example.invalid')
        parent = spec(children=['docs/specs/c.yaml'])
        self.write('p.yaml',parent); git('add','-A'); git('commit','-qm','parent')
        commit = git('rev-parse','HEAD')
        before = parse(spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],mapping=[{'parent_item':'acceptance-1','child_items':['acceptance-1']}]))
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        pin = {'seed':'docs/specs/p.yaml','commit':commit,'items':['acceptance-1']}
        detach = spec(); detach['lifecycle']['approved_by'] = 'user detach message 2'
        self.assertIn('pin previous parent docs/specs/p.yaml',' '.join(lc.transition(before,parse(detach),rd)))
        for field,value in (('seed','docs/specs/other.yaml'),('commit',commit[:12]),('items',['constraint-2'])):
            bad = copy.deepcopy(detach); bad['relations']['provenance'] = [dict(pin,**{field:value})]
            self.assertTrue(lc.transition(before,parse(bad),rd),field)
        detach['relations']['provenance'] = [pin]
        self.assertEqual(lc.transition(before,parse(detach),rd),[])
        self.assertEqual(sr.validate_provenance(rd,parse(detach),None),[])
        # The edit guard applies the same rule to a Write of the detached Seed.
        prior = dump(spec(parent='docs/specs/p.yaml',refines=['acceptance-1'],mapping=[{'parent_item':'acceptance-1','child_items':['acceptance-1']}]))
        payload = {'tool_name':'Write','tool_input':{'file_path':str(self.root/'docs/specs/c.yaml'),'content':dump(detach)}}
        self.assertEqual(guard.decide(payload,read_file=lambda _:prior),'')
        unpinned = copy.deepcopy(detach); unpinned['relations']['provenance'] = []
        payload['tool_input']['content'] = dump(unpinned)
        self.assertIn('pin previous parent',guard.decide(payload,read_file=lambda _:prior))
        # A version 2 reference edge (constraint-only refines) never composed its parent: dropping it pins nothing.
        reference = parse(spec(parent='docs/specs/p.yaml',refines=['constraint-1']))
        dropped = spec(); dropped['lifecycle']['approved_by'] = 'user reference cleanup 2'
        self.assertEqual(lc.transition(reference,parse(dropped),rd),[])
        # A relink keeps the same pin and still needs both directions of the new edge.
        relink = spec(parent='docs/specs/q.yaml',refines=['acceptance-1'],mapping=[{'parent_item':'acceptance-1','child_items':['acceptance-1']}])
        relink['lifecycle']['approved_by'] = 'user relink message 2'
        self.assertTrue(lc.transition(before,parse(relink),rd))
        relink['relations']['provenance'] = [pin]
        self.assertEqual(lc.transition(before,parse(relink),rd),[])
        self.write('q.yaml',spec()); self.write('c.yaml',relink)
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        self.assertEqual(sr.cmd_check(rd,'docs/specs/c.yaml',parse(relink))[1],1)
        self.write('q.yaml',spec(children=['docs/specs/c.yaml']))
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        lines,code = sr.cmd_check(rd,'docs/specs/c.yaml',parse(relink))
        self.assertEqual(code,0,lines)

    def test_legacy_previous_parent_pins_the_resolved_generation(self):
        # Legacy parents keep latest -vN resolution; the pin must name that file, never a guess.
        self.write('p.yaml',self.legacy()); self.write('p-v2.yaml',self.legacy())
        before = parse(self.legacy(parent='docs/specs/p.yaml',refines=['acceptance-1']))
        rd = sr.Reader(str(self.root)); rd._self_repo = None
        after = spec()
        after['relations']['provenance'] = [{'seed':'docs/specs/p.yaml','commit':'a'*40,'items':['acceptance-1']}]
        self.assertIn('pin previous parent docs/specs/p-v2.yaml',' '.join(lc.transition(before,parse(after),rd)))
        self.assertIn('repository reader',' '.join(lc.transition(before,parse(after))))
        after['relations']['provenance'][0]['seed'] = 'docs/specs/p-v2.yaml'
        self.assertEqual(lc.transition(before,parse(after),rd),[])

if __name__ == '__main__':
    os.environ['GH_BIN'] = '/nonexistent/gh'
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print(f'OK: all {result.testsRun} Seed lifecycle regression fixtures passed')
    sys.exit(0 if result.wasSuccessful() else 1)
