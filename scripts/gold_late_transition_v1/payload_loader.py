from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def _decode_base64_file(path: Path) -> bytes:
    if not path.exists():
        raise RuntimeError(f"Late Transition runtime payload file is missing: {path}")
    encoded = b"".join(path.read_bytes().split())
    try:
        return base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError(
            f"Late Transition Base64 payload file is invalid: {path.name}; "
            "pull the latest branch and retry"
        ) from exc


def load_verified_payload(base: Path, expected_sha256: str) -> bytes:
    """Rebuild the frozen payload from ASCII-only Base64 repository files.

    All three transport files are plain ASCII text. CRLF/LF conversion is
    harmless because whitespace is removed before strict Base64 decoding.
    The payload is accepted only when its full frozen SHA256 matches.
    """
    payload = b"".join(
        [
            _decode_base64_file(base / "runtime_payload_part00_v2.raw"),
            _decode_base64_file(base / "runtime_payload_part01.b64"),
            _decode_base64_file(base / "runtime_payload_part02_v2.b64"),
        ]
    )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(
            "Late Transition Base64 payload SHA256 mismatch; "
            f"expected={expected_sha256} observed={digest}. "
            "Pull the latest branch and retry."
        )
    return payload
