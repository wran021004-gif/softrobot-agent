"""Controller-free finite-time execution using the existing fixed-payout compiler."""
import time
from pathlib import Path
import numpy as np
import mujoco
from schemas.platform import BackendResult, Payload, Signal, SignalSpec
from tools.platform_store import plain
from tools.state_io import digest, atomic_json
from .backends import physics_for, MujocoFailureSnapshot
from .passive import PassiveModel
from .scene import assemble_physical
from extensions.reference.passive_response import task_definition, load_at


def source_binding(configuration):
    """One exact effective physical/task source; no fictitious control identity."""
    from schemas.platform import SessionInput
    inp=SessionInput.model_validate(configuration)
    from tools.platform_tasks import compile_input
    compile_input(plain(inp))
    p=physics_for(inp)
    return dict(source_kind='frozen_passive_protocol_v1',task_identity=digest(plain(inp.task)),
        design_identity=p['design_identity'],model_identity=digest(dict(physics=p['identity'],
            backend=plain(inp.policy.backend),model=plain(inp.policy.dynamics_model),
            environment=plain(inp.task.environment),initial=plain(inp.task.initializer),timing=plain(inp.task.timing))),
        protocol=plain(inp.task.goal),initial=plain(inp.task.initializer))


def observation_specs(inp,reg=None):
    fields=[('tip_position',3,'m','world'),('tip_velocity',3,'m/s','world'),
        ('material_position',3,'m','world'),('material_velocity',3,'m/s','world'),
        ('joint_position',1,'rad','joint_local'),('joint_velocity',1,'rad/s','joint_local'),
        ('tendon_length',1,'m','path'),('tendon_tension',1,'N','path'),('length_residual',1,'m','path')]
    p=physics_for(inp);specs=[]
    for case in inp.task.goal.data['load_conditions']:
        for name,dim,unit,frame in fields:
            entities=(p['dofs'] if name.startswith('joint_') else [t['entity'] for t in p['tendons']] if name.startswith('tendon_') or name=='length_residual'
                else ['point_'+str(i) for i,_ in enumerate(inp.task.physical_problem['monitor_s'])] if name.startswith('material_') else ['tip'])
            for entity in entities:
                specs.append(SignalSpec(name=name,entity=case+'__'+entity,dimension=dim,units=unit,frame=frame,phase='post_step'))
    return specs


def backend_result(inp,raw):
    fields=dict(tip_position='tip_m',tip_velocity='tip_velocity_m_s',material_position='material_positions_m',
        material_velocity='material_velocities_m_s',joint_position='qpos_rad',joint_velocity='qvel_rad_s',
        tendon_length='tendon_length_m',tendon_tension='actual_tension_n',length_residual='length_residual_m')
    signals=[];p=physics_for(inp)
    for spec in observation_specs(inp):
        case,entity=spec.entity.split('__',1)
        episode=next((e for e in raw.get('episodes',[]) if e['load_condition']==case),None)
        if episode is None:continue
        name=spec.name;rows=episode['samples'];field=fields[name]
        if name.startswith('material_'):index=int(entity.removeprefix('point_'))
        elif name.startswith('joint_'):index=p['dofs'].index(entity)
        elif name.startswith('tendon_') or name=='length_residual':index=[t['entity'] for t in p['tendons']].index(entity)
        else:index=None
        signals.append(Signal(spec=spec,times_s=[r['time_s'] for r in rows],
            values=[r[field] if index is None else r[field][index] if spec.dimension==3 else [r[field][index]] for r in rows]))
    return BackendResult(solver_status='completed' if raw['status']=='completed' else 'failed',
        backend_id='backend.family_passive_mujoco',model_id='mujoco_passive_fixed_payout_v1',signals=signals,
        data=Payload(contract='family.passive_dynamic_data',data=raw),initial_state=inp.task.initializer.parameters,seed=inp.seed,
        limitations=['MuJoCo unilateral soft tendon limits; static hard KKT feasibility does not imply dynamic acceptance.',
            'Contact-free serial bending model; no hardware, friction, mixed actuation or robustness claim.'])


def execute(inp,folder=None):
    from tools.platform_registry import registry
    goal,bounds,problem=task_definition(inp.task,registry())
    p=physics_for(inp);scene=assemble_physical(inp,p)
    scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1')
    folder=Path(folder) if folder else None
    if folder:folder.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    native=PassiveModel(p,plain(problem),folder/'passive.xml' if folder else None,scene=scene)
    model=native.model
    compile_s=time.perf_counter()-started
    binding=source_binding(plain(inp))
    raw=dict(kind='passive_dynamic_execution_v1',status='incomplete',physical_binding=binding,
        active_actuators=int(model.nu),joint_count=model.nv,coordinate_order=p['dofs'],tendon_order=[t['entity'] for t in p['tendons']],
        payout_lengths_m=native.payout.tolist(),initial_state=dict(qpos_rad=scene['qpos_rad'],qvel_rad_s=scene['qvel_rad_s']),
        episodes=[],physics_steps=0,attempted_steps=0,native_forward_calls=0,model_builds=1,
        timings_s=dict(model_compile=compile_s),mujoco_version=mujoco.__version__,
        solver_options=dict(timestep_s=float(model.opt.timestep),integrator=int(model.opt.integrator),
            iterations=int(model.opt.iterations),tolerance=float(model.opt.tolerance)))
    dt=inp.task.timing.timestep_s;steps=round(inp.task.timing.duration_s/dt);stride=round(inp.task.timing.sample_period_s/dt)
    failure=MujocoFailureSnapshot(model,binding['model_identity'],folder)
    tendon_ids={model.tendon(t['entity']).id:i for i,t in enumerate(p['tendons'])}
    def checkpoint():
        raw.update(physics_steps=failure.completed_steps,attempted_steps=failure.attempted_steps,
            native_forward_calls=failure.forward_evaluations)
        raw['cost']=dict(model_builds=1,physics_steps=failure.completed_steps,attempted_steps=failure.attempted_steps,
            native_forward_calls=failure.forward_evaluations,episodes_started=len(raw['episodes']),
            episodes_completed=sum(e['complete'] for e in raw['episodes']),material_point_jacobian_calls=native.cost['material_point_jacobian_calls'])
        raw['timings_s']['total']=time.perf_counter()-started
        if folder:atomic_json(folder/'passive_progress.json',raw)
    for case in goal.load_conditions:
        data=mujoco.MjData(model);mujoco.mj_resetData(model,data)
        data.qpos[:]=scene['qpos_rad'];data.qvel[:]=scene['qvel_rad_s']
        load=native.load(case)
        episode=dict(load_condition=case,initial_state=raw['initial_state'],complete=False,samples=[],
            physics_steps=0,checked_physics_steps=0,maximum_contacts=0,
            maximum_tension_n=0.,maximum_length_excess_m=0.)
        raw['episodes'].append(episode)
        def refresh(t):
            force,phase=load_at(goal,load,t)
            failure.call(data,mujoco.mj_forward,'passive_state_geometry')
            native.apply_force(data,load.material_s,force)
            failure.call(data,mujoco.mj_forward,'passive_loaded_constraints')
            return force,phase
        def tension():
            values=np.zeros(model.ntendon)
            for j in range(data.nefc):
                if data.efc_type[j]==int(mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON):
                    values[tendon_ids[int(data.efc_id[j])]]+=abs(float(data.efc_force[j]))
            return values.tolist()
        def safety():
            episode['maximum_contacts']=max(episode['maximum_contacts'],int(data.ncon))
            episode['maximum_tension_n']=max(episode['maximum_tension_n'],max(tension()))
            episode['maximum_length_excess_m']=max(episode['maximum_length_excess_m'],max(0.,float(max(data.ten_length-native.payout))))
        def sample(t,force,phase):
            points=[native.point(data,b) for b in native.points]
            return dict(time_s=t,engine_time_s=float(data.time),qpos_rad=data.qpos.tolist(),qvel_rad_s=data.qvel.tolist(),
                tip_m=points[-1][0].tolist(),tip_velocity_m_s=(points[-1][1]@data.qvel).tolist(),
                material_positions_m=[x[0].tolist() for x in points[:-1]],material_velocities_m_s=[(x[1]@data.qvel).tolist() for x in points[:-1]],
                tendon_length_m=data.ten_length.tolist(),length_residual_m=(data.ten_length-native.payout).tolist(),
                actual_tension_n=tension(),taut=[bool(v>0) for v in tension()],force_world_n=force,phase=phase,
                ncon=int(data.ncon),nefc=int(data.nefc),solver_iterations=int(np.max(data.solver_niter)),
                warnings=[dict(number=int(w.number),lastinfo=int(w.lastinfo)) for w in data.warning])
        try:
            force,phase=refresh(0.);safety();episode['samples'].append(sample(0.,force,phase));checkpoint()
            for tick in range(steps):
                # Force is evaluated at each integration interval start, in world N.
                force,phase=refresh(tick*dt)
                failure.call(data,mujoco.mj_step,'passive_time_integration')
                episode['physics_steps']+=1
                force,phase=refresh((tick+1)*dt);safety();episode['checked_physics_steps']+=1
                if (tick+1)%stride==0:
                    episode['samples'].append(sample((tick+1)*dt,force,phase));checkpoint()
            episode['complete']=True
        except Exception as exc:
            raw['reason']=str(exc)
            if getattr(exc,'mujoco_diagnostic',None):raw['numerical_failure']=exc.mujoco_diagnostic
            checkpoint();break
        checkpoint()
    if len(raw['episodes'])==len(goal.load_conditions) and all(e['complete'] for e in raw['episodes']):raw['status']='completed'
    checkpoint()
    return backend_result(inp,raw)


class NoActiveControl:
    """Registry execution declaration; intentionally has no command method."""
    def __init__(self,*args):pass
    def close(self):pass


class PassiveBackend:
    @classmethod
    def check(cls,inp,parameters,control):
        from tools.platform_registry import registry
        task_definition(inp.task,registry())
        if (inp.policy.controller.extension_id!='controller.no_active_control' or inp.robot.channels or
                inp.robot.structure.data.get('actuators') or not inp.robot.structure.data.get('fixed_payout_lengths_m')):
            raise ValueError('PASSIVE_NO_ACTIVE_CONTROL_ASSEMBLY_REQUIRED')
        assemble_physical(inp,physics_for(inp))
    def compile(self,inp,reg):self.inp=inp
    def initialize(self,initial,controller):
        if initial!=self.inp.task.initializer.parameters:raise ValueError('PASSIVE_INITIAL_STATE_MISMATCH')
    def run(self,folder,timeout_s):
        self.result=execute(self.inp,folder)
        atomic_json(Path(folder)/'result.json',plain(self.result))
        return self.result
    def export(self):return self.result
    def close(self):pass
