# Hand-off to Codex: independent derivation of the round-1 coherent excess (effective kappa)

Date 2026-10-09. From the main session (Claude) after its round-1 attempt. Purpose: an independent derivation by
Codex. To keep it independent, read `c1-joint-fp-theory.md` (Claude's attempt) only after drafting your own.

## Question
In round 1 (pilot-only start, 20 damped joint inner updates, your eqs 12-20), the channel error e* exceeds the error of
the same refit fed with independent symbol errors of equal true MSE. Derive that excess, or the receiver's
effective kappa, from the joint updates. Alternatively, show that no scalar closure can capture it and give the
smallest one that can.

## Facts any derivation must reproduce (measured; 8 dB / 6.5 dB / 11 dB cells, 40 frames each)
1. Your eqs 12-20 reproduce the kernel at N = 1024: LLR 3.7e-14, h 2.8e-16 (J run Q0).
2. Excess in the complement of span_C{h}: e_perp / e_ind,perp = 1.18-1.61. It falls with rho at 8 dB
   (L8: 1.57 / 1.40 / 1.19 for rho .2 / .3 / .5; L24: 1.44 / 1.35 / 1.23).
3. One alternating pass (fixed-gain detector at h* + delta, then the soft refit) has slope c_perp .58-.66
   (11 dB L8: .31). Along h: scale .25-.60, phase .40-.92. Yet the realised excess is far below (1 - c)^-2 in every
   direction: e_par / e_ind,par is .9-2.6 (one cell 20.7).
4. The detector absorbs additive input perturbations: in-span .51-.63, white .49-.55 (11 dB L8: .31 both). The reported Stein divergence
   d_hat (mean posterior variance / pseudo-variance) is .29-.44.
5. The 20-step output is not a fixed point. The ridge identity [B(x)^H B(x) + (n0 + V v)(K + u N v)] h = B(x)^H Y misses
   h* by 1.4-7%, and on one frame the recursion still moves ~1e-2 per step at T = 3000-4000.
6. Absorbing both noise and symbol-error interference ((1 - d)^2, dense AMP) under-predicts the excess in 10/10 cells.
   Absorbing only the thermal noise, [(1 - d)^2 n0 + (1 - d) q v]/(n0 + q v) / (1 - beta d)^2, gets the magnitude:
   7/10 within |ln| .2 with d_hat, but biased low, and it does not give the rho trend.
7. Earlier: V2 (6 cells, frames 600-639) has the same pattern; V3 blind cells show the kappa = w law over-predicts e*
   by ~23%; V1 shows the LMMSE link is right at large e*.

## Data and code
- J rows: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1jfp/rows_shard*.jsonl`
  (md5 in out/c1jfp/REMOTE_ROWS_MD5.txt); per-cell tables in out/c1jfp/analysis/jfp.{md,json}.
- V2 rows and tables: out/c1v2/ (same layout). Code: driver_c1jfp.py (contains an independent implementation of your
  eqs 12-20: `codex_recursion`, `CodexOps`), driver_c1v2.py, c1jfp_analyze.py.
- Observations are reproducible bit-exactly from driver_c1 (entropy 129abc...), frames 600-679.

## What would help most
A derivation with explicit assumptions, ending in a prediction testable on the J rows or a small new run. One of
these, for example: e_perp / e_ind,perp per cell from scalars; the T-dependence of e* (T = 10, 20, 40, 80); the rho
trend. Please also save the scripts behind any numerical checks.
