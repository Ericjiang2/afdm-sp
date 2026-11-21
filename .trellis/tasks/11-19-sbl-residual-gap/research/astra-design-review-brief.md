# Codex Astra brief: pre-freeze design review of the SBL residual-gap protocol (read-only)

Written 2026-11-19 by Claude (research-checkpoint §1.5; the result is stated as an intervention-level attribution). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only; your final message is the
deliverable. Model: `gpt-6.2-astra`. No receiver simulation; small in-memory algebra checks are allowed. Label claims D/N/A and issues
blocking or non-blocking.

## Material
- `.trellis/tasks/11-19-sbl-residual-gap/research/protocol-DRAFT.md`, `design.md`;
- `research-assets/res-20261119-03.md`;
- your spectral proposition `.trellis/tasks/11-19-unified-cov-prospective/research/astra-spectral-proposition-20261119.md`;
- `experiments/tf_e3_sbl_20261017/sbl_rx.py` (EM; Γ enters both the precision and the β update).

## Questions
1. **Construction.**
   - Is K (cap the exact co-delay eigenvalues above 1 at 1 in EM, with the Π_lo floor and cross-delay terms kept) a clean single-factor
     change from U2 for difference 1 in DRAFT §0?
   - Does capping interact with pruning by principal submatrix, or with the β update, in a way that confounds the attribution?
   - Is M (U2's EM output plus R0's scalar refinement) clean for difference 4?
2. **Coverage.** U2 and R0 also differ in the strength of the sub-resolution floor (u(1+λ) against u) and in the cross-delay terms. Is
   leaving these two unsplit acceptable when both K and M fail? Name the cheapest extra arm that would cover them, if one is needed.
3. **Decision rules.** Check for loopholes in the κ classification, the premise, the "both close" branch, and the leverage with 2,400
   keys for a 2.6 pp gap.
4. **Prediction.** From your proposition, would you expect K to close the gap? Give a derived or explicitly heuristic reason.

## Final message
English, ≤ 35 lines: the blocking items with minimal fixes first, then the non-blocking items, then the confirmed `model:`.
