"""Synthetic cache/invalidation regressions; no scientific execution or Provider."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from tools.platform_store import Store
from tools.research.conditions import joint_assessment
from tools.research.session_handoff import feedback_delivery,main_feedback_projection


class RequestQualificationTests(TestCase):
    def test_overlapping_projection_reuses_only_verified_fields(self):
        with TemporaryDirectory() as folder:
            store=Store(Path(folder));ref=store.put_context_checkpoint(dict(obj=dict(ok=True),null=None))
            reads=[];original=store.artifact
            def artifact(reference,**kwargs):
                if kwargs.get('db') is not None:reads.append(kwargs.get('paths'))
                return original(reference,**kwargs)
            with patch.object(store,'artifact',new=artifact),store.read_snapshot():
                self.assertEqual(store.artifact(ref,paths=('obj','absent')),dict(obj=dict(ok=True)))
                self.assertEqual(store.artifact(ref,paths=('obj.ok','absent')),dict(obj=dict(ok=True)))
                self.assertEqual(len(reads),1)
                with self.assertRaisesRegex(ValueError,'JSON_PATH_PROJECTION_REQUIRED'):
                    store.artifact(ref,paths=('obj',),raw=True)
                with closing(store.connect()) as db:
                    with db:db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']))
                with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                    store.artifact(ref,paths=('obj.ok',))
                with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                    store.artifact(ref,paths=())

    def test_baseline_failure_projection_retains_implementation_and_status(self):
        from tools.research.tool_readiness import native_baseline_failures
        with TemporaryDirectory() as folder:
            store=Store(Path(folder));candidate=dict(artifact_id='0'*64,media_type='application/json')
            failure=dict(reason='synthetic baseline failure',scientific_infeasibility=False)
            ref=store.put_context_checkpoint(dict(candidate=candidate,implementation='fixture',status='execution_incomplete',
                native_baseline_failure=failure,unused_trace=list(range(1000))))
            host=SimpleNamespace(store=store,run_id='fixture')
            with patch('tools.research.tool_readiness.state',return_value=dict(analysis_results=[ref],freeze='fixture')):
                self.assertEqual(native_baseline_failures(host,candidate),[dict(reference=ref,**failure)])

    def test_pointer_projection_types_arrays_escaping_and_integrity(self):
        with TemporaryDirectory() as folder:
            store=Store(Path(folder))
            ref=store.put_context_checkpoint({'items':[{'yes':True,'none':None}],'0':'object-key','a/b':{'~':3},'测量':4})
            pointers=['/items/0/yes','/items/0/none','/0','/a~1b/~0','/absent','/测量']
            self.assertEqual(store.artifact(ref,pointers=pointers),
                {'/items/0/yes':True,'/items/0/none':None,'/0':'object-key','/a~1b/~0':3,'/测量':4})
            with closing(store.connect()) as db:
                with db:db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']))
            with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                store.artifact(ref,pointers=['/0'])

    def test_sdk_rotation_and_read_credit_with_current_fixture_authorization(self):
        from tests.research.test_request_boundary_handoff import RequestBoundaryHandoffTests
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        fixture=RequestBoundaryHandoffTests()
        original=fixture.provision
        def provision():
            host=original();approve(host,[REGISTERED_MATHEMATICS_SCOPE]);return host
        with patch.object(fixture,'provision',side_effect=provision):
            fixture.test_rotation_precedes_next_send_without_fabricated_completed_invocation()
            fixture.test_full_read_credit_survives_compact_feedback_handoff()

    def test_scope_state_commit_and_return_copy(self):
        with TemporaryDirectory() as folder:
            store=Store(Path(folder));ref=store.put_context_checkpoint(dict(test='fixture'))
            host=SimpleNamespace(store=store,run_id='fixture')
            current=dict(reads=[],selected=None,spec=dict(task_conditions=['a','b']))
            def build(*args,**kw):return dict(qualified=True,conditions=['a','b'])
            with patch('tools.research.conditions.state',side_effect=lambda h:deepcopy(current)),patch(
                    'tools.research.conditions._joint_assessment',side_effect=build) as compute:
                with store.read_snapshot():
                    result=joint_assessment(host,[ref]);result['conditions'].clear()
                    self.assertEqual(joint_assessment(host,[ref])['conditions'],['a','b'])
                    self.assertEqual(compute.call_count,1)
                    joint_assessment(host,[ref],require_reads=False)
                    joint_assessment(host,[ref,ref])
                    self.assertEqual(compute.call_count,3)
                    current['reads'].append('new formal read')
                    joint_assessment(host,[ref]);self.assertEqual(compute.call_count,4)
                    # A commit from another Store connection invalidates all
                    # request facts even when the scientific state is unchanged.
                    store.put_context_checkpoint(dict(test='another immutable fixture'))
                    joint_assessment(host,[ref]);self.assertEqual(compute.call_count,5)
                joint_assessment(host,[ref]);self.assertEqual(compute.call_count,6)

    def test_last_feedback_is_exact_even_beyond_compact_allowance(self):
        result=dict(toolUseId='last',status='success',content=[dict(text='x'*24000)])
        saved=dict(tool_use=dict(toolUseId='last',name='evidence_read',input=dict(view='fields')),result=result)
        store=SimpleNamespace(events=lambda *a,**k:[dict(kind='model_original_tool_feedback',outputs=['ref'])],
            artifact=lambda *a,**k:deepcopy(saved))
        host=SimpleNamespace(store=store,run_id='fixture')
        with patch('tools.research.session_handoff.state',return_value=dict(spec={})):
            delivered=feedback_delivery(host,['last'],compact=True,exact=True)
        self.assertEqual(delivered['items'][0]['result'],result)
        self.assertEqual(delivered['items'][0]['delivery'],'exact_feedback')
        delivered['items'][0]['tool']='research_analysis'
        with patch('tools.research.object_choices.main_projection',new=lambda host,value:value):
            self.assertEqual(main_feedback_projection(host,delivered),delivered)
