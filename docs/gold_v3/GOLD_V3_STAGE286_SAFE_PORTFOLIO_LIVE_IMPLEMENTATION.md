# GOLD V3 Stage286 安全側ポートフォリオ live SHADOW実装

正式状態:

`GOLD_V3_286_SAFE_PORTFOLIO_LIVE_SHADOW_AUDIT_ONLY`

## 実装範囲

ローカルPC上で、既存の機械学習・候補生成コードが出した候補を受け取り、次を実行する。

1. closed足候補だけを受理
2. BASE / Stage280 / Stage281 / 厳格SHORTをentry時系列で処理
3. 同時刻は BASE=0、Stage280=10、Stage281=20、厳格SHORT=60 の順
4. 1ポジション制
5. 追加候補は確定済み統合DD30以下、共有cooldown 12時間
6. 厳格SHORTはさらに確定済み統合DD10以下、確定済み追加候補損失から24時間
7. BASEは予定最大保有区間がMT5サーバー00:00～01:59に重なる場合、統合対象から外して記録のみ
8. SQLiteへ状態と判断を永続保存

## 因果契約

候補判定時に履歴へ入れるのは、必ず次を満たす結果だけとする。

`exit_dt <= current entry_dt`

resolutionがデータベースへ登録済みでも、exit時刻が現在候補より後なら、DD・equity・損失lockoutへ入れない。未確定足、将来のTP/SL、将来horizon、将来の高値・安値・終値は候補入力へ渡さない。

候補はentry時刻の昇順で処理する。後から古いentry候補が届いた場合は停止し、すでに進んだ状態へ過去候補を混ぜない。同時刻の候補は全sourceを1ファイルへまとめて渡す。

## 厳格SHORT

固定条件:

- 元候補: `SHORT_EXHAUST_Q90_EMA20_E225_CD120`
- 元のQ90条件を維持
- GOLD M15 ret8/ATR score <= `2.992581130893`
- mean(SP500 M15 ret4/ATR, NAS100 M15 ret4/ATR) <= `0.410970621210`

閾値をlive中に再探索・変更しない。

## 機械学習コードとの接続

`producer_bridge.py` は既存ローカルモジュールを `package.module:function` 形式で読み込める。producerはentry時点で利用可能な候補情報だけを返す。

禁止フィールド:

- pnl / pnl_new / gross_pnl
- exit_dt / exit_reason
- label / target / future_result

候補の必須項目:

```json
{
  "candidate_id": "stable-id",
  "source": "BASE",
  "direction": "LONG",
  "signal_dt": "2026-06-23 10:00:00",
  "entry_dt": "2026-06-23 10:05:00",
  "max_holding_minutes": 120,
  "closed_bar": true,
  "features_asof": "2026-06-23 10:00:00",
  "closed_bar_time": "2026-06-23 10:00:00",
  "time_basis": "MT5_SERVER_NAIVE"
}
```

## 実行

```bash
python -m pip install -e .

python scripts/run_live_safe_portfolio.py \
  --config config/gold_v3_live_safe_portfolio.audit_only.json \
  --db runtime/gold_v3_safe_shadow.sqlite init
```

候補ファイルを処理:

```bash
python scripts/run_live_safe_portfolio.py \
  --config config/gold_v3_live_safe_portfolio.audit_only.json \
  --db runtime/gold_v3_safe_shadow.sqlite \
  ingest --candidates runtime/inbox/candidates.jsonl
```

観測済み決済を登録:

```bash
python scripts/run_live_safe_portfolio.py \
  --config config/gold_v3_live_safe_portfolio.audit_only.json \
  --db runtime/gold_v3_safe_shadow.sqlite \
  resolve --resolutions runtime/inbox/resolutions.jsonl
```

inbox監視:

```bash
python scripts/run_live_safe_portfolio.py \
  --config config/gold_v3_live_safe_portfolio.audit_only.json \
  --db runtime/gold_v3_safe_shadow.sqlite \
  watch --inbox runtime/inbox --archive runtime/archive
```

## 2026 cutover

選択済み安全側台帳から2026年状態を一度だけ復元できる。

```bash
python scripts/run_live_safe_portfolio.py \
  --config config/gold_v3_live_safe_portfolio.audit_only.json \
  --db runtime/gold_v3_safe_shadow.sqlite \
  bootstrap \
  --ledger docs/gold_v3/gold_v3_stage286_short_selected_portfolio_trades.csv \
  --portfolio PLUS_STRICT_SAFE \
  --start-dt "2026-01-01 00:00:00" \
  --through-dt "2026-06-19 23:59:59"
```

確認済み台帳では102件、累積`+965.6008808154`を復元する。cutover後は年が変わっても状態をリセットしない。

## 必要な既存producer

安全側runtimeへ次を接続する。

- SPECIALIST_HEALTH_ROUTER_V3 BASE候補生成器
- Stage280 LONG候補生成器
- Stage281候補生成器
- SHORT_EXHAUST_Q90元候補生成器

完成済み取引CSVをlive候補の代わりに使わない。

## フラグ

- audit_only = ON
- live_ready = OFF
- final_signal = OFF
- MT5_order = OFF
- Discord_notify = OFF
- partial_close = OFF
