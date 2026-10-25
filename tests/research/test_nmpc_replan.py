"""Fabricated plans test scheduling/provenance only; no scientific or Provider runs."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
from extensions.tendon_family.contracts import GVSTrajectoryParameters
from extensions.tendon_family import gvs_nmpc as nmpc
from extensions.tendon_family.gvs_trajectory import shifted_warm_plan,TrajectoryWorkspace
from tools.research.config import ROOT,resolve


def fabricated_workspace(parameters):
    w=NS(parameters=parameters,duration=.35,tracking=False,graph_s=0.,last=None,
        solver=NS(diagnostic_trace=False,complete_record=False),nominal_x=[0.,0.],nominal_u=[0.])
    w._motion=lambda q,v:(np.array([q[0],0.,0.]),np.array([v[0],0.,0.]))
    return w


def controller_fixture(cls=nmpc.DeadlineReachNMPCController,replan=.1):
    c=cls.__new__(cls)
    c.parameters=GVSTrajectoryParameters(replan_period_s=replan,recover_returned_tensions=False)
    c.period_s=.01;c.replan_steps=c.parameters.replan_steps(.01)
    c.workspace=fabricated_workspace(c.parameters);c.seed=None
    c.physics={};c.previous=np.array([0.]);c.coordinate_order=['fixture/q']
    c.plan=dict(identity='fabricated-plan',settling={},task={},robot={})
    c.observations=[];c.control_snapshots=[];c.record_update_ids=set()
    c.last={};c.cached_plan=None;c.last_solve_time=None;c.cached_update_id=None
    c.unusable_updates=0;c.stop_requested=False
    return c


def fabricated_result(t,horizon,accepted=True):
    return dict(accepted=accepted,optimization_converged=True,
        tensions=[[round(t*100)+i+1.] for i in range(horizon)],
        states=[[i/100.,i/100.] for i in range(horizon+1)],
        result=dict(status='converged',constraint_violation=0.),
        diagnostics=dict(return_status='Solve_Succeeded',selected_feasible_iteration=2,
            returned_iterate_constraint_violation=0.,construction_s=0.,solve_s=0.,
            validation_s=0.,policy_stop_reason=None),
        recovery=dict(selected=False,wall_s=0.),prediction_timing={},warm_start=dict(preparation_s=0.))


class ReplanTests(unittest.TestCase):
    def test_35_controls_four_solves_and_deadline_tail(self):
        c=controller_fixture();calls=[];rebuild_seeds=[]
        def solve(w,x,u,warm=None,*,elapsed_s,executed_intervals):
            calls.append((elapsed_s,w.parameters.horizon,executed_intervals))
            if warm is not None:rebuild_seeds.append(deepcopy(warm))
            out=fabricated_result(elapsed_s,w.parameters.horizon);w.last=out
            return out
        c.workspace.solve=lambda *a,**kw:solve(c.workspace,*a,**kw)
        def rebuild(task,robot,p,*args,**kw):
            w=fabricated_workspace(p);w.solve=lambda *a,**kw:solve(w,*a,**kw);return w
        geometry=dict(tip=np.zeros(3),gvs_projection=dict(projection_residual_max_rad_m=0.))
        with patch.object(nmpc,'execute_ideal_tension',side_effect=lambda p,u:(list(u),dict(actual_tension_n=list(u)))),\
                patch.object(nmpc,'TrajectoryWorkspace',side_effect=rebuild),\
                patch.object(nmpc.TaskDefinition,'model_validate'),patch.object(nmpc.RobotDescription,'model_validate'):
            actions=[c.command(i*.01,geometry,[0.],[0.]) for i in range(35)]
        np.testing.assert_allclose([a[0] for a in actions],np.arange(1,36))
        self.assertEqual(calls,[(0.,10,0),(.1,10,10),(.2,10,10),(.3,5,10)])
        self.assertEqual([r['time_s'] for r in c.observations if r['fresh_solve']],[0.,.1,.2,.3])
        self.assertEqual(sum(not r['fresh_solve'] for r in c.observations),31)
        self.assertEqual(rebuild_seeds[0]['shifted_executed_intervals'],10)
        self.assertEqual(len(rebuild_seeds[0]['tensions']),5)
        self.assertEqual(rebuild_seeds[0]['tensions'],[[30.]]*5)
        for i,row in enumerate(c.observations):
            self.assertAlmostEqual(row['one_step_prediction']['time_s'],(i+1)*.01)
            self.assertEqual(row['one_step_prediction']['applied_tension_n'],actions[i])
            if not row['fresh_solve']:
                self.assertEqual(row['reused_plan']['source_update_id'],(i//10)*10)
                self.assertIsNone(row['optimization_nonconverged'])
        from extensions.tendon_family.gvs_reporting import summarize
        task=NS(family='task.reach',timing=NS(duration_s=.35,sample_period_s=.01),
            goal=NS(data=dict(target_m=[0.,0.,0.])),evaluator=NS(parameters=NS(data=dict(tolerance_m=.01))))
        rows=[dict(time_s=(i+1)*.01,tip_m=[0.,0.,0.],tension_n=actions[i]) for i in range(35)]
        summary=summarize(task,dict(solver_status='incomplete',data=dict(data=dict(timings_s={}))),
            None,rows,c.observations,[],[100.])
        self.assertEqual((summary['actual_solver_calls'],summary['accepted_plans'],summary['converged_updates']),(4,4,4))
        self.assertEqual((summary['applied_control_updates'],summary['cached_control_intervals']),(35,31))
        self.assertEqual(summary['one_step_prediction_comparisons'][-1]['source_update_id'],30)
        from extensions.tendon_family.control_evidence import ControlEvidence,EvidenceQuery
        reader=ControlEvidence(None)
        source=dict(configuration=dict(policy={},task=dict(timing=dict(duration_s=.35))),
            manifest={},metadata=dict(candidate='fabricated',candidate_input={}),owner='fixture',files={})
        with patch.object(reader,'resolve',return_value=source),\
                patch.object(reader,'read_file',side_effect=lambda s,name,default:c.observations if name=='controller_observations.json' else default),\
                patch('extensions.tendon_family.gvs_profile.execution_scope',return_value={}):
            evidence=reader.query(EvidenceQuery(execution_id='fabricated',update_ids=[34]))
        self.assertFalse(evidence.capabilities['missing'])
        self.assertEqual(evidence.observations['updates'][0]['reused_plan']['source_update_id'],30)

    def test_legacy_default_solves_each_control_interval(self):
        c=controller_fixture(nmpc.GVSNMPCController,replan=None);calls=[]
        def solve(x,u,warm=None,*,elapsed_s,executed_intervals):
            calls.append(executed_intervals);return fabricated_result(elapsed_s,10)
        c.workspace.solve=solve
        geometry=dict(tip=np.zeros(3),gvs_projection=dict(projection_residual_max_rad_m=0.))
        with patch.object(nmpc,'execute_ideal_tension',side_effect=lambda p,u:(list(u),dict(actual_tension_n=list(u)))):
            for i in range(3):c.command(i*.01,geometry,[0.],[0.])
        self.assertEqual(calls,[0,1,1])
        self.assertTrue(all(r['fresh_solve'] for r in c.observations))

    def test_failure_expires_cached_plan_and_uses_original_bounded_hold(self):
        c=controller_fixture(nmpc.GVSNMPCController);attempts=[]
        def solve(x,u,warm=None,*,elapsed_s,executed_intervals):
            attempts.append(elapsed_s)
            if elapsed_s>=.1:raise RuntimeError('fabricated unusable solve')
            return fabricated_result(elapsed_s,10)
        c.workspace.solve=solve
        geometry=dict(tip=np.zeros(3),gvs_projection=dict(projection_residual_max_rad_m=0.))
        with patch.object(nmpc,'execute_ideal_tension',side_effect=lambda p,u:(list(u),dict(actual_tension_n=list(u)))):
            actions=[c.command(i*.01,geometry,[0.],[0.]) for i in range(13)]
        self.assertEqual(attempts,[0.,.1,.11,.12])
        self.assertEqual(actions[-4:],[[10.]]*4)
        self.assertTrue(c.stop_requested);self.assertIsNone(c.cached_plan)
        self.assertTrue(c.observations[-2]['failure_response_used'])

    def test_legacy_default_and_grid_coverage(self):
        self.assertEqual(GVSTrajectoryParameters().replan_steps(.01),1)
        self.assertEqual(GVSTrajectoryParameters(replan_period_s=.1).replan_steps(.01),10)
        for p in (GVSTrajectoryParameters(replan_period_s=.015),
                  GVSTrajectoryParameters(replan_period_s=.1,horizon=9)):
            with self.assertRaisesRegex(ValueError,'REPLAN_PERIOD'):p.replan_steps(.01)
        source=dict(states=[[i] for i in range(21)],tensions=[[i] for i in range(10)])
        shifted=shifted_warm_plan(source,10,2,5)
        self.assertEqual(shifted['states'],[[20]]*11)
        self.assertEqual(shifted['tensions'],[[9]]*5)
        self.assertEqual(source['tensions'][0],[0])

    def test_workspace_shifts_all_executed_intervals_and_records_actual_count(self):
        p=GVSTrajectoryParameters(replan_period_s=.1,regenerate_warm_states=False)
        w=TrajectoryWorkspace.__new__(TrajectoryWorkspace)
        w.parameters=p;w.tracking=False;w._set_prediction_time=lambda t:{}
        w.n=1;w.tendons=['fixture'];w.state_scales=np.ones(2);w.graph_s=0.
        w.nominal_x=[0.,0.];w.nominal_u=[0.];w.period=.01;w.goal_tolerance=.01
        w._tail_solver=None;w.last=dict(states=[[i,i] for i in range(11)],tensions=[[i] for i in range(10)])
        values={f'x/{i}/{j}':0. for i in range(11) for j in range(2)}
        values.update({f'u/{i}/fixture':0. for i in range(10)});values['previous_u/fixture']=0.
        w.problem=NS(variables={k:dict(bounds=[0.,1.]) for k in values},initial_guess=deepcopy(values))
        raw=NS(status='converged',constraint_violation=0.,optimum=values,model_dump=lambda **kw:dict(status='converged'))
        w.solver=NS(diagnostic_trace=False,complete_record=False,last_diagnostics={},solve=lambda *a,**kw:raw)
        w._extend_tail=lambda x,u,*a:(np.asarray(x),dict(fixture=True))
        output=w.solve([0.,0.],[0.],elapsed_s=.1,executed_intervals=10)
        self.assertEqual(output['warm_start']['executed_intervals'],10)
        self.assertEqual([w.problem.initial_guess[f'u/{i}/fixture'] for i in range(10)],[9.]*10)
        self.assertEqual(w.problem.initial_guess['x/0/0'],0.)

    def test_new_pair_frozen_common_replanning_and_unchanged_task_grid(self):
        specs=[resolve(ROOT/'configs/research'/f'study_c3_{a}_ab.json') for a in ('heuristic','math_search')]
        for s in specs:
            self.assertEqual(s['nmpc_replan_period_s'],.1)
            self.assertEqual(s['configuration']['policy']['controller']['parameters']['data']['recipe']['replan_period_s'],.1)
            timing=s['canonical_task']['timing']
            self.assertEqual((timing['duration_s'],timing['control_period_s'],timing['sample_period_s'],timing['timestep_s']),(.35,.01,.01,.0005))
        self.assertEqual(specs[0]['canonical_task'],specs[1]['canonical_task'])

    def test_generated_candidate_cannot_override_frozen_common_period(self):
        from tests.research.test_mixed_search import MixedSearchTests
        from tools.research.state import state,update
        from tools.research.design import generate_candidate
        fixture=MixedSearchTests();fixture.setUp();self.addCleanup(fixture.cleanup)
        h=fixture.host;s=state(h);spec=deepcopy(s['spec']);base=deepcopy(s['base_configuration'])
        spec['nmpc_replan_period_s']=.1
        base['policy']['controller']['parameters']['data']['recipe']['replan_period_s']=.1
        update(h,spec=spec,base_configuration=base)
        q=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
            segment_count=1,tendon_count=3,controller_recipe=dict(replan_period_s=.01))
        result=generate_candidate(h,q,dict(origin='fabricated-interface-fixture'))
        self.assertEqual((result['status'],result['reason']),('invalid','FROZEN_STUDY_NMPC_REPLAN_PERIOD'))
        self.assertFalse(state(h)['candidates'])


if __name__=='__main__':unittest.main()
