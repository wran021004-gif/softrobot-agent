"""Historical candidate views and exact applied-input handoffs; no execution."""
from copy import deepcopy
import hashlib
import tempfile
from pathlib import Path
import numpy as np
from tools.research import holding_diagnostic as history
from tools.research.numerics import archived, ROOT
from tools.research.feedback import task_gap
from tools.state_io import read, digest


def ranking_key(row):
    gap=row['task_gap']
    valid=gap['valid_complete'] and gap['normalized_gap'] is not None
    return (not (valid and gap['accepted']),not valid,
        gap['normalized_gap'] if valid else float('inf'),
        sum(gap['components'].values()) if valid else float('inf'))


def portfolio(rows):
    """Partition by exact task AND metric protocol; designs stay independent."""
    groups={}
    for row in rows:groups.setdefault(digest([row['task_identity'],row['metric_identity']]),[]).append(row)
    views=[]
    for identity,group in sorted(groups.items()):
        ranked=sorted(group,key=ranking_key)
        valid=[r for r in ranked if r['task_gap']['valid_complete'] and all(v is not None for v in r['metrics'].values())]
        def axes(r):return max(r['metrics']['terminal_position_error_m'],r['metrics']['holding_max_position_error_m']),r['metrics']['holding_max_speed_m_s']
        pareto=[r['source_result'] for r in valid if not any(
            all(a<=b for a,b in zip(axes(q),axes(r))) and any(a<b for a,b in zip(axes(q),axes(r))) for q in valid)]
        views.append(dict(comparison_identity=identity,ranked=ranked,position_speed_pareto=pareto))
    return dict(version='candidate_portfolio_v1',historical_only=True,groups=views)


def record(folder, reference, diagnostic=None):
    """All archive access uses the existing hash-verified importer."""
    from schemas.platform import SessionInput
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from extensions.tendon_family.mjcf import compile_xml
    from tools.platform_registry import registry
    result=archived(folder,reference);candidate=archived(folder,result['candidate']);cfg=candidate['configuration']
    inp=SessionInput.model_validate(cfg);physics=physics_for(inp);scene=assemble(inp,physics)
    spec=scene['control']['specification'];order=spec['tendon_order'];gap=task_gap(result)
    gap=deepcopy(gap)
    if not gap['valid_complete']:gap['normalized_gap']=None
    episodes=result.get('episodes',[]);metrics=(result.get('acceptance') or {}).get('metrics',{})
    names=('terminal_position_error_m','holding_max_position_error_m','holding_max_speed_m_s')
    if episodes:metrics={k:max((e[k] for e in episodes if e.get(k) is not None),default=None) for k in names}
    else:metrics=dict(zip(names,[metrics.get(k) for k in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')]))
    from tools.research_tasks import task_adapter
    metric_identity=digest(task_adapter(cfg).describe())
    row=dict(source_folder=folder,source_result=reference,source_candidate=result['candidate'],
        study=result.get('owning_study',result.get('study')),execution_id=result.get('execution_id'),
        controller=result.get('policy_sha256',digest(cfg['policy']['controller'])),
        task_identity=digest(cfg['task']),robot_identity=digest(cfg['robot']),design_identity=spec['design_identity'],
        model_identity=spec['identity'],metric_identity=metric_identity,tendon_order=order,control_mode='ideal_tension',
        metrics=metrics,task_gap=gap,original_acceptance=result['acceptance'],
        historical_status='original_task_passed' if gap['valid_complete'] and gap['accepted'] else
            'valid_task_failure' if gap['valid_complete'] else 'invalid_or_incomplete_execution',
        replay_status='replay_unavailable',rejection_reasons=[],schedule=None,
        cost=dict(numerical_s=result.get('charged_numerical_s',result.get('evaluation_elapsed_s',result.get('numerical_s'))),
            source_pointer='/charged_numerical_s' if 'charged_numerical_s' in result else
                '/evaluation_elapsed_s' if 'evaluation_elapsed_s' in result else '/numerical_s'),
        lineage=candidate.get('provenance'),source_hash=reference['artifact_id'])
    try:
        if scene['control']['tension_execution_mode']!='ideal_tension':raise ValueError('IDEAL_TENSION_REQUIRED')
        if diagnostic is None:
            if result.get('raw_reference'):
                raw=archived(folder,result['raw_reference'])
                diagnostic=dict(sampling_phase='post_control_interval',tendon_order=raw['tendon_order'],
                    timeline=[dict(time_s=r['time_s'],actual_tension_n=r['actual_tension_n'],
                        control_update_index=r['control_step']-1) for r in raw['samples']])
            else:raise ValueError('SAVED_APPLIED_TRAJECTORY_REQUIRED')
        if diagnostic.get('effective_configuration'):
            effective=diagnostic['effective_configuration'];task=effective['task']
            if (task['original']!=cfg['task'] or task['initializer']!=scene['initial'] or
                    task['target_m']!=scene['target_world_m'] or effective['candidate']['identity']!=candidate['identity'] or
                    effective['control_object']['semantics']!='ideal_tension'):
                raise ValueError('RL_TASK_INITIAL_DESIGN_OR_MODE_MISMATCH')
            with tempfile.TemporaryDirectory() as tmp:
                xml=compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),Path(tmp)/'robot.xml').read_text(encoding='utf8')
            if hashlib.sha256(xml.encode()).hexdigest()!=effective['candidate']['sha256']:
                raise ValueError('RL_PHYSICAL_MODEL_HASH_MISMATCH')
            row['physical_model_sha256']=effective['candidate']['sha256']
        elif diagnostic.get('source_files'):
            old=archived(folder,diagnostic['source_files']['control_spec.json'])
            if digest(old['specification'])!=digest(spec) or old['task']!=cfg['task'] or old['robot']!=cfg['robot']:
                raise ValueError('NMPC_MODEL_TASK_OR_DESIGN_MISMATCH')
            row['physical_model_sha256']=diagnostic['source_files']['robot.xml']['artifact_id']
        timing=cfg['task']['timing'];count=round(timing['duration_s']/timing['control_period_s'])
        limits=[next(t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons'] if t['id']==name) for name in order]
        if count!=35 or len(order)!=4:raise ValueError('CURRENT_35_BY_4_TASK_REQUIRED')
        u=history.applied_schedule(diagnostic['timeline'],phase=diagnostic['sampling_phase'],
            period=timing['control_period_s'],timestep=timing['timestep_s'],intervals=count,
            order=diagnostic['tendon_order'],expected_order=order,limits=limits)
        row.update(replay_status='pending_independent_replay',sequence_hash=digest(u),
            schedule=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',
                provenance=dict(folder=folder,result=reference,candidate=result['candidate'],
                    files=diagnostic.get('source_files'),trajectory=diagnostic.get('raw_trajectory_reference',result.get('raw_reference')),
                    raw_folder=diagnostic.get('raw_folder',folder),sampling_phase=diagnostic['sampling_phase']),
                trajectory=dict(tensions_n=u,times_s=[k*timing['control_period_s'] for k in range(count+1)],
                    tendon_order=order,model_identity=spec['identity'],design_identity=spec['design_identity'],task_identity=digest(cfg['task']))))
    except (ValueError,KeyError,StopIteration) as exc:row['rejection_reasons'].append(str(exc))
    return row


def historical_records():
    """Reuse S5.6/S5.8 readers; retain S5.9 RL and S5.10 physical comparison."""
    diagnostics=history.historical()['results'];rows=[]
    for d in diagnostics:
        rows.append(record(d['source_folder'],d['source_result'],d if d['route']!='fixed_tension' else None))
    folder='evidence/sorosim_s59/study';checkpoints=read(ROOT/'evidence/sorosim_s59/checkpoints/summary.json')
    for r in read(ROOT/'evidence/sorosim_s59/summary.json')['results']:
        result=archived(folder,r['reference'])
        checkpoint=next(x for x in checkpoints['runs'] if x['run_id']==result['run_id'])
        rows.append(record(folder,r['reference'],history.rl(folder,r['reference'],checkpoint['archive'],checkpoint['raw_files_index'])))
    best=read(ROOT/'evidence/sorosim_s510/summary.json')['ranked_candidates'][0]
    rows.append(record('evidence/sorosim_s510/study',best['reference']))
    return rows


def compatible_schedule(row, configuration):
    """Check the target before transferring a control; no execution implied."""
    from tools.research.physical_replay import binding
    if row['replay_status']!='pending_independent_replay':raise ValueError('REPLAY_UNAVAILABLE')
    if digest(configuration['robot'])!=row['robot_identity'] or digest(configuration['task'])!=row['task_identity']:
        raise ValueError('CONTROL_TRANSFER_ROBOT_OR_TASK_MISMATCH')
    binding(configuration,row['schedule']['trajectory'])
    return deepcopy(row['schedule'])
