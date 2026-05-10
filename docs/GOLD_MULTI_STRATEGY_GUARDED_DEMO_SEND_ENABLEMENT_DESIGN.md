# GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_ENABLEMENT_DESIGN

## 目的

GOLD BUY/SELL multi-strategy sidecar flow を、dry-run から guarded demo send へ進めるための設計を固定する。

ただし、このドキュメント時点ではまだ `--send` は有効化しない。

現在の到達点:

```text
標準確認: ALL PASS
sidecar dry-run単発: PASS
forever aligned dry-run: PASS
毎分02秒起動: OK
same-M15 no-signal skip: OK
1 loop: 約1.3秒
--send: 未使用
order_send: 0
production registry write: なし
```

---

## 現在の安全境界

現時点で守る境界:

```text
既存 Mochipoyo 本体へ直接混ぜない
既存本番BATを変更しない
既存Mochipoyo ledgersを変更しない
既存trigger-state filesを変更しない
production position_registry.csv を書かない
close intent MT5 execution はまだしない
BTC router/send integration はまだしない
```

GOLD multi-strategy は、独立 sidecar として扱う。

---

## 現在の標準確認コマンド

```bat
scripts\run_gold_multi_strategy_case_matrix_validation.bat
```

この1本で以下を確認する。

```text
1. Case Matrix 4ケース
2. monitor skip A/B invariance
3. same-M15 no-signal skip A/B invariance
```

期待値:

```text
GOLD standard validation ALL PASS
```

---

## 現在の実運用 sidecar dry-run

単発:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run.bat
```

forever aligned:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_forever_aligned.bat
```

現在の dry-run BAT は以下 wrapper を使う。

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run_fast_m15_patch.py
```

有効な軽量化:

```text
--skip-monitor-when-no-open-signals
--skip-same-m15-no-signal
```

---

## guarded demo send の基本方針

### 原則

```text
dry-run と demo-send を明示的に分ける
send は disabled-by-default
send を有効化するには専用BAT/専用フラグが必要
本番 registry write はさらに別段階
```

### 段階

```text
Stage 0: dry-run only 現状
Stage 1: guarded demo send preview design
Stage 2: guarded demo send BAT ただし signal がない限り送信されない
Stage 3: 実CSV signal 発生時に 1件だけ demo send
Stage 4: send成功後の registry write preview
Stage 5: production registry write を disabled-by-default flag で実装
```

このドキュメントの対象は Stage 1〜2。

---

## demo send を有効化するための必須guard

`--send` を渡す前に、最低限以下を必須にする。

```text
1. expected-login が一致する
2. require-demo-account が有効
3. broker-symbol が GOLD#
4. max-orders=1
5. fixed-lot=0.01
6. max-symbol-positions が小さい値
7. max-symbol-lot が小さい値
8. position-policy が明示されている
9. payload rows が 1件以内
10. order payload に strategy_id / signal_key / side / entry / sl / tp がある
11. dry-run sender check が通る
12. standard validation が直近PASS済み
```

既存値の候補:

```text
expected-login=75539039
require-demo-account=true
broker-symbol=GOLD#
fixed-lot=0.01
max-orders=1
deviation=50
position-policy=allow_any_until_max  ※要再検討
max-symbol-positions=5              ※demo initialとしては多い可能性あり
max-symbol-lot=0.05
```

初回demo sendではより保守的にする候補:

```text
position-policy=block_any
max-symbol-positions=1
max-symbol-lot=0.01
max-orders=1
```

---

## 初回demo sendで推奨するposition policy

現状 dry-run validation では `allow_any_until_max` を使っている。

ただし、初回の実MT5 demo sendでは安全側に寄せるなら以下が良い。

```text
position-policy=block_any
max-symbol-positions=1
max-symbol-lot=0.01
```

理由:

```text
初回はシステム全体の送信経路確認が目的
ポジション重複・複数建ての検証は次段階でよい
same_strategy BLOCK や registry-aware policy は別途検証済みだが、production registry write はまだ未実装
```

ただし、既存 validation と同じ設定で進めるなら `allow_any_until_max` のままでもよい。

この判断は demo send BAT 作成前に固定する。

---

## sender と registry の責務分離

現時点の重要事項:

```text
send_mt5_order_from_payload.py はまだ production registry write 用には変更していない
registry preview hook は設計/preview段階
```

したがって、guarded demo send 初期段階では以下に分ける。

### demo send sender

```text
MT5 order_send を呼ぶ可能性がある
--send が明示された時だけ実送信
order ledger へ送信結果を書く
```

### registry preview

```text
sender native registry preview row を作る
production position_registry.csv へは書かない
```

### production registry write

```text
まだ実装しない
send成功後にどう書くかを別段階で設計する
```

---

## demo send BAT の候補

新規BATとして作る。

候補名:

```bat
scripts\run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.bat
```

このBATだけが `--send` を渡す。

通常の dry-run BAT には絶対に `--send` を入れない。

---

## guarded demo send once の想定フロー

```text
standard validation を事前PASS
↓
sidecar dry-run wrapper を実行
↓
router / adapter / payload を作成
↓
payload rows == 0 なら send stage skip
↓
payload rows == 1 なら sender dry-run check
↓
MT5 account guard
  expected-login一致
  require-demo-account通過
  symbol=GOLD#
↓
position guard
  max-orders
  max-symbol-positions
  max-symbol-lot
  position-policy
↓
--send 明示時のみ order_send
↓
order ledger に結果記録
↓
registry preview は作る
↓
production registry write はしない
```

---

## 初回demo sendでは no-signal が正常

現状、最新確認では no-signal。

```text
signals_found_count=0
open_order_intent_count=0
payload_rows_out=0
sender=SKIPPED_NO_PAYLOAD_ROWS
```

そのため、guarded demo send BAT を作っても、signal が出ていない時は送信されない。

この挙動は正常。

初回の確認目的:

```text
--send を渡した状態でも payload rows 0 なら order_send されない
safety guards が壊れていない
standard validation と sidecar dry-run が維持される
```

---

## demo send 用 wrapper をどう作るか

選択肢は2つ。

### Option A: 既存 wrapper に `--send` パススルーフラグを追加

メリット:

```text
処理の重複が少ない
既存dry-run flowと同じコードパス
```

デメリット:

```text
既存dry-run wrapperに send 可能性が入る
安全境界が曖昧になりやすい
```

### Option B: demo-send専用wrapperを別ファイルで作る

メリット:

```text
send可能な入口が明確
通常dry-run wrapperは永遠にno-sendのまま
安全にレビューしやすい
```

デメリット:

```text
一部コード重複が出る
```

推奨:

```text
Option B
```

理由:

```text
ユーザー不安の主因は「どこで何が実行されるか分からないこと」
send可能な入口を専用ファイル/BATに限定した方が安全
```

---

## 推奨する新規ファイル

```text
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.bat
```

ただし、最初の実装では `.bat` は作っても `--send` を即有効化しない案もあり。

より安全な段階:

```text
1. guarded_demo_send_once.py を作る
2. default は dry-run sender
3. --allow-demo-send と --send の両方がある時だけ sender に --send を渡す
4. BAT は最初 `--allow-demo-send` なしで動作確認
5. その後、ユーザー明示承認で `--allow-demo-send --send` 版BATを別名で作る
```

---

## 二重承認フラグ案

demo send wrapper では二重フラグを必須にする。

```text
--allow-demo-send
--send
```

どちらか片方だけでは送信しない。

sender へ `--send` を渡す条件:

```text
args.allow_demo_send is True
args.send is True
payload_rows_out > 0
expected-login guard OK
require-demo-account guard OK
```

summary に以下を出す。

```json
{
  "allow_demo_send": true,
  "send_requested": true,
  "send_flag_passed_to_sender": true,
  "send_suppressed_reason": ""
}
```

送信しない場合:

```json
{
  "allow_demo_send": false,
  "send_requested": true,
  "send_flag_passed_to_sender": false,
  "send_suppressed_reason": "ALLOW_DEMO_SEND_NOT_SET"
}
```

---

## demo send でも維持する軽量化

以下は維持する。

```text
fast M15 parser
--skip-monitor-when-no-open-signals
--skip-same-m15-no-signal
```

理由:

```text
実運用sidecar loopとしては速度が必要
same-M15 skip は no-signal/no-intent/no-unresolved の時だけ発動
signalが出たら skip 条件から外れる
```

ただし、初回demo send once では、signal直後の挙動を見たい場合に `--disable-same-m15-skip` を用意してもよい。

---

## standard validation への追加方針

guarded demo send 実装後、標準確認に以下を追加する。

```text
Guarded demo send safety validation
```

確認項目:

```text
1. allow_demo_send=false / send=false
   → sender dry-run only

2. allow_demo_send=false / send=true
   → send_flag_passed_to_sender=false
   → reason=ALLOW_DEMO_SEND_NOT_SET

3. allow_demo_send=true / send=false
   → send_flag_passed_to_sender=false
   → reason=SEND_NOT_REQUESTED

4. payload rows 0
   → sender skipped / order_send_called_count=0

5. mock payload rowあり + allow_demo_send=false + send=true
   → order_send_called_count=0
```

実MT5 order_send を伴う validation は標準確認には入れない。

---

## 失敗時の停止条件

guarded demo send once は以下で即停止。

```text
standard validation が直近PASSしていない ※最初は手動確認で可
expected-login 不一致
demo account 判定NG
broker-symbol 不一致
payload rows > max-orders
payload rows > 1 初期段階では停止
max-symbol-lot 超過
sender dry-run check NG
order_send 例外
```

---

## ログ/summary に必ず出す項目

```text
cycle_ok
allow_demo_send
send_requested
send_flag_passed_to_sender
send_suppressed_reason
expected_login
require_demo_account
broker_symbol
payload_rows_out
sender_order_send_called_count
sender_sent_rows
sender_error_rows
registry_preview_rows
production_registry_mutated=false
```

---

## emergency stop / rollback

初期段階の停止方法:

```text
forever aligned console を Ctrl+C
send可能BATを実行しない
dry-run BAT はそのまま使用可能
```

ロールバック:

```text
通常dry-run BATには --send が入っていない
send可能入口は専用 guarded demo send BAT のみ
問題があればそのBATを使わない、または削除/無効化する
```

---

## 次に実装するなら

推奨順:

```text
1. guarded demo send once design validator を作る
2. guarded demo send once wrapper を作るが、defaultはdry-run sender
3. allow_demo_send/send 二重フラグの suppression を検証
4. 標準確認に no-send safety validation を追加
5. signal が出るまで forever aligned dry-run で待つ
6. 実CSV signal が出た時のみ、ユーザー明示承認で guarded demo send once を実行
```

---

## まだやらないこと

```text
既存本番BATへの統合
production registry write
close intent MT5 execution
BTC integration
自動で --send を常時loopに入れること
mock signal で実MT5 sendすること
```

---

## 結論

guarded demo send は進められる段階に来ている。

ただし次に書くべきコードは、いきなり `--send` 実行ではなく、send可能入口を明確に分けた guarded wrapper と、二重承認フラグの safety validation。

最初の実装では `order_send_called_count=0` を維持したまま、send suppression が正しく働くことを確認する。
