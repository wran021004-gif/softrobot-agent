"""Regression of opt-in physical guide holes and payload anchors; no integrations."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from extensions.tendon_family.family_space import parse_space,parse_build
from extensions.tendon_family.generated_serial import generate_family
from tools.platform_store import plain
from tools.state_io import digest
ROOT=Path(__file__).resolve().parents[2]
class PhysicalRoutingAdmissionTests(unittest.TestCase):
 def test_old_space_and_request_serialization_unchanged(self):
  old=json.loads((ROOT/'configs/research/family_space_passive_engineering_v1.json').read_text())
  self.assertEqual(plain(parse_space(old)),old)
  req=dict(version='serial_family_generation_v2',family_space_identity=digest(old),segment_count=1,tendon_count=1)
  value=plain(parse_build(dict(space=old,request=req)))
  self.assertNotIn('terminal_payload_anchor',value['space'])
  self.assertNotIn('guide_hole_positions_m',value['request'])
 def test_new_space_topology_and_payout_scope(self):
  s=parse_space(json.loads((ROOT/'configs/research/family_space_phs2d_admission_20261105_v1.json').read_text()))
  self.assertEqual(s.executable_segment_counts,[9]);self.assertEqual(s.executable_tendon_count_bounds,(4,4))
  self.assertTrue(s.terminal_payload_anchor);self.assertEqual(s.serial_assembly.cell_count_bounds,(8,8))
 def build(self,edit=None,grant=True):
  s=json.loads((ROOT/'configs/research/family_space_phs2d_admission_20261105_v1.json').read_text())
  s['terminal_payload_anchor']=grant
  s=plain(parse_space(s))
  r=dict(version='serial_family_generation_v2',family_space_identity=digest(s),segment_count=9,tendon_count=4,
    guide_hole_positions_m={'guide_1':{'tendon_0_hole':[0.,.007,.006]}})
  if edit:edit(r)
  return generate_family(parse_build(dict(space=s,request=r)))
 def test_explicit_holes_require_opt_in(self):
  with self.assertRaisesRegex(ValueError,'OPT_IN'):self.build(grant=False)
 def test_unknown_or_unused_hole_rejected(self):
  with self.assertRaisesRegex(ValueError,'USED_REAL_HOLE'):
   self.build(lambda r:r['guide_hole_positions_m'].update(unknown={'tendon_0_hole':[0.,.007,.006]}))
 def test_hole_outside_plate_rejected(self):
  with self.assertRaises(ValueError):
   self.build(lambda r:r['guide_hole_positions_m']['guide_1'].update(tendon_0_hole=[0.,1.,1.]))
 def payload_request(self,r,offset):
  r['guide_hole_positions_m']={}
  def point(part,pos,role):return dict(attachment=dict(part=part,s=0.,position_m=pos),role=role)
  r['route_overrides']={0:[point('fixed_base',[0.,.018,0.],'start'),point('payload',offset,'anchor')]}
 def test_payload_anchor_inside_real_envelope(self):
  design,mesh,physics=self.build(lambda r:self.payload_request(r,[0.,.007,.006]))
  self.assertEqual(design['tendons'][0]['points'][-1]['attachment']['part'],'payload')
  self.assertFalse(design['actuators'])
 def test_payload_anchor_outside_real_envelope_rejected(self):
  with self.assertRaisesRegex(ValueError,'INSIDE_REAL_ENVELOPE'):
   self.build(lambda r:self.payload_request(r,[0.,.02,.006]))
if __name__=='__main__':unittest.main()

