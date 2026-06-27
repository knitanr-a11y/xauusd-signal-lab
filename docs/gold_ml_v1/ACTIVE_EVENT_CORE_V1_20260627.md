# GML1 Active Event Core v1

Status: development-only and not connected to runtime output.

The candidate layer is now an event-supply layer for `GML1-META-CORE v1`. Event IDs describe market mechanisms rather than complete strategies. The fixed meta-model receives the event identity and 161 causal market features and decides whether the event is useful in context.

Rules:

- one event at most per decision time;
- no duplicate event rows;
- raw events are preserved before position handling;
- the meta-model contract is unchanged;
- no live or order path is connected.

Active channels:

- `GML1-EVT-001-L`: trend resumption event;
- `GML1-EVT-002-S`: compression release event;
- `GML1-EVT-003-L`: downside exhaustion event;
- `GML1-EVT-003-S`: upside exhaustion event.

Frozen proposal reference:

- 831 events;
- 831 unique decision times;
- LONG 495;
- SHORT 336;
- zero same-time overlap;
- all channels span 2023 through 2026;
- SHA256 `b5e017f2e8b08b8fdad3bcd9ca603155510d23cf2385bbcde2a36bdeff456c0b`.

This is the only active development candidate layer. Earlier candidate definitions are retired from the current tree and must not be used as fallback.
