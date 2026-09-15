from tools.platform_registry import Extension
from .contracts import Input, Output

CONTRACTS = []
EXTENSIONS = [Extension('analysis.example_square', 'tool', '1.0.0', Input, Output,
    'extensions.example_math.implementation:execute', '长度平方的最小数学模板，无机器人物理结论',
    sources=('extensions/example_math/contracts.py', 'extensions/example_math/implementation.py',
             'extensions/example_math/manifest.py'), cache=True)]
