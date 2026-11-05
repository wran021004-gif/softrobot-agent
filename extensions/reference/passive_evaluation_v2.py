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


def inspect(task,raw,*,intervention=False):
    goal=PassiveResponseGoalV2.model_validate(task.goal.data)
    original=goal.execution_protocol=='phs2d_original_v1'
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
            elif original:
                eq=raw['unloaded_equilibrium']
                if (eq['status']!='qualified_local_minimum' or not eq['equilibrium']['kkt_pass'] or
                        not eq['equilibrium']['second_order_sufficient'] or not eq['equilibrium']['capacity'] or
                        any(eq['solver_settings'].get(k)!=v for k,v in goal.unloaded_static_solver.items()) or
                        initial['qpos_rad']!=eq['equilibrium']['qpos'] or any(initial['qvel_rad_s']) or initial['time_s']!=0):
                    return 'invalid','QUALIFIED_FRESH_UNLOADED_EQUILIBRIUM_REQUIRED'
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
            else:
                named=task.initializer.parameters.data
                expected={key:[named[key].get(j,0.) for j in raw['coordinate_order']] for key in ('qpos_rad','qvel_rad_s')}
                if any(initial[k]!=v for k,v in expected.items()) or initial['time_s']!=0:return 'invalid','FROZEN_NAMED_INITIAL_STATE_MISMATCH'
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
                if not observed['passed']:return 'invalid','DYNAMIC_STAGE_NOT_QUALIFIED:'+rule.stage
            for key,limit in [('maximum_constraint_direction_error',goal.constraint_direction_tolerance),('maximum_force_map_error_nm',goal.force_map_tolerance_nm),('maximum_capacity_ratio',1.)]:
                if not np.isfinite(e[key]) or e[key]>limit:return 'invalid','CONSTRAINT_MAPPING_OR_CAPACITY_INVALID:'+key
            if e['minimum_constraint_multiplier_n'] < -goal.multiplier_sign_tolerance_n:return 'invalid','UNILATERAL_MULTIPLIER_SIGN_INVALID'
            if e['maximum_enabled_length_excess_m']>goal.length_tolerance_m:return 'invalid','ENABLED_TENDON_LENGTH_EXCESS'
            if set(e['stage_extrema'])!={s.name for s in stages} or sum(v['physics_steps'] for v in e['stage_extrema'].values())!=steps:
                return 'incomplete','PER_STEP_STAGE_EXTREMA_MISSING'
            if goal.route_check!='not_required':
                route=e['route_geometry'];expected_poses=(steps if goal.route_check=='every_physics_step' else count)+1
                if route['sampling']!=goal.route_check or route['checked_poses']!=expected_poses:return 'incomplete','ROUTE_POSE_COVERAGE_MISSING'
                if route['status']!='legal_at_checked_poses':return 'invalid','ILLEGAL_TENDON_ROUTE_AT_CHECKED_POSES'
            if goal.recording=='full_physics_csv':
                traces=[v for v in raw['trace_files'] if v['load_condition']==case]
                trace_steps=e['executed_physics_steps'] if original else steps
                if len(traces)!=1 or traces[0]['physics_steps']!=trace_steps or traces[0]['bytes']<=0 or len(traces[0]['sha256'])!=64:
                    return 'incomplete','FULL_PHYSICS_TRACE_MISSING'
        expected_cost=sum(e['executed_physics_steps'] for e in episodes) if original else steps*len(episodes)
        if raw['physics_steps']!=expected_cost:return 'incomplete','PHYSICS_COST_COVERAGE_MISMATCH'
    except (KeyError,TypeError,ValueError,StopIteration,IndexError):return 'incomplete','REQUIRED_V2_MEASUREMENTS_MISSING'
    return 'valid',None


def stage_rows(goal,episode,name):
    """Use the frozen stage qualification grid when it covers the score window."""
    stage=next(s for s in goal.programs[episode['load_condition']] if s.name==name)
    dense=any(q.stage==name and q.sampling=='every_physics_step' and q.window_s[0]<=stage.scoring_window_s[0]
        and q.window_s[1]>=stage.scoring_window_s[1] for q in goal.qualifications)
    return window_rows(episode['qualification_samples'] if dense else episode['samples'],stage.scoring_window_s)


def stiffness(task,raw,spec):
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);case=spec.load_condition
    e=next(e for e in raw['episodes'] if e['load_condition']==case);stages={s.name:s for s in goal.programs[case]}
    tails={name:stage_rows(goal,e,name) for name in stages}
    i=task.physical_problem['monitor_s'].index(spec.material_s);direction=np.asarray(spec.direction_world)
    positions={name:np.array([r['material_positions_m'][i] for r in rows]) for name,rows in tails.items()}
    projected={name:values@direction for name,values in positions.items()}
    base=float(projected[spec.reference_stage].mean());d=np.array([projected[name].mean()-base for name in spec.stages])
    f=np.array([np.asarray(tails[name][-1]['force_world_n'])@direction for name in spec.stages])
    spread=max(float(np.max(np.linalg.norm(v-v.mean(axis=0),axis=1))) for v in positions.values());floor=max(spec.denominator_min_m,spec.denominator_uncertainty_multiplier*spread)
    dd=np.diff(d);df=np.diff(f)
    if np.any(dd<=floor) or np.any(df<=0):return dict(valid=False,reason='UNRESOLVED_STIFFNESS_DENOMINATOR',displacement_m=d.tolist(),uncertainty_m=spread,denominator_floor_m=floor)
    k=df/dd;low=tails[spec.stages[0]];high=tails[spec.stages[-1]]
    # A qualifying tendon must exhibit both ends of the transition itself.
    transitions=[]
    for tendon in range(len(raw['tendon_order'])):
        transitions.append(bool(max(r['actual_tension_n'][tendon] for r in low)<=spec.low_tension_max_n
            and min(r['actual_tension_n'][tendon] for r in high)>=spec.high_tension_min_n
            and max(r['length_residual_m'][tendon] for r in low)<=-spec.low_slack_min_m
            and max(abs(r['length_residual_m'][tendon]) for r in high)<=spec.high_constraint_residual_max_m
            and all(r['constraint_active'][tendon] for r in high)))
    return dict(valid=True,displacement_m=d.tolist(),force_n=f.tolist(),interval_stiffness_n_m=k.tolist(),stiffness_ratio=float(k[1]/k[0]),
        denominator_floor_m=floor,uncertainty_m=spread,slack_to_taut=any(transitions),transition_tendons=[name for name,ok in zip(raw['tendon_order'],transitions) if ok])


def constraint_names(task):
    ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    names={b.name+'_'+side for b in ev.bounds for side in ('minimum','maximum') if getattr(b,side) is not None}
    if ev.prohibit_contact:names.add('no_contact')
    for s in ev.progressive_stiffness:names.update((s.load_condition+'_stiffness_ratio',s.load_condition+'_slack_to_taut'))
    if ev.mechanism:names.update(s.load_condition+'_paired_mechanism' for s in ev.progressive_stiffness)
    return names


def metrics(task,raw):
    from .passive_response import reduce_vector
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);ev=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data)
    pair=raw.get('paired_ablation');primary=raw
    if pair and 'baseline_cost' in pair:
        from extensions.tendon_family.passive_execution import baseline_arm
        primary=baseline_arm(raw)
    valid,reason=inspect(task,primary)
    def unknown(validity,reason):return dict(validity=validity,task_success=None,metrics=[],constraints=[],reason=reason)
    if valid!='valid':return unknown(valid,reason)
    measured=[];constraints=[]
    def add(name,value,limit,unit,satisfied):
        measured.append(Metric(name=name,value=float(value),units=unit))
        constraints.append(ConstraintResult(name=name,observed=float(value),limit=float(limit),units=unit,satisfied=bool(satisfied)))
    for b in ev.bounds:
        e=next(e for e in primary['episodes'] if e['load_condition']==b.load_condition);stages={s.name:s for s in goal.programs[b.load_condition]}
        rows=stage_rows(goal,e,b.window);refs=stage_rows(goal,e,b.reference_window)
        if b.aggregation=='mean_state':
            rows=[{**rows[-1],**{key:np.mean([r[key] for r in rows],axis=0).tolist() for key in ('material_positions_m','tip_m','material_velocities_m_s','tip_velocity_m_s')}}]
        reference=lambda key:np.asarray(refs[-1][key]) if b.reference_reduction=='last' else np.mean([r[key] for r in refs],axis=0)
        i=task.physical_problem['monitor_s'].index(b.material_s);values=[]
        for r in rows:
            delta_point=np.asarray(r['material_positions_m'][i])-reference('material_positions_m')[i];delta_tip=np.asarray(r['tip_m'])-reference('tip_m')
            point=float(np.linalg.norm(np.asarray(b.material_projection_world)@delta_point)) if b.material_projection_world is not None else reduce_vector(b,delta_point)
            tip=float(np.linalg.norm(np.asarray(b.tip_projection_world)@delta_tip)) if b.tip_projection_world is not None else reduce_vector(b,delta_tip)
            if b.quantity=='displacement_ratio' and max(point,b.denominator_floor_m)==0:return unknown('invalid','ZERO_DISPLACEMENT_RATIO_DENOMINATOR')
            value={'material_displacement':lambda:point,'tip_displacement':lambda:tip,'displacement_ratio':lambda:tip/max(point,b.denominator_floor_m),
                'displacement_difference':lambda:tip-b.material_scale*point,'maximum_tension':lambda:max(r['actual_tension_n']),
                'maximum_length_excess':lambda:max([0.]+r['length_residual_m']),'material_speed':lambda:reduce_vector(b,np.asarray(r['material_velocities_m_s'][i])),
                'tip_speed':lambda:reduce_vector(b,np.asarray(r['tip_velocity_m_s'])),'unloaded_tip_drift':lambda:tip,
                'maximum_joint_position':lambda:max(abs(v) for v in r['qpos_rad']),'maximum_joint_speed':lambda:max(abs(v) for v in r['qvel_rad_s'])}[b.quantity]()
            values.append(value)
        if b.aggregation=='mean':values=[float(np.mean(values))]
        elif b.aggregation=='last':values=values[-1:]
        elif b.quantity in ('maximum_tension','maximum_length_excess','maximum_joint_position','maximum_joint_speed'):
            values.append(e['stage_extrema'][b.window]['scoring'][b.quantity])
        if not np.isfinite(values).all():return unknown('invalid','NONFINITE_DYNAMIC_METRIC')
        if b.minimum is not None:add(b.name+'_minimum',min(values),b.minimum,b.physical_unit,min(values)>=b.minimum)
        if b.maximum is not None:add(b.name+'_maximum',max(values),b.maximum,b.physical_unit,max(values)<=b.maximum)
    if ev.prohibit_contact:
        contacts=max(e['maximum_contacts'] for e in primary['episodes']);add('no_contact',contacts,0,'count',contacts==0)
    observations={}
    for s in ev.progressive_stiffness:
        value=stiffness(task,primary,s);observations[s.load_condition]=value
        if not value['valid']:return unknown('invalid',value['reason'])
        add(s.load_condition+'_stiffness_ratio',value['stiffness_ratio'],s.stiffness_ratio_min,'1',value['stiffness_ratio']>=s.stiffness_ratio_min)
        add(s.load_condition+'_slack_to_taut',int(value['slack_to_taut']),1,'1',value['slack_to_taut'])
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
        for s in ev.progressive_stiffness:
            base=observations[s.load_condition];other_value=stiffness(task,other,s)
            if not other_value['valid']:return unknown('invalid','ABLATION_UNRESOLVED_STIFFNESS_DENOMINATOR')
            if base['displacement_m'][-1]<=base['denominator_floor_m']:return unknown('invalid','UNRESOLVED_MECHANISM_DENOMINATOR')
            high=other_value['displacement_m'][-1]/base['displacement_m'][-1]
            late=other_value['interval_stiffness_n_m'][-1]/base['interval_stiffness_n_m'][-1]
            passed=high>=ev.mechanism.high_displacement_increase_min or late<=ev.mechanism.late_stiffness_ratio_max
            add(s.load_condition+'_paired_mechanism',int(passed),1,'1',passed)
    return dict(validity='valid',task_success=all(c.satisfied for c in constraints),metrics=measured,constraints=constraints)


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
