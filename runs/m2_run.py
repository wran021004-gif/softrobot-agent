"""M2 operator checks around the unchanged research entry point; no science choices."""
import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.platform_host import Host
from tools.research import core
from tools.research.agent import converse, record
from tools.research.state import state, guard
from tools.research.design import verify_candidate, final_fidelity_matches


def supervised_dispatch(host, value, request_id, **kwargs):
    action = value.get('action')
    if action in ('execute', 'physical_replay'):
        s = state(host)
        payload = value if action == 'execute' else (value.get('physical_replay') or {})
        ref = payload.get('candidate')
        if ref is None:
            return original_dispatch(host, value, request_id, **kwargs)
        candidate = verify_candidate(host, ref)
        recipe = candidate['configuration']['policy']['controller']['parameters']['data']['recipe']
        expected = dict(replan_period_s=.1, horizon=10, substeps=1, tolerance=1e-6)
        if any(recipe[k] != v for k, v in expected.items()) or recipe['max_iterations'] > 120:
            raise ValueError('M2_FROZEN_CONTROLLER_COMPUTATION_LIMITS_REQUIRED')
        if not final_fidelity_matches(s['spec'], candidate):
            raise ValueError('M2_FINAL_FIDELITY_REQUIRED_BEFORE_PHYSICAL_LAUNCH')
        prior = [(host.store.artifact(r), route) for key, route in
                 (('results', 'execute'), ('physical_replays', 'physical_replay')) for r in s.get(key, [])]
        if sum(route == 'execute' for _, route in prior) != s.get('nmpc_launches', 0):
            raise ValueError('M2_UNSETTLED_NMPC_OPPORTUNITY_REQUIRES_REVIEW')
        if sum(route == 'physical_replay' for _, route in prior) != s.get('physical_replay_launches', 0):
            raise ValueError('M2_UNSETTLED_REPLAY_OPPORTUNITY_REQUIRES_REVIEW')
        used = [(host.store.artifact(p['candidate'])['physical_design_identity'], route) for p, route in prior]
        physical = candidate['physical_design_identity']
        if host.run_id == 'b3-t2-050-c-v2-draft':
            if len({physical, *(p for p, _ in used)}) > 2 or (physical, action) in used:
                raise ValueError('M2_C_TWO_STRUCTURES_ONE_NMPC_ONE_REPLAY_EACH')
        record(host, 'supervisor_physical_preflight', dict(candidate=ref, action=action,
            request_id=request_id, physical_design_identity=physical, computation_limits=expected,
            max_iterations=recipe['max_iterations'], prior_opportunities=used, admitted=True))
    return original_dispatch(host, value, request_id, **kwargs)


original_dispatch = core.dispatch
core.dispatch = supervised_dispatch
run = sys.argv[1]
assert run in ('b3-t2-050-b-v2-draft', 'b3-t2-050-c-v2-draft')
host = Host(ROOT/'runs/research'/run, run, actor='unified-research')
guard(host)
reviewed = '--reviewed' in sys.argv[2:]
if reviewed:
    pauses = [e for e in host.store.events(run) if e['kind'] == 'supervisor_pause']
    if not pauses:
        raise ValueError('M2_REVIEW_REQUIRES_ORIGINAL_SETTLED_SUPERVISOR_PAUSE')
    record(host, 'supervisor_budget_review', dict(pause=pauses[-1]['outputs'][0],
        budget=host.store.remaining(), additional_budget=0, protected_provider_requests=4,
        decision='Continue the same Agent and frozen scope within the original remaining counts; no scientific direction supplied'))
record(host, 'supervisor_run', dict(pid=os.getpid(), runner='runs/m2_run.py',
    scope='Only frozen computation and physical opportunity checks; original dispatch, ledger and tools unchanged'))
asyncio.run(converse(host, session_handoff=True, handoff_request_bytes=160000,
    pause_exploration_remaining=None if reviewed else 4))
