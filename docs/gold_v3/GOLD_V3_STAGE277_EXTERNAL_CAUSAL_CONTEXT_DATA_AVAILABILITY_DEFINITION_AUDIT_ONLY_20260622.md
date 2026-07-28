# GOLD V3 Stage277 定義固定
## External Causal Context Data Availability Audit

作成日: 2026-06-22  
状態: `GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_DEFINITION_LOCKED_AUDIT_ONLY`

## 1. 目的

Stage276でOHLC内部のsequence / state-transition探索を完了し、2024 discovery leadが0だったことを受け、次の候補探索を始める前に、GOLD以外のentry-known情報源が現在のbroker / MT5 server上で実在し、同一の時刻契約で取得可能かだけを監査する。

このStageではperformanceを評価しない。model、feature grid、candidate、threshold、exit、方向filter、health gateを作らない。

## 2. 正式な開始状態

- 現在: `GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`
- Stage276は完了済みであり、再実行・threshold緩和・片方向救済を行わない。
- current Specialist Health Router V3は変更しない。
- phase2 HV retestは`SHADOW-only`のまま維持する。

## 3. 絶対禁止事項

- GOLD V2、旧GOLD、DISC8、Stage41を読まない・使わない・参照しない・fallbackしない。
- brokerに存在しないsourceを推測で作らない。
- 似たsymbolを黙って置き換えない。
- Yahoo、別broker、別market、別timezoneへ黙ってfallbackしない。
- missing barを補間しない。
- nearest futureを使わない。
- 形成中barをinventoryへ含めない。
- Web上の時刻をMT5 server時刻へ推測変換しない。
- source availability確定前にperformance gridを始めない。
- Stage276 candidateを救済しない。
- live promotion、final signal、MT5注文、Discord通知、partial closeを行わない。

## 4. 優先source group

1. `XAGUSD`
2. `USDJPY`
3. `EURUSD`
4. `US500_RISK_PROXY`
5. `NAS100_RISK_PROXY`
6. `USD_INDEX_PROXY`
7. `YIELD_PROXY`
8. `ECONOMIC_CALENDAR`

symbol名は事前固定しない。MT5 serverが返したexact symbolをそのまま台帳化する。

文字列tokenによるsource group分類はinventory候補ラベルに限る。自動採用・自動置換・ACTIVE化ではない。複数候補があれば全候補を残し、人手で結果を見て都合のよいsymbolを選ばない。

## 5. Broker / server identity契約

Stage273で確認済みのGOLD baseline:

- account server: `XMTrading-MT5 3`
- exact GOLD symbol: `GOLD#`

Stage277のexportは同じMT5端末・同じaccount server・同じGOLD baseline chartから実行する。

次が一致しない場合は`BLOCKED`:

- broker company
- account server
- GOLD baseline exact symbol
- CSV間のidentity

## 6. 時刻・確定足契約

- CSVの`time`はbroker / MT5 serverのbar OPEN時刻。
- JSTへ変換しない。
- Stage277 exporterはclosed barだけを数える。
- availabilityは次で固定する。

| timeframe | source close availability |
|---|---:|
| M1 | `time + 60s` |
| M5 | `time + 300s` |
| M15 | `time + 900s` |
| H1 | `time + 3600s` |
| H4 | `time + 14400s` |
| D1 | `time + 86400s` |

将来のcandidate作成時も、使用可能なのは`source_close_time <= decision_time`のrowだけとする。

CSV最新行はexport時点でclosedであることを契約で保証する。形成中barは書き出さない。

## 7. History coverage契約

監査対象期間:

- 2023-01-01 00:00:00 server time inclusive
- 2027-01-01 00:00:00 server time exclusive
- 実効終了はexport開始時のserver timeまで

各exact symbolについて、次をM1 / M5 / M15 / H1 / H4 / D1で取得する。

- row count
- first / last bar OPEN time
- 2023 / 2024 / 2025 / 2026別row count
- duplicate count
- non-monotonic count
- raw interval gap count
- max raw gap seconds
- CopyRates error count
- empty chunk count
- status

raw gapはweekend・session close・holidayを含む可能性があるため、自動的にmissing barと断定しない。weekly trading sessionは別CSVへ保存する。

## 8. Spread契約

symbol inventoryでは次を保存する。

- digits
- point
- current spread points
- floating spread flag
- tick size
- tick value
- contract size

price単位への換算は`spread_price = spread_points * point`と明記する。

Stage277はspreadを用いたperformance評価を行わない。

## 9. Source status分類

- `OBSERVED_ALL_TIMEFRAMES_AVAILABLE`
- `OBSERVED_PARTIAL_TIMEFRAME_AVAILABILITY`
- `BROKER_SYMBOL_OBSERVED_NO_RATES_RETURNED`
- `NO_BROKER_SYMBOL_OBSERVED`
- `BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED`
- identity / safety契約違反時はStage全体を`BLOCKED`

取得不能sourceは削除せず、rejected / unavailable ledgerへ残す。

`ECONOMIC_CALENDAR`はsymbol sourceではないため、専用の明示監査が終わるまでは`BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED`とする。broker symbolが無い場合にWeb calendarへfallbackしない。

## 10. 実装成果物

- `tools/mt5/ExportGoldV3ExternalContextInventory.mq5`
- `tools/gold_v3/stage277_audit_external_context_inventory.py`
- `tests/gold_v3/test_stage277_external_context_inventory.py`
- `docs/gold_v3/README_EXPORT_GOLD_V3_EXTERNAL_CONTEXT_INVENTORY_MT5_JA.md`

MT5 exporter output:

- `*_symbols.csv`
- `*_timeframe_coverage.csv`
- `*_sessions.csv`
- `*_run_metadata.csv`

Python auditor output:

- `stage277_source_inventory.csv`
- `stage277_source_availability_matrix.csv`
- `stage277_history_coverage_matrix.csv`
- `stage277_causal_availability_contract.csv`
- `stage277_rejected_unavailable_source_ledger.csv`
- `stage277_summary.json`
- `GOLD_V3_STAGE277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY.md`

## 11. Completion gate

Stage277 availability auditを完了扱いにするには、少なくとも次が必要。

1. 同一MT5端末から4つのraw inventory CSVを取得。
2. exact broker/server/baseline identityが一致。
3. closed-only・no fallback・no gap fill safety flagが一致。
4. source inventory、availability matrix、coverage matrix、unavailable ledgerを生成。
5. unavailable / partial sourceを明示。
6. regression test PASS。

raw inventory未取得の時点では正式状態を`PARTIAL_PENDING_MT5_EXPORT_AUDIT_ONLY`とする。

## 12. Safety flags

- `audit_only=ON`
- `live_ready=OFF`
- `final_signal=OFF`
- `MT5_order=OFF`
- `Discord_notify=OFF`
- `partial_close=OFF`
- `performance_grid_run=OFF`
- `candidate_created=OFF`
- `Specialist_Health_Router_V3_changed=OFF`
- `phase2_HV_retest=SHADOW_ONLY`
- `continuous_tick_collection_required=OFF`
- `candidate_tick_collection_required=OFF`

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
