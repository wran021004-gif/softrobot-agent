"""Explicit read-only payload accounting and outcome audit; no scientific executions."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from unittest.mock import Mock, patch
from tools.research.config import ROOT
from tools.research.agent import error_feedback
from tools.state_io import atomic_json, read


def size(value):return len(json.dumps(value,separators=(',',':'),ensure_ascii=False).encode('utf8'))


def payload(wire):
    """Partition canonical serialized bytes, never estimate provider token parts."""
    result=dict(fixed_instructions=0,tool_schema=size(wire.get('tools',[])),current_packet=0,
        history_model_messages=0,history_tool_results=0)
    for m in wire['messages']:
        if m['role']=='system':
            text=m['content'];mark='\nCURRENT_RESEARCH_PACKET\n'
            if mark in text:
                instruction,packet=text.split(mark,1)
                result['fixed_instructions']+=size(instruction)-2
                result['current_packet']+=size(packet)-2
            else:result['fixed_instructions']+=size(text)-2
        elif m['role']=='tool':result['history_tool_results']+=size(m)
        elif m['role']=='assistant':result['history_model_messages']+=size(m)
    result['other_protocol']=size(wire)-sum(result.values())
    assert result['other_protocol']>=0
    return dict(total_bytes=size(wire),serialized_bytes=result,token_parts=None,
        measurement='Canonical compact UTF-8 JSON serialization; excludes HTTP headers. Byte parts are not token parts.')


def offline():
    studies=[]
    for name in ('mirror','variant'):
        folder=ROOT/'evidence'/('s7_'+name)/'study';manifest=read(folder/'archive_manifest.json')
        with tarfile.open(folder/'immutable_artifacts.tar.gz') as tar:
            values={}
            for m in manifest['members']:
                body=tar.extractfile(m['name']).read()
                assert hashlib.sha256(body).hexdigest()==m['sha256']
                if m['media']=='application/json':values[m['sha256']]=json.loads(body)
        snapshot=next(values[m['sha256']] for m in manifest['members'] if m['name'].startswith('snapshot/'))
        get=lambda r:values[r['artifact_id']]
        requests=[];usage={};errors=[]
        for e in snapshot['events']:
            if e['kind']=='r3_request':
                wire=get(get(e['outputs'][0])['request'])
                requests.append(dict(request_id=e['request_id'],**payload(wire)))
            if e['kind']=='r3_response':
                value=get(e['outputs'][0])
                if value.get('usage'):usage[e['request_id']]=value['usage']
            if e['kind']=='model_original_tool_feedback':
                v=get(e['outputs'][0]);old=v['result']
                if old.get('status')!='error':continue
                text=''.join(c.get('text','') for c in old.get('content',[]))
                try:message=json.loads(text).get('message',text)
                except ValueError:message=text
                with patch('tools.research.agent.state',return_value={}),patch('tools.research.agent.record',return_value=e['outputs'][0]):
                    new=error_feedback(Mock(),v['tool_use'],ValueError(message),{})
                errors.append(dict(original_feedback=e['outputs'][0],old_bytes=len(text.encode()),
                    new_bytes=size(new),new_feedback=new,method='Offline rejection formatter replay; original Store/archive unchanged'))
        studies.append(dict(study='s7_'+name,requests=requests,provider_usage=usage,errors=errors,
            immutable_members_verified=len(manifest['members'])))
    return dict(studies=studies,provider_requests=0,new_physics=0,
        limitation='S7 saved requests are historical reference. Error formatter comparison does not establish full-session token savings or decision equivalence.')


def live(host,destination):
    from tools.research.state import state
    from tests.research.s6_audit import audit
    from tests.research.s7_audit import verify_package
    from tools.research.control_correction import task_measure
    from tools.research_tasks import task_adapter
    from tools.research.feedback import task_gap
    s=state(host);summary=audit(host,destination)
    verified=verify_package(Path(destination)/'study/design_package.json')
    physical=[]
    for ref in s.get('physical_replays',[]):
        value=host.store.artifact(ref);cfg=host.store.artifact(value['candidate'])['configuration']
        source=host.store.artifact(value['source_reference']);raw=host.store.artifact(value['raw_reference'])
        if task_gap(value)['valid_complete']:
            from tools.research.control_correction import task_outputs
            adapter=task_adapter(cfg);limits=adapter.ranking_limits()
            measured=task_measure(task_outputs(raw),cfg['task']['goal']['data']['target_m'],adapter.holding_start_s(),
                limits['holding_max_error_m'],limits['holding_max_speed_m_s'],limits['terminal_error_m'])
            assert abs(measured['normalized_gap']-task_gap(value)['normalized_gap'])<1e-10
            assert raw['tendon_order']==source['trajectory']['tendon_order']
            for sample,requested in zip(raw['samples'][1:],source['trajectory']['tensions_n']):
                assert all(abs(a-b)<1e-12 for a,b in zip(sample['actual_tension_n'],requested))
            physical.append(dict(reference=ref,measured=measured))
    events=host.store.events(host.run_id);requests=[];usage={};feedback=[]
    for e in events:
        if e['kind']=='r3_request':
            wire=host.store.artifact(host.store.artifact(e['outputs'][0])['request'])
            requests.append(dict(request_id=e['request_id'],**payload(wire)))
        elif e['kind']=='r3_response':
            value=host.store.artifact(e['outputs'][0])
            if value.get('usage'):usage[e['request_id']]=value['usage']
        elif e['kind']=='model_original_tool_feedback':feedback.append(host.store.artifact(e['outputs'][0]))
    with host.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    selected_index=next((i for i,r in enumerate(s.get('physical_replays',[])) if r==s.get('selected')),None)
    if selected_index is not None:assert selected_index==len(s['physical_replays'])-1
    atomic_json(Path(destination)/'independent_audit.json',dict(package=verified,physical=physical,requests=requests,
        provider_usage=usage,tool_error_count=sum(v['result']['status']=='error' for v in feedback),
        tool_calls=len(feedback),searches=[host.store.artifact(r) for r in s.get('control_search_results',[])],
        selected_last_physical=selected_index is not None,pending=s['pending'],new_physical_launches=0))
    return summary


def verify_searches(host):
    """Reconstruct every stored trial without executing physics or optimization."""
    import numpy as np
    from tools.research.state import state
    from tools.research.contracts import ControlSearchRequest
    from tools.research.control_correction import corrected_tensions
    from tools.research.physical_replay import initialize_schedule
    s=state(host);plans=[];checks=[]
    for ref in s['plans']:
        p=host.store.artifact(ref)['original_plan']
        if p['action']=='control_search':plans.append(ControlSearchRequest.model_validate(p['control_search']))
    assert len(plans)==len(s.get('control_search_results',[]))
    for q,ref in zip(plans,s.get('control_search_results',[])):
        result=host.store.artifact(ref);starts={}
        for i,item in enumerate([q,*q.additional_starts]):
            cfg=host.store.artifact(item.candidate)['configuration'];source=host.store.artifact(item.source)
            if item.adaptation_from:source=initialize_schedule(cfg,source,item.adaptation_from)
            tr=source['trajectory'];limits={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
            starts[str(i)+'-'+item.source.artifact_id]=(tr,[limits[c] for c in tr['tendon_order']])
        rows=result['candidates'];new_fd=0
        for row in rows:
            tr,limits=starts[row['start']];x=np.asarray(row['coefficients_n']);selected=row['active_coefficients']
            inactive=[i for i in range(len(x)) if i not in selected]
            assert np.all(x[inactive]==0)
            expected=corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],q.settings.knots_s,x,limits,q.settings.correction_window_s)
            applied=host.store.artifact(row['source'])['trajectory']['tensions_n']
            assert np.allclose(expected,applied,rtol=0,atol=1e-12)
            if q.settings.correction_window_s:
                a,b=q.settings.correction_window_s;t=np.asarray(tr['times_s'][:-1]);outside=(t<a)|(t>b)
                np.testing.assert_array_equal(expected[outside],np.asarray(tr['tensions_n'])[outside])
            if row['label']=='finite_difference' and not row['cache_hit']:new_fd+=1
        assert result['finite_difference_evaluations']==sum(r['label']=='finite_difference' for r in rows)
        checks.append(dict(reference=ref,active_coefficients=result['active_coefficients'],search_dimension=result['search_dimension'],
            starts=result['start_count'],callbacks=len(rows),new_physical=sum(not r['cache_hit'] for r in rows),
            cache_hits=sum(r['cache_hit'] for r in rows),finite_difference_callbacks=result['finite_difference_evaluations'],
            new_finite_difference_physical=new_fd,all_trial_inputs_reconstructed=True,inactive_coefficients_exact_zero=True,
            window_exterior_unchanged=True,stop_reason=result['stop_reason']))
    with host.store.connect(True) as db:
        assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    assert s['pending'] is None
    return dict(study_id=host.run_id,searches=checks,all_receipts_settled=True,pending=None,new_physical_launches=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--offline',type=Path);p.add_argument('--run-id');p.add_argument('--destination',type=Path)
    args=p.parse_args()
    if args.offline:atomic_json(args.offline,offline())
    if args.run_id:
        from tools.platform_host import Host
        live(Host(ROOT/'runs/research'/args.run_id,args.run_id,actor='unified-research'),args.destination)
