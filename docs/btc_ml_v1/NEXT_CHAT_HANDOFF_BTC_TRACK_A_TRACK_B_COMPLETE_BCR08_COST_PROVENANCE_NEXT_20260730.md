# NEXT CHAT HANDOFF — BTC Track A / Track B complete, BCR08 cost provenance next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:25:00+09:00`
- status: `BTC_REDESIGN_TRACK_A_AND_TRACK_B_COMPLETE_OUTCOME_BLIND_BCR08_COST_PROVENANCE_READY`
- profitability outcomes opened in redesign: `false`
- deployable candidates: `0`

## 1. Startup hard gate

Use only branch:

`feature/btc-fresh-forward-research`

Do not use `main`, default branch, a similar file or an old handoff as current authority.

Start from:

`START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`

Do not begin with repo-wide search. Do not read `AGENTS.md`, GOLD V3, GOLD ML, old GOLD, DISC8, Stage41, old BTC stacking/YouTube handoffs or FF05 recovery V3–V11.

MOCHIPOYO broad search remains forbidden. Only the exact previously allowlisted M7C/Collector evidence may be read, and only read-only.

## 2. Runtime protection

Do not stop, restart, reset or modify:

- Collector;
- M7C;
- M8C;
- M9;
- M10;
- GOLD/MOCHIPOYO runtime or outputs.

Do not send Discord messages or MT5 orders. Do not write BTC research output into GOLD/MOCHIPOYO folders.

## 3. Frozen market-data provenance

Authoritative BTC M15 origin:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`

Frozen research content SHA256:

`b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

The live file at the same path may have grown. It does not silently replace the frozen snapshot.

Causal boundary:

- fully closed M15 history allowed;
- current M15 open allowed;
- current M15 high/low/close forbidden;
- future bars and gap interpolation forbidden;
- higher timeframe forbidden until a separate as-of contract exists.

## 4. Track A — Mochipoyo-source-anchored complete family

BCR05C proved that source exits are RCI extreme-state events rather than opposite-turn events:

- LONG exits: 17/17 in positive extreme, observed RCI9 70 to 91.67;
- SHORT exits: 10/10 in negative extreme, observed RCI9 -88.33 to -70;
- opposite RCI turn at exact exit: 0 in both directions.

M7C exit decomposition for comparable events:

- LONG exact / late-one-bar / missed: 9 / 4 / 4;
- SHORT exact / late-one-bar / missed: 4 / 2 / 3.

Three missed exits blocked later otherwise-valid primary events by stale ACTIVE state:

- exit 85 -> primary 86;
- exit 97 -> primary 98;
- exit 169 -> primary 172.

BCR05D produced two LONG and three SHORT finite exit variants. BCR05E replayed all 36 complete entry/exit combinations as path-dependent one-position state machines.

Frozen Track A family:

1. `TRACK_A_F1_COVERAGE_FIRST`
   - exact supported recall 51/53 = 96.23%;
   - extra transitions 66;
   - divergent boundaries 425.
2. `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE`
   - 50/53 = 94.34%;
   - extras 37;
   - divergence 266.
3. `TRACK_A_F3_STATE_FIDELITY`
   - 45/53 = 84.91%;
   - extras 16;
   - divergence 220.
4. `TRACK_A_F4_MINIMUM_EXTRA_PARETO`
   - 40/53 = 75.47%;
   - extras 15;
   - divergence 298.

All four remain frozen because none dominates the others. They are fidelity profiles, not profitability candidates.

Every future value test and standalone shadow must initialize `IDLE` and must not read source state.

Key artifacts:

- BCR05C package SHA: `221280603569054f3ffc23c6698446e377f9d650d288fa3d08d224a8e3925af3`
- BCR05D package SHA: `b1c4c66454f3076ffc90b22cac27280c6daa38f97db63ae07bed5294eed872d7`
- BCR05E package SHA: `d8fd13557f3b0a9c6d7fc9d499e7654ec4cb814f5538e41928b2e9d2c4d0ca84`
- family freeze: `docs/btc_ml_v1/BTC_BCR05F_TRACK_A_SOURCE_FIDELITY_FAMILY_FREEZE_20260730.md`

## 5. Track B — independent complete state machines

Track B excludes RCI, source labels/state and M7C thresholds.

BCR06 outcome-blind density audit advanced:

- B1 LONG trend-pullback `B1_LONG_S0_H8_C0`;
- B1 SHORT trend-pullback `B1_SHORT_S0_H4_C0`;
- B4 LONG overextension mean reversion `B4_LONG_T1p5_C0`;
- B4 SHORT overextension mean reversion `B4_SHORT_T1p0_C0`.

B2 compression-expansion did not advance because the frozen causal current-open breakout definition produced only 0–4 fires per grammar. No threshold rescue is allowed.

BCR07 froze four complete IDLE-seeded state machines:

1. `TRACK_B_B1_E0_EMA30_CROSS`
   - 1,980 closed episodes;
   - median hold 2 bars; p90 23; maximum 122.
2. `TRACK_B_B1_E1_STACK_BREAK`
   - 519 closed;
   - median 27; p90 103.2; maximum 254.
3. `TRACK_B_B4_E0_EMA20_TOUCH`
   - 773 closed and one open endpoint episode;
   - median 11; p90 31.8; maximum 69.
4. `TRACK_B_B4_E1_EXTENSION_CONTRACT`
   - 832 closed and one open endpoint episode;
   - median 9; p90 26; maximum 65.

All passed data-capability gates. None has been evaluated for profit.

Key artifacts:

- BCR06 package SHA: `04215689d2b861b72e737e000dfe6a6b3d2434ec2caae37b9574edd4b770027b`
- BCR07 package SHA: `7b2643a00179aaa3b09c2854fa52e10e4bbad6ed9ff69d0a58e3d279ea7cb0f4`

## 6. Why PnL must not be opened yet

The historical CSV `spread` column has values around the thousands. Its conversion cannot be guessed.

Before all eight frozen machines enter one shared value gate, prove:

- exact symbol name;
- digits and point;
- tick size and tick values;
- contract size;
- profit/margin currency;
- calculation and execution modes;
- relationship between CSV spread values, point and contemporaneous bid/ask spread;
- commission contract.

B1 E0 has a median holding of only two M15 bars, so cost interpretation is especially load-bearing.

## 7. BCR08 implementation

BCR08 is ready as a one-run read-only evidence exporter.

Files:

- contract: `docs/btc_ml_v1/BTC_BCR08_MT5_SYMBOL_AND_COST_PROVENANCE_CONTRACT_20260730.md`
- contract JSON: `configs/btc_ml_v1/btc_bcr08_mt5_symbol_cost_provenance_contract_20260730.json`
- Python: `scripts/btc_ml_v1/BCR08_mt5_symbol_cost_provenance/python/run_bcr08_mt5_symbol_cost_provenance.py`
- BAT: `scripts/btc_ml_v1/BCR08_mt5_symbol_cost_provenance/01_run_BCR08.bat`
- static test: `tests/btc_ml_v1/test_bcr08_mt5_symbol_cost_provenance.py`

Safety:

- requires `terminal64.exe` already running;
- refuses to launch a closed terminal;
- requires exact terminal `data_path` match;
- expected exact symbol hypothesis is `BTCUSD#`;
- if not found, emits a blocked ZIP with all `*BTC*` candidates;
- no order, position, order history, deal history or `symbol_select` call;
- account number, name, balances and PnL redacted;
- local static tests: 3 passed.

Commission remains unresolved even after a successful run because `symbol_info` does not establish the commission schedule.

## 8. Exact next action

In GitHub Desktop for `C:\btc-ff`:

1. confirm branch `feature/btc-fresh-forward-research`;
2. Fetch origin;
3. Pull origin;
4. keep the existing MT5 terminal, Collector and M7C running;
5. run once:

`C:\btc-ff\scripts\btc_ml_v1\BCR08_mt5_symbol_cost_provenance\01_run_BCR08.bat`

Upload the first generated ZIP, success or failure:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR08_mt5_symbol_cost_provenance\LATEST\99_UPLOAD_PACKAGE.zip`

Do not rerun automatically. If it blocks because the exact symbol is absent or another terminal is connected, the first package is the evidence needed to resolve it.

## 9. Still forbidden

- PnL/WR/PF/DD/MFE/MAE;
- spread conversion by assumption;
- zero-commission assumption;
- TP/SL or time-stop optimization;
- candidate promotion/rejection;
- FF06;
- prospective start or shadow;
- Discord or MT5 orders;
- runtime changes to GOLD/MOCHIPOYO systems.

## 10. After BCR08

Audit the package, freeze the exact spread-price conversion and commission evidence status, then preregister one shared retrospective trading-value contract for all four Track A and four Track B machines. No member receives a more favorable execution or cost assumption.
