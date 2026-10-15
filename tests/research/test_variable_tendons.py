"""Offline topology contracts and explicitly enabled, single-use M3-B1 control checks."""
from copy import deepcopy
from types import SimpleNamespace as NS
import os, time, unittest
from unittest.mock import patch
import numpy as np
from schemas.platform import SessionInput,ProjectConfig
from tools.platform_store import plain
from tools.state_io import digest,read,atomic_json
from tools.research.config import ROOT,resolve
from tools.research import core,design,analysis
from tools.research.state import state,update,save
from tools.research.contracts import Plan,Search,AnalysisRequest,Parameters,TopologyParameters
from extensions.tendon_family import generated_serial as family
from extensions.tendon_family.compiler import resolve as compile_physics
from extensions.tendon_family.contracts import Design,GVSModelParameters


def topology_cases(source):
    """Explicit authorized fixtures, never runtime templates or scientific ranking."""
    route=deepcopy(source['tendons'][0])
    route['points'][1]['attachment']['position_m']=[0.,.021,.006]
    added=deepcopy(source['tendons'][0]);added['id']='near_t3'
    for point in added['points'][:-1]:point['attachment']['position_m']=[0.,0.,.018]
    added['points'][-1]['hole']='near_h3'
    return dict(T0={},T1=dict(remove_tendons=['far_t2']),T2=dict(upsert_tendons=[route]),
        T3=dict(upsert_tendons=[added],guide_holes=dict(mid_guide=dict(near_h3=[0.,0.,.018]))))


class VariableTendonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from uuid import uuid4
        import shutil
        (ROOT/'runs').mkdir(exist_ok=True)
        cls.folder=ROOT/'runs'/('topology-fixture-'+uuid4().hex)
        def cleanup():
            import gc
            gc.collect()
            if cls.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            if cls.folder.exists():shutil.rmtree(cls.folder)
        cls.addClassCleanup(cleanup)
        cls.old=resolve(ROOT/'configs/research/study.json')
        def fixture_grant(**values):
            return ProjectConfig(**{**values,'project_id':cls.folder.name,'grant_id':cls.folder.name,
                'authorization_source':'Isolated offline test fixture; never a new live research allowance'})
        with patch.object(core,'ProjectConfig',side_effect=fixture_grant):
            cls.host=core.prepare(ROOT/'configs/research/topology.json',cls.folder)
        update(cls.host,freeze='offline-unbound-M3A-test-fixture')
        cls.spec=state(cls.host)['spec']
        cls.source=cls.spec['configuration']['robot']['structure']['data']
        cls.patches=topology_cases(cls.source);cls.candidates={};cls.parameters={}
        cls.construction_started=time.perf_counter()
        for name,topology in cls.patches.items():
            values=deepcopy(cls.spec['reference_parameters'])
            if topology:values.update(version='research_topology_parameters_v1',topology=topology)
            proposal=dict(action='propose',parameters=values,hypothesis='Offline topology interface fixture',
                expected_observation='Consistent ordered physical model',weakening_observation='Compiler rejects route',
                fixed_conditions='Frozen source geometry, material, mesh, task and control protocol',
                stopping_condition='Finish bounded M3-A checks',interpretation='Model consistency, not task acceptance')
            # Exercise native typed proposal/receipts; guard alone is replaced
            # because this uncommitted fixture is not a bound live study.
            with patch.object(core,'guard'):
                response=core.dispatch(cls.host,proposal,'topology-'+name)
            ref=response['result']['candidate']
            cls.candidates[name]=design.verify_candidate(cls.host,ref)
            cls.parameters[name]=values
        cls.construction_s=time.perf_counter()-cls.construction_started

    def configuration(self,name):return SessionInput.model_validate(self.candidates[name]['configuration'])

    def space(self,topology):
        return family.TopologyGeneratorSpace(source_design=self.source,
            source_mesh=self.spec['configuration']['policy']['discretization']['data'],
            segments=self.spec['reference_parameters']['segments'],authorization=self.spec['topology_authorization'],topology=topology)

    def test_old_identity_compilation_and_new_source_provenance(self):
        cfg=self.old['configuration']
        self.assertEqual(digest(cfg),'31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e')
        self.assertEqual(design.resolved_configuration(cfg,cfg,self.old['reference_parameters'],self.old['study_id']),cfg)
        self.assertNotIn('topology_authorization',self.old)
        self.assertEqual(self.spec['source_study_id'],self.old['study_id'])
        self.assertEqual(self.spec['source_study_identity'],digest(read(ROOT/'configs/research/study.json')))
        historical=read(ROOT/'evidence/topology_20261015/physical_diagnostics.json')
        mesh=cfg['policy']['discretization']['data'];old_physics=compile_physics(self.source,mesh)
        self.assertEqual(old_physics['identity'],historical['cases']['T0']['physics_identity'])
        self.assertEqual(digest(cfg),historical['source_configuration_identity'])
        for name,c in self.candidates.items():
            inp=self.configuration(name);physics=compile_physics(inp.robot.structure.data,mesh)
            self.assertEqual(c['source_identity'],digest(self.spec['configuration']))
            self.assertEqual(c['task_identity'],digest(cfg['task']))
            self.assertEqual(c['profile_identity'],state(self.host)['profile']['identity'])
            self.assertEqual(physics['discretization'],mesh)
            if name=='T0':self.assertEqual(physics,old_physics)
            for before,after in zip(self.source['components'],inp.robot.structure.data['components']):
                expected=deepcopy(before)
                if name=='T3' and expected['id']=='mid_guide':expected['guide_holes']['near_h3']=[0.,0.,.018]
                self.assertEqual(after,expected)

    def test_proposal_identity_order_control_and_fixed_topology_search_contract(self):
        from tools.platform_registry import registry
        from tools.platform_tasks import compile_input
        from extensions.tendon_family.gvs_profile import reach_numerical
        from tools.research.agent import decision_packet
        ids=[]
        for name,nu in (('T0',6),('T1',5),('T2',6),('T3',7)):
            c=self.candidates[name];inp=self.configuration(name);d=Design.model_validate(inp.robot.structure.data)
            builder,_=registry().bind(inp.policy.candidate_builder,'candidate_builder')
            self.assertEqual(builder.version,'4.0.0')
            compile_input(c['configuration'],registry())
            self.assertEqual(len(d.tendons),nu);self.assertEqual(len(d.actuators),nu)
            order=[t.id for t in d.tendons]
            self.assertEqual([a.transmission[0].tendon for a in d.actuators],order)
            numerical=reach_numerical(inp)
            self.assertEqual(numerical['tendon_order'],order)
            self.assertEqual(numerical['force_limits_n'],[8.]*nu)
            self.assertEqual(np.asarray(numerical['warm_guess']['tensions']).shape[1],nu)
            self.assertFalse(numerical['provenance']['reused'])
            self.assertFalse(numerical['provenance']['historical_states_reused'])
            self.assertEqual(len(numerical['nominal']['u0']),nu)
            ids.append(c['identity'])
        self.assertEqual(len(set(ids)),4)
        c=self.candidates['T2'];before=len(state(self.host)['candidates'])
        ref=design.construct(self.host,self.parameters['T2'],dict(label='A descriptive label cannot change physical identity'))
        self.assertEqual(ref['artifact_id'],digest(c));self.assertEqual(len(state(self.host)['candidates']),before)
        packet=decision_packet(self.host)
        self.assertEqual(packet['study']['topology_authorization'],self.spec['topology_authorization'])
        q=Search(variables=['segments.near.length_m'],bounds={'segments.near.length_m':(.152,.168)},
            fixed=self.parameters['T3'],objective='held_position_min_eigenvalue',operating_point='controller_start_input',
            protocol=self.spec['analysis_protocol'],scoring_window_s=.35,max_evaluations=1)
        self.assertIsInstance(q.fixed,TopologyParameters)
        self.assertEqual(q.fixed.topology.upsert_tendons[0].id,'near_t3')
        # Old proposals serialize identically, without even a new null field.
        self.assertEqual(plain(Plan.model_validate(dict(action='propose',parameters=self.old['reference_parameters'],
            hypothesis='fixture',expected_observation='fixture',weakening_observation='fixture',fixed_conditions='fixture',
            stopping_condition='fixture',interpretation='fixture')).parameters),plain(Parameters.model_validate(self.old['reference_parameters'])))
        combined=deepcopy(self.parameters['T2']);combined['segments']['near']['length_m']=.165
        with patch('tools.research.config.resolve',side_effect=AssertionError('Frozen study must not reload mutable sources')):
            cfg,_=design.configuration_for(self.host,combined,self.host.run_id)
        self.assertEqual(cfg['robot']['structure']['data']['tendons'],self.configuration('T2').robot.structure.data['tendons'])

    def test_reject_unauthorized_and_invalid_topology(self):
        host=self.host;s=state(host);old_spec=deepcopy(s['spec']);old_spec.pop('topology_authorization')
        try:
            update(host,spec=old_spec)
            with self.assertRaisesRegex(ValueError,'EXPLICIT_FROZEN_STUDY_GRANT'):
                design.configuration_for(host,self.parameters['T3'],host.run_id)
        finally:update(host,spec=s['spec'])
        invalid=[]
        invalid.append(dict(remove_tendons=['unknown']))
        invalid.append(dict(remove_tendons=['far_t0','far_t1']))
        invalid.append(dict(upsert_tendons=[self.source['tendons'][0]]*2))
        invalid.append(dict(guide_holes=dict(connector=dict(h=[0.,0.,0.]))))
        for coordinate in ([0.,.024,.024],self.source['components'][1]['guide_holes']['near_h0']):
            item=deepcopy(self.patches['T3']);item['guide_holes']['mid_guide']['near_h3']=coordinate;invalid.append(item)
        for edit in ('role','hole','owner','force','pretension','offset','span','occupied'):
            item=deepcopy(self.patches['T2']);t=item['upsert_tendons'][0]
            if edit=='role':t['points'][0]['role']='guide'
            elif edit=='hole':t['points'][-1]['hole']='missing'
            elif edit=='owner':t['points'][1]['attachment']['part']='unknown'
            elif edit=='force':t['force_limit_n']=9.
            elif edit=='pretension':t['pretension_n']=9.
            elif edit=='offset':t['points'][1]['attachment']['position_m'][1]=1.
            elif edit=='span':t['points'].insert(2,deepcopy(t['points'][1]))
            elif edit=='occupied':t['points'][-1]['hole']='near_h1'
            invalid.append(item)
        for item in invalid:
            with self.subTest(item=item),self.assertRaises(ValueError):family.generate_topology(self.space(item))
        # Compiler checks remain effective independently of the research grant.
        for edit in ('duplicate','diameter','pretension','transmission','rigid_envelope'):
            d=deepcopy(self.source)
            if edit=='duplicate':d['tendons'][1]['id']=d['tendons'][0]['id']
            elif edit=='diameter':d['tendons'][0]['diameter_m']=.004
            elif edit=='pretension':d['tendons'][0]['pretension_n']=9.
            elif edit=='transmission':d['actuators'][0]['transmission'][0]['tendon']='far_t1'
            elif edit=='rigid_envelope':d['tendons'][0]['points'][-1].update(hole=None,attachment=dict(part='payload',position_m=[0.,1.,0.]))
            with self.subTest(edit=edit),self.assertRaises(ValueError):compile_physics(d,self.space({}).source_mesh)
        # Physical actuator definitions cannot be smuggled into an undeclared patch.
        with self.assertRaises(ValueError):family.TopologyPatch.model_validate(dict(actuators=self.source['actuators']))

    def test_real_candidate_saved_inputs_reject_six_channel_states(self):
        from extensions.tendon_family.gvs_profile import reach_numerical
        for name in ('T1','T3'):
            c=self.candidates[name];inp=self.configuration(name);numerical=reach_numerical(inp)
            reference=state(self.host)['candidates'][c['identity']]
            saved=dict(candidate=reference,configuration_identity=digest(c['configuration']),x=numerical['measured_initial_state'],
                u=numerical['nominal']['u0'],tendon_order=numerical['tendon_order'],coordinate_order=numerical['coordinate_order'],
                phase='interval_start_previous_applied_input',input_units='N',actual_time_s=.30)
            for valid in (False,True):
                item=deepcopy(saved)
                if not valid:item['u']=[.2]*6
                q=AnalysisRequest(candidate=reference,operation='trajectory_feasibility',operating_point='saved_state',
                    saved_state=save(self.host,item),protocol=self.spec['analysis_protocol'])
                with patch('tools.service_execution._run_contained',return_value=NS(returncode=1)) as worker:
                    if valid:
                        result=analysis.dispatch(self.host,q,'fixture-saved-'+name,guard=lambda *a:None)
                        worker.assert_called_once()
                        self.assertEqual(result['status'],'incomplete') # Deliberate failed-worker fixture, no scientific success.
                    else:
                        with self.assertRaisesRegex(ValueError,'ORDER_AND_PHASE_REQUIRED'):
                            analysis.dispatch(self.host,q,'bad-saved-'+name,guard=lambda *a:None)
                        worker.assert_not_called()

    def test_empty_capabilities_engineering_export(self):
        original=state(self.host)['spec'];empty=deepcopy(original);empty['capabilities']=[]
        try:
            update(self.host,spec=empty)
            before=self.host.store.remaining()['used']
            result=core.export(self.host,self.folder/'diagnostic-export')
            self.assertEqual(result['resources']['shared_ledger']['used'],before)
            self.assertEqual(self.host.store.remaining()['used'],before)
            self.assertIsNone(result['claims'])
        finally:update(self.host,spec=original)

    def test_physical_gvs_geometry_and_three_step_mujoco_smokes(self):
        import mujoco
        from schemas.platform_math import SystemContext
        from extensions.tendon_family.gvs import GVSModel,tendon_lengths
        from extensions.tendon_family.gvs_casadi import functions_for,expression_from_system
        from extensions.tendon_family.gvs_basis import resolve_basis
        from extensions.tendon_family.geometry import geometry
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        from extensions.tendon_family.backends import _mujoco_state_failed
        diagnostics={};jacobians={};started=time.perf_counter()
        for name,nu in (('T0',6),('T1',5),('T2',6),('T3',7)):
            c=self.candidates[name];inp=self.configuration(name);d=inp.robot.structure.data
            physics=compile_physics(d,inp.policy.discretization.data)
            basis=inp.policy.controller.parameters.data['recipe']['basis'];resolved=resolve_basis(d,basis)
            n=len(resolved.coordinate_order);q=np.zeros(n);u=np.linspace(.1,.3,nu)
            parameters=GVSModelParameters(basis=basis)
            build_started=time.perf_counter()
            system=GVSModel(parameters).build_system(inp.robot,parameters,None,SystemContext(x0=[0.]*(2*n),u0=u.tolist(),scene=inp.task.environment))
            f=functions_for(expression_from_system(system));construction_s=time.perf_counter()-build_started
            evaluated=f.evaluate(np.r_[q,q],u);J=evaluated['tendon_length_jacobian'];jacobians[name]=J
            self.assertEqual(J.shape,(nu,n));self.assertEqual(len(system.u0),nu)
            self.assertEqual([s.entity for s in system.input_definition],[t['id'] for t in d['tendons']])
            np.testing.assert_allclose(evaluated['tendon_generalized_force'].ravel(),-J.T@u,atol=1e-12)
            direction=np.cos(np.arange(n)+1);h=1e-5
            fd=(tendon_lengths(d,q+h*direction,parameters)-tendon_lengths(d,q-h*direction,parameters))/(2*h)
            derivative_error=float(np.max(np.abs(fd-J@direction)))
            np.testing.assert_allclose(fd,J@direction,atol=1e-9,rtol=1e-5)
            linearization=None
            if name=='T3':
                linear_started=time.perf_counter();A,B,drift=f.linearize(np.r_[q,q],u)
                linearization=dict(elapsed_s=time.perf_counter()-linear_started,A_shape=list(A.shape),B_shape=list(B.shape))
                self.assertEqual(B.shape,(24,7));self.assertTrue(np.isfinite(A).all() and np.isfinite(B).all())
            scene=assemble(inp,physics);xml=self.folder/(name+'.xml');compile_xml(physics,scene,None,xml)
            model=mujoco.MjModel.from_xml_path(str(xml));data=mujoco.MjData(model)
            self.assertEqual(model.nu,nu);self.assertEqual(model.ntendon,nu)
            np.testing.assert_array_equal(model.actuator_trnid[:,0],np.arange(nu))
            np.testing.assert_array_equal(model.actuator_ctrlrange,np.tile([0.,8.],(nu,1)))
            self.assertEqual([model.tendon(i).name for i in range(nu)],[t['id'] for t in d['tendons']])
            data.ctrl[:]=u;mujoco.mj_forward(model,data)
            g=geometry(physics,np.zeros(len(physics['dofs'])))
            np.testing.assert_allclose(data.ten_length,g['lengths'],atol=1e-12)
            np.testing.assert_allclose(data.actuator_force,-u,atol=1e-12)
            np.testing.assert_allclose(data.qfrc_actuator,-g['Jlength'].T@u,atol=1e-11)
            smoke_started=time.perf_counter()
            for _ in range(3):
                before=data.time;mujoco.mj_step(model,data)
                self.assertFalse(_mujoco_state_failed(data,before))
            diagnostics[name]=dict(candidate_id=c['candidate_id'],candidate_artifact=state(self.host)['candidates'][c['identity']],
                configuration_identity=digest(c['configuration']),source_identity=c['source_identity'],profile_identity=c['profile_identity'],
                design_identity=physics['design_identity'],physics_identity=physics['identity'],model_identity=digest(plain(f.expression)),
                patch=plain(self.space(self.patches[name]).topology),tendon_order=[t['id'] for t in d['tendons']],
                actuator_order=[a['id'] for a in d['actuators']],coordinate_order=list(resolved.coordinate_order),
                bounds_n=[[0.,t['force_limit_n']] for t in d['tendons']],pretension_n=[t['pretension_n'] for t in d['tendons']],
                jacobian_shape=list(J.shape),jacobian=J.tolist(),tendon_force=evaluated['tendon_generalized_force'].ravel().tolist(),
                test_tensions_n=u.tolist(),finite_difference_direction=direction.tolist(),derivative_max_abs_error=derivative_error,
                gvs_construction_s=construction_s,linearization=linearization,
                mujoco=dict(actuators=model.nu,tendons=model.ntendon,xml_identity=digest(xml.read_text()),steps=3,
                    physical_time_s=float(data.time),physics_elapsed_s=time.perf_counter()-smoke_started,finite=True))
        delta=jacobians['T2']-jacobians['T0']
        self.assertGreater(np.linalg.norm(delta[0]),1e-6)
        np.testing.assert_array_equal(delta[1:],0.)
        report=dict(label='Offline physical/model consistency diagnostics; no task acceptance, topology ranking or live Agent',
            source_configuration_identity=digest(self.old['configuration']),source_design_identity=digest(self.source),
            study_identity=self.spec['resolved_identity'],source_study_identity=self.spec['source_study_identity'],
            topology_authorization=self.spec['topology_authorization'],common_pose=dict(q=[0.]*12,units='rad/m',frame='segment_local'),
            sign_convention='tau_tendon = -J_length.T @ total_tension',jacobian_units='m/(rad/m)',
            changed_route=dict(tendon_id='near_t0',input_index=0,jacobian_row_delta=delta[0].tolist(),
                input_direction_delta=(-delta[0]).tolist(),norm=float(np.linalg.norm(delta[0]))),
            cases=diagnostics,total_geometry_elapsed_s=time.perf_counter()-started,candidate_construction_elapsed_s=self.construction_s,
            resources=dict(gvs_graphs=4,new_topology_linearizations=1,mujoco_physics_steps=12,provider_calls=0,nmpc_solves=0,rl_training=0),
            unsupported=['manufacturability','global controllability','task feasibility','structural superiority'])
        from tools.research.state import science_hashes,core_hashes
        report['source_hashes']=dict(science=science_hashes(),core=core_hashes())
        print('M3A_PHYSICAL',dict(elapsed_s=report['total_geometry_elapsed_s'],route_change_norm=report['changed_route']['norm'],
            cases={k:dict(J=v['jacobian_shape'],derivative_error=v['derivative_max_abs_error'],smoke=v['mujoco']) for k,v in diagnostics.items()}))
        if os.environ.get('M3A_EVIDENCE'):
            atomic_json(ROOT/'evidence/topology_20261015/physical_diagnostics.json',report)


class M3BStudyTests(unittest.TestCase):
    def test_new_task_source_and_explicit_counts_preserve_historical_semantics(self):
        spec=resolve(ROOT/'configs/research/first_feasible_mirror.json')
        old=read(ROOT/'tasks/reach_hold.json');expected=deepcopy(old['task'])
        changes=read(ROOT/'tasks/reach_hold_mirror_v1.json')['task']
        from tools.research.config import patch as merge
        expected=merge(expected,changes)
        self.assertEqual(spec['configuration']['task'],expected)
        for key in ('evaluator','initializer','timing','sampling'):
            self.assertEqual(expected[key],old['task'][key])
        self.assertEqual(spec['configuration']['policy']['controller']['parameters']['data']['settling'],old['settling'])
        self.assertEqual(spec['configuration_provenance']['references']['task_base']['sha256'],digest(old))
        self.assertEqual(spec['topology_authorization']['tendon_count_bounds'],[1,7])
        self.assertEqual(spec['nmpc_limits']['executions'],spec['budgets']['physical_launches'])
        self.assertEqual(spec['budgets']['provider_requests'],12)
        self.assertEqual(spec['rl_limits']['training_stages'],0);self.assertNotIn('rl',spec['capabilities'])
        self.assertEqual(digest(resolve(ROOT/'configs/research/study.json')['configuration']),
            '31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e')

    def test_task_source_rejects_nested_escape_and_unknown_patch(self):
        from tools.research import config
        target=(ROOT/'tasks/reach_hold_mirror_v1.json').resolve();original=read(target)
        for replacement,pattern in ((dict(extends='../configs/research/robot.json'),'SINGLE_TASK_EXTENSION'),
            (dict(extends='reach_hold_mirror_v1.json'),'SINGLE_TASK_EXTENSION'),
            ({**original,'unknown_field':1},'UNKNOWN_CONFIGURATION_FIELD')):
            def source(path):return deepcopy(replacement) if path==target else read(path)
            with self.subTest(replacement=replacement),patch.object(config,'read',side_effect=source):
                with self.assertRaisesRegex(ValueError,pattern):config.resolve(ROOT/'configs/research/first_feasible_mirror.json')

    def test_zero_training_allowance_cannot_enable_rl(self):
        from tools.research import config
        target=(ROOT/'configs/research/first_feasible_mirror.json').resolve();bad=read(target)
        bad['capabilities'].append('rl')
        def source(path):return deepcopy(bad) if path==target else read(path)
        with patch.object(config,'read',side_effect=source):
            with self.assertRaisesRegex(ValueError,'TRAINING_STAGE_LIMIT'):config.resolve(target)


@unittest.skipUnless(os.environ.get('SOFTROBOT_M3B1_CONTROL')=='1',
    'set SOFTROBOT_M3B1_CONTROL=1 for five authorized single-update diagnostics')
class RealVariableTendonControl(unittest.TestCase):
    def test_single_use_registered_control_updates(self):
        import mujoco
        from tools.platform_registry import registry
        from tools.platform_store import zero
        from tools.research.state import science_hashes,core_hashes
        from extensions.tendon_family.gvs_casadi import functions_for,expression_from_system
        from extensions.tendon_family.gvs import GVSModel
        from extensions.tendon_family.control_evidence import COMPLETE_UPDATE_INPUTS
        from schemas.platform_math import SystemContext
        h=core.prepare(ROOT/'configs/research/topology_control_b1.json')
        spec=state(h)['spec'];source=spec['configuration']['robot']['structure']['data']
        cases=topology_cases(source)
        cases['S1']=dict(remove_tendons=[t['id'] for t in source['tendons'][1:]])
        self.assertFalse(any(e['kind']=='m3b1_started' for e in h.store.events(h.run_id)),
            'Single-use engineering scope: recover/read existing results; do not rerun solves')
        save(h,dict(cases=cases,scope='incomplete diagnostics; no task evaluator',
            source_hashes=dict(science=science_hashes(),core=core_hashes())), 'm3b1_started')
        reg=registry();reports={};started=time.perf_counter()
        class DiagnosticComplete(Exception):pass
        for name,topology in cases.items():
            values=deepcopy(spec['reference_parameters'])
            if topology:values.update(version='research_topology_parameters_v1',topology=topology)
            ref=design.construct(h,values,dict(origin='authorized_M3B1_single_update',case=name))
            c=h.store.artifact(ref);inp=SessionInput.model_validate(c['configuration'])
            backend_def,_=reg.bind(inp.policy.backend,'backend')
            controller_def,p=reg.bind(inp.policy.controller,'controller')
            controller=controller_def.resolve()(p,inp.task.timing.control_period_s)
            backend=backend_def.resolve()();folder=h.store.root/name;folder.mkdir(exist_ok=True)
            row,_=h.store.reserve(h.run_id,'diagnostic-'+name,digest(c),h.actor,
                {**zero(),'tool_calls':1,'backend_solves':1})
            case_start=time.perf_counter()
            try:
                ctx=NS(save_artifact=lambda value,kind:save(h,value,kind))
                controller_def.hook('prepare_execution')(ctx,controller,inp)
                backend.compile(inp,reg)
                initializer,ip=reg.bind(inp.task.initializer,'initializer')
                backend.initialize(initializer.resolve()(ip,inp.seed),controller)
                backend.folder=folder
                warm=deepcopy(controller.seed);previous=controller.previous.tolist()
                nu=len(controller.limits);n=controller.workspace.n
                modelp=GVSModelParameters(basis=controller.parameters.basis)
                system=GVSModel(modelp).build_system(inp.robot,modelp,None,
                    SystemContext(x0=controller.profile['numerical']['measured_initial_state'],u0=previous,scene=inp.task.environment))
                evaluated=functions_for(expression_from_system(system)).evaluate(
                    controller.profile['numerical']['measured_initial_state'],previous)
                self.assertEqual(evaluated['tendon_length_jacobian'].shape,(nu,n))
                self.assertEqual(evaluated['tendon_length_jacobian'].T.shape,(n,nu))
                B=np.vstack([np.zeros((n,nu)),np.linalg.solve(evaluated['mass_matrix'],-evaluated['tendon_length_jacobian'].T)])
                self.assertEqual(B.shape,(2*n,nu))
                original_command=controller.command;original_step=mujoco.mj_step;physical={}
                def command(*args):
                    if controller.observations:
                        physical.update(tip_m=args[1]['tip'].tolist(),tip_sample_phase='post_interval_mj_forward')
                        raise DiagnosticComplete()
                    return original_command(*args)
                def step(model,data,*args,**kwargs):
                    original_step(model,data,*args,**kwargs)
                    physical.update(time_s=float(data.time),qpos=data.qpos.tolist(),qvel=data.qvel.tolist(),
                        applied_tension_n=(-data.actuator_force).tolist(),tip_m=data.site_xpos[model.site('tip_site').id].tolist(),
                        nu=model.nu,actuator_tendon_indices=model.actuator_trnid[:,0].tolist())
                token=COMPLETE_UPDATE_INPUTS.set(True)
                try:
                    with patch.object(controller,'command',side_effect=command),patch.object(mujoco,'mj_step',side_effect=step):
                        with self.assertRaises(DiagnosticComplete):backend.solve(None)
                finally:COMPLETE_UPDATE_INPUTS.reset(token)
                self.assertEqual(len(controller.observations),1)
                self.assertEqual(physical['nu'],nu)
                self.assertEqual(physical['actuator_tendon_indices'],list(range(nu)))
                applied=np.asarray(physical['applied_tension_n'])
                self.assertTrue(np.isfinite(physical['qpos']).all() and np.isfinite(physical['qvel']).all())
                self.assertTrue(((applied>=-1e-12)&(applied<=controller.limits+1e-12)).all())
                reports[name]=dict(candidate=ref,configuration_identity=digest(c['configuration']),
                    physics_identity=backend.physics['identity'],control_identity=backend.scene['control']['identity'],
                    preparation=controller.preparation,numerical=controller.profile['numerical'],
                    tendon_order=controller.workspace.tendons,gvs_coordinates=n,gvs_states=2*n,
                    length_jacobian=evaluated['tendon_length_jacobian'].tolist(),input_matrix=B.tolist(),input_matrix_shape=list(B.shape),
                    optimization_variables=len(controller.workspace.problem.variables),inputs=nu,
                    warm_shapes=dict(states=list(np.asarray(warm['states']).shape),tensions=list(np.asarray(warm['tensions']).shape)),
                    previous_applied_tension_n=previous,observations=controller.observations,physical=physical,
                    preparation_graph_s=controller.workspace.graph_s,elapsed_s=time.perf_counter()-case_start,
                    complete_task=False,task_acceptance='not_assessed',scope='one real control update and one physical control interval')
                with h.store.transaction() as db:
                    reports[name]['raw_exports']=[dict(filename=p.name,
                        reference=plain(h.store.put(db,p.read_bytes(),'application/octet-stream')))
                        for p in sorted(folder.iterdir()) if p.is_file()]
                save(h,reports[name],'m3b1_case')
                h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
                    caller=h.actor,tool_id='engineering.m3b1',tool_version='1.0.0',execution_status='completed',charged=zero()),
                    reports[name],elapsed=reports[name]['elapsed_s'])
                print('M3B1',name,dict(outcome=controller.last['solver_outcome'],status=controller.last['optimization_raw_status'],
                    applied=applied.tolist(),elapsed_s=reports[name]['elapsed_s']),flush=True)
            finally:backend.close()
        update(h,numerical_s=state(h)['numerical_s']+sum(r['elapsed_s'] for r in reports.values()))
        report=dict(scope='M3-B1 engineering only; five real solves; zero complete task evaluations/provider requests',
            configuration=spec,cases=reports,elapsed_s=time.perf_counter()-started,ledger=h.store.remaining())
        atomic_json(ROOT/'evidence/topology_control_20261015/b1/control_diagnostics.json',report)
        ref=save(h,report,'m3b1_complete')
        update(h,research_status='stopped',closed_unix=time.time(),final_disposition=ref)
        core.export(h)


if __name__=='__main__':unittest.main()
