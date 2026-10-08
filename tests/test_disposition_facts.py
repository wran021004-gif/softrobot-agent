"""Targeted deterministic binding checks. No provider or scientific execution."""
from copy import deepcopy
import json
from unittest import TestCase
from tests import test_research_v1_capacity as fixtures
from tools.disposition_facts import catalog,expand,project,BindingError
from tools.research_investigations import InvestigationReturn,SourceFact
from tools.platform_store import plain,encode
from tools.research_execution import invoke
from tools.investigation_contract import contract
from schemas.platform_operations import ReadEvidence
from schemas.platform import EvidenceRef


class SelectableTests(TestCase):
    setUp=fixtures.CapacityBindingTests.setUp
    cleanup=fixtures.CapacityBindingTests.cleanup

    def setup_report(self):
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            # Select the new wire contract in this explicitly offline fixture.
            cfg=self.host.store.session(self.host.run_id,db)['snapshot']['input']
        result=self.dispatch.dispatch(plain(self.order),transport=lambda wire:fixtures.native(dict(
            facts=[dict(statement='Whole original object',reference=self.ref,pointer='',value=self.source)],
            interpretation='Fixture only; no scientific conclusions.')))
        self.assertEqual(result.status,'completed')
        self.report=plain(result.result)
        receipt=invoke(self.host,'research.investigation_read',dict(reference=self.ref,pointer='',limit=100),request_id='inspect')
        self.assertEqual(receipt['execution_status'],'completed')
        principal=self.order.model_copy(update=dict(investigation_id='principal',role='principal',evidence=[EvidenceRef.model_validate(self.ref),result.result],
            queries=[ReadEvidence(reference=self.report,pointer='',limit=100)]))
        self.dispatch._reserve(plain(principal))
        self.principal=principal
        self.dispatch.prepare(principal,executing=True)
        self.cat,self.body=catalog(self.dispatch,[dict(investigation_id='investigator',report=self.report)],[self.ref])
        self.handle=next(e['handle'] for e in self.body['entries'] if e['origin']=='report')
        self.additional=next(e['handle'] for e in self.body['entries'] if e['origin']=='principal_additional' and e['fact']['pointer']=='/scalar')

    def selection(self,kind='accept'):
        return dict(investigation_id='investigator',report=self.report,catalog=self.cat,catalog_version='1.0.0',disposition=kind,
            reason='Chosen by fixture, not by expansion',adopted_claims=[dict(statement='Original exact scalar',
                supporting_facts=[dict(handle=self.handle,projection='/scalar')],scope=[dict(handle=self.handle,projection='/execution_id')],
                support_explanation='Extraction only; semantics require separate review.')] if kind=='accept' else [])

    def test_deterministic_projection_public_validation_and_reversible_selection(self):
        self.setup_report();s=self.selection();a=expand(self.dispatch,s,self.cat)
        self.assertEqual(encode(plain(a)),encode(plain(expand(self.dispatch,s,self.cat))))
        self.assertEqual(a.adopted_claims[0].supporting_facts[0].value,self.source['scalar'])
        self.assertEqual(a.selection_provenance['model_selection']['adopted_claims'][0]['supporting_facts'][0]['handle'],self.handle)
        record=self.dispatch.disposition(a,validate_only=True)
        self.assertTrue(record['inspection_links']);self.assertEqual(record['semantic_correctness'],'unassessed; structural/source validation does not prove scientific interpretation')
        for field,value in [('value',0),('value',str(self.source['scalar'])),('source_identity',dict(execution_id='wrong'))]:
            broken=plain(a);broken['adopted_claims'][0]['supporting_facts'][0][field]=value
            with self.assertRaises(ValueError):self.dispatch.disposition(broken,validate_only=True)

    def test_ownership_version_unknown_handle_and_invalid_projection(self):
        self.setup_report()
        for field,value in [('investigation_id','wrong'),('catalog_version','2.0.0'),('report',self.ref),('catalog',self.ref)]:
            s=self.selection();s[field]=value
            with self.assertRaises(ValueError):expand(self.dispatch,s,self.cat)
        for selected in [dict(handle='unknown',projection=''),dict(handle=self.handle,projection='/flag/x'),dict(handle=self.handle,projection='/missing')]:
            s=self.selection();s['adopted_claims'][0]['supporting_facts']=[selected]
            with self.assertRaises(BindingError) as raised:expand(self.dispatch,s,self.cat,path='/dispositions/0')
            self.assertEqual(raised.exception.issue['path'],'/dispositions/0/adopted_claims/0/supporting_facts/0')
            self.assertEqual(raised.exception.issue['selection'],selected)
        for p in ('/-1','/01','/~2'):
            with self.assertRaises(ValueError):project([1,2],p)

    def test_additional_evidence_origin_and_all_dispositions(self):
        self.setup_report();s=self.selection()
        s['adopted_claims'][0]['supporting_facts']=[dict(handle=self.additional)]
        with self.assertRaisesRegex(BindingError,'impersonate'):expand(self.dispatch,s,self.cat)
        s=self.selection();s['adopted_claims'][0]['additional_support']=[dict(handle=self.additional)]
        a=expand(self.dispatch,s,self.cat);record=self.dispatch.disposition(a,validate_only=True)
        self.assertEqual(a.selection_provenance['links'][1]['origin'],'principal_additional')
        for kind in ('accept','defer','reject'):
            a=expand(self.dispatch,self.selection(kind),self.cat)
            self.assertEqual(self.dispatch.disposition(a,validate_only=True)['decision']['disposition'],kind)

    def test_wire_schema_strict_parser_and_array_units_preserved(self):
        self.setup_report();c=contract(selectable=True);s=self.selection()
        parsed=c.parse('investigation_return',json.dumps(dict(interpretation='fixture',dispositions=[s])))
        schema=c.tools()[0]['function']['parameters']
        self.assertIn('SelectedDisposition',schema['$defs']);self.assertEqual(parsed.dispositions[0].catalog_version,'1.0.0')
        s['adopted_claims'][0]['supporting_facts'][0]['value']=1
        with self.assertRaises(ValueError):c.parse('investigation_return',json.dumps(dict(interpretation='fixture',dispositions=[s])))
        original=dict(unit='m',values=[0.1,0.2,0.3]);self.assertEqual(project(original,'/values'),original['values'])
        self.assertIs(type(project(dict(flag=False),'/flag')),bool)

    def test_actual_selectable_request_decode_detail_access_and_capacity(self):
        self.setup_report()
        self.dispatch._native_v2=lambda:True;self.dispatch._selectable=lambda:True
        self.dispatch._state('principal',status='running')
        _,wire,_,measurement=self.dispatch.prepare(self.principal,executing=True)
        packet=json.loads(wire['messages'][1]['content']);cat=packet['fact_catalog']
        s=self.selection();s['catalog']=cat['reference']
        parsed=self.dispatch._decode(fixtures.native(dict(interpretation='Fixture principal decision',dispositions=[s])))
        self.dispatch._validate_return(self.principal,parsed,[])
        request=invoke(self.host,'research.investigation_disposition',plain(parsed.dispositions[0]),request_id='formal-selected')
        self.assertEqual(request['execution_status'],'completed')
        page=self.dispatch._query(self.principal,ReadEvidence(reference=cat['reference'],pointer='/entries/0',byte_limit=65536,limit=100))
        self.assertEqual(page['page']['content'],self.host.store.artifact(cat['reference'])['entries'][0])
        self.assertEqual(page['page']['content']['handle'],cat['content']['entries'][0]['handle'])
        self.assertEqual(wire['tools'],contract(selectable=True).tools())
        self.assertEqual(measurement['response_reserve_tokens'],32768)
        from tools.context_assembly import check_outgoing_request
        config=self.host.store.session(self.host.run_id)['snapshot']['input']['policy']['model']
        wire['messages'].append(dict(role='user',content='x'*160000))
        with self.assertRaisesRegex(ValueError,'OVERFLOW'):check_outgoing_request(wire,config,'research_decision')

    def test_cross_execution_binding_and_feedback_keeps_current_evidence(self):
        self.setup_report()
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            state['investigations']['investigator']['request_run_id']='other-execution'
            self.host.store.update_state(db,self.host.run_id,state)
        with self.assertRaisesRegex(BindingError,'execution'):expand(self.dispatch,self.selection(),self.cat)
        self.dispatch._selectable=lambda:True
        original=dict(messages=[dict(role='system',content='rules'),dict(role='user',content=json.dumps(dict(reports=['complete'],counterevidence=['negative'],remaining_budget=dict(model_calls=3)))),
            dict(role='assistant',content=None,reasoning_content='old long thinking',tool_calls=[]),dict(role='tool',tool_call_id='read',content='complete new page')])
        self.dispatch._append_correction(original,dict(tool_calls=[dict(id='failed',function=dict(name='investigation_return',arguments='unchanged invalid selection'))]),'failed',dict(issues=[dict(path='/dispositions/0',reason='wrong handle')]))
        packet=json.loads(original['messages'][1]['content'])
        self.assertEqual(packet['counterevidence'],['negative']);self.assertEqual(packet['remaining_budget']['model_calls'],3)
        self.assertEqual(packet['correction']['retained_tool_results'][0]['content'],'complete new page')
        self.assertNotIn('old long thinking',encode(original));self.assertIn('archive-only',packet['correction']['omitted'])
