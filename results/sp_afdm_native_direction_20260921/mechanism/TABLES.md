| Scope | Value |
|---|---|
| Source | Frozen direction validation, receiver2d130b4d; N=1024,P=8,P/N=0.0078125 |
| Full vector diagnostics | Existing frame0 at6/6.5/7dB; TF/POINT;2 rounds×20 iterations=240 rows |
| Paired scalar diagnostics | Existing first8 per SNR;2 arms×2 rounds×20=1920 rows |
| New Monte Carlo / receiver calls | 0 / 0 |
| Time convention | CSV iterations0–19 per round; figures1–40 concatenate two rounds. Pre-update variance/state quantities; current vq; post-update gain movement. |
| Aggregation | Medians below pool the2 coded rounds for one audit frame per SNR. Descriptive iteration summaries, not independent-sample statistics. |
| Phases | Initial: inner t=0 in each round; early:t=1–4; late:t=5–19. Late is a descriptive window, not a claim of convergence. |
| Scalar convention | Original scalar CSV gain_variance/data_variance are post-update; they are not mislabeled as pre-update. |

| SNR dB | Method | Late N vh_post | Late output correction % | Late actual reaction % | Early gain movement % | Late gain movement % |
|---:|---|---:|---:|---:|---:|---:|
| 6 | TF | 0.7102 | 1.204 | 0.824 | 16.413 | 0.735 |
| 6 | POINT | 0.0000 | 0.000 | 0.000 | 4.162 | 0.233 |
| 6.5 | TF | 0.6400 | 1.178 | 0.767 | 8.664 | 0.830 |
| 6.5 | POINT | 0.0000 | 0.000 | 0.000 | 4.545 | 0.357 |
| 7 | TF | 0.5670 | 1.185 | 0.756 | 6.073 | 0.576 |
| 7 | POINT | 0.0000 | 0.000 | 0.000 | 4.162 | 0.419 |

| SNR dB | TF initial vh_pre | Initial output correction % | Initial reaction % | Late correction / (P/N) | Late reaction / (P/N) |
|---:|---:|---:|---:|---:|---:|
| 6 | 0.125 | 226.77 | 112.37 | 1.541 | 1.055 |
| 6.5 | 0.125 | 283.58 | 143.31 | 1.508 | 0.982 |
| 7 | 0.125 | 387.77 | 168.06 | 1.517 | 0.968 |

| Scaling / mechanism question | Saved-state finding | Limit |
|---|---|---|
| vh=O(1/N) | Post-transient posterior N vh medians0.567–0.710; exact relation N vh=1/(sv xb_power+P/N) agrees to8.88e−16. Consistent with1/N posterior scaling if sv and xb_power remain order-one. | FixedN=1024 only; no empirical asymptotic order or exponent estimate. |
| Variance effects O(P/N) | Late relative output correction≈1.18–1.20%, reaction≈0.76–0.82%; coefficients after division byP/N are≈1.51–1.54 and≈0.97–1.06. Consistent at the observed operating point. | Initialization violates a uniform small-effect interpretation: vh_pre=1/P and relative effects are order-one. Earlier iterations also have larger coefficients. |
| Gain-mean updates remain first-order | Early movement is6.07–16.41% for TF and4.16–4.55% for POINT, despite POINT propagating vh=0. Thus mean adaptation remains substantial without gain-variance propagation. | Net movement decays to0.58–0.83% for TF and0.23–0.42% for POINT in the late window. First-order large-N scaling cannot be identified from oneN; it does not mean movement dominates variance terms at every iteration. |
| Full propagation versus POINT | POINT retains joint gain-mean adaptation and gain pseudo-variance/shrinkage, but propagated vh and both explicit gain-variance diagnostics are exactly0. Full propagation has a large startup perturbation followed by small corrections. | TF here propagates a scalar gain variance; it is not a full gain covariance matrix or a new full-Gamma experiment. |
| Consistency checks | Saved trace vq,sv,channel norm,post-vx/post-vh,bar/vp match reconstruction exactly; posterior scaling identity residual≤8.88e−16. | Algebraic replay consistency is not independent evidence of asymptotic scaling or unchanged statistical performance. |
