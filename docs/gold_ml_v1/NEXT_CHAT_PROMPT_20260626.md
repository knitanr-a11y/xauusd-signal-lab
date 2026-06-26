# GOLD_ML_V1 次チャット貼り付け用・最終版

repo: `knitanr-a11y/xauusd-signal-lab`

GOLD_ML_V1の続きです。
まず次のGitHubファイルを順番に実際に読んでください。

1. `docs/gold_ml_v1/NEXT_CHAT_START_HERE_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_FINAL_VERIFICATION_20260626.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
4. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_V2_20260626.md`
5. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
6. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`

旧実装契約
`GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
は経緯参照用です。実装判断には必ずV2を使ってください。

現在の正式状態:

- stack ID: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`
- accumulated: 15
- Research WATCH: 9
- retired: `GML1-WATCH-031-A`
- implementation level: 2 / 6
- 今回追加した候補の実行可能コード実装: 0件
- audit-only
- live / MT5 order / Discord / final signal: OFF

重要:

- GOLD_ML_V1だけを使用し、他のGOLD系、旧ロジック、DISC8、Stage41等を参照・fallback・補完に使わないでください。
- existing frozen nineを変更しないでください。
- candidate registryはappend-onlyです。ロジック、閾値、exit、source stack、priority、時間帯を変える場合は新candidate IDを発行してください。
- accumulatedは研究stackに残した状態で、コード実装済みという意味ではありません。
- WATCH-029-Aと030-Aはaccumulatedですが未実装です。
- WATCH-032-A、033-A、034-A/B/CはResearch WATCHで未実装です。
- WATCH-031-AはTP3/TP4を含んだため退役済みです。復活・実装・source利用・ID再利用をしないでください。
- WATCH-029-Aは現在の15候補ではなく、凍結13候補stack Pをsourceに使います。
- WATCH-033-AはcomponentごとのTP5/TP7.5とpriorityを維持します。
- WATCH-034-A/B/Cは同じentryの排他的exit variantです。同時運用、件数合算、損益合算は禁止です。
- CSV timeはMT5 server bar-openです。最新行はclosedです。
- 時間帯判定はJSTではなくMT5 server hourです。
- entryはdecision timeと完全一致するexact M1です。exact M1が欠ける場合は次のM1へずらさずskipしてください。
- causal closed-HTF join、dynamic bid/ask spread、same-M1 protective-firstを維持してください。
- 2024〜2026は診断済みです。true prospectiveは2026-06-26より後です。
- 私の明示指示なしに実装、昇格、portfolio化、live変更を始めないでください。

追加候補の成績、年別結果、強コスト結果、実装blockerは
`config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
を正本として確認してください。

最初の回答では次だけを短く報告してください。

1. 読んだファイル
2. stack ID
3. accumulated数
4. Research WATCH数
5. retired ID
6. implementation levelと実行可能実装数
7. audit-onlyを維持すること

その後は私の次の指示を待ってください。
