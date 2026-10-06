from copy import deepcopy
from unittest import TestCase
from tools.bound_reporting import ledger,render
from tools.state_io import read
from pathlib import Path

class BoundReportTests(TestCase):
    def setUp(self):
        p=Path(__file__).resolve().parents[1]/'evidence/milestone4_reporting_scientific_20261006/prepared_packet.json'
        self.packet=ledger(read(p)['summary'])
        p=self.packet
        self.report=dict(selected_execution_id=p['selected']['execution_id'],latest_execution_id=p['latest']['execution_id'],
            claims=[],geometry_groups=[dict(structure_identity=s,execution_ids=[r['execution_id'] for r in p['executions'] if r['structure_identity']==s]) for s in sorted({r['structure_identity'] for r in p['executions']})],replications=[dict(source_execution_id=r['original_execution_id'],repeat_execution_id=r['repeated_execution_id']) for r in p['replications']],
            interpretation='One aggregate repeat is recorded; wider repeatability remains unknown.',recommendation='Preserve the stopped scientific campaign.',unresolved=['Causality remains unknown.'])

    def claim(self,eid):
        row=next(r for r in self.packet['executions'] if r['execution_id']==eid)
        return dict(execution_id=eid,metric='terminal_error_m',fact_ref=row['facts']['terminal_error_m'],relation='recorded')

    def test_general_cross_execution_swap(self):
        a,b=self.packet['executions'][:2]
        claim=self.claim(a['execution_id']);claim['fact_ref']=b['facts']['terminal_error_m']
        self.report['claims']=[claim]
        with self.assertRaisesRegex(ValueError,'CROSS_EXECUTION'):render(self.report,self.packet)

    def test_equal_weights_different_structure(self):
        a=next(r for r in self.packet['executions'] if r['execution_id']=='a8382f8a4c6e4ebe921fb72f821b2188')
        b=next(r for r in self.packet['executions'] if r['execution_id']=='91c3ba1b01d6499fb26df8f95409401b')
        self.assertEqual(a['weights'],b['weights'])
        self.report['geometry_groups']=[dict(structure_identity=a['structure_identity'],execution_ids=[b['execution_id']])]
        with self.assertRaisesRegex(ValueError,'GEOMETRY'):render(self.report,self.packet)

    def test_replication_different_run_ids(self):
        render(self.report,self.packet)
        pair=self.packet['replications'][0]
        a,b=[next(r for r in self.packet['executions'] if r['execution_id']==pair[k]) for k in ('original_execution_id','repeated_execution_id')]
        self.assertNotEqual(a['execution_id'],b['execution_id'])
        self.assertEqual(a['scientific_configuration_identity'],b['scientific_configuration_identity'])

    def test_exact_and_rounded_render_and_comparison(self):
        self.report['claims']=[self.claim('a8382f8a4c6e4ebe921fb72f821b2188')]
        output=render(self.report,self.packet)
        self.assertIn('0.008117263030117125',output['rendered']);self.assertIn('0.00811726',output['rendered'])
        claim=self.report['claims'][0];claim['comparison_ref']=self.claim('91c3ba1b01d6499fb26df8f95409401b')['fact_ref'];claim['relation']='less'
        with self.assertRaisesRegex(ValueError,'CONTRADICTORY'):render(self.report,self.packet)
