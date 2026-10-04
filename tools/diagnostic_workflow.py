"""One sequential diagnostic workflow, configurable working-memory organization."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from tools.platform_store import Store, plain, encode
from tools.platform_host import Host
from tools.platform_models import run_loop, tool_naming_policy, READABLE_TOOL_NAMING
from tools.platform_diagnosis_coordinator import configure_role, transfer_recovery, execute_check_feedback, recovery_status
from tools.diagnostic_inventory import evidence_inventory
from tools.diagnostic_facts import POLICY as FACT_POLICY, handover
from tools.state_io import read, atomic_json
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution, BoundReader

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=0,worker_calls=0,wall_s=3600.)
NUMERICAL=dict(local_solves=6,prediction_evaluations=24)
SUFFIX_LIMITS=dict(model_calls=8,tool_calls=20,backend_solves=0,worker_calls=0,wall_s=1200.)
TOOLS={n:'1.0.0' for n in ('diagnosis.request','diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read')}
TOOLS['design.respond_diagnosis']='2.0.0'
TOOLS.update({'diagnosis.submit':'2.0.0','diagnosis.check_request':'2.0.0'})
CAPABILITIES=dict(
    prediction_braking='At one saved projected state, compare recorded input with instantaneous braking-box input over the fixed short horizon. Can measure local endpoint speed/position differences. Cannot separate objective weighting, seed selection, horizon effects or backend-model mismatch when they predict the same result; cannot identify the dominant settling cause.',
    local_comparison='Compare two local controller solves at the same saved state/previous input/horizon with exactly one adopted weight change. Measures local plan/endpoint differences; does not establish closed-loop settling or causal attribution. Requires a saved effective horizon matching the authorized horizon.')
SCOPE=dict(operations=['prediction_braking','local_comparison'],model='model.gvs@1.0.0',horizon_s=.01,
    integration='implicit_euler',integration_step_s=.002,max_wall_s=300.,max_checks=1,
    numerical_limits=NUMERICAL,configuration_scope='saved_state_or_temporary_analysis')
MEMORY=dict(policy='Reconstruct system instructions plus structured state; no chronological conversation replay.',
    context_bytes=200000,products=8,product_bytes=12000,total_product_bytes=48000,
    retention='Own accepted handoff products FIFO; oversized products retain reference only. Existing recent evidence pages and last four actions stay within their original host limits. Phase changes preserve these in the same context.',
    separation='single_context shares one memory across phases; dual_context keeps one per role and receives explicit current request/report/response/feedback handoffs.',
    cross_run_experience=False)
PERMISSIONS=dict(request=['evidence.read','diagnosis.request'],initial=['diagnosis.inspect_evidence','evidence.read','diagnosis.submit'],
    response_initial=['design.respond_diagnosis'],check=['evidence.read','diagnosis.inspect_evidence','diagnosis.check_request'],
    revision=['diagnosis.submit'],response_final=['design.respond_diagnosis'])
# Capacity belongs to phases, never to a role or number of contexts.
PHASES=dict(request=dict(limit=dict(model_calls=3),protect_project=dict(model_calls=21,tool_calls=40,wall_s=2400.)),
    initial=dict(limit=dict(model_calls=5),protect_project=dict(model_calls=16,tool_calls=30,wall_s=1800.)),
    response_initial=dict(limit=dict(model_calls=3,wall_s=300.),protect_project=dict(model_calls=13,tool_calls=20,wall_s=1200.)),
    check=dict(limit=dict(model_calls=6),protect_project=dict(model_calls=7,tool_calls=10,wall_s=700.)),
    revision=dict(limit=dict(model_calls=4),protect_project=dict(model_calls=3,tool_calls=3,wall_s=300.)),
    response_final=dict(limit=dict(model_calls=3,wall_s=300.)))
INSTRUCTIONS=dict(
    request='Inspect the common inventory and summary. Formulate an open diagnostic question about failed secondary performance despite successful terminal reach. Author scope and stopping conditions. No predetermined root cause. Host supplies the saved-state grant and subject identity.',
    initial='Read at least one prediction view and one motion or plans view. At most two successful reading turns; independent views can be batched. Then submit a concise initial report with 2-4 exact selected facts, competing hypotheses, explicit gaps and recommendations. Fact selectors point into original query result artifacts (e.g. /detail/summary/terminal_speed_m_s), not observation envelopes. report.source is the supplied binding; recommendation configuration_scope is identities.configuration. Recommendations may defer pending a check. Do not execute or select a numerical check in this phase.',
    response_initial='Read the initial report. Choose adopt, defer or reject yourself and independently choose request_check, verify_adopted_change or finish. defer + request_check is valid. Rejecting a recommendation need not end diagnosis. finish ends all workflow work. verify_adopted_change requires adoption of the exact existing parameter/value and only a temporary saved-state comparison. Adoption alone executes nothing. Explain the evidence basis.',
    check='Select one discriminating check based on unresolved hypotheses. Inspect retained evidence as needed to choose the operation and update_id. The host binds the chosen update\'s exact measured_initial_state and operation-defined input from the inventory controller file; do not copy vectors. prediction_braking uses current actual_tension_n; local_comparison uses previous actual_tension_n and requires the exact adopted parameter/value and a saved effective plan horizon of 0.01 s. prediction_braking compares held recorded input with an instantaneous braking box solution and requires no adoption. Choose update_id >= 1, hypotheses, fixed conditions, metrics, acceptance criteria and work_limits (wall_s <= 300; prediction_evaluations=2 or local_solves=2). Host fixes model.gvs@1.0.0, implicit Euler, 0.002 s step and 0.01 s horizon. At most two successful reading turns, then select the check. Do not overextend a local probe to the entire settling failure.',
    revision='Consume actual check_feedback and revise the previous report. The host links the immutable feedback envelope; do not supply check_results. Supply at least one relevant exact numeric fact selector from its result artifact when execution completed, and your interpretation. Explain which hypotheses are supported, weakened or unresolved and how the result changes or limits the next decision. Identify model, projected-state, input, integration and horizon limits. Failed or inconclusive checks permit honest delivery. No further check is authorized.',
    response_final='Read the revised report and actual feedback. Record your final recommendation disposition and reasoning. The one-check allowance is spent; next_action must be finish. Physical improvement was not evaluated.')
INSTRUCTIONS['initial']+=' Availability gaps must use inventory IDs and not_read, not_retained or retained_unavailable; identify needed information/capability and basis. Unlisted evidence uses source plus explicit basis. Full sampled backend q/qdot is retained, even though motion shows the final window. Raw weight magnitudes do not establish cost-term importance without actual contributions/scaling.'
INSTRUCTIONS['check']+=' State local_question, competing hypotheses, discriminating_observations and unresolved questions. If hypotheses predict the same result, explicitly say this check cannot separate them. Select a question the stated capability can answer; no dominant-cause claim.'
INSTRUCTIONS['revision']+=' Use inventory-linked gap declarations. Do not infer physical feedback delay from synchronous wall-clock deadline misses or cost importance from raw weights.'


def save(store,value):
    with store.transaction() as db:return plain(store.put(db,value))


def implementation():
    paths=['examples/stage359_continuation.py','examples/stage359_live_continuation.py','tests/test_stage359_explicit.py',
        'extensions/tendon_family/optimization.py','extensions/tendon_family/manifest.py','tests/test_stage359_continuation.py',
        'tools/diagnostic_handoff.py','tools/platform_search.py','tools/working_state.py','schemas/working_state.py',
        'examples/stage356_milestone2.py','examples/stage357_live_pilot.py','examples/stage358_confirmation.py','examples/stage358_interpretation_repair.py','tests/test_stage358_interpretation_repair.py','tests/test_stage358_confirmation.py','tests/test_stage356_milestone2.py','tests/test_stage356_batch.py','tests/test_stage357_live_batch.py',
        'tools/diagnostic_reference_adapter.py','tools/diagnostic_revision.py','schemas/diagnostic_revision.py','tools/diagnostic_workflow.py','tools/diagnostic_native.py','tools/diagnostic_inventory.py','tools/diagnostic_facts.py',
        'tools/diagnostic_summary.py','tools/live_batch_execution.py','extensions/tendon_family/diagnostic_evidence.py','tools/execution_completion.py',
        'tools/platform_models.py','tools/platform_handoff.py','tools/platform_diagnosis_coordinator.py',
        'tools/platform_host.py','tools/platform_store.py','schemas/platform_handoff.py','schemas/platform_diagnostics.py',
        'extensions/platform/manifest.py','extensions/tendon_family/diagnostic_evidence.py','extensions/tendon_family/diagnostic_math.py',
        'tools/model_transports/deepseek.py','examples/stage346_shared_diagnosis.py','examples/stage348_experiment.json','examples/stage349_experiment.json',
        'tools/diagnostic_improvement.py','tools/platform_tools.py','extensions/tendon_family/candidate.py',
        'examples/gvs_design_input.py','examples/gvs_nmpc_route_experiment.py','tasks/reach_free/task.yaml']
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


class DiagnosticWorkflow:
    limits = LIMITS
    tools = TOOLS
    scope = SCOPE
    capabilities = CAPABILITIES
    instructions = INSTRUCTIONS
    permissions = PERMISSIONS
    phases = PHASES
    numerical_limits = NUMERICAL
    def __init__(self, directory, mode, *, pilot=False, minimal=False, suffix=False, initial_only=False, experiment=None):
        if mode not in ('single_context','dual_context'):raise ValueError('UNKNOWN_ORGANIZATION_MODE')
        self.directory=Path(directory);self.mode=mode;self.pilot=pilot;self.minimal=minimal
        self.suffix=suffix
        self.initial_only=initial_only
        self.store=Store(directory);self.chain={};self.previous=None
        self.experiment=deepcopy(experiment or {})
        self.source=Path(self.experiment.get('source_store',SOURCE))
        self.execution=self.experiment.get('execution_id',EXECUTION)
        self.export_root=Path(self.experiment.get('evidence_directory',ROOT/'evidence/stage346_shared_diagnosis_20261002'))

    def prepare(self,runtime,*,resume_preparation=False):
        if (self.directory/'freeze.json').exists():raise ValueError('NEW_RUN_DIRECTORY_REQUIRED')
        if not (self.source/'platform.sqlite').exists():
            manifest=ROOT/'evidence/stage341_repaired_live_execution_20261001/live_outcome.json'
            raise ValueError('SEALED_SOURCE_STORE_UNAVAILABLE; explicit portable outcome: '+str(manifest)+'; no substitution permitted')
        reader=ControlEvidence(Store(self.source));source=reader.resolve(self.execution)
        if self.experiment.get('source_manifest',source['manifest'])!=source['manifest']:raise ValueError('FROZEN_SOURCE_MANIFEST_MISMATCH')
        self.project=self.experiment.get('project_prefix','gvs-stage346')+'-'+uuid4().hex[:12]
        limits=SUFFIX_LIMITS if self.suffix or self.initial_only else (dict(model_calls=3,tool_calls=3,backend_solves=0,worker_calls=0,wall_s=300.) if self.minimal else self.limits)
        numerical={k:0 for k in NUMERICAL} if self.suffix or self.initial_only else self.numerical_limits
        self.limits=limits
        if resume_preparation and self.store.db.exists():
            with self.store.connect(True) as db:
                if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:raise ValueError('PARTIAL_SESSIONS_REQUIRE_RECONCILIATION')
            if self.store.remaining()['used']!={'model_calls':0,'tool_calls':0,'backend_solves':0,'worker_calls':0,'wall_s':0.}:
                raise ValueError('PREPARATION_ALREADY_CHARGED')
            prior=self.store.config()
            if prior['budget']!=limits:raise ValueError('PREPARATION_BUDGET_MISMATCH')
            self.project=prior['project_id']
        else:
            self.store.create(dict(project_id=self.project,grant_id=self.project,budget=limits,
                authorization_source=self.experiment.get('authorization_source','User-authorized sequential Stage 3.46 native validation, pilot and two matched pairs; necessary context/evidence transmission to DeepSeek; no backend simulations/workers or push.')))
        self.hosts={}
        for role in (['shared'] if self.mode=='single_context' else ['design','diagnostic'])+['executor']:
            host=Host(self.directory,self.project+'-'+role);inp=deepcopy(source['configuration']);inp['run_id']=host.run_id
            bindings={'diagnosis.inspect_evidence':'1.0.0','diagnosis.saved_state_check':'1.0.0'} if role=='executor' else self.tools
            if (self.suffix or self.initial_only) and role=='executor':bindings={'diagnosis.inspect_evidence':'1.0.0'}
            inp['policy'].update(route=None,budget={**limits,'model_calls':0 if role=='executor' else limits['model_calls']},
                timeout_s=900. if role=='executor' else 30.,allowed_tools=[],tool_bindings=bindings)
            provider=read(Path(self.experiment.get('provider_freeze',ROOT/'evidence/stage346_shared_diagnosis_20261002/pilot/freeze.json')))['provider_configuration']
            inp['policy']['model']={**provider,'adapter_version':self.experiment.get('adapter_version','4.0.0'),'max_turns':24,
                'tool_naming':tool_naming_policy(bindings,READABLE_TOOL_NAMING)}
            if 'context_bytes' in self.experiment:
                inp['policy']['model']['context_bytes']=self.experiment['context_bytes']
            if 'context_guard' in self.experiment:
                inp['policy']['model']['context_guard']=self.experiment['context_guard']
            host.create(inp);self.hosts[role]=host
        self.binding=import_execution(reader,self.execution,self.store,self.hosts['executor'].run_id,source['manifest'])
        if self.experiment.get('fact_handles'):
            with self.store.transaction() as db:
                for host in self.hosts.values():
                    state=self.store.session(host.run_id,db)['state']
                    state['fact_scope']=dict(project=self.project,binding=self.binding)
                    self.store.update_state(db,host.run_id,state)
        with self.store.transaction() as db:
            db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=numerical,used={k:0 for k in NUMERICAL})),))
        executor=self.hosts['executor'];executor.resume()
        receipt=executor.invoke(dict(request_id='inventory-summary',tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',
            arguments=dict(binding=self.binding,view='summary'),reason='Read preserved source summary',cache='new'))
        if receipt['execution_status']!='completed':raise ValueError('SOURCE_SUMMARY_FAILED: '+str(receipt['error']))
        self.summary=receipt['output'];self.inventory=evidence_inventory(reader,source)
        self.inventory_ref=save(self.store,self.inventory)
        b=self.store.artifact(self.binding)
        self.identities={k:b[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest','configuration')}
        if self.suffix:self.import_feedback_suffix()
        self.freeze=dict(schema_version='1.0.0',project_id=self.project,mode=self.mode,pilot=self.pilot,minimal=self.minimal,suffix=self.suffix,initial_only=self.initial_only,
            hosts={k:h.run_id for k,h in self.hosts.items()},binding=self.binding,identities=self.identities,summary=self.summary,
            inventory=self.inventory,inventory_reference=self.inventory_ref,source_manifest=source['manifest'],
            implementation=implementation(),runtime=runtime,provider_configuration=self.store.session(self.host('design').run_id)['snapshot']['input']['policy']['model'],
            limits=limits,numerical_limits=numerical,scope=self.scope,memory_policy={**MEMORY,'context_bytes':self.experiment.get('context_bytes',MEMORY['context_bytes'])},fact_policy=FACT_POLICY,phase_budgets=self.phases,
            stage_instructions=self.instructions,permissions=self.permissions,capabilities=self.capabilities,experiment=self.experiment,
            recovery=recovery_status({},self.store.session(self.host('design').run_id)['snapshot']['input']['policy']['model']),
            host_provider_configurations={k:self.store.session(h.run_id)['snapshot']['input']['policy']['model'] for k,h in self.hosts.items()},
            tool_bindings=self.tools,review_rubric=read(ROOT/'evidence/stage346_shared_diagnosis_20261002/review_rubric.json'),
            outcomes=['workflow completion','exact selector validation','prose review','check usefulness','usage','physical improvement not evaluated'])
        atomic_json(self.directory/'freeze.json',self.freeze)
        return self.freeze

    def import_feedback_suffix(self):
        """Import a verified artifact closure; never copy sessions or their ledger."""
        old_root=Path(self.experiment['continuation_store']);old=Store(old_root)
        outcome=read(old_root/'outcome.json');chain=outcome['chain']
        saved_chain=read(old_root/'chain.json')
        if any(chain[k]!=v for k,v in saved_chain.items()):raise ValueError('CONTINUATION_CHAIN_MISMATCH')
        expected=self.experiment['continuation_feedback']
        if chain['feedback']!=expected:raise ValueError('CONTINUATION_FEEDBACK_MISMATCH')
        feedback=old.artifact(expected)
        if feedback!=read(old_root/'feedback.json'):raise ValueError('CONTINUATION_EXPORT_MISMATCH')
        if feedback['receipt']['execution_status']!='completed' or feedback['result']!=self.experiment['continuation_result']:
            raise ValueError('CONTINUATION_COMPLETED_RESULT_REQUIRED')
        if feedback['receipt']['execution_id']!=self.experiment['continuation_execution']:raise ValueError('CONTINUATION_EXECUTION_MISMATCH')
        request=old.artifact(chain['request'])
        if request['binding']!=self.binding or request['execution_id']!=self.execution:raise ValueError('CONTINUATION_SOURCE_MISMATCH')
        if feedback['check_request']!=chain['check'] or feedback['diagnosis_request']!=chain['request']:
            raise ValueError('CONTINUATION_LINK_MISMATCH')
        exported=self.experiment['continuation_exports']
        seen={}
        def collect(value):
            if isinstance(value,dict):
                if set(value)=={'artifact_id','media_type'}:
                    key=value['artifact_id']
                    if key in seen:return
                    body=old.artifact(value,raw=True);seen[key]=(value,body)
                    if value['media_type']=='application/json':collect(json.loads(body))
                else:
                    for child in value.values():collect(child)
            elif isinstance(value,list):
                for child in value:collect(child)
        self.chain={k:chain[k] for k in ('request','initial_report','initial_response','check','feedback')}
        for ref in self.chain.values():collect(ref)
        for ref in (expected,feedback['result']):
            if read(Path(exported)/'artifacts'/(ref['artifact_id']+'.json'))!=old.artifact(ref):raise ValueError('CONTINUATION_ARTIFACT_EXPORT_MISMATCH')
        with self.store.transaction() as db:
            for ref,body in seen.values():
                if plain(self.store.put(db,body,ref['media_type']))!=ref:raise ValueError('IMPORT_HASH_MISMATCH')
            provenance=dict(classification='cross-run continuation using preserved real numerical feedback',
                original_store=str(old_root),original_status=outcome['status'],original_stop_reason=outcome['stop_reason'],
                historical_usage=outcome['usage'],historical_numerical_work=outcome['numerical_work'],
                numerical_execution=feedback['receipt']['execution_id'],chain=self.chain,imported_references=[r for r,b in seen.values()],
                new_phases=['revision','response_final'],fresh_authorization=True,
                memory='Fresh structured memories with explicit preserved handoffs; no historical rejected drafts or transcript replay.')
            ref=self.store.put(db,provenance)
            self.store.event(db,self.host('diagnostic').run_id,'cross_run_continuation','imported',inputs=list(self.chain.values()),outputs=[ref])
        atomic_json(self.directory/'continuation_provenance.json',provenance)
        for key,ref in self.chain.items():atomic_json(self.directory/(key+'.json'),self.store.artifact(ref))
        atomic_json(self.directory/'chain.json',self.chain)

    def finish_feedback(self,retained):
        self.phase('revision','diagnosis_report','revised_report',previous_report=self.chain['initial_report'],
            previous_report_content=self.store.artifact(self.chain['initial_report']),check_feedback=retained,max_checks=1)
        self.phase('response_final','design_response','final_response',check_feedback=retained)

    def host(self,role):return self.hosts['shared' if self.mode=='single_context' else role]

    def fixed(self,phase):
        fixed={'diagnosis.inspect_evidence':dict(binding=self.binding)}
        if phase=='request':
            fixed['diagnosis.request']=dict(subject='control',binding=self.binding,
                **{k:self.identities[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest')},
                permitted_tools=['diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read'],
                budget=self.limits,saved_state_check=None if self.initial_only else SCOPE)
        if phase in ('initial','revision'):
            fixed['diagnosis.submit']=dict(request=self.chain['request'],previous_report=self.chain.get('initial_report') if phase=='revision' else None,
                check_results=[self.chain['feedback']] if phase=='revision' else [])
        if phase.startswith('response'):
            fixed['design.respond_diagnosis']=dict(report=self.chain['revised_report' if phase=='response_final' else 'initial_report'])
        if phase=='check':fixed['diagnosis.check_request']=dict(check_id='saved-state-check',diagnosis_request=self.chain['request'],model=SCOPE['model'],
            horizon_s=SCOPE['horizon_s'],integration=SCOPE['integration'],integration_step_s=SCOPE['integration_step_s'])
        return fixed

    def phase(self,phase,kind,key,**extra):
        role='design' if phase in ('request','response_initial','response_final','improvement') else 'diagnostic'
        host=self.host(role)
        if self.previous is not None and host.run_id!=self.previous.run_id:transfer_recovery(self.previous,host)
        state=self.store.session(host.run_id)['state']
        common=dict(binding=self.binding,identities=self.identities,summary=self.summary,
            summary_content=self.store.artifact(self.summary),inventory=self.inventory,inventory_reference=self.inventory_ref,
            protocol=dict(saved_state_check=self.scope) if self.scope else {},capabilities=self.capabilities,diagnostic_tools=list(self.tools),phase=phase,
            memory_identity=host.run_id,working_memory=state.get('workflow_memory',[]),memory_policy=MEMORY,
            phase_budget=self.phases[phase],phase_tools=self.permissions[phase],native_fixed=self.fixed(phase),native_store_root=str(self.directory),
            evidence_turn_limit=2 if phase in ('request','initial','check') else 0)
        if self.minimal:common['phase_budget']=dict(limit=dict(model_calls=3,tool_calls=3,wall_s=300.))
        if self.initial_only:
            common['protocol']={}
            common['phase_budget']=(dict(limit=dict(model_calls=3),protect_project=dict(model_calls=5,tool_calls=10,wall_s=600.))
                if phase=='request' else dict(limit=dict(model_calls=5)))
        if 'request' in self.chain:common.update(request=self.chain['request'],request_content=self.store.artifact(self.chain['request']))
        if phase.startswith('response'):
            report=self.chain['revised_report' if phase=='response_final' else 'initial_report']
            common.update(report=report,report_content=self.store.artifact(report),final_response=phase=='response_final')
        instruction=self.instructions[phase]
        instruction+=' Claims of dominant causes or ineffectiveness throughout a parameter range must state their evidential scope. Distinguish observations, hypotheses and proposed tests. A small unsuccessful batch only describes tested candidates. Raw termination and controller policy stops are separate. Zero bound violation does not exclude legal near-bound input.'
        if self.experiment.get('fact_handles'):
            instruction=instruction.replace('2-4 exact selected facts','2-4 facts selected using fact_handles').replace(
                'Fact selectors point into original query result artifacts (e.g. /detail/summary/terminal_speed_m_s), not observation envelopes. report.source is the supplied binding; recommendation configuration_scope is identities.configuration.',
                'Use the current fact_catalog; the host resolves selectors, report.source and recommendation configuration_scope.').replace(
                'at least one relevant exact numeric fact selector from its result artifact','at least one relevant numeric fact handle from the actual result artifact').replace(
                'not_read, not_retained or retained_unavailable','not_displayed, not_read, queried, not_retained or retained_unavailable')
            instruction+=' Availability status applies to the entire inventory entry unless you supply update_ids (controller updates) or time_range_s (sampled backend motion). For a partially read entry, use queried and describe missing coverage, or explicitly scope a not_read/not_displayed declaration to the unread subset.'
        if self.initial_only:
            instruction+=' Partial initial-report capability validation only: no check selection/execution, backend, or workers. Request scope must exclude numerical work in this run.'
        if self.pilot and phase=='response_initial':instruction+=' This development pilot requires one genuine check and report revision to validate feedback capability. Select a justified check action; retain your own disposition and engineering conclusion.'
        configure_role(host,role,instruction,**{**common,**extra})
        if self.experiment.get('fact_handles'):
            handover(host,self.summary,self.store.artifact(self.summary),origin=dict(context=self.hosts['executor'].run_id,receipt='inventory-summary'),kind='common_summary')
            # Transfer only the accepted report's cited facts, not the other role's query history.
            report=common.get('report_content') or extra.get('previous_report_content')
            report_ref=common.get('report') or extra.get('previous_report')
            if report and report_ref:
                selectors=[s for rows in report.get('fact_selectors',{}).values() for s in rows]
                handover(host,report_ref,report,origin=dict(kind='accepted_report',reference=report_ref),kind='report_facts',selectors=selectors)
            for feedback in extra.get('check_feedback',[]):
                if feedback.get('result_content') is not None:
                    handover(host,feedback['result'],feedback['result_content'],origin=dict(feedback=feedback['reference'],receipt=feedback['receipt']),kind='numerical_result')
        before=self.store.session(host.run_id)['state'].get('handoffs',{}).get(kind)
        print('PHASE',self.directory.name,phase,flush=True)
        if hasattr(self,'check_provider_payload'):self.check_provider_payload(host)
        run_loop(host)
        state=self.store.session(host.run_id)['state'];ref=state.get('handoffs',{}).get(kind)
        if not ref or ref==before:raise RuntimeError('PHASE_INCOMPLETE '+phase+': '+str(state.get('stop_reason')))
        self.chain[key]=ref;self.previous=host
        with self.store.transaction() as db:
            state=self.store.session(host.run_id,db)['state'];content=self.store.artifact(ref)
            entry=dict(phase=phase,reference=ref)
            if len(encode(content).encode())<=MEMORY['product_bytes']:entry['content']=content
            products=(state.get('workflow_memory',[])+[entry])[-MEMORY['products']:]
            while len(encode(products).encode())>MEMORY['total_product_bytes']:products.pop(0)
            state['workflow_memory']=products
            self.store.update_state(db,host.run_id,state)
        atomic_json(self.directory/(key+'.json'),self.store.artifact(ref));atomic_json(self.directory/'chain.json',self.chain)
        return ref

    def run(self):
        started=time.monotonic();status='incomplete';reason=None
        guard=self.directory/'live_attempt.json'
        if guard.exists():raise RuntimeError('LIVE_ATTEMPT_ALREADY_STARTED: counters may not be replenished')
        if implementation()['files']!=self.freeze['implementation']['files']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        self.validate_frozen_configuration()
        atomic_json(guard,dict(started=datetime.now(timezone.utc).isoformat()))
        try:
            if self.suffix:
                from tools.platform_diagnosis_coordinator import feedback_content
                feedback=self.store.artifact(self.chain['feedback'])
                self.finish_feedback([dict(reference=self.chain['feedback'],**feedback,
                    result_content=feedback_content(self.store,feedback['result']))])
                status='completed';reason='Cross-run preserved feedback consumed; accepted revision and final decision.'
            elif self.minimal:
                report=read(ROOT/'evidence/stage345_diagnostic_cycle_20261002/saved_diagnosis_report.json')
                self.chain['initial_report']=save(self.store,report)
                self.phase('response_initial','design_response','initial_response',
                    factual_review=read(ROOT/'evidence/stage345_diagnostic_cycle_20261002/delivery_review.json'),
                    validation_scope='Cross-run native protocol unit only, not a same-session diagnosis cycle. No check executes.')
                status='completed';reason='Native response validated; cross-run protocol unit only.'
            else:
                self.phase('request','diagnosis_request','request')
                self.phase('initial','diagnosis_report','initial_report',require_initial_views=True,
                    scheduling='Synchronous controller calls complete before fixed-count backend steps; wall deadline misses do not inject physical delay into simulated time.')
                if self.initial_only:
                    status='completed';reason='Accepted initial report; partial capability validation only, no check or complete diagnostic workflow.'
                    self.export(status,reason,time.monotonic()-started)
                    return read(self.directory/'outcome.json')
                self.phase('response_initial','design_response','initial_response')
                response=self.store.artifact(self.chain['initial_response'])
                if response['next_action']=='finish':
                    status='completed';reason='Model chose finish after initial report; no check executed.'
                else:
                    adopted=None
                    if response['disposition']=='adopt':
                        rec=next(r for r in self.store.artifact(self.chain['initial_report'])['recommendations'] if r['recommendation_id']==response['recommendation_id'])
                        if rec['action']=='control_parameter':adopted=dict(parameter=rec['parameter'],value=rec['value'])
                    self.phase('check','diagnostic_check','check',previous_report=self.chain['initial_report'],
                        previous_report_content=self.store.artifact(self.chain['initial_report']),design_response=self.chain['initial_response'],
                        design_response_content=response,adopted_parameter=adopted,max_checks=1,check_execution_enabled=True,check_feedback=[])
                    check=self.store.artifact(self.chain['check'])
                    if response['next_action']=='verify_adopted_change' and check['operation']!='local_comparison':raise ValueError('VERIFY_ACTION_REQUIRES_LOCAL_COMPARISON')
                    diagnostic=self.host('diagnostic');executor=self.hosts['executor']
                    configure_role(executor,'executor','Execute one saved-state check',phase_budget=dict(limit=dict(tool_calls=1,wall_s=300.),
                        protect_project=dict(model_calls=7,tool_calls=7,wall_s=600.)))
                    feedback=execute_check_feedback(diagnostic,executor,self.chain['check']);self.chain['feedback']=feedback
                    atomic_json(self.directory/'feedback.json',self.store.artifact(feedback))
                    retained=self.store.session(diagnostic.run_id)['state']['role_context']['check_feedback']
                    self.finish_feedback(retained)
                    status='completed';reason='Check feedback consumed, revised report and final decision delivered.'
        except Exception as exc:
            reason=str(exc);atomic_json(self.directory/'workflow_failure.json',dict(type=type(exc).__name__,message=reason))
            print('STOP',reason,flush=True)
        self.export(status,reason,time.monotonic()-started)
        return read(self.directory/'outcome.json')

    def export(self,status,reason,elapsed):
        destination=self.export_root/self.directory.name
        destination.mkdir(parents=True,exist_ok=True);artifacts=destination/'artifacts';artifacts.mkdir(exist_ok=True)
        events=[];receipts=[];raw=[];resolved=[];usage_rows=[];refs={}
        def include(ref):
            if ref and ref['media_type']=='application/json':refs[ref['artifact_id']]=ref
        for host in self.hosts.values():
            for e in self.store.events(host.run_id):
                events.append(e)
                for ref in e['inputs']+e['outputs']:include(ref)
                if e['kind']=='model_raw_response':
                    value=self.store.artifact(e['outputs'][0]);raw.append(dict(run_id=host.run_id,reference=e['outputs'][0],response=value))
                    if value.get('raw',{}).get('usage'):usage_rows.append(value['raw']['usage'])
                if e['kind']=='model_decision':resolved.append(dict(run_id=host.run_id,reference=e['outputs'][0],invocation=self.store.artifact(e['outputs'][0])))
            with self.store.connect(True) as db:
                for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(host.run_id,)):
                    r=json.loads(row[0]);receipts.append(r);include(r.get('output'))
        with self.store.connect(True) as db:work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
        feedback=self.store.artifact(self.chain['feedback']) if self.chain.get('feedback') else None
        for ref in self.chain.values():include(ref)
        if feedback:include(feedback.get('result'))
        outcome=dict(schema_version='1.0.0',status=status,stop_reason=reason,mode=self.mode,pilot=self.pilot,minimal=self.minimal,
            classification='partial initial-report capability validation' if self.initial_only else ('cross-run continuation using preserved real numerical feedback' if self.suffix else 'fresh workflow'),
            chain=self.chain,feedback_complete=all(k in self.chain for k in ('check','feedback','revised_report','final_response')),
            numerical_check_status=(feedback.get('receipt') or {}).get('execution_status') if feedback else None,
            usage=self.store.remaining(),numerical_work=work,provider_usage=usage_rows,monetary_cost=None,elapsed_s=elapsed,
            protocol_corrections=max(self.store.session(h.run_id)['state'].get('protocol_corrections_used',0) for h in self.hosts.values()),
            recovery={k:recovery_status(self.store.session(h.run_id)['state'],self.store.session(h.run_id)['snapshot']['input']['policy']['model']) for k,h in self.hosts.items()},
            physical_improvement='not evaluated',source_preserved=ControlEvidence(Store(self.source)).resolve(self.execution)['manifest']==self.freeze['source_manifest'])
        atomic_json(self.directory/'outcome.json',outcome)
        for path in self.directory.glob('*.json'):atomic_json(destination/path.name,read(path))
        for name,value in [('events',events),('receipts',receipts),('raw_calls',raw),('resolved_calls',resolved)]:atomic_json(destination/(name+'.json'),value)
        atomic_json(destination/'evidence_contexts.json',{k:{field:self.store.session(h.run_id)['state'].get(field)
            for field in ('fact_scope','fact_catalog','reference_interface','read_ledger')} for k,h in self.hosts.items()})
        for ref in refs.values():(artifacts/(ref['artifact_id']+'.json')).write_bytes(self.store.artifact(ref,raw=True))
        atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob('*.json')) if p.name!='sha256_manifest.json'})
        print('OUTCOME',status,'USAGE',outcome['usage']['used'],flush=True)

    def validate_frozen_configuration(self):
        for name,host in self.hosts.items():
            actual=self.store.session(host.run_id)['snapshot']['input']['policy']['model']
            if actual!=self.freeze['host_provider_configurations'][name]:raise ValueError('FROZEN_PROVIDER_CONFIGURATION_MISMATCH: '+name)
        for key,value in [('stage_instructions',self.instructions),('permissions',self.permissions),('phase_budgets',self.phases),('scope',self.scope),('memory_policy',{**MEMORY,'context_bytes':self.experiment.get('context_bytes',MEMORY['context_bytes'])}),('capabilities',self.capabilities),('experiment',self.experiment)]:
            if value!=self.freeze[key]:raise ValueError('FROZEN_CONFIGURATION_MISMATCH: '+key)


class EvidenceDrivenWorkflow(DiagnosticWorkflow):
    """Milestone 2 phases on the existing sequential host and shared ledger."""
    limits=dict(model_calls=24,tool_calls=60,backend_solves=0,worker_calls=0,wall_s=1800.)
    numerical_limits=dict(local_solves=2,prediction_evaluations=2)
    scope={**SCOPE,'max_wall_s':180.,'numerical_limits':numerical_limits}
    tools={**TOOLS,'design.respond_diagnosis':'4.0.0','design.assess_diagnosis':'1.0.0',
        'diagnosis.propose_check':'1.0.0','diagnosis.revise_assessment':'1.0.0','design.submit_search_plan':'1.0.0'}
    permissions=dict(initial=['diagnosis.submit'],response_initial=['design.assess_diagnosis'],
        check=['diagnosis.propose_check'],revision=['diagnosis.revise_assessment'],
        improvement=['design.submit_search_plan'],response_final=['design.respond_diagnosis'])
    phases=dict(initial=dict(limit=dict(model_calls=4),protect_project=dict(model_calls=14,tool_calls=12,wall_s=900.)),
        response_initial=dict(limit=dict(model_calls=3),protect_project=dict(model_calls=11,tool_calls=10,wall_s=800.)),
        check=dict(limit=dict(model_calls=5),protect_project=dict(model_calls=6,tool_calls=6,wall_s=600.)),
        revision=dict(limit=dict(model_calls=4),protect_project=dict(model_calls=4,tool_calls=4,wall_s=300.)),
        improvement=dict(limit=dict(model_calls=4),protect_project=dict(model_calls=2,tool_calls=2,wall_s=150.)),
        response_final=dict(limit=dict(model_calls=4)))
    capabilities={**CAPABILITIES,'evidence_query':'One model-selected archived prediction, plans or motion query with explicit coverage. The proposal precedes the query; newly read details may distinguish an assessment without numerical work.'}
    instructions=dict(
        initial='Use the common accepted historical report, current candidate feedback, summary and honest inventory. Author a concise initial assessment as diagnosis.submit, using exact F aliases for 2-4 facts. Author hypotheses with meaningful identifiers, explicit uncertainty and advisory recommendations; do not impose a dominant cause. No query yet. All supplied historical values are already known; selected prediction/plan detail has not been inspected in this fresh context. Do not call existing supplied results missing. No fixed hypothesis count.',
        response_initial='Use design.assess_diagnosis to respond to the accepted initial assessment. Select your recommendation disposition independently. This milestone requires a recorded check, then revision and a future plan; next_action=request_check is appropriate. Adoption of an exact existing control_parameter recommendation can enable local_comparison; it changes no production candidate. You may defer and choose an archived query or prediction_braking. Do not select a check here.',
        check='Record a CheckProposal through diagnosis.propose_check before obtaining its result. Identify a meaningful declared question, checked assessment IDs from the accepted report, evidence relationships with relevance to those IDs, missing detail, expected outcomes/effects and why they distinguish your question. A relationship must concern its named hypothesis. Terminal reach success is compatible with holding speed failure; do not fabricate contradicting evidence. Prefer an archived evidence_query when retained details can answer the question. Choose prediction/plans and explicit update_ids (at most 8), or motion for the final holding window. Specify units, work_limits={wall_s: at most 180, tool_calls:1}, limits and stopping conditions. Numerical operations require one eligible update ID, null view, and local_solves:2 or prediction_evaluations:2; max_checks=1 shared across operations. Numerical local_comparison additionally requires exact prior design adoption and matching saved horizon. Do not truncate horizons. No production changes/backend solves.',
        revision='Submit a CheckedRevision through diagnosis.revise_assessment using 1-6 new unique facts with exact result aliases. Address every checked assessment by identifier and mark retained, weakened, rejected or unresolved; supporting_fact_ids name report fact IDs, never aliases. At least one new result detail beyond initial supplied summaries must be linked to an assessment. Interpret the received result and its supplied coverage against the proposed question and expected observations; explain the change, remaining uncertainty and resolving evidence. An unresolved interpretation is valid. Inherited facts are host-preserved. Separate applied updates from optimized selections, wall deadlines from simulated steps, termination from convergence, terminal reach from holding, and projected predictions from measured motion.',
        improvement='Author one future SearchBatchPlan through design.submit_search_plan from the accepted revision and performed check. Cite exact F aliases including a result alias; choose your scientific promise and rationale. Variables are only control/recipe/terminal_tip_speed_weight and control/recipe/holding_tip_speed_weight within existing granted bounds. Saved starting values must lie within domains. Domains use zero or >=0.0001; a coordinate step must avoid forbidden tiny positives. Use installed method search.family_coordinate@1.0.0, max_candidates 1..12 and step (0,1]. This method supplies candidate ask/tell only; future evaluation and frozen comparison are required. fixed_controller is controller.gvs_nmpc@7.0.0. fixed_conditions must include robot,task,acceptance,controller_implementation,other_numerical_settings. objectives include joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s (optional complete_update_s). constraints include frozen_acceptance,force_bounds,finite_valid_execution. verification includes candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. Planned budget: backend_solves=max_candidates, tool_calls>=4*max_candidates, wall_s>=990*max_candidates, workers=0; state provider attempts if needed. Include hypothesis, weakening observations, fidelity limits and explicit stopping conditions. Local/raw weighted costs cannot be final physical ranking. A validated plan requires a future grant; this stage executes no batch and promotes no candidate.',
        response_final='Read the accepted revision, performed check interpretation and validated future search plan. Author your final recommendation disposition and separate candidate_disposition/selected_candidate using the exact historical evidence. next_action=finish. Explain diagnostic value and remaining uncertainty; a future plan is not an execution grant or evidence of physical improvement. Do not infer causal truth from validated citations.')

    def fixed(self,phase):
        fixed=super().fixed(phase)
        if phase=='response_initial':
            fixed.pop('design.respond_diagnosis',None)
            fixed['design.assess_diagnosis']=dict(report=self.chain['initial_report'])
        return fixed

    def phase(self,phase,kind,key,**extra):
        extra.update(source_report=self.common['source_report'],source_record=self.source_record,
            source_report_content=self.store.artifact(self.common['source_report']),
            historical_feedback=self.common['feedback'],improvement_feedback_content=self.historical_feedback,
            numerical_eligibility=self.eligibility,common_scientific_input=self.common,
            previous_report=self.chain.get('revised_report') if phase in ('improvement','response_final') else self.chain.get('initial_report'))
        if extra.get('previous_report'):extra['previous_report_content']=self.store.artifact(extra['previous_report'])
        if phase=='response_initial':extra['delivery_tool']='design.assess_diagnosis'
        if phase=='improvement':extra['delivery_tool']='design.submit_search_plan'
        if self.chain.get('feedback'):extra.update(result_feedback=self.chain['feedback'],proposal=self.chain['check'],
            performed_check=self.store.artifact(self.chain['check'])['proposal'],received_result=self.store.artifact(self.chain['feedback']))
        if phase=='response_final':
            extra.update(experiment_plan=self.chain['search_plan'],search_plan_content=self.store.artifact(self.chain['search_plan']),
                check_feedback=[dict(reference=self.common['feedback'])])
        for role in ('diagnostic','design'):
            host=self.host(role)
            handover(host,self.common['feedback'],self.historical_feedback,origin=dict(kind='verified_historical_feedback'),kind='campaign_comparison')
            handover(host,self.common['source_report'],self.store.artifact(self.common['source_report']),origin=dict(kind='verified_accepted_source'),
                kind='accepted_source_report',selectors=[s for rows in self.store.artifact(self.common['source_report'])['fact_selectors'].values() for s in rows])
        return super().phase(phase,kind,key,**extra)

    def run(self):
        started=time.monotonic();status='incomplete';reason=None;guard=self.directory/'live_attempt.json'
        if guard.exists():raise ValueError('LIVE_ATTEMPT_ALREADY_STARTED: never reset counters')
        if implementation()!=self.freeze['implementation']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        self.validate_frozen_configuration()
        atomic_json(guard,dict(started=datetime.now(timezone.utc).isoformat()))
        try:
            self.phase('initial','diagnosis_report','initial_report')
            self.phase('response_initial','design_response','initial_response')
            response=self.store.artifact(self.chain['initial_response'])
            if response['next_action']=='finish':raise ValueError('MILESTONE2_UNMET: model stopped before the required check')
            adopted=None
            if response['disposition']=='adopt':
                rec=next(r for r in self.store.artifact(self.chain['initial_report'])['recommendations'] if r['recommendation_id']==response['recommendation_id'])
                if rec['action']=='control_parameter':adopted=dict(parameter=rec['parameter'],value=rec['value'])
            self.phase('check','diagnostic_check','check',adopted_parameter=adopted,max_checks=1,check_feedback=[])
            check=self.store.artifact(self.chain['check']);proposal=check['proposal'];executor=self.hosts['executor']
            if response['next_action']=='verify_adopted_change' and proposal['operation']!='local_comparison':raise ValueError('VERIFY_ACTION_REQUIRES_MATCHED_LOCAL_COMPARISON')
            configure_role(executor,'executor','Execute the recorded model-selected check only.',
                phase_tools=['diagnosis.inspect_evidence','diagnosis.saved_state_check'],
                phase_budget=dict(limit=dict(tool_calls=1,wall_s=180.),protect_project=dict(model_calls=6,tool_calls=6,wall_s=600.)))
            executor.resume()
            numerical=check.get('numerical')
            invocation=dict(request_id='milestone2-selected-check',tool_id='diagnosis.saved_state_check' if numerical else 'diagnosis.inspect_evidence',
                tool_version='1.0.0',arguments=numerical or dict(binding=self.binding,view=proposal['view'],update_ids=proposal['update_ids']),
                reason='Obtain the result of the previously accepted model-authored proposal.',evidence=[self.chain['check']],cache='new')
            receipt=executor.invoke(invocation)
            from tools.diagnostic_facts import record_read
            if not numerical:record_read(self.host('diagnostic'),invocation,receipt)
            state=self.store.session(self.host('diagnostic').run_id)['state']
            coverage=state.get('read_ledger',[])[-1].get('coverage') if not numerical else dict(update_ids=proposal['update_ids'],horizon_s=.01,integration_step_s=.002,model='model.gvs@1.0.0')
            feedback=dict(proposal=self.chain['check'],previous_assessment=self.chain['initial_report'],receipt=receipt,result=receipt.get('output'),
                kind='newly_computed_local_evidence' if numerical else 'newly_read_historical_evidence',coverage=coverage,
                execution_id=self.execution,binding=self.binding,diagnosis_request=self.chain['request'])
            self.chain['feedback']=save(self.store,feedback)
            atomic_json(self.directory/'feedback.json',feedback)
            if receipt['execution_status']!='completed':raise ValueError('MILESTONE2_CHECK_FAILED: '+str(receipt.get('error')))
            content=self.store.artifact(receipt['output'])
            for role in ('diagnostic','design'):
                handover(self.host(role),receipt['output'],content,origin=dict(proposal=self.chain['check'],receipt=receipt),kind='selected_check_result')
            retained=[dict(reference=self.chain['feedback'],**feedback,result_content=content)]
            self.phase('revision','diagnosis_report','revised_report',check_feedback=retained)
            # Consume a second handoff from the accepted revision, preserving
            # relationships and binding the new result receipt and report chain.
            from tools.working_state import project_working_state
            from tools.diagnostic_handoff import bind_handoff
            diagnostic=self.host('diagnostic');role=dict(self.store.session(diagnostic.run_id)['state']['role_context'],previous_report=self.chain['revised_report'])
            assessments=deepcopy(check['handoff']['assessments'])
            revised=self.store.artifact(self.chain['revised_report'])
            for assessment,key in zip(assessments,proposal['assessment_ids']):
                row=next(r for r in revised['report']['attribution'] if r['cause']==key)
                assessment.update(statement=key+': '+row['reason'],previous_assessment=self.chain['initial_report'],changed_by=[self.chain['feedback']])
            handoff=bind_handoff(self.store,project_working_state(self.store,diagnostic.run_id),role,assessments,check['handoff']['check'],check_result=self.chain['feedback'])
            self.chain['revised_handoff']=save(self.store,handoff)
            self.phase('improvement','search_batch_plan','search_plan')
            self.phase('response_final','design_response','final_response')
            status='completed';reason='Accepted host-bound diagnostic products, recorded check, evidence-dependent revision, valid future batch plan and model final decision.'
        except Exception as exc:
            reason=str(exc);atomic_json(self.directory/'workflow_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
        self.export(status,reason,time.monotonic()-started)
        return read(self.directory/'outcome.json')
