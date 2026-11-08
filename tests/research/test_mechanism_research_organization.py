"""Focused offline organization checks; synthetic observations are not science."""
from copy import deepcopy
import json
import unittest
from tools.research import experience
from tools.research.config import ROOT
from tools.research.evidence_views import task_diagnosis
from tools.research.state import state,update
from tests.research.test_organized_knowledge import organized_host


class OrganizationTests(unittest.TestCase):
    def test_mechanism_priority_tracks_observations_and_ignores_cost_only_changes(self):
        from tools.research.reporter import interpretation_priority
        card=dict(identity=dict(result=dict(reference=dict(artifact_id='a'*64)),operation='mechanism_structure_v1',
                task_identity='metadata-only-fixture',candidate='same-fixture-candidate'),
            evidence_summary=dict(verification_status='computed'),metrics=[],main_violations=[],mathematics=dict(fixture=True),
            deterministic_summary=dict(structure_research=dict(operation='inspect',effect_semantics='mechanism_effect',
                target='constraint_active_set',constraint_state=dict(active_count=4,slack_count=0,LICQ=False),
                baseline=dict(norm=2.),cost=dict(kernel_wall_s=1.))))
        old=[dict(mode='automatic',results=[card])]
        changed=deepcopy(card);changed['identity']['result']['reference']['artifact_id']='b'*64
        changed['deterministic_summary']['structure_research'].update(
            constraint_state=dict(active_count=0,slack_count=4,LICQ=True),baseline=dict(norm=0.))
        self.assertEqual(interpretation_priority(dict(mode='automatic',results=[changed]),old,decision_v3=True),'new_mechanism_observation')
        changed=deepcopy(card);changed['identity']['candidate']='new-fixture-candidate'
        self.assertEqual(interpretation_priority(dict(mode='automatic',results=[changed]),old,decision_v3=True),'new_mechanism_observation')
        repeat=deepcopy(card);repeat['identity']['result']['reference']['artifact_id']='c'*64
        repeat['deterministic_summary']['structure_research']['cost']['kernel_wall_s']=2.
        self.assertEqual(interpretation_priority(dict(mode='automatic',results=[repeat]),old,decision_v3=True),'routine_or_repeated_result')

    def test_main_information_flow_retains_recorded_corrections(self):
        from tools.research.research_context import information_flow_brief
        correction=dict(source=dict(artifact_id='b'*64,media_type='application/json'),
            route_qualifications=[dict(first_issue=dict(time_s=0.,pose=0),meaning='Metadata-only regression fixture')])
        brief=dict(recorded_evidence_corrections=correction)
        view=information_flow_brief(brief,dict(budget={}))
        self.assertEqual(view['recorded_evidence_corrections'],correction)
        view['recorded_evidence_corrections']['route_qualifications'][0]['first_issue']['time_s']=1.
        self.assertEqual(brief['recorded_evidence_corrections']['route_qualifications'][0]['first_issue']['time_s'],0.)

    def test_route_failure_preserves_zero_time_unknowns_and_exact_raw_source(self):
        ref=dict(artifact_id='b'*64,media_type='application/json')
        issue=dict(time_s=0.0,pose=0,tendon=0,span=3,body='payload',reason='cable_solid_intersection',interval=[.84,1.])
        raw=dict(structure_research=dict(baseline=dict(task_gap=dict(constraints=[],valid_complete=False)),
            records=[dict(mechanics=dict(dynamic_execution=dict(episodes=[
                dict(load_condition='load_a',route_geometry=dict(status='illegal',checked_poses=801,first_issue=issue)),
                dict(load_condition='load_b',route_geometry=dict(status='unknown',first_issue=None))])))]))
        original=deepcopy(raw);view=task_diagnosis(raw,ref)
        self.assertFalse(view['valid_complete'])
        self.assertEqual(view['route_geometry'][0]['first_issue'],issue)
        self.assertEqual(view['route_geometry'][0]['source'],dict(reference=ref,
            pointer='/structure_research/records/0/mechanics/dynamic_execution/episodes/0/route_geometry'))
        self.assertIsNone(view['route_geometry'][1]['first_issue'])
        self.assertEqual(raw,original)

    def test_diagnosis_keeps_components_small_failures_unknown_times_and_sources(self):
        ref=dict(artifact_id='a'*64,media_type='application/json')
        rows=[dict(constraint_id=k,condition_id='condition',signal=s,observed_value=v,
            bound=b,bound_type=t,unit=u,normalized_violation=g,passed=p,time_window=[1.,2.])
            for k,s,v,b,t,u,g,p in [
                ('point','material_displacement',.001,.01,'lower','m',.9,False),
                ('tip','tip_displacement',.00500001,.005,'upper','m',.000002,False),
                ('ratio','displacement_ratio',5.,.3,'upper','1',15.666,False),
                ('unknown','unrecorded',None,None,'upper',None,None,None)]]
        raw=dict(structure_research=dict(baseline=dict(task_gap=dict(constraints=rows,
            valid_complete=True,comparable=True,signed_task_gap=15.666))))
        original=deepcopy(raw);view=task_diagnosis(raw,ref)
        condition=view['conditions'][0]
        self.assertEqual(condition['failed_constraint_count'],3)
        self.assertEqual(condition['unknown_constraint_count'],1)
        self.assertEqual([r['signal'] for r in condition['observations']],
            ['material_displacement','tip_displacement','displacement_ratio','unrecorded'])
        self.assertIsNone(condition['observations'][0]['time_s'])
        self.assertEqual(condition['observations'][1]['source']['pointer'],
            '/structure_research/baseline/task_gap/constraints/1')
        self.assertEqual(raw,original)

    def test_exact_new_skill_and_process_reads_preserve_old_revisions_without_credit(self):
        with organized_host() as h:
            spec=deepcopy(state(h)['spec']);policy=spec['knowledge']
            ids=['skill-parameter-model','skill-matched-comparison','skill-local-to-experiment',
                'mechanism-research-process','general-material-inertia','general-routing']
            policy['include_entry_ids']=list(dict.fromkeys(policy['include_entry_ids']+ids))
            policy['include_entry_revisions'].update({k:['3'] for k in ids[:3]})
            policy['include_entry_revisions'].update({'mechanism-research-process':['1'],
                'general-material-inertia':['2'],'general-routing':['2']})
            spec['knowledge_manifest']=experience.freeze_knowledge(policy);update(h,spec=spec)
            before=deepcopy(state(h)['analysis_results'])
            for key in ids:
                revision='3' if key.startswith('skill-') else '1' if key=='mechanism-research-process' else '2'
                receipt=experience.retrieve(h,dict(operation='read',entry_id=key,revision=revision))
                saved=h.store.artifact(receipt['reference'])
                self.assertEqual(saved['results'][0]['content']['revision'],revision)
            self.assertEqual(state(h)['analysis_results'],before)
            legacy=json.loads((ROOT/'memory/knowledge/research_organized_v2.json').read_text())['entries']
            self.assertEqual(legacy['skill-parameter-model']['revision'],'2')
            self.assertIn('skip irrelevant stages',legacy['mechanism-research-process']['decision_ownership'])


if __name__=='__main__':unittest.main()
