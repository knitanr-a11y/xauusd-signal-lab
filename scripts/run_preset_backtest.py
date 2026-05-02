from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Allow running as: python scripts/run_preset_backtest.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.presets import get_preset, list_preset_names


def build_combined_backtest_command(preset_name: str, save: bool, data_dir: Path | None) -> list[str]:
    preset = get_preset(preset_name)
    enabled_models = {item.strip().upper() for item in preset.models.split(",") if item.strip()}

    if "C2" in enabled_models:
        runner = "run_combined_abcc2_backtest.py"
    elif "C" in enabled_models:
        runner = "run_combined_abc_backtest.py"
    else:
        needs_extended_runner = any(
            [
                preset.a_exclude_hidden_price_delta_atr_lte is not None,
                preset.b_buy_exclude_risk_atr_range is not None,
                preset.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo is not None,
            ]
        )
        runner = "run_combined_backtest_with_a_filters.py" if needs_extended_runner else "run_combined_backtest.py"

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / runner),
    ]

    if data_dir is not None:
        command.extend(["--data-dir", str(data_dir)])

    # Only ABC/ABCC2 runners accept --preset-name. The older AB-only runners do not.
    if runner in {"run_combined_abc_backtest.py", "run_combined_abcc2_backtest.py"}:
        command.extend(["--preset-name", preset.name])

    command.extend(
        [
            "--symbols",
            preset.symbols,
            "--models",
            preset.models,
            "--near-atr",
            str(preset.near_atr),
            "--close-tolerance-atr",
            str(preset.close_tolerance_atr),
            "--swing-left",
            str(preset.swing_left),
            "--swing-right",
            str(preset.swing_right),
            "--recent-pullback-bars",
            str(preset.recent_pullback_bars),
            "--rr",
            str(preset.rr),
            "--sl-buffer-atr",
            str(preset.sl_buffer_atr),
            "--server-timezone",
            preset.server_timezone,
            "--server-utc-offset",
            str(preset.server_utc_offset),
            "--a-buy-jst-hours",
            preset.a_buy_jst_hours,
            "--a-sell-jst-hours",
            preset.a_sell_jst_hours,
            "--b-buy-jst-hours",
            preset.b_buy_jst_hours,
            "--b-sell-jst-hours",
            preset.b_sell_jst_hours,
        ]
    )

    if preset.a_exclude_hidden_price_delta_atr_lte is not None:
        command.extend([
            "--a-exclude-hidden-price-delta-atr-lte",
            str(preset.a_exclude_hidden_price_delta_atr_lte),
        ])
    if preset.b_exclude_risk_atr_range:
        command.extend(["--b-exclude-risk-atr-range", preset.b_exclude_risk_atr_range])
    if preset.b_exclude_macd_hist_delta_abs_range:
        command.extend(["--b-exclude-macd-hist-delta-abs-range", preset.b_exclude_macd_hist_delta_abs_range])
    if preset.b_buy_exclude_risk_atr_range:
        command.extend(["--b-buy-exclude-risk-atr-range", preset.b_buy_exclude_risk_atr_range])
    if preset.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo:
        command.extend([
            "--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo",
            preset.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo,
        ])
    if "C" in enabled_models:
        if preset.c_breakout_lookback_bars is not None:
            command.extend(["--c-breakout-lookback-bars", str(preset.c_breakout_lookback_bars)])
        if preset.c_buy_jst_hours is not None:
            command.extend(["--c-buy-jst-hours", preset.c_buy_jst_hours])
        if preset.c_sell_jst_hours is not None:
            command.extend(["--c-sell-jst-hours", preset.c_sell_jst_hours])
        if preset.c_buy_h1_ema_gap_atr_max is not None:
            command.extend(["--c-buy-h1-ema-gap-atr-max", str(preset.c_buy_h1_ema_gap_atr_max)])
    if "C2" in enabled_models:
        if preset.c2_range_lookback_bars is not None:
            command.extend(["--c2-range-lookback-bars", str(preset.c2_range_lookback_bars)])
        if preset.c2_max_range_width_atr is not None:
            command.extend(["--c2-max-range-width-atr", str(preset.c2_max_range_width_atr)])
        if preset.c2_min_breakout_atr is not None:
            command.extend(["--c2-min-breakout-atr", str(preset.c2_min_breakout_atr)])
        if preset.c2_max_breakout_atr is not None:
            command.extend(["--c2-max-breakout-atr", str(preset.c2_max_breakout_atr)])
        if preset.c2_buy_jst_hours is not None:
            command.extend(["--c2-buy-jst-hours", preset.c2_buy_jst_hours])
        if preset.c2_sell_jst_hours is not None:
            command.extend(["--c2-sell-jst-hours", preset.c2_sell_jst_hours])
        command.extend(["--c2-disable-buy" if preset.c2_disable_buy else "--no-c2-disable-buy"])
        command.extend(["--c2-disable-sell" if preset.c2_disable_sell else "--no-c2-disable-sell"])
    if preset.use_fixed_offset:
        command.append("--use-fixed-offset")
    if preset.no_ema20_reclaim:
        command.append("--no-ema20-reclaim")
    if preset.no_macd_signal_alignment:
        command.append("--no-macd-signal-alignment")
    if preset.no_histogram_acceleration:
        command.append("--no-histogram-acceleration")
    if preset.same_bar_win:
        command.append("--same-bar-win")
    if preset.max_bars_in_trade is not None:
        command.extend(["--max-bars-in-trade", str(preset.max_bars_in_trade)])
    if save:
        command.append("--save")

    return command


def print_preset_details(preset_name: str) -> None:
    preset = get_preset(preset_name)
    print("=" * 120)
    print(f"preset: {preset.name}")
    print(f"description: {preset.description}")
    print(f"symbols: {preset.symbols}")
    print(f"models: {preset.models}")
    print(f"near_atr: {preset.near_atr}")
    print(f"close_tolerance_atr: {preset.close_tolerance_atr}")
    print(f"swing_left: {preset.swing_left}")
    print(f"swing_right: {preset.swing_right}")
    print(f"recent_pullback_bars: {preset.recent_pullback_bars}")
    print(f"rr: {preset.rr}")
    print(f"sl_buffer_atr: {preset.sl_buffer_atr}")
    print(f"A BUY JST hours: {preset.a_buy_jst_hours}")
    print(f"A SELL JST hours: {preset.a_sell_jst_hours}")
    print(f"A exclude hidden_price_delta_atr <=: {preset.a_exclude_hidden_price_delta_atr_lte if preset.a_exclude_hidden_price_delta_atr_lte is not None else 'NONE'}")
    print(f"B BUY JST hours: {preset.b_buy_jst_hours}")
    print(f"B SELL JST hours: {preset.b_sell_jst_hours}")
    print(f"B exclude risk_atr_range: {preset.b_exclude_risk_atr_range or 'NONE'}")
    print(f"B exclude macd_hist_delta_abs_range: {preset.b_exclude_macd_hist_delta_abs_range or 'NONE'}")
    print(f"B BUY exclude risk_atr_range: {preset.b_buy_exclude_risk_atr_range or 'NONE'}")
    print(f"B BUY exclude risk/macd combo: {preset.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo or 'NONE'}")
    print(f"C breakout lookback bars: {preset.c_breakout_lookback_bars if preset.c_breakout_lookback_bars is not None else 'NONE'}")
    print(f"C BUY JST hours: {preset.c_buy_jst_hours or 'NONE'}")
    print(f"C SELL JST hours: {preset.c_sell_jst_hours or 'NONE'}")
    print(f"C BUY H1 EMA gap ATR max: {preset.c_buy_h1_ema_gap_atr_max if preset.c_buy_h1_ema_gap_atr_max is not None else 'NONE'}")
    print(f"C2 range lookback bars: {preset.c2_range_lookback_bars if preset.c2_range_lookback_bars is not None else 'NONE'}")
    print(f"C2 max range width ATR: {preset.c2_max_range_width_atr if preset.c2_max_range_width_atr is not None else 'NONE'}")
    print(f"C2 BUY JST hours: {preset.c2_buy_jst_hours or 'NONE'}")
    print(f"C2 SELL JST hours: {preset.c2_sell_jst_hours or 'NONE'}")
    print(f"C2 disable BUY: {preset.c2_disable_buy}")
    print(f"C2 disable SELL: {preset.c2_disable_sell}")
    print(f"server_timezone: {preset.server_timezone}")
    print(f"server_utc_offset: {preset.server_utc_offset}")
    print(f"use_fixed_offset: {preset.use_fixed_offset}")
    print("=" * 120)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a named backtest preset.")
    parser.add_argument("--preset", type=str, default="gold_abc_v2", help="Preset name. Default: gold_abc_v2")
    parser.add_argument("--data-dir", type=Path, default=None, help="Optional raw data folder. Example: data/raw/xm_kiwami")
    parser.add_argument("--list", action="store_true", help="List available presets and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated command without running it.")
    parser.add_argument("--save", action="store_true", help="Forward --save to the underlying backtest script.")
    args = parser.parse_args()

    if args.list:
        print("Available presets:")
        for name in list_preset_names():
            print(f"  {name}")
        return 0

    print_preset_details(args.preset)
    command = build_combined_backtest_command(args.preset, save=args.save, data_dir=args.data_dir)

    print("Generated command:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))

    if args.dry_run:
        return 0

    print("\nRunning preset backtest...")
    completed = subprocess.run(command, cwd=PROJECT_ROOT)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
