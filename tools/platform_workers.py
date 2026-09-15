"""Coordinator-owned scheduling, shared reservations and conditional merge."""
import json
from pathlib import Path
import subprocess
import sys
import time
from schemas.platform import WorkOrder, WorkerOutput, Budget
from tools.platform_store import plain, encode, zero
from tools.state_io import digest, atomic_json, read
from tools.spec_tools import ROOT
from schemas.platform_operations import WorkStatus

# Live handles are an optimization only; durable reservations survive host death.
PROCESSES = {}


class Coordinator:
    def __init__(self, host):
        self.host, self.store, self.run_id = host, host.store, host.run_id

    def _folder(self, work_id):
        return self.host.folder / 'workers' / work_id

    def _row(self, work_id):
        with self.store.connect(True) as db:
            row = db.execute('SELECT * FROM workers WHERE run_id=? AND work_id=?', (self.run_id, work_id)).fetchone()
        if row is None:
            raise ValueError('WORKER_NOT_FOUND')
        return dict(row)

    def submit(self, value, parent=None):
        order = WorkOrder.model_validate(value)
        definition, parameters = self.host.reg.bind(order.worker, 'worker')
        from tools.platform_registry import dependency_identity
        session_snapshot = self.store.session(self.run_id)['snapshot']
        if session_snapshot.get('parent_run_id'):
            raise ValueError('NESTED_WORKER_DISPATCH_UNSUPPORTED')
        inp = session_snapshot['input']
        if 'workers.submit' not in inp['policy']['allowed_tools']:
            raise ValueError('WORKER_SUBMISSION_NOT_GRANTED')
        if set(order.allowed_tools) - set(inp['policy']['tool_bindings']):
            raise ValueError('WORKER_TOOL_SCOPE_UNSUPPORTED')
        selected = {n: inp['policy']['tool_bindings'][n] for n in order.allowed_tools}
        if order.tool_bindings and order.tool_bindings != selected:
            raise ValueError('WORKER_TOOL_VERSION_NOT_GRANTED')
        order = order.model_copy(update=dict(tool_bindings=selected))
        if order.output_contract != definition.capabilities['output_contract']:
            raise ValueError('WORKER_OUTPUT_CONTRACT_MISMATCH')
        if order.budget.wall_s < order.timeout_s:
            raise ValueError('WORKER_TIMEOUT_EXCEEDS_WALL_GRANT')
        for dependency in order.dependencies:
            if self._row(dependency)['status'] != 'accepted':
                raise ValueError('WORKER_DEPENDENCY_NOT_ACCEPTED')
        raw = self.store.artifact(order.input_snapshot)
        for name in order.resources:
            if name not in self.store.config()['exclusive_resources']:
                raise ValueError('WORKER_RESOURCE_NOT_GRANTED')
        if set(definition.resources) - set(order.resources):
            raise ValueError('WORKER_RESOURCE_SCOPE_MISMATCH')
        row, fresh = self.store.reserve(self.run_id, 'worker-' + order.work_id, digest(plain(order)), 'worker:' + order.work_id,
            {**zero(), 'worker_calls': 1, 'wall_s': order.timeout_s}, definition.resources, parent=parent, inputs=[order.input_snapshot], kind='worker', version=definition.version)
        if not fresh:
            return self.status(order.work_id)
        folder = self._folder(order.work_id)
        folder.mkdir(parents=True, exist_ok=False)
        from tools.platform_host import Host
        from tools.platform_registry import dependency_closure
        child_run = self.run_id + '-work-' + order.work_id
        snapshot = dict(self.store.session(self.run_id)['snapshot'])
        import copy
        snapshot = copy.deepcopy(snapshot)
        snapshot['input']['run_id'] = child_run
        snapshot['input']['policy']['budget'] = plain(order.budget)
        snapshot['input']['policy']['allowed_tools'] = order.allowed_tools
        snapshot['input']['policy']['tool_bindings'] = {n: inp['policy']['tool_bindings'][n] for n in order.allowed_tools}
        snapshot['input_identity'] = digest(snapshot['input'])
        snapshot['parent_run_id'] = self.run_id
        snapshot['worker_parent_id'] = row['parent_id']
        snapshot['worker_order'] = plain(order)
        snapshot['dependencies'].update(dependency_closure([definition], self.host.reg))
        (self.store.root / 'sessions' / child_run).mkdir(parents=True, exist_ok=True)
        self.store.create_session(snapshot)
        atomic_json(folder / 'order.json', dict(order=plain(order), implementation=dependency_identity(definition),
            root=str(self.store.root), child_run=child_run))
        atomic_json(folder / 'input.json', raw)
        with self.store.transaction() as db:
            db.execute('INSERT INTO workers VALUES (?,?,?,?,?,?,?)', (self.run_id, order.work_id, encode(order), 'reserved', None, None, None))
        try:
            with (folder / 'worker.log').open('w', encoding='utf8') as log:
                process = subprocess.Popen([sys.executable, '-m', 'tools.platform_worker', str(folder / 'order.json')], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            PROCESSES[(str(self.store.root), self.run_id, order.work_id)] = (process, time.monotonic())
            with self.store.transaction() as db:
                db.execute("UPDATE workers SET status='running',pid=? WHERE run_id=? AND work_id=?", (process.pid, self.run_id, order.work_id))
                self.store.event(db, self.run_id, 'worker_dispatch', 'running', parent=row['parent_id'], caller='coordinator',
                    request=row['request_id'], execution=row['execution_id'], inputs=[order.input_snapshot])
            return WorkStatus(work_id=order.work_id, status='running')
        except Exception as exc:
            self._finish(order.work_id, 'failed', reason=str(exc))
            return self.status(order.work_id)

    def status(self, work_id):
        # Strictly read-only: observing process completion does not settle the ledger.
        row = self._row(work_id)
        status = row['status']
        folder = self._folder(work_id)
        if status == 'running' and (folder / 'output.json').exists():
            status = 'output_ready'
        elif status == 'running' and (folder / 'failure.json').exists():
            status = 'failure_ready'
        return WorkStatus(work_id=work_id, status=status, result=json.loads(row['output']) if row['output'] else None, reason=row['reason'])

    def collect(self, work_id):
        row = self._row(work_id)
        if row['status'] not in ('running', 'reserved', 'unknown'):
            return self.status(work_id)
        order = WorkOrder.model_validate_json(row['order_json'])
        folder = self._folder(work_id)
        handle = PROCESSES.get((str(self.store.root), self.run_id, work_id))
        if handle:
            process, started = handle
            if process.poll() is None:
                if time.monotonic() - started > order.timeout_s:
                    process.terminate()
                    process.wait(timeout=5)
                    return self._finish(work_id, 'cancelled', reason='WORKER_TIMEOUT')
                return self.status(work_id)
        if (folder / 'output.json').is_file():
            try:
                output = WorkerOutput.model_validate(read(folder / 'output.json'))
                definition, _ = self.host.reg.bind(order.worker, 'worker')
                if output.work_id != work_id or output.source != order.input_snapshot or output.base_candidate != order.base_candidate:
                    raise ValueError('WORKER_OUTPUT_IDENTITY_MISMATCH')
                self.host.reg.parse(output.result)
                child_events = self.store.events(self.run_id + '-work-' + work_id)
                produced = {r['artifact_id'] for event in child_events for r in event['outputs']}
                for ref in output.evidence:
                    self.store.artifact(ref)
                    if ref.artifact_id not in produced:
                        raise ValueError('WORKER_EVIDENCE_NOT_FROM_CHILD_EXECUTION')
                source = self.store.artifact(output.source)
                from importlib import import_module
                module, name = definition.capabilities['result_checker'].split(':')
                getattr(import_module(module), name)(order, output, source, self.host.reg,
                    [self.store.artifact(ref) for ref in output.evidence])
                actual = self.store.remaining(self.run_id + '-work-' + work_id)['used']
                if plain(output.usage) != actual:
                    raise ValueError('WORKER_USAGE_MISMATCH')
                return self._finish(work_id, output.status, output=output, reason=output.error)
            except (ValueError, TypeError, KeyError) as exc:
                return self._finish(work_id, 'failed', reason=str(exc))
        if (folder / 'failure.json').is_file():
            return self._finish(work_id, 'failed', reason=read(folder / 'failure.json')['error'])
        # No process handle and no sealed output: cannot assume cancelled or refund.
        self.store.mark_unknown(self.run_id, 'worker-' + work_id)
        with self.store.transaction() as db:
            db.execute("UPDATE workers SET status='unknown',reason=? WHERE run_id=? AND work_id=?", ('NO_SEALED_WORKER_OUTPUT', self.run_id, work_id))
        return self.status(work_id)

    def _finish(self, work_id, status, output=None, reason=None):
        row = self.store.lookup(self.run_id, 'worker-' + work_id)
        handle = PROCESSES.get((str(self.store.root), self.run_id, work_id))
        elapsed = time.monotonic() - handle[1] if handle else json.loads(row['reserved'])['wall_s']
        order = WorkOrder.model_validate_json(self._row(work_id)['order_json'])
        child_run = self.run_id + '-work-' + work_id
        if status in ('cancelled', 'failed'):
            with self.store.connect(True) as db:
                unfinished = [r[0] for r in db.execute("SELECT request_id FROM calls WHERE run_id=? AND status='running'", (child_run,))]
            for request_id in unfinished:
                self.store.mark_unknown(child_run, request_id)
        receipt = self.store.complete(row, dict(request_id=row['request_id'], execution_id=row['execution_id'], caller=row['caller'],
            tool_id=order.worker.extension_id, tool_version=order.worker.version, execution_status='completed' if status == 'needs_input' else status, error=reason, charged=zero()), plain(output) if output else None, elapsed, kind='worker')
        with self.store.transaction() as db:
            db.execute('UPDATE workers SET status=?,output=?,reason=? WHERE run_id=? AND work_id=?',
                (status, encode(receipt['output']) if receipt.get('output') else None, reason, self.run_id, work_id))
        return self.status(work_id)

    def cancel(self, work_id):
        row = self._row(work_id)
        if row['status'] not in ('running', 'reserved'):
            return self.status(work_id)
        handle = PROCESSES.get((str(self.store.root), self.run_id, work_id))
        if not handle:
            self.store.mark_unknown(self.run_id, 'worker-' + work_id)
            with self.store.transaction() as db:
                db.execute("UPDATE workers SET status='unknown',reason='CANCEL_UNCONFIRMED' WHERE run_id=? AND work_id=?", (self.run_id, work_id))
            return self.status(work_id)
        process = handle[0]
        if process.poll() is not None:
            return self.collect(work_id)
        process.terminate()
        process.wait(timeout=5)
        return self._finish(work_id, 'cancelled', reason='LOCAL_PROCESS_TERMINATED')

    def accept(self, work_id):
        self.collect(work_id)
        with self.store.transaction() as db:
            row = dict(db.execute('SELECT * FROM workers WHERE run_id=? AND work_id=?', (self.run_id, work_id)).fetchone())
            if row['status'] == 'accepted':
                return WorkStatus(work_id=work_id, status='accepted', result=json.loads(row['output']))
            if row['status'] != 'completed':
                return WorkStatus(work_id=work_id, status=row['status'], reason='RESULT_NOT_COMPLETE')
            output = WorkerOutput.model_validate(self.store.artifact(json.loads(row['output']), db=db))
            state = self.store.session(self.run_id, db)['state']
            current = state.get('active_candidate', 'baseline')
            if output.base_candidate != current:
                status, reason = 'stale', 'BASE_CANDIDATE_CHANGED'
            else:
                claims = db.execute('SELECT conclusion FROM merges WHERE run_id=? AND claim_key=?', (self.run_id, output.claim_key)).fetchall()
                conflict = any(r[0] != output.conclusion for r in claims)
                status, reason = ('conflict', 'CONTRADICTING_CLAIM_REQUIRES_REVIEW') if conflict else ('accepted', None)
            if status == 'accepted':
                db.execute('INSERT INTO merges VALUES (?,?,?,?,?)', (self.run_id, work_id, output.claim_key, output.conclusion, row['output']))
            db.execute('UPDATE workers SET status=?,reason=? WHERE run_id=? AND work_id=?', (status, reason, self.run_id, work_id))
            self.store.event(db, self.run_id, 'worker_merge', status, caller='coordinator', inputs=[output.source, *output.evidence], outputs=[json.loads(row['output'])], version='2.0.0')
        return WorkStatus(work_id=work_id, status=status, result=json.loads(row['output']), reason=reason)
