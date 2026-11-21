# Pilot 5 — SBL side of the detector-gain lead (2026-10-19; exploratory)

Predictions P11–P13 were committed before the run (cd8d5cd8, `research-assets/prediction-ledger.md`).
E-3 on-grid data-aided SBL (code imported unchanged). The same SBL output (atoms, gains, prior) is fed to two detectors:
fixed gains (E-3 as is) and joint gain re-estimation (only `gain_mode` changed). Slice: ρ .3, U and G, 7 and 8 dB,
fresh frames 9100–9299, 800 keys. Gate: the fixed path reproduces 24/24 saved E-3 keys bit for bit for both variants,
including the atom lists. The orchestrator's independent recount matches.

## Observation

| SBL variant | fixed-detector FER | joint-detector FER | transitions ok→fail / fail→ok | co-delay pairs | atoms |
|---|---|---|---|---|---|
| scalar Γ (L-diag) | .024 [.011, .039] | .101 [.076, .126] | 66 / 4 | 30.4 | 23.8 |
| full Γ (L-cov) | .088 [.065, .111] | .018 [.008, .031] | 1 / 57 | 5.0 | 22.9 |

- Interaction (scalar's degradation minus full's) = +.148 [.116, .179]. The sign is the same in every scenario × SNR
  group.
- A_fixed = +.064 [.045, .084]: the scalar variant is better with fixed gains.
- A_joint = −.084 [−.105, −.061]: the full variant is better with joint re-estimation.
- Full Γ with the joint detector has the lowest FER of the four combinations.

## Frozen predictions (scored in the ledger)
- P11 holds.
- P12 holds, but only because the sign flips.
- P13 (degeneracy) did not occur.

## Candidate explanation (untested, confidence M)
The SBL reversal is an interaction with the detector interface:
- Scalar-Γ SBL leaves about 30 near-duplicate co-delay pairs. With fixed SBL gains these are harmless. Once the detector
  re-estimates the gains, they make the problem ill-conditioned, as in CSTATE (pilot 4).
- Full-Γ SBL leaves well-separated atoms, but its gains are over-shrunk (res-20261018-02). Fixed gains expose the
  over-shrinkage; joint re-estimation repairs it.

## Limits
Pilot only: 200 frames, ρ .3, two SNR points, on-grid E-3 SBL (not Luo's D-GESBL), round 2 only. A prospective
confirmation on fresh frames (ρ .5, more SNRs, and the E-3b off-grid variant) is required before any claim.
