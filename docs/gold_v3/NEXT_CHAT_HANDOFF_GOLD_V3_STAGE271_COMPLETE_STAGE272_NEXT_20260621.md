# GOLD V3 Stage271 handoff

正式状態: `GOLD_V3_271_NO_STABLE_DIRECTION_GATE_R2_RECENT_ASSOCIATION_R3_LONG_INSUFFICIENT_AUDIT_ONLY`

## 結論

- STABLE_ENTRY_KNOWN_CAUSE feature: 0
- R2 LONG: RECENT_REGIME_ASSOCIATION_ONLY
- R2 SHORT: entry-known modelで直近勝敗を安定分離できない
- R3 LONG: latest60 n=6、INSUFFICIENT_SAMPLE
- R3 SHORT: 現在プラスだが下降regime依存、固定gate根拠なし

## Next

Stage272は新しいquality gateを作らない。

1. R2の48h pathをexit/horizon側から診断する。
2. delayed/fadeを区別するexit familyを事前固定する。
3. R3は追加sample監視。
4. M15 false-break near-leadは昇格しない。
5. LONG only / SHORT only禁止。
6. pre-2025 M15/M5/M1なしで新trigger探索禁止。

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
