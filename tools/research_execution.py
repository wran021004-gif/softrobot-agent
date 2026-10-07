"""Shared candidate/request services. Construction never executes the request."""
from copy import deepcopy
from schemas.platform import SessionInput, ToolRequest
from schemas.platform_operations import Simulate
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.state_io import digest
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, CandidateInput


class CandidatePreparation(Contract):
    candidate_id: str = Field(min_length=1,max_length=100)
    changes: dict[str,object] = Field(default_factory=dict)


class PreparedCandidate(Contract):
    configuration: EvidenceRef
    content_identity: str
    scope: str = 'Construction and request preparation only; scientific execution pending'


class ConfigurationAnalysis(Contract):
    configuration: EvidenceRef
    expected_content_identity: str
    protocol: EvidenceRef


def prepare_candidate_tool(ctx,args):
    result=prepare_execution_request(ctx.input,args.changes,candidate_id=args.candidate_id,reg=ctx.reg)
    return PreparedCandidate(configuration=ctx.save_artifact(result['candidate'],'prepared_candidate'),
        content_identity=result['candidate']['content_identity'])


def linearize_configuration(ctx,args):
    from extensions.tendon_family.candidate_analysis import configuration_binding
    from extensions.tendon_family.math_analysis import linearize_candidate_configuration
    from schemas.platform_analysis import TaskAnalysisProtocol
    candidate=CandidateInput.model_validate(ctx.artifact(args.configuration))
    if candidate.baseline_identity!=digest(plain(ctx.input)) or candidate.content_identity!=args.expected_content_identity:
        raise ValueError('ANALYSIS_OWNED_CANDIDATE_BINDING_MISMATCH')
    if digest(plain(candidate.effective))!=candidate.content_identity:raise ValueError('ANALYSIS_CANDIDATE_CONTENT_CHANGED')
    if candidate.effective.task.family!='task.reach':raise ValueError('CONFIGURATION_ANALYSIS_REACH_ONLY')
    binding=configuration_binding(candidate.effective,args.configuration,candidate.candidate_id,ctx.run_id,'prepared-configuration')
    protocol=TaskAnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    result=linearize_candidate_configuration(ctx,candidate.effective,binding,protocol,args.protocol)
    return result.model_copy(update={'limitations':[
        item for item in result.limitations if not item.startswith('Retrospective emulation')]+[
        'Owned candidate configuration-only analysis; no execution outcomes or trajectories were used.']})


def construct_candidate(configuration, changes, reg=None):
    from tools.platform_tools import _candidate
    return _candidate(SessionInput.model_validate(configuration), changes, reg or registry())


def prepare_execution_request(configuration, changes, *, candidate_id, request_id='simulation', reg=None):
    from tools.platform_tools import simulation_preflight
    inp = SessionInput.model_validate(configuration); reg = reg or registry()
    arguments = Simulate(candidate_id=candidate_id, changes=changes)
    result = simulation_preflight(inp, arguments, reg)
    candidate = result['prepared'].effective
    return dict(request=plain(ToolRequest(request_id=request_id, tool_id='simulation.run',
        arguments=plain(arguments), reason='Execute the exact constructed candidate under its frozen task and activity grant.', cache='new')),
        candidate=plain(result['prepared']), cost=result['cost'], resources=result['resources'],
        identity=digest(plain(result['prepared'])), task=plain(candidate.task),
        preparation_scope='Actual mutation, compatibility, compiler and request construction; no trajectory execution',
        scientific_preparation=dict(warm_trajectory_regeneration='pending_execution',
            controller_solve='pending_execution', backend_execution='pending_execution'))


def invoke(host, tool_id, arguments, *, request_id, evidence=(), reason='Frozen activity operation'):
    """Same Host authority, dependency freeze, accounting and failure boundary."""
    policy=host.store.session(host.run_id)['snapshot']['input']['policy']
    version=policy['tool_bindings'].get(tool_id)
    if version is None: raise ValueError('OPERATION_NOT_AUTHORIZED: '+tool_id)
    return host.invoke(plain(ToolRequest(request_id=request_id,tool_id=tool_id,tool_version=version,
        arguments=deepcopy(arguments),reason=reason,evidence=list(evidence),cache='new')))


def analysis_request(host, method, arguments, *, request_id, evidence=()):
    definition=host.reg.get(method,host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings'][method],'tool')
    if definition.capabilities.get('category') != 'analysis': raise ValueError('MATHEMATICAL_TOOL_REQUIRED')
    return invoke(host,method,arguments,request_id=request_id,evidence=evidence,
        reason='Candidate-local computation under an explicit grant; local evidence does not establish nonlinear or global feasibility.')


def replay_analysis(value, *, expected_binding, protocol, upstream=()):
    """Read exact historical analysis; never rebind it onto changed routing."""
    bindings=value.get('bindings',[value.get('binding')])
    if expected_binding not in bindings or value.get('protocol') != protocol:
        raise ValueError('HISTORICAL_ANALYSIS_BINDING_MISMATCH')
    if value.get('upstream',value.get('evidence',[])) != list(upstream): raise ValueError('HISTORICAL_ANALYSIS_UPSTREAM_MISMATCH')
    return dict(operation='historical_read_only', scientific_computation=False, value=deepcopy(value),
        limitations='Saved local evidence applies only to its bound candidate, working point, model, task and protocol.')
