"""Focused checks of saved evidence, evaluation, selection and recovery wiring."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import casadi as ca
import numpy as np
from extensions.optimization.ipopt import IpoptSolver,expression_payload
from schemas.platform import Objective,EvidenceRef
from schemas.platform_math import OptimizationProblem,OptimizationConstraint,OptimizationResult
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from tools.nmpc_feasibility import residual_row,saved_vector,schedule_identity
from tools.state_io import read
from tools.spec_tools import ROOT


class FeasibilityTests(unittest.TestCase):
    def test_saved_evaluation_never_constructs_or_runs_nlp(self):
        x=ca.MX.sym('x');bundle,selectors=expression_payload(['x'],dict(variables=dict(x=x),expression=x*x),dict(dynamics=x-.5))
        problem=OptimizationProblem(variables={'x':dict(type='number',bounds=[0.,1.])},objective=Objective(metric='cost',direction='minimize',units='1'),
            objective_function=bundle,constraints=[OptimizationConstraint(name='dynamics',expression=selectors[0],units='1',lower=0.,upper=0.)])
        solver=IpoptSolver()
        with patch('extensions.optimization.ipopt.ca.nlpsol',side_effect=AssertionError('Hidden NLP')),patch('extensions.optimization.ipopt._EXPRESSION_FUNCTIONS',{}):
            good=solver.evaluate_candidate(problem,{'x':.5});bad=solver.evaluate_candidate(problem,{'x':.6})
        self.assertTrue(good['feasible']);self.assertFalse(bad['feasible']);self.assertAlmostEqual(bad['constraint_values'][0],.1)
        self.assertEqual(solver._compiled,{});self.assertIsNone(solver.last_diagnostics)

    def test_actual_saved_rejected_vector_and_row_mapping(self):
        saved=read(ROOT/'evidence/nmpc_initialization_20261010/pair_variant_snapshot.json')
        values=saved_vector(saved,'returned');n=len(saved['snapshot']['measured_initial_state'])//2
        self.assertEqual(n,12)
        self.assertGreater(values['u/0/near_t0'],1.)
        self.assertAlmostEqual(saved_vector(saved,'selected')['u/0/near_t0'],.2)
        from extensions.tendon_family.gvs import coordinate_order
        cfg=read(ROOT/'evidence/nmpc_initialization_20261010/source_binding.json')['source']['configuration']
        coordinates=coordinate_order(cfg['robot']['structure']['data'],saved['parameters']['basis'])
        force=residual_row('dynamics_5_13',-.0009537607210136773,coordinates,.2,.01)
        self.assertEqual(force['coordinate'],coordinates[1]);self.assertAlmostEqual(force['start_s'],.25);self.assertAlmostEqual(force['end_s'],.26)
        self.assertAlmostEqual(force['signed_physical_residual'],-9.537607210136773e-7)
        kin=residual_row('dynamics_4_1',.002,coordinates,.2,.01)
        self.assertEqual(kin['kind'],'kinematic_consistency');self.assertAlmostEqual(kin['signed_physical_residual'],.02)
        same=deepcopy(saved);same['snapshot']['plans']['checkpoint_1']['tensions']=saved['snapshot']['plans']['returned']['tensions']
        self.assertEqual(schedule_identity(same,'returned'),schedule_identity(same,'checkpoint_1'))

    def test_live_recovery_preserves_solver_status_and_feasible_incumbent(self):
        ws=TrajectoryWorkspace.__new__(TrajectoryWorkspace);ws.n=1;ws.state_scales=np.array([10.,1000.]);ws.tendons=['a'];ws.problem='frozen'
        selected=OptimizationResult(status='feasible_early_stop',optimum={'u/0/a':.2},objective_value=100.,constraint_violation=0.,iterations=18)
        ws.solver=SimpleNamespace(last_diagnostics={'initial_objective':100.,'returned_iterate_objective':10.},
            last_returned_optimum={'u/0/a':7.},diagnostic_trace=True)
        repaired={'u/0/a':7.}
        with patch.object(ws,'regenerate_tensions',return_value=dict(optimum=repaired,integration_s=1.,steps=[],partial_states=[],error=None)):
            for feasible,objective in [(False,5.),(True,101.),(True,20.)]:
                ws.solver.evaluate_candidate=lambda *a:dict(feasible=feasible,objective=objective,scaled_violation=0. if feasible else .1)
                result,recovery=ws._recover_returned(selected,[0.,0.])
                self.assertEqual(result.iterations,18);self.assertEqual(result.status,selected.status)
                if feasible and objective<100.:
                    self.assertTrue(recovery['selected']);self.assertEqual(result.optimum,repaired)
                else:self.assertIs(result,selected)
        with patch.object(ws,'regenerate_tensions',return_value=dict(optimum=None,integration_s=1.,steps=[],partial_states=[[0.,0.]],error='root failure')):
            result,recovery=ws._recover_returned(selected,[0.,0.]);self.assertIs(result,selected);self.assertFalse(recovery['selected'])

    def test_recovery_flag_reaches_real_controller_recipe(self):
        from tools.casadi_closed_loop import resolve_candidate,validate_control
        from tools.nmpc_initialization import ArchiveStore,SOURCE,CANDIDATE
        from schemas.casadi_feedback import ControlChoice
        store=ArchiveStore();state=read(SOURCE/'state.json');candidate=EvidenceRef(artifact_id=CANDIDATE)
        cfg=read(ROOT/'evidence/casadi_nmpc_research_20261010/closed_loop_01_configuration.json')
        choice=ControlChoice(candidate=candidate,recover_returned_tensions=True,record_update_ids=[20])
        result,report=resolve_candidate(store,candidate,state['candidate_sources'][CANDIDATE],choice,'fixture',cfg['policy'])
        p=result['policy']['controller']['parameters']['data']['recipe'];self.assertTrue(p['recover_returned_tensions'])
        self.assertEqual((p['feasible_return']['budget_s'],p['max_cpu_s'],p['max_iterations'],p['substeps']),(15.,30.,120,1))

    def test_root_return_must_pass_equations(self):
        ws=TrajectoryWorkspace.__new__(TrajectoryWorkspace);ws.state_scales=np.array([10.,1000.])
        ws._tail_solver=lambda *a:np.array([0.,0.]);ws._tail_residual=lambda *a:np.array([0.,.01])
        with patch.object(ws,'_prepare_tail',return_value=0.):
            with self.assertRaisesRegex(RuntimeError,'FEASIBILITY_CHECK'):ws._extend_tail([0.,0.],[1.])

    def test_snapshot_distinguishes_ipopt_regenerated_and_delivered(self):
        from extensions.tendon_family.control_evidence import capture_snapshot
        from extensions.tendon_family.contracts import GVSTrajectoryParameters
        order=['x/0/0','x/0/1','x/1/0','x/1/1','u/0/a','previous_u/a']
        selected=dict(zip(order,[0.,0.,0.,0.,.2,.2]));repaired=dict(selected,**{'u/0/a':7.})
        d=dict(variable_order=order,retained_diagnostic_points=[dict(label='selected',vector=list(selected.values()),objective=100.)],
            selected_feasible_iteration=0,policy_stop_reason='budget_best_feasible',return_status='User_Requested_Stop',iteration_trace=[],
            solve_s=15.,validation_s=.01,construction_s=.1,function_statistics={})
        ws=SimpleNamespace(n=1,state_scales=np.array([10.,1000.]),tendons=['a'],period=.01,problem='frozen',
            parameters=GVSTrajectoryParameters(horizon=1),solver=SimpleNamespace(evaluate_candidate=lambda *a:dict(feasible=True,objective=20.,scaled_violation=0.)))
        solved=dict(diagnostics=d,recovery=dict(selected=True,candidate_optimum=repaired),result=dict(optimum=repaired),measured_initial_state=[0.,0.],
            previous_tensions_n=[.2],recording={},accepted=True,prediction_timing={},integration='implicit',warm_start=dict(preparation_s=.1),update_wall_s=16.)
        with patch('extensions.tendon_family.control_evidence.objective_components',return_value={'total':100.}),patch('extensions.tendon_family.control_evidence.plan_metrics',return_value={}):
            snapshot=capture_snapshot(ws,solved,20,.2,[7.],{'gvs_projection':{}})
        self.assertEqual(snapshot['plans']['selected']['tensions'],[[.2]])
        self.assertEqual(snapshot['plans']['regenerated']['tensions'],[[7.]])
        self.assertEqual(snapshot['plans']['delivered']['tensions'],[[7.]])
        self.assertEqual(snapshot['selection']['source'],'reintegrated_returned_iterate')
        self.assertIsNone(snapshot['selection']['selected_iteration']);self.assertEqual(snapshot['selection']['ipopt_selected_iteration'],0)


if __name__=='__main__':unittest.main()
