# Implement

Ordered checklist. Each stage ends with a commit; a failed gate stops the stage and is reported to the user.

## S0 Generator fix
1. Locate the exact frozen draw path and constants (l_max_cap, prefix length, delta_f, Ts, Doppler law, receiver delay
   and Doppler banks). Record them with file:line in `S0_NOTES.md`.
2. Copy the draw path into `experiments/tcom_reference_frame_20261015/gen_fixed.py` with the three opt-in flags.
3. Gates on deinlab (CPU):
   - G-S0a flags off: >= 1000 frames hash-identical (l_i, k_real, g_i, physical gains) to the frozen draw.
   - G-S0b D1/D2 on: same-delay stacking rate within 3 SE of the uncapped natural rate (MC); delay-span law KS p > .01;
     truncation rate at the receiver bank recorded.
   - G-S0c: H from the fixed generator equals the CPP propagation `physical_cpp_untruncated` to 1e-10; prefix >= max delay.
   - Geometric law: nu_max recorded; sign balance and |k| quantiles reported.
4. Commit `S0 generator fix: gates`.

## P1 Confirmation
1. Driver `p1_driver.py` (arms F0, B, LOCAL, C, D, A3; shared frames across rho and SNR); timing probe; quiet timing subset.
2. Codex single-pass review of the driver core diff.
3. Commit before the run; run in tmux `g_tcom_p1`; commit after; analysis per protocol §3.3; draft card.

## P2a Zheng 2025
1. Implement in own regime (N=512); gates G-Z1-Z3; commit.
2. Port (Z-faithful, Z-adapted, Z-turbo) on P1 frames; commit before/after; H5.

## P2b Embedded pilot
1. Analytical infeasibility note for the main scenario.
2. Scenario S (l_max 25) with rate-matched LDPC n = 1530; commit before/after; H6.

## Validation commands (template)
- `ssh deinlab "bash -lc 'cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015 && OMP_NUM_THREADS=1 /home/guoyikun/.conda/envs/AFDM/bin/python -B s0_gates.py'"`
