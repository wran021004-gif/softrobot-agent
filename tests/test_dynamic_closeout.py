"""One focused selection persistence/display check; no model or numerical workers."""
import contextlib
import copy
import io
import time
import unittest
import uuid
from unittest.mock import patch

from schemas.dynamic_workbench import Stop
from tools.dynamic_campaign import DynamicCampaign
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, digest, read


class SelectedDesignCheck(unittest.TestCase):
    def test_selected_id_persists_and_displays_existing_path(self):
        root=ROOT/'runs/round9_closeout_tests'/uuid.uuid4().hex
        book=DynamicCampaign.__new__(DynamicCampaign);book.root=root;book.tick=time.monotonic()
        current=read(ROOT/'runs/round9_reach/state.json')
        book.state=copy.deepcopy(current)
        book.state.pop('experiment',None)
        book.state.update(decisions=[],attempts=[],model_calls=[],verified_diagnoses=[],status='PAUSED',evidence={})
        candidate=copy.deepcopy(next(c for c in current['candidates'] if c['candidate_id']=='c071'))
        identity={'design':{'fixture_only':True},'control':{}}
        candidate['identity_hash']=digest(identity)
        book.state['candidates']=[candidate]
        atomic_json(root/candidate['path'],identity);book.register(root/candidate['path'])
        book.ledger=read(ROOT/'runs/round9_budget.json')
        book.ledger.update(entries=[],used={k:0 for k in book.ledger['limits']})
        book.decision_origin='deepseek_api'
        reason='I select c071 because its verified result meets the frozen target.'
        with patch('tools.dynamic_campaign.LEDGER',root/'ledger.json'):
            result,ref=book.submit('stop_design',Stop(selected_candidate_id='c071').model_dump(),reason,[candidate['path']])
            self.assertEqual(result['data']['selected_candidate_id'],'c071')
            self.assertEqual(read(root/ref)['data']['selected_candidate_id'],'c071')
            book.state=read(root/'state.json');book.render()
            selection=book.selected_design()
            self.assertEqual(selection['design_file'],str((root/candidate['path']).resolve()))
            output=io.StringIO()
            with contextlib.redirect_stdout(output):book.print_selected_design()
            for text in ('Selected candidate: c071','Design file: '+selection['design_file'],'Reason: '+reason):
                self.assertIn(text,output.getvalue())
                self.assertIn(text,(root/'index.html').read_text(encoding='utf8'))
            result,_=book.submit('stop_design',{'selected_candidate_id':None},'No design can be selected.',[candidate['path']])
            self.assertIsNone(result['data']['selected_candidate_id'])
            self.assertIsNone(book.selected_design()['design_file'])
            self.assertIsNone(Stop().selected_candidate_id)

        # The actual stopped campaign was annotated from its saved LLM words,
        # not by selecting the historical minimum-error candidate.
        book.root=ROOT/'runs/round9_reach';book.state=current
        selected=book.selected_design()
        expected=(book.root/'candidates/c071/candidate.json').resolve()
        self.assertEqual(selected['selected_candidate_id'],'c071')
        self.assertEqual(selected['design_file'],str(expected));self.assertTrue(expected.is_file())
        decision=next(d for d in current['decisions'] if d['sequence']==84)
        self.assertIn(selected['reason'],decision['reason'])
        self.assertIn('model_calls/061/response.json',selected['source'])
        self.assertEqual(current['status'],'STOPPED')
        page=(book.root/'index.html').read_text(encoding='utf8')
        self.assertIn('Selected candidate: c071',page)
        self.assertIn(str(expected),page)
        self.assertIn('Historical best: c066',page)


if __name__=='__main__':unittest.main()
