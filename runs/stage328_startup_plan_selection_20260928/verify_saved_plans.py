"""Value-only check of saved plans after withdrawing selection code; no solves."""
from startup_analysis import *
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from extensions.optimization.ipopt import _EXPRESSION_FUNCTIONS,_violation
saved=read(OUT/'selected_states.json');inp=SessionInput.model_validate(saved['input'])
first=saved['samples'][0]
ws=TrajectoryWorkspace(inp.task,inp.robot,saved['plan']['effective_parameters'],first['measured_x'],first['previous_u'])
bundle=ws.problem.objective_function.data;function=_EXPRESSION_FUNCTIONS[bundle['expression_digest']][1]
checks=[]
for label in ('baseline','revised'):
    for s,r in zip(saved['samples'],read(OUT/(label+'.json'))['records'],strict=True):
        ws._set_prediction_time(s['time_s'])
        for j,v in enumerate(s['measured_x']):ws.problem.variables[f'x/0/{j}']['bounds']=[v/ws.state_scales[j]]*2
        for t,v in zip(ws.tendons,s['previous_u']):ws.problem.variables['previous_u/'+t]['bounds']=[v]*2
        values=r['solved']['result']['optimum'];x=np.array([values[k] for k in bundle['variable_order']])
        check=function(x=x);lb,ub,_=ws.solver._bounds(ws.problem,bundle['variable_order'])
        violation=_violation(x,np.asarray(check['constraints']).ravel(),lb,ub,[0.]*len(ws.problem.constraints),[0.]*len(ws.problem.constraints))
        objective=float(check['objective'])
        assert violation<=1e-5 and abs(objective-r['independent_check']['objective'])<=1e-12
        checks.append(dict(variant=label,time_s=s['time_s'],objective=objective,scaled_violation=violation,feasible=True))
atomic_json(OUT/'original_graph_verification.json',dict(checks=checks,nlp_solves=0,integrations=0,backend_attempts=0))
print(json.dumps(checks,indent=2))
