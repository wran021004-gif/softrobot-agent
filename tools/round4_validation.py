"""Finite new development calls and historical read-only audit."""
import gzip
import json
from pathlib import Path
import numpy as np
from tools.spec_tools import ROOT
from tools.closeout_state import atomic_json, read, digest
from tools.artifact_tools import file_hash
from tools.round4_budget import Budget
from tools.round4_campaign import OUT, save_execution


def historical_audit():
    path=ROOT/'runs/20260912T082624_505318Z_6c8bf663/model_comparisons.json'
    rows=read(path)
    result=[]
    for r in rows:
        source=ROOT/'runs'/r['run_id'];trajectory=json.loads(gzip.decompress((source/'trajectory.json.gz').read_bytes()))
        result.append(dict(run_id=r['run_id'],source_sha256=file_hash(path),failure=r['dynamic'],
            max_contact_count=max(s['solver_contact_count'] for s in trajectory),
            input='recorded negative actuator force converted to nonnegative tension at solver_time_s; no length-servo equivalence',
            missing=['trigger time','trigger state','trial versus accepted','last valid sample'],
            conclusion='Historical reason preserved; cannot recover missing solver state. Contact and out-of-plane DOFs absent from reduced model.'))
    atomic_json(OUT/'historical_failure_audit.json',result)
    # Reuse the successful historical development trajectories with exact input provenance.
    old=read(ROOT/'runs/closeout_development_budget.json')
    index=[]
    for row in old['mechanics']:
        if row.get('input',{}).get('operation')=='dynamic' and row.get('result',{}).get('status')=='pass':
            target=OUT/'historical'/f'mechanics_{row["id"]}.json'
            if not target.exists():atomic_json(target,dict(input=row['input'],result=row['result'],provenance=dict(
                source='runs/closeout_development_budget.json',sha256=file_hash(ROOT/'runs/closeout_development_budget.json'),id=row['id'],reuse='historical; no new solve')))
            index.append(str(target.relative_to(ROOT)))
    atomic_json(OUT/'historical_animation_index.json',index)
    return rows


def solve_diagnostic(matlab, parameters, budget, name):
    from schemas.analysis_spec import AnalysisSpec
    from tools.round4_authority import check_authority
    check_authority()
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise ValueError('Invalid solve artifact name')
    try:p=AnalysisSpec.model_validate(parameters).model_dump(exclude_none=True)
    except ValueError as exc:
        return dict(result=dict(status='fail',failure_kind='CONDITION_NOT_APPLICABLE',reason=str(exc)),backend_started=False)
    def solve():
        future=matlab.eng.round4_mechanics(json.dumps(p,allow_nan=False),nargout=1,background=True)
        try:r=json.loads(future.result(timeout=45))
        except Exception:
            future.cancel();raise
        return dict(input=p,result=r)
    return budget.call('mechanics',name,dict(operation=p['operation'],entry='round4_mechanics',input_sha256=digest(p)),OUT/'validation'/f'{name}.json',solve)


def oscillator_comparison(matlab,budget):
    import mujoco
    folder=OUT/'validation/oscillator';folder.mkdir(parents=True,exist_ok=True)
    xml='''<mujoco model="round4_one_hinge"><option timestep="0.002" gravity="0 0 0" integrator="implicitfast"/>
    <worldbody><body name="rod"><inertial pos="0.1 0 0" mass="0.1" diaginertia="0.001 0.001 0.001"/>
    <joint name="bend" type="hinge" axis="0 -1 0" stiffness="0.1" damping="0.01"/>
    <geom type="capsule" fromto="0 0 0 0.2 0 0" size="0.01" contype="0" conaffinity="0"/>
    <site name="tip" pos="0.2 0 0"/></body></worldbody></mujoco>'''
    if not (folder/'model.xml').exists():(folder/'model.xml').write_text(xml)
    model=mujoco.MjModel.from_xml_path(str(folder/'model.xml'))
    p=dict(inertia=float(model.body_inertia[1,1]+model.body_mass[1]*model.body_ipos[1,0]**2),stiffness=.1,damping=.01,
        torque_nm=.003,q0=.1,dt_s=.002,duration_s=2.,length_m=.2)
    contract=dict(version='one_hinge_torque_v1',input=p,frame='world_base_x_forward_yz_cross_section',
        mapping='one rotational DOF q about -Y; J=Iyy+m*cx^2; no gravity/contact/tendons; constant world generalized torque',
        interpretation='same continuous equation; MuJoCo discretization error measured, not real material calibration')
    if not (folder/'mapping.json').exists():atomic_json(folder/'mapping.json',contract)
    def sim():
        data=mujoco.MjData(model);data.qpos[0]=p['q0'];data.qfrc_applied[0]=p['torque_nm']
        times=[0.];qs=[p['q0']];vel=[0.]
        for i in range(1000):
            mujoco.mj_step(model,data);times.append(float(data.time));qs.append(float(data.qpos[0]));vel.append(float(data.qvel[0]))
        return dict(status='pass',time_s=times,q_rad=qs,velocity_rad_s=vel)
    simresult=budget.call('development_mujoco','oscillator',contract,folder/'mujoco.json',sim)
    def solve():
        future=matlab.eng.round4_oscillator(json.dumps(p),nargout=1,background=True)
        try:return json.loads(future.result(timeout=45))
        except Exception:future.cancel();raise
    reference=budget.call('mechanics','oscillator',contract,folder/'matlab.json',solve)
    if simresult['status']!='pass' or reference['status']!='pass':return dict(status='fail',reason='backend failure')
    from tools.observation_tools import FRAME, comparison_eligibility
    observations=[]
    for backend,r in [('MuJoCo',simresult),('MATLAB',reference)]:
        obs=dict(format='observation_v1',backend=backend,source=str(folder/(backend.lower()+'.json')),
            source_sha256=file_hash(folder/(backend.lower()+'.json')),frame=FRAME,model='one_hinge_torque_v1',status='pass',
            design=dict(total_length_m=.2,segments=1),control='constant torque 0.003 N m',target_m=None,events=[],comparison_contract=contract,
            semantics={'state':'saved dynamic output','geometry':'reconstructed from q','input':'constant generalized torque; no tendon force'},samples=[])
        for t,q,v in zip(r['time_s'],r['q_rad'],r['velocity_rad_s']):
            tip=[.2*np.cos(q),0.,.2*np.sin(q)]
            obs['samples'].append(dict(time_s=t,state=[q,v],centerline_m=[[0,0,0],tip],tip_m=tip,error_m=None,input_time_s=t,
                tendon_target_m=None,tendon_actual_m=None,force_n=None,contact_count=0))
        atomic_json(folder/(backend.lower()+'_observation.json'),obs);observations.append(obs)
    comparison=comparison_eligibility(*observations)
    comparison.update(q_max_error_rad=float(np.max(np.abs(np.array(simresult['q_rad'])-reference['q_rad']))),mapping=contract)
    atomic_json(folder/'comparison.json',comparison);return comparison


def run_development():
    from tools.matlab_tools import MatlabTools
    from tools.experiment_policy_tools import validate_experiment_policy
    from tools.round4_authority import POLICY
    from tools.task_family_tools import FAMILIES,generate_task_instance,execution_task,evaluate_task_instance
    from tools.design_compiler import build_robot_ir
    from schemas.tool_result import ToolResult
    if (OUT/'development_summary.json').exists():
        return read(OUT/'development_summary.json')
    history=historical_audit();budget=Budget(OUT);matlab=MatlabTools();summary={}
    try:
        # One representative historical replay; all old raw files remain unchanged.
        h=history[0];source=ROOT/'runs'/h['run_id'];rows=json.loads(gzip.decompress((source/'trajectory.json.gz').read_bytes()))
        p={**h['parameters'], 'operation':'dynamic','duration_s':2.,'sample_dt_s':.01,
            'input_time_s':[r['solver_time_s'] for r in rows],
            'input_tension_n':[[max(0.,-f) for f in r['solver_actuator_force_n']] for r in rows]}
        diagnostic=solve_diagnostic(matlab,p,budget,'historical_recheck')
        summary['diagnostic']=dict(status=diagnostic.get('result',{}).get('status'),evidence='validation/historical_recheck.json')
        summary['comparison']=oscillator_comparison(matlab,budget)
        exp=validate_experiment_policy(ROOT/POLICY);design=exp.baseline
        evaluations=[]
        for family in FAMILIES:
            instance=generate_task_instance(family);task,env=execution_task(instance);folder=OUT/'tasks'/family
            folder.mkdir(parents=True,exist_ok=True)
            if not (folder/'instance.json').exists():atomic_json(folder/'instance.json',instance.model_dump(mode='json'))
            # Account model planning separately as a development mechanics/model solve.
            model=budget.call('mechanics','task_plan_'+family,dict(operation='plan_pcc_reach'),folder/'plan.json',
                lambda:matlab.plan_pcc_reach(build_robot_ir(design),task,env).model_dump(mode='json'))
            if model.get('status')!='pass':evaluations.append(dict(family=family,status='MODEL_ERROR'));continue
            plan=ToolResult.model_validate(model)
            value=budget.call('development_mujoco','task_'+family,instance.model_dump(mode='json'),folder/'result.json',
                lambda:save_execution(folder,design,task,env,plan,'C1',exp,disturbances=[instance.disturbance] if instance.disturbance else None))
            trajectory=json.loads(gzip.decompress((folder/'trajectory.json.gz').read_bytes())) if (folder/'trajectory.json.gz').exists() else []
            evaluation=evaluate_task_instance(instance,value,trajectory);atomic_json(folder/'evaluation.json',evaluation);evaluations.append(evaluation)
        summary['task_evaluations']=evaluations
        atomic_json(OUT/'development_summary.json',summary)
    finally:matlab.close()
    return summary
