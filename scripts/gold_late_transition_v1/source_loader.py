from __future__ import annotations

import hashlib
from pathlib import Path

_SOURCE_SHA256 = {
    "shadow_runtime": "246d701cbfbea0560e1e859f61c9587ee438459fcdd5739d9f1f11bab9431915",
    "discord_notifier": "89ac045ab756dc736cd21d444d1c8dd6a16e2080d963b9d72c895af73f4cf0fb",
}


def load_verified_source(base: Path, stem: str) -> str:
    paths = sorted(base.glob(f"{stem}_source_*.pytxt"))
    if not paths:
        raise RuntimeError(f"Late Transition UTF-8 source segments are missing: {stem}")
    source = "".join(path.read_text(encoding="utf-8") for path in paths)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    expected = _SOURCE_SHA256[stem]
    if digest != expected:
        raise RuntimeError(
            f"Late Transition UTF-8 source SHA256 mismatch for {stem}; "
            "pull the latest branch and retry"
        )
    return source
