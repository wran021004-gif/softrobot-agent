"""Explicitly linked remaining grant; stopped Milestone 4 ledger stays immutable."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone4 as prior
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.diagnostic_workflow import save,DiagnosticWorkflow
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.live_batch_execution import verified_historical_result
from tools.structural_study import research_planning_input
from tools.candidate_parameters import planning_configuration
from tools.platform_diagnosis_coordinator import configure_role
from tools.study_history import study_history
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.gvs_profile import execution_scope

RUN=ROOT/'runs/milestone45_continuation_20261004/single_context'
EVIDENCE=ROOT/'evidence/milestone45_continuation_20261004'
ORIGINAL=prior.RUN
CONTROL_EXECUTION='a8382f8a4c6e4ebe921fb72f821b2188'
PROFILE=ROOT/'extensions/tendon_family/profiles/milestone4_reach_experiment_v1.json'
FILES=['examples/milestone45_continuation.py','extensions/tendon_family/milestone5_preview.py','tests/test_milestone45.py']
AUTHORIZATION='User pasted request 2026-10-04: explicitly authorized linked continuation after stopped Milestone 4, combined 24 provider/60 tools/4 backends/9000 charged seconds/0 workers; 4 additional corrections max 2 consecutive; at most 6 local solves/12 short predictions. One new structure, 1 or 2 adaptations, prospective forecast, final decision, local commits; no push.'


def revision():
    result=prior.revision();result['files'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES})
    return result


def allocation(old):
    if old['occupied']:raise ValueError('PREDECESSOR_HAS_UNRESOLVED_RESERVATIONS')
    return {k:prior.GRANT[k]-old['used'][k] for k in prior.GRANT}


def compact_decision_packet(value,reference):
    packet=deepcopy(value);history=packet['history']
    keep=('candidate','configuration_identity','status','decisions','structure_identity','weights','metrics')
    history['rows']=[{k:row[k] for k in keep if k in row} for row in history['rows']]
    if 'pilot_assessment' in packet:
        assessment=packet['pilot_assessment']
        for row in assessment['outcomes']:
            for field in ('comparison','against_successful_reference'):
                row[field]={k:v for k,v in row[field].items() if k not in ('baseline','candidate')}
        pair=assessment.get('observed_complete_pair_comparison')
        if pair:assessment['observed_complete_pair_comparison']={k:v for k,v in pair.items() if k not in ('baseline','candidate')}
    if 'frozen_forecast' in packet:
        packet['frozen_forecast'].pop('revision',None)
        packet['frozen_forecast'].pop('usage',None)
    packet['full_packet_reference']=reference
    return packet


class Continuation(prior.MilestoneWorkflow):
    numerical_limits=dict(local_solves=6,prediction_evaluations=12)

    def phase(self,phase,kind,key,**extra):
        if 'decision_packet' in extra and 'history' in extra['decision_packet']:
            # Retain identities, exact decisions and all physical/timing metrics.
            # Repeated detailed meshes/material sections stay in the full sealed
            # packet referenced by decision_packet_reference.
            extra['decision_packet']=compact_decision_packet(extra['decision_packet'],extra.get('decision_packet_reference'))
        return super().phase(phase,kind,key,**extra)

    def check_provider_payload(self,host):
        assert_predecessor(self)
        super().check_provider_payload(host)
        adapter=EvidenceDrivenAdapter();payload=payload_for(host,adapter)
        expected='design.submit_search_plan' if self.store.session(host.run_id)['state']['role_context']['phase']=='improvement' else 'design.respond_diagnosis'
        advertised=[r for r in payload['tools'] if adapter.advertised[r['function']['name']]==expected]
        if len(advertised)!=1:raise ValueError('SERIALIZED_NATIVE_HANDOFF_REQUIRED')
        current=adapter.wire[expected].model_json_schema()
        serialized=advertised[0]['function']['parameters']
        if serialized['anyOf'][0]!={k:v for k,v in current.items() if k!='$defs'}:raise ValueError('SERIALIZED_SCHEMA_NOT_CURRENT')
        atomic_json(self.directory/(self.current_stage+'_serialized_schema_check.json'),dict(passed=True,tool=expected,
            actual_schema=advertised[0]['function']['parameters'],usage=combined(self),revision=revision()))


def assert_predecessor(w):
    old=Store(ORIGINAL)
    if old.remaining()!=w.freeze['authorization_link']['predecessor_usage']:raise ValueError('PREDECESSOR_ACCOUNTING_CHANGED')
    state=old.session(w.freeze['authorization_link']['predecessor_host'])['state']
    if digest(state)!=w.freeze['authorization_link']['predecessor_state_identity']:raise ValueError('PREDECESSOR_TERMINAL_STATE_CHANGED')
    total=combined(w)['combined']
    if any(total[k]>prior.GRANT[k]+1e-8 for k in total):raise ValueError('COMBINED_CEILING_EXCEEDED')


def combined(w):
    old=w.freeze['authorization_link']['predecessor_usage']['used'];new=w.store.remaining()['used']
    return dict(old=old,new=new,combined={k:old[k]+new[k] for k in old},limits=prior.GRANT)


def prepare(directory=RUN):
    from tools.runtime_identity import require_softagent_runtime
    from examples.stage356_milestone2 import scientific_bundle,import_common
    if Path(directory).exists():raise ValueError('CONTINUATION_ALREADY_EXISTS_NO_REPLACEMENT')
    old=Store(ORIGINAL);old_freeze=read(ORIGINAL/'freeze.json');usage=old.remaining();budget=allocation(usage)
    config=deepcopy(old_freeze['experiment']);source=ControlEvidence(old).resolve(CONTROL_EXECUTION)
    config.update(source_store=str(ORIGINAL),execution_id=CONTROL_EXECUTION,source_manifest=source['manifest'],
        evidence_directory=str(EVIDENCE),project_prefix='gvs-milestone45-continuation',authorization_source=AUTHORIZATION,
        provider_freeze=str(ORIGINAL/'freeze.json'))
    w=Continuation(directory,'single_context',experiment=config);w.limits=budget
    w.prepare(require_softagent_runtime());import_common(w,scientific_bundle());prior.prior.previous.prior.import_confirmation(w)
    review=prior.reviewed_changes()
    for dependency in old.session(source['owner'])['snapshot']['dependencies'].values():
        for path,row in review.items():
            previous_hash=dependency['sources'].get(path)
            if previous_hash and previous_hash not in row['historical_hashes']:row['historical_hashes'].append(previous_hash)
    w.historical_results=[verified_historical_result(w.host('design'),Store(p),e,r,review) for r,p,e in prior.SOURCES]
    w.historical_results.append(verified_historical_result(w.host('design'),old,CONTROL_EXECUTION,'historical_candidate',review))
    decision=read(ORIGINAL/'chain.json')['final_response'];prior.prior.copy_reference(w.store,old,decision)
    w.predecessor_decision=decision;w.latest_tested=w.historical_results[-1]['facts']['candidate'];w.retained_baseline=w.historical_results[0]['facts']
    original_host=old_freeze['hosts']['shared'];original_state=old.session(original_host)['state']
    w.freeze.update(historical_results=w.historical_results,compatibility_review=review,milestones2_and3_closed=True,
        authorization_link=dict(predecessor_project=old.config()['project_id'],predecessor_store=str(ORIGINAL),
            predecessor_host=original_host,predecessor_state_identity=digest(original_state),predecessor_usage=usage,
            predecessor_stop_reason=original_state.get('stop_reason'),old_corrections=original_state.get('protocol_corrections_used',0),
            combined_limits=prior.GRANT,continuation_allocation=budget,authorization=AUTHORIZATION),milestone45_revision=revision())
    w.freeze['confirmation_grant_links']=deepcopy(w.freeze['authorization_link'])
    # Same configured provider science/admin values, with explicitly renewed
    # correction segment only. No transfer/reset of the old terminal context.
    model=deepcopy(old_freeze['provider_configuration']);model['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    w.freeze['provider_configuration']=model
    for role in ('shared',):
        child=planning_configuration(w.store,w.latest_tested,w.store.session(w.host('design').run_id)['snapshot']['input']['policy'])
        projected=research_planning_input(child,read(PROFILE),budget=budget,model=model,tool_bindings=w.freeze['tool_bindings'])
        prior.migrate_planning_host(w,'authorized-structure-planning',input_override=projected)
    w.previous=w.host('design');atomic_json(w.directory/'freeze.json',w.freeze)
    atomic_json(w.directory/'authorization_link.json',w.freeze['authorization_link'])
    atomic_json(w.directory/'history_initial.json',study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested))
    return w


def restore():
    freeze=read(RUN/'freeze.json');w=Continuation(RUN,'single_context',experiment=freeze['experiment']);w.freeze=freeze
    w.project=freeze['project_id'];w.limits=freeze['limits'];w.hosts={k:Host(RUN,v) for k,v in freeze['hosts'].items()}
    for attr,key in [('binding','binding'),('identities','identities'),('summary','summary'),('inventory','inventory'),
        ('inventory_ref','inventory_reference'),('common','common_scientific_input'),('source_record','source_record'),('eligibility','numerical_eligibility')]:setattr(w,attr,freeze[key])
    w.chain=read(RUN/'chain.json');w.historical_results=freeze['historical_results'];w.retained_baseline=w.historical_results[0]['facts']
    with w.store.connect(True) as db:
        latest=db.execute("SELECT run_id FROM calls WHERE request_id='complete-profile' AND status='completed' ORDER BY rowid DESC LIMIT 1").fetchone()
    w.latest_tested=next(r['facts']['candidate'] for r in w.historical_results if r['facts']['candidate']['owner_run_id']==latest['run_id']) if latest else w.historical_results[-1]['facts']['candidate']
    w.predecessor_decision=w.chain.get('final_response') or read(ORIGINAL/'chain.json')['final_response']
    w.previous=w.host('design');w.historical_feedback=w.store.artifact(w.common['feedback']);assert_predecessor(w)
    return w


def preview_protocol(w,record,source):
    from schemas.platform import CandidateInput
    from tools.platform_tools import _candidate
    from schemas.platform import SessionInput
    batch=w.store.session(w.host('design').run_id)['state']['search_batch'];base=w.store.artifact(batch['base_configuration'])['effective']
    reader=ControlEvidence(w.store);saved=reader.resolve(source['facts']['execution_id']);observations=reader.read_file(saved,'controller_observations.json')
    # Last retained interval-start state is inside holding and has a one-period
    # effective horizon. This deterministic choice precedes numerical results.
    index=len(observations)-1;ob=observations[index];period=base['task']['timing']['control_period_s']
    if index<1 or abs((base['task']['timing']['duration_s']-ob['time_s'])-period)>1e-8:raise ValueError('LAST_SAVED_HOLDING_SNAPSHOT_REQUIRED')
    previous=observations[index-1]['actual_tension_n']
    snapshot=dict(update_id=index,time_s=ob['time_s'],measured_initial_state=ob['measured_initial_state'],previous_input_n=previous,
        effective_horizon=ob.get('effective_horizon',1),state_reference=dict(reference=saved['files']['controller_observations.json'],pointer=f'/{index}/measured_initial_state'),
        input_reference=dict(reference=saved['files']['controller_observations.json'],pointer=f'/{index-1}/actual_tension_n'),
        source_observation=ob,coordinate_mapping_reference=saved['files']['control_spec.json'])
    if snapshot['effective_horizon']!=1:raise ValueError('ONE_PERIOD_SAVED_EFFECTIVE_HORIZON_REQUIRED')
    snapshot['snapshot_identity']=digest(snapshot)
    configurations=[dict(candidate_id=source['facts']['candidate']['candidate_id'],configuration=source['facts']['configuration'],
        scientific_identity=digest(execution_scope(saved['configuration'])),role='reference')]
    for i,changes in enumerate(record['plan']['candidates']):
        effective=plain(_candidate(SessionInput.model_validate(base),changes,w.host('design').reg));candidate_id=batch['batch_id']+'-'+str(i)
        prepared=CandidateInput(candidate_id=candidate_id,baseline_identity=digest(base),builder=base['policy']['candidate_builder']['extension_id'],
            builder_version=base['policy']['candidate_builder']['version'],changes=changes,allowed=base['policy']['editable'],effective=effective,content_identity=digest(effective))
        configurations.append(dict(candidate_id=candidate_id,configuration=save(w.store,prepared),scientific_identity=digest(execution_scope(effective)),role='adaptation',changes=changes))
    physics=reader.read_file(saved,'resolved_physics.json');tendons=[t['id'] for t in base['robot']['structure']['data']['tendons']]
    if tendons!=[t['entity'] for t in physics['tendons']]:raise ValueError('FROZEN_INPUT_ORDER_MISMATCH')
    return dict(classification='prospective_same_structure_control_pilot',adaptation_plan=w.chain['search_plan'],source=source['facts']['candidate'],
        snapshot=snapshot,configurations=configurations,model='model.gvs@1.0.0',input_order=tendons,
        force_limits_n=[t['force_limit_n'] for t in physics['tendons']],horizon_s=period,integration_step_s=period/5,
        units=dict(state='GVS curvature rad/m followed by curvature rate rad/m/s',input='N',position='world m',speed='world m/s'),
        warm_start='Common cold constant previous-input seed; candidate-model states regenerated independently.',
        limits=dict(max_wall_s=300.,max_local_solves=len(configurations),max_prediction_rollouts=len(configurations)),
        controller_limits={k:base['policy']['controller']['parameters']['data']['recipe'][k] for k in ('max_cpu_s','max_iterations','tolerance','feasible_return')},
        selection='Keep explicit candidate execution order and frozen complete-evaluation physical comparison policy; forecasts are observational.',
        forecast_rule='Lower local endpoint speed suggests lower full-task max holding speed; lower local endpoint target error suggests lower max holding error, with epsilon 1e-6. No absolute pass prediction. Overall ordering unresolved without acceptance.',revision=revision())


def pilot(w,record,source):
    from extensions.tendon_family.milestone5_preview import DEFINITION
    from tools.platform_registry import registry
    protocol=preview_protocol(w,record,source);ref=save(w.store,protocol);atomic_json(w.directory/'pilot_protocol.json',protocol)
    reg=registry();reg.add(DEFINITION)
    inp=deepcopy(w.store.artifact(source['facts']['configuration'])['effective']);inp['run_id']=w.project+'-pilot-numerical'
    inp['policy'].update(budget={**w.limits,'model_calls':0},route=None,tool_bindings={DEFINITION.extension_id:DEFINITION.version},allowed_tools=[],timeout_s=300.)
    inp['policy']['operation_allowances']={DEFINITION.extension_id:dict(timeout_s=300.,reserve_s=300.)}
    numerical=Host(w.directory,inp['run_id'],reg=reg);numerical.create(inp);numerical.resume()
    receipt=numerical.invoke(dict(request_id='prospective-preview',tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
        arguments=dict(protocol=ref),reason='Authorized sealed prospective weight-specific solves and short rollouts before adaptation backend outcomes.',cache='new'))
    atomic_json(w.directory/'pilot_numerical_receipt.json',receipt)
    if receipt['execution_status']!='completed':raise ValueError('PILOT_NUMERICAL_GAP: '+str(receipt.get('error')))
    result=w.store.artifact(receipt['output'])['detail'];w.chain['pilot_numerical']=receipt['output'];atomic_json(w.directory/'pilot_numerical.json',result)
    w.current_stage='pilot_forecast';w.instructions={**w.instructions,'response_final':prior.FINAL+''' Prospective forecast phase, before adaptation executions. Interpret pilot_numerical only within its saved-state scope. Freeze a qualified full-task directional/speed-order hypothesis for each pending candidate, or explicitly abstain. Local endpoint speed is not full-task holding maximum. Joint acceptance and overall ranking remain unknown. Use candidate identities in the packet; do not select an unexecuted deliverable. This interpretation neither changes nor filters the frozen batch. next_research.route=stop, zero proposed_budget; this means no new experiment beyond the already accepted batch, which remains pending. About 250 words.'''}
    packet=dict(pilot_numerical=result,pending_configurations=protocol['configurations'][1:],full_outcomes_available=False,
        retained_baseline=prior.campaign_metrics(w.retained_baseline),completed_results=[dict(candidate_id=source['facts']['candidate']['candidate_id'],metrics=prior.campaign_metrics(source['facts']))])
    compact=w.store.artifact(w.chain['batch_summary'])
    w.phase('response_final','design_response','pilot_forecast',decision_packet=packet,decision_packet_reference=save(w.store,packet),
        batch_result=compact,require_research_route=True,require_research_budget=True,research_records=w.historical_results,latest_tested=w.latest_tested,
        improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
        source_report=w.common['source_report'],source_record=w.source_record)
    forecast=dict(protocol=ref,numerical=receipt['output'],model_interpretation=w.chain['pilot_forecast'],
        interpretation=w.store.artifact(w.chain['pilot_forecast']),forecasts=[dict(candidate_id=r['candidate_id'],configuration=r['configuration'],scientific_identity=r['scientific_identity'],
            **r['full_task_hypothesis']) for r in result['rows'][1:]],predicted_speed_order=result['predicted_speed_order'],predicted_physical_order=None,
        acceptance_prediction='unknown',sealed_before_backend=True,usage=combined(w),revision=revision())
    w.chain['pilot_forecast_seal']=save(w.store,forecast);atomic_json(w.directory/'pilot_forecast_seal.json',forecast)
    with w.store.transaction() as db:
        w.store.event(db,w.host('design').run_id,'prospective_forecast','sealed',inputs=[ref,receipt['output'],w.chain['pilot_forecast']],
            outputs=[w.chain['pilot_forecast_seal']])
    atomic_json(w.directory/'chain.json',w.chain);w.current_stage='adaptation'


def assess_pilot(w):
    forecast=read(w.directory/'pilot_forecast_seal.json');result=read(w.directory/'adaptation_batch_result.json')
    numerical=read(w.directory/'pilot_numerical.json');source=next(r['facts'] for r in w.historical_results if r['facts']['candidate']==read(w.directory/'adaptation_plan.json')['bindings']['subject'])
    from extensions.tendon_family.milestone5_preview import physical_direction
    outcomes=[]
    for predicted in forecast['forecasts']:
        row=next(r for r in result['candidates'] if r['candidate_id']==predicted['candidate_id']);facts=row['execution']['factual_result']
        cfg=w.store.artifact(facts['configuration'])['effective']
        if row['configuration']!=predicted['configuration']:raise ValueError('FORECAST_PREPARED_CONFIGURATION_MISMATCH')
        if digest(execution_scope(cfg))!=predicted['scientific_identity']:raise ValueError('FORECAST_ACTUAL_CONFIGURATION_MISMATCH')
        comparison=prior.compare_results(source,facts);a=prior.campaign_metrics(facts);b=prior.campaign_metrics(source)
        actual=dict(holding_speed_direction=physical_direction(a['holding_max_speed_m_s']-b['holding_max_speed_m_s']),
            holding_position_direction=physical_direction(a['holding_max_error_m']-b['holding_max_error_m']))
        verdict={k:'unresolved' if predicted[k]=='unresolved' or actual[k]=='unresolved' else 'correct' if predicted[k]==actual[k] else 'incorrect' for k in actual}
        outcomes.append(dict(candidate_id=row['candidate_id'],forecast=predicted,observed=actual,verdict=verdict,comparison=comparison,metrics=a,
            against_successful_reference=prior.compare_results(next(r['facts'] for r in w.historical_results if r['facts']['execution_id']==CONTROL_EXECUTION),facts)))
    observed_order=[r['candidate_id'] for r in sorted(outcomes,key=lambda r:r['metrics']['holding_max_speed_m_s'])]
    assessment=dict(status='completed',outcomes=outcomes,predicted_speed_order=forecast['predicted_speed_order'],observed_speed_order=observed_order,
        speed_order_matched=None if forecast['predicted_speed_order'] is None else forecast['predicted_speed_order']==observed_order,
        overall_order='unresolved: forecast abstained because joint acceptance was unknown',predictor_cost_s=numerical['complete_cost_s'],
        full_backend_receipt_cost_s=sum(r['execution']['receipts']['simulation']['charged']['wall_s'] for r in result['candidates'] if r.get('execution')),
        full_evaluation_cost_s=sum(stage['charged']['wall_s'] for r in result['candidates'] if r.get('execution') for stage in r['stages'].values()),
        predictor_tool_charged_s=read(w.directory/'pilot_numerical_receipt.json')['charged']['wall_s'],
        observed_complete_pair_comparison=prior.compare_results(result['candidates'][0]['execution']['factual_result'],result['candidates'][1]['execution']['factual_result']) if len(outcomes)==2 else None,
        forecast_unchanged=True,scope='Initial same-structure control pilot only; no general screening reliability or automatic rejection validation.')
    atomic_json(w.directory/'pilot_assessment.json',assessment);w.chain['pilot_assessment']=save(w.store,assessment);return assessment


def export(w,status,reason,elapsed):
    w.freeze['historical_results']=w.historical_results;w.freeze['milestone45_revision']=revision();atomic_json(w.directory/'freeze.json',w.freeze)
    atomic_json(w.directory/'chain.json',w.chain)
    DiagnosticWorkflow.export(w,status,reason,elapsed)
    from tools.improvement_workflow import archive_store
    destination=EVIDENCE/'single_context';archive_store(w.store,destination,source_stores=[ORIGINAL,*[p for _,p,_ in prior.SOURCES],prior.prior.previous.prior.CONFIRM])
    with w.store.connect(True) as db:
        rows=[dict(row) for row in db.execute('SELECT run_id,request_id,status,charged,receipt FROM calls')]
    atomic_json(destination/'campaign_receipts.json',[dict(run_id=r['run_id'],receipt=json.loads(r['receipt'])) for r in rows if r['receipt']])
    atomic_json(destination/'campaign_calls.json',[{**r,'charged':json.loads(r['charged']),'receipt':json.loads(r['receipt']) if r['receipt'] else None} for r in rows])
    corrections=max(w.store.session(h.run_id)['state'].get('protocol_corrections_used',0) for h in w.hosts.values())
    atomic_json(EVIDENCE/'accounting.json',dict(**combined(w),corrections=dict(old=4,new=corrections,lifetime=4+corrections,new_limit=4,consecutive_limit=2),
        receipt_charge_sum={k:sum(json.loads(r['charged'])[k] for r in rows) for k in prior.GRANT},predecessor_unchanged=True))
    atomic_json(EVIDENCE/'campaign_status.json',dict(status=status,reason=reason,revision=revision(),usage=combined(w)))


def live(stage):
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    # PowerShell caller resolves this exact established configuration path.
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    w=prepare() if stage=='structure' else restore();start=time.monotonic();status='incomplete';reason=None
    if (w.directory/(stage+'_batch_result.json')).exists():raise ValueError('DO_NOT_REPLAY_SEALED_STAGE')
    try:
        if stage=='adaptation':
            decision=read(w.directory/'structure_final_response.json')
            if decision['next_research']['route']!='controller_adaptation':raise ValueError('MODEL_DECLINED_REQUIRED_ADAPTATION')
            current=w.store.session(w.host('design').run_id)['snapshot']['input'];science=planning_configuration(w.store,w.latest_tested,current['policy'])
            projected=research_planning_input(science,read(PROFILE),budget=w.limits,model=w.freeze['provider_configuration'],tool_bindings=w.freeze['tool_bindings'])
            prior.migrate_planning_host(w,'structure-to-adaptation',input_override=projected)
        instructions=(prior.STRUCTURE_PLAN if stage=='structure' else prior.ADAPT_PLAN).replace('No separate numerical diagnostic work.',
            'The explicitly authorized prospective pilot reserves 300 charged seconds, one numerical workflow tool and one model/tool forecast interpretation before adaptation backends. It cannot filter or reorder the batch.')
        instructions+=' This is an explicitly authorized continuation segment with only remaining cumulative capacity. Historical stopped campaign stays stopped, old corrections=4, new segment correction cap=4 (max two consecutive); no usage erased.'
        instructions+=' Selecting a source independently does not require it to differ from latest or baseline. Fixed material/section-scale values are fixed conditions, not additional changes or confounders; use validated actual_differences.'
        if stage=='adaptation':instructions+=' Prefer one-factor holding-weight comparison with two distinct points if remaining capacity supports it, to test speed ordering. Local comparison uses candidate-specific solves; final physical ranking stays unchanged.'
        record=prior.plan(w,stage,1 if stage=='structure' else 2,instructions)
        if stage=='structure':w.freeze['original_research_source']=record['bindings']['subject']
        atomic_json(w.directory/(stage+'_prelaunch_review.json'),dict(passed=True,plan=w.chain['search_plan'],source=record['bindings']['subject'],
            actual_differences=record['actual_differences'],budget=record['available_capacity'],revision=revision(),combined_usage=combined(w)))
        if stage=='adaptation':
            budget=w.store.remaining()['remaining'];requirement=prior.batch_requirement(record['plan']['max_candidates'],preparation_reserve_s=5.)['requirement']
            for k,extra in dict(wall_s=600.,model_calls=1,tool_calls=2).items():requirement[k]+=extra
            if any(v>budget[k] for k,v in requirement.items()):raise ValueError('ADAPTATION_PLUS_PILOT_DELIVERY_CAPACITY_INSUFFICIENT')
        prior.execute(w,stage,record,before_execution=pilot if stage=='adaptation' else None)
        if stage=='adaptation':
            assessment=assess_pilot(w);w.current_stage='pilot_post_outcome'
            w.instructions={**w.instructions,'response_final':prior.FINAL+' Final complete-sequence decision plus post-outcome pilot assessment. Interpret pilot_assessment, explicitly count correct/incorrect/unresolved directions and speed ordering. Explain consequences without inventing a cause of proxy disagreement. Forecast remains unchanged; this is later interpretation. Separate structural effect, adaptation effect, selected complete candidate and timing. next_research.route=stop and zero budget. No further work in this campaign.'}
            packet=read(w.directory/'adaptation_decision_packet.json');packet.update(pilot_assessment=assessment,frozen_forecast=read(w.directory/'pilot_forecast_seal.json'),
                structure_results=read(w.directory/'structure_decision_packet.json')['completed_results'])
            w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=save(w.store,packet),
                batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,
                research_records=w.historical_results,latest_tested=w.latest_tested,
                improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
                source_report=w.common['source_report'],source_record=w.source_record)
            atomic_json(w.directory/'complete_sequence_final_response.json',w.store.artifact(w.chain['final_response']))
            status='sequence_complete';reason='Changed structure, adaptation and accepted final sequence decision; prospective pilot assessed.'
        else:status='structure_complete';reason='Changed-structure full evaluation and accepted model interpretation sealed.'
    except Exception as exc:
        reason=str(exc);atomic_json(w.directory/(stage+'_failure.json'),dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    assert_predecessor(w);export(w,status,reason,time.monotonic()-start)


def resume_structure_interpretation():
    """Concrete recovery of the sealed structural result, no backend path."""
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    w=restore();w.current_stage='structure';w.freeze['confirmation_grant_links']=deepcopy(w.freeze['authorization_link'])
    record=read(w.directory/'structure_plan.json');result=read(w.directory/'structure_batch_result.json')
    if (w.directory/'structure_final_response.json').exists():raise ValueError('STRUCTURE_INTERPRETATION_ALREADY_SEALED')
    start=time.monotonic();status='incomplete';reason=None
    try:
        prior.execute(w,'structure',record,sealed_result=result,decision_extra=dict(plan_semantic_review=read(w.directory/'structure_plan_semantic_review.json')))
        status='structure_complete';reason='Sealed structure interpreted after summary/export host repair; backend not replayed.'
    except Exception as exc:
        reason=str(exc);atomic_json(w.directory/'structure_interpretation_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    assert_predecessor(w);export(w,status,reason,time.monotonic()-start)


def correct_structure_semantics():
    """Paid model correction; original scientific prose remains immutable."""
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    w=restore();w.current_stage='structure_semantic_correction';start=time.monotonic();status='incomplete';reason=None
    record=read(w.directory/'structure_plan.json');packet=read(w.directory/'structure_decision_packet.json')
    review=dict(original_response=w.chain['final_response'],original_preserved=True,semantic_passed=False,
        issue='Reasoning claims clean single-variable attribution is not fully shown because material and section scale are listed in decision fields. Those are fixed values in source and candidate, not changes.',
        actual_differences=record['actual_differences'],fixed_conditions=dict(section_scale=.95,material_scenario='compliant',holding_weight=0.,terminal_weight=.05),
        required_correction='State the observed effect of the single tested near-length change under fixed control. Preserve limited tested-point/simulation scope; do not invent confounding changes. Source and latest are independent roles and can coincide.')
    atomic_json(w.directory/'structure_interpretation_semantic_review.json',review);packet.update(semantic_review=review)
    w.instructions={**w.instructions,'response_final':prior.FINAL+' Correct the precise material issue in semantic_review using actual_differences. Do not rewrite the prior response; this is a superseding interpretation. Keep next_research.route=controller_adaptation for the required separately planned one-or-two-point batch; budgets use shared current requirement, stop at completed target, not merely because source already passes. No new structure or backend execution in this response.'}
    try:
        w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=save(w.store,packet),
            batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,candidate_preparation_reserve_s=5.,
            research_records=w.historical_results,latest_tested=w.latest_tested,
            improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
            source_report=w.common['source_report'],source_record=w.source_record)
        atomic_json(w.directory/'structure_corrected_final_response.json',w.store.artifact(w.chain['final_response']))
        status='structure_complete';reason='Model-authored structural interpretation corrected; original response and all charges preserved.'
    except Exception as exc:reason=str(exc);print('STOP',reason,flush=True)
    assert_predecessor(w);export(w,status,reason,time.monotonic()-start)


def resume_adaptation_interpretation():
    """Interpret sealed adaptations after compacting the public history view."""
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    w=restore();w.current_stage='adaptation';start=time.monotonic();status='incomplete';reason=None
    if (w.directory/'complete_sequence_final_response.json').exists():raise ValueError('COMPLETE_SEQUENCE_ALREADY_SEALED')
    try:
        assessment=assess_pilot(w)
        prior.execute(w,'adaptation',read(w.directory/'adaptation_plan.json'),sealed_result=read(w.directory/'adaptation_batch_result.json'),
            decision_extra=dict(pilot_assessment=assessment,frozen_forecast=read(w.directory/'pilot_forecast_seal.json'),
                structure_results=read(w.directory/'structure_decision_packet.json')['completed_results'],
                forecast_consequence='Local pilot abstained: zero resolved direction/order. All three local attempts stopped at verified_settled_seed, selected iteration zero. Full evaluation remains necessary; no general screening validation.'))
        atomic_json(w.directory/'complete_sequence_final_response.json',w.store.artifact(w.chain['final_response']))
        status='sequence_complete';reason='Complete structure/adaptation sequence and pilot assessment interpreted from sealed results; no backend replay.'
    except Exception as exc:
        reason=str(exc);atomic_json(w.directory/'adaptation_interpretation_failure.json',dict(type=type(exc).__name__,message=reason));print('STOP',reason,flush=True)
    assert_predecessor(w);export(w,status,reason,time.monotonic()-start)


def complete_final_semantics(*,future_only=False):
    """Complete omitted sequence/pilot interpretation through the research model."""
    if subprocess.check_output(['git','diff','HEAD','--',*revision()['files']],cwd=ROOT,text=True):raise ValueError('COMMIT_BEFORE_LIVE')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        if '127.0.0.1:9' in os.environ.get(key,''):os.environ.pop(key)
    w=restore();w.current_stage='final_closure_status' if future_only else 'complete_sequence_semantics';start=time.monotonic();status='incomplete';reason=None
    old=w.chain['final_response'];assessment=read(w.directory/'pilot_assessment.json')
    review=dict(prior_response=old,prior_response_preserved=True,complete_sequence_semantic_passed=False,
        omitted=['Separate structural effect under fixed 0/0.05 recipe.','Frozen pilot forecasts versus outcomes, four unresolved directions and no ordering prediction.','Supported consequence for use of the nondiscriminating local proxy.','Why choose the passing adaptation versus the passing pre-adaptation structure/control pair.'],
        hypothesis_and_physical_comparisons_accurate=True,selection_is_permitted_tradeoff=True)
    atomic_json(w.directory/'final_semantic_review.json',review)
    packet=read(w.directory/'adaptation_decision_packet.json');packet.update(semantic_review=review,pilot_assessment=assessment,
        frozen_forecast=read(w.directory/'pilot_forecast_seal.json'),structure_results=read(w.directory/'structure_decision_packet.json')['completed_results'],
        successful_control_reference=prior.campaign_metrics(next(r['facts'] for r in w.historical_results if r['facts']['execution_id']==CONTROL_EXECUTION)))
    w.instructions={**w.instructions,'response_final':'''Submit one final complete-sequence decision, correcting the omissions in semantic_review. This is the required final deliverable, not a new experiment. Keep next_action=finish, next_research.route=stop with zero budget; no new numerical/backend work. Preserve prior response and forecasts. Use about 450 words in reasoning, in this order: (1) structural effect of near 0.15->0.16 under fixed holding 0 / terminal 0.05 against declared source and retained baseline; (2) adaptation effects for both 0.05 and 0.10 holding points on fixed structure, including joint acceptance loss at 0.10; (3) select any fully evaluated configuration yourself, explicitly justify the choice between passing pre-adaptation 0/0.05 and passing adaptation 0.05/0.05, acknowledging smaller errors versus slightly higher speed and timing as a tradeoff; compare selected outcome also with earlier successful control reference; (4) prospective pilot: zero correct, zero incorrect, four unresolved direction predictions (two metrics x two candidates), no predicted ordering so no ordering match can be established, joint acceptance was unknown; all three local controller attempts selected iteration zero with verified_settled_seed and identical commands, 3 short rollouts; report predictor and full evaluation costs from pilot_assessment. State the supported consequence: retain full evaluation; this saved-state proxy gave no demonstrated direction/ranking capability. Do not call abstention a correct forecast, invent a cause of full-task differences, compare local endpoint speed numerically with maximum holding speed, or rank raw weighted objectives. Report reach/holding/timing separately, with all 35/35 deadline misses and no real-time demonstration. Recommendation disposition is defer with null recommendation_id for hypothesis-only assessment; candidate selection independent. hypothesis_assessment refers to adaptation conjunction, weakened if joint acceptance fails at one tested point. No causal/global/hardware/continuous-time or general screening claims. Author exactly one required next_research with stop/zero budget; future work unexecuted.'''}
    if future_only:
        previous=w.store.artifact(old)
        review=dict(prior_response=old,scientific_reasoning_passed=True,selection_passed=True,
            next_research_status_passed=False,issue='The stop proposal labels current holding-weight candidates pending/unexecuted and their acceptance unknown. Both are fully evaluated; only the sealed pre-outcome forecast had that status.',
            correction='No current candidate remains pending. Stop with zero budget; unresolved questions may concern future validation on a different saved state or untested points, separately authorized, not these two known outcomes.')
        atomic_json(w.directory/'final_closure_status_semantic_review.json',review)
        packet.update(semantic_review=review,previous_final_reasoning=previous['reasoning'],previous_selection=previous['selected_candidate'])
        w.instructions={**w.instructions,'response_final':'''Submit the final response with previous_final_reasoning unchanged (it already accurately covers structure, adaptation, selected tradeoff, costs and the prospective pilot) and preserve previous_selection, disposition=defer with null recommendation_id, hypothesis_assessment=weakened, next_action=finish. Correct only the stale next_research status language identified by semantic_review. Both current adaptation candidates have complete evaluations; none is pending. The pre-outcome forecast had unknown acceptance, but observed joint acceptance is now known (0.05 passes,0.10 fails). next_research.route=stop and zero proposed_budget; bounded_check is none. State only unresolved FUTURE validation questions (for example whether another recorded braking snapshot can distinguish weight-dependent behavior), explicitly unexecuted and requiring new authorization. Do not describe evaluated current candidates as pending or their observed results as unknown. No additional run, forecast revision or new scientific selection.'''}
    try:
        w.phase('response_final','design_response','final_response',decision_packet=packet,decision_packet_reference=save(w.store,packet),
            batch_result=w.store.artifact(w.chain['batch_summary']),require_research_route=True,require_research_budget=True,research_records=w.historical_results,latest_tested=w.latest_tested,
            improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['batch_summary'])],
            source_report=w.common['source_report'],source_record=w.source_record)
        atomic_json(w.directory/('complete_sequence_closed_final_response.json' if future_only else 'complete_sequence_corrected_final_response.json'),w.store.artifact(w.chain['final_response']))
        status='sequence_complete';reason='Accepted model-authored complete-sequence and pilot interpretation supersedes the incomplete final prose; all original evidence preserved.'
    except Exception as exc:reason=str(exc);print('STOP',reason,flush=True)
    assert_predecessor(w);export(w,status,reason,time.monotonic()-start)


if __name__=='__main__':
    if sys.argv[1]=='resume-structure-interpretation':resume_structure_interpretation()
    elif sys.argv[1]=='correct-structure-semantics':correct_structure_semantics()
    elif sys.argv[1]=='resume-adaptation-interpretation':resume_adaptation_interpretation()
    elif sys.argv[1]=='complete-final-semantics':complete_final_semantics()
    elif sys.argv[1]=='correct-final-closure-status':complete_final_semantics(future_only=True)
    else:live(sys.argv[1])
