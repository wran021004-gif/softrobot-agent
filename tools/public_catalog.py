"""One discoverable projection of the actual allowlists; imports no engines.

Legacy wire names are scoped aliases. Library manifests never grant execution.
"""
from schemas.public_tools import PCCJacobian, PublicResult, ToolCall, SavedDiagnosis

VERSION = '1.1.0'
PCC_DESCRIPTION = ('Analytic single-section, inextensible PCC tip and local Jacobian. '
    'Origin at base, +x straight, bending in yz. No gravity, contact, elasticity, '
    'dynamics, calibration or task scoring; norm(bend_rad)<=pi. Outputs m and m/rad.')


def declaration_check(tool):
    """AST evidence for declared library entrypoints, without backend imports."""
    import ast
    from tools.spec_tools import ROOT
    implementation=tool.get('implementation')
    if not implementation:
        return 'NO_IMPLEMENTATION_DECLARED'
    path=ROOT/(implementation['module'].replace('.','/')+'.py')
    if not path.is_file():
        return 'MISSING_MODULE'
    nodes=ast.parse(path.read_text(encoding='utf8')).body
    for part in implementation['callable'].split('.'):
        node=next((n for n in nodes if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==part),None)
        if node is None:
            return 'MISSING_DECLARED_CALLABLE'
        nodes=getattr(node,'body',[])
    if implementation.get('backend') and not (ROOT/implementation['backend']).is_file():
        return 'MISSING_BACKEND_SOURCE'
    return 'ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED'


def entries():
    from tools.workbench_catalog import TOOLS as workbench, DESIGN_TOOLS
    from schemas.dynamic_workbench import TOOLS as dynamics, Read, RenderVideo
    from schemas.workbench import NoArguments
    out = {}
    for name, info in workbench.items():
        out['workbench.'+name] = _entry('workbench.'+name, 'workbench', name,
            info['schema'], info['permission'], info['purpose'],
            requires=info['requires'], cost=info['cost'],
            scope=('design_session' if name in DESIGN_TOOLS else 'fixed_session') if name != 'read_evidence' else 'both_sessions',
            implementation='tools.workbench_actions:execute',
            assumptions=['Frozen V1 task route and session exploration envelope; inspect request.json.'])
    for name, (schema, permission, description) in dynamics.items():
        out['dynamics.'+name] = _entry('dynamics.'+name, 'dynamics', name, schema, permission,
            description, implementation='tools.dynamic_actions:'+name,
            scope='campaign grant and optional subordinate experiment',
            assumptions=['Frozen numerical route; task, duration, bounds and resource limits come from saved request/grant.'])
    for name in ('stop_design', 'capability_missing'):
        out['workbench.'+name] = _entry('workbench.'+name, 'workbench', name, NoArguments,
            'session_control', 'Record a cited terminal decision with reason; no numerical execution.',
            implementation='tools.workbench:Workbench.submit', scope='design_session control', assumptions=['Only changes workflow status; never scientific truth.'])
    from tools.tool_registry import service_tools
    for definition in service_tools().values():
        tool_id,schema,permission,description,implementation=(definition.tool_id,definition.schema,definition.permission,definition.description,definition.binding)
        out[tool_id] = _entry(tool_id, 'services', tool_id.replace('.', '__'), schema, permission,
            description, implementation=implementation, scope='independent configured service session',
            assumptions=[PCC_DESCRIPTION] if permission == 'analysis' else ['Saved evidence only; preserve recorded frame, time phases and model identity.'])
        out[tool_id].update(tool_version=definition.version,registered=True,implemented=bool(definition.binding),
            accepted_versions=[definition.version,*definition.compatible_versions],
            callable=bool(definition.binding),permission_granted=None,
            execution=dict(adapter=definition.adapter,isolation=definition.isolation,timeout_s=definition.timeout_s,
                process_tree=definition.process_tree,timeout_scope='worker execution, including startup/render/encode/decode/shutdown; up to 5 seconds for termination' if definition.process_tree else 'worker only' if definition.isolation=='process' else 'no public hard deadline',
                cache=definition.cache,resources=dict(definition.resources),input_refs=list(definition.input_refs)),
            detail_contract=definition.output_contract)
        out[tool_id]['analysis_scope']=definition.analysis_scope
        out[tool_id]['detail_schema']=definition.output_schema.model_json_schema() if definition.output_schema else None
        out[tool_id]['implementation_status']='IMPLEMENTED' if definition.binding else 'PLANNED'
    return out


def _entry(tool_id, runtime, alias, schema, permission, purpose, *, requires=(), cost=None,
           scope, implementation, assumptions):
    numerical = alias in ('simulate_candidate', 'evaluate_candidate', 'evaluate_design', 'optimize_matlab')
    video = tool_id.endswith('render_simulation_video')
    return dict(tool_id=tool_id, tool_version=VERSION, contract_version='1.0', runtime=runtime,
        registered=True,implemented=True,permission_granted=None,accepted_versions=['1.0.0',VERSION],
        wire_name=alias, schema=schema, permission=permission, purpose=purpose,
        requires=list(requires), scope=scope, implementation=implementation,
        implementation_status='IMPLEMENTED', callable=True,
        dependency_conditions=(['MATLAB Engine/license for MATLAB; MuJoCo for MuJoCo; exact requirements selected by backend'] if numerical else
            ['Cache hit: saved files only; otherwise MuJoCo Renderer or MATLAB Figure; FFmpeg or MATLAB MPEG-4 encoder'] if video else ['Python dependencies in requirements.txt']),
        availability='CONDITIONAL: runtime binding, permissions, evidence, budget and dependencies checked at invocation; no startup probe',
        cost_policy=dict(reservation=cost or {}, backend_solves='per actual rollout; failed reservations retained' if numerical else 0,
            billing_owner=runtime, tool_calls='existing runner rules; services charge one validated permitted call including cache hits',
            model_calls='host transport only; human/development tool invocation does not charge model API calls',
            wall_time='measured elapsed separately; legacy campaign active wall accounting unchanged'),
        assumptions=assumptions, units=dict(length='m', angle='rad', force='N', time='s', jacobian='m/rad'),
        time_semantics='Saved time_s is post-step state time; solver_time_s is solver force phase; playback time differs; wall time is monotonic elapsed.',
        frame='Read saved environment/IR. PCC explicit base origin, +x straight, yz bending; no implicit world transform.',
        result_schema='PublicResult', failure_categories=['input','permission','budget','evidence','dependency','timeout','interrupted','execution'])


def catalog(runtime=None):
    from capabilities.registry import query_tools, load_catalog
    tools = [{k: v for k, v in info.items() if k != 'schema'} |
             {'input_schema': info['schema'].model_json_schema()}
             for info in entries().values() if runtime is None or info['runtime'] == runtime]
    library = [dict(tool_id='library.'+t['bundle']+'.'+t['name'], name=t['name'],
        implementation_status=t['implementation_status'], callable=False,
        declaration_check=declaration_check(t),
        manifest=t, note='Descriptive library entry; not an executable public alias. Use explicit runtime adapter.') for t in query_tools()]
    bundle_paths={};aliases={}
    for name,path in load_catalog()['tool_bundles'].items():
        if path in bundle_paths:aliases[name]=bundle_paths[path]
        else:bundle_paths[path]=name
    return dict(contract_version='1.0', tools=tools, library=library,library_bundle_aliases=aliases,
        unavailable=['Host video/frame inspection: references do not expose pixels to a text-only model.',
                     'New task semantics, general dynamics quantities, force/torque actuator channels and multi-agent scheduling need explicit adapters.'],
        call_schema=ToolCall.model_json_schema(), result_schema=PublicResult.model_json_schema(),
        alias_rule='Bare names resolve only within a bound runtime. Cross-runtime public calls require tool_id. No silent fallback.')


def native_tools(runtime):
    """Provider wire schema generated from exactly the same registered inputs."""
    out = []
    for info in entries().values():
        if info['runtime'] != runtime or not info['implemented']:
            continue
        s = info['schema'].model_json_schema()
        s['properties'].update(reason={'type':'string','minLength':1},
            evidence={'type':'array','items':{'type':'string'},'minItems':0 if runtime == 'services' else 1})
        s['required'] = s.get('required', []) + ['reason', 'evidence']
        if runtime == 'dynamics':
            s['properties']['working_memory'] = dict(type='object', properties=dict(
                findings={'type':'array','items':{'type':'string'}}, unresolved={'type':'array','items':{'type':'string'}}, next_action={'type':'string'}), additionalProperties=False)
            s['required'].append('working_memory')
        out.append(dict(type='function', function=dict(name=info['wire_name'],
            description=f"{info['tool_id']}@{info['tool_version']}: {info['purpose']} Permission: {info['permission']}. Requires: {info['requires']}. Backend solves: {info['cost_policy']['backend_solves']}.", parameters=s)))
    return out


def discover_bound(book):
    """Read-only availability view. Dependencies are declared, never started."""
    runtime='dynamics' if book.state.get('version')=='dynamic_workbench_v2' or hasattr(book,'ledger') else 'workbench'
    result=catalog(runtime)
    remaining=book.remaining()
    design=bool(book.state['request'].get('design_session'))
    for entry in result['tools']:
        reasons=[]
        if entry['permission']!='session_control' and entry['permission'] not in book.state['request']['permissions']:
            reasons.append('PERMISSION_DENIED')
        if runtime=='workbench':
            scope=entry['scope']
            if ('design_session' in scope and not design) or (scope=='fixed_session' and design):
                reasons.append('SESSION_MODE_MISMATCH')
        if remaining.get('decisions',1)<=0:
            reasons.append('DECISION_BUDGET_EXHAUSTED')
        entry['session_available']=not reasons
        entry['session_blockers']=reasons
        entry['remaining']=remaining
        entry['invocation_checks']='Backend budget, candidate-bound prerequisites, evidence hashes, cache and experiment restrictions checked by submit.'
    return result


def workbench_native_tools():
    from tools.workbench_catalog import DESIGN_TOOLS
    from schemas.workbench import WorkingMemory
    allowed = set(DESIGN_TOOLS) | {'read_evidence','stop_design','capability_missing'}
    out = [t for t in native_tools('workbench') if t['function']['name'] in allowed]
    for tool in out:
        schema=tool['function']['parameters']
        schema['properties']['working_memory']=WorkingMemory.model_json_schema()
        schema['required'].append('working_memory')
    return out


def markdown_catalog(directory):
    """Generated documentation is a projection, never another registry."""
    clean=lambda value:str(value).replace('|',' / ').replace('\n',' ')
    lines=['# Unified tool directory (generated)', '',
        'Generated by `python examples/public_tools.py catalog --markdown --output docs/public_tools_catalog.md`.',
        'Public protocol 1.0; each registration owns its tool version and accepted compatibility set. Full schemas are in the JSON catalog.',
        'See [framework extensions and migration](framework_extensions.md). Registration and implementation do not grant permission.', '',
        '| Public identity | Tool version | Required permission | Purpose | Implementation binding |', '| --- | --- | --- | --- | --- |']
    for tool in directory['tools']:
        lines.append('| '+' | '.join(clean(tool[k]) for k in ('tool_id','tool_version','permission','purpose','implementation'))+' |')
    lines+=['','## 库能力（不授予公共调用权限）','',
        'IMPLEMENTED 表示已声明实现；AST 检查只证明声明入口存在，未启动后端。PLANNED 不可执行。',
        '库名可与公共名称相似，但参数和调用层级不同；不得自动互换。','',
        '| 库身份 | 声明状态 | 源码核对 | 既有入口 |','| --- | --- | --- | --- |']
    for tool in directory['library']:
        impl=tool['manifest'].get('implementation') or {}
        entry=impl.get('module','')+':'+impl.get('callable','') if impl else '—'
        lines.append('| '+' | '.join(clean(x) for x in (tool['tool_id'],tool['implementation_status'],tool['declaration_check'],entry))+' |')
    lines+=['','Bundle aliases: `'+str(directory['library_bundle_aliases'])+'`.', '',
        'Service bindings, model quantities, saved-signal rules, task context, evaluator/search and C1/C2 lifecycle are implemented. See framework_extensions.md for supported scope and extension routes. Host visual understanding and new actuator channels remain outside this release.', '']
    return '\n'.join(lines)
