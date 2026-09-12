"""Explicit development validation and exactly-once full regression accounting."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['real','full-suite','analyze']);parser.add_argument('path',nargs='?')
    args=parser.parse_args()
    from tools.closeout_validation import validate_real,analyze_saved,reserve
    from tools.closeout_state import atomic_json
    from tools.spec_tools import ROOT
    if args.mode=='real':validate_real();return
    if args.mode=='analyze':analyze_saved(args.path);return
    reserve('full_suite','Only full regression in this closeout, real MATLAB enabled')
    import os,unittest,time
    os.environ['SOFTROBOT_TEST_MATLAB']='1'
    import tools.mujoco_tools as mujoco_tools
    import tools.matlab_tools as matlab_tools
    counts={};original=mujoco_tools.run_task
    def counted(*a,**kw):
        counts['mujoco_rollouts']=counts.get('mujoco_rollouts',0)+1
        return original(*a,**kw)
    mujoco_tools.run_task=counted
    for name in ('analyze_workspace','plan_pcc_reach','pcc_centerline','analyze_clearance'):
        fn=getattr(matlab_tools.MatlabTools,name)
        def wrapper(*a,_fn=fn,_name=name,**kw):
            counts[_name]=counts.get(_name,0)+1
            return _fn(*a,**kw)
        setattr(matlab_tools.MatlabTools,name,wrapper)
    start=time.monotonic();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    atomic_json(ROOT/'runs/closeout_full_suite_result.json',dict(tests=result.testsRun,passed=result.wasSuccessful(),
        failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors],skipped=len(result.skipped),
        elapsed_s=time.monotonic()-start,backend_calls=counts,scope='REGRESSION_NOT_FORMAL_CANDIDATES',real_matlab_enabled=True))
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
