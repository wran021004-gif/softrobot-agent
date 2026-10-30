"""G3 authorized Operator preparation; no Main scientific decision is scripted."""
import asyncio,json,os
from copy import deepcopy
from pathlib import Path
import httpx
from tools.research.config import ROOT,resolve
from tools.state_io import read,atomic_json,digest
from tools.research import core,analysis,reporter
from tools.research.state import state,save,update,require_authorization,guard
from tools.research.provider import credential
from tools.research.tool_readiness import execution_environment
from tools.research.design import generate_candidate
from tools.research.physical_replay import seed_control,dispatch as physical_dispatch
from tools.research.contracts import ControlSeedRequest,PhysicalReplayRequest
from tools.research.scientific_intent import control_settings

path=ROOT/'configs/research/study_p63g3_m3_action_handoff_sol.json'
run_id='p63g3-m3-action-handoff-sol-20261030'
if (ROOT/'runs/research'/run_id/'platform.sqlite').exists():raise RuntimeError('Unique G3 Study already exists; never reset or create replacement science.')
runtime=read(ROOT/'configs/research/runtime_p63b1_sol_none.json')
for k,v in runtime['threads'].items():os.environ[k]=v
key=credential(runtime['provider'],Path(runtime['credentials_reference']).expanduser())
health=httpx.get('http://127.0.0.1:8787/health',headers={'Authorization':'Bearer '+key},timeout=15)
health.raise_for_status()
h=core.prepare(path);h.actor='operator';spec=state(h)['spec']
scope=dict(study_id=run_id,resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],
    native_control_limits=spec['native_control_limits'],canonical_task_identity=spec['canonical_task_identity'],
    family_space_identity=spec['family_space_identity'],execution_scopes=['registered mathematics',*spec['capabilities']],
    authorized_provider_ceiling=16,includes_preparation_reporter=True,one_study_only=True,
    no_automatic_budget_extension=True,live_handoff_authorized=True,
    user_request='C:/Users/gugugaga/.codex/attachments/39b79326-a450-4a29-b499-3737c2a947e2/已粘贴的文本.txt')
auth=save(h,dict(user_approval='Explicit G3 authorization: original Operator preparation plus one <=16 total real Provider request validation; no additional approval.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
require_authorization(h);core.bind(h,specification=spec)
env=execution_environment(spec)
if env['status']!='ready':raise RuntimeError(env)
envref=save(h,env,'formal_environment_admission');guard(h)
before=deepcopy(state(h));assert not before['candidates'] and not before['plans'] and not before['analysis_results']
g1=read(ROOT/'docs/research/p63g1_live_audit.json')
generation=deepcopy([r['original_plan']['generation'] for r in g1['plans'] if r['original_plan']['action']=='generate'][1])
generation['family_space_identity']=spec['family_space_identity']
candidate=generate_candidate(h,generation,dict(origin='operator',scope='G3 post-failure preparation, not Main autonomous design',
    source='Rebuild G1 request 4 generation parameters with original tools; no result/control/Store imported.'))['candidate']
source=seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'),'g3-operator-baseline')['source']
settings=control_settings(spec,dict(method='pattern',knot_count=4,iterations=80,evaluation_requests=120))
q=dict(candidate=candidate,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
    operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
    control_optimization=dict(source=source,settings=settings.model_dump()))
math_before=deepcopy(state(h));result=analysis.dispatch(h,q,'g3-operator-math',guard=guard,origin='operator_preparation')
mathref=result['reference'];raw=h.store.artifact(mathref)
reporter.scientific_feedback(h,result,math_before)
physical_before=deepcopy(state(h))
physical=physical_dispatch(h,PhysicalReplayRequest(candidate=candidate,source=raw['control_schedule_reference']),'g3-operator-failure-replay')
physicalref=physical['reference'];accepted=h.store.artifact(physicalref)['acceptance']
reporter.scientific_feedback(h,physical,physical_before)
preparation=dict(decision_owner='Operator',candidate=candidate,baseline_source=source,math_result=mathref,
    optimized_source=raw['control_schedule_reference'],independent_result=physicalref,
    generation_request=generation,control_search_settings=settings.model_dump(),acceptance=accepted,
    before_live_provider_used=h.store.remaining()['used']['model_calls'],
    numerical_s=state(h)['numerical_s'],construction_numerical_s=state(h)['construction_numerical_s'],
    mathematical_evaluations=state(h)['mathematical_evaluations'],physical_replay_launches=state(h)['physical_replay_launches'],
    no_historical_result_import=True,no_main_plan_submitted=not state(h)['plans'])
save(h,preparation,'operator_g3_preparation')
atomic_json(h.store.root/'g3_preparation.json',dict(study_id=run_id,freeze=state(h)['freeze'],authorization=auth,environment_admission=envref,**preparation))
if accepted['status']!='valid_failure':raise RuntimeError('Prepared physical result is not a valid failure; preserve and report, never fabricate or retry to force failure.')
async def reports():
    async with httpx.AsyncHTTPTransport() as transport:
        await reporter.complete_reports(h,transport,max_model_calls=16)
asyncio.run(reports())
admission=save(h,dict(user_authorization=auth,boundary='request_feedback',
    basis='G3 original SDK/Mock route -> scientific intent -> original Plan admission tests, G0 bounded delivery, and G1 real request-feedback continuity. Current Study Main not yet sent.',
    no_extra_provider_requests=True),'live_handoff_admission')
update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback','live_admission_reference':admission})
baseline=resolve(ROOT/'configs/research/study_p63g1_m3_autonomous_sol.json')
same={k:spec[k]==baseline[k] for k in ('canonical_task','family_space','analysis_protocol','control')};assert all(same.values())
final=dict(study_id=run_id,freeze=state(h)['freeze'],authorization=auth,environment_admission=envref,
    **preparation,exact_task_family_protocol_control=same,
    provider_after_reporter=h.store.remaining()['used']['model_calls'],provider_usage=reporter.provider_usage(h),
    operator_report_references=[dict(reference=ref,status=r['interpretation_status']) for ref,r in reporter.current_reports(h)],
    live_handoff_admission=admission,ledger_before_main=h.store.remaining()['used'])
atomic_json(h.store.root/'g3_preparation.json',final)
print(json.dumps(dict(study_id=run_id,candidate=candidate,math=mathref,independent=physicalref,
    acceptance_status=accepted['status'],metrics=accepted['metrics'],math_summary=raw['nonlinear_capability'],
    provider_after_reporter=final['provider_after_reporter'],reporter_statuses=final['operator_report_references']),ensure_ascii=False,indent=2))
