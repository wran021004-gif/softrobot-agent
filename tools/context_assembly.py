"""Derived working views over durable evidence, never a new scientific catalog.

No provider, experiment, grant creation or credential loading occurs here. Both
purposes reuse bound_reporting and study_history identities. Every omission has
an original-document pointer; oversized required views fail before sending.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
from tools.state_io import atomic_json, digest, read
from tools.platform_store import plain, encode
from tools.bound_reporting import ledger, model_packet

VERSION = 'evidence_context_assembly@1.0.0'
ROOT = Path(__file__).resolve().parents[1]
INPUT_BUDGET = {'research_decision': 160000, 'final_report': 96000}
INTERACTION_RESERVE = 8192
ARCHIVE_FIELDS = {'protected_hashes', 'sha256_manifest', 'file_hashes', 'hashes', 'receipts',
                  'trajectory', 'trajectories', 'raw_trace', 'runtime_objects'}


def pointer_part(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def _no_secrets(value):
    # Credential loader is deliberately absent. Fail rather than archive secrets.
    if isinstance(value, dict):
        for k, v in value.items():
            if k.lower() in {'api_key', 'deepseek_api_key', 'password', 'access_token'}:
                raise ValueError('CONTEXT_SECRET_FIELD')
            if k.lower()=='authorization' and isinstance(v,str) and re.match(r'(?i)\s*(bearer|basic)\s+',v):
                raise ValueError('CONTEXT_SECRET_FIELD')
            _no_secrets(v)
    elif isinstance(value, list):
        for v in value: _no_secrets(v)


class EvidenceArchive:
    """Content-addressed snapshots and an explicit, scope-local read allowlist.

    Existing stores are read only, and must already be authorized by the caller.
    No directory traversal, arbitrary path reads, or discovery of other stores.
    """
    def __init__(self, directory, *, scope, stores=()):
        self.directory = Path(directory).resolve()
        if not self.directory.is_relative_to(ROOT):
            raise ValueError('CONTEXT_ARCHIVE_OUTSIDE_WORKSPACE')
        self.scope = deepcopy(scope)
        self.stores = tuple(stores)
        self.sources = {}

    def snapshot(self, value):
        _no_secrets(value)
        body = encode(value).encode('utf-8')
        ref = dict(artifact_id=hashlib.sha256(body).hexdigest(), media_type='application/json')
        path = self.directory / 'sources' / (ref['artifact_id'] + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temporary = path.with_suffix('.tmp'); temporary.write_bytes(body); temporary.replace(path)
        if path.read_bytes() != body: raise ValueError('CONTEXT_ARCHIVE_CHANGED')
        self.sources[ref['artifact_id']] = dict(reference=ref, path=path.relative_to(ROOT).as_posix(),
            verified=True, permission_scope=self.scope)
        return ref

    def register(self, reference):
        if reference['artifact_id'] in self.sources: return reference
        for store in self.stores:
            try: store.artifact(reference, raw=True)
            except ValueError: continue
            self.sources[reference['artifact_id']] = dict(reference=reference,
                store_root=store.root.relative_to(ROOT).as_posix(), verified=True,
                permission_scope=self.scope)
            return reference
        raise ValueError('CONTEXT_SOURCE_NOT_RETRIEVABLE: ' + reference['artifact_id'])

    def register_references(self, value):
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                self.register(value)
            else:
                for v in value.values(): self.register_references(v)
        elif isinstance(value, list):
            for v in value: self.register_references(v)

    def manifest(self):
        value = dict(version=VERSION, scope=self.scope,
            sources=[self.sources[k] for k in sorted(self.sources)])
        path = self.directory / 'manifests' / (digest(value) + '.json')
        if not path.exists(): atomic_json(path, value)
        if read(path) != value: raise ValueError('CONTEXT_MANIFEST_CHANGED')
        return path.relative_to(ROOT).as_posix()

    @classmethod
    def from_manifest(cls, path, *, scope, stores=()):
        """Reopen a durable read allowlist without discovering new permissions."""
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT) or path.parent.name!='manifests':
            raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
        value=read(path)
        if value['scope']!=scope or value['version']!=VERSION:
            raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
        if path.stem!=digest(value):raise ValueError('CONTEXT_MANIFEST_CHANGED')
        archive=cls(path.parent.parent,scope=scope,stores=stores)
        allowed={s.root.relative_to(ROOT).as_posix() for s in stores}
        for source in value['sources']:
            if source['permission_scope']!=scope:
                raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
            if 'store_root' in source and source['store_root'] not in allowed:
                raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
            if 'path' in source and not (ROOT/source['path']).resolve().is_relative_to(archive.directory):
                raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
            archive.sources[source['reference']['artifact_id']]=source
        return archive

    def retrieve(self, reference, *, pointer='', offset=0, limit=20, byte_limit=4096, binding=None):
        """Same original-pointer paging as evidence.read, without host mutations."""
        from schemas.platform_operations import ReadEvidence
        from tools.platform_tools import bounded_evidence_page
        source = self.sources.get(reference['artifact_id'])
        if not source or source['reference'] != reference:
            raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
        if 'path' in source:
            path = (ROOT / source['path']).resolve()
            if not path.is_relative_to(self.directory): raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != reference['artifact_id']:
                raise ValueError('CONTEXT_ARCHIVE_CHANGED')
            value = json.loads(raw)
        else:
            store = next((s for s in self.stores if s.root.relative_to(ROOT).as_posix() == source['store_root']), None)
            if store is None: raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
            value = store.artifact(reference)
        args = ReadEvidence(reference=reference, pointer=pointer, offset=offset, limit=limit, byte_limit=byte_limit)
        page = plain(bounded_evidence_page(value, args))
        return dict(page=page, binding=binding, units=(binding or {}).get('unit'),
            truncated=page['kind'] == 'overview' or page['next_offset'] is not None,
            continuation=(dict(reference=reference, pointer=pointer, offset=page['next_offset'],
                limit=limit, byte_limit=byte_limit) if page['next_offset'] is not None else None),
            child_pointers=page['content'] if page['kind'] == 'overview' else None,
            evidence_is_authority=False)


def _offload(value, reference, omissions, path=''):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            child_path = path + '/' + pointer_part(key)
            if key in ARCHIVE_FIELDS:
                omissions.append(dict(reason='Archive-only trace/receipt/hash metadata',
                    reference=reference, pointer=child_path))
                result[key + '_archive'] = dict(reference=reference, pointer=child_path)
            else: result[key] = _offload(child, reference, omissions, child_path)
        return result
    if isinstance(value, list):
        return [_offload(v, reference, omissions, path + '/' + str(i)) for i, v in enumerate(value)]
    return value


def _compact_ledger(bound):
    view=model_packet(bound)
    view['facts']={key:{k:f[k] for k in ('value','unit')} for key,f in bound['facts'].items()}
    view['binding_resolution']='Each executions row supplies execution/structure/scientific identities; facts[metric] selects the immutable fact ID and canonical value/unit. metric_sources resolve original sources. Full expanded ledger retained in archive.'
    return view


def _comparison_bindings(content, authority=None):
    result=[]
    for outcome in content.get('outcomes', []):
        comparisons={}
        for kind in ('baseline_comparison','source_comparison'):
            if kind not in outcome:continue
            c=outcome[kind]
            if 'relation' in c:
                # Joint acceptance comparisons carry a relation rather than the
                # legacy metric wrappers. Bind their subjects to the explicit
                # feedback source and retained-baseline authority.
                source=(content['source'] if kind=='source_comparison' else
                        authority['roles']['source_baseline'])
                baseline_id=source['execution_id']; candidate_id=outcome['candidate']['execution_id']
                classification=c['relation']
            else:
                baseline_id=c['baseline']['source']['execution_id']
                candidate_id=c['candidate']['source']['execution_id']; classification=c['classification']
            comparisons[kind]=dict(baseline_execution_id=baseline_id,
                candidate_execution_id=candidate_id,classification=classification,
                scope='Frozen campaign metric comparison; changing weights/structure does not isolate a cause')
        result.append(dict(candidate=outcome['candidate'],comparisons=comparisons))
    return result


def _research(packet, authority, archive):
    """Reuse reporting_summary/ledger; F aliases remain the current host catalog."""
    from tools.study_history import reporting_summary
    history = packet['history']
    rows = history['rows']
    if any(not r.get('scientific_configuration_identity') for r in rows):
        raise ValueError('SCIENTIFIC_REPORTING_IDENTITY_REQUIRED')
    # Explicit case membership, plus lineage/role anchors. No recency cutoff.
    required = set(packet.get('case', {}).get('evidence_execution_ids', []))
    required.update(c['execution_id'] for c in authority.get('roles', {}).values() if c and c.get('execution_id'))
    candidates = authority.get('comparison_execution_ids')
    if candidates is not None:
        allowed = set(candidates) | required
        rows = [r for r in rows if r['candidate'].get('execution_id') in allowed]
    else:
        # These are the caller's already scoped research_records, not all stores.
        allowed = {r['candidate'].get('execution_id') for r in rows}
    pairs = authority.get('replication_pairs', [])
    for a, b in pairs:
        if a not in allowed or b not in allowed: raise ValueError('CONTEXT_REPLICATION_LINEAGE_OMITTED')
    summary = reporting_summary(dict(history, rows=rows),
        new_execution_ids=authority.get('new_execution_ids', []), replication_pairs=pairs,
        selected=authority['roles'].get('selected_incumbent'), latest=authority['roles'].get('latest_attempt'),
        usage=packet['capabilities']['remaining'], stop=authority.get('stop', {}))
    summary['batch_count'] = packet.get('engineering_coverage', {}).get('completed_search_batches', 0)
    bound = ledger(summary)
    bound['structure_definitions'] = {r['structure_identity']:r.get('physical_structure',
        bound['structure_definitions'][r['structure_identity']]) for r in rows if r.get('metrics')}
    reduced = deepcopy(packet)
    reduced['history'] = dict(history, rows=[{k:deepcopy(r[k]) for k in ('candidate','status','configuration_identity')} |
        {k:deepcopy(r[k]) for k in ('case_id','seed','task_identity') if k in r} |
        ({k:deepcopy(r[k]) for k in ('structure_identity','scientific_configuration_identity','decisions','controller')} if not r.get('metrics') else {})
        for r in sorted(rows, key=lambda r:(r['candidate'].get('execution_id') or '', r['configuration_identity']))])
    # Sorting is presentation only; chronology and latest remain event-bound.
    reduced['bound_evidence'] = _compact_ledger(bound)
    if reduced.get('study',{}).get('m5_feedback'):
        m5=reduced['study']['m5_feedback']
        reduced['study']['m5_feedback']=dict(source=m5['source'],scope=m5['scope'],
            negative_findings='Retained prediction evidence supplies no screening authority, candidate exclusion, v8 adoption or compression-benefit claim.',
            complete_text=dict(reference=archive.snapshot(packet),pointer='/study/m5_feedback'))
    if reduced.get('study',{}).get('parameter_catalog'):
        catalog=reduced['study']['parameter_catalog']
        retained=('id','kind','meaning','type','unit','current_value','builder_domain',
            'experiment_granted_domain','effective_locations','operation','coupled_constraints',
            'study_permission','technical_support')
        catalog['parameters']=[{k:r[k] for k in retained if k in r} for r in catalog['parameters']]
        catalog['full_mutation_rebuild_reuse_evidence']=dict(reference=archive.snapshot(packet),pointer='/study/parameter_catalog')
    reduced['scientific_overlap'] = dict(new_execution_count=summary['new_execution_count'],
        novel_configuration_count=summary['novel_configuration_count'],
        previously_evaluated_count=summary['scientifically_previously_evaluated_count'],
        overlaps=summary['scientific_overlaps'],deliberate_replication_count=summary['replication_count'])
    if 'case' in reduced:
        reduced['case']['question_status'] = 'frozen_pre_experiment_background; consult recorded_replications for current evidence'
    feedback = reduced['current_feedback']
    feedback['content'] = dict(status=feedback['content'].get('status'),
        stop_reason=feedback['content'].get('stop_reason'),
        comparison_bindings=_comparison_bindings(packet['current_feedback']['content'],authority),
        evidence_coverage='Current exact F aliases below; complete feedback in archive')
    current_ref = feedback['reference']
    reduced['performed_batch_evidence'] = [r for r in reduced.get('performed_batch_evidence', [])
        if r['reference'] != current_ref]
    required_aliases=set(authority.get('required_aliases', []))
    def selected_aliases(aliases):
        selected={a:r for a,r in aliases.items() if a in required_aliases or
            ((('/metrics/' in r['pointer'] and '/source/' not in r['pointer'] and '/coverage/' not in r['pointer']) or
              ('/acceptance/' in r['pointer'] and r['pointer'].endswith(('/accepted','/passed','/status'))) or
              '/candidate_minus_baseline/' in r['pointer'] or r['pointer'].endswith(('/classification','/status','/stop_reason'))))}
        # Initial handoffs have no outcome wrapper; preserve that exact handoff.
        return selected or aliases
    feedback['aliases']=selected_aliases(feedback['aliases'])
    for r in reduced['performed_batch_evidence']:
        r['aliases']=selected_aliases(r['aliases'])
        source=archive.sources[r['reference']['artifact_id']]
        store=next(s for s in archive.stores if s.root.relative_to(ROOT).as_posix()==source['store_root'])
        r['comparison_bindings']=_comparison_bindings(store.artifact(r['reference']),authority)
    return reduced, bound


def assemble_context(purpose, packet, *, archive, authority=None):
    """One entry point for purpose views from the same bound source records."""
    if purpose not in INPUT_BUDGET: raise ValueError('CONTEXT_PURPOSE')
    authority = deepcopy(authority or {})
    original = archive.snapshot(dict(packet=packet, authority=authority))
    # Validate every original immutable reference before offloading anything.
    archive.register_references(packet)
    archive.register_references(authority)
    omissions = []
    if purpose == 'research_decision' and 'history' in packet:
        reduced, bound = _research(packet, authority, archive)
        for key in ('history', 'current_feedback', 'performed_batch_evidence'):
            omissions.append(dict(reason='Normalized facts / deduplicated aliases; original retained',
                reference=original, pointer='/packet/' + key))
        fact_ids = sorted(bound['facts'])
    elif 'executions' in packet and 'facts' in packet:
        # Accept the expanded canonical ledger; do not construct competing IDs.
        reduced = _compact_ledger(packet)
        reduced['executions'].sort(key=lambda r:r['execution_id'])
        bound = packet
        fact_ids = sorted(packet['facts'])
    else:
        reduced = deepcopy(packet)
        bound = dict(facts=packet.get('bound_facts', {}))
        fact_ids = sorted(bound['facts'])
        if bound['facts']:
            common=('execution_id','candidate','controller','scientific_configuration_identity',
                'structure_identity','time_s','owner_run_id','source_artifact','source_path','comparison_conditions')
            sources={}; compact={}
            for key,fact in bound['facts'].items():
                metadata={k:fact[k] for k in common if k in fact}
                source_key=digest(metadata)[:20]  # Presentation join, not a new scientific identity.
                sources[source_key]=metadata
                compact[key]={k:v for k,v in fact.items() if k not in common} | dict(source_context=source_key)
            reduced['bound_facts']=compact
            reduced['execution_sources']=sources
            reduced['binding_resolution']='bound_facts[key] joins execution_sources[source_context]; expanded original bindings remain in the archived canonical ledger.'
    reduced = _offload(reduced, original, omissions, '/packet')
    roles = authority.get('roles', {})
    if not roles:
        roles = dict(selected_incumbent=packet.get('selected'), latest_attempt=packet.get('latest'),
            latest_completed_evaluation=None, source_baseline=None)
    repeat_count = len(bound.get('replications', []))
    reduced['working_context'] = dict(version=VERSION, purpose=purpose,
        scientific_question=authority.get('question'), unchanged_acceptance=authority.get('acceptance'),
        roles=roles, chronology=authority.get('chronology', packet.get('chronology')),
        case_id=authority.get('case_id', packet.get('case_id')),
        observations_scope='Observed bound facts; frozen_pre_experiment_background is historical.',
        recorded_replications=bound.get('replications', []),
        repeatability_scope=('Matching recorded repeats retained; they do not establish broad variability.' if repeat_count
            else 'No explicit matching repeat in this supplied scope; other scopes are not ruled out.'),
        hypotheses=authority.get('hypotheses', []), contradictions=authority.get('contradictions', []),
        rejected_claims=authority.get('rejected_claims', packet.get('failures', {})),
        known_review_issues=authority.get('known_review_issues', []),
        unresolved_questions=authority.get('unresolved', packet.get('confounders', [])),
        evidence_that_would_change_decision=authority.get('change_evidence', []),
        legal_actions=authority.get('legal_actions', packet.get('capabilities', {}).get('legal', {})),
        remaining_budget=authority.get('remaining_budget', packet.get('capabilities', {}).get('remaining')),
        stop=authority.get('stop', packet.get('stop')),
        sources=dict(reference=original, pointer='/packet', verified_retrievable=True),
        detail_access='Read only original pointers using EvidenceArchive.retrieve or already advertised evidence.read/diagnosis.inspect_evidence. No hidden model tools; if required input cannot fit, preparation fails.',
        retrieval_permission_scope=archive.scope)
    # M4 already carries replications in its normalized canonical packet.
    if 'replications' in reduced: reduced['working_context'].pop('recorded_replications')
    if purpose=='research_decision' and 'history' in packet:
        reduced['working_context']['chronology']=dict(view_pointer='/chronology',authority='Store reservation/completion events')
        reduced['working_context']['unchanged_acceptance']=dict(view_pointer='/acceptance' if 'acceptance' in reduced else '/scope')
    canonical_reference = archive.snapshot(dict(facts=bound['facts']))
    manifest = archive.manifest()
    audit = dict(version=VERSION, purpose=purpose, selected_fact_ids=fact_ids,
        source_manifest=manifest, source_reference=original, omissions=omissions,
        canonical_fact_reference=canonical_reference,
        scientific_thresholds_changed=False, facts_renderer='evidence_bound_reporting@3.0.0',
        actual_input_tokens=None, live_observed=False)
    return dict(view=reduced, audit=audit, canonical_facts=bound['facts'])


def retrieve_fact(assembly, fact_id, *, archive, expected=None):
    """Bound ledger paging; wrong execution/metric/structure is an error."""
    facts=assembly['canonical_facts']
    if fact_id not in facts: raise ValueError('UNRESOLVED_FACT')
    fact=facts[fact_id]
    if any(fact.get(k)!=v for k,v in (expected or {}).items()):
        raise ValueError('CROSS_EXECUTION_METRIC_BINDING')
    return archive.retrieve(assembly['audit']['canonical_fact_reference'],
        pointer='/facts/'+pointer_part(fact_id),limit=100,byte_limit=4096,binding=fact)


def request_facts(request):
    """Render from the exact archived input ledger, not today's working view."""
    audit=request.get('context_assembly_audit')
    if not audit:
        return json.loads(request['payload']['messages'][1]['content'])['bound_facts']
    manifest_path=(ROOT/audit['source_manifest']).resolve()
    if not manifest_path.is_relative_to(ROOT):raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
    manifest=read(manifest_path)
    ref=audit['canonical_fact_reference']
    source=next((s for s in manifest['sources'] if s['reference']==ref),None)
    if source is None or 'path' not in source:raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
    path=(ROOT/source['path']).resolve()
    archive_root=manifest_path.parent.parent
    if not path.is_relative_to(archive_root):raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['artifact_id']:raise ValueError('CONTEXT_ARCHIVE_CHANGED')
    return json.loads(raw)['facts']


def measure_input(payload, config, purpose):
    """Complete wire payload measurement; explicit conservative estimate only."""
    _no_secrets(payload)
    # Match the transport serializer, including its spaces, rather than only
    # measuring the canonical archive encoding.
    serialized = json.dumps(payload, ensure_ascii=False)
    byte_count = len(serialized.encode('utf-8'))
    guard = config['context_guard']; framing = guard['framing_headroom_tokens']
    estimate = byte_count + framing
    allowance = min(INPUT_BUDGET[purpose], guard['context_limit_tokens'] -
        payload['max_tokens'] - INTERACTION_RESERVE)
    return dict(characters=len(serialized), utf8_bytes=byte_count,
        estimated_input_tokens=estimate, actual_input_tokens=None,
        method='Conservative estimate: one token per serialized UTF-8 byte plus configured framing; no appropriate installed tokenizer. Includes all messages, schemas and wire metadata.',
        input_budget_tokens=allowance, configured_context_limit_tokens=guard['context_limit_tokens'],
        response_reserve_tokens=payload['max_tokens'], interaction_reserve_tokens=INTERACTION_RESERVE,
        passed=estimate<=allowance and byte_count<=config['context_bytes'])


def fit_request(wire, config, purpose, *, archive):
    """Bounded deterministic fitting; required facts never become references.

    Full originals and each changed section remain retrievable. Schema, model
    settings, exact observations, current permissions and budget stay inline.
    """
    wire = deepcopy(wire)
    original = archive.snapshot(wire)
    steps = []
    context = json.loads(wire['messages'][1]['content'])
    def report():
        sections = {k:len(json.dumps(v,ensure_ascii=False).encode('utf8'))
                    for k,v in context.items()}
        role = context.get('role_context', {})
        sections.update({'role_context/'+k:len(json.dumps(v,ensure_ascii=False).encode('utf8'))
                         for k,v in role.items()})
        packet = role.get('research_packet', context)
        sections.update({'packet/'+k:len(json.dumps(v,ensure_ascii=False).encode('utf8'))
                         for k,v in packet.items()})
        sections['tool_schemas'] = len(json.dumps(wire.get('tools',[]),ensure_ascii=False).encode('utf8'))
        return sections
    def reference(value, path):
        return dict(reference=archive.snapshot(value), pointer='',
                    original_request=dict(reference=original,pointer=path),
                    scope='Archived detail; required decision facts retained inline')
    for stage in range(4):
        wire['messages'][1]['content'] = encode(context)
        measurement = measure_input(wire,config,purpose)
        steps.append(dict(stage=stage,measurement=measurement,section_bytes=report()))
        if measurement['passed']:
            return wire,dict(fitting_steps=steps,measurement=measurement,original_payload=original)
        if stage==3:break
        seen={}
        def compact(value,path=''):
            if isinstance(value,list):return [compact(v,path+'/'+str(i)) for i,v in enumerate(value)]
            if not isinstance(value,dict):return value
            out={}
            for key,child in value.items():
                p=path+'/'+pointer_part(key)
                # Current execution authority is compared with its immutable
                # snapshot at the wire boundary. Keep its menu and budgets
                # inline; duplicate-detail pointers are for archived evidence.
                if key=='capabilities' and isinstance(child,dict) and child.get('authority_snapshot'):
                    out[key]=deepcopy(child);continue
                # Remove only redundant representations, never an execution's
                # metric, alias, identity or failure. First occurrence stays.
                if stage==0 and isinstance(child,(dict,list)) and key in {
                        'parameter_catalog','legal_actions','remaining_budget','chronology','frozen_cases'}:
                    identity=digest(child)
                    if identity in seen:
                        out[key]=dict(view_pointer=seen[identity]);continue
                    seen[identity]=p
                # Verbose historical decisions are not current instructions.
                if stage==1 and key in {'decisions','original_action','complete_original_decision'}:
                    # Parameter decision dictionaries are exact configuration
                    # facts. Only historical free-text rationale is offloaded.
                    def prior_summary(v,location):
                        if isinstance(v,list):return [prior_summary(x,location+'/'+str(i)) for i,x in enumerate(v)]
                        if not isinstance(v,dict):return v
                        return {k:(reference(x,location+'/'+pointer_part(k)) if k in {
                            'reasoning','rationale','next_step'} and isinstance(x,str) else
                            prior_summary(x,location+'/'+pointer_part(k))) for k,x in v.items()}
                    out[key]=prior_summary(child,p);continue
                if stage==2 and key in {'considered','experiment_ledger','evidence_history',
                        'candidate_artifacts','full_mutation_rebuild_reuse_evidence','metric_sources'}:
                    out[key]=reference(child,p);continue
                out[key]=compact(child,p)
            return out
        context=compact(context)
    audit=dict(fitting_steps=steps,measurement=measurement,original_payload=original,
        action='Reduce optional archived detail or split the decision purpose; required facts/schemas exceed the unchanged cap.')
    path=archive.directory/'audits'/(digest(audit)+'.json')
    atomic_json(path,audit)
    raise ValueError('CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET: '+str(path)+'; '+json.dumps(report(),sort_keys=True))


def assemble_request(payload, config, purpose, packet, *, archive, authority=None, context_slot=None):
    """Finalize actual outgoing schemas/messages, preserving provider settings."""
    result = assemble_context(purpose, packet, archive=archive, authority=authority)
    wire = deepcopy(payload)
    if context_slot:
        # Retain role instructions, rejected draft and protocol recovery messages.
        context = json.loads(wire['messages'][1]['content'])
        context['role_context'][context_slot] = result['view']
        wire['messages'][1]['content'] = encode(context)
    else:
        wire['messages'][1]['content'] = encode(result['view'])
    # Archive original full payload; audits never go in the model's input.
    original_wire = archive.snapshot(payload)
    seen_receipts = set();seen_history = set()
    def inspect(v):
        if isinstance(v, dict):
            if 'execution_status' in v and 'charged' in v and 'request_id' in v:
                key = digest(v)
                if key in seen_receipts: raise ValueError('CONTEXT_DUPLICATE_RECEIPT')
                seen_receipts.add(key)
            if len(v)>8 and all(isinstance(x,str) and len(x)==64 for x in v.values()):
                raise ValueError('CONTEXT_FULL_HASH_MANIFEST')
            for key,child in v.items():
                if key in ('history','research_history','study_history'):
                    identity=digest(child)
                    if identity in seen_history:raise ValueError('CONTEXT_DUPLICATE_HISTORY')
                    seen_history.add(identity)
                inspect(child)
        elif isinstance(v, list):
            for child in v: inspect(child)
    issues=[]
    try:inspect(json.loads(wire['messages'][1]['content']))
    except ValueError as exc:issues.append(str(exc))
    wire,fitting=fit_request(wire,config,purpose,archive=archive)
    result['audit'].update(**fitting,
        before_measurement=measure_input(payload, config, purpose),
        unassembled_payload=original_wire, assembled_payload_identity=digest(wire),
        source_manifest=archive.manifest(),preparation_issues=issues)
    audit_path = archive.directory / 'audits' / (digest(result['audit']) + '.json')
    atomic_json(audit_path, result['audit'])
    # Persist even a rejected preparation; never silently truncate a counterexample.
    if issues or not result['audit']['measurement']['passed']:
        raise ValueError('CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET: ' + str(audit_path))
    assembled = archive.snapshot(wire)
    result['audit']['assembled_input_reference'] = assembled
    result['audit']['source_manifest'] = archive.manifest()
    audit_path = archive.directory / 'audits' / (digest(result['audit']) + '.json')
    atomic_json(audit_path, result['audit'])
    return wire, result['audit']


def research_authority(packet, *, replication_pairs=(), new_execution_ids=()):
    """Role bindings come from saved scheduler/events, never from row order."""
    chronology = packet['chronology']; identities = packet['history']['identities']
    return dict(question=dict(frozen_pre_experiment_question=packet.get('case', {}).get('question'),
            current_question='Choose the next legal decision from updated bound feedback, including recorded matching repeats.'),
        acceptance=packet.get('acceptance', packet.get('scope')),
        case_id=packet.get('case_id'), chronology=chronology,
        roles=dict(selected_incumbent=identities['selected_deliverable'] or packet['incumbent'],
            latest_attempt=chronology['latest_execution'],
            latest_completed_evaluation=chronology['latest_completed_evaluation'],
            source_baseline=identities['retained_baseline'], current_case=packet.get('primary'),
            current_batch_source=packet.get('current_batch_source')),
        replication_pairs=list(replication_pairs), new_execution_ids=list(new_execution_ids),
        legal_actions=packet['capabilities']['legal'], remaining_budget=packet['capabilities']['remaining'],
        stop=dict(sealed_cases=packet.get('sealed_cases', []),
            status=packet['current_feedback']['content'].get('status'),
            reason=packet['current_feedback']['content'].get('stop_reason')),
        unresolved=['Dominant physical cause and broad repeatability remain unresolved.'],
        change_evidence=packet.get('case', {}).get('stopping_criteria', []))


WORKING_STATE_VERSION = 'research_working_state@1.0.0'
EXPERIMENT_STATUSES = {'pending', 'failed', 'incomplete', 'completed'}


def _claim_revision(claim, sequence, archive):
    """Claims are interpretations; source validity does not make them facts."""
    archive.register_references(claim)
    for key in ('supporting_evidence', 'counterexamples'):
        for selector in claim.get(key, []):
            if isinstance(selector, dict) and 'reference' in selector:
                page = archive.retrieve(selector['reference'], pointer=selector.get('pointer', ''),
                    limit=100, byte_limit=8192)
                if 'value' in selector and page['page']['content'] != selector['value']:
                    raise ValueError('CONTEXT_CLAIM_EVIDENCE_VALUE_CHANGED')
    return dict(sequence=sequence, claim=deepcopy(claim),
        evidence_source=archive.snapshot(claim), causal_truth_verified=False)


def create_working_state(packet, *, authority, archive, claims=(), experiments=(),
                         candidate_configuration=None, candidate_artifacts=()):
    """Derived state over the shared assembler and caller's authorized sources.

    Metric descriptions and scientific interpretations are supplied by the task
    adapter. This common layer retains evidence, identity, lineage and authority.
    It neither discovers historical Stores nor allocates research resources.
    """
    assembly = assemble_context('research_decision', packet, archive=archive, authority=authority)
    state = dict(version=WORKING_STATE_VERSION, revision=0, packet=deepcopy(packet),
        authority=deepcopy(authority), current_facts=assembly['canonical_facts'],
        evidence_history=[dict(revision=0, source=assembly['audit']['source_reference'],
            canonical_facts=assembly['audit']['canonical_fact_reference'])],
        claims={}, experiments={}, candidate_configuration=deepcopy(candidate_configuration),
        candidate_artifacts=deepcopy(list(candidate_artifacts)),
        capabilities=deepcopy(packet.get('capabilities', {})),
        experiment_permissions=deepcopy(authority.get('experiment_permissions', packet.get('scope'))),
        budget=deepcopy(authority.get('remaining_budget')),
        budget_accounting=deepcopy(authority.get('budget_accounting')), archive_scope=deepcopy(archive.scope))
    for claim in claims:
        state['claims'].setdefault(claim['claim_id'], []).append(_claim_revision(claim, 0, archive))
    return update_working_state(state, archive=archive, experiment_updates=experiments,
        _initial=True)


def update_working_state(state, *, archive, evidence_packet=None, authority=None,
                         claim_revisions=(), experiment_updates=(),
                         candidate_configuration=None, _initial=False):
    """Append traceable claim/experiment revisions; never reset a sealed scope."""
    if state['version'] != WORKING_STATE_VERSION or state['archive_scope'] != archive.scope:
        raise ValueError('CONTEXT_WORKING_STATE_SCOPE')
    result = deepcopy(state)
    revision = state['revision'] + (0 if _initial else 1)
    result['revision'] = revision
    if authority is not None:
        old_stop = state['authority'].get('stop', {})
        new_stop = authority.get('stop', {})
        old_status = str(old_stop.get('status', '')).lower()
        if (old_stop.get('sealed_cases') or 'stop' in old_status or
                old_status in {'sealed', 'closed', 'finished'}) and new_stop != old_stop:
            raise ValueError('CONTEXT_SEALED_SCOPE_CANNOT_REOPEN')
        # A new observation may consume resources; it cannot mint restored budget.
        old_budget = state.get('budget') or {}
        new_budget = authority.get('remaining_budget') or {}
        reconciled=False
        if authority.get('ledger_reconciliation'):
            run_id=archive.scope.get('context_id')
            for store in archive.stores:
                try:store.session(run_id)
                except ValueError:continue
                actual=store.remaining()
                if (authority.get('budget_accounting')==actual and
                    state.get('budget_accounting',{}).get('limit')==actual['limit'] and
                    new_budget==store.spendable(run_id)['remaining']):
                    reconciled=True
            if not reconciled:raise ValueError('CONTEXT_LEDGER_RECONCILIATION_NOT_VERIFIED')
        for key, value in old_budget.items():
            if isinstance(value, (int, float)) and new_budget.get(key, value) > value and not reconciled:
                raise ValueError('CONTEXT_BUDGET_CANNOT_RESET')
        result['authority'] = deepcopy(authority)
        result['budget'] = deepcopy(new_budget)
        result['budget_accounting'] = deepcopy(authority.get('budget_accounting', state.get('budget_accounting')))
        result['experiment_permissions'] = deepcopy(authority.get('experiment_permissions', state.get('experiment_permissions')))
    if evidence_packet is not None:
        assembly = assemble_context('research_decision', evidence_packet,
            archive=archive, authority=result['authority'])
        result['packet'] = deepcopy(evidence_packet)
        result['current_facts'] = assembly['canonical_facts']
        result['capabilities'] = deepcopy(evidence_packet.get('capabilities', {}))
        result['evidence_history'].append(dict(revision=revision,
            source=assembly['audit']['source_reference'],
            canonical_facts=assembly['audit']['canonical_fact_reference']))
    for claim in claim_revisions:
        result['claims'].setdefault(claim['claim_id'], []).append(_claim_revision(claim, revision, archive))
    for experiment in experiment_updates:
        if experiment['status'] not in EXPERIMENT_STATUSES:
            raise ValueError('CONTEXT_EXPERIMENT_STATUS')
        archive.register_references(experiment)
        key = experiment['experiment_id']
        previous = result['experiments'].get(key)
        if previous and previous[-1]['entry']['status'] != 'pending':
            if previous[-1]['entry'] != experiment:
                raise ValueError('CONTEXT_COMPLETED_WORK_IMMUTABLE')
            continue
        repeat = experiment.get('replication_of')
        if repeat and repeat == key:
            raise ValueError('CONTEXT_REPLICATION_REQUIRES_NEW_ID')
        if repeat and (repeat not in result['experiments'] or
                       result['experiments'][repeat][-1]['entry']['status'] != 'completed'):
            raise ValueError('CONTEXT_REPLICATION_SOURCE_NOT_COMPLETED')
        if repeat and experiment.get('cache_hit'):
            raise ValueError('CONTEXT_CACHE_IS_NOT_REPETITION')
        result['experiments'].setdefault(key, []).append(dict(revision=revision, entry=deepcopy(experiment)))
    if candidate_configuration is not None and candidate_configuration != state.get('candidate_configuration'):
        result['candidate_configuration'] = deepcopy(candidate_configuration)
        for artifact in result['candidate_artifacts']:
            # Dependencies are the adapter/catalog declaration, not guessed from metric names.
            dependencies = artifact.get('dependencies', {})
            if not dependencies or any(candidate_configuration.get(k) != v for k, v in dependencies.items()):
                artifact.update(reusable=False, invalidated_at_revision=revision,
                    invalidation_reason='Declared candidate configuration dependency changed')
    return result


def assert_experiment_eligible(state, experiment):
    """Recovery must not replay completed or uncertain work, or resume STOP."""
    stop = state['authority'].get('stop', {})
    status = str(stop.get('status', '')).lower()
    if stop.get('sealed_cases') or 'stop' in status or status in {'sealed', 'closed', 'finished'}:
        raise ValueError('CONTEXT_SEALED_SCOPE_CANNOT_RESUME')
    key = experiment['experiment_id']
    if key in state['experiments']:
        current = state['experiments'][key][-1]['entry']['status']
        raise ValueError('CONTEXT_WORK_ALREADY_RECORDED: ' + current)
    action = experiment.get('action')
    if action and not state['authority'].get('legal_actions', {}).get(action, False):
        raise ValueError('CONTEXT_ACTION_NOT_PERMITTED')
    repeat = experiment.get('replication_of')
    if repeat and (repeat not in state['experiments'] or
                   state['experiments'][repeat][-1]['entry']['status'] != 'completed'):
        raise ValueError('CONTEXT_REPLICATION_SOURCE_NOT_COMPLETED')
    if repeat and experiment.get('cache_hit'):
        raise ValueError('CONTEXT_CACHE_IS_NOT_REPETITION')
    for key, cost in experiment.get('cost', {}).items():
        budget = state.get('budget') or {}
        if cost > budget.get(key, 0):
            raise ValueError('CONTEXT_BUDGET_EXHAUSTED: ' + key)
    return True


def assemble_working_context(purpose, state, *, archive):
    """Decisions and reporting consume identical bound facts and role bindings."""
    packet = state['packet']
    if purpose == 'final_report' and 'history' in packet:
        _, packet = _research(packet, state['authority'], archive)
    result = assemble_context(purpose, packet, archive=archive, authority=state['authority'])
    if result['canonical_facts'] != state['current_facts']:
        raise ValueError('CONTEXT_WORKING_FACTS_CHANGED')
    state_reference = archive.snapshot(state)
    if purpose == 'final_report':
        result['view']['working_context']['chronology'] = dict(reference=state_reference,
            pointer='/authority/chronology', authority='Original reservation/completion events; current roles retained above')
    experiment_view = {key:[dict(revision=row['revision'], entry={k:v for k,v in row['entry'].items()
        if k in {'status','case_id','seed','task_identity','structure_identity','cache_hit'}}, original_entry=dict(reference=state_reference,
            pointer='/experiments/' + pointer_part(key) + '/' + str(i) + '/entry'))
        for i,row in enumerate(rows)] for key,rows in state['experiments'].items()}
    result['view']['working_context']['recovery'] = dict(version=state['version'],
        revision=state['revision'], claim_history={key:dict(entries=len(rows),
            original_history=dict(reference=state_reference,pointer='/claims/'+pointer_part(key)))
            for key,rows in state['claims'].items()},
        experiment_ledger=experiment_view, candidate_artifacts=state['candidate_artifacts'],
        evidence_history=state['evidence_history'],
        budget_accounting=state['budget_accounting'],
        experiment_permissions=dict(reference=state_reference, pointer='/experiment_permissions'),
        authority_scope='Derived read-only state; does not authorize execution or override host grants')
    result['audit']['source_manifest'] = archive.manifest()
    return result


def assemble_working_request(payload, config, purpose, state, *, archive, context_slot=None):
    """Prepare, measure and archive the recovered next input, without sending."""
    result = assemble_working_context(purpose, state, archive=archive)
    wire = deepcopy(payload)
    if context_slot:
        context=json.loads(wire['messages'][1]['content'])
        context['role_context'][context_slot]=result['view']
        wire['messages'][1]['content']=encode(context)
    else:
        wire['messages'][1]['content'] = encode(result['view'])
    wire,fitting=fit_request(wire,config,purpose,archive=archive)
    measurement = fitting['measurement']
    result['audit'].update(**fitting, working_revision=state['revision'],
        assembled_input_reference=archive.snapshot(wire), source_manifest=archive.manifest())
    atomic_json(archive.directory / 'audits' / (digest(result['audit']) + '.json'), result['audit'])
    if not measurement['passed']:
        raise ValueError('CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET')
    return wire, result['audit']


def persist_working_state(state, *, store, archive):
    """Store immutable full state alongside the existing source allowlist."""
    _no_secrets(state)
    archive.register_references(state)
    value = dict(version=WORKING_STATE_VERSION, state=state, source_manifest=archive.manifest())
    return store.put_context_checkpoint(value)


def restore_working_state(reference, *, store, scope, stores=()):
    """Rehydrate from durable Store bytes; caller supplies the same read scope."""
    value = store.artifact(reference)
    if value['version'] != WORKING_STATE_VERSION or value['state']['archive_scope'] != scope:
        raise ValueError('CONTEXT_WORKING_STATE_SCOPE')
    archive = EvidenceArchive.from_manifest(ROOT / value['source_manifest'], scope=scope, stores=stores)
    archive.register_references(value['state'])
    return deepcopy(value['state']), archive
