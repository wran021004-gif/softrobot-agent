"""Deterministic factual delivery; provider reasoning and its review stay separate."""
from pydantic import Field, FiniteFloat, ValidationError
from schemas.common import Contract
from tools.platform_store import plain


class TrackingFacts(Contract):
    candidate: dict | None
    configuration: dict | None
    execution_id: str
    simulation: dict
    evaluation: dict
    report: dict | None
    task_accepted: bool | None
    valid_complete_execution: bool
    maximum_tracking_error_m: FiniteFloat | None
    rms_tracking_error_m: FiniteFloat | None
    declared_limit_m: FiniteFloat
    control_updates: int = Field(ge=0)
    accepted_feasible_plans: int = Field(ge=0)
    converged_updates: int = Field(ge=0)
    deadline_misses: int = Field(ge=0)
    control_period_s: FiniteFloat
    simulated_duration_s: FiniteFloat | None
    measured_computation_s: FiniteFloat | None
    mean_complete_update_s: FiniteFloat | None
    real_time_demonstrated: bool


def tracking_facts(summary, candidate=None, report=None):
    metrics = {m['name']: m['value'] for m in summary['tracking']['metrics']}
    if candidate is None and summary.get('candidate_id'):
        candidate=dict(candidate_id=summary['candidate_id'],configuration=summary['configuration'])
    return plain(TrackingFacts(candidate=candidate,
        configuration=candidate['configuration'] if candidate else summary.get('configuration'),
        execution_id=summary['execution_id'], simulation=summary['simulation'],
        evaluation=summary['evaluation'], report=report,
        task_accepted=summary['official_task_success'],
        valid_complete_execution=summary['valid_complete_execution'],
        maximum_tracking_error_m=metrics.get('max_position_error'),
        rms_tracking_error_m=metrics.get('rms_position_error'),
        declared_limit_m=summary['tracking']['acceptance']['data']['max_position_error_m'],
        control_updates=summary['updates'], accepted_feasible_plans=summary['accepted_plans'],
        converged_updates=summary['converged_updates'], deadline_misses=summary['deadline_misses'],
        control_period_s=summary['task']['timing']['control_period_s'],
        simulated_duration_s=summary['last_valid_time_s'], measured_computation_s=summary['simulation_wall_s'],
        mean_complete_update_s=summary['mean_update_s'], real_time_demonstrated=summary['real_time_demonstrated']))


def bound_tracking_facts(store, trial, candidate):
    binding = trial.get('profile_report')
    if not binding: return None
    summary = store.artifact(binding['reference'])['detail']
    if 'tracking' not in summary: return None
    evaluation = store.artifact(trial['evaluation'])
    if not (summary['execution_id']==candidate['execution_id']==binding['execution_id']==evaluation['source_execution_id']
            and summary['evaluation']==trial['evaluation'] and summary['simulation']==trial['simulation']['output']
            and binding['owner_run_id']==candidate['owner_run_id']
            and evaluation['task_success']==summary['official_task_success']):
        raise ValueError('DELIVERY_FACT_BINDING_MISMATCH')
    if summary['tracking']['metrics']!=evaluation['metrics']:
        raise ValueError('DELIVERY_FACT_BINDING_MISMATCH: evaluation metrics')
    return tracking_facts(summary, candidate, binding)


def check_tracking_statement(facts, statement):
    if statement is None:
        return dict(accepted=False, reason='typed result statement absent; prose not checked')
    try:
        checked = plain(TrackingFacts.model_validate(statement, strict=True))
    except ValidationError as exc:
        return dict(accepted=False, reason=str(exc))
    differences = [k for k in facts if checked[k] != facts[k]]
    return dict(accepted=not differences, mismatched_fields=differences,
        scope='Typed claims only; free-text reasoning still requires separate review')
