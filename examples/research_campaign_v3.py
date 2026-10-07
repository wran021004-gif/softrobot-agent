"""Successor native campaign with current authority and conditional verification."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples import research_campaign_v2 as previous
from examples import research_model_v1 as pilot
from tools.state_io import read,atomic_json,digest
from tools.platform_store import zero
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.fixed_research import select_candidate

CONFIG=ROOT/'configs/research/native_campaign_v3.json'
FILES=(*previous.FILES,'examples/research_campaign_v3.py','configs/research/native_campaign_v3.json',
       'tools/current_research_authority.py','tools/platform_models.py')


def seal():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES},
        stable_controller=pilot.revision()['stable_controller'])


def prepare(directory=None,*,offline_fixture=False):
    config=read(CONFIG)
    if not offline_fixture and time.time()-config['preparation_started_unix']>7200:
        raise ValueError('PREPARATION_ACTIVE_LIMIT_REACHED')
    w=previous.prepare(directory,offline_fixture,config=config)
    w.freeze.update(implementation=seal(),clock_policy=config['clock_policy'],live_clock=None,
        predecessor=dict(campaign='research_native_development_v2_20261007',status='sealed_failed',
            review='evidence/research_native_development_v2_20261007/independent_live_review.json',
            old_grant_transferred=False),preparation_started_unix=config['preparation_started_unix'])
    w.freeze['known_review_issues']+=read(ROOT/'evidence/research_native_development_v2_20261007/independent_live_review.json')['issues']
    pilot.adopt_current_working(w)
    pilot.configure(w);pilot.persist(w)
    adapter=EvidenceDrivenAdapter();payload=payload_for(w.host,adapter)
    pilot.adopt_current_working(w)
    pilot.persist(w)
    atomic_json(w.directory/'prepared_request.json',dict(payload=payload,audit=adapter.context_assembly_audit))
    atomic_json(w.directory/'freeze_seal.json',dict(identity=digest(w.freeze),before_paid_activity=True))
    return w


def start_clock(w):
    if w.freeze.get('live_clock'):raise ValueError('LIVE_CLOCK_ALREADY_STARTED_NO_RESET')
    usage=w.store.remaining()['used']
    if usage['model_calls'] or usage['backend_solves']:raise ValueError('PAID_ACTIVITY_PRECEDES_LIVE_CLOCK')
    now=time.time()
    waits=read(w.directory/'authorization_wait.json') if (w.directory/'authorization_wait.json').exists() else dict(intervals=[],total_s=0.)
    active=now-w.freeze['preparation_started_unix']-waits.get('total_s',0.)
    if active>7200:raise ValueError('PREPARATION_ACTIVE_LIMIT_REACHED')
    charged=max(0.,active-usage['wall_s'])
    boundary=dict(preparation_active_s=active,authorization_waits=waits,
        preparation_total_elapsed_s=now-w.freeze['preparation_started_unix'],prior_charged_s=usage['wall_s'],
        separately_charged_engineering_s=charged,physical_activity=0)
    reservation,_=w.store.reserve(w.host.run_id,'successor-preflight-engineering',digest(boundary),'engineering',
        {**zero(),'tool_calls':1,'wall_s':7200.})
    w.store.complete(reservation,dict(request_id=reservation['request_id'],execution_id=reservation['execution_id'],
        caller='engineering',tool_id='engineering.successor_preflight',tool_version='1.0.0',
        execution_status='completed',charged=zero()),boundary,charged)
    atomic_json(w.directory/'preparation_accounting.json',boundary)
    origin=time.time()
    w.freeze['live_clock']=dict(version='successor_clock@3.0.0',origin_unix=origin,deadline_unix=origin+36000.,
        reset_permitted=False,subsequent_waits_pause_clock=False)
    # Existing completion helpers consume this timestamp only in this new grant.
    w.freeze['assignment_start_unix']=origin
    atomic_json(w.directory/'live_clock.json',w.freeze['live_clock'])
    pilot.configure(w);pilot.persist(w)


def verification_gate(w):
    chosen=select_candidate([r for r in previous.search_rows(w) if r['case_id']=='nominal'])
    count=20 if chosen else 10
    required=dict(backend_solves=count,model_calls=2,tool_calls=3*count+10,wall_s=990.*count+1200.,worker_calls=0)
    available=deepcopy(w.store.remaining()['remaining'])
    clock=w.freeze.get('live_clock')
    available['wall_s']=min(available['wall_s'],max(0.,clock['deadline_unix']-time.time())) if clock else 0.
    shortfalls={k:max(0.,v-available[k]) for k,v in required.items()}
    frozen={k:deepcopy(chosen[k]) for k in ('candidate_id','configuration','changes')} if chosen else None
    return dict(version='conditional_verification@3.0.0',selected_candidate=frozen,
        branch='matched_comparison' if chosen else 'incumbent_only_characterization',attempts=count,
        schedule='Five existing cases, seed17 then18, incumbent then candidate per slot when paired',
        no_candidate_question='What is the unchanged incumbent performance under the currently unmeasured frozen perturbations?',
        required=required,available=available,shortfalls=shortfalls,authorized=not any(shortfalls.values()),
        limitation='Final verification is conditional, not guaranteed by the research allocation; no schedule reduction or search-result substitution.')


def verify(w):
    path=w.directory/'conditional_verification_gate.json'
    if path.exists():raise ValueError('CONDITIONAL_VERIFICATION_ALREADY_GATED_NO_REPLAY')
    gate=verification_gate(w);atomic_json(path,gate)
    if not gate['authorized']:
        result=dict(status='not_started',reason='Full frozen verification and delivery do not fit remaining resources',
            gate=gate,complete=False,improvement_supported=False)
        atomic_json(w.directory/'verification_not_started.json',result)
        pilot.reusable.feedback(w,result,'conditional_verification_not_started')
        return result
    return previous.verify(w)


def live(directory=None):
    from examples.gvs_nmpc_route_experiment import load_credential
    config=read(CONFIG);w=pilot.restore(directory or ROOT/'runs'/config['campaign_id'])
    if w.status!='prepared' or w.freeze.get('offline_fixture') or w.freeze.get('live_clock'):
        raise ValueError('SEALED_OR_ATTEMPTED_SUCCESSOR_NO_RESET')
    if seal()['files']!=w.freeze['implementation']['files']:raise ValueError('FROZEN_SUCCESSOR_IMPLEMENTATION_CHANGED')
    # No provider call: inspect actual current menu and complete fitted payload.
    adapter=EvidenceDrivenAdapter();payload_for(w.host,adapter)
    load_credential(Path.home()/'.codex/.env')
    start_clock(w);w.status='running';pilot.persist(w)
    try:
        while w.status=='running':
            if time.time()>=w.freeze['live_clock']['deadline_unix']:
                w.status='host_stopped';w.stop_reason='Live elapsed ceiling';break
            row=previous.native_decision(w)
            pilot.reusable.execute(w,row)
            previous.append_results(w,row)
    except Exception as exc:
        w.status='failed';w.stop_reason=str(exc)
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
    pilot.persist(w)
    if w.status in ('model_stopped','execution_stopped'):
        try:verify(w)
        except Exception as exc:atomic_json(w.directory/'verification_failure.json',dict(message=str(exc)))
    previous.finish(w)
    atomic_json(Path(w.freeze['experiment']['evidence_directory'])/'successor_clock_summary.json',
        dict(preparation=read(w.directory/'preparation_accounting.json'),live_clock=w.freeze['live_clock'],
            live_elapsed_s=time.time()-w.freeze['live_clock']['origin_unix'],grant_unchanged=True,
            conditional_verification=read(w.directory/'conditional_verification_gate.json') if (w.directory/'conditional_verification_gate.json').exists() else None))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','live']);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.mode=='prepare':prepare(args.output)
    else:live(args.output)
