"""Curated procedural guidance; immutable read receipts never grant science credit."""
from pathlib import Path
from tools.research.state import save,update,state,protected
from tools.state_io import read
ROOT=Path(__file__).resolve().parents[2]
import hashlib
import json
from tools.research.contracts import ExperienceQuery
from tools.platform_store import plain

PUBLIC_STATUS='public_procedural_guidance; generalization_unverified'
PRIVATE_STATUS='private_owner_authorized; generalization_unverified'


def freeze_study_entries(spec, index):
    """Opt-in local manifest, confined to this Study's experience directory."""
    scope=(ROOT/'runs/research'/spec['study_id']/'experience').resolve()
    source=(ROOT/index).resolve()
    if source.parent!=scope or source.name!='index.json':
        raise ValueError('STUDY_EXPERIENCE_INDEX_OUTSIDE_OWNED_SCOPE')
    manifest=read(source)
    if manifest.get('study_id')!=spec['study_id'] or manifest.get('schema')!='study_private_experience_v1':
        raise ValueError('STUDY_PRIVATE_EXPERIENCE_MANIFEST_REQUIRED')
    rows=manifest['entries']
    for row in rows:
        target=(ROOT/row['path']).resolve()
        if (target.parent!=scope or target.suffix!='.md' or not target.is_file()
                or row['status']!=PRIVATE_STATUS or row['kind']!='case'
                or row['study_id']!=spec['study_id']):
            raise ValueError('STUDY_PRIVATE_EXPERIENCE_ENTRY_OUTSIDE_OWNED_SCOPE')
        for field in ('entry_id','revision','task','structure','failure_type','version'):
            if not isinstance(row[field],str) or not row[field]:
                raise ValueError('STUDY_PRIVATE_EXPERIENCE_METADATA_REQUIRED')
    if len({(r['entry_id'],r['revision']) for r in rows})!=len(rows):
        raise ValueError('DUPLICATE_STUDY_EXPERIENCE_ENTRY')
    return rows


def entries(host):
    path=ROOT/'memory/diagnostic_index.json'
    rows=read(path).get('entries',[]) if path.is_file() else []
    if state(host)['spec'].get('capabilities'):
        rows=[r for r in rows if r['kind']=='procedure' and r['status']==PUBLIC_STATUS]
    spec=state(host)['spec']
    rows += [r for r in spec.get('study_experience_entries',[])
        if r['study_id']==spec['study_id'] and r['status']==PRIVATE_STATUS]
    return rows


def retrieval_hint(host):
    s=state(host)
    if s['spec'].get('rl_evaluation_source') or s.get('research_status')=='stopped' or protected(host):return None
    task=s['spec'].get('canonical_task',s['spec'].get('task',{}))
    family=task.get('family','') if isinstance(task,dict) else ''
    name=family.removeprefix('task.')
    from tools.research.evidence_policy import english_sources
    eligible=[r for r in entries(host) if not english_sources(s['spec']) or english_source_ready(r)]
    available=sorted({r['task'] for r in eligible})
    if not available:return None
    return dict(query=dict(operation='search',task=name) if name in available else dict(operation='search'), available_historical_tasks=available,
        study_private_entries=[dict(entry_id=r['entry_id'],revision=r['revision'],task=r['task'],
            read_query=dict(operation='read',entry_id=r['entry_id'],revision=r['revision']))
            for r in eligible if r['status']==PRIVATE_STATUS],
        scope='Optional experience_retrieve search then exact read; procedural guidance only, never current Study evidence or permission to act. research_investigate may request experience_queries alongside saved evidence. No cases preloaded.')


def english_source_ready(entry):
    origin=entry.get('language_origin') or {}
    return entry.get('authored_language')=='en' and (origin.get('kind')=='authored_english' or
        (origin.get('kind')=='reviewed_translation' and bool(origin.get('original_reference')) and bool(origin.get('reviewed_by'))))


def retrieve(host,query,*,reader='agent'):
    q=ExperienceQuery.model_validate(query);rows=[]
    for entry in entries(host):
        from tools.research.evidence_policy import english_sources
        if q.operation=='search' and english_sources(state(host)['spec']) and not english_source_ready(entry):continue
        canonical=entry['entry_id']+'@'+entry['revision']
        if q.key is not None and q.key not in (entry.get('legacy_key'),entry['entry_id'],canonical):continue
        if q.entry_id is not None and q.entry_id!=entry['entry_id']:continue
        if q.revision is not None and q.revision!=entry['revision']:continue
        if any(getattr(q,name) is not None and getattr(q,name)!=entry[name]
            for name in ('task','structure','failure_type','version')):continue
        source=ROOT/entry['path']
        if not source.is_file():
            if q.operation=='read':
                rows.append(dict(key=canonical,entry_id=entry['entry_id'],revision=entry['revision'],
                    status='source_unavailable',source_path=entry['path'],explanation='The historical guidance source is unavailable.'))
            continue
        body=source.read_bytes()
        content=read(ROOT/entry['path']) if entry['path'].endswith('.json') else body.decode('utf8')
        from tools.research.evidence_policy import english_sources
        if q.operation=='read' and english_sources(state(host)['spec']):
            # No silent translation or claim that historical prose is a fresh
            # observation. The owner supplies a reviewed, referenced view.
            if entry.get('authored_language')!='en':
                raise ValueError('EXPERIENCE_REQUIRES_REVIEWED_ENGLISH_SOURCE: '+canonical)
            origin=entry.get('language_origin') or {}
            if origin.get('kind') not in ('authored_english','reviewed_translation'):
                raise ValueError('EXPERIENCE_ENGLISH_ORIGIN_REQUIRED: '+canonical)
            if origin['kind']=='reviewed_translation' and (not origin.get('original_reference') or not origin.get('reviewed_by')):
                raise ValueError('REVIEWED_ENGLISH_DERIVATION_REQUIRED')
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
            applicability='Transfer diagnostic principles only after checking trigger and scope; historical task numbers and controls do not transfer. Cross-task validity is unverified.',
            historical_task_type=entry['task'], current_task_type=state(host)['spec'].get('canonical_task',{}).get('family'),
            **(dict(content=content) if q.operation=='read' else {})))
    if q.operation=='read' and len(rows)!=1:raise ValueError('EXACT_EXPERIENCE_READ_REQUIRES_ONE_ENTRY_AND_REVISION')
    record=dict(query=plain(q),results=rows,supplied_startup_context=False,
        evidence_role='context_only',
        reader=reader,scientific_evidence=False,scope='Historical procedural guidance, not current Study scientific evidence; transfer analytical principles only, not historical task values or control results. Cross-task validity is unverified; no acceptance or action authorization')
    if q.operation=='search' and not rows:
        from tools.research.evidence_policy import english_sources
        eligible=[r for r in entries(host) if not english_sources(state(host)['spec']) or english_source_ready(r)]
        record['empty_search_recovery']=dict(available_task_tags=sorted({r['task'] for r in eligible}),
            search_query=dict(operation='search'),
            exact_reads=[dict(operation='read',entry_id=r['entry_id'],revision=r['revision']) for r in eligible[:8]],
            reason='Filters are exact metadata matches. Version and revision are distinct fields. Cross-task entries are context_only; applicability unverified.')
    ref=save(host,record,'actual_experience_retrieval')
    update(host,retrievals=[*state(host)['retrievals'],ref])
    return dict(reference=ref,**record)


def disposition_bindings(host,dispositions):
    reads={}
    for ref in state(host)['retrievals']:
        receipt=host.store.artifact(ref)
        if receipt['query']['operation']!='read' or len(receipt['results'])!=1:continue
        row=receipt['results'][0]
        if row.get('status')=='source_unavailable':continue
        binding=dict(read_receipt=ref,entry_id=row['entry_id'],revision=row['revision'],exact_key=row['exact_key'],
            content_sha256=row['content_sha256'],reader=receipt.get('reader','agent'))
        reads[ref['artifact_id']]=binding;reads[row['exact_key']]=binding
    if set(dispositions)-set(reads):raise ValueError('DISPOSITION_REQUIRES_EXACT_ACTUAL_READ; SEARCH_OR_STARTUP_TEXT_IS_INSUFFICIENT')
    return [dict(**reads[key],disposition=value) for key,value in dispositions.items()]


def read_progress(host):
    """Deduplicate Main's existing receipts; confirm exact delivery from saved wires."""
    from tools.research.research_context import confirmed_tool_deliveries
    receipts={}
    for ref in state(host)['retrievals']:
        receipt=host.store.artifact(ref)
        if (receipt.get('reader','agent')!='agent' or receipt['query']['operation']!='read'
                or len(receipt['results'])!=1):continue
        row=receipt['results'][0]
        if row.get('status')=='source_unavailable':continue
        receipts[(row['entry_id'],row['revision'])]=(ref,receipt)
    if not receipts:return None
    deliveries,_=confirmed_tool_deliveries(host);provided={}
    for contents in deliveries.values():
        for content in contents:
            try:value=json.loads(content)
            except (ValueError,TypeError):continue
            if isinstance(value,dict) and isinstance(value.get('reference'),dict) and value.get('query',{}).get('operation')=='read':
                provided[value['reference']['artifact_id']]=value
    return dict(reads=[dict(entry_id=key[0],revision=key[1],read_receipt=ref,
        tool_read_completed=True,body_delivered=provided.get(ref['artifact_id'])==dict(reference=ref,**receipt))
        for key,(ref,receipt) in receipts.items()],
        scope='Main read receipts only; body_delivered requires exact feedback in a confirmed Provider request. No card bodies preloaded here; delivery proves neither understanding, adoption nor scientific evidence.')
