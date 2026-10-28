"""Capture actual portable viewer/render/replay-recipe checks, without integration."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phs2d_io import TASK_DIR,read,write,sha,require


def checks(package, gui=False):
    results=[]
    def run(script,arguments):
        relative=['scripts/'+script,*arguments]
        command=[sys.executable,'-B',str(package/relative[0]),*relative[1:]]
        process=subprocess.run(command,cwd=package,capture_output=True,text=True,encoding='utf8')
        require(process.returncode==0,'CHECK_FAILED:'+script+'\n'+process.stderr)
        records=[json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
        require(records and all(r['physics_steps']==0 for r in records),'CHECK_MUST_RECORD_ZERO_STEPS')
        results.append(dict(command=['python','-B',*relative],status='passed',results=records))
    preview=TASK_DIR+'/previews/model_preview.png'
    run('view_phs2d.py',['--s','0.70','--direction','negative','--render',preview])
    run('view_phs2d.py',['--s','0.40','--direction','negative','--check-states'])
    run('simulate_phs2d.py',['--s','0.50','--direction','negative','--check-only'])
    if gui:run('view_phs2d.py',['--s','0.50','--direction','positive','--loop','--speed','2','--smoke-seconds','3'])
    current=read(package/'viewer_validation.json')
    legacy=current.get('legacy',current)
    report=dict(version='base_only_viewer_checks_v2',legacy=legacy,
        phs2d=dict(status='passed',checks=results,physics_steps=0,preview_sha256=sha(package/preview),
            environment=dict(python=platform.python_version(),mujoco=mujoco.__version__,numpy=np.__version__,platform=platform.platform()),
            gui_smoke_executed=gui,linux_tested=False,
            script_sha256={p.name:sha(p) for p in (package/'scripts').glob('*phs2d*.py')}))
    write(package/'viewer_validation.json',report)
    print(json.dumps(report['phs2d'],ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True)
    p.add_argument('--gui',action='store_true');args=p.parse_args();checks(args.package.resolve(),args.gui)


if __name__=='__main__':main()
