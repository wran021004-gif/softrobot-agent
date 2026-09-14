"""Copy a sealed design boundary into a new run, retaining every budget charge."""
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from schemas.workbench import DeepSeekConfig
from schemas.design_spec import DesignSpec
from tools.artifact_tools import file_hash
from tools.spec_tools import ROOT, load_yaml
from tools.state_io import read, atomic_json, digest
from tools.workbench import Workbench, owner, source_hashes, runtime


# Only orchestration/presentation may change across this continuation. Everything
# else (including numerical tools, contracts, metrics and settings) must match.
SESSION_FILES = {
    'tools/workbench.py', 'tools/workbench_view.py', 'tools/workbench_catalog.py',
    'tools/workbench_actions.py', 'tools/design_session.py', 'tools/design_actions.py',
    'tools/deepseek_adapter.py', 'tools/design_evidence.py', 'tools/design_continuation.py',
    'schemas/workbench.py', 'examples/workbench.py', 'configs/deepseek.yaml',
    'configs/prompts/design_system.md',
    'tools/design_memory.py', 'tools/native_replay.py', 'examples/native_replay.py',
    # Public contracts and orchestration/presentation only; numerical adapters,
    # evaluators, tasks and physics definitions remain outside this allowlist.
    'schemas/public_tools.py', 'tools/public_catalog.py', 'tools/public_feedback.py',
    'tools/public_gateway.py', 'tools/public_services.py', 'examples/public_tools.py',
    'examples/check_public_tools.py',
    'schemas/dynamic_workbench.py', 'tools/dynamic_campaign.py',
    'tools/dynamic_experiment.py', 'tools/dynamic_view.py',
    'capabilities/README.md', 'agents/contracts/README.md',
}

ROUND_LEDGER = ROOT / 'runs/round8_budget.json'
ROUND_LIMITS = dict(model_calls=12, candidates=1, simulations=1, matlab_calls=3, tool_calls=16, decisions=16)


def start_round(book, source, config_path):
    """The user's one explicit round8 grant; importing twice cannot mint credit."""
    with owner(ROOT / 'runs', '.round8_budget.lock'):
        if ROUND_LEDGER.exists():
            raise ValueError('ROUND_BUDGET_ALREADY_ASSIGNED: resume ' + read(ROUND_LEDGER)['active_root'])
        continue_design(book, source, config_path, new_round=True)
        atomic_json(ROUND_LEDGER, dict(active_root=book.root.relative_to(ROOT).as_posix(), **book.state['request']['round_budget']))
    return book.state


def verify_round_owner(book):
    grant = book.state['request'].get('round_budget')
    if grant:
        ledger = read(ROUND_LEDGER)
        if ledger != dict(active_root=book.root.relative_to(ROOT).as_posix(), **grant):
            raise ValueError('ROUND_BUDGET_BOUND_TO_ANOTHER_RUN: resume the recorded round8 run')


def compatible(request, current, environment):
    prior = request['sources']
    changed = sorted(k for k in prior.keys() | current.keys() if prior.get(k) != current.get(k))
    invalid = [k for k in changed if k not in SESSION_FILES]
    if invalid or request['runtime'] != environment:
        raise ValueError('INCOMPATIBLE_COMPUTATION: ' + str(invalid or ['runtime']))
    return changed


def continue_design(book, source, config_path, *, new_round=False):
    source = Workbench(source).root
    if book.root.exists() or book.root.is_relative_to(source):
        raise ValueError('CONTINUATION_REQUIRES_NEW_SEPARATE_DIRECTORY')
    config = DeepSeekConfig.model_validate(load_yaml(config_path)).model_dump(mode='json')
    with owner(source), owner(source, '.worker.lock'):
        state = read(source / 'state.json')
        request = state['request']
        if request.get('round_budget'):
            raise ValueError('ROUND_ALREADY_IMPORTED: use resume; do not reimport the round budget')
        if not request.get('design_session') or request != read(source / 'request.json'):
            raise ValueError('INVALID_CONTINUATION_SOURCE')
        if any(a['status'] == 'reserved' for a in state['attempts']) or any(m['status'] in ('reserved', 'responded') for m in state['model_calls']):
            raise ValueError('CONTINUATION_REQUIRES_SETTLED_BOUNDARY: finish pending response in original run first')
        for ref in state['evidence'].values():
            path = (source / ref['path']).resolve()
            if not path.is_relative_to(source) or file_hash(path) != ref['sha256']:
                raise ValueError('EVIDENCE_CHANGED: ' + ref['path'])
        current = source_hashes()
        changed = compatible(request, current, runtime())
        limits = ({**ROUND_LIMITS, 'model_calls': min(config['model_calls'], 12)} if new_round else
                  {k: config[k] if k != 'matlab_calls' else config['simulations'] * 3 for k in request['limits']})
        if not new_round and (any(limits[k] > request['limits'][k] for k in limits) or config['computation_retries'] > request['design_session']['computation_retries'] or config['model_failure_retries'] > request['design_session']['model_failure_retries']):
            raise ValueError('CONTINUATION_CANNOT_INCREASE_BUDGET')
        prior = Workbench(source)
        prior.state = state
        used = {k: request['limits'][k] - v for k, v in prior.remaining().items()}
        if not new_round and any(used[k] > limits[k] for k in used):
            raise ValueError('CONTINUATION_LIMIT_BELOW_USED')
        if new_round:
            from tools.design_session import evaluation
            if len(state['candidates']) != 2 or any(not (ev := evaluation(state, c['candidate_id'])) or ev['result']['data'].get('canonical_task_status') not in ('PASS', 'FAIL') for c in state['candidates']):
                raise ValueError('ROUND8_REQUIRES_TWO_EVALUATED_CANDIDATES')
        from tools.closeout_state import verify_run
        for c in state['candidates']:
            if digest(DesignSpec.model_validate(load_yaml(source / c['path'])).model_dump(mode='json')) != c['design_hash']:
                raise ValueError('CANDIDATE_CHANGED')
        for a in state['attempts']:
            if a['tool'] == 'evaluate_candidate' and a.get('result', {}).get('data', {}).get('run'):
                verify_run(source / a['result']['data']['run'])
        shutil.copytree(source, book.root, ignore=shutil.ignore_patterns('*.lock', '*.tmp'))
    # Keep the previous top-level manifests and prompt before installing new ones.
    lineage = book.root / 'lineage' / ('parent_' + file_hash(book.root / 'state.json')[:12])
    lineage.mkdir(parents=True)
    for name in ('request.json', 'state.json', 'source_snapshot.zip', 'index.html', 'design_report.json'):
        shutil.copyfile(book.root / name, lineage / name)
    shutil.copyfile(book.root / 'inputs/system_prompt.md', lineage / 'system_prompt.md')
    book.state = state
    new_request = {**request, 'sources': current, 'runtime': runtime(), 'design_session': config, 'limits': limits,
                   'timeout_s': config['tool_timeout_s'], 'created_at': datetime.now(timezone.utc).isoformat(),
                   'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   'git_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                   'continuation': dict(origin=source.relative_to(ROOT).as_posix(), parent_state_sha256=file_hash(lineage / 'state.json'),
                                        archive=lineage.relative_to(book.root).as_posix(), used=used,
                                        changed_session_files=changed, previous_stop_reason=state.get('stop_reason'))}
    if new_round:
        new_request['round_budget'] = dict(authorization_id='round8-user-grant', baseline=used, limits=limits,
                                          historical_limits=request['limits'], source_state_sha256=file_hash(lineage / 'state.json'),
                                          note='本轮独立新增预算；旧18次模型请求保留在历史账目中，不返还或清零。')
    atomic_json(book.root / 'request.json', new_request)
    with zipfile.ZipFile(book.root / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in current:
            archive.write(ROOT / name, name)
    (book.root / 'inputs/system_prompt.md').write_bytes((ROOT / 'configs/prompts/design_system.md').read_bytes())
    state.update(request=new_request, status='READY', stop_reason=None, context_start=len(state['model_calls']))
    from tools.design_memory import rebuild
    rebuild(book)
    for path in lineage.iterdir():
        book.register(path)
    for name in ('request.json', 'source_snapshot.zip', 'inputs/system_prompt.md'):
        book.register(book.root / name, 'request' if name == 'request.json' else name)
    with owner(book.root):
        book.save()
    return state
