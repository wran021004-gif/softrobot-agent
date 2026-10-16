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
    if isinstance(q,FamilyMixedSearch):
        from extensions.tendon_family.family_space import search_domains
        grant=s['spec'].get('family_search')
        if not grant or q.screening_fidelity not in s['spec']['fidelity_policy']['screening']:
            raise ValueError('FROZEN_MIXED_SEARCH_AND_SCREENING_GRANT_REQUIRED')
        domains=search_domains(s['spec']['family_space'],q,grant)
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
            fidelity=s['spec']['fidelity_policy'],protocol=s['spec']['analysis_protocol'])
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
    m=a.get('metrics') or {}
    values=[m.get(k,float('inf'))/limit for k,limit in limits.items()]
    return (0 if a.get('accepted') else 1,max(values),sum(values))


def run_search(host,query,key,*,guard,execute,capacity):
    from tools.research.analysis import admission,dispatch as analyze
    guard(host,True)
    q=parse_search(query)
    mixed=isinstance(q,FamilyMixedSearch)
    mathematical=mixed or q.evaluation_mode=='mathematical_proxy'
    s=state(host)
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
            iteration=0,step=q.step,pending=None,termination=None,proposal_count=0,
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
            consumed=sum(row.get('actual_mathematical_evaluations',1) for row in rows) if mixed else len(rows)
            if consumed>=checkpoint['problem']['max_evaluations']:
                checkpoint['termination']='evaluation_budget_exhausted'
                break
            if mixed and checkpoint['proposal_count']>=q.max_proposals:
                checkpoint['termination']='proposal_budget_exhausted'
                break
            if mixed and not admission(host,1)['admitted']:
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
                parent=best['evidence']['candidate'] if best else plain(q.previous_candidate_ref)
                evidence=[best['evidence']['analysis']] if best and best['evidence'].get('analysis') else [plain(r) for r in q.evidence_used]
                checkpoint['pending']=dict(parameters=params,point=point,latent=[],proposal_id=str(checkpoint['proposal_count']),
                    feedback=parent,lineage=dict(version='search_lineage_v1',requesting_plan=requesting_plan,previous_candidate_ref=parent,evidence_used=evidence,
                        variables_or_topology_changed=changes,search_method=q.method,origin='optimizer_internal',
                        proposal_id=str(checkpoint['proposal_count']),decision='move from best observed proxy' if best else 'initialize authorized family subspace'))
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
            if not mixed and any(digest(row['parameters'])==digest(params) for row in rows):
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
                generated=generate_candidate(host,proposal['parameters'],dict(lineage=proposal['lineage'],plan_key=owner),screening_fidelity=q.screening_fidelity)
                if not generated.get('candidate'):
                    rows.append(dict(point=proposal['point'],parameters=proposal['parameters'],candidate_id=None,
                        computation_status=generated['status'],construction=generated,lineage=proposal['lineage'],
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
        if not mathematical:
            completed=next((host.store.artifact(r) for r in state(host)['results'] if host.store.artifact(r)['operation_key']==op),None)
            output=completed or execute(host,ref,op,role='search')
            r=output if completed else host.store.artifact(output['reference'])
            row=dict(acceptance=r.get('acceptance'),evidence=dict(candidate=ref,result=r),kind='backend_task')
        else:
            request=dict(candidate=ref,operation='equilibrium' if q.objective=='target_equilibrium_residual' else 'controllability',
                operating_point=q.operating_point,protocol=s['spec']['analysis_protocol'] if mixed else plain(q.protocol),
                scoring_window_s=s['spec']['scoring_window_s'] if mixed else q.scoring_window_s)
            reused=next((r for r in state(host).get('analysis_results',[]) if mixed and
                host.store.artifact(r).get('requested_operation')==plain(AnalysisRequest.model_validate(request))),None)
            output=dict(reference=reused) if reused else analyze(host,request,op,guard=guard,origin='model_search')
            r=host.store.artifact(output['reference'])
            row=dict(kind='mathematical_proxy',computation_status=r['status'],proxy_values=r.get('proxy_values',{}),
                local_model_constraints=r.get('local_model_constraints'),task_acceptance='unmeasured',
                evidence=dict(candidate=ref,analysis=output['reference'],score_semantics=r.get('score_semantics')))
        row.update(candidate_id=c['candidate_id'],scientific_identity=c['identity'],parameters=proposal['parameters'],
            latent_coordinates=proposal['latent'],objective_identity=digest(checkpoint['problem']),used_feedback=proposal['feedback'])
        if mixed:
            row.update(point=proposal['point'],resolved_parameters=c['resolved_parameters'],
                physical_design_identity=c['physical_design_identity'],numerical_model_identity=c['numerical_model_identity'],
                actual_mathematical_evaluations=0 if reused else 1,
                lineage={**proposal['lineage'],'new_candidate_ref':ref,'actual_mathematical_evaluation_ref':output['reference'],
                    'observed_result':r.get('proxy_values',{}),'cost':dict(additional_evaluations=0 if reused else 1,
                        numerical_s=0 if reused else r.get('charged_numerical_s'))})
        rows.append(row)
        checkpoint['pending']=None
        checkpoint['updates'].append(dict(candidate_id=c['candidate_id'],incumbent_after=min(rows,key=lambda row:rank(row,q,limits))['candidate_id']))
        if state(host).get('success_gate'):
            checkpoint['termination']='fresh_task_pass_requires_closeout'
        if mixed and q.stop_score is not None and rank(row,q)[0]==0:
            score=row['proxy_values'][q.objective]
            if (score<=q.stop_score if q.objective=='target_equilibrium_residual' else score>=q.stop_score):
                checkpoint['termination']='requested_proxy_stopping_score; task_unmeasured'
        persist()
    checkpoint_ref=persist()
    rows=checkpoint['evaluated']
    best=min(rows,key=lambda row:rank(row,q,limits)) if rows else None
    supported=best is not None and rank(best,q,limits)[0]==0
    result=dict(problem_identity=identity,status=('best_mathematical_candidate' if supported else 'no_supported_result') if mathematical else 'bounded_backend_search',
        requesting_plan=requesting_plan,best_mathematical_candidate=best if mathematical and supported else None,best_observed=best,evaluated=rows,
        termination_reason=checkpoint['termination'],search_updates=checkpoint['updates'],search_state=checkpoint_ref,
        resource_use=dict(evaluated_designs=len(rows),proposed_designs=checkpoint['proposal_count'],
            actual_mathematical_evaluations=sum(row.get('actual_mathematical_evaluations',1) for row in rows) if mathematical else 0,
            elapsed_s=time.time()-checkpoint['started']),
        unsearched_scope=dict(global_feasibility_proven=False,global_optimality_proven=False))
    changed=None if mixed else sum(host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s['nominal_configuration']['robot'] for row in rows)
    ref=save(host,dict(result=result,structurally_changed_evaluations=changed,admission=fit),'design_search_result')
    checkpoint['result_reference']=ref
    update(host,searches={**state(host)['searches'],owner:checkpoint})
    update(host,search_results=[*state(host).get('search_results',[]),ref])
    return dict(reference=ref,result=result,structurally_changed_evaluations=changed,admission=fit)
