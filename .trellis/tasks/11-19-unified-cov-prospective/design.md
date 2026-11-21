# Design — unified covariance prospective test

Canonical definitions are in [research/protocol-DRAFT.md](research/protocol-DRAFT.md) (§1 construction, §3 arms, §4 verdicts). This
file fixes the code boundaries and the gates. Sol may revise it in Phase 1 and must record each reason.

## Code locations (read-only sources)
- SBL leg: reuse `experiments/sbl_spectral_split_20261119/` (`spectral_receiver.py`, `main_receiver.py`, `run_main.py`), which already
  builds S-lo / S-hi / S-isolo on top of `experiments/tf_e3c_shrink_20261018/e3c_driver.py`. The only new receiver logic is U2's
  refinement covariance.
- CSTATE leg: Stage 3 harness `experiments/cstate_codelay_sbl_stage3_20261118/` (`codelay.py` binds the closed-form co-delay block into
  the E-1 geometry source `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py`). A2 is the same schedule with
  `gamma_mode='diag'` (E-1 `ARM_SPECS['A2']`).
- Γ_U is not entrywise, so the CODELAY `_gamma_cross` binding cannot express it. Expected route: score each trial support exactly with
  Γ_U on that support (for example via the direct strategy or an exact rescoring of trials whose co-delay block has an eigenvalue
  below τ), and use a frozen-per-pass projector inside `_system` for local passes and the final refit. Sol chooses the route; its
  exactness is what G2 checks.

## New code
`experiments/unified_cov_prospective_20261119/` with its own `PROTOCOL.md` copy, receivers, launcher, aggregate/verdict code with
synthetic tests, and `out/`.

## Gates
- **G1 reference parity (old keys only).**
  - SBL: R0, R1, S-lo, S-hi and S-isolo reproduce archived E-3c / spectral-split rows on 20 seeded keys from frames 4000–4099. Compare
    decoded SHA, information errors, atom counts and NMSE.
  - CSTATE: F0 and CD reproduce archived Stage 3 rows on at least 8 triggered keys from frames 4000–4399. A2 reproduces an archived
    E-1 / split-prosp A2 row where one exists on the same harness; otherwise record why not.
- **G2 construction and reduction.**
  - Synthetic checks: Γ_U is Hermitian PSD; each Π_lo is idempotent; single-atom delays are unchanged; on an exact duplicate pair, Γ_U
    applied to the equal split equals Γ applied to it.
  - U with τ = 0 (or u = 0) is bit-identical to CD in every exchange decision and the final state on the G1 CSTATE keys.
  - U2 with the refinement projector forced empty is bit-identical to S-lo.
  - The exact trial scores under Γ_U match a brute-force `_system` evaluation to 1e-10 relative on synthetic and smoke supports.
- **G3 repeatability.** New arms reproduce on repeated smoke runs (frames 8400–8411 or another previously used smoke block) after
  removing timings.

## Outputs
Per-key rows with decoded SHA, errors, NMSE (SBL), atom and co-delay counts, β and convergence (SBL), first-edit type, and the Π_lo
census (CSTATE). Rows stay on deinlab; `results.json` (with `_argv` / `_config`), `RESULTS.md` and the MD5 list come back.
