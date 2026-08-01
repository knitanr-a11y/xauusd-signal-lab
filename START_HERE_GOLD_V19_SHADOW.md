# START HERE — GOLD V19 Prospective Shadow

このbranchは、V19で固定された次の研究候補を**観測専用Prospective Shadow**として動かすための実装です。

`SEMIANNUAL_EXPANDING + P90 + FIRST_P90_PER_IMPULSE_EARLY_EPISODE + TP20/SL10`

最初に読む順番:

1. `docs/gold_wave_shadow_v19/NEXT_CHAT_HANDOFF_GOLD_V19_SHADOW_READY_DISCORD_ENTRY_ALERT_NEXT_20260801.md`
2. `docs/gold_wave_shadow_v19/GOLD_V19_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
3. `docs/gold_wave_shadow_v19/GOLD_V19_DISCORD_ENTRY_ALERT_ADDENDUM_20260801.md`
4. `config/gold_wave_shadow_v19/frozen_contract_20260801.json`
5. `config/gold_wave_shadow_v19/discord_alert_contract_20260801.json`
6. `config/gold_wave_shadow_v19/current_state_20260801.json`
7. `config/gold_wave_shadow_v19/next_action_20260801.json`

Shadow判断はDiscord、AI判断、MT5注文、実売買に依存しません。

ユーザーの明示許可により、**新しく採用されたShadow entryだけ**をDiscordへ送る観測用sidecarが追加されています。Discordは通知専用で、売買判断・成績・半年更新へ影響しません。

## WindowsでのShadow開始

1. `scripts/gold_wave_shadow_v19/01_INSTALL.bat`
2. 自動作成された `config/gold_wave_shadow_v19/local_config.json` のCSVパスを修正
3. `scripts/gold_wave_shadow_v19/02_BOOTSTRAP_ACTIVATE.bat`
4. `scripts/gold_wave_shadow_v19/03_RUN_LOOP.bat`
5. 状態確認は `scripts/gold_wave_shadow_v19/04_STATUS.bat`

初回activateはno-backfillです。起動時点以前の候補をShadow取引として記録しません。

## Discord entry通知

branch更新後に次を行います。

1. `01_INSTALL.bat`を再実行
2. `06_CONFIGURE_DISCORD.bat`でWebhook URLをローカル入力
3. `07_TEST_DISCORD.bat`で接続とM15チャートを確認
4. `08_RUN_DISCORD_ALERTS.bat`をShadow loopと同時に開いておく
5. `09_DISCORD_STATUS.bat`で通知状態を確認

Webhook URLは`local_config.json`だけに保存され、Gitには追加されません。Webhook URLをチャット、Issue、PR、ログへ貼らないでください。
