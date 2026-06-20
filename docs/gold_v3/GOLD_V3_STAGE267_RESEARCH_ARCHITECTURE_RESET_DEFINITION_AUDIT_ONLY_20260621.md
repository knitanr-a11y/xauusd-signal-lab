# GOLD V3 Stage267 研究アーキテクチャ・リセット定義

作成日: 2026-06-21  
状態: `GOLD_V3_267_RESEARCH_ARCHITECTURE_RESET_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

従来の「一部時間帯・固定8時間exit・共通EMA環境・候補追加＋gate」の設計を停止し、戦略探索前の市場・データ・将来経路基盤を再構築する。

Stage267では売買戦略を採用しない。以下だけを監査する。

1. M1取引休止と真の欠損の分離
2. 全H1/H4確定足を含むdecision universe
3. 取引再開後の正しいactivation時刻
4. 4/8/12/24/48/72/120取引時間のforward path
5. 8時間ラベルによる誤分類診断
6. 既存C1/F12をreference-onlyへ格下げ

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSV各行は確定足、`time`はOPEN時刻。
- M1はtime+1分、H1はtime+1時間、H4はtime+4時間、D1はtime+1日で利用可能。
- `source_close_time <= decision_time`のみ。
- 形成中足のOHLCは使わない。
- sourceは混ぜず、`GOLD_HASH_2025`と`GOLDSHARP_2026`を別区間として保持。
- 取引休止は観測calendarとして識別し、欠損と同一扱いしない。
- official broker calendarとは呼ばない。
- 近傍bar fallback禁止。activationは同source内の最初の実在M1をexact searchsortedで取得。
- strategy、direction、SL、TP、gateを最適化しない。
- live promotion禁止。

## 観測session分類

連続M1間のgapを以下へ分類する。

- `OBSERVED_DAILY_MAINTENANCE`: 50〜90分
- `OBSERVED_WEEKEND_CLOSURE`: 2400分以上
- `OBSERVED_HOLIDAY_OR_EARLY_CLOSE`: 120〜2399分
- `RARE_DATA_GAP`: 2〜49分または91〜119分

これは観測分類であり、official session情報ではない。

## decision universe

### H1

- 全完了H1を対象
- decision_time = H1 time + 1時間
- decision hourの除外なし

### H4

- 全完了H4を対象
- decision_time = H4 time + 4時間
- 1日6本すべてを対象

各decisionについて:

- source区間
- decision時点がtradableかclosure内か
- activation_time = decision_time以降の最初の同source M1
- activation_delay_minutes
- activation_price = activation M1 open
- prior observed closure class

を保存する。

## forward path

activation M1をindex0とし、実在する取引M1行数で将来を測る。

horizon:

- 4取引時間 = 240 M1
- 8取引時間 = 480 M1
- 12取引時間 = 720 M1
- 24取引時間 = 1440 M1
- 48取引時間 = 2880 M1
- 72取引時間 = 4320 M1
- 120取引時間 = 7200 M1

各horizonで:

- endpoint_time / endpoint_close
- long close return
- short close return
- long MFE / MAE
- short MFE / MAE
- maximum favorable/adverse arrival index

を保存する。

maintenance・weekendをまたいでも、取引M1ベースのhorizonは短縮しない。

## 既存候補の格下げ

- C1_CHANNEL6
- F12_H1_FALSE_BREAK_RECLAIM
- その他Stage265〜266候補

を全て`REFERENCE_ONLY_NOT_VALIDATED`とする。

既存8時間損益・gate判定は、新しい戦略の採用根拠に使用しない。

## 8時間ラベル誤分類診断

既存reference tradeについて:

- 8取引時間時点で負け
- 24/48/72/120取引時間時点では方向側プラス

となる比率を測る。

さらに8時間負け群の:

- その後の最大MFE
- 24/48/72/120時間return
- reversal率

を出す。

## Stage267合格条件

戦略成績ではなく基盤整合性を判定する。

- M1 source内time単調増加・重複0
- gap全件分類
- H1/H4 decision activation coverage 99%以上
- decision_time前のM1をactivationに使わない
- source跨ぎactivation 0
- horizon endpoint source跨ぎ0
- forward path algebra parity 100%
- C1/F12 statusがreference-only

## 次段階

Stage268ではStage267 path ledgerを使い、strategy familyを作る前に以下を診断する。

- H1/H4のbar時刻別 forward distribution
- volatility regime別
- trend/range regime別
- horizon別signal-to-noise
- 短期型・遅延型・multi-day型の分離

その後にentry familyとexit familyを別々に設計する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
