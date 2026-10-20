"""Cold initialization and archived errors; no Provider or scientific solves."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from uuid import uuid4
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research.config import ROOT
from tools.research.core import prepare, read_evidence
from tools.research.state import state
from tools.research.contracts import Plan, ControlSeedRequest
from tools.research.evidence_policy import admit_decision
from tools.research.research_context import import_history, context, decision_brief, compact_evidence
from tools.research.agent import plan_schema
from tests.research.s125_wire_audit import audit, reproduce


def cold_host(mode='formal_research'):
    """Unique isolated engineering grant; never reuse a formal Study budget."""
    c=json.loads((ROOT/'configs/research/study_s125_cold.json').read_text())
    c['study_id']='s125-preflight-'+uuid4().hex
    c['mode']=mode
    path=ROOT/'runs'/c['study_id'];path.mkdir(parents=True)
    for key in ('defaults','family_space','control','task'):
        c[key]=str((ROOT/'configs/research'/c[key]).resolve())
    # Config owner requires defaults adjacent: temporary leaf in the config folder.
    spec=ROOT/'configs/research'/('._'+c['study_id']+'.json')
    spec.write_text(json.dumps(c),encoding='utf8')
    try:return prepare(spec,directory=path)
    finally:spec.unlink()


class S125ContractTests(unittest.TestCase):
    def test_cold_store_and_initialization(self):
        from tools.research.design import generate_candidate
        from tools.research.physical_replay import seed_control
        from tools.research.mechanics import warm_start
        from tools.research.contracts import MechanicsRequest
        h=cold_host();import_history(h);s=state(h)
        for key in ('research_history','research_mathematics','control_initializations','candidates'):
            self.assertFalse(s.get(key))
        self.assertIsNone(s['reference_candidate'])
        self.assertFalse(s['spec']['implementation_scaffold']['scientific_candidate'])
        self.assertEqual(s['pilot']['framework_session_id'],h.run_id)
        self.assertFalse((h.store.root/'framework_sessions').exists())
        current=context(h);self.assertIsNone(decision_brief(current)['best_valid'])
        self.assertIn('generate',current['actions'])
        archived=audit()['errors'][0]['tool_use']['input']['reference']
        with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING'):
            read_evidence(h,dict(reference=archived))
        base=dict(hypothesis='Fixture legal generation, not scientific evidence',
            expected_observation='Generated candidate',weakening_observation='Invalid request',
            fixed_conditions='Frozen domain',stopping_condition='No scientific solve',interpretation='Unmeasured')
        request=dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],
            segment_count=2,tendon_count=4)
        p=Plan(action='generate',generation=request,decision=dict(hypothesis_id='cold-fixture',
            research_intent='DESIGN_MODIFICATION',selected_method='generate'),**base)
        admit_decision(h,p)
        result=generate_candidate(h,p.generation,dict(origin='isolated_engineering_fixture'))
        candidate=result['candidate']
        seed=seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'))
        self.assertTrue(seed)
        self.assertIsNone(warm_start(h,MechanicsRequest(candidate=candidate,initialization='constant_0_2')))
        rows=context(h)['decision_feedback']['actions']
        self.assertTrue(any(r['action']=='mechanics' and r['cold_initializations'] for r in rows))
        ledger=h.store.remaining()
        self.assertEqual(ledger['used']['model_calls'],0)
        self.assertEqual(ledger['used']['backend_solves'],0)

    def test_archived_errors_and_byte_partition(self):
        report=audit()
        self.assertEqual(len(reproduce(report['errors'])),4)
        for row in report['requests']:
            self.assertEqual(row['total_bytes'],sum(row['serialized_bytes'].values()))
        self.assertGreater(report['cumulative_bytes']['history_reasoning'],0)
        for row in report['errors'][1:3]:
            self.assertFalse(Draft202012Validator(plan_schema(['physical_replay'],decision_required=True)).is_valid(row['tool_use']['input']))

    def test_action_schema_exact_payloads_and_legacy_exceptions(self):
        actions=Plan.model_json_schema()['properties']['action']['enum']
        for action in actions:
            schema=plan_schema([action],decision_required=True)
            Draft202012Validator.check_schema(schema)
            self.assertIn('decision',schema['required'])
            for name in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation'):
                self.assertIn(name,schema['required'])
            self.assertEqual(schema['properties']['action']['enum'],[action])
        schema=plan_schema(['physical_replay'],decision_required=True)
        self.assertIn('physical_replay',schema['required'])
        self.assertNotIn('candidate',schema['properties'])
        self.assertNotIn('mechanics',schema['properties'])
        self.assertNotIn('physical_replay',plan_schema(['stop'])['properties'])
        self.assertIn('mechanics_source',plan_schema(['propose'])['properties'])
        self.assertNotIn('diagnostic',plan_schema(['diagnose'])['required'])
        # Shared multi-action schema still rejects the wrong non-null payload.
        q=audit()['errors'][-1]['tool_use']['input'];q=deepcopy(q)
        q['decision']['claimed_inference']='empirical_search'
        validator=Draft202012Validator(plan_schema(['physical_replay','execute'],decision_required=True))
        self.assertTrue(validator.is_valid(q))
        q['candidate']=q['physical_replay']['candidate']
        self.assertFalse(validator.is_valid(q))
        with self.assertRaises(ValueError):Plan.model_validate(q)

    def test_exact_queries_empty_arrays_and_escaped_keys(self):
        ref={'artifact_id':'f'*64,'media_type':'application/json'}
        v={'parameters':{'a/b':{'~key':[1,2,3,4]}},'empty':[]}
        view=compact_evidence(v,ref)
        query=next(q for q in view['read_queries'] if q['pointer']=='/parameters')
        self.assertEqual(query,dict(reference=ref,pointer='/parameters',view='summary'))
        self.assertEqual(view['value']['empty'],[])
        self.assertEqual(view['value']['parameters']['a/b']['~key']['read_pointer'],'/parameters/a~1b/~0key')

    def test_actual_strands_http_wire_schema(self):
        import asyncio, os, httpx
        from tools.research.agent import converse
        h=cold_host();import_history(h);captured={}
        class Captured(BaseException):pass
        class Boundary(httpx.AsyncBaseTransport):
            def __init__(self,*args,**kwargs):pass
            async def handle_async_request(self,request):
                captured.update(json.loads(request.content));raise Captured()
        packet=dict(research=decision_brief(context(h)),implementation='isolated_wire_fixture')
        with patch('tools.research.agent.LiveBoundary',Boundary),patch('tools.research.core.guard'),\
             patch('tools.research.agent.decision_packet',return_value=packet),\
             patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'synthetic-fixture'}):
            with self.assertRaises(Captured):asyncio.run(converse(h))
        schema=next(t['function']['parameters'] for t in captured['tools'] if t['function']['name']=='research_plan')
        def constraints(v):
            if isinstance(v,dict):return {k:constraints(x) for k,x in v.items() if k not in ('description','title')}
            if isinstance(v,list):return [constraints(x) for x in v]
            return v
        self.assertEqual(constraints(schema),constraints(plan_schema(packet['research']['actions'],decision_required=True)))
        Draft202012Validator.check_schema(schema)
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
