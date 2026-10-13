# Frozen development pilot: blind joint acquisition performance and cost

Date: 2026-10-07. Same user-approved exploration, not production/CONF. Admission of the implementation remains required before numerical execution. Live CSV: .mission/20261007-acquisition-performance/20261007-acquisition-performance.csv.

## Two claims and hard interpretation limits
Primary: a nonquadratic known column phase code plus FFT fourth-power screening gives useful joint acquisition accuracy at lower complete estimator cost than exhaustive finite-grid likelihood. Supporting: its accuracy gain survives comparison to an observation-independent optimized conventional quadratic code, not only the old small c2. Classical ingredients are attributed; substantial innovation is linked to the preceding design-class theorem. This pilot alone is not sufficient to certify general performance, continuous CFO or multipath.

## Model
N∈{32,64}, s=5, R[n]=exp(-πi s n²/N), CP=N/4, L=N+CP, T=4 contiguous frames. Delay l uniformly drawn from 0,...,N/4-1; integer physical CFO ν uniformly from 0,...,N-1; gain h=ρexp(iφ), ρ uniform [.75,1.25], φ uniform [0,2π). Symbols independent QPSK with states 0,1,2,3 mapped to [(1+i),(1−i),(−1+i),(−1−i)]/sqrt(2). Nominal σ²=10^(−SNRdB/10), independent of hidden ρ; noise sqrt(σ²/2)(ξ_R+iξ_I) with independent standard normal components. Conditional received SNR is ρ²/σ². Useful blocks are

y_t=h exp(2πiνLt/N) D_ν Π_l R F^H C S_t+η_t.

Known sample-window timing, fixed h, same l/ν over T. Guard is transmitted and discarded. This is exactly the declared integer acquisition problem, with no free fractional correction. Because 4νL/N=5ν is integer, frame phase lies in C4; it is absorbed by iid QPSK in the marginalized law and disappears under fourth powers. No unjustified coherent alignment is performed. Noise variance is known to likelihood methods; h,l,ν,S are hidden from all estimators.

## Stage D: observation-independent waveform design
For each N, compare: current v_j=exp[-2πi j²/(10N²)]; optimized quadratic; and one random unit-modulus w with v its principal fourth root. Random code RNG seed is 2026100701, drawn once in ascending N order, no rejection/seed selection. This draws 96 design phases and zero channel/noise observations; save code bytes.

Optimized quadratic minimizes max_(k=1,...,N-1; d=0,...,N/4-1) |A_(v^4)(k,4d)| over exactly 129 candidates: current c2 and c2=(j+sqrt(2))/(4*129), j=0,...,127. Lowest candidate index breaks exact ties. This finite search is a strong tuned quadratic baseline, not a certified global optimum. Include candidate construction, ambiguity FFTs, code generation and chosen-code bytes in offline design time/cost. Evaluate 130 codes per N (129 quadratic candidates including current, plus one random arm); the current arm reuses its design result. Each code evaluates (N-1)*(N/4) nontrivial pairs, totaling 163280 scalar ambiguity values. No adaptive search.

## Observation-only algorithms
Each complete call includes validation, R dechirping, unitary FFTs, code/template construction and final a,l,ν,h estimates. No shared across-call preprocessing cache; report design offline cost separately.

Let X=F R^H Y and m_j=mean_t X_tj^4. For each a, compute q_aj=m_j conjugate(w_(j-a)); the score for delay l is |N ifft(q_a)[4l mod N]|. The omitted exp(-8πila/N) has unit modulus. Keep all N*(N/4) hypotheses in deterministic a-major, l-minor order. FFT-screening uses the exact same score as direct summation.

1. FOURTH: choose highest fourth-power score, lowest index breaks ties.
2. SCREEN32: keep the 32 highest-scoring hypotheses, stable index tie break; evaluate the exact finite-grid marginalized QPSK likelihood on them.
3. FULL: evaluate that same finite-grid likelihood on every hypothesis. No truth initialization.

For candidate (a,l), demodulated coordinates are z_tj=X_tj conjugate(v_(j-a)) exp(2πil(j-a)/N). For gain grid magnitude [.75,1,1.25] and phase rπ/(2*16), r=0,...,15, score

Σ_(t,j) [logcosh(sqrt(2) Re(z_tj exp(-iφ))ρ/σ²)+logcosh(sqrt(2) Im(z_tj exp(-iφ))ρ/σ²)-ρ²/σ²].

This is the exact QPSK mixture log density up to constants common to hypotheses, on a finite gain grid. Stable logcosh uses logaddexp(u,-u)-log(2). The unknown continuous h is approximated by the same grid for SCREEN32 and FULL; neither is claimed globally optimal continuous ML. Lowest global hypothesis then gain index breaks exact ties. The gain grid estimates h_eff=h exp(−πis l²/N); return physical h_hat=h_eff_hat exp(+πis l_hat²/N), identifiable only modulo C4. Return physical ν=(a-5l) mod N. FULL and SCREEN32 are separately paid calls, including recomputed FFT/template work. Store full likelihood scores/best-gain indices and fourth scores for audit. Pure FOURTH does not estimate h and must return explicit unavailable gain, never a fake value.

## Stage P: paired pilot and accounting
Data seed 2026100702; N ascending, SNRdB∈[5,15] ascending, 64 independent groups per cell. Four cells, 256 paired groups. Draw per group in order: l, ν, ρ, φ, QPSK states T×N, standard noise real, standard noise imaginary. All three waveform arms share these exogenous variables. Save raw source arrays and all Y, with dtype/shape/content hashes.

Run all three algorithms on all three waveforms: 2304 paid acquisition calls; no production receiver/decoder calls. 768 waveform datasets, 3072 newly generated N-vectors, 147456 complex observations. Rotate the nine algorithm/arm execution order cyclically by group index for timing balance; no warmup datasets. Save every error, tie, selected parameters, score grids and elapsed time. Error iff either integer ν or l differs from truth; no discarded ties/failures.

Complete algorithm timing excludes common generation and disk logging, includes every algorithm operation and uncached template; report process/startup/raw I/O separately. Single CPU thread, no concurrently timed jobs and no GPU. Changing waveform is reported as a design intervention; same-waveform FULL versus SCREEN32 isolates algorithmic cost.

## Frozen gates
All are required for a positive development signal, which still requires independent audit:
- Numerical contracts: FFT scores agree with direct sums in deterministic tests; FULL score ≥ SCREEN32 score for every observed case within absolute 1e-8 + relative 1e-10; no invalid/counted-missing groups.
- Same nonquadratic waveform: SCREEN32 complete elapsed sum at least 3× faster than FULL, and mean per-cell time ratio also reported; no universal hardware claim.
- Same-waveform noninferiority: total bad-direction discordance x≤1 across 256 independent groups. The estimand is the four-cell equal-weight average P(SCREEN32 wrong and FULL correct). This preserves the originally specified CP acceptance set, but does not mislabel heterogeneous Bernoulli sampling as iid. Under mean risk≥.02, P(x≤1)≤BinomCDF(1;256,.02)<.05 by the pairwise averaging proof in METHOD_REVIEW.md. Report CP only as a binomial reference and report opposite discordance. No generic exact stratified CP confidence claim.
- Accuracy of the full proposed package: equal-cell-weighted error-rate reduction (optimized-quadratic SCREEN32 minus random-code SCREEN32) ≥.10, with exploratory paired normal 95% interval lower bound >0. Report both current and optimized quadratic for all algorithms and each cell, plus FULL comparisons so weak screening cannot masquerade as code benefit.
- Paired accuracy SE is sqrt(sum_c sample_var(D_c)/(4²*64)), with D=quadratic error−random error; the normal interval is exploratory.
- No cell of the random SCREEN32 arm has error rate above .25. This protects against claiming an unusable fast estimator from a pooled result.

Failure of any gate means no joint performance–cost success for this pilot. Preserve results, diagnose the actual failure, and register targeted followup before modifying sources/grids. Do not retrospectively adjust gates, select better seeds or pool later data into this pilot.

## Execution and resource contract
Stages D/P/A: design wall cap120s; paired pilot600s; independent raw audit300s; total reservations1020s. Peak whole-process RSS2GiB, output512MiB. Exactly96 design phase draws,0 new observations in D; exactly3072 in P;0 new observations in A. No retry budget implied. Existing source-bound immutable recorder owns admissions, source snapshots, reservations, failures and resource accounting. All task Python/config bytes committed before GO; independent source admission precedes isolated remote snapshot. Imports preloaded before thread-inventory freeze.

deinlab only, conda AFDM; all remote source/output/tmp/cache under /data/guoyikun, CUDA hidden and BLAS/OpenMP1. Stage names immutable; retain failed attempts. Small results/raw audit receipts return locally; large files remain remote with path/hash. This frozen plan is a development experiment, not manuscript promotion or fresh CONF.

## User preference retained
Useful OFDM-to-AFDM adaptations are eligible modest contributions even where the ingredients are established; do not discard them for lack of first-in-literature novelty. Preserve them with scoped attribution, while this continuation also tests the stronger joint theory/performance–cost objective. Protocol definitions corrected before any scientific observations after independent METHOD_REVIEW.md.
