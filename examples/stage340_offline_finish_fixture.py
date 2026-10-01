"""Disposable saved-fact finish fixture; never a live model-authored delivery."""
from copy import deepcopy
from pathlib import Path
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples.stage337_autonomous_design_experiment import fixture_call
from tools.platform_host import Host
from tools.platform_registry import dependency_closure
from tools.platform_store import Store,plain,encode
from tools.platform_models import payload_for,ReadableDeepSeekAdapter
from tools.state_io import atomic_json,read,digest


def run():
    source=ROOT/'runs/stage339_candidate_analysis_autonomous_20261001'
    root=ROOT/'runs/stage340_offline_finish'/uuid4().hex
    old=Store(source);store=Store(root)
    store.create(dict(project_id='stage340-finish-fixture',grant_id=uuid4().hex,
        authorization_source='User-authorized disposable saved-fact context/finish check; no provider or backend.',
        budget=dict(model_calls=0,tool_calls=4,backend_solves=0,worker_calls=0,wall_s=300.)))
    run_id=read(source/'workflow.json')['run_id'];host=Host(root,run_id)
    # Import immutable evidence and ownership metadata into an independent fixture grant.
    # No calls/charges or original session authorization are copied or resumed.
    with old.connect(True) as src,store.transaction() as dst:
        dst.executemany('INSERT OR IGNORE INTO artifacts VALUES (?,?,?)',
            [tuple(row) for row in src.execute('SELECT * FROM artifacts')])
        for row in src.execute('SELECT * FROM sessions'):
            saved=old.session(row['run_id']);snapshot=deepcopy(saved['snapshot'])
            snapshot['dependencies']=dependency_closure([host.reg.get(*key.rsplit('@',1))
                for key in snapshot['dependencies']],host.reg)
            snapshot['input']['policy']['model']['context_bytes']=200000
            snapshot['input_identity']=digest(snapshot['input'])
            ref=store.put(dst,snapshot);state=deepcopy(saved['state'])
            state.update(pending=None,stop_reason=None)
            dst.execute('INSERT INTO sessions VALUES (?,?,?,?)',(row['run_id'],ref.artifact_id,'running',encode(state)))
            (root/'sessions'/row['run_id']).mkdir(parents=True,exist_ok=True)
    payload=payload_for(host,ReadableDeepSeekAdapter());serialized=encode(payload).encode('utf8')
    atomic_json(root/'post_backend_payload.json',payload)
    overview=host.context()['route'];incumbent=overview['incumbent']
    route=store.session(run_id)['state']['route']
    node=next(n for n in route['nodes'] if n['node_id']==incumbent['node_id'])
    facts=incumbent['candidate_facts'];result=incumbent['factual_result']
    receipt,_=fixture_call(host,1000,'route.advance',dict(node_id='offline-only-finish',action='finish',
        evidence=[node['result']],reason='Offline fixture of saved failed reach facts; not a provider decision.',
        next_step='Stop the disposable fixture.',design_statement=facts,result_statement=result))
    assert receipt['execution_status']=='completed',receipt
    final=store.session(run_id)['state']['route']['final']
    assert final['candidate_facts']==facts and final['factual_result']==result
    used=store.remaining(run_id)['used']
    assert used['model_calls']==used['backend_solves']==0
    report=dict(status='passed',scripted_fixture_not_live_model_finish=True,fixture_root=str(root),
        saved_source=str(source),serialized_request_bytes=len(serialized),context_bytes=200000,
        headroom_bytes=200000-len(serialized),candidate_facts_preserved=True,result_facts_preserved=True,
        execution_ownership_preserved=final['factual_result']['execution_id']==result['execution_id'],
        analysis_status=overview['candidate_analysis_status'],receipt=receipt,usage=used)
    assert report['headroom_bytes']>0
    atomic_json(ROOT/'evidence/stage340_bounded_autonomous_20261001/context_finish_fixture.json',report)
    print(encode({k:v for k,v in report.items() if k not in ('analysis_status','receipt')}))
    return report


if __name__=='__main__':run()
