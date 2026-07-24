# NEXT CHAT HANDOFF — MOCHIPOYO ALERT RESEARCH — M9V v2 INITIAL PASS / PERSISTENT FORWARD NEXT

Date: 2026-07-24

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## 1. Objective

Build a robust multi-timeframe / multi-asset trading edge with useful portfolio-level frequency, strong PF/win rate, balanced payoff, reduced DD/tails, and live-causal reproducibility. Exact proprietary Mochipoyo reproduction is not the final objective.

## 2. Hard guardrails

Audit-only.

Keep OFF:
- Discord send
- MT5 orders
- live ready
- final signal
- entry gate

Never reset M7C or M8C. Never reuse their prospective starts. New M9V is separate and has its own immutable start.

M8C / M7C / genuine source collector remain running unchanged.

## 3. Historical multi-timeframe reference

M9U deterministic reproduction matched M9T:
- S1 M5: 1256
- S2 M15: 1495
- S3 H1: 191
- S4 H4: 70
- causal one-position portfolio: 2241
- historical PF: 1.444651452178
- about 53.36 accepted trades/month
- WR about 63.23%
- all available years PF > 1
- extra 2 bps/trade PF about 1.1617
- 2025Q3 remained weak (~0.804 PF)

Historical/research-exposed only; not independent forward validation.

## 4. M9V arms

Fresh GOLD multi-timeframe forward comparison:
- V0 = M15 N3 only
- V1 = M15 N3 + H1 S3
- V2 = M5 S1 + M15 S2 + H1 S3 + H4 S4

One GOLD LONG position per arm. Later eligible branch signals during an active position are ordered confirmation metadata only. No generic agreement score and no pyramiding.

M9R remains frozen/not started:
- R0 N3 base
- R1 N6 half-risk
- R2 selective half-runner
- R3 combined

Do not mix M9R into base M9V yet.

## 5. v1 incident and v2 fix

Original v1 start passed initializer but first one-shot blocked:

`historical prefix changed after M9V start: M5`

This was an implementation-contract bug, not user error and not strategy failure.

v2 runtime version:

`M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`

v2 freezes the exact first N rows physically present at initialization and verifies those rows never mutate; later strictly ascending appends are allowed.

Formal incident file:

`config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json`

The invalid v1 runtime was handled through the guarded BAT 00 recovery path. BAT 00 and BAT 01 must never be rerun now.

## 6. v2 initial local PASS

User submitted:

`99_UPLOAD_PACKAGE(19).zip`

SHA256:

`8c6bf608887966d50474c49ac63dd73eb20fb112d74df0a6c3f89bc61138e5cd`

Formal result:

`config/mochipoyo_alert_research/m9v_v2_initial_local_pass_20260724.json`

Fresh start, MT5 server time:

`2026.07.24 11:04:00`

Runtime created at:

`2026-07-24T08:05:49Z`

Initial one-shot built:

`2026-07-24T08:06:08Z`

At that first one-shot:
- candidate_count = 0
- V0 = 0
- V1 = 0
- V2 = 0
- confirmations = 0

This is expected because only about one M1 minute had elapsed beyond the fresh start. This initial package was an integrity/bootstrap check, not a performance result.

Runtime integrity confirmed:
- runtime version v2 correct
- historical backfill false
- pre-start PRIMARY candidate eligibility false
- prefix integrity verified
- nearest M1 fallback false
- pyramiding false
- generic agreement score false
- M9R overlay excluded
- Discord/MT5/live/final all false
- M8C not reset

Bootstrap state at start:
- M5 ACTIVE_SHORT inherited from 2026.07.24 07:45:00
- M15 IDLE
- H1 ACTIVE_LONG inherited from 2026.07.23 03:00:00
- H4 IDLE

Inherited pre-start ACTIVE states are state only; their pre-start PRIMARYs are not prospective candidates.

## 7. Current operator action

M9V v2 is now approved for persistent audit-only forward collection.

Run and keep open:

`scripts/mochipoyo_alert_research/m9v/bat/03_run_shadow_forever.bat`

Keep M8C, M7C and genuine source collector running in parallel.

Safe stop only:

`scripts/mochipoyo_alert_research/m9v/bat/04_stop_shadow_forever.bat`

Never rerun:
- `00_recover_invalid_v1_prefix_start_once.bat`
- `01_initialize_fresh_runtime_once.bat`

Never delete/reset the v2 runtime manifest/start receipt.

When a checkpoint package is requested:

`scripts/mochipoyo_alert_research/m9v/bat/05_open_latest_results.bat`

Submit:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9V\LATEST\99_UPLOAD_PACKAGE.zip`

## 8. Review gates

M9V contract checkpoints:
- operational: total accepted arm events >= 20
- interim: >= 60
- H1 branch review: S3 H1 candidates >= 10
- formal portfolio review: >= 120

These are review checkpoints, not guaranteed statistical sufficiency. No automatic live promotion.

## 9. BTC

BTC remains separate.

Do not transplant GOLD rules into BTC. Continue genuine-source / M7C / M8C forward evidence unchanged. M8C BTC LONG rejection challenger remains running.

## 10. Files to read in the next chat

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_V2_INITIAL_PASS_PERSISTENT_FORWARD_NEXT_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/m9v_v2_initial_local_pass_20260724.json`
5. `config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json`
6. `config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`

## 11. Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。

最初に次を順番どおり必ず読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_V2_INITIAL_PASS_PERSISTENT_FORWARD_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/m9v_v2_initial_local_pass_20260724.json
5. config/mochipoyo_alert_research/m9v_v1_prefix_freeze_incident_and_v2_recovery_20260724.json
6. config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json

M8C / M7C / genuine source collectorは継続中です。停止・reset・prospective start変更禁止です。

M9V v1 prefix incidentは解決済みです。現在はruntime v2 `M9V_RUNTIME_V2_APPEND_SAFE_PREFIX` です。
M9V v2 fresh startはMT5 server time 2026.07.24 11:04:00で固定済みです。BAT 00とBAT 01は二度と実行しないでください。

初回one-shot ZIPはPASS済みで、現在は03_run_shadow_forever.batによるpersistent audit-only forward collection段階です。
M9R risk/reward overlayはまだ開始しないでください。
```
