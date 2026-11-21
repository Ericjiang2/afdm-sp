# Information-budget screen: is there algorithmic headroom above the practical SP-AFDM load cliff? (FROZEN 2026-10-14)

Active task: `.trellis/tasks/10-08-doppler-cluster`. Status: **FROZEN** in the commit that adds the Codex confirm-3 record (READY-TO-FREEZE). Opus and Codex converged on every row of §8 (independent derivation, convergence round, skill-based adversarial check, three confirmations). No code or number exists yet. Process (user, 2026-10-14): Opus derives
and drafts the rule; Codex (gpt-6.1-sol, xhigh) derives independently without reading this file
(`codex-info-budget-independent-20261014.md`); every divergence is resolved and recorded in §8 before freezing; only then
code (Sonnet), a single core code review (Codex), the run, and the decision (Opus). Context: M2 in
`mainline-first-principles-20261014.md`.

## 1. Object

Same system as C1: N = 1024, SP with pilot energy rho and QPSK data a = 1 - rho on all N symbols, sigma2 = 10^(-SNR/10),
LDPC (3,6) n = 2048 (one frame, rate 1/2). Time domain after IDAFT (unitary):

    Y = sum_l D_l(s) a_l + w,   D_l(s) = diag(cp_l ⊙ S_l s),   s = pt + xt,   w ~ CN(0, sigma2 I).

a_l in C^N is the tap-l gain sequence. Question: what load can an ideal receiver of the same transmitted signal support,
measured by a quantity that is provably below I(d; y)?

## 2. Lower bound (per frame, bits)

Exact identity (chain rule on I(d, a; y)):  I(d;y) = I(d;y|a) - I(a;y|d) + I(a;y).

- (T1) coherent term, lower-bounded: I(d;y|a) >= sum_m I(d_m; y|a) (independent symbols) >= sum_m I(d_m; z_m), z_m the
  LMMSE estimate of d_m from y with a known (data processing). Evaluated as 2 C_BPSK(gamma_m) with
  gamma_m = a / MMSE_m - 1, MMSE_m = a [(I + (a/sigma2) H^H H)^(-1)]_mm, H the DAFT-domain data channel of the frame.
  **Superseded:** the Gaussian-residual evaluation is not a bound for QPSK. Primary T1 = A(h), the ZF-SIC/QR bound of
  §2.1 (X4); the LMMSE-output GMI is report-only and its empirical estimate carries no bound guarantee.
- (T2) learning cost, exact for a Gaussian law: I(a;y|d) = log2 det(I_N + C_s / sigma2), C_s = sum_l D_l(s) R_l D_l(s)^H.
  For a non-Gaussian law with the same covariance, the Gaussian value is an upper bound (Gaussian input maximises
  I(a; y | d) for a fixed covariance), so subtracting it keeps a lower bound.
- (T3) channel information without the data, lower-bounded by the pilot-only LMMSE estimate â = W y:
  write the stacked taps as a = B g, g ~ CN(0, I_r) (r = rank of the stacked covariance; no full-space entropy is used).
  I(a;y) = I(g;y) >= I(g;ĝ) >= h(g) - h(g - ĝ) >= -log2 det C_e = log2 det(Q + C_p) - log2 det Q = J,
  C_e = (I_r + F^H Q^-1 F)^-1 the LMMSE error covariance of g, F the pilot regressor of g, C_p = F F^H = sum_l D_l(pt) R_l D_l(pt)^H,
  C_int = E[sum_l D_l(xt) R_l D_l(xt)^H] (data interference; uncorrelated with a because E xt = 0). Needs h(g) to be the
  Gaussian entropy of the support coordinates g ~ CN(0, I_r), i.e. **valid for a Gaussian channel law only** (for a
  non-Gaussian law h(g) is smaller and T3 can overstate). Therefore the whole bound is stated for a Gaussian channel law with the chosen covariance.

Per-frame score (not itself a bound): l(D, h, d) = A(h) - f(d) + J(D), f(d) = log2 det(I + C_s(d)/sigma2), J(D) the T3
value for the frame's delay set D. **Only the expectation is the bound:** E[l] <= I(d; y | D) averaged over D (C1 draws D
per frame; every term is computed conditional on the frame's D). Frames (D, h, d, w) are i.i.d.

### 2.1 Self red-team (proof-checker ledger + counterexample pass, Opus, before seeing Codex)

| ID | Step | Condition needed | Status | Fix (applied below unless noted) |
|---|---|---|---|---|
| P1 | identity in §2 | finite MI | OK | — |
| P2 | T1 sum over symbols | d_m mutually independent: i.i.d. uniform QPSK = random-coding ensemble, not the LDPC codebook | OK, scope | state scope |
| P3 | T1 Gaussian-residual evaluation | none available for QPSK | **UNJUSTIFIED (MAJOR)** | replaced: primary T1 = ZF-SIC/QR bound A(h); LMMSE-output GMI report-only (X4) |
| P4 | T3 `log det R - log det E` | R invertible; the J0 Toeplitz covariance is numerically rank-deficient | UNCLEAR (MINOR) | write the stacked taps as h = B g, g ~ CN(0, I_r) on the support; entropy arguments on g; result = identity form, computed as log2 det(Q + C_p) - log2 det Q (Hermitian; Cholesky-safe) |
| P5 | whole bound | delays known; PHYS also needs the covariance known | HIDDEN ASSUMPTION | bound is conditional on the delay set (as the genie-delay receiver) and on R_l |
| P6 | T2 at high SNR | — | looseness: sigma2 -> 0 gives T2 -> inf while I(d;y) <= 2N stays finite (equality would need zero-noise identifiability, not shown) | intrinsic looseness (learning charged to noise precision); handled by the UNINFORMATIVE branch; 9.5 dB report-only |
| P7 | §4 threshold | code gap transfers to this channel | assumption, not a bound | kept as stated; R_eff = 1.0 reported |

**T1, corrected (P3), then revised after convergence (X4, X7): primary T1 = ZF-SIC/QR bound.** For the frame channel G_h
(DAFT-domain data channel) take a QR factorisation G_h Pi = V R with a column ordering Pi chosen from h only (e.g. pivoted
QR). Chain rule in that order, keeping only row i of V^H y after cancelling the already-conditioned symbols:
I(d;y|h) >= A(h) = sum_i J_QPSK(a |R_ii|^2 / sigma2) (expand the chain rule in reverse order i = N, ..., 1, conditioning on and
cancelling d_j for j > i; zero diagonal entries are allowed and contribute 0), J_QPSK the exact 4-point AWGN MI. Deterministic given h, range [0, 2N].
The LMMSE-output GMI below is **report-only** (selection bias if maxed per frame; samples unbounded below).
Former text (kept for the record): Per frame simulate y with the drawn channel, compute the LMMSE output z_m = w_m^H (y - H_p) with
bias mu_m = w_m^H h_m and residual variance v_m = E|z_m - mu_m d_m|^2 (closed form from H). With the Gaussian metric
q(d, z) = exp(-|z - mu_m d|^2 / v_m), the generalized mutual information at s = 1,
GMI_m = E[ log2( q(d_m, z_m) / ((1/4) sum_{d'} q(d', z_m)) ) ],
is <= I(d_m; z_m) as a population quantity; its empirical estimate carries no lower-bound guarantee. REPORT-ONLY.

### 2.2 Formal statement and two-pass check (methods borrowed from math-adversarial-proof-search and Rethlas)

**Proposition.** Fix N, the pilot p, the delay set {l} and per-tap covariances {R_l}. Let a_l ~ CN(0, R_l) be independent
across taps, d i.i.d. uniform QPSK with E|d_m|^2 = a, w ~ CN(0, sigma2 I), with a, d, w mutually independent. Then
E[T1 - T2 + T3] <= I(d; y), with T1 = A(h) the ZF-SIC/QR bound (§2.1, X4), T2 = E_d log2 det(I + C_s/sigma2),
T3 = log2 det(I + Q^-1 C_p), Q = C_int + sigma2 I. Nothing is claimed for non-Gaussian channel laws, unknown delays or an
unknown R_l, or for the LDPC codebook as input law.

Structure pass (roles simulated in the main session, not separate agents):
- The proposition is exactly what §4 uses (mean over frames -> K*). Every stated assumption is used: tap independence
  (block-diagonal R, C_int diagonal), known delays and R_l (LMMSE in T3), i.i.d. d (T1 sum; white xt so C_int = a diag).
- Logical order: identity -> three one-sided steps (T1 down, T2 exact for the Gaussian law, T3 down); no circularity.

Detail pass:
- Complex Gaussian MI carries no 1/2; log2 for bits. T3 is derived on the support coordinates g (I_r prior, so
  h(g) = r log2(pi e) and no singular log det appears); -log2 det C_e = log2 det(I_r + F^H Q^-1 F) = log2 det(Q + F F^H) -
  log2 det Q by Sylvester. xt = IDAFT(x) is white with variance a (unitary map), so
  C_int = a sum_l diag(R_l[k,k]) = a I for PHYS and = a (1/K) sum_j diag|m_j|^2 for MODEL (not a I; compute exactly).
- Cross terms in Q vanish: E xt = 0 and taps independent.
- Units: all computed in physical units (rho, a, sigma2); never mix with the receiver's internal rho = .5 normalisation.
- Similar-looking quantities kept apart: I* is per coded bit (decoder input); R_eff = 2 I* is per QPSK symbol.

**Gate U4 (toy exact falsification, from Rethlas construct-toy-examples; revised per X12 and the skill check).** The paired
difference Delta = l - log2[p(y|d)/p(y)] is unbounded above (Codex counterexample: N = L = 1, the information density of the
smaller-variance component tends to -inf in the tail), so Monte Carlo + Bonferroni cannot certify coverage. Primary gate:
deterministic quadrature with explicit error bounds for N in {1, 2}, L = 1, flat and rank-1 covariances, SNR in {0, 6.5, 15}
dB, rho in {0, .2, .5}: pass iff E[l] <= I(d; y) - (quadrature error bound) in every case. Codex reference values
(N = L = 1, rho .5, sigma2 = 10, 1, .1): (LB, MI) = (.00142, .00298), (.01812, .08711), (-.67701, .28870); the code must
reproduce them. N = 4 Monte Carlo is report-only. An exceedance stops the screen for investigation.

## 3. Two references (same generator constants as driver_c1)

- MODEL: a_l on the receiver's 8-DPSS basis (W = 2.5) with h ~ CN(0, I/K), K = 8L, i.e. R_l = (1/K) M M^H (M = sqrt(N) DPSS
  columns).
- PHYS: Gaussian with the generator's second-order statistics. Rays nu = 2 cos(theta), theta ~ U[0, 2pi), gain
  variance 1/(L R) summed over R rays: R_l[n, n'] = (1/L) J0(2 pi * 2 (n - n') / N) for every tap, independent across
  taps, independent of the ray count. (Doppler unit "bins" = cycles per frame; Sonnet must verify against
  `draw_c1_paths` before any run.) Limitation: the simulated channel has 1 + Poisson(3) rays per tap, i.e. is not Gaussian; the practical
  cliffs were measured on that channel, not on PHYS.

## 4. Load threshold (converged: X6, X7)

tau = 1 bit per QPSK symbol (code rate 1/2; supports achievability for i.i.d. random coding across independent frames).
K* = the largest load on the frozen L grid such that the lower confidence bound of I_LB/N exceeds tau at that grid point
and at every smaller grid point (no monotonicity assumed). LCB: empirical Bernstein (Maurer-Pontil) on i.i.d. frames, n >= 2, for the three
random terms (A, f, J) separately with proven ranges: A in [0, 2N]; f in [0, B], B = N log2[1 + beta (sqrt(rho) + sqrt(a))^2 / sigma2],
beta = sum_l max_n R_l[n, n] (energy argument; IDAFT output is not constant-modulus). For range b, sample variance S^2 and
risk delta_i: e = sqrt(2 S^2 ln(2/delta_i) / n) + 7 b ln(2/delta_i) / (3 (n - 1)). LCB = mean(A) - e_A - mean(f) - e_f +
mean(J) - e_J (J varies with D; range [0, N log2(1 + beta rho / sigma2)], since J <= log2 det(I + C_p / sigma2)). Fixed total alpha = .05 split over all one-sided endpoints (grid points x
conditions x references x stages), sum delta_i <= alpha. Two stages: 64 frames on the full grid to locate;
512 independent frames on all grid points up to and including the located K* + 1 grid step to confirm (the confirmation
decides). If the locate stage has no passing point, confirm the first two grid points only. K* = the grid point just before the
first confirmed point that fails (if the smallest grid point fails, no K* exists: UNINFORMATIVE for that condition). Right-
censoring (">=") applies only if every point that was actually confirmed passes and the confirmed set does not reach the
end of the frozen grid; K* is then the last confirmed point, a valid conservative endpoint, not the grid maximum.
H_low certifies the numerator only: Kc_best is a fixed historical point estimate. The empirical 2 I* = 1.154 version is a labelled side table only. H includes the code's own gap (I* .577 vs
.5), so it is not pure receiver headroom.

## 5. Practical reference Kc_best (stored, best configuration measured, from out/c1ib2/analysis_stdout.txt)

| condition | Kc_best | config |
|---|---|---|
| 6.5 dB rho .2 | 201.0 | R4/T40 |
| 6.5 dB rho .3 | 213.6 | R10/T40 |
| 8 dB rho .2 | 254.2 | R4/T40 |
| 8 dB rho .3 | 269.3 | R4/T40 |
| 8 dB rho .5 | 222.9 | R4/T40 |
| 9.5 dB rho .3 | >= 320 (censored) | R4/T40, report-only |

## 6. Decision rule (converged: X8, X9, X11)

H_low = K*_LCB / Kc_best per reference, on the 5 uncensored conditions (9.5 dB excluded from any positive claim).
Classification per reference, in this order (fixes the skill-check CRITICAL: (1.30, 1.30, 1.30, 1.15, 1.15) must be WEAK):
1. INFO-HEADROOM: H_low >= 1.25 in >= 4/5 -> "information headroom under the MODEL (resp. PHYS) Gaussian reference":
   licenses prioritising validation of a stronger receiver (M3). No claim that same-code FER gains are proven, no causal
   attribution (algorithm / model / bootstrap).
2. else WEAK: H_low >= 1.10 in >= 4/5 -> small-scale validation only.
3. else UNINFORMATIVE: the bound cannot decide; this does not deny algorithmic headroom.
Labels are given per reference; the two need not agree. Report-only: RAY reference (X10), the 1.154 side table, the rho
maximising K*_LCB per SNR, the 9.5 dB condition.

## 7. Computation plan (zero receiver runs)

L grid {4, 8, ..., 96}; 64 frames per (condition, L, reference) from the C1 generator constants with an own seed domain
(data drawn i.i.d. QPSK; channel drawn from the reference's Gaussian law). Per frame: one N x N Cholesky for T2 (Hermitian I + C_s/sigma2) and two for T3 (Q + C_p and Q),
one pivoted QR for T1. CPU, single-thread jobs, <= 40 concurrent; estimate < 3 core-hours.
Unit checks before scoring: (U1) T2 equals the K x K form log2 det(I_K + A^H A / (K sigma2)) for MODEL to 1e-8;
(U2) A(h) with G_h = identity equals N J_QPSK(a/sigma2) exactly (deterministic); U >= the MC estimate of E[T2] only in
expectation (checked with its confidence interval); (U3) J0 covariance matches the empirical covariance of 10^5 generator
rays within 1e-2; (U4) toy exact gate (§2.2).

## 8. Divergence log with Codex (independent: codex-info-budget-independent-20261014.md; convergence round:
codex-info-budget-convergence-20261014.md). All rows converged; text above already carries the resolutions.

| ID | item | final resolution | who changed |
|---|---|---|---|
| X1 | identity, three terms | as stated, conditional on the delay set | none |
| X2 | T2 | MC exact E_d log det as primary, subtracted via its simultaneous UCB; U >= E[T2] only in expectation | Opus (UCB) |
| X3 | T3 | J = log det(I + Q^-1 C_p); MODEL interference diag(q) kept | none |
| X4 | T1 | primary A(h) = ZF-SIC/QR bound (deterministic given h, ordering from h only); LMMSE-GMI report-only (per-frame max had selection bias) | Opus |
| X5 | input law | i.i.d. QPSK; no statement about the LDPC codebook | none |
| X6 | threshold | tau = 1; 1.154 side table | Opus |
| X7 | K* and LCB | continuous pass along the grid; frame-level Bernstein with proven ranges; independent 512-frame confirmation | Opus |
| X8 | decision | NEAR-LIMIT dropped (lower bound cannot show near-limit) | Opus |
| X9 | references | per-reference labels "information headroom under X reference"; no causal attribution | both |
| X10 | ray law | RAY reference report-only (A under ray law, U, J_z) | Opus (added) |
| X11 | conditions | 5 uncensored; 9.5 dB excluded | Codex |
| X12 | U4 | deterministic quadrature with explicit error bounds (N in {1, 2}); N = 4 Monte Carlo report-only; exceedance = stop and investigate | Opus |
| N1 | P6 wording | I(d;y) <= 2N; equality needs zero-noise identifiability | Opus |
| N2 | GMI sample count | moot after X4 (GMI report-only); per-frame statistics use independent frames | Opus |
| N3 | U2 | restated for A(h): exact deterministic identity | Opus |
| C2 | confirm round 2: T3 entropy on support coordinates g; censoring rule (first failing confirmed point truncates; right-censor only if all confirmed points pass and grid not exhausted) | adopted | Opus |
| S1 | skill check (codex-info-budget-skillcheck-20261014.md): decision-rule CRITICAL, U4 unbounded Delta, T2 range, Bernstein form, delays per frame, non-Hermitian det, reverse QR order, sample vs expectation, singular support, right-censoring, Kc point estimate | all adopted as written in §2, §2.1, §2.2, §4, §6, §7 | Opus |

## 9. Post-freeze disclosures (rule unchanged)

- **Design defect found at implementation (phase 1, d44eafc7), missed by both Opus and Codex in all review rounds:** with
  the frozen worst-case ranges (A in [0, 2N], f in [0, B]) the empirical-Bernstein range term at n = 64 alone costs
  2.5-4.7 bits/symbol, while LB/N <= ~2.1. The locate stage can therefore never pass; the confirm set is always {L4, L8},
  K* <= 64 and H_low <= .32: every label is UNINFORMATIVE by construction. The rule is run as frozen and this is recorded,
  not repaired after the fact.
- Independent of the defect, phase-1 point estimates of LB/N already fall below tau = 1 at K ~ 130-190 (PHYS) against
  Kc_best 200-270, i.e. the bound sits below the practical cliffs before any confidence offset; a repaired statistic would
  not change the label. Report-only point-estimate crossings are produced by the run.
- Implementation notes accepted by Opus (conservative or report-only): delta split three ways over A, f, J; frames shared
  across the 5 conditions per (L, reference); RAY and 9.5 dB outside the alpha budget; PHYS truncated to rank 13
  (error 2.6e-13). Codex single-pass core code review: 5/5 OK (codex-ib-code-review-20261014.md).
