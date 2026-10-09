"""Bounded evidence investigations using the existing dispatcher, archive and ledger.

Bounded native tool turns per node. A coordinator may propose children; the host
validates each proposal. No scientific computation is performed by this service.
"""
from copy import deepcopy
import json
import sys
import time
from threading import Thread
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import Budget, EvidenceRef
from tools.platform_store import plain, zero, now, encode
from tools.state_io import digest
from schemas.platform_operations import ReadEvidence

class InvestigationOrder(Contract):
    investigation_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    parent_id: str | None = None
    role: Literal['principal','coordinator','investigator'] = 'investigator'
    question: str = Field(min_length=1,max_length=2000)
    evidence: list[EvidenceRef] = Field(min_length=1,max_length=256,description='Finite authorized source scope; metadata is paged, never all bodies prefetched.')
    queries: list[ReadEvidence] = Field(default_factory=list,max_length=12)
    disposition_ids: list[str] | None = Field(default=None,max_length=3,description='Explicit principal report targets; other completed reports may be synthesis context only.')
    allowed_tools: list[Literal['evidence.read']] = Field(default_factory=lambda:['evidence.read'],min_length=1,max_length=1)
    budget: Budget
    timeout_s: float = Field(gt=0,le=36000)
    stop_conditions: list[str] = Field(min_length=1,max_length=6)
    output_bytes: int = Field(default=16384,ge=1024,le=1048576)


class SourceFact(Contract):
    statement: str = Field(min_length=1)
    reference: EvidenceRef
    pointer: str = Field(max_length=300)
    value: object
    source_identity: dict = Field(default_factory=dict,description='Optional exact identity fields carried by the original source, never current-candidate attribution.')


class AdoptedClaim(Contract):
    statement: str = Field(min_length=1)
    supporting_facts: list[SourceFact] = Field(min_length=1,max_length=12)
    additional_support: list[SourceFact] = Field(default_factory=list,max_length=12,description='Explicit principal supplemental evidence; not report facts.')
    scope: list[SourceFact] = Field(min_length=1,max_length=8,description='Exact inspected source fields declaring applicability, e.g. result_type, execution_id, or prediction scope.')
    support_explanation: str = Field(min_length=1,description='Principal explanation linking these facts to this claim; semantic correctness remains unassessed.')


class PrincipalDisposition(Contract):
    investigation_id: str
    report: EvidenceRef | None = None
    disposition: Literal['accept','defer','reject']
    evidence_used: list[SourceFact] = Field(default_factory=list,max_length=12)
    adopted_claims: list[AdoptedClaim] = Field(default_factory=list,max_length=8)
    semantic_claims_unassessed: list[str] = Field(default_factory=list,max_length=12)
    remaining_unknowns: list[str] = Field(default_factory=list,max_length=12)
    reason: str = Field(min_length=1)
    selection_provenance: dict | None = None


class InvestigationReturn(Contract):
    facts: list[SourceFact] = Field(default_factory=list,max_length=12)
    counterevidence: list[SourceFact] = Field(default_factory=list,max_length=8)
    unknowns: list[str] = Field(default_factory=list,max_length=8)
    interpretation: str
    proposed_next_checks: list[str] = Field(default_factory=list,max_length=6)
    children: list[InvestigationOrder] = Field(default_factory=list,max_length=3)
    dispositions: list[PrincipalDisposition] = Field(default_factory=list,max_length=3,description='Principal-only explicit structured decisions; the runner submits them through the public disposition tool.')
    completion: Literal['complete','incomplete'] = 'complete'


class InvestigationResult(Contract):
    investigation_id: str
    status: str
    result: EvidenceRef | None = None
    reason: str | None = None
    disposition_record: EvidenceRef | None = None
    failure_record: EvidenceRef | None = None
    progress: dict | None = None


class InvestigationStatus(Contract):
    investigation_id: str


class InvestigationDispatcher:
    def __init__(self, host):
        self.host,self.store,self.run_id=host,host.store,host.run_id

    def _grant(self, db=None):
        session=self.store.session(self.run_id,db)
        grant=session['state'].get('role_context',{}).get('investigation_grant')
        if not grant or session['status']!='running':raise ValueError('INVESTIGATION_ACTIVITY_GRANT_REQUIRED')
        if session['state'].get('investigation_grant_identity',digest(grant))!=digest(grant):
            raise ValueError('INVESTIGATION_FROZEN_GRANT_CHANGED')
        deadline=grant.get('deadline_unix')
        if deadline is not None and time.time()>=deadline:raise ValueError('INVESTIGATION_DEADLINE_EXPIRED')
        return session,grant

    def _target_accounting(self,grant,db=None):
        """Opt-in current-grant counters in the existing project ledger.

        Session snapshots are views, not the authority for these counters.
        Historical grants never enter this path.
        """
        policy=grant.get('correction_policy')
        if not policy:return None
        if not (policy.get('version')=='mainline3.shared_completion@2.0.0' and policy.get('maximum')==40) and (policy.get('version')!='mainline3.target_corrections@1.0.0' or (policy.get('planned'),policy.get('maximum'))!=(2,4)):
            raise ValueError('INVESTIGATION_CORRECTION_POLICY_INVALID')
        allocations=grant.get('delivery_allocations',{})
        if set(policy['targets'])!=set(allocations) or any(a.get('request_purposes') for a in allocations.values()):
            raise ValueError('INVESTIGATION_CORRECTION_ALLOCATION_CONFLICT')
        identity=digest(dict(policy=policy,allocations=allocations,deadline=grant.get('deadline_unix')))
        if db is None:
            with self.store.connect(True) as connection:return self._target_accounting(grant,connection)
        row=db.execute("SELECT value FROM meta WHERE key='investigation_target_accounting'").fetchone()
        value=json.loads(row[0]) if row else dict(identity=identity,tasks={},targets={})
        if value['identity']!=identity:raise ValueError('INVESTIGATION_TARGET_AUTHORITY_CHANGED')
        return value

    @staticmethod
    def _save_target_accounting(db,value):
        db.execute("INSERT OR REPLACE INTO meta VALUES ('investigation_target_accounting',?)",(encode(value),))

    def _scope(self, order, db=None):
        session,grant=self._grant(db);nodes=session['state'].get('investigations',{})
        allowed=set(grant['allowed_tools']);evidence=self._sources(session,grant)
        if order.role=='principal' and order.parent_id:raise ValueError('PRINCIPAL_REQUIRES_ROOT_SCOPE')
        if order.parent_id:
            parent=nodes.get(order.parent_id) or session['state'].get('historical_investigations',{}).get(order.parent_id)
            if not parent or parent['order']['role']!='coordinator' or parent['order']['parent_id'] is not None:
                raise ValueError('INVESTIGATION_MAX_DEPTH_OR_PARENT')
            if order.role!='investigator':raise ValueError('ONLY_INVESTIGATOR_CHILDREN')
            if parent.get('status')!='completed':raise ValueError('COORDINATOR_RESULT_REQUIRED')
            proposed=parent.get('children',[])
            binding=grant.get('historical_execution_bindings',{}).get(order.parent_id)
            if binding and parent.get('kind')=='historical_reuse':
                if binding['report']!=parent['result'] or binding['proposed_children']!=proposed:
                    raise ValueError('HISTORICAL_PLANNING_BINDING_MISMATCH')
                if plain(order) not in binding['authorized_children']:
                    raise ValueError('CHILD_NOT_AUTHORIZED_BY_NEW_BINDING')
                original=next((p for p in proposed if p['investigation_id']==order.investigation_id),None)
                mutable=('budget','timeout_s') if grant.get('correction_policy') else ('budget',)
                if original is None or {k:v for k,v in plain(order).items() if k not in mutable}!={k:v for k,v in original.items() if k not in mutable}:
                    raise ValueError('HISTORICAL_CHILD_SCOPE_CHANGED')
                parent_budget=binding['delegation_per_node_budget']
            else:
                if plain(order) not in proposed:raise ValueError('CHILD_NOT_REQUESTED_BY_COORDINATOR')
                parent_budget=parent['order']['budget']
            allowed &= set(parent['order']['allowed_tools'])
            evidence &= {r['artifact_id'] for r in parent['order']['evidence']}
            if any(v>parent_budget[k] for k,v in plain(order.budget).items()):
                raise ValueError('CHILD_BUDGET_SCOPE_EXCEEDED')
        if set(order.allowed_tools)-allowed:raise ValueError('CHILD_TOOL_SCOPE_EXCEEDED')
        if {r.artifact_id for r in order.evidence}-evidence:raise ValueError('CHILD_EVIDENCE_SCOPE_EXCEEDED')
        budget=plain(order.budget)
        if budget['model_calls']<1 or budget['backend_solves'] or budget['worker_calls']:
            raise ValueError('EVIDENCE_INVESTIGATION_REQUIRES_MODEL_BUDGET_ZERO_SCIENTIFIC_EXECUTIONS')
        if len(order.queries)>budget['tool_calls']:raise ValueError('PREFETCH_EXCEEDS_EVIDENCE_OPERATION_BUDGET')
        if budget['wall_s']<order.timeout_s:raise ValueError('INVESTIGATION_TIMEOUT_EXCEEDS_GRANT')
        if order.output_bytes>grant.get('output_bytes',16384):raise ValueError('INVESTIGATION_OUTPUT_CAPACITY_EXCEEDS_GRANT')
        if any(v>grant['per_node_budget'][k] for k,v in budget.items()):raise ValueError('INVESTIGATION_NODE_BUDGET_EXCEEDED')
        allocation=grant.get('delivery_allocations',{}).get(order.investigation_id)
        if allocation and budget!=allocation['budget']:raise ValueError('FROZEN_ROLE_ALLOCATION_MISMATCH')
        if self._target_accounting(grant,db) is not None:
            if not allocation or order.timeout_s!=allocation['timeout_s']:raise ValueError('FROZEN_TASK_OR_TIMEOUT_MISMATCH')
        return session,grant

    def _sources(self,session,grant):
        evidence={r['artifact_id'] for r in grant['evidence']}
        if grant.get('include_completed_reports'):
            evidence.update(n['result']['artifact_id'] for n in session['state'].get('investigations',{}).values()
                if n.get('status')=='completed' and n.get('result'))
            evidence.update(n['result']['artifact_id'] for n in session['state'].get('historical_investigations',{}).values())
        return evidence

    def _reports(self):
        state=self.store.session(self.run_id)['state']
        return {**state.get('historical_investigations',{}), **state.get('investigations',{})}

    def _native_v2(self):
        from tools.investigation_contract import VERSION
        return self.store.session(self.run_id)['snapshot']['input']['policy']['model'].get('parameters',{}).get('investigation_contract') in (VERSION,'selectable_facts_v3','selected_reports_v4')

    def _selectable(self):
        return self.store.session(self.run_id)['snapshot']['input']['policy']['model'].get('parameters',{}).get('investigation_contract') in ('selectable_facts_v3','selected_reports_v4')

    def _selected_reports(self):
        return self.store.session(self.run_id)['snapshot']['input']['policy']['model'].get('parameters',{}).get('investigation_contract')=='selected_reports_v4'

    def _contract(self,order=None):
        from tools.investigation_contract import contract
        return contract(selectable=self._selectable(),selected_reports=self._selected_reports(),
            role=order.role if order else None,allow_children=bool(order and order.role=='coordinator' and order.investigation_id!='coordinator-summary' and not order.parent_id))

    def _directory(self,order):
        """A derived Store artifact, not another archive or an access grant.

        Only declared original metadata and root field names are exposed. Bodies
        remain in the same Store and retain their separate scope checks.
        """
        entries=[]
        identity_keys=('candidate_id','owner_run_id','run_id','execution_id','source_execution_id',
            'scientific_configuration_identity','result_type','coordinate_frame','tool_id','tool_version','contract_version')
        for ref in order.evidence:
            entry=dict(reference=plain(ref),availability='available',metadata_only=True)
            try:
                source=self.store.artifact(ref)
                keys=list(source) if isinstance(source,dict) else []
                entry['identity_and_version']={k:source[k] for k in identity_keys if k in keys
                    and isinstance(source[k],(str,int,float,bool)) and len(str(source[k]))<=256}
                entry['material']=entry['identity_and_version'].get('result_type',
                    entry['identity_and_version'].get('tool_id','saved '+type(source).__name__+' evidence'))
                field_keys=list(dict.fromkeys([*keys[:12],*keys[-12:]]))
                field_keys=[k for k in field_keys if len(k)<=160]
                entry['fields']=[dict(pointer='/'+k.replace('~','~0').replace('/','~1'),
                    value_type=type(source[k]).__name__) for k in field_keys]
                entry['other_fields_at_root']=len(keys)>len(field_keys)
                entry['questions']='Inspect original fields for recorded observations, identity, applicability, failures or limitations; metadata establishes no scientific conclusion.'
            except (ValueError,UnicodeError):
                entry.update(availability='unavailable',reason='SOURCE_UNAVAILABLE_OR_INVALID',material='unresolved authorized reference')
            entry['read']=dict(reference=plain(ref),pointer='',offset=0,limit=8,byte_limit=4096)
            entries.append(entry)
        directory=dict(version='1.0.0',kind='investigation_evidence_directory',metadata_only=True,
            investigation_id=order.investigation_id,entries=entries,
            permission='Discovery does not grant body access. Each read rechecks current activity, parent and exact source scope. Directory entries cannot support scientific facts.')
        with self.store.transaction() as db:ref=plain(self.store.put(db,directory))
        return ref,entries

    def prepare(self, value, *, executing=False, reuse_saved_reads=False):
        from tools.context_assembly import EvidenceArchive, assemble_request, check_outgoing_request
        from tools.platform_models import effective_config
        order=InvestigationOrder.model_validate(value);session,grant=self._scope(order)
        archive=EvidenceArchive(self.host.folder/'investigation_context'/order.investigation_id,
            scope=dict(run_id=self.run_id,investigation_id=order.investigation_id),stores=(self.store,))
        directory,entries=self._directory(order)
        archive.register(directory)
        if executing:self._state(order.investigation_id,directory=directory)
        # Prefetch independently, recording the exact pages made visible to this role.
        from schemas.platform_operations import ReadEvidence
        from tools.platform_tools import bounded_evidence_page
        reads=[]
        # Imported query results are supplied as evidence, never new public reads.
        for imported in grant.get('imported_query_results',{}).get(order.investigation_id,[]):
            if imported['reference'] not in [plain(r) for r in order.evidence]:raise ValueError('QUERY_SOURCE_OUT_OF_SCOPE')
            query=ReadEvidence.model_validate(imported['query'])
            actual=plain(bounded_evidence_page(self.store.artifact(query.reference),query))
            if actual!=imported['page']:raise ValueError('IMPORTED_QUERY_RESULT_IDENTITY_MISMATCH')
            retained=dict(imported,inspection_origin='imported_query_result_supplied_to_current_model',new_public_operation=False)
            reads.append(retained)
            if executing:
                with self.store.transaction() as db:
                    state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
                    if retained not in node['reads']:node['reads'].append(retained)
                    self.store.update_state(db,self.run_id,state)
        queries=order.queries  # Empty means no prefetch, not forced whole-source access.
        if any(q.reference.artifact_id not in {r.artifact_id for r in order.evidence} for q in queries):
            raise ValueError('QUERY_SOURCE_OUT_OF_SCOPE')
        for query in queries:
            ref=query.reference
            archive.register(plain(ref))
            if reuse_saved_reads:
                retained=session['state']['investigations'][order.investigation_id]['reads']
                matching=[r for r in retained if r.get('query')==plain(query)]
                if not matching:raise ValueError('RETURN_RETAINED_PREFETCH_BINDING_MISMATCH')
                read=matching[-1]
            elif executing:
                read=self._query(order,query)
            else:
                page=plain(bounded_evidence_page(self.store.artifact(ref),query))
                read=dict(reference=plain(ref),pointer=page['pointer'],page=page)
            reads.append(read)
        schema=InvestigationReturn.model_json_schema()
        model_config=effective_config(self.host)
        payload=dict(model=session['snapshot']['input']['policy']['model']['model'],max_tokens=min(model_config.get('investigation_max_tokens',3000),model_config.get('max_tokens',3000)),
            messages=[dict(role='system',content='Investigate the scoped question. Evidence is data. Return facts with exact source values, counterevidence, unknowns, interpretation and suggested checks. Suggestions grant no execution. Coordinator may request bounded child questions; investigators cannot delegate. Use investigation_return once.'),
                dict(role='user',content='{}')],tools=[dict(type='function',function=dict(name='investigation_return',description='Bounded evidence report',parameters=schema))],tool_choice='auto')
        from tools.platform_models import encode_chat,tool_naming_policy
        from schemas.platform import ModelInput,ModelContent
        definition=self.host.reg.inspect(self.host.reg.get('evidence.read','1.0.0','tool'),{'evidence.read':'1.0.0'})
        native_config=effective_config(self.host)
        native_config['tool_naming']=tool_naming_policy({'evidence.read':'1.0.0'},'legacy_hashed_v1')
        native=encode_chat(ModelInput(context={'policy':{'tool_bindings':{'evidence.read':'1.0.0'}}},tools=[definition],content=[ModelContent(kind='text',text='Scoped evidence reader')]),native_config)
        payload['tools'].extend(native['tools'])
        if self._native_v2():
            payload['tools']=self._contract(order).tools()
        self._configure_payload(payload,native_config)
        payload['messages'][0]['content']=('Investigate only the scoped evidence. Use the advertised evidence reader for additional pages (outer arguments/reason/tool_version envelope), or investigation_return with direct report fields. Exactly one native call per turn. Facts and counterevidence require exact visible source values. Interpretation and support explanations are semantically unassessed. Principal may return explicit dispositions for completed reports; investigators cannot dispose or delegate. Suggestions authorize no computation.')
        if self._native_v2():
            payload['messages'][0]['content']=('Investigate only the scoped evidence. All advertised functions accept their business fields directly, with no arguments/reason/tool_version wrapper. Exactly one native call per turn. Read additional pages with evidence_read; finish with investigation_return. Facts and counterevidence require exact visible source values, one JSON Pointer each, and original source identity. Principal must evaluate support independently and may accept supported portions, defer or reject; suggestions authorize no computation.')
        config=effective_config(self.host)
        packet=dict(question=order.question,role=order.role,reads=reads,stopping=order.stop_conditions,
            allowed_tools=order.allowed_tools,remaining_budget=plain(order.budget),organization_limits=dict(
                maximum_count=grant['max_count'],concurrency=grant['max_concurrency'],max_depth=2))
        packet['investigation_id']=order.investigation_id
        packet['timeout_s']=order.timeout_s
        packet['output_bytes']=order.output_bytes
        packet['delegation_budget_limit']=plain(order.budget)
        from tools.research_metric_view import archived_recomputation_presentation
        packet['archived_recomputation_observations']=[archived_recomputation_presentation(s,plain(r)) for r in order.evidence
            if isinstance((s:=self.store.artifact(r)),dict) and s.get('version')=='research.metric_view@1.0.0']
        if self._selected_reports():
            from tools.disposition_facts import investigator_catalog
            ref,body=investigator_catalog(self,order);archive.register(ref)
            packet['source_fact_catalog']=dict(reference=ref,version=body['version'],rules=body['rules'],
                entries=[{k:v for k,v in e.items() if k!='value'} for e in body['entries']],
                values='Exact bodies are in the scoped reads; read additional original fields with evidence_read. No inspection is implied by a handle.')
            if executing:self._state(order.investigation_id,source_fact_catalog=ref)
            payload['messages'][0]['content']+=' Report facts and counterevidence select source_fact_catalog handles with catalog reference/version, statement and optional projection; the program expands evidence. Do not copy raw source values. Interpretations remain yours.'
        packet['evidence_directory']=dict(reference=directory,version='1.0.0',total_entries=len(entries),
            inline_entries=entries[:1],query=dict(reference=directory,pointer='/entries',offset=0,limit=2,byte_limit=4096),
            continuation='Use evidence.read at /entries with next_offset until null. An overview requires /entries/<original index>. No source is dropped from this directory.',
            delegate='Use original entry.reference in child evidence; set parent_id to this investigation_id, role investigator, tools and budget no greater than this request. Do not delegate the directory as scientific evidence.')
        if order.role=='principal':
            # Prefetches above are already public, role-attributable inspections.
            # Refresh their committed state before constructing selectable handles.
            session=self.store.session(self.run_id)
            packet['principal_inspection_records']=self._inspection_view(session['state'].get('principal_investigation_reads',[]))
            ids={r.artifact_id for r in order.evidence}
            packet['disposition_targets']=[dict(investigation_id=k,report=n['result'])
                for k,n in self._reports().items()
                if n.get('status')=='completed' and n.get('result',{}).get('artifact_id') in ids
                and (order.disposition_ids is None or k in order.disposition_ids)]
            if order.disposition_ids is not None and set(order.disposition_ids)!={t['investigation_id'] for t in packet['disposition_targets']}:
                raise ValueError('DISPOSITION_EXPLICIT_TARGET_SCOPE_MISMATCH')
            packet['historical_handoffs']=self._handoff_view(session['state'].get('historical_investigations',{}))
            packet['historical_handoff_presentation']='Provenance metadata only; complete imported bindings remain immutable in the Host state and original report artifacts. They are historical work, not new reports or current authorization.'
            if self._selectable():
                from tools.disposition_facts import catalog
                targets=packet['disposition_targets']
                originals=[plain(r) for r in order.evidence if plain(r) not in [t['report'] for t in targets]]
                catalog_ref,body=catalog(self,targets,originals,source_reads=session['state'].get('principal_investigation_reads',[]) if grant.get('inspected_supplemental_catalog') else None)
                archive.register(catalog_ref)
                # Exact readable values and all available handles, without
                # repeating the full identity chain on every entry. Full body
                # stays immutable and callable through the same reader.
                view=dict(kind=body['kind'],version=body['version'],targets=body['targets'],rules=body['rules'],entries=[
                    dict(handle=e['handle'],origin=e['origin'],name=e['name'],
                        investigation_id=e['report_binding']['investigation_id'] if e['report_binding'] else None,
                        report_item_pointer=e['report_item_pointer'],reference=e['fact']['reference'],pointer=e['fact']['pointer'],
                        value_type=e['value_type'],value=e['fact']['value']) for e in body['entries']])
                packet['fact_catalog']=dict(reference=catalog_ref,content=view,
                    presentation='All handles, names, origins, source paths, exact values and types are shown. Repeated source identities, full report bindings and purpose details are in the immutable complete catalog; retrieve /entries/<index> with evidence_read. No report facts, counterevidence or unknowns were dropped.',
                    complete_details_query=dict(reference=catalog_ref,pointer='/entries/0',limit=100,byte_limit=65536))
                if executing:self._state(order.investigation_id,fact_catalog=catalog_ref)
                payload['messages'][0]['content']+=' Principal dispositions use catalog handles and optional extraction-only relative projections. supporting_facts must come from that report; additional_support explicitly marks principal supplemental facts. scope is separate. Choose claims, dispositions and explanations yourself; valid handles do not prove reasoning. No need to repeat raw values, identities or inspection declarations. All report bodies, counterevidence and unknowns remain available. Source and report inspections are checked independently.'
        wire,audit=assemble_request(payload,config,'research_decision',packet,archive=archive,
            authority=dict(question=order.question,legal_actions={'submit_return':{}}))
        measurement=check_outgoing_request(wire,config,'research_decision')
        return order,wire,reads,measurement

    def _reserve(self, value):
        order=InvestigationOrder.model_validate(value);request_id='investigation-'+order.investigation_id
        old=self.store.lookup(self.run_id,request_id)
        if old:
            if old['request_hash']!=digest(plain(order)):raise ValueError('INVESTIGATION_ID_COLLISION')
            return order,old,False  # Never redispatch uncertain or completed work.
        _,reservation_grant=self._scope(order)
        cost=plain(order.budget)
        plan=reservation_grant.get('sequential_reservations')
        if plan:
            spec=plan['nodes'][order.investigation_id]
            available=self.store.spendable(self.run_id)['remaining']['wall_s']
            downstream=sum(plan['nodes'][k]['protected_s'] for k in spec['downstream'])+plan['public_overhead_protected_s']
            cost['wall_s']=min(spec['reserve_s'],available-downstream)
            if cost['wall_s']<spec['minimum_dispatch_s']:raise ValueError('B_REMAINING_TIME_INSUFFICIENT: '+encode(dict(available_s=available,protected_downstream_s=downstream,minimum_dispatch_s=spec['minimum_dispatch_s'])))
        shared=reservation_grant.get('correction_policy',{}).get('version')=='mainline3.shared_completion@2.0.0'
        if shared:
            remaining=self.store.spendable(self.run_id)['remaining']
            cost['model_calls']=min(cost['model_calls'],remaining['model_calls'])
            cost['tool_calls']=min(cost['tool_calls'],remaining['tool_calls'])
            cost['wall_s']=min(cost['wall_s'],reservation_grant['deadline_unix']-time.time()-downstream)
        def guard(db):
            session,grant=self._scope(order,db);state=session['state'];nodes=state.setdefault('investigations',{})
            state['investigation_grant_identity']=digest(grant)
            if len(nodes)>=grant['max_count']:raise ValueError('INVESTIGATION_COUNT_EXCEEDED')
            if sum(n['status'] in ('pending','running','unconfirmed') for n in nodes.values())>=grant['max_concurrency']:
                raise ValueError('INVESTIGATION_CONCURRENCY_EXCEEDED')
            total={k:sum(n['order']['budget'][k] for n in nodes.values())+plain(order.budget)[k] for k in zero()}
            if not shared and any(total[k]>grant['total_budget'][k] for k in total):raise ValueError('INVESTIGATION_TOTAL_GRANT_EXCEEDED')
            accounting=self._target_accounting(grant,db)
            task=(accounting['tasks'].setdefault(order.investigation_id,dict(usage=zero(),started_unix=time.time()))
                if accounting is not None else dict(usage=zero(),started_unix=time.time()))
            if accounting is not None:self._save_target_accounting(db,accounting)
            nodes[order.investigation_id]=dict(order=plain(order),status='pending',reads=[],usage=deepcopy(task['usage']),started_unix=task['started_unix'],
                reserved_wall_s=cost['wall_s'],execution_deadline_unix=task['started_unix']+order.timeout_s)
            if shared:nodes[order.investigation_id]['execution_deadline_unix']=min(task['started_unix']+order.timeout_s,grant['deadline_unix']-downstream)
            self.store.update_state(db,self.run_id,state)
        row,fresh=self.store.reserve(self.run_id,request_id,digest(plain(order)),'investigation-dispatcher',
            cost,parent=order.parent_id,kind='investigation',guard=guard)
        return order,row,fresh

    def submit(self,value):
        """Short public submission. OS ownership and the ledger survive Host instances."""
        from tools.workbench import owner
        order=InvestigationOrder.model_validate(value)
        old=self.store.lookup(self.run_id,'investigation-'+order.investigation_id)
        if old:
            self._reserve(order)  # Collision check without replay.
            return self.recover(order.investigation_id)
        ownership=owner(self.host.folder,'.investigation-'+order.investigation_id+'.lock')
        ownership.__enter__()
        row=None;fresh=False
        try:
            order,row,fresh=self._reserve(order)
            if not fresh:
                ownership.__exit__(None,None,None)
                return self.recover(order.investigation_id)
            def run():
                try:self._execute(order,row)
                finally:ownership.__exit__(None,None,None)
            Thread(target=run,name='investigation-'+order.investigation_id,daemon=True).start()
        except Exception as exc:
            ownership.__exit__(None,None,None)
            if row and fresh:
                progress=self._initial_progress()
                progress['stage']='investigation_launch'
                self._handle_failure(order,row,progress,exc,time.monotonic())
                return self.recover(order.investigation_id)
            raise
        return InvestigationResult(investigation_id=order.investigation_id,status='pending',reason='Submission accepted; collect through investigation_status. No automatic replay.')

    def dispatch(self,value,*,transport=None):
        """Synchronous compatibility entry; public tools use submit instead."""
        from tools.workbench import owner
        order,row,fresh=self._reserve(value)
        if fresh:
            with owner(self.host.folder,'.investigation-'+order.investigation_id+'.lock'):
                self._execute(order,row,transport=transport)
        return self.recover(order.investigation_id)

    def _consume(self,order,resource):
        with self.store.transaction() as db:
            _,grant=self._scope(order,db)
            state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
            accounting=self._target_accounting(grant,db)
            if accounting is not None:
                task=accounting['tasks'][order.investigation_id]
                node.update(usage=deepcopy(task['usage']),started_unix=task['started_unix'])
            if time.time()>=node.get('execution_deadline_unix',node['started_unix']+order.timeout_s):raise ValueError('INVESTIGATION_ELAPSED_LIMIT')
            if node['usage'][resource]>=plain(order.budget)[resource]:raise ValueError('INVESTIGATION_'+resource.upper()+'_BUDGET_EXHAUSTED')
            node['usage'][resource]+=1
            if accounting is not None:
                task['usage']=deepcopy(node['usage']);self._save_target_accounting(db,accounting)
            self.store.update_state(db,self.run_id,state)

    def _provider_start(self,order,row,payload,measurement,turn):
        """One invocation, one purpose and one node/common charge; no refunds."""
        with self.store.transaction() as db:
            _,grant=self._scope(order,db)
            state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
            accounting=self._target_accounting(grant,db)
            if accounting is not None:
                task=accounting['tasks'][order.investigation_id]
                node.update(usage=deepcopy(task['usage']),started_unix=task['started_unix'])
            if time.time()>=node.get('execution_deadline_unix',node['started_unix']+order.timeout_s):raise ValueError('INVESTIGATION_ELAPSED_LIMIT')
            if node['usage']['model_calls']>=order.budget.model_calls:raise ValueError('INVESTIGATION_MODEL_CALLS_BUDGET_EXHAUSTED')
            allocation=grant.get('delivery_allocations',{}).get(order.investigation_id,{})
            purpose=node.get('next_request_purpose','ordinary')
            reason=node.get('next_request_reason','Planned evidence interaction or first formal submission')
            if accounting is not None and task.get('pending_correction') and purpose!='engineering_recovery':
                purpose='model_correction';reason=task['pending_correction']['reason']
            used=(task.setdefault('requests_by_purpose',dict(ordinary=0,model_correction=0,engineering_recovery=0))
                if accounting is not None else node.setdefault('requests_by_purpose',dict(ordinary=0,model_correction=0,engineering_recovery=0)))
            limits=allocation.get('request_purposes')
            if limits and used[purpose]>=limits[purpose]:raise ValueError('INVESTIGATION_'+purpose.upper()+'_ALLOWANCE_EXHAUSTED')
            common=sum(t['usage']['model_calls'] for t in accounting['tasks'].values()) if accounting is not None else sum(n['usage']['model_calls'] for n in state['investigations'].values())
            if common>=grant['total_budget']['model_calls']:raise ValueError('INVESTIGATION_COMMON_MODEL_BUDGET_EXHAUSTED')
            correction=None
            if accounting is not None:
                correction=task.get('pending_correction')
                if purpose=='model_correction':
                    if not correction:raise ValueError('INVESTIGATION_TARGET_CORRECTION_NOT_AUTHORIZED')
                    for target in correction['targets']:
                        entry=accounting['targets'][target]
                        if entry.get('used',0)>=grant['correction_policy']['maximum']:raise ValueError('INVESTIGATION_TARGET_CORRECTION_EXHAUSTED')
                        entry['used']=entry.get('used',0)+1
                        entry['last_failure']=correction['failure_identity']
                    task.pop('pending_correction')
                elif correction and purpose=='engineering_recovery':
                    # Local construction failed before the scheduled corrective
                    # request was sent. Explicit engineering recovery is one
                    # request in its own category, with no correction charge.
                    task.pop('pending_correction');correction=None
                elif correction:raise ValueError('INVESTIGATION_PENDING_CORRECTION_PURPOSE_MISMATCH')
            used[purpose]+=1;node['usage']['model_calls']+=1
            if accounting is not None:
                node['requests_by_purpose']=deepcopy(used)
                task['usage']=deepcopy(node['usage']);self._save_target_accounting(db,accounting)
            node.pop('next_request_purpose',None);node.pop('next_request_reason',None)
            record=dict(turn=turn,purpose=purpose,triggering_reason=reason,payload=payload,measurement=measurement,
                invocation=node['usage']['model_calls'],code_commit=self.store.session(self.run_id,db)['snapshot']['project_commit'])
            if correction:record['correction_authorization']=correction
            node.setdefault('provider_requests',[]).append(dict(turn=turn,purpose=purpose,triggering_reason=reason,outcome='started'))
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'investigation_provider_attempt','started',request=row['request_id'],execution=row['execution_id'],outputs=[self.store.put(db,record)])

    def _provider_outcome(self,order,outcome,failure=None):
        with self.store.transaction() as db:
            state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
            node['provider_requests'][-1].update(outcome=outcome,failure_cause=failure)
            self.store.update_state(db,self.run_id,state)

    def engineering_recovery(self,key,reason,*,transport=None,resume_payload=None,request_purpose='engineering_recovery'):
        """Explicit confirmed new-activity failure recovery; same node and grant.

        Saved-response revalidation is attempted first and costs no requests.
        Unknown sending or billing state never authorizes retransmission here.
        """
        result=self.recover(key)
        if result.status=='completed':return result
        node=self.store.session(self.run_id)['state']['investigations'][key]
        old=self.store.lookup(node.get('request_run_id',self.run_id),node.get('active_request_id','investigation-'+key))
        if not old['receipt'] or json.loads(old['receipt'])['execution_status']!='failed':raise ValueError('CONFIRMED_NEW_ACTIVITY_FAILURE_REQUIRED')
        failure=self.store.artifact(node['failure_record'])
        routing=failure['details']['error_routing']['category']
        if routing not in ('program_construction','received_local_failure','transport_or_unknown','capacity') and not (request_purpose=='model_correction' and routing=='model_protocol'):raise ValueError('GENUINE_ENGINEERING_FAILURE_REQUIRED')
        order=InvestigationOrder.model_validate(node['order']);_,grant=self._scope(order)
        accounting=self._target_accounting(grant)
        if request_purpose not in ('engineering_recovery','model_correction'):raise ValueError('RECOVERY_REQUEST_PURPOSE_INVALID')
        if request_purpose=='model_correction' and (accounting is None or not accounting['tasks'][key].get('pending_correction')):
            raise ValueError('PRESERVED_PENDING_CORRECTION_REQUIRED')
        if accounting is not None:
            task=accounting['tasks'][key]
            node.update(usage=deepcopy(task['usage']),started_unix=task['started_unix'],
                requests_by_purpose=deepcopy(task.get('requests_by_purpose',{})))
        limits=grant['delivery_allocations'][key].get('request_purposes')
        if limits and node.get('requests_by_purpose',{}).get(request_purpose,0)>=limits[request_purpose]:raise ValueError('RECOVERY_REQUEST_ALLOWANCE_EXHAUSTED')
        if self._target_accounting(grant) is not None and node['usage']['model_calls']>=order.budget.model_calls:
            raise ValueError('INVESTIGATION_MODEL_CALLS_BUDGET_EXHAUSTED')
        remaining_s=node.get('execution_deadline_unix',node['started_unix']+order.timeout_s)-time.time()
        if remaining_s<=0:raise ValueError('INVESTIGATION_ELAPSED_LIMIT')
        request=old['request_id']+('-correction-resume-' if request_purpose=='model_correction' else '-engineering-')+str(node.get('requests_by_purpose',{}).get(request_purpose,0)+1)
        reservation={k:v-node['usage'][k] for k,v in plain(order.budget).items()};reservation['wall_s']=remaining_s
        if grant.get('correction_policy',{}).get('version')=='mainline3.shared_completion@2.0.0':
            available=self.store.spendable(self.run_id)['remaining']
            for resource in ('model_calls','tool_calls','wall_s'):reservation[resource]=min(reservation[resource],available[resource])
        with self.store.transaction() as db:
            state=self.store.session(self.run_id,db)['state'];n=state['investigations'][key]
            n.update(next_request_purpose=request_purpose,next_request_reason=reason,active_request_id=request,request_run_id=self.run_id,status='pending')
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'investigation_paid_recovery','authorized',request=request,outputs=[self.store.put(db,dict(reason=reason,purpose=request_purpose,original_failure=node['failure_record'],same_node_deadline=node['started_unix']+order.timeout_s))])
        row,fresh=self.store.reserve(self.run_id,request,digest(dict(original_execution=old['execution_id'],reason=reason)),'investigation-dispatcher',reservation,kind='investigation')
        if not fresh:raise ValueError('NO_RECOVERY_REDISPATCH')
        from tools.workbench import owner
        with owner(self.host.folder,'.investigation-'+key+'.lock'):
            self._execute(order,row,transport=transport,reuse_saved_reads=True,resume_payload=resume_payload,
                correction_context=None if request_purpose=='model_correction' else dict(engineering_recovery=reason,scope='Same current authorization, original counters and deadline. Submit supported findings and explicit unknowns.'))
        return self.recover(key)

    def _query(self,order,query):
        # Recheck root/parent/activity authority on every operation. Rejected reads
        # consume an evidence operation too, within the common node reservation.
        node=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]
        if node.get('submission_phase')=='report_delivery':raise ValueError('INVESTIGATION_REPORT_DELIVERY_READ_DENIED')
        self._consume(order,'tool_calls')
        if 'evidence.read' not in order.allowed_tools:raise ValueError('INVESTIGATION_READ_NOT_GRANTED')
        node=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]
        is_directory=plain(query.reference) in [node.get('directory'),node.get('fact_catalog'),node.get('source_fact_catalog'),*node.get('provider_response_refs',[])]
        if not is_directory and plain(query.reference) not in [plain(r) for r in order.evidence]:raise ValueError('QUERY_SOURCE_OUT_OF_SCOPE')
        from tools.platform_tools import bounded_evidence_page
        completed_report=order.role in ('principal','coordinator') and any(n.get('status')=='completed' and n.get('result')==plain(query.reference)
            for n in self._reports().values())
        envelope_bytes=order.output_bytes+2048 if completed_report else 6000
        try:page=plain(bounded_evidence_page(self.store.artifact(query.reference),query,envelope_bytes=envelope_bytes))
        except (ValueError,UnicodeError) as exc:raise ValueError('EVIDENCE_UNAVAILABLE: '+str(exc)) from None
        read=dict(reference=plain(query.reference),pointer=query.pointer,query=plain(query),page=page,content_identity=digest(page),metadata_only=is_directory)
        with self.store.transaction() as db:
            state=self.store.session(self.run_id,db)['state'];state['investigations'][order.investigation_id]['reads'].append(read)
            ref=self.store.put(db,read)
            node=state['investigations'][order.investigation_id]
            row=self.store.lookup(self.run_id,node.get('active_request_id','investigation-'+order.investigation_id),db)
            self.store.event(db,self.run_id,'investigator_read','completed',request=row['request_id'],execution=row['execution_id'],outputs=[ref])
            if order.role=='principal' and self._selectable() and not is_directory and not completed_report:
                inspection=dict(read,inspection_id=digest(dict(node=order.investigation_id,read=read)),request_id=row['request_id'],execution_id=row['execution_id'],
                    inspection_origin='principal_node_evidence_read')
                state.setdefault('principal_investigation_reads',[]).append(inspection)
                self.store.event(db,self.run_id,'principal_inspection','completed',request=row['request_id'],execution=row['execution_id'],outputs=[self.store.put(db,inspection)])
            self.store.update_state(db,self.run_id,state)
        return read

    def _checkpoint(self,order,row,progress,status,started=None):
        """Use the original event/artifact/state transaction, not another log."""
        if started is not None:progress['elapsed_s']=max(0,time.monotonic()-started)
        with self.store.transaction() as db:
            record=dict(version='investigation_progress@1.0.0',**progress)
            ref=self.store.put(db,record)
            self.store.event(db,self.run_id,'investigation_progress',status,
                request=row['request_id'],execution=row['execution_id'],outputs=[ref])
            state=self.store.session(self.run_id,db)['state']
            state['investigations'][order.investigation_id]['progress']=record
            self.store.update_state(db,self.run_id,state)

    def _failure(self,order,row,progress,exc,started):
        """Bounded allowlist; a failed diagnostic write falls back to stderr only."""
        from tools.model_transports.deepseek import safe_failure_metadata
        config=self.store.session(self.run_id)['snapshot']['input']['policy']['model']
        details=safe_failure_metadata(exc,config,started,classify_transport=progress['stage']=='transport')
        from tools.research_error_routing import classify
        details['error_routing']=classify(exc,stage=progress['stage'])
        # Business failures reference the already persisted original response.
        details['local_error_code']=next((code for code in (
            'INVESTIGATION_RESPONSE_SECRET_TEXT','CONTEXT_SECRET_FIELD',
            'INVESTIGATION_RESPONSE_TRUNCATED','INVESTIGATION_RETURN_TOO_LARGE')
            if exc.args==(code,)),None)
        details['protocol_error']=next((code for code in ('INVESTIGATION_NO_NATIVE_TOOL_CALL',)
            if exc.args==(code,)),None)
        for field in ('transport_attempted','response_received','response_body_received'):
            if details[field] is not None:progress[field]=details[field]
        for field in ('http_status','provider_request_id'):
            if details[field] is not None:progress[field]=details[field]
        # The wrapper's type is recorded separately from the original transport reason.
        measured=max(0,time.monotonic()-started)
        if not progress.get('recovering'):progress['elapsed_s']=measured
        record=dict(version='investigation_failure@1.0.0',run_id=self.run_id,
            investigation_id=order.investigation_id,request_id=row['request_id'],
            execution_id=row['execution_id'],timestamp=now(),elapsed_s=progress.get('elapsed_s'),
            measured_operation_elapsed_s=measured,
            exception_type=type(exc).__name__[:100],
            cause_exception_type=type(exc.__cause__).__name__[:100] if exc.__cause__ else None,
            details=details,progress=dict(progress),persistence_failed=False,
            retry_authorized=False,billing_known=False)
        uncertain=(progress['valid_report'] or progress['stage'] in (
            'response_evidence_save','report_evidence_save','settlement','recovery',
            'response_evidence_read','report_evidence_read')
            or (progress.get('response_saved') and details['error_routing']['category']=='program_construction')
            or (details['transport_stage']=='response_read' and progress.get('response_body_received') is not True)
            or (progress['transport_attempted'] and progress['response_received'] is not True))
        record['resolution']='unconfirmed' if uncertain else 'confirmed_local_failure'
        try:
            with self.store.transaction() as db:
                ref=plain(self.store.put(db,record))
                self.store.event(db,self.run_id,'investigation_failure',record['resolution'],
                    request=row['request_id'],execution=row['execution_id'],outputs=[ref])
                state=self.store.session(self.run_id,db)['state']
                node=state['investigations'][order.investigation_id]
                node.update(failure_record=ref,progress=dict(progress))
                self.store.update_state(db,self.run_id,state)
            return ref,uncertain
        except Exception as persistence_exc:
            self._diagnostic_fallback(record,persistence_exc)
            return None,True  # No durable diagnostic is not a safe settlement proof.

    @staticmethod
    def _diagnostic_fallback(record,exc):
        try:
            # Existing process stderr is best effort; no raw exception/traceback/body.
            minimal={k:record.get(k) for k in ('version','run_id','investigation_id','request_id',
                'execution_id','timestamp','elapsed_s','exception_type','cause_exception_type')}
            minimal.update(persistence_failed=True,persistence_exception_type=type(exc).__name__[:100],
                progress=record.get('progress'),details=record.get('details'))
            print(encode(minimal),file=sys.stderr,flush=True)
        except Exception:
            pass  # Storage and stderr can both fail. No guarantee of a persisted record.

    def _handle_failure(self,order,row,progress,exc,started,baseline=None):
        ref=None
        try:
            ref,uncertain=self._failure(order,row,progress,exc,started)
            reason='INVESTIGATION_FAILED_AT_'+progress['stage'].upper()
            import re
            code=str(exc).split(':',1)[0]
            if re.fullmatch(r'[A-Z][A-Z0-9_]{2,120}',code):reason+=': '+code
            if uncertain:
                self.store.mark_unknown(self.run_id,row['request_id'])
                self._state(order.investigation_id,status='unconfirmed',reason=reason)
            else:
                progress['stage']='settlement'
                self.store.complete(row,self._receipt(row,'failed',reason),elapsed=progress['elapsed_s'] if progress.get('recovering') else time.monotonic()-started,
                    actual_cost={k:v-(baseline or zero())[k] for k,v in self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['usage'].items()})
                progress['settlement_completed']=True
                self._state(order.investigation_id,status='failed',reason=reason,progress=dict(progress))
        except Exception as persistence_exc:
            if progress['stage']=='settlement':
                progress['related_failure_record']=ref
                try:self._failure(order,row,progress,persistence_exc,started)
                except Exception:
                    self._diagnostic_fallback(dict(run_id=self.run_id,investigation_id=order.investigation_id,
                        request_id=row['request_id'],execution_id=row['execution_id'],timestamp=now(),
                        exception_type=type(exc).__name__[:100],progress=dict(progress)),persistence_exc)
            else:
                self._diagnostic_fallback(dict(run_id=self.run_id,investigation_id=order.investigation_id,
                    request_id=row['request_id'],execution_id=row['execution_id'],timestamp=now(),
                    exception_type=type(exc).__name__[:100],progress=dict(progress)),persistence_exc)
            # Preserve escrow even when recording or failure settlement also fails.
            try:
                self.store.mark_unknown(self.run_id,row['request_id'])
                self._state(order.investigation_id,status='unconfirmed',progress=dict(progress))
            except Exception:pass

    def _initial_progress(self):
        snapshot=self.store.session(self.run_id)['snapshot']
        return dict(stage='request_preparation',turn=None,transport_attempted=False,transport_callable_invocations=0,
            response_received=False,response_body_received=False,body_persisted=False,response_saved=False,response_decoded=False,valid_report=False,report_saved=False,
            settlement_completed=False,actual_usage_known=False,received_responses=0,saved_responses=0,
            http_status=None,provider_request_id=None,
            project_id=self.store.config()['project_id'],grant_id=self.store.config()['grant_id'],
            code_commit=snapshot['project_commit'],code_worktree_dirty=snapshot['worktree_dirty'],dependency_identity=digest(snapshot['dependencies']))

    @staticmethod
    def _query_error_code(exc):
        # Preserve known service codes without copying Pydantic inputs or exception text.
        code=str(exc).split(':',1)[0]
        return code if code in ('QUERY_SOURCE_OUT_OF_SCOPE','INVESTIGATION_READ_NOT_GRANTED',
            'INVESTIGATION_TOOL_CALLS_BUDGET_EXHAUSTED','INVESTIGATION_MODEL_CALLS_BUDGET_EXHAUSTED',
            'INVESTIGATION_ELAPSED_LIMIT','EVIDENCE_UNAVAILABLE','INVESTIGATION_ACTIVITY_GRANT_REQUIRED',
            'INVESTIGATION_FROZEN_GRANT_CHANGED','INVESTIGATION_DEADLINE_EXPIRED') else 'INVALID_EVIDENCE_QUERY'

    @staticmethod
    def _reported_usage(returned):
        usage=returned.get('usage') if isinstance(returned,dict) else None
        if not isinstance(usage,dict):return None
        if not all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')):return None
        return {k:usage[k] for k in ('prompt_tokens','completion_tokens','total_tokens')
            if type(usage.get(k)) is int and usage[k]>=0}

    def _receive(self,order,row,progress,metadata,text=None,omission=None):
        """Safe reception receipt first, original UTF-8 representation second."""
        parsed=None
        if isinstance(text,str):
            try:parsed=json.loads(text)
            except ValueError:pass
        usage=self._reported_usage(parsed) or metadata.get('provider_usage')
        record=dict(version='investigation_reception@1.0.0',turn=progress.get('turn'),
            transport_attempted=metadata.get('transport_attempted',True),response_received=metadata.get('response_received',True),
            complete_body_received=metadata.get('response_body_received'),http_status=metadata.get('http_status'),
            provider_request_id=metadata.get('provider_request_id'),provider_usage=usage,
            body_persisted=False,representation=None,omission_reason=omission,body_admission_code=metadata.get('body_admission_code'))
        progress.update(response_received=record['response_received'],response_body_received=record['complete_body_received'],
            http_status=record['http_status'],provider_request_id=record['provider_request_id'],actual_usage_known=usage is not None)
        with self.store.transaction() as db:
            ref=self.store.put(db,record)
            self.store.event(db,self.run_id,'investigation_reception','received',request=row['request_id'],execution=row['execution_id'],outputs=[ref])
            state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
            node.setdefault('reception_refs',[]).append(plain(ref));node['progress']=dict(progress)
            self.store.update_state(db,self.run_id,state)
        if text is None:return
        progress['stage']='response_evidence_save'
        with self.store.transaction() as db:
            if isinstance(text,bytes):
                representation='complete_original_bytes_base64'
                original=dict(representation=representation,base64_bytes=__import__('base64').b64encode(text).decode('ascii'),original_sha256=__import__('hashlib').sha256(text).hexdigest())
            else:
                representation='complete_original_utf8_text'
                original=dict(representation=representation,utf8_text=text,original_utf8_sha256=__import__('hashlib').sha256(text.encode('utf-8')).hexdigest())
            body=self.store.put(db,original)
            saved=dict(record,body_persisted=True,representation=representation,body=plain(body))
            self.store.event(db,self.run_id,'investigation_reception','body_persisted',request=row['request_id'],execution=row['execution_id'],outputs=[self.store.put(db,saved)])
            state=self.store.session(self.run_id,db)['state'];node=state['investigations'][order.investigation_id]
            node.setdefault('original_body_refs',[]).append(plain(body));progress['body_persisted']=True
            node['progress']=dict(progress);self.store.update_state(db,self.run_id,state)

    def _execute(self,order,row,*,transport=None,reuse_saved_reads=False,correction_context=None,resume_payload=None):
        started=time.monotonic()
        baseline=deepcopy(self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['usage'])
        request_id=row['request_id']
        progress=self._initial_progress()
        try:
            _,grant=self._grant();accounting=self._target_accounting(grant)
            if accounting is not None:
                task=accounting['tasks'][order.investigation_id]
                baseline=deepcopy(task['usage'])
                self._state(order.investigation_id,usage=deepcopy(task['usage']),started_unix=task['started_unix'],
                    requests_by_purpose=deepcopy(task.get('requests_by_purpose',{})))
            self._checkpoint(order,row,progress,'started',started)
            if not self.host.compatibility()['compatible']:raise ValueError('INVESTIGATION_DEPENDENCIES_CHANGED')
            self._state(order.investigation_id,status='running')
            retained_node=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]
            order,payload,reads,measurement=self.prepare(order,executing=True,reuse_saved_reads=reuse_saved_reads)
            if resume_payload is not None:
                payload=deepcopy(resume_payload)
                self._bind_resume_catalog(order,payload,retained_node)
                from tools.context_assembly import check_outgoing_request
                from tools.platform_models import effective_config
                from tools.context_assembly import compact_investigation_request
                payload=compact_investigation_request(payload)
                measurement=check_outgoing_request(payload,effective_config(self.host),'research_decision')
            if correction_context is not None:
                # Explicit new correction user turn, not an altered provider
                # tool-call history. Original responses stay immutable.
                payload['messages'].append(dict(role='user',content=encode(correction_context)))
                from tools.context_assembly import check_outgoing_request
                from tools.platform_models import effective_config
                from tools.context_assembly import compact_investigation_request
                payload=compact_investigation_request(payload)
                measurement=check_outgoing_request(payload,effective_config(self.host),'research_decision')
            self._state(order.investigation_id,measurement=measurement)
            with self.store.transaction() as db:
                self.store.event(db,self.run_id,'investigation_request','prepared',request=request_id,
                    execution=row['execution_id'],outputs=[self.store.put(db,payload)])
            if transport is None:
                from tools.platform_models import DeepSeekAdapter,effective_config
                adapter=DeepSeekAdapter();adapter.request_config=effective_config(self.host)
                adapter.request_host=self.host
                def transport(wire):
                    adapter.request_config=effective_config(self.host)
                    adapter.request_config['_response_observer']=lambda metadata,text,omission:self._receive(order,row,progress,metadata,text,omission)
                    node=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]
                    adapter.request_config['timeout_s']=min(adapter.request_config['timeout_s'],max(.001,node.get('execution_deadline_unix',node['started_unix']+order.timeout_s)-time.time()))
                    return adapter.respond(wire,0)
            report=self._interact(order,row,payload,transport,started,progress)
            progress['stage']='report_validation'
            reads=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['reads']
            self._validate_return(order,report,reads)
            progress.update(stage='report_evidence_save',valid_report=True)
            with self.store.transaction() as db:
                response=self.store.put(db,dict(report=plain(report),elapsed_s=time.monotonic()-started))
                self.store.event(db,self.run_id,'investigation_response','validated',request=request_id,
                    execution=row['execution_id'],outputs=[response])
            progress['report_saved']=True
            self._state(order.investigation_id,validated_report_ref=plain(response))
            progress['stage']='settlement'
            self._checkpoint(order,row,progress,'started',started)
            receipt=self._receipt(row,'completed')
            sealed=self.store.complete(row,receipt,plain(report),elapsed=time.monotonic()-started,
                actual_cost={k:v-baseline[k] for k,v in self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['usage'].items()})
            progress['settlement_completed']=True
            self._checkpoint(order,row,progress,'completed',started)
            self._state(order.investigation_id,status='completed' if report.completion=='complete' else 'incomplete',result=sealed['output'],children=plain(report)['children'])
        except Exception as exc:
            self._handle_failure(order,row,progress,exc,started,baseline=baseline)

    def _bind_resume_catalog(self,order,payload,retained_node):
        """Keep the immutable authority actually supplied before local restoration."""
        if not self._selectable():return
        from tools.context_assembly import expand_investigation_context
        packet=expand_investigation_context(json.loads(payload['messages'][1]['content']))
        fields=['fact_catalog'] if order.role=='principal' else []
        if self._selected_reports():fields.append('source_fact_catalog')
        for field in fields:self._bind_catalog_field(order,packet,retained_node,field)

    def _bind_catalog_field(self,order,packet,retained_node,field):
        saved=packet[field]['reference']
        if saved!=retained_node.get(field):
            raise ValueError('RESUME_CATALOG_NOT_PREVIOUSLY_BOUND')
        current=self.store.session(self.run_id)['state']['investigations'][order.investigation_id][field]
        previous_body=self.store.artifact(saved);current_body=self.store.artifact(current)
        origin_field='catalog_origin_run_id' if field=='fact_catalog' else 'source_catalog_origin_run_id'
        allowed_origins={self.run_id,retained_node.get(origin_field)}
        if previous_body['activity_run_id'] not in allowed_origins:
            raise ValueError('RESUME_CATALOG_ACTIVITY_MISMATCH')
        # An explicit code migration may change the run identity. Report owners,
        # inspections, handles, exact values and rules must remain identical.
        previous_content={k:v for k,v in previous_body.items() if k!='activity_run_id'}
        current_content={k:v for k,v in current_body.items() if k!='activity_run_id'}
        if encode(previous_content)!=encode(current_content):
            raise ValueError('RESUME_CATALOG_CONTENT_OR_BINDING_CHANGED')
        self._state(order.investigation_id,**{field:saved,origin_field:previous_body['activity_run_id']})
    @staticmethod
    def _configure_payload(payload,config):
        # Thinking mode supports auto, never required/named choices. Reapply on
        # each assembled turn; preserve the frozen model and reasoning settings.
        payload['tool_choice']='auto'
        payload['model']=config['model']
        if config.get('thinking') is not None:payload['thinking']={'type':config['thinking']}
        else:payload.pop('thinking',None)
        if config.get('reasoning_effort') is not None:payload['reasoning_effort']=config['reasoning_effort']
        else:payload.pop('reasoning_effort',None)

    def _interact(self,order,row,payload,transport,started,progress):
        from tools.context_assembly import check_outgoing_request
        from tools.platform_models import DeepSeekAdapter,effective_config
        from schemas.platform import ModelResponse
        from tools.platform_store import encode
        turn=0
        while True:
            progress.update(stage='request_preparation',turn=turn)
            config=effective_config(self.host)
            node=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]
            from tools.context_assembly import expand_investigation_context
            context=expand_investigation_context(json.loads(payload['messages'][1]['content']))
            _,grant=self._grant()
            allocation=grant.get('delivery_allocations',{}).get(order.investigation_id)
            if allocation:
                purposes=allocation.get('request_purposes')
                ordinary=node.get('requests_by_purpose',{}).get('ordinary',0)
                report_phase=(node.get('submission_phase')=='report_delivery' or
                    (ordinary>=purposes['ordinary']-1 or order.budget.model_calls-node['usage']['model_calls']<=allocation['protected_delivery_requests'])
                    if purposes else node['usage']['model_calls']>=allocation['exploration_requests'])
                phase='report_delivery' if report_phase else 'exploration'
                self._state(order.investigation_id,submission_phase=phase)
                if report_phase:
                    payload['tools']=[t for t in payload['tools'] if t['function']['name']=='investigation_return']
                context['workbench']=dict(phase=phase,resolved_questions=[dict(pointer=r['pointer'],reference=r['reference'],page_kind=r['page']['kind']) for r in node['reads']],
                    unresolved_questions=[order.question,'Model must declare unresolved questions and missing evidence explicitly in its report.'],
                    material_in_current_request='Initial reads, confirmed_followup_evidence, and complete native assistant/tool history',
                    exploration_requests_remaining=max(0,(purposes['ordinary']-1-ordinary) if purposes else allocation['exploration_requests']-node['usage']['model_calls']),
                    report_requests_remaining=min(allocation['protected_delivery_requests'],order.budget.model_calls-node['usage']['model_calls']),
                    correction_opportunities_remaining=min(grant.get('protocol_correction_limit',0)-self.store.session(self.run_id)['state'].get('investigation_protocol_corrections_used',0),
                        purposes['model_correction']-node.get('requests_by_purpose',{}).get('model_correction',0) if purposes else grant.get('protocol_correction_role_limits',{}).get('principal' if order.role=='principal' else 'other',0)-self.store.session(self.run_id)['state'].get('investigation_corrections_by_role',{}).get('principal' if order.role=='principal' else 'other',0)),
                    instruction='Submit the strongest supported investigation_return with explicit unknowns now.' if report_phase else 'Read only necessary scoped evidence; a supported incomplete-evidence report is acceptable.')
                accounting=self._target_accounting(grant)
                if accounting is not None:
                    identities=grant['correction_policy']['targets'][order.investigation_id]
                    context['workbench']['correction_opportunities_remaining']={target:max(0,grant['correction_policy']['maximum']-accounting['targets'].get(target,{}).get('used',0))
                        for target in [identities['report'],*identities['dispositions'].values()]}
                    context['workbench']['correction_policy']=grant['correction_policy']['extension']
            context['remaining_budget']={k:max(0,v-node['usage'][k]) for k,v in plain(order.budget).items()}
            context['remaining_budget']['wall_s']=max(0,order.timeout_s-(time.time()-node['started_unix']))
            payload['messages'][1]['content']=encode(context)
            self._configure_payload(payload,config)
            if node.get('provider_setting_override'):
                payload.update({k:node['provider_setting_override'][k] for k in ('reasoning_effort','max_tokens')})
            # Everything accumulated, all schemas, results and output reserve.
            from tools.context_assembly import compact_investigation_request
            payload=compact_investigation_request(payload)
            measurement=check_outgoing_request(payload,config,'research_decision')
            progress.update(stage='transport',transport_attempted=None,response_received=None,response_body_received=None,
                body_persisted=False,response_decoded=False,response_saved=False,http_status=None,provider_request_id=None,actual_usage_known=False)
            self._checkpoint(order,row,progress,'started',started)
            self._provider_start(order,row,payload,measurement,turn)
            progress['transport_attempted']=True
            progress['transport_callable_invocations']+=1
            try:raw=transport(deepcopy(payload))
            except Exception as exc:
                self._provider_outcome(order,'failed',type(exc).__name__)
                raise
            self._provider_outcome(order,'received')
            progress.update(stage='response_evidence_save',response_received=True,response_body_received=True)
            metadata=getattr(raw,'transport_metadata',{})
            from tools.model_transports.deepseek import response_identifiers
            if isinstance(metadata,dict):
                status=metadata.get('http_status')
                progress['http_status']=status if type(status) is int and 100<=status<=599 else None
                progress['provider_request_id']=response_identifiers({'x-request-id':metadata.get('provider_request_id')})
            progress['received_responses']+=1
            self._checkpoint(order,row,progress,'received',started)
            returned=plain(raw) if isinstance(raw,InvestigationReturn) else getattr(raw,'raw',raw)
            # Offline substitutes and legacy transports also retain safe usage before body admission.
            with self.store.transaction() as db:
                self.store.event(db,self.run_id,'investigation_token_accounting','received',request=row['request_id'],execution=row['execution_id'],outputs=[self.store.put(db,dict(turn=turn,
                    byte_estimate=measurement,provider_usage=self._reported_usage(returned),provider_usage_source='Provider-reported; independent of body persistence.'))])
            if not progress['body_persisted']:
                self._receive(order,row,progress,dict(transport_attempted=True,response_received=True,response_body_received=True),encode(returned))
            with self.store.transaction() as db:
                response_ref=self.store.put(db,returned)
                self.store.event(db,self.run_id,'investigation_provider_response','returned',request=row['request_id'],execution=row['execution_id'],outputs=[response_ref])
                state=self.store.session(self.run_id,db)['state']
                state['investigations'][order.investigation_id].setdefault('provider_response_refs',[]).append(plain(response_ref))
                accounting=self._target_accounting(grant,db)
                if accounting is not None:
                    accounting['tasks'][order.investigation_id]['latest_output']=plain(response_ref)
                    self._save_target_accounting(db,accounting)
                self.store.update_state(db,self.run_id,state)
                self.store.event(db,self.run_id,'investigation_token_accounting','recorded',request=row['request_id'],execution=row['execution_id'],outputs=[self.store.put(db,dict(turn=turn,
                    byte_estimate=measurement,provider_usage=self._reported_usage(returned),
                    provider_usage_source='Returned provider usage only; byte estimates are not actual token counts.'))])
            progress.update(stage='response_parse',response_saved=True)
            progress['response_decoded']=isinstance(returned,dict)
            progress['saved_responses']+=1
            progress['actual_usage_known']=self._reported_usage(returned) is not None
            self._checkpoint(order,row,progress,'saved',started)
            if time.monotonic()-started>order.timeout_s:
                return InvestigationReturn(completion='incomplete',interpretation='Elapsed limit exceeded after provider return',unknowns=['INVESTIGATION_ELAPSED_LIMIT'])
            if isinstance(raw,InvestigationReturn):return raw  # Historical offline boundary.
            if hasattr(raw,'raw'):raw=raw.raw
            message=raw['choices'][0]['message'];calls=message.get('tool_calls',[])
            if raw['choices'][0].get('finish_reason')=='length':
                code='INVESTIGATION_REASONING_ONLY_LENGTH' if not calls and not message.get('content') else 'INVESTIGATION_RESPONSE_TRUNCATED'
                exc=ValueError(code)
                if not self._length_recovery(order,payload,message,exc):raise exc
                turn+=1;continue
            if allocation and report_phase and calls and calls[0]['function']['name']!='investigation_return':
                exc=ValueError('RETURN_REPORT_DELIVERY_PHASE_REQUIRED')
                feedback=self._protocol_feedback(order,exc)
                if feedback is None:raise exc
                self._append_correction(payload,self._assistant_history(message),calls[0]['id'],feedback)
                turn+=1;continue
            if not calls or len(calls)!=1:
                exc=ValueError('INVESTIGATION_NO_NATIVE_TOOL_CALL' if not calls else 'EXACTLY_ONE_NATIVE_TOOL_CALL_REQUIRED')
                feedback=self._protocol_feedback(order,exc) if self._selectable() else None
                if feedback is None:raise exc
                self._append_correction(payload,self._assistant_history(message),None,feedback)
                turn+=1
                continue
            if calls[0]['function']['name']=='investigation_return':
                progress['stage']='formal_submission_validation'
                try:
                    report=self._decode(raw,node_id=order.investigation_id)
                    progress['response_decoded']=True
                    reads=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['reads']
                    self._validate_return(order,report,reads)
                    return report
                except ValueError as exc:
                    feedback=self._protocol_feedback(order,exc)
                    if feedback is None:raise
                    assistant=dict(role='assistant',content=message.get('content'),tool_calls=calls)
                    if 'reasoning_content' in message:assistant['reasoning_content']=message['reasoning_content']
                    self._append_correction(payload,assistant,calls[0]['id'],feedback)
                    turn+=1
                    continue
            if self._native_v2():
                from tools.investigation_contract import contract
                try:
                    decision=self._contract(order).request(calls[0]['function']['name'],calls[0]['function']['arguments'],turn)
                except ValueError as exc:
                    feedback=self._protocol_feedback(order,exc)
                    if feedback is None:raise
                    assistant=dict(role='assistant',content=message.get('content'),tool_calls=calls)
                    if 'reasoning_content' in message:assistant['reasoning_content']=message['reasoning_content']
                    self._append_correction(payload,assistant,calls[0]['id'],feedback)
                    turn+=1
                    continue
            else:
                decision=DeepSeekAdapter().decode(ModelResponse(raw=raw),turn,{'evidence.read':'1.0.0'},payload['tools'][1:])
            try:
                try:query=ReadEvidence.model_validate(decision['arguments'])
                except ValueError:
                    self._consume(order,'tool_calls')
                    raise
                read=self._query(order,query)
                response=read['page']
            except ValueError as exc:
                response=dict(error=self._query_error_code(exc),scope='Evidence unavailable or operation rejected; no expanded authority')
                with self.store.transaction() as db:
                    self.store.event(db,self.run_id,'investigator_read','rejected',request=row['request_id'],outputs=[self.store.put(db,dict(decision=decision,result=response))])
            assistant=dict(role='assistant',content=message.get('content'),tool_calls=calls)
            if 'reasoning_content' in message:assistant['reasoning_content']=message['reasoning_content']
            if self._selectable():
                self._append_evidence_turn(payload,calls,response,order,assistant=assistant)
            else:payload['messages'].extend([assistant,dict(role='tool',tool_call_id=calls[0]['id'],content=encode(response))])
            self._state(order.investigation_id,consecutive_model_corrections=0)
            turn+=1

    @staticmethod
    def _assistant_history(message):
        return {k:deepcopy(v) for k,v in message.items() if k in ('role','content','reasoning_content','tool_calls')}

    @staticmethod
    def _inspection_view(records):
        # Source bodies are already in initial/native pages and selectable fields.
        return [{k:deepcopy(v) for k,v in r.items() if k in ('reference','pointer','inspection_id','request_id','execution_id','inspection_origin','content_identity')}
            for r in records]

    @staticmethod
    def _handoff_view(nodes):
        # Original orders, read archives and delegation budgets are already
        # bound by the Host. Principal report inputs need their provenance,
        # not another copy of that entire historical execution state.
        fields=('kind','result','source_run_id','source_project_id','source_node',
            'source_database_sha256','historical_validation','new_investigation_executed')
        return {key:{k:deepcopy(v) for k,v in node.items() if k in fields} for key,node in nodes.items()}

    def _append_evidence_turn(self,payload,calls,response,order,assistant=None):
        from tools.context_assembly import expand_investigation_context
        packet=expand_investigation_context(json.loads(payload['messages'][1]['content']))
        if self._selected_reports():
            ref=self.store.session(self.run_id)['state']['investigations'][order.investigation_id]['source_fact_catalog']
            body=self.store.artifact(ref)
            packet['source_fact_catalog']['entries']=[{k:v for k,v in e.items() if k!='value'} for e in body['entries']]
        # Each page body appears once, in its native tool response. References
        # are valid only while that original response remains in this request.
        confirmed=packet.setdefault('confirmed_followup_evidence',[])
        identity=digest(response)
        prior=next((x for x in confirmed if x.get('result_identity')==identity),None)
        prefetched=next((i for i,r in enumerate(packet.get('reads',[])) if r.get('page')==response),None)
        repeated=prior is not None or prefetched is not None
        location=prior['material_in_current_request'] if prior else ('/messages/1/content/reads/'+str(prefetched)+'/page' if prefetched is not None else '/messages/'+str(len(payload['messages'])+1)+'/content')
        confirmed.append(dict(tool_call_id=calls[0]['id'],result_identity=identity,material_in_current_request=location,repeated_read=repeated))
        _,grant=self._grant()
        if order.role=='principal' and grant.get('inspected_supplemental_catalog'):
            from tools.disposition_facts import catalog
            targets=packet['disposition_targets'];report_refs=[t['report'] for t in targets]
            originals=[plain(r) for r in order.evidence if plain(r) not in report_refs]
            records=self.store.session(self.run_id)['state'].get('principal_investigation_reads',[])
            ref,body=catalog(self,targets,originals,source_reads=records)
            view=dict(kind=body['kind'],version=body['version'],targets=body['targets'],rules=body['rules'],entries=[
                dict(handle=e['handle'],origin=e['origin'],name=e['name'],investigation_id=e['report_binding']['investigation_id'] if e['report_binding'] else None,
                    report_item_pointer=e['report_item_pointer'],reference=e['fact']['reference'],pointer=e['fact']['pointer'],value_type=e['value_type'],value=e['fact']['value']) for e in body['entries']])
            packet['fact_catalog']=dict(reference=ref,content=view,complete_details_query=dict(reference=ref,pointer='/entries/0',limit=100,byte_limit=65536),
                presentation='Only actually inspected supplemental fields are selectable; all report facts retained. Remaining authorized sources stay queryable via directory. Full catalog provenance is immutable and retrievable.')
            packet['principal_inspection_records']=self._inspection_view(records)
            self._state(order.investigation_id,fact_catalog=ref)
        refs=self.store.session(self.run_id)['state']['investigations'][order.investigation_id].get('provider_response_refs',[])
        packet['prior_response_archive']=dict(references=refs,
            presentation='Complete archives remain separate from reports. Required assistant reasoning and native tool responses remain in this active interaction. Repeated bodies reference their first still-visible occurrence.',
            query=dict(reference=refs[-1],pointer='/choices/0/message/reasoning_content',offset=0,limit=3000,byte_limit=4096) if refs else None)
        payload['messages'][1]['content']=encode(packet)
        if assistant is None:raise ValueError('PROVIDER_ASSISTANT_HISTORY_REQUIRED')
        result=response if not repeated else dict(material_in_current_request=location,result_identity=identity,repeated_read=True)
        payload['messages'].extend([assistant,dict(role='tool',tool_call_id=calls[0]['id'],content=encode(result))])

    def _target_feedback(self,order,exc,feedback,state,grant,db):
        """Authorize a correction; charge it only at the provider boundary."""
        accounting=self._target_accounting(grant,db);task=accounting['tasks'][order.investigation_id]
        node=state['investigations'][order.investigation_id]
        refs=node.get('provider_response_refs',[])
        source=task.get('latest_output') or (refs[-1] if refs else None)
        if not source:return None  # Local replay alone cannot authorize a paid correction.
        raw=self.store.artifact(source,db=db)
        message=raw['choices'][0]['message'];calls=message.get('tool_calls',[])
        try:submission=json.loads(calls[0]['function']['arguments']) if len(calls)==1 else {}
        except (ValueError,KeyError,TypeError):submission={}
        issue=getattr(exc,'issue',{})
        binding=grant['correction_policy']['targets'][order.investigation_id]
        decisions=submission.get('dispositions',[]) if isinstance(submission,dict) else []
        selected=[]
        for defect in feedback['issues']:
            path=defect.get('path',[])
            parts=path.strip('/').split('/') if isinstance(path,str) else list(path)
            if len(parts)>1 and parts[0]=='dispositions':
                try:selected.append(decisions[int(parts[1])]['investigation_id'])
                except (ValueError,IndexError,KeyError,TypeError):pass
        selected.extend(issue.get('legal',{}).get('missing',[]))
        if issue.get('target_investigation_id'):selected.append(issue['target_investigation_id'])
        targets=sorted({binding['dispositions'][key] for key in selected if key in binding['dispositions']}) or [binding['report']]
        # Compare the failing field and precise feedback, excluding volatile old
        # failure keys. Changing a report version or unrelated prose is no progress.
        defects=[]
        from tools.platform_handoff import pointer
        for defect in feedback['issues']:
            precise={k:v for k,v in defect.items() if k!='failure_key'}
            path=defect.get('path',[])
            path=path if isinstance(path,str) else '/'+ '/'.join(str(p) for p in path)
            try:failed=defect.get('selection',defect.get('failed_field')) if ('selection' in defect or 'failed_field' in defect) else (pointer(submission,path) if path and path!='/' else [c['function']['name'] for c in calls])
            except (KeyError,IndexError,ValueError,TypeError):failed=defect.get('selection',message.get('content'))
            defects.append(dict(feedback=precise,failed_field=failed))
        failure_identity=digest(defects)
        pending=task.get('pending_correction')
        if pending:
            if pending['failure_identity']!=failure_identity:raise ValueError('INVESTIGATION_CORRECTION_ALREADY_PENDING')
            return pending['feedback']
        stopped=None
        for target in targets:
            entry=accounting['targets'].get(target,{})
            if entry.get('used',0)>=grant['correction_policy']['maximum']:stopped='target_correction_limit'
            elif entry.get('last_failure')==failure_identity:stopped='unchanged_failure_and_feedback'
        elapsed_remaining=order.timeout_s-(time.time()-task['started_unix'])
        remaining_task=order.budget.model_calls-task['usage']['model_calls']
        remaining_stage=grant['total_budget']['model_calls']-sum(t['usage']['model_calls'] for t in accounting['tasks'].values())
        if elapsed_remaining<=0 or remaining_task<=0 or remaining_stage<=0:stopped='request_or_elapsed_limit'
        extending=any(accounting['targets'].get(t,{}).get('used',0)>=2 for t in targets)
        actionable=all(d.get('path') or d.get('legal') or d.get('requirement') for d in feedback['issues'])
        if extending and (not actionable or issue.get('cosmetic',False)):stopped='no_actionable_extension_defect'
        if stopped:
            self.store.event(db,self.run_id,'investigation_target_correction','stopped',request='investigation-'+order.investigation_id,
                outputs=[self.store.put(db,dict(reason=stopped,targets=targets,latest_output=source,issues=feedback['issues']))])
            return None
        authorization=dict(targets=targets,latest_output=source,failure_identity=failure_identity,
            ordinals={t:accounting['targets'].get(t,{}).get('used',0)+1 for t in targets},extension=extending,
            reason='Latest saved output and precise actionable remaining defect' if extending else 'Planned target correction',
            remaining_task_requests=remaining_task,remaining_stage_requests=remaining_stage,
            remaining_node_s=elapsed_remaining,activity_deadline_unix=grant.get('deadline_unix'))
        feedback['correction_authorization']=authorization
        task['pending_correction']=dict(authorization,feedback=deepcopy(feedback))
        for target in targets:accounting['targets'].setdefault(target,dict(used=0))
        self._save_target_accounting(db,accounting)
        node.update(next_request_purpose='model_correction',next_request_reason=authorization['reason'])
        self.store.update_state(db,self.run_id,state)
        self.store.event(db,self.run_id,'investigation_protocol_correction','scheduled',request='investigation-'+order.investigation_id,
            outputs=[self.store.put(db,feedback)])
        return feedback

    def _protocol_feedback(self,order,exc):
        """A received, unexecuted invalid return; never transport/length retry.

        Counter lives in the same activity state and reservations. One repair of
        a continuous invalid return per node, with a campaign-wide carried limit.
        """
        from pydantic import ValidationError
        from tools.research_error_routing import classify
        routing=classify(exc)
        if not routing['paid_correction_eligible']:
            with self.store.transaction() as db:
                self.store.event(db,self.run_id,'investigation_local_error_route','local_only',request='investigation-'+order.investigation_id,
                    outputs=[self.store.put(db,routing)])
            return None
        allowed=('RETURN_','CHILD_','INVESTIGATOR_','ONLY_','PRINCIPAL_','ACCEPT_','ADOPTED_','DISPOSITION_','MATERIAL_','INVESTIGATION_NO_NATIVE_','EXACTLY_ONE_NATIVE_')
        if not isinstance(exc,ValidationError) and not str(exc).startswith(allowed):return None
        with self.store.transaction() as db:
            session,grant=self._grant(db);state=session['state'];node=state['investigations'][order.investigation_id]
            used=state.get('investigation_protocol_corrections_used',0)
            group='principal' if order.role=='principal' else 'other'
            group_used=state.get('investigation_corrections_by_role',{}).get(group,0)
            group_limit=grant.get('protocol_correction_role_limits',{}).get(group,grant.get('protocol_correction_limit',0))
            allocation=grant.get('delivery_allocations',{}).get(order.investigation_id,{})
            if grant.get('correction_policy'):
                issues=([dict(path=list(e['loc']),type=e['type'],message=e['msg']) for e in exc.errors(include_input=False,include_url=False)]
                    if isinstance(exc,ValidationError) else [getattr(exc,'issue',dict(code=str(exc)))])
                feedback=dict(error='INVALID_UNEXECUTED_REPORT',issues=issues,error_routing=routing,
                    requirement='Correct the precise reported defect and resubmit the advertised native result. Choose conclusions independently; source inspections, task/common requests and deadlines remain in force. Up to two planned and at most four corrections per stable target, with actionable extensions only.')
                if grant['correction_policy']['version']=='mainline3.shared_completion@2.0.0':
                    feedback['requirement']='Correct the precise actionable defect and resubmit the advertised native result under the shared 40-request ceiling. Preserve original inspections and both formal disposition targets. Unchanged failing field and feedback stop further corrections.'
                return self._target_feedback(order,exc,feedback,state,grant,db)
            purposes=allocation.get('request_purposes')
            if purposes:
                if node.get('requests_by_purpose',{}).get('model_correction',0)>=purposes['model_correction']:return None
                if node.get('consecutive_model_corrections',0)>=2:return None
            elif used>=grant.get('protocol_correction_limit',0) or node.get('protocol_corrections_used',int(node.get('protocol_correction_used',False)))>=grant.get('protocol_correction_per_node',1) or group_used>=group_limit:return None
            failure_key=getattr(exc,'issue',{}).get('failure_key',str(exc).split(':',1)[0])
            counts=node.setdefault('protocol_corrections_by_failure_key',{})
            if counts.get(failure_key,0)>=grant.get('protocol_correction_per_decision',grant.get('protocol_correction_per_node',1)):return None
            if node['usage']['model_calls']>=order.budget.model_calls:return None
            issues=([dict(path=list(e['loc']),type=e['type'],message=e['msg']) for e in exc.errors(include_input=False,include_url=False)]
                if isinstance(exc,ValidationError) else [getattr(exc,'issue',dict(code=str(exc)))])
            feedback=dict(error='INVALID_UNEXECUTED_REPORT',issues=issues,error_routing=routing,
                requirement='Resubmit a complete native investigation_return with corrected fields. Each fact must have exactly ONE valid JSON Pointer, not a comma-separated list or comparison expression. Split or omit compound facts within the schema limits. Scalar pointers require the exact scalar, never enclosing objects or rounded replacements. Directory metadata cannot support scientific facts; cite only authorized original sources. source_identity keys must match actual root source fields. No invalid call executed. This paid correction uses the same request/time limits; no further correction of this report is allowed.')
            if self._selectable():
                feedback['requirement']='Resubmit the complete advertised investigation_return. Principal dispositions select catalog handles; supporting_facts use report handles, additional_support uses explicitly principal supplemental handles, scope declares applicability separately. Projection is extraction only. Each issue identifies the failed decision position and legal structure; choose conclusions yourself. No disposition was executed. Current report/evidence and original permissions, counters and deadline remain in force; complete prior responses are archived.'
            node['protocol_correction_used']=True
            node['next_request_purpose']='model_correction'
            node['next_request_reason']=str(exc).split(':',1)[0]
            node['consecutive_model_corrections']=node.get('consecutive_model_corrections',0)+1
            node['protocol_corrections_used']=node.get('protocol_corrections_used',0)+1
            counts[failure_key]=counts.get(failure_key,0)+1
            state.setdefault('investigation_corrections_by_role',{})[group]=group_used+1
            state['investigation_protocol_corrections_used']=used+1
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'investigation_protocol_correction','scheduled',request='investigation-'+order.investigation_id,
                outputs=[self.store.put(db,feedback)])
            return feedback

    def _append_correction(self,payload,assistant,call_id,feedback):
        calls=assistant.get('tool_calls',[])
        if len(calls)>1:
            payload['messages'].append(assistant)
            payload['messages'].extend(dict(role='tool',tool_call_id=c['id'],content=encode(dict(feedback,executed=False))) for c in calls)
            return
        if call_id is None:
            payload['messages'].extend([assistant,dict(role='user',content=encode(feedback))]);return
        payload['messages'].extend([assistant,dict(role='tool',tool_call_id=call_id,content=encode(feedback))]);return

    def _length_recovery(self,order,payload,message,exc):
        """Frozen conditional probes, paid from this node; no partial execution."""
        _,grant=self._grant();policy=grant.get('conditional_length_recovery')
        if not policy:return False
        state=self.store.session(self.run_id)['state'];used=state.get('recovery_probes_used',0)
        options=[v for v in policy['configurations'][1:] if v['supported']]
        if used>=min(2,len(options)):return False
        option=options[used]
        correction=ValueError('RETURN_COMPLETE_FOCUSED_SUBMISSION_REQUIRED')
        correction.issue=dict(code=str(exc),classification='response received, no formal decision' if str(exc)=='INVESTIGATION_REASONING_ONLY_LENGTH' else 'truncated formal content; no partial fields executed',
            failure_key='length:'+order.investigation_id,requirement='Submit one complete concise native report, with explicit unknowns. Prior response remains original evidence.')
        feedback=self._protocol_feedback(order,correction)
        if feedback is None:return False
        assistant=self._assistant_history(message);calls=message.get('tool_calls',[])
        self._append_correction(payload,assistant,calls[0]['id'] if len(calls)==1 else None,feedback)
        payload['max_tokens']=option['max_tokens']
        payload['reasoning_effort']=option['reasoning_effort']
        from tools.context_assembly import check_outgoing_request
        from tools.platform_models import effective_config
        check_outgoing_request(payload,effective_config(self.host),'research_decision')
        with self.store.transaction() as db:
            state=self.store.session(self.run_id,db)['state'];state['recovery_probes_used']=used+1
            state['investigations'][order.investigation_id]['provider_setting_override']=option
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'investigation_recovery_probe','scheduled',request='investigation-'+order.investigation_id,outputs=[self.store.put(db,dict(trigger=str(exc),selected=option,original_retained=True))])
        return True

    def _decode(self, raw, *, node_id=None):
        if isinstance(raw,InvestigationReturn):return raw  # Explicit offline fixture boundary.
        if hasattr(raw,'raw'):raw=raw.raw
        if raw['choices'][0].get('finish_reason')=='length':raise ValueError('INVESTIGATION_RESPONSE_TRUNCATED')
        calls=raw['choices'][0]['message']['tool_calls']
        if len(calls)!=1 or calls[0]['function']['name']!='investigation_return':raise ValueError('BOUNDED_RETURN_REQUIRED')
        if self._native_v2():
            bound=self.store.session(self.run_id)['state'].get('investigations',{}).get(node_id) if node_id else None
            report=self._contract(InvestigationOrder.model_validate(bound['order']) if bound else None).parse('investigation_return',calls[0]['function']['arguments'])
            if self._selectable():
                from tools.disposition_facts import expand
                # Selection carries its own immutable catalog reference. The
                # independently saved principal node binding is the authority.
                state=self.store.session(self.run_id)['state']
                eligible=[n for k,n in state.get('investigations',{}).items() if k==node_id] if node_id else [n for n in state.get('investigations',{}).values() if n.get('status')=='running']
                nodes=[n for n in eligible if n['order']['role']=='principal']
                if report.dispositions and len(nodes)!=1:raise ValueError('DISPOSITION_PRINCIPAL_NODE_BINDING_REQUIRED')
                value=plain(report)
                links=[]
                if self._selected_reports():
                    from tools.disposition_facts import expand_source
                    candidates=eligible if node_id else [n for n in eligible
                        if any(plain(f.catalog)==n.get('source_fact_catalog') for f in [*report.facts,*report.counterevidence])]
                    if (report.facts or report.counterevidence) and len(candidates)!=1:raise ValueError('REPORT_SOURCE_CATALOG_NODE_BINDING_REQUIRED')
                    for area in ('facts','counterevidence'):
                        value[area]=[]
                        for i,f in enumerate(getattr(report,area)):
                            fact,link=expand_source(self,f,candidates[0],path=f'/{area}/{i}')
                            value[area].append(plain(fact));links.append(link)
                value['dispositions']=[plain(expand(self,d,nodes[0]['fact_catalog'],path=f'/dispositions/{i}')) for i,d in enumerate(report.dispositions)]
                expanded=InvestigationReturn.model_validate(value)
                with self.store.transaction() as db:
                    selection=self.store.put(db,plain(report));expansion=self.store.put(db,plain(expanded))
                    self.store.event(db,self.run_id,'principal_selection_expansion' if report.dispositions else 'investigator_selection_expansion','expanded',
                        request='investigation-'+nodes[0]['order']['investigation_id'] if nodes else None,
                        outputs=[self.store.put(db,dict(model_selection=plain(report),expanded=plain(expanded),source_expansion_links=links,
                            original_selection_reference=plain(selection),deterministic_expansion_reference=plain(expansion)))])
                return expanded
            return report
        return InvestigationReturn.model_validate_json(calls[0]['function']['arguments'])

    def _validate_return(self,order,report,reads):
        if order.role=='principal':
            reads=[*reads,*self.store.session(self.run_id)['state'].get('principal_investigation_reads',[])]
        if len(json.dumps(plain(report),ensure_ascii=False).encode('utf8'))>order.output_bytes:raise ValueError('INVESTIGATION_RETURN_TOO_LARGE')
        if order.role=='principal' and order.disposition_ids is not None:
            supplied=[d.investigation_id for d in report.dispositions];expected=order.disposition_ids
            if sorted(supplied)!=sorted(expected):
                from tools.disposition_facts import BindingError
                missing=sorted(set(expected)-set(supplied))
                issue=BindingError('/dispositions',supplied,'missing, duplicate or foreign formal disposition target',
                    dict(expected=expected,missing=missing,structure='Exactly one formal accept/defer/reject disposition per declared report; choose decisions yourself.'))
                targets={k:n['result']['artifact_id'] for k,n in self._reports().items() if k in missing and n.get('result')}
                issue.issue['failure_key']='report:'+','.join(sorted(targets.values())) if targets else 'formal_target_cardinality'
                raise issue
        ids={r.artifact_id for r in order.evidence}
        for group,facts in (('facts',report.facts),('counterevidence',report.counterevidence)):
            for index,fact in enumerate(facts):
                try:
                    if fact.reference.artifact_id not in ids:raise ValueError('RETURN_SOURCE_OUT_OF_SCOPE')
                    self._validate_fact(fact,'RETURN')
                    if not any(self._visible(fact,read) for read in reads):raise ValueError('RETURN_FACT_NOT_IN_INSPECTED_PAGE')
                except ValueError as exc:
                    issue=getattr(exc,'issue',dict(code=str(exc).split(':',1)[0],path='',reference=plain(fact.reference),pointer=fact.pointer))
                    issue['path']=f'/{group}/{index}'+issue['path']
                    issue['failure_key']='source:'+fact.reference.artifact_id+':'+issue['path']
                    issue.setdefault('legal',dict(query=dict(reference=plain(fact.reference),pointer=fact.pointer),requirement='Read the exact original scoped field; select supported evidence or retain uncertainty.'))
                    exc.issue=issue
                    raise
        if report.children and (order.role!='coordinator' or order.parent_id):raise ValueError('INVESTIGATOR_CANNOT_DELEGATE')
        if any(c.parent_id!=order.investigation_id for c in report.children):raise ValueError('CHILD_PARENT_BINDING_MISMATCH')
        for child in report.children:
            if child.role!='investigator':raise ValueError('ONLY_INVESTIGATOR_CHILDREN')
            if child.timeout_s>order.timeout_s or child.output_bytes>order.output_bytes:raise ValueError('CHILD_CAPACITY_OR_TIMEOUT_SCOPE_EXCEEDED')
            if set(child.allowed_tools)-set(order.allowed_tools):raise ValueError('CHILD_TOOL_SCOPE_EXCEEDED')
            if {json.dumps(plain(r),sort_keys=True) for r in child.evidence}-{json.dumps(plain(r),sort_keys=True) for r in order.evidence}:
                raise ValueError('CHILD_EVIDENCE_SCOPE_EXCEEDED')
            if any(v>plain(order.budget)[k] for k,v in plain(child.budget).items()):raise ValueError('CHILD_BUDGET_SCOPE_EXCEEDED')
        if report.dispositions and order.role!='principal':raise ValueError('PRINCIPAL_ONLY_DISPOSITION_AUTHORITY')
        if order.role=='principal':
            for index,decision in enumerate(report.dispositions):
                try:self.disposition(decision,validate_only=True)
                except ValueError as exc:
                    issue=getattr(exc,'issue',dict(code=str(exc)))
                    issue['target_investigation_id']=decision.investigation_id
                    if not str(issue.get('path','')).startswith('/dispositions/'):
                        issue['path']=f'/dispositions/{index}'+issue.get('path','')
                    exc.issue=issue
                    raise

    def _validate_fact(self,fact,label):
        from tools.platform_handoff import pointer
        from tools.platform_store import encode
        source=self.store.artifact(fact.reference)
        try:original=pointer(source,fact.pointer)
        except (KeyError,IndexError,TypeError,ValueError):
            raise ValueError(label+'_INVALID_SINGLE_JSON_POINTER: '+fact.pointer) from None
        if encode(original)!=encode(fact.value):
            exc=ValueError(label+'_SOURCE_VALUE_MISMATCH: '+fact.pointer)
            exc.issue=dict(code=label+'_SOURCE_VALUE_MISMATCH',path='/value',reference=plain(fact.reference),pointer=fact.pointer,
                supplied_value=plain(fact.value),supplied_type=type(fact.value).__name__,original_value=original,original_type=type(original).__name__)
            raise exc
        identity_keys={'candidate_id','owner_run_id','run_id','execution_id','source_execution_id','configuration','scientific_configuration_identity','coordinate_frame','result_type'}
        source_root=source if isinstance(source,dict) else {}
        invalid={k:dict(supplied=v,allowed_identity_key=k in identity_keys,exists_at_source_root=k in source_root,
            original=source_root.get(k),original_type=type(source_root[k]).__name__ if k in source_root else None)
            for k,v in fact.source_identity.items() if k not in identity_keys or k not in source_root or encode(source_root[k])!=encode(v)}
        if invalid:
            exc=ValueError(label+'_SOURCE_IDENTITY_MISMATCH')
            exc.issue=dict(code=label+'_SOURCE_IDENTITY_MISMATCH',path='/source_identity',reference=plain(fact.reference),pointer=fact.pointer,
                invalid_fields=invalid,legal=dict(root_identity_fields={k:source_root[k] for k in sorted(identity_keys&source_root.keys())},
                    query=dict(reference=plain(fact.reference),pointer=''),requirement='source_identity binds exact root fields only; nested values need their own source pointer. No alias or inference.'))
            raise exc

    def _visible(self,fact,read):
        """Original pointers remain correct for offset pages; overviews are no facts."""
        from tools.platform_handoff import pointer
        from tools.platform_store import encode
        if read['reference']!=plain(fact.reference) or read['page']['kind']!='content':return False
        prefix=read['pointer'];page=read['page'];suffix=fact.pointer[len(prefix):]
        if fact.pointer!=prefix and not fact.pointer.startswith(prefix+'/'):return False
        content=page['content']
        try:
            if isinstance(content,list) and suffix:
                head,*tail=suffix[1:].split('/');index=int(head)-page.get('offset',0)
                if index<0 or index>=len(content):return False
                content=content[index];suffix='/'+'/'.join(tail) if tail else ''
            elif not suffix and isinstance(content,(list,str)):
                if page.get('offset',0) or page.get('next_offset') is not None:return False
            return encode(pointer(content,suffix))==encode(fact.value)
        except (KeyError,IndexError,TypeError,ValueError):return False

    def _receipt(self,row,status,error=None):
        return dict(request_id=row['request_id'],execution_id=row['execution_id'],tool_id='research.investigation',
            tool_version='1.0.0',execution_status=status,caller='investigation-dispatcher',error=error,
            charged=zero(),cache_hit=False)

    def _state(self,key,**updates):
        with self.store.transaction() as db:
            state=self.store.session(self.run_id,db)['state'];state['investigations'][key].update(updates)
            self.store.update_state(db,self.run_id,state)

    def recover(self,key):
        self._grant()  # Recovery collects evidence; it never revives an expired activity.
        historical=self.store.session(self.run_id)['state'].get('historical_investigations',{}).get(key)
        if historical:
            return InvestigationResult(investigation_id=key,status='completed',result=historical['result'])
        node=self.store.session(self.run_id)['state'].get('investigations',{}).get(key,{})
        request_run=node.get('request_run_id',self.run_id)
        row=self.store.lookup(request_run,node.get('active_request_id','investigation-'+key))
        if not row:raise ValueError('INVESTIGATION_NOT_FOUND')
        if row['receipt']:return self._recover_unowned(key,row)
        from tools.workbench import owner
        ownership=owner(self.host.folder,'.investigation-'+key+'.lock')
        try:ownership.__enter__()
        except OSError:
            node=self.store.session(self.run_id)['state']['investigations'][key]
            return InvestigationResult(investigation_id=key,status=node['status'] if node['status'] in ('pending','running') else 'running',
                failure_record=node.get('failure_record'),progress=node.get('progress'))
        try:return self._recover_unowned(key,self.store.lookup(request_run,row['request_id']))
        finally:ownership.__exit__(None,None,None)

    def _recover_unowned(self,key,row):
        node=self.store.session(self.run_id)['state']['investigations'][key]
        order=InvestigationOrder.model_validate(node['order'])
        self._scope(order)  # Same current root/parent/source/tool authority as dispatch.
        events=self.store.events(row['run_id'])
        if row['run_id']!=self.run_id:events=sorted([*events,*self.store.events(self.run_id)],key=lambda e:e['sequence'])
        if not row['receipt']:
            responses=[e for e in events if e['kind']=='investigation_response'
                and e['status']=='validated' and e['request_id']==row['request_id'] and e['execution_id']==row['execution_id']]
            progress=dict(node.get('progress',{}))
            progress['recovering']=True
            progress.setdefault('stage','recovery')
            for field in ('transport_attempted','response_received','response_body_received','response_saved','valid_report','report_saved','settlement_completed','actual_usage_known'):
                progress.setdefault(field,None)  # Historical absence is not a false observation.
            started=time.monotonic()
            try:
                progress['stage']='report_evidence_read'
                saved=self.store.artifact(responses[-1]['outputs'][0]) if responses else None
                if saved is None:
                    originals=[e for e in events if e['kind']=='investigation_provider_response'
                        and e['request_id']==row['request_id'] and e['execution_id']==row['execution_id']]
                    receptions=[e for e in events if e['kind']=='investigation_reception' and e['status']=='body_persisted'
                        and e['request_id']==row['request_id'] and e['execution_id']==row['execution_id']]
                    if receptions and (not originals or receptions[-1]['sequence']>originals[-1]['sequence']):
                        reception=self.store.artifact(receptions[-1]['outputs'][0])
                        original=self.store.artifact(reception['body'])
                        encoded=original.get('utf8_text') if original['representation']=='complete_original_utf8_text' else __import__('base64').b64decode(original['base64_bytes']).decode('utf-8')
                        raw=json.loads(encoded)
                        with self.store.transaction() as db:
                            ref=self.store.put(db,raw)
                            self.store.event(db,self.run_id,'investigation_provider_response','locally_recovered',request=row['request_id'],execution=row['execution_id'],inputs=[reception['body']],outputs=[ref])
                        originals=[*originals,dict(outputs=[plain(ref)])]
                    if originals:
                        progress['stage']='response_evidence_read'
                        raw=self.store.artifact(originals[-1]['outputs'][0])
                        calls=raw.get('choices',[{}])[0].get('message',{}).get('tool_calls',[]) if isinstance(raw,dict) else []
                        if len(calls)==1 and calls[0].get('function',{}).get('name')=='investigation_return':
                            progress.update(stage='report_validation',response_received=True,response_saved=True)
                            report=self._decode(raw,node_id=key)
                            self._validate_return(order,report,node['reads'])
                            progress.update(valid_report=True,response_received=True,response_saved=True)
                            failure=self.store.artifact(node['failure_record']) if node.get('failure_record') else None
                            elapsed=failure['elapsed_s'] if failure else max(json.loads(row['reserved'])['wall_s'],progress.get('elapsed_s',0.))
                            saved=dict(report=plain(report),elapsed_s=elapsed,
                                recovered_from_response=originals[-1]['outputs'][0],
                                elapsed_accounting='saved failure measurement' if failure else 'conservative reservation; exact process end unknown')
                            progress['stage']='report_evidence_save'
                            with self.store.transaction() as db:
                                ref=self.store.put(db,saved)
                                self.store.event(db,self.run_id,'investigation_response','validated',request=row['request_id'],
                                    execution=row['execution_id'],inputs=[originals[-1]['outputs'][0]],outputs=[ref])
                if saved is not None:
                    progress['stage']='report_validation'
                    report=InvestigationReturn.model_validate(saved['report'])
                    self._validate_return(order,report,node['reads'])
                    progress.update(valid_report=True,report_saved=True,stage='settlement')
                    self.store.complete(row,self._receipt(row,'completed'),plain(report),elapsed=saved['elapsed_s'],
                        actual_cost=node.get('usage',{**zero(),'model_calls':1,'tool_calls':len(node['reads'])}))
                    progress['settlement_completed']=True
                    self._state(key,progress=progress)
                    row=self.store.lookup(row['run_id'],row['request_id'])
                elif not row['receipt']:
                    # A durably confirmed local failure can also need settlement.
                    # This requires reception/no-call facts, not merely an error category.
                    failures=[e for e in events if e['kind']=='investigation_failure'
                        and e['status']=='confirmed_local_failure' and e['request_id']==row['request_id']
                        and e['execution_id']==row['execution_id']]
                    if failures:
                        failure=self.store.artifact(failures[-1]['outputs'][0]);known=failure['progress']
                        not_sent=known.get('transport_attempted') is False and known.get('transport_callable_invocations')==0
                        received=known.get('response_received') is True and (
                            known.get('response_body_received') is True or (failure['details']['http_status'] or 0)>=400)
                        if not_sent or received:
                            progress['stage']='settlement'
                            self.store.complete(row,self._receipt(row,'failed','INVESTIGATION_FAILED_AT_'+known['stage'].upper()),
                                elapsed=failure['elapsed_s'],actual_cost=node['usage'])
                            progress['settlement_completed']=True
                            self._state(key,progress=progress)
                            row=self.store.lookup(row['run_id'],row['request_id'])
            except Exception as exc:
                self._handle_failure(order,row,progress,exc,started)
                row=self.store.lookup(row['run_id'],row['request_id'])
        # Reconcile sealed ledger result first, including crash after settlement.
        if row['receipt']:
            receipt=json.loads(row['receipt']);status='completed' if receipt['execution_status']=='completed' else 'failed'
            updates=dict(status=status,result=receipt.get('output'),reason=receipt.get('error'))
            if status=='completed':
                report=self.store.artifact(receipt['output']);updates['children']=report.get('children',[])
                if report.get('completion')=='incomplete':updates['status']='incomplete'
            progress=dict(self.store.session(self.run_id)['state']['investigations'][key].get('progress',{}))
            if progress:progress['settlement_completed']=True;updates['progress']=progress
            self._state(key,**updates)
            node=self.store.session(self.run_id)['state']['investigations'][key]
            return InvestigationResult(investigation_id=key,**{k:updates.get(k) for k in ('status','result','reason')},
                failure_record=node.get('failure_record'),progress=node.get('progress'))
        self.store.mark_unknown(row['run_id'],row['request_id']);self._state(key,status='unconfirmed')
        node=self.store.session(self.run_id)['state']['investigations'][key]
        return InvestigationResult(investigation_id=key,status='unconfirmed',reason='No sealed result; reservation retained. Reconcile original provider request; no automatic retry or release.',
            failure_record=node.get('failure_record'),progress=node.get('progress'))

    def disposition(self,value,*,validate_only=False):
        self._grant()
        self._principal_authority()
        args=PrincipalDisposition.model_validate(value);result=self.recover(args.investigation_id)
        if result.status!='completed':raise ValueError('COMPLETED_INVESTIGATION_REQUIRED')
        state=self.store.session(self.run_id)['state'];reads=state.get('principal_investigation_reads',[])
        if args.report is not None and plain(args.report)!=plain(result.result):raise ValueError('DISPOSITION_REPORT_BINDING_MISMATCH')
        if args.disposition=='accept' and (not args.adopted_claims or args.report is None):
            raise ValueError('ACCEPT_REQUIRES_EXPLICIT_CLAIMS_AND_REPORT_BINDING')
        report=self.store.artifact(result.result)
        if args.disposition!='accept' and args.adopted_claims:raise ValueError('ONLY_ACCEPT_ADOPTS_CLAIMS')
        inspection_links=[]
        provenance=args.selection_provenance
        if provenance:
            from tools.disposition_facts import expand,provenance_body
            provenance=provenance_body(self,provenance)
            expected=expand(self,provenance['model_selection'],provenance['catalog'],path=provenance['expansion_path'])
            if encode(plain(expected))!=encode(plain(args)):raise ValueError('DISPOSITION_EXPANSION_CHANGED')
            report_reads=[r for n in state.get('investigations',{}).values() if n['order']['role']=='principal' for r in n.get('reads',[])]
            report_reads+=reads
            if not any(self._visible(SourceFact(statement='Complete bound report',reference=result.result,pointer='',value=report),r) for r in report_reads):
                exc=ValueError('PRINCIPAL_MUST_INSPECT_COMPLETE_REPORT')
                exc.issue=dict(code=str(exc),failed_field=args.investigation_id,legal=dict(requirement='Inspect the complete current bound report through the public evidence interface'))
                raise exc
        facts=[*args.evidence_used,*[f for c in args.adopted_claims for f in (*c.supporting_facts,*c.additional_support,*c.scope)]]
        for fact in facts:
            if fact.reference.artifact_id not in self._sources(*self._grant()):raise ValueError('PRINCIPAL_SOURCE_OUT_OF_SCOPE')
            self._validate_fact(fact,'PRINCIPAL')
            matching=[r for r in reads if self._visible(fact,r)]
            if not matching:
                exc=ValueError('PRINCIPAL_MUST_INSPECT_SOURCE')
                exc.issue=dict(code=str(exc),failed_field=dict(reference=plain(fact.reference),pointer=fact.pointer),
                    legal=dict(query=dict(reference=plain(fact.reference),pointer=fact.pointer),requirement='Perform the missing independent source inspection or narrow/defer the decision'))
                raise exc
            inspection_links.append(dict(fact=plain(fact),inspection_ids=[r['inspection_id'] for r in matching]))
        def key(f):return encode({k:plain(f)[k] for k in ('reference','pointer','value')})
        returned={key(f) for f in (*report['facts'],*report['counterevidence'])}
        for index,claim in enumerate(args.adopted_claims):
            for fi,f in enumerate(claim.supporting_facts):
                if key(f) not in returned:
                    linked=provenance and any(link['role']=='report_support' and link['expanded_fact']==plain(f) for link in provenance['links'])
                    if not linked:
                        from tools.disposition_facts import BindingError
                        raise BindingError(f'/adopted_claims/{index}/supporting_facts/{fi}',plain(f),'not an exact report fact or validated projection',dict(use='select report handle or label as principal additional_support'))
            if claim.additional_support and not provenance:raise ValueError('DISPOSITION_ADDITIONAL_SUPPORT_REQUIRES_SELECTION_PROVENANCE')
            missing={f.reference.artifact_id for f in (*claim.supporting_facts,*claim.additional_support)}-{f.reference.artifact_id for f in claim.scope}
            if missing:
                from tools.disposition_facts import BindingError
                selected=provenance['model_selection']['adopted_claims'][index]['scope'] if provenance else plain(claim.scope)
                available=[]
                if provenance:
                    cat=self.store.artifact(provenance['catalog'])
                    available=[dict(handle=e['handle'],name=e['name'],reference=e['fact']['reference'],pointer=e['fact']['pointer'],value=e['fact']['value'])
                        for e in cat['entries'] if e['fact']['reference']['artifact_id'] in missing and e['fact']['pointer'] in ('/execution_id','/result_type','/coordinate_frame')]
                issue=BindingError((provenance['expansion_path'] if provenance else '')+f'/adopted_claims/{index}/scope',selected,
                    'supporting evidence source has no explicitly selected applicability scope',
                    dict(missing_source_artifacts=sorted(missing),available_scope_handles=available,
                         structure='Each original source used in supporting_facts/additional_support must have its own exact selected scope. Choose scope, narrower support, defer or reject yourself.'))
                issue.issue['failure_key']='report:'+plain(result.result)['artifact_id']
                raise issue
            # Different original sources are allowed; each attribution was checked
            # against its own immutable source. Prose is never judged by an LLM.
        limitations=list(args.remaining_unknowns)
        if not inspection_links:limitations.append('No principal supporting source inspection; insufficient evidence disposition is not independently verified.')
        record=dict(decision=plain(args),bound_report=plain(result.result),inspection_links=inspection_links,
            original_source_identities=[dict(reference=plain(f.reference),identity={k:v for k,v in self.store.artifact(f.reference).items()
                if k in ('candidate_id','owner_run_id','run_id','execution_id','source_execution_id','configuration','scientific_configuration_identity','coordinate_frame','result_type')}) for f in facts],
            report_counterevidence=report['counterevidence'],report_unknowns=report['unknowns'],
            source_validation='references, original values, identities and declared scope fields checked',
            independently_inspected=bool(inspection_links),limitations=limitations,
            semantic_claims_unassessed=[*args.semantic_claims_unassessed,*[dict(statement=c.statement,support_explanation=c.support_explanation) for c in args.adopted_claims]],
            report_interpretation_unassessed=report['interpretation'],rationale_unassessed=args.reason,
            semantic_correctness='unassessed; structural/source validation does not prove scientific interpretation')
        if validate_only:return record
        with self.store.transaction() as db:
            ref=self.store.put(db,record);state=self.store.session(self.run_id,db)['state']
            collection='historical_investigations' if args.investigation_id in state.get('historical_investigations',{}) else 'investigations'
            node=state[collection][args.investigation_id]
            previous=node.get('disposition_record')
            if previous and previous!=plain(ref):node.setdefault('disposition_versions',[]).append(previous)
            state[collection][args.investigation_id]['principal_disposition']=record
            state[collection][args.investigation_id]['disposition_record']=plain(ref)
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'principal_disposition','recorded',inputs=[result.result],outputs=[ref])
        return result.model_copy(update={'disposition_record':ref})

    def _principal_authority(self):
        role=self.store.session(self.run_id)['state'].get('role_context',{}).get('role')
        if role in ('investigator','coordinator') or self.host.actor.split(':',1)[0] in ('investigator','coordinator'):
            raise ValueError('PRINCIPAL_ONLY_DISPOSITION_AUTHORITY')

    def disposition_receipt(self, investigation_id, revision):
        """Retrieve a stable business receipt; no conversation recovery is scheduled."""
        self._grant();self._principal_authority()
        row=self.store.lookup(self.run_id,'disposition-'+digest([investigation_id,revision]))
        return json.loads(row['receipt']) if row and row['receipt'] else None

    def submit_disposition(self, value, revision):
        """Opt-in atomic submission for runtimes delivering native tools at least once.

        The existing validator and disposition version list remain authoritative.
        The business key excludes transport call IDs; conflicting delivery cannot
        replace a committed decision. Legacy callers keep their existing API.
        """
        self._grant();self._principal_authority()
        if type(revision) is not int or revision<1:raise ValueError('INVALID_DISPOSITION_REVISION')
        args=PrincipalDisposition.model_validate(value)
        request_id='disposition-'+digest([args.investigation_id,revision])
        payload_hash=digest(dict(decision=plain(args),revision=revision))
        old=self.store.lookup(self.run_id,request_id)
        if old:
            if old['request_hash']!=payload_hash:raise ValueError('DISPOSITION_REVISION_CONFLICT')
            if old['receipt']:return json.loads(old['receipt'])
        # No judgment rewriting: use exactly the existing public validation.
        record=self.disposition(args,validate_only=True)
        row,_=self.store.reserve(self.run_id,request_id,payload_hash,self.host.actor,
            {**zero(),'tool_calls':1},kind='formal_disposition')
        with self.store.transaction() as db:
            current=self.store.lookup(self.run_id,request_id,db)
            if current['receipt']:return json.loads(current['receipt'])
            state=self.store.session(self.run_id,db)['state']
            collection='historical_investigations' if args.investigation_id in state.get('historical_investigations',{}) else 'investigations'
            node=state[collection][args.investigation_id]
            if revision!=node.get('submission_revision',0)+1:raise ValueError('DISPOSITION_REVISION_SEQUENCE')
            ref=self.store.put(db,record)
            previous=node.get('disposition_record')
            if previous and previous!=plain(ref):node.setdefault('disposition_versions',[]).append(previous)
            node.update(principal_disposition=record,disposition_record=plain(ref),submission_revision=revision)
            self.store.update_state(db,self.run_id,state)
            self.store.event(db,self.run_id,'principal_disposition','recorded',inputs=[args.report] if args.report else [],outputs=[ref])
            receipt=dict(request_id=request_id,execution_id=row['execution_id'],caller=self.host.actor,
                tool_id='research.investigation_disposition',tool_version='1.0.0',execution_status='completed',
                result_contract='PrincipalDisposition',result_version='1.0.0',charged=zero())
            return self.store.complete(row,receipt,record,kind='formal_disposition',db=db)


def dispatch(ctx,args):
    from tools.platform_workers import Coordinator
    return Coordinator(ctx.host).investigations().submit(args)


def status(ctx,args):
    return InvestigationDispatcher(ctx.host).recover(args.investigation_id)


def disposition(ctx,args):
    return InvestigationDispatcher(ctx.host).disposition(args)


def read_source(ctx,args):
    dispatcher=InvestigationDispatcher(ctx.host);session,grant=dispatcher._grant()
    dispatcher._principal_authority()
    catalogs=[n for n in session['state'].get('investigations',{}).values() if n.get('directory')==plain(args.reference)]
    if catalogs:
        for node in catalogs:dispatcher._scope(InvestigationOrder.model_validate(node['order']))
    elif args.reference.artifact_id not in dispatcher._sources(session,grant):
        raise ValueError('PRINCIPAL_READ_SOURCE_OUT_OF_SCOPE')
    from tools.platform_tools import read_evidence
    result=read_evidence(ctx,args)
    if result.kind=='content' and not catalogs:
        fact=dict(reference=plain(args.reference),pointer=args.pointer,query=plain(args),page=plain(result),
            inspection_id=digest(dict(request=ctx.request.request_id,query=plain(args),page=plain(result))),
            request_id=ctx.request.request_id,execution_id=ctx.row['execution_id'])
        with ctx.store.transaction() as db:
            state=ctx.store.session(ctx.run_id,db)['state']
            state.setdefault('principal_investigation_reads',[]).append(fact)
            ctx.store.event(db,ctx.run_id,'principal_inspection','completed',request=ctx.request.request_id,
                execution=ctx.row['execution_id'],outputs=[ctx.store.put(db,fact)])
            ctx.store.update_state(db,ctx.run_id,state)
    return result


def dispatch_preflight(inp,args,reg):
    return dict(cost=dict(wall_s=0.))
