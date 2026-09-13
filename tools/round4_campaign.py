"""One finite length campaign, reusing the compiler, planner, controllers and evaluator."""
import gzip
import json
import math
import subprocess
import sys
from pathlib import Path
import yaml
from tools.spec_tools import ROOT, load_run_settings, load_yaml
from tools.closeout_state import atomic_json, read, digest
from tools.artifact_tools import file_hash
from tools.round4_budget import Budget
from tools.round4_authority import POLICY

OUT = ROOT/'runs/round4'


def make_plan():
    from tools.experiment_policy_tools import validate_experiment_policy
    from tools.pcc_math import analytic_target_matching_length
    exp=validate_experiment_policy(ROOT/POLICY)
    boundary=math.dist([0,0,0],exp.resolved.task.target_m)-exp.resolved.task.position_error_max_m
    lengths=sorted(set([.05,.15,.25,round(boundary-.001,9),round(boundary+.001,9),.29,.298,
        analytic_target_matching_length(exp.resolved.task.target_m)['total_length_m'],.4,.5,.6,.7,.8]))
    return dict(version='round4_length_v1',baseline=exp.baseline.model_dump(mode='json'),lengths=lengths,
        geometry_rejection='L < norm(target-base)-tolerance is a necessary inextensible reach failure; no model screening used to exclude long designs',
        coarse='All non-rejected lengths, ascending; C1 and C2 at every length (<=10 pairs)',
        refinement='Once only: take midpoint on each side of the best actual coarse length separately for C1 and C2; round to 9 decimals; exact dedup; sorted; <=4 pairs',
        stop='One coarse pass and one refinement pass; no retry; no additional search based on task failure',
        budgets=dict(coarse=dict(length_screen=20,length_mujoco=20),fine=dict(length_screen=4,length_mujoco=8)),
        execution_sources={str(p.relative_to(ROOT)).replace('\\','/'):file_hash(p) for folder in ('tools','controllers','matlab','schemas','metrics','physics_contracts','configs','tasks','capabilities') for p in (ROOT/folder).rglob('*') if p.suffix in ('.py','.m','.yaml','.xml')},
        software={name:__import__('importlib.metadata',fromlist=['version']).version(name) for name in ('numpy','mujoco','matlabengine','pydantic')},
        initial_state='default MjData; zero qpos/qvel',duration_s=2.,controller_parameters=exp.policy.feedback_parameters.model_dump(),
        historical_reuse='none; earlier results cited as historical context only')


def freeze():
    path=OUT/'frozen_plan.json';plan=make_plan()
    if path.exists():
        if read(path)!=plan:raise ValueError('Frozen plan already exists and sources changed')
    else:
        import zipfile
        OUT.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(OUT/'execution_sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name,expected in plan['execution_sources'].items():
                if file_hash(ROOT/name)!=expected:raise ValueError('Source changed while freezing')
                archive.write(ROOT/name,name)
        atomic_json(path,plan)
    return path


def save_execution(folder, design, task, environment, plan, controller_level, experiment, *, disturbances=None):
    from tools.design_compiler import build_robot_ir
    from tools.mujoco_tools import compile_mujoco,run_task
    from controllers.open_loop_length import OpenLoopLength
    from controllers.pcc_tip_feedback import PCCTipFeedback
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    ir=build_robot_ir(design)
    for name,value in [('design_input.yaml',design),('task.yaml',task),('environment.yaml',environment),('robot_ir.yaml',ir)]:
        (folder/name).write_text(yaml.safe_dump(value.model_dump(mode='json')),encoding='utf-8')
    compiled=compile_mujoco(ir,task,folder/'robot.xml',environment)
    if compiled.status!='pass':return compiled.model_dump(mode='json')
    controller=PCCTipFeedback(ir,task,plan,experiment) if controller_level=='C2' else OpenLoopLength(plan.metrics['tendon_target_lengths_m'])
    result=run_task(folder/'robot.xml',task,controller,load_run_settings(),environment,record_shape=True,record_trajectory=True,disturbances=disturbances)
    value=result.model_dump(mode='json');rows=value['artifacts'].pop('trajectory',[])
    (folder/'trajectory.json.gz').write_bytes(gzip.compress(json.dumps(rows,allow_nan=False).encode(),mtime=0))
    atomic_json(folder/'observation_metadata.json',dict(controller=controller_level,frame='world_base_x_forward_yz_cross_section'))
    if controller_level=='C2':atomic_json(folder/'feedback_updates.json',controller.updates)
    atomic_json(folder/'model_result.json',plan.model_dump(mode='json'))
    atomic_json(folder/'mujoco_result.json',value)
    return value


def run_campaign(*, resume=False):
    """OS advisory file lock prevents concurrent owners, including explicit resume."""
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'length_owner.lock').open('a+b') as handle:
        handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
        if sys.platform=='win32':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:return _run_campaign(resume=resume)
        finally:
            if sys.platform=='win32':handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)


def _run_campaign(*, resume=False):
    from tools.experiment_policy_tools import validate_experiment_policy
    from tools.matlab_tools import MatlabTools
    from tools.design_compiler import build_robot_ir
    from schemas.tool_result import ToolResult
    frozen=read(OUT/'frozen_plan.json')
    if (OUT/'length_summary.json').exists():return read(OUT/'length_summary.json')
    if frozen!=make_plan():raise ValueError('Source/input drift; mixed-revision execution forbidden')
    exp=validate_experiment_policy(ROOT/POLICY);budget=Budget(OUT,retry_interrupted=resume)
    matlab=MatlabTools()
    rows=[]
    def evaluate(length,stage):
        design=exp.validate_candidate({**frozen['baseline'],'total_length_m':length})
        key=f'{length:.12g}';folder=OUT/'length'/key;folder.mkdir(parents=True,exist_ok=True)
        rejection=length<math.dist([0,0,0],exp.resolved.task.target_m)-exp.resolved.task.position_error_max_m
        if rejection:
            row=dict(length_m=length,stage=stage,status='GEOMETRY_REJECTED',reason=frozen['geometry_rejection'])
            if not (folder/'rejection.json').exists():atomic_json(folder/'rejection.json',row)
            rows.append(row);return
        model=budget.call('length_screen',key,dict(design=design.model_dump(),calls=['plan_pcc_reach']),folder/'screen.json',
            lambda:matlab.plan_pcc_reach(build_robot_ir(design),exp.resolved.task,exp.resolved.environment).model_dump(mode='json'),stage=stage)
        if model.get('status')!='pass':
            rows.append(dict(length_m=length,stage=stage,status='MODEL_ERROR',evidence=str(folder/'screen.json')));return
        plan=ToolResult.model_validate(model)
        for level in ('C1','C2'):
            run=folder/level
            result=budget.call('length_mujoco',key+level,dict(design=design.model_dump(),controller=level,plan_sha256=file_hash(folder/'screen.json')),
                run/'result.json',lambda:save_execution(run,design,exp.resolved.task,exp.resolved.environment,plan,level,exp),stage=stage)
            rows.append(dict(length_m=length,stage=stage,controller=level,status=result.get('failure_code') or result['status'],
                error_m=result.get('metrics',{}).get('position_error_m'),task_success=result.get('metrics',{}).get('task_success'),
                model_error_m=plan.metrics['predicted_position_error_m'],run=str(run.relative_to(ROOT)),result_sha256=file_hash(run/'result.json')))
            print(stage,key,level,rows[-1]['error_m'],flush=True)
    try:
        for length in frozen['lengths']:evaluate(length,'coarse')
        decision_path=OUT/'refinement.json'
        if decision_path.exists():decision=read(decision_path)
        else:
            selected=set();available=sorted(set(r['length_m'] for r in rows if r.get('error_m') is not None))
            for level in ('C1','C2'):
                eligible=[r for r in rows if r.get('controller')==level and r.get('error_m') is not None]
                if not eligible:continue
                best=min(eligible,key=lambda r:(r['error_m'],r['length_m']))['length_m'];i=available.index(best)
                for j in (i-1,i+1):
                    if 0<=j<len(available):selected.add(round((best+available[j])/2,9))
            decision=dict(rule=frozen['refinement'],selected=sorted(selected-set(frozen['lengths']))[:4],observations=rows.copy())
            atomic_json(decision_path,decision)
        for length in decision['selected']:evaluate(length,'fine')
        best={c:min((r for r in rows if r.get('controller')==c and r.get('error_m') is not None),key=lambda r:(r['error_m'],r['length_m']),default=None) for c in ('C1','C2')}
        summary=dict(rows=rows,best=best,stop='ONE_COARSE_AND_ONE_REFINEMENT_COMPLETE',physics='UNCALIBRATED_LEGACY_SURROGATE',
            task_success=any(r.get('task_success') for r in rows),plan_sha256=file_hash(OUT/'frozen_plan.json'))
        atomic_json(OUT/'length_summary.json',summary);return summary
    finally:matlab.close()
