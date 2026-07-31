from pathlib import Path
import base64
import hashlib
import io
import zipfile

_BASE = Path(__file__).parent
_PAYLOAD = (
    (_BASE / "runtime_payload_part00.raw").read_bytes()
    + base64.b64decode((_BASE / "runtime_payload_part01.b64").read_bytes(), validate=True)
    + (_BASE / "runtime_payload_part02.raw").read_bytes()
)
_EXPECTED_SHA256 = "0b59b0d91cf9dedaf81fd23c2b16fd03f23a44a790e4c5bf80914dbcb9e4c69a"
if hashlib.sha256(_PAYLOAD).hexdigest() != _EXPECTED_SHA256:
    raise RuntimeError("Late Transition runtime payload SHA256 mismatch; pull the latest branch and retry")
with zipfile.ZipFile(io.BytesIO(_PAYLOAD)) as archive:
    _SOURCE = archive.read("discord_notifier_core.py").decode("utf-8")
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())
