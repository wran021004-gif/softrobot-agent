"""Candidate-bound coordinate search with sealed proposals and cumulative evaluator costs."""
from copy import deepcopy
import math,time
from tools.research.contracts import Search
from tools.research.design import construct,verify_candidate,parameter_value,set_parameter
from tools.research.state import state,update,save
from tools.platform_store import plain
from tools.state_io import digest
from tools.optimization_interfaces import coordinate_proposal


def search_problem(host,query,count):
    q=Search.model_validate(query);s=state(host)
    for key,(lo,hi) in q.bounds.items():
        grant=s['spec']['allowed_parameters'].get(key)
        if not grant or not grant[0]<=lo<hi<=grant[1]:raise ValueError('SEARCH_BOUNDS_OUTSIDE_STUDY_GRANT: '+key)
    if plain(q.protocol)!=s['spec']['analysis_protocol'] or q.scoring_window_s!=s['spec']['scoring_window_s']:
        raise ValueError('SEARCH_REQUIRES_FROZEN_PROTOCOL_AND_SCORE_WINDOW')
    return dict(query=plain(q),max_evaluations=count,profile=s['profile']['identity'])


def rank(row,query):
    if query.evaluation_mode=='mathematical_proxy':
        value=row.get('proxy_values',{}).get(query.objective)
        valid=row.get('computation_status')=='computed' and value is not None and math.isfinite(value)
        return (0 if valid else 1,(-value if query.objective=='held_position_min_eigenvalue' else value) if valid else float('inf'))
    a=row.get('acceptance') or {};m=a.get('metrics') or {}
    values=[m.get(k,float('inf'))/limit for k,limit in [('terminal_error_m',.01),('holding_max_error_m',.01),('holding_max_speed_m_s',.02)]]
    return (0 if a.get('accepted') else 1,max(values),sum(values))


def run_search(host,query,key,*,guard,execute,capacity):
    from tools.research.analysis import admission,dispatch as analyze
    guard(host,True);q=Search.model_validate(query);s=state(host)
    fit=admission(host,q.max_evaluations) if q.evaluation_mode=='mathematical_proxy' else capacity(host,q.max_evaluations)
    identity=digest(dict(query=plain(q),profile=s['profile']['identity']))
    owner=s.get('search_bindings',{}).get(identity,key)
    checkpoint=s['searches'].get(owner)
    if checkpoint is None:
        if not fit['admitted']:return dict(status='budget_limited',admission=fit,evaluated=[])
        problem=search_problem(host,q,fit['admitted'])
        checkpoint=dict(problem=problem,problem_identity=identity,started=time.time(),evaluated=[],updates=[],
            iteration=0,step=q.step,pending=None,termination=None,proposal_count=0)
        update(host,search_bindings={**s.get('search_bindings',{}),identity:owner})
    if checkpoint['problem_identity']!=identity:raise ValueError('SEARCH_RECOVERY_IDENTITY_MISMATCH')
    names=sorted(q.variables)
    def persist():
        update(host,searches={**state(host)['searches'],owner:deepcopy(checkpoint)})
        return save(host,checkpoint,'search_checkpoint')
    while not checkpoint['termination']:
        rows=checkpoint['evaluated']
        if checkpoint['pending'] is None:
            if len(rows)>=checkpoint['problem']['max_evaluations']:
                checkpoint['termination']='evaluation_budget_exhausted';break
            if checkpoint['step']<q.minimum_step:
                checkpoint['termination']='minimum_coordinate_step';break
            fixed=plain(q.fixed)
            if not rows:
                latent=[(parameter_value(fixed,k)-q.bounds[k][0])/(q.bounds[k][1]-q.bounds[k][0]) for k in names]
                parent=None
            else:
                best=min(rows,key=lambda row:rank(row,q));parent=best['candidate_id']
                latent=coordinate_proposal(dict(best=best['latent_coordinates'],iteration=checkpoint['iteration'],step=checkpoint['step']))['x']
                checkpoint['iteration']+=1
                if checkpoint['iteration']%(2*len(names))==0:checkpoint['step']/=2
            params=deepcopy(fixed)
            for k,x in zip(names,latent):
                lo,hi=q.bounds[k];set_parameter(params,k,lo+x*(hi-lo))
            checkpoint['proposal_count']+=1
            if any(digest(row['parameters'])==digest(params) for row in rows):
                if checkpoint['proposal_count']>128:checkpoint['termination']='duplicate_proposal_limit'
                persist();continue
            checkpoint['pending']=dict(parameters=params,latent=latent,proposal_id=str(len(rows)),feedback=parent)
            persist()
        proposal=checkpoint['pending'];op=owner+':'+proposal['proposal_id']
        # Proposal candidate is persisted before the expensive worker. Existing receipts
        # and the owned pending worker prohibit repeating an uncertain/completed solve.
        if not proposal.get('candidate'):
            proposal['candidate']=construct(host,proposal['parameters'],dict(origin='model_design_search',plan_key=owner,proposal_id=proposal['proposal_id']))
            persist()
        ref=proposal['candidate'];c=verify_candidate(host,ref)
        if q.evaluation_mode=='backend_task':
            completed=next((host.store.artifact(r) for r in state(host)['results'] if host.store.artifact(r)['operation_key']==op),None)
            output=completed or execute(host,ref,op,role='search')
            r=output if completed else host.store.artifact(output['reference'])
            row=dict(acceptance=r.get('acceptance'),evidence=dict(candidate=ref,result=r),kind='backend_task')
        else:
            output=analyze(host,dict(candidate=ref,operation='equilibrium' if q.objective=='target_equilibrium_residual' else 'controllability',
                operating_point=q.operating_point,protocol=plain(q.protocol),scoring_window_s=q.scoring_window_s),op,guard=guard,origin='model_search')
            r=host.store.artifact(output['reference'])
            row=dict(kind='mathematical_proxy',computation_status=r['status'],proxy_values=r.get('proxy_values',{}),
                local_model_constraints=r.get('local_model_constraints'),task_acceptance='unmeasured',
                evidence=dict(candidate=ref,analysis=output['reference'],score_semantics=r.get('score_semantics')))
        row.update(candidate_id=c['candidate_id'],scientific_identity=c['identity'],parameters=proposal['parameters'],
            latent_coordinates=proposal['latent'],objective_identity=digest(checkpoint['problem']),used_feedback=proposal['feedback'])
        rows.append(row);checkpoint['pending']=None
        checkpoint['updates'].append(dict(candidate_id=c['candidate_id'],incumbent_after=min(rows,key=lambda row:rank(row,q))['candidate_id']))
        persist()
    checkpoint_ref=persist();rows=checkpoint['evaluated']
    best=min(rows,key=lambda row:rank(row,q)) if rows else None
    result=dict(problem_identity=identity,status='best_mathematical_candidate' if q.evaluation_mode=='mathematical_proxy' else 'bounded_backend_search',
        best_mathematical_candidate=best if q.evaluation_mode=='mathematical_proxy' else None,best_observed=best,evaluated=rows,
        termination_reason=checkpoint['termination'],search_updates=checkpoint['updates'],search_state=checkpoint_ref,
        resource_use=dict(evaluated_designs=len(rows),elapsed_s=time.time()-checkpoint['started']),
        unsearched_scope=dict(global_feasibility_proven=False,global_optimality_proven=False))
    changed=sum(host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s['nominal_configuration']['robot'] for row in rows)
    ref=save(host,dict(result=result,structurally_changed_evaluations=changed,admission=fit),'design_search_result')
    update(host,search_results=[*state(host).get('search_results',[]),ref])
    return dict(reference=ref,result=result,structurally_changed_evaluations=changed,admission=fit)
