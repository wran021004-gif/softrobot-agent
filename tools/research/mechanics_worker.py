"""Contained fixed-candidate mathematical worker, independent of retired workflows."""
import sys,time,traceback
from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import plain
from tools.service_execution import contain_worker_children

def calculate(request):
    from extensions.tendon_family.gvs_codesign import Workspace,integrate
    from extensions.optimization.ipopt import IpoptSolver
    cfg=request['configuration']
    if request['operation']=='replay':
        w=Workspace(cfg)
        replay=integrate(w.functions,w.tip,w.velocity,request['trajectory'],cfg['task']['goal']['data']['target_m'])
        return dict(status='computed',replay=replay,physical_validation='not_run; model integration only')
    a=request['arguments'];w=Workspace(cfg,a['substeps'])
    settings=dict(design_bounds=[0.,0.],design_initial=0.,position_weight=a['position_weight'],speed_weight=a['speed_weight'],secondary_coefficient=a['secondary_coefficient'],objective_mode=a['objective_mode'],initialization=a['initialization'])
    problem=w.assemble('A',a['initialization'],settings)
    solver=IpoptSolver(dict(max_iterations=120,tolerance=1e-6,max_cpu_s=None,max_wall_s=None,retain_feasible_iterate=True))
    result=solver.solve(problem);trajectory=w.decode(result.optimum)
    return dict(status=result.status,optimization_result=plain(result),diagnostics=solver.last_diagnostics,trajectory=trajectory,trajectory_metrics=w.metrics(trajectory),objective_definition=settings,physical_validation='not_run')

def main():
    request=read(sys.argv[1]);started=time.perf_counter()
    contain_worker_children()
    try:value=calculate(request)
    except Exception as exc:value=dict(status='engineering_error',reason=str(exc),traceback=traceback.format_exc())
    value['elapsed_s']=time.perf_counter()-started
    atomic_json(Path(sys.argv[1]).with_name('result.json'),value)

if __name__=='__main__':main()
