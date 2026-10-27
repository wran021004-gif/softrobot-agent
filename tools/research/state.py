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
    linked=list(s.get('analysis_results',[]))+list(s.get('search_results',[]))+list(s.get('joint_results',[]))
    linked += [r for e in s['spec'].get('research_decisions',{}).get('background',[]) for r in e.get('dependencies',[])]
    linked += [entry['reference'] for entry in s.get('stage_context',[])]
    linked += list(s.get('runtime_capabilities',{}).values())
    linked += list(s.get('control_search_results',[]))
    linked += [e[k] for e in s.get('control_initializations',[]) for k in ('candidate','source')]
    linked += list(s.get('research_mathematics',[]))
    linked += [e[k] for e in s.get('research_history',[]) for k in ('reference','source','candidate','historical_candidate')]
    if host:
        linked += [host.store.artifact(e['reference'])['raw_reference'] for e in s.get('research_history',[])]
        for ref in s.get('physical_replays',[]):
            replay=host.store.artifact(ref)
            linked += [replay[k] for k in ('source_reference','raw_reference','evaluation_reference','profile_reference') if replay.get(k)]
    if host:
        if s.get('pilot',{}).get('handoff'):
            preparation=host.store.artifact(s['pilot']['handoff'])
            linked += [r['feedback_reference'] for r in preparation.get('pending_feedback_delivery',{}).get('items',[])]
        from extensions.tendon_family.control_evidence import ControlEvidence
        for ref in s.get('results',[]):
            result=host.store.artifact(ref)
            if result.get('profile',{}).get('motion'):linked.append(result['profile']['motion'])
            try:linked.extend(ControlEvidence(host.store).resolve(result['execution_id'])['files'].values())
            except (ValueError,KeyError):pass
        for ref in s.get('mechanics_results',[]):
            result=host.store.artifact(ref)
            linked.extend(result[k] for k in ('checkpoint_reference','trajectory_reference','original_request','log_reference') if result.get(k))
    return [*s['results'], *s.get('mechanics_results', []), *s.get('physical_replays', []), *s.get('matched_state_results', []), *s.get('rl_evaluations', []), *s.get('rl_training_summaries', []),
        *s.get('scoped_context',[]), *s.get('imported_mechanics_sources',[]), *s.get('imported_mechanics_results',[]), *s.get('linked_selections',[]), *s.get('historical_confirmations',[]), *linked,
        *[s[k] for k in ('rl_task','rl_source_summary','rl_source_candidate','family_space_reference','public_prior_manifest') if s.get(k)],
        *[r for entry in s.get('rl_runs',{}).values() for r in (entry.get('candidate'),entry.get('configuration')) if r]]

from tools.research.budget import (protected, closeout_operations, admit_closeout,
    charge_start, allowance, repetition_reserve, nmpc_timing, capacity)


def enabled(spec, capability):
    return capability in spec.get('capabilities', ['rl'] if spec.get('mode')=='rl_interface' else ['mathematics','search','nmpc'])

def confirmation_count(s):
    return s['spec']['confirmation']['fresh_independent_repetitions']

SCIENCE_FILES = ['extensions/tendon_family/'+n+'.py' for n in ('gvs_nmpc','gvs_trajectory','gvs_projection','contracts','control_evidence','backends','generated_serial','gvs_profile','gvs_codesign','gvs_casadi','gvs','gvs_basis','math_analysis','compiler','sections','geometry','manifest')]
SCIENCE_FILES += ['extensions/optimization/contracts.py','extensions/optimization/ipopt.py','extensions/math_analysis/tools.py','extensions/math_analysis/kernels.py','schemas/platform_analysis.py','tools/execution_completion.py','tools/research_tasks.py']
SCIENCE_FILES += ['extensions/math_analysis/trajectory.py','extensions/math_analysis/task_capability.py','tools/research/capability.py']
SCIENCE_FILES += ['extensions/math_analysis/conic_capability.py','extensions/math_analysis/capability_sensitivity.py']
SCIENCE_FILES += ['extensions/tendon_family/family_space.py']
SCIENCE_FILES += ['extensions/tendon_family/mujoco_analysis.py']
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

def require_authorization(host):
    """New opt-in studies require local approval bound to their frozen identity."""
    s=state(host)
    if not s['spec']['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'):return
    from tools.state_io import digest
    for event in reversed(host.store.events(host.run_id)):
        if event['kind']!='formal_study_authorization':continue
        approval=host.store.artifact(event['outputs'][0])
        scope=approval.get('scope',{})
        if (approval.get('user_approval') and approval.get('scope_identity')==digest(scope)
                and scope.get('resolved_identity')==s['spec']['resolved_identity']
                and scope.get('study_id')==host.run_id):return
    raise ValueError('INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED_BEFORE_PROVIDER_OR_SCIENCE')


def bounded_worker_timeout(host):
    """Opt-in P2 worker boundary; existing count-only studies remain unchanged."""
    s=state(host)
    policy=s['spec'].get('numerical_execution_guard')
    if policy is None:return None
    remaining=policy['limit_s']-s['numerical_s']-policy['margin_s']
    if remaining<=0:raise ValueError('BOUNDED_NUMERICAL_ALLOWANCE_EXHAUSTED')
    return min(policy['worker_timeout_s'],remaining)


def guard(host, expensive=False):
    s=state(host)
    require_authorization(host)
    bounded_worker_timeout(host)
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
