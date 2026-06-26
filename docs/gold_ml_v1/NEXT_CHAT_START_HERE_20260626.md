# GOLD_ML_V1 — NEXT CHAT START HERE

新しいチャットは最初に次を順番に読むこと。

1. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
2. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
3. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
4. `config/gold_ml_v1/handoff_snapshot_20260626.json`
5. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
6. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_15_ACCUMULATED_9_WATCHES_20260626.md` — 探索経緯の参照用
7. 対象candidate config

## 正本の優先順位

1. 候補のaccumulated / Research WATCH / retired状態: stack file
2. 実装済み範囲・候補成績: `implementation_status_and_metrics_20260626.json`
3. 3回監査による訂正・未完了項目: three-pass audit文書
4. entry/exitロジックと実装契約: implementation contract
5. 旧handoff本文: 探索経緯・背景だけに使用

旧handoff本文内の「029/030個別configがaccumulated=false」という記述は修正前の履歴であり、現在は無効。029/030個別configはaccumulatedへ同期済み。

現在:

- stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`
- accumulated: 15
- research WATCH: 9
- retired: `GML1-WATCH-031-A`
- implementation level: 2 / 6
- added WATCH executable implementation: 0
- audit-only
- live / MT5 order / Discord / final signal: OFF

用語:

- accumulated = research stack採用。実行コード実装済みという意味ではない。
- implemented = executable detector、exact-M1 integration、parity testsがGitHubへcommit済みの場合だけ使用する。

ユーザーの明示指示なしに実装、昇格、live変更を開始しない。
