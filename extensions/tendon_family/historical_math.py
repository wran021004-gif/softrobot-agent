"""Narrow current-session ownership wrapper for frozen historical mathematics."""
from schemas.platform_analysis import HistoricalMathBindingResult
from tools.platform_store import plain


NAMES=('linearization','metrics','endpoint','screen')
KINDS=dict(linearization='candidate_linearization',metrics='control_metrics',
    endpoint='bounded_endpoint',screen='design_screen')


def _reference(entry,name):
    ref=entry.get('reference') if isinstance(entry,dict) and 'reference' in entry else entry
    if not isinstance(ref,dict) or set(ref)!={'artifact_id','media_type'}:
        raise ValueError(f'HISTORICAL_MATH_REFERENCE_INVALID: field=references.{name}; submitted={ref!r}')
    return ref


def bind(ctx,args):
    """Validate imported bytes and bind their original lineage to one exact new build."""
    from .candidate_analysis import scientific_configuration_identity
    from .route import policy,source_node
    spec=policy(ctx.input)
    if spec.historical_math is None or plain(args.import_manifest)!=plain(spec.historical_math):
        raise ValueError('HISTORICAL_MATH_IMPORT_MANIFEST_NOT_FROZEN: field=import_manifest; submitted='+repr(plain(args.import_manifest)))
    manifest=ctx.artifact(args.import_manifest)
    if manifest.get('kind')!='historical_math_import_manifest' or manifest.get('historical_computation') is not True:
        raise ValueError('HISTORICAL_MATH_IMPORT_MANIFEST_INVALID')
    route=ctx.store.session(ctx.run_id)['state']['route']
    node,built=source_node(ctx,args,route)
    if node['action']!='build':
        raise ValueError('PROPOSAL_BOUND_BUILD_REQUIRED: field=source_node; submitted='+repr(args.source_node))
    if not built.get('proposal_provenance'):
        actual=scientific_configuration_identity(ctx.artifact(built['configuration']))
        if actual!=manifest.get('scientific_configuration_identity'):
            raise ValueError('HISTORICAL_MATH_ALTERED_SCIENTIFIC_CONFIGURATION_REJECTED: '
                f'field=source_node; submitted={args.source_node!r}; actual={actual!r}; '
                f'expected={manifest.get("scientific_configuration_identity")!r}')
        raise ValueError('PROPOSAL_BOUND_BUILD_REQUIRED: field=source_node; submitted='+repr(args.source_node))
    provenance=built['proposal_provenance']
    required={
        'optimizer_result':provenance['optimizer_result'],
        'optimizer_candidate_id':provenance['optimizer_candidate_id'],
        'proposal_configuration':provenance['proposal_configuration'],
        'scientific_configuration_identity':provenance['scientific_configuration_identity'],
    }
    for field,expected in required.items():
        if manifest.get(field)!=expected:
            raise ValueError(f'HISTORICAL_MATH_IMPORT_MISMATCH: field={field}; submitted={manifest.get(field)!r}; build_stored_original={expected!r}')
    build_input=ctx.artifact(built['configuration'])
    scientific_id=scientific_configuration_identity(build_input)
    if scientific_id!=provenance['scientific_configuration_identity']:
        raise ValueError('HISTORICAL_MATH_BUILD_SCIENTIFIC_CONFIGURATION_MISMATCH')
    optimizer=ctx.artifact(manifest['optimizer_result'])
    proposal=next((row for row in optimizer.get('proposals',[])
        if row.get('candidate_id')==provenance['optimizer_candidate_id']),None)
    valid=[row.get('candidate_id') for row in optimizer.get('proposals',[]) if row.get('candidate_id')]
    if proposal is None:
        raise ValueError('HISTORICAL_MATH_OPTIMIZER_PROPOSAL_NOT_FOUND: field=optimizer_candidate_id; '
            f'submitted={provenance["optimizer_candidate_id"]!r}; valid_optimizer_candidate_ids={valid!r}')
    if proposal.get('configuration')!=provenance['proposal_configuration']:
        raise ValueError('HISTORICAL_MATH_PROPOSAL_CONFIGURATION_MISMATCH')
    original=ctx.artifact(provenance['proposal_configuration'])
    if scientific_configuration_identity(original)!=scientific_id:
        raise ValueError('HISTORICAL_MATH_ALTERED_SCIENTIFIC_CONFIGURATION_REJECTED')
    supplied=manifest.get('references') or {}
    if set(NAMES)-set(supplied):
        raise ValueError('HISTORICAL_MATH_ESSENTIAL_EVIDENCE_MISSING: '+repr(sorted(set(NAMES)-set(supplied))))
    refs={name:_reference(supplied[name],name) for name in NAMES}
    artifacts={name:ctx.artifact(ref) for name,ref in refs.items()}
    for name,result in artifacts.items():
        if result.get('kind')!=KINDS[name] or not result.get('bindings'):
            raise ValueError(f'HISTORICAL_MATH_ARTIFACT_KIND_OR_BINDING_MISMATCH: field=references.{name}; submitted={refs[name]!r}')
        identities={binding.get('scientific_configuration_identity') for binding in result['bindings']}
        if identities!={scientific_id}:
            raise ValueError(f'HISTORICAL_MATH_ARTIFACT_SCIENTIFIC_CONFIGURATION_MISMATCH: field=references.{name}; submitted={sorted(str(v) for v in identities)!r}')
    if artifacts['screen'].get('evidence')!=[refs['linearization'],refs['metrics'],refs['endpoint']]:
        raise ValueError('HISTORICAL_MATH_SCREEN_EVIDENCE_CHAIN_MISMATCH')
    if artifacts['screen'].get('protocol')!=plain(spec.analysis_protocol) or artifacts['endpoint'].get('protocol')!=plain(spec.analysis_protocol):
        raise ValueError('HISTORICAL_MATH_PROTOCOL_MISMATCH')
    if plain(spec.endpoint_target) not in artifacts['endpoint'].get('evidence',[]):
        raise ValueError('HISTORICAL_MATH_ENDPOINT_TARGET_MISMATCH')
    references={}
    for name in NAMES:
        declared=supplied[name] if isinstance(supplied[name],dict) else {}
        binding=artifacts[name]['bindings'][0]
        references[name]=dict(reference=refs[name],kind=KINDS[name],
            tool_id=declared.get('tool_id'),tool_version=declared.get('tool_version'),
            source_binding={key:binding.get(key) for key in ('candidate_id','source_node','owner_run_id',
                'configuration','scientific_configuration_identity')},historical_computation=True)
    lineage=dict(import_manifest=plain(args.import_manifest),source_stage=manifest.get('source_stage'),
        source_run_id=manifest.get('source_run_id'),source_store=manifest.get('source_store'),
        source_implementation_commit=manifest.get('source_implementation_commit'),
        import_created_by=manifest.get('import_created_by'),applicability=manifest.get('applicability'),
        original_protocol=manifest.get('protocol'),original_target=manifest.get('target'),
        original_optimizer_tool=dict(id='design.optimize_math',version=manifest.get('optimizer_tool_version')),
        historical_computation=True)
    return HistoricalMathBindingResult(build_candidate_id=built['candidate_id'],
        optimizer_candidate_id=provenance['optimizer_candidate_id'],source_build_node=args.source_node,
        optimizer_result=provenance['optimizer_result'],proposal_configuration=provenance['proposal_configuration'],
        scientific_configuration_identity=scientific_id,references=references,lineage=lineage,
        usage=dict(new_mathematical_evaluations=0,historical_mathematical_evaluations=manifest.get('historical_mathematical_evaluations'),
            backend_executions=0,nmpc_solves=0,workers=0))
