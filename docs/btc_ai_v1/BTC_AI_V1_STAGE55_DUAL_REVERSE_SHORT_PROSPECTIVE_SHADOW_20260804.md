# BTC AI V1 Stage 55 — 騙し後SHORT 2候補 Prospective Shadow

日付: 2026-08-04  
対象: XM `BTCUSD#`  
モード: observation-only prospective shadow

## 1. なぜShadowを作るのか

Stage54で残った2つのSHORT familyは、単一parameterや最大winnerだけに依存する形には見えなかった。一方、2,880構成を確認した後に安定領域を選んでいるため、`post-selection / multiple-testing overfit` は否定できない。

その疑いを検証する方法は、過去データでさらにthresholdを探すことではない。条件を完全に固定し、初回activate以降の新しいclosed OHLCだけを全件観測することである。

このShadowは利益を出すための運用ではなく、後付け選択リスクを測るための観測装置である。

## 2. 実装候補

### A. M1騙し後SHORT

1. H4上昇trend。
2. 最後に閉じたM15が上向きEMA配列。
3. M15直近20本高値の0.50 M15 ATR以内で、M1二本反転LONG sourceが発生。
4. source発生30分後、固定Logistic fakeout scoreが過去training scoreのQ70以上。
5. その後15分以内に、closed M1がEMA20を下回り、実体が `-0.10 M1 ATR` 以下。
6. confirmation close時刻と同時刻のexact M1 openでSHORT。
7. SLは直近5本のclosed M5高値 + `0.10 M5 ATR`。
8. TPは2R、最大240 exact M1分。

LogisticはStage55開始時に固定したbootstrap historyを使用する。Stage55中に結果を見てモデル、Q70、featureを変更しない。

### B. M5水準拒否後SHORT

1. 同じH4・M15環境でM5二本反転LONG sourceが発生。
2. 15分または30分checkpointで、breakout水準へ `0.05 M15 ATR`以内まで到達済み。
3. M5終値が水準より `0.10 M15 ATR`以上下へ戻り、陰線。
4. その後30分以内にM5二本足の弱気反転。
5. confirmation close時刻と同時刻のexact M1 openでSHORT。
6. SLはsource発生後からconfirmationまでのM5最高値 + `0.10 M5 ATR`。
7. TPは2R、最大480 exact M1分。

## 3. 絶対境界

- MT5 broker-server naive timeを使用する。
- CSVに存在するclosed足だけを使う。
- open/as-of足を作らない。
- entry時刻のM1が欠けている場合、次の利用可能M1へfallbackしない。
- 同一M1でSLとTPへ触れた場合はSL優先。
- 往復costは1SHORT当たり22.5 USD。
- 各family内は1ポジション。
- 両familyを一つの成績へ混ぜて、悪い方を消さない。
- Discord、MT5 order、live trading、final signalはOFF。

## 4. no-backfill

初回 `02_BOOTSTRAP_ACTIVATE.bat` を実行した時点の最新closed M1をactivation cutoffにする。

- cutoff以前のcandidateはShadow取引へ入れない。
- 起動時点で進行中のsource setupは消費済みにする。
- runtimeのpoll gapが10分を超えた区間のcandidateは `RECOVERY_REPLAY_NOT_TRADED` として記録する。
- 停止中のcandidateを後から利益・損失へ加えない。

## 5. 歴史実装parity

Stage51・54のledgerと照合した。

| 対象 | 一致 |
|---|---:|
| M1 source LONG | 972 / 972 |
| M5 source LONG | 326 / 326 |
| M5 rule・confirmation path | 57 / 57 |
| M1の月次research procedure | 51 / 52 |

M1の残り1件は、2023-10-08 02:21のexact M1 openがCSVに存在せず、過去診断では次の02:22へentryしていた。Stage55 Shadowではexact-M1契約を優先して無効化する。

Stage55のM1 detectorは2026年8月開始時に固定したbootstrap modelを使い、Shadow中は再学習しない。過去の月次再学習成績を、この固定modelの新しいbacktest成績として読み替えない。

これは条件救済ではなく、prospective runtimeのfail-closed修正である。

## 6. 観測終了gate

各familyについて、次の両方を満たすまで結論を出さない。

- closed trade 20件以上
- activationから6暦月以上

観測時に報告するのは、件数、勝率、PF、純損益、DD、月別結果、最大winner除外、2倍cost診断である。

次は禁止する。

- 途中の勝敗でQ70を変更
- confirmation時間を変更
- SL、TP、最大保有を変更
- 不利な月や片側familyを削除
- 自動promotion

## 7. 出力

state root:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_stage55_shadow`

主要ファイル:

- `runtime_state.json`
- `runtime_health.json`
- `outputs/source_m1_synthetic_long_ledger.csv`
- `outputs/source_m5_synthetic_long_ledger.csv`
- `outputs/shadow_candidate_ledger.csv`
- `outputs/shadow_trade_ledger.csv`
- `logs/shadow_runtime.log`

## 8. 起動手順

1. `01_INSTALL.bat`
2. `02_BOOTSTRAP_ACTIVATE.bat`
3. 初回は `config/local_config.json` が作られ、Notepadが開く。
4. H4、M15、M5、M1のCSV pathを正確に設定する。
5. `02_BOOTSTRAP_ACTIVATE.bat`を再実行する。
6. `READY_NO_BACKFILL_ACTIVATED`を確認する。
7. `03_RUN_LOOP.bat`を開いたままにする。
8. `04_STATUS.bat`でhealthを確認する。

CSV pathを推測したり、似たfileへfallbackしない。

## 9. 現在の判断

Shadow作成は妥当である。ただし、これは正式採用ではない。

- Stage54の正式survivor: 0
- Stage55: post-selection overfitを検証するobservation-only Shadow
- Discord: OFF
- MT5注文: OFF
- live-ready: OFF
