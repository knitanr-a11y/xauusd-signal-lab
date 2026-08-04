# BTC AI V1 — H4 day-open 勝率改善機構監査

日付: 2026-08-05  
branch: `feature/btc-day-open-win-rate-mechanism-audit`  
事前登録commit: `1e7c8a13125dbe0fe19598aebca4b83a10b6037e`

## 結論

親候補 `FLIP_OR_4ATR_STOP_BE_AFTER_2ATR` は変更していない。勝率改善だけを目的に、利益lock 3案・部分利確4案・controlを結果前に固定して監査した。

3構成が事前登録した勝率・PF・年別・DD・cost・方向・集中gateをすべて通過した。

- `LOCK_0P25ATR_AFTER_2ATR`
- `LOCK_1P00ATR_AFTER_2ATR`
- `PARTIAL_25PCT_AT_2ATR_AND_BE`

最大statusは `POST_HOC_WIN_RATE_ENHANCED_RETROSPECTIVE_LEAD_REQUIRES_FRESH_PROSPECTIVE_CONFIRMATION`。同じ消費済み履歴上のpost-hoc機構監査であり、live authorizationではない。

## Formal period 2024〜2026年7月

| 構成 | Trades | 勝率 | PF | 純損益 USD | Max DD | Net/DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| Control: +2ATR後BE | 1,357 | 17.69% | 1.198 | +78,236.15 | 21,915.64 | 3.570 | 親候補 |
| +2ATR後 +0.25ATR lock | 1,357 | 56.67% | 1.225 | +85,951.14 | 18,996.77 | 4.525 | PASS |
| +2ATR後 +0.50ATR lock | 1,357 | 58.73% | 1.196 | +74,964.99 | 29,627.10 | 2.530 | REJECT |
| +2ATR後 +1.00ATR lock | 1,357 | 58.81% | 1.198 | +75,647.18 | 34,274.88 | 2.207 | PASS |
| +1ATRで25%利確→+2ATRでBE | 1,357 | 57.04% | 1.147 | +50,322.45 | 16,443.38 | 3.060 | REJECT |
| +1ATRで50%利確→+2ATRでBE | 1,357 | 60.28% | 1.074 | +22,408.75 | 18,820.18 | 1.191 | REJECT |
| +2ATRで25%利確＋残りBE | 1,357 | 58.81% | 1.160 | +61,154.80 | 17,174.90 | 3.561 | PASS |
| +2ATRで50%利確＋残りBE | 1,357 | 58.88% | 1.115 | +44,073.46 | 19,236.04 | 2.291 | REJECT |

## 最もバランスが良い勝率改善案

`LOCK_0P25ATR_AFTER_2ATR`

- +2ATR到達M1の次の実在M1から、stopをentry+0.25ATR（SHORTはentry−0.25ATR）へ移動
- state flipまではrunnerを維持
- 初期stopは4ATR
- stop後の同state再entryなし

| 指標 | Control BE | +0.25ATR lock | 差 |
|---|---:|---:|---:|
| 勝率 | 17.69% | **56.67%** | **+38.98pt** |
| PF | 1.198 | **1.225** | +0.027 |
| 純損益 | +78,236.15 | **+85,951.14** | +7,715.00 |
| Max DD | 21,915.64 | **18,996.77** | -2,918.87 |
| Net/DD | 3.570 | **4.525** | +0.955 |

この案は勝率だけを上げたのではなく、PF・純利益・DD・Net/DDもcontrolより改善した。

## 年別 — +0.25ATR lock

| 期間 | Trades | 勝率 | PF | 純損益 USD |
|---|---:|---:|---:|---:|
| 2024 | 544 | 54.04% | 1.049 | +7,535.51 |
| 2025 | 527 | 60.15% | 1.274 | +41,745.46 |
| 2026年1〜7月 | 286 | 55.24% | 1.492 | +36,670.17 |
| 2026年7月 | 42 | 54.76% | 0.753 | -2,400.80 |
| 2023 sanity | 528 | 22.16% | 0.790 | -11,290.90 |

2026年7月は勝率54.76%でもPF 0.753、純損失だった。勝率改善は月単位の利益を保証しない。2023 sanityも不合格。

## Gate耐性 — 通過3構成

| 構成 | 勝率 | 最大winner除外PF | 1.5倍cost PF | 2倍cost PF | LONG PF | SHORT PF |
|---|---:|---:|---:|---:|---:|---:|
| `LOCK_0P25ATR_AFTER_2ATR` | 56.67% | 1.192 | 1.182 | 1.140 | 1.179 | 1.278 |
| `LOCK_1P00ATR_AFTER_2ATR` | 58.81% | 1.165 | 1.156 | 1.114 | 1.138 | 1.268 |
| `PARTIAL_25PCT_AT_2ATR_AND_BE` | 58.81% | 1.135 | 1.118 | 1.078 | 1.125 | 1.201 |

## なぜ勝率が上がったか

Controlでは+2ATR到達後にentry価格へ戻ると、cost後は小さな負けとして数えられていた。+0.25ATR lockでは同じ戻りを小さな確定益へ変えつつ、大きく伸びるtradeはstate flipまで残した。

Formal periodの+0.25ATR lockでは、lock stop 581件のうち554件がnet positiveとなった。

## 実装・因果監査

- control 1,885 tradesは親ledgerとentry・exit・価格・gross・netまで完全一致
- 独立Python referenceと高速scanは8構成、先頭500 H4 events、各122 tradesで完全一致
- synthetic tests 3/3 PASS
- lock/BEはtrigger M1の次の実在M1から有効
- exact M1欠損時fallbackなし
- future/open/as-of使用0
- Stage55・親候補変更なし

## 推奨する次段階

Fresh no-backfillでは、親controlと `LOCK_0P25ATR_AFTER_2ATR` の2本だけを同じentryでmatched-pair Shadowする。`LOCK_1P00ATR` と部分利確案まで同時に持ち込まず、多重比較を増やさない。

最低gate案: 各100 closed trades AND 6 calendar months。新Shadow開始後はentry・4ATR stop・2ATR trigger・0.25ATR lock・state flip・cost・cutoffを変更しない。

## 境界

- Fresh Shadow未作成
- MT5 orders / live trading / live-ready / final signal / Discord OFF
- Stage55変更なし
