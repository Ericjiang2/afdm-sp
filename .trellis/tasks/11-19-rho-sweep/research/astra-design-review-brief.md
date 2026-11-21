# Codex Astra brief: pre-freeze design review of the ρ-sweep protocol (read-only)

Written 2026-11-19 by Claude. Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Read-only; your final message is the deliverable. Model: `gpt-6.2-astra`. No receiver simulation; small in-memory checks are allowed.
Label claims D/N/A and issues blocking or non-blocking.

## Material
- `.trellis/tasks/11-19-rho-sweep/research/protocol-DRAFT.md`, `design.md`;
- `research-assets/res-20261118-03.md` (Stage 3 crossings and censoring);
- `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md` §2 (two-ρ readout);
- skeleton v1.3 `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md` (window caveat);
- `research-assets/res-20261119-01.md` (window vs reality).

## Questions
1. **Predictions.** Does the window lower bound 1 + 2(1−x)/x with x = 2(1−ρ)v̄ really predict that CODELAY's gain over the scalar grows
   as ρ falls? Account for these effects:
   - how u and E change with ρ;
   - pilot-only F0 getting worse;
   - detector absorption.

   If the direction is ambiguous, say what the design should predict instead.
2. **Metrics.**
   - Are crossing-based contrasts (Δg, argmin ρ*, Δ_best) sound under left and right censoring?
   - Is averaging the two scenarios right?
   - Is the "≥ 95% of draws" rule for an argmin over a 6-point grid meaningful, or should V2 use a smoothed or paired comparison?
3. **Discrimination.** Do V1 and V4 separate H-window from H-F0 and H-collapse, as the table claims?
4. **Design.**
   - Is the ρ grid adequate?
   - Is the SNR grid adequate?
   - Are 400 frames enough to resolve 10⁻² crossings at low ρ?
   - Any confound in ρ changing both the pilot power and the data power at fixed total power?

## Final message
English, ≤ 35 lines: blocking items with minimal fixes first, then non-blocking items, then the confirmed `model:`.
