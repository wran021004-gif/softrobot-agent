"""Preserve actual delivered context, separately from optional typed retrieval.

This indexes original packets and native resource references without modifying
them or equating availability with a read. No research API is imported.
"""
import csv,gzip,hashlib,json,sqlite3,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def aid(r):return r.get('artifact_id') if isinstance(r,dict) else None
def csvout(p,rs):
 fields=list(dict.fromkeys(k for r in rs for k in r)) or ['task_id','condition','status']
 with p.open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else '' if v is None else v for k,v in r.items()} for r in rs)
exposure=[];access=[];raw=[]
for p in sorted((R/'episode_manifests').glob('*/*.json')):
 m=load(p);folder=R/m['source_episode'];dbpath=folder/'STORE/platform.sqlite'
 with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
  db.execute('PRAGMA query_only=ON');s=json.loads(db.execute('select state from sessions where run_id=?',(m['episode_id'],)).fetchone()[0])
 refs={aid(r.get('reference')):r for r in s.get('authorized_full_case_context',[]) if aid(r.get('reference'))}
 m['resource_delivery_audit']=dict(public_prior_manifest=s.get('public_prior_manifest'),typed_retrieval_receipts=s.get('retrievals',[]),
  delivered_context_records=s.get('authorized_full_case_context',[]),context_exposure_recorded=bool(s.get('historical_success_case_exposure')),
  scope='Actual delivery records, distinct from typed Knowledge/Skill catalog access. Availability is not a read.')
 write(p,m)
 for name in ['DELIVERED_INITIAL_PACKET.json','PROMPT.json']:
  src=folder/name
  if src.exists():
   dest=R/'raw_archive/context_packets'/f'{m["task_id"]}_{m["condition"]}_{name}.gz';dest.parent.mkdir(parents=True,exist_ok=True)
   with src.open('rb') as inp,dest.open('wb') as out,gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as z:shutil.copyfileobj(inp,z,1024*1024)
   raw.append(dict(task_id=m['task_id'],condition=m['condition'],source=str(src.relative_to(R)),archived=str(dest.relative_to(R)),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
 for ref,r in refs.items():exposure.append(dict(task_id=m['task_id'],condition=m['condition'],episode_id=m['episode_id'],reference=ref,kind=r.get('kind'),source=r.get('source'),source_sha256=r.get('source_sha256'),scope='native delivered context record; not proof of a separate exact read'))
 for n,line in enumerate((folder/'CORE_CALLS.jsonl').open(encoding='utf8'),1):
  c=json.loads(line);q=c['arguments'].get('query') or {};ref=aid(q.get('reference'))
  if c['tool'] in ['evidence_read','evidence_page'] and ref in refs:
   ev=c['arguments'].get('event') or {};access.append(dict(task_id=m['task_id'],condition=m['condition'],episode_id=m['episode_id'],resource_id=ref,revision=refs[ref].get('source_sha256'),
    resource_role='delivered_context',access=c['tool'],detail=q.get('view',q.get('pointer')),request_id=c['request_id'],timestamp=c.get('started_at'),transport_status=c.get('status'),
    read_returned_body=c.get('status')=='completed',trigger=ev.get('research_question'),hypothesis=ev.get('hypothesis'),decision=ev.get('selected_action'),subsequent_research_change=ev.get('next_research_step'),
    actual_causal_influence='not_established',source_path=str((folder/'CORE_CALLS.jsonl').relative_to(R)),source_line=n))
csvout(R/'summary/CONTEXT_EXPOSURE.csv',exposure);csvout(R/'summary/CONTEXT_READS.csv',access);csvout(R/'raw_archive/CONTEXT_PACKET_MANIFEST.csv',raw)
with (R/'summary/RESOURCE_TO_ACTION.csv').open(encoding='utf8',newline='') as f:typed=[r for r in csv.DictReader(f) if r.get('resource_role')!='delivered_context']
csvout(R/'summary/RESOURCE_TO_ACTION.csv',typed+access)
write(R/'publication/CONTEXT_AUDIT.json',dict(delivered_records=len(exposure),explicit_context_reads=len(access),packet_copies=len(raw),scope='Typed retrieval and delivered context are reported separately; all actual exposure remains auditable.'))
print(json.dumps(dict(delivered_records=len(exposure),explicit_context_reads=len(access),packet_copies=len(raw))))
