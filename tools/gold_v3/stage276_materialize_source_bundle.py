from __future__ import annotations

import base64
import hashlib
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO_ROOT = BASE.parents[1]
BUNDLE_TEXT = BASE / "stage276_source_bundle_20260622.zip.b64"
EXPECTED_ZIP_SHA256 = "06c9a0547a177e539a60fb2232387cc58db67ea7ecfc33f593d2e89b83ff91e6"
EXPECTED_CORE_SHA256 = "c2d4b1d382cd382eea9a2be80bd9e6d38525aa7a7198644dc87532c24f3ac922"

DESTINATIONS = {
    "stage276_sequence_state_transition_audit.py": BASE / "stage276_sequence_state_transition_audit.py",
    "stage276_prefix_feature_parity.py": BASE / "stage276_prefix_feature_parity.py",
    "stage276_run_all.py": BASE / "stage276_run_all_materialized.py",
    "test_stage276_sequence_state_transition.py": REPO_ROOT / "tests" / "gold_v3" / "test_stage276_sequence_state_transition.py",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    encoded = "".join(BUNDLE_TEXT.read_text(encoding="ascii").split())
    archive = base64.b64decode(encoded, validate=True)
    actual_zip_sha = sha256(archive)
    if actual_zip_sha != EXPECTED_ZIP_SHA256:
        raise RuntimeError(
            f"Stage276 source bundle SHA mismatch: {actual_zip_sha} != {EXPECTED_ZIP_SHA256}"
        )

    zip_path = BASE / ".stage276_source_bundle_verified.zip"
    zip_path.write_bytes(archive)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member, destination in DESTINATIONS.items():
                data = zf.read(member)
                if member == "stage276_sequence_state_transition_audit.py":
                    actual_core_sha = sha256(data)
                    if actual_core_sha != EXPECTED_CORE_SHA256:
                        raise RuntimeError(
                            f"Stage276 core SHA mismatch: {actual_core_sha} != {EXPECTED_CORE_SHA256}"
                        )
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                print(f"materialized {destination}")
    finally:
        zip_path.unlink(missing_ok=True)

    print("Stage276 verified source materialization PASS")


if __name__ == "__main__":
    main()
