"""Offline interface fixtures only; no scientific integration."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import gc
import json
import shutil
from uuid import uuid4
from schemas.platform import ProjectConfig
from tools.research import core, search, analysis, design
from tools.research.config import ROOT
from tools.research.contracts import FamilyMixedSearch, AnalysisRequest
from tools.research.state import state, update, save
from tools.platform_store import plain
from tools.research.design import final_fidelity_matches
from tools.state_io import digest


class FrozenConditionFidelityTests(unittest.TestCase):
    def test_each_frozen_condition_retains_exact_mesh_and_backend(self):
        policy=dict(final_evaluation=dict(cells_per_segment=12))
        cfg=dict(policy=dict(backend={'fixture':1},discretization=dict(data=dict(cells={'a':12,'b':12}))))
        task={'fixture':'second'}
        spec=dict(fidelity_policy=policy,final_evaluation_identity='fixture',configuration=cfg,
            canonical_task_identity='root',task_conditions=[dict(condition_id='second',task=task)])
        c=dict(configuration=deepcopy(cfg),fidelity_policy_identity=digest(policy),final_evaluation_identity='fixture',task_identity='root')
        self.assertTrue(final_fidelity_matches(spec,c))
        c.update(condition_id='second',task_identity=digest(task))
        self.assertTrue(final_fidelity_matches(spec,c))
        c['task_identity']='root'
        self.assertFalse(final_fidelity_matches(spec,c))
        c['task_identity']=digest(task);c['configuration']['policy']['discretization']['data']['cells']['b']=6
        self.assertFalse(final_fidelity_matches(spec,c))
        c['configuration']=deepcopy(cfg);c['condition_id']='unfrozen'
        self.assertFalse(final_fidelity_matches(spec,c))


class NativeMixedSearchTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('native-search-fixture-'+uuid4().hex)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':self.folder.name,'grant_id':self.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            self.host=core.prepare(ROOT/'configs/research/study_family_mujoco_search.json',self.folder)
        self.spec=state(self.host)['spec'];self.addCleanup(self.cleanup)

    def cleanup(self):
        gc.collect()
        if self.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
        if self.folder.exists():shutil.rmtree(self.folder)

    def query(self,**changes):
        return dict(version='family_mixed_search_v1',family_space_identity=self.spec['family_space_identity'],
            variable_groups=['lengths'],segment_counts=[2],tendon_counts=[6],span_strategies=['distributed_consecutive'],
            bounds={'length_m':(.1,.18)},screening_fidelity='standard',objective='task_violation',
            operating_point='standardized_initial_pretension',max_proposals=2,max_evaluations=6,
            evaluation_mode='mujoco_control',initial_tension_n=.2,
            control_settings=dict(version='local_control_search_v2',correction_window_s=[0,.6],
                knots_s=[0,.2,.4,.58],evaluation_requests=51,iterations=2),**changes)

    def plan(self,q):
        return dict(action='search',search=q,hypothesis='Synthetic search interface fixture',
            expected_observation='Six separate condition analyses',weakening_observation='Incomplete references',
            fixed_conditions='Frozen tasks and common synthetic control settings',stopping_condition='Two proposals',
            interpretation='Fabricated callback results; no scientific integration')

    def scored(self,host,query,key,**kwargs):
        request=plain(AnalysisRequest.model_validate(query))
        for ref in state(host)['analysis_results']:
            a=host.store.artifact(ref)
            if a.get('requested_operation')==request:return dict(reference=ref)
        self.assertEqual(query['operation'],'mujoco_nonlinear_task_capability_v1')
        c=design.verify_candidate(host,query['candidate'])
        source=host.store.artifact(query['control_optimization']['source'])
        self.assertTrue(all(all(u==.2 for u in row) for row in source['trajectory']['tensions_n']))
        j=-c['resolved_parameters']['segments'][0]['length_m']
        value=dict(status='computed',operation_key=key+'-analysis',candidate=query['candidate'],
            requested_operation=request,charged_analysis_evaluations=1,charged_numerical_s=0.,fixture=True,
            control_schedule_reference=query['control_optimization']['source'],
            nonlinear_capability=dict(J=j,initial_J=1.,callbacks=3,stop_reason='synthetic_fixture'),
            native_dynamics=dict(cost=dict(model_builds=0,physics_steps=0,rollouts=0,fixture=True)))
        ref=save(host,value,'synthetic_native_analysis_fixture');s=state(host)
        update(host,analysis_results=[*s['analysis_results'],ref],mathematical_evaluations=s['mathematical_evaluations']+1)
        return dict(reference=ref)

    def test_native_contract_grants_and_discovery_without_conic(self):
        from jsonschema import Draft202012Validator
        from tools.research.agent import plan_schema
        q=FamilyMixedSearch.model_validate(self.query())
        Draft202012Validator(plan_schema(['search'],family_version='serial_family_space_v2')).validate(json.loads(json.dumps(self.plan(self.query()))))
        with patch('tools.research.task_constraints.analysis_capabilities',side_effect=AssertionError('CONIC must not be consulted')):
            problem=search.search_problem(self.host,q,6)
        self.assertEqual(problem['analyses_per_structure'],3)
        self.assertIn('native_mode',search.request_guidance(self.spec)['search'])
        with self.assertRaisesRegex(ValueError,'ALL_CONDITIONS'):
            search.search_problem(self.host,q,2)
        with self.assertRaisesRegex(ValueError,'STUDY_NATIVE_CONTROL_LIMIT'):
            search.search_problem(self.host,q.model_copy(update=dict(control_settings=q.control_settings.model_copy(update=dict(evaluation_requests=52)))),6)
        with self.assertRaises(ValueError):FamilyMixedSearch.model_validate({**self.query(),'control_settings':None})
        legacy={k:v for k,v in self.query().items() if k not in ('evaluation_mode','control_settings','initial_tension_n')}
        self.assertEqual(plain(FamilyMixedSearch.model_validate(legacy)),json.loads(json.dumps({**legacy,'method':'bounded_mixed_coordinate_v1',
            'section_types':[],'previous_candidate_ref':None,'evidence_used':[],'step':.25,'minimum_step':.03125,'stop_score':None})))
        with self.assertRaisesRegex(ValueError,'SEARCH_MODE_OUTSIDE'):
            spec=deepcopy(self.spec);spec['family_search'].pop('evaluation_modes');update(self.host,spec=spec)
            search.search_problem(self.host,q,6)

    def test_public_search_reoptimizes_all_conditions_and_reuses_result(self):
        from tools.research.feedback import search_feedback
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=self.scored):
            output=core.dispatch(self.host,self.plan(self.query()),'native-fixture')['result']
        result=output['result'];self.assertEqual(len(result['evaluated']),2)
        self.assertIsNone(result['best_mathematical_candidate']);self.assertIsNotNone(result['best_native_candidate'])
        self.assertEqual(result['resource_use']['actual_mathematical_evaluations'],6)
        self.assertEqual(len(state(self.host)['control_initializations']),6)
        self.assertFalse(state(self.host).get('success_gate'))
        self.assertEqual(state(self.host)['physical_replays'],[])
        for row in result['evaluated']:
            self.assertEqual(len(row['evidence']['conditions']),3)
            self.assertEqual(row['task_acceptance'],'unmeasured')
            self.assertAlmostEqual(row['proxy_values']['task_violation'],max(r['J'] for r in row['evidence']['conditions'].values()))
        feedback=search_feedback(self.host,output['reference'])
        self.assertEqual(len(feedback['conditions']),3)
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=AssertionError('No recomputation')):
            reused=search.run_search(self.host,self.query(),'another-plan',guard=core.guard,execute=None,capacity=None)
        self.assertTrue(reused['reused']);self.assertEqual(state(self.host)['mathematical_evaluations'],6)

    def test_interrupted_native_condition_resumes_saved_analysis(self):
        calls=[]
        def interrupted(*args,**kwargs):
            out=self.scored(*args,**kwargs);calls.append(out)
            if len(calls)==2:raise RuntimeError('synthetic interruption after immutable T1')
            return out
        with patch.object(analysis,'dispatch',side_effect=interrupted):
            with self.assertRaises(RuntimeError):search.run_search(self.host,self.query(),'interrupted',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(state(self.host)['mathematical_evaluations'],2)
        with patch.object(analysis,'dispatch',side_effect=self.scored):
            out=search.run_search(self.host,self.query(),'resume',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(state(self.host)['mathematical_evaluations'],6)
        self.assertEqual(out['result']['resource_use']['actual_mathematical_evaluations'],6)
        self.assertEqual(len(state(self.host)['control_initializations']),6)
        self.assertEqual(out['result']['evaluated'][0]['evidence']['conditions']['negative_low']['analysis'],calls[1]['reference'])


if __name__=='__main__':unittest.main()
