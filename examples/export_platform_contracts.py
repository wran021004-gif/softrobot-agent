"""Generate public contract/catalog projections from authoritative Python types."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schemas import platform
from schemas.common import Contract
from tools.platform_registry import registry
from tools.platform_store import encode
from tools.spec_tools import ROOT


def export():
    target = ROOT / 'docs/platform_generated'
    target.mkdir(parents=True, exist_ok=True)
    contracts = {name: cls.model_json_schema() for name, cls in vars(platform).items()
        if isinstance(cls, type) and issubclass(cls, Contract) and cls.__module__ == platform.__name__}
    from tools.platform_physics import ModelQuantityRequest, ModelQuantityResult
    contracts.update({cls.__name__: cls.model_json_schema() for cls in (ModelQuantityRequest, ModelQuantityResult)})
    reg = registry()
    contracts['payloads'] = {name + '@' + version: schema.model_json_schema() for (name, version), schema in sorted(reg.contracts.items())}
    for name, value in [('contracts.json', contracts), ('capabilities.json', reg.catalog())]:
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    schema = platform.TaskDefinition.model_json_schema()
    fields = [dict(field=name, required=name in schema['required'], default=spec.get('default'), schema=spec)
        for name, spec in schema['properties'].items()]
    (target / 'task_fields.json').write_text(json.dumps(fields, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    lines = ['# 公共能力目录（生成）', '', '由 `python examples/export_platform_contracts.py` 生成；不是授权清单。', '',
        '分类、内部库和兼容入口说明见 [领域能力边界](../platform_domain.md)。存在绑定不代表物理验证。', '',
        '| 身份 | 分类 | 角色 | 类型 | 版本 | 实现存在 | 绑定入口 | 说明 |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
    lines += [f"| {r['extension_id']} | {r['capabilities'].get('category', 'platform_services')} | {r['capabilities'].get('role', 'adapter')} | {r['kind']} | {r['version']} | {r['implementation_exists']} | {r['binding'] or '未实现'} | {r['description']} |" for r in reg.catalog()]
    (target / 'catalog.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    return dict(contracts=len(contracts) - 1, payloads=len(reg.contracts), extensions=len(reg.extensions))


if __name__ == '__main__':
    print(export())
