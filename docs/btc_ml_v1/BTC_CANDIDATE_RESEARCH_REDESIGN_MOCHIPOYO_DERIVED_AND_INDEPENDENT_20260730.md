# BTC候補研究 再設計 — もちぽよ由来系統と独立ベクトル系統

- repository: `knitanr-a11y/xauusd-signal-lab`
- working branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- status: `DESIGN_FROZEN_IMPLEMENTATION_NOT_YET_AUTHORIZED`
- scope: `BTCUSD candidate research only`

## 0. 今回の正式判断

1. FF05フル履歴再実行のV3〜V11継ぎ足し実装は、今後の通常実行経路として使用しない。
2. 失敗記録、原因、コミットは監査履歴として残す。削除や隠蔽はしない。
3. FF01〜FF04で確認した因果・bar-open・exact-entry・fail-closed契約は、再設計でも維持する。
4. BTC7Rはselection provenance未証明のため隔離を継続する。
5. 不完全履歴FF05および未完走のrecovery実行から、候補採用・不採用・`NO_CANDIDATE`を結論しない。
6. 次の通常番号`FF06`は、この再設計をfresh-forwardの続きとして扱うか、新しい研究系列を開始するかを正式決定するまで使用しない。
7. 新しいBATや候補評価コードは、本設計と入力証拠契約の確認が終わるまで作らない。

## 1. 最終目的

目的は、過去バックテストで一度だけ良く見えるルールを作ることではない。

次を同時に満たすBTC研究・運用系を作る。

- BTCで将来も使える可能性がある候補を複数の異なる原理から育てる。
- もちぽよの実際のsource alertから、発火構造と状態遷移を証拠ベースで抽出する。
- もちぽよ完全複製を目的化せず、BTCでの収益性・安定性・損失制御を優先する。
- ただし、元アラートの再現と、勝ちやすさを高める変更を混同しない。
- 因果性、時刻、データ可用時点、コスト、重複ポジションをresearchからshadowまで同一契約にする。
- 候補追加、凍結、prospective shadow、停止、隔離、再検証の理由を後から追跡できるようにする。
- 単体候補の成績だけでなく、候補間の発火重複、損益相関、共同DD、役割分担を評価する。

## 2. 研究の二本柱

### 2.1 Track A — もちぽよsource-anchored BTC research

M7Cとcollectorに記録された実source alertを一次証拠として使用する。

M7CはBTCUSDとXAUUSDのdual-source prospective trackであり、BTCUSDを既に含む。BTC研究ではBTCUSD source eventを主教師とし、XAUUSD eventは構造比較用の副証拠とする。両銘柄を理由なく一つの母集団へ混ぜない。

最終目的は完全複製ではない。

- source alertをどの程度説明・近似できるか
- proxy extra alertに独自価値があるか
- source matchedとextraのどちらが利益・DDへ寄与するか
- 負けやすいextraを発火時点情報だけで抑制できるか
- BTC固有のentry timing、exit、risk controlで改善できるか

を分離して調べる。

### 2.2 Track B — independent-vector BTC research

もちぽよのRCI、stack、state transitionを前提にしない独立候補を作る。

最初から特定指標へ固定せず、相場原理を先に定義する。

候補原理の例:

- trend continuation / pullback continuation
- volatility compression to expansion
- breakout, retest and re-acceleration
- overextension / exhaustion mean reversion
- direction-asymmetric BTC behavior
- higher-timeframe regime plus lower-timeframe execution
- liquidity/time-window behavior, only when timestamp evidence supports it

同じ原理のパラメータ違いを別ベクトルとは呼ばない。Track Aとの発火・損益の相関が高い場合は、独立候補ではなく同族候補として扱う。

## 3. M7C・collectorの保護契約

M7C・collectorは変更対象ではなく、読み取り専用の証拠源である。

### 3.1 絶対に行わないこと

- collectorを停止、再起動、再初期化しない。
- M7Cを停止、再起動、再初期化しない。
- M7C prospective startを変更しない。
- runtime manifest、formula、threshold、grace、matching ruleを変更しない。
- M8C、M9V、M9Y、M10B、M10E、M10P、M10P2、M10W系をBTC研究のために変更しない。
- GOLD/MOCHIPOYO側のファイルへBTC研究結果を書き込まない。
- source alertをBTC candidate gateで黙って消した結果を、再現成功として扱わない。

### 3.2 読み取り対象候補

M7Cの正式資料が指定する現行証拠候補:

- `latest_m7c_prospective_shadow.json`
- `latest_m7c_shadow_loop_status.json`
- `latest_m7c_source_event_comparisons.csv`
- `latest_m7c_extra_proxy_signals.csv`
- `latest_m7c_proxy_signals.csv`
- `latest_m7c_proxy_decisions.csv`
- `m7c_shadow_forever.log`

collector障害・欠損・cursor確認が必要な場合だけ、collector log/status/resultを追加する。

### 3.3 BTC側への取り込み方法

1. 元ファイルは読み取り専用で開く。
2. BTC研究側へcontent-addressed snapshotとして複製する。
3. 各ファイルについて絶対パス、SHA256、bytes、mtime、取得時刻、source branch、source commitをmanifestへ記録する。
4. 複製後に元ファイルのSHAを再確認し、読取中変更があればそのrunを無効にする。
5. snapshot作成後の分析はBTC研究側のsnapshotだけを読む。
6. 自動探索、似たファイル名へのfallback、古いarchiveの自動採用は禁止する。

## 4. 証拠の階層

同じ「アラート」に見えても証拠強度を分ける。

1. `GENUINE_SOURCE_EVENT`
   - collectorが取得したもちぽよsource event。
2. `M7C_SOURCE_MATCHED`
   - supported source eventとone-to-oneで対応したM7C proxy transition。
3. `M7C_MISSED_SOURCE`
   - supported source eventだがM7C proxyで対応できなかったもの。
4. `M7C_EXTRA_CANDIDATE`
   - grace終了後もsource matchがないproxy transition。
5. `UNSUPPORTED_SOURCE_EVENT`
   - 現行M7Cがformal scoring対象にしていないREENTRY等。
6. `BTC_RESEARCH_DERIVED_SIGNAL`
   - 新BTC研究が独自生成した候補。source eventと同一視しない。

`SOURCE_MATCHED`、`MISSED_SOURCE`、`EXTRA_CANDIDATE`を同じ母集団へまとめて勝率を出さない。

## 5. イベント台帳

最初の実装成果物は売買候補ではなく、改変不能なsource-event ledgerである。

最低限の列:

- immutable `event_id`
- source file SHA and row locator
- source type
- symbol
- transition type: PRIMARY_LONG / PRIMARY_SHORT / LONG_EXIT / SHORT_EXIT / REENTRY / other
- source event time
- collection/observation time
- M7C decision time
- exact / within-one-M15 / missed / extra classification
- M7C state before decision and after transition
- supported-for-formal-recall flag
- duplicate/revision/late-event flags
- clock domain
- feature availability cutoff
- source payload hash
- outcome exposure status

### 5.1 outcome exposure status

各eventに次を付ける。

- `OUTCOME_UNSEEN`
- `OUTCOME_SEEN_DESCRIPTIVE_ONLY`
- `OUTCOME_USED_IN_PRIOR_DESIGN`
- `UNKNOWN_TREAT_AS_EXPOSED`

不明な場合はblindと主張せず、exposedとして扱う。

## 6. positive eventだけを学習しない

source alertの共通点だけを見ると、相場で頻出する条件を「発火原因」と誤認する。

比較対象を必ず作る。

- 同銘柄・近い時刻・近いATR帯で発火しなかったcontrol window
- source event直前のnear-miss window
- M7C missed source event
- M7C extra candidate
- 同じRCI turnでもstack/stateが異なるwindow
- 同じstackでもRCI turnがないwindow
- alert直後ではなく、同一regime内の通常window

control抽出はoutcomeを見ずに固定し、再現特徴を選ぶ段階ではwin/loss、MFE、MAE、PFを読まない。

## 7. もちぽよ由来研究を二層に分離する

### 7.1 Fidelity layer

問い:

- もちぽよsource eventの発火を、発火時点までの情報でどの程度説明できるか。
- M7Cのstate machine、RCI turn、stack、ENTRY/EXIT遷移のどこが必要か。
- exactではなく1本ずれる原因は何か。
- missed sourceはデータ欠損、state差、threshold差、未モデル遷移のどれか。

この層ではoutcomeを使用しない。

成果:

- source-event ledger
- feature-availability ledger
- trigger-signature hypotheses
- recall / timing / extra-rate report
- 再現不能理由の分類

### 7.2 Value layer

Fidelity layerでformula familyを凍結してから、初めて将来outcomeを開く。

問い:

- BTCでtradeableなENTRYとして価値があるか。
- source matched、extra、missed-recoveryのどこに価値があるか。
- entry confirmation、risk、exit、time stopで期待値を改善できるか。
- 損失削減gateが別期間でも再現するか。

完全再現より利益を優先してよいが、変更した部分を`fidelity change`、`execution change`、`loss-reduction change`に分類する。

## 8. Track Aのcandidate family構造

### A0. Frozen coverage anchor

現行M7Cのformula・state machineを基準線として保存する。これは自動的な売買候補ではなく、source coverage比較のanchorである。

### A1. Source-signature approximation family

source eventとcontrolをoutcome-blindで比較し、小さな事前登録grammarを作る。

候補特徴は実データ確認後に決める。RCI9、EMA stackだけで十分と決めつけない。

検討対象には次を含める。

- state machine context: IDLE / ACTIVE_LONG / ACTIVE_SHORT
- sequence and duration since previous transition
- RCI9 turn shape, speed, zone, persistence
- EMA alignment, slope, separation and recent transition
- current/open-only versus previous fully closed bar information
- candle shape and displacement known at decision time
- volatility and compression state
- recent swing/location context
- source alert cadence and duplicate suppression

### A2. BTC execution family

同じtriggerでも、entry timingとexit/riskを分ける。

- decision bar and exact entry row
- immediate entry versus preregistered confirmation
- stop construction
- target / time stop / transition exit
- one-position and overlap policy
- signal conflict priority
- same-bar collision priority

複数executionを試す場合は別hypothesisとしてtrial countへ含める。

### A3. Extra-value family

M7C extra candidateをsource matchedから分離し、追加価値を評価する。

- source matchedをextra gateで黙って除外しない。
- extra candidateのoutcome timestampを先に凍結する。
- extra gateは同じforward sampleで設計と性能主張をしない。

### A4. Loss-reduction family

損失を見てから条件を足すのではなく、次の順を守る。

1. base triggerとexecutionを固定
2. development期間でloss phenotypeを分類
3. pre-decision-only filter hypothesisを事前登録
4. 別のforward-chaining segmentで検証
5. prospective shadow中は変更しない

LONGとSHORT、source matchedとextra、regimeを必要に応じて分ける。件数が不足する場合は無理にfilterを作らない。

## 9. Track Bのcandidate family構造

Track Bでは、先にmechanism statementを書く。

各familyは最低限、次を持つ。

- why an edge may exist
- required information and availability time
- expected holding horizon
- expected failure regime
- directional symmetry or asymmetry
- overlap expectation with Track A
- finite parameter grammar
- maximum trial count

最初のinventory候補:

- B1 trend continuation / pullback
- B2 volatility compression / expansion
- B3 breakout-retest / re-acceleration
- B4 overextension / exhaustion mean reversion

同時に全familyを巨大gridで探索しない。label-free densityとevent availabilityを先に確認し、実行可能なfamilyだけをpreregisterする。

## 10. 時刻・因果・execution契約

FF04のbar-open semanticsを継承する。

- CSV `time`はbar OPEN。
- M5 OHLCは`time + 5m`以後に利用可。
- M15 OHLCは`time + 15m`以後に利用可。
- H1 OHLCは`time + 60m`以後に利用可。
- decision logicはnaive MT5 broker-server wall-clockを維持する。
- UTCは境界・報告にのみ使用する。
- exact entry rowがなければ`NO_TRADE`。
- nearest/next/interpolated/future fallbackは禁止。
- same-bar TP/SLは事前登録した保守優先順位を使用する。
- signal time、decision time、entry observation time、exit observation timeを別列にする。

M7C source timeとBTC candle timeのclock domainを推測で結合しない。source payload、collector timestamp、M7C decision timestamp、broker-server candle timestampの対応をsource inventoryで実証する。

## 11. データ分割とoutcome隔離

### 11.1 retrospective data

既に結果を見た期間を独立OOSとは呼ばない。

- 既存BTC researchで閲覧済みの2024〜2026履歴
- FF02の6 losses
- 不完全FF05の上位cell
- recovery過程で開いたsummary

はresearch-exposedとして記録する。

retrospective評価ではrandom splitを禁止し、nested forward-chainingだけを使う。それでも`retrospective walk-forward`であり、独立prospective evidenceではない。

### 11.2 prospective boundary

候補formula、execution、cost、conflict、monitoring contractをcommitで凍結した後に、新しいprospective startを設定する。

- 過去へのbackfill禁止
- start reset禁止
- shadow中のthreshold変更禁止
- outcomeを見た後のcandidate rescue禁止
- prospective結果はformula familyごとに独立保存

M7Cの既存prospective startはM7C source-fidelity trackの開始であり、新BTC trade candidateのprospective startとして流用しない。

## 12. 評価指標

### 12.1 Fidelity metrics

- supported source-event recall
- exact M15 match rate
- within-one-M15-bar match rate
- missed source count
- wrong-transition-nearby count
- extra candidate rate
- symbol / transition / regime別coverage
- timing error distribution

### 12.2 Trading value metrics

最低限:

- resolved trades
- win rate after costs
- PF after costs
- net R / net pips
- expectancy per trade
- initial-zero max DD
- maximum losing streak
- tail loss and adverse excursion summary
- LONG / SHORT別
- year / quarter / volatility / trend regime別
- cost and slippage sensitivity
- single-trade and single-period profit concentration

勝率だけで採用しない。PFだけでも採用しない。

### 12.3 Robustness metrics

- parameter-neighborhood stability
- walk-forward consistency
- calendar block bootstrap
- multiple-testing adjustment
- trial registry completeness
- minimum event/trade count
- missing-data sensitivity
- data-source stability

### 12.4 Portfolio metrics

Track AとTrack Bについて:

- signal overlap
- simultaneous position overlap
- PnL correlation
- loss-day / loss-week overlap
- joint max DD
- marginal net profit
- marginal PF
- marginal losing streak
- regime-level complementarity

単体で良い候補でも、既存候補と同じ場所で同じ負け方をする場合は優先度を下げる。

## 13. selection governance

すべての候補は次の状態を通る。

1. `HYPOTHESIS_PROPOSED`
2. `OUTCOME_BLIND_DENSITY_AUDITED`
3. `FORMULA_PREREGISTERED`
4. `RETROSPECTIVE_WALK_FORWARD_EVALUATED`
5. `RESEARCH_SURVIVOR_NOT_PROSPECTIVE`
6. `RULE_AND_RUNTIME_FROZEN`
7. `PROSPECTIVE_SHADOW_RUNNING`
8. `PROSPECTIVE_REVIEW_PASSED_OR_FAILED`
9. `LIVE_PROMOTION_EXPLICITLY_APPROVED_OR_REJECTED`

ルール:

- rejected candidateを削除しない。
- 全trialをregistryへ残す。
- threshold救済、期間救済、方向削除を結果閲覧後に行わない。
- 同じ仮説の微修正を新しい独立familyとして数えない。
- manual overrideは理由、時刻、変更前後を記録する。
- `retrospective survivor`を`live-ready`と呼ばない。

## 14. research・shadow・liveの分離

### Research

- 自由な探索は許可するが、input、code commit、config、trial count、outcome exposureを記録する。
- live runtimeやcollectorへ書き込まない。

### Frozen shadow

- formula、threshold、entry、exit、cost、state、startを固定する。
- order送信なし。
- source inputとdecision outputをappend-onlyで保存する。
- backtest/live parity sentinelを継続する。

### Live candidate

- user explicit approvalなしで作らない。
- Discord、MT5 order、lot設計は別契約。
- researchコードや古いcandidateへのfallback禁止。

### Monitoring and stop

監視対象:

- data freshness and cadence
- feature availability lag
- trigger frequency drift
- LONG/SHORT ratio drift
- volatility/regime distribution drift
- backtest/shadow decision mismatch
- duplicate signal and state divergence
- spread/slippage deterioration
- unexpected consecutive losses
- unresolved/open trade accumulation

停止時はprospective startやledgerを消さず、原因を記録してfail-closedとする。

## 15. 実装構造の原則

FF05 recoveryで起きた問題を再発させない。

禁止:

- V3がV2をimportし、V4がV3をimportする継ぎ足し構造
- monkey patchで入力探索を差し替える
- profile/environmentを隠して偶然のpath選択に依存する
- source directoryを複数stageで共有しながら削除・再生成する
- 自動探索とfallback
- success summaryだけ残りpayloadが消える構造

必須:

- 各stageは単独の明示input manifestを受け取る
- input path、SHA、rows、range、clock、availabilityを開始前に検証
- immutable snapshotをcontent hashで識別
- stage-specific workspace
- atomic publish
- one-run lock
- failureは1回で停止
- synthetic testだけでなくlocal exact-path integration test
- output schema and ZIP layout test
- source hashes before and after execution

## 16. 正式フェーズ

### D0 — Redesign freeze

本書、current state、next actionを作成する。コード実装なし。

### D1 — M7C / collector source inventory read-only

目的:

- exact files and schemas
- current source/event counts
- BTCUSD/XAUUSD split
- transition types
- timestamps and clock domains
- duplicate/revision/late-event behavior
- outcome exposure
- source data gaps

成果物:

- source allowlist
- file/hash manifest
- schema inventory
- clock-domain audit plan
- unresolved questions

停止条件:

- source fileが実行中に変化
- manifest mismatch
- prospective start mismatch
- collector/M7C abnormal status
- exact source provenance不明

### D2 — Immutable evidence snapshot and event ledger

sourceをBTC research側へ複製し、event ledgerを生成する。outcomeは開かない。

### D3 — Trigger-signature and control design

source eventとcontrol windowの抽出規則、feature availability、finite grammarをpreregisterする。

### D4 — Track A and Track B outcome-blind density audit

件数、欠損、重複、side/regime coverageを確認する。性能評価なし。

### D5 — Retrospective walk-forward evaluation

凍結formulaだけを評価し、trial registryとmultiple-testing controlを適用する。

### D6 — Complementarity and portfolio review

Track A/Track Bの重複・相関・共同DD・限界寄与を評価する。

### D7 — Rule/runtime freeze and prospective shadow

明示承認後だけ進む。新しいprospective boundaryを設定する。

## 17. D1で未決の事項

以下は推測で決めない。

1. collectorのgenuine source payloadに、どのtimestampを正式event timeとして使えるか。
2. BTCUSD source eventとbroker BTC candleのserver-time対応。
3. M7CのBTCUSDと現在BTC research CSVが同一symbol/cadence/price sourceか。
4. unsupported REENTRYを将来別familyとして扱うか、初期範囲外とするか。
5. source EXITをtrade exit教師として使うか、state transition証拠だけにするか。
6. M7C source eventのoutcomeがどこまで既に閲覧済みか。
7. 新研究系列のuser-facing stage prefixを、既存FF系列と分けるか。
8. prospective shadowへ進む最低件数・DD上限・コスト条件。

これらはD1の証拠を確認後、候補grammarを作る前にユーザーへ提示する。

## 18. 現在の次アクション

次はD1のみ。

- M7C・collectorの契約資料と提出対象を読み取り専用でinventoryする。
- GOLD/MOCHIPOYO runtimeへ変更を加えない。
- BTC candidate formulaを書かない。
- outcome、WR、PF、MFE、MAEを開かない。
- BATをユーザーへ実行依頼しない。
- D1結果と未決事項を提示してから、D2実装の承認を得る。
