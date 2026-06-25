from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

path = Path(__file__).with_name("nine_candidate_local_replay_v4.py")
spec = importlib.util.spec_from_file_location("batch023_v4", path)
if spec is None or spec.loader is None:
    raise RuntimeError(path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def prepare(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = frame.copy()
    out["atr14"] = module.atr_for_name(out, "sma14_full")
    if timeframe == "H1":
        mean = out["close"].rolling(60, min_periods=60).mean()
        sd = out["close"].rolling(60, min_periods=60).std(ddof=0)
        out["bb60_upper"] = mean + 2.0 * sd
        out["spread_atr"] = out["spread"] * module.base.POINT / out["atr14"]
        return out
    if timeframe == "D1":
        out["rci18"] = module.rci_variant(out["close"], 18, "average", "d2")
        out["tickvol_ratio50"] = out["tick_volume"] / out["tick_volume"].rolling(50, min_periods=50).mean()
        out["delta_atr_3"] = (out["close"] - out["close"].shift(3)) / out["atr14"]
        return out
    raise ValueError(timeframe)


module.prepare_h1_d1 = prepare
raise SystemExit(module.main())
