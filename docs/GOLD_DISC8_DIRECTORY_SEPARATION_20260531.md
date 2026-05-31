# GOLD DISC8 ディレクトリ分離方針

作成日: 2026-05-31

## 背景

当初、data-driven DISC8 のAI評価導線を `scripts/gold_specialist_8/` と `data/gold_specialist_8/` 配下に作成した。

しかし `gold_specialist_8` は、過去の探索・再バックテスト・前回失敗したAI評価導線の文脈を含むため、今回の `DISC_*` 8条件の固定評価と混ざるリスクがある。

そのため、今後のDISC8作業は専用ディレクトリに分離する。

## 新しい入口

今後、ユーザーが直接実行するBAT/Pythonは以下を使う。

```text
scripts/gold_disc8/
```

## 新しい出力先

今後のサンプル、payload、AI評価結果、タグsummaryは以下へ出力する。

```text
data/gold_disc8/
```

## 旧ディレクトリの扱い

旧ディレクトリは互換・過去検証用として残す。

```text
scripts/gold_specialist_8/
data/gold_specialist_8/
```

ただし、今後のDISC8運用では直接叩かない。

## 新ディレクトリの予定構成

```text
scripts/gold_disc8/
  run_gold_disc8_migrate_from_gold_specialist8_outputs.bat
  run_gold_disc8_ai_review_sample_80_loss45_AUDIT_ONLY.bat
  run_gold_disc8_ai_review_PAYLOAD_AUDIT_ONLY.bat
  run_gold_disc8_ai_review_AI_REVIEW.bat
  run_gold_disc8_ai_review_pipeline.py
  run_disc8_trade_ai_review_from_payloads_progress.py

data/gold_disc8/
  config/
    disc8_static_rule_definitions_20260531.json
  verification/
    data_driven_static_rebacktest/
      static_rule_trade_ledger.csv
    ai_review_data_driven/
      latest_ai_review_sample_80_loss45.csv
      latest_ai_review_sample_80_loss45_audit_summary.json
      disc8_ai_review/
        trade_ai_review_payloads.jsonl
        trade_ai_review_payloads_pending.jsonl
        trade_ai_review_ledger.jsonl
        trade_ai_tag_summary.csv
        trade_ai_tag_summary.json
```

## source of truth

DISC8条件定義:

```text
data/gold_disc8/config/disc8_static_rule_definitions_20260531.json
```

AI評価対象サンプル:

```text
data/gold_disc8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45.csv
```

AI評価はこのサンプルCSVのみを対象とする。

## 禁止事項

```text
full static_rule_trade_ledger.csv を直接AI評価対象にしない
OHLCからDISC条件を再検出してAI評価対象を作らない
旧gold_specialist_8配下の結果と新DISC8結果を混在させない
```

## 移行手順

既に `data/gold_specialist_8/` 側で作成済みのサンプルやpayloadがある場合は、以下を1回実行して新ディレクトリへコピーする。

```bat
scripts\gold_disc8\run_gold_disc8_migrate_from_gold_specialist8_outputs.bat
```

その後は以下だけを使う。

```bat
scripts\gold_disc8\run_gold_disc8_ai_review_PAYLOAD_AUDIT_ONLY.bat
scripts\gold_disc8\run_gold_disc8_ai_review_AI_REVIEW.bat
```
