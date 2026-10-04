"""Additive typed domains; archived two-number bounds remain valid."""
from typing import Literal
from pydantic import Field,model_validator
from schemas.common import Contract


class ContinuousDomain(Contract):
    kind: Literal['continuous'] = 'continuous'
    bounds: list[float] = Field(min_length=2,max_length=2)

    @model_validator(mode='after')
    def ordered(self):
        import math
        if not all(math.isfinite(v) for v in self.bounds) or self.bounds[0]>=self.bounds[1]:raise ValueError('INVALID_CONTINUOUS_DOMAIN')
        return self


class DiscreteDomain(Contract):
    kind: Literal['discrete'] = 'discrete'
    choices: list[str | float] = Field(min_length=1)

    @model_validator(mode='after')
    def unique(self):
        import math
        if len(set(self.choices))!=len(self.choices) or any(isinstance(v,float) and not math.isfinite(v) for v in self.choices):raise ValueError('INVALID_DISCRETE_DOMAIN')
        return self


ParameterDomain = list[float] | ContinuousDomain | DiscreteDomain


def domain(value):
    if isinstance(value,(ContinuousDomain,DiscreteDomain)):return value.model_dump(mode='json')
    if isinstance(value,(list,tuple)):return ContinuousDomain(bounds=list(value)).model_dump(mode='json')
    if value.get('kind')=='discrete':return DiscreteDomain.model_validate(value).model_dump(mode='json')
    return ContinuousDomain.model_validate(value).model_dump(mode='json')
