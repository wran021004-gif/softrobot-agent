"""Bounded real-engine regression of the shared v2 passive path."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import unittest
import json
from unittest.mock import patch
from schemas.platform import SessionInput, EvidenceRef
from tools.platform_store import plain
from tools.research.config import resolve
from tools.platform_registry import registry
from tools.research_tasks import task_adapter,assemble_acceptance
from tools.research.physical_replay import evaluate_playback
from extensions.tendon_family.passive_execution import execute,execute_pair,restore_state
from extensions.reference.passive_response import evaluate,inspect_evidence

ROOT=Path(__file__).resolve().parents[2]


def configuration_v2():
    cfg=resolve(ROOT/'configs/research/study_passive_engineering_v1.json')['configuration'];task=cfg['task']
    case='lateral';forces=[0.,.002,.004,.006,0.];names=['unloaded','low','middle','high','recovery'];stages=[]
    for i,(name,force) in enumerate(zip(names,forces)):
        start=round(i*.1,10);end=round((i+1)*.1,10)
        stages.append(dict(name=name,start_s=start,end_s=end,force_start_world_n=[0.,forces[i-1] if i else 0.,0.],
            force_end_world_n=[0.,force,0.],interpolation='smoothstep' if i else 'hold',ramp_until_s=round(start+.05,10),
            observation_window_s=[start,end],scoring_window_s=[round(end-.02,10),end]))
    task['goal'].update(version='2.0.0',data=dict(version='passive_response_v2',load_conditions=[case],programs={case:stages},
        protocol_source=dict(artifact_id='0'*64),force_sampling='interval_end',static_balance_reference='copied_integration_zero_velocity',
        initial_source='qualified_unloaded',allow_saved_state=True,unloaded_stage='unloaded',qualifications=[dict(stage='unloaded',window_s=[.08,.1],
            tip_speed_max_m_s=.001,monitor_speed_max_m_s=.001,qvel_max_rad_s=.01,tail_drift_max_m=.0005,static_balance_max_nm=1e-5,
            length_excess_max_m=5e-5,sampling='every_physics_step')],solreflimit=[.004,1.],solimplimit=[.999,.999,.001,.5,2.],
        length_tolerance_m=5e-5,tension_tolerance_n=.005,multiplier_sign_tolerance_n=0.,constraint_direction_tolerance=1e-12,
        force_map_tolerance_nm=1e-12,allowed_ablation='disable_selected_passive_limits',recording='full_physics_csv'))
    task['evaluator']['version']='2.0.0';task['evaluator']['parameters'].update(version='2.0.0',data=dict(bounds=[dict(name='response',
        quantity='material_displacement',load_condition=case,material_s=.5,window='high',reference_window='unloaded',maximum=.1)]))
    task['timing']['duration_s']=.5;task['sampling']['window_s']=[0.,.5]
    task['physical_problem']['loads']=[v for v in task['physical_problem']['loads'] if v['name'] in ('unloaded',case)]
    task['physical_problem']['loads'][1]['force_world_n']=[0.,.006,0.]
    task['observations']=[v for v in task['observations'] if v['entity'].startswith(case+'__')]
    task['objectives'][0]['metric']='response_maximum'
    return cfg


def prepared_host_v2(*,failure=False):
    from tools.research import core
    from tools.research.state import state,save,update
    from tools.state_io import digest
    name='u3-wire-'+uuid4().hex[:10];cfg=json.loads((ROOT/'configs/research/study_passive_engineering_v1.json').read_text())
    task=configuration_v2()['task'];source=dict(version='u3_small_engineering_protocol',scope='Bounded zero-gravity test only; not a PHS/P3 substitute')
    if failure:task['evaluator']['parameters']['data']['bounds'][0]['maximum']=1e-9
    task['goal']['data']['protocol_source']=dict(artifact_id=digest(source))
    task_path=ROOT/'tasks'/('._'+name+'.json');study_path=ROOT/'configs/research'/('._'+name+'.json')
    cfg.update(study_id=name,evidence_destination='runs/'+name,task='../../tasks/'+task_path.name,mode='formal_research')
    cfg['budgets']['physical_launches']=8;cfg['physical_replay_limit']=8
    task_path.write_text(json.dumps(dict(task=task,seed=1)));study_path.write_text(json.dumps(cfg))
    try:h=core.prepare(study_path,ROOT/'runs'/name)
    finally:task_path.unlink();study_path.unlink()
    core.bind(h);save(h,source,'frozen_engineering_protocol')
    scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=['registered mathematics'])
    save(h,dict(user_approval='User authorized U3 bounded engineering verification.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    pilot=state(h)['pilot'];pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback');update(h,pilot=pilot)
    from tools.research.design import generate_candidate
    s=state(h);result=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],segment_count=1,tendon_count=1),dict(origin='u3_engineering'))
    assert result['status']=='generated',result
    return h,result['candidate']


class PassiveProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=configuration_v2();cls.inp=SessionInput.model_validate(cls.cfg)
        cls.folder=ROOT/'runs/u3_tests'/uuid4().hex;cls.backend=execute(cls.inp,cls.folder)
        cls.raw=cls.backend.data.data;cls.ref=EvidenceRef(artifact_id='0'*64)

    def test_real_program_qualification_and_continuity(self):
        self.assertEqual(self.raw['status'],'completed',self.raw.get('reason'))
        self.assertEqual(inspect_evidence(self.inp.task,self.raw),('valid',None))
        e=self.raw['episodes'][0];self.assertEqual(e['state_resets'],1)
        self.assertEqual(len(e['phase_boundaries']),5);self.assertEqual(e['checked_physics_steps'],500)
        self.assertEqual(len(e['qualification_samples']),21)
        self.assertEqual(self.raw['trace_files'][0]['physics_steps'],500)
        registry().parse(self.backend.data)
        ev,profile=evaluate_playback(self.cfg,self.raw,plain(self.ref),'v2-fixture')
        profile.update(execution_id='fixture',simulation=plain(self.ref),evaluation=plain(self.ref))
        acceptance=assemble_acceptance(self.cfg,ev,profile,evaluation_reference=self.ref,profile_reference=self.ref)
        self.assertEqual(ev.validity,'valid',ev.reason);self.assertEqual(acceptance['status'],'accepted',acceptance)
        self.assertEqual(task_adapter(self.cfg).describe()['registered_acceptance'],'offline_passive_response_v2')
        self.assertFalse(task_adapter(self.cfg).ppo_applicability()['supported'])

    def test_evidence_mutations_are_not_accepted(self):
        for field,value in [('force_world_n',[1.,0.,0.]),('constraint_classification',['taut']),('engine_time_s',100.)]:
            raw=deepcopy(self.raw);raw['episodes'][0]['samples'][20][field]=value
            self.assertNotEqual(inspect_evidence(self.inp.task,raw)[0],'valid',field)
        raw=deepcopy(self.raw);raw['episodes'][0]['qualification_samples'].pop()
        self.assertEqual(inspect_evidence(self.inp.task,raw)[0],'incomplete')
        raw=deepcopy(self.raw);raw['episodes'][0]['phase_boundaries'][1]['integration_state']['state_vector'][0]=0
        self.assertEqual(inspect_evidence(self.inp.task,raw)[0],'invalid')
        raw=deepcopy(self.raw);raw['episodes'][0]['integration_initial'].pop('state_vector')
        self.assertNotEqual(inspect_evidence(self.inp.task,raw)[0],'valid')

    def test_real_saved_full_state_and_pair(self):
        state=self.raw['episodes'][0]['qualified_state']
        restored=execute(self.inp,ROOT/'runs/u3_tests'/uuid4().hex,initial_state=state,initial_state_result=plain(self.ref))
        self.assertEqual(inspect_evidence(self.inp.task,restored.data.data),('valid',None))
        self.assertEqual(restored.data.data['cost']['integration_state_restores'],1)
        name=self.raw['tendon_order'][0]
        paired=execute_pair(self.inp,ROOT/'runs/u3_tests'/uuid4().hex,[name]);raw=paired.data.data
        self.assertEqual(raw['status'],'completed',raw.get('reason'));self.assertEqual(raw['cost']['physics_steps'],1000)
        self.assertEqual(raw['model_builds'],2)
        self.assertEqual(raw['episodes'][0]['qualified_state'],raw['paired_ablation']['ablation']['episodes'][0]['qualified_state'])
        self.assertEqual(inspect_evidence(self.inp.task,raw),('valid',None))
        self.assertEqual(inspect_evidence(self.inp.task,raw['paired_ablation']['ablation'])[0],'invalid')
        with self.assertRaisesRegex(ValueError,'EXACT_UNIQUE'):execute_pair(self.inp,ROOT/'runs/u3_tests'/uuid4().hex,[name,name])

    def test_version_and_program_rejections(self):
        for mutate in ('gap','active','version'):
            cfg=deepcopy(self.cfg)
            if mutate=='gap':cfg['task']['goal']['data']['programs']['lateral'][1]['start_s']=.11
            elif mutate=='active':cfg['task']['actuator_channels']=[dict(name='tendon_tension',entity='tendon_0',dimension=1,units='N')]
            else:cfg['task']['evaluator']['version']='1.0.0'
            with self.assertRaises(ValueError):execute(SessionInput.model_validate(cfg))

    def test_real_sdk_mock_shared_worker_and_receipts(self):
        from tools.research import core
        from tools.research.state import state
        from tools.state_io import atomic_json
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_passive_physical_acceptance import replay_plan
        from tools.research.reporter import _card
        from tools.research.evidence_views import acceptance_certificate
        h,c=prepared_host_v2();plan=replay_plan(c);plan['physical_replay']['passive_ablation']=['tendon_0']
        with patch('tools.research.physical_replay.guard'),patch('tools.research.reporter._wire',side_effect=ValueError('Mock Reporter transport disabled')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='physical_replay')),('research_plan',plan)],limit=2)
        self.assertEqual(len(state(h).get('physical_replays',[])),1)
        ref=state(h)['physical_replays'][0];result=h.store.artifact(ref)
        self.assertEqual(result['acceptance']['status'],'accepted',result)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        self.assertEqual(set(result['passive_l2']['arms']),{'baseline','ablation'})
        for arm in result['passive_l2']['arms'].values():
            receipt=h.store.artifact(arm['receipt_reference']);self.assertTrue(receipt['parent_boundary']['termination_confirmed'])
            self.assertEqual(receipt['raw_reference'],arm['raw_reference'])
        schema=next(t['function']['parameters'] for t in wires[1]['tools'] if t['function']['name']=='research_plan')
        self.assertIn('passive_ablation',schema['$defs']['PhysicalReplayRequest']['properties'])
        self.assertNotIn('state_vector',json.dumps(schema));self.assertNotIn('efc_J',json.dumps(wires))
        card=plain(_card(h,ref));self.assertTrue(any(f['name']=='passive_program' for f in card['recorded_context']))
        cert=acceptance_certificate(h,ref);self.assertTrue(cert['complete_acceptance_view'],cert)
        from tools.research.scientific_intent import scientific_actions
        actions={r['scientific_goal']:r for r in scientific_actions(state(h)['spec'])}
        self.assertFalse(actions['control_feasibility']['available']);self.assertTrue(actions['mechanism_research']['available'])
        self.assertTrue(result['profile']['passive_program']['phase_measurements'])
        from tests.research.test_p63r3_closure import selection
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_ADDITIONAL_PHYSICS')),patch('tools.research.reporter._wire',side_effect=ValueError('Mock Reporter transport disabled')):
            wires+=run_fixture(h,[('evidence_read',dict(reference=ref,view='acceptance_certificate')),
                ('research_route',dict(tool='research_plan',action='select')),('research_plan',selection(c,ref))],id_offset=2)
        self.assertEqual(state(h)['selected'],ref);self.assertEqual(state(h)['research_status'],'stopped')
        atomic_json(ROOT/'runs/u3_tests/wire_validation.json',dict(study=h.run_id,store=str(h.store.root),result=ref,certificate=cert,
            reporter_card=card,wire=wires,provider='SDK Mock HTTP only; no external Provider'))

    def test_interrupted_pair_recovers_durable_lower_bounds_without_relaunch(self):
        import mujoco
        from types import SimpleNamespace
        from tools.research import core
        from tools.research.state import state
        from tools.state_io import read,atomic_json
        from tools.research.physical_replay import calculate
        from tests.research.test_passive_physical_acceptance import replay_plan
        h,c=prepared_host_v2();plan=replay_plan(c);plan['physical_replay']['passive_ablation']=['tendon_0']
        engine_step=mujoco.mj_step;attempts=0
        def kill(model,data):
            nonlocal attempts
            attempts+=1
            if attempts==507:raise KeyboardInterrupt('ENGINEERING_HARD_INTERRUPTION_AFTER_BASELINE')
            engine_step(model,data)
        def worker(command,log,timeout):
            path=Path(command[-1])
            try:
                with patch.object(mujoco,'mj_step',kill):calculate(read(path),path.parent)
            except KeyboardInterrupt:pass
            return SimpleNamespace(returncode=1)
        with patch.object(core,'guard'),patch('tools.research.physical_replay.guard'),patch('tools.service_execution._run_contained',worker):
            result=core.dispatch(h,plan,'u3-interruption')['result']
        raw=h.store.artifact(result['raw_reference'])
        self.assertIsNone(result['acceptance']['accepted']);self.assertEqual(result['acceptance']['status'],'incomplete')
        self.assertTrue(raw['unobserved_work_possible']);self.assertEqual(raw['cost']['physics_steps'],500)
        self.assertTrue(result['passive_l2']['unsealed_traces']);self.assertIsNone(state(h)['pending'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        with patch.object(core,'guard'),patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_RELAUNCH')):
            core.dispatch(h,plan,'u3-interruption')
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        atomic_json(ROOT/'runs/u3_tests/interruption_validation.json',dict(study=h.run_id,result=result['reference'],
            injected_actual_completed_steps=506,durable_observed_lower_bound=raw['cost']['physics_steps'],unobserved_work_possible=True,
            pending=state(h)['pending'],reserved_backend_solves=2,no_relaunch=True))

    def test_bad_unloaded_state_and_wrong_state_reference(self):
        cfg=deepcopy(self.cfg);cfg['task']['initializer']['parameters']['data']['qvel_rad_s'][self.raw['coordinate_order'][0]]=1.
        inp=SessionInput.model_validate(cfg);b=execute_pair(inp,ROOT/'runs/u3_tests'/uuid4().hex,[self.raw['tendon_order'][0]])
        self.assertEqual(b.data.data['paired_ablation']['status'],'not_executed_baseline_invalid')
        self.assertEqual(b.data.data['cost']['model_builds'],1);self.assertEqual(inspect_evidence(inp.task,b.data.data)[0],'invalid')
        from tools.research.physical_replay import passive_source
        with self.assertRaisesRegex(ValueError,'EXACT_GRANTED'):passive_source(self.cfg,plain(self.ref),dict(passive_ablation=['wrong_tendon']))

    def test_existing_dynamic_mechanism_uses_same_v2_pair_executor(self):
        from tools.research.structure_research import calculate
        from tools.research.contracts import AnalysisRequest,MechanismStudy
        from tools.state_io import atomic_json
        study=MechanismStudy(operation='inspect',target=dict(quantity='finite_time_task_violation',goal='decrease'),
            point_semantics='frozen_task_initial_state',effect_semantics='finite_time_task_response',max_evaluations=1,passive_ablation=['tendon_0'])
        query=AnalysisRequest(candidate=self.ref,operation='mechanism_structure_v1',mechanism_study=study,operating_point='standardized_initial_pretension',model_source='mujoco',
            protocol=resolve(ROOT/'configs/research/study_passive_engineering_v1.json')['analysis_protocol'])
        folder=ROOT/'runs/u3_tests'/uuid4().hex;folder.mkdir(parents=True)
        def checkpoint(name,value):atomic_json(folder/(name+'.json'),value)
        checkpoint.directory=folder
        result=calculate(self.cfg,dict(candidate=plain(self.ref)),query,dict(actual_time_s=0.),dict(selected_parameters=[],evaluations=1),checkpoint=checkpoint)
        self.assertEqual(result['status'],'computed',result.get('reason'))
        execution=result['structure_research']['records'][0]['mechanics']['dynamic_execution']
        self.assertEqual(execution['cost']['physics_steps'],1000);self.assertEqual(execution['model_builds'],2)

    def test_saved_state_reference_reaches_original_worker(self):
        from tools.research.physical_replay import dispatch,resolve_passive_state
        from tools.research.contracts import PhysicalReplayRequest
        from tools.research.state import state
        h,c=prepared_host_v2(failure=True)
        with patch('tools.research.physical_replay.guard'):
            first=dispatch(h,PhysicalReplayRequest(candidate=c),'saved-state-source')
            second=dispatch(h,PhysicalReplayRequest(candidate=c,initial_state_result=first['reference'],initial_state_episode='lateral'),'saved-state-target')
        raw=h.store.artifact(second['raw_reference'])
        self.assertEqual(second['acceptance']['status'],'valid_failure',second['acceptance'])
        self.assertEqual(raw['cost']['integration_state_restores'],1)
        self.assertEqual(raw['initial_state_result'],first['reference'])
        source_raw=h.store.artifact(first['raw_reference'])
        self.assertEqual(raw['episodes'][0]['engine_origin_s'],source_raw['episodes'][0]['qualified_state']['time_s'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        cfg=h.store.artifact(c)['configuration']
        with self.assertRaisesRegex(ValueError,'CURRENT_OWNED'):
            resolve_passive_state(h.store,h.run_id,c,cfg,dict(initial_state_result=plain(self.ref),initial_state_episode='lateral'))


if __name__=='__main__':unittest.main()
