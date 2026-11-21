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