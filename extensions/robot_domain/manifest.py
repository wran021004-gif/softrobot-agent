"""Registered adapters over existing design, solver exports and saved-data services."""
from schemas.platform import SessionInput
from tools.platform_registry import Extension
from . import contracts as c
from .candidate import EDITABLE

SOURCES = ('extensions/robot_domain/contracts.py', 'extensions/robot_domain/candidate.py',
    'extensions/robot_domain/signals.py', 'extensions/robot_domain/saved.py', 'extensions/robot_domain/manifest.py')
CONTRACTS = [('domain.rod_design', '1.0.0', c.RodDesign), ('domain.empty', '1.0.0', c.Empty)]
EXTENSIONS = [Extension('candidate.rod_design', 'candidate_builder', '1.0.0', c.Empty, SessionInput,
    'extensions.robot_domain.candidate:apply_design', '单 section / 八节等效杆：从冻结 DesignSpec 重编译派生量',
    sources=(*SOURCES, 'tools/design_compiler.py', 'schemas/design_spec.py', 'schemas/robot_ir.py', 'schemas/exploration.py'),
    assets=('physics_contracts/equivalent_rod_v2.md',),
    contract_dependencies=(('domain.rod_design', '1.0.0'), ('domain.empty', '1.0.0')),
    capabilities=dict(editable=list(EDITABLE), category='robot_design', role='adapter',
        model='equivalent_rod_v2; uncalibrated; sections=1, segments=8, tendons=4',
        semantics='absolute SI changes relative to frozen session design; candidate_id is a label'))]

for name, version, inp, out, binding, description in [
    ('diagnostics.sample_exceeds', '1.1.0', c.EntityDiagnosticQuery, c.EntityDiagnosticResult, 'signals:sample_exceeds', '按名称/实体/相位选择保存标量并检查严格大于阈值；无新求解/评分'),
    ('signals.read', '1.0.0', c.SignalQuery, c.SelectedSignal, 'signals:read_signal', '按名称/实体/相位读取保存统一信号，歧义拒绝'),
    ('diagnostics.saved_trajectory', '2.0.0', c.SavedDiagnosis, c.SavedProduct, 'saved:diagnosis', '平台结果引用自动进入旧保存轨迹诊断；无新求解/评分'),
    ('diagnostics.signal_rule', '2.0.0', c.SavedRule, c.SavedProduct, 'saved:rule', '平台结果引用自动进入既有保存信号规则'),
    ('visualization.saved_replay', '1.0.0', c.ResultSource, c.SavedProduct, 'saved:replay', '恢复原始包并准备已有回放 observation；不开窗口'),
    ('visualization.render_simulation_video', '2.0.0', c.SavedVideo, c.SavedProduct, 'saved:video', '同一证据桥接调用已有视频执行器；显式派生产物'),
]:
    EXTENSIONS.append(Extension(name, 'tool', version, inp, out,
        'extensions.robot_domain.' + binding, description,
        sources=(*SOURCES, 'tools/public_services.py', 'tools/trajectory_diagnosis.py', 'tools/diagnostic_rules.py',
            'tools/observation_contract.py', 'tools/observation_tools.py', 'tools/rules/contact_presence.py',
            'tools/simulation_video.py', 'tools/native_replay.py', 'tools/matlab_replay.py', 'tools/service_execution.py',
            'tools/tool_registry.py', 'tools/service_worker.py', 'tools/model_provider.py', 'schemas/platform_operations.py'),
        capabilities=dict(category='signals_diagnostics', role='public_tool',
            model='BackendResult signals' if binding.startswith('signals:') else 'saved MATLAB/MuJoCo exports',
            semantics='saved sample times and units; zero dynamics and no rescoring'),
        side_effects='current invocation materialization and immutable saved products'))
