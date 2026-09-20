"""Historical scientific tool declarations retained for exact-version sessions."""
from schemas.platform_math import DynamicSystem, LinearizedModel
from tools.platform_registry import Extension


def registrations(contracts, *, pcc_sources, gvs_sources, contract_dependencies):
    common = dict(contract_dependencies=contract_dependencies, cache=True, side_effects='none')
    legacy = dict(route_visible=False, legacy=True, recommended=False, backend_solves=0)
    return [
        Extension(
            'dynamics.gvs_build_system', 'tool', '1.0.0',
            contracts.GVSBuildSystemRequest, DynamicSystem,
            'extensions.tendon_family.gvs_casadi:gvs_build_system_tool',
            'Historical inline DynamicSystem export retained for exact-version compatibility.',
            sources=gvs_sources, dependencies=('numpy', 'casadi'),
            extension_dependencies=(('model.gvs', '1.0.0'),),
            capabilities={**legacy, 'category': 'mathematical_models', 'role': 'compatibility_tool',
                          'model': 'model.gvs', 'representation': 'dynamic_system'}, **common,
        ),
        Extension(
            'linearization.linearize', 'tool', '1.0.0',
            contracts.GVSLinearizeRequest, LinearizedModel,
            'extensions.tendon_family.gvs_casadi:linearize_tool',
            'Historical inline linearization retained for exact-version compatibility.',
            sources=gvs_sources, dependencies=('numpy', 'casadi'),
            extension_dependencies=(('linearizer.casadi', '1.0.0'),),
            capabilities={**legacy, 'category': 'linearization', 'role': 'compatibility_tool'}, **common,
        ),
        Extension(
            'control.lqr_describe', 'tool', '1.0.0',
            contracts.LQRDescribeRequest, contracts.LQRDescription,
            'extensions.tendon_family.gvs_casadi:lqr_describe_tool',
            'Historical matrix-level LQR description retained for exact-version compatibility.',
            sources=gvs_sources, dependencies=('numpy', 'scipy'),
            extension_dependencies=(('controller.lqr', '1.0.0'),),
            capabilities={**legacy, 'category': 'control', 'role': 'compatibility_tool'}, **common,
        ),
        Extension(
            'dynamics.gvs_evaluate', 'tool', '1.0.0',
            contracts.GVSDynamicsRequest, contracts.GVSDynamicsResult,
            'extensions.tendon_family.gvs:gvs_evaluate_tool',
            'Historical full GVS result retained for exact-version compatibility.',
            sources=gvs_sources, dependencies=('numpy',),
            extension_dependencies=(('model.gvs', '1.0.0'),),
            capabilities={**legacy, 'category': 'mathematical_models', 'role': 'compatibility_tool',
                          'model': 'model.gvs'}, **common,
        ),
        Extension(
            'kinematics.pcc_forward', 'tool', '1.0.0',
            contracts.PCCForwardRequest, contracts.PCCKinematicsResult,
            'extensions.tendon_family.pcc:pcc_forward_tool',
            'Historical full PCC result retained for exact-version compatibility.',
            sources=pcc_sources, dependencies=('numpy',),
            extension_dependencies=(('model.pcc', '1.0.0'),),
            capabilities={**legacy, 'category': 'mathematical_models', 'role': 'compatibility_tool',
                          'model': 'model.pcc'}, **common,
        ),
    ]
