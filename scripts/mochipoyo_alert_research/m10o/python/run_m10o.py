from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for rel in ("m10a/python", "m10l/python"):
    p = MR / rel
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import frozen_core as c
import run_m10l as m10l

STAGE = "M10O_C056_G013_DETERMINISTIC_REPRODUCTION"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10o_c056_g013_deterministic_reproduction_contract_20260725.json"
POINT = c.POINT
HORIZON = 240


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_candidate_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    rows = m10l.build_feature_rows(bars)
    selected = [
        row for row in rows
        if float(row["h1_macd_hist_bps"]) >= 3.637199446
        and float(row["h1_macd_line_bps"]) <= -7.667425443
        and float(row["h1_ret3_bps"]) >= 18.70087437
        and float(row["d1_macd_hist_bps"]) >= -14.25480242
    ]
    selected.sort(key=lambda row: row["decision"])
    return selected


def build_trade_ledger(rows: list[dict[str, Any]], m1: list[c.Bar]) -> list[dict[str, Any]]:
    by_time = {bar.time: bar for bar in m1}
    trades: list[dict[str, Any]] = []
    blocked_until: datetime | None = None
    for row in rows:
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        entry = by_time.get(decision)
        exit_time = decision + timedelta(minutes=HORIZON)
        exit_bar = by_time.get(exit_time)
        if entry is None or exit_bar is None:
            continue
        entry_bid = float(entry.open)
        actual_exit_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
        fixed_exit_ask = float(exit_bar.open) + 0.20
        trades.append({
            "entry_time": decision.strftime(c.TIME_FORMAT),
            "exit_time": exit_time.strftime(c.TIME_FORMAT),
            "year": int(row["year"]),
            "entry_bid": entry_bid,
            "exit_open": float(exit_bar.open),
            "exit_spread_points": int(exit_bar.spread),
            "actual_exit_ask": actual_exit_ask,
            "fixed0p20_exit_ask": fixed_exit_ask,
            "return_bps": c.directional_return("SHORT", entry_bid, actual_exit_ask),
            "fixed0p20_return_bps": c.directional_return("SHORT", entry_bid, fixed_exit_ask),
            "h1_macd_hist_bps": float(row["h1_macd_hist_bps"]),
            "h1_macd_line_bps": float(row["h1_macd_line_bps"]),
            "h1_ret3_bps": float(row["h1_ret3_bps"]),
            "d1_macd_hist_bps": float(row["d1_macd_hist_bps"]),
        })
        blocked_until = exit_time
    return trades


def split_metrics(trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    specs = {
        "train": {2023, 2024},
        "val2025": {2025},
        "test2026": {2026},
        "all": {2023, 2024, 2025, 2026},
    }
    out: dict[str, dict[str, Any]] = {}
    for name, years in specs.items():
        subset = [row for row in trades if int(row["year"]) in years]
        actual = c.metrics_from_values([float(row["return_bps"]) for row in subset])
        fixed = c.metrics_from_values([float(row["fixed0p20_return_bps"]) for row in subset])
        out[name] = {"actual": actual, "fixed0p20": fixed}
    return out


def assert_reference(metrics: dict[str, dict[str, Any]], expected: dict[str, Any], tolerance: float) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for split in ("train", "val2025", "test2026", "all"):
        actual = metrics[split]["actual"]
        fixed = metrics[split]["fixed0p20"]
        exp = expected[split]
        checks.append({"split": split, "field": "count", "expected": int(exp["count"]), "actual": int(actual["count"]), "pass": int(actual["count"]) == int(exp["count"])})
        for field, got, want in (
            ("pf", actual["profit_factor_bps"], exp["pf"]),
            ("fixed0p20_pf", fixed["profit_factor_bps"], exp["fixed0p20_pf"]),
        ):
            ok = got is not None and math.isfinite(float(got)) and abs(float(got) - float(want)) <= tolerance
            checks.append({"split": split, "field": field, "expected": float(want), "actual": got, "abs_diff": None if got is None else abs(float(got) - float(want)), "pass": ok})
    if not all(bool(row["pass"]) for row in checks):
        failed = [row for row in checks if not bool(row["pass"])]
        raise AuditError(f"deterministic reproduction mismatch: {failed}")
    return checks


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10O contract")
        local = local_root()
        data_root = m10l.resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual_hash}")
            paths[tf] = path
            hashes[tf] = actual_hash
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        candidate_rows = build_candidate_rows(bars)
        trades = build_trade_ledger(candidate_rows, bars["M1"])
        metrics = split_metrics(trades)
        checks = assert_reference(metrics, contract["expected_reference"], float(contract["reproduction_rules"]["metric_tolerance"]))

        out_root = local / "outputs" / "M10O"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10O deterministic reproduction of M10L_H240_C056 + M10N_G013 from frozen raw GOLD data. Historical audit-only; this is not fresh prospective proof.\n",
            encoding="utf-8",
        )
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_DETERMINISTIC_REPRODUCTION_AUDIT_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_row_count_before_one_position": len(candidate_rows),
            "trade_count_after_one_position": len(trades),
            "metrics": metrics,
            "reference_checks": checks,
            "frozen_hashes": hashes,
            "guardrails": contract["safety"],
        }
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_reproduced_trade_ledger.csv", trades)
        write_csv(archive / "03_reference_checks.csv", checks)
        (archive / "04_data_quality.json").write_text(json.dumps({
            "frozen_hashes": hashes,
            "newest_row_contract": "CLOSED",
            "time_basis": "MT5 server time",
            "nearest_m1_fallback": False,
            "exact_m1_entry_and_exit_only": True,
            "actual_spread_at_short_exit": True,
            "fixed_spread_sensitivity_usd": 0.20,
            "reads_m10n_result_csv_for_generation": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "05_audit.log").write_text("\n".join([
            "status=PASS_DETERMINISTIC_REPRODUCTION_AUDIT_ONLY",
            f"candidate_rows={len(candidate_rows)}",
            f"trades={len(trades)}",
            "all_reference_checks_pass=true",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")
        latest = out_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_reproduced_trade_ledger.csv", "03_reference_checks.csv", "04_data_quality.json", "05_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print("[M10O PASS] Deterministic C056+G013 reproduction completed")
        print(f"[RESULT] trades={len(trades)} all_pf={metrics['all']['actual']['profit_factor_bps']}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10O BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] Existing forward monitors and all frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
