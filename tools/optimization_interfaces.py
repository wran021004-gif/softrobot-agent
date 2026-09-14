"""Search, parameter space, candidate creation and evaluation are independent."""
import math
from typing import Protocol
from schemas.framework import Evaluation


class Evaluator(Protocol):
    @property
    def identity(self) -> str: ...
    def evaluate(self, candidate, purpose: str) -> Evaluation: ...


class ParameterSpace:
    def __init__(self, variables, bounds, logarithmic=()):
        if not variables or len(set(variables))!=len(variables) or any(v not in bounds for v in variables):
            raise ValueError('INVALID_PARAMETER_SPACE')
        self.variables=tuple(variables);self.logs=set(logarithmic)
        self.bounds=[]
        for name in variables:
            lo,hi=bounds[name]
            if not all(math.isfinite(v) for v in (lo,hi)) or lo>=hi or (name in self.logs and lo<=0):
                raise ValueError('INVALID_PARAMETER_BOUNDS')
            self.bounds.append((math.log(lo),math.log(hi)) if name in self.logs else (lo,hi))

    def encode(self, values):
        result=[((math.log(values[n]) if n in self.logs else values[n])-lo)/(hi-lo)
            for n,(lo,hi) in zip(self.variables,self.bounds)]
        self.decode(result)
        return result

    def decode(self, vector):
        if len(vector)!=len(self.variables) or any(not math.isfinite(v) or not -1e-12<=v<=1+1e-12 for v in vector):
            raise ValueError('PARAMETERS_OUT_OF_BOUNDS')
        return {n:math.exp(lo+v*(hi-lo)) if n in self.logs else lo+v*(hi-lo)
                for n,(lo,hi),v in zip(self.variables,self.bounds,vector)}


def coordinate_proposal(state):
    """Exact bounded coordinate step of matlab/tdcr_search_step.m (1-based axis)."""
    x=list(state['best']);k=state['iteration'];axis=(k//2)%len(x);direction=1-2*(k%2)
    x[axis]=min(1.,max(0.,x[axis]+direction*state['step']))
    return dict(x=x,axis=axis+1,direction=direction,algorithm='bounded_coordinate_pattern_local_v1')


class MatlabCoordinateProposal:
    def __init__(self, book):self.book=book
    def propose(self, state, search_id):
        receipt,new=self.book.reserve('matlab_other',f'{search_id}:{state["iteration"]}')
        if new:
            import json
            proposal=json.loads(self.book.backends.engine().tdcr_search_step(json.dumps(state),nargout=1))
            self.book.finish(receipt,proposal=proposal)
        else:proposal=receipt.get('proposal')
        if not proposal:raise ValueError('INTERRUPTED_SEARCH_PROPOSAL: reservation retained')
        return proposal


def evaluation_from_result(out, actual=0):
    score=out.get('position_error_m')
    valid=out.get('complete') is True and out.get('computation_status') in ('completed','COMPLETED')
    valid=valid and type(score) in (float,int) and math.isfinite(score) and score>=0
    return Evaluation(status='VALID' if valid else 'INCOMPLETE' if not out.get('complete') else 'INVALID',
        score=float(score) if valid else None,task_success=out.get('canonical_task_success') if valid else None,
        evidence_ref=out.get('result_ref'),actual_evaluations=actual,reason=out.get('reason'))


class CampaignEvaluator:
    """Existing campaign remains owner of permissions, receipts and cache."""
    def __init__(self, book, backend):self.book,self.backend=book,backend
    @property
    def identity(self):
        from tools.state_io import digest
        return digest(dict(request=self.book.state['request'],backend=self.backend,sources=self.book.numerical_sources()))
    def evaluate(self, candidate, purpose):
        resource='matlab_dynamic' if self.backend=='matlab' else 'mujoco'
        before=self.book.ledger['used'][resource]
        out=self.book.simulate(candidate['candidate_id'],self.backend,purpose)
        return evaluation_from_result(out,self.book.ledger['used'][resource]-before)
