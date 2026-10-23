"""S138 boundary regressions; no Provider, physical step or training."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import json
import unittest
from unittest.mock import patch
import numpy as np

from schemas.platform import SessionInput
from schemas.platform_analysis import TaskAnalysisProtocol
from tools.platform_store import plain
from tools.state_io import digest,atomic_json
from tools.research import analysis,search,optimal_capability as opt,feedback
from tools.research.contracts import AnalysisRequest,Search
from tools.research.design import resolved_configuration
from tools.research.state import state,update,save
from tools.research.task_constraints import describe_analysis_requirements,analysis_capabilities,endpoint_target
from tools.research_tasks import assemble_acceptance,task_adapter
from tests.research.test_s135_control import configuration
from tests.research import test_mainline as fixtures
from tests.research.test_tracking import evaluate,fixture


def protocol(cfg):
    from tools.research.config import ROOT,resolve
    p=deepcopy(resolve(ROOT/'configs/research/study.json')['analysis_protocol'])
    p.update(duration_s=cfg['task']['timing']['duration_s'],period_s=cfg['task']['timing']['control_period_s'],
        windows_s=[.1,.4] if cfg['task']['family']=='task.tracking' else p['windows_s'])
    return p


class ResearchTests(unittest.TestCase):
    def host(self,tracking=False):
        f=fixtures.MainlineTests();f.setUp();self.addCleanup(f.tearDown)
        cfg=configuration(tracking);p=protocol(cfg);spec=deepcopy(f.spec)
        spec.update(configuration=cfg,analysis_protocol=p,mathematical_methods={opt.CONIC:True,opt.SENSITIVITY:True})
        spec['budgets']['mathematical_evaluations']=100
        update(f.host,spec=spec,base_configuration=cfg,freeze='s138-synthetic-fixture',mathematical_evaluations=0,searches={})
        c=f.host.store.artifact(f.candidate);c['configuration']=cfg
        return f.host,c,f.candidate

    def test_condition_admission_and_static_assumptions(self):
        cfg=configuration(True);p=protocol(cfg);req=describe_analysis_requirements(cfg,{})
        rows=analysis_capabilities(cfg,req,p,mathematical_methods={opt.CONIC:True,opt.SENSITIVITY:False})
        by={r.get('submode') or r.get('capability_method') or r['operation']:r for r in rows}
        self.assertEqual(by['linearization']['status'],'applicable')
        self.assertEqual(by['controllability']['status'],'applicable')
        self.assertIn('constant',str(by['equilibrium']['reasons']))
        self.assertIn('Terminal norm',str(by['endpoint']['reasons']))
        self.assertEqual(by[opt.CONIC]['status'],'conditional')
        self.assertFalse(by[opt.CONIC]['full_task_supported'])
        self.assertEqual(by[opt.CONIC]['evaluations'],20)
        self.assertIn('method_not_authorized',by['optimal_sensitivity']['reasons'])
        bad=deepcopy(cfg);bad['task']['environment']['data']['external_forces']=[dict(entity='tip',force_n=[1.,0.,0.],start_s=0.,end_s=.4)]
        rows=analysis_capabilities(bad,describe_analysis_requirements(bad,{}),p)
        self.assertTrue(all(r['status']=='not_applicable' for r in rows))

    def test_timed_endpoint_uses_adapter_and_does_not_invent_holding(self):
        cfg=configuration(True)
        cfg['task']['goal']['data'].update(time_requirement='timed',times_s=[0.,.2,.4])
        cfg['task']['sampling']['window_s']=[.02,.4]
        cfg['policy']['controller']['parameters']['data']['recipe']['reference_mode']='timed'
        req=describe_analysis_requirements(cfg,{})
        target=endpoint_target(req,TaskAnalysisProtocol.model_validate(protocol(cfg)))
        self.assertEqual(list(target.position_m),cfg['task']['goal']['data']['vertices_m'][-1])
        rows={r['operation']:r for r in analysis_capabilities(cfg,req,protocol(cfg))}
        self.assertEqual(rows['endpoint']['status'],'applicable')
        self.assertEqual(rows['endpoint']['coverage'][0]['status'],'partial')
        self.assertEqual(rows['braking']['status'],'not_applicable')
        with self.assertRaisesRegex(ValueError,'Terminal norm'):endpoint_target(req,TaskAnalysisProtocol.model_validate(protocol(cfg)),braking=True)

    def test_real_generated_dynamic_models_share_preparation(self):
        from extensions.tendon_family.math_analysis import calculate_candidate_configuration
        from extensions.tendon_family.gvs_profile import mathematical_numerical,checked_control
        from tools.research.config import ROOT,resolve
        spec=resolve(ROOT/'configs/research/study.json');source=configuration();params=deepcopy(spec['reference_parameters'])
        params['segments']['near']['length_m']+=.002;params['segments']['distal1']['length_m']-=.002
        models=[]
        for kind in ('constant','free_progress','timed'):
            cfg=configuration(kind!='constant')
            if kind!='constant':params.update(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.)
            if kind=='timed':
                cfg['task']['goal']['data'].update(time_requirement='timed',times_s=[0.,.2,.4])
                cfg['task']['sampling']['window_s']=[.02,.4]
                cfg['policy']['controller']['parameters']['data']['recipe']['reference_mode']='timed'
            cfg=resolved_configuration(source,cfg,params,'s138-real-model-preparation')
            inp=SessionInput.model_validate(cfg);numerical=mathematical_numerical(inp)
            ref=dict(artifact_id=digest(cfg),media_type='application/json')
            binding=dict(candidate_id=digest(cfg),configuration=ref,task_identity=digest(cfg['task']),
                basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis'],coordinate_order=numerical['coordinate_order'])
            result=calculate_candidate_configuration(inp,binding,TaskAnalysisProtocol.model_validate(protocol(cfg)),ref,
                operating_points=['controller_start_input'])
            models.append(result.records[1]['model'])
            if kind=='timed':
                with self.assertRaisesRegex(ValueError,'PHYSICAL_ROUTE_UNSUPPORTED'):checked_control(inp)
        for model in models[1:]:
            for key in ('A','B','C','D','drift','x0','u0'):np.testing.assert_allclose(models[0][key],model[key])

    def test_path_budget_planning_and_grants(self):
        cfg=configuration(True);req=describe_analysis_requirements(cfg,{})
        q=AnalysisRequest(candidate=dict(artifact_id='a'*64),operation='task_capability',operating_point='controller_start_input',protocol=protocol(cfg),capability_method=opt.CONIC)
        spec=dict(configuration=cfg,mathematical_methods={opt.CONIC:True,opt.SENSITIVITY:True},budgets=dict(mathematical_evaluations=100))
        self.assertEqual(opt.method_admission(spec,q,requirements=req)['expected_mathematical_evaluations'],20)
        for steps,expected in (([.001],59),([.001,.0005],99)):
            raw=plain(q);raw['optimal_sensitivity']=dict(variable='segments.near.length_m',steps=steps,model_results=[plain(q.candidate)]*(1+2*len(steps)))
            fit=opt.method_admission(spec,AnalysisRequest.model_validate(raw),requirements=req)
            self.assertEqual(fit['expected_mathematical_evaluations'],expected)
            self.assertEqual(opt.sensitivity_cost(len(steps),1+2*len(steps),100,subproblems=19)['kernel_evaluations'],expected)
        denied=deepcopy(spec);denied['mathematical_methods']={}
        self.assertIn('AUTHORIZATION',str(opt.method_admission(denied,q,requirements=req)['reasons']))
        denied['mathematical_methods']=spec['mathematical_methods'];denied['budgets']['mathematical_evaluations']=19
        self.assertIn('INSUFFICIENT',str(opt.method_admission(denied,q,requirements=req)['reasons']))

    def test_tracking_dispatch_reserves_all_branches_and_reuses_failed_receipt(self):
        h,c,ref=self.host(True)
        q=dict(candidate=ref,operation='task_capability',operating_point='controller_start_input',protocol=state(h)['spec']['analysis_protocol'],capability_method=opt.CONIC)
        def failed_worker(command,log,timeout):
            self.assertEqual(state(h)['mathematical_evaluations'],20)
            atomic_json(Path(command[-1]).with_name('result.json'),dict(status='execution_incomplete',error='synthetic failure'))
            return NS(returncode=1)
        with patch.object(analysis,'verify_candidate',return_value=c),patch('tools.service_execution._run_contained',side_effect=failed_worker) as worker:
            out=analysis.dispatch(h,q,'s138-path',guard=lambda *a:None)
            replay=analysis.dispatch(h,q,'s138-path',guard=lambda *a:None)
        self.assertEqual(worker.call_count,1)
        self.assertEqual(out['charged_analysis_evaluations'],20)
        self.assertEqual(replay['operation_reuse']['additional_analysis_evaluations'],0)
        self.assertEqual(state(h)['mathematical_evaluations'],20)

    def test_tracking_ranking_uses_all_five_independent_conditions(self):
        cfg=configuration(True);vertices=cfg['task']['goal']['data']['vertices_m']
        def accepted_path(points):
            ev=evaluate(fixture(points,task=cfg['task']),cfg['task'])
            return assemble_acceptance(cfg,ev,dict(complete=True,solver_error_count=0,force_bound_violation_n=0,tracking_sampling_complete=True))
        stationary=accepted_path([vertices[0]]*3);complete=accepted_path(vertices)
        gap=feedback.task_gap(dict(status='evaluated',acceptance=stationary))
        self.assertTrue(gap['valid_complete']);self.assertEqual(len(gap['components']),5)
        self.assertGreater(gap['normalized_gap'],0.)
        query=NS(evaluation_mode='backend_task')
        self.assertLess(search.rank(dict(acceptance=complete),query,task_adapter(cfg).ranking_limits()),
            search.rank(dict(acceptance=stationary),query,task_adapter(cfg).ranking_limits()))
        incomplete=deepcopy(complete);incomplete['components']['tracking_sampling']['passed']=False
        self.assertGreater(search.rank(dict(acceptance=incomplete),query),search.rank(dict(acceptance=stationary),query))

    def test_search_task_violation_charges_per_solve_and_preserves_scope(self):
        h,c,ref=self.host();s=state(h);p=s['spec']['reference_parameters']
        spec=deepcopy(s['spec']);spec['length_constraint']={};spec['allowed_parameters']['segments.near.length_m']=[.15,.17]
        update(h,spec=spec)
        q=Search(variables=['segments.near.length_m'],bounds={'segments.near.length_m':[.15,.17]},fixed=p,
            objective='task_violation',operating_point='controller_start_input',scoring_window_s=.1,
            protocol=s['spec']['analysis_protocol'],max_evaluations=3)
        def scored(host,query,key,**kw):
            self.assertEqual(query['capability_method'],opt.CONIC)
            raw=dict(status='computed',charged_analysis_evaluations=2,proxy_values={},
                trajectory=dict(replay=dict(numerically_valid=True),replayed_violation=-.2,optimality_status='numerically_checked'),
                analysis_applicability=dict(full_task_supported=False))
            update(h,mathematical_evaluations=state(h)['mathematical_evaluations']+2)
            return dict(reference=save(h,raw))
        with patch.object(search,'construct',return_value=ref),patch.object(search,'verify_candidate',return_value=c),patch.object(analysis,'dispatch',side_effect=scored) as calls:
            out=search.run_search(h,q,'s138-search',guard=lambda *a:None,execute=None,capacity=None)
        self.assertEqual(calls.call_count,1)
        self.assertEqual(out['result']['resource_use']['actual_mathematical_evaluations'],2)
        best=out['result']['best_mathematical_candidate']
        self.assertEqual(best['proxy_values']['task_violation'],-.2)
        self.assertFalse(best['task_violation_scope']['coverage']['full_task_supported'])

    def test_core_math_search_admission_does_not_use_physical_budget(self):
        from tools.research import core
        h,c,ref=self.host();s=state(h);spec=deepcopy(s['spec'])
        spec['capabilities']=list(set(spec['capabilities'])|{'search'})
        spec.pop('research_decisions',None);update(h,spec=spec)
        q=dict(variables=['segments.near.length_m'],bounds={'segments.near.length_m':[.15,.17]},
            fixed=spec['reference_parameters'],objective='task_violation',operating_point='controller_start_input',
            scoring_window_s=.1,protocol=spec['analysis_protocol'],max_evaluations=2)
        plan=dict(action='search',search=q,hypothesis='fixture',expected_observation='fixture',weakening_observation='fixture',
            fixed_conditions='fixture',stopping_condition='fixture',interpretation='fixture')
        with (patch.object(core,'guard'),patch.object(core,'capacity',side_effect=AssertionError('No physical budget query')),
                patch.object(core,'run_search',return_value=dict(status='synthetic fixture'))):
            result=core.dispatch(h,plan,'s138-core-budget')
        saved=h.store.artifact(result['plan'])
        self.assertEqual(saved['admission']['admitted'],2)
        self.assertNotIn('internal_launches',saved['admission'])

    def test_precheck_saved_conditions_and_no_structure_attribution_from_A(self):
        path=Path('evidence/s138_task_conditioned/structure_precheck.json')
        value=json.loads(path.read_text(encoding='utf8'))
        self.assertEqual(len(value['cases']),6)
        self.assertEqual({digest(c['configuration']['task']) for c in value['cases']},
            {digest(c['configuration']['task']) for c in value['cases'][:2]})
        self.assertEqual(value['budgets']['conic_solves'],6)
        for name in ('provider_calls','mujoco_steps','ppo_training','formal_studies'):self.assertEqual(value['budgets'][name],0)
        for row in value['cases']:
            self.assertEqual(row['mathematics']['task_acceptance'],'unmeasured')
            self.assertTrue(row['reoptimized_evaluator']['evaluation']['task_success'])
        self.assertFalse(value['cases'][1]['original_evaluator']['evaluation']['task_success'])
        self.assertTrue(all(abs(c['C_minus_B'])<1e-8 for c in value['comparisons']))


if __name__=='__main__':unittest.main()
