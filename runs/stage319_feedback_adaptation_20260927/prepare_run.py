"""Freeze the one B execution only after the two-state repair evidence passes."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import atomic_json
HERE=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text(encoding='utf8'))
b=read(HERE/'baseline.json');r=read(HERE/'reintegrate.json')
assert b['input_identity']==r['input_identity']
for row in r['rows']:
    plan=row['plan'];initial=row['candidates']['initial'];delivered=row['candidates']['delivered']
    assert plan['accepted'] and plan['recovery']['selected']
    assert plan['result']['constraint_violation']<=1e-5
    assert delivered['terminal_error_m']<initial['terminal_error_m']
    assert plan['recovery']['first_command_change_n']>0
    if row['label']=='near_fast':assert delivered['terminal_speed_m_s']<initial['terminal_speed_m_s']
inp=read(ROOT/'runs/stage318_parameterized_reach_20260927/B/input.json')
inp['run_id']='stage319-B-reintegrated'
inp['policy']['controller']['parameters']['data']['recipe']['recover_returned_tensions']=True
atomic_json(HERE/'B_input.json',inp)
print('Both frozen cases independently feasible with useful corrections; B input frozen, only recovery recipe enabled.')
