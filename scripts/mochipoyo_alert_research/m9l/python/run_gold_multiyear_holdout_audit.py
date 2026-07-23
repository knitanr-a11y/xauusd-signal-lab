from __future__ import annotations

import bisect
import csv
import hashlib
import json
import os
import shutil
import statistics
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
LONG_EXIT_RCI9 = 78.333333333333
SHORT_EXIT_RCI9 = -75.0
TURN_LOOKBACK = 5

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from feature_snapshot_builder import MINIMUM_WARMUP_BARS, load_indicator_series, rci_value

EXPECTED = {
    "M1": ("gold_v3_2023_2026_m1.csv", "dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2"),
    "M5": ("gold_v3_2023_2026_m5.csv", "c47c0a136e8a953bf219bfbcb80a79ccacac3afb04a0ed6e825843eba143948d"),
    "M15": ("gold_v3_2023_2026_m15.csv", "e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28"),
    "H1": ("gold_v3_2023_2026_h1.csv", "fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a"),
    "H4": ("gold_v3_2023_2026_h4.csv", "5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913"),
    "D1": ("gold_v3_2023_2026_d1.csv", "58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6"),
}
EXPECTED_HEADER = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise RuntimeError(f"unexpected header: {path.name}")
        rows = list(reader)
    if not rows:
        raise RuntimeError(f"empty CSV: {path.name}")
    return rows


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


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def load_m1(path: Path) -> list[dict[str, Any]]:
    raw = read_csv(path)
    output: list[dict[str, Any]] = []
    previous: datetime | None = None
    for row in raw:
        current = parse_time(row["time"])
        if previous is not None and current <= previous:
            raise RuntimeError(f"M1 timestamp not strictly ascending: {row['time']}")
        previous = current
        output.append({
            "time": current,
            "time_text": row["time"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "spread": int(row["spread"]),
        })
    return output


def execution_entry(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "LONG" else row["open"]


def execution_exit(direction: str, row: dict[str, Any], point: float) -> float:
    return row["open"] + row["spread"] * point if direction == "SHORT" else row["open"]


def bps(delta: float, reference: float) -> float:
    return delta / abs(reference) * 10000.0


def trade_return(direction: str, entry: float, exit_price: float) -> float:
    return bps(exit_price - entry, entry) if direction == "LONG" else bps(entry - exit_price, entry)


def metrics(rows: list[dict[str, Any]], key: str, order_key: str) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row[order_key])
    values = [float(row[key]) for row in ordered if row.get(key) not in (None, "")]
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    positive = [v for v in values if v > 0]
    negative = [v for v in values if v < 0]
    return {
        "count": len(values),
        "win_rate": sum(v > 0 for v in values) / len(values),
        "profit_factor_bps": None if losses == 0 else wins / losses,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
        "median_bps": statistics.median(values),
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
        "average_win_bps": statistics.fmean(positive) if positive else None,
        "average_loss_bps": statistics.fmean(negative) if negative else None,
    }


def replay_m7c(m15_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    series = load_indicator_series(m15_path)
    signals: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    state = "IDLE"
    open_primary: dict[str, Any] | None = None
    seq = 0
    for current_index in range(MINIMUM_WARMUP_BARS, len(series.bars)):
        current_bar = series.bars[current_index]
        selected_index = current_index - 1
        rci9 = series.rci[9][selected_index]
        p1 = series.rci[9][selected_index - 1]
        p2 = series.rci[9][selected_index - 2]
        if rci9 is None or p1 is None or p2 is None:
            continue
        turn_up = rci9 > p1 and p1 <= p2
        turn_down = rci9 < p1 and p1 >= p2
        e20 = series.ema[20][selected_index]
        e30 = series.ema[30][selected_index]
        e40 = series.ema[40][selected_index]
        bullish = e20 > e30 > e40
        bearish = e20 < e30 < e40
        transition: str | None = None
        state_before = state
        if state == "IDLE":
            if turn_up and bullish:
                transition = "PRIMARY_LONG"
                state_after = "ACTIVE_LONG"
            elif turn_down and bearish:
                transition = "PRIMARY_SHORT"
                state_after = "ACTIVE_SHORT"
            else:
                continue
        elif state == "ACTIVE_LONG":
            if rci9 >= LONG_EXIT_RCI9:
                transition = "LONG_EXIT"
                state_after = "IDLE"
            else:
                continue
        else:
            if rci9 <= SHORT_EXIT_RCI9:
                transition = "SHORT_EXIT"
                state_after = "IDLE"
            else:
                continue
        seq += 1
        row = {
            "signal_id": f"XAU_MULTI_{seq:06d}",
            "server_open": current_bar.server_open.strftime(TIME_FORMAT),
            "selected_feature_bar_server_open": series.bars[selected_index].server_open.strftime(TIME_FORMAT),
            "transition": transition,
            "state_before": state_before,
            "state_after": state_after,
            "rci9": float(rci9),
            "ema20": float(e20),
            "ema30": float(e30),
            "ema40": float(e40),
        }
        signals.append(row)
        if transition.startswith("PRIMARY_"):
            open_primary = {**row, "direction": "LONG" if transition == "PRIMARY_LONG" else "SHORT"}
        else:
            if open_primary is None:
                raise RuntimeError(f"exit without open primary at {row['server_open']}")
            pairs.append({
                "trade_id": f"XAU_MULTI_T{len(pairs)+1:06d}",
                "direction": open_primary["direction"],
                "entry_server_open": open_primary["server_open"],
                "exit_server_open": row["server_open"],
                "entry_rci9": open_primary["rci9"],
                "exit_rci9": row["rci9"],
            })
            open_primary = None
        state = state_after
    return signals, pairs


def is_turn_candidate(direction: str, rows: list[dict[str, Any]], index: int, signal_bid: float) -> bool:
    if index < 1:
        return False
    previous = rows[index - 1]
    current = rows[index]
    history = rows[max(0, index - TURN_LOOKBACK):index]
    if len(history) < TURN_LOOKBACK:
        return False
    if direction == "LONG":
        return previous["low"] <= min(row["low"] for row in history) and previous["low"] < signal_bid and current["close"] > previous["close"]
    return previous["high"] >= max(row["high"] for row in history) and previous["high"] > signal_bid and current["close"] < previous["close"]


def first_turn_rows(resolved: list[dict[str, Any]], m1: list[dict[str, Any]], m1_index: dict[str, int], point: float, h1_path: Path) -> list[dict[str, Any]]:
    h1 = load_indicator_series(h1_path)
    h1_close_times = [bar.server_open + timedelta(hours=1) for bar in h1.bars]
    output: list[dict[str, Any]] = []
    for trade in resolved:
        ai = m1_index[trade["entry_server_open"]]
        zi = m1_index[trade["exit_server_open"]]
        signal_bid = m1[ai]["open"]
        for index in range(ai + 1, zi):
            if index + 1 >= zi:
                break
            if not is_turn_candidate(trade["direction"], m1, index, signal_bid):
                continue
            turn_index = index + 1
            entry_exec = execution_entry(trade["direction"], m1[turn_index], point)
            exit_exec = execution_exit(trade["direction"], m1[zi], point)
            decision_time = m1[turn_index]["time"]
            h1_index = bisect.bisect_right(h1_close_times, decision_time) - 1
            h1_rci9 = h1.rci[9][h1_index] if h1_index >= 0 else None
            directional_h1 = None if h1_rci9 is None else (float(h1_rci9) if trade["direction"] == "LONG" else -float(h1_rci9))
            m1_selected = turn_index - 1
            m1_rci18 = None
            if m1_selected >= 17:
                m1_rci18 = rci_value([row["close"] for row in m1[m1_selected - 17:m1_selected + 1]])
            output.append({
                **trade,
                "turn_entry_time": m1[turn_index]["time_text"],
                "return_from_first_turn_bps": trade_return(trade["direction"], entry_exec, exit_exec),
                "turn_h1_directional_rci9": directional_h1,
                "turnrich_m1_rci18": m1_rci18,
            })
            break
    return output


def yearly(rows: list[dict[str, Any]], key: str, time_key: str) -> list[dict[str, Any]]:
    years = sorted({row[time_key][:4] for row in rows})
    result: list[dict[str, Any]] = []
    for year in years:
        group = [row for row in rows if row[time_key].startswith(year)]
        result.append({"year": year, **metrics(group, key, time_key)})
    return result


def branch_yearly(rows: list[dict[str, Any]], key: str, time_key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    years = sorted({row[time_key][:4] for row in rows})
    for year in years:
        for direction in ("LONG", "SHORT"):
            group = [row for row in rows if row[time_key].startswith(year) and row["direction"] == direction]
            result.append({"year": year, "direction": direction, **metrics(group, key, time_key)})
    return result


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not meta_path.is_file():
        print("[M9L BLOCKED] M8B symbol metadata missing")
        return 2
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9L BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2
    paths: dict[str, Path] = {}
    try:
        for timeframe, (name, expected_hash) in EXPECTED.items():
            path = files_root / name
            if not path.is_file():
                raise RuntimeError(f"required uploaded GOLD file missing from MT5 Files root: {name}")
            actual_hash = sha256(path)
            if actual_hash != expected_hash:
                raise RuntimeError(f"SHA256 mismatch for {name}: {actual_hash}")
            paths[timeframe] = path

        signals, pairs = replay_m7c(paths["M15"])
        m1 = load_m1(paths["M1"])
        m1_index = {row["time_text"]: index for index, row in enumerate(m1)}
        point = float(meta["symbols"]["XAUUSD"]["point"])
        resolved: list[dict[str, Any]] = []
        missing_exact = 0
        for pair in pairs:
            if pair["entry_server_open"] not in m1_index or pair["exit_server_open"] not in m1_index:
                missing_exact += 1
                continue
            ai = m1_index[pair["entry_server_open"]]
            zi = m1_index[pair["exit_server_open"]]
            if zi <= ai:
                continue
            entry_exec = execution_entry(pair["direction"], m1[ai], point)
            exit_exec = execution_exit(pair["direction"], m1[zi], point)
            resolved.append({**pair, "return_bps": trade_return(pair["direction"], entry_exec, exit_exec)})

        turns = first_turn_rows(resolved, m1, m1_index, point, paths["H1"])
        h2 = [row for row in turns if not (row["direction"] == "LONG" and row.get("turn_h1_directional_rci9") is not None and float(row["turn_h1_directional_rci9"]) >= 80.0)]
        h3 = [row for row in h2 if not (row["direction"] == "SHORT" and row.get("turnrich_m1_rci18") is not None and float(row["turnrich_m1_rci18"]) <= -80.0)]

        pre_resolved = [row for row in resolved if row["entry_server_open"][:4] in ("2023", "2024", "2025")]
        pre_turns = [row for row in turns if row["turn_entry_time"][:4] in ("2023", "2024", "2025")]
        pre_h2 = [row for row in h2 if row["turn_entry_time"][:4] in ("2023", "2024", "2025")]
        pre_h3 = [row for row in h3 if row["turn_entry_time"][:4] in ("2023", "2024", "2025")]

    except Exception as exc:
        print(f"[M9L BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9L_GOLD_2023_2026_MULTIYEAR_HOLDOUT_AUDIT",
        "contract": "MOCHIPOYO_M9L_GOLD_MULTIYEAR_HOLDOUT_V1",
        "status": "PASS_HISTORICAL_HOLDOUT_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "M1_rows": len(m1),
            "M15_signal_count": len(signals),
            "paired_trade_count": len(pairs),
            "exact_m1_resolved_trade_count": len(resolved),
            "first_turn_count": len(turns),
            "missing_exact_m1_entry_or_exit": missing_exact,
        },
        "m7c_2023_2025_immediate": metrics(pre_resolved, "return_bps", "entry_server_open"),
        "m7c_2023_2025_first_turn": metrics(pre_turns, "return_from_first_turn_bps", "turn_entry_time"),
        "prefrozen_h2_2023_2025": metrics(pre_h2, "return_from_first_turn_bps", "turn_entry_time"),
        "prefrozen_h3_2023_2025": metrics(pre_h3, "return_from_first_turn_bps", "turn_entry_time"),
        "holdout_decisions": {
            "H2": "REJECT_IF_2023_2025_PF_DOES_NOT_CLEAR_1_WITH_STABLE_YEARLY_SUPPORT",
            "H3": "REJECT_IF_2023_2025_PF_DOES_NOT_CLEAR_1_WITH_STABLE_YEARLY_SUPPORT",
            "next_partition": "Use 2023-2024 only for new GOLD hypothesis discovery. Keep 2025 feature/outcome relationships sealed until hypotheses are frozen. 2026 is reference only."
        },
        "guardrails": {
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
            "historical_spread_used": True,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
            "automatic_gate_promotion": False,
            "audit_only": True,
        },
    }
    year_immediate = yearly(resolved, "return_bps", "entry_server_open")
    year_turn = yearly(turns, "return_from_first_turn_bps", "turn_entry_time")
    branch_immediate = branch_yearly(resolved, "return_bps", "entry_server_open")
    branch_turn = branch_yearly(turns, "return_from_first_turn_bps", "turn_entry_time")
    h2_year = yearly(h2, "return_from_first_turn_bps", "turn_entry_time")
    h3_year = yearly(h3, "return_from_first_turn_bps", "turn_entry_time")

    out_root = local_root / "outputs" / "M9L"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9L replays the unchanged frozen M7C XAUUSD proxy on the user-supplied 2023-2026 GOLD data. "
        "2023-2025 are historical holdout for previously frozen H2/H3 only. New GOLD hypotheses must be discovered using 2023-2024 only, with 2025 feature/outcome relationships reserved for later validation. Commission/swap are not modeled.\n",
        encoding="utf-8",
    )
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_yearly_immediate_summary.csv", year_immediate)
    write_csv(archive / "03_yearly_first_turn_summary.csv", year_turn)
    write_csv(archive / "04_branch_yearly_immediate_summary.csv", branch_immediate)
    write_csv(archive / "05_branch_yearly_first_turn_summary.csv", branch_turn)
    write_csv(archive / "06_prefrozen_h2_yearly_summary.csv", h2_year)
    write_csv(archive / "07_prefrozen_h3_yearly_summary.csv", h3_year)
    write_csv(archive / "08_trade_outcomes.csv", resolved)
    write_csv(archive / "09_first_turn_outcomes.csv", turns)
    dump_json(archive / "10_data_hashes.json", {tf: {"file": EXPECTED[tf][0], "sha256": EXPECTED[tf][1]} for tf in EXPECTED})
    (archive / "11_audit.log").write_text(
        "\n".join([
            "status=PASS_HISTORICAL_HOLDOUT_ONLY",
            f"signals={len(signals)}",
            f"paired_trades={len(pairs)}",
            f"resolved={len(resolved)}",
            f"first_turn={len(turns)}",
            f"missing_exact_m1={missing_exact}",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "2025_reserved_for_next_new_gold_hypothesis_holdout=true",
            "",
        ]), encoding="utf-8"
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_yearly_immediate_summary.csv", "03_yearly_first_turn_summary.csv",
        "04_branch_yearly_immediate_summary.csv", "05_branch_yearly_first_turn_summary.csv", "06_prefrozen_h2_yearly_summary.csv",
        "07_prefrozen_h3_yearly_summary.csv", "08_trade_outcomes.csv", "09_first_turn_outcomes.csv", "10_data_hashes.json", "11_audit.log"
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M9L PASS] resolved={len(resolved)} first_turn={len(turns)}")
    print("[M9L OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
