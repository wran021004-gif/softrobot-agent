"""Focused changes only; no NLP solve. Numeric tests run inside speed reservation."""
import unittest
import numpy as np
import casadi as ca
from pydantic import ValidationError
from schemas.casadi_feedback import Candidate,Plan
from extensions.tendon_family.gvs_codesign import Workspace
from tools.casadi_feedback_worker import assess


class PlanTests(unittest.TestCase):
    def test_solver_return_survives_candidate_packaging(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from schemas.platform_math import OptimizationResult
        from tools.casadi_feedback_worker import solve
        from tools.state_io import read
        order=['design/d','slack/position','slack/speed']+[f'u/{k}/0' for k in range(35)]
        values=dict.fromkeys(order,0.)
        problem=SimpleNamespace(variables={k:dict(type='number',bounds=[0.,1.]) for k in order},
            constraints=[SimpleNamespace(name=k) for k in ['dynamics_0_0','terminal_position','holding_speed_35']])
        candidate=dict(d=0.,lengths_m=[.16,.11])
        w=SimpleNamespace(n=1,m=1,assemble=lambda *a:problem,decode=lambda v:dict(candidate),
            mechanics_construction_s=0.,assembly_s=0.,initial_rollout={})
        result=OptimizationResult(status='converged',optimum=values,objective_value=0.,constraint_violation=0.,iterations=3)
        solver=SimpleNamespace(solve=lambda p:result,_bounds=lambda p,o:([0.]*len(o),[1.]*len(o),[0.]*len(o)),
            last_returned_optimum=values,last_diagnostics=dict(return_status='Solve_Succeeded',variable_order=order,
                constraint_upper=[float('inf')],construction_s=0.,solve_s=0.,
                retained_diagnostic_points=[dict(iteration=3,vector=list(values.values()),label='returned')]))
        assessment=dict(candidate=dict(candidate),hard_max_normalized_violation=0.,original_task_gaps=dict(position=0.,speed=0.),
            effort=0.,variation_weighted=0.,slack_values=dict(position=0.,speed=0.))
        args=dict(substeps=1,initialization='pretension_0_2',position_weight=1.,speed_weight=1.,secondary_coefficient=0.)
        with TemporaryDirectory() as folder,patch('tools.casadi_feedback_worker.Workspace',return_value=w),\
            patch('tools.casadi_feedback_worker.IpoptSolver',return_value=solver),patch('tools.casadi_feedback_worker.assess',return_value=assessment):
            progress=str(Path(folder)/'progress.json');output=solve({},args,'reverse',progress=progress)
            self.assertEqual(output['candidate']['selection']['iteration'],3)
            self.assertEqual(output['status'],'converged')
            saved=read(progress);self.assertEqual(saved['phase'],'solver_returned')
            self.assertEqual(saved['diagnostics']['constraint_upper'],[None])

    def test_generic_incumbent_keeps_original_gap_rank(self):
        from extensions.optimization.ipopt import _FeasibleIterate
        callback=_FeasibleIterate(1,1)
        callback.reset([0.],[1.],[-np.inf],[1.],0.,trace=True)
        callback.research_rank=lambda x,g:(float(x[0]),)
        def invoke(x,objective):
            args=[ca.DM([x]) if name=='x' else ca.DM([.5]) if name=='g' else ca.DM([objective]) if name=='f'
                else ca.DM.zeros(callback.get_sparsity_in(i)) for i,name in enumerate(callback.names)]
            callback.eval(args)
        invoke(.9,0.);invoke(.8,1.);invoke(.2,9.)
        self.assertAlmostEqual(callback.checkpoints['research_incumbent']['x'][0],.2)
        self.assertEqual(callback.checkpoints['research_incumbent']['iteration'],2)

    def test_frozen_domains_and_weight_menu(self):
        for kwargs in [dict(design_bounds=(-1.1,1.)),dict(design_bounds=(.1,.2),design_initial=0.),
            dict(position_weight=0.),dict(speed_weight=4.1),dict(secondary_coefficient=.01),
            dict(initialization='saved_schedule'),dict(objective_mode='task_gap',secondary_coefficient=.001)]:
            with self.assertRaises(ValidationError):Candidate(**kwargs)
        self.assertEqual(Candidate(design_bounds=(.2,.2),design_initial=.2).design_initial,.2)

    def test_plan_operations_match(self):
        ref=dict(artifact_id='a'*64,media_type='application/json')
        base=dict(hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',
            revision_or_stop_rule='r',disposition='d',limitations=['l'])
        with self.assertRaises(ValidationError):Plan(action='batch',**base)
        with self.assertRaises(ValidationError):Plan(action='stop',requested_nlp_solves=1,**base)
        self.assertEqual(Plan(action='batch',candidates=[Candidate()],requested_nlp_solves=1,requested_replays=1,**base).action,'batch')

    def test_refined_rollout_actual_design_and_continuous_zero(self):
        # Analytic implicit integrator checks saved schedule, nonzero design and switches.
        w=Workspace.__new__(Workspace);w.n=w.m=1;w.steps=70;w.substeps=2;w.h=.005;w.scales=np.array([10.,1000.])
        a=ca.MX.sym('a',2);b=ca.MX.sym('b',2);u=ca.MX.sym('u');d=ca.MX.sym('d')
        w.step=ca.Function('toy_step',[a,b,u,d],[ca.vertcat((b[0]-a[0]-w.h*b[1])/10.,(b[1]-a[1]-w.h*(u+d))/.001)])
        schedule=np.r_[np.full(10,.2),np.full(25,.4)][:,None]
        result=w.rollout(schedule,.5)
        self.assertIsNone(result['failure']);self.assertEqual(len(result['states']),71)
        np.testing.assert_array_equal(result['states'][0],[0.,0.])
        self.assertAlmostEqual(result['states'][-1][1],.7*.1+.9*.25,places=12)
        self.assertLess(max(r['max_normalized_residual'] for r in result['residuals']),1e-10)


def numerical_semantics(configuration):
    """One actual graph, nonzero design, coherent zero rollout, shared slack semantics."""
    w=Workspace(configuration,local_ad='automatic')
    research=dict(design_bounds=[-.5,-.5],design_initial=-.5,objective_mode='task_gap',
        position_weight=1.,speed_weight=1.,secondary_coefficient=0.)
    problem=w.assemble('B','pretension_0_2',research)
    item=assess(w,problem,problem.initial_guess)
    if problem.initial_guess['design/d']!=-.5 or item['hard_max_normalized_violation']>1e-7:
        raise AssertionError('ACTUAL_DESIGN_INITIALIZATION_NOT_COHERENT')
    if not item['relaxed_nlp_feasible'] or item['original_task_feasible']:
        raise AssertionError('SLACK_SEMANTICS_MUST_SEPARATE_RELAXED_AND_ORIGINAL_ACCEPTANCE')
    if len([name for name in problem.variables if name.startswith('slack/')])!=2:raise AssertionError('TWO_SHARED_SLACKS_REQUIRED')
    return dict(status='passed',design_initial=-.5,hard_residual=item['hard_max_normalized_violation'],
        relaxed_feasible=item['relaxed_nlp_feasible'],original_task_feasible=item['original_task_feasible'],
        slacks=item['slack_values'],original_gaps=item['original_task_gaps'],nlp_invocations=0)


if __name__=='__main__':unittest.main()
