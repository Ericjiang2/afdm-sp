# SBL spectral-split Phase 1 design

## Reference rows and computation

Join R0/R1/R2 outcomes at `max_iter=100`. On 2026-11-19 a read-only check on deinlab verified all 24 gzip shards against the local E-3c MD5 manifest. It found exactly 1,200 distinct expected keys and all 3,600 reference arm rows included `sbl.{beta,iterations,converged,n_final}`, `n_atoms`, `n_pair`, `pairs`, `fer`, and `nmse`. Validate those fields and the key set again when joining. [E-3c archive and manifest location](../../../research-assets/res-20261018-01.md)

T0 still consumes the live R1 SBL output for that key and iteration budget. Cache the result before output selection so T0 and R1 can use the same indices and posterior gains. At 100 iterations the join supplies R1's archived terminal result, and T0's timing must include the required live R1 SBL fit. At 400 iterations measure and charge the R1 fit and its terminal scoring.

## Receiver data flow

Reuse E-3c key selection, source identity verification, receiver context, arm specifications for the references, scoring, and E-3 EM and candidate functions. E-3c's `process_key` hardcodes its own six-arm loop, so the new experiment needs a local preparation and dispatch path. Preserve operation order in the shared E-3c stage 1, round 1 and stage-2 candidate preparation for exact parity. Attribute any copied frozen function as specified in the brief.

On the candidate set compute full Γ and `u = sum(v)` once. Construct the delay-block projectors and ridges from the eigenpairs of `D_l = Γ[S_l,S_l]/u`, using `λ < .5` for Π_lo. Pass each effective Γ into frozen `sbl_em`. Its existing principal-submatrix restriction prunes a pre-added ridge with the same indices as Γ. Check this on a synthetic case where pruning removes an atom from a projected block. Test the refinement contribution directly from `_system` and verify normal-equation closure separately. The SBL component and refinement component each have their own expected value for S0, T0 and the four spectral arms. [Frozen EM](../../../experiments/tf_e3_sbl_20261017/sbl_rx.py) · [E-3c covariance checks](../../../experiments/tf_e3c_shrink_20261018/e3c_arms.py)

Record initial EM ridge trace and refinement ridge trace at their respective atom counts. Record the inclusive [.25, .75] eigenvalue count and total candidate eigenvalues from the same full-Γ blocks once per key and attach them to arm diagnostics. For joined reference rows, derive the traces from the arm formulas and attach the common candidate census. Pool the 12 key counts for the smoke share.

## Execution and receipts

The Phase 1 launcher exposes only synthetic, seeded parity and smoke modes. G1 uses `e3c_lib.gate_keys()` and runs R0/R1/R2 at 100 iterations. G2 and G3 run on the smoke allowlist from `e3c_lib.smoke_keys()`, with G2 also covering synthetic inputs. Check actual loaded paths and hashes against the frozen manifests, and bind receipts to source hashes, keys, runtime and `_argv`/`_config`. Frozen source or archive discrepancies stop the run. Own-code discrepancies get a recorded fix and a new attempt directory.

Time all arms at both budgets on the 12 smoke keys. Charge shared preparation once per key per cohort and count the live R1 SBL fit required by T0 once. Apply the 1.3 multiplier to the projected elapsed core-seconds for 1,200 keys × six new arms at 100 and 600 keys × R1/S0/S-lo/S-hi at 400. If above 30 core-hours, recalculate the 400 cohort with frames 4000–4024 (300 keys). Return the projection and stop if the reduced schedule also exceeds 30.

In the experiment DRAFT, explain the archive join, the trace and eigenvalue logging conventions, the separate side-specific checks, and any cost-triggered subset change. The scientific rules and predictions remain those in the task draft. [Task draft](research/protocol-DRAFT.md)
