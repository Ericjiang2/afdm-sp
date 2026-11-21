# FROZEN 2026-11-18 — One decision-directed noise variance update

Eric approved the freeze and 5 core-hour cap after Phase 1 qualification at `d7617798`. Decision rules are never relabelled.
The prior slot-mismatch N cell shifted the B crossing by +1.189 dB at cap 8 and +0.992 dB at cap 12.
The fixed true-channel A3 crossing shifted from 4.679 to 5.000 dB. These are observations from
one calibrated single-frame estimator under G, physical pilot fraction .3. [Slot-mismatch readout](../slot_mismatch_20261019/out/RESULTS.md)

## Receiver and units

Use the frozen P1 normalizer with physical pilot power fraction `rho=.3`. It divides the physical
AF-domain observations and pilot by `a=sqrt(2*(1-rho))`, the physical noise variance by `a²`,
and leaves the channel gain convention unchanged. The internal data symbol power is .5.
`obs["sigma2"] = E[|w_AF|²]` is variance per **complex** internal AF sample. The AF transform
is unitary. There is no additional sample-power, real-dimension or rho conversion in the DD kernel.

B_known uses the generated true variance throughout. B_SF uses the exact frozen N-cell moment
`s0=max(.001, (||y||²-||pilot||²)/N-.5)` throughout. For B_DD the pilot front and first F0
round use `s0`. After the first LDPC call, take delays and Dopplers from the round's native
CE, complex gains `h` from the scalar-joint detector's returned state, and the vectors
`mu,v` from the clipped LDPC APP with internal symbol power .5. These are observed-input
estimates. Use the APP rather than the detector soft output because it is the state which
enters the existing second-round CE. With `N=len(y)=1024` compute

```text
raw = (||y - B(pilot + mu) h||² - Re(hᴴ Γ(v) h)) / N
sDD = max(.001, raw)
```

`B(x)` has columns given by the AF-domain response of each selected unit-gain path to `x`.
`Γ(v)[i,j] = tr(U_iᴴ U_j diag(v))` is the exact projected variance from the frozen
`physical.projected_variance`, including cross-delay terms. Both numerator terms are
total internal AF receive energy. In the extreme case of true geometry, gains and symbols
with `v=0`, the result before flooring is the mean squared magnitude of the normalized noise.
For true `H`, centered symbol error with diagonal covariance `diag(v)` and zero error–noise
cross moment, expected residual energy is `N*sigma2 + Re(hᴴ Γ(v) h)`. In production, APP depends
on the same `y`, its errors may be correlated or miscalibrated, and geometry and gains are fitted.
These conditions can move the estimate in either direction.

Use `sDD` in F0 round 2 CE and scalar-joint detection. Retain the same check prior, decoder
schedule and LLR clipping. The LLRs carry the new detector likelihood. With nonzero final
F0 syndrome use frozen A1c CODELAY with the same two swaps and two local passes, including
ridge and detector noise set to `sDD`. A1c retains its frozen covariance construction from
the new round-2 APP. With zero syndrome use F0. Only one update is made. A3 retains the
original fixed true channel, with the corresponding variance fixed for both of its rounds.
A3_DD receives the value produced by B_DD, so it measures that value's downstream suitability
under true H and also inherits its dependence on the ordinary receiver.

## Design and decisions

- Proposed P1 G cohort: physical rho .3, P=8, cap 8, frames 11000–11999 inclusive, and
  4.5–8.0 dB in .5 dB steps. The corrected P1 entropy `2261fde3…` and domain `TCRF` are
  inherited. The three B and three A3 arms use the same observation, noise realization
  and LDPC message at each key. G3 binds the frame reservation before the run.
- Use unconditional information-bit FER. Compute the first FER=.01 crossing with the
  frozen slot-mismatch log interpolation and a zero replacement of `.5/n` inside the
  bracket only. Report censor bounds throughout, with no extrapolation.
- Use 20,000 paired physical-frame bootstrap draws, seed 20261019, sharing the
  multiplicities across all SNRs and six arms. Preserve unbounded endpoints in the
  paired differences and the 2.5th/97.5th percentiles.
- Primary: the paired 95% interval of `Δ_DD = crossing(B_DD)-crossing(B_known)`.
  **ROBUST** if the interval is inside [−.25,+.25] dB. **DEGRADED** if its lower bound
  exceeds +.25 dB. **INCONCLUSIVE** otherwise.
- Secondary: report `R = crossing(B_SF)-crossing(B_DD)`, the three A3 crossings,
  and per-SNR means, SDs and floor rates of `sDD/sigma2`. Report DD's noise diagnostics
  overall and by final F0_DD syndrome trigger, with stratum sizes. Compare paired
  round-1 DD/known delay sets and report missed true delays by the same diagnostic
  strata. Truth is used only for scoring and A3.
- Precision: at n=1000, ten errors give a pointwise exact 95% FER interval of about
  [.0048,.0183]. A shallow crossing or weak pairing can leave the ±.25 dB decision
  unresolved. The historical cap-8 loss is large enough to motivate the comparison.

## Competing hypotheses and premortem

| Hypothesis | B arms | A3 arms and auxiliary predictions |
| --- | --- | --- |
| H-good | DD recovers known-noise performance within ±.25 dB while SF retains a positive gap. | A3_DD is closer to A3_known than A3_SF if the updated likelihood scale explains part of the recovery. |
| H-bias | B_known leads B_DD by >.25 dB, with B_DD improving on B_SF. | Positive DD bias concentrates on triggers. A3_DD can retain a smaller positive gap when estimated noise itself harms decoding. |
| H-none | B_DD and B_SF are practically equivalent within ±.25 dB despite their different estimates. | A3_DD can improve while B does not if the shared SF first round limits recovery. If both stay close to SF, examine variance calibration and likelihood sensitivity. |

A missed path or gain misspecification can inflate the DD residual on the frames that
trigger A1c. Stratified estimates and geometry counts check that association, and the
same-frame A3 contrast reveals downstream sensitivity under fixed true H. A high
floor rate is also possible if noise-dependent APP removes residual noise or
overstates removable uncertainty. The reported raw estimate, floor rate and G2
isolate floor clipping and unit errors. The shared SF initialization may change
the first-round geometry before the update can help. DD/SF round-1 parity plus
the DD/known geometry comparison make that limitation visible. This study
tests end-to-end robustness of this specific estimator and timing point.

## Qualification and cost

1. G1 on deinlab, 32 historical paired G/.3/cap-8 keys from frames
   10000, 10001, 10998 and 10999 across all SNRs. Compare B_known to M and
   B_SF to N. Require exact F0 syndrome, information errors, both slot counts,
   delays and Dopplers. On every trigger compare A1c edits, final geometry and
   information errors. The archived JSON floats round-trip, so use bitwise Dopplers.
2. G2 on 32 historical frames 7800–7831 across all eight SNRs. Use true geometry,
   gains, and symbols (`v=0`), reconstruct the normalized waveform, and require
   mean `sDD/sigma2` in [0.98,1.02] both pooled and at each SNR. Report the bias
   and floor rate using the same H and heterogeneous synthetic soft moments
   from independently flipped I/Q signs with fixed AF-coordinate flip probabilities
   .05 and .20. This side information is independent of the channel-noise draw.
3. G3 repeats the slot-mismatch output/config and static frame-range scan in both
   the local and deinlab experiment trees, including files without a P1 flag.
   Review every source hit for P1 usage and rerun the inventory before any main launch.
4. Smoke uses 16 old frames (7832–7847) at all eight SNRs, rotating arm order
   and timing generation, both F0 rounds, triggered A1c, and each A3. Require DD/SF
   round-1 arrays to agree bitwise. On one triggered old key, check that
   a single update supplies the second F0 round, A1c ridge and detection, and both A3 rounds.
   Extrapolate the summed process CPU times to
   8,000 observations, include a 30% allowance, and project wall time at 16
   single-thread workers. Eric sets the cap before launch.

An archive, frozen receiver or scientific gate failure stops Phase 1. Runner
defects are corrected, documented and rerun. The future launch uses one unattended
chain with a CPU budget stop and a terminal DONE/STOPPED record.

## Phase 1 evidence

- G1 matched all saved fields on 32/32 keys per arm. The compared Dopplers
  were bitwise equal, including all 6 B_known and 14 B_SF A1c branches.
  [Receipt](out/gate_20261118/g1_final.json)
- G2 reconstructed the normalized waveform within `2.18e-12` maximum absolute
  difference. The zero-variance mean ratio was 1.00213 at each SNR and pooled.
  The synthetic positive-variance case had pooled relative bias +1.08%, with
  per-SNR means 1.00893–1.01301 and zero floor hits. SNRs share the 32 noise draws.
  [Receipt](out/gate_20261118/g2_final.json)
- G3 found no overlap with P1 or other recorded frame IDs in the proposed block.
  The local and deinlab scans inspected 1,293 and 12,382 existing output files
  and 1,087 and 1,028 source files, respectively. The reviewed static matches
  contain no use of the proposed P1 frames. [Receipt](out/gate_20261118/g3.json)
- Smoke timed 128 historical keys per arm. Estimate 3.12 core-hours for the full
  design, or 4.06 core-hours and 15.2 minutes at 16 workers with the allowance.
  The suggested cap is 5 core-hours. The out-of-timing routing check observed
  one DD update on a triggered key that reached the floor.
  [Receipt](out/gate_20261118/smoke_final.json)

## Changes from the Claude draft

- Wrote the normalization and complex-variance convention explicitly to avoid a
  second rho or factor-of-two conversion. The numeric estimator and floor are unchanged.
- Specified post-LDPC APP, detector gains and CE geometry, and traced ridge,
  likelihood and A3 variance usage so the compared paths have a single timing
  difference between SF and DD. A3_DD shares B_DD's estimate for a matched fixed-H contrast.
- Qualified the expected-energy identity by its error–noise and covariance
  assumptions, and added possible downward bias and floor diagnostics because
  production APP depends on the received noise.
- Defined the bootstrap seed, FER interpolation, censoring and precision with
  the slot-mismatch decision rule. Clarified that trigger strata and A3 are descriptive.
- Replaced G1 decoded-hash matching after archive inspection, per `881ddfc8`.
  Added the G2 waveform reconstruction and synthetic side-information definition
  to make the units and positive-variance test reproducible. The zero-variance
  tolerance is checked per SNR as well as pooled. Fixed the smoke sample and cost
  allowance to cover the full grid and shared generation.
