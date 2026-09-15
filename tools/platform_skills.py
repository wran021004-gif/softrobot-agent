"""Existing SkillRegistry lifecycle with a platform evidence-reader adapter."""
import json
from types import SimpleNamespace
from schemas.evidence import ArtifactReference
from schemas.platform import EvidenceRef
from tools.platform_store import encode


class PlatformEvidenceStore:
    def __init__(self, host):
        self.host = host

    def run(self, run_id):
        snapshot = self.host.store.session(run_id)['snapshot']['input']
        return SimpleNamespace(random_seed=snapshot['seed'])

    def reference(self, run_id, path, pointer=None):
        return ArtifactReference(run_id=run_id, path=path, pointer=pointer)

    def resolve(self, ref):
        snapshot = self.host.store.session(ref.run_id)['snapshot']['input']
        if ref.path == 'task.yaml':
            value = dict(task_type=snapshot['task']['family'])
        elif ref.path == 'design_input.yaml':
            value = dict(robot_family=snapshot['robot']['family'])
        elif ref.path.startswith('objects/') and ref.path.endswith('.json'):
            identity = ref.path[len('objects/'):-len('.json')]
            if ref.sha256 != identity:
                raise ValueError('SKILL_SOURCE_HASH_REQUIRED')
            value = self.host.store.artifact(EvidenceRef(artifact_id=identity))
            events = self.host.store.events(ref.run_id)
            if not any(identity == output['artifact_id'] for event in events for output in event['outputs']):
                raise ValueError('SKILL_EVIDENCE_NOT_FROM_DECLARED_RUN')
        else:
            raise ValueError('PLATFORM_SKILL_EVIDENCE_PATH_UNSUPPORTED')
        if ref.pointer:
            for part in ref.pointer[1:].split('/'):
                key = part.replace('~1', '/').replace('~0', '~')
                value = value[int(key)] if isinstance(value, list) else value[key]
            return value
        return encode(value).encode('utf8')


def library(host):
    from skills.registry import SkillRegistry
    from tools.skill_policy import validate_skill
    snapshot = host.store.session(host.run_id)['snapshot']['input']
    family = snapshot['robot']['family']
    manifests = {d.extension_id: dict(implementation_status='IMPLEMENTED' if d.binding else 'PLANNED', implementation=d.binding,
        supported_robot_families=[family]) for d in host.reg.extensions.values() if d.kind == 'tool'}
    def validate(skill, root):
        if skill.provenance.source_findings:
            raise ValueError('PLATFORM_FINDING_ADAPTER_REQUIRED')
        return validate_skill(skill, root, evidence_store=PlatformEvidenceStore(host), tool_manifests=manifests, robot_families=[family])
    return SkillRegistry(host.store.root / 'development_skills', host.store.root, validator=validate)


def applicable(host, reference):
    inp = host.store.session(host.run_id)['snapshot']['input']
    candidates = library(host).retrieve_skills(robot_family=inp['robot']['family'], task_type=inp['task']['family'],
        include_candidates=inp['policy']['allow_development_skills'])
    return [s.model_dump(mode='json') for s in candidates if (reference is None or s.reference == reference)
        and not set(s.required_tools) - set(inp['policy']['allowed_tools'])]
