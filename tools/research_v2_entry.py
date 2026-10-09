"""Mainline 4 starting configuration over the finite public V2 capability pool.

Preparation is solve-free. Execution requires an explicitly supplied new grant;
historical V1/V2 permissions and unused budgets are never transferred.
"""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.research_v2 import configuration,TOOLS
from tools.research_execution import prepare_execution_request,invoke
from tools.state_io import atomic_json,read
from tools.platform_store import Store,plain
from tools.platform_host import Host
from schemas.platform import ProjectConfig


def prepare(template='T1'):
    from tools.parameter_catalog import effective_catalog
    cfg=configuration('mainline4-finite-entry')
    return dict(configuration=cfg,catalog=effective_catalog(cfg),
        prepared=prepare_execution_request(cfg,{'template':template},candidate_id='mainline4-'+template),
        selected_template=template,selection_method='search.family_explicit@1.0.0',
        status='prepared_only_new_Mainline4_execution_authorization_required',
        evidence='evidence/research_mainline3_v2_20261009/completion.json',
        scientific_claim='Finite capability entry; no incumbent promotion or optimization gain')


def main():
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--run-with-grant',type=Path)
    p.add_argument('--template',choices=['T0','T1','T2','T3'],default='T1')
    p.add_argument('--output',type=Path,default=Path('runs/mainline4_finite_entry.json'))
    p.add_argument('--directory',type=Path);args=p.parse_args()
    value=prepare(args.template)
    if args.prepare:
        atomic_json(args.output,value);print(str(args.output.resolve()));return
    if not args.directory:p.error('--directory is required with --run-with-grant')
    from tools.research_mainline3 import fixed_pipeline
    from schemas.platform_analysis import TaskAnalysisProtocol,EndpointTarget
    grant=ProjectConfig.model_validate(read(args.run_with_grant))
    cfg=value['configuration'];cfg['policy']['budget']=plain(grant.budget)
    for tool in ('research.capability_catalog','research.select_template'):
        cfg['policy']['tool_bindings'][tool]='1.0.0'
        cfg['policy']['operation_allowances'][tool]=dict(timeout_s=60.,reserve_s=30.)
    cfg['policy']['allowed_tools']=list(cfg['policy']['tool_bindings'])
    store=Store(args.directory);store.create(grant)
    host=Host(store.root,cfg['run_id']);host.create(cfg);host.resume()
    invoke(host,'research.capability_catalog',{},request_id='mainline4-catalog')
    chosen=invoke(host,'research.select_template',{'template':args.template},request_id='mainline4-select')
    if chosen['execution_status']!='completed':raise ValueError(str(chosen))
    from extensions.tendon_family.finite_templates import catalog
    design=catalog()['templates'][args.template]['design']
    protocol=TaskAnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in design['components'] if c['kind']=='flexible_segment'},frequency_rad_s=[.1,1.,10.])
    target=EndpointTarget(position_m=cfg['task']['goal']['data']['target_m'],position_tolerance_m=.01,position_scale_m=.01)
    with store.transaction() as db:
        protocol_ref=plain(store.put(db,protocol));target_ref=plain(store.put(db,target))
    result=fixed_pipeline(host,changes=store.artifact(chosen['output'])['detail']['changes'],protocol=protocol_ref,target=target_ref,
        execute_backend=True,candidate_id='mainline4-'+args.template,request_prefix='mainline4-'+args.template)
    rows=result['receipts'];built=store.artifact(rows[0]['output'])
    acceptance=invoke(host,'research.task_acceptance',dict(configuration=built['configuration'],evaluation=rows[5]['output'],profile=rows[6]['output']),
        request_id='mainline4-'+args.template+'-acceptance')
    result['acceptance_receipt']=acceptance
    if acceptance['execution_status']=='completed':result['joint_acceptance']=store.artifact(acceptance['output'])['detail']
    atomic_json(args.output,result)


if __name__=='__main__':main()
