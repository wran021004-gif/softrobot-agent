"""Linked M5 recovery/diagnosis stage; no future forecasts or backend execution."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_preparation as preparation
from examples import milestone5_diagnostic as diagnostic
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.state_io import read,atomic_json,digest
from tools.runtime_identity import require_softagent_runtime
from tools.diagnostic_workflow import save
from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
from tools.platform_models import payload_for,tool_naming_policy,READABLE_TOOL_NAMING
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.milestone5_recovery import DEFINITION

RUN=ROOT/'runs/milestone5_recovery_20261005'
EVIDENCE=ROOT/'evidence/milestone5_recovery_20261005'
LIMITS=dict(model_calls=8,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=2400.)
NUMERICAL=dict(local_solves=4,prediction_evaluations=16,preview_attempts=0)
AUTHORIZATION=dict(source='User attachment 29068dbf-8b23-4786-87c9-3eab51752771, explicit direct transmission authorization, 2026-10-05',
    destination='https://api.deepseek.com',model='deepseek-flash',data='Compact project configurations, saved results, aligned extracts, bounded diagnostic evidence, schemas and interpretation instructions',
    credential_policy='Normal authentication from Join-Path $HOME .codex/.env; never printed or included in evidence/messages',
    limits=LIMITS,numerical_limits=NUMERICAL,backend_steps=0,complete_previews=0,workers=0,subagents=0,local_commit=True,push=False)


def reg():
    r=registry();r.add(DEFINITION);return r


def host(name):
    names=read(RUN/'session_revision.json') if (RUN/'session_revision.json').exists() else {}
    return Host(RUN,names.get(name,'m5recovery-'+name),reg=reg())


def repair_snapshots():
    """Preserve failed receipts and refreeze only this corrected diagnostic implementation."""
    from tools.platform_diagnosis_coordinator import transfer_recovery
    old={name:host(name) for name in ('research','align','compare')};names={name:h.run_id+'-shape-index-repair' for name,h in old.items()}
    for name,h in old.items():
        cfg=deepcopy(h.store.session(h.run_id)['snapshot']['input']);cfg['run_id']=names[name]
        new=Host(RUN,names[name],reg=reg());new.create(cfg);transfer_recovery(h,new)
    atomic_json(RUN/'session_revision.json',names)
    atomic_json(RUN/'alignment_repair.json',dict(failed_receipt='align_receipt.json',reason='Shape comparison initially included fixed_base; saved trajectory contains only compiled_physics.body_ids. Assertion rejected mismatched lengths before any propagation.',
        correction='Use exact compiled body_ids and verify full-state kinematic reconstruction against all saved positions. Preserve failed call and old sessions; fresh linked snapshots within same grant.',new_numerical_attempts_in_failure=0))
    (RUN/'align_receipt.json').rename(RUN/'align_failed_receipt.json')


def predecessor_snapshot():
    store=Store(preparation.RUN)
    with store.connect(True) as db:
        sessions=[dict(row) for row in db.execute('SELECT * FROM sessions ORDER BY run_id')]
        calls=[dict(row) for row in db.execute('SELECT * FROM calls ORDER BY run_id,request_id')]
    return dict(usage=store.remaining(),sessions=sessions,calls=calls,
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in (preparation.EVIDENCE,preparation.RUN) for p in folder.rglob('*') if p.is_file() and p.suffix=='.json'})


def check_previous():assert predecessor_snapshot()==read(RUN/'freeze.json')['predecessor'],'COMPLETED_PREPARATION_CHANGED'


def prepare():
    require_softagent_runtime()
    if (RUN/'freeze.json').exists():check_previous();return
    store=Store(RUN);store.create(dict(project_id='m5-recovery-20261005',grant_id='m5-recovery-20261005',budget=LIMITS,authorization_source=json.dumps(AUTHORIZATION)))
    old=Store(preparation.RUN);inp=deepcopy(old.session(preparation.host('research').run_id)['snapshot']['input'])
    bindings={DEFINITION.extension_id:DEFINITION.version,RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    provider=deepcopy(read(preparation.RUN/'freeze.json')['provider_configuration']);provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    inp['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=bindings,model=provider,timeout_s=600.,operation_allowances={DEFINITION.extension_id:dict(timeout_s=600.,reserve_s=600.)})
    for name in ('research','align','compare'):
        h=host(name);cfg=deepcopy(inp);cfg['run_id']=h.run_id;h.create(cfg)
    with store.transaction() as db:db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    w=diagnostic.restore();p=w.store.artifact(w.freeze['diagnostic_protocol'])
    # Import only the two exact historical manifests and configuration references.
    from extensions.tendon_family.diagnostic_evidence import BoundReader,import_execution
    imported=[import_execution(BoundReader(w.store,b),w.store.artifact(b)['execution_id'],store,host('align').run_id) for b in p['bindings']]
    frozen=dict(authorization=AUTHORIZATION,predecessor=predecessor_snapshot(),provider_configuration=provider,bindings=imported,
        source_binding=read(preparation.RUN/'freeze.json')['source_binding'],incumbent=read(preparation.RUN/'freeze.json')['incumbent'])
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',frozen)
    completed=[];registration=read(preparation.RUN/'registration.json')
    reference=preparation.completed_calculation('reference',dict(operation='reference',intervals=read(diagnostic.RUN/'intervals.json')['result']))
    assert reference is not None
    for name,weight in [('history075',.075),('history15',.15)]:
        cfg=deepcopy(registration['development_configuration']);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
        assert preparation.completed_calculation(name,dict(operation='history',configuration=cfg,initial_state=registration['development_initial_state'],allowance_s=1200.)) is not None
        completed.append(name)
    prior_work=read(preparation.RUN/'accounting.json')['numerical_work']
    admission=preparation.recovery_admission(registration,completed,old.remaining()['remaining'],prior_work)
    admission.update(new_stage_numerical_reservation_s=600.,protected_final_interpretation_export_s=660.,
        reference_integrations_reused=6,complete_previews_reused=2,new_complete_previews=0,predecessor_ledger_unchanged=True)
    assert admission['passed'] and admission['required_solves']==0 and admission['required_wall_s']==660.
    atomic_json(RUN/'recovery_admission.json',admission)


def research(phase,packet,instructions):
    path=RUN/(phase+'_response.json');h=host('research')
    if path.exists():return read(path)
    saved=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_'+phase)
    if saved:
        result=h.store.artifact(saved);atomic_json(path,result);return result
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project='m5-recovery-20261005',binding=read(RUN/'freeze.json')['source_binding']));state.setdefault('fact_catalog',{})
        h.store.update_state(db,h.run_id,state)
    instructions+=' Return exactly one research.milestone5_preparation call: phase='+phase+', two distinct supported holding_weights, rationale, readiness, limitations, next_action=finish_stop. Retain incumbent; M2-4 closed, M5 open. No execution grant or future numerical experiment. Answer in English.'
    configure_role(h,'design',instructions,phase=phase,delivery_tool=RESEARCH.extension_id,native_store_root=str(RUN),memory_identity=h.run_id,native_fixed={},
        binding=read(RUN/'freeze.json')['source_binding'],decision_packet=packet,decision_packet_reference=save(h.store,packet),phase_budget=dict(limit=dict(model_calls=4,tool_calls=10,wall_s=600.)))
    atomic_json(RUN/(phase+'_serialized_handoff.json'),payload_for(h,EvidenceDrivenAdapter()))
    ref=run_until_handoff(h,'m5_'+phase);result=h.store.artifact(ref);atomic_json(path,result);return result


def calculate(name,protocol):
    h=host(name);prior=h.store.lookup(h.run_id,'saved-'+name)
    if prior:
        if not prior['receipt']:raise ValueError('UNRESOLVED_CALCULATION_NO_REPLAY')
        receipt=json.loads(prior['receipt'])
        events=[e for e in h.store.events(h.run_id) if e['request_id']=='saved-'+name and e['status']=='reserved']
        if len(events)!=1:raise ValueError('SAVED_DIAGNOSTIC_REQUEST_BINDING')
        request=h.store.artifact(events[0]['inputs'][0]);saved=h.store.artifact(request['arguments']['protocol'])
        if {k:v for k,v in saved.items() if k!='completed_substitutions'}!={k:v for k,v in protocol.items() if k!='completed_substitutions'}:
            raise ValueError('SAVED_DIAGNOSTIC_PROTOCOL_MISMATCH')
    else:
        if h.store.remaining()['remaining']['wall_s']<1260.:raise ValueError('PROTECTED_FINAL_INTERPRETATION_EXPORT')
        h.resume();receipt=h.invoke(dict(request_id='saved-'+name,tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
            arguments=dict(protocol=save(h.store,protocol)),reason='Bounded retrospective saved-evidence analysis; zero backend advances and zero complete previews',cache='new'))
    atomic_json(RUN/(name+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    result=h.store.artifact(receipt['output'])['detail'];atomic_json(RUN/(name+'.json'),result);return result,receipt['output']


def initial():
    prepare();f=read(RUN/'freeze.json');registration=read(preparation.RUN/'registration.json')
    packet=dict(authorization=AUTHORIZATION,incumbent=f['incumbent'],registered_scenarios=[{k:v for k,v in s.items() if k not in ('full_restorable_new_episode_state','projection')} for s in registration['scenarios']],
        historical_inventory=registration['inventory'],provisional_weights=[.075,.15],saved_reference=read(preparation.RUN/'reference.json'),
        saved_complete_previews=read(preparation.RUN/'preview_summary.json'),costs=dict(previews_s=694.427,evaluations_s=605.937),
        recovery=read(RUN/'recovery_admission.json'),previous_rejection=read(preparation.RUN/'platform_rejection.json'),
        proposed_diagnostic='Align each original historical initializer/recipe with its own backend history; bounded A-D numerical/state/input substitution on one holding-critical interval per recipe. No new complete forecasts.')
    research('selection',packet,'Recover the blocked research handoff using the saved results. Independently answer four questions explicitly in rationale: Are provisional .075/.15 recipes justified for a future experiment? What do saved .20/.30 coordinate/velocity restarts at a NEW zero clock with controller/integrator reset actually test? Is another full validation scientifically worthwhile given known false-safe prediction, vector errors, ranking abstention at unchanged 1e-4 margin, and preview cost exceeding evaluation? Which uncertainty should current diagnostics resolve FIRST? Retain/revise a concrete supported pair or recommend deferring execution. Historical weights do not imply observed future scenario outcomes. Do not rubber-stamp readiness. About 500 words.')
    check_previous()


def diagnose():
    prepare();f=read(RUN/'freeze.json')
    histories=[read(preparation.RUN/(n+'.json'))['result'] for n in ('history075','history15')]
    configurations=[]
    for weight in (.075,.15):
        cfg=deepcopy(read(preparation.RUN/'registration.json')['development_configuration']);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight;configurations.append(cfg)
    aligned,ref=calculate('align',dict(operation='align',bindings=f['bindings'],histories=histories,
        history_configurations=configurations,
        history_sources=['evidence/milestone5_preparation_20261005/'+n+'.json' for n in ('history075','history15')]))
    # Freeze before new numerical comparisons: common holding entry, not the best-looking error timestamp.
    selected=[next(i for i,r in enumerate(c['rows']) if abs(r['start_s']-.30)<1e-9) for c in aligned['result']['cases']]
    selection=dict(rule='First interval starting at holding entry .30 s for each own historical execution. Holding-critical false-safe/.15 contrast and already stable matching observed-state/input reference make substitutions economical. Full onset timeline retained; selection does not erase earlier accumulation.',
        selected_updates=selected,intervals_s=[[.30,.31],[.30,.31]],new_attempt_ceiling=14,
        conditions='A coarse preview start/input; B refine same start/input; C refine projected backend start/preview input; D exact saved backend start/input reference reused; same original task time and .01 duration',
        refinements_s=[.0005,.00025,.000125],reference_qualification='Both successive scalar and vector differences <=1e-4; empirical resolution uncertainty, not a proven bound',
        local_controller_attempts=0,prototype_remaining_attempts=2)
    atomic_json(RUN/'interval_selection.json',selection)
    calculate('compare',dict(operation='compare',alignment=ref,selected_updates=selected,saved_intervals=read(diagnostic.RUN/'intervals.json')['result'],
        saved_reference=read(preparation.RUN/'reference.json'),reference_source='evidence/milestone5_preparation_20261005/reference.json'))
    check_previous()


def final_interpretation():
    prepare();store=Store(RUN);alignment=read(RUN/'align.json')['result'];comp=read(RUN/'compare.json')['result']
    packet=dict(authorization=AUTHORIZATION,selected_weights=read(RUN/'selection_response.json')['holding_weights'],recovery_judgment=read(RUN/'selection_response.json'),
        aligned_summaries=[c['summary'] for c in alignment['cases']],holding_rows=[c['rows'][30] for c in alignment['cases']],
        comparisons=comp,interval_selection=read(RUN/'interval_selection.json'),saved_preview_summary=read(preparation.RUN/'preview_summary.json'),remaining=store.remaining()['remaining'],
        incumbent=read(RUN/'freeze.json')['incumbent'],future_public_reservations=preparation.reservations(),
        readiness_dimensions=['recovery/research handoff','implementation','local numerical reference','physical accuracy','candidate discrimination','cost usefulness','worthwhile bounded prospective hypothesis','milestone acceptance'])
    research('interpretation',packet,'Interpret the aligned historical histories and controlled A-D substitutions. Select exactly ONE primary next action explicitly: improve simulated-plant preview propagation only; repair identified projection defect; repair identified model/input defect; investigate one precisely stated model limitation; or retain local diagnosis and DEFER screening. Explain observed problem, quantitative evidence, remaining gap, exact scoped method/investigation, expected effect, falsifying result, and cost. Do not invent a patch. The fixed-input fine propagation already is an isolated diagnostic prototype; optimizer transcription and production controller remain unchanged. No complete-history benefit is measured. Explicitly interpret vector telescoping terms, speed vs vector differences, residual, cancellation and substitution order; no unique causal percentages. Both B/C successive refinements and existing D reference must be assessed. Separate gradual early accumulation, commands, and optimizer/stopping paths; exact historical warm plans unavailable. Keep selected pair unchanged. Either support a concrete unexecuted first-batch hypothesis or state precise deferral and next targeted investigation; fields alone cannot establish readiness. If proposing future validation retain both previews + pair seal before either complete backend evaluation, both evaluations even if rejected, checkpoint seal before advance, separate local/screening assessment, interpretation/export/stop; second scenario conditional only. Do not lower thresholds/margin or assume modified costs fit 6000 s. About 800 words.')
    check_previous()


def export():
    check_previous();store=Store(RUN);f=read(RUN/'freeze.json');selection=read(RUN/'selection_response.json') if (RUN/'selection_response.json').exists() else None
    interpretation=read(RUN/'interpretation_response.json') if (RUN/'interpretation_response.json').exists() else None
    refs=store.session(host('research').run_id)['state'].get('handoffs',{})
    decisions={phase:refs['m5_'+phase] for phase in ('selection','interpretation') if 'm5_'+phase in refs}
    provisional=selection or dict(holding_weights=[.075,.15],rationale='Provisional historical pair; accepted recovery selection missing')
    p=preparation.protocol(read(preparation.RUN/'registration.json'),provisional,read(preparation.RUN/'reference.json'),research_store=store,decision_refs=decisions,
        supersedes=dict(protocol='evidence/milestone5_preparation_20261005/protocol.json',seal=read(preparation.RUN/'protocol_seal.json'),rejection='evidence/milestone5_preparation_20261005/platform_rejection.json'))
    p.update(version='milestone5_recovery_protocol@1.0.0',status='deferred_not_executed',recovery_complete=bool(selection and interpretation),
        accepted_research_judgment=interpretation,development_data=['milestone5_validation_20261004','milestone5_diagnostic_20261005','milestone5_preparation_20261005','milestone5_recovery_20261005'],
        diagnostic_method='Ordered fixed-input substitutions on original .30-.31 histories; isolated simulated-plant refinement, optimizer unchanged',
        execution_policy='Deferred. No grant, future forecast or backend execution created. Historical 5830/6000 plan remains conditional planning only; any changed complete method requires measured pilot cost and recalculation without changing public rules.')
    p['reservations']['previous_preparation']=p['reservations'].pop('development')
    p['reservations']['recovery']=dict(ceiling=LIMITS,numerical_ceiling=NUMERICAL,admission='recovery_admission.json',protected_final_interpretation_export_s=660.,actual_accounting='accounting.json')
    p['diagnostic_evidence']=dict(alignment='align.json',interval_selection='interval_selection.json',comparisons='compare.json',classification='Retrospective development only')
    p['scientific_next_action']=read(RUN/'final_local_review.json') if (RUN/'final_local_review.json').exists() else interpretation
    if not (selection and interpretation):
        p['status']='deferred_not_ready_research_handoff_blocked'
        p['unresolved_prerequisite']='Automatic approval review rejected DeepSeek transmission despite explicit attachment authorization; direct inline confirmation requested. No accepted recovery judgment or final interpretation exists.'
    p['commands']={'readiness':"& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' examples/milestone5_recovery.py --check",'operational_next_action':'finish_stop'}
    p['implementation_identity']['files'].update({n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('examples/milestone5_recovery.py','extensions/tendon_family/milestone5_recovery.py')})
    atomic_json(RUN/'protocol.json',p);pr=save(store,p)
    atomic_json(RUN/'protocol_seal.json',dict(protocol_reference=pr,protocol_identity=digest(p),supersedes=p['supersedes'],classification='Unexecuted deferred hypothesis protocol revision; no forecast seal',future_forecasts=0,backend_authorized=False))
    from examples.milestone5_future_validation import readiness
    r=readiness(p);r['dimensions']=dict(recovery_handoff_complete=bool(selection and interpretation),implementation_complete=True,numerical_reference_supported='Only the explicitly checked local intervals',physical_accuracy=False,candidate_discrimination=False,cost_usefulness=False,ready_for_bounded_prospective_experiment=False,milestone_acceptance=False)
    atomic_json(RUN/'readiness.json',r)
    with store.transaction() as db:
        store.event(db,host('research').run_id,'recovery_stage','finish_stop',outputs=[pr])
        for row in db.execute('SELECT run_id FROM sessions').fetchall():
            session=store.session(row[0],db);state=session['state'];state['recovery_stage_finished']=True;store.update_state(db,row[0],state,'stopped')
    with store.connect(True) as db:
        receipts=[json.loads(x[0]) for x in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    used=store.remaining()['used'];historical=read(preparation.RUN/'accounting.json')['cumulative'];charges={k:sum(r['charged'][k] for r in receipts) for k in used}
    assert all(abs(used[k]-charges[k])<1e-7 for k in used)
    state=store.session(host('research').run_id)['state']
    accounting=dict(historical=historical,new_stage=used,cumulative={k:historical[k]+used[k] for k in historical},limits=LIMITS,numerical_work=work,receipt_charge_sum=charges,occupied=store.remaining().get('occupied',{}),
        cumulative_numerical_work=dict(controller_solves=79+work['used']['local_solves'],standalone_reduced_rollouts=21+work['used']['prediction_evaluations'],historical_backend_controller_updates=210,new_backend_updates=0),
        reused=dict(preparation_reference_integrations=6,complete_previews=2,comparison_D_reference_integrations=6,recomputation_charge=0),
        corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0),business=state.get('business_failures_total',0)),
        convention='Read/edit/export/test time follows existing offline engineering convention. Graph construction, propagation and nested work charged once by outer calculation receipts. Reused computations have zero new charge.')
    atomic_json(RUN/'accounting.json',accounting);atomic_json(RUN/'receipts.json',receipts)
    with store.connect(True) as db:ids=[row[0] for row in db.execute('SELECT run_id FROM sessions')]
    events=[e for run_id in ids for e in store.events(run_id)];atomic_json(RUN/'events.json',events)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for path in RUN.glob('*.json'):(EVIDENCE/path.name).write_bytes(path.read_bytes())
    # Export immutable artifacts referenced by receipts, events and decision packets.
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (ValueError,KeyError):return # predecessor references retain their exact source
                target=EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'));target.parent.mkdir(exist_ok=True);target.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts)
    for name in ('examples/milestone5_recovery.py','extensions/tendon_family/milestone5_recovery.py','examples/milestone5_preparation.py','examples/milestone5_future_validation.py','tests/test_milestone5_recovery.py'):
        target=EVIDENCE/'implementation'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    atomic_json(EVIDENCE/'delivery.json',dict(status='completed_stopped' if selection and interpretation else 'completed_stopped_with_blocked_research_handoff',research_handoff_complete=bool(selection and interpretation),selection='selection_response.json' if selection else None,interpretation='interpretation_response.json' if interpretation else None,
        protocol='protocol.json',readiness='readiness.json',accounting='accounting.json',incumbent=f['incumbent'],milestone2='closed',milestone3='closed',milestone4='closed',milestone5='open',future_executed=False,future_authorized=False,backend_steps=0,complete_previews=0,subagents=0,pushed=False,operational_next_action='finish_stop',
        blockers=[] if selection and interpretation else [p['unresolved_prerequisite']],engineering_review='final_local_review.json',verification='verification.json'))
    atomic_json(EVIDENCE/'sha256_manifest.json',{p.relative_to(EVIDENCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EVIDENCE.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print(json.dumps(dict(status='stopped',usage=used,numerical=work),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['initial','diagnose','interpret','export']);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        from examples.milestone5_future_validation import readiness
        print(json.dumps(readiness(read(EVIDENCE/'protocol.json')),indent=2))
    elif args.phase=='initial':initial()
    elif args.phase=='diagnose':diagnose()
    elif args.phase=='interpret':final_interpretation()
    elif args.phase=='export':export()
    else:parser.error('Choose a phase; no backend or complete preview path exists.')
