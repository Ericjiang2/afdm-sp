# Design: headroom ladder + pilot-fraction sweep (physical G1 world)

Inputs: research/theory-headroom.md (T1-T3, predictions P1-P5), research/lit-sp-power.md,
scout report (summarized here). E1 world (G0 truncated generator + genie n_paths=P_actual)
is NOT used: idealized. All work on physical G1 CPP channel, count-blind production receiver.

## Production receiver (paper arm)
B = F0 + TF + CSTATE20 (results/cstate_method_closure_20260928/MANUSCRIPT_SCOPE_DECISION.md).
Entry logic: experiments/tf_cstate_prospective_20260923/run_prospective.py:264-281
(native.receive rounds=2 it=20 soft/joint; trigger = final syndrome != 0; _branch CSTATE20).
F0 = B's first two rounds (free). Count-blind: obs keys {y,pilot,sigma2} only. Design constants
(max_paths 8, OMP nomination 40, Doppler window +-3) and true sigma2 are given; disclosed.

## rho shim (verified)
Frozen guard native_twofft.py:12 requires system.rho == .5. Generate frame with shim
system copy (rho = r), normalize obs by s = sqrt(2(1-r)): data power -> .5 (pd = 1 - .5 exact),
pilot power -> r/(2(1-r)), sigma2 -> sigma2/s^2, channel unchanged. Receiver gets original
rho=.5 system; pilot amplitude comes from obs['pilot'] (grep: no other system.rho use).
Asserts per frame: observed pilot power and sigma2 match formulas.

## Arms
- A0  B (and F0 readout).
- A1  genie delays + multiplicity (repeats kept), Dopplers estimated: new refine_override
      (copy of twofft.time_refine body, l = genie delays incl. repeats; Doppler init = acquired
      ks at same delay by |g| desc, missing slots by coarse scan [-3,3] step .25 with same ev();
      then bounded coordinate search as native). TF-only, no CSTATE.
- A2  genie geometry (true l_i, k_real), gains estimated: interventions.run_true_geometry.
- A3  true H fixed: interventions.run_fixed_channel (gain_mode fixed, TF20R2).
Genie arms have no CSTATE; compare A1-A3 against both F0 and B.

## Experiments
E-ladder: existing random prospective population (deinlab results/tf_cstate_prospective_20260923/
population_observed + population_truth; 3072 frames, 6/6.5/7 dB; rho .5). Rerun A0-A3 for uniform
logging. Caveat: frames previously used for CSTATE confirmatory test -> diagnostic only.
E-rho: fresh population, new DOMAIN + entropy, seeds keyed by frame only (channel/bits/noise shared
across rho and SNR -> paired). rho in {.2,.3,.4,.5}; total SNR 4.5..8.0 step .5; 2000 frames.
Arms A0 (B, F0), A2, A3.

## Metrics / output
Per row (rho, snr, frame, arm): info_errors, coded_errors, decode_ok, syndrome, triggered,
ldpc_iters, logloss_bits (mean log2(1+exp(-(1-2b)L)) on final decoder-input LLRs), seconds,
channel_seed, physical_gains_sha256, n_distinct_delays, truth PDP summary (sorted |g_i|^2),
papr_db. JSONL shards + results.json with _argv/_config/source hashes.
Analysis: FER curves, dB shift at FER 1e-1 / 1e-2 (log-linear crossing), frame-block bootstrap
B=20000; logistic AUC of pass-1 undetectable mass E_miss(rho) vs failure (P3).

## Pre-registered decisions
- rho line alive iff some rho < .5 gives B shift >= 0.3 dB at FER 1e-1 (CI excludes 0).
- P2 check: A3 shift across rho vs 10 log10((1-r1)/(1-r2)) within 0.15 dB.
- Ladder routing per prd.md kill rules; A1 vs A2 splits multiplicity/delay vs Doppler.

## Compute / rules
deinlab CPU only, 1 thread per worker, <= 100 workers (leave >= 16 cores), tmux g_headroom,
code+outputs under /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/,
scratch /data/guoyikun/tmp/. python -B, PYTHONDONTWRITEBYTECODE=1. No edits to frozen/reviewed trees.
Small results (results.json, logs, md, launch .sh) scp back + .gitignore whitelist; big JSONL md5 noted.
