"""One <=5,000-step force execution check; fixed cold inputs, no Study/search.

Run from the repository root with -m examples.b2_load_force_smoke. Refuses to
overwrite evidence. The exact pre-change NativeModel is read from Git only.
"""
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import argparse
import hashlib
import json
import subprocess
import sys
import time
import mujoco
import numpy as np
import scipy

from schemas.platform import SessionInput
from tools.state_io import read,atomic_json,digest
from tools.research.physical_replay import evaluate_playback
from tools.research_tasks import assemble_acceptance
from extensions.tendon_family.backends import MujocoFailureSnapshot,playback_tensions
from extensions.tendon_family.mujoco_analysis import NativeModel

ROOT=Path(__file__).resolve().parents[1]
BASE='618fba9a11a1a1d0c9fca5228d25e873b7c8dddd'
CAP=5000
FORCE=dict(entity='payload',point='center_of_mass',frame='world',force_n=[0.,.02,-.03],start_s=.1,end_s=.25)


def configuration():
    # Reuse only the existing neutral robot and task configuration, never its control.
    cfg=deepcopy(read(ROOT/'evidence/b3_r1_history_assisted_050/design_package.json')['configuration'])
    cfg['task']['timing']['duration_s']=.35;cfg['task']['sampling']['window_s']=[0.,.35]
    cfg['task']['task_id']='b2-force-runtime-engineering-smoke'
    cfg['task']['source']='B1 engineering matching only; no task feasibility claim'
    cfg['task']['environment']['data']['external_forces']=[]
    return cfg


def initial(native):
    d=mujoco.MjData(native.model)
    d.qpos[native.qi]=native.scene['qpos_rad'];d.qvel[native.vi]=native.scene['qvel_rad_s']
    native.forward(d)
    return d


def compare(left,right):
    p=np.asarray(left['tip_positions_m'])-right['tip_positions_m']
    v=np.asarray(left['tip_velocities_m_s'])-right['tip_velocities_m_s']
    result=dict(samples=len(p),max_time_difference_s=float(max(abs(np.asarray(left['times_s'])-right['times_s']))),
        max_position_difference_m=float(max(np.linalg.norm(p,axis=1))),
        max_velocity_difference_m_s=float(max(np.linalg.norm(v,axis=1))))
    assert result['max_time_difference_s']<1e-12,result
    assert result['max_position_difference_m']<1e-12 and result['max_velocity_difference_m_s']<1e-12,result
    return result


def run(folder, recover_zero_playback=None):
    if folder.exists():raise ValueError('REFUSE_TO_OVERWRITE_PRIOR_COSTS_OR_EVIDENCE')
    folder.mkdir(parents=True)
    cfg=configuration();loaded=deepcopy(cfg);loaded['task']['environment']['data']['external_forces']=[FORCE]
    times=np.arange(36)*.01
    native=NativeModel(cfg);load_native=NativeModel(loaded)
    commands=np.full((35,len(native.aids)),.2)
    atomic_json(folder/'inputs.json',dict(baseline=BASE,configuration_zero=cfg,external_force=FORCE,
        times_s=times.tolist(),absolute_tensions_n=commands.tolist(),control_initialization='constant 0.2 N; no saved successful control',
        runtime=dict(python=sys.version,mujoco=mujoco.__version__,numpy=np.__version__,scipy=scipy.__version__)))
    source=subprocess.check_output(['git','show',BASE+':extensions/tendon_family/mujoco_analysis.py'],cwd=ROOT,text=True,encoding='utf8')
    legacy=ModuleType('extensions.tendon_family._b1_baseline');legacy.__package__='extensions.tendon_family'
    exec(compile(source,BASE+':mujoco_analysis.py','exec'),legacy.__dict__)
    old_native=legacy.NativeModel(cfg)
    prior=read(recover_zero_playback/'cost.json') if recover_zero_playback else None
    ledger=dict(cap=CAP,physics_step_attempts=prior['physics_step_attempts'] if prior else 0,
        physics_steps=prior['physics_steps'] if prior else 0,phases={})
    if prior:
        assert read(recover_zero_playback/'summary.json')['status']=='failed'
        assert prior['physics_step_attempts']==2100 and prior['physics_steps']==2100
        ledger['prior_attempt']=dict(path=str(recover_zero_playback),cost=prior,
            missing='Original and new zero Native position/velocity arrays were not saved before evaluation error; repeat only 0.02 s.')
    traces={};label=None;original=MujocoFailureSnapshot.call

    def audited(safety,data,operation,location):
        if operation is mujoco.mj_step:
            if ledger['physics_step_attempts']>=CAP:raise ValueError('ENGINEERING_INTEGRATION_CAP_EXHAUSTED')
            ledger['physics_step_attempts']+=1
            bid=safety.model.body('payload').id
            traces[label].append(dict(tick=round(data.time/safety.model.opt.timestep),
                force_n=data.xfrc_applied[bid,:3].tolist(),couple_nm=data.xfrc_applied[bid,3:].tolist()))
        result=original(safety,data,operation,location)
        if operation is mujoco.mj_step:ledger['physics_steps']+=1
        return result

    def phase(name,fn,cost=None):
        nonlocal label
        label=name;traces[name]=[];before=ledger['physics_step_attempts'];started=time.perf_counter()
        try:return fn()
        finally:
            ledger['phases'][name]=dict(physics_step_attempts=ledger['physics_step_attempts']-before,
                wall_s=time.perf_counter()-started,**(dict(native_cost=deepcopy(cost)) if cost is not None else {}))
            atomic_json(folder/'cost.json',ledger);atomic_json(folder/'force_steps.json',traces)

    def replay(configuration,n,name,raw=None):
        inp=SessionInput.model_validate(configuration)
        if raw is None:raw=playback_tensions(inp,n.physics,n.scene,commands,folder/name)
        (folder/name).mkdir(exist_ok=True)
        atomic_json(folder/name/'raw.json',raw)
        raw_ref=dict(artifact_id=digest(raw),media_type='application/json')
        evaluation,profile=evaluate_playback(configuration,raw,raw_ref,digest(configuration))
        evaluation_ref=dict(artifact_id=digest(evaluation.model_dump(mode='json')),media_type='application/json')
        profile.update(simulation=raw_ref,evaluation=evaluation_ref)
        profile_ref=dict(artifact_id=digest(profile),media_type='application/json')
        acceptance=assemble_acceptance(configuration,evaluation,profile,evaluation_reference=evaluation_ref,
            profile_reference=profile_ref,motion=[dict(time_s=s['time_s']) for s in raw['samples']])
        atomic_json(folder/(name+'.json'),dict(raw=raw,evaluation=evaluation.model_dump(mode='json'),profile=profile,acceptance=acceptance))
        assert profile['complete'] and raw['physics_steps']==700,profile
        return dict(times_s=[s['time_s'] for s in raw['samples']],tip_positions_m=[s['tip_m'] for s in raw['samples']],
            tip_velocities_m_s=[s['tip_velocity_m_s'] for s in raw['samples']]),acceptance

    summary=dict(status='running',implementation=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    try:
        with patch.object(MujocoFailureSnapshot,'call',audited):
            if prior:
                xml=recover_zero_playback/'zero_playback/robot.xml'
                recovered=dict(status='completed',failure=None,samples=read(recover_zero_playback/'zero_playback/samples.json'),
                    physics_steps=700,physics_step_attempts=700,command_intervals=35,tendon_order=native.tendons,
                    model_identity=native.physics['identity'],scene_identity=native.scene['identity'],
                    xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),physics_timestep_s=float(native.model.opt.timestep),
                    integrator=int(native.model.opt.integrator),physical_backend='backend.family_mujoco',tension_execution_mode='ideal_tension',
                    recovery='Raw envelope reconstructed from saved samples, XML, input and 700 audited completed step calls; no new playback integration.')
                zero_replay,zero_accept=phase('zero_playback_recovered_evaluation',lambda:replay(cfg,native,'zero_playback',recovered))
            zero_times=times[:3] if prior else times
            zero_commands=commands[:len(zero_times)-1]
            zero_old=phase('zero_original_native',lambda:old_native.rollout_sequence(initial(old_native),zero_times,zero_commands),old_native.cost)
            atomic_json(folder/'zero_original_native.json',zero_old)
            zero=phase('zero_native',lambda:native.rollout_sequence(initial(native),zero_times,zero_commands),native.cost)
            atomic_json(folder/'zero_native.json',zero)
            if not prior:zero_replay,zero_accept=phase('zero_playback',lambda:replay(cfg,native,'zero_playback'))
            force=phase('force_native',lambda:load_native.rollout_sequence(initial(load_native),times,commands),load_native.cost)
            atomic_json(folder/'force_native.json',force)
            force_replay,force_accept=phase('force_playback',lambda:replay(loaded,load_native,'force_playback'))
            summary['matches']=dict(zero_original_native=compare(zero,zero_old),zero_playback=compare(zero,{k:v[:len(zero_times)] for k,v in zero_replay.items()}),
                nonzero_playback=compare(force,force_replay))
            # Reconstruct to the force-on boundary using fresh engine history.
            rows=read(folder/'force_playback.json')['raw']['samples'][1:11]
            point=dict(physics_identity=load_native.physics['identity'],native_replay=dict(scene=load_native.scene,
                rows=[dict(r,tension_n=r['actual_tension_n']) for r in rows]),candidate={},configuration_identity=digest(loaded),u=commands[10].tolist(),provenance={})
            checkpoint,start=phase('force_prefix',lambda:load_native.reconstruct(point),load_native.cost)
            restored=load_native.restore(checkpoint)
            continuation=phase('force_restored_suffix',lambda:load_native.rollout_sequence(restored,times[10:],commands[10:]),load_native.cost)
            expected={k:force[k][10:] for k in ('times_s','tip_positions_m','tip_velocities_m_s')}
            summary['matches']['reconstruct_restore_suffix']=compare(continuation,expected)
            short=phase('force_constant_rollout',lambda:load_native.rollout(start,commands[10],.02),load_native.cost)
            short2=phase('force_repeated_candidate',lambda:load_native.rollout(start,commands[10],.02),load_native.cost)
            for key in ('tip_position_m','tip_velocity_m_s'):
                np.testing.assert_allclose(short[key],force['tip_positions_m' if key=='tip_position_m' else 'tip_velocities_m_s'][12],atol=1e-12,rtol=0)
                np.testing.assert_array_equal(short[key],short2[key])
            mechanics=load_native.mechanics(start,commands[10])
            summary['mechanics']=dict(mass_balance_residual_inf_nm=mechanics['mass_balance_residual_inf_nm'],
                generalized_external_force_inf_nm=float(max(abs(np.asarray(mechanics['generalized_forces_nm']['external_body'])))),
                com_to_tip_distance_m=float(np.linalg.norm(start.site_xpos[load_native.tip]-start.xipos[load_native.model.body('payload').id])))
            atomic_json(folder/'mechanics.json',mechanics)
        for name,trace in traces.items():
            loaded_phase=name.startswith('force_')
            for row in trace:
                expected=FORCE['force_n'] if loaded_phase and 200<=row['tick']<500 else [0.,0.,0.]
                assert row['force_n']==expected and row['couple_nm']==[0.,0.,0.],(name,row)
        summary.update(status='passed',force_window_verified_every_step=True,
            full_run_active_steps={name:sum(any(row['force_n']) for row in traces[name]) for name in ('zero_native','force_native','force_playback')},
            nonzero_effect=dict(max_position_change_m=float(max(np.linalg.norm(np.asarray(force['tip_positions_m'])-zero_replay['tip_positions_m'],axis=1))),
                max_velocity_change_m_s=float(max(np.linalg.norm(np.asarray(force['tip_velocities_m_s'])-zero_replay['tip_velocities_m_s'],axis=1)))),
            original_acceptance=dict(zero=zero_accept,force=force_accept),cost=ledger,
            native_costs=dict(original=old_native.cost,zero=native.cost,force=load_native.cost),
            limitations='Matching execution semantics only; no B2 feasibility or structural advantage; task draft remains unfrozen.')
        assert summary['nonzero_effect']['max_position_change_m']>1e-6
        atomic_json(folder/'native_outputs.json',dict(zero_original=zero_old,zero=zero,force=force,restored_suffix=continuation,short=short,repeated_candidate=short2))
    except Exception as exc:
        summary.update(status='failed',reason=str(exc),cost=ledger,
            native_diagnostic=getattr(exc,'native_diagnostic',None),mujoco_diagnostic=getattr(exc,'mujoco_diagnostic',None))
        raise
    finally:atomic_json(folder/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'evidence/b2_external_force_runtime')
    parser.add_argument('--recover-zero-playback',type=Path,help='Explicit recovery of this smoke\'s first evaluation-only error; carries all 2100 prior steps.')
    args=parser.parse_args()
    run(args.output.resolve(),args.recover_zero_playback.resolve() if args.recover_zero_playback else None)
