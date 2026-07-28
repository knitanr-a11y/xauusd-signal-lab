# BTC ML V1 次チャット開始用プロンプト — 二系統分離・M7C保全・FF01のみ

以下を新しいチャットへそのまま貼り付ける。

```text
repo: knitanr-a11y/xauusd-signal-lab
authoritative base branch: main
BTC ML V1 working branch: feature/btc-fresh-forward-research

BTC研究の続きです。

BTCに関係する研究は2系統あります。両者を混同せず、両方を壊さないでください。

Track A:
BTC ML V1の凍結済み5候補研究です。

- BTC4_RISK_CAP_400
- BTC5_TWO_PIVOT_P2_CLEAN_N_382_786
- BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886
- BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110
- BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080

Track Aの正本はmainです。
新しい実装をmainへ直接行わず、mainから分岐したfeature/btc-fresh-forward-researchで作業してください。
GOLD/MOCHIPOYOの既存ローカルフォルダとは別cloneまたは別worktreeを使用してください。

Track B:
feature/mochipoyo-alert-researchで稼働中のM7C genuine-source prospective background trackです。
BTCUSDとXAUUSDを同時に扱っています。

- branch: feature/mochipoyo-alert-research
- symbols: BTCUSD, XAUUSD
- immutable start: 2026-07-20T14:54:15Z
- collector、M7C、M8Cは変更せず稼働継続

Track BはBTC ML V1の5候補研究とは別系統です。
M7CのBTC観測をBTC4/BTC5/BTC6/BTC7R/BTC9Rへ自動利用しないでください。
BTC ML V1の結果でM7Cのformula、matching、start、runtime、state、gateを変更しないでください。
feature/mochipoyo-alert-researchをBTC ML V1のworking branchへmergeしないでください。

M10以降のactive candidate/value researchはXAUUSD/GOLD-onlyです。
M7CがBTCUSDも収集していることを理由に、M10B/M10E/M10P/M10P2/M10W系をBTCへ拡張しないでください。
M10W24Bを含むM10W系へ触れないでください。

最初にGitHubの次を順番どおり、最初から最後まで読んでください。

1. START_HERE_BTC_ML_V1_NEXT_CHAT.md
2. docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md
3. configs/btc_ml_v1/current_state_20260729.json
4. configs/btc_ml_v1/next_action_20260729.json
5. configs/btc_ml_v1/btc_dual_track_scope_20260729.json
6. configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json
7. docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md
8. docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_FIX_AND_VERIFIED_RUN_20260702.md
9. docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md
10. docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md
11. configs/btc_ml_v1/btc_candidate_master_catalog.json
12. configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json
13. configs/btc_ml_v1/btc_stacking_reproduction_reference.json

古いBTCハンドオフが上記20260729正本と矛盾する場合、古い文書を使用しないでください。
GOLDやM10Wの古いハンドオフをBTC作業の根拠にしないでください。

現在のformal status:
BTC_DUAL_TRACK_SEPARATED_FIVE_CANDIDATES_FF01_NEXT_M7C_BACKGROUND_PRESERVED

Track Aのfresh-forward exclusive cutoff:
entry_dt > 2026-07-02 02:15:00 UTC

現在の次Stageは次だけです。

BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY

FF01の最初は書込みなしです。
許可されたBTC範囲だけで、現在有効な同等availability監査が存在するか確認してください。
既存の同等機能がある場合は重複実装しないでください。
同等機能がない場合だけ、正式handoffとnext_actionに指定された次のBTC専用pathへ最小実装してください。

scripts/btc_ml_v1/fresh_forward_availability/

FF01では次だけを確認します。

- M5
- M15
- H1
- D1
- H4 fresh tail
- BTC4用2017年開始long H4 warmup
- MT5 broker-server timestamp
- 正本broker UTC offset変換
- cutoff後の行数
- 時刻昇順違反
- 重複時刻
- 候補別READY/BLOCKED

候補ごとの必要データ:

BTC4: H4 long warmup + cutoff後H4 + cutoff後M5
BTC5: cutoff後M5
BTC6: cutoff後M15
BTC7R: cutoff後M5 + M15 + H1
BTC9R: cutoff後M5 + M15 + H1 + D1

全時間足がそろわないことを理由に、必要データがある候補まで一括BLOCKしないでください。

FF01で禁止:

- source CSVの追記、上書き、copy、merge、rename、delete
- PC全体の再帰検索
- 似たCSVや別symbolの代用
- naive時刻をUTCとみなすこと
- 固定で2時間または3時間を引く独自変換
- fresh performance evaluatorの実装または実行
- candidate engineによるfresh trade生成
- reproduce_btc_stacking_portfolio.pyをextended fresh CSVへ実行
- --skip-input-hash-checkをfresh evaluatorとして使用
- 候補条件、threshold、TP、SL、exit順序、spread、pip、overlap ruleの変更
- lot設計、金額DD計算
- 新候補探索、BTC10R混入
- collector、常駐loop、dashboard作成
- Discord、MT5 order、live-ready、final signal
- feature/mochipoyo-alert-researchのcheckout、merge、変更
- collector、M7C、M8C、GOLD loopの停止、再起動、taskkill
- M7Cのstart、runtime、state、lock、formula、matching、gateの変更
- M10W24Bやその他M10W系への接触

FF01の提出物:

%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST\99_UPLOAD_PACKAGE.zip

availability packageまたは明確なBLOCKED reportを作成した時点で停止してください。
FF02、fresh成績評価、lot設計、新候補探索へ進まないでください。
FF02はpackageレビュー後、ユーザーの明示許可が出るまで未承認です。

作業開始前に、実装や変更を行わず、次を回答してください。

1. repository
2. authoritative base branch
3. BTC ML V1 working branch
4. Track Aの目的と凍結5候補
5. Track Bの目的、branch、symbols、immutable start
6. Track AとTrack Bを混ぜないこと
7. M10 lineがGOLD-onlyであること
8. exclusive fresh cutoff
9. 現在のformal status
10. 次StageがFF01 availability-onlyであること
11. phase 0は書込みなしであること
12. FF01 package作成後に停止すること
13. feature/mochipoyo-alert-research、M7C/M8C、M10W24Bを変更しないこと
```

## 正式参照

- `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
- `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md`
- `configs/btc_ml_v1/current_state_20260729.json`
- `configs/btc_ml_v1/next_action_20260729.json`
- `configs/btc_ml_v1/btc_dual_track_scope_20260729.json`
- `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`

この開始文は、BTC ML V1のFF01を進める一方で、feature/mochipoyo-alert-research上のM7C dual-source backgroundを保全するためのものです。