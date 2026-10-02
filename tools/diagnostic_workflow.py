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
from tools.state_io import read, atomic_json
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution, BoundReader

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'
LIMITS=dict(model_calls=24,tool_calls=60,backend_solves=0,worker_calls=0,wall_s=3600.)
NUMERICAL=dict(local_solves=6,prediction_evaluations=24)
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
    revision='Consume actual check_feedback and revise the previous report. Cite the feedback in check_results and at least one relevant exact numeric selector from its result artifact when execution completed. Explain which hypotheses are supported, weakened or unresolved and how the result changes or limits the next decision. Identify model, projected-state, input, integration and horizon limits. Failed or inconclusive checks permit honest delivery. No further check is authorized.',
    response_final='Read the revised report and actual feedback. Record your final recommendation disposition and reasoning. The one-check allowance is spent; next_action must be finish. Physical improvement was not evaluated.')
INSTRUCTIONS['initial']+=' Availability gaps must use inventory IDs and not_read, not_retained or retained_unavailable; identify needed information/capability and basis. Unlisted evidence uses source plus explicit basis. Full sampled backend q/qdot is retained, even though motion shows the final window. Raw weight magnitudes do not establish cost-term importance without actual contributions/scaling.'
INSTRUCTIONS['check']+=' State local_question, competing hypotheses, discriminating_observations and unresolved questions. If hypotheses predict the same result, explicitly say this check cannot separate them. Select a question the stated capability can answer; no dominant-cause claim.'
INSTRUCTIONS['revision']+=' Use inventory-linked gap declarations. Do not infer physical feedback delay from synchronous wall-clock deadline misses or cost importance from raw weights.'


def save(store,value):
    with store.transaction() as db:return plain(store.put(db,value))


def implementation():
    paths=['tools/diagnostic_workflow.py','tools/diagnostic_native.py','tools/diagnostic_inventory.py',
        'tools/platform_models.py','tools/platform_handoff.py','tools/platform_diagnosis_coordinator.py',
        'tools/platform_host.py','tools/platform_store.py','schemas/platform_handoff.py','schemas/platform_diagnostics.py',
        'extensions/platform/manifest.py','extensions/tendon_family/diagnostic_evidence.py','extensions/tendon_family/diagnostic_math.py',
        'tools/model_transports/deepseek.py','examples/stage346_shared_diagnosis.py','examples/stage347_experiment.json']
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


class DiagnosticWorkflow:
    def __init__(self, directory, mode, *, pilot=False, minimal=False, experiment=None):
        if mode not in ('single_context','dual_context'):raise ValueError('UNKNOWN_ORGANIZATION_MODE')
        self.directory=Path(directory);self.mode=mode;self.pilot=pilot;self.minimal=minimal
        self.store=Store(directory);self.chain={};self.previous=None
        self.experiment=deepcopy(experiment or {})
        self.source=Path(self.experiment.get('source_store',SOURCE))
        self.execution=self.experiment.get('execution_id',EXECUTION)
        self.export_root=Path(self.experiment.get('evidence_directory',ROOT/'evidence/stage346_shared_diagnosis_20261002'))

    def prepare(self,runtime):
        if (self.directory/'freeze.json').exists():raise ValueError('NEW_RUN_DIRECTORY_REQUIRED')
        if not (self.source/'platform.sqlite').exists():
            manifest=ROOT/'evidence/stage341_repaired_live_execution_20261001/live_outcome.json'
            raise ValueError('SEALED_SOURCE_STORE_UNAVAILABLE; explicit portable outcome: '+str(manifest)+'; no substitution permitted')
        reader=ControlEvidence(Store(self.source));source=reader.resolve(self.execution)
        if self.experiment.get('source_manifest',source['manifest'])!=source['manifest']:raise ValueError('FROZEN_SOURCE_MANIFEST_MISMATCH')
        self.project=self.experiment.get('project_prefix','gvs-stage346')+'-'+uuid4().hex[:12]
        limits=dict(model_calls=3,tool_calls=3,backend_solves=0,worker_calls=0,wall_s=300.) if self.minimal else LIMITS
        self.store.create(dict(project_id=self.project,grant_id=self.project,budget=limits,
            authorization_source=self.experiment.get('authorization_source','User-authorized sequential Stage 3.46 native validation, pilot and two matched pairs; necessary context/evidence transmission to DeepSeek; no backend simulations/workers or push.')))
        self.hosts={}
        for role in (['shared'] if self.mode=='single_context' else ['design','diagnostic'])+['executor']:
            host=Host(self.directory,self.project+'-'+role);inp=deepcopy(source['configuration']);inp['run_id']=host.run_id
            bindings={'diagnosis.inspect_evidence':'1.0.0','diagnosis.saved_state_check':'1.0.0'} if role=='executor' else TOOLS
            inp['policy'].update(route=None,budget={**limits,'model_calls':0 if role=='executor' else limits['model_calls']},
                timeout_s=900. if role=='executor' else 30.,allowed_tools=[],tool_bindings=bindings)
            provider=read(Path(self.experiment.get('provider_freeze',ROOT/'evidence/stage346_shared_diagnosis_20261002/pilot/freeze.json')))['provider_configuration']
            inp['policy']['model']={**provider,'adapter_version':'4.0.0','max_turns':24,
                'tool_naming':tool_naming_policy(bindings,READABLE_TOOL_NAMING)}
            host.create(inp);self.hosts[role]=host
        self.binding=import_execution(reader,self.execution,self.store,self.hosts['executor'].run_id,source['manifest'])
        with self.store.transaction() as db:
            db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
        executor=self.hosts['executor'];executor.resume()
        receipt=executor.invoke(dict(request_id='inventory-summary',tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',
            arguments=dict(binding=self.binding,view='summary'),reason='Read preserved source summary',cache='new'))
        if receipt['execution_status']!='completed':raise ValueError('SOURCE_SUMMARY_FAILED: '+str(receipt['error']))
        self.summary=receipt['output'];self.inventory=evidence_inventory(reader,source)
        self.inventory_ref=save(self.store,self.inventory)
        b=self.store.artifact(self.binding)
        self.identities={k:b[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest','configuration')}
        self.freeze=dict(schema_version='1.0.0',project_id=self.project,mode=self.mode,pilot=self.pilot,minimal=self.minimal,
            hosts={k:h.run_id for k,h in self.hosts.items()},binding=self.binding,identities=self.identities,summary=self.summary,
            inventory=self.inventory,inventory_reference=self.inventory_ref,source_manifest=source['manifest'],
            implementation=implementation(),runtime=runtime,provider_configuration=self.store.session(self.host('design').run_id)['snapshot']['input']['policy']['model'],
            limits=limits,numerical_limits=NUMERICAL,scope=SCOPE,memory_policy=MEMORY,phase_budgets=PHASES,
            stage_instructions=INSTRUCTIONS,permissions=PERMISSIONS,capabilities=CAPABILITIES,experiment=self.experiment,
            recovery=recovery_status({},self.store.session(self.host('design').run_id)['snapshot']['input']['policy']['model']),
            host_provider_configurations={k:self.store.session(h.run_id)['snapshot']['input']['policy']['model'] for k,h in self.hosts.items()},
            tool_bindings=TOOLS,review_rubric=read(ROOT/'evidence/stage346_shared_diagnosis_20261002/review_rubric.json'),
            outcomes=['workflow completion','exact selector validation','prose review','check usefulness','usage','physical improvement not evaluated'])
        atomic_json(self.directory/'freeze.json',self.freeze)
        return self.freeze

    def host(self,role):return self.hosts['shared' if self.mode=='single_context' else role]

    def fixed(self,phase):
        fixed={'diagnosis.inspect_evidence':dict(binding=self.binding)}
        if phase=='request':
            fixed['diagnosis.request']=dict(subject='control',binding=self.binding,
                **{k:self.identities[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest')},
                permitted_tools=['diagnosis.inspect_evidence','diagnosis.check_request','diagnosis.submit','evidence.read'],
                budget=LIMITS,saved_state_check=SCOPE)
        if phase in ('initial','revision'):
            fixed['diagnosis.submit']=dict(request=self.chain['request'],previous_report=self.chain.get('initial_report') if phase=='revision' else None,
                check_results=[self.chain['feedback']] if phase=='revision' else [])
        if phase.startswith('response'):
            fixed['design.respond_diagnosis']=dict(report=self.chain['revised_report' if phase=='response_final' else 'initial_report'])
        if phase=='check':fixed['diagnosis.check_request']=dict(check_id='saved-state-check',diagnosis_request=self.chain['request'],model=SCOPE['model'],
            horizon_s=SCOPE['horizon_s'],integration=SCOPE['integration'],integration_step_s=SCOPE['integration_step_s'])
        return fixed

    def phase(self,phase,kind,key,**extra):
        role='design' if phase in ('request','response_initial','response_final') else 'diagnostic'
        host=self.host(role)
        if self.previous is not None and host.run_id!=self.previous.run_id:transfer_recovery(self.previous,host)
        state=self.store.session(host.run_id)['state']
        common=dict(binding=self.binding,identities=self.identities,summary=self.summary,
            summary_content=self.store.artifact(self.summary),inventory=self.inventory,inventory_reference=self.inventory_ref,
            protocol=dict(saved_state_check=SCOPE),capabilities=CAPABILITIES,diagnostic_tools=list(TOOLS),phase=phase,
            memory_identity=host.run_id,working_memory=state.get('workflow_memory',[]),memory_policy=MEMORY,
            phase_budget=PHASES[phase],phase_tools=PERMISSIONS[phase],native_fixed=self.fixed(phase),native_store_root=str(self.directory),
            evidence_turn_limit=2 if phase in ('request','initial','check') else 0)
        if self.minimal:common['phase_budget']=dict(limit=dict(model_calls=3,tool_calls=3,wall_s=300.))
        if 'request' in self.chain:common.update(request=self.chain['request'],request_content=self.store.artifact(self.chain['request']))
        if phase.startswith('response'):
            report=self.chain['revised_report' if phase=='response_final' else 'initial_report']
            common.update(report=report,report_content=self.store.artifact(report),final_response=phase=='response_final')
        instruction=INSTRUCTIONS[phase]
        if self.pilot and phase=='response_initial':instruction+=' This development pilot requires one genuine check and report revision to validate feedback capability. Select a justified check action; retain your own disposition and engineering conclusion.'
        configure_role(host,role,instruction,**{**common,**extra})
        before=self.store.session(host.run_id)['state'].get('handoffs',{}).get(kind)
        print('PHASE',self.directory.name,phase,flush=True)
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
            if self.minimal:
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
                    self.phase('revision','diagnosis_report','revised_report',previous_report=self.chain['initial_report'],
                        previous_report_content=self.store.artifact(self.chain['initial_report']),check_feedback=retained,max_checks=1)
                    self.phase('response_final','design_response','final_response',check_feedback=retained)
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
        outcome=dict(schema_version='1.0.0',status=status,stop_reason=reason,mode=self.mode,pilot=self.pilot,minimal=self.minimal,
            chain=self.chain,feedback_complete=all(k in self.chain for k in ('check','feedback','revised_report','final_response')),
            numerical_check_status=feedback['receipt']['execution_status'] if feedback else None,
            usage=self.store.remaining(),numerical_work=work,provider_usage=usage_rows,monetary_cost=None,elapsed_s=elapsed,
            protocol_corrections=max(self.store.session(h.run_id)['state'].get('protocol_corrections_used',0) for h in self.hosts.values()),
            recovery={k:recovery_status(self.store.session(h.run_id)['state'],self.store.session(h.run_id)['snapshot']['input']['policy']['model']) for k,h in self.hosts.items()},
            physical_improvement='not evaluated',source_preserved=ControlEvidence(Store(self.source)).resolve(self.execution)['manifest']==self.freeze['source_manifest'])
        atomic_json(self.directory/'outcome.json',outcome)
        for path in self.directory.glob('*.json'):atomic_json(destination/path.name,read(path))
        for name,value in [('events',events),('receipts',receipts),('raw_calls',raw),('resolved_calls',resolved)]:atomic_json(destination/(name+'.json'),value)
        for ref in refs.values():(artifacts/(ref['artifact_id']+'.json')).write_bytes(self.store.artifact(ref,raw=True))
        atomic_json(destination/'sha256_manifest.json',{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob('*.json')) if p.name!='sha256_manifest.json'})
        print('OUTCOME',status,'USAGE',outcome['usage']['used'],flush=True)

    def validate_frozen_configuration(self):
        for name,host in self.hosts.items():
            actual=self.store.session(host.run_id)['snapshot']['input']['policy']['model']
            if actual!=self.freeze['host_provider_configurations'][name]:raise ValueError('FROZEN_PROVIDER_CONFIGURATION_MISMATCH: '+name)
        for key,value in [('stage_instructions',INSTRUCTIONS),('permissions',PERMISSIONS),('phase_budgets',PHASES),('scope',SCOPE),('memory_policy',MEMORY),('capabilities',CAPABILITIES),('experiment',self.experiment)]:
            if value!=self.freeze[key]:raise ValueError('FROZEN_CONFIGURATION_MISMATCH: '+key)
