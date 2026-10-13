# Residual-CFO fourth-moment transfer and branch preservation

## Target
Establish a mathematical increment beyond the previous oracle-fractional bridge: exact population response under nonzero residual fractional CFO, and a valid consistency result when the fractional estimate uses the same data. This is a candidate modest AFDM phase-code contribution, not a first-in-literature claim.

## Status
COHERENT AS STATED after explicit assumptions and scope corrections — cross-model review passed for Propositions 1–5. No new simulation or performance result.

## Invariant Object
The complex correlation of the population holomorphic fourth moment with cyclic shifts of the known fourth-power phase code. The modulus is taken after expectation, not before it.

## Assumptions
N>=2 fixed; iid frames and iid entries of S uniformly distributed on exp(i*pi/4)*{1,i,-1,-i}, each point with probability 1/4; a complete untruncated single zero-delay path with fixed unknown complex h!=0 and fixed CFO nu=r+kappa; independent zero-mean proper white Gaussian noise eta_t~CN(0,sigma^2 I_N), sigma^2<infinity, independent across frames and of all symbols. Known U=R F^H C with diagonal unit-modulus R, C_jj=v_j, |v_j|=1, unitary negative-exponent F. No unknown timing, multipath, IQ imbalance or variable gain. In particular h includes the block-start phase and is fixed across iid snapshots: consecutive free-running CFO blocks generally accumulate a block-start phase and are NOT automatically covered without a justified phase-alignment model. The candidate fourth-power code w_j=v_j^4 has periodic autocorrelation sum_j w_j conjugate(w_{j-q})=N*1_{q=0}. The previous even-N c2=1/(8N) and odd-N c2=1/(4N) satisfy this assumption.

## Notation
D_b=diag(exp(2*pi*i*b*n/N)); P_r x at index s is x_{s-r}, indices modulo N. After known R removal, Z_t=h D_nu F^H C S_t+eta_t. At any real trial a, X_t(a)=F D_{-a} Z_t. Define residual delta=kappa-a and integer reference r. Define g_delta(l)=N^{-1} sum_{n=0}^{N-1} exp(2*pi*i*(delta-l)*n/N), b_delta(l)=g_delta(l)^4, u_k=P_k w. Define m_T(a)=T^{-1} sum_t X_t(a)^{odot4}, mu(a)=E[m_T(a)] for deterministic a, and c_k(a)=u_k^H mu(a)/N. For quadratic chirps v_j=exp(-2*pi*i*c2*j^2). All CFO statements are modulo N, the intrinsic sampling alias period.

## Derivation Strategy
Use proper source moments to eliminate all mixed fourth-order terms, then cyclic code orthogonality to invert the resulting convolution. Handle adaptive a_T by a uniform empirical bound over the whole real trial axis, rather than falsely conditioning on a same-sample estimate and retaining white noise.

## Derivation Map
1. Fixed trial a: residual Fourier mixing is circulant with entries g_delta(s-j).
2. Holomorphic fourth moment: exact convolution with b_delta, including Gaussian noise cancellation only at the population level.
3. CAZAC fourth-power code: circular correlation removes the code and returns b_delta shifted by r.
4. Nearest-bin Dirichlet amplitude: strict peak at r for |delta|<1/2, tie at the half-bin boundary.
5. Finite trigonometric-polynomial representation of the empirical statistic: uniform strong law and a finite-N probability bound, applicable to arbitrary same-data a_T.

## Main Derivation

### Proposition 1. Exact residual transfer for an arbitrary unit-modulus code
For every fixed real a,

mu_s(a)=-h^4 sum_l b_delta(l) w_{s-r-l}.

Indeed F D_delta F^H has entry g_delta(s-j), so X_s(a)=h sum_j g_delta(s-j) v_{j-r} S_{j-r}+xi_s. For deterministic a the noise is proper Gaussian and independent of S. E[S]=E[S^2]=E[S^3]=0 and E[S^4]=-1. In expanding the fourth power only four equal source indices survive. Proper Gaussian holomorphic moments through order four vanish, and all mixed noise-source terms vanish. This gives the displayed formula. It is a fourth POWER, not |g|^4 inside the complex convolution. It is not a formula for the conditional mean given a data-selected a_T.

### Proposition 2. Orthogonal phase codes reveal the leakage kernel exactly
Under the fourth-power CAZAC assumption,

c_k(a)=-h^4 g_delta(k-r)^4,
|c_k(a)|=|h|^4 |g_delta(k-r)|^4.

Proof: insert Proposition 1 into N^{-1} sum_s conjugate(w_{s-k}) mu_s. The inner circular correlation of w vanishes unless k=r+l modulo N, when it equals N. The shift and factor N follow directly. No inverse of a noisy covariance or knowledge of h is used by the statistic.

For delta not an integer,

|g_delta(l)|=|sin(pi*delta)|/[N |sin(pi*(delta-l)/N)|].

Interpret the removable singularities by the finite sum definition. For delta=0, g_0(l)=1_{l=0}. For |delta|<1/2 the circular distance between delta and l=0 is strictly less than to any other integer modulo N. On circular distances in [0,N/2], sin(pi*d/N) is strictly increasing. Thus k=r is the UNIQUE maximizer of |c_k|. At delta=+1/2 the branches r and r+1 tie; at -1/2 the branches r and r-1 tie (for N=2 these are the same neighbor). This boundary is a property of the chosen population correlation, not an impossibility theorem for all estimators.

Define for epsilon in (0,1/2),

G_{N,epsilon}=min_{|delta|<=1/2-epsilon} (|g_delta(0)|^4-max_{l!=0}|g_delta(l)|^4)>0.

Strict positivity follows from continuity, the pointwise strict gap above, and compactness. The normalized population score margin is at least |h|^4 G_{N,epsilon}. This does not assert an N-uniform lower bound or an optimal finite-sample code.

### Proposition 3. Uniform control removes the same-data conditioning error
For every frame t define Q=4(N-1)+1 and coefficients

B_{s,q,t}=N^{-2} exp(-2*pi*i*s*q/N) sum_{n1+...+n4=q} Z_{n1,t} Z_{n2,t} Z_{n3,t} Z_{n4,t},

where each n_j ranges from 0 to N-1, and q=0,...,4(N-1). Ordered tuples are included. Direct expansion gives

X_{s,t}(a)^4=sum_q B_{s,q,t} exp(-2*pi*i*a*q/N).

Every coefficient is iid across t, has finite second moment (bounded source plus Gaussian noise), and no independence among s or q is assumed. Let Delta B_{s,q}=T^{-1} sum_t B_{s,q,t}-E[B_{s,q,1}]. Then

sup_{a in R} max_k |u_k^H(m_T(a)-mu(a))/N|
<= N^{-1} sum_{s,q}|Delta B_{s,q}| =: E_T.

The finite collection of strong laws yields E_T->0 almost surely for fixed N,h,nu,sigma. This uniform event holds before choosing a_T and so applies even to a_T computed from those same T frames. No claim of a conditional Gaussian noise law is needed.

A loose finite-N quantitative version follows from Cauchy-Schwarz over NQ coefficients:

E[E_T^2] <= (Q/N) sum_{s,q} Var(B_{s,q,1})/T = K_N/T,

where Var means E|B-E B|^2. K_N is finite, can depend on h,sigma,nu,N, and is not claimed dimension-free or sharp. Therefore P(E_T>=b)<=K_N/(T*b^2).

### Corollary. Adaptive front-end branch consistency with a safety margin
Let a_T be ANY measurable real-valued function of the same observed frames. Let r be the fixed integer in nu=r+kappa, and let rhat_T maximize |u_k^H m_T(a_T)| with any fixed tie rule. For epsilon in (0,1/2),

P(rhat_T!=[r]_N) <= P(|kappa-a_T|>1/2-epsilon)
 + 4 K_N/[T |h|^8 G_{N,epsilon}^2].

Proof: if the first event is absent and E_T<|h|^4 G/2, every empirical wrong-branch score is strictly below the true score by triangle inequalities. Apply the probability bound. The right side can exceed one and can always be capped at one; no finite-T sharpness is claimed.

If, for some fixed epsilon>0, the front end stays in the contracted interval |kappa-a_T|<=1/2-epsilon with probability tending to one, then rhat_T->r in probability. If it stays in that same fixed contracted interval eventually almost surely, the branch is eventually correct almost surely by the uniform strong law. The front end NEED NOT converge to zero residual for this branch statement. Accurate TOTAL CFO still requires accurate fractional estimation. The theorem does not establish that the existing three-point front end meets the interior condition.

More explicitly, define rho_T=nu-a_T, j_T=floor(rho_T+1/2), d_T=rho_T-j_T. The same bound is P(rhat_T!=[j_T]_N)<=P(|d_T|>1/2-epsilon)+4K_N/(T|h|^8 G^2). This is correct tracking of a potentially varying integer target, not convergence to one fixed integer.

For an a_T convention in [0,1) that crosses a fractional wrap, the appropriate branch is the integer part relative to that compensation; one must reindex nu-a_T into r_T+delta_T, delta_T in [-1/2,1/2). The same uniform argument works on events with |delta_T|<=1/2-epsilon, with target r_T rather than an incorrectly frozen original integer. This avoids claiming an error from a representation carry. Any same-data rule with residual distance from half-integers bounded away from zero qualifies; proximity to a half-integer destroys the uniform margin.

### Proposition 4. A front-end-free population CFO decoder for N>=3
The same transfer identity suggests a stronger endpoint: set a=0, compute only m_T(0) and its code correlation. No fractional search or oracle correction is required. Write nu=r+delta modulo N with delta in [-1/2,1/2]. Let c_k=u_k^H mu(0)/N. Choose r from the maximum |c_k|. If the two neighbors have nonzero unequal magnitudes, choose d in {-1,+1} toward the larger one, comparing |c_{r+1}| to |c_{r-1}|. Define

R=(|c_{r+d}|/|c_r|)^(1/4),
f(R)=N/pi * arctan( R*sin(pi/N)/(1+R*cos(pi/N)) ),
nu_decoded=r+d*f(R) modulo N.

For delta=0 set f=0; equal zero neighbors do not matter. At a half-bin tie, either maximum r may be selected and d points toward the other maximum, with R=1 and f=1/2. Both choices return the same nu modulo N.

Proof: for 0<|delta|<=1/2 and N>=3, the neighbor in the direction of delta is strictly closer on the N-circle than the opposite neighbor, hence larger by the Dirichlet magnitude formula. Let theta=pi*|delta|/N and alpha=pi/N. Then R=sin(theta)/sin(alpha-theta), so tan(theta)=R*sin(alpha)/(1+R*cos(alpha)). Since theta in [0,alpha/2] and alpha<=pi/3, the principal arctan yields exactly theta. Unknown |h| cancels in R. The gain phase never enters the magnitude statistic.

Implementable plug-in: replace c by c_hat_k=u_k^H m_T(0)/N, select its largest modulus and larger adjacent modulus by a deterministic tie rule, and use the same formula. The selected main modulus is at least the neighboring modulus, so 0<=R<=1 by construction, without numerical clipping. If all scores are exactly zero, declare non-identification rather than divide by zero. This branch cannot persist asymptotically when h!=0 because the population main score is positive.

For fixed N>=3,h!=0,nu,sigma, the plug-in estimate converges almost surely to nu modulo N as T->infinity. Finite-dimensional strong convergence of c_hat proves this: away from integer/half-integer CFO the peak and direction are eventually the correct unique choices and the formula is continuous. At integer CFO, either noisy direction gives R->0 and the same decoded limit r. At half-integer CFO, only the two tied adjacent peaks can remain selected; for either peak the selected adjacent direction points to the other peak eventually, R->1, and both outputs converge to the same half-integer. Thus all boundary cases have the same modulo-N limit. This is a complete asymptotic CFO estimator in the restricted model, not merely a conditional branch theorem.

N=2 is deliberately excluded: the two adjacent indices coincide, so their magnitudes cannot determine the sign of a nonzero residual. No claim about all alternative N=2 estimators is made. Although fourth powers cancel unknown QPSK only after expectation at nonzero residual, iid frames supply that expectation. T=1 exact recovery at arbitrary residual is NOT claimed.

Computational architecture, not a measured benchmark: each frame needs one known dechirp and N-point FFT, then pointwise fourth powers and an average; one cyclic correlation (FFT implementation possible) and a constant-size ratio inversion finish the estimate. The classical three-point fractional update is absent. No numerical implementation or runtime benefit has been tested for this new decoder.

### Proposition 5. The naive fourth-root decoder is nonregular at integer CFO
This limitation is part of the result, not an optional caveat. Suppose nu is an integer, N>=3 and sigma^2>0. In the correctly shifted Fourier coordinates, each fourth-power entry equals -h^4 w plus independent proper error of variance

V=16|h|^6 sigma^2+72|h|^4 sigma^4+96|h|^2 sigma^6+24 sigma^8.

Properness follows by conditioning on the QPSK symbol: the centered fourth-power error is a polynomial in the proper Gaussian noise with zero constant term, and its holomorphic square has zero expectation. Errors are independent across coordinates. The CAZAC cyclic-shift matrix, divided by sqrt(N), is unitary. Consequently the multivariate CLT gives

sqrt(T)*(c_hat-c) -> CN(0,(V/N) I_N).

For integer nu=r, c_r=-h^4 and all off-peak c_k=0. Let G_plus,G_minus be independent CN(0,V/N), the limiting adjacent errors. Peak selection is eventually r. With d chosen toward the larger adjacent modulus, the ratio in Proposition 4 obeys

T^(1/8) R -> (max(|G_plus|,|G_minus|)/|h|^4)^(1/4)

in distribution. Since f(R)=(N/pi)*sin(pi/N)*R+O(R^2),

T^(1/8) dist_modN(nu_hat,nu)
 -> (N/pi)*sin(pi/N)*(max(|G_plus|,|G_minus|)/|h|^4)^(1/4).

The limit is nondegenerate for sigma^2>0. Thus the naive estimator has T^(-1/8) error scale at integer CFO, despite being strongly consistent. This is an estimator-specific pointwise statement at a fixed integer CFO, not a neighborhood-uniform rate, not a worst-local-rate claim, and not an information lower bound for raw Y or all estimators. With sigma=0 the exact-integer fourth-power statistic has no payload variance and this slow-rate statement does not apply.

Scientific consequence: the population fourth-root inversion is an explicit identifiability construction, but cannot be promoted as a generally better practical replacement for the classical fractional front end. The branch robustness theorem can still support retaining that front end and using the phase code for integer discrimination. No tuning, new run or finite-T superiority is implied.

### Cross-frame phase cancellation is an explicit applicability boundary
For physical consecutive blocks with absolute start n_t=tL, a constant oscillator CFO produces Z_t=h exp(2*pi*i*nu*tL/N) D_nu F^H C S_t+eta_t even in a static channel. Unweighted fourth-moment averaging then has expected correlation

E[c_hat_k(a)]=-h^4 g_delta(k-r)^4 A_T,
A_T=T^{-1} sum_{t=0}^{T-1} exp(8*pi*i*nu*tL/N).

If exp(8*pi*i*nu*L/N)!=1, the geometric sum is O(1/T), so the fixed nonzero population margin vanishes. For independent frames with bounded moments the averaging noise is generally of order T^(-1/2), so this is not repaired by collecting more unaligned blocks. At resonance A_T=1; no blanket cancellation claim applies there. For finite T with A_T!=0, the exact population ratio still cancels A_T; the problem is the shrinking mean relative to nondegenerate sampling fluctuations, not necessarily loss of every finite-T algebraic inversion. This is not a non-identifiability claim for raw continuous-frame observations or all receivers. The fixed-complex-gain theorem therefore describes coherent/reset snapshots, not a free-running continuous frame receiver. No unknown phase alignment is assumed free. This observation prevents promoting Proposition 4 into a generally useful deployed method without a new physical and statistical derivation.

## Remarks and Interpretation
The extra mathematical content is not the classical three-point update or CAZAC autocorrelation identity by itself. It is the exact fourth-order residual transfer, the half-bin peak-preservation result for unknown random payload, and the uniform argument permitting reuse of front-end data. The previous bridge assumed perfectly corrected fractional CFO and explicitly could not justify the same-data case.

Physical intuition: the unknown QPSK payload disappears only in the population fourth moment. The fourth-power phase code acts as a known signature there. Orthogonal cyclic signatures make residual Fourier leakage visible without allowing code sidelobes to bias the integer maximum. Finite-frame payload cross terms and noise remain; zero-noise one-frame exactness from the previous zero-residual case does NOT carry over here.

An arbitrary non-CAZAC code yields a convolution of b_delta with its cyclic autocorrelation, not an isolated leakage kernel. This gives a specific design reason for orthogonal fourth-power shifts beyond exact zero-residual identifiability.

## Boundaries and Non-Claims
- Fixed N, T->infinity with h,nu fixed; no uniform deep-fade guarantee, no growing-N/sample-efficiency theorem.
- The population score is |E[complex statistic]|, never E[|statistic|].
- No new Monte Carlo, SSH workload or improved BER/runtime claim is made.
- Does not claim the frozen T=1/4 pilot reaches the asymptotic regime or passes its failed design gate.
- Same complete single zero-delay path; no full multipath/delay guarantee or production chirp change.
- No novelty-exclusive claim; closest literature and independent review must assess whether this is a publishable modest increment.

## Open Risks
Nearest prior art may already analyze fourth-order precoded CFO residuals. The coefficient variance bound is conservative and may be numerically useless at small T. The guarantee requires a margin from half-bin boundaries and does not prove the preceding fractional estimator meets that condition. Cross-model mathematical review passed; no practical-receiver or first-in-literature certification.
