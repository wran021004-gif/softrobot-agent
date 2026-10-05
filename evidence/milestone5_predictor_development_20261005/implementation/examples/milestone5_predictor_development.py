"""One linked development ledger; validation grant is conditional, never implicit."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_first_interval as previous
from examples import milestone5_preparation as preparation
from tools.platform_store import Store,encode,plain
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.state_io import read,atomic_json,digest
from tools.runtime_identity import require_softagent_runtime
from tools.diagnostic_workflow import save
from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
from extensions.tendon_family.milestone5_predictor import DEFINITION,CONTINUATION_STEPS,PREDICTOR_VERSION
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.diagnostic_evidence import BoundReader,import_execution

RUN=ROOT/'runs/milestone5_predictor_development_20261005'
EVIDENCE=ROOT/'evidence/milestone5_predictor_development_20261005'
LIMITS=dict(model_calls=10,tool_calls=50,backend_solves=0,worker_calls=0,wall_s=4800.)
NUMERICAL=dict(reference_integrations=3,prediction_evaluations=12,local_solves=80,preview_attempts=2)
VALIDATION_LIMITS=dict(model_calls=4,tool_calls=16,backend_solves=2,worker_calls=0,wall_s=6000.)
AUTHORIZATION=dict(source='User attachment f6b47ec6-a617-4cc5-a5de-8999c641dcfa, 2026-10-05',
    destination='https://api.deepseek.com',model='deepseek-flash',development_limits=LIMITS,numerical_limits=NUMERICAL,
    conditional_first_batch_limits=VALIDATION_LIMITS,conditional_backend_attempts=2,backend_steps_during_development=0,
    credentials='Normal authentication only from Join-Path $HOME .codex/.env; never serialized',workers=0,subagents=0,
    commit=True,push_remote='origin',push_branch='feat/gvs-dynamics',force_push=False)


def reg():
    r=registry();r.add(DEFINITION);return r


def host(name):
    names=read(RUN/'session_revision.json') if (RUN/'session_revision.json').exists() else {}
    return Host(RUN,names.get(name,'m5develop-'+name),reg=reg())


def migrate():
    """Explicit session revision in the SAME grant; no usage reset."""
    names=read(RUN/'session_revision.json') if (RUN/'session_revision.json').exists() else {}
    for name in ('compute','research'):
        old=host(name)
        if old.compatibility()['compatible']:continue
        inp=deepcopy(old.store.session(old.run_id)['snapshot']['input'])
        inp['policy']['tool_bindings'][DEFINITION.extension_id]=DEFINITION.version
        inp['policy']['model']['tool_naming']=tool_naming_policy(inp['policy']['tool_bindings'],READABLE_TOOL_NAMING)
        names[name]=old.run_id+'-r';inp['run_id']=names[name]
        new=Host(RUN,names[name],reg=reg());new.create(inp)
        with new.store.transaction() as db:
            old_session=new.store.session(old.run_id,db);preserved=deepcopy(old_session['state'])
            if preserved.get('role_context',{}).get('phase_budget'):
                phase=preserved['role_context']['phase_budget'];old_usage=new.store.remaining(old.run_id,db)['used']
                phase['started_usage']={k:phase['started_usage'][k]-old_usage[k] for k in old_usage}
            new.store.update_state(db,new.run_id,preserved,'stopped')
            running=db.execute("SELECT 1 FROM calls WHERE run_id=? AND status='running'",(old.run_id,)).fetchone()
            if not running:
                s=new.store.session(old.run_id,db);new.store.update_state(db,old.run_id,s['state'],'stopped')
            new.store.event(db,new.run_id,'implementation_revision','same_grant_no_counter_reset',outputs=[new.store.put(db,dict(previous=old.run_id,usage=new.store.remaining()['used']))])
    atomic_json(RUN/'session_revision.json',names)


def snapshot():
    folders=[previous.RUN,previous.EVIDENCE,preparation.RUN,preparation.EVIDENCE,
        ROOT/'runs/milestone5_recovery_20261005',ROOT/'evidence/milestone5_recovery_20261005']
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in folders for p in folder.rglob('*') if p.is_file() and p.suffix not in ('.db-wal','.db-shm') and not p.name.endswith(('-wal','-shm'))}


def check_previous():
    assert snapshot()==read(RUN/'freeze.json')['predecessors'],'PREDECESSOR_CHANGED'


def prepare():
    require_softagent_runtime()
    if (RUN/'freeze.json').exists():check_previous();return
    old=Store(previous.RUN);inp=deepcopy(old.session(previous.host('research').run_id)['snapshot']['input'])
    store=Store(RUN)
    if not store.db.exists():store.create(dict(project_id='m5-predictor-development-20261005',grant_id='m5-predictor-development-20261005',
        budget=LIMITS,authorization_source=json.dumps(AUTHORIZATION)))
    else:assert store.config()['budget']==LIMITS
    bindings={DEFINITION.extension_id:DEFINITION.version,RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    provider=deepcopy(read(previous.RUN/'freeze.json')['provider_configuration']);provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    provider['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    inp['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=bindings,model=provider,timeout_s=600.,
        operation_allowances={DEFINITION.extension_id:dict(timeout_s=1200.,reserve_s=1200.),
        RESEARCH.extension_id:dict(timeout_s=10.,reserve_s=5.),'evidence.read':dict(timeout_s=10.,reserve_s=5.)})
    for name in ('compute','research'):
        cfg=deepcopy(inp);cfg['run_id']=host(name).run_id
        with store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(cfg['run_id'],)).fetchone()
        if not exists:host(name).create(cfg)
    with store.transaction() as db:db.execute("INSERT OR IGNORE INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    imported=[]
    for binding in read(previous.RUN/'freeze.json')['bindings']:
        r=BoundReader(old,binding);imported.append(import_execution(r,r.binding['execution_id'],store,host('compute').run_id))
    r=BoundReader(old,read(previous.RUN/'freeze.json')['source_binding'])
    incumbent=import_execution(r,r.binding['execution_id'],store,host('research').run_id)
    frozen=dict(authorization=AUTHORIZATION,predecessors=snapshot(),bindings=imported,source_binding=incumbent,
        provider_configuration=provider,incumbent=read(previous.RUN/'freeze.json')['incumbent'],
        accepted_direction=read(previous.RUN/'interpretation_response.json'),accepted_selection=read(previous.RUN/'selection_response.json'),
        cases=dict(shared_first=[0.,.01],early_divergence=[.01,.02],holding_entry=[.30,.31],
            historical_executions=[store.artifact(b)['execution_id'] for b in imported],complete_history_scope=[0.,.35],holding_window=[.30,.35]),
        quantities=['shape and rate reconstruction','world position and Jacobian velocity','local vector/speed/position/direction errors',
            'last TWO successive fine vector/speed differences','known false-safe outcomes','pair ranking coverage/order/abstention','cost versus ONE skipped evaluation'],
        criteria=dict(reference='Finite roots, residual <=1e-5 and two final vector AND speed differences <=1e-4; no backend-agreement gate',
            local_vector_tolerance_m_s=1e-4,local_speed_tolerance_m_s=1e-4,ranking_margin_m_s=1e-4,physical_position_limit_m=.01,physical_speed_limit_m_s=.02,
            prospective=['correct implementation and causal inputs','supported reference for claimed scope','one evidence-backed correction with limitations',
                'resolved useful historical discrimination; universal abstention fails','known failures handled within claimed role',
                'measured screening cost < expected ONE skipped complete evaluation cost','concrete independent experiment','accepted research interpretation','budget sufficient']),
        maximum_work=NUMERICAL,development_limits=LIMITS,validation_limits=VALIDATION_LIMITS,
        exit_conditions=['Stop reference after stability or three attempts','No physical parameter fitting or production control changes',
            'No full preview if an output-only correction permits exact reuse of independent causal state/input/optimizer histories',
            'No prospective batch unless ALL frozen prerequisites pass','Stop and export precise no-go on unresolved prerequisite'],
        protected_interpretation_export_s=1265.,reference_reserve_s=1200.,analysis_reserve_s=1200.,
        corrections=dict(total=4,consecutive=2),conditional_validation_ledger='Separate matching grant ONLY after checks pass; predecessor counters immutable')
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',frozen)
    atomic_json(RUN/'development_plan_seal.json',dict(identity=digest(frozen),frozen_before_new_results=True))
    print(json.dumps(dict(status='frozen',cases=frozen['cases'],limits=LIMITS)))


def calculate(name,p):
    prepare();h=host('compute');request='development-'+name;prior=h.store.lookup(h.run_id,request)
    if prior:
        if not prior['receipt']:raise ValueError('UNRESOLVED_ATTEMPT_NO_REPLAY')
        receipt=json.loads(prior['receipt'])
        event=next(e for e in h.store.events(h.run_id) if e['request_id']==request and e['status']=='reserved')
        saved=h.store.artifact(h.store.artifact(event['inputs'][0])['arguments']['protocol'])
        if saved!=p:raise ValueError('REQUEST_BINDING_MISMATCH')
    else:
        if h.store.remaining()['remaining']['wall_s']<2465.:raise ValueError('PROTECTED_INTERPRETATION_EXPORT')
        h.resume();receipt=h.invoke(dict(request_id=request,tool_id=DEFINITION.extension_id,tool_version=DEFINITION.version,
            arguments=dict(protocol=save(h.store,p)),reason='Authorized bounded development; no backend steps or production changes',cache='new'))
    atomic_json(RUN/(name+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    result=h.store.artifact(receipt['output'])['detail'];atomic_json(RUN/(name+'.json'),result);check_previous()
    print(json.dumps(dict(phase=name,status='completed',numerical_stability_supported=result.get('numerical_stability_supported'),complete_cost_s=result.get('complete_cost_s'))));return result


def complete_reference():
    return calculate('reference',dict(operation='reference',specification=read(previous.RUN/'specification.json'),
        completed_results=read(previous.RUN/'calculation.json')['results'],
        projected_observed_output=read(previous.RUN/'calculation.json')['observed_projected_output']))


def recover_reference():
    """Export completed subresults after a failed outer call. Never replay it."""
    from extensions.tendon_family.milestone5_first_interval import stable,differences,output_accounting
    store=Store(RUN)
    with store.connect(True) as db:
        calls=db.execute("SELECT run_id,receipt FROM calls WHERE request_id='development-reference'").fetchall()
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
    if len(calls)!=1 or not calls[0]['receipt']:raise ValueError('REFERENCE_STILL_UNRESOLVED')
    receipt=json.loads(calls[0]['receipt'])
    if receipt['execution_status']=='completed':raise ValueError('USE_COMPLETED_REFERENCE_OUTPUT')
    spec=read(previous.RUN/'specification.json');earlier=read(previous.RUN/'calculation.json');results=list(earlier['results'])
    for e in store.events(calls[0]['run_id']):
        if e['kind']=='reference_continuation_completed':
            saved=store.artifact(e['outputs'][0]);assert saved['specification_identity']==spec['identity'];results.append(saved['result'])
    assert len({r['step_s'] for r in results})==len(results)
    atomic_json(RUN/'reference.json',dict(specification_identity=spec['identity'],shared_identity=spec['shared_identity'],results=results,
        numerical_stability_supported=stable(results),fine_differences=differences(results[1:]),measured_uncertainty=differences(results)[-1],
        new_integration_attempts=work['used']['reference_integrations'],new_integrations=len(results)-len(earlier['results']),reused_integrations=len(earlier['results']),
        failed_attempts=work['used']['reference_integrations']-(len(results)-len(earlier['results'])),failed_outer_receipt=receipt,
        endpoint_accounting=output_accounting(results[-1],earlier['observed_projected_output'],spec['observed']),
        reference_scope='Shared original .00-.01 s only; finest COMPLETED tested result, not stabilized',
        failure_classification='The third declared integration exceeded an incorrectly undersized 400 s per-integration guard. Not evidence of numerical instability or nonfinite roots.',
        backend_steps=0,controller_attempts=0,residual_limit=1e-5))
    atomic_json(RUN/'interventions.json',dict(setup=[dict(issue='Initial freeze used artifact reference as execution identity',correction='Resolve bound artifact execution_id before freeze; no numerical work or charged workflow call'),
        dict(issue='Source edits invalidated session dependency fingerprints',correction='Preserved old snapshots and created explicit session revisions in SAME project/grant; no counter reset'),
        dict(issue='Third reference integration per-attempt guard 400 s versus roughly 600 s measured scaling',correction='Preserved two completed subresults and failed third attempt; no fourth integration, no stability claim, no backend. Corrected future guard to 800 s in diagnostic tool 1.0.1, keeping the 1200 s outer reservation. That repaired reference path is unexecuted. Bound remaining numerical-reference investigation to this missing resolution under fresh authorization')],
        semantic_provider_corrections=0,backend_replacements=0,workers=0,subagents=0))
    print(json.dumps(dict(status='reference_partial_recovered_no_replay',completed_new=len(results)-6,attempts=work['used']['reference_integrations'],stable=stable(results))))


def analyze(ctx,p):
    import time
    import numpy as np
    from extensions.tendon_family.milestone5_serial_output import SerialOutput
    from extensions.tendon_family.gvs_projection import project,PROJECTOR_ID
    from extensions.tendon_family.gvs_basis import resolve_basis
    from schemas.platform import SessionInput
    from extensions.tendon_family.diagnostic_math import NonlinearModel
    from extensions.tendon_family.milestone5_recovery import motion,norm
    start=time.perf_counter();frozen=read(RUN/'freeze.json');cases=[]
    alignment=read(ROOT/'runs/milestone5_recovery_20261005/align.json')['result']['cases']
    for binding,case in zip(frozen['bindings'],alignment):
        r=BoundReader(ctx.store,binding);s=r.resolve(r.binding['execution_id']);cfg=s['configuration']
        physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json')
        trajectory=r.read_file(s,'trajectory.json.gz');updates=r.read_file(s,'controller_observations.json')
        out=SerialOutput(cfg,physics,compiled,ctx.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
        if p['operation']=='localize':
            model=NonlinearModel(cfg,case['rows'][0]['observed_start_projected_state'],case['rows'][0]['actual_input_n'],.01)
            inp=SessionInput.model_validate(cfg);basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
            rows=[]
            for i in (0,1,29,30):
                saved=case['rows'][i];end=trajectory[i];z=np.array(saved['observed_end_projected_state']);serial=out.motion(z)
                backend=out.raw(end['qpos_rad'],end['qvel_rad_s']);continuous=motion(model,z)
                reconstructed=project(physics,basis,out.mapping@z[:out.n],out.mapping@z[out.n:])
                roundtrip=norm(z,reconstructed['q_gvs']+reconstructed['qdot_gvs'])
                dt=1e-7;plus=z.copy();minus=z.copy();plus[:out.n]+=dt*z[out.n:];minus[:out.n]-=dt*z[out.n:]
                continuous_fd=norm((np.asarray(motion(model,plus)['position_m'])-motion(model,minus)['position_m'])/(2*dt),continuous['velocity_m_s'])
                qhat=out.mapping@z[:out.n];vhat=out.mapping@z[out.n:]
                rows.append(dict(endpoint_s=end['time_s'],continuous=continuous,represented_serial=serial,
                    backend={k:backend[k] for k in ('position_m','velocity_m_s','speed_m_s')},
                    serial_jacobian_fd_error_m_s=out.differential_check(z),continuous_jacobian_fd_error_m_s=continuous_fd,
                    projection_roundtrip_norm=roundtrip,
                    represented_cell_angle_residual_rad=norm(qhat,end['qpos_rad']),represented_cell_rate_residual_rad_s=norm(vhat,end['qvel_rad_s']),
                    represented_shape_max_error_m=float(np.max(np.linalg.norm(np.asarray(serial['body_positions_m'])-end['body_positions_m'],axis=1))),
                    decomposition={k:dict(continuous_minus_serial=(np.asarray(continuous[k])-serial[k]).tolist(),
                        serial_minus_backend=(np.asarray(serial[k])-backend[k]).tolist(),
                        continuous_backend_norm=norm(continuous[k],backend[k]),serial_backend_norm=norm(serial[k],backend[k])) for k in ('position_m','velocity_m_s')},
                    saved_state=trajectory[i],sources=dict(binding=binding,trajectory=s['files']['trajectory.json.gz'],pointer='/'+str(i))))
            cases.append(dict(execution_id=s['execution_id'],rows=rows,output_setup_s=out.setup_s))
        else:
            cases.append(assess_case(out,case,s,r,updates,ctx,p))
    if p['operation']=='localize':
        return dict(cases=cases,projector_identity=PROJECTOR_ID,frame='world',units='m, s, rad; same XML tip_site and compiled joint/body indices',
            backend_steps=0,integrations=0,controller_attempts=0,complete_cost_s=time.perf_counter()-start,
            classification='Both mappings are differentiably consistent with their own position maps. The continuous-to-serial kinematic definition differs; reduced projection drops cell shape/rate components. A representation/model discrepancy is not established as a projection implementation bug.')
    return assessment_summary(cases,time.perf_counter()-start)


def localize():return calculate('localization',dict(operation='localize',frozen_plan_identity=read(RUN/'development_plan_seal.json')['identity']))


def assess_case(out,case,source,reader,updates,ctx,p):
    import time
    import numpy as np
    from extensions.tendon_family.milestone5_recovery import norm
    from extensions.tendon_family.milestone5_serial_output import VERSION
    from extensions.tendon_family.milestone5_first_interval import differences,output_accounting,stable
    from extensions.tendon_family.milestone5_validation import local_score,TOLERANCES
    from extensions.tendon_family.milestone5_protocol import assess_local
    from extensions.tendon_family.gvs_profile import execution_scope
    locals=[];shared=read(RUN/'reference.json')
    refs=read(preparation.RUN/'reference.json')['result']['rows']
    for index in (0,1,30):
        row=case['rows'][index]
        if index==0:results=shared['results'];reference_supported=shared['numerical_stability_supported']
        elif index==30:
            ref=next(r for r in refs if r['execution_id']==source['execution_id']);results=ref['results'];reference_supported=ref['numerical_reference_established']
        else:
            saved=row['actual_one_step'];results=[dict(state=saved['state'],position_m=saved['tip_position_m'],velocity_m_s=saved['tip_velocity_m_s'],
                speed_m_s=float(np.linalg.norm(saved['tip_velocity_m_s'])),step_s=.01,complete_cost_s=None)]
            reference_supported=False
        assert updates[index]['actual_tension_n']==updates[index]['desired_tension_n']==row['actual_input_n']
        corrected=[dict(**r,serial_output=out.motion(r['state'])) for r in results]
        a=out.motion(row['observed_start_projected_state']);observed=dict(row['observed_endpoint'],target_m=source['configuration']['task']['goal']['data']['target_m'])
        serial_fine=[dict(**r['serial_output'],step_s=r['step_s']) for r in corrected]
        d=differences(serial_fine);stable_serial=stable(serial_fine) if index==0 else len(d)>=2 and all(x['velocity_m_s']<=1e-4 and x['speed_m_s']<=1e-4 for x in d[-2:])
        # Practical version uses .000125, not the extremely fine offline reference.
        working=next((r for r in corrected if r['step_s']==.000125),corrected[0])
        coarse=next((r for r in corrected if r['step_s']==.00025),None)
        uncertainty=None if coarse is None else dict(velocity_m_s=norm(working['serial_output']['velocity_m_s'],coarse['serial_output']['velocity_m_s']),
            speed_m_s=abs(working['serial_output']['speed_m_s']-coarse['serial_output']['speed_m_s']),position_m=norm(working['serial_output']['position_m'],coarse['serial_output']['position_m']))
        def prediction(end,initial,stable_flag):
            return dict(endpoint_position_m=end['position_m'],endpoint_velocity_m_s=end['velocity_m_s'],endpoint_speed_m_s=end['speed_m_s'],
                initial_projected_speed_m_s=initial['speed_m_s'],initial_backend_speed_m_s=row['observed_start']['speed_m_s'],
                start_s=row['start_s'],end_s=row['end_s'],numerical_stable=stable_flag)
        fine=corrected[-1];fine_prediction=prediction(fine['serial_output'],a,reference_supported and stable_serial)
        work_prediction=prediction(working['serial_output'],a,reference_supported and stable_serial and uncertainty is not None and uncertainty['velocity_m_s']<=1e-4 and uncertainty['speed_m_s']<=1e-4)
        old_prediction=prediction(working,row['projected_observed_start'],reference_supported)
        finest_unc=0. if not d else d[-1]['speed_m_s']
        score=assess_local(work_prediction,observed,0. if uncertainty is None else uncertainty['speed_m_s'])
        score['position_within_tolerance']=score['position_error_norm_m']<=TOLERANCES['position_m']
        # The finest numerical result and the affordable working version are separate.
        finest_score=assess_local(fine_prediction,observed,finest_unc)
        old_score=local_score(old_prediction,observed)
        projected=out.motion(row['observed_end_projected_state'])
        cost=None if coarse is None else working['complete_cost_s']+coarse['complete_cost_s']
        locals.append(dict(interval_s=[row['start_s'],row['end_s']],version=VERSION,working_prediction=work_prediction,
            input_n=row['actual_input_n'],input_information_time_s=row['start_s'],input_policy='Saved pre-step desired == actual ideal direct tension held for .01 s; retrospective development',
            working_step_s=working['step_s'],working_score=score,saved_continuous_same_resolution_score=old_score,
            numerical_uncertainty=uncertainty,reference_supported=reference_supported and stable_serial,reference_scope='This exact fixed-state/fixed-command interval only',
            serial_reference_differences=d[-2:],finest_tested_score=finest_score,finest_tested_step_s=fine['step_s'],
            ordered_physical_error=output_accounting(fine['serial_output'],projected,observed),
            measured_reused_two_grid_calculation_cost_s=cost,cost_convention='Previous measured construction/integration costs reused, plus separately measured output mapping. No duplicated integration charge.',
            early_interval_role='Coarse saved one-step mapping check only; no supported fine reference' if index==1 else 'Working .000125 versus offline finest reference'))
    name='history075' if case['configuration']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']==.075 else 'history15'
    saved=read(preparation.RUN/(name+'.json'))['result'];forecast=deepcopy(saved)
    saved_cfg=deepcopy(read(preparation.RUN/'registration.json')['development_configuration'])
    saved_cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=case['configuration']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']
    assert digest(saved_cfg)==saved['configuration_identity'] and execution_scope(saved_cfg)==execution_scope(case['configuration'])
    bound=preparation.completed_calculation(name,dict(operation='history',configuration=saved_cfg,
        initial_state=read(preparation.RUN/'registration.json')['development_initial_state'],allowance_s=1200.))
    assert bound['result']==saved,'REUSED_FORECAST_RECEIPT_BINDING'
    output_start=time.perf_counter()
    for row in forecast['rows']:
        # Only the candidate's own previously sealed forecast state enters this map.
        row.update(out.motion(row['state']));row['error_m']=norm(row['position_m'],source['configuration']['task']['goal']['data']['target_m'])
    holding=[r for r in forecast['rows'] if r['endpoint_s']>=.3-1e-9]
    forecast.update(version=VERSION,candidate_id=name,
        metrics=dict(holding_max_speed_m_s=max(r['speed_m_s'] for r in holding),holding_max_error_m=max(r['error_m'] for r in holding),terminal_error_m=forecast['rows'][-1]['error_m']),
        output_map_cost_s=time.perf_counter()-output_start,controller_policy='Unchanged production controller.gvs_nmpc@7.0.0 continuous objectives and transcription; candidate owns warm plan and commanded tensions',
        propagation='Unchanged reduced implicit transcription at .01 s; output-only correction does not feed back into control',
        reuse='Exact saved independent causal predictor histories; no measured future state/input or observed outcome enters re-output',
        retrospective=True,new_controller_attempts=0,new_preview_attempts=0)
    assert len(forecast['rows'])==35 and forecast['interval_s']==[0.,.35]
    assert all(row['initial_state']==saved['rows'][i]['initial_state'] and row['state']==saved['rows'][i]['state'] and row['input_n']==saved['rows'][i]['input_n'] and row['plan_identity']==saved['rows'][i]['plan_identity'] for i,row in enumerate(forecast['rows']))
    actual_holding=[r['observed_endpoint'] for r in case['rows'] if r['end_s']>=.3-1e-9]
    outcome=dict(candidate_id=name,holding_max_speed_m_s=max(r['speed_m_s'] for r in actual_holding),
        joint_acceptance=max(r['speed_m_s'] for r in actual_holding)<=.02 and max(r['error_m'] for r in actual_holding)<=.01)
    return dict(candidate_id=name,execution_id=source['execution_id'],locals=locals,forecast=forecast,outcome=outcome,output_setup_s=out.setup_s,
        source_manifest=source['manifest'])


def assessment_summary(cases,new_cost):
    from extensions.tendon_family.milestone5_protocol import pair_decision,assess_screening
    histories=[c['forecast'] for c in cases];decision=pair_decision(histories)
    previous_summary=read(preparation.RUN/'preview_summary.json')
    additional_output_s=sum(c['forecast']['output_map_cost_s']+c['output_setup_s'] for c in cases)
    screening_cost=previous_summary['cost_s']+additional_output_s
    # Exact historical complete-pair charges come from the original receipts, below.
    costs=historical_backend_costs();pair_cost=sum(costs.values())
    score=assess_screening(decision,[c['outcome'] for c in cases],screening_cost,pair_cost)
    skipped=decision['hypothetical_rejection'];saving=0. if skipped is None else costs[skipped]
    # Even the larger of either single evaluation is an upper bound on a ONE-skipped saving.
    economic_possible=screening_cost<max(costs.values())
    locals=[l for c in cases for l in c['locals']];primary=[l for l in locals if l['working_step_s']<.01]
    unique_primary=[cases[0]['locals'][0]]+[c['locals'][2] for c in cases]
    return dict(version=PREDICTOR_VERSION,cases=cases,decision=decision,screening_assessment=score,
        previous_screening=previous_summary['predicted'],
        local_counts=dict(planned=len(locals),first_interval_shared_duplicate_reports=1,primary_reports=len(primary),primary_unique_intervals=len(unique_primary),
            reference_supported=sum(l['reference_supported'] for l in locals),direction_resolved=sum(l['working_score']['direction_verdict']!='unresolved' for l in primary),
            direction_correct=sum(l['working_score']['direction_verdict']=='correct' for l in primary),
            working_vector_passes=sum(l['working_score']['vector_within_tolerance'] for l in primary),
            working_speed_passes=sum(l['working_score']['endpoint_within_tolerance'] for l in primary),
            working_position_passes=sum(l['working_score']['position_within_tolerance'] for l in primary),
            holding_false_safe=sum(l['working_score']['physical_holding_false_safe'] for l in primary)),
        unique_primary_counts=dict(planned=len(unique_primary),direction_resolved=sum(l['working_score']['direction_verdict']!='unresolved' for l in unique_primary),
            direction_correct=sum(l['working_score']['direction_verdict']=='correct' for l in unique_primary),
            vector_passes=sum(l['working_score']['vector_within_tolerance'] for l in unique_primary),speed_passes=sum(l['working_score']['endpoint_within_tolerance'] for l in unique_primary),
            position_passes=sum(l['working_score']['position_within_tolerance'] for l in unique_primary),holding_false_safe=sum(l['working_score']['physical_holding_false_safe'] for l in unique_primary)),
        economics=dict(one_time_new_analysis_s=new_cost,reused_complete_history_cost_s=previous_summary['cost_s'],new_output_map_s=additional_output_s,
            per_pair_forecast_cost_s=screening_cost,complete_evaluation_costs_s=costs,complete_pair_cost_s=pair_cost,
            one_skipped_evaluation_upper_bound_s=max(costs.values()),required_retained_evaluation_cost_s=min(costs.values()),
            selected_skipped_evaluation_cost_s=saving,hypothetical_net_savings_s=saving-screening_cost,
            possible_one_skipped_cost_benefit=economic_possible,actual_validation_savings_s=0,
            setup_amortization='Mapping setup included once per candidate; skipping setup cannot eliminate the 694 s state/controller history cost'),
        complete_cost_s=new_cost,new_integrations=0,new_controller_attempts=0,new_complete_previews=0,
        remaining_limitation='Reduced cell-rate modes and continuum/serial dynamics mismatch persist. Output correction alone cannot repair independent state/input histories or make existing controller forecast cost economical.',
        safety_claim=False,production_changes=0)


def historical_backend_costs():
    """Follow owning-store links; take complete simulation receipts, never guessed filenames."""
    from examples import milestone5_validation as validation
    batch=read(validation.RUN/'validation_batch_result.json');origin=Store(validation.RUN)
    costs={};frozen=read(RUN/'freeze.json');store=Store(RUN)
    for name,binding in zip(('history075','history15'),frozen['bindings']):
        source=BoundReader(store,binding).binding
        row=next(c for c in batch['candidates'] if c['candidate_id']==source['candidate_id'])
        receipts=row['execution']['receipts']
        simulation=next(r for r in receipts.values() if r['tool_id']=='simulation.run')
        assert simulation['execution_id']==source['execution_id']
        for receipt in receipts.values():
            with origin.connect(True) as db:rows=db.execute('SELECT receipt FROM calls WHERE execution_id=? AND receipt IS NOT NULL',(receipt['execution_id'],)).fetchall()
            assert any(json.loads(row[0])==receipt for row in rows),'HISTORICAL_COST_RECEIPT_MISMATCH'
        costs[name]=sum(r['charged']['wall_s'] for r in receipts.values())
    return costs


def assess():return calculate('assessment',dict(operation='assess',correction=read(RUN/'correction.json'),reference=read(RUN/'reference.json')))


def interpretation():
    from tools.platform_diagnosis_coordinator import configure_role,run_until_handoff
    from tools.platform_models import payload_for
    from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
    from examples.gvs_nmpc_route_experiment import load_credential
    prepare();h=host('research');path=RUN/'interpretation_response.json'
    prior=h.store.session(h.run_id)['state'].get('handoffs',{}).get('m5_interpretation')
    if prior:atomic_json(path,h.store.artifact(prior));return
    load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
    ref=read(RUN/'reference.json');assessment=read(RUN/'assessment.json');localization=read(RUN/'localization.json')
    compact_localization=[dict(execution_id=c['execution_id'],rows=[{k:v for k,v in r.items() if k not in ('saved_state','represented_serial','sources','continuous','backend')} for r in c['rows']]) for c in localization['cases']]
    packet=dict(authorization=AUTHORIZATION,selected_weights=read(RUN/'freeze.json')['accepted_selection']['holding_weights'],
        frozen_criteria=read(RUN/'freeze.json')['criteria'],incumbent=read(RUN/'freeze.json')['incumbent'],
        reference={k:v for k,v in ref.items() if k!='results'},reference_finest_completed={k:v for k,v in ref['results'][-1].items() if k!='state'},
        localization=compact_localization,correction=read(RUN/'correction.json'),
        local_cases=[dict(candidate_id=c['candidate_id'],locals=c['locals']) for c in assessment['cases']],
        screening={k:v for k,v in assessment.items() if k not in ('cases',)},
        forecast_metrics=[dict(candidate_id=c['candidate_id'],predicted=c['forecast']['metrics'],observed=c['outcome']) for c in assessment['cases']],
        first_future_scenario='incumbent_checkpoint_20_new_clock; exact restored state, zero clock/controller reset/direct input semantics unchanged, unobserved outcomes',
        conditional_authorization='Two attempts ONLY if ALL criteria pass; otherwise no grant and no backend',
        remaining=Store(RUN).remaining()['remaining'],realtime='Historical incumbent 35/35 deadline misses; unchanged, not addressed by offline mapping')
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];state.setdefault('fact_scope',dict(project='m5-predictor-development-20261005',binding=read(RUN/'freeze.json')['source_binding']));state.setdefault('fact_catalog',{})
        h.store.update_state(db,h.run_id,state)
    instruction=('Interpret the actual scientific evidence and make a real go/no-go decision against the FROZEN criteria. '
        'Do not certify merely that fields exist. Distinguish completed local self-consistency, physical agreement, and candidate discrimination. '
        'The prior accepted selection and direction C are reused; do not reselect or repeat recovery. '
        'Evaluate ONE predictor-only represented serial output correction; both Jacobians can be correct for different position maps, and projection drops cell modes. '
        'Report quantitative failures, cancellation of large terms, .075 known false-safe, resolved ranking count/order or abstention, cost versus ONE skipped evaluation, retained evaluation still required. '
        'Fine reference and affordable .000125 working local predictor are separate; a two-grid working check is not two-successive-reference convergence. '
        'Saved early .01-.02 coarse interval has no fine reference, and original .00-.01 references do not validate complete histories. '
        'Exact output-only forecast state/input/plan histories are reused with completed receipt bindings and no future observed data entering their re-output; no new 70-solve preview is required for this isolated correction. '
        'If any frozen criterion fails, conclude NOT READY, name exact remaining obstacle and ONE bounded next investigation with a falsification test, without a broad parameter fit or new campaign. '
        'State supported local diagnostic uses, whether screening is deferred/experimental/supported, when complete evaluation remains necessary, whether another batch is justified, why incumbent remains. '
        'No promotion, no M5 closure; broader repeatability/real-time unmet. Return exactly ONE native research.milestone5_preparation call: phase interpretation, '
        'holding_weights unchanged [.075,.15], rationale, readiness, limitations, next_action finish_stop. About 650 words. No text JSON substitute.')
    configure_role(h,'design',instruction,phase='interpretation',delivery_tool=RESEARCH.extension_id,native_store_root=str(RUN),memory_identity=h.run_id,
        native_fixed={},binding=read(RUN/'freeze.json')['source_binding'],decision_packet=packet,decision_packet_reference=save(h.store,packet),
        phase_budget=dict(limit=dict(model_calls=6,tool_calls=12,wall_s=1200.),protect_project=dict(wall_s=65.)))
    atomic_json(RUN/'interpretation_serialized_handoff.json',payload_for(h,EvidenceDrivenAdapter()))
    decision=run_until_handoff(h,'m5_interpretation');atomic_json(path,h.store.artifact(decision));check_previous()


def export():
    check_previous();store=Store(RUN);frozen=read(RUN/'freeze.json');ref=read(RUN/'reference.json');assessment=read(RUN/'assessment.json')
    interpretation=read(RUN/'interpretation_response.json') if (RUN/'interpretation_response.json').exists() else None
    old=Store(previous.RUN);selection_ref=old.session(previous.host('research').run_id)['state']['handoffs']['m5_selection']
    state=store.session(host('research').run_id)['state'];decision_refs=dict(selection=selection_ref)
    if interpretation is not None:
        decision_refs['interpretation']=state['handoffs']['m5_interpretation']
        if store.artifact(decision_refs['interpretation'])!=interpretation:
            raise ValueError('SAVED_INTERPRETATION_BINDING_MISMATCH')
    p=preparation.protocol(read(preparation.RUN/'registration.json'),frozen['accepted_selection'],read(preparation.RUN/'reference.json'))
    p=preparation.finalize_protocol(p,research_store=store,decision_refs=decision_refs,decision_stores=dict(selection=old),
        supersedes=dict(protocol='evidence/milestone5_first_interval_20261005/protocol.json',seal=read(previous.RUN/'protocol_seal.json')))
    p.update(version='milestone5_predictor_development@1.0.0',status='not_ready_first_batch_not_launched',preview_version=PREDICTOR_VERSION,
        local_version=PREDICTOR_VERSION,accepted_research_judgment=interpretation,
        development_plan='freeze.json',development_assessment='assessment.json',correction='correction.json',
        reference_scope=dict(original_first_interval=ref['numerical_stability_supported'],holding_entry_original_cases=True,early_divergence_fine_reference=False,
            changed_serial_output_scope='Recomputed two final comparisons on same stored reference states; see assessment',complete_history_reference=False),
        batches=p['batches'][:1],continuation='Only the first batch is conditionally authorized. No second scenario batch. No grant before all frozen criteria pass.',
        prospective_outcomes_observed=False,prospective_forecasts_generated=False,
        accepted_research_decision_sources=dict(selection=str(previous.RUN),interpretation=str(RUN)),
        conditional_authorization=AUTHORIZATION,operational_next_action='finish_stop')
    # Full-history numerical reference and future .20 checkpoint are not established by local stability.
    checks=dict(correct_implementation=True,causal_data_use=True,
        supported_first_reference=ref['numerical_stability_supported'],evidence_backed_one_correction=True,
        useful_historical_discrimination=assessment['decision']['status']=='resolved' and assessment['screening_assessment']['pairwise_order_verdict']=='correct',
        known_failures_handled=not assessment['screening_assessment']['predicted_safe_observed_violating'],
        measured_screening_cost_benefit=assessment['economics']['possible_one_skipped_cost_benefit'],
        independent_experiment_worth_performing=False,research_interpretation_accepted=p['research_interpretation_complete'])
    p['development_entry_checks']=checks;p['ready_for_bounded_prospective_experiment']=all(checks.values())
    if p['ready_for_bounded_prospective_experiment']:raise ValueError('GO_REQUIRES_VALIDATION_PATH_BEFORE_FINISH')
    # Recompute from CURRENT public allowances; never treat the old 5830 value as proof.
    from tools.batch_budget import batch_requirement
    base=batch_requirement(2,planning=dict(model_calls=0,tool_calls=0,wall_s=0.),preparation_reserve_s=5.)
    required=deepcopy(base['requirement']);required['tool_calls']+=4;required['wall_s']+=3000.+180.+60.
    p['reservations']=dict(development=dict(ceiling=LIMITS,numerical=NUMERICAL),
        batch1=dict(public_base=base,complete_requirement=required,ceiling=VALIDATION_LIMITS,
            preview_reserve_s=3000.,local_overhead_reserve_s=180.,export_reserve_s=60.,
            controller_attempts=dict(preview=70,production=70,combined=140),
            method_specific_admitted=False,reason='Development fails scientific/economic entry; changed-method complete preview and causal checkpoint costs not validated. No launch.'))
    p['commands']=dict(status='python examples/milestone5_predictor_development.py --phase export',execution='No grant materialized; no executable first batch authorized until frozen scientific and changed-method budget checks pass')
    files=['examples/milestone5_predictor_development.py','extensions/tendon_family/milestone5_predictor.py',
        'extensions/tendon_family/milestone5_serial_output.py','extensions/tendon_family/milestone5_first_interval.py','examples/milestone5_preparation.py']
    p['implementation_identity']['files'].update({n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files})
    atomic_json(RUN/'protocol.json',p);seal=save(store,p);atomic_json(RUN/'protocol_seal.json',dict(protocol_reference=seal,identity=digest(p),backend_grant_materialized=False,forecasts_sealed=False))
    atomic_json(RUN/'readiness.json',dict(checks=checks,passed=False,failed=[k for k,v in checks.items() if not v],
        numerical_accuracy_preserved_failed=True,first_batch_authorization_conditional=True,grant_materialized=False,
        backend_attempts=0,backend_steps=0,future_forecasts=0,real_time_status='Unmet; production unchanged',milestone5='open'))
    with store.transaction() as db:
        for row in db.execute('SELECT run_id FROM sessions').fetchall():
            session=store.session(row[0],db);session['state']['development_finished']=True;store.update_state(db,row[0],session['state'],'stopped')
        store.event(db,host('research').run_id,'development','finish_stop',outputs=[seal])
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0]);ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    used=store.remaining()['used'];historical=read(previous.RUN/'accounting.json')['cumulative'];charges={k:sum(r['charged'][k] for r in receipts) for k in used}
    assert all(abs(charges[k]-used[k])<1e-7 for k in used),'RECEIPT_RECONCILIATION'
    semantic_corrections=read(RUN/'interventions.json').get('semantic_provider_corrections',0)
    protocol_corrections=dict(total=state.get('protocol_corrections_used',0),consecutive=state.get('protocol_corrections_consecutive',0))
    correction_usage=dict(protocol_recovery=protocol_corrections,semantic_provider_corrections=semantic_corrections,
        total=protocol_corrections['total']+semantic_corrections,total_limit=frozen['corrections']['total'],
        consecutive_limit=frozen['corrections']['consecutive'],
        note='One semantic follow-up; both native responses accepted. Protocol recovery counters remain unchanged; all provider attempts included above.')
    assert correction_usage['total']<=correction_usage['total_limit'],'CORRECTION_BUDGET_EXCEEDED'
    atomic_json(RUN/'accounting.json',dict(historical=historical,development=used,validation={k:0 for k in used},
        cumulative={k:historical[k]+used[k] for k in historical},development_limits=LIMITS,conditional_validation_limits=VALIDATION_LIMITS,
        receipt_charge_sum=charges,numerical_work=work,occupied=store.remaining()['occupied'],
        cumulative_numerical_work=dict(controller_attempts=79+work['used']['local_solves'],standalone_integrations=41+work['used']['reference_integrations']+work['used']['prediction_evaluations'],
            historical_backend_controller_updates=210,new_backend_updates=0),
        protocol_corrections=protocol_corrections,correction_usage=correction_usage,
        reused=dict(prior_first_integrations=6,holding_reference_integrations=6,holding_substitutions=14,complete_independent_histories=2,new_charge=0),
        convention='All numerical analysis/model construction/kinematic re-output charged once in outer receipts. Prior numerical work reused without charge. Editing, focused verification and export use existing offline engineering accounting. No workers/subagents.'))
    atomic_json(RUN/'receipts.json',receipts);events=[e for i in ids for e in store.events(i)];atomic_json(RUN/'events.json',events)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    for file in RUN.glob('*.json'):(EVIDENCE/file.name).write_bytes(file.read_bytes())
    seen=set()
    def copy(value):
        if isinstance(value,dict):
            if set(value)=={'artifact_id','media_type'} and isinstance(value['artifact_id'],str) and isinstance(value['media_type'],str):
                key=value['artifact_id']
                if key in seen:return
                seen.add(key)
                try:body=store.artifact(value,raw=True)
                except (ValueError,KeyError):return
                dest=EVIDENCE/'artifacts'/(key+('.json' if value['media_type']=='application/json' else '.bin'));dest.parent.mkdir(exist_ok=True);dest.write_bytes(body)
                if value['media_type']=='application/json':copy(json.loads(body))
            else:
                for child in value.values():copy(child)
        elif isinstance(value,list):
            for child in value:copy(child)
    copy(events);copy(receipts)
    for n in files+['tests/test_milestone5_predictor.py']:
        if (ROOT/n).exists():
            dest=EVIDENCE/'implementation'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/n).read_bytes())
    atomic_json(EVIDENCE/'delivery.json',dict(status=p['status'],incumbent=frozen['incumbent'],milestone2='closed',milestone3='closed',milestone4='closed',milestone5='open',
        scientific_go=False,research_interpretation_accepted=interpretation is not None,backend_attempts=0,backend_steps=0,prospective_results=None,
        conditional_first_batch='Not launched; no grant; exact scenario/recipe outcomes remain unobserved',second_batch_authorized=False,
        report='docs/milestone5_predictor_development.md',accounting='accounting.json',protocol='protocol.json',workers=0,subagents=0,operational_next_action='finish_stop'))
    atomic_json(EVIDENCE/'sha256_manifest.json',{f.relative_to(EVIDENCE).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(EVIDENCE.rglob('*')) if f.is_file() and f.name!='sha256_manifest.json'})
    print(json.dumps(dict(status=p['status'],usage=used,work=work),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='migrate':migrate()
    elif args.phase=='reference':complete_reference()
    elif args.phase=='recover-reference':recover_reference()
    elif args.phase=='localize':localize()
    elif args.phase=='assess':assess()
    elif args.phase=='interpret':interpretation()
    elif args.phase=='export':export()
    else:raise ValueError('Unsupported phase')
