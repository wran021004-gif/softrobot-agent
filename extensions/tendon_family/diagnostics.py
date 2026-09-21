"""Named saved-signal adaptation of the existing reach-event criteria."""
import numpy as np
from schemas.platform import BackendResult
from tools.trajectory_diagnosis import RULES, intervals
from tools.state_io import read
from tools.platform_store import plain


def diagnose(ctx,args,source):
    result=BackendResult.model_validate(ctx.artifact(args.result))
    folder=source['root']; p=read(folder/'resolved_physics.json'); scene=read(folder/'experiment_scene.json')
    direct_tension=scene['control'].get('tension_execution_mode')=='ideal_tension'
    events=[]; queries=[]; missing=[]
    signals={(s.spec.name,s.spec.entity):s for s in result.signals}
    def series(name,entity):
        s=signals.get((name,entity))
        if s is None or not s.values:
            missing.append(dict(signal=name,entity=entity,reason='not recorded')); return None
        t=np.asarray(s.times_s); v=np.asarray(s.values)
        mask=np.ones(len(t),dtype=bool)
        if args.t_start_s is not None: mask &= t>=args.t_start_s
        if args.t_end_s is not None: mask &= t<=args.t_end_s
        ids=np.flatnonzero(mask)
        if not len(ids): missing.append(dict(signal=name,entity=entity,reason='no samples in requested interval')); return None
        return s,t,v,ids,mask
    def record(item,ids,kind,values,rule):
        s,t,_,_,_=item
        return dict(candidate_id=source['metadata']['candidate'],backend=result.backend_id,model_id=result.model_id,
            entity=s.spec.entity,signal=s.spec.name,frame=s.spec.frame,phase=s.spec.phase,units=s.spec.units,
            time_range_s=[float(t[ids[0]]),float(t[ids[-1]])],sample_indices=[int(i) for i in ids],
            observation=kind,values=values,criterion=rule,evidence=dict(result=plain(args.result),signal=plain(s.spec),
                time_range_s=[float(t[ids[0]]),float(t[ids[-1]])]),possible_causes=[],recommendations=[])
    def inspect(name,entity,rules=()):
        if args.entity not in ('all',entity): return
        item=series(name,entity)
        if item is None:return
        s,t,v,ids,mask=item
        if not np.isfinite(v[ids]).all():
            missing.append(dict(signal=name,entity=entity,reason='nonfinite saved values'));return
        queries.append(record(item,ids,'sampled_range',dict(minimum=float(v[ids].min()),maximum=float(v[ids].max()),
            final=v[ids[-1]].tolist()),'saved samples; extrema are not continuous-time bounds'))
        for hit,kind,criterion in rules:
            for g in intervals(hit(v[:,0]) & mask,t):
                events.append(record(item,g,kind,dict(minimum=float(v[g].min()),maximum=float(v[g].max())),criterion))
    tip=series('tip_position','tip') if args.entity in ('all','tip') else None
    if tip:
        s,t,v,ids,mask=tip; error=np.linalg.norm(v-np.asarray(scene['target_world_m']),axis=1)
        queries.append(record(tip,ids,'tip_error_over_time',dict(times_s=t[ids].tolist(),error_m=error[ids].tolist(),
            final_error_m=float(error[ids[-1]]),maximum_error_m=float(error[ids].max())),
            'Euclidean distance to saved TaskDefinition goal; descriptive only, no repeated evaluation'))
    for td in p['tendons']:
        limit=td['force_limit_n']; fraction=RULES['near_force_fraction']; zero=RULES['zero_force_n']
        if direct_tension:
            for signal in ('desired_tendon_tension','tendon_length','tendon_length_change','tendon_length_rate'):
                inspect(signal,td['entity'])
        inspect('tendon_tension',td['entity'],[
            (lambda v,limit=limit:v>=fraction*limit,'near_pull_limit',dict(threshold_n=fraction*limit,
                source='resolved_physics tendon.force_limit_n * tools.trajectory_diagnosis.RULES.near_force_fraction',
                minimum_duration_s=RULES['min_duration_s'],meaning='near limit does not prove controller clipping')),
            (lambda v:v<=zero,'near_zero_tension',dict(threshold_n=zero,source='tools.trajectory_diagnosis.RULES.zero_force_n',
                minimum_duration_s=RULES['min_duration_s'],meaning='near-zero positive pull; no independent slack measurement'))])
    for a in ([] if direct_tension else p['actuators']):
        name=a['id']; lo,hi=a['limits']; margin=(hi-lo)*(1-RULES['near_force_fraction'])
        inspect('actuator_command',name,[(lambda v,lo=lo,hi=hi,margin=margin:(v<=lo+margin)|(v>=hi-margin),
            'near_travel_limit',dict(limits=[lo,hi],margin=margin,source='saved actuator limits; 1% travel span',
                minimum_duration_s=RULES['min_duration_s'],meaning='sample proximity, not a clipping observation'))])
        if args.entity not in ('all',name):continue
        item=series('actuator_command',name)
        if item and len(item[1])>1:
            s,t,v,ids,_=item; rate=np.diff(v[:,0])/np.diff(t); end_ids=ids[ids>0]
            if len(end_ids):
                entry=record(item,end_ids,'sampled_command_rate',dict(maximum_abs=float(abs(rate[end_ids-1]).max()),
                    velocity_limit=a['velocity_limit'],near_limit=bool(np.any(abs(rate[end_ids-1])>=.99*a['velocity_limit']))),
                    'finite difference over adjacent saved command samples; 99% of saved velocity limit; no clipping claim')
                entry['units']=s.spec.units+'/s'; entry['difference_intervals_s']=[[float(t[i-1]),float(t[i])] for i in end_ids]
                queries.append(entry)
        else:missing.append(dict(signal='actuator_command_rate',entity=name,reason='requires two command samples'))
    for name in p['dofs']:
        inspect('joint_position',name); inspect('joint_velocity',name)
    if direct_tension and args.entity in ('all','tip'):
        observations=read(folder/'controller_observations.json')
        projected=[row for row in observations if 'projected_gvs_q' in row and
            (args.t_start_s is None or row['time_s']>=args.t_start_s) and
            (args.t_end_s is None or row['time_s']<=args.t_end_s)]
        if projected:
            queries.append(dict(candidate_id=source['metadata']['candidate'],backend=result.backend_id,
                observation='projected_gvs_state',entity='tip',signal='controller_observations',
                time_range_s=[projected[0]['time_s'],projected[-1]['time_s']],
                values=dict(initial_q=projected[0]['projected_gvs_q'],final_q=projected[-1]['projected_gvs_q'],
                    initial_qdot=projected[0]['projected_gvs_qdot'],final_qdot=projected[-1]['projected_gvs_qdot'],
                    maximum_projection_residual_rad_m=max(row['gvs_projection_residual_max_rad_m'] for row in projected),
                    maximum_rate_projection_residual_rad_m_s=max(row['gvs_rate_projection_residual_max_rad_m_s'] for row in projected)),
                criterion='saved pre-step controller projection; descriptive only',evidence=dict(result=plain(args.result),
                    saved_file='controller_observations.json')))
    times=[t for s in result.signals if s.spec.phase=='post_step' for t in s.times_s]
    raw_fields={}
    for name in args.fields:
        found=[s for s in result.signals if s.spec.name==name and args.entity in ('all',s.spec.entity)]
        if not found:missing.append(dict(signal=name,reason='unknown or unrecorded public signal'))
        raw_fields[name]=[]
        for s in found:
            item=series(name,s.spec.entity)
            if item:
                _,t,v,ids,_=item
                raw_fields[name].append(dict(spec=plain(s.spec),times_s=t[ids].tolist(),values=v[ids].tolist(),evidence=plain(args.result)))
    return dict(status='completed' if queries else 'missing_data',events=events,queries=queries,missing=missing,raw_fields=raw_fields,
        numerical=dict(solver_status=result.solver_status,reason=result.data.data.get('reason'),
            valid_state_range_s=[min(times),max(times)] if times else None,expected_duration_s=scene['duration_s'],
            evidence=plain(args.result)),backend_solves=0,rescoring=False,rules=RULES,
        limitations=['No joint limits are configured; no joint-limit violation inferred.',
            'Pre-step force and post-step state samples remain separate.',
            'Observations do not establish mechanical or controller causes.'])
