"""Prepare one authorized blank V1 Store; no candidates, science or Provider sends."""
import os,json
from pathlib import Path
from tools.research import core
from tools.research.config import ROOT,resolve
from tools.research.state import state,save,update,require_authorization,guard
from tools.research.tool_readiness import execution_environment
from tools.state_io import read,atomic_json,digest

RUN='p63v1-m3-autonomous-feasibility-sol-20261030'
if (ROOT/'runs/research'/RUN/'platform.sqlite').exists():raise RuntimeError('Single V1 Study exists; never replace or reset.')
for k,v in read(ROOT/'configs/research/runtime_p63b1_sol_none.json')['threads'].items():os.environ[k]=v
h=core.prepare(ROOT/'configs/research/study_p63v1_m3_autonomous_sol.json');h.actor='operator-v1-preparation'
s=state(h);spec=s['spec']
baseline=resolve(ROOT/'configs/research/study_p63g3_m3_action_handoff_sol.json')
same={k:spec[k]==baseline[k] for k in ('canonical_task','family_space','analysis_protocol','control','fidelity_policy','runtime')}
assert all(same.values()) and not s['candidates'] and not s['plans'] and not s['analysis_results'] and not s['physical_replays']
assert spec['budgets']['provider_requests']==80 and spec['native_control_limits']==dict(evaluation_requests=1000,iterations=100,knots_s=4)
assert spec['research_decisions']['analysis_interface']=='scientific_question_v3'
assert not spec['research_decisions']['history'] and not spec['research_decisions']['background']
scope=dict(study_id=RUN,resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],
    native_control_limits=spec['native_control_limits'],canonical_task_identity=spec['canonical_task_identity'],
    family_space_identity=spec['family_space_identity'],execution_scopes=['registered mathematics',*spec['capabilities']],
    authorized_provider_ceiling=80,one_study_only=True,no_automatic_budget_extension=True,
    empty_candidate_pool=True,no_g3_or_v0_solution_import=True,
    user_request='f985cfb8-175c-48d6-a027-208747a6f60f/已粘贴的文本.txt')
auth=save(h,dict(user_approval='Explicit current V1 task authorizes one full blank autonomous Study, <=80 total real Provider sends including Reporter/failures/closeout; no further confirmation.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
require_authorization(h);core.bind(h,specification=spec)
environment=execution_environment(spec)
assert environment['status']=='ready',environment
env=save(h,environment,'formal_environment_admission');guard(h)
admission=save(h,dict(user_authorization=auth,boundary='request_feedback',
    basis='G3 already validated real scientific-action handoff and original SDK/Store boundary. User authorizes continuing the same V1 Study after Worker/Reporter delivery until SELECT/STOP/budget/real blocker.',
    no_research_action_prescribed=True),'live_handoff_admission')
update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,
    'session_handoff_boundary':'request_feedback','live_admission_reference':admission})
out=dict(study_id=RUN,freeze=state(h)['freeze'],authorization=auth,environment_admission=env,
    live_handoff_admission=admission,exact_g3_task_family_protocol_control_runtime=same,
    candidate_count=0,main_plan_count=0,mathematical_evaluations=0,physical_replays=0,
    provider_used=h.store.remaining()['used']['model_calls'],historical_solution_imported=False,
    task_instructions_source='Original G1 blank full-Study instruction, with G3 validated contracts; no short-window early closure instruction.',
    checkpoints=[15,35,60],stop_policy='Continue same Study until autonomous SELECT/STOP, total Provider ceiling, or unrecoverable actual blocker. Read-only checkpoints do not prescribe research.')
atomic_json(h.store.root/'v1_preparation.json',out)
atomic_json(ROOT/'docs/research/p63v1_preflight.json',out)
print(json.dumps(out,indent=2))
