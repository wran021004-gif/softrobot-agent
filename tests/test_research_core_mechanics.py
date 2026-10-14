"""Focused fixtures for feedback, current-study mechanics and handoff; no real solves."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from tools.research import core as core
from tools.research import mechanics as mechanics
from tools.research.feedback import eligibility
from schemas.research_core import Plan
from tools.research.mechanics import LegacySearch as Search


class MechanicsTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=core.ROOT/'runs',prefix='mechanics-fixture-')
        spec=core.read(core.ROOT/'examples/mechanics_control/specification.json')
        spec.update(study_id='mechanics-fixture-'+Path(self.temp.name).name,started_unix=time.time())
        path=Path(self.temp.name)/'spec.json';core.atomic_json(path,spec)
        self.host=core.prepare(path,Path(self.temp.name)/'business')
        core.update(self.host,freeze='fixture-commit')

    def tearDown(self):
        import gc
        gc.collect();self.temp.cleanup()

    def plan(self,action,**kwargs):
        return dict(action=action,**{k:'fixture' for k in ('hypothesis','expected_observation','weakening_observation',
            'fixed_conditions','stopping_condition','interpretation')},**kwargs)

    def test_candidate_reuse_retains_failed_offline_lineage(self):
        h=self.host; s=core.state(h)
        source=core.save(h,dict(operation='solve',candidate={'d':0.},trajectory_reference=core.save(h,{'trajectory':'fixture'}),
            relaxed_nlp_feasible=True,original_task_feasible=False))
        core.update(h,mechanics_results=[source])
        a=mechanics.handoff(h,source);b=mechanics.handoff(h,source)
        self.assertEqual(a['candidate'],s['reference_candidate']);self.assertEqual(a['candidate'],b['candidate'])
        self.assertTrue(a['exploratory']);self.assertFalse(a['original_task_feasible'])
        self.assertEqual(len(core.state(h)['handoffs']),2)
        with self.assertRaisesRegex(ValueError,'MATCH_MECHANICS'):mechanics.handoff(h,source,dict(d=.5))
        with self.assertRaisesRegex(ValueError,'OWNED_CURRENT'):mechanics.source(h,s['reference_candidate'])

    def test_failed_packaging_recovers_once_and_shares_budget(self):
        h=self.host;before=core.state(h)['numerical_s'];calls=[]
        def worker(args,**kwargs):
            req=core.read(args[-2]);calls.append(req['operation'])
            if req['operation']=='solve':
                core.atomic_json(req['progress'],dict(phase='solver_returned',variable_order=['design/d']))
                core.atomic_json(args[-1],dict(status='engineering_error',termination_reason='injected packaging failure'))
            else:
                core.atomic_json(args[-1],dict(status='iteration_limit',candidate=dict(d=0.,tensions_n=[[.2]*6]*35),
                    original_task_feasible=False,relaxed_nlp_feasible=True,recovered_without_nlp=True,costs_s={'solve':.1}))
            return SimpleNamespace(stdout=b'fixture',returncode=0)
        with patch.object(core,'guard'),patch.object(mechanics.subprocess,'run',side_effect=worker):
            output=core.dispatch(h,self.plan('mechanics',mechanics={}), 'fixture-mechanics',origin='engineering')
            cached=core.dispatch(h,self.plan('mechanics',mechanics={}), 'fixture-mechanics',origin='engineering')
        self.assertEqual(calls,['solve','recover']);self.assertEqual(core.state(h)['offline_nlp'],1)
        self.assertEqual(core.state(h)['numerical_reserved_s'],0.)
        self.assertGreater(core.state(h)['numerical_s'],before)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(cached['operation_reuse']['additional_numerical_s'],0.)
        self.assertTrue(output['result']['handoff']['exploratory'])
        value=h.store.artifact(output['result']['reference']);self.assertTrue(value['recovered_without_nlp'])
        self.assertIsNotNone(value['checkpoint_reference'])

    def test_confirmation_feedback_distinguishes_candidate_execution_and_cost(self):
        h=self.host;s=core.state(h);c=core.verify_candidate(h,s['reference_candidate'])
        self.assertFalse(eligibility(h,s['reference_candidate'])['eligible'])
        r=dict(candidate=s['reference_candidate'],profile_identity=s['profile']['identity'],
            scientific_configuration=c['scientific_configuration'],acceptance={'accepted':True},
            role='search',owning_study=h.run_id,owner_run_id=h.run_id+'-exec-fixture',numerical_s=40.)
        ref=core.save(h,r);core.update(h,results=[ref])
        self.assertTrue(eligibility(h,ref)['eligible']);self.assertEqual(eligibility(h,ref)['selected_execution'],ref)
        r['acceptance']['accepted']=False;failed=core.save(h,r);core.update(h,results=[ref,failed])
        self.assertIn('result did not pass complete original task evaluation',eligibility(h,failed)['reasons'])
        core.update(h,research_status='stopped');self.assertFalse(eligibility(h,ref)['eligible'])

    def test_mixed_numerical_and_incomplete_diagnosis_does_not_resolve_physics(self):
        h=self.host
        numerical=core.save(h,dict(operation='replay',status='completed',execution_id='bdf-fixture',replay={'gates_passed':False}))
        failed=core.save(h,dict(status='execution_incomplete',execution_id='failed-physics-fixture'))
        core.update(h,mechanics_results=[numerical],results=[failed])
        with patch('extensions.tendon_family.control_evidence.ControlEvidence.resolve',side_effect=AssertionError('no sealed physical export')):
            output=core.diagnose(h,[numerical,failed])
        self.assertFalse(output['numerical_evidence'][0]['physical_validation'])
        self.assertFalse(output['incomplete_executions'][0]['acceptance_available'])
        self.assertEqual(output['execution_evidence'],[])

    def test_boundary_control_search_two_distinct_configs_at_fixed_structure(self):
        from tools.design_optimization import solve
        h=self.host;profile=core.state(h)['profile']
        for start in (.025,.10):
            q=Search(variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':(.025,.10)},
                fixed=dict(d=.8,holding_tip_speed_weight=start,terminal_tip_speed_weight=.10),max_evaluations=2)
            seen=[]
            def evaluator(problem,values,candidate_id):
                seen.append(values)
                return dict(status='evaluated',acceptance=dict(accepted=False,status='valid_failure',metrics=dict(
                    terminal_error_m=.02,holding_max_error_m=.02,holding_max_speed_m_s=.03)),evidence={'fixture':True})
            result=solve(core.search_problem(h,q,2),evaluator=evaluator,evaluation_profile=profile)
            self.assertEqual(len(result.evaluated),2)
            self.assertEqual(len({v['holding_tip_speed_weight'] for v in seen}),2)
            self.assertEqual({tuple(v['lengths_m']) for v in seen},{(.1644,.1056)})
            self.assertEqual({v['terminal_tip_speed_weight'] for v in seen},{.10})

    def test_mechanics_admission_preserves_confirmation_capacity(self):
        h=self.host;s=core.state(h)
        core.update(h,numerical_s=s['spec']['budgets']['numerical_s']-900.-3800.+1.)
        with patch.object(core,'guard'),patch.object(mechanics.subprocess,'run',side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(ValueError,'MECHANICS_AND_REPETITION_RESERVE'):mechanics.dispatch(h,'solve',{},'no-fit')
        self.assertEqual(core.state(h)['offline_nlp'],0)

    def test_diagnostic_inspection_uses_solver_order_after_sorted_json(self):
        from tools.research.diagnostic import inspect_problem
        seen=[]
        def evaluate(problem,values):
            seen.append(values)
            return dict(objective=7.,scaled_violation=0.,constraint_values=[0.])
        problem=SimpleNamespace(variables={'a':{},'z':{}},objective_function=SimpleNamespace(
            data={'variable_order':['z','a']},model_dump=lambda **kw: {'serialized':'fixture'}),
            constraints=[SimpleNamespace(name='dynamics',lower=0.,upper=0.)])
        ws=SimpleNamespace(problem=problem,solver=SimpleNamespace(evaluate_candidate=evaluate),_tail_solver=None)
        r=dict(initialization={'initialized_vector':[2.,3.],'variable_order':['z','a']},
            model_identity=core.digest({'serialized':'fixture'}),selected_feasible_plan={'z':2.,'a':3.},
            prediction_timing={'current_time_s':.01},mutable_workspace={'cached_solver':True},
            diagnostics=dict(initial_objective=7.,initial_scaled_violation=0.,selected_feasible_candidate={'objective':7.},
                constraint_values=[0.],constraint_order=['dynamics'],constraint_lower=[0.],constraint_upper=[0.]))
        inspection=inspect_problem(ws,r)
        self.assertEqual(seen[0],{'z':2.,'a':3.});self.assertEqual(inspection['initial_objective_difference'],0.)
        self.assertTrue(inspection['variable_order_equal'])

    def test_progress_reader_lock_retries_replacement_without_repeating_command(self):
        from extensions.tendon_family import backends
        folder=Path(self.temp.name)/'progress';folder.mkdir()
        observations=[dict(complete_update_record=dict(model_identity='a'*64,resolved_problem={'graph':'fixture'},
            problem_variables={'x':{'bounds':[1.,1.]}},initial_guess={'x':1.}))]
        original=backends.atomic_json;attempts=[]
        def save(path,value):
            attempts.append(path.name)
            if path.name=='nmpc_updates.json':
                path.with_suffix('.json.tmp').write_text(core.json.dumps(value),encoding='utf8')
                error=PermissionError('injected Windows reader lock');error.winerror=5;raise error
            original(path,value)
        with patch.object(backends,'atomic_json',side_effect=save):backends.save_nmpc_progress(folder,observations)
        saved=core.read(folder/'nmpc_updates.json')[0]['complete_update_record']
        self.assertNotIn('resolved_problem',saved);self.assertIn('resolved_problem_reference',saved)
        self.assertLessEqual(len(saved['resolved_problem_reference']['filename']),len('nmpc_updates.json'))
        self.assertEqual(core.read(folder/saved['resolved_problem_reference']['filename']),{'graph':'fixture'})
        self.assertEqual(attempts.count('nmpc_updates.json'),1);self.assertEqual(len(observations),1)
        self.assertEqual(saved['problem_variables']['x']['bounds'],[1.,1.])

    def test_structure_improvement_requires_comparable_control_adaptation(self):
        h=self.host;s=core.state(h);rows=[]
        def execution(d,weight=.1,role='development',selected=None,error=.003):
            candidate=core.construct(h,dict(d=d,holding_tip_speed_weight=weight,terminal_tip_speed_weight=.1),{'fixture':True})
            c=h.store.artifact(candidate)
            ref=core.save(h,dict(candidate=candidate,profile_identity=s['profile']['identity'],scientific_identity=c['identity'],
                scientific_configuration=c['scientific_configuration'],status='evaluated',role=role,selected_execution=selected,
                acceptance=dict(accepted=True,metrics=dict(terminal_error_m=error,holding_max_error_m=error,holding_max_speed_m_s=.01))))
            rows.append(ref);return ref
        execution(0.,error=.006);selected=execution(.5)
        execution(.5,role='confirmation',selected=selected);execution(.5,role='confirmation',selected=selected)
        core.update(h,results=rows,selected=selected)
        self.assertTrue(core.claims(h)['limited_repeat_supported_acceptance'])
        self.assertFalse(core.claims(h)['parameter_improvement_attribution_permitted'])
        execution(0.,weight=.075,error=.006);execution(.5,weight=.075)
        core.update(h,results=rows)
        self.assertTrue(core.claims(h)['comparable_control_adaptation_for_structure_comparison'])
        self.assertTrue(core.claims(h)['parameter_improvement_attribution_permitted'])


    def test_effective_research_work_allowance_reaches_solver_without_internal_limit(self):
        from schemas.research_core import Plan
        from tools import casadi_feedback_worker as feedback
        s=core.state(self.host);spec=s['spec'];spec.update(offline_solver_s=3300,offline_stopping_policy='research_work_v1')
        spec['mechanics_allowances']['solve_s']=3300;core.update(self.host,spec=spec)
        captured=[]
        def worker(argv,**kwargs):
            request=core.read(argv[-2]);captured.append(request)
            self.assertEqual(kwargs['timeout'],3300)
            core.atomic_json(argv[-1],dict(status='fixture_no_candidate'))
            return SimpleNamespace(stdout=b'',returncode=0)
        with patch.object(core,'guard'),patch.object(mechanics.subprocess,'run',side_effect=worker):
            mechanics.dispatch(self.host,'solve',Plan.model_validate(self.plan('mechanics',mechanics={})).mechanics,'allowance')
        request=captured[0];self.assertEqual(request['offline_solver_s'],3300);self.assertEqual(request['offline_stopping_policy'],'research_work_v1')
        problem=SimpleNamespace(variables={'slack/position':{},'slack/speed':{},**{f'u/{k}/0':{} for k in range(35)}},constraints=[])
        workspace=SimpleNamespace(mechanics_construction_s=1,assembly_s=2,m=1,assemble=lambda *a:problem)
        class ReachedSolver(Exception):pass
        class Solver:
            def __init__(self,options):
                self.options=options
                self.last_diagnostics={}
            def _bounds(self,*args):return [],[],[]
            def solve(self,*args):
                self_test.assertEqual(self.options['max_iterations'],1000)
                self_test.assertIsNone(self.options['max_cpu_s']);self_test.assertIsNone(self.options['max_wall_s'])
                raise ReachedSolver()
        self_test=self;progress=Path(self.temp.name)/'effective_progress.json'
        with patch.object(feedback,'Workspace',return_value=workspace),patch.object(feedback,'IpoptSolver',Solver):
            with self.assertRaises(ReachedSolver):feedback.solve(request['configuration'],request['arguments'],'reverse',progress=progress,execution={'offline_solver_s':request['offline_solver_s'],'stopping_policy':request['offline_stopping_policy']})
        self.assertEqual(core.read(progress)['phase'],'solver_entered')
        self.assertIsNone(core.read(progress)['options']['max_wall_s'])
