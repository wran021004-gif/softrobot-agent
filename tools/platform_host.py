"""Common host: validate -> authorize -> reserve -> execute -> seal -> observe.

Host construction is a local trusted Python/CLI boundary, not authentication.
"""
import json
from pathlib import Path
import time
from uuid import uuid4
from schemas.platform import ToolRequest, ToolReceipt, SessionInput, EvidenceRef, BackendResult, EvaluationResult
from tools.platform_registry import registry, dependency_identity, dependency_closure
from tools.platform_store import Store, plain, encode, zero
from tools.state_io import digest, atomic_json


class InvocationContext:
    def __init__(self, host, row, request, prepared=None):
        self.prepared = prepared
        self.result_execution = None
        self.host, self.store, self.reg = host, host.store, host.reg
        self.run_id, self.row, self.request = host.run_id, row, request
        self.snapshot = self.store.session(self.run_id)['snapshot']
        self.input = SessionInput.model_validate(self.snapshot['input'])
        allowance=self.input.policy.operation_allowances.get(request.tool_id)
        self.timeout_s=allowance.timeout_s if allowance else self.input.policy.timeout_s
        self.folder = host.folder / 'executions' / row['execution_id']
        self.folder.mkdir(parents=True, exist_ok=False)

    def artifact(self, ref):
        # Project-local evidence read is permitted only when evidence.read granted;
        # work orders receive an immutable input snapshot, not this context object.
        return self.store.artifact(ref)

    def save_artifact(self, value, kind='scientific_artifact'):
        """Persist a large scientific value and return its immutable reference."""
        with self.store.transaction() as db:
            ref = self.store.put(db, value)
            self.store.event(
                db, self.run_id, kind, 'saved', parent=self.row['parent_id'],
                request=self.row['request_id'], execution=self.row['execution_id'],
                caller=self.host.actor, outputs=[ref], version=self.request.tool_version,
            )
        return ref

    def record(self, kind, status, *, inputs=(), outputs=(), candidate=None):
        with self.store.transaction() as db:
            return self.store.event(db, self.run_id, kind, status, parent=self.row['parent_id'],
                request=self.row['request_id'], execution=self.row['execution_id'], caller=self.host.actor,
                inputs=inputs, outputs=outputs, candidate=candidate, version=self.request.tool_version)


class Host:
    def __init__(self, root, run_id, *, actor='local-human', reg=None):
        from pydantic import TypeAdapter
        from schemas.evidence import Identifier
        run_id = TypeAdapter(Identifier).validate_python(run_id)
        self.store = Store(root)
        self.run_id, self.actor, self.reg = run_id, actor, reg or registry()
        self.folder = self.store.root / 'sessions' / run_id

    def create(self, value, *, parent_run_id=None, parent_event_id=None):
        from tools.platform_tasks import compile_input
        import subprocess
        from tools.paths import ROOT
        snapshot = compile_input(value, self.reg)
        if parent_run_id:
            snapshot.update(parent_run_id=parent_run_id, worker_parent_id=parent_event_id)
        if snapshot['input']['run_id'] != self.run_id:
            raise ValueError('RUN_ID_MISMATCH')
        snapshot['project_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        snapshot['worktree_dirty'] = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True))
        self.folder.mkdir(parents=True, exist_ok=True)
        return self.store.create_session(snapshot)

    def compatibility(self):
        snapshot = self.store.session(self.run_id)['snapshot']
        changed = []
        for key, expected in snapshot['dependencies'].items():
            name, version = key.rsplit('@', 1)
            try:
                if dependency_closure([self.reg.get(name, version)], self.reg)[key] != expected:
                    changed.append(key)
            except ValueError:
                changed.append(key)
        return dict(compatible=not changed, changed=changed, action='new session or explicit version migration' if changed else 'resume allowed')

    def discover(self):
        inp = self.store.session(self.run_id)['snapshot']['input']
        rows = self.reg.catalog(inp['policy'].get('tool_bindings') or inp['policy']['allowed_tools'])
        remaining = self.store.remaining(self.run_id)['remaining']
        for row in rows:
            if row['kind'] == 'tool' and remaining['tool_calls'] <= 0:
                row['executable'] = False
                row['reasons'].append('TOOL_BUDGET_EXHAUSTED')
        return rows

    def _receipt(self, request, row, status, error=None, **fields):
        return dict(request_id=request.request_id, execution_id=row['execution_id'], caller=self.actor,
                    tool_id=request.tool_id, tool_version=request.tool_version, execution_status=status, error=error, charged=zero(), **fields)

    def invoke(self, value, *, parent=None):
        from tools.file_lock import owner
        with owner(self.folder, '.platform_call.lock'):
            receipt = self._invoke(value, parent=parent)
            with self.store.transaction() as db:
                state = self.store.session(self.run_id, db)['state']
                state['last_receipt'] = receipt
                self.store.update_state(db, self.run_id, state)
            return receipt

    def _invoke(self, value, *, parent=None):
        started = time.monotonic()
        if parent is None:
            parent = self.store.session(self.run_id)['snapshot'].get('worker_parent_id')
        # Invalid envelopes are recorded as rejection events without inventing a valid request.
        try:
            request = ToolRequest.model_validate_json(json.dumps(value, allow_nan=False), strict=True)
        except (ValueError, TypeError) as exc:
            with self.store.transaction() as db:
                error_ref = self.store.put(db, dict(error=str(exc)))
                self.store.event(db, self.run_id, 'request_validation', 'rejected', parent=parent, caller=self.actor, outputs=[error_ref])
            return dict(execution_status='rejected', error=str(exc), charged=zero())
        request_hash = digest(plain(request))
        old = self.store.lookup(self.run_id, request.request_id)
        if old:
            if old['request_hash'] != request_hash or old['caller'] != self.actor:
                return self._receipt(request, old, 'rejected', 'REQUEST_ID_COLLISION')
            if old['receipt']:
                return json.loads(old['receipt'])
            # Acquired per-session owner lock proves no other invocation is executing.
            self.store.mark_unknown(self.run_id, request.request_id)
            return {
                **self._receipt(request, old, 'unknown', 'NO_SEALED_RECEIPT: reservation retained; no automatic replay'),
                'charged': json.loads(old['charged'])}
        with self.store.transaction() as db:
            request_ref = self.store.put(db, request)
        row = None
        try:
            snapshot = self.store.session(self.run_id)
            inp = SessionInput.model_validate(snapshot['snapshot']['input'])
            role_grant = snapshot['state'].get('role_grant')
            if snapshot['state'].get('role_context',{}).get('decision_only') and request.tool_id!='research.decide':
                raise ValueError('DECISION_ONLY_NO_EXPERIMENT_DISPATCH')
            if role_grant and request.tool_id not in role_grant['permitted_tools']:
                raise ValueError('TOOL_NOT_IN_DIAGNOSTIC_REQUEST_SCOPE')
            if snapshot['status'] in ('paused', 'stopped', 'needs_input', 'capability_missing', 'failed', 'budget_exhausted'):
                raise ValueError('SESSION_NOT_RUNNING: explicitly resume before invoking more tools')
            compatible = self.compatibility()
            if not compatible['compatible']:
                raise ValueError('DEPENDENCIES_CHANGED: ' + repr(compatible['changed']))
            definition = self.reg.get(request.tool_id, request.tool_version, 'tool')
            if inp.policy.tool_bindings.get(request.tool_id) != request.tool_version:
                raise ValueError('TOOL_VERSION_NOT_GRANTED')
            discovery = self.reg.inspect(definition, inp.policy.tool_bindings)
            if not discovery['executable']:
                raise ValueError('; '.join(discovery['reasons']))
            from tools.platform_validation import validate_arguments
            arguments = validate_arguments(definition.input_schema, request.arguments)
            for ref in request.evidence:
                self.store.artifact(ref)
            # References nested in typed input contracts receive the same integrity checks.
            self._validate_refs(plain(arguments), role_archive_read=request.tool_id == 'evidence.read')
            key = digest(dict(tool=request.tool_id, version=request.tool_version, arguments=plain(arguments),
                evidence=[plain(r) for r in request.evidence], input=snapshot['snapshot']['input_identity'], dependencies=dependency_identity(definition)))
            cached = self.store.cache(self.run_id, key) if definition.cache and request.cache == 'reuse' else None
            allowance=inp.policy.operation_allowances.get(request.tool_id)
            cost = {**zero(), 'tool_calls': 1, 'wall_s': allowance.reserve_s if allowance else inp.policy.timeout_s}
            resources = list(definition.resources)
            # Each implementation supplies a preflight hook through its declaration;
            # no software/tool-name routing in the loop or accounting core.
            extra = {}
            preflight = definition.hook('preflight')
            if preflight:
                extra = preflight(inp, arguments, self.reg)
                cost.update(extra.get('cost', {}))
                resources.extend(extra.get('resources', []))
            result_execution = None
            reuse = definition.hook('cache_reuse')
            if cached and reuse:
                result_execution = reuse(self, arguments, extra.get('prepared'), cached)
                if result_execution is None:
                    cached = None
            work_order = snapshot['snapshot'].get('worker_order')
            if work_order and set(resources) - set(work_order['resources']):
                raise ValueError('WORKER_RESOURCE_NOT_GRANTED')
            if cached:
                cost['backend_solves'] = 0
                resources = []
            row, fresh = self.store.reserve(self.run_id, request.request_id, request_hash, self.actor, cost,
                resources, key, parent, [request_ref, *request.evidence], version=definition.version)
            if not fresh:
                raise RuntimeError('REQUEST_RESERVATION_RACE')
            if cached:
                result = self.store.artifact(cached['output'])
            else:
                context = InvocationContext(self, row, request, extra.get('prepared'))
                if definition.legacy_service:
                    result = self._legacy_service(context, definition, arguments)
                else:
                    result = definition.resolve()(context, arguments)
                result_execution = context.result_execution
            # Both fresh objects and cached dictionaries have the declared type.
            result = definition.output_schema.model_validate_json(encode(result), strict=True)
            fields = dict(cache_hit=bool(cached), result_contract=definition.output_schema.__name__, result_version=getattr(result, 'contract_version', definition.version))
            data = plain(result)
            if issubclass(definition.output_schema, BackendResult):
                fields['solver_status'] = data['solver_status']
            if issubclass(definition.output_schema, EvaluationResult):
                fields.update(analysis_status=data['validity'], task_success=data['task_success'])
            if result_execution is not None:
                fields['original_execution_id'] = result_execution['original_execution_id']
            receipt = self._receipt(request, row, 'completed', **fields)
            elapsed = 0. if definition.capabilities.get('delegated_execution') else time.monotonic() - started
            # Synchronous Python tools cannot be safely preempted. Seal their
            # returned output and actual overrun; never call an overrun free.
            if allowance and elapsed>allowance.timeout_s:
                receipt.update(execution_status='failed',error='OPERATION_TIMEOUT_EXCEEDED_AFTER_RETURN')
            return self.store.complete(row, receipt, data, elapsed, result_execution=result_execution)
        except Exception as exc:
            if row:
                if isinstance(exc, TimeoutError) or 'UNCONFIRMED' in str(exc) or 'timeout' in type(exc).__name__.lower():
                    self.store.mark_unknown(self.run_id, request.request_id)
                    return {**self._receipt(request, row, 'unknown', str(exc)), 'charged': json.loads(row['reserved'])}
                elapsed = 0. if definition.capabilities.get('delegated_execution') else time.monotonic() - started
                return self.store.complete(row, self._receipt(request, row, 'failed', str(exc)), elapsed=elapsed)
            with self.store.transaction() as db:
                error_ref = self.store.put(db, self._receipt(request, dict(execution_id='not_executed'), 'rejected', str(exc)))
                self.store.event(db, self.run_id, 'tool', 'rejected', parent=parent, request=request.request_id, caller=self.actor, inputs=[request_ref], outputs=[error_ref], version=request.tool_version)
            # Opt-in role phases charge rejected model calls too. A depleted
            # phase cannot borrow its protected downstream allocation.
            state = self.store.session(self.run_id)['state']
            if self.actor == 'model' and state.get('role_context', {}).get('phase_budget') is not None:
                try:
                    rejected, fresh = self.store.reserve(self.run_id, request.request_id, request_hash,
                        self.actor, {**zero(), 'tool_calls':1}, parent=parent, inputs=[request_ref])
                except ValueError:
                    pass  # Budget rejection itself cannot exceed the ceiling.
                else:
                    if fresh:
                        return self.store.complete(rejected, self._receipt(request, rejected, 'rejected', str(exc)), elapsed=0.)
            # Historical preflight rejections retain their original accounting.
            return self._receipt(request, dict(execution_id='not_executed'), 'rejected', str(exc))

    def _validate_refs(self, value, *, role_archive_read=False):
        if isinstance(value, dict):
            if 'artifact_id' in value:
                # Integrity checking must not decode valid binary evidence as UTF-8.
                reference = EvidenceRef.model_validate(value)
                self.store.artifact(reference,raw=True)
            else:
                for item in value.values():
                    self._validate_refs(item, role_archive_read=role_archive_read)
        elif isinstance(value, list):
            for item in value:
                self._validate_refs(item, role_archive_read=role_archive_read)


    def resume(self):
        compatible = self.compatibility()
        if not compatible['compatible']:
            raise ValueError('DEPENDENCIES_CHANGED: ' + repr(compatible['changed']))
        with self.store.transaction() as db:
            session = self.store.session(self.run_id, db)
            if session['state'].get('route', {}).get('final'):
                raise ValueError('FINISHED_DELIVERY_IS_IMMUTABLE')
            if session['status']=='budget_exhausted':
                raise ValueError('BUDGET_EXHAUSTED: resume cannot replenish authorization')
            if session['state'].get('stop_reason')=='BOUNDED_ARGUMENT_CORRECTION_FAILED':
                raise ValueError('BOUNDED_ARGUMENT_CORRECTION_FAILED: correction opportunity already consumed')
            self.store.update_state(db, self.run_id, session['state'], 'running')
            self.store.event(db, self.run_id, 'session', 'resumed')


    def model_scope(self):
        inp = self.store.session(self.run_id)['snapshot']['input']
        return digest(dict(robot=inp['robot'], backend=inp['policy']['backend']))

    def model_identity(self):
        inp = self.store.session(self.run_id)['snapshot']['input']
        from tools.state_io import digest
        return inp['robot']['structure']['data'].get('model_identity') or digest(inp['robot'])

    def observation(self, receipt):
        if not receipt:
            return None
        from schemas.platform import ToolObservation, ToolReceipt
        if 'request_id' not in receipt:
            return dict(error=receipt.get('error'), execution_status=receipt['execution_status'])
        content = self.store.artifact(receipt['output']) if receipt.get('output') else receipt.get('error')
        size = len(encode(content).encode('utf8'))
        limit = 8192
        observation=ToolObservation(receipt=ToolReceipt.model_validate(receipt),content=content,content_bytes=size,truncated=False)
        if len(encode(observation).encode('utf8')) > limit:
            from tools.platform_tools import evidence_overview
            content=dict(kind='overview',source=receipt.get('output'),pointer='',
                summary='Navigation overview, not original evidence. Read child pointers from this source using evidence.read.',
                entries=evidence_overview(content,'',0,12),bytes=size)
            observation=observation.model_copy(update=dict(content=content,truncated=True))
        result=plain(observation)
        state=self.store.session(self.run_id)['state']
        if state.get('fact_scope') and receipt.get('output'):
            entry=next((r for r in state.get('read_ledger',[]) if r.get('execution_id')==receipt.get('execution_id')),None)
            if entry:
                result['fact_handles']=entry['handles']
                result['catalog_location']='role_context.fact_catalog; exact source mappings retained by host'
        return result

