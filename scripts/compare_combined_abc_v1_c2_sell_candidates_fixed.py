from __future__ import annotations

import sys
from pathlib import Path

# Allow running as: python scripts/compare_combined_abc_v1_c2_sell_candidates_fixed.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.compare_combined_abc_v1_c2_sell_candidates as original
from src.presets import get_preset


_original_apply_preset_defaults = original.apply_preset_defaults


def apply_preset_defaults_with_c_fields(args):
    """Patch preset defaults for the original C2 comparison script.

    The original comparison script reuses run_combined_abc_backtest.run_symbol(),
    which expects C1 preset fields to already be present on args. Generic
    apply_preset_defaults() fills A/B fields, but not the newer C fields.

    Without this patch, gold_abc_v1 baseline is accidentally run with:
        - C BUY hours = ALL
        - C BUY H1 EMA gap max = None
    which produces a wrong baseline such as 207 trades instead of the confirmed
    gold_abc_v1 result around 150 trades.
    """
    args = _original_apply_preset_defaults(args)
    preset = get_preset(args.preset)

    args.preset_name = preset.name

    if getattr(args, "models", None) is None:
        args.models = preset.models

    if getattr(args, "c_breakout_lookback_bars", None) is None and preset.c_breakout_lookback_bars is not None:
        args.c_breakout_lookback_bars = preset.c_breakout_lookback_bars

    if getattr(args, "c_buy_jst_hours", None) is None:
        args.c_buy_jst_hours = preset.c_buy_jst_hours

    if getattr(args, "c_sell_jst_hours", None) is None:
        args.c_sell_jst_hours = preset.c_sell_jst_hours

    if getattr(args, "c_buy_h1_ema_gap_atr_max", None) is None:
        args.c_buy_h1_ema_gap_atr_max = preset.c_buy_h1_ema_gap_atr_max

    return args


original.apply_preset_defaults = apply_preset_defaults_with_c_fields


if __name__ == "__main__":
    raise SystemExit(original.main())
