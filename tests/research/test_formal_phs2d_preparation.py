"""Directed formal-Study regressions. Workers and HTTP are synthetic fixtures."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from tools.research import core,analysis
from tools.research.config import ROOT,resolve
from tools.research.state import state,update,save,require_research_authorization
from tools.research.research_context import context,candidate_workflow,execution_preview,pending_evaluation
from tools.research.budget import decision_budget,capacity,mathematics_fits,protected
from tools.research.design import generate_candidate
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE,PhysicalReplayRequest
from tools.state_io import atomic_json,digest,read
from tools.platform_store import zero
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_stage2_workflow import request
from tests.research.test_research_authorization_preflight import approve
from tests.research.test_passive_physical_acceptance import replay_plan

SPEC=ROOT/'configs/research/study_phs2d_topology_successor_20261106.json'


class FormalPreparationTests(unittest.TestCase):
    def candidate(self,h,i=0):
        return generate_candidate(h,request(h,i,True),dict(origin='Explicit offline regression fixture'))['candidate']

    def test_interleaved_results_use_store_sequence_in_all_views(self):
        with fixture() as h:
            c=self.candidate(h)
            layers=analysis.diagnostic_layers(dict(status='execution_incomplete'))
            def mathematics(status):
                value=deepcopy(layers);value['static_qualification']['status']=status
                return save(h,dict(candidate=c,status='execution_incomplete',operation='mechanism_structure_v1',
                    diagnostic_layers=value),'candidate_analysis_result')
            first=mathematics('unqualified')
            physics=save(h,dict(candidate=c,status='execution_incomplete',physical_launches=10),'physical_playback_result')
            latest=mathematics('passed')
            # Category order and within-category order are deliberately wrong.
            update(h,analysis_results=[latest,first],physical_replays=[physics])
            current=context(h)
            self.assertEqual(current['all_fresh_results'],[first,physics,latest])
            owners=[(r,h.store.artifact(r)) for r in (latest,first,physics)]
            workflow=candidate_workflow(h,current,[c],owners)
            self.assertEqual([v['reference'] for v in workflow['evaluations']],[first,physics,latest])
            self.assertEqual(workflow['candidates'][0]['latest_mathematics'],latest)
            preview=execution_preview(h,c,owners)
            self.assertEqual(preview['latest_qualification']['reference'],latest)
            self.assertEqual(preview['evidence_since_qualification'],[])
            tail=save(h,dict(candidate=c,status='execution_incomplete',physical_launches=10,fixture='later'),
                'physical_playback_result')
            owners.insert(0,(tail,h.store.artifact(tail)))
            self.assertEqual(execution_preview(h,c,owners)['evidence_since_qualification'],[tail])

    def test_physical_plan_pending_and_result_keep_exact_candidate(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE]);c=self.candidate(h);other=self.candidate(h,1)
            save(h,read(ROOT/'configs/research/phs2d_original_protocol_source_v1_2.json'),'offline_protocol_fixture')
            def worker(command,*args,**kwargs):
                p=state(h)['pending'];pending=pending_evaluation(h,p)
                self.assertEqual(pending['kind'],'physical_replay');self.assertEqual(pending['candidate'],c)
                self.assertEqual(pending['episode_count'],10);self.assertEqual(pending['route'],'passive_protocol')
                self.assertEqual(pending['reserved_resources']['backend_solves'],10)
                self.assertIsNone(pending['worker_started']);self.assertIsNone(pending['worker_alive'])
                self.assertIsNotNone(pending['plan']);self.assertIsNotNone(pending['source'])
                atomic_json(Path(command[-1]).with_name('result.json'),dict(status='execution_incomplete',
                    reason='Explicit Mock Worker fixture; no physical computation'))
                return SimpleNamespace(returncode=0)
            with patch.object(core,'guard'),patch('tools.research.physical_replay.guard'),\
                    patch('tools.service_execution._run_contained',side_effect=worker):
                out=core.dispatch(h,replay_plan(c),'mock-physical-plan')
            result=h.store.artifact(out['result']['reference'])
            self.assertEqual(result['plan_reference'],out['plan']);self.assertEqual(result['candidate'],c)
            workflow=context(h)['evidence_working_set']['research_workflow']
            self.assertIsNone(workflow['pending_evaluation'])
            self.assertEqual(workflow['evaluations'][-1]['plan'],out['plan'])
            from tools.research.physical_replay import dispatch
            with patch('tools.research.physical_replay.guard'),self.assertRaisesRegex(ValueError,'PLAN_CANDIDATE_MISMATCH'):
                dispatch(h,PhysicalReplayRequest(candidate=other),'wrong-physical-plan',plan_reference=out['plan'])
            with patch('tools.research.physical_replay.guard'),self.assertRaisesRegex(ValueError,'PLAN_CANDIDATE_MISMATCH'):
                dispatch(h,PhysicalReplayRequest(candidate=c),'different-plan-key',plan_reference=out['plan'])

    def test_pending_only_reports_durable_worker_facts(self):
        with fixture() as h:
            folder=h.store.root/'pending-fixture';folder.mkdir()
            p=dict(kind='physical_replay',folder=str(folder))
            self.assertIsNone(pending_evaluation(h,p)['worker_started'])
            atomic_json(folder/'worker_lifecycle.json',dict(pid=123,started_unix=0))
            view=pending_evaluation(h,p);self.assertTrue(view['worker_started']);self.assertIsNone(view['worker_alive'])
            atomic_json(folder/'boundary.json',dict(termination_confirmed=True,returncode=1))
            self.assertTrue(pending_evaluation(h,p)['termination_confirmed'])

    def test_resolved_design_and_gateway_policy(self):
        s=resolve(SPEC)
        self.assertEqual(s['runtime']['provider']['adapter'],'chatgpt_gateway')
        self.assertEqual(s['runtime']['provider']['model'],'gpt-5.6-sol')
        self.assertEqual(s['family_space']['segment_count_bounds'],[1,9])
        self.assertEqual(s['family_space']['executable_segment_counts'],list(range(1,10)))
        self.assertEqual(s['family_space']['executable_tendon_count_bounds'],[1,12])
        self.assertEqual(s['budgets']['provider_requests'],64)
        self.assertEqual(s['budgets']['protected_provider_requests'],6)
        self.assertIsNone(s['provider_request_extension_policy']['maximum_additional_requests'])
        from tools.research.optimal_capability import family_variable_authorized
        for path in ('segments.0.length_m','segments.0.young_pa','spans.0.radius_m','spans.0.phase_rad',
                'spans.0.angular_offsets_rad.0','segments.0.sections.0.kind'):
            self.assertTrue(family_variable_authorized(s,path),path)

    def test_finite_request_additions_have_no_implicit_cumulative_ceiling(self):
        from tools.research.budget import extend_provider_requests
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            spec['provider_request_extension_policy']=dict(version='finite_provider_request_extension_v1',maximum_additional_requests=None)
            update(h,spec=spec)
            def approval():
                s=state(h)['spec'];scope=dict(study_id=h.run_id,resolved_identity=s['resolved_identity'],
                    previous_request_limit=s['budgets']['provider_requests'],additional_requests=300)
                return dict(version='provider_request_extension_approval_v1',approved=True,
                    source='Explicit offline additive budget fixture',scope=scope,scope_identity=digest(scope))
            before=h.store.remaining();first=approval()
            extend_provider_requests(h,first);extend_provider_requests(h,approval())
            self.assertEqual(h.store.remaining()['limit']['model_calls'],before['limit']['model_calls']+600)
            self.assertEqual(h.store.remaining()['used'],before['used'])
            self.assertTrue(extend_provider_requests(h,first)['already_applied'])
            bad=approval();bad['approved']=False
            with self.assertRaisesRegex(ValueError,'EXACT_USER_APPROVED'):extend_provider_requests(h,bad)

    def test_request_only_budget_keeps_numeric_costs_and_real_sdk_mock_compatible(self):
        from schemas.platform import MeasuredCost
        from tests.research.test_phs2d_topology_support import topology_fixture
        from tests.research.test_recent_round_tools import run_fixture
        with topology_fixture() as h:
            spec=state(h)['spec'];approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            update(h,freeze='offline-fixture',pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,
                'session_handoff_boundary':'request_feedback'})
            self.assertTrue(mathematics_fits(spec,10**9,100))
            self.assertEqual(capacity(h,10,root_operation=True,route='passive_protocol')['admitted'],10)
            b=decision_budget(h)
            self.assertIsNone(b['public_operation_budget']['remaining_total'])
            self.assertIsNone(b['science_budget']['remaining_full_replays']);self.assertFalse(protected(h))
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                self.assertEqual(len(run_fixture(h,[None])),1)
            c=self.candidate(h)
            save(h,read(ROOT/'configs/research/phs2d_original_protocol_source_v1_2.json'),'offline_protocol_fixture')
            def worker(command,*args,**kwargs):
                atomic_json(Path(command[-1]).with_name('result.json'),dict(status='execution_incomplete',reason='Mock Worker only'))
                return SimpleNamespace(returncode=0)
            with patch.object(core,'guard'),patch('tools.research.physical_replay.guard'),\
                    patch('tools.service_execution._run_contained',side_effect=worker):
                core.dispatch(h,replay_plan(c),'offline-unmetered-physics')
            self.assertEqual(h.store.remaining()['used']['backend_solves'],10)
            cost={**zero(),'backend_solves':1000,'tool_calls':1000}
            row,_=h.store.reserve(h.run_id,'offline-cost-fixture','fixture',h.actor,cost)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],1010)
            self.assertIsNone(h.store.remaining()['remaining']['tool_calls'])
            with self.assertRaises(ValueError):MeasuredCost.model_validate({**zero(),'tool_calls':None})

    def test_handoff_admission_requires_current_formal_approval_and_verified_live_evidence(self):
        from tools.research.session_handoff import assess_live_admission,admit_formal_study
        with fixture() as parent,fixture() as h:
            # Synthetic Store history: no HTTP transport or scientific worker exists.
            provider=state(h)['spec']['runtime']['provider'];session='offline-source-sdk'
            delivery=dict(items=[dict(preserve_once=True,tool_id='offline-call',fixture='Synthetic feedback')])
            def record_send(key,messages):
                wire=dict(model=provider['model'],reasoning_effort=provider['reasoning'],messages=messages)
                row,_=parent.store.reserve(parent.run_id,key,digest(wire),parent.actor,{**zero(),'model_calls':1})
                wire_ref=save(parent,wire)
                with parent.store.transaction() as db:
                    ref=parent.store.put(db,dict(endpoint=provider['base_url'].rstrip('/')+'/chat/completions',
                        purpose='conversation',request=wire_ref))
                    parent.store.event(db,parent.run_id,'r3_request','saved',request=key,outputs=[ref])
                    body=parent.store.put(db,json.dumps(dict(choices=[dict(finish_reason='tool_calls',message=dict(
                        tool_calls=[dict(id='offline-call',function=dict(name='evidence_read',arguments='{}'))]))])).encode(),
                        media='application/octet-stream')
                    reception=parent.store.put(db,dict(http_status=200,body=body.model_dump(mode='json')))
                    parent.store.event(db,parent.run_id,'r3_response','saved',request=key,outputs=[reception])
                parent.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=parent.actor,
                    tool_id='test.offline_model_fixture',tool_version='1.0.0',execution_status='completed',charged=zero()))
            record_send('offline-old',[])
            messages=[dict(role='assistant',content=[dict(toolUse=dict(toolUseId='offline-call'))]),
                dict(role='user',content=[dict(toolResult=dict(toolUseId='offline-call'))])]
            boundary=save(parent,dict(session_id=session,messages=messages))
            prep=dict(boundary_kind='request_feedback',previous_session=session,boundary=boundary,
                boundary_identity=digest(messages),pending_feedback_delivery=delivery)
            with parent.store.transaction() as db:
                preparation=parent.store.put(db,prep);restored=parent.store.put(db,dict(independently_restored=True,
                    preparation=preparation.model_dump(mode='json'),snapshot_files={'offline':digest('fixture')}))
                parent.store.event(db,parent.run_id,'session_handoff','saved',outputs=[preparation,restored])
            record_send('offline-continued',[dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+
                json.dumps(dict(research=dict(pending_feedback_delivery=delivery))))])
            proof=assess_live_admission(h,parent.store.root,parent.run_id);self.assertEqual(proof['status'],'ready')
            ref=save(h,proof,'handoff_admission_assessment')
            update(h,pilot={k:v for k,v in state(h)['pilot'].items() if k not in
                ('session_handoff_live_admitted','session_handoff_boundary')})
            with self.assertRaisesRegex(ValueError,'EXACT_FORMAL'):admit_formal_study(h,ref)
            scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],
                implementation_freeze=state(h)['freeze'],execution_scopes=[REGISTERED_MATHEMATICS_SCOPE,
                    'request-feedback session handoff'],session_handoff=dict(boundary='request_feedback',evidence=ref))
            grant=save(h,dict(user_approval='Explicit offline fixture only',scope=scope,scope_identity=digest(scope)),
                'formal_study_authorization')
            ledger=h.store.remaining();admit_formal_study(h,grant)
            self.assertTrue(state(h)['pilot']['session_handoff_live_admitted']);self.assertEqual(h.store.remaining(),ledger)
            changed=deepcopy(state(h)['spec']);changed['runtime']['provider']['model']='different-model'
            update(h,spec=changed)
            with self.assertRaisesRegex(ValueError,'SAME_PROVIDER_LIVE'):admit_formal_study(h,grant)


if __name__=='__main__':unittest.main()
