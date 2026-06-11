from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "reports" / "gold_v3" / "stage107"
DEFAULT_HANDOFF = PROJECT_ROOT / "docs" / "gold_v3" / "NEXT_CHAT_HANDOFF_GOLD_V3_99_106_DONE_107_NEXT_DIRECTION_AND_TIME_AUDIT_20260611.md"
STATUS_READY = "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY"
STATUS_BLOCKED = "BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN"
FORBIDDEN_PATH_PARTS = ("gold_v2", "old_gold", "legacy_gold", "disc8", "stage41", "gold_specialist_8")
SIDE_WORDS = ("side", "direction", "trade_side", "signal_side", "position_side", "order_side", "dir")
TIME_CANDIDATES = ("time", "entry_time", "m15_time", "bar_time", "timestamp", "datetime")
OPEN_CANDIDATES = ("open", "m5_open", "Open")
HIGH_CANDIDATES = ("high", "m5_high", "High")
LOW_CANDIDATES = ("low", "m5_low", "Low")
CLOSE_CANDIDATES = ("close", "m5_close", "Close", "entry", "entry_price")
CANDIDATE_ID_CANDIDATES = ("candidate_id", "rule_id", "profile", "candidate", "name", "strategy_id")
ATR_CANDIDATES = ("m15_atr28", "atr28", "atr", "m15_atr14")
HIGH_VOL_CANDIDATES = ("is_high_vol", "high_vol", "m15_is_high_vol")


@dataclass
class ProxyProfile:
    name: str
    tp: float
    sl: float
    horizon_m5_bars: int


def is_forbidden(path: Path) -> bool:
    s = str(path).replace("\\", "/").lower()
    return any(part in s for part in FORBIDDEN_PATH_PARTS)


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".json", ".jsonl"}:
        try:
            return pd.read_json(path, lines=suffix == ".jsonl")
        except ValueError:
            return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported input file type: {path}")


def find_first(columns: Iterable[str], names: Iterable[str]) -> str | None:
    cols = list(columns)
    lower = {c.lower(): c for c in cols}
    for name in names:
        if name in cols:
            return name
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def safe_candidates(root: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_file() and not is_forbidden(p):
                found.append(p)
    return sorted(set(found), key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)


def autodiscover_candidate_file(root: Path) -> Path | None:
    patterns = [
        "reports/gold_v3/**/*107*.csv",
        "reports/gold_v3/**/*stage69*.csv",
        "reports/gold_v3/**/*stage45*.csv",
        "data/**/*gold_v3*candidate*.csv",
        "data/**/*stage69*.csv",
        "data/**/*stage45*.csv",
        "**/*gold_v3*candidate*.csv",
        "**/*stage69*.csv",
        "**/*stage45*.csv",
    ]
    for p in safe_candidates(root, patterns):
        if "candidate" in p.name.lower() or "stage45" in p.name.lower() or "stage69" in p.name.lower():
            return p
    return None


def autodiscover_m5_file(root: Path) -> Path | None:
    patterns = [
        "data/**/*M5*.csv",
        "data/**/*m5*.csv",
        "**/*M5*.csv",
        "**/*m5*.csv",
    ]
    for p in safe_candidates(root, patterns):
        name = p.name.lower()
        if "m5" in name and "backtest" in name:
            return p
    files = safe_candidates(root, patterns)
    return files[0] if files else None


def parse_time_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def infer_entry_price(row: pd.Series, close_col: str | None, m15_by_time: dict[pd.Timestamp, float] | None = None) -> float | None:
    for col in ("entry_price", "entry", "close", "m15_close", "Close"):
        if col in row.index and pd.notna(row[col]):
            try:
                return float(row[col])
            except Exception:
                pass
    if close_col and close_col in row.index and pd.notna(row[close_col]):
        try:
            return float(row[close_col])
        except Exception:
            pass
    if m15_by_time is not None:
        t = row.get("_entry_time")
        if pd.notna(t) and t in m15_by_time:
            return float(m15_by_time[t])
    return None


def parse_profiles_from_row(row: pd.Series, default_scale: float, default_horizon_m5: int) -> list[ProxyProfile]:
    # Explicit numeric columns win.
    tp_col = find_first(row.index, ("tp", "tp_dist", "take_profit", "tp_distance", "tp_usd"))
    sl_col = find_first(row.index, ("sl", "sl_dist", "stop_loss", "sl_distance", "sl_usd"))
    h_col = find_first(row.index, ("horizon_m5_bars", "horizon", "horizon_bars", "h"))
    if tp_col and sl_col and pd.notna(row[tp_col]) and pd.notna(row[sl_col]):
        try:
            h = int(row[h_col]) if h_col and pd.notna(row[h_col]) else default_horizon_m5
            return [ProxyProfile("explicit", abs(float(row[tp_col])), abs(float(row[sl_col])), h)]
        except Exception:
            pass

    text = " ".join(str(row.get(c, "")) for c in row.index if isinstance(row.get(c, ""), (str, int, float)))
    matches = re.findall(r"TP(\d+(?:\.\d+)?)_SL(\d+(?:\.\d+)?)(?:_H(\d+))?", text, flags=re.I)
    profiles: list[ProxyProfile] = []
    for tp, sl, h in matches:
        profiles.append(ProxyProfile(f"TP{tp}_SL{sl}_H{h or default_horizon_m5}", float(tp) * default_scale, float(sl) * default_scale, int(h) if h else default_horizon_m5))
    if profiles:
        return profiles
    return [ProxyProfile("default_TP180_SL70_H128", 180 * default_scale, 70 * default_scale, default_horizon_m5)]


def adjudicate(entry_time: pd.Timestamp, entry_price: float, m5: pd.DataFrame, profile: ProxyProfile, side: str, same_bar_priority: str) -> dict[str, Any]:
    after = m5[m5["_time"] > entry_time].head(profile.horizon_m5_bars)
    if after.empty:
        return {"outcome": "NO_FUTURE_M5", "exit_time": None, "exit_price": math.nan, "bars_scanned": 0}
    if side == "LONG":
        tp_price = entry_price + profile.tp
        sl_price = entry_price - profile.sl
        tp_hit = after["_high"] >= tp_price
        sl_hit = after["_low"] <= sl_price
    else:
        tp_price = entry_price - profile.tp
        sl_price = entry_price + profile.sl
        tp_hit = after["_low"] <= tp_price
        sl_hit = after["_high"] >= sl_price

    for idx, (_, r) in enumerate(after.iterrows(), start=1):
        tp = bool(tp_hit.loc[r.name])
        sl = bool(sl_hit.loc[r.name])
        if tp and sl:
            outcome = "LOSS" if same_bar_priority.upper() == "SL" else "WIN"
            exit_price = sl_price if outcome == "LOSS" else tp_price
            return {"outcome": outcome, "exit_time": str(r["_time"]), "exit_price": exit_price, "bars_scanned": idx, "same_bar_hit": True}
        if tp:
            return {"outcome": "WIN", "exit_time": str(r["_time"]), "exit_price": tp_price, "bars_scanned": idx, "same_bar_hit": False}
        if sl:
            return {"outcome": "LOSS", "exit_time": str(r["_time"]), "exit_price": sl_price, "bars_scanned": idx, "same_bar_hit": False}
    last_close = float(after.iloc[-1]["_close"])
    pnl = (last_close - entry_price) if side == "LONG" else (entry_price - last_close)
    return {"outcome": "TIMEOUT", "exit_time": str(after.iloc[-1]["_time"]), "exit_price": last_close, "bars_scanned": len(after), "same_bar_hit": False, "timeout_pnl": pnl}


def metrics(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        wins = int((g["outcome"] == "WIN").sum())
        losses = int((g["outcome"] == "LOSS").sum())
        timeout = int((g["outcome"] == "TIMEOUT").sum())
        total = len(g)
        denom = wins + losses
        wr = wins / denom if denom else None
        rec = {c: v for c, v in zip(group_cols, keys)}
        rec.update({"trades": total, "wins": wins, "losses": losses, "timeouts": timeout, "win_rate_ex_timeout": wr})
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def make_report(summary: dict[str, Any]) -> str:
    lines = [
        "# GOLD V3 Stage107 — NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY REPORT",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Guardrails",
        "",
        "GOLD V3 remains audit-only/proxy-only. No runtime logic, candidate pool, Stage45, Stage69, CSV, Discord, MT5, AI API, live hook, live evaluator, or final signal was changed.",
        "",
        "## Inputs",
        "",
        f"- candidate_file: `{summary.get('candidate_file')}`",
        f"- m5_file: `{summary.get('m5_file')}`",
        f"- m15_file: `{summary.get('m15_file')}`",
        "",
        "## Findings",
        "",
    ]
    for item in summary.get("findings", []):
        lines.append(f"- {item}")
    if summary.get("blocked_reasons"):
        lines.extend(["", "## Blocked reasons", ""])
        for item in summary["blocked_reasons"]:
            lines.append(f"- {item}")
    lines.extend([
        "",
        "## Output files",
        "",
    ])
    for k, v in summary.get("outputs", {}).items():
        lines.append(f"- {k}: `{v}`")
    lines.extend([
        "",
        "## Next",
        "",
        "If Stage107 is READY, create Stage108: `GOLD_V3_108_JST_VS_MT5_TIME_BASIS_DIFFERENTIAL_AUDIT_ONLY`.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="GOLD V3 Stage107 direction assumption audit-only script")
    ap.add_argument("--candidate-file", type=Path)
    ap.add_argument("--m5-csv", type=Path)
    ap.add_argument("--m15-csv", type=Path)
    ap.add_argument("--handoff-doc", type=Path, default=DEFAULT_HANDOFF)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--profile-scale", type=float, default=0.1)
    ap.add_argument("--default-horizon-m5", type=int, default=128)
    ap.add_argument("--same-bar-priority", choices=["SL", "TP"], default="SL")
    args = ap.parse_args()

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "stage": "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY",
        "status": STATUS_BLOCKED,
        "guardrails": {
            "audit_only": True,
            "runtime_mutation": False,
            "candidate_pool_mutation": False,
            "csv_mutation": False,
            "forbidden_sources_skipped": list(FORBIDDEN_PATH_PARTS),
        },
        "candidate_file": None,
        "m5_file": None,
        "m15_file": str(args.m15_csv) if args.m15_csv else None,
        "blocked_reasons": [],
        "findings": [],
        "outputs": {},
        "profile_scale": args.profile_scale,
        "same_bar_priority": args.same_bar_priority,
    }

    candidate_file = args.candidate_file or autodiscover_candidate_file(PROJECT_ROOT)
    m5_file = args.m5_csv or autodiscover_m5_file(PROJECT_ROOT)
    if candidate_file and is_forbidden(candidate_file):
        summary["blocked_reasons"].append(f"candidate_file is in forbidden path: {candidate_file}")
        candidate_file = None
    if m5_file and is_forbidden(m5_file):
        summary["blocked_reasons"].append(f"m5_file is in forbidden path: {m5_file}")
        m5_file = None
    summary["candidate_file"] = str(candidate_file) if candidate_file else None
    summary["m5_file"] = str(m5_file) if m5_file else None

    if not candidate_file:
        summary["blocked_reasons"].append("No safe candidate artifact found. Pass --candidate-file explicitly.")
    if not m5_file:
        summary["blocked_reasons"].append("No safe M5 OHLC artifact found. Pass --m5-csv explicitly.")

    if summary["blocked_reasons"]:
        summary["findings"].append("Stage107 could not compute proxy trade metrics because required read-only inputs were incomplete.")
    else:
        cand = read_table(candidate_file)
        m5 = read_table(m5_file)
        time_col = find_first(cand.columns, TIME_CANDIDATES)
        m5_time_col = find_first(m5.columns, TIME_CANDIDATES)
        high_col = find_first(m5.columns, HIGH_CANDIDATES)
        low_col = find_first(m5.columns, LOW_CANDIDATES)
        close_col = find_first(m5.columns, CLOSE_CANDIDATES)
        if not time_col:
            summary["blocked_reasons"].append("Candidate artifact has no usable time/entry_time column.")
        if not all([m5_time_col, high_col, low_col, close_col]):
            summary["blocked_reasons"].append("M5 artifact lacks required time/high/low/close columns.")
        if summary["blocked_reasons"]:
            summary["findings"].append("Input files were present but schema was insufficient for proxy adjudication.")
        else:
            cand = cand.copy()
            cand["_entry_time"] = parse_time_series(cand[time_col])
            m5 = m5.copy()
            m5["_time"] = parse_time_series(m5[m5_time_col])
            m5["_high"] = pd.to_numeric(m5[high_col], errors="coerce")
            m5["_low"] = pd.to_numeric(m5[low_col], errors="coerce")
            m5["_close"] = pd.to_numeric(m5[close_col], errors="coerce")
            m5 = m5.dropna(subset=["_time", "_high", "_low", "_close"]).sort_values("_time")
            side_cols = [c for c in cand.columns if any(w == c.lower() or w in c.lower() for w in SIDE_WORDS)]
            id_col = find_first(cand.columns, CANDIDATE_ID_CANDIDATES)
            hv_col = find_first(cand.columns, HIGH_VOL_CANDIDATES)
            atr_col = find_first(cand.columns, ATR_CANDIDATES)
            cand["_candidate_id"] = cand[id_col].astype(str) if id_col else cand.index.map(lambda x: f"row_{x}")
            cand["_is_hv_named"] = cand["_candidate_id"].str.contains("HV", case=False, na=False)
            cand["_jst_time"] = cand["_entry_time"] + pd.Timedelta(hours=9)
            cand["_jst_hour"] = cand.get("jst_hour", cand["_jst_time"].dt.hour)
            cand["_jst_weekday"] = cand.get("jst_weekday", cand["_jst_time"].dt.weekday)
            cand["_h4_bucket"] = cand["_jst_time"].dt.floor("4h")
            entry_close_col = find_first(cand.columns, CLOSE_CANDIDATES)

            trades: list[dict[str, Any]] = []
            for _, row in cand.dropna(subset=["_entry_time"]).iterrows():
                entry_price = infer_entry_price(row, entry_close_col)
                if entry_price is None or not math.isfinite(entry_price):
                    continue
                profiles = parse_profiles_from_row(row, args.profile_scale, args.default_horizon_m5)
                for profile in profiles:
                    for side in ("LONG", "SHORT"):
                        res = adjudicate(row["_entry_time"], entry_price, m5, profile, side, args.same_bar_priority)
                        rec = {
                            "entry_time": str(row["_entry_time"]),
                            "candidate_id": row["_candidate_id"],
                            "candidate_kind": "HV_NAMED" if row["_is_hv_named"] else "NORMAL_OR_UNNAMED",
                            "proxy_side": side,
                            "profile": profile.name,
                            "entry_price": entry_price,
                            "tp_distance": profile.tp,
                            "sl_distance": profile.sl,
                            "horizon_m5_bars": profile.horizon_m5_bars,
                            "jst_hour": row["_jst_hour"],
                            "jst_weekday": row["_jst_weekday"],
                            "h4_bucket": str(row["_h4_bucket"]),
                        }
                        if hv_col:
                            rec["is_high_vol_value"] = row.get(hv_col)
                        if atr_col:
                            rec["atr_value"] = row.get(atr_col)
                        rec.update(res)
                        trades.append(rec)
            trade_df = pd.DataFrame(trades)
            trade_path = out / "gold_v3_107_trade_level_long_short_proxy.csv"
            trade_df.to_csv(trade_path, index=False)
            summary["outputs"]["trade_level"] = str(trade_path)

            if trade_df.empty:
                summary["blocked_reasons"].append("No evaluable trades were produced; candidate rows may lack entry price/time.")
                summary["findings"].append("Direction metadata scan completed, but proxy metrics are blocked by non-evaluable candidate rows.")
            else:
                per_candidate = metrics(trade_df, ["candidate_kind", "candidate_id", "profile", "proxy_side"])
                h4 = metrics(trade_df, ["h4_bucket", "proxy_side"])
                hour = metrics(trade_df, ["jst_hour", "proxy_side"])
                weekday = metrics(trade_df, ["jst_weekday", "proxy_side"])
                paths = {
                    "per_candidate": out / "gold_v3_107_per_candidate_long_short_metrics.csv",
                    "segment_h4": out / "gold_v3_107_segment_h4_bucket_metrics.csv",
                    "segment_jst_hour": out / "gold_v3_107_segment_jst_hour_metrics.csv",
                    "segment_jst_weekday": out / "gold_v3_107_segment_jst_weekday_metrics.csv",
                }
                per_candidate.to_csv(paths["per_candidate"], index=False)
                h4.to_csv(paths["segment_h4"], index=False)
                hour.to_csv(paths["segment_jst_hour"], index=False)
                weekday.to_csv(paths["segment_jst_weekday"], index=False)
                summary["outputs"].update({k: str(v) for k, v in paths.items()})
                summary["status"] = STATUS_READY
                summary["findings"].append(f"Candidate rows evaluated bidirectionally: {len(trade_df)} proxy trade rows.")

            if side_cols:
                summary["findings"].append(f"Explicit side/direction-like columns found: {side_cols}")
            else:
                summary["findings"].append("CRITICAL: no explicit side/direction-like metadata column was found in the candidate artifact.")
            if hv_col:
                counts = cand[hv_col].value_counts(dropna=False).to_dict()
                summary["findings"].append(f"HV semantic column `{hv_col}` value counts: {counts}")
                if cand["_is_hv_named"].any():
                    hv_named_counts = cand.loc[cand["_is_hv_named"], hv_col].value_counts(dropna=False).to_dict()
                    summary["findings"].append(f"HV-named candidate rows `{hv_col}` value counts: {hv_named_counts}")
            else:
                summary["findings"].append("No `is_high_vol`-like column found; corrected true-HV semantics could not be revalidated from this artifact.")
            summary["findings"].append("Stage99-106 recap: independent true-HV LONG proxy was all-loss in the recent window, while independent true-HV SHORT proxy was all-win; this remains proxy-only and must not be promoted to runtime.")

    if summary["blocked_reasons"]:
        summary["status"] = STATUS_BLOCKED
    summary_path = out / "gold_v3_107_direction_assumption_summary.json"
    report_path = out / "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md"
    summary["outputs"]["summary"] = str(summary_path)
    summary["outputs"]["report"] = str(report_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report_path.write_text(make_report(summary), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary": str(summary_path), "report": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == STATUS_READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
