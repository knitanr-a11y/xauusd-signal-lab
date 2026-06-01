# GOLD DISC8 pre-send tagger audit-only stage

作成日: 2026-06-02

## 目的

DISC8の live decision 候補に対して、通知/発注前のタグ判定を監査する。

ただし、この段階では **dispatch_ready を有効化しない**。

## 背景

`gold_disc8_runtime_group_tag_gate_rules.json` は、過去AIレビューで得られた group tag を使っている。
ライブ運用で同じタグを使うには、現在の候補シグナルから `strategy_id / tag_group / tag_name` を生成する pre-send tagger が必要。

このタグ判定を未検証のまま通知/発注へ接続すると、過去AI評価とライブ判定がズレる可能性がある。

## 今回の範囲

```text
scripts/gold_disc8/apply_gold_disc8_pre_send_tagger_audit_latest.py
scripts/gold_disc8/run_gold_disc8_pre_send_tagger_audit_latest.bat
```

入力:

```text
data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_candidates.csv
data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_audit_summary.json
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json
```

出力:

```text
data/runtime_logs/gold_disc8_pre_send_tagger_audit/latest/gold_disc8_pre_send_tag_hits.csv
data/runtime_logs/gold_disc8_pre_send_tagger_audit/latest/gold_disc8_pre_send_gate_audit.csv
data/runtime_logs/gold_disc8_pre_send_tagger_audit/latest/gold_disc8_pre_send_tagger_audit_summary.json
```

## 重要な安全仕様

- OpenAI APIを呼ばない
- Discord送信しない
- MT5発注しない
- decision ledgerを書き換えない
- ALLOWを出しても dispatch_ready は false のまま
- 出力は監査専用

## タグ判定の扱い

今回のタグ判定は、既存runtime gate ruleのタグ名を使い、candidate行に含まれる `matched_conditions` / `failed_conditions` / 価格情報から、保守的にタグ候補を作る。

これは正式な統計検証済みnumeric taggerではない。
そのため、出力には `tagger_validation_status=PROVISIONAL_AUDIT_ONLY` を入れる。

正式接続前には、source trade ledger / AI review ledger / live feature snapshot を使って、タグヒットごとの勝率・PF・TotalRを再監査する必要がある。
