# Design (staged)

## Evidence base
F1 (a5e51ad0): B collapses on clustered channels. F2 (58c393bb): PS (keep_slots, cap 8) gap @1e-1 N4b .62 / J4 3.41 dB;
free-frequency oracle needs ~2/3/3-4 exponentials per tap; P_eff MC predicted 2.0/2.7/3.6 (theory-peff.md).
1-bin lattice oracle uninformative (Fourier leakage).

## Method hypothesis M
Per active delay tap l: estimate a_l[n] in a band-limited subspace: modulated DPSS e^{j2pi c_l n/N} v_d[n], d < D_l,
half-bandwidth W_l (bins) around centre c_l. Centre/band from the DAFT window energy of tap l (AFDM puts tap l's Doppler
spectrum in window 2Nc1·l); D_l from P_eff rule (#eigen-components with frame SNR > 1) or MDL. Linear LS / LMMSE for the
coefficients given soft data (SP turbo, data-aided). No per-ray Doppler search; conditioning bounded.
Claimed advantage to test: near true-H (OF3-level) at <= PS cost; beats PS (cap 8) and PS-bigcap (cap 16) at equal cost.

## Stage M1 (now): prerequisites, oracle only
1. Detector interface: can scalar_joint / TimePathOps / interventions.run_fixed_channel accept general per-tap time-varying
   gains? If not: represent a band-limited tap exactly enough by a dense in-band exponential set (0.25-bin grid inside
   [c-W, c+W]) with LS/ridge gains (span ~ DPSS); check operator error and detector cost vs P.
2. DPSS oracle ladder: project true taps onto D-dim modulated DPSS around true power-weighted centroid with W = true
   half-spread + 0.5 bin; D in {1,2,3,4,6}; fixed-H TF detection. Predicted (Landau-Pollak + rays): N4a 2, N4b 3-4, J4 5-6.
   Configs N4a, N4b, J4, (D1 sanity, D=1 must equal A3 up to the W>0 basis). 600 frames, SNR 6-11.
3. Feasibility of PS-bigcap: what to change in a COPY of f1.py/keep_slots.py to raise the 8-slot cap to 16.

## Stage M2 (after M1): estimated method M vs B, PS, PS-bigcap, Benzine-style grid-centred DPSS-BEM (SP-adapted), true H.
Coded FER + complete per-frame cost; configs D1/N4a/N4b/J4 (+ lambda 8 Jakes); 1000 frames.

## M1 outcome (8aaa935d)
TF detector accepts arbitrary per-sample taps (TapChannel, runtime TimePathOps subclass; frozen untouched; P-independent
cost). DPSS oracle saturation D = 1/3/4/8 (D1/N4a/N4b/J4) at W = max ray offset + .5; free exponentials 1/2/3/3-4.
PS cap 16 needs a stopping rule (count-blind fill); only a pure cap-16 bound is run.

## Stage M2: estimated method (pre-registered before any M2 result)
Core: scalar_joint joint gain/data estimation with DPSS columns as "paths" (TapChannel-style modulations
v_d[n] e^{j2pi c n/N}, rescaled to norm sqrt(N)) and per-column prior variance ~ tap power x Slepian eigenvalue lambda_d
(Wiener shrinkage gamma/(1+gamma) = soft P_eff rule). Delays from production pilot_front acquisition (distinct delays);
taps with negligible estimated energy dropped. Turbo: 2 coded rounds like B (TF20, LDPC 50); no CSTATE.
Arms:
- B (production), PS (cap 8, as F2), A3 (true H).
- M_full: every acquired tap uses full-band DPSS, centre 0, W = nu_max + .5 = 2.5 bins, D = 8 (Zemen-style BEM baseline).
- M_adapt: per tap centre c_l and half-band W_l estimated from the data (pilot / data-aided Doppler energy profile of that
  delay after round 1; round 1 uses M_full), D_l = ceil(2 W_l) + 2, Slepian prior with estimated tap SNR.
- PB16 bound: PS copy with cap 16, no stopping rule; N4b, J4 x SNR {7, 9, 11} only.
Configs D1, N4a, N4b, J4, J8 (lambda 8 Jakes); SNR 6..11; test frames 0..999 (paired with F1/F2/M1).
Any design choice (band threshold, prior scaling) tuned ONLY on dev frames 1000..1199, then frozen before test run.
Pre-registered success:
 S1 M_adapt within .3 dB of A3 @1e-1 on N4b and J4; S2 M_adapt no worse than B by > .1 dB @1e-1 on D1;
 S3 M_adapt beats PS by >= .3 dB @1e-1 on N4b and J4 at <= PS mean cost;
 S4 (adaptivity) M_adapt beats M_full by >= .1 dB on D1 or N4a; else adaptivity claim dropped (method = SP-AFDM DPSS-BEM
    with Slepian prior, combination-level).
