from __future__ import annotations

import base64
import hashlib
from itertools import product
from pathlib import Path


def _unique(items: list[bytes]) -> list[bytes]:
    result: list[bytes] = []
    seen: set[bytes] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def raw_part_variants(data: bytes) -> list[bytes]:
    """Return only deterministic checkout/encoding repair candidates.

    GitHub's repository blob is authoritative. Some Windows checkouts can alter
    line endings, and a prior contents-API upload can UTF-8 encode a latin-1
    byte-preserving string. Every candidate is still rejected unless the full
    packaged payload matches the frozen SHA256.
    """
    bases = _unique([data, data.replace(b"\r\n", b"\n")])
    variants = list(bases)
    for value in bases:
        try:
            variants.append(value.decode("utf-8").encode("latin-1"))
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return _unique(variants)


def load_verified_payload(base: Path, expected_sha256: str) -> bytes:
    left_path = base / "runtime_payload_part00.raw"
    middle_path = base / "runtime_payload_part01.b64"
    right_path = base / "runtime_payload_part02.raw"
    missing = [str(path) for path in (left_path, middle_path, right_path) if not path.exists()]
    if missing:
        raise RuntimeError("Late Transition runtime payload files are missing: " + ", ".join(missing))

    left_variants = raw_part_variants(left_path.read_bytes())
    right_variants = raw_part_variants(right_path.read_bytes())
    middle_ascii = b"".join(middle_path.read_bytes().split())
    try:
        middle = base64.b64decode(middle_ascii, validate=True)
    except Exception as exc:
        raise RuntimeError("Late Transition Base64 payload part is invalid; pull the latest branch and retry") from exc

    observed: list[str] = []
    for left, right in product(left_variants, right_variants):
        payload = left + middle + right
        digest = hashlib.sha256(payload).hexdigest()
        observed.append(digest)
        if digest == expected_sha256:
            return payload

    detail = ",".join(observed[:8])
    raise RuntimeError(
        "Late Transition runtime payload SHA256 mismatch after safe checkout repair; "
        "pull the latest branch and retry. observed=" + detail
    )
