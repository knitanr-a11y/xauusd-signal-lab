from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
M10A_DIR = MR / "m10a" / "python"
if str(M10A_DIR) not in sys.path:
    sys.path.insert(0, str(M10A_DIR))

import frozen_core as c
import payoff_rules as pay

STAGE = "M10I_MOCHIPOYO_INDEPENDENT_M15_SHORT_ARCHETYPE_DISCOVERY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10i_mochipoyo_independent_m15_short_archetype_discovery_contract_20260725.json"
HORIZONS = (60, 120, 240)
POINT = c.POINT


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def resolve_data_root(local: Path) -> Path:
    override = os.environ.get("M10I_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata = local / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata.is_file():
        raise AuditError("M8B symbol metadata unavailable; set M10I_GOLD_DATA_ROOT")
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    root = str(payload.get("mt5_files_root", "")).strip()
    if not root:
        raise AuditError("mt5_files_root missing in M8B metadata")
    return Path(root) / "gold_v3_2023_2026"


def returns_bps(bars: list[c.Bar], lookback: int) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    for i in range(lookback, len(bars)):
        prev = bars[i - lookback].close
        if prev != 0:
            out[i] = (bars[i].close - prev) / abs(prev) * 10000.0
    return out


def atr_percentile100(atr: list[float | None]) -> list[float | None]:
    out: list[float | None] = [None] * len(atr)
    for i in range(99, len(atr)):
        window = atr[i - 99:i + 1]
        if any(v is None or not math.isfinite(float(v)) for v in window):
            continue
        values = [float(v) for v in window if v is not None]
        current = float(atr[i])
        out[i] = sum(v <= current for v in values) / len(values)
    return out


def precompute(bars: list[c.Bar]) -> dict[str, Any]:
    closes = [b.close for b in bars]
    ema20 = c.ema(closes, 20)
    ema30 = c.ema(closes, 30)
    ema40 = c.ema(closes, 40)
    macd_line = c.macd_bps(bars)
    macd_signal = c.ema(macd_line, 4)
    macd_hist = [a - b for a, b in zip(macd_line, macd_signal)]
    rci9 = c.rci_series(closes, 9)
    atr14 = pay.wilder_atr14(bars)
    return {
        "ema20": ema20,
        "ema30": ema30,
        "ema40": ema40,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "rci9": rci9,
        "atr14": atr14,
        "atr_pct100": atr_percentile100(atr14),
        "ret3": returns_bps(bars, 3),
        "ret5": returns_bps(bars, 5),
    }


def selected_closed_index(bars: list[c.Bar], delta: timedelta, decision: datetime) -> int:
    close_times = [bar.time + delta for bar in bars]
    return bisect.bisect_right(close_times, decision) - 1


def safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def feature_row(
    i: int,
    m15: list[c.Bar],
    f15: dict[str, Any],
    h1: list[c.Bar],
    fh1: dict[str, Any],
    h4: list[c.Bar],
    fh4: dict[str, Any],
) -> dict[str, Any] | None:
    if i < 120 or i + 1 >= len(m15):
        return None
    decision = m15[i + 1].time
    ih1 = selected_closed_index(h1, timedelta(hours=1), decision)
    ih4 = selected_closed_index(h4, timedelta(hours=4), decision)
    if ih1 < 50 or ih4 < 50:
        return None
    atr = safe(f15["atr14"][i])
    rci = safe(f15["rci9"][i])
    rci_prev = safe(f15["rci9"][i - 1])
    atr_pct = safe(f15["atr_pct100"][i])
    ret3 = safe(f15["ret3"][i])
    ret5 = safe(f15["ret5"][i])
    if None in (atr, rci, rci_prev, atr_pct, ret3, ret5) or atr is None or atr <= 0:
        return None
    bar = m15[i]
    prev = m15[i - 1]
    rng = bar.high - bar.low
    if rng <= 0:
        return None
    body_fraction = max(0.0, (bar.open - bar.close) / rng)
    close_position = (bar.close - bar.low) / rng
    ema20 = float(f15["ema20"][i])
    ema30 = float(f15["ema30"][i])
    ema40 = float(f15["ema40"][i])
    prev_ema20 = float(f15["ema20"][i - 1])
    macd_line = float(f15["macd_line"][i])
    macd_hist = float(f15["macd_hist"][i])
    macd_hist_prev = float(f15["macd_hist"][i - 1])
    h1_bear = float(fh1["ema20"][ih1]) < float(fh1["ema30"][ih1]) < float(fh1["ema40"][ih1])
    h4_bear = float(fh4["ema20"][ih4]) < float(fh4["ema30"][ih4]) < float(fh4["ema40"][ih4])
    h1_hist = float(fh1["macd_hist"][ih1])
    h1_hist_prev = float(fh1["macd_hist"][ih1 - 1])
    return {
        "decision": decision,
        "entry_year": decision.year,
        "m15_index": i,
        "bar_bearish": bar.close < bar.open,
        "body_fraction": body_fraction,
        "close_position": close_position,
        "m15_bearish_stack": ema20 < ema30 < ema40,
        "h1_bearish_stack": h1_bear,
        "h4_bearish_stack": h4_bear,
        "macd_line_negative": macd_line < 0,
        "macd_hist_negative": macd_hist < 0,
        "macd_hist_falling": macd_hist < macd_hist_prev,
        "h1_macd_hist_negative": h1_hist < 0,
        "h1_macd_hist_falling": h1_hist < h1_hist_prev,
        "ret3_negative": float(ret3) < 0,
        "ret5_negative": float(ret5) < 0,
        "rci9": float(rci),
        "rci9_prev": float(rci_prev),
        "rci9_falling": float(rci) < float(rci_prev),
        "atr_pct100": float(atr_pct),
        "atr14": float(atr),
        "ema20": ema20,
        "prev_ema20": prev_ema20,
        "close_minus_ema20_atr": (bar.close - ema20) / float(atr),
        "high_minus_ema20_atr": (bar.high - ema20) / float(atr),
        "prev_close_minus_ema20_atr": (prev.close - prev_ema20) / float(atr),
        "break_low_10": bar.close < min(x.low for x in m15[i - 10:i]),
        "break_low_20": bar.close < min(x.low for x in m15[i - 20:i]),
    }


def build_rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    for lookback in (10, 20):
        for body in (0.4, 0.6):
            rules.append({
                "archetype": "TREND_BREAKDOWN",
                "variant": f"break{lookback}_body{body}",
                "params": {"lookback": lookback, "body": body},
                "match": lambda r, lb=lookback, bd=body: bool(r["m15_bearish_stack"] and r["h1_bearish_stack"] and r[f"break_low_{lb}"] and r["macd_hist_negative"] and r["macd_hist_falling"] and r["bar_bearish"] and r["body_fraction"] >= bd),
            })

    for pullback in (0.0, 0.25, 0.5):
        for body in (0.4, 0.6):
            rules.append({
                "archetype": "PULLBACK_RESUME",
                "variant": f"pullback{pullback}_body{body}",
                "params": {"ema_pullback_atr": pullback, "body": body},
                "match": lambda r, pb=pullback, bd=body: bool(r["h1_bearish_stack"] and r["bar_bearish"] and r["body_fraction"] >= bd and r["high_minus_ema20_atr"] >= 0 and r["close_minus_ema20_atr"] <= pb and r["macd_hist_falling"] and r["rci9_falling"]),
            })

    for require_h4 in (False, True):
        for require_ret5 in (False, True):
            rules.append({
                "archetype": "MOMENTUM_ACCELERATION",
                "variant": f"h4{int(require_h4)}_ret5{int(require_ret5)}",
                "params": {"require_h4_bearish": require_h4, "require_ret5_negative": require_ret5},
                "match": lambda r, h4req=require_h4, r5=require_ret5: bool(r["h1_bearish_stack"] and (not h4req or r["h4_bearish_stack"]) and r["macd_line_negative"] and r["macd_hist_negative"] and r["macd_hist_falling"] and r["ret3_negative"] and (not r5 or r["ret5_negative"]) and r["rci9_falling"]),
            })

    for lookback in (10, 20):
        for atrp in (0.5, 0.7):
            for body in (0.4, 0.6):
                for closepos in (0.25, 0.4):
                    rules.append({
                        "archetype": "VOLATILITY_BREAKDOWN",
                        "variant": f"break{lookback}_atr{atrp}_body{body}_cp{closepos}",
                        "params": {"lookback": lookback, "atr_percentile": atrp, "body": body, "close_position": closepos},
                        "match": lambda r, lb=lookback, ap=atrp, bd=body, cp=closepos: bool(r[f"break_low_{lb}"] and r["atr_pct100"] >= ap and r["bar_bearish"] and r["body_fraction"] >= bd and r["close_position"] <= cp),
                    })

    for lookback in (10, 20):
        for body in (0.4, 0.6):
            rules.append({
                "archetype": "HTF_ALIGNMENT_BREAK",
                "variant": f"break{lookback}_body{body}",
                "params": {"lookback": lookback, "body": body},
                "match": lambda r, lb=lookback, bd=body: bool(r["h4_bearish_stack"] and r["h1_bearish_stack"] and r[f"break_low_{lb}"] and r["macd_hist_falling"] and r["bar_bearish"] and r["body_fraction"] >= bd),
            })

    for threshold in (60.0, 80.0):
        for body in (0.4, 0.6):
            for h1_required in (False, True):
                rules.append({
                    "archetype": "EXHAUSTION_REVERSAL",
                    "variant": f"rci{int(threshold)}_body{body}_h1{int(h1_required)}",
                    "params": {"previous_rci9_min": threshold, "body": body, "require_h1_bearish": h1_required},
                    "match": lambda r, th=threshold, bd=body, h1req=h1_required: bool(r["rci9_prev"] >= th and r["rci9_falling"] and r["bar_bearish"] and r["body_fraction"] >= bd and (not h1req or r["h1_bearish_stack"])),
                })
    return rules


def trade_rows_for_rule(
    feature_rows: list[dict[str, Any]],
    rule: dict[str, Any],
    horizon: int,
    m1_by_time: dict[datetime, c.Bar],
) -> tuple[list[dict[str, Any]], int]:
    matches = [r for r in feature_rows if rule["match"](r)]
    matches.sort(key=lambda r: r["decision"])
    out: list[dict[str, Any]] = []
    skipped_missing = 0
    blocked_until: datetime | None = None
    for row in matches:
        decision = row["decision"]
        exit_time = decision + timedelta(minutes=horizon)
        if blocked_until is not None and decision < blocked_until:
            continue
        entry = m1_by_time.get(decision)
        exit_bar = m1_by_time.get(exit_time)
        if entry is None or exit_bar is None:
            skipped_missing += 1
            continue
        entry_bid = float(entry.open)
        actual_exit_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
        fixed_exit_ask = float(exit_bar.open) + 0.20
        out.append({
            "entry_time": decision.strftime(c.TIME_FORMAT),
            "exit_time": exit_time.strftime(c.TIME_FORMAT),
            "entry_year": decision.year,
            "return_bps": c.directional_return("SHORT", entry_bid, actual_exit_ask),
            "fixed0p20_return_bps": c.directional_return("SHORT", entry_bid, fixed_exit_ask),
        })
        blocked_until = exit_time
    return out, skipped_missing


def metrics(rows: list[dict[str, Any]], key: str = "return_bps") -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: r["entry_time"])
    return c.metrics_from_values([float(r[key]) for r in ordered])


def split(rows: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    if name == "train":
        return [r for r in rows if int(r["entry_year"]) in (2023, 2024)]
    if name == "val2025":
        return [r for r in rows if int(r["entry_year"]) == 2025]
    if name == "test2026":
        return [r for r in rows if int(r["entry_year"]) == 2026]
    if name == "all":
        return list(rows)
    raise ValueError(name)


def flatten_metrics(prefix: str, value: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{k}": v for k, v in value.items()}


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


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10I contract")
        local = local_root()
        data_root = resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual = c.sha256(path)
            if actual != expected:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual}")
            paths[tf] = path
            hashes[tf] = actual
        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        f15 = precompute(bars["M15"])
        fh1 = precompute(bars["H1"])
        fh4 = precompute(bars["H4"])
        feature_rows: list[dict[str, Any]] = []
        for i in range(len(bars["M15"])):
            row = feature_row(i, bars["M15"], f15, bars["H1"], fh1, bars["H4"], fh4)
            if row is not None and 2023 <= int(row["entry_year"]) <= 2026:
                feature_rows.append(row)
        m1_by_time = {bar.time: bar for bar in bars["M1"]}
        rules = build_rules()
        results: list[dict[str, Any]] = []
        for rule_number, rule in enumerate(rules, start=1):
            for horizon in HORIZONS:
                trades, missing = trade_rows_for_rule(feature_rows, rule, horizon, m1_by_time)
                row: dict[str, Any] = {
                    "candidate_id": f"M10I_C{rule_number:03d}_H{horizon}",
                    "archetype": rule["archetype"],
                    "variant": rule["variant"],
                    "params_json": json.dumps(rule["params"], sort_keys=True, separators=(",", ":")),
                    "horizon_minutes": horizon,
                    "missing_exact_m1_exit_count": missing,
                }
                for split_name in ("train", "val2025", "test2026", "all"):
                    selected = split(trades, split_name)
                    row.update(flatten_metrics(split_name, metrics(selected)))
                    row.update(flatten_metrics(f"fixed0p20_{split_name}", metrics(selected, "fixed0p20_return_bps")))
                train_count = int(row.get("train_count") or 0)
                val_count = int(row.get("val2025_count") or 0)
                test_count = int(row.get("test2026_count") or 0)
                train_pf = row.get("train_profit_factor_bps")
                val_pf = row.get("val2025_profit_factor_bps")
                test_pf = row.get("test2026_profit_factor_bps")
                fixed_all_pf = row.get("fixed0p20_all_profit_factor_bps")
                row["eligible_train_count"] = train_count >= 40
                row["robust_pf2"] = bool(
                    train_count >= 40 and val_count >= 20 and test_count >= 15
                    and train_pf is not None and float(train_pf) >= 2.0
                    and val_pf is not None and float(val_pf) >= 2.0
                    and test_pf is not None and float(test_pf) >= 2.0
                    and float(row.get("train_net_bps") or 0) > 0
                    and float(row.get("val2025_net_bps") or 0) > 0
                    and float(row.get("test2026_net_bps") or 0) > 0
                    and fixed_all_pf is not None and float(fixed_all_pf) > 1.0
                )
                results.append(row)

        train_eligible = [r for r in results if r["eligible_train_count"]]
        top_train: list[dict[str, Any]] = []
        for archetype in sorted({str(r["archetype"]) for r in train_eligible}):
            for horizon in HORIZONS:
                group = [r for r in train_eligible if r["archetype"] == archetype and int(r["horizon_minutes"]) == horizon]
                group.sort(key=lambda r: (float(r.get("train_profit_factor_bps") or -math.inf), float(r.get("train_net_bps") or -math.inf), int(r.get("train_count") or 0)), reverse=True)
                for rank, row in enumerate(group[:5], start=1):
                    top_train.append({"train_rank_within_archetype_horizon": rank, **row})
        robust = [r for r in results if r["robust_pf2"]]
        robust.sort(key=lambda r: (float(r.get("test2026_profit_factor_bps") or -math.inf), float(r.get("val2025_profit_factor_bps") or -math.inf), float(r.get("train_profit_factor_bps") or -math.inf)), reverse=True)
        best_train = sorted(train_eligible, key=lambda r: (float(r.get("train_profit_factor_bps") or -math.inf), float(r.get("train_net_bps") or -math.inf)), reverse=True)[:20]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_HISTORICAL_INDEPENDENT_M15_SHORT_ARCHETYPE_DISCOVERY_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_universe": "all causal M15 decisions; not M7C KERNEL-S1, M10F C0049, or M10G reclaim",
            "feature_row_count": len(feature_rows),
            "rule_variant_count": len(rules),
            "rule_horizon_result_count": len(results),
            "train_eligible_result_count": len(train_eligible),
            "robust_pf2_candidate_count": len(robust),
            "top_train_only_candidates": best_train,
            "robust_pf2_candidates": robust[:20],
            "split_contract": {"discovery": "2023-2024", "validation": "2025", "final_test": "2026 through 2026-06-19"},
            "interpretation": "Historical research-exposed screening only. A robust PF2 row is a reproduction candidate, not a forward-approved signal.",
            "guardrails": {
                "audit_only": True,
                "mochipoyo_kernel_used_as_candidate_universe": False,
                "m10f_c0049_used_as_candidate_universe": False,
                "future_outcome_used_in_features": False,
                "m7c_modified_or_reset": False,
                "m10b_modified_or_reset": False,
                "m10e_modified_or_reset": False,
                "historical_backfill": False,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
                "automatic_live_promotion": False,
            },
        }
        output_root = local / "outputs" / "M10I"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10I independent M15 SHORT archetype discovery. Historical audit-only. Candidate universe is all causal M15 decisions and does not use the frozen Mochipoyo PRIMARY_SHORT kernel.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_all_rule_results.csv", results)
        write_csv(archive / "03_top_train_candidates.csv", top_train)
        write_csv(archive / "04_robust_pf2_candidates.csv", robust)
        (archive / "05_data_quality.json").write_text(json.dumps({
            "frozen_hashes": hashes,
            "newest_row_contract": "CLOSED",
            "time_basis": "MT5 server time",
            "nearest_m1_fallback": False,
            "exact_m1_entry_and_exit_only": True,
            "actual_spread_at_short_exit": True,
            "fixed_spread_sensitivity_usd": 0.20,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_audit.log").write_text("\n".join([
            "status=PASS_HISTORICAL_INDEPENDENT_M15_SHORT_ARCHETYPE_DISCOVERY_ONLY",
            f"feature_rows={len(feature_rows)}",
            f"rule_variants={len(rules)}",
            f"rule_horizon_results={len(results)}",
            f"robust_pf2_candidates={len(robust)}",
            "mochipoyo_kernel_candidate_universe=false",
            "future_outcome_used_in_features=false",
            "m7c_modified_or_reset=false",
            "m10b_modified_or_reset=false",
            "m10e_modified_or_reset=false",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        package_names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_all_rule_results.csv", "03_top_train_candidates.csv", "04_robust_pf2_candidates.csv", "05_data_quality.json", "06_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in package_names:
                zf.write(latest / name, arcname=name)
        print("[M10I PASS] independent M15 SHORT archetype discovery completed")
        print(f"[RESULT] rule_horizon_results={len(results)} robust_pf2={len(robust)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10I BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] M7C/M10B/M10E and all forward starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
