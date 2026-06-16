repo: knitanr-a11y/xauusd-signal-lab

まず以下だけを読んで、続きからお願いします。

1. docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_215_DONE_216_RESULT_NEXT_AUDIT_ONLY_20260616.md
2. docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_215_DONE_216_RESULT_NEXT_CLARITY_ADDENDUM_20260616.md
3. このチャットに添付する Stage216 の paste_me.txt

GOLD V3は現在も audit-only です。

重要:
- GOLD V2 / 旧GOLD / DISC8 / Stage41 は読まない・使わない・参照しない・fallbackにしないでください。
- 旧シグナル候補や古いcandidate探索ドキュメントも読まないでください。
- 必要がある場合でも、まず上記ハンドオフ、clarity addendum、添付したStage216結果だけで判断してください。
- CSV最新行は契約上 closed です。open/as-of扱いは禁止です。
- candidate pool を黙って外さないでください。
- F002 exclusion を bypass しないでください。
- Discord通知、MT5発注、AI API、payload、live hook、final live、autotrade はまだOFFです。
- NO_SIGNAL時はDiscord通知しません。
- MT5/CSV時刻基準で進めてください。検出ロジックでJST変換しないでください。

現在位置:
- Stage215まで完了。
- Stage214で duplicate signal_id / idempotency audit は解消済みです。
- Stage216はこの次チャットに結果を添付します。
- まずStage216 paste_me.txtを確認し、PASS/BLOCKEDを判断してください。

Stage216がPASSなら次は原則 Stage217:
GOLD_V3_217_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT_ONLY

Stage217の目的:
- production/live retention fileではなく staging file にだけ書くdry-run
- latest_state overwrite / signal append / notification append preview / no_signal counter / health rollup / debug tail を実ファイル形式で検証
- Discord送信・MT5発注・actual import・payload・live hook・autotradeはOFF維持

Stage216がBLOCKEDなら:
- Stage216だけを修正してください。
- live送信/発注系には進まないでください。

用語注意:
- 補助戦略候補は SECONDARY_AUDIT_CANDIDATE または SCALP_SECONDARY_CANDIDATE と呼んでください。
- 「ウォッチリスト」と呼ばないでください。
- cost5 は spread-only ではなく worse-execution stress proxy です。
