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
        description="Compute the maximum absolute value of a force sequence; input and output in newtons; does not judge robot task success.",
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
