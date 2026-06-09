#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixed runner for GOLD V3 16 all replay result review.

The original Stage 16 module creates the normal READY summary with explicit
safety keys such as final_candidate_approval=False and also expands
FALSE_FLAGS, which contains the same keys. Python rejects duplicate keyword
arguments in dict(..., **FALSE_FLAGS).

This runner removes only those duplicate keys from FALSE_FLAGS before
executing the original module. The original summary still writes the explicit
safety flags as false.
"""

from __future__ import annotations

import sys

import gold_v3_16_all_replay_result_review_and_narrowing_audit_only as stage16

_DUPLICATE_READY_SUMMARY_KEYS = {
    "final_candidate_approval",
    "threshold_finalization",
    "model_training",
    "signals_generated",
    "zip_output_created",
}

stage16.FALSE_FLAGS = {
    k: v for k, v in stage16.FALSE_FLAGS.items()
    if k not in _DUPLICATE_READY_SUMMARY_KEYS
}

if __name__ == "__main__":
    raise SystemExit(stage16.main(sys.argv[1:]))
