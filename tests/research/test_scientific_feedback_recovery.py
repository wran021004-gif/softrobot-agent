"""Saved scientific-intent receipt recovery; all numerical values are fixtures."""
import asyncio,json,unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from tools.platform_store import plain,zero
from tools.state_io import digest
from tools.research.state import state,save,update
from tools.research.contracts import ScientificQuestionV4
from tools.research.session_handoff import recover_feedback,unmatched
from tools.research.object_choices import reference_choices
from tests.research.test_m1_native_search_scope import scoped_fixture


def fixture(h,*,validated=True,wrong_binding=False,raw=False):
    source=save(h,dict(scope='Synthetic control-source fixture; no physics'),'fixture_source')
    alias=next(k for k,v in reference_choices(h,include_all=True).items() if v==source)
    payload=dict(version='scientific_question_v4',domain='control',control=dict(question_type='control_feasibility',
        effect_semantics='reoptimized_task_capability',source_selection=dict(control_source=alias),
        control_search_effort=dict(method='pattern',evaluation_requests=1000,knot_count=8,iterations=200)))
    expanded=deepcopy(payload);expanded['control']['source_selection']['control_source']=source
    query=dict(operation='mujoco_direct_control_v1',candidate=source,model_source='mujoco',
        control_optimization=dict(source=source,settings=dict(iterations=200,evaluation_requests=1000)))
    if raw:payload=deepcopy(query)
    use=dict(toolUseId='fixture-scientific-call',name='research_analysis',input=payload)
    save(h,dict(tool_use=use),'model_original_tool_request')
    if not raw:
        bound=deepcopy(query)
        if wrong_binding:bound['operation']='native_dynamics_v1'
        binding=save(h,dict(tool_use_id=use['toolUseId'],raw_main_input=expanded,full_request=bound,
            provider_schema=ScientificQuestionV4.model_json_schema()),'analysis_request_binding')
        if validated:save(h,dict(binding=binding,json_schema_valid=True,pydantic_valid=True),'analysis_request_binding_validated')
    result=dict(status='incomplete',operation=query['operation'],candidate=source,requested_operation=query,
        task_acceptance='unmeasured',scope='Synthetic interrupted calculation; never executed')
    row,_=h.store.reserve(h.run_id,'native-'+use['toolUseId']+'-analysis',digest(query),h.actor,zero())
    h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
        tool_id='research.candidate_analysis',tool_version='1.0.0',execution_status='completed',charged=zero()),result)
    session=state(h)['pilot']['framework_session_id']
    agent=SimpleNamespace(messages=[dict(role='assistant',content=[dict(toolUse=use)])],
        _session_manager=SimpleNamespace(session_id=session,save_snapshot=AsyncMock()))
    return agent,use


class ScientificFeedbackRecoveryTests(unittest.TestCase):
    def exercise(self,**changes):
        with scoped_fixture() as h:
            agent,use=fixture(h,**changes);ledger=h.store.remaining();before=deepcopy(state(h))
            with (patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')),
                 patch('tools.research.research_context.tool_feedback',side_effect=lambda _h,v:v),
                 patch('tools.research.reporter.scientific_feedback',return_value=None)):
                count=asyncio.run(recover_feedback(h,agent))
                self.assertEqual(count,1);self.assertFalse(unmatched(agent.messages))
                self.assertEqual(asyncio.run(recover_feedback(h,agent)),0)
            self.assertEqual(h.store.remaining(),ledger);self.assertEqual(state(h),before)
            result=agent.messages[-1]['content'][0]['toolResult']
            self.assertEqual(result['toolUseId'],use['toolUseId'])
            self.assertEqual(json.loads(result['content'][0]['text'])['status'],'incomplete')
            agent._session_manager.save_snapshot.assert_awaited_once()

    def test_saved_scientific_question_and_alias_binding_restore_without_execution(self):self.exercise()

    def test_legacy_full_request_recovery_is_unchanged(self):self.exercise(raw=True)

    def test_missing_validation_or_conflicting_bound_request_fails_closed(self):
        for changes in (dict(validated=False),dict(wrong_binding=True)):
            with self.subTest(changes=changes),scoped_fixture() as h:
                agent,_=fixture(h,**changes);ledger=h.store.remaining()
                with self.assertRaisesRegex(ValueError,'ORIGINAL_TOOL_IDENTITY_MISMATCH'):
                    asyncio.run(recover_feedback(h,agent))
                self.assertEqual(h.store.remaining(),ledger);self.assertTrue(unmatched(agent.messages))

    def test_changed_scientific_intent_is_not_accepted_as_saved_binding(self):
        with scoped_fixture() as h:
            agent,use=fixture(h)
            use['input']['control']['control_search_effort']['knot_count']=9
            # An independently saved original request cannot change the binding.
            save(h,dict(tool_use=use),'model_original_tool_request')
            with self.assertRaisesRegex(ValueError,'ORIGINAL_TOOL_IDENTITY_MISMATCH'):
                asyncio.run(recover_feedback(h,agent))


if __name__=='__main__':unittest.main()
