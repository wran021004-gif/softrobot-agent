"""Shared IR transport, persistent MATLAB Engine, and independent backends."""
import gzip
import json
import math
import time
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from schemas.exploration import ExplorationControl
from tools.spec_tools import ROOT, load_task_package, load_simulator, load_run_settings
from tools.state_io import atomic_json, digest

MODEL_ID = 'matlab_tdcr_planar_dynamic_v1'
SOLVER = dict(version='ode15s_v1',rtol=1e-5,atol=1e-7,max_step_s=.02)


def control_commands(ir, control):
    L=ir.total_length_m
    active=[np.clip(-ir.tendon_routing_radius_m*(control.bend_y_rad*math.cos(r.angle_rad)+
                    control.bend_z_rad*math.sin(r.angle_rad)), -.25*L,.25*L) for r in ir.tendon_routes]
    return [float(np.clip(L+a+control.bias_fraction*L,.73*L,1.30*L)) for a in active]


def make_controller(ir,task,control,*,authority=None,timestep_s=None,parameter_source=None,controller_id=None):
    from controllers.registry import generate
    return generate(ir,task,control,authority=authority,timestep_s=timestep_s,
        parameter_source=parameter_source,controller_id=controller_id)


def export_shared(ir,control,folder,task_context=None):
    from tools.mujoco_tools import compile_mujoco
    import mujoco
    from tools.task_context import legacy_context
    context=task_context or legacy_context()
    task,environment=context.task,context.environment;dt=context.timestep_s;duration=context.duration_s
    if dt!=load_simulator().timestep_s:raise ValueError('SIMULATOR_ADAPTER_REQUIRED: timestep differs from compiled source')
    result=compile_mujoco(ir,task,folder/'robot.xml',environment)
    if result.status!='pass': raise ValueError(result.message)
    model=mujoco.MjModel.from_xml_path(str(folder/'robot.xml'))
    masses=[]; inertia=[]
    for i in range(ir.segments):
        body=model.body(f'segment_{i}'); rot=np.zeros(9); mujoco.mju_quat2Mat(rot,body.iquat)
        R=rot.reshape(3,3); masses.append(float(body.mass[0])); inertia.append(float((R@np.diag(body.inertia)@R.T)[1,1]))
        if not np.allclose(body.ipos,[ir.section.segment_length_m/2,0,0],atol=1e-12): raise ValueError('COM mismatch')
    qids=[model.joint(f'joint_{i}_y').id for i in range(ir.segments)]
    if model.nq!=2*ir.segments or model.ntendon!=ir.tendon_count: raise ValueError('DOF or route mismatch')
    p=dict(model_id=MODEL_ID,ir_hash=digest(ir.model_dump(mode='json')),control_hash=digest(control.model_dump()),
        length=ir.total_length_m,ds=ir.section.segment_length_m,radius=ir.tendon_routing_radius_m,body_radius=ir.body_radius_m,
        mass=masses,inertia_y=inertia,stiffness=model.jnt_stiffness[qids].tolist(),
        damping=[float(model.dof_damping[int(model.jnt_dofadr[j])]) for j in qids],
        natural=[float(model.qpos_spring[int(model.jnt_qposadr[j])]) for j in qids],
        kp=ir.mechanics.tendon_servo_kp_n_per_m,fmax=ir.mechanics.tendon_force_limit_n,
        offsets=[list(r.offset_yz_m) for r in ir.tendon_routes],angles=[r.angle_rad for r in ir.tendon_routes],
        command=control_commands(ir,control),bend=[control.bend_y_rad,control.bend_z_rad],control=control.model_dump(),
        gravity=list(environment.gravity_m_s2),floor_z=environment.objects[0].position_m[2],duration=duration,dt=dt,
        target=list(task.target_m),tolerance=task.position_error_max_m,timeout_s=120,solver=SOLVER,
        task_hash=digest(task.model_dump(mode='json')),environment_hash=digest(environment.model_dump(mode='json')),
        task_context=context.model_dump(mode='json'),task_context_hash=context.identity)
    if ir.resolved_rod:
        rod=ir.resolved_rod
        if not np.allclose(masses,rod.mass_kg,atol=1e-12) or not np.allclose(inertia,[i[1] for i in rod.inertia_diagonal_kg_m2],atol=1e-12):
            raise ValueError('V2 compiled mass/inertia mismatch')
    atomic_json(folder/'shared_input.json',p); atomic_json(folder/'robot_ir.json',ir.model_dump(mode='json'))
    return p


class DynamicsBackends:
    def __init__(self): self.matlab=None
    def engine(self):
        if self.matlab is None:
            from tools.matlab_tools import MatlabTools
            self.matlab=MatlabTools()
        return self.matlab.eng
    def close(self):
        if self.matlab: self.matlab.close(); self.matlab=None
    def simulate(self,backend,ir,control,folder,timeout_s=None,task_context=None,controller_id=None):
        from tools.task_context import legacy_context
        from controllers.registry import check_backend
        context=task_context or legacy_context()
        check_backend(control.mode,backend,context,controller_id=controller_id)
        setup=time.monotonic();eng=self.engine() if backend=='matlab' else None;engine_setup_s=time.monotonic()-setup
        started=time.monotonic();limit=timeout_s or (120 if backend=='matlab' else 180)
        folder.mkdir(parents=True,exist_ok=True); p=export_shared(ir,control,folder,context)
        p['timeout_s']=max(.01,limit-(time.monotonic()-started)-.5)
        atomic_json(folder/'shared_input.json',p)
        if backend=='matlab':
            path=folder/'matlab_raw.json'
            # One Engine retained across candidates; timeout also enforced in RHS.
            future=eng.tdcr_planar_dynamic(json.dumps(p),str(path.resolve()),nargout=0,background=True)
            try: future.result(timeout=max(.01,limit-(time.monotonic()-started)))
            except Exception:
                future.cancel(); raise
            out=json.loads(path.read_text()); rows=out.pop('trajectory'); atomic_json(folder/'solver_internal.json',out.pop('internal_time_s'))
            if not out['complete']:out['position_error_m']=None
            path.unlink(); out['numerical_wall_s']=out['elapsed_s']; out['wall_including_transport_s']=time.monotonic()-started
            out['omissions']=['out_of_plane DOFs','self_collision','friction','MuJoCo contact solver']; out['contact_model']='two endpoint half-weight unilateral normal penalty with contact damping taper, uncalibrated'
            out['applicability']='CONTACT_APPROXIMATION' if out['max_sampled_penetration_m']>1e-5 else 'PLANAR_UNCALIBRATED'
            out['applicability_warnings']=[]
            if ir.tendon_count%2 or abs(control.bend_y_rad)>1e-8:
                out['applicability_warnings'].append('Out-of-plane symmetry is not ensured by this routing/control; omitted motion requires MuJoCo verification')
            if p['body_radius']>-p['floor_z']+1e-12:
                out['applicability_warnings'].append('Initial capsule at fixed base overlaps floor; rotation cannot remove the base-cap overlap. Do not interpret this contact approximation as validated geometry')
        else:
            from tools.mujoco_tools import run_task
            task,env=context.task,context.environment
            controller=make_controller(ir,task,control,authority=context.authority,timestep_s=context.timestep_s,
                parameter_source=folder/'shared_input.json',controller_id=controller_id)
            from controllers.registry import ControllerRuntime
            controller=ControllerRuntime(controller,'mujoco',context.timestep_s)
            result=run_task(folder/'robot.xml',task,controller,environment=env,record_trajectory=True,record_shape=True,
                timeout_s=max(.01,limit-(time.monotonic()-started)),run_settings=context.run_settings,evaluator=context.evaluator())
            rows=result.artifacts.pop('trajectory',result.artifacts.pop('partial_trajectory',[]))
            atomic_json(folder/'controller_contract.json',controller.diagnostics())
            atomic_json(folder/'controller_updates.json',getattr(controller,'updates',[]))
            atomic_json(folder/'canonical_result.json',result.model_dump(mode='json'))
            complete=result.metrics.get('steps_completed')==context.run_settings.steps and result.failure_code in (None,'TASK_FAILED')
            out=dict(model_id='mujoco_segmented_v2' if ir.resolved_rod else 'mujoco_legacy_v1',complete=complete,
                computation_status='completed' if complete else 'failed',reason=result.message,position_error_m=result.metrics.get('position_error_m'),
                tip_m=result.metrics.get('tip_position_m'),canonical_task_success=result.metrics.get('task_success',False) if complete else None,
                elapsed_s=time.monotonic()-started,last_valid_time_s=rows[-1]['time_s'] if rows else 0,
                successful_internal_steps=result.metrics.get('steps_completed',0),solver='frozen MuJoCo timestep/integrator',
                controller_diagnostics=controller.diagnostics())
        with gzip.open(folder/'trajectory.json.gz','wt',encoding='utf8') as stream: json.dump(rows,stream,allow_nan=False)
        out.update(backend=backend,shared_input_hash=digest(p),trajectory_ref='trajectory.json.gz',actual_evaluations=1,
            engine_setup_s=engine_setup_s,rollout_wall_limit_s=limit,
            phase='MATLAB sampled state and force at same time; MuJoCo post-step qpos and pre-step solver force have separate times',
            residual_qvel_norm_rad_s=float(np.linalg.norm(rows[-1]['qvel_rad_s'])) if rows else None)
        atomic_json(folder/'result.json',out)
        return out
