# GOLD V3 Stage262 監査
## live-resolvable exit ledger と新情報readiness

作成日: 2026-06-20  
正式状態: `GOLD_V3_262_PREKNOWN_CALENDAR_AND_NEW_DATA_REQUIRED_BLOCKED_AUDIT_ONLY`

## 結論

Stage262Aのexit state machineは実装・synthetic検証できたが、実データへ正式適用するためのbroker/server別の事前公開session calendarが存在しないためBLOCKED。

Stage262Bでは、現在のCSVにtick arrival timing、bid/ask path、外部市場同期、事前macro calendar、独立broker feedが存在しないことを確認した。

したがって、現在のデータだけで候補探索を再開しない。

## Stage262A

### 固定exit契約

- session closeの5分前をcalendar forced-exit時刻とする。
- planned exitは固定horizon終了とforced-exitの早い方。
- entry時点でcalendar rowがない、未公開、holiday closed、終了間際の場合はcandidateを削除せずNO_ENTRY状態を記録。
- TP/SLはM1 high/lowで判定。
- 同一M1でTP＋SLならSL優先。
- TP/SL未到達はplanned-exit時刻に始まるM1 OPENで強制決済。
- exact M1がなければ補間せずDATA_MISSING_BLOCKED。

exit engine synthetic tests: 5/5 PASS。

### calendar inventory

確認できたcalendar関連ファイルは1件のみ。

`stage260_e2_mt5_session_calendar_observed.csv`

これはM1の連続区間と欠損から後付け生成されたobserved calendarであり、次がない。

- broker/server ID
- symbol group契約
- timezone契約
- holiday closed flag
- short-sessionの事前公表情報
- published_at
- source/version

よってlive calendarには使用できない。

### observed calendar診断

promote禁止の診断としてobserved session endを使い、session close 5分前のforced exitを適用した。

- candidate: 641
- exact entry M1あり: 641
- exact planned-exit M1あり: 641
- 決定的に解決: 641/641

したがって、M1価格データ自体は十分で、主要なBLOCKERはpre-known calendarである。

ただしobserved calendarは将来由来なので、以下の成績は正式評価ではない。

| portfolio | count | cost2 expectancy | PF |
|---|---:|---:|---:|
| P1 E5-E8 parallel | 641 | -0.643 | 0.893 |
| P2 first-come | 543 | -0.686 | 0.888 |
| P4 E5+E7 | 382 | +0.270 | 1.045 |

P4 E5+E7の2026H1部分:

- expectancy -1.155
- PF 0.853

missing tradeをforced exitで含めても2026劣化は解消しなかった。

## Stage262B readiness

| category | status | 現在の状況 |
|---|---|---|
| pre-known broker session calendar | MISSING_EXTERNAL_DATA | observed post-hocのみ |
| M1 exit price data | READY_IF_CALENDAR_SUPPLIED | 診断上641/641 exact timestampあり |
| tick arrival timing / sub-bar path | MISSING_EXTERNAL_DATA | bar tick_volume合計のみ |
| bid/ask / spread path | PARTIAL_NOT_DIRECTIONAL | bar単位spread 1値のみ |
| DXY / US2Y / US10Y / GC | MISSING_EXTERNAL_DATA | 同期ファイルなし |
| pre-known macro calendar | MISSING_EXTERNAL_DATA | schedule/publication metadataなし |
| multi-broker robustness | SOURCE_IDENTITY_UNPROVEN | overlapするM5以上が完全同一、M1 overlapなし |

### source identity

2025年重複期間ではgold#とgoldsharpのM5、M15、H1、H4、D1がOHLC、tick_volume、spreadまで完全一致した。

これはsymbol名が違っても独立broker feedであることを証明しない。M1は期間が重ならないため比較不能。

## formal verdict

`PREKNOWN_CALENDAR_AND_NEW_DATA_REQUIRED_BLOCKED`

- exit engine: READY
- exact M1 prices: READY_IF_CALENDAR_SUPPLIED
- pre-known broker calendar: BLOCKED
- directional new information: MISSING
- live promotion: 禁止

## 次

`GOLD_V3_263_EXTERNAL_DATA_ACQUISITION_AND_CALENDAR_BINDING_NEXT_AUDIT_ONLY`

必要入力:

1. 実際のbroker名、MT5 server名、正式symbol名、server timezone。
2. brokerが事前公表した2025〜2026 holiday/short-session trading hours。
3. MT5 tick export: time_msc、bid、ask、last、flags。
4. DXY、US2Y、US10Y、GCのUTC同期データとavailability timestamp。
5. scheduled macro calendarとpublished_at。
6. 可能なら独立brokerの同期間データ。

これらが揃うまでE9以降のshape探索は停止する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
