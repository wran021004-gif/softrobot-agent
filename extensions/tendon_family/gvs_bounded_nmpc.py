"""Experimental v8 short-horizon work budget; distinct scientific behavior."""
from .gvs_nmpc import DeadlineReachNMPCController

class BoundedReachNMPCController(DeadlineReachNMPCController):
    def __init__(self,parameters,period_s):
        super().__init__(parameters,period_s)
        p=self.parameters
        if (p.horizon!=2 or p.max_iterations!=2 or p.max_cpu_s!=1. or
            p.feasible_return is None or p.feasible_return.minimum_s!=.001 or
            p.feasible_return.budget_s!=.005 or p.feasible_return.relative_improvement!=.1 or
            not p.regenerate_warm_states or p.recover_returned_tensions):
            raise ValueError('V8_FROZEN_COMPUTATION_POLICY_REQUIRED')
