"""Charged, bounded accuracy and cost assessments; no prospective/backend entry."""
from copy import deepcopy
import time
import numpy as np
from tools.platform_registry import Extension
from tools.state_io import read,digest
from .diagnostic_evidence import DiagnosticEvidence,BoundReader
from .diagnostic_math import charge_units
from .milestone5_preview import PreviewRequest
from .milestone5_first_interval import differences,stable
from .milestone5_validation import speed_change_direction
from .milestone5_campaign_predictor import SerialMechanics,GRIDS,VERSION,probe,history


def bound(ctx,binding):
    r=BoundReader(ctx.store,binding);s=r.resolve(r.binding['execution_id'])
    m=SerialMechanics(s['configuration'],r.read_file(s,'resolved_physics.json'),r.read_file(s,'compiled_physics.json'),
        ctx.store.artifact(s['files']['robot.xml'],raw=True).decode('utf8'))
    return r,s,m


def score(end,initial,actual,start,t,stable_flag,uncertainty):
    dp=end['speed_m_s']-initial['speed_m_s'];da=actual['speed_m_s']-start['speed_m_s']
    pred=speed_change_direction(dp);truth=speed_change_direction(da)
    resolved=stable_flag and min(abs(dp-1e-4),abs(dp+1e-4))>uncertainty
    ep=float(np.linalg.norm(np.asarray(end['position_m'])-actual['position_m']))
    ev=float(np.linalg.norm(np.asarray(end['velocity_m_s'])-actual['velocity_m_s']))
    es=abs(end['speed_m_s']-actual['speed_m_s'])
    return dict(position_error_m=ep,vector_error_m_s=ev,speed_error_m_s=es,
        position_pass=ep<=1e-6,vector_pass=ev<=1e-4,speed_pass=es<=1e-4,
        predicted_speed_change_m_s=dp,observed_speed_change_m_s=da,
        predicted_direction=pred if resolved else 'indeterminate',observed_direction=truth,
        direction_resolved=resolved,direction_correct=resolved and pred==truth,
        speed_false_safe=end['speed_m_s']<=.02 and actual['speed_m_s']>.02,
        holding_false_safe=t>=.3-1e-10 and end['speed_m_s']<=.02 and actual['speed_m_s']>.02)


def accuracy(ctx,p):
    from examples import milestone5_predictor_campaign as stage
    from examples import milestone5_predictor_development as previous
    frozen=read(stage.RUN/'freeze.json');localization=read(stage.RUN/'localization-r1.json')
    align=read(stage.ROOT/'runs/milestone5_recovery_20261005/align.json')['result']['cases']
    cases=[];start=time.perf_counter()
    for item,localized in zip(frozen['distinct_local_intervals'],localization['cases']):
        j=item['binding_indices'][0];idx=round(item['interval_s'][0]/.01)
        r,s,model=bound(ctx,frozen['bindings'][j]);row=align[j]['rows'][idx]
        initial=model.motion(localized['state']);results=[];failure=None
        for grid in GRIDS:
            charge_units(ctx,'prediction_evaluations',1)
            try:
                result=model.propagate(localized['state'],localized['input_n'],grid=grid,deadline=start+1100.)
            except Exception as exc:
                failure=dict(type=type(exc).__name__,message=str(exc),grid=grid)
                ctx.save_artifact(dict(case=item['case'],failure=failure),'local_integration_failed');break
            ctx.save_artifact(dict(case=item['case'],result=result),'local_integration_completed');results.append(result)
        d=differences([dict(**x,step_s=x['grid']['max_step_s']) for x in results])
        valid=len(d)==2 and all(x['velocity_m_s']<=1e-4 and x['speed_m_s']<=1e-4 for x in d)
        end=results[-1] if results else None
        previous_case=read(previous.RUN/'assessment.json')['cases'][j]['locals'][{0:0,1:1,30:2}[idx]]
        uncertainty=None if not d else d[-1]
        cases.append(dict(case=item['case'],interval_s=item['interval_s'],results=results,failure=failure,
            numerical_differences=d,numerical_pass=valid,
            prediction=None if end is None else dict(version=VERSION,initial=initial,position_m=end['position_m'],
                velocity_m_s=end['velocity_m_s'],speed_m_s=end['speed_m_s'],input_n=localized['input_n'],
                input_information_time_s=item['interval_s'][0],frame='world',interval_s=item['interval_s'],
                numerical_uncertainty=uncertainty,model_error_bound=None,supported_scope='Exact declared historical local interval only; no safety authority'),
            score=None if end is None else score(end,initial,row['observed_endpoint'],row['observed_start'],item['interval_s'][0],valid,
                d[-1]['speed_m_s'] if d else float('inf')),
            previous_working_score=previous_case['working_score'],
            initial_projection_position_error_m=localized['instantaneous_serial_position_error_m'],
            initial_projection_vector_error_m_s=localized['instantaneous_serial_vector_error_m_s']))
    # Re-output ALL existing reference endpoints in a common map, never reintegrate.
    reference=read(stage.RUN/'reference.json');_,_,output=bound(ctx,frozen['bindings'][0])
    serial=[dict(**output.motion(x['state']),step_s=x['step_s']) for x in reference['results']]
    serial_d=differences(serial)
    return dict(cases=cases,reference_assessments=dict(continuous=dict(passed=reference['numerical_stability_supported'],
        final_differences=reference['continuous_differences'][-2:]),
        represented_serial=dict(passed=stable(serial),final_differences=serial_d[-2:],outputs=serial),
        scope='Original continuum dynamics only. Neither output mapping reference validates changed serial mechanics or complete histories.'),
        numerical_supported_count=sum(c['numerical_pass'] for c in cases),distinct_intervals=len(cases),
        new_integrations=sum(len(c['results'])+int(c['failure'] is not None) for c in cases),
        complete_cost_s=time.perf_counter()-start,backend_steps=0)


def execute(ctx,args):
    from examples import milestone5_predictor_campaign as stage
    from examples import milestone5_preparation as preparation
    p=ctx.artifact(args.protocol);frozen=read(stage.RUN/'freeze.json');start=time.perf_counter()
    if p['operation']=='accuracy':result=accuracy(ctx,p)
    elif p['operation']=='cost_probe':
        registration=read(preparation.RUN/'registration.json')
        cfg=deepcopy(registration['development_configuration'])
        cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=.075
        result=probe(cfg,registration['development_initial_state'],lambda:charge_units(ctx,'local_solves',1))
        # Outcomes become accessible only after the independent response was generated.
        r=BoundReader(ctx.store,frozen['bindings'][0]);s=r.resolve(r.binding['execution_id'])
        updates=r.read_file(s,'controller_observations.json')
        comparisons=[]
        for i,u in enumerate(result['first_five_inputs']):
            actual=updates[i]['actual_tension_n']
            comparisons.append(dict(time_s=i*.01,predicted_input_n=u,observed_input_n=actual,
                error_norm_n=float(np.linalg.norm(np.asarray(u)-actual)),
                max_abs_error_n=float(np.max(abs(np.asarray(u)-actual)))))
        result['saved_production_comparison']=comparisons
        result['scope']='First original .00-.05 interval only, first command exact input-state alignment checked; no whole-task controller-response fidelity claim'
    elif p['operation']=='history':
        j=p['candidate_index'];r,s,model=bound(ctx,frozen['bindings'][j])
        registration=read(preparation.RUN/'registration.json');cfg=deepcopy(registration['development_configuration'])
        cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=(.075,.15)[j]
        charge_units(ctx,'preview_attempts',1)
        result=history(cfg,registration['development_initial_state'],model,lambda:charge_units(ctx,'local_solves',1),
            deadline=start+1100.,save_update=lambda row:ctx.save_artifact(row,'combined_preview_update_completed'))
        result.update(candidate_id=('history075','history15')[j],serial_setup_s=model.setup_s,
            classification='Retrospective development, independent own-history forecast; no future backend state/input read by predictor',
            source_manifest=s['manifest'])
    else:raise ValueError('UNKNOWN_CAMPAIGN_OPERATION')
    result['outer_complete_cost_s']=time.perf_counter()-start
    return DiagnosticEvidence(detail=result)


def preflight(inp,args,reg):return dict(cost=dict(wall_s=1200.))


DEFINITION=Extension('analysis.milestone5_campaign_assessment','tool','1.0.0',PreviewRequest,DiagnosticEvidence,
    'extensions.tendon_family.milestone5_campaign_assessment:execute',
    'Bounded corrected local integrations, isolated cost probe, or final combined historical preview.',
    sources=('extensions/tendon_family/milestone5_campaign_assessment.py','extensions/tendon_family/milestone5_campaign_predictor.py',
             'extensions/tendon_family/milestone5_campaign_localization.py','extensions/tendon_family/milestone5_serial_output.py'),
    side_effects='artifact_store',capabilities=dict(preflight='extensions.tendon_family.milestone5_campaign_assessment:preflight'))
