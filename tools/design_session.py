"""Candidate identities and authority for the existing workbench, not a new engine."""
from pathlib import Path
import yaml
from schemas.design_spec import DesignSpec
from tools.spec_tools import ROOT, load_yaml
from tools.state_io import atomic_json, digest, read
from tools.design_envelope import load_envelope, envelope_variables, validate_envelope_design
from tools.task_contract_tools import resolve_task_contract


def initialize(book):
    resolved = resolve_task_contract(ROOT / book.state['request']['task'])
    envelope, source = load_envelope(resolved.grammar)
    design = validate_envelope_design(load_yaml(book.root / 'inputs/design.yaml'), envelope)
    fields = [n for n, f in envelope['fields'].items() if f['optimization_status'] in ('AUTHORIZED', 'AUTHORIZED_DISCRETE')]
    variables = envelope_variables(envelope, fields)
    context = dict(task=resolved.task.model_dump(mode='json'), environment=resolved.environment.model_dump(mode='json'),
                   task_authority=resolved.reference_view(), envelope_source=source.relative_to(ROOT).as_posix(),
                   allowed_changes={n: envelope['fields'][n] for n in fields},
                   fixed_parameters={k: v for k, v in design.model_dump().items() if k not in fields},
                   relational_constraints=envelope['relational_constraints'], envelope=envelope,
                   evaluator=resolved.contract.evaluator, control='C1', physics=envelope['physics_profile'])
    atomic_json(book.root / 'inputs/task_context.json', context)
    policy = dict(policy_id='bounded_model_design_v1', authorization_mode='ENVELOPE_SUBSET', purpose='DESIGN_SEARCH',
                  physics_profile=envelope['physics_profile'], task_contract_id=resolved.contract.contract_id,
                  task_contract_source=resolved.manifest_path.relative_to(ROOT).as_posix(),
                  baseline_design=(book.root / 'inputs/design.yaml').relative_to(ROOT).as_posix(),
                  scientific_status='HUMAN_APPROVED', approval_status='HUMAN_APPROVED', approval_source=envelope['approval_source'],
                  variables=[{k: getattr(v, k) for k in ('name', 'unit', 'lower_bound', 'upper_bound', 'constraints')} for v in variables],
                  objective_metric_refs=['model.predicted_position_error_m', 'mujoco.position_error_m'],
                  evaluation_budget=book.state['request']['limits']['candidates'],
                  mujoco_validation_budget=book.state['request']['limits']['simulations'], seed=0,
                  allowed_model_levels=['M0', 'M1'], allowed_controller_levels=['C1'],
                  repair_iteration_budget=0, repair_actions=[], stop_conditions=['budget_exhausted', 'actions_exhausted'])
    (book.root / 'inputs/experiment.yaml').write_text(yaml.safe_dump(policy), encoding='utf-8')
    from tools.experiment_policy_tools import validate_experiment_policy
    validate_experiment_policy(book.root / 'inputs/experiment.yaml')
    prompt = (ROOT / 'configs/prompts/design_system.md').read_text(encoding='utf-8')
    (book.root / 'inputs/system_prompt.md').write_text(prompt, encoding='utf-8')
    for name in ('task_context.json', 'experiment.yaml', 'system_prompt.md'):
        book.register(book.root / 'inputs' / name)
    book.state.update(candidates=[dict(candidate_id='c000', parent_id=None, design=design.model_dump(mode='json'),
                                      design_hash=digest(design.model_dump(mode='json')), path='inputs/design.yaml',
                                      reason='初始候选，来自用户指定设计', evidence=['request'], changes={})], model_calls=[])


def candidate(state, candidate_id):
    return next((c for c in state['candidates'] if c['candidate_id'] == candidate_id), None)


def evaluation(state, candidate_id):
    return next((a for a in reversed(state['attempts']) if a['tool'] == 'evaluate_candidate'
                 and a['arguments']['candidate_id'] == candidate_id and 'result' in a), None)


def preconditions(book, decision, arguments):
    """Bind checks, cache identity and feedback to the actual candidate bytes."""
    tool = decision.tool
    state = book.state
    if tool == 'create_candidate':
        parent = candidate(state, arguments['parent_id'])
        if parent is None or parent != state['candidates'][-1]:
            raise ValueError('PARENT_REQUIRED: use the latest candidate')
        previous = evaluation(state, parent['candidate_id'])
        if not previous or previous['result_ref'] not in decision.evidence:
            raise ValueError('FEEDBACK_REQUIRED: cite the parent evaluation result before changing design')
        task_context = read(book.root / 'inputs/task_context.json')
        if not set(arguments['changes']) <= set(task_context['allowed_changes']):
            raise ValueError('PARAMETER_NOT_AUTHORIZED')
        design = validate_envelope_design({**parent['design'], **arguments['changes']}, task_context['envelope'])
        arguments['changes'] = {k: getattr(design, k) for k in arguments['changes']}
        if digest(design.model_dump(mode='json')) in {c['design_hash'] for c in state['candidates']}:
            raise ValueError('DUPLICATE_DESIGN: changes must produce a new candidate')
        return dict(parent=parent['design_hash'], feedback=state['evidence'][previous['result_ref']]['sha256'])
    if tool == 'read_evidence':
        return {}
    ids = arguments.get('candidate_ids', [arguments.get('candidate_id')])
    binding = {}
    for cid in ids:
        c = candidate(state, cid)
        if c is None:
            raise ValueError('UNKNOWN_CANDIDATE')
        if digest(DesignSpec.model_validate(load_yaml(book.root / c['path'])).model_dump(mode='json')) != c['design_hash']:
            raise ValueError('CANDIDATE_CHANGED')
        binding[cid] = c['design_hash']
        ev = evaluation(state, cid)
        if tool in ('compare_candidates', 'observe_candidate'):
            if not ev or ev['result']['data'].get('canonical_task_status') not in ('PASS', 'FAIL'):
                raise ValueError('EVALUATION_REQUIRED: no completed actual score for ' + cid)
            binding[cid + '_evaluation'] = state['evidence'][ev['result_ref']]['sha256']
        if tool == 'evaluate_candidate':
            failed = [a for a in state['attempts'] if a['tool'] == tool and a['arguments'].get('candidate_id') == cid
                      and a.get('result', {}).get('status') in ('failed', 'interrupted', 'capability_missing')]
            if len(failed) > state['request']['design_session']['computation_retries']:
                raise ValueError('COMPUTATION_RETRY_EXHAUSTED')
    return binding


def finish_candidate(state, attempt):
    result = attempt['result']
    if attempt['tool'] == 'create_candidate' and result['status'] == 'completed':
        c = dict(result['data']['candidate'])
        if candidate(state, c['candidate_id']) is None:
            c['evidence'] = state['decisions'][attempt['decision']]['proposal']['evidence']
            c['reason'] = state['decisions'][attempt['decision']]['proposal']['reason']
            c['decision'] = attempt['decision']
            state['candidates'].append(c)
    elif attempt['tool'] in ('check_candidate', 'evaluate_candidate', 'observe_candidate'):
        c = candidate(state, attempt['arguments']['candidate_id'])
        c[attempt['tool'] + '_ref'] = attempt['result_ref']


def compact_result(result):
    data = result.get('data', {})
    return dict(status=result['status'], failure_code=result.get('failure_code'), message=result.get('message'), data=data,
                artifacts=result.get('artifacts', []))


def model_context(book):
    state = book.state
    task = read(book.root / 'inputs/task_context.json')
    candidates = []
    for c in state['candidates']:
        ev = evaluation(state, c['candidate_id'])
        candidates.append({**c, 'evaluation': compact_result(ev['result']) if ev else {'status': 'NOT_RUN'}})
    return dict(task={k: v for k, v in task.items() if k not in ('envelope', 'task_authority')},
                authority=task['task_authority']['source_paths'], candidates=candidates,
                remaining=book.remaining(), computation_retries=state['request']['design_session']['computation_retries'],
                decisions=state['decisions'][-4:],
                evidence={k: v for k, v in state['evidence'].items() if k == 'request' or k.endswith(('result.json', 'task_context.json')) or k.startswith('history:')},
                current_phase=state['status'], frozen_truth='task and scoring are read-only; no new physics')


def summary(state):
    rows = []
    for c in state.get('candidates', []):
        ev = evaluation(state, c['candidate_id'])
        data = ev['result']['data'] if ev else {}
        rows.append(dict(candidate_id=c['candidate_id'], parent_id=c['parent_id'], design=c['design'],
                         canonical_task_status=data.get('canonical_task_status', 'NOT_RUN'),
                         position_error_m=data.get('position_error_m'), evaluation_ref=ev['result_ref'] if ev else None,
                         failure_code=ev['result'].get('failure_code') if ev else None))
    scored = [r for r in rows if r['canonical_task_status'] in ('PASS', 'FAIL') and r['position_error_m'] is not None]
    best = min(scored, key=lambda r: (r['canonical_task_status'] != 'PASS', r['position_error_m'])) if scored else None
    live_decisions = {m['decision_sequence'] for m in state.get('model_calls', [])
                      if m.get('transport') == 'official_deepseek' and m.get('status') == 'completed'}
    modified = [c['candidate_id'] for c in state.get('candidates', []) if c.get('parent_id') and c.get('decision') in live_decisions]
    verified = any((ev := evaluation(state, cid)) and ev['result']['data'].get('evidence_role') == 'new_computation'
                   and ev['result']['data'].get('canonical_task_status') in ('PASS', 'FAIL') for cid in modified)
    return dict(status=state['status'], stop_reason=state.get('stop_reason'), candidates=rows, best_candidate=best,
                task_achieved=bool(best and best['canonical_task_status'] == 'PASS'),
                live_model_feedback_modifications=modified, live_model_feedback_loop_verified=verified,
                evidence_role='new_computation', evaluator_authority='metrics.reach.evaluate_reach; original Harness gates')
