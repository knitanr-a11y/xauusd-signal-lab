# GOLD V3 Stage261 候補ポートフォリオ・情報不足監査

作成日: 2026-06-20  
正式状態: `GOLD_V3_261_INSUFFICIENT_COMMON_LEDGER_BLOCKED_AUDIT_ONLY`

## 1. 結論

Stage260 E2〜E8を同一形式へ統合し、live-parity済みE5〜E8の固定セルを使ってポートフォリオ監査を行った。

結果は次の二点に分かれた。

1. **評価済みsubset上でも、全候補またはfirst-comeポートフォリオは安定しなかった。**
2. **E5＋E7は補完性を示したが、共通ledgerの固定結果カバレッジが不足し、2026で赤字化したため、新しいholdoutへ進む基準を満たさなかった。**

formal verdictは`INSUFFICIENT_COMMON_LEDGER_BLOCKED`とする。

このBLOCKEDはentryがlive再現できないという意味ではない。E5〜E8のentry parityはPASS済みである。問題は、Stage260の240分固定セルで、将来のセッション切れ・欠損を跨がず最後まで評価できたtradeだけがgridに残っており、**live時点では分からない結果経路の完全性で一部イベントが除外されている**ことである。

## 2. 結果前に固定したStage261契約

定義コミット:

`46f37132bb91c5f4aa9d40848a253be2202d37bd`

- 各Stageの2025H1 discovery cellを変更せず使用。
- 全期間best cell、方向別best、月別bestを使用しない。
- portfolio対象はlive-parity済みE5〜E8。
- E2〜E4は重複・情報系統診断だけ。
- E5＋E7は、price-only continuationとtick-volume impulseという事前に異なる情報系統としてP4へ固定。
- この既知データからlive昇格禁止。

固定セル:

| candidate | horizon | TP | SL |
|---|---:|---:|---:|
| E5 | 240 | 25 | 10 |
| E6 | 240 | 10 | 15 |
| E7 | 240 | 25 | 10 |
| E8 | 60 | 20 | 15 |

## 3. 共通ledgerのカバレッジ

| candidate | live events | fixed-cell outcomes | missing | coverage |
|---|---:|---:|---:|---:|
| E5 | 178 | 150 | 28 | 84.3% |
| E6 | 54 | 52 | 2 | 96.3% |
| E7 | 204 | 167 | 37 | 81.9% |
| E8 | 205 | 201 | 4 | 98.0% |

E5〜E8合計では641候補に対し、固定セル結果があるのは570件、coverageは`88.9%`。

first-come P2では529候補を受け入れる順番になったが、59件の固定損益が欠けた。未評価イベントを0円扱いすることも、後から削除することもlive再現ではないため、P2を完全なlive portfolioとして評価できない。

E5＋E7 P4のcoverage:

| half | full events | evaluated | missing | coverage |
|---|---:|---:|---:|---:|
| 2025H1 | 146 | 127 | 19 | 87.0% |
| 2025H2 | 151 | 126 | 25 | 83.4% |
| 2026H1 | 85 | 64 | 21 | 75.3% |

特に2026H1部分は75.3%しか評価できていない。これは2026の良否を都合よく変えるためではなく、portfolio routeを正式判断できない根本的なledger欠損である。

## 4. 固定候補単体

| candidate | ALL expectancy | ALL PF | 2025H1 exp | 2025H2 exp | 2026H1 exp |
|---|---:|---:|---:|---:|---:|
| E5 | +0.215 | 1.037 | +0.406 | +1.108 | -1.508 |
| E6 | -2.910 | 0.562 | -0.806 | -4.060 | -4.500 |
| E7 | +0.971 | 1.152 | +2.415 | +0.364 | -0.563 |
| E8 | -1.843 | 0.685 | -0.478 | -2.409 | -3.057 |

E5〜E8は全て、2025H2から2026H1部分へexpectancyが低下し、2026は全候補が赤字だった。異なる定義を組み合わせても、同じ市場状態変化に対して共通劣化している。

## 5. 事前固定ポートフォリオ

| portfolio | trades with outcomes | coverage | PnL | expectancy | PF | max DD | positive months |
|---|---:|---:|---:|---:|---:|---:|---:|
| P1_PARALLEL_EQUAL_UNIT | 570 | 88.9% | -327.24 | -0.574 | 0.906 | 582.55 | 9/18 |
| P2_ONE_ACTIVE_FIRST_COME | 470 | 88.8% | -288.57 | -0.614 | 0.900 | 443.52 | 9/18 |
| P3_ONE_ACTIVE_120M | 436 | 89.5% | -215.53 | -0.494 | 0.917 | 401.08 | 8/18 |
| P4_E5_E7_PREDECLARED_COMPLEMENT | 317 | 83.0% | +194.50 | +0.614 | 1.100 | 203.97 | 11/18 |

### P1 全live候補並列

- 全期間: expectancy `-0.574`, PF `0.906`
- 2025H1: `+0.583`
- 2025H2: `-0.904`
- 2026H1: `-2.099`

全候補を足しても2025H2から赤字化し、2026に悪化した。

### P2 one-active first-come

- 全期間: expectancy `-0.614`, PF `0.900`
- 2025H1: `+0.017`
- 2025H2: `-0.587`
- 2026H1: `-1.715`
- accepted outcome unavailable: 59件

重複を抑えても改善しなかった。

### P4 E5＋E7事前固定補完

評価済みsubset上では最も良かった。

- 全期間 PnL: `+194.50`
- expectancy: `+0.614`
- PF: `1.100028`
- positive months: `11/18`
- max DD: `203.97`
- E5＋E7単体DD合計に対するDD減少: 39.3%

期間別:

| half | count | PnL | expectancy | PF |
|---|---:|---:|---:|---:|
| 2025H1 | 127 | +178.14 | +1.403 | 1.254 |
| 2025H2 | 126 | +84.53 | +0.671 | 1.117 |
| 2026H1 | 64 | -68.17 | -1.065 | 0.869 |

2025年はプラスだったが、2026H1部分はexpectancy`-1.065`、PF`0.869`へ悪化した。

またP4の絶対PnL寄与はE7が`83.4%`、E5が`16.6%`で、単一候補80%以下という分散基準を失敗した。

## 6. 候補間の独立性

E5とE7:

- 日次PnL相関: `0.106`
- 月次PnL相関: `0.067`
- entry ±120分のmatched overlap: `32組`
- Jaccard-like overlap: `9.1%`
- overlap時の同方向率: `78.1%`

したがってE5とE7は発生時刻と日次損益の面ではある程度補完的だった。しかし両方とも2026で赤字化しており、低相関だけでは時間安定性を作れなかった。

E7とE8:

- entry ±120分のmatched overlap: `97組`
- 両候補の約47%が120分以内に対応
- Jaccard-like overlap: `31.1%`

同じtick-volume activity windowを継続と反転の別形で再利用している割合が高く、E8は独立edgeではなかった。

## 7. MFEとMAEの共通問題

120分平均:

| candidate | MFE | MAE | MFE-MAE |
|---|---:|---:|---:|
| E2 | 14.94 | 15.58 | -0.64 |
| E3 | 11.75 | 9.54 | +2.21 |
| E4 | 13.28 | 13.44 | -0.16 |
| E5 | 12.47 | 10.50 | +1.97 |
| E6 | 12.88 | 12.24 | +0.64 |
| E7 | 20.97 | 19.67 | +1.30 |
| E8 | 15.54 | 19.99 | -4.45 |

E7は最も大きな値幅を見つけたが、MFE20.97に対してMAE19.67だった。現在のOHLC＋bar-level tick_volumeは「大きく動く場面」を見つけても、到達順序と方向を十分に分けられていない。

## 8. Stage261事前基準

P2とP4のどちらも`PORTFOLIO_ROUTE_WORTH_NEW_HOLDOUT`を満たさなかった。

P4は全期間PFとpositive month数、低相関、DD削減を満たしたが、次を失敗した。

- 全half expectancy非負: FAIL
- 単一候補寄与80%以下: FAIL
- outcome coverage 100%: FAIL

P2は期間安定性、PF、月数、coverageを失敗した。

## 9. formal verdict

`GOLD_V3_261_INSUFFICIENT_COMMON_LEDGER_BLOCKED_AUDIT_ONLY`

診断上は同時に`NEW_INFORMATION_REQUIRED`である。

理由:

1. entryはlive再現できるが、固定ホライズンのexit/outcome ledgerがlive時点で完全再現できていない。
2. 評価可能subsetでも、P1/P2/P3は赤字。
3. 最良のP4も2026赤字、E7依存、coverage不足。
4. E5〜E8が2026に一斉悪化しており、OHLC＋bar tick-volumeの共通情報限界がある。

## 10. 次に必要なこと

E9のような新しいローソク形状探索は停止する。

次は次の二段階を先に行う。

### Stage262A live-resolvable exit ledger

- pre-known MT5 holiday / short-session calendarを用意する。
- entry時点で確定できるsession closeとforced-exit規則を固定する。
- 生成された全candidateを、将来のpath completenessで削除せず評価する。
- entry parityに加え、exit state machine、restart、resolved-only health parityを確認する。

### Stage262B new information readiness

優先順位:

1. tick arrival timingとM1/M5内部のsub-bar tick path
2. bid/askとspreadの時系列
3. DXY、米2年・10年金利、GC futuresの同期方向
4. 事前既知のmacro calendar
5. 複数broker/sourceでの再現性

特にE7はactivity検出までは成功しているため、次に必要なのはvolume閾値の微調整ではなく、activityがbid/askどちらへ進んだか、終盤まで継続したかを判別する情報である。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
