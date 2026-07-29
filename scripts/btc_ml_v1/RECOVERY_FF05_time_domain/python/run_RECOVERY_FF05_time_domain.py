from __future__ import annotations

import base64
import hashlib
import zlib
from pathlib import Path

_SOURCE_SHA256 = "b480a5abf0cf0179b4ba125ed9cdeef6f9fd593322fec1875d7490ec45bd5f7d"
_CHUNKS = ("source_01.b64", "source_02.b64", "source_03.b64")

_payload = "".join(
    Path(__file__).with_name(name).read_text(encoding="ascii").strip()
    for name in _CHUNKS
)
_source = zlib.decompress(base64.b64decode(_payload))
_actual = hashlib.sha256(_source).hexdigest()
if _actual != _SOURCE_SHA256:
    raise RuntimeError(
        f"embedded RECOVERY_FF05 time-domain source hash mismatch: "
        f"expected={_SOURCE_SHA256} actual={_actual}"
    )
exec(compile(_source, __file__, "exec"), globals(), globals())
