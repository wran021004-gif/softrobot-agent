from pathlib import Path
import hashlib,math,os
from copy import deepcopy
from tools.state_io import digest
ROOT=Path(__file__).resolve().parents[2]
"""Store-backed shared state and budget policy, independent of orchestration."""
import time
from tools.platform_store import plain

def save(host, value, kind='core_evidence'):
    with host.store.transaction() as db:
        ref = host.store.put(db, value)
        host.store.event(db, host.run_id, kind, 'saved', outputs=[ref])
        return plain(ref)

def state(host):
    return host.store.session(host.run_id)['state']

def update(host, **values):
    with host.store.transaction() as db:
        s = host.store.session(host.run_id, db)['state']; s.update(values)
        host.store.update_state(db, host.run_id, s)

def readable_results(s, host=None):
    linked=list(s.get('analysis_results',[]))+list(s.get('search_results',[]))
    if host:
        for ref in s.get('mechanics_results',[]):
            result=host.store.artifact(ref)
            linked.extend(result[k] for k in ('checkpoint_reference','trajectory_reference','original_request','log_reference') if result.get(k))
    return [*s['results'], *s.get('mechanics_results', []), *s.get('rl_evaluations', []), *s.get('rl_training_summaries', []),
        *s.get('scoped_context',[]), *s.get('imported_mechanics_sources',[]), *s.get('imported_mechanics_results',[]), *s.get('linked_selections',[]), *s.get('historical_confirmations',[]), *linked,
        *[s[k] for k in ('rl_task','rl_source_summary','rl_source_candidate') if s.get(k)],
        *[r for entry in s.get('rl_runs',{}).values() for r in (entry.get('candidate'),entry.get('configuration')) if r]]

def protected(host):
    s=state(host)
    if s['spec'].get('mode')=='engineering_numerical':return False
    return (host.store.remaining()['remaining']['model_calls']<=s['spec']['budgets']['protected_provider_requests']
        or time.time()>=s['cutoff_unix'])

def closeout_operations(host):
    s=state(host)
    return dict(research_plan=[a for a in ('stop','select','confirm') if a in s['spec'].get('allowed_plan_actions',('stop','select','confirm'))],
        research_rl=[a for a in ('status','stop','evaluate') if s.get('rl_runs') and a in s['spec'].get('allowed_rl_operations',('status','stop','evaluate'))])

def admit_closeout(host, name, value):
    if protected(host) and name in ('research_plan','research_rl'):
        field='action' if name=='research_plan' else 'operation'
        if value.get(field) not in closeout_operations(host)[name]:
            raise ValueError('PROTECTED_CLOSEOUT_REQUIRES_EXISTING_WORK_OR_STOP')

def execution_deadline(host):
    s=state(host)
    return s['started_unix']+s['spec']['budgets']['activity_s'] if protected(host) else s['cutoff_unix']

def charge_start(s):
    """Shared charged starts, including unsuccessful starts; never recycled."""
    limit=s['spec'].get('shared_start_limit')
    if limit is not None:
        if s.get('charged_starts',0)>=limit: raise ValueError('SHARED_CHARGED_START_CEILING')
        s['charged_starts']=s.get('charged_starts',0)+1

def enabled(spec, capability):
    return capability in spec.get('capabilities', ['rl'] if spec.get('mode')=='rl_interface' else ['mathematics','search','nmpc'])

def confirmation_count(s):
    return s['spec']['confirmation']['fresh_independent_repetitions']

SCIENCE_FILES = ['extensions/tendon_family/'+n+'.py' for n in ('gvs_nmpc','gvs_trajectory','gvs_projection','contracts','control_evidence','backends','generated_serial','gvs_profile','gvs_codesign','gvs_casadi','gvs','gvs_basis','math_analysis','compiler','sections','geometry','manifest')]
SCIENCE_FILES += ['extensions/optimization/contracts.py','extensions/optimization/ipopt.py','extensions/math_analysis/tools.py','extensions/math_analysis/kernels.py','schemas/platform_analysis.py','tools/execution_completion.py','tools/research_tasks.py']
CORE_FILES = ['tools/research/'+p.name for p in (ROOT/'tools/research').glob('*.py')]
CORE_FILES += ['tools/service_execution.py','tools/rl/env.py','tools/rl/run.py','tools/rl/train.py','tools/rl/checks.py','tools/rl/config.json']



def science_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SCIENCE_FILES}

def core_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CORE_FILES}

def limits(spec):
    b = spec['budgets']
    return dict(model_calls=b['provider_requests'], tool_calls=b['public_operations'],
        backend_solves=b['physical_launches'], worker_calls=0, wall_s=b['activity_s'])

def allowance(s):
    if s['spec'].get('nmpc_execution_cap_s'): return s['spec']['nmpc_execution_cap_s']
    estimate=s.get('execution_cost_estimate')
    if estimate and estimate['recipe_identity']==digest(s['profile']['recipe']):
        return estimate['total_watchdog_s']
    return sum(s['spec']['execution_allowances'].values())

def repetition_reserve(s):
    return s['spec'].get('diagnostic_protocol', {}).get('repetition_launch_reserve', 1) if s['spec'].get('mode') == 'engineering_numerical' else confirmation_count(s)

def nmpc_timing(host, candidate=None):
    """Historical estimates inform decisions; the persisted hard cap bounds launches."""
    from tools.research.design import verify_candidate
    s=state(host);records=s['spec'].get('nmpc_timing_evidence',[])
    configuration=verify_candidate(host,candidate)['scientific_configuration'] if candidate else None
    matched=[r for r in records if r['scientific_configuration_identity']==digest(configuration)] if configuration else records
    for ref in s.get('results',[]):
        r=host.store.artifact(ref)
        if configuration==r.get('scientific_configuration') and r.get('status')=='evaluated':
            matched.append(dict(complete_execution_s=r['numerical_s'],source=ref))
    estimate=max((r['complete_execution_s'] for r in matched),default=None)
    cap=s['spec']['nmpc_execution_cap_s']
    return dict(available=cap>0,complete_execution_s=estimate,cap_s=cap,
        reservation_s=cap,first_use_available=True,
        reason='Contained full execution under hard cap; matching timing is an estimate only',
        evidence_sources=[r['source'] for r in matched],design_feasibility='not assessed by budget admission')

def capacity(host, requested=1, confirmation=False, *, root_operation=False, candidate=None):
    """Admit internal NMPC launches with configured confirmation slots and time."""
    s=state(host); b=s['spec']['budgets']; a=allowance(s)
    timing=nmpc_timing(host,candidate) if s['spec'].get('nmpc_execution_cap_s') else None
    if timing and not timing['available']: return dict(requested=requested,admitted=0,internal_launches=0,timing=timing)
    if timing: a=timing['reservation_s']
    remaining=host.store.remaining()['remaining']; protect=0 if confirmation else repetition_reserve(s)
    if s['spec'].get('shared_start_limit') is not None:
        remaining=deepcopy(remaining);remaining['backend_solves']=min(remaining['backend_solves'],s['spec']['shared_start_limit']-s.get('charged_starts',0))
    if s['spec'].get('nmpc_limits'):
        remaining=deepcopy(remaining);remaining['backend_solves']=min(remaining['backend_solves'],s['spec']['nmpc_limits']['executions']-s.get('nmpc_launches',0))
    science=b['numerical_s']-s['numerical_s']-s['numerical_reserved_s']
    integration=s.get('validation_reservation',{}) or {}
    required=s['spec'].get('execution_required_integrations',0)
    jobs=max(0,required-s.get('fixed_validation_jobs',0))
    extra=max(0.,jobs*s['spec'].get('mechanics_allowances',{}).get('replay_s',0.)-integration.get('seconds',0.))
    integration_time=jobs*s['spec'].get('mechanics_allowances',{}).get('replay_s',0.)
    delivery_numerical=b.get('delivery_numerical_s',0.)
    available_time=min(science-extra-delivery_numerical, (execution_deadline(host) if confirmation else s['cutoff_unix'])-time.time()-integration_time, remaining['wall_s']-integration_time)
    fit=max(0,min(requested,int(remaining['backend_solves'])-protect,math.floor(available_time/a)-protect,
        (int(remaining['tool_calls'])-4*protect-int(root_operation))//3))
    return dict(requested=requested, admitted=fit, internal_launches=fit, numerical_reservation_s=fit*a,
        confirmation_launch_reserve=protect, confirmation_time_reserve_s=protect*a,
        remaining_numerical_s=science, per_execution_s=a,independent_integration_reserve_s=extra,
        delivery_activity_reserve_s=b['delivery_reserve_s'],delivery_numerical_reserve_s=delivery_numerical,
        remaining_activity_s=s['cutoff_unix']-time.time())

def guard(host, expensive=False):
    s=state(host)
    if s['research_status']=='stopped': raise ValueError('ACCEPTED_STOP_SEALED')
    if s['pending']: raise ValueError('PENDING_EXECUTION_RECOVER_WITHOUT_NEW_LAUNCH')
    if 'freeze' not in s: raise ValueError('COMMIT_AND_BIND_BEFORE_RESEARCH')
    if science_hashes()!=s['profile']['science_hashes'] or core_hashes()!=s.get('core_hashes') or not host.compatibility()['compatible']:
        raise ValueError('DEPENDENCIES_CHANGED_COMMIT_AND_MIGRATE_WITHOUT_RESETTING_COSTS')
    if time.time()>=s['started_unix']+s['spec']['budgets']['activity_s']: raise ValueError('ACTIVITY_DEADLINE_EXHAUSTED')
    if s['spec'].get('mode') == 'engineering_numerical':
        if host.store.remaining()['used']['model_calls'] or s['pilot']['live_model_requests']:
            raise ValueError('NUMERICAL_MODE_MODEL_REQUEST_VIOLATION')
    elif expensive and protected(host):
        raise ValueError('PROTECTED_CLOSEOUT_REQUIRES_EXISTING_WORK_OR_STOP')
