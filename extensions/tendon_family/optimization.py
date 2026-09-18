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
    from .contracts import Space, Control
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
        target=Control.model_validate(inp.policy.controller.parameters.data).model_dump(mode='json') if control else inp.robot.structure.data
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


def optimize(root, value, *, parent_run_id=None, parent_event_id=None):
    from tools.platform_host import Host
    from tools.platform_search import run_search
    from tools.state_io import atomic_json, digest
    request,inp=prepare_optimization(value)
    host=Host(root,inp.run_id)
    ensure_session(host,inp,parent_run_id=parent_run_id,parent_event_id=parent_event_id)
    with host.store.transaction() as db:
        state=host.store.session(inp.run_id,db)['state']
        if 'optimization_request' not in state:
            ref=host.store.put(db,request);state['optimization_request']=plain(ref)
            host.store.update_state(db,inp.run_id,state)
            host.store.event(db,inp.run_id,'optimization','prepared',parent=parent_event_id,outputs=[ref])
    atomic_json(Path(root)/(inp.run_id+'_optimization_request.json'),plain(request))
    outcome=run_search(host)
    outcome.update(run_id=inp.run_id,method=request.method,template=request.template,
        variables=plain(request)['variables'],objectives=plain(inp.task)['objectives'],
        constraint_authority=plain(inp.task.evaluator),task_identity=digest(plain(inp.task)),
        usage=host.store.remaining(inp.run_id)['used'],
        attribution='Combined physical design and controller configuration; no isolated causal claim')
    for key in ('baseline','best'):
        trial=outcome.get(key)
        if trial and trial.get('simulation'):
            eid=trial['simulation']['execution_id']
            metadata=host.store.session(inp.run_id)['state']['result_executions'][eid]
            trial['configuration']=metadata['candidate_input']
            trial['evaluation_data']=host.store.artifact(trial['evaluation'])
            data=host.store.artifact(trial['simulation']['output'])['data']['data']
            trial['execution_plan']=data.get('execution_plan')
    if outcome.get('baseline') and outcome.get('best') and outcome['baseline'].get('score') is not None:
        outcome['best_minus_baseline_rank_score']=outcome['best']['score']-outcome['baseline']['score']
    atomic_json(Path(root)/(inp.run_id+'_optimization.json'),outcome)
    return outcome
