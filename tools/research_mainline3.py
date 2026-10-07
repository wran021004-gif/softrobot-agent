"""Small independent fixed workflow; default only constructs a future request."""
from copy import deepcopy
from pathlib import Path
import argparse
from tools.state_io import read,atomic_json
from tools.platform_store import plain
from tools.parameter_catalog import study_input,STUDY_GRANTS
from tools.research_execution import prepare_execution_request,invoke

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'evidence/research_native_development_v3_20261007/store/artifacts/3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b.json'


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
            pending=['candidate analysis working-point solves','warm trajectory regeneration','controller/backend execution']))
        return
    if args.directory is None:parser.error('--execute-grant requires a new --directory')
    from schemas.platform import ProjectConfig
    from tools.platform_host import Host
    from tools.platform_store import Store
    grant=ProjectConfig.model_validate(read(args.execute_grant))
    if args.mode=='fixed' and (grant.budget.backend_solves!=1 or grant.budget.model_calls!=0 or grant.budget.tool_calls<7):
        raise ValueError('FIXED_VALIDATION_REQUIRES_SEPARATE_ONE_BACKEND_ZERO_PROVIDER_GRANT_AND_SEVEN_TOOLS')
    needed=3 if args.mode=='direct' else 4
    if args.mode!='fixed' and (grant.budget.model_calls<needed or grant.budget.backend_solves):
        raise ValueError('INTERFACE_TEST_REQUIRES_SEPARATE_MODEL_BUDGET_ZERO_BACKENDS')
    cfg['run_id']='mainline3-'+args.mode
    if args.mode=='fixed':
        tools={'research.prepare_candidate':'1.0.0','analysis.linearize_configuration':'1.0.0',
            'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
            'simulation.run':'1.0.0','evaluation.run':'1.0.0','control.profile_report':'1.0.0'}
    else:
        tools={t:'1.0.0' for t in ('research.investigate','research.investigation_read','research.investigation_disposition')}
    cfg['policy'].update(budget=plain(grant.budget),allowed_tools=list(tools),tool_bindings=tools,
        timeout_s=900.,operation_allowances={})
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


def live_interface_scenario(host,mode):
    """Future engineered interface test; not a physics experiment or acceptance claim."""
    from tools.research_investigations import InvestigationOrder
    from tools.platform_store import zero
    audit=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')
    with host.store.transaction() as db:
        source=plain(host.store.put(db,audit['execution']['factual_result']))
        state=host.store.session(host.run_id,db)['state']
        count=3 if mode=='direct' else 4
        state['role_context']=dict(investigation_grant=dict(max_count=count,max_concurrency=2,
            allowed_tools=['evidence.read'],evidence=[source],include_completed_reports=True,
            per_node_budget={**zero(),'model_calls':1,'wall_s':180.},
            total_budget={**zero(),'model_calls':count,'wall_s':180.*count}))
        host.store.update_state(db,host.run_id,state)
    def order(key,question,queries,role='investigator',evidence=None):
        return plain(InvestigationOrder(investigation_id=key,question=question,role=role,
            evidence=evidence or [source],queries=queries,budget={**zero(),'model_calls':1,'wall_s':180.},
            timeout_s=180.,stop_conditions=['One bounded return','No scientific computation','No provider retries']))
    rows=[]
    def returned(receipt):
        if receipt.get('execution_status')!='completed':
            return dict(status=receipt.get('execution_status','incomplete'),reason=receipt.get('error'))
        return host.store.artifact(receipt['output'])
    if mode=='direct':
        questions=[order('reach-question','Explain saved reach/settling results and unknowns',
            [dict(reference=source,pointer=p) for p in ('/terminal_error_m','/task_accepted','/sampled_settling')]),
            order('timing-question','Explain saved complete-update accounting and its limits',
            [dict(reference=source,pointer=p) for p in ('/deadline_misses','/mean_complete_update_s','/control_period_s')])]
    else:
        coordinator=order('temporary-coordinator','Request exactly two distinct subordinate evidence investigations: reach/settling and complete-update accounting. Set each child parent_id to temporary-coordinator; same source evidence, evidence.read only, one model call, zero backend/worker/tool calls, wall_s=180, timeout_s=180. Do not infer causality.',[],role='coordinator')
        receipt=invoke(host,'research.investigate',coordinator,request_id='coordinator');rows.append(receipt)
        result=returned(receipt)
        if result['status']!='completed':return dict(engineered_interface_test=True,status=result['status'],receipts=rows)
        questions=host.store.artifact(result['result'])['children']
        if len(questions)!=2:raise ValueError('ENGINEERED_SCENARIO_REQUIRES_TWO_DISTINCT_QUESTIONS')
    for index,question in enumerate(questions):
        rows.append(invoke(host,'research.investigate',question,request_id='question-'+str(index)))
    reports=[]
    for receipt in rows:
        result=returned(receipt)
        if result['status']!='completed':return dict(engineered_interface_test=True,status=result['status'],receipts=rows)
        reports.append(result['result'])
    queries=[dict(reference=ref,pointer=p) for ref in reports[-2:] for p in ('/facts','/interpretation')]
    queries.extend(dict(reference=source,pointer=p) for p in ('/terminal_error_m','/deadline_misses','/sampled_settling','/task_accepted'))
    synthesis=order('principal-synthesis','Synthesize the two distinct evidence questions. Inspect the prefetched original source facts independently of the child reports. Separate checked facts, counterevidence and unknowns. Explain whether suggested checks should be accepted, deferred or rejected; no new computation is authorized by recommendations.',
        queries,role='principal',evidence=[source,*reports])
    rows.append(invoke(host,'research.investigate',synthesis,request_id='synthesis'))
    result=returned(rows[-1])
    if result['status']!='completed':return dict(engineered_interface_test=True,status=result['status'],receipts=rows)
    return dict(engineered_interface_test=True,status='interface_returns_recorded',receipts=rows,
        meaning='Live interface behavior only; no new physics, performance or causality validation')


if __name__=='__main__':main()
