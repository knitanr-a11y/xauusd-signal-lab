repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_117N_DONE_118_NEXT_DEMO_ALERT_ONLY_RESTART_REVIEW_20260615.md
```

GOLD V3はaudit-only継続です。
ただしStage115/116の demo Discord alert-only loop は許可済みです。
MT5発注、実口座、live order、final signal化は禁止です。
NO_SIGNALはDiscord通知しません。

絶対禁止:
- GOLD V2 / 旧GOLD / DISC8 は隔離中。読まない、使わない、参照しない、fallbackしない。
- Stage41 feature-only snapshotもtrading sourceにしない。
- CSV最新行はclosed契約。open/as-ofは禁止。
- candidate poolを外さない。
- 6月8件のreview-only restoreをlive policyへ自動採用しない。

現在位置:
- Stage117Nまで完了。
- status: GOLD_V3_117N_LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY_READY
- decision: NO_PRETRADE_EXCEPTION_REVIEW_GATE_PASS_KEEP_F002_EXCLUSION
- 結論: 6月8件を復活させるための、結果を使わない事前特徴ベースの例外ルールは見つからなかった。よって現時点ではF002除外維持。

重要な到達点:
1. 109c selected ledgerは2026-05-29で止まっている。
2. 107R6 base ledgerも2026-05-29で止まっている。
3. 107Q best family ledgerも2026-05-29で止まっている。
4. 107L inputには2026-06-05まで8件の6月行がある。
5. Stage117Jで107Qをshadow再実行したが、bestは同じ F002 / score <= / L20 / T5 で、6月0件。
6. Stage117Lで、107Lの6月8件はすべて F002 score <= 1715.701299 により除外されたことを確認。
7. 6月8件は勝率50%、PF2.0、損益+37.5。
8. Stage117Mで8件全部を戻すreview-only比較を実施。損益は+37.5増えるが、全体WR/PFはわずかに低下。自動採用不可。
9. Stage117Nで事前特徴ベースの例外復活を確認したが、review_gate_count 0。

2026年度成績、日本式年度2026年4月以降、F002除外維持:
- trades 166
- wins 111
- losses 55
- WR 66.87%
- PF 3.615
- sum_result_usd +654.94

live demoに戻る場合:
- 戻せるのは demo Discord alert-only loop のみ。
- 推奨BAT:
  scripts/gold_v3_runtime/bat/run_gold_v3_116_115_full_loop.bat
- ただし現行109c/107Q本命は6月0件なので、しばらくNO_SIGNALが正常。
- NO_SIGNALはDiscord通知しない。

BAT運用ルール:
- 今後のBATには進行度表示を入れる。
- 最低限:
  [1/4] Working directory set
  [2/4] Starting Python audit script
  [3/4] Python script finished
  [4/4] Output location
- 117N BATは進行度付きに更新済み。

次にやること:
- Stage118: GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY
- 目的: Stage115/116 demo Discord alert-only loopに戻す前の安全確認。
- order pathなし、NO_SIGNAL通知なし、closed CSV契約維持、Discord alert-onlyのみを確認。
