repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

- docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_180_DONE_181_NEXT_HIGH_FREQUENCY_CANDIDATE_SEARCH_20260616.md
- docs/gold_v3/GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_AUDIT_SPEC_20260616.md
- docs/gold_v3/GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_LOCAL_RUNBOOK_20260616.md

GOLD V3は現在audit-onlyです。
GOLD V2 / 旧GOLD / DISC8 / Stage41は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。

CSV最新行はclosedです。open/as-ofは禁止です。
Candidate poolを勝手に外さないでください。
F002 exclusionをbypassしないでください。
Discord通知、MT5発注、AI API、live hook、final signal、payload、autotradeは明示許可までOFFです。
NO_SIGNAL時はDiscord通知しません。

現在位置:
- Stage177: OHLC-only候補検出済み。
- Stage178: dedup + cost 3後も候補あり。
- Stage179: 選択候補の月別表作成済み。full_n=110、full_pf=16.09、test_pf=5.83、負け月0。
- Stage180: 安定性確認済み。TP/SL/horizon grid 75/90が旧PF超え、threshold variant 12/21が旧PF超え。
- ただしユーザーがトレード回数が少ないため別候補も欲しいと希望。

次はStage181:
GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_AUDIT_ONLY

実行:
scripts/gold_v3_runtime/bat/run_gold_v3_181_high_frequency_candidate_search_audit.bat

出力:
MQL5\Files\FX_OUTPUTS\gold_v3\181\paste_me.txt

Stage181は高頻度候補探索です。target-full-n default 150、cost-points default 3.0です。A/B/C tierで候補を分類します。

Stage181の結果を見て、A候補があれば優先。B/Cしかなければ、負け月、recent3m PF、high_vol PF、test PFを確認してください。live承認はしないでください。次もaudit-onlyレビューです。
