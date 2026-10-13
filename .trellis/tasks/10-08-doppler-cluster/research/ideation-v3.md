# Ideation v3 — Trans-level candidates (2026-10-08, main session, first principles)

Inputs: res-20261008-01/02, M2 (order within class ~0 at N=1024; class matters ~3 dB), lit (Ma-Giannakis 2003 LTV
diversity; Zemen 2005 DPSS-BEM; Benzine-Bemani 2025 AFDM DPSS-BEM; SP-OTFS power papers). Borrowed lenses:
ccf-idea-optimizer (problem -> root challenge -> insight -> mechanism -> falsifiable test; closest-overlap check),
scientific-brainstorming (challenge shared assumptions; look for non-monotone phenomena).

## Shared assumption challenged
SP-AFDM literature (and this project) treats channel estimation as "accuracy" problem. First principles: SP receiver must
BOOTSTRAP — first estimate is pilot-only with data as self-interference. Whether the turbo loop starts depends on channel
DoF K, not on final accuracy.

## C1 (TOP) Bootstrapping limit of SP-AFDM in rich doubly-dispersive channels  [problem + theory]
Derivation: pilot-only LS/LMMSE of K coefficients, error/sample eps ~ K (sigma^2 + (1-rho) E_h)/(rho N).
First-pass data SINR = (1-rho)/(sigma^2 + eps). Loop starts iff SINR > gamma_th (decoder/EXIT tunnel threshold) =>
  K* ~ rho N [ (1-rho)/gamma_th - sigma^2 ] / (sigma^2 + 1 - rho).
N1024, rho .5, 8 dB: K* ~ 200 coeffs (~25 diffuse taps x 8); N256: ~50 (~6 diffuse taps). Rich channels sit at K*.
Phenomenon: channel richness double-edged — DoF K raises harvestable diversity (F3) but beyond K* SP loop cannot start.
Predictions (falsifiable): P1 SP-receiver FER vs K at fixed SNR is U-shaped; true-H FER monotone decreasing.
P2 K* proportional to rho N (sweep N in {256,512,1024}, rho in {.3,.5}). P3 prior shaping (Slepian/Wiener) replaces K by
effective DoF K_eff = sum gamma/(1+gamma) and shifts K* outward — the regime where order/prior DOES matter (explains M2
S4 null at K << K*). Method consequence: order-progressive bootstrapping (start low-DoF, expand as reliability grows),
schedule derived from the EXIT-type fixed point.
Closest-overlap risk: EXIT/convergence analyses of iterative SP / superimposed-training receivers (OFDM, block fading);
DoF-threshold framing for doubly-dispersive AFDM likely new — CHECK.

## C2 AFDM diversity under general (diffuse) doubly-dispersive channels  [theory]
Claim: with ML / full-diversity c1, AFDM diversity = channel LTV DoF (sum_l rank R_l), not path count P; discrete-path
full-diversity theorems are a special case; F3 evidence (4 Jakes taps ~ 16 paths). Pairs with C1 (diversity side of the
trade-off). Risk: Ma-Giannakis general LTV max-diversity; AFDM fractional-Doppler diversity papers — CHECK.

## C3 Pilot-overhead scaling law for coherent AFDM under fractional Doppler  [theory, high risk]
Minimum pilot energy/chips vs spread; SP vs EP vs DDST achievability; ties to noncoherent capacity of underspread channels
(Durisi et al.). Risk: crowded/heavy — CHECK only if C1/C2 collapse.

## C4 Communication-centric scattering-function estimation with SP-AFDM  [new application, off-core]
Parked.

## Decisive test for C1 (after lit check)
Clustered/diffuse generator, number of taps L in {2,4,8,12,16,24} x Jakes, N in {256,512,1024}, rho in {.3,.5}, fixed SNR;
arms: true-H, SP full-band DPSS (flat prior), SP Slepian prior, SP order-progressive. Measure FER vs K and first-pass SINR.
Kill: no U-shape / no K* scaling with rho N.
