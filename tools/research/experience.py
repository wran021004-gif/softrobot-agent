"""Scoped Skills and Experience patterns; read receipts never grant science credit."""
from pathlib import Path
from copy import deepcopy
from tools.research.state import save,update,state,protected
from tools.state_io import read
ROOT=Path(__file__).resolve().parents[2]
import hashlib
import json
from tools.research.contracts import ExperienceQuery
from tools.platform_store import plain

PUBLIC_STATUS='public_procedural_guidance; generalization_unverified'
PRIVATE_STATUS='private_owner_authorized; generalization_unverified'
PATTERN_STATUS='public_decision_pattern; generalization_unverified'


def knowledge_type(entry):
    return 'skill' if entry['kind']=='procedure' else 'experience'


def freeze_study_entries(spec, index, policy=None):
    """Opt-in local manifest, confined to this Study's experience directory."""
    policy=plain(policy) if policy is not None else {}
    if policy.get('mode')=='off':return []
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
    return [row for row in rows if _permitted(row,policy,legacy=True)]


def _permitted(entry, policy, *, legacy=False):
    if entry['entry_id'] in policy.get('exclude_entry_ids',[]):return False
    if policy.get('include_entry_ids') is not None and entry['entry_id'] not in policy['include_entry_ids']:return False
    if policy.get('allowed_kinds') is not None and entry['kind'] not in policy['allowed_kinds']:return False
    if entry.get('benchmark_sensitive') and not policy.get('allow_benchmark_answers',False):return False
    if legacy:return True
    return ((entry['kind']=='procedure' and (entry['status']==PUBLIC_STATUS or
        entry.get('introduced_in')=='p3_knowledge_v1' and entry['status']=='reference_backed_scoped'))
        or (entry['kind']=='case' and entry['status']==PATTERN_STATUS and
            entry.get('introduced_in')=='knowledge_organization_v1' and not entry.get('benchmark_sensitive')
            and entry.get('disclosure')=='abstract_decision_pattern_only')
        or (entry['entry_id']=='phs2d-research-process' and entry['revision']=='1' and entry['kind']=='case'
            and entry['entry_id'] in (policy.get('include_entry_ids') or [])
            and entry['status']==PATTERN_STATUS and entry.get('introduced_in')=='phs2d_process_v1'
            and entry.get('disclosure')=='answer_isolated_expert_process' and not entry.get('benchmark_sensitive'))
        or (entry['kind'] in ('case','success_case') and entry.get('benchmark_sensitive')
            and policy.get('allow_benchmark_answers',False) and entry['status']=='reference_backed_scoped'))


def _index_rows():
    path=ROOT/'memory/diagnostic_index.json'
    return read(path).get('entries',[]) if path.is_file() else []


def freeze_knowledge(policy):
    """Freeze authorized metadata and optional short principles; no full bodies."""
    policy=plain(policy)
    if policy.get('mode')=='off':return dict(entries=[])
    rows=deepcopy([entry for entry in _index_rows() if _permitted(entry,policy)])
    if policy.get('delivery')=='compact_skill_v1':
        for row in rows:
            if row.get('introduced_in')=='phs2d_process_v1':
                value=json.loads((ROOT/row['path']).read_bytes())
                row['compact_process']=dict(steps=value['startup_process'],lessons=value['general_lessons'],
                    ownership=value['decision_ownership'])
            if knowledge_type(row)!='skill' or row.get('introduced_in')!='knowledge_organization_v1':continue
            body=(ROOT/row['path']).read_bytes();value=json.loads(body)
            row['compact_skill']=dict(principle=value['principle'][:280],
                when=value['problem_or_trigger'][:180],source_sha256=hashlib.sha256(body).hexdigest())
    return dict(entries=rows)


def knowledge_enabled(spec):
    return spec.get('knowledge',{}).get('mode','enabled')!='off'


def research_catalogue(host):
    """Short frozen entry identities; bodies and confirmed reads keep existing owners."""
    rows=entries(host)
    if not any(r.get('introduced_in')=='passive_research_v1' for r in rows):return None
    return [dict(entry_id=r['entry_id'],revision=r['revision'],
        knowledge_type=knowledge_type(r),summary=r.get('summary',''),
        read_query=dict(operation='read',entry_id=r['entry_id'],revision=r['revision'])) for r in rows]


def entries(host):
    spec=state(host)['spec']
    policy=spec.get('knowledge',{})
    if policy.get('mode')=='off':return []
    manifest=spec.get('knowledge_manifest')
    if manifest is not None:
        rows=deepcopy(manifest['entries'])
    else:
        # Frozen P6 Studies retain their historical catalogue; adding files must
        # not silently disclose new answers or reinterpret their experiments.
        rows=[r for r in _index_rows() if not r.get('introduced_in') or
            (r.get('introduced_in')=='p3_knowledge_v1' and 'knowledge' in spec)]
        if spec.get('capabilities'):
            rows=[r for r in rows if r['kind']=='procedure' and (r['status']==PUBLIC_STATUS or
                r.get('introduced_in')=='p3_knowledge_v1' and 'knowledge' in spec)]
        rows=[r for r in rows if _permitted(r,policy,legacy=True)]
    rows += [r for r in spec.get('study_experience_entries',[])
        if r['study_id']==spec['study_id'] and r['status']==PRIVATE_STATUS
        and (manifest is not None or _permitted(r,policy,legacy=True))]
    return rows


def retrieval_hint(host):
    s=state(host)
    if not knowledge_enabled(s['spec']) or s['spec'].get('rl_evaluation_source') or s.get('research_status')=='stopped' or protected(host):return None
    task=s['spec'].get('canonical_task',s['spec'].get('task',{}))
    family=task.get('family','') if isinstance(task,dict) else ''
    name=family.removeprefix('task.')
    if s['spec'].get('knowledge',{}).get('delivery')=='compact_skill_v1':
        phase=decision_phase(host)
        process=next((r for r in entries(host) if r.get('compact_process') and
            name in [r['task'],*r.get('applicable_tasks',[])]),None)
        if process and phase:
            delivered=hint_progress(host);key='process:'+process['entry_id']+'@'+process['revision']
            first=not any(key in r.get('summary_keys',[]) for r in delivered)
            relevant=phase['phase'] in ('initialization_failure_review','voluntary_stop')
            if first or relevant and not any(r['notice_id']==phase['notice_id'] for r in delivered):
                compact=process['compact_process']
                return dict(boundary='first_process' if first else phase['notice_id'],
                    expert_process=dict(key=key,ownership=compact['ownership'],
                        steps=compact['steps'] if first else [compact['steps'][0],compact['steps'][2]],
                        lessons=compact['lessons'] if first else [compact['lessons'][3],compact['lessons'][6]],
                        read_query=dict(operation='read',entry_id=process['entry_id'],revision=process['revision'])),
                    decision_reason=phase['reason'],
                    scope='Historical process, context only; no winning design, current scientific evidence or prescribed research direction. Delivery does not prove adoption.')
        rows=[r for r in entries(host) if r.get('compact_skill') and phase and
            phase['phase'] in r.get('applicable_triggers',[]) and
            (r['task']=='soft_robot_research' or name in [r['task'],*r.get('applicable_tasks',[])])]
        if not rows:return None
        # One relevant principle, delivered directly. Experience stays on demand.
        row=sorted(rows,key=lambda r:(r['task']!=name,r['entry_id']))[0]
        key='summary:'+row['entry_id']+'@'+row['revision']
        if any(key in r.get('summary_keys',[]) and r['notice_id']==phase['notice_id'] for r in hint_progress(host)):return None
        result=dict(skill=dict(key=key,principle=row['compact_skill']['principle'],when=row['compact_skill']['when']),
            boundary=phase['notice_id'],scope='Current model facts prevail; cross-task transfer unverified. Summary only; full Skill/Experience via experience_retrieve.')
        if phase['phase']=='finite_search_structural_review':
            experience=next((r for r in entries(host) if r['entry_id']=='experience-structure-readaptation' and
                knowledge_type(r)=='experience'),None)
            if experience:
                result['experience']=dict(summary=experience['summary'][:160],
                    read_query=dict(operation='read',entry_id=experience['entry_id'],revision=experience['revision']))
        return result
    from tools.research.evidence_policy import english_sources
    eligible=[r for r in entries(host) if not english_sources(s['spec']) or english_source_ready(r)]
    available=sorted({r['task'] for r in eligible})
    if not available:return None
    hint=dict(query=dict(operation='search',task=name) if name in available else dict(operation='search'), available_historical_tasks=available,
        study_private_entries=[dict(entry_id=r['entry_id'],revision=r['revision'],task=r['task'],
            read_query=dict(operation='read',entry_id=r['entry_id'],revision=r['revision']))
            for r in eligible if r['status']==PRIVATE_STATUS],
        scope='Optional Experience/Skill search then exact read; context only, never current Study evidence or permission. No bodies preloaded.')
    if 'knowledge_manifest' in s['spec']:
        latest={}
        for row in eligible:
            if not row.get('summary'):continue
            key=row['entry_id'];revision=lambda r:(r['revision'].isdigit(),int(r['revision']) if r['revision'].isdigit() else r['revision'])
            if key not in latest or revision(row)>revision(latest[key]):latest[key]=row
        def matches(row):return name in [row['task'],*row.get('applicable_tasks',[])]
        phase=decision_phase(host)
        choices=sorted(latest.values(),key=lambda r:(not (phase and phase['phase'] in r.get('applicable_triggers',[])),r['task']!=name,not matches(r),r['entry_id']))
        choices=[r for r in choices if matches(r)]
        # At most one per type when both are authorized. Never widen a manifest.
        types=('skill','experience') if phase and phase['phase']!='first_scientific_plan' else ('skill',)
        selected=[next((r for r in choices if knowledge_type(r)==t),None) for t in types]
        choices=[r for r in selected if r]
        if len(choices)==1 and not any(knowledge_type(r)=='experience' for r in latest.values()):
            choices += [r for r in latest.values() if matches(r) and r not in choices][:1]
        delivered=hint_progress(host)
        if phase and not any(r['notice_id']==phase['notice_id'] for r in delivered):
            hint['decision_notice']=dict(**phase,
                instruction='Before this decision, optionally read one or two relevant entries using the exact read_query. Check trigger and assumptions against current model facts, which take precedence. If used in a Plan, bind experience_disposition to the actual read and explain applicability, affected experiment and weakening observation in interpretation; receipt, declared adoption and observable decision influence are distinct.')
        hint['hints']=[dict(entry_id=r['entry_id'],revision=r['revision'],knowledge_type=knowledge_type(r),method=r['summary'][:200],
            task=r['task'],scope='context_only; cross-task generalization unverified',
            read_query=dict(operation='read',entry_id=r['entry_id'],revision=r['revision'])) for r in choices] if hint.get('decision_notice') else []
        hint['confirmed_hint_deliveries']=delivered[-3:]
        hint['query']=dict(operation='search',task=name) if choices else dict(operation='search')
    return hint


def decision_phase(host):
    """Finite reminders at scientific boundaries; no new action or STOP gate."""
    s=state(host);route_ref=s.get('pilot',{}).get('tool_route')
    route=host.store.artifact(route_ref) if route_ref else {}
    results=s.get('analysis_results',[])
    if route.get('tool')=='research_plan' and route.get('action')=='stop':
        boundary=results[-1]['artifact_id'] if results else 'empty'
        return dict(phase='voluntary_stop',notice_id='stop:'+boundary,
            reason='Review untried legal experiments, evidence for declining them and uncertainty in Plan interpretation. A nonpassing witness or an iteration/callback cap alone does not establish scientific closure.')
    if not s.get('plans'):
        return dict(phase='first_scientific_plan',notice_id='first_plan',
            reason='Check model/input semantics and how condition-specific experiments can distinguish competing explanations before selecting the first research plan.')
    from tools.research.research_context import initialization_review
    review=initialization_review(host)
    if review and review['repeated_block'] and review['failed_attempts'] in (2,4,8,16,32,64):
        return dict(phase='initialization_failure_review',notice_id='initialization:'+str(review['failed_attempts']),
            reason='Repeated unloaded qualification failures span the observed candidates. Compare competing geometry, unilateral-branch and numerical explanations; a low-value local route does not exhaust other legal mathematical methods. Main chooses whether to switch.')
    from tools.research.evidence_views import native_search_summary
    failed=[]
    for ref in results:
        if not host.store.artifact(ref,paths=('native_dynamics.optimization',)).get('native_dynamics',{}).get('optimization'):
            continue
        a=host.store.artifact(ref);search=native_search_summary(a,ref)
        if search and not search['model_predicates_passed']:failed.append(a)
    if len(failed)>=2:
        def structure(a):
            ref=a['candidate']
            return (host.store.artifact(ref).get('physical_design_identity',ref['artifact_id'])
                if s['spec'].get('knowledge',{}).get('delivery')=='compact_skill_v1' else ref['artifact_id'])
        candidate=structure(failed[-1])
        if s.get('plans'):
            selected=(host.store.artifact(s['plans'][-1]).get('original_plan',{}).get('decision') or {}).get('selected_candidate')
            if selected:candidate=structure(dict(candidate=selected))
        if sum(structure(a)==candidate for a in failed)>=2:
            return dict(phase='finite_search_structural_review',notice_id='structural_review:'+candidate,
                reason='Repeated finite control searches have not established acceptance. Before changing structure, distinguish solver limits, unresolved parameter effects and missing matched-condition controls; reinitialize/reoptimize every required condition after a change.')
    return None


def hint_progress(host):
    """Confirmed wires prove hint delivery, never a read or understanding."""
    def collect():
        events=host.store.events(host.run_id)
        confirmed={e['request_id'] for e in events if e['kind']=='r3_response' and
            200<=host.store.artifact(e['outputs'][0]).get('http_status',0)<300}
        rows=[];seen=set()
        for event in events:
            if event['kind']!='r3_request' or event['request_id'] not in confirmed:continue
            meta=host.store.artifact(event['outputs'][0]);wire=host.store.artifact(meta['request'])
            for message in wire.get('messages',[]):
                content=message.get('content')
                if not isinstance(content,str) or not content.startswith('CURRENT_RESEARCH_PACKET\n'):continue
                research=json.loads(content.split('\n',1)[1]).get('research',{})
                hint=(research.get('knowledge') or {}).get('access') or research.get('experience_guidance') or {}
                if hint.get('skill') or hint.get('expert_process'):
                    notice_id=hint['boundary'];skill=hint.get('skill') or hint['expert_process']
                    if notice_id in seen:continue
                    seen.add(notice_id)
                    rows.append(dict(notice_id=notice_id,request=event['outputs'][0],wire=meta['request'],
                        summary_keys=[skill['key']],summary=skill,
                        **(dict(experience_hint=hint['experience']) if hint.get('experience') else {}),
                        evidence_role='confirmed_expert_process_delivery_only' if hint.get('expert_process') else 'confirmed_skill_summary_delivery_only'))
                    continue
                notice=hint.get('decision_notice')
                if not notice or notice['notice_id'] in seen:continue
                seen.add(notice['notice_id'])
                rows.append(dict(notice_id=notice['notice_id'],phase=notice['phase'],request=event['outputs'][0],
                    wire=meta['request'],entries=[dict(entry_id=r['entry_id'],revision=r['revision']) for r in hint.get('hints',[])],
                    evidence_role='confirmed_hint_delivery_only'))
        return rows
    return host.store.snapshot_value(('knowledge_hint_deliveries',host.run_id),collect)


def english_source_ready(entry):
    origin=entry.get('language_origin') or {}
    return entry.get('authored_language')=='en' and (origin.get('kind')=='authored_english' or
        (origin.get('kind')=='reviewed_translation' and bool(origin.get('original_reference')) and bool(origin.get('reviewed_by'))))


def retrieve(host,query,*,reader='agent'):
    if not knowledge_enabled(state(host)['spec']):raise ValueError('KNOWLEDGE_DISABLED_BY_FROZEN_STUDY')
    q=ExperienceQuery.model_validate(query);rows=[]
    for entry in entries(host):
        from tools.research.evidence_policy import english_sources
        if q.operation=='search' and english_sources(state(host)['spec']) and not english_source_ready(entry):continue
        canonical=entry['entry_id']+'@'+entry['revision']
        if q.key is not None and q.key not in (entry.get('legacy_key'),entry['entry_id'],canonical):continue
        if q.entry_id is not None and q.entry_id!=entry['entry_id']:continue
        if q.revision is not None and q.revision!=entry['revision']:continue
        if q.knowledge_type is not None and q.knowledge_type!=knowledge_type(entry):continue
        if any(getattr(q,name) is not None and getattr(q,name)!=entry[name]
            and getattr(q,name) not in entry.get('applicable_'+name+'s',[])
            for name in ('task','structure','failure_type','version','kind')):continue
        source=ROOT/entry['path']
        if not source.is_file():
            if q.operation=='read':
                rows.append(dict(key=canonical,entry_id=entry['entry_id'],revision=entry['revision'],
                    status='source_unavailable',source_path=entry['path'],explanation='The historical guidance source is unavailable.'))
            continue
        content=None;body_hash=None
        if q.operation=='read':
            body=source.read_bytes()
            frozen_hash=entry.get('compact_skill',{}).get('source_sha256')
            if frozen_hash and hashlib.sha256(body).hexdigest()!=frozen_hash:
                raise ValueError('FROZEN_KNOWLEDGE_CONTENT_CHANGED: '+canonical)
            content=json.loads(body) if source.suffix=='.json' else body.decode('utf8')
            # Existing receipt identity only; never an admission/comparison gate.
            body_hash=hashlib.sha256(body).hexdigest()
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
        rows.append(dict(**{k:v for k,v in entry.items() if k!='content_sha256'},key=entry.get('legacy_key',canonical),exact_key=canonical,
            knowledge_type=knowledge_type(entry),
            **(dict(content_sha256=body_hash) if q.operation=='read' else {}),original_evidence_references=refs,
            read_query=dict(operation='read',entry_id=entry['entry_id'],revision=entry['revision']),
            content_role='research_trace' if entry['kind'] in ('case','success_case') else 'procedural_knowledge',
            applicability='Transfer diagnostic principles only after checking trigger and scope; historical task numbers and controls do not transfer. Cross-task validity is unverified.',
            historical_task_type=entry['task'], current_task_type=state(host)['spec'].get('canonical_task',{}).get('family'),
            **(dict(content=content) if q.operation=='read' else {})))
    if q.operation=='read' and len(rows)!=1:raise ValueError('EXACT_EXPERIENCE_READ_REQUIRES_ONE_ENTRY_AND_REVISION')
    matched=len(rows)
    if q.operation=='search' and q.limit is not None:rows=rows[:q.limit]
    record=dict(query=plain(q),results=rows,supplied_startup_context=False,
        matched_count=matched,
        evidence_role='context_only',
        reader=reader,scientific_evidence=False,scope='Historical decision pattern or conditional method; not current evidence or authorization. Do not transfer historical task values or controls. Cross-task validity is unverified.')
    if q.operation=='search':record['read_guidance']='Execute an entry read_query exactly; the retrieval receipt reference.artifact_id is not a Knowledge entry_id.'
    from tools.research.structure_intent import enabled as structure_enabled
    if structure_enabled(state(host)['spec']):
        record['filter_values']={name:sorted({r[name] for r in entries(host)}) for name in ('kind','task','structure','failure_type','version')}
        record['prior_read_progress']=read_progress(host)
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
    if not dispositions:return []
    from tools.research.object_choices import reference_choices
    aliases={ref['artifact_id']:name for name,ref in reference_choices(host,include_all=True).items()}
    reads={}
    for ref in state(host)['retrievals']:
        receipt=host.store.artifact(ref)
        if receipt['query']['operation']!='read' or len(receipt['results'])!=1:continue
        row=receipt['results'][0]
        if row.get('status')=='source_unavailable':continue
        binding=dict(read_receipt=ref,entry_id=row['entry_id'],revision=row['revision'],exact_key=row['exact_key'],
            content_sha256=row['content_sha256'],reader=receipt.get('reader','agent'))
        reads[ref['artifact_id']]=binding;reads[row['exact_key']]=binding
        if ref['artifact_id'] in aliases:reads[aliases[ref['artifact_id']]]=binding
    if state(host)['spec'].get('knowledge',{}).get('delivery')=='compact_skill_v1':
        for delivery in hint_progress(host):
            for key in delivery.get('summary_keys',[]):
                reads[key]=dict(summary_delivery=delivery['request'],entry_key=key,
                    source_kind='expert_process_summary' if key.startswith('process:') else 'skill_summary',full_read=False)
                if key.startswith('process:'):reads['summary:'+key.removeprefix('process:')]=reads[key]
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
    from tools.research.object_choices import main_projection
    deliveries,_=confirmed_tool_deliveries(host);provided=[]
    for contents in deliveries.values():
        for content in contents:
            try:value=json.loads(content)
            except (ValueError,TypeError):continue
            if isinstance(value,dict) and value.get('query',{}).get('operation')=='read':provided.append(value)
    return dict(reads=[dict(entry_id=key[0],revision=key[1],read_receipt=ref,
        tool_read_completed=True,body_delivered=any(value in (dict(reference=ref,**receipt),
            main_projection(host,dict(reference=ref,**receipt))) for value in provided))
        for key,(ref,receipt) in receipts.items()],
        scope='Main read receipts only; body_delivered requires exact feedback in a confirmed Provider request. No card bodies preloaded here; delivery proves neither understanding, adoption nor scientific evidence.')
