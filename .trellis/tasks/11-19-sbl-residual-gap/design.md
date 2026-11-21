# Design — SBL residual gap
- Base code: `experiments/unified_cov_prospective_20261119/sbl.py` and `projector.py` (R0, U2 as frozen there).
- K: EM covariance Γ + u·Π_lo − u·Σ_{λ_i>1}(λ_i − 1)e_i e_iᴴ per co-delay block. It is built once at EM start on the initial
  candidate grid, with the same eigen-decomposition as Π_lo, and pruned by principal submatrix. Cross-delay entries stay unchanged.
  Refinement is as in U2.
- M: reuse U2's EM output (bit-identical) and run R0's refinement and decode.
- Gates:
  - G1: R0 and U2 reproduce archived res-20261119-03 rows on 20 seeded keys from 4400–4599.
  - G2:
    - K with the cap disabled is bit-identical to U2;
    - K's EM covariance has no co-delay eigenvalue above 1 in the capped part (synthetic and smoke);
    - M's EM output equals U2's bit for bit, and M's refinement equals R0's refinement on that input.
  - G3: repeatability on smoke keys.
- Per key: per-arm FER, information errors, NMSE, β, iterations, convergence, output co-delay pairs, and K's capped trace and count.
