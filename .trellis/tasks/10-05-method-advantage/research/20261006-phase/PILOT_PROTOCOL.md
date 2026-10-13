# Frozen bounded pilot: useful classical CFO adaptation

Date: 2026-10-06. Scientific status: exploratory development pilot, not CONF, not production promotion. Source implementation and independent admission remain prerequisites. User explicitly requests continued exploration, permits useful OFDM adaptations and SSH for numerical work.

## Question and model

Can a Y-only classical three-evaluation fractional-CFO update replace a 64-point search in a specified AFDM estimator, and can a fourth-power CAZAC chirp improve integer-CFO resolution over the current small c2?

Use the complete, untruncated, single-path zero-delay model Y_n=h exp(2πiνn/N)[R F^H C S]_n+noise_n. F is unitary negative-exponent DFT, R_nn=exp(-2πi c1 n²), C_ss=exp(-2πi c2 s²), c1=2.5/N. h=exp(iφ), unknown to every estimator. S iid unit-power exp(iπ/4) C4, σ²=10^(-SNR/10); no oracle normalization. This is an explicit restricted physical use case. Existing narrow Doppler priors would remove most integer aliases and must not be replaced silently in production.

## Fixed design and exact budget

- One RNG seed 20261006, NumPy default_rng; N in [16,64], T in [1,4], SNR dB in [10,20], 128 independent trial groups per cell. Eight cells, 1024 paired groups.
- For each group, integer r uniform over [-N/2,N/2), fractional δ uniform over [-0.5,0.5), φ uniform [0,2π); ν=r+δ interpreted modulo N. Save all exogenous S, standard complex noise, r, δ, φ, and each resulting Y.
- Three waveforms per group: c2=0; current c2=1/(10N²); designed c2=1/(8N) (both N values even). Same S, h, ν, standard noise for all waveforms.
- 3072 waveform/trial datasets and 7680 new N-vector observations (sum over T); also report complex scalar count 307200. No new geometry probes. One worker, one thread, CPU only. Wall cap 300 seconds, peak RSS cap 2 GiB, total output cap 256 MiB. No retry sampling or tuning within this allocation.
- Timing is exploratory same-process paired elapsed time, not a hardware-general speedup claim. Include complete estimator work; separately count FFTs and objective evaluations. Interpreter startup is separate.

## Estimators and fairness

All estimators receive only Y, known R/C, and N/T. Dechirp z=R^H Y. Evaluate J(a)=mean_t sum_s |F D(-a) z_t|^4 at a=0,1/3,2/3. Recover the exact single harmonic with a three-point DFT and minimize analytically on [0,1). Declare flat/near-flat when harmonic magnitude <= 1e-12 times max(1,mean absolute J); record flag, select a=0 deterministically without pretending identification.

At chosen a, compute X=F D(-a)z, m_s=mean_t X_st^4, and all score_r=|sum_s m_s conjugate(w_(s-r))| with w_s=C_ss^4. FFT circular correlation is allowed. Select smallest index among maxima, record near tie (within 1e-10 times max score, or exact all zero). Return νhat=a+rhat modulo N. c2=0 produces tied integer scores; retain all its errors and flag lack of identification, never discard.

Comparison A: three-evaluation analytic versus exactly the same estimator with a=0,1/64,...,63/64 minimizing J; current c2 only. Charge final X and integer correlation to both. Every dataset shared, no truth to either estimator.

Comparison B: analytic two-stage estimator across all three waveforms. Costs include fractional and integer stages. Changing c2 is a waveform design intervention, not an unchanged-waveform algorithm improvement.

## Metrics and decision rules

Store per group all estimates, flags, objective minima, elapsed times and counts. Fractional error is signed modulo-one error in [-.5,.5); full CFO error is signed modulo-N error in [-N/2,N/2). Catastrophic error iff absolute full error >0.5. Report each cell's count, catastrophe proportion, full and fractional RMSE; retain every trial and tie.

Primary design question: paired catastrophe reduction (current minus designed) in each cell, equal-weight average across cells, and a paired normal 95% interval on the average using independent groups within fixed cells (sum cell variances / (8²*128)); report exploratory normal approximation, no confirmatory p-value. Useful pilot signal requires mean reduction >=0.10 and interval lower bound >0. If not, do not tune/post-select; report no demonstrated design benefit in this pilot.

Primary computation question: analytic J <= grid J to relative 1e-9 for every group; >=10x reduction in objective evaluations (64/3), plus report actual total estimator elapsed ratio and estimation errors. Do not claim accuracy dominance from objective dominance. This can independently establish a bounded computation benefit, with explicit grid-baseline limitation.

Secondary noiseless algebra fixtures belong to local contract tests only (small fixed arrays), not new scientific datasets or finite-sample evidence. Main pilot contains no additional noiseless sweeps.

## Integrity / failure

Reuse existing immutable source-bound recorder and effective thread check. Config SHA256 and all executed project Python bytes must be committed before run; independent admission precedes source commit and isolated SSH snapshot. All remote writes under /data/guoyikun including TMP/cache; conda AFDM; tmux g_*. Keep failed attempts/reservations and immutable raw hashes. Any algebra mismatch, invalid input, source/config change, count/resource violation or nonfinite estimate fails visibly; no clipping, retry, dropped failures or best-seed selection. No code run is authorized by mere writing of this protocol before admission.
