#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin read-only entry point. No MT5 orders or Discord transmission."""
from gold_v3_289_audit_cycle import main
from gold_v3_289_candidates import dedupe_source_candidates, load_model_contracts
from gold_v3_289_state import empty_observation_ledger, evaluate_shadow_eligibility

if __name__ == "__main__":
    raise SystemExit(main())
