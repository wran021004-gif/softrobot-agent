"""Receipt-backed continuation of the three existing complete-execution tools.

Sealed receipts are the commit boundary. Missing receipts keep their reservation
and remain unresolved, even if intermediate artifacts exist. No automatic replay.
"""
from copy import deepcopy
import json
from pathlib import Path
import time

from tools.platform_store import plain, zero
from tools.state_io import digest

STAGES=(('simulation','simulation.run'),('evaluation','evaluation.run'),('profile','control.profile_report'))


def structured_feedback(store, result, source):
    """Coverage from actual timestamps; reach evaluator semantics stay unchanged."""
    from extensions.tendon_family.control_evidence import ControlEvidence
    detail=store.artifact(result['receipts']['profile']['output'])['detail']
    motion=store.artifact(detail['motion']);timing=source['configuration']['task']['timing']
    from tools.acceptance_definitions import resolve_acceptance
    definitions=resolve_acceptance(dict(effective=source['configuration']),result['configuration'],profile=detail,
        profile_reference=result['receipts']['profile']['output'])
    if definitions['missing']:raise ValueError('ACCEPTANCE_DEFINITION_MISSING: '+str(definitions['missing']))
    duration=definitions['holding']['duration']['value'];position_limit=definitions['holding']['position']['value']
    speed_limit=definitions['holding']['speed']['value'];terminal_limit=definitions['terminal']['value']
    end=timing['duration_s'];start=end-duration;period=timing['sample_period_s']
    window=[r for r in motion if start-1e-9<=r['time_s']<=end+1e-9]
    times=[r['time_s'] for r in window]
    expected=[start+i*period for i in range(round(duration/period)+1)]
    coverage=len(times)==len(expected) and all(abs(a-b)<1e-8 for a,b in zip(times,expected))
    position=max((r['tip_error_m'] for r in window),default=None)
    speed=max((r['tip_speed_m_s'] for r in window),default=None)
    commands=ControlEvidence(store).read_file(source,'actual_commands.json')
    reach=result['evaluation_data']['task_success'];valid=result['evaluation_data']['validity']=='valid'
    return dict(completion={k:'completed' for k,_ in STAGES},source_execution_id=source['execution_id'],
        source_owner=source['owner'],configuration=result['configuration'],evaluator=source['configuration']['task']['evaluator'],
        acceptance_definition=definitions,
        terminal=dict(error_m=detail['terminal_error_m'],limit_m=terminal_limit,passed=reach),
        holding=dict(interval_s=[start,end],sample_times_s=times,sample_count=len(times),coverage_complete=coverage,
            max_position_error_m=position,position_limit_m=position_limit,position_passed=position<=position_limit if coverage else None,
            max_speed_m_s=speed,speed_limit_m_s=speed_limit,speed_passed=speed<=speed_limit if coverage else None,
            speed_definition='Euclidean norm of tip-site translational Jacobian times recorded backend qvel, reconstructed with sealed robot.xml and qpos; no finite differencing',
            speed_units='m/s',frame='world',continuous_time_guarantee=False),
        actual_applied_control_updates=len(commands) if commands is not None else None,
        initialization_selected=detail['initialization_selected'],newly_optimized_selected=detail['accepted_noninitialization_plans'],
        simulated_duration_s=detail['last_valid_time_s'],simulation_wall_s=detail['simulation_wall_s'],
        deadline_misses=detail['deadline_misses'],mean_complete_update_s=detail['mean_update_s'],
        reach_only_success=reach,joint_reach_holding_success=bool(valid and reach and coverage and position<=position_limit and speed<=speed_limit),
        evidence=dict(simulation=result['receipts']['simulation']['output'],evaluation=result['receipts']['evaluation']['output'],
            profile=result['receipts']['profile']['output'],motion=detail['motion'],manifest=source['manifest'],
            commands=source['files'].get('actual_commands.json')),
        missing_data=[] if coverage and commands is not None else ['Holding coverage or applied commands incomplete'],
        timing_qualification='Initialization-selected plans apply control. Synchronous wall overruns do not establish skipped updates or simulated actuator delay.')


def completed_receipt(store, run_id, request_id):
    row=store.lookup(run_id,request_id)
    if row:return json.loads(row['receipt']) if row['receipt'] else None
    imported=store.session(run_id)['state'].get('completion_import',{})
    receipt=imported.get('receipt')
    return receipt if receipt and request_id=='complete-simulation' else None


def source_for(host, simulation):
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.diagnostic_evidence import BoundReader
    imported=host.store.session(host.run_id)['state'].get('completion_import')
    reader=BoundReader(host.store,imported['binding']) if imported else ControlEvidence(host.store)
    source=reader.resolve(simulation['execution_id'])
    if source['metadata']['artifact_id']!=simulation['output']['artifact_id']:
        raise ValueError('CONTINUATION_SOURCE_LINKAGE_MISMATCH')
    for ref in [source['manifest'],source['metadata']['candidate_input'],simulation['output'],*source['files'].values()]:
        host.store.artifact(ref,raw=True)
    return source


def import_completed_simulation(host, source_store, execution_id):
    """Explicit read-only source migration. Original costs/owner stay historical.

    Only simulation is imported; evaluation/profile are new charged operations.
    This is not a copied calls table or a new simulation receipt.
    """
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.diagnostic_evidence import import_execution
    from extensions.tendon_family.gvs_profile import execution_scope
    from tools.platform_registry import dependency_identity
    prior=host.store.session(host.run_id)['state'].get('completion_import')
    if prior:
        if prior['source_store']!=str(source_store.root) or prior['execution_id']!=execution_id:
            raise ValueError('CONTINUATION_IMPORT_COLLISION')
        source_for(host,prior['receipt'])
        return prior
    request='import-completed-simulation'
    old=host.store.lookup(host.run_id,request)
    if old:raise ValueError('UNRESOLVED_IMPORT: reconcile the retained reservation; no replay')
    row,_=host.store.reserve(host.run_id,request,digest(dict(source=str(source_store.root),execution=execution_id)),
        host.actor,{**zero(),'tool_calls':1,'wall_s':30.})
    started=time.monotonic()
    try:
        reader=ControlEvidence(source_store);source=reader.resolve(execution_id)
        original=source_store.lookup(source['owner'],source['metadata']['request_id'])
        receipt=json.loads(original['receipt']) if original and original['receipt'] else None
        if not receipt or receipt['execution_status']!='completed' or receipt.get('solver_status')!='completed' or receipt['execution_id']!=execution_id:
            raise ValueError('VERIFIED_COMPLETED_SIMULATION_REQUIRED')
        snapshot=host.store.session(host.run_id)['snapshot']
        if execution_scope(source['configuration'])!=execution_scope(snapshot['input']):
            raise ValueError('CONTINUATION_SCIENTIFIC_SCOPE_MISMATCH')
        if source['metadata']['instance']!=snapshot['instance_identity']:
            raise ValueError('CONTINUATION_INSTANCE_MISMATCH')
        if receipt['tool_id']!='simulation.run' or receipt['tool_version']!='1.0.0':
            raise ValueError('CONTINUATION_SIMULATION_VERSION_MISMATCH')
        binding=source['configuration']['task']['evaluator']
        name=binding['extension_id']+'@'+binding['version']
        historical=source_store.session(source['owner'])['snapshot']['dependencies'][name]
        current=dependency_identity(host.reg.get(binding['extension_id'],binding['version']))
        # Explicit infrastructure migration; the evaluator binding, scientific
        # source, contracts, runtime and packages must remain identical.
        infrastructure={'schemas/platform.py','tools/platform_host.py','tools/platform_store.py'}
        changes=[p for p,h in historical['sources'].items() if current['sources'].get(p)!=h]
        if set(changes)-infrastructure or any(historical[k]!=current[k] for k in
                ('version','python','packages','input_schema','output_schema','declaration')):
            raise ValueError('HISTORICAL_EVALUATOR_SEMANTICS_CHANGED')
        imported=import_execution(reader,execution_id,host.store,host.run_id,source['manifest'])
        result=dict(binding=imported,source_store=str(source_store.root),execution_id=execution_id,
            owner_run_id=source['owner'],receipt=receipt,evaluator=binding,
            infrastructure_migration=changes,semantic_difference=None,
            historical_charged_usage=receipt['charged'],new_simulation_charge=zero())
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state']
            state['completion_import']=result
            state.setdefault('result_executions',{})[execution_id]=source['metadata']
            host.store.update_state(db,host.run_id,state)
            host.store.event(db,host.run_id,'completion_import','verified',inputs=[imported],outputs=[host.store.put(db,result)])
        status='completed';error=None
    except Exception as exc:
        status='failed';error=str(exc);result=None
    host.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],caller=host.actor,
        tool_id='execution.import_completed',tool_version='1.0.0',execution_status=status,error=error,charged=zero()),
        result,time.monotonic()-started)
    if error:raise ValueError(error)
    return result


def complete_execution(host, baseline, candidate_id, *, stop_after=None):
    from extensions.tendon_family.candidate import candidate_facts
    from extensions.tendon_family.delivery_facts import bound_result_facts
    from extensions.tendon_family.gvs_profile import execution_scope
    host.resume()
    state=host.store.session(host.run_id)['state']
    identity=dict(candidate_id=candidate_id,input_identity=host.store.session(host.run_id)['snapshot']['input_identity'],
        baseline_identity=digest(plain(baseline)),completion_implementation=digest(Path(__file__).read_text(encoding='utf8')))
    record=state.get('execution_completion',dict(identity=identity,stages={}))
    if record['identity']!=identity:raise ValueError('CONTINUATION_IDENTITY_MISMATCH')
    receipts={};source=None
    for key,tool in STAGES:
        request_id='complete-'+key
        receipt=completed_receipt(host.store,host.run_id,request_id)
        row=host.store.lookup(host.run_id,request_id)
        if row and not receipt:
            host.store.mark_unknown(host.run_id,request_id)
            events=[e for e in host.store.events(host.run_id) if e['execution_id']==row['execution_id']]
            # Artifacts alone cannot prove sealed completion or its actual charge.
            return dict(status='execution_unresolved',stage=key,receipts=receipts,
                execution_id=row['execution_id'],retained_evidence=[r for e in events for r in e['outputs']],
                reason='Reservation has no sealed receipt; artifacts inspected, completion and charge remain uncertain. No replay.')
        if not receipt:
            if key=='simulation':args=dict(candidate_id=candidate_id,changes={})
            elif key=='evaluation':args=dict(result=receipts['simulation']['output'],execution_id=receipts['simulation']['execution_id'])
            else:args=dict(simulation_request_id='complete-simulation',evaluation_request_id='complete-evaluation')
            receipt=host.invoke(dict(request_id=request_id,tool_id=tool,tool_version='1.0.0',arguments=args,
                reason='Authorized single complete execution and fixed evaluation/profile',cache='new'))
        receipts[key]=receipt
        if receipt['execution_status']!='completed':
            return dict(status='execution_unresolved' if receipt['execution_status']=='unknown' else 'execution_incomplete',stage=key,receipts=receipts)
        if receipt['tool_id']!=tool or receipt['tool_version']!='1.0.0':raise ValueError('CONTINUATION_OPERATION_VERSION_MISMATCH')
        data=host.store.artifact(receipt['output'])
        if key=='simulation':
            source=source_for(host,receipt)
            if source['metadata']['candidate']!=candidate_id or execution_scope(source['configuration'])!=execution_scope(host.store.session(host.run_id)['snapshot']['input']):
                raise ValueError('CONTINUATION_CANDIDATE_MISMATCH')
        elif key=='evaluation':
            evaluator=source['configuration']['task']['evaluator']
            if (data['source_execution_id']!=receipts['simulation']['execution_id'] or data['source']!=receipts['simulation']['output']
                    or data['candidate_id']!=candidate_id or data['evaluator']!=evaluator['extension_id'] or data['evaluator_version']!=evaluator['version']):
                raise ValueError('CONTINUATION_EVALUATION_LINKAGE_MISMATCH')
        else:
            detail=data['detail']
            if (detail['execution_id']!=source['execution_id'] or detail['configuration']!=source['metadata']['candidate_input']
                    or detail['simulation']!=receipts['simulation']['output'] or detail['evaluation']!=receipts['evaluation']['output']):
                raise ValueError('CONTINUATION_PROFILE_LINKAGE_MISMATCH')
            for field in ('motion','one_step_prediction_evidence'):host.store.artifact(detail[field])
        stage=dict(candidate_id=candidate_id,configuration=source['metadata']['candidate_input'],source_execution_id=source['execution_id'],
            source_owner=source['owner'],operation=tool,version=receipt['tool_version'],status='completed',receipt=receipt,
            evaluator=source['configuration']['task']['evaluator'],charged_usage=receipt['charged'],
            accounting_scope='historical_source_only' if key=='simulation' and state.get('completion_import') else 'current_store')
        if key in record['stages'] and record['stages'][key]!=stage:raise ValueError('CONTINUATION_STAGE_RECORD_CHANGED')
        if key not in record['stages']:
            record['stages'][key]=stage
            with host.store.transaction() as db:
                state=host.store.session(host.run_id,db)['state'];state['execution_completion']=record
                host.store.update_state(db,host.run_id,state)
                host.store.event(db,host.run_id,'execution_completion',key,inputs=[receipt['output']],outputs=[host.store.put(db,stage)])
        if stop_after==key:return dict(status='continuation_pending',completed_stage=key,receipts=receipts)
    sim=receipts['simulation'];ev=receipts['evaluation'];profile=receipts['profile']
    configuration=source['metadata']['candidate_input']
    facts=candidate_facts(baseline,host.store.artifact(configuration),configuration,candidate_id,source['owner'],sim['execution_id'])
    binding=dict(reference=profile['output'],owner_run_id=source['owner'],execution_id=sim['execution_id'],request_id='complete-profile')
    result=bound_result_facts(host.store,dict(profile_report=binding,evaluation=ev['output'],simulation=sim),facts)
    evaluation=host.store.artifact(ev['output']);detail=host.store.artifact(profile['output'])['detail']
    if detail['official_task_success']!=evaluation['task_success'] or detail['evaluation_validity']!=evaluation['validity']:
        raise ValueError('COMPLETE_EVALUATION_INCONSISTENT')
    completed=dict(status='evaluated',receipts=receipts,execution_id=sim['execution_id'],configuration=configuration,
        design_statement=facts,factual_result=result,profile_report=binding,evaluation_data=evaluation,
        completion_stages=record['stages'],profile_producer_run_id=host.run_id)
    completed['structured_feedback']=structured_feedback(host.store,completed,source) if source['configuration']['task']['family']=='task.reach' else None
    return completed
