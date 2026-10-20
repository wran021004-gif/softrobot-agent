"""Real compilation and Store fixtures; no model requests or scientific rollout."""
from copy import deepcopy
from pathlib import Path
import gc, shutil, unittest
from uuid import uuid4
from unittest.mock import patch
import numpy as np
from schemas.platform import ProjectConfig
from tools.research import core, design
from tools.research.config import ROOT, resolve
from tools.research.state import state, update, save
from tools.research.contracts import ControlSeedRequest
from tools.research.research_context import import_history, context
from tools.research.physical_replay import seed_control, binding, model_context
from extensions.tendon_family.family_space import parameter_capabilities
from extensions.tendon_family.generated_serial import generate_family
from tools.platform_store import plain
from tools.state_io import digest, read


class S7IntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'runs'/('s7-fixture-'+uuid4().hex)
        def cleanup():
            gc.collect()
            if cls.directory.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            if cls.directory.exists():shutil.rmtree(cls.directory)
        cls.addClassCleanup(cleanup)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':cls.directory.name,'grant_id':cls.directory.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            cls.host=core.prepare(ROOT/'configs/research/study_s7_mirror.json',cls.directory)
        import_history(cls.host)
        cls.spec=state(cls.host)['spec']
        cls.entry=state(cls.host)['control_initializations'][0]
        cls.candidate=cls.host.store.artifact(cls.entry['candidate'])

    def test_distinct_tasks_and_identical_agent(self):
        a=self.spec;b=resolve(ROOT/'configs/research/study_s7_variant.json')
        self.assertNotEqual(a['canonical_task_identity'],b['canonical_task_identity'])
        self.assertEqual(a['execution_instructions'],b['execution_instructions'])
        self.assertEqual(a['configuration']['policy']['controller']['parameters']['data']['settling'],
            b['configuration']['policy']['controller']['parameters']['data']['settling'])
        self.assertNotIn('length_servo_gain_n_m',a['allowed_parameters'])

    def test_historical_success_is_only_unmeasured_control(self):
        s=state(self.host);c=context(self.host)
        self.assertEqual(s['research_history'],[]);self.assertIsNone(c['best_valid'])
        self.assertFalse(s.get('success_gate'));self.assertEqual(c['observations'],[])
        self.assertEqual(self.entry['task_acceptance'],'unmeasured')
        schedule=self.host.store.artifact(self.entry['source'])
        self.assertFalse(schedule['provenance']['inherited_acceptance'])
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)
        before=state(self.host);import_history(self.host);self.assertEqual(before,state(self.host))

    def test_conditional_capabilities_and_inactive_servo(self):
        from tools.research.agent import read_tool_evidence
        request=deepcopy(self.candidate['parameters']);request.update(segment_count=1,tendon_count=3,segments={})
        request['spans']=[];request['route_overrides']={}
        rows=parameter_capabilities(self.spec['family_space'],request)
        ids=[r['parameter_id'] for r in rows]
        self.assertFalse(any('segments.1.' in i or 'route_overrides.3' in i for i in ids))
        self.assertTrue(any(i.endswith('density_kg_m3') for i in ids))
        self.assertFalse(next(r for r in rows if r['parameter_id']=='tendon_parameters.length_servo_gain_n_m')['effective_in_current_execution'])
        actual=read_tool_evidence(self.host,dict(reference=self.entry['candidate'],view='capabilities'))
        self.assertTrue(any(r['parameter_id']=='segments.1.physical_parameters.density_kg_m3' for r in actual))
        density=next(r for r in actual if r['parameter_id']=='segments.1.physical_parameters.density_kg_m3')
        self.assertEqual(density['default'],1050.)
        viscosity=next(r for r in actual if r['parameter_id']=='segments.0.physical_parameters.viscosity_y_nm2_s')
        self.assertEqual(viscosity['default'],.0005)
        with self.assertRaisesRegex(ValueError,'WHOLE_CANDIDATE'):
            core.read_evidence(self.host,dict(reference=self.entry['candidate'],pointer='/parameters',view='capabilities'))

    def test_material_edits_affect_compiled_mass_stiffness_and_rest_pose(self):
        cfg=self.candidate['configuration'];_,base_physics,_,base_spec=model_context(cfg)
        base=deepcopy(self.candidate['parameters'])
        for key,value in [('density_kg_m3',1300.),('viscosity_y_nm2_s',.02),('curvature_y_rad_m',.2),('section_angle_rad',.3)]:
            request=deepcopy(base);request['segments']['0']['physical_parameters']={key:value}
            result=design.generate_candidate(self.host,request,dict(origin='offline_fixture'))
            self.assertEqual(result['status'],'generated',result)
            new=self.host.store.artifact(result['candidate'])
            _,physics,_,spec=model_context(new['configuration'])
            self.assertNotEqual(base_physics['identity'],physics['identity'])
            self.assertNotEqual(base_spec['identity'],spec['identity'])
            if key=='density_kg_m3':
                self.assertNotEqual(base_spec['links'][0]['mass'],spec['links'][0]['mass'])
            if key.startswith('curvature'):
                self.assertNotEqual(base_spec['links'][0]['natural'],spec['links'][0]['natural'])

    def test_reject_outside_domain_and_unknown_physics(self):
        for edits in [dict(density_kg_m3=-1),dict(density_kg_m3=2600),dict(fake=1)]:
            request=deepcopy(self.candidate['parameters']);request['segments']['0']['physical_parameters']=edits
            result=design.generate_candidate(self.host,request,dict(origin='offline_fixture'))
            self.assertEqual(result['status'],'invalid');self.assertIsNone(result['candidate'])

    def test_new_topology_uses_pretension_and_explicit_mapping_only(self):
        request=deepcopy(self.candidate['parameters']);request.update(tendon_count=3,spans=[],route_overrides={})
        request['tendon_parameters']['pretension_n']=.5
        result=design.generate_candidate(self.host,request,dict(origin='offline_fixture'))
        self.assertEqual(result['status'],'generated',result)
        new=result['candidate'];cfg=self.host.store.artifact(new)['configuration']
        seeded=seed_control(self.host,ControlSeedRequest(candidate=new,source=self.entry['source'],parent=self.entry['candidate']))
        source=self.host.store.artifact(seeded['source']);binding(cfg,source['trajectory'])
        np.testing.assert_array_equal(source['trajectory']['tensions_n'],np.full((35,3),.5))
        with self.assertRaises(ValueError):
            seed_control(self.host,ControlSeedRequest(candidate=new,tensions_n=[[9,0,0]]))
        old=self.host.store.artifact(self.entry['source'])['trajectory']
        mapped=seed_control(self.host,ControlSeedRequest(candidate=new,source=self.entry['source'],parent=self.entry['candidate'],
            channel_map={source['trajectory']['tendon_order'][0]:old['tendon_order'][1]}))
        np.testing.assert_array_equal(np.asarray(self.host.store.artifact(mapped['source'])['trajectory']['tensions_n'])[:,0],np.asarray(old['tensions_n'])[:,1])

    def test_query_views_and_exact_retrieval(self):
        from tools.research.agent import read_tool_evidence
        ref=save(self.host,dict(samples=list(range(150)),nested=dict(trajectory=list(range(1000)))),'offline_fixture')
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref,pointer='/samples',view='range',start=98,count=3))['items'],[98,99,100])
        preview=core.read_evidence(self.host,dict(reference=ref,view='summary'))
        self.assertEqual(preview['value']['nested']['trajectory']['read_pointer'],'/nested/trajectory')
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref,view='fields',fields=['samples']))['samples'],list(range(150)))
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref,pointer='/nested/trajectory',view='full')),list(range(1000)))
        query=dict(reference=ref,pointer='/nested/trajectory',view='full');before=deepcopy(query)
        self.assertEqual(read_tool_evidence(self.host,query),list(range(1000)))
        self.assertEqual(query,before)
        self.assertEqual(read_tool_evidence(self.host,dict(reference=ref))['view'],'deterministic_summary')

    def test_incomplete_nmpc_remains_invalid_and_does_not_break_context(self):
        from tools.research.evidence_policy import summarize_evidence
        value=dict(status='execution_incomplete',candidate=self.entry['candidate'],acceptance=None,raw_reference=None,
            execution=dict(stage='simulation',status='execution_incomplete'))
        ref=save(self.host,value,'offline_incomplete_execution_fixture');before=state(self.host)['results']
        try:
            update(self.host,results=[*before,ref])
            c=context(self.host)
            self.assertIn(ref,c['all_fresh_results']);self.assertIsNone(c['best_valid'])
            self.assertFalse(c['observations'][-1]['task_gap']['valid_complete'])
            summary=summarize_evidence(value,ref)
            self.assertEqual(summary['verification_status'],'incomplete_or_unbound_execution')
            self.assertNotIn('observed_task_pass',summary['supported_inferences'])
        finally:update(self.host,results=before)

    def test_changed_horizon_and_period_use_explicit_zero_order_hold(self):
        cfg=deepcopy(self.candidate['configuration'])
        cfg['task']['timing'].update(duration_s=.40,control_period_s=.02,sample_period_s=.02)
        cfg['policy']['controller']['parameters']['data']['settling']['window_s']=.04
        with patch('tools.research.physical_replay.verify_candidate',return_value=dict(configuration=cfg)):
            entry=seed_control(self.host,ControlSeedRequest(candidate=self.entry['candidate'],source=self.entry['source'],parent=self.entry['candidate']))
        trajectory=self.host.store.artifact(entry['source'])['trajectory']
        self.assertEqual(np.asarray(trajectory['tensions_n']).shape,(20,4))
        self.assertEqual(trajectory['times_s'][-1],.4)
        original=self.host.store.artifact(self.entry['source'])['trajectory']
        np.testing.assert_array_equal(trajectory['tensions_n'][-1],original['tensions_n'][-1])

    def test_provider_confirmed_response_replays_exactly_without_second_send(self):
        import asyncio, httpx
        from tools.research.agent import LiveBoundary
        provider=self.spec['runtime']['provider'];sends=[]
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='OFFLINE_FIXTURE')])
        def respond(request):
            sends.append(request)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='tool_calls',message=dict(reasoning_content='fixture only'))],usage=dict(prompt_tokens=11,completion_tokens=3)))
        async def exercise():
            boundary=LiveBoundary(self.host,httpx.MockTransport(respond))
            def request(value):return httpx.Request('POST',provider['base_url']+'/chat/completions',json=value)
            before=self.host.store.remaining()['used']['model_calls']
            first=await boundary.handle_async_request(request(wire))
            again=await boundary.handle_async_request(request(wire))
            self.assertEqual(first.content,again.content);self.assertEqual(len(sends),1)
            with self.assertRaisesRegex(ValueError,'MUST_BE_PROCESSED_FIRST'):
                await boundary.handle_async_request(request(dict(wire,messages=[])))
            self.assertEqual(self.host.store.remaining()['used']['model_calls'],before+1)
            boundary.consumed();self.assertFalse(state(self.host)['pilot'].get('unconsumed_response'))
            await boundary.aclose()
        asyncio.run(exercise())

    def test_provider_unknown_send_blocks_retry_and_preserves_charge(self):
        import asyncio,httpx
        from tools.research.agent import LiveBoundary,pending
        directory=self.directory/'unknown-provider-fixture'
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':self.directory.name+'-unknown','grant_id':self.directory.name+'-unknown'})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            host=core.prepare(ROOT/'configs/research/study_s7_mirror.json',directory)
        provider=state(host)['pilot']['provider'];sends=[]
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='OFFLINE_FAILURE_FIXTURE')])
        def fail(request):
            sends.append(request);raise httpx.ReadError('synthetic unknown send outcome')
        async def exercise():
            boundary=LiveBoundary(host,httpx.MockTransport(fail))
            request=lambda:httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)
            with self.assertRaises(httpx.ReadError):await boundary.handle_async_request(request())
            with self.assertRaisesRegex(ValueError,'R3_UNCONFIRMED_ATTEMPT_BLOCKS_SEND'):
                await boundary.handle_async_request(request())
            self.assertEqual(len(sends),1);self.assertEqual(host.store.remaining()['used']['model_calls'],1)
            self.assertEqual(len(pending(host)),1);self.assertFalse(state(host)['pilot'].get('unconsumed_response'))
            await boundary.aclose()
        asyncio.run(exercise())

    def test_controller_patches_are_validated_and_cannot_modify_acceptance(self):
        request=deepcopy(self.candidate['parameters']);request['controller_recipe']=dict(horizon=8,max_iterations=25)
        result=design.generate_candidate(self.host,request,dict(origin='offline_fixture'))
        self.assertEqual(result['status'],'generated',result)
        control=self.host.store.artifact(result['candidate'])['configuration']['policy']['controller']['parameters']['data']
        self.assertEqual(control['recipe']['horizon'],8)
        self.assertEqual(control['settling'],self.candidate['configuration']['policy']['controller']['parameters']['data']['settling'])
        request['controller_recipe']=dict(tolerance_m=.5)
        self.assertEqual(design.generate_candidate(self.host,request,dict(origin='offline_fixture'))['status'],'invalid')


if __name__=='__main__':unittest.main()
