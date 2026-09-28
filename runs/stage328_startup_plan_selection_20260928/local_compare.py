"""Exactly one production solve per variant per saved operating point."""
from startup_analysis import *
import casadi as ca
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_nmpc import TrackingNMPCController
from extensions.tendon_family.gvs_profile import candidate_numerical,load_profile
from extensions.tendon_family.tracking import checked_tracking
from extensions.tendon_family.gvs_projection import project
import extensions.optimization.ipopt as ipopt

label=sys.argv[1]
assert label in ('baseline','revised')
attempt=sys.argv[2] if len(sys.argv)>2 else '1'
start_file=OUT/(label+('_attempt'+attempt if attempt!='1' else '')+'_started.json')
assert not start_file.exists()
atomic_json(start_file,dict(max_nlp_solves=2,variant=label,attempt=attempt))
saved=read(OUT/'selected_states.json');inp=SessionInput.model_validate(saved['input'])
controller=TrackingNMPCController(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
controller.parameters=controller.parameters.model_copy(update={'startup_recovery_shortlist':label=='revised'})
controller.preparation={};controller.profile=dict(numerical=candidate_numerical(inp,checked_tracking(inp),load_profile()))
start=time.perf_counter();controller.configure(saved['physics'],saved['plan']);ws=controller.workspace
ws.solver.diagnostic_trace=True
integrations=[];original_tail=ws._extend_tail
def counted(*args,**kwargs):
    integrations.append(1)
    return original_tail(*args,**kwargs)
ws._extend_tail=counted
s=saved['samples'][0];ws._extend_tail(s['measured_x'],s['previous_u'])
original=ca.nlpsol
class Constructed(Exception):pass
class StopBeforeSolve:
    def __init__(self,solver):self.solver=solver
    def __call__(self,**kwargs):raise Constructed()
with patch.object(ipopt.ca,'nlpsol',side_effect=lambda *a,**k:StopBeforeSolve(original(*a,**k))):
    try:ws.solver.solve(ws.problem)
    except Constructed:pass
for key,(function,solver,selector) in list(ws.solver._compiled.items()):
    ws.solver._compiled[key]=(function,solver.solver,selector)
setup=time.perf_counter()-start
b=ROOT/saved['observation_source'];rows=json.loads(gzip.decompress(b.with_name('trajectory.json.gz').read_bytes()));initial=read(b.with_name('experiment_scene.json'))
records=[]
for s in saved['samples']:
    controller.previous=np.array(s['previous_u']);controller.seed=deepcopy(s['warm']);controller.unusable_updates=0
    geometry=deepcopy(s['geometry']);geometry['tip']=np.array(geometry['tip'])
    raw=initial if s['time_s']==0 else next(r for r in rows if abs(r['time_s']-s['time_s'])<1e-9)
    before=len(integrations);start=time.perf_counter()
    projection=project(saved['physics'],controller.resolved_basis,raw['qpos_rad'],raw['qvel_rad_s'],convention=controller.projector_id)
    x=np.r_[projection['q_gvs'],projection['qdot_gvs']]
    assert np.max(abs(x-s['measured_x']))<=1e-12
    geometry['gvs_projection']=projection
    try:
        controller.command(s['time_s'],geometry,x[:ws.n],x[ws.n:])
        wall=time.perf_counter()-start
    finally:
        atomic_json(OUT/(label+'_attempt'+attempt+'_progress.json'),dict(time_s=s['time_s'],integration_calls=len(integrations)-before,
            elapsed_s=time.perf_counter()-start,solver_diagnostics=ws.solver.last_diagnostics))
    solved=ws.last
    assert solved is not None,controller.last
    values=solved['result']['optimum']
    record=dict(time_s=s['time_s'],complete_update_s=wall,integration_calls=len(integrations)-before,
        independent_check=ws.solver.evaluate_candidate(ws.problem,values),metrics=metrics(ws,values,s['previous_u']),
        observation=controller.observations[-1],solved=solved)
    records.append(record)
    atomic_json(OUT/(label+'.json'),dict(label=label,setup_s=setup,priming_integrations=1,records=records,nlp_solves=len(records),provider_attempts=0,backend_attempts=0))
    print(label,s['time_s'],wall,record['metrics'],solved['recovery'],flush=True)
