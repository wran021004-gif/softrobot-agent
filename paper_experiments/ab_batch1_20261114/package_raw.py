"""Lossless Git transport for large native evidence; never runs a simulation.

After cloning: python paper_experiments/ab_batch1_20261114/package_raw.py restore
"""
import argparse
import gzip
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'raw_archives.json'


def pack():
    sources = sorted(
        p for task in ('T01', 'T04', 'T07', 'PHS-2D')
        for method in ('A', 'B')
        for p in (ROOT / task / method).rglob('*')
        if p.is_file() and (
            p.suffix == '.sqlite'
            or ('physics' in p.relative_to(ROOT).parts and p.stat().st_size >= 1024**2)
        )
    )
    records = []
    for source in sources:
        relative = source.relative_to(ROOT).as_posix()
        destination = ROOT / 'RAW_ARCHIVE' / (relative + '.gz')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or destination.stat().st_mtime_ns < source.stat().st_mtime_ns:
            with source.open('rb') as reader, destination.open('wb') as target:
                with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0) as writer:
                    shutil.copyfileobj(reader, writer)
        # Reading to EOF checks gzip's CRC and uncompressed size, without a hash audit.
        with gzip.open(destination, 'rb') as reader:
            restored_size = 0
            while chunk := reader.read(1024**2):
                restored_size += len(chunk)
        assert restored_size == source.stat().st_size, relative
        archives = [destination]
        if destination.stat().st_size >= 100 * 1024**2:
            archives = []
            with destination.open('rb') as reader:
                while chunk := reader.read(40 * 1024**2):
                    part = destination.with_name(destination.name + f'.part{len(archives):03d}')
                    part.write_bytes(chunk)
                    archives.append(part)
            destination.unlink()  # Only this newly generated oversized gzip; native source stays intact.
        size = sum(p.stat().st_size for p in archives)
        records.append(dict(original=relative, archives=[p.relative_to(ROOT).as_posix() for p in archives],
                            original_bytes=restored_size, archive_bytes=size))
        print(relative, '->', size, flush=True)
    MANIFEST.write_text(json.dumps(dict(format='gzip', restore_command=
        'python paper_experiments/ab_batch1_20261114/package_raw.py restore',
        scope='Native A/B stores and large physical records; originals remain local and unchanged.',
        files=records), indent=2) + '\n', encoding='utf8')
    (ROOT / '.gitignore').write_text(
        '# Machine-local authority anchor; large originals have lossless archived copies.\n'
        '/runtime/\n/__pycache__/\n' + ''.join('/' + r['original'] + '\n' for r in records),
        encoding='utf8')
    print('Packed', len(records), 'files;', sum(r['archive_bytes'] for r in records), 'bytes')


def restore():
    for record in json.loads(MANIFEST.read_text(encoding='utf8'))['files']:
        destination = ROOT / record['original']
        if destination.exists():
            print('Already present:', record['original'])
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        archives = [ROOT / path for path in record['archives']]
        if len(archives) == 1:
            with gzip.open(archives[0], 'rb') as reader, destination.open('xb') as writer:
                shutil.copyfileobj(reader, writer)
        else:
            with tempfile.TemporaryFile() as combined:
                for archive in archives:
                    with archive.open('rb') as reader:
                        shutil.copyfileobj(reader, combined)
                combined.seek(0)
                with gzip.GzipFile(fileobj=combined) as reader, destination.open('xb') as writer:
                    shutil.copyfileobj(reader, writer)
        assert destination.stat().st_size == record['original_bytes'], record['original']
        print('Restored:', record['original'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('pack', 'restore'))
    {'pack': pack, 'restore': restore}[parser.parse_args().operation]()
