# Selection implementation excerpts

Line numbers refer to commit `31522c63b0de00409c78e32f82c6b335f99da7a4`.

## `extensions/optimization/ipopt.py`

```python
  47:     def reset(self,lbx,ubx,lbg,ubg,start,policy=None,seed_objective=None,seed_settled=False,trace=False):
  48:         self.bounds=(lbx,ubx,lbg,ubg);self.best=None;self.first=None;self.latest=None
  49:         self.iteration=-1;self.start=start
  50:         self.policy=policy;self.seed_objective=seed_objective;self.seed_settled=seed_settled
  51:         self.stop_reason=None;self.stop_s=None
  52:         self.trace=[] if trace else None
  53:
  54:     def eval(self,args):
  55:         elapsed=time.perf_counter()-self.start
  56:         self.iteration+=1;items=dict(zip(self.names,args))
  57:         x=np.asarray(items['x']).ravel();g=np.asarray(items['g']).ravel();objective=float(items['f'])
  58:         violation=_violation(x,g,*self.bounds)
  59:         if self.trace is not None:
  60:             self.trace.append(dict(iteration=self.iteration,elapsed_s=elapsed,objective=objective,
  61:                 scaled_violation=violation,eligible=bool(np.isfinite(np.r_[x,g,objective]).all() and violation<=1e-5)))
  62:         self.latest=None
  63:         if np.isfinite(np.r_[x,g,objective]).all() and violation<=1e-5:
  64:             candidate=dict(x=x.copy(),objective=objective,iteration=self.iteration,
  65:                 elapsed_s=elapsed,scaled_violation=violation,
  66:                 iteration_zero=self.iteration==0)
  67:             self.latest=candidate
  68:             if self.first is None:self.first=candidate
  69:             if self.best is None or objective<self.best['objective'] or (self.best.get('initialization_only') and objective==self.best['objective']):
  70:                 self.best=candidate
  71:         if self.policy is not None and self.best is not None:
  72:             base=self.seed_objective
  73:             improvement=(base-self.best['objective'])/max(abs(base),1e-12) if base is not None else None
  74:             if self.seed_settled and base is not None and self.best['objective']<=base+1e-12:
  75:                 self.stop_reason='verified_settled_seed'
  76:             elif elapsed>=self.policy.minimum_s and improvement is not None and improvement>=self.policy.relative_improvement:
  77:                 self.stop_reason='relative_seed_improvement'
  78:             elif elapsed>=self.policy.budget_s and (base is None or self.best['objective']<=base+1e-12):
  79:                 self.stop_reason='budget_best_feasible'
  80:             if self.stop_reason is not None:
  81:                 self.stop_s=elapsed
  82:                 return [1]

 226:         initial_check_start=time.perf_counter()
 227:         initial_check=function(x=x0)
 228:         initial_violation=_violation(np.asarray(x0),np.asarray(initial_check['constraints']).ravel(),lbx,ubx,lbg,ubg)
 229:         initial_check_s=time.perf_counter()-initial_check_start
 230:         solve_start=time.perf_counter()
 231:         initial_finite=np.isfinite(np.r_[x0,np.asarray(initial_check['constraints']).ravel(),float(initial_check['objective'])]).all()
 232:         seed_objective=float(initial_check['objective']) if initial_finite and initial_violation<=1e-5 else None
 233:         if seed_objective is not None and problem.objective.direction!='minimize':seed_objective=-seed_objective
 234:         if selector is not None:selector.reset(lbx,ubx,lbg,ubg,solve_start,self.parameters.feasible_return,seed_objective,seed_settled,self.diagnostic_trace)
 235:         if selector is not None and seed_objective is not None and self.parameters.feasible_return is not None:
 236:             selector.best=dict(x=np.asarray(x0),objective=seed_objective,iteration=-1,
 237:                 elapsed_s=0.,scaled_violation=initial_violation,iteration_zero=False,
 238:                 initialization_only=True)
 239:         solution = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
 240:         solve_s=time.perf_counter()-solve_start
 241:         stats = solver.stats()
 242:         validation_start=time.perf_counter()
 243:         values = np.asarray(solution['x'], dtype=float).reshape(-1)
 244:         returned_values=values.copy();selected_iteration=None;selected_candidate=None
 245:         if not stats.get('success') and selector is not None and selector.best is not None:
 246:             values=selector.best['x'];selected_iteration=selector.best['iteration']
 247:             selected_candidate=selector.best
 248:         elif selector is not None and selector.latest is not None and np.array_equal(values,selector.latest['x']):
 249:             selected_candidate=selector.latest
 250:             selected_iteration=selected_candidate['iteration']
 251:         # At most one model evaluation per distinct first/selected/raw vector.
 252:         verified={}
 253:         def verify(vector):
 254:             key=np.asarray(vector,dtype=float).tobytes()
 255:             if key not in verified:
 256:                 check=function(x=vector)
 257:                 g=np.asarray(check['constraints'],dtype=float).ravel()
 258:                 verified[key]=(float(check['objective']),g,_violation(vector,g,lbx,ubx,lbg,ubg))
 259:             return verified[key]
 260:         raw_value,constraint_values,violation=verify(values)
 261:         returned_objective,returned_g,returned_violation=verify(returned_values)
 262:         def candidate_record(candidate):
 263:             if candidate is None:return None
 264:             objective,g,error=verify(candidate['x'])
 265:             return {**candidate,'x':candidate['x'].tolist(),
 266:                 'objective':candidate['objective'] if problem.objective.direction=='minimize' else -candidate['objective'],
 267:                 'independent_objective':objective,'independent_scaled_violation':error,
 268:                 'independently_feasible':bool(error<=1e-5 and np.isfinite(np.r_[candidate['x'],g,objective]).all())}
 269:         first_record=candidate_record(None if selector is None else selector.first)
 270:         selected_record=candidate_record(selected_candidate)
 271:         if not np.isfinite(np.r_[values,constraint_values,raw_value,returned_values,returned_g]).all():
 272:             raise ValueError('IPOPT_NONFINITE_SOLUTION')
 273:         return_status = str(stats.get('return_status', ''))
 274:         if bool(stats.get('success')):
 275:             status = 'converged'
 276:         elif selector is not None and selector.stop_reason is not None and violation<=1e-5:
 277:             status = 'feasible_early_stop'
 278:         elif return_status in ('Maximum_Iterations_Exceeded', 'Maximum_CpuTime_Exceeded'):
 279:             status = 'iteration_limit'
 280:         elif 'Infeasible' in return_status:
 281:             status = 'infeasible'
 282:         elif 'Unbounded' in return_status or 'Diverging_Iterates' in return_status:
 283:             status = 'unbounded'
 284:         else:
 285:             status = 'failed'
 286:         self.last_diagnostics = {
 287:             'solver': 'solver.ipopt',
 288:             'return_status': return_status,
 289:             'success': bool(stats.get('success')),
 290:             'iterations': int(stats.get('iter_count', 0)),
 291:             'variable_order': bundle.variable_order,
 292:             'constraint_order': bundle.constraint_order,
 293:             'constraint_values': constraint_values.tolist(),
 294:             'constraint_lower': lbg,
 295:             'constraint_upper': ubg,
 296:             'options': self.parameters.model_dump(mode='json'),
 297:             'construction_s':construction_s, 'solve_s':solve_s, 'cached_solver':cached,
 298:             'selected_feasible_iteration':selected_iteration,
 299:             'first_feasible_candidate':first_record,
 300:             'selected_feasible_candidate':selected_record,
 301:             'candidate_timer_origin':'perf_counter immediately before numerical solver call; callback entry timestamps; iteration zero is the initial iterate, not convergence',
 302:             'initial_scaled_violation':initial_violation,
 303:             'initial_objective':float(initial_check['objective']),
 304:             'policy_stop_reason':None if selector is None else selector.stop_reason,
 305:             'policy_stop_s':None if selector is None else selector.stop_s,
 306:             'initial_check_s':initial_check_s,
 307:             'returned_iterate_constraint_violation':returned_violation,
 308:             'returned_iterate_objective':returned_objective,
 309:             'validation_s':time.perf_counter()-validation_start,
 310:             'function_statistics':{k:v for k,v in stats.items()
 311:                 if k.startswith(('n_call_', 't_proc_', 't_wall_'))},
 312:             'constraint_derivative':'CasADi exact AD ('+self.parameters.constraint_jacobian_mode+')',
 313:         }
 314:         if self.diagnostic_trace:
 315:             self.last_diagnostics['iteration_trace']=None if selector is None else selector.trace
 316:             self.last_diagnostics['diagnostic_plans']=dict(initial=list(x0),selected=values.tolist(),returned=returned_values.tolist())
 317:         self.last_returned_optimum = dict(zip(bundle.variable_order,returned_values.tolist()))
 318:         return OptimizationResult(
 319:             status=status,
 320:             optimum=dict(zip(bundle.variable_order, values.tolist())),
 321:             objective_value=raw_value,
 322:             constraint_violation=float(violation),
 323:             iterations=int(stats.get('iter_count', 0)),
 324:         )

```

## `extensions/tendon_family/gvs_trajectory.py`

```python
  91:         dt=task.timing.control_period_s; h=dt/p.substeps; constraints={}; objective=0
  92:         if task.evaluator.extension_id!=('evaluate.tracking' if tracking else 'evaluate.reach'):
  93:             raise ValueError('GVS_TRAJECTORY_REQUIRES_REACH_EVALUATOR')
  94:         tolerance=p.position_error_scale_m or task.evaluator.parameters.data['max_position_error_m' if tracking else 'tolerance_m']
  95:         step_residual=implicit_step_residual(functions,n,m,h)
  96:         mapped=step_residual.map(steps,'thread',p.evaluation_threads)
  97:         residuals=mapped(ca.horzcat(*X[:-1]),ca.horzcat(*X[1:]),
  98:             ca.horzcat(*[U[k//p.substeps] for k in range(steps)]))
  99:         for k in range(steps):
 100:             x,y,u=X[k],X[k+1],U[k//p.substeps]
 101:             residual=residuals[:,k]
 102:             for j in range(2*n): constraints[f'dynamics_{k}_{j}']=residual[j]
 103:             tip=ca.mtimes(ca.DM(rotation),local_tip(y[:n]))+mount
 104:             if tracking:
 105:                 target=ca.vertcat(*[symbols[f'reference/position/{k+1}/{j}'] for j in range(3)])
 106:                 target_velocity=ca.vertcat(*[symbols[f'reference/velocity/{k+1}/{j}'] for j in range(3)])
 107:                 velocity_error=ca.mtimes(ca.DM(rotation),local_velocity(y[:n],y[n:]))-target_velocity
 108:             objective+=h*(p.tracking_weight*ca.sumsqr((tip-target)/tolerance)+p.velocity_weight*ca.sumsqr(velocity_error/p.tip_speed_scale_m_s if tracking else y[n:]))
 109:             if p.holding_tip_speed_weight:
 110:                 speed=ca.mtimes(ca.DM(rotation),local_velocity(y[:n],y[n:]))
 111:                 objective+=h*p.holding_tip_speed_weight*symbols[f'holding/{k+1}']*ca.sumsqr(speed/p.tip_speed_scale_m_s)
 112:         for k,u in enumerate(U):
 113:             objective+=dt*(p.tension_weight*ca.sumsqr(u)+p.variation_weight*ca.sumsqr(u-(previous if k==0 else U[k-1])))
 114:         objective+=p.terminal_weight*ca.sumsqr((tip-target)/tolerance)+p.terminal_velocity_weight*ca.sumsqr(velocity_error/p.tip_speed_scale_m_s if tracking else X[-1][n:])
 115:         if local_velocity is not None:
 116:             world_velocity=ca.mtimes(ca.DM(rotation),local_velocity(X[-1][:n],X[-1][n:]))
 117:             objective+=p.terminal_tip_speed_weight*ca.sumsqr((world_velocity-target_velocity if tracking else world_velocity)/p.tip_speed_scale_m_s)
 118:         objective*=specification.objectives[0].weight
 119:         bundle,selectors=expression_payload(list(expected),dict(variables=decision_symbols,expression=objective),constraints)
 120:         variables={name:dict(spec) for name,spec in expected.items()}
 121:         for j,value in enumerate(context.x0):
 122:             scale=variables[f'x/0/{j}']['physical_scale'];variables[f'x/0/{j}']['bounds']=[value/scale,value/scale]
 123:         for t,value in zip(tendons,context.u0): variables['previous_u/'+t]['bounds']=[value,value]
 124:         # These are fixed scheduling inputs, never optimized decisions. Generic
 125:         # assembly starts at task time zero with no hold enabled; the workspace
 126:         # fixes them from explicit execution time and acceptance configuration.
 127:         if p.holding_tip_speed_weight:
 128:             for k in range(1,steps+1):variables[f'holding/{k}']['bounds']=[0.,0.]
 129:         guess=dict(specification.initial_guess)
 130:         if tracking:
 131:             from .tracking import reference_at
 132:             positions,velocities=reference_at(task.goal.data,np.arange(1,steps+1)*h)
 133:             for quantity,values in (('position',positions),('velocity',velocities)):
 134:                 for k,row in enumerate(values,1):
 135:                     for j,value in enumerate(row):
 136:                         name=f'reference/{quantity}/{k}/{j}'
 137:                         variables[name]['bounds']=[float(value)]*2
 138:                         guess[name]=float(value)
 139:         if p.holding_tip_speed_weight:
 140:             for k in range(1,steps+1):guess[f'holding/{k}']=0.
 141:         for t,value in zip(tendons,context.u0):guess['previous_u/'+t]=value
 142:         for k in range(steps+1):
 143:             for j,value in enumerate(context.x0):guess.setdefault(f'x/{k}/{j}',value/variables[f'x/{k}/{j}']['physical_scale'])
 144:         for k in range(p.horizon):
 145:             for t,value in zip(tendons,context.u0): guess.setdefault(f'u/{k}/{t}',value)
 146:         return OptimizationProblem(variables=variables,objective=Objective(metric='gvs_dynamic_tracking_cost',direction='minimize',units='dimensionless'),
 147:             objective_function=bundle,constraints=[OptimizationConstraint(name=name,expression=selector,units='scaled_residual',lower=0.,upper=0.)
 148:                 for name,selector in zip(constraints,selectors)],initial_guess=guess,horizon=p.horizon,
 149:             model_reference=Binding(extension_id='model.gvs',parameters=Payload(contract='family.gvs_model',data=model_params.model_dump(mode='json'))))

 245:     def solve(self,measured_x,previous_u,warm=None,*,elapsed_s=None):
 246:         update_start=time.perf_counter()
 247:         prediction_timing=self._set_prediction_time(elapsed_s)
 248:         for j,value in enumerate(measured_x):self.problem.variables[f'x/0/{j}']['bounds']=[float(value)/self.state_scales[j]]*2
 249:         for t,value in zip(self.tendons,previous_u): self.problem.variables['previous_u/'+t]['bounds']=[float(value)]*2
 250:         source=warm if warm is not None else self.last
 251:         tails=[]
 252:         if source is not None:
 253:             X=np.asarray(source['states']);U=np.asarray(source['tensions']);s=0 if warm is not None else self.parameters.substeps
 254:             # An explicit warm seed already starts at the current horizon. The
 255:             # last plan has executed exactly one command interval (s nodes).
 256:             if s:
 257:                 X=np.concatenate([X[s:],np.repeat(X[-1:],s,axis=0)])
 258:                 U=np.concatenate([U[1:],U[-1:]])
 259:                 if not self.parameters.regenerate_warm_states:
 260:                     for k in range(len(X)-s,len(X)):
 261:                         X[k],diagnostic=self._extend_tail(X[k-1],U[-1]);tails.append(diagnostic)
 262:             if self.parameters.regenerate_warm_states:
 263:                 X=X.copy();X[0]=measured_x
 264:                 for k in range(1,len(X)):
 265:                     X[k],diagnostic=self._extend_tail(X[k-1],U[(k-1)//self.parameters.substeps],X[k])
 266:                     tails.append(diagnostic)
 267:             for k in range(len(X)):
 268:                 for j in range(2*self.n):self.problem.initial_guess[f'x/{k}/{j}']=float(X[k,j])/self.state_scales[j]
 269:             for k in range(len(U)):
 270:                 for j,t in enumerate(self.tendons):self.problem.initial_guess[f'u/{k}/{t}']=float(U[k,j])
 271:         elif self.parameters.regenerate_warm_states:
 272:             state=np.asarray(measured_x)
 273:             for k in range(self.parameters.horizon):
 274:                 for t,value in zip(self.tendons,previous_u):self.problem.initial_guess[f'u/{k}/{t}']=float(value)
 275:             for k in range(1,self.parameters.horizon*self.parameters.substeps+1):
 276:                 state,diagnostic=self._extend_tail(state,previous_u);tails.append(diagnostic)
 277:                 for j,value in enumerate(state):self.problem.initial_guess[f'x/{k}/{j}']=float(value)/self.state_scales[j]
 278:         for j,value in enumerate(measured_x):self.problem.initial_guess[f'x/0/{j}']=float(value)/self.state_scales[j]
 279:         for t,value in zip(self.tendons,previous_u):self.problem.initial_guess['previous_u/'+t]=float(value)
 280:         preparation_s=time.perf_counter()-update_start
 281:         seed_settled=False
 282:         if not self.tracking and self.parameters.feasible_return is not None and self._tail_solver is not None:
 283:             metrics=[]
 284:             for k in range(self.parameters.horizon*self.parameters.substeps+1):
 285:                 state=np.array([self.problem.initial_guess[f'x/{k}/{j}'] for j in range(2*self.n)])*self.state_scales
 286:                 tip,speed=self._motion(state[:self.n],state[self.n:])
 287:                 metrics.append((np.linalg.norm(np.asarray(tip).ravel()-self.target),np.linalg.norm(np.asarray(speed))))
 288:             seed_settled=all(e<=self.parameters.seed_position_tolerance_fraction*self.goal_tolerance
 289:                 and v<=self.parameters.seed_speed_limit_m_s for e,v in metrics)
 290:         preparation_s=time.perf_counter()-update_start
 291:         start=time.perf_counter(); result=self.solver.solve(self.problem,seed_settled=seed_settled);total=time.perf_counter()-start
 292:         recovery=dict(enabled=self.parameters.recover_returned_tensions,attempted=False,selected=False,wall_s=0.)
 293:         if self.parameters.recover_returned_tensions and result.status in ('converged','iteration_limit','feasible_early_stop'):
 294:             result,recovery=self._recover_returned(result,measured_x)
 295:         values=result.optimum;steps=self.parameters.horizon*self.parameters.substeps
 296:         X=np.array([[values[f'x/{k}/{j}']*self.state_scales[j] for j in range(2*self.n)] for k in range(steps+1)])
 297:         U=np.array([[values[f'u/{k}/{t}'] for t in self.tendons] for k in range(self.parameters.horizon)])
 298:         output=dict(states=X.tolist(),tensions=U.tolist(),result=result.model_dump(mode='json'),
 299:             prediction_timing=prediction_timing,
 300:             decision_state_scales=self.state_scales.tolist(),
 301:             diagnostics=self.solver.last_diagnostics,total_s=total,graph_s=self.graph_s,
 302:             recovery=recovery,
 303:             warm_start=dict(executed_intervals=int(source is not None and warm is None),
 304:                 preparation_s=preparation_s,regenerated_all_states=self.parameters.regenerate_warm_states,seed_settled=seed_settled,tail_initialization=tails),
 305:             nominal_operating_state=self.nominal_x,measured_initial_state=list(measured_x),
 306:             previous_tensions_n=list(previous_u),
 307:             period_s=self.period,substeps=self.parameters.substeps,
 308:             integration='implicit Euler in mass/force form; q scale 10 rad/m, force scale .001 N*m^2/rad',
 309:             cost='Stage weights per second on squared tip/position scale, curvature rate/(1 rad/(m*s)), tension/(1 N) and delta tension/(1 N); terminal weights on squared tip/position scale, curvature rate and world tip speed/speed scale. Optional holding speed cost starts at max(0, task duration minus settling window minus holding_brake_lead_s), using absolute prediction-node times. Acceptance timing is unchanged. Position scale defaults to task tolerance. Smoothing is a design penalty.',
 310:             cost_scales=dict(position_m=self.parameters.position_error_scale_m or self.goal_tolerance,
 311:                 tip_speed_m_s=self.parameters.tip_speed_scale_m_s))
 312:         # A feasible finite-iteration plan can drive suboptimal NMPC. Keep its
 313:         # nonconverged solver status; feasibility never implies optimality.
 314:         accepted=result.status in ('converged','iteration_limit','feasible_early_stop') and result.constraint_violation<=1e-5
 315:         if self.tracking:
 316:             output['prediction_timing']['seed_settled_shortcut']='disabled for tracking, including constant references'
 317:             output['cost']='Squared position and world tip velocity reference errors; terminal reference at terminal node; bounded tension and tension variation. No zero-speed holding schedule.'
 318:         output['accepted']=accepted
 319:         output['optimization_converged']=result.status=='converged'
 320:         if self.parameters.recover_returned_tensions:
 321:             def terminal_motion(values):
 322:                 state=np.array([values[f'x/{steps}/{j}'] for j in range(2*self.n)])*self.state_scales
 323:                 tip,speed=self._motion(state[:self.n],state[self.n:])
 324:                 return dict(error_m=float(np.linalg.norm(np.asarray(tip).ravel()-(self.reference_positions[-1] if self.tracking else self.target))),
 325:                     speed_m_s=float(np.linalg.norm(np.asarray(speed))),
 326:                     velocity_error_m_s=float(np.linalg.norm(np.asarray(speed).ravel()-self.reference_velocities[-1])) if self.tracking else None)
 327:             output['feedback']=dict(initial_objective=self.solver.last_diagnostics['initial_objective'],
 328:                 delivered_objective=result.objective_value,
 329:                 first_command_change_from_initialization_n=float(max(abs(values[f'u/0/{t}']-self.problem.initial_guess[f'u/0/{t}']) for t in self.tendons)),
 330:                 initial_terminal=terminal_motion(self.problem.initial_guess),delivered_terminal=terminal_motion(values))
 331:         # A finite unfinished iterate is still a useful next optimization guess.
 332:         # Command acceptance remains the separate, stricter feasibility check.
 333:         if result.status in ('converged','iteration_limit','feasible_early_stop'):self.last=output
 334:         output['update_wall_s']=time.perf_counter()-update_start
 335:         return output

```

## `extensions/tendon_family/gvs_nmpc.py`

```python
  97:     def command(self,t,geometry,q,v):
  98:         start=time.perf_counter();x=np.r_[q,v];error=None;solved=None
  99:         try:
 100:             solved=self.workspace.solve(x,self.previous,warm=self.seed,elapsed_s=t)
 101:             success=solved['accepted']
 102:         except (RuntimeError,ValueError) as exc:
 103:             success=False;error=str(exc)
 104:         self.seed=None
 105:         self.unusable_updates=0 if success else self.unusable_updates+1
 106:         self.stop_requested=self.unusable_updates>=self.parameters.max_unusable_updates
 107:         requested=np.asarray(solved['tensions'][0]) if success else self.previous.copy()
 108:         command,bridge=execute_ideal_tension(self.physics,requested)
 109:         self.previous=np.asarray(command).copy();elapsed=time.perf_counter()-start
 110:         converged=solved is not None and solved['optimization_converged']
 111:         intentional=solved is not None and solved['result']['status']=='feasible_early_stop'
 112:         self.last={**bridge,'plan_accepted':success,'solver_failed':not success or (not converged and not intentional),
 113:             'optimization_nonconverged':not converged,'failure_response_used':not success and not self.stop_requested,
 114:             'feasible_suboptimal_update':success and not converged,
 115:             'solver_error':error,'optimization_status':None if solved is None else solved['result']['status'],
 116:             'optimization_constraint_violation':None if solved is None else solved['result']['constraint_violation'],
 117:             'optimization_selected_iteration':None if solved is None or solved['recovery']['selected'] else solved['diagnostics']['selected_feasible_iteration'],
 118:             'plan_source':None if solved is None else ('reintegrated_returned_iterate' if solved['recovery']['selected'] else 'ipopt_selected'),
 119:             'feasibility_recovery':None if solved is None else solved['recovery'],
 120:             'feedback':None if solved is None else solved.get('feedback'),
 121:             'prediction_timing':None if solved is None else solved['prediction_timing'],
 122:             'recovery_wall_s':None if solved is None else solved['recovery']['wall_s'],
 123:             'recovery_integration_s':None if solved is None else solved['recovery'].get('integration_s',0.),
 124:             'recovery_validation_s':None if solved is None else solved['recovery'].get('validation_s',0.),
 125:             'optimization_returned_violation':None if solved is None else solved['diagnostics']['returned_iterate_constraint_violation'],
 126:             'update_wall_s':elapsed,'deadline_missed':elapsed>self.period_s,
 127:             'solver_construction_s':None if solved is None else solved['diagnostics']['construction_s'],
 128:             'optimization_solve_s':None if solved is None else solved['diagnostics']['solve_s'],
 129:             'policy_stop_reason':None if solved is None else solved['diagnostics']['policy_stop_reason'],
 130:             'plan_validation_s':None if solved is None else solved['diagnostics']['validation_s']+solved['recovery'].get('validation_s',0.),
 131:             'warm_preparation_s':None if solved is None else solved['warm_start']['preparation_s'],
 132:             'optimization_raw_status':None if solved is None else solved['diagnostics']['return_status'],
 133:             'unusable_updates':self.unusable_updates,'stop_requested':self.stop_requested,
 134:             'gvs_projection_residual_max_rad_m':geometry['gvs_projection']['projection_residual_max_rad_m']}
 135:         if success and (self.workspace.tracking or 'settling' in self.plan):
 136:             node=self.parameters.substeps
 137:             predicted=np.asarray(solved['states'][node])
 138:             tip,velocity=self.workspace._motion(predicted[:len(q)],predicted[len(q):])
 139:             self.last['one_step_prediction']=dict(time_s=t+self.period_s,state=predicted.tolist(),
 140:                 tip_position_m=np.asarray(tip).ravel().tolist(),tip_velocity_m_s=np.asarray(velocity).ravel().tolist(),
 141:                 frame='world',prediction_source='accepted_plan',applied_tension_n=list(command),integration='implicit Euler',substeps=node)
 142:         self.observations.append(dict(time_s=t,phase='current_state_before_integration',
 143:             tip_position_m=geometry['tip'].tolist(),gvs_q=list(q),gvs_qdot=list(v),
 144:             measured_initial_state=x.tolist(),graph_construction_s=self.workspace.graph_s,**self.last))
 145:         # Prediction evaluation and observation construction are operational work.
 146:         elapsed=time.perf_counter()-start
 147:         self.last.update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
 148:         self.observations[-1].update(update_wall_s=elapsed,deadline_missed=elapsed>self.period_s)
 149:         return command

```

## `extensions/tendon_family/gvs_reporting.py`

```python
  55:         terminal_tip_speed_m_s=motion[-1]['tip_speed_m_s'] if complete and motion else None,
  56:         sampled_settling=dict(available=available,passed=all(r['tip_error_m']<=acceptance.position_limit_m and r['tip_speed_m_s']<=acceptance.speed_limit_m_s for r in window) if available else None,
  57:             **plain(acceptance),continuous_time_guarantee=False,
  58:             max_error_m=max(r['tip_error_m'] for r in window) if available else None,
  59:             max_speed_m_s=max(r['tip_speed_m_s'] for r in window) if available else None),
  60:         updates=len(observations),accepted_plans=sum(o.get('plan_accepted',o.get('optimization_constraint_violation') is not None and
  61:             o['optimization_constraint_violation']<=1e-5 and not o.get('stop_requested',False) and
  62:             not o.get('failure_response_used',False)) for o in observations),
  63:         optimization_status_counts=dict(Counter(o.get('optimization_status') or 'unavailable' for o in observations)),
  64:         raw_termination_counts=dict(Counter(o.get('optimization_raw_status') or 'unavailable' for o in observations)),
  65:         initialization_selected=sum(o.get('optimization_selected_iteration') in (-1,0) for o in observations),
  66:         recovered_plans=sum(o.get('plan_source')=='reintegrated_returned_iterate' for o in observations),
  67:         accepted_noninitialization_plans=sum(bool(o.get('plan_accepted')) and
  68:             (o.get('plan_source')=='reintegrated_returned_iterate' or
  69:              (o.get('optimization_selected_iteration') is not None and o['optimization_selected_iteration']>0)) for o in observations),
  70:         converged_updates=sum(not o['optimization_nonconverged'] for o in observations),
  71:         solver_error_count=sum(o.get('solver_error') is not None for o in observations),
  72:         solver_failure_flags=sum(o['solver_failed'] for o in observations),

```
