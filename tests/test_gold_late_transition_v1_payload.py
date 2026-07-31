from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from pathlib import Path


def test_packaged_payload_binary_attributes_and_frozen_zip_sha() -> None:
    root = Path(__file__).resolve().parents[1]
    package = root / "scripts" / "gold_late_transition_v1"
    attributes = (root / ".gitattributes").read_text(encoding="utf-8")
    assert "runtime_payload_part00.raw binary" in attributes
    assert "runtime_payload_part02.raw binary" in attributes
    raw = (
        (package / "runtime_payload_part00.raw").read_bytes()
        + base64.b64decode((package / "runtime_payload_part01.b64").read_bytes(), validate=True)
        + (package / "runtime_payload_part02.raw").read_bytes()
    )
    assert hashlib.sha256(raw).hexdigest() == "0b59b0d91cf9dedaf81fd23c2b16fd03f23a44a790e4c5bf80914dbcb9e4c69a"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert sorted(archive.namelist()) == ["discord_notifier_core.py", "shadow_runtime_core.py"]
