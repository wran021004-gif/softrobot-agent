"""Prepare the user-authorized Reach/Hold Study without choosing scientific actions."""
import hashlib
import json
import subprocess
from pathlib import Path
from tools.research.config import ROOT, resolve
from tools.research.core import prepare, bind
from tools.research.state import state, save, require_authorization
from tools.research.agent import pending
from tools.state_io import digest

SPEC=ROOT/'configs/research/study_reach_hold_native_autonomous.json'
REQUEST=Path('C:/Users/gugugaga/.codex/attachments/9715d1fb-7b11-4e81-856f-d955fb8266f8/已粘贴的文本.txt')


def prepare_authorized():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('CLEAN_COMMITTED_IMPLEMENTATION_REQUIRED')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','rev-parse','origin/integration/research-next'],cwd=ROOT,text=True).strip()
    if commit!=remote:raise ValueError('PUSHED_IMPLEMENTATION_REQUIRED')
    spec=resolve(SPEC); run=ROOT/'runs/research'/spec['study_id']
    if run.exists():raise ValueError('EXISTING_STUDY_MUST_BE_INSPECTED_NOT_RECREATED')
    if (spec['supplied_evidence'] or any(spec['research_decisions'][k] for k in ('history','mathematics','control_seeds'))
        or spec['family_search']['evaluation_modes']!=['mujoco_control']
        or set(spec['mathematical_methods'])!={'mujoco-nonlinear-task-capability-v1'}
        or spec['runtime']['provider']['max_tokens'] is not None):raise ValueError('FROZEN_SCOPE_MISMATCH')
    expected=dict(provider_requests=64,protected_provider_requests=8,public_operations=120,
        protected_public_operations=12,physical_launches=6,mathematical_evaluations=12)
    if any(spec['budgets'][k]!=v for k,v in expected.items()) or spec['physical_replay_limit']!=5:
        raise ValueError('FROZEN_BUDGET_MISMATCH')
    h=prepare(SPEC);s=state(h)
    if (s['candidates'] or s['results'] or s['physical_replays'] or s['analysis_results'] or s['selected']
        or s['searches'] or s['pending'] or pending(h) or s['pilot']['live_model_requests']):
        raise ValueError('NEW_STUDY_NOT_EMPTY')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSETTLED_REQUEST')
    scope=dict(study_id=spec['study_id'],code_commit=commit,resolved_identity=spec['resolved_identity'],
        canonical_task_identity=spec['canonical_task_identity'],family_space_identity=spec['family_space_identity'],
        budgets=spec['budgets'],physical_replay_limit=spec['physical_replay_limit'],
        native_control_limits=spec['native_control_limits'],family_search=spec['family_search'],
        mathematical_methods=spec['mathematical_methods'],provider=spec['runtime']['provider'],
        execution_scopes=['Native MuJoCo analysis','independent MuJoCo replay','Reporter','optional historical procedural guidance'],
        source_user_request=dict(path=str(REQUEST),sha256=hashlib.sha256(REQUEST.read_bytes()).hexdigest()),
        empty_candidate_and_evidence_pool_verified=True,unknown_pending_requests_verified_absent=True)
    ref=save(h,dict(user_approval=True,scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    require_authorization(h);bind(h,specification=spec)
    print(json.dumps(dict(study_id=h.run_id,authorization=ref,freeze=state(h)['freeze'],
        resolved_identity=spec['resolved_identity'],remaining=h.store.remaining()),ensure_ascii=False))


if __name__=='__main__':prepare_authorized()
