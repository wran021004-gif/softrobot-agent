"""Explicit improvement decisions, accepted-report handoff and existing execution tools."""
from typing import Literal
from uuid import uuid4
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, SessionInput, CandidateInput, ToolReceipt
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.state_io import digest


class LocalImprovementComparison(Contract):
    update_id: int = Field(ge=1,description='Saved baseline controller update; effective plan horizon must be 0.01 s.')
    parameter: Literal['terminal_tip_speed_weight','holding_tip_speed_weight']


class ImprovementDecision(Contract):
    """Flat model-authored business fields; host owns all source identities."""
    disposition: Literal['adopt','defer','reject']
    changes: dict[str, object] = Field(default_factory=dict, description='Only paths/values allowed by the existing candidate builder grant.')
    rationale: str = Field(min_length=1)
    expected_measurable_effect: str = Field(min_length=1)
    local_comparison: LocalImprovementComparison | None = Field(default=None,
        description='Optional only when the supplied campaign grant permits it: compare baseline against one selected changed positive weight at a legal saved state. No sweep; omit if unnecessary.')


class ImprovementPreparation(Contract):
    status: Literal['prepared_no_execution','no_change_selected']
    source_execution: str
    source_report: EvidenceRef
    source_configuration: EvidenceRef
    decision: ImprovementDecision
    candidate_id: str | None = None
    configuration: EvidenceRef | None = None
    actual_diff: list[dict] = Field(default_factory=list)
    execution_receipt: ToolReceipt | None = None
    evaluation_receipt: ToolReceipt | None = None
    feedback: EvidenceRef | None = None
    final_delivery: EvidenceRef | None = None
    reporting_dimensions: tuple[str, ...] = ('terminal_reach','holding_window_position_and_speed','complete_update_computation')


def actual_diff(before,after,path=''):
    if isinstance(before,dict) and isinstance(after,dict):
        return [row for key in sorted(before.keys()|after.keys())
                for row in actual_diff(before.get(key),after.get(key),path+'/'+key.replace('~','~0').replace('/','~1'))]
    if isinstance(before,list) and isinstance(after,list) and len(before)==len(after):
        return [row for i,(a,b) in enumerate(zip(before,after)) for row in actual_diff(a,b,path+'/'+str(i))]
    return [] if before==after else [dict(pointer=path,before=before,after=after)]


def prepare_improvement(host, report_reference, decision):
    """Explicit host invocation after a model decision; adoption never invokes it."""
    decision=ImprovementDecision.model_validate(decision)
    require_accepted_report(host, report_reference)
    report=host.store.artifact(report_reference)
    binding=host.store.artifact(report['report']['source'])
    baseline=SessionInput.model_validate(host.store.artifact(binding['configuration'])['effective'])
    result=ImprovementPreparation(status='no_change_selected',source_execution=binding['execution_id'],
        source_report=report_reference,source_configuration=binding['configuration'],decision=decision)
    if decision.disposition!='adopt':
        if decision.changes:raise ValueError('DEFER_OR_REJECT_CANNOT_PREPARE_CHANGES')
        if decision.local_comparison:raise ValueError('LOCAL_PAIR_REQUIRES_ADOPTED_DELTA')
        return result
    if not decision.changes:raise ValueError('ADOPT_REQUIRES_EXPLICIT_DELTA')
    # The family builder can support choice dimensions beyond the session's
    # explicit numeric edit grant. Capability is not improvement authorization.
    outside=set(decision.changes)-set(baseline.policy.editable)
    if outside:raise ValueError('PARAMETER_NOT_AUTHORIZED_IN_IMPROVEMENT_GRANT: '+', '.join(sorted(outside)))
    candidate=_candidate(baseline,decision.changes,registry())
    differences=actual_diff(plain(baseline),plain(candidate))
    if not differences:raise ValueError('EFFECTIVE_CHANGE_REQUIRED')
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    if set(baseline.policy.editable)<=set(REACH_WEIGHT_PATHS):
        permitted={'/policy/controller/parameters/data/'+p.removeprefix('control/') for p in decision.changes}
        if any(row['pointer'] not in permitted for row in differences):
            raise ValueError('CONTROL_ONLY_CANDIDATE_CHANGED_FROZEN_FIELDS')
    identity='improvement-'+uuid4().hex[:12]
    prepared=CandidateInput(candidate_id=identity,baseline_identity=digest(plain(baseline)),
        builder=baseline.policy.candidate_builder.extension_id,builder_version=baseline.policy.candidate_builder.version,
        changes=decision.changes,allowed=baseline.policy.editable,effective=candidate,content_identity=digest(plain(candidate)),
        sources=dict(source_report=plain(report_reference)['artifact_id'],source_execution=binding['execution_id'],
            source_configuration=binding['configuration']['artifact_id']))
    with host.store.transaction() as db:
        configuration=host.store.put(db,prepared)
        result=result.model_copy(update=dict(status='prepared_no_execution',candidate_id=identity,
            configuration=configuration,actual_diff=differences))
        reference=host.store.put(db,result)
        host.store.event(db,host.run_id,'improvement_preparation','prepared_no_execution',
            inputs=[report_reference,binding['configuration']],outputs=[configuration,reference])
    return result


def require_accepted_report(host, reference):
    reference=plain(reference)
    state=host.store.session(host.run_id)['state']
    if any(h['kind']=='diagnosis_report' and h['reference']==reference for h in state.get('handoff_history',[])):
        return
    for proof in state.get('accepted_report_transfers',[]):
        if proof['reference']!=reference:continue
        source=host.store.session(proof['source_context'])['state']
        if any(h['kind']=='diagnosis_report' and h['reference']==reference for h in source.get('handoff_history',[])) and any(
                e['kind']=='role_transition' and e['status']=='diagnosis_report' and reference in e['outputs']
                for e in host.store.events(proof['source_context'])):
            return
    raise ValueError('ACCEPTED_DIAGNOSIS_REQUIRED')


def transfer_accepted_report(source, destination, reference):
    """Transfer one accepted product, never another role's memory or artifact presence."""
    if source.store.root!=destination.store.root:raise ValueError('SAME_PROJECT_HANDOFF_REQUIRED')
    reference=plain(reference)
    require_accepted_report(source,reference)
    events=[e for e in source.store.events(source.run_id) if e['kind']=='role_transition'
        and e['status']=='diagnosis_report' and reference in e['outputs']]
    if not events:raise ValueError('ACCEPTED_REPORT_TRANSITION_REQUIRED')
    proof=dict(reference=reference,source_context=source.run_id,destination_context=destination.run_id)
    with destination.store.transaction() as db:
        state=destination.store.session(destination.run_id,db)['state']
        state.setdefault('accepted_report_transfers',[]).append(proof)
        destination.store.update_state(db,destination.run_id,state)
        destination.store.event(db,destination.run_id,'accepted_report_handoff','transferred',inputs=[reference],outputs=[destination.store.put(db,proof)])
    return proof


def decide(ctx,args):
    """Native intent only; a separate host step prepares and executes any delta."""
    from tools.platform_handoff import require_role, transition
    require_role(ctx,'design')
    role=ctx.store.session(ctx.run_id)['state']['role_context']
    require_accepted_report(ctx.host,role['report'])
    if args.disposition!='adopt' and args.changes:raise ValueError('DEFER_OR_REJECT_CANNOT_PREPARE_CHANGES')
    if args.disposition=='adopt' and not args.changes:raise ValueError('ADOPT_REQUIRES_EXPLICIT_DELTA')
    return transition(ctx,'improvement_decision',dict(source_report=role['report'],decision=plain(args)))


def complete_execution(host, baseline, candidate_id, **kwargs):
    """Shared recorded simulation/evaluation/profile continuation."""
    from tools.execution_completion import complete_execution as complete
    return complete(host,baseline,candidate_id,**kwargs)
