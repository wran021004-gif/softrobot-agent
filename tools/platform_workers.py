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
from extensions.reference.contracts import WorkStatus

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
        inp = self.store.session(self.run_id)['snapshot']['input']
        if 'workers.submit' not in inp['policy']['allowed_tools']:
            raise ValueError('WORKER_SUBMISSION_NOT_GRANTED')
        if set(order.allowed_tools) - set(inp['policy']['allowed_tools']) or order.allowed_tools != ['evidence.read']:
            raise ValueError('WORKER_TOOL_SCOPE_UNSUPPORTED')
        if order.output_contract != definition.capabilities['output_contract']:
            raise ValueError('WORKER_OUTPUT_CONTRACT_MISMATCH')
        if order.budget.worker_calls != 1 or order.budget.tool_calls != 1 or order.budget.model_calls or order.budget.backend_solves:
            raise ValueError('REFERENCE_WORKER_REQUIRES_ONE_READ_AND_ONE_WORKER_SLOT')
        if order.budget.wall_s < order.timeout_s:
            raise ValueError('WORKER_TIMEOUT_EXCEEDS_WALL_GRANT')
        for dependency in order.dependencies:
            if self._row(dependency)['status'] != 'accepted':
                raise ValueError('WORKER_DEPENDENCY_NOT_ACCEPTED')
        raw = self.store.artifact(order.input_snapshot)
        for name in order.resources:
            if name not in self.store.config()['exclusive_resources']:
                raise ValueError('WORKER_RESOURCE_NOT_GRANTED')
        row, fresh = self.store.reserve(self.run_id, 'worker-' + order.work_id, digest(plain(order)), 'worker:' + order.work_id,
            plain(order.budget), order.resources, parent=parent, inputs=[order.input_snapshot], kind='worker')
        if not fresh:
            return self.status(order.work_id)
        folder = self._folder(order.work_id)
        folder.mkdir(parents=True, exist_ok=False)
        atomic_json(folder / 'order.json', dict(order=plain(order), implementation=dependency_identity(definition)))
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
            output = WorkerOutput.model_validate(read(folder / 'output.json'))
            _, parameters = self.host.reg.bind(order.worker, 'worker')
            if output.work_id != work_id or output.source != order.input_snapshot or output.base_candidate != order.base_candidate or output.signal != parameters.signal:
                return self._finish(work_id, 'failed', reason='WORKER_OUTPUT_IDENTITY_MISMATCH')
            source = self.store.artifact(output.source)
            from schemas.platform import BackendResult
            raw = BackendResult.model_validate(source)
            signal = next((s for s in raw.signals if s.spec.name == output.signal), None)
            if signal:
                if output.sample_indices != list(range(len(signal.values))) or output.values != signal.values or output.status != 'observed':
                    return self._finish(work_id, 'failed', reason='WORKER_SAMPLE_EVIDENCE_MISMATCH')
            elif output.status != 'missing_data' or output.values or output.sample_indices:
                return self._finish(work_id, 'failed', reason='WORKER_MISSING_DATA_MISMATCH')
            return self._finish(work_id, 'completed', output=output)
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
        receipt = self.store.complete(row, dict(request_id=row['request_id'], execution_id=row['execution_id'], caller=row['caller'],
            tool_id='worker.signal', execution_status=status, error=reason, charged=zero()), plain(output) if output else None, elapsed, kind='worker')
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
            self.store.event(db, self.run_id, 'worker_merge', status, caller='coordinator', inputs=[output.source], outputs=[json.loads(row['output'])])
        return WorkStatus(work_id=work_id, status=status, result=json.loads(row['output']), reason=reason)
