# Design

Canonical mathematical design: `.mission/20261005_10-48-35-afdm-efficient-information/PLAN.md`. New code in `experiments/afdm_efficient_information/`, results in `results/afdm_efficient_information/`. Reuse frozen mathematical kernels read-only. Separate actual-prior geometry/density, control efficient scores, observed feature inference, and immutable run recording. No production integration. All new stage inputs and tolerances committed before numerical generation; independent saved-output audit at the end.
