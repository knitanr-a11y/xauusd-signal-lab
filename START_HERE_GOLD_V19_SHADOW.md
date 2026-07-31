# START HERE — GOLD V19 Prospective Shadow

このbranchは、V19で固定された次の研究候補を**観測専用Prospective Shadow**として動かすための実装です。

`SEMIANNUAL_EXPANDING + P90 + FIRST_P90_PER_IMPULSE_EARLY_EPISODE + TP20/SL10`

最初に読む順番:

1. `docs/gold_wave_shadow_v19/GOLD_V19_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
2. `config/gold_wave_shadow_v19/frozen_contract_20260801.json`
3. `config/gold_wave_shadow_v19/current_state_20260801.json`
4. `config/gold_wave_shadow_v19/next_action_20260801.json`

この実装はDiscord、AI判断、MT5注文、実売買を行いません。

## Windowsでの開始

1. `scripts/gold_wave_shadow_v19/01_INSTALL.bat`
2. 自動作成された `config/gold_wave_shadow_v19/local_config.json` のCSVパスを修正
3. `scripts/gold_wave_shadow_v19/02_BOOTSTRAP_ACTIVATE.bat`
4. `scripts/gold_wave_shadow_v19/03_RUN_LOOP.bat`
5. 状態確認は `scripts/gold_wave_shadow_v19/04_STATUS.bat`

初回activateはno-backfillです。起動時点以前の候補をShadow取引として記録しません。
