"""Durable, bounded execution around the existing scientific Harness."""
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import zipfile

from schemas.workbench import Decision, WorkbenchResult
from tools.artifact_tools import file_hash
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT
from tools.workbench_catalog import TOOLS, PERMISSIONS, LIMITS, executable_catalog


def source_hashes():
    folders = ('tools', 'schemas', 'controllers', 'metrics', 'matlab', 'capabilities',
               'physics_contracts', 'tasks', 'benchmarks', 'configs', 'agents', 'examples', 'skills')
    paths = [p for folder in folders for p in (ROOT / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.m', '.yaml', '.xml', '.md')]
    paths.append(ROOT / 'requirements.txt')
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)}


def runtime():
    packages = {}
    for name in ('numpy', 'mujoco', 'pydantic', 'PyYAML', 'matlabengine', 'matplotlib', 'Pillow'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return dict(python=sys.version, packages=packages)


@contextmanager
def owner(root, filename='.owner.lock'):
    """OS releases the lock on process death; no stale lock-file deletion needed."""
    with (root / filename).open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def launch(root, folder, timeout):
    with (folder / 'worker.log').open('w', encoding='utf-8') as log:
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen([sys.executable, '-m', 'tools.workbench_worker', str(root), str(folder)],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, **kwargs)
        try:
            code = process.wait(timeout=timeout)
            if code:
                raise RuntimeError(f'Worker exit {code}; see worker.log')
        except BaseException:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise


class Workbench:
    def __init__(self, root, *, launcher=launch):
        self.root = Path(root).resolve()
        if not self.root.is_relative_to((ROOT / 'runs').resolve()) or self.root == (ROOT / 'runs').resolve():
            raise ValueError('Workbench output must be a child of runs/')
        self.launcher = launcher

    def create(self, *, design=ROOT / 'configs/design_tendon_arm.yaml', history=(), simulations=1, replay_run=None, deepseek_config=None):
        config = None
        if deepseek_config:
            from schemas.workbench import DeepSeekConfig
            from tools.spec_tools import load_yaml
            config = DeepSeekConfig.model_validate(load_yaml(deepseek_config)).model_dump(mode='json')
            if replay_run:
                raise ValueError('Model design sessions require new computation, not replay')
        if simulations not in (0, 1):
            raise ValueError('Simulation budget must be 0 or 1')
        self.root.mkdir(parents=True, exist_ok=False)
        with owner(self.root):
            hashes = source_hashes()
            with zipfile.ZipFile(self.root / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, expected in hashes.items():
                    data = (ROOT / name).read_bytes()
                    import hashlib
                    if hashlib.sha256(data).hexdigest() != expected:
                        raise ValueError('Source changed while snapshotting')
                    archive.writestr(name, data)
            (self.root / 'inputs').mkdir()
            (self.root / 'inputs/design.yaml').write_bytes(Path(design).read_bytes())
            replay = None
            if replay_run is not None:
                from tools.closeout_state import verify_run
                from tools.spec_tools import load_yaml, validate_design
                import shutil
                source = Path(replay_run).resolve()
                if not source.is_relative_to(ROOT / 'runs'):
                    raise ValueError('Replay source must be a saved repository run')
                record = verify_run(source)
                if read(source / 'gate_summary.json')['canonical_result'] not in ('PASS', 'FAIL'):
                    raise ValueError('REPLAY_INCOMPLETE: a canonical historical result is required')
                if (record['task_contract_id'] != 'reach_free_v1' or record['control_level'] != 'C1'
                        or record['task_hash'] != file_hash(ROOT / 'tasks/reach_free/task.yaml')
                        or record['environment_hash'] != file_hash(ROOT / 'tasks/reach_free/environment.yaml')
                        or validate_design(load_yaml(source / 'design_input.yaml')) != validate_design(load_yaml(design))):
                    raise ValueError('REPLAY_INPUT_MISMATCH: task, environment, design or controller differs')
                target = self.root / 'inputs/replay' / source.name
                target.mkdir(parents=True)
                for name in ('run.json', *record['artifact_hashes']):
                    destination = target / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / name, destination)
                verify_run(target, file_hash(source / 'run.json'))
                replay = dict(origin=source.relative_to(ROOT).as_posix(), path=target.relative_to(self.root).as_posix(),
                              run_manifest_sha256=file_hash(target / 'run.json'), role='historical_replay',
                              original_git_commit=record['git_commit'])
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
            request = dict(schema_version=1, task='tasks/reach_free', design='inputs/design.yaml',
                           controller='C1', physics='legacy_v1_surrogate',
                           limits={**LIMITS, 'simulations': 0 if replay else simulations, 'matlab_calls': 0 if replay else 2}, permissions=PERMISSIONS,
                           replay=replay,
                           timeout_s=180, created_at=datetime.now(timezone.utc).isoformat(),
                           git_commit=git('rev-parse', 'HEAD'), git_dirty=bool(git('status', '--porcelain')),
                           sources=hashes, runtime=runtime(),
                           scope='framework validation; no search, calibration or canonical override')
            if config:
                request.update(design_session=config, scope='bounded model-directed design within approved envelope',
                               timeout_s=config['tool_timeout_s'],
                               limits={k: config[k] for k in ('tool_calls', 'decisions', 'simulations', 'candidates', 'model_calls')})
                request['limits']['matlab_calls'] = config['simulations'] * 3
            atomic_json(self.root / 'request.json', request)
            self.state = dict(version=1, status='READY', request=request, attempts=[], decisions=[], reuse=[], evidence={})
            for name in ('request.json', 'source_snapshot.zip', 'inputs/design.yaml'):
                self.register(self.root / name, 'request' if name == 'request.json' else name)
            if replay:
                for path in sorted((self.root / 'inputs/replay').rglob('*')):
                    if path.is_file():
                        self.register(path)
            # History is copied byte-for-byte and labelled as context, never a current score/cache hit.
            for index, source in enumerate(history):
                source = Path(source).resolve()
                if not source.is_relative_to(ROOT) or source.suffix != '.json':
                    raise ValueError('History must be a repository JSON evidence file')
                read(source)
                target = self.root / 'inputs' / f'history_{index}.json'
                target.write_bytes(source.read_bytes())
                self.register(target, f'history:{index}')
                self.state['evidence'][f'history:{index}']['origin'] = source.relative_to(ROOT).as_posix()
                self.state['evidence'][f'history:{index}']['role'] = 'historical_context_only'
            if config:
                from tools.design_session import initialize
                initialize(self)
            self.save()
        return self.state

    def register(self, path, evidence_id=None):
        path = Path(path).resolve()
        relative = path.relative_to(self.root).as_posix()
        evidence_id = evidence_id or relative
        self.state['evidence'][evidence_id] = dict(path=relative, sha256=file_hash(path))
        return evidence_id

    def save(self):
        if self.state.get('candidates'):
            from tools.design_evidence import refresh_index
            refresh_index(self)
            from tools.design_session import summary
            atomic_json(self.root / 'design_report.json', summary(self.state))
        atomic_json(self.root / 'state.json', self.state)
        from tools.workbench_view import write_dashboard
        write_dashboard(self.root, self.state)

    def load(self):
        with owner(self.root, '.worker.lock'):
            return self._load_idle()

    def _load_idle(self):
        self.state = read(self.root / 'state.json')
        from tools.design_continuation import verify_round_owner
        verify_round_owner(self)
        for ref in self.state['evidence'].values():
            path = (self.root / ref['path']).resolve()
            if not path.is_relative_to(self.root) or file_hash(path) != ref['sha256']:
                raise ValueError('EVIDENCE_CHANGED: ' + ref['path'])
        if self.state['request'] != read(self.root / 'request.json'):
            raise ValueError('REQUEST_CHANGED')
        if self.state['status'] not in ('STOPPED', 'CAPABILITY_MISSING') and (self.state['request']['sources'] != source_hashes() or self.state['request']['runtime'] != runtime()):
            raise ValueError('SOURCE_OR_RUNTIME_CHANGED: resume requires the recorded revision and environment')
        for attempt in self.state['attempts']:
            if attempt['status'] == 'reserved':
                folder = self.root / attempt['folder']
                # Atomic worker output is the completion boundary. Otherwise keep its cost charged.
                if (folder / 'result.json').exists():
                    result = WorkbenchResult.model_validate(read(folder / 'result.json'))
                else:
                    result = WorkbenchResult(status='interrupted', tool=attempt['tool'], failure_code='INTERRUPTED',
                                             message='Unsealed attempt; reservation remains charged; no automatic replay')
                self.finish(attempt, result)
        return self.state

    def remaining(self):
        used = {name: 0 for name in self.state['request']['limits']}
        used['decisions'] = len(self.state['decisions'])
        if 'candidates' in used:
            used['candidates'] = 1
            used['model_calls'] = len(self.state.get('model_calls', []))
        for attempt in self.state['attempts']:
            for name, count in attempt['cost'].items():
                used[name] += count
        baseline = self.state['request'].get('round_budget', {}).get('baseline', {})
        return {name: cap - (used[name] - baseline.get(name, 0)) for name, cap in self.state['request']['limits'].items()}

    def context(self):
        if self.state.get('candidates'):
            from tools.design_session import model_context
            return model_context(self)
        return dict(request=self.state['request'], attempts=self.state['attempts'],
                    evidence=self.state['evidence'], remaining=self.remaining(), tools=executable_catalog(),
                    decision_schema=Decision.model_json_schema(), result_schema=WorkbenchResult.model_json_schema())

    def finish(self, attempt, result):
        folder = self.root / attempt['folder']
        atomic_json(folder / 'result.json', result.model_dump(mode='json'))
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                self.register(path)
        attempt.update(status='completed', result=result.model_dump(mode='json'),
                       result_ref=(folder / 'result.json').relative_to(self.root).as_posix())
        if self.state.get('candidates'):
            from tools.design_session import finish_candidate
            finish_candidate(self.state, attempt)
        self.state['status'] = 'PAUSED' if result.status == 'interrupted' else 'RUNNING'
        self.save()

    def submit(self, value):
        """Caller holds owner lock and has loaded state. Untrusted JSON is validated before dispatch."""
        from tools.design_continuation import verify_round_owner
        verify_round_owner(self)
        if self.remaining()['decisions'] <= 0:
            self.state.update(status='STOPPED', stop_reason='DECISION_BUDGET_EXHAUSTED')
            self.save()
            return
        row = dict(sequence=len(self.state['decisions']), proposal=value.model_dump(mode='json') if isinstance(value, Decision) else value)
        self.state['decisions'].append(row)
        try:
            decision = Decision.model_validate(row['proposal'])
            if any(ref not in self.state['evidence'] for ref in decision.evidence):
                raise ValueError('UNKNOWN_EVIDENCE')
            if decision.working_memory and any(ref not in self.state['evidence'] for ref in decision.working_memory.evidence):
                raise ValueError('UNKNOWN_MEMORY_EVIDENCE')
            row['evidence_hashes'] = {ref: self.state['evidence'][ref]['sha256'] for ref in decision.evidence}
            if decision.action != 'continue':
                row['status'] = 'accepted'
                self.state.update(status='STOPPED' if decision.action == 'stop' else 'CAPABILITY_MISSING', stop_reason=decision.reason)
                self.save()
                return
            if decision.tool not in TOOLS:
                raise ValueError('CAPABILITY_MISSING: tool is not executable')
            from tools.workbench_catalog import DESIGN_TOOLS, LEGACY_TOOLS
            design_mode = bool(self.state['request'].get('design_session'))
            allowed = set(DESIGN_TOOLS) | {'read_evidence'} if design_mode else LEGACY_TOOLS
            if decision.tool not in allowed:
                raise ValueError('PERMISSION_DENIED: tool is not enabled in this session')
            info = TOOLS[decision.tool]
            arguments = info['schema'].model_validate(decision.arguments).model_dump(mode='json')
            if info['permission'] not in self.state['request']['permissions']:
                raise ValueError('PERMISSION_DENIED')
            binding = {}
            if design_mode:
                from tools.design_session import preconditions
                binding = preconditions(self, decision, arguments)
            completed = {a['tool']: a for a in self.state['attempts'] if a.get('result', {}).get('status') == 'completed'
                         and (not design_mode or a['arguments'].get('candidate_id') == arguments.get('candidate_id'))}
            if any(name not in completed for name in info['requires']):
                raise ValueError('PRECONDITION_FAILED')
            if decision.tool == 'read_evidence':
                ref = self.state['evidence'].get(arguments['evidence_id'])
                if ref is None or not ref['path'].endswith('.json'):
                    raise ValueError('INVALID_INPUT: registered JSON evidence required')
            # A continuation changes the request hash, but completed candidate
            # evaluations remain valid under the verified computation identity.
            if design_mode and decision.tool == 'evaluate_candidate':
                from tools.design_session import evaluation
                previous = evaluation(self.state, arguments['candidate_id'])
                if previous and previous['result']['data'].get('canonical_task_status') in ('PASS', 'FAIL'):
                    row.update(status='reused', result_ref=previous['result_ref'])
                    self.state['reuse'].append(dict(decision=row['sequence'], result_ref=previous['result_ref']))
                    self.save()
                    return
            key = digest(dict(request=self.state['evidence']['request']['sha256'], design=self.state['evidence']['inputs/design.yaml']['sha256'],
                              tool=decision.tool, arguments=arguments, candidate_binding=binding,
                              dependencies={n: self.state['evidence'][completed[n]['result_ref']]['sha256'] for n in info['requires']}))
            cached = next((a for a in self.state['attempts'] if a['key'] == key and a.get('result', {}).get('status') == 'completed'), None)
            if cached:
                row.update(status='reused', result_ref=cached['result_ref'])
                self.state['reuse'].append(dict(decision=row['sequence'], result_ref=cached['result_ref']))
                self.save()
                return
            backend_cost = {} if decision.tool == 'evaluate_design' and self.state['request'].get('replay') else info['cost']
            cost = dict(tool_calls=1, **backend_cost)
            if any(self.remaining()[name] < count for name, count in cost.items()):
                raise ValueError('BUDGET_EXHAUSTED')
        except (ValueError, TypeError) as exc:
            row.update(status='rejected', failure_code=str(exc))
            self.save()
            return
        folder = self.root / 'attempts' / f'{len(self.state["attempts"]):03d}_{decision.tool}'
        folder.mkdir(parents=True)
        attempt = dict(tool=decision.tool, arguments=arguments, key=key, cost=cost, status='reserved',
                       folder=folder.relative_to(self.root).as_posix(), decision=row['sequence'])
        self.state['attempts'].append(attempt)
        row['status'] = 'accepted'
        atomic_json(folder / 'job.json', dict(tool=decision.tool, arguments=arguments))
        self.state['status'] = 'RUNNING'
        self.save()  # Charge before launching, including crashes/timeouts.
        try:
            self.launcher(self.root, folder, self.state['request']['timeout_s'])
            result = WorkbenchResult.model_validate(read(folder / 'result.json'))
        except KeyboardInterrupt:
            self.finish(attempt, WorkbenchResult(status='interrupted', tool=decision.tool, failure_code='INTERRUPTED'))
            raise
        except Exception as exc:
            result = WorkbenchResult(status='failed', tool=decision.tool,
                                     failure_code='TIMEOUT' if isinstance(exc, subprocess.TimeoutExpired) else 'TOOL_ERROR', message=str(exc))
        self.finish(attempt, result)

    def run(self, *, steps=None, decision=None, policy=None):
        from tools.workbench_policy import decide
        with owner(self.root):
            self.load()
            if self.state['request'].get('design_session') and policy is None and decision is None:
                from tools.deepseek_adapter import run_model
                return run_model(self, steps=steps)
            policy = policy or decide
            count = 0
            while self.state['status'] not in ('STOPPED', 'CAPABILITY_MISSING'):
                if steps is not None and count >= steps:
                    self.state['status'] = 'PAUSED'
                    self.save()
                    break
                proposal = decision if decision is not None else policy(self.context())
                self.submit(proposal)
                count += 1
                print(json.dumps(dict(status=self.state['status'], remaining=self.remaining(), decision=self.state['decisions'][-1]), ensure_ascii=True), flush=True)
                if decision is not None:
                    break
        return self.state
