# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9V IMPLEMENTED / FRESH START INIT NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This is the current restart point if the conversation hits its length limit.

---

## 1. Actual user goal

Not exact Mochipoyo reproduction.

Build a robust multi-timeframe / multi-asset trading portfolio with:

- high win rate where possible,
- PF materially above 1 after realistic costs,
- lower DD and smaller loss tails,
- improved reward/risk,
- useful portfolio-level frequency,
- strict branch quality because breadth across GOLD M5/M15/H1/H4 and later BTC can supply frequency.

Do not protect one timeframe's trade count at the expense of quality.

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
- use unconfirmed OHLC where closed bars are required,
- change frozen M7C formulas/thresholds,
- reset M7C runtime manifest,
- stop/reset M8C,
- reset/reuse M8C prospective start,
- backfill a new prospective shadow,
- treat historical proxy events as genuine source truth,
- claim commission/swap modeled when not,
- transplant GOLD rules to BTC,
- pyramid overlapping M5/M15/H1/H4 LONG signals by default,
- use generic agreement count as an automatically positive confidence score.

Research/trading time basis = MT5 server time.

---

## 3. User operating preferences

- User does not run Python directly.
- Only numbered BATs when local execution is actually needed.
- Do not request a BAT for every exploration.
- Assistant-side exploration/self-verification preferred.
- Exact filenames/rules/metrics/commit state; do not guess.
- Maintain a current handoff before fragile/long work.

Local repo root:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\xauusd-signal-lab-clean\xauusd-signal-lab`

Live GOLD files are in MT5 Files root:

- M1 `goldsharp_m1.csv`
- M5 `goldsharp_m5.csv`
- M15 `goldsharp_m15.csv`
- H1 `goldsharp_h1.csv`
- H4 `goldsharp_h4.csv`
- D1 `goldsharp_d1.csv`

Historical GOLD folder:
`MT5 Files\gold_v3_2023_2026\`

No comparable BTC 2023-2026 historical dataset supplied.

---

## 4. M7C frozen state — never change/reset

M7C source-proxy formula M15:

- PRIMARY_LONG = IDLE AND rci9_turn_up AND BULLISH_STACK
- PRIMARY_SHORT = IDLE AND rci9_turn_down AND BEARISH_STACK
- LONG_EXIT = ACTIVE_LONG AND rci9 >= 78.333333333333
- SHORT_EXIT = ACTIVE_SHORT AND rci9 <= -75
- REENTRY not modeled/scored

M7C prospective start:
`2026-07-20T14:54:15Z`

Keep M7C running.

---

## 5. M8C still running — never reset

BTC CONTROL/CHALLENGER forward shadow remains:

- CONTROL accepts all future proxy PRIMARY
- CHALLENGER rejects BTCUSD PRIMARY_LONG on proxy branch only
- genuine source anchor remains separate/unsuppressed

Keep M8C / M7C / genuine source collector running unchanged.

M8C persistent BAT:
`scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat`

Never reuse M8C start for GOLD.

---

## 6. BTC current policy

Corrected M9I2 replaced invalid old M9B timing.
M9J entry-RCI mining failed.
M9K historical BTC LONG tail-state mining did not produce a stable promotable gate.

BTC remains a separate forward research family.
Do not transplant GOLD multi-timeframe rules into BTC.

---

## 7. M15 canonical N3 — M9P deterministic PASS

N1:
latest fully closed M5 tick_volume_ratio20 <= trailing200 q50.

N2:
latest fully closed M15 MACD(6,13) line bps >= trailing200 q75.

N3 = N1 OR N2.

M9P:

- 1495 historical/reference trades
- ~35.6/month
- WR 62.27%
- PF 1.3659
- avg win +17.20bps
- avg loss -20.87bps
- DD 510.5bps
- streak 11

72/72 nearby W/q combinations retained PF>1 each year and aggregate PF>1 after extra2bps/trade stress.

---

## 8. M9Q/M9R risk-reward work — keep frozen, do NOT start yet

N6 H4 RCI9 percentile risk band was historically weak.

Exploratory:

- Q1 N6 0.50x virtual size
- Q2 selective half-runner when H1 MACD still rising at original exit
- Q3 combined

Historical exposed Q3:

- PF1.4703
- DD418.2bps
- avg positive +17.64bps
- avg negative -17.26bps

M9R four-arm fresh design is frozen but NOT STARTED.
Do not mix M9R into initial multi-timeframe M9V forward test because runner changes holding duration and would confound branch-breadth comparison.

---

## 9. M9T multi-timeframe robustness

Formal result:
`config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`

### S1 M5

Canonical:
- n1256
- WR65.45%
- PF1.3337
- DD335.3bps

Stress729 nearby definitions:
- all aggregate PF>1
- 408/729 all-year PF>1
- only4/729 remain aggregate PF>1 after extra2bps
- canonical extra2bps PF~0.9568

Decision: auxiliary/cost-sensitive, not primary.

### S2 M15

Canonical M9P N3.
Primary reproducible branch.

### S3 H1

Definition:
- closed H4 MACD bps >= trailing100 q75
- closed D1 MACD bps >= trailing100 q50

Canonical:
- n191
- WR71.20%
- PF1.7802
- ~4.55/month

Stress81 nearby definitions:
- 81/81 PF>1 every available year
- 81/81 aggregate PF>1 after extra2bps
- PF range ~1.57–2.63
- extra2bps PF range ~1.43–2.34
- min calendar-year PF ~1.09

Decision: highest-priority new multi-timeframe branch for fresh prospective evidence.

### S4 H4

Definition:
- closed D1 RCI9 >= trailing100 median
- D1 EMA20>EMA30>EMA40

Canonical historical:
- n70
- WR72.86%
- PF3.2956

Stress9 nearby definitions:
- 9/9 aggregate survives extra2bps
- only4/9 all-year PF>1

Decision: premium/reference small-sample only.

---

## 10. M9T causal historical one-position portfolio

Rules:

- GOLD LONG only
- chronological first eligible branch opens one position
- later branch candidates during active position = confirmation metadata only
- simultaneous priority H4 > H1 > M15 > M5
- accepted branch uses its own proxy exit
- no pyramiding

Historical exposed reference:

- n2241
- ~53.36/month
- WR63.23%
- PF1.4447
- avg win +17.23bps
- avg loss -20.54bps
- DD535.4bps
- streak8
- all four years PF>1
- 13/14 quarters PF>1
- remaining weak 2025Q3 PF~0.804
- extra2bps PF1.1617

Monthly branch return correlations were low, supporting diversification.

Generic timeframe agreement is NOT always good; sequence/order changes outcome materially.

---

## 11. M9U deterministic reproduction — PASS

Implementation:
`scripts/mochipoyo_alert_research/m9u/python/run_multitimeframe_portfolio_reproduction_audit.py`

Result:
`config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`

Assistant self-verified exact M9T reference:

- S1=1256
- S2=1495
- S3=191
- S4=70
- portfolio=2241
- PF=1.444651452178

Still historical research-exposed; not independent validation/live.

---

## 12. M9V contract — fresh forward breadth test

Contract:
`config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`

Arms:

### V0_M15_ONLY
S2 M15 only.

### V1_M15_PLUS_H1
S2 + S3.

### V2_ALL_TIMEFRAMES
S1 + S2 + S3 + S4.

All arms:

- one GOLD LONG position only
- when flat first eligible candidate accepted
- later eligible candidate during active trade = ordered confirmation metadata
- no pyramiding
- no generic agreement score
- accepted candidate uses its own native proxy exit
- no M9R runner in M9V

Fresh start:

- brand-new GOLD start required
- no M7C/M8C start reuse
- no historical backfill
- pre-start PRIMARY never eligible
- pre-start bars may rehydrate state only
- if ACTIVE at start due pre-start PRIMARY, wait for its EXIT/IDLE before eligible post-start PRIMARY
- immutable runtime manifest/start receipt

---

## 13. M9V implementation — DONE / self-test PASS

Self-test result:
`config/mochipoyo_alert_research/m9v_implementation_self_test_result_20260724.json`

Core:
`scripts/mochipoyo_alert_research/m9v/python/m9v_core.py`

Initializer:
`scripts/mochipoyo_alert_research/m9v/python/initialize_m9v_runtime.py`

Default one-time initializer:
`scripts/mochipoyo_alert_research/m9v/python/initialize_m9v_fresh_runtime_once.py`

One-shot:
`scripts/mochipoyo_alert_research/m9v/python/run_m9v_shadow_once.py`

Persistent safe loop:
`scripts/mochipoyo_alert_research/m9v/python/run_m9v_shadow_forever_safe.py`

Stop helper:
`scripts/mochipoyo_alert_research/m9v/python/stop_m9v_shadow_forever.py`

Self-test intentionally used a historical file truncation/start/append simulation; it is implementation evidence only, NOT forward trading evidence.

Simulated start:
`2025.05.30 23:57:00` MT5 server time.

State at simulated start deliberately included inherited active states:

- M5 IDLE
- M15 ACTIVE_SHORT from pre-start primary
- H1 ACTIVE_LONG from pre-start primary
- H4 ACTIVE_LONG from pre-start primary

After later rows were appended:

- candidate primary at/before start = 0
- earliest candidate primary after start = 2025.06.02 01:05
- V0/V1/V2 holding overlap counts = 0
- pre-start M15 CSV row tamper caused immediate `[M9V BLOCKED]` exit2
- rerunning initializer with existing runtime caused `[M9V INIT FAIL_CLOSED]` exit2
- safe forever loop passed one-cycle test

This confirms:

- inherited ACTIVE is state only, not candidate backfill,
- immutable start prefix integrity,
- no arm pyramiding,
- initializer cannot silently reset/re-freeze.

---

## 14. Numbered M9V operator BATs

Folder:
`scripts/mochipoyo_alert_research/m9v/bat`

Physical order:

1. `01_initialize_fresh_runtime_once.bat`
2. `02_run_shadow_once.bat`
3. `03_run_shadow_forever.bat`
4. `04_stop_shadow_forever.bat`
5. `05_open_latest_results.bat`

Runtime manifest:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m9v_runtime\m9v_runtime_manifest.json`

Start receipt:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m9v_runtime\m9v_runtime_start_receipt.json`

Latest results:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9V\LATEST`

Submission:
`99_UPLOAD_PACKAGE.zip`

---

## 15. IMMEDIATE NEXT ACTION

Keep M8C / M7C / genuine source collector running.

User must Fetch/Pull latest branch first.

Then:

### Step 1 — ONE TIME
Run:
`scripts/mochipoyo_alert_research/m9v/bat/01_initialize_fresh_runtime_once.bat`

Success text:
`[M9V INIT PASS] fresh GOLD prospective start frozen`

If PASS:

- NEVER run 01 again,
- NEVER delete/reset/replace M9V runtime manifest/start receipt.

If `[M9V INIT FAIL_CLOSED]`:

- no new start was frozen,
- send full screen output,
- do not manually delete anything unless explicitly reviewed.

### Step 2 — ONE TIME INITIAL AUDIT
After INIT PASS run:
`scripts/mochipoyo_alert_research/m9v/bat/02_run_shadow_once.bat`

Success:
`[M9V PASS] ...`

Then run:
`scripts/mochipoyo_alert_research/m9v/bat/05_open_latest_results.bat`

Submit:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9V\LATEST\99_UPLOAD_PACKAGE.zip`

### Step 3 — DO NOT START YET
Do NOT start `03_run_shadow_forever.bat` until the first local M9V package is reviewed by ChatGPT.

After review, 03 will become the persistent monitor while M8C/M7C/collector continue in parallel.

---

## 16. Current state files

Read after this handoff because they may be newer:

1. `config/mochipoyo_alert_research/current_state_20260723.json`
2. `config/mochipoyo_alert_research/next_action_20260723.json`
3. `config/mochipoyo_alert_research/m9v_implementation_self_test_result_20260724.json`
4. `config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`
5. `config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`
6. `config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json`
7. `config/mochipoyo_alert_research/m9q_gold_loss_reduction_profit_extension_exploratory_result_20260724.json`

---

## 17. Always-ready next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初にGitHubの次を順番どおり必ず読んでください。

1.
docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_IMPLEMENTED_FRESH_START_INIT_NEXT_20260724.md

2.
config/mochipoyo_alert_research/current_state_20260723.json

3.
config/mochipoyo_alert_research/next_action_20260723.json

4.
config/mochipoyo_alert_research/m9v_implementation_self_test_result_20260724.json

5.
config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json

6.
config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json

7.
config/mochipoyo_alert_research/m9t_multitimeframe_branch_robustness_portfolio_dedup_result_20260724.json

現在audit-onlyです。
M8C/M7C/genuine source collectorは継続中です。停止・reset・prospective start変更・backfillは禁止です。

GOLD multi-timeframe方針:
S1=M5補助、S2=M15 N3主軸、S3=H1最高優先新枝、S4=H4 premium小標本。
同一相場の複数時間足LONGはpyramidingせず、一ポジションdedup＋ordered confirmation metadataです。
単純な複数時間足一致数をpositive confidenceにしないでください。

M9U決定論的再現はPASS: S1=1256 S2=1495 S3=191 S4=70 portfolio=2241 PF1.444651452178。

M9Vは実装・bootstrap/fail-closed self-testまでPASSし、ユーザー環境fresh start初期化待ちです。
M9V arms:
V0=M15のみ
V1=M15+H1
V2=M5+M15+H1+H4
M9R half-risk/runnerはまだ混ぜません。

現在の次アクションは、ユーザーが最新branchをPullしてM9Vの01を一回だけ実行し、INIT PASS後に02を一回実行、05から99_UPLOAD_PACKAGE.zipを提出することです。
INIT PASS後は01を二度と再実行・resetしないでください。
03 persistent loopは最初のpackage review前には開始しません。

ユーザーはPythonを直接実行しません。
わからないことを憶測で実装しないでください。ただしhandoffに答えがあることを再質問しないでください。
```

---

## 18. Handoff maintenance

After the user creates the real M9V fresh start, immediately record the immutable start/receipt status and create/update the next handoff before starting the persistent loop.
