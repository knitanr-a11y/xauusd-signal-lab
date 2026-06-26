# GOLD_ML_V1 — NEXT CHAT START HERE

新しいチャットは最初に次を順番に読むこと。

1. `docs/gold_ml_v1/NEXT_CHAT_FINAL_VERIFICATION_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
3. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_V2_20260626.md`
4. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
5. `config/gold_ml_v1/handoff_snapshot_20260626.json`
6. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
7. 対象candidate config

旧ファイル
`docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
は経緯参照用であり、実装契約の正本には使用しない。

## 正本の優先順位

1. candidate state: stack file
2. implementation completion / metrics: `implementation_status_and_metrics_20260626.json`
3. implementation logic: V2 implementation contract
4. corrections / known incomplete items: three-pass audit and final verification

現在:

- stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`
- accumulated: 15
- Research WATCH: 9
- retired: `GML1-WATCH-031-A`
- implementation level: 2 / 6
- added WATCH executable implementation: 0
- audit-only
- live / MT5 order / Discord / final signal: OFF

用語:

- accumulated = research stack採用。実行コード実装済みという意味ではない。
- implemented = executable detector、exact-M1 integration、parity testsがGitHubへcommit済みの場合だけ使用する。

絶対条件:

- GOLD_ML_V1だけを使用する。
- 他のGOLD系をfallback・補完に使わない。
- frozen nineを変更しない。
- ロジック等を変える場合は新candidate ID。
- ユーザーの明示指示なしに実装、昇格、live変更を開始しない。
