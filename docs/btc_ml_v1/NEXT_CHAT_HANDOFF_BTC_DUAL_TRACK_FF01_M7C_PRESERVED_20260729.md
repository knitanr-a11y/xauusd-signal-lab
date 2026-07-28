# BTC ML V1 次チャット正式引き継ぎ V2 — 二系統分離・M7C保全・FF01のみ次

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative base branch: `main`
- BTC ML V1 working branch: `feature/btc-fresh-forward-research`
- recorded date: `2026-07-29`
- formal status: `BTC_DUAL_TRACK_SEPARATED_FIVE_CANDIDATES_FF01_NEXT_M7C_BACKGROUND_PRESERVED`
- next stage: `BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY`

この文書は、BTCに関係する研究が2系統存在することを明示し、両方を壊さずにBTC ML V1を再開するための最優先正本である。

## 1. 最初に読む順序

1. `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md`
3. `configs/btc_ml_v1/current_state_20260729.json`
4. `configs/btc_ml_v1/next_action_20260729.json`
5. `configs/btc_ml_v1/btc_dual_track_scope_20260729.json`
6. `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`
7. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md`
8. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_FIX_AND_VERIFIED_RUN_20260702.md`
9. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md`
10. `docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md`
11. `configs/btc_ml_v1/btc_candidate_master_catalog.json`
12. `configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json`
13. `configs/btc_ml_v1/btc_stacking_reproduction_reference.json`

古いBTCハンドオフがこの文書と矛盾する場合、この文書を優先する。

## 2. BTCに関係する2系統

### Track A — BTC ML V1

対象は凍結済み5候補。

- `BTC4_RISK_CAP_400`
- `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786`
- `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886`
- `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110`
- `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080`

正本は`main`。新規実装は`main`へ直接行わず、`main`から分岐した`feature/btc-fresh-forward-research`で行う。

fresh-forward exclusive cutoff:

```text
entry_dt > 2026-07-02 02:15:00 UTC
```

現在は5候補の固定再現・2026評価が完了し、cutoff後のローカルclosed-bar availabilityが未確認。

### Track B — MOCHIPOYO M7C background

`feature/mochipoyo-alert-research`には、BTCUSDとXAUUSDを同時に扱う凍結済みM7C genuine-source prospective trackが存在する。

- branch: `feature/mochipoyo-alert-research`
- symbols: `BTCUSD`, `XAUUSD`
- immutable start: `2026-07-20T14:54:15Z`
- collector、M7C、M8Cは稼働継続

正式scope clarification:

```text
docs/mochipoyo_alert_research/SCOPE_CLARIFICATION_M10_GOLD_ONLY_M7C_DUAL_SOURCE_BACKGROUND_20260727.md
```

M7Cはsource-fidelity/background collectionであり、BTC ML V1の5候補stackingとは目的・条件・start・runtime・gateが別。

## 3. M10のscope

`feature/mochipoyo-alert-research`のactive M10 candidate/value lineはXAUUSD/GOLD-only。

M7CがBTCUSDも収集していることを理由に、M10B/M10E/M10P/M10P2/M10W系をBTCへ広げない。

M7CのBTC観測は、GOLD M10の候補、threshold、payoff、portfolioへ自動混入させない。

## 4. 二系統を混ぜない契約

- M7C BTC観測をBTC4/BTC5/BTC6/BTC7R/BTC9Rのfeature、filter、entry、outcomeとして自動使用しない。
- BTC ML V1の結果でM7Cのformula、matching、start、runtime、review gateを変更しない。
- `feature/mochipoyo-alert-research`をBTC FF01 branchへmergeしない。
- GOLD/M10WファイルをBTC FF01の実装対象にしない。
- M7Cを「存在しない扱い」にせず、別の凍結済みbackground trackとして保全する。
- 将来、M7C BTCとBTC ML V1を比較する場合は、FF01とは別の事前登録Stageとユーザーの明示許可が必要。

## 5. ブランチとローカルフォルダ

推奨構成:

```text
GOLD/MOCHIPOYO用の既存ローカルフォルダ
  branch: feature/mochipoyo-alert-research
  collector/M7C/M8C/9本のloopを継続
  checkoutしない

BTC ML V1用の別cloneまたは別worktree
  base: main
  working branch: feature/btc-fresh-forward-research
  FF01だけを実施
```

同じローカルフォルダでbranchを切り替えて、稼働中のGOLD/MOCHIPOYO環境を巻き込まない。

## 6. 現在の次StageはFF01だけ

```text
BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY
```

目的はM5/M15/H1/D1/H4 fresh tailとBTC4用long H4 warmupの存在・時刻・整合を読取専用で確認すること。

最初は書込みなしで、現在有効な同等監査が既に存在するかをBTC許可範囲内だけで確認する。同等監査がない場合だけ、`scripts/btc_ml_v1/fresh_forward_availability/`へ最小実装する。

## 7. FF01で行わないこと

- fresh performance evaluatorの実装・実行
- candidate engineによるfresh trade生成
- 5候補の条件、threshold、TP、SL、exit、spread、pip、overlap rule変更
- lot設計、金額DD計算
- 新候補探索、BTC10R混入
- collector、常駐loop、dashboard作成
- Discord、MT5 order、live-ready、final signal
- M7C/M8C/GOLD loopの停止・再起動・変更
- `reproduce_btc_stacking_portfolio.py`をextended fresh CSVへ実行
- `--skip-input-hash-check`をfresh evaluatorとして使用

## 8. FF01の停止条件

availability packageまたは明確なBLOCKED reportを作成した時点で停止する。

提出物:

```text
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST\99_UPLOAD_PACKAGE.zip
```

FF02はpackageのレビューとユーザーの明示許可まで未承認。

## 9. GOLD/MOCHIPOYO保全

BTC ML V1作業中、GOLD/MOCHIPOYO側を変更してはならない。

ただし、M7C dual-source trackの存在を理解するために、このV2 handoffと`btc_dual_track_scope_20260729.json`に記録されたscope情報は正本として扱う。FF01実装のためにM10W24BやM10W系を読む必要はない。

incidentが見える場合も、BTCチャットからGOLD process、lock、runtime、stateを操作しない。GOLD専用チャットで現在の正式handoffに従う。

## 10. 次チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
base branch: main
working branch: feature/btc-fresh-forward-research

BTC研究の続きです。BTCには2系統あります。

Track AはBTC ML V1の凍結5候補研究です。
Track Bはfeature/mochipoyo-alert-researchで稼働中のM7C dual-source backgroundで、BTCUSDとXAUUSDを収集しています。
両者を混ぜず、両方を壊さないでください。

最初にGitHubの次を順番どおり、最初から最後まで読んでください。

1. START_HERE_BTC_ML_V1_NEXT_CHAT.md
2. docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md
3. configs/btc_ml_v1/current_state_20260729.json
4. configs/btc_ml_v1/next_action_20260729.json
5. configs/btc_ml_v1/btc_dual_track_scope_20260729.json
6. configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json

BTC ML V1はmainを正本とし、mainへ直接実装せず、mainから分岐したfeature/btc-fresh-forward-researchで作業してください。

feature/mochipoyo-alert-researchのcollector/M7C/M8C/GOLD loopは停止・変更・checkoutしないでください。
M7CのBTC観測をBTC ML V1の5候補へ自動混入させないでください。
M10 lineはGOLD-onlyのままです。

次はBTC_FF01 availability read-onlyだけです。
availability packageを作成した時点で停止し、fresh成績評価、lot設計、新候補探索へ進まないでください。

作業開始前に、Track AとTrack Bの違い、使用branch、FF01の停止条件を回答してください。
```

## 11. 正式参照

- dual-track scope: `configs/btc_ml_v1/btc_dual_track_scope_20260729.json`
- current state: `configs/btc_ml_v1/current_state_20260729.json`
- next action: `configs/btc_ml_v1/next_action_20260729.json`
- BTC/GOLD firewall: `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`
- MOCHIPOYO scope clarification: `feature/mochipoyo-alert-research:docs/mochipoyo_alert_research/SCOPE_CLARIFICATION_M10_GOLD_ONLY_M7C_DUAL_SOURCE_BACKGROUND_20260727.md`

このV2 handoffは、`NEXT_CHAT_HANDOFF_BTC_FRESH_FORWARD_AVAILABILITY_GOLD_FIREWALL_20260729.md`をsupersedeする。
