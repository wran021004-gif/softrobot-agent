"""Store state, immutable evidence, implementation identities and shared guards."""
from pathlib import Path
import hashlib
from tools.platform_store import plain
ROOT=Path(__file__).resolve().parents[2]

def save(host, value, kind='core_evidence'):
    with host.store.transaction() as db:
        ref = host.store.put(db, value)
        host.store.event(db, host.run_id, kind, 'saved', outputs=[ref])
        return plain(ref)

def state(host):
    return host.store.session(host.run_id)['state']

def update(host, **values):
    with host.store.transaction() as db:
        s = host.store.session(host.run_id, db)['state']
        s.update(values)
        host.store.update_state(db, host.run_id, s)

def readable_results(s, host=None):
    linked=list(s.get('analysis_results',[]))+list(s.get('search_results',[]))
    linked += list(s.get('runtime_capabilities',{}).values())
    if host:
        for ref in s.get('mechanics_results',[]):
            result=host.store.artifact(ref)
            linked.extend(result[k] for k in ('checkpoint_reference','trajectory_reference','original_request','log_reference') if result.get(k))
    return [*s['results'], *s.get('mechanics_results', []), *s.get('physical_replays', []), *s.get('rl_evaluations', []), *s.get('rl_training_summaries', []),
        *s.get('scoped_context',[]), *s.get('imported_mechanics_sources',[]), *s.get('imported_mechanics_results',[]), *s.get('linked_selections',[]), *s.get('historical_confirmations',[]), *linked,
        *[s[k] for k in ('rl_task','rl_source_summary','rl_source_candidate','family_space_reference') if s.get(k)],
        *[r for entry in s.get('rl_runs',{}).values() for r in (entry.get('candidate'),entry.get('configuration')) if r]]

from tools.research.budget import (protected, closeout_operations, admit_closeout,
    charge_start, allowance, repetition_reserve, nmpc_timing, capacity)


def enabled(spec, capability):
    return capability in spec.get('capabilities', ['rl'] if spec.get('mode')=='rl_interface' else ['mathematics','search','nmpc'])

def confirmation_count(s):
    return s['spec']['confirmation']['fresh_independent_repetitions']

SCIENCE_FILES = ['extensions/tendon_family/'+n+'.py' for n in ('gvs_nmpc','gvs_trajectory','gvs_projection','contracts','control_evidence','backends','generated_serial','gvs_profile','gvs_codesign','gvs_casadi','gvs','gvs_basis','math_analysis','compiler','sections','geometry','manifest')]
SCIENCE_FILES += ['extensions/optimization/contracts.py','extensions/optimization/ipopt.py','extensions/math_analysis/tools.py','extensions/math_analysis/kernels.py','schemas/platform_analysis.py','tools/execution_completion.py','tools/research_tasks.py']
SCIENCE_FILES += ['extensions/math_analysis/trajectory.py']
SCIENCE_FILES += ['extensions/tendon_family/family_space.py']
SCIENCE_FILES += ['tools/rl/'+name+'.py' for name in ('env','train','checks','continuation')]
CORE_FILES = ['tools/research/'+p.name for p in (ROOT/'tools/research').glob('*.py')]
CORE_FILES += ['tools/service_execution.py','tools/rl/env.py','tools/rl/run.py','tools/rl/train.py','tools/rl/checks.py','tools/rl/continuation.py']


def science_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SCIENCE_FILES}

def core_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CORE_FILES}

def limits(spec):
    b = spec['budgets']
    return dict(model_calls=b['provider_requests'], tool_calls=b['public_operations'],
        backend_solves=b['physical_launches'], worker_calls=0, wall_s=b['activity_s'])

def guard(host, expensive=False):
    s=state(host)
    if s['research_status']=='stopped':
        raise ValueError('ACCEPTED_STOP_SEALED')
    if expensive and s.get('success_gate'):
        raise ValueError('FRESH_TASK_PASS_REQUIRES_IMMEDIATE_CLOSEOUT')
    if s['pending']:
        raise ValueError('PENDING_EXECUTION_RECOVER_WITHOUT_NEW_LAUNCH')
    if 'freeze' not in s:
        raise ValueError('COMMIT_AND_BIND_BEFORE_RESEARCH')
    if s.get('validation_extension_pending_binding'):
        raise ValueError('AUTHORIZED_EXTENSION_REQUIRES_COMMITTED_EXPLICIT_MIGRATION')
    if science_hashes()!=s['profile']['science_hashes'] or core_hashes()!=s.get('core_hashes') or not host.compatibility()['compatible']:
        raise ValueError('DEPENDENCIES_CHANGED_COMMIT_AND_MIGRATE_WITHOUT_RESETTING_COSTS')
    if s['spec'].get('mode') == 'engineering_numerical':
        if host.store.remaining()['used']['model_calls'] or s['pilot']['live_model_requests']:
            raise ValueError('NUMERICAL_MODE_MODEL_REQUEST_VIOLATION')
    elif expensive and protected(host):
        raise ValueError('PROTECTED_CLOSEOUT_REQUIRES_EXISTING_WORK_OR_STOP')
