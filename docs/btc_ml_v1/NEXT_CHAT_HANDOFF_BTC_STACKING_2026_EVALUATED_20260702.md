# NEXT CHAT HANDOFF — BTC積み重ね候補・2026評価・再現性監査完了

作成日: 2026-07-02

repo: `knitanr-a11y/xauusd-signal-lab`

## 次チャットで最初に読む順番

1. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md`
2. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md`
3. `docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md`
4. `configs/btc_ml_v1/btc_candidate_master_catalog.json`
5. `configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json`
6. `configs/btc_ml_v1/btc_stacking_reproduction_reference.json`
7. 各候補の個別config・研究文書

古いentry-onlyファイルに残る `post2026_outcomes_evaluated=false` より、上記のマスターカタログ、2026評価config、再現referenceを現在の正本として扱う。

## 新チャットへ必ず添付する入力

GitHubには大容量の履歴CSVをコミットしていない。候補条件コードだけでは取引位置・成績を再計算できない。

必須パッケージ:

```text
BTCUSD_HISTORY_CHAT_PACKAGE.zip
SHA256: 9b0b74e9937eca05e895047f5737c6794332af7ec25f2a30b64d9440c9e0dd22

BTCUSD_H4_WARMUP_PACKAGE.zip
SHA256: d150eaee0c126e2eb4c4aecb667ff0ad181a9a0a6e060cc5c1613b60e0a8019a
```

H4 warmupは2017年開始。BTC4では通常履歴パッケージ内の2024年開始H4を代用しない。

## 一括再現

パッケージ展開後、リポジトリルートから:

```bat
RUN_BTC_STACKING_REPRODUCTION.bat ^
  "C:\BTC_REPRO\history" ^
  "C:\BTC_REPRO\h4_warmup\btcusdsharp_h4.csv" ^
  "outputs\btc_ml_v1\btc_stacking_reproduction_20260702"
```

正本スクリプト:

```text
scripts/btc_ml_v1/research/reproduce_btc_stacking_portfolio.py
```

入力の行数・期間・SHA256、候補エントリー指紋、2026年決着、全体指標を照合し、すべて一致した場合のみ:

```text
btc_stacking_reproduction_report.json
reproduction_pass = true
```

個別コマンド・入力SHA・成功条件は再現runbookを参照する。

## 現在の積み重ね採用候補

| 候補 | 時間足 | 状態 | ロット |
|---|---|---|---:|
| `BTC4_RISK_CAP_400` | H4 | 採用・未ライブ | 0.02 |
| `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786` | M5 | 採用・未ライブ | 未設定 |
| `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886` | M15 | 採用・未ライブ | 未設定 |
| `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110` | M15 | 採用・未ライブ | 未設定 |
| `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080` | M15 | 採用・未ライブ | 未設定 |

BTC9Rはユーザー判断により積み重ね採用候補へ昇格した。

## 2026年以前の全体成績

- 142取引
- 104勝38敗
- 勝率73.24%
- PF2.787
- 合計+5,768.32pips
- 平均+40.62pips
- 最大DD345.18pips
- 正確なユニークエントリー時刻137

## 開封した2026年テスト

データ終端: `2026-07-02 02:15:00 UTC`

候補条件は2026年結果を開く前に凍結済み。2026年結果は条件選定・再最適化に使用していない。

- 43取引
- 26勝17敗
- 勝率60.47%
- PF2.023
- 合計+1,199.42pips
- 平均+27.89pips
- 最大DD247.84pips
- 正確なユニークエントリー時刻40
- 43件すべてデータ終端までに決着

### 2026年候補別

| 候補 | 件数 | 勝ち | 負け | 勝率 | PF | 合計pips |
|---|---:|---:|---:|---:|---:|---:|
| BTC4 | 2 | 2 | 0 | 100.00% | ∞ | +732.26 |
| BTC5 | 5 | 3 | 2 | 60.00% | 1.446 | +60.98 |
| BTC6 | 1 | 0 | 1 | 0.00% | 0.000 | -35.61 |
| BTC7R | 22 | 11 | 11 | 50.00% | 1.045 | +35.51 |
| BTC9R | 13 | 10 | 3 | 76.92% | 2.963 | +406.29 |

BTC4・BTC6は件数不足。BTC7Rは2026年に大きく弱化したが僅かにプラス。BTC9Rは2026年でも高いPFを維持した。これを見て既存条件を変更してはいけない。

### 2026年月別

- 2026-01: +635.55pips
- 2026-02: +54.43pips
- 2026-03: -28.98pips
- 2026-04: +346.63pips
- 2026-05: +68.40pips
- 2026-06: +123.40pips

6か月中5か月プラス。

## 全評価期間

- 185取引
- 130勝55敗
- 勝率70.27%
- PF2.583
- 合計+6,967.74pips
- 平均+37.66pips
- 最大DD345.18pips
- 正確なユニークエントリー時刻177
- 完全一致による追加取引8件
- 最大同時保有3ポジション

完全一致時刻も別候補として集計している。グローバル1ポジション制限は導入していない。

## 実装上の重要事項

- BTC pip契約: 価格差10ドル=1pip。
- 主スプレッド: 30ドル。
- CSV `time` は足の始値。
- 確定足だけを使う。
- エントリーは判定後の正確な下位足始値。
- 同一判定足でSLとTPが両方成立する場合はSL優先。
- BTC4はTP1後のみ建値をTP2より先に判定する。
- BTC6の2026結果判定はM15足で行う。M5インデックスとして扱わない。
- BTC7RとBTC9RのH1 EMA200傾斜は、M15へas-of結合後の `shift(4)` であり、実装上は前の確定H1値との比較。4本前のH1ではない。
- 2026年を開封済みなので、今後この期間を再びholdoutと呼ばない。
- 次の未使用フォワード境界は `2026-07-02 02:15:00 UTC` より後。

## 再現性の現在の判定

- 候補条件コード: mainに存在
- 個別config: mainに存在
- 個別契約テスト: mainに存在
- 一括再現スクリプト: mainに存在
- 入力SHA・候補指紋・期待成績: mainに存在
- 生CSV: GitHub外。新チャットへの添付が必須
- GitHub Actionsの大容量golden-data再計算: 未実施

したがって、**新チャットへ2つの入力パッケージを添付すれば再現可能**。GitHubだけでは取引再計算は不可能。

新チャットでは、説明だけで「再現できた」と判断せず、一括スクリプトを実行し `reproduction_pass=true` を確認する。

## 金額成績をまだ出していない理由

BTC4以外のロットが未設定。現在の全体成績は1候補シグナルを1取引としてpips集計したもの。ロットを勝手に0.02へ統一しない。

## 次に行うこと

1. 新チャット開始直後に2つの入力パッケージを添付し、一括再現を実行する。
2. `reproduction_pass=true` を確認するまで、新しい候補探索やロット設定へ進まない。
3. BTC5・BTC6・BTC7R・BTC9Rのロットと、最大3ポジション同時時の総口座リスクを決める。
4. ロット決定後、同時保有を含む金額ベースのポートフォリオDDを計算する。
5. 既存候補を2026年結果で再調整せず、2026-07-02以降の新規データをフォワード監視する。
6. 新候補探索を続ける場合も、既存5候補を置換せず別candidate IDで追加する。
7. GOLD横展開ではBTCのpip・スプレッド・SL幅・ロットを流用しない。

## 現在の禁止状態

- 自動注文 OFF
- Discord OFF
- `live_ready=false`
- `final_signal=false`

候補採用・再現成功はライブ稼働許可ではない。
