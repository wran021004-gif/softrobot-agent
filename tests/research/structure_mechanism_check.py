"""One explicitly authorized six-model engineering check via production admission.

No Provider, control search, rollout, task evaluator or autonomous Agent. Run once
after committing. Existing receipts are reused; failures/costs are never reset.
"""
from copy import deepcopy
import json
import os
import numpy as np
from tools.research import core, analysis, reporter
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.research.design import generate_candidate
from tools.research.scientific_intent import compile_question
from tools.research.evidence_views import result_card
from tools.research.contracts import MechanismTarget
from tools.state_io import atomic_json,digest,read
from extensions.math_analysis.mechanism_registry import observe


DEST=ROOT/'runs/structure_mechanism_m01'


def main():
    h=core.prepare(ROOT/'configs/research/study_structure_mechanism_m01_check.json',DEST/'store')
    h.actor='operator-structure-mechanism-check'
    for key,value in state(h)['spec']['runtime']['threads'].items():os.environ[key]=value
    if 'freeze' not in state(h):core.bind(h)
    core.guard(h)
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],
        execution_scopes=['registered mathematics'],maximum_mechanism_evaluations=6,
        physics_steps=0,provider_requests=0,independent_task_evaluations=0)
    if not any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)):
        save(h,dict(user_approval='Explicit user Softrobot-Agent A A7: one tiny controlled accounted MuJoCo numerical check; not a full autonomous Study.',
            scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    prep=DEST/'preparation.json'
    if prep.exists():candidate=read(prep)['candidate']
    else:
        generated=generate_candidate(h,dict(version='serial_family_generation_v2',
            family_space_identity=state(h)['spec']['family_space_identity'],segment_count=2,tendon_count=4),
            dict(origin='user_authorized_bounded_engineering_check',historical_answers_imported=False))
        assert generated['status']=='generated',generated
        candidate=generated['candidate'];atomic_json(prep,dict(candidate=candidate,scope=scope))
    original=deepcopy(state(h)['candidates'])
    core.dispatch(h,dict(action='diagnose',hypothesis='A small legal first-segment length change alters local tension-to-tip acceleration authority at the frozen initial pose.',
        expected_observation='Two finite-difference scales agree in direction for the registered acceleration-map norm.',
        weakening_observation='Sign disagreement, illegal structure, nonfinite mechanics or a flat local response.',
        fixed_conditions='Registered reach_free task, topology, remaining geometry, named initial coordinates and absolute tensions.',
        stopping_condition='One six-model local mechanism computation; zero physics steps.',
        interpretation='Operator engineering hypothesis; full task improvement remains unmeasured.',
        decision=dict(hypothesis_id='bounded-mechanism-length',research_intent='DIAGNOSE',
            selected_candidate=candidate,requested_budget=6)), 'structure-mechanism-diagnose')
    question=dict(version='scientific_question_v2',operation='optimize',effect_semantics='mechanism_effect',
        parameter_paths=['segments.0.length_m'],target=dict(quantity='tip_acceleration_input_map',reduction='norm',goal='increase'),
        operating_point='frozen_task_initial_state',control_treatment='fixed_absolute_tensions',requested_budget=6)
    if (DEST/'response.json').exists():out=read(DEST/'response.json')
    else:
        compiled=compile_question(h,question,tool_use_id='operator-structure-mechanism-question')
        assert compiled['status']=='ready',compiled
        out=analysis.dispatch(h,compiled['request'],'structure-mechanism-six-models',guard=core.guard,origin='engineering_preflight')
        atomic_json(DEST/'response.json',out)
    assert out.get('reference'),out
    raw=h.store.artifact(out['reference']);atomic_json(DEST/'raw.json',raw)
    assert raw['status']=='computed',raw
    evidence=raw['structure_research'];cost=evidence['cost'];response=evidence['sensitivity']
    assert cost['model_builds']==cost['mechanics_evaluations']==cost['evaluation_attempts'],cost
    assert 5<=cost['evaluation_attempts']<=6,cost
    assert cost['physics_steps']==cost['rollouts']==0,cost
    assert state(h)['mathematical_evaluations']==6
    assert state(h)['candidates']==original
    assert not state(h)['results'] and not state(h)['physical_replays']
    assert h.store.remaining()['used']['model_calls']==0
    assert raw['charged_analysis_evaluations']==6
    direction=evidence.get('structure_direction')
    if direction:
        assert direction['full_task_improvement_verified'] is False and direction['formal_candidate_created'] is False
        assert response['consistency']['passed'] and evidence['local_proposal_recheck']['passed']
    else:
        assert response['direction_status']=='unresolved' and response['suggested_delta'] is None
    base=evidence['records'][0]['mechanics']
    # Independent shape/unit checks against the already computed raw mechanics.
    expected_shapes=dict(tip_jacobian=(3,len(base['qpos_rad'])),tendon_jacobian=(4,len(base['qpos_rad'])),
        input_force_map=(len(base['qpos_rad']),4),mass_matrix=(len(base['qpos_rad']),len(base['qpos_rad'])),
        tip_acceleration_input_map=(3,4),drive_singular_values=(3,),drive_directions=(3,3))
    for name,shape in expected_shapes.items():
        value=observe(base,MechanismTarget(quantity=name))
        assert tuple(value['metadata']['actual_shape'])==shape
    np.testing.assert_allclose(evidence['baseline']['value'],np.linalg.norm(base['tip_acceleration_input_map_m_s2_n']))
    assert observe(base,dict(quantity='instantaneous_braking'))['reason']=='NONZERO_VELOCITY_REQUIRED'
    # Parameter effectiveness is observable even when the chosen function metric
    # is flat. Never demand an improving direction from a numerical check.
    changed=evidence['records'][1]['mechanics']['mass_matrix_kg_m2']
    assert np.max(abs(np.asarray(changed)-base['mass_matrix_kg_m2']))>1e-9
    card=result_card(h,out['reference']);report=reporter.assemble(h,[out['reference']])
    assert card.evidence_summary.claim_kind=='NUMERICAL_DIAGNOSTIC'
    assert report.results[0].mathematics.claim.conclusion=='diagnostic'
    summary=dict(status='passed',scope=scope,reference=out['reference'],
        task_environment='reach_free',candidate_count=len(original),baseline=evidence['baseline']['value'],
        perturbed_metrics=[r['observation']['value'] for r in evidence['records'][1:]],metric_unit=evidence['baseline']['unit'],
        parameter=raw['requested_operation']['mechanism_study']['parameter_path'],baseline_length_m=response['value'],
        proposed_delta_m=direction['delta'] if direction else None,direction_status=response['direction_status'],
        parameter_effect_mass_matrix_inf=float(np.max(abs(np.asarray(changed)-base['mass_matrix_kg_m2']))),
        steps_m=response['steps'],derivatives=response['derivatives'],
        derivative_unit=response['derivative_unit'],consistency=response['consistency'],cost=cost,
        charged_analysis_evaluations=raw['charged_analysis_evaluations'],charged_numerical_s=raw['charged_numerical_s'],
        formal_candidate_created=False,task_acceptance='unmeasured',full_task_improvement_verified=False)
    atomic_json(DEST/'validation.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
