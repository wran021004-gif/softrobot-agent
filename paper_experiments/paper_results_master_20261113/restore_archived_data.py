"""Restore losslessly compressed result data after cloning. No simulation."""
from pathlib import Path
import gzip,shutil

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    for source in sorted((ROOT/'SOURCE_DATA').rglob('*.json.gz')):
        destination=source.with_suffix('')
        if destination.exists():
            print('Already present:',destination.relative_to(ROOT))
            continue
        with gzip.open(source,'rb') as reader,destination.open('xb') as writer:
            shutil.copyfileobj(reader,writer)
        print('Restored:',destination.relative_to(ROOT))
