"""Stage I real SDK/Mock HTTP regression; all numerical results are fabricated."""
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.research import analysis,core
from tools.research.contracts import ScientificQuestionV2,ScientificQuestionV3,MechanismQuestionV2
from tools.research.scientific_intent import question_contract,question_schema,compile_question
from tools.research.state import state,update
from tools.research.object_choices import reference_choices
from tests.research.test_b_scientific_intent import mechanism_question
from tests.research.test_structure_mechanism_aplus import prepare,synthetic_worker,execute_synthetic
from tests.research.test_p63g3_action_handoff import diagnosis,schema,g3_host
from tests.research.test_p63a_math_interface import t1_request,diagnose
from tests.research.test_information_flow import packet,generation
from tests.research.test_recent_round_tools import run_fixture


def integrated_host():
    h,c=prepare();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['analysis_interface']='scientific_question_v4'
    update(h,spec=spec)
    return h,c


def structure_question():
    q=mechanism_question();q.pop('version')
    q['target']['goal']='increase'
    return dict(version='scientific_question_v4',domain='structure',structure=q)


class IntegratedWireTests(unittest.TestCase):
    def test_shared_scoped_feedback_retains_historical_packets_only(self):
        from types import SimpleNamespace
        from tools.research.evidence_views import scoped_feedback
        records=[dict(schema=version,unmodified_value=i) for i,version in enumerate((
            'sorosim_s55_s5t_feedback_v1','sorosim_s56_s5t2_feedback_v1','sorosim_s57_prediction_feedback_v1','unrelated'))]
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:records[ref]))
        result=scoped_feedback(host,range(4))
        self.assertEqual([row['evidence'] for row in result],records[:3])

    def test_historical_contracts_and_v4_domain_admission(self):
        h,c=integrated_host();spec=state(h)['spec']
        for version,contract in [('scientific_question_v3',ScientificQuestionV3),('scientific_question_v2',ScientificQuestionV2)]:
            old=deepcopy(spec);old['research_decisions']['analysis_interface']=version
            old['mathematical_methods'].pop('mechanism_structure_v1')
            self.assertIs(question_contract(old),contract)
        old=deepcopy(spec);old['research_decisions']['analysis_interface']='scientific_question_v2'
        self.assertIs(question_contract(old),MechanismQuestionV2)
        Draft202012Validator.check_schema(question_schema(spec))
        q=structure_question();q['structure']['effect_semantics']='re_equilibrated_passive_response'
        before=state(h)['mathematical_evaluations']
        self.assertEqual(compile_question(h,q,tool_use_id='unsupported')['status'],'unsupported')
        self.assertEqual(state(h)['mathematical_evaluations'],before)
        q=structure_question();q['structure']['target'].pop('goal')
        self.assertEqual(compile_question(h,q,tool_use_id='goal')['reason'],'EXPLICIT_MECHANISM_GOAL_REQUIRED')

    def test_actual_wire_executes_mechanism_delivers_fixed_facts_without_reporter(self):
        h,c=integrated_host();before=deepcopy(state(h)['candidates'])
        missing_goal=structure_question();missing_goal['structure']['target'].pop('goal')
        with synthetic_worker(h,c),patch('tools.research.reporter._wire',side_effect=ValueError('OFFLINE_REPORTER_UNAVAILABLE')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',diagnosis(c,'mechanism_research')),('research_analysis',missing_goal),
                ('research_analysis',structure_question()),None])
        self.assertIn('EXPLICIT_MECHANISM_GOAL_REQUIRED',json.dumps(wires[3]))
        self.assertEqual(schema(wires[2],'research_analysis')['properties']['version']['const'],'scientific_question_v4')
        self.assertNotIn('control',schema(wires[2],'research_analysis')['properties'])
        s=state(h);self.assertEqual(len(s['analysis_results']),1);self.assertEqual(s['candidates'],before)
        ref=s['analysis_results'][0];raw=h.store.artifact(ref)
        self.assertEqual(raw['operation'],'mechanism_structure_v1');self.assertEqual(s['mathematical_evaluations'],5)
        l0=packet(wires[-1]);latest=l0['mathematical_research']['latest_result']
        self.assertEqual(latest['status'],'computed');self.assertEqual(latest['effect_semantics'],'mechanism_effect')
        self.assertGreater(latest['structure_research']['baseline'],0)
        self.assertEqual(latest['structure_research']['cost']['physics_steps'],0)
        self.assertIn('unsupported_conclusions',latest['structure_research'])
        self.assertEqual(len(latest['structure_research']['parameter_sensitivities']),1)
        self.assertNotIn('delta',latest['structure_research']['structure_direction'])
        self.assertNotIn('native',latest['actual_cost'])
        self.assertEqual(l0['reporter_findings'][-1]['status'],'unavailable')
        self.assertIn('advertised selected-tool Schema takes precedence',wires[-1]['messages'][0]['content'])
        for wire in wires:
            text=json.dumps(wire)
            self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])',text,re.I))
            self.assertNotIn('artifact_id',text);self.assertNotIn('x-research-reference-choices',text)
            self.assertIsNone(re.search(r'[\u4e00-\u9fff]',text))
        self.assertNotIn('scientific_results',l0)
        self.assertEqual(l0['research_focus']['latest_result']['facts_at'],'mathematical_research.latest_result')
        self.assertFalse(any(r.get('structure_research') for r in l0.get('verified_facts',[])))
        # Save the actual complete wire as an explicitly labelled synthetic example.
        destination=Path(__file__).resolve().parents[2]/'runs/stage1_validation/wire_example.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(dict(scope='Synthetic SDK/Mock HTTP fixture; no scientific evidence or real Provider',
            wire=wires[-1]),indent=2),encoding='utf-8')
        unchanged=packet(run_fixture(h,[None])[-1])['mathematical_research']['latest_result']
        self.assertNotIn('structure_research',unchanged)
        self.assertEqual(unchanged['status'],'computed')

    def test_direction_handoff_uses_existing_generate_and_keeps_attribution(self):
        h,c=integrated_host();q=structure_question()
        out=execute_synthetic(h,c,q);ref=out['reference'];raw=h.store.artifact(ref)
        request=raw['structure_research']['structure_direction']['generation_handoff']['generation']
        plan=generation(h);plan.update(generation=request,supporting_evidence=[ref])
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_PHYSICAL_WORKER')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='generate')),('research_plan',plan),None])
        self.assertEqual(len(state(h)['candidates']),2)
        generated=next(r for r in state(h)['candidates'].values() if r!=c)
        diagnose(h,generated,'scientific_question')
        from tools.research.research_context import agent_decision_brief
        attribution=agent_decision_brief(h)['mechanism_research']
        self.assertTrue(attribution['generation_plan_cited_evidence']);self.assertTrue(attribution['suggestion_adopted'])
        self.assertTrue(attribution['formal_candidate_created']);self.assertFalse(attribution['direction_proposed'])
        generation_schema=schema(wires[1],'research_plan')
        self.assertNotIn('family_space_identity',json.dumps(generation_schema))

    def test_native_control_compiles_original_effort_and_rejects_domain_change(self):
        h,c=integrated_host();t1_request(h,c);diagnose(h,c,'scientific_question')
        q=dict(version='scientific_question_v4',domain='control',control=dict(question_type='control_feasibility',
            control_scope=dict(mode='full_task'),control_search_effort=dict(method='response',knot_count=4,iterations=7,evaluation_requests=5)))
        result=compile_question(h,q,tool_use_id='v4-control')
        self.assertEqual(result['status'],'ready',result)
        effort=result['request']['control_optimization']['settings']
        self.assertEqual((len(effort['knots_s']),effort['iterations'],effort['evaluation_requests']),(4,7,5))
        self.assertEqual(result['request']['candidate'],c)
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        with patch.object(core,'guard'):core.dispatch(h,diagnosis(c,'mechanism_research'),'v4-own-domain')
        self.assertEqual(compile_question(h,q,tool_use_id='wrong-domain')['reason'],'DIAGNOSE_DOMAIN_MISMATCH')

    def test_projection_preserves_authored_text_and_queryable_store_identity(self):
        from tools.research.object_choices import main_projection
        h,c=integrated_host();text='User-authored hypothesis: '+c['artifact_id']
        before=deepcopy(h.store.artifact(c));value=main_projection(h,dict(hypothesis=text,candidate=c))
        self.assertEqual(value['hypothesis'],text)
        self.assertEqual(h.store.artifact(c),before)
        self.assertIsInstance(value['candidate'],str)
        preview='[Truncated: 1 block, ~1,570 tokens]\n\n'+json.dumps(dict(candidate=c))[:90]
        projected=main_projection(h,[dict(role='tool',content=preview),dict(role='user',content=text)])
        self.assertNotIn(c['artifact_id'],projected[0]['content'])
        self.assertIn('no complete-read credit',projected[0]['content'])
        self.assertEqual(projected[1]['content'],text)


if __name__=='__main__':unittest.main()
