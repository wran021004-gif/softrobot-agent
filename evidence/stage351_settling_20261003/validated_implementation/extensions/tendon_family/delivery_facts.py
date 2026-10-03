"""Deterministic factual delivery; provider reasoning and its review stay separate."""
from pydantic import Field, FiniteFloat, ValidationError
from schemas.common import Contract
from tools.platform_store import plain
from typing import Literal


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


class ReachFacts(Contract):
    result_type: Literal['free_reach'] = 'free_reach'
    candidate: dict | None
    configuration: dict | None
    execution_id: str
    simulation: dict
    evaluation: dict
    report: dict | None
    task_accepted: bool | None
    evaluation_validity: str | None
    complete: bool
    valid_complete_execution: bool
    target_position_m: list[FiniteFloat]
    terminal_position_m: list[FiniteFloat] | None
    signed_position_error_m: list[FiniteFloat] | None
    error_convention: Literal['actual_tip minus target'] = 'actual_tip minus target'
    coordinate_frame: Literal['world'] = 'world'
    terminal_error_m: FiniteFloat | None
    terminal_tip_speed_m_s: FiniteFloat | None
    sampled_settling: dict
    control_updates: int
    accepted_plans: int
    initialization_selected: int
    accepted_noninitialization_plans: int
    converged_updates: int
    solver_error_count: int
    hold_last_responses: int
    applied_tension_ranges: list[dict]
    force_bound_violation_n: FiniteFloat | None
    one_step_prediction_summary: dict
    one_step_prediction_evidence: dict | None
    simulated_duration_s: FiniteFloat | None
    measured_computation_s: FiniteFloat | None
    mean_complete_update_s: FiniteFloat | None
    control_period_s: FiniteFloat
    deadline_misses: int
    real_time_demonstrated: bool


def reach_facts(summary, candidate=None, report=None):
    s=summary
    target=s['task']['goal']['data']['target_m']
    tip=s.get('terminal_position_m')
    identity=None if candidate is None else {k:candidate[k] for k in ('candidate_id','owner_run_id','configuration','execution_id')}
    return plain(ReachFacts(candidate=identity,configuration=s.get('configuration'),
        execution_id=s['execution_id'],simulation=s['simulation'],evaluation=s['evaluation'],report=report,
        task_accepted=s['official_task_success'],evaluation_validity=s['evaluation_validity'],
        complete=s['complete'],valid_complete_execution=s['valid_complete_execution'],
        target_position_m=target,terminal_position_m=tip,
        signed_position_error_m=None if tip is None else [a-b for a,b in zip(tip,target)],
        terminal_error_m=s['terminal_error_m'],terminal_tip_speed_m_s=s['terminal_tip_speed_m_s'],
        sampled_settling=s['sampled_settling'],control_updates=s['updates'],
        **{k:s[k] for k in ('accepted_plans','initialization_selected','accepted_noninitialization_plans',
            'converged_updates','solver_error_count','hold_last_responses','force_bound_violation_n',
            'one_step_prediction_summary','deadline_misses','real_time_demonstrated')},
        applied_tension_ranges=[{k:r[k] for k in ('tendon','tendon_index','minimum_n','maximum_n','limit_n') if k in r}
            for r in s['drive_utilization']],one_step_prediction_evidence=s.get('one_step_prediction_evidence'),
        simulated_duration_s=s['last_valid_time_s'],measured_computation_s=s['simulation_wall_s'],
        mean_complete_update_s=s['mean_update_s'],control_period_s=s['task']['timing']['control_period_s']))


def bound_result_facts(store, trial, candidate):
    binding=trial.get('profile_report')
    if not binding: return None
    summary=dict(store.artifact(binding['reference'])['detail'])
    if 'tracking' in summary: return bound_tracking_facts(store,trial,candidate)
    if summary.get('task',{}).get('family')!='task.reach': return None
    # Pre-multiphysics reports do not contain this contract's required bindings
    # and measurements. Preserve their legacy view rather than invent facts.
    if any(k not in summary for k in ('configuration','accepted_noninitialization_plans',
            'drive_utilization','one_step_prediction_summary')): return None
    evaluation=store.artifact(trial['evaluation'])
    if not (summary['execution_id']==candidate['execution_id']==binding['execution_id']==evaluation['source_execution_id']
            and summary['evaluation']==trial['evaluation'] and summary['simulation']==trial['simulation']['output']
            and summary['configuration']==candidate['configuration']
            and binding['owner_run_id']==candidate['owner_run_id']
            and evaluation['task_success']==summary['official_task_success']
            and evaluation['candidate_id']==candidate['candidate_id']):
        raise ValueError('DELIVERY_FACT_BINDING_MISMATCH')
    # Older sealed reports omitted the measured tip. Use only a timestamp-aligned
    # measured endpoint from their sealed prediction comparison, never a prediction.
    if 'terminal_position_m' not in summary and summary['complete'] and summary.get('one_step_prediction_evidence'):
        rows=store.artifact(summary['one_step_prediction_evidence'])
        terminal=[r for r in rows if abs(r['end_s']-summary['last_valid_time_s'])<1e-8 and r['frame']=='world']
        if len(terminal)==1: summary['terminal_position_m']=terminal[0]['measured_tip_m']
    return reach_facts(summary,candidate,binding)


def check_result_statement(facts, statement):
    if facts.get('result_type')!='free_reach': return check_tracking_statement(facts,statement)
    if statement is None: return dict(accepted=False,reason='free_reach result_statement required; copy factual_result')
    try: checked=plain(ReachFacts.model_validate(statement,strict=True))
    except ValidationError as exc: return dict(accepted=False,reason=str(exc))
    differences=[k for k in facts if checked[k]!=facts[k]]
    return dict(accepted=not differences,mismatched_fields=differences,
        scope='Typed claims only; free-text reasoning requires separate review')
