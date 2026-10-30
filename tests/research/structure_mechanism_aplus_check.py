"""Exactly three predeclared A+ checks. Commit first; never reset/retry receipts.

Existing reach_free, FamilySpace, budget, worker, NativeModel and Store only.
15 native attempts maximum, zero integration, real Provider or task evaluation.
"""
from copy import deepcopy
import json
import os
from tools.research import core,analysis,reporter
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.research.design import generate_candidate
from tools.research.scientific_intent import compile_question
from tools.research.research_context import agent_decision_brief
from tools.state_io import atomic_json,read,digest

DEST=ROOT/'runs/structure_mechanism_aplus'
CHECKS=[
    ('section','segments.1.sections.0.parameters.width_y_m',dict(quantity='directional_acceleration_bounds',reduction='maximum',direction_world=[0.,.6,.8],goal='increase')),
    ('material','segments.1.physical_parameters.density_kg_m3',dict(quantity='directional_acceleration_bounds',reduction='maximum',direction_world=[0.,.6,.8],goal='increase')),
    ('routing','spans.0.phase_rad',dict(quantity='directional_drive',tendon_channel=0,direction_world=[0.,.6,.8],goal='increase')),
]


def main():
    h=core.prepare(ROOT/'configs/research/study_structure_mechanism_aplus_check.json',DEST/'store')
    h.actor='operator-aplus-bounded-check'
    for key,value in state(h)['spec']['runtime']['threads'].items():os.environ[key]=value
    if 'freeze' not in state(h):core.bind(h)
    core.guard(h)
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],
        execution_scopes=['registered mathematics'],maximum_mechanism_evaluations=15,
        checks=CHECKS,physics_steps=0,provider_requests=0,independent_task_evaluations=0)
    if not any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)):
        save(h,dict(user_approval='User A+ A6/A8 explicitly requests three minimal representative real MuJoCo checks; not an autonomous Study.',
            scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    prep=DEST/'preparation.json'
    if prep.exists():candidate=read(prep)['candidate']
    else:
        out=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
            segment_count=2,tendon_count=4),dict(origin='user_authorized_aplus_bounded_check',historical_answers_imported=False))
        assert out['status']=='generated',out
        candidate=out['candidate'];atomic_json(prep,dict(candidate=candidate,scope=scope))
    before=deepcopy(state(h)['candidates']);summaries=[];refs=[]
    for category,path,target in CHECKS:
        core.dispatch(h,dict(action='diagnose',hypothesis='A legal '+category+' perturbation changes the specified directional native mechanism at the task initial state.',
            expected_observation='Actual rebuilt coefficients change and two normalized scales agree if the selected mechanism is numerically distinguishable.',
            weakening_observation='Flat, inconsistent, illegal or insufficient numerical response; retain unresolved.',
            fixed_conditions='Registered reach_free task, topology, other parameters, task initial state and absolute tensions.',
            stopping_condition='One five-attempt difference for this category; no budget enlargement or task evaluation.',
            interpretation='Local model diagnostic; task capability unmeasured.',
            decision=dict(hypothesis_id='aplus-'+category,research_intent='DIAGNOSE',selected_candidate=candidate,requested_budget=5)),
            'aplus-diagnose-'+category)
        question=dict(version='scientific_question_v2',operation='differentiate',effect_semantics='mechanism_effect',
            parameter_paths=[path],target=target,operating_point='frozen_task_initial_state',
            control_treatment='fixed_absolute_tensions',requested_budget=5)
        receipt=DEST/(category+'-response.json')
        if receipt.exists():out=read(receipt)
        else:
            compiled=compile_question(h,question,tool_use_id='aplus-question-'+category)
            assert compiled['status']=='ready',compiled
            atomic_json(DEST/(category+'-compiled.json'),compiled)
            out=analysis.dispatch(h,compiled['request'],'aplus-native-'+category,guard=core.guard,origin='engineering_preflight')
            atomic_json(receipt,out)
        assert out.get('reference'),out
        refs.append(out['reference']);raw=h.store.artifact(out['reference']);atomic_json(DEST/(category+'-raw.json'),raw)
        evidence=raw.get('structure_research',{});sensitivity=evidence.get('sensitivity',{});cost=evidence.get('cost',{})
        summaries.append(dict(category=category,parameter_path=path,reference=out['reference'],status=raw['status'],reason=raw.get('reason'),
            target=target,baseline=evidence.get('baseline'),perturbed_metrics=[r['observation']['value'] for r in evidence.get('records',[])[1:]],
            derivatives=sensitivity.get('derivatives'),derivative_unit=sensitivity.get('derivative_unit'),
            normalized_derivatives=sensitivity.get('normalized_derivatives'),steps=sensitivity.get('steps'),
            consistency=sensitivity.get('consistency'),model_effect_observed=sensitivity.get('model_effect_observed'),
            compiled_physical_changes=[r['compiled_physical_changes'] for r in evidence.get('records',[])[1:]],
            direction_status=evidence.get('direction_status'),structure_direction=evidence.get('structure_direction'),cost=cost,
            charged_evaluations=raw.get('charged_analysis_evaluations'),charged_numerical_s=raw.get('charged_numerical_s')))
        atomic_json(DEST/'partial-validation.json',dict(scope=scope,checks=summaries))
        print(json.dumps(dict(category=category,status=raw['status'],baseline=evidence.get('baseline',{}).get('value'),
            direction_status=evidence.get('direction_status'),cost=cost)),flush=True)
    assert state(h)['candidates']==before
    assert state(h)['mathematical_evaluations']<=15
    assert not state(h)['results'] and not state(h)['physical_replays']
    assert h.store.remaining()['used']['model_calls']==0
    for row in summaries:
        assert row['cost'].get('evaluation_attempts',0)<=5
        assert row['cost'].get('physics_steps',0)==row['cost'].get('rollouts',0)==0
    report=reporter.assemble(h,refs)
    assert all(r.mathematics.claim.conclusion=='diagnostic' for r in report.results)
    validation=dict(scope=scope,task_environment='reach_free',checks=summaries,
        status='passed' if all(r['status']=='computed' and r['model_effect_observed'] for r in summaries) else 'incomplete',
        charged_evaluations=state(h)['mathematical_evaluations'],formal_candidate_created=False,
        provider_requests=0,task_acceptance='unmeasured',full_task_improvement_verified=False,
        l0=agent_decision_brief(h),reporter=report.model_dump(mode='json'))
    atomic_json(DEST/'validation.json',validation)
    core.export(h)
    atomic_json(ROOT/'evidence/structure_mechanism_aplus/validation.json',validation)
    print(json.dumps(dict(status=validation['status'],charged_evaluations=validation['charged_evaluations'],formal_candidate_created=False)))


if __name__=='__main__':main()
