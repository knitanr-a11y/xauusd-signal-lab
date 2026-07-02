from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import export_btcusdsharp_history as exporter

DEFAULT_START = "2017-01-01"
DEFAULT_PACKAGE = Path("BTCUSD_H4_WARMUP_PACKAGE.zip")
DEFAULT_SUMMARY = Path("BTCUSD_H4_WARMUP_PASTE_THIS.txt")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _export_args(output_dir: Path, start: datetime, end: datetime, args: argparse.Namespace) -> Namespace:
    return Namespace(
        output_dir=str(output_dir),
        start=start.isoformat(),
        end=end.isoformat(),
        timeframes=["H4"],
        terminal_path=args.terminal_path,
        login=args.login,
        password=args.password,
        server=args.server,
    )


def build_package(mt5: Any, args: argparse.Namespace) -> dict[str, Any]:
    start = _parse_utc(args.start)
    end = datetime.now(timezone.utc).replace(microsecond=0)
    if start >= end:
        raise ValueError("start must be earlier than the current UTC time")

    package_path = Path(args.package).expanduser().resolve()
    summary_path = Path(args.summary).expanduser().resolve()
    stage_parent = Path(args.stage_parent).expanduser().resolve()
    package_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    stage_parent.mkdir(parents=True, exist_ok=True)

    stage_root = Path(tempfile.mkdtemp(prefix=".btcusd_h4_warmup_", dir=str(stage_parent)))
    temporary_zip = package_path.with_name(package_path.name + f".tmp.{os.getpid()}")
    try:
        export_dir = stage_root / "export"
        export_dir.mkdir(parents=True, exist_ok=False)
        manifest = exporter.run_export(mt5, _export_args(export_dir, start, end, args))
        if len(manifest.get("timeframes", [])) != 1:
            raise RuntimeError("H4 export manifest did not contain exactly one timeframe")
        item = manifest["timeframes"][0]
        csv_path = export_dir / item["path"]
        if item.get("timeframe") != "H4" or not csv_path.is_file():
            raise RuntimeError("H4 CSV was not created")

        package_manifest = {
            "schema_version": 1,
            "stage": "BTC_H4_MT5_EMA_WARMUP_EXPORT",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": exporter.SYMBOL,
            "requested_start_utc": start.strftime("%Y-%m-%d %H:%M:%S"),
            "snapshot_end_utc": end.strftime("%Y-%m-%d %H:%M:%S"),
            "latest_row_contract": "CLOSED_ONLY",
            "purpose": "MT5 EMA20/EMA200 and ATR14 warm-up parity before BTC-3 recalculation",
            "orders_enabled": False,
            "discord_enabled": False,
            "live_ready": False,
            "final_signal": False,
            "timeframe": item,
            "warnings": manifest.get("warnings") or [],
        }
        manifest_path = stage_root / "btcusdsharp_h4_warmup_manifest.json"
        manifest_path.write_text(
            json.dumps(package_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        lines = [
            "BTCUSD# H4 WARMUP RESULT",
            f"symbol: {package_manifest['symbol']}",
            f"requested_start_utc: {package_manifest['requested_start_utc']}",
            f"snapshot_end_utc: {package_manifest['snapshot_end_utc']}",
            f"rows: {item['rows']}",
            f"first: {item['first_time_utc']}",
            f"last: {item['last_time_utc']}",
            f"gaps: {item['gaps_over_one_bar']}",
            "purpose: mature MT5 EMA20/EMA200 warm-up for BTC-3 recalculation",
        ]
        in_zip_summary = stage_root / "BTCUSD_H4_WARMUP_PASTE_THIS.txt"
        in_zip_summary.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with zipfile.ZipFile(
            temporary_zip,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as archive:
            archive.write(csv_path, arcname=csv_path.name)
            archive.write(manifest_path, arcname=manifest_path.name)
            archive.write(in_zip_summary, arcname=in_zip_summary.name)
        os.replace(temporary_zip, package_path)

        package_manifest["package_path"] = str(package_path)
        package_manifest["package_bytes"] = package_path.stat().st_size
        package_manifest["package_sha256"] = _sha256(package_path)
        lines.extend(
            [
                f"package: {package_path.name}",
                f"package_size_mb: {package_path.stat().st_size / (1024 * 1024):.3f}",
                f"package_sha256: {package_manifest['package_sha256']}",
            ]
        )
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return package_manifest
    finally:
        temporary_zip.unlink(missing_ok=True)
        shutil.rmtree(stage_root, ignore_errors=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export only BTCUSD# H4 from 2017 for MT5 EMA warm-up recalculation."
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--stage-parent", default="Files")
    parser.add_argument("--terminal-path")
    parser.add_argument("--login")
    parser.add_argument("--password")
    parser.add_argument("--server")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit(
            "MetaTrader5 Python package is required. Run: python -m pip install MetaTrader5"
        ) from exc
    result = build_package(mt5, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
