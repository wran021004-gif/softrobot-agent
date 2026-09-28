"""Actionable domain-argument errors, before reservation or execution."""
import json
from pydantic import ValidationError


class ToolArgumentError(ValueError):
    def __init__(self, message):
        super().__init__('INVALID_TOOL_ARGUMENTS: '+message)


def validate_arguments(schema, arguments):
    try:
        return schema.model_validate_json(json.dumps(arguments, allow_nan=False), strict=True)
    except ValidationError as exc:
        issues = []
        for error in exc.errors(include_input=False, include_url=False):
            path = 'arguments.'+'.'.join(map(str, error['loc']))
            hint = error['msg']
            if error['loc'] == ('reason',) and error['type'] == 'extra_forbidden':
                hint += '; omit arguments.reason for this tool; keep the required OUTER reason'
            issues.append(path+': '+hint)
        fields = schema.model_fields
        required = ', '.join(k for k, v in fields.items() if v.is_required()) or '(none)'
        raise ToolArgumentError('; '.join(issues)+'. Required fields: '+required+
            '. Allowed fields: '+', '.join(fields)) from exc
