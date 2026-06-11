# GOLD V3 Stage106 — Independent High-Vol SHORT Proxy Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_AUDIT_ONLY`

READY status:

`GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY`

## Purpose

Stage105 evaluated true high-vol rows as LONG and produced zero wins in the recent window.

Stage106 evaluates the same independent high-vol universe as SHORT:

```text
entry = close
TP = entry - tp_usd
SL = entry + sl_usd
```

This checks whether recent high-vol rows are downward high-vol conditions that require SELL-side logic rather than LONG-side logic.

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, candidate pool mutation, or manual candidate demotion/removal.
