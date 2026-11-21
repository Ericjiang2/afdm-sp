# Claim brief (stands in for a paper draft): data-aided channel reacquisition for SP-AFDM with fractional Doppler

Target: IEEE Transactions on Communications (regular paper). No manuscript exists yet; this brief lists the headline claims the
paper would make, the evidence behind each, and the limitations the authors already know. Paths are relative to
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Setting
AFDM with N = 1024, superimposed ZC pilot (power fraction ρ), LDPC-coded QPSK, doubly dispersive channel with 8 paths at integer
delays 0–102 and continuous (fractional) Dopplers. A two-round data-aided receiver (F0) estimates the channel from the pilot and the
decoder's soft symbols. When F0's LDPC syndrome stays nonzero, the receiver reopens the path support: it scores swaps of up to two
path atoms (delay, Doppler) on a 0.25-bin grid plus local Doppler refinement, refits, and decodes again ("triggered support
exchange"). Swap scores are the profiled least-squares fit on the soft-mean dictionary plus a data-uncertainty penalty hᴴ(Γ + λI)h,
where Γ depends on the soft-symbol variances v_n (u = Σ v_n).

## Headline claims
- **C1 (architecture).** Triggered support exchange rescues about one third of F0-failed frames and lowers the SNR needed for 1% FER
  by 1.14 dB [0.56, 2.07] against F0 (each at its best pilot fraction). Against Luo-style SBL ports in the same harness it wins on
  1403:0 / 1014:0 / 66:0 discordant keys at 11.9–16.0× lower single-core runtime.
  Evidence: `research-assets/res-20261119-06.md`, `res-20261118-03.md`, `res-20261017-01.md`.
- **C2 (diagnosis).** Adding the soft-symbol uncertainty diagonally in path coordinates (Γ = uI, exact on orthogonal integer grids)
  makes support exchange insert phantom near-duplicate paths at an occupied delay: first-edit phantoms 89.1% versus 1.8%; rescue
  14.9% versus 33.8%. Mechanism: the diagonal penalty does not collapse when two atoms coincide, and because it is quadratic in gain,
  splitting one path into two halves halves the penalty (Prop 2).
  Evidence: `research-assets/res-20261120-01.md`, `res-20261118-06.md`; proofs
  `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex`.
- **C3 (criterion).** Uncertainty may enter support scoring only in a split-invariant way: no penalty (Γ = 0), hard decisions, or the
  exact co-delay block (`CODELAY`) all avoid phantoms. A prospective test (prediction registered before the run) found Γ = 0
  equivalent to `CODELAY` on P1 (Δ rescue −0.31 pp [−0.74, +0.10]), and on a channel with genuine 0.35-bin co-delay doublets
  FER-equivalent within ±1.5 pp (+0.54 pp [−0.03, +1.13], 2,400 fresh frames).
  Evidence: `research-assets/res-20261120-01.md`, `res-20261120-02.md`, `res-20261120-03.md`.
- **C4 (`CODELAY` as the default member).** The exact co-delay block equals u·D_N(Δν) for any variance profile because AFDM's chirp
  makes every synthesis column time-flat and pushes cross-delay coupling into Dirichlet sidelobes (≤ 0.82% of u measured); it needs
  one scalar, closed form. On genuine close doublets it keeps both rays more often than Γ = 0 (occupancy −1.54 pp [−2.27, −0.81] for
  Γ = 0). Evidence: Prop 1 in the proofs file; `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md`
  §1, §4; `research-assets/res-20261120-03.md`.
- **C5 (mirror).** In overcomplete-grid SBL the same non-collapsing diagonal term acts as a useful floor on the unidentifiable
  difference directions: the scalar SBL variant has lower FER than the exact-Γ variant, and adding only a sub-resolution floor to
  exact Γ recovers the gap prospectively. Evidence: `research-assets/res-20261119-02.md`, `res-20261119-03.md`, `res-20261017-03.md`.

## Positioning (from a literature check)
No paper found uses the diagonal model with soft variances in fractional-Doppler support search or SBL; data-aided estimators there
use hard or mean symbols with isotropic noise (e.g. Y. Luo, IEEE TCOM 2026) or exact second-moment weights (VALSE, BEM message
passing). The diagonal form is textbook where atoms are orthogonal (MIMO-OFDM turbo channel estimation). Evidence:
`.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md`.

## Known limitations
- Two synthetic channel families (P1: distinct delays; MIXED8: one 0.35-bin and one 0.75-bin doublet per frame), known noise
  variance, QPSK, ρ mainly .3/.5; no measured channels.
- Single-frame noise estimation costs about 1 dB; decision-directed estimation was worse (`research-assets/res-20261118-05.md`).
- The SBL mirror is shown for one SBL configuration (E-3c); a Γ = 0 SBL arm has not been run.
- Path count is assumed known (cap = 8).
