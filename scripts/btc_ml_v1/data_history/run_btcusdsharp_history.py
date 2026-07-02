from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Sequence

import export_btcusdsharp_history as exporter


def _cleanup_failed_run(output_dir: Path) -> None:
    output_dir = output_dir.expanduser().resolve()
    (output_dir / "btcusdsharp_history_export.lock").unlink(missing_ok=True)
    suffix = f"_{os.getpid()}"
    for path in output_dir.glob(".btcusdsharp_stage_*"):
        if path.is_dir() and path.name.endswith(suffix):
            shutil.rmtree(path, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = exporter.parse_args(argv)
    output_dir = Path(args.output_dir)
    try:
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise SystemExit(
                "MetaTrader5 Python package is required on the user PC"
            ) from exc
        manifest = exporter.run_export(mt5, args)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    finally:
        _cleanup_failed_run(output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
