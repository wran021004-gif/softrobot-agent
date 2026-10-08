"""Original saved answer replay and component counterexamples, offline only."""
from copy import deepcopy
from contextlib import contextmanager
import json
from pathlib import Path
from unittest import TestCase
from tools.state_io import read,digest
from tools.platform_store import Store,plain,encode
from tools.research_metric_view import build
from tools.research_error_routing import classify
from tools.disposition_facts import expand
from tools.investigation_contract import contract
from tools.research_investigations import InvestigationDispatcher,SourceFact
from tools.context_assembly import check_outgoing_request

ROOT=Path(__file__).resolve().parents[1]


class MemoryArchive:
    def __init__(self,bundle):self.bundle=deepcopy(bundle);self.artifacts=self.bundle['artifacts']
    def artifact(self,ref,db=None):return self.artifacts[plain(ref)['artifact_id']]
    def session(self,run_id,db=None):return dict(state=self.bundle['state'])
    def lookup(self,run_id,request_id,db=None):return next((c for c in self.bundle['calls'] if c['run_id']==run_id and c['request_id']==request_id),None)
    @contextmanager
    def transaction(self):yield None
    def put(self,db,value):
        ref=dict(artifact_id=digest(value),media_type='application/json');self.artifacts[ref['artifact_id']]=plain(value);return ref
    def update_state(self,db,run_id,state):self.bundle['state']=state
    def event(self,*args,**kwargs):pass


class FinishTests(TestCase):
    def historical(self):
        a=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')
        s=Store(ROOT/'runs/stage336_manual_20261001_090616')
        return a['execution']['factual_result'],s

    def test_original_version_components_recomputed(self):
        f,s=self.historical();v=build(f,s.artifact)
        self.assertEqual(v['reach']['recorded_result'],False);self.assertEqual(v['reach']['recomputed_result'],False)
        self.assertEqual(v['holding']['position']['recomputed_result'],False)
        self.assertEqual(v['holding']['speed']['recomputed_result'],False)
        self.assertEqual(v['reach']['criterion_version'],'evaluate.reach@1.0.0')
        self.assertIn('@6.0.0',v['holding']['speed']['criterion_version'])

    def test_official_failure_without_independent_signal_is_retained(self):
        f,s=self.historical()
        def resolve(ref):
            if ref==f['simulation']:raise KeyError('missing archived signal')
            return s.artifact(ref)
        v=build(f,resolve)
        self.assertIs(v['official']['recorded_result'],False)
        self.assertIsNone(v['reach']['recomputed_result'])
        self.assertEqual(v['reach']['independent_recomputation'],'unavailable')

    def test_component_pass_does_not_imply_joint_acceptance(self):
        from tools.research_tasks import assemble_acceptance
        f,s=self.historical();cfg=s.artifact(f['configuration']);ev=s.artifact(f['evaluation']);profile=s.artifact(f['report']['reference'])
        # Explicit counterexample, not a new historical outcome or backend run.
        ev=deepcopy(ev);ev['task_success']=True;ev['metrics'][0]['value']=.005
        ev['constraints'][0].update(observed=.005,satisfied=True)
        profile=deepcopy(profile);profile['detail']['official_task_success']=True
        result=assemble_acceptance(cfg,evaluation=ev,profile=profile,evaluation_reference=f['evaluation'],profile_reference=f['report']['reference'])
        self.assertFalse(result['accepted']);self.assertTrue(result['components']['task_evaluator']['passed'])
        self.assertFalse(result['components']['holding_speed']['passed'])

    def test_saved_real_native_selection_exact_replay_and_capacity(self):
        bundle=read(ROOT/'evidence/research_disposition_facts_20261008/stages/reuse_bundle.json')
        archive=MemoryArchive(bundle);d=object.__new__(InvestigationDispatcher)
        d.store=archive;d.run_id='mainline3-reuse-repair2'
        d._reports=lambda:{**bundle['state']['historical_investigations'],**bundle['state']['investigations']}
        event=[e for e in bundle['events'] if e['kind']=='investigation_provider_response'][-1]
        raw=archive.artifact(event['outputs'][0]);parsed=contract(selectable=True).parse('investigation_return',raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        node=bundle['state']['investigations']['principal-historical-disposition']
        cfg=read(ROOT/'evidence/research_disposition_facts_20261008/stages/frozen_configuration.json')['policy']['model']
        for e in bundle['events']:
            if e['kind']=='investigation_provider_attempt':self.assertTrue(check_outgoing_request(archive.artifact(e['outputs'][0])['payload'],cfg,'research_decision')['passed'])
        expanded=[expand(d,selected,node['fact_catalog'],path=f'/dispositions/{i}') for i,selected in enumerate(parsed.dispositions)]
        self.assertLess(len(json.dumps(dict(interpretation=parsed.interpretation,dispositions=[plain(x) for x in expanded]),ensure_ascii=False).encode()),65536)
        self.assertEqual([x.disposition for x in expanded],[x.disposition for x in parsed.dispositions])
        for x in expanded:
            for c in x.adopted_claims:
                for fact in (*c.supporting_facts,*c.additional_support,*c.scope):d._validate_fact(fact,'PRINCIPAL')
        # Correct references validate structure; the disputed inference remains a separate review.
        disputed=expanded[0].adopted_claims[3]
        self.assertIn('reach success is unknown',disputed.statement)
        self.assertTrue(all('one_step_prediction_summary' in f.pointer for f in disputed.supporting_facts))

    def test_program_capacity_never_spends_protocol_correction(self):
        self.assertFalse(classify(ValueError('INVESTIGATION_RETURN_TOO_LARGE'))['paid_correction_eligible'])
        self.assertFalse(classify(ValueError('CONTEXT_SEND_BOUNDARY_OVERFLOW: measured'))['paid_correction_eligible'])
        self.assertFalse(classify(OSError('disk write'))['paid_correction_eligible'])
        self.assertTrue(classify(ValueError('PRINCIPAL_MUST_INSPECT_SOURCE'))['paid_correction_eligible'])
        self.assertTrue(classify(ValueError('MATERIAL_INSUFFICIENT_SUPPORT'))['paid_correction_eligible'])
        self.assertFalse(classify(TimeoutError(),stage='transport')['automatic_transport_retry'])

    def test_public_joint_operation_schema_and_source_binding(self):
        from tools.platform_registry import registry
        from tools.research_joint_evaluation import JointEvaluation,evaluate
        from types import SimpleNamespace
        f,s=self.historical();args=JointEvaluation(configuration=f['configuration'],evaluation=f['evaluation'],profile=f['report']['reference'])
        ext=registry().get('research.task_acceptance','1.0.0','tool')
        self.assertIs(ext.input_schema,JointEvaluation)
        result=evaluate(SimpleNamespace(artifact=s.artifact),args).detail
        self.assertEqual(result['status'],'valid_failure');self.assertFalse(result['accepted'])
        self.assertEqual(result['new_backend_solves'],0)
        self.assertEqual(result['execution_id'],f['execution_id'])
        profile=deepcopy(s.artifact(f['report']['reference']));profile['detail']['configuration']=f['simulation']
        def bad(ref):return profile if plain(ref)==f['report']['reference'] else s.artifact(ref)
        with self.assertRaisesRegex(ValueError,'CONFIGURATION_BINDING'):evaluate(SimpleNamespace(artifact=bad),args)

    def test_new_saved_scope_error_locates_claim_and_available_handles(self):
        from tools.disposition_facts import BindingError
        from tools.research_investigations import InvestigationResult
        path=ROOT/'evidence/research_mainline3_v1_finish_20261008/reuse_bundle.json'
        if not path.exists():self.skipTest('New real answer not yet available')
        b=read(path);archive=MemoryArchive(b);d=object.__new__(InvestigationDispatcher)
        d.store=archive;d.run_id='mainline3-reuse-received-recovery1'
        d._reports=lambda:{**b['state']['historical_investigations'],**b['state']['investigations']}
        d._grant=lambda *a:(dict(state=b['state']),b['state']['role_context']['investigation_grant'])
        d._principal_authority=lambda:None
        d.recover=lambda key:InvestigationResult(investigation_id=key,status='completed',result=b['state']['historical_investigations'][key]['result'])
        failure=next(e for e in b['events'] if e['kind']=='investigation_protocol_correction' and any(i.get('code')=='ADOPTED_CLAIM_SCOPE_SOURCE_MISMATCH' for i in archive.artifact(e['outputs'][0])['issues']))
        event=next(e for e in reversed(b['events']) if e['kind']=='investigation_provider_response' and e['sequence']<failure['sequence'])
        raw=archive.artifact(event['outputs'][0])
        selected=contract(selectable=True).parse('investigation_return',raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        node=b['state']['investigations']['principal-historical-v2']
        expanded=expand(d,selected.dispositions[0],plain(selected.dispositions[0].catalog),path='/dispositions/0')
        with self.assertRaises(BindingError) as caught:d.disposition(expanded,validate_only=True)
        self.assertIn('/adopted_claims/',caught.exception.issue['path'])
        self.assertTrue(caught.exception.issue['path'].endswith('/scope'))
        self.assertTrue(caught.exception.issue['legal']['available_scope_handles'])

    def test_corrections_preserve_phase_cap_and_per_unresolved_report_cap(self):
        from types import SimpleNamespace
        state=dict(investigations={'same-logical-node':dict(usage=dict(model_calls=0))})
        archive=MemoryArchive(dict(state=state,artifacts={}))
        d=object.__new__(InvestigationDispatcher);d.store=archive;d.run_id='offline-counter';d._selectable=lambda:True
        grant=dict(protocol_correction_limit=4,protocol_correction_role_limits=dict(principal=4,other=0),protocol_correction_per_node=4,protocol_correction_per_decision=3)
        d._grant=lambda *a:(dict(state=archive.bundle['state']),grant)
        o=SimpleNamespace(investigation_id='same-logical-node',role='principal',budget=SimpleNamespace(model_calls=12))
        def issue(key):
            e=ValueError('DISPOSITION_FACT_BINDING: fixture');e.issue=dict(failure_key='report:'+key,path='/dispositions',reason='offline counterexample');return e
        for _ in range(3):self.assertIsNotNone(d._protocol_feedback(o,issue('immutable-a')))
        self.assertIsNone(d._protocol_feedback(o,issue('immutable-a')))
        self.assertIsNotNone(d._protocol_feedback(o,issue('immutable-b')))
        self.assertEqual(archive.bundle['state']['investigation_protocol_corrections_used'],4)
        self.assertIsNone(d._protocol_feedback(o,issue('immutable-b')))

    def test_response_admission_failure_saves_only_exact_public_code(self):
        from types import SimpleNamespace
        import time
        archive=MemoryArchive(dict(state=dict(investigations={'offline-node':{}}),artifacts={}))
        archive.session=lambda *a,**k:dict(state=archive.bundle['state'],snapshot=dict(input=dict(policy=dict(model={}))))
        d=object.__new__(InvestigationDispatcher);d.store=archive;d.run_id='offline-admission'
        progress=dict(stage='response_evidence_save',valid_report=False,transport_attempted=True,response_received=True)
        row=dict(request_id='unchanged-request',execution_id='unchanged-execution')
        ref,uncertain=d._failure(SimpleNamespace(investigation_id='offline-node'),row,progress,ValueError('INVESTIGATION_RESPONSE_SECRET_TEXT'),time.monotonic())
        self.assertTrue(uncertain)
        self.assertEqual(archive.artifact(ref)['details']['local_error_code'],'INVESTIGATION_RESPONSE_SECRET_TEXT')
        ref,_=d._failure(SimpleNamespace(investigation_id='offline-node'),row,progress,ValueError('private body must never be copied'),time.monotonic())
        self.assertIsNone(archive.artifact(ref)['details']['local_error_code'])
        self.assertNotIn('private body',encode(archive.artifact(ref)))
        routed=classify(ValueError('MODEL_NODE_INCOMPLETE'))
        self.assertEqual(routed['category'],'bounded_stop');self.assertFalse(routed['paid_correction_eligible'])
