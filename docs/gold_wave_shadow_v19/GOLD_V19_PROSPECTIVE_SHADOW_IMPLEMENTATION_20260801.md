# GOLD V19 Prospective Shadow 実装契約

日付: 2026-08-01  
対象: XAUUSD / GOLD  
モード: observation-only prospective shadow

## 1. 実装した候補

V19で正式に固定した主候補のみを実装する。

```text
SEMIANNUAL_EXPANDING
+ P90 past-only rank by direction
+ causal IMPULSE_EARLY episode
+ first eligible P90 only per episode
+ TP20 / SL10
```

歴史評価は169件、PF 2.030、純値幅 +730.96、最大DD 80.00、評価25か月で月平均6.76件だった。ただしこれは回顧結果であり、live利益の証明ではない。

## 2. 絶対境界

- MT5 broker-server naive timeをそのまま使用する。
- CSV最新行は契約上closedである。
- open/as-of足を作らない。
- exact M1だけでTP/SLを判定する。
- 上位足へのfallbackをしない。
- 同一M1でTPとSLの両方へ触れた場合はSL優先。
- 固定spreadは0.30ドル。
- entry時のrecorded spreadが30 pointsを超える候補はE40 originから除外する。
- 1ポジション非重複。
- episode当たり1回だけ。
- runner、2回目entry、片側削除を行わない。
- Discord、AI、MT5注文、実売買はOFF。

## 3. 方向ルーター

E40方向ルーターは短期スキャルピング方向器ではない。

- label: TP40 before SL20
- horizon: 720 exact M1 minutes
- causal H4/H1 features
- LONG/SHORTを別々に学習
- 過去60日のscore分布で方向別percentile rank
- 現在のMT5 server dateはrank referenceから除外

V19 Shadowでは、その中期方向priorと波動episodeのentry位置を結合する。

## 4. 曖昧波動grammar

未来確定ZigZagを使用しない。次の6尺度を因果的に計算する。

- M15_K080
- M15_K140
- H1_K080
- H1_K140
- H4_K060
- H4_K100

一つの厳密なエリオットカウントを断定せず、複数尺度を統合して `IMPULSE_EARLY` 等の状態を生成する。cycle位相はV17で追加価値がなく、実装しない。

## 5. episodeと初回P90

LONGとSHORTそれぞれについて、連続するclosed M15判定が `IMPULSE_EARLY` の間を一つのepisodeとする。

- M15判定が15分連続でない場合、新episodeとして扱う。
- `IMPULSE_EARLY`以外へ移った時点でepisodeを終了する。
- 選択方向のrankがP90へ初めて到達した候補だけを消費する。
- open position中でもepisodeは消費され、後から同episodeへ再entryしない。
- PC再起動後は直近状態を復元する。
- 起動時点で進行中の `IMPULSE_EARLY` episodeはno-backfillのため消費済みにする。

## 6. 因果的session horizon guard

V10/V19の歴史評価ではE40 label作成のため、entryから720分のexact M1連続性があるoriginだけが残っていた。この条件をprospectiveで未来を見て判定することはできない。

runtimeでは、すでに観測済みの当日session開始時刻を基準として、通常session終了を固定推定する。

- 月曜～木曜: session開始から1378分後を最後のM1とする。
- 金曜: session開始から1377分後を最後のM1とする。
- entry後720分を確保できないoriginは事前に除外する。
- 休日・短縮日は、事前に分かる場合だけ `session_overrides` へ固定登録できる。
- 想定外の早期終了やデータgapが後から判明したShadow取引はINVALIDとして記録する。

この因果的guardを歴史期間へ適用した監査では、V19の正式169件とentry timestampが169/169一致した。

```text
trades: 169
PF: 2.0299563195716415
net: +730.959999999995
unexpected-gap first candidates: 5
accepted-trade overlap: 169/169
```

## 7. score historyの成熟

新しいraw scoreを即座にrank referenceへ入れない。

1. raw scoreをpendingへ保存する。
2. 720 exact M1 minutesが揃うまで待つ。
3. 全区間が連続ならvalid score historyへ昇格する。
4. gapがあれば破棄してledgerへ記録する。
5. 当日scoreはrank referenceから除外する。

これにより、歴史評価で使われた「E40 label可能originだけのscore分布」を未来情報なしで再現する。

## 8. 半年更新

半年更新は自動で行う。

固定境界:

- 1月1日
- 7月1日

現在のactive boundaryは `2026-07-01`、次は `2027-01-01`。

更新時の動作:

1. 最新closed dataからactive boundaryを検出する。
2. 新boundary後、E40 labelに必要な720分のデータが揃うまでfail-closedにする。
3. 2023-01-01からboundary直前までのexpanding trainingを再構築する。
4. boundary直前6か月をcalibrationとする。
5. 新model、calibration、manifestをatomicに保存する。
6. old boundaryのrank historyを新modelへ持ち越さない。
7. 新modelが完成するまで旧modelへfallbackしない。

Shadowを2027年1月まで回さず停止した場合、当然ながら更新は一度も発生しない。後日再起動して新boundaryに到達していれば、その時点で自動構築する。

## 9. no-backfillと停止中の扱い

初回activate以前のcandidateは取引記録に入れない。

runtime停止中にclosed M15判定が複数進んでいた場合は、episode状態とscore ledgerを回復するが、missed candidateをShadow取引として採用しない。`RECOVERY_REPLAY_NOT_TRADED`として記録する。

これは「後からCSVを見て取引したことにする」backfillを防ぐためである。

## 10. 出力

state root:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow`

主要ファイル:

- `runtime_state.json`
- `runtime_health.json`
- `models/YYYY-MM-DD/manifest.json`
- `score_history.csv.gz`
- `pending_scores.csv.gz`
- `outputs/shadow_score_ledger.csv`
- `outputs/shadow_candidate_ledger.csv`
- `outputs/shadow_trade_ledger.csv`
- `outputs/score_history_invalid_gap_ledger.csv`
- `logs/shadow_runtime.log`

## 11. 起動手順

1. `01_INSTALL.bat`を実行する。
2. `02_BOOTSTRAP_ACTIVATE.bat`を初めて実行すると、`local_config.json`がなければexampleから作成してNotepadを開く。
3. 全時間足のCSV pathを正確に設定する。
4. `02_BOOTSTRAP_ACTIVATE.bat`を再実行する。
5. healthが`READY`であることを確認する。
6. `03_RUN_LOOP.bat`を開いたままにする。
7. `04_STATUS.bat`で状態を確認する。

CSV sourceを推測したり、似たファイルへfallbackしたりしない。

## 12. 現在の限界

GitHubへ実装しただけでは、ユーザーPC上のloopは起動しない。CSV pathを設定し、BATを実行した時点からProspective Shadowが始まる。

本Shadowの目的は新しい未来データで固定候補を観測することであり、短期間の勝敗を見てP85/P95、波動尺度、TP/SLを変更しない。
