"""Explicit owned build binding for pre-execution GVS mathematics."""
from types import SimpleNamespace
from pydantic import Field
from schemas.common import Contract
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import GVSDynamicsRequestV2


class CandidateDynamicsRequest(GVSDynamicsRequestV2):
    source_node: str = Field(description='Completed build node in this Route session. Analysis uses its immutable effective configuration, never the selected incumbent or parent robot. Basis comes from the frozen controller.')


class CandidateAnalysisResult(Contract):
    binding: dict
    calculation: dict


def resolve_candidate(ctx, source_node):
    state=ctx.store.session(ctx.run_id)['state']
    node=next((n for n in state.get('route',{}).get('nodes',[]) if n['node_id']==source_node
        and n['action']=='build' and n['status']=='completed'),None)
    if node is None:
        raise ValueError('OWNED_COMPLETED_BUILD_REQUIRED')
    built=ctx.artifact(node['result'])
    inp=SessionInput.model_validate(ctx.artifact(built['configuration']))
    if plain(inp.task)!=plain(ctx.input.task):
        raise ValueError('CANDIDATE_ANALYSIS_FROZEN_TASK_MISMATCH')
    basis=inp.policy.controller.parameters.data['recipe']['basis']
    from .gvs_basis import resolve_basis
    resolved=resolve_basis(inp.robot.structure.data,basis)
    return inp, dict(source_node=source_node,candidate_id=built['candidate_id'],configuration=built['configuration'],
        owner_run_id=ctx.run_id,effective_configuration_identity=digest(plain(inp)),robot_identity=digest(plain(inp.robot)),
        task_identity=digest(plain(inp.task)),physical_context=plain(inp.task.environment),
        model='model.gvs@1.0.0',basis=plain(resolved),coordinate_order=list(resolved.coordinate_order),
        calculation_frame='robot_base',execution_data_used=False)


def evaluate_candidate(ctx,args):
    from .gvs import gvs_evaluate_tool_v2
    from .contracts import GVSDynamicsRequestV3
    inp,binding=resolve_candidate(ctx,args.source_node)
    request=GVSDynamicsRequestV3(**args.model_dump(exclude={'source_node'}),
        basis=inp.policy.controller.parameters.data['recipe']['basis'])
    result=gvs_evaluate_tool_v2(SimpleNamespace(input=inp,reg=ctx.reg),request)
    return CandidateAnalysisResult(binding=binding,calculation=plain(result))


def require_completed_analysis(ctx, built, tool):
    """A Route run must cite mathematics on this exact owned build first."""
    import json
    with ctx.store.connect(True) as db:
        receipts=[json.loads(r['receipt']) for r in db.execute(
            'SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,))]
    for receipt in receipts:
        if receipt['tool_id']==tool and receipt['execution_status']=='completed' and receipt.get('output'):
            binding=ctx.artifact(receipt['output'])['binding']
            if binding['configuration']==built['configuration'] and binding['candidate_id']==built['candidate_id']:
                return receipt['output']
    raise ValueError('CANDIDATE_BOUND_ANALYSIS_REQUIRED_BEFORE_EXECUTION: '+tool)
