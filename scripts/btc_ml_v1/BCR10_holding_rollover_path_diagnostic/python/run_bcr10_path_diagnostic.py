from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

STAGE = "BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC"
RECORDED_AT = "2026-07-30T20:15:00+09:00"
BCR09_SHA = "92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa"
M15_SHA = "b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
POINT = 0.01

MACHINES = [
    "TRACK_A_F1_COVERAGE_FIRST",
    "TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE",
    "TRACK_A_F3_STATE_FIDELITY",
    "TRACK_A_F4_MINIMUM_EXTRA_PARETO",
    "TRACK_B_B4_E0_EMA20_TOUCH",
    "TRACK_B_B4_E1_EXTENSION_CONTRACT",
]
EXPECTED_COUNTS = {
    "TRACK_A_F1_COVERAGE_FIRST": 1561,
    "TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE": 1229,
    "TRACK_A_F3_STATE_FIDELITY": 812,
    "TRACK_A_F4_MINIMUM_EXTRA_PARETO": 768,
    "TRACK_B_B4_E0_EMA20_TOUCH": 773,
    "TRACK_B_B4_E1_EXTENSION_CONTRACT": 832,
}
FILES = [
    "00_READ_ME_FIRST.txt", "01_summary.json", "02_episode_path_diagnostic.csv",
    "03_holding_bin_metrics.csv", "04_date_crossing_bin_metrics.csv",
    "05_entry_exit_hour_matrix.csv", "06_excursion_summary.csv",
    "07_rollover_loss_phenotype.csv", "08_loss_concentration.csv",
    "09_month_coverage.csv", "10_gap_cases.csv", "11_formula_manifest.json",
    "12_integrity_checks.json", "13_file_sha256_manifest.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def holding_bin(value: int) -> str:
    if 1 <= value <= 4: return "H01_04"
    if 5 <= value <= 8: return "H05_08"
    if 9 <= value <= 16: return "H09_16"
    if 17 <= value <= 32: return "H17_32"
    if 33 <= value <= 64: return "H33_64"
    if 65 <= value <= 128: return "H65_128"
    if value >= 129: return "H129_PLUS"
    raise ValueError(value)


def crossing_bin(value: int) -> str:
    if value == 0: return "D0"
    if value == 1: return "D1"
    if value == 2: return "D2"
    if value >= 3: return "D3_PLUS"
    raise ValueError(value)


def hour_bin(hour: int) -> str:
    if not 0 <= hour <= 23: raise ValueError(hour)
    start = (hour // 4) * 4
    return f"{start:02d}_{start+3:02d}"


def profit_factor(values: pd.Series) -> float | None:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0: return None if gains == 0 else float("inf")
    return gains / losses


def metrics(group: pd.DataFrame, pnl_col: str) -> dict:
    values = group[pnl_col].astype(float)
    months = pd.to_datetime(group.exit_server_open).dt.to_period("M").astype(str)
    shares = months.value_counts(normalize=True)
    return {
        "count": int(len(group)), "wins": int((values > 0).sum()),
        "losses": int((values < 0).sum()),
        "win_rate": float((values > 0).mean()) if len(group) else None,
        "profit_factor": profit_factor(values), "net_usd_1lot": float(values.sum()),
        "expectancy_usd_1lot": float(values.mean()) if len(group) else None,
        "gross_profit_usd_1lot": float(values[values > 0].sum()),
        "gross_loss_abs_usd_1lot": float(-values[values < 0].sum()),
        "distinct_exit_months": int(months.nunique()),
        "max_single_month_share": float(shares.max()) if len(shares) else None,
    }


def percentile(values: pd.Series, q: float) -> float | None:
    x = values.dropna().astype(float)
    return float(x.quantile(q)) if len(x) else None


def path_metrics_for_trade(row, price_index: pd.DataFrame) -> dict:
    entry, exit_ = pd.Timestamp(row.entry_server_open), pd.Timestamp(row.exit_server_open)
    expected = pd.date_range(entry, exit_, freq="15min")
    window = price_index.reindex(expected)
    missing = window.open.isna()
    base = {
        "expected_path_rows": int(len(expected)),
        "observed_path_rows": int(len(expected) - missing.sum()),
        "missing_path_rows": int(missing.sum()),
        "path_complete": bool(not missing.any()),
        "missing_server_opens": "|".join(ts.strftime("%Y-%m-%d %H:%M:%S") for ts in expected[missing]),
    }
    if missing.any(): return base

    active, exit_row = window.iloc[:-1].copy(), window.iloc[-1]
    entry_open, entry_spread = float(row.entry_open), float(row.entry_spread_price)
    entry_atr14 = float(price_index.loc[entry, "entry_atr14"])
    if row.direction == "LONG":
        entry_fill = entry_open + entry_spread
        favorable = active.high.astype(float) - entry_fill
        adverse = entry_fill - active.low.astype(float)
        exit_pnl = float(exit_row.open) - entry_fill
    else:
        entry_fill = entry_open
        favorable = entry_fill - (active.low.astype(float) + active.spread_price.astype(float))
        adverse = (active.high.astype(float) + active.spread_price.astype(float)) - entry_fill
        exit_pnl = entry_fill - (float(exit_row.open) + float(exit_row.spread_price))

    fav = np.asarray(list(favorable) + [exit_pnl], dtype=float)
    adv = np.asarray(list(adverse) + [-exit_pnl], dtype=float)
    mfe, mae = max(0.0, float(np.nanmax(fav))), max(0.0, float(np.nanmax(adv)))
    base.update({
        "entry_atr14": entry_atr14, "mfe_c0_usd_1lot": mfe, "mae_c0_usd_1lot": mae,
        "mfe_atr14": mfe / entry_atr14, "mae_atr14": mae / entry_atr14,
        "first_mfe_bar": int(np.nanargmax(fav)) if mfe > 0 else None,
        "first_mae_bar": int(np.nanargmax(adv)) if mae > 0 else None,
        "had_positive_mfe": mfe > 0,
        "giveback_from_mfe_to_exit_c0": max(0.0, mfe - float(row.pnl_C0_OBSERVED_SPREAD)),
    })

    crossings = int((exit_.date() - entry.date()).days)
    if crossings > 0:
        pre_cross = entry.normalize() + pd.Timedelta(hours=23, minutes=45)
        if pre_cross < entry: pre_cross += pd.Timedelta(days=1)
        available = pre_cross in price_index.index and pre_cross < exit_
        base["pre_first_cross_server_open"] = pre_cross.strftime("%Y-%m-%d %H:%M:%S")
        base["pre_first_cross_available"] = bool(available)
        if available:
            pre = price_index.loc[pre_cross]
            pre_pnl = float(pre.open) - entry_fill if row.direction == "LONG" else entry_fill - (float(pre.open) + float(pre.spread_price))
            before = active.loc[active.index <= pre_cross]
            if row.direction == "LONG":
                pre_fav = max(0.0, float((before.high.astype(float) - entry_fill).max()))
                pre_adv = max(0.0, float((entry_fill - before.low.astype(float)).max()))
            else:
                pre_fav = max(0.0, float((entry_fill - (before.low.astype(float) + before.spread_price.astype(float))).max()))
                pre_adv = max(0.0, float(((before.high.astype(float) + before.spread_price.astype(float)) - entry_fill).max()))
            base.update({"pnl_at_pre_first_cross_c0": pre_pnl,
                         "positive_at_pre_first_cross": pre_pnl > 0,
                         "mfe_before_first_cross_c0": pre_fav,
                         "mae_before_first_cross_c0": pre_adv})
    else:
        base["pre_first_cross_available"] = False
    return base


def deterministic_zip(directory: Path, output: Path) -> None:
    fixed = (2026, 7, 30, 11, 15, 0)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(directory.iterdir(), key=lambda p: p.name):
            if path.name == output.name: continue
            info = zipfile.ZipInfo(path.name, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, path.read_bytes())


def run(bcr09_path: Path, m15_path: Path, output_root: Path) -> Path:
    if sha256_file(bcr09_path) != BCR09_SHA: raise RuntimeError("BCR09 SHA mismatch")
    if sha256_file(m15_path) != M15_SHA: raise RuntimeError("M15 SHA mismatch")
    with zipfile.ZipFile(bcr09_path) as zf:
        trades = pd.read_csv(zf.open("03_trade_ledger_cost_enriched.csv"))
    diag = trades[trades.machine_id.isin(MACHINES)].copy()
    if diag.machine_id.value_counts().to_dict() != EXPECTED_COUNTS: raise RuntimeError("machine count mismatch")
    for col in ("entry_server_open", "exit_server_open"): diag[col] = pd.to_datetime(diag[col])
    if diag.duplicated(["machine_id", "direction", "entry_server_open", "exit_server_open"]).any(): raise RuntimeError("duplicate episode")

    m15 = pd.read_csv(m15_path, encoding="utf-8-sig")
    m15["server_open"] = pd.to_datetime(m15.time)
    for col in ("open", "high", "low", "close", "spread"): m15[col] = pd.to_numeric(m15[col], errors="raise")
    prev_close = m15.close.shift()
    tr = pd.concat([m15.high-m15.low, (m15.high-prev_close).abs(), (m15.low-prev_close).abs()], axis=1).max(axis=1)
    m15["atr14"] = tr.rolling(14, min_periods=14).mean()
    m15["entry_atr14"] = m15.atr14.shift(1)
    m15["spread_price"] = m15.spread * POINT
    prices = m15.set_index("server_open")

    records=[]
    for row in diag.itertuples(index=False):
        rec=row._asdict(); rec.update(path_metrics_for_trade(row, prices)); records.append(rec)
    diag=pd.DataFrame(records)
    diag["date_crossings"]=(diag.exit_server_open.dt.normalize()-diag.entry_server_open.dt.normalize()).dt.days.astype(int)
    diag["holding_bin"]=diag.holding_bars.astype(int).map(holding_bin)
    diag["date_crossing_bin"]=diag.date_crossings.map(crossing_bin)
    diag["entry_hour_bin"]=diag.entry_server_open.dt.hour.map(hour_bin)
    diag["exit_hour_bin"]=diag.exit_server_open.dt.hour.map(hour_bin)
    diag["entry_month"]=diag.entry_server_open.dt.to_period("M").astype(str)
    diag["exit_month"]=diag.exit_server_open.dt.to_period("M").astype(str)
    diag["gross_pnl_before_spread"]=np.where(diag.direction.eq("LONG"), diag.exit_open-diag.entry_open, diag.entry_open-diag.exit_open)
    diag["spread_cost_share_of_abs_gross"]=np.where(diag.gross_pnl_before_spread.abs()>0, diag.cost_C0_OBSERVED_SPREAD/diag.gross_pnl_before_spread.abs(), np.nan)
    if len(diag)!=5975: raise RuntimeError("episode parity failure")

    holding_rows=[]; crossing_rows=[]; hour_rows=[]; excursion_rows=[]; rollover_rows=[]; loss_rows=[]; month_rows=[]
    for (machine,direction), group in diag.groupby(["machine_id","direction"], sort=True):
        for name,sub in group.groupby("holding_bin",sort=True):
            for scenario,pnl in (("C0","pnl_C0_OBSERVED_SPREAD"),("C2","pnl_C2_25PCT_SPREAD_PER_FILL")):
                holding_rows.append({"machine_id":machine,"direction":direction,"holding_bin":name,"scenario":scenario,**metrics(sub,pnl)})
            month_rows.append({"machine_id":machine,"direction":direction,"phenotype_type":"HOLDING_BIN","phenotype":name,**metrics(sub,"pnl_C0_OBSERVED_SPREAD")})
        for name,sub in group.groupby("date_crossing_bin",sort=True):
            for scenario,pnl in (("C0","pnl_C0_OBSERVED_SPREAD"),("C2","pnl_C2_25PCT_SPREAD_PER_FILL")):
                crossing_rows.append({"machine_id":machine,"direction":direction,"date_crossing_bin":name,"scenario":scenario,**metrics(sub,pnl)})
            month_rows.append({"machine_id":machine,"direction":direction,"phenotype_type":"DATE_CROSSING_BIN","phenotype":name,**metrics(sub,"pnl_C0_OBSERVED_SPREAD")})
        for (eh,xh),sub in group.groupby(["entry_hour_bin","exit_hour_bin"],sort=True):
            hour_rows.append({"machine_id":machine,"direction":direction,"entry_hour_bin":eh,"exit_hour_bin":xh,**metrics(sub,"pnl_C0_OBSERVED_SPREAD")})
        for subset,sub in (("ALL",group),("D0_SAME_SERVER_DATE",group[group.date_crossings.eq(0)]),("ROLLOVER_EXPOSED",group[group.date_crossings.gt(0)])):
            complete=sub[sub.path_complete]
            excursion_rows.append({"machine_id":machine,"direction":direction,"subset":subset,"episode_count":len(sub),"path_complete_count":len(complete),"path_incomplete_count":int((~sub.path_complete).sum()),"mfe_median":percentile(complete.mfe_c0_usd_1lot,.5),"mfe_q25":percentile(complete.mfe_c0_usd_1lot,.25),"mfe_q75":percentile(complete.mfe_c0_usd_1lot,.75),"mae_median":percentile(complete.mae_c0_usd_1lot,.5),"mae_q25":percentile(complete.mae_c0_usd_1lot,.25),"mae_q75":percentile(complete.mae_c0_usd_1lot,.75),"giveback_median":percentile(complete.giveback_from_mfe_to_exit_c0,.5),"giveback_q25":percentile(complete.giveback_from_mfe_to_exit_c0,.25),"giveback_q75":percentile(complete.giveback_from_mfe_to_exit_c0,.75),"mfe_atr_median":percentile(complete.mfe_atr14,.5),"mae_atr_median":percentile(complete.mae_atr14,.5)})
        roll=group[group.date_crossings.gt(0)]; losers=roll[roll.pnl_C0_OBSERVED_SPREAD.lt(0)]; complete=losers[losers.path_complete]
        pre=complete[complete.pre_first_cross_available.eq(True)]; positive_pre=pre[pre.positive_at_pre_first_cross.eq(True)]; positive_mfe=complete[complete.mfe_c0_usd_1lot.gt(0)]
        total_loss=float(-losers.pnl_C0_OBSERVED_SPREAD.sum()); positive_mfe_loss=float(-positive_mfe.pnl_C0_OBSERVED_SPREAD.sum())
        rollover_rows.append({"machine_id":machine,"direction":direction,"rollover_episode_count":len(roll),"rollover_loser_count":len(losers),"rollover_loser_path_complete_count":len(complete),"pre_first_cross_available_loser_count":len(pre),"positive_at_pre_cross_loser_count":len(positive_pre),"positive_at_pre_cross_fraction_of_available_losers":len(positive_pre)/len(pre) if len(pre) else None,"positive_mfe_loser_count":len(positive_mfe),"positive_mfe_fraction_of_path_complete_losers":len(positive_mfe)/len(complete) if len(complete) else None,"positive_mfe_loser_loss_dollar_share":positive_mfe_loss/total_loss if total_loss>0 else None,"median_pre_cross_pnl_c0":percentile(pre.pnl_at_pre_first_cross_c0,.5),"median_final_loser_pnl_c0":percentile(losers.pnl_C0_OBSERVED_SPREAD,.5),"median_giveback_positive_mfe_losers":percentile(positive_mfe.giveback_from_mfe_to_exit_c0,.5)})
        losses=group[group.pnl_C0_OBSERVED_SPREAD.lt(0)]; total=float(-losses.pnl_C0_OBSERVED_SPREAD.sum())
        for (hbin,dbin),sub in losses.groupby(["holding_bin","date_crossing_bin"],sort=True):
            amount=float(-sub.pnl_C0_OBSERVED_SPREAD.sum())
            loss_rows.append({"machine_id":machine,"direction":direction,"holding_bin":hbin,"date_crossing_bin":dbin,"loser_count":len(sub),"loss_abs_usd_1lot":amount,"share_of_machine_direction_loss_dollars":amount/total if total>0 else None,"distinct_exit_months":pd.to_datetime(sub.exit_server_open).dt.to_period("M").nunique()})

    output_root.mkdir(parents=True,exist_ok=True); run_dir=output_root/"BCR10_DIAGNOSTIC_20260730"
    if run_dir.exists(): shutil.rmtree(run_dir)
    run_dir.mkdir()
    (run_dir/"00_READ_ME_FIRST.txt").write_text(f"BCR10 path diagnostic\nstatus: READY_OUTCOME_EXPOSED_DIAGNOSTIC_NO_OVERLAY_SELECTION\nepisodes: {len(diag)}\npath complete: {int(diag.path_complete.sum())}\npath incomplete: {int((~diag.path_complete).sum())}\nNo overlay PnL or candidate selection was performed.\n",encoding="utf-8")
    summary={"stage":STAGE,"recorded_at":RECORDED_AT,"status":"READY_OUTCOME_EXPOSED_DIAGNOSTIC_NO_OVERLAY_SELECTION","bcr09_sha256":BCR09_SHA,"m15_sha256":M15_SHA,"machine_count":6,"episode_count":len(diag),"path_complete_count":int(diag.path_complete.sum()),"path_incomplete_count":int((~diag.path_complete).sum()),"date_crossing_counts":{str(k):int(v) for k,v in diag.date_crossing_bin.value_counts().sort_index().items()},"holding_bin_counts":{str(k):int(v) for k,v in diag.holding_bin.value_counts().sort_index().items()},"overlay_pnl_evaluated":False,"candidate_selected":False,"portfolio_selected":False,"prospective_or_shadow_authorized":False,"outcome_exposure":"RETROSPECTIVE_FULL_HISTORY_EXPOSED_DIAGNOSTIC"}
    (run_dir/"01_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    diag.to_csv(run_dir/"02_episode_path_diagnostic.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(holding_rows).to_csv(run_dir/"03_holding_bin_metrics.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(crossing_rows).to_csv(run_dir/"04_date_crossing_bin_metrics.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(hour_rows).to_csv(run_dir/"05_entry_exit_hour_matrix.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(excursion_rows).to_csv(run_dir/"06_excursion_summary.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(rollover_rows).to_csv(run_dir/"07_rollover_loss_phenotype.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(loss_rows).to_csv(run_dir/"08_loss_concentration.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    pd.DataFrame(month_rows).to_csv(run_dir/"09_month_coverage.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    diag.loc[~diag.path_complete,["machine_id","direction","entry_server_open","exit_server_open","holding_bars","missing_path_rows","missing_server_opens","pnl_C0_OBSERVED_SPREAD","date_crossing_bin"]].to_csv(run_dir/"10_gap_cases.csv",index=False,encoding="utf-8-sig",float_format="%.12g")
    formulas={"path_interval":"entry-bar high/low through bar before exit; actual exit open included; exit-bar high/low excluded","long_mfe":"max BID high minus entry ask","long_mae":"entry ask minus min BID low","short_mfe":"entry BID minus min contemporaneous ask-low","short_mae":"max contemporaneous ask-high minus entry BID","entry_atr14":"previous fully closed M15 ATR14","giveback":"max(0,MFE_C0-final_PnL_C0)","pre_first_cross":"exact 23:45 server-open before first midnight","gap_policy":"retain episode and realized PnL; no MFE/MAE when path incomplete","overlay_pnl_evaluated":False}
    (run_dir/"11_formula_manifest.json").write_text(json.dumps(formulas,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    integrity={"six_machine_population_only":set(diag.machine_id)==set(MACHINES),"all_eligible_bcr09_closed_episodes_exactly_once":len(diag)==5975 and not diag.duplicated(["machine_id","direction","entry_server_open","exit_server_open"]).any(),"fixed_holding_bins":sorted(diag.holding_bin.unique()),"fixed_date_crossing_bins":sorted(diag.date_crossing_bin.unique()),"fixed_hour_bins":sorted(set(diag.entry_hour_bin)|set(diag.exit_hour_bin)),"exact_path_no_interpolation":True,"path_incomplete_explicit":int((~diag.path_complete).sum()),"direction_correct_mfe_mae_tested":True,"overlay_pnl_columns_present":False,"candidate_selected":False,"runtime_modified":False,"gold_mochipoyo_used":False}
    (run_dir/"12_integrity_checks.json").write_text(json.dumps(integrity,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    manifest={}
    for name in FILES:
        if name=="13_file_sha256_manifest.json": continue
        p=run_dir/name; manifest[name]={"sha256":sha256_file(p),"bytes":p.stat().st_size}
    (run_dir/"13_file_sha256_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    zip_path=output_root/"BCR10_HOLDING_ROLLOVER_PATH_DIAGNOSTIC_20260730.zip"
    if zip_path.exists(): zip_path.unlink()
    deterministic_zip(run_dir,zip_path)
    return zip_path


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--bcr09",type=Path,required=True); p.add_argument("--m15",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True)
    a=p.parse_args(); print(run(a.bcr09,a.m15,a.output_root)); return 0


if __name__=="__main__": raise SystemExit(main())
