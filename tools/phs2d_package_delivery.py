"""Stage, index and atomically deliver an additive portable PHS benchmark package."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from phs2d_io import TASK_DIR, read, write, sha, require

# No legacy task, control, trajectory, artifact, or old script may change.
MUTABLE_ROOT = {'README.md','manifest.json','validation.json','viewer_validation.json',
                'delivery_report.json','delivery_report.md','export_audit.json','code_provenance.json'}


def snapshot(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def prepare(package, staging):
    require(package.is_dir() and not staging.exists(), 'REQUIRE_EXISTING_PACKAGE_AND_FRESH_STAGING')
    require(not (package/TASK_DIR).exists(), 'PHS_ALREADY_PRESENT')
    require(shutil.disk_usage(package).free >= 12*1024**3, 'INSUFFICIENT_SPACE_NO_FILES_REMOVED')
    manifest = read(package/'manifest.json')
    require(len(manifest['trajectories']) == 10, 'ORIGINAL_TEN_ACTIVE_TRAJECTORIES')
    before = snapshot(package)
    require(all(before.get(name) == identity for name,identity in manifest['files'].items()), 'ORIGINAL_PACKAGE_HASH_FAILURE')
    shutil.copytree(package, staging)
    write(staging/TASK_DIR/'evidence/legacy_hash_snapshot.json', dict(version='legacy_package_snapshot_v1',
        original_version=manifest['version'], files=before, mutable_root_files=sorted(MUTABLE_ROOT),
        original_manifest=manifest, original_zip_sha256=sha(package.with_suffix('.zip'))))
    require(snapshot(package) == before, 'ORIGINAL_PACKAGE_CHANGED_DURING_COPY')
    print(json.dumps(dict(status='staged', original_files=len(before), free_bytes=shutil.disk_usage(package).free)))


def index(staging):
    manifest = read(staging/'manifest.json')
    baseline = read(staging/TASK_DIR/'evidence/legacy_hash_snapshot.json')
    require(manifest['trajectories'] == baseline['original_manifest']['trajectories'], 'LEGACY_TRAJECTORIES_CHANGED')
    dataset = read(staging/TASK_DIR/'dataset.json')
    require(dataset['complete'] and len(dataset['trajectories']) == 11, 'PHS_DATASET_INCOMPLETE')
    manifest['version'] = 'base_only_package_v2_with_passive_phs2d'
    manifest['passive_benchmarks'] = [dict(type='passive_fixed_payout_v1', benchmark=TASK_DIR,
        directory=TASK_DIR, dataset=TASK_DIR+'/dataset.json', trajectories=dataset['trajectories'],
        classification=dataset['classification'])]
    manifest['phs2d_export_actual_mj_step_calls'] = 0
    manifest['actual_mj_step_calls_semantics'] = 'Legacy M1-M6 export historical count; PHS increment is zero.'
    manifest['files'] = {p.relative_to(staging).as_posix():sha(p) for p in sorted(staging.rglob('*'))
        if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts and '.viewer-env' not in p.parts}
    write(staging/'manifest.json', manifest)
    for name, identity in baseline['files'].items():
        if name not in MUTABLE_ROOT:
            require(sha(staging/name) == identity, 'LEGACY_FILE_CHANGED:'+name)
    print(json.dumps(dict(status='indexed', files=len(manifest['files']), active_trajectories=10, passive_trajectories=11)))


def publish(package, staging):
    baseline = read(staging/TASK_DIR/'evidence/legacy_hash_snapshot.json')
    original_state=snapshot(package) == baseline['files']
    if not original_state:
        # Permit correcting only this task's already published, hash-verified increment.
        current=read(package/'manifest.json')
        owned=read(package/'phs2d_delivery_report.json')
        require(current['version']=='base_only_package_v2_with_passive_phs2d' and
                owned['source_research_commit']==read(staging/'phs2d_delivery_report.json')['source_research_commit'],
                'NOT_AN_OWNED_PHS_INCREMENT')
        require(all(sha(package/p)==identity for p,identity in current['files'].items()),'CURRENT_INCREMENT_CHANGED')
        require(all(sha(package/p)==identity for p,identity in baseline['files'].items() if p not in MUTABLE_ROOT),
                'ORIGINAL_IMMUTABLE_FILE_CHANGED')
    manifest = read(staging/'manifest.json')
    require(all(sha(staging/p) == identity for p,identity in manifest['files'].items()), 'STAGING_HASH_FAILURE')
    require(read(staging/'validation.json')['status'] == 'passed', 'STAGING_VALIDATION_NOT_PASSED')
    total = sum((staging/p).stat().st_size for p in manifest['files'])
    require(shutil.disk_usage(package).free > 2*total+package.with_suffix('.zip').stat().st_size,
            'INSUFFICIENT_SPACE_OLD_ZIP_PRESERVED')
    archive = package.with_suffix('.zip')
    previous_zip_sha256=sha(archive)
    temporary = archive.with_name(archive.name+'.phs2d-building')
    require(not temporary.exists(), 'TEMPORARY_ZIP_ALREADY_EXISTS')
    paths = [staging/'manifest.json', *[staging/p for p in manifest['files']]]
    with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for path in paths:
            z.write(path, package.name+'/'+path.relative_to(staging).as_posix())
    with zipfile.ZipFile(temporary) as z:
        require(z.testzip() is None, 'ZIP_CRC_FAILURE')
        require(len(z.namelist()) == len(paths) and len(set(z.namelist())) == len(paths), 'ZIP_MEMBER_COUNT')
    # Verify all ZIP contents against SHA-256, not only CRC.
    import hashlib
    with zipfile.ZipFile(temporary) as z:
        for name, identity in manifest['files'].items():
            h = hashlib.sha256()
            with z.open(package.name+'/'+name) as stream:
                while block := stream.read(4*1024*1024): h.update(block)
            require(h.hexdigest() == identity, 'ZIP_MEMBER_SHA256:'+name)
    backup = archive.with_name(archive.stem+'.before_phs2d.zip')
    if not backup.exists():
        require(original_state,'ORIGINAL_BACKUP_REQUIRED_FOR_CORRECTION')
        shutil.copy2(archive, backup)
    require(sha(backup) == baseline['original_zip_sha256'], 'OLD_ZIP_BACKUP_HASH')
    require(original_state == (not (package/TASK_DIR).exists()),'PHS_DESTINATION_STATE_CHANGED')
    import_copy=package.parent/'.phs2d_verified_import_20261028'
    require(not import_copy.exists(),'TEMPORARY_IMPORT_DIRECTORY_ALREADY_EXISTS')
    shutil.copytree(staging/TASK_DIR, import_copy, ignore=shutil.ignore_patterns('__pycache__'))
    for name,identity in manifest['files'].items():
        if name.startswith(TASK_DIR+'/'):
            require(sha(import_copy/Path(name).relative_to(TASK_DIR))==identity,'IMPORTED_TASK_HASH')
    previous_import=package.parent/'.phs2d_previous_import_20261028'
    require(not previous_import.exists(),'PREVIOUS_IMPORT_BACKUP_ALREADY_EXISTS')
    if not original_state:os.replace(package/TASK_DIR,previous_import)
    os.replace(import_copy,package/TASK_DIR)
    for path in paths:
        name = path.relative_to(staging).as_posix()
        if name.startswith(TASK_DIR+'/') or name == 'manifest.json': continue
        target = package/name
        if name in baseline['files'] and name not in MUTABLE_ROOT:
            require(sha(target) == baseline['files'][name], 'LEGACY_TARGET_CHANGED:'+name)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name+'.phs2d-new')
        shutil.copyfile(path, temp)
        os.replace(temp, target)
    # Manifest is the last directory index to change.
    temp_manifest = package/'manifest.json.phs2d-new'
    shutil.copyfile(staging/'manifest.json', temp_manifest)
    os.replace(temp_manifest, package/'manifest.json')
    for name,identity in baseline['files'].items():
        if name not in MUTABLE_ROOT: require(sha(package/name) == identity, 'PRESERVATION_FAILURE:'+name)
    for name,identity in manifest['files'].items(): require(sha(package/name) == identity, 'PUBLISHED_FILE_HASH:'+name)
    os.replace(temporary, archive)
    report = dict(status='published',zip_file=archive.name,original_zip_backup=backup.name,
        manifest_sha256=sha(package/'manifest.json'),zip_bytes=archive.stat().st_size, zip_sha256=sha(archive),
        old_zip_backup_sha256=sha(backup),previous_zip_sha256=previous_zip_sha256,zip_crc_and_all_member_hashes='passed',
        all_legacy_immutable_files_preserved=True, physics_steps=0)
    write(staging.parent/(package.name+'.phs2d-publication.json'), report)
    if previous_import.exists():
        require(previous_import.resolve().parent==package.parent.resolve() and
                previous_import.name=='.phs2d_previous_import_20261028','UNSAFE_TEMPORARY_IMPORT_CLEANUP')
        shutil.rmtree(previous_import)
    print(json.dumps(report))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare','index','publish'])
    p.add_argument('--package', type=Path)
    p.add_argument('--staging', type=Path, required=True)
    args = p.parse_args()
    staging = args.staging.resolve()
    if args.action == 'index': index(staging)
    else:
        require(args.package is not None, '--package REQUIRED')
        package = args.package.resolve()
        require(package != staging and not staging.is_relative_to(package), 'ISOLATED_STAGING_REQUIRED')
        (prepare if args.action == 'prepare' else publish)(package, staging)


if __name__ == '__main__': main()
