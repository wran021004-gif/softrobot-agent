"""Fresh-process public reproduction; no experiment imports or private caches.

prepare creates a session and predeclares the strategy without a numerical solve.
run resumes that prepared session, or prepares a new one, then executes once.
inspect creates a new read-only session and demonstrates normal skill retrieval.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(name,'1')
from extensions.tendon_family.gvs_profile import profile_input, execution_scope
from extensions.tendon_family.gvs_reporting import markdown
from tools.platform_host import Host
from tools.platform_store import Store, now
from tools.state_io import atomic_json
from tools.skill_policy import REQUIRED_CONSTRAINTS, strategy_hash


def call(host, name, arguments, request):
    receipt=host.invoke(dict(request_id=request,tool_id=name,arguments=arguments,cache='new',
        reason='Authorized deterministic public GVS profile reproduction and evidence-backed development experience'))
    atomic_json(host.store.root/(request+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise RuntimeError(json.dumps(receipt))
    return receipt,host.store.artifact(receipt['output'])


def artifact(run, ref):
    return dict(run_id=run,path='objects/'+ref['artifact_id']+'.json',sha256=ref['artifact_id'])


def strategy(inp, source):
    ref=artifact(inp['run_id'],source)
    steps=[
        'Select the declared fixed free-reach profile only for its exact scope. Read the predictor/execution distinction, ideal-tension assumption and historical cost. Changed configurations are unvalidated starting points.',
        'Use simulation.run with the configured profile. The implementation imports numerical guesses and regenerates the entire warm state trajectory from actual measurements; nominal metadata is not the current state.',
        'Use evaluation.run on the saved execution with its execution identity. Preserve the original task duration, bounds and authoritative evaluator.',
        'Use control.profile_report to separate independently accepted plans from raw optimizer convergence and selected initialization. A feasible early stop is suboptimal; a historical guess is not new execution evidence.',
        'Inspect complete update delivery, including preparation, construction and validation. Report reach, sampled final-window settling and deadline misses as separate results.',
        'If numerical resets or incomplete execution occur, preserve the last valid trajectory boundary. Inspect the saved reason and evidence; do not treat post-reset samples as recovery or relabel completion as task success.'
    ]
    tools=['control.profile_describe','simulation.run','evaluation.run','control.profile_report','evidence.read']
    return dict(skill_id='gvs_nmpc_free_reach',version=1,name='Use and diagnose the fixed GVS NMPC free-reach profile',
        status='candidate',category='CONTROL',description='Evidence-backed selection and diagnosis of one offline ideal-tension free-reach configuration. Combined configuration evidence; no isolated causal claim.',
        trigger_signature={},when_to_apply=['Exact declared profile scope with an offline simulation budget'],
        when_not_to_apply=['Real-time or motor execution, contact tasks, global robustness claims; changed tasks without new validation'],
        applicability=dict(robot_families=[inp['robot']['family']],task_types=[inp['task']['family']],
            model_levels=['M2'],control_levels=['C3'],execution_scope=execution_scope(inp)),
        required_tools=tools,strategy=[dict(action='invoke_tool',tool=t,instruction=s) for t,s in zip(tools[:4],steps[:4])]+
            [dict(action='inspect_evidence',evidence_refs=[ref],instruction=s) for s in steps[4:]],
        negative_constraints=sorted(REQUIRED_CONSTRAINTS),evidence=[ref],
        provenance=dict(source_runs=[inp['run_id']],supporting_evidence=[ref],created_by='harness',created_at=now()))


def prepare(root):
    store=Store(root)
    if store.db.exists():
        state=json.loads((root/'workflow.json').read_text(encoding='utf8'))
        return Host(root,state['run_id']),state
    identity=uuid4().hex[:12]
    store.create(dict(project_id='gvs-profile-'+identity,grant_id='gvs-profile-'+identity,
        authorization_source='User authorized one original-task public NMPC acceptance, development skills and local evidence; no model calls',
        budget=dict(tool_calls=40,model_calls=0,backend_solves=1,worker_calls=0,wall_s=7200.)))
    inp=profile_input('gvs-profile-'+identity);host=Host(root,inp['run_id']);host.create(inp)
    desc,_=call(host,'control.profile_describe',{},'describe')
    skill=strategy(inp,desc['output'])
    call(host,'skills.propose',dict(skill=skill),'propose')
    call(host,'control.profile_declare_strategy',dict(skill_ref='gvs_nmpc_free_reach@1'),'declare')
    state=dict(run_id=inp['run_id'],strategy_sha256=strategy_hash(skill),interpreter=sys.executable,
        threads={k:os.environ[k] for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')})
    atomic_json(root/'workflow.json',state)
    atomic_json(root/'input.json',inp)
    print('Prepared solve-free public session '+inp['run_id'],flush=True)
    return host,state


def inspect(root):
    inp=profile_input('gvs-profile-discovery-'+uuid4().hex[:12])
    inp['policy']['budget'].update(backend_solves=0,wall_s=120.)
    inp['policy']['timeout_s']=30.
    host=Host(root,inp['run_id']);host.create(inp)
    _,retrieved=call(host,'skills.search',{},'retrieve-'+inp['run_id'])
    context=host.context()
    compact=dict(run_id=host.run_id,skills=[dict(skill_id=s['skill_id'],status=s['status'],
        human_approval=s['human_approval'],scope_assessment=s.get('scope_assessment')) for s in retrieved['skills']],
        context_skill_ids=[s['skill_id'] for s in context['skills']],memory_count=len(context['memory']))
    atomic_json(root/'fresh_session_discovery.json',compact)
    print(json.dumps(compact),flush=True)


def run(root):
    host,state=prepare(root)
    print('Starting one 350 ms public MuJoCo execution; updates run offline.',flush=True)
    sim,_=call(host,'simulation.run',dict(candidate_id='profile-original',changes={}),'simulate')
    ev,_=call(host,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),'evaluate')
    _,reported=call(host,'control.profile_report',dict(simulation_request_id='simulate',evaluation_request_id='evaluate'),'report')
    summary=reported['detail'];atomic_json(root/'summary.json',summary)
    (root/'report.md').write_text(markdown(summary),encoding='utf8')
    inp=host.store.session(host.run_id)['snapshot']['input']
    worked=summary['strategy_worked']
    record=dict(validation_id='public-profile-original',skill_ref='gvs_nmpc_free_reach@1',
        strategy_sha256=state['strategy_sha256'],method='deterministic',outcome='passed' if worked else 'failed',
        validated_runs=[host.run_id] if worked else [],failed_validation_runs=[] if worked else [host.run_id],
        task_coverage=[inp['task']['family']],robot_coverage=[inp['robot']['family']],seed_coverage=[inp['seed']],
        evidence_refs=[artifact(host.run_id,summary['strategy_validation'])],validated_by='harness',validated_at=now(),
        summary='Trusted predeclared strategy check against fresh public original-task execution; no approval, transfer, settling or real-time inference.')
    call(host,'skills.validate',dict(reference='gvs_nmpc_free_reach@1',record=record),'validate')
    notes=[
        'The gvs_nmpc_free_reach_v1 profile has separate predictor and execution models. Select via control.profile_describe and inspect its exact scope. Its historical numerical data are guesses; execution regenerates warm states. The successful combination does not establish isolated causality for each setting.',
        'For profile diagnosis use control.profile_report: reach, sampled settling, accepted feasibility, raw termination, initialization selection, hold-last use and full delivery cost are separate. Preserve pre-reset boundaries on numerical failure. These notes recommend inspection; only linked sealed evaluations establish task outcomes.'
    ]
    for i,note in enumerate(notes):
        call(host,'memory.save',dict(entry=dict(memory_id=f'gvs-profile-note-{i}',summary=note,kind='model_note',
            task_family=inp['task']['family'],task_version=inp['task']['task_version'],backend=inp['policy']['backend']['extension_id'],
            model_id=host.model_identity(),model_scope=host.model_scope(),tags=['gvs_nmpc_free_reach_v1'],sources=[ev['output']])),f'memory-{i}')
    print(json.dumps({k:summary[k] for k in ('complete','official_task_success','terminal_error_m','sampled_settling',
        'accepted_plans','updates','mean_update_s','deadline_misses')}),flush=True)
    inspect(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run','inspect'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.output.resolve()
    {'prepare':prepare,'run':run,'inspect':inspect}[args.action](root)
