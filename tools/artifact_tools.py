"""Content hashing used by scientific dependency and file evidence checks."""
import hashlib
def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
