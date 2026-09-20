"""Signals expand from physical entity and actuator maps; clocks stay explicit."""
from schemas.platform import Signal, SignalSpec


def declarations(tension_reference=False):
    values=[
        ('tip_position','tip',3,'m','world','post_step','tip_m'),
        ('joint_position','joint',1,'rad','joint_local','post_step','qpos_rad'),
        ('joint_velocity','joint',1,'rad/s','joint_local','post_step','qvel_rad_s'),
        ('tendon_length','tendon',1,'m','path','post_step','tendon_length_m'),
        ('tendon_tension','tendon',1,'N','path','pre_step_solver','tension_n'),
        ('tendon_target_length','tendon',1,'m','path','pre_step_solver','command_m'),
        ('actuator_command','actuator',1,'actuator_specific','actuator','pre_step_solver','actuator_command'),
        ('actuator_torque','joint',1,'N.m','joint_local','pre_step_solver','solver_qfrc_actuator_nm'),
        ('external_torque','joint',1,'N.m','joint_local','pre_step_solver','external_torque_nm')]
    if tension_reference:
        values.append(('desired_tendon_tension','tendon',1,'N','path','pre_step_solver','desired_tension_n'))
    return [dict(name=n,entity_group=g,dimension=d,units=u,frame=f,phase=phase,field=field)
        for n,g,d,u,f,phase,field in values]


def expanded(p,tension_reference=False):
    groups=dict(joint=p['dofs'],tendon=[t['entity'] for t in p['tendons']],actuator=[a['id'] for a in p['actuators']],tip=['tip'])
    for item in declarations(tension_reference):
        for i,entity in enumerate(groups[item['entity_group']]):
            units=p['actuators'][i]['units'] if item['entity_group']=='actuator' else item['units']
            yield item,i,SignalSpec(name=item['name'],entity=entity,dimension=item['dimension'],units=units,frame=item['frame'],phase=item['phase'])


def observation_specs(inp,reg):
    from .backends import physics_for
    from .contracts import Control
    tension=Control.model_validate(inp.policy.controller.parameters.data).mode=='tension_reference'
    return [s for _,_,s in expanded(physics_for(inp),tension)]


def export(rows,p,tension_reference=False):
    return [Signal(spec=s,times_s=[r['time_s' if s.phase=='post_step' else 'solver_time_s'] for r in rows],
        values=[r[item['field']] if s.dimension==3 else [r[item['field']][i]] for r in rows])
        for item,i,s in expanded(p,tension_reference)]
