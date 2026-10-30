"""B's bounded forward link: saved M0 -> original generation/T1 -> saved M1/M2.

Commit first. Nine rollout callbacks / 9000 steps maximum. No new M0, Provider,
physical replay or autonomous Study. Original receipts survive resume/failure.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from tools.platform_store import plain
from tools.state_io import atomic_json,read,digest
from tools.research import core,analysis,reporter
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.research.contracts import PLAN_RESEARCH_INTENTS
from tools.research.design import set_parameter,verify_candidate
from tools.research.scientific_intent import compile_question
from tools.research.nonlinear_capability import T1,T2_OPERATION
from tools.research.research_context import agent_decision_brief
from extensions.tendon_family.family_space import resolved_request

DEST=ROOT/'runs/structure_control_b'
EVIDENCE=ROOT/'evidence/structure_control_b'
PATH='segments.1.sections.0.parameters.width_y_m'


def plan(h,action,key,*,candidate=None,evidence=None,**fields):
    value=dict(action=action,hypothesis='A+ narrower section increases directional authority; its fixed-control and reoptimized task effects may compete.',
        expected_observation='Source-bound physical responses and finite-budget differences; task improvement is not implied by M0.',
        weakening_observation='Opposite effects, active changes, flat response, insufficient control search or numerical failure.',
        fixed_conditions='Original reach_free task, other structure, legal absolute initial controls and matched finite T1 settings.',
        stopping_condition='Three capped T1 calculations and one saved aggregation; no budget enlargement.',
        interpretation='Scripted Main tool choice in an authorized engineering check; no autonomous model or task acceptance.',
        supporting_evidence=evidence or [],decision=dict(hypothesis_id='b-'+key,research_intent=PLAN_RESEARCH_INTENTS[action],selected_candidate=candidate),**fields)
    return core.dispatch(h,value,'b-'+key,origin='engineering_preflight')


def export_results(h,info,refs,t2ref):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    m0ref=state(h)['research_mathematics'][0];m0=h.store.artifact(m0ref)
    facts=[]
    for name,ref in zip(('baseline','suggested','opposite'),refs):
        raw=h.store.artifact(ref);atomic_json(EVIDENCE/('t1-'+name+'.json'),raw)
        t=raw.get('nonlinear_capability',{});cfg=verify_candidate(h,raw['candidate'])['configuration']
        facts.append(dict(name=name,candidate=raw['candidate'],reference=ref,status=raw['status'],
            width_m=resolved_request(state(h)['spec']['family_space'],h.store.artifact(raw['candidate'])['parameters'])['segments']['1']['sections'][0]['parameters']['width_y_m'],
            initial_J=t.get('initial_J'),best_found_J=t.get('J'),initial_metrics=t.get('initial_metrics'),best_metrics=t.get('best_metrics'),
            input_saturation=t.get('input_saturation'),stop_reason=t.get('stop_reason'),settings=t.get('settings'),
            cost=raw.get('native_dynamics',{}).get('cost') or raw.get('native_diagnostic',{}).get('cost'),
            charged_numerical_s=raw.get('charged_numerical_s')))
    result=h.store.artifact(t2ref) if t2ref else None
    if result:atomic_json(EVIDENCE/'t2.json',result)
    report=reporter.investigate(h,dict(question='How does the historical M0 section direction relate to measured fixed-control M1 and matched finite-budget M2, and what remains unresolved?',
        references=[m0ref,*([t2ref] if t2ref else refs)]))
    report_ref=report['report_reference'];core.read_evidence(h,dict(reference=report_ref,view='full'),record_read=True)
    atomic_json(EVIDENCE/'reporter.json',h.store.artifact(report_ref))
    current=agent_decision_brief(h)
    validation=dict(scope='Actual bounded Native forward research; scripted operator Main Plans, no Provider.',
        study_id=h.run_id,freeze=state(h)['freeze'],historical_M0=dict(reference=m0ref,candidate=m0['candidate'],
            direction=m0['structure_research']['structure_direction'],status='reused_original_evidence_no_recomputation'),
        preparation=info,results=facts,T2=t2ref,reporter=report,interpretation_status='deferred_no_Provider',
        mathematical_evaluations=state(h)['mathematical_evaluations'],numerical_s=state(h)['numerical_s'],
        cost_totals={key:sum((r['cost'] or {}).get(key,0) for r in facts) for key in ('model_builds','rollouts','physics_steps','forward_evaluations')},
        task_acceptance='unmeasured',independent_replays=0,provider_requests=h.store.remaining()['used']['model_calls'],
        m2_direction_status=result.get('nonlinear_response',{}).get('direction_status') if result else 'not_computed',l0=current)
    atomic_json(EVIDENCE/'validation.json',validation)
    assert validation['cost_totals']['model_builds']<=3
    assert validation['cost_totals']['rollouts']<=9 and validation['cost_totals']['physics_steps']<=9000
    assert validation['mathematical_evaluations']<=4 and validation['provider_requests']==0
    # A Main decision can stop on limited evidence; neither Reporter nor M0 submits a candidate automatically.
    if state(h)['research_status']!='stopped':
        stop=plan(h,'stop','stop-after-facts',evidence=[m0ref,*refs,*([t2ref] if t2ref else [])])
        atomic_json(EVIDENCE/'main-stop.json',stop)
    core.export(h)
    print(json.dumps(dict(status='completed_with_recorded_limits',cost=validation['cost_totals'],m2=validation['m2_direction_status'],numerical_s=validation['numerical_s'])),flush=True)


def main():
    h=core.prepare(ROOT/'configs/research/study_structure_control_b_check.json',DEST/'store');h.actor='operator-b-scripted-main'
    if state(h)['research_status']=='stopped':
        print('Original stopped receipts retained; no new computation.');return
    for k,v in state(h)['spec']['runtime']['threads'].items():os.environ[k]=v
    if 'freeze' not in state(h):core.bind(h)
    core.guard(h)
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=['registered mathematics'],
        maximum_T1_models=3,maximum_rollout_callbacks=9,maximum_physics_steps=9000,maximum_math_evaluations=4,
        provider_requests=0,independent_task_evaluations=0,M0='historical archive only')
    if not any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)):
        save(h,dict(user_approval='User Softrobot-Agent B explicitly authorizes necessary budget-constrained minimal real research; not an autonomous Study.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    m0ref=state(h)['research_mathematics'][0];source=h.store.artifact(m0ref);direction=source['structure_research']['structure_direction']
    old=h.store.artifact(source['candidate']);prep=DEST/'preparation.json'
    if prep.exists():info=read(prep)
    else:
        original=deepcopy(old['parameters']);canonical=resolved_request(state(h)['spec']['family_space'],original)
        change=direction['parameter_changes'][0];assert change['parameter_path']==PATH
        hstep=abs(change['delta']);assert hstep>0
        opposite=deepcopy(canonical);set_parameter(opposite,PATH,change['baseline']+hstep)
        requests=[original,direction['generation_handoff']['generation'],opposite];candidates=[];adoption=[]
        for name,request in zip(('baseline','suggested','opposite'),requests):
            result=plan(h,'generate','generate-'+name,evidence=[m0ref],generation=request)
            candidate=result['result']['candidate'];candidates.append(candidate)
            view=agent_decision_brief(h)['mechanism_research'];adoption.append(dict(name=name,view=view))
        assert [r['view']['suggestion_adopted'] for r in adoption]==[False,True,False]
        # Historical M0 baseline is the same actual structure/task, with its original provenance preserved.
        base=verify_candidate(h,candidates[0]);assert base['scientific_configuration']==old['scientific_configuration']
        period=base['configuration']['task']['timing']['control_period_s'];duration=base['configuration']['task']['timing']['duration_s']
        dt=base['configuration']['task']['timing']['timestep_s'];assert round(duration/dt)*9<=9000
        sources=[]
        for i,candidate in enumerate(candidates):
            seed=dict(candidate=candidate,method='baseline')
            if i:seed.update(parent=candidates[0],source=sources[0])
            out=plan(h,'initialize_control','seed-'+str(i),candidate=candidate,control_seed=seed)
            sources.append(out['result']['source'])
        trajectories=[h.store.artifact(r)['trajectory'] for r in sources]
        assert all(all(t[k]==trajectories[0][k] for k in ('times_s','tendon_order','tensions_n')) for t in trajectories)
        info=dict(candidates=candidates,sources=sources,M0_reference=m0ref,adoption=adoption,parameter=PATH,step=hstep,
            settings=dict(version='local_control_search_v2',method='response',knots_s=[0.,duration],correction_window_s=[0.,duration],
                active_coefficients=[0],coefficient_limit_n=.5,difference_step_n=.01,initial_radius_n=.1,minimum_radius_n=.0001,
                evaluation_requests=3,iterations=1,safety_margin_fraction=0.))
        atomic_json(prep,info)
    refs=[]
    for i,(candidate,control) in enumerate(zip(info['candidates'],info['sources'])):
        plan(h,'diagnose','diagnose-T1-'+str(i),candidate=candidate,evidence=[m0ref])
        out=analysis.dispatch(h,dict(candidate=candidate,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=state(h)['spec']['analysis_protocol'],
            control_optimization=dict(source=control,settings=info['settings'])),'b-T1-'+str(i),guard=core.guard,origin='engineering_preflight')
        atomic_json(DEST/('t1-'+str(i)+'-response.json'),out)
        assert out.get('reference'),out
        refs.append(out['reference']);raw=h.store.artifact(out['reference'])
        print(json.dumps(dict(stage='T1-'+str(i),status=raw['status'],J=raw.get('nonlinear_capability',{}).get('J'),cost=raw.get('native_dynamics',{}).get('cost'))),flush=True)
        if raw['status']!='computed':
            export_results(h,info,refs,None);return
    base=info['candidates'][0];plan(h,'diagnose','diagnose-M2',candidate=base,evidence=refs)
    q=dict(version='scientific_question_v2',operation='differentiate',effect_semantics='reoptimized_task_capability',
        parameter_paths=[PATH],target='holding_max_speed_m_s',operating_point='frozen_task_initial_state',control_treatment='reoptimized',
        requested_budget=1,source_selection=dict(t1_results=refs))
    compiled=compile_question(h,q,tool_use_id='b-high-level-M2');atomic_json(DEST/'m2-compiled.json',compiled)
    assert compiled['status']=='ready',compiled
    out=analysis.dispatch(h,compiled['request'],'b-T2',guard=core.guard,origin='engineering_preflight');atomic_json(DEST/'t2-response.json',out)
    assert out.get('reference'),out
    raw=h.store.artifact(out['reference']);assert raw.get('nonlinear_response',{}).get('cost',{}).get('physics_steps')==0
    export_results(h,info,refs,out['reference'])


if __name__=='__main__':main()
