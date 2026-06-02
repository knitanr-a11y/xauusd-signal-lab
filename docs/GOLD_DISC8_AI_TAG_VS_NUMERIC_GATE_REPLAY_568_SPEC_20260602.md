# GOLD DISC8 AIタグSOT vs numeric gate replay 568 仕様書（2026-06-02）

## 目的

過去AIレビュー済み568件をsource of truthとして、実AIタグのgroup_tag_filter結果と、既存numeric gate rulesの再現結果がどこでズレているかを監査する。

この実装は原因分析専用であり、runtime gate rulesへの昇格、Discord送信、MT5発注、OpenAI API呼び出し、SOT更新、live decision ledger更新は行わない。

## source of truth

この監査ではOHLCから568件を再検出しない。以下の既存ファイルだけをsource of truthとして読む。

| 種別 | 入力ファイル | 用途 |
|---|---|---|
| AI review ledger | `data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_ai_review_ledger.jsonl` | 実AIレビューのタグ抽出元 |
| trade feature snapshot | `data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_feature_snapshot.csv` | 568件へnumeric ruleを当てるpre-entry feature |
| base 568 outcome sample | `data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/disc8_review_trade_outcome_sample.csv` | AIレビュー済み568件の取引母集団、`trade_id`、`strategy_id`、`entry_time`、`direction`、`profit_r_num/profit_r` |
| frozen kept SOT | `data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_ledger.csv` | group_tag_filter後に残った取引。base 568のうちここにある`trade_id`をAI_ALLOW、ない`trade_id`をAI_BLOCKと定義する |
| original group tag gate rules | `data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json` | 実AIタグのblock/watch対象tag定義 |
| numeric rules | `data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_rules.json` | 既存numeric gate再現rule。新規生成しない |
| tag recall summary | `data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv` | `--promotable-only`時の対象tag制限 |

## AI_BLOCK / AI_ALLOW定義

既存group_tag_filterの結果をそのままSOTにする。

- `base 568 trade_id` が frozen kept SOT に存在する: `AI_ALLOW` / `truth_label=actual_kept`
- `base 568 trade_id` が frozen kept SOT に存在しない: `AI_BLOCK` / `truth_label=actual_blocked`

AIタグの名前や文章から近似判定しない。SOT ledgerのmembershipだけで判定する。

## numeric gate定義

既存の `gold_disc8_ai_tag_numeric_tagger_rules.json` を読む。新しいrule探索・再生成はしない。

適用前に `gold_disc8_feature_contract_bridge.filter_pre_entry_rules()` を通し、`mfe/mae/post_entry/after_entry`など未来・post-entry疑いのfeature ruleを除外する。

`--promotable-only` が有効な場合は、既存 `tag_recall_summary.csv` の `POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW` tagだけを対象にする。

- block ruleに1件以上hit: `numeric_gate_decision=BLOCK`, `numeric_binary=NUMERIC_BLOCK`
- watch ruleのみhit: `numeric_gate_decision=WATCH_ONLY`, `numeric_binary=NUMERIC_ALLOW`
- hitなし: `numeric_gate_decision=ALLOW_NUMERIC_AUDIT_ONLY`, `numeric_binary=NUMERIC_ALLOW`

## 4分類

各取引を以下に分類する。

| classification | 意味 |
|---|---|
| `AI_BLOCK_AND_NUMERIC_BLOCK` | 実AIタグfilterもnumeric gateもBLOCK |
| `AI_BLOCK_AND_NUMERIC_ALLOW` | 実AIタグfilterではBLOCKだがnumeric gateでは非BLOCK |
| `AI_ALLOW_AND_NUMERIC_BLOCK` | 実AIタグfilterではALLOWだがnumeric gateではBLOCK |
| `AI_ALLOW_AND_NUMERIC_ALLOW` | 実AIタグfilterもnumeric gateも非BLOCK |

## 監査対象キー

- `trade_id`: 568件SOT照合キー
- `strategy_id`: strategy別集計キー
- `entry_time`: 月別集計、時系列監査キー
- `direction`: BUY/SELL確認用
- `TP/SL`: この監査では再計算しない。base/outcome sampleに存在する場合のみ出力側で参照可能。成績は既存`profit_r_num/profit_r`をsource of truthとして使う。
- `outcome`: 既存`profit_r_num/profit_r`からWIN/LOSS/FLAT_OR_UNRESOLVEDを導出する。M5から再判定しない。

## 期待件数と停止条件

期待件数:

- `base_trade_rows = 568`
- `numeric_rules_json` のrulesが1件以上存在すること
- `gate_rules_json` から対象tagが1件以上読めること
- `trade_id`, `strategy_id`, `entry_time`, `direction`, `profit_r_num/profit_r` が監査可能であること

停止条件:

- 必須入力ファイルが存在しない
- base trade rowsが568件でない（BAT既定）
- `trade_id` が欠落している
- 成績R列が欠落している
- gate target tagまたはnumeric ruleが0件
- 未来/post-entry除外後のnumeric ruleが0件

停止時も、可能な限り `input_file_audit.csv`、`column_audit.csv`、`summary.json` を出力する。

## 出力

出力先:

`data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/`

run別:

`data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/runs/<run_id>/`

latest snapshot:

`data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/latest/`

出力ファイル:

| ファイル | 内容 |
|---|---|
| `gold_disc8_ai_tag_vs_numeric_gate_input_file_audit.csv` | 入力ファイル存在、行数、カラム監査 |
| `gold_disc8_ai_tag_vs_numeric_gate_column_audit.csv` | 重要カラム監査 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv` | 568件ごとのAI判定、numeric判定、4分類、R、tag |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_numeric_rule_hits.csv` | numeric rule hit明細 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_rule_eval_audit.csv` | numeric rule評価明細 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_overall_summary.csv` | 全体confusion×成績 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_monthly_summary.csv` | 月別confusion×成績 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_strategy_summary.csv` | strategy別confusion×成績 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_tag_trade_audit.csv` | tag×trade明細 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_tag_summary.csv` | tag別confusion×成績 |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_tag_recall_summary.csv` | AI tag vs numeric hitのprecision/recall |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_568_excluded_future_rules.csv` | 除外した未来/post-entry rule |
| `gold_disc8_ai_tag_vs_numeric_gate_replay_summary.json` | safety flags、件数、classification metrics、出力パス |

## 実装ファイル

- script: `scripts/gold_disc8/audit_gold_disc8_ai_tag_vs_numeric_gate_replay_568.py`
- BAT: `scripts/gold_disc8/run_gold_disc8_ai_tag_vs_numeric_gate_replay_568.bat`

## 実行順序

1. `scripts\gold_disc8\run_gold_disc8_ai_tag_vs_numeric_gate_replay_568.bat`
2. `data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_summary.json` を確認
3. `overall_summary.csv`、`strategy_summary.csv`、`tag_summary.csv`、`tag_recall_summary.csv` を確認
4. 特に以下を確認する
   - `AI_BLOCK_AND_NUMERIC_ALLOW`: numericが取り逃がしたAI_BLOCK
   - `AI_ALLOW_AND_NUMERIC_BLOCK`: numericが利益を捨てる誤BLOCK
   - `strategy_id`別にDISC_11 SELLなどだけ有効か
   - BUY側`against_h4_context`等が利益を捨てていないか

## 成功条件

- `cycle_ok=true`
- `base_trade_rows=568`
- `dispatch_ready_rows=0`
- `no_ai_api_call=true`
- `no_discord_send=true`
- `no_mt5_order_send=true`
- `sot_mutated=false`
- `runtime_gate_rules_mutated=false`
- `live_decision_ledger_mutated=false`
- 4分類の合計が568件

## 実行してはいけないこと

- OpenAI API評価
- Discord送信
- MT5発注
- runtime gate rulesへの昇格
- SOT更新
- live decision ledger更新
- OHLCから568件を再検出すること
- `review-target all` や上限なしAI評価の追加
