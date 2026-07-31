from pathlib import Path
import io
import zipfile

_PARTS = [
    "runtime_payload_part00.bin",
    "runtime_payload_part01.bin",
    "runtime_payload_part02.bin",
]
_PAYLOAD = b"".join(Path(__file__).with_name(part).read_bytes() for part in _PARTS)
with zipfile.ZipFile(io.BytesIO(_PAYLOAD)) as archive:
    _SOURCE = archive.read("shadow_runtime.py").decode("utf-8")
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())
