"""Observed B1 generation boundaries; no Provider or numerical workers."""
from copy import deepcopy
import json
import unittest
from jsonschema import Draft202012Validator
from extensions.tendon_family import generated_serial
from extensions.tendon_family.family_space import parse_build, resolved_request, decision_summary
from tools.research.agent import plan_schema
from tools.research.config import ROOT, resolve


class GenerationInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_p63b1_sol_m1_traces12.json')
        cls.space=cls.spec['family_space']

    def test_sparse_overrides_inherit_prototypes_without_task_evaluation(self):
        request=dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],
            segment_count=2,tendon_count=4,segments={'0':dict(length_m=.2),'1':dict(length_m=.2)})
        resolved=resolved_request(self.space,request)
        summary=decision_summary(self.space,{},['generate'])['generation_inputs']
        robot,mesh,_=generated_serial.generate_family(parse_build(dict(space=self.space,request=request)))
        parts={p['id']:p for p in self.space['assembly']['components']}
        for i,segment in enumerate(p for p in robot['components'] if p['kind']=='flexible_segment'):
            key='root_segment' if i==0 else 'repeated_segment'
            prototype=parts[self.space['serial_assembly'][key]]
            inherited=resolved['segments'][str(i)]
            self.assertEqual(inherited['sections'],[st['section'] for st in prototype['sections']])
            self.assertEqual(segment['sections'],prototype['sections'])
            self.assertEqual(mesh['cells'][segment['id']],self.space['serial_assembly']['default_cells'])
            self.assertEqual(inherited['cells'],summary['cells']['default'])
            self.assertEqual(summary['sections']['prototypes'][i]['count'],len(prototype['sections']))
        self.assertNotIn('sections',request['segments']['0'])
        self.assertNotIn('cells',request['segments']['0'])

    def test_observed_explicit_overrides_still_fail_original_domain(self):
        audit=json.loads((ROOT/'docs/research/p63b1_sol_audit.json').read_text(encoding='utf8'))
        section_plan=deepcopy(audit['requests'][9]['tool_actions'][0]['input'])
        cell_plan=deepcopy(audit['requests'][10]['tool_actions'][0]['input'])
        schema=plan_schema(['generate'],decision_required=True,focused=True,study=self.spec,
            family_version=self.space['version'])
        validator=Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(section_plan))
        with self.assertRaisesRegex(ValueError,'EXACT_SECTION_STATIONS_REQUIRED'):
            generated_serial.generate_family(parse_build(dict(space=self.space,request=section_plan['generation'])))
        self.assertFalse(validator.is_valid(cell_plan))
        with self.assertRaisesRegex(ValueError,'CELLS_OUTSIDE_FAMILY_DOMAIN'):
            generated_serial.generate_family(parse_build(dict(space=self.space,request=cell_plan['generation'])))


if __name__=='__main__':unittest.main()
