from __future__ import annotations

import run_genuine_source_vs_proxy_gap_audit as audit

# M9I's frozen contract compares M5/M15/H1/H4 decision context.  The reusable
# M9E helper normally also iterates M1, so scope it explicitly to M9I's frozen
# timeframes before running.  This changes no M7C formula, threshold, source
# event, proxy event, or outcome; it only keeps the divergence helper inside
# the M9I feature contract.
audit.m9e.TIMEFRAMES = audit.FEATURE_TIMEFRAMES

if __name__ == "__main__":
    raise SystemExit(audit.main())
