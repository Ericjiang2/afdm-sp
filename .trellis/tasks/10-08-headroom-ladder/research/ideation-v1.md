# Ideation v1: elevating the paper's innovation level (2026-10-08, main session)

User direction: rho tuning = engineering detail. Rank: new problem > new model > new method > combination.
Lenses used: first principles (what physics is actually in the channel), critical thinking (which assumption is shared
by the project AND the AFDM literature), CCF-idea-optimizer (problem -> root challenge -> insight -> mechanism -> falsifiable test).

## Shared hidden assumption found
Project channel is underwater acoustic (afdm_env.py: fc 12 kHz, B 4 kHz, c 1500 m/s, per-path Doppler SCALE a_i = v_i/c).
B/fc = 1/3 (extremely wideband). Generator keeps only the narrowband shift D_i = a_i fc/fs (afdm_env.py:516-550);
the baseband time compression x((1+a_i)t - tau_i) is dropped in G0 and G1. Classical narrowband-validity condition
(radar/sonar wideband ambiguity, Kelly-Wishner / Van Trees): (v/c)·B·T << 1. Here a·N = (v/c)·B·T ~ 1.3e-3 x 1024 ~ 1.36 > 1.

## T4 (first principles): wideband Doppler in AFDM
Path baseband: r_i(t) = h_i e^{j2pi fc a_i t} x_bl((1+a_i)t - tau_i), x_bl = band-limited (DAC) interpolation of the AFDM samples.
Discrete: time-varying delay l_i(n) = l_i - a_i n (drift a_i N samples per frame) + narrowband shift nu_i = a_i fc T.
- Band-limited AFDM chirp has sawtooth instantaneous frequency f(n) = (2 c1 n + m/N) mod 1. A delay d shifts it by 2 c1 d
  cycles/sample = 2Nc1·d DAFT bins (standard AFDM delay mapping). Time-varying delay a n -> DAFT location drifts by
  2Nc1·a·n: each path smeared over S = 2Nc1·aN bins, plus frequency scaling (1+a) (+-aN/2 bins, as in OFDM ICI).
- Narrowband full-diversity design: 2Nc1 ~ 2 alpha_max + 1, alpha_max ~ a fc T = aN fc/B. Then
  S ~ (2 aN fc/B + 1)·aN, and S / (delay-slot width 2Nc1) ~ aN  -> independent of c1 to leading order.
  => AFDM delay-Doppler separability under wideband Doppler requires a·N < 1; choice of c1 cannot fix it.
  UWA production: aN ~ 1.36 -> S ~ 12 bins > slot 9 -> paths leak into neighbouring delay slots (looks exactly like
  "missed delay / same-delay multiplicity" errors). OFDM sees the same physics only as +-aN/2 ~ 0.68-bin ICI.
- Model-mismatch energy of best narrowband fit (frequency-dependent Doppler residual eps(k) = a·k, k in +-N/2 bins):
  eta ~ (pi^2/3) E[eps^2] = pi^2 (aN)^2 / 36 = 0.51 for aN = 1.36 (critically sampled; -3 dB!).
  After standard common resampling by mean scale a_bar: eta ~ pi^2 N^2/36 · sum_i |h_i|^2 (a_i - a_bar)^2.
  e.g. residual (Delta a) N ~ 0.34 -> eta ~ 0.032 (-15 dB) ~ 0.5-0.7 dB loss at 6.5 dB SNR.
- Compare: local CRB loss K_r/(2N) ~ 1% (T1). Wideband residual dominates by 3x-50x.
- Why SP matters here: embedded-pilot AFDM needs guard bins >= spread; wideband spread S multiplies guard overhead by
  ~aN. SP has no guard, its pilot energy spans the whole frame (drift is observable via the long window: Fisher info for
  scale ~ N^3 like frequency). SP is the natural pilot for wideband AFDM.

## Candidate cards (parent / operation / contribution type)

C1 (BEST) Wideband-Doppler SP-AFDM. parent: project + UWA physics; op: invert (challenge narrowband assumption).
  Type: new problem + new model (+ method). Problem: AFDM's delay-Doppler separability and diversity analysis assume
  narrowband Doppler; in wideband (UWA) channels the 2Nc1 delay mapping turns per-path time compression into
  DAFT-domain smearing of aN delay slots. Model: DAFT-domain I/O with per-path (l, nu, a); first-order scale atom
  (d/da of x((1+a)t) = t x'(t)) or exact resampling operator. Method: SP-based joint (l, nu, a) estimation inside
  the existing turbo receiver (scale atom = one extra real per path; resampling-based TF). Theory: separability
  criterion aN<1 (c1-independent), mismatch energy formula, pilot-guard argument for SP.
  Falsifiable now: production B on a wideband channel G2 (same h, l, nu, plus true time compression) vs G1.
  Prediction: raw G2 -> collapse; with oracle common resampling -> loss ~0.3-1 dB growing with velocity spread;
  scale-aware oracle (true a_i in model) recovers it.
  Closest-overlap risk: UWA OFDM/OTFS MSML literature (resampling, multi-resampling); AFDM-UWA papers may already use
  scale models -> lit check running. Narrowband criterion itself is classical (claim AFDM-specific consequences only).

C2 (fallback, structurally different) Order-free per-delay-tap model. op: transfer (OFDM DPSS-BEM, Zemen 2005) +
  instrument. Type: new model/method. Measured failure: same-delay multiplicity underfit (AUC .64-.77) and B's error
  floor removed by genie delays+multiplicity (A1). Represent each delay tap's time variation in a Slepian subspace of
  dim D ~ 2 nu_max + few (no path count, no Doppler resolution needed). Cost: D·L_active params -> variance ~K_r/2N
  ~ 0.25 dB; gain: removes order-selection failures. Hybrid: parametric for resolved paths, subspace for unresolved
  clusters, switched by a resolvability statistic. Note: DPSS subspace also absorbs wideband residual (scale drift
  within a tap is band-limited) -> C2 is also a robust answer to C1's residual. Novelty: BEM in OFDM/OTFS known; AFDM+SP
  hybrid with resolvability switch = combination-level unless tied to C1.

C3 (supporting theory) Acquisition-decoding fixed point of SP turbo receivers (bistability -> outage/error floor).
  Population-level rho law confirmed, per-frame threshold predictor failed (P3) -> weak as main contribution.

C4 (dropped) rho*(N, PDP) scaling law: engineering detail per user.
C5 (dropped) local-uncertainty VB / pair covariance: measured <= .13 dB.

## Coherence / critical check of C1
- Is UWA the intended application? Code says yes (UWA generator, fc/B/c). Paper framing must say so.
- Does the effect survive standard practice (front-end resampling)? Residual non-uniform scale is the known hard UWA
  problem; magnitude depends on velocity spread v_std -> must use the generator's own v distribution, and sweep it.
- Is the gain from modelling real, not from a straw-man? Baselines: (i) narrowband B on G2 without resampling,
  (ii) with oracle/estimated common resampling (standard), (iii) scale-aware (proposed), (iv) PCSI wideband.
- One central insight: "AFDM converts Doppler scaling into DAFT-domain delay-slot leakage of aN slots, independent of c1;
  superimposed pilots are what make the scale observable without guard overhead."
Next: wait for constants (exact v distribution, fs/T) + literature; then falsification run on G2.
