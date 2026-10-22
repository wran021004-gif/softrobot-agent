"""Final read-only audit/export through the existing research exporter."""
from collections import Counter
import hashlib
import json
import tarfile
import zipfile
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state, science_hashes, core_hashes
from tools.research.core import export
from tools.research.agent import pending, received
from tools.research.research_context import research_action_trace
from tools.research.reporter import current_reports, provider_usage
from tools.state_io import atomic_json, read, digest

h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
s=state(h);events=h.store.events(h.run_id);out=ROOT/'evidence/f3_formal'
if s['pending'] or pending(h) or s['pilot'].get('unconsumed_response'):
    raise ValueError('UNSETTLED_EXECUTION_BLOCKS_FINAL_EXPORT')
if s['research_status']!='stopped':raise ValueError('FINAL_EXPORT_REQUIRES_LEGAL_TERMINATION')
result=export(h)
requests=[]
for e in events:
    if e['kind']!='r3_request':continue
    meta=h.store.artifact(e['outputs'][0]);r=received(h,e['request_id'])
    requests.append(dict(sequence=e['sequence'],request_id=e['request_id'],execution_id=e['execution_id'],
        request_metadata=e['outputs'][0],**meta,response=r,
        receipt=json.loads(h.store.lookup(h.run_id,e['request_id'])['receipt'])))
approvals=[dict(reference=e['outputs'][0],value=h.store.artifact(e['outputs'][0]))
    for e in events if e['kind']=='formal_study_authorization']
handoffs=[dict(sequence=e['sequence'],status=e['status'],references=e['outputs'],
    values=[h.store.artifact(r) for r in e['outputs']]) for e in events
    if e['kind'] in ('session_handoff','session_handoff_live_admission')]
packets=[]
for e in events:
    if e['kind']!='model_decision_packet':continue
    p=h.store.artifact(e['outputs'][0]);r=p.get('research',{})
    packets.append(dict(sequence=e['sequence'],reference=e['outputs'][0],identity=digest(p),
        research_intent=r.get('research_intent'),latest_feedback=r.get('latest_scientific_feedback'),
        latest_reports=r.get('latest_reports'),budget=r.get('budget'),candidates=p.get('candidates'),
        available_research_actions=r.get('available_research_actions'),actions=r.get('actions')))
with h.store.connect(True) as db:
    owners=[r[0] for r in db.execute('SELECT run_id FROM sessions WHERE run_id!=?',(h.run_id,))]
workers=[dict(owner=owner,events=h.store.events(owner)) for owner in owners]
audit=dict(study_id=h.run_id,implementation=s['freeze'],resolved_identity=s['spec']['resolved_identity'],
    canonical_task_identity=s['spec']['canonical_task_identity'],family_space_identity=s['spec']['family_space_identity'],
    implementation_unchanged=science_hashes()==s['profile']['science_hashes'] and core_hashes()==s['core_hashes'],
    binding=read(ROOT/'runs/f3-final-binding.json'),authorization=approvals,
    public_prior_reference=s['public_prior_manifest'],public_prior_manifest=h.store.artifact(s['public_prior_manifest']),
    no_history=dict(supplied_evidence=s['spec']['supplied_evidence'],
        research_decisions={k:s['spec']['research_decisions'][k] for k in ('history','mathematics','control_seeds')},
        imported_history=s.get('research_history',[]),imported_mathematics=s.get('research_mathematics',[])),
    requests=requests,provider_usage=provider_usage(h),action_trace=research_action_trace(h,limit=None),
    provider_recovery=[dict(sequence=e['sequence'],kind=e['kind'],references=e['outputs'],
        values=[h.store.artifact(r) for r in e['outputs']]) for e in events
        if e['kind'] in ('provider_response_loss_authorization','provider_response_loss_disposition')],
    reports=[dict(reference=r,value=v) for r,v in current_reports(h)],decision_deliveries=packets,
    handoffs=handoffs,workers=workers,event_counts=dict(Counter(e['kind'] for e in events)),
    ledger=h.store.remaining(),nmpc_launches=s.get('nmpc_launches',0),
    mathematical_evaluations=s.get('mathematical_evaluations',0),status=s['research_status'],
    selected=s.get('selected'),final_disposition=s.get('final_disposition'),export=result)
atomic_json(out/'formal_audit.json',audit)
atomic_json(out/'public_prior_manifest.json',audit['public_prior_manifest'])
atomic_json(out/'events.json',events)
with tarfile.open(out/'immutable_artifacts.tar.gz','r:gz') as archive:
    for row in read(out/'archive_manifest.json')['members']:
        if hashlib.sha256(archive.extractfile(row['name']).read()).hexdigest()!=row['sha256']:
            raise ValueError('ARCHIVE_CONTENT_HASH_MISMATCH')
with zipfile.ZipFile(out/'native_sessions_and_workers.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for directory in ('framework_sessions','executions'):
        for p in sorted((h.store.root/directory).rglob('*')):
            if p.is_file():z.write(p,p.relative_to(h.store.root).as_posix())
    for pattern in ('f3_formal_*.py','f3-formal-*.stdout.json','f3-formal-*.stderr.log','f3-formal-live-admission.json'):
        for p in sorted((ROOT/'runs').glob(pattern)):
            z.write(p,'supervision/'+p.name)
atomic_json(out/'final_artifact_manifest.json',dict(files={p.name:dict(bytes=p.stat().st_size,
    sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file()
    and p.name!='final_artifact_manifest.json'},store=str(h.store.root),archive_contents_verified=True))
print(json.dumps(dict(study_id=h.run_id,status=s['research_status'],selected=s.get('selected'),
    final_disposition=s.get('final_disposition'),ledger=h.store.remaining(),files=len(list(out.iterdir())))))
