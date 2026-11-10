"""Only v1.2 launch admission; no Provider send, physical integration or high mesh build."""
import os
for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[name]='1'
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from tools.state_io import read,digest,atomic_json
from tools.platform_store import Store,plain
from tools.research.config import resolve
from tools.research.design import family_configuration,final_fidelity_matches
from tools.research.contracts import MechanismStudy
from tools.research.structure_research import prepare_context,parameters
from schemas.platform import SessionInput,TaskDefinition
from extensions.reference.contracts import PassiveResponseEvaluationV2

ROOT=Path(__file__).resolve().parents[3]
DOC=Path(__file__).resolve().parent
SPEC=ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json'
OLD=ROOT/'runs/research/p3-passive-progressive-stiffness-autonomous-20261109-01'
NAME='p3-passive-progressive-stiffness-autonomous-20261110-v1_2'


def main():
    guards=[patch('mujoco.mj_step',side_effect=AssertionError('PREFLIGHT_INTEGRATION_FORBIDDEN')),
        patch('httpx.Client.send',side_effect=AssertionError('PREFLIGHT_PROVIDER_FORBIDDEN')),
        patch('httpx.AsyncClient.send',side_effect=AssertionError('PREFLIGHT_PROVIDER_FORBIDDEN'))]
    for guard in guards:guard.start()
    checks=[]
    def checked(name,details):checks.append(dict(name=name,passed=True,details=details))
    spec=resolve(SPEC);original=read(ROOT/'tasks/passive_progressive_stiffness_dev_v1_1.json')['task']
    task=spec['canonical_task'];TaskDefinition.model_validate(task)
    checked('task_parser',dict(task_id=task['task_id'],identity=digest(task)))
    left=deepcopy(original);right=deepcopy(read(ROOT/'tasks/passive_progressive_stiffness_dev_v1_2.json')['task'])
    for value in (left,right):
        for key in ('task_id','task_version','name','source'):value.pop(key)
        value['evaluator']['parameters']['data']['numerical_confirmation'].pop('variants',None)
    assert left==right
    assert task['evaluator']['parameters']['data']['numerical_confirmation']['variants']==[]
    assert plain(PassiveResponseEvaluationV2.model_validate(original['evaluator']['parameters']['data']).numerical_confirmation)==original['evaluator']['parameters']['data']['numerical_confirmation']
    checked('core_thresholds_unchanged',dict(exact_task_comparison_exclusions=['identity metadata','confirmation variants'],legacy_confirmation_serialization_unchanged=True))
    from tools.research.contracts import fidelity_levels
    levels=fidelity_levels(spec['fidelity_policy'])
    assert levels['final_evaluation']['cells_per_segment']==2
    assert spec['fidelity_policy']['refinement']['refinement2']['cells_per_segment']==2
    assert {v['cells_per_segment'] for v in spec['fidelity_policy']['numerical_sensitivity'].values()}=={4,8,12,16,32}
    checked('final_two_cells_optional_higher',dict(policy=spec['fidelity_policy'],required_confirmation_variants=[]))
    space=spec['family_space'];assert space['segment_count_bounds']==[2,6] and space['tendon_count_bounds']==[2,4]
    assert spec['initial_structure_strategy']=='agent_choice' and not spec['supplied_evidence'] and not spec['research_decisions']['background']
    checked('original_p3_domain_no_seed',dict(segment_bounds=[2,6],tendon_bounds=[2,4],candidate_pool='not created by preflight'))
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=2,
        segments={'0':dict(length_m=.025,cells=2),'1':dict(length_m=.025,cells=2)},payout_offsets_m={'tendon_0':.001,'tendon_1':.001})
    cfg,build,_=family_configuration(spec['configuration'],space,request,'unregistered-v1_2-preflight-fixture')
    inp=SessionInput.model_validate(cfg)
    assert set(inp.policy.discretization.data['cells'].values())=={2}
    from extensions.tendon_family.passive_execution import PassiveBackend
    from tools.platform_tasks import compile_input
    from tools.platform_registry import registry
    compiled=compile_input(cfg,registry());PassiveBackend.check(inp,inp.policy.backend.parameters,None)
    assert compiled
    from tools.research.execution_worker import main as worker_entry
    assert callable(worker_entry)
    checked('real_two_cell_compiler_worker_evaluator_admission',dict(backend=cfg['policy']['backend']['extension_id'],cells=cfg['policy']['discretization']['data']['cells'],worker='tools.research.execution_worker -> physical_replay.calculate -> PassiveBackend',integration_calls=0))
    candidate=dict(configuration=cfg,parameters=plain(build.request),generation_version='serial_family_generation_v2',task_identity=spec['canonical_task_identity'],
        family_space_identity=spec['family_space_identity'],fidelity_policy_identity=digest(spec['fidelity_policy']),final_evaluation_identity=spec['final_evaluation_identity'])
    assert final_fidelity_matches(spec,candidate)
    base=dict(operation='inspect',point_semantics='frozen_task_initial_state',target=dict(quantity='finite_time_task_violation',goal='decrease'),
        effect_semantics='finite_time_task_response',execution_profile=dict(purpose='exploration',load_conditions=['plus_x'],stage_prefix='low',fidelity='screening'),max_evaluations=1)
    context=prepare_context(spec,candidate,MechanismStudy.model_validate(base),[])
    assert context['dynamic_cost_bound']['episodes']==1
    from tools.research.search import search_problem
    from tools.research.structure_intent import compile_search
    host=SimpleNamespace(store=Mock());s=dict(spec=spec,profile=dict(identity='fixture'),base_configuration=spec['configuration'])
    search=dict(version='scientific_structure_search_v1',research_goal='passive_structure_research',design_variable_groups=['lengths'],evaluation_model='passive_task_response',
        control_treatment='no_active_control',structure_search_effort=dict(max_proposals=2,max_evaluations=2),proxy_objective='task_violation',segment_counts=[2],tendon_counts=[2],
        bounds={'length_m':[.025,.1]},screening_fidelity='screening',execution_profile=base['execution_profile'])
    with patch('tools.research.structure_intent.state',return_value=s),patch('tools.research.search.state',return_value=s),patch('tools.research.structure_intent.save'),patch('tools.research.analysis.admission',return_value=dict(admitted=2)):
        plan=compile_search(host,dict(action='search',search=search,decision=dict(hypothesis_id='unregistered-offline-fixture'),
            hypothesis='Offline admission fixture',expected_observation='No execution',weakening_observation='No execution',
            fixed_conditions='Frozen task',stopping_condition='Compile only',interpretation='Not a Main Plan or scientific evidence'),'v1_2-offline')
        admitted=search_problem(host,plan['search'],2)
    assert admitted['passive_problem']['action']=='baseline_response'
    assert spec['family_search']['coupled_block_enabled']
    coupled=dict(version='family_mixed_search_v2',family_space_identity=spec['family_space_identity'],previous_candidate_ref={'artifact_id':'a'*64},
        analysis=dict(effect_semantics='finite_time_task_response',target='finite_time_task_violation',parameter_paths=['segments.0.young_pa','segments.1.young_pa'],
            operating_point='frozen_task_initial_state',control_treatment='no_active_control',physical_problem='passive_unilateral_equilibrium',execution_profile=base['execution_profile']))
    with patch('tools.research.search.state',return_value=s),patch('tools.research.search.verify_candidate',return_value=candidate):
        block=search_problem(host,coupled,4)
    assert len(block['points'])==4
    checked('baseline_coordinate_coupled_admission',dict(single_direction_prefix_episodes=1,baseline_ablation_required=False,coordinate_search=True,coupled_blocks=True))
    rows=parameters(spec,candidate);assert rows and spec['family_sensitivity_variables']['variables']==['*']
    from tools.research.structure_research import finite_time_discovery
    methods=finite_time_discovery(cfg)
    checked('main_parameter_and_method_discovery',dict(parameter_count=len(rows),parameter_ids=[r['parameter_id'] for r in rows],finite_time=methods,search=spec['family_search']))
    manifest=spec['knowledge_manifest'];ids={r['entry_id'] for r in manifest['entries']}
    required=set(read(SPEC)['knowledge']['include_entry_ids']);assert required<=ids
    assert [r['revision'] for r in manifest['entries'] if r['entry_id']=='p3-case']==['3']
    assert not any(r.get('benchmark_sensitive') for r in manifest['entries'])
    for row in manifest['entries']:
        value=read(ROOT/row['path'])['entries'][row['content_key']] if row.get('content_key') else (ROOT/row['path']).read_bytes()
        if row.get('content_key'):assert digest(value)==row['content_sha256']
        else:
            import hashlib
            assert hashlib.sha256(value).hexdigest()==row['content_sha256']
    atomic_json(DOC/'knowledge-manifest.json',manifest)
    checked('specified_answer_isolated_knowledge',dict(entries=[r['entry_id']+'@'+r['revision'] for r in manifest['entries']],manifest_identity=digest(manifest)))
    b=spec['budgets'];assert b['provider_requests']==80 and b['protected_provider_requests']==0
    assert all(b[k] is None for k in ('public_operations','physical_launches','mathematical_evaluations','offline_nlp','bdf_replays','numerical_s','activity_s','local_solve_s','delivery_reserve_s'))
    assert spec['physical_replay_limit'] is None and spec['family_search']['max_proposals'] is None and spec['family_search']['max_evaluations'] is None and spec['analysis_cap_s'] is None
    checked('provider_shared_80',dict(total=80,role_subbudgets=False,extra_requests=False))
    checked('cumulative_science_unlimited',dict(budgets=b,replay_limit=None,search_limits=None,physics_step_limit=None,candidate_limit=None,worker_watchdogs_s=[spec['physical_worker_watchdog_s'],spec['mathematical_worker_watchdog_s']],legacy_local_solves='inactive NMPC diagnostic, not passive research'))
    old=Store(OLD);old_state=old.session('p3-passive-progressive-stiffness-autonomous-20261109-01')['state']
    assert not (ROOT/'runs/research'/NAME).exists()
    checked('independent_new_store',dict(old_store=str(old.db),new_store=str(ROOT/'runs/research'/NAME),old_state_identity=digest(old_state),old_ledger=old.remaining(),new_store_exists=False,old_supervisor_pauses=[e['kind'] for e in old.events('p3-passive-progressive-stiffness-autonomous-20261109-01') if e['kind']=='supervisor_pause'][-1:]))
    from tools.research.tool_readiness import execution_environment
    environment=execution_environment(spec);assert environment['status']=='ready'
    checked('runtime_environment',environment)
    result=dict(ready=True,checks=checks,physics_integrations=0,provider_requests=0,high_fidelity_builds=0,old_state_identity=digest(old_state),old_ledger=old.remaining())
    atomic_json(DOC/'preflight.json',result)
    print(json.dumps(dict(ready=True,checks=[c['name'] for c in checks]),ensure_ascii=True))


if __name__=='__main__':main()
