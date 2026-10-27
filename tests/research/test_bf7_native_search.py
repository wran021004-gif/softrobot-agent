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


class NativeFirstProgressTests(unittest.TestCase):
    def test_completed_computation_releases_gate_but_rejection_and_interruption_do_not(self):
        from unittest.mock import Mock
        host=Mock()
        analysis_ref={'artifact_id':'analysis'}; result_ref={'artifact_id':'result'}
        row={'evidence':{'conditions':{'primary':{'analysis':analysis_ref,'callbacks':2}}}}
        result={'resource_use':{'actual_mathematical_evaluations':1},'evaluated':[row],
                'termination_reason':'budget_exhausted','best_native_candidate':None}
        checkpoint={'problem':{'query':{'version':'family_mixed_search_v1','objective':'task_violation',
                                      'evaluation_mode':'mujoco_control'}},'result_reference':result_ref}
        snapshot={'spec':{'initial_structure_strategy':'native_search'},'searches':{'a':checkpoint},
                  'analysis_results':[analysis_ref]}
        host.store.artifact.return_value={'result':result}
        with patch.object(search,'state',return_value=snapshot):
            self.assertEqual(search.initial_search_progress(host)['status'],'completed_unresolved')
            row['evidence']['conditions']['primary']['callbacks']=0
            self.assertFalse(search.initial_search_progress(host)['requirement_satisfied'])
            row['evidence']['conditions']['primary']['cost']={'physics_steps':327}
            self.assertEqual(search.initial_search_progress(host)['status'],'completed_unresolved')
            row['evidence']['conditions']['primary']['cost']={'physics_steps':0}
            row['evidence']['conditions']['primary']['callbacks']=2
            result['termination_reason']='analysis_not_admitted'
            self.assertFalse(search.initial_search_progress(host)['requirement_satisfied'])
            result['termination_reason']='budget_exhausted'
            checkpoint.pop('result_reference')
            self.assertFalse(search.initial_search_progress(host)['requirement_satisfied'])


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
        guidance=search.request_guidance(self.spec)
        self.assertIn('native_mode',guidance['search'])
        self.assertEqual(guidance['generate']['segment_section_format']['required_section_counts'],{'first':1,'subsequent':2})
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

    def test_v3_adaptive_coupled_search_rebinds_controls_and_preserves_unresolved(self):
        from tools.research.config import resolve
        from tools.research.feedback import search_feedback
        spec=deepcopy(self.spec);spec.pop('task_conditions',None);spec['initial_structure_strategy']='agent_choice'
        space=resolve(ROOT/'configs/research/study_serial_v3_dev.json')['family_space']
        spec['family_space']=space;spec['family_space_identity']=digest(space)
        spec['family_search']['methods']=['bounded_mixed_coordinate_v1','adaptive_joint_block_v1']
        update(self.host,spec=spec)
        seed=design.generate_candidate(self.host,dict(version='serial_family_generation_v3',
            family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=6),
            dict(origin='offline_fixture'),screening_fidelity='standard')
        self.assertEqual(seed['status'],'generated',seed)
        total=sum(x['length_m'] for x in seed['resolved']['segments'])
        spec['length_constraint']={'fixed_total_m':total};update(self.host,spec=spec)
        for method in ('bounded_mixed_coordinate_v1','normalized_joint_block_v1'):
            invalid=self.query();invalid.update(family_space_identity=spec['family_space_identity'],method=method)
            with self.assertRaisesRegex(ValueError,'V3_SEARCH_METHOD_UNSUPPORTED'):
                search.search_problem(self.host,invalid,4)
        q=self.query();q.update(family_space_identity=spec['family_space_identity'],method='adaptive_joint_block_v1',
            previous_candidate_ref=seed['candidate'],span_strategies=['whole_chain'],
            max_proposals=4,max_evaluations=4,variable_groups=['lengths','routing'],
            block_parameters=['segments.0.length_m','segments.1.length_m','routes.1.segments.1.radius_m','routes.1.segments.1.angle_rad'],
            block_direction={'segments.0.length_m':1.,'segments.1.length_m':-1.,
                'routes.1.segments.1.radius_m':1.,'routes.1.segments.1.angle_rad':1.},
            block_bounds={'routes.1.segments.1.angle_rad':[.95,1.15]},bounds={})
        invalid=deepcopy(q);invalid['block_parameters']=['tendon_parameters.length_servo_gain_n_m'];invalid['block_direction']={};invalid['block_bounds']={};invalid['variable_groups']=['routing']
        with self.assertRaisesRegex(ValueError,'ADAPTIVE_BLOCK_REQUIRES_EFFECTIVE_SELECTED_PARAMETER'):
            search.search_problem(self.host,invalid,4)
        invalid=deepcopy(q);invalid['block_bounds']={'segments.0.length_m':[.001,1.]}
        with self.assertRaisesRegex(ValueError,'ADAPTIVE_BLOCK_BOUND_OUTSIDE_DOMAIN'):
            search.search_problem(self.host,invalid,4)
        calls=[]
        def score_or_incomplete(host,query,key,**kwargs):
            calls.append(key)
            if len(calls)<4:return self.scored(host,query,key,**kwargs)
            value=dict(status='execution_incomplete',operation_key=key+'-analysis',candidate=query['candidate'],
                requested_operation=plain(AnalysisRequest.model_validate(query)),charged_analysis_evaluations=1,charged_numerical_s=0.,
                native_progress=dict(cost=dict(physics_steps=10,rollouts=1)),fixture=True)
            ref=save(host,value,'synthetic_incomplete_native_fixture');s=state(host)
            update(host,analysis_results=[*s['analysis_results'],ref],mathematical_evaluations=s['mathematical_evaluations']+1)
            return dict(reference=ref)
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=score_or_incomplete):
            out=core.dispatch(self.host,self.plan(q),'v3-adaptive-fixture')['result']
        value=out['result'];rows=value['evaluated'];updates=value['search_updates']
        self.assertEqual(len(rows),4)
        for row in rows:
            self.assertAlmostEqual(sum(v['length_m'] for v in row['parameters']['segments'].values()),total,places=11)
            self.assertEqual(row['parameters']['version'],'serial_family_generation_v3')
            self.assertEqual(len(row['evidence']['conditions']),1)
        self.assertEqual(len(rows[1]['lineage']['variables_or_topology_changed']),4)
        self.assertEqual([u['decision'] for u in updates],['baseline','accepted_improvement','rejected_no_improvement','unresolved'])
        self.assertGreater(updates[1]['radius_after'],updates[1]['radius_before'])
        self.assertLess(updates[2]['radius_after'],updates[2]['radius_before'])
        self.assertEqual(updates[3]['radius_after'],updates[3]['radius_before'])
        self.assertIsNone(rows[3]['proxy_values'].get('task_violation'))
        self.assertEqual(len(state(self.host)['control_initializations']),4)
        self.assertEqual(search_feedback(self.host,out['reference'])['final_materialization']['generation']['version'],'serial_family_generation_v3')
        self.assertFalse(state(self.host).get('success_gate'))
        with patch.object(analysis,'dispatch',side_effect=AssertionError('No recomputation')):
            reused=search.run_search(self.host,q,'v3-second-plan',guard=lambda *a:None,execute=None,capacity=None)
        self.assertTrue(reused['reused'])
        # A saved T1 receipt is recovered after interruption; no extra evaluation.
        q2=deepcopy(q);q2.update(max_proposals=2,max_evaluations=2,step=.2)
        q2['control_settings']['iterations']=1
        observed=[]
        def interrupt_after_save(*args,**kwargs):
            value=self.scored(*args,**kwargs);observed.append(value)
            if len(observed)==2:raise RuntimeError('synthetic interruption after saved result')
            return value
        with patch.object(analysis,'dispatch',side_effect=interrupt_after_save):
            with self.assertRaisesRegex(RuntimeError,'synthetic interruption'):
                search.run_search(self.host,q2,'v3-interrupted',guard=lambda *a:None,execute=None,capacity=None)
        count=state(self.host)['mathematical_evaluations']
        with patch.object(analysis,'dispatch',side_effect=self.scored):
            recovered=search.run_search(self.host,q2,'v3-interrupted',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(state(self.host)['mathematical_evaluations'],count)
        self.assertEqual(recovered['result']['evaluated'][1]['evidence']['conditions']['primary']['analysis'],observed[-1]['reference'])

    def test_single_task_native_search_uses_one_analysis_per_structure(self):
        spec=deepcopy(self.spec);spec.pop('task_conditions',None);spec['initial_structure_strategy']='native_search'
        update(self.host,spec=spec)
        q=self.query();q.update(max_proposals=1,max_evaluations=1)
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=self.scored):
            output=core.dispatch(self.host,self.plan(q),'single-native-fixture')['result']
        result=output['result']
        self.assertEqual(result['resource_use']['actual_mathematical_evaluations'],1)
        self.assertEqual(set(result['best_native_candidate']['evidence']['conditions']),{'primary'})
        self.assertTrue(search.initial_search_progress(self.host)['requirement_satisfied'])
        self.assertFalse(state(self.host).get('success_gate'))

    def test_unrankable_native_rows_are_not_described_as_best(self):
        def incomplete(host,query,key,**kwargs):
            request=plain(AnalysisRequest.model_validate(query))
            value=dict(status='execution_incomplete',operation_key=key+'-analysis',candidate=query['candidate'],
                requested_operation=request,charged_analysis_evaluations=1,charged_numerical_s=0.,fixture=True,
                native_progress=dict(cost=dict(physics_steps=10,rollouts=1)))
            ref=save(host,value,'synthetic_incomplete_native_fixture');s=state(host)
            update(host,analysis_results=[*s['analysis_results'],ref],mathematical_evaluations=s['mathematical_evaluations']+1)
            return dict(reference=ref)
        spec=deepcopy(self.spec);spec.pop('task_conditions',None);spec['initial_structure_strategy']='native_search'
        update(self.host,spec=spec)
        q=self.query();q.update(max_proposals=2,max_evaluations=2)
        with patch.object(core,'guard'),patch.object(analysis,'dispatch',side_effect=incomplete):
            out=core.dispatch(self.host,self.plan(q),'incomplete-native-fixture')['result']['result']
        self.assertIsNone(out['best_native_candidate'])
        self.assertIsNone(out['best_observed'])
        self.assertTrue(all(u['incumbent_after'] is None for u in out['search_updates']))
        from tools.research.feedback import search_feedback
        ref=state(self.host)['search_results'][-1];feedback=search_feedback(self.host,ref)
        self.assertEqual(feedback['J_units'],'dimensionless signed normalized constraint violation')
        observed=feedback['recent_outcomes'][0]['conditions']['primary']
        self.assertIsNone(observed['J'])
        self.assertEqual(observed['scientific_computation']['status'],'numerically_incomplete')
        self.assertEqual(observed['cost']['physics_steps'],10)
        self.assertTrue(search.initial_search_progress(self.host)['requirement_satisfied'])
        self.assertNotIn('best',out['evaluated'][1]['lineage']['decision'])

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
