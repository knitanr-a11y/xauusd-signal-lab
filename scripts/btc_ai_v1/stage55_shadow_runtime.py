from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from stage55_shadow_candidates import build_short_candidates
from stage55_shadow_features import build_source_ledger, expand_path, load_csv


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_model_artifact(script_path: Path) -> Path:
    filename = "m1_cp30_logistic_q70_bootstrap_model_202608.json"
    candidates = [
        script_path.resolve().parents[1] / "config" / filename,
        script_path.resolve().parents[2] / "config" / "btc_ai_v1" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Frozen Stage55 model artifact not found: " + ", ".join(map(str, candidates)))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC Stage55 observation-only dual reverse-SHORT shadow")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    cfg = read_json(args.config)
    script_path = Path(__file__)
    state_root = expand_path(cfg["state_root"]); state_root.mkdir(parents=True, exist_ok=True)
    outputs = state_root / "outputs"; outputs.mkdir(exist_ok=True)
    logs = state_root / "logs"; logs.mkdir(exist_ok=True)
    logging.basicConfig(filename=logs / "shadow_runtime.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data = {tf: load_csv(expand_path(cfg["ohlc_paths"][tf]), tf) for tf in ["H4", "M15", "M5", "M1"]}
    latest = pd.Timestamp(data["M1"].close_time.iloc[-1])
    state_path = state_root / "runtime_state.json"
    state = read_json(state_path) if state_path.exists() else {}
    if not state:
        if not args.activate:
            raise RuntimeError("Not activated. Run once with --activate; existing data is consumed with no backfill.")
        state = {"contract_id": cfg["contract_id"], "activated_at_m1_close": latest.isoformat(),
                 "last_seen_m1_close": latest.isoformat(), "accepted_candidate_keys": [],
                 "recovery_candidate_keys": [], "runs": 1}
        write_json(state_path, state)
        write_json(state_root / "runtime_health.json", {"status": "READY_NO_BACKFILL_ACTIVATED",
                   "latest_m1_close": latest, "accepted_candidates": 0})
        print(json.dumps({"status": "READY_NO_BACKFILL_ACTIVATED", "latest_m1_close": str(latest)}, ensure_ascii=False))
        return
    activated = pd.Timestamp(state["activated_at_m1_close"]); previous = pd.Timestamp(state["last_seen_m1_close"])
    model = read_json(resolve_model_artifact(script_path))
    m1_src = build_source_ledger("M1", data["H4"], data["M15"], data["M1"], data["M1"])
    m5_src = build_source_ledger("M5", data["H4"], data["M15"], data["M5"], data["M1"])
    candidates = build_short_candidates(m1_src, m5_src, model, data["H4"], data["M15"], data["M5"], data["M1"], activated)
    if candidates.empty:
        candidates = pd.DataFrame(columns=["candidate_key", "family", "confirmation_time", "entry_time", "status", "pnl"])
    else:
        candidates["confirmation_time"] = pd.to_datetime(candidates.confirmation_time)
        candidates = candidates[candidates.confirmation_time > activated].copy()
    accepted = set(state.get("accepted_candidate_keys", [])); recovery = set(state.get("recovery_candidate_keys", []))
    gap_minutes = (latest - previous).total_seconds() / 60
    max_gap = float(cfg.get("max_recoverable_poll_gap_minutes", 10))
    for _, row in candidates.iterrows():
        key = str(row.candidate_key)
        if key in accepted or key in recovery:
            continue
        if pd.Timestamp(row.confirmation_time) <= previous or gap_minutes > max_gap:
            recovery.add(key)
        else:
            accepted.add(key)
    candidates["observation_status"] = candidates.candidate_key.map(
        lambda key: "ACCEPTED_SHADOW" if key in accepted else ("RECOVERY_REPLAY_NOT_TRADED" if key in recovery else "PENDING"))
    candidates.to_csv(outputs / "shadow_candidate_ledger.csv", index=False)
    candidates[candidates.observation_status == "ACCEPTED_SHADOW"].to_csv(outputs / "shadow_trade_ledger.csv", index=False)
    m1_src.to_csv(outputs / "source_m1_synthetic_long_ledger.csv", index=False)
    m5_src.to_csv(outputs / "source_m5_synthetic_long_ledger.csv", index=False)
    state.update({"last_seen_m1_close": latest.isoformat(), "accepted_candidate_keys": sorted(accepted),
                  "recovery_candidate_keys": sorted(recovery), "runs": int(state.get("runs", 0)) + 1})
    write_json(state_path, state)
    health = {"status": "READY_OBSERVATION_ONLY", "latest_m1_close": latest, "poll_gap_minutes": gap_minutes,
              "accepted_candidates": len(accepted), "recovery_candidates": len(recovery),
              "shadow": True, "discord": False, "mt5_orders": False, "live_trading": False}
    write_json(state_root / "runtime_health.json", health)
    print(json.dumps(health, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
