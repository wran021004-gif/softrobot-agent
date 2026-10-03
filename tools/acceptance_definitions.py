"""Interpret frozen contracts; never re-evaluate an archived outcome."""
from tools.platform_store import plain

RANKING = dict(version='1.0.0',rule='Joint acceptance first; otherwise componentwise physical comparison.',
    physical_metrics=['terminal_error_m','holding_max_error_m','holding_max_speed_m_s'],
    tolerance=1e-9,tradeoff='Any physical improvement accompanied by physical worsening is a trade-off, not overall improvement.',
    computation='Reported separately; never substitutes for reach or holding acceptance.',
    objective='Raw scalar objectives under different weights are not ranked.')


def resolve_acceptance(configuration, reference=None, *, profile=None, profile_reference=None, comparison=None):
    value = plain(configuration)
    effective = value.get('effective', value)
    task = effective['task']; controller = effective['policy']['controller']
    timing = task['timing']; evaluator = task['evaluator']
    missing = []
    def field(value, unit, definition, pointer, authority=reference):
        if value is None:
            missing.append(pointer)
        return dict(value=value, unit=unit, definition=definition,
                    source=dict(reference=authority, pointer=pointer))
    prefix = '/effective' if 'effective' in value else ''
    tolerance = evaluator['parameters']['data'].get('tolerance_m') if evaluator['extension_id']=='evaluate.reach' else None
    settling = controller['parameters']['data'].get('settling')
    historical = None
    # This is the explicit original profile contract, not a current default.
    if settling is None and controller['extension_id']=='controller.gvs_nmpc' and controller['version'] in ('1.0.0','2.0.0'):
        from extensions.tendon_family.gvs_profile import SampledSettling
        settling = plain(SampledSettling())
        historical = dict(contract='gvs_profile.settling_for',controller_version=controller['version'],
                          implementation='extensions/tendon_family/gvs_profile.py::settling_for',
                          definition='Historical v1/v2 profile uses the frozen SampledSettling contract.')
    settling = settling or {}
    duration = timing.get('duration_s'); window = settling.get('window_s'); period = timing.get('sample_period_s')
    start = duration-window if duration is not None and window is not None else None
    base = prefix+'/policy/controller/parameters/data/settling/'
    detail = (profile or {}).get('detail', profile or {})
    return dict(contract='platform.acceptance_definition',version='1.0.0',
        terminal=field(tolerance,'m','Euclidean world tip position error at the final execution sample; sealed evaluate.reach is the outcome authority.',prefix+'/task/evaluator/parameters/data/tolerance_m'),
        holding=dict(duration=field(window,'s','Final closed interval [task duration - window, task duration].',base+'window_s'),
            interval_s=[start,duration] if start is not None else None,
            position=field(settling.get('position_limit_m'),'m','Maximum sampled world tip position error in the final interval.',base+'position_limit_m'),
            speed=field(settling.get('speed_limit_m_s'),'m/s','Maximum sampled world tip translational speed norm in the final interval.',base+'speed_limit_m_s'),
            coverage=dict(expected_sample_count=round(window/period)+1 if window is not None and period else None,
                definition='Both endpoints, timestamps aligned to task sample_period_s; missing samples are unavailable, never a pass.',
                recorded_available=detail.get('sampled_settling',{}).get('available'),
                source=dict(reference=profile_reference,pointer='/detail/sampled_settling/available')),
            continuous_time_guarantee=False),
        speed=dict(definition='Euclidean norm of tip-site translational Jacobian times recorded backend qvel, reconstructed with sealed robot.xml and qpos; no finite differencing',
            unit='m/s',frame='world',implementation='extensions/tendon_family/gvs_reporting.py::reconstruct_motion',
            source=dict(reference=detail.get('motion'),pointer='/*/tip_speed_m_s')),
        timing=dict(control_period=field(timing.get('control_period_s'),'s','Simulated control spacing; synchronous wall overruns do not imply skipped applied updates or injected actuator delay.',prefix+'/task/timing/control_period_s'),
            sample_period=field(period,'s','Retained backend sampling interval.',prefix+'/task/timing/sample_period_s'),
            duration=field(duration,'s','Simulated task horizon, separate from computation wall time.',prefix+'/task/timing/duration_s'),
            interpretation='Applied updates, initialization selections, simulated duration and measured wall time are separate facts.'),
        comparison=dict(policy=(comparison or {}).get('ranking_rule',RANKING),
            source='sealed campaign_comparison.ranking_rule' if comparison else 'tools/acceptance_definitions.py::RANKING (settling campaign v1)',
            applicable=task['family']=='task.reach'),historical_contract=historical,missing=missing)


def feedback_acceptance(store, feedback, *, db=None):
    result = feedback.get('execution') or {}
    facts = result.get('factual_result') or feedback.get('baseline_facts') or {}
    ref = facts.get('configuration')
    if not ref:
        return None
    profile_ref = (facts.get('report') or {}).get('reference')
    return resolve_acceptance(store.artifact(ref,db=db),ref,
        profile=store.artifact(profile_ref,db=db) if profile_ref else None,
        profile_reference=profile_ref,comparison=feedback.get('campaign_comparison'))
