"""Host-backed, typed admission operations with retained failure evidence."""
from pathlib import Path
import os
import subprocess
import time
from schemas.platform import SessionInput
from schemas.soromox_pilot import Feedback, WorkerInput, WorkerOutput
from tools.platform_store import plain
from tools.state_io import digest, atomic_json, read
from tools.spec_tools import ROOT
from extensions.tendon_family.generated_serial import dimensions


def specification(case):
    return read(ROOT/'examples/soromox'/('case_'+case+'.json'))


def preflight(inp, args, reg):
    if inp.run_id != 'soromox-pilot-20261010':
        raise ValueError('SOROMOX_PILOT_FRESH_ACTIVITY_REQUIRED')
    return {}


def admission(ctx):
    state = ctx.store.session(ctx.run_id)['state']
    if 'soromox_freeze' not in state:
        raise ValueError('COMMITTED_IMPLEMENTATION_FREEZE_REQUIRED')
    if time.time() >= state['soromox_cutoff_unix']:
        raise ValueError('DELIVERY_RESERVE_NO_NUMERICAL_DISPATCH')
    if state.get('soromox_admission'):
        ref = state['soromox_admission']
        return ctx.artifact(ref), ref
    if state.get('soromox_numerical_pending'):
        raise ValueError('UNCONFIRMED_NUMERICAL_OUTCOME_INSPECT_FILES_NO_AUTOMATIC_REPEAT')
    timeout = 900.
    if state['soromox_numerical_s']+timeout > 7200. or time.time()+timeout >= state['soromox_cutoff_unix']:
        raise ValueError('NUMERICAL_BUDGET_CANNOT_FIT_ADMISSION')
    interpreter = Path(state['soromox_python'])
    if not interpreter.is_file():
        raise ValueError('ISOLATED_PILOT_INTERPRETER_MISSING')
    request = WorkerInput(configuration=plain(ctx.input), dimensions=dimensions(ctx.input),
        implementation=state['soromox_freeze'])
    inp, out = ctx.folder/'worker_input.json', ctx.folder/'worker_output.json'
    atomic_json(inp, plain(request))
    with ctx.store.transaction() as db:
        current = ctx.store.session(ctx.run_id, db)['state']
        current['soromox_numerical_pending'] = dict(input=str(inp), output=str(out), reserved_s=timeout)
        ctx.store.update_state(db, ctx.run_id, current)
    env = os.environ.copy()
    env.update(JAX_ENABLE_X64='true', JAX_PLATFORMS='cpu')
    env['PATH'] = str(interpreter.parent/'Library/bin')+os.pathsep+env.get('PATH', '')
    started = time.perf_counter()
    # Timeout retains the pending identity. No optimizer or backend is retried.
    process = subprocess.run([str(interpreter), '-m', 'tools.soromox_worker', str(inp), str(out)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    elapsed = time.perf_counter()-started
    log = ctx.save_artifact(process.stdout, 'soromox_worker_log')
    if process.returncode == 0 and out.is_file():
        result = plain(WorkerOutput.model_validate(read(out)))
    else:
        result = plain(WorkerOutput(gate='check_failed', reasons=['Worker failed before complete admission; inspect retained log'],
            checks={'returncode': process.returncode}, costs_s={'worker_total': elapsed}, versions={}, sources={}))
    result.update(process_elapsed_s=elapsed, log_reference=plain(log), implementation=request.implementation)
    ref = ctx.save_artifact(result, 'soromox_admission')
    with ctx.store.transaction() as db:
        current = ctx.store.session(ctx.run_id, db)['state']
        current['soromox_numerical_s'] += elapsed
        current.pop('soromox_numerical_pending', None)
        current['soromox_admission'] = plain(ref)
        ctx.store.update_state(db, ctx.run_id, current)
    return result, plain(ref)


def packet(ctx, args, operation):
    evidence, ref = admission(ctx)
    spec = specification(args.case)
    state = ctx.store.session(ctx.run_id)['state']
    checks = evidence['checks']
    mismatch = checks.get('basis_mismatch', {})
    residuals = [dict(name=mismatch.get('variable'), normalized_arc_s=.25, time_s=None,
        value=mismatch.get('max_abs_basis_error'), units='basis coefficient', status='incompatible_strain_field')]
    candidate = None
    reason = '; '.join(evidence['reasons'])
    if operation == 'replay':
        candidate = digest(ctx.artifact(args.candidate))
        reason = 'No admitted dynamics or optimized candidate exists; the referenced artifact cannot qualify for replay. '+reason
    return Feedback(problem_identity=digest(spec), model_identity=digest(dict(robot=plain(ctx.input.robot), versions=evidence['versions'])),
        implementation_identity=state['soromox_freeze'], candidate_identity=candidate,
        evidence_identity=ref['artifact_id'], operation=operation, case=args.case,
        status=evidence['gate'] if operation=='describe' else 'entry_gate_rejected' if operation=='solve' else 'candidate_rejected',
        termination_reason=reason, design_values=spec['design'], largest_residuals=residuals,
        derivative_check=dict(mapping_status='passed' if checks.get('exact_mapping_passed') else 'failed_or_incomplete',
            scope='partial derivatives of source-geometry tip/tendon map; no mechanics or reoptimized optimum sensitivity',
            objective_gradient=checks.get('objective_gradient', 'not_run'), constraint_jacobian=checks.get('constraint_jacobian', 'not_run'),
            mechanics='not_established'),
        replay=dict(status='not_run', reason='model admission failed', discrepancies=None),
        consumption=dict(numerical_s=state['soromox_numerical_s'], nlp_solves=0, closed_loop_launches=0,
                         requested_initialization=getattr(args, 'initialization', None)),
        remaining_budget=dict(store=ctx.store.remaining(), numerical_s=max(0., 7200.-state['soromox_numerical_s']),
            nlp_primary=4, nlp_additional=2, closed_loop=2, eligible_to_dispatch=False,
            activity_s=max(0., state['soromox_cutoff_unix']+1800.-time.time())), full_artifacts=[ref])


def describe(ctx, args):
    return packet(ctx, args, 'describe')


def solve(ctx, args):
    return packet(ctx, args, 'solve')


def replay(ctx, args):
    return packet(ctx, args, 'replay')
