"""Saved-state, non-advancing physical localization and saved timing profile."""
import time
import numpy as np
import mujoco
from tools.platform_registry import Extension
from tools.state_io import read
from .diagnostic_evidence import DiagnosticEvidence, BoundReader
from .diagnostic_math import NonlinearModel
from .milestone5_preview import PreviewRequest
from .milestone5_serial_output import SerialOutput
from .gvs_projection import project, PROJECTOR_ID
from .gvs_basis import resolve_basis
from schemas.platform import SessionInput


def forward_terms(out,q,v,u):
    """Pure point evaluation of saved serial mechanics; never advance its clock."""
    m,d=out.model,out.data;c=out.compiled
    d.qpos[c['qpos_indices']]=q;d.qvel[c['qvel_indices']]=v
    d.ctrl[c['direct_tension_ids']]=u
    clock=float(d.time);mujoco.mj_forward(m,d)
    if d.time!=clock:raise ValueError('NONADVANCING_FORWARD_REQUIRED')
    if np.max(abs(-d.actuator_force[c['direct_tension_ids']]-u))>1e-10:
        raise ValueError('DIRECT_INPUT_BINDING')
    if d.ncon or np.linalg.norm(d.qfrc_constraint)>1e-10:
        raise ValueError('UNSUPPORTED_CONTACT_OR_CONSTRAINT')
    mass=np.zeros((m.nv,m.nv));mujoco.mj_fullM(m,d,mass)
    vi=c['qvel_indices'];mass=mass[np.ix_(vi,vi)]
    return dict(mass=mass,force=(d.qfrc_actuator+d.qfrc_passive-d.qfrc_bias)[vi].copy(),
        passive=d.qfrc_passive[vi].copy(),bias=d.qfrc_bias[vi].copy(),actuator=d.qfrc_actuator[vi].copy(),
        acceleration=d.qacc[vi].copy())


def execute(ctx,args):
    from examples import milestone5_predictor_campaign as stage
    from examples import milestone5_preparation as preparation
    from examples import milestone5_predictor_development as previous
    start=time.perf_counter();p=ctx.artifact(args.protocol);frozen=read(stage.RUN/'freeze.json')
    alignment=read(stage.ROOT/'runs/milestone5_recovery_20261005/align.json')['result']['cases']
    cases=[];model=None
    for item in frozen['distinct_local_intervals']:
        j=item['binding_indices'][0];index=round(item['interval_s'][0]/.01)
        binding=frozen['bindings'][j];r=BoundReader(ctx.store,binding);s=r.resolve(r.binding['execution_id'])
        cfg=s['configuration'];inp=SessionInput.model_validate(cfg)
        physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json')
        trajectory=r.read_file(s,'trajectory.json.gz');scene=r.read_file(s,'experiment_scene.json')
        saved=scene if index==0 else trajectory[index-1];a=alignment[j]['rows'][index]
        updates=r.read_file(s,'controller_observations.json');u=np.asarray(updates[index]['actual_tension_n'])
        z=np.asarray(a['observed_start_projected_state']);n=len(z)//2
        if abs(updates[index]['time_s']-item['interval_s'][0])>1e-10 or u.tolist()!=a['actual_input_n']:
            raise ValueError('STATE_INPUT_TIME_ALIGNMENT')
        out=SerialOutput(cfg,physics,compiled,ctx.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
        basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
        q=np.asarray(saved['qpos_rad']);v=np.asarray(saved['qvel_rad_s']);B=out.mapping
        projected=project(physics,basis,q,v)
        if np.max(abs(z-np.r_[projected['q_gvs'],projected['qdot_gvs']]))>1e-9:raise ValueError('PROJECTION_BINDING')
        if model is None:model=NonlinearModel(cfg,z,u,.01)
        continuous=model.functions.evaluate(z,u)
        # CasADi returns column vectors; prevent NumPy Nx1 minus N broadcasting.
        continuous={k:np.asarray(value) if k in ('mass_matrix','tendon_length_jacobian')
                    else np.asarray(value).ravel() for k,value in continuous.items()}
        actual=forward_terms(out,q,v,u);represented=forward_terms(out,B@z[:n],B@z[n:],u)
        mr=B.T@represented['mass']@B;fr=B.T@represented['force'];ar=np.linalg.solve(mr,fr)
        projected_a=np.asarray(project(physics,basis,np.zeros_like(q),actual['acceleration'])['qdot_gvs'])
        cm=continuous['mass_matrix'];cf=(continuous['tendon_generalized_force']+continuous['gravity_force']-
            continuous['velocity_bias']-continuous['elastic_force']-continuous['damping_force'])
        # Compare complete mechanics, not fitted parameter substitutions.
        terms={}
        pairs=dict(mass=(cm,mr),actuator=(continuous['tendon_generalized_force'],B.T@represented['actuator']),
            passive=(-continuous['elastic_force']-continuous['damping_force'],B.T@represented['passive']),
            gravity_minus_bias=(continuous['gravity_force']-continuous['velocity_bias'],-B.T@represented['bias']),force=(cf,fr))
        for name,(x,y) in pairs.items():
            terms[name]=dict(continuous=np.asarray(x).tolist(),serial_pullback=np.asarray(y).tolist(),
                relative_frobenius_difference=float(np.linalg.norm(np.asarray(x)-y)/max(np.linalg.norm(y),1e-20)))
        raw=out.raw(q,v);serial=out.motion(z)
        reconstructed=project(physics,basis,B@z[:n],B@z[n:])
        dt=1e-7
        zp=project(physics,basis,q+dt*v,v);zm=project(physics,basis,q-dt*v,v)
        rate_fd=(np.asarray(zp['q_gvs'])-zm['q_gvs'])/(2*dt)
        J=out.raw(B@z[:n],B@z[n:])['jacobian']
        cases.append(dict(case=item['case'],execution_id=s['execution_id'],interval_s=item['interval_s'],
            manifest=s['manifest'],saved_state_pointer='experiment_scene.json' if index==0 else 'trajectory.json.gz/'+str(index-1),
            state=z.tolist(),input_n=u.tolist(),input_information_time_s=item['interval_s'][0],
            projection_rate_fd_norm=float(np.linalg.norm(rate_fd-z[n:])),
            projection_roundtrip_norm=float(np.linalg.norm(np.r_[reconstructed['q_gvs'],reconstructed['qdot_gvs']]-z)),
            discarded_angle_norm_rad=float(np.linalg.norm(q-B@z[:n])),discarded_rate_norm_rad_s=float(np.linalg.norm(v-B@z[n:])),
            instantaneous_serial_position_error_m=float(np.linalg.norm(np.asarray(serial['position_m'])-raw['position_m'])),
            instantaneous_serial_vector_error_m_s=float(np.linalg.norm(np.asarray(serial['velocity_m_s'])-raw['velocity_m_s'])),
            continuous_acceleration=continuous['qdd'].tolist(),serial_pullback_acceleration=ar.tolist(),
            projected_full_acceleration=projected_a.tolist(),
            continuous_vs_projected_acceleration_norm=float(np.linalg.norm(continuous['qdd']-projected_a)),
            pullback_vs_projected_acceleration_norm=float(np.linalg.norm(ar-projected_a)),
            endpoint_J_acceleration_change_m_s2=float(np.linalg.norm(J@(continuous['qdd']-ar))),
            serial_full_mode_acceleration_residual=float(np.linalg.norm(actual['acceleration']-B@ar)),
            reduced_mass_min_eigenvalue=float(np.linalg.eigvalsh(mr).min()),
            terms=terms,backend_clock_unchanged=float(out.data.time)==0.))
    timings=[]
    for name in frozen['historical_complete_cases']:
        h=read(preparation.RUN/(name+'.json'))['result'];rows=h['rows']
        components={k:sum(row[k] for row in rows) for k in ('graph_construction_s','controller_s','propagation_s')}
        components['warm_preparation_inside_controller_s']=sum(row['warm_start']['preparation_s'] for row in rows)
        components['optimization_and_validation_inside_controller_s']=components['controller_s']-components['warm_preparation_inside_controller_s']
        components['serialization_loop_remainder_s']=h['complete_cost_s']-sum(components[k] for k in ('graph_construction_s','controller_s','propagation_s'))
        timings.append(dict(candidate=name,total_s=h['complete_cost_s'],components=components,
            calls=len(rows),receipt=read(preparation.RUN/(name+'_receipt.json')) if (preparation.RUN/(name+'_receipt.json')).exists() else None))
    return DiagnosticEvidence(detail=dict(cases=cases,cost_profile=timings,
        prior_serial_output_overhead_s=read(previous.RUN/'assessment.json')['economics']['new_output_map_s'],
        required_model_decision_cost='Must be measured on accepted final research call and included conservatively per pair; not assumed free',
        projector_identity=PROJECTOR_ID,dynamics_identity='model.gvs@1.0.0 / gvs_variable_strain_bending_v1',
        serial_mechanics='Exact saved compiled XML point evaluations with constant linear virtual-work pullback B.T M B and B.T f; no backend steps',
        backend_steps=0,integrations=0,controller_attempts=0,complete_cost_s=time.perf_counter()-start))


def preflight(inp,args,reg):return dict(cost=dict(wall_s=1200.))


DEFINITION=Extension('analysis.milestone5_campaign_localization','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_campaign_localization:execute',
    'Saved-state physical mechanics and timing localization without stepping.',
    sources=('extensions/tendon_family/milestone5_campaign_localization.py',
             'extensions/tendon_family/milestone5_serial_output.py','extensions/tendon_family/gvs_projection.py'),
    side_effects='artifact_store',capabilities=dict(preflight='extensions.tendon_family.milestone5_campaign_localization:preflight'))
