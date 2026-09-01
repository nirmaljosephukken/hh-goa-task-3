from pathlib import Path

from src.hashing import sha256_file


def test_sha256_file(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"hello")

    assert sha256_file(file_path) == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )
