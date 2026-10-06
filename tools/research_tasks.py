"""Future research task adapters and one evidence-bound offline acceptance result.

Archived evaluators, kernels and campaigns retain their original semantics.
The new reach/hold protocol composes their outputs rather than replacing them.
"""
from dataclasses import dataclass
import math

from schemas.platform import SessionInput, EvaluationResult
from tools.platform_store import plain
from tools.state_io import digest


def effective_input(configuration):
    value = plain(configuration)
    return value.get('effective', value.get('input', value))


@dataclass(frozen=True)
class ResearchTaskAdapter:
    configuration: dict

    @property
    def task(self):
        return self.configuration['task']

    def reference_at(self, times):
        """Use existing timed-reference semantics; a reach target is constant."""
        import numpy as np
        times = np.asarray(times, dtype=float)
        if self.task['family'] == 'task.tracking':
            from extensions.tendon_family.tracking import reference_at
            return reference_at(self.task['goal']['data'], times)
        target = self.task['goal']['data']['target_m']
        return np.broadcast_to(target, times.shape + (3,)).copy(), np.zeros(times.shape + (3,))

    def operating_point(self, time_s=0.):
        position, velocity = self.reference_at(time_s)
        return dict(time_s=time_s, reference_position_m=position.tolist(),
                    reference_velocity_m_s=velocity.tolist(), frame='world',
                    state_source='Named task initializer; subsequent measured backend state',
                    reference_is_equilibrium=False)

    def describe(self):
        task = self.task
        reach = task['family'] == 'task.reach'
        metrics = ([dict(name='terminal_error_m', unit='m', meaning='Sealed endpoint evaluator position error'),
                    dict(name='holding_max_error_m', unit='m', meaning='Maximum sampled final-window tip error'),
                    dict(name='holding_max_speed_m_s', unit='m/s', meaning='Maximum sampled world translational tip speed')]
                   if reach else [dict(name=name, unit='m', meaning=meaning) for name, meaning in (
                       ('max_position_error', 'Maximum timed-reference error in scored interval'),
                       ('rms_position_error', 'Arithmetic RMS over inclusive uniform scored samples'),
                       ('terminal_position_error', 'Timed-reference error at execution endpoint'))])
        controller = self.configuration['policy']['controller']
        return dict(contract='research.task_adapter', version='1.0.0', family=task['family'],
            evaluator=task['evaluator'], output=next(s for s in task['observations'] if s['name']=='tip_position'),
            reference=task['goal'], operating_point=self.operating_point(), metrics=metrics,
            scoring_interval_s=task['sampling']['window_s'],
            holding=(controller['parameters']['data'].get('settling') if reach else None),
            timing=task['timing'], continuous_time_guarantee=False,
            context=('Endpoint reach and final-window position/speed are distinct components. Offline deployment timing is diagnostic.'
                     if reach else 'Timed world reference and inclusive interval error; no absolute-speed holding requirement.'))

    def check_compatibility(self):
        """Check the actual registered pairing, separately from historical matches."""
        from tools.platform_tasks import compile_input
        from tools.platform_registry import registry
        inp = SessionInput.model_validate(self.configuration)
        reg = registry()
        definition = reg.get(inp.policy.controller.extension_id, inp.policy.controller.version, 'controller')
        if inp.task.family == 'task.tracking' and inp.policy.controller.extension_id == 'controller.gvs_nmpc' and inp.policy.controller.version != '5.0.0':
            return dict(technical_compatibility=dict(status='unsupported',
                reason='TRACKING_CONTROLLER_VERSION_REQUIRED: controller.gvs_nmpc@5.0.0 owns timed-reference control; @'+inp.policy.controller.version+' is reach control'),
                historical_evidence=dict(status='not_assessed', reason='Historical reach outcomes cannot validate tracking'))
        try:
            compile_input(inp.model_dump(mode='json'), reg)
            hook = definition.hook('route_applicability')
            if hook:
                hook(inp)
        except (ValueError, TypeError) as exc:
            return dict(technical_compatibility=dict(status='unsupported', reason=str(exc)),
                        historical_evidence=dict(status='not_assessed'))
        return dict(technical_compatibility=dict(status='supported', reason='Registered task, evaluator, signals, initializer, controller and backend checks passed'),
                    historical_evidence=dict(status='not_assessed', reason='Technical support does not establish exact frozen experiment identity or performance'))

    def lifecycle(self):
        from tools.platform_registry import registry
        policy = self.configuration['policy']
        caps = registry().get(policy['controller']['extension_id'], policy['controller']['version'], 'controller').capabilities
        return dict(initialization='Each new execution compiles its candidate and applies all named qpos/qvel from the task initializer once; measured warm states are regenerated',
            controller_reset_supported=caps.get('reset', False), controller_restore_supported=caps.get('restore', False),
            new_execution='New isolated controller/backend instances; task seed and initial state remain frozen',
            cache='New request_id with cache:new; only a distinct non-cache simulation receipt charged one backend solve is a repetition',
            restore='Restore research evidence and pending work from Store; do not resume a partial physical trajectory or controller warm state',
            unsupported=['In-place GVS controller reset', 'Controller/backend trajectory checkpoint continuation'],
            failure='Retain the original failed/incomplete slot; any deliberately authorized replacement is a separately labelled attempt')


def task_adapter(configuration):
    value = effective_input(configuration)
    if value['task']['family'] not in ('task.reach', 'task.tracking'):
        raise ValueError('RESEARCH_TASK_ADAPTER_REQUIRED: '+value['task']['family'])
    # Validate the registered task itself before extracting task-specific meanings.
    from tools.platform_tasks import check_definition
    check_definition(value['task'])
    return ResearchTaskAdapter(value)


def _component(value, passed, unit=None, limit=None, reason=None):
    return dict(value=value, passed=passed, unit=unit, limit=limit, reason=reason)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assemble_acceptance(configuration, evaluation, profile, *, evaluation_reference=None,
                        profile_reference=None, motion=None, protocol_id=None):
    """Compose sealed evaluator and profile, preserving missing and failed components.

    `profile` is control.profile_report's detail or the enclosing ProfileOutput.
    Optional sealed motion verifies the exact holding grid without recomputing
    physics. The profile's `available` is otherwise the existing coverage authority.
    """
    adapter = task_adapter(configuration)
    cfg, task = adapter.configuration, adapter.task
    if protocol_id is None:
        protocol_id = ('offline_reach_hold_v1' if task['family']=='task.reach'
                       else 'offline_tracking_v1')
    ev = plain(evaluation) if evaluation is not None else None
    if ev is not None:
        ev = plain(EvaluationResult.model_validate(ev))
    report = plain(profile) if profile is not None else {}
    report = report.get('detail', report)
    components = {}
    issues = []
    controller = cfg['policy']['controller']
    if task['family']=='task.tracking' and controller['extension_id']=='controller.gvs_nmpc' and controller['version']!='5.0.0':
        issues.append('TRACKING_CONTROLLER_VERSION_REQUIRED')
    validity = None if ev is None else ev['validity']
    components['evaluation_validity'] = _component(validity, None if ev is None else validity=='valid')
    complete = report.get('complete')
    components['execution_complete'] = _component(complete, complete)
    components['task_evaluator'] = _component(None if ev is None else ev['task_success'],
                                              None if ev is None else ev['task_success'])
    if ev and ev['evaluator'] != task['evaluator']['extension_id']:
        issues.append('EVALUATOR_IDENTITY_MISMATCH')
    if ev and ev.get('source_execution_id') and report.get('execution_id') != ev['source_execution_id']:
        issues.append('EVALUATION_PROFILE_EXECUTION_MISMATCH')
    if ev and report.get('evaluation') and evaluation_reference and report['evaluation'] != plain(evaluation_reference):
        issues.append('EVALUATION_REFERENCE_MISMATCH')
    if ev and report.get('simulation') and report['simulation'] != ev['source']:
        issues.append('EVALUATION_SOURCE_MISMATCH')
    if ev and 'official_task_success' in report and report['official_task_success'] != ev['task_success']:
        issues.append('PROFILE_EVALUATOR_OUTCOME_MISMATCH')
    if report.get('task') and digest(report['task']) != digest(task):
        issues.append('PROFILE_TASK_MISMATCH')
    if report.get('execution_scope'):
        from extensions.tendon_family.gvs_profile import execution_scope
        if report['execution_scope'] != execution_scope(cfg):
            issues.append('PROFILE_EXECUTION_SCOPE_MISMATCH')
    metrics = {m['name']: m['value'] for m in (ev or {}).get('metrics', [])}
    constraints = (ev or {}).get('constraints', [])
    for constraint in constraints:
        components['evaluator:'+constraint['name']] = _component(constraint['observed'], constraint['satisfied'], constraint['units'], constraint['limit'])
    errors = report.get('solver_error_count')
    components['solver_errors'] = _component(errors, errors==0 if _number(errors) else None, 'count', 0)
    violation = report.get('force_bound_violation_n')
    # Matches the registered tracking evaluator's numerical force tolerance.
    components['force_bounds'] = _component(violation, 0<=violation<=1e-8 if _number(violation) else None, 'N', 1e-8)
    if task['family'] == 'task.reach':
        metrics = dict(terminal_error_m=metrics.get('position_error'),
                       holding_max_error_m=None, holding_max_speed_m_s=None)
        settling = report.get('sampled_settling', {})
        limits = cfg['policy']['controller']['parameters']['data']['settling']
        matched = all(settling.get(k)==limits[k] for k in ('window_s','position_limit_m','speed_limit_m_s'))
        covered = settling.get('available')
        if covered and not matched:
            issues.append('HOLDING_DEFINITION_MISMATCH')
        duration, period = task['timing']['duration_s'], task['timing']['sample_period_s']
        expected = round(limits['window_s']/period)+1
        if motion is not None:
            selected = [r for r in plain(motion) if duration-limits['window_s']-1e-9 <= r['time_s'] <= duration+1e-9]
            grid = [duration-limits['window_s']+i*period for i in range(expected)]
            covered = bool(covered and len(selected)==expected and all(abs(r['time_s']-t)<=1e-8 for r,t in zip(selected,grid)))
        components['holding_coverage'] = _component(covered, covered, 'inclusive uniform samples', expected)
        for name, field, threshold, unit in (
                ('holding_position','max_error_m','position_limit_m','m'),
                ('holding_speed','max_speed_m_s','speed_limit_m_s','m/s')):
            value = settling.get(field)
            components[name] = _component(value, 0<=value<=limits[threshold] if covered and matched and _number(value) else None, unit, limits[threshold])
        if covered and matched and all(components[n]['passed'] is not None for n in ('holding_position','holding_speed')):
            calculated = components['holding_position']['passed'] and components['holding_speed']['passed']
            if settling.get('passed') is not calculated:
                issues.append('PROFILE_HOLDING_OUTCOME_MISMATCH')
        metrics.update(holding_max_error_m=settling.get('max_error_m'), holding_max_speed_m_s=settling.get('max_speed_m_s'))
    else:
        components['tracking_sampling'] = _component(validity=='valid' if ev else None, validity=='valid' if ev else None,
            reason='Registered tracking evaluator checks inclusive motion and pre-step tension grids')
    missing = [name for name, c in components.items() if c['passed'] is None]
    if issues or validity=='invalid':
        status, accepted = 'invalid', None
    elif validity=='incomplete' or complete is False:
        status, accepted = 'incomplete', None
    elif missing or (task['family']=='task.reach' and not components['holding_coverage']['passed']):
        status, accepted = 'missing_evidence', None
    else:
        accepted = all(c['passed'] for c in components.values())
        status = 'accepted' if accepted else 'valid_failure'
    return dict(contract='research.task_acceptance', version='1.0.0', protocol_id=protocol_id,
        task_family=task['family'], task_identity=digest(task), status=status, accepted=accepted,
        components=components, metrics=metrics, missing=missing, issues=issues,
        execution_id=report.get('execution_id'),
        sources=dict(evaluation=plain(evaluation_reference), profile=plain(profile_reference)),
        timing=dict(**task['timing'], real_time_required=False, real_time_demonstrated=report.get('real_time_demonstrated'),
            deadline_misses=report.get('deadline_misses'), mean_update_s=report.get('mean_update_s'), simulation_wall_s=report.get('simulation_wall_s')),
        continuous_time_guarantee=False)


def aggregate_acceptance(records, scheduled, *, schedule=None):
    """The frozen scheduled denominator includes absent, incomplete and replay slots."""
    if not isinstance(scheduled, int) or scheduled<=0 or len(records)>scheduled:
        raise ValueError('POSITIVE_FROZEN_SCHEDULE_REQUIRED')
    if schedule is not None and len(schedule)!=scheduled:
        raise ValueError('SCHEDULE_COUNT_MISMATCH')
    results = [r['acceptance'] for r in records if r.get('acceptance')]
    families = {r['task_family'] for r in results}
    protocols = {r['protocol_id'] for r in results}
    if len(families)>1 or len(protocols)>1:
        raise ValueError('AGGREGATION_TASK_PROTOCOL_MISMATCH')
    family = next(iter(families), None)
    metric_names = (('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
                    if family=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error')
                    if family=='task.tracking' else ())
    slots, seen, entries = set(), set(), []
    accepted = 0
    for record in records:
        slot = (record.get('case_id'), record.get('seed'), record.get('repetition'))
        if slot in slots:
            raise ValueError('DUPLICATE_SCHEDULE_SLOT')
        slots.add(slot)
        if schedule is not None and not any(slot==(s.get('case_id'),s.get('seed'),s.get('repetition')) for s in schedule):
            raise ValueError('UNSCHEDULED_REPETITION')
        receipt = plain(record.get('receipt') or {})
        result = record.get('acceptance')
        execution = receipt.get('execution_id')
        fresh = bool(execution and execution not in seen and receipt.get('cache_hit') is False
                     and receipt.get('charged',{}).get('backend_solves')==1
                     and receipt.get('tool_id')=='simulation.run'
                     and receipt.get('original_execution_id') in (None,execution))
        if execution:
            seen.add(execution)
        binding_matches = bool(result and execution == result.get('execution_id'))
        count = bool(fresh and binding_matches and result['accepted'] is True)
        accepted += count
        entries.append(dict(case_id=slot[0], seed=slot[1], repetition=slot[2],
            fresh_execution=fresh, acceptance_execution_matches=binding_matches,
            counted_accepted=count, acceptance=result,
            status=('not_new_repetition' if receipt and not fresh else
                    'acceptance_identity_mismatch' if result and result.get('execution_id') and not binding_matches else
                    result['status'] if result else 'pending_or_incomplete')))
    return dict(contract='research.task_aggregation',version='1.0.0',accepted=accepted,scheduled=scheduled,
        task_family=family,protocol_id=next(iter(protocols), None),
        schedule_identity=digest(schedule) if schedule is not None else None,
        recorded=len(records),unrecorded=scheduled-len(records),joint_acceptance_fraction=accepted/scheduled,
        all_scheduled_accepted=accepted==scheduled,entries=entries,
        interpretation='Deterministic frozen-case observed fraction; not a population success probability',
        metrics={name:max(r['metrics'][name] for r in results)
                 if len(results)==scheduled and all(_number(r['metrics'].get(name)) for r in results) else None
                 for name in metric_names})


def compare_acceptance(candidate, incumbent, tolerance=1e-9):
    """Primary acceptance followed by componentwise physical comparison, no score."""
    if candidate['contract'] != incumbent['contract']:
        raise ValueError('ACCEPTANCE_CONTRACT_MISMATCH')
    aggregate = candidate['contract']=='research.task_aggregation'
    if aggregate:
        if candidate['scheduled'] != incumbent['scheduled']:
            raise ValueError('SCHEDULE_COUNT_MISMATCH')
        if (candidate['task_family'],candidate['protocol_id'],candidate['schedule_identity']) != (incumbent['task_family'],incumbent['protocol_id'],incumbent['schedule_identity']):
            raise ValueError('TASK_ACCEPTANCE_SCHEDULE_MISMATCH')
        left, right = candidate['joint_acceptance_fraction'], incumbent['joint_acceptance_fraction']
    else:
        if (candidate['task_identity'],candidate['protocol_id']) != (incumbent['task_identity'],incumbent['protocol_id']):
            raise ValueError('TASK_ACCEPTANCE_IDENTITY_MISMATCH')
        if candidate['accepted'] is None or incumbent['accepted'] is None:
            return dict(relation='unavailable',reason='Missing, invalid or incomplete acceptance is not a physical failure')
        left,right = int(candidate['accepted']),int(incumbent['accepted'])
    if left != right:
        return dict(relation='improved' if left>right else 'worse',basis='primary_joint_acceptance')
    names = (('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
             if candidate['task_family']=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error'))
    if any(not _number(v['metrics'].get(n)) for v in (candidate,incumbent) for n in names):
        return dict(relation='unavailable',reason='Component metrics missing')
    changes = {n:candidate['metrics'][n]-incumbent['metrics'][n] for n in names}
    better, worse = any(v < -tolerance for v in changes.values()), any(v > tolerance for v in changes.values())
    return dict(relation='tradeoff' if better and worse else 'improved' if better else 'worse' if worse else 'equivalent',
                basis='componentwise_physical_metrics',changes=changes,computation='reported separately')


def stop_interpretation(result, reason, *, budget_exhausted=False, remaining_work=0):
    """A legal stop and a supported success claim do not prove an optimal stop."""
    aggregate = result['contract']=='research.task_aggregation'
    accepted = result['all_scheduled_accepted'] if aggregate else result['accepted'] is True
    legal = ((reason=='budget_exhausted' and budget_exhausted) or
             (reason=='completed_schedule' and remaining_work==0) or
             reason=='predeclared_policy')
    return dict(legal=legal,reason=reason,success_claim_supported=accepted,
                optimality='not_assessed',acceptance_result=result,
                budget_is_upper_bound=True)
