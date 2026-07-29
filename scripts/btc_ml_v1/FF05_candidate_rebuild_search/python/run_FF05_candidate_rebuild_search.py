from __future__ import annotations

import base64
import hashlib
import zlib
from pathlib import Path

_SOURCE_SHA256 = "3f03979249e22d17a54ff2814147eb5edb1a6d8d0bb8734aa4eb6e9537968715"
_CHUNK_NAMES = tuple(f"source_{index:02d}.b64" for index in range(1, 7))

_payload_parts: list[str] = []
for _name in _CHUNK_NAMES:
    _path = Path(__file__).with_name(_name)
    if not _path.is_file():
        raise RuntimeError(f"missing embedded FF05 source chunk: {_path}")
    _payload_parts.append(_path.read_text(encoding="ascii").strip())

_source = zlib.decompress(base64.b64decode("".join(_payload_parts)))
_actual = hashlib.sha256(_source).hexdigest()
if _actual != _SOURCE_SHA256:
    raise RuntimeError(
        f"embedded FF05 source hash mismatch: expected={_SOURCE_SHA256} actual={_actual}"
    )
exec(compile(_source, __file__, "exec"), globals(), globals())
