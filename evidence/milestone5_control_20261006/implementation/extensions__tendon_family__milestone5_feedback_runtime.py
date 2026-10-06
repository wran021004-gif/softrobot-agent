"""Experimental native evaluation and every-update causal feedback reference.

This is full-order diagnostic emulation, never independent simulator validation.
The controller's objective, constraints and stopping policy remain v7's; faster
wall-clock evaluation can change its selected iterate, so its identity is new.
"""
from copy import copy,deepcopy
import hashlib
import time
from pathlib import Path
import casadi as ca
import numpy as np
from .gvs_trajectory import use_trajectory_functions

VERSION='native_exact_every_update@1.0.0'


def bound_controller(inp):
    """Resolve the declared scientific controller, including experimental versions."""
    from tools.platform_registry import registry
    definition=registry().get(inp.policy.controller.extension_id,inp.policy.controller.version,'controller')
    return definition.resolve()(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)


class NativeFunctions:
    def __init__(self,reference,library,*,library_sha256):
        if hashlib.sha256(Path(library).read_bytes()).hexdigest()!=library_sha256:
            raise ValueError('NATIVE_LIBRARY_IDENTITY_MISMATCH')
        self.expected=hashlib.sha256(reference.implicit_residual.serialize().encode()).hexdigest()
        self.function=ca.external('gvs_force_balance',str(library));self.cache={}

    def __call__(self,original):
        if id(original) not in self.cache:
            actual=hashlib.sha256(original.implicit_residual.serialize().encode()).hexdigest()
            if actual!=self.expected:raise ValueError('NATIVE_KERNEL_PHYSICAL_IDENTITY_MISMATCH')
            result=copy(original);result.implicit_residual=self.function
            self.cache[id(original)]=(original,result)
        return self.cache[id(original)][1]


def history(configuration,initial_state,model,physics,ctx,*,provider,count,deadline,save_update):
    """No observed future states/commands/outcomes or other candidate plans."""
    from schemas.platform import SessionInput
    from .gvs_profile import prepare_execution
    from .gvs_nmpc import resolve_gvs_nmpc_control
    from .gvs_projection import project
    from .gvs_basis import resolve_basis
    from .diagnostic_math import charge_units
    from tools.state_io import digest
    started=time.perf_counter();inp=SessionInput.model_validate(configuration)
    basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
    controller=bound_controller(inp)
    prepare_execution(ctx,controller,inp);plan=resolve_gvs_nmpc_control(inp,physics)
    with use_trajectory_functions(provider):controller.configure(physics,plan)
    setup_s=time.perf_counter()-started;period=inp.task.timing.control_period_s
    x=np.asarray(initial_state,dtype=float).copy();rows=[]
    for i in range(count):
        if time.perf_counter()>deadline:raise RuntimeError('NATIVE_FEEDBACK_DEADLINE')
        before=x.copy();input_to_command_start=time.perf_counter();observe_start=time.perf_counter();z=project(physics,basis,x[:model.full_n],x[model.full_n:])
        motion=model.motion(x);geometry=dict(tip=np.asarray(motion['position_m']),gvs_projection=z)
        observation_s=time.perf_counter()-observe_start
        warm=controller.seed if controller.seed is not None else controller.workspace.last
        warm_record=None if warm is None else deepcopy({k:warm[k] for k in ('states','tensions')})
        previous_input=np.asarray(controller.previous).tolist() if hasattr(controller,'previous') else None
        charge_units(ctx,'local_solves',1);start=time.perf_counter()
        with use_trajectory_functions(provider):command=controller.command(i*period,geometry,z['q_gvs'],z['qdot_gvs'])
        complete_command_s=time.perf_counter()-start
        packaging_start=time.perf_counter();command=list(command);packaging_s=time.perf_counter()-packaging_start
        input_to_command_s=time.perf_counter()-input_to_command_start
        if controller.stop_requested:raise ValueError('CAUSAL_CONTROLLER_STOP')
        selected=controller.workspace.last
        sealed=dict(update_id=i,time_s=i*period,initial_full_state=before.tolist(),input_n=list(command),
            previous_plan_identity=None if i==0 else rows[-1]['plan_identity'],
            plan_identity=digest(dict(states=selected['states'],tensions=selected['tensions'])),
            selected_plan={k:selected[k] for k in ('states','tensions')},warm_before_command=warm_record,
            command_receipt=controller.observations[-1],complete_command_s=complete_command_s,observation_s=observation_s,
            projected_current_state=deepcopy(z),previous_input_n=previous_input,command_packaging_s=packaging_s,
            software_input_to_command_s=input_to_command_s,
            accepted=controller.last['plan_accepted'],replanned=True)
        save_update(dict(phase='sealed_before_emulated_advance',**sealed))
        end=model.propagate(x,command,grid=dict(max_step_s=.0005),deadline=deadline,duration_s=period);x=np.asarray(end['state'])
        row=dict(**sealed,state=x.tolist(),endpoint_s=(i+1)*period,position_m=end['position_m'],
            velocity_m_s=end['velocity_m_s'],speed_m_s=end['speed_m_s'],
            error_m=float(np.linalg.norm(np.asarray(end['position_m'])-inp.task.goal.data['target_m'])),
            max_scaled_residual=end['max_scaled_residual'],emulated_physics_steps=end['backend_equivalent_integration_steps'],
            propagation_s=end['cost_s'])
        rows.append(row);save_update(dict(phase='emulated_endpoint',**row))
    return dict(version=VERSION,controller_binding=inp.policy.controller.model_dump(mode='json'),configuration_identity=digest(configuration),initial_state=list(initial_state),rows=rows,
        setup_s=setup_s,complete_cost_s=time.perf_counter()-started,complete=count==round(inp.task.timing.duration_s/period),
        controller_solves=count,emulated_physics_steps=sum(r['emulated_physics_steps'] for r in rows),backend_steps=0,
        full_order=True,controller_policy='Replan every configured update, with own previous plan and current predicted full state.',
        historical_controller_equivalence='Explicit bound controller version; v8 changes horizon/work/termination behavior. Historical v7 outcomes cannot validate it; v7 timed selections may also differ with runtime.',
        timing='Complete command boundary including graph changes, warm regeneration, optimization, validation and observation construction. Initial configure/setup and full-state observation separately charged.')
