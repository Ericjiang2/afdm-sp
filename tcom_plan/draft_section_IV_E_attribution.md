# §IV-E Per-candidate mechanism attribution (draft)

> Drop-in subsection text for `paper/sections/Section4.tex`. Concrete
> numbers are filled in once `outputs_attribution/attribution.json`
> lands.

## Motivation

The FYP review's verdict on claim C4 — that the learned head's added
atoms are concentrated on Dirichlet-sidelobe positions of physical taps,
rather than fitting noise — was *partial* ("consistent with") because no
direct attribution was performed. We close that gap here by
geometrically classifying every head-added atom against the simulator's
known physical paths.

## Method

For each frame in a 250-frame paired evaluation run at SNR ∈ {15, 20,
25} dB, we hook the F2-P refinement step to record:

1. The raw OMP support `S_omp` (size = sparsity = 8).
2. The post-refinement support `S_final` after F2-P selects up to
   K_add=4 additional atoms.
3. The simulator's true physical paths (`l_p`, `k_p`) for that channel
   realisation.

The set of "head-added" atoms is `S_final \ S_omp`. For each added atom
`(l_a, k_a)`, we classify it geometrically against every physical path
`(l_p, k_p)`:

| Class | Definition |
|---|---|
| Main-lobe collision | `l_a == l_p AND k_a == k_p` (head re-picks an OMP atom that survived) |
| Dirichlet sidelobe | `l_a == l_p AND |k_a - k_p| ≤ 1`, and not on tap |
| Virtual tap | `|l_a - l_p| ≤ k_leak AND |k_a - k_p| ≤ k_leak`, and not on the prior two |
| False positive | More than `k_leak = 2` bins from any physical path |

## Results

> **Pending result placeholder.** Filled in from
> `outputs_attribution/attribution_summary.md` when the run lands.

| SNR (dB) | Added/frame | Main | Sidelobe | Virtual | False | Side+Virt% |
|---|---:|---:|---:|---:|---:|---:|
| 15 | TBD | TBD | TBD | TBD | TBD | TBD% |
| 20 | TBD | TBD | TBD | TBD | TBD | TBD% |
| 25 | TBD | TBD | TBD | TBD | TBD | TBD% |

## Interpretation rule

If "Sidelobe + Virtual" exceeds 60 % across all three SNRs, the §IV-E
claim moves from "consistent with side-lobe repair" to "explanatory
evidence supports side-lobe repair as the dominant mechanism." Below
60 % indicates a more mixed mechanism, in which case the strongest
single class is reported and the partial-verdict language of the FYP
version is preserved.
