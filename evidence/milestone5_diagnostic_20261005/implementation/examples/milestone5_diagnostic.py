"""New linked diagnostic grant. Numerical and interpretation recovery reuse receipts."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_validation as previous
from tools.diagnostic_workflow import DiagnosticWorkflow, save
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import read, atomic_json, digest
from tools.runtime_identity import require_softagent_runtime
from tools.platform_registry import registry
from tools.platform_diagnosis_coordinator import configure_role, run_until_handoff
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution
from extensions.tendon_family.milestone5_diagnostic import DEFINITION

RUN=ROOT/'runs/milestone5_diagnostic_20261005/single_context'
EVIDENCE=ROOT/'evidence/milestone5_diagnostic_20261005'
LIMITS=dict(model_calls=8,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=1800.)
EXECUTIONS=['2413ff2a56de422dac47b7fd78717563','9865f1636266479c93817cad42a65353']
AUTHORIZATION=dict(source='User attachment f275d000-9975-4e2d-9a19-444a8e36850f, 2026-10-05',
    stage='NEW bounded diagnostic stage linked to completed prediction-validation; predecessor not reopened',
    destination='https://api.deepseek.com',model='deepseek-flash',
    covered_data=['robot/task/model/controller/candidate configurations','saved historical and prospective results and trajectories',
        'compact diagnostics/numerical comparisons/artifact references/implementation details','instructions/tool schemas/budgets/proposals/interpretation and necessary corrections'],
    credentials='Normal authentication only via Join-Path $HOME .codex/.env; excluded from evidence',
    limits=LIMITS,numerical_limits=dict(local_solves=6,prediction_evaluations=8),backend_stepping_replay=0,
    protocol_corrections=dict(max_total=4,max_consecutive=2),workers_subagents=0,local_commit=True,push=False)


class Workflow(DiagnosticWorkflow):
    limits=LIMITS
    numerical_limits=dict(local_solves=6,prediction_evaluations=8)
    tools={'design.respond_diagnosis':'3.0.0','evidence.read':'1.0.0'}


def sealed_state(store):
    with store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    return dict(usage=store.remaining(),states={i:digest(store.session(i)['state']) for i in ids})


def assert_previous(w):
    link=w.freeze['predecessor']
    assert sealed_state(Store(previous.RUN))==link['state']
    for p,sha in link['files'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p


def prepare():
    old=previous.restore();reader=ControlEvidence(Store(previous.predecessor.RUN));source=reader.resolve(previous.INCUMBENT)
    cfg=deepcopy(old.freeze['experiment']);cfg.update(source_store=str(previous.predecessor.RUN),execution_id=previous.INCUMBENT,
        source_manifest=source['manifest'],evidence_directory=str(EVIDENCE),project_prefix='gvs-milestone5-diagnostic',
        authorization_source=json.dumps(AUTHORIZATION),provider_freeze=str(previous.RUN/'freeze.json'))
    if (RUN/'freeze.json').exists():
        frozen=read(RUN/'freeze.json')
        if 'predecessor' in frozen:raise ValueError('PREPARATION_ALREADY_COMPLETED')
        w=Workflow(RUN,'single_context',experiment=frozen['experiment']);w.freeze=frozen;w.project=frozen['project_id']
        w.hosts={k:Host(RUN,v) for k,v in frozen['hosts'].items()}
        for attr,key in [('binding','binding'),('identities','identities'),('summary','summary'),('inventory','inventory'),('inventory_ref','inventory_reference')]:setattr(w,attr,frozen[key])
        atomic_json(RUN/'preparation_recovery.json',dict(error='Historical artifact-shaped selector contained nested identity; old recursive helper treated it as EvidenceRef.',
            recovery='Typed reference check; reuse existing stage, source summary receipt and grant; no reset or repeated calculation.',provider_attempts=0,numerical_attempts=0))
    else:
        w=Workflow(RUN,'single_context',experiment=cfg);w.prepare(require_softagent_runtime())
    refs={}
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                if value['artifact_id'] in seen:return
                seen.add(value['artifact_id']);body=old.store.artifact(value,raw=True)
                with w.store.transaction() as db:assert plain(w.store.put(db,body,value['media_type']))==value
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    for name in ('revised_report','prediction_numerical','forecast_seal','final_response','prediction_assessment'):
        copy(old.chain[name]);refs[name]=old.chain[name]
    w.chain={};w.freeze.update(authorization=AUTHORIZATION,predecessor=dict(store=str(previous.RUN),state=sealed_state(old.store),
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in previous.EVIDENCE.rglob('*') if p.is_file()}),
        predecessor_refs=refs,incumbent=old.incumbent,original_baseline=old.retained_baseline,
        primary_reference=old.incumbent['candidate'],latest_tested=old.latest_tested,
        selected_deliverable=old.incumbent['candidate'],development_executions=EXECUTIONS,
        original_reference=next(r['facts']['candidate'] for r in old.historical_results if r['facts']['execution_id']==previous.DEVELOPMENT[0]))
    bindings=[import_execution(ControlEvidence(old.store),e,w.store,w.hosts['executor'].run_id) for e in EXECUTIONS]
    protocol=read(previous.RUN/'prediction_protocol.json');protocol_ref=save(w.store,protocol)
    w.freeze['diagnostic_protocol']=save(w.store,dict(bindings=bindings,incumbent_binding=w.binding,numerical=refs['prediction_numerical'],preview_protocol=protocol_ref))
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',w.freeze);atomic_json(RUN/'chain.json',w.chain)
    return w


def restore():
    frozen=read(RUN/'freeze.json');w=Workflow(RUN,'single_context',experiment=frozen['experiment']);w.freeze=frozen
    w.project=frozen['project_id'];w.hosts={k:Host(RUN,v) for k,v in frozen['hosts'].items()};w.binding=frozen['binding'];w.identities=frozen['identities']
    w.summary=frozen['summary'];w.inventory=frozen['inventory'];w.inventory_ref=frozen['inventory_reference'];w.chain=read(RUN/'chain.json')
    return w


def calculate(w,operation):
    receipt_path=RUN/(operation+'_receipt.json')
    if receipt_path.exists():
        receipt=read(receipt_path)
        if receipt['execution_status']!='completed':raise ValueError('FAILED_NUMERICAL_ATTEMPT_REQUIRES_REVIEW')
        w.chain[operation]=receipt['output'];return
    reg=registry();reg.add(DEFINITION)
    inp=deepcopy(w.store.session(w.hosts['executor'].run_id)['snapshot']['input']);run_id=w.project+'-'+operation
    inp['run_id']=run_id;inp['policy'].update(tool_bindings={DEFINITION.extension_id:DEFINITION.version},allowed_tools=[],timeout_s=600.,
        operation_allowances={DEFINITION.extension_id:dict(timeout_s=600.,reserve_s=600.)})
    host=Host(RUN,run_id,reg=reg);host.create(inp);host.resume();w.hosts[operation]=host
    w.freeze['hosts'][operation]=run_id;atomic_json(RUN/'freeze.json',w.freeze)
    protocol={**w.store.artifact(w.freeze['diagnostic_protocol']), 'operation':operation}
    receipt=host.invoke(dict(request_id='saved-'+operation,tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
        arguments=dict(protocol=save(w.store,protocol)),reason='Authorized saved-evidence diagnosis; zero backend steps, zero controller weight experiments.',cache='new'))
    atomic_json(receipt_path,receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    w.chain[operation]=receipt['output'];atomic_json(RUN/(operation+'.json'),w.store.artifact(receipt['output'])['detail']);atomic_json(RUN/'chain.json',w.chain)


def compact(w):
    rows=w.store.artifact(w.chain['intervals'])['detail']['result'];preview=w.store.artifact(w.chain['preview'])['detail']['result']
    intervals=[]
    for r in rows:
        item={k:v for k,v in r.items() if k not in ('files','integration','state')}
        item['integration']=[{k:v for k,v in row.items() if k!='trajectory'} for row in r['integration']]
        intervals.append(item)
    production=[{k:v for k,v in r.items() if k!='state'} for r in preview['production']]
    packet=dict(evidence_type='current retrospective diagnostic calculation; .075/.15 are development data',
        intervals=intervals,preview={**preview,'production':production},
        predecessor_results=dict(local_direction_correct=4,local_numerical_pass=0,full_task_resolved=0,full_task_unresolved=4,ordering='abstained',accuracy_among_resolved=None,immutable=True),
        original_baseline=w.freeze['original_baseline']['candidate'],primary_reference=w.freeze['primary_reference'],
        passing_pre_adaptation_reference=w.freeze['original_reference'],latest_tested=w.freeze['latest_tested'],selected_deliverable=w.freeze['selected_deliverable'],
        incumbent=w.freeze['incumbent'],authorization=AUTHORIZATION,remaining=w.store.remaining()['remaining'],
        prior_costs=dict(preview_s=73.31299999984913,two_full_evaluations_s=605.936999999918),
        choices=dict(A='Improve local prediction integration if numerical error materially contributes.',B='Specific defect repair only if identified; otherwise targeted investigation.',
            C='Candidate-specific generated history preview only if supported; cannot use unseen future backend state.',D='Retain local diagnosis only and defer run-ahead screening.'),
        next_validation='Prepare only; no execution. Independent evidence required; .075/.15 cannot be fresh validation.',milestone4='closed',milestone5='open')
    if (RUN/'semantic_correction.json').exists():packet['semantic_correction']=read(RUN/'semantic_correction.json')
    ref=save(w.store,packet);atomic_json(RUN/'diagnostic_handoff.json',packet);return packet,ref


def interpret(w):
    if 'final_response' in w.chain:return
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    packet,ref=compact(w);host=w.host('design');report=w.freeze['predecessor_refs']['revised_report']
    if '--correct' in sys.argv:
        if w.freeze.get('semantic_corrections',0):raise ValueError('CORRECTION_ALREADY_STARTED_USE_SAVED_RECOVERY')
        rejected=[]
        for event in w.store.events(host.run_id):
            if event['kind']=='model_decision':rejected.extend(event['outputs'])
        issues=[
            'The primary D decision is allowed, but integration IS a measured contributor: coarse-to-.001 speeds increase .00165639008211407 and .00109026085753176 m/s, reducing scalar endpoint errors about 26.16% and 20.99%. Fine differences .00020740822618719/.000129349605445708 are .001-minus-.002, NOT fine-minus-coarse. Do not call numerical resolution immaterial by comparing position offset to a speed error.',
            'Residuals for refined roots reach 4.486943585776948e-11, not all <=2.4e-14. Saved production defects 5.0952387057809356e-8 / 1.9131447419756277e-6 explain tiny coarse reproduction differences; these do not explain the millimetres-per-second discrepancy.',
            'Initial position error norms .0026891778822236262/.0026889844817533045; initial velocity vector error norms .00037922371316335865/.00036431540818624943 despite tiny speed offsets. Endpoint vector errors .007492333503420177/.006934123087733086. At .15 refinement improves scalar speed but worsens vector error .006934196218480314 -> .007222011082626113. No uniquely proven projection-level physical cause.',
            'Separate incumbent original saved observations from previously sealed FOUR prospective intervals; current six calculations retrospective. No new prospective accuracy.',
            'Settled seed position check is .005 m; physical task holding position acceptance remains .01 m, speed .02 m/s, numerical speed tolerance 1e-4. .075 prediction .016953566461155 <.02 while observed .023285947509969908 >.02; .001 result .01860995697336772 still false-safe.',
            'Choose exactly ONE A/B/C/D primary action yourself after acknowledging material scalar resolution contribution AND remaining vector error. Retain local diagnostic role if evidence insufficient; no screening promise. Future protocol must require genuinely NEW independent backend evidence under a FUTURE separate grant; zero backend in this diagnostic stage does not mean a future fresh observation can be obtained for zero backend cost. Specify resolved coverage, conditional accuracy, false-safe counts, cost/discrimination, exit rules and a bounded budget. Operational next_research stays stop/zero.',
            'Prior final handoff used @4, which requires an unexecuted batch plan; this stage makes no batch. Migrate to existing @3 feedback-bound finish decision. Preserve all failed receipts/counters; no numerical replay.'
        ]
        correction=dict(rejected_decisions=rejected,issues=issues,evidence_type='engineering semantic review; no fabricated model response')
        atomic_json(RUN/'semantic_correction.json',correction);packet['semantic_correction']=correction
        ref=save(w.store,packet)
        inp=deepcopy(w.store.session(host.run_id)['snapshot']['input']);inp['run_id']=w.project+'-feedback-bound-final'
        inp['policy']['tool_bindings']=Workflow.tools
        from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
        inp['policy']['model']['tool_naming']=tool_naming_policy(Workflow.tools,READABLE_TOOL_NAMING)
        new=Host(RUN,inp['run_id']);new.create(inp)
        from tools.platform_diagnosis_coordinator import transfer_recovery
        transfer_recovery(host,new);w.hosts['retired_shared']=host;w.hosts['shared']=new;host=new
        w.freeze.update(hosts={k:h.run_id for k,h in w.hosts.items()},semantic_corrections=1)
        atomic_json(RUN/'freeze.json',w.freeze)
    from tools.diagnostic_facts import handover
    with w.store.transaction() as db:
        state=w.store.session(host.run_id,db)['state'];state.setdefault('fact_scope',dict(project=w.project,binding=w.binding));state.setdefault('fact_catalog',{})
        w.store.update_state(db,host.run_id,state)
    handover(host,ref,packet,origin=dict(kind='current_retrospective_diagnostic',references=[w.chain['intervals'],w.chain['preview']]),kind='diagnostic_handoff')
    instruction='''Interpret current compact diagnostic evidence yourself. Choose exactly ONE primary A/B/C/D action and narrowest supported role; say it explicitly in reasoning. Quantify coarse production reproduction, initial/vector/change errors, refinement contributions, fine-step differences and unresolved causes. Do not call a speed-norm match a vector match or claim convergence from a single finer value. Explain the .30 settled-seed thresholds, feasibility, weight-independent checks and iteration zero acceptance. Production history,state,input,solver paths also differ; historical warm plans absent. No broad causal claim, promotion or new experiment. Retain exact incumbent batch-ebbeadbdaca10732-0 execution 91c3ba1b01d6499fb26df8f95409401b; selected_candidate=baseline, candidate_disposition=retain_baseline. disposition=defer,recommendation_id=null. next_action=finish,next_research.route=stop and zero proposed_budget: this grant stops. In reasoning propose ONE precise future falsification/validation protocol, clearly unexecuted, with independent data, quantity/scope, direction/error/order/abstention/threshold-crossing reporting, cost and bounded proposed future budget. This future budget is prose only and separate from zero operational next_research budget. Distinguish sealed prior prospective results from development and retrospective calculations. M4 closed,M5 open. Preserve 1e-4 m/s numerical reporting tolerance and real-time acceptance. About 650 words.'''
    configure_role(host,'design',instruction,phase='response_final',memory_identity=host.run_id,native_store_root=str(RUN),
        binding=w.binding,identities=w.identities,report=report,report_content=w.store.artifact(report),final_response=True,
        phase_budget=dict(limit=LIMITS),phase_tools=['design.respond_diagnosis'],delivery_tool='design.respond_diagnosis',
        native_fixed={'design.respond_diagnosis':dict(report=report)},decision_packet=packet,decision_packet_reference=ref,
        improvement_feedback_content=dict(baseline_facts=w.freeze['incumbent'],execution=None),
        check_feedback=[dict(reference=w.chain['intervals'])],require_research_route=True,require_research_budget=True)
    payload=payload_for(host,EvidenceDrivenAdapter());atomic_json(RUN/'final_serialized_handoff.json',payload)
    assert json.dumps(AUTHORIZATION,sort_keys=True) in json.dumps(json.loads(payload['messages'][1]['content']),sort_keys=True)
    atomic_json(RUN/'provider_attempt_guard.json',dict(authorization=AUTHORIZATION,previous_usage=w.store.remaining()['used']))
    w.chain['final_response']=run_until_handoff(host,'design_response');atomic_json(RUN/'final_response.json',w.store.artifact(w.chain['final_response']));atomic_json(RUN/'chain.json',w.chain)


def refine_final(w):
    """One semantic clarification, same successful context and unchanged grant."""
    count=w.freeze.get('semantic_corrections',0)
    if count not in (1,2):raise ValueError('SEMANTIC_REVIEW_ALLOWANCE_EXHAUSTED')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    host=w.host('design');packet,ref=compact(w);prior=w.chain['final_response']
    atomic_json(RUN/('final_response_before_clarification'+str(count+1)+'.json'),w.store.artifact(prior))
    issues=[
        'Keep primary D and local diagnostic use; give its specific justification: scalar refinement helps materially but residual speed error remains .004676/.004103 m/s, >40 times 1e-4, and vector error is not consistently improved. A does NOT require numerical integration to be the sole cause; defer adoption because these local results do not establish numerical accuracy or useful screening.',
        'The .15 velocity error .006934196218480314 -> .007222011082626113 is coarse .01 -> fine .001. The .002 error is .007142183950770937. Fix that comparison label. Narrow role includes retrospective diagnosis of the development executions bound to the incumbent reference, not falsely calling the two interval states incumbent states.',
        'Use this exact FUTURE protocol for D without executing it: production predictor/controller unchanged (.01 implicit Euler, @7, incumbent .05/.05), zero screening authority. Two new independent held-out initial-state histories with configuration/initial states sealed before backend, same robot/task/acceptance/controller recipe; exact histories must be fixed in the future grant, not selected after results. Seal production first-period predictions at .20 and .30 s, compare .21/.31 backend samples under actual applied tension (four intervals). Current .075/.15 and any current calculations development only. No new weight experiments.',
        'For every interval report norm and vector projection/change/endpoint errors, signed predicted-minus-observed speed error, speed direction with +/-1e-4 rule, endpoint scalar and vector passes <=1e-4 m/s, position discrepancy separately; false-safe if predicted <=.02 and observed >.02; report distance to threshold. Invalid alignment/residual >1e-5/nonfinite -> abstention, preserve failed attempts. Report resolved coverage, accuracy among resolved (undefined when zero), false-safe counts and total/conditional rates. Full-task ordering/screening always abstain under D; no candidate ranking. Useful local information and capture/reconstruction overhead versus full evaluation cost reported separately.',
        'Proposed FUTURE ceiling (separate from operational zero budget): 4 provider attempts,20 workflow calls,2 backend attempts,0 extra controller solves,0 reduced rollouts,2500 charged seconds,0 workers,2 total corrections max2 consecutive. Production predictions already embedded, no extra solves. Stop on failed validity, any false-safe, both runs completed, or any ceiling reached. Endpoint numerical failure retains diagnosis only and prohibits screening; do not close M5. No automatic launch.',
        'Explicitly preserve historical four correct local directions/zero endpoint passes and full-task 0 resolved/4 unresolved plus ordering abstention; this current retrospective diagnosis cannot change prior sealed results or establish new prospective reliability.'
    ]
    if count==2:
        issues=[
            'Correct exactly the false-safe scope: ONLY the .075 development interval crosses .02 (predicted .016953566461155, observed .023285947509969908). The .15 interval predicts .005830076194148043 and observes .011023132121572656; BOTH below .02, so .15 is NOT false-safe. This is 1 of 2 development intervals, not prospective validation. The .001 .075 prediction remains false-safe. Remove plural .075/.15 false-safe claim.',
            'The FOUR direction-correct/zero endpoint-pass intervals were previously SEALED PROSPECTIVELY in the completed predecessor. They now serve as development data for this new diagnostic stage. Preserve the six older historical development intervals separately. Keep all accurate current numerical conclusions, primary D, exact future protocol and incumbent/finish/stop/zero operational budget. No new study or inference.'
        ]
    review=dict(rejected_response=prior,issues=issues,classification='semantic clarification of labels and exact proposed future protocol; no numerical work')
    atomic_json(RUN/('final_clarification'+str(count+1)+'.json'),review);packet['final_clarification']=review
    role=deepcopy(w.store.session(host.run_id)['state']['role_context']);role.pop('role',None);instructions=role.pop('instructions')
    role.update(decision_packet=packet,decision_packet_reference=save(w.store,packet))
    configure_role(host,'design',instructions+' Correct final_clarification issues while preserving stop and retained candidate. About 600 words.',**role)
    payload=payload_for(host,EvidenceDrivenAdapter());atomic_json(RUN/('final_clarification'+str(count+1)+'_serialized_handoff.json'),payload)
    w.freeze['semantic_corrections']=count+1;atomic_json(RUN/'freeze.json',w.freeze)
    w.chain['final_response']=run_until_handoff(host,'design_response');atomic_json(RUN/'final_response.json',w.store.artifact(w.chain['final_response']));atomic_json(RUN/'chain.json',w.chain)


def export(w,status,reason):
    assert_previous(w)
    DiagnosticWorkflow.export(w,status,reason,0.)
    used=w.store.remaining()['used'];old=read(previous.EVIDENCE/'delivery.json')['accounting']['cumulative']
    with w.store.connect(True) as db:
        calls=list(db.execute('SELECT charged FROM calls WHERE charged IS NOT NULL'));work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    sums={k:sum(json.loads(r[0])[k] for r in calls) for k in LIMITS};assert sums==used
    corrections=max(w.store.session(h.run_id)['state'].get('protocol_corrections_used',0) for h in w.hosts.values())
    accounting=dict(old=old,new=used,cumulative={k:old[k]+used[k] for k in old},stage_limits=LIMITS,receipt_charge_sum=sums,numerical_work=work,
        cumulative_numerical_work=dict(local_solves=9+work['used']['local_solves'],prediction_evaluations=9+work['used']['prediction_evaluations'],embedded_controller_updates=210),
        corrections=dict(old=6,new=corrections,cumulative=6+corrections),semantic_corrections=dict(old=5,new=w.freeze.get('semantic_corrections',0),cumulative=5+w.freeze.get('semantic_corrections',0)),occupied=w.store.remaining()['occupied'])
    atomic_json(EVIDENCE/'accounting.json',accounting)
    atomic_json(EVIDENCE/'delivery.json',dict(status=status,reason=reason,predecessor_preserved=True,milestone4_closed=True,milestone5_complete=False,
        selected_deliverable=w.freeze['selected_deliverable'],primary_reference=w.freeze['primary_reference'],latest_tested=w.freeze['latest_tested'],
        original_baseline=w.freeze['original_baseline']['candidate'],passing_pre_adaptation_reference=w.freeze['original_reference'],
        accounting=accounting,authorization=AUTHORIZATION,final_response=w.chain.get('final_response'),next_validation_executed=False,
        backend_stepping_replay=0,no_workers=True,no_subagents=True,pushed=False))


def deliver(w):
    """Verify saved results and package the single D decision, without execution."""
    import numpy as np
    final=w.store.artifact(w.chain['final_response']);rows=w.store.artifact(w.chain['intervals'])['detail']['result']
    preview=w.store.artifact(w.chain['preview'])['detail']['result']
    assert final['next_action']=='finish' and final['next_research']['route']=='stop'
    assert all(v==0 for v in final['next_research']['proposed_budget'].values())
    assert final['selected_candidate']==w.freeze['incumbent']['candidate'] and final['candidate_disposition']=='retain_baseline'
    assert 'Primary action: D' in final['reasoning'] or 'Primary action D' in final['reasoning']
    for row in rows:
        assert row['execution_id'] in EXECUTIONS and abs(row['duration_s']-.01)<1e-12
        assert row['coarse_reproduction']['velocity_difference_norm_m_s']<1e-7
        assert row['coarse_reproduction']['position_difference_m']<1e-9
        for d in row['decomposition'].values():assert d['identity_residual']<1e-15
        assert [r['step_s'] for r in row['integration']]==[.01,.002,.001]
        for calc in row['integration']:
            assert calc['max_scaled_residual']<1e-10 and calc['status']=='root_residual_verified'
            assert abs(calc['endpoint']['time_s']-.01)<1e-12
        assert abs(row['fine_difference']['speed_m_s'])>1e-4
    cold=[r for r in preview['rows'] if r['checkpoint_s']==.3]
    assert len(cold)==3 and len({r['maximum_selected_plan_speed_m_s'] for r in cold})==1
    for r in cold:
        assert r['selected_iteration']==0 and r['seed_settled'] and r['feasibility']['feasible']
        assert r['maximum_selected_plan_error_m']<=r['position_threshold_m']==.005
        assert r['maximum_selected_plan_speed_m_s']<=r['speed_threshold_m_s']==.02
        assert r['previous_input_n']==r['first_command_n'] and not r['optimized_before_acceptance']
    assert not any(r['historical_warm_plan_available'] for r in preview['production'])
    assert_previous(w)
    assert w.store.remaining()['occupied']=={}
    export(w,'completed','Research model chose D: retain local diagnostic use and defer run-ahead screening; finish/stop. Future protocol is unexecuted.')
    protocol=dict(schema_version='1.0.0',classification='proposed future validation protocol, sealed but NOT executed or authorized by this stage',
        selected_primary_action='D',intended_role='Local diagnosis only; no run-ahead screening, candidate ordering or automatic rejection',
        implementation_change='None. Retain production first-period implicit Euler @0.01 s and controller.gvs_nmpc@7.0.0; no production shortcut/weight/projection changes.',
        selected_deliverable=w.freeze['selected_deliverable'],development_data=dict(executions=EXECUTIONS,current_retrospective_rollouts=6,
            predecessor_prospective_intervals=4,independent_prospective_validation=False),
        required_new_evidence='Two genuinely new held-out initial-state histories/executions. Their exact existing-family initial configurations must be registered and frozen in a separate future grant before backend advancement. No new weight experiments. Deterministic identical repeats are not independent evidence.',
        fixed_conditions=['incumbent robot 0.16/0.11 m,section scale 0.95,compliant material','incumbent holding/terminal .05/.05',
            'same reach task, world frame,0.01 s control period','physical holding .01 m/.02 m/s and real-time acceptance unchanged','same solver and provider settings'],
        checkpoints_s=[.2,.3],endpoint_s=[.21,.31],interval_duration_s=.01,prediction_source='Actual-input production accepted first-period prediction sealed before backend advancement; no extra optimization or rollout',
        quantities=['world position and velocity vectors','speed norms','initial projection error','predicted and observed changes','predicted-minus-observed endpoint errors','distance to physical thresholds'],
        direction_rule='Speed change <-1e-4 decreasing, >1e-4 increasing, otherwise approximately unchanged; compare predicted relative to projected initial and observed relative to backend initial.',
        numerical_rules=dict(speed_error_tolerance_m_s=1e-4,velocity_vector_error_tolerance_m_s=1e-4,position='Report vectors and norms separately; no new accuracy claim from holding acceptance'),
        abstention='Unaligned state/input/time, nonfinite prediction, unavailable endpoint or scaled residual >1e-5: unresolved, never silently exclude; valid near-threshold estimates retain signed error and false-safe scoring.',
        ordering_rule='Not supported under D; all full-task candidate directions, ordering and screening remain abstentions. No unseen future backend state/warm plan used for screening.',
        threshold_crossing=dict(speed_limit_m_s=.02,holding_position_limit_m=.01,scope='Holding-entry .30-.31 interval',
            false_safe='predicted <= limit and observed > limit',false_unsafe='predicted > limit and observed <= limit',report='counts, signed margins and errors; do not weaken 1e-4 tolerance'),
        reporting=dict(resolved_prediction_coverage='resolved/planned; invalids count in denominator',accuracy_among_resolved='correct/resolved, undefined if none',
            predicted_safe_observed_violating='Count and rates among planned and resolved predictions',useful_discrimination='Local diagnostic information and threshold classification per charged second; full-task discrimination remains unsupported'),
        cost_comparison=dict(prior_preview_s=73.31299999984913,prior_two_full_evaluations_s=605.936999999918,
            measure='Separate full-evaluation costs, incremental sealing/reconstruction/interpretation overhead, embedded control work. Cheaper alone does not establish decision value.'),
        proposed_future_ceiling=dict(model_calls=4,tool_calls=20,backend_solves=2,local_solves=0,prediction_evaluations=0,wall_s=2500.,worker_calls=0,corrections_total=2,corrections_consecutive=2),
        exit_conditions=['Invalid alignment or numerical validity','Any false-safe holding threshold crossing','Both fresh executions and four interval scores complete','Any ceiling reached'],
        acceptance='Numerical misses preserve diagnosis-only use and prohibit screening; correct local directions alone do not pass endpoint accuracy. No automatic candidate promotion or Milestone5 closure.',
        status='unexecuted',backend_authorization_in_current_stage=0)
    atomic_json(EVIDENCE/'next_validation_protocol.json',protocol)
    summary=[]
    for r in rows:
        coarse,middle,fine=r['integration'];error=r['decomposition']['speed_m_s']['endpoint_error']
        contribution=fine['endpoint']['speed_m_s']-coarse['endpoint']['speed_m_s']
        summary.append(dict(execution_id=r['execution_id'],candidate_id=r['candidate_id'],configuration=r['configuration'],checkpoint_s=.3,interval_s=[.3,.31],
            evidence_type='current retrospective diagnostic calculation',initial_speed_offset_m_s=r['decomposition']['speed_m_s']['initial_projection_error'],
            initial_velocity_error_norm_m_s=r['decomposition']['velocity_m_s']['initial_error_norm'],initial_position_error_norm_m=r['decomposition']['position_m']['initial_error_norm'],
            scalar_change_error_m_s=r['decomposition']['speed_m_s']['change_error'],saved_endpoint_speed_error_m_s=error,
            coarse_to_fine_speed_change_m_s=contribution,scalar_error_reduction_fraction=1-abs(fine['endpoint_speed_error_m_s'])/abs(coarse['endpoint_speed_error_m_s']),
            fine_endpoint_speed_error_m_s=fine['endpoint_speed_error_m_s'],fine_velocity_error_norm_m_s=fine['endpoint_velocity_error_norm_m_s'],fine_difference=r['fine_difference'],
            supported_inference='Integration resolution contributes materially to scalar speed error, but residual discrepancy and fine-step differences remain; vector improvement inconsistent.',
            uncertainty='No convergence at reporting tolerance or uniquely identified physical defect; projection is not full backend state.',
            supported_use='Local diagnosis only',proposed_next_test='next_validation_protocol.json'))
    handoff=dict(selected_primary_action='D',operational_decision='finish/stop',retained_candidate=w.freeze['incumbent']['candidate'],
        original_baseline=w.freeze['original_baseline']['candidate'],passing_pre_adaptation_reference=w.freeze['original_reference'],latest_tested=w.freeze['latest_tested'],
        evidence_classes=dict(historical_development='Known configurations,actual observations,cold preview plans',previously_sealed_prospective='Predecessor 4 local intervals and 4 unresolved full-task forecasts; immutable',
            current_retrospective='Two interval decompositions,six reduced rollouts,preview extraction; no new prospective evidence'),
        numerical_records=summary,preview_reference='single_context/preview.json',initialization_policy='Cold repeated previous input for preview; actual projected state/applied tension for resolution comparison',
        comparison_reference='Exact source manifests, saved controller observations, serial q/qdot and XML; no stepping',
        supported_model_role='local diagnostic evidence only',next_validation='next_validation_protocol.json',research_model_final=w.chain['final_response'])
    atomic_json(EVIDENCE/'research_handoff.json',handoff)
    verification=dict(passed=True,checks=['exact manifest/state/input/time alignment','vector and scalar identities separately',
        'coarse reproduction explicitly quantified','all six root residuals checked; no false convergence claim','same dynamics/integration family/input per interval',
        'cold seed thresholds,independent feasibility and iteration zero verified','production warm-plan availability inspected once; no replay',
        'final exact incumbent binding,stop/zero operational budget','predecessor entire evidence directory hashes/session states/usage unchanged',
        'receipt sums and sublimit charges reconciled; no occupied resources'],unit_tests=3,
        no_production_change=True,backend_steps=0,backend_attempts=0,extra_controller_solves=0,reduced_rollouts=6,
        provider_configuration='Only tool bindings/naming changed for diagnostic handoff; endpoint/model/reasoning/token/context/TLS/transport preserved',
        engineering_recoveries=['Reuse partial preparation receipt after old reference helper misclassified nested selector',
            'Populate existing fact catalog before serialization; no provider attempts for serializer failures',
            'Migrate @4 future-batch-plan-only final tool to existing @3 feedback-bound final tool; preserve old failed calls and recovery counters',
            'Three semantic reviews: numerical/provenance corrections, exact future protocol/labels, and false-safe scope; originals preserved; no numerical replay'],
        unresolved=['Endpoint speed errors exceed tolerance','Fine results not converged at tolerance','No unique physical defect or screening value','Historical warm vectors unavailable','Real-time unmet'])
    atomic_json(EVIDENCE/'verification.json',verification)
    review=dict(status='accept D/local-diagnosis role, exact incumbent retention and operational finish/stop; scope-qualified reasoning',
        accepted_response=w.chain['final_response'],additional_provider_request=False,
        limitations=[
            'Material integration contribution supports further numerical investigation; it does not make A an unfounded experiment. D is chosen because these results do not establish endpoint accuracy, stable vector improvement or decision value.',
            'Missing historical warm plans prevent replay of the original warm-start run. They do not prove candidate-specific GENERATED run-ahead history is impossible; C remains unvalidated and is deferred, not ruled out.',
            'The varied preview factor was HOLDING weight .05/.075/.15; terminal weight remained .05. The final prose terminal_weight label is inaccurate; exact artifact fields and this handoff define the comparison.',
            'The precise host-frozen next_validation_protocol.json elaborates the earlier model proposal/clarification; the final model response shortened it. It is unexecuted and requires separately frozen independent histories and authorization.'
        ],scientific_basis='Scalar error still .004676/.004103 m/s; fine differences exceed 1e-4, vector error worsens for .15, and the old cold preview abstained. No unique physical cause or screening reliability.')
    atomic_json(EVIDENCE/'final_semantic_review.json',review)
    delivery=read(EVIDENCE/'delivery.json');delivery.update(selected_primary_action='D',accepted_model_role=handoff['supported_model_role'],
        accepted_model_next_action='finish/stop',next_validation='next_validation_protocol.json',research_handoff='research_handoff.json',
        numerical_summary=summary,verification='verification.json',semantic_review='final_semantic_review.json',
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    atomic_json(EVIDENCE/'delivery.json',delivery)
    for path in ('examples/milestone5_diagnostic.py','extensions/tendon_family/milestone5_diagnostic.py','tests/test_milestone5_diagnostic.py'):
        target=EVIDENCE/'implementation'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    atomic_json(EVIDENCE/'next_validation_seal.json',dict(protocol_sha256=hashlib.sha256((EVIDENCE/'next_validation_protocol.json').read_bytes()).hexdigest(),
        status='proposed/unexecuted',new_authorization_required=True))
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})


def main():
    ready=(RUN/'freeze.json').exists() and 'predecessor' in read(RUN/'freeze.json')
    w=restore() if ready else prepare();assert_previous(w)
    try:
        if '--deliver' in sys.argv:
            deliver(w);return
        elif '--refine-final' in sys.argv:
            refine_final(w)
        elif '--prepare' not in sys.argv:
            calculate(w,'intervals');calculate(w,'preview')
            if '--calculate' not in sys.argv:interpret(w)
        export(w,'completed' if 'final_response' in w.chain else 'diagnostics_prepared','Saved-evidence diagnostic stage; no future protocol executed.')
    except Exception as exc:
        atomic_json(RUN/'stage_failure.json',dict(type=type(exc).__name__,message=str(exc)));export(w,'incomplete',str(exc));raise


if __name__=='__main__':main()
