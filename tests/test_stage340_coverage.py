"""Scoped coverage, evaluated proposals and reservation-free rejection."""
from copy import deepcopy
import unittest
from uuid import uuid4

from tests.test_candidate_analysis_bundle import CandidateAnalysisBundleTests
from examples.stage339_candidate_analysis_experiment import TOOLS
from extensions.tendon_family.candidate import experiment_coverage
from extensions.tendon_family.optimization import covered_search_start
from extensions.tendon_family.route import create,check_run_eligibility
from tools.platform_host import Host


class Stage340CoverageTests(unittest.TestCase):
    def test_thresholds_and_ineligible_bounds(self):
        def facts(n=.16,f=.12,s=1.,m='baseline'):
            return dict(parameters=[dict(path=p,effective_value=v) for p,v in zip(
                ['components/near/length_m','components/far/length_m','design/section_scale','design/material_scenario'],[n,f,s,m])])
        self.assertFalse(experiment_coverage(facts(.15,.11,1.,'compliant'))['eligible'])
        self.assertTrue(experiment_coverage(facts(.159,.12,.99,'stiff'))['eligible'])
        self.assertFalse(experiment_coverage(facts(.1591,.12,.99,'compliant'))['eligible'])
        self.assertFalse(experiment_coverage(facts(.159,.12,.9901,'compliant'))['eligible'])
        self.assertFalse(experiment_coverage(facts(.159,.12,.99,'invented'))['eligible'])
        initial={'components/near/length_m':.16,'components/far/length_m':.12,'design/section_scale':1.}
        bounds=dict(zip(initial,[(.15,.17),(.11,.13),(.95,1.05)]))
        projected=covered_search_start(initial,bounds)
        self.assertTrue(experiment_coverage(dict(parameters=[dict(path=k,effective_value=v) for k,v in
            {**projected,'design/material_scenario':'compliant'}.items()]))['eligible'])
        with self.assertRaisesRegex(ValueError,'NO_ELIGIBLE_SECTION'):
            covered_search_start(initial,{**bounds,'design/section_scale':(.995,1.005)})

    def test_search_build_and_gate(self):
        fixture=CandidateAnalysisBundleTests();fixture.setUp()
        store=fixture.store;inp=deepcopy(store.session(fixture.host.run_id)['snapshot']['input'])
        inp['run_id']='stage340-coverage-'+uuid4().hex
        inp['policy']['tool_bindings']=TOOLS
        inp['policy']['route']['data'].update(multi_category_coverage_required=True,math_evaluation_limit=4)
        create(fixture.root,inp);host=Host(fixture.root,inp['run_id'])
        def call(tool,args):
            r=host.invoke(dict(request_id=uuid4().hex,tool_id=tool,tool_version=TOOLS[tool],
                arguments=args,reason='Offline scoped coverage verification.'))
            self.assertEqual(r['execution_status'],'completed',r)
            return r['output'],store.artifact(r['output'])
        _,seed=call('route.advance',dict(node_id='seed',action='build',combination='candidate_gvs_nmpc',
            changes={},evidence=[],reason='Solve-free unchanged seed.',next_step='Bounded mathematics.'))
        seedref=seed['detail']['result']
        bypass=host.invoke(dict(request_id=uuid4().hex,tool_id='simulation.run',tool_version='1.0.0',
            arguments=dict(candidate_id='bypass',changes={}),reason='Reject direct experiment execution before reservation.'))
        self.assertEqual(bypass['execution_status'],'rejected')
        self.assertIn('COVERED_EXPERIMENT_REQUIRES_ROUTE_RUN',bypass['error'])
        with self.assertRaisesRegex(ValueError,'MULTI_CATEGORY_COVERAGE_REQUIRED'):
            check_run_eligibility(host,'seed')
        rejected=host.invoke(dict(request_id=uuid4().hex,tool_id='route.advance',tool_version='1.0.0',
            arguments=dict(node_id='reject-seed',action='run',source_node='seed',evidence=[seedref],
                reason='Deliberately reject baseline before backend reservation.',next_step='Use an evaluated proposal.'),reason='Offline gate check.'))
        self.assertEqual(rejected['execution_status'],'failed')
        self.assertIn('MULTI_CATEGORY_COVERAGE_REQUIRED',rejected['error'])
        policy=inp['policy']['route']['data']
        ref,optimized=call('design.optimize_math',dict(source_node='seed',protocol=policy['analysis_protocol'],
            target=policy['endpoint_target'],variables={'components/near/length_m':[.15,.17],
                'components/far/length_m':[.11,.13],'design/section_scale':[.95,1.05]},
            material_scenarios=['compliant','stiff'],max_evaluations=4))
        self.assertEqual(len(optimized['proposals']),2)
        evaluated={r['candidate_id']:r for r in optimized['evaluations']}
        for proposal in optimized['proposals']:
            row=evaluated[proposal['candidate_id']]
            self.assertTrue(row['coverage']['eligible'])
            self.assertEqual(row['parameters'],proposal['parameters'])
        selected=optimized['proposals'][0]
        _,built=call('design.build_proposal',dict(node_id='proposal',optimizer_result=ref,
            optimizer_candidate_id=selected['candidate_id'],reason='Exact eligible evaluated proposal.',next_step='Prepare analysis.'))
        build=store.artifact(built['detail']['result'])
        self.assertTrue(experiment_coverage(build['candidate_facts'])['eligible'])
        self.assertEqual(build['proposal_provenance']['optimizer_candidate_id'],selected['candidate_id'])
        used=store.remaining(inp['run_id'])['used']
        self.assertEqual(used['model_calls'],0);self.assertEqual(used['backend_solves'],0)


if __name__=='__main__':unittest.main()
