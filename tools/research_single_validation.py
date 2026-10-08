"""One explicitly authorized public investigation; default preparation is offline."""
import argparse
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4

from tools.context_assembly import _no_secrets, check_outgoing_request
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero, now, encode
from tools.research_execution import invoke
from tools.research_investigations import InvestigationDispatcher, InvestigationOrder
from tools.research_mainline3 import configuration
from tools.state_io import atomic_json, digest, read

ROOT = Path(__file__).resolve().parents[1]
BASE = '93ed0d846813300cac03bf5803acf24dfed46eb8'
SOURCE = 'runs/stage336_manual_20261001_090616/stage336_audit.json'
OLD = 'runs/mainline3-validation-769f832fdbf5-direct'
SCHEDULE = (30, 60, 90, 120, 150, 175, 205)
PROJECT = {**zero(), 'model_calls': 1, 'tool_calls': 9, 'wall_s': 240.}
NODE = {**zero(), 'model_calls': 1, 'tool_calls': 1, 'wall_s': 180.}
STOP = ['One provider attempt; no retry or protocol correction',
        'Only supplied prefetch; no additional reads or delegation',
        'Stop at terminal outcome, deadline, recipient/configuration drift or persistence failure',
        'Unknown retains reservation; old activities remain stopped']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_review():
    store = Store(ROOT / OLD)
    previous=read(ROOT/'evidence/research_single_validation_20261008/validation_manifest.json')
    prior_store=Store(ROOT/previous['store'])
    return dict(store_sha256=sha(store.db), ledger=store.remaining(),
        status=store.session('mainline3-direct')['status'],
        previous_single=dict(store_sha256=sha(prior_store.db),ledger=prior_store.remaining(),
            status=prior_store.session(previous['activity_id'])['status']),
        files={p.relative_to(ROOT).as_posix(): sha(p) for p in
               [*sorted((ROOT/'evidence/research_mainline3_validation_20261008').glob('*.json')),
                *sorted((ROOT/'evidence/research_single_validation_20261008').glob('*'))] if p.is_file()})


def stop(host, reason):
    with host.store.transaction() as db:
        state = host.store.session(host.run_id, db)['state']
        state['stop_reason'] = reason
        host.store.update_state(db, host.run_id, state, status='stopped')
        host.store.event(db, host.run_id, 'session', 'stopped',
                         outputs=[host.store.put(db, dict(reason=reason, timestamp=now()))])


def prepare(out):
    if out.exists():
        raise ValueError('FRESH_OUTPUT_REQUIRED')
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT)
    cfg = configuration()
    approved = read(ROOT/'evidence/research_mainline3_validation_20261008/frozen_configuration.json')['policy']['model']
    if cfg['policy']['model'] != approved or (approved['base_url'], approved['model']) != ('https://api.deepseek.com', 'deepseek-flash'):
        raise ValueError('APPROVED_PROVIDER_CONFIGURATION_DIFFERS')
    out.mkdir(parents=True)
    identity = 'mainline3-single-' + uuid4().hex[:12]
    cfg['run_id'] = identity
    tools = {k: '1.0.0' for k in ('research.investigate', 'research.investigation_status')}
    cfg['policy'].update(route=None, budget=PROJECT, allowed_tools=list(tools), tool_bindings=tools,
        timeout_s=180., operation_allowances={k: dict(reserve_s=5., timeout_s=30.) for k in tools})
    grant = dict(project_id=identity, grant_id=identity,
        authorization_source='User 2026-10-08 single real validation: approved DeepSeek endpoint/model; one saved page, one provider attempt, no retries/science; '+out.relative_to(ROOT).as_posix(),
        budget=PROJECT)
    atomic_json(out/'authorization.json', dict(project=grant, node_budget=NODE,
        public_operation_ceiling=8, shared_project_tool_ceiling=9,
        endpoint=approved['base_url'], model=approved['model'], provider_identity=digest(approved),
        data_scope='Non-secret scoped question, one saved sampled-settling page, necessary source-directory metadata, tool schemas and investigation context',
        forbidden='Secrets, unrelated data, other model calls, connectivity probes, scientific operations, Version 2',
        output_bytes=16384, node_timeout_s=180, activity_timeout_s=240, stop_conditions=STOP))
    store = Store(ROOT/'runs'/identity)
    store.create(grant)
    host = Host(store.root, identity)
    host.create(cfg)
    host.resume()
    original = read(ROOT/SOURCE)['execution']['factual_result']
    _no_secrets(original)
    with store.transaction() as db:
        ref = plain(store.put(db, original))
        state = store.session(identity, db)['state']
        inv_grant = dict(max_count=1, max_concurrency=1, allowed_tools=['evidence.read'], evidence=[ref],
            include_completed_reports=False, per_node_budget=NODE, total_budget=NODE)
        state['role_context'] = dict(investigation_grant=inv_grant)
        state['investigation_grant_identity'] = digest(inv_grant)
        store.update_state(db, identity, state)
        store.event(db, identity, 'single_validation_authorization', 'prepared', outputs=[store.put(db, grant)])
    order = plain(InvestigationOrder(investigation_id='single-saved-fact', role='investigator',
        question='Using ONLY the supplied sampled_settling page, briefly state whether the recorded sampled settling passed. Return 2-3 facts with exact source references, JSON pointers and values (including passed and one observed value/limit), then a short interpretation. This is historical sampled evidence, not a continuous-time guarantee or a causal diagnosis. Return investigation_return directly. No evidence query, child, disposition or further model turn is authorized. If insufficient, explicitly report unknowns.',
        evidence=[ref], queries=[dict(reference=ref, pointer='/sampled_settling', limit=20, byte_limit=2048)],
        budget=NODE, timeout_s=180, output_bytes=16384, stop_conditions=STOP))
    atomic_json(out/'order.json', order)
    atomic_json(out/'frozen_configuration.json', cfg)
    atomic_json(out/'historical_before.json', old_review())
    manifest = dict(activity_id=identity, store=store.root.relative_to(ROOT).as_posix(),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        configuration_identity=digest(cfg), provider_identity=digest(approved),
        source=dict(path=SOURCE, sha256=sha(ROOT/SOURCE), pointer='/execution/factual_result', reference=ref),
        relevant_files_sha256={p: sha(ROOT/p) for p in ('tools/research_single_validation.py',
            'tools/research_investigations.py','tools/model_transports/deepseek.py','tools/platform_models.py',
            'tools/platform_host.py','tools/platform_store.py','configs/deepseek.yaml')},
        order_identity=digest(order), schedule_seconds=list(SCHEDULE),
        permissions='Exactly one new node; no transfer/release of historical escrow',
        preparation_passed=False)
    atomic_json(out/'validation_manifest.json', manifest)
    try:
        _, wire, reads, measurement = InvestigationDispatcher(host).prepare(order)
        assert len(reads)==1 and reads[0]['page']['kind']=='content' and reads[0]['page']['next_offset'] is None
        assert wire['model']==approved['model']
        assert wire['tool_choice']=='auto' and wire.get('thinking')=={'type':approved['thinking']}
        assert wire.get('reasoning_effort')==approved.get('reasoning_effort')
        _no_secrets(wire)
        atomic_json(out/'prepared_request.json', wire)
        atomic_json(out/'preparation_gate.json', dict(passed=True, measurement=measurement,
            request_settings={k:wire.get(k) for k in ('model','thinking','reasoning_effort','tool_choice','max_tokens')},
            visible_reads=reads, prefetch_count=1, qualifying_followup_count=0,
            investigator_selected_followup='unverified; no such operation is authorized',
            local_length_check_is_provider_acceptance=False, provider_attempts=0))
        manifest['preparation_passed']=True
    except Exception as exc:
        atomic_json(out/'preparation_gate.json', dict(passed=False, stage='request_preparation',
            exception_type=type(exc).__name__, provider_attempts=0))
        raise
    finally:
        stop(host, 'PREPARED_ONLY_NO_PROVIDER_ATTEMPT')
        atomic_json(out/'validation_manifest.json', manifest)
    print(encode(dict(activity_id=identity, preparation_passed=True, output=str(out))))


def result(host, receipt):
    if receipt.get('execution_status')!='completed':
        return dict(status='public_operation_failed', receipt=receipt)
    return host.store.artifact(receipt['output'])


def owned_thread():
    return next((t for t in threading.enumerate() if t.name=='investigation-single-saved-fact'), None)


def collect(host, order, *, schedule=SCHEDULE, cutoff=235.):
    started=time.monotonic()
    receipts=[]
    receipt=invoke(host,'research.investigate',order,request_id='single-submit')
    receipts.append(receipt)
    outcome=result(host,receipt)
    for index, due in enumerate(schedule):
        if outcome['status'] not in ('pending','running'):break
        thread=owned_thread()
        if thread is not None:
            thread.join(max(0,min(due,cutoff)-(time.monotonic()-started)))
        if time.monotonic()-started>=cutoff:break
        receipt=invoke(host,'research.investigation_status',dict(investigation_id=order['investigation_id']),
            request_id='single-collect-'+str(index))
        receipts.append(receipt)
        outcome=result(host,receipt)
    thread=owned_thread()
    if outcome['status'] in ('pending','running') and thread is not None:
        thread.join(max(0,cutoff-(time.monotonic()-started)))
    thread=owned_thread()
    active=bool(thread and thread.is_alive())
    if outcome['status'] in ('pending','running'):
        host.store.mark_unknown(host.run_id,'investigation-'+order['investigation_id'])
        outcome=dict(status='unconfirmed',reason='No terminal public result within collection/activity ceiling; reservation retained')
    return dict(result=outcome,public_receipts=receipts,elapsed_s=time.monotonic()-started,
        thread_active_at_close=active,thread_completed_before_close=not active,
        provider_cancellation_confirmed=False,
        cleanup='Stopped activity; daemon thread may end at application exit; remote completion/billing not inferred' if active else 'Owned investigation thread finished before application close')


def execute(out, *, live=True, schedule=SCHEDULE, cutoff=235.):
    manifest=read(out/'validation_manifest.json')
    if (out/'launch.json').exists():raise ValueError('NO_REPEATED_LAUNCH')
    assert manifest['preparation_passed'] and read(out/'preparation_gate.json')['passed']
    cfg=read(out/'frozen_configuration.json');order=read(out/'order.json')
    assert digest(cfg)==manifest['configuration_identity'] and digest(order)==manifest['order_identity']
    assert digest(configuration()['policy']['model'])==manifest['provider_identity']
    assert all(sha(ROOT/p)==h for p,h in manifest['relevant_files_sha256'].items())
    assert sha(ROOT/SOURCE)==manifest['source']['sha256']
    assert old_review()==read(out/'historical_before.json')
    assert cfg['policy']['budget']==PROJECT and order['budget']==NODE
    host=Host(ROOT/manifest['store'],manifest['activity_id'])
    assert host.compatibility()['compatible']
    assert host.store.session(host.run_id)['status']=='stopped'
    assert not host.store.session(host.run_id)['state'].get('investigations')
    check_outgoing_request(read(out/'prepared_request.json'),cfg['policy']['model'],'research_decision')
    atomic_json(out/'launch.json',dict(timestamp=now(),mode='real_configured_deepseek' if live else 'deterministic_offline_substitute',
        ceiling=1,repeat_forbidden=True))
    started=time.monotonic()
    lifecycle=None
    try:
        if live:
            from examples.gvs_nmpc_route_experiment import load_credential
            load_credential(Path.home()/'.codex/.env')
        host.resume()
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state']
            grant=state['role_context']['investigation_grant']
            grant['deadline_unix']=time.time()+240.-(time.monotonic()-started)
            state['investigation_grant_identity']=digest(grant)
            host.store.update_state(db,host.run_id,state)
            host.store.event(db,host.run_id,'single_validation_authorization','activated',outputs=[host.store.put(db,grant)])
        lifecycle=collect(host,order,schedule=schedule,cutoff=max(0,cutoff-(time.monotonic()-started)))
        atomic_json(out/'application_lifecycle.json',lifecycle)
    except Exception as exc:
        atomic_json(out/'application_failure.json',dict(timestamp=now(),exception_type=type(exc).__name__,
            elapsed_s=time.monotonic()-started,provider_outcome='Consult original events; do not infer no send or billing'))
        raise
    finally:
        stop(host,'SINGLE_VALIDATION_TERMINAL_OR_CEILING_NO_MORE_WORK')
        export(out)
    print(encode(dict(status=lifecycle['result']['status'],public_calls=len(lifecycle['public_receipts']),
        elapsed_s=lifecycle['elapsed_s'],ledger=host.store.remaining())))


def export(out):
    manifest=read(out/'validation_manifest.json')
    store=Store(ROOT/manifest['store'])
    with closing(store.connect(True)) as db:
        session=store.session(manifest['activity_id'],db)
        calls=[]
        for item in db.execute('SELECT * FROM calls ORDER BY rowid'):
            row=dict(item)
            for key in ('reserved','charged','resources','receipt'):
                if row[key] is not None:row[key]=json.loads(row[key])
            calls.append(row)
        bundle=dict(project=store.config(db),snapshot=session['snapshot'],state=session['state'],
            session_status=session['status'],calls=calls,
            artifacts={r['id']:json.loads(r['body']) for r in db.execute('SELECT id,body FROM artifacts')},
            events=[json.loads(r['body']) for r in db.execute('SELECT body FROM events ORDER BY seq')])
    _no_secrets(bundle)
    atomic_json(out/'bundle.json',bundle)
    atomic_json(out/'ledger.json',store.remaining())
    historical=old_review()
    atomic_json(out/'historical_after.json',dict(unchanged=historical==read(out/'historical_before.json'),review=historical))
    nodes=bundle['state'].get('investigations',{})
    node=nodes.get('single-saved-fact',{})
    events=bundle['events']
    attempts=[e for e in events if e['kind']=='investigation_provider_attempt']
    wires=[bundle['artifacts'][e['outputs'][0]['artifact_id']]['payload'] for e in attempts]
    provider=bundle['snapshot']['input']['policy']['model']
    reads=[e for e in events if e['kind']=='investigator_read']
    first_attempt=next((i for i,e in enumerate(events) if e['kind']=='investigation_provider_attempt'),len(events))
    prefetch=[e for i,e in enumerate(events) if e['kind']=='investigator_read' and i<first_attempt and e['status']=='completed']
    followup=[e for i,e in enumerate(events) if e['kind']=='investigator_read' and i>first_attempt]
    tokens=[bundle['artifacts'][e['outputs'][0]['artifact_id']] for e in events if e['kind']=='investigation_token_accounting']
    public=[c for c in calls if c['caller']!='investigation-dispatcher']
    progress=node.get('progress',{})
    valid_report=store.artifact(node['result']) if node.get('result') else None
    gate=dict(version='single_validation_gate@1.0.0',source='bundle.json',bundle_identity=digest(bundle),
        recorded_attempts=len(attempts),public_operation_count=len(public),node_count=len(nodes),
        successful_prefetch_count=len(prefetch),
        followup_read_count=sum(e['status']=='completed' for e in followup),
        rejected_followup_count=sum(e['status']=='rejected' for e in followup),
        followup_capability='unverified; only initial prefetch authorized',
        principal_inspection_count=0,coordinated_capability='unverified',
        compatible_actual_requests=bool(wires) and all(w['tool_choice']=='auto' and
            w['model']==provider['model'] and w.get('thinking')=={'type':provider['thinking']} and
            w.get('reasoning_effort')==provider.get('reasoning_effort') for w in wires),
        limits_passed=len(attempts)<=1 and len(public)<=8 and len(nodes)<=1 and len(prefetch)<=1
            and not any(e['status']=='completed' for e in followup) and node.get('usage',zero())['tool_calls']<=1
            and store.remaining()['used']['tool_calls']<=9 and historical==read(out/'historical_before.json'),
        single_report_passed=node.get('status')=='completed' and progress.get('settlement_completed') is True
            and valid_report is not None and bool(valid_report.get('facts')),
        scope='Only this single public request. Formal exit/status does not establish all Mainline 3 gates.')
    atomic_json(out/'gate.json',gate)
    atomic_json(out/'delivery_report.json',dict(活动=manifest['activity_id'],结果=node.get('status','not_submitted'),
        已知状态=progress,失败记录=node.get('failure_record'),账本=store.remaining(),
        失败详情=store.artifact(node['failure_record']) if node.get('failure_record') else None,
        请求预留与结算=calls,供应商返回用量=tokens,供应商费用=None,
        原活动及预留未改变=historical==read(out/'historical_before.json'),
        本次门禁=gate,有效报告=valid_report,
        限制=['没有按需追读或协调调查验证；没有科学计算或机器人改善验证',
              '本地长度检查不证明服务端接收；错误类别不证明未计费',
              '历史两次请求具体原因、到达情况及供应商费用仍未知'],
        下一步建议=('单请求报告及结算完成后，可另行授权完整直接调查；需独立预算、门禁和停止条件，不自动启动协调或科学实验'
            if gate['single_report_passed'] else '按本次失败记录核对最小处理；若字段缺失则保持未知与预留，不重发。任何后续付费验证需新授权')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','execute','export'])
    parser.add_argument('directory',type=Path)
    args=parser.parse_args();out=args.directory.resolve()
    if not out.is_relative_to(ROOT/'evidence'):raise ValueError('TASK_EVIDENCE_DIRECTORY_REQUIRED')
    {'prepare':prepare,'execute':execute,'export':export}[args.action](out)


if __name__=='__main__':main()
