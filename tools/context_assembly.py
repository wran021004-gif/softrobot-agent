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


def role_evidence_archive(store, run_id):
    """Reopen the current role's existing source allowlist, without discovery."""
    role = store.session(run_id)['state'].get('role_context', {})
    manifest = role.get('context_source_manifest') or role.get('research_working_manifest')
    scope = role.get('context_archive_scope') or (role.get('research_working_state') or {}).get('archive_scope')
    if not manifest or not scope:
        raise ValueError('CONTEXT_READ_OUT_OF_SCOPE')
    return EvidenceArchive.from_manifest(ROOT / manifest, scope=scope, stores=(store,))


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

    def load(self, reference):
        """Resolve only the verified immutable source in this scope's allowlist."""
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
        return value

    def retrieve(self, reference, *, pointer='', offset=0, limit=20, byte_limit=4096, binding=None):
        """Same original-pointer paging as evidence.read, without host mutations."""
        from schemas.platform_operations import ReadEvidence
        from tools.platform_tools import bounded_evidence_page
        value=self.load(reference)
        args = ReadEvidence(reference=reference, pointer=pointer, offset=offset, limit=limit, byte_limit=byte_limit)
        page = plain(bounded_evidence_page(value, args))
        return dict(page=page, binding=binding, units=(binding or {}).get('unit'),
            source=self.sources[reference['artifact_id']],
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
    rows = deepcopy(history['rows'])
    if any(not r.get('scientific_configuration_identity') for r in rows):
        raise ValueError('SCIENTIFIC_REPORTING_IDENTITY_REQUIRED')
    from tools.bound_reporting import authoritative_metrics
    for row in rows:
        if not row.get('metrics'):continue
        metrics=row['metrics'];source=metrics['source']
        projection=authoritative_metrics(dict(execution_id=row['candidate']['execution_id'],sources=source,
            structure_identity=row['structure_identity'],scientific_configuration_identity=row['scientific_configuration_identity'],
            legacy_metrics=metrics),archive.load)
        metrics['legacy_profile_metrics']={n:metrics[n] for n in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')}
        metrics.update({f['metric']:f['value'] for f in projection['facts'].values()})
    # Explicit case membership, plus lineage/role anchors. No recency cutoff.
    required = set(packet.get('case', {}).get('evidence_execution_ids', []))
    required.update(c['execution_id'] for c in authority.get('roles', {}).values() if c and c.get('execution_id'))
    # Relationships and canonical results cover the authorized history before
    # the display selection. A narrow view cannot turn a repeat into novelty.
    full_rows=rows
    candidates = authority.get('comparison_execution_ids')
    if candidates is not None:
        allowed = set(candidates) | required
        rows = [r for r in rows if r['candidate'].get('execution_id') in allowed]
    else:
        # These are the caller's already scoped research_records, not all stores.
        allowed = {r['candidate'].get('execution_id') for r in rows}
    pairs = authority.get('replication_pairs', [])
    history_ids={r['candidate'].get('execution_id') for r in full_rows}
    for a, b in pairs:
        if a not in history_ids or b not in history_ids: raise ValueError('CONTEXT_REPLICATION_LINEAGE_OMITTED')
    summary = reporting_summary(dict(history, rows=full_rows),
        new_execution_ids=authority.get('new_execution_ids', []), replication_pairs=pairs,
        selected=authority['roles'].get('selected_incumbent'), latest=authority['roles'].get('latest_attempt'),
        usage=packet['capabilities']['remaining'], stop=authority.get('stop', {}))
    summary['batch_count'] = packet.get('engineering_coverage', {}).get('completed_search_batches', 0)
    bound = ledger(summary,resolve=archive.load)
    bound['structure_definitions'] = {r['structure_identity']:r.get('physical_structure',
        bound['structure_definitions'][r['structure_identity']]) for r in full_rows if r.get('metrics')}
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
        # Final feedback embeds records in both groups and aggregate entries,
        # and may embed search records again in its frozen plan. Retain the
        # authoritative group-record leaves once; their duplicate representations
        # stay in the original archive and exact canonical execution ledger.
        if any(r['pointer'].startswith('/verification/') for r in aliases.values()):
            selected={a:r for a,r in aliases.items() if a in required_aliases or
                re.fullmatch(r'/verification/groups/\d+/records/\d+/acceptance/(?:metrics/[^/]+|accepted|status)',r['pointer']) or
                re.fullmatch(r'/verification/aggregates/\d+/acceptance/(?:accepted|scheduled|recorded|unrecorded|joint_acceptance_fraction|all_scheduled_accepted)',r['pointer']) or
                (r['pointer'].startswith('/verification/comparison/') and not isinstance(r['value'],(dict,list))) or
                r['pointer'] in {'/status','/verification/complete','/verification/improvement_supported'}}
            return selected
        if any(r['pointer'].startswith('/outcomes/') for r in aliases.values()):
            return {a:r for a,r in aliases.items() if a in required_aliases or
                re.fullmatch(r'/outcomes/\d+/metrics/[^/]+',r['pointer']) or
                re.fullmatch(r'/outcomes/\d+/acceptance/(?:accepted|status)',r['pointer']) or
                r['pointer'] in {'/status','/stop_reason'}}
        selected={a:r for a,r in aliases.items() if a in required_aliases or
            ((('/metrics/' in r['pointer'] and '/source/' not in r['pointer'] and '/coverage/' not in r['pointer']) or
              ('/acceptance/' in r['pointer'] and r['pointer'].endswith(('/accepted','/passed','/status'))) or
              '/candidate_minus_baseline/' in r['pointer'] or r['pointer'].endswith(('/classification','/status','/stop_reason'))))}
        # Initial handoffs have no outcome wrapper; preserve that exact handoff.
        return selected or aliases
    feedback['aliases']=selected_aliases(feedback['aliases'])
    for r in reduced['performed_batch_evidence']:
        if set(packet.get('capabilities',{}).get('legal',{}))=={'stop'} and packet.get('verification'):
            # Historical alias wrappers are optional after the research STOP.
            # Keep those cited by the final hypothesis/correction; every old
            # exact metric/failure remains in the inline canonical ledger.
            r['aliases']={a:v for a,v in r['aliases'].items() if a in required_aliases}
        else:r['aliases']=selected_aliases(r['aliases'])
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
        operational_facts=authority.get('operational_facts'),
        phase_boundaries=authority.get('phase_boundaries'),
        remaining_budget=authority.get('remaining_budget', packet.get('capabilities', {}).get('remaining')),
        stop=authority.get('stop', packet.get('stop')),
        sources=dict(reference=original, pointer='/packet', verified_retrievable=True),
        detail_access='Read only original pointers using EvidenceArchive.retrieve or already advertised evidence.read/diagnosis.inspect_evidence. No hidden model tools; if required input cannot fit, preparation fails.',
        retrieval_permission_scope=archive.scope)
    if purpose=='final_report' and authority.get('prefetched_report_only'):
        if authority.get('legal_actions') != {'report': {'execution_authorized': False}}:
            raise ValueError('CONTEXT_REPORT_PERMISSION_REQUIRED')
        reduced['working_context']['detail_access']='All required evidence is prefetched. References are archive provenance, not model-callable retrieval. No scientific or read tools are available in this report request.'
        reduced['working_context']['sources']['verified_retrievable']=False
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


def check_outgoing_request(payload, config, purpose, *, host=None, as_of_unix=None):
    """Check the exact final object after every appended message/tool result.

    No fitting or credential loading occurs here. Preparation must resolve an
    overflow before this boundary, and historical reproduction cannot dispatch.
    """
    measurement=measure_input(payload,config,purpose)
    if not measurement['passed']:
        raise ValueError('CONTEXT_SEND_BOUNDARY_OVERFLOW: '+json.dumps(measurement,sort_keys=True))
    if host is not None:
        from tools.current_research_authority import check_payload
        import time
        now=time.time() if as_of_unix is None else as_of_unix
        session=host.store.session(host.run_id);role=session['state'].get('role_context',{})
        deadline=role.get('campaign_permissions',{}).get('elapsed_deadline_unix')
        if session['status']!='running':raise ValueError('CONTEXT_SEND_SESSION_NOT_RUNNING')
        if deadline is not None and now>=deadline:raise ValueError('CONTEXT_SEND_DEADLINE_EXPIRED')
        if not host.compatibility()['compatible']:raise ValueError('CONTEXT_SEND_DEPENDENCIES_CHANGED')
        check_payload(host,payload)
    return measurement


def declare_retrieval(view, payload):
    """Advertise actual native reads or explicit prefetch, never a hidden tool."""
    from tools.platform_models import provider_name_map, LEGACY_TOOL_NAMING, READABLE_TOOL_NAMING
    names={t['function']['name'] for t in payload.get('tools',[])}
    reads={'evidence.read':'1.0.0'}
    callable_read=any(provider_name_map(reads,scheme)['evidence.read'] in names
        for scheme in (LEGACY_TOOL_NAMING,READABLE_TOOL_NAMING))
    working=view['working_context']
    working['model_callable_archive_read']=callable_read
    working['detail_access']=('Use the advertised evidence.read with the original reference and JSON pointer; bounded pages preserve source scope.'
        if callable_read else 'Required evidence is prefetched. Archive references are provenance only; this request has no model-callable archive read. Missing required material must fail preparation.')


def fit_request(wire, config, purpose, *, archive):
    """Bounded deterministic fitting; required facts never become references.

    Full originals and each changed section remain retrievable. Schema, model
    settings, exact observations, current permissions and budget stay inline.
    """
    wire = deepcopy(wire)
    original = archive.snapshot(wire)
    steps = []
    context = json.loads(wire['messages'][1]['content'])
    original_metric_sources={}
    def collect_metric_sources(value):
        if isinstance(value,dict):
            for row in value.get('executions',[]) if isinstance(value.get('executions'),list) else []:
                if isinstance(row,dict) and 'execution_id' in row and isinstance(row.get('metric_sources'),dict):
                    old=original_metric_sources.get(row['execution_id'])
                    if old is not None and old!=row['metric_sources']:raise ValueError('CONTEXT_EXECUTION_SOURCE_CONFLICT')
                    original_metric_sources[row['execution_id']]=deepcopy(row['metric_sources'])
            for child in value.values():collect_metric_sources(child)
        elif isinstance(value,list):
            for child in value:collect_metric_sources(child)
    collect_metric_sources(context)
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
    for stage in range(7):
        wire['messages'][1]['content'] = encode(context)
        measurement = measure_input(wire,config,purpose)
        steps.append(dict(stage=stage,measurement=measurement,section_bytes=report()))
        if measurement['passed']:
            return wire,dict(fitting_steps=steps,measurement=measurement,original_payload=original)
        if stage==6:break
        if stage==4:
            packet=context.get('role_context',{}).get('research_packet',context)
            bound=packet.get('bound_evidence',{})
            execution_rows={r['execution_id']:r for r in bound.get('executions',[])}
            # Join identity/case columns that were repeated in a second history
            # table. Every original field is retained in the same execution row.
            for row in packet.get('history',{}).get('rows',[]):
                candidate=row.get('candidate',{});eid=candidate.get('execution_id')
                target=execution_rows.get(eid)
                if target is None:continue
                for key,value in row.items():
                    if key=='candidate':
                        target['candidate']=deepcopy(value)
                    elif key in target and target[key]!=value:
                        raise ValueError('CONTEXT_HISTORY_EXECUTION_JOIN_CONFLICT: '+key)
                    else:target[key]=deepcopy(value)
            if execution_rows and 'history' in packet:
                packet['history']['rows']=[dict(execution_id=r['candidate']['execution_id'],
                    inline_execution_row=True) if r['candidate'].get('execution_id') in execution_rows else r
                    for r in packet.get('history',{}).get('rows',[])]
                bound['history_binding']='history.rows execution_id joins this executions table; candidate/configuration/case/seed/task identity/status are retained there.'
            for attempt in packet.get('chronology',{}).get('attempts',[]):
                candidate=attempt.get('candidate');target=execution_rows.get((candidate or {}).get('execution_id'))
                if target and target.get('candidate')==candidate:
                    attempt.pop('candidate');attempt['execution_id']=candidate['execution_id']
                    attempt['inline_candidate_binding']=True
            packet.get('chronology',{})['candidate_binding']='An attempts row with inline_candidate_binding joins the exact candidate in bound_evidence.executions by execution_id; reservation event, sequence, status and original ordering stay here.'
            verification=packet.get('verification')
            if verification:
                for row in verification.get('outcomes',[]):
                    target=execution_rows.get(row.get('execution_id'))
                    if target is None:continue
                    # Outcome metrics resolve to the exact metric table; retain
                    # role/repetition and all other outcome fields inline once.
                    for key,value in row.items():
                        if key=='metrics':
                            if 'fact_columns' not in bound:continue
                            actual={bound['metric_columns'][c[0]][0]:c[2] for c in target['facts']}
                            if any(actual.get(k)!=v for k,v in value.items()):
                                raise ValueError('CONTEXT_VERIFICATION_METRIC_JOIN_CONFLICT')
                        elif key in {'status','accepted'}:target['verification_'+key]=deepcopy(value)
                        elif key not in {'role','repetition'}:
                            if key=='configuration' and target.get('candidate',{}).get('configuration')==value:continue
                            if key=='candidate_id' and target.get('candidate',{}).get('candidate_id')==value:continue
                            if key in target and target[key]!=value:raise ValueError('CONTEXT_VERIFICATION_EXECUTION_JOIN_CONFLICT: '+key)
                            target[key]=deepcopy(value)
                    preserved={k:row[k] for k in ('execution_id','role','repetition')}
                    row.clear();row.update(preserved,inline_execution_row=True)
                verification['outcome_binding']='Each outcomes execution_id joins bound_evidence.executions; that row retains case/seed/configuration, verification_status/accepted and exact metric cells. Role/repetition retained here.'
            legal=packet.get('capabilities',{}).get('legal',{})
            if set(legal)=={'stop'} and verification:
                # Catalog mechanics are historical after a scientific STOP;
                # exact executed structures remain in bound_evidence, and the
                # authoritative STOP-only capabilities/schema remain untouched.
                study=packet.get('study',{})
                if 'parameter_catalog' in study:
                    study['parameter_catalog']=reference(study['parameter_catalog'],'/role_context/research_packet/study/parameter_catalog')
                if 'subsequent_event' in study:
                    # Exact earlier execution metrics/identity are already in
                    # the bound execution table; this wrapper repeats its full
                    # acceptance and historical implementation manifest.
                    study['subsequent_event']=reference(study['subsequent_event'],'/role_context/research_packet/study/subsequent_event')
            continue
        if stage==5:
            packet=context.get('role_context',{}).get('research_packet',context)
            def compact_references(value,key=None):
                if key=='capabilities':return deepcopy(value)
                if isinstance(value,dict):
                    if set(value)=={'artifact_id','media_type'} and value['media_type']=='application/json':
                        return {'$e':value['artifact_id']}
                    if set(value)=={'$e'}:raise ValueError('CONTEXT_INLINE_EVIDENCE_TAG_COLLISION')
                    return {k:compact_references(v,k) for k,v in value.items()}
                if isinstance(value,list):return [compact_references(v) for v in value]
                return value
            def table(rows):
                columns=sorted({k for row in rows for k in row})
                return dict(table_columns=columns,table_rows=[[row.get(k,{'$absent':True}) for k in columns] for row in rows])
            bound=packet.get('bound_evidence',{})
            if isinstance(bound.get('executions'),list) and bound['executions']:
                bound['executions']=table(bound['executions'])
            chronology=packet.get('chronology',{})
            if isinstance(chronology.get('attempts'),list) and chronology['attempts']:
                chronology['attempts']=table(chronology['attempts'])
            packet['inline_table_binding']='A {table_columns,table_rows} object is the same row list with field names transmitted once. Each table_rows cell corresponds to table_columns at the same index; singleton {"$absent":true} means that original row omitted the field. Exact values and identities remain inline.'
            for block in [packet.get('current_feedback',{}),*packet.get('performed_batch_evidence',[])]:
                aliases=block.get('aliases',{})
                if not aliases:continue
                prefixes=sorted({v['pointer'].rsplit('/',1)[0] for v in aliases.values()})
                prefix_indices={p:i for i,p in enumerate(prefixes)}
                block['aliases']={a:[prefix_indices[v['pointer'].rsplit('/',1)[0]],v['pointer'].rsplit('/',1)[1],v['value']] for a,v in aliases.items()}
                block['alias_pointer_prefixes']=prefixes
                block['alias_columns']=['pointer_prefix_index','escaped_pointer_leaf','exact_value']
                block['alias_binding']='aliases[F] has alias_columns; exact original JSON pointer is alias_pointer_prefixes[index]+"/"+escaped_pointer_leaf. Its source is this block reference. Native F handles and original host catalog are unchanged.'
            compressed=compact_references(packet)
            packet.clear();packet.update(compressed)
            packet['inline_evidence_binding']='Singleton {"$e":sha256} is exactly {artifact_id:sha256,media_type:"application/json"}; media type transmitted once. All original artifact IDs remain inline. Current capabilities are untouched.'
            counts={}
            def count_strings(value,key=None):
                if key=='capabilities':return
                if isinstance(value,str) and len(value)>=32:counts[value]=counts.get(value,0)+1
                elif isinstance(value,dict):
                    for k,v in value.items():count_strings(v,k)
                elif isinstance(value,list):
                    for v in value:count_strings(v)
            count_strings(packet)
            strings=sorted(s for s,n in counts.items() if n>=2 and (n-1)*len(s)>n*15)
            indices={s:i for i,s in enumerate(strings)}
            def intern(value,key=None):
                if key=='capabilities':return deepcopy(value)
                if isinstance(value,str) and value in indices:return {'$s':indices[value]}
                if isinstance(value,dict):
                    if set(value)=={'$s'}:raise ValueError('CONTEXT_INLINE_STRING_TAG_COLLISION')
                    return {k:intern(v,k) for k,v in value.items()}
                if isinstance(value,list):return [intern(v) for v in value]
                return value
            packed=intern(packet)
            packed['inline_strings']=strings
            packed['inline_string_binding']='A singleton {"$s":i} means the exact string inline_strings[i] in THIS input. This lossless table interns repeated identity/source strings only; numbers, units, facts and immutable current capabilities are unchanged. No archive read is needed.'
            packet.clear();packet.update(packed)
            continue
        if stage==3:
            # Each metric was previously transmitted twice: an execution's
            # metric->fact-ID map, then a global fact-ID->value/unit map.
            # Join those two exact tables inline. No fact or binding disappears;
            # canonical archived facts and all F selectors remain unchanged.
            def join_tables(value):
                if isinstance(value,list):return [join_tables(v) for v in value]
                if not isinstance(value,dict):return value
                if isinstance(value.get('executions'),list) and isinstance(value.get('facts'),dict):
                    result=deepcopy(value);facts=result['facts']
                    if all(isinstance(r,dict) and isinstance(r.get('facts'),dict) and
                           all(fid in facts and set(facts[fid])=={'value','unit'} for fid in r['facts'].values())
                           for r in result['executions']):
                        referenced={fid for row in result['executions'] for fid in row['facts'].values()}
                        if referenced==set(facts):
                            metric_units={}
                            for row in result['executions']:
                                for metric,fid in row['facts'].items():
                                    unit=facts[fid]['unit']
                                    if metric in metric_units and metric_units[metric]!=unit:
                                        raise ValueError('CONTEXT_METRIC_UNIT_CONFLICT')
                                    metric_units[metric]=unit
                            result['metric_columns']=[[metric,metric_units[metric]] for metric in sorted(metric_units)]
                            indices={pair[0]:i for i,pair in enumerate(result['metric_columns'])}
                            result['fact_columns']=['metric_index','fact_id','value','source_index']
                            for row in result['executions']:
                                sources=row.pop('source_artifacts')
                                metric_sources=row.pop('metric_sources')
                                if 'reference' in metric_sources:
                                    original_sources=original_metric_sources.get(row['execution_id'])
                                    if original_sources is None or hashlib.sha256(encode(original_sources).encode('utf8')).hexdigest()!=metric_sources['reference']['artifact_id']:
                                        raise ValueError('CONTEXT_METRIC_SOURCES_CHANGED')
                                    metric_sources=original_sources
                                source_keys=sorted(sources)
                                source_indices={key:i for i,key in enumerate(source_keys)}
                                row['sources']=[sources[key] for key in source_keys]
                                row['facts']=[[indices[metric],fid,facts[fid]['value'],source_indices[metric_sources[metric]]]
                                    for metric,fid in sorted(row['facts'].items())]
                            result.pop('facts')
                            result['binding_resolution']='Each execution retains exact identities. facts rows use fact_columns: metric_index, immutable fact_id, exact value, source_index. metric_columns[metric_index] is [metric,unit]; row.sources[source_index] is the exact original source artifact. No observation or source binding omitted.'
                            return result
                return {k:join_tables(v) for k,v in value.items()}
            context=join_tables(context)
            continue
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
                    if stage==0:
                        for name in ('legal','remaining','operational_facts'):
                            if name in child:seen[digest(child[name])]=p+'/'+name
                    out[key]=deepcopy(child);continue
                # Remove only redundant representations, never an execution's
                # metric, alias, identity or failure. First occurrence stays.
                if stage==0 and isinstance(child,(dict,list)) and key in {
                        'parameter_catalog','legal_actions','remaining_budget','chronology','frozen_cases',
                        'operational_facts','budget_accounting',
                        'acceptance','unchanged_acceptance','task_acceptance','roles','incumbent',
                        'primary','source_baseline','latest_attempt','selected_incumbent','current_batch_source'}:
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
                if stage==2 and key in {'considered','experiment_ledger','evidence_history','claim_history',
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
    declare_retrieval(result['view'],payload)
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


def candidate_roles(packet, *, frozen_selection=None):
    """Bind each role to its explicit decision/event; promotion preserves STOP."""
    chronology=packet['chronology'];identities=packet['history']['identities']
    roles=dict(selected_incumbent=identities['selected_deliverable'] or packet['incumbent'],
        latest_attempt=chronology['latest_execution'],latest_completed_evaluation=chronology['latest_completed_evaluation'],
        source_baseline=identities['retained_baseline'],current_case=packet.get('primary'),
        current_batch_source=packet.get('current_batch_source'),frozen_challenger=None,promoted_deliverable=None)
    if frozen_selection:roles.update(selection_roles(frozen_selection))
    return roles


def selection_roles(frozen_selection):
    """Post-verification adoption changes a delivery role, never the old STOP."""
    return dict(incumbent_at_decision=deepcopy(frozen_selection['model_selected_at_research_stop']),
        frozen_challenger=deepcopy(frozen_selection['selected_configuration']),
        promoted_deliverable=(deepcopy(frozen_selection['selected_configuration'])
            if frozen_selection.get('outcome')=='promote_frozen_candidate' and frozen_selection.get('improvement_supported') is True else None))


def research_authority(packet, *, replication_pairs=(), new_execution_ids=(), frozen_selection=None):
    """Role bindings come from saved scheduler/events, never from row order."""
    chronology = packet['chronology']; identities = packet['history']['identities']
    return dict(question=dict(frozen_pre_experiment_question=packet.get('case', {}).get('question'),
            current_question='Choose the next legal decision from updated bound feedback, including recorded matching repeats.'),
        acceptance=packet.get('acceptance', packet.get('scope')),
        case_id=packet.get('case_id'), chronology=chronology,
        roles=candidate_roles(packet,frozen_selection=frozen_selection),
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
        if authority.get('accounting_binding'):
            from tools.current_research_authority import verify_accounting_transition
            reconciled=verify_accounting_transition(state,authority,archive)
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
    if state.get('current_execution'):
        from tools.current_research_authority import restored_execution
        result['current_execution']=restored_execution(result,archive.stores)
    return result


def assert_experiment_eligible(state, experiment, *, as_of_unix=None):
    """Recovery must not replay completed or uncertain work, or resume STOP."""
    stop = state['authority'].get('stop', {})
    status = str(stop.get('status', '')).lower()
    if stop.get('sealed_cases') or 'stop' in status or status in {'sealed', 'closed', 'finished'}:
        raise ValueError('CONTEXT_SEALED_SCOPE_CANNOT_RESUME')
    import time
    now=time.time() if as_of_unix is None else as_of_unix
    deadline=(state['authority'].get('campaign_clock') or {}).get('deadline_unix') or state['authority'].get('elapsed_deadline_unix')
    current=state.get('current_execution')
    if current:
        deadline=current.get('elapsed_deadline_unix') or deadline
        if not current.get('current_session_verified') or not current.get('implementation_compatible') or current.get('sealed') or current.get('expired'):
            raise ValueError('CONTEXT_CURRENT_EXECUTION_AUTHORITY_UNAVAILABLE')
    if deadline is not None and now>=deadline:raise ValueError('CONTEXT_EXECUTION_DEADLINE_EXPIRED')
    key = experiment['experiment_id']
    if key in state['experiments']:
        current = state['experiments'][key][-1]['entry']['status']
        raise ValueError('CONTEXT_WORK_ALREADY_RECORDED: ' + current)
    action = experiment.get('action')
    legal=(current or state['authority']).get('legal_actions',{})
    if action and not legal.get(action, False):
        raise ValueError('CONTEXT_ACTION_NOT_PERMITTED')
    if action and isinstance(legal.get(action),dict) and legal[action].get('execution_authorized') is False:
        raise ValueError('CONTEXT_ACTION_EXECUTION_UNAUTHORIZED')
    repeat = experiment.get('replication_of')
    if repeat and (repeat not in state['experiments'] or
                   state['experiments'][repeat][-1]['entry']['status'] != 'completed'):
        raise ValueError('CONTEXT_REPLICATION_SOURCE_NOT_COMPLETED')
    if repeat and experiment.get('cache_hit'):
        raise ValueError('CONTEXT_CACHE_IS_NOT_REPETITION')
    for key, cost in experiment.get('cost', {}).items():
        budget = current['remaining_budget'] if current else state.get('budget') or {}
        if cost > budget.get(key, 0):
            raise ValueError('CONTEXT_BUDGET_EXHAUSTED: ' + key)
    return True


def assemble_working_context(purpose, state, *, archive):
    """Decisions and reporting consume identical bound facts and role bindings."""
    packet = state['packet']
    if purpose == 'final_report' and 'history' in packet:
        _, packet = _research(packet, state['authority'], archive)
    result = assemble_context(purpose, packet, archive=archive, authority=state['authority'])
    if state.get('current_execution'):
        live=state['current_execution'];view=result['view']['working_context']
        view.update(current_execution=deepcopy(live),legal_actions=deepcopy(live['legal_actions']),remaining_budget=deepcopy(live['remaining_budget']))
        if result['view'].get('capabilities'):
            result['view']['capabilities']=dict(legal=deepcopy(live['legal_actions']),remaining=deepcopy(live['remaining_budget']),
                reason=live['reason'])
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
    round_claim = lambda key: re.fullmatch(r'round\d+-interpretation-\d+',key) is not None
    latest_claim_revision=max((rows[-1]['sequence'] for key,rows in state['claims'].items() if rows and round_claim(key)),default=0)
    result['view']['working_context']['hypothesis_revisions']={key:dict(
        current={k:deepcopy(v) for k,v in rows[-1]['claim'].items()
            if k not in ('supporting_evidence','counterexamples','evidence_aliases')},revision=rows[-1]['sequence'],
        supporting_evidence_count=len(rows[-1]['claim'].get('supporting_evidence',[])),
        counterexample_count=len(rows[-1]['claim'].get('counterexamples',[])),
        supporting_and_contradicting_sources=rows[-1]['evidence_source'],
        previous_revisions=dict(reference=state_reference,pointer='/claims/'+pointer_part(key)),
        evidence_scope='Original revision retains exact selectors; all current canonical observations/counterexamples remain in the fact table.',
        causal_truth_verified=False) for key,rows in state['claims'].items()
            if rows and (not round_claim(key) or rows[-1]['sequence']==latest_claim_revision)}
    result['view']['working_context']['hypothesis_display_policy']='Current named hypotheses and latest round interpretations are displayed; earlier round interpretations and all supporting/counterexample selectors remain in recovery.claim_history. The complete canonical evidence table is unchanged.'
    result['audit']['source_manifest'] = archive.manifest()
    return result


def assemble_working_request(payload, config, purpose, state, *, archive, context_slot=None):
    """Prepare, measure and archive the recovered next input, without sending."""
    result = assemble_working_context(purpose, state, archive=archive)
    declare_retrieval(result['view'],payload)
    wire = deepcopy(payload)
    if context_slot:
        context=json.loads(wire['messages'][1]['content'])
        context['role_context'][context_slot]=result['view']
        wire['messages'][1]['content']=encode(context)
    else:
        wire['messages'][1]['content'] = encode(result['view'])
    if state.get('current_execution'):
        # These are offline next-request preparations. The historical schema
        # cannot advertise scientific actions after expiry or sealing.
        legal=state['current_execution']['legal_actions']
        for tool in wire.get('tools',[]):
            if tool['function']['name']=='research_decide':
                schema=tool['function']['parameters']
                schema=(schema.get('anyOf') or [schema])[0]
                schema['properties']['action']['enum']=list(legal)
    wire,fitting=fit_request(wire,config,purpose,archive=archive)
    measurement = fitting['measurement']
    result['audit'].update(**fitting, working_revision=state['revision'],
        assembled_input_reference=archive.snapshot(wire), source_manifest=archive.manifest())
    if state.get('current_execution'):
        result['audit'].update(offline_preparation=True,execution_authorized=False,
            historical_as_of=(state['authority'].get('operational_facts') or {}).get('cutoff'),
            current_execution=state['current_execution'])
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


def restore_working_state(reference, *, store, scope, stores=(), as_of_unix=None):
    """Rehydrate from durable Store bytes; caller supplies the same read scope."""
    value = store.artifact(reference)
    if value['version'] != WORKING_STATE_VERSION or value['state']['archive_scope'] != scope:
        raise ValueError('CONTEXT_WORKING_STATE_SCOPE')
    archive = EvidenceArchive.from_manifest(ROOT / value['source_manifest'], scope=scope, stores=stores)
    archive.register_references(value['state'])
    state=deepcopy(value['state'])
    from tools.current_research_authority import restored_execution
    state['current_execution']=restored_execution(state,stores,as_of_unix=as_of_unix)
    return state, archive
