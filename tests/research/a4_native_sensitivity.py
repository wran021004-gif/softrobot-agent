"""One explicitly authorized, <=20,000-step A4 engineering experiment.

Run once from a clean committed worktree. Uses the production generator,
analysis/Worker/Store, control search, task adapter and evidence projections.
Existing source archives are read only. No Provider or independent task pass.
"""
from copy import deepcopy
from pathlib import Path
import sys
import time

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import plain
from tools.research import core,analysis,design
from tools.research.state import state,save,update
from tools.research.numerics import archived
from tools.research.physical_replay import seed_control
from tools.research.contracts import ControlSeedRequest
from tools.research.evidence_views import result_card
from tools.research.research_context import mathematical_decision_view
from tools.research.task_constraints import mathematical_method_view
from tools.research.nonlinear_capability import T1,T2
from extensions.tendon_family.mujoco_analysis import NativeModel

CAP=20000
FOLDER=ROOT/'runs/mujoco-native-task-sensitivity'
DIRECTIONS=[('segments.0.young_pa',10000.,'Pa'),('spans.0.radius_m',.00001,'m'),
    ('segments.0.sections.0.parameters.semi_y_m',.00001,'m')]
SETTINGS=dict(version='local_control_search_v2',knots_s=[0.,.34],correction_window_s=[0.,.35],
    evaluation_requests=3,iterations=1,active_coefficients=[0],difference_step_n=.01)


def prepare():
    old=read(ROOT/'evidence/mujoco_task_capability_parameters_smoke/configuration.json')
    example=read(ROOT/'evidence/mujoco_task_capability_parameters_smoke/example.json')
    source=archived('evidence/mujoco_task_capability_parameters_smoke',example['baseline_candidate'])
    FOLDER.mkdir(parents=True,exist_ok=True)
    task=dict(seed=source['configuration']['seed'],task=source['configuration']['task'],
        settling=source['configuration']['policy']['controller']['parameters']['data']['settling'])
    taskpath=FOLDER/'task.json';atomic_json(taskpath,task)
    cfg=read(ROOT/'configs/research/study_variable_segments_dev.json')
    cfg.update(study_id='mujoco-native-task-sensitivity-a4',family_space='family_space_s7.json',task=str(taskpath),
        authorization='User A4 attachment: finite native mechanics and independent sensitivity predictions; <=20000 new physics steps.',
        mathematical_methods={T1:'A4 bounded native engineering verification',T2:'A4 saved-evidence sensitivity and prediction validation'},
        family_sensitivity_variables=old['family_sensitivity_variables'],native_control_limits=dict(evaluation_requests=3,iterations=1,knots_s=2))
    cfg['budgets'].update(mathematical_evaluations=64,public_operations=128,protected_public_operations=0)
    path=ROOT/'configs/research/a4_native_engineering.json';atomic_json(path,cfg)
    try:host=core.prepare(path,FOLDER/'store')
    finally:path.unlink()
    if state(host).get('freeze')!=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip():
        core.bind(host,reason='A4 local implementation correction; all prior results and costs retained.' if state(host).get('freeze') else None)
    return host,source


def costs(host):
    rows=[]
    for ref in state(host).get('analysis_results',[]):
        raw=host.store.artifact(ref)
        for cost in raw.get('internal_calculations',[]):rows.append(cost)
    for ref in state(host).get('research_mathematics',[]):
        cost=host.store.artifact(ref).get('cost')
        if cost:rows.append(cost)
    return {k:sum(c.get(k,0) for c in rows) for k in
        ('physics_steps','model_builds','forward_evaluations','mechanics_evaluations','rollouts','kernel_wall_s')}


def run_analysis(host,query,key,ceiling):
    assert costs(host)['physics_steps']+ceiling<=CAP
    out=analysis.dispatch(host,query,key,guard=core.guard,origin='engineering_preflight')
    raw=host.store.artifact(out['reference'])
    print(key,raw['status'],costs(host),flush=True)
    assert raw['status']=='computed',(out,raw.get('reason'))
    return out['reference'],raw


def r1_audit(host):
    existing=next((ref for ref in state(host).get('research_mathematics',[]) if
        host.store.artifact(ref).get('kind')=='A4_R1_native_contact_audit'),None)
    if existing:return existing
    package=read(ROOT/'evidence/b3_r1_history_assisted_050/design_package.json')
    cfg=package['configuration'];tr=package['control']['trajectory']
    assert costs(host)['physics_steps']+1000<=CAP
    started=time.perf_counter();native=NativeModel(cfg)
    try:
        d=mujoco.MjData(native.model);d.qpos[native.qi]=native.scene['qpos_rad'];d.qvel[native.vi]=native.scene['qvel_rad_s']
        native.forward(d);outputs=native.rollout_sequence(d,tr['times_s'],tr['tensions_n'])
        result=dict(status='applicable',terminal=outputs['tip_positions_m'][-1])
    except ValueError as exc:
        result=dict(status='not_applicable',reason=str(exc),diagnostic=getattr(exc,'native_diagnostic',None))
    result.update(kind='A4_R1_native_contact_audit',candidate=package['candidate'],
        source='evidence/b3_r1_history_assisted_050/design_package.json',
        cost=dict(**native.cost,kernel_wall_s=time.perf_counter()-started))
    ref=save(host,result,'native_contact_audit');update(host,research_mathematics=[*state(host).get('research_mathematics',[]),ref],
        numerical_s=state(host)['numerical_s']+result['cost']['kernel_wall_s'])
    print('R1',result,flush=True)
    return ref


def r1_peak_mechanics(host):
    """Original R1 measured coordinates; reset history, no replay or projection."""
    existing=next((r for r in state(host).get('research_mathematics',[]) if
        host.store.artifact(r).get('kind')=='A4_R1_peak_mechanics'),None)
    if existing:return existing
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    from tools.research_tasks import task_adapter
    from tools.research.nonlinear_capability import sampled_constraints
    package=read(ROOT/'evidence/b3_r1_history_assisted_050/design_package.json')
    raw=archived('evidence/b3_r1_history_assisted_050',package['raw_reference'])
    cfg=package['configuration'];hold=task_adapter(cfg).holding_start_s()
    index=max((i for i,s in enumerate(raw['samples']) if s['time_s']>=hold-1e-12),key=lambda i:raw['samples'][i]['speed_m_s'])
    sample=raw['samples'][index];started=time.perf_counter();native=NativeModel(cfg)
    point=dict(dof_order=native.order,tendon_order=native.tendons,qpos_rad=sample['qpos_rad'],qvel_rad_s=sample['qvel_rad_s'],actual_time_s=sample['time_s'])
    u=sample['actual_tension_n'];d=native.restore(point,comparable=True);mechanics=native.mechanics(d,u)
    # These directions are frozen here before any perturbation model is built.
    paths=[('segments.1.young_pa',10000.,'Pa'),('spans.0.radius_m',.00001,'m'),('segments.1.sections.0.parameters.radius_m',.00001,'m')]
    directions=[];model_costs=[native.cost]
    builder=cfg['policy']['candidate_builder']['parameters']['data']
    from tools.research.task_constraints import describe_analysis_requirements
    req=describe_analysis_requirements(cfg,{})
    outputs=dict(times_s=[s['time_s'] for s in raw['samples']],tip_positions_m=[s['tip_m'] for s in raw['samples']],
        tip_velocities_m_s=[s['tip_velocity_m_s'] for s in raw['samples']])
    for path,h,unit in paths:
        probes=[]
        for factor in (-1.,1.,-.5,.5):
            p=deepcopy(package['design_parameters']);p.pop('controller_recipe',None)
            design.set_parameter(p,path,design.parameter_value(p,path)+factor*h)
            build=parse_build(dict(space=builder['space'],request=p));robot,mesh,_=generate_family(build)
            other_cfg=deepcopy(cfg);other_cfg['robot']['structure']['data']=robot;other_cfg['policy']['discretization']['data']=mesh
            other=NativeModel(other_cfg);state_at_point=other.restore(point,comparable=True)
            changed=other.mechanics(state_at_point,u);model_costs.append(other.cost)
            fields=('mass_matrix_kg_m2','input_force_map_nm_n','tendon_jacobian_m_rad','qacc_rad_s2','tip_acceleration_m_s2')
            probes.append(dict(delta=factor*h,physics_identity=other.physics['identity'],mechanics=changed,
                relative_changes={k:float(np.linalg.norm(np.asarray(changed[k])-mechanics[k])/max(np.linalg.norm(mechanics[k]),1e-15)) for k in fields}))
        directions.append(dict(variable=path,base_value=design.parameter_value(package['design_parameters'],path),unit=unit,step=h,probes=probes,
            scope='Fixed native qpos/qvel/input only. No R1 full-task structural prediction or reoptimization.'))
    result=dict(kind='A4_R1_peak_mechanics',source=package['raw_reference'],sample_index=index,
        state_comparison='Original measured native qpos/qvel and actual input; reset history in all models',
        input_phase='Previous applied interval tension at measured post-step state; not a new command',
        mechanics=mechanics,directions=directions,original_task_samples=sampled_constraints(outputs,req),
        cost={k:sum(c[k] for c in model_costs) for k in native.cost})
    result['cost']['kernel_wall_s']=time.perf_counter()-started
    ref=save(host,result,'native_R1_mechanics_and_physical_responses')
    update(host,research_mathematics=[*state(host).get('research_mathematics',[]),ref],numerical_s=state(host)['numerical_s']+result['cost']['kernel_wall_s'])
    return ref


def compact_summary(summary):
    """Keep one small delivery index; original arrays and sources stay in Store."""
    for direction in summary['structure_predictions']:
        direction['metric_responses']=[dict(metric=m['metric'],unit=m['unit'],secant_unit=m.get('secant_unit'),
            **{scope:{k:v for k,v in m[scope].items() if k!='sources'} for scope in ('fixed_control','reoptimized_control')})
            for m in direction['metric_responses']]
    summary['control_prediction_validation']['validation'].pop('samples',None)
    return summary


def postflight_review(host,t2):
    """Re-read saved samples with the final stricter policy; zero native calls."""
    from tools.research.contracts import AnalysisRequest
    from tools.research.nonlinear_capability import saved_context,response
    started=time.perf_counter();raw=host.store.artifact(t2)
    value=response(saved_context(host,AnalysisRequest.model_validate(raw['requested_operation'])))
    card=plain(result_card(host,t2));view=mathematical_decision_view(card)
    assert view['nonlinear_response']['direction_count']==3 and view['nonlinear_response']['stencil_count']==6
    assert len(view['nonlinear_response']['directions'])==3
    exact=dict(reference=t2,view='full',pointer='/nonlinear_response/directions/0/task_sensitivity/fixed_control/finite_difference_per_unit')
    assert core.read_evidence(host,exact,record_read=False)==raw['nonlinear_response']['directions'][0]['task_sensitivity']['fixed_control']['finite_difference_per_unit']
    result=dict(kind='A4_postflight_saved_sample_review',source=t2,
        practical_error_fraction_of_actual_change=.25,material_normalized_change=1e-8,
        interpretation='Stricter final empirical policy; original T2 artifact and numeric samples unchanged. Not an error bound.',
        structural=[dict(direction_id=d['direction_id'],scopes={k:v['status'] for k,v in d['task_sensitivity'].items()}) for d in value['directions']],
        normalized_sensitivities=[dict(direction_id=d['direction_id'],
            scopes={k:dict(legal_coordinate_span=v['legal_coordinate_span'],dimensionless_sensitivity=v['dimensionless_sensitivity'],
                raw_sample_pointer=f'/nonlinear_response/directions/{i}/task_sensitivity/{k}/samples',
                raw_derivative_pointer=f'/nonlinear_response/directions/{i}/task_sensitivity/{k}/finite_difference_per_unit')
                for k,v in d['task_sensitivity'].items()}) for i,d in enumerate(value['directions'])],
        control_status=value['control_prediction_validation']['status'],l0_physical_paths=3,l0_stencils=6,
        exact_matrix_query=exact,
        cost=dict(model_builds=0,physics_steps=0,rollouts=0,kernel_wall_s=time.perf_counter()-started))
    ref=save(host,result,'saved_sample_policy_review')
    update(host,research_mathematics=[*state(host).get('research_mathematics',[]),ref],numerical_s=state(host)['numerical_s']+result['cost']['kernel_wall_s'])
    return ref


def main():
    delivered=ROOT/'evidence/mujoco_native_task_sensitivity/summary.json'
    if delivered.exists() and (FOLDER/'store/platform.sqlite').exists():
        print('A4_ALREADY_DELIVERED',read(delivered)['cost'],flush=True)
        return
    host,source=prepare();r1=r1_audit(host)
    generated={};t1={};raws={}
    def generate(parameters,label):
        out=design.generate_candidate(host,parameters,dict(origin='A4 frozen finite verification',label=label))
        assert out['status']=='generated',out
        return out['candidate'],design.verify_candidate(host,out['candidate'])
    generated['baseline']=generate(source['parameters'],'baseline')
    baseline,c=generated['baseline'];assert c['configuration']['task']==source['configuration']['task']
    assert c['configuration']['robot']==source['configuration']['robot']
    def search(label,candidate,step=.01):
        source_control=seed_control(host,ControlSeedRequest(candidate=candidate,tensions_n=[[1.,1.,1.]]))
        settings=dict(SETTINGS,difference_step_n=step)
        query=dict(candidate=candidate,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=state(host)['spec']['analysis_protocol'],
            control_optimization=dict(source=source_control['source'],settings=settings))
        ref,raw=run_analysis(host,query,'a4-t1-'+label,525);t1[label]=ref;raws[label]=raw
        return ref
    search('baseline',baseline)
    directions=[]
    for j,(path,h,unit) in enumerate(DIRECTIONS):
        for factor in (-1.,1.,-.5,.5,.75):
            label=f'{j}_{factor}';p=deepcopy(source['parameters'])
            design.set_parameter(p,path,design.parameter_value(p,path)+factor*h)
            generated[label]=generate(p,label);search(label,generated[label][0])
        for scale in (1.,.5):
            directions.append(dict(direction_id=f'{path}@{scale}h',variables={path:1.},coordinate_unit=unit,
                coordinates=[0.,-h*scale,h*scale],t1_results=[t1['baseline'],t1[f'{j}_{-scale}'],t1[f'{j}_{scale}']],
                validation_coordinates=[.75*h],validation_t1_results=[t1[f'{j}_0.75']]))
    search('control_fine',baseline,.005);search('control_holdout',baseline,.0075)
    query=dict(candidate=baseline,operation='mujoco_reoptimized_structure_response_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=state(host)['spec']['analysis_protocol'],
        nonlinear_response=dict(version='nonlinear_response_v2',directions=directions,
            control_validation_t1_results=[t1['baseline'],t1['control_fine'],t1['control_holdout']]))
    t2,aggregate=run_analysis(host,query,'a4-t2-independent-predictions',0)
    point=raws['baseline']['native_dynamics']['baseline_peak_speed_state']
    pointref=save(host,point,'A4_original_native_peak_state');update(host,scoped_context=[*state(host)['scoped_context'],pointref])
    basequery=dict(candidate=baseline,model_source='mujoco',operating_point='saved_state',saved_state=pointref,
        protocol=state(host)['spec']['analysis_protocol'])
    mechanics,mechanics_raw=run_analysis(host,dict(basequery,operation='native_dynamics_v1'),'a4-peak-native-mechanics',0)
    # Verify engine extraction at the exact saved state without advancing physics.
    if not any(host.store.artifact(r).get('kind')=='A4_direct_native_checks' for r in state(host).get('research_mathematics',[])):
        started=time.perf_counter();native=NativeModel(c['configuration']);d=native.restore(point);native.apply(d,point['u'])
        mass=np.empty((native.model.nv,native.model.nv));mujoco.mj_fullM(native.model,d,mass)
        m=mechanics_raw['native_dynamics']['mechanics']
        np.testing.assert_array_equal(mass[np.ix_(native.vi,native.vi)],m['mass_matrix_kg_m2'])
        np.testing.assert_array_equal(d.qacc[native.vi],m['qacc_rad_s2'])
        np.testing.assert_array_equal(d.qpos[native.qi],m['qpos_rad'])
        result=dict(kind='A4_direct_native_checks',array_equal=['mj_fullM','qacc','qpos'],
            mjd_transitionFD=dict(binding_available=hasattr(mujoco,'mjd_transitionFD'),
                integrator=int(native.model.opt.integrator),solver=int(native.model.opt.solver),
                physics_steps_per_control_interval=round(.01/native.model.opt.timestep),
                choice='Reuse output probes over full task. No dense state Jacobian or uncounted derivative calls.'),
            cost=dict(**native.cost,kernel_wall_s=time.perf_counter()-started))
        ref=save(host,result,'native_array_verification');update(host,research_mathematics=[*state(host).get('research_mathematics',[]),ref],
            numerical_s=state(host)['numerical_s']+result['cost']['kernel_wall_s'])
    paired={}
    for j,(path,h,unit) in enumerate(DIRECTIONS):
        for label,factors in [('coarse',[-1.,1.]),('fine',[-.5,.5]),('holdout',[.75])]:
            ref,raw=run_analysis(host,dict(basequery,operation='fixed_input_structure_v1',native=dict(horizon_s=.01),
                structure_response=dict(variable=path,candidates=[generated[f'{j}_{factor}'][0] for factor in factors])),
                f'a4-mechanics-{j}-{label}',5*(1+len(factors)))
            paired[f'{j}_{label}']=dict(reference=ref,changes=[dict(candidate=r['candidate'],delta=r['delta'],
                mechanism_changes={k:{name:value for name,value in change.items() if name!='finite_difference_per_parameter'}
                    for k,change in r['mechanism_changes'].items() if k!='generalized_forces_nm'})
                for r in raw['native_dynamics']['structure_responses']])
    card=plain(result_card(host,t2));view=mathematical_decision_view(card)
    l1=dict(reference=t2,view='working_set',pointer='/mathematical_decision_view/nonlinear_response')
    assert core.read_evidence(host,l1,record_read=False)==view['nonlinear_response']
    wire=__import__('json').dumps(view)
    assert 'finite_difference_per_unit' not in wire and 'mass_matrix_kg_m2' not in wire
    before=state(host)['numerical_s'];reuse=analysis.dispatch(host,query,'a4-t2-independent-predictions',guard=core.guard,origin='engineering_preflight')
    assert reuse['operation_reuse']['additional_analysis_evaluations']==0 and state(host)['numerical_s']==before
    catalog=mathematical_method_view(host,baseline)['methods'][T2]
    assert catalog['batch_request'] and catalog['applicable']
    assert not catalog['executable'] and 'formal_study_math_scope_required' in catalog['missing']
    r1_mechanics=r1_peak_mechanics(host)
    review=postflight_review(host,t2)
    total=costs(host);assert total['physics_steps']<=CAP
    final=aggregate['nonlinear_response']
    summary=dict(label='A4 bounded real MuJoCo experiment; no independent task acceptance',implementation=state(host)['freeze'],
        store=str(host.store.root),budget_physics_steps=CAP,cost=total,
        analysis_evaluations=state(host)['mathematical_evaluations'],numerical_s=state(host)['numerical_s'],
        original_store_ledger=host.store.remaining(),r1_audit=dict(reference=r1,value=host.store.artifact(r1)),
        r1_peak_mechanics=dict(reference=r1_mechanics,query=dict(reference=r1_mechanics,view='full',pointer='/mechanics')),
        final_saved_sample_review=dict(reference=review,value=host.store.artifact(review)),
        baseline_candidate=baseline,baseline_metrics=raws['baseline']['nonlinear_capability']['initial_metrics'],
        peak_native_mechanics=dict(reference=mechanics,query=dict(reference=mechanics,view='full',pointer='/native_dynamics/mechanics'),
            time_s=point['actual_time_s'],mass_balance_residual_inf_nm=mechanics_raw['native_dynamics']['mechanics']['mass_balance_residual_inf_nm']),
        t1_results=t1,t2_result=t2,exact_l1_query=l1,comparison_summary=final['comparison_summary'],
        structure_predictions=[dict(direction_id=d['direction_id'],step=d['step'],
            scopes={scope:dict(status=v['status'],reasons=v['reasons'],scale_comparisons=v['scale_comparisons'],
                active_switches=v['active_switches'],validation=[{k:x for k,x in check.items() if k!='samples'} for check in v['validation']])
                for scope,v in d['task_sensitivity'].items()},metric_responses=d['metric_responses']) for d in final['directions']],
        control_prediction_validation=final['control_prediction_validation'],fixed_state_mechanics=paired,
        queries=dict(structural=dict(reference=t2,view='full',pointer='/nonlinear_response/directions'),
            control=dict(reference=t2,view='full',pointer='/nonlinear_response/control_prediction_validation')))
    destination=ROOT/'evidence/mujoco_native_task_sensitivity';destination.mkdir(exist_ok=True)
    completion=save(host,dict(kind='A4_engineering_completion',status='stopped',task_acceptance='unmeasured',
        results=[t2,mechanics,r1_mechanics,review],physics_steps=total['physics_steps'],
        reason='A4 bounded verification complete; no new Study or scan authorized by this driver.'),'engineering_completed')
    update(host,research_status='stopped',final_disposition=completion,closed_unix=time.time())
    summary['completion_reference']=completion;summary['research_status']='stopped'
    atomic_json(destination/'summary.json',compact_summary(summary))
    print('A4_COMPLETE',total,flush=True)


if __name__=='__main__':main()
