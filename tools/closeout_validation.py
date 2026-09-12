"""Small real validation runs, backend lifecycle checks and offline trajectory replay."""
import gzip
import json
from pathlib import Path
import sys
import subprocess
from tools.artifact_tools import create_run,finalize_run,file_hash
from tools.closeout_state import atomic_json,read
from tools.spec_tools import ROOT

BUDGET=ROOT/'runs/closeout_development_budget.json'


def reserve(kind,context):
    ledger=read(BUDGET) if BUDGET.exists() else dict(mechanics=[],mujoco=[],full_suite=[])
    if len(ledger[kind])>=dict(mujoco=12,full_suite=1)[kind]: raise ValueError('Development budget exhausted')
    ledger[kind].append(dict(context=context,status='reserved'))
    atomic_json(BUDGET,ledger)


def environment_check():
    import xml.parsers.expat
    from importlib.metadata import version
    result=dict(python=sys.executable,packages={p:version(p) for p in ('numpy','mujoco','matlabengine','pydantic')},
        dll_order='Python Expat imported before MATLAB Engine',hardware='NOT_STARTED',matlab_started=False)
    from tools.matlab_tools import MatlabTools
    tool=MatlabTools()
    try: result.update(matlab_started=True,matlab_version=tool.version(),matlab_probe=float(tool.eng.sqrt(4.)))
    finally: tool.close()
    return result


class ReplayAdapter:
    """Read-only observation/action interface; explicitly LOG_REPLAY, no hardware."""
    mode='LOG_REPLAY'
    def __init__(self,rows): self.rows=iter(rows); self.closed=False
    def observe(self):
        if self.closed: raise ValueError('Adapter closed')
        return next(self.rows,None)
    def apply(self,command): raise ValueError('LOG_REPLAY cannot send hardware actions')
    def close(self): self.closed=True


def replay(run_path,output=None):
    path=Path(run_path); rows=json.loads(gzip.decompress((path/'trajectory.json.gz').read_bytes()))
    adapter=ReplayAdapter(rows); count=0
    while adapter.observe() is not None: count+=1
    adapter.close()
    result=dict(mode='LOG_REPLAY',samples=count,hardware_started=False,source_sha256=file_hash(path/'trajectory.json.gz'))
    if output:
        import csv
        with Path(output).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['time_s','tip_x_m','tip_y_m','tip_z_m']);w.writerows([r['time_s'],*r['tip_m']] for r in rows)
        result['output']=str(output)
    return result


def validate_real():
    from tools.matlab_tools import MatlabTools
    from tools.harness import run_reach,_snapshot_sources
    from tools.closeout_authority import POLICY
    from tools.mechanics_tools import MechanicsTools,export_parameters
    from tools.design_compiler import build_robot_ir
    from tools.spec_tools import load_yaml,validate_design,load_task_package,load_run_settings
    from tools.mujoco_tools import run_task
    from controllers.open_loop_length import OpenLoopLength
    import numpy as np
    run=create_run(ROOT/'runs'); _snapshot_sources(run)
    run.save('validation_scope.json',dict(scope='DEVELOPMENT_VALIDATION',formal_candidate=False))
    matlab=MatlabTools(); run.save('matlab_environment.json',dict(version=matlab.version(),python=sys.executable))
    class Shared:
        def __getattr__(self,name): return getattr(matlab,name)
        def close(self): pass
    result={};children=[]
    try:
        for controller in ('C1','C2'):
            reserve('mujoco','development real Harness '+controller)
            child=run_reach(experiment_path=ROOT/POLICY,controller_level=controller,matlab_factory=Shared,
                experiment_context={'parent_experiment_id':run.path.name,'candidate_id':'DEVELOPMENT_'+controller})
            assert child.record.final_status in ('PASS','TASK_FAILED'),read(child.path/'error.json') if (child.path/'error.json').exists() else child.record.final_status
            children.append(child.path)
        c1,c2=children
        task,env=load_task_package(); command=read(c1/'tendon_command.json')['tendon_target_lengths_m']
        reserve('mujoco','development observation-invariance comparator')
        plain=run_task(c1/'robot.xml',task,OpenLoopLength(command),load_run_settings())
        observed=read(c1/'mujoco_result.json')
        assert plain.artifacts['final_state']==observed['artifacts']['final_state']
        assert plain.metrics['position_error_m']==observed['metrics']['position_error_m']
        run.save('observation_invariance.json',dict(passed=True,plain=plain.model_dump(mode='json'),observed_run=c1.name))
        reserve('mujoco','development external-force pulse, outside main experiment')
        disturbed=run_task(c1/'robot.xml',task,OpenLoopLength(command),load_run_settings(),record_trajectory=True,
            disturbances=[dict(body='segment_7',coordinate_frame='world',start_s=.5,end_s=.7,force_n=[0,0,1.])])
        assert 'task_success' in disturbed.metrics
        run.save('disturbance.json',disturbed)
        assert disturbed.metrics['tip_position_m']!=plain.metrics['tip_position_m']
        result['observation_and_disturbance']=True
        ir=build_robot_ir(validate_design(load_yaml(c1/'design_input.yaml')))
        parameters=export_parameters(c1/'robot.xml',ir); run.save('analysis_parameters.json',parameters)
        mechanics=MechanicsTools(matlab)
        zero={**parameters,'gravity_m_s2':[0,0,0]}
        static_zero=mechanics.solve(zero,operation='static'); assert static_zero['status']=='pass',static_zero
        assert abs(static_zero['q_rad'])<1e-6
        loaded=mechanics.solve(zero,operation='static',tip_force_n=[0,0,.03]); assert loaded['status']=='pass' and loaded['q_rad']>0,loaded
        gravity=mechanics.solve(parameters,operation='static'); assert gravity['status']=='pass' and gravity['q_rad']<0,gravity
        tendon=mechanics.solve(zero,operation='static',tension_n=[0,1,0,0]); assert tendon['status']=='pass' and tendon['q_rad']>0,tendon
        dyn=dict(operation='dynamic',duration_s=2.,sample_dt_s=.01,initial_q_rad=0.,initial_velocity_rad_s=0.)
        resting=mechanics.solve(zero,**dyn); assert resting['status']=='pass' and max(abs(v) for v in resting['q_rad'])<1e-6,resting
        decay=mechanics.solve(zero,**{**dyn,'initial_q_rad':.3})
        assert decay['status']=='pass' and decay['mechanical_potential_energy_j'][-1]<decay['mechanical_potential_energy_j'][0],decay
        assert max(np.diff(decay['mechanical_potential_energy_j']))<1e-8
        pulse=dict(pulse_start_s=.3,pulse_end_s=.6,pulse_force_n=[0,0,0],pulse_tension_n=[0,1,0,0])
        driven=mechanics.solve(zero,**dyn,**pulse); assert driven['status']=='pass' and max(driven['q_rad'])>1e-4,driven
        force=mechanics.solve(zero,**dyn,**{**pulse,'pulse_tension_n':[0,0,0,0],'pulse_force_n':[0,0,.1]})
        assert force['status']=='pass' and max(force['q_rad'])>1e-4,force
        result['mechanics']={k:v for k,v in locals().copy().items() if k in ('static_zero','loaded','gravity','tendon','resting','decay','driven','force')}
        train=[-.06,-.03,.03,.06];validation=[-.045,.045]
        run.save('frozen_identification_split.json',dict(train_force_n=train,validation_force_n=validation,
            truth_scale=1.4,bounds=[.5,2.],loss='mean squared equilibrium torque residual',validation_used_for_selection=False))
        observations=[]
        for f in train+validation:
            value=mechanics.solve(zero,operation='static',stiffness_scale=1.4,tip_force_n=[0,0,f])
            assert value['status']=='pass',value
            observations.append(value['q_rad'])
        fitted=mechanics.solve(zero,operation='fit',train_q_rad=observations[:4],train_force_n=train,
            validation_q_rad=observations[4:],validation_force_n=validation)
        assert fitted['status']=='pass' and abs(fitted['stiffness_scale']-1.4)<1e-5 and fitted['validation_mse_nm2']<1e-12,fitted
        invalid=mechanics.solve(zero,operation='static',tension_n=[-1,0,0,0]); assert invalid['status']=='fail'
        result.update(fit=fitted,invalid_input=invalid,real_validation_passed=True,development_mujoco_rollouts=4)
        run.save('validation_results.json',result)
        run.save('child_runs.json',[dict(run_id=p.name,manifest_sha256=file_hash(p/'run.json')) for p in children])
        run.save('solve_budget_snapshot.json',read(BUDGET))
        finalize_run(run,'PASS')
    finally: matlab.close()
    print('VALIDATION',run.path,flush=True)
    return run.path


def analyze_saved(parent):
    from tools.matlab_tools import MatlabTools
    from tools.mechanics_tools import MechanicsTools,export_parameters
    from tools.design_compiler import build_robot_ir
    from tools.spec_tools import load_yaml,validate_design
    from tools.harness import _snapshot_sources
    parent=Path(parent);summary=read(parent/'closeout_summary.json')
    run=create_run(ROOT/'runs');_snapshot_sources(run);matlab=MatlabTools();tool=MechanicsTools(matlab)
    comparisons=[]
    try:
        for a in (summary['baseline'],summary['historical_best_current_revision'],summary['best']):
            child=parent.parent/a['run_id'];actual=read(child/'mujoco_result.json')
            p=export_parameters(child/'robot.xml',build_robot_ir(validate_design(load_yaml(child/'design_input.yaml'))))
            tensions=[max(0.,-v) for v in actual['metrics']['actuator_force']]
            static=tool.solve(p,operation='static',tension_n=tensions)
            rows=json.loads(gzip.decompress((child/'trajectory.json.gz').read_bytes()))
            dynamic=tool.solve(p,operation='dynamic',duration_s=2.,sample_dt_s=.01,
                input_time_s=[r['solver_time_s'] for r in rows],
                input_tension_n=[[max(0.,-v) for v in r['solver_actuator_force_n']] for r in rows])
            comparisons.append(dict(run_id=child.name,manifest_sha256=file_hash(child/'run.json'),parameters=p,
                input_semantics='Observed MuJoCo tensile-force replay; conditional analysis, no length-to-tension equivalence claimed',
                pcc=read(child/'model_result.json')['metrics'],actual_tip_m=actual['metrics']['tip_position_m'],
                actual_qvel_rad_s=actual['artifacts']['final_state']['qvel'],
                quasi_static=static,dynamic=dynamic,
                static_vs_transient='NOT_EQUIVALENT: 2-second MuJoCo final state is not certified equilibrium; no static accuracy claim',
                scientific_status='SIM_TO_SIM / CONDITIONAL_OBSERVED_FORCE_INPUT'))
        run.save('model_comparisons.json',comparisons);run.save('solve_budget_snapshot.json',read(BUDGET));finalize_run(run,'PASS')
    finally:matlab.close()
    print('ANALYSIS',run.path,flush=True);return run.path
