"""Real MATLAB callback/solve gates; software fault tests are explicitly isolated."""
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import os
import unittest
import numpy as np
from unittest.mock import patch

from test_sorosim_contract import ROOT,final_candidate
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain
from schemas.platform import ProjectConfig,Payload
from extensions.tendon_family.sorosim_control import SorosimNMPCController,resolve_control
from extensions.tendon_family.backends import physics_for
from tools.platform_registry import registry

CALLBACK_LIMITS=dict(objective_absolute=.1,objective_relative=2e-4,
    constraint_absolute=2e-3,constraint_relative=2e-4,solution_scaled_violation=1e-5)


def prepare_controller(inp,folder):
    """Use the registered preparation hook and the existing immutable Store."""
    store=Store(folder/'store')
    name='sorosim-check-'+uuid4().hex
    store.create(ProjectConfig(project_id=name,grant_id=name,authorization_source='User-authorized bounded S0-S3 engineering checks',
        budget=inp.policy.budget))
    def save(value,kind):
        with store.transaction() as db:return plain(store.put(db,value))
    reg=registry();definition,parameters=reg.bind(inp.policy.controller,'controller')
    controller=definition.resolve()(parameters,inp.task.timing.control_period_s)
    definition.hook('prepare_execution')(SimpleNamespace(save_artifact=save),controller,inp)
    controller.validation_store=store
    return controller


def objective_reference(result,request):
    """Independent Python sum of the frozen scientific objective terms."""
    p=request['recipe'];X=np.asarray(result['states']);U=np.asarray(result['tensions'])
    P=np.asarray(result['tip_positions']);V=np.asarray(result['tip_velocities'])
    n=X.shape[1]//2;h=request['period_s']/p['substeps'];dt=request['period_s']
    scale=p['position_error_scale_m'] or request['position_tolerance_m']
    errors=(P-np.asarray(request['target']))/scale
    cost=h*(p['tracking_weight']*np.sum(errors**2)+p['velocity_weight']*np.sum(X[1:,n:]**2))
    start=max(0,request['duration_s']-request['settling']['window_s']-p['holding_brake_lead_s'])
    holding=request['elapsed_s']+h*np.arange(1,len(X))>=start-1e-12
    norm=p['holding_speed_cost_window_s'] if p['holding_speed_cost_mode']=='window_normalized_v1' else 1.
    cost+=h*p['holding_tip_speed_weight']/norm*np.sum((V[holding]/p['tip_speed_scale_m_s'])**2)
    change=U-np.vstack([request['previous_input'],U[:-1]])
    cost+=dt*(p['tension_weight']*np.sum(U**2)+p['variation_weight']*np.sum(change**2))
    cost+=p['terminal_weight']*np.sum(errors[-1]**2)+p['terminal_velocity_weight']*np.sum(X[-1,n:]**2)
    cost+=p['terminal_tip_speed_weight']*np.sum((V[-1]/p['tip_speed_scale_m_s'])**2)
    return float(cost)


def run_update(destination,check_only):
    destination=Path(destination)
    if destination.exists():raise ValueError('PRESERVE_EXISTING_EVIDENCE')
    folder=ROOT/'runs'/('sorosim-nmpc-'+uuid4().hex);folder.mkdir()
    inp,source=final_candidate();physics=physics_for(inp);plan=resolve_control(inp,physics)
    controller=prepare_controller(inp,folder)
    try:
        controller.configure(physics,plan)
        state=controller.profile['numerical']['measured_initial_state']
        request=controller.request(0.,state,check_only=check_only)
        result=controller.session.evaluate('nmpc',request)
        if check_only:
            holding_request=controller.request(.28,state,check_only=True)
            result['holding_window_check']=controller.session.evaluate('nmpc',holding_request)
    except Exception as exc:
        message=str(exc).replace(str(ROOT),'$REPO').replace(os.environ.get('SOROSIM_ROOT','__unset__'),'$SOROSIM_ROOT')
        atomic_json(destination,dict(stage='S3_callbacks' if check_only else 'S3_one_update',status='execution_error',
            error=message,limits=CALLBACK_LIMITS,timings=controller.session.timings))
        raise
    finally:
        controller.close()
    # Infinity means an unbounded state coordinate in the MATLAB-only context.
    if check_only:
        value=dict(stage='S3_callbacks',source=source,limits=CALLBACK_LIMITS,result=result,
            timings=controller.session.timings,scope='Directional differences at the actual regenerated candidate warm plan; no solver outcome')
    else:
        value=dict(stage='S3_one_update',source=source,limits=CALLBACK_LIMITS,result=result,request=request,
            python_objective=objective_reference(result,request),timings=controller.session.timings,
            scope='One real full-horizon MATLAB fmincon solve; no physical task acceptance')
    atomic_json(destination,value)
    return value


def verify_callbacks(e):
    assert e['limits']==CALLBACK_LIMITS
    result=e['result'];assert result['decision_dimension']==304 and result['constraint_dimension']==264
    bounds=np.array([CALLBACK_LIMITS[k] for k in ['objective_absolute','objective_relative','constraint_absolute','constraint_relative']])
    assert np.all(np.array(result['directional_errors'])<=bounds),result['directional_errors']
    assert result['constraint_violation']<=1e-5
    holding=result['holding_window_check']
    assert holding['context']['horizon']==7
    assert np.all(np.array(holding['directional_errors'])<=bounds),holding['directional_errors']


def verify_solution(e):
    result=e['result'];check=result['independent_validation'];x=np.array(result['states']);u=np.array(result['tensions'])
    assert result['accepted'],result['message']
    assert result['horizon']==10 and len(x)==11 and x.shape[1]==24
    assert result['constraint_violation']<=1e-5 and check['feasible']
    assert np.max(np.abs(check['constraints']))<=1e-5
    assert np.all(u>=0) and np.all(u<=8)
    assert np.max(np.abs(x[0]-e['request']['measured_state']))<1e-10
    assert abs(e['python_objective']-result['objective'])<=1e-8*max(1.,abs(result['objective']))


class NMPCTests(unittest.TestCase):
    def test_real_callbacks(self):
        p=ROOT/'evidence/sorosim_control/s3_callbacks.json'
        if not p.exists():self.skipTest('Real callbacks not yet recorded')
        verify_callbacks(read(p))

    def test_real_solution(self):
        p=ROOT/'evidence/sorosim_control/s3_update.json'
        if not p.exists():self.skipTest('Real solve not yet recorded')
        verify_solution(read(p))

    def test_failure_response_software_fixture(self):
        # Isolated failure injection; no fabricated mechanics or passing plan.
        inp,_=final_candidate();folder=ROOT/'runs'/('sorosim-fault-'+uuid4().hex);folder.mkdir()
        c=prepare_controller(inp,folder);plan=resolve_control(inp,physics_for(inp))
        fake=SimpleNamespace(__enter__=lambda:None,construct=lambda _:dict(construction_s=0.),
            close=lambda:None,timings=dict(calls=[dict(operation='nmpc',software_fixture=True)]))
        def fail(*args):raise RuntimeError('ISOLATED_SOFTWARE_FAULT')
        fake.evaluate=fail
        with patch('extensions.tendon_family.sorosim_session.SorosimSession',return_value=fake):
            c.configure(physics_for(inp),plan)
        g=dict(tip=np.zeros(3),gvs_projection=dict(projection_residual_max_rad_m=0.))
        for k in range(c.parameters.max_unusable_updates):
            command=c.command(.01*k,g,np.zeros(12),np.zeros(12))
            np.testing.assert_array_equal(command,[.2]*4)
            self.assertFalse(c.last['plan_accepted'])
        self.assertTrue(c.stop_requested)
        self.assertEqual(c.unusable_updates,c.parameters.max_unusable_updates)
        c.close()


@unittest.skipUnless(os.environ.get('SOFTROBOT_S56_GRID_TEST')=='1',
    'explicit MATLAB interface fixture; no dynamics or physical stepping')
class TimeGridBoundary(unittest.TestCase):
    def test_all_35_updates_and_last_interval(self):
        import hashlib,json,time
        import matlab.engine
        from tools.research.config import resolve
        cfg=resolve(ROOT/'configs/research/study_sorosim_s56_physics.json')['configuration']
        parameters=cfg['policy']['controller']['parameters']['data'];timing=cfg['task']['timing']
        # Dimension/input fixture only. No SoRoSim model or equations are constructed.
        model=dict(S=dict(ndof=12),spec=dict(routes=[dict(force_limit_n=8.) for _ in range(4)]))
        request=dict(recipe=parameters['recipe'],elapsed_s=0.,period_s=timing['control_period_s'],
            duration_s=timing['duration_s'],measured_state=[0.]*24,previous_input=[.2]*4,
            target=cfg['task']['goal']['data']['target_m'],position_tolerance_m=.01,
            settling=parameters['settling'],context_only=True)
        engine=matlab.engine.start_matlab('-nodesktop -nosplash');started=time.perf_counter();rows=[]
        try:
            engine.addpath(str(ROOT/'matlab/sorosim_control'),nargout=0)
            def inspect():
                engine.workspace['grid_fixture']=json.dumps(dict(model=model,request=request))
                engine.eval('fixture=jsondecode(grid_fixture); context_out=sr_nmpc(fixture.model,fixture.request);',nargout=0)
                return json.loads(engine.eval("jsonencode(struct('horizon',context_out.horizon,'steps',context_out.steps,'h',context_out.h))"))
            for k in range(35):
                request['elapsed_s']=k*timing['control_period_s'];row=inspect()
                self.assertEqual(row['horizon'],min(10,35-k));rows.append(row)
            request['recipe']=dict(request['recipe'],substeps=4)
            self.assertEqual(inspect()['steps'],4)  # last held command, four internal steps
            request.update(elapsed_s=0.,full_task=True)
            full=inspect();self.assertEqual(full['horizon'],35);self.assertEqual(full['steps'],140)
            for invalid in (.345,.35):
                request['elapsed_s']=invalid
                with self.assertRaisesRegex(matlab.engine.MatlabExecutionError,'CONTROL_TIME_GRID_REQUIRED'):inspect()
            atomic_json(ROOT/'runs/s56_grid_boundary_check.json',dict(fixture=True,contexts=rows,
                full_four_step_context=full,invalid_times_s=[.345,.35],physical_steps=0,implicit_roots=0,
                sqp_calls=0,elapsed_s=time.perf_counter()-started,
                implementation_sha256=hashlib.sha256((ROOT/'matlab/sorosim_control/sr_nmpc.m').read_bytes()).hexdigest()))
        finally:engine.quit()


if __name__=='__main__':
    path=os.environ.get('SOROSIM_S3_CALLBACKS')
    if path:verify_callbacks(run_update(path,True))
    path=os.environ.get('SOROSIM_S3_UPDATE')
    if path:verify_solution(run_update(path,False))
    unittest.main()
