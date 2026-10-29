"""B4 one-shot preparation only. No Provider, authorization or Worker dispatch."""
from copy import deepcopy
from types import SimpleNamespace
import json
from tools.research import core
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.design import generate_candidate,verify_candidate,parameter_value
from tools.research.native_analysis import structure_context,assessment,applicability
from tools.research.numerics import native_point
from tools.research.optimal_capability import family_parameters
from tools.research.state import state,save
from tools.research.task_constraints import describe_analysis_requirements
from schemas.platform import SessionInput
from tools.state_io import atomic_json,read


SPECS={'M':'study_p63b4_m_sol_prepared.json','M0':'study_p63b4_m0_mechanism_prepared.json'}


def prepare_study(kind, spec_path=None):
    h=core.prepare(spec_path or ROOT/'configs/research'/SPECS[kind])
    path=h.store.root/'b4_preparation.json'
    if path.exists():return h,read(path)
    s=state(h);spec=s['spec']
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=4)
    baseline=generate_candidate(h,request,dict(decision_owner='Operator',origin='operator_provided_unmeasured_baseline',
        scope='B4 preparation only; legal compilation, no task evaluation or mathematical result.'))['candidate']
    base=verify_candidate(h,baseline)
    result=dict(study_id=h.run_id,store=str(h.store.root),resolved_identity=spec['resolved_identity'],
        configuration=SPECS[kind],baseline=baseline,baseline_generation_request=request,
        authorization='pending separate explicit Study approval; no authorization event created',budgets=spec['budgets'],
        task_identity=spec['canonical_task_identity'],family_space_identity=spec['family_space_identity'],
        native_control_limits=spec['native_control_limits'],task_acceptance='unmeasured',
        success_cases=[dict(entry_id=e['entry_id'],revision=e['revision']) for e in spec['knowledge_manifest']['entries'] if e['kind']=='success_case'])
    if kind=='M0':
        variable='segments.0.length_m';parameters,domain=family_parameters(spec,base,variable)
        p0=parameter_value(parameters,variable);step=.001;comparisons=[]
        for sign in (-1,1):
            choice=deepcopy(request);choice['segments']={'0':dict(length_m=p0+sign*step)}
            comparison=generate_candidate(h,choice,dict(decision_owner='Operator',origin='operator_mechanism_stencil',
                variable=variable,unit='m',delta=sign*step,baseline=baseline))['candidate']
            verify_candidate(h,comparison);comparisons.append(comparison)
        cfg=base['configuration']
        point=native_point(h,SimpleNamespace(candidate=baseline,saved_state=None,
            operating_point='standardized_initial_pretension'),cfg)
        query=dict(candidate=baseline,operation='fixed_input_structure_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
            native=dict(tensions_n=point['u'],horizon_s=.01),
            structure_response=dict(variable=variable,candidates=comparisons))
        q=AnalysisRequest.model_validate(query)
        rows=structure_context(base,[(r,verify_candidate(h,r)) for r in comparisons],q.structure_response,spec=spec)
        requirements=describe_analysis_requirements(cfg,{})
        fit=applicability(requirements,q,assessment(SessionInput.model_validate(cfg),requirements),point)
        if fit['status']=='not_applicable':raise ValueError(fit['reasons'])
        alignment=[]
        for ref in [baseline,*comparisons]:
            c=verify_candidate(h,ref)
            other=native_point(h,SimpleNamespace(candidate=ref,saved_state=None,
                operating_point='standardized_initial_pretension'),c['configuration'])
            if any(other[k]!=point[k] for k in ('qpos_rad','qvel_rad_s','dof_order','tendon_order','phase','actual_time_s','input_units','u')):
                raise ValueError('M0_INITIAL_COORDINATES_OR_CHANNELS_NOT_COMPARABLE')
            robot=c['configuration']['robot']['structure']['data']
            limits=[next(t['force_limit_n'] for t in robot['tendons'] if t['id']==name) for name in point['tendon_order']]
            if not all(0<=u<=hi for u,hi in zip(point['u'],limits)):raise ValueError('M0_FIXED_TENSIONS_OUTSIDE_BOUND')
            alignment.append(dict(candidate=ref,physical_validation=c['physical_validation'],
                dimensions=c['resolved_parameters']['dimensions'],force_limits_n=limits,
                initializer=c['configuration']['task']['initializer']))
        units={'mass_matrix_kg_m2':'kg*m^2/m','tip_jacobian_m_rad':'(m/rad)/m',
            'tendon_jacobian_m_rad':'(m/rad)/m','tip_acceleration_input_map_m_s2_n':'(m/(s^2*N))/m',
            'passive_tip_acceleration_contribution_m_s2':'(m/s^2)/m'}
        result.update(variable=variable,unit='m',domain=domain,base_value=p0,minus_value=rows[0]['value'],
            plus_value=rows[1]['value'],h=step,actual_deltas=[r['delta'] for r in rows],
            comparisons=comparisons,initial_state=point,alignment=alignment,request=query,applicability=fit,
            expected_mathematical_evaluations=1+len(comparisons),
            expected_native_work=dict(model_builds=3,rollouts=3,horizon_s=.01,
                scope='Prediction only; actual native_dynamics.cost owns builds, forward/mechanics evaluations, rollouts, physics_steps and wall time.'),
            result_fields=[dict(field=field,central_unit=unit,
                baseline_pointer='/native_dynamics/structure_baseline/mechanics/'+field,
                side_pointers=['/native_dynamics/structure_responses/'+str(i)+'/mechanics/'+field for i in (0,1)],
                secant_pointers=['/native_dynamics/structure_responses/'+str(i)+'/mechanism_changes/'+field+'/finite_difference_per_parameter' for i in (0,1)])
                for field,unit in units.items()],
            postprocessing=dict(central='(F_plus - F_minus)/(p_plus - p_minus)',
                reuse_secants='(delta_plus * s_plus - delta_minus * s_minus)/(delta_plus - delta_minus); symmetric stencil equals (s_plus+s_minus)/2',
                scope='One h central secant, not convergence-verified derivative. Store original arrays, side secants, units, coordinates and source pointers. Passive means J M^-1 qfrc_passive; gravity bias is separate. No causal/task-acceptance inference.'))
        atomic_json(h.store.root/'m0_analysis_request.json',query)
    result['preparation_reference']=save(h,result,'operator_b4_preparation')
    atomic_json(path,result)
    return h,result


if __name__=='__main__':
    print(json.dumps({kind:prepare_study(kind)[1] for kind in SPECS},ensure_ascii=False,indent=2))
