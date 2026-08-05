# BTC AI V1 Stage55 Discord entry通知 addendum

日付: 2026-08-04  
モード: Prospective Shadowの配送sidecar

## 通知対象

新しく `ACCEPTED_SHADOW` になった次のSHORT entryだけをDiscordへ通知する。

1. M1騙し後・M1陰転確認SHORT
2. M5水準拒否後・M5弱気反転SHORT

通知は売買判断器ではなく、ユーザーがentry位置を目視確認するための配送経路である。

## 通知内容

- family
- SHORT方向
- MT5 source時刻
- 騙し警告時刻
- 弱気確認時刻
- exact M1 entry時刻
- Entry / SL / 2R TP
- risk幅 / 最大保有時間
- M1 familyの固定scoreと閾値
- 観測専用・実注文なしの警告
- M1またはM5チャート（設定でOFF可能）

## no-backfill

Discord notifierを初めて起動した時点で、既存のaccepted entryをbaselineとして消費し、送信しない。

再起動後に未送信entryが見つかっても、現在の最新closed M1から10分を超えて古い場合は `STALE_ENTRY_NO_BACKFILL` として記録し、送信しない。通知停止中の過去entryを後から現在のentryのように送らないためである。

## 通知しないもの

- NO_SIGNAL
- recovery replay
- exact M1欠損・無効candidate
- 抑制されたcandidate
- TP / SL / MAX決済
- 成績判定・promotion
- notifier初回起動以前のentry

## Webhook

Webhook URLは `runtime/btc_ai_v1/stage55_shadow/local_config.json` のみに保存する。GitHub、example、チャットへ秘密を貼らない。

```json
"discord": {
  "enabled": true,
  "webhook_source": "LOCAL_CONFIG",
  "webhook_url": "https://discord.com/api/webhooks/...",
  "username": "BTC Stage55 Shadow",
  "attach_chart": true,
  "chart_bars": 120,
  "poll_seconds": 15
}
```

## 起動

Shadow本体の `03_RUN_LOOP.bat` と、通知用の `07_RUN_DISCORD_ALERTS.bat` を同時に開いておく。

1. `05_CONFIGURE_DISCORD.bat`
2. `06_TEST_DISCORD.bat`
3. `07_RUN_DISCORD_ALERTS.bat`
4. `08_DISCORD_STATUS.bat`

## 絶対境界

通知の成功・失敗、ユーザーの目視印象、チャート形状を、Stage55候補の削除・条件変更・成績判定へ使用しない。MT5注文、live trading、final_signal、live_readyはOFFのまま。
