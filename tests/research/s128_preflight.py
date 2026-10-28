"""S12.8 preparation only: no Provider traffic, training or scientific rollout."""
import asyncio
from copy import deepcopy
from importlib.metadata import version
import json
import os
import subprocess
import sys
import unittest
from uuid import uuid4
from unittest.mock import patch

import httpx
from tools.research.config import ROOT, resolve
from tools.research.core import prepare
from tools.research.state import state, update
from tools.research import rl
from tools.research.budget import reserve_evaluation, backend_capacity, stage_usage
from tools.research.agent import build_harness, LiveBoundary, live_model_class, plan_schema, error_feedback
from tools.research.contracts import Plan, RLRequest
from tools.state_io import read, atomic_json, digest

SPEC = ROOT/'configs/research/study_s128_cold.json'
OUT = ROOT/'evidence/s128_preflight'


def fixture():
    leaf = read(SPEC)
    leaf['study_id'] = 's128-check-'+uuid4().hex[:12]
    leaf['authorization'] = 'Current S12.8 preparation: isolated offline fixture; no external traffic or training'
    path = SPEC.parent/('._'+leaf['study_id']+'.json')
    atomic_json(path, leaf)
    try:
        return prepare(path, directory=ROOT/'runs'/leaf['study_id'])
    finally:
        path.unlink()


def provider_scope(spec):
    return dict(stage='S12.8',study_id=spec['study_id'],resolved_identity=spec['resolved_identity'],
        endpoint='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',
        max_output_tokens=131072,budgets=spec['budgets'],nmpc_limits=spec['nmpc_limits'],rl_limits=spec['rl_limits'],
        transmissions=['frozen new-study task, FamilySpace, candidate structures and controls',
            'tool schemas, exact scoped scientific evidence, actual new-study tool history',
            'complete assistant reasoning_content, tool calls/IDs and tool results on subsequent requests'],
        excluded=['credentials, unrelated/private workspace data, old Study chats and measured experimental answers'],
        local_raw_data='runs/research/'+spec['study_id']+'; original HTTP bytes, reasoning, SDK snapshots, Store, receipts, checkpoints and scientific arrays remain local',
        github_publication=['project code and configuration','derived statistics','necessary evidence identities/references','approved public reports'],
        raw_provider_store_sdk_publication=False,automatic_retries=0,context_limit_tokens=1000000,
        session_strategy='fresh continuous Strands; minimal SDK consistency checks; production rotation requires separate full-path admission',
        authority='Original independent MuJoCo evaluator, unchanged task and thresholds',
        ceilings_not_required_usage=True,authorization_status='pending_independent_explicit_user_approval')


def environment_check():
    """Candidate exists only in an isolated construction fixture, never formal science."""
    from tools.research.design import generate_candidate
    h=fixture();s=state(h)
    candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
        family_space_identity=s['spec']['family_space_identity'],segment_count=2,tendon_count=4),
        dict(origin='S12.8 environment-construction fixture, unmeasured'))['candidate']
    cfg,_=rl.prepare_input(h,RLRequest(operation='start',candidate=candidate,mode='direct',
        allocation=dict(actions=1048576),rationale='Construct only, no training or rollout'))
    rl.training_capacity(h,dict(actions=cfg['budget']['actions']))
    path=h.store.root/'environment.json';atomic_json(path,cfg)
    script="""import json,sys,shutil
from importlib.metadata import version
from tools.state_io import read
from tools.rl.env import TensionEnv
from tools.rl import train,checks,continuation
e=TensionEnv(read(sys.argv[1]))
print(json.dumps(dict(status='constructed',python=sys.executable,dofs=e.model.nq,actions=list(e.action_space.shape),observations=list(e.observation_space.shape),intervals=e.horizon,timestep_s=e.model.opt.timestep,versions={p:version(p) for p in ('mujoco','torch','stable-baselines3','gymnasium')},checkpoint_entry=callable(train.publish_checkpoint),checkpoint_validation_entry=callable(train.valid_checkpoint),continuation_entry=callable(continuation.initialize),evaluation_entry=callable(checks.evaluate),free_disk_bytes=shutil.disk_usage('.').free,training_actions=0,physics_steps=0)))
e.close()
"""
    done=subprocess.run([s['spec']['runtime']['rl_python'],'-c',script,str(path)],cwd=ROOT,
        capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if done.returncode:raise RuntimeError(done.stderr[-4000:])
    result=json.loads(done.stdout)
    assert result['intervals']==35 and result['timestep_s']==.0005
    assert all(result[k] for k in ('checkpoint_entry','checkpoint_validation_entry','continuation_entry','evaluation_entry'))
    result.update(fixture_study=h.run_id,formal_evidence_imported=False,scientific_evidence=False,
        requested_actions=1048576,aligned_actions=cfg['budget']['actions'])
    atomic_json(OUT/'rl_environment.json',result)
    return result


def prepare_formal():
    """Provision a never-used local Store and a zero-message SDK; do not invoke it."""
    spec=resolve(SPEC);directory=ROOT/'runs/research'/spec['study_id']
    if directory.exists():raise ValueError('NEW_STORE_DIRECTORY_REQUIRED; audit existing Store instead of overwriting')
    atomic_json(OUT/'provider_scope.json',provider_scope(spec))
    h=prepare(SPEC);s=state(h)
    def forbidden(request):raise AssertionError('S12.8 preparation forbids Provider traffic')
    boundary=LiveBoundary(h,httpx.MockTransport(forbidden))
    from strands.tools.executors import SequentialToolExecutor
    def build():
        return build_harness(h,transport=boundary,api_key='offline-preparation-no-credential',
            instructions='Provision empty S12.8 SDK only; no invocation',model_class=live_model_class(boundary),
            tool_executor=SequentialToolExecutor(),research_tools=[],configuration_path=h.store.root/'empty_sdk_configuration.json',
            session_directory=h.store.root/'framework_sessions')
    agent=build()
    assert not agent.messages
    async def persist_and_reopen():
        await agent._session_manager.save_snapshot(agent,is_latest=True)
        restored=build()
        assert await restored._session_manager.restore_snapshot(restored)
        assert not restored.messages and restored._session_manager.session_id==h.run_id
    asyncio.run(persist_and_reopen())
    from tools.research.session_handoff import snapshot_files
    empty_snapshot=snapshot_files(h.store.root/'framework_sessions',h.run_id,flush=True)
    empty_keys=('candidates','results','physical_replays','analysis_results','mechanics_results','rl_runs',
        'research_history','research_mathematics','control_initializations','scoped_context')
    assert all(not s.get(k) for k in empty_keys)
    assert not h.store.remaining()['used']['model_calls'] and not h.store.remaining()['used']['backend_solves']
    wire=dict(model='deepseek-flash',thinking=dict(type='enabled'),reasoning_effort='high',max_tokens=131072,
        stream=False,messages=[dict(role='system',content=spec['execution_instructions']),
        dict(role='user',content=json.dumps(spec['family_space']))],
        tools=[dict(type='function',function=dict(name='research_plan',parameters=plan_schema(spec['allowed_plan_actions'],decision_required=True)))])
    size=len(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire).content)
    assert size+131072+8192<1000000
    result=dict(status='prepared_approval_pending',study_id=h.run_id,store=str(h.store.root),
        directory_absent_before_prepare=True,framework_session_id=s['pilot']['framework_session_id'],sdk_messages=0,
        empty_sdk_persisted_and_independently_reopened=True,empty_snapshot_files=empty_snapshot,
        empty_scientific_state={k:not s.get(k) for k in empty_keys},ledger=h.store.remaining(),
        resolved_identity=spec['resolved_identity'],canonical_task_identity=spec['canonical_task_identity'],
        family_space_identity=spec['family_space_identity'],scope_identity=digest(provider_scope(spec)),
        capacity=dict(serialized_utf8_bytes=size,max_output_tokens=131072,framing=8192,
            conservative_total=size+131072+8192,limit=1000000,actual_tokens=None,
            scope='Initial instructions/family/Plan-schema envelope, not actual full runtime wire; every actual wire is checked by LiveBoundary'),
        versions={p:version(p) for p in ('openai','strands-agents','strands-harness','pydantic','mujoco','casadi','scipy')},
        scientific_evidence=False,formal_agent_started=False,production_handoff_admitted=False)
    atomic_json(OUT/'cold_start.json',result)
    asyncio.run(boundary.aclose())
    return result


class PreflightTests(unittest.TestCase):
    def test_full_high_allocation_admission_stops_at_worker_launch_boundary(self):
        from tools.research.design import generate_candidate
        from tools.research.state import core_hashes
        h=fixture();s=state(h)
        candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
            family_space_identity=s['spec']['family_space_identity'],segment_count=2,tendon_count=4),
            dict(origin='Isolated high-budget admission fixture only'))['candidate']
        update(h,freeze='isolated-offline-admission-fixture',core_hashes=core_hashes())
        with patch.object(rl,'invoke',return_value=dict(status='preflight_worker_launch_intercepted')) as launch:
            for i in range(4):
                request=dict(operation='start',candidate=candidate,mode='direct',allocation=dict(actions=1048576),
                    rationale='Isolated admission fixture '+str(i))
                result=rl.dispatch(h,request,'preflight-stage-'+str(i))
                self.assertEqual(result['effective_allocation']['actions'],1048576)
                used=h.store.remaining()
                self.assertEqual(rl.dispatch(h,request,'preflight-stage-'+str(i)),result)
                self.assertEqual(h.store.remaining(),used)
            with self.assertRaisesRegex(ValueError,'ACTION_COUNT'):
                rl.dispatch(h,dict(request,rationale='fifth exceeds aggregate'),'preflight-fifth')
            self.assertEqual(launch.call_count,4)
        self.assertEqual(stage_usage(state(h))['actual_actions'],0)
        self.assertEqual(state(h)['admitted_training_stages'],4)
        self.assertEqual(backend_capacity(h),72)  # Four fixture starts plus four held evaluations.
        atomic_json(OUT/'rl_admission.json',dict(fixture_study=h.run_id,scientific_evidence=False,
            admission='Full real dispatch, candidate, task, identity, configuration, shared atomic reservation and count guards; only worker invocation intercepted',
            aligned_actions_per_stage=1048576,admitted_fixture_stages=4,aggregate_allocated=4194304,
            actual_training_actions=0,actual_worker_launches=0,evaluation_reservations=4,
            unused_stage_slots=4,fifth_stage_rejected_for_aggregate=True,
            per_stage_upper_bound=1048576,training_and_evaluation_share_80_launch_ceiling=True,
            formal_store_affected=False))

    def test_independent_approval_blocks_before_credentials_and_science(self):
        from tools.research.agent import converse,record
        from tools.research.state import guard,require_authorization
        h=fixture();s=state(h);spec=deepcopy(s['spec'])
        spec['authorization']=read(SPEC)['authorization'];update(h,spec=spec)
        with patch('tools.research.provider.load_credential',side_effect=AssertionError('No credentials')):
            with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):asyncio.run(converse(h))
        with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):guard(h,expensive=True)
        wrong=provider_scope(spec);wrong['study_id']='old-s127-study'
        record(h,'formal_study_authorization',dict(scope=wrong,scope_identity=digest(wrong),user_approval='Explicit offline fixture only'))
        with self.assertRaisesRegex(ValueError,'APPROVAL_REQUIRED'):require_authorization(h)
        scope=provider_scope(spec)
        record(h,'formal_study_authorization',dict(scope=scope,scope_identity=digest(scope),user_approval='Explicit offline fixture only'))
        require_authorization(h)
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)

    def test_exact_startup_wire_and_capacity_failure_before_reservation(self):
        from tools.research.agent import converse
        from tests.research.test_s127_session_recovery import response
        h=fixture();update(h,freeze='isolated-s128-wire-fixture');wires=[]
        def capture(request):
            wires.append(request.content);update(h,research_status='stopped')
            return response(request)
        with patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(capture)):
            asyncio.run(converse(h))
        self.assertEqual(len(wires),1)
        wire=json.loads(wires[0]);self.assertEqual(wire['max_tokens'],131072)
        self.assertEqual(wire['reasoning_effort'],'high')
        self.assertEqual(wire['thinking'],dict(type='enabled'))
        self.assertTrue({'research_plan','research_rl','research_analysis','evidence_read'}<=
            {t['function']['name'] for t in wire['tools']})
        atomic_json(OUT/'startup_capacity.json',dict(actual_runtime_wire=True,synthetic_response=True,
            actual_provider_requests=0,scientific_workers=0,serialized_utf8_bytes=len(wires[0]),
            max_output_tokens=131072,framing=8192,conservative_total=len(wires[0])+131072+8192,
            context_limit_tokens=1000000,fits=len(wires[0])+131072+8192<=1000000,actual_tokens=None,
            note='Exact fresh-runtime startup path with synthetic HTTP only; fixture guards bypass implementation binding, not LiveBoundary capacity or receipt accounting'))
        clean=fixture();boundary=LiveBoundary(clean,httpx.MockTransport(lambda request:self.fail('Must not send')))
        wire['messages']=[dict(role='user',content='x'*1000000)]
        before=clean.store.remaining()
        async def reject():
            with self.assertRaisesRegex(ValueError,'CONTEXT_CAPACITY'):
                await boundary.handle_async_request(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire))
            await boundary.aclose()
        asyncio.run(reject());self.assertEqual(clean.store.remaining(),before)

    def test_task_and_cold_configuration(self):
        spec=resolve(SPEC)
        old=resolve(ROOT/'configs/research/study_s126_cold.json')
        self.assertEqual(spec['canonical_task_identity'],old['canonical_task_identity'])
        self.assertEqual(spec['family_space_identity'],old['family_space_identity'])
        self.assertEqual(spec['configuration']['task'],old['configuration']['task'])
        self.assertTrue(all(not spec['research_decisions'][k] for k in ('history','mathematics','control_seeds')))
        self.assertFalse(spec['supplied_evidence'])
        self.assertEqual(spec['runtime']['provider']['max_tokens'],131072)
        self.assertEqual(spec['budget_semantics']['mode'],'count')

    def test_large_allocations_and_shared_evaluation_reservations(self):
        h=fixture()
        for actions in (512,65536,524288,1048576):
            self.assertEqual(rl.align_steps(actions,256),actions)
            rl.training_capacity(h,dict(actions=actions))
        with self.assertRaisesRegex(ValueError,'ACTION_COUNT'):rl.training_capacity(h,dict(actions=1048832))
        entries={}
        for i in range(8):
            rl.training_capacity(h,dict(actions=524288))
            with h.store.transaction() as db:reserve_evaluation(h,state(h),db,training=True)
            entries[str(i)]=dict(allocation=dict(actions=524288),evaluations=0,evaluation_reserved=True,
                status=dict(worker_alive=False,consumed=dict(attempted_actions=0,completed_actions=0)))
            update(h,rl_runs=deepcopy(entries),admitted_training_stages=i+1)
        self.assertEqual(backend_capacity(h),72)
        self.assertEqual(rl.allocation_feedback(h)['remaining_allocatable_actions'],0)
        self.assertEqual(stage_usage(state(h))['admitted'],8)
        self.assertEqual(stage_usage(state(h))['actual_actions'],0)
        with self.assertRaisesRegex(ValueError,'STAGE_LIMIT'):rl.training_capacity(h,dict(actions=512))
        update(h,admitted_training_stages=7)
        with self.assertRaisesRegex(ValueError,'ACTION_COUNT'):rl.training_capacity(h,dict(actions=512))
        for entry in entries.values():entry['evaluations']=1
        entries['0']['evaluations']=5
        update(h,rl_runs=entries)
        with h.store.transaction() as db:
            with self.assertRaisesRegex(ValueError,'EVALUATION_CAPACITY'):reserve_evaluation(h,state(h),db,training=True)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_hypothesis_and_extra_fields_feedback(self):
        h=fixture();before=state(h)
        payload=dict(action='initialize_control',control_seed=dict(candidate=before['family_space_reference'],method='baseline'),
            expected_observation='fixture',weakening_observation='fixture',fixed_conditions='fixture',
            stopping_condition='fixture',interpretation='fixture')
        for changes,field in (({},'hypothesis'),(dict(hypothesis='fixture',unexpected_field=1),'unexpected_field')):
            value={**payload,**changes}
            try:Plan.model_validate(value)
            except ValueError as exc:feedback=error_feedback(h,dict(name='research_plan',input=value),exc,before)
            else:self.fail('Invalid Plan unexpectedly accepted')
            self.assertEqual(feedback['field'],field)
            self.assertFalse(feedback['scientific_execution_started'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_wrapper_samples_feedback_exposes_real_raw_reference(self):
        from tools.research.core import read_evidence
        from tools.research.state import save
        h=fixture();raw=save(h,dict(samples=[dict(time_s=0.)]))
        wrapper=save(h,dict(raw_reference=raw,status='fixture_only'))
        query=dict(reference=wrapper,view='range',pointer='/samples')
        before=state(h)
        with self.assertRaises(KeyError) as raised:read_evidence(h,query)
        feedback=error_feedback(h,dict(name='evidence_read',input=query),raised.exception,before)
        self.assertIn('raw_reference',feedback['expected'])
        self.assertFalse(feedback['scientific_execution_started'])
        self.assertEqual(read_evidence(h,dict(reference=raw,view='range',pointer='/samples'))['total'],1)

    def test_inconsistent_committed_history_is_rejected(self):
        """The original S12.8 reproduction now fails before any Store side effect."""
        from tests.research.test_s127_session_recovery import factory, response, complete
        from tools.research.session_handoff import handoff, reconcile
        from tools.research.agent import converse
        h=fixture();update(h,freeze='isolated-offline-S128-handoff-fixture')
        boundary=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,boundary)
        async def exercise():
            old=build();await complete(h,old,'Complete the synthetic boundary')
            _,new=await handoff(h,old,build,h.store.root/'sdk')
            new.messages.append(dict(role='assistant',content=[dict(text='Changed fixture history without any Provider send')]))
            await new._session_manager.save_snapshot(new,is_latest=True)
            before=state(h);events=h.store.events(h.run_id);ledger=h.store.remaining()
            with self.assertRaisesRegex(ValueError,'INITIAL_CONTEXT'):await reconcile(h,build,h.store.root/'sdk')
            self.assertEqual(state(h),before);self.assertEqual(h.store.events(h.run_id),events);self.assertEqual(h.store.remaining(),ledger)
            self.assertFalse(state(h)['pilot'].get('session_handoff_live_admitted',False))
            await boundary.aclose()
        asyncio.run(exercise())
        with patch('tools.research.provider.load_credential',side_effect=AssertionError('No credentials')):
            with self.assertRaisesRegex(ValueError,'HANDOFF_NOT_ADMITTED'):asyncio.run(converse(h,session_handoff=True))
        atomic_json(OUT/'session_admission.json',dict(production_handoff_admitted=False,
            actual_provider_requests=0,synthetic_http_responses=1,scientific_workers=0,
            prior_live_proof='evidence/s127_6_handoff/live_reopen.json',
            original_gap_fixed=True,snapshot_content_integrity_passed=True,
            decision='Use Store initial messages/files or latest completed-turn identity for consistency; interrupted tool rounds retain existing receipt/feedback recovery. Production admission is assessed separately after focused regressions.',
            affected_path='Optional handoff only; no formal S12.8 Store or old sealed Store was modified'))


if __name__=='__main__':
    if '--environment' in sys.argv:print(json.dumps(environment_check()))
    elif '--prepare' in sys.argv:print(json.dumps(prepare_formal()))
    else:unittest.main()
