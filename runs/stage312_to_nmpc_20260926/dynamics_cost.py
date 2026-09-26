"""Check the contracted Christoffel graph against mass finite differences and saved AD."""
import time
import numpy as np
from experiment import context,HERE,HISTORY,read,atomic_json
from extensions.tendon_family.gvs_casadi import functions_for,expression_from_system

raw,frozen,system=context()
start=time.perf_counter();f=functions_for(expression_from_system(system));build=time.perf_counter()-start
x=np.array(system.x0);x[12:]=np.linspace(-.2,.3,12);u=np.array(system.u0)
start=time.perf_counter();values=f.evaluate(x,u);call=time.perf_counter()-start
print('contracted graph',build,'call',call,flush=True)
eps=1e-5;derivatives=[]
for j in range(12):
    d=np.eye(24)[j]*eps
    derivatives.append((f.evaluate(x+d,u)['mass_matrix']-f.evaluate(x-d,u)['mass_matrix'])/(2*eps))
v=x[12:];C=np.einsum('k,kij,j->i',v,np.array(derivatives),v)-.5*np.einsum('j,ijk,k->i',v,np.array(derivatives),v)
np.testing.assert_allclose(values['velocity_bias'].ravel(),C,rtol=2e-5,atol=1e-12)
start=time.perf_counter();A,B,drift=f.linearize(system.x0,u);derivative=time.perf_counter()-start
saved=read(HISTORY)['chain']
np.testing.assert_allclose(A,saved['A'],rtol=1e-8,atol=1e-5)
np.testing.assert_allclose(B,saved['B'],rtol=1e-8,atol=1e-5)
atomic_json(HERE/'dynamics_cost.json',dict(graph_s=build,call_s=call,derivative_construction_and_call_s=derivative,
    christoffel_finite_difference_max_error=float(max(abs(values['velocity_bias'].ravel()-C))),
    saved_A_max_error=float(np.max(abs(A-np.array(saved['A'])))),saved_B_max_error=float(np.max(abs(B-np.array(saved['B'])))),
    drift_inf=float(np.max(abs(drift))),earlier_uncontracted_call_s=.3266862998716533))
print('verified',derivative,flush=True)
