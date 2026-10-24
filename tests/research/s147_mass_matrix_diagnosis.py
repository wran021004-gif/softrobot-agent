"""Decompose saved-state GVS/MuJoCo mass matrices without stepping physics.

Common cell masses isolate quadrature, longitudinal inertia and kinematics.
All audit variants are local; production parameters and the 12-coordinate T stay fixed.
"""
import argparse
from pathlib import Path
import sys
import time
import traceback

import casadi as ca
import numpy as np
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from s145_gvs_prediction_diagnosis import Diagnosis, audit, maxabs, norm, read, write
from extensions.tendon_family.compiler import rx
from extensions.tendon_family.gvs import _mass_descriptors, _observe_mass, _topology
from extensions.tendon_family.gvs_casadi import _SymbolicKinematics, _angular_jacobian
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs_projection import project
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation


def total(samples, key):
    return sum((s[key] for s in samples),np.zeros((12,12)))


def check_zero_reference(result,mount_r):
    """Closed-form first-cell check: root hinge versus distributed curvature."""
    entry = next(s for s in result['states'] if s['time_s']==0.)
    length = result['basis']['segments'][0]['length_m']
    ds = length/12
    s = ds/2
    # First nodal basis phi_0(u)=1-2u/L; first COM uses one midpoint GVS cell.
    gvs_angular = s*(1-s/length)
    gvs_linear = -.5*s*s*(1-s/length)
    mj_angular = ds*(1-ds/length)
    mj_linear = -s*mj_angular
    continuum_exact_linear = -.5*s*s+s**3/(3*length)
    comparisons = []
    for key,linear,angular in (('common_samples',gvs_linear,gvs_angular),
                               ('discrete_samples',mj_linear,mj_angular)):
        sample = entry[key][0]
        v = np.asarray(mount_r) @ np.array([0.,0.,linear])
        w = np.asarray(mount_r) @ np.array([0.,angular,0.])
        assert maxabs(v-np.asarray(sample['jv'])[:,0]) < 1e-16
        assert maxabs(w-np.asarray(sample['jw'])[:,0]) < 1e-16
        comparisons.append(dict(model=key,jv_column_expected_m2=v,jw_column_expected_m=w))
    result['zero_state_reference'] = dict(cell_length_m=ds,center_arc_m=s,
        checks=comparisons,gvs_midpoint_jv_z_m2=gvs_linear,
        exact_continuum_jv_z_m2=continuum_exact_linear,
        discrete_jv_z_m2=mj_linear,gvs_jw_y_m=gvs_angular,discrete_jw_y_m=mj_angular)
    result['ledger']['fixture_zero_reference'] = 1


class MassGraph:
    """Expose the production kinematics/Jacobians and each mass-sample contribution."""
    def __init__(self, name, topology, basis, descriptors, steps, mount):
        q = ca.MX.sym('q',12)
        state = _SymbolicKinematics(topology,q,steps,basis)
        mount_r, mount_p = ca.DM(mount[0]),ca.DM(mount[1])
        outputs = []
        for item in descriptors:
            pose = (state.point_pose(item['component'],item['s']) if item['kind']=='segment'
                    else state.base_pose(item['component']))
            rotation = mount_r @ pose[:3,:3] @ ca.DM(item.get('frame_rotation',np.eye(3)))
            position = mount_p + mount_r @ (pose[:3,3]+pose[:3,:3] @ ca.DM(item['offset']))
            jv, jw = ca.jacobian(position,q),_angular_jacobian(rotation,q)
            linear = item['mass']*(jv.T @ jv)
            angular = jw.T @ rotation @ ca.DM(item['inertia']) @ rotation.T @ jw
            longitudinal = jw.T @ rotation @ ca.DM(item.get('longitudinal_inertia',np.zeros((3,3)))) @ rotation.T @ jw
            outputs.extend([linear,angular,position,rotation,jv,jw,longitudinal])
        self.function = ca.Function(name,[q],outputs)
        self.descriptors = descriptors

    def evaluate(self,q):
        values = self.function(q)
        keys = ('linear','angular','position','rotation','jv','jw','longitudinal')
        return [dict(component=item['component'],**{
                    key:np.asarray(values[7*i+j]).reshape(-1) if key=='position'
                    else np.asarray(values[7*i+j]) for j,key in enumerate(keys)})
                for i,item in enumerate(self.descriptors)]


class Experiment:
    def __init__(self,output):
        self.output = output.resolve()
        source = REPO.parent/'s142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023'
        paired = REPO.parent/'s144-terminal-control-diagnosis/runs/s144'
        self.d = Diagnosis(source.resolve(),paired.resolve(),self.output)
        self.archive = read(REPO.parent/'s145-gvs-prediction-diagnosis/runs/s145/verified/result.json')
        self.result = self.d.result
        self.ledger = self.d.ledger
        self.ledger.update(mass_graph_build=0,mass_graph_evaluate=0,
            numpy_mass_pose_evaluate=0,project=0,mujoco_body_com_jacobian=0,
            fixture_angular_jacobian=0,root=0)
        self.result.update(states=[],finite_difference_checks=[],ledger=self.ledger,
            protocol=dict(times_s=[0.,.33,.34,.35],basis_dimension=12,
                mass_quadrature=5,spatial_integration=24,
                audit_only_quadrature=10,audit_only_spatial_integration=48,
                finite_difference_h=1e-6,finite_difference_times_s=[.34,.33]))
        self.topology = _topology(self.d.spec['robot']['structure']['data'])
        self.parameters = GVSModelParameters(basis=self.d.basis.specification)
        assert self.parameters.quadrature_points_per_segment==5
        assert self.parameters.integration_steps_per_segment==24
        self.mount_r = quaternion_wxyz_to_rotation(self.d.spec['task']['environment']['data']['mount']['quaternion_wxyz'])
        self.mount_p = np.asarray(self.d.spec['task']['environment']['data']['mount']['position_m'])
        self.descriptors = _mass_descriptors(self.topology,5,self.d.basis.specification)
        common = []
        counts = {local.segment:0 for local in self.d.basis.segments}
        for part in self.d.physics['parts']:
            inertia = np.asarray(part['inertia_com_local_kg_m2'])
            if part['dofs']:
                count = len(self.d.physics['entity_map'][part['component']]['bodies'])
                i = counts[part['component']]
                counts[part['component']] += 1
                rotation = rx(part['section_axis_rad'])
                offset = np.r_[0.,rotation[1:,1:] @ np.asarray(part['com_local_m'])[1:]]
                longitudinal = np.diag([0.,1.,1.])*part['mass_kg']*part['length_m']**2/12.
                common.append(dict(kind='segment',component=part['component'],s=(i+.5)/count,
                    offset=offset,mass=part['mass_kg'],inertia=inertia,frame_rotation=rotation,
                    longitudinal_inertia=longitudinal))
            else:
                common.append(dict(kind='rigid',component=part['component'],
                    offset=np.asarray(part['com_local_m']),mass=part['mass_kg'],inertia=inertia))
        self.common = common
        self.groups = list(dict.fromkeys(part['component'] for part in self.d.physics['parts']))
        start = time.perf_counter()
        mount = (self.mount_r,self.mount_p)
        self.baseline = MassGraph('s147_baseline',self.topology,self.d.basis,self.descriptors,24,mount)
        self.matched = MassGraph('s147_common_cells',self.topology,self.d.basis,common,24,mount)
        self.refined_quadrature = MassGraph('s147_quadrature10',self.topology,self.d.basis,
            _mass_descriptors(self.topology,10,self.d.basis.specification),24,mount)
        self.refined_spatial = MassGraph('s147_spatial48',self.topology,self.d.basis,self.descriptors,48,mount)
        self.ledger['mass_graph_build'] += 4
        self.result['graph_wall_s'] = time.perf_counter()-start
        self.result['mass_inventory'] = [dict(component=group,
            continuum_kg=sum(a['mass'] for a in self.descriptors if a['component']==group),
            discrete_kg=sum(a['mass'] for a in common if a['component']==group)) for group in self.groups]
        self.result['descriptors'] = dict(continuum=self.descriptors,common_cells=common)
        self.result['xml_audit'] = self.xml_audit()

    def xml_audit(self):
        m,p = self.d.model,self.d.physics
        errors = []
        for part in p['parts']:
            bid = m.body(part['entity']).id
            r = quaternion_wxyz_to_rotation(m.body_iquat[bid])
            errors.append(dict(entity=part['entity'],mass_kg=abs(m.body_mass[bid]-part['mass_kg']),
                com_m=maxabs(m.body_ipos[bid]-part['com_local_m']),
                inertia_kg_m2=maxabs(r @ np.diag(m.body_inertia[bid]) @ r.T-part['inertia_com_local_kg_m2'])))
        assert max(max(row[k] for k in ('mass_kg','com_m','inertia_kg_m2')) for row in errors) < 1e-12
        assert maxabs(m.dof_armature)==0 and maxabs(m.dof_frictionloss)==0
        return errors

    def mj_samples(self,q,time_s):
        d,m,t = self.d.data,self.d.model,self.d.mapping
        d.time = time_s
        d.qpos[self.d.qi] = t @ q
        d.qvel[:] = 0.
        d.ctrl[:] = 0.
        mujoco.mj_forward(m,d)
        self.ledger['mujoco_forward'] += 1
        assert d.time==time_s and d.ncon==d.nefc==0
        assert all(w.number==0 for w in d.warning)
        full = np.empty((48,48))
        mujoco.mj_fullM(m,d,full)
        self.ledger['mujoco_full_mass'] += 1
        matrix = t.T @ full[np.ix_(self.d.vi,self.d.vi)] @ t
        samples = []
        for part in self.d.physics['parts']:
            bid = m.body(part['entity']).id
            jv,jw = np.zeros((3,48)),np.zeros((3,48))
            mujoco.mj_jacBodyCom(m,d,jv,jw,bid)
            self.ledger['mujoco_body_com_jacobian'] += 1
            jv,jw = jv[:,self.d.vi] @ t,jw[:,self.d.vi] @ t
            ri = d.ximat[bid].reshape(3,3)
            iw = ri @ np.diag(m.body_inertia[bid]) @ ri.T
            samples.append(dict(component=part['component'],linear=m.body_mass[bid]*(jv.T @ jv),
                angular=jw.T @ iw @ jw,position=d.xipos[bid].copy(),
                rotation=d.xmat[bid].reshape(3,3).copy(),jv=jv,jw=jw))
        assert maxabs(total(samples,'linear')+total(samples,'angular')-matrix) < 1e-17
        return matrix,samples

    def graph(self,graph,q):
        self.ledger['mass_graph_evaluate'] += 1
        return graph.evaluate(q)

    def state(self,time_s,q):
        mr,mj = self.mj_samples(q,time_s)
        baseline = self.graph(self.baseline,q)
        common = self.graph(self.matched,q)
        mg = total(baseline,'linear')+total(baseline,'angular')
        mc = total(common,'linear')+total(common,'angular')
        ml = total(common,'longitudinal')
        if time_s:
            archived = next(s for s in self.archive['mechanics'] if abs(s['time_s']-time_s)<1e-12)
            assert maxabs(mr-np.asarray(archived['represented']['mass_matrix'])) < 1e-17
            assert maxabs(mg-np.asarray(archived['gvs']['mass_matrix'])) < 1e-17
        deltas = dict(sampling=mc-ml-mg,longitudinal=ml,geometry=mr-mc)
        difference = mr-mg
        assert maxabs(sum(deltas.values())-difference) < 1e-18
        chol = np.linalg.cholesky(mr)
        whitened = np.linalg.solve(chol,np.linalg.solve(chol,mg).T).T
        group_rows = []
        for group in self.groups:
            g = [s for s in baseline if s['component']==group]
            c = [s for s in common if s['component']==group]
            b = [s for s in mj if s['component']==group]
            group_rows.append(dict(component=group,
                continuum_linear=total(g,'linear'),continuum_angular=total(g,'angular'),
                discrete_linear=total(b,'linear'),discrete_angular=total(b,'angular'),
                matched_linear=total(c,'linear'),matched_angular=total(c,'angular'),
                center_distance_max_m=max(norm(a['position']-v['position']) for a,v in zip(c,b)),
                jv_relative=norm(np.concatenate([a['jv']-v['jv'] for a,v in zip(c,b)]))/norm(np.concatenate([v['jv'] for v in b])),
                jw_relative=norm(np.concatenate([a['jw']-v['jw'] for a,v in zip(c,b)]))/norm(np.concatenate([v['jw'] for v in b]))))
        blocks = []
        for i,label_i in zip((0,3,6,9),('near_y','near_z','distal1_y','distal1_z')):
            for j,label_j in zip((0,3,6,9),('near_y','near_z','distal1_y','distal1_z')):
                blocks.append(dict(row=label_i,column=label_j,difference_norm_kg_m4=norm(difference[i:i+3,j:j+3]),
                    relative_to_discrete=norm(difference[i:i+3,j:j+3])/norm(mr[i:i+3,j:j+3])))
        entry = dict(time_s=time_s,q_rad_m=q,continuum=mg,discrete=mr,common_fullcell=mc,
            continuum_samples=baseline,common_samples=common,discrete_samples=mj,
            difference=difference,deltas=deltas,relative_difference=norm(difference)/norm(mr),
            delta_norms={key:norm(value) for key,value in deltas.items()},
            matrix_norm_kg_m4=norm(mr),difference_norm_kg_m4=norm(difference),
            linear_difference_norm_kg_m4=norm(total(mj,'linear')-total(baseline,'linear')),
            angular_difference_norm_kg_m4=norm(total(mj,'angular')-total(baseline,'angular')),
            generalized_mass_eigenvalue_ratios=np.linalg.eigvalsh(whitened),
            condition_discrete=float(np.linalg.cond(mr)),condition_continuum=float(np.linalg.cond(mg)),
            groups=group_rows,blocks=blocks)
        if time_s in (.33,.34):
            mq_samples = self.graph(self.refined_quadrature,q)
            ms_samples = self.graph(self.refined_spatial,q)
            mq = total(mq_samples,'linear')+total(mq_samples,'angular')
            ms = total(ms_samples,'linear')+total(ms_samples,'angular')
            entry['integration_checks'] = dict(quadrature10=mq,spatial48=ms,
                quadrature_change_relative_to_discrete=norm(mq-mg)/norm(mr),
                spatial_change_relative_to_discrete=norm(ms-mg)/norm(mr))
        self.result['states'].append(entry)
        print('STATE',time_s,'relative',entry['relative_difference'],'delta norms',entry['delta_norms'],flush=True)
        return entry

    def observed(self,q):
        self.ledger['numpy_mass_pose_evaluate'] += 1
        observations = _observe_mass(self.topology,q,24,self.descriptors,self.d.basis.specification)
        return [(self.mount_p+self.mount_r @ p,self.mount_r @ r) for p,r in observations]

    def finite_difference(self,entry):
        q = np.asarray(entry['q_rad_m'])
        self.d.data.time = entry['time_s']
        h = 1e-6
        base = self.observed(q)
        jvs,jws = [np.zeros((3,12)) for _ in base],[np.zeros((3,12)) for _ in base]
        for i in range(12):
            delta = np.zeros(12)
            delta[i] = h
            plus,minus = self.observed(q+delta),self.observed(q-delta)
            for k,((_,r),(pp,rp),(pm,rm)) in enumerate(zip(base,plus,minus)):
                jvs[k][:,i] = (pp-pm)/(2*h)
                angular = (rp-rm)/(2*h) @ r.T
                angular = (angular-angular.T)/2
                jws[k][:,i] = [angular[2,1],angular[0,2],angular[1,0]]
        symbolic = entry['continuum_samples']
        checks = dict(time_s=entry['time_s'],
            position_max_m=max(maxabs(p-s['position']) for (p,_),s in zip(base,symbolic)),
            rotation_max=max(maxabs(r-s['rotation']) for (_,r),s in zip(base,symbolic)),
            jv_max_m2=max(maxabs(v-s['jv']) for v,s in zip(jvs,symbolic)),
            jw_max_m=max(maxabs(w-s['jw']) for w,s in zip(jws,symbolic)))
        assert checks['position_max_m'] < 1e-12 and checks['rotation_max'] < 1e-12
        assert checks['jv_max_m2'] < 1e-8 and checks['jw_max_m'] < 1e-8
        # Independent MuJoCo directional pose difference at the same T coordinates.
        direction = np.arange(1,13,dtype=float)
        direction /= norm(direction)
        poses = []
        for sign in (1.,-1.):
            self.d.data.qpos[self.d.qi] = self.d.mapping @ (q+sign*h*direction)
            mujoco.mj_fwdPosition(self.d.model,self.d.data)
            self.ledger['mujoco_fwd_position'] += 1
            poses.append([(self.d.data.xipos[self.d.model.body(p['entity']).id].copy(),
                           self.d.data.xmat[self.d.model.body(p['entity']).id].reshape(3,3).copy())
                          for p in self.d.physics['parts']])
        v_errors,w_errors = [],[]
        for (pp,rp),(pm,rm),s in zip(*poses,entry['discrete_samples']):
            v_errors.append(maxabs((pp-pm)/(2*h)-s['jv'] @ direction))
            angular = (rp-rm)/(2*h) @ s['rotation'].T
            angular = (angular-angular.T)/2
            w_errors.append(maxabs(np.array([angular[2,1],angular[0,2],angular[1,0]])-s['jw'] @ direction))
        checks.update(mujoco_directional_jv_max_m2=max(v_errors),mujoco_directional_jw_max_m=max(w_errors))
        assert max(v_errors) < 1e-8 and max(w_errors) < 1e-8
        self.result['finite_difference_checks'].append(checks)
        print('JACOBIAN CHECK',checks,flush=True)

    def run(self):
        start = time.perf_counter()
        self.result['status'] = 'running'
        try:
            qfixture = ca.MX.sym('qfixture',12)
            theta = qfixture[0]
            r = ca.vertcat(ca.horzcat(ca.cos(theta),-ca.sin(theta),0),
                          ca.horzcat(ca.sin(theta),ca.cos(theta),0),ca.horzcat(0,0,1))
            fixture = ca.Function('angular_fixture',[qfixture],[_angular_jacobian(r,qfixture)])
            actual = np.asarray(fixture(np.r_[.3,np.zeros(11)]))
            expected = np.zeros((3,12)); expected[2,0] = 1.
            assert maxabs(actual-expected) < 1e-14
            self.ledger['fixture_angular_jacobian'] += 1
            for time_s,index in ((0.,None),(.33,32),(.34,33),(.35,34)):
                if index is None:
                    q = np.zeros(12)
                else:
                    row = self.d.rows[index]
                    projection = project(self.d.physics,self.d.basis,row['qpos_rad'],row['qvel_rad_s'])
                    self.ledger['project'] += 1
                    q = np.asarray(projection['q_gvs'])
                self.state(time_s,q)
            check_zero_reference(self.result,self.mount_r)
            for time_s in (.34,.33):
                self.finite_difference(next(s for s in self.result['states'] if s['time_s']==time_s))
            self.result['status'] = 'completed'
        except Exception:
            self.result['status'] = 'failed'
            self.result['traceback'] = traceback.format_exc()
            raise
        finally:
            self.result['wall_s'] = time.perf_counter()-start
            self.result['store_after'] = audit(self.d.source)
            self.result['store_unchanged'] = self.result['store_after']==self.result['store_before']
            write(self.output/'result.json',self.result)
            assert self.result['store_unchanged']
            print('FINAL',self.result['status'],self.ledger,flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=REPO/'runs/s147')
    args = parser.parse_args()
    Experiment(args.output).run()
