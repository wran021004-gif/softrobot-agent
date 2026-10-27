"""Candidate-bound coordinate search with sealed proposals and cumulative evaluator costs."""
from copy import deepcopy
import math,time
from tools.research.contracts import Search, FamilyMixedSearch, AnalysisRequest
from tools.research.design import construct,verify_candidate,parameter_value,set_parameter
from tools.research.state import state,update,save
from tools.platform_store import plain
from tools.state_io import digest
"""Shared bounded coordinate proposal used by the active research search."""
def coordinate_proposal(state):
    """Exact bounded coordinate step of matlab/tdcr_search_step.m (1-based axis)."""
    x=list(state['best'])
    k=state['iteration']
    axis=(k//2)%len(x)
    direction=1-2*(k%2)
    x[axis]=min(1.,max(0.,x[axis]+direction*state['step']))
    return dict(x=x,axis=axis+1,direction=direction,algorithm='bounded_coordinate_pattern_local_v1')


def search_problem(host,query,count):
    q=parse_search(query)
    s=state(host)
    native=isinstance(q,FamilyMixedSearch) and q.evaluation_mode=='mujoco_control'
    if q.objective=='task_violation' and not native:
        from tools.research.task_constraints import describe_analysis_requirements,analysis_capabilities
        from tools.research.optimal_capability import CONIC
        cfg=s['base_configuration']
        rows=analysis_capabilities(cfg,describe_analysis_requirements(cfg,{}),s['spec']['analysis_protocol'],
            remaining_evaluations=count,mathematical_methods={CONIC:s['spec'].get('mathematical_methods',{}).get(CONIC)})
        fit=next(r for r in rows if r.get('capability_method')==CONIC and not r.get('submode'))
        if fit['status']=='not_applicable':raise ValueError('TASK_VIOLATION_SEARCH_NOT_ADMITTED: '+str(fit['reasons']))
    if isinstance(q,FamilyMixedSearch):
        from extensions.tendon_family.family_space import search_domains
        grant=s['spec'].get('family_search')
        if not grant or q.screening_fidelity not in s['spec']['fidelity_policy']['screening']:
            raise ValueError('FROZEN_MIXED_SEARCH_AND_SCREENING_GRANT_REQUIRED')
        if q.evaluation_mode not in grant.get('evaluation_modes',['mathematical_proxy']):
            raise ValueError('SEARCH_MODE_OUTSIDE_FROZEN_GRANT')
        domains=search_domains(s['spec']['family_space'],q,grant)
        if native:
            spec=s['spec']
            if ('mujoco_control' not in grant.get('evaluation_modes',[]) or
                    not {'analysis','control_correction'}<=set(spec['capabilities']) or
                    not spec.get('mathematical_methods',{}).get('mujoco-nonlinear-task-capability-v1')):
                raise ValueError('FROZEN_NATIVE_SEARCH_ANALYSIS_CONTROL_AND_T1_GRANTS_REQUIRED')
            tasks=[c['task'] for c in spec.get('task_conditions',[])] or [s['base_configuration']['task']]
            if any(t['family']!='task.reach' or tuple(q.control_settings.correction_window_s)!=(0.,t['timing']['duration_s']) for t in tasks):
                raise ValueError('NATIVE_STRUCTURE_SEARCH_REQUIRES_COMPLETE_REACH_HOLD_WINDOWS')
            for name,limit in spec.get('native_control_limits',{}).items():
                requested=len(q.control_settings.knots_s) if name=='knots_s' else getattr(q.control_settings,name)
                if requested>limit:raise ValueError('STUDY_NATIVE_CONTROL_LIMIT: '+name)
            if count<len(tasks):raise ValueError('ALL_CONDITIONS_MUST_FIT_NATIVE_ANALYSIS_ALLOWANCE')
        if q.previous_candidate_ref:
            previous=verify_candidate(host,q.previous_candidate_ref)
            if previous.get('generation_version')!='serial_family_generation_v2' or previous['family_space_identity']!=q.family_space_identity:
                raise ValueError('PREVIOUS_CANDIDATE_REQUIRES_EXACT_SERIAL_FAMILY')
        from tools.research.state import readable_results
        for ref in q.evidence_used:
            if plain(ref) not in readable_results(s,host):
                raise ValueError('OWNED_SEARCH_EVIDENCE_REQUIRED')
            host.store.artifact(ref)
        return dict(query=plain(q),max_evaluations=count,domains=domains,profile=s['profile']['identity'],
            configuration_identity=s['spec']['resolved_identity'],task_identity=s['spec']['canonical_task_identity'],
            fidelity=s['spec']['fidelity_policy'],protocol=s['spec']['analysis_protocol'],
            **(dict(conditions=[c['condition_id'] for c in s['spec'].get('task_conditions',[])] or ['primary'],
                analyses_per_structure=len(tasks),native_callback_cap_per_condition=q.control_settings.evaluation_requests,
                score_semantics='max of per-condition finite-budget best found Native signed J; no global optimum or task acceptance') if native else {}))
    for key,(lo,hi) in q.bounds.items():
        grant=s['spec']['allowed_parameters'].get(key)
        if not grant or not grant[0]<=lo<hi<=grant[1]:
            raise ValueError('SEARCH_BOUNDS_OUTSIDE_STUDY_GRANT: '+key)
    if plain(q.protocol)!=s['spec']['analysis_protocol'] or q.scoring_window_s not in s['spec']['analysis_protocol']['windows_s']:
        raise ValueError('SEARCH_REQUIRES_FROZEN_PROTOCOL_AND_SCORE_WINDOW')
    layout=coordinate_layout(q,s['spec'].get('length_constraint',{}))
    return dict(query=plain(q),max_evaluations=count,profile=s['profile']['identity'],configuration_identity=s['spec']['resolved_identity'],layout=layout)


def parse_search(query):
    raw=plain(query)
    return (FamilyMixedSearch if raw.get('version')=='family_mixed_search_v1' else Search).model_validate(raw)


def initial_search_progress(host):
    """Project the existing search receipts; unresolved is never infeasible."""
    s=state(host);attempts=[]
    native=s['spec'].get('initial_structure_strategy')=='native_search'
    for checkpoint in s.get('searches',{}).values():
        query=checkpoint['problem']['query']
        if (query.get('version')!='family_mixed_search_v1' or query['objective']!='task_violation'
                or (query.get('evaluation_mode','mathematical_proxy')=='mujoco_control') != native):continue
        ref=checkpoint.get('result_reference')
        result=host.store.artifact(ref)['result'] if ref else {}
        used=result.get('resource_use',{}).get('actual_mathematical_evaluations',0)
        evaluated_math=any(row.get('evidence',{}).get('analysis') in s.get('analysis_results',[])
            for row in result.get('evaluated',[]))
        if native:
            evaluated_math=any(r.get('analysis') in s.get('analysis_results',[]) and (r.get('callbacks') or 0)>0
                for row in result.get('evaluated',[]) for r in row.get('evidence',{}).get('conditions',{}).values())
        complete=bool(ref and evaluated_math and result.get('termination_reason')!='analysis_not_admitted')
        attempts.append(dict(reference=ref,status='candidate_found' if complete and (result.get('best_native_candidate') if native else result.get('best_mathematical_candidate'))
            else 'completed_unresolved' if complete else 'incomplete',
            mathematical_evaluations=used,termination=result.get('termination_reason',checkpoint.get('termination'))))
    completed=[r for r in attempts if r['status'] in ('candidate_found','completed_unresolved')]
    return dict(status=('candidate_found' if any(r['status']=='candidate_found' for r in completed) else 'completed_unresolved')
        if completed else 'incomplete' if attempts else 'not_executed',attempts=attempts[-2:],
        requirement_satisfied=bool(completed),
        scope='A completed finite mathematical attempt releases the initial route gate, even without a ranked candidate. '
            'Unresolved math establishes neither structural infeasibility nor physical acceptance; interrupted/unadmitted work does not satisfy the start requirement.')


def request_guidance(spec):
    """Discovery works before a candidate exists; no scientific choice is made."""
    grant=spec['family_search']
    guidance=dict(generate=dict(tool='research_plan',action='generate',payload='generation',
            version='serial_family_generation_v2',required=['family_space_identity','segment_count','tendon_count']),
        search=dict(tool='research_plan',action='search',payload='search',
            version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],method=grant['method'],
            required=['variable_groups','segment_counts','tendon_counts','screening_fidelity','objective','operating_point','max_proposals','max_evaluations'],
            grant=grant,screening_fidelities=list(spec['fidelity_policy']['screening']),
            parameter_blocks=dict(lengths='Segment length in m',materials='Young modulus in Pa',
                sections='Section type/dimensions in m',routing='Span phase, station, channel angle and radius',
                spans='Consecutive span strategy',segment_count='Discrete number of segments',tendon_count='Discrete number of channels'),
            block_selection='Agent chooses a subset, e.g. lengths+materials or routing+sections, and singleton counts for fixed topology. Evidence-based selection requires exact evidence_used; otherwise label it a heuristic hypothesis.',
            objectives=dict(task_violation='CONIC sampled model task capability; controller_start_input or standardized_initial_pretension; model build + internal solves charged',
                target_equilibrium_residual='Static proxy only; target_equilibrium required',
                held_position_min_eigenvalue='Local held-input drive proxy only; controller_start_input or standardized_initial_pretension'),
            omit_legacy_fields=['variables','fixed','evaluation_mode','protocol','scoring_window_s']),
        analysis=dict(tool='research_analysis',operation='task_capability',candidate='existing owned candidate required',
            capability_method='sampled-affine-conic-minimax-v1',protocol='exact frozen analysis_protocol'),
        scope='All actions retain Plan hypothesis/decision obligations. Numerical failure is unknown; no proxy establishes independent physical acceptance.')
    if 'mujoco_control' in grant.get('evaluation_modes',[]):
        guidance['search']['native_mode']=dict(evaluation_mode='mujoco_control',objective='task_violation',
            inner_analysis='mujoco_nonlinear_task_capability_v1',
            operating_point='standardized_initial_pretension',
            required=['control_settings','initial_tension_n'],control_limits=spec.get('native_control_limits'),
            conditions=[c['condition_id'] for c in spec.get('task_conditions',[])] or ['primary'],
            initialization='Agent chooses legal common initial_tension_n; every proposed structure receives fresh independent per-condition Native control optimization.',
            budgets='max_evaluations counts condition analysis entries; each control_settings.evaluation_requests limits full Native callbacks. Construction, failures, steps and worker wall time retain original Store accounting. Independent physical replay uses the existing separate shared backend budget.',
            interpretation='Finite-budget best found J per condition, shared max J. No global optimum, infeasibility certificate or physical acceptance. T2 must compare evidence within one condition.',
            followup='Agent may independently replay a chosen schedule, continue bounded control optimization, change structure, or diagnose; structure search is optional.')
        if grant['evaluation_modes']==['mujoco_control']:
            guidance['search']['objectives']=dict(task_violation='Worst per-condition finite-budget best found Native J; original analysis entry and internal callback costs recorded separately.')
            guidance['analysis']=dict(tool='research_analysis',operation='mujoco_nonlinear_task_capability_v1',
                model_source='mujoco',candidate='existing owned task-bound candidate required',
                required=['control_optimization={source,settings}'],protocol='exact frozen analysis_protocol')
    return guidance


def coordinate_layout(query,constraint):
    names=sorted(query.variables)
    bounds=deepcopy(query.bounds)
    dependent=None
    total=constraint.get('fixed_total_m')
    lengths=[k for k in names if k.startswith('segments.') and k.endswith('.length_m')]
    if total is not None and lengths:
        if len(lengths)!=2:
            raise ValueError('FIXED_TOTAL_LENGTH_SEARCH_REQUIRES_BOTH_SEGMENT_LENGTHS')
        first,dependent=lengths
        names.remove(dependent)
        fixed=plain(query.fixed)
        other=sum(p['length_m'] for name,p in fixed['segments'].items() if 'segments.'+name+'.length_m' not in lengths)
        remaining=total-other
        lo,hi=bounds[first]
        a,b=bounds[dependent]
        bounds[first]=[max(lo,remaining-b),min(hi,remaining-a)]
        if bounds[first][0]>=bounds[first][1] or abs(sum(p['length_m'] for p in fixed['segments'].values())-total)>1e-12:
            raise ValueError('FIXED_TOTAL_SEARCH_INITIAL_OR_INTERVAL_INVALID')
        bounds.pop(dependent)
    return dict(names=names,bounds=bounds,dependent_length=dependent,fixed_total_m=total)


def rank(row,query,limits=None):
    if isinstance(query,FamilyMixedSearch) or query.evaluation_mode=='mathematical_proxy':
        value=row.get('proxy_values',{}).get(query.objective)
        valid=row.get('computation_status')=='computed' and value is not None and math.isfinite(value)
        return (0 if valid else 1,(-value if query.objective=='held_position_min_eigenvalue' else value) if valid else float('inf'))
    a=row.get('acceptance') or {}
    if a.get('components'):
        from tools.research.feedback import task_gap
        gap=task_gap(dict(status='evaluated',acceptance=a))
        valid=gap['valid_complete'] and gap['normalized_gap'] is not None
        return (0 if valid and a.get('accepted') else 1 if valid else 2,
            gap['normalized_gap'] if valid else float('inf'),sum(gap['components'].values()) if valid else float('inf'))
    m=a.get('metrics') or {}
    values=[m[k]/limit if isinstance(m.get(k),(float,int)) and math.isfinite(m[k]) else float('inf') for k,limit in limits.items()]
    return (0 if a.get('accepted') else 1,max(values),sum(values))


def native_evaluation(host, query, proposal, operation, persist, guard):
    """Use existing seeds/Native workers per frozen condition; checkpoint refs only."""
    from tools.research.analysis import dispatch as analyze
    from tools.research.physical_replay import seed_control
    from tools.research.contracts import ControlSeedRequest
    s=state(host);conditions=s['spec'].get('task_conditions',[]) or [dict(condition_id=None)]
    records=proposal.setdefault('native_conditions',{})
    for index,condition in enumerate(conditions):
        cid=condition['condition_id'];name=cid or 'primary';key=operation+':condition:'+str(index)
        record=records.setdefault(name,{})
        if 'seed' not in record:
            # A crash after seed publication reuses the existing initialization.
            saved=next((e for e in state(host).get('control_initializations',[])
                if host.store.artifact(e['source'])['provenance'].get('operation_key')==key+'-seed'),None)
            if saved is None:
                c=verify_candidate(host,proposal['candidate'])
                channels=len(c['configuration']['robot']['structure']['data']['tendons'])
                saved=seed_control(host,ControlSeedRequest(candidate=proposal['candidate'],condition_id=cid,
                    tensions_n=[[query.initial_tension_n]*channels]),key+'-seed')
            record['seed']=saved;persist()
        seed=record['seed']
        if 'analysis' not in record:
            request=dict(candidate=seed['candidate'],operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
                operating_point='standardized_initial_pretension',protocol=s['spec']['analysis_protocol'],
                control_optimization=dict(source=seed['source'],settings=plain(query.control_settings)))
            out=analyze(host,request,key,guard=guard,origin='model_search')
            if not out.get('reference'):
                return dict(kind='finite_budget_native_control',computation_status='not_applicable',proxy_values={},
                    evidence=dict(candidate=proposal['candidate'],conditions=deepcopy(records)),analysis_rejection=out,
                    actual_mathematical_evaluations=sum(r.get('charged_analysis_evaluations',0) for r in records.values()))
            record['analysis']=out['reference'];persist()
        a=host.store.artifact(record['analysis']);t=a.get('nonlinear_capability',{})
        attributed=a.get('operation_key')==key+'-analysis'
        record.update(candidate=seed['candidate'],status=a['status'],J=t.get('J'),initial_J=t.get('initial_J'),
            control_source=a.get('control_schedule_reference'),callbacks=t.get('callbacks'),
            stop_reason=t.get('stop_reason'),cost=a.get('native_dynamics',a.get('native_progress',{})).get('cost'),
            charged_analysis_evaluations=a.get('charged_analysis_evaluations',1) if attributed else 0,
            charged_numerical_s=a.get('charged_numerical_s',0.) if attributed else 0.)
        persist()
    complete=all(r.get('status')=='computed' and isinstance(r.get('J'),(int,float)) and math.isfinite(r['J']) for r in records.values())
    return dict(kind='finite_budget_native_control',computation_status='computed' if complete else 'unresolved',
        proxy_values=dict(task_violation=max(r['J'] for r in records.values())) if complete else {},
        task_acceptance='unmeasured',evidence=dict(candidate=proposal['candidate'],conditions=deepcopy(records)),
        actual_mathematical_evaluations=sum(r['charged_analysis_evaluations'] for r in records.values()),
        mathematical_numerical_s=sum(r['charged_numerical_s'] for r in records.values()),
        score_semantics='Best found under the recorded finite per-condition control budgets; max J across frozen tasks. Independent physical_replay and original joint SELECT remain required.')


def run_search(host,query,key,*,guard,execute,capacity):
    from tools.research.analysis import admission,dispatch as analyze
    guard(host,True)
    q=parse_search(query)
    mixed=isinstance(q,FamilyMixedSearch)
    native=mixed and q.evaluation_mode=='mujoco_control'
    mathematical=mixed or q.evaluation_mode=='mathematical_proxy'
    s=state(host)
    per_evaluation=1
    if native:
        per_evaluation=len(s['spec'].get('task_conditions',[])) or 1
    elif q.objective=='task_violation':
        from tools.research.optimal_capability import conic_subproblems
        from tools.research.task_constraints import describe_analysis_requirements
        per_evaluation=1+conic_subproblems(describe_analysis_requirements(s['base_configuration'],{}))
    fit=admission(host,q.max_evaluations) if mathematical else capacity(host,q.max_evaluations)
    identity=digest(dict(query=plain(q),profile=s['profile']['identity'],configuration_identity=s['spec']['resolved_identity']))
    owner=s.get('search_bindings',{}).get(identity,key)
    checkpoint=s['searches'].get(owner)
    if checkpoint and checkpoint.get('result_reference'):
        ref=checkpoint['result_reference']
        return dict(reference=ref,**host.store.artifact(ref),reused=True,
            operation_reuse=dict(additional_mathematical_evaluations=0,additional_numerical_s=0.))
    if checkpoint is None:
        if not fit['admitted']:
            return dict(status='budget_limited',admission=fit,evaluated=[])
        problem=search_problem(host,q,fit['admitted'])
        checkpoint=dict(problem=problem,problem_identity=identity,started=time.time(),evaluated=[],updates=[],
            iteration=0,step=q.step,pending=None,termination=None,proposal_count=0,skipped_moves=[],
            requesting_plan=next((r for r in s['plans'] if host.store.artifact(r)['request_id']==key),None))
        update(host,search_bindings={**s.get('search_bindings',{}),identity:owner})
    if checkpoint['problem_identity']!=identity:
        raise ValueError('SEARCH_RECOVERY_IDENTITY_MISMATCH')
    requesting_plan=checkpoint.get('requesting_plan')
    from tools.research_tasks import task_adapter
    limits=task_adapter(s['base_configuration']).ranking_limits()
    layout=checkpoint['problem'].get('layout',{})
    names=layout.get('names',[])
    bounds=layout.get('bounds',{})
    def persist():
        update(host,searches={**state(host)['searches'],owner:deepcopy(checkpoint)})
        return save(host,checkpoint,'search_checkpoint')
    while not checkpoint['termination']:
        rows=checkpoint['evaluated']
        if checkpoint['pending'] is None:
            consumed=sum(row.get('actual_mathematical_evaluations',1) for row in rows) if mathematical else len(rows)
            if consumed+per_evaluation>checkpoint['problem']['max_evaluations']:
                checkpoint['termination']='evaluation_budget_exhausted'
                break
            if mixed and checkpoint['proposal_count']>=q.max_proposals:
                checkpoint['termination']='proposal_budget_exhausted'
                break
            if mathematical and admission(host,per_evaluation)['admitted']<per_evaluation:
                checkpoint['termination']='study_mathematical_budget_exhausted'
                break
            if checkpoint['step']<q.minimum_step:
                checkpoint['termination']='minimum_coordinate_step'
                break
            if mixed:
                from tools.research.mixed_moves import initial,next_move,generation
                space=s['spec']['family_space']
                best=min((r for r in rows if r.get('candidate_id')),key=lambda row:rank(row,q),default=None)
                if not rows:
                    point=initial(space,q)
                    if q.previous_candidate_ref:
                        prior=verify_candidate(host,q.previous_candidate_ref)['resolved_parameters']
                        seed={str(i):dict(length_m=v['length_m'],young_pa=v['physics']['young_pa'],
                            section_kind=v['sections'][0]['section']['kind'],section_dimensions=v['sections'][0]['section']['parameters'])
                            for i,v in enumerate(prior['segments'])}
                        point=initial(space,q,dict(segments=seed))
                    changes=['family_defaults_and_authorized_ranges']
                else:
                    base=best['point'] if best else initial(space,q)
                    point,changes,checkpoint['step']=next_move(space,q,base,checkpoint['iteration'],q.step)
                    checkpoint['iteration']+=1
                    if point is None:
                        checkpoint['termination']='no_active_coordinate_moves'
                        break
                checkpoint['proposal_count']+=1
                params=generation(space,q,point)
                if any(row['parameters']==params for row in rows):
                    checkpoint.setdefault('skipped_moves',[]).append(dict(proposal=checkpoint['proposal_count'],
                        changed_paths=changes,reason='duplicate_or_clipped_no_change',additional_evaluations=0))
                    persist()
                    continue
                parent=best['evidence']['candidate'] if best else plain(q.previous_candidate_ref)
                evidence=([r['analysis'] for r in best['evidence']['conditions'].values() if r.get('analysis')]
                    if native and best else [best['evidence']['analysis']] if best and best['evidence'].get('analysis') else [plain(r) for r in q.evidence_used])
                checkpoint['pending']=dict(parameters=params,point=point,latent=[],proposal_id=str(checkpoint['proposal_count']),
                    feedback=parent,lineage=dict(version='search_lineage_v1',requesting_plan=requesting_plan,previous_candidate_ref=parent,evidence_used=evidence,
                        variables_or_topology_changed=changes,search_method=q.method,origin='optimizer_internal',
                        proposal_id=str(checkpoint['proposal_count']),decision=('move from best finite-budget Native result' if native else 'move from best observed proxy') if best else 'initialize authorized family subspace'))
                persist()
            else:
                fixed=plain(q.fixed)
            if not mixed and not rows:
                latent=[(parameter_value(fixed,k)-bounds[k][0])/(bounds[k][1]-bounds[k][0]) for k in names]
                parent=None
            elif not mixed:
                best=min(rows,key=lambda row:rank(row,q,limits))
                parent=best['candidate_id']
                latent=coordinate_proposal(dict(best=best['latent_coordinates'],iteration=checkpoint['iteration'],step=checkpoint['step']))['x']
                checkpoint['iteration']+=1
                if checkpoint['iteration']%(2*len(names))==0:
                    checkpoint['step']/=2
            if not mixed:
                params=deepcopy(fixed)
                for k,x in zip(names,latent):
                    lo,hi=bounds[k]
                    set_parameter(params,k,lo+x*(hi-lo))
            if not mixed and layout['dependent_length']:
                dependent=layout['dependent_length']
                other=sum(v['length_m'] for name,v in params['segments'].items() if 'segments.'+name+'.length_m'!=dependent)
                set_parameter(params,dependent,layout['fixed_total_m']-other)
            if not mixed:
                checkpoint['proposal_count']+=1
            if not mixed and any(row['parameters']==params for row in rows):
                if checkpoint['proposal_count']>128:
                    checkpoint['termination']='duplicate_proposal_limit'
                persist()
                continue
            if not mixed:
                checkpoint['pending']=dict(parameters=params,latent=latent,proposal_id=str(len(rows)),feedback=parent)
            persist()
        proposal=checkpoint['pending']
        op=owner+':'+proposal['proposal_id']
        # Proposal candidate is persisted before the expensive worker. Existing receipts
        # and the owned pending worker prohibit repeating an uncertain/completed solve.
        if not proposal.get('candidate'):
            if mixed:
                from tools.research.design import generate_candidate
                before=state(host).get('construction_numerical_s',0.)
                generated=generate_candidate(host,proposal['parameters'],dict(lineage=proposal['lineage'],plan_key=owner),screening_fidelity=q.screening_fidelity)
                proposal['construction_numerical_s']=state(host).get('construction_numerical_s',0.)-before
                if not generated.get('candidate'):
                    rows.append(dict(point=proposal['point'],parameters=proposal['parameters'],candidate_id=None,
                        computation_status=generated['status'],construction=generated,
                        lineage={**proposal['lineage'],'new_candidate_ref':None,'actual_mathematical_evaluation_ref':None,
                            'observed_result':generated,'cost':dict(additional_evaluations=0,construction_numerical_s=proposal['construction_numerical_s'])},
                        actual_mathematical_evaluations=0,evidence={}))
                    checkpoint['pending']=None
                    persist()
                    continue
                proposal['candidate']=generated['candidate']
            else:
                proposal['candidate']=construct(host,proposal['parameters'],dict(origin='model_design_search',plan_key=owner,proposal_id=proposal['proposal_id']))
            persist()
        ref=proposal['candidate']
        c=verify_candidate(host,ref)
        if native:
            row=native_evaluation(host,q,proposal,op,persist,guard)
        elif not mathematical:
            completed=next((host.store.artifact(r) for r in state(host)['results'] if host.store.artifact(r)['operation_key']==op),None)
            output=completed or execute(host,ref,op,role='search')
            r=output if completed else host.store.artifact(output['reference'])
            row=dict(acceptance=r.get('acceptance'),evidence=dict(candidate=ref,result=r),kind='backend_task')
        else:
            request=dict(candidate=ref,operation='task_capability' if q.objective=='task_violation' else 'equilibrium' if q.objective=='target_equilibrium_residual' else 'controllability',
                operating_point=q.operating_point,protocol=s['spec']['analysis_protocol'] if mixed else plain(q.protocol),
                scoring_window_s=s['spec']['scoring_window_s'] if mixed else q.scoring_window_s)
            if q.objective=='task_violation':
                from tools.research.optimal_capability import CONIC
                request.update(capability_method=CONIC,scoring_window_s=None)
            reused=next((r for r in state(host).get('analysis_results',[]) if mixed and
                host.store.artifact(r).get('requested_operation')==plain(AnalysisRequest.model_validate(request))),None)
            output=dict(reference=reused) if reused else analyze(host,request,op,guard=guard,origin='model_search')
            if not output.get('reference'):
                checkpoint['termination']='analysis_not_admitted'
                checkpoint['analysis_rejection']=output
                persist()
                break
            r=host.store.artifact(output['reference'])
            proxies=dict(r.get('proxy_values',{}))
            trajectory=r.get('trajectory') or {}
            if q.objective=='task_violation' and trajectory.get('replay',{}).get('numerically_valid'):
                proxies['task_violation']=trajectory.get('replayed_violation')
            row=dict(kind='mathematical_proxy',computation_status=r['status'],proxy_values=r.get('proxy_values',{}),
                local_model_constraints=r.get('local_model_constraints'),task_acceptance='unmeasured',
                evidence=dict(candidate=ref,analysis=output['reference'],score_semantics=r.get('score_semantics')))
            row.update(proxy_values=proxies,actual_mathematical_evaluations=r.get('charged_analysis_evaluations',1),
                task_violation_scope=dict(task_identity=c.get('task_identity'),coverage=r.get('analysis_applicability'),
                    optimality_status=trajectory.get('optimality_status'),source_pointer='/trajectory/replayed_violation') if q.objective=='task_violation' else None)
        row.update(candidate_id=c['candidate_id'],scientific_identity=c['identity'],parameters=proposal['parameters'],
            latent_coordinates=proposal['latent'],objective_identity=digest(checkpoint['problem']),used_feedback=proposal['feedback'])
        if native:
            row.update(point=proposal['point'],resolved_parameters=c['resolved_parameters'],
                physical_design_identity=c['physical_design_identity'],numerical_model_identity=c['numerical_model_identity'],
                lineage={**proposal['lineage'],'new_candidate_ref':ref,
                    'actual_mathematical_evaluation_refs':[r['analysis'] for r in row['evidence']['conditions'].values() if r.get('analysis')],
                    'observed_result':row['proxy_values'],'cost':dict(attributed_evaluations=row['actual_mathematical_evaluations'],
                        construction_numerical_s=proposal.get('construction_numerical_s',0.),attributed_numerical_s=row.get('mathematical_numerical_s',0.))})
        elif mixed:
            attributed=not reused or r.get('operation_key')==op+'-analysis'
            row.update(point=proposal['point'],resolved_parameters=c['resolved_parameters'],
                physical_design_identity=c['physical_design_identity'],numerical_model_identity=c['numerical_model_identity'],
                actual_mathematical_evaluations=r.get('charged_analysis_evaluations',1) if attributed else 0,
                mathematical_numerical_s=r.get('charged_numerical_s',0.) if attributed else 0.,
                lineage={**proposal['lineage'],'new_candidate_ref':ref,'actual_mathematical_evaluation_ref':output['reference'],
                    'observed_result':row['proxy_values'],'cost':dict(additional_evaluations=0 if reused else r.get('charged_analysis_evaluations',1),
                        attributed_evaluations=r.get('charged_analysis_evaluations',1) if attributed else 0,
                        construction_numerical_s=proposal.get('construction_numerical_s',0.),
                        numerical_s=0 if reused else r.get('charged_numerical_s'))})
        rows.append(row)
        checkpoint['pending']=None
        checkpoint['updates'].append(dict(candidate_id=c['candidate_id'],incumbent_after=min(rows,key=lambda row:rank(row,q,limits))['candidate_id']))
        if state(host).get('success_gate'):
            checkpoint['termination']='fresh_task_pass_requires_closeout'
        if mixed and q.stop_score is not None and rank(row,q)[0]==0:
            score=row['proxy_values'][q.objective]
            if (score>=q.stop_score if q.objective=='held_position_min_eigenvalue' else score<=q.stop_score):
                checkpoint['termination']='requested_finite_budget_native_score; task_unmeasured' if native else 'requested_proxy_stopping_score; task_unmeasured'
        persist()
    checkpoint_ref=persist()
    rows=checkpoint['evaluated']
    best=min(rows,key=lambda row:rank(row,q,limits)) if rows else None
    supported=best is not None and rank(best,q,limits)[0]==0
    result=dict(problem_identity=identity,status=('best_finite_budget_native_candidate' if supported else 'no_supported_result') if native else ('best_mathematical_candidate' if supported else 'no_supported_result') if mathematical else 'bounded_backend_search',
        requesting_plan=requesting_plan,best_mathematical_candidate=best if mathematical and supported and not native else None,best_observed=best,evaluated=rows,
        termination_reason=checkpoint['termination'],search_updates=checkpoint['updates'],search_state=checkpoint_ref,
        analysis_rejection=checkpoint.get('analysis_rejection'),
        resource_use=dict(evaluated_designs=len(rows),proposed_designs=checkpoint['proposal_count'],
            legally_constructed=sum(bool(row.get('candidate_id')) for row in rows),
            skipped_moves=checkpoint.get('skipped_moves',[]),
            actual_mathematical_evaluations=sum(row.get('actual_mathematical_evaluations',1) for row in rows) if mathematical else 0,
            elapsed_s=time.time()-checkpoint['started']),
        unsearched_scope=dict(global_feasibility_proven=False,global_optimality_proven=False))
    if native:
        result.update(best_native_candidate=best if supported else None,
            score_semantics=checkpoint['problem']['score_semantics'],task_acceptance='unmeasured',
            cost_scope='Original per-condition receipts attributed to this search; checkpoint/result reuse does not charge those receipts again.',
            comparison_summary=[dict(candidate=r.get('evidence',{}).get('candidate'),shared_J=r.get('proxy_values',{}).get('task_violation'),
                conditions={cid:{k:v.get(k) for k in ('status','J','initial_J','callbacks','stop_reason','cost','analysis','control_source')}
                    for cid,v in r.get('evidence',{}).get('conditions',{}).items()}) for r in rows])
    changed=None if mixed else sum(host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s['nominal_configuration']['robot'] for row in rows)
    ref=save(host,dict(result=result,structurally_changed_evaluations=changed,admission=fit),'design_search_result')
    checkpoint['result_reference']=ref
    update(host,searches={**state(host)['searches'],owner:checkpoint})
    update(host,search_results=[*state(host).get('search_results',[]),ref])
    return dict(reference=ref,result=result,structurally_changed_evaluations=changed,admission=fit)
