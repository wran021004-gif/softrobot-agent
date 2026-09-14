"""Conservative normalization: never infer a scientific conclusion from exit status."""
import re
from schemas.public_tools import PublicResult, Caller, ToolError


def error_info(message, code='TOOL_ERROR'):
    text = (code+' '+message).upper()
    rules = [
        ('permission', ('PERMISSION','AUTHORIZED','ALLOWLIST'), 'Use a tool permitted by the saved run grant.'),
        ('budget', ('BUDGET','RESOURCE LIMIT'), 'Inspect remaining resources and charged receipts; do not retry or reset the ledger.'),
        ('evidence', ('EVIDENCE','SOURCE_CHANGED','RESULT_CHANGED','UNREGISTERED','MISSING_SAVED','NOT_RUN','IDENTITY CHANGED'), 'Read the registered source/receipt; restore matching saved bytes or select existing complete evidence.'),
        ('timeout', ('TIMEOUT','TIMED OUT'), 'Inspect partial artifacts and charged reservation before an explicitly authorized retry.'),
        ('interrupted', ('INTERRUPTED',), 'Resume from sealed artifacts; incomplete reservations remain charged.'),
        ('dependency', ('UNAVAILABLE','CAPABILITY_MISSING','NO MODULE','ENCODER'), 'Install/configure the declared dependency or use existing cached evidence.'),
        ('input', ('INVALID','VALIDATION','UNKNOWN','MISMATCH','REVERSED','INTERVAL','REQUIRED','PRECONDITION','PCC BRANCH','NO_SAVED_SAMPLE_OR_ENTITY'), 'Read the input schema and preconditions, correct arguments, and cite valid evidence.')]
    category, action = next(((cat, action) for cat, keys, action in rules if any(k in text for k in keys)),
                            ('execution', 'Inspect the detailed result and worker log; do not assume a failed task or retry automatically.'))
    prefix=message.split(':',1)[0]
    canonical_code=prefix if re.fullmatch('[A-Z][A-Z0-9_]+',prefix) else {
        'input':'INVALID_INPUT','permission':'PERMISSION_DENIED','budget':'BUDGET_EXHAUSTED',
        'evidence':'EVIDENCE_UNAVAILABLE_OR_CHANGED','dependency':'DEPENDENCY_UNAVAILABLE',
        'timeout':'TIMEOUT','interrupted':'INTERRUPTED','execution':code}.get(category,code)
    return ToolError(category=category, code=canonical_code, message=message,
        recovery_condition=action, next_actions=[action])


def normalize(tool_id, result, *, call_id, caller, evidence=(), cost=None, details_ref=None, provenance=None):
    data = result.get('data') or {}
    status = result.get('status', 'failed')
    raw_solver = data.get('computation_status')
    solver = str(raw_solver or 'NOT_APPLICABLE').upper()
    if solver not in ('NOT_APPLICABLE','NOT_RUN','COMPLETED','INCOMPLETE','FAILED'):
        solver = 'UNKNOWN'
    if 'complete' in data and solver == 'NOT_APPLICABLE':
        solver = 'COMPLETED' if data['complete'] else 'INCOMPLETE'
    if data.get('execution_completed') is True:
        solver = 'COMPLETED'
    task = 'NOT_ASSESSED'
    # Historical replay and comparisons are never a new task evaluation.
    if data.get('evidence_role') == 'historical_replay':
        task = 'NOT_RUN'
    elif data.get('canonical_task_success') is not None:
        task = 'PASS' if data['canonical_task_success'] else 'FAIL'
    elif data.get('canonical_task_status') in ('PASS','FAIL','NOT_RUN'):
        task = data['canonical_task_status']
    analysis = 'NOT_ASSESSED'
    if data.get('model_task_success') is not None:
        analysis = 'MODEL_PREDICTS_PASS' if data['model_task_success'] else 'MODEL_PREDICTS_FAIL'
    if tool_id.endswith(('pcc_jacobian', 'analyze_pcc', 'analyze_design')) and status == 'completed':
        analysis = 'LOCAL_GEOMETRY_ONLY'
    if tool_id.endswith(('saved_trajectory','diagnose_trajectory')) and status == 'completed':
        analysis = 'SAMPLED_DIAGNOSTIC_RULES'
    message = result.get('message') or ''
    err = error_info(message, result.get('failure_code') or 'TOOL_ERROR') if status != 'completed' else None
    # Dispatch completion and a failed solver are independent states.
    if data.get('complete') is False:
        err = error_info(str(data.get('reason', 'Numerical rollout incomplete; inspect partial evidence')), 'SOLVER_INCOMPLETE')
    summary=message or f'{tool_id}: execution={status}; solver={solver}; analysis={analysis}; task={task}'
    if status=='completed' and data.get('tip_jacobian_m_per_rad') is not None:
        summary=f"Local PCC geometry: tip={data.get('tip_m')} m; 3x2 Jacobian in m/rad. No task evaluation."
    elif status=='completed' and data.get('video_ref'):
        summary=f"Saved video: {data['video_ref']}; {data.get('t_start_s')}–{data.get('t_end_s')} s. Zero dynamics solves; reference received, frames not viewed."
    elif analysis=='SAMPLED_DIAGNOSTIC_RULES':
        summary=f"Saved samples: {len(data.get('queries',[]))} entity summaries, {len(data.get('events',[]))} rule events. Read details for phases, thresholds and hypotheses; no task evaluation."
    return PublicResult(tool_id=tool_id, call_id=call_id, caller=Caller.model_validate(caller),
        execution_status=status, solver_status=solver, analysis_status=analysis, task_status=task,
        summary=summary[:1200],
        error=err, evidence=list(evidence), cost=cost or {}, details_ref=details_ref,
        provenance={**(provenance or {}),'raw_failure_code':result.get('failure_code'),'raw_solver_status':raw_solver}, epistemics=dict(
            observations='Only hash-linked saved numerical samples or direct analytic computation are facts of this model.',
            inference='Model predictions and diagnostic rule interpretations are not physical validation.',
            unverified=['Causal attribution and physical calibration unless separately evidenced.'],
            visual_access='reference_only' if 'video_ref' in data else 'not_applicable')).model_dump(mode='json')


def runner_feedback(book, runtime, name, result, ref, *, before=None, elapsed_s=None, decision_index=-1):
    decision=book.state.get('decisions', [{}])[decision_index] if book.state.get('decisions') else {}
    origin = decision.get('origin',getattr(book, 'decision_origin', 'legacy_unknown'))
    caller = dict(actor_id=origin, origin='agent' if origin == 'deepseek_api' else 'development' if origin == 'codex_development' else 'legacy_unknown',
                  transport='legacy_runner', model_request_index=getattr(book, 'current_model_row', {}).get('index') if getattr(book, 'current_model_row', None) else None)
    caller = decision.get('caller') or getattr(book, 'public_caller', None) or caller
    registry = book.state['evidence']
    refs = [dict(ref=ref, role='detail')]
    proposal=decision.get('proposal',decision)
    for item in proposal.get('evidence',[]) if isinstance(proposal,dict) else []:
        if item in registry:
            refs.append(dict(ref=item,sha256=registry[item]['sha256'],role='input'))
    data = result.get('data', {})
    for key, value in data.items():
        if key.endswith('_ref') and isinstance(value, str) and value in registry:
            refs.append(dict(ref=value, sha256=registry[value]['sha256'], role='output'))
    used = getattr(book, 'ledger', {}).get('used', {})
    charged = {k: v-before.get(k, 0) for k, v in used.items()} if before is not None else {}
    return normalize(runtime+'.'+name, result, call_id=ref, caller=caller, evidence=refs,
        details_ref=ref, cost=dict(charged=charged, elapsed_s=elapsed_s, billing_owner=runtime,
            accounting='Existing reservations are authoritative; no extra backend or model charges from normalization.'),
        provenance=dict(legacy_status=result.get('status'), run_root=str(book.root),
                        arguments=proposal.get('arguments',{}) if isinstance(proposal,dict) else {},
                        implementation_hashes=_implementation_hashes(runtime,name),
                        source_semantics='Existing receipts remain unchanged; public metadata is additive.'))


def _implementation_hashes(runtime,name):
    from tools.spec_tools import ROOT
    from tools.artifact_tools import file_hash
    paths=['tools/public_feedback.py','schemas/public_tools.py',
           'tools/dynamic_campaign.py' if runtime=='dynamics' else 'tools/workbench.py']
    if name in ('analyze_pcc','analyze_design'):
        paths+=['tools/pcc_math.py','tools/public_services.py']
    return {p:file_hash(ROOT/p) for p in paths}
