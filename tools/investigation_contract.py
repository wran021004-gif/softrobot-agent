"""Versioned native investigation contract, shared by wire and executor.

Legacy sessions keep their original envelope. v2 never unwraps one.
"""
import json
from schemas.platform import ToolRequest
from tools.platform_store import plain

VERSION = 'business_fields_v2'


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


def contract():
    from schemas.platform_operations import ReadEvidence
    from tools.research_investigations import InvestigationReturn
    return NativeContract(dict(
        investigation_return=('investigation_return', '2.0.0', InvestigationReturn),
        evidence_read=('evidence.read', '1.0.0', ReadEvidence)))
