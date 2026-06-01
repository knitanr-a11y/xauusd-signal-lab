# GOLD DISC8 group-tag filtered selection freeze spec

作成日: 2026-06-01

## 目的

DISC8 のAIタグ SAFE フィルタ適用後のトレード集合を、新しい source of truth として固定する。

これ以降、通知候補・追加監査・次段階の実装は、未フィルタの DISC8 ではなく、以下の固定出力を参照する。

```text
data/gold_disc8/selected/
```

## 入力

SAFEフィルタ適用後の成果物を入力とする。

```text
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_after_group_tag_filter_trade_ledger.csv
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_blocked_by_group_tag_filter_trade_ledger.csv
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_after_group_tag_filter_strategy_summary.csv
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_after_group_tag_filter_monthly_summary.csv
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_group_tag_filter_rule_hit_summary.csv
data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_group_tag_filter_audit.json
data/gold_disc8/config/disc8_ai_group_tag_filter_rules_20260531.json
```

## 出力

```text
data/gold_disc8/selected/selected_disc8_group_tag_filtered_strategies.csv
data/gold_disc8/selected/group_tag_filtered_source_trade_ledger.csv
data/gold_disc8/selected/group_tag_filtered_blocked_trade_ledger.csv
data/gold_disc8/selected/group_tag_filtered_monthly_summary.csv
data/gold_disc8/selected/group_tag_filtered_strategy_summary.csv
data/gold_disc8/selected/group_tag_filter_rule_hit_summary.csv
data/gold_disc8/selected/group_tag_filtered_selection_audit.json
```

## 成功条件

SAFE監査値を満たすこと。

```text
input_trade_rows = 568
kept_trade_rows = 292
blocked_trade_rows = 276
configured_rule_rows = 21
active_rule_rows = 21
blocking_rule_rows = 18
watch_only_rule_rows = 3
profile = safe
```

また、固定後の選定戦略数は8、月数は6、AI API・MT5・Discordは未使用でなければならない。

## 停止条件

以下の場合は停止する。

```text
SAFEフィルタ監査JSONが無い
SAFE適用後トレード台帳が無い
kept_trade_rows と source trade ledger 行数が一致しない
blocked_trade_rows と blocked ledger 行数が一致しない
strategy_id が8つ揃わない
htf_no_future_ok が false の行がある
AI API / MT5 / Discord を呼ぶ必要がある処理になっている
```

## API使用

```text
OpenAI API: 使用しない
MT5 order_send: 使用しない
Discord送信: 使用しない
```

## 備考

この固定化は、AIタグSAFEフィルタを source of truth に昇格するための監査用ステップであり、AIタグ名を直接EAへ実装する最終ステップではない。

次段階では、`selected_disc8_group_tag_filtered_strategies.csv` と `group_tag_filtered_source_trade_ledger.csv` を基準に、実運用通知・再現検証・必要に応じた数値ルール化を行う。
