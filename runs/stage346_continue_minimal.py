"""Explicit operator continuation after a sealed network failure; no budget reset."""
from pathlib import Path
import sys
import time
import shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.diagnostic_workflow import DiagnosticWorkflow
from tools.platform_host import Host
from tools.platform_models import run_loop
from tools.state_io import read,atomic_json
from examples.gvs_nmpc_route_experiment import load_credential

directory=ROOT/'runs/stage346_shared_diagnosis_20261002/minimal'
w=DiagnosticWorkflow(directory,'dual_context',minimal=True)
w.freeze=read(directory/'freeze.json');w.project=w.freeze['project_id']
w.hosts={k:Host(directory,v) for k,v in w.freeze['hosts'].items()}
w.chain=read(directory/'outcome.json')['chain'];host=w.host('design')
state=w.store.session(host.run_id)['state']
if state.get('stop_reason')!='DEEPSEEK_NETWORK_ERROR':raise ValueError('Only the sealed network failure may continue')
guard=directory/'explicit_continuation.json'
if guard.exists():raise ValueError('Continuation already used')
shutil.copyfile(directory/'outcome.json',directory/'initial_transport_failure.json')
atomic_json(guard,dict(reason='Curl and same-interpreter urllib HEAD probes both reached the authorized endpoint with HTTP 401; explicitly continue within original three-attempt allocation.',
    prior_usage=w.store.remaining(),prior_turn=state['turn'],automatic_transport_retry=False))
with w.store.transaction() as db:
    state['turn']+=1
    state.pop('stop_reason',None)
    w.store.update_state(db,host.run_id,state,'paused')
    w.store.event(db,host.run_id,'explicit_continuation','sealed_network_failure',outputs=[w.store.put(db,read(guard))])
load_credential(Path.home()/'.codex/.env');started=time.monotonic()
run_loop(host)
state=w.store.session(host.run_id)['state'];ref=state.get('handoffs',{}).get('design_response')
if ref:
    w.chain['initial_response']=ref
    atomic_json(directory/'initial_response.json',w.store.artifact(ref));atomic_json(directory/'chain.json',w.chain)
w.export('completed' if ref else 'incomplete',
    'Native response validated after explicit same-ledger network continuation; cross-run protocol unit only.' if ref else str(state.get('stop_reason')),
    read(directory/'initial_transport_failure.json')['elapsed_s']+time.monotonic()-started)
