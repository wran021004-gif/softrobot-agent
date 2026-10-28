"""Offline disposition admission fixtures; no Provider or science execution."""
import asyncio,json,unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from tools.state_io import digest
from tools.research.session_handoff import inspect_confirmed_incomplete

class IncompleteAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.s={'pilot':{'unconsumed_response':'request','framework_session_id':'old'},'research_status':'ready','freeze':'fixture','pending':None}
        use={'toolUseId':'tool1','name':'research_plan','input':{'action':'generate'}}
        result={'toolUseId':'tool1','status':'success','content':[{'text':'fixture'}]}
        self.agent=SimpleNamespace(_session_manager=SimpleNamespace(session_id='old'),messages=[{'role':'assistant','content':[{'toolUse':use}]},{'role':'user','content':[{'toolResult':result}]}],context_manager=None)
        self.wire={'messages':[{'role':'system','content':'fixture'},{'role':'user','content':'CURRENT_RESEARCH_PACKET\n{\"implementation\":\"fixture\"}'}]}
        self.body={'choices':[{'finish_reason':'length','message':{'tool_calls':[{'id':'partial'}]}}],'usage':{'prompt_tokens':2}}
        self.rec={'body':{'artifact_id':'body'},'http_status':200,'usage':self.body['usage'],'finish_reasons':['length']}
        self.events=[{'kind':'model_original_tool_feedback','sequence':1,'outputs':[{'artifact_id':'feedback'}]}, {'kind':'model_decision_packet','sequence':2,'outputs':[{'artifact_id':'packet'}]}, {'kind':'r3_request','request_id':'request','sequence':3,'outputs':[{'artifact_id':'meta'}]}]
        self.objects={'packet':{'implementation':'fixture'},'feedback':{'tool_use':use,'result':result},'meta':{'purpose':'conversation','request':{'artifact_id':'wire'}},'wire':self.wire,'body':json.dumps(self.body).encode(),'settled':self.rec}
        self.receipt={'request_id':'request','tool_id':'model.deepseek','execution_status':'completed','charged':{'model_calls':1},'output':{'artifact_id':'settled'}}
        self.row={'request_hash':digest(self.wire),'receipt':json.dumps(self.receipt),'execution_id':'exec'}
        self.h=MagicMock();self.h.run_id='fixture';self.h.store.events.side_effect=lambda _:self.events
        self.h.store.artifact.side_effect=lambda r,**kwargs:self.objects[r['artifact_id']]
        self.h.store.lookup.return_value=self.row;self.h.store.remaining.return_value={'used':{'model_calls':1}}
        db=self.h.store.connect.return_value.__enter__.return_value;db.execute.return_value.fetchone.return_value=(0,)
    def inspect(self):
        with patch('tools.research.session_handoff.state',return_value=self.s),patch('tools.research.agent.pending',return_value=[]),patch('tools.research.agent.received',return_value=self.rec),patch('tools.research.agent.DeepSeekModel.format_request_messages',return_value=self.wire['messages'][:1]),patch('tools.research.session_handoff.snapshot_files',return_value={'x':'hash'}):
            return asyncio.run(inspect_confirmed_incomplete(self.h,self.agent,'fixture'))
    def test_confirmed_truncation_is_read_only_and_never_executes_partial(self):
        before=deepcopy(self.s);proof=self.inspect()
        self.assertEqual(proof['finish_reasons'],['length']);self.assertFalse(proof['truncated_tool_fields_executed'])
        self.assertEqual(self.s,before);self.h.store.update_state.assert_not_called()
    def test_complete_response_is_not_discardable(self):
        self.body['choices'][0]['finish_reason']='stop';self.objects['body']=json.dumps(self.body).encode()
        with self.assertRaisesRegex(ValueError,'EXPLICIT_LENGTH_TRUNCATION_REQUIRED'):self.inspect()
    def test_unknown_worker_or_changed_history_refuses(self):
        self.s['pending']={'kind':'fixture'}
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PROVIDER_OR_SCIENTIFIC_WORKER'):self.inspect()
        self.s['pending']=None;self.agent.messages[-1]['content'][0]['toolResult']['content'][0]['text']='altered'
        # Independent Store feedback is unchanged.
        self.objects['feedback']=deepcopy(self.objects['feedback']);self.objects['feedback']['result']['content'][0]['text']='fixture'
        with self.assertRaisesRegex(ValueError,'SDK_OFFLOAD_ORIGINAL_REQUIRED'):self.inspect()
    def test_any_post_send_tool_event_refuses(self):
        self.events.append({'kind':'model_original_tool_request','sequence':4,'outputs':[]})
        with self.assertRaisesRegex(ValueError,'POST_TRUNCATION_TOOL_EXECUTION_NOT_EXCLUDED'):self.inspect()
