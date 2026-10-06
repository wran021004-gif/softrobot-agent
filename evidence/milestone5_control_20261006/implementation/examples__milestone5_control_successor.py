"""Saved-state diagnosis and bounded experimental controller measurements."""
from copy import deepcopy
from pathlib import Path
import sys,time,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from tools.state_io import read,atomic_json,digest
from examples.milestone_bound_successor import M5,operation,export,host,AUTH,LIMIT5
OLD=ROOT/'evidence/milestone5_matched_20261006'

def distance(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))

def saved_diagnosis(ctx):
    cases=[];snapshots=[]
    for name in ('original075','original15'):
        f=read(OLD/f'forecast_{name}.json');b=read(OLD/f'backend_summary_{name}.json')
        rows=[]
        case=next(c for c in read(OLD/'protocol.json')['candidates'] if c['name']==name)
        for i in range(len(f['rows'])):
            fr=f['rows'][i];br=b['command_plan_capture'][i];bu=b['updates'][i]
            matching=next((r for r in b['full_states'] if abs(r['time_s']-fr['time_s'])<1e-9),None)
            if matching is None and i==0:matching=dict(time_s=0.,state=case['initial_full_state'])
            if matching is None:raise ValueError('FULL_STATE_TIMESTAMP_NOT_FOUND')
            x=fr['command_receipt']['measured_initial_state'];y=br['projected_current_state']
            warm_f=fr['warm_before_command'];warm_b=b['command_plan_capture'][i-1]['selected_plan'] if i else None
            rows.append(dict(update=i,time_s=fr['time_s'],command_linf_n=distance(fr['input_n'],br['input_n']),
                projected_state_linf=distance(x,y),full_state_linf=distance(fr['initial_full_state'],matching['state']),
                selected_iterations=[fr['command_receipt']['optimization_selected_iteration'],bu['optimization_selected_iteration']],
                warm_states_linf=None if i==0 else distance(warm_f['states'],warm_b['states']),
                warm_tensions_linf_n=None if i==0 else distance(warm_f['tensions'],warm_b['tensions']),
                forecast_warm_identity=digest(warm_f),backend_previous_plan_identity=None if i==0 else digest(warm_b),
                forecast_stop=fr['command_receipt']['policy_stop_reason'],backend_stop=bu['policy_stop_reason']))
        idx=next((r['update'] for r in rows if r['command_linf_n']>1e-8),None)
        cases.append(dict(candidate=name,rows=rows[:max(5,idx+2)],first_command_divergence_update=idx,
            ownership=dict(forecast=OLD.relative_to(ROOT).as_posix()+f'/forecast_{name}.json',backend=b['execution_id'],manifest=b['source_manifest'])))
        # Always inspect .02 on .075; use earliest divergence on .15.
        i=2 if name=='original075' else idx
        if i is None:raise ValueError('NO_SAVED_DIVERGENCE')
        fr=f['rows'][i];br=b['command_plan_capture'][i];bu=b['updates'][i]
        matching=next((r for r in b['full_states'] if abs(r['time_s']-fr['time_s'])<1e-9),None)
        snapshots.append(dict(candidate=name,update_id=i,time_s=fr['time_s'],
            forecast=fr,backend_current_full_state=matching,backend_current_projected_state=br['projected_current_state'],
            backend_previous_input=b['command_plan_capture'][i-1]['input_n'] if i else fr['previous_input_n'],
            backend_warm=b['command_plan_capture'][i-1]['selected_plan'] if i else fr['warm_before_command'],backend_receipt=bu,
            backend_execution_id=b['execution_id'],backend_manifest=b['source_manifest'],
            configuration=next(c['configuration'] for c in read(OLD/'protocol.json')['candidates'] if c['name']==name),
            runtime_identity=read(OLD/'protocol.json')['implementation_identity']))
    atomic_json(M5/'saved_snapshots_v2.json',snapshots)
    return dict(version='saved_command_divergence@1.0.1',cases=cases,
        observation='Command comparison precedes the next physics advance; previous complete warm plans are distinct inputs even if first commands/current states agree.',
        limitations=['Saved backend capture holds prior selected plan, not complete solver input after regeneration; initial backend warm is obtained from same declared preparation, not assumed bitwise identical.',
            'Selected iterations alone do not establish optimizer inputs matched or unique causal mechanism.'])

def freeze():
    if (M5/'protocol.json').exists():raise ValueError('PROTOCOL_ALREADY_FROZEN')
    old=read(OLD/'protocol.json');p=dict(version='m5_control_successor@1.0.0',authorization=AUTH,
        predecessor=dict(protocol=digest(old),checkpoint=read(OLD/'checkpoint_seal.json')),allocation=LIMIT5,
        numerical_limits=dict(standalone_updates=240,forecasts=6,backends=6,component_evaluations=24),
        experimental_version_limit=2,screening_families=1,screening_revisions=1,
        correction_limits=dict(cumulative=4,consecutive=2),engineering_repair_limit_per_scope=1,
        candidates=old['candidates'],original_rules=old['original_rules'],thresholds=old['thresholds'],
        local_numerical_protocol=read(ROOT/'evidence/milestone5_successor_20261005/fixed_target_protocol.json'),
        protected_validation=old['protected_validation'],incumbent=old['incumbent'],
        requirement_map=dict(physical_task='Unchanged candidate configurations, robot, actuation/physics/task/timing except distinct experimental controller binding/recipe.',
            local='fixed_backend_transition_validation@2.0.0 retained; full-state outputs and independent checks, historical refinement failures separate.',
            trajectory='Original 1e-6 m / 1e-4 m/s speed/vector accuracy, direction/classifications required.',
            ranking='Feasibility-qualified useful order and missed viable candidate audit; abstention not success.',
            economics='All-in preparation, fitting/calibration/diagnostics and interpretation/corrections included; actual savings zero under all-candidate verification.',
            realtime='Every complete software input-to-command interval <=.01 s; setup/physics separate; no hardware WCET claim.',
            validation='Two untouched combinations and preregistered independent repeat; exact original repeat/positive pair economics gates; no grants before joint admission.'),
        diagnostic=dict(work_cap=10,local_comparisons='Per candidate same forecast saved x, previous input, complete warm, horizon, functions and numerical settings. Replace timed callback termination only with fixed work cap. Then one warm-only intervention if saved discrepancy warrants it.',
            prospective_choices_forbidden=True,maximum_planned_solves=6,reserve_per_operation_s=240.),
        proposed_redesign=dict(controller='controller.gvs_nmpc@8.0.0',horizon=2,max_iterations=2,
            feasible_return=dict(minimum_s=.001,budget_s=.005,relative_improvement=.1),max_cpu_s=1.,
            rationale='Measured regeneration and optimization dominate. Two-node warm regeneration plus bounded iterations cut both workloads, at the cost of shorter predictive behavior; no equivalence or convergence claim.',
            warm='Regenerate all short-horizon states from actual candidate measurement; own previous plan only; initial compatible bounded tensions remain guesses.',
            feasibility='Independently finite plan, initial consistency, shooting residual and physical input bounds <= original 1e-5 scaled tolerance.',
            fallback='Same bounded previous command on unusable plan; stop after declared three consecutive unusable updates; engineering fallback has no safety guarantee.',
            deadline='Record full boundary miss even if callback checks or preparation overrun; budget is a work/timer allowance, not hard wall-clock guarantee.',
            local_admission='All representative complete input-to-command intervals <=.01 s, accepted feasible improvement; otherwise no complete pair.'),
        costs=dict(cold_start='Actual construction/loading/setup charged; existing verified DLL reused with measured historical compile cost retained separately.',
            amortization='No hypothetical amortization credit; one screening decision must pay all required method development/interpretation costs.',
            boundary=old['costs'],new_timed_comparisons_serial=True),
        implementation=dict(kernel=old['implementation']['kernel']),workers=0,subagents=0)
    p['implementation']['files']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('extensions/optimization/ipopt.py','examples/milestone5_control_successor.py','extensions/tendon_family/gvs_bounded_nmpc.py')}
    p['implementation_identity']=digest(p['implementation'])
    atomic_json(M5/'protocol.json',p);atomic_json(M5/'protocol_seal.json',dict(identity=digest(p),before_new_numerical_results=True))
    return p

def provider_native():
    from examples.milestone5_successor import reference_functions
    from extensions.tendon_family.milestone5_feedback_runtime import NativeFunctions
    k=read(M5/'protocol.json')['implementation']['kernel']
    return NativeFunctions(reference_functions(),k['library'],library_sha256=k['library_sha256'])

def local_compare(ctx,name,policy,warm_kind='forecast'):
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    from schemas.platform import SessionInput,RobotDescription,TaskDefinition
    from extensions.tendon_family.gvs_profile import reach_numerical
    from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace,use_trajectory_functions
    from extensions.tendon_family.diagnostic_math import charge_units
    from extensions.tendon_family.contracts import GVSTrajectoryParameters
    s=next(s for s in read(M5/'saved_snapshots_v2.json') if s['candidate']==name)
    inp=SessionInput.model_validate(s['configuration']);p=GVSTrajectoryParameters.model_validate(inp.policy.controller.parameters.data['recipe'])
    numerical=reach_numerical(inp);nominal=numerical['nominal'];start=time.perf_counter();provider=provider_native()
    with use_trajectory_functions(provider):
        ws=TrajectoryWorkspace(inp.task,inp.robot,p,[*nominal['q0'],*([0.]*len(nominal['q0']))],nominal['u0'],settling=inp.policy.controller.parameters.data['settling'])
        setup=time.perf_counter()-start
        warm=deepcopy(s['forecast']['warm_before_command'] if warm_kind=='forecast' else s['backend_warm'])
        # A prior selected plan requires one-interval shifting. Saved forecast warm is also prior selected.
        ws.last=warm;ws.solver.diagnostic_trace=True
        if policy=='deterministic':ws.solver.diagnostic_work_cap=read(M5/'protocol.json')['diagnostic']['work_cap']
        elif policy!='timed':raise ValueError('UNDECLARED_POLICY')
        charge_units(ctx,'local_solves',1);start=time.perf_counter()
        solved=ws.solve(s['forecast']['command_receipt']['measured_initial_state'],s['forecast']['previous_input_n'],elapsed_s=s['time_s'])
        package_start=time.perf_counter();command=np.asarray(solved['tensions'][0]).tolist();packaging=time.perf_counter()-package_start
        complete=time.perf_counter()-start
    d=solved['diagnostics']
    return dict(candidate=name,snapshot_update=s['update_id'],policy=policy,warm_kind=warm_kind,
        setup_s=setup,full_measured_compute_s=complete,command_packaging_s=packaging,
        standalone_attempts=1,backend_steps=0,command=command,
        selected_iteration=d['selected_feasible_iteration'],objective=solved['result']['objective_value'],
        constraint_violation=solved['result']['constraint_violation'],accepted=solved['accepted'],
        termination=d['policy_stop_reason'],raw_termination=d['return_status'],
        input_identity=digest(dict(x=s['forecast']['command_receipt']['measured_initial_state'],previous=s['forecast']['previous_input_n'],warm=warm,numerical=p.model_dump(mode='json'))),
        configuration_identity=digest(s['configuration']),runtime_identity=read(M5/'protocol.json')['implementation_identity'],
        solved=solved,scope='Local saved-state diagnostic only; fixed work is not production convergence, safety or real-time evidence.')

def measure8(ctx,name):
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    from schemas.platform import SessionInput
    from extensions.tendon_family.gvs_bounded_nmpc import BoundedReachNMPCController
    from extensions.tendon_family.gvs_profile import prepare_execution
    from extensions.tendon_family.gvs_nmpc import resolve_gvs_nmpc_control
    from extensions.tendon_family.gvs_trajectory import use_trajectory_functions
    from extensions.tendon_family.gvs_projection import project
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.milestone5_fullstate import DiscreteFullState
    from extensions.tendon_family.diagnostic_math import charge_units
    p=read(M5/'protocol.json');case=next(c for c in p['candidates'] if c['name']==name)
    snap=next(s for s in read(M5/'saved_snapshots_v2.json') if s['candidate']==name)
    cfg=deepcopy(case['configuration']);cfg['policy']['controller']['version']='8.0.0'
    recipe=cfg['policy']['controller']['parameters']['data']['recipe'];redesign=p['proposed_redesign']
    for k in ('horizon','max_iterations','feasible_return','max_cpu_s'):recipe[k]=redesign[k]
    cfg['run_id']=M5.name+'-v8-'+name
    ctx.save_artifact(cfg,'v8_candidate_configuration');inp=SessionInput.model_validate(cfg)
    start=time.perf_counter();provider=provider_native()
    model=DiscreteFullState(cfg,case['physics'],case['compiled'],case['xml'])
    basis=resolve_basis(inp.robot.structure.data,recipe['basis'])
    control=BoundedReachNMPCController(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
    prepare_execution(ctx,control,inp);plan=resolve_gvs_nmpc_control(inp,case['physics'])
    with use_trajectory_functions(provider):control.configure(case['physics'],plan)
    setup=time.perf_counter()-start
    source=snap['forecast']['warm_before_command'];warm=dict(states=source['states'][1:4],tensions=source['tensions'][1:3])
    rows=[]
    for temperature in ('cold','cached'):
        control.seed=deepcopy(warm);control.workspace.last=deepcopy(warm)
        control.previous=np.asarray(snap['forecast']['previous_input_n']).copy()
        charge_units(ctx,'local_solves',1)
        full=np.asarray(snap['forecast']['initial_full_state']);start=time.perf_counter()
        z=project(case['physics'],basis,full[:model.full_n],full[model.full_n:]);motion=model.motion(full)
        geometry=dict(tip=np.asarray(motion['position_m']),gvs_projection=z)
        observation=time.perf_counter()-start
        with use_trajectory_functions(provider):command=control.command(snap['time_s'],geometry,z['q_gvs'],z['qdot_gvs'])
        packaging_start=time.perf_counter();packaged=list(command);packaging=time.perf_counter()-packaging_start
        complete=time.perf_counter()-start;d=control.workspace.solver.last_diagnostics
        rows.append(dict(temperature=temperature,full_software_input_to_command_s=complete,observation_s=observation,
            packaging_s=packaging,deadline_missed=complete>.01,command=packaged,receipt=deepcopy(control.observations[-1]),
            diagnostics=deepcopy(d),accepted=control.last['plan_accepted'],
            improvement=None if d is None or control.workspace.last is None or 'result' not in control.workspace.last else d['initial_objective']-control.workspace.last['result']['objective_value'],
            candidate_configuration_identity=digest(cfg),warm_identity=digest(warm),
            feasibility_evidence=deepcopy(control.workspace.last)))
    return dict(controller='controller.gvs_nmpc@8.0.0',configuration=cfg,configuration_identity=digest(cfg),candidate=name,
        measured_snapshot_time_s=snap['time_s'],setup_s=setup,rows=rows,standalone_updates=2,backend_steps=0,
        boundary='Full saved physical state supplied; includes projection/world output, controller preparation/optimization/independent validation/observation and list packaging. Physics and one-time setup separate.',
        cache='Second measurement repeats identical owned input/previous/warm with compiled solver/tail cached; not a causal trajectory or convergence claim.',
        local_admitted=all(r['accepted'] and not r['deadline_missed'] and r['improvement'] is not None and r['improvement']>0 for r in rows))

def assess(ctx):
    saved=read(M5/'saved_diagnosis_corrected.json')
    comparisons={p.stem:read(p) for p in M5.glob('local_*.json') if not p.stem.endswith(('_receipt','_pending'))}
    timed=comparisons['local_original075_timed_forecast'];fixed=comparisons['local_original075_deterministic_forecast'];perturb=comparisons['local_original075_deterministic_backend']
    controller=[read(M5/f'measure8_{n}.json') for n in ('original075','original15')]
    local=all(m['local_admitted'] for m in controller)
    inherited=read(OLD/'operational_assessment.json')
    return dict(version='bounded_control_admission@1.0.0',controller='controller.gvs_nmpc@8.0.0',
        diagnosis=dict(saved=saved,comparison_refs=list(comparisons),
            same_input_timed_vs_work=timed['input_identity']==fixed['input_identity'],
            timed_vs_work_command_linf_n=distance(timed['command'],fixed['command']),
            work_warm_only_command_linf_n=distance(fixed['command'],perturb['command']),
            supported_cause='On original075 saved projected state and own warm, termination-only intervention reproduces iteration 5 versus 10 command separation. Warm-only tiny perturbation at the same work cap has negligible effect in this local test.',
            confounders=['Bitwise initial state and prior warm plans differ; derivative/conditioning amplification outside tested snapshot remains possible.',
                'Original15 earliest above-1e-8 command discrepancy is tiny at update4, with equal iteration indices. Timing is not a demonstrated unique cause for that discrepancy.',
                'Cold local runs differ from original hot runtime/cache history; five seconds is a conditional relative-improvement criterion, not an unconditional floor.',
                'No observed backend iteration decisions were supplied to a forecast; diagnostic cap was preregistered independently.']),
        controller_measurements=[dict(candidate=m['candidate'],configuration_identity=m['configuration_identity'],setup_s=m['setup_s'],rows=[
            dict(temperature=r['temperature'],full_input_to_command_s=r['full_software_input_to_command_s'],
                preparation_s=r['receipt']['warm_preparation_s'],optimization_s=r['diagnostics']['solve_s'],validation_s=r['diagnostics']['validation_s'],
                accepted=r['accepted'],improvement=r['improvement'],selected_iteration=r['diagnostics']['selected_feasible_iteration'],
                scaled_violation=r['receipt']['optimization_constraint_violation'],deadline_missed=r['deadline_missed']) for r in m['rows']]) for m in controller],
        local_admitted=local,formal_admitted=False,m5_closed=False,
        failed_gates=['Every complete controller interval must meet 10 ms; all four v8 local measurements miss.',
            'Frozen local advancement requires accepted feasible improvement; all four select initialization with zero improvement.'],
        unrun_gates=['New-controller complete causal full-history accuracy, direction, threshold component classifications and feasibility-qualified useful ranking.',
            'New-controller matched independent backend accuracy and all-in positive screening economics.',
            'Two untouched formal pairs and preregistered independent repeat, original repeat tolerances and every update timing.'],
        local_numerical_support=dict(version='fixed_backend_transition_validation@2.0.0',historical_support_reused=True,
            scope='Fixed-input emulated physical transition only; not v8 full-feedback validation.',historical_continuous_and_refinement_failures_preserved=True),
        screening=dict(decision='Diagnostic reference only; no elimination authority and no complete pair launched.',
            revised_reference_runtime='Own-feedback full-state predictor now resolves explicit registered controller including v8. No full v8 rollout claimed; local gate fails before expense is justified.',
            cheaper_family_implemented=False,reason='No admissible revised controller; shortening the timer returned initialization and preparation alone exceeds deadline. A cheap task-output surrogate cannot supply inherited full-state/local numerical evidence. A second arbitrary timer/work variant is not supported by a new mechanism.',
            new_accuracy='Unmeasured complete trajectory; local plan feasibility is not task acceptance.',
            new_classification_and_ranking='Unmeasured; no pair ordering or candidate rejection claimed.',
            new_economics='No screening decision executed; required development/interpretation costs charged. No positive counterfactual saving claimed.',
            historical_reference=inherited,historical_interpretation_scope='Stopped v7 study is negative evidence only, not validation of v8.',
            actual_avoided_evaluations=0,actual_savings_s=0.,counterfactual_new_savings_s=None),
        experimental_versions_used=1,unused_second_version=1,screening_families_used=0,screening_revisions_used=0,
        development_forecasts=0,development_backends=0,standalone_updates=9,additional_component_evaluations=0,embedded_updates=0,
        protected_pairs_used=0,protected_backend_slots_preserved=6,
        next_technical_decision='A distinct approximation/reuse algorithm must cut preparation and first callback/derivative work, while earning fresh feasibility/dynamics/closed-loop evidence; repeating a smaller timer with the same GVS kernel has no measured route to 10 ms.',
        research_interpretation_status='Awaiting direct chat external-transmission authorization after automatic-review rejection; no LLM approval can override failed local gates.')

if __name__=='__main__':
    action=sys.argv[1]
    if action=='freeze':freeze()
    elif action=='inspect':operation(M5,'saved_diagnosis',saved_diagnosis,reserve=60.)
    elif action=='inspect_corrected':operation(M5,'saved_diagnosis_corrected',saved_diagnosis,reserve=60.)
    elif action=='compare':
        name,policy=sys.argv[2:4];warm=sys.argv[4] if len(sys.argv)>4 else 'forecast'
        operation(M5,f'local_{name}_{policy}_{warm}',lambda ctx:local_compare(ctx,name,policy,warm),reserve=240.)
    elif action=='measure8':
        name=sys.argv[2];operation(M5,'measure8_'+name,lambda ctx:measure8(ctx,name),reserve=240.)
    elif action=='assess':operation(M5,'development_assessment',assess,reserve=60.)
    elif action=='export':export(M5)
