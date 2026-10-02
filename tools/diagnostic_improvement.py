"""Preparation seam only. No tool registration, execution action or backend call.

Future orchestration must separately authorize matched baseline/candidate runs
through simulation.run, evaluation.run and control.profile_report (the existing
gvs_nmpc_route_experiment entry point / route.run_built path), then return sealed
receipts to diagnosis. Reach acceptance remains evaluate.reach; holding and
computation are separate reporting dimensions, never inferred from reach.
"""
from typing import Literal
from uuid import uuid4
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef, SessionInput, CandidateInput, ToolReceipt
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.state_io import digest


class ImprovementDecision(Contract):
    """Flat model-authored business fields; host owns all source identities."""
    disposition: Literal['adopt','defer','reject']
    changes: dict[str, object] = Field(default_factory=dict, description='Only paths/values allowed by the existing candidate builder grant.')
    rationale: str = Field(min_length=1)
    expected_measurable_effect: str = Field(min_length=1)


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
    accepted=host.store.session(host.run_id)['state'].get('handoff_history',[])
    if not any(h['kind']=='diagnosis_report' and h['reference']==plain(report_reference) for h in accepted):
        raise ValueError('ACCEPTED_DIAGNOSIS_REQUIRED')
    report=host.store.artifact(report_reference)
    binding=host.store.artifact(report['report']['source'])
    baseline=SessionInput.model_validate(host.store.artifact(binding['configuration'])['effective'])
    result=ImprovementPreparation(status='no_change_selected',source_execution=binding['execution_id'],
        source_report=report_reference,source_configuration=binding['configuration'],decision=decision)
    if decision.disposition!='adopt':
        if decision.changes:raise ValueError('DEFER_OR_REJECT_CANNOT_PREPARE_CHANGES')
        return result
    if not decision.changes:raise ValueError('ADOPT_REQUIRES_EXPLICIT_DELTA')
    candidate=_candidate(baseline,decision.changes,registry())
    differences=actual_diff(plain(baseline),plain(candidate))
    if not differences:raise ValueError('EFFECTIVE_CHANGE_REQUIRED')
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
