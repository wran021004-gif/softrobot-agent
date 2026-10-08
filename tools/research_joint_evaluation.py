"""Public composition of sealed evaluation/profile/motion; no backend execution."""
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.state_io import digest


class JointEvaluation(Contract):
    configuration: EvidenceRef
    evaluation: EvidenceRef
    profile: EvidenceRef


class JointResult(Contract):
    detail: dict


def evaluate(ctx,args):
    from tools.research_tasks import assemble_acceptance
    cfg=ctx.artifact(args.configuration);ev=ctx.artifact(args.evaluation);profile=ctx.artifact(args.profile)
    detail=profile['detail'];motion=ctx.artifact(detail['motion'])
    if cfg.get('content_identity') != digest(cfg['effective']):raise ValueError('JOINT_CONFIGURATION_CONTENT_CHANGED')
    if detail['configuration']!=plain(args.configuration):raise ValueError('JOINT_CONFIGURATION_BINDING_MISMATCH')
    result=assemble_acceptance(cfg,ev,profile,evaluation_reference=args.evaluation,profile_reference=args.profile,motion=motion)
    result.update(configuration=plain(args.configuration),official_recorded_task_success=ev['task_success'],
        composition_authority='research.task_acceptance@1.0.0; historical official evaluation retained separately',new_backend_solves=0)
    return JointResult(detail=result)


def preflight(inp,args,reg):return dict(cost=dict(wall_s=0.))
