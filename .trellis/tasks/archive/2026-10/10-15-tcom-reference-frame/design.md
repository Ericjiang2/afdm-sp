# Design

The experimental design, hypotheses and decision rules are frozen in `protocol.md`; this file records the code boundaries.

## Code boundaries

- New code lives in `experiments/tcom_reference_frame_20261015/`. No frozen module is edited
  (`experiments/sp_afdm_native_joint_reviewed_20260921`, `sp_afdm_frozen_reviewed_20260921`, `tf_*`,
  `afdm_sp_joint_unrolled/*`, `headroom_ladder_20261008/*`).
- S0 generator: a copy of the frozen channel-draw path used by `headroom_ladder_20261008/driver.py`
  (`budgeted_support_eval.make_frame` -> `afdm_env` draw -> `supplement_g1.physical_observation`), with opt-in flags
  `--fix-delay-cap`, `--fix-delay-grid`, `--doppler-law {uwa, geometric}`, and `--fix-energy` (amendment A1: no
  Frobenius scale of the Doppler-truncated H; per-frame total path power 1). Flags off must reproduce the frozen draw
  bit for bit (gate G-S0a), which is what validates the copy.
- Receivers are imported unchanged: F0/B/LOCAL via the native schedule and `run_validation._branch`, F1 via the Stage-A
  code, A3 via `interventions.run_fixed_channel`. The P1 driver follows `headroom_ladder_20261008/driver.py`
  (sharded, resumable JSONL rows, config with `_argv`/`_config` and code md5).
- P2a (Zheng) and P2b (EP) receivers are new modules in the same directory, each with its own gates.

## Constraints found during planning (to be resolved in S0, reported before P1)

- Delay support: the stated law allows delays up to 107 samples after the D1 fix, but the frozen front-end bank and the
  CSTATE bank cover delays 0..102. S0 must use an explicit truncated law at the receiver bank (redraw above it) and
  record the truncation rate.
- CPP prefix: `physical_observation` uses `prefix_length = l_max_cap`. The prefix must be at least the maximum drawn
  delay after the fix; S0 verifies this and records the value.
- Geometric Doppler: nu_max is set to the 99% quantile of the UWA law's |k_real| (computed and recorded in S0), so that
  both laws fit the same receiver Doppler window.
