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


def _protocol_requirements(result):
    """Required meanings come from the supported protocol, never submitted keys."""
    common = {'evaluation_validity', 'execution_complete', 'task_evaluator',
              'solver_errors', 'force_bounds'}
    protocol, family = result.get('protocol_id'), result.get('task_family')
    if (protocol, family) == ('offline_reach_hold_v1', 'task.reach'):
        return common | {'holding_coverage', 'holding_position', 'holding_speed',
                         'evaluator:task_bound'}
    if (protocol, family) == ('offline_tracking_v1', 'task.tracking'):
        limits = result.get('evaluator_tension_channels')
        if not limits:
            return None
        return common | {'tracking_sampling', 'evaluator:sampled_tracking_bound'} | {
            'evaluator:tension_bound_' + channel for channel in limits}
    return None


def _outcome_issue(result):
    required = _protocol_requirements(result)
    if required is None:
        return 'TASK_PROTOCOL_REQUIREMENTS_UNAVAILABLE'
    components = result.get('components') or {}
    if required - components.keys() or any(type(c.get('passed')) is not bool for c in components.values()):
        return 'PROTOCOL_REQUIRED_COMPONENT_MISSING_OR_UNKNOWN'
    # Invalidity and absent coverage are not ordinary physical failures.
    coverage = 'holding_coverage' if result['task_family']=='task.reach' else 'tracking_sampling'
    if any(components[n]['passed'] is not True for n in ('evaluation_validity', 'execution_complete', coverage)):
        return 'PROTOCOL_VALIDITY_OR_COVERAGE_UNRESOLVED'
    passed = all(c['passed'] for c in components.values())
    if (result.get('status') != ('accepted' if passed else 'valid_failure') or
            result.get('accepted') is not passed):
        return 'ACCEPTANCE_COMPONENT_OUTCOME_INCONSISTENT'
    return None


def _source_issue(result, evidence=None):
    """Check presence before equality; reach profile links stay reach-specific."""
    sources = result.get('sources') or {}
    evidence = evidence if evidence is not None else result.get('evidence_binding') or {}
    for kind in ('evaluation', 'profile'):
        ref = sources.get(kind)
        if not isinstance(ref, dict) or not ref.get('artifact_id'):
            return 'PROTOCOL_REQUIRED_SOURCE_MISSING:' + kind
        if evidence.get(kind) is None:
            return 'PROTOCOL_REQUIRED_SOURCE_MISSING:' + kind + '_evidence'
        if ref != evidence[kind]:
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    execution = result.get('execution_id')
    if not execution or not evidence.get('simulation'):
        return 'PROTOCOL_REQUIRED_SOURCE_MISSING:execution'
    binding = evidence.get('profile_binding') or {}
    if binding.get('execution_id') is not None and binding['execution_id'] != execution:
        return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    evaluation_binding = evidence.get('evaluation_binding') or {}
    if (evaluation_binding.get('source_execution_id') not in (None,execution) or
            evaluation_binding.get('original_execution_id') not in (None,execution) or
            evaluation_binding.get('source') not in (None,evidence['simulation'])):
        return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    if result['protocol_id']=='offline_reach_hold_v1':
        for kind in ('evaluation', 'simulation', 'execution_id'):
            if not binding.get(kind):
                return 'PROTOCOL_REQUIRED_SOURCE_MISSING:profile_' + kind
        if (binding['evaluation'] != sources['evaluation'] or binding['simulation'] != evidence['simulation'] or
                binding['execution_id'] != execution):
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    for kind, tool in (('evaluation', 'evaluation.run'), ('profile', 'control.profile_report')):
        receipts = [r for r in evidence.get('receipts', []) if r.get('tool_id')==tool]
        if receipts and (len(receipts)!=1 or receipts[0].get('output')!=sources[kind] or
                         receipts[0].get('execution_status')!='completed'):
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    return None


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
        evidence_binding=dict(evaluation=plain(evaluation_reference), profile=plain(profile_reference),
            simulation=(ev or {}).get('source'),
            evaluation_binding={k:(ev or {}).get(k) for k in ('source','source_execution_id','original_execution_id')},
            profile_binding={k:report[k] for k in ('evaluation','simulation','execution_id') if k in report}),
        evaluator_tension_channels=(sorted(task['evaluator']['parameters']['data']['tension_limits_n'])
            if task['family']=='task.tracking' else None),
        timing=dict(**task['timing'], real_time_required=False, real_time_demonstrated=report.get('real_time_demonstrated'),
            deadline_misses=report.get('deadline_misses'), mean_update_s=report.get('mean_update_s'), simulation_wall_s=report.get('simulation_wall_s')),
        continuous_time_guarantee=False)


def aggregate_acceptance(records, scheduled, *, schedule=None, evidence_policy=None, comparison_scope=None):
    """The frozen scheduled denominator includes absent, incomplete and replay slots."""
    if not isinstance(scheduled, int) or scheduled<=0 or len(records)>scheduled:
        raise ValueError('POSITIVE_FROZEN_SCHEDULE_REQUIRED')
    if schedule is not None and len(schedule)!=scheduled:
        raise ValueError('SCHEDULE_COUNT_MISMATCH')
    policy = evidence_policy or {'require_fresh_repetitions':True, 'allow_historical_reuse':False}
    if any(type(policy.get(k,default)) is not bool for k,default in (
            ('require_fresh_repetitions',True),('allow_historical_reuse',False))):
        raise ValueError('DECLARED_FRESHNESS_POLICY_REQUIRED')
    if any('fresh_required' in s and type(s['fresh_required']) is not bool for s in (schedule or [])):
        raise ValueError('DECLARED_SLOT_FRESHNESS_REQUIRED')
    def slot_key(row):return (row.get('case_id'),row.get('seed'),row.get('repetition'))
    if schedule is not None and len({slot_key(s) for s in schedule}) != scheduled:
        raise ValueError('DUPLICATE_SCHEDULE_SLOT')
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
        fresh = bool(not record.get('historical_reuse') and execution and execution not in seen and receipt.get('cache_hit') is False
                     and receipt.get('charged',{}).get('backend_solves')==1
                     and receipt.get('tool_id')=='simulation.run'
                     and receipt.get('original_execution_id') in (None,execution))
        if execution:
            seen.add(execution)
        binding_matches = bool(result and execution == result.get('execution_id'))
        source_issues=[]
        for kind in ('evaluation','profile'):
            expected=((result or {}).get('sources') or {}).get(kind)
            if record.get(kind) and record[kind]!=expected:source_issues.append(kind)
        declaration=next((s for s in (schedule or []) if slot==slot_key(s)), {})
        fresh_required=declaration.get('fresh_required', policy.get('require_fresh_repetitions', True))
        # Reuse is protocol evidence, never a fresh repetition. An explicit
        # policy and source binding are both required for a nonfresh slot.
        reuse = bool(not fresh and policy.get('allow_historical_reuse') and
            record.get('historical_reuse') and binding_matches and execution and
            receipt.get('tool_id')=='simulation.run')
        evidence_eligible = fresh or (not fresh_required and reuse)
        count = bool(evidence_eligible and binding_matches and result['accepted'] is True)
        accepted += count
        entries.append(dict(case_id=slot[0], seed=slot[1], repetition=slot[2],
            fresh_execution=fresh, acceptance_execution_matches=binding_matches,
            fresh_required=fresh_required,
            historical_reuse=bool(record.get('historical_reuse') or receipt.get('cache_hit')),
            reuse_permitted=reuse,
            evidence_eligible=evidence_eligible, receipt=receipt,
            source_binding_issues=source_issues,
            source_evidence=dict(evaluation=record.get('evaluation'), profile=record.get('profile'),
                simulation=receipt.get('output'), receipts=record.get('receipts', []),
                evaluation_binding=(record.get('evaluation_data') or
                    (result or {}).get('evidence_binding', {}).get('evaluation_binding') or {}),
                profile_binding={k:record.get('profile_summary', {}).get(k)
                    for k in ('evaluation','simulation','execution_id')}),
            counted_accepted=count, acceptance=result,
            status=('not_new_repetition' if receipt and not fresh else
                    'acceptance_identity_mismatch' if result and result.get('execution_id') and not binding_matches else
                    result['status'] if result else 'pending_or_incomplete')))
    return dict(contract='research.task_aggregation',version='1.0.0',accepted=accepted,scheduled=scheduled,
        task_family=family,protocol_id=next(iter(protocols), None),
        schedule_identity=digest(schedule) if schedule is not None else None,
        schedule=schedule, evidence_policy=policy, comparison_scope=comparison_scope,
        recorded=len(records),unrecorded=scheduled-len(records),joint_acceptance_fraction=accepted/scheduled,
        all_scheduled_accepted=accepted==scheduled,entries=entries,
        interpretation='Deterministic frozen-case observed fraction; not a population success probability',
        metrics={name:max(r['metrics'][name] for r in results)
                 if len(results)==scheduled and all(_number(r['metrics'].get(name)) for r in results) else None
                 for name in metric_names})


def comparison_prerequisites(candidate, incumbent):
    """Check complete interpretable slots before any aggregate ranking.

    Task identity is compared per declared slot; robot/control identity may
    differ. Historical aggregates remain readable, but raw receipts are needed
    to re-establish executable comparison prerequisites.
    """
    issues=[]; seen=set()
    if candidate.get('comparison_scope') != incumbent.get('comparison_scope'):
        issues.append(dict(reason='INCOMPATIBLE_COMPARISON_SCOPE'))
    if candidate.get('evidence_policy') != incumbent.get('evidence_policy'):
        issues.append(dict(reason='INCOMPATIBLE_EVIDENCE_POLICY'))
    indexed=[]
    for role, group in [('candidate',candidate),('incumbent',incumbent)]:
        schedule=group.get('schedule'); entries=group.get('entries',[])
        key=lambda r:(r.get('case_id'),r.get('seed'),r.get('repetition'))
        required={key(r) for r in (schedule or [])}
        actual={key(r) for r in entries}
        if schedule is None or len(required)!=group['scheduled'] or digest(schedule)!=group.get('schedule_identity'):
            issues.append(dict(role=role,reason='DECLARED_SCHEDULE_REQUIRED'))
        for slot in sorted(required-actual, key=str):
            issues.append(dict(role=role,slot=list(slot),reason='MISSING_SLOT'))
        if len(actual)!=len(entries) or actual-required:
            issues.append(dict(role=role,reason='DUPLICATE_OR_UNDECLARED_SLOT'))
        counted=0
        for entry in entries:
            slot=key(entry); result=entry.get('acceptance') or {};receipt=entry.get('receipt') or {}
            eid=receipt.get('execution_id')
            fresh=bool(not entry.get('historical_reuse') and eid and eid not in seen and receipt.get('cache_hit') is False and
                receipt.get('charged',{}).get('backend_solves')==1 and receipt.get('tool_id')=='simulation.run' and
                receipt.get('original_execution_id') in (None,eid))
            if eid:seen.add(eid)
            declaration=next((s for s in (schedule or []) if key(s)==slot), {})
            policy=group.get('evidence_policy') or {}
            fresh_required=declaration.get('fresh_required',policy.get('require_fresh_repetitions',True))
            reuse=bool(not fresh_required and policy.get('allow_historical_reuse') and entry.get('historical_reuse'))
            reason=None
            if not eid or eid!=result.get('execution_id') or receipt.get('tool_id')!='simulation.run':reason='EXECUTION_RECEIPT_BINDING_MISMATCH'
            elif entry.get('source_binding_issues'):reason='ACCEPTANCE_SOURCE_BINDING_MISMATCH'
            elif receipt.get('execution_status')!='completed':reason='EXECUTION_NOT_COMPLETE'
            elif not fresh and not reuse:reason='REQUIRED_FRESH_REPETITION_ABSENT'
            elif result.get('status') not in ('accepted','valid_failure') or result.get('accepted') is not (result.get('status')=='accepted'):
                reason='OUTCOME_NOT_INTERPRETABLE'
            elif result.get('task_family')!=group['task_family'] or result.get('protocol_id')!=group['protocol_id']:
                reason='TASK_PROTOCOL_MISMATCH'
            elif _outcome_issue(result):reason=_outcome_issue(result)
            elif _source_issue(result, entry.get('source_evidence')):
                reason=_source_issue(result, entry.get('source_evidence'))
            elif any(not _number(result['metrics'].get(n)) for n in group.get('metrics',{})):
                reason='METRIC_MISSING_OR_UNINTERPRETABLE'
            if reason:issues.append(dict(role=role,slot=list(slot),reason=reason))
            else:counted+=result['accepted'] is True
        if counted!=group['accepted'] or group['joint_acceptance_fraction']!=group['accepted']/group['scheduled']:
            issues.append(dict(role=role,reason='AGGREGATE_COUNT_MISMATCH'))
        indexed.append({key(e):e.get('acceptance') or {} for e in entries})
    for slot in indexed[0].keys() & indexed[1].keys():
        a,b=indexed[0][slot],indexed[1][slot]
        semantics=lambda r:(r.get('task_identity'),r.get('protocol_id'),
            {k:(v.get('unit'),v.get('limit')) for k,v in r.get('components',{}).items()})
        if not a.get('task_identity') or semantics(a)!=semantics(b):
            issues.append(dict(slot=list(slot),reason='INCOMPATIBLE_TASK_OR_METRIC_MEANINGS'))
    return issues


def compare_acceptance(candidate, incumbent, tolerance=1e-9):
    """Primary acceptance followed by componentwise physical comparison, no score."""
    if candidate['contract'] != incumbent['contract']:
        return dict(relation='unavailable',reason='ACCEPTANCE_CONTRACT_MISMATCH')
    aggregate = candidate['contract']=='research.task_aggregation'
    if aggregate:
        if candidate['scheduled'] != incumbent['scheduled']:
            return dict(relation='unavailable',reason='SCHEDULE_COUNT_MISMATCH')
        if (candidate['task_family'],candidate['protocol_id'],candidate['schedule_identity']) != (incumbent['task_family'],incumbent['protocol_id'],incumbent['schedule_identity']):
            return dict(relation='unavailable',reason='TASK_ACCEPTANCE_SCHEDULE_MISMATCH')
        unresolved=comparison_prerequisites(candidate,incumbent)
        if unresolved:
            return dict(relation='unavailable',reason='Comparison prerequisites unresolved',unresolved=unresolved)
        left, right = candidate['joint_acceptance_fraction'], incumbent['joint_acceptance_fraction']
    else:
        if (candidate['task_identity'],candidate['protocol_id']) != (incumbent['task_identity'],incumbent['protocol_id']):
            return dict(relation='unavailable',reason='TASK_ACCEPTANCE_IDENTITY_MISMATCH')
        if candidate['accepted'] is None or incumbent['accepted'] is None:
            return dict(relation='unavailable',reason='Missing, invalid or incomplete acceptance is not a physical failure')
        for result in (candidate, incumbent):
            issue = _outcome_issue(result) or _source_issue(result)
            if issue:
                return dict(relation='unavailable',reason=issue)
        left,right = int(candidate['accepted']),int(incumbent['accepted'])
    if left != right:
        names=(('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
               if candidate['task_family']=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error'))
        components={n:dict(candidate=candidate['metrics'].get(n),incumbent=incumbent['metrics'].get(n),
            change=candidate['metrics'][n]-incumbent['metrics'][n]) for n in names
            if all(_number(v['metrics'].get(n)) for v in (candidate,incumbent))}
        return dict(relation='improved' if left>right else 'worse',basis='primary_joint_acceptance',
                    componentwise=components)
    names = (('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
             if candidate['task_family']=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error'))
    if any(not _number(v['metrics'].get(n)) for v in (candidate,incumbent) for n in names):
        return dict(relation='unavailable',reason='Component metrics missing')
    changes = {n:candidate['metrics'][n]-incumbent['metrics'][n] for n in names}
    better, worse = any(v < -tolerance for v in changes.values()), any(v > tolerance for v in changes.values())
    return dict(relation='tradeoff' if better and worse else 'improved' if better else 'worse' if worse else 'equivalent',
                basis='componentwise_physical_metrics',changes=changes,
                componentwise={n:dict(candidate=candidate['metrics'][n],incumbent=incumbent['metrics'][n],change=changes[n]) for n in names},
                computation='reported separately')


def stop_interpretation(result, reason, *, budget_exhausted=False, remaining_work=0, operational=None, assertions=()):
    """A legal stop and a supported success claim do not prove an optimal stop."""
    aggregate = result.get('contract')=='research.task_aggregation'
    accepted = result.get('all_scheduled_accepted',False) if aggregate else result.get('accepted') is True
    legal = ((reason=='budget_exhausted' and budget_exhausted) or
             (reason=='completed_schedule' and remaining_work==0) or
             reason in ('predeclared_policy','voluntary_stop','limited_value','engineering_blocker'))
    checked=[]
    for assertion in assertions:
        resource=assertion.get('resource');field=assertion.get('field')
        values=(operational or {}).get(field) if field in (
            'executable_capacity','plan_shortfall','actual_shortfall') else None
        observed=values.get(resource) if isinstance(values,dict) else None
        checked.append(dict(assertion=assertion,observed=observed,
            support='not_assessed' if observed is None else 'supported' if observed==assertion.get('value') else 'unsupported'))
    explanation=('unsupported' if any(r['support']=='unsupported' for r in checked) else
        'supported' if checked and all(r['support']=='supported' for r in checked) else 'not_assessed')
    return dict(legal=legal,reason=reason,success_claim_supported=accepted,
                explanation_support=explanation,checked_assertions=checked,
                optimality='not_assessed',acceptance_result=result,
                budget_is_upper_bound=True)
