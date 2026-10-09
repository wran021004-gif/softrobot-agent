"""Bounded Mainline 3 V2 orchestration through existing Host/public tools."""
from copy import deepcopy
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path
import time
from schemas.platform import SessionInput,ProjectConfig
from schemas.platform import EvidenceRef
from schemas.common import Contract
from pydantic import Field
from tools.state_io import atomic_json,read,digest
from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.research_execution import invoke
from extensions.tendon_family import finite_templates as finite

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/research_mainline3_v2_20261009'
RUN=ROOT/'runs/mainline3-v2-20261009'
STARTED_UNIX=1791526756.
LIMITS=dict(model_calls=40,tool_calls=1024,backend_solves=6,worker_calls=0,wall_s=43200.)
REPORT_OUTPUT_BYTES=1048576
TOOLS={'research.prepare_candidate':'1.0.0','analysis.linearize_configuration':'1.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
    'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0',
    'research.task_acceptance':'1.0.0'}


class Empty(Contract):
    pass


class TemplateSelection(Contract):
    template: str = Field(description='Granted named categorical template T0, T1, T2 or T3; no interpolation')


class CandidateDimensions(Contract):
    configuration: EvidenceRef


class CapabilityResult(Contract):
    detail: dict


class CapabilityReport(Contract):
    configuration: EvidenceRef
    execution_evidence: EvidenceRef
    interpretation: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


def public_catalog(ctx,args):
    from tools.parameter_catalog import effective_catalog
    return CapabilityResult(detail=effective_catalog(plain(ctx.input)))


def public_select(ctx,args):
    from tools.platform_search import parameter_search
    space=ctx.input.policy.candidate_builder.parameters.data
    options=space['parameters']['template']['options']
    algorithm=parameter_search(plain(ctx.input),'search.family_explicit@1.0.0',
        {'template':{'kind':'discrete','choices':options}},candidates=[{'template':args.template}])
    selected=algorithm.propose()
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']
        state['v2_template_selection']=dict(changes=selected,method='search.family_explicit@1.0.0')
        ctx.store.update_state(db,ctx.run_id,state)
    return CapabilityResult(detail=dict(changes=selected,method='search.family_explicit@1.0.0',
        next_tool='research.prepare_candidate',scientific_execution=False))


def public_dimensions(ctx,args):
    candidate=ctx.artifact(args.configuration)
    if candidate['baseline_identity']!=digest(plain(ctx.input)) or digest(candidate['effective'])!=candidate['content_identity']:
        raise ValueError('V2_DIMENSIONS_OWNED_CONFIGURATION_REQUIRED')
    return CapabilityResult(detail=finite.dimensions(SessionInput.model_validate(candidate['effective'])))


def public_report(ctx,args):
    if len(json.dumps(plain(args),ensure_ascii=False).encode('utf8'))>REPORT_OUTPUT_BYTES:
        raise ValueError('V2_CAPABILITY_REPORT_EXCEEDS_1_MIB_ALLOWANCE')
    candidate=ctx.artifact(args.configuration)
    selection=ctx.store.session(ctx.run_id)['state'].get('v2_template_selection',{})
    if candidate['baseline_identity']!=digest(plain(ctx.input)) or candidate['changes']!=selection.get('changes'):
        raise ValueError('V2_REPORT_REQUIRES_OWN_SELECTED_PREPARATION')
    key=finite.template_id(candidate['effective']['robot']['structure']['data'])
    if key=='T0':raise ValueError('V2_CAPABILITY_USE_REQUIRES_NONBASELINE')
    evidence=ctx.artifact(args.execution_evidence)
    original=ctx.artifact(evidence['configuration'])
    from extensions.tendon_family.gvs_profile import execution_scope
    if execution_scope(original['effective'])!=execution_scope(candidate['effective']):
        raise ValueError('V2_REPORT_SCIENTIFIC_SCOPE_MISMATCH')
    if evidence.get('status') not in ('accepted','valid_failure'):
        raise ValueError('V2_REPORT_REQUIRES_COMPLETE_VALID_EVIDENCE')
    detail=dict(report=plain(args),template=key,original_execution_id=evidence['execution_id'],
        label='engineered capability-use test',scientific_claims='No autonomous topology invention, optimization gain or research superiority established')
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state'];state['v2_capability_report']=detail
        ctx.store.update_state(db,ctx.run_id,state,'stopped')
    return CapabilityResult(detail=detail)


def configuration(run_id='mainline3-v2'):
    from extensions.tendon_family.gvs_profile import profile_input
    value=profile_input(run_id);source=finite.catalog()['scientific_source']
    for field in ('robot','task','seed'):value[field]=deepcopy(source[field])
    for field,binding in source['policy'].items():value['policy'][field]=deepcopy(binding)
    value=finite.study_input(value)
    value['policy'].update(budget=deepcopy(LIMITS),allowed_tools=list(TOOLS),tool_bindings=deepcopy(TOOLS),
        timeout_s=36000.,operation_allowances={t:dict(timeout_s=36000.,reserve_s=6000. if t=='simulation.run' else 1200. if t=='analysis.linearize_configuration' else 60.) for t in TOOLS})
    return SessionInput.model_validate(value).model_dump(mode='json')


def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'activity.json').exists():return read(OUT/'activity.json')
    value=dict(activity_id='mainline3-v2-20261009',started_unix=STARTED_UNIX,
        started_at=datetime.fromtimestamp(STARTED_UNIX,timezone.utc).isoformat(),
        deadline_unix=STARTED_UNIX+43200,execution_cutoff_unix=STARTED_UNIX+41400,
        limits=LIMITS,mathematical_operations=32,primary_backend_slots=['T1','T2','T3','justified_T0'],
        technical_retry_slots=2,authorization_attachment='6632c0ed-5d89-4aaa-9d00-827531ca80d3/pasted-text-1.txt',
        original_source=dict(configuration=finite.catalog()['t0_configuration'],backend_execution=finite.catalog()['t0_backend_execution']),
        finite_catalog_identity=digest(finite.catalog()),delivery_reserve_s=1800.,
        provider_monetary_cost=None,engineering_interventions=[])
    atomic_json(OUT/'activity.json',value)
    atomic_json(OUT/'frozen_templates.json',finite.catalog())
    return value


def start():
    activity=freeze();store=Store(RUN)
    if not store.db.exists():
        store.create(ProjectConfig(project_id=activity['activity_id'],grant_id='mainline3-v2-original-grant',
            authorization_source='Explicit V2 authorization attachment 6632c0ed-5d89-4aaa-9d00-827531ca80d3; independent finite templates and real capability-use model session',
            budget=LIMITS,exclusive_resources={'backend.family_mujoco':1}))
    host=Host(RUN,'mainline3-v2')
    if not host.folder.exists():host.create(configuration())
    host.resume()
    return host


def native_configuration(run_id='mainline3-v2-native'):
    value=configuration(run_id)
    tools={t:'1.0.0' for t in ('research.capability_catalog','research.select_template',
        'research.prepare_candidate','research.candidate_dimensions','evidence.read','research.capability_report')}
    model=deepcopy(read(ROOT/'evidence/research_mainline3_v1_handoff_20261009/frozen_configuration.json')['policy']['model'])
    model.update(max_turns=40,max_repairs=10,protocol_recovery=dict(max_total=40,max_consecutive=40),
        tool_naming=None,length_recovery=None)
    value['policy'].update(model=model,allowed_tools=list(tools),tool_bindings=tools,
        operation_allowances={t:dict(timeout_s=600.,reserve_s=30.) for t in tools})
    return SessionInput.model_validate(value).model_dump(mode='json')


def native_session():
    from tools.platform_models import run_loop
    from tools.investigation_contract import BusinessFieldsAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    from tools.context_assembly import _no_secrets
    activity=read(OUT/'activity.json');host=Host(RUN,'mainline3-v2-native')
    evidence={}
    for key in ('T1','T2','T3'):
        result=read(OUT/(key+'_result.json'))
        with host.store.transaction() as db:
            evidence[key]=plain(host.store.put(db,result['joint_acceptance']))
    if not host.folder.exists():
        host.create(native_configuration())
        menu=invoke(host,'research.capability_catalog',{},request_id='native-catalog-handoff')
        if menu['execution_status']!='completed':raise ValueError('V2_NATIVE_CATALOG_HANDOFF_FAILED: '+str(menu))
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state']
            state['role_context']=dict(role='research',phase='finite_capability_use',
                shared_provider_capacity=True,evidence=evidence,
                report_output_bytes=REPORT_OUTPUT_BYTES,
                capability_catalog=host.store.artifact(menu['output']),capability_catalog_reference=menu['output'],
                execution_evidence={key:host.store.artifact(ref) for key,ref in evidence.items()},
                activity_deadline_unix=activity['execution_cutoff_unix'],
                instructions='Engineered finite capability-use test. The actual granted capability_catalog was delivered by research.capability_catalog and its public receipt/reference is supplied. Choose one supported nonbaseline T1/T2/T3 yourself through research.select_template, then research.prepare_candidate with the returned changes. Inspect that owned configuration through research.candidate_dimensions; if its result is a navigation overview, read /detail/dimensions and relevant ordering fields from that output using evidence.read. Inspect the original execution_evidence supplied with its immutable references in evidence; do not reread supplied facts unnecessarily. Its execution owner remains mainline3-v2; the prepared model-session candidate has the same scientific scope. Finally call research.capability_report with the owned prepared configuration, original execution evidence, a limited interpretation, and limitations; this stops the session. No simulation is granted and no duplicate run is needed. Do not claim autonomous topology invention, optimization gain, motor-realistic execution, causal diagnosis or research superiority. Reach, holding position, holding speed and timing are separate facts. Available false criteria mean failed, not unavailable. All tools use direct native business fields, no outer envelope. Use the registered schemas and exact references. No paid stylistic rewriting.')
            host.store.update_state(db,host.run_id,state)
    class BoundedAdapter(BusinessFieldsAdapter):
        def respond(self,payload,turn):
            if time.time()>=activity['execution_cutoff_unix']:raise ValueError('V2_DELIVERY_RESERVE_REACHED')
            return super().respond(payload,turn)
    adapter=BoundedAdapter();host.resume()
    _no_secrets(native_configuration())
    load_credential(Path.home()/'.codex/.env')
    result=run_loop(host,adapter)
    atomic_json(OUT/'native_result.json',dict(status=result['status'],state=result['state']))
    return result


def bind_before_dispatch():
    """Finalize engineering before the first scientific dispatch; same grant."""
    from contextlib import closing
    import subprocess
    from tools.platform_tasks import compile_input
    host=Host(RUN,'mainline3-v2')
    with closing(host.store.connect(True)) as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('PRE_DISPATCH_BINDING_REQUIRES_ZERO_CALLS')
        raw=db.execute('SELECT snapshot FROM sessions WHERE run_id=?',(host.run_id,)).fetchone()[0]
    # A demonstrated pre-dispatch engineering serialization failure is repaired
    # from its exact saved snapshot; no calls or grants have been issued anew.
    old=read(OUT/'pre_dispatch_snapshot.json')['before'] if raw.startswith('{') else host.store.session(host.run_id)['snapshot']
    current=compile_input(old['input'],host.reg)
    assert current['instance_identity']==old['instance_identity']
    current.update(project_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)))
    atomic_json(OUT/'pre_dispatch_snapshot.json',dict(before=old,after=current,
        rule='Before any provider/scientific calls; same input, activity start, grant and cumulative ledger; only finalized engineering dependency snapshot'))
    with host.store.transaction() as db:
        reference=host.store.put(db,current)
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(reference.artifact_id,host.run_id))
        host.store.event(db,host.run_id,'engineering','pre_dispatch_binding',outputs=[host.store.put(db,dict(
            before_dependencies=old['dependencies'],after_dependencies=current['dependencies']))])
    elapsed=time.time()-STARTED_UNIX
    row,fresh=host.store.reserve(host.run_id,'engineering-initial',digest({'started':STARTED_UNIX}),host.actor,
        {**zero(),'wall_s':elapsed},kind='engineering')
    if fresh:host.store.complete(row,dict(request_id='engineering-initial',execution_id=row['execution_id'],
        caller=host.actor,tool_id='engineering.initial',tool_version='1.0.0',execution_status='completed',charged=zero()),
        output=dict(interval_s=elapsed,scope='Inspection, finite implementation, focused checks and code freeze'),elapsed=elapsed,kind='engineering')
    return host


def guard(host,tool):
    activity=read(OUT/'activity.json')
    if time.time()>=activity['execution_cutoff_unix']:raise ValueError('V2_DELIVERY_RESERVE_REACHED')
    from contextlib import closing
    with closing(host.store.connect(True)) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    if tool.startswith('analysis.') and sum(c['request_id'].startswith(('v2-T1-linear','v2-T1-metrics','v2-T1-endpoint','v2-T2-linear','v2-T2-metrics','v2-T2-endpoint','v2-T3-linear','v2-T3-metrics','v2-T3-endpoint')) for c in calls)>=32:
        raise ValueError('V2_MATHEMATICAL_OPERATION_CEILING')


def scientific_case(host,key):
    from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
    from tools.research_mainline3 import fixed_pipeline
    source=finite.catalog()['scientific_source'];template=finite.catalog()['templates'][key]
    protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in template['design']['components'] if c['kind']=='flexible_segment'},frequency_rad_s=[.1,1.,10.])
    target=EndpointTarget(position_m=source['task']['goal']['data']['target_m'],position_tolerance_m=.01,position_scale_m=.01)
    with host.store.transaction() as db:
        protocol_ref=plain(host.store.put(db,protocol));target_ref=plain(host.store.put(db,target))
    rows=[]
    def call(tool,args,request_id):
        guard(host,tool)
        receipt=invoke(host,tool,args,request_id=request_id)
        rows.append(receipt)
        atomic_json(OUT/(key+'_receipts.json'),rows)
        return receipt
    result=fixed_pipeline(host,changes={'template':key},protocol=protocol_ref,target=target_ref,
        execute_backend=True,executor=call,candidate_id='v2-'+key,request_prefix='v2-'+key)
    result['mode']='actual_host_execution'
    prepared=host.store.artifact(rows[0]['output'])
    acceptance=call('research.task_acceptance',dict(configuration=prepared['configuration'],
        evaluation=rows[5]['output'],profile=rows[6]['output']),'v2-'+key+'-acceptance')
    if acceptance.get('execution_status')!='completed':raise ValueError('V2_ACCEPTANCE_INCOMPLETE: '+str(acceptance))
    result['receipts']=rows;result['joint_acceptance']=host.store.artifact(acceptance['output'])['detail']
    atomic_json(OUT/(key+'_result.json'),result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','construct','start','bind','execute','native']);p.add_argument('--case',choices=['T1','T2','T3']);args=p.parse_args()
    freeze()
    if args.action=='freeze':print(json.dumps(read(OUT/'activity.json')));return
    if args.action=='construct':
        from tools.research_execution import prepare_execution_request
        from tools.parameter_catalog import effective_catalog
        value=configuration();records={}
        for key in finite.catalog()['templates']:
            prepared=prepare_execution_request(value,{'template':key},candidate_id='v2-'+key)
            inp=SessionInput.model_validate(prepared['candidate']['effective'])
            detail=finite.dimensions(inp)
            init=finite.semantic_initialization(inp.robot.structure.data,inp.policy.discretization.data,inp.policy.controller.parameters.data['recipe']['basis'])
            records[key]=dict(prepared=prepared,dimensions=detail,initialization=init)
            print(key,detail['dimensions'])
        atomic_json(OUT/'construction.json',records)
        atomic_json(OUT/'public_catalog.json',effective_catalog(value))
        return
    if args.action=='native':
        result=native_session();print(json.dumps(dict(status=result['status'],stop_reason=result['state'].get('stop_reason'))));return
    if args.action=='bind':bind_before_dispatch();return
    host=start()
    if args.action=='execute':
        if not args.case:p.error('--case required')
        result=scientific_case(host,args.case)
        print(json.dumps(dict(case=args.case,status=result['joint_acceptance']['status'])))


if __name__=='__main__':main()
