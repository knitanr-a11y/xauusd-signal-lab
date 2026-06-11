#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path
import pandas as pd

READY = "GOLD_V3_104_HIGH_VOL_POLARITY_AND_PROXY_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "goldsharp_m15.csv").exists() and (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise SystemExit("Files dir not found")


def load_stage45(path: Path):
    spec = importlib.util.spec_from_file_location("gold_v3_stage45", path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--start", default="2026-06-02 15:00:00")
    ap.add_argument("--end", default="")
    args = ap.parse_args()
    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    out = base / "104c"
    out.mkdir(parents=True, exist_ok=True)
    p45 = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")
    p50q = base / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only" / "gold_v3_50_rolling_prior_60d_q70_state.csv"
    blockers = []
    for p in [p45, p50q, src / "goldsharp_m15.csv", src / "goldsharp_h4.csv", src / "goldsharp_m5.csv"]:
        if not p.exists():
            blockers.append({"path": str(p), "reason": "missing"})
    rows = []
    if not blockers:
        st45 = load_stage45(p45)
        m15, _ = st45.prepare(src, "closed", 60, 0.70)
        q = read_csv(p50q)
        if not q.empty:
            q["m15_time_jst"] = pd.to_datetime(q["m15_time_jst"], errors="coerce")
            q = q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
            m15 = m15.drop(columns=["m15_atr28_q", "is_high_vol"], errors="ignore")
            m15 = m15.merge(q[["m15_time_jst", "atr28_q70", "high_vol_pass"]], left_on="time", right_on="m15_time_jst", how="left")
            m15["m15_atr28_q"] = pd.to_numeric(m15["atr28_q70"], errors="coerce")
            m15["is_high_vol"] = m15["high_vol_pass"].fillna(False).astype(bool)
        start = pd.Timestamp(args.start)
        end = pd.Timestamp(args.end) if args.end else pd.to_datetime(m15["time"], errors="coerce").max()
        win = m15[(pd.to_datetime(m15["time"], errors="coerce") >= start) & (pd.to_datetime(m15["time"], errors="coerce") <= end)].copy()
        src_rows = st45.source_rows(win)
        base_cands = st45.base_candidates()
        base_map = {c["label"]: c for c in base_cands}
        for hc in st45.add_hv_siblings(base_cands):
            base_label = hc["label"].split("__HV_")[0].replace("HV_", "", 1)
            bc = base_map[base_label]
            sub0 = src_rows[src_rows.source_rank.astype(str).isin(hc["ranks"])].copy() if not src_rows.empty else pd.DataFrame()
            current = sub0.copy()
            intended = sub0.copy()
            base_only = sub0.copy()
            for f in bc["filters"]:
                if not base_only.empty:
                    base_only = base_only[st45.keep_mask(base_only, f)].copy()
                if not intended.empty:
                    intended = intended[st45.keep_mask(intended, f)].copy()
            if not intended.empty:
                intended = intended[intended["is_high_vol"].fillna(False).astype(bool)].copy()
            for f in hc["filters"]:
                if not current.empty:
                    current = current[st45.keep_mask(current, f)].copy()
            cur_true = int(current["is_high_vol"].fillna(False).astype(bool).sum()) if not current.empty else 0
            cur_false = int((~current["is_high_vol"].fillna(False).astype(bool)).sum()) if not current.empty else 0
            rows.append({
                "hv_candidate_label": hc["label"],
                "base_candidate_label": base_label,
                "source_rows": len(sub0),
                "base_after_filters": len(base_only),
                "current_stage45_hv_rows": len(current),
                "current_true_rows": cur_true,
                "current_false_rows": cur_false,
                "intended_require_high_vol_rows": len(intended),
                "polarity_mismatch": bool(len(current) > 0 and cur_true == 0),
            })
    df = pd.DataFrame(rows)
    df.to_csv(out / "high_vol_polarity_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")
    current_rows = int(df["current_stage45_hv_rows"].sum()) if not df.empty else 0
    true_rows = int(df["current_true_rows"].sum()) if not df.empty else 0
    false_rows = int(df["current_false_rows"].sum()) if not df.empty else 0
    intended_rows = int(df["intended_require_high_vol_rows"].sum()) if not df.empty else 0
    mismatch = int(df["polarity_mismatch"].sum()) if not df.empty else 0
    status = READY if not blockers else "GOLD_V3_104_HIGH_VOL_POLARITY_AND_PROXY_BLOCKED_AUDIT_ONLY"
    summary = dict(status=status, high_vol_polarity_and_proxy_ready=not blockers, live_ready=False, source_csv_mutated=False, contract_mutated=False, manual_candidate_demotion_or_removal=False, open_asof_allowed=False, csv_contract=CSV_CONTRACT, csv_open_bar_exclusion_required=False, safety="audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false", pool_policy=POOL_POLICY, current_stage45_hv_total_rows=current_rows, current_stage45_hv_true_rows=true_rows, current_stage45_hv_false_rows=false_rows, intended_require_high_vol_total_rows=intended_rows, polarity_mismatch_candidate_count=mismatch, blocker_count=len(blockers))
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    top = df.sort_values(["current_stage45_hv_rows", "intended_require_high_vol_rows"], ascending=False).head(50) if not df.empty else pd.DataFrame()
    paste = ["GOLD V3 104 PASTE_ME_HIGH_VOL_POLARITY_AND_PROXY_SUMMARY"]
    for k, v in summary.items():
        paste.append(f"{k}: {v}")
    paste += ["", "POLARITY_COMPARISON_TOP", top.to_string(index=False) if not top.empty else "NO_ROWS", "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "OUTPUTS", "paste_me.txt", "summary.json", "high_vol_polarity_comparison.csv", "blockers.csv"]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
