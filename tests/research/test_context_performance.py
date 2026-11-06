"""Projection equivalence, integrity and settled SDK rotation; offline fixtures."""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from tools.platform_store import Store
from tools.research.core import material_dependency_change
from tests.research.test_cross_task_integration import fixture_directory


class ContextPerformanceTests(unittest.TestCase):
    def test_report_status_and_latest_selection_preserve_revision_order_without_raw_history(self):
        from tools.research.reporter import current_reports,entries
        with fixture_directory() as folder:
            store=Store(folder)
            a=store.put_context_checkpoint(dict(interpretation_for=None,interpretation_status='deferred',request=dict(trace=list(range(2000)))))
            b=store.put_context_checkpoint(dict(interpretation_for=None,interpretation_status='deferred',request=dict(trace=['fixture'])))
            rb=store.put_context_checkpoint(dict(interpretation_for=b,interpretation_status='available',request=dict(trace=['B original'])))
            ra=store.put_context_checkpoint(dict(interpretation_for=a,interpretation_status='unavailable',request=dict(trace=['A original'])))
            references=[a,b,rb,ra]
            events=[dict(kind='research_report',outputs=[r]) for r in references]
            host=SimpleNamespace(store=store,run_id='offline-report-history')
            expected=[(ra,store.artifact(ra)),(rb,store.artifact(rb))]
            with patch.object(store,'events',return_value=events),store.read_snapshot():
                self.assertEqual(entries(host),[(r,store.artifact(r)) for r in references])
                self.assertEqual(current_reports(host),expected)
                with patch.object(store,'artifact',wraps=store.artifact) as reads:
                    statuses=current_reports(host,status_only=True)
                    self.assertEqual(statuses,[(r,{k:v[k] for k in ('interpretation_for','interpretation_status')}) for r,v in expected])
                    outer=[c for c in reads.call_args_list if c.kwargs.get('db') is None]
                    self.assertTrue(all(c.kwargs.get('paths')==('interpretation_for','interpretation_status') for c in outer))
                with patch.object(store,'artifact',wraps=store.artifact) as reads:
                    latest=current_reports(host,limit=1)
                    self.assertEqual(latest,expected[-1:])
                    full=[c.args[0] for c in reads.call_args_list if not c.kwargs]
                    self.assertEqual(full,[rb])
                latest[0][1]['request']['trace'].append('mutation')
                self.assertEqual(current_reports(host,limit=1),expected[-1:])
                with closing(store.connect()) as db:
                    db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',a['artifact_id']));db.commit()
                with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                    current_reports(host,status_only=True)

    def test_first_exact_subnode_reads_avoid_full_root_and_keep_copy_isolation(self):
        from tools.research.core import read_evidence
        with fixture_directory() as folder:
            store=Store(folder)
            value={'rows':[{'x':False,'none':None},{'x':2}],
                '0':{'a/b':{'~':[1,2]}},'trace':list(range(2000))}
            ref=store.put_context_checkpoint(value)
            host=SimpleNamespace(store=store,run_id='offline-exact-read')
            queries=[(dict(pointer='/rows/0',view='fields',fields=['x','none']),value['rows'][0]),
                (dict(pointer='/0/a~1b/~0'),[1,2]),
                (dict(pointer='/rows/0/none'),None),
                (dict(pointer='/rows',view='range',start=1,count=1),dict(total=2,start=1,items=[{'x':2}]))]
            with patch('tools.research.core.state',return_value={'spec':{}}),\
                    patch('tools.research.core.protected',return_value=False),store.read_snapshot():
                for query,expected in queries:
                    with self.subTest(query=query),patch.object(store,'artifact',wraps=store.artifact) as reads:
                        actual=read_evidence(host,dict(reference=ref,**query),record_read=False)
                        self.assertEqual(actual,expected)
                        outer=[c for c in reads.call_args_list if c.kwargs.get('db') is None]
                        self.assertEqual([c.kwargs for c in outer],[{'pointers':(query['pointer'],)}])
                actual['items'][0]['x']=-1
                self.assertEqual(read_evidence(host,dict(reference=ref,**queries[-1][0]),record_read=False),queries[-1][1])
                self.assertEqual(store.artifact(ref),value)
                with closing(store.connect()) as db:
                    db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']));db.commit()
                with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                    read_evidence(host,dict(reference=ref,pointer='/rows/0/none'),record_read=False)

    def test_exact_projection_preserves_original_error_navigation_and_index_semantics(self):
        from tools.research.core import read_evidence
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(dict(rows=[dict(x=1),None],acceptance=dict(task_passed=False)))
            original=store.artifact
            def unprojected(reference,**kwargs):
                return {} if kwargs.get('pointers') is not None else original(reference,**kwargs)
            def outcome(query,legacy):
                host=SimpleNamespace(store=store,run_id='offline-navigation')
                with patch.object(store,'artifact',side_effect=unprojected if legacy else original):
                    try:return ('value',read_evidence(host,dict(reference=ref,**query),record_read=False))
                    except (KeyError,IndexError,ValueError) as exc:
                        return (type(exc).__name__,str(exc),getattr(exc,'evidence_navigation',None))
            queries=[dict(pointer='/rows/00/x'),dict(pointer='/rows/2'),dict(pointer='/rows/no-index'),
                dict(pointer='/rows/0/missing'),dict(pointer='/rows/0',view='fields',fields=['x','missing']),
                dict(pointer='/rows/1',view='fields',fields=['x']),dict(pointer='/rows/0',view='range'),
                dict(pointer='/rows',view='range',start=3),dict(pointer='/task_passed'),dict(pointer='rows')]
            with patch('tools.research.core.state',return_value={'spec':{}}),\
                    patch('tools.research.state.state',return_value={'spec':{}}),\
                    patch('tools.research.core.protected',return_value=False),store.read_snapshot():
                for query in queries:
                    with self.subTest(query=query):self.assertEqual(outcome(query,False),outcome(query,True))

    def test_cached_evidence_field_rechecks_integrity_without_copying_unused_root(self):
        from tools.research.core import read_evidence
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(dict(status='computed',trace=list(range(2000))))
            host=SimpleNamespace(store=store,run_id='offline-evidence-cache')
            query=dict(reference=ref,view='fields',fields=['status'])
            with patch('tools.research.core.state',return_value={'spec':{}}),\
                    patch('tools.research.core.protected',return_value=False),store.read_snapshot():
                self.assertEqual(read_evidence(host,query,record_read=False),{'status':'computed'})
                with patch.object(store,'artifact',wraps=store.artifact) as reads:
                    self.assertEqual(read_evidence(host,query,record_read=False),{'status':'computed'})
                    outer=[c for c in reads.call_args_list if c.kwargs.get('db') is None]
                    self.assertEqual(len(outer),1)
                    self.assertEqual(outer[0].kwargs,{'paths':()})
                with closing(store.connect()) as db:
                    db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']));db.commit()
                with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                    read_evidence(host,query,record_read=False)

    def test_full_evidence_has_one_cache_owner_and_derived_view_keeps_verification(self):
        from tools.research.core import read_evidence
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(dict(status='computed',trace=list(range(2000))))
            host=SimpleNamespace(store=store,run_id='offline-evidence-view')
            with patch('tools.research.core.state',return_value={'spec':{}}),\
                    patch('tools.research.core.protected',return_value=False),store.read_snapshot():
                result=read_evidence(host,dict(reference=ref),record_read=False);result['trace'][0]=-1
                self.assertEqual(read_evidence(host,dict(reference=ref),record_read=False)['trace'][0],0)
                self.assertFalse(getattr(host,'_evidence_query_cache',{}))
                with patch('tools.research.task_constraints.mathematical_method_view',return_value={'methods':['offline']}),\
                        patch.object(store,'artifact',wraps=store.artifact) as reads:
                    self.assertEqual(read_evidence(host,dict(reference=ref,view='mathematical_capabilities',pointer='/methods'),record_read=False),['offline'])
                    outer=[c for c in reads.call_args_list if c.kwargs.get('db') is None]
                    self.assertEqual(len(outer),1)
                    self.assertEqual(outer[0].kwargs,{'paths':()})

    def test_mechanism_scope_summary_matches_full_evidence_without_trace_read(self):
        from tools.research.evidence_policy import summarize_evidence,summarize_saved_evidence
        with fixture_directory() as folder:
            store=Store(folder)
            value=dict(operation='mechanism_structure_v1',status='computed',candidate=dict(artifact_id='0'*64),
                scoped_claim=dict(binding=dict(candidate=dict(artifact_id='0'*64),task_identity='task-fixture'),
                    model_identity='model-fixture',numerical_result_pointer='/structure_research',conclusion='diagnostic'),
                structure_research=dict(operation='inspect',records=[dict(trace=list(range(2000)))]))
            ref=store.put_context_checkpoint(value);expected=summarize_evidence(store.artifact(ref),ref)
            original=store.artifact
            def projected(reference,**kwargs):
                self.assertIsNotNone(kwargs.get('paths'),'Scope summary materialized full trace')
                return original(reference,**kwargs)
            with patch.object(store,'artifact',side_effect=projected),store.read_snapshot():
                actual=summarize_saved_evidence(SimpleNamespace(store=store),ref)
            self.assertEqual(actual,expected)

    def test_different_projections_share_verified_parse_and_preserve_original(self):
        with fixture_directory() as folder:
            store=Store(folder)
            value={'status':'computed','obj':{'ok':True,'none':None},'items':[{'x':False}],
                '0':'numeric key','a/b':{'~':3},'trace':[float(i) for i in range(2000)]}
            ref=store.put_context_checkpoint(value)
            original=store.artifact(ref,raw=True)
            with patch('tools.platform_store.hashlib.sha256',wraps=hashlib.sha256) as verify:
                with store.read_snapshot():
                    self.assertEqual(store.artifact(ref,paths=('status',)),{'status':'computed'})
                    self.assertEqual(store.artifact(ref,paths=('obj.none','missing','other')),{'obj':{'none':None}})
                    self.assertEqual(store.artifact(ref,pointers=('/items/0/x','/0','/a~1b/~0','/absent')),
                        {'/items/0/x':False,'/0':'numeric key','/a~1b/~0':3})
                    result=store.artifact(ref,paths=('obj',));result['obj']['ok']=False
                    self.assertTrue(store.artifact(ref,paths=('obj.ok',))['obj']['ok'])
                    self.assertEqual(verify.call_count,1)
                    with self.assertRaisesRegex(ValueError,'JSON_PATH_PROJECTION_REQUIRED'):
                        store.artifact(ref,paths=('obj',),raw=True)
                    with self.assertRaises(KeyError):store.artifact(ref,pointers=('/items/00',))
                    after_validation=verify.call_count
                store.artifact(ref,paths=('status',))
                self.assertEqual(verify.call_count,after_validation+1)
            self.assertEqual(store.artifact(ref),value)
            self.assertEqual(store.artifact(ref,raw=True),original)

    def test_store_io_migration_is_explicit_and_cannot_hide_other_dependency_changes(self):
        old=dict(sources={'tools/platform_store.py':'old','physics.py':'same'},packages={'solver':'1'},declaration={'version':'1'})
        new=deepcopy(old);new['sources']['tools/platform_store.py']='new'
        self.assertTrue(material_dependency_change(old,new))
        self.assertFalse(material_dependency_change(old,new,store_io_only=True))
        for field,value in [('sources',{'tools/platform_store.py':'new','physics.py':'different'}),
                ('sources',{'physics.py':'same'}),('packages',{'solver':'2'}),('declaration',{'version':'2'})]:
            changed={**new,field:value}
            self.assertTrue(material_dependency_change(old,changed,store_io_only=True))
        self.assertTrue(material_dependency_change(None,new,store_io_only=True))

    def test_explicit_writer_transaction_cannot_reuse_verified_projection(self):
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(dict(status='original'))
            with store.read_snapshot():
                self.assertEqual(store.artifact(ref,paths=('status',)),{'status':'original'})
                with closing(store.connect()) as db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']))
                    with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):
                        store.artifact(ref,db=db,paths=('status',))
                    db.rollback()
                self.assertEqual(store.artifact(ref,paths=('status',)),{'status':'original'})

    def test_recent_round_handoff_builds_only_packets_that_can_be_sent(self):
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_phs2d_knowledge_start import fixture
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        from tools.research import agent
        from tools.research.state import state
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            ref=state(h)['family_space_reference']
            with patch('tools.research.agent.credential',return_value='offline-fixture'), patch(
                    'tools.research.agent.decision_packet',wraps=agent.decision_packet) as packet:
                wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),
                    ('evidence_read',dict(reference=ref,view='summary')),None],limit=3)
            self.assertEqual(len(wires),3)
            self.assertEqual(packet.call_count,len(wires))
            self.assertEqual(h.store.remaining()['used']['model_calls'],3)
            for wire in wires:
                packets=[m for m in wire['messages'] if isinstance(m.get('content'),str)
                    and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')]
                self.assertEqual(len(packets),1)
                json.loads(packets[0]['content'].split('\n',1)[1])

    def test_settled_budget_review_precedes_packet_build_and_next_send(self):
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_phs2d_knowledge_start import fixture
        from tests.research.test_research_authorization_preflight import approve
        from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
        from tools.research import agent
        from tools.research.state import state
        original=agent.converse
        async def bounded(*args,**kwargs):
            return await original(*args,**kwargs,pause_exploration_remaining=100)
        with fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            with patch('tools.research.agent.credential',return_value='offline-fixture'), patch(
                    'tools.research.agent.converse',side_effect=bounded), patch(
                    'tools.research.agent.decision_packet',wraps=agent.decision_packet) as packet:
                wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),None],limit=2)
            self.assertEqual(len(wires),1);self.assertEqual(packet.call_count,1)
            events=h.store.events(h.run_id)
            self.assertTrue(any(e['kind']=='request_feedback_boundary' for e in events))
            self.assertTrue(any(e['kind']=='supervisor_pause' for e in events))
            self.assertFalse(any(e['kind']=='session_handoff' and e['status']=='committed' for e in events))
            self.assertIsNone(state(h)['pending'])


if __name__=='__main__':unittest.main()
