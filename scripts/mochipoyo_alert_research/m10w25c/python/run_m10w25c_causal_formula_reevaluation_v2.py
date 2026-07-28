from __future__ import annotations

import run_m10w25c_causal_formula_reevaluation as implementation

# M10W23 frozen MVI1 has exactly three conditions. The prior wrapper's extra
# m1_ret5_bps condition was set-redundant on both frozen cohorts, but it is not
# part of the preregistered formula and therefore must not remain in execution.
implementation.FAMILIES["MVI1_LONG_M5_VOLUME_IMPULSE"] = lambda row: (
    float(row["m5_tick_volume_ratio20"]) >= 1.0
    and float(row["m5_body_ratio"]) >= 0.5
    and float(row["m5_close_location"]) >= (2.0 / 3.0)
)

_original_main = implementation.main


def main() -> int:
    result = _original_main()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
