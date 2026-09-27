"""Existing SkillRegistry lifecycle with a platform evidence-reader adapter."""
import json
from types import SimpleNamespace
from schemas.evidence import ArtifactReference
from schemas.platform import EvidenceRef
from tools.platform_store import encode


def skill_source(host,run_id):
    """Local sessions or explicitly imported historical evidence, never executable authority."""
    with host.store.connect(True) as db:
        if db.execute('SELECT 1 FROM sessions WHERE run_id=?',(run_id,)).fetchone():
            return host.store.session(run_id)['snapshot']['input'],host.store.events(run_id)
        row=db.execute('SELECT value FROM meta WHERE key=?',('skill_source:'+run_id,)).fetchone()
    if row is None: raise ValueError('SKILL_SOURCE_NOT_IMPORTED: '+run_id)
    source=host.store.artifact(json.loads(row[0]))
    return source['snapshot']['input'],source['events']


def import_skill_history(host,source_root,source_run):
    """Trusted preparation: preserve revisions and source bytes without importing grants/calls/sessions."""
    from tools.platform_host import Host
    from tools.platform_store import plain
    source=Host(source_root,source_run)
    history=library(source).history()  # Verify original lifecycle and evidence before import.
    runs={run for revisions in history.values() for row in revisions
        for run in row.skill.provenance.source_runs}
    records={run:dict(source_root=str(source.store.root),source_project=source.store.config()['project_id'],
        snapshot=source.store.session(run)['snapshot'],events=source.store.events(run)) for run in runs}
    with source.store.connect(True) as original,host.store.transaction() as db:
        # Preserve content-addressed artifacts (including nested references) exactly.
        for row in original.execute('SELECT id,media,body FROM artifacts'):
            ref=host.store.put(db,bytes(row['body']),row['media'])
            if ref.artifact_id!=row['id']: raise ValueError('IMPORTED_ARTIFACT_HASH_MISMATCH')
        for run,record in records.items():
            ref=host.store.put(db,record)
            db.execute('INSERT INTO meta VALUES (?,?)',('skill_source:'+run,encode(ref)))
        imported=host.store.put(db,dict(source_root=str(source.store.root),source_runs=sorted(runs),
            authority_imported=False,session_rows_imported=False,call_rows_imported=False))
        host.store.event(db,host.run_id,'skill_history_import','imported',outputs=[imported])
    for path in (source.store.root/'development_skills').glob('*/*.yaml'):
        destination=host.store.root/'development_skills'/path.parent.name/path.name
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as stream: stream.write(path.read_bytes())
    library(host).history()
    return plain(imported)


class PlatformEvidenceStore:
    def __init__(self, host):
        self.host = host

    def run(self, run_id):
        snapshot,_ = skill_source(self.host,run_id)
        return SimpleNamespace(random_seed=snapshot['seed'])

    def reference(self, run_id, path, pointer=None):
        return ArtifactReference(run_id=run_id, path=path, pointer=pointer)

    def resolve(self, ref):
        snapshot,events = skill_source(self.host,ref.run_id)
        if ref.path == 'task.yaml':
            value = dict(task_type=snapshot['task']['family'])
        elif ref.path == 'design_input.yaml':
            value = dict(robot_family=snapshot['robot']['family'])
        elif ref.path.startswith('objects/') and ref.path.endswith('.json'):
            identity = ref.path[len('objects/'):-len('.json')]
            if ref.sha256 != identity:
                raise ValueError('SKILL_SOURCE_HASH_REQUIRED')
            value = self.host.store.artifact(EvidenceRef(artifact_id=identity))
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
                    source,_=skill_source(host,run_id)
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
                source,_ = skill_source(host,run)
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
