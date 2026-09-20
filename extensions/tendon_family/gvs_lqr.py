"""Candidate-owned GVS equilibrium/LQR composition and backend tension execution."""
from copy import deepcopy
import numpy as np

from schemas.platform import Binding, Payload
from schemas.platform_math import ConstraintSelection, ObjectiveSelection, OptimizationSpecification, SystemContext
from tools.state_io import digest
from .contracts import GVSInverseAssemblerParameters, GVSModelParameters, GVSLQRControl, GVSEquilibriumRequest, LQRParameters
from .control import execute_ideal_tension, execute_tension_reference
from .gvs import GVSModel, coordinate_order, forward_kinematics
from .gvs_casadi import CasadiLinearizer, ContinuousLQRController
from .gvs_projection import PROJECTOR_ID, description as projector_description, project
from .pcc import quaternion_wxyz_to_rotation


def _nominal_environment(environment):
    value=environment.model_copy(deep=True)
    value.data['external_forces']=[]
    return value


_OPERATING_POINTS = {}


def _candidate_operating_point(inp):
    """Compose the existing inverse/static tools for this physical candidate."""
    from extensions.optimization.ipopt import IpoptSolver
    from tools.platform_optimization import assemble_optimization
    from tools.platform_registry import registry
    from .gvs_casadi import gvs_equilibrium_tool
    from .scientific_optimization import gvs_authorization

    nominal=inp.model_copy(deep=True)
    nominal.task.environment.data['external_forces']=[]
    design=nominal.robot.structure.data
    coordinates=coordinate_order(design);tendons=[t['id'] for t in design['tendons']]
    key=digest(dict(design=design,environment=nominal.task.environment.model_dump(mode='json'),
        target=nominal.task.goal.data['target_m'],source='gvs_inverse_tip_static_v1'))
    if key in _OPERATING_POINTS:
        return deepcopy(_OPERATING_POINTS[key])
    reg=registry();q_paths=['q/'+name for name in coordinates]
    tension_paths=['tendon_tensions_n/'+name for name in tendons]
    binding=Binding(extension_id='optimization_assembler.gvs_inverse',parameters=Payload(
        contract='family.gvs_inverse_assembler_parameters',data=GVSInverseAssemblerParameters(
            template='inverse_tip_static').model_dump(mode='json')))
    parameters=reg.bind(binding,'optimization_assembler')[1]
    space=gvs_authorization(nominal.robot,reg.parse(nominal.policy.candidate_builder.parameters).model_dump(mode='json'),parameters)
    initial={name:0. for name in q_paths}
    initial.update({'tendon_tensions_n/'+t['id']:min(float(t['force_limit_n']),max(float(t['pretension_n']),.2))
        for t in design['tendons']})
    problem=assemble_optimization(reg,binding,task=nominal.task,robot=nominal.robot,space=space,
        mathematical_model=reg.mathematical_model(Binding(extension_id='model.gvs',parameters=Payload(
            contract='family.gvs_model',data={}))),
        specification=OptimizationSpecification(variables=q_paths+tension_paths,
            objectives=[ObjectiveSelection(template_id='tip_position_error_squared')],
            constraints=[ConstraintSelection(template_id='static_equilibrium'),
                ConstraintSelection(template_id='tendon_force_bounds')],initial_guess=initial),
        context=SystemContext(x0=[],u0=[],scene=nominal.task.environment))
    solved=IpoptSolver({'max_iterations':500,'tolerance':1e-9}).solve(problem)
    if solved.status!='converged' or solved.constraint_violation>1e-7:
        raise ValueError('GVS_OPERATING_POINT_INVERSE_FAILED: status='+solved.status+
            ', constraint_violation='+str(solved.constraint_violation))
    q0=[solved.optimum[name] for name in q_paths]
    u0=[solved.optimum[name] for name in tension_paths]
    from types import SimpleNamespace
    refined=gvs_equilibrium_tool(SimpleNamespace(input=nominal,reg=reg),GVSEquilibriumRequest(
        tendon_tensions_n=dict(zip(tendons,u0)),initial_q=q0,tolerance=1e-16,max_iterations=20))
    if not refined.converged:
        raise ValueError('GVS_OPERATING_POINT_REFINEMENT_FAILED: residual='+str(refined.residual_norm))
    point=dict(q0=refined.q_equilibrium,u0=u0,coordinate_order=coordinates,tendon_order=tendons,
        inverse_objective_value=solved.objective_value,inverse_constraint_violation=solved.constraint_violation,
        inverse_iterations=solved.iterations,refined_equilibrium_residual_norm=refined.residual_norm,
        refinement_iterations=refined.iterations,source='gvs_inverse_tip_static',candidate_model_identity=key,
        nominalization='Only time-window external forces omitted; frozen target and backend task are unchanged.')
    point['identity']=digest(point)
    _OPERATING_POINTS[key]=deepcopy(point)
    return point


def resolve_gvs_lqr_control(inp,physics):
    c=GVSLQRControl.model_validate(inp.policy.controller.parameters.data)
    design=inp.robot.structure.data
    order=coordinate_order(design);tendon_order=[t['entity'] for t in physics['tendons']]
    point=_candidate_operating_point(inp);q0=point['q0'];u0=np.asarray(point['u0'],dtype=float)
    if len(q0)!=len(order): raise ValueError('GVS_LQR_Q0_DIMENSION_MISMATCH')
    if len(u0)!=len(tendon_order): raise ValueError('GVS_LQR_U0_DIMENSION_MISMATCH')
    limits=np.array([t['force_limit_n'] for t in physics['tendons']])
    if np.any(u0>limits): raise ValueError('GVS_LQR_U0_FORCE_LIMIT_EXCEEDED')
    parameters=GVSModelParameters()
    x0=[*q0,*([0.]*len(order))]
    system=GVSModel(parameters).build_system(inp.robot,parameters,None,SystemContext(
        x0=x0,u0=u0.tolist(),scene=_nominal_environment(inp.task.environment)))
    dynamic_system_identity=digest(system.model_dump(mode='json'))
    linear=CasadiLinearizer().linearize(system)
    state_names=[spec.name for spec in linear.state_definition]
    unknown=set(c.state_weight_overrides)-set(state_names)
    if unknown: raise ValueError('GVS_LQR_UNKNOWN_STATE_WEIGHT: '+','.join(sorted(unknown)))
    qdiag=[float(c.state_weight_overrides.get(name,c.state_rate_weight if name.endswith('.rate') else c.curvature_weight))
        for name in state_names]
    rdiag=[float(c.tendon_tension_weight)]*len(tendon_order)
    lqr_parameters=LQRParameters(Q=np.diag(qdiag).tolist(),R=np.diag(rdiag).tolist(),tendon_order=tendon_order,
        force_limits_n=limits.tolist(),equilibrium_tolerance=c.equilibrium_tolerance)
    lqr=ContinuousLQRController(lqr_parameters);K=lqr.configure_model(linear)
    gain_identity=digest(dict(K=K.tolist(),Q_diagonal=qdiag,R_diagonal=rdiag,x0=x0,u0=u0.tolist(),
        tendon_order=tendon_order,force_limits_n=limits.tolist()))
    linearization_identity=digest(linear.model_dump(mode='json'))
    local_tip=forward_kinematics(design,q0,samples_per_segment=2)['tip_position_m']
    assembly=inp.task.environment.data
    rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
    world_tip=(rotation@local_tip+np.asarray(assembly['mount']['position_m'])).tolist()
    projector=projector_description(physics,design)
    if inp.policy.backend.extension_id!='backend.family_mujoco':
        raise ValueError('GVS_LQR_BACKEND_EXECUTION_UNSUPPORTED: '+inp.policy.backend.extension_id)
    execution_mode=c.development_execution_mode or 'ideal_tension'
    if execution_mode=='ideal_tension':
        mapping=dict(id='direct_bounded_tendon_tension_v1',bridge='execute_ideal_tension',tendon_order=tendon_order,
            force_limits_n=limits.tolist(),order=['project_backend_state','continuous_lqr','clip_tendon_force',
                'apply_direct_backend_tendon_force'],
            bypassed=['transmission_pseudoinverse','actuator_velocity_limit','actuator_travel_limit','tendon_length_servo'])
        lifecycle=dict(initialize='observe actual backend state; no actuator state',reset='clear observations',restore='not implemented')
    else:
        mapping=dict(id='ideal_tendon_transmission_v1',bridge='execute_tension_reference',transmission=physics['transmission'],
            actuator_order=[a['id'] for a in physics['actuators']],tendon_order=tendon_order,
            order=['project_backend_state','continuous_lqr','clip_tendon_force','solve_transmission_minimum_norm',
                'rate_limit_actuator_command','clip_actuator_travel','apply_length_servo'])
        lifecycle=dict(initialize='zero actuator command; observe actual backend state',reset='zero command and clear observations',restore='not implemented')
    plan=dict(mode='gvs_lqr',tension_execution_mode=execution_mode,
        reference=dict(kind='gvs_equilibrium',target_world_m=list(inp.task.goal.data['target_m']),
        equilibrium_q=list(q0),equilibrium_tensions_n=u0.tolist(),tendon_order=tendon_order,
        source=c.operating_point_source,operating_point_identity=point['identity'],derivation=point,
        nominal_external_forces='omitted_from_GVS_operating_point_but_retained_in_backend_task'),
        algorithm=dict(id='gvs_lqr_tension_composition_v1',equation='u=clip(u0-K@(project(q,qdot)-x0),0,force_limit)',
            x0=x0,u0=u0.tolist(),K=K.tolist(),Q_diagonal=qdiag,R_diagonal=rdiag,
            gain_identity=gain_identity,dynamic_system_identity=dynamic_system_identity,
            linearization_identity=linearization_identity,
            gain_source='deterministic existing Linearizer + ContinuousLQRController at candidate build time',
            linearized_drift_norm_inf=float(np.linalg.norm(np.asarray(linear.drift),ord=np.inf)),
            lqr_implementation='ContinuousLQRController',projector=projector),
        mapping=mapping,
        timing=dict(period_s=inp.task.timing.control_period_s,observation='interval_start_pre_step'),
        lifecycle=lifecycle,
        effective_parameters=c.model_dump(mode='json',exclude_none=True),backend_execution_source=(
            'development comparison override' if c.development_execution_mode else 'backend.family_mujoco fixed semantics'),
        predicted_equilibrium_tip_world_m=world_tip,
        projector_id=PROJECTOR_ID)
    plan['identity']=digest(plan)
    return plan


class GVSLQRController:
    def __init__(self,parameters,period_s):
        self.parameters=GVSLQRControl.model_validate(parameters);self.period_s=period_s

    def configure(self,physics,plan):
        self.physics=physics;self.plan=plan;self.coordinate_order=plan['algorithm']['projector']['coordinate_order']
        self.K=np.asarray(plan['algorithm']['K']);self.x0=np.asarray(plan['algorithm']['x0']);self.u0=np.asarray(plan['algorithm']['u0'])
        self.execution_mode=plan.get('tension_execution_mode','actuator_realistic')
        self.u=None if self.execution_mode=='ideal_tension' else np.zeros(len(physics['actuators']))
        self.observations=[];self.last={}

    def command(self,t,geometry,q,v):
        projection=project(self.physics,self.coordinate_order,q,v)
        x=np.r_[projection['q_gvs'],projection['qdot_gvs']];delta=x-self.x0
        raw=self.u0-self.K@delta
        if self.execution_mode=='ideal_tension':
            command,bridge=execute_ideal_tension(self.physics,raw)
        else:
            self.u,command,bridge=execute_tension_reference(self.physics,self.period_s,self.u,geometry,raw)
        self.last={**bridge,'raw_desired_tension_n':raw.tolist(),
            'lqr_tension_saturated':(np.asarray(bridge['desired_tension_n'])!=raw).tolist(),
            'projected_gvs_q':projection['q_gvs'],'projected_gvs_qdot':projection['qdot_gvs'],
            'gvs_state_error':delta.tolist(),
            'gvs_projection_residual_max_rad_m':projection['projection_residual_max_rad_m'],
            'gvs_rate_projection_residual_max_rad_m_s':projection['rate_projection_residual_max_rad_m_s']}
        observation=dict(time_s=t,phase='current_state_before_integration',tip_position_m=geometry['tip'].tolist(),
            qpos_rad=q.tolist(),qvel_rad_s=v.tolist(),tendon_length_m=geometry['lengths'].tolist(),**self.last)
        if self.execution_mode=='actuator_realistic':
            observation.update(actuator_command=self.u.tolist(),target_lengths_m=command.tolist())
        self.observations.append(observation)
        return command
