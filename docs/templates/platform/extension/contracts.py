from typing import Literal
from pydantic import Field
from schemas.common import Contract


class Input(Contract):
    length_m: float = Field(ge=0)
    frame: Literal['world'] = 'world'


class Output(Contract):
    area_m2: float
    frame: Literal['world'] = 'world'
    scope: Literal['mathematical_only'] = 'mathematical_only'
