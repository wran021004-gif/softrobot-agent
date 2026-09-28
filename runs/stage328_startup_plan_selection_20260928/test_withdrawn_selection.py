"""Focused bounded recovery selection behavior; no numerical optimization."""
from types import SimpleNamespace
import unittest
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from schemas.platform_math import OptimizationResult

class SelectionTests(unittest.TestCase):
    def workspace(self):
        ws=TrajectoryWorkspace.__new__(TrajectoryWorkspace)
        ws.tendons=['t'];ws.solver=SimpleNamespace(last_diagnostics=dict(selected_feasible_iteration=-1,returned_iterate_objective=5.),
            last_returned_optimum={'u/0/t':3.},last_recovery_candidates=[dict(iteration=i,objective=4.,optimum={'u/0/t':float(i)}) for i in (1,2,3)])
        ws._plan_peak=lambda v:v['u/0/t']
        ws.calls=[]
        def recover(result,x):
            raw=ws.solver.last_returned_optimum;ws.calls.append(raw)
            value=raw['u/0/t']
            if value in getattr(ws,'fail',[]):
                return result,dict(attempted=True,selected=False,wall_s=.1,error='integration failed')
            return result.model_copy(update=dict(optimum=raw,objective_value=value,constraint_violation=0.)),dict(source='returned_ipopt_tensions_reintegrated_from_current_measurement',attempted=True,selected=True,wall_s=.1,integration_s=.08,validation_s=.02,objective=value)
        ws._recover_returned=recover
        return ws

    def result(self):
        return OptimizationResult(status='feasible_early_stop',optimum={'u/0/t':10.},objective_value=10.,constraint_violation=0.,iterations=3)

    def test_better_recovered_candidate_and_cap(self):
        ws=self.workspace();result,d=ws._recover_shortlist(self.result(),[])
        self.assertEqual(result.objective_value,1.)
        self.assertEqual(d['parent_iteration'],1)
        self.assertEqual(d['recovery_attempts'],3)
        self.assertEqual(d['candidate_count'],3)
        self.assertEqual(len(ws.calls),3)
        self.assertEqual(ws.solver.last_returned_optimum,{'u/0/t':3.})

    def test_failed_recovery_preserves_incumbent(self):
        ws=self.workspace();ws.fail=[1,2,3];incumbent=self.result()
        result,d=ws._recover_shortlist(incumbent,[])
        self.assertIs(result,incumbent);self.assertFalse(d['selected'])

    def test_optimized_feasible_incumbent_disables_extra_work(self):
        ws=self.workspace();ws.solver.last_diagnostics['selected_feasible_iteration']=4
        _,d=ws._recover_shortlist(self.result(),[])
        self.assertFalse(d['activated']);self.assertEqual(len(ws.calls),1)

    def test_lower_objective_does_not_override_peak_guard(self):
        ws=self.workspace();ws._plan_peak=lambda v:10.-v['u/0/t']
        result,d=ws._recover_shortlist(self.result(),[])
        self.assertEqual(result.objective_value,3.);self.assertEqual(d['parent_iteration'],3)

if __name__=='__main__':unittest.main()
