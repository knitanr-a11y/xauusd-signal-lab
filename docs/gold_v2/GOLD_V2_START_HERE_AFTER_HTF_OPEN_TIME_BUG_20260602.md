# GOLD V2 START HERE — HTF open-time bug reset

Created: 2026-06-02
Status: CANONICAL STARTING POINT for GOLD going forward

## 1. Why GOLD documents are reset

All prior GOLD/XAUUSD documents, handoff notes, postmortems, gate design notes, AI-tag notes, and DISC8 operational notes must be treated as **legacy forensic material only** unless they are explicitly revalidated under this GOLD V2 document set.

The reason is a critical timing bug risk:

- MT5-style candle timestamps are open times, not close times.
- A candle row timestamp such as `H1 09:00` represents the 09:00-10:00 candle, not a candle already closed at 09:00.
- A candle row timestamp such as `H4 08:00` represents the 08:00-12:00 candle.
- A candle row timestamp such as `D1 00:00` represents the current trading day candle.

Therefore, the following check is **not sufficient**:

```text
source_time <= entry_time
```

The correct no-future check is:

```text
H1 source_open_time + 1h <= M15 entry/eval time
H4 source_open_time + 4h <= M15 entry/eval time
D1 source_open_time + 1d <= M15 entry/eval time
```

Any document, script, CSV, ledger, or manifest that claims `close_time <= M15 close_time` must be re-audited if its source timestamp may actually be candle open time.

## 2. Legacy documents are not source of truth

Do not use prior GOLD documents as implementation truth for:

- live decision logic
- demo MT5 autotrading
- dispatch_ready rules
- DISC8 membership
- AI tag gate rules
- numeric gate rules
- reported win rate / PF / TotalR
- HTF no-future claims

They may be used only to understand history and to locate files for forensic audit.

## 3. Current known failures / unresolved items

### 3.1 HTF confirmation audit is invalid if timestamps are open time

A previous run metadata claimed:

```text
H1/H4/D1 features merged by close_time <= M15 close_time using merge_asof backward
h1_future_rows = 0
h4_future_rows = 0
d1_future_rows = 0
```

This is not enough if the stored H1/H4/D1 timestamp is the candle open time.

### 3.2 DISC set lineage is contaminated

The original high-performing recommended set was reported as:

```text
DISC_01, DISC_02, DISC_04, DISC_05, DISC_06, DISC_09, DISC_10, DISC_13
```

A later operational DISC8/AI review flow used a different set:

```text
DISC_01, DISC_02, DISC_04, DISC_05, DISC_06, DISC_08, DISC_09, DISC_11
```

This means DISC_10 and DISC_13 disappeared, and DISC_08 and DISC_11 entered before or during AI review / operational manifest preparation.

No further demo runtime connection should proceed until this lineage is repaired or a new V2 set is created from audited data.

## 4. GOLD V2 non-negotiable rules

### 4.1 Timestamp rule

All candles are treated as open-time rows unless proven otherwise.

### 4.2 HTF rule

For M15 evaluation at `eval_time`, HTF features may only use bars satisfying:

```text
h1_open_time + 1h <= eval_time
h4_open_time + 4h <= eval_time
d1_open_time + 1d <= eval_time
```

### 4.3 Entry rule

Preferred evaluation for static DISC-like signals:

```text
M15 signal bar closes first
entry_time = m15_open_time + 15 minutes
entry_price = M15 close
```

### 4.4 Outcome rule

Preferred outcome audit:

```text
M1 first-touch if available
M5 acceptable only for secondary compatibility audit
path starts strictly after entry_time
TP first = WIN
SL first = LOSS
same-bar TP/SL conflict = SL priority
unresolved handled explicitly, not silently discarded
```

### 4.5 Source of truth rule

Do not recreate conditions by approximation if a mined rule CSV or trade ledger exists.

However, any existing mined rule CSV or trade ledger must first pass open-time HTF confirmation audit.

### 4.6 Safety rule

Until GOLD V2 is rebuilt:

```text
OpenAI API: disabled for new scoring/review
Discord send: disabled for GOLD V2 autotrade
MT5 order_send: disabled for GOLD V2 autotrade
dispatch_ready: must remain false
runtime gate mutation: forbidden
SOT mutation: forbidden except explicitly versioned GOLD V2 rebuild outputs
```

## 5. Files uploaded in the reset discussion

These files are important forensic inputs, but not automatically trusted as implementation SOT until re-audited with open-time HTF logic:

```text
recommended8_static_rules.csv
static_rule_definitions.csv
static_rule_definitions.json
static_rule_strategy_summary.csv
static_rule_trade_ledger.csv
static_rule_grouped_trade_ledger.csv
static_rule_grouped_summary.csv
static_rule_grouped_monthly_summary.csv
static_rule_monthly_summary.csv
static_rule_component_ledger.csv
run_metadata.json
notification_alert_examples.csv
```

## 6. Next required work

Create a GOLD V2 audit that reads the static rule ledger and verifies, row by row:

```text
entry_time == m15_bar_open_time + 15 minutes
h1_source_open_time + 1h <= entry_time
h4_source_open_time + 4h <= entry_time
d1_source_open_time + 1d <= entry_time
M1 path starts after entry_time
```

Then produce:

```text
gold_v2_htf_open_time_audit_summary.json
gold_v2_htf_open_time_audit_by_strategy.csv
gold_v2_htf_open_time_audit_violations.csv
gold_v2_static_rule_revalidated_strategy_summary.csv
```

If violations are found, the old performance table must be considered invalid for live/demo use.

## 7. Current decision

Do not proceed with live decision audit hook or demo MT5 autotrading for GOLD until GOLD V2 audit outputs are created and reviewed.
