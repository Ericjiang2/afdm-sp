# Design

Canonical design: `.mission/20261004_21-37-05-afdm-higher-order-information/PLAN.md`. Reuse frozen physical and probability kernels read-only. Isolate new implementations in `experiments/afdm_higher_order_information/`. Main coordinates contracts, evidence and synthesis; delegated streams own control moments/information, actual priors, and LLR integration. All numerical stages use the common registered attempt API, with no concurrent performance measurement.
