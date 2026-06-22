# GOLD V3 最新引き継ぎ — Stage276完了 / Stage277外部causal context可用性監査へ

作成日: 2026-06-22  
対象repo: `knitanr-a11y/xauusd-signal-lab`  
正式状態: `GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`  
次工程: `GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY`

## 0. このファイルの位置づけ

次チャットでは、まずこのファイルを最初から最後まで読むこと。

このファイルは、次を一つに統合した最新版の引き継ぎである。

- Stage275のstatic snapshot探索結果
- Stage276のsequence / state-transition探索結果
- Specialist Health Router V3を変更しない正式判断
- phase2 HV retest候補がSHADOW止まりであること
- Stage273で判明したMT5 tick履歴の可用範囲
- 新しいforward tick-windowスクリプトの正規配置
- ユーザー環境での1時間tick取得成功確認
- 次のStage277で行うことと、行ってはいけないこと

この引き継ぎは、過去の不合格candidateを救済する許可ではない。

## 1. GitHub上の正式な現在地

この引き継ぎ作成前のmain基準commit:

`793a7de621601393e3d7f88f1945de78738cf552`

commit内容:

`Stage276 sequence and state-transition discovery audit (#3)`

Stage276の正式ファイル:

- `docs/gold_v3/GOLD_V3_STAGE276_NO_DISCOVERY_LEAD_AUDIT_ONLY_20260622.md`
- `docs/gold_v3/GOLD_V3_STAGE276_SEQUENCE_AND_STATE_TRANSITION_DISCOVERY_DEFINITION_AUDIT_ONLY_20260622.md`
- `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_STAGE276_NO_LEAD_STAGE277_EXTERNAL_CONTEXT_NEXT_20260622.md`
- `docs/gold_v3/stage276_final_summary_20260622.json`
- `docs/gold_v3/stage276_key_results_20260622.csv`
- `docs/gold_v3/stage276_model_calibration_thresholds_20260622.csv`
- `docs/gold_v3/stage276_reproducibility_manifest_20260622.json`
- `tests/gold_v3/test_stage276_sequence_state_transition.py`
- `tools/gold_v3/stage276_materialize_source_bundle.py`
- `tools/gold_v3/stage276_run_verified.py`
- `tools/gold_v3/stage276_source_bundle_20260622.zip.b64`
- `tools/gold_v3/stage276_source_manifest.json`

MT5 forward tick-windowツール:

- `tools/mt5/ExportGoldV3ForwardTickWindow.mq5`
- `docs/gold_v3/README_EXPORT_GOLD_V3_FORWARD_TICK_WINDOW_MT5_JA.md`

このツール追加のmerge commit:

`f72fd4a03fbe124dffbfcca46230688a31ecb953`

## 2. 絶対禁止事項

以下は次チャットでも維持する。

- GOLD V3はaudit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない・使わない・参照しない・fallbackしない。
- live promotionを行わない。
- final signalを作らない。
- MT5注文を送らない。
- Discord通知を行わない。
- AI APIをlive判断へ接続しない。
- partial closeを行わない。最小lot・全量決済契約を維持する。
- candidate poolを結果を見て手動削除しない。
- 2026年だけ良いcandidateを採用しない。
- LONGまたはSHORTだけを結果を見て後付け除外しない。
- threshold、exit、時間帯、方向を後付け調整して不合格candidateを救済しない。
- 欠損データを補間しない。
- nearest futureを使わない。
- 別sourceへの黙ったfallbackを行わない。
- sourceが取得不能なら、取得不能と明記してBLOCKEDまたはPARTIALにする。

安全フラグ:

- `audit_only=ON`
- `live_ready=OFF`
- `final_signal=OFF`
- `MT5_order=OFF`
- `Discord_notify=OFF`
- `partial_close=OFF`

## 3. CSV・確定足・時刻契約

- CSVの全行は契約上closed。
- CSVの最新行もclosedとして扱う。
- `time`はbroker / MT5 serverのbar OPEN時刻。
- JSTへ変換して判定しない。
- M1 availabilityは`time + 1m`。
- M5 availabilityは`time + 5m`。
- M15 availabilityは`time + 15m`。
- H1 availabilityは`time + 1h`。
- H4 availabilityは`time + 4h`。
- D1 availabilityは`time + 1d`。
- 上位足は`source_close_time <= decision_time`のみ使用する。
- entryはdecision以後の最初の同source M1 open。
- future TP/SL、MFE、MAE、horizon outcomeはentry featureへ入れない。
- same M1でTP/SL両方成立した場合はSL優先。
- gap-through stopは有利に補正しない。
- candidate / health / gate historyは、そのentry時点までにresolvedになった結果だけを使用する。

## 4. 評価・期間・コスト契約

Stage275 / 276の時系列分離を壊さない。

- 2023: train / calibration
- 2024: discovery
- 2025: confirmation
- 2026: final/current diagnostic

2025・2026を見て2024 discovery条件を変更しない。

Stage276の正式performance契約:

- discovery cost: `0.60 USD/oz`
- stress cost: `1.00 USD/oz`
- 2024 discovery lead条件を通ったcellだけを2025へ進める
- Stage276では112 fixed cellsを事前固定

過去artifactにあるcost1 / cost2 / cost3 / cost5等の名称や結果を、別のコスト定義へ黙って読み替えない。
Stage277は最初にデータ可用性を監査する段階であり、取得可能sourceが確定する前にperformance gridを始めない。

2026年は複数回見ており、pristine holdoutではない。

## 5. Stage275の結論

正式状態:

`GOLD_V3_275_NO_DISCOVERY_LEAD_LIVE_REPRODUCIBLE_AUDIT_ONLY`

- M15 decision times: 80,995
- LONG/SHORT direction-expanded rows: 161,990
- causal numeric features: 96
- model families: LR_GLOBAL / HGB_GLOBAL / HGB_ROUTED
- fixed candidate cells: 81
- prefix feature parity: 256/256 PASS
- model score parity: PASS
- batch/stream candidate parity: 81/81 PASS
- 2024 discovery lead: 0

最良2024 cellもcost後不合格だった。
Stage275の81cellをthreshold変更で救済しない。

## 6. Stage276で実施した別ベクトル探索

正式状態:

`GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`

Stage275のstatic snapshotを再調整せず、次を評価した。

- M15 32〜64本のsequence
- finite-state transition
- volatility compression → expansion
- H1/H4 trend transition
- state dwell / transition age
- expanding monthly walk-forward SGD
- Compression → Expansion → First Retest
- Failed Breakout → Reclaim / Rejection
- H1 Transition → First Pullback

規模:

- M15 decision times: 81,781
- LONG/SHORT rows: 163,562
- sequence/state features: 48
- model cells: 32
- event cells: 80
- total fixed cells: 112

Live再現性:

- prefix feature parity: 64/64 PASS
- NaN mismatch: 0
- maximum feature difference: 0.0
- model parity: 4/4 PASS
- chunk64 max difference: 0.0
- one-row max difference: 2.22e-16以下
- candidate accepted index exact: 16/16
- candidate direction exact: 16/16

float32では約1e-7差が出たため正式採用せず、float64へ固定した。

正式結果:

- 2024 discovery lead: 0
- 2025 confirmationへ進んだcell: 0
- 2026 final cell: 0
- 強い候補のACTIVE追加: なし

最上位model cell:

`SGD_A5E4_Q95_M03_C4H_WIDE_225_40_3H`

2024:

- n=98
- win rate=58.16%
- cost0.60 mean=-0.315
- cost0.60 PF=0.831
- cost1.00 PF=0.649
- median gross R=+1.054
- LONG mean=+0.285
- SHORT mean=-0.695

2025はn=17、mean=-3.144、PF0.503。
2026はn=9、mean+14.932、PF26.60だが、2024/2025を通っておらず採用禁止。

Event familiesも不合格:

- Compression → Expansion → First Retest: 安定PF1以上なし
- Failed Breakout最良近傍: 2024 n=394、mean=-0.722、PF0.744
- H1 Transition最良近傍: 2024 n=163、mean=-0.533、PF0.750

不合格理由はlive再現不能ではない。2024でedgeがなく、2025へ一般化しなかったため。

## 7. 現行Specialist Health Router V3の扱い

Stage276後も変更しない。

- 現行Specialist Health Router V3を基準候補として凍結
- Stage276のcandidateを追加しない
- phase2 HV retestをACTIVE化しない
- candidate poolの台帳は保持

補助監査で最も有望だったshadow:

`L_HV_CONTINUATION_RETEST` with closed H1 `ATR14/ATR50 >= 1.14`

これは2024/2025 standaloneでは良く見えたが、統合DD基準を通らず、2026の追加2件は両方負けた。
したがってSHADOW-onlyであり、Stage277の入力candidateとして自動採用しない。

execution robustnessで検討したrollover overlap回避も、ACTIVE変更ではない。
ユーザーは継続的なtick収集や候補ごとのtick取得を不要と判断したため、次工程の必須作業にしない。

## 8. MT5 tick履歴について判明済みのこと

Stage273の正式確認:

- broker / server: XMTrading-MT5 3
- symbol: `GOLD#`
- 2023 tick rows: 0
- 2024 tick rows: 0
- 2025 tick rows: 0
- 2026 tick rows: 10,146,463
- 最初の取得可能tick: `2026-05-13 01:00:02.024`

この端末は2023〜2025の古いtickを提供しない。
別スクリプトで繰り返し取得を試しても、存在しない履歴を生成できない。
古いtick取得を次チャットで再開しない。

## 9. forward tick-windowスクリプト

正規配置:

- repo: `tools/mt5/ExportGoldV3ForwardTickWindow.mq5`
- README: `docs/gold_v3/README_EXPORT_GOLD_V3_FORWARD_TICK_WINDOW_MT5_JA.md`
- MT5側: `MQL5/Scripts/ExportGoldV3ForwardTickWindow.mq5`

EAではなく1回実行型Scriptなので、既存ローソク足取得EAを外さず、EA枠も使用しない。

ユーザー環境での確認結果:

- requested range: `[2026.06.22 07:21:17, 2026.06.22 08:21:17)`
- symbol: `GOLD#`
- status: `SUCCESS`
- rows: 14,943
- chunks: 4
- empty chunks: 0
- copy errors: 0
- gap fill: false
- audit only: true
- time_msc non-increasing / duplicate violation: 0
- spread mean: 約0.3121 USD
- spread min: 0.24 USD
- spread max: 0.34 USD

したがって現在tickを狭い時間窓で取得する機能は確認済み。
ただしユーザー判断により、継続収集、毎候補取得、常駐logger化は行わない。
明示的に必要になった場合だけ使用する。

## 10. 次に行うStage277

次工程:

`GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY`

目的は、強いcandidateをすぐ作ることではない。
まず、GOLD以外のentry-known情報源を同一時刻契約で実際に取得できるかをinventory化する。

優先source候補:

1. XAGUSD
2. USDJPY
3. EURUSD
4. US500 / NAS100等のrisk proxy
5. brokerで取得可能なUSD index proxy
6. 金利・実質金利proxy
7. 経済指標calendar / event proximity

Stage277で最初に確認する項目:

- broker上の正確なsymbol名
- sourceが本当に存在するか
- 2023〜2026の履歴開始・終了
- M1 / M5 / M15 / H1 / H4 / D1の取得可否
- broker server時刻契約
- bar OPEN時刻とclose availability
- missing / duplicate / non-monotonic
- trading session
- spread列の意味と単位
- source間で同一時刻にas-of join可能か
- 形成中barを混ぜずにclosed-onlyで取得可能か

Stage277では、source inventoryと契約固定より前にmodelやcandidate gridを作らない。

sourceが取得不能な場合:

- 推測で代替しない
- Yahoo等へ黙ってfallbackしない
- 似たsymbolへ黙って置換しない
- unavailableとして台帳化する
- 必要ならBLOCKED / PARTIALとする

## 11. Stage277の推奨成果物

まず以下を作る。

- Stage277 definition lock
- source inventory CSV
- source availability matrix
- symbol / broker / timeframe metadata
- history coverage matrix
- causal availability contract
- rejected / unavailable source ledger
- Stage277 summary JSON
- Stage277 audit report
- regression tests
- next-chat handoff

performance評価は、利用可能sourceとas-of契約が固定されてから別stageで行う。

## 12. 次チャットでやってはいけないこと

- Stage276を未実施としてやり直さない。
- Stage276の上位cellを2026成績だけで採用しない。
- Stage276のSHORTを除いてLONGだけ残さない。
- Stage275 / 276のthresholdを緩和しない。
- phase2 HV retestをACTIVEへ昇格しない。
- rollover shadowをACTIVEへ自動変更しない。
- 2023〜2025のGOLD tick取得を再試行し続けない。
- tick収集をStage277の必須条件にしない。
- 外部sourceがある前提でfeatureを作らない。
- web上の別市場時刻をMT5 server時刻へ推測変換しない。
- missing external sourceをGOLD自身の特徴で埋めない。

## 13. 次チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab

GOLD V3の続きです。

まず次の引き継ぎファイルを最初から最後まで読んでください。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_STAGE276_DONE_STAGE277_EXTERNAL_CONTEXT_NEXT_TICK_CONFIRMED_20260622.md

必要に応じて、そこに列挙されたStage276正式ファイルとStage273 tick監査、MT5 forward tick-window READMEだけを追加確認してください。

現在の正式状態は:
GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY

次は:
GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY

重要:
- GOLD V3はaudit-onlyです。
- GOLD V2 / 旧GOLD / DISC8 / Stage41は読まない・使わない・fallbackしないでください。
- Stage276は完了済みです。再実行やthreshold救済をしないでください。
- まず外部sourceの実在、symbol名、期間、時間足、server時刻、closed availabilityをinventory化してください。
- source取得不能時は推測や別source fallbackをせず、BLOCKED/PARTIALとして記録してください。
- current Specialist Health Router V3は変更しません。
- phase2 HV retestはSHADOW-onlyです。
- continuous tick collectionやcandidateごとのtick取得は不要です。
- live、final signal、MT5注文、Discord通知、partial closeはOFFです。
```

## 14. 引き継ぎ内容の3回確認記録

### 確認1 — 契約漏れ確認

確認対象:

- audit-only
- legacy隔離
- CSV closed / bar OPEN時刻
- HTF close availability
- future leakage禁止
- same M1 SL優先
- candidate pool維持
- 2024/2025/2026分離
- live / MT5 / Discord / partial close禁止

結果: `PASS`

### 確認2 — GitHub事実・パス・数値整合

確認対象:

- main基準commit
- Stage276正式状態
- Stage276 112 fixed cells
- parity結果
- Stage277名称
- Stage276正式ファイルのrepo path
- MT5 tick script / README path
- Stage273 tick可用範囲

結果: `PASS`

### 確認3 — 次チャット再開整合

確認対象:

- Stage276を次工程として示していないこと
- 次工程がStage277 availability auditで統一されていること
- performance探索をavailability確定前に始めないこと
- HV retest / rollover / tick収集がACTIVE必須扱いになっていないこと
- 2026-only救済を許可していないこと
- 開始用プロンプトがこの最新ファイルを指していること

結果: `PASS`

## 15. 最終状態

`GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`

次工程:

`GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
