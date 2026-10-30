"""State-aware discovery fixtures; no real Provider, worker or integration.

Saved synthetic numbers exercise presentation only, never scientific acceptance.
"""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from tools.platform_store import plain

from tools.research import core,reporter
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.nonlinear_capability import T1,T2
from tools.research.research_context import (agent_decision_brief, research_decision_brief_v3,
    information_flow_brief, mathematical_discovery_observations)
from tools.research.state import state,update
from tools.research.task_constraints import (mathematical_method_view,
    mathematical_opportunity_summary,analysis_capabilities,mathematical_research_view)
from tools.state_io import atomic_json,read
from tools.research_tasks import task_adapter
from tests.research.test_p63a_math_interface import (fixture_host,generate,t1_request,offline_dispatch,diagnose)
from tests.research.test_p63b3_action_interface import provision
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


EXAMPLES={}


def example(name,brief):
    value=research_decision_brief_v3(brief)
    EXAMPLES[name]=dict(mathematical_research=value['mathematical_research'],
        mathematical_research_bytes=len(json.dumps(value['mathematical_research'],ensure_ascii=False).encode()),
        l0_bytes=len(json.dumps(value,ensure_ascii=False).encode()),
        action_menu=value['action_menu'])
    atomic_json(ROOT/'runs/p63c1_offline_examples.json',dict(
        scope='Offline engineering fixtures; synthetic data is not scientific evidence; real Provider/science workers/integration = 0',
        examples=EXAMPLES))
    return value


class StateAwareMathDiscoveryTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained',
                'extensions.tendon_family.mujoco_analysis.NativeModel','mujoco.mj_step'):
            stop=patch(target,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_INTEGRATION'))
            stop.start();self.addCleanup(stop.stop)

    def test_no_candidate_preserves_static_discovery_and_initial_entries(self):
        h=provision();before=deepcopy(state(h));brief=agent_decision_brief(h)
        math=example('no_candidate',brief)['mathematical_research']
        self.assertEqual(math['status'],'requires_owned_candidate');self.assertEqual(math['methods'],[])
        self.assertEqual(math['known_capabilities'],dict(formally_integrated=18,unintegrated=9))
        self.assertEqual(len(math['operation_categories']),5)
        inventory=core.read_evidence(h,math['full_catalog_query'],record_read=False)
        self.assertEqual(len(inventory),27)
        self.assertTrue(all('request_template' not in r for r in inventory.values()))
        self.assertTrue(all(not r['current_execution']['assessed'] for r in inventory.values() if r['has_formal_execution_entry']))
        self.assertTrue(math['initial_entries']);self.assertIn('generate',[r['action'] for r in math['initial_entries']])
        for key in ('parameters_query','model_capabilities_query'):
            self.assertTrue(core.read_evidence(h,math[key],record_read=False))
        self.assertEqual(state(h),before)

    def test_missing_source_and_recorded_source_do_not_imply_request_admission(self):
        h=provision();candidate=generate(h)
        for has_source in (False,True):
            if has_source:t1_request(h,candidate)
            before=deepcopy(state(h));brief=agent_decision_brief(h)
            math=example('candidate_with_source' if has_source else 'candidate_without_source',brief)['mathematical_research']
            self.assertLessEqual(len(math['methods']),4)
            control=next(r for r in math['methods'] if r['method'] in (T1,'mujoco_direct_control_v1'))
            self.assertEqual(control['recorded_control_source_available'],has_source)
            self.assertEqual('legal_control_source' in control['missing'],not has_source)
            self.assertEqual(control['readiness'],'requires_inputs')
            self.assertEqual(control['request_admission'],'not_checked')
            if not has_source:self.assertEqual(control['preparation']['action'],'initialize_control')
            self.assertEqual(state(h),before)
        # All original methods, including unprioritized model comparisons, remain reachable.
        methods=core.read_evidence(h,math['method_directory_query'],record_read=False)
        self.assertGreater(len(methods),len(math['methods']))
        self.assertIn('linearization',methods);self.assertIn('native_dynamics_v1',methods)
        schema=core.read_evidence(h,dict(reference=candidate,view='mathematical_capabilities',pointer='/analysis_request_schema'),record_read=False)
        self.assertEqual(schema,AnalysisRequest.model_json_schema())
        inventory=core.read_evidence(h,math['full_catalog_query'],record_read=False)
        self.assertEqual(len(inventory),27)
        self.assertFalse(inventory['passive_equilibrium_v1']['has_formal_execution_entry'])

    def test_budget_authorization_and_closeout_retain_read_access(self):
        for mode in ('unauthorized','budget_exhausted','protected_closeout'):
            h=fixture_host() if mode=='unauthorized' else provision()
            candidate=generate(h);t1_request(h,candidate)
            if mode=='budget_exhausted':update(h,mathematical_evaluations=state(h)['spec']['budgets']['mathematical_evaluations'])
            if mode=='protected_closeout':update(h,count_closeout=True)
            before=deepcopy(state(h));brief=agent_decision_brief(h)
            math=example(mode,brief)['mathematical_research']
            self.assertEqual(math['methods'],[])
            self.assertEqual(math['status'],'no_new_mathematical_request_available')
            self.assertTrue(math['unavailable_status_counts'])
            if mode=='protected_closeout':
                if brief['current_research_state']['object']['provenance_query']:
                    self.assertTrue(core.read_evidence(h,math['full_catalog_query'],record_read=False))
                else:
                    self.assertNotIn('full_catalog_query',math)
                    self.assertEqual(core.read_evidence(h,math['legal_evidence_query'],record_read=False),[])
            # Uses the exact original closeout-readable anchor, not candidate reads.
            self.assertEqual(core.read_evidence(h,brief['stop_result_index']['query'],record_read=False),[])
            self.assertEqual(state(h),before)

    def test_completed_synthetic_math_has_single_numeric_owner_and_free_choices(self):
        h=provision();candidate=generate(h)
        result=offline_dispatch(h,t1_request(h,candidate),'c1-synthetic-t1')
        reporter.scientific_feedback(h,result)  # Deterministic deferred report; no model call.
        diagnose(h,candidate,T1)
        before=deepcopy(state(h));brief=agent_decision_brief(h);l0=example('computed_math',brief)
        math=l0['mathematical_research'];latest=math['latest_result']
        raw=h.store.artifact(result['reference']);native=raw['nonlinear_capability']
        self.assertEqual(latest['quantities']['J'],native['J'])
        self.assertEqual(latest['quantities']['initial_J'],native['initial_J'])
        self.assertEqual(latest['reliability']['convergence'],'unresolved')
        self.assertEqual(latest['task_acceptance'],'unmeasured')
        self.assertEqual(latest['reference'],result['reference'])
        self.assertTrue(latest['scientific_scope']['model']);self.assertTrue(latest['unresolved'])
        self.assertEqual([r['constraint_id'] for r in math['current_focus']],['holding_max_speed_m_s'])
        self.assertTrue(all(r['status']=='violated' for r in math['current_focus']))
        self.assertTrue(any('analyze' in r['generic_operations'] for r in math['methods']))
        self.assertTrue(any('compare' in r['generic_operations'] for r in math['methods']))
        self.assertNotIn('next_plan',math);self.assertNotIn('selected_method',math)
        self.assertTrue(all('methods' not in r for r in l0['action_menu']))
        flow=information_flow_brief(brief,l0)
        owner=next(f for f in flow['verified_facts'] if f.get('result_reference')==result['reference'])
        self.assertEqual(owner,dict(result_reference=result['reference'],facts_at='mathematical_research.latest_result'))
        self.assertLessEqual(len(json.dumps(math).encode()),10000)
        self.assertEqual(state(h),before)
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)

    def test_measured_focus_is_scoped_and_never_an_automatic_cause(self):
        h=provision();candidate=generate(h);ref=state(h)['family_space_reference']
        observed=dict(candidate_reference=candidate,valid_complete=True,task_passed=False,
            critical_samples=[dict(raw_reference=ref,constraints=[dict(constraint='holding_max_speed_m_s',
                normalized_excess=.2,raw_pointer='/fixture_saved_speed',raw_reference=ref)])])
        current=dict(latest_scientific_feedback=dict(physical_diagnostic=observed))
        observations,latest=mathematical_discovery_observations(h,current,candidate)
        self.assertIsNone(latest);self.assertEqual(observations[0]['scope'],'physical_task')
        view=mathematical_method_view(h,candidate)
        math=mathematical_opportunity_summary(view,observations=observations)
        self.assertEqual(math['current_focus'][0]['status'],'violated')
        self.assertGreaterEqual(len(math['methods']),2)
        self.assertNotIn('cause',math);self.assertNotIn('structure_change',math)
        # A result of another candidate cannot become this candidate's focus.
        observed['candidate_reference']=ref
        self.assertEqual(mathematical_discovery_observations(h,current,candidate),([],None))

    def test_original_task_coverage_controls_tracking_and_axis_discovery(self):
        h=provision();candidate=generate(h);base=mathematical_method_view(h,candidate)
        original=deepcopy(h.store.artifact(candidate))
        for filename in ('bf4_tracking_direction_change_v1.json','bf5_position_tool_axis_v1.json'):
            path=ROOT/'tasks'/filename
            cfg=deepcopy(original['configuration']);cfg['task']=read(path)['task']
            req=task_adapter(cfg).analysis_requirements({})
            rows={r['operation']:r for r in analysis_capabilities(cfg,req,state(h)['spec']['analysis_protocol'])}
            view=deepcopy(base)
            for key,detail in view['methods'].items():
                if detail['operation'] in rows:
                    row=rows[detail['operation']]
                    detail.update(planning_status=row['planning_status'],execution_status='blocked' if row['planning_status']=='unsupported' else 'conditional_on_admission',
                        coverage=row['coverage'],full_task_supported=row['full_task_supported'],applicability=row,missing=row.get('reasons',[]))
                else:detail.update(planning_status='unsupported',missing=['Original task contract has no nonlinear T1/T2 adaptation'])
            c={**original,'configuration':cfg}
            view['research_opportunities']=mathematical_research_view(state(h)['spec'],c,candidate,req,view['methods'])
            math=mathematical_opportunity_summary(view)
            self.assertNotIn(T1,[r['method'] for r in math['methods']]);self.assertNotIn(T2,[r['method'] for r in math['methods']])
            self.assertEqual(rows['mujoco_direct_control_v1']['planning_status'],'requires_parameters')
            if cfg['task']['family']=='task.position_tool_axis':
                self.assertEqual(rows['task_capability']['planning_status'],'unsupported')

    def test_actual_mock_wire_keeps_current_packet_tail_and_other_method_queries(self):
        h=provision();candidate=generate(h);t1_request(h,candidate)
        view=mathematical_method_view(h,candidate)
        wires=run_fixture(h,[('evidence_read',view['methods']['native_dynamics_v1']['detail_query']),None])
        for wire in wires:
            l0=packet(wire);math=l0['mathematical_research']
            self.assertLessEqual(len(math['methods']),4)
            self.assertNotIn('analysis_request_schema',json.dumps(math))
            self.assertNotIn('parameters.',json.dumps(math))
            self.assertTrue(wire['messages'][-1]['content'].startswith('CURRENT_RESEARCH_PACKET\n'))
            self.assertNotIn('mathematical_research',wire['messages'][0]['content'])
            self.assertTrue(math['full_catalog_query'])
        example('mock_wire_source_ready',agent_decision_brief(h))

    def test_saved_b6_projection_keeps_original_numbers_without_mutating_its_store(self):
        audit=read(ROOT/'docs/research/p63b6_gateway_retest_audit.json')
        path=Path(audit['operator_inputs']['store'])/'platform.sqlite'
        if not path.is_file():self.skipTest('Original local B6 Store unavailable; synthetic tests remain independent')
        h=provision();reference=audit['mathematical_results'][0]['reference']
        before_stat=path.stat().st_mtime_ns
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            original=h.store.artifact
            def artifact(ref,**kwargs):
                ref=plain(ref)
                row=db.execute('SELECT body FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone()
                return json.loads(row[0]) if row else original(ref,**kwargs)
            with patch.object(h.store,'artifact',side_effect=artifact):
                raw=artifact(reference)
                # Fixture-only index exposes the immutable result for this pure read.
                update(h,analysis_results=[reference])
                observations,latest=mathematical_discovery_observations(h,{},raw['candidate'])
                self.assertEqual(latest['quantities']['initial_J'],13.45390642085818)
                self.assertEqual(latest['quantities']['J'],11.269234347898596)
                self.assertEqual(len(observations),3);self.assertTrue(all(r['passed'] is False for r in observations))
                self.assertEqual(latest['reliability'],dict(global_optimality='not_established',convergence='unresolved'))
                self.assertEqual(latest['task_acceptance'],'unmeasured')
                self.assertNotIn('next_actions',latest)
                EXAMPLES['saved_b6_read_only']=dict(latest_result=latest,
                    scope='Read original B6 result through an isolated presentation fixture. No current execution permission or new Main decision is implied.')
                atomic_json(ROOT/'runs/p63c1_offline_examples.json',dict(scope='Offline engineering/saved-state projection only',examples=EXAMPLES))
            self.assertEqual(db.total_changes,0)
        self.assertEqual(path.stat().st_mtime_ns,before_stat)


if __name__=='__main__':unittest.main()
