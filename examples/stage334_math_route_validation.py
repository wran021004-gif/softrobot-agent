"""One deterministic build -> shared analysis -> math optimization -> Route report workflow."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from extensions.tendon_family.route import create as create_route
from schemas.platform import ToolRequest
from schemas.platform_analysis import EndpointTarget, TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import atomic_json


VERSIONS={
    'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0','analysis.linearize_candidate':'1.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
    'design.screen':'1.0.0','design.optimize_math':'1.0.0','evidence.read':'1.0.0',
}


def save(store,value):
    with store.transaction() as db: return plain(store.put(db,value))


def call(host,receipts,tool,arguments,reason):
    receipt=plain(host.invoke(plain(ToolRequest(request_id='stage334-'+uuid4().hex,tool_id=tool,
        tool_version=VERSIONS[tool],arguments=arguments,reason=reason,cache='new'))))
    receipts.append(receipt)
    if receipt['execution_status']!='completed': raise RuntimeError(json.dumps(receipt,indent=2))
    return receipt['output'],host.store.artifact(receipt['output'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();root=args.output or Path('runs')/('stage334_math_route_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    root.mkdir(parents=True,exist_ok=False)
    source=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923/resolved_frozen_input.json')
    frozen=json.loads(source.read_text(encoding='utf8')); budget=dict(tool_calls=80,model_calls=0,backend_solves=0,worker_calls=0,wall_s=7200.)
    store=Store(root/'analysis');store.create(dict(project_id='stage334-math-route',grant_id='stage334-'+uuid4().hex,
        authorization_source='Deterministic mathematics-only Route verification; no provider or physical backend.',
        budget=budget,exclusive_resources={'matlab':1}))
    lengths={row['id']:row['length_m'] for row in frozen['robot']['structure']['data']['components'] if 'length_m' in row}
    task=frozen['task']; control=frozen['policy']['controller']['parameters']['data']
    protocol=TaskAnalysisProtocol(baseline_lengths_m=lengths,duration_s=task['timing']['duration_s'],
        period_s=task['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.,100.,1000.],samples_s=[])
    target=EndpointTarget(position_m=tuple(task['goal']['data']['target_m']),
        position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
        tip_speed_limit_m_s=control['settling']['speed_limit_m_s'],tip_velocity_scale_m_s=control['settling']['speed_limit_m_s'])
    pref,tref=save(store,protocol),save(store,target)
    value=json.loads(json.dumps(frozen));value['run_id']='stage334-deterministic-math-route'
    value['policy'].update(budget=budget,timeout_s=1800.,model={},allowed_tools=[],tool_bindings=VERSIONS)
    value['policy']['route']['data'].update(analysis_protocol=pref,endpoint_target=tref,analysis_required_before_run=True,
        math_evaluation_limit=8,max_trials=3,guidance='Build, invoke the configured shared analysis and mathematical optimizer, attach their exact report, and do not execute a backend in this deterministic validation.')
    value['policy']['route']['data']['historical_case']=None
    create_route(store.root,value);host=Host(store.root,value['run_id'],actor='deterministic-validation');receipts=[]
    build_ref,_=call(host,receipts,'route.advance',dict(node_id='math_start',action='build',combination='candidate_gvs_nmpc',
        candidate_id='math-start',changes={},variables={},max_trials=1,evidence=[],reason='Create the explicit immutable optimizer start.',
        next_step='Run candidate-bound shared mathematics.'),'Deterministic Route build; zero backend solves.')
    build_node_ref=store.session(host.run_id)['state']['route']['nodes'][0]['result']
    linear_ref,linear=call(host,receipts,'analysis.linearize_candidate',dict(source_node='math_start',protocol=pref),
        'Bind configuration-only local models to the exact completed build.')
    models=[row['model'] for row in linear['records'] if 'model' in row]
    metrics_ref,_=call(host,receipts,'analysis.control_metrics',dict(models=models,protocol=pref,implementation='scipy'),
        'Compute shared local metrics without physical execution.')
    endpoint_ref,_=call(host,receipts,'analysis.bounded_endpoint',dict(models=models,protocol=pref,target=tref),
        'Check task-time local endpoint witnesses and certificates.')
    screen_ref,_=call(host,receipts,'design.screen',dict(source_node='math_start',protocol=pref,
        linearization=linear_ref,metrics=metrics_ref,endpoint=endpoint_ref),'Create the shared advisory report.')
    variables={'components/near/length_m':(.15,.17),'components/far/length_m':(.11,.13),'design/section_scale':(.95,1.05)}
    optimize_ref,optimized=call(host,receipts,'design.optimize_math',dict(source_node='math_start',protocol=pref,target=tref,
        variables=variables,material_scenarios=['compliant','stiff'],max_evaluations=8,
        objective='controller_start_local_endpoint_lexicographic_v1'),
        'Run the declared bounded mathematics-only coordinate search; no provider, NMPC, or backend.')
    report_ref,report=call(host,receipts,'route.record_analysis',dict(node_id='math_report',source_node='math_start',evidence=[build_node_ref,optimize_ref],
        linearization=linear_ref,metrics=metrics_ref,endpoint=endpoint_ref,screen=screen_ref,
        math_optimization=optimize_ref,validation_disposition='recommended',
        reason='Shared local evidence supplies conditional candidate proposals; backend validation would be required to test closed-loop reach.',
        next_step='Deterministic validation stops before physical execution.'),'Attach the exact shared report and optimizer provenance to Route.')
    _,overview=call(host,receipts,'route.inspect',{},'Verify the Route context exposes the shared report workflow.')
    usage=store.remaining(host.run_id)
    verification=dict(all_calls_completed=all(row['execution_status']=='completed' for row in receipts),
        no_provider_backend_or_worker=all(usage['used'][key]==0 for key in ('model_calls','backend_solves','worker_calls')),
        optimizer_evaluations=len(optimized['evaluations']),optimizer_within_budget=len(optimized['evaluations'])<=8,
        route_report_links_optimizer=report['detail']['summary']['math_optimization']==optimize_ref,
        route_report_links_screen=report['detail']['summary']['analysis_report']==screen_ref,
        route_context_configured=overview['detail']['analysis_workflow']['required_before_run'])
    verification['passed']=all(value if isinstance(value,bool) else True for value in verification.values())
    for name,data in (('protocol',plain(protocol)),('target',plain(target)),('linearization',linear),
            ('optimizer',optimized),('route_report',report),('route_overview',overview),('receipts',receipts),
            ('usage',usage),('verification',verification)):
        atomic_json(root/(name+'.json'),data)
    if not verification['passed']: raise RuntimeError(json.dumps(verification,indent=2))
    print('Completed: '+str(root),flush=True)


if __name__=='__main__': main()
