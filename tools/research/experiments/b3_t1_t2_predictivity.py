"""Freeze once, then compare B3 models and finite native control searches once.

Uses original generators, admission, kernels, search and independent evaluator.
No Provider, formal Study, Store mutation, NMPC or inherited task acceptance.
"""
from copy import deepcopy
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import tarfile
import time

import numpy as np

from schemas.platform import SessionInput
from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol
from tools.platform_store import plain
from tools.state_io import atomic_json, digest, read
from tools.research import analysis
from tools.research.contracts import AnalysisRequest, LocalControlSearchSettings
from tools.research.physical_replay import binding, initialize_schedule, evaluate_playback
from tools.research_tasks import assemble_acceptance, task_adapter

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'runs/b3-t1t2-control-predictivity'
EVIDENCE = ROOT / 'evidence/b3_t1_t2_control_predictivity'
ARCHIVE = 'evidence/b3_t2_pilot_050_c'
BASE = '78ca687fd893bfc805cfcaf1370ea62dd14dbf65'
MODULI = dict(d_minus=4.86e6, d_zero=5.40e6, d_plus=5.94e6)
SETTINGS = dict(version='local_control_search_v2', method='response',
    knots_s=[0., .38, .45, .50], correction_window_s=[0., .50],
    active_coefficients=[9, 10, 13, 14], coefficient_limit_n=2.,
    difference_step_n=.01, initial_radius_n=.1, minimum_radius_n=.0001,
    evaluation_requests=12, iterations=2, safety_margin_fraction=.05)


def r1_state():
    path = ROOT.parent / 'b3-r0-decision-efficiency/runs/research/b3-r1-history-assisted-050/platform.sqlite'
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True) as con:
        con.execute('PRAGMA query_only=ON')
        run, raw = con.execute('SELECT run_id,state FROM sessions').fetchone()
        s = json.loads(raw)
        return dict(run_id=run, size=path.stat().st_size, mtime_ns=path.stat().st_mtime_ns,
            research_status=s['research_status'], pending=s['pending'], freeze=s['freeze'],
            mathematical_evaluations=s['mathematical_evaluations'],
            results=len(s['results']), analysis_results=len(s['analysis_results']),
            calls=con.execute('SELECT COUNT(*) FROM calls').fetchone()[0],
            events=con.execute('SELECT COUNT(*) FROM events').fetchone()[0])


def prepare():
    """No mathematical solve or physics step; immutable source plus legal binding."""
    from tools.research.numerics import archived
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    from extensions.tendon_family.gvs_profile import mathematical_numerical
    from tools.research.optimal_capability import family_parameters
    import scipy, casadi, mujoco, cvxpy, clarabel
    with tarfile.open(ROOT/ARCHIVE/'immutable_artifacts.tar.gz') as archive:
        snapshot = json.load(archive.extractfile(next(n for n in archive.getnames() if n.startswith('snapshot/'))))
    s = snapshot['session']['state']
    parent = next(iter(s['candidates'].values()))
    candidate = archived(ARCHIVE, parent)
    replay_ref = s['physical_replays'][0]
    replay = archived(ARCHIVE, replay_ref)
    source_ref = replay['source_reference']; source = archived(ARCHIVE, source_ref)
    raw = archived(ARCHIVE, replay['raw_reference'])
    assert s['research_status']=='stopped' and source_ref==s['control_initializations'][-1]['source']
    assert source['trajectory']['tensions_n']==[r['actual_tension_n'] for r in raw['samples'][1:]]
    params, parameter = family_parameters(s['spec'], candidate, 'segments.1.young_pa')
    variants = {}
    for label, young in MODULI.items():
        request = deepcopy(params); request['segments']['1']['young_pa'] = young
        build = parse_build(dict(space=s['spec']['family_space'], request=request))
        robot, mesh, _ = generate_family(build)
        cfg = deepcopy(candidate['configuration']); cfg['run_id']='b3-predictivity-'+label
        cfg['robot']['structure']['data']=robot; cfg['policy']['discretization']['data']=mesh
        cfg['policy']['candidate_builder']['parameters']['data']=plain(build)
        cfg = plain(SessionInput.model_validate(cfg))
        numerical = mathematical_numerical(SessionInput.model_validate(cfg))
        schedule = initialize_schedule(cfg, source, parent)
        assert cfg['task']==candidate['configuration']['task'] and len(numerical['tendon_order'])==4
        assert numerical['measured_initial_state']==[0.]*len(numerical['measured_initial_state'])
        if label=='d_zero':
            assert robot==candidate['configuration']['robot']['structure']['data']
            assert mesh==candidate['configuration']['policy']['discretization']['data']
        variants[label]=dict(configuration=cfg, parameters=plain(build.request), schedule=schedule,
            binding=dict(candidate_id=cfg['run_id'], candidate=dict(artifact_id=digest(cfg),media_type='application/json'),
                configuration=dict(artifact_id=digest(cfg),media_type='application/json'),
                effective_configuration_identity=digest(cfg), task_identity=digest(cfg['task']),
                source_identity=candidate['source_identity'], basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis'],
                coordinate_order=numerical['coordinate_order'], tendon_order=numerical['tendon_order'],
                tension_limits_n=numerical['force_limits_n']))
    adapter=task_adapter(variants['d_zero']['configuration'])
    frozen=dict(version='b3_t1_t2_predictivity_v1', baseline=BASE, date='2026-10-26 Asia/Shanghai',
        scope='Independent mathematical/simulation engineering validation; no formal Study or SELECT',
        source=dict(folder=ARCHIVE,candidate=parent,schedule=source_ref,replay=replay_ref,
            raw=replay['raw_reference'],inherited_acceptance=False),
        task=dict(identity=digest(cfg['task']), target_m=cfg['task']['goal']['data']['target_m'],
            timing=cfg['task']['timing'],limits=adapter.ranking_limits(),holding_start_s=adapter.holding_start_s()),
        moduli_pa=MODULI,parameter=parameter,protocol=s['spec']['analysis_protocol'],
        settings=plain(LocalControlSearchSettings(**SETTINGS)),
        control_initialization='M2 C independently replayed schedule; identical absolute U0; legal per-design rebinding',
        active_rule='Same four knot-major coefficients 9,10,13,14 as saved M2 C search; declared before new results',
        math_rule='Three initial-point models; T1 values from the original single-scale T2 internal CONIC solves; no duplicate T1 or h/2',
        physical_rule='One fixed backend replay, one native search and one independent best-control backend replay per structure',
        metric='Original evaluator metrics: max(terminal/limit, holding_position/limit, holding_speed/limit)-1',
        judgment=dict(model_resolution='Original recorded primal/support estimates and T2 direction_status',
            physical_resolution='Observed deterministic differences separated from unknown nonlinear optimization error',
            ranking='No structure optimum ranking without bounded search/model error; no invented confidence interval',
            nmpc='Not allocated in this minimal single-scale experiment; no closed-loop verification'),
        caps=dict(provider=0,mathematical_evaluations=22,structures=3,callbacks_per_structure=12,
            updates_per_structure=2,fixed_replays_per_structure=1,best_replays_per_structure=1,
            physics_steps=50000,nmpc=0,ppo=0,matlab=0,formal_study=0),
        worst_case_physics_steps=3*(12+2)*1000,
        math_accounting='Engineering equivalent of original counters: 3 model/Gramian preparations + 3 CONIC + 2 dual-face + 3 native analyses = 11; no formal Store ledger created',
        runtime=dict(python=platform.python_version(), versions={m.__name__:m.__version__ for m in (np,scipy,casadi,mujoco,cvxpy,clarabel)}),
        r1_before=r1_state(),raw_directory=str(RUN))
    assert adapter.ranking_limits()==dict(terminal_error_m=.01,holding_max_error_m=.01,holding_max_speed_m_s=.02)
    RUN.mkdir(parents=True,exist_ok=False)
    atomic_json(RUN/'inputs.json',variants); atomic_json(EVIDENCE/'frozen_plan.json',frozen)
    print(json.dumps(dict(prepared=True, task=frozen['task'],settings=frozen['settings'],r1=frozen['r1_before']),ensure_ascii=False))


def playback(label, item, schedule, role):
    from extensions.tendon_family.backends import playback_tensions
    from tools.research.control_correction import task_outputs
    cfg=item['configuration']; inp,physics,scene=binding(cfg,schedule['trajectory'])
    folder=RUN/label/role
    raw=playback_tensions(inp,physics,scene,schedule['trajectory']['tensions_n'],folder)
    atomic_json(folder/'raw.json',raw)
    ref=dict(artifact_id=digest(raw),media_type='application/json')
    evaluation,profile=evaluate_playback(cfg,raw,ref,digest(cfg))
    acceptance=assemble_acceptance(cfg,evaluation,profile,motion=[dict(time_s=r['time_s']) for r in raw['samples']])
    atomic_json(folder/'evaluation.json',dict(evaluation=plain(evaluation),profile=profile,acceptance=acceptance))
    assert acceptance['status'] in ('accepted','valid_failure')
    limits=task_adapter(cfg).ranking_limits()
    J=max(acceptance['metrics'][k]/limits[k] for k in limits)-1
    hold=[r for r in raw['samples'] if r['time_s']>=task_adapter(cfg).holding_start_s()-1e-12]
    u=np.asarray(schedule['trajectory']['tensions_n'])
    return dict(acceptance=acceptance,J=J,physics_steps=raw['physics_steps'],
        maximum_tension_n=float(u.max()),minimum_tension_n=float(u.min()),
        upper_boundary_count=int(np.sum(u>=8.-1e-10)),lower_boundary_count=int(np.sum(u<=1e-10)),
        holding_peak_speed_time_s=max(hold,key=lambda r:r['speed_m_s'])['time_s'],
        reference=dict(file=str((folder/'raw.json').relative_to(ROOT)),pointer=''),raw_reference=ref,
        outputs=task_outputs(raw))


def run():
    from tools.research.optimal_capability import calculate_sensitivity
    from tools.research.capability import capability_summary, task_control_capability_comparison
    from extensions.tendon_family.mujoco_analysis import NativeModel
    frozen=read(EVIDENCE/'frozen_plan.json');items=read(RUN/'inputs.json')
    assert frozen['moduli_pa']==MODULI and frozen['settings']==plain(LocalControlSearchSettings(**SETTINGS))
    marker=RUN/'execution.json'
    if marker.exists():raise ValueError('ALREADY_STARTED_PRESERVE_RESULTS_NO_AUTOMATIC_RELAUNCH')
    ledger=dict(status='running',implementation=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        model_preparations=0,conic_attempts=0,dual_face_attempts=0,native_analyses=0,physics_steps=0,provider=0,nmpc=0)
    began=time.perf_counter();rows={};models={};p=TaskAnalysisProtocol.model_validate(frozen['protocol'])
    def record():
        ledger['physics_steps_including_inflight']=ledger['physics_steps']+ledger.get('native_inflight',{}).get('physics_steps',0)
        ledger['wall_s']=time.perf_counter()-began;atomic_json(marker,ledger)
    def checkpoint(name,value):
        atomic_json(RUN/'checkpoints'/(name+'.json'),value)
        if value.get('stage')=='attempt':
            kind=value.get('kind')
            if kind=='capability':ledger['conic_attempts']+=1
            elif kind=='dual_face':ledger['dual_face_attempts']+=1
        record()
    def guard_steps(count):
        if ledger['physics_steps']+count>frozen['caps']['physics_steps']:raise ValueError('PHYSICS_BUDGET_EXHAUSTED')
    record()
    try:
        for label,item in items.items():
            q=AnalysisRequest(candidate=item['binding']['configuration'],operation='linearization',
                operating_point='controller_start_input',scoring_window_s=.5,protocol=p)
            ledger['model_preparations']+=1;record()
            value=analysis.calculate(item['configuration'],item['binding'],plain(q))
            atomic_json(RUN/label/'model.json',value)
            if value['status']!='computed' or not value.get('model'):raise ValueError('MODEL_ADMISSION_FAILED')
            models[label]=value
        points=[]
        for label in ('d_zero','d_minus','d_plus'):
            item=items[label];value=models[label]
            points.append(dict(value=MODULI[label],parameters=item['parameters'],model=value['model'],
                requirements=value['task_analysis'],initial_delta=None,
                source_reference=dict(file=str((RUN/label/'model.json').relative_to(ROOT)),pointer='/model'),
                context=dict(source_identity=item['binding']['source_identity'],
                    topology_identity=digest([item['binding']['coordinate_order'],item['binding']['tendon_order']]),
                    fixed_configuration_identity=digest(dict(task=item['configuration']['task'],
                        policy={k:item['configuration']['policy'][k] for k in ('controller','backend','dynamics_model')})),
                    construction_rule='controller_start_input')))
        q=AnalysisRequest(candidate=items['d_zero']['binding']['configuration'],operation='task_capability',
            operating_point='controller_start_input',protocol=p,capability_method='sampled-affine-conic-minimax-v1')
        t2=calculate_sensitivity(dict(points=points,parameter=frozen['parameter'],baseline=models['d_zero']),q,checkpoint)
        atomic_json(RUN/'t2.json',t2)
        for point,sol in zip(points,t2['optimal_sensitivity'].get('numerical_optimality',[])):
            label=next(k for k,v in MODULI.items() if v==point['value'])
            models[label]['trajectory']=sol['result']
        for label,item in items.items():
            guard_steps(1000);fixed=playback(label,item,item['schedule'],'fixed')
            ledger['physics_steps']+=fixed['physics_steps'];record()
            rows[label]=dict(fixed=fixed)
        for label,item in items.items():
            guard_steps(12000)
            native=NativeModel(item['configuration'])
            assert native.tendons==item['binding']['tendon_order'] and native.model.opt.timestep==.0005
            assert np.array_equal(native.limits,np.tile([0.,8.],(4,1)))
            assert not any(native.scene['qpos_rad']) and not any(native.scene['qvel_rad_s'])
            point=dict(physics_identity=native.physics['identity'],candidate=item['binding']['configuration'],
                configuration_identity=digest(item['configuration']),native_replay=dict(rows=[],scene=native.scene),
                actual_time_s=0.,phase='interval_start_native',input_units='N',
                u=[t['pretension_n'] for t in item['configuration']['robot']['structure']['data']['tendons']],
                provenance=dict(initialization='own frozen zero initializer',inherited_acceptance=False))
            q=AnalysisRequest(candidate=item['binding']['configuration'],operation='mujoco_direct_control_v1',
                model_source='mujoco',operating_point='standardized_initial_pretension',protocol=p,
                control_optimization=dict(source=frozen['source']['schedule'],settings=SETTINGS))
            ledger['native_analyses']+=1;record()
            def native_progress(name,value):
                atomic_json(RUN/label/'native_progress'/(name+'.json'),value)
                ledger['native_inflight']=dict(candidate=label,**value.get('cost',{}));record()
            value=analysis.calculate(item['configuration'],item['binding'],plain(q),point,
                design_context=dict(schedule=item['schedule'],source=frozen['source']['schedule']),checkpoint=native_progress)
            atomic_json(RUN/label/'native.json',value)
            raw=value['native_dynamics'];cost=raw['cost'];ledger['physics_steps']+=cost['physics_steps']
            ledger.pop('native_inflight',None);record()
            assert cost['optimization_evaluations']<=12 and cost['optimization_iterations']<=2
            best=raw['optimization']['best'];schedule=raw['optimized_schedule']
            guard_steps(1000);actual=playback(label,item,schedule,'reoptimized')
            ledger['physics_steps']+=actual['physics_steps'];record()
            error={k:float(np.max(abs(np.asarray(actual['outputs'][k])-best['outputs'][k]))) for k in actual['outputs']}
            actual['native_replay_difference']=error
            settings=raw['optimization']
            rows[label].update(reoptimized=actual,native=dict(cost=cost,stop_reason=settings['stop_reason'],
                iterations=settings['iterations_started'],local_responses=settings['local_responses'],
                solver=[r['local_solver'] for r in settings['candidates'] if r.get('local_solver')],
                initial=settings['candidates'][0]['measure'],best=best['measure'],
                source=dict(file=str((RUN/label/'native.json').relative_to(ROOT)),pointer='/native_dynamics')))
        for label,item in items.items():
            model=EndpointLinearizedModel.model_validate(models[label]['model'])
            rows[label].update(candidate=dict(label=label,young_pa=MODULI[label],configuration_identity=digest(item['configuration'])),
                conditions=dict(task=frozen['task'],protocol=frozen['protocol'],settings=frozen['settings'],
                    initialization=frozen['control_initialization'],model_family='GVS structural-linear / native MuJoCo, 12 cells per segment'),
                mathematics=dict(trajectory=models[label].get('trajectory',{})),
                local=dict(state_dimension=len(model.x0),working_point=model.operating_point,x0=model.x0,u0=model.u0,
                    position_windows=[{k:w[k] for k in ('window_s','held','continuous')} for w in models[label]['metrics']['windows']],
                    authority=models[label]['metrics']['authority'],validity=models[label]['metrics']['validity']),
                t1=capability_summary(models[label].get('trajectory',{})),
                sources=dict(model=dict(file=str((RUN/label/'model.json').relative_to(ROOT)),pointer=''),
                    t2=dict(file=str((RUN/'t2.json').relative_to(ROOT)),pointer='/optimal_sensitivity')))
        ledger.update(status='completed',r1_after=r1_state())
        assert ledger['r1_after']==frozen['r1_before']
        record()
    except Exception as exc:
        ledger.update(status='failed',error=repr(exc));raise
    finally:
        record();atomic_json(RUN/'partial_summary.json',rows)
    comparison=task_control_capability_comparison(rows,t2=t2['optimal_sensitivity'])
    # Full trajectories/matrices stay in ignored runs; the committed view is derived.
    summary=deepcopy(rows)
    for row in summary.values():
        row.pop('mathematics');row.pop('local')
        for role in ('fixed','reoptimized'):row[role].pop('outputs')
    atomic_json(EVIDENCE/'summary.json',dict(candidates=summary,comparison=comparison,resources=ledger,
        mathematical_cost=t2['optimal_sensitivity'].get('computation_cost'),raw_directory=str(RUN)))
    print(json.dumps(dict(resources=ledger,comparison=comparison),ensure_ascii=False))


if __name__=='__main__':
    import sys
    {'prepare':prepare,'run':run}[sys.argv[1]]()
