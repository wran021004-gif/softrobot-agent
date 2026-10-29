"""Two offline B0 checks; no live Provider or numerical/physical Worker.

One new candidate tests formal-scope routing. Existing saved synthetic T1 rows
test T2 readiness read-only, without repeating the five-candidate calculation.
"""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator
from tools.platform_host import Host
from tools.research import agent, analysis, core
from tools.research.config import ROOT
from tools.research.nonlinear_capability import T1, T2
from tools.research.state import state, update, save, require_authorization
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import atomic_json, digest, read
from tests.research.test_information_flow import packet
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_p63a_math_interface import generate, t1_request

DRAFT=ROOT/'configs/research/study_p63b1_m1_math_draft.json'


class PreparationTests(unittest.TestCase):
    def test_fresh_draft_formal_scope_diagnose_and_next_mock_wire(self):
        cfg=read(DRAFT);cfg['study_id']='p63b0-fixture-'+uuid4().hex[:8]
        path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json')
        atomic_json(path,cfg)
        try:h=core.prepare(path,ROOT/'runs'/cfg['study_id'])
        finally:path.unlink()
        s=state(h);spec=s['spec']
        self.assertEqual(spec['budgets']['provider_requests'],8)
        self.assertEqual(spec['budgets']['mathematical_evaluations'],4)
        self.assertEqual(spec['native_control_limits']['evaluation_requests'],24)
        self.assertFalse(s['candidates']);self.assertIsNone(s['reference_candidate'])
        for field in ('history','mathematics','control_seeds','background'):
            self.assertEqual(spec['research_decisions'][field],[])
        self.assertTrue(spec['knowledge_manifest']['entries'])
        self.assertFalse(any(e['kind']=='success_case' for e in spec['knowledge_manifest']['entries']))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
            require_authorization(h)
        # This event belongs only to a separate explicitly synthetic test Study.
        scope=dict(study_id=h.run_id,resolved_identity=spec['resolved_identity'],
            budgets=spec['budgets'],capabilities=spec['capabilities'],
            execution_scopes=['registered mathematics'],provider=spec['runtime']['provider'])
        save(h,dict(user_approval='OFFLINE FIXTURE ONLY; not authorization for B1',
            scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
        require_authorization(h)
        pilot=s['pilot'];pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback')
        update(h,freeze='explicit-b0-offline-fixture',pilot=pilot)
        with patch('tools.research.agent.credential',return_value='offline'),\
                patch('tools.research.provider.credential',return_value='offline'),\
                patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            first=run_fixture(h,[None])[0]
            l0=packet(first)
            design=next(c for c in l0['capabilities'] if c['category']=='Design')
            self.assertIn('generate',[a['action'] for a in design['actions']])
            self.assertEqual(l0['mathematical_research']['status'],'requires_owned_candidate')
            self.assertTrue(l0['evidence_access']['domain']['query'])
            candidate=generate(h)
            methods=mathematical_method_view(h,candidate)['methods']
            self.assertEqual(methods[T1]['planning_status'],'requires_parameters')
            self.assertEqual(methods[T2]['planning_status'],'requires_comparable_t1_results')
            self.assertTrue(methods[T1]['formal_execution_authorized'])
            request=t1_request(h,candidate)
            plan=dict(action='diagnose',hypothesis='Synthetic B0 scientific selection',
                expected_observation='Legal mathematics Schema becomes visible',weakening_observation='Request unavailable',
                fixed_conditions='Frozen M1 condition',stopping_condition='No numerical execution',
                interpretation='Offline routing only',decision=dict(hypothesis_id='b0-fixture',research_intent='DIAGNOSE',
                    selected_method=T1,selected_candidate=candidate,requested_budget=0))
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',plan),None])
            self.assertIsNotNone(agent.selected_analysis(h,None))
            schema=next(t['function']['parameters'] for t in wires[-1]['tools'] if t['function']['name']=='research_analysis')
            payload=dict(operating_point='standardized_initial_pretension',control_optimization=request['control_optimization'])
            Draft202012Validator(schema).validate(payload)
            bound=agent.bind_selected_analysis_request(h,payload,tool_use_id='offline-b0-binding')
            self.assertEqual(bound['candidate'],candidate);self.assertEqual(bound['protocol'],spec['analysis_protocol'])
            excessive=deepcopy(bound);excessive['control_optimization']['settings']['evaluation_requests']=25
            with self.assertRaisesRegex(ValueError,'STUDY_NATIVE_CONTROL_LIMIT'):
                analysis.dispatch(h,excessive,'offline-overlimit',guard=lambda *a:None)
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(h.store.remaining()['used']['model_calls'],4)  # Mock HTTP only.
        atomic_json(h.store.root/'b0_preflight_summary.json',dict(fixture_store=str(h.store.root),
            initial_capabilities=l0['capabilities'],next_analysis_schema=schema,
            candidate=candidate,formal_scope='synthetic only',real_provider_requests=0,real_workers=0))

    def test_existing_saved_t2_is_ready_under_formal_scope_without_recalculation(self):
        source=read(ROOT/'docs/research/p63a_interface_examples.json')
        root=Path(source['fixture_store'])
        if not (root/'platform.sqlite').exists():self.skipTest('Original local synthetic fixture unavailable')
        h=Host(root,root.name);before=deepcopy(state(h));candidate=source['candidate']
        self.assertEqual(mathematical_method_view(h,candidate)['methods'][T2]['planning_status'],'unauthorized')
        # View-only approval/budget premise; no historical Store field is changed.
        s=deepcopy(before);s['spec']['budgets']['mathematical_evaluations']=before['mathematical_evaluations']+1
        with patch('tools.research.state.state',return_value=s),\
                patch('tools.research.research_context.mathematics_authorization',return_value=dict(registered_study_scope_authorized=True)):
            method=mathematical_method_view(h,candidate)['methods'][T2]
            self.assertEqual(method['planning_status'],'ready');self.assertTrue(method['executable'])
            schema=agent.selected_analysis_schema(T2,method,bound=True)
            payload=dict(operating_point='standardized_initial_pretension',
                nonlinear_response=method['request_template']['nonlinear_response'])
            Draft202012Validator(schema).validate(payload)
        self.assertEqual(state(h),before)


if __name__=='__main__':unittest.main()
