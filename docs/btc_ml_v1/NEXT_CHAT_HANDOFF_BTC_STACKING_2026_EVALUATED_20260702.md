# NEXT CHAT HANDOFF — BTC積み重ね候補・2026評価・end-to-end再現完了

更新日: 2026-07-02

repo: `knitanr-a11y/xauusd-signal-lab`

## 正式な固定基準

BTC6 CLI修正を取り込んだ最低基準コミット:

```text
dc29fbf5345e26c7890b5ab836a0dd3182e99fe9
```

旧基準コミット:

```text
97fd7ae097bf608d8fbc954d2641e8c9b72dc7ed
```

旧基準はBTC6がCSV等を書き出した後、存在しない `engine._json_default` を参照して終了コード1となるため、end-to-end一括再現には使用しない。

## 次チャットで最初に読む順番

1. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md`
2. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_FIX_AND_VERIFIED_RUN_20260702.md`
3. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md`
4. `docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md`
5. `configs/btc_ml_v1/btc_candidate_master_catalog.json`
6. `configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json`
7. `configs/btc_ml_v1/btc_stacking_reproduction_reference.json`
8. 各候補の個別config・研究文書

古いentry-onlyファイルに残る `post2026_outcomes_evaluated=false` より、上記のマスターカタログ、2026評価config、再現reference、再現実測文書を現在の正本として扱う。

## 必須入力パッケージ

GitHubには大容量の履歴CSVをコミットしていない。取引位置・成績を再計算する場合は、次の2パッケージが必要。

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

## end-to-end実測結果

2026-07-02に、2つの元データパッケージから5候補をCLIで再生成し、入力SHA検証を有効のまま一括スクリプトを完走した。

```json
{
  "reproduction_pass": true,
  "metric_errors": {},
  "fingerprint_errors": {},
  "unresolved_post2026": 0,
  "maximum_simultaneous_positions": 3
}
```

実物レポートSHA256:

```text
45fcde35def8d82e2ff67f11fc7131fbf8f3112eeccb761706bfb3e37f4e1989
```

回帰テスト:

```text
5 passed
```

実測環境:

```text
Python 3.13.5
NumPy 2.3.5
pandas 2.2.3
pytest 9.0.2
```

referenceの予定環境とは一部異なるが、候補指紋・期待指標・未決着件数はすべて一致した。

## 現在の積み重ね採用候補

| 候補 | 時間足 | 状態 | ロット |
|---|---|---|---:|
| `BTC4_RISK_CAP_400` | H4 | 採用・未ライブ | 0.02 |
| `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786` | M5 | 採用・未ライブ | 未設定 |
| `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886` | M15 | 採用・未ライブ | 未設定 |
| `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110` | M15 | 採用・未ライブ | 未設定 |
| `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080` | M15 | 採用・未ライブ | 未設定 |

BTC9Rはユーザー判断により積み重ね採用候補へ昇格済み。

## 2026年以前の全体成績

- 142取引
- 104勝38敗
- 勝率73.24%
- PF2.787
- 合計+5,768.32pips
- 平均+40.62pips
- 最大DD345.18pips
- 正確なユニークエントリー時刻137

## 開封済み2026評価

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

BTC4・BTC6は件数不足。BTC7Rは2026年に弱化したが僅かにプラス。BTC9Rは高いPFを維持した。これを見て既存条件を変更しない。

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

## 実装上の固定契約

- symbol: `BTCUSD#`
- 価格差10ドル = 1pip
- 主スプレッド30ドル
- CSV `time` は足の始値
- 確定足だけを使用
- エントリーは判定後の正確な下位足始値
- 同一判定足でSLとTPが両方成立する場合はSL優先
- BTC4はTP1後、建値判定をTP2より先に行う
- BTC4 EMA Applied PriceはClose
- BTC4 risk capは400pips
- BTC4は2017年開始H4 warmupを使用
- BTC6のentry/exit判定はM15。M5ではない
- 候補間の同時刻取引を重複排除しない
- グローバル1ポジション制限なし
- 最大同時ポジション実測3
- BTC7R/BTC9RのH1 EMA200傾斜はM15へas-of結合後の `shift(4)`。前の確定H1値との比較であり、H1の4本前ではない
- 2026年を開封済みなので、今後この期間をholdoutと呼ばない
- 次の未使用フォワード境界は `2026-07-02 02:15:00 UTC` より後

## 再現性の現在の判定

- 生CSVから5候補をCLI生成: 完了
- BTC6 CLI正常終了: 完了
- 入力CSV SHA・行数・期間検証: 一致
- 候補指紋: 全件一致
- 142件・43件・185件集計: 一致
- 2026年未決着: 0
- 実物 `reproduction_pass=true` レポート: 存在
- GitHub Actionsでの大容量golden-data再計算: 未実施

GitHubだけでは取引再計算できないが、指定2パッケージを使うend-to-end再現性は実測確認済み。

## 次に行うこと

1. BTC5・BTC6・BTC7R・BTC9Rのロットを決める。BTC4の0.02を勝手に横展開しない。
2. 最大3ポジション同時時の総口座リスク上限を決める。
3. ロット決定後、同時保有を含む金額ベースのポートフォリオDDを計算する。
4. 既存候補を2026年結果で再調整せず、`2026-07-02 02:15:00 UTC` より後の新規データをフォワード監視する。
5. 新候補探索を続ける場合も、既存5候補を置換せず別candidate IDで追加する。
6. GOLD横展開ではBTCのpip・スプレッド・SL幅・ロットを流用しない。

ロット設計・新候補探索・ライブ化は、ユーザーの明示指示を受けてから開始する。

## 現在の禁止状態

- 自動注文 OFF
- Discord OFF
- `orders_enabled=false`
- `discord_enabled=false`
- `live_ready=false`
- `final_signal=false`

候補採用・再現成功はライブ稼働許可ではない。
