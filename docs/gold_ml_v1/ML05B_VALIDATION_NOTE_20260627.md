# GML1-MLR1 ML-05B validation note

ML-05B joins the frozen combined primary proposal registry to the frozen resolved-only ML-03 label registry using `decision_time + direction`.

Validated result:

- proposal rows: 4,263
- joined event rows: 4,263
- missing labels: 0
- duplicate candidate events: 0
- duplicate label keys: 0
- candidate event registry SHA256: `060e2cc0d12ce35cd9962684d73d9adac6d3255d9677848956ba44adf9ede7d9`
- deterministic two-run hash match: true
- unit tests passed: 6

The raw event registry is preserved before one-open, dedup, conflict arbitration or portfolio rules. Label and exit fields are target or audit columns only and are excluded from model inputs. Any later training or rolling history must include an event only when `exit_time <= simulated_asof_time`.

Controls remain audit-only. No model, shadow signal, live signal, MT5 order or Discord output is active.
