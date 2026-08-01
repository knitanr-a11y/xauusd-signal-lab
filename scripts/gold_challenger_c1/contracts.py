from __future__ import annotations
from pathlib import Path
import json

CANDIDATE_ID = "GOLD_CHALLENGER_C1_V2_DATA_V3"
SEED = 20260801
FIXED_SPREAD = 0.30
SPREAD_GATE_POINTS = 30
E40_TARGET = 40.0
E40_STOP = 20.0
E40_HORIZON = 720
T20_TARGET = 20.0
T20_STOP = 10.0
T20_HORIZON = 480
RANK_CEILING = 0.90
TRAIN_START = "2023-01-01"
TARGET_STATES = frozenset({"IMPULSE_LATE", "CORRECTION_EARLY"})
ALLOWED_ENTRY_COLUMNS = (
    "decision_dt", "origin_id", "entry_idx", "chosen_side", "chosen_rank",
    "wave_state", "episode_id", "previous_decision_dt",
)
FORBIDDEN_ENTRY_EXACT = frozenset({
    "immediate_pnl", "pnl", "mfe", "mae", "exit_dt", "exit_price",
    "outcome", "winner", "tp_hit", "sl_hit",
})

def load_contract(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
