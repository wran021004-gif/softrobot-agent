"""Only the new cross-session provenance/compatibility boundary."""
import copy
import unittest
from uuid import uuid4
from unittest.mock import patch
from examples.platform_fixtures import reference_input,project
from tools.platform_host import Host
from tools.platform_store import Store
from tools.spec_tools import ROOT

class SavedEvaluationTests(unittest.TestCase):
    def test_public_saved_evaluation_keeps_producer_and_checks_context(self):
        root=ROOT/'runs/saved_evaluation_tests'/uuid4().hex
        db=Store(root);db.create(project());raw=reference_input('producer')
        producer=Host(root,'producer');producer.create(raw)
        sim=producer.invoke(dict(request_id='simulate',tool_id='simulation.run',arguments={},reason='Reference fixture'))
        self.assertEqual(sim['execution_status'],'completed')
        before=db.session('producer')['snapshot']
        value=copy.deepcopy(raw);value['run_id']='reader'
        value['policy'].update(allowed_tools=['evaluation.saved'],tool_bindings={'evaluation.saved':'1.0.0'})
        reader=Host(root,'reader');reader.create(value)
        request=dict(request_id='evaluate',tool_id='evaluation.saved',arguments=dict(source_run_id='producer',
            execution_id=sim['execution_id'],result=sim['output']),reason='Original evaluator on sealed evidence')
        result=reader.invoke(request)
        self.assertEqual(result['execution_status'],'completed',result)
        self.assertEqual(result['charged']['backend_solves'],0)
        self.assertEqual(db.artifact(result['output'])['source_execution_id'],sim['execution_id'])
        self.assertEqual(db.session('producer')['snapshot'],before)
        value['run_id']='different-task';value['task']['goal']['data']['length_m']=.32
        mismatch=Host(root,'different-task');mismatch.create(value)
        self.assertIn('CONTEXT_MISMATCH',mismatch.invoke(request)['error'])
        with patch.object(Host,'compatibility',autospec=True,side_effect=lambda h:dict(
                compatible=h.run_id!='producer',changed=['backend.reference@1.0.0'])):
            rejected=reader.invoke({**request,'request_id':'changed-source'})
        self.assertIn('SOURCE_DEPENDENCIES_CHANGED',rejected['error'])

if __name__=='__main__':unittest.main()
