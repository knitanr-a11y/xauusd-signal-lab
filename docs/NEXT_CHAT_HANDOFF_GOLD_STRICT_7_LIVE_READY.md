# NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY

Last updated: 2026-05-20

この文書は、GOLD strict 7 の現状を次チャットへ引き継ぐためのメモです。

---

## 1. 現在のステータス

GOLD側は、strict 7 の候補を中心に以下の構成まで整理済みです。

```text
- シグナル検出
- Discord通知
- guarded demo connector
- post-trade AI review
- backtest AI review と live AI review の分離
```

GOLD strict 7 は、デモ検証を開始できる構成になっています。

最終的な完成判定は、実シグナル1件について、通知、ledger記録、決済後AI評価、重複スキップまで確認してからです。

---

## 2. 現行GOLD strict 7候補

```text
1. SELL_KC_CCI150_LONDON_TP100_SL10
2. BUY_SWEEP_RECLAIM_RSI_TP150_SL10
3. BUY_STOCH_BB_KTURN_NY_TP150_SL10
4. SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5
5. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120
6. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60
7. BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5
```

この7本を現行GOLD候補として扱います。
旧GOLD候補は、このstrict 7運用の対象外です。

---

## 3. 主要ドキュメント

まず読む文書:

```text
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
docs/REPOSITORY_CLEANUP_AND_DEPRECATION_POLICY.md
```

この文書:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
```

---

## 4. 主要スクリプト

シグナル仕様:

```text
scripts/gold_strict_7_signals/gold_strict_7_signal_specs.py
```

strict 7 検出・共通関数:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_backtest_from_csv.py
```

Discord通知系:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notifier_from_csv.py
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notify_forever_aligned.py
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notify_forever_aligned.bat
```

guarded demo connector系:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_guarded_demo_autotrade_from_csv.py
scripts/gold_strict_7_signals/run_gold_strict_7_guarded_demo_autotrade_forever_aligned.py
scripts/gold_strict_7_signals/run_gold_strict_7_guarded_demo_autotrade_forever_aligned.bat
```

live AI review系:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_live_ai_review_safe.py
scripts/gold_strict_7_signals/run_gold_strict_7_live_ai_review_pipeline.py
scripts/gold_strict_7_signals/run_gold_strict_7_live_ai_review_dry.bat
scripts/gold_strict_7_signals/run_gold_strict_7_live_ai_review.bat
```

既存sender:

```text
scripts/send_mt5_order_from_payload.py
```

---

## 5. 現在の監視間隔とCSV方針

EA側のCSV書き出しが約1分遅れる可能性があるため、GOLD strict 7 の常時監視BATは毎分監視へ変更済みです。

```text
interval_minutes: 1
run_delay_seconds: 2
bar_offset: 0
```

理由:

```text
- EAが確定足だけを書き出している前提。
- 最新CSV行を判定対象にする。
- 書き出しが1分程度遅れても次の1分チェックで拾える。
- 同じ足を複数回見てもledgerで重複を防ぐ。
```

軽量tail設定:

```text
M5: 2000
H1: 1000
H4: 500
D1: 300
```

---

## 6. Ledger と出力先

Discord通知ledger:

```text
data/runtime_state/gold/strict_7/discord_notification_ledger.csv
```

strict 7 connector ledger:

```text
data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv
```

live AI review 出力:

```text
data/runtime_logs/trade_ai_review_live_gold_strict_7/
```

backtest AI review 出力:

```text
data/runtime_logs/trade_ai_review_backtest_gold_strict_7/
```

---

## 7. AI評価の扱い

AI評価は、発生前の可否判定ではなく、完了後の仮説タグ付けとして扱います。

live AI review は以下のIDを見て、既に評価済みのものを除外します。

```text
trade_id
order_key
payload_key
```

まだstrict 7 ledgerが無い場合:

```text
reason: NO_ORDER_LEDGER_YET
cycle_ok: True
```

評価対象になる完了済みtradeが無い場合:

```text
reason: NO_REVIEWABLE_CLOSED_STRICT7_TRADE
cycle_ok: True
```

重要方針:

```text
- AI評価は仮説タグ付けのみ。
- 1件だけで条件変更しない。
- 自動停止、ブロック、ロット変更はまだ行わない。
- live結果とbacktest結果は混ぜない。
```

---

## 8. backtest AI review 初回結果

GOLD strict 7 backtest AI review は 314/314件完了済みです。

```text
payload_rows: 314
review_rows: 314
remaining_payload_rows_after_resume: 0
should_investigate_rows: 23
```

詳細:

```text
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```

---

## 9. まだ実地確認が必要なこと

次に確認すべきこと:

```text
1. Discord通知が毎分監視で遅れず届くか
2. strict 7 connector ledger が想定通り残るか
3. 既存sender側のチェック結果がsummaryに残るか
4. 完了後、live AI reviewが新規分だけ拾うか
5. 2回目live AI reviewで同じIDがスキップされるか
6. loop summaryのelapsed_secondsが十分短いか
7. EAのCSV書き出し時刻とPython検出時刻のズレが許容範囲か
```

見るsummary列:

```text
elapsed_seconds
ctx_rows
raw_recent_signals_after_cooldown
preview_rows
payload_rows
reason
pending_rows
skipped_already_reviewed_rows
review_rows_written_this_run
```

---

## 10. 次チャットで続ける場合

次チャットでは、まずこの文書と以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```

その後、実シグナルが出ていれば、以下を確認する。

```text
- Discord通知の有無
- strict 7 connector ledger
- loop summary CSV
- live AI review summary
```

実シグナルがまだ出ていなければ、GOLD側は監視継続でよい。

BTC側は、GOLD strict 7 の実地確認後に再開する。
