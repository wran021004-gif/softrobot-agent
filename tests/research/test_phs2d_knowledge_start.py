"""Knowledge isolation and finite grants. All SDK replies are offline fixtures."""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools.research import core, agent, experience
from tools.research.config import ROOT, resolve
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.evidence_policy import registered_references
from tools.research.state import state, update
from tests.research.test_cross_task_integration import fixture_directory
from tests.research.test_research_authorization_preflight import approve
from tests.research.test_recent_round_tools import run_fixture

SPEC=ROOT/'configs/research/study_phs2d_knowledge_autonomy_20261105.json'


@contextmanager
def fixture():
    spec=resolve(SPEC)
    spec['study_id']='phs-knowledge-fixture-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id']
    with fixture_directory() as folder, patch('tools.research.config.resolve',return_value=spec):
        h=core.prepare(directory=folder)
        update(h,freeze='offline-fixture',pilot={**state(h)['pilot'],
            'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
        yield h


class PhsKnowledgeStartTests(unittest.TestCase):
    def test_generation_catalog_does_not_conflate_math_direction_authorization(self):
        from tools.research.design import generate_candidate
        from tools.research.evidence_intent import resolve_evidence_intent
        from tools.research.optimal_capability import family_parameters
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            result=generate_candidate(h,dict(version='serial_family_generation_v2',
                family_space_identity=spec['family_space_identity'],segment_count=9,tendon_count=4,
                segments={'0':dict(length_m=0.159)},spans=[dict(first_segment=0,last_segment=3,count=4)],
                payout_lengths_m={'tendon_'+str(i):0.4 for i in range(4)}),dict(origin='Offline catalog/legality fixture only'))
            self.assertEqual(result['status'],'generated',result)
            ref=result['candidate'];candidate=h.store.artifact(ref)
            query=dict(subject=ref,topic='structure_parameters',group='segment')
            catalog=resolve_evidence_intent(h,query)
            self.assertIn('segment',catalog['parameter_groups'])
            self.assertIn('segments.0.length_m',catalog['parameter_choices'])
            overview=resolve_evidence_intent(h,dict(subject=ref,topic='structure_parameters',group='geometry',detail_level='targeted'))
            self.assertGreater(len(overview['facts']),1)
            self.assertNotIn('execution_semantics',overview['facts'][0])
            selected=resolve_evidence_intent(h,{**query,'selection':['segments.0.length_m']})
            row=selected['facts'][0]
            self.assertTrue(row['generation_available'])
            self.assertFalse(row['study_authorized'])
            self.assertFalse(row['selectable'])
            self.assertEqual(row['current_value'],0.159)
            self.assertIn('Mathematical',selected['authorization_scope']['study_authorized'])
            with self.assertRaisesRegex(ValueError,'AUTHORIZED_FAMILY_CONTINUOUS_PARAMETER_REQUIRED'):
                family_parameters(spec,candidate,'segments.0.length_m')
            self.assertEqual(state(h)['spec'],spec)
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_analysis_recovery_preserves_partial_worker_costs_and_unknown_fallback(self):
        from tools.platform_store import zero
        from tools.state_io import atomic_json,digest
        from tools.research import analysis
        for recorded in (True,False):
            with self.subTest(recorded=recorded),fixture() as h:
                query=dict(operation='mechanism_structure_v1',candidate=state(h)['family_space_reference'])
                key='offline-partial-cost-recovery';h.store.reserve(h.run_id,key,digest(query),h.actor,zero())
                folder=h.store.root/'offline-analysis-recovery';folder.mkdir()
                costs=[dict(purpose='failed_native_analysis',physics_steps=0,native_forward_calls=0,native_forward_attempts=1)]
                value=dict(status='execution_incomplete',reason='Synthetic engine failure fixture; no science')
                if recorded:value['internal_calculations']=costs
                atomic_json(folder/'result.json',value)
                atomic_json(folder/'boundary.json',dict(termination_confirmed=True,elapsed_s=0.4,returncode=1))
                (folder/'worker.log').write_text('Offline fixture only',encoding='utf-8')
                update(h,pending=dict(folder=str(folder),worker_request_id=key,request=query,
                    origin='offline-fixture',implementation='offline-fixture',reserved_s=0.),mathematical_evaluations=1)
                before=h.store.remaining()
                result=analysis.recover(h);raw=h.store.artifact(result['reference'])
                if recorded:
                    self.assertEqual(raw['internal_calculations'],costs)
                    self.assertEqual(state(h)['analysis_costs'][-1]['internal_calculations'],costs)
                else:self.assertEqual(raw['internal_calculations']['status'],'partial_or_unavailable')
                self.assertEqual(raw['status'],'execution_incomplete')
                self.assertEqual(state(h)['mathematical_evaluations'],1)
                before['used']['wall_s']+=0.4  # Original settlement records the fixture's elapsed time.
                self.assertEqual(h.store.remaining(),before)
                self.assertIsNone(state(h)['pending'])

    def test_failed_static_forward_retains_pre_call_state_and_partial_costs(self):
        from types import SimpleNamespace
        import mujoco
        import numpy as np
        from extensions.tendon_family.passive_equilibrium import StaticProblem
        model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint type="hinge"/><geom size="0.1"/></body></worldbody></mujoco>')
        native=SimpleNamespace(model=model,physics=dict(identity='offline-toy-model'),
            cost=dict(model_builds=1,material_point_jacobian_calls=0,tendon_jacobian_extractions=0))
        problem=StaticProblem(native)
        def fail(model,data):
            data.qpos[:]=999
            raise mujoco.FatalError('FactorizeHessian: rank-deficient sparse Hessian')
        with patch.object(mujoco,'mj_forward',new=fail),self.assertRaises(mujoco.FatalError) as error:
            problem.at(np.array([0.125]))
        value=error.exception
        self.assertEqual(value.mujoco_diagnostic['qpos'],[0.125])
        self.assertEqual(value.mujoco_diagnostic['error_location'],'passive_hard_equilibrium_forward')
        self.assertEqual(value.mujoco_diagnostic['failed_call_internal_steps'],'unknown')
        self.assertEqual(value.native_diagnostic['cost']['native_forward_calls'],0)
        self.assertEqual(value.native_diagnostic['cost']['native_forward_attempts'],1)
        self.assertEqual(value.native_diagnostic['cost']['physics_steps'],0)
        self.assertIsNone(problem.last)
        clean=StaticProblem(native);actual=clean.at(np.array([0.125]))
        expected=mujoco.MjData(model);expected.qpos[:]=0.125;mujoco.mj_forward(model,expected)
        for field in ('qpos','qvel','qfrc_bias','qfrc_passive','ten_length'):
            np.testing.assert_array_equal(getattr(actual,field),getattr(expected,field))
        clean.at(np.array([0.125]))
        self.assertEqual(clean.cost['native_forward_calls'],1)

    def test_discovery_reuses_v2_generation_without_changing_parameter_facts(self):
        from tools.research import optimal_capability as opt
        from tools.research.design import generate_candidate
        with fixture() as h:
            generated=generate_candidate(h,dict(version='serial_family_generation_v2',
                family_space_identity=state(h)['spec']['family_space_identity'],
                segment_count=9,tendon_count=4,spans=[dict(first_segment=0,last_segment=3,count=4)],
                payout_lengths_m={'tendon_'+str(i):0.4 for i in range(4)}),
                dict(origin='offline discovery regression; no scientific evaluation'))
            self.assertEqual(generated['status'],'generated',generated)
            ref=generated['candidate'];candidate=h.store.artifact(ref);spec=state(h)['spec']
            before=h.store.remaining();original=opt._family_parameter_data
            with patch.object(opt,'_family_parameter_data',wraps=original) as builds:
                result=opt.candidate_methods(h,ref)
            self.assertGreater(len(result['variables']),10)
            self.assertEqual(builds.call_count,1)
            for row in result['variables']:
                _,parameter=opt.family_parameters(spec,candidate,row['variable'])
                self.assertEqual(row['parameter'],parameter)
                self.assertEqual(row['current_value'],parameter['current_value'])
            changed=deepcopy(candidate)
            segment=next(p for p in changed['configuration']['robot']['structure']['data']['components'] if p['kind']=='flexible_segment')
            segment['length_m']+=0.001
            with self.assertRaisesRegex(ValueError,'GENERATED_CONFIGURATION'):
                opt.family_parameters(spec,changed,result['variables'][0]['variable'])
            legacy=deepcopy(spec)
            legacy['family_sensitivity_variables']=dict(version='family_sensitivity_v1',
                variables=['segments.0.length_m','spans.0.radius_m'])
            legacy_params,legacy_domain=opt.family_parameters(legacy,candidate,'segments.0.length_m')
            self.assertEqual(legacy_domain['current_value'],0.16)
            self.assertEqual(legacy_params['segments']['0']['length_m'],0.16)
            _,radius=opt.family_parameters(legacy,candidate,'spans.0.radius_m')
            self.assertEqual(radius['path'],'spans.0.radius_m')
            self.assertEqual(h.store.remaining(),before)
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_citation_error_feedback_resolves_advertised_alias_without_masking_gate(self):
        from tools.research.state import save
        from tools.research.agent import error_feedback
        with fixture() as h:
            ref=save(h,dict(fixture='Offline source only; no scientific computation'))
            update(h,analysis_results=[ref])
            before=deepcopy(state(h));ledger=h.store.remaining()
            use=dict(name='research_plan',toolUseId='offline-citation-failure',input=dict(
                action='stop',supporting_evidence=['result_1'],decision=dict(claimed_inference='local_diagnostic')))
            original=deepcopy(use)
            value=error_feedback(h,use,ValueError('EVIDENCE_DESIGN_IDENTITY_MISMATCH'),before)
            self.assertEqual(value['error_code'],'EVIDENCE_DESIGN_IDENTITY_MISMATCH')
            self.assertEqual(value['citation_errors'][0]['reference'],ref)
            self.assertFalse(value['worker_started'])
            self.assertEqual(use,original)
            self.assertEqual(h.store.remaining(),ledger)
            self.assertEqual(state(h)['research_status'],'ready')
            self.assertIsNone(state(h)['selected'])

    def test_rejected_payout_delivers_exact_frozen_domain_without_repair(self):
        from tools.research.design import generate_candidate
        from extensions.tendon_family.family_space import Domain
        with fixture() as h:
            before=deepcopy(state(h));ledger=h.store.remaining()
            request=dict(version='serial_family_generation_v2',
                family_space_identity=before['spec']['family_space_identity'],segment_count=9,tendon_count=4,
                spans=[dict(first_segment=0,last_segment=8,count=4,phase_rad=0)],
                payout_lengths_m={'tendon_'+str(i):1.3465 for i in range(4)})
            original=deepcopy(request)
            result=generate_candidate(h,request,dict(origin='offline rejection fixture'))
            self.assertEqual(result['status'],'invalid')
            self.assertEqual(result['reason'],'OUTSIDE_FAMILY_DOMAIN: payout_lengths_m.tendon_0')
            diagnostic=result['diagnostic']
            self.assertEqual(diagnostic['field'],'payout_lengths_m.tendon_0')
            self.assertEqual(diagnostic['requested_value'],1.3465)
            domain=Domain.model_validate(before['spec']['family_space']['passive_payout_domains_m']['tendon_0'])
            self.assertEqual(diagnostic['minimum'],domain.minimum)
            self.assertEqual(diagnostic['maximum'],domain.maximum)
            self.assertFalse(diagnostic['automatic_repair'])
            for boundary in (domain.minimum,domain.maximum):self.assertEqual(domain.check(boundary,'fixture'),boundary)
            self.assertEqual(request,original)
            self.assertEqual(state(h)['spec'],before['spec'])
            self.assertEqual(state(h)['candidates'],before['candidates'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining(),ledger)

    def test_accounted_quota_probe_does_not_become_sdk_history(self):
        import httpx
        from types import SimpleNamespace
        from tools.research.provider import LiveBoundary,request_settings
        from tools.research.session_handoff import trusted_history
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            provider=state(h)['pilot']['provider']
            def reply(request):
                return httpx.Response(200,json=dict(model=provider['model'],choices=[dict(
                    finish_reason='stop',message=dict(role='assistant',content='OK'))],
                    usage=dict(prompt_tokens=4,completion_tokens=1,total_tokens=5)))
            boundary=LiveBoundary(h,httpx.MockTransport(reply));boundary.purpose='gateway_quota_probe'
            async def probe():
                request=httpx.Request('POST',provider['base_url']+'/chat/completions',json=dict(
                    **request_settings(provider),messages=[dict(role='user',content='Offline quota fixture')]))
                response=await boundary.handle_async_request(request)
                self.assertEqual(response.status_code,200)
                boundary.consumed();await boundary.aclose()
            asyncio.run(probe())
            sdk=SimpleNamespace(messages=[],_session_manager=SimpleNamespace(
                session_id=state(h)['pilot']['framework_session_id']))
            self.assertEqual(trusted_history(h,sdk),'empty')
            from tools.research.state import save
            unknown=save(h,dict(purpose='unrecognized_probe'))
            with patch.object(h.store,'events',return_value=[dict(kind='r3_request',
                    request_id='synthetic-unrecognized-request',sequence=1,outputs=[unknown])]):
                with self.assertRaisesRegex(ValueError,'NO_TRUSTED_STORE_ANCHOR'):
                    trusted_history(h,sdk)
            sdk.messages=[dict(role='user',content=[dict(text='Untrusted suffix')])]
            with self.assertRaisesRegex(ValueError,'NO_TRUSTED_STORE_ANCHOR'):trusted_history(h,sdk)
            self.assertEqual(h.store.remaining()['used']['model_calls'],1)
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[None],limit=1)
            self.assertEqual(len(wires),1)
            self.assertEqual(h.store.remaining()['used']['model_calls'],2)
            self.assertFalse(state(h)['candidates'])
            self.assertFalse(state(h)['physical_replays'])

    def test_new_identity_preserves_science_and_freezes_only_six_procedures(self):
        old=resolve(ROOT/'configs/research/study_phs2d_autonomous_original_prepared_20261105.json')
        new=resolve(SPEC)
        for key in ('canonical_task','family_space','analysis_protocol','budgets',
                    'physical_replay_limit','physical_worker_watchdog_s','mathematical_worker_watchdog_s'):
            self.assertEqual(new[key],old[key],key)
        for key in ('backend','dynamics_model','discretization','controller'):
            self.assertEqual(new['configuration']['policy'][key],old['configuration']['policy'][key],key)
        self.assertEqual(new['provider_request_extension_policy'],dict(version='finite_provider_request_extension_v1',
            maximum_additional_requests=104,maximum_requests_per_extension=8))
        self.assertNotEqual(old['resolved_identity'],new['resolved_identity'])
        rows=new['knowledge_manifest']['entries']
        self.assertEqual(len(rows),6)
        self.assertEqual({r['entry_id'] for r in rows},set(new['knowledge']['include_entry_ids']))
        for row in rows:
            self.assertEqual(row['kind'],'procedure')
            self.assertEqual(row['revision'],'1')
            self.assertEqual(row['compact_skill']['source_sha256'],hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest())
        self.assertFalse(new['supplied_evidence'])
        for key in ('history','mathematics','control_seeds'):
            self.assertFalse(new['research_decisions'][key])

    def test_all_index_entries_and_referenced_sources_remain_confined(self):
        with fixture() as h:
            allowed=set(state(h)['spec']['knowledge']['include_entry_ids'])
            found=experience.retrieve(h,dict(operation='search'))
            self.assertEqual({r['entry_id'] for r in found['results']},allowed)
            self.assertTrue(all('content' not in r for r in found['results']))
            for row in experience._index_rows():
                if row['entry_id'] in allowed:continue
                self.assertFalse(experience.retrieve(h,dict(entry_id=row['entry_id']))['results'])
                with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
                    experience.retrieve(h,dict(operation='read',entry_id=row['entry_id'],revision=row['revision']))
            for row in found['results']:
                for reader in ('agent','reporter'):
                    read=experience.retrieve(h,row['read_query'],reader=reader)
                    self.assertFalse(read['scientific_evidence'])
                    self.assertEqual(read['results'][0]['content_role'],'procedural_knowledge')
                    for source in read['results'][0]['content']['evidence_sources']:
                        if 'entry_id' in source:
                            with self.assertRaisesRegex(ValueError,'EXACT_EXPERIENCE_READ'):
                                experience.retrieve(h,dict(operation='read',**source),reader=reader)
            self.assertEqual(registered_references(h),[])
            self.assertFalse(state(h)['candidates'])
            self.assertFalse(state(h)['results'])
            self.assertFalse(state(h)['physical_replays'])

    def test_read_rejects_content_drift_against_frozen_hash(self):
        with fixture() as h:
            query=dict(operation='read',entry_id='skill-parameter-model',revision='1')
            with patch('pathlib.Path.read_bytes',return_value=b'{"changed":true}'):
                with self.assertRaisesRegex(ValueError,'FROZEN_KNOWLEDGE_CONTENT_CHANGED'):
                    experience.retrieve(h,query)
            self.assertFalse(state(h)['retrievals'])

    def test_knowledge_receipts_cannot_support_select_or_stop(self):
        from tools.research.contracts import Plan
        from tools.research.evidence_policy import admit_decision
        from tests.research.test_cross_task_integration import plan
        with fixture() as h:
            receipt=experience.retrieve(h,dict(operation='read',entry_id='skill-witness-replay',revision='1'))['reference']
            for action in ('select','stop'):
                with self.subTest(action=action):
                    payload=dict(supporting_evidence=[receipt])
                    if action=='select':payload['selected_execution']=receipt
                    value=Plan.model_validate(plan(action,**payload))
                    with self.assertRaisesRegex(ValueError,'UNREGISTERED_RESEARCH_EVIDENCE'):
                        admit_decision(h,value)
            self.assertIsNone(state(h)['selected'])
            self.assertEqual(state(h)['research_status'],'ready')

    def test_gateway_sdk_wire_delivers_hint_then_on_demand_body(self):
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            hint=experience.retrieval_hint(h)
            self.assertIn('skill',hint)
            self.assertNotIn('content',hint)
            query=dict(operation='read',entry_id='skill-parameter-model',revision='1')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('experience_retrieve',query),None],limit=2)
            names={t['function']['name'] for t in wires[0]['tools']}
            self.assertIn('experience_retrieve',names)
            self.assertEqual(wires[0]['model'],'gpt-5.6-sol')
            self.assertEqual(wires[0]['reasoning_effort'],'medium')
            self.assertTrue(experience.hint_progress(h))
            self.assertTrue(experience.read_progress(h)['reads'][0]['body_delivered'])
            self.assertNotIn('diagnostic_questions',json.dumps(wires[0]))
            self.assertIn('diagnostic_questions',json.dumps(wires[1]))
            self.assertEqual(registered_references(h),[])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_new_study_rejects_live_entry_before_credentials_or_transport(self):
        with fixture() as h:
            with patch('tools.research.agent.credential') as credentials,patch('httpx.AsyncHTTPTransport') as transport:
                with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
                    asyncio.run(agent.converse(h,max_new_provider_requests=1))
            credentials.assert_not_called()
            transport.assert_not_called()
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)


if __name__=='__main__':unittest.main()
