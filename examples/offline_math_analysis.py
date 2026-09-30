"""Retrospective saved-data study. No provider, worker, simulation, or NMPC call."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from schemas.platform import ToolRequest
from schemas.platform_analysis import AnalysisProtocol
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import atomic_json, digest
from extensions.tendon_family.saved_cases import read_cases, file_hash
from extensions.math_analysis.kernels import normalized,raw_scipy

SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923')


def verification_acceptance(report):
    scipy=all(report[k] for k in ('protocol_binding_passed','derivative_checks_passed',
        'repeat_checks_passed','serialized_outputs_verified','prohibited_usage_zero','caller_contract_identical'))
    return dict(acceptance_status='full_cross_implementation' if scipy and report['matlab_checks_passed'] else 'scipy_only_partial',
        full_cross_implementation_accepted=bool(scipy and report['matlab_checks_passed']))


def save(store,value):
    with store.transaction() as db: return plain(store.put(db,value))


def invoke(host,name,args,actor='design-facing'):
    host.actor=actor
    receipt=host.invoke(plain(ToolRequest(request_id='analysis-'+uuid4().hex,tool_id=name,tool_version='1.0.0',
        arguments=args,reason='Deterministic offline shared mathematical analysis; no model or backend execution.',cache='new')))
    receipt=plain(receipt)
    if receipt['execution_status']!='completed': raise RuntimeError(json.dumps(receipt))
    return receipt['output'],host.store.artifact(receipt['output'])


def comparison(a,b,p):
    checks={}
    def check(name,x,y):
        x=np.asarray(x); y=np.asarray(y); error=np.abs(x-y)
        checks[name]=dict(passed=bool(np.all(error<=p.comparison_atol+p.comparison_rtol*np.abs(y))),
            max_absolute_error=float(error.max()),max_scaled_error=float(np.max(error/(p.comparison_atol+p.comparison_rtol*np.abs(y)))))
    x=np.asarray(a['poles']); y=np.asarray(b['poles']); i,j=linear_sum_assignment(np.linalg.norm(x[:,None,:]-y[None,:,:],axis=2))
    check('pole_sets',x[i],y[j])
    for k in ('A_d','B_d','drift_d','singular_values','continuous_gramians','held_gramians'):
        check(k,a[k],b[k])
    for part in ('real','imag'):
        check('freqresp_'+part,[r[part] for r in a['frequency_response']],[r[part] for r in b['frequency_response']])
    return checks


def delivery(root,comparison_result,p,matlab_comparison,usage):
    rows=[]
    for c in comparison_result['records']:
        f=c['saved']['factual_result']; regions=c['operating_regions']
        static=next((r for r in regions if r['point']['phase']=='computed_static_equilibrium'),None)
        eq=static if static and static['validity']['equilibrium'] else None
        last=next((r for r in regions if r['point'].get('requested_time_s')==.34),None)
        initial=next((r for r in regions if r['point'].get('requested_time_s')==0),None)
        def weak(r): return None if r is None else r['windows'][-1]['continuous']['output']['eigenvalues'][0]
        def energy(r):
            if r is None: return None
            return r['windows'][-1]['continuous']['minimum_energy']['energy']
        rows.append(dict(candidate=c['binding']['candidate_id'],passed=f['task_accepted'],terminal_error_mm=1000*f['terminal_error_m'],
            terminal_speed_m_s=f['terminal_tip_speed_m_s'],settled=f['sampled_settling']['passed'],
            peak_tension_n=max(r['maximum_n'] for r in f['applied_tension_ranges']),
            prediction_mean_mm=1000*f['one_step_prediction_summary']['mean_tip_difference_m'],
            feasible=f['accepted_plans'],converged=f['converged_updates'],initialization=f['initialization_selected'],
            optimized=f['accepted_noninitialization_plans'],mean_update_s=f['mean_complete_update_s'],
            deadline_misses=f['deadline_misses'],samples=c['sampled_statistics']['sample_count'],
            equilibrium_qualified=None if static is None else static['validity']['equilibrium'],
            equilibrium_weak_output=weak(eq),initial_weak_output=weak(initial),late_weak_output=weak(last),
            equilibrium_energy=energy(eq),late_energy=energy(last),
            maximum_sampled_unstable=max(r['unstable_modes'] for r in regions if r['point'].get('actual_time_s') is not None)))
    with (root/'cross_case.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]); writer.writeheader();writer.writerows(rows)
    atomic_json(root/'cross_case.json',rows)
    associations={}
    for k in ('equilibrium_weak_output','initial_weak_output','late_weak_output','late_energy','peak_tension_n','prediction_mean_mm','optimized','mean_update_s','terminal_speed_m_s'):
        pairs=[(r[k],r['terminal_error_mm']) for r in rows if r[k] is not None]
        rho=None if len(pairs)<3 or len(set(a for a,b in pairs))<2 else float(spearmanr(*zip(*pairs)).statistic)
        associations[k]=dict(spearman_rho=rho,count=len(pairs),interpretation='Descriptive association only; no fitted threshold, no causal claim.')
    atomic_json(root/'associations.json',associations)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    for ax,key,label in zip(axs,('late_weak_output','prediction_mean_mm','optimized'),('Late weak output Gramian','Saved mean one-step error (mm)','Optimized selections')):
        for i,r in enumerate(rows):
            if r[key] is not None:
                ax.scatter(r[key],r['terminal_error_mm'],color='green' if r['passed'] else 'tab:blue')
                ax.annotate(str(i+1),(r[key],r['terminal_error_mm']),fontsize=8)
        ax.axhline(10,color='gray',linestyle=':');ax.set_xlabel(label);ax.set_ylabel('Terminal error (mm)')
    fig.tight_layout();fig.savefig(root/'associations.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for i,c in enumerate(comparison_result['records']):
        eq=next((r for r in c['operating_regions'] if r['point']['phase']=='computed_static_equilibrium' and r['validity']['equilibrium']),None)
        if eq:
            curve=eq['authority'];ax.loglog(curve['frequency_rad_s'],curve['minimum_singular_value'],label=str(i+1))
    ax.set_xlabel('Angular frequency (rad/s)');ax.set_ylabel('Minimum normalized singular value')
    ax.set_title('Qualified equilibrium authority curves; usable bandwidth undefined')
    ax.legend(title='Case');fig.tight_layout();fig.savefig(root/'authority.png',dpi=160);plt.close(fig)
    numerical_checks=[v for r in matlab_comparison.get('comparisons',[]) for v in r['checks'].values()]
    numerical_summary=dict(available=matlab_comparison.get('available'),models=matlab_comparison.get('models'),
        checks=len(numerical_checks),passed=sum(c['passed'] for c in numerical_checks),
        worst_tolerance_fraction=max((c['max_scaled_error'] for c in numerical_checks),default=None),
        absolute_tolerance=p.comparison_atol,relative_tolerance=p.comparison_rtol,
        environment=matlab_comparison.get('environment'),blocker=matlab_comparison.get('blocker'))
    atomic_json(root/'numerical_summary.json',numerical_summary)
    facts=[]
    for c in comparison_result['records']:
        saved=json.loads((root/'cases'/c['binding']['candidate_id']/'saved_case.json').read_text(encoding='utf8'))
        facts.extend(dict(binding=c['binding'],fact=f) for f in saved['facts'])
    atomic_json(root/'deterministic_facts.json',facts)
    lines=['Offline shared mathematical analysis', '',
        'Nine completed historical executions, one passing terminal reach case. No new trajectory or controller execution.',
        'Numerical implementation verification and explanatory usefulness are separate conclusions.', '',
        'Protocol: fixed baseline curvature-angle scaling, 0.35 s velocity scaling, 8 N input and 0.01 m output; windows 0.05/0.10/0.35 s.',
        'All windows are nominal frozen local windows, including at t=0.34 where only 0.01 s remains. Energy is not a task-feasibility certificate.',
        'Energy includes affine zero-perturbation-input endpoint drift, reports unreachable output components, and separates continuous from dt-weighted held-input cost.',
        'Frequency curves are equilibrium transfers only when normalized drift passes 1e-5/s. No justified task bandwidth threshold: usable bandwidth undefined.',
        '', 'Case table (plot numbers follow this order):']
    for i,r in enumerate(rows):
        lines.append(f"{i+1}. {r['candidate']}: error={r['terminal_error_mm']:.6f} mm, speed={r['terminal_speed_m_s']:.6f} m/s, settled={r['settled']}; optimized={r['optimized']}/35, converged={r['converged']}, update={r['mean_update_s']:.3f} s.")
    lines+=['','Descriptive associations with terminal error:',json.dumps(associations,indent=2), '',
        'Interpretation: compare passing case against its immediate predecessor and all failures in cross_case.csv. Local metrics describe operating-point-dependent directions and unconstrained authority. They cannot certify bounded reach.',
        'Controller selection and initial guessed tension changes must be assessed separately from plant capability. Feasible initialization is not a converged optimized solution.',
        'Small one-step discrepancy does not imply cumulative terminal reach success. Terminal acceptance does not imply settling or meeting 0.01 s compute deadlines.',
        'Weak or mixed associations are valid results; no composite score, fitted screening threshold, or PASS/REJECT classifier was created.',
        '', 'Numerical comparison:',json.dumps(numerical_summary,indent=2), '', 'Resource usage:',json.dumps(usage,indent=2),
        '', 'Limits: nine retrospective cases with one pass; sparse saved projected states, reduced bending physics, no physical hardware validation; nonlinear extrapolation over nominal windows may be poor.',
        'Reproducibility means matching source inputs/protocol and numerical agreement within frozen tolerances, not bitwise identity across software/hardware.',
        'MATLAB reference: https://www.mathworks.com/help/control/ref/gramoptions.html (R2016a introduction); https://www.mathworks.com/help/control/ref/statespacemodel.gram.html (stable model requirement).']
    (root/'report.txt').write_text('\n'.join(lines),encoding='utf8')
    findings=interpretation(rows,associations)
    (root/'findings.txt').write_text('\n\n'.join(findings),encoding='utf8')
    text=(root/'report.txt').read_text(encoding='utf8')
    (root/'report.txt').write_text(text.replace('Case table (plot numbers follow this order):',
        'Explanatory findings:\n\n'+'\n\n'.join(findings)+'\n\nCase table (plot numbers follow this order):'),encoding='utf8')
    return rows


def interpretation(rows,associations):
    passing=next(r for r in rows if r['passed']);previous=next(r for r in rows if r['candidate'].startswith('b1_near'))
    counter=next(r for r in rows if r['candidate']=='rev_compliant_max')
    later_counter=next(r for r in rows if r['candidate']=='fresh_near0p168_far0p128_compliant_s1p05')
    return [
        f"Useful descriptive association: late output minimum eigenvalue vs terminal error rho={associations['late_weak_output']['spearman_rho']:.3f}; late affine-corrected energy rho={associations['late_energy']['spearman_rho']:.3f}. These use post-control states and are not prospective design screens.",
        f"Weak plant-only distinction: passing vs immediate failure equilibrium weak output eigenvalues {passing['equilibrium_weak_output']:.3f} vs {previous['equilibrium_weak_output']:.3f}, a {100*(passing['equilibrium_weak_output']/previous['equilibrium_weak_output']-1):.2f}% difference, while terminal errors are {passing['terminal_error_mm']:.3f} vs {previous['terminal_error_mm']:.3f} mm.",
        f"Counterexample: rev_compliant_max fails at {counter['terminal_error_mm']:.3f} mm despite a larger qualified equilibrium weak eigenvalue ({counter['equilibrium_weak_output']:.3f}) and larger late weak eigenvalue ({counter['late_weak_output']:.3f}) than the passing case ({passing['late_weak_output']:.3f}).",
        f"Counterexample: fresh_near0p168_far0p128 fails at {later_counter['terminal_error_mm']:.3f} mm despite lower late nominal correction energy ({later_counter['late_energy']:.6g}) than the passing case ({passing['late_energy']:.6g}). These 0.35 s windows exceed the 0.01 s remaining at t=0.34.",
        'Initial tip-output Gramian is rank two in all nine cases: axial first-order correction is unreachable at the straight configuration. This common geometry does not distinguish outcomes.',
        f"Saved prediction discrepancy is not a success proxy: passing mean {passing['prediction_mean_mm']:.3f} mm exceeds its failed predecessor {previous['prediction_mean_mm']:.3f} mm.",
        f"Controller-selection association is stronger (rho={associations['optimized']['spearman_rho']:.3f}), but noncausal: passing selects optimized plans {passing['optimized']}/35 vs predecessor {previous['optimized']}/35; rev_compliant_max selects {counter['optimized']}/35 and still fails. Inspect selected iteration, not plan_source alone.",
        'All nine have 35 feasible updates, zero converged updates and 35 deadline misses. These counts cannot distinguish success. Mean update time is roughly 12-18 s for a 0.01 s period; no real-time operation was demonstrated.',
        f"All nine fail the saved settling window; passing terminal speed is {passing['terminal_speed_m_s']:.3f} m/s, above the saved 0.02 m/s settling speed limit. Terminal reach acceptance is narrower than settling.",
        'All saved tensions are below 8 N and no bound entries are saturated. Headroom shows unused actuator range, not proof that a feasible correcting tension trajectory exists.',
        'Passing and some failures have unstable modes at transient frozen points; other failures have none. Neither transient open-loop poles nor static poles certify closed-loop performance.',
        'All 45 measured states fail the equilibrium residual criterion. Nine static force solves converge within the fixed 20-iteration limit; only eight also pass the independent normalized dynamic-drift criterion. c3_compliant_scale1p02 is excluded from equilibrium-only frequency summaries, without a recovery solve.',
        'Unavailable: defensible task-required bandwidth threshold, causal plant/controller decomposition, continuous settling guarantee, and validation against real hardware. No threshold was inferred from the single terminal pass.'
    ]


def verify_saved_study(root):
    """Audit retained evidence and lightweight calculations, without graph/Engine work."""
    from schemas.platform_analysis import OutputLinearizedModel
    p=AnalysisProtocol.model_validate(json.loads((root/'protocol.json').read_text(encoding='utf8')))
    cases=json.loads((root/'case_sources.json').read_text(encoding='utf8'))['cases']
    identities={(c['source_session_id'],c['execution_id']) for c in cases}
    original_files={};build_bindings=[];applicability=[]
    for c in cases:
        source=Path(c['source_directory'])
        descriptor=next(d for d in json.loads((root/'case_sources.json').read_text(encoding='utf8'))['descriptors'] if d['source_session_id']==c['source_session_id'])
        ledger=source/descriptor['live_store']/'platform.sqlite'
        if not ledger.exists(): ledger=source/descriptor['ledger']
        original_files[str(ledger)]=file_hash(ledger)==c['ledger_sha256']
        frozen=source/descriptor['frozen_input']
        original_files[str(frozen)]=file_hash(frozen)==c['frozen_input_sha256']
        source_store=Store(root/'source_ledgers'/c['source_session_id'])
        session=source_store.session(c['source_session_id'])
        build=next(n for n in session['state']['route']['nodes'] if n['node_id']==c['build_node'])
        built=source_store.artifact(build['result'])
        assert build['action']=='build' and build['status']=='completed'
        build_input=source_store.artifact(built['configuration'])
        execution_input=source_store.artifact(c['configuration'])['effective']
        # Route build stores SessionInput; execution stores a candidate envelope.
        # Host compilation canonically sorts the tool grant list.
        for value in (build_input,execution_input): value['policy']['allowed_tools']=sorted(value['policy']['allowed_tools'])
        assert build_input==execution_input and built['candidate_id']==c['candidate_id']
        build_bindings.append(dict(candidate_id=c['candidate_id'],build_result=build['result'],
            build_configuration=built['configuration'],execution_configuration=c['configuration'],
            comparison='Full effective SessionInput equality after sorting allowed_tools only',verified=True))
        from schemas.platform import SessionInput,Binding,Payload
        from extensions.tendon_family.model_applicability import assess_model_uses
        effective=SessionInput.model_validate(source_store.artifact(c['configuration'])['effective'])
        model=Binding(extension_id='model.gvs',version='1.0.0',parameters=Payload(contract='family.gvs_model',
            data=dict(basis=effective.policy.controller.parameters.data['recipe']['basis'])))
        scope=assess_model_uses(effective.robot,effective.task,model,
            ['static_equilibrium','reduced_dynamics','linearization','control_trend','local_model_control'])
        applicability.append(dict(binding=c,assessment=plain(scope),interpretation='Saved comparisons do not confer global physical validation.'))
        for name,location in c['saved_signal_locations'].items():
            if '!' in location:
                import hashlib,zipfile
                archive,member=location.split('!',1)
                with zipfile.ZipFile(archive) as z: actual=hashlib.sha256(z.read(member)).hexdigest()
            else: actual=file_hash(location)
            original_files[location]=actual==c['saved_signal_sha256'][name]
    models=[]; derivative=[]
    for c in cases:
        folder=root/'cases'/c['candidate_id']
        models.extend(OutputLinearizedModel.model_validate(m) for m in json.loads((folder/'physical_models.json').read_text(encoding='utf8')))
        linear=json.loads((folder/'linearizations.json').read_text(encoding='utf8'))
        derivative.extend(r['derivative_check'] for r in linear['records'] if r.get('derivative_check'))
    matlab=json.loads((root/'matlab_scipy_comparison.json').read_text(encoding='utf8'))
    repeat=json.loads((root/'reproducibility.json').read_text(encoding='utf8'))
    host=Host(root/'analysis','offline-math')
    receipts=json.loads((root/'receipts.json').read_text(encoding='utf8'))
    used=host.store.remaining(host.run_id)['used']
    report=dict(distinct_completed_executions=len(identities),model_count=len(models),
        saved_point_count=sum(m.operating_point.get('actual_time_s') is not None for m in models),
        original_files_unchanged=original_files,
        dimensions=sorted({(len(m.x0)//2,len(m.x0),len(m.u0),len(m.y0)) for m in models}),
        protocol_binding_passed=all(m.protocol_identity==digest(plain(p)) for m in models),
        derivative_checks_passed=all(r[k]['passed'] for r in derivative for k in ('dynamics','output')),
        matlab_checks_passed=bool(matlab.get('available')) and all(c['passed'] for r in matlab.get('comparisons',[]) for c in r['checks'].values()),
        repeat_checks_passed=all(c['passed'] for r in repeat for c in r['checks'].values()),
        serialized_outputs_verified=all(host.store.artifact(r['output']) is not None for r in receipts if r.get('output')),
        prohibited_usage_zero=all(used[k]==0 for k in ('model_calls','backend_solves','worker_calls')),
        caller_contract_identical=json.loads((root/'shared_callers.json').read_text(encoding='utf8'))['identical_contract'])
    report.update(verification_acceptance(report))
    atomic_json(root/'verification.json',report)
    atomic_json(root/'build_binding_verification.json',build_bindings)
    atomic_json(root/'model_applicability.json',applicability)
    # Preserve the calculation snapshot, and separately identify later reporting
    # edits. Never relabel earlier artifacts as having been generated by new code.
    execution_identity=json.loads((root/'source_identity.json').read_text(encoding='utf8'))
    changed={f:dict(calculation_hash=h,current_hash=file_hash(f)) for f,h in execution_identity['hashes'].items()
        if Path(f).is_file() and file_hash(f)!=h}
    atomic_json(root/'delivery_source_identity.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        changes_since_calculation_snapshot=changed,
        explanation='Only the offline entry point/reporting and independent tests/documentation were finalized after the numerical run; original calculation identity retained.',
        new_files={str(f).replace('\\','/'):file_hash(f) for folder in ('extensions/math_analysis',) for f in Path(folder).glob('*.py')}))
    assert len(identities)==9 and len(models)==54
    assert all(original_files.values())
    assert all(report[k] for k in ('protocol_binding_passed','derivative_checks_passed','repeat_checks_passed',
        'serialized_outputs_verified','prohibited_usage_zero','caller_contract_identical','matlab_checks_passed'))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--matlab-only',action='store_true',help='Retry only the saved-matrix MATLAB batch after an environment startup failure')
    parser.add_argument('--report-only',action='store_true',help='Verify and render saved results; no graph, static solve, MATLAB session or provider')
    args=parser.parse_args()
    if args.report_only:
        if args.output is None: parser.error('--report-only requires --output of an existing study')
        root=args.output
        load=lambda name: json.loads((root/name).read_text(encoding='utf8'))
        delivery(root,load('comparison.json'),AnalysisProtocol.model_validate(load('protocol.json')),load('matlab_scipy_comparison.json'),load('usage.json'))
        print(json.dumps(verify_saved_study(root),indent=2))
        return
    if args.matlab_only:
        if args.output is None: parser.error('--matlab-only requires --output of an existing study')
        retry_matlab(args.output)
        return
    root=args.output or Path('runs')/('offline_math_analysis_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    root.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    frozen=json.loads((SOURCE/'resolved_frozen_input.json').read_text(encoding='utf8'))
    # Freeze before reading or comparing outcome metrics.
    p=AnalysisProtocol(baseline_lengths_m={c['id']:c['length_m'] for c in frozen['robot']['structure']['data']['components'] if 'length_m' in c},
        frequency_rad_s=np.logspace(-1,3,65).tolist())
    atomic_json(root/'protocol.json',plain(p))
    descriptors=json.loads((SOURCE/'historical_sources.json').read_text(encoding='utf8'))
    sid=json.loads((SOURCE/'live/route_status.json').read_text(encoding='utf8'))['run_id']
    descriptors.append(dict(directory=str(SOURCE),source_session_id=sid,live_store='live',ledger='platform.sqlite.gz',frozen_input='resolved_frozen_input.json'))
    cases=[]
    for d in descriptors: cases.extend(read_cases(d,root))
    keys=[(c['binding']['source_session_id'],c['binding']['execution_id']) for c in cases]
    if len(set(keys))!=9 or len(keys)!=9: raise ValueError('NINE_DISTINCT_EXECUTIONS_REQUIRED')
    # Explicit first slice: passing, immediately preceding failed, bound historical.
    cases=sorted(cases,key=lambda c:(0 if c['binding']['candidate_id'].startswith('b2_near0p169') else 1 if c['binding']['candidate_id'].startswith('b1_near0p17') else 2 if c['binding']['candidate_id']=='rev_compliant_max' else 3,c['binding']['candidate_id']))
    task=digest(cases[0]['effective']['task']); controller=digest(cases[0]['effective']['policy']['controller'])
    if any(digest(c['effective']['task'])!=task or digest(c['effective']['policy']['controller'])!=controller for c in cases):
        raise ValueError('FROZEN_TASK_OR_CONTROLLER_MISMATCH')
    atomic_json(root/'case_sources.json',dict(descriptors=descriptors,cases=[c['binding'] for c in cases]))
    source_files=sorted(set(subprocess.check_output(['git','ls-files'],text=True).splitlines()+[
        str(f).replace('\\','/') for folder in ('extensions/math_analysis',) for f in Path(folder).glob('*.py')]+
        ['schemas/platform_analysis.py','extensions/tendon_family/math_analysis.py','extensions/tendon_family/saved_cases.py','matlab/analyze_linear_model.m','examples/offline_math_analysis.py']))
    atomic_json(root/'source_identity.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        hashes={f:file_hash(f) for f in source_files if Path(f).is_file() and not f.startswith('runs/')}))
    budget=dict(tool_calls=100,model_calls=0,backend_solves=0,worker_calls=0,wall_s=14400.)
    store=Store(root/'analysis');store.create(dict(project_id='offline-analysis',grant_id='offline-analysis-'+uuid4().hex,
        authorization_source='User-authorized deterministic saved-data mathematical study; no provider or physical execution.',budget=budget,exclusive_resources={'matlab':1}))
    value=json.loads(json.dumps(frozen));value['run_id']='offline-math';value['policy'].update(budget=budget,timeout_s=1800.,route=None,model={},
        tool_bindings={k:'1.0.0' for k in ('analysis.linearize_saved_case','analysis.control_metrics','analysis.saved_case','analysis.compare_case_metrics','evidence.read')},allowed_tools=[])
    host=Host(store.root,value['run_id']);host.create(value); pref=save(store,p)
    results=[]; representatives=[]; scipy_records={}; derivative_checks=[]
    for i,case in enumerate(cases):
        print(f"Case {i+1}/9: {case['binding']['candidate_id']}",flush=True)
        cref=save(store,case)
        sref,saved=invoke(host,'analysis.saved_case',dict(case=cref,protocol=pref),'diagnostic-facing');results.append(sref)
        lref,linear=invoke(host,'analysis.linearize_saved_case',dict(case=cref,protocol=pref))
        models=[r['model'] for r in linear['records'] if 'model' in r]
        derivative_checks.extend(dict(candidate=case['binding']['candidate_id'],**r['derivative_check']) for r in linear['records'] if r.get('derivative_check'))
        mref,metrics=invoke(host,'analysis.control_metrics',dict(models=models,protocol=pref,implementation='scipy'));results.append(mref)
        folder=root/'cases'/case['binding']['candidate_id'];folder.mkdir(parents=True)
        for name,data in [('saved_case',saved),('linearizations',linear),('metrics',metrics)]: atomic_json(folder/(name+'.json'),data)
        atomic_json(folder/'physical_models.json',[store.artifact(m) for m in models])
        for record in metrics['records']: scipy_records[record['model_reference']['artifact_id']]=record
        if i<3:
            representatives.append(models[0]); representatives.append(models[-1])
            if i==0: representatives.append(models[3])
        if i==2:
            _,first=invoke(host,'analysis.compare_case_metrics',dict(results=results,protocol=pref),'diagnostic-facing')
            atomic_json(root/'first_slice.json',first)
            print('First three-case end-to-end slice completed.',flush=True)
    atomic_json(root/'derivative_checks.json',derivative_checks)
    matlab_summary={}
    try:
        ref,matlab=invoke(host,'analysis.control_metrics',dict(models=representatives,protocol=pref,implementation='matlab'))
        atomic_json(root/'matlab_metrics.json',matlab)
        matlab_summary=dict(available=True,models=len(representatives),comparisons=[dict(model=r['model_reference'],
            checks=comparison(scipy_records[r['model_reference']['artifact_id']]['raw'],r['raw'],p)) for r in matlab['records']],
            environment=matlab['records'][0]['implementation']['matlab'])
    except Exception as exc:
        matlab_summary=dict(available=False,blocker=str(exc))
    atomic_json(root/'matlab_scipy_comparison.json',matlab_summary)
    # Lightweight repeat from already saved matrices; no graph rebuild or solve.
    repeats=[]
    from schemas.platform_analysis import OutputLinearizedModel
    for ref in representatives[:2]:
        m=OutputLinearizedModel.model_validate(store.artifact(ref)); A,B,C,D=normalized(m)
        again=raw_scipy(A,B,C,D,np.asarray(m.drift)/m.state_scales,p)
        repeats.append(dict(model=ref,checks=comparison(scipy_records[ref['artifact_id']]['raw'],again,p)))
    atomic_json(root/'reproducibility.json',repeats)
    # Both roles consume the identical saved contract through Host.invoke.
    cref,combined=invoke(host,'analysis.compare_case_metrics',dict(results=results,protocol=pref),'design-facing')
    dref,diagnostic=invoke(host,'analysis.compare_case_metrics',dict(results=results,protocol=pref),'diagnostic-facing')
    assert combined==diagnostic
    atomic_json(root/'comparison.json',combined)
    atomic_json(root/'shared_callers.json',dict(design=cref,diagnostic=dref,identical_contract=True))
    usage=store.remaining(host.run_id)
    with store.connect(True) as db:
        receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        counts=dict(model_requests=sum(e['kind']=='model_request' for e in store.events(host.run_id)),workers=db.execute('SELECT count(*) FROM workers').fetchone()[0],
            backend_calls=sum(r['tool_id']=='simulation.run' for r in receipts))
    usage.update(actual_counts=counts,analysis_elapsed_s=time.perf_counter()-start,distinct_candidate_graphs=len(cases),bounded_static_attempts=len(cases),matlab_batches=1)
    atomic_json(root/'usage.json',usage);atomic_json(root/'receipts.json',receipts)
    delivery(root,combined,p,matlab_summary,usage)
    verify_saved_study(root)
    print('Completed: '+str(root),flush=True)


def retry_matlab(root):
    host=Host(root/'analysis','offline-math');store=host.store
    p=AnalysisProtocol.model_validate(json.loads((root/'protocol.json').read_text(encoding='utf8')))
    pref=save(store,p)
    combined=json.loads((root/'comparison.json').read_text(encoding='utf8'))
    representatives=[]; scipy_records={}
    for i,c in enumerate(combined['records']):
        metrics=json.loads((root/'cases'/c['binding']['candidate_id']/'metrics.json').read_text(encoding='utf8'))
        for r in metrics['records']: scipy_records[r['model_reference']['artifact_id']]=r
        if i<3:
            representatives.extend([metrics['records'][0]['model_reference'],metrics['records'][-1]['model_reference']])
            if i==0: representatives.append(metrics['records'][3]['model_reference'])
    ref,matlab=invoke(host,'analysis.control_metrics',dict(models=representatives,protocol=pref,implementation='matlab'))
    atomic_json(root/'matlab_metrics.json',matlab)
    summary=dict(available=True,models=len(representatives),comparisons=[dict(model=r['model_reference'],
        checks=comparison(scipy_records[r['model_reference']['artifact_id']]['raw'],r['raw'],p)) for r in matlab['records']],
        environment=matlab['records'][0]['implementation']['matlab'])
    old=json.loads((root/'matlab_scipy_comparison.json').read_text(encoding='utf8'))
    atomic_json(root/'matlab_startup_failure.json',old)
    atomic_json(root/'matlab_scipy_comparison.json',summary)
    usage=json.loads((root/'usage.json').read_text(encoding='utf8'));usage.update(store.remaining(host.run_id))
    usage['matlab_batches']=1;usage['matlab_startup_failures']=1
    atomic_json(root/'usage.json',usage)
    with store.connect(True) as db: receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
    atomic_json(root/'receipts.json',receipts)
    delivery(root,combined,p,summary,usage)
    verify_saved_study(root)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
