# Idea harvest — Devin (independent), 2026-11-19

Models: lead = Devin, "Fusion (Claude Fable 5.2 Low + SWE-2 High)". Sidekick: not run (all reading, aggregation and writing done by the lead).
Independence: did not read `idea-harvest-claude-*`, `ambition-direction-*`, `divergence-*` or any Astra output.
Constraints kept: no simulation, no remote access, no commit; only this file written. Two local read-only aggregations of saved `results.json` were made (stated where used).

Labels: **[G file]** grounded in a file, **[D]** derived by me from grounded numbers, **[A]** assumed.

Data-availability fact that bounds every check below: per-key raw rows of every experiment are remote only (local `out/*/REMOTE_ROWS_MD5.txt` / `RAW_SHARDS_MD5.txt` list them; no `rows*.jsonl.gz` exists locally) [G `experiments/*/out/*/`]. Checks marked LOCAL use local `results.json`; checks marked REMOTE-ROWS need a readout over saved rows on deinlab (no receiver calls), which I could not run.

---

## Ranking (value × probability of surviving its check)

| # | Idea | Value | P(survive) | Place |
|---|------|-------|-----------|-------|
| 1 | CODELAY keeps the receiver near the true-H bound while pilot power drops; F0 does not. The paper's gain is a pilot-overhead result, not only a covariance result | high | ~.7 | paper 1 main text |
| 2 | One spectrum, two opposite failures; correct placement depends on the algorithm class (discrete exchange vs overcomplete EM) | high | ~.6 as scoped | paper 1 main text (already there; tighten) |
| 3 | Standard AFDM chirp makes cross-delay uncertainty negligible, so CODELAY is the structure AFDM itself selects, not an approximation of FULL | medium-high | ~.6 | paper 1 main text, one paragraph + one figure |
| 4 | Scalar phantom reward is ~9× the reward of the true missed path: a quantitative "why scalar must fail" | medium | ~.8 | paper 1 main text (one number) |
| 5 | SBL residual gap is two additive pieces (EM sum-mode excess + refinement covariance) | medium | ~.4 | paper 1 discussion/appendix |
| 6 | Fixed heuristics (blanket co-delay ban, near-duplicate ban, scalar) each fail in one regime | low-medium | ~.8 | paper 1 appendix table |

---

## Idea 1 — CODELAY is what lets the receiver follow the true-H bound when pilot power is cut

**Claim.** Going from ρ=.5 to ρ=.3 moves the true-H (ideal CSI) FER=.01 crossing by about 1.5 dB. F0 gets almost none of that; CODELAY gets about 1.2–1.3 dB of it. So the estimation loss (gap to true-H) of F0 roughly triples while CODELAY's stays within about half a dB. Stated for a reader: same decoder, same waveform, about 40% less pilot power fraction for a comparable estimation loss.

**Evidence.**
- True-H reference `A3` crossing, P=8 family M, scenario U: 4.66 dB at ρ=.3, 6.14 dB at ρ=.5; scenario G: 4.68 / 6.12 [G `experiments/slot_mismatch_20261019/out/main_20261118/results.json`, `q1.curves`; A3 = "original fixed true-H reference" per `PROTOCOL.md` l.17]. LOCAL aggregation done by me.
- Same file, arm `B` cap 8 (CODELAY continuation on triggered frames, F0 otherwise): U 5.24 / 6.23; G 5.15 / 6.22. Gap to true-H: U .59 → .08 dB, G .47 → .10 dB [D].
- Fresh ρ sweep: F0 6.61 (ρ=.3) / 6.77 (ρ=.5); CD 5.00 / 6.28; A2 5.72 / 6.45, scenario U [G `experiments/rho_sweep_20261119/out/main_20261119/results.json`, `crossings`; res-20261119-06].
- Cross-experiment gap to true-H [D, different frame sets]: F0 ≈ .63 dB at ρ=.5 → ≈ 1.95 dB at ρ=.3; CD ≈ .14 → ≈ .34 dB.
- At ρ=.5, 5 dB, true-H itself fails on 946/1000 frames [G slot_mismatch `q1.curves` error_counts]. This is the missing explanation for "both rescue rates near zero at ρ=.5" in `mechanism-readout-20261119.md`: there the channel estimate is not the bottleneck [D]. It partly substitutes for the TRUE_GEOMETRY arm the ρ sweep lacks.

**What it adds.** The skeleton currently sells a covariance mechanism. A TCOM reader cares more about a system number: pilot overhead. This turns res-20261119-06 from "CODELAY is best at ρ≈.25–.30" into "the scalar receiver cannot use the SNR that pilot reduction frees; the co-delay block can, to within ~.5 dB of ideal CSI". It also gives claim 1 of the skeleton ("residual gap to ideal CSI is missed weak delays") a ρ-dependence that is its strongest support.

**Killing alternative.** The comparison mixes two experiments (frames 10000–10999 with cap 8 vs the ρ-sweep frames, possibly different cap/schedule). If F0 on the slot-mismatch frames is itself within .5 dB of A3 at ρ=.3, the "F0 cannot follow" half is an artefact of mixing.

**Cheapest falsifying check.**
- LOCAL part (done): `B_8 − A3` gap ≤ .75 dB at ρ=.3 in both scenarios — holds (.59, .47).
- REMOTE-ROWS part: rows `rows_shard*.jsonl.gz` of slot_mismatch main_20261118, filter `family=='M'`; per (scenario, rho_permille, snr_centi_db) compute FER of F0 from `s['8']['f0']['info_errors'] > 0`, of B_8 from `s['8']['arms']['A1c']['info_errors'] > 0` if `s['8']['triggered']` else the F0 value, of true-H from `A3['info_errors'] > 0`; interpolate FER=.01 crossings with the existing `phase3_crossings.py` routine; frame bootstrap (1000 frames). Statistic: Δ = [cross(F0) − cross(A3)]_{ρ=.3} − [cross(F0) − cross(A3)]_{ρ=.5}, same for B_8.
- Decision rule: idea survives if Δ_F0 95% lower bound > .5 dB and Δ_B8 95% upper bound < .75 dB. If Δ_F0 < .5 dB, drop to discussion.

**Limits to state in the paper.** True-H reference exists only at ρ ∈ {.3,.5}; collapse below ρ=.25 (res-20261119-06: ρ=.20 loses 1.21 dB) means the claim is a band, not "less pilot is always fine" [G]. P1 distinct-delay channels only.

**Place:** paper 1 main text (results headline and abstract sentence). Confidence **M** (H after the REMOTE-ROWS part).

---

## Idea 2 — Same spectrum, opposite failures; the placement rule depends on the algorithm class

**Claim.** The co-delay block ≈ u·D has large eigenvalues on sum modes and near-zero ones on difference modes. Discrete exchange fails when the sum mode is under-penalised (scalar → phantoms); overcomplete EM fails when the difference mode is under-regularised (exact Γ → SBL loss). The supported statement is a stage-specific rule, not a universal covariance.

**Evidence.** SBL FER: scalar .0408, full Γ .1900, S-lo .0763, S-hi .1838, U2 .0671; CSTATE: A2 .1302, CD .0974, U .0974, C-lo .1303 [G res-20261119-03]. Γ_U costs 4.17 pp two-atom representation on true 0.35-bin doublets, FER +1.00 pp [−.17, +2.17] [G res-20261119-04]. Replay split [G res-20261119-02].

**Adds.** A design rule a reader can reuse outside this receiver: decide where uncertainty must be coherent by asking whether the stage chooses among atoms (needs sum-mode truth) or fits amplitudes over a redundant dictionary (needs a difference-mode floor).

**Killing alternative.** The SBL effect is not spectral at all but a generic "any extra diagonal loading helps EM"; then S-lo wins only because it adds more trace.

**Check (REMOTE-ROWS, unified_cov_prospective main_20261119).** Rows: SBL stage, arms `S-lo`, `S-hi`, `S-isolo`; fields per key: arm `info_errors` (failure = >0), frame. Statistic: paired frame-cluster bootstrap of FER(S-hi) − FER(S-lo) and FER(S-isolo) − FER(S-lo). Rule: spectral reading survives if FER(S-hi) − FER(S-lo) lower bound > 5 pp (point is 10.75 pp [D]) and S-isolo (trace-matched isotropic floor, .0875) is not better than S-lo. Already close to settled from the card; the open part is only whether S-isolo ≈ S-lo (.0875 vs .0763 [G]) — if their paired interval contains 0, the honest wording is "a floor on difference modes is sufficient; an isotropic floor of the same size does about as well", which weakens "spectral" to "any floor that reaches the difference modes".

**Place:** main text, as scoped. Confidence M.

## Idea 3 — AFDM's chirp selects the co-delay structure

**Evidence.** Actual cross-delay coupling ≤ .0082u (median .00061u) over 1,000 failed frames; OFDM no-chirp counterfactual median .039u, i.e. ≈65× (median) / 16× (p95) [G `zero-cost-readouts-20261119.md`]. CODELAY vs FULL discordance 0:0 on 13,600 keys [G res-20261118-03].

**Adds.** Makes CODELAY an AFDM property ("the waveform diagonalises uncertainty across delays"), which answers the reviewer question "why not FULL?" by structure instead of by runtime (runtime gain over FULL is only 1.2% [G res-20261118-03]).

**Killing alternative.** Post hoc, failed frames only, one c1/c2 setting; the OFDM number is a structural counterfactual, not an OFDM receiver. The 0:0 result could hold because cross-delay terms are small in these channels (distinct delays), not because of the chirp.

**Check.** No saved row holds cross-delay covariance per key outside the 1,000-frame readout [G code inspection: CSTATE rows store edits/outcomes, not Γ]. Existing-data check is therefore only: in the readout's own table, the AFDM max (.0082u) must be below the OFDM 5th percentile; if the readout does not report that percentile, the claim stays "median 65×" and goes in as one paragraph with the word counterfactual. A full test needs a c1 sweep = new computation, out of scope [A].

**Place:** main text, one paragraph + one figure. Confidence M.

## Idea 4 — Scalar pays more for a phantom than for the truth

**Evidence.** Median reward: A2 phantom 117λ, true missed path 13.5λ, false new delay 34λ; CODELAY phantom 8.2λ [G `zero-cost-readouts-20261119.md`]. A2 reward model fit Spearman .9991; phantom share +21.98 pp inside vs outside the window [G res-20261118-06]. 64.6–97.1% of phantom repeats attributable to missing coupling [G res-20261118-01].

**Adds.** One sentence that makes the failure inevitable rather than occasional: ratio ≈ 8.7 [D] phantom/true under scalar, ≈ .6 [D] under CODELAY.

**Killing alternative.** Medians are over different candidate populations; per frame the true path may still win.

**Check (REMOTE-ROWS, ratio_sweep main_v2_20261119).** Rows with `defined==True`; per row and arm (`A2`, `CODELAY`) the phantom, true-delay and false-delay gains (`G_P`, `G_T`, `G_F`). Statistic: fraction of rows with G_P > G_T, per arm, pooled over `rho`,`R`. Rule: survives if A2 fraction ≥ .8 and CODELAY fraction ≤ .3; otherwise report medians only and drop "must".

**Place:** main text (one number). Confidence M-H.

## Idea 5 — The SBL residual gap is two pieces

**Evidence.** FER: U2 4.96%, K′ 3.42%, M 3.75%, KM′ 2.58%, scalar R0 2.63%; K′ recovers .66, M .52 of the gap, both frozen uncertain against the half-gap criterion [G res-20261119-05].

**Killing alternative.** KM′ is a secondary, non-preregistered arm; .66 + .52 > 1 means the pieces overlap, so "additive" is wrong as stated [D].

**Check (REMOTE-ROWS, sbl_residual_gap main_v2_20261119).** Per key failure indicators of U2, K′, M, KM′. Statistic: among keys where U2 fails and R0 succeeds, 2×2 table (K′ fixes, M fixes). Rule: "two mechanisms" survives if both off-diagonal cells are ≥ 15% of that set; if one cell is < 5%, it is one mechanism seen twice.

**Place:** discussion/appendix. Confidence L-M.

## Idea 6 — Every fixed heuristic fails somewhere

**Evidence.** Blanket co-delay bans fail on genuine sparse doublets; CODELAY matches FULL; each fixed scalar ban fails in at least one regime [G res-20261118-02]. Slot cap 6 degraded, 10/12 robust [G res-20261118-04]; estimated noise variance costs ≈1.64 dB [G res-20261118-05].

**Adds.** A guardrail table; pre-empts "just forbid repeated delays". **Kill:** regimes were chosen by us. **Check:** LOCAL, res-20261118-02 table: count regimes where each arm is within its margin; rule: table is worth printing only if no fixed heuristic passes all regimes and CODELAY passes all. **Place:** appendix. Confidence H (low value).

---

## Single most valuable idea

**Idea 1**, confidence **M**: the paper's headline should be pilot economy — CODELAY keeps the receiver within ≈.1–.6 dB of true-H while ρ goes .5 → .3 and the true-H bound moves ≈1.5 dB; F0's loss grows from ≈.6 to ≈1.9 dB. One readout over saved slot-mismatch rows (F0 on the same frames as A3) confirms or kills it.

## Where we are fooling ourselves

1. **"One covariance unifies both failures" (skeleton claim 4) is stronger than the data.** Scalar still wins in SBL (.0408 vs U2 .0671 [G res-20261119-03]); U = CD on P1 is zero-discordance almost by construction; Γ_U hurts true 0.35-bin doublets [G res-20261119-04]; an isotropic floor does nearly as well as the low-mode floor (.0875 vs .0763). What is shown is an explanation of two failures, not a covariance to use. **Strongest item.**
2. **The closed-form flip window is not a predictor.** A2 prefers phantoms far beyond it; detector absorption shifts the flip [G res-20261119-01]. The +21.98 pp inside/outside contrast is association, not a threshold law.
3. **"Data-limited at ρ=.5" was inferred without a true-H arm in the ρ sweep.** The slot-mismatch A3 numbers support it, but from other frames [D].
4. **CODELAY vs FULL**: equal FER and 1.2% faster. Any "low-complexity" wording must be against Luo-style ports (11.9–16.0×), not FULL [G res-20261118-03].
5. **Chirp suppression (65×)** is a post hoc readout on failed frames against a counterfactual, not an OFDM experiment.
6. **Robustness**: cap 6 degrades and estimated noise costs 1.64 dB [G res-20261118-04/05]; all headline gains assume known noise variance and cap ≥ 8.
