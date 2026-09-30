"""Freeze, run, and audit one math-led DeepSeek/Route reach experiment."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ.setdefault(name,'1')

from examples.gvs_nmpc_route_experiment import inspect as standard_inspect, load_credential
from extensions.tendon_family.route import create
from schemas.platform_analysis import EndpointTarget, TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import atomic_json, digest, read


SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923')
VERSIONS={
    'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0',
    'analysis.linearize_candidate':'1.0.0','analysis.control_metrics':'2.0.0',
    'analysis.bounded_endpoint':'1.0.0','design.screen':'1.0.0','design.optimize_math':'1.0.0',
    'analysis.compare_candidates':'1.0.0','analysis.gvs_candidate_evaluate':'1.0.0',
    'control.profile_describe':'1.0.0','control.profile_report':'1.0.0',
    'diagnostics.saved_trajectory':'2.0.0','evaluation.run':'1.0.0','evidence.read':'1.0.0',
    'session.control':'1.0.0','simulation.run':'1.0.0',
}


def historical_sources():
    sources=read(SOURCE/'historical_sources.json')
    sources.append(dict(directory=str(SOURCE),source_session_id='gvs-live-f4a6655fe472',
        candidate_ids=['b1_near0p17_far0p128_compliant_s1p05','b2_near0p169_far0p129_compliant_s1p05'],
        records='actual_fresh_candidates.json',live_store='live',ledger='platform.sqlite.gz',
        frozen_input='resolved_frozen_input.json',backend_evidence='backend_evidence.zip',
        allow_ledger_record_reconstruction=True))
    return sources


def prepare(root):
    if (root/'workflow.json').is_file(): return Host(root,read(root/'workflow.json')['run_id'])
    root.mkdir(parents=True,exist_ok=False)
    inp=deepcopy(read(SOURCE/'resolved_frozen_input.json'));run_id='gvs-stage334-'+uuid4().hex[:12];inp['run_id']=run_id
    budget=dict(model_calls=24,tool_calls=160,backend_solves=3,worker_calls=0,wall_s=7200.)
    inp['policy'].update(budget=budget,timeout_s=1800.,allowed_tools=[],tool_bindings=VERSIONS)
    inp['policy']['model']['max_turns']=24
    store=Store(root);store.create(dict(project_id=run_id,grant_id=run_id,
        authorization_source='User-authorized Stage 3.34 one bounded real math-led DeepSeek design-and-validation experiment.',
        budget=budget))
    task=inp['task'];controller=inp['policy']['controller']['parameters']['data']
    lengths={row['id']:row['length_m'] for row in inp['robot']['structure']['data']['components'] if 'length_m' in row}
    protocol=TaskAnalysisProtocol(baseline_lengths_m=lengths,duration_s=task['timing']['duration_s'],
        period_s=task['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.,100.,1000.],samples_s=[])
    target=EndpointTarget(position_m=tuple(task['goal']['data']['target_m']),
        position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
        tip_speed_limit_m_s=controller['settling']['speed_limit_m_s'],
        tip_velocity_scale_m_s=controller['settling']['speed_limit_m_s'])
    with store.transaction() as db: pref=plain(store.put(db,protocol));tref=plain(store.put(db,target))
    from extensions.tendon_family.historical_failure import bind_sources
    sources=historical_sources();prior=bind_sources(sources,inp,store)
    with store.transaction() as db: href=plain(store.put(db,prior))
    novelty=dict(rule_id='stage334-math-led-novelty-v1',declared_before_launch=True,
        prohibited=['unchanged baseline','any exact one of the nine bound historical evaluated configurations'],
        required=['first executed candidate is a changed compliant or stiff design matching an exact design.optimize_math proposal',
            'candidate-bound shared screen and Route report precede execution'],
        comparison='Exact declared near length, far length, material scenario and common section scale.',
        stop='Stop further physical search when a qualifying changed candidate passes official reach, or at budget/stop policy.')
    guidance=(
        'Conduct one bounded math-led design experiment on the frozen reach task. First create an analysis seed build; the unchanged baseline may be built only as a solve-free mathematical starting configuration and must never be executed. '
        'Invoke analysis.linearize_candidate, analysis.control_metrics, analysis.bounded_endpoint and design.screen on an owned completed build. Invoke design.optimize_math with exactly the authorized near-length [0.15,0.17] m, far-length [0.11,0.13] m and section-scale [0.95,1.05] bounds, both compliant and stiff scenarios, the configured protocol/target, and at most 16 evaluations. '
        'Read its structured objectives, ties, applicability and limits. Select one exact optimizer proposal yourself, explain the cited mathematical values as a local proxy rather than a success prediction, and build those exact near/far/scale/material values as a changed candidate. Do not replay any of the nine historical evaluated configurations, including the known historical passing candidate. '
        'Obtain that changed build\'s candidate-bound shared analysis and screen, run design.optimize_math rooted at it so its exact design is a returned proposal, then call route.record_analysis with the exact evidence and disposition before route.advance run. The Route enforces proposal matching and report linkage. '
        'Decide whether to spend a backend attempt from the advisory report. Read actual evaluation and control.profile_report evidence after every execution; compare candidates when useful. At most three backend attempts include failures/retries. Stop further physical search immediately after a qualifying changed reach pass and finish it; otherwise revise only from actual evidence while budget remains. '
        'Separate mathematical correctness, local applicability, official endpoint reach, sampled 0.05 s settling, complete-update real-time feasibility, and factual delivery. A reach pass does not prove settling, real time, causality, or global optimality. Use English and retain exact candidate/evidence identities. On finish copy candidate_facts into design_statement and factual_result into result_statement exactly.')
    inp['policy']['route']['data'].update(source='Stage 3.34 frozen math-led experiment; implementation commit '+subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        historical_case=href,max_trials=3,analysis_protocol=pref,endpoint_target=tref,
        analysis_required_before_run=True,math_evaluation_limit=16,math_selection_required_before_run=True,
        stop_on_task_success=True,guidance=guidance)
    create(root,inp);host=Host(root,run_id)
    atomic_json(root/'frozen_input.json',inp);atomic_json(root/'analysis_protocol.json',plain(protocol));atomic_json(root/'endpoint_target.json',plain(target))
    atomic_json(root/'historical_sources.json',sources);atomic_json(root/'historical_case.json',dict(reference=href,bindings=prior['cases']))
    atomic_json(root/'novelty_rule.json',novelty)
    context=host.context()
    from tools.platform_models import payload_for,DeepSeekAdapter
    payload=payload_for(host,DeepSeekAdapter())
    workflow=dict(run_id=run_id,implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        implementation_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
        input_identity=digest(inp),protocol=pref,target=tref,historical_case=href,novelty=novelty,
        limits=budget,math_evaluations_pre_live=8,math_evaluations_live_limit=16,
        provider_configuration=inp['policy']['model'],initial_context_bytes=len(json.dumps(payload).encode()),status='prepared')
    atomic_json(root/'workflow.json',workflow);atomic_json(root/'prepared_context.json',context)
    print('Prepared '+run_id+' from '+workflow['implementation_commit']+'; no provider/backend calls.',flush=True)
    return host


def math_audit(host):
    route=host.store.session(host.run_id)['state']['route'];nodes=route['nodes'];analysis=[];executions=[];optimizers=[]
    for node in nodes:
        if node.get('status')!='completed' or not node.get('result'): continue
        out=host.store.artifact(node['result'])
        if node['action']=='analyze':
            analysis.append(dict(node_id=node['node_id'],source_node=out['source_node'],screen=out['screen'],
                math_optimization=out.get('math_optimization'),selection_trace=out.get('math_selection_trace'),
                disposition=out['validation_disposition'],reason=out['disposition_reason']))
            if out.get('math_optimization'):
                optimized=host.store.artifact(out['math_optimization']);optimizers.append(dict(reference=out['math_optimization'],
                    evaluations=len(optimized['evaluations']),proposals=optimized['proposals'],objective=optimized['objective'],
                    provenance=optimized['provenance']))
        if node['action']=='run':
            build=next(item for item in nodes if item['node_id']==node['selection']['source_node'])
            linked=next((row for row in analysis if row['source_node']==build['node_id'] and row['selection_trace']['matches_proposal']),None)
            executions.append(dict(node_id=node['node_id'],build_node=build['node_id'],candidate_id=out['candidate_id'],
                configuration=out['build_configuration'],build_reason=build['selection']['reason'],analysis=linked,
                factual_result=out.get('factual_result'),evaluation=out['evaluation'],profile_report=out.get('profile_report')))
    used=host.store.remaining()['used'];final=route.get('final')
    audit=dict(run_id=host.run_id,optimizer_calls=optimizers,executions=executions,
        qualifying_math_led_execution=any(row['analysis'] is not None for row in executions),
        provider_authored_finish=bool(final and final.get('explicit_delivery')),
        final_candidate_id=None if not final else final.get('candidate_id'),usage=used,
        within_limits=used['model_calls']<=24 and used['tool_calls']<=160 and used['backend_solves']<=3 and used['worker_calls']==0 and used['wall_s']<=7200)
    atomic_json(host.store.root/'math_influence_audit.json',audit);return audit


def inspect(host):
    standard=standard_inspect(host);audit=math_audit(host)
    workflow=read(host.store.root/'workflow.json');workflow['status']=standard['status'];workflow['final_audit']=audit
    atomic_json(host.store.root/'workflow.json',workflow)
    print(json.dumps(dict(math_led=audit['qualifying_math_led_execution'],usage=audit['usage'],
        final_candidate=audit['final_candidate_id']),indent=2),flush=True)
    return standard,audit


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','run','inspect'])
    parser.add_argument('--output',type=Path,default=Path('runs')/('stage334_math_led_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    parser.add_argument('--credential-file',type=Path,default=Path.home()/'.codex/.env');args=parser.parse_args()
    root=args.output.resolve();host=prepare(root) if args.action in ('prepare','run') else Host(root,read(root/'workflow.json')['run_id'])
    if args.action=='run':
        load_credential(args.credential_file);print('Starting bounded real math-led Route.',flush=True);host.run();inspect(host)
    elif args.action=='inspect': inspect(host)


if __name__=='__main__': main()
