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
            if set(value) == {'artifact_id', 'media_type'}:
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


def _comparison_bindings(content):
    result=[]
    for outcome in content.get('outcomes', []):
        comparisons={}
        for kind in ('baseline_comparison','source_comparison'):
            if kind not in outcome:continue
            c=outcome[kind]
            comparisons[kind]=dict(baseline_execution_id=c['baseline']['source']['execution_id'],
                candidate_execution_id=c['candidate']['source']['execution_id'],classification=c['classification'],
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
        ({k:deepcopy(r[k]) for k in ('structure_identity','scientific_configuration_identity','decisions','controller')} if not r.get('metrics') else {})
        for r in sorted(rows, key=lambda r:(r['candidate'].get('execution_id') or '', r['configuration_identity']))])
    # Sorting is presentation only; chronology and latest remain event-bound.
    reduced['bound_evidence'] = _compact_ledger(bound)
    if 'case' in reduced:
        reduced['case']['question_status'] = 'frozen_pre_experiment_background; consult recorded_replications for current evidence'
    feedback = reduced['current_feedback']
    feedback['content'] = dict(status=feedback['content'].get('status'),
        stop_reason=feedback['content'].get('stop_reason'),
        comparison_bindings=_comparison_bindings(packet['current_feedback']['content']),
        evidence_coverage='Current exact F aliases below; complete feedback in archive')
    current_ref = feedback['reference']
    reduced['performed_batch_evidence'] = [r for r in reduced.get('performed_batch_evidence', [])
        if r['reference'] != current_ref]
    required_aliases=set(authority.get('required_aliases', []))
    def selected_aliases(aliases):
        selected={a:r for a,r in aliases.items() if a in required_aliases or
            ((('/metrics/' in r['pointer'] and '/source/' not in r['pointer'] and '/coverage/' not in r['pointer']) or
              '/candidate_minus_baseline/' in r['pointer'] or r['pointer'].endswith(('/classification','/status','/stop_reason'))))}
        # Initial handoffs have no outcome wrapper; preserve that exact handoff.
        return selected or aliases
    feedback['aliases']=selected_aliases(feedback['aliases'])
    for r in reduced['performed_batch_evidence']:
        r['aliases']=selected_aliases(r['aliases'])
        source=archive.sources[r['reference']['artifact_id']]
        store=next(s for s in archive.stores if s.root.relative_to(ROOT).as_posix()==source['store_root'])
        r['comparison_bindings']=_comparison_bindings(store.artifact(r['reference']))
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
    serialized = encode(payload)
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
    result['audit'].update(measurement=measure_input(wire, config, purpose),
        before_measurement=measure_input(payload, config, purpose),
        original_payload=original_wire, assembled_payload_identity=digest(wire),
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
