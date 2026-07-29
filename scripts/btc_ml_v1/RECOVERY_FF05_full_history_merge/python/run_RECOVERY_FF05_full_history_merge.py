from __future__ import annotations

import base64
import hashlib
import zlib
from pathlib import Path

_SOURCE_SHA256 = "d1cc7f79ebf820878b8cba2f1dee15981632032c57dc187426997d3ddb42ec49"
_payload = Path(__file__).with_name("source_01.b64").read_text(encoding="ascii").strip()
_source = zlib.decompress(base64.b64decode(_payload))
_actual = hashlib.sha256(_source).hexdigest()
if _actual != _SOURCE_SHA256:
    raise RuntimeError(
        f"embedded RECOVERY_FF05 full-history merge source hash mismatch: "
        f"expected={_SOURCE_SHA256} actual={_actual}"
    )
exec(compile(_source, __file__, "exec"), globals(), globals())
