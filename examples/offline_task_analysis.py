"""Deterministic task-time analysis: no provider, worker, backend run, or NMPC solve."""
from __future__ import annotations

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

from examples.offline_math_analysis import comparison
from extensions.math_analysis.kernels import normalized, raw_scipy
from extensions.tendon_family.saved_cases import file_hash, read_cases
from schemas.platform import ToolRequest
from schemas.platform_analysis import (AnalysisProtocol, EndpointTarget, OutputLinearizedModel,
    TaskAnalysisProtocol)
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import atomic_json, digest


BASELINE=Path('runs/offline_math_analysis_20260930_final')
SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923')
PRIMARY=('b2_near0p169_far0p129_compliant_s1p05','b1_near0p17_far0p128_compliant_s1p05')
REVIEWED='c92d91b'
VERSIONS={
    'route.advance':'1.0.0','analysis.linearize_candidate':'1.0.0',
    'analysis.linearize_saved_case':'2.0.0','analysis.saved_case':'2.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0',
    'design.screen':'1.0.0','evidence.read':'1.0.0',
}


def save(store,value):
    with store.transaction() as db: return plain(store.put(db,value))


def invoke(host,name,args,actor='analysis-study',evidence=()):
    host.actor=actor
    receipt=plain(host.invoke(plain(ToolRequest(request_id='task-'+uuid4().hex,tool_id=name,
        tool_version=VERSIONS[name],arguments=args,evidence=list(evidence),
        reason='Deterministic offline task-time analysis; no provider, worker, physical execution, or NMPC solve.',cache='new'))))
    if receipt['execution_status']!='completed': raise RuntimeError(json.dumps(receipt,indent=2))
    return receipt['output'],host.store.artifact(receipt['output']),receipt


def retained_paths():
    names=('protocol.json','case_sources.json','comparison.json','cross_case.csv',
        'matlab_scipy_comparison.json','numerical_summary.json','verification.json','source_identity.json',
        'delivery_source_identity.json','receipts.json')
    paths=[BASELINE/name for name in names]
    paths += sorted((BASELINE/'cases').glob('*/physical_models.json'))
    paths += sorted((BASELINE/'cases').glob('*/metrics.json'))
    paths += sorted((BASELINE/'source_ledgers').glob('*/platform.sqlite'))
    return paths


def seal_baseline(root):
    paths=retained_paths(); before={str(path).replace('\\','/'):file_hash(path) for path in paths}
    old_p=AnalysisProtocol.model_validate(json.loads((BASELINE/'protocol.json').read_text(encoding='utf8')))
    checks=[]
    for candidate,index in ((PRIMARY[0],0),(PRIMARY[0],3),(PRIMARY[1],5)):
        folder=BASELINE/'cases'/candidate
        model=OutputLinearizedModel.model_validate(json.loads((folder/'physical_models.json').read_text(encoding='utf8'))[index])
        saved_metrics=json.loads((folder/'metrics.json').read_text(encoding='utf8'))['records'][index]
        A,B,C,D=normalized(model)
        repeated=raw_scipy(A,B,C,D,np.asarray(model.drift)/model.state_scales,old_p)
        checks.append(dict(candidate_id=candidate,model_index=index,
            checks=comparison(saved_metrics['raw'],repeated,old_p)))
    preserved=all(item['passed'] for row in checks for item in row['checks'].values())
    matlab=json.loads((BASELINE/'matlab_scipy_comparison.json').read_text(encoding='utf8'))
    matlab_passed=bool(matlab.get('available')) and all(check['passed']
        for row in matlab.get('comparisons',[]) for check in row['checks'].values())
    manifest=dict(reviewed_baseline_commit=REVIEWED,actual_start_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(
        ['git','branch','--show-current'],text=True).strip(),original_protocol=str(BASELINE/'protocol.json'),
        immutable_baseline=str(BASELINE),retained_artifact_hashes=before,
        preservation_checks=checks,preservation_passed=preserved,
        retained_matlab_scipy_acceptance=dict(available=matlab.get('available'),passed=matlab_passed,
            status='full_cross_implementation' if matlab_passed else 'scipy_only_partial'),
        note='No report-only or other write operation was run against the retained baseline.')
    atomic_json(root/'baseline_sealing_manifest.json',manifest)
    atomic_json(root/'baseline_numerical_preservation.json',dict(passed=preserved,representatives=checks))
    if not preserved or not matlab_passed: raise RuntimeError('SEALED_BASELINE_ACCEPTANCE_FAILED')
    return before


def build_sources():
    source=json.loads((BASELINE/'case_sources.json').read_text(encoding='utf8'))
    rows=[]
    for binding in sorted(source['cases'],key=lambda row:row['candidate_id']):
        ledger=Store(BASELINE/'source_ledgers'/binding['source_session_id'])
        session=ledger.session(binding['source_session_id'])
        node=next(row for row in session['state']['route']['nodes'] if row['node_id']==binding['build_node'])
        built=ledger.artifact(node['result']); historical=ledger.artifact(built['configuration'])
        rows.append(dict(source_binding=binding,changes=node['selection']['changes'],historical_build=historical,
            historical_build_reference=built['configuration']))
    return rows,source['descriptors']


def scientific_projection(value):
    return dict(robot=value['robot'],task=value['task'],mount=value['task']['environment']['data']['mount'],
        initializer=value['task']['initializer'],controller=value['policy']['controller'],
        dynamics_model=value['policy']['dynamics_model'],discretization=value['policy']['discretization'],
        gvs_basis=value['policy']['controller']['parameters']['data']['recipe']['basis'])


def make_host(root,frozen):
    budget=dict(tool_calls=240,model_calls=0,backend_solves=0,worker_calls=0,wall_s=14400.)
    store=Store(root/'analysis'); store.create(dict(project_id='offline-task-analysis',
        grant_id='offline-task-'+uuid4().hex,authorization_source='User-authorized deterministic analysis-only study.',
        budget=budget,exclusive_resources={'matlab':1}))
    value=json.loads(json.dumps(frozen)); value['run_id']='offline-task-analysis'
    value['policy'].update(budget=budget,timeout_s=1800.,model={},allowed_tools=[],tool_bindings=VERSIONS)
    from extensions.tendon_family.route import create as create_route
    create_route(store.root,value)
    host=Host(store.root,value['run_id'])
    return store,host


def build_and_screen(root,store,host,source_rows,candidate_protocol,target_ref):
    pref=save(store,candidate_protocol); previous=None; bindings=[]; outputs=[]
    folder=root/'configuration_only'; folder.mkdir()
    for index,row in enumerate(source_rows,1):
        screen_id=f'screen-{index:02d}'; node_id=f'screen_build_{index:02d}'
        args=dict(node_id=node_id,action='build',combination='candidate_gvs_nmpc',changes=row['changes'],
            candidate_id=screen_id,evidence=[] if previous is None else [previous],max_trials=1,
            reason='Reconstruct one declared candidate configuration for analysis-only screening.',
            next_step='Run deterministic configuration-only mathematics; never execute the physical backend.')
        bref,built,build_receipt=invoke(host,'route.advance',args,evidence=[] if previous is None else [previous])
        previous=bref
        state=store.session(host.run_id)['state']; node=next(item for item in state['route']['nodes'] if item['node_id']==node_id)
        build_result=store.artifact(node['result']); new_config=store.artifact(build_result['configuration'])
        expected=scientific_projection(row['historical_build']); actual=scientific_projection(new_config)
        equal=expected==actual
        permissions=dict(new=dict(budget=new_config['policy']['budget'],tool_bindings=new_config['policy']['tool_bindings'],
            allowed_tools=new_config['policy']['allowed_tools']),historical=dict(
            budget=row['historical_build']['policy']['budget'],tool_bindings=row['historical_build']['policy']['tool_bindings'],
            allowed_tools=row['historical_build']['policy']['allowed_tools']))
        binding=dict(screen_id=screen_id,new_build_node=node_id,new_build_result=node['result'],
            new_configuration=build_result['configuration'],source_session_id=row['source_binding']['source_session_id'],
            source_build_node=row['source_binding']['build_node'],source_configuration=row['historical_build_reference'],
            scientific_projection_identity=digest(actual),scientific_equality=equal,
            comparison='Exact robot, task/environment/mount, initializer, controller recipe, model, GVS basis and discretization equality.',
            analysis_permissions_recorded_separately=permissions)
        if not equal: raise RuntimeError('SCIENTIFIC_RECONSTRUCTION_MISMATCH: '+screen_id)
        lref,linear,_=invoke(host,'analysis.linearize_candidate',dict(source_node=node_id,protocol=pref))
        models=[item['model'] for item in linear['records'] if 'model' in item]
        mref,metrics,_=invoke(host,'analysis.control_metrics',dict(models=models,protocol=pref,implementation='scipy'))
        eref,endpoint,_=invoke(host,'analysis.bounded_endpoint',dict(models=models,protocol=pref,target=target_ref))
        sref,screen,_=invoke(host,'design.screen',dict(source_node=node_id,protocol=pref,
            linearization=lref,metrics=mref,endpoint=eref),'design-facing')
        candidate_folder=folder/screen_id; candidate_folder.mkdir()
        for name,value in (('linearization',linear),('metrics',metrics),('bounded_endpoint',endpoint),('screen',screen)):
            atomic_json(candidate_folder/(name+'.json'),value)
        bindings.append(binding); outputs.append(dict(screen_id=screen_id,source=row['source_binding'],
            build_node=node_id,linearization=lref,metrics=mref,endpoint=eref,screen=sref,screen_result=screen))
        print(f'Configuration-only screen {index}/9: {screen_id}',flush=True)
    # The same deterministic report contract is callable by both roles.
    first=outputs[0]
    dref,diagnostic,_=invoke(host,'design.screen',dict(source_node=first['build_node'],protocol=pref,
        linearization=first['linearization'],metrics=first['metrics'],endpoint=first['endpoint']),'diagnostic-facing')
    identical=store.artifact(first['screen'])==diagnostic
    atomic_json(root/'shared_screen_callers.json',dict(design=first['screen'],diagnostic=dref,identical_contract=identical))
    atomic_json(root/'public_call_examples.json',dict(versions=VERSIONS,examples=[
        dict(tool_id='analysis.linearize_candidate',arguments=dict(source_node=first['build_node'],protocol=pref)),
        dict(tool_id='analysis.control_metrics',arguments=dict(models=[row['model'] for row in
            store.artifact(first['linearization'])['records'] if 'model' in row],protocol=pref,implementation='scipy')),
        dict(tool_id='analysis.bounded_endpoint',arguments=dict(models=[row['model'] for row in
            store.artifact(first['linearization'])['records'] if 'model' in row],protocol=pref,target=target_ref)),
        dict(tool_id='design.screen',arguments=dict(source_node=first['build_node'],protocol=pref,
            linearization=first['linearization'],metrics=first['metrics'],endpoint=first['endpoint']))],
        note='Wrap each item in the normal ToolRequest envelope and call Host.invoke in the owning analysis session.'))
    atomic_json(root/'configuration_build_bindings.json',bindings)
    atomic_json(root/'configuration_only_complete.json',dict(completed=True,count=len(outputs),
        saved_before_outcome_reveal=True,execution_data_used=False,shared_callers_identical=identical))
    if len(outputs)!=9 or not identical: raise RuntimeError('CONFIGURATION_ONLY_SCREEN_INCOMPLETE')
    return pref,outputs


def load_cases(root,descriptors):
    cases=[]
    for descriptor in descriptors:
        value=dict(descriptor)
        if descriptor['source_session_id']=='gvs-live-f4a6655fe472': value['trajectory_candidate_ids']=list(PRIMARY)
        cases.extend(read_cases(value,root))
    if len(cases)!=9: raise RuntimeError('NINE_CASES_REQUIRED')
    return {case['binding']['candidate_id']:case for case in cases}


def diagnostic_study(root,store,host,cases,protocol):
    pref=save(store,protocol); results={}
    for candidate in PRIMARY:
        cref=save(store,cases[candidate])
        rref,result,_=invoke(host,'analysis.saved_case',dict(case=cref,protocol=pref),'diagnostic-facing')
        results[candidate]=dict(case_ref=cref,result_ref=rref,result=result)
    passing=results[PRIMARY[0]]['result']['records'][0]; predecessor=results[PRIMARY[1]]['result']['records'][0]
    commands={candidate:cases[candidate]['saved']['actual_commands.json'] for candidate in PRIMARY}
    divergence=None
    for index,(a,b) in enumerate(zip(commands[PRIMARY[0]],commands[PRIMARY[1]])):
        delta=np.asarray(a['desired_tension_n'])-np.asarray(b['desired_tension_n'])
        if np.any(np.abs(delta)>1e-12):
            divergence=dict(command_index=index,time_s=a['time_s'],passing_minus_predecessor_n=delta.tolist()); break
    facts=dict(passing_first_positive_noninitialization_time_s=passing['first_positive_noninitialization_time_s'],
        passing_selected_iteration_at_divergence=next(row['selected_iteration'] for row in passing['diagnostic_samples'] if abs(row['timestamp_s']-.23)<1e-9),
        predecessor_initialization_selected_all_updates=predecessor['initialization_selected_all_updates'],
        first_applied_tension_divergence=divergence,
        verified=passing['first_positive_noninitialization_time_s']==.23
            and predecessor['initialization_selected_all_updates'] and divergence['time_s']==.23)
    rows=[]
    by_case={candidate:{row['timestamp_s']:row for row in results[candidate]['result']['records'][0]['diagnostic_samples']} for candidate in PRIMARY}
    for t in (.22,.23,.24):
        a,b=by_case[PRIMARY[0]][t],by_case[PRIMARY[1]][t]
        state=np.asarray(a['projected_state']['measured_initial_state'])-np.asarray(b['projected_state']['measured_initial_state'])
        rows.extend([dict(row,comparison_at_time_s=dict(other_candidate=PRIMARY[1] if candidate==PRIMARY[0] else PRIMARY[0],
            passing_minus_predecessor_state_norm=float(np.linalg.norm(state)),
            passing_minus_predecessor_tip_m=(np.asarray(a['world_tip_position_m'])-np.asarray(b['world_tip_position_m'])).tolist(),
            same_applied_tensions=bool(np.allclose(a['next_interval_applied_input_n'],b['next_interval_applied_input_n'],rtol=0,atol=1e-12))))
            for candidate,row in ((PRIMARY[0],a),(PRIMARY[1],b))])
    atomic_json(root/'control_divergence_facts.json',facts)
    atomic_json(root/'diagnostic_022_023_024.json',rows)
    with (root/'diagnostic_022_023_024.csv').open('w',newline='',encoding='utf8') as stream:
        simple=[]
        for row in rows:
            simple.append(dict(candidate_id=row['candidate_id'],timestamp_s=row['timestamp_s'],
                observation_index=row['observation_index'],command_index=row['command_index'],
                selection_kind=row['selection_kind'],selected_iteration=row['selected_iteration'],
                target_error_m=row['target_error_norm_m'],projection_residual=row['projected_state']['projection_residual_max_rad_m'],
                previous_input_n=json.dumps(row['previous_applied_input_n']),next_input_n=json.dumps(row['next_interval_applied_input_n']),
                tension_change_n=json.dumps(row['tension_change_from_previous_n']),
                gvs_tip_velocity_m_s=json.dumps(row['gvs_derived_instantaneous_tip_velocity']['value_m_s']),
                backend_velocity_estimates=json.dumps(row['backend_tip_velocity_estimates']),
                prediction_discrepancy_m=None if row['one_step_discrepancy'] is None else row['one_step_discrepancy']['norm_m']))
        writer=csv.DictWriter(stream,fieldnames=simple[0]); writer.writeheader(); writer.writerows(simple)
    atomic_json(root/'diagnostic_interpretation.json',dict(observed_facts=[
        'The two command sequences are identical through 0.22 s and first differ at 0.23 s.',
        'At 0.23 s the passing case selects positive iteration 19; the predecessor selects initialization iteration 0 at every update.',
        'Projected states and world tips already differ before 0.23 s because the geometries differ despite equal tensions.',
        'Backend velocity is available only as explicitly interval-labelled finite differences; GVS J(q)qdot values are separate model-derived signals.',
        'No saved full optimizer iterate or full objective plan is available.'],conditional_hypotheses=[
        'The noninitialization selection may have contributed to the later trajectory, but temporal association does not establish why the case passed.',
        'Geometry-dependent state evolution and subsequent tension changes are both plausible contributors; the saved evidence does not identify a causal decomposition.'],
        unsupported=['Plan-selection divergence is not proof of success causation.','No optimizer or NMPC rerun was performed.']))
    if not facts['verified']: raise RuntimeError('SAVED_DIVERGENCE_FACTS_NOT_VERIFIED')
    return pref,results


def saved_endpoint_study(root,store,host,cases,primary_protocol,late_protocol,target_ref):
    outputs={}; primary_pref=save(store,primary_protocol); late_pref=save(store,late_protocol)
    for candidate in PRIMARY:
        cref=save(store,cases[candidate])
        lref,linear,_=invoke(host,'analysis.linearize_saved_case',dict(case=cref,protocol=primary_pref,include_static_equilibrium=False))
        models=[row['model'] for row in linear['records'] if 'model' in row]
        mref,metrics,_=invoke(host,'analysis.control_metrics',dict(models=models,protocol=primary_pref,implementation='scipy'))
        eref,endpoint,_=invoke(host,'analysis.bounded_endpoint',dict(models=models,protocol=primary_pref,target=target_ref))
        outputs[candidate]=dict(linearization=linear,metrics=metrics,endpoint=endpoint,references=dict(linear=lref,metrics=mref,endpoint=eref))
    late_models=[]; late_linear={}
    for candidate,case in sorted(cases.items()):
        cref=save(store,case)
        lref,linear,_=invoke(host,'analysis.linearize_saved_case',dict(case=cref,protocol=late_pref,include_static_equilibrium=False))
        model=next(row['model'] for row in linear['records'] if 'model' in row)
        late_models.append(model); late_linear[candidate]=dict(reference=lref,result=linear,model=model)
    mref,metrics,_=invoke(host,'analysis.control_metrics',dict(models=late_models,protocol=late_pref,implementation='scipy'))
    eref,endpoint,_=invoke(host,'analysis.bounded_endpoint',dict(models=late_models,protocol=late_pref,target=target_ref))
    metric_map={row['binding']['candidate_id']:row for row in metrics['records']}
    endpoint_map={row['binding']['candidate_id']:row for row in endpoint['records']}
    late=[]
    for candidate in sorted(cases):
        baseline=json.loads((BASELINE/'cases'/candidate/'metrics.json').read_text(encoding='utf8'))
        old=next(row for row in baseline['records'] if row['operating_point'].get('requested_time_s')==.34)
        nominal=old['windows'][-1]
        late.append(dict(candidate_id=candidate,actual_remaining_s=.01,
            task_time=endpoint_map[candidate],nominal_window_s=nominal['window_s'],
            nominal_continuous_energy=nominal['continuous']['minimum_energy'],
            nominal_held_energy=nominal['held']['minimum_energy'],new_metrics=metric_map[candidate],
            interpretation='Task-time result is 1 held step; nominal 0.35 s energy is retained only as a distinct baseline quantity.'))
    atomic_json(root/'primary_remaining_time_analysis.json',outputs)
    atomic_json(root/'late_remaining_time_all_cases.json',late)
    atomic_json(root/'late_public_references.json',dict(linearizations={k:v['reference'] for k,v in late_linear.items()},metrics=mref,endpoint=eref))
    return outputs,late


def reveal_outcomes(root,screen_outputs,cases):
    source_by_id={row['source']['candidate_id']:row for row in screen_outputs}
    mapping=[]
    for historical,screen in sorted(source_by_id.items()):
        result=cases[historical]['factual_result']; report=screen['screen_result']['records'][0]
        points=[row for row in report['operating_points'] if row.get('available')]
        point_metrics=[dict(name=row['point'].get('name'),held_weak_eigenvalue=row['local_directions']['held_output']['eigenvalues'][0],
            position_status=row['task_time']['position_only']['status'],braking_status=row['task_time']['position_and_braking']['status'])
            for row in points]
        mapping.append(dict(screen_id=screen['screen_id'],historical_candidate_id=historical,
            task_accepted=result['task_accepted'],terminal_error_m=result['terminal_error_m'],
            terminal_tip_speed_m_s=result['terminal_tip_speed_m_s'],
            available_operating_points=len(points),position_feasible_witnesses=report['priority_reasoning']['position_feasible_witnesses'],
            braking_feasible_witnesses=report['priority_reasoning']['braking_feasible_witnesses'],
            point_metrics=point_metrics,
            initial_held_weak_eigenvalue=None if not points else points[0]['local_directions']['held_output']['eigenvalues'][0]))
    signatures={(row['position_feasible_witnesses'],row['braking_feasible_witnesses'],
        tuple((point['name'],round(point['held_weak_eigenvalue'],12),point['position_status'],point['braking_status']) for point in row['point_metrics']))
        for row in mapping}
    assessment=dict(outcomes_revealed_after_configuration_only_save=True,rows=mapping,
        genuinely_preexecution_information=['immutable robot/task/controller/model configuration','declared pretension and bounds',
            'configuration-derived operating points','local Jacobians','nominal and task-time bounded local witnesses','model applicability'],
        unavailable_preexecution_information=['executed terminal error','observed tensions','optimizer selections/history','backend trajectory'],
        distinguishes_candidates=len(signatures)>1,
        ties='Common straight-configuration rank limitations and equal status counts remain ties where present.',
        counterexamples=['Several failed cases have two local position-feasible pre-execution operating points while the sole passing case has one; witness count cannot rank success.',
            'The failed predecessor and passing case tie at one position and one braking witness; status counts do not distinguish them.',
            'A stronger local metric in a failed historical case remains a counterexample to treating any single local metric as a success score.',
            'A feasible local position witness without a braking witness does not imply the original nonlinear execution will pass or settle.'],
        prioritization='Conditional evidence may prioritize follow-up analysis, but this nine-case retrospective set supports no fitted score, threshold, or guaranteed ranking.')
    atomic_json(root/'revealed_outcome_comparison.json',assessment)
    return assessment


def finalize(root,store,host,before,protocols,outcome,started):
    after={str(path).replace('\\','/'):file_hash(path) for path in retained_paths()}
    immutable=before==after
    usage=store.remaining(host.run_id)
    with store.connect(True) as db:
        receipts=[json.loads(row[0]) for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        workers=db.execute('SELECT count(*) FROM workers').fetchone()[0]
    usage.update(actual_counts=dict(model_requests=sum(event['kind']=='model_request' for event in store.events(host.run_id)),
        workers=workers,backend_calls=sum(row.get('tool_id')=='simulation.run' for row in receipts)),
        elapsed_s=time.perf_counter()-started,matlab_batches=0,nmpc_solves=0,physical_backend_executions=0)
    atomic_json(root/'protocols.json',{name:plain(value) for name,value in protocols.items()})
    atomic_json(root/'receipts.json',receipts); atomic_json(root/'resource_usage.json',usage)
    snapshot=store.session(host.run_id)['snapshot']
    atomic_json(root/'dependencies.json',dict(run_id=host.run_id,project_commit=snapshot.get('project_commit'),
        worktree_dirty=snapshot.get('worktree_dirty'),dependencies=snapshot['dependencies'],
        selected_implementation_environment=json.loads((root/'configuration_only/screen-01/metrics.json').read_text(encoding='utf8'))['records'][0]['implementation']))
    source_files=('schemas/platform_analysis.py','extensions/math_analysis/kernels.py','extensions/math_analysis/tools.py',
        'extensions/math_analysis/manifest.py','extensions/math_analysis/matlab.py','extensions/tendon_family/math_analysis.py',
        'extensions/tendon_family/saved_cases.py','extensions/tendon_family/candidate_analysis.py',
        'extensions/tendon_family/model_applicability.py','extensions/tendon_family/gvs_casadi.py',
        'examples/offline_task_analysis.py','examples/offline_math_analysis.py','matlab/analyze_linear_model.m',
        'tests/test_math_analysis.py','tests/test_task_analysis.py','docs/offline_math_analysis.rst')
    atomic_json(root/'source_identity.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
        hashes={name:file_hash(name) for name in source_files}))
    atomic_json(root/'baseline_immutability_check.json',dict(passed=immutable,before=before,after=after))
    verification=dict(baseline_immutable=immutable,nine_completed_builds=len(store.session(host.run_id)['state']['route']['nodes'])==9,
        configuration_only_before_outcomes=True,prohibited_usage_zero=all(usage['used'][key]==0 for key in ('model_calls','backend_solves','worker_calls')),
        public_calls_completed=all(row['execution_status']=='completed' for row in receipts),
        shared_contract=json.loads((root/'shared_screen_callers.json').read_text(encoding='utf8'))['identical_contract'],
        outcome_count=len(outcome['rows']))
    verification['passed']=all(verification.values())
    atomic_json(root/'verification.json',verification)
    report=['Offline task-time and design screening analysis','',
        '1. Interface fixes and baseline preservation',
        'SciPy public calls no longer require MATLAB Engine; discrete input models and misaligned sampled horizons are rejected. The retained baseline was not rewritten and representative numerical matrices were preserved.',
        '', '2. Observed control divergence',
        'The saved primary command sequences first differ at 0.23 s. The passing case selects noninitialization iteration 19 there; the predecessor selects initialization at all 35 updates. Their states already differ before this event because their geometries differ.',
        '', '3. Conditional local-model correction and braking',
        'Exact-ZOH affine endpoint calculations use actual remaining task time, affine drift, and 0 <= applied tension <= candidate limits. Position and terminal-speed constraints are reported separately; undetermined is never relabelled infeasible. At t=0.34 the calculation uses one 0.01 s step, while original 0.35 s energy remains a distinct nominal baseline.',
        '', '4. Actual pre-execution screening capability',
        'Nine genuine completed build nodes were created without Route run actions. Configuration-only screens use declared initial/pretension data, one bounded target-static attempt, one fixed halfway waypoint, shared control metrics, bounded endpoint results and applicability. Historical outcomes were joined only after these artifacts were saved. No scalar score or fitted threshold was created.',
        '', '5. Unsupported conclusions',
        'The evidence does not prove why the passing execution succeeded, global or physical feasibility/infeasibility, nonlinear settling, real-time operation, or prospective independent validation. Rank two at the straight configuration is not a global reach rejection.',
        '', 'Reproduction (PowerShell, from D:\\softrobot-agent):',
        "& 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe' examples/offline_task_analysis.py",
        '', 'Public call chain: route.advance(build) -> analysis.linearize_candidate -> analysis.control_metrics -> analysis.bounded_endpoint -> design.screen. The same design.screen report was consumed by design-facing and diagnostic-facing callers.',
        '', 'Resource usage:',json.dumps(usage,indent=2)]
    (root/'report.txt').write_text('\n'.join(report),encoding='utf8')
    if not verification['passed']: raise RuntimeError('FINAL_VERIFICATION_FAILED')


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path)
    args=parser.parse_args(); root=args.output or Path('runs')/('offline_task_analysis_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    root.mkdir(parents=True,exist_ok=False); started=time.perf_counter()
    before=seal_baseline(root); frozen=json.loads((SOURCE/'resolved_frozen_input.json').read_text(encoding='utf8'))
    lengths={row['id']:row['length_m'] for row in frozen['robot']['structure']['data']['components'] if 'length_m' in row}
    common=dict(baseline_lengths_m=lengths,frequency_rad_s=np.logspace(-1,3,65).tolist())
    protocols=dict(candidate=TaskAnalysisProtocol(**common,samples_s=[]),
        primary=TaskAnalysisProtocol(**common,samples_s=[.22,.23,.24]),
        late=TaskAnalysisProtocol(**common,samples_s=[.34]))
    target=EndpointTarget(position_m=tuple(frozen['task']['goal']['data']['target_m']),
        position_tolerance_m=frozen['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
        tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02)
    atomic_json(root/'frozen_protocols_initial.json',{name:plain(value) for name,value in protocols.items()})
    source_rows,descriptors=build_sources(); store,host=make_host(root,frozen); target_ref=save(store,target)
    _,screens=build_and_screen(root,store,host,source_rows,protocols['candidate'],target_ref)
    cases=load_cases(root,descriptors)
    atomic_json(root/'case_sources.json',dict(descriptors=descriptors,cases=[case['binding'] for case in cases.values()]))
    diagnostic_study(root,store,host,cases,protocols['primary'])
    saved_endpoint_study(root,store,host,cases,protocols['primary'],protocols['late'],target_ref)
    outcomes=reveal_outcomes(root,screens,cases)
    finalize(root,store,host,before,protocols,outcomes,started)
    print('Completed: '+str(root),flush=True)


if __name__=='__main__': main()
