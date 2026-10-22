"""F3 engineering authorization/admission only; never chooses scientific actions."""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import httpx
from tools.research.config import ROOT, resolve
from tools.research.state import state, save, update, require_authorization, science_hashes, core_hashes
from tools.research.agent import load_credential, pending, received, record, decision_packet
from tools.research.core import prepare, bind
from tools.platform_host import Host
from tools.state_io import read, atomic_json, digest

APPROVAL=Path('C:/Users/gugugaga/.codex/attachments/1f5240bb-afd7-4cfa-a8c4-cd6eb88c6c0a/已粘贴的文本.txt')
PREFLIGHT=ROOT/'runs/f3-formal-environment.json'


def preflight():
    from tools.research.tool_readiness import probe
    runtime=read(ROOT/'configs/research/runtime_f3.json')
    for key,value in runtime['threads'].items():os.environ[key]=value
    os.environ['SOROSIM_ROOT']=read(ROOT/'evidence/f3_prestudy/sorosim_readiness.json')['environment']['SOROSIM_ROOT']
    if Path(sys.executable).resolve()!=Path(runtime['research_python']).resolve():raise ValueError('WRONG_RESEARCH_INTERPRETER')
    load_credential(Path(runtime['credentials_reference']).expanduser())
    provider=runtime['provider']
    response=httpx.get(provider['base_url'].rstrip('/')+'/models',
        headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},timeout=30,follow_redirects=False)
    response.raise_for_status()
    if provider['model'] not in [m['id'] for m in response.json()['data']]:raise ValueError('PROVIDER_MODEL_UNAVAILABLE')
    import cvxpy
    versions={p:metadata.version(p) for p in ('strands-agents','strands-harness','numpy','scipy','casadi','mujoco','cvxpy','clarabel')}
    rl=json.loads(subprocess.check_output([runtime['rl_python'],'-c',
        'import sys,json,stable_baselines3,torch,mujoco;print(json.dumps(dict(python=sys.executable,ppo=stable_baselines3.__version__,torch=torch.__version__,mujoco=mujoco.__version__)))'],text=True))
    readiness=probe()
    value=dict(status=readiness['status'],python=sys.executable,rl=rl,versions=versions,
        solvers=cvxpy.installed_solvers(),provider=dict(endpoint=provider['base_url'],model=provider['model'],authentication_checked=True),
        runtime_identity=digest(runtime),science_hashes=science_hashes(),core_hashes=core_hashes(),
        dependency_locks={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('requirements-s130-t3.txt','requirements-strands-mainline5.lock')},
        threads=runtime['threads'],sorosim=readiness,cwd=str(ROOT),disk_free_bytes=shutil.disk_usage(ROOT).free,
        scientific_experiments=0,provider_completions=0)
    atomic_json(PREFLIGHT,value)
    if value['status']!='ready' or 'CLARABEL' not in value['solvers']:raise ValueError('ENVIRONMENT_NOT_READY')
    return dict(status=value['status'],python=sys.executable,versions=versions,preflight=str(PREFLIGHT))


def authorize():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('CLEAN_FINAL_CHECKOUT_REQUIRED')
    spec=resolve(ROOT/'configs/research/.f3_pending_final.json')
    env=read(PREFLIGHT)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','rev-parse','origin/integration/f3-prestudy'],cwd=ROOT,text=True).strip()
    if commit!=remote or commit!=spec['base_commit']:raise ValueError('PUSHED_FINAL_BINDING_REQUIRED')
    if read(ROOT/'runs/f3-final-binding.json')['resolved_identity']!=spec['resolved_identity']:raise ValueError('FINAL_RESOLVE_IDENTITY_MISMATCH')
    if env['status']!='ready' or env['science_hashes']!=science_hashes() or env['core_hashes']!=core_hashes():
        raise ValueError('CURRENT_ENVIRONMENT_ADMISSION_REQUIRED')
    if env['runtime_identity']!=digest(spec['runtime']):raise ValueError('RUNTIME_CHANGED')
    if (ROOT/'runs/research'/spec['study_id']).exists():raise ValueError('PRESERVE_EXISTING_STUDY_USE_RUN_ID')
    if spec['supplied_evidence'] or any(spec['research_decisions'][k] for k in ('history','mathematics','control_seeds')):
        raise ValueError('NO_HISTORICAL_EXPERIMENTAL_FEEDBACK_REQUIRED')
    approved=dict(provider_requests=128,protected_provider_requests=8,public_operations=400,
        protected_public_operations=20,physical_launches=80,mathematical_evaluations=64,offline_nlp=2,bdf_replays=2)
    if (any(spec['budgets'][k]!=v for k,v in approved.items()) or spec['nmpc_limits']['executions']!=6
            or any(spec['rl_limits'][k]!=v for k,v in dict(training_stages=2,training_actions=262144,
                actions_per_trial=262144,evaluation_episodes=2).items())):
        raise ValueError('EXPLICIT_USER_COUNTS_REQUIRED')
    scope=dict(study_id=spec['study_id'],code_commit=commit,resolved_identity=spec['resolved_identity'],
        canonical_task_identity=spec['canonical_task_identity'],family_space_identity=spec['family_space_identity'],
        budgets=spec['budgets'],nmpc_limits=spec['nmpc_limits'],rl_limits=spec['rl_limits'],
        provider=spec['runtime']['provider'],data_scope=['Frozen task and public engineering priors',
            'Current Study Agent decisions, candidates, controls, scoped experimental results and reports'],
        execution_scopes=['registered mathematics','SoRoSim MATLAB R2024a','MuJoCo','NMPC','PPO'],
        independent_reporter=True,live_session_handoff_authorized=True,
        known_risk='Historical F3.0 failed_semantic_admission accepted by user; historical result unchanged',
        source_user_request=dict(path=str(APPROVAL),sha256=hashlib.sha256(APPROVAL.read_bytes()).hexdigest()),
        environment_identity=digest(env))
    h=prepare(ROOT/'configs/research/.f3_pending_final.json')
    ref=save(h,dict(user_approval=True,scope=scope,scope_identity=digest(scope)), 'formal_study_authorization')
    require_authorization(h)
    save(h,env,'formal_environment_admission')
    bind(h,specification=spec)
    return dict(study_id=h.run_id,freeze=state(h)['freeze'],approval=ref,
        public_prior_manifest=state(h)['public_prior_manifest'],resolved_identity=spec['resolved_identity'])


async def admit(h,*,boundary='completed_invocation'):
    from tools.research.agent import build_harness, LiveBoundary, live_model_class
    from tools.research.session_handoff import safe_boundary, trusted_history, schemas, snapshot_files
    from tools.research.reporter import current_reports
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    require_authorization(h);s=state(h);events=h.store.events(h.run_id)
    from tests.research.f3_provider_recovery import loss_disposition
    if pending(h) or s['pilot'].get('unconsumed_response'):raise ValueError('UNSETTLED_PROVIDER')
    requests=[(e,h.store.artifact(e['outputs'][0])) for e in events if e['kind']=='r3_request']
    confirmed=[];losses=[]
    for e,v in requests:
        reception=received(h,e['request_id']);row=h.store.lookup(h.run_id,e['request_id'])
        if reception is None:
            loss=loss_disposition(h,row)
            if loss is None:raise ValueError('REAL_SETTLED_RESPONSE_REQUIRED')
            losses.append(dict(sequence=e['sequence'],request_id=e['request_id'],disposition=loss))
            continue
        if not row['receipt'] or not reception or reception['http_status']!=200:raise ValueError('REAL_SETTLED_RESPONSE_REQUIRED')
        confirmed.append((e,v))
    main=[(e,v) for e,v in confirmed if v['purpose']=='conversation']
    if len(main)<2:raise ValueError('REAL_CONTINUOUS_MAIN_REQUESTS_REQUIRED')
    if losses and main[-1][0]['sequence']<=losses[-1]['sequence']:
        raise ValueError('NEW_REAL_MAIN_RESPONSE_AFTER_AUTHORIZED_LOSS_REQUIRED')
    uses=[h.store.artifact(e['outputs'][0])['tool_use'] for e in events if e['kind']=='model_original_tool_request']
    feedback=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_tool_feedback']
    if not uses or {u['toolUseId'] for u in uses}!={v['tool_use']['toolUseId'] for v in feedback}:
        raise ValueError('PAIRED_REAL_NATIVE_TOOLS_REQUIRED')
    if not any(v['result']['status']=='success' for v in feedback):raise ValueError('LEGAL_REAL_NATIVE_TOOL_REQUIRED')
    if any(v['interpretation_status']=='deferred' for _,v in current_reports(h)):raise ValueError('REPORTER_NOT_DELIVERED')
    wires=[h.store.artifact(v['request']) for _,v in main]
    if not any(m['role']=='tool' for w in wires[1:] for m in w['messages']):raise ValueError('REAL_TOOL_FEEDBACK_IN_NEXT_REQUEST_REQUIRED')
    definitions=[t['function'] for t in wires[-1].get('tools',[])]
    def no_execution(*a,**kw):raise AssertionError('ADMISSION_IS_READ_ONLY')
    tools=[PythonAgentTool(d['name'],dict(name=d['name'],description=d.get('description',''),
        inputSchema={'json':d['parameters']}),no_execution) for d in definitions if d['name']!='retrieve_context']
    transport=LiveBoundary(h,httpx.MockTransport(no_execution))
    try:
        agent=build_harness(h,transport=transport,api_key='no-send-admission',instructions=s['spec']['execution_instructions'],
            model_class=live_model_class(transport),tool_executor=SequentialToolExecutor(),research_tools=tools,
            configuration_path=h.store.root/'admission_configuration.json',session_directory=h.store.root/'framework_sessions')
        if not await agent._session_manager.restore_snapshot(agent):raise ValueError('SDK_SNAPSHOT_MISSING')
        # retrieve_context is SDK-owned; restore its exact last advertised schema.
        for d in definitions:
            agent.tool_registry.registry[d['name']].tool_spec=dict(name=d['name'],description=d.get('description',''),inputSchema={'json':d['parameters']})
        if boundary=='request_feedback':
            from tools.research.session_handoff import request_feedback_boundary
            await request_feedback_boundary(h,agent)
        trusted_history(h,agent)
        with h.store.connect(True) as db:safe_boundary(h,state(h),db,agent.messages,boundary=boundary)
        packet=decision_packet(h)
        proof=dict(real_requests=[e['request_id'] for e,_ in requests],tool_ids=[u['toolUseId'] for u in uses],
            authorized_response_losses=losses,
            sdk_history_identity=digest(agent.messages),tool_schemas=schemas(agent),
            snapshot_files=snapshot_files(h.store.root/'framework_sessions',s['pilot']['framework_session_id']),
            l0_identity=digest(packet),independently_restored=True,boundary_kind=boundary,
            scope='Real current-Study continuity plus explicit user handoff authorization; request-feedback timing additionally requested on 2026-10-23')
        with h.store.transaction() as db:
            current=h.store.session(h.run_id,db)['state']
            if current!=s:raise ValueError('ADMISSION_STATE_CHANGED')
            ref=h.store.put(db,proof);current['pilot'].update(session_handoff_live_admitted=True,live_admission_reference=dict(artifact_id=ref.artifact_id),session_handoff_boundary=boundary)
            h.store.update_state(db,h.run_id,current)
            h.store.event(db,h.run_id,'session_handoff_live_admission','admitted',outputs=[ref])
        return dict(study_id=h.run_id,live_admitted=True,proof=dict(artifact_id=ref.artifact_id))
    finally:await transport.aclose()


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['preflight','authorize','admit']);p.add_argument('--run-id');a=p.parse_args()
    if a.command=='preflight':value=preflight()
    elif a.command=='authorize':value=authorize()
    else:
        if not a.run_id:p.error('--run-id required')
        value=asyncio.run(admit(Host(ROOT/'runs/research'/a.run_id,a.run_id,actor='unified-research')))
    print(json.dumps(value))


if __name__=='__main__':main()
