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
    return dict(research_plan=[a for a in ('stop','confirm') if a in s['spec'].get('allowed_plan_actions',('stop','confirm'))],
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
