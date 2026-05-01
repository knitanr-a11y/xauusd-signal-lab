from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestPreset:
    """Reusable backtest preset.

    Presets are intentionally explicit so the same settings can later be reused by:
        - backtest scripts
        - live signal scanner
        - Discord notification process
        - AI evaluation prompt builder
    """

    name: str
    description: str
    symbols: str
    models: str
    near_atr: float
    close_tolerance_atr: float
    swing_left: int
    swing_right: int
    recent_pullback_bars: int
    rr: float
    sl_buffer_atr: float
    a_buy_jst_hours: str
    a_sell_jst_hours: str
    b_buy_jst_hours: str
    b_sell_jst_hours: str
    server_timezone: str = "Europe/Athens"
    server_utc_offset: int = 3
    use_fixed_offset: bool = False
    no_ema20_reclaim: bool = False
    no_macd_signal_alignment: bool = False
    no_histogram_acceleration: bool = False
    same_bar_win: bool = False
    max_bars_in_trade: int | None = None
    a_exclude_hidden_price_delta_atr_lte: float | None = None
    b_exclude_risk_atr_range: str | None = None
    b_exclude_macd_hist_delta_abs_range: str | None = None


PRESETS: dict[str, BacktestPreset] = {
    "gold_ab_v1": BacktestPreset(
        name="gold_ab_v1",
        description=(
            "GOLD A+B baseline. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Uses JST side/model specific time filters, RR 1.5, SL buffer ATR 0.05."
        ),
        symbols="gold",
        models="A,B",
        near_atr=0.30,
        close_tolerance_atr=0.50,
        swing_left=3,
        swing_right=2,
        recent_pullback_bars=6,
        rr=1.5,
        sl_buffer_atr=0.05,
        a_buy_jst_hours="7,13",
        a_sell_jst_hours="2,13,19",
        b_buy_jst_hours="20,21,22,23",
        b_sell_jst_hours="10",
    ),
    "gold_ab_v2": BacktestPreset(
        name="gold_ab_v2",
        description=(
            "Current GOLD main candidate after B-signal quality filtering. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Compared with v1, excludes weak B risk/ATR and MACD histogram acceleration bands. "
            "Filter ranges use the narrower robustness-tested values."
        ),
        symbols="gold",
        models="A,B",
        near_atr=0.30,
        close_tolerance_atr=0.50,
        swing_left=3,
        swing_right=2,
        recent_pullback_bars=6,
        rr=1.5,
        sl_buffer_atr=0.05,
        a_buy_jst_hours="7,13",
        a_sell_jst_hours="2,13,19",
        b_buy_jst_hours="20,21,22,23",
        b_sell_jst_hours="10",
        b_exclude_risk_atr_range="2.00,2.40",
        b_exclude_macd_hist_delta_abs_range="0.40,0.60",
    ),
    "gold_ab_v3": BacktestPreset(
        name="gold_ab_v3",
        description=(
            "GOLD A+B main candidate after A-signal quality filtering. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Compared with v2, excludes weak A hidden-price-delta/ATR signals while keeping B v2 filters."
        ),
        symbols="gold",
        models="A,B",
        near_atr=0.30,
        close_tolerance_atr=0.50,
        swing_left=3,
        swing_right=2,
        recent_pullback_bars=6,
        rr=1.5,
        sl_buffer_atr=0.05,
        a_buy_jst_hours="7,13",
        a_sell_jst_hours="2,13,19",
        a_exclude_hidden_price_delta_atr_lte=0.271,
        b_buy_jst_hours="20,21,22,23",
        b_sell_jst_hours="10",
        b_exclude_risk_atr_range="2.00,2.40",
        b_exclude_macd_hist_delta_abs_range="0.40,0.60",
    ),
}


def list_preset_names() -> list[str]:
    return sorted(PRESETS.keys())


def get_preset(name: str) -> BacktestPreset:
    key = name.strip().lower()
    if key not in PRESETS:
        available = ", ".join(list_preset_names())
        raise ValueError(f"Unknown preset: {name}. Available presets: {available}")
    return PRESETS[key]
