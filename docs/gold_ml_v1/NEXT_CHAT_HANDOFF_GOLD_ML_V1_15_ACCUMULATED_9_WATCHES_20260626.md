# NEXT CHAT HANDOFF — GOLD_ML_V1

Date: 2026-06-26  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Current stack: `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`  
Status: `FIFTEEN_ACCUMULATED_WITH_NINE_RESEARCH_WATCHES`  
Mode: `AUDIT_ONLY`

## 1. 新チャットが最初に読むもの

次の順で読む。

1. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_15_ACCUMULATED_9_WATCHES_20260626.md`
2. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
3. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
4. 実装・検証対象のcandidate config
5. 必要な診断doc

候補状態はstack fileを正本とする。

## 2. 絶対条件

- GOLD_ML_V1だけを扱う。
- audit-onlyを維持する。
- live、MT5 order、Discord、final signalはOFF。
- existing frozen nineを変更しない。
- candidate registryはappend-only。
- 閾値・exit・source stackを変更する場合は新ID。
- CSV `time`はMT5 server bar-open。
- CSV最新行はclosed。
- H1/H4/M5はclosed barだけをcausal as-of join。
- exact M1 entry、dynamic spread/bid-ask、same-M1 protective-first。
- 時間帯条件はJSTではなくMT5 server hour。
- `USD`はXAUUSD価格差で、口座損益ではない。

## 3. raw data cutoff

このチャットで使った診断データ終端:

- M1: 2026-06-19 19:54 MT5 server time
- M5: 2026-06-19 19:50
- M15: 2026-06-19 19:45
- H1: 2026-06-19 19:00
- H4: 2026-06-19 16:00
- D1: 2026-06-19 00:00

2024〜2026は診断で何度も見ている。true prospectiveは2026-06-26より後。

## 4. 現在のaccumulated 15

1. GML1-PROV-007
2. GML1-PROV-008
3. GML1-WATCH-022-B
4. GML1-PROV-010
5. GML1-PROV-015
6. GML1-PROV-020
7. GML1-WATCH-021-A
8. GML1-WATCH-021-B
9. GML1-WATCH-021-C
10. GML1-WATCH-024-A
11. GML1-WATCH-026-B
12. GML1-WATCH-027-B
13. GML1-WATCH-028-B
14. GML1-WATCH-029-A
15. GML1-WATCH-030-A

このチャットでaccumulatedへ追加したのは029-Aと030-A。

重要:

- 個別029/030 configの`controls.accumulated=false`は古い研究時点の値。
- 現在の状態はstack Wのaccumulated listを正とする。

## 5. 現在のResearch WATCH 9

既存:

- GML1-WATCH-025-A
- GML1-WATCH-026-A
- GML1-WATCH-027-A
- GML1-WATCH-028-A

このチャットで登録:

- GML1-WATCH-032-A — high-win failed-break SHORT、TP5/SL6
- GML1-WATCH-033-A — compact rejection LONG、TP5/7.5、SL5
- GML1-WATCH-034-A — practical fixed TP75 LONG
- GML1-WATCH-034-B — absolute robust fixed TP100 LONG
- GML1-WATCH-034-C — +50部分利確後TP100 runner LONG

Retired:

- GML1-WATCH-031-A — TP3/TP4を含み、ユーザーの最低TP5条件に違反。実装・再利用禁止。

## 6. このチャットの問題意識

### 6.1 accumulated count audit

nominal候補発火の約70%が重複していた。

- nominal 1545
- unique entry_time+direction 461
- global one-open reference 429
- 2026 unique 55、one-open 51

候補を増やしても同じ時刻に発火するだけでは意味がないため、以後は低重複・別mechanism・one-openを重視した。

### 6.2 ユーザー要求

- コンスタントに最低5ドル価格を狙う
- TP3/TP4は禁止
- 負けを削り、勝ちやすい場所を探す
- さらにTPを最大化する

## 7. WATCH-029-A — accumulated fixed-five meta lane

Config:

`config/gold_ml_v1/watch029a_fixed5_simple_meta_lane_20260626.json`

特徴:

- 凍結13候補をproposal engineとして使うmeta lane
- duplicate collapse後の単独発火、またはM15 directional roomが十分な発火だけを残す
- TP5 / emergency distance 10 / 12h
- 198 trades、TP5 hit 77.78%、PF2.603
- 2026 23 trades、PF2.375、+55

注意:

- raw独立detectorではない。
- sourceは当時の13候補stack Pで固定。current 15へ差し替え禁止。
- source stackを変える場合は新ID。

## 8. WATCH-030-A — accumulated independent sweep SHORT

Config:

`config/gold_ml_v1/watch030a_prev_day_high_sweep_short_20260626.json`

特徴:

- 前日高値を0.25ATR以上上抜いた後、同じM15で内側へ戻るSHORT
- 朝branchと夕方branch
- TP5 / emergency distance 10 / 12h
- 106 trades、TP5 rate 71.70%、PF1.849
- 2026 14 trades、PF3.0、+40
- existing13および029-Aと±60分重複0

SL10を縮めると年別安定性が低下したため、030-A自体は変更しない。

## 9. WATCH-032-A — high-win SHORT

Config:

`config/gold_ml_v1/watch032a_high_win_or_failed_break_short_20260626.json`

- 13:00〜13:59 opening range高値のfailed breakout
- 14:00〜18:59
- H4 range state
- M15/H4上昇傾斜が止まった後だけSHORT
- TP5 / protective distance 6 / 24h

結果:

- base 97 trades
- TP5 hit 71.13%
- PF2.119
- DD18
- strong cost TP5 hit 69.39%、PF1.891
- 2026 14 trades、11 TP、PF3.056
- current accumulated15相当との±60分重複約2%

現時点のhigh-win最有力。

## 10. WATCH-033-A — high-win LONG

Config:

`config/gold_ml_v1/watch033a_high_win_compact_rejection_long_20260626.json`

- 夜間のcompleted 13:00〜19:00 block lowまたはrolling20 lowのsweep/reclaim
- 大き過ぎない足、非常に大きいlower wickだけ
- 3componentのTP5/TP7.5を保持
- protective distance 5 / 8h

結果:

- 70 trades
- positive exit 71.43%
- full configured target hit 50%
- PF2.434
- DD10
- strong cost PF2.150

注意:

positive exitにはprofitable time exitを含む。TP hit 71%と説明してはいけない。

## 11. WATCH-034 lineage — TP最大化

共通entry:

- prior M15がInside + NR7
- H4 EMA20-EMA50 gap > 0
- H4 EMA20 slope4 > 0
- H1 gap > -0.10 ATR
- MT5 server 19:00〜23:59
- current M15 close >= prior M15 high
- bullish body fraction >= 0.50

A/B/Cは同じentryの排他的exit variant。3つを同時運用・件数合算してはいけない。

### 11.1 WATCH-034-A

Config:

`config/gold_ml_v1/watch034a_tp75_practical_compression_long_20260626.json`

- fixed TP75
- protective distance 10
- horizon 168h
- strong cost 98 trades、17 TP、PF2.195、mean +8.744、DD70.7
- 4年すべてTP75 hitあり

実用primary。

### 11.2 WATCH-034-B

Config:

`config/gold_ml_v1/watch034b_tp100_absolute_max_compression_long_20260626.json`

- fixed TP100
- protective distance 5
- horizon 168h
- strong cost 112 trades、7 TP、PF2.095、mean +4.785、DD81.6
- target hitは3年

robust fixed TP上限確認用。実用primaryではない。

### 11.3 WATCH-034-C

Config:

`config/gold_ml_v1/watch034c_tp100_runner_compression_long_20260626.json`

- initial protective distance 8
- +50で25%利確
- 残り75%を+100へ
- +50後、残りprotective levelをentry+10へ
- horizon 168h
- strong cost 101 trades、7 runner hit、PF2.279、mean +7.489、DD69.2

TP100を維持しつつ、固定TP100より実用バランスが良い。

TP探索結論:

- observed fixed target hit上限: 150
- robust fixed上限: 100
- practical fixed: 75
- robust runner上限: 100
- runner TP200: hit 0

## 12. 実装に必要な文書

必ず読む:

`docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`

この文書に以下を固定済み:

- causal join
- dynamic bid/ask
- feature formula
- exact session boundary
- 029 frozen source stack
- 032 H4 range-state formula
- 033 component priorityと個別TP
- 034 common entryのexact formula
- 034-C same-M1 runner順序
- 必須schema
- parity基準
- 実装blocker

## 13. 推奨実装順

実装をユーザーが明示的に依頼した場合のみ進める。

1. shared causal feature engine
2. shared exact-M1 execution engine
3. WATCH-030-A
4. WATCH-032-A
5. WATCH-033-A
6. WATCH-034 common detector + A/B/C exit policy
7. WATCH-029-Aは最後

029-Aは凍結13候補proposal/family map依存のため最後。

## 14. 未完了

- accumulated15全体のauthoritative raw-event portfolio replay
- frozen nine全てのexact registry body確保
- WATCH-029-A source proposal registry/family mapのrepo内固定
- WATCH-034 A/B/Cの最終採用variant決定
- 2026-06-26以降のtrue prospective評価
- live実装

## 15. 次チャットの開始時にしてはいけないこと

- WATCHを自動的にaccumulatedへ昇格しない
- live/MT5/Discordを触らない
- 031-Aを復活させない
- 029-Aをcurrent15 sourceで再計算しない
- 034-A/B/Cを3つ同時に運用しない
- 2024〜2026を未使用holdoutと呼ばない
- TP3/TP4候補を再提案しない
- ユーザーの新指示なしに実装を開始しない

## 16. このチャットの主要commit

- WATCH-029-A config: `d3ba72678c6f15786cc209c1944c7d281295c5fb`
- WATCH-029-A accumulated: `2d5436ce04ce08c16c5d571ccacb91fcc3e31310`
- WATCH-030-A config: `0e5bbb27e72f987928c0c065afd25785fec8a65a`
- WATCH-030-A accumulated: `3343f6139be0627e8d87142b4b14df12f681c365`
- WATCH-032-A config: `02f477b93ffe6309ad19910cf5fb44d4a1818bfb`
- WATCH-033-A config: `02f870c168418e37ee97435caf1a7c9f7dfd6698`
- WATCH-034-A config: `bf2f3d677ebc82899911f8bdc4e911ab365bda3f`
- WATCH-034-B config: `76a10bfe8853e92a78908bcc5b38c4c62548db5f`
- WATCH-034-C config: `e59bf46365ab9576bc56c314677e0eeed70d88b1`
- current stack W: `22781e105514d6cba0d800e7cc3cc0951dbe14d4`
- TP-max result: `58772481ac0d054aa90b1f5c6ec8f0845b26316a`
- TP-max doc: `71f42b9353f994c58b457c428e636ba76a803b45`
- implementation contract: `02885350f6b9b113aedf6a1f37f4ff2364e09078`

## 17. 次チャットの最初の応答

新チャットは上記文書とstackを実際に読み、次を短く報告する。

- stack ID
- accumulated数
- research WATCH数
- retired ID
- audit-onlyを維持すること
- ユーザーの次の指示を待つこと

理解確認のために過去候補を勝手に再計算しない。
