"""Registered platform operations. Permissions/accounting belong to Host."""
import math
from schemas.platform import SessionInput, BackendResult, Payload, EvaluationResult, MemoryEntry
from tools.platform_store import plain, zero
from tools.state_io import digest
from schemas import platform_operations as c


def simulation_preflight(inp, arguments, reg):
    candidate = _candidate(inp, arguments.changes, reg)
    backend, parameters = reg.bind(candidate.policy.backend, 'backend')
    _, control = reg.bind(candidate.policy.controller, 'controller')
    backend.resolve().check(candidate, parameters, control)
    from schemas.platform import CandidateInput
    prepared = CandidateInput(candidate_id=arguments.candidate_id, baseline_identity=digest(plain(inp)),
        builder=inp.policy.candidate_builder.extension_id, builder_version=inp.policy.candidate_builder.version,
        changes=arguments.changes, allowed=inp.policy.editable, effective=candidate, content_identity=digest(plain(candidate)),
        sources=dict(entity_design='effective.robot.structure',model_discretization='effective.policy.discretization',
            task_environment='effective.task',run_plan='effective.policy'))
    return dict(cost={'backend_solves': int(not backend.capabilities.get('reference', False))},
                resources=list(backend.resources), prepared=prepared)


def _candidate(inp, changes, reg):
    builder, parameters = reg.bind(inp.policy.candidate_builder, 'candidate_builder')
    authorize = builder.hook('authorize_changes')
    if authorize:
        authorize(inp, parameters, changes)
    for key, value in changes.items():
        if authorize:
            continue
        if key not in inp.policy.editable:
            raise ValueError('PARAMETER_NOT_AUTHORIZED: ' + key)
        lo, hi = inp.policy.editable[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('PARAMETER_OUT_OF_BOUNDS: ' + key)
    candidate = SessionInput.model_validate(builder.resolve()(inp.model_copy(deep=True), parameters, changes))
    # Builder may alter physical design, declared discretization and controller/
    # model parameter payloads. Extension identities and the task stay fixed.
    before, after = plain(inp), plain(candidate)
    for data in (before, after):
        data['robot']['structure']['data'] = {}
        data['policy']['discretization'] = None
        data['policy']['controller']['parameters']['data'] = {}
        if data['policy']['dynamics_model'] is not None:
            data['policy']['dynamics_model']['parameters']['data'] = {}
    if before != after:
        raise ValueError('CANDIDATE_CHANGED_FROZEN_TASK_OR_POLICY')
    reg.parse(candidate.robot.structure)
    if candidate.policy.discretization is not None:
        reg.parse(candidate.policy.discretization)
    reg.bind(candidate.policy.controller, 'controller')
    if candidate.policy.dynamics_model is not None:
        reg.bind(candidate.policy.dynamics_model, 'dynamics_model')
    return candidate


def simulation_reuse(host, args, prepared, cached):
    """Read-only eligibility check; Host seals returned provenance with the receipt."""
    session = host.store.session(host.run_id)
    metadata = session['state'].get('result_executions', {}).get(cached['execution_id'])
    if (not metadata or cached.get('solver_status') != 'completed'
            or metadata.get('original_execution_id') != cached['execution_id']
            or cached.get('original_execution_id') != cached['execution_id']
            or metadata.get('artifact_id') != cached['output']['artifact_id']
            or metadata.get('instance') != session['snapshot']['instance_identity']
            or metadata.get('candidate') != args.candidate_id
            or not metadata.get('candidate_input')):
        return None
    if host.store.artifact(metadata['candidate_input']) != plain(prepared):
        return None
    return dict(metadata)


def simulate(ctx, args):
    inp = ctx.prepared.effective
    with ctx.store.transaction() as db:
        candidate_ref = ctx.store.put(db, ctx.prepared)
        ctx.store.event(db, ctx.run_id, 'candidate', 'frozen', request=ctx.row['request_id'], execution=ctx.row['execution_id'],
            parent=ctx.row['parent_id'], outputs=[candidate_ref], candidate=args.candidate_id, version=ctx.prepared.builder_version)
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
                request=ctx.row['request_id'], execution=ctx.row['execution_id'], outputs=refs, candidate=args.candidate_id, version=backend_def.version)
            ctx.result_execution = dict(artifact_id=ref.artifact_id, instance=ctx.snapshot['instance_identity'],
                backend=inp.policy.backend.extension_id, task=inp.task.model_dump(mode='json'), candidate=args.candidate_id,
                candidate_input=plain(candidate_ref), request_id=ctx.row['request_id'], original_execution_id=ctx.row['execution_id'])
        return result
    finally:
        backend.close()


def evaluate(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    identities = ctx.store.session(ctx.run_id)['state'].get('result_executions', {})
    matches = [(key, m) for key, m in identities.items() if m['artifact_id'] == args.result.artifact_id
               and (args.execution_id is None or key == args.execution_id)]
    if len(matches) != 1:
        raise ValueError('RESULT_EXECUTION_SELECTION_REQUIRED: arguments.execution_id')
    source_execution, metadata = matches[0]
    if metadata['instance'] != ctx.snapshot['instance_identity']:
        raise ValueError('RESULT_INSTANCE_MISMATCH')
    evaluator, parameters = ctx.reg.bind(ctx.input.task.evaluator, 'evaluator')
    identity = digest(dict(instance=ctx.snapshot['instance_identity'], task=ctx.input.task.model_dump(mode='json'),
        evaluator=ctx.input.task.evaluator.model_dump(mode='json'), backend=result.backend_id, model=result.model_id,
        evaluator_dependencies=ctx.snapshot['dependencies'][evaluator.extension_id + '@' + evaluator.version],
        backend_dependencies=ctx.snapshot['dependencies'][ctx.input.policy.backend.extension_id + '@' + ctx.input.policy.backend.version]))
    outcome = evaluator.resolve()(ctx.input.task, result, args.result, ctx.reg, identity)
    outcome = outcome.model_copy(update=dict(source_execution_id=source_execution,
        original_execution_id=metadata.get('original_execution_id'),
        candidate_id=metadata['candidate'], evaluator_version=evaluator.version))
    with ctx.store.transaction() as db:
        ref = ctx.store.put(db, outcome)
        ctx.store.event(db, ctx.run_id, 'evaluation', outcome.validity, parent=ctx.row['parent_id'], request=ctx.row['request_id'],
            execution=ctx.row['execution_id'], inputs=[args.result, metadata['candidate_input']], outputs=[ref], candidate=metadata['candidate'], version=evaluator.version)
    return outcome


def evidence_overview(value, pointer, offset, limit):
    """Pointers always address the original document, including one-key wrappers."""
    keys=list(value) if isinstance(value,dict) else list(range(len(value))) if isinstance(value,list) else []
    entries=[]
    for key in keys[offset:offset+limit]:
        child=value[key]
        entries.append(dict(pointer=pointer+'/'+str(key).replace('~','~0').replace('/','~1'),
            type=type(child).__name__,items=len(child) if isinstance(child,(dict,list,str)) else 1))
    return entries


def read_evidence(ctx, args):
    value = ctx.artifact(args.reference)
    if args.pointer:
        if not args.pointer.startswith('/'):
            raise ValueError('JSON_POINTER_MUST_START_WITH_SLASH')
        try:
            for part in args.pointer[1:].split('/'):
                key = part.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
        except (KeyError, IndexError, TypeError, ValueError):
            hint = '; use pointer="" to read the root object' if args.pointer == '/' else ''
            raise ValueError('EVIDENCE_POINTER_NOT_FOUND: ' + args.pointer + hint) from None
    from tools.platform_store import encode
    presentation='original'
    total=len(value) if isinstance(value,(list,dict,str)) else 1
    count=min(args.limit,max(0,total-args.offset));kind='content'
    while True:
        end=args.offset+count
        if kind=='overview': page=evidence_overview(value,args.pointer,args.offset,count)
        elif isinstance(value,dict): page={k:value[k] for k in list(value)[args.offset:end]}
        elif isinstance(value,(list,str)): page=value[args.offset:end]
        else: page=value
        result=c.EvidencePage(source=args.reference,pointer=args.pointer,content=page,
            next_offset=end if end<total else None,kind=kind,offset=args.offset,total_items=total,returned_items=count,presentation=presentation)
        # Include the EvidencePage envelope and leave room for Host's receipt and
        # ToolObservation envelope.
        measured=plain(result)
        if len(encode(measured['content']).encode('utf8'))<=args.byte_limit and len(encode(measured).encode('utf8'))<=6000:
            break
        if count>1:
            count=max(1,count//2)
        elif kind=='content' and isinstance(value,(dict,list)):
            kind='overview'
        else:
            raise ValueError('EVIDENCE_POINTER_OR_BYTE_LIMIT_TOO_SMALL: increase byte_limit for this pointer; original evidence retained')
    with ctx.store.transaction() as db:
        state = ctx.store.session(ctx.run_id, db)['state']
        state.setdefault('reads', {})[digest(plain(args))] = dict(source=plain(args.reference), pointer=args.pointer, offset=args.offset,
            next_offset=result.next_offset, kind=kind,content_hash=digest(result.content))
        state['reads'] = dict(list(state['reads'].items())[-8:])
        ctx.store.update_state(db, ctx.run_id, state)
    return result


def diagnose(ctx, args):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    matches = [s for s in result.signals if s.spec.name == args.signal]
    if len(matches) > 1:
        raise ValueError('SIGNAL_SELECTION_REQUIRED: bind diagnostics.sample_exceeds@1.1.0 in policy.tool_bindings; pass the original result with entity and phase')
    signal = matches[0] if matches else None
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
