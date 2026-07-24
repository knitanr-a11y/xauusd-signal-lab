# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9V v1 PREFIX INCIDENT / v2 RECOVERY NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

This is the current restart point if the conversation reaches its length limit.

## 1. Actual objective

The goal is not exact Mochipoyo reproduction. The goal is a robust multi-timeframe / multi-asset trading edge with useful portfolio-level frequency, high win rate where possible, PF materially above 1 after realistic costs, lower DD/loss tails, and better reward/risk.

Current strategic direction:
- GOLD M5/M15/H1/H4 are separate branches.
- A single branch may be strict; portfolio breadth supplies frequency.
- Overlapping timeframe signals are deduplicated; no automatic pyramiding.
- Ordered timeframe sequence matters more than generic agreement count.
- BTC remains a separate research family; never transplant GOLD rules directly into BTC.

## 2. Hard safety contracts

Audit-only remains ON.

All remain OFF/FALSE:
- Discord send
- MT5 orders
- live ready
- final signal
- real entry gate

Never:
- reset M7C,
- reset M8C,
- reuse M7C/M8C prospective starts,
- backfill a new prospective shadow,
- use future outcome data in candidate construction,
- pyramid overlapping M5/M15/H1/H4 LONG signals by default,
- claim commission/swap are modeled when they are not.

M8C, M7C and genuine source collector remain running unchanged.

## 3. M9U deterministic historical portfolio reproduction

M9U self-verification matched M9T:
- S1 M5 = 1256
- S2 M15 = 1495
- S3 H1 = 191
- S4 H4 = 70
- causal one-position portfolio = 2241
- portfolio PF = 1.444651452178
- approximately 53.36 accepted trades/month historically
- WR about 63.23%
- all available years PF > 1
- extra 2 bps/trade PF about 1.1617
- 2025Q3 remains weak (~0.804 PF)

This is historical/research-exposed evidence, not independent forward validation.

## 4. M9V intended fresh forward arms

M9V compares portfolio breadth before adding M9R risk/reward overlays:
- V0 = M15 N3 only
- V1 = M15 N3 + H1 S3
- V2 = M5 S1 + M15 S2 + H1 S3 + H4 S4

Each arm is one-position GOLD LONG accounting. Later eligible branch signals while active are ordered confirmation metadata only.

M9R remains frozen/not started:
- R0 N3 base
- R1 N6 half-risk
- R2 selective half-runner
- R3 combined

Do not mix M9R into M9V initial breadth comparison.

## 5. M9V v1 incident — IMPORTANT

User successfully ran the original BAT 01, then BAT 02 immediately blocked with:

`[M9V BLOCKED] M9VContractError: historical prefix changed after M9V start: M5`

This was diagnosed as an implementation-contract bug, not a user error and not a strategy failure.

### Root cause

v1 froze a fingerprint of every CSV row whose server-open timestamp was <= the M1-derived start.

The initializer allowed M5 to trail M1. A normal later M5 catch-up/append could therefore add a row whose server-open timestamp was <= the already-frozen start. The v1 one-shot then interpreted that normal append as a historical mutation and blocked.

The one-shot blocked before producing a PASS prospective output.

Do NOT manually delete/reset the v1 runtime.

## 6. M9V runtime v2 fix

Formal incident file:

`config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json`

Runtime version:

`M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`

v2 semantics:
- freeze the exact first N rows physically present in each CSV at initialization,
- verify those frozen N rows never change,
- allow later strictly ascending appends,
- anchor bootstrap state comparison to the frozen-row snapshot,
- no historical backfill,
- pre-start PRIMARY candidate eligibility remains false.

v2 self-tests passed:
- v2 initializer PASS,
- normal append after start PASS,
- M5 append whose server-open is before the M1 start PASS,
- tampering with an already-frozen M5 row BLOCKS,
- recovery archives old runtime before removing original,
- recovery refuses to invalidate an old start if a successful M9V PASS summary exists for that same start.

## 7. Current operator sequence — DO THIS EXACTLY

After pulling latest branch, while M8C/M7C/collector remain running:

### Step 00 — one-time incident recovery

Run:

`scripts/mochipoyo_alert_research/m9v/bat/00_recover_invalid_v1_prefix_start_once.bat`

Expected success:

`[M9V RECOVERY PASS]`

This archives the old v1 runtime + receipt under the local M9V runtime `invalidated` folder and only then removes the active originals. It creates no new prospective start.

If BLOCKED: do not delete anything manually; send full screen output.

### Step 01 — fresh runtime v2, exactly once

After Step 00 PASS, run:

`scripts/mochipoyo_alert_research/m9v/bat/01_initialize_fresh_runtime_once.bat`

Expected success:

`[M9V INIT PASS]`

After PASS, never rerun 01 and never delete/reset the v2 runtime manifest/start receipt.

### Step 02 — initial one-shot v2

After Step 01 PASS, run:

`scripts/mochipoyo_alert_research/m9v/bat/02_run_shadow_once.bat`

Expected success:

`[M9V PASS]`

Then run:

`scripts/mochipoyo_alert_research/m9v/bat/05_open_latest_results.bat`

Submit:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9V\LATEST\99_UPLOAD_PACKAGE.zip`

### Step 03 — DO NOT START YET

Do not run `03_run_shadow_forever.bat` until ChatGPT reviews the initial v2 package.

## 8. Current implementation files

- `scripts/mochipoyo_alert_research/m9v/python/m9v_core_v2.py`
- `scripts/mochipoyo_alert_research/m9v/python/initialize_m9v_runtime_v2.py`
- `scripts/mochipoyo_alert_research/m9v/python/initialize_m9v_fresh_runtime_once_v2.py`
- `scripts/mochipoyo_alert_research/m9v/python/run_m9v_shadow_once_v2.py`
- `scripts/mochipoyo_alert_research/m9v/python/run_m9v_shadow_forever_safe_v2.py`
- `scripts/mochipoyo_alert_research/m9v/python/recover_m9v_v1_prefix_incident_once.py`

The v1 files remain as history/compatibility and should not be used by the numbered BAT flow now.

## 9. Current state files

Always read these after this handoff:

1. `config/mochipoyo_alert_research/current_state_20260723.json`
2. `config/mochipoyo_alert_research/next_action_20260723.json`
3. `config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json`
4. `config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`
5. `config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`

## 10. Next-chat start prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初に次を順番どおり必ず読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_V1_PREFIX_INCIDENT_V2_RECOVERY_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json
5. config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json

M8C / M7C / genuine source collectorは動作継続中です。停止・reset・prospective start変更をしないでください。

M9V v1は01 PASS後、最初の02で `historical prefix changed after M9V start: M5` となりました。これはprefix freeze semanticsの実装事故で、ユーザー操作ミスでも戦略失敗でもありません。

修正版M9V runtime v2は `M9V_RUNTIME_V2_APPEND_SAFE_PREFIX` です。
現在は、旧v1 startをBAT 00で正式archive無効化 → BAT 01でv2 fresh start → BAT 02でinitial one-shot → ZIP確認、の順です。
BAT 03 persistent loopはinitial ZIPレビューまで開始しないでください。

憶測で旧runtimeを削除したり、M8C/M7Cをresetしたりしないでください。
```
