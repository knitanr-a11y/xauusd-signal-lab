from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATUS_READY = "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY"
STATUS_BLOCKED = "BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN"
FORBIDDEN = ("gold_v2", "old_gold", "legacy_gold", "disc8", "stage41", "gold_specialist_8")


def bad_path(p: Path) -> bool:
    s = str(p).replace("\\", "/").lower()
    return any(x in s for x in FORBIDDEN)


def mt5_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    env = os.environ.get("MT5_FILES_DIR") or os.environ.get("MQL5_FILES_DIR")
    return Path(env).resolve() if env else PROJECT_ROOT


def out_dir(root: Path) -> Path:
    return root / "FX_OUTPUTS" / "gold_v3" / "107c"


def read_any(path: Path) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".csv":
        return pd.read_csv(path)
    if suf in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suf in (".json", ".jsonl"):
        return pd.read_json(path, lines=(suf == ".jsonl"))
    raise ValueError(f"unsupported file type: {path}")


def find_col(cols, names):
    lower = {str(c).lower(): str(c) for c in cols}
    for n in names:
        if n in cols:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def newest(root: Path, patterns):
    files = []
    for pat in patterns:
        files += [p for p in root.glob(pat) if p.is_file() and not bad_path(p)]
    files = sorted(set(files), key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)
    return files[0] if files else None


def auto_candidate(mt5: Path) -> Path | None:
    pats = [
        "FX_OUTPUTS/gold_v3/**/*candidate*.csv",
        "FX_OUTPUTS/gold_v3/**/*stage69*.csv",
        "FX_OUTPUTS/gold_v3/**/*stage45*.csv",
        "data/**/*candidate*.csv",
        "data/**/*stage69*.csv",
        "data/**/*stage45*.csv",
    ]
    return newest(mt5, pats) or newest(PROJECT_ROOT, pats)


def auto_m5(mt5: Path) -> Path | None:
    pats = ["**/*M5*.csv", "**/*m5*.csv", "**/*M5*.parquet", "**/*m5*.parquet"]
    return newest(mt5, pats) or newest(PROJECT_ROOT, pats)


def profile_from_row(row, scale: float, default_h: int):
    cols = row.index
    tp = find_col(cols, ("tp", "tp_dist", "take_profit", "tp_distance", "tp_usd"))
    sl = find_col(cols, ("sl", "sl_dist", "stop_loss", "sl_distance", "sl_usd"))
    hh = find_col(cols, ("horizon_m5_bars", "horizon", "horizon_bars", "h"))
    if tp and sl and pd.notna(row[tp]) and pd.notna(row[sl]):
        try:
            return [("explicit", abs(float(row[tp])), abs(float(row[sl])), int(row[hh]) if hh and pd.notna(row[hh]) else default_h)]
        except Exception:
            pass
    text = " ".join(str(v) for v in row.to_dict().values() if pd.notna(v))
    found = re.findall(r"TP(\d+(?:\.\d+)?)_SL(\d+(?:\.\d+)?)(?:_H(\d+))?", text, flags=re.I)
    if found:
        return [(f"TP{a}_SL{b}_H{h or default_h}", float(a) * scale, float(b) * scale, int(h) if h else default_h) for a, b, h in found]
    return [("default_TP180_SL70_H128", 180 * scale, 70 * scale, default_h)]


def adjudicate(entry_time, entry_price, m5, tp, sl, horizon, side, priority):
    w = m5[m5["_time"] > entry_time].head(horizon)
    if w.empty:
        return "NO_FUTURE_M5", "", math.nan, 0, False
    if side == "LONG":
        tp_price, sl_price = entry_price + tp, entry_price - sl
        tp_hit, sl_hit = w["_high"] >= tp_price, w["_low"] <= sl_price
    else:
        tp_price, sl_price = entry_price - tp, entry_price + sl
        tp_hit, sl_hit = w["_low"] <= tp_price, w["_high"] >= sl_price
    for i, (idx, r) in enumerate(w.iterrows(), 1):
        th, sh = bool(tp_hit.loc[idx]), bool(sl_hit.loc[idx])
        if th and sh:
            outcome = "LOSS" if priority == "SL" else "WIN"
            return outcome, str(r["_time"]), sl_price if outcome == "LOSS" else tp_price, i, True
        if th:
            return "WIN", str(r["_time"]), tp_price, i, False
        if sh:
            return "LOSS", str(r["_time"]), sl_price, i, False
    return "TIMEOUT", str(w.iloc[-1]["_time"]), float(w.iloc[-1]["_close"]), len(w), False


def metric(df, cols):
    rows = []
    if df.empty:
        return pd.DataFrame()
    for k, g in df.groupby(cols, dropna=False):
        if not isinstance(k, tuple):
            k = (k,)
        wins = int((g.outcome == "WIN").sum())
        losses = int((g.outcome == "LOSS").sum())
        den = wins + losses
        r = dict(zip(cols, k))
        r.update(trades=int(len(g)), wins=wins, losses=losses, timeouts=int((g.outcome == "TIMEOUT").sum()), no_future_m5=int((g.outcome == "NO_FUTURE_M5").sum()), win_rate_ex_timeout=(wins / den if den else None))
        rows.append(r)
    return pd.DataFrame(rows)


def write_paste(path: Path, s: dict[str, Any]) -> None:
    lines = [
        "GOLD V3 Stage107 paste_me",
        f"status: {s['status']}",
        f"ready: {str(s['ready']).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_open_bar_exclusion_required: false",
        "csv_contract: open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden",
        "safety_flags: audit_only=true; proxy_only=true; runtime_mutated=false; stage45_runtime_mutated=false; stage69_runtime_mutated=false; discord_enabled=false; mt5_execution_enabled=false; ai_api_enabled=false; live_hook_enabled=false; final_signal_enabled=false",
        "pool_policy: poolから外さない。rolling health gateに判断させる。",
        "key_metrics:",
    ]
    lines += [f"  {k}: {v}" for k, v in s.get("key_metrics", {}).items()]
    lines += [f"blocker_count: {len(s.get('blockers', []))}", "BLOCKERS:"]
    lines += [f"  - {x}" for x in s.get("blockers", [])] or ["  none"]
    lines += ["VALIDATION:"] + [f"  - {x}" for x in s.get("validation", [])]
    lines += ["OUTPUTS:"] + [f"  {k}: {v}" for k, v in s.get("outputs", {}).items()]
    lines += ["FINDINGS:"] + [f"  - {x}" for x in s.get("findings", [])]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-file")
    ap.add_argument("--m5-csv")
    ap.add_argument("--mt5-files-dir")
    ap.add_argument("--profile-scale", type=float, default=0.1)
    ap.add_argument("--default-horizon-m5", type=int, default=128)
    ap.add_argument("--same-bar-priority", choices=("SL", "TP"), default="SL")
    args = ap.parse_args()
    root = mt5_root(args.mt5_files_dir)
    od = out_dir(root)
    od.mkdir(parents=True, exist_ok=True)
    s: dict[str, Any] = dict(status=STATUS_BLOCKED, ready=False, candidate_file=None, m5_file=None, mt5_files_dir=str(root), blockers=[], validation=[], findings=[], outputs={}, key_metrics={})
    cfile = Path(args.candidate_file).resolve() if args.candidate_file else auto_candidate(root)
    m5file = Path(args.m5_csv).resolve() if args.m5_csv else auto_m5(root)
    if cfile and bad_path(cfile):
        s["blockers"].append(f"candidate file is forbidden path: {cfile}"); cfile = None
    if m5file and bad_path(m5file):
        s["blockers"].append(f"M5 file is forbidden path: {m5file}"); m5file = None
    s["candidate_file"] = str(cfile) if cfile else None
    s["m5_file"] = str(m5file) if m5file else None
    if not cfile:
        s["blockers"].append("No safe candidate artifact found. Use BAT optional --candidate-file.")
    if not m5file:
        s["blockers"].append("No safe M5 OHLC artifact found. Use BAT optional --m5-csv.")
    if not s["blockers"]:
        try:
            cand, m5 = read_any(cfile), read_any(m5file)
            tcol = find_col(cand.columns, ("time", "entry_time", "m15_time", "bar_time", "timestamp", "datetime"))
            mt = find_col(m5.columns, ("time", "timestamp", "datetime"))
            hi = find_col(m5.columns, ("high", "m5_high", "High"))
            lo = find_col(m5.columns, ("low", "m5_low", "Low"))
            cl = find_col(m5.columns, ("close", "m5_close", "Close"))
            if not tcol:
                s["blockers"].append("Candidate artifact has no time column.")
            if not all([mt, hi, lo, cl]):
                s["blockers"].append("M5 artifact lacks time/high/low/close columns.")
            if not s["blockers"]:
                cand = cand.copy(); m5 = m5.copy()
                cand["_time"] = pd.to_datetime(cand[tcol], errors="coerce")
                m5["_time"] = pd.to_datetime(m5[mt], errors="coerce")
                m5["_high"] = pd.to_numeric(m5[hi], errors="coerce")
                m5["_low"] = pd.to_numeric(m5[lo], errors="coerce")
                m5["_close"] = pd.to_numeric(m5[cl], errors="coerce")
                m5 = m5.dropna(subset=["_time", "_high", "_low", "_close"]).sort_values("_time")
                idc = find_col(cand.columns, ("candidate_id", "rule_id", "profile", "candidate", "name", "strategy_id"))
                entryc = find_col(cand.columns, ("entry_price", "entry", "close", "m15_close", "Close"))
                hvc = find_col(cand.columns, ("is_high_vol", "high_vol", "m15_is_high_vol"))
                side_cols = [str(x) for x in cand.columns if any(w in str(x).lower() for w in ("side", "direction", "trade_side", "signal_side", "position_side", "order_side", "dir"))]
                cand["_id"] = cand[idc].astype(str) if idc else cand.index.map(lambda x: f"row_{x}")
                cand["_hv_named"] = cand["_id"].str.contains("HV", case=False, na=False)
                cand["_jst"] = cand["_time"] + pd.Timedelta(hours=9)
                cand["_jst_hour"] = cand["jst_hour"] if "jst_hour" in cand.columns else cand["_jst"].dt.hour
                cand["_jst_weekday"] = cand["jst_weekday"] if "jst_weekday" in cand.columns else cand["_jst"].dt.weekday
                cand["_h4_bucket"] = cand["_jst"].dt.floor("4h")
                trades = []
                for _, r in cand.dropna(subset=["_time"]).iterrows():
                    if not entryc or pd.isna(r[entryc]):
                        continue
                    try:
                        ep = float(r[entryc])
                    except Exception:
                        continue
                    for prof, tp, sl, hz in profile_from_row(r, args.profile_scale, args.default_horizon_m5):
                        for side in ("LONG", "SHORT"):
                            outcome, xt, xp, bars, same = adjudicate(r["_time"], ep, m5, tp, sl, hz, side, args.same_bar_priority)
                            rec = dict(entry_time=str(r["_time"]), candidate_id=r["_id"], candidate_kind="HV_NAMED" if r["_hv_named"] else "NORMAL_OR_UNNAMED", proxy_side=side, profile=prof, entry_price=ep, tp_distance=tp, sl_distance=sl, horizon_m5_bars=hz, jst_hour=r["_jst_hour"], jst_weekday=r["_jst_weekday"], h4_bucket=str(r["_h4_bucket"]), outcome=outcome, exit_time=xt, exit_price=xp, bars_scanned=bars, same_bar_hit=same)
                            if hvc: rec["is_high_vol_value"] = r.get(hvc)
                            trades.append(rec)
                df = pd.DataFrame(trades)
                trade_path = od / "gold_v3_107_trade_level_long_short_proxy.csv"; df.to_csv(trade_path, index=False); s["outputs"]["trade_level"] = str(trade_path)
                s["key_metrics"].update(candidate_rows=int(len(cand)), proxy_trade_rows=int(len(df)), hv_named_candidate_rows=int(cand["_hv_named"].sum()), side_direction_column_count=len(side_cols))
                if df.empty:
                    s["blockers"].append("No evaluable proxy trades produced; candidate rows may lack entry price/time.")
                else:
                    outs = {
                        "per_candidate": od / "gold_v3_107_per_candidate_long_short_metrics.csv",
                        "segment_h4": od / "gold_v3_107_segment_h4_bucket_metrics.csv",
                        "segment_jst_hour": od / "gold_v3_107_segment_jst_hour_metrics.csv",
                        "segment_jst_weekday": od / "gold_v3_107_segment_jst_weekday_metrics.csv",
                    }
                    metric(df, ["candidate_kind", "candidate_id", "profile", "proxy_side"]).to_csv(outs["per_candidate"], index=False)
                    metric(df, ["h4_bucket", "proxy_side"]).to_csv(outs["segment_h4"], index=False)
                    metric(df, ["jst_hour", "proxy_side"]).to_csv(outs["segment_jst_hour"], index=False)
                    metric(df, ["jst_weekday", "proxy_side"]).to_csv(outs["segment_jst_weekday"], index=False)
                    s["outputs"].update({k: str(v) for k, v in outs.items()})
                    by_side = metric(df, ["proxy_side"])
                    for _, rr in by_side.iterrows():
                        k = str(rr.proxy_side).lower(); s["key_metrics"][f"{k}_wins"] = int(rr.wins); s["key_metrics"][f"{k}_losses"] = int(rr.losses); s["key_metrics"][f"{k}_win_rate_ex_timeout"] = rr.win_rate_ex_timeout
                s["findings"].append(f"side/direction columns: {side_cols if side_cols else 'NONE - CRITICAL direction-assumption risk'}")
                s["findings"].append(f"high-vol semantic column: {hvc if hvc else 'NONE'}")
                s["findings"].append("Stage105/106 recap: true-HV LONG proxy all-loss and true-HV SHORT proxy all-win in recent window; proxy-only, no runtime promotion.")
        except Exception as e:
            s["blockers"].append(f"Unhandled exception: {type(e).__name__}: {e}")
    s["ready"] = not s["blockers"]
    s["status"] = STATUS_READY if s["ready"] else STATUS_BLOCKED
    s["validation"] = ["audit_only=true", "proxy_only=true", "source_csv_mutated=false", "contract_mutated=false", "candidate_pool_mutated=false", "stage45_runtime_mutated=false", "stage69_runtime_mutated=false", "open_asof_allowed=false", "paste_me.txt written"]
    summary = od / "gold_v3_107_direction_assumption_summary.json"
    report = od / "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md"
    paste = od / "paste_me.txt"
    s["outputs"].update(summary=str(summary), report=str(report), paste_me=str(paste))
    summary.write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report.write_text("# GOLD V3 Stage107 Report\n\n" + json.dumps(s, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    write_paste(paste, s)
    print(json.dumps({"status": s["status"], "ready": s["ready"], "paste_me": str(paste)}, ensure_ascii=False, indent=2))
    return 0 if s["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
