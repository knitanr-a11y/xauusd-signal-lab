from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import export_btcusdsharp_history as exporter

DEFAULT_PACKAGE = Path("BTCUSD_HISTORY_CHAT_PACKAGE.zip")
DEFAULT_SUMMARY = Path("BTCUSD_HISTORY_PASTE_THIS.txt")
DEFAULT_M1_DAYS = 90
DEFAULT_M5_DAYS = 730
DEFAULT_CORE_DAYS = 730
TIMEFRAME_ORDER = ("M1", "M5", "M15", "H1", "H4", "D1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _export_args(
    *,
    output_dir: Path,
    start_utc: datetime,
    end_utc: datetime,
    timeframes: Sequence[str],
    args: argparse.Namespace,
) -> Namespace:
    return Namespace(
        output_dir=str(output_dir),
        start=start_utc.isoformat(),
        end=end_utc.isoformat(),
        timeframes=list(timeframes),
        terminal_path=args.terminal_path,
        login=args.login,
        password=args.password,
        server=args.server,
    )


def _summary_lines(manifest: dict[str, Any]) -> list[str]:
    lines = [
        "BTCUSD# CHAT PACKAGE RESULT",
        f"generated_at_utc: {manifest['generated_at_utc']}",
        f"symbol: {manifest['symbol']}",
        "compression: standard ZIP / DEFLATE / no password",
        "usage: upload BTCUSD_HISTORY_CHAT_PACKAGE.zip to this chat",
        "",
        "PURPOSE",
        "M1: short execution, spread and same-bar audit window",
        "M5: candidate timing and later TP/SL first-touch evaluation",
        "M15/H1/H4/D1: candidate discovery and higher-timeframe context",
        "",
        "TIMEFRAMES",
    ]
    by_timeframe = {item["timeframe"]: item for item in manifest["timeframes"]}
    for timeframe in TIMEFRAME_ORDER:
        item = by_timeframe.get(timeframe)
        if item is None:
            continue
        lines.append(
            f"{timeframe}: rows={item['rows']}, first={item['first_time_utc']}, "
            f"last={item['last_time_utc']}, gaps={item['gaps_over_one_bar']}, "
            f"max_gap_seconds={item['maximum_gap_seconds']}"
        )
    warnings = manifest.get("warnings") or []
    if warnings:
        lines.extend(["", "WARNINGS"])
        lines.extend(f"- {warning}" for warning in warnings)
    return lines


def build_package(mt5: Any, args: argparse.Namespace) -> dict[str, Any]:
    package_path = Path(args.package).expanduser().resolve()
    summary_path = Path(args.summary).expanduser().resolve()
    package_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = datetime.now(timezone.utc).replace(microsecond=0)
    profiles = [
        ("m1", ("M1",), int(args.m1_days)),
        ("m5", ("M5",), int(args.m5_days)),
        ("core", ("M15", "H1", "H4", "D1"), int(args.core_days)),
    ]
    for name, _timeframes, days in profiles:
        if days <= 0:
            raise ValueError(f"{name} days must be greater than zero")

    stage_parent = Path(args.stage_parent).expanduser().resolve()
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(prefix=".btcusd_chat_stage_", dir=str(stage_parent))
    )
    temporary_zip = package_path.with_name(package_path.name + f".tmp.{os.getpid()}")

    manifests: list[dict[str, Any]] = []
    csv_sources: dict[str, Path] = {}
    try:
        for profile_name, timeframes, days in profiles:
            output_dir = stage_root / profile_name
            output_dir.mkdir(parents=True, exist_ok=False)
            start = snapshot - timedelta(days=days)
            manifest = exporter.run_export(
                mt5,
                _export_args(
                    output_dir=output_dir,
                    start_utc=start,
                    end_utc=snapshot,
                    timeframes=timeframes,
                    args=args,
                ),
            )
            manifests.append(manifest)
            for item in manifest["timeframes"]:
                source = output_dir / item["path"]
                if not source.is_file():
                    raise RuntimeError(f"exported CSV missing: {source}")
                csv_sources[item["timeframe"]] = source

        exports = [
            item
            for timeframe in TIMEFRAME_ORDER
            for manifest in manifests
            for item in manifest["timeframes"]
            if item["timeframe"] == timeframe
        ]
        uncompressed_bytes = sum(path.stat().st_size for path in csv_sources.values())
        warnings = [
            warning
            for manifest in manifests
            for warning in (manifest.get("warnings") or [])
        ]
        combined = {
            "schema_version": 1,
            "stage": "BTC_CHAT_UPLOAD_PACKAGE_BEFORE_CANDIDATE_DISCOVERY",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "snapshot_end_utc": snapshot.strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": exporter.SYMBOL,
            "time_basis": "UTC_NAIVE_FROM_MT5_EPOCH",
            "latest_row_contract": "CLOSED_ONLY",
            "compression": "ZIP_DEFLATED_LEVEL_9_NO_PASSWORD",
            "orders_enabled": False,
            "discord_enabled": False,
            "live_ready": False,
            "final_signal": False,
            "candidate_discovery_started": False,
            "profile_days": {
                "M1": int(args.m1_days),
                "M5": int(args.m5_days),
                "M15_H1_H4_D1": int(args.core_days),
            },
            "intended_use": {
                "M1": "execution_spread_and_same_bar_audit_only",
                "M5": "candidate_timing_and_future_first_touch_evaluation",
                "M15_H1_H4_D1": "candidate_discovery_and_higher_timeframe_context",
            },
            "csv_uncompressed_bytes": uncompressed_bytes,
            "timeframes": exports,
            "warnings": warnings,
            "symbol_contract": manifests[0].get("symbol_contract", {}),
            "terminal": manifests[0].get("terminal", {}),
            "account": manifests[0].get("account", {}),
        }

        manifest_path = stage_root / "btcusdsharp_chat_package_manifest.json"
        manifest_path.write_text(
            json.dumps(combined, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        in_zip_summary = stage_root / "BTCUSD_HISTORY_PASTE_THIS.txt"
        in_zip_summary.write_text(
            "\n".join(_summary_lines(combined)) + "\n",
            encoding="utf-8",
        )

        with zipfile.ZipFile(
            temporary_zip,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as archive:
            for timeframe in TIMEFRAME_ORDER:
                source = csv_sources.get(timeframe)
                if source is not None:
                    archive.write(source, arcname=source.name)
            archive.write(
                manifest_path,
                arcname="btcusdsharp_chat_package_manifest.json",
            )
            archive.write(in_zip_summary, arcname="BTCUSD_HISTORY_PASTE_THIS.txt")

        os.replace(temporary_zip, package_path)
        package_bytes = package_path.stat().st_size
        combined["package_path"] = str(package_path)
        combined["package_bytes"] = package_bytes
        combined["package_megabytes"] = round(package_bytes / (1024 * 1024), 3)
        combined["package_sha256"] = _sha256(package_path)

        root_lines = _summary_lines(combined)
        root_lines.extend(
            [
                "",
                "PACKAGE",
                f"file: {package_path.name}",
                f"size_mb: {combined['package_megabytes']}",
                f"sha256: {combined['package_sha256']}",
                "Upload the ZIP file itself to the chat; do not paste the CSV text.",
            ]
        )
        summary_path.write_text("\n".join(root_lines) + "\n", encoding="utf-8")
        return combined
    finally:
        temporary_zip.unlink(missing_ok=True)
        shutil.rmtree(stage_root, ignore_errors=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build one lightweight standard ZIP for chat upload: M1 90 days, "
            "M5 730 days, and M15/H1/H4/D1 730 days by default."
        )
    )
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--stage-parent", default="Files")
    parser.add_argument("--m1-days", type=int, default=DEFAULT_M1_DAYS)
    parser.add_argument("--m5-days", type=int, default=DEFAULT_M5_DAYS)
    parser.add_argument("--core-days", type=int, default=DEFAULT_CORE_DAYS)
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
    manifest = build_package(mt5, args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
