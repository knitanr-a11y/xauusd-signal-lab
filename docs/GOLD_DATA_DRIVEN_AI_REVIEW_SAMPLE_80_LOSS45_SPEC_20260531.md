# GOLD data-driven DISC8 AI評価サンプル 80/LOSS45 仕様書

作成日: 2026-05-31
対象: data-driven DISC8 / AIタグ評価サンプル作成

## 1. 目的

`DISC_*` 8条件のAIタグ評価用サンプルを作る。

今回のAI評価の目的は、勝率やPFを再計算することではなく、以下を把握すること。

- 各DISC条件が負けるときの事前特徴
- 勝ちと負けの違い
- 危険タグ候補
- 通知時に注意表示すべき局面
- 後段のルール改善・ロット調整・回避条件の材料

## 2. AI API

この仕様でまず作るものは **audit-only / sample CSV作成のみ**。

```text
AI API: 呼ばない
OpenAI API key: 不要
MT5 order_send: なし
Discord送信: なし
```

AI評価BATは、サンプルCSVの監査が通ってから別途作る。

## 3. source of truth

### 3.1 DISC8条件定義

```text
docs/GOLD_DATA_DRIVEN_DISC8_CONDITION_DEFINITIONS_20260531.md
data/gold_specialist_8/config/disc8_static_rule_definitions_20260531.json
```

この8条件を唯一のDISC8定義とする。

### 3.2 trade ledger

前回の固定再バックテスト出力に含まれる以下をsource ledgerとする。

```text
static_rule_trade_ledger.csv
```

想定配置例:

```text
data/gold_specialist_8/verification/data_driven_static_rebacktest/static_rule_trade_ledger.csv
```

または、BAT/スクリプト引数 `--trade-ledger-csv` で明示する。

## 4. 対象シグナル

対象は以下の8条件のみ。

```text
DISC_01_BUY_TP200_SL100_RR2
DISC_02_BUY_TP80_SL50_RR1p6
DISC_04_BUY_TP150_SL100_RR1p5
DISC_05_BUY_TP80_SL50_RR1p6
DISC_06_SELL_TP80_SL50_RR1p6
DISC_08_BUY_TP200_SL100_RR2
DISC_09_BUY_TP80_SL50_RR1p6
DISC_11_SELL_TP80_SL50_RR1p6
```

## 5. サンプル抽出ルール

各シグナルごとに最大80件。

```text
max_per_strategy: 80
max_loss_per_strategy: 45
max_non_loss_per_strategy: 35
max_total: 640
```

抽出対象:

- LOSS系: `outcome == LOSS` または `profit_r < 0`
- non-loss系: `profit_r >= 0` かつAI評価可能な結果

優先:

- 月別にできるだけ偏らせない
- train/test両方を含める
- quick lossだけに偏らせない
- 可能なら通常負け・速い負け・長時間負けを混ぜる
- deterministic / 再実行しても同じサンプルになる

## 6. 出力

出力先:

```text
data/gold_specialist_8/verification/ai_review_data_driven/sample_80_loss45/YYYY/MM/YYYYMMDD_HHMMSS/
```

latest copy:

```text
data/gold_specialist_8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45.csv
data/gold_specialist_8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45_summary_by_strategy.csv
data/gold_specialist_8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45_monthly_distribution.csv
data/gold_specialist_8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45_audit_summary.json
```

run dir内:

```text
ai_review_sample_80_loss45.csv
ai_review_sample_80_loss45_summary_by_strategy.csv
ai_review_sample_80_loss45_monthly_distribution.csv
ai_review_sample_80_loss45_rejected.csv
ai_review_sample_80_loss45_audit_summary.json
```

## 7. 成功条件

```text
DISC8定義JSONが存在する
source trade ledgerが存在する
DISC8の8 candidate_idがsource ledgerに存在する
sample_total <= 640
各candidate_id sample_total <= 80
各candidate_id sample_loss_count <= 45
各candidate_id sample_non_loss_count <= 35
htf_no_future_ok が存在する場合、False行が0
summary_by_strategyが出力される
monthly_distributionが出力される
AI APIを呼ばない
```

## 8. 停止条件

以下の場合は非0 exitで停止する。

```text
source trade ledger がない
DISC8定義JSONがない
8 candidate_id がsource ledgerに揃っていない
sample_total > 640
candidate別 sample_total > 80
candidate別 sample_loss_count > 45
candidate別 sample_non_loss_count > 35
HTF未来参照疑い行がある
```

## 9. 監査表示

AUDIT_ONLY BATでは以下を表示する。

```text
source_trade_rows
selected_source_rows
sample_total
rejected_rows
candidate別:
  full_trades
  full_losses
  full_non_losses
  sample_total
  sample_losses
  sample_non_losses
  train_count
  test_count
  months
  earliest_entry
  latest_entry
estimated_api_calls
output csv paths
```

## 10. AI評価に進む条件

このsample CSVを確認し、以下に問題がない場合だけAI評価BATへ進む。

```text
8シグナルすべて存在
最大640件以内
LOSS寄せサンプルになっている
月別・train/testが極端に偏っていない
重複・不正なcandidate_idがない
HTF未来参照なし
```

## 11. 注意

このサンプルはLOSSを多めに抽出するため、母集団の勝率/PFとは一致しない。

したがって、AI評価後のタグsummaryは以下に使う。

```text
負けパターン抽出
危険タグ候補
通知文面改善
回避条件候補
```

以下には使わない。

```text
本当の勝率計算
本当のPF計算
採用/不採用の最終判断
```

本当の勝率/PFは必ず full static_rule_trade_ledger.csv / full backtest summary で見る。
