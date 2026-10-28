"""Extract the final ZIP to a fresh path and run all 21 zero-integration checks."""
import argparse
import json
import os
from pathlib import Path,PurePosixPath
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phs2d_io import read,write,require,sha


def check(archive,output,report_path,publication):
    require(not output.exists(),'FRESH_EXTRACTION_DIRECTORY_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    roots=set()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            path=PurePosixPath(member.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in member.filename,
                    'UNSAFE_ZIP_RELATIVE_PATH')
            target=(output/Path(*path.parts)).resolve()
            require(target.is_relative_to(output.resolve()),'ZIP_PATH_ESCAPE')
            roots.add(path.parts[0])
        require(len(roots)==1,'ONE_PACKAGE_ROOT_REQUIRED')
        z.extractall(output)
    package=output/roots.pop()
    print(json.dumps(dict(action='zip_extracted',arbitrary_path_with_spaces_and_unicode=True)),flush=True)
    command=[sys.executable,'-B',str(package/'scripts/validate_all.py'),'--package',str(package),'--report',str(report_path)]
    environment={**os.environ,'PYTHONIOENCODING':'utf-8'}
    process=subprocess.Popen(command,cwd=package,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,encoding='utf8',env=environment)
    captured=[]
    for line in process.stdout:
        captured.append(line)
        if line.startswith('{"condition"'):print(line.rstrip(),flush=True)
    code=process.wait()
    if code:
        print(''.join(captured),flush=True)
        raise SystemExit(code)
    report=read(report_path)
    require(report['status']=='passed' and len(report['active']['results'])==10 and len(report['passive']['results'])==11
            and report['physics_steps']==0,'ROUNDTRIP_VALIDATION_FAILED')
    result=dict(status='passed',active_trajectories=10,passive_trajectories=11,physics_steps=0,
        all_member_sha256_and_relative_paths='passed',manifest_sha256=sha(package/'manifest.json'),
        zip_sha256=sha(archive),arbitrary_path_with_spaces_and_unicode=True)
    if publication:
        published=read(publication)
        require(published['zip_sha256']==result['zip_sha256'] and published['manifest_sha256']==result['manifest_sha256'],
                'PUBLISHED_ARCHIVE_IDENTITY_CHANGED')
        published['zip_extraction_validation']=result
        write(publication,published)
    print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('archive','output','report'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--publication',type=Path);args=p.parse_args()
    check(args.archive.resolve(),args.output.resolve(),args.report.resolve(),args.publication.resolve() if args.publication else None)


if __name__=='__main__':main()
