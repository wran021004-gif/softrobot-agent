"""Bounded real co-design pilot through the existing Harness and Store."""
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
from tools.state_io import read,digest
from tools.platform_store import plain
from sorosim_s35_probe import ROOT,save


def plan(action,**kwargs):
    return dict(action=action,hypothesis='A bounded physical length change may improve the same full-task mathematical control problem.',
        expected_observation='Changed physical identity and adapted control with independent mathematical replay.',
        weakening_observation='No improvement, nonconvergence, positive task slacks, or replay discrepancy.',
        fixed_conditions='Frozen task, family domains, force bounds, basis, substeps and objective.',
        stopping_condition='Two candidates, two nonlinear solves, two mathematical replays; no physical execution.',
        interpretation='Local bounded structure/control experiment; not global optimality or MuJoCo acceptance.',**kwargs)


def check(folder):
    from test_sorosim_analysis import inputs
    from extensions.tendon_family.sorosim_codesign import calculate
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    inp,_,_,binding=inputs()
    request=dict(configuration=plain(inp),design_candidate=binding['candidate'],operation='solve',check_only=True,
        arguments=dict(substeps=1,initialization='constant_0_2',objective_mode='task_gap_with_effort',
            position_weight=1.,speed_weight=1.,secondary_coefficient=.001))
    result=calculate(request,lambda name,value:save(folder,name,value));save(folder,'derivative_checks',result)
    assert result['objective_relative_error']<2e-4 and result['constraint_relative_error']<2e-4


def pilot(directory,destination=None):
    from tools.research import core
    from tools.research.state import state,save as persist
    from tools.research.design import verify_candidate,numerical_binding
    from test_sorosim_analysis import inputs
    directory=Path(directory);host=core.prepare(ROOT/'configs/research/study_sorosim_s4b.json',directory)
    if 'freeze' not in state(host):core.bind(host)
    inp,_,_,_=inputs();parameters=deepcopy(inp.policy.candidate_builder.parameters.data['request'])
    sensitivity=read(ROOT/'evidence/sorosim_s4a/attempt01/design_sensitivity.json')
    raw=sensitivity['raw_facts'];target=np.array(inp.task.goal.data['target_m'])
    gradient=float(2*(np.array(raw['position'])-target)@np.array(sensitivity['sensitivity']['dp_dd']))
    bound=state(host)['spec']['family_space']['segment_domains'].get('0',state(host)['spec']['family_space']['segment_domain'])['length_m']
    original=parameters['segments']['0']['length_m'];proposed=float(np.clip(original-np.sign(gradient)*.005,bound['minimum'],bound['maximum']))
    if proposed==original:raise ValueError('PILOT_REQUIRES_ACTUAL_PHYSICAL_DESIGN_CHANGE')
    analysis_ref=persist(host,dict(source='evidence/sorosim_s4a/attempt01/design_sensitivity.json',
        sensitivity=sensitivity,gradient_squared_static_error_per_m=gradient,proposed_length_m=proposed,
        bound=bound,qualification='Local static derivative proposes direction only; full nonlinear solves determine ranking.'),'reused_sensitivity')
    rows=[];evidence=[]
    for i,length in enumerate((original,proposed)):
        request=deepcopy(parameters);request['segments']['0']['length_m']=length
        generated=core.dispatch(host,plan('generate',generation=request,supporting_evidence=[analysis_ref]),f'codesign-generate-{i}')
        ref=generated['result']['candidate'];candidate=verify_candidate(host,ref)
        if i==0 and candidate['configuration']['robot']['structure']['data']!=plain(inp.robot.structure)['data']:
            raise ValueError('REUSED_SENSITIVITY_PHYSICAL_DESIGN_MISMATCH')
        solved=core.dispatch(host,plan('mechanics',mechanics=dict(candidate=ref,substeps=1,
            initialization='constant_0_2',objective_mode='task_gap_with_effort',position_weight=1.,speed_weight=1.,secondary_coefficient=.001),
            supporting_evidence=[analysis_ref]),f'codesign-solve-{i}')['result']
        evidence.append(solved['reference'])
        if not solved.get('trajectory'):
            rows.append(dict(candidate=ref,length_m=length,solve=solved,replay=None));continue
        replay=core.dispatch(host,plan('replay',mechanics_source=solved['reference'],supporting_evidence=[solved['reference']]),
            f'codesign-replay-{i}')['result'];evidence.append(replay['reference'])
        rows.append(dict(candidate=ref,length_m=length,physical_design_identity=numerical_binding(candidate['configuration'],state(host)['spec'])['physical_design_identity'],solve=solved,replay=replay))
        print('Candidate',i,'length',length,'objective',solved['mathematical_facts']['objective'],
            'replay',replay.get('replay',{}).get('passed'),flush=True)
    summary=dict(stage='S4-B',variable='segments.0.length_m',bounds=bound,rows=rows,
        reused_sensitivity=analysis_ref,source_commit=state(host)['freeze'],numerical_s=state(host)['numerical_s'],
        counts={k:state(host).get(k,0) for k in ('offline_nlp','bdf_replays','mathematical_evaluations')},
        original_task_acceptance='unmeasured',provider_requests=0,physical_steps=0,rl_training=0)
    if len(rows)==2 and all((r.get('replay') or {}).get('replay',{}).get('passed') for r in rows):
        objectives=[r['solve']['mathematical_facts']['objective'] for r in rows]
        summary.update(objective_change=objectives[1]-objectives[0],improvement_observed=objectives[1]<objectives[0],
            control_change_norm_n=float(np.linalg.norm(np.array(rows[1]['solve']['trajectory']['tensions_n'])-rows[0]['solve']['trajectory']['tensions_n'])))
    summary_ref=persist(host,summary,'codesign_pilot_summary')
    core.dispatch(host,plan('stop',supporting_evidence=evidence+[summary_ref]),'codesign-stop')
    out=Path(destination or directory/'export')
    if out.exists():raise ValueError('PRESERVE_PILOT_EXPORT')
    export=core.export(host,out);save(Path(export['destination']),'summary',summary)
    return summary


class CodesignTests(unittest.TestCase):
    def test_frozen_harness_configuration_compiles(self):
        from tools.research.config import resolve
        from tools.platform_tasks import compile_input
        from tools.platform_registry import registry
        spec=resolve(ROOT/'configs/research/study_sorosim_s4b.json')
        snapshot=compile_input(spec['configuration'],registry())
        self.assertIn('controller.sorosim_matlab_nmpc@1.0.0',snapshot['dependencies'])

    def test_full_problem_derivatives(self):
        out=read(ROOT/'evidence/sorosim_s4b/check01/derivative_checks.json')
        self.assertEqual(out['variables'],1006);self.assertEqual(out['equalities'],864)
        self.assertEqual(out['inequalities'],13)
        self.assertLess(out['objective_relative_error'],2e-4)
        self.assertLess(out['constraint_relative_error'],2e-4)

    def test_real_design_control_and_replay(self):
        result=read(ROOT/'evidence/sorosim_s4b/pilot/summary.json');rows=result['rows']
        self.assertNotEqual(rows[0]['physical_design_identity'],rows[1]['physical_design_identity'])
        self.assertGreater(result['control_change_norm_n'],1e-4)
        self.assertEqual(result['counts']['offline_nlp'],2);self.assertEqual(result['counts']['bdf_replays'],2)
        for row in rows:
            self.assertTrue(row['replay']['replay']['passed'])
            self.assertEqual(len(row['solve']['trajectory']['tensions_n']),35)
            self.assertAlmostEqual(row['solve']['trajectory']['times_s'][-1],.35)
            self.assertEqual(row['solve']['task_acceptance'],'unmeasured')
            self.assertTrue(row['solve']['mathematical_facts']['relaxed_feasible'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--check',type=Path);p.add_argument('--pilot',type=Path)
    p.add_argument('--destination',type=Path);a=p.parse_args()
    if a.check:check(a.check)
    elif a.pilot:pilot(a.pilot,a.destination)
    else:unittest.main(argv=['test_sorosim_codesign'])
