from src.hashing import sha256_bytes


def test_hash_changes_when_content_changes():
    first = sha256_bytes(b"original")
    second = sha256_bytes(b"modified")

    assert first != second
