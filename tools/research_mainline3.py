"""Small independent fixed workflow; default only constructs a future request."""
from copy import deepcopy
from pathlib import Path
import argparse
import time
from tools.state_io import read,atomic_json
from tools.platform_store import plain
from tools.parameter_catalog import study_input,STUDY_GRANTS
from tools.research_execution import prepare_execution_request,invoke

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'evidence/research_native_development_v3_20261007/store/artifacts/3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b.json'


def interface_proposal(mode, *, expanded=False):
    """Inactive proposal, including collection and independent principal reads."""
    from tools.platform_store import zero
    count=3 if mode=='direct' else 4
    tools={t:'1.0.0' for t in ('research.investigate','research.investigation_status','research.investigation_read','research.investigation_disposition')}
    timeout=600. if expanded else 180.
    return dict(tool_bindings=tools,node_budget={**zero(),'model_calls':6,'tool_calls':8,'wall_s':timeout},
        total_node_budget={**zero(),'model_calls':6*count,'tool_calls':8*count,'wall_s':timeout*count},
        project_budget={**zero(),'model_calls':6*count,'tool_calls':512,'wall_s':(4800. if mode=='direct' else 6400.) if expanded else (2400. if mode=='direct' else 3200.)},
        operation_allowances={t:dict(reserve_s=5.,timeout_s=30.) for t in tools},
        node_count=count,concurrency=2,node_timeout_s=timeout,output_bytes=65536 if expanded else 16384,provider_retries=0,
        discovery_accounting='Up to five query/response turns then report per node; catalog pages, original reads and returned reports share eight evidence operations. Larger directories require a separately budgeted narrowed scope, not silent truncation.',
        status='proposal_only_separate_operator_grant_required')


def configuration(grants=None):
    source=deepcopy(read(SOURCE)['effective'])
    source['policy']['controller']['version']='9.0.0'  # Explicit new envelope, not historical evidence.
    grants=deepcopy(STUDY_GRANTS if grants is None else grants)
    for c in ('near','far'):grants['design/'+c+'_routing_radius_scale']=dict(bounds=[.98,1.02])
    return study_input(source,grants,builder_version='1.2.0')


def fixed_pipeline(host, *, changes, protocol, target, execute_backend=False, executor=None):
    """All computations go through Host; injected executor is a labelled fixture."""
    call=executor or (lambda tool,args,key: invoke(host,tool,args,request_id=key))
    rows=[]
    def step(tool,args,key):
        receipt=call(tool,args,key);rows.append(receipt)
        if receipt.get('execution_status')!='completed':raise ValueError('FIXED_PIPELINE_COMPONENT_INCOMPLETE: '+key)
        return receipt
    built=step('research.prepare_candidate',dict(candidate_id='fixed-radius',changes=changes),'fixed-build')
    prepared=host.store.artifact(built['output'])
    linear=step('analysis.linearize_configuration',dict(configuration=prepared['configuration'],
        expected_content_identity=prepared['content_identity'],protocol=protocol),'fixed-linear')
    step('analysis.control_metrics',dict(models=[linear['output']],protocol=protocol,implementation='scipy'),'fixed-metrics')
    step('analysis.bounded_endpoint',dict(models=[linear['output']],protocol=protocol,target=target),'fixed-endpoint')
    if execute_backend:
        simulation=step('simulation.run',dict(candidate_id='fixed-radius',changes=changes),'fixed-simulation')
        step('evaluation.run',dict(result=simulation['output'],execution_id=simulation['execution_id']),'fixed-evaluation')
        step('control.profile_report',dict(simulation_request_id='fixed-simulation',evaluation_request_id='fixed-evaluation'),'fixed-profile')
    return dict(mode='isolated_execution_substitutes' if executor else 'actual_host_execution',receipts=rows,
        scientific_validation='pending' if executor or not execute_backend else 'Read official evaluation/profile; no inferred success')


def main():
    parser=argparse.ArgumentParser()
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare',type=Path)
    action.add_argument('--execute-grant',type=Path)
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--mode',choices=['fixed','direct','coordinated'],default='fixed')
    args=parser.parse_args()
    cfg=configuration();changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99}
    result=prepare_execution_request(cfg,changes,candidate_id='future-radius-validation')
    if args.prepare:
        atomic_json(args.prepare,dict(configuration=cfg,prepared=result,changes=changes,
            status='prepared_only_no_execution_grant',future_pipeline='tools.research_mainline3.fixed_pipeline',
            budgets_proposed_only=dict(model_calls=0,mathematical_computations=3,backend_solves=1,correction_allowance=0),
            interface_proposals={mode:interface_proposal(mode) for mode in ('direct','coordinated')},
            pending=['candidate analysis working-point solves','warm trajectory regeneration','controller/backend execution']))
        return
    if args.directory is None:parser.error('--execute-grant requires a new --directory')
    from schemas.platform import ProjectConfig
    from tools.platform_host import Host
    from tools.platform_store import Store
    grant=ProjectConfig.model_validate(read(args.execute_grant))
    if args.mode=='fixed' and (grant.budget.backend_solves!=1 or grant.budget.model_calls!=0 or grant.budget.tool_calls<7):
        raise ValueError('FIXED_VALIDATION_REQUIRES_SEPARATE_ONE_BACKEND_ZERO_PROVIDER_GRANT_AND_SEVEN_TOOLS')
    proposal=interface_proposal(args.mode) if args.mode!='fixed' else None
    if proposal and (any(plain(grant.budget)[k]<v for k,v in proposal['project_budget'].items()) or grant.budget.backend_solves or grant.budget.worker_calls):
        raise ValueError('INTERFACE_TEST_REQUIRES_SEPARATE_INTERACTIVE_MODEL_AND_COLLECTION_BUDGET_ZERO_SCIENTIFIC_EXECUTIONS')
    cfg['run_id']='mainline3-'+args.mode
    if args.mode=='fixed':
        tools={'research.prepare_candidate':'1.0.0','analysis.linearize_configuration':'1.0.0',
            'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
            'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0'}
    else:
        tools=proposal['tool_bindings']
    cfg['policy'].update(budget=plain(grant.budget),allowed_tools=list(tools),tool_bindings=tools,
        timeout_s=900.,operation_allowances=proposal['operation_allowances'] if proposal else {})
    store=Store(args.directory);store.create(grant)
    host=Host(store.root,cfg['run_id']);host.create(cfg);host.resume()
    if args.mode=='fixed':
        from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
        source=cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
        protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in source['components'] if c['kind']=='flexible_segment'},
            frequency_rad_s=[.1,1.,10.])
        target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],
            position_tolerance_m=cfg['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01)
        with store.transaction() as db:
            protocol_ref=plain(store.put(db,protocol));target_ref=plain(store.put(db,target))
        output=fixed_pipeline(host,changes=changes,protocol=protocol_ref,target=target_ref,execute_backend=True)
    else:output=live_interface_scenario(host,args.mode)
    atomic_json(host.folder/'mainline3_result.json',output)


def direct_validation_plan(source, *, expanded=False, mode='direct'):
    """Frozen direct questions; no prescribed investigator follow-up path."""
    from tools.research_investigations import InvestigationOrder
    proposal=interface_proposal(mode,expanded=expanded)
    def order(key,question,pointer):
        return plain(InvestigationOrder(investigation_id=key,question=question,role='investigator',
            evidence=[source],queries=[dict(reference=source,pointer=pointer)],
            budget=proposal['node_budget'],timeout_s=proposal['node_timeout_s'],output_bytes=proposal['output_bytes'],stop_conditions=[
                'Bounded evidence turns then one report','Historical Stage336 evidence only; no scientific computation',
                'No transport retries, protocol corrections, delegation or new authority']))
    result=dict(questions=[
        order('reach-question','For the historical Stage336 proposal-build execution 494deb38d6374deb8f741e96f2430826, explain which reach and sampled holding/settling judgments the available evidence supports and which remain unknown. The small initial page is not the whole authorized source. Choose relevant further evidence yourself if needed, within budget; report exact sourced facts, counterevidence and limits. Do not attribute this old result to the later promoted candidate or diagnose a dominant cause.', '/terminal_error_m'),
        order('timing-question','For the same historical Stage336 proposal-build execution 494deb38d6374deb8f741e96f2430826, explain what recorded computation time and control period support, and the limits of timing interpretations. The small initial page is not the whole authorized source. Choose relevant further evidence yourself if needed, within budget; report exact sourced facts, counterevidence and unknowns. Do not infer real robot performance or a causal bottleneck.', '/deadline_misses')],
        principal_inspections=[dict(reference=source,pointer=p,limit=100,byte_limit=8192) for p in (
            '/sampled_settling','/mean_complete_update_s','/control_period_s','/execution_id')],
        principal_report_pointer='',principal_budget={**proposal['node_budget'],'tool_calls':4},
        principal_accounting='Four public independent key-source inspections plus at most four node evidence operations: combined principal ceiling eight.',
        source_case='Stage336 saved proposal-build only; later promoted configuration is not execution evidence')
    if expanded:
        result.update(proposal=proposal,principal_inspections=[dict(reference=source,pointer='',limit=100,byte_limit=8192)],
            principal_budget={**proposal['node_budget'],'tool_calls':7},principal_report_bytes=65536,
            principal_accounting='One independent complete original-source page plus at most seven node evidence operations, including report prefetch.')
        for question in result['questions']:
            question['stop_conditions'][-1]='No transport retries, delegation or new authority; only frozen bounded protocol corrections'
    return result


def import_historical_provenance(store,value):
    from tools.platform_store import Store
    historical=Store(ROOT/'runs/stage336_manual_20261001_090616')
    refs={}
    def collect(item):
        if isinstance(item,dict):
            if set(item)=={'artifact_id','media_type'}:refs[item['artifact_id']]=item
            else:
                for child in item.values():collect(child)
        elif isinstance(item,list):
            for child in item:collect(child)
    collect(value)
    originals={key:historical.artifact(ref) for key,ref in refs.items()}
    with store.transaction() as db:
        for key,body in originals.items():
            if plain(store.put(db,body))!=refs[key]:raise ValueError('HISTORICAL_PROVENANCE_IDENTITY_CHANGED')
    return list(refs.values())


def live_interface_scenario(host,mode,*,plan=None):
    """Future engineered interface test; not a physics experiment or acceptance claim."""
    from tools.research_investigations import InvestigationOrder
    from tools.platform_store import zero
    proposal=plan['proposal'] if plan and 'proposal' in plan else interface_proposal(mode)
    audit=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')
    # Preserve referenced provenance in the same Store. Import is preparation,
    # not an investigator inspection or authority to read those bodies. The
    # source grant below remains the single factual-result document.
    preparation_started=time.monotonic()
    imported=import_historical_provenance(host.store,audit['execution']['factual_result'])
    with host.store.transaction() as db:
        host.store.event(db,host.run_id,'historical_provenance_preparation','completed',outputs=[host.store.put(db,dict(
            originals=imported,original_reads=len(imported),elapsed_s=time.monotonic()-preparation_started,
            purpose='Immutable archival references only; bodies not exposed to investigators or principal as observations; no source grant expansion',
            investigation_inspection=False))])
    with host.store.transaction() as db:
        source=plain(host.store.put(db,audit['execution']['factual_result']))
        state=host.store.session(host.run_id,db)['state']
        count=proposal['node_count']
        grant=dict(max_count=count,max_concurrency=2,
            allowed_tools=['evidence.read'],evidence=[source],include_completed_reports=True,
            per_node_budget=proposal['node_budget'],total_budget=proposal['total_node_budget'])
        grant['output_bytes']=proposal['output_bytes']
        # Preserve the wrapper's frozen deadline and role authority, if present.
        old=state.get('role_context',{}).get('investigation_grant',{})
        for field in ('deadline_unix','protocol_correction_limit','protocol_correction_role_limits','protocol_correction_per_node'):
            if field in old:grant[field]=old[field]
        state['role_context']=dict(role='principal',investigation_grant=grant)
        from tools.state_io import digest
        state['investigation_grant_identity']=digest(grant)
        host.store.update_state(db,host.run_id,state)
    def order(key,question,queries,role='investigator',evidence=None):
        return plain(InvestigationOrder(investigation_id=key,question=question,role=role,
            evidence=evidence or [source],queries=queries,budget=proposal['node_budget'],
            timeout_s=proposal['node_timeout_s'],output_bytes=proposal['output_bytes'],stop_conditions=['Bounded evidence turns then one report','No scientific computation','No provider retries']))
    rows=[]
    def returned(receipt):
        if receipt.get('execution_status')!='completed':
            return dict(status=receipt.get('execution_status','incomplete'),reason=receipt.get('error'))
        return host.store.artifact(receipt['output'])
    def collect(receipt):
        result=returned(receipt)
        if result['status'] not in ('pending','running'):return result
        import threading
        node=host.store.session(host.run_id)['state']['investigations'][result['investigation_id']]
        deadline=time.monotonic()+max(0,node['order']['timeout_s']-(time.time()-node['started_unix']))+10.
        for attempt in range(48):
            thread=next((t for t in threading.enumerate() if t.name=='investigation-'+result['investigation_id']),None)
            wait=max(0,min(15.,deadline-time.monotonic()))
            if thread is not None:thread.join(wait)
            elif wait:time.sleep(wait)
            checked=invoke(host,'research.investigation_status',dict(investigation_id=result['investigation_id']),
                request_id='collect-'+result['investigation_id']+'-'+str(attempt))
            rows.append(checked);result=returned(checked)
            if result['status'] not in ('pending','running'):return result
            if time.monotonic()>=deadline:break
        return dict(status='incomplete',reason='Collection limit reached; original reservation retained, no redispatch')
    if mode=='direct':
        questions=plan['questions'] if plan else [order('reach-question','Explain saved reach/settling results and unknowns',
            [dict(reference=source,pointer='/terminal_error_m')]),
            order('timing-question','Explain saved complete-update accounting and its limits',
            [dict(reference=source,pointer='/deadline_misses')])]
    else:
        coordinator=order('temporary-coordinator','Request exactly two distinct subordinate evidence investigations about the saved reach/settling and complete-update accounting questions. Select original sources from the actual directory. Children may read on demand without prefetch. Set parent_id to temporary-coordinator, role investigator, evidence.read only, zero backend/worker calls; respect delegation_budget_limit, timeout_s and output_bytes from this packet. Do not infer causality.',[],role='coordinator')
        receipt=invoke(host,'research.investigate',coordinator,request_id='coordinator');rows.append(receipt)
        result=collect(receipt)
        if result['status']!='completed':return dict(engineered_interface_test=True,status=result['status'],receipts=rows)
        questions=host.store.artifact(result['result'])['children']
        if len(questions)!=2 or len({q['investigation_id'] for q in questions})!=2 or len({q['question'] for q in questions})!=2:
            raise ValueError('ENGINEERED_SCENARIO_REQUIRES_TWO_DISTINCT_QUESTIONS')
    submissions=[]
    for index,question in enumerate(questions):
        if plan and plan.get('collect_existing'):
            receipt=invoke(host,'research.investigation_status',dict(investigation_id=question['investigation_id']),request_id='retained-question-'+str(index))
        else:receipt=invoke(host,'research.investigate',question,request_id='question-'+str(index))
        rows.append(receipt);submissions.append(receipt)
    reports=[]
    failed=[]
    for receipt in submissions:
        result=collect(receipt)
        if result['status']!='completed':failed.append(result)
        else:reports.append(result['result'])
    if failed:return dict(engineered_interface_test=True,status=failed[0]['status'],failures=failed,receipts=rows)
    # Public principal reads happen before its decision; exact receipts and pages
    # are passed into its independently assembled input, separately from child reads.
    source_pointers=('/terminal_error_m','/deadline_misses','/sampled_settling','/task_accepted','/mean_complete_update_s','/control_period_s','/execution_id','/result_type')
    inspections=plan['principal_inspections'] if plan else [dict(reference=source,pointer=p) for p in source_pointers]
    for index,query in enumerate(inspections):
        receipt=invoke(host,'research.investigation_read',query,request_id='principal-inspect-'+str(index));rows.append(receipt)
        if receipt['execution_status']!='completed':return dict(engineered_interface_test=True,status=receipt['execution_status'],receipts=rows)
    queries=[dict(reference=ref,pointer=plan['principal_report_pointer'] if plan else '/facts',
        **(dict(limit=100,byte_limit=plan.get('principal_report_bytes',8192)) if plan else {})) for ref in reports]
    if not plan:queries.extend(dict(reference=source,pointer=p) for p in source_pointers[:4])
    synthesis=order('principal-synthesis','Synthesize the two distinct completed evidence questions. Public principal inspection records and original pages are supplied independently of child reads. Return exactly one explicit structured disposition for each of these investigation IDs: '+', '.join(q['investigation_id'] for q in questions)+'. Bind each report reference. Accept only with adopted_claims, specific supporting report facts, exact inspected scope fields, and support_explanation; semantic reasoning remains unassessed. Defer/reject may have no inspections when evidence is insufficient; state remaining_unknowns. Do not replace decisions with informal prose. No new computation is authorized.',
        queries,role='principal',evidence=[source,*reports])
    if plan:
        synthesis['budget']=plan['principal_budget']
        synthesis['question']+=' Historical applicability is Stage336 proposal-build execution 494deb38d6374deb8f741e96f2430826 only, not the later promoted candidate. Only facts and scope covered by principal_inspection_records qualify for formal adoption; other node reads support analysis but do not substitute independent public inspection. Limit adopted claims accordingly or defer/reject uninspected conclusions. Check factual and interpretive support separately; do not force acceptance. No children or protocol correction requests are authorized.'
    rows.append(invoke(host,'research.investigate',synthesis,request_id='synthesis'))
    result=collect(rows[-1])
    if result['status']!='completed':return dict(engineered_interface_test=True,status=result['status'],receipts=rows)
    decisions=host.store.artifact(result['result'])['dispositions']
    expected={q['investigation_id']:ref for q,ref in zip(questions,reports)}
    if len(decisions)!=2 or {d['investigation_id'] for d in decisions}!=set(expected):
        return dict(engineered_interface_test=True,status='incomplete',reason='Two formal principal decisions required',receipts=rows)
    dispositions=[]
    for decision in decisions:
        if decision['report']!=expected[decision['investigation_id']]:
            return dict(engineered_interface_test=True,status='incomplete',reason='Principal report binding mismatch',receipts=rows)
        receipt=invoke(host,'research.investigation_disposition',decision,request_id='dispose-'+decision['investigation_id']);rows.append(receipt)
        if receipt['execution_status']!='completed':return dict(engineered_interface_test=True,status=receipt['execution_status'],receipts=rows)
        dispositions.append(host.store.artifact(receipt['output'])['disposition_record'])
    return dict(engineered_interface_test=True,status='formal_dispositions_recorded',receipts=rows,dispositions=dispositions,
        meaning='Live interface behavior only; no new physics, performance or causality validation')


if __name__=='__main__':main()
