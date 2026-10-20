"""Hash-verified historical construction replay; no Provider or scientific workers."""
from copy import deepcopy
from collections import Counter
import unittest
from tests.research.s8_audit import archive_host
from tests.research.test_s125_contract import cold_host
from tools.research.design import generate_candidate
from tools.research.state import state, update
from tools.research.config import ROOT
from tools.state_io import atomic_json, digest


def replay():
    old,_=archive_host('evidence/s125_cold/study')
    host=cold_host('engineering_numerical');rows=[]
    # Hold the original evaluator/profile binding fixed when checking content.
    # Production correctly assigns a new profile identity after source changes.
    update(host,profile=state(old)['profile'])
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

    def test_symmetric_asymmetric_and_exact_collision_facts(self):
        import numpy as np
        from extensions.tendon_family.generated_serial import generate_family, GeometryFailure
        host=cold_host('engineering_numerical');spec=state(host)['spec']
        request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
            segment_count=2,tendon_count=4)
        build=dict(space=spec['family_space'],request=request)
        robot,_,_=generate_family(build)
        positions=[t['points'][0]['attachment']['position_m'] for t in robot['tendons']]
        radius=spec['family_space']['routing_domains']['radius_m']['default']
        np.testing.assert_allclose(positions,[[0,radius,0],[0,0,radius],[0,-radius,0],[0,0,-radius]],atol=1e-15)
        request['spans']=[dict(last_segment=1,count=4,angular_offsets_rad=[.1,.2,.3,.4])]
        asymmetric,_,_=generate_family(build)
        for j,t in enumerate(asymmetric['tendons']):
            angle=2*np.pi*j/4+.1*(j+1)
            np.testing.assert_allclose(t['points'][0]['attachment']['position_m'],[0,radius*np.cos(angle),radius*np.sin(angle)])
        request['spans'][0]['angular_offsets_rad']=[0,-np.pi/2,0,0]
        with self.assertRaises(GeometryFailure) as caught:generate_family(build)
        d=caught.exception.diagnostic
        self.assertEqual([a['tendon'] for a in d['attachments']],['tendon_0','tendon_1'])
        self.assertEqual(d['station'],dict(part='fixed_base',s=0.))
        a,b=d['attachments'];self.assertEqual(d['actual_distance_m'],float(np.linalg.norm(np.array(a['position_m'])-b['position_m'])))
        self.assertLess(d['actual_distance_m'],d['required_distance_m'])
        output=generate_candidate(host,request,{})
        raw=host.store.artifact(output['diagnostic']['raw_reference'])
        self.assertEqual(raw['diagnostic'],d);self.assertEqual(raw['request'],request)

    def test_structure_feedback_and_research_budget_are_facts(self):
        from tools.research.research_context import context, tool_feedback
        from tools.research.budget import decision_budget
        h=cold_host();s=state(h)
        result=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],tendon_count=4),{})
        before=h.store.remaining();budget=decision_budget(h);current=context(h)
        self.assertEqual(h.store.remaining(),before)
        self.assertEqual(current['candidate_status']['generated_valid'],1)
        self.assertEqual(current['candidate_status']['independent_physical_evaluations'],0)
        self.assertFalse(current['task_accepted'])
        facts=tool_feedback(h,dict(result=result))['new_facts']['structure_facts']
        self.assertEqual(facts['scientific_acceptance'],'unmeasured')
        self.assertFalse(facts['control_source_initialized'])
        self.assertEqual(facts['tendon_count'],4)
        self.assertEqual(budget['provider_budget']['exploration_after_additional_read_requests']['3'],40)
        routes=h.store.artifact(facts['full_routes']['reference'])['resolved_parameters']['tendons']
        self.assertEqual(len(routes),4)


if __name__=='__main__':unittest.main()
