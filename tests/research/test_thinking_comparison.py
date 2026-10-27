"""Read-only paired-wire and source-identity fixtures; no model/science calls."""
from copy import deepcopy
import json,unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from tools.research.decision_comparison import nonthinking_wire,comparison_budget,validate_proposals
from tools.research.agent import plan_schema

class ThinkingComparisonTests(unittest.TestCase):
    def setUp(self):
        self.ref={'artifact_id':'a'*64,'media_type':'application/json'}
        self.packet={'research':{'actions':['initialize_control','stop']},'candidates':[self.ref]}
        self.wire={'model':'deepseek-flash','thinking':{'type':'enabled'},'reasoning_effort':'high','max_tokens':32768,'stream':False,
            'messages':[{'role':'system','content':'fixture'},{'role':'user','content':'fixture'}],
            'tools':[{'type':'function','function':{'name':'research_plan','description':'fixture',
                'parameters':plan_schema(['initialize_control','stop'],decision_required=True,family_version='serial_family_space_v3')}}]}
    def call(self,candidate=None):
        ref=candidate or self.ref
        plan=dict(action='initialize_control',control_seed=dict(candidate=ref,tensions_n=[[.2,.2,.2]]),
            decision=dict(research_intent='CONTROL_SEARCH',selected_candidate=ref,selected_method='baseline',hypothesis_id='h'),
            hypothesis='h',expected_observation='e',weakening_observation='w',fixed_conditions='f',stopping_condition='s',interpretation='i')
        return {'choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[{'id':'fixture','type':'function',
            'function':{'name':'research_plan','arguments':json.dumps(plan)}}]}}]}
    def test_only_mode_fields_change(self):
        original=deepcopy(self.wire);other=nonthinking_wire(original)
        self.assertEqual(other['thinking'],{'type':'disabled'});self.assertNotIn('reasoning_effort',other)
        self.assertEqual({k:v for k,v in other.items() if k not in ('thinking','reasoning_effort')},
            {k:v for k,v in original.items() if k not in ('thinking','reasoning_effort')})
        self.assertEqual(original,self.wire)
    def test_independent_budget_fails_closed_even_when_arithmetic_fits(self):
        store=MagicMock();store.remaining.return_value={'remaining':{'model_calls':3}}
        store.session.return_value={'state':{'spec':{'budgets':{'protected_provider_requests':2}}}}
        result=comparison_budget(SimpleNamespace(store=store,run_id='fixture'),aggregate_used=5)
        self.assertTrue(result['arithmetic_fits']);self.assertFalse(result['admitted'])
        store.reserve.assert_not_called();store.transaction.assert_not_called()
    def test_proposals_are_validated_without_dispatch(self):
        result=validate_proposals(self.wire,self.packet,self.call())
        self.assertEqual(result['proposals'][0]['status'],'contract_and_visible_references_valid')
        self.assertEqual(result['proposals'][0]['action'],'initialize_control')
        missing={'artifact_id':'b'*64,'media_type':'application/json'}
        self.assertEqual(validate_proposals(self.wire,self.packet,self.call(missing))['proposals'][0]['status'],'rejected')
        self.assertEqual(validate_proposals(self.wire,self.packet,{'choices':[{'finish_reason':'length','message':{}}]})['status'],'incomplete')
    def test_single_row_hint_preserves_complete_sequence_contract(self):
        from tools.research.contracts import ControlSeedRequest
        one=ControlSeedRequest(candidate=self.ref,tensions_n=[[.2,.3,.4]])
        many=ControlSeedRequest(candidate=self.ref,tensions_n=[[.2,.3,.4],[.4,.5,.6]])
        self.assertEqual(len(one.tensions_n),1);self.assertEqual(len(many.tensions_n),2)
        desc=ControlSeedRequest.model_json_schema()['properties']['tensions_n']['description']
        self.assertIn('one bounded tendon-order row',desc)

    def test_freeze_checks_original_receipt_packet_and_clean_history(self):
        from tools.research.decision_comparison import freeze_original
        from tools.state_io import digest
        from unittest.mock import patch
        packet={'study_id':'fixture','research':{'candidate_status':{'control_sources_initialized':0}}}
        wire=deepcopy(self.wire);wire['messages']=[{'role':'system','content':'fixture'},
            {'role':'user','content':'CURRENT_RESEARCH_PACKET\n'+json.dumps(packet)}]
        body={'choices':[{'finish_reason':'tool_calls','message':{}}],'usage':{'prompt_tokens':10}}
        rec={'body':{'artifact_id':'body'},'http_status':200,'usage':body['usage'],'elapsed_s':1}
        receipt={'charged':{'model_calls':1},'output':{'artifact_id':'settled'}}
        row={'receipt':json.dumps(receipt),'request_hash':digest(wire),'execution_id':'execution'}
        events=[{'kind':'model_decision_packet','sequence':1,'outputs':[{'artifact_id':'packet'}]},
            {'kind':'r3_request','sequence':2,'request_id':'id','outputs':[{'artifact_id':'meta'}]}]
        values={'packet':packet,'meta':{'request':{'artifact_id':'wire'}},'wire':wire,'settled':rec,'body':json.dumps(body).encode()}
        store=MagicMock();store.events.return_value=events;store.lookup.return_value=row
        store.artifact.side_effect=lambda r,**kwargs:values[r['artifact_id']]
        h=SimpleNamespace(store=store,run_id='fixture')
        with patch('tools.research.decision_comparison.received',return_value=rec):
            result=freeze_original(h,'id');self.assertEqual(result['original_request_identity'],digest(wire))
            store.transaction.assert_not_called();store.reserve.assert_not_called()
            values['packet']={'study_id':'different'}
            with self.assertRaisesRegex(ValueError,'ORIGINAL_DECISION_PACKET_MISMATCH'):freeze_original(h,'id')

    def test_pending_feedback_seed_import_cannot_run_at_bind_without_approval(self):
        import gc,shutil
        from uuid import uuid4
        from unittest.mock import patch
        from tools.research import core
        from tools.research.config import ROOT,resolve
        from tools.research.state import state
        from tools.research.agent import session_storage_path
        folder=ROOT/'runs'/('p2-pending-fixture-'+uuid4().hex[:8])
        spec=deepcopy(resolve(ROOT/'configs/research/study_p2_feedback_pending.json'))
        spec['study_id']=folder.name;spec['configuration']['run_id']=folder.name
        try:
            with patch('tools.research.config.resolve',return_value=spec):h=core.prepare(directory=folder)
            with patch('tools.research.core.subprocess.check_output',return_value=''):
                with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED'):
                    core.bind(h)
            self.assertFalse(state(h)['candidates']);self.assertNotIn('freeze',state(h))
            self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        finally:
            gc.collect();shutil.rmtree(session_storage_path(folder),ignore_errors=True)
