"""A new evaluation session can consume a compatible, sealed producer result."""
import json
from pydantic import Field
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import BackendResult, EvidenceRef, SessionInput
from tools.state_io import digest


class SavedEvaluation(Contract):
    source_run_id: Identifier
    execution_id: str = Field(min_length=1)
    result: EvidenceRef


def evaluate_saved(ctx,args):
    from tools.platform_host import Host
    source_host=Host(ctx.store.root,args.source_run_id,reg=ctx.reg)
    compatibility=source_host.compatibility()
    if not compatibility['compatible']:
        raise ValueError('SOURCE_DEPENDENCIES_CHANGED: '+repr(compatibility['changed']))
    source=ctx.store.session(args.source_run_id)
    snapshot=source['snapshot'];inp=SessionInput.model_validate(snapshot['input'])
    if (snapshot['instance_identity']!=ctx.snapshot['instance_identity']
            or inp.task!=ctx.input.task or inp.robot!=ctx.input.robot
            or inp.policy.backend!=ctx.input.policy.backend):
        raise ValueError('SAVED_EVALUATION_CONTEXT_MISMATCH')
    metadata=source['state'].get('result_executions',{}).get(args.execution_id)
    if metadata is None or metadata['artifact_id']!=args.result.artifact_id:
        raise ValueError('RESULT_EXECUTION_MISMATCH')
    producer=ctx.store.lookup(args.source_run_id,metadata['request_id'])
    receipt=json.loads(producer['receipt']) if producer and producer['receipt'] else None
    if (receipt is None or receipt['execution_status']!='completed'
            or receipt['execution_id']!=args.execution_id or receipt.get('output')!=args.result.model_dump(mode='json')):
        raise ValueError('SEALED_PRODUCER_RECEIPT_REQUIRED')
    result=BackendResult.model_validate(ctx.artifact(args.result))
    evaluator,_=ctx.reg.bind(inp.task.evaluator,'evaluator')
    identity=digest(dict(instance=snapshot['instance_identity'],task=inp.task.model_dump(mode='json'),
        evaluator=inp.task.evaluator.model_dump(mode='json'),backend=result.backend_id,model=result.model_id,
        evaluator_dependencies=snapshot['dependencies'][evaluator.extension_id+'@'+evaluator.version],
        backend_dependencies=snapshot['dependencies'][inp.policy.backend.extension_id+'@'+inp.policy.backend.version]))
    outcome=evaluator.resolve()(inp.task,result,args.result,ctx.reg,identity)
    outcome=outcome.model_copy(update=dict(source_execution_id=args.execution_id,
        original_execution_id=metadata['original_execution_id'],candidate_id=metadata['candidate'],evaluator_version=evaluator.version))
    ctx.record('saved_evaluation_source','verified',inputs=[args.result,metadata['candidate_input']],candidate=metadata['candidate'])
    return outcome
