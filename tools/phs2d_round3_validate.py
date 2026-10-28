"""Independent-process final validation; all integration uses Study reservations."""
import argparse
import json
from tools.research.phs2d_inverse import context,dynamic_set
from tools.research.state import state


def validate(group,label='P3_real9_E80_full8'):
    h,p=context();v=state(h)['phs']
    if not v.get('ten_case_witness') or v['ten_case_witness']['label']!=label:raise ValueError('TEN_CASE_WITNESS_REQUIRED')
    options={
        'independent':dict(timestep=p['timestep_s'],record=True,replicate=1),
        'half_step':dict(timestep=p['timestep_s']/2,replicate=2),
        'perturbation':dict(timestep=p['timestep_s'],perturbation=.0001,replicate=3)}[group]
    for holdout in (False,True):
        result=dynamic_set(label,holdout=holdout,phase='FINAL',**options)
        print(json.dumps(dict(group=group,**result)),flush=True)
        if not result['all_pass']:raise ValueError('FINAL_VALIDATION_FAILED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('group',choices=['independent','half_step','perturbation']);args=parser.parse_args();validate(args.group)
