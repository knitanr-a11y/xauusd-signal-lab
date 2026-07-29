BTC fresh-forward stage index
=============================

User-facing folders are sorted by FF number.

FF01_data_availability
  Check whether the required fresh CSV timeframes exist and are usable.

FF02_performance_evaluation
  Evaluate the frozen five candidates after the fresh cutoff.

FF03_btc7r_causality_audit
  Audit BTC7R prefix causality and historical selection provenance.

FF04_bar_time_audit
  Confirm that CSV time is BAR OPEN time and verify causal M5/M15/H1 timing.

Use only the numbered FF folders for normal manual execution.
The older unnumbered folders are retained as internal compatibility paths.

Recovery and incident material will begin with RECOVERY_, INCIDENT_, or FORENSIC_
so that it cannot be buried among normal stage numbers.

Do not run a later FF stage unless ChatGPT explicitly instructs you to do so after reviewing the previous ZIP.
