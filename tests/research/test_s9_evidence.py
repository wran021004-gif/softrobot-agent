"""S8 pointer failure patterns, immutable previews and protected reads; offline only."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from tools.research.core import read_evidence
from tools.research.research_context import compact_evidence, context
from tools.state_io import digest

REF=dict(artifact_id='a'*64,media_type='application/json')


class EvidenceTests(unittest.TestCase):
    def read(self,value,**query):
        host=Mock();host.store.artifact.return_value=value
        with patch('tools.research.core.state',return_value={}),patch('tools.research.core.protected',return_value=False):
            return read_evidence(host,dict(reference=REF,**query))

    def test_s8_false_display_and_result_paths_are_rejected(self):
        for pointer in ('/value/best','/proposals','/evaluations','/samples'):
            with self.subTest(pointer=pointer),self.assertRaises(KeyError):
                self.read(dict(best={},candidates=[]),pointer=pointer)

    def test_actual_pointer_and_field_names_survive_preview(self):
        value={'a/b':{'~key':list(range(8))},'best':{'task_gap':{}},'candidates':[]}
        original=digest(value);summary=compact_evidence(value,REF)
        path=summary['value']['a/b']['~key']['read_pointer']
        self.assertEqual(self.read(value,pointer=path),list(range(8)))
        self.assertEqual(summary['summary']['small_query']['fields'],['task_gap'])
        self.assertEqual(digest(value),original)

    def test_invalid_fields_range_and_indices(self):
        for pointer in ('/rows/-1','/rows/8','/rows/not-an-index'):
            with self.subTest(pointer=pointer),self.assertRaises(IndexError):
                self.read({'rows':[1,2]},pointer=pointer)
        with self.assertRaises(KeyError):self.read({'best':{}},view='fields',fields=['display_field'])
        with self.assertRaisesRegex(ValueError,'FIELDS_REQUIRES'):self.read([1],view='fields',fields=['x'])
        with self.assertRaisesRegex(ValueError,'RANGE_REQUIRES'):self.read({},view='range')
        with self.assertRaisesRegex(ValueError,'START_OUTSIDE'):self.read([1],view='range',start=2)
        with self.assertRaisesRegex(ValueError,'INVALID_EVIDENCE_POINTER'):self.read({},pointer='best')

    def test_synthetic_key_preview_never_advertises_synthetic_paths(self):
        raw=dict(rows=[dict(a=1,b=2,c=3,d=4,e=5)]*8,best=None,candidates=[])
        view=compact_evidence(raw,REF)
        item=view['value']['rows']['preview'][0]
        self.assertIsInstance(item['keys'],list)
        self.assertEqual(self.read(raw,pointer=item['read_pointer']),raw['rows'][0])
        self.assertIsNone(self.read(raw,**view['summary']['small_query']))

    def test_protected_read_rejected_before_traversal(self):
        host=Mock();host.store.artifact.return_value={}
        with patch('tools.research.core.state',return_value={}),patch('tools.research.core.protected',return_value=True),patch('tools.research.core.readable_results',return_value=[]):
            with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE_READ'):
                read_evidence(host,dict(reference=REF,pointer='/missing'))

    def test_physical_task_facts_precede_large_outputs(self):
        from tools.research.numerics import archived
        from tools.state_io import read
        from tools.research.config import ROOT
        package=read(ROOT/'evidence/s8_variant/study/design_package.json')
        value=archived('evidence/s8_variant/study',package['evaluation'])
        original=digest(value);summary=compact_evidence(value,package['evaluation'])
        self.assertFalse(summary['summary']['task_gap']['accepted'])
        self.assertAlmostEqual(summary['summary']['task_gap']['normalized_gap'],.11786172695770314)
        self.assertFalse(summary['summary']['constraints']['holding_speed']['passed'])
        self.assertEqual(digest(value),original)

    def test_complete_stop_index_includes_non_observation_results(self):
        # Test the common context assembly independently of numerical workers.
        s=dict(spec={},research_status='stopped',mechanics_results=[REF],analysis_results=[dict(REF,artifact_id='b'*64)])
        current=dict(actions=[],method_remaining={},control_search_starts=[])
        host=Mock();host.store.remaining.return_value={'remaining':{'backend_solves':0}}
        with patch('tools.research.research_context.state',return_value=s),patch('tools.research.research_context.legacy_context',return_value=current),patch('tools.research.research_context.action_feedback',return_value=[]):
            view=context(host)
        self.assertEqual(view['all_fresh_results'],[REF,dict(REF,artifact_id='b'*64)])

    def test_saved_s8_pointer_errors_remain_strictly_rejected(self):
        import json,tarfile,hashlib
        from tools.research.config import ROOT
        checked=0
        for name in ('variant','mirror'):
            with tarfile.open(ROOT/('evidence/s8_'+name+'/study/immutable_artifacts.tar.gz')) as archive:
                values={}
                for member in archive.getmembers():
                    if not member.name.endswith('.json'):continue
                    body=archive.extractfile(member).read();key=member.name.split('/')[-1][:-5]
                    self.assertEqual(hashlib.sha256(body).hexdigest(),key);values[key]=json.loads(body)
            snapshot=next(v for v in values.values() if isinstance(v,dict) and 'events' in v and 'calls' in v)
            for event in snapshot['events']:
                if event['kind']!='model_original_tool_feedback':continue
                feedback=values[event['outputs'][0]['artifact_id']]
                if feedback['result']['status']!='error':continue
                try:old=json.loads(''.join(c.get('text','') for c in feedback['result']['content']))
                except ValueError:continue
                if old.get('error_code') not in ('INVALID_EVIDENCE_POINTER','EVIDENCE_RANGE_REQUIRES_LIST_POINTER'):continue
                query=feedback['tool_use']['input'];value=values[query['reference']['artifact_id']]
                with self.assertRaises((KeyError,IndexError,ValueError,TypeError)):
                    self.read(value,**{k:v for k,v in query.items() if k!='reference'})
                checked+=1
        self.assertGreaterEqual(checked,10)


if __name__=='__main__':unittest.main()
