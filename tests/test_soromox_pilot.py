"""Focused offline checks for the frozen domain and public tool boundary."""
import unittest
from pydantic import ValidationError
from schemas.platform import SessionInput
from schemas.design_optimization import DesignOptimizationProblem
from schemas.soromox_pilot import Solve
from tools.soromox_service import specification
from tools.research_soromox import configuration
from tools.design_optimization import continuous_space, structures
from extensions.tendon_family.generated_serial import dimensions
from tools.platform_registry import registry


def test_frozen_a_b_domain_has_one_independent_length_only_in_b():
    a, b = specification('A'), specification('B')
    pa, pb = [DesignOptimizationProblem.model_validate(s['physical_source']) for s in (a, b)]
    _, xa = continuous_space(pa, structures(pa)[0])
    allocation, xb = continuous_space(pb, structures(pb)[0])
    assert xa == {}
    assert len(xb) == 1
    for value in (0., .5, 1.):
        lengths = allocation.decode({name:value for name in xb})
        assert abs(sum(lengths)-.27) <= 1e-12
        assert .1545-1e-12 <= lengths[0] <= .1655+1e-12
        assert .1045-1e-12 <= lengths[1] <= .1155+1e-12
    for p in (pa, pb):
        assert p.variables['holding_tip_speed_weight'].value == .05
        assert p.execution.force_limit_n == 8.


def test_physical_zero_mapping_is_separate_from_numerical_tension_guess():
    cfg = SessionInput.model_validate(configuration())
    resolved = dimensions(cfg)
    assert resolved['dimensions']['reduced_coordinate'] == len(resolved['coordinate_order'])
    assert resolved['dimensions']['tendon_input'] == len(resolved['tendon_input_order'])
    physical = resolved['physical_initialization']
    for field in ('qpos_rad','qvel_rad_s'):
        assert set(physical[field]) == set(resolved['backend_position_order'])
        assert not any(physical[field].values())
    numeric = resolved['numerical_initialization']
    assert numeric['nominal']['u0'] == [.2]*len(resolved['tendon_input_order'])
    assert not any(numeric['measured_initial_state'])
    assert numeric['provenance']['nominal_is_current_target_solution'] is False


def test_typed_requests_cannot_expand_the_scientific_domain():
    for request in ({'case':'C'}, {'case':'B','lengths_m':[.20,.07]}, {'case':'A','initialization':'high_tension'}):
        try:
            Solve.model_validate(request)
        except ValidationError:
            pass
        else:
            raise AssertionError('Expanded scientific domain was accepted')


def test_new_tools_register_without_loading_the_isolated_runtime():
    import sys
    cfg = configuration(); reg = registry()
    for name in cfg['policy']['tool_bindings']:
        assert reg.inspect(reg.get(name), cfg['policy']['tool_bindings'])['executable']
    assert 'soromox' not in sys.modules
    assert 'jax' not in sys.modules


def load_tests(loader, suite, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(fn) for fn in (
        test_frozen_a_b_domain_has_one_independent_length_only_in_b,
        test_physical_zero_mapping_is_separate_from_numerical_tension_guess,
        test_typed_requests_cannot_expand_the_scientific_domain,
        test_new_tools_register_without_loading_the_isolated_runtime))
