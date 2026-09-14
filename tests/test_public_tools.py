"""Public contracts and actual native-call adapters; no new dynamics/API solves."""
import copy
import json
import math
import time
import unittest
from uuid import uuid4
from unittest.mock import patch, Mock

from schemas.public_tools import PublicResult
from tools.artifact_tools import file_hash
from tools.public_catalog import catalog, entries, native_tools
from tools.public_services import ServiceSession
from tools.public_feedback import normalize
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, read

CALLER=dict(actor_id='contract-test-agent',origin='agent',transport='offline_native_fixture')


class PublicToolTests(unittest.TestCase):
    def session(self, permissions=None, budget=12):
        session=ServiceSession(ROOT/'runs/public_interface_tests'/uuid4().hex)
        session.create(dict(profile_id='independent-no-task',permissions=permissions or ['analysis','read_evidence','derived_artifacts'],tool_calls=budget))
        return session

    def call(self, session, tool_id='analysis.pcc_jacobian', arguments=None, **kwargs):
        return session.invoke(dict(tool_id=tool_id,arguments=arguments or {'length_m':1.25,'bend_rad':[.4,-.2]},
            reason='Test a specific local derivative independently of any task.',evidence=[],**kwargs),caller=CALLER)

    def test_directory_identity_schema_and_actual_native_tools(self):
        from schemas.dynamic_workbench import TOOLS
        from tools.deepseek_adapter import native_tools as old_native
        dynamic=native_tools('dynamics')
        self.assertEqual(set(TOOLS),{t['function']['name'] for t in dynamic})
        registry=entries()
        self.assertNotEqual(registry['workbench.evaluate_candidate']['scope'],registry['dynamics.evaluate_candidate']['scope'])
        for runtime,tools in (('dynamics',dynamic),('workbench',old_native()),('services',native_tools('services'))):
            for tool in tools:
                entry=next(e for e in registry.values() if e['runtime']==runtime and e['wire_name']==tool['function']['name'])
                schema=entry['schema'].model_json_schema()
                for key,value in schema['properties'].items():
                    self.assertEqual(tool['function']['parameters']['properties'][key],value)
                self.assertIn(entry['tool_id'],tool['function']['description'])
        self.assertTrue(all(not e['callable'] for e in catalog()['library']))

    def test_interface_continuation_keeps_numerical_guard(self):
        from tools.design_continuation import compatible
        prior={'tools/pcc_math.py':'fixed-math','tools/workbench.py':'old-interface'}
        request=dict(sources=prior,runtime={'test':'same'})
        current={**prior,'tools/workbench.py':'new-interface','schemas/public_tools.py':'new-contract'}
        self.assertIn('schemas/public_tools.py',compatible(request,current,{'test':'same'}))
        with self.assertRaisesRegex(ValueError,'INCOMPATIBLE_COMPUTATION'):
            compatible(request,{**current,'tools/pcc_math.py':'changed-math'},{'test':'same'})

    def test_native_agent_math_then_read_and_finite_difference(self):
        session=self.session()
        with patch('tools.reach_dynamics.DynamicsBackends.simulate',side_effect=AssertionError('No solve')), \
             patch('tools.deepseek_adapter.request_completion',side_effect=AssertionError('No API')):
            output=session.apply_tool_call(dict(name='analysis__pcc_jacobian',arguments=json.dumps(dict(
                length_m=1.25,bend_rad=[.4,-.2],reason='Local derivative check',evidence=[]))),caller=CALLER)
            PublicResult.model_validate(output)
            self.assertEqual(output['analysis_status'],'LOCAL_GEOMETRY_ONLY')
            self.assertEqual(output['task_status'],'NOT_ASSESSED')
            details=read(session.root/output['details_ref'])
            page=session.apply_tool_call(dict(name='evidence__read_json',arguments=json.dumps(dict(
                evidence_ref=output['details_ref'],pointer='/tip_jacobian_m_per_rad',reason='Read the derivative evidence',evidence=[output['details_ref']]))),caller=CALLER)
        self.assertEqual(read(session.root/page['details_ref'])['content'],details['tip_jacobian_m_per_rad'])
        # Independent finite difference of geometric position, away from straight state.
        def tip(u,v):
            theta=math.hypot(u,v)
            return [1.25*math.sin(theta)/theta,1.25*(1-math.cos(theta))*u/theta**2,1.25*(1-math.cos(theta))*v/theta**2]
        for j in range(2):
            plus=[.4,-.2];minus=plus[:];plus[j]+=1e-6;minus[j]-=1e-6
            for i,(a,b) in enumerate(zip(tip(*plus),tip(*minus))):
                self.assertAlmostEqual((a-b)/2e-6,details['tip_jacobian_m_per_rad'][i][j],places=7)
        self.assertEqual(page['cost']['charged']['model_calls'],0)
        self.assertEqual(read(session.root/'state.json')['used']['tool_calls'],2)
        self.assertNotIn('candidate',json.dumps(read(session.root/'service_config.json')))

    def test_invalid_versions_inputs_identity_and_permission(self):
        session=self.session(permissions=['read_evidence'])
        denied=self.call(session)
        self.assertEqual(denied['error']['category'],'permission')
        self.assertEqual(denied['cost']['charged']['tool_calls'],0)
        session=self.session()
        for args in ({'length_m':'1.25','bend_rad':[0,0]}, {'length_m':1,'bend_rad':[4,0]},
                     {'length_m':1,'bend_rad':[0,0],'caller':CALLER}, {'length_m':float('nan'),'bend_rad':[0,0]}):
            self.assertEqual(self.call(session,arguments=args)['execution_status'],'rejected')
        self.assertEqual(self.call(session,tool_version='2.0.0')['execution_status'],'rejected')
        self.assertEqual(self.call(session,tool_id='evaluate_candidate')['execution_status'],'rejected')
        self.assertEqual(self.call(session,tool_id={'invalid':'identity'})['execution_status'],'rejected')
        malformed=session.apply_tool_call(dict(name='analysis__pcc_jacobian',arguments='{'),caller=CALLER)
        self.assertEqual(malformed['execution_status'],'rejected')
        self.assertEqual(session.load()['used']['tool_calls'],0)

    def test_budget_failure_recovery_and_evidence_tampering(self):
        session=self.session(budget=2)
        with patch('tools.public_services.pcc_jacobian',side_effect=RuntimeError('fixture backend unavailable')):
            failed=self.call(session)
        self.assertEqual(failed['execution_status'],'failed')
        self.assertEqual(failed['error']['category'],'dependency')
        self.assertFalse(failed['error']['retryable'])
        done=self.call(session)
        self.assertEqual(self.call(session)['error']['category'],'budget')
        # Simulate crash before final state commit; a sealed result is recovered without executing again.
        state=session.load();state['calls'][1]['status']='reserved';atomic_json(session.root/'state.json',state)
        with patch('tools.public_services.pcc_jacobian',side_effect=AssertionError('No replay')):
            self.call(session)
        self.assertEqual(session.load()['calls'][1]['status'],'completed')
        self.assertEqual(session.load()['used']['tool_calls'],2)
        (session.root/done['details_ref']).write_text('{}',encoding='utf8')
        bad=self.call(session,tool_id='evidence.read_json',arguments={'evidence_ref':done['details_ref']})
        self.assertEqual(bad['error']['category'],'evidence')

    def test_statuses_never_turn_solver_failure_or_screening_into_task_failure(self):
        for data,solver,analysis,task in (
            ({'complete':False,'computation_status':'failed','reason':'Partial rollout'},'FAILED','NOT_ASSESSED','NOT_ASSESSED'),
            ({'complete':True,'model_task_success':False},'COMPLETED','MODEL_PREDICTS_FAIL','NOT_ASSESSED'),
            ({'complete':True,'canonical_task_success':False},'COMPLETED','NOT_ASSESSED','FAIL'),
            ({'evidence_role':'historical_replay','canonical_task_status':'PASS'},'NOT_APPLICABLE','NOT_ASSESSED','NOT_RUN')):
            out=normalize('dynamics.simulate_candidate',dict(status='completed',data=data),call_id='x',caller=CALLER)
            self.assertEqual((out['execution_status'],out['solver_status'],out['analysis_status'],out['task_status']),('completed',solver,analysis,task))

    def dynamic_fixture(self):
        from tools.dynamic_campaign import DynamicCampaign
        b=DynamicCampaign.__new__(DynamicCampaign)
        b.root=ROOT/'runs/public_interface_tests'/uuid4().hex;b.root.mkdir(parents=True)
        b.tick=time.monotonic();b.backends=Mock()
        grant=read(ROOT/'configs/experiments/round9_grant.json')
        b.state=dict(request=dict(permissions=['analysis','read_evidence','derived_artifacts'],grant=grant),
            candidates=[],attempts=[],decisions=[],model_calls=[],evidence={},working_memory={},verified_diagnoses=[])
        b.ledger=dict(limits=grant['limits'],used={k:0 for k in grant['limits']},entries=[])
        atomic_json(b.root/'fixture.json',dict(role='synthetic input evidence'))
        b.register(b.root/'fixture.json')
        return b

    def test_actual_dynamic_native_response_dispatch_receipt_and_preview(self):
        b=self.dynamic_fixture()
        args=dict(length_m=1.25,bend_rad=[.4,-.2],reason='Inspect the PCC derivative',evidence=['fixture.json'],working_memory={})
        row=dict(index=0,decision_sequence=0)
        response=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[dict(function=dict(name='analyze_pcc',arguments=json.dumps(args)))]))])
        with patch('tools.dynamic_campaign.LEDGER',b.root/'ledger.json'):
            b.apply_model_response(row,response)
        result=read(b.root/row['feedback_ref'])
        self.assertEqual(result['public']['caller']['origin'],'agent')
        self.assertEqual(result['public']['analysis_status'],'LOCAL_GEOMETRY_ONLY')
        self.assertEqual(b.ledger['used']['tool_calls'],1)
        self.assertEqual(b.ledger['used']['matlab_dynamic'],0)
        self.assertIn('public',b.latest_preview())
        self.assertEqual(result['public']['evidence'][1]['sha256'],file_hash(b.root/'fixture.json'))

    def test_dynamic_unknown_name_cannot_escape_attempt_directory(self):
        b=self.dynamic_fixture()
        with patch('tools.dynamic_campaign.LEDGER',b.root/'ledger.json'):
            result,ref=b.submit('../../escaped',{},'Check unknown tool',['fixture.json'])
        self.assertEqual(ref,'attempts/000_unknown_tool/result.json')
        self.assertEqual(result['public']['error']['category'],'permission')
        self.assertEqual(b.ledger['used']['tool_calls'],0)

    def test_bound_gateway_workbench_result_and_reuse(self):
        from tools.workbench import Workbench, owner
        from tools.workbench_worker import work
        from tools.public_gateway import invoke_bound
        root=ROOT/'runs/public_interface_tests'/uuid4().hex
        book=Workbench(root,launcher=lambda root,folder,timeout:work(root,folder))
        book.create(simulations=0)
        request=dict(tool_id='workbench.inspect_task',arguments={},reason='Read the frozen contract',evidence=['request'])
        with owner(root):
            out=invoke_bound(book,request,caller=CALLER)
            second=invoke_bound(book,request,caller=CALLER)
        self.assertEqual(out['execution_status'],'completed')
        self.assertTrue(second['cost']['cache_hit'])
        self.assertEqual(second['cost']['charged'],{'decisions':1})
        self.assertEqual(len(book.state['attempts']),1)

    def test_existing_native_video_both_backends_cache_and_lineage(self):
        source=ROOT/'runs/round9_reach'
        backends=set()
        for manifest in (source/'observations/videos').glob('*/native_video.json'):
            info=read(manifest)
            backends.add(info['parameters']['backend'])
            refs=list(info['source_hashes'])+list(info['artifact_hashes'])+[manifest.relative_to(source).as_posix()]
            session=ServiceSession(ROOT/'runs/public_interface_tests'/uuid4().hex)
            session.create(dict(profile_id='saved-native-cache',permissions=['read_evidence','derived_artifacts'],tool_calls=4),
                source_root=source,evidence_refs=refs)
            with patch('tools.simulation_video._mujoco_frames',side_effect=AssertionError('Must reuse frames')), \
                 patch('tools.simulation_video._encode',side_effect=AssertionError('Must reuse video')), \
                 patch('tools.reach_dynamics.DynamicsBackends.simulate',side_effect=AssertionError('No dynamics')):
                result=self.call(session,tool_id='visualization.render_simulation_video',arguments=info['parameters'])
                again=self.call(session,tool_id='visualization.render_simulation_video',arguments=info['parameters'])
            self.assertEqual(result['execution_status'],'completed',result)
            details=read(session.root/result['details_ref'])
            self.assertTrue(details['cached'])
            self.assertEqual(result['epistemics']['visual_access'],'reference_only')
            self.assertEqual(again['cost']['charged']['backend_solves'],0)
            self.assertEqual(file_hash(session.root/details['video_ref']),info['artifact_hashes'][details['video_ref']])
            self.assertEqual(file_hash(manifest),file_hash(session.root/manifest.relative_to(source)))
            diagnosis=self.call(session,tool_id='diagnostics.saved_trajectory',arguments=dict(
                result_ref=info['parameters']['result_ref'],backend=info['parameters']['backend'],entity='tendon_0'))
            self.assertEqual(diagnosis['execution_status'],'completed',diagnosis)
            self.assertEqual(read(session.root/diagnosis['details_ref'])['backend_solves'],0)
        self.assertEqual(backends,{'matlab','mujoco'})

    def test_independent_saved_times_and_target_without_campaign_defaults(self):
        import gzip
        from tools.dynamic_view import render_candidate
        session=self.session()
        rows=[dict(time_s=3+i*.01,solver_time_s=2.99+i*.01,tip_m=[1,0,.3],qpos_rad=[0],qvel_rad_s=[0],
            command_m=[1],solver_tendon_length_m=[1],solver_actuator_force_n=[0],solver_contact_count=0,centerline_m=[[0,0,0],[1,0,.3]]) for i in range(51)]
        folder=session.root/'saved/specimen_alpha';folder.mkdir(parents=True)
        with gzip.open(folder/'trajectory.json.gz','wt',encoding='utf8') as stream:json.dump(rows,stream)
        shared=dict(model_id='matlab_tdcr_planar_dynamic_v1',mass=[.1],fmax=20,kp=1000,length=1,offsets=[[0,.01]],natural=[0],
            stiffness=[.1],damping=[.1],target=[.7,.1,.2],floor_z=-.3)
        atomic_json(folder/'shared_input.json',shared)
        r=dict(complete=True,backend='matlab',candidate_id='specimen_alpha',result_ref='saved/specimen_alpha/result.json')
        atomic_json(folder/'result.json',r)
        state=session.load()
        for path in folder.iterdir():state['evidence'][path.relative_to(session.root).as_posix()]=dict(sha256=file_hash(path))
        atomic_json(session.root/'state.json',state)
        out=self.call(session,tool_id='diagnostics.saved_trajectory',arguments=dict(result_ref=r['result_ref'],backend='matlab',entity='tendon_0'))
        self.assertEqual(out['execution_status'],'completed',out)
        data=read(session.root/out['details_ref'])
        self.assertEqual(data['interval_s'],[2.99,3.5])
        self.assertEqual(data['queries'][0]['t_start_s'],2.99)
        with patch('tools.reach_dynamics.DynamicsBackends.simulate',side_effect=AssertionError('No simulation')):
            page=render_candidate(session.root,dict(candidate_id='specimen_alpha',design={'total_length_m':1},control={},results={'matlab':r}),'matlab')
        html=page.read_text(encoding='utf8')
        payload=json.loads(html.split('const D=',1)[1].split(';const rows=',1)[0])
        self.assertEqual(payload['target_m'],shared['target'])
        self.assertEqual(payload['time_range_s'],[2.99,3.5])


if __name__=='__main__':unittest.main()
