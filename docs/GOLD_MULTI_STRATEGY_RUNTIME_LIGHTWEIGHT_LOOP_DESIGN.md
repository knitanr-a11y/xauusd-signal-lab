# GOLD_MULTI_STRATEGY_RUNTIME_LIGHTWEIGHT_LOOP_DESIGN

## 目的

GOLD multi-strategy sidecar loop を、実運用で使える速度へ軽量化する。

現状の minute-aligned runner は毎分 02 秒で回るが、内部では BUY/SELL の各戦略 runner が毎回 CSV 全体を読み、全履歴に対して indicator / context / candidate を作る構造になっている。

そのため、戦略数が増えると 1 ループが重くなりやすい。

目標:

```text
GOLD BUY/SELL multi-strategy sidecar 1 loop を数秒以内で完了させる
```

---

## 現状の重いポイント

### 1. 毎回サブプロセスを多段起動している

現在の no-signal 実運用相当 flow:

```text
aligned runner
→ mochipoyo loop dry-run wrapper
→ router
→ BUY dry-run cycle
  → BUY live scan subprocess
  → BUY position monitor subprocess
→ SELL dry-run loop
  → SELL live scan subprocess
  → SELL position monitor subprocess
→ adapter subprocess
→ payload bridge subprocess
→ sender subprocess if payload rows exist
```

no-signal でも subprocess が多い。

### 2. 最新確定 M15 だけ見ればよいのに、毎回フル履歴処理している

BUY:

```text
load H4/H1/M15/M5 CSVs
add indicators on full frames
build all H1 events
build all M15 trigger base
build all trade candidates grid
then filter latest confirmed M15
```

SELL:

```text
load D1/H4/H1/M15 CSVs
add indicators on full frames
attach context on full M15
build backtest-style raw candidates
compute live flags on full M15 context
then filter latest confirmed M15
```

実運用では、最終的に必要なのは最新確定 M15 付近だけ。

### 3. no-signal でも position monitor を必ず呼んでいる

現状は BUY/SELL ともに no-signal でも monitor を呼ぶ。

ただし、monitor は既存未解決 signal の TP/SL/time exit を見る役割があるため、完全に常時 skip は危険。

安全な軽量化方針:

```text
未解決 signal がない場合だけ monitor を skip 可能にする
```

### 4. 毎分 loop なのに、同じ M15 close_time を毎回再評価している

M15確定足は 15 分ごとにしか変わらない。

したがって、毎分 02 秒で起動しても、同じ latest_m15_close_time の間は新規 scan を再実行しなくてもよい。

ただし、monitor は未解決ポジションがあれば毎分必要。

---

## 軽量化の基本方針

### 原則

```text
バックテスト用フル探索と live runtime 判定を分ける
```

バックテスト/研究:

```text
全履歴 scan OK
candidate CSV 大量出力 OK
```

live runtime:

```text
最新確定 M15 周辺だけを見る
必要な過去本数だけ読む/使う
no-signal のときは軽く終わる
未解決ポジションがない monitor は skip 可能にする
同じ M15 close_time は再scanしない
```

---

## 目標 runtime design

### Phase L0: 計測と安全確認

まず各 stage の秒数を summary に出す。

対象:

```text
router total seconds
BUY runner seconds
SELL runner seconds
adapter seconds
payload bridge seconds
sender seconds
aligned loop total seconds
```

目的:

- どこが本当に重いかを数値で見る。
- 軽量化後に改善を比較できるようにする。

### Phase L1: no-signal fast skip

同じ latest_m15_close_time の間は、前回 no-signal なら scan を skip する。

必要 state:

```text
runtime_state.json
  latest_m15_close_time_seen_by_strategy
  previous_scan_reason
  previous_signal_found
  previous_signal_key
```

条件:

```text
latest_m15_close_time が前回と同じ
前回 signal_found=false
未解決 signal がない
```

このとき:

```text
scan skipped
adapter/payload/sender は rows 0 扱い
summary reason=SKIPPED_SAME_CONFIRMED_M15_NO_SIGNAL
```

### Phase L2: monitor conditional skip

monitor は以下の場合のみ走らせる。

```text
strategy ledger に DRY_RUN_SIGNAL_CREATED かつ未解決の可能性がある行がある
または close/position result 確認が必要な open_unresolved がある
```

未解決行がなければ:

```text
monitor skipped
reason=MONITOR_SKIPPED_NO_OPEN_DRY_RUN_SIGNALS
```

### Phase L3: recent-window scan

live scan では必要な過去本数だけに制限する。

候補:

```text
M15: latest 3000 bars 以上
H1: latest 1500 bars 以上
H4: latest 800 bars 以上
D1: latest 500 bars 以上
M5/M1 monitor: latest horizon + buffer
```

注意:

- indicator の warmup が必要なので、短すぎる window は不可。
- H1/H4 divergence / EMA / MACD / ATR / rolling low などの warmup を確保する。
- まずは保守的に大きめ window から始める。

### Phase L4: in-process router

現在は subprocess 多段起動。

将来は以下のように Python 関数化して 1 process 内で回す。

```text
load CSV once
share frames across BUY/SELL
BUY scan function
SELL scan function
adapter function
payload bridge function
sender dry-run function
```

効果:

```text
CSV読み込み重複削減
Python起動コスト削減
ログ保存コスト削減
```

ただし、大きな改修になるため後段。

---

## すぐやるべき第一実装

安全に効果が出やすい順番:

### 1. runtime 秒数計測を追加

まず壊しにくい。

追加先候補:

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run.py
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

summary に以下を追加:

```json
"timing": {
  "router_seconds": 0.0,
  "adapter_seconds": 0.0,
  "payload_bridge_seconds": 0.0,
  "sender_seconds": 0.0,
  "total_seconds": 0.0
}
```

### 2. no-signal monitor skip の設計/実装

BUY/SELL dry-run cycle で、ledger に未解決 signal がない場合は monitor subprocess を skip できるようにする。

flag:

```text
--skip-monitor-when-no-open-signals
```

デフォルトは安全のため false でもよい。

minute-aligned sidecar では true を使う。

### 3. recent-window scan flag を追加

flag:

```text
--scan-recent-m15-bars
--scan-recent-h1-bars
--scan-recent-h4-bars
--scan-recent-d1-bars
```

最初の値:

```text
M15=3000
H1=1500
H4=800
D1=500
```

### 4. same M15 no-signal skip

state を見て同じ M15 かつ前回 no-signal なら scan を skip。

flag:

```text
--skip-same-m15-no-signal
```

注意:

- CSV更新の遅延や週明けギャップに注意。
- signal_found=true の場合は duplicate/ledger確認が必要なので skipしない。

---

## 最初の実装方針

一気に全部やらない。

最初は以下だけにする。

```text
1. loop summary に timing を追加
2. no-signal monitor skip flag を追加
3. case matrix に runtime 秒数を表示/保存
```

その後に recent-window / same-M15 skip へ進む。

理由:

- まず計測できないと軽量化の効果が見えない。
- monitor skip は比較的安全。
- recent-window はシグナルロジックへの影響があり得るため、検証が必要。
- same-M15 skip は状態管理が必要で、誤るとシグナル取りこぼしにつながる。

---

## 成功条件

短期目標:

```text
no-signal 1 loop が数秒以内
case_matrix_validation.bat は checks_failed=0 を維持
order_send_called_count=0
sent_rows=0
```

中期目標:

```text
forever sidecar loop で毎分02秒起動しても、次の分まで余裕を持って終わる
BUY/SELLが増えても loop が肥大化しない
```

---

## 注意事項

以下はやらない。

```text
シグナル条件を簡略化して軽くする
バックテストで決めた条件を勝手に省略する
latest confirmed M15 判定を壊す
MTF join の confirmed-time 制約を崩す
--send を有効化する
production registry write を入れる
```

軽量化は、ロジックの省略ではなく runtime 処理の最適化で行う。

---

## 次の推奨作業

1. `run_gold_multi_strategy_mochipoyo_loop_dry_run.py` に stage timing を追加する。
2. `run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py` に wrapper total seconds を追加する。
3. Case Matrix で Case A/D の timing を summary/details に残す。
4. その後 `--skip-monitor-when-no-open-signals` を BUY/SELL cycle に追加する。

これで、まず「現状何秒か」「どこが重いか」を見えるようにする。
