from pathlib import Path
import base64
import hashlib
import io
import zipfile


def test_ascii_base64_payload_matches_frozen_zip_sha() -> None:
    root = Path(__file__).resolve().parents[1]
    package = root / "scripts" / "gold_late_transition_v1"

    def decode(name: str) -> bytes:
        encoded = b"".join((package / name).read_bytes().split())
        return base64.b64decode(encoded, validate=True)

    raw = (
        decode("runtime_payload_part00_v2.raw")
        + decode("runtime_payload_part01.b64")
        + decode("runtime_payload_part02_v2.b64")
    )
    assert hashlib.sha256(raw).hexdigest() == "0b59b0d91cf9dedaf81fd23c2b16fd03f23a44a790e4c5bf80914dbcb9e4c69a"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert sorted(archive.namelist()) == ["discord_notifier_core.py", "shadow_runtime_core.py"]
