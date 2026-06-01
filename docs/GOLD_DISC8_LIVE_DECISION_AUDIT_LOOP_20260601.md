# GOLD DISC8 live decision audit loop

作成日: 2026-06-01

## 目的

DISC8をDiscord通知/MT5自動売買へ接続する前に、共通の候補検出・decision ledgerを作る。

## 方針

入口BATは将来、通知用と自動売買用で分けてもよい。ただし、以下は分けない。

- DISC8候補検出
- group-tag gate判定
- source of truth
- decision ledger

通知用・自動売買用は、共通decision ledgerの `decision == ALLOW` だけを読む薄い後段にする。

## 今回の実装範囲

```text
scripts/gold_disc8/run_gold_disc8_live_decision_audit_forever_aligned.py
scripts/gold_disc8/run_gold_disc8_live_decision_audit_forever_aligned.bat
```

この段階では以下を行う。

- MQL5 Files配下の `goldsharp_m15.csv` / `goldsharp_h1.csv` / `goldsharp_h4.csv` / `goldsharp_d1.csv` を読む
- operational manifest の8戦略条件を評価する
- runtime gate rules JSONを読む
- 候補を共通decision ledgerへ出力する
- Discord送信しない
- MT5発注しない
- OpenAI APIを呼ばない

## 重要な制約

現時点の `gold_disc8_runtime_group_tag_gate_rules.json` は `requires_pre_send_tagger: true` である。
つまり、ライブ候補に対して `strategy_id / tag_group / tag_name` を返す検証済みpre-send taggerが必要。

今回のaudit loopは、候補検出までは行うが、検証済みpre-send taggerが無いため、候補のdecisionは原則として以下になる。

```text
PENDING_TAGGER
```

これは安全のためであり、通知/発注へ接続してはいけない。

## 出力

```text
data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_candidates.csv
data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_audit_summary.json
data/runtime_logs/gold_disc8_live_decision_audit/gold_disc8_live_decision_ledger.csv
data/runtime_logs/gold_disc8_live_decision_audit/<year>/<month>/week_<week>/gold_disc8_live_decision_loop_summary.csv
```

## 次段階

1. decision audit loopが候補を安定検出するか確認する。
2. DISC8用の数値pre-send taggerを作る。
3. tagger検証後、同じdecision ledgerをDiscord通知/自動売買の後段に渡す。
