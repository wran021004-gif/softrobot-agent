import numpy as np
from .kernels import normalized,raw_scipy,summarize,versions
"""Pure shared mathematical scalar calculations used by the research evaluator."""
def calculate_control_metrics(model,protocol):
    """Calculation boundary shared by public tools and current candidate analysis."""
    A,B,C,D=normalized(model); drift=np.asarray(model.drift)/model.state_scales
    return summarize(model,protocol,raw_scipy(A,B,C,D,drift,protocol),dict(name='scipy',versions=versions(),matlab=None))
