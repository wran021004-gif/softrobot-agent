"""Low-cost changed admission and numerical-failure contracts, never live science."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from uuid import uuid4
import unittest
from unittest.mock import patch
import mujoco
import numpy as np
from tools.research.config import ROOT,resolve
from tools.research.state import state,update,save
from tools.research import core,analysis,search
from tools.platform_store import plain
from tests.research import test_mixed_search as mixed


class C3ReadinessTests(unittest.TestCase):
    def test_strict_generate_retries_and_releases_common_actions(self):
        from tools.research.research_context import agent_decision_brief
        fixture=mixed.MixedSearchTests();fixture.setUp();self.addCleanup(fixture.cleanup)
        host=fixture.host;spec=deepcopy(state(host)['spec']);spec['initial_structure_strategy']='heuristic_generate'
        update(host,spec=spec)
        self.assertEqual(core.initial_structure_action(host),'generate')
        self.assertNotIn('search',agent_decision_brief(host)['actions'])
        with patch.object(core,'guard'),self.assertRaisesRegex(ValueError,'FIRST_STRUCTURE_REQUIRES_GENERATE'):
            core.dispatch(host,mixed.plan(mixed.request(spec)),'rejected-first-search')
        generation=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=1,tendon_count=3)
        p=mixed.plan(None);p.update(action='generate',generation={**generation,'segments':{'0':{'length_m':2.}}});p.pop('search')
        with patch.object(core,'guard'):
            self.assertEqual(core.dispatch(host,p,'invalid-generation')['result']['status'],'invalid')
            self.assertEqual(core.initial_structure_action(host),'generate')
            p['generation']=generation
            self.assertEqual(core.dispatch(host,p,'legal-generation')['result']['status'],'generated')
        self.assertIsNone(core.initial_structure_action(host))
        self.assertIn('search',agent_decision_brief(host)['actions'])
    def test_saved_context_navigation_and_selected_method_projection(self):
        from tests.research.c3_readiness_audit import C3Archive
        from tools.research.research_context import compact_scientific_delivery
        archive=C3Archive();self.addCleanup(archive.archive.close)
        before=archive.requests()[-1][3]['research'];original=deepcopy(before)
        before['selected_mathematical_method']=dict(method='native_dynamics_v1')
        after=compact_scientific_delivery(before,decision_only=True)
        self.assertEqual(after['selected_mathematical_method']['query']['pointer'],'/methods/native_dynamics_v1')
        for key in ('task','task_identity','budget','stop_result_index'):
            self.assertEqual(after[key],original[key])
        for old,new in zip(before['latest_reports'],after['latest_reports']):
            archive.artifact(new['report_reference'])
            self.assertEqual(old['scope'],new['scope']);self.assertEqual(old['limitations'],new['limitations'])
            for finding in new['findings']:archive.artifact(finding['result']['reference'])

    def test_ab_common_scope_and_pending_authorization(self):
        paths=[ROOT/'configs/research'/f'study_c3_{arm}_ab.json' for arm in ('heuristic','math_search')]
        a,b=[json.loads(p.read_text()) for p in paths]
        differences={k for k in a if a[k]!=b[k]}
        self.assertEqual(differences,{'study_id','evidence_destination','initial_structure_strategy','execution_instructions'})
        specs=[resolve(p) for p in paths]
        for s in specs:
            self.assertTrue(s['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))
            self.assertEqual(s['family_space']['executable_segment_counts'],[1,2,3])
            self.assertEqual(s['family_space']['executable_tendon_count_bounds'],[3,4])
            self.assertFalse(s['research_decisions']['history']);self.assertFalse(s['supplied_evidence'])
            self.assertEqual(s['budgets']['mathematical_evaluations'],24)
            self.assertEqual(s['family_search']['max_evaluations'],12)
        self.assertEqual(specs[0]['canonical_task'],specs[1]['canonical_task'])
        self.assertEqual(specs[0]['family_space_identity'],specs[1]['family_space_identity'])

    def test_first_math_candidate_admission_and_two_slot_cost(self):
        fixture=mixed.MixedSearchTests();fixture.setUp();self.addCleanup(fixture.cleanup)
        host=fixture.host;spec=deepcopy(state(host)['spec'])
        spec['initial_structure_strategy']='math_search'
        spec['mathematical_methods']={'sampled-affine-conic-minimax-v1':'explicit engineering fixture'}
        update(host,spec=spec)
        generation=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=1,tendon_count=3)
        bad=mixed.plan(None);bad.update(action='generate',generation=generation);bad.pop('search')
        with patch.object(core,'guard'),self.assertRaisesRegex(ValueError,'FIRST_STRUCTURE'):
            core.dispatch(host,bad,'rejected-first-generation')
        q=mixed.request(spec);q.update(objective='task_violation',operating_point='controller_start_input',max_evaluations=2)
        self.assertEqual(search.search_problem(host,q,2)['query']['version'],'family_mixed_search_v1')
        def scored(h,query,key,**kwargs):
            raw=dict(status='computed',candidate=query['candidate'],requested_operation=plain(__import__('tools.research.contracts',fromlist=['AnalysisRequest']).AnalysisRequest.model_validate(query)),
                operation_key=key+'-analysis',charged_analysis_evaluations=2,charged_numerical_s=0.,
                proxy_values={},trajectory=dict(replay=dict(numerically_valid=True),replayed_violation=.5),fixture=True)
            ref=save(h,raw,'explicit_conic_score_fixture')
            update(h,analysis_results=[ref],mathematical_evaluations=2)
            return dict(reference=ref)
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=scored):
            result=core.dispatch(host,mixed.plan(q),'first-math-fixture')['result']['result']
        self.assertEqual(result['resource_use']['actual_mathematical_evaluations'],2)
        self.assertEqual(result['resource_use']['legally_constructed'],1)
        self.assertEqual(result['best_mathematical_candidate']['task_acceptance'],'unmeasured')
        self.assertTrue(result['best_mathematical_candidate']['lineage']['actual_mathematical_evaluation_ref'])
        self.assertIsNone(core.initial_structure_action(host))
        from tools.research.research_context import agent_decision_brief
        update(host,freeze='explicit-offline-conic-fixture')
        self.assertIn('generate',agent_decision_brief(host)['actions'])

    def test_failure_snapshot_is_pre_call_and_worker_persists_unknown_progress(self):
        from extensions.tendon_family.backends import MujocoFailureSnapshot
        from tools.research import execution_worker
        model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint name="q" type="hinge"/><geom size="0.1"/></body></worldbody><actuator><motor joint="q"/></actuator></mujoco>')
        data=mujoco.MjData(model);data.ctrl[:]=.2
        safety=MujocoFailureSnapshot(model,'explicit-toy-model')
        safety.call(data,mujoco.mj_step,'toy.completed')  # One tiny engineering step.
        expected=data.qpos.copy();time=float(data.time)
        def failure(model,data):
            data.qpos[:]=999
            raise mujoco.FatalError('FactorizeHessian: rank-deficient sparse Hessian')
        with patch.object(mujoco,'mj_step',new=failure),self.assertRaises(mujoco.FatalError) as raised:
            safety.call(data,mujoco.mj_step,'toy.failure')
        diagnostic=raised.exception.mujoco_diagnostic
        np.testing.assert_array_equal(diagnostic['qpos'],expected)
        self.assertEqual(diagnostic['time_before_call_s'],time)
        self.assertEqual(diagnostic['confirmed_completed_steps'],1)
        self.assertEqual(diagnostic['failed_call_internal_steps'],'unknown')
        restored=mujoco.MjData(model)
        mujoco.mj_setState(model,restored,np.array(diagnostic['integration_state']),safety.spec)
        np.testing.assert_array_equal(restored.qpos,expected)
        folder=ROOT/'runs'/('c3-failure-'+uuid4().hex[:8]);folder.mkdir()
        self.addCleanup(lambda:shutil.rmtree(folder))
        path=folder/'request.json'
        path.write_text(json.dumps(dict(kind='candidate_analysis',implementation='offline',configuration={},binding={},query={})))
        with patch.object(execution_worker,'contain_worker_children'),patch('sys.argv',['worker',str(path)]),patch.object(analysis,'calculate',side_effect=raised.exception):
            execution_worker.main()
        result=json.loads(path.with_name('result.json').read_text())
        self.assertEqual(result['status'],'execution_incomplete')
        self.assertTrue(path.with_name('numerical_failure.json').exists())
        self.assertEqual(result['physics_steps_lower_bound'],1)
        self.assertNotIn('trajectory',result)


if __name__=='__main__':unittest.main()
