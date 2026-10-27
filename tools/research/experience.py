"""Curated procedural guidance; immutable read receipts never grant science credit."""
from pathlib import Path
from tools.research.state import save,update,state,protected
from tools.state_io import read
ROOT=Path(__file__).resolve().parents[2]
import hashlib
from tools.research.contracts import ExperienceQuery
from tools.platform_store import plain

PUBLIC_STATUS='public_procedural_guidance; generalization_unverified'


def entries(host):
    rows=read(ROOT/'memory/diagnostic_index.json')['entries']
    if state(host)['spec'].get('capabilities'):
        rows=[r for r in rows if r['kind']=='procedure' and r['status']==PUBLIC_STATUS]
    return rows


def retrieval_hint(host):
    s=state(host)
    if s['spec'].get('rl_evaluation_source') or s.get('research_status')=='stopped' or protected(host):return None
    task=s['spec'].get('canonical_task',s['spec'].get('task',{}))
    family=task.get('family','') if isinstance(task,dict) else ''
    name=family.removeprefix('task.')
    if not any(r['task']==name for r in entries(host)):return None
    return dict(query=dict(operation='search',task=name),
        scope='Optional experience_retrieve search then exact read; procedural guidance only, never current Study evidence or permission to act. research_investigate may request experience_queries alongside saved evidence. No cases preloaded.')


def retrieve(host,query,*,reader='agent'):
    q=ExperienceQuery.model_validate(query);rows=[]
    for entry in entries(host):
        canonical=entry['entry_id']+'@'+entry['revision']
        if q.key is not None and q.key not in (entry.get('legacy_key'),entry['entry_id'],canonical):continue
        if q.entry_id is not None and q.entry_id!=entry['entry_id']:continue
        if q.revision is not None and q.revision!=entry['revision']:continue
        if any(getattr(q,name) is not None and getattr(q,name)!=entry[name]
            for name in ('task','structure','failure_type','version')):continue
        body=(ROOT/entry['path']).read_bytes()
        content=read(ROOT/entry['path']) if entry['path'].endswith('.json') else body.decode('utf8')
        refs=[]
        def walk(value):
            if isinstance(value,dict):
                if 'artifact_id' in value:refs.append(value)
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        if q.operation=='read':walk(content)
        rows.append(dict(**entry,key=entry.get('legacy_key',canonical),exact_key=canonical,
            content_sha256=hashlib.sha256(body).hexdigest(),original_evidence_references=refs,
            applicability='Check trigger, versions and tested scope; recommendation with generalization unverified',
            **(dict(content=content) if q.operation=='read' else {})))
    if q.operation=='read' and len(rows)!=1:raise ValueError('EXACT_EXPERIENCE_READ_REQUIRES_ONE_ENTRY_AND_REVISION')
    record=dict(query=plain(q),results=rows,supplied_startup_context=False,
        reader=reader,scientific_evidence=False,scope='Historical procedural guidance; no current acceptance, citation eligibility or scientific action authorization')
    ref=save(host,record,'actual_experience_retrieval')
    update(host,retrievals=[*state(host)['retrievals'],ref])
    return dict(reference=ref,**record)


def disposition_bindings(host,dispositions):
    reads={}
    for ref in state(host)['retrievals']:
        receipt=host.store.artifact(ref)
        if receipt['query']['operation']!='read' or len(receipt['results'])!=1:continue
        row=receipt['results'][0]
        binding=dict(read_receipt=ref,entry_id=row['entry_id'],revision=row['revision'],exact_key=row['exact_key'],
            content_sha256=row['content_sha256'],reader=receipt.get('reader','agent'))
        reads[ref['artifact_id']]=binding;reads[row['exact_key']]=binding
    if set(dispositions)-set(reads):raise ValueError('DISPOSITION_REQUIRES_EXACT_ACTUAL_READ; SEARCH_OR_STARTUP_TEXT_IS_INSUFFICIENT')
    return [dict(**reads[key],disposition=value) for key,value in dispositions.items()]
