"""One authorized SOCP Study; zero Provider/physics/NMPC/PPO, no retry grant."""
import argparse
from copy import deepcopy
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from tools.state_io import read,atomic_json,digest
from tools.research.config import ROOT
from tools.research import core,analysis,reporter
from tools.research.state import state,guard
from tools.research.optimal_capability import CONIC
from tools.platform_host import Host
from tools.platform_store import plain

STUDY='f3-preflight-socp-20261022-01'
OUTPUT=ROOT/'evidence/f3_prestudy'


def plan(action,**fields):
    return dict(action=action,hypothesis='Engineering-only SOCP evidence/control handoff validation',
        expected_observation='One bounded real mathematical result; no task acceptance',
        weakening_observation='Admission, solver, replay or binding failure',
        fixed_conditions='Frozen task, FamilySpace, implementation and two-evaluation ceiling',
        stopping_condition='Exactly one SOCP request, then deterministic evidence audit',
        interpretation='Local mathematics only; no autonomous-science or physical success claim',**fields)


def audit(host):
    s=state(host);refs=s.get('analysis_results',[])
    raw=host.store.artifact(refs[0]) if refs else {}
    trajectory=raw.get('trajectory',{})
    receipt=host.store.lookup(host.run_id,'f3-single-socp-analysis')
    result=dict(study_id=host.run_id,implementation=s['freeze'],result_reference=refs[0] if refs else None,
        status=raw.get('status','no_result'),task_acceptance=raw.get('task_acceptance','unmeasured'),
        solver=trajectory.get('solver'),versions=trajectory.get('versions'),
        optimality_status=trajectory.get('optimality_status'),replayed_violation=trajectory.get('replayed_violation'),
        replay={k:trajectory.get('replay',{}).get(k) for k in ('passed','finite','numerically_valid','max_prediction_replay_error')},
        gap=trajectory.get('dual_checks',{}).get('replayed_support_gap'),
        reserved_evaluations=raw.get('method_admission',{}).get('expected_mathematical_evaluations'),
        charged_evaluations=s.get('mathematical_evaluations',0),charged_numerical_s=raw.get('charged_numerical_s'),
        actual_calls=raw.get('actual_mathematical_calls'),attempt_boundaries=raw.get('recorded_attempt_boundaries'),
        worker_runtime=raw.get('worker_runtime'),receipt=json.loads(receipt['receipt']) if receipt and receipt['receipt'] else None,
        ledger=host.store.remaining(),pending=s.get('pending'),failure=raw.get('reason') or raw.get('error'),
        control_initializations=s.get('control_initializations',[]),
        scientific_scope='Local sampled affine model, floating numerical checks; no physical experiment or autonomous Provider decision.',
        formal_f3_started=False,historical_semantic_admission='failed_semantic_admission')
    atomic_json(OUTPUT/'real_socp_audit.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    directory=ROOT/'runs/research'/STUDY
    if args.audit_only:
        print(json.dumps(audit(Host(directory,STUDY,actor='unified-research')),indent=2));return
    if directory.exists():raise ValueError('SINGLE_ATTEMPT_STUDY_ALREADY_EXISTS: use --audit-only; no new request')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('CLEAN_COMMITTED_IMPLEMENTATION_REQUIRED')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    runtime=read(ROOT/'configs/research/runtime.json');runtime['research_python']=sys.executable
    for key,value in runtime['threads'].items():os.environ[key]=value
    runtime_path=ROOT/'runs/f3-preflight-runtime.json';atomic_json(runtime_path,runtime)
    environment=dict(python=sys.executable,version=sys.version,implementation=commit,threads=runtime['threads'],
        packages={k:importlib.metadata.version(k) for k in ('strands-agents','strands-harness','pydantic','numpy','scipy','casadi','cvxpy','clarabel')},
        dependency_lock_identity=digest((ROOT/'requirements-s130-t3.txt').read_text()),
        mainline_lock_identity=digest((ROOT/'requirements-strands-mainline5.lock').read_text()),
        matlab_engine='Bundled R2024a build/lib imported through isolated-environment .pth; no engine started',
        sorosim='Existing repository integration; engine/gateway numerical execution not exercised by this GVS request')
    import cvxpy
    environment['installed_solvers']=cvxpy.installed_solvers()
    if 'CLARABEL' not in environment['installed_solvers']:raise ValueError('CLARABEL_REQUIRED_BEFORE_SINGLE_REQUEST')
    raw=read(ROOT/'configs/research/study_variable_segments_dev.json')
    raw.update(study_id=STUDY,base_commit=commit,runtime=str(runtime_path),
        authorization='User F3-Preflight attachment: one independent real SOCP request, reserve at most 2 mathematical evaluations; zero Provider and physical launches.',
        mathematical_methods={CONIC:'User explicitly authorized one SOCP engineering request'},
        capabilities=['analysis','control_correction'],allowed_plan_actions=['generate','initialize_control','stop'],
        evidence_destination='evidence/f3_prestudy',execution_instructions='One real SOCP engineering request only; no Provider, NMPC, PPO or physical execution.')
    raw['budgets'].update(mathematical_evaluations=2,provider_requests=0,physical_launches=0)
    path=ROOT/'configs/research/._f3_math_preflight.json';atomic_json(path,raw)
    try:host=core.prepare(path,directory)
    finally:path.unlink()
    core.bind(host)
    s=state(host)
    assert Path(s['spec']['runtime']['research_python']).resolve()==Path(sys.executable).resolve()
    generated=core.dispatch(host,plan('generate',generation=dict(version='serial_family_generation_v2',
        family_space_identity=s['spec']['family_space_identity'],segment_count=2,tendon_count=3)), 'f3-generate')['result']
    if generated['status']!='generated':raise ValueError(generated)
    query=dict(candidate=generated['candidate'],operation='task_capability',operating_point='controller_start_input',
        protocol=s['spec']['analysis_protocol'],capability_method=CONIC)
    atomic_json(OUTPUT/'environment.json',environment)
    atomic_json(OUTPUT/'engineering_scope.json',dict(study_id=STUDY,resolved_identity=s['spec']['resolved_identity'],
        task_identity=s['spec']['canonical_task_identity'],family_space_identity=s['spec']['family_space_identity'],
        implementation=commit,budgets=s['spec']['budgets'],nmpc_limits=s['spec']['nmpc_limits'],rl_limits=s['spec']['rl_limits'],
        authorization=raw['authorization'],query=query))
    try:
        result=analysis.dispatch(host,query,'f3-single-socp',guard=guard,origin='engineering_preflight')
        if not result.get('reference'):raise ValueError(result)
        reference=result['reference'];saved=host.store.artifact(reference)
        again=analysis.dispatch(host,query,'f3-single-socp',guard=guard,origin='engineering_preflight')
        assert again['operation_reuse']['additional_analysis_evaluations']==0
        report=reporter.assemble(host,[reference]);report_ref=reporter._save(host,report,status='deterministic_only')
        from tools.research.research_context import agent_decision_brief
        l0=agent_decision_brief(host)
        from tools.research.core import read_evidence
        for quantity in plain(report)['results'][0].get('mathematics',{}).get('quantities',[]):
            if quantity.get('source'):assert read_evidence(host,quantity['source'],record_read=False)==quantity['value']
        atomic_json(OUTPUT/'real_socp_result.json',saved)
        atomic_json(OUTPUT/'deterministic_delivery.json',dict(report_reference=report_ref,report=plain(report),L0=l0,
            operation_reuse=again['operation_reuse'],provider_requests=0))
        if saved.get('trajectory',{}).get('replay',{}).get('numerically_valid'):
            converted=core.dispatch(host,plan('initialize_control',control_seed=dict(candidate=generated['candidate'],
                method='capability_sequence',response_evidence=reference)), 'f3-control-source')
            atomic_json(OUTPUT/'control_handoff.json',dict(result=converted,
                source=host.store.artifact(converted['result']['source']),physical_execution=False))
        # Preserve complete current-study raw artifact references for exact offline reads.
        with host.store.connect(True) as db:
            artifacts={r['id']:json.loads(r['body']) for r in db.execute("SELECT id,body FROM artifacts WHERE media='application/json'")}
        atomic_json(OUTPUT/'artifacts.json',artifacts)
    finally:audit(host)


if __name__=='__main__':main()
