# Kill Argument Report — SP-AFDM data-aided channel reacquisition (claim brief, 2026-11-20)

**Reviewer model**: gpt-6.2-astra xhigh, two fresh `codex exec --sandbox read-only` sessions (Codex MCP is retired)
**Attack session**: 01a1f7f8-6b75-7ee0-9c66-87b4e579d152 · **Adjudicator session**: 01a1f7fa-2c1b-7581-bfa7-d53b67379d5f
**Input**: no manuscript; [CLAIMS.md](CLAIMS.md) and the evidence it cites (hashes in KILL_ARGUMENT.json)
**Verdict (computed from the per-point table, not by the adjudicator)**: **FAIL** (`reason_code: unresolved_critical`)

## Net assessment (adjudicator)
The architecture result and the diagnosis of the diagonal penalty would survive this memo. The attribution objection stands: the
materials establish a 1.14 dB advantage for the complete receiver over F0, a decoding cost from imposing the diagonal penalty, and a
small occupancy advantage for `CODELAY` over means-only scoring, but no incremental decoding gain from including soft-symbol
uncertainty in the search score over the simpler means-only search. The brief largely respects that distinction; the earlier covariance
attribution (E-1) and the wording "keeps both rays" are where evidence and submission still diverge.

## Attack memo (verbatim)
> The submission does not establish that its treatment of soft-symbol uncertainty contributes to the advertised 1.14 dB gain at a 1% frame error rate. The pilot-power sweep compares a receiver that searches again for missing paths after decoding fails with one that stops. It omits the decisive control at that operating point: the same search scored using soft-symbol means alone. [res-20261119-06.md, lines 15–34](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-06.md:15)
> 
> Where the authors run that control, it reproduces the central result. On 1,952 triggered cases, omitting the uncertainty penalty rescues 653 cases against 659 with the exact co-delay block. Both produce exactly 36 phantom first edits. Even on 2,400 frames constructed with genuine close path pairs, the frame-error difference is 0.54 percentage points, with a 95% interval of −0.03 to +1.13, inside the authors’ equivalence margin. [Distinct-delay experiment](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-01.md:31) · [Close-pair experiment](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-03.md:20)
> 
> The striking 89.1% phantom rate arises from assigning an independent uncertainty penalty to each candidate path. The authors’ literature search identifies no published fractional-Doppler support estimator that uses this penalty. The closest receiver, Luo et al., feeds back hard decisions. The diagnosis therefore explains the failure of an approximation introduced by the authors, while the headline gain establishes the value of reopening the path search. Neither result identifies a decoding gain attributable to the proposed criterion. [Literature comparison, §2](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md:60)
## Adjudication (verbatim)

### Point P1: Attribution of the 1.14 dB gain

**Attack claim**: The pilot-power sweep lacks the comparison needed to determine how much of the 1.14 dB gain at a 1% frame error rate (FER) comes from using soft-symbol uncertainty.

**Verdict**: still_unresolved

**Evidence (or lack of)**: The sweep includes the receiver that stops after decoding fails (F0), a search with a diagonal penalty, and a search with the exact co-delay block (`CODELAY`). The 1.14 dB difference, with a 98.33% interval of [0.56, 2.07] dB, compares F0 and `CODELAY` at their respective best tested pilot fractions. The brief correctly calls this an architecture gain. The means-only crossing is missing. [CLAIMS.md:15–19](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/CLAIMS.md:15) · [res-20261119-06.md:15–34](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-06.md:15)

**Severity if unresolved**: critical for attributing any share of the headline gain to uncertainty scoring.

**If unresolved, recommended fix**: A new experiment is required for attribution. Run means-only scoring on the same frames and pilot-power grid, hold the gain-refit rule fixed, and report the paired difference in best-tested 1% FER crossings against `CODELAY`.

### Point P2: Means-only scoring reproduces the distinct-delay result

**Attack claim**: On the 1,952 triggered cases, means-only scoring reproduces both the rescue rate and the low phantom count used to motivate the exact co-delay block.

**Verdict**: partially_answered

**Evidence (or lack of)**: Means-only scoring rescued 653 cases and `CODELAY` rescued 659. Each produced 36 phantom first edits. The paired rescue difference was −0.31 percentage points [−0.74, +0.10], inside the prespecified ±3-point margin. The authors intentionally include means-only scoring in their criterion. That position is sustainable for rescue pooled across the tested conditions. An earlier cited card still credits full covariance with the rescue. [res-20261120-01.md:26–41](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-01.md:26) · [res-20261120-01.md:64–75](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-01.md:64) · [CLAIMS.md:26–30](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/CLAIMS.md:26)

**Severity if unresolved**: major.

**If unresolved, recommended fix**: Reframing alone suffices here. Correct the earlier covariance attribution and state that either scoring choice achieved equivalent pooled rescue on the distinct-delay channel.

### Point P3: Genuine close pairs show an occupancy advantage

**Attack claim**: Even on channels containing genuine close path pairs, the 2,400-frame experiment establishes FER equivalence within the authors’ margin and supplies no decoding-superiority result for `CODELAY`.

**Verdict**: partially_answered

**Evidence (or lack of)**: At 7 dB and pilot fraction 0.5, means-only FER was 6.96% versus 6.42% for `CODELAY`. The paired difference of +0.54 percentage points [−0.03, +1.13] satisfies the prespecified ±1.5-point margin. `CODELAY` did place two atoms at the true close-pair delay more often, 959 versus 922 frames. The authors’ intentional preference for `CODELAY` is sustainable on that occupancy measure. Individual Doppler recovery was untested. [res-20261120-03.md:15–30](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-03.md:15) · [res-20261120-02.md:56–58](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-02.md:56) · [CLAIMS.md:31–35](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/CLAIMS.md:31)

**Severity if unresolved**: major.

**If unresolved, recommended fix**: Reframing alone suffices for the measured advantage. Replace “keeps both rays” with the tested endpoint, “places two atoms at the true doublet delay,” and report FER equivalence alongside it.

### Point P4: The 89.1% phantom rate has no identified published counterpart

**Attack claim**: The diagonal penalty responsible for the striking phantom rate is an author-constructed comparison. The closest published receiver, Luo et al., uses hard decisions and therefore supplies no example of this failure.

**Verdict**: partially_answered

**Evidence (or lack of)**: The literature check explicitly reports finding no fractional-Doppler support estimator using this path-coordinate penalty. Testing the diagonal rule from an orthogonal grid is an intentional and sustainable diagnostic choice. With the search held fixed, the diagonal arm produced 1,740 phantom first edits and 290 rescues versus 36 and 659 for `CODELAY`. This demonstrates a decoding cost for that approximation. Luo’s receiver uses a different rule. [lit-diag-soft-variance-20261120.md:60–66](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md:60) · [res-20261120-01.md:31–37](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261120-01.md:31)

**Severity if unresolved**: major.

**If unresolved, recommended fix**: Reframing alone supports the diagnosis. Identify the diagonal arm as the authors’ extrapolation and explain the failure directly: splitting one path gain equally between two coincident atoms halves its diagonal uncertainty penalty. [CLAIMS.md:20–25](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/CLAIMS.md:20)

## Summary

Total rejection points: 4; answered_by_current_text: 0; partially_answered: 3; still_unresolved: 1

## Net assessment

The architecture result and the diagnosis of the diagonal penalty would survive this memo. The reviewer’s attribution objection also stands. The materials establish a 1.14 dB advantage for the complete receiver over F0, a decoding cost from imposing the diagonal penalty, and a small occupancy advantage for `CODELAY` over means-only scoring. They do not establish an incremental decoding gain from including soft-symbol uncertainty in the search score over the simpler means-only search. The brief largely respects that distinction. Its earlier covariance attribution and its wording about recovering both rays are the two places where the cited evidence and the submission still diverge.

## Top action items

1. Add the paired means-only 1% FER crossing if the paper claims any part of the 1.14 dB comes from uncertainty scoring. The architecture claim can stand on the existing sweep.
2. Reconcile the earlier rescue attribution with the prospective means-only control, and identify the diagonal penalty as an author-constructed comparison wherever the 89.1% figure appears.
3. Justify the `CODELAY` default with the measured close-pair occupancy difference and give the paired FER interval in the same passage.
## Reading the FAIL (Claude)
- The single critical point (P1) is conditional: it is critical only if the paper credits part of the 1.14 dB to uncertainty scoring.
  The adjudicator states the architecture claim can stand on the existing sweep. Two exits: run the means-only (Γ = 0) arm on the
  ρ-sweep grid and report the paired crossing, or credit the system gain to the architecture alone.
- P2–P4 need reframing only, no new experiments.

## Correction note (Claude, 2026-11-20, after the run)
The claim brief (CLAIMS.md) labelled C1 "architecture" without stating its novelty status, so neither thread could judge it. The
project's own records already rule it out as a contribution: the 10-17 novelty verdict lists data-aided reacquisition as a method
class that cannot be claimed (Kanazawa, Luo, Zheng); novelty-positioning-20261118 §2 assigns the fixed-cardinality swap plus greedy
continuous-frequency refinement to SBR (Soussen TSP'11) and NOMP (Mamandipoor TSP'16); skeleton v1.4.2 treats F0, the syndrome
trigger and the exchange as the deployment shell. "The architecture result survives" in the net assessment therefore means the
evidence supports the number, not that the architecture is new.
