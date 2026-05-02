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
    b_buy_exclude_risk_atr_range: str | None = None
    b_buy_exclude_risk_atr_macd_hist_delta_abs_combo: str | None = None
    c_breakout_lookback_bars: int | None = None
    c_buy_jst_hours: str | None = None
    c_sell_jst_hours: str | None = None
    c_buy_h1_ema_gap_atr_max: float | None = None
    c2_range_lookback_bars: int | None = None
    c2_max_range_width_atr: float | None = None
    c2_min_breakout_atr: float | None = None
    c2_max_breakout_atr: float | None = None
    c2_buy_jst_hours: str | None = None
    c2_sell_jst_hours: str | None = None
    c2_disable_buy: bool = True
    c2_disable_sell: bool = False


def _gold_abc_v2_kwargs(symbols: str, description: str, c_buy_jst_hours: str = "1,5,11,12,15,18,21,22") -> dict[str, object]:
    return dict(
        description=description,
        symbols=symbols,
        models="A,B,C,C2",
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
        b_buy_exclude_risk_atr_range="0.928,1.241",
        b_buy_exclude_risk_atr_macd_hist_delta_abs_combo="1.241,2.40,0.375,0.742",
        c_breakout_lookback_bars=12,
        c_buy_jst_hours=c_buy_jst_hours,
        c_sell_jst_hours="",
        c_buy_h1_ema_gap_atr_max=3.623,
        c2_range_lookback_bars=12,
        c2_max_range_width_atr=2.50,
        c2_min_breakout_atr=0.0,
        c2_max_breakout_atr=None,
        c2_buy_jst_hours="",
        c2_sell_jst_hours="11,14,17",
        c2_disable_buy=True,
        c2_disable_sell=False,
    )


PRESETS: dict[str, BacktestPreset] = {
    "gold_ab_v1": BacktestPreset(
        name="gold_ab_v1",
        description=(
            "GOLD/XAUUSD A+B baseline. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Uses JST side/model specific time filters, RR 1.5, SL buffer ATR 0.05."
        ),
        symbols="xauusd",
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
            "GOLD/XAUUSD main candidate after B-signal quality filtering. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Compared with v1, excludes weak B risk/ATR and MACD histogram acceleration bands. "
            "Filter ranges use the narrower robustness-tested values."
        ),
        symbols="xauusd",
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
            "GOLD/XAUUSD A+B main candidate after A-signal quality filtering. "
            "A=hidden divergence, B=EMA20 reclaim + MACD reacceleration. "
            "Compared with v2, excludes weak A hidden-price-delta/ATR signals while keeping B v2 filters."
        ),
        symbols="xauusd",
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
    "gold_ab_v4": BacktestPreset(
        name="gold_ab_v4",
        description=(
            "GOLD/XAUUSD A+B main candidate after A filter and B BUY quality filtering. "
            "Compared with v3, excludes weak B BUY risk/MACD combinations while keeping A v3 and B v2 filters. "
            "This is the frozen AB baseline for C-signal research."
        ),
        symbols="xauusd",
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
        b_buy_exclude_risk_atr_range="0.928,1.241",
        b_buy_exclude_risk_atr_macd_hist_delta_abs_combo="1.241,2.40,0.375,0.742",
    ),
    "gold_abc_v1": BacktestPreset(
        name="gold_abc_v1",
        **_gold_abc_v2_kwargs(
            symbols="xauusd",
            description=(
                "GOLD/XAUUSD A+B+C candidate. "
                "AB uses frozen gold_ab_v4. "
                "C=H1-aligned M15 breakout-continuation BUY only, signal hours 1,5,11,12,15,18,21,22, "
                "with H1 EMA gap <= 3.623 ATR. C SELL remains disabled."
            ),
        ),
    ),
    "gold_abc_v2": BacktestPreset(
        name="gold_abc_v2",
        **_gold_abc_v2_kwargs(
            symbols="xauusd",
            description=(
                "GOLD/XAUUSD A+B+C+C2 candidate. "
                "gold_abc_v1 plus C2 SELL range-compression breakout at signal JST hours 11,14,17. "
                "C2 BUY remains disabled."
            ),
        ),
    ),
    "xm_kiwami_gold_abc_v2": BacktestPreset(
        name="xm_kiwami_gold_abc_v2",
        **_gold_abc_v2_kwargs(
            symbols="goldsharp",
            description=(
                "XM KIWAMI GOLD# A+B+C+C2 candidate. "
                "Logic is copied from gold_abc_v2, but symbols uses local CSV base name goldsharp. "
                "Use with --data-dir data/raw/xm_kiwami."
            ),
        ),
    ),
    "xm_kiwami_gold_abc_v3": BacktestPreset(
        name="xm_kiwami_gold_abc_v3",
        **_gold_abc_v2_kwargs(
            symbols="goldsharp",
            c_buy_jst_hours="1,5,11,12,15,18",
            description=(
                "XM KIWAMI GOLD# A+B+C+C2 comparison preset. "
                "Based on xm_kiwami_gold_abc_v2, but removes C BUY signal JST hours 21 and 22. "
                "This tests the weak C entries observed around JST 21-22 entry hours."
            ),
        ),
    ),
    "xm_kiwami_gold_abc_v4": BacktestPreset(
        name="xm_kiwami_gold_abc_v4",
        **_gold_abc_v2_kwargs(
            symbols="goldsharp",
            c_buy_jst_hours="1,5,11,15,18",
            description=(
                "XM KIWAMI GOLD# A+B+C+C2 comparison preset. "
                "Based on xm_kiwami_gold_abc_v3, and additionally removes C BUY signal JST hour 12. "
                "This is a stricter C-hour filter test; use only if v3 is still unstable."
            ),
        ),
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
