"""B5 engineering inputs only; original generator/initialize_control, no dispatch."""
from tools.research import core
from tools.research.config import ROOT
from tools.research.contracts import ControlSeedRequest
from tools.research.design import generate_candidate,verify_candidate
from tools.research.physical_replay import seed_control,binding
from tools.research.state import state,save
from tools.state_io import atomic_json,read

SPEC='study_p63b5_m_native_sol_prepared.json'


def prepare_study(spec_path=None):
    h=core.prepare(spec_path or ROOT/'configs/research'/SPEC)
    path=h.store.root/'b5_preparation.json'
    if path.exists():return h,read(path)
    h.actor='Operator';spec=state(h)['spec']
    generation=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
        segment_count=2,tendon_count=4)
    provenance=dict(decision_owner='Operator',origin='operator_provided_unmeasured_baseline',
        scope='B5 engineering structure input; legal compilation only, no scientific or task evaluation.')
    candidate=generate_candidate(h,generation,provenance)['candidate']
    seed=dict(candidate=candidate,method='baseline')
    # This is exactly the baseline implementation used by research_plan(initialize_control).
    # No Plan is invented on behalf of Main and no authorization is created.
    initialized=seed_control(h,ControlSeedRequest.model_validate(seed),'operator-p63b5-initialize-control')
    source=h.store.artifact(initialized['source']);cfg=verify_candidate(h,candidate)['configuration']
    binding(cfg,source['trajectory'])
    control_provenance=save(h,dict(decision_owner='Operator',origin='operator_initialize_control_baseline',
        candidate=candidate,source=initialized['source'],request=seed,
        implementation='research_plan(initialize_control) -> seed_control(method=baseline)',
        original_source_provenance=source['provenance'],task_acceptance='unmeasured',
        scope='Engineering input ownership only; not a Main Plan, mathematical result or task evaluation.'),
        'operator_control_initialization_provenance')
    result=dict(study_id=h.run_id,store=str(h.store.root),resolved_identity=spec['resolved_identity'],
        configuration=SPEC,baseline=candidate,baseline_generation_request=generation,
        baseline_provenance=provenance,control_initialization=initialized,
        control_seed_request=seed,control_operator_provenance=control_provenance,
        source_provenance=source['provenance'],task_acceptance='unmeasured',
        task_identity=spec['canonical_task_identity'],family_space_identity=spec['family_space_identity'],
        budgets=spec['budgets'],native_control_limits=spec['native_control_limits'],
        provider=dict(model=spec['runtime']['provider']['model'],reasoning=spec['runtime']['provider']['reasoning']),
        trajectory_binding={k:source['trajectory'][k] for k in
            ('tendon_order','task_identity','model_identity','design_identity')},
        time_grid=dict(points=len(source['trajectory']['times_s']),intervals=len(source['trajectory']['tensions_n']),
            start_s=source['trajectory']['times_s'][0],end_s=source['trajectory']['times_s'][-1],
            period_s=cfg['task']['timing']['control_period_s']),
        default_tensions_n=source['trajectory']['tensions_n'][0],
        tension_bounds_n=[[0.,t['force_limit_n']] for t in cfg['robot']['structure']['data']['tendons']],
        authorization='pending separate explicit approval; no formal authorization or live handoff admission',
        imported_scientific_results=[],main_plans=0,real_provider_requests=0,scientific_workers=0)
    result['preparation_reference']=save(h,result,'operator_b5_preparation')
    atomic_json(path,result)
    return h,result


if __name__=='__main__':
    import json
    print(json.dumps(prepare_study()[1],ensure_ascii=False,indent=2))
