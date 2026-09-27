"""One fresh public task process with whole-process timing and acceptance gates."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.state_io import atomic_json,read

def passed(folder):
    if not (folder/'summary.json').exists():return False
    s=read(folder/'summary.json')
    return bool(s['valid_complete_execution'] and s['official_task_success'] and s['sampled_settling']['passed'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label',choices=['B','B_correction','A','live'])
    args=parser.parse_args();label=args.label
    if label in ('A','live') and not (passed(HERE/'B') or passed(HERE/'B_correction')):
        raise ValueError('B reach and sampled settling gate has not passed')
    if label=='live' and not passed(HERE/'A'):raise ValueError('A reach and sampled settling gate has not passed')
    if (HERE/label/'workflow.json').exists():raise ValueError('Use saved evidence; this runner starts fresh executions only')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    inp=HERE/(('B' if label=='live' else label)+'_input.json')
    example='gvs_nmpc_route_experiment.py' if label=='live' else 'gvs_parameterized_reach.py'
    cmd=[sys.executable,str(ROOT/'examples'/example),'run','--input',str(inp),'--output',str(HERE/label)]
    start=time.perf_counter()
    with (HERE/(label+'.log')).open('w',encoding='utf8') as log:
        process=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    atomic_json(HERE/(label+'_process_timing.json'),dict(process_wall_s=time.perf_counter()-start,
        exit_code=process.returncode,command=cmd,scope='Fresh public process including preparation, execution, evaluation and report; live also includes provider decisions'))
    print(json.dumps(dict(label=label,exit_code=process.returncode,passed=passed(HERE/label))),flush=True)
    sys.exit(process.returncode)
