from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from scripts.gold_late_transition_v1.payload_loader import load_verified_payload, raw_part_variants


def write_parts(root: Path, left: bytes, middle: bytes, right: bytes) -> str:
    (root / "runtime_payload_part00.raw").write_bytes(left)
    (root / "runtime_payload_part01.b64").write_bytes(base64.encodebytes(middle))
    (root / "runtime_payload_part02.raw").write_bytes(right)
    return hashlib.sha256(left + middle + right).hexdigest()


def test_exact_payload_is_accepted(tmp_path: Path) -> None:
    expected = write_parts(tmp_path, b"PK\x00\xffleft", b"middle", b"right\x80")
    assert hashlib.sha256(load_verified_payload(tmp_path, expected)).hexdigest() == expected


def test_utf8_latin1_contents_api_expansion_is_repaired(tmp_path: Path) -> None:
    left = b"PK\x00\x80\xffleft"
    middle = b"middle\x00\xff"
    right = b"right\x90\xfe"
    expected = hashlib.sha256(left + middle + right).hexdigest()
    write_parts(
        tmp_path,
        left.decode("latin-1").encode("utf-8"),
        middle,
        right.decode("latin-1").encode("utf-8"),
    )
    assert hashlib.sha256(load_verified_payload(tmp_path, expected)).hexdigest() == expected


def test_utf8_expansion_plus_windows_crlf_is_repaired(tmp_path: Path) -> None:
    left = b"PK\n\x80\xffleft\n"
    middle = b"middle"
    right = b"right\n\x90\xfe"
    expected = hashlib.sha256(left + middle + right).hexdigest()
    write_parts(
        tmp_path,
        left.decode("latin-1").encode("utf-8").replace(b"\n", b"\r\n"),
        middle,
        right.decode("latin-1").encode("utf-8").replace(b"\n", b"\r\n"),
    )
    assert hashlib.sha256(load_verified_payload(tmp_path, expected)).hexdigest() == expected


def test_unrecognized_corruption_remains_fail_closed(tmp_path: Path) -> None:
    write_parts(tmp_path, b"bad-left", b"middle", b"bad-right")
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        load_verified_payload(tmp_path, "0" * 64)


def test_raw_variants_are_deduplicated() -> None:
    values = raw_part_variants(b"plain")
    assert values == [b"plain"]
