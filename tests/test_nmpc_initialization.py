"""Concrete single-factor, stopping interpretation and delivery wiring checks."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from tools.state_io import read
from tools.spec_tools import ROOT
from extensions.tendon_family.diagnostic_math import SavedStateCheck,changed_recipe,termination_facts,local_pair
from schemas.casadi_feedback import InitializationPlan,CloseoutPlan,ControlChoice
from schemas.platform import EvidenceRef

REF=dict(artifact_id='a'*64,media_type='application/json')
BASE=dict(hypothesis='Stopping may retain initialization.',supporting_evidence=[REF],weakening_observation='No progress.',
    expected_observation='Improved feasible plan.',fixed_conditions='Same frozen task and physics.',revision_or_stop_rule='Consume evidence then STOP.',
    disposition='Bounded comparison.',limitations=['Local evidence only.'])


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.cfg=read(ROOT/'evidence/casadi_nmpc_research_20261010/closed_loop_01_configuration.json')
        self.recipe=self.cfg['policy']['controller']['parameters']['data']['recipe']

    def test_only_declared_budget_changes_no_other_ceiling(self):
        p=changed_recipe(self.recipe,'feasible_return.budget_s',30.)
        self.assertEqual(p['max_cpu_s'],30.);self.assertEqual(p['max_iterations'],120)
        p['feasible_return']['budget_s']=15.
        self.assertEqual(p,self.recipe)
        with self.assertRaises(ValueError):changed_recipe(self.recipe,'feasible_return.budget_s',31.)
        with self.assertRaises(ValueError):changed_recipe(self.recipe,'holding_tip_speed_weight',.2)
        with self.assertRaises(ValueError):SavedStateCheck(binding=REF,update_id=0,operation='local_comparison')

    def test_actual_termination_is_reported_without_budget_ineffectiveness(self):
        d=dict(policy_stop_reason=None,return_status='Maximum_Iterations_Exceeded',iterations=120,solve_s=19.,
            options=dict(feasible_return=dict(budget_s=30.)))
        result=termination_facts(d)
        self.assertEqual(result['actual_stop_reason'],'Maximum_Iterations_Exceeded')
        self.assertFalse(result['feasible_return_budget_triggered']);self.assertFalse(result['budget_effect_isolated'])
        self.assertIn('cannot establish',result['interpretation'])
        d.update(return_status='User_Requested_Stop',policy_stop_reason='relative_seed_improvement')
        self.assertEqual(termination_facts(d)['actual_stop_reason'],'relative_seed_improvement')

    def test_native_pair_has_authorized_300s_allowance(self):
        from tools import research_casadi_feedback as research
        with patch.object(research,'INITIALIZATION',True),patch.dict(research.CEILINGS,pair_wall_s=300.):
            cfg=research.configuration()
        allowance=cfg['policy']['operation_allowances']['diagnosis.saved_state_check']
        self.assertEqual(allowance,dict(timeout_s=300.,reserve_s=300.))

    def test_pair_uses_saved_time_previous_input_and_separate_seed_workspaces(self):
        captured=[];artifacts=[];cfg=self.cfg
        updates=[dict(time_s=.00,actual_tension_n=[.3]*6),
            dict(time_s=.01,actual_tension_n=[7.]*6,measured_initial_state=[0.]*24,effective_horizon=9)]
        class Workspace:
            def __init__(self,task,robot,p,state,previous,settling):
                self.solver=SimpleNamespace(evaluate_candidate=lambda *a:dict(feasible=True));self.n=12;self.period=.01
                self.target=np.array([.29,.035,.19]);self.problem='fixture'
                captured.append(dict(p=deepcopy(p),state=list(state),previous=list(previous),ws=self))
            def _motion(self,*a):return np.array([.29,.035,.19]),np.zeros(3)
            def solve(self,state,previous,**kw):
                captured[-1]['elapsed_s']=kw['elapsed_s'];captured[-1]['warm']=kw.get('warm')
                d=dict(selected_feasible_iteration=-1,policy_stop_reason=None,return_status='Maximum_Iterations_Exceeded',
                    iterations=120,solve_s=1.,options=dict(feasible_return=self_p['feasible_return']))
                return dict(states=[[0.]*24]*10,tensions=[[.3]*6]*9,result=dict(optimum={'raw':'fixture'}),diagnostics=d)
        self_p=self.recipe
        snapshot=dict(plans={k:dict(verification=dict(scaled_violation=v),objective_components=dict(total=f),metrics={})
            for k,v,f in [('initial',0.,100.),('returned',.2,90.),('selected',0.,100.)]})
        ctx=SimpleNamespace(save_artifact=lambda v,*a:artifacts.append(v) or EvidenceRef.model_validate(REF))
        args=SavedStateCheck(binding=REF,update_id=1,operation='local_comparison',changed_parameter='feasible_return.budget_s',changed_value=30.,max_wall_s=300.)
        with patch('extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace',Workspace),patch('extensions.tendon_family.diagnostic_math.charge_units'),\
            patch('extensions.tendon_family.control_evidence.plan_metrics',return_value={}),patch('extensions.tendon_family.control_evidence.capture_snapshot',return_value=snapshot):
            result=local_pair(ctx,args,None,dict(configuration=cfg,files={'controller_observations.json':REF}),updates)
        self.assertEqual(len(captured),2);self.assertIsNot(captured[0]['ws'],captured[1]['ws'])
        for c in captured:
            self.assertEqual(c['previous'],[.3]*6);self.assertEqual(c['elapsed_s'],.01);self.assertEqual(c['p']['horizon'],9);self.assertIsNone(c['warm'])
        self.assertEqual(captured[1]['p']['feasible_return']['budget_s'],30.)
        self.assertEqual(result['previous_input_reference']['pointer'],'/0/actual_tension_n')
        self.assertIn('diagnostics',artifacts[0])
        self.assertEqual(artifacts[1]['snapshot']['plans']['returned']['verification']['scaled_violation'],.2)
        self.assertEqual(artifacts[1]['snapshot']['plans']['selected']['verification']['scaled_violation'],0.)

    def test_native_actions_feedback_and_stop_contract(self):
        plan=InitializationPlan(action='saved_state_comparison',comparison=dict(update_id=20,changed_parameter='feasible_return.budget_s',changed_value=30.),**BASE)
        self.assertEqual(plan.comparison.update_id,20)
        with self.assertRaises(ValueError):InitializationPlan(action='solve',**BASE)
        self.assertEqual(CloseoutPlan(action='stop',**BASE).action,'stop')
        with self.assertRaises(ValueError):CloseoutPlan(action='stop',comparison=plan.comparison,**BASE)
        from tools.nmpc_initialization import compact_pair
        rows=[dict(label='variant',metrics={},plans={'returned':{'objective_components':{'total':90.}}},verification={},reference=REF,
            selected_iteration=-1,stop_reason=None,termination={'actual_stop_reason':'Maximum_Iterations_Exceeded'},complete_cost_s=1.)]
        compact=compact_pair(dict(changed_factor='feasible_return.budget_s',rows=rows))
        self.assertIn('returned',compact['rows'][0]['plans'])

    def test_revision_budget_reaches_controller_recipe_and_recording_scope(self):
        from tools.casadi_closed_loop import resolve_candidate,finish_closed_loop
        from tools.nmpc_initialization import ArchiveStore,SOURCE
        from extensions.tendon_family.control_evidence import RECORD_UPDATE_IDS
        store=ArchiveStore();sources=read(SOURCE/'state.json')['candidate_sources']
        candidate=EvidenceRef(artifact_id='0e16077e9183ebcd64729eb982aa5a73e5eb03e111d5d7ed402552ca16db345b')
        choice=ControlChoice(candidate=candidate,feasible_return_budget_s=30.,record_update_ids=[20])
        cfg,report=resolve_candidate(store,candidate,sources[candidate.artifact_id],choice,'fixture',self.cfg['policy'])
        recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        self.assertEqual(recipe['feasible_return']['budget_s'],30.)
        self.assertEqual(recipe['max_cpu_s'],30.);self.assertEqual(recipe['max_iterations'],120)
        self.assertEqual(report['changes'],{})
        pending=dict(owner_run_id='fixture',configuration=REF,control=dict(record_update_ids=[20]))
        parent=SimpleNamespace(store=SimpleNamespace(session=lambda *a:dict(state=dict(pending=pending)),artifact=lambda *a:cfg))
        seen=[]
        def at_worker(*a):seen.append(RECORD_UPDATE_IDS.get());raise RuntimeError('fixture stops before backend')
        with patch('tools.execution_completion.complete_execution',side_effect=at_worker):
            with self.assertRaisesRegex(RuntimeError,'fixture stops'):
                finish_closed_loop(parent,child=SimpleNamespace(),started=0.)
        self.assertEqual(seen,[(20,)]);self.assertEqual(RECORD_UPDATE_IDS.get(),())

if __name__=='__main__':unittest.main()
