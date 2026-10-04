"""Offline preparation only: Stage 3.58's semantic gate remains unaccepted.

The shared coordinate executor supports one varied weight. No new candidate
generation strategy or live launcher is selected without an accepted decision.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples import stage358_confirmation as prior
from extensions.tendon_family.control_evidence import ControlEvidence
from tools.live_batch_execution import verified_historical_result
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero
from tools.state_io import read, atomic_json, digest

EVIDENCE = ROOT / 'evidence/stage359_continuation_20261004'
SOURCES = (
    prior.SOURCES[0],
    ('historical_candidate', prior.HISTORY, prior.SOURCES[1][2]),
    prior.SOURCES[2],
    ('historical_candidate', prior.RUN, '22241105b8984e0daae4530963848953'),
    ('historical_start', prior.RUN, '50618bf23b31464ba4f84c55cd26d1ca'),
)
GRANT = dict(model_calls=8, tool_calls=20, backend_solves=2,
             worker_calls=0, wall_s=4200.)


def require_interpretation_gate():
    gate = read(prior.EVIDENCE / 'milestone3_acceptance.json')
    if not gate['passed'] or not gate['criteria']['accurate_model_interpretation_and_final_decision']:
        raise ValueError('STAGE359_REQUIRES_ACCEPTED_STAGE358_INTERPRETATION')


def reviewed_changes():
    review = prior.reviewed_changes()
    for path in ('extensions/tendon_family/optimization.py','extensions/tendon_family/manifest.py'):
        review[path]=dict(reason='Add a separate finite ask/tell proposal adapter and registration; existing coordinate algorithm, physical equations, simulation/controller and physical contracts unchanged.',
            current_hash=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),historical_hashes=[])
    # Only the already reviewed transport/accounting/scheduling migrations.
    # Every scientific source and contract still must agree exactly.
    for _, directory, execution in SOURCES:
        store = Store(directory)
        owner = ControlEvidence(store).resolve(execution)['owner']
        for dep in store.session(owner)['snapshot']['dependencies'].values():
            for path, row in review.items():
                old = dep['sources'].get(path)
                if old and old not in row['historical_hashes']:
                    row['historical_hashes'].append(old)
    return review


def import_references(host):
    review = reviewed_changes()
    return [verified_historical_result(host, Store(path), execution, role, review)
            for role, path, execution in SOURCES], review


def prepare_references(directory):
    """Verify/import five complete sources in a zero-live-work offline store."""
    store = Store(directory)
    store.create(dict(project_id='stage359-offline-references',
                     grant_id='stage359-offline-references-'+digest(str(store.root))[:12], budget=zero(),
                     authorization_source='Offline verified-history preparation; no provider or numerical work.'))
    source = ControlEvidence(Store(prior.RUN)).resolve(SOURCES[-1][2])
    inp = deepcopy(source['configuration'])
    inp['run_id'] = 'stage359-offline-references'
    inp['policy'].update(budget=zero(), route=None, search=None,
                         allowed_tools=[], tool_bindings={})
    host = Host(directory, inp['run_id'])
    host.create(inp)
    results, review = import_references(host)
    chain = read(prior.RUN / 'chain.json')
    references = dict(
        status='offline_prepared_live_blocked_by_semantic_gate',
        accepted_executable_plan=None, method=None, proposal_sequence=[],
        retained_baseline=results[0]['facts']['candidate'],
        historical_search_start=results[1]['facts']['candidate'],
        search_start=results[-1]['facts']['candidate'],
        immediate_predecessor=results[-1]['facts']['candidate'],
        predecessor_plan=chain['search_plan'],
        predecessor_decision=chain['final_response'],
        predecessor_decision_accepted=False,
        predecessor_store=str(prior.RUN),
        predecessor_gate=str(prior.EVIDENCE / 'milestone3_acceptance.json'),
        complete_historical_records=results,
        excluded_execution='d06d23180c19424faf5ac6618c779173',
        historical_unknown_reservation_s=900.,
        separate_future_grant=GRANT, proposal_cap=4,
        operation_reservations_s=dict(simulation=900, evaluation=30, profile=60),
        interpretation_reserve=dict(wall_s=600, model_calls=4, tool_calls=4),
        fixed_holding_tip_speed_weight=0., terminal_weight_permitted_range=[0., 1.],
        fixed_conditions=['robot', 'material', 'task', 'goal', 'acceptance',
                          'controller.gvs_nmpc@7.0.0', 'timing', 'horizon_policy',
                          'solver_budget', 'initialization_and_warm_start',
                          'all_other_numerical_settings'],
        candidate_generation='Unselected: coordinate domains/step/feedback or an explicit finite set require a new accepted model-authored plan. No exact 0.10/0.25 sequence is promised.',
        live_counts=dict(proposals=0, reuses=0, backend_attempts=0,
                         completed_evaluations=0, completed_profiles=0),
        structure_transition=dict(
            sequence=['fixed structure -> bounded control study',
                      'explicit fixed control -> one structural variable',
                      'reassess before another change'],
            binding='Use existing CandidateInput, immutable plan and fixed_configuration_identity.',
            reuse='Changed structure requires a new complete evaluation. Existing weight records remain references only.',
            authorized_now=False),
        offline_usage=store.remaining(), compatibility_review=review)
    with store.transaction() as db:
        ref = plain(store.put(db, references))
        store.event(db, host.run_id, 'offline_continuation_preparation', 'prepared', outputs=[ref])
    return host, references


def export_offline():
    directory = ROOT / 'runs/stage359_offline_preparation_20261004'
    if directory.exists():
        raise ValueError('PRESERVE_EXISTING_OFFLINE_PREPARATION')
    host, references = prepare_references(directory)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    atomic_json(EVIDENCE / 'offline_references.json', references)
    atomic_json(EVIDENCE / 'compatibility_review.json', references['compatibility_review'])
    from tools.improvement_workflow import archive_store
    archive_store(host.store, EVIDENCE / 'offline', source_stores=[path for _, path, _ in SOURCES])
    files = {str(p.relative_to(EVIDENCE)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in EVIDENCE.rglob('*') if p.is_file() and p.name != 'sha256_manifest.json'}
    atomic_json(EVIDENCE / 'sha256_manifest.json', files)
    print('OFFLINE: five verified records; zero live work; interpretation gate remains blocked.')


if __name__ == '__main__':
    export_offline()
