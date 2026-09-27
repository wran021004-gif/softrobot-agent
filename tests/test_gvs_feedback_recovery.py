"""Focused independent validation of an externally reintegrated NLP candidate."""
import unittest
import casadi as ca
from extensions.optimization.ipopt import IpoptSolver,expression_payload
from schemas.platform import Objective
from schemas.platform_math import OptimizationProblem,OptimizationConstraint


class FeedbackRecoveryTests(unittest.TestCase):
    def test_repaired_candidate_uses_original_dynamics_and_bounds(self):
        x,u=ca.MX.sym('x'),ca.MX.sym('u')
        bundle,selectors=expression_payload(['x','u'],
            dict(variables=dict(x=x,u=u),expression=(x-.25)**2),dict(dynamics=x-u*u))
        problem=OptimizationProblem(variables={k:dict(type='number',bounds=[0.,1.]) for k in ('x','u')},
            objective=Objective(metric='tracking',direction='minimize',units='1'),objective_function=bundle,
            constraints=[OptimizationConstraint(name='dynamics',expression=selectors[0],units='1',lower=0.,upper=0.)],
            initial_guess=dict(x=1.,u=1.))
        solver=IpoptSolver(dict(retain_feasible_iterate=True));solver.diagnostic_trace=True
        result=solver.solve(problem)
        self.assertEqual(result.status,'converged')
        self.assertTrue(solver.last_diagnostics['iteration_trace'])
        self.assertEqual(set(solver.last_diagnostics['diagnostic_plans']),{'initial','selected','returned'})
        self.assertFalse(solver.evaluate_candidate(problem,dict(x=.25,u=.6))['feasible'])
        self.assertTrue(solver.evaluate_candidate(problem,dict(x=.36,u=.6))['feasible'])
        # Exact dynamics alone cannot authorize an out-of-bounds tension.
        self.assertFalse(solver.evaluate_candidate(problem,dict(x=1.44,u=1.2))['feasible'])
        self.assertAlmostEqual(solver.evaluate_candidate(problem,dict(x=.36,u=.6))['objective'],.11**2)


if __name__=='__main__':unittest.main()
