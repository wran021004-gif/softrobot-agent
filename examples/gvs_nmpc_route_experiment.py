"""Prepare and run one bounded real-provider Route capability-use experiment."""
import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(name,'1')
from tools.state_io import atomic_json,read
from tools.platform_host import Host
from tools.platform_store import Store,plain
from extensions.tendon_family.gvs_profile import profile_input
from extensions.tendon_family.route import create,view


def route_input(run_id,offline=False):
    from tools.platform_config import load
    inp=profile_input(run_id);p=inp['policy'];config=load('configs/deepseek.yaml')
    p['model']=dict(adapter='offline' if offline else 'deepseek',model=config['model'],
        base_url=config['base_url'],thinking=config['thinking'],max_tokens=config['max_tokens'],
        timeout_s=config['timeout_s'],context_bytes=150000,max_turns=24)
    p['budget'].update(model_calls=24,tool_calls=60,backend_solves=1,wall_s=7200.)
    p['allowed_tools']=[]
    p['tool_bindings']={k:'1.0.0' for k in ('route.advance','route.inspect','simulation.run',
        'evaluation.run','evidence.read','session.control','skills.search','control.profile_describe','control.profile_report')}
    p['route']=dict(contract='family.route_policy',version='1.0.0',data=dict(
        source='User authorized one fresh original-task capability-use experiment, with historical scoped development skill evidence.',
        combinations={'validated_gvs_nmpc':{k:p[k] for k in ('dynamics_model','backend','controller')}},max_trials=1,
        guidance='Complete a fresh execution of the original reach task using the available applicable control capability, inspect the resulting evaluation and report, and deliver the outcome with evidence, including settling and computational limitations. Historical evidence is prior evidence only. One fresh backend execution is authorized for this session.'))
    return inp


def prepare(root,source):
    if (root/'workflow.json').exists():
        state=read(root/'workflow.json');return Host(root,state['run_id'])
    identity='gvs-live-'+uuid4().hex[:12]
    store=Store(root)
    store.create(dict(project_id=identity,grant_id=identity,
        authorization_source='Attached user request: bounded genuine DeepSeek capability-use experiment; one primary backend execution, project ceiling two only for justified infrastructure retry; scoped development skill import. No human skill approval.',
        budget=dict(model_calls=24,tool_calls=60,backend_solves=2,worker_calls=0,wall_s=7200.)))
    inp=route_input(identity);create(root,inp);host=Host(root,identity)
    from tools.platform_skills import import_skill_history
    imported=import_skill_history(host,source,read(source/'workflow.json')['run_id'])
    context=host.context()
    from tools.platform_models import payload_for,DeepSeekAdapter
    payload=payload_for(host,DeepSeekAdapter())
    state=dict(run_id=identity,interpreter=sys.executable,source_history=imported,
        model=inp['policy']['model'],threads={k:os.environ[k] for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
        context_bytes=len(json.dumps(payload).encode()),
        delivered_skills=[dict(reference=s['skill_id']+'@'+str(s['version']),status=s['status'],
            scope=s.get('scope_assessment'),human_approval=s['human_approval']) for s in context['skills']],
        reservation_analysis=dict(project_wall_s=7200,session_wall_s=7200,tool_reservation_s=inp['policy']['timeout_s'],
            parent_route_preflight_reservation_s=0,anticipated_nested_execution_charge_s=1800,
            post_execution_report_reservation_s=inp['policy']['timeout_s'],
            note='Route preflight reserves zero wall; completed Route and child elapsed times are both charged. 7200 s leaves space for 1800 s cheap-tool reservations after the expected ~900 s simulation.'))
    atomic_json(root/'input.json',inp);atomic_json(root/'workflow.json',state)
    atomic_json(root/'prepared_context.json',context)
    print('Prepared '+identity+'; scoped skills: '+str(len(context['skills']))+'; no provider/backend calls.',flush=True)
    return host


def load_credential(path):
    if not os.environ.get('DEEPSEEK_API_KEY') and path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and key.strip()=='DEEPSEEK_API_KEY':
                value=value.strip()
                if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
                os.environ['DEEPSEEK_API_KEY']=value
    if not os.environ.get('DEEPSEEK_API_KEY'):raise ValueError('MODEL_KEY_MISSING')
    print('Required provider credential is present.',flush=True)


def inspect(host):
    out=view(host);store=host.store;events=store.events(host.run_id)
    actions=[];deliveries=[];responses=[]
    for event in events:
        if event['kind']=='context_delivery':
            payload=store.artifact(event['inputs'][0]);ctx=json.loads(payload['messages'][-1]['content'])
            deliveries.append(dict(request_id=event['request_id'],payload=event['inputs'][0],
                skills=[s['skill_id'] for s in ctx.get('skills',[])],
                control_profiles=ctx['route']['control_profiles'],
                fresh_report=(ctx['route'].get('selected_summary') or {}).get('profile_report'),
                incumbent_report=(ctx['route'].get('incumbent') or {}).get('profile_report')))
        if event['kind']=='model_raw_response':
            raw=store.artifact(event['outputs'][0])['raw']
            responses.append(dict(request_id=event['request_id'],reference=event['outputs'][0],
                model=raw.get('model'),provider_id=raw.get('id'),usage=raw.get('usage')))
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    for row in calls:
        if row['run_id']==host.run_id and row['caller']=='model-transport' and row['receipt']:
            receipt=json.loads(row['receipt'])
            decision=store.artifact(receipt['output']) if receipt.get('output') else None
            actions.append(dict(request_id=row['request_id'],receipt=receipt,decision=decision))
    final=out['route']['final']
    summary=(final or {}).get('profile_report_summary')
    audit=dict(run_id=host.run_id,provider_responses=responses,context_deliveries=deliveries,
        actions=actions,counts=out['counts'],project_usage=store.remaining(),session_usage=out['usage'],
        tool_calls=sum(json.loads(r['charged'])['tool_calls'] for r in calls),
        real_model_requests=sum(json.loads(r['charged'])['model_calls'] for r in calls),
        backend_executions=sum(json.loads(r['charged'])['backend_solves'] for r in calls),
        stop_reason=out['stop_reason'],status=out['status'],final=final,
        actual_provider_response_received=bool(responses),
        skill_delivered=any(d['skills'] for d in deliveries),
        fresh_report_delivered=any(d['fresh_report'] or d['incumbent_report'] for d in deliveries),
        provider_authored_delivery=(final or {}).get('stop_reason') if (final or {}).get('explicit_delivery') else None)
    atomic_json(store.root/'route_status.json',out);atomic_json(store.root/'behavior_audit.json',audit)
    if summary:
        atomic_json(store.root/'summary.json',summary)
        from extensions.tendon_family.gvs_reporting import markdown
        (store.root/'report.md').write_text(markdown(summary),encoding='utf8')
    print(json.dumps({k:audit[k] for k in ('status','real_model_requests','tool_calls','backend_executions',
        'actual_provider_response_received','skill_delivered','fresh_report_delivered','stop_reason')},indent=2),flush=True)
    return audit


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run','inspect'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path,default=ROOT/'runs/stage316_public_profile_20260927')
    parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env')
    args=parser.parse_args();root=args.output.resolve()
    if args.action=='inspect':host=Host(root,read(root/'workflow.json')['run_id']);inspect(host)
    else:
        host=prepare(root,args.source.resolve())
        if args.action=='run':
            load_credential(args.credential_file)
            print('Starting real provider Route loop; at most one primary backend execution.',flush=True)
            host.run()
            inspect(host)
