"""Public bounded optimization using the existing Host, ask/tell and coordinate step."""
from pathlib import Path
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import SessionInput, Payload, Binding
from tools.optimization_interfaces import ParameterSpace, coordinate_proposal
from tools.platform_store import plain
from schemas.parameter_domains import ParameterDomain


class SearchParameters(Contract):
    initial: dict[str, float]
    bounds: dict[str, tuple[float, float]]
    max_trials: int = Field(default=3, ge=1)
    step: float = Field(default=.2, gt=0, le=1)


class SearchState(Contract):
    proposed: int = 0
    best: list[float] = Field(default_factory=list)
    pending: list[float] = Field(default_factory=list)
    best_score: float | None = None


class ExplicitSearchParameters(Contract):
    initial: dict[str, float | str]
    bounds: dict[str, ParameterDomain]
    candidates: list[dict[str, float | str]] = Field(min_length=1, max_length=12)

    @property
    def max_trials(self): return len(self.candidates)


class OptimizationRequest(Contract):
    session: SessionInput
    template: str | None = None
    variables: dict[str, tuple[float, float]]
    method: Literal['bounded_coordinate_pattern_local_v1'] = 'bounded_coordinate_pattern_local_v1'
    max_trials: int = Field(default=3, ge=1)
    step: float = Field(default=.2, gt=0, le=1)


class CoordinateSearch:
    def __init__(self, parameters):
        self.parameters=parameters
        self.space=ParameterSpace(list(parameters.initial),parameters.bounds)
        self.state=SearchState(best=self.space.encode(parameters.initial))

    def propose(self):
        s=self.state
        pending=(list(s.best) if s.proposed==0 else coordinate_proposal(
            dict(best=s.best,iteration=s.proposed-1,step=self.parameters.step))['x'])
        self.state=s.model_copy(update=dict(pending=pending,proposed=s.proposed+1))
        return self.space.decode(pending)

    def feedback(self, score):
        if score is not None and (self.state.best_score is None or score<self.state.best_score):
            self.state=self.state.model_copy(update=dict(best_score=score,best=list(self.state.pending)))

    def stopped(self): return self.state.proposed>=self.parameters.max_trials
    def save(self): return Payload(contract='family.search_state',data=plain(self.state))
    def restore(self, state): self.state=SearchState.model_validate(state)


class ExplicitSearch(CoordinateSearch):
    """Finite ask/tell sequence; feedback ranks results without moving points."""
    def __init__(self, parameters):
        super().__init__(parameters)
        for point in parameters.candidates:
            if set(point)!=set(parameters.initial): raise ValueError('EXPLICIT_CANDIDATE_PATHS_MISMATCH')
            self.space.encode(point)

    def propose(self):
        if self.stopped(): raise ValueError('EXPLICIT_PROPOSAL_LIMIT')
        point=dict(self.parameters.candidates[self.state.proposed])
        self.state=self.state.model_copy(update=dict(pending=self.space.encode(point),proposed=self.state.proposed+1))
        return point


def batch_search(method, parameters):
    if method=='search.family_coordinate@1.0.0':
        return CoordinateSearch(SearchParameters.model_validate(parameters))
    if method=='search.family_explicit@1.0.0':
        return ExplicitSearch(ExplicitSearchParameters.model_validate(parameters))
    raise ValueError('BATCH_SEARCH_METHOD_UNAVAILABLE')


def prepare_optimization(value):
    from tools.platform_registry import registry
    from tools.platform_tools import _candidate
    from tools.platform_tasks import compile_input
    from .candidate import read_parameter
    from .contracts import Space, Control, GVSLQRControl
    request=OptimizationRequest.model_validate(value)
    inp=request.session
    if inp.policy.candidate_builder.extension_id!='candidate.family':
        raise ValueError('FAMILY_CANDIDATE_BUILDER_REQUIRED')
    inp=_candidate(inp,{'template':request.template} if request.template else {},registry())
    space=Space.model_validate(inp.policy.candidate_builder.parameters.data)
    initial={}
    for path,bounds in request.variables.items():
        control=path.startswith('control/')
        spec=(space.control_parameters if control else space.parameters).get(path)
        if spec is None or spec['type']!='number' or path.startswith('discretization/'):
            raise ValueError('CONTINUOUS_PHYSICAL_OR_CONTROL_VARIABLE_REQUIRED: '+path)
        lo,hi=bounds
        if not spec['bounds'][0]<=lo<hi<=spec['bounds'][1]:
            raise ValueError('OPTIMIZATION_BOUNDS_OUTSIDE_AUTHORIZED_SPACE: '+path)
        from .contracts import GVSTrajectoryParameters
        control_type=GVSTrajectoryParameters if inp.policy.controller.extension_id=='controller.gvs_nmpc' else GVSLQRControl if inp.policy.controller.extension_id in ('controller.gvs_lqr','controller.gvs_sampled_lqr') else Control
        target=control_type.model_validate(inp.policy.controller.parameters.data).model_dump(mode='json') if control else inp.robot.structure.data
        initial[path]=read_parameter(target,path.removeprefix('control/') if control else path)
    parameters=SearchParameters(initial=initial,bounds=request.variables,max_trials=request.max_trials,step=request.step)
    CoordinateSearch(parameters)  # checks the baseline against the requested bounds
    binding=Binding(extension_id='search.family_coordinate',parameters=Payload(contract='family.search',data=plain(parameters)))
    inp=inp.model_copy(update={'policy':inp.policy.model_copy(update={'search':binding})})
    compile_input(plain(inp))
    return request,inp


def ensure_session(host, inp, *, parent_run_id=None, parent_event_id=None):
    """One normalized input comparison for optimization and independent review."""
    from tools.platform_tasks import compile_input
    normalized=compile_input(plain(inp),host.reg)['input']
    try: existing=host.store.session(host.run_id)
    except ValueError: existing=None
    if existing is None:
        return host.create(normalized,parent_run_id=parent_run_id,parent_event_id=parent_event_id)
    previous=compile_input(existing['snapshot']['input'],host.reg)['input']
    if previous!=normalized or existing['snapshot'].get('parent_run_id')!=parent_run_id:
        raise ValueError('SESSION_INPUT_CHANGED: use a new session identity')
    return existing


def optimize(root, value, *, parent_run_id=None, parent_event_id=None, starting_trial=None, actor='local-human'):
    from tools.platform_host import Host
    from tools.platform_search import run_search
    from tools.state_io import atomic_json, digest
    request,inp=prepare_optimization(value)
    host=Host(root,inp.run_id,actor=actor)
    ensure_session(host,inp,parent_run_id=parent_run_id,parent_event_id=parent_event_id)
    with host.store.transaction() as db:
        state=host.store.session(inp.run_id,db)['state']
        if 'optimization_request' not in state:
            ref=host.store.put(db,request);state['optimization_request']=plain(ref)
            state['optimization_start']=starting_trial
            host.store.update_state(db,inp.run_id,state)
            host.store.event(db,inp.run_id,'optimization','prepared',parent=parent_event_id,outputs=[ref])
    atomic_json(Path(root)/(inp.run_id+'_optimization_request.json'),plain(request))
    outcome=run_search(host,host.store.session(inp.run_id)['state'].get('optimization_start'))
    outcome.update(run_id=inp.run_id,method=request.method,template=request.template,
        variables=plain(request)['variables'],objectives=plain(inp.task)['objectives'],
        constraint_authority=plain(inp.task.evaluator),task_identity=digest(plain(inp.task)),
        usage=host.store.remaining(inp.run_id)['used'],
        attribution='Combined physical design and controller configuration; no isolated causal claim')
    for key in ('baseline','best'):
        trial=outcome.get(key)
        if trial and trial.get('simulation'):
            eid=trial['simulation']['execution_id']
            metadata=host.store.session(trial.get('owner_run_id',inp.run_id))['state']['result_executions'][eid]
            trial['configuration']=metadata['candidate_input']
            trial['evaluation_data']=host.store.artifact(trial['evaluation'])
            data=host.store.artifact(trial['simulation']['output'])['data']['data']
            trial['execution_plan']=data.get('execution_plan')
    if outcome.get('baseline') and outcome.get('best') and outcome['baseline'].get('score') is not None:
        outcome['best_minus_baseline_rank_score']=outcome['best']['score']-outcome['baseline']['score']
    atomic_json(Path(root)/(inp.run_id+'_optimization.json'),outcome)
    return outcome


def covered_search_start(initial,bounds):
    """Project a search seed onto the experiment domain before any evaluation.

    Keep the existing coordinate method; this only supplies an eligible start.
    Equal-distance projections choose the lower value deterministically.
    """
    result=dict(initial)
    def choices(path,baseline,delta):
        lo,hi=bounds[path]
        return [v for v in (lo,hi,baseline-delta,baseline+delta)
            if lo<=v<=hi and abs(v-baseline)>=delta-1e-12]
    section='design/section_scale'
    if section not in result:raise ValueError('COVERAGE_SEARCH_REQUIRES_SECTION_VARIABLE')
    if abs(result[section]-1.)<.01-1e-12:
        options=choices(section,1.,.01)
        if not options:raise ValueError('COVERAGE_SEARCH_HAS_NO_ELIGIBLE_SECTION')
        result[section]=min(options,key=lambda v:(abs(v-result[section]),v))
    lengths=[(path,base) for path,base in (('components/near/length_m',.16),
        ('components/far/length_m',.12)) if path in result]
    if not any(abs(result[path]-base)>=.001-1e-12 for path,base in lengths):
        options=[(abs(v-result[path])/(bounds[path][1]-bounds[path][0]),path,v)
            for path,base in lengths for v in choices(path,base,.001)]
        if not options:raise ValueError('COVERAGE_SEARCH_HAS_NO_ELIGIBLE_LENGTH')
        _,path,value=min(options);result[path]=value
    return result


def optimize_math(ctx,args):
    """Deterministic configuration-only search; never calls NMPC or a backend."""
    from copy import deepcopy
    import math
    import numpy as np
    from schemas.platform_analysis import (EndpointLinearizedModel, EndpointTarget, MathOptimizationResult,
        TaskAnalysisProtocol)
    from tools.platform_tasks import compile_input
    from tools.platform_tools import _candidate
    from tools.state_io import digest
    from extensions.math_analysis.kernels import bounded_endpoint, endpoint_map, _output_endpoint, LIMITATIONS
    from .candidate import read_parameter
    from .candidate_analysis import (configuration_binding, resolve_candidate, scientific_configuration,
        scientific_configuration_identity)
    from .math_analysis import linearize_candidate_configuration, _validate_task_protocol

    start,start_binding=resolve_candidate(ctx,args.source_node)
    route_data=ctx.input.policy.route.data if ctx.input.policy.route is not None else {}
    evaluation_limit=int(route_data.get('math_evaluation_limit',24))
    if args.max_evaluations>evaluation_limit: raise ValueError('ROUTE_MATH_EVALUATION_LIMIT')

    def current_ledger(db=None):
        if db is None:
            with ctx.store.transaction() as conn: return current_ledger(conn)
        state=ctx.store.session(ctx.run_id,db)['state'];route=state['route']
        ledger=route.setdefault('math_evaluations',dict(limit=evaluation_limit,used=0,
            remaining=evaluation_limit,cache={},attempts=[]))
        if ledger['limit']!=evaluation_limit: raise ValueError('ROUTE_MATH_EVALUATION_LEDGER_LIMIT_MISMATCH')
        ledger['remaining']=max(0,evaluation_limit-ledger['used'])
        ctx.store.update_state(db,ctx.run_id,state)
        return deepcopy(ledger)

    def begin_evaluation(identity,scenario,values):
        with ctx.store.transaction() as db:
            ledger=current_ledger(db)
            if identity in ledger['cache']: return deepcopy(ledger['cache'][identity]),False
            if ledger['used']>=ledger['limit']: raise ValueError('ROUTE_MATH_EVALUATION_BUDGET_EXHAUSTED')
            ledger['used']+=1;ledger['remaining']=ledger['limit']-ledger['used']
            ledger['attempts'].append(dict(identity=identity,scenario=scenario,parameters=values,
                request_id=ctx.request.request_id,status='started',ordinal=ledger['used']))
            state=ctx.store.session(ctx.run_id,db)['state'];state['route']['math_evaluations']=ledger
            ctx.store.update_state(db,ctx.run_id,state)
            return None,True

    def finish_evaluation(identity,row,status,error=None):
        with ctx.store.transaction() as db:
            ledger=current_ledger(db)
            attempt=next(item for item in reversed(ledger['attempts'])
                if item['identity']==identity and item['status']=='started')
            attempt['status']=status
            if error is not None: attempt['error']=str(error)
            if status=='completed': ledger['cache'][identity]=deepcopy(row)
            state=ctx.store.session(ctx.run_id,db)['state'];state['route']['math_evaluations']=ledger
            ctx.store.update_state(db,ctx.run_id,state)

    current_ledger()
    p=TaskAnalysisProtocol.model_validate(ctx.artifact(args.protocol)); _validate_task_protocol(start,p)
    target=EndpointTarget.model_validate(ctx.artifact(args.target))
    if not np.allclose(target.position_m,start.task.goal.data['target_m'],rtol=0,atol=p.endpoint_check_atol):
        raise ValueError('MATH_OPTIMIZER_TARGET_MISMATCH')
    if not np.isclose(target.position_tolerance_m,start.task.evaluator.parameters.data['tolerance_m'],rtol=0,atol=p.endpoint_check_atol):
        raise ValueError('MATH_OPTIMIZER_REACH_TOLERANCE_MISMATCH')
    space_spec=start.policy.candidate_builder.parameters.data['parameters']
    for path,bounds in args.variables.items():
        spec=space_spec.get(path)
        if spec is None or spec.get('type')!='number' or not spec['bounds'][0]<=bounds[0]<bounds[1]<=spec['bounds'][1]:
            raise ValueError('MATH_OPTIMIZER_BOUNDS_OUTSIDE_AUTHORIZED_SPACE: '+path)
    initial={path:read_parameter(start.robot.structure.data,path) if not path.startswith('design/')
        else start.robot.structure.data.get('metadata',{}).get('design_decisions',{}).get('selections',{}).get(path,
            start.policy.candidate_builder.parameters.data['semantic_decisions'][path]['baseline_value'])
        for path in args.variables}
    parameter_space=ParameterSpace(list(args.variables),args.variables)
    coverage_required=route_data.get('multi_category_coverage_required',False)
    historical_parameters=[]
    if coverage_required and route_data.get('historical_case'):
        from .historical_failure import cases
        historical_parameters=[{r['path']:r['effective_value'] for r in c['candidate_facts']['parameters']}
            for c in cases(ctx.artifact(route_data['historical_case']))]
    if coverage_required:
        initial=covered_search_start(initial,args.variables)
    initial_vector=parameter_space.encode(initial)
    evaluations=[];seen=set();new_evaluations=0;cache_hits=0
    states={scenario:dict(best=list(initial_vector),best_key=None,iteration=0)
        for scenario in args.material_scenarios}
    evidence=[start_binding['configuration'],plain(args.protocol),plain(args.target)]
    primary_resolution=p.endpoint_check_atol/target.position_tolerance_m

    def key_for(objective):
        residual=objective.get('position_residual_upper_bound_ratio')
        energy=objective.get('feasible_witness_normalized_input_energy')
        ordered_residual=math.inf if residual is None else 0. if residual<=primary_resolution else residual
        return (ordered_residual,math.inf if energy is None else energy)

    def evaluate(scenario,vector):
        nonlocal new_evaluations,cache_hits
        values=parameter_space.decode(vector)
        changes={**values,'design/material_scenario':scenario}
        candidate=_candidate(start,changes,ctx.reg); data=plain(candidate)
        data['run_id']=start.run_id[:32]+'-math-'+digest(dict(scenario=scenario,values=values))[:16]
        compiled=compile_input(data,ctx.reg)['input'];candidate=type(start).model_validate(compiled)
        scientific_id=scientific_configuration_identity(candidate)
        identity=digest(dict(scientific_configuration=scientific_configuration(candidate),
            protocol=plain(p),target=plain(target),objective=args.objective))
        cached,_=begin_evaluation(identity,scenario,values)
        if cached is not None:
            row=deepcopy(cached);row['cache_hit']=True
            row['reused_by_request_id']=ctx.request.request_id
            cache_hits+=1
            added=identity not in seen
            if identity not in seen:
                row['evaluation_index']=len(evaluations)+1;evaluations.append(row);seen.add(identity)
                for ref in (row.get('configuration'),row.get('linearization'),row.get('controller_start_endpoint')):
                    if ref and ref not in evidence:evidence.append(ref)
            return row,added
        try:
            configuration=plain(ctx.save_artifact(compiled,'math_optimizer_configuration'))
            candidate_id='math-'+scenario+'-'+scientific_id[:12]
            binding=configuration_binding(candidate,configuration,candidate_id,ctx.run_id,
                'design.optimize_math:'+args.source_node)
            linear=linearize_candidate_configuration(ctx,candidate,binding,p,args.protocol)
            linear_ref=plain(ctx.save_artifact(linear,'math_optimizer_linearization'))
            point=next((item for item in linear.records[1:] if item.get('model') and
                item['point'].get('name')=='controller_start_input'),None)
            endpoint=None; endpoint_ref=None; objective=dict(position_residual_upper_bound_ratio=None,
                feasible_witness_normalized_input_energy=None,applicability='unavailable')
            if point is not None:
                model=EndpointLinearizedModel.model_validate(ctx.artifact(point['model']))
                endpoint=bounded_endpoint(model,p,target,braking=False)
                endpoint_ref=plain(ctx.save_artifact(endpoint,'math_optimizer_endpoint'))
                residual=endpoint['independent_residual_problems']['position']['candidate_residual']
                mapping=endpoint_map(model,model.operating_point['remaining_task_s'],p.period_s,p.horizon_alignment_atol_s)
                _,_,position_map=_output_endpoint(model,mapping,'tip_position');world_x=np.asarray(position_map)[0]
                objective=dict(position_residual_upper_bound_ratio=residual/target.position_tolerance_m,
                    feasible_witness_normalized_input_energy=endpoint['normalized_input_energy']
                        if endpoint['status']=='feasible_in_local_model' else None,
                    applicability='controller-start frozen local affine exact-ZOH model',
                    scope='position endpoint only; terminal braking and other sampled configurations are not objective terms',
                    status=endpoint['status'],candidate_residual_m=residual,
                    residual_role='upper bound on the bounded minimum; not an infeasibility proof',
                    position_tolerance_m=target.position_tolerance_m,
                    matrix_evidence=dict(world_x_position_control_row_shape=list(world_x.shape),
                        world_x_position_control_row_linf=float(np.max(np.abs(world_x))),
                        world_x_position_control_nonzero_count=int(np.count_nonzero(world_x))))
            compact_binding={key:binding[key] for key in ('source_node','candidate_id','configuration','owner_run_id',
                'effective_configuration_identity','scientific_configuration_identity','robot_identity','task_identity',
                'model','target_m','task_duration_s','control_period_s','physics_timestep_s','tendon_order','tension_bounds_n')}
            row=dict(evaluation_index=len(evaluations)+1,candidate_id=candidate_id,configuration=configuration,
                build_identity=identity,scientific_configuration_identity=scientific_id,
                material_scenario=scenario,parameters=values,candidate_binding=compact_binding,
                linearization=linear_ref,controller_start_endpoint=endpoint_ref,
                endpoint_summary=None if endpoint is None else dict(question=endpoint['question'],status=endpoint['status'],
                    sampled_horizon=endpoint['sampled_horizon'],checks=endpoint['checks'],
                    position_error_m=endpoint['endpoint']['position_error_m'],tip_speed_m_s=endpoint['endpoint']['tip_speed_m_s'],
                    certificate=endpoint['infeasibility_certificate']),objective=objective,
                unavailable_constructions=[r.get('name') for r in linear.records[1:] if not r.get('available',False)],
                cache_hit=False,producer_request_id=ctx.request.request_id,
                backend_executed=False,nmpc_solved=False,provider_called=False)
            if coverage_required:
                from .candidate import candidate_facts,experiment_coverage
                facts=candidate_facts(ctx.input,compiled,configuration,candidate_id)
                row['coverage']=experiment_coverage(facts)
                row['historical_duplicate']={r['path']:r['effective_value'] for r in facts['parameters']} in historical_parameters
            finish_evaluation(identity,row,'completed');new_evaluations+=1
        except Exception as exc:
            finish_evaluation(identity,{},'failed',exc);raise
        evaluations.append(row);seen.add(identity);evidence.extend([configuration,linear_ref]);
        if endpoint_ref: evidence.append(endpoint_ref)
        return row,True

    # One explicit start per discrete scenario, then bounded coordinate moves.
    for scenario in args.material_scenarios:
        try: row,_=evaluate(scenario,initial_vector)
        except ValueError as exc:
            if 'ROUTE_MATH_EVALUATION_BUDGET_EXHAUSTED' in str(exc): break
            raise
        states[scenario]['best_key']=key_for(row['objective'])
    if any(state['best_key'] is None for state in states.values()):
        raise ValueError('ROUTE_MATH_EVALUATION_BUDGET_EXHAUSTED_BEFORE_ALL_SCENARIO_STARTS')
    attempts=0
    budget_exhausted=False
    while new_evaluations<args.max_evaluations and attempts<args.max_evaluations*12:
        scenario=args.material_scenarios[attempts%len(args.material_scenarios)]; state=states[scenario]
        phase=state['iteration']//(2*len(initial_vector)); step=.5 if phase==0 else .25
        proposal=coordinate_proposal(dict(best=state['best'],iteration=state['iteration'],step=step))['x']
        state['iteration']+=1; attempts+=1
        try: row,added=evaluate(scenario,proposal)
        except ValueError as exc:
            if 'ROUTE_MATH_EVALUATION_BUDGET_EXHAUSTED' in str(exc): budget_exhausted=True;break
            raise
        if not added: continue
        candidate_key=key_for(row['objective'])
        if candidate_key<state['best_key']:
            state['best']=list(proposal);state['best_key']=candidate_key
    def tied(a,b):
        ka,kb=key_for(a['objective']),key_for(b['objective'])
        return abs(ka[0]-kb[0])<=p.endpoint_check_atol/target.position_tolerance_m and (
            (math.isinf(ka[1]) and math.isinf(kb[1])) or abs(ka[1]-kb[1])<=p.endpoint_check_atol)
    proposals=[]
    for scenario in args.material_scenarios:
        rows=[row for row in evaluations if row['material_scenario']==scenario and
            (not coverage_required or (row.get('coverage',{}).get('eligible') and not row.get('historical_duplicate')))]
        if not rows:continue
        best=min(rows,key=lambda row:key_for(row['objective']))
        tied_rows=[row for row in rows if tied(row,best)]
        proposals.append(dict(material_scenario=scenario,candidate_id=best['candidate_id'],
            configuration=best['configuration'],parameters=best['parameters'],objective=best['objective'],
            tied_candidate_ids=[row['candidate_id'] for row in tied_rows],
            selection_rationale='Lowest declared residual-upper-bound ratio; feasible local input energy is a secondary lexicographic component only.'))
    grouped={}
    for row in evaluations:
        grouped.setdefault(tuple(sorted(row['parameters'].items())),{})[row['material_scenario']]=row['objective'].get('position_residual_upper_bound_ratio')
    material_pairs=[values for values in grouped.values() if set(values)==set(args.material_scenarios)]
    ratios=[row['objective'].get('position_residual_upper_bound_ratio') for row in evaluations
        if row['objective'].get('position_residual_upper_bound_ratio') is not None]
    ledger=current_ledger()
    return MathOptimizationResult(starting_binding=start_binding,protocol=args.protocol,target=args.target,
        objective=dict(objective_id=args.objective,primary=dict(name='controller_start_bounded_position_residual_upper_bound_ratio',
            definition='SciPy bounded least-squares position candidate residual divided by official reach tolerance; terminal braking is excluded',units='1',direction='minimize'),
            secondary=dict(name='feasible_position_witness_normalized_input_energy',
                definition='Exact-ZOH held-input sum(period * ||delta_u/input_scale||^2), used only after primary ordering',
                units='s (normalized input squared integral)',direction='minimize'),
            ordering='lexicographic; primary values within endpoint_check_atol/tolerance are tied; no fitted weights or historical outcomes',
            primary_tie_resolution=primary_resolution,operating_point='controller_start_input',
            sampled_configuration_aggregation='none; only controller_start_input contributes to the objective',
            terminal_braking_in_objective=False,observed_scope_evidence=dict(
                all_world_x_position_control_rows_zero=all(row['objective'].get('matrix_evidence',{}).get(
                    'world_x_position_control_nonzero_count')==0 for row in evaluations if row['objective'].get('matrix_evidence')),
                material_pair_primary_ratios_equal=bool(material_pairs) and all(len(set(values.values()))==1 for values in material_pairs),
                observed_primary_ratio_range=[min(ratios),max(ratios)] if ratios else None,
                interpretation='Observed values describe only this bounded sample and local model; they do not predict nonlinear bending or closed-loop performance.')),
        bounds=args.variables,material_scenarios=args.material_scenarios,evaluations=evaluations,proposals=proposals,
        provenance=dict(method='bounded_coordinate_pattern_local_v1',deterministic=True,seed=None,
            requested_new_evaluation_cap=args.max_evaluations,new_evaluations_this_call=new_evaluations,
            coverage_required=coverage_required,evaluated_start_parameters=initial,
            cache_hits_this_call=cache_hits,returned_scientific_configurations=len(evaluations),iterations=attempts,
            cumulative_evaluation_limit=ledger['limit'],cumulative_evaluations_used=ledger['used'],
            cumulative_evaluations_remaining=ledger['remaining'],failed_evaluations_counted=sum(
                item['status']=='failed' for item in ledger['attempts']),
            stop_reason='cumulative_evaluation_budget' if budget_exhausted else
                'requested_evaluation_cap' if new_evaluations>=args.max_evaluations else 'no_new_distinct_proposals',
            implementation_identity=digest(dict(source=__file__,objective=args.objective,protocol=plain(p))),
            physical_backend_calls=0,nmpc_solves=0,provider_calls=0),evidence=evidence,
        limitations=LIMITATIONS+['The objective can favor geometric alignment at the straight controller-start configuration; it does not predict nonlinear bending, closed-loop reach, settling, real-time performance, or global optimality.',
            'Terminal braking and other sampled configurations are not aggregated into this optimization objective.',
            'Candidate residuals are upper bounds; only explicit separating-direction records may certify local infeasibility.',
            'Scenario winners and ties are bounded-search proposals, not global optima.'])
