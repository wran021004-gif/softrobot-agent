"""Bounded retrospective history alignment and ordered substitutions only."""
from copy import deepcopy
import time
import numpy as np
from tools.platform_registry import Extension
from tools.state_io import digest
from .diagnostic_evidence import BoundReader,DiagnosticEvidence,measured_motion
from .diagnostic_math import NonlinearModel,charge_units
from .milestone5_preview import PreviewRequest
from .milestone5_preparation import fixed_input


def norm(a,b):return float(np.linalg.norm(np.asarray(a)-b))


def motion(model,state):
    p,v,*_=model.motion(state[:model.n],state[model.n:]);v=np.asarray(v).ravel()
    return dict(position_m=np.asarray(p).ravel().tolist(),velocity_m_s=v.tolist(),speed_m_s=float(np.linalg.norm(v)))


def vector_accounting(a,b,c,d,observed):
    result={}
    for key in ('position_m','velocity_m_s','speed_m_s'):
        values=[np.asarray(x[key]) for x in (a,b,c,d,observed)]
        terms=[values[0]-values[1],values[1]-values[2],values[2]-values[3],values[3]-values[4]]
        result[key]=dict(coarse_minus_fine=terms[0].tolist(),preview_start_minus_observed_start=terms[1].tolist(),
            preview_input_minus_observed_input=terms[2].tolist(),remaining_residual=terms[3].tolist(),
            total= (values[0]-values[4]).tolist(),term_norms=[float(np.linalg.norm(t)) for t in terms],
            identity_residual=float(np.max(abs(values[0]-values[4]-sum(terms)))))
    return result


def align(ctx,protocol):
    from schemas.platform import SessionInput
    from .gvs_basis import resolve_basis
    from .gvs_projection import project,discretize,discretization_jacobian
    import mujoco
    cases=[]
    for binding,history in zip(protocol['bindings'],protocol['histories']):
        r=BoundReader(ctx.store,binding);s=r.resolve(r.binding['execution_id']);cfg=s['configuration']
        updates=r.read_file(s,'controller_observations.json');trajectory=r.read_file(s,'trajectory.json.gz');actual=measured_motion(r,s)
        inp=SessionInput.model_validate(cfg);physics=r.read_file(s,'resolved_physics.json');compiled=r.read_file(s,'compiled_physics.json')
        basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
        mapping=discretization_jacobian(physics,basis)
        model=NonlinearModel(cfg,history['rows'][0]['initial_state'],history['rows'][0]['input_n'],.01)
        backend=mujoco.MjModel.from_xml_string(ctx.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'));data=mujoco.MjData(backend)
        def shape(z):
            q,v=discretize(physics,basis,z[:model.n],z[model.n:]);data.qpos[compiled['qpos_indices']]=q;data.qvel[compiled['qvel_indices']]=v
            mujoco.mj_forward(backend,data)
            return data.xpos[compiled['body_ids']].copy()
        rows=[]
        assert len(updates)==len(trajectory)==len(history['rows'])==35
        from .gvs_profile import execution_scope
        preview_cfg=protocol['history_configurations'][len(cases)]
        assert history['configuration_identity']==digest(preview_cfg),'SAVED_PREVIEW_CONFIGURATION_MISMATCH'
        assert execution_scope(preview_cfg)==execution_scope(cfg),'HISTORICAL_RECIPE_MISMATCH'
        initializer=cfg['task']['initializer']['parameters']['data']
        initial_q=[initializer.get('qpos_rad',{}).get(j,0.) for j in physics['dofs']]
        initial_v=[initializer.get('qvel_rad_s',{}).get(j,0.) for j in physics['dofs']]
        initial_projected=project(physics,basis,initial_q,initial_v)
        assert np.max(abs(np.asarray(initial_projected['q_gvs']+initial_projected['qdot_gvs'])-history['rows'][0]['initial_state']))<1e-10
        for i,(p,o,end,obs) in enumerate(zip(history['rows'],updates,trajectory,actual)):
            assert p['update_id']==i and abs(p['time_s']-o['time_s'])<1e-9 and abs(p['endpoint_s']-end['time_s'])<1e-9
            assert abs(end['solver_time_s']-o['time_s'])<1e-9 and o['phase']=='current_state_before_integration'
            assert np.max(abs(np.asarray(end['tension_n'])-o['actual_tension_n']))<1e-9
            previous=trajectory[i-1] if i else None
            q,v=(previous['qpos_rad'],previous['qvel_rad_s']) if previous else (initial_q,initial_v)
            z=project(physics,basis,q,v);z=z['q_gvs']+z['qdot_gvs']
            assert np.max(abs(np.asarray(z)-o['measured_initial_state']))<1e-8
            ze=project(physics,basis,end['qpos_rad'],end['qvel_rad_s']);ze=ze['q_gvs']+ze['qdot_gvs']
            projected=motion(model,ze);start_projected=motion(model,z)
            start_backend=actual[i-1] if i else dict(position_m=o['tip_position_m'],velocity_m_s=[0.,0.,0.],speed_m_s=0.)
            one=o['one_step_prediction'];assert abs(one['time_s']-p['endpoint_s'])<1e-9
            saved_shape=np.asarray(end['body_positions_m']);pred_shape=shape(p['state']);projected_shape=shape(ze)
            assert saved_shape.shape==pred_shape.shape,'COMPILED_BODY_INDEX_ALIGNMENT'
            data.qpos[compiled['qpos_indices']]=end['qpos_rad'];data.qvel[compiled['qvel_indices']]=end['qvel_rad_s'];mujoco.mj_forward(backend,data)
            assert norm(data.xpos[compiled['body_ids']],saved_shape)<1e-9,'SAVED_BODY_POSITION_ALIGNMENT'
            diff=np.asarray(p['initial_state'])-z
            rows.append(dict(update_id=i,start_s=p['time_s'],end_s=p['endpoint_s'],observation_s=o['time_s'],command_application_s=o['time_s'],
                preview_start_state=p['initial_state'],preview_end_state=p['state'],observed_start_projected_state=z,observed_end_projected_state=ze,
                preview_endpoint={k:p[k] for k in ('position_m','velocity_m_s','speed_m_s')},observed_endpoint=obs,projected_observed_endpoint=projected,
                projected_observed_start=start_projected,observed_start=start_backend,
                preview_input_n=p['input_n'],actual_requested_n=o['requested_tension_n'],actual_input_n=o['actual_tension_n'],
                actual_previous_input_n=updates[i-1]['actual_tension_n'] if i else p['previous_input_n'],preview_previous_input_n=p['previous_input_n'],
                command_gap_max_n=float(np.max(abs(np.asarray(p['input_n'])-o['actual_tension_n']))),
                start_cell_angle_rms_rad=float(np.sqrt(np.mean((mapping@diff[:model.n])**2))),
                start_cell_rate_rms_rad_s=float(np.sqrt(np.mean((mapping@diff[model.n:])**2))),
                projection_position_error_m=norm(projected['position_m'],obs['position_m']),projection_vector_error_m_s=norm(projected['velocity_m_s'],obs['velocity_m_s']),
                preview_position_error_m=norm(p['position_m'],obs['position_m']),preview_vector_error_m_s=norm(p['velocity_m_s'],obs['velocity_m_s']),preview_speed_error_m_s=p['speed_m_s']-obs['speed_m_s'],
                actual_one_step=one,one_step_position_error_m=norm(one['tip_position_m'],obs['position_m']),one_step_vector_error_m_s=norm(one['tip_velocity_m_s'],obs['velocity_m_s']),
                shape=dict(method='Same serial-cell kinematics after GVS discretization, compared to saved body origins; separate from continuous-model tip.',
                    preview_positions_m=pred_shape.tolist(),observed_positions_m=saved_shape.tolist(),projected_observed_positions_m=projected_shape.tolist(),
                    preview_max_error_m=float(np.max(np.linalg.norm(pred_shape-saved_shape,axis=1))),projection_max_error_m=float(np.max(np.linalg.norm(projected_shape-saved_shape,axis=1)))),
                holding=p['endpoint_s']>=.3-1e-9,
                preview_selection={k:p[k] for k in ('selected_iteration','stop_reason','raw_stop','accepted','effective_horizon','initialization','plan_identity')},
                actual_selection={k:o[k] for k in ('optimization_selected_iteration','policy_stop_reason','optimization_raw_status','plan_accepted','effective_horizon','unusable_updates','stop_requested')},
                sources=dict(manifest=s['manifest'],trajectory=s['files']['trajectory.json.gz'],trajectory_pointer='/'+str(i),row_start_pointer=None if i==0 else '/'+str(i-1),
                    observations=s['files']['controller_observations.json'],observation_pointer='/'+str(i),preview=protocol['history_sources'][len(cases)],preview_pointer='/result/rows/'+str(i))))
        def first(field,threshold):return next((dict(start_s=x['start_s'],end_s=x['end_s'],value=x[field]) for x in rows if abs(x[field])>threshold),None)
        # Descriptive onset scales, not acceptance or ranking gates.
        summary=dict(execution_id=s['execution_id'],candidate_id=r.binding['candidate_id'],
            first_nonzero_command_gap=first('command_gap_max_n',1e-9),first_material_command_gap=first('command_gap_max_n',.1),
            first_position_over_1mm=first('preview_position_error_m',.001),first_vector_over_1e4=first('preview_vector_error_m_s',1e-4),
            first_vector_over_1cm_s=first('preview_vector_error_m_s',.01),
            timeline=[{k:x[k] for k in ('start_s','end_s','command_gap_max_n','preview_position_error_m','preview_vector_error_m_s','preview_speed_error_m_s','projection_vector_error_m_s')} for x in rows],
            iteration_zero_preview=sum(x['preview_selection']['selected_iteration']==0 for x in rows),
            iteration_zero_actual=sum(x['actual_selection']['optimization_selected_iteration']==0 for x in rows),
            max_shape_error_m=max(x['shape']['preview_max_error_m'] for x in rows),max_tip_error_m=max(x['preview_position_error_m'] for x in rows))
        cases.append(dict(binding=binding,configuration=cfg,summary=summary,rows=rows))
    return dict(cases=cases,backend_advances=0,alignment='Observation i at row start; trajectory i at row end. trajectory i stores command from observation i, not a new endpoint command.',
        coordinate_scales='Map curvature difference to represented cell angles in rad and rate difference to cell rates in rad/s; report separately.',
        shape_scope='All saved body origins. Distributed comparison uses represented serial kinematics, not a claimed continuous-model shape identity.')


def compare(ctx,protocol):
    alignment=ctx.artifact(protocol['alignment'])['detail']['result'];cases=[]
    for case,index in zip(alignment['cases'],protocol['selected_updates']):
        row=case['rows'][index];cfg=case['configuration'];outputs={};costs=[]
        for label,state,input_n in [('A',row['preview_start_state'],row['preview_input_n']),('B',row['preview_start_state'],row['preview_input_n']),
                ('C',row['observed_start_projected_state'],row['preview_input_n']),('D',row['observed_start_projected_state'],row['actual_input_n'])]:
            if label=='D':
                saved=next(x for x in protocol['saved_intervals'] if x['execution_id']==case['summary']['execution_id'])
                reference=next(x for x in protocol['saved_reference']['result']['rows'] if x['execution_id']==saved['execution_id'])
                assert saved['state']==state and saved['input_n']==input_n and abs(saved['interval_s'][0]-row['start_s'])<1e-9
                assert abs(saved['duration_s']-.01)<1e-12 and ctx.artifact(saved['configuration'])['effective']==cfg,'SAVED_REFERENCE_BINDING'
                outputs[label]=dict(results=reference['results'],endpoint=reference['results'][-1],resolution=reference['differences'][-1],
                    reference_supported=reference['numerical_reference_established'],reused=True,source=protocol['reference_source'],new_charge=0)
                continue
            results=[]
            for step in ((.01,) if label=='A' else (.0005,.00025,.000125)):
                completed=[x for x in protocol.get('completed_substitutions',[]) if x['execution_id']==case['summary']['execution_id'] and x['update_id']==index and x['label']==label and x['endpoint']['step_s']==step]
                if completed:
                    assert len(completed)==1,'DUPLICATE_COMPLETED_SUBSTITUTION'
                    results.append(deepcopy(completed[0]['endpoint']));continue
                charge_units(ctx,'prediction_evaluations',1);start=time.perf_counter()
                model=NonlinearModel(cfg,state,input_n,step)
                end=fixed_input(model,state,input_n,.01,time.perf_counter()+90.)
                end.update(step_s=step,complete_cost_s=time.perf_counter()-start);costs.append(end['complete_cost_s']);results.append(end)
                ctx.save_artifact(dict(execution_id=case['summary']['execution_id'],update_id=index,label=label,endpoint=end),'substitution_completed')
                if label=='A':
                    if norm(end['velocity_m_s'],row['preview_endpoint']['velocity_m_s'])>1e-8 or norm(end['state'],row['preview_end_state'])>1e-7:
                        raise ValueError('COARSE_REPRODUCTION_MISMATCH_STOP_BEFORE_REFINEMENT')
            outputs[label]=dict(results=results,endpoint=results[-1])
            if label!='A':
                differences=[dict(position_m=norm(a['position_m'],b['position_m']),velocity_m_s=norm(a['velocity_m_s'],b['velocity_m_s']),speed_m_s=abs(a['speed_m_s']-b['speed_m_s'])) for a,b in zip(results,results[1:])]
                outputs[label]['resolution']=differences[-1];outputs[label]['differences']=differences
                outputs[label]['reference_supported']=all(x['velocity_m_s']<=1e-4 and x['speed_m_s']<=1e-4 for x in differences)
        cases.append(dict(execution_id=case['summary']['execution_id'],candidate_id=case['summary']['candidate_id'],update_id=index,interval_s=[row['start_s'],row['end_s']],
            fixed=['historical model/recipe','original task clock and target','same .01 s duration','held ideal direct tension; pre-step command'],outputs=outputs,
            observed=row['observed_endpoint'],coarse_reproduction=dict(state_max=float(np.max(abs(np.asarray(outputs['A']['endpoint']['state'])-row['preview_end_state']))),
                velocity_m_s=norm(outputs['A']['endpoint']['velocity_m_s'],row['preview_endpoint']['velocity_m_s'])),
            ordered_accounting=vector_accounting(*(outputs[k]['endpoint'] for k in 'ABCD'),row['observed_endpoint']),
            complete_cost_s=sum(costs)))
    return dict(cases=cases,standalone_attempts=14,local_controller_attempts=0,
        caution='Ordered substitutions; coupled state/input histories, cancellation and order dependence prohibit unique causal percentage attribution. Residual includes projection/model/input representation and unresolved numerical effects.',
        prototype='Fine simulated-plant propagation at a fixed saved command only; controller optimization transcription remains unchanged. No complete preview.')


def execute(ctx,args):
    p=ctx.artifact(args.protocol);start=time.perf_counter()
    result=align(ctx,p) if p['operation']=='align' else compare(ctx,p)
    return DiagnosticEvidence(detail=dict(result=result,complete_cost_s=time.perf_counter()-start))


def preflight(inp,args,reg):return dict(cost=dict(wall_s=600.))


DEFINITION=Extension('analysis.milestone5_recovery','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_recovery:execute','Align saved histories and perform bounded ordered fixed-input substitutions.',
    sources=('extensions/tendon_family/milestone5_recovery.py',),side_effects='artifact_store',
    capabilities=dict(preflight='extensions.tendon_family.milestone5_recovery:preflight'))
