"""Reporting identities and evidence projection; no numerical/provider work."""
from copy import deepcopy
from unittest import TestCase
from examples import milestone4_reporting_scientific as report
from tools.state_io import digest,read
from tools.study_history import reporting_scientific_scope,reporting_summary
from examples.milestone45_checkpoint import reporting_payload


class SourceBoundReportingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet,cls.bindings,cls.history=report.build_packet()

    def summarize(self,history):
        s=self.packet['summary']
        return reporting_summary(history,
            new_execution_ids=[r['execution_id'] for r in s['results'] if r['observation_phase']=='updated_campaign_observation'],
            replication_pairs=[(r['original_execution_id'],r['repeated_execution_id']) for r in s['replications']],
            selected=s['selected'],latest=s['latest'],usage=s['usage'],stop=s['stop'])

    def test_equal_weights_different_structures_never_merge(self):
        rows=self.packet['summary']['results']
        a=next(r for r in rows if r['execution_id']=='a8382f8a4c6e4ebe921fb72f821b2188')
        b=next(r for r in rows if r['execution_id']=='91c3ba1b01d6499fb26df8f95409401b')
        self.assertEqual(a['weights'],b['weights'])
        self.assertNotEqual(a['structure_identity'],b['structure_identity'])
        self.assertNotEqual(a['scientific_configuration_identity'],b['scientific_configuration_identity'])
        with self.assertRaisesRegex(ValueError,'REPLICATION_CONFIGURATION_MISMATCH'):
            reporting_summary(self.history,new_execution_ids=[b['execution_id']],
                replication_pairs=[(a['execution_id'],b['execution_id'])],selected=b['candidate'],latest=b['candidate'],usage={},stop={})

    def test_run_labels_excluded_scientific_settings_retained(self):
        a=self.bindings[-1]['configuration']['effective'];b=deepcopy(a)
        b['run_id']='different-incidental-run'
        b['policy']['budget']['wall_s']+=1
        self.assertNotEqual(digest(a),digest(b))
        self.assertEqual(reporting_scientific_scope(a),reporting_scientific_scope(b))
        changes=[('seed',lambda c:c.update(seed=c['seed']+1)),
            ('initial',lambda c:c['task']['initializer']['parameters']['data'].update(qvel_rad_s={'near_y_0':.1})),
            ('task',lambda c:c['task']['goal']['data']['target_m'].__setitem__(0,.28)),
            ('numerical',lambda c:c['policy']['controller']['parameters']['data']['recipe'].update(horizon=11)),
            ('source',lambda c:c['policy']['controller']['parameters']['data'].update(numerical_source='initial_state_pretension')),
            ('physics',lambda c:c['robot']['structure']['data']['components'][0]['physics'].update(young_pa=12345)),
            ('timing',lambda c:c['task']['timing'].update(timestep_s=.001))]
        for name,change in changes:
            with self.subTest(name=name):
                altered=deepcopy(a);change(altered)
                self.assertNotEqual(reporting_scientific_scope(a),reporting_scientific_scope(altered))

    def test_history_reordering_has_no_count_chronology_or_replication_effect(self):
        history=deepcopy(self.history);history['rows'].reverse()
        self.assertEqual(self.summarize(history),self.summarize(self.history))

    def test_one_matching_replication_is_only_one_aggregate_observation(self):
        s=self.packet['summary'];self.assertEqual((s['new_execution_count'],s['novel_configuration_count'],s['replication_count']),(4,3,1))
        pair=s['replications'][0]
        self.assertEqual(set(pair['measured_differences'].values()),{0.})
        self.assertEqual(pair['replication_of']['execution_id'],pair['original_execution_id'])
        self.assertEqual(pair['repeated_execution_id'],'9af9c7a3d6d84751ab0c1ebacd73d0f8')
        self.assertIn('not full trajectories or timing',pair['comparison_scope'])
        self.assertIn('does not establish general repeatability',s['limits'][0])
        for row in s['results']:
            self.assertEqual(row['metrics']['source']['execution_id'],row['execution_id'])
            self.assertEqual(row['metrics']['source']['configuration'],row['candidate']['configuration'])
            self.assertTrue(row['references']['configuration'])

    def test_reporting_parameters_match_working_thinking_client(self):
        config=read(report.OLD/'freeze.json')['provider_configuration']
        request=reporting_payload(config,self.packet,report.INSTRUCTIONS)
        working=read(report.PRIOR/'correction2_request.json')
        params=lambda p:{k:v for k,v in p.items() if k not in ('messages','tools')}
        self.assertEqual(config,working['provider_configuration'])
        self.assertEqual(params(request),params(working['payload']))
        self.assertEqual(request['tools'],working['payload']['tools'])
        self.assertNotIn('tool_choice',request)
