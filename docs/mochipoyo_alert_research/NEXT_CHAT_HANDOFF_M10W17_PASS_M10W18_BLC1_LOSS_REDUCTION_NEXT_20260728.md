# MOCHIPOYO Alert Research handoff — M10W17 PASS / M10W18 BLC1 loss reduction next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current direction

M10W16 did not produce a ROBUST/STRONG BLC1 family as-is. The user correctly asked whether BLC1 could improve by suppressing losing conditions rather than abandoning the whole family.

A post-hoc diagnostic joined the M10W16 resolved BLC1 ledger to the pre-existing M10W14 H1 ATR terciles. The HIGH_GE_0P67 BLC1 subset was weak overall and especially weak in 2025/2026, while the retained LOW+MID subset looked materially stronger. This is not clean validation and not an exact filtered portfolio because capacity was not rebuilt after exclusions.

M10W17 separately found stable unconditional LONG directional opportunity in both LOW and HIGH ATR bullish-aligned NEITHER buckets. Therefore do not conclude HIGH ATR is generically bad. The working hypothesis is a BLC1 trigger x HIGH-ATR interaction.

## M10W18

Stage:
`M10W18_BLC1_HIGH_ATR_LOSS_REDUCTION_CHALLENGER_AUDIT_ONLY`

Contract:
`config/mochipoyo_alert_research/m10w18_blc1_high_atr_loss_reduction_challenger_contract_20260728.json`

Operator:
`scripts/mochipoyo_alert_research/m10w18/bat/01_run_blc1_high_atr_loss_reduction_challenger.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W18/LATEST/99_UPLOAD_PACKAGE.zip`

Frozen challenger:
- keep exact BLC1 formula and 240-minute horizon
- compute causal H1 ATR14 percentile100 at decision
- accept only `h1_atr_pct100 < 0.67`
- exclude `>= 0.67` or unavailable
- 0.67 is the already outcome-blind M10W14 tercile boundary; no new numeric threshold search
- apply gate before one-position allocation, then rebuild exact M1 ledger so freed capacity is handled correctly

## Interpretation limits

This challenger was motivated after historical outcomes were seen. Therefore even an excellent M10W18 historical result is research-exposed and cannot by itself establish edge or change existing monitors. If materially improved, freeze the rule and create a brand-new independent fresh prospective shadow before support.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- existing monitors unchanged
- M10P/P2 BAT01 forbidden
- M10V forbidden before both SHORT families reach 20 resolved + integrity PASS
- no Discord send / MT5 order / live_ready / final_signal
