# MOCHIPOYO Live Notification Design Review

最終更新: 2026-05-06

このドキュメントは、GOLD/BTC もちぽよ式通知システムを常時稼働・将来自動売買へ進める前の設計レビューである。

## 結論

現時点では、既存の通知系スクリプトをそのまま常時稼働に使わない。

理由は、検証用の full scan 系スクリプトをライブ通知ループへ接続してしまっており、常時稼働用としては重すぎるため。

特に以下は問題として明確に残す。

```text
1. run_mochipoyo_live_notify_loop.py は常時稼働に使わない。
2. 初期版 run_mochipoyo_live_notify_loop_light.py も「更新なしなら軽い」だけで、M15更新時には重い。
3. run_mochipoyo_live_dryrun_strict.py は allowed_slices で後段絞り込みしているが、候補生成段階では全ペアを scan している。
4. tail CSV版も、scannerに渡すCSVは小さくなるが、tail作成時に元CSVを pandas full read しているため、完全な軽量化ではない。
5. ライブ通知専用 minimal scanner を作る前に仕様を固定し、full scan との一致検証を行う。
```

## 既存スクリプトの扱い

### 使ってよい部品

```text
scripts/format_mochipoyo_discord_messages.py
scripts/send_mochipoyo_discord_messages.py
```

用途:

```text
- Discord文面整形
- Discord送信
- payload_key/send ledger による重複送信防止
```

ただし、送信対象CSVには事前に以下を満たす行だけを渡すこと。

```text
- risk_status OK
- 採用済みslice
- 安定payload_key
- 最新確定足ベース
```

### 条件付きで使ってよい部品

```text
scripts/run_mochipoyo_live_dryrun_strict.py
scripts/enrich_mochipoyo_live_payload_risk.py
```

用途:

```text
- dry-run検証
- full scan と minimal scan の照合基準
- 通知候補の監査
```

注意:

```text
- strict版は allowed_slices 後段絞り込みであり、処理量はまだ多い。
- GOLD enrich で live_risk_status != OK が出る場合がある。
- live_risk_status != OK / btc_live_risk_status != OK は通知対象外にする。
```

### そのまま常時稼働に使わない

```text
scripts/run_mochipoyo_live_notify_loop.py
scripts/run_mochipoyo_live_notify_loop_light.py
```

理由:

```text
- 通常版loopは毎回full scanに近い。
- light版は更新検知ゲートはあるが、初期設計ではM15/H1更新時に重いscanが走る。
- tail CSV版もまだ元CSV full read が残っている。
```

## MQL5 CSV Export EA 仕様メモ

ユーザー提示の `ExportOhlcToCsv.mq5` v1.32 を前提とする。

重要設定:

```text
#property version "1.32"
InpIncludeCurrentBar = false
InpAlignExportToMinute = true
InpExportSecond = 0
InpTimerSeconds = 1
InpAppendMode = true
InpAppendLookbackBars = 20
InpSkipUnchangedFiles = true
```

出力列:

```text
time, open, high, low, close, tick_volume, spread, real_volume
```

確定足仕様:

```text
CopyConfirmedRates() は InpIncludeCurrentBar=false の場合、CopyRates start_pos=1 で取得する。
したがってCSV末尾の最新行は、EA設定がこのままであれば形成中足ではなく確定済み足として扱う。
Python側は基本的に latest row / bar-offset 0 を使ってよい。
```

ただし、ライブ読み込み側は以下を守る。

```text
- MT5がCSV追記中の瞬間にPythonが読む可能性がある。
- 末尾の不完全行・空行・parse不能行は捨てる。
- 読めない場合は短時間リトライする。
- time列が昇順でない場合はその回をskipする。
```

EAのAppend仕様:

```text
初回:
  full export

2回目以降:
  remembered last bar 以降の新規確定足だけ append

InpSkipUnchangedFiles=true:
  最新確定足が前回と同じなら書き換え/追記しない
```

このため、Python側の軽量ループはファイル更新時刻だけでなく、CSV末尾のtime列を確認するのが正しい。

## ライブ通知 minimal scanner の必須仕様

新規実装する場合、既存full scannerをそのまま呼ばない。

### 1. pair単位トリガー

symbol単位ではなく pair単位で更新検知する。

```text
GOLD_H4_M5_SCALP      -> M5更新で判定
GOLD_H4_M15_DAYTRADE  -> M15更新で判定
GOLD_D1_H1_DAYTRADE   -> H1更新で判定
BTC_H4_M15_DAYTRADE   -> M15更新で判定
```

理由:

```text
GOLD_H4_M5_SCALP はM5ベースなので、M15更新だけで見ると最大10分程度遅れる可能性がある。
```

### 2. 採用済みsliceから必要pairだけ決める

NG:

```text
全ペアscan
↓
allowed_slicesで後段絞り込み
```

OK:

```text
allowed_slices
↓
必要pairを決定
↓
必要pairだけscan
```

現在の採用slice:

```text
GOLD_H4_M5_SCALP|B|SELL
GOLD_H4_M15_DAYTRADE|B|SELL
GOLD_D1_H1_DAYTRADE|B|BUY
GOLD_D1_H1_DAYTRADE|A|BUY
GOLD_H4_M5_SCALP|A|SELL
GOLD_H4_M15_DAYTRADE|B|BUY

BTC_H4_M15_DAYTRADE|A|BUY
BTC_H4_M15_DAYTRADE|A|SELL
```

### 3. confirmed-time rule は必須

MTF結合は必ず以下を満たす。

```text
context_close_time <= base_close_time
```

また、pivot系は必ず以下を満たす。

```text
pivot_confirmed_time <= signal_close_time
entry_time >= signal_close_time
```

### 4. 最新足はEA仕様上 latest row を使ってよいが、リーダーは堅牢にする

EAが `InpIncludeCurrentBar=false` で確定足のみ出すため、Python通知側は原則 latest row を使う。

ただしCSV競合対策として、以下は必須。

```text
- 末尾不完全行を捨てる
- parse不能行を捨てる
- time昇順チェック
- 短時間リトライ
```

### 5. tail本数はwarmup込みで設計する

軽量化しても、インジケーター・pivot・cooldownが変わるほど短いtailは不可。

危険な要素:

```text
EMA200
RCI
ZigZag/pivot
hidden divergence
cooldown
過去通知との重複判定
```

tailは「判定対象数本」ではなく「warmup + 判定対象」で読む。

### 6. risk OK 以外は通知しない

通知対象条件:

```text
GOLD: live_risk_status == OK
BTC : btc_live_risk_status == OK
```

NG行は通知しない。

理由:

```text
SL/TPが計算できない通知は実運用・自動売買へ進める上で危険。
```

### 7. payload_key は安定キーにする

NG候補:

```text
source_filter_name を payload_key に含める
```

理由:

```text
同じシグナルでも、どの固定フィルターに先に一致したかでkeyが変わる可能性がある。
```

推奨payload_key:

```text
symbol
pair_name
candidate_rank
direction
entry_time
entry_price
```

必要なら `base_close_time` / `signal_close_time` も含める。

### 8. cooldown は ledger/state で管理する

ライブでは最新数本だけを見るため、DataFrame上の過去候補だけではcooldown判定が不足する。

必要なstate:

```text
last_notified_time_by_symbol_pair_direction
last_signal_key
send ledger
```

### 9. BTCスプレッドはライブでも必須

BTC通知には必ず以下を持たせる。

```text
mode/current spread price
spread_to_sl_ratio
effective_rr_after_spread
net_sl_after_spread_price
net_tp_after_spread_price
```

自動売買では、通知より厳しく以下を拒否条件にする。

```text
spread_to_sl_ratio が上限超え
effective_rr_after_spread が下限未満
spreadが取得不能
```

## minimal scanner 実装前の検証条件

実装前に仕様として固定し、実装後は必ず以下を通す。

### 検証1: full scan一致確認

同じCSV時点で以下を比較する。

```text
full strict scan
minimal scan
```

比較項目:

```text
entry_time
pair_name
candidate_rank
direction
entry_price
reason_text
SL
TP
risk_status
payload_key
```

最新付近の通知候補が一致しない場合、minimal scannerは使わない。

### 検証2: tail本数感度

tail本数を変えて結果が変わらないか確認する。

```text
M1  : 3000 / 6000 / 12000
M5  : 1000 / 3000 / 6000
M15 : 1000 / 2000 / 3000 / 5000
H1  : 500 / 1000 / 1500
H4  : 300 / 800 / 1500
D1  : 200 / 400 / 800
```

### 検証3: pair別更新トリガー

```text
GOLD_H4_M5_SCALP      -> M5更新で判定される
GOLD_H4_M15_DAYTRADE  -> M15更新で判定される
GOLD_D1_H1_DAYTRADE   -> H1更新で判定される
BTC_H4_M15_DAYTRADE   -> M15更新で判定される
```

### 検証4: 重複通知

同じCSVで連続実行して以下を満たす。

```text
1回目: 新規候補は通知対象
2回目: sent 0 / duplicate skip
```

同一シグナルが複数フィルターに一致しても1回しか通知しない。

## 次にコードを書く前に決めること

```text
1. GOLD_H4_M5 をM5ごとに通知するか -> 推奨: YES
2. GOLD_H4_M15 をM15ごとに通知するか -> 推奨: YES
3. GOLD_D1_H1 をH1ごとに通知するか -> 推奨: YES
4. BTC_H4_M15 をM15ごとに通知するか -> 推奨: YES
5. latest row を使うか -> EA設定上は YES。ただし不完全行対策必須。
6. payload_keyから source_filter_name を外すか -> 推奨: YES
7. risk_status NGを完全除外するか -> YES
8. full scan一致テストを作るか -> YES
```

## 作業停止メモ

現時点では、まだGitHubへ新しい minimal scanner 実装を追加しない。

次に進む場合は、上記仕様に合意してから、まず検証用の比較スクリプトを作る。

実装順は以下。

```text
1. minimal scanner仕様固定
2. full strict scan vs minimal scan 比較スクリプト
3. minimal scanner本体
4. pair別軽量loopへ差し替え
5. Discord送信再確認
6. デモ口座自動売買設計
```
