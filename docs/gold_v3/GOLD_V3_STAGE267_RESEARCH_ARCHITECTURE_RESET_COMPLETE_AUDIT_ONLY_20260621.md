# GOLD V3 Stage267 研究アーキテクチャ・リセット監査

正式状態: `GOLD_V3_267_RESEARCH_ARCHITECTURE_RESET_COMPLETE_AUDIT_ONLY`

## 結論

従来の候補成績を改善する作業を停止し、取引session・全時間足decision・multi-horizon pathを作り直した。
C1/F12を含むStage265〜266候補はすべて`REFERENCE_ONLY_NOT_VALIDATED`へ格下げした。

## 観測session

- GOLDSHARP_2026 / OBSERVED_DAILY_MAINTENANCE: 87 gaps、observed closed minutes=5311
- GOLDSHARP_2026 / OBSERVED_HOLIDAY_OR_EARLY_CLOSE: 3 gaps、observed closed minutes=645
- GOLDSHARP_2026 / OBSERVED_WEEKEND_CLOSURE: 22 gaps、observed closed minutes=66163
- GOLDSHARP_2026 / RARE_DATA_GAP: 1 gaps、observed closed minutes=1
- GOLD_HASH_2025 / OBSERVED_DAILY_MAINTENANCE: 198 gaps、observed closed minutes=12080
- GOLD_HASH_2025 / OBSERVED_HOLIDAY_OR_EARLY_CLOSE: 7 gaps、observed closed minutes=3447
- GOLD_HASH_2025 / OBSERVED_WEEKEND_CLOSURE: 52 gaps、observed closed minutes=154803
- GOLD_HASH_2025 / RARE_DATA_GAP: 11 gaps、observed closed minutes=36

通常のdaily maintenanceは約62分で、時期により`23:58→01:00`または`22:58→00:00`へ切り替わる。
これをデータ欠損としてpending注文を失効させた旧実装は誤りだった。

## 全H1/H4 decision activation

- H1: source-covered=8479、activated=8479、coverage=100.00%、closure後activation=369、median delay=0.00分
- H4: source-covered=2216、activated=2216、coverage=100.00%、closure後activation=341、median delay=0.00分

全時間帯を対象とし、decision時刻が休止中なら同sourceの最初の実在M1へ繰り越した。
旧StageのH4 `00/04/08 UTC`制限は撤廃し、1日6本すべてをdecision universeへ含めた。

## 8時間ラベル誤分類

- C1_CHANNEL6_REFERENCE_ONLY: legacy 8h-loss 34件のうち、24取引時間後にプラス=47.06%、平均return=2.91
- C1_CHANNEL6_REFERENCE_ONLY: legacy 8h-loss 34件のうち、48取引時間後にプラス=64.71%、平均return=18.41
- C1_CHANNEL6_REFERENCE_ONLY: legacy 8h-loss 34件のうち、72取引時間後にプラス=73.53%、平均return=54.77
- C1_CHANNEL6_REFERENCE_ONLY: legacy 8h-loss 33件のうち、120取引時間後にプラス=63.64%、平均return=47.47
- F12_H1_FALSE_BREAK_RECLAIM_REFERENCE_ONLY: legacy 8h-loss 19件のうち、24取引時間後にプラス=52.63%、平均return=-5.15
- F12_H1_FALSE_BREAK_RECLAIM_REFERENCE_ONLY: legacy 8h-loss 19件のうち、48取引時間後にプラス=78.95%、平均return=11.77
- F12_H1_FALSE_BREAK_RECLAIM_REFERENCE_ONLY: legacy 8h-loss 19件のうち、72取引時間後にプラス=73.68%、平均return=51.99
- F12_H1_FALSE_BREAK_RECLAIM_REFERENCE_ONLY: legacy 8h-loss 19件のうち、120取引時間後にプラス=63.16%、平均return=52.27

旧gateが学習した「負け」には、8時間以内に動かなかっただけで24〜120取引時間後にはプラスになった候補が含まれる。
したがって旧loss gateを中期戦略の負け除外器として使用しない。

## 旧C1候補の消失経路

- hour 00: total=161、旧gap失効=144
- hour 04: total=194、旧gap失効=1
- hour 08: total=193、旧gap失効=1

## 根本設計の誤り

- 旧H4対象時刻`00/04/08 UTC`は、全source-covered H4 decisionの49.86%だけだった。
- 00時候補の大半がmaintenanceを欠損扱いされ、実効対象は`04/08 UTC`の33.30%だった。
- 旧C1の00時候補161件中144件が`ORDER_STREAM_GAP_BEFORE_TRIGGER`で失効した。
- M1履歴はsource gap込みでも約17.51か月しかなく、中期・方向・期間安定性を同時評価するには短い。
- 旧候補群は共通contextと共通exitを使い、独立strategy familyではなかった。

## 無条件forward baseline

全H1/H4確定足について、完了足の方向へその後も進む割合は、4〜120取引時間で概ね50〜52%だった。
したがって、足の色や単純continuationだけには明確なedgeはなく、次はtrend/range・volatility・時間帯・horizonの組合せで分布差を診断する。

## 現在の判断

1. 戦略研究は最初からやり直す。
2. 残すのは時刻・as-of・M1執行・candidate台帳・parity基盤だけ。
3. H1/H4候補を固定8時間labelで勝敗分類しない。
4. 次はpath ledgerを用いて、horizon・時間帯・trend/range・volatility regime別の分布を診断する。
5. entry familyとexit familyを分離してから戦略を作る。

## correctness

- regression tests: 4/4 PASS
- Stage267 acceptance criteria: ALL PASS
- activation coverage: H1/H4とも100%
- source crossing: 0

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
