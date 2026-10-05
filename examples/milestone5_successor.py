"""Linked continuation; historical fullscope receipts and roots stay immutable."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from examples import milestone5_fullscope as previous
from tools.platform_store import Store,encode,zero
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from examples.milestone5_future_validation import SimpleContext

RUN=ROOT/'runs/milestone5_successor_20261005'
EVIDENCE=ROOT/'evidence/milestone5_successor_20261005'
PAST=read(previous.RUN/'accounting.json')['new_campaign']
REMAINING={k:previous.TOTAL[k]-PAST[k] for k in previous.TOTAL}
BATCH=previous.BATCH
DEVELOPMENT={k:REMAINING[k]-3*BATCH[k] for k in REMAINING}


def predecessor_hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for root in (previous.RUN,previous.EVIDENCE) for p in root.rglob('*')
        if p.is_file() and not p.name.endswith(('-wal','-shm'))}


def check_previous():
    previous.check_previous()
    assert predecessor_hashes()==read(RUN/'plan.json')['predecessors'],'SEALED_PREDECESSOR_CHANGED'


def prepare():
    if (RUN/'plan.json').exists():check_previous();return
    store=Store(RUN);store.create(dict(project_id='m5-successor-20261005',grant_id='m5-successor-development',budget=DEVELOPMENT,
        authorization_source='Direct user attachment 8ce90352-a8fa-40f1-8eb2-32f3e6cf85b0; shared fullscope envelope, authorized implementation/DeepSeek/conditional independent validation/normal push. Scientific target changes need explicit approval.'))
    with store.transaction() as db:
        limits=dict(local_solves=100,prediction_evaluations=96,preview_attempts=8,component_evaluations=100)
        db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=limits,used={k:0 for k in limits})),))
    plan=dict(version='m5_successor_plan@1.0.0',starting_commit='c848fea82856971777397d83fa95330d8c50a6c5',
        shared_envelope=previous.TOTAL,fullscope_actual_charges=PAST,remaining_envelope=REMAINING,
        development_allocation=DEVELOPMENT,protected_validation=[dict(batch=i,limit=BATCH,grant_created=False) for i in (1,2,3)],
        protected_final_interpretation_export_s=1265.,predecessors=predecessor_hashes(),
        thresholds=read(previous.RUN/'plan.json')['thresholds'],development_cases=read(previous.RUN/'plan.json')['development_cases'],
        incumbent=read(previous.RUN/'plan.json')['incumbent'],historical_NO_GO_preserved=True,
        runtime_check='Verified once before successor preparation: existing softagent Python 3.11.16, CasADi 3.7.2, SciPy 1.17.1, NumPy 2.4.6, MuJoCo 3.13.0.',
        credential_location='Requested $HOME/.codex.env is absent. Reuse existing loader and verified $HOME/.codex/.env; no credentials in evidence.',
        work=['A: quantify existing six-case numerical targets without new integrations; preserve original gate pending any explicitly approved semantic/reference change.',
            'B: trace earliest feedback divergence; implement and benchmark evidence-backed component/runtime improvements before full forecasts.',
            'C: retain both original and reset histories, original tolerances, causal candidate histories, feasibility-qualified decisions and full costs; native research assessment.',
            'D: only if unchanged or explicitly approved development gates and complete-update timing pass, freeze two untouched pairs and independent repeat; six independent backends maximum.'],
        scope_rules='No implicit tolerance/plant/objective/constraint change; no replacement after frozen validation STOP. Version controller changes and measure changed behavior. No arbitrary revision-count endpoint; each next hypothesis needs evidence, bounded workload and funds.',
        accounting='Only fullscope plus successor use this envelope; lifetime totals are separate. Numerical/provider failures charged. Offline code/inspection/export retain established engineering convention.',
        workers=0,subagents=0)
    atomic_json(RUN/'plan.json',plan);atomic_json(RUN/'plan_seal.json',dict(identity=digest(plan),before_new_numerical_work=True))


def session(name):
    prepare();h=Host(RUN,'m5successor-'+name)
    with h.store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
    if exists:return h
    old=Store(previous.RUN).session('m5full-research')['snapshot']['input'];cfg=deepcopy(old);cfg['run_id']=h.run_id
    cfg['policy']['budget']=DEVELOPMENT;h.create(cfg);return h


def calculate(name,operation,reserve_s):
    h=session(name);old=h.store.lookup(h.run_id,name)
    if old:
        assert old['receipt'],'PENDING_NO_REPLAY'
        receipt=json.loads(old['receipt']);assert receipt['execution_status']=='completed','FAILED_NO_REPLAY'
        return h.store.artifact(receipt['output'])
    assert h.store.remaining()['remaining']['wall_s']>=reserve_s+1265.,'FINALIZATION_RESERVED'
    row,_=h.store.reserve(h.run_id,name,digest(dict(operation=name,plan=digest(read(RUN/'plan.json')))),h.actor,{**zero(), 'tool_calls':1,'wall_s':reserve_s})
    ctx=SimpleContext(h,row);start=time.monotonic()
    try:
        phase_plan=RUN/(name+'_plan.json')
        ctx.save_artifact(dict(operation=name,phase_plan=read(phase_plan) if phase_plan.exists() else None,
            implementation_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                'examples/milestone5_successor.py','extensions/tendon_family/milestone5_fast_kernel.py',
                'extensions/tendon_family/milestone5_fixed_transition.py','extensions/tendon_family/milestone5_feedback_runtime.py',
                'extensions/tendon_family/gvs_trajectory.py')}), 'calculation_inputs_frozen')
        result=operation(ctx);error=None;status='completed'
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc));result=dict(error=error);status='failed'
    elapsed=time.monotonic()-start
    atomic_json(RUN/(name+'_completion_pending.json'),dict(result=result,status=status,elapsed_s=elapsed,error=error))
    receipt=h.store.complete(row,dict(request_id=name,execution_id=row['execution_id'],caller=h.actor,
        tool_id='analysis.milestone5_successor',tool_version='1.0.0',execution_status=status,charged=zero(),error=None if error is None else json.dumps(error)),result,elapsed)
    atomic_json(RUN/(name+'.json'),result);atomic_json(RUN/(name+'_receipt.json'),receipt);check_previous()
    print(json.dumps(dict(operation=name,status=status,charged=receipt['charged'])),flush=True)
    if error:raise RuntimeError(error)
    return result


def numerical_targets(ctx):
    continuous=read(previous.RUN/'revision1_local.json');discrete=read(previous.RUN/'revision2_local.json');cases=[]
    def difference(a,b):
        return dict(position_m=float(np.linalg.norm(np.asarray(a['position_m'])-b['position_m'])),
            vector_m_s=float(np.linalg.norm(np.asarray(a['velocity_m_s'])-b['velocity_m_s'])),speed_m_s=abs(a['speed_m_s']-b['speed_m_s']))
    for a,b in zip(continuous['cases'],discrete['cases']):
        for k in ('case','initial_state','input_n','observed_endpoint'):assert a[k]==b[k],k
        r1=a['results'];r2=b['results'];truth=a['observed_endpoint']
        cases.append(dict(case=a['case'],source=a['source'],update_id=a['update_id'],
            current_full_state_identity=digest(a['initial_state']),input_n=a['input_n'],interval_s=[a['update_id']*.01,(a['update_id']+1)*.01],
            original_reduced_mapping_error=dict(position_m=a['initial_reduced_position_error_m'],vector_m_s=a['initial_reduced_vector_error_m_s']),
            full_state_mapping_error_m=0.,continuous_to_backend=difference(r1[-1],truth),
            fixed_discrete_to_backend=difference(r2[0],truth),
            refined_discrete_to_continuous=[dict(step_s=r['step_s'],difference=difference(r,r1[-1])) for r in r2],
            continuous_successive_differences=a['numerical_differences'],discrete_successive_differences=b['numerical_differences'],
            maximum_continuous_scaled_residual=max(r['max_scaled_residual'] for r in r1),maximum_discrete_scaled_residual=max(r['max_scaled_residual'] for r in r2),
            original_scores=dict(R1=a['score'],R2=b['score'])))
    result=dict(version='m5_target_audit@1.0.0',cases=cases,source_identities={n:digest(read(previous.RUN/n)) for n in ('revision1_local.json','revision2_local.json','plan.json')},
        targets=dict(accuracy='Observed frozen implicitfast .0005-second backend transition over .01 s, world tip outputs at endpoint under fixed actual input.',
            continuous_resolution='Convergence of the independent continuous serial ODE, tested by Radau tolerances/max steps.',
            discrete_resolution='Changing the recurrence step changes the finite-step transition being emulated, rather than only the linear-algebra solution accuracy at a fixed transition.',
            reconstruction='Full serial state and common world-frame output; reduced lift can discard modes. No projection defect is implied.',
            residual='Scaled algebraic force-balance equation error, separate from time-discretization error and physical task position limit.'),
        conclusion='Saved data identify backend discretization as the remaining full-state continuous-versus-backend difference in these cases. They do not prove impossibility of all predictors or justify mixing passes from R1 and R2.',
        proposed_scientific_decision=dict(status='pending_user_decision',
            recommended='Explicitly target the existing fixed .0005 s backend transition. Keep all physical prediction tolerances, plant, task and backend unchanged. Replace temporal refinement of this fixed discrete map with preregistered two-successive independent algebraic-accuracy/refinement checks at fixed h, residual <=1e-5 and output speed/vector <=1e-4; preserve time-step sensitivity as a separate mandatory limitation.',
            change='This changes the meaning of the previous successive-time-resolution gate for the discrete predictor and requires explicit user approval. No such pass is claimed now.',
            alternative='Keep continuous-limit target and original temporal refinement; separately approve changing backend/reference construction and validate its numerical convergence before using it as new truth.',
            unchanged_option='Retain both existing targets and gates; continue performance work but no admission claim from R1 or R2.'),
        new_integrations=0,new_controller_solves=0,new_backend_evaluations=0)
    ctx.save_artifact(result,'numerical_targets_assessed');return result


def freeze_kernel_probe():
    prepare();path=RUN/'kernel_probe_plan.json'
    if path.exists():return
    plan=dict(version='gvs_scalar_force_kernel@1.0.0',hypothesis='Saved matched IPOPT Jacobians take .212-.213 s per call and dominate solve time; a single-step scalar CasADi evaluation may remove interpreter graph overhead without changing the equation.',
        evidence='Fullscope matched diagnostics: Jacobian 7.648/8.585 s and 6.173/6.872 s of optimization; warm generation similarly differentiates the same dynamics.',
        change='Expand only the existing force-balance kernel to SX, retaining cell function boundaries. No whole-horizon expansion, solver migration, physics or acceptance change.',
        decisive_comparison='Six registered development current states and current applied inputs, acceleration fixed to zero: compare original and scalar force residual plus exact full argument Jacobian. Residual difference <=1e-10, relative Jacobian difference <=1e-8. Measure cold construction separately.',
        workload=dict(force_and_jacobian_point_evaluations=12,complete_controller_solves=0,backend_steps=0,reserve_s=600.),
        continuation='Only if equivalent and materially faster, integrate into a versioned workspace and measure actual warm regeneration/complete controller updates; no claim from kernel timings.',
        target_decision_dependency=False)
    atomic_json(path,plan);atomic_json(RUN/'kernel_probe_seal.json',dict(identity=digest(plan)))


def kernel_probe(ctx):
    from schemas.platform import SessionInput
    from schemas.platform_math import SystemContext
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs import GVSModel
    from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
    from extensions.tendon_family.gvs_profile import reach_numerical
    from extensions.tendon_family.milestone5_fast_kernel import scalar_kernel,evaluate_pair
    from extensions.tendon_family.diagnostic_math import charge_units
    r,s=previous.source('original075');inp=SessionInput.model_validate(s['configuration']);num=reach_numerical(inp)
    p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis']);start=time.perf_counter()
    functions=functions_for(expression_from_system(GVSModel(p).build_system(inp.robot,p,None,SystemContext(
        x0=num['nominal']['q0']+[0.]*len(num['nominal']['q0']),u0=num['nominal']['u0'],scene=inp.task.environment))))
    baseline_setup=time.perf_counter()-start;kernel=scalar_kernel(functions);cases=[]
    ctx.save_artifact({k:v for k,v in kernel.items() if k not in ('function','jacobian')},'scalar_kernel_constructed')
    for case in read(RUN/'plan.json')['development_cases']:
        r,s=previous.source(case['source']);o=r.read_file(s,'controller_observations.json')[case['update_id']]
        charge_units(ctx,'component_evaluations',2)
        result=evaluate_pair(functions,kernel,o['measured_initial_state'],o['actual_tension_n'],[0.]*functions.q_symbol.numel())
        result.update(case=case['case'],state=o['measured_initial_state'],input_n=o['actual_tension_n'])
        ctx.save_artifact(result,'force_kernel_comparison');cases.append(result)
        print(json.dumps(dict(case=case['case'],equivalent=result['equivalent'],speedup=result['speedup'])),flush=True)
    return dict(cases=cases,baseline_setup_s=baseline_setup,kernel={k:v for k,v in kernel.items() if k not in ('function','jacobian')},
        all_equivalent=all(c['equivalent'] for c in cases),median_speedup=float(np.median([c['speedup'] for c in cases])),
        complete_update_measured=False,scientific_target_unchanged=True)


def approve_fixed_target():
    prepare();path=RUN/'fixed_target_protocol.json'
    if path.exists():return
    protocol=dict(version='fixed_backend_transition_validation@2.0.0',supersedes_only='Successor local numerical gate; historical fullscope audits and rules remain immutable.',
        authorization='Direct user reply to request_user_input_async: approve existing fixed .5 ms backend transition target, separate version; no invented two-level tolerance for direct solves; use residual/independent implementation/error checks; retain original accuracy/physics and all other gates.',
        physical_step_s=.0005,local_duration_s=.01,initial_state='Same saved full serial state for each original six cases',input='Same actual current input held over interval',
        outputs='World tip position, speed, velocity at identical endpoint; no future endpoint supplied to predictor',
        equation='(M(q)+h*C)*a=f(q,v,u); v_next=v+h*a; q_next=q+h*v_next',
        original_implementation='Saved R2 NumPy general direct LU results at .0005 s, reused without recomputation',
        independent_implementation='SciPy Cholesky SPD factorization and triangular solves; own propagation from same initializer and input, same point mechanics',
        numerical_checks=['All finite and SPD factorization succeeds at all 20 steps; scaled equation residual <=1e-5 at every step.',
            'Normwise backward error <=1e-12 at every step; report condition estimate and inverse-norm residual acceleration error estimate (local linear algebra only, not rigorous global propagation/physical bound).',
            'Independent Cholesky endpoint versus saved LU endpoint satisfies original 1e-6 m position and 1e-4 m/s speed/vector tolerances.',
            'Predicted endpoint versus saved observed backend endpoint independently satisfies those same tolerances; report original direction and all threshold classifications.'],
        no_fictitious_refinement='No adjustable iterative tolerance exists in either direct solve. No repeated identical solve or two fake tolerance levels.',
        sensitivity='Retain all old physical-step .0005/.00025/.000125 results and R1 continuous reference separately; discretization bias is not removed or excused.',
        scope='Numerical reproduction of fixed-step simulation transition only; no continuous/hardware correctness, cheap reduced-model claim, independent validation or milestone closure.',
        workload=dict(new_local_propagations=6,reservation_s=90.,new_complete_forecasts=0,new_backend_evaluations=0))
    atomic_json(path,protocol);atomic_json(RUN/'fixed_target_seal.json',dict(identity=digest(protocol),before_new_fixed_target_work=True))


def fixed_target_validation(ctx):
    from extensions.tendon_family.milestone5_fullstate import DiscreteFullState
    from extensions.tendon_family.milestone5_fixed_transition import predict
    from extensions.tendon_family.milestone5_campaign_assessment import score
    from extensions.tendon_family.diagnostic_math import charge_units
    cases=[];start=time.perf_counter()
    for old in read(previous.RUN/'revision2_local.json')['cases']:
        r,s=previous.source(old['source']);model=DiscreteFullState(s['configuration'],r.read_file(s,'resolved_physics.json'),
            r.read_file(s,'compiled_physics.json'),r.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
        charge_units(ctx,'prediction_evaluations',1)
        result=predict(model,old['initial_state'],old['input_n'],deadline=start+80.)
        ctx.save_artifact(dict(case=old['case'],result=result,protocol_identity=digest(read(RUN/'fixed_target_protocol.json'))),'fixed_transition_prediction_sealed')
        lu=old['results'][0];differences=dict(position_m=float(np.linalg.norm(np.asarray(result['position_m'])-lu['position_m'])),
            vector_m_s=float(np.linalg.norm(np.asarray(result['velocity_m_s'])-lu['velocity_m_s'])),speed_m_s=abs(result['speed_m_s']-lu['speed_m_s']))
        numerical=differences['position_m']<=1e-6 and max(differences['vector_m_s'],differences['speed_m_s'])<=1e-4
        scored=score(result,old['initial'],old['observed_endpoint'],old['initial'],old['update_id']*.01,numerical,differences['speed_m_s'])
        scored['speed_false_unsafe']=result['speed_m_s']>.02>=old['observed_endpoint']['speed_m_s']
        cases.append(dict(case=old['case'],result=result,numerical_pass=numerical,independent_solver_difference=differences,score=scored))
    return dict(protocol_identity=digest(read(RUN/'fixed_target_protocol.json')),cases=cases,
        counts={k:sum(c['score'][k] for c in cases) for k in ('position_pass','speed_pass','vector_pass','direction_resolved','direction_correct','speed_false_safe','speed_false_unsafe')},
        numerical_passes=sum(c['numerical_pass'] for c in cases),backend_attempts=0,new_local_propagations=6,
        target='Approved fixed .5 ms simulation transition; not continuous physics',old_sensitivity_reused=True)


def compiler_setup(ctx):
    import urllib.request
    import zipfile
    metadata=json.loads((RUN/'compiler_release.json').read_text(encoding='utf-8-sig'))
    atomic_json(RUN/'compiler_release.json',metadata)
    destination=RUN/'toolchain';destination.mkdir(exist_ok=True);archive=destination/metadata['name']
    if not archive.exists():
        with urllib.request.urlopen(metadata['browser_download_url'],timeout=60.) as response,archive.open('wb') as out:
            while block:=response.read(1024*1024):out.write(block)
    actual=hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual!=metadata['digest'].split(':',1)[1]:raise ValueError('OFFICIAL_COMPILER_DIGEST_MISMATCH')
    with zipfile.ZipFile(archive) as bundle:
        root=destination.resolve()
        for member in bundle.infolist():
            if not (root/member.filename).resolve().is_relative_to(root):raise ValueError('TOOLCHAIN_ARCHIVE_PATH')
        bundle.extractall(root)
    compiler=destination/metadata['name'].removesuffix('.zip')/'bin/clang.exe'
    assert compiler.is_file()
    return dict(compiler=str(compiler),release=metadata,archive_sha256=actual,
        existing_python_environment_unchanged=True,scope='Portable task-local C compiler; no installation, PATH or security setting changes.')


def freeze_native_probe():
    prepare();path=RUN/'native_probe_plan.json'
    if path.exists():return
    scalar=read(RUN/'kernel_probe.json');assert scalar['all_equivalent'] and scalar['median_speedup']<1.
    plan=dict(version='gvs_native_force_kernel@1.0.0',hypothesis='Scalar expansion was equivalent but slower (median speedup .556). Exact native code for the force balance and AD Jacobian targets measured interpreter/graph evaluation cost without changing equations.',
        source='CasADi 3.7.2 existing MX function and exact jacobian()',compiler=read(RUN/'compiler_release.json'),
        options=['-O2','-fno-fast-math','-shared'],environment='Task-local portable compiler; installed Conda packages unchanged.',
        workload=dict(builds=1,native_points=6,baseline_reused='Saved original evaluations in kernel_probe.json at identical states/inputs and zero acceleration',reserve_s=1200.),
        criteria=dict(residual_difference=1e-10,relative_jacobian_difference=1e-8,performance='Measure native force+Jacobian including Python call boundary; only proceed to full update if useful.'),
        charging='Compilation/download are charged campaign setup; operational candidate work and any amortization will be explicit. Kernel time never counts as full-update time.')
    atomic_json(path,plan);atomic_json(RUN/'native_probe_seal.json',dict(identity=digest(plan)))


def native_probe(ctx):
    from schemas.platform import SessionInput
    from schemas.platform_math import SystemContext
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs import GVSModel
    from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
    from extensions.tendon_family.gvs_profile import reach_numerical
    from extensions.tendon_family.milestone5_fast_kernel import build_native,evaluate_native
    from extensions.tendon_family.diagnostic_math import charge_units
    _,s=previous.source('original075');inp=SessionInput.model_validate(s['configuration']);num=reach_numerical(inp)
    p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
    functions=functions_for(expression_from_system(GVSModel(p).build_system(inp.robot,p,None,SystemContext(
        x0=num['nominal']['q0']+[0.]*len(num['nominal']['q0']),u0=num['nominal']['u0'],scene=inp.task.environment))))
    kernel=build_native(functions,RUN/'native_kernel',read(RUN/'compiler_setup.json')['compiler']);cases=[]
    ctx.save_artifact({k:v for k,v in kernel.items() if k not in ('function','jacobian')},'native_kernel_built')
    for old in read(RUN/'kernel_probe.json')['cases']:
        charge_units(ctx,'component_evaluations',1)
        result=evaluate_native(kernel,old['state'],old['input_n'],[0.]*functions.q_symbol.numel());original=old['evaluations'][0]
        dr=float(np.max(abs(np.asarray(result['residual'])-original['residual'])))
        dj=float(np.max(abs(np.asarray(result['jacobian'])-original['jacobian'])))
        scale=max(float(np.max(abs(np.asarray(original['jacobian'])))),1.)
        row=dict(case=old['case'],result=result,residual_difference=dr,relative_jacobian_difference=dj/scale,
            equivalent=dr<=1e-10 and dj/scale<=1e-8,speedup=original['evaluation_s']/max(result['evaluation_s'],1e-12),baseline=original['evaluation_s'])
        cases.append(row);ctx.save_artifact(row,'native_force_comparison');print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    return dict(kernel={k:v for k,v in kernel.items() if k not in ('function','jacobian')},cases=cases,
        all_equivalent=all(c['equivalent'] for c in cases),median_speedup=float(np.median([c['speedup'] for c in cases])),complete_update_measured=False)


def feedback_audit(ctx):
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.gvs_projection import project
    cases=[]
    for name in ('original075','original15','reset075','reset15'):
        r,s=previous.source(name);observations=r.read_file(s,'controller_observations.json');physics=r.read_file(s,'resolved_physics.json')
        inp=SessionInput.model_validate(s['configuration']);basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
        h=read(previous.RUN/f'forecast_{name}.json');differences=[float(np.max(abs(np.asarray(row['input_n'])-o['actual_tension_n']))) for row,o in zip(h['rows'],observations)]
        first=next(i for i,e in enumerate(differences) if e>1e-9);rows=[]
        for i in range(first+2):
            p=h['rows'][i];o=observations[i];full=np.asarray(p['initial_full_state']);n=len(full)//2
            z=project(physics,basis,full[:n],full[n:]);predicted=z['q_gvs']+z['qdot_gvs']
            actual=o['measured_initial_state']
            rows.append(dict(update_id=i,time_s=o['time_s'],predicted_current_reduced_state=predicted,observed_current_reduced_state=actual,
                state_max_difference=float(np.max(abs(np.asarray(predicted)-actual))),
                previous_input_max_difference_n=None if i==0 else float(np.max(abs(np.asarray(h['rows'][i-1]['input_n'])-observations[i-1]['actual_tension_n']))),
                predicted_input_n=p['input_n'],actual_input_n=o['actual_tension_n'],command_max_difference_n=differences[i],
                predictor_replanned=p['replanned'],predictor_plan_start_s=p['plan_start_s'],predictor_plan_identity=p['plan_identity'],
                production_horizon=o['effective_horizon'],production_selected_iteration=o['optimization_selected_iteration'],production_stop=o['policy_stop_reason'],
                production_update_s=o['update_wall_s'],production_warm_preparation_s=o['warm_preparation_s']))
        cases.append(dict(candidate=name,first_divergence_update=first,rows=rows,
            saved_plan_limit='Complete early historical selected and warm plans were not exported; one-step predictions, current states, actual commands and selection reasons are available. Do not fabricate warm-plan identity.',
            hypothesis='When current state and previous input match but no preview replan is performed, held plan continuation cannot reproduce the production feedback decision. Evaluate exact every-update feedback with its own causal history after component acceleration.'))
    result=dict(cases=cases,new_solves=0,new_integrations=0,proposed_rule='Every configured control update, throughout transient and holding; no retrospectively selected trigger timestamp.',
        operating_constraint='An exact every-update full-order emulation is only a diagnostic reference until measured full cost and independent feasibility-qualified validation support operational use.')
    ctx.save_artifact(result,'earliest_feedback_divergence_assessed');return result


def native_o0_probe(ctx,optimized=False,reverse=False):
    from extensions.tendon_family.milestone5_fast_kernel import compile_existing,evaluate_native
    from extensions.tendon_family.diagnostic_math import charge_units
    if reverse in ('chunked','full-chunked'):
        from extensions.tendon_family.milestone5_fast_kernel import build_native_chunked
        kernel=build_native_chunked(RUN/('native_kernel' if reverse=='full-chunked' else 'native_reverse'),read(RUN/'compiler_setup.json')['compiler'],full_jacobian=reverse=='full-chunked')
    elif reverse in ('split','shared'):
        from extensions.tendon_family.milestone5_fast_kernel import build_native_split
        kernel=build_native_split(RUN/'native_reverse',read(RUN/'compiler_setup.json')['compiler'],shared_runtime=reverse=='shared')
    elif reverse=='mixed':
        from extensions.tendon_family.milestone5_fast_kernel import build_native_mixed
        kernel=build_native_mixed(RUN/'native_reverse',read(RUN/'compiler_setup.json')['compiler'])
    elif reverse=='optimized':
        kernel=compile_existing(RUN/'native_reverse',read(RUN/'compiler_setup.json')['compiler'],source_name='force_reverse',optimization='-O1',extra_flags=('-fno-inline','-ftime-trace'),timeout_s=900.)
        kernel['version']='gvs_native_reverse_kernel@1.2.0'
    elif reverse=='reuse':
        kernel=compile_existing(RUN/'native_reverse',read(RUN/'compiler_setup.json')['compiler'],source_name='force_reverse',timeout_s=90.)
        kernel['version']='gvs_native_reverse_kernel@1.1.0'
    elif reverse:
        from extensions.tendon_family.milestone5_fast_kernel import build_native_reverse
        kernel=build_native_reverse(reference_functions(),RUN/'native_reverse',read(RUN/'compiler_setup.json')['compiler'])
    else:
        kernel=compile_existing(RUN/'native_kernel',read(RUN/'compiler_setup.json')['compiler'],
            **(dict(optimization='-O1',timeout_s=360.,extra_flags=('-fno-inline',)) if optimized else {}))
    cases=[]
    if optimized:kernel['version']='gvs_native_force_kernel@1.2.0'
    ctx.save_artifact({k:v for k,v in kernel.items() if k not in ('function','jacobian')},'native_o0_built')
    for old in read(RUN/'kernel_probe.json')['cases']:
        charge_units(ctx,'component_evaluations',1)
        result=evaluate_native(kernel,old['state'],old['input_n'],[0.]*12);original=old['evaluations'][0]
        dr=float(np.max(abs(np.asarray(result['residual'])-original['residual'])))
        dj=float(np.max(abs(np.asarray(result['jacobian'])-original['jacobian'])))
        scale=max(float(np.max(abs(np.asarray(original['jacobian'])))),1.)
        row=dict(case=old['case'],result=result,residual_difference=dr,relative_jacobian_difference=dj/scale,
            equivalent=dr<=1e-10 and dj/scale<=1e-8,speedup=original['evaluation_s']/max(result['evaluation_s'],1e-12),baseline=original['evaluation_s'])
        cases.append(row);ctx.save_artifact(row,'native_o0_force_comparison');print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    return dict(kernel={k:v for k,v in kernel.items() if k not in ('function','jacobian')},cases=cases,
        all_equivalent=all(c['equivalent'] for c in cases),median_speedup=float(np.median([c['speedup'] for c in cases])),complete_update_measured=False)


def reference_functions():
    from schemas.platform import SessionInput
    from schemas.platform_math import SystemContext
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs import GVSModel
    from extensions.tendon_family.gvs_casadi import expression_from_system,functions_for
    from extensions.tendon_family.gvs_profile import reach_numerical
    _,s=previous.source('original075');inp=SessionInput.model_validate(s['configuration']);num=reach_numerical(inp)
    p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
    return functions_for(expression_from_system(GVSModel(p).build_system(inp.robot,p,None,SystemContext(
        x0=num['nominal']['q0']+[0.]*len(num['nominal']['q0']),u0=num['nominal']['u0'],scene=inp.task.environment))))


def mass_form_probe(ctx):
    from extensions.tendon_family.milestone5_fast_kernel import mass_form_kernel
    from extensions.tendon_family.diagnostic_math import charge_units
    start=time.perf_counter();kernel=mass_form_kernel(reference_functions());setup_s=time.perf_counter()-start;cases=[]
    for old in read(RUN/'kernel_probe.json')['cases']:
        charge_units(ctx,'component_evaluations',1);start=time.perf_counter()
        r,j=kernel['jacobian'](np.r_[old['state'],old['input_n'],np.zeros(12)]);elapsed=time.perf_counter()-start
        original=old['evaluations'][0];res=np.asarray(r).ravel();jac=np.asarray(j)
        dr=float(np.max(abs(res-original['residual'])));dj=float(np.max(abs(jac-original['jacobian'])))
        scale=max(float(np.max(abs(np.asarray(original['jacobian'])))),1.)
        row=dict(case=old['case'],result=dict(residual=res.tolist(),jacobian=jac.tolist(),evaluation_s=elapsed),
            residual_difference=dr,relative_jacobian_difference=dj/scale,equivalent=dr<=1e-10 and dj/scale<=1e-8,
            speedup=original['evaluation_s']/elapsed,baseline=original['evaluation_s'])
        cases.append(row);ctx.save_artifact(row,'mass_form_kernel_comparison');print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    return dict(version=kernel['version'],setup_s=setup_s,kernel_construction_s=kernel['construction_s'],cases=cases,
        all_equivalent=all(c['equivalent'] for c in cases),median_speedup=float(np.median([c['speedup'] for c in cases])),complete_update_measured=False)


def feedback_component(ctx,kernel_name='native_reverse_optimized'):
    import casadi as ca
    from extensions.tendon_family.milestone5_feedback_runtime import NativeFunctions,history
    from extensions.tendon_family.milestone5_fullstate import DiscreteFullState
    from extensions.tendon_family.diagnostic_math import charge_units
    from extensions.tendon_family.milestone5_fast_kernel import evaluate_native
    start=time.perf_counter();reference=reference_functions()
    native=read(RUN/(kernel_name+'.json'))['kernel']
    provider=NativeFunctions(reference,native['library'],library_sha256=native['library_sha256']);results=[]
    z=ca.MX.sym('nonzero_acceleration_arguments',42);residual=reference.implicit_residual(z[:24],z[24:30],z[30:])
    exact=ca.Function('nonzero_acceleration_reference',[z],[residual,ca.jacobian(residual,z)],{'ad_weight':1.})
    checks=[]
    for name,index in (('original075',1),('reset075',20)):
        r,s=previous.source(name);observation=r.read_file(s,'controller_observations.json')[index]
        state=observation['measured_initial_state'];u=observation['actual_tension_n']
        acceleration=(np.asarray(observation['one_step_prediction']['state'][12:])-state[12:])/.01
        charge_units(ctx,'component_evaluations',2);expected_r,expected_j=exact(np.r_[state,u,acceleration])
        result=evaluate_native(dict(function=provider.function,jacobian=provider.function.jacobian()),state,u,acceleration)
        dr=float(np.max(abs(np.asarray(result['residual'])-np.asarray(expected_r).ravel())))
        dj=float(np.max(abs(np.asarray(result['jacobian'])-np.asarray(expected_j))))/max(1.,float(np.max(abs(np.asarray(expected_j)))))
        check=dict(candidate=name,update_id=index,acceleration=acceleration.tolist(),force_difference=dr,relative_jacobian_difference=dj,passed=dr<=1e-10 and dj<=1e-8)
        checks.append(check);ctx.save_artifact(check,'native_nonzero_acceleration_check')
        if not check['passed']:raise ValueError('NONZERO_ACCELERATION_EQUIVALENCE_FAILED')
    kernel_setup_and_checks_s=time.perf_counter()-start
    for name,count in (('original075',3),('reset075',2)):
        r,s=previous.source(name);physics=r.read_file(s,'resolved_physics.json');scene=r.read_file(s,'experiment_scene.json')
        model=DiscreteFullState(s['configuration'],physics,r.read_file(s,'compiled_physics.json'),r.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
        result=history(s['configuration'],scene['qpos_rad']+scene['qvel_rad_s'],model,physics,ctx,
            provider=provider,count=count,deadline=time.perf_counter()+210.,
            save_update=lambda row:ctx.save_artifact(dict(candidate=name,**row),'native_feedback_update'))
        # Reference outcomes are read only after the candidate's own sequence.
        observed=r.read_file(s,'controller_observations.json')
        for row,truth in zip(result['rows'],observed):
            row['posthoc_command_difference_n']=float(np.max(abs(np.asarray(row['input_n'])-truth['actual_tension_n'])))
            row['historical_complete_update_s']=truth['update_wall_s']
        result.update(candidate=name,model_setup_s=model.setup_s);results.append(result)
        ctx.save_artifact(result,'native_feedback_component');print(json.dumps(dict(candidate=name,updates=[dict(time_s=x['time_s'],update_s=x['complete_command_s'],warm_s=x['command_receipt']['warm_preparation_s'],difference_n=x['posthoc_command_difference_n']) for x in result['rows']])),flush=True)
    return dict(version='native_exact_every_update@1.0.0',results=results,complete_update_deadline_s=.01,
        realtime=all(x['complete_command_s']<=.01 for r in results for x in r['rows']),complete_forecasts=0,backend_attempts=0,
        nonzero_acceleration_checks=checks,kernel_setup_and_checks_s=kernel_setup_and_checks_s,kernel_name=kernel_name)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True);args=p.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='targets':calculate('numerical_targets',numerical_targets,30.)
    elif args.phase=='kernel-probe':freeze_kernel_probe();calculate('kernel_probe',kernel_probe,600.)
    elif args.phase=='fixed-target':approve_fixed_target();calculate('fixed_target',fixed_target_validation,90.)
    elif args.phase=='compiler-setup':calculate('compiler_setup',compiler_setup,900.)
    elif args.phase=='native-probe':freeze_native_probe();calculate('native_probe',native_probe,1200.)
    elif args.phase=='feedback-audit':calculate('feedback_audit',feedback_audit,30.)
    elif args.phase=='native-o0':
        assert read(RUN/'native_probe_receipt.json')['execution_status']=='failed'
        plan=dict(version='gvs_native_force_kernel@1.1.0',hypothesis='The 81 MB exact derivative source exceeded the O2 compilation cap. Disable optimization to bound build work and measure native call overhead reduction separately; no source or equation change.',source_sha256=hashlib.sha256((RUN/'native_kernel/force_native.c').read_bytes()).hexdigest(),compiler_flags=['-O0','-fno-fast-math','-shared'],compile_cap_s=180.,points=6,baseline='Saved original kernel_probe six identical points',reserve_s=240.)
        if not (RUN/'native_o0_plan.json').exists():atomic_json(RUN/'native_o0_plan.json',plan)
        calculate('native_o0',native_o0_probe,240.)
    elif args.phase=='native-o1':
        old=read(RUN/'native_o0.json');assert old['all_equivalent'] and old['median_speedup']<1.
        plan=dict(version='gvs_native_force_kernel@1.2.0',hypothesis='Native O0 is equivalent but slower; compiler optimization is needed. O1 with inlining disabled bounds the huge generated derivative compilation while retaining local scalar optimizations. Reuse exact C source and baseline.',source_sha256=hashlib.sha256((RUN/'native_kernel/force_native.c').read_bytes()).hexdigest(),compiler_flags=['-O1','-fno-inline','-fno-fast-math','-shared'],compile_cap_s=360.,points=6,reserve_s=420.)
        if not (RUN/'native_o1_plan.json').exists():atomic_json(RUN/'native_o1_plan.json',plan)
        calculate('native_o1',lambda ctx:native_o0_probe(ctx,True),420.)
    elif args.phase.startswith('feedback-component'):
        kernel_name={'':'native_reverse_optimized','-mixed':'native_mixed','-split':'native_split','-shared':'native_shared',
            '-chunked':'native_chunked_repair1','-full-chunked':'native_full_chunked'}[args.phase.removeprefix('feedback-component')]
        k=read(RUN/(kernel_name+'.json'));assert k['all_equivalent'] and k['median_speedup']>1.
        plan=dict(version='native_exact_every_update@1.0.0',hypothesis='Exact native force/Jacobian acceleration enables testing every-update feedback at the earliest original and reset divergences. Complete command and warm/solve/validation costs, not kernel timings, decide realtime. Timed stopping may change controller response and is recorded.',cases=[dict(candidate='original075',updates=3),dict(candidate='reset075',updates=2)],nonzero_acceleration_checks=[dict(candidate='original075',update=1),dict(candidate='reset075',update=20)],nonzero_acceleration_work='Two original and two native residual/Jacobian evaluations; saved current-time one-step controller plans supply acceleration, never used to advance the new candidate history.',native_identity=digest(k),full_forecasts=0,new_backends=0,reserve_s=450.)
        if not (RUN/'feedback_component_plan.json').exists():atomic_json(RUN/'feedback_component_plan.json',plan)
        calculate('feedback_component',lambda ctx:feedback_component(ctx,kernel_name),450.)
    elif args.phase=='native-reverse':
        plan=dict(version='gvs_native_reverse_kernel@1.0.0',hypothesis='Full Jacobian generated 81 MB and both O2/O1 exceeded build caps; exact scalar reverse AD avoids wide derivative code generation. Compile force plus adj1 and assemble exact Jacobian from those native calls.',compiler_flags=['-fintegrated-cc1','-O1','-fno-inline','-fno-fast-math','-shared'],compile_cap_s=180.,points=6,reserve_s=240.,baseline='Saved six original points, no replay')
        if not (RUN/'native_reverse_plan.json').exists():atomic_json(RUN/'native_reverse_plan.json',plan)
        calculate('native_reverse',lambda ctx:native_o0_probe(ctx,reverse=True),240.)
    elif args.phase=='native-reverse-o0':
        plan=dict(version='gvs_native_reverse_kernel@1.1.0',hypothesis='The reduced 16 MB reverse derivative source still exceeded the short optimized compilation cap. Test unoptimized native scalar reverse AD independently of the slow full-Jacobian O0 route. Reuse generated source and original six points.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),compile_cap_s=90.,compiler_flags=['-O0','-fno-fast-math','-shared'],points=6,reserve_s=120.)
        if not (RUN/'native_reverse_o0_plan.json').exists():atomic_json(RUN/'native_reverse_o0_plan.json',plan)
        calculate('native_reverse_o0',lambda ctx:native_o0_probe(ctx,reverse='reuse'),120.)
    elif args.phase=='native-reverse-optimized':
        old=read(RUN/'native_reverse_o0.json');assert old['all_equivalent']
        plan=dict(version='gvs_native_reverse_kernel@1.2.0',hypothesis='O0 reverse is equivalent but slower; optimization is essential. The prior 180-second cap did not establish a performance result. Explicitly allocate 900 seconds to finish one optimized build of the 16 MB source, retaining all failed costs; no regenerated model or baseline replay.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),compile_cap_s=900.,compiler_flags=['-O1','-fno-inline','-ftime-trace','-fno-fast-math','-shared'],points=6,reserve_s=960.,protection='Existing development reservation check retains 1265 seconds finalization and separate 18000 seconds/six backend validation allocation.')
        if not (RUN/'native_reverse_optimized_plan.json').exists():atomic_json(RUN/'native_reverse_optimized_plan.json',plan)
        calculate('native_reverse_optimized',lambda ctx:native_o0_probe(ctx,reverse='optimized'),960.)
    elif args.phase=='native-mixed':
        old=read(RUN/'native_reverse_optimized.json')
        assert 'error' in old or old['median_speedup']<=1.
        plan=dict(version='gvs_native_mixed_kernel@1.0.0',hypothesis='Source inspection locates 4.84 MB force and 10.97 MB adjoint orchestration functions, 97.7 percent of the 16.18 MB unit. Suppress optimization on just these two functions, optimize 25-100 KB cell derivative helpers at O2; no mathematical code change.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),annotation='optnone on casadi_f0/casadi_f7 only',compiler_reference='https://clang.llvm.org/docs/AttributeReference.html#optnone',compile_cap_s=120.,points=6,reserve_s=180.)
        if not (RUN/'native_mixed_plan.json').exists():atomic_json(RUN/'native_mixed_plan.json',plan)
        calculate('native_mixed',lambda ctx:native_o0_probe(ctx,reverse='mixed'),180.)
    elif args.phase=='native-split':
        assert 'error' in read(RUN/'native_mixed.json')
        plan=dict(version='gvs_native_split_kernel@1.0.0',hypothesis='Per-function optnone still exceeded 120 s in the O2 unit. Separate the two giant orchestration functions into an O0 translation unit and optimize only shared small helpers in another O2 unit, avoiding whole-module optimization/code-generation of giant graphs. Exact arithmetic retained; independent six-point equivalence and timing required.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),compile_caps_s=[120.,120.,30.],points=6,reserve_s=300.)
        if not (RUN/'native_split_plan.json').exists():atomic_json(RUN/'native_split_plan.json',plan)
        calculate('native_split',lambda ctx:native_o0_probe(ctx,reverse='split'),300.)
    elif args.phase=='native-shared':
        old=read(RUN/'native_split.json');assert old['all_equivalent'] and old['median_speedup']<1.
        plan=dict(version='gvs_native_split_kernel@2.0.0',hypothesis='Split compilation succeeds in 6.5 s but native evaluation remains slower (median about .686). Shared matrix/copy/dot runtime helpers still compiled at O0 in the orchestration unit. Link those exact nine helpers once from the O2 unit; no arithmetic or model changes.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),points=6,compile_caps_s=[120.,120.,30.],reserve_s=300.)
        if not (RUN/'native_shared_plan.json').exists():atomic_json(RUN/'native_shared_plan.json',plan)
        calculate('native_shared',lambda ctx:native_o0_probe(ctx,reverse='shared'),300.)
    elif args.phase in ('native-chunked','native-chunked-repair1'):
        old=read(RUN/'native_shared.json');assert old['all_equivalent'] and old['median_speedup']<1.
        plan=dict(version='gvs_native_chunked_kernel@1.0.0',hypothesis='Split compilation is fast but unoptimized orchestration remains slower; shared optimized matrix helpers alone worsened performance. Partition giant force/adjoint code at complete MX operation boundaries into <=250-operation functions so the entire unchanged arithmetic graph can be optimized in bounded-size functions. Cross-chunk scalar and read-only pointer temporaries are explicitly retained.',source_sha256=hashlib.sha256((RUN/'native_reverse/force_reverse.c').read_bytes()).hexdigest(),compiler_flags=['-O1','-fno-inline','-fno-fast-math','-shared'],compile_cap_s=240.,points=6,reserve_s=300.)
        name=args.phase.replace('-','_')
        if args.phase.endswith('repair1'):
            plan.update(version='gvs_native_chunked_kernel@1.0.1',repair='First parse rejected the generated const casadi_int *cii declaration; now explicitly supported. Prior 1.063 s failed receipt retained, no prior numerical result to replay.')
        if not (RUN/(name+'_plan.json')).exists():atomic_json(RUN/(name+'_plan.json'),plan)
        calculate(name,lambda ctx:native_o0_probe(ctx,reverse='chunked'),300.)
    elif args.phase=='mass-form':
        plan=dict(version='gvs_mass_form_kernel@1.0.0',hypothesis='Native reverse variants still repeat direction calculations and have not accelerated the baseline. Before a larger compilation, test the already implemented algebraically equivalent implicit_terms mass/force representation against the current projected inertial wrench representation. It preserves all mass, gravity, velocity bias, tendon, elasticity and damping terms; only expression/AD organization changes.',points=6,acceleration='Zero, identical to the saved baseline; further nonzero-acceleration checks required before use.',equivalence=dict(force=1e-10,relative_jacobian=1e-8),reserve_s=180.)
        if not (RUN/'mass_form_plan.json').exists():atomic_json(RUN/'mass_form_plan.json',plan)
        calculate('mass_form',mass_form_probe,180.)
    elif args.phase=='native-full-chunked':
        old=read(RUN/'native_chunked_repair1.json');assert old['all_equivalent'] and old['median_speedup']<1.
        plan=dict(version='gvs_native_chunked_kernel@2.0.0',hypothesis='Chunked scalar reverse compiles with optimization and preserves all six comparisons, but .87x speedup still loses to baseline. Reuse the already generated full-Jacobian source and apply the proven chunking transformation, avoiding repeated directional forward/reverse work when the entire Jacobian is requested. The cheap equivalent mass-form probe was also slower (.12x), so it is rejected.',source_sha256=hashlib.sha256((RUN/'native_kernel/force_native.c').read_bytes()).hexdigest(),compiler_flags=['-O1','-fno-inline','-fno-fast-math','-shared'],compile_cap_s=900.,points=6,reserve_s=960.,continuation='Only equivalent and faster kernel qualifies for nonzero-acceleration checks and five complete causal controller updates, never direct backend admission.')
        if not (RUN/'native_full_chunked_plan.json').exists():atomic_json(RUN/'native_full_chunked_plan.json',plan)
        calculate('native_full_chunked',lambda ctx:native_o0_probe(ctx,reverse='full-chunked'),960.)
    else:raise ValueError('Unknown successor phase')
