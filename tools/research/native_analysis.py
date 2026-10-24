"""Native-model request preparation and task interpretation in research_analysis.

Uses existing candidate admission, task constraints and evidence projections.
The family kernel owns all mechanics/integration; this module owns no Store.
"""
from copy import deepcopy
import time
import numpy as np
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.research.design import parameter_value, set_parameter

METHODS=('native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1')


def structure_context(base, candidates, request):
    """Existing verified source-relative candidates; exactly one continuous edit."""
    variable=request.variable
    if not (variable.startswith('segments.') and (variable.endswith('.young_pa') or '.sections.' in variable)):
        raise ValueError('NATIVE_V1_SUPPORTS_MODULUS_OR_SECTION_PARAMETER_ONLY')
    value=parameter_value(base['parameters'],variable);rows=[]
    for reference,c in candidates:
        other=parameter_value(c['parameters'],variable)
        expected=deepcopy(base['parameters']);set_parameter(expected,variable,other)
        if c['parameters']!=expected or other==value:raise ValueError('SINGLE_CHANGED_CONTINUOUS_PARAMETER_REQUIRED')
        a,b=base['configuration'],c['configuration']
        if (a['task']!=b['task'] or a['seed']!=b['seed'] or any(a['policy'][k]!=b['policy'][k]
                for k in ('controller','backend','dynamics_model','discretization'))):
            raise ValueError('NATIVE_STRUCTURE_REQUIRES_FIXED_TASK_CONTROL_AND_DISCRETIZATION')
        rows.append(dict(candidate=plain(reference),configuration=b,variable=variable,
            base_value=value,value=other,delta=other-value))
    return rows


def assessment(configuration, requirements):
    reasons=[]
    if configuration.policy.backend.extension_id!='backend.family_mujoco':reasons.append('MuJoCo backend required.')
    if configuration.task.environment.data.get('external_forces'):reasons.append('Native v1 has no scheduled external-force application.')
    supported={'gravity','elasticity','damping','inertia','tendon_actuation','large_deformation'}
    unknown=set(requirements.required_physics)-supported
    if unknown:reasons.append('Native v1 required physics unsupported: '+', '.join(sorted(unknown)))
    return dict(model_id='model.mujoco_native',model_version='1.0.0',representation_id='native_named_hinges_v1',
        relevant_assumptions=['MuJoCo compiled family model; no GVS projection; ideal absolute tensions.',
            'Contact-free, unconstrained hinges without activation dynamics; runtime checked.',
            'Short fixed-input numerical responses; no optimal-value or KKT interpretation.'],
        uses=dict(native_numerics=dict(status='REJECT' if reasons else 'ACCEPT',reasons=reasons)))


def applicability(requirements, query, assessed, point):
    reasons=[r for use in assessed['uses'].values() for r in use['reasons']]
    point=point or {};start=point.get('actual_time_s')
    horizon=0. if query.operation=='native_dynamics_v1' else query.native.horizon_s
    if query.operating_point!='saved_state' or not (point.get('integration_state') or point.get('native_replay')):
        reasons.append('Exact native integration checkpoint required; a GVS state cannot substitute.')
    p=query.protocol
    if abs(p.duration_s-requirements.duration_s)>p.horizon_alignment_atol_s or abs(p.period_s-requirements.physical_inputs['control_period_s'])>p.horizon_alignment_atol_s:
        reasons.append('Frozen task duration and input period must match protocol.')
    if start is None or start<0 or start+horizon>requirements.duration_s+p.horizon_alignment_atol_s:
        reasons.append('Native response must remain inside actual frozen task horizon.')
    coverage=[dict(constraint_id=c.constraint_id,expressible=c.kind!='unsupported',
        status='diagnostic',analyzed_indices=[],reason='Only matched short endpoint proxies; no full task or optimized structural capability.')
        for c in requirements.constraints]
    return dict(status='not_applicable' if reasons else 'applicable',reasons=reasons,
        constraint_coverage=coverage,full_task_supported=False,execution_support='not_assessed',
        model_assessment=assessed,horizon=dict(task_duration_s=requirements.duration_s,origin=start,
            remaining_task_s=None if start is None else requirements.duration_s-start,analysis_horizon_s=horizon,
            period_s=p.period_s,interpretation='Native instant or fixed-input short endpoint; no frozen full-task acceptance.'))


def task_proxy(requirements, terminal):
    """Reuse translated frozen constraints and the existing norm/interval margins."""
    from extensions.math_analysis.trajectory import _margins
    signals={'tip_position':terminal['tip_position_m'],'tip_velocity':terminal['tip_velocity_m_s']}
    rows=[]
    for c in requirements.constraints:
        if (c.signal.name not in signals or c.signal.entity!='tip' or c.signal.frame!='world'
                or c.signal.phase!='post_step' or c.kind not in ('norm_bound','component_interval')):continue
        for j,i in enumerate(c.indices):
            if abs(requirements.time_grid_s[i]-terminal['time_s'])>1e-12:continue
            residual=np.asarray(signals[c.signal.name])-c.reference[j]
            margins,value=_margins(c,residual)
            rows.append(dict(constraint_id=c.constraint_id,sample_index=i,time_s=terminal['time_s'],
                signal=c.signal.name,value=value,units=c.signal.units,margins=margins.tolist(),
                scope='short_endpoint_proxy',passed=bool(min(margins)>=0)))
    return rows


def calculate(configuration, binding, query, point, requirements, comparisons):
    from extensions.tendon_family.mujoco_analysis import calculate as kernel
    from tools.research.control_correction import constrained_response_step
    from tools.research.analysis import scoped_result
    started=time.perf_counter()
    raw,native,start=kernel(configuration,point,query.native,query.operation,comparisons)
    mechanics=raw['mechanics'];quantities=[]
    def quantity(name,value,unit,pointer):
        quantities.append(dict(name=name,value=float(value),unit=unit,source_pointer='/native_dynamics/'+pointer))
    quantity('native_mass_balance_residual',mechanics['mass_balance_residual_inf_nm'],'N*m','mechanics/mass_balance_residual_inf_nm')
    quantity('native_tip_speed',np.linalg.norm(mechanics['tip_velocity_m_s']),'m/s','mechanics/tip_speed_m_s')
    mechanics['tip_speed_m_s']=quantities[-1]['value']
    mechanism='Engine mass/bias/passive/actuator forces, named tip and tendon Jacobians; gravity bias is obtained with zero velocity.'
    unresolved=['No whole-task acceptance, reoptimized structural capability, regional bound or global infeasibility established.']
    if 'input_response' in raw:
        response=raw['input_response'];terminal=response['baseline'];response['task_proxy']=task_proxy(requirements,terminal)
        terminal['speed_m_s']=float(np.linalg.norm(terminal['tip_velocity_m_s']))
        quantity('baseline_short_endpoint_speed',terminal['speed_m_s'],'m/s','input_response/baseline/speed_m_s')
        for key in ('position','velocity'):
            quantity(key+'_step_relative_change',response['step_consistency_relative'][key],'1','input_response/step_consistency_relative/'+key)
        if query.native.correction_radius_n and response['step_consistency_passed']:
            # Existing bounded response optimizer; only an optional single local proposal.
            proxies=response['task_proxy'];norms={c.constraint_id:c for c in requirements.constraints if c.kind=='norm_bound'}
            selected=[r for r in proxies if r['constraint_id'] in norms]
            if selected:
                vectors=[];jac=[]
                for row in selected:
                    c=norms[row['constraint_id']];j=c.indices.index(row['sample_index'])
                    key='tip_position_m' if c.signal.name=='tip_position' else 'tip_velocity_m_s'
                    matrix=response['position_input_jacobian_m_n' if c.signal.name=='tip_position' else 'velocity_input_jacobian_m_s_n']
                    vectors.append((np.asarray(terminal[key])-c.reference[j])/c.radius);jac.append(np.asarray(matrix)/c.radius)
                u=np.asarray(terminal['actual_tensions_n']);n=len(u);radius=query.native.correction_radius_n
                solved=constrained_response_step(vectors,jac,np.zeros(n),u[None,:],np.eye(n),native.limits[:,1],radius,radius)
                response['correction']={**solved,'delta':solved['delta'].tolist()}
                if solved['success']:
                    actual=np.clip(u+solved['delta'],native.limits[:,0],native.limits[:,1])
                    candidate=native.rollout(start,actual,query.native.horizon_s)
                    candidate['speed_m_s']=float(np.linalg.norm(candidate['tip_velocity_m_s']))
                    response['correction'].update(actual_delta_n=(actual-u).tolist(),terminal=candidate,task_proxy=task_proxy(requirements,candidate),
                        scope='One nonlinear native short execution; no automatic control adoption or full-task acceptance.')
                    quantity('corrected_short_endpoint_speed',candidate['speed_m_s'],'m/s','input_response/correction/terminal/speed_m_s')
            else:response['correction']=dict(status='not_applicable',reason='No matched endpoint norm constraints.')
        mechanism='Six-channel local position/velocity response uses actual legal tensions, central or one-sided FD and two step sizes.'
        if not response['step_consistency_passed']:unresolved.append('Two-size input FD disagreement exceeds 5%; no correction proposed.')
    if 'structure_responses' in raw:
        base=raw['structure_baseline'];base['task_proxy']=task_proxy(requirements,base['terminal'])
        for i,row in enumerate(raw['structure_responses']):
            row['task_proxy']=task_proxy(requirements,row['terminal']);changes={}
            for key in ('mass_matrix_kg_m2','tip_acceleration_input_map_m_s2_n','passive_tip_acceleration_contribution_m_s2',
                    'tip_acceleration_m_s2','tendon_lengths_m','input_force_map_nm_n'):
                a=np.asarray(row['mechanics'][key]);b=np.asarray(base['mechanics'][key])
                changes[key]=dict(delta_norm=float(np.linalg.norm(a-b)),relative_change=float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-15)))
            for key in base['mechanics']['components']:
                a=np.asarray(row['mechanics']['components'][key]);b=np.asarray(base['mechanics']['components'][key])
                changes[key]=dict(delta_norm=float(np.linalg.norm(a-b)),relative_change=float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-15)))
            speed=float(np.linalg.norm(row['terminal']['tip_velocity_m_s']));base_speed=float(np.linalg.norm(base['terminal']['tip_velocity_m_s']))
            row.update(mechanism_changes=changes,endpoint_speed_change_m_s=speed-base_speed,
                endpoint_speed_secant_per_parameter=(speed-base_speed)/row['delta'],
                position_response_per_parameter=((np.asarray(row['terminal']['tip_position_m'])-base['terminal']['tip_position_m'])/row['delta']).tolist(),
                velocity_response_per_parameter=((np.asarray(row['terminal']['tip_velocity_m_s'])-base['terminal']['tip_velocity_m_s'])/row['delta']).tolist())
        # One comparison's core effects inline; every pairing and matrix stays in raw evidence.
        row=raw['structure_responses'][0];root='structure_responses/0/'
        for name,key in [('mass_relative_change','mass_matrix_kg_m2'),('drive_authority_relative_change','tip_acceleration_input_map_m_s2_n'),('passive_response_relative_change','passive_tip_acceleration_contribution_m_s2')]:
            quantity(name,row['mechanism_changes'][key]['relative_change'],'1',root+'mechanism_changes/'+key+'/relative_change')
        quantity('structure_endpoint_speed_change',row['endpoint_speed_change_m_s'],'m/s',root+'endpoint_speed_change_m_s')
        if len(raw['structure_responses'])==2:
            a,b=raw['structure_responses']
            raw['structure_secant_relative_change']={key:float(np.linalg.norm(np.asarray(a[key])-b[key])/max(np.linalg.norm(b[key]),1e-15))
                for key in ('position_response_per_parameter','velocity_response_per_parameter')}
        mechanism='Recompiled legal candidates at identical named qpos/qvel and fixed absolute tensions. Measured mass, stiffness, passive, geometry and drive changes are recorded separately.'
        unresolved.append('Matched coordinates do not imply matched equilibria or energy; secants concern fixed input, not optimal task capability.')
    raw['cost'].update(native.cost,kernel_wall_s=time.perf_counter()-started)
    assessed=assessment(SessionInput.model_validate(configuration),requirements)
    fit=applicability(requirements,query,assessed,point)
    summary=dict(question=query.operation,basis=dict(model='model.mujoco_native@1.0.0',
        state_time_s=point['actual_time_s'],horizon_s=fit['horizon']['analysis_horizon_s'],tensions_n=mechanics['actual_tensions_n'],
        channels=binding['tendon_order'],comparison=raw['state_comparison']),quantities=quantities,
        interpretation=mechanism,limitations=['Local floating-point native dynamics; no continuous affine model or conic/envelope claim.'],
        unresolved=unresolved,cost=raw['cost'],detail_pointer='/native_dynamics')
    # Reuse the admitted exact configuration identity (includes scene/numerics),
    # rather than hash a second native manifest or identify dynamics by mass alone.
    identity=binding['effective_configuration_identity']
    result=dict(status='computed',operation=query.operation,binding={**binding,'model_identity':identity},
        model_identity=identity,protocol=plain(query.protocol),operating_point={k:point[k] for k in
            ('actual_time_s','phase','input_units')},native_dynamics=raw,native_analysis=summary,
        task_acceptance='unmeasured',local_model_constraints=dict(status='diagnostic_only'),proxy_values={},
        internal_calculations=[dict(purpose=query.operation,**raw['cost'])],limitations=summary['limitations'])
    return scoped_result(result,requirements,fit,query)
