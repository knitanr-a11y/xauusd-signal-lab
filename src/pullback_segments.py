from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SegmentSettings:
    max_gap_bars: int = 1
    min_segment_bars: int = 1

    def validate(self) -> None:
        if self.max_gap_bars < 0:
            raise ValueError(f"max_gap_bars must be >= 0: {self.max_gap_bars}")
        if self.min_segment_bars <= 0:
            raise ValueError(f"min_segment_bars must be positive: {self.min_segment_bars}")


def _finalize_segment(
    *,
    df: pd.DataFrame,
    side: str,
    segment_id: int,
    start_index: int,
    end_index: int,
    signal_index: int,
    rows: list[dict[str, object]],
) -> None:
    segment = df.iloc[start_index : end_index + 1]
    signal_row = df.iloc[signal_index]

    if side == "BUY":
        extreme_offset = int(segment["low"].astype(float).idxmin())
        extreme_price = float(df.at[extreme_offset, "low"])
    elif side == "SELL":
        extreme_offset = int(segment["high"].astype(float).idxmax())
        extreme_price = float(df.at[extreme_offset, "high"])
    else:
        raise ValueError(f"Unsupported segment side: {side}")

    extreme_macd = df.at[extreme_offset, "macd_line"] if "macd_line" in df.columns else pd.NA

    rows.append(
        {
            "segment_id": segment_id,
            "side": side,
            "segment_start_index": start_index,
            "segment_end_index": end_index,
            "segment_signal_index": signal_index,
            "segment_start_time": df.at[start_index, "time"],
            "segment_end_time": df.at[end_index, "time"],
            "segment_signal_time": signal_row["time"],
            "segment_bars": end_index - start_index + 1,
            "extreme_index": extreme_offset,
            "extreme_time": df.at[extreme_offset, "time"],
            "extreme_price": extreme_price,
            "extreme_macd": extreme_macd,
            "h1_time": signal_row.get("h1_time", pd.NaT),
            "h1_trend": signal_row.get("h1_trend", ""),
            "signal_close": signal_row.get("close", pd.NA),
            "signal_ema_20": signal_row.get("ema_20", pd.NA),
            "signal_atr_14": signal_row.get("atr_14", pd.NA),
            "last_confirmed_swing_low_time": signal_row.get("last_confirmed_swing_low_time", pd.NaT),
            "last_confirmed_swing_low_price": signal_row.get("last_confirmed_swing_low_price", pd.NA),
            "last_confirmed_swing_low_macd": signal_row.get("last_confirmed_swing_low_macd", pd.NA),
            "last_confirmed_swing_high_time": signal_row.get("last_confirmed_swing_high_time", pd.NaT),
            "last_confirmed_swing_high_price": signal_row.get("last_confirmed_swing_high_price", pd.NA),
            "last_confirmed_swing_high_macd": signal_row.get("last_confirmed_swing_high_macd", pd.NA),
        }
    )


def build_pullback_segments(
    df: pd.DataFrame,
    max_gap_bars: int = 1,
    min_segment_bars: int = 1,
) -> pd.DataFrame:
    """Build BUY/SELL pullback segments from bar-level pullback candidates.

    Why this exists:
        The first prototype marks each M15 candle as a pullback candidate.
        That can produce repeated signals inside the same pullback.

    This function groups nearby candidate bars into one segment.

    Timing rule:
        A segment signal is placed on the first non-candidate bar after the segment.
        Therefore a strategy can enter on the next bar after `segment_signal_time`,
        just like the existing bar-level signal uses next bar open.

    Parameters:
        max_gap_bars:
            Allows small holes inside a pullback. Example: max_gap_bars=1 means
            BUY candidate, non-candidate, BUY candidate can still be one segment.

        min_segment_bars:
            Minimum number of bars from start to end, including small allowed gaps.
    """
    settings = SegmentSettings(max_gap_bars=max_gap_bars, min_segment_bars=min_segment_bars)
    settings.validate()

    required = [
        "time",
        "high",
        "low",
        "close",
        "buy_pullback_candidate",
        "sell_pullback_candidate",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required pullback segment columns: {missing}")

    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    rows: list[dict[str, object]] = []
    segment_id = 1

    for side, candidate_col in [("BUY", "buy_pullback_candidate"), ("SELL", "sell_pullback_candidate")]:
        in_segment = False
        start_index = -1
        last_candidate_index = -1
        gap_count = 0

        for i, is_candidate in enumerate(out[candidate_col].astype(bool).tolist()):
            if is_candidate:
                if not in_segment:
                    in_segment = True
                    start_index = i
                    last_candidate_index = i
                    gap_count = 0
                else:
                    last_candidate_index = i
                    gap_count = 0
                continue

            if not in_segment:
                continue

            gap_count += 1
            if gap_count <= settings.max_gap_bars:
                continue

            # Segment ended at the last real candidate, not at the gap bar.
            end_index = last_candidate_index
            signal_index = i
            segment_bars = end_index - start_index + 1
            if segment_bars >= settings.min_segment_bars and signal_index < len(out):
                _finalize_segment(
                    df=out,
                    side=side,
                    segment_id=segment_id,
                    start_index=start_index,
                    end_index=end_index,
                    signal_index=signal_index,
                    rows=rows,
                )
                segment_id += 1

            in_segment = False
            start_index = -1
            last_candidate_index = -1
            gap_count = 0

        # Do not finalize an open-ended segment at the dataset end.
        # In live trading, a segment is not finished until a non-candidate bar confirms it.

    if not rows:
        return pd.DataFrame(
            columns=[
                "segment_id",
                "side",
                "segment_start_index",
                "segment_end_index",
                "segment_signal_index",
                "segment_start_time",
                "segment_end_time",
                "segment_signal_time",
                "segment_bars",
                "extreme_index",
                "extreme_time",
                "extreme_price",
                "extreme_macd",
            ]
        )

    segments = pd.DataFrame(rows).sort_values(["segment_signal_time", "side"], kind="mergesort").reset_index(drop=True)
    return segments


def add_hidden_divergence_to_segments(segments: pd.DataFrame) -> pd.DataFrame:
    """Add hidden divergence flags to pullback segments.

    BUY segment:
        segment low > previous confirmed swing low
        segment MACD at low < MACD at previous confirmed swing low

    SELL segment:
        segment high < previous confirmed swing high
        segment MACD at high > MACD at previous confirmed swing high
    """
    if segments.empty:
        out = segments.copy()
        out["hidden_bullish_divergence"] = pd.Series(dtype=bool)
        out["hidden_bearish_divergence"] = pd.Series(dtype=bool)
        out["hidden_divergence"] = pd.Series(dtype=bool)
        return out

    required = [
        "side",
        "extreme_price",
        "extreme_macd",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_macd",
    ]
    missing = [col for col in required if col not in segments.columns]
    if missing:
        raise ValueError(f"Missing required segment divergence columns: {missing}")

    out = segments.copy()

    out["hidden_bullish_divergence"] = (
        out["side"].eq("BUY")
        & out["extreme_price"].notna()
        & out["extreme_macd"].notna()
        & out["last_confirmed_swing_low_price"].notna()
        & out["last_confirmed_swing_low_macd"].notna()
        & (out["extreme_price"] > out["last_confirmed_swing_low_price"])
        & (out["extreme_macd"] < out["last_confirmed_swing_low_macd"])
    )

    out["hidden_bearish_divergence"] = (
        out["side"].eq("SELL")
        & out["extreme_price"].notna()
        & out["extreme_macd"].notna()
        & out["last_confirmed_swing_high_price"].notna()
        & out["last_confirmed_swing_high_macd"].notna()
        & (out["extreme_price"] < out["last_confirmed_swing_high_price"])
        & (out["extreme_macd"] > out["last_confirmed_swing_high_macd"])
    )

    out["hidden_divergence"] = out["hidden_bullish_divergence"] | out["hidden_bearish_divergence"]

    out["bullish_hidden_price_delta"] = out["extreme_price"] - out["last_confirmed_swing_low_price"]
    out["bullish_hidden_macd_delta"] = out["last_confirmed_swing_low_macd"] - out["extreme_macd"]
    out["bearish_hidden_price_delta"] = out["last_confirmed_swing_high_price"] - out["extreme_price"]
    out["bearish_hidden_macd_delta"] = out["extreme_macd"] - out["last_confirmed_swing_high_macd"]

    return out


def segment_summary(segments: pd.DataFrame) -> dict[str, object]:
    if segments.empty:
        return {
            "segments": 0,
            "buy_segments": 0,
            "sell_segments": 0,
            "hidden_bullish_segments": 0,
            "hidden_bearish_segments": 0,
        }

    return {
        "segments": int(len(segments)),
        "buy_segments": int(segments["side"].eq("BUY").sum()),
        "sell_segments": int(segments["side"].eq("SELL").sum()),
        "hidden_bullish_segments": int(segments.get("hidden_bullish_divergence", pd.Series(False, index=segments.index)).sum()),
        "hidden_bearish_segments": int(segments.get("hidden_bearish_divergence", pd.Series(False, index=segments.index)).sum()),
    }
