"""Independent finite-program evidence checks and registered passive metrics.

Only recorded measurements are consumed. No engine, control or Store lives here.
"""
import numpy as np
from schemas.platform import Metric, ConstraintResult
from tools.state_io import digest
from .contracts import PassiveResponseGoalV2, PassiveResponseEvaluationV2
from .passive_program import force_at, window_rows, qualification


def state_ok(value, raw):
    body={k:v for k,v in value.items() if k!='state_identity'}
    n=raw['joint_count'];vector=np.asarray(value.get('state_vector',[]),float)
    return (value.get('version')=='passive_integration_state_v2' and digest(body)==value.get('state_identity')
        and value.get('physical_binding')==raw['physical_binding'] and value.get('mujoco_version')==raw['mujoco_version']
        and isinstance(value.get('state_spec'),int) and len(vector)>=1+2*n and np.isfinite(vector).all()
        and vector[0]==value['time_s'] and vector[1:1+n].tolist()==value['qpos_rad']
        and vector[1+n:1+2*n].tolist()==value['qvel_rad_s'])


def inspect(task,raw,*,intervention=False,qualification_failures=None):
    if raw.get('execution_checks',{}).get('level')=='screening':
        return 'incomplete','SCREENING_REQUIRES_ORIGINAL_FULL_VALIDATION'
    goal=PassiveResponseGoalV2.model_validate(task.goal.data)
    original=goal.execution_protocol=='phs2d_original_v1'
    hard=goal.execution_protocol in ('phs2d_original_v1','hard_equilibrium_continuous_v1')
    source=raw.get('physical_binding',{})
    if (raw.get('kind')!='passive_dynamic_execution_v2' or source.get('task_identity')!=digest(task.model_dump(mode='json'))
            or raw.get('active_actuators')!=0 or not source.get('design_identity') or not source.get('model_identity')):
        return 'invalid','PASSIVE_EXECUTION_SOURCE_MISMATCH'
    if raw.get('numerical_failure'):return 'invalid','MUJOCO_NUMERICAL_FAILURE'
    if raw.get('reason')=='UNLOADED_DYNAMIC_QUALIFICATION_FAILED':return 'invalid',raw['reason']
    episodes=raw.get('episodes',[]);dt=task.timing.timestep_s;period=task.timing.sample_period_s
    count=round(task.timing.duration_s/period);steps=round(task.timing.duration_s/dt)
    if [e.get('load_condition') for e in episodes]!=goal.load_conditions:return 'incomplete','REQUIRED_LOAD_CASE_MISSING'
    n=raw.get('joint_count',0);nt=len(raw.get('tendon_order',[]));nm=len(task.physical_problem['monitor_s'])
    if n<=0 or nt<=0 or len(raw.get('coordinate_order',[]))!=n:return 'invalid','MISSING_MODEL_DIMENSIONS'
    action=raw.get('intervention',{});disabled=[]
    if action.get('kind')!='none':
        if not intervention or goal.allowed_ablation!='disable_selected_passive_limits':return 'invalid','UNPAIRED_INTERVENTION_NOT_CANDIDATE_EVIDENCE'
        names=action.get('tendons',[])
        if not names or len(set(names))!=len(names) or set(names)-set(raw['tendon_order']) or action.get('only_limit_array_changed') is not True:
            return 'invalid','INVALID_LIMIT_INTERVENTION'
        disabled=[raw['tendon_order'].index(name) for name in names]
    physical_failures=qualification_failures if qualification_failures is not None else []
    try:
        first_state=None
        for e in episodes:
            rows=e['samples'];case=e['load_condition'];stages=goal.programs[case]
            if (not e['complete'] or len(rows)!=count+1 or e['physics_steps']!=steps or e['checked_physics_steps']!=steps
                    or not np.allclose([r['time_s'] for r in rows],np.arange(count+1)*period,rtol=0,atol=1e-10)):
                return 'incomplete','COMPLETE_DYNAMIC_GRID_REQUIRED'
            initial=e['integration_initial']
            if not state_ok(initial,raw) or e['state_resets']!=(2 if original else 1):return 'invalid','COMPLETE_INITIAL_STATE_MISMATCH'
            if first_state is None:first_state=initial
            elif initial!=first_state:return 'invalid','EPISODES_DID_NOT_RESET_SAME_COMPLETE_STATE'
            if raw['initial_state_source']=='saved_integration_state':
                if not goal.allow_saved_state or not raw.get('initial_state_result'):return 'invalid','SAVED_STATE_SOURCE_REQUIRED'
            elif hard:
                eq=raw['unloaded_equilibrium']
                expected_q=(np.asarray(eq['equilibrium']['qpos'])+goal.initial_perturbation_rad*np.sin(np.arange(n))).tolist()
                if (eq['status']!='qualified_local_minimum' or not eq['equilibrium']['kkt_pass'] or
                        not eq['equilibrium']['second_order_sufficient'] or not eq['equilibrium']['capacity'] or
                        any(eq['solver_settings'].get(k)!=v for k,v in goal.unloaded_static_solver.items()) or
                        initial['qpos_rad']!=expected_q or any(initial['qvel_rad_s']) or initial['time_s']!=0):
                    return 'invalid','QUALIFIED_FRESH_UNLOADED_EQUILIBRIUM_REQUIRED'
            else:
                named=task.initializer.parameters.data
                expected={key:[named[key].get(j,0.) for j in raw['coordinate_order']] for key in ('qpos_rad','qvel_rad_s')}
                if any(initial[k]!=v for k,v in expected.items()) or initial['time_s']!=0:return 'invalid','FROZEN_NAMED_INITIAL_STATE_MISMATCH'
            if original:
                loading=e['loading_initial'];boundary=e['phase_boundaries'][0]['integration_state']
                if (not state_ok(loading,raw) or loading['qpos_rad']!=boundary['qpos_rad'] or
                        any(loading['qvel_rad_s']) or loading['time_s']!=0 or
                        any(loading['state_vector'][1+2*n:])):
                    return 'invalid','QPOS_ONLY_COLD_LOADING_RESET_REQUIRED'
                prefix=[r for r in rows if r['time_s']<=stages[0].end_s]
                first_prefix=[r for r in episodes[0]['samples'] if r['time_s']<=stages[0].end_s]
                if prefix!=first_prefix:return 'invalid','SHARED_UNLOADED_BASELINE_MISMATCH'
                expected_steps=steps if e is episodes[0] else steps-round(stages[0].end_s/dt)
                if e['executed_physics_steps']!=expected_steps:return 'invalid','SHARED_BASELINE_COST_MISMATCH'
            if rows[0]['qpos_rad']!=initial['qpos_rad'] or rows[0]['qvel_rad_s']!=initial['qvel_rad_s']:
                return 'invalid','INITIAL_MEASUREMENT_MISMATCH'
            if len(e['phase_boundaries'])!=len(stages):return 'incomplete','PHASE_BOUNDARY_STATE_MISSING'
            for boundary,stage in zip(e['phase_boundaries'],stages):
                if boundary['stage']!=stage.name or boundary['time_s']!=stage.end_s or not state_ok(boundary['integration_state'],raw):
                    return 'invalid','PHASE_STATE_OR_CLOCK_MISMATCH'
                row=next(r for r in rows if abs(r['time_s']-stage.end_s)<1e-10)
                value=boundary['integration_state']
                engine_time=stage.end_s-(stages[0].end_s if original and stage is not stages[0] else 0)
                if value['qpos_rad']!=row['qpos_rad'] or value['qvel_rad_s']!=row['qvel_rad_s'] or abs(value['time_s']-e['engine_origin_s']-engine_time)>1e-8:
                    return 'invalid','PHASE_BOUNDARY_MEASUREMENT_MISMATCH'
            if e['qualified_state']!=e['phase_boundaries'][0]['integration_state']:return 'invalid','QUALIFIED_STATE_BINDING_MISMATCH'
            if disabled and e.get('intervention_at_s')!=stages[0].end_s:return 'invalid','INTERVENTION_BEFORE_COMMON_QUALIFICATION'
            for r in rows+e['qualification_samples']:
                shapes=dict(qpos_rad=(n,),qvel_rad_s=(n,),tip_m=(3,),tip_velocity_m_s=(3,),material_positions_m=(nm,3),
                    material_velocities_m_s=(nm,3),tendon_length_m=(nt,),length_residual_m=(nt,),actual_tension_n=(nt,),force_world_n=(3,))
                for field,shape in shapes.items():
                    a=np.asarray(r[field],float)
                    if a.shape!=shape or not np.isfinite(a).all():return 'invalid','NONFINITE_OR_MALFORMED_PHYSICAL_STATE'
                t=r['time_s'];held=t if goal.force_sampling=='interval_end' or t==0 else max(0.,t-dt)
                force=force_at(goal,case,held)[0];phase=force_at(goal,case,t)[1]
                if r['phase']!=phase or not np.allclose(r['force_world_n'],force,rtol=0,atol=1e-12):return 'invalid','FROZEN_FORCE_PROTOCOL_MISMATCH'
                engine_time=t-(stages[0].end_s if original and t>stages[0].end_s else 0)
                if abs(r['engine_time_s']-e['engine_origin_s']-engine_time)>1e-8:return 'invalid','ENGINE_CLOCK_MISMATCH'
                if not np.allclose(np.asarray(r['tendon_length_m'])-raw['payout_lengths_m'],r['length_residual_m'],rtol=0,atol=1e-12):
                    return 'invalid','MEASURED_LENGTH_RESIDUAL_MISMATCH'
                if any(w['number'] for w in r['warnings']):return 'invalid','MUJOCO_WARNING'
                if not isinstance(r['ncon'],int) or r['ncon']<0 or r['solver_iterations']<0 or r['nefc']<sum(map(len,r['constraint_states'])):
                    return 'invalid','INVALID_RECORDED_SOLVER_STATE'
                if len(r['constraint_states'])!=nt or len(r['constraint_residuals_m'])!=nt:return 'incomplete','ACTUAL_CONSTRAINT_ROWS_MISSING'
                for i,(tension,gap,states,residuals,label) in enumerate(zip(r['actual_tension_n'],r['length_residual_m'],r['constraint_states'],r['constraint_residuals_m'],r['constraint_classification'])):
                    if len(states)!=len(residuals) or not np.isfinite(residuals).all():return 'invalid','MALFORMED_CONSTRAINT_ROWS'
                    off=i in disabled and t>stages[0].end_s+1e-10
                    expected=('disabled' if off else 'taut' if tension>goal.tension_tolerance_n and states and max(states)>0 and gap>=-goal.length_tolerance_m
                        else 'slack' if gap<-goal.length_tolerance_m and tension<=goal.tension_tolerance_n and not states else 'transition_or_indeterminate')
                    if label!=expected:return 'invalid','CONSTRAINT_CLASSIFICATION_MISMATCH'
                if not np.isfinite([r['static_balance_inf_nm'],r['force_map_error_nm'],r['constraint_direction_error']]).all():return 'invalid','NONFINITE_BALANCE_OR_MAPPING'
            for rule in goal.qualifications:
                selected=window_rows(e['qualification_samples'] if rule.sampling=='every_physics_step' else rows,rule.window_s)
                sampling=dt if rule.sampling=='every_physics_step' else period
                grid=np.arange(round(rule.window_s[0]/sampling),round(rule.window_s[1]/sampling)+1)*sampling
                if len(selected)!=len(grid) or not np.allclose([r['time_s'] for r in selected],grid,rtol=0,atol=1e-10):
                    return 'incomplete','COMPLETE_QUALIFICATION_GRID_REQUIRED'
                observed=qualification(selected,rule,disabled_limits=disabled if rule.stage!=goal.unloaded_stage else ())
                if e['qualifications'].get(rule.stage)!=observed:return 'invalid','QUALIFICATION_RECOMPUTATION_MISMATCH'
                if not observed['passed']:physical_failures.append('DYNAMIC_STAGE_NOT_QUALIFIED:'+rule.stage)
            for key,limit in [('maximum_constraint_direction_error',goal.constraint_direction_tolerance),('maximum_force_map_error_nm',goal.force_map_tolerance_nm),('maximum_capacity_ratio',1.)]:
                if not np.isfinite(e[key]) or e[key]>limit:physical_failures.append('CONSTRAINT_MAPPING_OR_CAPACITY_INVALID:'+key)
            if e['minimum_constraint_multiplier_n'] < -goal.multiplier_sign_tolerance_n:physical_failures.append('UNILATERAL_MULTIPLIER_SIGN_INVALID')
            if e['maximum_enabled_length_excess_m']>goal.length_tolerance_m:physical_failures.append('ENABLED_TENDON_LENGTH_EXCESS')
            if set(e['stage_extrema'])!={s.name for s in stages} or sum(v['physics_steps'] for v in e['stage_extrema'].values())!=steps:
                return 'incomplete','PER_STEP_STAGE_EXTREMA_MISSING'
            if goal.route_check!='not_required':
                route=e['route_geometry'];expected_poses=(steps if goal.route_check=='every_physics_step' else count)+1
                if route['sampling']!=goal.route_check or route['checked_poses']!=expected_poses:return 'incomplete','ROUTE_POSE_COVERAGE_MISSING'
                if route['status']!='legal_at_checked_poses':physical_failures.append('ILLEGAL_TENDON_ROUTE_AT_CHECKED_POSES')
            if goal.recording=='full_physics_csv':
                traces=[v for v in raw['trace_files'] if v['load_condition']==case]
                trace_steps=e['executed_physics_steps'] if original else steps
                if len(traces)!=1 or traces[0]['physics_steps']!=trace_steps or traces[0]['bytes']<=0 or len(traces[0]['sha256'])!=64:
                    return 'incomplete','FULL_PHYSICS_TRACE_MISSING'
        expected_cost=sum(e['executed_physics_steps'] for e in episodes) if original else steps*len(episodes)
        if raw['physics_steps']!=expected_cost:return 'incomplete','PHYSICS_COST_COVERAGE_MISMATCH'
    except (KeyError,TypeError,ValueError,StopIteration,IndexError):return 'incomplete','REQUIRED_V2_MEASUREMENTS_MISSING'
    return ('invalid',';'.join(physical_failures)) if physical_failures else ('valid',None)


def stage_rows(goal,episode,name):
    """Use the frozen stage qualification grid when it covers the score window."""
    stage=next(s for s in goal.programs[episode['load_condition']] if s.name==name)
    dense=any(q.stage==name and q.sampling=='every_physics_step' and q.window_s[0]<=stage.scoring_window_s[0]
        and q.window_s[1]>=stage.scoring_window_s[1] for q in goal.qualifications)
    return window_rows(episode['qualification_samples'] if dense and episode.get('qualification_samples') else episode['samples'],stage.scoring_window_s)


def stiffness(task,raw,spec):
    """Independent stiffness and per-tendon observations, including failed predicates."""
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);case=spec.load_condition
    e=next(e for e in raw['episodes'] if e['load_condition']==case)
    names=[stage.name for stage in goal.programs[case]]
    if raw.get('execution_profile',{}).get('purpose')=='exploration':
        end=raw['execution_profile']['end_s'][case]
        names=[name for name in names if next(s for s in goal.programs[case] if s.name==name).end_s<=end]
    tails={name:stage_rows(goal,e,name) for name in names}
    stages={s.name:s for s in goal.programs[case]}
    def rows_for(name):
        rows=tails[name];window=stages[name].scoring_window_s
        period=raw.get('execution_profile',{}).get('sample_period_s',task.timing.sample_period_s)
        dense=any(q.stage==name and q.sampling=='every_physics_step' for q in goal.qualifications)
        if dense and raw.get('execution_profile',{}).get('purpose')!='exploration':period=task.timing.timestep_s
        expected=np.arange(round(window[0]/period),round(window[1]/period)+1)*period
        if not rows or len(rows)!=len(expected) or not np.allclose([r['time_s'] for r in rows],expected,rtol=0,atol=1e-10):
            raise ValueError('COMPLETE_STAGE_WINDOW_REQUIRED:'+name)
        return rows
    result=dict(valid=False,reason='UNRESOLVED_STIFFNESS_DENOMINATOR',denominator_valid=False,
        displacement_m=None,force_n=None,denominator_m=None,uncertainty_m=None,
        denominator_floor_m=None,interval_stiffness_n_m=None,stiffness_ratio=None)
    try:
        i=task.physical_problem['monitor_s'].index(spec.material_s);direction=np.asarray(spec.direction_world)
        positions={name:np.asarray([r['material_positions_m'][i] for r in rows_for(name)]) for name in names}
        if not all(np.isfinite(v).all() for v in positions.values()):raise ValueError('NONFINITE_POSITION')
        projected={name:v@direction for name,v in positions.items()}
        base=float(projected[spec.reference_stage].mean());d=np.array([projected[name].mean()-base for name in spec.stages])
        f=np.array([np.asarray(tails[name][-1]['force_world_n'])@direction for name in spec.stages])
        spread=max(float(np.max(np.linalg.norm(v-v.mean(axis=0),axis=1))) for v in positions.values())
        floor=max(spec.denominator_min_m,spec.denominator_uncertainty_multiplier*spread);dd=np.diff(d);df=np.diff(f)
        valid=bool(np.isfinite(f).all() and np.all(dd>floor) and np.all(df>0))
        k=df/dd if valid else None
        result.update(valid=valid,reason=None if valid else result['reason'],denominator_valid=valid,
            displacement_m=d.tolist(),force_n=f.tolist(),denominator_m=dd.tolist(),uncertainty_m=spread,
            denominator_floor_m=floor,interval_stiffness_n_m=k.tolist() if valid else None,
            stiffness_ratio=float(k[1]/k[0]) if valid else None)
    except (KeyError,IndexError,ValueError) as exc:result['reason']=str(exc)
    tendons=[]
    for i,name in enumerate(raw['tendon_order']):
        facts={};conditions={}
        for label,stage in zip(('low','middle','high'),spec.stages):
            try:
                rows=rows_for(stage)
                tension=np.asarray([r['actual_tension_n'][i] for r in rows]);residual=np.asarray([r['length_residual_m'][i] for r in rows])
                active=np.asarray([r['constraint_active'][i] for r in rows],bool)
                if not np.isfinite(tension).all() or not np.isfinite(residual).all():raise ValueError('NONFINITE_TENDON_DATA')
                facts[label]=dict(tension_min_n=float(min(tension)),tension_max_n=float(max(tension)),
                    slack_gap_min_m=float(min(-residual)),length_residual_max_m=float(max(abs(residual))),
                    signed_length_residual_min_m=float(min(residual)),signed_length_residual_max_m=float(max(residual)),
                    length_excess_max_m=float(max(0.,max(residual))),
                    active_fraction=float(active.mean()),window_s=list(stages[stage].scoring_window_s))
            except (KeyError,IndexError,ValueError) as exc:facts[label]=dict(missing_reason=str(exc))
        for key,stage,field,limit,lower in (
                ('low_tension','low','tension_max_n',spec.low_tension_max_n,False),
                ('low_slack','low','slack_gap_min_m',spec.low_slack_min_m,True),
                ('high_tension','high','tension_min_n',spec.high_tension_min_n,True),
                ('high_length','high','length_residual_max_m',spec.high_constraint_residual_max_m,False),
                ('high_active','high','active_fraction',1.,True)):
            value=facts[stage].get(field);margin=(value-limit if lower else limit-value) if value is not None else None
            conditions[key]=dict(value=value,threshold=limit,margin=margin,signed_violation=-margin if margin is not None else None,
                unit='N' if key.endswith('tension') else '1' if key.endswith('active') else 'm',passed=margin>=0 if margin is not None else None)
        passed=[v['passed'] for v in conditions.values()]
        transition=False if False in passed else None if None in passed else True
        low=facts['low'];high=facts['high']
        classification=('unresolved' if None in passed else 'valid_transition' if transition else
            'early_engagement' if conditions['low_tension']['passed'] is False or conditions['low_slack']['passed'] is False else
            'length_violation' if high['length_excess_max_m']>spec.high_constraint_residual_max_m else
            'intermittent_engagement' if 0<high['active_fraction']<1 or high['tension_min_n']<spec.high_tension_min_n<=high['tension_max_n'] else
            'no_high_engagement')
        tendons.append(dict(tendon=name,**facts,conditions=conditions,slack_to_taut=transition,classification=classification))
    transitions=[t['slack_to_taut'] for t in tendons]
    result.update(tendon_transitions=tendons,slack_to_taut=True if True in transitions else None if None in transitions or not transitions else False,
        transition_tendons=[t['tendon'] for t in tendons if t['slack_to_taut'] is True])
    return result


def constraint_names(task):
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    names={b.name+'_'+side for b in ev.bounds for side in ('minimum','maximum') if getattr(b,side) is not None}
    if ev.prohibit_contact:names.add('no_contact')
    for s in ev.progressive_stiffness:names.update((s.load_condition+'_stiffness_ratio',s.load_condition+'_slack_to_taut'))
    if ev.mechanism:names.update(s.load_condition+'_paired_mechanism' for s in ev.progressive_stiffness)
    return names


def bound_values(task, primary, b):
    """Pure frozen metric extraction shared by formal and diagnostic evaluation."""
    from .passive_response import reduce_vector
    goal=PassiveResponseGoalV2.model_validate(task.goal.data)
    e=next(e for e in primary['episodes'] if e['load_condition']==b.load_condition);stages={s.name:s for s in goal.programs[b.load_condition]}
    relative=b.quantity in ('material_displacement','tip_displacement','displacement_ratio','displacement_difference','unloaded_tip_drift')
    rows=stage_rows(goal,e,b.window);refs=stage_rows(goal,e,b.reference_window) if relative else []
    if not rows or relative and not refs:raise ValueError('SCORING_OR_REFERENCE_WINDOW_UNAVAILABLE')
    windows=[(b.window,rows,b.aggregation=='last')]
    if relative:windows.append((b.reference_window,refs,b.reference_reduction=='last'))
    for name,selected,last_only in windows:
        stage=stages[name];window=stage.scoring_window_s
        dense=any(q.stage==name and q.sampling=='every_physics_step' and q.window_s[0]<=window[0] and q.window_s[1]>=window[1] for q in goal.qualifications)
        period=primary.get('execution_profile',{}).get('sample_period_s',task.timing.timestep_s if dense else task.timing.sample_period_s)
        expected=[window[1]] if last_only else np.arange(round(window[0]/period),round(window[1]/period)+1)*period
        observed=[selected[-1]['time_s']] if last_only else [r['time_s'] for r in selected]
        if len(observed)!=len(expected) or not np.allclose(observed,expected,rtol=0,atol=1e-10):
            raise ValueError('COMPLETE_SCORING_OR_REFERENCE_GRID_REQUIRED')
    times=[r['time_s'] for r in rows]
    if b.aggregation=='mean_state':
        rows=[{**rows[-1],**{key:np.mean([r[key] for r in rows],axis=0).tolist() for key in ('material_positions_m','tip_m','material_velocities_m_s','tip_velocity_m_s') if key in rows[-1]}}]
    reference=lambda key:np.asarray(refs[-1][key]) if b.reference_reduction=='last' else np.mean([r[key] for r in refs],axis=0)
    i=task.physical_problem['monitor_s'].index(b.material_s);values=[]
    for r in rows:
        def point():
            delta=np.asarray(r['material_positions_m'][i])-reference('material_positions_m')[i]
            return float(np.linalg.norm(np.asarray(b.material_projection_world)@delta)) if b.material_projection_world is not None else reduce_vector(b,delta)
        def tip():
            delta=np.asarray(r['tip_m'])-reference('tip_m')
            return float(np.linalg.norm(np.asarray(b.tip_projection_world)@delta)) if b.tip_projection_world is not None else reduce_vector(b,delta)
        if b.quantity=='displacement_ratio' and max(point(),b.denominator_floor_m)==0:raise ValueError('ZERO_DISPLACEMENT_RATIO_DENOMINATOR')
        value={'material_displacement':point,'tip_displacement':tip,'displacement_ratio':lambda:tip()/max(point(),b.denominator_floor_m),
            'displacement_difference':lambda:tip()-b.material_scale*point(),'maximum_tension':lambda:max(r['actual_tension_n']),
            'maximum_length_excess':lambda:max([0.]+r['length_residual_m']),'material_speed':lambda:reduce_vector(b,np.asarray(r['material_velocities_m_s'][i])),
            'tip_speed':lambda:reduce_vector(b,np.asarray(r['tip_velocity_m_s'])),'unloaded_tip_drift':tip,
            'maximum_joint_position':lambda:max(abs(v) for v in r['qpos_rad']),'maximum_joint_speed':lambda:max(abs(v) for v in r['qvel_rad_s'])}[b.quantity]()
        values.append(value)
    if b.aggregation=='mean':values=[float(np.mean(values))]
    elif b.aggregation=='last':values=values[-1:]
    elif b.quantity in ('maximum_tension','maximum_length_excess','maximum_joint_position','maximum_joint_speed'):
        values.append(e['stage_extrema'][b.window]['scoring'][b.quantity])
    if not np.isfinite(values).all():raise ValueError('NONFINITE_DYNAMIC_METRIC')
    return values,times


def qualification_observations(task,raw):
    """Actual stage values and coverage; no reconstructed states or integrations."""
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);facts=[]
    for i,e in enumerate(raw.get('episodes',[])):
        for rule in goal.qualifications:
            sparse=raw.get('execution_profile',{}).get('purpose')=='exploration'
            dense=rule.sampling=='every_physics_step' and not sparse
            rows=window_rows(e.get('qualification_samples',[]) if dense else e.get('samples',[]),rule.window_s)
            period=task.timing.timestep_s if dense else raw.get('execution_profile',{}).get('sample_period_s',task.timing.sample_period_s)
            expected=np.arange(round(rule.window_s[0]/period),round(rule.window_s[1]/period)+1)*period
            complete=bool(rows and len(rows)==len(expected) and np.allclose([r['time_s'] for r in rows],expected,rtol=0,atol=1e-10))
            measurements={}
            definitions=(('tip_speed','tip_speed_max_m_s',lambda r:np.linalg.norm(r['tip_velocity_m_s']),'m/s'),
                ('monitor_speed','monitor_speed_max_m_s',lambda r:np.max(np.linalg.norm(r['material_velocities_m_s'],axis=1)),'m/s'),
                ('qvel','qvel_max_rad_s',lambda r:max(abs(v) for v in r['qvel_rad_s']),'rad/s'),
                ('static_balance','static_balance_max_nm',lambda r:r['static_balance_inf_nm'],'N*m'),
                ('length_excess','length_excess_max_m',lambda r:max([0.]+r['length_residual_m']),'m'))
            for name,field,extract,unit in definitions:
                try:
                    values=[float(extract(r)) for r in rows]
                    value=max(values) if values and np.isfinite(values).all() else None
                except (KeyError,ValueError,IndexError,TypeError):value=None
                limit=getattr(rule,field)
                measurements[name]=dict(value=value,threshold=limit,unit=unit,margin=limit-value if value is not None else None,
                    passed=value<=limit if value is not None else None,
                    role=rule.qvel_role if name=='qvel' else 'qualification')
            stored=e.get('qualifications',{}).get(rule.stage,{})
            measurements['tail_drift']=dict(value=stored.get('drift_m'),threshold=rule.tail_drift_max_m,unit='m',
                role='diagnostic' if 'tail_drift' in stored.get('diagnostic_checks',{}) else 'qualification')
            scales=[r['generalized_force_scale_nm'] for r in rows if r.get('generalized_force_scale_nm') is not None]
            normalized=[r['normalized_static_balance'] for r in rows if r.get('normalized_static_balance') is not None]
            facts.append(dict(load_condition=e['load_condition'],stage=rule.stage,measurements=measurements,
                generalized_force_scale_nm=max(scales) if scales else None,normalized_static_balance=max(normalized) if normalized else None,
                static_balance_calibration='incomplete; absolute frozen threshold retained',
                sampled_window_s=list(rule.window_s),sampling_period_s=period,sample_count=len(rows),
                complete_requested_grid=complete,frozen_qualification_coverage=complete and not sparse,
                source_pointer='/episodes/'+str(i),qualification=stored))
    return facts


def diagnostic_metrics(task, raw,*,include_mechanism=True):
    """Saved observations only, independently of qualification; no acceptance."""
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    primary=raw
    if 'baseline_cost' in (raw.get('paired_ablation') or {}):
        from extensions.tendon_family.passive_execution import baseline_arm
        primary=baseline_arm(raw)
    observations={}
    binding=primary.get('physical_binding',{})
    if binding.get('task_identity')!=digest(task.model_dump(mode='json')):return {}
    for b in ev.bounds:
        try:
            values,times=bound_values(task,primary,b)
            error=None
        except (KeyError,IndexError,StopIteration,TypeError,ValueError) as exc:
            values=[];times=[];error=str(exc) or 'REQUIRED_TRAJECTORY_UNAVAILABLE'
        for side,reduce in (('minimum',min),('maximum',max)):
            limit=getattr(b,side)
            if limit is None:continue
            value=reduce(values) if values else None
            # Aggregated states/extrema have no unique measured peak timestamp.
            sample_time=(times[-1] if b.aggregation=='last' else
                times[values.index(value)] if b.aggregation=='range' and len(values)==len(times) else None) if values else None
            observations['evaluator:'+b.name+'_'+side]=dict(value=value,limit=limit,unit=b.physical_unit,
                passed=(value>=limit if side=='minimum' else value<=limit) if value is not None else None,
                sample_time=sample_time,missing_reason=error,
                aggregation=b.aggregation,reference_window=b.reference_window,reference_reduction=b.reference_reduction)
    if ev.prohibit_contact:
        episodes=primary.get('episodes',[])
        complete=({e.get('load_condition') for e in episodes}>=set(task.goal.data['load_conditions'])
            and all(e.get('complete') and e.get('physics_steps')==round(task.timing.duration_s/task.timing.timestep_s) for e in episodes))
        value=max((e['maximum_contacts'] for e in episodes if 'maximum_contacts' in e),default=None)
        observations['evaluator:no_contact']=dict(value=value,passed=(value==0 if complete or value>0 else None) if value is not None else None,limit=0,unit='count',
            missing_reason=None if value is not None else 'REQUIRED_EPISODES_UNAVAILABLE')
    for spec in ev.progressive_stiffness:
        try:
            response=stiffness(task,primary,spec)
            error=None if response['valid'] else response['reason']
        except (KeyError,IndexError,StopIteration,TypeError,ValueError) as exc:
            response={};error=str(exc) or 'REQUIRED_STIFFNESS_TRAJECTORY_UNAVAILABLE'
        for suffix,limit,key in (('stiffness_ratio',spec.stiffness_ratio_min,'stiffness_ratio'),('slack_to_taut',1,'slack_to_taut')):
            value=float(response[key]) if response.get(key) is not None else None
            observations['evaluator:'+spec.load_condition+'_'+suffix]=dict(value=value,limit=limit,unit='1',
                passed=value>=limit if value is not None else None,missing_reason=error if value is None else None,
                observable=response if suffix=='slack_to_taut' else {k:v for k,v in response.items() if k not in ('tendon_transitions','transition_tendons','slack_to_taut')},time_window=[0.,task.timing.duration_s])
    if ev.mechanism and include_mechanism:
        responses={spec.load_condition:observations['evaluator:'+spec.load_condition+'_slack_to_taut']['observable'] for spec in ev.progressive_stiffness}
        pair=mechanism_metrics(task,raw,primary,responses)
        values={c.name:c for c in pair['constraints']}
        for spec in ev.progressive_stiffness:
            name=spec.load_condition+'_paired_mechanism';c=values.get(name)
            observations['evaluator:'+name]=dict(value=c.observed if c else None,limit=1.,unit='1',
                passed=c.satisfied if c else None,missing_reason=None if c else pair.get('reason'),
                source_pointers=['/episodes/'+str(i) for i,e in enumerate(primary.get('episodes',[])) if e['load_condition']==spec.load_condition]+
                    ['/paired_ablation/ablation/episodes/'+str(i) for i,e in enumerate((raw.get('paired_ablation') or {}).get('ablation',{}).get('episodes',[])) if e['load_condition']==spec.load_condition])
    return observations


def mechanism_metrics(task,raw,primary,observations,*,baseline_inspection=None):
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    pair=raw.get('paired_ablation');measured=[];constraints=[]
    def unknown(validity,reason):return dict(validity=validity,reason=reason,metrics=measured,constraints=constraints)
    def add(name,value,limit,unit,satisfied):
        measured.append(Metric(name=name,value=float(value),units=unit))
        constraints.append(ConstraintResult(name=name,observed=float(value),limit=float(limit),units=unit,satisfied=bool(satisfied)))
    valid,reason=baseline_inspection if baseline_inspection is not None else inspect(task,primary)
    if valid!='valid':return unknown(valid,'BASELINE_'+str(reason))
    if ev.mechanism:
        if not pair or pair.get('status')!='completed':return unknown('incomplete','COMPLETED_PAIRED_ABLATION_REQUIRED')
        other=pair['ablation'];valid,reason=inspect(task,other,intervention=True)
        if valid!='valid':return unknown(valid,'ABLATION_'+str(reason))
        if other['physical_binding']!=primary['physical_binding'] or other['base_model_signature']!=primary['base_model_signature'] or other['solver_options']!=primary['solver_options']:
            return unknown('invalid','PAIRED_PHYSICAL_SOURCE_MISMATCH')
        for a,b in zip(primary['episodes'],other['episodes']):
            if a['integration_initial']!=b['integration_initial'] or a['qualified_state']!=b['qualified_state']:return unknown('invalid','PAIRED_COMMON_STATE_MISMATCH')
        for arm,value in [('baseline',primary),('ablation',other)]:
            receipt=pair.get('arm_receipts',{}).get(arm,{})
            # Store annotations are outside the signed native receipt body.
            if receipt.get('raw_identity')!=digest(value) or receipt.get('execution_status')!='completed':return unknown('invalid','PAIRED_NATIVE_RECEIPT_MISMATCH')
        issues=[]
        for s in ev.progressive_stiffness:
            base=observations[s.load_condition];other_value=stiffness(task,other,s)
            if not base.get('valid'):
                issues.append('BASELINE_UNRESOLVED_STIFFNESS_DENOMINATOR:'+s.load_condition);continue
            if not other_value['valid']:
                issues.append('ABLATION_UNRESOLVED_STIFFNESS_DENOMINATOR:'+s.load_condition);continue
            if base['displacement_m'][-1]<=base['denominator_floor_m']:
                issues.append('UNRESOLVED_MECHANISM_DENOMINATOR:'+s.load_condition);continue
            high=other_value['displacement_m'][-1]/base['displacement_m'][-1]
            late=other_value['interval_stiffness_n_m'][-1]/base['interval_stiffness_n_m'][-1]
            passed=high>=ev.mechanism.high_displacement_increase_min or late<=ev.mechanism.late_stiffness_ratio_max
            add(s.load_condition+'_paired_mechanism',int(passed),1,'1',passed)
        if issues:return unknown('incomplete',';'.join(issues))
    return dict(validity='valid',metrics=measured,constraints=constraints)


def metrics(task,raw,*,check_confirmation=True,check_mechanism=True):
    """Compute every independent measurement before forming one acceptance outcome."""
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    primary=raw
    if 'baseline_cost' in (raw.get('paired_ablation') or {}):
        from extensions.tendon_family.passive_execution import baseline_arm
        primary=baseline_arm(raw)
    physical_issues=[]
    valid,reason=inspect(task,primary,qualification_failures=physical_issues)
    diagnostics=diagnostic_metrics(task,primary,include_mechanism=False)
    measured=[];constraints=[]
    for key,row in diagnostics.items():
        if row.get('value') is None:continue
        name=key.removeprefix('evaluator:');unit=row.get('unit','count')
        measured.append(Metric(name=name,value=float(row['value']),units=unit))
        if row['passed'] is not None:constraints.append(ConstraintResult(name=name,observed=float(row['value']),limit=float(row.get('limit',0)),units=unit,satisfied=row['passed']))
    issues=[] if valid=='valid' else [dict(validity=valid,reason=reason)]
    integrity='complete' if valid=='valid' or physical_issues and reason==';'.join(physical_issues) else 'incomplete' if valid=='incomplete' else 'invalid'
    if physical_issues and valid!='invalid':issues.append(dict(validity='invalid',reason=';'.join(physical_issues)))
    observations={}
    for spec in ev.progressive_stiffness:
        observations[spec.load_condition]=diagnostics.get('evaluator:'+spec.load_condition+'_slack_to_taut',{}).get('observable',{})
    if ev.mechanism and check_mechanism:
        pair=mechanism_metrics(task,raw,primary,observations,baseline_inspection=(valid,reason))
        measured.extend(pair['metrics']);constraints.extend(pair['constraints'])
        by_name={c.name:c for c in pair['constraints']}
        for spec in ev.progressive_stiffness:
            name=spec.load_condition+'_paired_mechanism';c=by_name.get(name)
            diagnostics['evaluator:'+name]=dict(value=c.observed if c else None,limit=1.,unit='1',
                passed=c.satisfied if c else None,missing_reason=None if c else pair.get('reason'),
                source_pointers=['/episodes/'+str(i) for i,e in enumerate(primary.get('episodes',[])) if e['load_condition']==spec.load_condition]+
                    ['/paired_ablation/ablation/episodes/'+str(i) for i,e in enumerate((raw.get('paired_ablation') or {}).get('ablation',{}).get('episodes',[])) if e['load_condition']==spec.load_condition])
        if pair['validity']!='valid':issues.append(dict(validity=pair['validity'],reason=pair.get('reason')))
    if ev.numerical_confirmation and check_confirmation:
        confirmation_valid,confirmation_reason=confirmation(task,raw)
        if confirmation_valid!='valid':issues.append(dict(validity=confirmation_valid,reason=confirmation_reason))
    unknown=[key for key,row in diagnostics.items() if row['value'] is None or row['passed'] is None]
    if not diagnostics:unknown=['source_bound_measurements']
    # Baseline objectives omit only mechanism evidence, never physical task bounds.
    if not check_mechanism:unknown=[key for key in unknown if not key.endswith('_paired_mechanism')]
    if unknown:issues.append(dict(validity='incomplete',reason='MEASUREMENTS_MISSING',constraints=unknown))
    exploration=primary.get('execution_profile',{}).get('purpose')=='exploration' or primary.get('execution_checks',{}).get('level')=='screening'
    failed=any(c.satisfied is False for c in constraints) or any(i['validity']=='invalid' for i in issues)
    status='FAIL' if failed else 'INCOMPLETE' if issues else 'PASS'
    validity='invalid' if any(i['validity']=='invalid' for i in issues) else 'incomplete' if issues or exploration else 'valid'
    return dict(validity=validity,task_success=all(c.satisfied for c in constraints) if validity=='valid' else None,
        metrics=measured,constraints=constraints,reason=issues[0]['reason'] if issues else None,
        overall_status=status,acceptance_status='not_evaluated' if exploration or not check_confirmation or not check_mechanism else status,
        diagnostics=dict(evidence_integrity=dict(status=integrity,reason=None if integrity=='complete' else reason),
            qualification_status='FAIL' if physical_issues else 'PASS' if integrity=='complete' else 'UNKNOWN',
            observations=diagnostics,qualification=qualification_observations(task,primary),issues=issues))


def confirmation(task,raw):
    """Verify measured independent executions, never a score-grid surrogate."""
    from .passive_program import confirmation_task
    from extensions.tendon_family.passive_execution import baseline_arm
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data);spec=ev.numerical_confirmation
    c=raw.get('numerical_confirmation')
    if not c or c.get('version')!='passive_numerical_confirmation_v1':return 'incomplete','INDEPENDENT_NUMERICAL_CONFIRMATION_REQUIRED'
    try:
        if (c['source_execution_id']==c['independent_execution_id'] or not c['source_result']['artifact_id']
                or c['source_binding']!=raw['physical_binding'] or len(c['source_raw_identity'])!=64):
            return 'invalid','CONFIRMATION_SOURCE_IDENTITY_MISMATCH'
        independent=baseline_arm(raw)
        for variant in ('half_timestep','initial_perturbation'):
            record=c['executions'][variant];effective=confirmation_task(task,variant);other=record['raw']
            if (record['raw_identity']!=digest(other) or record['task']!=effective.model_dump(mode='json')
                    or record['execution_id'] in (c['source_execution_id'],c['independent_execution_id'])
                    or other['physical_binding']['design_identity']!=raw['physical_binding']['design_identity']
                    or other['numerical_invariant_model_signature']!=raw['numerical_invariant_model_signature']
                    or any(other[k]!=raw[k] for k in ('coordinate_order','tendon_order','payout_lengths_m'))
                    or other['unloaded_equilibrium']['equilibrium']['qpos']!=raw['unloaded_equilibrium']['equilibrium']['qpos']):
                return 'invalid','CONFIRMATION_VARIANT_IDENTITY_MISMATCH'
            valid,reason=inspect(effective,other)
            if valid!='valid':return valid,'CONFIRMATION_'+variant+':'+str(reason)
            if other['intervention']['kind']!='none':return 'invalid','CONSTRAINED_NUMERICAL_CONFIRMATION_REQUIRED'
            if metrics(effective,other,check_confirmation=False,check_mechanism=False).get('task_success') is not True:
                return 'invalid','CONFIRMATION_TASK_BOUNDS_FAILED:'+variant
        if c['executions']['half_timestep']['execution_id']==c['executions']['initial_perturbation']['execution_id']:
            return 'invalid','DISTINCT_NUMERICAL_EXECUTIONS_REQUIRED'
        for s in ev.progressive_stiffness:
            base=np.asarray(stiffness(task,independent,s)['displacement_m'])
            source=np.asarray(c['source_displacements_m'][s.load_condition])
            if base.shape!=(3,) or source.shape!=base.shape or not np.isfinite(source).all():return 'invalid','CONFIRMATION_DISPLACEMENTS_MISSING'
            values=[source]+[np.asarray(stiffness(confirmation_task(task,v),c['executions'][v]['raw'],s)['displacement_m'])
                for v in ('half_timestep','initial_perturbation')]
            if any(a.shape!=base.shape or not np.isfinite(a).all() or np.max(abs(a-base))>spec.max_displacement_difference_m for a in values):
                return 'invalid','CROSS_EXECUTION_DISPLACEMENT_DIFFERENCE'
        required={'baseline','ablation','half_timestep','initial_perturbation'}
        if set(c['saved_state_replay'])!=required:return 'incomplete','COMPLETE_SAVED_STATE_REPLAY_SCOPE_REQUIRED'
        arms=dict(baseline=independent,ablation=raw['paired_ablation']['ablation'],
            **{v:c['executions'][v]['raw'] for v in ('half_timestep','initial_perturbation')})
        for name,arm in arms.items():
            replay=c['saved_state_replay'][name]
            if (replay['status']!='verified' or replay['integrations']!=0 or replay['raw_identity']!=digest(arm)
                    or replay['traces']!=arm['trace_files'] or replay['rows_checked']!=arm['physics_steps']
                    or replay['route_checked_poses']!=arm['physics_steps']
                    or replay['maximum_position_difference_m']>1e-10):
                return 'invalid','SAVED_STATE_REPLAY_BINDING_MISMATCH'
    except (KeyError,TypeError,ValueError,IndexError):return 'incomplete','COMPLETE_NUMERICAL_CONFIRMATION_RECORD_REQUIRED'
    return 'valid',None


def summary(task,raw):
    """Bounded L0 stage facts; full arrays and traces remain in L2."""
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);phases=[]
    loads={v['name']:v for v in task.physical_problem['loads']}
    for episode_index,e in enumerate(raw.get('episodes',[])):
        case=e['load_condition'];i=task.physical_problem['monitor_s'].index(loads[case]['material_s'])
        base_stage=goal.programs[case][0];base=stage_rows(goal,e,base_stage.name)
        reference=np.mean([r['material_positions_m'][i] for r in base],axis=0) if base else None
        for stage in goal.programs[case]:
            rows=stage_rows(goal,e,stage.name)
            if not rows:continue
            mean=np.mean([r['material_positions_m'][i] for r in rows],axis=0)
            phases.append(dict(load_condition=case,stage=stage.name,window_s=list(stage.scoring_window_s),material_s=loads[case]['material_s'],
                actual_last_force_world_n=rows[-1]['force_world_n'],mean_material_position_m=mean.tolist(),
                displacement_from_unloaded_tail_mean_m=(mean-reference).tolist() if reference is not None else None,
                maximum_tip_speed_m_s=float(max(np.linalg.norm(r['tip_velocity_m_s']) for r in rows)),
                maximum_tension_n=max(max(r['actual_tension_n']) for r in rows),
                last_constraint_classification=rows[-1]['constraint_classification'],
                qualifications=e.get('qualifications',{}).get(stage.name),
                source_pointer='/episodes/'+str(episode_index),
                scope='Recorded scoring window on its frozen qualification grid where available; failed qualification prevents a mechanism or acceptance claim.'))
    return dict(version='passive_program_summary_v2',initial_state_source=raw.get('initial_state_source'),
        phase_measurements=phases,
        stages=[dict(load_condition=e['load_condition'],complete=e['complete'],qualifications=e.get('qualifications'),
            state_resets=e.get('state_resets'),qualified_state_identity=e.get('qualified_state',{}).get('state_identity'),
            maximum_tension_n=e.get('maximum_tension_n'),maximum_enabled_length_excess_m=e.get('maximum_enabled_length_excess_m'),
            transition_count=len(e.get('constraint_transitions',[]))) for e in raw.get('episodes',[])],
        paired_status=(raw.get('paired_ablation') or {}).get('status'),cost=raw.get('cost'),
        cost_observation_scope=raw.get('cost_observation_scope',raw.get('cost',{}).get('observation_scope','observed_native_counts')),
        unobserved_work_possible=raw.get('unobserved_work_possible',raw.get('cost',{}).get('unobserved_work_possible',False)))
