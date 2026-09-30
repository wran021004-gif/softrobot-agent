"""Public bounded optimization using the existing Host, ask/tell and coordinate step."""
from pathlib import Path
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import SessionInput, Payload, Binding
from tools.optimization_interfaces import ParameterSpace, coordinate_proposal
from tools.platform_store import plain


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


def optimize_math(ctx,args):
    """Deterministic configuration-only search; never calls NMPC or a backend."""
    import math
    import numpy as np
    from schemas.platform_analysis import (EndpointLinearizedModel, EndpointTarget, MathOptimizationResult,
        TaskAnalysisProtocol)
    from tools.platform_tasks import compile_input
    from tools.platform_tools import _candidate
    from tools.state_io import digest
    from extensions.math_analysis.kernels import bounded_endpoint, LIMITATIONS
    from .candidate import read_parameter
    from .candidate_analysis import configuration_binding, resolve_candidate
    from .math_analysis import linearize_candidate_configuration, _validate_task_protocol

    start,start_binding=resolve_candidate(ctx,args.source_node)
    route_data=ctx.input.policy.route.data if ctx.input.policy.route is not None else {}
    evaluation_limit=int(route_data.get('math_evaluation_limit',24))
    if args.max_evaluations>evaluation_limit: raise ValueError('ROUTE_MATH_EVALUATION_LIMIT')
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
    initial_vector=parameter_space.encode(initial)
    evaluations=[]; cache={}; states={scenario:dict(best=list(initial_vector),best_key=None,iteration=0)
        for scenario in args.material_scenarios}
    evidence=[start_binding['configuration'],plain(args.protocol),plain(args.target)]
    primary_resolution=p.endpoint_check_atol/target.position_tolerance_m

    def key_for(objective):
        residual=objective.get('position_residual_upper_bound_ratio')
        energy=objective.get('feasible_witness_normalized_input_energy')
        ordered_residual=math.inf if residual is None else 0. if residual<=primary_resolution else residual
        return (ordered_residual,math.inf if energy is None else energy)

    def evaluate(scenario,vector):
        values=parameter_space.decode(vector)
        changes={**values,'design/material_scenario':scenario}
        candidate=_candidate(start,changes,ctx.reg); data=plain(candidate)
        data['run_id']=start.run_id[:32]+'-math-'+digest(dict(scenario=scenario,values=values))[:16]
        compiled=compile_input(data,ctx.reg)['input']; identity=digest(compiled)
        if identity in cache: return cache[identity]
        configuration=plain(ctx.save_artifact(compiled,'math_optimizer_configuration'))
        candidate_id='math-'+scenario+'-'+identity[:12]
        binding=configuration_binding(candidate,configuration,candidate_id,ctx.run_id,
            'design.optimize_math:'+args.source_node)
        linear=linearize_candidate_configuration(ctx,candidate,binding,p,args.protocol)
        linear_ref=plain(ctx.save_artifact(linear,'math_optimizer_linearization'))
        point=next((row for row in linear.records[1:] if row.get('model') and
            row['point'].get('name')=='controller_start_input'),None)
        endpoint=None; endpoint_ref=None; objective=dict(position_residual_upper_bound_ratio=None,
            feasible_witness_normalized_input_energy=None,applicability='unavailable')
        if point is not None:
            model=EndpointLinearizedModel.model_validate(ctx.artifact(point['model']))
            endpoint=bounded_endpoint(model,p,target,braking=False)
            endpoint_ref=plain(ctx.save_artifact(endpoint,'math_optimizer_endpoint'))
            residual=endpoint['independent_residual_problems']['position']['candidate_residual']
            objective=dict(position_residual_upper_bound_ratio=residual/target.position_tolerance_m,
                feasible_witness_normalized_input_energy=endpoint['normalized_input_energy']
                    if endpoint['status']=='feasible_in_local_model' else None,
                applicability='controller-start frozen local affine exact-ZOH model',
                status=endpoint['status'],candidate_residual_m=residual,
                residual_role='upper bound on the bounded minimum; not an infeasibility proof',
                position_tolerance_m=target.position_tolerance_m)
        compact_binding={key:binding[key] for key in ('source_node','candidate_id','configuration','owner_run_id',
            'effective_configuration_identity','robot_identity','task_identity','model','target_m','task_duration_s',
            'control_period_s','physics_timestep_s','tendon_order','tension_bounds_n')}
        row=dict(evaluation_index=len(evaluations)+1,candidate_id=candidate_id,configuration=configuration,
            build_identity=identity,material_scenario=scenario,parameters=values,binding=binding,
            candidate_binding=compact_binding,linearization=linear_ref,controller_start_endpoint=endpoint_ref,
            endpoint_summary=None if endpoint is None else dict(question=endpoint['question'],status=endpoint['status'],
                sampled_horizon=endpoint['sampled_horizon'],checks=endpoint['checks'],
                position_error_m=endpoint['endpoint']['position_error_m'],tip_speed_m_s=endpoint['endpoint']['tip_speed_m_s'],
                certificate=endpoint['infeasibility_certificate']),objective=objective,
            unavailable_constructions=[r.get('name') for r in linear.records[1:] if not r.get('available',False)],
            backend_executed=False,nmpc_solved=False,provider_called=False)
        row.pop('binding')
        evaluations.append(row); evidence.extend([configuration,linear_ref]);
        if endpoint_ref: evidence.append(endpoint_ref)
        cache[identity]=row
        return row

    # One explicit start per discrete scenario, then bounded coordinate moves.
    for scenario in args.material_scenarios:
        if len(evaluations)>=args.max_evaluations: break
        row=evaluate(scenario,initial_vector); states[scenario]['best_key']=key_for(row['objective'])
    attempts=0
    while len(evaluations)<args.max_evaluations and attempts<args.max_evaluations*12:
        scenario=args.material_scenarios[attempts%len(args.material_scenarios)]; state=states[scenario]
        phase=state['iteration']//(2*len(initial_vector)); step=.5 if phase==0 else .25
        proposal=coordinate_proposal(dict(best=state['best'],iteration=state['iteration'],step=step))['x']
        state['iteration']+=1; attempts+=1
        before=len(evaluations); row=evaluate(scenario,proposal)
        if len(evaluations)==before: continue
        candidate_key=key_for(row['objective'])
        if candidate_key<state['best_key']:
            state['best']=list(proposal);state['best_key']=candidate_key
    def tied(a,b):
        ka,kb=key_for(a['objective']),key_for(b['objective'])
        return abs(ka[0]-kb[0])<=p.endpoint_check_atol/target.position_tolerance_m and (
            (math.isinf(ka[1]) and math.isinf(kb[1])) or abs(ka[1]-kb[1])<=p.endpoint_check_atol)
    proposals=[]
    for scenario in args.material_scenarios:
        rows=[row for row in evaluations if row['material_scenario']==scenario]
        best=min(rows,key=lambda row:key_for(row['objective']))
        tied_rows=[row for row in rows if tied(row,best)]
        proposals.append(dict(material_scenario=scenario,candidate_id=best['candidate_id'],
            configuration=best['configuration'],parameters=best['parameters'],objective=best['objective'],
            tied_candidate_ids=[row['candidate_id'] for row in tied_rows],
            selection_rationale='Lowest declared residual-upper-bound ratio; feasible local input energy is a secondary lexicographic component only.'))
    return MathOptimizationResult(starting_binding=start_binding,protocol=args.protocol,target=args.target,
        objective=dict(objective_id=args.objective,primary=dict(name='controller_start_bounded_position_residual_upper_bound_ratio',
            definition='SciPy bounded least-squares candidate residual divided by official reach tolerance',units='1',direction='minimize'),
            secondary=dict(name='feasible_position_witness_normalized_input_energy',
                definition='Exact-ZOH held-input sum(period * ||delta_u/input_scale||^2), used only after primary ordering',
                units='s (normalized input squared integral)',direction='minimize'),
            ordering='lexicographic; primary values within endpoint_check_atol/tolerance are tied; no fitted weights or historical outcomes',
            primary_tie_resolution=primary_resolution,operating_point='controller_start_input'),
        bounds=args.variables,material_scenarios=args.material_scenarios,evaluations=evaluations,proposals=proposals,
        provenance=dict(method='bounded_coordinate_pattern_local_v1',deterministic=True,seed=None,
            evaluation_budget=args.max_evaluations,distinct_evaluations=len(evaluations),iterations=attempts,
            stop_reason='evaluation_budget' if len(evaluations)>=args.max_evaluations else 'no_new_distinct_proposals',
            implementation_identity=digest(dict(source=__file__,objective=args.objective,protocol=plain(p))),
            physical_backend_calls=0,nmpc_solves=0,provider_calls=0),evidence=evidence,
        limitations=LIMITATIONS+['The objective is a local mathematical proxy and does not predict closed-loop success.',
            'Candidate residuals are upper bounds; only explicit separating-direction records may certify local infeasibility.',
            'Scenario winners and ties are bounded-search proposals, not global optima.'])
