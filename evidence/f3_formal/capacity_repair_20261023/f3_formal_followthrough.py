"""Finish this one authorized F3 run using existing CLI/admission/export only."""
import asyncio
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback
import zipfile
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state, core_hashes, science_hashes
from tools.research.agent import pending, load_credential
from tools.rl.run import process_birth
from tools.state_io import atomic_json, read
from tests.research.f3_formal_control import admit
from tests.research.f3_provider_recovery import approve_from_standing, apply as close_provider_loss

STUDY='f3-autonomous-20261022-01'
h=Host(ROOT/'runs/research'/STUDY,STUDY,actor='unified-research')
STATUS=ROOT/'runs/f3-formal-supervision.json'
os.environ.update(SOROSIM_ROOT='D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc/runs/SoRoSim-pinned',
    OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONIOENCODING='utf-8')


def checkpoint(phase,**values):
    s=state(h)
    atomic_json(STATUS,dict(study_id=STUDY,pid=os.getpid(),birth=process_birth(os.getpid()),
        phase=phase,updated_unix=time.time(),freeze=s['freeze'],status=s['research_status'],
        pending_owner=(s.get('pending') or {}).get('owner'),provider_requests=s['pilot']['live_model_requests'],
        nmpc_launches=s.get('nmpc_launches',0),physical_used=h.store.remaining()['used']['backend_solves'],
        live_admitted=s['pilot'].get('session_handoff_live_admitted',False),**values))


def settled():
    s=state(h)
    if s['pending'] or pending(h) or s['pilot'].get('unconsumed_response'):raise ValueError('UNSETTLED_OUTCOME_NO_NEW_SEND')
    if core_hashes()!=s['core_hashes'] or science_hashes()!=s['profile']['science_hashes']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')


def recover_authorized_loss():
    rows=pending(h)
    if len(rows)!=1 or rows[0]['status']!='unknown' or not args.standing_authorization:return False
    from tools.research.agent import received
    requests=[e for e in h.store.events(STUDY) if e['kind']=='r3_request']
    consecutive=0
    for event in reversed(requests):
        if received(h,event['request_id']) is not None:break
        consecutive+=1
    if consecutive>state(h)['spec']['runtime']['provider']['max_no_progress']:
        raise ValueError('REPEATED_TRANSPORT_LOSS_REQUIRES_ENGINEERING_DIAGNOSIS')
    reference=read(args.standing_authorization)
    approval=approve_from_standing(h,reference,rows[0]['request_id'])
    folder=ROOT/'runs/f3-automatic-recovery'/rows[0]['request_id'];folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'authorization.json',approval)
    result=close_provider_loss(h,approval);atomic_json(folder/'disposition.json',result)
    checkpoint('provider_delivery_loss_recovered',request_id=rows[0]['request_id'],standing_authorization=reference)
    return True


def run_cli(label,*arguments):
    for attempt in range(state(h)['spec']['runtime']['provider']['max_repairs']+1):
        stem='f3-formal-'+label+'-'+str(time.time_ns())
        with (ROOT/'runs'/(stem+'.stdout.json')).open('w',encoding='utf-8') as stdout,\
                (ROOT/'runs'/(stem+'.stderr.log')).open('w',encoding='utf-8') as stderr:
            process=subprocess.Popen([sys.executable,'-m',*arguments],cwd=ROOT,stdout=stdout,stderr=stderr,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            while process.poll() is None:
                checkpoint(label,cli_pid=process.pid,cli_birth=process_birth(process.pid),attempt=attempt,log_stem=stem)
                time.sleep(10)
        if process.returncode==0:return
        if not recover_authorized_loss():raise ValueError(label+'_EXIT_'+str(process.returncode)+'; inspect runs/'+stem+'.stderr.log')
    raise ValueError('CONFIGURED_ENGINEERING_REPAIR_LIMIT_REACHED')


def publish_report():
    out=ROOT/'evidence/f3_formal';a=read(out/'formal_audit.json');package=read(out/'design_package.json')
    disposition=read(out/'disposition.json');s=state(h)
    lines=['# Formal F3 autonomous study','',
        f'One bounded Study `{STUDY}` has legally terminated with status `{package["status"]}`. Original-task acceptance: **{package["accepted"]}**. The autonomous Agent selected the scientific actions; Codex handled engineering admission and evidence supervision.','',
        f'Executed branch: `integration/f3-prestudy`. Current explicit implementation binding: `{s["freeze"]}`. Resolved Study identity: `{s["spec"]["resolved_identity"]}`. Initial scientific execution baseline: `8269178b9cc3824b6ee3b4fc13dfb8c224405fa9`. Explicit core migrations are retained in the audit; old results and costs preserve their original provenance. Report commits do not migrate the binding.','',
        f'Original mirror task identity: `{a["canonical_task_identity"]}`. Original FamilySpace identity: `{a["family_space_identity"]}`. Both are unchanged. Final source hashes match the frozen profile: `{a["implementation_unchanged"]}`. The final clean-head binder output and identity-bound authorization are in [formal audit](../../evidence/f3_formal/formal_audit.json).','',
        'Declared FamilySpace retains 1–9 segments, 1–12 tendons and all original length/material/section/routing/physical variables. The registered execution envelope is 1–7 tendons. Selected topology, route/section/attachment clearance, mesh, physical model dimensions and controller/solver support remain candidate-specific. T2 additionally requires actual legal indices, authorized continuous variables, complete exactly bound registered model groups and sufficient preparation/kernel budget.','',
        f'No historical experimental results were supplied: `{json.dumps(a["no_history"],ensure_ascii=False)}`. Public engineering priors are immutable artifact `{a["public_prior_reference"]["artifact_id"]}`; see [manifest](../../evidence/f3_formal/public_prior_manifest.json). Geometry/material prototypes, defaults, control weights, task/evaluator and mathematical/model capabilities are public priors. They may carry historical design knowledge; initialization is not random or information-free. Future comparison Agents must receive the same frozen priors and resource conditions.','',
        'The explicit user authorization binds the Study, final SHA, resolved/task/family identities, Provider endpoint/model/data scope, independent Reporter, mathematics, SoRoSim R2024a, MuJoCo, NMPC, PPO and later Live Session Handoff. Historical F3.0 `failed_semantic_admission` is preserved and accepted as a research risk. No new static semantic exam or repeated SOCP preflight was performed.','',
        'Authorized ceilings: Provider 128 including 8 protected and Reporter; public operations 400 including 20 protected; mathematics 64; shared physical launches 80; NMPC 6; PPO stages 2 and aggregate actions 262144; independent RL evaluation episodes 2; offline NLP 2; BDF replay 2. All counts remain in the original frozen ledger; no resets or extensions occurred.','',
        f'Actual ledger: `{json.dumps(a["ledger"],ensure_ascii=False)}`. NMPC launches: `{a["nmpc_launches"]}`; mathematical evaluations: `{a["mathematical_evaluations"]}`. Exact RL stage/action usage is in [disposition](../../evidence/f3_formal/disposition.json) and the archived state.','',
        'Environment admission used the isolated research interpreter and existing RL interpreter. Provider authentication/model availability, MATLAB R2024a/Optimization Toolbox, pinned SoRoSim gateway, MuJoCo, CasADi, CVXPY/Clarabel and single-thread BLAS/OMP/MKL passed without a robot scientific experiment. Exact dependency/source hashes and versions are in [environment](../../evidence/f3_formal/prelaunch_environment.json).','',
        'Focused offline regression: 41 passed with real SDK/Store, mock HTTP and scientific workers blocked. The first attempt had 26 passes and one missing-archive-path error, preserved in [first attempt](../../evidence/f3_formal/prelaunch_first_attempt.json). The [corrected run](../../evidence/f3_formal/prelaunch_regression.json) supplied the original archive path and verified its hash unchanged.','',
        f'Real Provider usage, including independent Reporter: `{json.dumps(a["provider_usage"],ensure_ascii=False)}`. The first requests, original response bytes, usage, tool IDs, receipts and request/response identities are indexed in the audit and immutable archive. Reported monetary cost remains unknown when the Provider did not supply it.','',
        f'Provider delivery-loss recovery audit contains `{len(a.get("provider_recovery",[]))}` authorization/disposition records. Any lost response retains remote outcome unknown and its original request charge. A separately authorized local delivery-failure receipt releases only its occupied lease; subsequent requests have new identities and new charges under the same frozen total. No model response or completed invocation is fabricated.','',
        f'Live Handoff records: `{len(a["handoffs"])}` admission/preparation/commit records. Their exact snapshot identities, independent restore verification, original scope and post-rotation L0 deliveries are in the audit. If the Agent legally stopped before a usable rotation boundary, no extra scientific action was forced to obtain a handoff.','',
        f'First SoRoSim scientific execution was autonomously selected NMPC on candidate `d1f82aca6c318a365d9842b46cfef9d8c5ec61f38cdb70456345538ebb67b997`. The actual MATLAB process started and the Store saved 12 generalized coordinates, 24 state entries and 4 tendon inputs with current-candidate initial-state provenance. Its original worker events, returned status, control traces, scientific validation and independent evaluator output are retained in the archive and worker package. This is separate from environment readiness and does not by itself establish task success.','',
        'Reporter reports retain deterministic numerical facts and non-authoritative interpretations. `decision_deliveries` in the audit links exact report references to the following main-Agent packet; original event order demonstrates delivery before the next decision. Any unavailable interpretation remains explicitly unavailable rather than changing scientific evidence.','',
        '## Original autonomous research trace','',
        '| Action | Agent method / intent | Recorded execution | Outcome |','|---|---|---|---|']
    for row in a['action_trace']['recent']:
        cells=[row.get('action'),row.get('method'),row.get('execution_status'),json.dumps(row.get('outcome'),ensure_ascii=False)]
        lines.append('| '+' | '.join(str(c).replace('|','/').replace('\n',' ') for c in cells)+' |')
    lines+=['', 'Original hypotheses, expected/weakening observations, fixed conditions, evidence citations and subsequent choices remain in `action_trace` in the audit. Failed generation, numerical attempts, physical failures and reasoning errors are preserved. The supervisor supplied no scientific candidate, control sequence or method order.','',
        '## Final measured outcome','',
        f'Final disposition: `{json.dumps(a["final_disposition"],ensure_ascii=False)}`. Selected evidence: `{json.dumps(a["selected"],ensure_ascii=False)}`.','',
        f'Best verified delivery status: `{package["status"]}`. Acceptance: `{json.dumps(package.get("acceptance"),ensure_ascii=False)}`. The complete design, control schedule, raw evaluation and exact identity are in [design package](../../evidence/f3_formal/design_package.json). If acceptance is false, this is not a successful task solution. Failed local attempts establish neither global infeasibility nor a proven causal mechanism. Robustness, repeatability and hardware performance remain unassessed.','',
        '## Traceable artifacts','',
        'The [immutable artifact archive](../../evidence/f3_formal/immutable_artifacts.tar.gz) contains original Store blobs and a full state/events/calls/ledger snapshot. Every member hash was independently checked against [archive manifest](../../evidence/f3_formal/archive_manifest.json). [Native sessions and workers](../../evidence/f3_formal/native_sessions_and_workers.zip) preserves SDK snapshots, worker requests/results and original logs. [Final file manifest](../../evidence/f3_formal/final_artifact_manifest.json) records file hashes. The original Store remains at `runs/research/f3-autonomous-20261022-01/platform.sqlite`.','']
    (ROOT/'docs/research/f3_formal_study.md').write_text('\n'.join(lines),encoding='utf-8')
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser())
    secret=os.environ['DEEPSEEK_API_KEY'].encode()
    with tarfile.open(out/'immutable_artifacts.tar.gz','r:gz') as archive:
        if any(secret in archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()):raise ValueError('SECRET_IN_ARCHIVE')
    with zipfile.ZipFile(out/'native_sessions_and_workers.zip') as z:
        if any(secret in z.read(n) for n in z.namelist()):raise ValueError('SECRET_IN_SESSION_PACKAGE')
    for p in [ROOT/'docs/research/f3_formal_study.md',*out.glob('*.json')]:
        if secret in p.read_bytes():raise ValueError('SECRET_IN_REPORT')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    publication_hold=ROOT/'runs/f3-raw-publication-hold.json'
    if publication_hold.exists() and read(publication_hold).get('publication_status')!='approved':
        raise ValueError('RAW_PUBLICATION_REVIEW_PENDING_NO_PUSH')
    # New raw SDK/session exports were rejected for remote publication. Keep
    # them local; this automatic publication includes only the summary report.
    subprocess.run(['git','add','docs/research/f3_formal_study.md'],cwd=ROOT,check=True)
    subprocess.run(['git','commit','-m','Archive formal F3 autonomous study and final audit'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','integration/f3-prestudy'],cwd=ROOT,check=True)


try:
    parser=argparse.ArgumentParser();entry=parser.add_mutually_exclusive_group(required=True)
    entry.add_argument('--first-pid',type=int);entry.add_argument('--resume-settled',action='store_true')
    parser.add_argument('--standing-authorization')
    args=parser.parse_args()
    first_pid=args.first_pid;first_birth=process_birth(first_pid) if first_pid is not None else None
    checkpoint('waiting_first_completed_invocation' if first_pid is not None else 'resuming_settled_invocation',first_pid=first_pid,first_birth=first_birth)
    while first_birth is not None and process_birth(first_pid)==first_birth:
        time.sleep(10);checkpoint('waiting_first_completed_invocation',first_pid=first_pid,first_birth=first_birth)
    if pending(h):
        if not recover_authorized_loss():raise ValueError('UNSETTLED_OUTCOME_NO_NEW_SEND')
        run_cli('recovered-first','tools.research','run','--run-id',STUDY,'--pause-after-completed-invocations','1')
    settled()
    if state(h)['research_status']!='stopped':
        if not any(e['kind']=='supervisor_pause' for e in h.store.events(h.run_id)):
            run_cli('first-completed-invocation','tools.research','run','--run-id',STUDY,'--pause-after-completed-invocations','1')
            settled()
    if state(h)['research_status']!='stopped':
        if not any(e['kind']=='supervisor_pause' for e in h.store.events(h.run_id)):raise ValueError('FIRST_COMPLETED_PAUSE_REQUIRED')
        checkpoint('live_admission');proof=asyncio.run(admit(h));atomic_json(ROOT/'runs/f3-formal-live-admission.json',proof)
        run_cli('handoff-validation','tools.research','run','--run-id',STUDY,'--session-handoff','--pause-after-completed-invocations','2')
        settled()
        if state(h)['research_status']!='stopped':
            commits=[e for e in h.store.events(h.run_id) if e['kind']=='session_handoff' and e['status']=='committed']
            if not commits:raise ValueError('FIRST_REAL_HANDOFF_NOT_COMMITTED')
            packets=[e for e in h.store.events(h.run_id) if e['kind']=='model_decision_packet' and e['sequence']>commits[0]['sequence']]
            if not packets:raise ValueError('POST_HANDOFF_REAL_DECISION_PACKET_REQUIRED')
            packet=h.store.artifact(packets[0]['outputs'][0]);r=packet['research']
            if not all(k in r for k in ('research_intent','budget','actions')) or not packet['candidates']:
                raise ValueError('POST_HANDOFF_RESEARCH_STATE_MISSING')
            checkpoint('post_handoff_verified',packet=packets[0]['outputs'][0])
            run_cli('autonomous-remainder','tools.research','run','--run-id',STUDY,'--session-handoff')
    settled()
    run_cli('final-export','runs.f3_formal_export')
    checkpoint('publishing_final_audit');publish_report();checkpoint('complete')
except BaseException as exc:
    checkpoint('engineering_attention_required',error=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
    raise
