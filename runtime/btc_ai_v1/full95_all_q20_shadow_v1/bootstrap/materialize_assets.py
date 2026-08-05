#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, os, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("materialize_assets_manifest.json")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as h:
            h.write(data); h.flush(); os.fsync(h.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def main() -> int:
    spec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, item in spec.items():
        compressed = b"".join(base64.b64decode((ROOT / rel).read_text(encoding="ascii"), validate=True) for rel in item["chunks"])
        if len(compressed) != item["compressed_bytes"]:
            raise RuntimeError(f"FROZEN_BUNDLE_COMPRESSED_SIZE_MISMATCH: {name}")
        raw = gzip.decompress(compressed)
        if len(raw) != item["bytes"] or sha256(raw) != item["sha256"]:
            raise RuntimeError(f"FROZEN_BUNDLE_MATERIALIZATION_MISMATCH: {name}")
        out = ROOT / item["output"]
        if not out.exists() or out.read_bytes() != raw:
            atomic_write(out, raw)
        if sha256(out.read_bytes()) != item["sha256"]:
            raise RuntimeError(f"MATERIALIZED_ASSET_HASH_MISMATCH: {out}")
    print(json.dumps({"status":"MATERIALIZED_FROZEN_ASSETS_VERIFIED","asset_count":len(spec)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
