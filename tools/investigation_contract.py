"""Versioned native investigation contract, shared by wire and executor.

Legacy sessions keep their original envelope. v2 never unwraps one.
"""
import json
from typing import Literal
from schemas.common import Contract
from schemas.platform import ToolRequest
from tools.platform_store import plain

VERSION = 'business_fields_v2'


class NativeInvestigationParameters(Contract):
    investigation_contract: Literal['business_fields_v2'] = VERSION


class SelectableFactParameters(Contract):
    investigation_contract: Literal['selectable_facts_v3'] = 'selectable_facts_v3'


class NativeContract:
    def __init__(self, definitions):
        # name -> (canonical ID, version, authoritative Pydantic schema)
        self.definitions = definitions

    def tools(self):
        return [dict(type='function', function=dict(name=name,
            description=identity+'@'+version+'; direct business fields only',
            parameters=schema.model_json_schema()))
            for name, (identity, version, schema) in self.definitions.items()]

    def parse(self, name, encoded):
        if name not in self.definitions:
            raise ValueError('RETURN_UNADVERTISED_NATIVE_FUNCTION')
        identity, version, schema = self.definitions[name]
        # JSON validation preserves JSON arrays for tuple fields; no text extraction.
        return schema.model_validate_json(encoded, strict=True)

    def request(self, name, encoded, turn):
        args = self.parse(name, encoded)
        identity, version, _ = self.definitions[name]
        return plain(ToolRequest(request_id=f'model-{turn}-tool', tool_id=identity,
            tool_version=version, arguments=plain(args),
            reason='Native investigation business decision under frozen v2 contract.'))


def contract(*,selectable=False):
    from schemas.platform_operations import ReadEvidence
    from tools.research_investigations import InvestigationReturn
    if selectable:
        from tools.disposition_facts import SelectedDisposition
        from pydantic import Field
        class SelectableReturn(InvestigationReturn):
            dispositions: list[SelectedDisposition] = Field(default_factory=list,max_length=3)
        InvestigationReturn=SelectableReturn
    return NativeContract(dict(
        investigation_return=('investigation_return', '3.0.0' if selectable else '2.0.0', InvestigationReturn),
        evidence_read=('evidence.read', '1.0.0', ReadEvidence)))


from tools.platform_models import DeepSeekAdapter,encode_chat,provider_name_map,ModelLengthTruncationError


class BusinessFieldsAdapter(DeepSeekAdapter):
    """v7: same domain contract for schema, strict parsing and ToolRequest."""
    def encode(self, model_input, config):
        payload=super().encode(model_input,config)
        from tools.platform_registry import registry
        names=provider_name_map(model_input.context['policy']['tool_bindings'],self.tool_naming_scheme)
        self.native_contract=NativeContract({names[d['extension_id']]:(d['extension_id'],d['version'],
            registry().get(d['extension_id'],d['version'],'tool').input_schema) for d in model_input.tools})
        payload['tools']=self.native_contract.tools()
        payload['messages'][0]['content']=model_input.content[0].text+' All tools accept direct business fields; the program constructs metadata. No outer argument envelope.'
        return payload

    def decode(self,response,turn,bindings,advertised_tools=None):
        choice=response.raw['choices'][0]
        if choice.get('finish_reason')=='length':raise ModelLengthTruncationError()
        calls=choice['message'].get('tool_calls',[])
        if len(calls)!=1 or calls[0].get('type')!='function':raise ValueError('RETURN_EXACTLY_ONE_NATIVE_FUNCTION_REQUIRED')
        fn=calls[0]['function']
        if advertised_tools is not None and fn['name'] not in {t['function']['name'] for t in advertised_tools}:raise ValueError('RETURN_UNADVERTISED_NATIVE_FUNCTION')
        return self.native_contract.request(fn['name'],fn['arguments'],turn)
