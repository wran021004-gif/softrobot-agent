"""Task-independent saved-evidence/analysis runtime with durable call receipts.

No evaluator or dynamics backend is imported by math/read operations.
"""
import json
from pathlib import Path
import time
from uuid import uuid4

from schemas.public_tools import Caller, ServiceConfig, ToolCall, PCCJacobian
from tools.artifact_tools import file_hash
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, read, digest


def checked_path(root, registry, ref):
    item = registry.get(ref)
    if item is None:
        raise ValueError('UNREGISTERED_EVIDENCE: '+ref)
    path = (root / item.get('path', ref)).resolve()
    if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != item['sha256']:
        raise ValueError('EVIDENCE_CHANGED_OR_MISSING: '+ref)
    return path


def pcc_jacobian(arguments):
    from tools.pcc_math import tip_and_jacobian
    args = PCCJacobian.model_validate(arguments)
    tip, jacobian = tip_and_jacobian(args.length_m, args.bend_rad)
    return dict(tip_m=tip, tip_jacobian_m_per_rad=jacobian,
        tip_length_derivative=[v/args.length_m for v in tip], frame=args.frame,
        model_id='single_section_inextensible_pcc_v1', backend_solves=0,
        assumptions=['Constant curvature, one section, fixed base, no extension.',
                     'No mechanics, gravity, contact, dynamics or physical calibration.'],
        applicability='Local geometric derivative on norm(bend_rad)<=pi; not a reachable-task certificate.',
        units=dict(tip='m', jacobian='m/rad', length_derivative='dimensionless'))


def read_json(root, registry, arguments):
    from tools.dynamic_context import evidence_page
    args = dict(arguments)
    ref = args.pop('evidence_ref')
    return evidence_page(read(checked_path(root, registry, ref)), ref, **args)


def saved_diagnosis(root, registry, arguments, *, source_identity=None):
    from tools.trajectory_diagnosis import diagnose, load_rows, metadata_from_shared
    path=checked_path(root,registry,arguments['result_ref'])
    result=read(path)
    if result.get('backend')!=arguments['backend']:
        raise ValueError('BACKEND_MISMATCH')
    paths=[path,path.parent/'shared_input.json',path.parent/'trajectory.json.gz']
    hashes={}
    for item in paths:
        ref=item.relative_to(root).as_posix()
        hashes[ref]=file_hash(checked_path(root,registry,ref))
    rows=load_rows(paths[-1])
    if not rows:
        raise ValueError('MISSING_SAVED_SAMPLES')
    start=min(rows[0]['time_s'],rows[0]['solver_time_s']) if arguments['t_start_s'] is None else arguments['t_start_s']
    end=max(rows[-1]['time_s'],rows[-1]['solver_time_s']) if arguments['t_end_s'] is None else arguments['t_end_s']
    try:
        identity = source_identity or {}
        meta=metadata_from_shared(read(paths[1]),identity.get('candidate_id',result.get('candidate_id','saved')),
            arguments['backend'],identity.get('run_id',root.name))
        data=diagnose(paths[-1],meta,arguments['entity'],start,end,arguments['fields'])
    except KeyError as exc:
        raise ValueError('MISSING_SAVED_FIELD: '+str(exc)) from exc
    if not data.get('queries') and not data.get('events') and data.get('status') not in ('NO_EVENT','MISSING_DATA'):
        raise ValueError('NO_SAVED_SAMPLE_OR_ENTITY: inspect saved entity names and time range')
    data.update(source_hashes=hashes,backend_solves=0,rescoring=False,
        processor='tools.trajectory_diagnosis.diagnose',processor_sha256=file_hash(ROOT/'tools/trajectory_diagnosis.py'),
        interval_s=[start,end])
    return data


class ServiceSession:
    def __init__(self, root):
        self.root = Path(root).resolve()
        runs = (ROOT/'runs').resolve()
        if not self.root.is_relative_to(runs) or self.root == runs:
            raise ValueError('Service output must be a child of runs/')

    def create(self, config, *, source_root=None, evidence_refs=()):
        config = ServiceConfig.model_validate(config).model_dump(mode='json')
        imports = []
        if source_root is not None:
            source = Path(source_root).resolve()
            if not source.is_relative_to((ROOT/'runs').resolve()) or source == self.root:
                raise ValueError('Evidence source must be a separate saved repository run')
            registry = read(source/'state.json')['evidence']
            for ref in evidence_refs:
                path = checked_path(source, registry, ref)
                # Keep original directory structure, but never copy run management files.
                relative = path.relative_to(source)
                if relative.parts[0] in ('state.json','service_config.json','service_calls','.owner.lock'):
                    raise ValueError('INVALID_EVIDENCE_IMPORT: '+ref)
                imports.append((relative, path.read_bytes(), str(source), ref, registry[ref]['sha256']))
        elif evidence_refs:
            raise ValueError('Evidence source is required')
        self.root.mkdir(parents=True, exist_ok=False)
        atomic_json(self.root/'service_config.json', config)
        state = dict(version='public_services_v1', config=config, config_hash=digest(config),
                     used={'tool_calls':0}, calls=[], evidence={}, imports=[])
        for relative, data, source, original_ref, expected in imports:
            destination = self.root/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            if file_hash(destination) != expected:
                raise ValueError('EVIDENCE_CHANGED_DURING_IMPORT')
            ref = destination.relative_to(self.root).as_posix()
            state['evidence'][ref] = dict(sha256=expected)
            state['imports'].append(dict(ref=ref, source_root=source, source_ref=original_ref, sha256=expected))
        atomic_json(self.root/'state.json', state)
        return state

    def discover(self):
        from tools.public_catalog import catalog
        state = self.load()
        result = catalog('services')
        for entry in result['tools']:
            entry['permitted'] = entry['permission'] in state['config']['permissions']
            entry['remaining_tool_calls'] = state['config']['tool_calls']-state['used']['tool_calls']
        return result

    def load(self):
        state = read(self.root/'state.json')
        if state.get('version') != 'public_services_v1':
            raise ValueError('Wrong runtime: public service session required')
        if digest(read(self.root/'service_config.json')) != state['config_hash'] or digest(state['config']) != state['config_hash']:
            raise ValueError('PERMISSION_CONFIG_CHANGED')
        return state

    def invoke(self, value, *, caller):
        from tools.workbench import owner
        # Trusted host supplies caller, never tool arguments.
        caller = Caller.model_validate(caller).model_dump(mode='json')
        with owner(self.root):
            return self._invoke(value, caller)

    def _invoke(self, value, caller):
        from tools.public_catalog import entries
        from tools.public_feedback import normalize
        state = self.load()
        # Recovery seals the accounting state without replaying any operation.
        for old in state['calls']:
            if old['status'] == 'reserved':
                old['status'] = 'interrupted'
                result_path=self.root/old['result_ref']
                if result_path.is_file():
                    from schemas.public_tools import PublicResult
                    sealed=PublicResult.model_validate(read(result_path))
                    if sealed.call_id != old['call_id']:
                        raise ValueError('EVIDENCE_CALL_ID_MISMATCH')
                    for item in sealed.evidence:
                        path=(self.root/item.ref).resolve()
                        if not path.is_relative_to(self.root) or not path.is_file() or (item.sha256 and file_hash(path)!=item.sha256):
                            raise ValueError('EVIDENCE_CHANGED_DURING_RECOVERY')
                        state['evidence'][item.ref]=dict(sha256=file_hash(path))
                    state['evidence'][old['result_ref']]=dict(sha256=file_hash(result_path))
                    old['status']=sealed.execution_status
        call_id = uuid4().hex
        folder = self.root/'service_calls'/call_id
        folder.mkdir(parents=True)
        ref = (folder/'result.json').relative_to(self.root).as_posix()
        tool_id = value.get('tool_id', 'unknown') if isinstance(value, dict) else 'unknown'
        if not isinstance(tool_id,str):
            tool_id='unknown'
        started = time.monotonic()
        row = dict(call_id=call_id, tool_id=tool_id, caller=caller, status='rejected', result_ref=ref)
        state['calls'].append(row)
        charged = 0
        refs = []
        arguments = {}
        implementation_hashes = {}
        cache_key = None
        resolved_version = None
        requested_version = None
        try:
            call = ToolCall.model_validate_json(json.dumps(value, allow_nan=False), strict=True)
            requested_version=call.tool_version
            tool_id = call.tool_id
            info = entries().get(tool_id)
            if info is None or info['runtime'] != 'services':
                raise ValueError('UNKNOWN_TOOL: discover the bound services catalog')
            from tools.tool_registry import service_tools
            from tools.service_execution import identity, execute
            definition=service_tools()[tool_id]
            resolved_version=definition.version
            if call.tool_version is not None and call.tool_version not in (definition.version,*definition.compatible_versions):raise ValueError('TOOL_VERSION_MISMATCH')
            if not definition.binding:raise ValueError('IMPLEMENTATION_REQUIRED: '+tool_id)
            arguments = info['schema'].model_validate_json(json.dumps(call.arguments, allow_nan=False), strict=True).model_dump(mode='json')
            if info['permission'] not in state['config']['permissions']:
                raise ValueError('PERMISSION_DENIED: '+info['permission'])
            for evidence_ref in dict.fromkeys(call.evidence + [arguments[k] for k in definition.input_refs]):
                path = checked_path(self.root, state['evidence'], evidence_ref)
                refs.append(dict(ref=evidence_ref, sha256=file_hash(path), role='input'))
            cache_key,implementation_hashes=identity(definition,arguments,refs)
            cached=state.get('cache',{}).get(cache_key) if definition.cache else None
            if cached:checked_path(self.root,state['evidence'],cached)
            if state['used']['tool_calls'] >= state['config']['tool_calls']:
                raise ValueError('BUDGET_EXHAUSTED: tool_calls')
            atomic_json(folder/'request.json', dict(call=call.model_dump(mode='json'), caller=caller, parsed_arguments=arguments))
            charged = 1
            state['used']['tool_calls'] += charged
            row['status'] = 'reserved'
            row.update(cache_key=cache_key,implementation_hashes=implementation_hashes,resources=dict(definition.resources))
            atomic_json(self.root/'state.json', state)
            if cached:
                data={**read(checked_path(self.root,state['evidence'],cached)), 'cached':True,'cache_source_ref':cached}
            else:
                data=execute(definition,self.root,state['evidence'],arguments,folder)
                if definition.output_schema:
                    data=definition.output_schema.model_validate_json(json.dumps(data,allow_nan=False),strict=True).model_dump(mode='json')
            legacy = dict(status='completed', data=data)
            if data.get('status')=='EXECUTION_FAILED':
                legacy.update(status='failed',failure_code='DIAGNOSTIC_EXECUTION_FAILED',message=data.get('reason','Rule execution failed'))
        except Exception as exc:
            legacy = dict(status='failed' if charged else 'rejected', failure_code='TOOL_ERROR' if charged else 'INVALID_REQUEST', message=str(exc), data={})
        detail_ref = (folder/'data.json').relative_to(self.root).as_posix()
        atomic_json(self.root/detail_ref, legacy['data'])
        state['evidence'][detail_ref] = dict(sha256=file_hash(self.root/detail_ref))
        if legacy['status']=='completed' and definition.cache:
            state.setdefault('cache',{})[cache_key]=detail_ref
        refs.append(dict(ref=detail_ref, sha256=state['evidence'][detail_ref]['sha256'], role='detail'))
        for key, output in legacy['data'].items():
            if key.endswith('_ref') and isinstance(output, str) and output in state['evidence']:
                refs.append(dict(ref=output, sha256=state['evidence'][output]['sha256'], role='output'))
        result = normalize(tool_id, legacy, call_id=call_id, caller=caller, evidence=refs, details_ref=detail_ref,
            tool_version=resolved_version,
            analysis_scope=definition.analysis_scope if charged else None,
            cost=dict(charged={'tool_calls':charged, 'backend_solves':0, 'model_calls':0}, elapsed_s=time.monotonic()-started,
                      cache_hit=bool(legacy['data'].get('cached')), billing_owner='services',
                      recovery='Charged before execution; interrupted calls never automatically replayed.'),
            provenance=dict(arguments=arguments,requested_tool_version=requested_version,config_hash=state['config_hash'], imports=state['imports'],
                implementation_hashes=implementation_hashes,cache_key=cache_key,
                processing='Analytic computation or saved-data processing; no dynamics or rescoring.'))
        atomic_json(self.root/ref, result)
        state['evidence'][ref] = dict(sha256=file_hash(self.root/ref))
        row['status'] = legacy['status']
        atomic_json(self.root/'state.json', state)
        return result

    def apply_tool_call(self, function, *, caller):
        """Native provider response adapter; same core invocation as human JSON."""
        from tools.public_catalog import entries
        try:
            args = json.loads(function['arguments'])
            if not isinstance(args,dict):
                raise ValueError('Tool arguments must be an object')
            name = function['name']
        except (ValueError,KeyError,TypeError) as exc:
            return self.invoke(dict(tool_id='unknown',arguments={},reason='INVALID_NATIVE_CALL: '+str(exc),evidence=[]),caller=caller)
        entry = next((i for i in entries().values() if i['runtime']=='services' and i['wire_name']==name), None)
        tool_id = entry['tool_id'] if entry else name
        reason = args.pop('reason', '')
        evidence = args.pop('evidence', [])
        return self.invoke(dict(tool_id=tool_id,tool_version=entry['tool_version'] if entry else None,
            arguments=args, reason=reason, evidence=evidence), caller=caller)
