"""Fresh bounded SoRoMoX pilot; accepted Strands/Host/Store boundaries."""
from pathlib import Path
from copy import deepcopy
import argparse
import asyncio
import json
import os
import subprocess
import time
from schemas.platform import ProjectConfig
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero
from tools.research_execution import invoke
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT

ACTIVITY = 'soromox-pilot-20261010'
RUN = ROOT/'runs'/ACTIVITY
OUT = ROOT/'evidence/soromox_pilot_20261010'
STARTED = 1791607429.
LIMITS = dict(model_calls=4, tool_calls=32, backend_solves=2, worker_calls=0, wall_s=28800.)
TOOLS = {name: '1.0.0' for name in ('math.soromox_describe', 'math.soromox_solve', 'math.soromox_replay', 'evidence.read')}


def configuration():
    from tools.research_v2 import native_configuration
    from tools.design_optimization import resolved_input
    from schemas.design_optimization import DesignOptimizationProblem
    spec = read(ROOT/'examples/soromox/case_A.json')
    source = DesignOptimizationProblem.model_validate(spec['physical_source'])
    base = native_configuration(ACTIVITY)
    base['policy'].update(budget=LIMITS, allowed_tools=[], tool_bindings=TOOLS,
        operation_allowances={name: dict(timeout_s=960., reserve_s=30.) for name in TOOLS})
    base['policy']['model'].update(max_turns=4)
    values = dict(segment_count=2, proximal_tendons=3, distal_tendons=3, lengths_m=[.16, .11],
        material='baseline', section_scale=1., routing_scale=1., pretension_n=.2,
        holding_tip_speed_weight=.05, terminal_tip_speed_weight=.1)
    return resolved_input(source, values, ACTIVITY, base['policy'])


def host():
    return Host(RUN, ACTIVITY, actor='soromox-pilot')


def prepare():
    h = host()
    if h.store.db.exists():
        return h
    h.store.create(ProjectConfig(project_id=ACTIVITY, grant_id=ACTIVITY+'-authorized',
        authorization_source='User /goal attachment a72147c4-ec94-437b-bda6-ee1d63dc3520/pasted-text-1.txt',
        budget=LIMITS, exclusive_resources={'provider_request': 1, 'backend.family_mujoco': 1}))
    h.create(configuration()); h.resume()
    with h.store.transaction() as db:
        state = h.store.session(ACTIVITY, db)['state']
        state.update(soromox_started_unix=STARTED, soromox_cutoff_unix=STARTED+27000.,
            soromox_numerical_s=0., soromox_python='D:/softrobot-agent/.soromox-env/python.exe')
        cfg = h.store.session(ACTIVITY, db)['snapshot']['input']
        state['pilot'] = dict(activity_id=ACTIVITY, provider=cfg['policy']['model'], framework_session_id=ACTIVITY,
            live_model_requests=0, started_unix=STARTED, request_deadline_unix=STARTED+27000.)
        h.store.update_state(db, ACTIVITY, state)
    atomic_json(RUN/'activity.json', dict(activity_id=ACTIVITY, started_unix=STARTED, limits=LIMITS,
        numerical_limit_s=7200., delivery_reserve_s=1800., primary_nlp=4, additional_nlp=2,
        nlp_solve_limit_s=300., closed_loop_limit=2, closed_loop_launch_limit_s=1800.,
        base_commit='2d13dfcc6395e09b53f6241dac3cae24ee69abb8', historical_activity='sealed STOP; not accessed for dispatch'))
    return h


def bind(h):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('COMMIT_IMPLEMENTATION_BEFORE_BIND')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:
            raise ValueError('BIND_REQUIRES_ZERO_CALLS')
    old = h.store.session(ACTIVITY)['snapshot']; snapshot = compile_input(old['input'], h.reg)
    if snapshot['instance_identity'] != old['instance_identity']:
        raise ValueError('BIND_CHANGED_SCIENCE')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    snapshot.update(project_commit=commit, worktree_dirty=False)
    with h.store.transaction() as db:
        ref = h.store.put(db, snapshot); db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?', (ref.artifact_id, ACTIVITY))
        state = h.store.session(ACTIVITY, db)['state']; state['soromox_freeze'] = commit
        h.store.update_state(db, ACTIVITY, state); h.store.event(db, ACTIVITY, 'implementation_freeze', 'committed', outputs=[ref])
    atomic_json(RUN/'implementation_freeze.json', dict(commit=commit, dependencies=snapshot['dependencies']))


async def smoke(h):
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from tools.strands_pilot import build_harness
    from tools.strands_pilot_r3 import LiveBoundary, live_model_class, record, pending
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex'/'.env')
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise ValueError('DEEPSEEK_API_KEY_UNAVAILABLE')
    if pending(h):
        raise ValueError('UNCONFIRMED_PROVIDER_OUTCOME_NO_REPEAT')
    tools = []
    for tool_id in TOOLS:
        definition = h.reg.get(tool_id)
        def handler(use, _id=tool_id, **kwargs):
            receipt = invoke(h, _id, use['input'], request_id='soromox-native-'+use['toolUseId'])
            result = h.store.artifact(receipt['output']) if receipt.get('output') else None
            value = dict(receipt=receipt, feedback=result)
            record(h, 'soromox_native_feedback', value)
            return dict(toolUseId=use['toolUseId'], status='success' if receipt['execution_status']=='completed' else 'error',
                content=[dict(text=json.dumps(value))])
        tools.append(PythonAgentTool(tool_id.replace('.', '_'), dict(name=tool_id.replace('.', '_'),
            description=definition.description, inputSchema={'json':definition.input_schema.model_json_schema()}), handler))
    boundary = LiveBoundary(h, allow_truncated_response=True)
    instructions = ('Perform one bounded mathematical tool-use smoke. Call math_soromox_describe for case A, '
        'consume its actual structured feedback, then explain the next decision and admission limitation. '
        'You may read its immutable evidence. Do not request optimization after a failed model gate. '
        'Do not plan a new research campaign. Task success, mechanics equivalence, motor validation and global optimality are unestablished.')
    agent = build_harness(h, transport=boundary, api_key=os.environ['DEEPSEEK_API_KEY'], instructions=instructions,
        model_class=live_model_class(boundary), tool_executor=SequentialToolExecutor(), research_tools=tools,
        configuration_path=RUN/'framework_configuration.json', session_directory=RUN/'framework_sessions')
    started = time.perf_counter()
    try:
        result = await agent.invoke_async('Inspect the frozen mathematical model through its describe tool and explain what the returned evidence permits next.')
        record(h, 'soromox_live_smoke', dict(elapsed_s=time.perf_counter()-started, result=str(result)))
    except Exception as exc:
        record(h, 'soromox_live_smoke', dict(elapsed_s=time.perf_counter()-started,
            status='incomplete', exception_type=type(exc).__name__, message=str(exc),
            accounting=h.store.remaining()), status='stopped')
        raise
    finally:
        await boundary.aclose()


def export(h):
    import tarfile
    import io
    import hashlib
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    with h.store.connect(True) as db, tarfile.open(OUT/'immutable_artifacts.tar.gz', 'w:gz') as tar:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            suffix = '.json' if row['media']=='application/json' else '.bin'
            name = 'artifacts/'+row['id']+suffix
            info = tarfile.TarInfo(name); info.size = len(row['body']); info.mtime = int(STARTED)
            tar.addfile(info, io.BytesIO(row['body']))
            manifest.append(dict(name=name, sha256=row['id'], bytes=info.size, media=row['media']))
        for folder in (RUN/'framework_sessions',):
            for path in sorted(folder.rglob('*')):
                if not path.is_file(): continue
                body=path.read_bytes(); name='framework/'+path.relative_to(folder).as_posix()
                info=tarfile.TarInfo(name); info.size=len(body); info.mtime=int(STARTED)
                tar.addfile(info,io.BytesIO(body))
                manifest.append(dict(name=name,sha256=hashlib.sha256(body).hexdigest(),bytes=info.size,media='application/json'))
    state = h.store.session(ACTIVITY)['state']
    atomic_json(OUT/'activity.json', read(RUN/'activity.json'))
    freeze=read(RUN/'implementation_freeze.json')
    original=next(e['outputs'][0] for e in h.store.events(ACTIVITY) if e['kind']=='implementation_freeze')
    atomic_json(OUT/'implementation_freeze.json', dict(commit=freeze['commit'],
        dependency_identity=digest(freeze['dependencies']), snapshot_reference=original,
        dependencies_pointer='/dependencies', archive_member='artifacts/'+original['artifact_id']+'.json'))
    atomic_json(OUT/'events.json', h.store.events(ACTIVITY))
    atomic_json(OUT/'ledger.json', h.store.remaining())
    atomic_json(OUT/'state.json', state)
    if state.get('soromox_admission'):
        atomic_json(OUT/'admission.json', h.store.artifact(state['soromox_admission']))
    if state.get('soromox_native_followup'):
        atomic_json(OUT/'native_endpoint_followup.json', h.store.artifact(state['soromox_native_followup']))
    if (RUN/'reporting_repair.json').exists():
        atomic_json(OUT/'reporting_repair.json',read(RUN/'reporting_repair.json'))
    atomic_json(OUT/'archive_manifest.json', dict(members=manifest,
        archive_sha256=hashlib.sha256((OUT/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    with h.store.connect(True) as db:
        calls = [dict(row) for row in db.execute('SELECT * FROM calls ORDER BY rowid')]
    atomic_json(OUT/'calls.json', calls)
    return dict(artifacts=len(manifest), elapsed_activity_s=time.time()-STARTED, ledger=h.store.remaining(),
        numerical_s=state['soromox_numerical_s'], nlp_solves=0, closed_loop_launches=0)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare','bind','check','smoke','export','status','stop'])
    args = parser.parse_args()
    h = prepare() if args.command=='prepare' else host()
    if args.command=='bind': bind(h)
    if args.command=='check':
        value = invoke(h, 'math.soromox_describe', {'case':'A'}, request_id='soromox-admission-v1')
        print(json.dumps(value)); return
    if args.command=='smoke': asyncio.run(smoke(h))
    if args.command=='stop':
        elapsed = time.time()-STARTED
        engineering = max(0., elapsed-h.store.remaining()['used']['wall_s'])
        row, fresh = h.store.reserve(ACTIVITY, 'pilot-engineering-closeout', digest({'started':STARTED}), h.actor,
            {**zero(), 'wall_s':engineering}, kind='engineering')
        if fresh:
            h.store.complete(row, dict(request_id=row['request_id'], execution_id=row['execution_id'], caller=h.actor,
                tool_id='engineering.soromox', tool_version='1.0.0', execution_status='completed', charged=zero()),
                dict(elapsed_activity_s=elapsed, engineering_and_uninstrumented_setup_s=engineering), elapsed=engineering)
        with h.store.transaction() as db:
            state = h.store.session(ACTIVITY, db)['state']
            state['soromox_decision'] = 'defer_adoption'; state['soromox_completed_unix'] = time.time()
            h.store.update_state(db, ACTIVITY, state, 'stopped')
            h.store.event(db, ACTIVITY, 'pilot_decision', 'STOP')
    if args.command=='export': print(json.dumps(export(h))); return
    print(json.dumps(dict(status=h.store.session(ACTIVITY)['status'], ledger=h.store.remaining())))


if __name__ == '__main__':
    main()
