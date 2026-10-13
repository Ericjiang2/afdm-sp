# Physical bridge code precheck

Preparatory only: M route and M-03 remain pending BASE-CANCEL-01 and ROUTE-01.

Read-only Luna review located `physical_cluster_weights` and `fit_physical_cluster` in `afdm_sp_joint_unrolled/budgeted_support_diagnostics.py:80`. The weight constructor requires only model-defined slots, delays and continuous Doppler candidates; no true gains are necessary. Receiver-derived candidate geometry can therefore use this mathematical path, provided its provenance is distinct from the existing oracle adapters.

Important boundary: form the full truncated/normalized Dirichlet template with the frozen generator convention, then restrict rows to S0. Do not renormalize after S0 restriction; do not fill missing rows with oracle support. Overlaps sum complex contributions. Fractional Doppler is expanded into integer virtual taps before `gen_h_daft`, whose interface accepts integer delays/Dopplers and gains.

Any legal implementation still needs fixed center selection/query count, no expansion beyond S0, capacity<=40, explicit zero/overlap/rank/soft-fallback behavior and real full-chain validation. Existing truth-ledger routines remain evaluator-only. This note does not demonstrate a deployable method, effect size or novelty.
