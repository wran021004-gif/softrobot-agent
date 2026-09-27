"""One candidate prediction/plan check; no backend rollout or provider call."""
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from schemas.platform import SessionInput
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.state_io import atomic_json
from examples.gvs_design_input import experiment_input
from extensions.tendon_family.gvs_profile import reach_numerical,checked_reach
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace

started=time.perf_counter()
inp=_candidate(SessionInput.model_validate(experiment_input()),{'components/near/length_m':.162},registry())
num=reach_numerical(inp);control=checked_reach(inp)
workspace=TrajectoryWorkspace(inp.task,inp.robot,control.recipe,num['measured_initial_state'],num['nominal']['u0'],settling=control.settling)
result=workspace.solve(num['measured_initial_state'],num['nominal']['u0'],warm=num['warm_guess'],elapsed_s=0.)
atomic_json(Path(__file__).parent/'plan_check.json',dict(
    purpose='Resolve candidate-owned warm-state regeneration and plan validity launch risk; no full rollout; not an LLM design choice',
    input=inp.model_dump(mode='json'),numerical=num,result=result,graph_s=workspace.graph_s,
    wall_s=time.perf_counter()-started,interpreter=sys.executable,
    threads={k:os.environ[k] for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
print(dict(accepted=result['accepted'],status=result['result']['status'],violation=result['result']['constraint_violation'],wall_s=time.perf_counter()-started),flush=True)
if not result['accepted']:raise SystemExit(1)
