# Stage M7C — Prospective Shadow Reproduction Audit Contract

作成日: 2026-07-20 JST  
repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## 1. 正式Stage

```text
M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY
```

M7Cは、M7Bで凍結した独立proxy条件を、M7B結果確認後に到着する新しい本物アラートへ前向きに照合するStageである。

M7Cは売買Stageではない。  
本物もちぽよ内部式を特定したと主張しない。  
過去全履歴を再生しない。

## 2. M7Bから引き継ぐ正式結果

M7B実データ結果:

```text
status: PASS
built_at_utc: 2026-07-19T18:50:47Z
decision samples: 472
genuine events: 41
no-event controls: 431
M7C blocking reasons: 0
```

M7B PASSの意味は、M7C prospective shadowを開始してよいということだけである。

次は未承認のまま維持する。

```text
historical full scan
cross-timeframe extraction
entry gate
Discord
MT5 order
live-ready
final signal
automatic trading rule approval
```

## 3. 前向き開始点

M7Cの開始点は固定する。

```text
prospective_start_utc = 2026-07-19T18:50:47Z
```

最初の対象decisionは、この時刻より厳密に後の最初のM15境界とする。

開始点以前のM15判断をM7C成績へ混ぜない。  
開始点以前の本物イベントは、proxy状態のbootstrap確認にだけ使う。

遅れて到着したイベントにより開始点以前のイベントID列が変わった場合はfail closedする。

## 4. 凍結するproxy

### PRIMARY LONG

```text
KERNEL-L1
state == IDLE
AND rci9_turn_up == True
AND ema_alignment == BULLISH_STACK
```

### PRIMARY SHORT

```text
KERNEL-S1
state == IDLE
AND rci9_turn_down == True
AND ema_alignment == BEARISH_STACK
```

### LONG EXIT

```text
EXIT-L0
state == ACTIVE_LONG
AND rci9 >= 78.333333333333
```

### SHORT EXIT

```text
EXIT-S0
state == ACTIVE_SHORT
AND rci9 <= -75
```

M7C中に閾値、EMA許容幅、条件、優先順位を変更しない。

## 5. 独立proxy状態機械

M7Cは本物イベントの現在stateを各barのproxy判定に使用しない。  
開始点のbootstrap後は、proxy自身の発火だけでshadow stateを更新する。

```text
IDLE + PRIMARY_LONG  -> ACTIVE_LONG
IDLE + PRIMARY_SHORT -> ACTIVE_SHORT
ACTIVE_LONG + LONG_EXIT -> IDLE
ACTIVE_SHORT + SHORT_EXIT -> IDLE
```

ACTIVE中の反対方向PRIMARYは評価しない。  
REENTRYは凍結していないため生成も採点もしない。

同じIDLE境界でLONGとSHORTが同時成立した場合は、注文や方向選択をせず、`AMBIGUOUS_PRIMARY`として記録してNO SIGNALにする。

## 6. bootstrap

M7C開始時点の状態は、開始点以前の凍結済み本物イベント列から確認する。

```text
BTCUSD:
  latest raw alert ID = 42
  state = ACTIVE_LONG
  offset = UTC+3

XAUUSD:
  latest raw alert ID = 40
  state = ACTIVE_LONG
  offset = UTC+3
```

開始点以前のイベントID列、最終ID、stateが変わった場合は停止する。

UTC+3を永久固定とはみなさない。  
新しいイベントのM4監査でoffset変更が判明した場合は、同一区間に混ぜずDST segment reviewで停止する。

## 7. 因果性

判断時点は新しいM15足の始値時刻。

使用可能:

```text
直前に完全確定したM15足までのindicator
新しいM15足のopen
```

禁止:

```text
新しいM15足のhigh
新しいM15足のlow
新しいM15足のclose
未来足
M6の損益
MFE
MAE
勝敗
PF
```

## 8. 本物イベントとの照合

同一銘柄・同一transitionについて、一対一で照合する。

優先順位:

1. 同じM15境界
2. proxyが1本早い
3. proxyが1本遅い
4. 近傍に別transitionがある
5. miss

分類:

```text
EXACT_MATCH
EARLY_1_BAR
LATE_1_BAR
WRONG_TRANSITION_NEARBY
MISSED
PENDING_CSV_COVERAGE
UNSUPPORTED_REENTRY_NOT_SCORED
```

proxyだけが発火した場合、Webhook到着遅延を考慮して120分のgraceを置く。

```text
grace中: PENDING_SOURCE_ARRIVAL_GRACE
grace後: FINALIZED_EXTRA_PROXY_SIGNAL
```

## 9. 自動監視

既存Cloudflare collectorは別プロセスのまま維持する。  
M7Cはcollectorを置換せず、第二collectorも起動しない。

M7C loopは5分ごとに次を行う。

1. 凍結manifestを読み込む
2. 新しいM15境界までproxy shadowを再構築
3. SQLiteにある新しい本物イベントと照合
4. 出力JSON / CSVを原子的に更新
5. 新規raw eventでM3/M4がstaleの場合だけ、既存M3/M4 derived tableを更新して再試行

M7C自身はraw alertsとMT5 CSVを書き換えない。

## 10. 出力

```text
latest_m7c_prospective_shadow.json
latest_m7c_proxy_decisions.csv
latest_m7c_proxy_signals.csv
latest_m7c_source_event_comparisons.csv
latest_m7c_extra_proxy_signals.csv
latest_m7c_shadow_loop_status.json
m7c_shadow_forever.log
```

既定位置:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs
```

## 11. 件数ベースの確認点

時間経過だけでは判定しない。

```text
5 supported source events:
  operational checkpoint

15 supported source events:
  interim checkpoint

formal manual review:
  supported source events >= 30
  BTCUSD supported events >= 10
  XAUUSD supported events >= 10
  PRIMARY_LONG >= 5
  PRIMARY_SHORT >= 5
  LONG_EXIT + SHORT_EXIT >= 10
```

件数到達時も、プログラムは「再現成功」を自動宣言しない。

出力は次まで。

```text
READY_FOR_MANUAL_REPRODUCTION_REVIEW
```

正式な再現判断は、recall、余計発火、方向違い、銘柄差、時刻差を人間が監査して決める。

## 12. 実行BAT

一回だけ確認:

```text
scripts\mochipoyo_alert_research\run_build_m7c_prospective_shadow_once.bat
```

継続監視:

```text
scripts\mochipoyo_alert_research\run_m7c_prospective_shadow_forever.bat
```

停止:

```text
scripts\mochipoyo_alert_research\stop_m7c_prospective_shadow_forever.bat
```

既存collector:

```text
scripts\mochipoyo_alert_research\run_collect_events_cloudflare_forever.bat
```

collectorとM7C monitorは別ウィンドウで動作する。

## 13. 絶対禁止

- M7C結果を見ながら凍結式を変更しない
- no-eventを増やすためにpre-collector過去を追加しない
- REENTRYを少数例から固定しない
- 本物内部式を復元したと断定しない
- historical scanを開始しない
- M5 / H1 / H4 / D1へ展開しない
- Discordを送らない
- MT5注文を出さない
- entry gateを有効にしない
- live-ready / final signalにしない
