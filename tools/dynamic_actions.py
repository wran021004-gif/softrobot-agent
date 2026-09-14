"""Trusted dynamic tool bindings; submit owns permissions, budgets and recovery.

Add a schema declaration and one binding here to extend this runtime. New
independent analytic/saved-data tools should use the service registry instead.
"""
import math
from tools.spec_tools import ROOT
from tools.state_io import read, atomic_json, digest
from tools.trajectory_diagnosis import diagnose, metadata_from_shared
from tools.dynamic_context import evidence_page

def analyze_pcc(book, args, evidence, reason):
    from tools.public_services import pcc_jacobian
    return pcc_jacobian(args)

def render_simulation_video(book, args, evidence, reason):
    from tools.simulation_video import render_simulation_video
    return render_simulation_video(book.root, book.state['evidence'], **args)

def create_candidate(book, args, evidence, reason):
    return dict(candidate=book.create_candidate(**args, evidence=evidence, reason=reason))

def simulate_candidate(book, args, evidence, reason):
    return book.simulate(args['candidate_id'], args['backend'], args['purpose'], args['model_id'])

def evaluate_candidate(book, args, evidence, reason):
    return book.simulate(args['candidate_id'], 'mujoco')

def optimize_matlab(book, args, evidence, reason):
    return book.optimize(args, evidence, reason)

def compare_candidates(book, args, evidence, reason):
    return book.compare(args['candidate_ids'], args['offset'], args['limit'])

def diagnose_trajectory(book, args, evidence, reason):
    c = book.candidate(args['candidate_id'])
    r = c['results'].get(args['backend'])
    if not r or not r.get('result_ref'):
        raise ValueError('Backend NOT_RUN')
    source_hashes = book.saved_sources(r)
    folder = (book.root / r['result_ref']).parent
    if args['t_end_s'] < args['t_start_s']:
        raise ValueError('Reversed time window')
    meta = metadata_from_shared(read(folder / 'shared_input.json'), c['candidate_id'], args['backend'], book.root.name)
    d = diagnose(folder / 'trajectory.json.gz', meta, args['entity'], args['t_start_s'], args['t_end_s'], args['fields'])
    d.update(source_hashes=source_hashes, parameters=args, backend_solves=0, rescoring=False, processor='tools.trajectory_diagnosis.diagnose', processor_sha256=__import__('hashlib').sha256((ROOT / 'tools/trajectory_diagnosis.py').read_bytes()).hexdigest())
    path = book.root / f'diagnostics/{digest(args)[:16]}.json'
    atomic_json(path, d)
    book.register(path)
    return {**{k: v for k, v in d.items() if k != 'raw_fields'}, 'raw_fields_ref': path.relative_to(book.root).as_posix()}

def observe_candidate(book, args, evidence, reason):
    c = book.candidate(args['candidate_id'])
    r = c['results'].get(args['backend'])
    if not r or not r.get('result_ref'):
        raise ValueError('Backend NOT_RUN')
    source_hashes = book.saved_sources(r)
    folder = (book.root / r['result_ref']).parent
    from tools.dynamic_view import render_candidate
    path = render_candidate(book.root, c, args['backend'])
    book.register(path)
    metadata = path.with_suffix('.provenance.json')
    atomic_json(metadata, dict(source_hashes=source_hashes, parameters=args, backend_solves=0, rescoring=False, processor='tools.dynamic_view.render_candidate', processor_sha256=__import__('hashlib').sha256((ROOT / 'tools/dynamic_view.py').read_bytes()).hexdigest(), artifact_hashes={path.relative_to(book.root).as_posix(): book.state['evidence'][path.relative_to(book.root).as_posix()]['sha256']}))
    book.register(metadata)
    return dict(candidate_id=c['candidate_id'], backend_solves=0, html_ref=path.relative_to(book.root).as_posix(), metadata_ref=metadata.relative_to(book.root).as_posix())

def read_evidence(book, args, evidence, reason):
    ref = args['evidence_ref']
    book.check_evidence(ref)
    value = read(book.root / ref)
    return evidence_page(value, ref, args.get('pointer', ''), args.get('offset', 0), args.get('limit', 10), args.get('max_bytes', 4000))

def record_verified_diagnosis(book, args, evidence, reason):
    book.check_evidence(args['evidence_ref'])
    d = read(book.root / args['evidence_ref'])
    r = d[args['record_type']][args['record_index']]
    if r['entity_name'] != args['entity_name'] or abs(r['t_start_s'] - args['t_start_s']) > 1e-09 or abs(r['t_end_s'] - args['t_end_s']) > 1e-09:
        raise ValueError('Diagnostic entity/time mismatch')
    if args['field'] not in r['values'] or not math.isclose(r['values'][args['field']], args['value'], rel_tol=1e-06, abs_tol=1e-09):
        raise ValueError('Diagnostic numeric mismatch')
    claim = {**args, 'origin': getattr(book, 'decision_origin', 'codex_development'), 'candidate_id': r.get('candidate_id'), 'provenance': book.action_provenance(), 'verification': 'NUMERIC_ENTITY_TIME_MATCH', 'semantic_text_verification': 'not inferred; structured fields authoritative'}
    book.state['verified_diagnoses'].append(claim)
    atomic_json(book.root / 'verified_diagnoses.json', book.state['verified_diagnoses'])
    return claim

def stop_design(book, args, evidence, reason):
    selected = args.get('selected_candidate_id')
    if selected is not None:
        book.candidate(selected)
    selection = dict(selected_candidate_id=selected, reason=reason, source='stop_design.selected_candidate_id', provenance=book.action_provenance())
    book.state['decisions'][-1]['selection'] = selection
    book.state.update(status='STOPPED', stop_reason=reason)
    if book.experiment():
        book.experiment()['stop_decision_sequence'] = len(book.state['decisions']) - 1
    return dict(status='STOPPED', reason=reason, selected_candidate_id=selected, experiment=book.experiment_summary())
BINDINGS = {'analyze_pcc': analyze_pcc, 'render_simulation_video': render_simulation_video, 'create_candidate': create_candidate, 'simulate_candidate': simulate_candidate, 'evaluate_candidate': evaluate_candidate, 'optimize_matlab': optimize_matlab, 'compare_candidates': compare_candidates, 'diagnose_trajectory': diagnose_trajectory, 'observe_candidate': observe_candidate, 'read_evidence': read_evidence, 'record_verified_diagnosis': record_verified_diagnosis, 'stop_design': stop_design}
