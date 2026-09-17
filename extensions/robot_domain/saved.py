"""One materialization bridge for old diagnosis, rules and saved replay/video."""
from pathlib import Path
from pydantic import ValidationError
from schemas.platform import BackendResult, ExportBundle
from tools.platform_store import plain
from .contracts import SavedProduct


def restore(ctx, args, *, family_replay=False):
    result = BackendResult.model_validate(ctx.artifact(args.result))
    if result.data.contract == 'experiment.backend_data':
        raise ValueError('SAVED_LEGACY_MODEL_UNSUPPORTED: assembled spatial/planar exports use signals.read and diagnostics.sample_exceeds@1.1.0; legacy replay/trajectory schemas are not reused')
    if result.data.contract == 'family.backend_data' and not family_replay:
        raise ValueError('FAMILY_SAVED_OPERATION_UNSUPPORTED: use signals.read, diagnostics.sample_exceeds or visualization.saved_replay')
    records = ctx.store.session(ctx.run_id)['state'].get('result_executions', {})
    matches = [(eid, m) for eid, m in records.items() if m['artifact_id'] == args.result.artifact_id
               and (args.execution_id is None or args.execution_id == eid)]
    if len(matches) != 1:
        raise ValueError('RESULT_EXECUTION_SELECTION_REQUIRED: arguments.execution_id')
    selected, metadata = matches[0]
    original = metadata.get('original_execution_id')
    if not original:
        raise ValueError('ORIGINAL_EXECUTION_NOT_RECORDED')
    bundles = []
    for event in ctx.store.events(ctx.run_id):
        if event['execution_id'] != original or event['kind'] != 'simulation':
            continue
        for ref in event['outputs']:
            if ref['media_type'] != 'application/json':
                continue
            try:
                bundle = ExportBundle.model_validate(ctx.artifact(ref))
            except ValidationError:
                continue
            if bundle.result == args.result and bundle.source == result.backend_id:
                bundles.append((ref, bundle))
    if len(bundles) != 1:
        raise ValueError('RESULT_EXPORT_BUNDLE_REQUIRED')
    bundle_ref, bundle = bundles[0]
    root = ctx.folder / 'saved'
    root.mkdir()
    registry = {}
    for file in bundle.files:
        # ExportBundle from simulation contains flat backend exports only.
        if Path(file.filename).name != file.filename or file.filename in ('.', '..') or ':' in file.filename:
            raise ValueError('INVALID_EXPORT_FILENAME')
        (root / file.filename).write_bytes(ctx.store.artifact(file.reference, raw=True))
        registry[file.filename] = dict(sha256=file.reference.artifact_id)
    return dict(root=root, registry=registry, bundle=bundle_ref, selected=selected,
                original=original, metadata=metadata, backend=result.data.data.get('backend', result.backend_id))


def seal(ctx, args, source, report):
    from tools.artifact_tools import file_hash
    files = {}
    with ctx.store.transaction() as db:
        # Include restored inputs and products; content addressing shares original bytes.
        for name, record in source['registry'].items():
            path = (source['root'] / record.get('path', name)).resolve()
            if not path.is_relative_to(source['root']) or file_hash(path) != record['sha256']:
                raise ValueError('SAVED_PRODUCT_CHANGED')
            files[name] = ctx.store.put(db, path.read_bytes(), 'application/octet-stream')
        report_ref = ctx.store.put(db, report)
        product = SavedProduct(source=args.result, source_execution_id=source['selected'],
            original_execution_id=source['original'], candidate_id=source['metadata']['candidate'],
            bundle=source['bundle'], report=report_ref, files=files)
        ref = ctx.store.put(db, product)
        ctx.store.event(db, ctx.run_id, 'saved_data', 'derived', request=ctx.row['request_id'],
            execution=ctx.row['execution_id'], parent=ctx.row['parent_id'],
            inputs=[args.result, source['bundle'], source['metadata']['candidate_input']],
            outputs=[ref], candidate=product.candidate_id, version=ctx.request.tool_version)
    return product


def diagnosis(ctx, args):
    from schemas.public_tools import SavedDiagnosis
    from tools.public_services import saved_diagnosis
    source = restore(ctx, args, family_replay=True)
    if source['backend'] in ('backend.matlab_spatial','backend.family_mujoco'):
        from extensions.tendon_family.diagnostics import diagnose
        return seal(ctx,args,source,diagnose(ctx,args,source))
    options = args.model_dump(exclude={'result', 'execution_id'})
    options = plain(SavedDiagnosis(result_ref='result.json', backend=source['backend'], **options))
    report = saved_diagnosis(source['root'], source['registry'], options,
        source_identity=dict(candidate_id=source['metadata']['candidate'], run_id=ctx.run_id))
    return seal(ctx, args, source, report)


def rule(ctx, args):
    from schemas.framework import RuleQuery
    from tools.diagnostic_rules import run_saved_rule
    source = restore(ctx, args)
    options = plain(RuleQuery(result_ref='result.json', backend=source['backend'],
        **args.model_dump(exclude={'result', 'execution_id'})))
    return seal(ctx, args, source, run_saved_rule(source['root'], source['registry'], options))


def replay(ctx, args):
    from tools.observation_tools import load_observation
    source = restore(ctx, args, family_replay=True)
    if source['backend'] in ('backend.matlab_spatial', 'backend.family_mujoco'):
        import gzip
        import json
        from tools.state_io import atomic_json
        from tools.artifact_tools import file_hash
        rows = json.loads(gzip.decompress((source['root'] / 'trajectory.json.gz').read_bytes()))
        path = source['root'] / 'replay_trajectory.json'
        atomic_json(path, rows)
        source['registry'][path.name] = dict(sha256=file_hash(path))
        return seal(ctx, args, source, dict(model=source['backend'], samples=len(rows),
            candidate_id=source['metadata']['candidate'], new_solves=0,
            viewer='extensions.tendon_family.saved:view', states='replay_trajectory.json',
            geometry='resolved_physics.json', collision='See saved applicability; section visualization is not exact contact'))
    observation = load_observation(source['root'])
    observation['candidate_id'] = source['metadata']['candidate']
    # Both native replay/renderer entries consume this same existing observation format.
    # This operation only prepares saved observations; it opens no window/engine.
    return seal(ctx, args, source, observation)


def video(ctx, args):
    from tools.tool_registry import service_tools
    from tools.service_execution import execute
    source = restore(ctx, args, family_replay=True)
    backend={'backend.matlab_spatial':'matlab','backend.family_mujoco':'mujoco'}.get(source['backend'],source['backend'])
    definition = service_tools()['visualization.render_simulation_video']
    options = plain(definition.schema.model_validate(dict(result_ref='result.json', backend=backend,
        **args.model_dump(exclude={'result', 'execution_id'}))))
    report = execute(definition, source['root'], source['registry'], options, ctx.folder)
    return seal(ctx, args, source, report)
