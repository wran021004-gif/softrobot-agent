"""Saved evidence and mocked transport boundaries only: no provider or backend calls."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extensions.tendon_family import route
from extensions.tendon_family.candidate import candidate_facts, check_design_statement
from tools.platform_host import Host
from tools.platform_models import action_signature, payload_for
from tools.platform_store import encode
from tools.platform_tools import retain_evidence
from tools.state_io import read

SOURCE=Path('runs/stage322_live_design_20260928')


class DeliveryRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host=Host(SOURCE,read(SOURCE/'workflow.json')['run_id'])
        cls.store=cls.host.store
        saved=cls.store.session(cls.host.run_id)
        cls.baseline=saved['snapshot']['input']
        cls.saved_route=saved['state']['route']
        cls.runs=[n for n in cls.saved_route['nodes'] if n['action']=='run']

    def test_facts_survive_build_run_incumbent_delivery_and_switch(self):
        node=self.runs[-1];out=self.store.artifact(node['result'])
        built_node=next(n for n in self.saved_route['nodes'] if n['node_id']==node['selection']['source_node'])
        built=self.store.artifact(built_node['result'])
        facts=route.trial_facts(self.store,self.baseline,built)
        built['candidate_facts']=facts
        self.assertEqual(route.summarize(built)['candidate_facts'],facts)
        ctx=SimpleNamespace(store=self.store,host=self.host,input=self.baseline,
            run_id=self.host.run_id,row={'parent_id':None},reg=self.host.reg)
        # Replay saved receipts into the real run projection; no execution is invoked.
        with patch.object(route,'source_node',return_value=(built_node,built)), \
             patch('extensions.tendon_family.optimization.ensure_session'), \
             patch('extensions.tendon_family.crosscheck.invoke',side_effect=[out['simulation'],{'output':out['evaluation']}]) as invoke, \
             patch.object(route,'profile_capability',return_value=None):
            current=route.run_built(ctx,SimpleNamespace(candidate_id=None),self.saved_route)
        self.assertEqual(invoke.call_count,2)
        current_facts=route.summarize(current)['candidate_facts']
        self.assertEqual(current_facts['parameters'],facts['parameters'])
        values={r['path']:r for r in current_facts['parameters']}
        near=values['components/near/length_m'];far=values['components/far/length_m']
        self.assertAlmostEqual(near['effective_value'],.159)
        self.assertAlmostEqual(near['baseline_delta'],-.001)
        self.assertEqual(far['baseline_delta'],0)
        self.assertEqual(near['unit'],'m')
        state={'nodes':[],'incumbent':None}
        route.update_incumbent(ctx,state,node,current)
        self.assertEqual(state['incumbent']['candidate_facts'],current_facts)
        child=SimpleNamespace(run_id=current['run_id'])
        with patch.object(route,'view',return_value={'limitations':[]}):
            delivered=route.delivery(ctx,state,child,current,'Provider explanation',deepcopy(current_facts))
        self.assertEqual(route.delivery_summary(delivered)['candidate_facts'],current_facts)
        self.assertTrue(delivered['design_statement_check']['accepted'])
        self.assertEqual(delivered['interpretation_status'],'prose_review_required')
        first=route.trial_facts(self.store,self.baseline,self.store.artifact(self.runs[0]['result']))
        self.assertEqual(next(r for r in first['parameters'] if '/near/' in r['path'])['effective_value'],.170)
        self.assertNotEqual(first['configuration'],current_facts['configuration'])
        self.assertNotEqual(first['execution_id'],current_facts['execution_id'])
        switched=route.view(self.host)
        switched['route']['nodes']=[n for n in switched['route']['nodes'] if n['node_id']!=self.runs[0]['node_id']]+[self.runs[0]]
        with patch.object(route,'view',return_value=switched):
            projection=route.overview(self.host)
        self.assertEqual(projection['selected_summary']['candidate_facts'],first)
        self.assertEqual(projection['incumbent']['candidate_facts'],current_facts)
        baseline=deepcopy(self.baseline)
        effective=deepcopy(self.store.artifact(current['configuration'])['effective'])
        baseline['robot']['structure']['data']['fixture_gain']=2.
        effective['robot']['structure']['data']['fixture_gain']=2.5
        baseline['policy']['candidate_builder']['parameters']['data']['parameters']['fixture_gain']={'type':'number','bounds':[1,3],'unit':'1'}
        generic=candidate_facts(baseline,{'effective':effective},current['configuration'],'alternate')
        self.assertEqual(generic['parameters'][-1],dict(path='fixture_gain',baseline_value=2.,effective_value=2.5,baseline_delta=.5,unit='1'))

    def test_saved_repeated_reads_are_retained_bounded_and_reports_deduplicated(self):
        pages=[];reads=0;identities=set()
        for action in read(SOURCE/'behavior_audit.json')['actions']:
            decision=action.get('decision') or {}
            if decision.get('tool_id')!='evidence.read':continue
            receipt=json.loads(self.store.lookup(self.host.run_id,decision['request_id'])['receipt'])
            page=self.store.artifact(receipt['output'])
            before=deepcopy(page)
            pages=retain_evidence(pages,page);reads+=1
            identities.add(pages[-1]['content_identity'])
            self.assertEqual(pages[-1]['page'],before)
            modified=deepcopy(decision);modified['arguments']['byte_limit']=999
            self.assertEqual(action_signature(decision,receipt,self.store),action_signature(modified,receipt,self.store))
            self.assertLessEqual(len(pages),3)
            self.assertLessEqual(len(encode(pages).encode('utf8')),12000)
        self.assertEqual(reads,19)
        self.assertLess(len(identities),reads)
        ctx=self.host.context();ctx['recent_evidence']=pages
        projection=ctx['route']
        self.assertEqual(len(projection['profile_reports']),1)
        selected=projection['selected_summary'];incumbent=projection['incumbent']
        self.assertEqual(selected['profile_report_summary_ref'],incumbent['profile_report_summary_ref'])
        self.assertNotIn('profile_report_summary',selected)
        with patch.object(self.host,'context',return_value=deepcopy(ctx)):
            payload=payload_for(self.host)
        self.assertLessEqual(len(encode(payload).encode('utf8')),self.baseline['policy']['model']['context_bytes'])
        self.assertEqual(json.loads(payload['messages'][-1]['content'])['recent_evidence'],pages)
        attributed=retain_evidence([],pages[-1]['page'],{'source_execution_id':'historical-execution'})
        self.assertEqual(attributed[0]['attribution']['source_execution_id'],'historical-execution')
        self.assertEqual(attributed[0]['page'],pages[-1]['page'])
        constrained=deepcopy(ctx)
        constrained['policy']['model']['context_bytes']=len(encode(payload).encode('utf8'))-100
        with patch.object(self.host,'context',return_value=constrained):
            smaller=payload_for(self.host)
        compact=json.loads(smaller['messages'][-1]['content'])
        self.assertLess(len(compact['recent_evidence']),len(pages))
        self.assertEqual(compact['route']['selected_summary']['candidate_facts'],ctx['route']['selected_summary']['candidate_facts'])
        different=deepcopy(incumbent);different['profile_report']['execution_id']='different'
        different['profile_report_summary']={'distinct':True}
        selected=deepcopy(selected);selected['profile_report_summary']={'distinct':False}
        self.assertEqual(len(route.compact_reports(dict(selected_summary=selected,incumbent=different))['profile_reports']),2)

    def test_values_deltas_and_binding_checked_independently_of_prose(self):
        facts=route.trial_facts(self.store,self.baseline,self.store.artifact(self.runs[-1]['result']))
        index=next(i for i,r in enumerate(facts['parameters']) if '/near/' in r['path'])
        correct=deepcopy(facts);correct['parameters'][index]['baseline_delta']=-.001
        self.assertTrue(check_design_statement(facts,correct)['accepted'])
        wrong=deepcopy(correct);wrong['parameters'][index].update(effective_value=.150,baseline_delta=-.010)
        self.assertFalse(check_design_statement(facts,wrong)['accepted'])
        wrong=deepcopy(correct);wrong['configuration']={'artifact_id':'0'*64}
        self.assertFalse(check_design_statement(facts,wrong)['accepted'])
        wrong=deepcopy(correct);wrong['parameters'][0]['unit']='mm'
        self.assertFalse(check_design_statement(facts,wrong)['accepted'])
        self.assertFalse(check_design_statement(facts,None)['accepted'])
        # Structured agreement cannot accept contradictory or unreviewed prose.
        old=read(SOURCE/'provider_interpretation_review.json')
        self.assertFalse(old['correct_use_of_current_evidence'])
        self.assertTrue(check_design_statement(facts,correct)['accepted'])
        self.assertIn('0.15 m',(SOURCE/'model_final.txt').read_text(encoding='utf8'))


if __name__=='__main__':unittest.main()
