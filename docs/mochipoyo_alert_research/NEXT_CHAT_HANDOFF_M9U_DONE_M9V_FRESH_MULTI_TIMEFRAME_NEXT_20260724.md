# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9U DONE / M9V NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This is the current restart point if the conversation reaches its length limit.

---

## 1. User objective

Final goal is NOT exact Mochipoyo reproduction.

Target:

- robust trading edge,
- high win rate when possible,
- PF materially above 1 after realistic costs,
- lower DD / loss tails,
- better reward-risk,
- useful portfolio-level frequency,
- GOLD M5/M15/H1/H4 and later BTC as separate branches.

Critical user decision:

A single timeframe does not need high frequency. Because multiple timeframes and BTC can provide breadth, each branch may be stricter and quality should be prioritized.

---

## 2. Absolute contracts

Audit-only remains ON.

Keep OFF/FALSE:

- discord_send
- mt5_order
- live_ready
- final_signal
- entry_gate_enabled

Never:

- use future bars/outcomes in candidate construction,
- use unconfirmed OHLC when closed bars are required,
- change M7C formulas/thresholds,
- reset M7C runtime manifest,
- stop/reset M8C,
- reset/reuse M8C prospective start,
- backfill a new prospective shadow,
- claim commission/swap modeled when not,
- treat historical proxy as genuine source truth,
- transplant GOLD rules to BTC,
- sum overlapping timeframe signals as independent positions,
- pyramid overlapping M5/M15/H1/H4 LONG signals by default.

Time basis = MT5 server time.

---

## 3. User operating preferences

- User does not run Python directly.
- Use numbered BATs only at meaningful local/prospective checkpoints.
- Do not request BAT execution for every exploration.
- Assistant-side historical exploration/self-verification is preferred.
- User dislikes guessing; use exact files/rules/metrics/commits.
- Keep handoff current before fragile work.

GOLD historical files folder:

`MT5 Files\gold_v3_2023_2026\`

Live GOLD file map:

- M1 `goldsharp_m1.csv`
- M5 `goldsharp_m5.csv`
- M15 `goldsharp_m15.csv`
- H1 `goldsharp_h1.csv`
- H4 `goldsharp_h4.csv`
- D1 `goldsharp_d1.csv`

No comparable BTC 2023-2026 historical set has been supplied.

---

## 4. M7C — frozen / do not change

M15 source-proxy formula:

- PRIMARY_LONG = IDLE AND rci9_turn_up AND BULLISH_STACK
- PRIMARY_SHORT = IDLE AND rci9_turn_down AND BEARISH_STACK
- LONG_EXIT = ACTIVE_LONG AND rci9 >= 78.333333333333
- SHORT_EXIT = ACTIVE_SHORT AND rci9 <= -75
- REENTRY not modeled/scored

M7C prospective start:

`2026-07-20T14:54:15Z`

Do not reset.

---

## 5. M8C — still running / never reset

BTC forward CONTROL/CHALLENGER continues:

- CONTROL accepts future proxy PRIMARY
- CHALLENGER rejects BTCUSD PRIMARY_LONG on proxy branch only
- genuine source anchor separate/unsuppressed

Keep M8C/M7C/collector running unchanged.

Persistent M8C BAT:

`scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat`

Do not reuse M8C start for GOLD.

---

## 6. BTC state

Corrected genuine source M9I2 replaced invalid old M9B timing.

M9J entry-RCI mining failed.
M9K BTC LONG tail state was descriptive but not stable enough for historical promotion.

BTC remains separate; no GOLD rule transfer.
Continue genuine source + M7C + M8C forward evidence.

---

## 7. M15 canonical branch — M9P PASS

Canonical N3:

N1: latest fully closed M5 tick_volume_ratio20 <= trailing200 q50.

N2: latest fully closed M15 MACD(6,13) line bps >= trailing200 q75.

N3 = N1 OR N2.

M9P deterministic local PASS:

- 1495
- ~35.6/month historical average
- WR 62.27%
- PF 1.3659
- avg win +17.20bps
- avg loss -20.87bps
- DD 510.5bps
- streak 11

72/72 nearby W/q combinations retained PF>1 every year and aggregate PF>1 after extra 2bps/trade stress.

---

## 8. M9Q / M9R — M15 risk-reward ideas retained but not started

N6 H4 RCI9 percentile risk band >0.25 and <=0.50 was historically weak.

Q1: N6 half-risk accounting.
Q2: selective 50% runner when H1 MACD rising at original exit.
Q3: combined.

Historical exploratory Q3:

- PF 1.4703
- DD 418.2bps
- avg positive +17.64bps
- avg negative -17.26bps

All exposed history; no promotion.

M9R four-arm fresh M15 design remains frozen NOT STARTED:

- R0 base
- R1 half-risk
- R2 runner
- R3 combined

Do not mix M9R into the first multi-timeframe forward comparison. First isolate value of branch breadth.

---

## 9. M9T branch robustness — DONE

Formal result:

`config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`

### S1 M5

Canonical historical:

- 1256
- WR 65.45%
- PF 1.3337
- DD 335.3bps

729 nearby combinations:

- all aggregate PF>1
- 408/729 all-year PF>1
- only 4/729 aggregate PF>1 after extra 2bps
- canonical extra-2bps PF ~0.9568

Decision: auxiliary/cost-sensitive. Do not use M5 frequency to justify weak trades.

### S2 M15

Canonical M9P N3. Primary reproducible branch.

### S3 H1

Definition:

- closed H4 MACD bps >= trailing100 q75
- closed D1 MACD bps >= trailing100 q50

Canonical:

- 191
- ~4.55/month historical average
- WR 71.20%
- PF 1.7802
- DD 532.3bps

Stress 81 nearby combinations:

- 81/81 PF>1 in every available calendar year
- 81/81 aggregate PF>1 after extra 2bps
- PF range ~1.57-2.63
- extra2bps PF range ~1.43-2.34
- minimum calendar-year PF across grid ~1.09

Decision: highest-priority new branch for fresh prospective evidence.

### S4 H4

Definition:

- closed D1 RCI9 >= trailing100 median
- D1 EMA20>EMA30>EMA40

Canonical:

- 70
- WR 72.86%
- PF 3.2956

Stress 9 nearby definitions:

- 9/9 aggregate survives extra 2bps
- only 4/9 all-year PF>1

Decision: premium/reference only; sample small.

---

## 10. M9T causal portfolio reference

One-position historical reference:

- sort S1/S2/S3/S4 chronologically
- flat => first qualifying LONG opens one virtual position
- active => later LONG candidates are confirmation metadata only
- simultaneous priority H4 > H1 > M15 > M5
- accepted trade uses its own branch proxy exit
- no future event decides initial entry

Result:

- 2241 accepted trades
- ~53.36/month historical average
- WR 63.23%
- PF 1.4447
- net 7515.3bps
- avg win +17.23bps
- avg loss -20.54bps
- DD 535.4bps
- streak 8
- <=-100bps tail ~1.16%

Year PF:

- 2023 1.3191
- 2024 1.5245
- 2025 1.3616
- 2026-to-Jun19 1.5965

13/14 quarters PF>1.
Remaining weakness: 2025Q3 PF ~0.804.

Extra cost:

- +1bps PF 1.2967
- +2bps PF 1.1617
- +3bps PF 1.0400

Accepted branch contribution:

- M15 1104
- M5 952
- H1 139
- H4 46

---

## 11. Agreement count is NOT a generic confidence score

M9T checked causal prior sequence.

Examples:

- M15 after prior M5 <=60m PF ~1.84
- H1 after prior M5 <=4h PF ~4.21
- H1 after prior M15 <=4h PF ~0.90
- M5 after prior H1 <=4h PF ~2.32
- M5 after prior H4 <=4h PF ~0.65

So order/market phase matters.

Do not implement "more timeframes agree = higher score".
Store ordered causal sequence/time gaps as metadata first.

---

## 12. M9U — deterministic reproduction DONE

Implementation:

`scripts/mochipoyo_alert_research/m9u/python/run_multitimeframe_portfolio_reproduction_audit.py`

Formal result:

`config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`

Assistant self-executed on the same hashed six GOLD CSVs.

PASS exact M9T reference:

- S1=1256
- S2=1495
- S3=191
- S4=70
- portfolio=2241
- portfolio PF=1.444651452178

This means the multi-timeframe historical design is now deterministic/reproducible, not just notebook exploration.

Still NOT independent validation or live.

---

## 13. M9V fresh prospective design — FROZEN, NOT STARTED

Contract:

`config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`

Purpose: isolate forward value of adding timeframe breadth before mixing risk/reward overlays.

Arms:

### V0 M15_ONLY

Eligible: S2 canonical M15 N3 only.

### V1 M15_PLUS_H1

Eligible: S2 + S3.

### V2 ALL_TIMEFRAMES

Eligible: S1 + S2 + S3 + S4.

Every arm is one-position GOLD LONG only.

While active, later eligible branch events become ordered confirmation metadata, not extra positions.

No M9R runner/half-risk in M9V.

Fresh start rules:

- NEW GOLD-specific start required
- never reuse M7C/M8C starts
- no backfill
- pre-start PRIMARY may NOT become prospective candidate
- pre-start closed bars may rehydrate state only
- if state is ACTIVE because of a pre-start PRIMARY, wait for its exit/IDLE before a new post-start PRIMARY becomes eligible
- immutable runtime manifest/start receipt before prospective rows are accepted

Review checkpoints:

- operational: 20 accepted arm events
- interim: 60
- minimum H1 branch review: 10 S3 candidates
- formal portfolio review: 120 accepted arm events

These are review checkpoints, not statistical guarantees.

---

## 14. Current state / next action

Read after this handoff:

1. `config/mochipoyo_alert_research/current_state_20260723.json`
2. `config/mochipoyo_alert_research/next_action_20260723.json`
3. `config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`
4. `config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`
5. `config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`
6. `config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json`

Preserve M7C/M8C contracts and starts.

---

## 15. Next stage

`M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW_IMPLEMENTATION`

Do next:

1. Implement live audit-only engine on `goldsharp_m1/m5/m15/h1/h4/d1.csv`.
2. Closed bars only, MT5 server time.
3. Independent M7C-style state per signal timeframe M5/M15/H1/H4.
4. First-turn must match frozen historical contract.
5. Only post-start PRIMARY is eligible for M9V candidate accounting.
6. State rehydration before start is allowed, candidate backfill is forbidden.
7. Implement V0/V1/V2 arms with independent one-position state.
8. Later candidate while active = ordered confirmation metadata only.
9. No pyramiding, no generic agreement score.
10. Create fail-closed runtime initializer/start receipt.
11. Self-verify bootstrap/start semantics before creating numbered BATs.
12. Only after implementation is ready ask user for BAT.
13. Keep M8C/M7C/collector running throughout.
14. Do not start M9R yet.
15. BTC remains separate.

---

## 16. Always-ready next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初にGitHubの次を順番どおり必ず読んでください。

1.
docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9U_DONE_M9V_FRESH_MULTI_TIMEFRAME_NEXT_20260724.md

2.
config/mochipoyo_alert_research/current_state_20260723.json

3.
config/mochipoyo_alert_research/next_action_20260723.json

4.
config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json

5.
config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json

6.
config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json

現在audit-onlyです。
M8C/M7C/genuine source collectorは継続中です。停止・reset・prospective start変更・backfillは禁止です。

M9UでGOLD M5/M15/H1/H4の決定論的再現がPASSしました。S1=1256、S2=1495、S3=191、S4=70、因果的1ポジションportfolio=2241、PF1.444651452178でM9Tと一致しています。

H1 S3は81/81近傍定義で全4年PF>1かつ追加2bps耐性があり、最高優先の新枝です。
M5 S1はコスト感度が高いので補助です。
H4 S4は小標本premiumです。
M15 S2=N3は主軸です。

単純な複数時間足一致数をconfidenceにしないでください。順序で成績が逆転するためordered causal sequenceとして記録します。

M9V fresh prospective designは凍結済みですが未開始です。
V0=M15のみ、V1=M15+H1、V2=全時間足を、各arm一ポジションで比較します。
M9RのN6半リスク/runnerはM9Vには混ぜません。

次はM9V live audit-only implementation / fresh-start initializerを作り、自己検証後にだけユーザーへ番号付きBATを依頼してください。

ユーザーはPythonを直接実行しません。
わからないことを憶測で実装しないでください。ただしhandoffに答えがあることを再質問しないでください。
```

---

## 17. Handoff maintenance

When M9V implementation/start materially changes state, start receipts, BATs, metrics or next action, create/update the next handoff immediately.
