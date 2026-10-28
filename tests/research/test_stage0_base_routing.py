"""Base-only construction and reused cross-task fixtures; no scientific evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from extensions.tendon_family import generated_serial as family
from extensions.tendon_family.family_space import (
    parse_space, resolved_request, decision_summary, search_domains,
)
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.research import core, design, analysis, search, config
from tools.research.contracts import FamilyMixedSearch
from tools.research.state import state
from tools.state_io import read, digest
from tests.research import test_cross_task_integration as cross
from tests.research import test_bf7_native_search as native


ROOT = config.ROOT
RULE = 'base_only_consecutive_spans_v1'
BASE_DEFINITION = ROOT/'configs/research/family_space_stage0_base_only_v1.json'
ORIGINAL_RESOLVE = config.resolve


def base_only_spec(path, **kwargs):
    """Resolve the existing fixture Study with the new public family definition."""
    def source(file):
        value = read(BASE_DEFINITION if file.name == 'family_space_v2.json' else file)
        if value.get('version') == 'serial_family_space_v2':
            value = {**value, 'conditional_rules': RULE}
        return value
    with patch.object(config, 'read', side_effect=source):
        spec = ORIGINAL_RESOLVE(path, **kwargs)
    assert spec['family_space']['conditional_rules'] == RULE
    return spec


class BaseRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = base_only_spec(ROOT/'configs/research/study_mixed_family_search_dev.json')
        cls.space = cls.spec['family_space']

    def request(self, **changes):
        return dict(version='serial_family_generation_v2',
            family_space_identity=digest(self.space), segment_count=2, tendon_count=3, **changes)

    def build(self, request=None, space=None):
        return family.generate_family(dict(space=space or self.space, request=request or self.request()))

    def assert_base_routes(self, robot):
        starts = []
        for tendon in robot['tendons']:
            points = tendon['points']
            self.assertEqual(points[0]['attachment']['part'], 'fixed_base')
            self.assertEqual(points[0]['role'], 'start')
            self.assertEqual(points[-1]['role'], 'anchor')
            self.assertTrue(all(p['role'] == 'guide' for p in points[1:-1]))
            starts.append(points[0]['attachment']['position_m'])
        self.assertEqual(len(starts), len({tuple(p) for p in starts}))

    def test_single_multiple_segments_and_distributed_anchors(self):
        for n in (1, 2, 3):
            q = self.request(); q['segment_count'] = n
            q['spans'] = [dict(first_segment=0, last_segment=j % n, count=1, phase_rad=2*j)
                for j in range(3)]
            robot, _, _ = self.build(q)
            self.assert_base_routes(robot)
            self.assertEqual([t['points'][-1]['attachment']['part'] for t in robot['tendons']],
                ['segment_'+str(j % n) for j in range(3)])

    def test_exact_valid_override_and_physical_identity(self):
        q = self.request(); robot, mesh, physics = self.build(q)
        route = deepcopy(robot['tendons'][0]['points'])
        q['route_overrides'] = {0: route}
        same, same_mesh, same_physics = self.build(q)
        self.assertEqual(robot, same); self.assertEqual(mesh, same_mesh)
        self.assertEqual(physics['identity'], same_physics['identity'])
        q['route_overrides'][0][-1]['attachment']['s'] = .9
        changed, _, changed_physics = self.build(q)
        self.assert_base_routes(changed)
        self.assertNotEqual(physics['design_identity'], changed_physics['design_identity'])

    def test_reject_old_span_without_reinterpreting_it(self):
        q = self.request(); q['spans'] = [dict(first_segment=1, last_segment=1, count=3)]
        with self.assertRaisesRegex(ValueError, 'BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO'):
            self.build(q)
        with self.assertRaisesRegex(ValueError, 'BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO'):
            resolved_request(self.space, q)
        for leaf in ('study_family_space_dev.json', 'study_mixed_family_search_dev.json'):
            legacy = ORIGINAL_RESOLVE(ROOT/'configs/research'/leaf)['family_space']
            old = deepcopy(q); old['family_space_identity'] = digest(legacy)
            if legacy['version'].endswith('_v1'):old.pop('version')
            robot, _, _ = self.build(old, legacy)
            self.assertEqual(robot['tendons'][0]['points'][0]['attachment']['part'],
                'mid_guide' if legacy['version'].endswith('_v1') else 'guide_1')
            restricted = {**legacy, 'conditional_rules': RULE}
            old['family_space_identity'] = digest(restricted)
            with self.assertRaisesRegex(ValueError, 'BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO'):
                self.build(old, restricted)

    def test_overrides_cannot_bypass_base_or_role_order(self):
        robot, _, _ = self.build()
        route = robot['tendons'][0]['points']
        invalid = []
        for part in ('guide_1', 'segment_0'):
            r = deepcopy(route)
            r[0]['attachment']['part'] = part
            invalid.append(r)
        r = deepcopy(route); r[1]['role'] = 'start'; invalid.append(r)
        r = deepcopy(route); r[0]['role'] = 'guide'; invalid.append(r)
        r = deepcopy(route); r[-1]['role'] = 'guide'; invalid.append(r)
        r = deepcopy(route); r[0]['hole'] = 'fake'; invalid.append(r)
        invalid.extend([[], [deepcopy(route[0])]])
        for r in invalid:
            with self.subTest(route=r), self.assertRaisesRegex(ValueError, 'BASE_START_GUIDES_ANCHOR_REQUIRED'):
                self.build({**self.request(), 'route_overrides': {0: r}})

    def test_existing_clearance_order_anchor_and_hole_checks_remain(self):
        robot, _, _ = self.build(); route = robot['tendons'][0]['points']
        invalid = []
        r = deepcopy(route); r[1]['attachment']['position_m'] = [0., .005, 0.]; invalid.append(r)
        r = deepcopy(route); r[1], r[2] = r[2], r[1]; invalid.append(r)
        r = deepcopy(route); r[-1]['attachment']['part'] = 'segment_0'; invalid.append(r)
        r = deepcopy(route); r[2]['hole'] = 'tendon_1_hole'; invalid.append(r)
        for r in invalid:
            with self.subTest(route=r), self.assertRaises(ValueError):
                self.build({**self.request(), 'route_overrides': {0: r}})
        colliding = deepcopy(route)
        for point in colliding:
            if point['hole']:point['hole'] = 'tendon_1_hole'
        with self.assertRaisesRegex(ValueError, 'TENDON_ATTACHMENT_CLEARANCE'):
            self.build({**self.request(), 'route_overrides': {1: colliding}})

    def test_rule_identity_and_legacy_serialization(self):
        old = ORIGINAL_RESOLVE(ROOT/'configs/research/study_mixed_family_search_dev.json')['family_space']
        self.assertEqual(plain(parse_space(old)), old)
        self.assertEqual(digest(plain(parse_space(old))), digest(old))
        self.assertNotEqual(digest({**old, 'conditional_rules': RULE}), digest(old))

    def test_search_strategy_admission_and_topology_moves(self):
        from tools.research.mixed_moves import initial, next_move, generation
        from tests.research.test_mixed_search import request
        raw = request(self.spec)
        raw['span_strategies'] = ['whole_chain', 'base_to_distributed_anchors']
        q = FamilyMixedSearch.model_validate(raw)
        search_domains(self.space, q, self.spec['family_search'])
        summary = decision_summary(self.space, {}, ['generate'])
        self.assertIn('first_segment == 0', summary['span_semantics'])
        self.assertEqual(summary['applicable_span_strategies'], raw['span_strategies'])
        self.assertEqual(search.request_guidance(self.spec)['search']['applicable_span_strategies'], raw['span_strategies'])
        for n in q.segment_counts:
            for strategy in raw['span_strategies']:
                p = initial(self.space, q)
                p.update(segment_count=n, span_strategy=strategy)
                from tools.research.mixed_moves import reshape
                p = reshape(self.space, q, p)
                self.assert_base_routes(self.build(generation(self.space, q, p))[0])
                for cursor in range(6):
                    move, _, _ = next_move(self.space, q, p, cursor, .25)
                    proposed = generation(self.space, q, move)
                    self.assertTrue(all(span['first_segment'] == 0 for span in proposed['spans']))
        for strategy in ('distal', 'distributed_consecutive'):
            bad = q.model_copy(update=dict(span_strategies=[strategy]))
            with self.assertRaisesRegex(ValueError, 'SPAN_STRATEGY_NOT_APPLICABLE'):
                search_domains(self.space, bad, self.spec['family_search'])
            p = initial(self.space, bad)
            with self.assertRaisesRegex(ValueError, 'SPAN_STRATEGY_NOT_APPLICABLE'):
                generation(self.space, bad, p)

    def test_public_and_registry_generation_share_rule_and_reuse(self):
        with cross.fixture_directory() as folder, patch.object(cross, 'resolve', side_effect=base_only_spec):
            host = cross.fixture_host(folder)
            spec = state(host)['spec']
            q = self.request(); q['family_space_identity'] = spec['family_space_identity']
            q['tendon_count'] = 6
            with patch.object(core, 'guard'):
                made = core.dispatch(host, cross.plan('generate', generation=q), 'base')['result']
                self.assertEqual(made['status'], 'generated')
                c = design.verify_candidate(host, made['candidate'])
                self.assert_base_routes(c['configuration']['robot']['structure']['data'])
                explicit = {**q, 'spans': [dict(first_segment=0, last_segment=1, count=6)]}
                same = core.dispatch(host, cross.plan('generate', generation=explicit), 'explicit')['result']
                self.assertEqual(made['candidate'], same['candidate'])
                cfg = deepcopy(c['configuration'])
                build = cfg['policy']['candidate_builder']['parameters']['data']
                build['request']['spans'] = [dict(first_segment=1, last_segment=1, count=6)]
                with self.assertRaisesRegex(ValueError, 'BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO'):
                    family.authorize(SessionInput.model_validate(cfg), build, {})
                with patch.object(analysis, 'dispatch', side_effect=AssertionError('Invalid design must not evaluate')):
                    bad = {**q, 'spans': [dict(first_segment=1, last_segment=1, count=6)]}
                    result = core.dispatch(host, cross.plan('generate', generation=bad), 'invalid')['result']
                    self.assertEqual(result['status'], 'invalid')
            self.assertEqual(state(host)['mathematical_evaluations'], 0)
            self.assertEqual(host.store.remaining()['used']['backend_solves'], 0)
            self.assertEqual(state(host)['physical_replays'], [])


class BaseOnlyCrossTaskTests(cross.CrossTaskIntegrationTests):
    """Reuse all existing 2/3-condition, task adapter, replay and SELECT checks."""
    def setUp(self):
        self.enterContext(patch.object(cross, 'resolve', side_effect=base_only_spec))


class BaseOnlyNativeSearchTests(native.NativeMixedSearchTests):
    """Reuse Native counting, independent controls, failure and recovery checks."""
    def setUp(self):
        self.enterContext(patch.object(config, 'resolve', side_effect=base_only_spec))
        super().setUp()

    def query(self, **changes):
        q = super().query(**changes)
        q['span_strategies'] = ['base_to_distributed_anchors']
        return q

    def test_public_search_proposes_different_legal_topologies(self):
        q = self.query()
        q.update(variable_groups=['segment_count', 'spans'], segment_counts=[1, 2, 3],
            span_strategies=['whole_chain', 'base_to_distributed_anchors'],
            bounds={}, max_proposals=3, max_evaluations=9)
        with patch.object(core, 'guard'), patch.object(analysis, 'dispatch', side_effect=self.scored):
            out = core.dispatch(self.host, self.plan(q), 'base-topologies')['result']['result']
        # On a one-segment chain both strategies are physically equivalent.
        # Reusing that proposal must not spend another three condition entries.
        self.assertEqual(out['resource_use']['actual_mathematical_evaluations'], 6)
        self.assertEqual(out['resource_use']['skipped_moves'][0]['additional_evaluations'], 0)
        self.assertEqual({r['parameters']['segment_count'] for r in out['evaluated']}, {1, 2})
        for row in out['evaluated']:
            c = design.verify_candidate(self.host, row['evidence']['candidate'])
            robot = c['configuration']['robot']['structure']['data']
            self.assertTrue(all(t['points'][0]['attachment']['part'] == 'fixed_base' for t in robot['tendons']))
            self.assertEqual(c['configuration']['policy']['candidate_builder']['parameters']['data']['space']['conditional_rules'], RULE)
        self.assertIsNone(state(self.host).get('success_gate'))


if __name__ == '__main__':
    unittest.main()
