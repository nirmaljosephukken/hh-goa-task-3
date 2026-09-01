from .blockchain import verify_hash
from .hashing import sha256_file


def verify_file(w3, contract, file_path: str):
    digest = sha256_file(file_path)
    exists, source_url, timestamp, submitter = verify_hash(
        w3, contract, digest
    )

    return {
        "local_hash": digest,
        "exists": bool(exists),
        "source_url": source_url,
        "timestamp": int(timestamp),
        "submitter": submitter,
        "verified": bool(exists),
    }
