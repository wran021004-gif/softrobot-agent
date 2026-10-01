"""Explicit owned build binding for pre-execution GVS mathematics."""
import json
from types import SimpleNamespace
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef,SessionInput
from schemas.platform_analysis import CandidateAnalysisBundle, CandidateAnalysisComponent, TaskAnalysisProtocol
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import GVSDynamicsRequestV2


class CandidateDynamicsRequest(GVSDynamicsRequestV2):
    source_node: str = Field(description='Completed build node in this Route session. Analysis uses its immutable effective configuration, never the selected incumbent or parent robot. Basis comes from the frozen controller.')


class CandidateAnalysisResult(Contract):
    binding: dict
    calculation: dict
    physical_summary: dict


def scientific_configuration(inp):
    """Identity of every setting that can change the declared scientific case.

    Deliberately excludes run/candidate labels, provider transport, accounting and
    tool grants.  Those are bookkeeping, whereas the complete robot, task and
    bound model/controller/build policy below determine the calculation.
    """
    inp=SessionInput.model_validate(inp)
    return dict(robot=plain(inp.robot),task=plain(inp.task),seed=inp.seed,policy={key:plain(getattr(inp.policy,key))
        for key in ('dynamics_model','backend','controller','discretization','candidate_builder','editable')})


def scientific_configuration_identity(inp):
    return digest(scientific_configuration(inp))


def configuration_binding(inp, configuration, candidate_id, owner_run_id, source_node):
    inp=SessionInput.model_validate(inp)
    basis=inp.policy.controller.parameters.data['recipe']['basis']
    from .gvs_basis import resolve_basis
    resolved=resolve_basis(inp.robot.structure.data,basis)
    tendons=inp.robot.structure.data['tendons']; control=inp.policy.controller.parameters.data
    return dict(source_node=source_node,candidate_id=candidate_id,configuration=plain(configuration),
        owner_run_id=owner_run_id,effective_configuration_identity=digest(plain(inp)),
        scientific_configuration_identity=scientific_configuration_identity(inp),robot_identity=digest(plain(inp.robot)),
        task_identity=digest(plain(inp.task)),physical_context=plain(inp.task.environment),
        model='model.gvs@1.0.0',basis=plain(resolved),coordinate_order=list(resolved.coordinate_order),
        calculation_frame='robot_base',endpoint_frame='world',target_m=inp.task.goal.data['target_m'],
        task_duration_s=inp.task.timing.duration_s,control_period_s=inp.task.timing.control_period_s,
        physics_timestep_s=inp.task.timing.timestep_s,initializer=plain(inp.task.initializer),
        controller=plain(inp.policy.controller),controller_numerical_source=control.get('numerical_source'),
        tendon_order=[row['id'] for row in tendons],tension_bounds_n=[[0.,row['force_limit_n']] for row in tendons],
        declared_pretension_n=[row['pretension_n'] for row in tendons],
        endpoint_requirements=dict(official_reach=plain(inp.task.evaluator),
            terminal_braking_diagnostic=control.get('settling')),
        analysis_protocol='supplied_by_analysis_call',execution_data_used=False)


def resolve_candidate(ctx, source_node):
    state=ctx.store.session(ctx.run_id)['state']
    node=next((n for n in state.get('route',{}).get('nodes',[]) if n['node_id']==source_node
        and n['action']=='build' and n['status']=='completed'),None)
    if node is None:
        raise ValueError('OWNED_COMPLETED_BUILD_REQUIRED')
    built=ctx.artifact(node['result'])
    inp=SessionInput.model_validate(ctx.artifact(built['configuration']))
    if plain(inp.task)!=plain(ctx.input.task):
        raise ValueError('CANDIDATE_ANALYSIS_FROZEN_TASK_MISMATCH')
    binding=configuration_binding(inp,built['configuration'],built['candidate_id'],ctx.run_id,source_node)
    if built.get('proposal_provenance'):
        binding['proposal_provenance']=built['proposal_provenance']
    return inp,binding


_COMPONENTS={
    'linearization':('candidate_linearization','analysis.linearize_candidate','1.0.0'),
    'metrics':('control_metrics','analysis.control_metrics','2.0.0'),
    'endpoint':('bounded_endpoint','analysis.bounded_endpoint','1.0.0'),
    'screen':('design_screen','design.screen','1.0.0'),
}


def _build(ctx,source_node):
    route=ctx.store.session(ctx.run_id)['state'].get('route',{})
    node=next((row for row in route.get('nodes',[]) if row.get('node_id')==source_node
        and row.get('action')=='build' and row.get('status')=='completed' and row.get('result')),None)
    if node is None: raise ValueError('OWNED_COMPLETED_BUILD_REQUIRED')
    return node,ctx.artifact(node['result'])


def candidate_analysis_scope(ctx,source_node):
    """Resolve the one frozen scope shared by preparation, overview and registration."""
    from .route import policy
    inp,binding=resolve_candidate(ctx,source_node);spec=policy(ctx.input)
    if not spec.analysis_protocol or not spec.endpoint_target:
        raise ValueError('ROUTE_ANALYSIS_NOT_CONFIGURED')
    protocol=TaskAnalysisProtocol.model_validate(ctx.artifact(spec.analysis_protocol))
    versions={name:ctx.input.policy.tool_bindings.get(tool,default)
        for name,(_,tool,default) in _COMPONENTS.items()}
    dependencies={}
    for name,(_,tool,_) in _COMPONENTS.items():
        key=tool+'@'+versions[name];value=ctx.snapshot.get('dependencies',{}).get(key)
        dependencies[key]=None if value is None else digest(value)
    scope=dict(source_node=source_node,candidate_id=binding['candidate_id'],configuration=binding['configuration'],
        scientific_configuration_identity=binding['scientific_configuration_identity'],
        protocol=plain(spec.analysis_protocol),protocol_identity=digest(plain(protocol)),target=plain(spec.endpoint_target),
        model=binding['model'],basis=binding['basis'],coordinate_order=binding['coordinate_order'],
        dependency_identities=dependencies)
    return inp,binding,plain(spec.analysis_protocol),plain(spec.endpoint_target),versions,dependencies,digest(scope)


def _same_binding(value,binding):
    required=('source_node','candidate_id','configuration','scientific_configuration_identity')
    bindings=value.get('bindings') or []
    return bool(bindings) and all(all(row.get(key)==binding.get(key) for key in required) for row in bindings)


def _valid_component(value,name,binding,protocol,target):
    if not isinstance(value,dict) or value.get('kind')!=_COMPONENTS[name][0]: return False
    if value.get('protocol')!=protocol or not _same_binding(value,binding): return False
    if name=='endpoint' and target not in value.get('evidence',[]): return False
    return True


def _analysis_inventory(ctx):
    """References reachable from committed receipts, component events and Route reports."""
    entries=[];seen=set();bundles=[]
    def add(ref,origin):
        ref=plain(ref);key=ref.get('artifact_id') if isinstance(ref,dict) else None
        if not key or key in seen:return
        try:value=ctx.artifact(ref)
        except (ValueError,TypeError):return
        seen.add(key)
        if value.get('kind')=='candidate_analysis_bundle':
            bundles.append((ref,value,origin))
            for component in value.get('components',{}).values():
                if component.get('reference'):add(component['reference'],'bundle')
        elif value.get('kind') in {row[0] for row in _COMPONENTS.values()}:
            entries.append((ref,value,origin))
    with ctx.store.connect(True) as db:
        for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
            receipt=json.loads(row['receipt'])
            if receipt.get('execution_status')=='completed' and receipt.get('output'):
                add(receipt['output'],'completed_tool_result')
    for event in ctx.store.events(ctx.run_id):
        if event.get('kind')=='candidate_analysis_component':
            for ref in event.get('outputs',[]):add(ref,'component_event')
    route=ctx.store.session(ctx.run_id)['state'].get('route',{})
    for node in route.get('nodes',[]):
        if node.get('action')!='analyze' or node.get('status')!='completed' or not node.get('result'):continue
        try:report=ctx.artifact(node['result'])
        except ValueError:continue
        for name in _COMPONENTS:
            if report.get(name):add(report[name],'registered_report')
    return entries,bundles


def _matching_chain(ctx,binding,protocol,target):
    entries,bundles=_analysis_inventory(ctx)
    grouped={name:[] for name in _COMPONENTS}
    for ref,value,origin in entries:
        for name in _COMPONENTS:
            if _valid_component(value,name,binding,protocol,target):grouped[name].append((ref,value,origin))
    best=None
    for linear in reversed(grouped['linearization']):
        lref=linear[0]
        metrics=[row for row in grouped['metrics'] if lref in row[1].get('evidence',[])]
        endpoints=[row for row in grouped['endpoint'] if lref in row[1].get('evidence',[])]
        metric=metrics[-1] if metrics else None;endpoint=endpoints[-1] if endpoints else None;screen=None
        if metric and endpoint:
            screen=next((row for row in reversed(grouped['screen'])
                if row[1].get('evidence')==[lref,metric[0],endpoint[0]]),None)
        chain=dict(linearization=linear,metrics=metric,endpoint=endpoint,screen=screen)
        score=sum(value is not None for value in chain.values())
        if best is None or score>best[0]:best=(score,chain)
        if score==4:break
    chain=best[1] if best else {name:None for name in _COMPONENTS}
    matching_bundles=[row for row in bundles if row[1].get('source_node')==binding['source_node']
        and row[1].get('build_candidate_id')==binding['candidate_id']
        and row[1].get('configuration')==binding['configuration']
        and row[1].get('protocol')==protocol and row[1].get('target')==target]
    return chain,grouped,matching_bundles


class _ComponentContext:
    def __init__(self,ctx,version):self._ctx=ctx;self.request=SimpleNamespace(tool_version=version)
    def __getattr__(self,name):return getattr(self._ctx,name)


def prepare_candidate(ctx,args):
    """Compose the established four calculations under one receipt and exact scope."""
    from .math_analysis import linearize_candidate
    from extensions.math_analysis.tools import control_metrics,bounded_endpoint_analysis,design_screen
    inp,binding,protocol,target,versions,dependencies,scope_identity=candidate_analysis_scope(ctx,args.source_node)
    protocol_ref=EvidenceRef.model_validate(protocol);target_ref=EvidenceRef.model_validate(target)
    node,built=_build(ctx,args.source_node)
    chain,_,_=_matching_chain(ctx,binding,protocol,target)
    components={};values={}

    def reuse(name):
        row=chain.get(name)
        if row is None:return None
        components[name]=CandidateAnalysisComponent(tool_id=_COMPONENTS[name][1],tool_version=versions[name],
            status='reused',reference=row[0],detail='Exact candidate, protocol, target and upstream evidence chain match.').model_dump(mode='json')
        values[name]=row[1]
        return row[0]

    def compute(name,operation):
        try:
            value=operation();ref=plain(ctx.save_artifact(value,'candidate_analysis_component'))
            components[name]=CandidateAnalysisComponent(tool_id=_COMPONENTS[name][1],tool_version=versions[name],
                status='computed',reference=ref).model_dump(mode='json');values[name]=plain(value);return ref
        except Exception as exc:
            failure=plain(ctx.save_artifact(dict(kind='candidate_analysis_component_failure',component=name,
                source_node=args.source_node,analysis_scope_identity=scope_identity,error=str(exc)),
                'candidate_analysis_component_failure'))
            ctx.record('candidate_analysis_component','failed',inputs=[built['configuration'],protocol,target],
                outputs=[failure],candidate=binding['candidate_id'])
            components[name]=CandidateAnalysisComponent(tool_id=_COMPONENTS[name][1],tool_version=versions[name],
                status='failed',failure=failure,detail=str(exc)).model_dump(mode='json')
            return None

    linear=reuse('linearization')
    if linear is None:
        linear=compute('linearization',lambda:linearize_candidate(ctx,SimpleNamespace(source_node=args.source_node,protocol=protocol_ref)))
    if linear is not None:
        metrics=reuse('metrics')
        if metrics is None:
            metrics=compute('metrics',lambda:control_metrics(_ComponentContext(ctx,versions['metrics']),
                SimpleNamespace(models=[EvidenceRef.model_validate(linear)],protocol=protocol_ref,implementation='scipy')))
        endpoint=reuse('endpoint')
        if endpoint is None:
            endpoint=compute('endpoint',lambda:bounded_endpoint_analysis(ctx,
                SimpleNamespace(models=[EvidenceRef.model_validate(linear)],protocol=protocol_ref,target=target_ref)))
    else:metrics=endpoint=None
    if linear is not None and metrics is not None and endpoint is not None:
        screen=reuse('screen')
        if screen is None:
            screen=compute('screen',lambda:design_screen(ctx,SimpleNamespace(source_node=args.source_node,
                protocol=protocol_ref,linearization=EvidenceRef.model_validate(linear),
                metrics=EvidenceRef.model_validate(metrics),endpoint=EvidenceRef.model_validate(endpoint))))
    else:screen=None
    for name in _COMPONENTS:
        if name not in components:
            components[name]=CandidateAnalysisComponent(tool_id=_COMPONENTS[name][1],tool_version=versions[name],
                status='not_performed',detail='Blocked by an earlier missing or failed component.').model_dump(mode='json')
    refs=[components[name].get('reference') for name in _COMPONENTS if components[name].get('reference')]
    complete=all(components[name]['reference'] is not None for name in _COMPONENTS)
    findings={}
    if complete:
        report=values['screen']['records'][0]
        findings=dict(priority_reasoning=report.get('priority_reasoning'),
            operating_point_availability=report.get('operating_point_availability'),
            reachability_evidence=report.get('reachability_evidence'),hard_rejection=report.get('hard_rejection'))
    model=dict(extension_id=binding['model'].split('@')[0],version=binding['model'].split('@')[1],
        basis=binding['basis'],coordinate_order=binding['coordinate_order'])
    return CandidateAnalysisBundle(source_node=args.source_node,build_candidate_id=binding['candidate_id'],
        build_result=node['result'],configuration=built['configuration'],
        scientific_configuration_identity=binding['scientific_configuration_identity'],
        analysis_scope_identity=scope_identity,protocol=protocol,target=target,binding=binding,model=model,
        dependency_identities=dependencies,components=components,
        evidence=[built['configuration'],protocol,target,*refs],advisory_findings=findings,
        limitations=['Configuration-only local analysis; no backend trajectory or evaluator result is used.',
            'A local bounded witness or screen cannot certify nonlinear reach, settling, real-time feasibility or global optimality.'],
        proposal_provenance=built.get('proposal_provenance'),complete=complete)


def _failed_prepare_attempts(ctx,source_node):
    failures=[]
    events=ctx.store.events(ctx.run_id)
    request_refs={event.get('request'):event.get('inputs',[None])[0] for event in events
        if event.get('kind')=='tool' and event.get('status')=='reserved' and event.get('inputs')}
    with ctx.store.connect(True) as db:
        for row in db.execute('SELECT request_id,receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
            receipt=json.loads(row['receipt'])
            if receipt.get('tool_id')!='analysis.prepare_candidate' or receipt.get('execution_status')=='completed':continue
            ref=request_refs.get(row['request_id'])
            try:request=ctx.artifact(ref) if ref else {}
            except ValueError:request={}
            if request.get('arguments',{}).get('source_node')==source_node:
                failures.append(dict(request_id=row['request_id'],status=receipt.get('execution_status'),error=receipt.get('error')))
    return failures


def candidate_analysis_status(ctx,source_node):
    """Compact read-only status derived only from Store artifacts, receipts and Route nodes."""
    _,binding,protocol,target,versions,_,scope_identity=candidate_analysis_scope(ctx,source_node)
    node,built=_build(ctx,source_node);chain,_,bundles=_matching_chain(ctx,binding,protocol,target)
    route=ctx.store.session(ctx.run_id)['state'].get('route',{})
    reports=[]
    for report_node in route.get('nodes',[]):
        if report_node.get('action')!='analyze' or report_node.get('status')!='completed' or not report_node.get('result'):continue
        report=ctx.artifact(report_node['result'])
        if report.get('source_build_node')==source_node and report.get('build_configuration')==built['configuration']:
            reports.append((report_node['result'],report))
    registered=reports[-1] if reports else None
    matching_bundles=[row for row in bundles if row[1].get('analysis_scope_identity')==scope_identity]
    bundle=matching_bundles[-1] if matching_bundles else None
    failed=_failed_prepare_attempts(ctx,source_node)
    components={};missing=[]
    failed_selections=[row.get('selection',{}) for row in route.get('nodes',[])
        if row.get('action')=='analyze' and row.get('status')=='failed'
        and row.get('selection',{}).get('source_node')==source_node]
    for name,(kind,tool,default) in _COMPONENTS.items():
        row=chain.get(name)
        if registered and registered[1].get(name):
            components[name]=dict(state='available_attached',available=True,reference=registered[1][name])
            continue
        if row:
            components[name]=dict(state='available_unattached',available=True,reference=row[0])
            continue
        incompatible=None
        for selection in reversed(failed_selections):
            reference=selection.get(name)
            if not reference:continue
            try:value=ctx.artifact(reference)
            except ValueError:continue
            if value.get('kind')!=kind:
                incompatible=dict(state='incompatible_kind',reference=reference,detail=f'Expected {kind}; received {value.get("kind")!r}.');break
            if value.get('protocol')!=protocol:
                incompatible=dict(state='incompatible_protocol',reference=reference,detail='Reference belongs to a different analysis protocol.');break
            if not _same_binding(value,binding):
                incompatible=dict(state='foreign_candidate_or_configuration',reference=reference,detail='Reference belongs to a different candidate, build, or immutable configuration.');break
            if name=='endpoint' and target not in value.get('evidence',[]):
                incompatible=dict(state='incompatible_target',reference=reference,detail='Endpoint result does not bind the frozen Route target.');break
            incompatible=dict(state='incompatible_evidence_chain',reference=reference,detail='Result exists but does not form the exact upstream evidence chain required for this build.');break
        bundle_component=(bundle[1].get('components',{}).get(name) if bundle else None) or {}
        if bundle_component.get('status')=='failed':
            components[name]=dict(state='computation_failed',available=False,
                detail=bundle_component.get('detail'),failure=bundle_component.get('failure'))
        elif incompatible:
            components[name]=dict(available=False,**incompatible)
        elif failed:
            components[name]=dict(state='computation_failed',available=False,
                detail=failed[-1]['error'],request_id=failed[-1]['request_id'])
        else:
            components[name]=dict(state='not_performed',available=False)
        missing.append(name+': '+components[name]['state'])
    proposal=built.get('proposal_provenance')
    if proposal:
        proposal={key:proposal.get(key) for key in ('optimizer_candidate_id','optimizer_result','proposal_configuration',
            'scientific_configuration_identity','source_build_node')}
    result=dict(source_node=source_node,build_candidate_id=built['candidate_id'],build_result=node['result'],
        immutable_configuration=built['configuration'],scientific_configuration_identity=binding['scientific_configuration_identity'],
        protocol=protocol,endpoint_target=target,analysis_scope_identity=scope_identity,components=components,
        bundle=None if bundle is None else bundle[0],registered_report=None if registered is None else registered[0],
        proposal_provenance=proposal,analysis_complete=all(row['available'] for row in components.values()),
        missing_or_incompatible=missing)
    if not result['analysis_complete']:
        result['candidate_analysis_operation']=dict(tool_id='analysis.prepare_candidate',arguments=dict(source_node=source_node))
    if registered is None:
        result['registration_operation']=dict(tool_id='route.record_analysis',source_node=source_node,
            required_prior_node_evidence=[node['result']],candidate_analysis_bundle=None if bundle is None else bundle[0])
    return result


def evaluate_candidate(ctx,args):
    from .gvs import gvs_evaluate_tool_v2
    from .contracts import GVSDynamicsRequestV3
    inp,binding=resolve_candidate(ctx,args.source_node)
    request=GVSDynamicsRequestV3(**args.model_dump(exclude={'source_node'}),
        basis=inp.policy.controller.parameters.data['recipe']['basis'])
    result=gvs_evaluate_tool_v2(SimpleNamespace(input=inp,reg=ctx.reg),request)
    from .design_decisions import physical_summary
    return CandidateAnalysisResult(binding=binding,calculation=plain(result),
        physical_summary=physical_summary(inp.robot.structure.data, inp.policy.discretization.data))


def require_completed_analysis(ctx, built, tool):
    """A Route run must cite mathematics on this exact owned build first."""
    import json
    with ctx.store.connect(True) as db:
        receipts=[json.loads(r['receipt']) for r in db.execute(
            'SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,))]
    for receipt in receipts:
        if receipt['tool_id']==tool and receipt['execution_status']=='completed' and receipt.get('output'):
            binding=ctx.artifact(receipt['output'])['binding']
            if binding['configuration']==built['configuration'] and binding['candidate_id']==built['candidate_id']:
                return receipt['output']
    raise ValueError('CANDIDATE_BOUND_ANALYSIS_REQUIRED_BEFORE_EXECUTION: '+tool)
