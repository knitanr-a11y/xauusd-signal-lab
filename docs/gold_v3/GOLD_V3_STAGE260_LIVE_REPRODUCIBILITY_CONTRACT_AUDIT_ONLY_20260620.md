# GOLD V3 Stage260 live再現性契約

作成日: 2026-06-20  
状態: `GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_LOCKED_AUDIT_ONLY`

## 目的

バックテスト上でのみ成立する候補を禁止し、同じ確定足を時系列順に1本ずつ受信するlive-replayでも、同一の候補・方向・decision_time・entry_timeを再現できることを必須条件とする。

本契約はE5以降の全候補へ適用する。

## 絶対契約

- CSV最新行はclosed。
- CSV `time`は足のOPEN時刻。
- 各足は`source_close_time = time + timeframe`以降だけ利用可能。
- 任意の判断時刻`t`で利用できる行は`source_close_time <= t`だけ。
- open中の足、後から確定する高値・安値・ATR・ピボット・セッション終了時刻を使わない。
- rolling値、分位、平均、標準偏差、ATRは現在判断足より後を含めない。
- 未来の方向、未来の最良entry、未来の最良levelを過去へ持ち込まない。
- batch detectorとstreaming detectorは別実装で照合する。
- 2025H1で発見、2025H2で選定、2026は無変更固定。
- audit-only。MT5発注、Discord通知、live hook、order payload、autotrade、final signalはOFF。

## entry時刻契約

確定M15でイベントが完成した場合:

- `decision_time = trigger_m15_open_time + 15分`
- `entry_time = decision_time`
- 評価価格は`entry_time`に始まるM1のOPEN。
- そのM1が存在しない、または時刻ギャップがある場合はentry未成立。

確定M5でイベントが完成した場合も同様に、`decision_time = trigger_m5_open_time + 5分`、entryは同時刻のM1 OPENとする。

## streaming状態機械契約

候補検出は少なくとも次の情報だけを状態として保持する。

- 現在state
- event anchor time / price
- direction
- threshold values fixed at anchor time
- first pullbackの有無と時刻
- expiry time
- invalidation status
- active trade expiry / duplicate suppression state

禁止:

- 過去全体を見直してanchorを選び直す
- 後からより良いdisplacement、level、pivotへ差し替える
- 同一イベントのentryを後から前倒しする
- 結果経路を見てstateを修正する

## batch / live-replay完全一致条件

両実装の出力を次の列で完全一致させる。

- `candidate_key`
- `event_type`
- `direction`
- `anchor_time`
- `decision_time`
- `entry_time`
- `entry_price_source_time`
- `state_version`

価格・ATR・閾値列は許容誤差`1e-9`以内。

次のいずれかがあればlive再現性FAIL:

- batchだけに存在する候補
- streamingだけに存在する候補
- decision_time不一致
- entry_time不一致
- direction不一致
- candidate_key重複
- event完成後に過去時刻へentryが移動
- `source_close_time > decision_time`の入力利用

## prefix invariance

履歴を任意の時刻`t`で切断して検出した結果は、全履歴で検出した`decision_time <= t`の結果と同一でなければならない。

最低チェックポイント:

- 月末
- 四半期末
- 2025-06-30
- 2025-12-31
- 2026年各月末
- 各イベントdecision_time直後のランダム100点

## restart invariance

streaming detectorはstate snapshotを保存・復元できなければならない。

同じデータについて:

1. 最初から連続実行
2. 任意時刻でsnapshot保存
3. 新しいprocessで復元して続行

の候補出力が完全一致すること。

## resolved-only health契約

候補のrolling healthへ使用できる取引結果は、現在entry_timeより前に`exit_time`が確定済みのものだけ。

- `exit_time <= current_entry_time`のみ利用可能
- 未解決tradeを勝敗・PF・期待値へ入れない
- 後続結果で過去entryを取り消さない

## live-parity合格ゲート

候補は次をすべて満たすまでlive-readyではない。

1. batch / streaming候補完全一致
2. prefix invariance PASS
3. restart invariance PASS
4. source_close_time違反0件
5. candidate_key重複0件
6. entry M1欠落時のfail-closed確認
7. 週末・大ギャップ跨ぎ0件
8. resolved-only health parity PASS

成績が良くても、このゲートを1件でも失敗した候補は不採用またはBLOCKEDとする。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
