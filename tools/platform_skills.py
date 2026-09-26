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
        checked=validate_skill(skill, root, evidence_store=PlatformEvidenceStore(host), tool_manifests=manifests, robot_families=[family])
        if checked.applicability.execution_scope is not None:
            for record in checked.validation:
                for run_id in (*record.validated_runs, *record.failed_validation_runs):
                    source=host.store.session(run_id)['snapshot']['input']
                    if scope_match(checked.applicability.execution_scope, source)!='matching':
                        raise ValueError('SKILL_VALIDATION_EXECUTION_SCOPE_MISMATCH')
        return checked
    return SkillRegistry(host.store.root / 'development_skills', host.store.root, validator=validate)


def applicable(host, reference):
    inp = host.store.session(host.run_id)['snapshot']['input']
    candidates = library(host).retrieve_skills(robot_family=inp['robot']['family'], task_type=inp['task']['family'],
        include_candidates=inp['policy']['allow_development_skills'])
    def same_model(skill):
        if skill.applicability.execution_scope is not None:
            return scope_match(skill.applicability.execution_scope, inp) != 'incompatible'
        # Old skill records have no explicit model-transfer scope. Keep their source
        # assumptions, never infer portability merely from a shared backend name.
        current = inp['robot']
        for run in skill.provenance.source_runs:
            try:
                source = host.store.session(run)['snapshot']['input']
            except ValueError:
                return False
            if source['robot'] != current or source['policy']['backend'] != inp['policy']['backend']:
                return False
        return True
    records=[]
    for s in candidates:
        if ((reference is not None and s.reference != reference)
                or set(s.required_tools)-set(inp['policy']['allowed_tools']) or not same_model(s)):
            continue
        record=s.model_dump(mode='json')
        if s.applicability.execution_scope is not None:
            match=scope_match(s.applicability.execution_scope, inp)
            record['scope_assessment']=dict(match=match, validation_applies=match=='matching',
                meaning='Only matching scope carries validation; changed configuration is an unvalidated starting point.')
        records.append(record)
    return records


def scope_match(scope, inp):
    # Scope is structured evidence metadata, never execution authorization.
    from extensions.tendon_family.gvs_profile import execution_scope
    current=execution_scope(inp)
    if current == scope:
        return 'matching'
    if (current['robot']['family'] != scope['robot']['family']
            or current['backend']['extension_id'] != scope['backend']['extension_id']
            or current['execution_model'] != scope['execution_model']
            or current['controller']['extension_id'] != scope['controller']['extension_id']
            or current['controller']['version'] != scope['controller']['version']
            or current['task']['family'] != scope['task']['family']):
        return 'incompatible'
    return 'unvalidated_starting_point'
