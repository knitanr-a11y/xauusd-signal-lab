# GOLD V3 Stage292 — 安全側ポートフォリオ live final signal

## 構成

Stage292は次を同じ時系列で処理する。

- BASE: Stage69 condition + Stage70 health decision
- Stage280 LONG
- Stage281 LONG
- Stage286 strict SHORT（US500Cash# / US100Cash# M15使用）

優先順位:

- BASE 0
- Stage280 10
- Stage281 20
- Stage286 60

## 安全側受入

- PENDING_FILLまたはOPENは全体で1件まで
- 追加候補の確定済み統合DD <= 30
- 追加候補共有cooldown 12時間
- Stage281は最新の確定済みBASE損失後72時間以内
- Stage286は確定済み統合DD <= 10
- Stage286は最新の確定済み追加候補損失後24時間以上
- BASEの予定保有区間がMT5 server 00:00-01:59へ重なる場合は不採用

状態更新は決済済み結果だけを使用する。未来のexit結果は使わない。

## 2026 cutover

`PLUS_STRICT_SAFE`の2026年履歴を2026-06-19 15:51で引き継ぐ。

- equity: 965.6008808154019
- peak: 985.2064859116765
- current realized DD: 19.605605096274644
- last candidate entry: 2026-06-19 08:30
- last candidate loss exit: 2026-04-29 21:45
- last BASE exit: 2026-06-19 15:51
- last BASE pnl: -19.605605096274644

このためcutover直後はStage286のDD<=10条件を満たさず、Stage286候補が出ても安全側ポートフォリオでは不採用となる。Stage280/281の共通DD上限30は満たす。

年が変わっても状態をリセットしない。

## 実行

1回確認:

`scripts/gold_v3_runtime/bat/run_gold_v3_292_safe_portfolio_live.bat`

継続監視:

`scripts/gold_v3_runtime/bat/run_gold_v3_292_safe_portfolio_live_continuous.bat`

継続監視は60秒ごとにclosed CSVを確認する。停止は`Ctrl+C`。

初回起動は最新時刻をwatermarkとして保存し、過去候補を遡ってfinal signalにしない。2回目以降に新しく確定した候補だけを処理する。

## 出力

`MQL5/Files/FX_OUTPUTS/gold_v3/292_safe_portfolio_live/`

- `gold_v3_292_final_live_signal.csv`
- `gold_v3_292_decision_ledger.csv`
- `gold_v3_292_live_signal_ledger.csv`
- `gold_v3_292_execution_updates.csv`
- `gold_v3_292_applied_updates_latest.csv`
- `gold_v3_292_runtime_state.json`
- `gold_v3_292_summary.json`

## 約定・決済

final signalは実際の約定を勝手に仮定しない。受入後は`PENDING_FILL`となる。

実際に約定した場合:

`record_gold_v3_292_latest_fill.bat`

実際に決済した場合:

`record_gold_v3_292_latest_close.bat`

FILLED後に実約定価格からTP/SL価格を再計算する。CLOSEDの実現損益だけがDD、24時間ロック、次候補の受入へ反映される。

## 有効範囲

- live final signal: ON
- actual fill/close state: ON
- MT5自動注文: OFF
- Discord: OFF
- partial close: OFF

自動注文を追加する前にlot、最大損失、magic number、既存ポジション照合、注文拒否時処理を別契約で固定する。
