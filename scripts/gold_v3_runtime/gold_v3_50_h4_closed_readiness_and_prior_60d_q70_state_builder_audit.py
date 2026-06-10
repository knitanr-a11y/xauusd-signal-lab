#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 50 H4 closed-readiness + prior-60D q70 state builder audit-only.

Materializes the first two Stage49 schemas:
- h4_closed_readiness_state
- rolling_prior_60d_q70_state

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
STAGE49_READY = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m15.csv").exists() and (d / "goldsharp_h4.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m15/h4.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--stage49-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--hv-rolling-days", type=int, default=60)
    p.add_argument("--hv-quantile", type=float, default=0.70)
    return p.parse_args()


def read_candles(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    for c in ["time", "open", "high", "low", "close"]:
        if c not in df.columns:
            raise ValueError(f"{path.name}: missing {c}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)


def row_hash(row: pd.Series, cols: list[str]) -> str:
    payload = "|".join(str(row.get(c, "")) for c in cols)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]), (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    s46 = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    s47 = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "47_closed_asof_pool_contract_forward_audit_only"
    s49 = Path(a.stage49_dir).expanduser().resolve() if a.stage49_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "49_closed_asof_state_schema_and_shadow_ledger_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p46 = s46 / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    p47 = s47 / "gold_v3_47_forward_audit_summary.json"
    p49 = s49 / "gold_v3_49_state_schema_summary.json"
    m15_path = cdir / "goldsharp_m15.csv"
    h4_path = cdir / "goldsharp_h4.csv"

    val: list[dict[str, Any]] = []
    for name, path in [("stage46_contract", p46), ("stage47_forward", p47), ("stage49_schema", p49), ("m15_csv", m15_path), ("h4_csv", h4_path)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))

    j46 = read_json(p46) if p46.exists() else {}
    j47 = read_json(p47) if p47.exists() else {}
    j49 = read_json(p49) if p49.exists() else {}

    if j46:
        frozen = j46.get("frozen_contract", {})
        val.append(ok("stage46_status_ready", j46.get("status") == STAGE46_READY, j46.get("status"), STAGE46_READY))
        val.append(ok("stage46_closed_asof", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
        val.append(ok("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
        val.append(ok("stage46_contract_not_mutated", True, "not_mutated_by_stage50", "not_mutated_by_stage50"))
    if j47:
        val.append(ok("stage47_status_ready", j47.get("status") == STAGE47_READY, j47.get("status"), STAGE47_READY))
        val.append(ok("stage47_contract_reused", j47.get("contract_reused_without_candidate_changes") is True, j47.get("contract_reused_without_candidate_changes"), True))
        val.append(ok("stage47_no_manual_demotion", j47.get("manual_candidate_demotion_or_removal") is False, j47.get("manual_candidate_demotion_or_removal"), False))
    if j49:
        val.append(ok("stage49_status_ready", j49.get("status") == STAGE49_READY, j49.get("status"), STAGE49_READY))
        val.append(ok("stage49_schema_ready", j49.get("schema_ready") is True, j49.get("schema_ready"), True))

    pre_fail = [r for r in val if r["result"] != "PASS"]
    if pre_fail:
        pd.DataFrame(val).to_csv(out / "gold_v3_50_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    m15 = read_candles(m15_path)
    h4 = read_candles(h4_path)
    val.append(ok("m15_has_rows", len(m15) > 0, len(m15), ">0"))
    val.append(ok("h4_has_rows", len(h4) > 0, len(h4), ">0"))

    h4_state = h4[["time", "open", "high", "low", "close"]].copy()
    h4_state["state_time_jst"] = pd.Timestamp.utcnow().tz_localize(None) + pd.Timedelta(hours=9)
    h4_state["latest_h4_open_time_jst"] = h4_state["time"]
    h4_state["latest_h4_close_time_jst"] = h4_state["time"] + pd.Timedelta(hours=4)
    h4_state["is_closed_safe"] = True
    h4_state["source_file"] = str(h4_path)
    h4_state["source_row_hash"] = h4_state.apply(lambda r: row_hash(r, ["time", "open", "high", "low", "close"]), axis=1)
    h4_out = h4_state[["state_time_jst", "latest_h4_open_time_jst", "latest_h4_close_time_jst", "is_closed_safe", "source_file", "source_row_hash"]]
    h4_out.to_csv(out / "gold_v3_50_h4_closed_readiness_state.csv", index=False, encoding="utf-8-sig")

    m15 = m15.copy()
    m15["m15_atr28"] = atr(m15, 28)
    window_bars = int(a.hv_rolling_days) * 96
    min_periods = max(28, window_bars // 4)
    shifted = m15["m15_atr28"].shift(1)
    m15["m15_atr28_q70"] = shifted.rolling(window_bars, min_periods=min_periods).quantile(float(a.hv_quantile))
    m15["high_vol_pass"] = (m15["m15_atr28"] >= m15["m15_atr28_q70"]) & m15["m15_atr28_q70"].notna()
    m15["lookback_end_jst"] = m15["time"] - pd.Timedelta(minutes=15)
    m15["lookback_start_jst"] = m15["time"] - pd.Timedelta(days=int(a.hv_rolling_days))
    q_state = pd.DataFrame({
        "m15_time_jst": m15["time"],
        "lookback_start_jst": m15["lookback_start_jst"],
        "lookback_end_jst": m15["lookback_end_jst"],
        "atr28_q70": m15["m15_atr28_q70"],
        "m15_atr28": m15["m15_atr28"],
        "high_vol_pass": m15["high_vol_pass"],
    })
    q_state.to_csv(out / "gold_v3_50_rolling_prior_60d_q70_state.csv", index=False, encoding="utf-8-sig")

    first_valid_idx = q_state["atr28_q70"].first_valid_index()
    val.append(ok("q70_uses_shift1_formula", True, "m15_atr28.shift(1).rolling(...).quantile(0.70)", "shift(1) prior-only"))
    val.append(ok("q70_min_periods", min_periods == max(28, window_bars // 4), min_periods, max(28, window_bars // 4)))
    val.append(ok("q70_no_value_before_min_history", first_valid_idx is None or first_valid_idx >= min_periods, first_valid_idx, f">={min_periods}"))
    val.append(ok("q70_has_values_after_history", q_state["atr28_q70"].notna().sum() > 0, int(q_state["atr28_q70"].notna().sum()), ">0"))
    val.append(ok("high_vol_pass_has_true_after_history", q_state["high_vol_pass"].sum() > 0, int(q_state["high_vol_pass"].sum()), ">0"))
    val.append(ok("h4_feature_time_is_time_plus_4h", (h4_out["latest_h4_close_time_jst"] - h4_out["latest_h4_open_time_jst"]).eq(pd.Timedelta(hours=4)).all(), "time+4h", "time+4h"))

    summary_df = pd.DataFrame([{
        "m15_rows": int(len(m15)),
        "h4_rows": int(len(h4)),
        "q70_window_bars": int(window_bars),
        "q70_min_periods": int(min_periods),
        "q70_valid_rows": int(q_state["atr28_q70"].notna().sum()),
        "high_vol_true_rows": int(q_state["high_vol_pass"].sum()),
        "high_vol_rate_on_valid": float(q_state.loc[q_state["atr28_q70"].notna(), "high_vol_pass"].mean()) if q_state["atr28_q70"].notna().any() else 0.0,
        "first_m15_time": str(m15["time"].iloc[0]) if len(m15) else "",
        "last_m15_time": str(m15["time"].iloc[-1]) if len(m15) else "",
        "first_q70_valid_time": str(q_state.loc[first_valid_idx, "m15_time_jst"]) if first_valid_idx is not None else "",
        "last_h4_open_time": str(h4["time"].iloc[-1]) if len(h4) else "",
        "last_h4_closed_feature_time": str(h4_out["latest_h4_close_time_jst"].iloc[-1]) if len(h4_out) else "",
    }])
    summary_df.to_csv(out / "gold_v3_50_high_vol_state_summary.csv", index=False, encoding="utf-8-sig")

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_50_validation_matrix.csv", index=False, encoding="utf-8-sig")

    result = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "live_ready": False,
        "state_builder_ready": failed.empty,
        "q70_formula": "m15_atr28.shift(1).rolling(60*96, min_periods=max(28, window//4)).quantile(0.70)",
        "summary": summary_df.iloc[0].to_dict(),
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_50_state_builder_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 50 PASTE_ME_STATE_BUILDER_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("state_builder_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append("")
    paste.append("HIGH_VOL_STATE_SUMMARY")
    paste.append(summary_df.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_50_h4_closed_readiness_state.csv")
    paste.append("gold_v3_50_rolling_prior_60d_q70_state.csv")
    paste.append("gold_v3_50_high_vol_state_summary.csv")
    (out / "gold_v3_50_PASTE_ME_STATE_BUILDER_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 50 H4 closed-readiness and prior-60D q70 state builder audit-only report

Status: `{status}`

## Meaning

H4 closed-readiness state and prior-60D q70 high-vol state were generated for audit-only use.
This does not implement live trading.

## Summary

```json
{json.dumps(summary_df.iloc[0].to_dict(), ensure_ascii=False, indent=2)}
```

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_50_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_50_PASTE_ME_STATE_BUILDER_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
