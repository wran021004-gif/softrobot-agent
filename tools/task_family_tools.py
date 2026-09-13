"""Seeded instances and normal evaluation using the existing reach executors."""
import math
import random
import numpy as np
from schemas.task_family import TaskInstance
from tools.spec_tools import ROOT, load_task_package

FAMILIES = ('reach_free','reach_obstacle','tip_stability_external_force')


def describe_tasks():
    return {f:dict(version='round4_development_v1', frame='world', duration_s=2.,
        initial='zero hinge qpos/qvel', seeds=dict(development=[0,999],evaluation=[10000,10999]),
        variable_parameters=dict(target_z_m=[.14,.16],external_force_z_n=[.08,.12] if 'stability' in f else None),
        evaluation='max and RMS error over [0.8,2] s' if 'stability' in f else 'final reach + existing window constraints when applicable',
        success='0.01 m max error' if 'stability' in f else 'existing 0.01 m reach tolerance and existing window acceptance',
        tools=['build_robot_ir','plan_pcc_reach','plan_open_loop','compile_mujoco','run_task','evaluate_task_instance','load_observation'],
        missing=['base motion executor','task-specific optimal controller','calibrated physics'],
        authority='DEVELOPMENT_ONLY; reach/window sources reused; stability window and pulse are implementation choices for interface validation') for f in FAMILIES}


def generate_task_instance(family, seed=17, split='development'):
    if family not in FAMILIES: raise ValueError('IMPLEMENTATION_REQUIRED: unknown task family')
    rng=random.Random(seed)
    package='tests/fixtures/reach_window_dev' if family=='reach_obstacle' else 'tasks/reach_free'
    stable=family=='tip_stability_external_force'
    return TaskInstance(family=family,split=split,seed=seed,package=package,target_m=(.25,0.,rng.uniform(.14,.16)),
        evaluation_start_s=.8 if stable else 0.,tolerance_m=.01,
        disturbance=dict(body='segment_7',coordinate_frame='world',start_s=.5,end_s=.7,force_n=[0.,0.,rng.uniform(.08,.12)]) if stable else None)


def execution_task(instance):
    instance=TaskInstance.model_validate(instance)
    task,environment=load_task_package(ROOT/instance.package)
    return task.model_copy(update=dict(target_m=list(instance.target_m),position_error_max_m=instance.tolerance_m)),environment


def evaluate_task_instance(instance, result, trajectory):
    instance=TaskInstance.model_validate(instance)
    if hasattr(result,'model_dump'):result=result.model_dump(mode='json')
    if result.get('failure_code') not in (None,'TASK_FAILED') or 'task_success' not in result.get('metrics',{}):
        return dict(status='EXECUTION_ERROR',task_success=None,reason=result.get('message','missing normal metrics'))
    m=result['metrics']
    if (m.get('target_position_m')!=list(instance.target_m) or m.get('position_error_max_m')!=instance.tolerance_m):
        return dict(status='EVIDENCE_MISMATCH',task_success=None,reason='execution target/tolerance does not match instance')
    expected=[instance.disturbance] if instance.disturbance else []
    if result.get('artifacts',{}).get('disturbances',[])!=expected:
        return dict(status='EVIDENCE_MISMATCH',task_success=None,reason='executed disturbance does not match instance')
    if not trajectory or abs(trajectory[-1]['time_s']-2.)>1e-8:
        return dict(status='EVIDENCE_INCOMPLETE',task_success=None,reason='full 2 s trajectory required')
    ts=np.array([s['time_s'] for s in trajectory])
    if not np.isfinite(ts).all() or np.any(np.diff(ts)<=0) or ts[0]>.00200001 or np.max(np.diff(ts))>.00200001:
        return dict(status='EVIDENCE_INCOMPLETE',task_success=None,reason='regular 0.002 s saved samples required')
    samples=[s for s in trajectory if s['time_s']>=instance.evaluation_start_s-1e-10]
    errors=[math.dist(s['tip_m'],instance.target_m) for s in samples]
    if not np.isfinite(errors).all(): return dict(status='EVIDENCE_INVALID',task_success=None)
    stable=instance.family=='tip_stability_external_force'
    from metrics.reach import evaluate_reach
    task,_=execution_task(instance)
    try:canonical=evaluate_reach(trajectory[-1]['tip_m'],task,m.get('window_evidence'))
    except ValueError as exc:return dict(status='EVIDENCE_INCOMPLETE',task_success=None,reason=str(exc))
    success=max(errors)<=instance.tolerance_m if stable else canonical['task_success']
    return dict(status='EVALUATED',task_success=success,authority=instance.authority,instance=instance.model_dump(mode='json'),
        metrics=dict(final_error_m=errors[-1],maximum_error_m=max(errors),rms_error_m=float(np.sqrt(np.mean(np.square(errors)))),
            window_evidence=result['metrics'].get('window_evidence')), samples=len(samples),
        success_rule='max error over evaluation interval' if stable else 'existing reach/window evaluator')
