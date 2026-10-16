"""Single-use M3-C3 offline delivery checks, never a second research service.

Run diagnose, then search, from a clean committed worktree. Existing studies are
read/recovered, never reset. No provider, RL, controller update or task evaluation.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.state import state
from tools.state_io import read, atomic_json

OUT=ROOT/'evidence/m3c3_mixed_family_search'


def committed():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_BEFORE_SCIENTIFIC_ENGINEERING_EXECUTION')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def diagnose():
    from tools.research.runtime_capability import environment
    from tools.service_execution import _run_contained
    commit=committed()
    target=OUT/'windows_loader_boundary.json'
    if target.exists():
        print(json.dumps(read(target),indent=2));return
    original=ROOT.parent/'m3c2-variable-segments/runs/serial-fixture-39f089bdddcf41cc8c2970843afb2b09/6.xml'
    # Inspect the actual retained failure; no geometry regeneration or default-stack rerun.
    xml=original.read_bytes();identity=hashlib.sha256(xml).hexdigest()
    tree=ET.fromstring(xml)
    assert identity=='2f53a0dadae471cde5f2618a2a473275d19e16d55ebfccc826290ec0bc26c969'
    assert len(tree.findall('.//joint'))-1==144  # excludes default declaration
    spec=resolve(ROOT/'configs/research/study_mixed_family_search_dev.json')
    folder=ROOT/'runs/m3c3-loader';folder.mkdir(parents=True,exist_ok=True)
    intent=folder/'intent.json';boundary=folder/'boundary.json'
    if intent.exists() and not boundary.exists():
        raise ValueError('UNCERTAIN_DIAGNOSTIC_NO_BLIND_RELAUNCH')
    if not boundary.exists():
        atomic_json(intent,dict(commit=commit,xml_sha256=identity,authorized_native_loads=1,stack_bytes=16*1024*1024))
        command='\n'.join([
            'from tools.service_execution import contain_worker_children',
            'job=contain_worker_children()',
            'import threading,sys,mujoco',
            'threading.stack_size(16*1024*1024)',
            'def load():',
            '    m=mujoco.MjModel.from_xml_path(sys.argv[1])',
            '    print(dict(nv=m.nv,nu=m.nu),flush=True)',
            't=threading.Thread(target=load);t.start();t.join()'])
        started=time.perf_counter()
        try:
            with (folder/'worker.log').open('w',encoding='utf8') as log:
                done=_run_contained([sys.executable,'-X','faulthandler','-c',command,str(original)],log,30)
            result=dict(returncode=done.returncode,termination_confirmed=True)
        except subprocess.TimeoutExpired as exc:
            result=dict(returncode=None,termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
        result['elapsed_s']=time.perf_counter()-started
        atomic_json(boundary,result)
    result=read(boundary);log=(folder/'worker.log').read_text(encoding='utf8',errors='replace')
    verified=result.get('returncode')==0 and "'nv': 144" in log and "'nu': 3" in log
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(original,OUT/'original_six_segment_12_cell.xml')
    value=dict(implementation=commit,original_failure_preserved=True,default_stack_repeats=0,
        observations=[dict(xml_sha256=identity,environment=environment(),backend=spec['configuration']['policy']['backend'],
            native_exit_code=-1073741571,source_evidence='evidence/m3c2_variable_segments/windows_xml_limitation.json',
            environment_provenance='Original retained XML and same specified Python/MuJoCo installation; current identity inspected, no new default-stack execution',
            failed_boundary='MjModel.from_xml_path/default Windows main-thread stack')],
        alternative_loader_check=dict(verified=verified,stack_bytes=16*1024*1024,boundary=result,worker_log=log,
            scope='XML load only on an explicitly enlarged thread stack; no controller or full execution validation',
            enabled_in_final_runtime=False,native_loads=1,physics_steps=0),
        task_success=None,physical_infeasibility_proven=False)
    atomic_json(target,value)
    print(json.dumps(value,indent=2))


def search():
    committed()
    path=ROOT/'configs/research/study_mixed_family_search_dev.json'
    host=core.prepare(path)
    if 'freeze' not in state(host):core.bind(host)
    s=state(host)
    query=dict(version='family_mixed_search_v1',family_space_identity=s['spec']['family_space_identity'],
        variable_groups=['segment_count','tendon_count','spans','lengths','materials','sections','routing'],
        segment_counts=[1,2,3],tendon_counts=[3,4],span_strategies=['whole_chain','distributed_consecutive','distal'],
        screening_fidelity='coarse',objective='target_equilibrium_residual',operating_point='target_equilibrium',
        max_proposals=16,max_evaluations=8)
    plan=dict(action='search',search=query,hypothesis='Bounded mixed family proposals can be scored without a predefined robot',
        expected_observation='Candidate-bound static residuals change incumbent and subsequent proposals',
        weakening_observation='No applicable finite residual or no feedback-responsive move',
        fixed_conditions='Frozen task, family, coarse screening and exact 12-cell final protocol',
        stopping_condition='At most 16 proposals and 8 mathematical attempts; no physical rollout',
        interpretation='Engineering demonstration of local proxy search, not a task-feasible robot discovery')
    response=core.dispatch(host,plan,'m3c3-first-bounded-search')
    current=state(host)
    if current['research_status']!='stopped':
        stop={k:v for k,v in plan.items() if k not in ('search','action')}
        stop.update(action='stop',supporting_evidence=current['analysis_results'])
        core.dispatch(host,stop,'m3c3-stop')
    core.export(host,OUT/'search')
    s=state(host)
    rows=response['result']['result']['evaluated']
    atomic_json(OUT/'search_verification.json',dict(implementation=s['freeze'],study=host.run_id,
        family_space_identity=s['spec']['family_space_identity'],final_evaluation_identity=s['spec']['final_evaluation_identity'],
        plan=response['plan'],search_result=response['result']['reference'],search_state=response['result']['result']['search_state'],
        rows=[dict(candidate=r['evidence'].get('candidate'),analysis=r['evidence'].get('analysis'),parameters=r['parameters'],
            status=r['computation_status'],scores=r.get('proxy_values'),lineage=r.get('lineage'),
            physical_design_identity=r.get('physical_design_identity'),numerical_model_identity=r.get('numerical_model_identity')) for r in rows],
        best=response['result']['result']['best_mathematical_candidate'],
        resource_use=dict(provider_requests=0,rl_training_stages=0,controller_updates=0,physical_backend_launches=0,
            complete_task_evaluations=0,physics_steps=0,mathematical_evaluations=s['mathematical_evaluations'],
            analysis_costs=s['analysis_costs'],construction_numerical_s=s['construction_numerical_s'],numerical_s=s['numerical_s']),
        closure=dict(status=s['research_status'],pending=s['pending'],success_gate=s.get('success_gate'),
            unsealed_calls=sum(not r['receipt'] for r in host.store.connect(True).execute('SELECT receipt FROM calls')))))
    print(json.dumps(dict(status='stopped',scores=[r.get('proxy_values') for r in rows],
        references=response['result']['reference'],mathematical_evaluations=s['mathematical_evaluations']),indent=2))


if __name__=='__main__':
    {'diagnose':diagnose,'search':search}[sys.argv[1]]()
