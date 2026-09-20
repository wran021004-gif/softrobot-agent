"""Ideal actuator commands and end-point resolved-rate feedback, no PCC reuse."""
import numpy as np
from tools.state_io import digest
from .contracts import Control


def execute_tension_reference(physics, period_s, previous_u, geometry, requested_tensions):
    """Execute model-space tensions through the one shared ideal-servo bridge."""
    requested=np.asarray(requested_tensions,dtype=float)
    force=np.array([x['force_limit_n'] for x in physics['tendons']])
    desired=np.clip(requested,0.,force)
    kp=np.array([x['kp_n_m'] for x in physics['tendons']])
    pretension=np.array([x['pretension_n'] for x in physics['tendons']])
    B=np.array(physics['transmission'])
    target_for_tension=geometry['lengths']-desired/kp
    wanted=np.linalg.pinv(B)@(target_for_tension-np.array(physics['reference_lengths_m'])+pretension/kp)
    limits=np.array([a['limits'] for a in physics['actuators']])
    speed=np.array([a['velocity_limit'] for a in physics['actuators']])
    rate_limited=previous_u+np.clip(wanted-previous_u,-speed*period_s,speed*period_s)
    command=np.clip(rate_limited,limits[:,0],limits[:,1])
    target=np.array(physics['reference_lengths_m'])+B@command-pretension/kp
    predicted=np.clip(kp*(geometry['lengths']-target),0.,force)
    error=predicted-desired
    telemetry=dict(requested_tension_n=requested.tolist(),desired_tension_n=desired.tolist(),
        predicted_tension_n=predicted.tolist(),tension_tracking_error_n=error.tolist(),
        force_limit_saturated=(requested!=desired).tolist(),
        actuator_saturated=(np.abs(command-wanted)>1e-12).tolist(),
        tension_command_unrealizable=(np.abs(error)>1e-9).tolist())
    return command,target,telemetry


def resolve_control(inp, physics):
    """Normalize reference, algorithm and actuator mapping without running it."""
    c=Control.model_validate(inp.policy.controller.parameters.data)
    tendon_order=[t['entity'] for t in physics['tendons']]
    if c.mode == 'tension_reference':
        if len(c.desired_tendon_tensions_n) != len(tendon_order):
            raise ValueError('TENSION_REFERENCE_DIMENSION_MISMATCH')
        requested=np.array(c.desired_tendon_tensions_n)
        force_limits=np.array([t['force_limit_n'] for t in physics['tendons']])
        desired=np.clip(requested,0.,force_limits)
        reference=dict(kind='tendon_tensions',requested_tensions_n=requested.tolist(),
            desired_tensions_n=desired.tolist(),units='N',frame='tendon_path',
            tendon_order=tendon_order,force_limit_saturated=(requested!=desired).tolist())
        source='Control.desired_tendon_tensions_n in frozen robot tendon order'
    elif c.reference is None:
        reference=(dict(kind='actuator_commands',commands=c.commands,units='m_or_rad_by_actuator',frame='actuator')
                   if c.mode=='deterministic' else
                   dict(kind='task_goal',commands={},units='m',frame='world'))
        source='legacy Control fields / TaskDefinition.goal compatibility'
    else:
        reference=c.reference.model_dump(mode='json'); source='Control.reference'
    if c.mode=='deterministic' and reference['kind']!='actuator_commands':
        raise ValueError('DETERMINISTIC_CONTROL_REQUIRES_ACTUATOR_REFERENCE')
    if c.mode=='tip_feedback' and reference['kind']!='task_goal':
        raise ValueError('TIP_FEEDBACK_REQUIRES_TASK_GOAL_REFERENCE')
    unknown=set(reference.get('commands',{}))-{a['id'] for a in physics['actuators']}
    if unknown: raise ValueError('UNKNOWN_CONTROL_ACTUATOR: '+','.join(sorted(unknown)))
    target=list(inp.task.goal.data['target_m']) if reference['kind']=='task_goal' else list(inp.task.goal.data.get('target_m',()))
    reference.update(source=source,target_world_m=target if target else None)
    if c.mode == 'deterministic':
        algorithm=dict(id='deterministic_actuator_reference_v1',parameters=dict(ramp_s=c.ramp_s),
            observations=[],state=['actuator_command'],output='named_actuator_command')
    elif c.mode == 'tip_feedback':
        algorithm=dict(id='tip_resolved_rate_feedback_v1',parameters=dict(feedback_gain=c.feedback_gain,damping=c.damping,
            max_joint_update_rad=c.max_joint_update_rad),observations=['tip_position_m','qpos_rad','qvel_rad_s','tendon_length_m'],
            state=['actuator_command'],output='named_actuator_command')
    else:
        algorithm=dict(id='constant_tendon_tension_reference_v1',parameters={},
            observations=['tendon_length_m'],state=['actuator_command'],output='named_actuator_command',
            equation='target_length=current_length-desired_tension/length_servo_gain',
            transmission_solution='minimum_norm_pseudoinverse')
    mapping=dict(id='ideal_tendon_transmission_v1',input='named actuator displacement or drum rotation',
        output='tendon target length m',transmission=physics['transmission'],
        actuator_order=[a['id'] for a in physics['actuators']],tendon_order=[t['entity'] for t in physics['tendons']],
        actuator_units={a['id']:a['units'] for a in physics['actuators']},
        winding_and_ratio={a['id']:a['transmission'] for a in physics['actuators']},
        limits={a['id']:a['limits'] for a in physics['actuators']},
        velocity_limits={a['id']:a['velocity_limit'] for a in physics['actuators']},
        tendon_pretension_n={t['entity']:t['pretension_n'] for t in physics['tendons']},
        tendon_force_limits_n={t['entity']:t['force_limit_n'] for t in physics['tendons']},
        tension_servo_equation='T=clip(kp*(current_tendon_length-target_tendon_length),0,force_limit)',
        order=((['solve_transmission_minimum_norm'] if c.mode=='tension_reference' else [])+
            ['rate_limit_actuator_command','clip_actuator_travel','apply_transmission','subtract_pretension_extension','backend_tension_only_force_limit']))
    effective=c.model_dump(mode='json')
    effective['commands']=dict(reference.get('commands',{}))
    if c.mode == 'tension_reference':
        effective.update(desired_tendon_tensions_n=reference['desired_tensions_n'],
            requested_tendon_tensions_n=reference['requested_tensions_n'],
            force_limit_saturated=reference['force_limit_saturated'])
    plan=dict(mode=c.mode,reference=reference,algorithm=algorithm,mapping=mapping,
        timing=dict(period_s=inp.task.timing.control_period_s,observation='interval_start_pre_step',
            force_signals='interval_start_pre_step_solver',state_signals='interval_end_post_step'),
        lifecycle=dict(initialize='zero actuator command',reset='zero command and clear observations at run start',restore='not implemented'),
        effective_parameters=effective)
    plan['identity']=digest(plan)
    return plan


class Controller:
    def __init__(self, parameters, period_s):
        self.parameters, self.period_s = parameters, period_s

    def configure(self, physics, plan):
        self.physics = physics
        self.plan = plan
        target=plan['reference'].get('target_world_m')
        self.target = np.array(target if target is not None else [])
        self.commands = plan['reference'].get('commands',{})
        self.desired_tensions = np.array(plan['reference'].get('desired_tensions_n',[]))
        self.requested_tensions = np.array(plan['reference'].get('requested_tensions_n',[]))
        self.force_limit_saturated = plan['reference'].get('force_limit_saturated',[])
        self.u = np.zeros(len(physics['actuators']))
        self.observations = []
        self.last = {}

    def command(self, t, geometry, q, v):
        p,c,dt = self.physics,self.parameters,self.period_s
        B = np.array(p['transmission'])
        if c.mode == 'deterministic':
            wanted = np.array([self.commands.get(a['id'],0.) for a in p['actuators']])*min(1.,(t+dt)/c.ramp_s)
        elif c.mode == 'tip_feedback':
            J = geometry['Jtip']; error = self.target-geometry['tip']
            dq = c.feedback_gain*dt*J.T@np.linalg.solve(J@J.T+c.damping**2*np.eye(3),error)
            dq = np.clip(dq,-c.max_joint_update_rad,c.max_joint_update_rad)
            wanted = self.u+np.linalg.pinv(B)@geometry['Jlength']@dq
        else:
            self.u,target,self.last=execute_tension_reference(p,dt,self.u,geometry,self.requested_tensions)
            observation=dict(time_s=t,phase='current_state_before_integration',tip_position_m=geometry['tip'].tolist(),
                qpos_rad=q.tolist(),qvel_rad_s=v.tolist(),tendon_length_m=geometry['lengths'].tolist(),actuator_command=self.u.tolist(),target_lengths_m=target.tolist())
            observation.update(self.last); self.observations.append(observation)
            return target
        limits = np.array([a['limits'] for a in p['actuators']]); speed = np.array([a['velocity_limit'] for a in p['actuators']])
        previous=self.u.copy()
        rate_limited=previous+np.clip(wanted-previous,-speed*dt,speed*dt)
        self.u = np.clip(rate_limited,limits[:,0],limits[:,1])
        target = np.array(p['reference_lengths_m'])+B@self.u-np.array([t['pretension_n']/t['kp_n_m'] for t in p['tendons']])
        self.last={}
        observation=dict(time_s=t,phase='current_state_before_integration',tip_position_m=geometry['tip'].tolist(),
            qpos_rad=q.tolist(),qvel_rad_s=v.tolist(),tendon_length_m=geometry['lengths'].tolist(),actuator_command=self.u.tolist(),target_lengths_m=target.tolist())
        observation.update(self.last); self.observations.append(observation)
        return target
