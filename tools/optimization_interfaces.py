"""Shared bounded coordinate proposal used by the active research search."""
def coordinate_proposal(state):
    """Exact bounded coordinate step of matlab/tdcr_search_step.m (1-based axis)."""
    x=list(state['best']);k=state['iteration'];axis=(k//2)%len(x);direction=1-2*(k%2)
    x[axis]=min(1.,max(0.,x[axis]+direction*state['step']))
    return dict(x=x,axis=axis+1,direction=direction,algorithm='bounded_coordinate_pattern_local_v1')
