# TRADE_AI_REVIEW_JOURNAL_DESIGN

## 目的

GOLD/BTC のデモ口座シグナル・自動売買履歴を、単なる勝敗記録で終わらせず、次回以降の判断材料として使える **AI評価ジャーナル** にするための設計方針を残す。

この設計では、AIを「1件の負け理由を断定する裁判官」として使わない。
AIの役割は、各トレードに対して **それっぽい危険仮説タグを軽く付ける係** とする。

重要思想:

```text
1件の負けを重く見ない。
AI評価は断定ではなく仮説タグ付け。
似た仮説タグが複数件たまったら、初めて危険候補として見る。
危険候補は、勝ちトレードも含めたタグ別成績で検証する。
数字で悪いことが確認できるまでは、売買条件へ直接反映しない。
最初の反映先は自動停止ではなく Discord 警告にする。
```

---

## 背景

現在、デモ口座で以下のような GOLD/BTC シグナル・自動売買が動いている。

```text
GOLD:
  既存もちぽよGOLD
  新GOLD multi-strategy

BTC:
  GOLDとは別枠BAT・別ログ・別stateで動かす方針
```

GOLD側は、既存もちぽよGOLDと新GOLD multi-strategyを混ぜずに別枠で動かす構成になっている。
BTCもGOLDと無理に統合せず、別枠BAT・別ログ・別stateで扱う。

このAI評価ジャーナルも、既存の運用分離を壊さない。
各戦略の `order_key` / `payload_key` / `signal_key` / `strategy_id` / `condition_id` をできるだけ維持し、後追い評価で結合できるようにする。

---

## 基本方針

### 1. AIは断定しない

AI評価は以下を禁止する。

```text
この1件の負けだけで戦略が悪いと断定する。
この1件のAIコメントだけで売買条件を変更する。
entry後の値動きを見て、entry前から分かっていたかのように理由を作る。
負けトレードだけを見て、勝ちトレードとの比較なしに危険条件と決める。
```

AIの役割は以下に限定する。

```text
可能性のある危険タグを付ける。
チャート上の違和感を仮説としてメモする。
許容できる負けか、要注意の負けかを仮分類する。
execution問題かsignal問題かを分ける補助をする。
```

1件ごとのAI評価には、必ず以下の思想を含める。

```text
single_trade_warning = DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE
review_role = HYPOTHESIS_TAGGING_ONLY
```

---

### 2. 負けだけではなく勝ちも評価する

負けトレードだけをAIに見せると、AIはそれっぽい負け理由を作りやすい。
そのため、AI評価ジャーナルでは勝ちトレードも比較対象に含める。

対象方針:

```text
負けトレード:
  原則全件レビュー

勝ちトレード:
  原則レビュー対象
  件数が多すぎる場合はサンプリング可

建値・微益・微損:
  優先レビュー対象
  勝敗だけでは質を判断しづらいため
```

タグ集計では必ず以下を見る。

```text
タグ付き勝ち件数
タグ付き負け件数
タグ付き勝率
タグ付き平均R
タグ付きPF
タグなし勝率
タグなし平均R
全体勝率との差
全体平均Rとの差
```

「タグ付き負けが多い」だけでは危険判定しない。
タグ付きトレード全体の成績が悪いかを見る。

---

### 3. M15コンテキストは前100本・後20本を基本にする

当初案の M15 前20本・後20本では、前後約5時間しか見えず、GOLD/BTCの実運用評価には不足しやすい。

採用方針:

```text
M15:
  entry前 100本
  entry後 20本

M5:
  first-touch / MFE / MAE / TP/SL順序判定に必要な範囲

H1:
  entry前 50本〜100本

H4:
  entry前 30本〜60本

D1:
  entry前 20本〜40本
```

M15前100本は約25時間分に相当する。
これにより、以下を見やすくする。

```text
前日高値安値との位置
直近100本レンジ内のentry位置
直近トレンドの伸び切り
レンジ上限/下限
ブレイクの遅さ
押し戻り不足
高値掴み/安値売り
```

---

### 4. AIには生ローソク足だけでなくPython要約も渡す

M15前100本をそのままAIに渡すだけだと、情報量が多く評価がブレる可能性がある。
そのため、AI payloadにはローソク足データに加えて、Pythonで計算した要約特徴を必ず入れる。

M15要約例:

```text
pre_m15_bars = 100
post_m15_bars = 20
range_100_high
range_100_low
entry_position_in_range_100_pct
trend_20_direction
trend_50_direction
trend_100_direction
latest_swing_high_distance
latest_swing_low_distance
atr14_at_entry
signal_candle_range_atr_ratio
signal_candle_body_ratio
signal_candle_close_pos
ema20_distance_atr
ema50_distance_atr
ema200_distance_atr
macd_hist_at_entry
macd_hist_delta_at_entry
recent_large_candle_count
recent_breakout_count
```

AIはこの要約を主に読み、必要に応じてローソク足配列を見る。

---

## リーク禁止設計

AI評価では、entry前データとentry後データを明確に分ける。

```text
entry前データ:
  シグナル品質評価に使ってよい

entry後データ:
  結果説明、MFE/MAE、値動き確認にのみ使う
```

禁止:

```text
entry後に逆行した事実を見て、entry時点で明確に危険だったと断定する。
TP/SL結果を見てから、都合よく負け理由を作る。
未来の値動きを、entry時点で観測可能だった情報のように扱う。
```

AIプロンプトには、以下を明記する。

```text
You must separate pre-entry observable risk from post-entry outcome explanation.
Do not claim that a risk was obvious at entry unless it is supported by pre-entry features.
Post-entry bars may be used only to describe how the trade unfolded, not to invent pre-entry reasons.
```

---

## 出力ファイル設計

### 1. trade_outcome_ledger.csv

実際の勝敗・損益・R・決済理由など、Pythonで確定できる事実を保存する。

想定列:

```text
schema_version
created_at_utc
updated_at_utc
account_login
broker_symbol
symbol
strategy_key
strategy_alias
strategy_id
condition_id
router_strategy_slot
router_strategy_id
pair_name
candidate_rank
direction
lot
order_key
payload_key
signal_key
position_ticket
order_ticket
deal_ticket
entry_time
entry_price
sl_price
tp_price
close_time
close_price
profit
profit_points
profit_r
commission
swap
net_profit
outcome
close_reason
holding_minutes
mfe_points
mae_points
mfe_r
mae_r
max_adverse_before_max_favorable
spread_at_entry
slippage_entry
slippage_close
source_order_ledger_csv
source_mt5_history_csv
notes
```

`outcome` 例:

```text
WIN
LOSS
BREAKEVEN
SMALL_WIN
SMALL_LOSS
OPEN
UNKNOWN
```

`close_reason` 例:

```text
TP
SL
MANUAL_CLOSE
TIME_EXIT
BROKER_CLOSE
UNKNOWN
```

---

### 2. trade_feature_snapshot.csv / jsonl

AI評価前に、entry時点の特徴量・ローソク足要約を保存する。

想定内容:

```text
trade_id / order_key / payload_key
symbol / strategy_id / direction
entry_time / entry_price / sl_price / tp_price
M15前100本要約
M15後20本要約
H1/H4/D1環境
M5 first-touch情報
ATR/EMA/MACD/レンジ/高値安値距離
```

ローソク足配列そのものはCSVよりJSONLに向く。
必要に応じて以下のように分ける。

```text
trade_feature_snapshot.csv:
  集計しやすい数値特徴

trade_feature_snapshot.jsonl:
  AIに渡す詳細payload
```

---

### 3. trade_ai_review_ledger.jsonl

1件ごとのAI評価結果を保存する。
CSVではなくJSONLを基本にする。
タグ配列、メモ、理由、バージョン情報を保持しやすいため。

想定JSON:

```json
{
  "review_schema_version": "trade_ai_review_v1",
  "prompt_version": "trade_ai_review_prompt_v1",
  "tag_taxonomy_version": "trade_ai_tag_taxonomy_v1",
  "created_at_utc": "",
  "trade_id": "",
  "order_key": "",
  "payload_key": "",
  "symbol": "GOLD",
  "strategy_id": "",
  "direction": "BUY",
  "outcome": "LOSS",
  "profit_r": -1.0,
  "review_role": "HYPOTHESIS_TAGGING_ONLY",
  "single_trade_warning": "DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE",
  "pre_entry_quality_score": 0,
  "post_entry_explanation_score": 0,
  "possible_risk_tags": [],
  "possible_positive_tags": [],
  "execution_issue_tags": [],
  "system_issue_tags": [],
  "risk_category": "unclear_loss",
  "issue_category": "market_structure_issue",
  "avoidable_hypothesis": "unknown",
  "should_change_strategy_from_this_single_trade": false,
  "confidence": 0.0,
  "pre_entry_observable_reasons": [],
  "post_entry_outcome_explanation": [],
  "notes": ""
}
```

---

### 4. trade_ai_tag_summary.csv

複数件たまった後に、タグ別成績を集計する。

想定列:

```text
summary_schema_version
tag_taxonomy_version
symbol
strategy_key
strategy_id
tag_name
tag_group
tag_status
trade_count
win_count
loss_count
breakeven_count
win_rate
avg_r
total_r
profit_factor
max_losing_streak
tagged_vs_untagged_win_rate_diff
tagged_vs_untagged_avg_r_diff
overall_win_rate_diff
overall_avg_r_diff
min_sample_pass
should_investigate
investigation_reason
example_win_trade_ids
example_loss_trade_ids
last_seen_trade_time
created_at_utc
updated_at_utc
```

---

## タグの考え方

### タグ名は断定形にしない

避ける:

```text
loss_reason
確定負け理由
```

採用:

```text
possible_risk_tags
hypothesis_tags
possible_issue_tags
```

---

### 共通タグ / GOLD専用タグ / BTC専用タグを分ける

共通タグ例:

```text
entry_after_extended_move
m15_signal_candle_large
near_recent_high
near_recent_low
against_h1_context
against_h4_context
low_volatility_fake_break
high_volatility_chase
poor_pullback_structure
late_breakout
range_edge_entry
ema_distance_too_large
macd_late_signal
```

GOLD専用タグ例:

```text
gold_h1_reversal_zone
gold_london_ny_whipsaw
gold_news_like_spike
gold_fast_mean_reversion
gold_near_daily_key_level
```

BTC専用タグ例:

```text
btc_spread_sensitive
btc_weekend_thin_move
btc_fast_reversal_after_break
btc_slippage_sensitive
btc_low_liquidity_chop
btc_large_wick_reversal
```

execution/system系タグ例:

```text
wide_spread_at_entry
entry_slippage_large
close_slippage_large
order_price_mismatch
tp_sl_distance_invalid
duplicate_context
position_overlap_issue
mt5_execution_delay
missing_history_data
```

---

## タグステータス管理

タグには成長段階を持たせる。

```text
NEW:
  新しく出た仮説。
  件数が少なく、危険扱いしない。

WATCH:
  複数件で出てきた。
  まだ危険断定はしない。

SUSPECT:
  タグ付き成績が全体より悪い。
  検証候補。

CONFIRMED:
  過去データで仮バックテストしても悪い。
  フィルタ/ロット調整/警告強化の候補。

REJECTED:
  勝ちトレードにも多く、危険条件ではなさそう。
```

初期の判定目安:

```text
NEW:
  trade_count < 5

WATCH:
  trade_count >= 5

SUSPECT:
  trade_count >= 5
  かつ以下のいずれか:
    タグ付き勝率が全体勝率より10%以上悪い
    タグ付き平均Rが明確に悪い
    タグ付きPFが明確に悪い
    タグ付き最大連敗が目立つ

CONFIRMED:
  SUSPECT条件を満たし、さらに過去トレードへの仮フィルタ検証でも改善

REJECTED:
  タグ付き成績が悪くない
  または勝ちトレードにも同程度以上に出る
```

---

## 勝ち負けの質分類

単純な勝ち負けだけでなく、勝ち方・負け方も分ける。

```text
good_win:
  きれいに伸びて勝った
  MAEが小さく、MFEが素直に伸びた

bad_win:
  勝ったが危なかった
  大きく逆行してからTP
  たまたま助かった可能性あり

good_loss:
  形は悪くないが通常の負け
  戦略上許容できる負け

bad_loss:
  形も悪く、改善候補になり得る負け

unclear:
  判断困難
```

`bad_win` は特に重要。
今は勝っていても、将来崩れる条件の候補になる可能性がある。

---

## 負け分類

負けをすべて改善対象にしない。

```text
acceptable_loss:
  戦略上ありえる普通の負け
  直ちに改善対象にしない

bad_loss:
  条件・形・環境に問題がありそうな負け

unclear_loss:
  まだ判断不能

system_error_loss:
  システム/データ/発注処理由来の負け

execution_loss:
  スプレッド、滑り、約定遅延など実行由来の負け
```

`acceptable_loss` を明示的に持つ理由:

```text
全ての負けを直そうとすると過剰フィルタになる。
良い戦略でも普通に負けは出る。
直すべき負けと許容する負けを分ける必要がある。
```

---

## issue_category 分類

AI評価では、問題の種類を分ける。

```text
signal_quality_issue:
  シグナル条件そのものの問題

market_structure_issue:
  レンジ、上位足、直近高値安値、伸び切りなど相場構造の問題

execution_issue:
  スプレッド、滑り、約定タイミングなどの問題

risk_setting_issue:
  SL/TP距離、RR、ロット、保有時間などの問題

system_issue:
  データ欠損、重複、発注不整合、ledger不整合などの問題

unclear:
  判断困難
```

この分類を入れる理由:

```text
シグナル条件を直すべきではない負けまで、シグナル改善候補に混ざるのを防ぐ。
```

---

## 人間メモ / override

AI評価だけで完結させない。
ユーザーの肌感覚・手動確認を残す欄を必ず用意する。

想定列:

```text
human_review_status
human_review_note
human_override_tags
human_issue_category_override
human_loss_class_override
human_checked_at
```

`human_review_status` 例:

```text
UNREVIEWED
AGREE_WITH_AI
DISAGREE_WITH_AI
PARTIAL_AGREE
MANUAL_TAGGED
IGNORE
```

この欄により、以下を後から補正できる。

```text
AIの見立てと違う
指標っぽい
単純にエントリーが遅い
許容できる負け
シグナルではなく約定問題
```

---

## Discord通知への反映方針

初期段階では、AI評価結果で自動売買を止めない。
まずはDiscord通知に履歴警告として出す。

通知例:

```text
AI履歴警告:
- entry_after_extended_move: 過去12件 / 勝率33% / 平均R -0.41 / status=SUSPECT
- near_h1_resistance: 過去8件 / 勝率37% / 平均R -0.22 / status=WATCH

判定:
  送信は通常通り
  ただし注意タグあり
```

段階:

```text
Phase 1:
  記録だけ

Phase 2:
  Discord警告だけ

Phase 3:
  危険タグが強い場合にlotを下げる案を検討

Phase 4:
  バックテストで確認済みのCONFIRMEDタグのみ、フィルタ化を検討
```

---

## フィルタ候補の採用ルール

AIタグ集計だけで売買条件を変更しない。
フィルタ候補は必ず仮バックテストする。

検証項目:

```text
除外前 trades
除外後 trades
除外前 total R
除外後 total R
除外前 PF
除外後 PF
除外前 max DD
除外後 max DD
月別 trades / win_rate / total R / PF
戦略別成績
GOLD/BTC別成績
```

採用候補にできる条件:

```text
SUSPECTタグである
十分な件数がある
過去トレードで除外検証して改善がある
月別で過剰最適化に見えない
トレード数が減りすぎない
```

---

## バージョン管理

AIプロンプトやタグ定義を変えると、昔の評価と新しい評価が混ざる。
そのため、以下を必ず保存する。

```text
review_schema_version
prompt_version
tag_taxonomy_version
feature_snapshot_version
outcome_ledger_schema_version
```

目的:

```text
後から集計したときに、どの基準で付けたタグか分かるようにする。
プロンプト変更前後でタグ成績を混ぜないようにする。
```

---

## 既存システムとの接続方針

### 使用する主キー候補

```text
order_key
payload_key
signal_key
strategy_id
condition_id
broker_symbol
entry_time
order_ticket
deal_ticket
position_ticket
```

原則:

```text
order_key / payload_key を最優先
MT5履歴側とは order_ticket / deal_ticket / position_ticket で結合
不足する場合は symbol + direction + time proximity で補助結合
```

### GOLD既存もちぽよ

想定入力:

```text
data/results/mochipoyo/minimal_live_once_test/gold_notification_ledger.csv
data/mt5_demo_order_test/goldsharp_auto_trade_demo_prod_order_ledger.csv
data/runtime_logs/gold/YYYY/MM/week_XX/mochipoyo_gold/loop/gold_minimal_live_loop_live_summary.csv
```

### GOLD multi-strategy

想定入力:

```text
data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv
data/runtime_logs/gold/YYYY/MM/week_XX/multi_strategy_gold/loop/aligned_loop_log.csv
data/runtime_logs/gold/YYYY/MM/week_XX/multi_strategy_gold/loop/latest_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_result.json
```

### BTC

想定入力:

```text
data/runtime_state/btc/.../guarded_demo_order_ledger.csv
data/runtime_logs/btc/YYYY/MM/week_XX/.../loop/*.csv
data/runtime_logs/btc/YYYY/MM/week_XX/.../loop/latest_*.json
```

---

## 実装ステップ案

### Step 1: 決済済みトレード履歴の取得

```text
scripts/export_mt5_closed_trade_history.py
```

目的:

```text
MT5のhistory_deals_get / history_orders_getから、決済済みトレード履歴をCSV出力する。
```

---

### Step 2: outcome ledger作成

```text
scripts/build_trade_outcome_ledger_from_order_ledger.py
```

目的:

```text
order ledger と MT5履歴を結合し、trade_outcome_ledger.csv を作る。
```

---

### Step 3: feature snapshot作成

```text
scripts/build_trade_feature_snapshots.py
```

目的:

```text
各トレードのentry時点を基準に、M15前100本・後20本、H1/H4/D1、M5 first-touchを集める。
```

---

### Step 4: AI review payload作成

```text
scripts/build_trade_ai_review_payloads.py
```

目的:

```text
AIに渡すJSONL payloadを作る。
entry前情報とentry後情報を明確に分離する。
```

---

### Step 5: AIレビュー実行

```text
scripts/run_trade_ai_review_from_payloads.py
```

目的:

```text
OpenAI APIで1件ずつ仮説タグを付け、trade_ai_review_ledger.jsonl に保存する。
```

---

### Step 6: タグ集計

```text
scripts/summarize_trade_ai_review_ledger.py
```

目的:

```text
タグ別の勝率、平均R、PF、件数、危険候補判定を出す。
```

---

### Step 7: Discord警告連携

既存のシグナル通知時に、過去のタグ成績を参照して警告を出す。

```text
まずは自動売買停止には使わない。
注意喚起のみ。
```

---

## 禁止事項

```text
1件のAI評価だけで売買条件を変更しない。
負けトレードだけを見てタグを危険断定しない。
勝ちトレードとの比較なしにフィルタ化しない。
entry後の値動きをentry前の根拠として扱わない。
AIの自由文だけを根拠にしない。
タグのバージョンを保存せずに集計しない。
GOLD/BTCや戦略別の違いを無視してタグを一括評価しない。
execution_issueをsignal_quality_issueとして扱わない。
許容できる負けまで全て排除しようとしない。
初期段階で自動売買を止める判定に使わない。
```

---

## 現時点の結論

この設計は、以下の思想で進める。

```text
AIは裁判官ではなく、付箋を貼る係。
1件の負けではなく、似た仮説タグの蓄積を見る。
負けだけでなく勝ちも比較する。
M15は前100本・後20本を基本にする。
リークを防ぎ、entry前評価とentry後説明を分ける。
人間メモとoverrideを残す。
約定問題とシグナル問題を分ける。
まずは記録とDiscord警告。
フィルタ化は、タグ別成績と仮バックテストで確認してから。
```

この方針により、AI評価を実運用に近い形で安全に蓄積し、GOLD/BTCの次回以降の判断材料として使えるようにする。
