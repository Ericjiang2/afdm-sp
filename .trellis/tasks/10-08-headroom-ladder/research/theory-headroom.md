# Theory: where SP-AFDM coded headroom can live (2026-10-08, main session)

Status: derivation sketch, order-of-magnitude; predictions below are to be falsified by E-rho / E-ladder.
Model: y = sum_i h_i A_i (p + d) + w, E|p_n|^2 = rho, E|d_n|^2 = 1-rho, sum E|h_i|^2 = 1,
sigma^2 = 10^(-SNR/10), N = 1024. A_i = delay l_i, continuous Doppler nu_i (CPP physical operator, G1).

## T1. Local (CRB-regime) estimation loss is ~K_r/(2N)

Single path, gain refit as nuisance, D(nu) = diag(exp(i t_n nu)), t_n = 2 pi n/N, Var(t) = pi^2/3:

    J_nu = (2|h|^2|x|^2/sigma^2) N pi^2/3      =>  E[delta^2] >= 3 sigma^2 / (2 pi^2 |h|^2 |x|^2 N)
    residual power / sample = |h|^2 |x|^2 Var(t) E[delta^2] >= sigma^2/(2N)

Each real parameter in CRB regime costs sigma^2/(2N). Total: Loss_local ~= 10 log10(1 + K_r/(2N)).
P = 8, K_r = 24 -> 0.05 dB (data-aided, x fully known). Uncertainty-aware detection gain <= Loss_local.
Using Codex's measured curvature kappa ~ 8e3..2.36e4 (UNCERTAINTY_VALUE_BOUND.md) -> Doppler part ~0.01 dB.
Consistent with: continuous-VB ~= point; quadrature failures from over-concentrated posterior;
S7: true H adds only +1/32 rescue over true geometry (gains not the bottleneck).
Not covered: unresolved same-delay pairs (near-singular Fisher), multimodal / missed paths.

## T2. Missed geometry energy explains the observed gap order

Unmodeled path energy E_miss carries pilot + data -> interference E_miss after pilot cancellation:

    SINR_data ~= (1-rho)(1-E_miss) / (sigma^2 + E_miss)

6.5 dB (sigma^2 = .224), E_miss = .04 (S7 median working-geometry projection residual 4.08%):
loss = 10 log10((.224+.04)/.224) + 10 log10(1/.96) ~= 0.71 + 0.18 = 0.9 dB  ~ E1-order gap.
=> geometry acquisition (missed delays / undercounted same-delay multiplicity) is the first-order term.

## T3. Pilot fraction rho: exact data-power term vs acquisition threshold

PCSI curve shift is exact (same code, Gaussian-ish detector):  dSNR_PCSI(rho1->rho2) = 10 log10((1-rho1)/(1-rho2)).
.5 -> .3: 1.46 dB; .5 -> .2: 2.04 dB.  This is the upside ceiling of lowering rho.

Pass-1 pilot-only acquisition of path i at its true cell: detection SNR

    gamma_i = rho N |h_i|^2 / (sigma^2 + (1-rho))        (data of all paths = interference)

Detect iff gamma_i >~ ln(M/eps), M ~ number of delay-Doppler cells x candidates (~1e4..1e6) -> ln ~ 12..16.
6.5 dB: rho=.5 -> |h_i|^2_min ~ .019; rho=.3 -> ~.041; rho=.2 -> ~.069.
Weak-path mass below |h|^2_min -> E_miss(rho) (PDP-dependent, frame-random).

Data-aided recovery: after a decoder pass with reliability I in [0,1], effective known energy
rho + (1-rho) I, interference (1-rho)(1-I):

    gamma_i(I) = (rho + (1-rho) I) N |h_i|^2 / (sigma^2 + (1-rho)(1-I))
    I_next = Dec( SINR(E_miss(gamma(I))) )

=> two-map fixed point (acquisition <-> decoding), EXIT-like. Frame fails when tunnel closes:
pass-1 E_miss too large -> SINR below decoder threshold -> I stays ~0 -> no data-aided rescue.
Triggered re-acquisition (CSTATE, syndrome>0) = second attempt at higher effective I; matches
S5 34/40 rescues.

Predictions (falsifiable):
P1. Deployed coded FER vs rho at fixed SNR is non-monotone; interior optimum rho* < .5
    (uncoded evidence: S9 classical errors 14371 @.25, 14081 @.375, 27259 @.5 at SNR15).
P2. PCSI shift across rho matches 10 log10((1-rho1)/(1-rho2)) within ~0.1 dB.
P3. Deployed-to-PCSI gap grows as rho decreases; failure frames enriched in pass-1 undetectable
    mass E_miss(rho) computed from truth PDP (logistic AUC well above .5).
P4. rho* scales ~ ln(M) / (N * typical weak-path power); shrinks with N, grows with PDP weak tail.
P5. Same-delay multiplicity (|dnu| < ~1 bin) adds a resolution-limited term (separation scale
    ~ R^-1/4, cf. Codex collision study res-20261005) not removable by more pilot power at fixed N.

Candidate contribution (if P1-P3 hold): acquisition-decoding fixed-point analysis for SP-AFDM
under continuous fractional Doppler -> rho* law + triggered data-aided re-acquisition at
controlled cost. Novelty to be checked (EXIT analysis of iterative channel estimation exists in
OFDM/CDMA literature; SP power allocation exists for OFDM/OTFS) -> claim modestly.
