from tools.platform_registry import Extension
from .contracts import PeakInput, PeakOutput

CONTRACTS = []
EXTENSIONS = [
    Extension(
        extension_id="analysis.force_peak",
        kind="tool",
        version="1.0.0",
        input_schema=PeakInput,
        output_schema=PeakOutput,
        binding="extensions.learning_peak.implementation:calculate",
        description="计算力序列的最大绝对值；输入输出单位为牛顿，不判断机器人任务成功。",
        sources=(
            "extensions/learning_peak/contracts.py",
            "extensions/learning_peak/implementation.py",
            "extensions/learning_peak/manifest.py",
        ),
        cache=True,
        capabilities=dict(category='mathematical_models', role='teaching_example',
            semantics='force sequence N -> maximum absolute force N; no task-success claim'),
    )
]
