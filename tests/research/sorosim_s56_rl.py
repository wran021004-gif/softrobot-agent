"""Two genuine PPO routes; saved-state diagnostics never step the simulator."""
import json
from pathlib import Path
import time
import subprocess

import numpy as np
from tests.research.sorosim_s56_refinement import initialize,finish
from tools.platform_host import Host
from tools.platform_store import plain
from tools.research import core,rl
from tools.research.state import state,save,update
from tools.state_io import atomic_json,read

ROOT=Path(__file__).resolve().parents[2]


def preserve_files(host,directory,paths):
    records=[]
    for path in paths:
        with host.store.transaction() as db:
            ref=plain(host.store.put(db,path.read_bytes(),media='application/octet-stream'))
        records.append(dict(path=str(path.relative_to(directory)),reference=ref,bytes=path.stat().st_size))
    return save(host,records,'rl_raw_files')


def evaluate_route(host,request,key):
    started=rl.dispatch(host,request,key+'-start');run_id=started['run_id']
    while True:
        for attempt in range(3):
            try:
                status=rl.reconcile(host,run_id,lightweight=True);break
            except PermissionError:
                if attempt==2:raise
                time.sleep(.05)  # Windows can briefly deny reads during atomic state replacement.
        if not status['worker_alive']:break
        time.sleep(5)
    terminal=rl.dispatch(host,dict(operation='status',run_id=run_id,rationale='Read actual actions, failures, optimizer updates and checkpoint'),key+'-status')
    summary=core.read_evidence(host,dict(reference=terminal['training_summary_reference']))
    result=dict(mode=request.get('mode','residual'),run_id=run_id,training_summary=terminal['training_summary_reference'],
        consumed=summary['consumed'],checkpoint=summary.get('checkpoint'),training_status=summary['status'])
    checkpoint=summary.get('checkpoint')
    folder=host.store.root/'rl'/run_id
    files=list((folder/'failures').rglob('*.*'))
    if checkpoint and checkpoint['policy_present']:
        generation=checkpoint['generation']
        files.extend([folder/'checkpoint.json',folder/'checkpoints'/generation/'metadata.json',
            folder/'checkpoints'/generation/'policy.zip'])
        evaluation=rl.dispatch(host,dict(operation='evaluate',run_id=run_id,checkpoint=generation,
            rationale='Independent frozen original-task evaluation; training reward is not acceptance'),key+'-evaluate')
        result['evaluation']=evaluation['reference']
        result['evaluation_facts']=core.read_evidence(host,dict(reference=evaluation['reference']))
        trajectory=Path(result['evaluation_facts'].get('trajectory',''))
        if trajectory.is_file():files.append(trajectory)
    result['raw_files']=preserve_files(host,folder,[p for p in files if p.is_file()])
    result['numerical_failures']=rl.run.failure_diagnosis(folder)
    continuation=folder/'continuation.json'
    if continuation.exists():result['continuation']=save(host,read(continuation),'ppo_optimizer_continuation_proof')
    return result


def run():
    host,candidate,source=initialize('s56_rl')
    historical=read(ROOT/'evidence/sorosim_s5rl/summary.json')
    # Read-only audit from all original failure states, with representative raw provenance.
    audit=read(ROOT/'evidence/sorosim_s56/rl/preflight_saved_states.json')
    diagnosis=save(host,audit,'saved_direct_failure_characterization')
    rows=[]
    direct=dict(operation='start',candidate=candidate,mode='direct',initial_tension_n=.2,
        allocation=dict(actions=65536),rationale='One controlled new lineage: initial mean tension .2 N instead of approximately 4 N after saved-state instability audit; retain variance, reward and physical protocol')
    rows.append(evaluate_route(host,direct,'s56-direct'))
    atomic_json(host.store.root/'partial_summary.json',dict(routes=rows,diagnosis=diagnosis))
    parent=Host(ROOT/'runs/research/sorosim-s5rl-design-b-20261016','sorosim-s5rl-design-b-20261016')
    previous=next(v for v in historical['routes'] if v['mode']=='residual')
    relation=rl.import_continuation_source(host,parent,previous['run_id'])
    request=dict(operation='continue',run_id=relation['run_id'],checkpoint=relation['checkpoint'],
        allocation=dict(actions=65536),rationale='Genuine additional residual PPO training: retain exact old candidate, four-channel reference, policy weights and Adam state; its previous independent task failure remains preserved')
    rows.append(evaluate_route(host,request,'s56-residual'))
    # Compare genuinely complete new direct episodes with the old failure boundary states.
    folder=host.store.root/'rl'/rows[0]['run_id'];started=time.perf_counter()
    code='import sys,json; from tools.rl.checks import stable_phase_diagnostics; print(json.dumps(stable_phase_diagnostics(sys.argv[1])))'
    done=subprocess.run([state(host)['spec']['runtime']['rl_python'],'-c',code,str(folder)],
        cwd=ROOT,capture_output=True,text=True,check=True)
    stable=json.loads(done.stdout);elapsed=time.perf_counter()-started
    update(host,numerical_s=state(host)['numerical_s']+elapsed)
    comparison=save(host,dict(stable,old_failures=diagnosis,elapsed_s=elapsed),'direct_stable_failure_comparison')
    summary=dict(stage='S5.6-RL',source_freeze=state(host)['freeze'],candidate=candidate,
        diagnosis=diagnosis,stable_comparison=comparison,parent_relation=relation,routes=rows,
        costs=rl.allocation_feedback(host),numerical_s=state(host)['numerical_s'],provider_requests=0,
        reference_decision='Retain old compatible residual reference to isolate genuine continuation. New P2 reference is not a physically passing witness and would change continuation semantics.',
        limitations=['one fixed seed and initial state per route','different direct initialization lineage',
            'residual policy/Adam continuation with its original reference','no formal superiority or robustness claim'])
    finish(host,summary,'evidence/sorosim_s56/rl')
    print(json.dumps(dict(routes=[dict(mode=r['mode'],consumed=r['consumed']) for r in rows],costs=summary['costs'])),flush=True)


if __name__=='__main__':run()
