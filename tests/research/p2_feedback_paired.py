"""Explicit P2 continuation: shared-ledger authorization and one real T1.

Nothing runs on import. Later paired decisions must use one frozen feedback
and a shared project reservation; the two closeout pools remain protected.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
from copy import deepcopy
import json
import subprocess
import sys
from tools.platform_host import Host
from tools.platform_store import encode,plain
from tools.research import core,analysis
from tools.research.agent import pending
from tools.research.config import ROOT
from tools.research.state import state,guard,science_hashes
from tools.research.tool_readiness import execution_environment
from tools.state_io import digest

RUN='p2-v3-positive-high-agent-remaining-20261028'
CANDIDATE={'artifact_id':'ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02','media_type':'application/json'}
SOURCE={'artifact_id':'67395ed42e34265a501c1fb6d8ec6f0601a9d860733d1c1911ecc618d9131130','media_type':'application/json'}
BASELINE_ID='d07434e1037975aef3f84bd42d21f5c7847e06f901beed22cbac558f3c687bc3'
T1_KEY='p2-feedback-paired-shared-t1-v1'


def host():
    return Host(ROOT/'runs'/RUN/'private-store',RUN,actor='unified-research')


def clean_commit():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_IMPLEMENTATION_BEFORE_AUTHORIZATION_OR_BIND')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def authorize(h):
    """Append exact user addendum, atomically extend the original grant, then bind."""
    commit=clean_commit();old=state(h);ledger=h.store.remaining()
    if old['spec']['resolved_identity']!=BASELINE_ID or old.get('validation_extension_pending_binding'):
        raise ValueError('EXACT_UNEXTENDED_SOURCE_REQUIRED_NO_REPEAT')
    if ledger['limit']['model_calls']!=8 or ledger['used']['model_calls']!=6 or ledger['remaining']['model_calls']!=2:
        raise ValueError('EXPECTED_ORIGINAL_LEDGER_REQUIRED')
    if old['research_status']!='ready' or old.get('pending') or pending(h) or ledger['occupied'] or old['pilot'].get('unconsumed_response'):
        raise ValueError('SETTLED_SOURCE_BOUNDARY_REQUIRED')
    if old['control_initializations']!=[dict(candidate=CANDIDATE,source=SOURCE,task_acceptance='unmeasured')]:
        raise ValueError('EXACT_SOURCE_CONTROL_REQUIRED')
    if science_hashes()!=old['profile']['science_hashes'] or execution_environment(old['spec'])['status']!='ready':
        raise ValueError('FROZEN_SCIENCE_AND_ENVIRONMENT_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    spec=deepcopy(old['spec']);spec['budgets']['provider_requests']=13
    # Original two reserved requests remain protected; the new segment also
    # retains its two proposed closeout requests, so exploration protects four.
    spec['budgets']['protected_provider_requests']=4
    spec['configuration']['policy']['budget']['model_calls']=13
    spec.pop('resolved_identity')
    with h.store.transaction() as db:
        if h.store.remaining(db=db)!=ledger or h.store.session(RUN,db)['state']!=old:
            raise ValueError('SOURCE_CHANGED_DURING_AUTHORIZATION')
        previous_state=plain(h.store.put(db,old));previous_snapshot=plain(h.store.put(db,h.store.session(RUN,db)['snapshot']))
        authorization=dict(version='p2_feedback_paired_addendum_v1',user_approval=True,
            approval_text='批准将 P2 全局 Provider 上限提高到 13，按待批准方案使用已有候选和控制源开展 T1—真实反馈—自主修订验证；保留原有两次保护额度和历史证据，严格执行预算，不启动 P3。两种 Thinking 模式配对相同反馈及调用条件。',
            previous_state=previous_state,previous_snapshot=previous_snapshot,previous_ledger=ledger,
            provider_limit=13,original_protected=2,new_segment_protected=2,new_segment_provider_limit=5,
            public_remaining_limit=23,math_remaining_limit=2,native_t1_attempts_max=2,
            native_callbacks_per_t1_max=51,numerical_seconds_limit=300,worker_timeout_s=180,
            independent_replays_max=1,candidate=CANDIDATE,control_source=SOURCE,
            paired_condition='same actual shared T1 result, same messages and schema; observe each model output independently',
            p3='PENDING_EXPLICIT_P3_APPROVAL',implementation_commit=commit)
        addendum=plain(h.store.put(db,authorization));spec.setdefault('authorization_addenda',[]).append(addendum)
        spec['resolved_identity']=digest(spec)
        snapshot=deepcopy(h.store.session(RUN,db)['snapshot']);snapshot['input']['policy']['budget']['model_calls']=13
        snapref=h.store.put(db,snapshot)
        config=h.store.config(db);previous_hash=digest(config);config['budget']['model_calls']=13
        db.execute('ATTACH DATABASE ? AS authority',(str(ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(config),config['grant_id'],str(h.store.root),previous_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_GRANT_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(config),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapref.artifact_id,RUN))
        current=h.store.session(RUN,db)['state'];current.update(spec=spec,validation_extension_pending_binding=True)
        current.setdefault('validation_extensions',[]).append(addendum)
        h.store.update_state(db,RUN,current)
        h.store.event(db,RUN,'request_budget_extension','authorized',outputs=[addendum,snapref])
    core.bind(h,reason='User-authorized P2 feedback and paired Thinking comparison; global Provider cap 13, two original plus two segment closeout slots protected, original scientific profile and history preserved')
    guard(h)
    current=state(h)
    if current['profile']!=old['profile'] or current['control_initializations']!=old['control_initializations']:
        raise ValueError('ORIGINAL_SCIENCE_IDENTITY_CHANGED_STOP')
    if h.store.remaining()['used']!=ledger['used']:raise ValueError('AUTHORIZATION_MUST_NOT_SPEND')
    return dict(addendum=addendum,freeze=current['freeze'],ledger=h.store.remaining(),profile_preserved=True)


def shared_t1(h):
    """One explicit fixed-source T1; a saved or uncertain attempt never relaunches."""
    guard(h,True);s=state(h)
    if s['spec']['budgets']['provider_requests']!=13 or s['spec']['budgets']['protected_provider_requests']!=4:
        raise ValueError('EXPLICIT_PAIRED_ADDENDUM_REQUIRED')
    if h.store.remaining()['used']['model_calls']!=6 or s.get('mathematical_evaluations')!=0:
        raise ValueError('UNEXPECTED_SCIENCE_OR_PROVIDER_USAGE')
    if h.store.lookup(RUN,T1_KEY+'-analysis') or s.get('pending'):
        raise ValueError('EXISTING_T1_ATTEMPT_REQUIRES_RECOVERY_NO_RELAUNCH')
    query=dict(candidate=CANDIDATE,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=s['spec']['analysis_protocol'],
        control_optimization=dict(source=SOURCE,settings=dict(version='local_control_search_v2',
            correction_window_s=[0.,.6],knots_s=[0.,.2,.4,.58],evaluation_requests=51,iterations=1)))
    return analysis.dispatch(h,query,T1_KEY,guard=core.guard,origin='user_authorized_shared_t1')


def main():
    if sys.argv[1:] not in (['authorize'],['t1']):raise ValueError('EXPLICIT_COMMAND_REQUIRED: authorize or t1')
    value=authorize(host()) if sys.argv[1]=='authorize' else shared_t1(host())
    print(json.dumps(value,ensure_ascii=True))


if __name__=='__main__':main()
