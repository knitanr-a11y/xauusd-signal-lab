# NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521

Last updated: 2026-05-21

この文書は、2026-05-21時点で実施した以下の内容を、次チャットへ正確に引き継ぐための最新版メモです。

```text
- GOLD strict7 / BTC strict5 official の通知タイミング調整
- GOLD strict7 の浅いSL探索結果
- GOLD AIタグの負けタグ/勝ちタグの見直し
- GOLD/BTC Discord通知の毎分重複通知問題とhotfix
- 現時点での運用確認ポイント
```

---

## 1. 最重要結論

### GOLD strict7 のSLは現行維持

GOLD strict7では、浅いSLを深くする探索を実施した。

結論:

```text
SLを深くすると勝率は少し上がるが、PF / Total R が大きく低下する。
したがって、現時点ではGOLD strict7のSLは変更しない。
```

特に `BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5` は、SLを深くしても勝率改善が弱く、Total Rの悪化が大きかったため現行維持。

`SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5` は SL10 も妥協案としてはあり得たが、PF/Total Rでは現行SL7.5が最良だったため、こちらも現行維持。

### EA/BATタイミング

EA側:

```text
InpExportSecond = 2 推奨
```

GOLD/BTC通知・自動売買BAT側:

```text
run-delay / offset = +5秒
```

対象:

```text
GOLD strict7 Discord通知: +5秒
GOLD strict7 guarded demo autotrade: +5秒
BTC strict5 official Discord通知: +5秒
BTC strict5 guarded demo send: +5秒
```

理由:

```text
EAが+2秒でCSVを書き、Pythonが+5秒で読むことで約3秒の余裕を確保する。
0秒/1秒ぴったり取得はMT5 OnTimerや新バーtick依存で1分遅れや更新前読込の原因になる。
```

---

## 2. GOLD AIタグの最新方針

### 旧問題

以前のAIタグは、実質的に以下の見え方だった。

```text
負けタグらしきものがHIT
  -> ⚠️ 注意
```

しかし監査の結果、負けタグとして付いたものでも、勝ちトレードにも普通に出ているタグがあった。

そのため、単純に「負けタグ = 悪い」と扱うと、勝ちパターンまで過剰警告するリスクがあった。

### 新方針

AIタグ通知は以下の分類で表示する。

```text
✅ 好材料
  勝ちトレードに寄っているタグ。

好材料候補
  勝ち寄りだがサンプルや安定性はまだ確認中。

⚠️ 強め注意
  負け側に明確に偏っているタグ。

注意
  やや負け寄りのタグ。

参考注意
  気になるが、勝ちにも出るため強警告にしないタグ。

参考
  サンプル不足、または弱い材料。
```

通知例:

```text
AIタグ: ✅ 好材料 1件 / ⚠️ 強め注意 1件 / 参考注意 2件
判定: 評価可 18/24・特徴不足 6・HIT 4

- ✅ 好材料: GOLD短期反発の形（gold_fast_mean_reversion） / タグ実績avgR=11.23 / 勝率=78%
- ⚠️ 強め注意: 高ボラ追いかけ気味（high_volatility_chase） / タグ実績avgR=-0.78 / 勝率=10%
- 参考注意: 伸びた後のエントリー（entry_after_extended_move） / 勝ちにも出るため参考扱い

注: AIタグは過去レビュー類似の注意/好材料ラベルで、勝敗確定ではありません。
```

### 最新AIタグJSONの確認結果

ユーザーが貼った `data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json` は新形式で生成済み。

確認済み内容:

```text
schema_version: gold_strict_7_ai_tag_numeric_rules_v3_positive_balance_audit
cycle_ok: true
rules_count: 173
tag_balance_audit_rows: 157
```

内訳の目安:

```text
risk系ルール: 135
positive系ルール: 38
好材料: 29
好材料候補: 5
強め注意: 12
注意: 61
参考注意: 50
参考: 16
```

重要:

```text
- tag_role: positive が入っている
- display_level_suggestion: 好材料 が入っている
- verdict: not_loss_specific_also_on_wins が入っている
```

したがって、GOLD AIタグJSON自体はOK。

### 関連スクリプト

共有ユーティリティ:

```text
scripts/ai_tag_numeric_rule_utils.py
```

GOLD AIタグ監査:

```text
scripts/gold_strict_7_signals/audit_gold_strict_7_ai_tag_win_loss_balance.py
```

GOLD AIタグ生成:

```text
scripts/gold_strict_7_signals/build_gold_strict_7_ai_tag_numeric_rules.py
scripts/build_gold_strict_7_ai_tag_numeric_rules.bat
```

GOLD AIタグ生成パッチャー:

```text
scripts/gold_strict_7_signals/apply_ai_tag_positive_balance_patch.py
```

---

## 3. Discord通知が毎分来続けた問題

### 発生した問題

GOLD Discord通知で、シグナル検出後、新しいローソク足が出るまで毎分通知が来続けた。

自動売買は毎分されなかった。

理由:

```text
自動売買側は order ledger / position guard で重複発注を防いでいた。
一方、Discord通知側は CSV ledger 依存で、同じ足の再通知を完全には止めきれていなかった。
```

### 原因

GOLD通知本体は当初、以下の構造だった。

```text
notification_key = GOLD|STRICT7|strategy|direction|close_time
重複判定 = discord_notification_ledger.csv のみ
ledger追記 = 最後にまとめてappend
```

このため、以下の条件で同じシグナルが毎分通知され得る。

```text
- ledger追記が次ループに見えない
- ledger追記前に落ちる
- close_timeが同一M5足内で微妙にズレる
- 同じシグナルが新しいM5足まで検出され続ける
```

BTC official Discord通知にも同じ構造のリスクがあった。

### hotfix方針

GOLD:

```text
notification_key の時刻を 5分足bucket に固定
CSV ledger + JSON seen_state の二重重複ガード
Discord送信成功直後に即時ledger追記
Discord送信成功直後にseen_state JSONへ即時保存
```

BTC:

```text
notification_key の時刻を 15分足bucket に固定
CSV ledger + JSON seen_state の二重重複ガード
Discord送信成功直後に即時ledger追記
Discord送信成功直後にseen_state JSONへ即時保存
```

### hotfix適用スクリプト

```text
scripts/apply_gold_btc_discord_duplicate_guard_hotfix.py
```

実行ログでは、GOLD/BTCともに以下まで成功済み。

```text
[OK] GOLD patched and verified
[OK] BTC patched and verified
[DONE] GOLD/BTC Discord duplicate guard hotfix applied. Restart Discord notification BATs.
```

### GitHub反映状況

ユーザーが本体ファイルを1つずつpush済み。

GitHub上で以下を確認済み。

GOLD:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notifier_from_csv.py
SCHEMA_VERSION = gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard
DEFAULT_SEEN_STATE_JSON = data/runtime_state/gold/strict_7/discord_notification_seen_keys.json
notification_key uses 5min bucket
load_notified_keys + load_seen_state_keys
append_ledger_row_durable
mark_seen_state_key
```

BTC:

```text
scripts/btc_strict_5_signals/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py
SCHEMA_VERSION = btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard
DEFAULT_SEEN_STATE_JSON = data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_seen_keys.json
notification_key uses 15min bucket
load_notified_keys + load_seen_state_keys
append_ledger_row_durable
mark_seen_state_key
```

### 注意: 現在の本体には軽微な重複行あり

複数回のローカルパッチ適用の影響で、以下の軽微な重複が残っている。

GOLD:

```text
notification_bucket_time_text が2回定義されている
print(seen_state_json) が2回出る
summary内で ledger_append_error_rows / ledger_append_errors が重複
safety内で seen_state_duplicate_guard_enabled / notification_key_uses_5min_candle_bucket が重複
```

BTC:

```text
summary内で ledger_append_error_rows / ledger_append_errors が重複
```

実害:

```text
同名関数は後の定義で上書きされる。
summaryの同じキーは同値のため大きな実害はない。
重複通知防止の中核処理には影響しない見込み。
```

ただし、後で本体2ファイルを整理して重複行を除去した方がよい。

---

## 4. 現在の運用確認手順

### 1. 古い通知BATを止める

修正前のプロセスは古い本体を読み続けるため、必ず停止する。

### 2. 通知BATを再起動

GOLD:

```text
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notify_forever_aligned.bat
```

BTC:

```text
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat
```

### 3. summaryで確認する項目

GOLD:

```text
schema_version: gold_strict_7_discord_notifier_v9_candle_bucket_duplicate_guard
duplicate_guard_mode: ledger_csv_plus_seen_state_json_plus_5min_candle_bucket_key
seen_state_json: data/runtime_state/gold/strict_7/discord_notification_seen_keys.json
seen_state_duplicate_guard_enabled: true
notification_key_uses_5min_candle_bucket: true
skipped_duplicates
ledger_rows_appended
seen_state_error_rows
```

BTC:

```text
schema_version: btc_strict_5_official_discord_notifier_numeric_ai_tags_v5_m15_bucket_duplicate_guard
duplicate_guard_mode: ledger_csv_plus_seen_state_json_plus_15min_candle_bucket_key
seen_state_json: data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_seen_keys.json
seen_state_duplicate_guard_enabled: true
notification_key_uses_15min_candle_bucket: true
skipped_duplicates
ledger_rows_appended
seen_state_error_rows
```

### 4. 期待挙動

GOLD:

```text
同じM5足の同じstrategy/directionは1回だけ通知。
次ループ以降は skipped_duplicates が増える。
```

BTC:

```text
同じM15足の同じstrategy/direction/filter_variantは1回だけ通知。
次ループ以降は skipped_duplicates が増える。
```

---

## 5. 残課題

### A. Discord通知本体のクリーンアップ

GOLD/BTC通知本体は、hotfixの止血は入ったが、重複行が残っている。

落ち着いたら以下を整理する。

```text
scripts/gold_strict_7_signals/run_gold_strict_7_discord_notifier_from_csv.py
scripts/btc_strict_5_signals/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py
```

整理内容:

```text
- notification_bucket_time_text の重複定義削除
- seen_state_json print重複削除
- summary重複キー削除
- cycle_ok / return code に seen_state_errors も含める
- apply_gold_btc_discord_duplicate_guard_hotfix.py は将来的に不要なら削除またはarchive
```

### B. AIタグ表示の実通知確認

次回GOLD通知で確認すること。

```text
AIタグ: ✅ 好材料 / ⚠️ 強め注意 / 参考注意 / 参考
判定: 評価可 x/y・特徴不足 z・HIT n
```

が出るか確認。

### C. GOLD/BTCとも、実シグナル時に1回通知で止まるか確認

```text
GOLDはM5単位
BTCはM15単位
```

で重複が止まることを確認する。

### D. 価格ズレ/浅いSL監視

SLは変更しない方針だが、GOLDの浅いSL戦略では、通知時点の価格ズレやSL残距離を将来的に通知へ出すとよい。

対象優先:

```text
BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5
SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5
SELL_KC_CCI150_LONDON_TP100_SL10
BUY_SWEEP_RECLAIM_RSI_TP150_SL10
BUY_STOCH_BB_KTURN_NY_TP150_SL10
```

---

## 6. 次チャットで最初に見るファイル

```text
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```

特に、通知重複やAIタグの話を続ける場合は、この文書を最優先で読む。
