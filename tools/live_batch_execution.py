"""Real batch stages use the existing receipt-backed execution continuation."""
from copy import deepcopy
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import digest
from tools.execution_completion import complete_execution
from extensions.tendon_family.gvs_profile import execution_scope


def verified_historical_result(host, source_store, execution_id, role, approved_changes):
    """Verify one explicitly supplied complete execution; never query a cache."""
    import json
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.diagnostic_evidence import import_execution
    from extensions.tendon_family.delivery_facts import bound_result_facts
    from tools.platform_registry import dependency_closure
    reader=ControlEvidence(source_store);source=reader.resolve(execution_id)
    snapshot=source_store.session(source['owner'])['snapshot']
    receipts={}
    with source_store.connect(True) as db:
        for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(source['owner'],)):
            receipt=json.loads(row['receipt']);tool=receipt['tool_id']
            stage={'simulation.run':'simulation','evaluation.run':'evaluation','control.profile_report':'profile'}.get(tool)
            if not stage or not receipt.get('output'):continue
            data=source_store.artifact(receipt['output']);detail=data.get('detail',data)
            linked=receipt['execution_id'] if stage=='simulation' else detail.get('source_execution_id' if stage=='evaluation' else 'execution_id')
            if linked!=execution_id:continue
            if stage in receipts:raise ValueError('HISTORICAL_COMPLETE_RECEIPT_NOT_UNIQUE')
            if receipt['execution_status']!='completed' or receipt['tool_version']!='1.0.0':raise ValueError('HISTORICAL_INCOMPLETE_RECEIPT')
            receipts[stage]=receipt
    if set(receipts)!={'simulation','evaluation','profile'}:raise ValueError('HISTORICAL_COMPLETE_CHAIN_REQUIRED')
    sim=receipts['simulation'];evaluation=source_store.artifact(receipts['evaluation']['output'])
    detail=source_store.artifact(receipts['profile']['output'])['detail'];cfg=source['metadata']['candidate_input']
    if (sim.get('solver_status')!='completed' or sim['output']['artifact_id']!=source['metadata']['artifact_id']
            or source['metadata']['instance']!=snapshot['instance_identity']
            or evaluation['validity']!='valid' or evaluation['source']!=sim['output']
            or evaluation['candidate_id']!=source['metadata']['candidate']
            or detail['configuration']!=cfg or detail['simulation']!=sim['output'] or detail['evaluation']!=receipts['evaluation']['output']
            or detail['execution_scope']!=execution_scope(source['configuration'])
            or not detail['complete'] or not detail['valid_complete_execution']
            or detail['official_task_success']!=evaluation['task_success']):raise ValueError('HISTORICAL_RESULT_ASSOCIATION_MISMATCH')
    evaluator=source['configuration']['task']['evaluator']
    if (evaluation['evaluator'],evaluation['evaluator_version'])!=(evaluator['extension_id'],evaluator['version']):
        raise ValueError('HISTORICAL_EVALUATOR_BINDING_MISMATCH')
    # These two additions affect transport/accounting only. All physical schema
    # fields and every other contract must still agree exactly.
    def scientific_schema(value):
        value=deepcopy(value);defs=value.get('$defs',{})
        defs.pop('OperationAllowance',None)
        for name,field in [('ModelConfig','context_guard'),('ExperimentPolicy','operation_allowances')]:
            if name in defs:defs[name]['properties'].pop(field,None)
        return value
    checked={}
    for key,old in snapshot['dependencies'].items():
        if not key.startswith(('simulation.','evaluation.','evaluate.','control.profile_report@','controller.','backend.','model.','initialize.','candidate.family@')):continue
        name,version=key.split('@');current=dependency_closure([host.reg.get(name,version)],host.reg)[key]
        changes={p:dict(historical=h,current=current['sources'].get(p)) for p,h in old['sources'].items() if current['sources'].get(p)!=h}
        if set(old['sources'])!=set(current['sources']):raise ValueError('HISTORICAL_DEPENDENCY_SOURCE_SET_CHANGED: '+key)
        for path,hashes in changes.items():
            review=approved_changes.get(path,{})
            if hashes['historical'] not in review.get('historical_hashes',[]) or hashes['current']!=review.get('current_hash'):
                raise ValueError('HISTORICAL_UNREVIEWED_IMPLEMENTATION_CHANGE: '+path)
        for field in old:
            if field=='sources':continue
            a,b=old[field],current.get(field)
            if field in ('input_schema','output_schema'):a,b=scientific_schema(a),scientific_schema(b)
            if field=='contracts':a,b=({k:scientific_schema(v) for k,v in x.items()} for x in (a,b))
            if a!=b:raise ValueError('HISTORICAL_SCIENTIFIC_DEPENDENCY_CHANGED: '+key+' '+field)
        checked[key]=dict(reviewed_source_changes=changes,python=current['python'],packages=current['packages'],scientific_contracts_match=True)
    binding=dict(reference=receipts['profile']['output'],owner_run_id=source['owner'],execution_id=execution_id,request_id=receipts['profile']['request_id'])
    candidate=dict(candidate_id=source['metadata']['candidate'],owner_run_id=source['owner'],configuration=cfg,execution_id=execution_id)
    facts=bound_result_facts(source_store,dict(profile_report=binding,evaluation=receipts['evaluation']['output'],simulation=sim),candidate)
    seen=set()
    def copy(ref):
        if ref['artifact_id'] in seen:return
        seen.add(ref['artifact_id']);body=source_store.artifact(ref,raw=True)
        with host.store.transaction() as db:
            if plain(host.store.put(db,body,ref['media_type']))!=ref:raise ValueError('HISTORICAL_IMPORT_BYTES_CHANGED')
    imported=import_execution(reader,execution_id,host.store,host.run_id,source['manifest'])
    for ref in [*(r['output'] for r in receipts.values()),detail['motion'],detail['one_step_prediction_evidence']]:copy(ref)
    result=dict(role=role,facts=facts,execution_scope=execution_scope(source['configuration']),binding=imported,
        source_store=str(source_store.root),owner_run_id=source['owner'],execution_id=execution_id,receipts=receipts,
        compatibility=checked,source_commit=snapshot['project_commit'],source_worktree_dirty=snapshot['worktree_dirty'],
        reuse_reason='Explicit complete comparable historical record with verified artifacts, receipts and scientific dependencies; original charges remain historical.')
    with host.store.transaction() as db:
        host.store.event(db,host.run_id,'historical_result_reuse','verified',inputs=[imported],outputs=[host.store.put(db,result)])
    return result


class LiveBatchExecution:
    mode='live'

    def __init__(self,host):self.host=host

    def candidate_host(self,candidate):
        host=Host(self.host.store.root,candidate['candidate_id'],actor=self.host.actor)
        prepared=self.host.store.artifact(candidate['configuration'])
        inp=deepcopy(prepared['effective']);inp['run_id']=host.run_id
        current=self.host.store.session(self.host.run_id)['snapshot']['input']['policy']
        inp['policy'].update(budget={**current['budget'],'model_calls':0},model=current['model'],route=None,allowed_tools=[],
            tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
            operation_allowances={n:dict(timeout_s=s,reserve_s=s) for n,s in
                [('simulation.run',900.),('evaluation.run',30.),('control.profile_report',60.)]})
        if execution_scope(inp)!=execution_scope(prepared['effective']):raise ValueError('BATCH_EXECUTOR_CHANGED_SCIENCE')
        try:session=host.store.session(host.run_id)
        except ValueError:session=host.create(inp)
        from tools.platform_tasks import compile_input
        if session['snapshot']['input']!=compile_input(inp,host.reg)['input']:raise ValueError('BATCH_EXECUTOR_INPUT_CHANGED')
        return host

    def stage(self,stage,candidate):
        host=self.candidate_host(candidate)
        batch=self.host.store.session(self.host.run_id)['state']['search_batch']
        baseline=self.host.store.artifact(batch['base_configuration'])['effective']
        if stage=='apply':return self.host.store.artifact(candidate['configuration'])
        result=complete_execution(host,baseline,candidate['candidate_id'],stop_after=stage)
        receipt=result.get('receipts',{}).get(stage)
        if receipt is None:
            return dict(execution_status='unknown',error=result.get('reason',result['status']),output=None)
        return receipt

    def facts(self,candidate):
        host=self.candidate_host(candidate)
        batch=self.host.store.session(self.host.run_id)['state']['search_batch']
        baseline=self.host.store.artifact(batch['base_configuration'])['effective']
        result=complete_execution(host,baseline,candidate['candidate_id'])
        if result['status']!='evaluated':raise ValueError('BATCH_COMPLETION_UNRESOLVED')
        expected=self.host.store.artifact(candidate['configuration'])['effective']
        actual=self.host.store.artifact(result['configuration'])['effective']
        if execution_scope(actual)!=execution_scope(expected) or actual['robot']!=expected['robot'] or actual['task']!=expected['task']:
            raise ValueError('BATCH_REAL_RESULT_CONFIGURATION_MISMATCH')
        return result
