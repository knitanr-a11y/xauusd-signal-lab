# GOLD_ML_V1 WATCH-029〜034 実装契約 V2

Date: 2026-06-26  
Status: `AUTHORITATIVE_AUDIT_ONLY_IMPLEMENTATION_CONTRACT_V2`  
Stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`

このV2をWATCH-029〜034の実装契約の正本とする。旧ファイル
`GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
は経緯参照用であり、状態判定・実装判断には使用しない。

## 1. 現在状態とこの契約の対象

stack全体:

- accumulated: 15
- Research WATCH: 9
- retired: `GML1-WATCH-031-A`
- implementation level: 2 / 6
- executable candidate implementation committed: 0
- audit-only
- portfolio/live/MT5 order/Discord/final signal: OFF

このV2契約の対象:

- accumulated: `GML1-WATCH-029-A`, `GML1-WATCH-030-A`
- Research WATCH: `GML1-WATCH-032-A`, `GML1-WATCH-033-A`, `GML1-WATCH-034-A/B/C`
- retired: `GML1-WATCH-031-A`

このV2の対象外だがstackに存在する既存Research WATCH:

- `GML1-WATCH-025-A`
- `GML1-WATCH-026-A`
- `GML1-WATCH-027-A`
- `GML1-WATCH-028-A`

`accumulated`は研究stack採用を意味し、コード実装済みを意味しない。

## 2. 状態と成績の正本

1. candidate state:
   `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
2. implementation completion and metrics:
   `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
3. corrections and known incomplete items:
   `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
4. entry/exit implementation contract:
   this V2 file

WATCH-029-Aと030-Aの個別configはaccumulatedへ同期済み。WATCH-031-Aはretiredへ同期済み。

## 3. 絶対禁止・隔離

- GOLD_ML_V1だけを使用する。
- GOLD V2、GOLD V3、旧GOLD、DISC8、Stage41その他のGOLD系を参照、fallback、補完に使わない。
- existing frozen nineを変更しない。
- candidate registryはappend-only。
- ロジック、閾値、exit、source stack、priority、時間帯のいずれかを変える場合は新candidate IDを発行する。
- Research WATCHを自動的にaccumulated、portfolio、liveへ昇格しない。
- WATCH-031-Aを復活、実装、source利用、ID再利用しない。

## 4. データ・時刻・因果性

- CSV `time`はMT5 server bar-open時刻。
- CSV最新行は契約上closed。open/as-of扱い禁止。
- M15 decision time = M15 bar-open + 15分。
- entryはdecision timeと完全一致するexact M1 bar-open。
- exact M1が欠ける場合は次や近傍のM1へずらさずskipし、監査ログへ残す。
- 時間帯条件はMT5 server hour。JSTへ変換して判定しない。
- H1/H4/M5は`bar_close_time <= decision_time`を満たす最後のclosed barだけをbackward as-of joinする。
- current open HTF barを使わない。
- rolling high/lowは`shift(1)`しcurrent decision barを含めない。
- previous-day high/lowはMT5 server dateで完了した前日だけから作る。
- session rangeはsession完了後だけ使用する。
- future barをfeature、filter、priority、tie-breakに使わない。

## 5. M1約定契約

M1 OHLCはbid系列。spreadはpoint単位、XAUUSD pointは0.01。

LONG:

- entry ask = M1 bid open + spread × 0.01
- target/protective判定はbid high/low
- time exitはbid close

SHORT:

- entry bid = M1 bid open
- 各M1のdynamic ask OHLC = bid OHLC + そのM1 spread × 0.01
- target/protective判定はdynamic ask low/high
- time exitはdynamic ask close

共通:

- same-M1でtargetとprotective levelの両方に触れ得る場合はprotective levelを先に処理する。
- strong cost = spread 2倍 + entry/exit各0.10 USD-price slippage。
- USD-priceは口座損益ではなくXAUUSD価格差。

## 6. one-open

- 各lane内で1ポジションだけ。
- 新entryは`entry_time > occupied_until`だけ許可。
- `entry_time == prior exit_time`もskip。
- portfolio全体one-openはまだ正式実装済みではない。

## 7. 共通feature

Wilder ATR14:

`TR = max(high-low, abs(high-prev_close), abs(low-prev_close))`

最初の14本平均で初期化し、その後Wilder平滑。

ローソク足:

- `range = high-low`
- `body_frac = (close-open)/range`
- `close_pos = (close-low)/range`
- `lower_wick_frac = (min(open,close)-low)/range`
- `upper_wick_frac = (high-max(open,close))/range`
- `range_atr = range/ATR14`

range=0はcandidate false。

EMA/ADX:

- `gap20_50_atr = (EMA20-EMA50)/ATR14`
- `slope4_atr = (EMA20-EMA20.shift(4))/ATR14`
- `H4 range_state = H4 ADX14 <= 27 OR abs(H4 gap20_50_atr) <= 0.25`
- `H4 not_strong_bear = NOT(H4 gap20_50_atr < -0.35 AND H4 slope4_atr < 0)`

## 8. WATCH-029-A — accumulated meta lane

Config:
`config/gold_ml_v1/watch029a_fixed5_simple_meta_lane_20260626.json`

### 8.1 sourceは凍結13候補

current accumulated15をsourceにしてはならない。source stack ID:

`GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_P`

source IDs:

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C
- GML1-WATCH-024-A
- GML1-WATCH-026-B
- GML1-WATCH-027-B
- GML1-WATCH-028-B

proposal registryに必要な列:

- candidate_id
- source_family
- direction
- entry_time
- decision M15 close
- exact source trigger identity

`exact_group_size`はone-open/dedupe前に`entry_time + direction`で数える。
canonical source-family mapを推測して実装してはならない。未固定なら先にregistry/family mapを作る。

### 8.2 gate

同一`entry_time + direction`を1行へcollapse。

Branch A:

- exact_group_size <= 1
- source family != H1-D1 existing

Branch B:

- LONG: `(prior_M15_high20 - close)/ATR14 >= 1.355958344`
- SHORT: `(close - prior_M15_low20)/ATR14 >= 1.355958344`
- MT5 server entry hourが14,15,16ではない

Final = A OR B。

### 8.3 exit/parity

- TP5
- protective distance 10
- horizon 12h
- one-open

Expected base:
198 trades、TP5 hit 77.7778%、PF2.60274。

Expected strong cost:
198 trades、PF2.24641。

## 9. WATCH-030-A — accumulated previous-day high sweep SHORT

Config:
`config/gold_ml_v1/watch030a_prev_day_high_sweep_short_20260626.json`

Common:

- SHORT
- `M15 high >= previous_day_high + 0.25*ATR14`
- same closed M15 `close <= previous_day_high`
- close_pos <= 0.30

Morning:

- MT5 hour 7〜12
- upper_wick_frac >= 0.35

Evening:

- MT5 hour 16〜21
- upper_wick_frac >= 0.20
- reject if last closed H4 `gap20_50_atr > 0.35 AND slope4_atr > 0`

Exit:

- TP5
- protective distance 10
- horizon 12h
- one-open

Expected base:
106 trades、TP5 hit 71.6981%、PF1.84928。

Expected strong cost:
108 trades、PF1.49471。

## 10. WATCH-032-A — Research WATCH high-win SHORT

Config:
`config/gold_ml_v1/watch032a_high_win_or_failed_break_short_20260626.json`

OR13:
MT5 server 13:00〜13:59のhigh/low。14時以降だけ使用。

Entry:

- SHORT
- MT5 hour 14〜18
- H4 range_state
- M15 high >= OR13 high
- M15 close <= OR13 high
- upper_wick_frac >= 0.30
- close_pos <= 0.35
- M15 slope4_atr <= 0.2531587996
- last closed H4 slope4_atr <= 0.004782248063

minimum sweep depthは設定しない。

Exit:

- TP5
- protective distance 6
- horizon 24h

Expected base:
97 trades、TP5 hit 71.1340%、PF2.11916、DD18。

Expected strong cost:
98 trades、TP5 hit 69.3878%、PF1.89082。

## 11. WATCH-033-A — Research WATCH compact rejection LONG

Config:
`config/gold_ml_v1/watch033a_high_win_compact_rejection_long_20260626.json`

MT5 13:00〜18:59のcompleted block lowを作り、trade windowは19:00〜23:59。

Priority 1 `HW_BLOCK_5_5`:

- low <= block low
- close >= block low
- lower_wick_frac >= 0.15
- close_pos >= 0.75
- H4 not_strong_bear
- TP5 / protective 5 / 8h

Priority 2 `HW_BLOCK_DEEP_7.5_5`:

- low <= block low - 0.30*ATR14
- close >= block low
- lower_wick_frac >= 0.15
- close_pos >= 0.75
- TP7.5 / protective 5 / 8h

Priority 3 `HW_ROLL20_5_5`:

- prior rolling20 low = `low.shift(1).rolling(20).min()`
- low <= rolling20 low - 0.30*ATR14
- close >= rolling20 low
- lower_wick_frac >= 0.20
- close_pos >= 0.65
- TP5 / protective 5 / 8h

同一entry_timeはpriority順で1つだけ残す。その後one-open。
追加filter:

- range_atr <= 1.223196212
- lower_wick_frac >= 0.4319499106

component targetを一律化しない。
8h time exitを使用。positive exit rateとfull target hit rateを混同しない。

Expected base:
70 trades、positive exit 71.4286%、full target hit 50%、PF2.43356、DD10。

Expected strong cost:
70 trades、PF2.14976、DD10.72。

## 12. WATCH-034 common entry

Configs:

- `config/gold_ml_v1/watch034a_tp75_practical_compression_long_20260626.json`
- `config/gold_ml_v1/watch034b_tp100_absolute_max_compression_long_20260626.json`
- `config/gold_ml_v1/watch034c_tp100_runner_compression_long_20260626.json`

Current M15 indexをiとする。

- `inside_prev = high[i-1] <= high[i-2] AND low[i-1] >= low[i-2]`
- `range_atr = (high-low)/ATR14`
- `nr7_prev = range_atr[i-1] <= min(range_atr[i-7:i])`
- last closed H4 gap20_50_atr > 0
- last closed H4 slope4_atr > 0
- last closed H1 gap20_50_atr > -0.10
- MT5 hour 19〜23
- current close >= prior M15 high
- current body_frac >= 0.50

entryはcurrent M15 close時刻のexact M1。

A/B/Cは同じentry detectorの排他的exit variant。次の1つだけを選ぶ。
同時注文、件数合算、損益合算、diversification扱いは禁止。

## 13. WATCH-034-A

- fixed TP75
- protective distance 10
- horizon 168h
- one-open

Expected strong cost:
98 trades、TP75 hit 17、PF2.194952、mean +8.743878、total +856.90、DD70.70。

## 14. WATCH-034-B

- fixed TP100
- protective distance 5
- horizon 168h
- one-open

Expected strong cost:
112 trades、TP100 hit 7、PF2.094506、mean +4.784554、total +535.87、DD81.60。

TP125/150はhitが2年に偏るためrobust fixed maximumではない。

## 15. WATCH-034-C

- initial protective distance 8
- milestone +50
- +50で25%決済
- 残り75%を+100へ
- milestone後の残りprotective level = entry+10
- horizon 168h

M1 ordering:

milestone未到達:
1. initial protective
2. +50 milestone

+50を同一M1でhitした後、および以後:
1. entry+10 protective
2. +100 runner target

この保守的順序を変更しない。

Expected strong cost:
101 trades、+50 milestone 22、+100 hit 7、PF2.279160、mean +7.488787、total +756.3675、DD69.20。

## 16. 現在の実装状況

WATCH-029-A、030-A、032-A、033-A、034-A/B/Cは全てLevel 2 / 6。

完了:

- audit prototype/backtest
- config
- metrics
- implementation contract

未実装:

- executable detector
- exact-M1 integration
- parity tests
- authoritative portfolio integration
- runtime/live

## 17. 推奨実装順

ユーザーが明示的に実装を依頼した場合だけ開始する。

1. shared causal feature engine
2. shared exact-M1 execution engine
3. WATCH-030-A
4. WATCH-032-A
5. WATCH-033-A
6. WATCH-034 common detector + 排他的exit policies
7. WATCH-029-Aを最後

## 18. 必須出力

proposal registry:

- candidate_id / logic_version
- direction
- decision_time / entry_time
- source component/candidate/family
- threshold-driving feature values
- target/protective/horizon
- data cutoff / input hash

resolved trade registry:

- candidate_id
- entry/exit time
- direction
- entry/exit bid/ask
- entry/exit spread
- target/protective values
- exit reason
- realized PnL in XAUUSD price units
- same-M1 collision flag

## 19. 必須テスト

- causality: future dataを変えても過去proposalが変わらない
- MT5 server midnightとsession boundary
- closed H4 exact match
- LONG/SHORT dynamic spread
- missing exact M1 skip
- same-M1 protective-first
- time exit
- slippage stress
- entry==prior exit skip
- component priority
- candidate別trade count/year count/target hit/PF/total/DD parity

## 20. 既知のblocker

- frozen nineの完全exact registryが未整備
- WATCH-029-Aの凍結13 proposal registryとfamily mapが未固定
- accumulated15 authoritative raw-event portfolio replay未完了
- 大きなM1 resolved registriesと探索scriptの多くはGitHub executable sourceではない
- WATCH-034 A/B/Cの最終採用variant未決定
- true prospective実績0件

## 21. 禁止

- 閾値を丸める、改善する
- MT5 server hourをJSTへ置換する
- current open HTFを使う
- missing M1を次のM1で代用する
- WATCH-029-Aをcurrent15 sourceへ変更する
- WATCH-033-Aのcomponent target/priorityを変える
- WATCH-034 A/B/Cを同時運用または成績合算する
- retired 031-Aを使用する
- 明示指示なしに実装、昇格、live変更する
