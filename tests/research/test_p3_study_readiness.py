"""Synthetic contract fixtures only: no Provider, integration or historical Replay."""
from copy import deepcopy
import json, subprocess, tempfile, unittest
import csv,hashlib
from unittest.mock import patch
from types import SimpleNamespace
from uuid import uuid4
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from schemas.platform import TaskDefinition
from tools.state_io import digest
from tools.platform_store import plain
from extensions.reference.contracts import PassiveResponseGoalV2,PassiveResponseEvaluationV2
from extensions.reference.passive_program import force_at,qualification,confirmation_task
from extensions.reference.passive_evaluation_v2 import inspect,stiffness,metrics,confirmation
from extensions.tendon_family.passive_execution import paired_raw,baseline_arm
from extensions.tendon_family.family_space import parse_space,resolved_request,parameter_capabilities
from extensions.tendon_family.generated_serial import generate_family
from tools.research.config import resolve
from tools.research.agent import plan_schema
from tools.research.experience import freeze_knowledge
ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1.json'
DOC=ROOT/'docs/research/p3-autonomous-study-readiness-20261109'
def read(p):return json.loads((ROOT/p).read_bytes())
@contextmanager
def fixture_directory():
    # Default inherited workspace ACL; retain ignored fixtures for audit.
    path=ROOT/'runs'/('p3-contract-fixture-'+uuid4().hex);path.mkdir()
    yield path
def small_task():
    v=read('tasks/passive_progressive_stiffness_dev_v1.json')['task']
    v['timing'].update(duration_s=.01,sample_period_s=.0005,control_period_s=.0005)
    v['sampling']['window_s']=[0.,.01]
    for stages in v['goal']['data']['programs'].values():
        for i,s in enumerate(stages):
            start=i*.002;end=(i+1)*.002
            s.update(start_s=start,end_s=end,ramp_until_s=start+.00025,observation_window_s=[start,end],scoring_window_s=[end-.001,end])
    for i,q in enumerate(v['goal']['data']['qualifications']):q['window_s']=[(i+1)*.002-.001,(i+1)*.002]
    return TaskDefinition.model_validate(v)
def fixture(task,ablation=False):
    """Invented static arrays for admission boundary tests; not scientific evidence."""
    goal=PassiveResponseGoalV2.model_validate(task.goal.data);dt=task.timing.timestep_s;n=2;nt=2
    binding=dict(task_identity=digest(plain(task)),design_identity='d'*64,model_identity=digest(dict(dt=dt)))
    qp=(goal.initial_perturbation_rad*np.sin(np.arange(n))).tolist()
    def state(t):
        s=dict(version='passive_integration_state_v2',physical_binding=binding,mujoco_version='fixture',state_spec=1,time_s=t,qpos_rad=qp,qvel_rad_s=[0.,0.],state_vector=[t,*qp,0.,0.])
        return dict(s,state_identity=digest(s))
    episodes=[];steps=round(task.timing.duration_s/dt);nm=len(task.physical_problem['monitor_s'])
    for case in goal.load_conditions:
        stages=goal.programs[case];values=dict(unloaded=0.,low=.007,middle=.014,high=.0175,recovery=0.)
        direction=1 if case=='plus_x' else -1
        rows=[]
        for tick in range(steps+1):
            t=tick*dt;force,phase=force_at(goal,case,t);high=phase=='high';off=ablation and t>stages[0].end_s+1e-10
            tension=[.1,.1] if high else [0.,0.];gap=[0.,0.] if high else [-.001,-.001]
            states=[[1],[1]] if high else [[],[]];resids=[[0.],[0.]] if high else [[],[]]
            if off:tension=[0.,0.];states=[[],[]];resids=[[],[]]
            label='disabled' if off else 'taut' if high else 'slack'
            positions=[[direction*values[phase],0.,.5]]*nm
            rows.append(dict(time_s=t,engine_time_s=t,qpos_rad=qp,qvel_rad_s=[0.,0.],tip_m=positions[-1],tip_velocity_m_s=[0.,0.,0.],material_positions_m=positions,material_velocities_m_s=[[0.,0.,0.]]*nm,tendon_length_m=[1.+g for g in gap],length_residual_m=gap,actual_tension_n=tension,force_world_n=force,phase=phase,ncon=0,nefc=sum(map(len,states)),solver_iterations=1,warnings=[],constraint_states=states,constraint_residuals_m=resids,constraint_active=[bool(s) for s in states],constraint_classification=[label]*nt,static_balance_inf_nm=0.,force_map_error_nm=0.,constraint_direction_error=0.))
        samples=[r for i,r in enumerate(rows) if i%round(task.timing.sample_period_s/dt)==0]
        dense=[r for r in rows if any(q.window_s[0]-1e-10<=r['time_s']<=q.window_s[1]+1e-10 for q in goal.qualifications)]
        boundaries=[dict(stage=s.name,time_s=s.end_s,integration_state=state(s.end_s)) for s in stages]
        e=dict(load_condition=case,complete=True,samples=samples,qualification_samples=dense,physics_steps=steps,checked_physics_steps=steps,integration_initial=state(0.),engine_origin_s=0.,state_resets=1,phase_boundaries=boundaries,qualified_state=boundaries[0]['integration_state'],qualifications={q.stage:qualification(dense,q,disabled_limits=(0,1) if ablation and q.stage!='unloaded' else ()) for q in goal.qualifications},maximum_constraint_direction_error=0.,maximum_force_map_error_nm=0.,maximum_capacity_ratio=.1,minimum_constraint_multiplier_n=0.,maximum_enabled_length_excess_m=0.,maximum_contacts=0,stage_extrema={s.name:dict(physics_steps=sum(r['phase']==s.name for r in rows[1:])) for s in stages},route_geometry=dict(sampling='every_physics_step',checked_poses=steps+1,status='legal_at_checked_poses'))
        if ablation:e['intervention_at_s']=stages[0].end_s
        episodes.append(e)
    return dict(kind='passive_dynamic_execution_v2',status='completed',physical_binding=binding,active_actuators=0,joint_count=n,coordinate_order=['a','b'],tendon_order=['tendon_0','tendon_1'],mujoco_version='fixture',payout_lengths_m=[1.,1.],initial_state_source='fresh_unloaded_hard_equilibrium',unloaded_equilibrium=dict(status='qualified_local_minimum',equilibrium=dict(kkt_pass=True,second_order_sufficient=True,capacity=True,qpos=[0.,0.]),solver_settings=goal.unloaded_static_solver),episodes=episodes,intervention=dict(kind='disable_selected_passive_limits' if ablation else 'none',tendons=['tendon_0','tendon_1'] if ablation else [],only_limit_array_changed=True),physics_steps=steps*2,trace_files=[dict(path=case+'.csv',physics_steps=steps,bytes=100,sha256='e'*64,load_condition=case) for case in goal.load_conditions],base_model_signature='f'*64,numerical_invariant_model_signature='c'*64,solver_options=dict(timestep_s=dt),cost=dict(physics_steps=steps*2),timings_s=dict(total=0.),model_builds=1)

class P3ReadinessTests(unittest.TestCase):
    def test_protocol_translation_and_unlimited_budget(self):
        p=read('configs/research/passive_progressive_stiffness_dev_v1.json');s=resolve(SPEC);t=s['canonical_task'];g=t['goal']['data'];ev=t['evaluator']['parameters']['data']
        self.assertEqual(t['status'],'development_valid');self.assertEqual(g['protocol_source']['artifact_id'],digest(p))
        self.assertEqual(g['force_sampling'],'interval_end');self.assertEqual(g['execution_protocol'],'hard_equilibrium_continuous_v1')
        self.assertEqual(t['timing']['duration_s'],20.);self.assertEqual(t['timing']['timestep_s'],p['timestep_s'])
        self.assertEqual(list(g['programs']),list(p['directions']));self.assertEqual(ev['numerical_confirmation']['max_displacement_difference_m'],.001)
        for name,d in p['directions'].items():
            self.assertEqual([x['force_end_world_n'] for x in g['programs'][name]],[[x['force_n']*v for v in d] for x in p['stages']])
        b=s['budgets'];self.assertEqual((b['provider_requests'],b['protected_provider_requests']),(80,8))
        for k in ('public_operations','physical_launches','mathematical_evaluations','activity_s','numerical_s','local_solve_s'):self.assertIsNone(b[k])
        self.assertIsNone(s['physical_replay_limit']);self.assertIsNone(s['analysis_cap_s']);self.assertNotIn('provider_request_extension_policy',s)
        self.assertEqual(s['research_decisions']['history'],[]);self.assertFalse(s['knowledge']['allow_benchmark_answers'])

    def test_relative_payout_compiles_every_topology_and_length_gate(self):
        f=read('configs/research/family_space_p3_passive_v2.json')
        for n,t in ((2,2),(3,3),(6,4)):
            r=dict(version='serial_family_generation_v2',family_space_identity=digest(f),segment_count=n,tendon_count=t,segments={str(i):dict(length_m=.025) for i in range(n)},payout_offsets_m={'tendon_'+str(i):.001 for i in range(t)})
            design,mesh,physics=generate_family(dict(space=f,request=r))
            self.assertEqual(len(design['fixed_payout_lengths_m']),t)
            self.assertTrue(np.allclose(list(design['fixed_payout_lengths_m'].values()),np.asarray(physics['reference_lengths_m'])+.001,rtol=0,atol=1e-14))
            paths={p['parameter_id']:p for p in parameter_capabilities(f,r)}
            self.assertTrue(paths['payout_offsets_m.tendon_'+str(t-1)]['continuous_perturbation'])
            self.assertFalse(paths['segments.0.physical_parameters.curvature_y_rad_m']['continuous_perturbation'])
        r['segments']={str(i):dict(length_m=.14) for i in range(6)}
        with self.assertRaisesRegex(ValueError,'FULL_UNDEFORMED_ASSEMBLY_LENGTH'):generate_family(dict(space=f,request=r))
        r['payout_lengths_m']={'tendon_0':.1}
        with self.assertRaisesRegex(ValueError,'PAYOUT_PARAMETERIZATION'):generate_family(dict(space=f,request=r))

    def test_hard_common_initial_state_phase_and_same_tendon(self):
        t=small_task();r=fixture(t);self.assertEqual(inspect(t,r),('valid',None))
        broken=deepcopy(r);broken['episodes'][1]['integration_initial']['qvel_rad_s'][0]=1.
        self.assertEqual(inspect(t,broken)[0],'invalid')
        broken=deepcopy(r);broken['episodes'][0]['state_resets']=2
        self.assertEqual(inspect(t,broken)[0],'invalid')
        broken=deepcopy(r);broken['episodes'][0]['phase_boundaries'].pop()
        self.assertEqual(inspect(t,broken)[0],'incomplete')
        spec=PassiveResponseEvaluationV2.model_validate(t.evaluator.parameters.data).progressive_stiffness[0]
        value=stiffness(t,r,spec);self.assertTrue(value['slack_to_taut']);self.assertAlmostEqual(value['stiffness_ratio'],4.)
        broken=deepcopy(r)
        for row in broken['episodes'][0]['qualification_samples']:
            if row['phase']=='low':row['actual_tension_n'][0]=.1
            if row['phase']=='high':row['actual_tension_n'][1]=0.
        self.assertFalse(stiffness(t,broken,spec)['slack_to_taut'])

    def test_paired_and_complete_independent_confirmation_admission(self):
        t=small_task();pair=paired_raw(fixture(t),fixture(t,True),Path('independent'),['tendon_0','tendon_1'],0.)
        # Synthetic ablation displacement equals baseline; mechanism fails as expected,
        # but the immutable pairing/initialization gate must remain valid.
        value=metrics(t,pair,check_confirmation=False);self.assertEqual(value['validity'],'valid');self.assertFalse(value['task_success'])
        self.assertEqual(metrics(t,pair)['reason'],'INDEPENDENT_NUMERICAL_CONFIRMATION_REQUIRED')
        c=dict(version='passive_numerical_confirmation_v1',source_result=dict(artifact_id='a'*64),source_execution_id='source',independent_execution_id='independent',source_raw_identity='b'*64,source_binding=pair['physical_binding'],source_displacements_m={s.load_condition:stiffness(t,baseline_arm(pair),s)['displacement_m'] for s in PassiveResponseEvaluationV2.model_validate(t.evaluator.parameters.data).progressive_stiffness},executions={},saved_state_replay={})
        for v in ('half_timestep','initial_perturbation'):
            effective=confirmation_task(t,v);raw=fixture(effective);c['executions'][v]=dict(raw=raw,raw_identity=digest(raw),task=plain(effective),execution_id=v)
        pair['numerical_confirmation']=c
        arms=dict(baseline=baseline_arm(pair),ablation=pair['paired_ablation']['ablation'],**{v:c['executions'][v]['raw'] for v in c['executions']})
        for name,raw in arms.items():c['saved_state_replay'][name]=dict(status='verified',integrations=0,raw_identity=digest(raw),traces=raw['trace_files'],rows_checked=raw['physics_steps'],route_checked_poses=raw['physics_steps'],maximum_position_difference_m=0.)
        self.assertEqual(confirmation(t,pair),('valid',None))
        broken=deepcopy(pair);broken['numerical_confirmation']['source_displacements_m']['plus_x'][0]+=.00101
        self.assertEqual(confirmation(t,broken)[1],'CROSS_EXECUTION_DISPLACEMENT_DIFFERENCE')
        broken=deepcopy(pair);broken['numerical_confirmation']['executions'].pop('half_timestep')
        self.assertEqual(confirmation(t,broken)[0],'incomplete')
        broken=deepcopy(pair);broken['numerical_confirmation']['source_execution_id']='independent'
        self.assertEqual(confirmation(t,broken)[0],'invalid')
        broken=deepcopy(pair);broken['paired_ablation']['ablation']['episodes'][0]['qualified_state']['qpos_rad'][0]=.2
        self.assertEqual(metrics(t,broken,check_confirmation=False)['validity'],'invalid')

    def test_safe_manifest_references_and_main_schema(self):
        s=resolve(SPEC);manifest=s['knowledge_manifest'];keys={r['entry_id']+'@'+r['revision'] for r in manifest['entries']}
        new=read('docs/research/p3-autonomous-study-readiness-20261109/knowledge-revisions.json')['added'];content=read('memory/knowledge/research_organized_v2.json')['entries']
        original=json.loads(subprocess.check_output(['git','show','8f5a1e7619134d1218f277629f7dce974cfc3f77:memory/knowledge/research_organized_v2.json'],cwd=ROOT))['entries']
        for key,v in original.items():self.assertEqual(content[key],v)
        canonical={v['entry_id']+'@'+str(v['revision']):v for v in content.values()}
        for key in new:
            self.assertIn(key,keys);entry=content[key]
            for field in ('source_refs','evidence_level','applicability','confidence','limitations','related_skills','knowledge_refs'):self.assertIn(field,entry)
            self.assertNotIn('decision_ownership',entry)
            for ref in entry['source_refs']+entry['related_skills']+entry['knowledge_refs']:
                root,*suffix=ref.split(':');self.assertIn(root,keys)
                if suffix:
                    node=canonical[root]
                    for part in suffix[0].split('.'):node=node[part]
        case=content['p3-case@3'];self.assertEqual(len(case['action_trace']),8)
        body=json.dumps(case);self.assertNotIn('platform.sqlite',body);self.assertNotIn('candidate_id',body);self.assertNotIn('fixed_payout_lengths_m',body)
        self.assertTrue(all(not r.get('benchmark_sensitive') for r in manifest['entries']))
        self.assertTrue(all(len(r['content_sha256'])==64 for r in manifest['entries']))
        schema=plan_schema(s['allowed_plan_actions'],decision_required=True,study=s)
        defs=schema['$defs'];self.assertIn('validation_source',defs['PhysicalReplayRequest']['properties'])
        self.assertIn('payout_offsets_m',defs['GenerationRequestV2']['properties'])
        self.assertTrue(s['family_search']['coupled_block_enabled']);self.assertIn('payout',s['family_search']['variable_groups'])
        self.assertIn('mechanism_structure_v1',s['mathematical_methods'])

    def test_confirmation_composition_preserves_signed_arms_and_actual_costs(self):
        from extensions.tendon_family.passive_execution import execute_confirmation
        t=small_task();source=paired_raw(fixture(t),fixture(t,True),Path('source'),['tendon_0','tendon_1'],0.)
        class Input:
            task=t
            def model_copy(self,update):return SimpleNamespace(**update)
        def backend(inp,raw):return SimpleNamespace(data=SimpleNamespace(data=raw))
        def replay(inp,raw,folder):return dict(status='verified',integrations=0,raw_identity=digest(raw),traces=raw['trace_files'],rows_checked=raw['physics_steps'],route_checked_poses=raw['physics_steps'],maximum_position_difference_m=0.,cost=dict(native_forward_calls=3))
        with fixture_directory() as directory,patch('extensions.tendon_family.passive_execution.execute_pair',return_value=backend(None,deepcopy(source))),patch('extensions.tendon_family.passive_execution.execute',side_effect=lambda inp,*a,**k:backend(inp,fixture(inp.task))),patch('extensions.tendon_family.passive_execution.replay_saved_traces',side_effect=replay),patch('extensions.tendon_family.passive_execution.backend_result',side_effect=backend):
            raw=execute_confirmation(Input(),Path(directory)/'fresh',source,dict(artifact_id='a'*64),'source').data.data
        self.assertEqual(confirmation(t,raw),('valid',None))
        self.assertEqual(metrics(t,raw)['validity'],'valid')
        self.assertEqual(len(raw['trace_files']),8)
        self.assertEqual(raw['cost']['native_forward_calls'],12)
        self.assertEqual(raw['cost']['physics_steps'],fixture(t)['physics_steps']*5)

    def test_new_store_is_empty_and_separate(self):
        from tools.research.core import prepare
        from tools.research.state import state
        spec=resolve(SPEC);spec['study_id']='offline-p3-readiness-'+uuid4().hex
        spec['configuration']['run_id']=spec['study_id'];spec.pop('resolved_identity');spec['resolved_identity']=digest(spec)
        with fixture_directory() as directory,patch('tools.research.config.resolve',return_value=spec):
            host=prepare(SPEC,directory=directory);s=state(host)
            for field in ('candidates','plans','results','physical_replays','analysis_results','search_results'):
                self.assertFalse(s[field])
            remaining=host.store.remaining()['remaining']
            self.assertEqual(remaining['model_calls'],80);self.assertIsNone(remaining['backend_solves']);self.assertIsNone(remaining['tool_calls'])
            self.assertEqual(s['numerical_s'],0.);self.assertNotIn('freeze',s)
            from tools.research.experience import retrieve
            self.assertEqual(retrieve(host,dict(operation='read',entry_id='p3-case',revision='3'))['results'][0]['content']['entry_id'],'p3-case')
            from tools.research.design import generate_candidate,verify_candidate
            from tools.research.structure_research import parameters,prepare_context,finite_time_discovery
            from tools.research.contracts import MechanismStudy
            from tools.research.scientific_intent import parameter_catalog
            generated=generate_candidate(host,dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=2,segments={'0':dict(length_m=.025),'1':dict(length_m=.025)},payout_offsets_m=dict(tendon_0=.001,tendon_1=.001)),dict(origin='synthetic_offline_admission_fixture'))
            candidate=verify_candidate(host,generated['candidate']);rows=parameters(spec,candidate)
            self.assertTrue(all(r['study_authorized'] for r in rows if '*' not in r['parameter_id']))
            catalog=parameter_catalog(spec,candidate)
            self.assertTrue(next(r for r in catalog if r['parameter_id']=='payout_offsets_m.tendon_1')['selectable'])
            self.assertTrue(finite_time_discovery(candidate['configuration'])['paired_required'])
            common=dict(operation='interact',parameter_paths=['segments.0.length_m','payout_offsets_m.tendon_0'],max_evaluations=4)
            for effect,point,target,extra in (
                ('mechanism_effect','re_equilibrated',dict(quantity='tangent_compliance',reduction='norm'),dict(load_condition='plus_x')),
                ('finite_time_task_response','frozen_task_initial_state',dict(quantity='finite_time_task_violation',goal='decrease'),dict(passive_ablation=['tendon_0']))):
                q=MechanismStudy(**common,effect_semantics=effect,point_semantics=point,target=target,**extra)
                self.assertEqual(prepare_context(spec,candidate,q,[])['minimum_evaluations'],4)

    def test_saved_csv_checks_all_steps_and_reconstructs_states_without_integration(self):
        from extensions.tendon_family.passive_execution import replay_saved_traces
        t=small_task();g=PassiveResponseGoalV2.model_validate(t.goal.data)
        model=SimpleNamespace(nq=2,nv=2,ntendon=2)
        native=SimpleNamespace(model=model,payout=np.ones(2),physics=dict(tendons=[dict(force_limit_n=1.)]*2),
            points=['tip'],cost=dict(material_point_jacobian_calls=0),load=lambda name:SimpleNamespace(name=name),
            point=lambda data,b:(np.zeros(3),np.zeros((3,2)),0))
        inp=SimpleNamespace(task=t,robot=SimpleNamespace(structure=SimpleNamespace(data=dict(components=[]))))
        with fixture_directory() as directory:
            path=directory/'episode.csv'
            headers=['time_s','stage','engine_time_s','force_x_n','force_y_n','force_z_n']+[p+'_'+str(i) for p in ('qpos','qvel','length_m','tension_n','length_residual_m') for i in range(2)]+['contacts','warnings','constraint_direction_error_m_rad','force_map_error_nm']
            def write(force=0.):
                with path.open('w',newline='') as stream:
                    writer=csv.writer(stream);writer.writerow(headers)
                    for tick in (1,2):writer.writerow([tick*t.timing.timestep_s,'unloaded',tick*t.timing.timestep_s,force,0.,0.,0.,0.,0.,0.,.999,.999,0.,0.,-.001,-.001,0,0,0.,0.])
                body=path.read_bytes();return dict(path=path.name,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),physics_steps=2)
            raw=dict(trace_files=[write()],episodes=[dict(load_condition='plus_x',samples=[dict(time_s=2*t.timing.timestep_s,qpos_rad=[0.,0.],qvel_rad_s=[0.,0.],material_positions_m=[],tip_m=[0.,0.,0.])],qualification_samples=[])],intervention=dict(tendons=[]),tendon_order=['tendon_0','tendon_1'],physics_steps=2)
            data=SimpleNamespace(qpos=np.zeros(2),qvel=np.zeros(2))
            with patch('extensions.tendon_family.passive_execution.task_definition',return_value=(g,None,{})),patch('extensions.tendon_family.passive_execution.physics_for',return_value={}),patch('extensions.tendon_family.passive_execution.assemble_physical',return_value={}),patch('extensions.tendon_family.passive_execution.PassiveModel',return_value=native),patch('mujoco.MjData',return_value=data),patch('mujoco.mj_resetData'),patch('mujoco.mj_forward'),patch('extensions.tendon_family.route_validation.validate_routes',return_value=dict(issues=[],segment_body_checks=1)),patch('mujoco.mj_step',side_effect=AssertionError('Replay must not integrate')):
                result=replay_saved_traces(inp,raw,directory)
                self.assertEqual((result['rows_checked'],result['route_checked_poses'],result['integrations']),(2,2,0))
                raw['trace_files']=[write(force=.01)]
                with self.assertRaisesRegex(ValueError,'STEP_CHECK'):replay_saved_traces(inp,raw,directory)

if __name__=='__main__':unittest.main()
