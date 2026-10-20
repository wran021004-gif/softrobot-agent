"""S12 engineering checks and read-only audit entry; never choose research actions."""
import json,subprocess
from tools.research.config import ROOT,resolve
from tools.research.state import state
from tools.research.research_context import context,decision_brief
from tools.research.contracts import RLRequest
from tools.research.rl import prepare_input
from tools.research.budget import nmpc_timing
from tools.research.analysis import admission
from tools.state_io import atomic_json
from tools.platform_host import Host


def preflight():
    h=Host(ROOT/'runs/research/s12-engineering-verified-20261020','s12-engineering-verified-20261020',actor='unified-research')
    s=state(h);candidate=s['research_history'][-1]['candidate']
    cfg,task=prepare_input(h,RLRequest(operation='start',candidate=candidate,mode='direct',rationale='S12 environment construction only, no training or rollout'))
    atomic_json(h.store.root/'rl_environment_input.json',cfg)
    code="import json,sys; from tools.rl.env import TensionEnv; c=json.load(open(sys.argv[1],encoding='utf8')); e=TensionEnv(c); print(json.dumps(dict(status='constructed',mode=e.mode,dofs=e.model.nv,actions=list(e.action_space.shape),observations=list(e.observation_space.shape),command_intervals=c['task']['command_intervals'],lower=e.lower.tolist(),upper=e.upper.tolist()))); e.close()"
    p=subprocess.run([s['spec']['runtime']['rl_python'],'-c',code,str(h.store.root/'rl_environment_input.json')],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:raise ValueError(p.stderr)
    formal=resolve(ROOT/'configs/research/study_s12_mirror.json')
    report=dict(scientific_evidence=False,provider_requests=0,new_physics=0,training_executed=False,
        engineering_study=h.run_id,implementation=s['freeze'],canonical_task_identity=formal['canonical_task_identity'],
        family_space_identity=formal['family_space_identity'],matlab=formal['tool_readiness']['sorosim_matlab']['status'],
        mathematics_admission=admission(h),nmpc_admission=nmpc_timing(h,candidate),direct_rl_environment=json.loads(p.stdout),
        residual_rl='Requires original complete compatible published reference; no acceptance transfer',
        history=s['research_history'],mathematics=s['research_mathematics'],current_context=decision_brief(context(h)),
        limits=dict(budgets=formal['budgets'],nmpc=formal['nmpc_limits'],rl=formal['rl_limits']),ledger=h.store.remaining(),
        limitations=['Readiness does not establish NMPC, training or task acceptance','Historical mathematics is not current verified input sensitivity'])
    assert report['ledger']['used']['backend_solves']==report['ledger']['used']['model_calls']==0
    atomic_json(ROOT/'evidence/s12_mirror/preflight.json',report)
    return dict(matlab=report['matlab'],direct_rl=report['direct_rl_environment'],new_physics=0,provider_requests=0)


if __name__=='__main__':print(json.dumps(preflight()))
