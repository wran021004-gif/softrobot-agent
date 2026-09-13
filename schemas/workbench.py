"""JSON boundary shared by deterministic policies and future model adapters."""
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract


class WorkingMemory(Contract):
    findings: list[str] = Field(default_factory=list, max_length=4)
    unresolved: list[str] = Field(default_factory=list, max_length=4)
    next_action: str = Field(max_length=300)
    evidence: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def concise(self):
        if any(len(s) > 300 for s in self.findings + self.unresolved):
            raise ValueError('Memory notes must be brief observations, at most 300 characters each')
        return self


class Decision(Contract):
    action: Literal['continue', 'stop', 'capability_missing']
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)
    evidence: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=4000)
    working_memory: WorkingMemory | None = None

    @model_validator(mode='after')
    def consistent(self):
        if (self.action == 'continue') != (self.tool is not None):
            raise ValueError('Only continue selects a tool')
        if self.action != 'continue' and self.arguments:
            raise ValueError('Terminal decisions cannot carry arguments')
        return self


class NoArguments(Contract):
    pass


class EvaluationArguments(Contract):
    controller: Literal['C1'] = 'C1'


class EvidenceArguments(Contract):
    evidence_id: str = Field(min_length=1)
    pointer: str = Field(default='', description='JSON Pointer，如 /data/diagnostics 或 /metrics；空串选择根')
    offset: int = Field(default=0, ge=0, description='对象条目或数组元素的起始位置')
    limit: int = Field(default=10, ge=1, le=50)
    byte_offset: int = Field(default=0, ge=0, description='超大字段的 UTF-8 分片起点，使用上次返回的 next_byte_offset')
    max_bytes: int = Field(default=3000, ge=256, le=6000, description='本次内容字节上限，完整文件仍保存在磁盘')


class CandidateArguments(Contract):
    candidate_id: str = Field(pattern=r'^c\d{3}$')


class CreateCandidateArguments(Contract):
    parent_id: str = Field(pattern=r'^c\d{3}$')
    changes: dict = Field(min_length=1)


class CompareCandidatesArguments(Contract):
    candidate_ids: list[str] = Field(min_length=1, max_length=3)


class DeepSeekConfig(Contract):
    model: str = Field(pattern=r'^deepseek-[a-z0-9.-]+$')
    base_url: str
    thinking: Literal['disabled', 'enabled'] = 'disabled'
    context_turns: int | None = Field(default=None, description='旧配置兼容字段；不再按往返数重建会话')
    context_compact_ratio: float = Field(default=0.85, ge=0.5, le=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    max_input_bytes: int = Field(default=60000, ge=4000, le=200000)
    timeout_s: int = Field(default=90, ge=1, le=180)
    model_calls: int = Field(default=18, ge=1, le=40)
    model_failure_retries: int = Field(default=1, ge=0, le=2)
    candidates: int = Field(default=3, ge=1, le=3)
    simulations: int = Field(default=3, ge=0, le=3)
    computation_retries: int = Field(default=0, ge=0, le=1)
    tool_calls: int = Field(default=24, ge=1, le=40)
    decisions: int = Field(default=24, ge=1, le=40)
    tool_timeout_s: int = Field(default=180, ge=1, le=300)

    @model_validator(mode='after')
    def official_endpoint(self):
        from urllib.parse import urlsplit
        url = urlsplit(self.base_url)
        if (url.scheme != 'https' or url.netloc != 'api.deepseek.com'
                or url.path.rstrip('/') not in ('', '/v1') or url.query or url.fragment):
            raise ValueError('Use the official https://api.deepseek.com or /v1 endpoint')
        if self.simulations > self.candidates:
            raise ValueError('Simulation limit must not exceed candidate limit')
        return self


class WorkbenchResult(Contract):
    status: Literal['completed', 'failed', 'capability_missing', 'rejected', 'interrupted']
    tool: str
    failure_code: str | None = None
    message: str = ''
    data: dict = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
