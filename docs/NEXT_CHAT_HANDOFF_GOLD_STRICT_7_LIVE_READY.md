# NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY

Last updated: 2026-05-21

この文書は、GOLD strict 7 の現状を次チャットへ引き継ぐためのメモです。

> 重要: 2026-05-21後半に、GOLD/BTC Discord通知の毎分重複通知、AIタグの勝ち/負けバランス、EA/BATタイミング、GOLD shallow SL探索について追加整理した最新版ハンドオフを作成済みです。通知重複・AIタグ・SL探索の話を続ける場合は、まず以下を読むこと。
>
> ```text
> docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
> ```

---

## 1. 現在のステータス

GOLD側は、strict 7 の候補を中心に以下の構成まで整理済みです。

```text
- シグナル検出
- Discord通知
- guarded demo connector
- post-trade AI review
- backtest AI review と live AI review の分離
- 通知時 numeric AI tag 推定
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
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
docs/REPOSITORY_CLEANUP_AND_DEPRECATION_POLICY.md
```

この文書:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
```

BTC側の現状:

```text
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
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

通知時AIタグ推定:

```text
scripts/ai_tag_numeric_rule_utils.py
scripts/gold_strict_7_signals/build_gold_strict_7_ai_tag_numeric_rules.py
scripts/build_gold_strict_7_ai_tag_numeric_rules.bat
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

注: この節の旧記述には `run_delay_seconds: 2` が残っていましたが、2026-05-21後半の見直し後はEA `InpExportSecond=2`、BAT側 `+5秒` が推奨です。詳細は最新版ハンドオフを参照してください。

```text
最新参照:
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
```

---

## 6. Ledger と出力先

Discord通知ledger:

```text
data/runtime_state/gold/strict_7/discord_notification_ledger.csv
```

Discord通知 seen-state JSON:

```text
data/runtime_state/gold/strict_7/discord_notification_seen_keys.json
```

strict 7 connector ledger:

```text
data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv
```

AI tag numeric rules:

```text
data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json
data/runtime_state/gold/strict_7/ai_tag_numeric_rules_summary.csv
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

## 7. 通知時 AIタグ推定

注: 2026-05-21後半に、AIタグは「負けタグ警告」だけでなく、勝ち側に寄った `✅ 好材料`、勝ちにも出るため強警告にしない `参考注意` を含む表示へ更新済みです。詳細は最新版ハンドオフを参照してください。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
```

---

## 8. AI評価の扱い

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
- 通知時AIタグ推定はOpenAIを呼ばない。
```

---

## 9. backtest AI review 初回結果

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

## 10. まだ実地確認が必要なこと

次に確認すべきこと:

```text
1. Discord通知が毎分監視で遅れず届くか
2. 同じM5足でGOLD通知が再通知されず skipped_duplicates になるか
3. 通知本文にAIタグ推定欄が出るか
4. summaryで ai_tag_rules_cycle_ok: true になるか
5. strict 7 connector ledger が想定通り残るか
6. 既存sender側のチェック結果がsummaryに残るか
7. 完了後、live AI reviewが新規分だけ拾うか
8. 2回目live AI reviewで同じIDがスキップされるか
9. loop summaryのelapsed_secondsが十分短いか
10. EAのCSV書き出し時刻とPython検出時刻のズレが許容範囲か
```

見るsummary列:

```text
elapsed_seconds
ctx_rows
raw_recent_signals_after_cooldown
preview_rows
ai_tag_hit_rows
ai_tag_rules_count
ai_tag_rules_cycle_ok
payload_rows
reason
pending_rows
skipped_already_reviewed_rows
review_rows_written_this_run
duplicate_guard_mode
seen_state_json
skipped_duplicates
ledger_rows_appended
seen_state_error_rows
```

---

## 11. 次チャットで続ける場合

次チャットでは、まずこの文書と以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```
