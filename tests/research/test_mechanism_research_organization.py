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
