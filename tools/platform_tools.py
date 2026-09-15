"""Registered platform operations. Permissions/accounting belong to Host."""
import math
from schemas.platform import SessionInput, BackendResult, Payload, EvaluationResult, MemoryEntry
from tools.platform_store import plain, zero
from tools.state_io import digest
from extensions.reference import contracts as c


def simulation_preflight(inp, arguments, reg):
    backend, parameters = reg.bind(inp.policy.backend, 'backend')
    controller, control = reg.bind(inp.policy.controller, 'controller')
    _candidate(inp, arguments.changes, reg)
    backend.resolve().check(inp, parameters, control)
    # Reference steps are counted separately as synthetic computations, not backend solves.
    return dict(cost={'backend_solves': int(not backend.capabilities.get('reference', False))}, resources=list(backend.resources))


def _candidate(inp, changes, reg):
    data = inp.model_dump(mode='json')
    for key, value in changes.items():
        if key not in inp.policy.editable:
            raise ValueError('PARAMETER_NOT_AUTHORIZED: ' + key)
        lo, hi = inp.policy.editable[key]
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('PARAMETER_OUT_OF_BOUNDS: ' + key)
        group, name = key.split('.', 1)
        if group != 'controller':
            raise ValueError('PARAMETER_ADAPTER_REQUIRED')
        data['policy']['controller']['parameters']['data'][name] = value
    candidate = SessionInput.model_validate(data)
    reg.bind(candidate.policy.controller, 'controller')
    return candidate


def simulate(ctx, args):
    inp = _candidate(ctx.input, args.changes, ctx.reg)
    backend_def, _ = ctx.reg.bind(inp.policy.backend, 'backend')
    controller_def, parameters = ctx.reg.bind(inp.policy.controller, 'controller')
    backend = backend_def.resolve()()
    controller = controller_def.resolve()(parameters, inp.task.timing.control_period_s)
    ctx.record('simulation', 'started', candidate=args.candidate_id)
    try:
        backend.compile(inp, ctx.reg)
        backend.initialize(Payload.model_validate(ctx.snapshot['initial']), controller)
        result = backend.run(folder=ctx.folder / 'backend', timeout_s=inp.policy.timeout_s)
        ctx.reg.parse(result.data)
        ctx.reg.parse(result.initial_state)
        with ctx.store.transaction() as db:
            ref = ctx.store.put(db, result)
            # Raw exports are immutable blobs with causal links; working folder is disposable.
            refs = [ref]
            files = []
            for path in sorted((ctx.folder / 'backend').glob('*')):
                if path.is_file():
                    saved = ctx.store.put(db, path.read_bytes(), 'application/octet-stream')
                    refs.append(saved)
                    files.append(dict(filename=path.name, reference=plain(saved)))
            if files:
                from schemas.platform import ExportBundle
                refs.append(ctx.store.put(db, ExportBundle(result=ref, files=files, source=backend_def.extension_id)))
            ctx.store.event(db, ctx.run_id, 'simulation', result.solver_status, parent=ctx.row['parent_id'],
                request=ctx.row['request_id'], execution=ctx.row['execution_id'], outputs=refs, candidate=args.candidate_id)
            state = ctx.store.session(ctx.run_id, db)['state']
            state.setdefault('result_identities', {})[ref.artifact_id] = dict(instance=ctx.snapshot['instance_identity'],
                backend=inp.policy.backend.extension_id, task=inp.task.model_dump(mode='json'), candidate=args.candidate_id)
            ctx.store.update_state(db, ctx.run_id, state)
        return result
    finally:
        backend.close()


def evaluate(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    identities = ctx.store.session(ctx.run_id)['state'].get('result_identities', {})
    metadata = identities.get(args.result.artifact_id)
    if not metadata or metadata['instance'] != ctx.snapshot['instance_identity']:
        raise ValueError('RESULT_INSTANCE_MISMATCH')
    evaluator, parameters = ctx.reg.bind(ctx.input.task.evaluator, 'evaluator')
    identity = digest(dict(instance=ctx.snapshot['instance_identity'], task=ctx.input.task.model_dump(mode='json'),
        evaluator=ctx.input.task.evaluator.model_dump(mode='json'), backend=result.backend_id, model=result.model_id,
        evaluator_dependencies=ctx.snapshot['dependencies'][evaluator.extension_id + '@' + evaluator.version],
        backend_dependencies=ctx.snapshot['dependencies'][ctx.input.policy.backend.extension_id + '@' + ctx.input.policy.backend.version]))
    outcome = evaluator.resolve()(ctx.input.task, result, args.result, ctx.reg, identity)
    with ctx.store.transaction() as db:
        ref = ctx.store.put(db, outcome)
        ctx.store.event(db, ctx.run_id, 'evaluation', outcome.validity, parent=ctx.row['parent_id'], request=ctx.row['request_id'],
            execution=ctx.row['execution_id'], inputs=[args.result], outputs=[ref], candidate=metadata['candidate'])
    return outcome


def read_evidence(ctx, args):
    value = ctx.artifact(args.reference)
    if args.pointer:
        if not args.pointer.startswith('/'):
            raise ValueError('JSON_POINTER_MUST_START_WITH_SLASH')
        for part in args.pointer[1:].split('/'):
            key = part.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
    end = args.offset + args.limit
    if isinstance(value, list):
        page, next_offset = value[args.offset:end], end if end < len(value) else None
    elif isinstance(value, dict):
        keys = list(value)
        page, next_offset = {k: value[k] for k in keys[args.offset:end]}, end if end < len(keys) else None
    else:
        page, next_offset = value, None
    result = c.EvidencePage(source=args.reference, pointer=args.pointer, content=page, next_offset=next_offset)
    with ctx.store.transaction() as db:
        state = ctx.store.session(ctx.run_id, db)['state']
        state.setdefault('reads', {})[digest(plain(args))] = dict(source=plain(args.reference), pointer=args.pointer, offset=args.offset,
            next_offset=next_offset, content_hash=digest(page))
        ctx.store.update_state(db, ctx.run_id, state)
    return result


def diagnose(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    signal = next((s for s in result.signals if s.spec.name == args.signal), None)
    if signal is None:
        status, indices = 'missing_data', []
    elif signal.spec.units != args.units or signal.spec.dimension != 1:
        status, indices = 'not_applicable', []
    else:
        indices = [i for i, row in enumerate(signal.values) if row[0] > args.threshold]
        status = 'events_found' if indices else 'no_event'
    output = c.DiagnosticResult(status=status, source=args.result, signal=args.signal, sample_indices=indices,
                               observed=[signal.values[i] for i in indices] if signal else [])
    ctx.record('diagnosis', status, inputs=[args.result])
    return output


def memory_search(ctx, args):
    return c.MemoryResults(entries=ctx.store.memories(plain(args)))


def memory_save(ctx, args):
    entry = args.entry
    if ctx.host.actor == 'model' and entry.kind not in ('model_note', 'hypothesis'):
        raise ValueError('MODEL_MEMORY_MUST_REMAIN_NOTE_OR_HYPOTHESIS')
    # A model cannot turn prose into a verified scientific conclusion.
    if entry.kind == 'verified_record':
        for ref in entry.sources:
            EvaluationResult.model_validate(ctx.artifact(ref))
        if ctx.host.actor != 'local-human':
            raise ValueError('VERIFIED_RECORD_REQUIRES_TRUSTED_HOST_CHECK')
    if entry.task_family != ctx.input.task.family or entry.task_version != ctx.input.task.task_version:
        raise ValueError('MEMORY_APPLICABILITY_MISMATCH')
    return c.SavedMemory(entry=ctx.store.save_memory(ctx.run_id, entry))


def stop(ctx, args):
    with ctx.store.transaction() as db:
        state = ctx.store.session(ctx.run_id, db)['state']
        state['stop_reason'] = args.reason
        ctx.store.update_state(db, ctx.run_id, state, args.status)
    return c.Stopped(status=args.status, reason=args.reason)


def skills_search(ctx, args):
    from tools.platform_skills import applicable
    return c.SkillRecords(skills=applicable(ctx.host, args.reference))


def skills_propose(ctx, args):
    from tools.platform_skills import library
    skill = library(ctx.host).propose(args.skill)
    return c.SkillRecords(skills=[skill.model_dump(mode='json')])


def skills_validate(ctx, args):
    from tools.platform_skills import library
    record = args.record
    if ctx.host.actor != 'local-human':
        raise ValueError('SKILL_VALIDATION_REQUIRES_TRUSTED_HOST_EVIDENCE_CHECK')
    if record.validated_by != 'harness':
        raise ValueError('HOST_VALIDATOR_IDENTITY_REQUIRED')
    skill = library(ctx.host).record_validation(args.reference, record)
    return c.SkillRecords(skills=[skill.model_dump(mode='json')])


def worker_submit(ctx, args):
    from tools.platform_workers import Coordinator
    return Coordinator(ctx.host).submit(args.order, parent=ctx.row['parent_id'])


def worker_status(ctx, args):
    from tools.platform_workers import Coordinator
    return Coordinator(ctx.host).status(args.work_id)


def worker_cancel(ctx, args):
    from tools.platform_workers import Coordinator
    return Coordinator(ctx.host).cancel(args.work_id)


def worker_accept(ctx, args):
    from tools.platform_workers import Coordinator
    return Coordinator(ctx.host).accept(args.work_id)
