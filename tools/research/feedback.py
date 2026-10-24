"""Program facts about evidence identity, ownership, cost and legal references."""
from copy import deepcopy
import json
import math
import tarfile
from tools.platform_store import plain
from tools.state_io import digest


def execution_evidence(result):
    """Expose recorded numerical validity separately from physical task outcome."""
    acceptance=result.get('acceptance') or {}
    profile=result.get('profile') or {}
    execution=result.get('execution') or {}
    return dict(configured_termination_conditions=(acceptance.get('timing') or {}).get('termination'),
        configured_termination_is_observed_reason=False,
        actual_termination=dict(solver_status=profile.get('solver_status'),complete=profile.get('complete'),
            reason=execution.get('failure_reason') or profile.get('execution_failure_reason')),
        numerical_validity=dict(acceptance_status=acceptance.get('status'),
        execution_status=result.get('status'),failure_stage=execution.get('stage'),
        failure_reason=execution.get('failure_reason') or profile.get('execution_failure_reason'),
        components={k:v for k,v in acceptance.get('components',{}).items() if k in
            ('evaluation_validity','execution_complete','holding_coverage','solver_errors','force_bounds')},
        missing=acceptance.get('missing'),issues=acceptance.get('issues'),
        evaluation_validity=profile.get('evaluation_validity'),
        valid_complete_execution=profile.get('valid_complete_execution'),
        last_valid_time_s=profile.get('last_valid_time_s'),boundary=execution.get('boundary'),
        source_pointers=['/acceptance','/profile','/execution']),
        solver_outcome={k:profile.get(k) for k in ('solver_status','execution_failure_reason',
            'optimization_status_counts','raw_termination_counts','policy_stop_reason_counts',
            'solver_error_count','solver_failure_flags','unusable_plans','maximum_plan_violation')})


def task_gap(result):
    """Rank recorded physical metrics only; original acceptance owns validity."""
    acceptance=result.get('acceptance') or {}
    if 'independent_evaluation_executed' in result:
        episodes=result.get('episodes',[])
        pairs=(('terminal_position_error_m','terminal_position_limit_m'),
            ('holding_max_position_error_m','position_limit_m'),('holding_max_speed_m_s','holding_speed_limit_m_s'))
        gaps={key:max(0.,max(e[key] for e in episodes)/acceptance[limit]-1)
            for key,limit in pairs if episodes and all(e.get(key) is not None for e in episodes) and acceptance.get(limit,0)>0}
        return dict(normalized_gap=max(gaps.values()) if len(gaps)==3 else None,components=gaps,
            valid_complete=bool(result['independent_evaluation_executed'] and episodes and all(
                e['complete'] and e.get('holding_coverage_complete') and not e.get('numerical_failure') for e in episodes)),
            accepted=bool(result.get('passed')),interpretation='Research ranking only; original independent acceptance unchanged')
    components=acceptance.get('components',{})
    tracking=acceptance.get('task_family')=='task.tracking'
    scored=(('evaluator:tracking_max_error','evaluator:path_coverage','evaluator:path_start',
        'evaluator:path_end','evaluator:path_progress_regression') if tracking else
        ('evaluator:task_bound','holding_position','holding_speed'))
    ratios={name:max(0.,row['value']/row['limit']-1) for name,row in components.items()
        if name in scored
        and isinstance(row.get('value'),(float,int)) and math.isfinite(row['value']) and row.get('limit',0)>0}
    valid=bool(result.get('status')=='evaluated' and all(components.get(k,{}).get('passed') is True
        for k in ('evaluation_validity','execution_complete','tracking_sampling' if tracking else 'holding_coverage','solver_errors','force_bounds')))
    return dict(normalized_gap=max(ratios.values()) if len(ratios)==len(scored) else None,
        components=ratios,valid_complete=valid,accepted=bool(acceptance.get('accepted')),
        interpretation='Research ranking only; invalid executions remain invalid regardless of gap')


def search_feedback(host, reference):
    """Exact evidence links and a generate recipe, without new scientific work."""
    from tools.research.state import state
    from tools.research.design import final_generation_request
    result=host.store.artifact(reference)['result']
    best=result.get('best_mathematical_candidate') or {}
    candidate=best.get('evidence',{}).get('candidate')
    materialization=None
    if candidate:
        value=host.store.artifact(candidate)
        request=final_generation_request(state(host)['spec'],value)
        if request:
            materialization=dict(action='generate',generation=request,
                supporting_evidence=[reference,candidate],source_candidate=candidate,
                physical_design_identity=value.get('physical_design_identity'),
                note='Copy exact physical choices; cite source search/candidate and evidence actually used in the new plan. Screening evidence is not transferred to the new candidate.')
    return dict(reference=reference,status=result['status'],best_candidate=candidate,
        proxy_values=best.get('proxy_values'),final_materialization=materialization,
        lineage_pointer='/result/evaluated',task_acceptance='unmeasured')


def solution_identity(host, result, candidate):
    """Identify effective science and policy bytes, independent of artifact locations."""
    science = deepcopy(result.get('scientific_configuration', candidate['scientific_configuration']))
    design = science['robot']['structure']['data']
    design.pop('metadata', None)  # Contract declares descriptive data, never physics.
    design.pop('id', None)
    # Generator inputs/provenance are not a change to the resolved physical model.
    science['policy'].pop('candidate_builder', None)
    rl = 'run_id' in result and 'independent_evaluation_executed' in result
    if rl:
        configuration = host.store.artifact(result['configuration'])
        for key in ('controller', 'dynamics_model', 'discretization'):
            science['policy'].pop(key, None)  # RL executes the compiled MuJoCo model below.
        effective = {k: deepcopy(configuration[k]) for k in
            ('mode', 'seed', 'observation', 'action', 'control_object', 'task')}
        effective['candidate'] = {k: deepcopy(configuration['candidate'][k]) for k in ('xml', 'assets')}
        reference = configuration.get('reference')
        effective['reference'] = {k: reference[k] for k in
            ('sha256', 'tendon_order', 'control_period_s')} if reference else None
        policy_sha = result.get('policy_sha256')
        # An invalid attempt may never load weights; retain its frozen selection binding.
        if not policy_sha and result.get('role') == 'confirmation' and result.get('selected_execution'):
            policy_sha = host.store.artifact(result['selected_execution']).get('policy_sha256')
        controller = dict(route='rl', configuration=effective, policy_sha256=policy_sha)
    elif result.get('source_reference'):
        source=host.store.artifact(result['source_reference'])
        from tools.research.physical_replay import binding
        binding(candidate['configuration'],source['trajectory'])
        controller=dict(route='fixed_tension',source=result['source_reference'],
            sequence=source['trajectory'])
    else:
        from extensions.tendon_family.contracts import GVSTrajectoryParameters
        controller_configuration = science['policy']['controller']
        recipe = controller_configuration['parameters']['data']['recipe']
        recipe = plain(GVSTrajectoryParameters.model_validate(recipe))
        if recipe['stopping_policy'] == 'research_work_v1':
            recipe.update(max_cpu_s=None, feasible_return=None)
        controller_configuration['parameters']['data']['recipe'] = recipe
        controller = dict(route='nmpc', configuration=controller_configuration)
    return dict(scientific_configuration=science, controller=controller)


def experiment_identity(candidate, route, *, source=None, result=None, environment=None,
                        rl_configuration=None, policy_sha=None):
    """Effective experiment fields, excluding Store references and study labels."""
    def canonical(value):
        # Fingerprints only: discard machine-roundoff packaging, never alter
        # candidate bytes, solver inputs, ordered commands or task acceptance.
        if isinstance(value,float):return float(format(value,'.12g')) or 0.0
        if isinstance(value,dict):return {key:canonical(item) for key,item in value.items()}
        if isinstance(value,list):return [canonical(item) for item in value]
        return value
    from schemas.platform import SessionInput
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    science=deepcopy(candidate['scientific_configuration'])
    design=science['robot']['structure']['data']
    design.pop('id',None)
    design.pop('metadata',None)
    policy=science['policy']
    inp=SessionInput.model_validate(candidate['configuration'])
    physics=physics_for(inp)
    scene=assemble(inp,physics)
    # Compile canonical source numbers for the fingerprint, so cancellation in
    # derived inertia tensors cannot turn one-ULP input aliases into new science.
    # The actual scene above still validates the exact original binding.
    effective=physics_for(SessionInput.model_validate(canonical(candidate['configuration'])))
    for key in ('identity','source_identity','design_identity'):
        effective.pop(key,None)
    if scene['control']['tension_execution_mode']=='ideal_tension':
        # Direct tendon forces bypass motor kinematics and the length servo.
        design.pop('actuators',None)
        for tendon in design['tendons']:
            tendon.pop('length_servo_gain_n_m',None)
        for key in ('actuators','transmission'):
            effective.pop(key,None)
        for tendon in effective['tendons']:
            tendon.pop('kp_n_m',None)
    physical_scene={key:scene[key] for key in ('initial','qpos_rad','qvel_rad_s',
        'mount_rotation','mount_position','gravity','floor_z_m','floor_id','forces',
        'duration_s','timestep_s','control_period_s','sample_period_s','observation_phase')}
    physical_scene['tension_execution_mode']=scene['control']['tension_execution_mode']
    physical=dict(robot=science['robot'],backend=policy['backend'],
        discretization=policy['discretization'],compiled_physics_identity=digest(canonical(effective)),
        compiled_scene_identity=digest(canonical(physical_scene)))
    task=dict(task=science['task'],seed=science['seed'])
    if route=='rl':
        config=rl_configuration or {}
        required=('mode','seed','observation','action','control_object','task','reward','reference','candidate')
        missing=['rl_configuration.'+key for key in required if key not in config]
        reference=config.get('reference')
        action=dict(mode=config.get('mode'),observation=config.get('observation'),
            action=config.get('action'),control_object=config.get('control_object'),
            task=config.get('task'),reward=config.get('reward'),
            reference={k:reference.get(k) for k in
                ('sha256','candidate_identity','task_identity','tendon_order','control_period_s')} if reference else None,
            compiled_candidate_sha256=(config.get('candidate') or {}).get('sha256'),
            policy_sha256=policy_sha or (result or {}).get('policy_sha256'),
            evaluation=dict(deterministic=True,episodes=1))
        if not action['policy_sha256']:
            missing.append('action.policy_sha256')
        controller=dict(route=route,mode=config.get('mode'))
        runtime=dict(profile_identity=candidate.get('profile_identity'),
            inference_device=(config.get('ppo') or {}).get('device'))
    elif route=='fixed_tension':
        trajectory=(source or {}).get('trajectory') or {}
        required=('tensions_n','times_s','tendon_order','model_identity','design_identity','task_identity')
        action={key:trajectory[key] for key in ('tensions_n','times_s','tendon_order') if key in trajectory}
        missing=[key for key in required if key not in trajectory]
        controller=dict(route=route,command_semantics='ideal_tension')
        runtime=dict(profile_identity=candidate.get('profile_identity'),
            source_provenance={key:trajectory.get(key) for key in ('model_identity','design_identity','task_identity')})
    else:
        action=None
        missing=[]
        controller=dict(route=route,parameters=policy['controller'],
            mathematical_model=policy['dynamics_model'])
        runtime=dict(profile_identity=candidate.get('profile_identity'),
            numerical_environment=environment if environment is not None else (result or {}).get('numerical_environment'))
        if runtime['numerical_environment'] is None:
            missing.append('runtime.numerical_environment')
    if runtime['profile_identity'] is None:
        missing.append('runtime.profile_identity')
    return canonical(dict(identity_version='effective_experiment_v3',identity_precision_significant_digits=12,
        physical=physical,task=task,controller=controller,action=action,
        runtime=runtime,missing_effective_fields=missing))


def compare_experiments(proposed, previous):
    fields=('physical','task','controller','action','runtime')
    equal=[key for key in fields if proposed[key]==previous[key]]
    different=[key for key in fields if key not in equal]
    def paths(a,b,prefix):
        if a==b:
            return []
        if isinstance(a,dict) and isinstance(b,dict):
            return [path for key in sorted(a.keys()|b.keys())
                for path in paths(a.get(key),b.get(key),prefix+'.'+key)]
        if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
            return [path for i,(left,right) in enumerate(zip(a,b))
                for path in paths(left,right,prefix+'['+str(i)+']')]
        return [prefix]
    different_paths=[path for key in different
        for path in paths(proposed[key],previous[key],key)]
    missing=sorted(set(proposed['missing_effective_fields']+previous['missing_effective_fields']))
    if proposed.get('identity_version','legacy_v1')!=previous.get('identity_version','legacy_v1'):
        missing.append('identity_version')
        relation='unresolved_comparison'
    elif missing and not any(key in different for key in ('physical','task','controller','action')):
        relation='unresolved_comparison'
    elif all(key in equal for key in ('physical','task','controller','action')) and 'runtime' in different:
        relation='unresolved_comparison'
    elif not different:
        relation='equivalent_repeat'
    elif proposed['physical']==previous['physical'] and proposed['task']==previous['task']:
        relation='same_robot_different_control'
    elif proposed['controller']==previous['controller'] and proposed['task']==previous['task']:
        relation='same_controller_different_robot'
    elif proposed['task']['seed']!=previous['task']['seed'] and proposed['task']['task']==previous['task']['task']:
        relation='different_seed'
    else:
        relation='different_intervention'
    return dict(relation=relation,equal_fields=equal,different_fields=different,
        different_paths=different_paths,
        missing_effective_fields=missing)


def experiment_preflight(host, candidate_ref, route, *, source_ref=None, repeat=False,
                         rl_configuration=None, policy_sha=None):
    """Compare current proposal with sealed studies before any reservation."""
    from tools.research.state import ROOT, state
    candidate=host.store.artifact(candidate_ref)
    source=host.store.artifact(source_ref) if source_ref else None
    s=state(host)
    proposed=experiment_identity(candidate,route,source=source,
        environment=s['spec'].get('numerical_environment') if route=='nmpc' else None,
        rl_configuration=rl_configuration,policy_sha=policy_sha)
    matches=[]
    def consider(previous, ref, outcome, study):
        comparison=compare_experiments(proposed,previous)
        if comparison['relation'] in ('equivalent_repeat','unresolved_comparison'):
            matches.append(dict(study=study,reference=ref,previous_identity_sha256=digest(previous),
                outcome=outcome,**comparison))
    for ref in s.get('historical_experiments',[]):
        imported=host.store.artifact(ref)
        if imported['route']==route:
            consider(imported['identity'],imported['evaluation'],imported['outcome'],imported['study'])
    for ref in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]:
        row=host.store.artifact(ref)
        prior_route='rl' if row.get('independent_evaluation_executed') is not None else 'fixed_tension' if row.get('source_reference') else 'nmpc'
        if prior_route!=route:
            continue
        prior_candidate=host.store.artifact(row['candidate'])
        prior_source=host.store.artifact(row['source_reference']) if prior_route=='fixed_tension' else None
        prior_config=host.store.artifact(row['configuration']) if route=='rl' else None
        previous=experiment_identity(prior_candidate,route,source=prior_source,result=row,
            rl_configuration=prior_config)
        consider(previous,ref,(row.get('acceptance') or {}).get('status'),host.run_id)
    for summary_path in (ROOT/'evidence').glob('*/summary.json'):
        archive=summary_path.parent/'study/immutable_artifacts.tar.gz'
        if not archive.exists():
            continue
        summary=json.loads(summary_path.read_text(encoding='utf-8'))
        if route=='rl' and isinstance(summary.get('routes'),list) and isinstance(summary.get('candidate'),dict):
            try:
                with tarfile.open(archive,'r:gz') as bundle:
                    def artifact(ref):
                        return json.load(bundle.extractfile('artifacts/'+ref['artifact_id']+'.json'))
                    prior_candidate=artifact(summary['candidate'])
                    for item in summary['routes']:
                        row=item.get('evaluation_facts') or {}
                        if not row.get('independent_evaluation_executed') or not row.get('configuration'):
                            continue
                        previous=experiment_identity(prior_candidate,'rl',result=row,
                            rl_configuration=artifact(row['configuration']))
                        consider(previous,item['evaluation'],row.get('failure_reason'),summary_path.parent.name)
            except (KeyError,TypeError,tarfile.TarError):
                pass
            continue
        if route=='rl':
            continue
        if not isinstance(summary.get('candidate'),dict) or not isinstance(summary.get('result'),dict):
            continue
        stage_route='fixed_tension' if summary.get('source') else 'nmpc'
        if stage_route!=route:
            continue
        try:
            with tarfile.open(archive,'r:gz') as bundle:
                def artifact(ref):
                    return json.load(bundle.extractfile('artifacts/'+ref['artifact_id']+'.json'))
                prior_candidate=artifact(summary['candidate'])
                row=artifact(summary['result'])
                if route=='fixed_tension' and row.get('physical_launches')!=1:
                    continue
                if route=='nmpc' and 'execution' not in row:
                    continue
                prior_source=artifact(row['source_reference']) if route=='fixed_tension' else None
        except (KeyError,TypeError,tarfile.TarError):
            continue
        previous=experiment_identity(prior_candidate,route,source=prior_source,result=row)
        consider(previous,summary['result'],(row.get('acceptance') or {}).get('status'),summary_path.parent.name)
    repeats=[m for m in matches if m['relation'] in ('equivalent_repeat','unresolved_comparison')]
    return dict(proposed_identity=proposed,proposed_identity_sha256=digest(proposed),
        matches=matches,new_evidence_expected=not bool(repeats),
        authorized_as_repeat=bool(repeat),
        admitted=bool(repeat or not repeats))


def import_experiment(host, folder, reference, route):
    """Register verified sealed science once; never add a fresh evaluation."""
    from tools.research.numerics import archived
    from tools.research.state import save, state, update
    row=archived(folder,reference)
    candidate=archived(folder,row['candidate'])
    source=archived(folder,row['source_reference']) if route=='fixed_tension' else None
    configuration=archived(folder,row['configuration']) if route=='rl' else None
    for ref,value in ((row['candidate'],candidate),(reference,row)):
        if save(host,value,'historical_experiment_bytes')!=ref:
            raise ValueError('HISTORICAL_EXPERIMENT_IDENTITY_MISMATCH')
    identity=experiment_identity(candidate,route,source=source,result=row,rl_configuration=configuration)
    imported=save(host,dict(route=route,identity=identity,evaluation=plain(reference),
        study=row.get('owning_study') or row.get('study') or row.get('evaluation_owner'),
        outcome=row.get('acceptance') or dict(passed=row.get('passed')),
        source_folder=str(folder),imported_historical_evidence=True,
        ownership='sealed historical evidence; no fresh execution or charged allocation'),
        'historical_experiment_identity')
    current=state(host)
    update(host,historical_experiments=list({r['artifact_id']:r for r in
        [*current.get('historical_experiments',[]),imported]}.values()))
    return imported


def confirmation_progress(host, selected=None):
    """Retain all solution failures; only current-study launches satisfy fresh repetitions."""
    from tools.research.state import state, confirmation_count
    s=state(host)
    selected=plain(selected or s.get('selected'))
    rows={}
    chosen=result_view(host,selected) if selected else None
    for historical, refs in ((True,[*s.get('historical_confirmations',[]), *s.get('linked_selections',[]), *s.get('scoped_context',[])]),
                             (False,[*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])])):
        for ref in refs:
            r=host.store.artifact(ref)
            if not isinstance(r,dict) or r.get('role')!='confirmation':
                continue
            v=result_view(host,ref)
            if not chosen or v['solution_identity']!=chosen['solution_identity']:
                continue
            owner=r.get('evaluation_owner') or r.get('study') or r.get('owning_study')
            is_historical=historical or not v['fresh_current_study']
            execution=(owner, r.get('execution_id') or r.get('operation_key') or ref['artifact_id'])
            previous=rows.get(execution)
            if previous:
                # A second reference to a launch cannot hide incomplete/failing evidence.
                previous['complete'] &= v['complete']
                previous['passed'] &= v['passed']
                previous['historical'] |= is_historical
            else:
                rows[execution]=dict(reference=ref,historical=is_historical,
                    owner=owner,complete=v['complete'],passed=v['passed'])
    values=list(rows.values())
    required=confirmation_count(s)
    fresh=[v for v in values if not v['historical']]
    return dict(required_total=required,historical_confirmations=sum(v['historical'] for v in values),
        current_study_confirmations=sum(not v['historical'] for v in values),
        remaining=max(0,required-len(fresh)),failures=sum(v['complete'] and not v['passed'] for v in values),
        invalid_executions=sum(not v['complete'] for v in values),executions=values,
        confirmed=bool(required>0 and chosen and chosen['fresh_current_study'] and chosen['passed'] and len(fresh)==required
            and all(v['complete'] and v['passed'] for v in values)),
        correct_operation=dict(tool='research_plan',action='select' if required==0 else 'confirm',selected_execution=selected))


def result_view(host, reference):
    """Organize original evidence once, without recomputing task metrics."""
    from tools.research.state import state
    from tools.research.design import full_science
    r=host.store.artifact(reference)
    c=host.store.artifact(r['candidate'])
    # Historical reads stay valid after the active profile/selection changes.
    if c['scientific_configuration']!=full_science(c['configuration']):
        raise ValueError('IMPORTED_CONFIGURATION_IDENTITY_MISMATCH')
    rl='run_id' in r and 'independent_evaluation_executed' in r
    episodes=r.get('episodes',[]) if rl else []
    complete=bool(r.get('independent_evaluation_executed') and episodes and all(e['complete'] for e in episodes)) if rl else r.get('status')=='evaluated'
    passed=bool(complete and (r.get('passed') if rl else (r.get('acceptance') or {}).get('accepted')))
    controller=dict(route='rl',configuration=r['configuration'],checkpoint=r.get('checkpoint'),policy_sha256=r.get('policy_sha256')) if rl else dict(route='fixed_tension',source=r['source_reference']) if r.get('source_reference') else dict(route='nmpc',configuration=c['scientific_configuration']['policy']['controller'])
    identity=solution_identity(host,r,c)
    owner=r.get('evaluation_owner') or r.get('study') or r.get('owning_study')
    s=state(host)
    current_refs=[*s.get('results',[]),*s.get('rl_evaluations',[]),*s.get('physical_replays',[])]
    from tools.research.design import final_fidelity_matches
    fidelity_ok=final_fidelity_matches(s['spec'],c)
    if s['spec'].get('fidelity_policy') and not rl:
        fidelity_ok &= r.get('scientific_configuration')==c['scientific_configuration'] and r.get('profile_identity')==s['profile']['identity']
    passed &= fidelity_ok
    fresh=bool(plain(reference) in current_refs and plain(reference) not in s.get('historical_confirmations',[])
        and plain(reference) not in s.get('linked_selections',[]) and owner==host.run_id and not r.get('imported_historical_evidence')
        and r.get('fresh_execution',True) and not r.get('cached_operation_receipt'))
    metrics=episodes if rl else (r.get('acceptance') or {}).get('metrics')
    failed_metrics=[]
    acceptance=r.get('acceptance') or {}
    if not rl:
        from tools.research_tasks import task_adapter
        profile=r.get('profile') or {}
        motion=host.store.artifact(profile['motion']) if profile.get('motion') else []
        duration=c['configuration']['task']['timing']['duration_s']
        holding_start=(task_adapter(c['configuration']).holding_start_s() if
            {'holding_position','holding_speed'} & acceptance.get('components',{}).keys() else None)
        for name,component in acceptance.get('components',{}).items():
            if component.get('passed') is not False:
                continue
            key={'holding_speed':'tip_speed_m_s','holding_position':'tip_error_m','evaluator:task_bound':'tip_error_m'}.get(name)
            samples=[(i,v) for i,v in enumerate(motion) if key and key in v and
                (name not in ('holding_speed','holding_position') or
                 holding_start-1e-12<=v['time_s']<=duration+1e-12)]
            if name=='evaluator:task_bound':
                samples=[(i,v) for i,v in samples if abs(v['time_s']-duration)<=1e-8]
            index,worst=max(samples,key=lambda item:item[1][key]) if samples else (None,{})
            failed_metrics.append(dict(metric=name,value=component.get('value'),threshold=component.get('limit'),unit=component.get('unit'),
                time_s=worst.get('time_s'),sample_value=worst.get(key),
                component_pointer='/acceptance/components/'+name,
                sample_evidence=profile.get('motion'),sample_pointer=None if index is None else '/'+str(index)))
    for episode in episodes:
        for metric,limit in (('terminal_position_error_m','terminal_position_limit_m'),('holding_max_position_error_m','position_limit_m'),('holding_max_speed_m_s','holding_speed_limit_m_s')):
            if episode.get(metric) is not None and acceptance.get(limit) is not None and episode[metric]>acceptance[limit]:
                failed_metrics.append(dict(metric=metric,value=episode[metric],threshold=acceptance[limit],time_s='not recorded in evaluation summary'))
    return dict(failed_metrics=failed_metrics,task_gap=task_gap(r),**execution_evidence(r),
        execution_timing=acceptance.get('timing'),failure_state_analysis=mathematical_context(host,r['candidate']),
        evaluation_evidence=dict(trajectory=r.get('trajectory') or (r.get('profile') or {}).get('motion'),reference=plain(reference)),candidate=r['candidate'],task=r.get('task',c['configuration']['task']),controller_route=controller['route'],controller=controller,
        mathematical_provenance=mechanics_context(host,r['candidate']),mathematical_evidence=mathematical_context(host,r['candidate']),metrics=metrics,complete=complete,passed=passed,
        task_performance='provisional' if complete and not fidelity_ok else 'passed' if passed else 'failed' if complete else 'unmeasured',
        failure_stage=r.get('failure_stage') or ('task criteria unmet' if complete and not passed else r.get('failure_reason')),
        costs=dict(evaluation_elapsed_s=r.get('evaluation_elapsed_s'),numerical_s=r.get('numerical_s'),counts=r.get('counts')),
        evidence=plain(reference),role=r.get('role','development'),selected_execution=r.get('selected_execution'),
        fresh_current_study=fresh,solution_identity=identity,solution_identity_sha256=digest(identity))


def eligibility(host, reference, *, revise_selection=False, selection=None, root_operation=True):
    from tools.research.state import state,capacity
    from tools.research.design import verify_candidate
    from tools.research.rl import evaluation_capacity
    s=state(host)
    selection=(s['spec']['confirmation']['fresh_independent_repetitions']==0) if selection is None else selection
    ref=plain(reference)
    reasons=[]
    refs=[*s['results'],*s.get('rl_evaluations',[]),*s.get('physical_replays',[]),*s.get('linked_selections',[])]
    if ref not in refs:
        return dict(eligible=False,reasons=['not a current-study controller result'],required_field='selected_execution')
    r=host.store.artifact(ref)
    count=0
    progress=None
    fit=None
    try:
        v=result_view(host,ref)
        if ref not in s.get('evaluation_reads',[]):
            reasons.append('explicit evidence_read of this completed evaluation required before selection or confirmation')
        if not v['fresh_current_study']:
            reasons.append('historical or imported result is not fresh development evidence')
        if r.get('role','development')=='confirmation':
            reasons.append('selection requires a passing development evaluation')
        if not v['passed']:
            reasons.append('result did not pass complete original task evaluation')
        c=verify_candidate(host,r['candidate'])
        if v['controller_route']=='nmpc' and (r.get('profile_identity')!=s['profile']['identity'] or r['scientific_configuration']!=c['scientific_configuration']):
            reasons.append('selected scientific configuration mismatch')
        if v['controller_route']=='rl' and (not r.get('checkpoint') or not r.get('policy_sha256')):
            reasons.append('exact evaluated checkpoint identity missing')
        if s.get('selected') and s['selected']!=ref:
            old=confirmation_progress(host,s['selected'])
            if not revise_selection:
                reasons.append('confirmation selection already frozen; explicit revise_selection required')
            if not (old['failures'] or old['invalid_executions']):
                reasons.append('selection remains immutable during its confirmation attempt')
            if result_view(host,s['selected'])['solution_identity']==v['solution_identity']:
                reasons.append('revision requires a scientifically changed solution; relabeling cannot erase failure')
        elif revise_selection:
            reasons.append('revision requires a different failed selection')
        progress=confirmation_progress(host,ref)
        count=progress['required_total']-progress['remaining']
        required=progress['required_total']
        if progress['failures'] or progress['invalid_executions']:
            reasons.append('confirmation failed or invalid for this scientific solution; inspect evidence, no automatic retry')
        if not selection and count>=required:
            reasons.append('declared confirmations already recorded')
        if revise_selection and count:
            reasons.append('revised solution already has a confirmation attempt; allowance cannot restart')
        remaining=required if revise_selection else required-count
        fit=dict(admitted=remaining,selection_without_execution=True) if selection else evaluation_capacity(host,remaining,confirmation=True) if v['controller_route']=='rl' else capacity(host,remaining,True,root_operation=root_operation if v['controller_route']=='fixed_tension' else True,candidate=r['candidate'],route=v['controller_route'])
        if selection and required==0 and progress['current_study_confirmations']:
            reasons.append('unexpected extra confirmations in zero-repetition study')
        if fit['admitted']<remaining:
            reasons.append('remaining required confirmations do not fit route budget')
    except (ValueError,KeyError) as exc:
        reasons.append(str(exc))
        count=0
    if s['research_status']=='stopped':
        reasons.append('study sealed after STOP')
    if s.get('selected') and confirmation_progress(host)['confirmed']:
        reasons.append('solution confirmed; close study')
    return dict(eligible=not reasons,reasons=reasons,required_field='selected_execution',selected_execution=ref,
        owning_study=r.get('study',r.get('owning_study')),historical_input=ref in s.get('linked_selections',[]),
        completed_confirmations=count,progress=progress,confirmation_reservation=fit)


def facts(host):
    from tools.research.state import state
    s = state(host)
    if s['spec'].get('mode')=='rl_interface':
        from tools.rl.run import failure_diagnosis
        return dict(owning_study=host.run_id,rl_runs=s.get('rl_runs',{}),rl_evaluations=s.get('rl_evaluations',[]),
            numerical_failure_categories={run_id:failure_diagnosis(host.store.root/'rl'/run_id)
                for run_id in s.get('rl_runs',{}) if (host.store.root/'rl'/run_id).exists()},
            available_controller_routes=['direct','residual'],
            frozen_task=s.get('rl_task'),closeout='Explicit evaluation evidence read and cited next-step decision; no second trial')
    progress=confirmation_progress(host)
    options=[*s['results'],*s.get('rl_evaluations',[]),*s.get('physical_replays',[]),*s.get('linked_selections',[])]
    return dict(owning_study=host.run_id,
        physical_replays=[dict(reference=r,candidate=host.store.artifact(r).get('candidate'),
            acceptance=host.store.artifact(r).get('acceptance')) for r in s.get('physical_replays',[])],
        identity_rules=dict(candidate='immutable full configuration; may be shared by identical constructions',
            execution='fresh independent launch with separate execution_id and owner_run_id',
            historical='imported evidence has its original ownership and previous cost; no new execution',
            receipt='reusing an operation ID returns a cached receipt; additional execution cost is zero',
            role='origin, role and phase are metadata, not scientific configuration changes',
            solution='effective scientific configuration and policy content; artifact labels and checkpoint paths excluded'),
        confirmation_progress=progress,selection_history=s.get('selection_history',[]),
        confirmation_options=[dict(execution_reference=r, **eligibility(host,r)) for r in options],
        revision_options=[dict(execution_reference=r,revise_selection=True,**eligibility(host,r,revise_selection=True))
            for r in options if r!=s.get('selected')] if s.get('selected') and (progress['failures'] or progress['invalid_executions']) else [],
        confirmation_reference_shape={'selected_execution':{'artifact_id':'exact passing result artifact_id','media_type':'application/json'}})


def cached(output):
    """Keep saved facts intact while describing the additional cost of this call."""
    return dict(output, operation_reuse=dict(cached_operation_receipt=True,
        additional_numerical_s=0., additional_scientific_executions=0,
        prior_result_costs='retained in saved result numerical_s; not newly incurred by receipt retrieval'))


def mechanics_context(host,candidate):
    from tools.research.state import state
    return [dict(reference=ref,operation=value.get('operation'),task_acceptance='unmeasured',physical_validation=value.get('physical_validation'))
        for ref in state(host).get('mechanics_results',[]) if (value:=host.store.artifact(ref)).get('design_candidate')==plain(candidate)]


def mathematical_context(host,candidate):
    """Exact candidate links to calculated evidence; no recomputation or interpretation."""
    from tools.research.state import state
    records=[]
    for ref in state(host).get('analysis_results',[]):
        value=host.store.artifact(ref)
        if value['candidate']!=plain(candidate):
            continue
        records.append(dict(reference=ref,**{k:value.get(k) for k in
            ('operation','origin','status','operating_point','proxy_values','local_model_constraints','charged_numerical_s')}))
    return records


def compact_local(row):
    keys=('execution_id','historical_input','source_update_id','first_input_n','original_applied_action_n',
          'exact_initialized_vector_equal','exact_bounds_equal','charged_numerical_s','diagnostic_trace_enabled')
    result={k:row.get(k) for k in keys}
    i=dict(row.get('problem_inspection') or {})
    recovery=i.get('original_recovery_selection') or {}
    i['original_recovery_selection']={k:recovery.get(k) for k in ('attempted','selected','objective','parent_iteration')}
    result.update(problem_inspection=i,local_iterations=(row.get('diagnostics') or {}).get('iterations'),
        stopping_controls=row.get('stopping_controls'),verification=row.get('verification'),
        raw_termination=(row.get('diagnostics') or {}).get('return_status'),
        selected_iteration=(row.get('diagnostics') or {}).get('selected_feasible_iteration'),
        local_recovery_selection={k:(row.get('recovery') or {}).get(k) for k in ('attempted','selected','objective','parent_iteration')})
    return result
