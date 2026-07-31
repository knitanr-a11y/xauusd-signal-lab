# NEXT CHAT HANDOFF — GOLD V19 Shadow implemented

repo: `knitanr-a11y/xauusd-signal-lab`  
working branch: `feature/gold-v19-wave-shadow`  
base: `main` at implementation start `7c3e9ee3e8bfb21f024a273cc3d695d273c0abd5`

最初に読む:

1. `START_HERE_GOLD_V19_SHADOW.md`
2. `docs/gold_wave_shadow_v19/GOLD_V19_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
3. `config/gold_wave_shadow_v19/frozen_contract_20260801.json`
4. `config/gold_wave_shadow_v19/current_state_20260801.json`
5. `config/gold_wave_shadow_v19/next_action_20260801.json`
6. `scripts/gold_wave_shadow_v19/frozen_router.py`
7. `scripts/gold_wave_shadow_v19/frozen_wave.py`
8. `scripts/gold_wave_shadow_v19/shadow_runtime.py`

現在の固定候補:

`SEMIANNUAL_EXPANDING + P90 + FIRST_P90_PER_IMPULSE_EARLY_EPISODE + TP20/SL10`

重要:

- Shadowはユーザー承認済み。
- observation-only。
- Discord、AI、MT5注文、実売買は禁止。
- 初回activateはno-backfill。
- PC停止中の候補は回復処理しても取引扱いにしない。
- 半年更新は自動。境界は1月1日・7月1日。
- active boundaryは2026-07-01、次は2027-01-01。
- 新boundaryでは720分のcausal label availabilityが揃うまでfail-closed。
- old model fallbackは禁止。
- P90、波動尺度、episode、TP20/SL10、LONG/SHORTを変更しない。
- causal session horizon guardは歴史169件と169/169 timestamp parity確認済み。

GitHub実装完了後も、ユーザーPC上では次が必要:

1. branchを取得
2. `01_INSTALL.bat`
3. `local_config.json`へexact CSV paths
4. `02_BOOTSTRAP_ACTIVATE.bat`
5. health READY確認
6. `03_RUN_LOOP.bat`

runtimeを回した期間が短く、2027-01-01へ到達しなければ半年更新は発生しない。
