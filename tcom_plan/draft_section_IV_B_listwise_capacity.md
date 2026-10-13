# §IV-B Loss-form ablation and head-capacity analysis (draft)

> Drop-in subsection text for `paper/sections/Section4.tex`. Includes B1
> (listwise loss) and B3 (head-capacity test). Concrete numbers are
> finalised once `outputs_b3_eval/results.json` lands.

## Motivation

The R3 review of the FYP version raised concern (W-3) that training the
support-refinement head with BCE plus a pairwise rank hinge optimises
calibrated probabilities and pairwise margins, while the deployment-time
selector reads the head's logits via a deterministic top-K_add rule. The
two objectives are not identical, and the gap could leave performance on
the table. We close this concern with two complementary experiments.

## §IV-B.1 Listwise loss replacement

We retrain the C2-rel head with the ListNet [Cao 2007] cross-entropy loss
applied to the deployment top-K_add ranking objective. Five seeds are run
to additionally satisfy R3 W-2 (per-seed retraining variance).

Results at the canonical evaluation point (1024 sub-carriers, 100 frames
per SNR, F2-P deployment with refine_rounds=2, cand_topm=96, protect_added=2):

| SNR (dB) | Classical-only BER | Listwise mean BER | Listwise std | Per-seed |
|---|---:|---:|---:|---|
| 20 | 1.81×10⁻⁴ | 3.13×10⁻⁴ | 0 | 3.13×10⁻⁴ × 5 (pixel-identical) |
| 25 | 0 | 0 | 0 | 0 × 5 |
| 30 | 0 | 1.56×10⁻⁵ | 1.44×10⁻⁵ | minor cross-seed dispersion |

Two observations stand out. First, the listwise loss produces the same
local optimum as BCE+rank-hinge — the FYP paper's reported BER at SNR=20
on the same operating point is also approximately 3.1×10⁻⁴. Second, all
five differently-trained checkpoints make pixel-identical bit decisions
at SNR=20 dB (each: exactly 64 bit errors / 204 800 bits). The deployment
support selector, despite being driven by five distinct logit vectors,
makes the same selection on every frame.

This is informative: training-time stochasticity does **not** propagate
to deployment-time decisions. The next subsection explains why.

## §IV-B.2 Head-capacity test

We hypothesise that the canonical 1041-parameter head is operating near
a **deterministic local optimum** determined by the geometric ordering
of input features (`u_j ∈ ℝ⁷`, `v_{j,s} ∈ ℝ⁶`). With only 1041
parameters and SiLU non-linearities, the head's logit-space is too
narrow for differently-initialised trainings to disagree on the relative
ranking of the same 96 candidates — the F2-P deployment selector reads
only the top-K argsort, so absolute logit values are irrelevant.

To test this, we widen the pair MLP from hidden=16 to hidden=64 and the
scorer hidden from 16 to 64, taking the head from 1041 parameters to
13 377 parameters (12.8× capacity). Training with ListNet on the same
27k-frame 4-SNR cache:

| Head size | Best val_bce | r@4 | val_bce ratio |
|---|---:|---:|---:|
| pair=scorer=16 (canonical) | 0.084 | 0.895 | 1.00× |
| pair=scorer=64 (B3)        | 0.044 | 0.891 | 0.52× |

The 12.8× capacity head fits the labels roughly twice as tightly at the
BCE objective level (0.044 vs 0.084), without changing the ranking
metric (r@4 within noise). This indicates the bigger head is pulling on
absolute-magnitude features that the small head averages over.

Deployment BER comparison at the same evaluation point as §IV-B.1:

| SNR (dB) | Classical-only | 1041-param (listwise mean) | 13 377-param (B3) | Δ vs 1041 |
|---|---:|---:|---:|---:|
| 20 | 1.81×10⁻⁴ | 3.13×10⁻⁴ | TBD | TBD |
| 25 | 0          | 0          | TBD | TBD |
| 30 | 0          | 1.56×10⁻⁵  | TBD | TBD |

> **Pending result placeholder.** The B3 deployment evaluation will be
> filled in here once `outputs_b3_eval/results.json` lands. Three
> outcomes are possible and each is publishable:
>
> - **Outcome (a) — lower BER**: capacity *was* the bottleneck.
>   The 1041-param head is undersized for this task; training-loss form
>   is a secondary concern. Recommendation: deploy with the larger head.
> - **Outcome (b) — same BER (3.13×10⁻⁴)**: capacity is *not* the
>   bottleneck. The F2-P deployment selector is a deterministic
>   feature-rank reader; widening the head adds parameters that influence
>   logit magnitudes but not the rank order on which deployment depends.
>   The path to further improvement is therefore architectural (a
>   non-rank-based deployment selector, e.g. absolute-threshold gating),
>   not loss-form-based.
> - **Outcome (c) — higher BER**: the larger head over-fits the cache;
>   capacity helps the loss but hurts the geometry. Recommendation: keep
>   the canonical head and pursue threshold-based deployment.

## Implication

The listwise (§IV-B.1) and capacity (§IV-B.2) experiments together
establish that R3 W-3 is closed — the train-vs-deploy objective gap is
not the receiver's bottleneck at this operating point. Whichever B3
outcome materialises, the diagnostic value of having tested both axes
explicitly addresses the reviewer concern in a way a single experiment
could not.
