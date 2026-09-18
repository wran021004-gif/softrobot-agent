"""Legacy import alias; current platform code uses tools.model_transports."""
import sys
from tools.legacy import workbench_deepseek

sys.modules[__name__] = workbench_deepseek
