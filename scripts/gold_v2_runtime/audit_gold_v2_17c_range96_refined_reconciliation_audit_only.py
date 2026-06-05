#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fail-safe placeholder for 17C RANGE96_REFINED reconciliation.

The full audit implementation was not installed in this commit. This script
intentionally exits non-zero so it cannot be mistaken for a completed audit.
"""
from __future__ import annotations
import json

payload = {
    "step": "17C_RANGE96_REFINED_RECONCILIATION_AUDIT_ONLY",
    "status": "NOT_IMPLEMENTED_FAIL_SAFE_PLACEHOLDER",
    "audit_only": True,
    "run_allowed": False,
    "reason": "Implementation is not present. Use the 17C specification document and do not treat this as a completed audit.",
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(2)
