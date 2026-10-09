"""One bounded numerical service shared by native Strands and direct callers."""
from copy import deepcopy
from itertools import product
import time
import numpy as np
from schemas.design_optimization import (DesignOptimizationProblem,DesignOptimizationResult,
    EvaluatedDesign,Fixed,Integer,Continuous,Structure)
from schemas.platform import SessionInput
from tools.platform_store import plain,zero
from tools.state_io import digest
from tools.optimization_interfaces import coordinate_proposal
from extensions.tendon_family import generated_serial as family


def structures(problem):
    def options(name):
        spec=problem.variables[name]
        return [spec.value] if isinstance(spec,Fixed) else list(range(spec.bounds[0],spec.bounds[1]+1)) if isinstance(spec,Integer) else spec.choices
    result=[]
    for n,p,d,m in product(*(options(k) for k in ('segment_count','proximal_tendons','distal_tendons','material'))):
        if any(count is not None and count!=p+d for count in (problem.fixed_tendon_count,problem.fixed_actuator_count)):continue
        result.append(dict(segment_count=n,proximal_tendons=p,distal_tendons=d,material=m))
    if not result:raise ValueError('NO_COMPATIBLE_STRUCTURE_FOR_FIXED_COUNTS')
    for s in problem.method.initial_structures:
        if plain(s) not in result:raise ValueError('INITIAL_STRUCTURE_OUTSIDE_DECLARED_DOMAIN')
    return result


class Allocation:
    """Sequential interval parameterization of a bounded simplex.

    Each active interval accounts for all remaining lower/upper bounds. No
    post-hoc normalization; the final length is derived by exact subtraction.
    Equal/fixed coordinates are absent from the latent vector.
    """
    def __init__(self,spec,count):
        self.total=spec.total_flexible_length_m
        self.base=spec.baseline_by_count[str(count)] if str(count) in spec.baseline_by_count else family.default_lengths(count,self.total)
        if len(self.base)!=count or any(l<=0 for l in self.base) or abs(sum(self.base)-self.total)>1e-12:
            raise ValueError('BASELINE_VECTOR_MUST_MATCH_COUNT_POSITIVE_AND_TOTAL')
        self.bounds=spec.bounds_by_count.get(str(count),[(l*(1-spec.relative_range),l*(1+spec.relative_range)) for l in self.base])
        if len(self.bounds)!=count:raise ValueError('TOPOLOGY_LENGTH_BOUNDS_SIZE')
        self.bounds=[tuple(b) for b in self.bounds]
        for i,(a,b) in enumerate(self.bounds):
            if not 0<a<=self.base[i]<=b:raise ValueError('BASELINE_OUTSIDE_POSITIVE_LENGTH_BOUNDS')
            # v1 stays conservative around the public topology-local baseline.
            if a<self.base[i]*.95-1e-12 or b>self.base[i]*1.05+1e-12:raise ValueError('LENGTH_BOUNDS_EXCEED_FIVE_PERCENT')
        fixed=spec.fixed_by_count.get(str(count),{})
        for key,value in fixed.items():
            if not key.isdigit() or not 0<=int(key)<count:raise ValueError('INACTIVE_FIXED_LENGTH_INDEX')
            i=int(key);a,b=self.bounds[i]
            if not a<=value<=b:raise ValueError('FIXED_LENGTH_OUTSIDE_BOUND')
            self.bounds[i]=(value,value)
        if not spec.free:
            if any(abs(value-self.base[int(key)])>1e-12 for key,value in fixed.items()):
                raise ValueError('FIXED_VECTOR_CONFLICTS_WITH_FIXED_LENGTH_OVERRIDE')
            self.bounds=[(l,l) for l in self.base]
        if sum(a for a,b in self.bounds)>self.total+1e-12 or sum(b for a,b in self.bounds)<self.total-1e-12:
            raise ValueError('INFEASIBLE_LENGTH_SUM_AND_BOUNDS')
        self.indices=[i for i,(a,b) in enumerate(self.bounds) if a<b]
        self.derived=self.indices[-1] if self.indices else None
        self.active=self.indices[:-1]
        # Fixed overrides may move the start; choose conditional interval
        # midpoints as a feasible initialization when the baseline is excluded.
        self.initial=self.encode(self.base) if self.valid(self.base) else {f'length/{i}':.5 for i in self.active}

    def valid(self,values):
        return abs(sum(values)-self.total)<=1e-12 and all(a-1e-12<=v<=b+1e-12 for v,(a,b) in zip(values,self.bounds))

    def interval(self,i,remaining,unassigned):
        a,b=self.bounds[i]
        return max(a,remaining-sum(self.bounds[j][1] for j in unassigned)),min(b,remaining-sum(self.bounds[j][0] for j in unassigned))

    def encode(self,values):
        remaining=self.total-sum(a for a,b in self.bounds if a==b);encoded={}
        for index,i in enumerate(self.active):
            a,b=self.interval(i,remaining,self.indices[index+1:])
            encoded[f'length/{i}']=(values[i]-a)/(b-a) if b-a>1e-15 else .5
            remaining-=values[i]
        return encoded

    def decode(self,latent):
        values=[a if a==b else None for a,b in self.bounds]
        remaining=self.total-sum(v for v in values if v is not None)
        for index,i in enumerate(self.active):
            a,b=self.interval(i,remaining,self.indices[index+1:]);x=latent[f'length/{i}']
            if not 0<=x<=1:raise ValueError('LATENT_LENGTH_COORDINATE_OUT_OF_BOUNDS')
            values[i]=a+x*max(0.,b-a);remaining-=values[i]
        if self.derived is not None:values[self.derived]=remaining
        if not self.valid(values):raise ValueError('DECODED_LENGTH_BOUNDS_OR_SUM')
        return values


def continuous_space(problem,structure):
    allocation=Allocation(problem.lengths,structure['segment_count']);initial=dict(allocation.initial)
    variables=problem.variables.items()
    if problem.method.name=='hierarchical_coordinate_v1_1':variables=sorted(variables)
    for k,v in variables:
        if isinstance(v,Continuous):initial[k]=(v.initial-v.bounds[0])/(v.bounds[1]-v.bounds[0])
    return allocation,initial


def decode(problem,structure,latent):
    allocation,initial=continuous_space(problem,structure)
    if set(latent)!=set(initial):raise ValueError('INACTIVE_OR_MISSING_LATENT_COORDINATES')
    values={k:v.value for k,v in problem.variables.items() if isinstance(v,Fixed)}
    values.update(structure)
    for k,v in problem.variables.items():
        if isinstance(v,Continuous):
            x=latent[k]
            if not 0<=x<=1:raise ValueError('LATENT_CONTINUOUS_COORDINATE_OUT_OF_BOUNDS')
            values[k]=v.bounds[0]+x*(v.bounds[1]-v.bounds[0])
    values['lengths_m']=allocation.decode(latent)
    return values


def resolved_input(problem,values,run_id,policy):
    r=family.Recipe.model_validate({k:v for k,v in values.items() if k not in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
    design,mesh,physics=family.generate(r)
    cfg=deepcopy(family.catalog()['scientific_source']);cfg['run_id']=run_id;cfg['seed']=problem.execution.seed
    cfg['robot']['structure']['data']=design;cfg['task']=plain(problem.task)
    cfg['task']['initializer']['parameters']['data']={field:{j:0. for j in physics['dofs']} for field in ('qpos_rad','qvel_rad_s')}
    cfg['task']['initializer']['parameters']['data']['unspecified']='zero'
    cfg['policy']=deepcopy(policy)
    cfg['policy'].update(controller=dict(extension_id='controller.gvs_nmpc',version=family.CONTROLLER_VERSION,
        parameters=dict(contract='family.gvs_reach_control',version='1.0.0',data=dict(recipe=plain(problem.execution.recipe),
            settling=plain(problem.execution.settling),numerical_source='initial_state_pretension'))),
        candidate_builder=dict(extension_id='candidate.family',version=family.BUILDER_VERSION,
            parameters=dict(contract='family.generator_space',version='1.0.0',data=plain(family.GeneratorSpace(recipe=r)))),
        discretization=dict(contract='family.discretization',version='1.0.0',data=mesh),editable={},route=None,search=None)
    for name in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        cfg['policy']['controller']['parameters']['data']['recipe'][name]=values[name]
    inp=SessionInput.model_validate(cfg);family.checked_reach(inp)
    return plain(inp)


def validate_problem(problem):
    problem=DesignOptimizationProblem.model_validate(problem)
    topology=structures(problem)
    for structure in topology:
        allocation,initial=continuous_space(problem,structure);decode(problem,structure,initial)
    # Scientific algorithm inherited, with only the declared two weights free.
    expected=family.catalog()['scientific_source']['policy']['controller']['parameters']['data']['recipe']
    actual=plain(problem.execution.recipe)
    for name in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        actual.pop(name);expected=deepcopy(expected);expected.pop(name,None)
    if actual!=expected:raise ValueError('INHERITED_NMPC_RECIPE_FROZEN_EXCEPT_DECLARED_WEIGHTS')
    if any(v!=0 for f in ('qpos_rad','qvel_rad_s') for v in problem.task.initializer.parameters.data.get(f,{}).values()):
        raise ValueError('PROBLEM_REQUIRES_PHYSICAL_ZERO_INITIAL_STATE')
    return problem,topology


def rank(row,problem):
    if row['feasible']:
        return (0,row['resolved']['actuator_count'] if problem.objective.accepted_resource_preference=='fewer_actuators' else 0,
                row['objective_values']['max_normalized_ratio'],row['objective_values']['sum_normalized_ratio'])
    return (1,row['objective_values'].get('max_normalized_ratio',1e100),row['objective_values'].get('sum_normalized_ratio',1e100))


def resolve_report(cfg,values):
    design=cfg['robot']['structure']['data'];mesh=cfg['policy']['discretization']['data']
    from extensions.tendon_family.design_decisions import physical_summary
    summary=physical_summary(design,mesh)
    from extensions.tendon_family.compiler import resolve
    from extensions.tendon_family.geometry import geometry
    physics=resolve(design,mesh)
    return dict(parameters=values,segment_count=values['segment_count'],tendon_count=len(design['tendons']),
        actuator_count=len(design['actuators']),total_flexible_length_m=sum(values['lengths_m']),
        physical_summary=summary,total_modeled_mass_kg=sum(p['mass_kg'] for p in physics['parts']),
        zero_state_base_to_tip_centerline_length_m=float(geometry(physics,np.zeros(len(physics['dofs'])))['tip'][0]),
        sum_individual_tension_limits_n=sum(t['force_limit_n'] for t in design['tendons']),
        motor_mass_established=False,geometry=design['components'],routing=design['tendons'],actuator_mapping=design['actuators'],
        discretization=mesh,tip=design['tip'],controller=cfg['policy']['controller'],
        physical_initial_state=cfg['task']['initializer']['parameters']['data'],
        numerical_initialization=family.dimensions(SessionInput.model_validate(cfg))['numerical_initialization'])


class ReceiptEvaluator:
    def __init__(self,host):self.host=host

    def __call__(self,problem,values,candidate_id):
        from tools.platform_host import Host
        from tools.execution_completion import complete_execution,EXECUTION_ALLOWANCES
        from tools.research_tasks import assemble_acceptance
        policy=deepcopy(self.host.store.session(self.host.run_id)['snapshot']['input']['policy'])
        existing=self.host.store.lookup(candidate_id,'complete-simulation')
        spec=self.host.store.session(self.host.run_id)['state'].get('mixed_spec')
        if not existing and spec:
            if time.time()+1800.>spec['execution_cutoff_unix']:raise ValueError('BACKEND_WOULD_ENTER_PROTECTED_DELIVERY_WINDOW')
            with self.host.store.connect(True) as db:
                attempts=[r['run_id'] for r in db.execute("SELECT run_id FROM calls WHERE request_id='complete-simulation'")]
            confirm=candidate_id.startswith('confirm-')
            if len(attempts)>=12 or (sum(r.startswith('confirm-') for r in attempts)>=2 if confirm else sum(not r.startswith('confirm-') for r in attempts)>=8):
                raise ValueError('PROTECTED_BACKEND_RESOURCE_CEILING')
        policy.update(budget={**policy['budget'],'model_calls':0},allowed_tools=[],
            tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
            operation_allowances=deepcopy(EXECUTION_ALLOWANCES))
        policy['operation_allowances']['simulation.run']=dict(timeout_s=1800.,reserve_s=1800.)
        cfg=resolved_input(problem,values,candidate_id,policy)
        child=Host(self.host.store.root,candidate_id,actor=self.host.actor)
        try:existing=child.store.session(candidate_id)
        except ValueError:existing=child.create(cfg,parent_run_id=self.host.run_id)
        from tools.platform_tasks import compile_input
        if existing['snapshot']['input']!=compile_input(cfg,child.reg)['input']:raise ValueError('DESIGN_EXECUTION_INPUT_CHANGED')
        result=complete_execution(child,cfg,candidate_id)
        if result['status']!='evaluated':return dict(status=result['status'],evidence=result)
        report=child.store.artifact(result['profile_report']['reference'])
        acceptance=assemble_acceptance(cfg,result['evaluation_data'],report,
            evaluation_reference=result['factual_result']['evaluation'],profile_reference=result['profile_report']['reference'],
            motion=child.store.artifact(report['detail']['motion']))
        return dict(status='evaluated',acceptance=acceptance,evidence=dict(configuration=result['configuration'],
            execution_id=result['execution_id'],owner_run_id=candidate_id,receipts=result['receipts'],
            profile=result['profile_report'],feedback=result['structured_feedback']),configuration=cfg)


def evaluate(problem,structure,latent,candidate_id,phase,evaluator,feedback=None):
    values=decode(problem,structure,latent);result=evaluator(problem,values,candidate_id)
    if result['status']!='evaluated':return result
    a=result['acceptance'];m=a['metrics']
    limits=tuple(a.get('components',{}).get(key,{}).get('limit',fallback) for key,fallback in
        [('evaluator:task_bound',.01),('holding_position',problem.execution.settling.position_limit_m),
         ('holding_speed',problem.execution.settling.speed_limit_m_s)])
    metrics=[m['terminal_error_m'],m['holding_max_error_m'],m['holding_max_speed_m_s']]
    ratios=[v/l for v,l in zip(metrics,limits)]
    cfg=result.get('configuration')
    resolved=resolve_report(cfg,values) if cfg else dict(parameters=values,segment_count=values['segment_count'],
        tendon_count=values['proximal_tendons']+values['distal_tendons'],actuator_count=values['proximal_tendons']+values['distal_tendons'])
    allocation,_=continuous_space(problem,structure)
    return plain(EvaluatedDesign(candidate_id=candidate_id,phase=phase,scientific_identity=digest(values),
        latent_coordinates=latent,resolved=resolved,feasible=a['accepted'],objective_values=dict(**m,
            max_normalized_ratio=max(ratios),sum_normalized_ratio=sum(ratios)),
        constraint_outcomes=dict(physical_acceptance=a,length_sum=abs(sum(values['lengths_m'])-problem.lengths.total_flexible_length_m)<=1e-12,
            individual_length_bounds=allocation.valid(values['lengths_m']),fixed_conditions='validated decoded problem and exact generated recipe'),
        evidence=result['evidence'],execution_status=a['status'],used_feedback=feedback))


def solve(problem,host=None,*,evaluator=None,state=None,save_state=None):
    """Bounded outer enumeration + feedback-directed inner coordinate proposals.

    Pending decoded proposals are sealed before execution. Recovery calls the
    existing complete_execution chain, which never repeats a sealed simulation.
    """
    problem,topology=validate_problem(problem);identity=digest(plain(problem))
    if host is not None:
        state=host.store.session(host.run_id)['state'].get('design_searches',{}).get(identity)
        evaluator=evaluator or ReceiptEvaluator(host)
        def save_state(value):
            with host.store.transaction() as db:
                session=host.store.session(host.run_id,db)['state'];session.setdefault('design_searches',{})[identity]=deepcopy(value)
                ref=host.store.put(db,value);host.store.update_state(db,host.run_id,session)
                host.store.event(db,host.run_id,'design_search','checkpoint',outputs=[ref])
            return plain(ref)
    if evaluator is None:raise ValueError('EVALUATOR_OR_HOST_REQUIRED')
    state=deepcopy(state) if state else dict(problem_identity=identity,problem=plain(problem),started=time.time(),evaluated=[],updates=[],rejections=[],
        initialized=[],inner={},pending=None,proposal_count=0,termination=None)
    if state['problem_identity']!=identity:raise ValueError('SEARCH_STATE_PROBLEM_IDENTITY')
    save_state=save_state or (lambda s:None)
    initial=[plain(s) for s in problem.method.initial_structures] or topology[:min(2,len(topology))]
    while not state['termination']:
        if state['pending'] is None:
            if len(state['evaluated'])>=problem.budget.max_evaluations:state['termination']='evaluation_budget_exhausted';break
            if time.time()-state['started']>=problem.budget.wall_s:state['termination']='wall_budget_exhausted';break
            missing=[s for s in initial if digest(s) not in state['initialized']]
            if missing:
                structure=missing[0];_,latent=continuous_space(problem,structure);phase='structural_initialization';feedback=None
            else:
                eligible=[r for r in state['evaluated'] if r['latent_coordinates']]
                if not eligible:state['termination']='all_design_variables_fixed';break
                incumbent=min(eligible,key=lambda r:rank(r,problem));structure={k:incumbent['resolved']['parameters'][k] for k in ('segment_count','proximal_tendons','distal_tendons','material')}
                inner=state['inner'].setdefault(digest(structure),dict(iteration=0,step=problem.method.step))
                if inner['step']<problem.method.minimum_step:state['termination']='minimum_coordinate_step';break
                names=list(continuous_space(problem,structure)[1]) if problem.method.name=='hierarchical_coordinate_v1_1' else list(incumbent['latent_coordinates'])
                proposal=coordinate_proposal(dict(best=[incumbent['latent_coordinates'][k] for k in names],**inner))
                latent=dict(zip(names,proposal['x']));phase='feedback_coordinate';feedback=incumbent['candidate_id']
                inner['iteration']+=1
                if inner['iteration']%(2*len(names))==0:inner['step']/=2
            values=decode(problem,structure,latent);scientific=digest(values)
            state['proposal_count']+=1
            if any(r['scientific_identity']==scientific for r in state['evaluated']):
                state['updates'].append(dict(kind='exact_cache_hit_no_backend',scientific_identity=scientific))
                if state['proposal_count']>128:state['termination']='duplicate_proposal_limit'
                save_state(state);continue
            state['pending']=dict(structure=structure,latent=latent,phase=phase,feedback=feedback,
                candidate_id='mixed-'+identity[:10]+'-'+str(len(state['evaluated'])),decoded=values)
            save_state(state)
        pending=state['pending']
        try:
            row=evaluate(problem,pending['structure'],pending['latent'],pending['candidate_id'],pending['phase'],evaluator,pending['feedback'])
        except ValueError as exc:
            # Construction rejects are not experiments. Backend reservation or
            # receipts forbid recasting an executed failure as a cheap rejection.
            if host is not None:
                with host.store.connect(True) as db:
                    attempted=db.execute("SELECT COUNT(*) FROM calls WHERE run_id=? AND request_id='complete-simulation'",(pending['candidate_id'],)).fetchone()[0]
                if attempted:raise
            state['rejections'].append(dict(proposal=pending,reason=str(exc)));state['termination']='construction_rejected';state['pending']=None;break
        if row.get('status') and row['status']!='evaluated':
            save_state(state)
            return DesignOptimizationResult(problem_identity=identity,status='pending_execution',evaluated=state['evaluated'],
                search_updates=state['updates'],termination_reason=row['status'],unsearched_scope=dict(topologies=topology),resource_use={},search_state=save_state(state))
        previous=min(state['evaluated'],key=lambda r:rank(r,problem)) if state['evaluated'] else None
        state['evaluated'].append(row);state['initialized'].append(digest(pending['structure']))
        state['updates'].append(dict(candidate_id=row['candidate_id'],phase=row['phase'],used_feedback=pending['feedback'],
            incumbent_before=previous['candidate_id'] if previous else None,
            incumbent_after=min(state['evaluated'],key=lambda r:rank(r,problem))['candidate_id'],objective=row['objective_values']))
        state['pending']=None;save_state(state)
        if row['feasible'] and problem.method.stop_on_acceptance:state['termination']='joint_acceptance_found'
    feasible=[r for r in state['evaluated'] if r['feasible']];infeasible=[r for r in state['evaluated'] if not r['feasible']]
    ref=save_state(state)
    return DesignOptimizationResult(problem_identity=identity,status='best_feasible_found' if feasible else 'bounded_search_without_feasible',
        best_feasible=min(feasible,key=lambda r:rank(r,problem)) if feasible else None,
        best_observed_infeasible=min(infeasible,key=lambda r:rank(r,problem)) if infeasible else None,
        evaluated=state['evaluated'],construction_rejections=state['rejections'],search_updates=state['updates'],
        termination_reason=state['termination'],search_state=ref,resource_use=dict(new_evaluated_designs=len(state['evaluated']),
            construction_rejections=len(state['rejections']),elapsed_s=time.time()-state['started']),
        unsearched_scope=dict(topologies=[s for s in topology if digest(s) not in state['initialized']],
            continuous_domain_exhausted=False,global_feasibility_proven=False,global_optimality_proven=False))


def solve_tool(ctx,args):
    from tools.platform_host import Host
    return solve(args,Host(ctx.store.root,ctx.run_id,actor=ctx.host.actor))
