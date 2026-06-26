# GOLD_ML_V1 WATCH-029〜034 実装契約

Date: 2026-06-26  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Status: `AUDIT_ONLY_IMPLEMENTATION_CONTRACT`  
Authoritative stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`

## 0. この文書の目的

このチャットで追加・登録した候補を、将来コードへ実装する場合の再現条件を固定する。

対象:

- accumulated: `GML1-WATCH-029-A`, `GML1-WATCH-030-A`
- research WATCH: `GML1-WATCH-032-A`, `GML1-WATCH-033-A`
- research WATCH sibling variants: `GML1-WATCH-034-A/B/C`
- retired: `GML1-WATCH-031-A`

この文書は実装許可ではない。現在もaudit-onlyで、portfolio/live/MT5 order/DiscordはOFF。

## 1. 状態の正本

候補の状態は次の優先順で判断する。

1. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
2. 各candidate configのロジック・閾値
3. この実装契約
4. 診断レポート・過去メッセージ

重要:

- `WATCH-029-A`と`WATCH-030-A`の個別configには古い`controls.accumulated=false`が残るが、stack Wではaccumulated。状態判定はstackを正本とする。
- `WATCH-031-A`はTP3/TP4を含んだためretired。実装・再利用・ID再利用は禁止。
- `WATCH-034-A/B/C`は同じentry lineageの出口違い。1つのportfolioで3つを同時発注してはならない。比較する排他的variantである。

## 2. 絶対契約

### 2.1 システム隔離

- GOLD_ML_V1だけを使用する。
- 他のGOLD系、旧ロジック、DISC8、Stage41等をfallbackや補完に使わない。
- 既存frozen nineを変更しない。
- candidate registryはappend-only。ロジック変更は新candidate IDを発行する。

### 2.2 時刻

- CSV `time`はMT5 server bar-open時刻。
- M15 decision time = `M15.time + 15 minutes`。
- M1 entry timeはdecision timeと完全一致するM1 bar-open。
- JSTへ変換してentry条件を判定しない。時間帯条件はすべてMT5 server hour。
- 最新CSV行は契約上closed。open/as-of扱いにしない。
- H1/H4/M5は`bar_close_time <= decision_time`の最後のclosed barを`merge_asof(..., direction="backward", allow_exact_matches=True)`で結合する。
- exact M1が欠ける場合はnearest barへずらさず、候補をskipして監査ログへ残す。

### 2.3 因果性

- rolling high/lowは必ず`shift(1)`してcurrent decision barを含めない。
- previous-day high/lowはMT5 server dateで完了した前日だけから作る。
- session rangeは対象session完了後だけ使用する。
- future barをfeature、filter、tie-breakへ使わない。

### 2.4 M1約定

M1 OHLCはbid系列、spreadはpoint単位、XAUUSD pointは0.01として再現する。

LONG:

- entry ask = M1 bid open + entry spread × 0.01
- target/stop判定はbid high/low
- time exitはbid close

SHORT:

- entry bid = M1 bid open
- 各M1でdynamic ask OHLC = bid OHLC + そのM1 spread × 0.01
- target/stop判定はdynamic ask low/high
- time exitはdynamic ask close

共通:

- 同一M1でprotective levelとtargetの双方に触れ得る場合、protective levelを先に処理する。
- stress testはspread 2倍＋entry/exit各0.10 USD-price slippage。
- `USD`表記は口座損益ではなくXAUUSD価格差。

### 2.5 one-open

- lane内で1ポジションだけ。
- 新entryは`entry_time > occupied_until`の場合だけ許可する。
- `entry_time == prior exit_time`もskipする。
- portfolio全体one-openはまだ正式実装契約ではない。

## 3. 共通feature定義

### 3.1 Wilder ATR14

`TR = max(high-low, abs(high-prev_close), abs(low-prev_close))`。初期値は最初の14本平均、その後Wilder平滑。

### 3.2 ローソク足

`range = high - low`

- `body_frac = (close-open)/range`
- `close_pos = (close-low)/range`
- `lower_wick_frac = (min(open,close)-low)/range`
- `upper_wick_frac = (high-max(open,close))/range`
- `range_atr = range/ATR14`

range=0はNaNとしてcandidate false。

### 3.3 EMA/ADX state

各TFでEMA20、EMA50、ATR14、ADX14を計算。

- `gap20_50_atr = (EMA20-EMA50)/ATR14`
- `slope4_atr = (EMA20-EMA20.shift(4))/ATR14`
- `H4 range_state = H4 ADX14 <= 27 OR abs(H4 gap20_50_atr) <= 0.25`
- `not_strong_bear = NOT(H4 gap20_50_atr < -0.35 AND H4 slope4_atr < 0)`
- `not_strong_bull = NOT(H4 gap20_50_atr > 0.35 AND H4 slope4_atr > 0)`

## 4. GML1-WATCH-029-A — accumulated meta lane

Config:

`config/gold_ml_v1/watch029a_fixed5_simple_meta_lane_20260626.json`

### 4.1 凍結source stack

WATCH-029-Aは現在の15候補をsourceにしてはいけない。以下の13候補proposalを使う凍結meta lane。

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

source stack IDは`GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_P`。

### 4.2 実装前提

source proposal registryに最低限必要な列:

- candidate_id
- source_family
- direction
- entry_time
- decision M15 close
- exact source trigger identity

`exact_group_size`はone-openやdedupeの前に、13候補のproposalを`entry_time + direction`で数える。

`source family != H1-D1 existing`のcanonical family mapがrepo内で再現できない場合、推測して実装してはならない。まず凍結source registry/family mapを作る。

### 4.3 gate

13候補proposalを同一`entry_time + direction`で1行へcollapseし、次を判定。

Branch A:

- `exact_group_size <= 1`
- source familyが`H1-D1 existing`ではない

Branch B:

- LONG: `(prior_M15_high20 - M15_close)/M15_ATR14 >= 1.355958344`
- SHORT: `(M15_close - prior_M15_low20)/M15_ATR14 >= 1.355958344`
- entry MT5 server hourが14,15,16ではない

Final gate = A OR B。

`prior_M15_high20/low20`はshift(1) rolling 20。

### 4.4 exit

- TP +5
- emergency protective distance 10
- horizon 12h
- lane one-open

### 4.5 不変条件

- source stack、family map、group countの定義を変更したらWATCH-029-Aを変更せず新IDを発行する。
- 実装parity基準: one-open 198 trades、TP5 hit 77.7778%、PF2.60274。強コスト198 trades、PF2.24641。

## 5. GML1-WATCH-030-A — accumulated previous-day high sweep SHORT

Config:

`config/gold_ml_v1/watch030a_prev_day_high_sweep_short_20260626.json`

### 5.1 common entry

- direction SHORT
- `M15 high >= previous_day_high + 0.25 * M15 ATR14`
- same closed M15 `close <= previous_day_high`
- `close_pos <= 0.30`

Morning branch:

- `7 <= M15 bar-open hour < 13`
- `upper_wick_frac >= 0.35`

Evening branch:

- `16 <= hour < 22`
- `upper_wick_frac >= 0.20`
- reject if last closed H4 has `gap20_50_atr > 0.35 AND slope4_atr > 0`

Entry = common AND (morning OR evening)。

### 5.2 exit

- TP +5
- protective distance 10
- horizon 12h
- lane one-open

### 5.3 parity

- base one-open 106 trades、TP5 rate 71.6981%、PF1.84928
- strong cost 108 trades、PF1.49471
- exact/±60m overlap vs frozen existing13 and WATCH-029-Aは0

## 6. GML1-WATCH-032-A — high-win opening-range failed-break SHORT

Config:

`config/gold_ml_v1/watch032a_high_win_or_failed_break_short_20260626.json`

### 6.1 opening range

MT5 server dateごとに、M15 bar-open hour `13 <= hour < 14`のhigh/lowを集約する。14時以降のみ使用。

### 6.2 entry

- direction SHORT
- `14 <= M15 bar-open hour < 19`
- H4 range_state
- `M15 high >= OR13_high`
- `M15 close <= OR13_high`
- `upper_wick_frac >= 0.30`
- `close_pos <= 0.35`
- `M15 slope4_atr <= 0.2531587996`
- last closed H4 `slope4_atr <= 0.004782248063`

minimum sweep depthは設定しない。OR高値へのtouch/上抜け後の内側closeで成立。

### 6.3 exit

- TP +5
- protective distance 6
- horizon 24h

### 6.4 parity

- base 97 trades、TP5 hit 71.1340%、PF2.11916、DD18
- strong cost 98 trades、TP5 hit 69.3878%、PF1.89082
- current accumulated15相当とのexact overlap 0、±60m overlap 2

## 7. GML1-WATCH-033-A — compact rejection LONG

Config:

`config/gold_ml_v1/watch033a_high_win_compact_rejection_long_20260626.json`

WATCH-033-Aは3component proposalを統合し、componentごとのtargetを保持する。

### 7.1 completed block

MT5 server dateごとに、M15 bar-open hour `13 <= hour < 19`のrangeを作る。

- `R13_19_low = min(low)`
- trade windowは`19 <= hour < 24`

### 7.2 component proposal

Priority 1 `HW_BLOCK_5_5`:

- low <= R13_19_low
- close >= R13_19_low
- lower_wick_frac >= 0.15
- close_pos >= 0.75
- not_strong_bear
- TP5 / protective distance 5 / horizon 8h

Priority 2 `HW_BLOCK_DEEP_7.5_5`:

- low <= R13_19_low - 0.30*ATR14
- close >= R13_19_low
- lower_wick_frac >= 0.15
- close_pos >= 0.75
- TP7.5 / protective distance 5 / horizon 8h

Priority 3 `HW_ROLL20_5_5`:

- prior rolling20 low = `low.shift(1).rolling(20).min()`
- low <= rolling20 low - 0.30*ATR14
- close >= rolling20 low
- lower_wick_frac >= 0.20
- close_pos >= 0.65
- TP5 / protective distance 5 / horizon 8h

### 7.3 union filter and priority

3componentをproposal化した後、同一entry_timeは上記priority順で1つだけ残す。その後lane one-open。

残したproposalに次を追加filter:

- `range_atr <= 1.223196212`
- `lower_wick_frac >= 0.4319499106`

componentのTP5/TP7.5を一律化してはいけない。

### 7.4 time exit

8h以内にtarget/protective levelへ触れない場合はhorizon M1 closeで決済。positive exit rateには利益のtime exitが含まれるため、full target hit rateと混同しない。

### 7.5 parity

- base 70 trades、positive exit 71.4286%、full target hit 50%、PF2.43356、DD10
- strong cost 70 trades、PF2.14976、DD10.72

## 8. WATCH-034 common entry lineage

Configs:

- `config/gold_ml_v1/watch034a_tp75_practical_compression_long_20260626.json`
- `config/gold_ml_v1/watch034b_tp100_absolute_max_compression_long_20260626.json`
- `config/gold_ml_v1/watch034c_tp100_runner_compression_long_20260626.json`

### 8.1 exact entry

Current M15 indexをiとする。

- `inside_prev = high[i-1] <= high[i-2] AND low[i-1] >= low[i-2]`
- `range_atr = (high-low)/ATR14`
- `nr7_prev = range_atr[i-1] <= min(range_atr[i-7:i])`
- H4 `gap20_50_atr > 0`
- H4 `slope4_atr > 0`
- H1 `gap20_50_atr > -0.10`
- `19 <= current M15 bar-open hour < 24`
- `close[i] >= high[i-1]`
- `body_frac[i] >= 0.50`

entryはcurrent M15 close時刻のexact M1。

### 8.2 sibling exclusivity

A/B/Cは同じentry detectorのexit-policy比較。次のいずれか1つだけを選ぶ。

- Aだけ
- Bだけ
- Cだけ

A/B/Cを3注文として同時発注、件数合算、portfolio diversification扱いしてはならない。

## 9. GML1-WATCH-034-A — practical fixed TP75

- TP75
- protective distance 10
- horizon 168h
- one-open

Parity strong cost:

- 98 trades
- TP75 hit 17
- PF2.194952
- mean +8.743878
- total +856.90
- DD70.70
- 4年すべてtarget hitあり

## 10. GML1-WATCH-034-B — absolute fixed TP100

- TP100
- protective distance 5
- horizon 168h
- one-open

Parity strong cost:

- 112 trades
- TP100 hit 7
- PF2.094506
- mean +4.784554
- total +535.87
- DD81.60
- target hitは3年

TP125/150には観測hitがあるが2年に偏る。robust fixed maximumはTP100。

## 11. GML1-WATCH-034-C — staged TP100 runner

- initial protective distance 8
- milestone +50
- +50で25%を決済
- 残り75%のprotective levelをentry+10へ移動
- 残りtarget +100
- horizon 168h

### 11.1 M1 ordering

milestone未到達:

1. initial protective level
2. +50 milestone

+50を同一M1でhitした後:

1. new protective level entry+10
2. +100 runner target

milestone後の以後のM1:

1. protective level entry+10
2. runner target +100

これは保守的な順序。変更禁止。

### 11.2 PnL

- milestone realized = 25% × (+50 - exit slippage)
- lock exit = milestone realized + 75% × (+10 - exit slippage)
- runner exit = milestone realized + 75% × (+100 - exit slippage)
- horizon exitは残り75%をhorizon M1 closeでmark-to-market

Parity strong cost:

- 101 trades
- +50 milestone 22
- +100 runner hit 7
- PF2.279160
- mean +7.488787
- total +756.3675
- DD69.20

## 12. 実装順序

1. 共通causal feature engineとM1 execution engine
2. WATCH-030-A
3. WATCH-032-A
4. WATCH-033-A
5. WATCH-034 common detector + A/B/C exit policies
6. WATCH-029-Aを最後に実装

WATCH-029-Aは凍結13候補proposalとfamily mapが必要なため、独立raw detectorより後にする。

## 13. 必須出力schema

candidate proposal registry:

- candidate_id
- logic_version
- direction
- decision_time
- entry_time
- source_component / source_candidate_id
- source_family where applicable
- all threshold-driving feature values
- target policy
- protective policy
- horizon
- data cutoff / input hash

resolved trade registry:

- candidate_id
- entry_time
- exit_time
- direction
- entry bid/ask
- exit bid/ask
- spread at entry/exit
- target/protective values
- exit reason: target / protective / time / milestone-lock / runner
- realized PnL in XAUUSD price units
- same-M1 collision flag

## 14. 必須テスト

### 14.1 causality

future M1/M15/H1/H4を変更しても過去decisionのfeatureとproposalが変わらないこと。

### 14.2 time boundary

- previous day at MT5 server midnight
- OR13 range completion
- R13_19 range completion
- 19時trade window開始
- 24時境界
- H4 close exact match

### 14.3 execution

LONG/SHORT dynamic spread、same-M1 protective-first、time exit、missing exact M1、slippage stress。

### 14.4 one-open

entry==prior exitをskip、overlap中のproposalをskip、component priorityを固定。

### 14.5 parity

各候補のtrade count、year count、target hit、PF、total、DDをこの文書の期待値へ合わせる。丸め前CSVで一致確認する。

## 15. 未完了・実装blocker

- frozen nineの完全なexact trade registryは全てrepoに揃っていない。
- WATCH-029-Aのexact reproductionには13候補のproposal registryとcanonical source-family mapが必要。
- このチャットの大きなM1 resolved registriesは監査artifactとして生成したが、全てをGitHubへcommitしていない。コード実装時はraw CSVから再生成し、expected metricsと照合する。
- WATCH-034 A/B/Cのportfolio採用variantは未決定。
- accumulated15全体のauthoritative raw-event portfolio replayは未完了。

## 16. 禁止

- 実装のついでに閾値を丸める・改善する
- server hourをJST hourへ置換する
- H1/H4 current open barを使う
- M1が欠けたとき次のM1へ入る
- WATCH-029-Aをcurrent 15-candidate sourceへ差し替える
- WATCH-033-Aのcomponent targetを一律TP5またはTP7.5へ変える
- WATCH-034 A/B/Cを同時注文する
- research WATCHをaccumulated/liveへ自動昇格する
