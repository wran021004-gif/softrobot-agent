"""Frozen engineering comparison using existing candidates, native search and replay.

Prepare once, commit the plan, then run once. No Study, Provider or new Store.
Detailed observations and partial costs remain in the ignored run directory.
"""
from copy import deepcopy
import json
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import plain
from tools.research.design import resolved_configuration,set_parameter
from tools.research.physical_replay import initialize_schedule,binding,evaluate_playback
from tools.research.control_correction import task_measure,task_outputs,corrected_tensions
from tools.research.local_control_search import search
from tools.research.contracts import LocalControlSearchSettings
from tools.research_tasks import task_adapter,assemble_acceptance

RUN=ROOT/'runs/mujoco-reoptimized-structure'
EVIDENCE=ROOT/'evidence/mujoco_reoptimized_structure'
MODULI={'d_minus':4.86e6,'d_zero':5.40e6,'d_plus':5.94e6}
SETTINGS=dict(version='local_control_search_v2',method='response',knots_s=[0.,.12,.23,.34],
    correction_window_s=[0.,.35],active_coefficients=list(range(24)),coefficient_limit_n=1.5,
    difference_step_n=.02,initial_radius_n=.15,minimum_radius_n=.0001,
    evaluation_requests=30,iterations=1,safety_margin_fraction=.05)
STEP_LIMIT=160000


def inputs():
    refs=read(ROOT/'evidence/mujoco_c1_autonomous/supervision_summary.json')['references']
    with tarfile.open(ROOT/'evidence/mujoco_c1_autonomous/immutable_artifacts.tar.gz') as archive:
        def artifact(ref):
            suffix='.json' if ref.get('media_type','application/json')=='application/json' else '.bin'
            return json.load(archive.extractfile('artifacts/'+ref['artifact_id']+suffix))
        snapshot=json.load(archive.extractfile(next(n for n in archive.getnames() if n.startswith('snapshot/'))))
        state=snapshot['session']['state'];candidate=artifact(refs['candidate'])
        source=artifact(refs['measured_schedule']);nmpc=artifact(refs['nmpc'])
        observations=artifact(source['provenance']['measured_input_reference'])
    tr=source['trajectory'];p=source['provenance']
    assert len(observations)==35 and p['execution_reference']==refs['nmpc']
    assert p['execution_id']==nmpc['execution_id'] and nmpc['profile']['complete']
    assert np.array_equal(tr['tensions_n'],[r['actual_tension_n'] for r in observations])
    assert np.allclose([r['time_s'] for r in observations],tr['times_s'][:-1],rtol=0,atol=1e-12)
    variants={}
    for label,young in MODULI.items():
        low,high=state['spec']['allowed_parameters']['segments.distal1.young_pa']
        assert low<=young<=high
        parameters=deepcopy(candidate['parameters']);set_parameter(parameters,'segments.distal1.young_pa',young)
        cfg=resolved_configuration(state['nominal_configuration'],candidate['configuration'],parameters,
            'mujoco-reoptimized-structure-'+label)
        schedule=initialize_schedule(cfg,source,refs['candidate'])
        variants[label]=dict(configuration=cfg,parameters=parameters,schedule=schedule)
    return variants,dict(archive='evidence/mujoco_c1_autonomous/immutable_artifacts.tar.gz',
        candidate=refs['candidate'],schedule=refs['measured_schedule'],execution=refs['nmpc'],
        actual_input=p['measured_input_reference'],execution_id=p['execution_id'],units='N',
        field='actual_tension_n',inherited_state=False,inherited_acceptance=False)


def prepare():
    import mujoco,scipy
    variants,origin=inputs();cfg=variants['d_zero']['configuration'];adapter=task_adapter(cfg)
    assert cfg['task']['timing']==dict(timestep_s=.0005,control_period_s=.01,sample_period_s=.01,
        duration_s=.35,termination=['duration','numerical_failure'])
    frozen=dict(baseline='e5cb92dd757f741ddab2fa1ee90fcfcbd3c97c8b',source=origin,
        moduli_pa=MODULI,parameters=variants['d_zero']['parameters'],settings=plain(LocalControlSearchSettings(**SETTINGS)),
        task=dict(identity=digest(cfg['task']),target_m=cfg['task']['goal']['data']['target_m'],
            timing=cfg['task']['timing'],limits=adapter.ranking_limits(),holding_start_s=adapter.holding_start_s()),
        tendon_order=variants['d_zero']['schedule']['trajectory']['tendon_order'],
        runtime=dict(python=platform.python_version(),mujoco=mujoco.__version__,numpy=np.__version__,scipy=scipy.__version__),
        physics_step_limit=STEP_LIMIT,worst_case_steps=6*30*700+6*700,
        cold_start_rule='After complete warm search and replay, run three pretension starts if >=63000 steps remain and no numerical failure.',
        metric='max(terminal_error/0.01, hold_position/0.01, hold_speed/0.02)-1',
        rank=['signed_maximum_excess','sum_normalized_excess'],stop_when=None,
        scope='engineering validation; no formal Study or SELECT',raw_directory=str(RUN))
    RUN.mkdir(parents=True,exist_ok=False)
    atomic_json(RUN/'inputs.json',variants);atomic_json(EVIDENCE/'frozen_plan.json',frozen)
    print(json.dumps(frozen,ensure_ascii=False,indent=2))


def options(cfg):
    adapter=task_adapter(cfg);limits=adapter.ranking_limits()
    return dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],
        speed_limit=limits['holding_max_speed_m_s'])


def measure(outputs,opts):
    value=task_measure(outputs,**opts)
    ratios=dict(terminal_position=value['terminal_position_error_m']/opts['terminal_position_limit'],
        holding_position=value['holding_max_position_error_m']/opts['position_limit'],
        holding_speed=value['holding_max_speed_m_s']/opts['speed_limit'])
    hold=np.asarray(outputs['times_s'])>=opts['holding_start']-1e-12
    return dict(**value,dominant_constraint=max(ratios,key=ratios.get),terminal_position_m=outputs['tip_positions_m'][-1],
        holding_samples=[dict(time_s=t,position_m=p,velocity_m_s=v) for t,p,v,keep in zip(
            outputs['times_s'],outputs['tip_positions_m'],outputs['tip_velocities_m_s'],hold) if keep])


def optimize(native,start,schedule,opts,folder,record,guard):
    initial=dict(id=folder.name,schedule=schedule,limits=native.limits[:,1].tolist(),task_options=opts)
    def evaluate(_start,source,metadata):
        guard();outputs=native.rollout_sequence(start,source['trajectory']['times_s'],source['trajectory']['tensions_n'])
        value=measure(outputs,opts)
        row=dict(reference=folder.name+'-'+str(native.cost['rollouts']),outputs=outputs,measure=value,
            task_gap=dict(valid_complete=True,accepted=False,normalized_gap=value['normalized_gap']),
            independent_evaluation_executed=False,cost_s=0.)
        atomic_json(folder/(row['reference']+'.json'),dict(**row,metadata=metadata,cost=deepcopy(native.cost)))
        record();return row
    result=search([initial],evaluate,SETTINGS,evaluation_kind='native_full_sequence',stop_when=None,
        rank_key=lambda r:(r['measure']['signed_maximum_excess'],r['measure']['sum_normalized_excess']))
    atomic_json(folder/'search.json',result)
    best=result['best'];optimized=deepcopy(schedule)
    optimized['trajectory']['tensions_n']=corrected_tensions(schedule['trajectory']['tensions_n'],
        schedule['trajectory']['times_s'][:-1],SETTINGS['knots_s'],best['coefficients_n'],
        native.limits[:,1],SETTINGS['correction_window_s']).tolist()
    atomic_json(folder/'best_schedule.json',optimized)
    u=np.asarray(optimized['trajectory']['tensions_n']);delta=u-np.asarray(schedule['trajectory']['tensions_n'])
    coefficients=np.asarray(best['coefficients_n'])
    summary=dict(initial=result['candidates'][0]['measure'],best=best['measure'],best_reference=best['reference'],
        best_label=best['label'],stop_reason=result['stop_reason'],cost=result['cost_feedback'],
        iterations=result['iterations_started'],local_responses=result['local_responses'],
        solver=[r['local_solver'] for r in result['candidates'] if 'local_solver' in r],
        effective_improvement=result['candidates'][0]['measure']['signed_maximum_excess']-best['measure']['signed_maximum_excess'],
        coefficients_n=best['coefficients_n'],correction_l2_n=float(np.linalg.norm(delta)),
        correction_inf_n=float(np.max(abs(delta))),coefficient_l2_n=float(np.linalg.norm(coefficients)),
        maximum_tension_n=float(u.max()),minimum_tension_n=float(u.min()),
        input_boundary=bool(np.any(u<=1e-10) or np.any(u>=native.limits[:,1]-1e-10)),
        trust_boundary=bool(np.max(abs(coefficients))>=SETTINGS['initial_radius_n']-1e-8),
        detail=str((folder/'search.json').relative_to(ROOT)))
    return optimized,best['outputs'],summary


def response_estimate(rows):
    def secant(field):
        a,b=rows['d_minus'][field],rows['d_plus'][field]
        if a is None or b is None:return None
        return (b['signed_maximum_excess']-a['signed_maximum_excess'])/1.08
    return dict(name='Finite-budget MuJoCo reoptimized structural response estimate',
        unit='normalized signed excess / MPa',fixed_per_mpa=secant('fixed'),
        reoptimized_per_mpa=secant('warm_best'),reliable_structure_direction='unknown',
        derivative_valid=False,interpretation='Descriptive finite-search secant; convergence, initialization and numerical error are not bounded.')


def run():
    from extensions.tendon_family.mujoco_analysis import NativeModel
    from extensions.tendon_family.backends import playback_tensions
    frozen=read(EVIDENCE/'frozen_plan.json');variants=read(RUN/'inputs.json')
    assert frozen['settings']==plain(LocalControlSearchSettings(**SETTINGS)) and frozen['moduli_pa']==MODULI
    marker=RUN/'execution.json'
    if marker.exists():raise ValueError('EXPERIMENT_ALREADY_STARTED_NO_AUTOMATIC_RELAUNCH')
    natives={};replay_steps=0;rows={label:{} for label in variants};began=time.perf_counter()
    ledger=dict(status='running',implementation=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    def record():
        ledger.update(native_cost={k:deepcopy(n.cost) for k,n in natives.items()},replay_steps=replay_steps,
            physics_steps=sum(n.cost['physics_steps'] for n in natives.values())+replay_steps,wall_s=time.perf_counter()-began)
        atomic_json(marker,ledger)
    def guard():
        record()
        if ledger['physics_steps']+700>STEP_LIMIT:raise ValueError('PHYSICS_STEP_BUDGET_EXHAUSTED')
    record()
    try:
        for label,item in variants.items():
            cfg=item['configuration'];native=natives[label]=NativeModel(cfg)
            assert native.model.opt.timestep==.0005 and native.tendons==frozen['tendon_order']
            assert np.array_equal(native.limits,np.tile([0.,8.],(6,1)))
            scene=native.scene;assert not any(scene['qpos_rad']) and not any(scene['qvel_rad_s'])
            point=dict(physics_identity=native.physics['identity'],candidate=label,configuration_identity=digest(cfg),
                native_replay=dict(rows=[],scene=scene),u=[t['pretension_n'] for t in cfg['robot']['structure']['data']['tendons']],
                provenance=dict(initialization='own frozen zero state',inherited_acceptance=False))
            point,start=native.reconstruct(point);item['start']=start
            atomic_json(RUN/label/'initial_state.json',point)
            guard();outputs=native.rollout_sequence(start,item['schedule']['trajectory']['times_s'],item['schedule']['trajectory']['tensions_n'])
            rows[label]['fixed']=measure(outputs,options(cfg));atomic_json(RUN/label/'fixed.json',outputs);record()
        for label,item in variants.items():
            native=natives[label];before=deepcopy(native.cost)
            schedule,prediction,summary=optimize(native,item['start'],item['schedule'],options(item['configuration']),RUN/label/'warm',record,guard)
            rows[label].update(warm=summary,warm_best=summary['best'],warm_native_cost={k:native.cost[k]-before[k] for k in before})
            item.update(best_schedule=schedule,prediction=prediction)
        for label,item in variants.items():
            cfg=item['configuration'];schedule=item['best_schedule'];inp,physics,scene=binding(cfg,schedule['trajectory']);guard()
            raw=playback_tensions(inp,physics,scene,schedule['trajectory']['tensions_n'],RUN/label/'replay')
            replay_steps+=raw['physics_steps'];record();atomic_json(RUN/label/'replay/raw.json',raw)
            # Existing source identities identify the NEW raw result, not an old accepted artifact.
            raw_ref=dict(artifact_id=digest(raw),media_type='application/json')
            evaluation,profile=evaluate_playback(cfg,raw,raw_ref,digest(cfg))
            acceptance=assemble_acceptance(cfg,evaluation,profile,motion=[dict(time_s=r['time_s']) for r in raw['samples']])
            actual=task_outputs(raw);difference={k:float(np.max(abs(np.asarray(actual[k])-item['prediction'][k]))) for k in actual}
            rows[label]['replay']=dict(acceptance=acceptance,measure=measure(actual,options(cfg)),
                prediction_difference=difference,physics_steps=raw['physics_steps'],command_intervals=raw['command_intervals'],
                raw_reference=raw_ref,detail=str((RUN/label/'replay/raw.json').relative_to(ROOT)))
            atomic_json(RUN/label/'replay/evaluation.json',dict(evaluation=plain(evaluation),profile=profile,acceptance=acceptance))
        if all(r['replay']['acceptance']['status'] in ('accepted','valid_failure') for r in rows.values()) and STEP_LIMIT-ledger['physics_steps']>=63000:
            for label,item in variants.items():
                cfg=item['configuration'];cold=deepcopy(item['schedule'])
                cold['trajectory']['tensions_n']=[[t['pretension_n'] for t in cfg['robot']['structure']['data']['tendons']]]*35
                cold['provenance']=dict(initialization='own candidate pretension',inherited_acceptance=False)
                binding(cfg,cold['trajectory']);native=natives[label];before=deepcopy(native.cost)
                _,_,summary=optimize(native,item['start'],cold,options(cfg),RUN/label/'cold',record,guard)
                rows[label].update(cold=summary,cold_native_cost={k:native.cost[k]-before[k] for k in before})
        ledger['status']='completed'
    except Exception as exc:
        ledger.update(status='failed',error=repr(exc));raise
    finally:
        record();atomic_json(RUN/'partial_summary.json',rows)
    summary=dict(scope=frozen['scope'],frozen_plan='evidence/mujoco_reoptimized_structure/frozen_plan.json',
        results=rows,response=response_estimate(rows),resources=ledger,
        forbidden_work=dict(provider=0,formal_study=0,nmpc=0,ppo=0,matlab=0),raw_directory=str(RUN))
    atomic_json(EVIDENCE/'summary.json',summary)
    print(json.dumps(dict(resources=ledger,response=summary['response']),ensure_ascii=False,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'run':run}[sys.argv[1]]()
