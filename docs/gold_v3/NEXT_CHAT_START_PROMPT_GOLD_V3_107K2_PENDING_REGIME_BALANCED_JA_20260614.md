# NEXT CHAT START PROMPT — GOLD V3 107K2 pending regime-balanced audit

新しいチャットでは、以下を貼って開始してください。

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

1. docs/gold_v3/READ_THIS_FIRST_GOLD_V3_CURRENT_107K2_PENDING_20260614.md
2. docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107K2_PENDING_REGIME_BALANCED_20260614.md

GOLD V3は現在audit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。
Stage41 feature-only snapshotもtrading sourceにしないでください。

このチャットではStage107GY〜107K2作成まで進みました。
107KはBLOCKEDでしたが、戦略失敗ではなく、既存設定ファイルに新regime split名を探した評価設計ミスです。
その修正版として107K2を作成済みです。

現在statusは以下です。
GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_PENDING_AUDIT_ONLY

次にやること:
添付する `FX_OUTPUTS/gold_v3/107k2c/paste_me.txt` を読んで、107K2結果を判断してください。

重要:
- 目的は2026年5月だけに適応する候補ではありません。
- 2025相場と2026高ボラ相場の両方で成果を残せる、フレキシブルなGOLD V3を作ることです。
- 5月だけ良い候補、2026だけ良い候補、2025だけ良い候補は完成扱いにしないでください。
- 評価軸は `all_regime_pass_65_count`, `all_regime_pass_60_count`, `best_min_wr`, `best_min_pf`, `best_min_trades`, `best_policy_regime_rows` です。
- 107K2の `test_end=2027-01-01` は上限です。実際には添付結果に存在する最新行までの評価として扱ってください。
- 107Jはexit_dt不足でBLOCKEDです。rolling health gateは、exit_dtがあるresolved-only ledgerがない限り進めないでください。
- health gate / rolling gateは必ず `exit_dt <= current entry_dt` の解決済み履歴だけを使ってください。
- open中の足はCSVには入りません。CSVの最新行はCSV契約上closedです。
- ただし未来の決済結果はlive時点では未知です。
- Discord通知、MT5発注、AI API、live hook、live evaluator、final signalは明示許可までOFFです。
- live_ready=falseのままです。
- source CSV、CSV契約、candidate pool、Stage45 runtime、Stage69 runtimeは変更しないでください。

107K2結果で balanced policy が出た場合:
次は 107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY を作ってください。

107K2結果で balanced policy が出なかった場合:
次は 107L_ADAPTIVE_BASE_CANDIDATE_GENERATION_AUDIT_ONLY を作ってください。
その場合も、5月適応ではなく、2025用候補群・2026高ボラ用候補群・live-known regime selectorの方向で進めてください。
```
