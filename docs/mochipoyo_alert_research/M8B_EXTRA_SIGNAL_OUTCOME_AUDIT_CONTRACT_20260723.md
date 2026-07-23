# MOCHIPOYO M8B Extra Signal Outcome Audit Contract

## 目的

M8Bは、M7C formal gate到達時点で既に固定されたextraを、**実トレードとして優位性があるか**評価するためのaudit-only Stageである。

最終目的は「もちぽよを厳密複製すること」ではない。評価の中心は、勝率・PF・値動き期待値・DD・連敗・頻度である。もちぽよsourceはcoverage/referenceとして扱うが、source matchそのものを最終promotion条件にはしない。

## Frozen population

- finalized extra signal: 36
- extra PRIMARY entry: 18
- extra EXIT action: 18
- pending source-arrival grace: 2（M8B対象外）

36 signalを36 tradeとは数えない。

WR/PFの母集団は、finalized extraのPRIMARY_LONG / PRIMARY_SHORTから開始した18 tradeのみとする。

## Trade pairing

各tickerのfrozen M7C proxy state-machine streamで、PRIMARY_LONG/PRIMARY_SHORTを次の対応EXITへ結ぶ。

- PRIMARY_LONG -> next LONG_EXIT
- PRIMARY_SHORT -> next SHORT_EXIT

prospective start以前から存在したbootstrap positionの最初のEXITは、post-start ENTRYが無いためtrade成績から除外する。

M7C formal freezeではextra ENTRY 18件は全て対応EXITまで解決済みである。後から増えたsignalを足してこの18件を救済しない。

extra EXIT 18件は親tradeのclose actionであり、独立tradeとしてWR/PFへ二重計上しない。別明細で監査する。

## Execution price

判定時刻はfrozen proxy decisionの`current_server_open`。

そのMT5 server-timeと**完全一致するM1 bar open**だけを使用する。nearest bar / same-minute代替は行わない。

M1 chart modeはBIDを要求する。

- LONG entry: bid open + spread points × SYMBOL_POINT
- LONG exit: bid open
- SHORT entry: bid open
- SHORT exit: bid open + spread points × SYMBOL_POINT

MqlRatesのspreadを使用し、SYMBOL_POINTはaudit実行時にMetaTrader5 `symbol_info()`から取得する。

## Cost sensitivity

M8B V1では以下を固定し、結果を見て変更しない。

- primary: historical spread × 1.0
- sensitivity: historical spread × 1.5
- sensitivity: historical spread × 2.0

commission / swapはM8B V1ではモデル化しない。したがって結果はspread-adjustedかつcommission/swap控除前である。lot sizingと口座通貨ベースのportfolio net profitはM8Dで別契約として固定する。

## Metrics

18 extra-entry tradesについて以下を集計する。

- count
- win rate
- PF（spread-adjusted return bps）
- net return bps sum
- average / median return bps
- max drawdown bps
- max losing streak
- calendar-day trade frequency
- ticker別
- LONG/SHORT別
- entry/exit origin組合せ別

勝率だけを上げるために発火条件を極端に厳しくし、trade frequencyを潰すことは目的ではない。

## Anti-overfit

M8Bの18件を見てルールを作り、その同じ18件の成績を「改善後実績」と主張してはならない。

M8BはM8C gate設計の探索材料には使えるが、M8Cの性能主張は新しいforward sampleまたは独立freeze sampleで検証する。

SOURCE_MATCHEDを将来performance ruleの対象にする場合も、黙って削除しない。明示契約と独立検証を先に行う。

## Safety

継続:

- audit-only ON
- Discord OFF
- MT5 order OFF
- live ready OFF
- final signal OFF
- entry gate OFF
- M7C formula/threshold/runtime manifest/prospective start変更禁止
