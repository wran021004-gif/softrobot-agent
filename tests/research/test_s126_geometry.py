"""Hash-verified historical construction replay; no Provider or scientific workers."""
from copy import deepcopy
from collections import Counter
import unittest
from tests.research.s8_audit import archive_host
from tests.research.test_s125_contract import cold_host
from tools.research.design import generate_candidate
from tools.research.state import state
from tools.research.config import ROOT
from tools.state_io import atomic_json, digest


def replay():
    old,_=archive_host('evidence/s125_cold/study')
    host=cold_host('engineering_numerical');rows=[]
    for event in old.store.events(old.run_id):
        if event['kind']!='model_original_tool_feedback':continue
        value=old.store.artifact(event['outputs'][0]);use=value['tool_use']
        if use['name']!='research_plan' or use['input'].get('action')!='generate':continue
        feedback=value['result']
        if feedback['status']!='success':continue  # Rejected before reaching generator.
        import json
        saved=json.loads(feedback['content'][0]['text'])
        wrapper=old.store.artifact(saved['wrapper_reference']);original=wrapper['result']
        request=use['input']['generation']
        result=generate_candidate(host,request,dict(origin='s126_offline_replay'))
        row=dict(sequence=event['sequence'],tool_use_id=use['toolUseId'],
            original_reference=event['outputs'][0],request_identity=digest(request),
            original_status=original['status'],status=result['status'],
            original_reason=original.get('reason'),reason=result.get('reason'),
            diagnostic=result.get('diagnostic'))
        assert result['status']==original['status'],row
        assert result.get('reason')==original.get('reason'),row
        if result['candidate']:
            candidate=host.store.artifact(result['candidate']);prior=old.store.artifact(original['candidate'])
            assert candidate['identity']==prior['identity'],row
            assert candidate['scientific_configuration']==prior['scientific_configuration'],row
            assert result['resolved']==original['resolved'],row
            row.update(candidate_identity=candidate['identity'],original_candidate=original['candidate'])
        rows.append(row)
    counts=Counter(r['status'] for r in rows)
    assert len(rows)==19 and counts==dict(generated=9,invalid=10),counts
    assert host.store.remaining()['used']['model_calls']==host.store.remaining()['used']['backend_solves']==0
    return dict(source='evidence/s125_cold/study',requests=rows,counts=dict(counts),
        new_provider_requests=0,new_scientific_executions=0,legal_science_identities_unchanged=True)


class GeometryTests(unittest.TestCase):
    def test_historical_requests(self):
        result=replay()
        atomic_json(ROOT/'evidence/s126_geometry/replay.json',result)


if __name__=='__main__':unittest.main()
