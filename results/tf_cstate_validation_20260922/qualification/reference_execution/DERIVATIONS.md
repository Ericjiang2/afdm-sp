# Exact compact structural exchange: derivation and novelty boundary

22 September 2026. This is an independently derived and numerically checked **classical control**, not a claimed new inference principle. It is designed to preserve the earlier GLOBAL20 fixed-working-distribution structural update. It has not been executed on the production receiver/checkpoints in this environment.

## 1. What is frozen

At the checkpoint, freeze the observation y, the APP-derived mean m=p+mu, diagonal AF-domain covariance V=diag(v), lambda=sigma^2, the Doppler proposal grid, the admissible delay range, and the number P of physical slots. Maintain repeated-delay cross terms. Do not replace the receiver's refit ridge by an asserted physical gain prior.

For physical operators U_i, define B=[U_i m], Gamma_ij=tr(U_i^H U_j V), A=B^H B+Gamma+lambda I, b=B^H y. The criterion is

Q(h,S)=||y-Bh||^2+h^H Gamma h+lambda||h||^2.

Its optimizer and optimum are h=A^-1 b and Q_S=||y||^2-b^H A^-1 b. All inverse notation is algebra; the reference obtains the small inverse by Cholesky solves. C=A^-1 is an optimization sensitivity, not calibrated posterior covariance and not TF's scalar gain variance.

## 2. The compact state and exact exchange formula

For a prospective physical atom a, let phi_a=U_a m, k_a=B^H phi_a+Gamma_(S,a), beta_a=phi_a^H y, d_a=||phi_a||^2+Gamma_aa+lambda. Since U_a is unitary,

d_a=||m||^2+sum(v)+lambda,

independent of delay and Doppler. Define

u_a=C k_a, s_a=d_a-k_a^H C k_a, g_a=beta_a-k_a^H h.

The augmented normal matrix is [[A,k_a],[k_a^H,d_a]]. Eliminating the old gains gives

Q_(S+a)=Q_S-|g_a|^2/s_a,
h_old_plus=h-u_a g_a/s_a,
h_a_plus=g_a/s_a,
C_old_plus=C+u_a u_a^H/s_a.

Here u_a is denoted by `u` in the code; it is not physical Doppler. The Schur complement is positive for positive ridge and PSD moment Gram. The addition is an algebraic device: the deployed model is not increased in order.

For any positive definite quadratic with optimizer z and inverse Hessian Cplus, constraining coefficient i to zero increases the optimum by |z_i|^2/Cplus_ii. To prove this, write the quadratic as Qmin+(h-z)^H Aplus(h-z), minimize subject to e_i^T h=0, and use a Lagrange multiplier. Therefore

**Q_(S-i+a)=Q_S-|g_a|^2/s_a + |h_i-u_ai*g_a/s_a|^2/(C_ii+|u_ai|^2/s_a).**

This is the full joint incoming-atom/outgoing-slot score. It is not an add-only score minus a deletion penalty evaluated before the addition.

For an M-atom bank, retain beta in C^M and K=[k_a] in C^(P x M), plus A, C, h. One C@K multiplication gives every u_a. All PM scores then require scalar elementwise operations. No P separate reduced normal solves are needed for each bank block. This is a compact sufficient state, not a proof of globally minimal memory/information.

## 3. Exact CPP-aware global correlations

Let x_T=A_DAFT^H m and use the positive-Doppler convention of the current master/reference implementation. Define an extended waveform for t=-L,...,N-1:

x_ext(t)=x_T(t), t>=0;
x_ext(t)=exp(j2pi c1 [N^2+2Nt]) x_T(t+N), t<0.

The path response is phi_(l,nu)[n]=exp(j2pi nu n/N)x_ext(n-l). For any observation-domain vector z,

F_z(l,nu)=sum_n conj(x_ext(n-l))*exp(-j2pi nu n/N)*z[n]
           =phi_(l,nu)^H z.

For each declared nu this is a linear correlation over **all** delays. Convolve exp(-j2pi nu n/N)z[n] with the reversed conjugate extended waveform. A transform length T>=2N+L-1 avoids aliasing, and output indices N-1+l give F_z(l,nu). Thus beta=F_y and K_i=conj(F_(B_i))+Gamma_(i,bank).

This computes all finite-bank candidates, including noninteger Dopplers, exactly up to floating point. It is not continuous global optimization and does not eliminate the bank search. It changes how the bank's sufficient statistics are obtained. There is no physical leakage-window truncation, no circular-prefix assumption in place of CPP, and no independent prior on time-domain samples.

For the current diagonal covariance use the established identity

Gamma_ij=exp(j2pi c1(l_i^2-l_j^2)) D_N(nu_j-nu_i+2Nc1(l_j-l_i)) FFT(v)[(l_j-l_i) mod N],

where D_N(t)=N^-1 sum_n exp(j2pi tn/N). The independent checks compare this with dense physical operators, including repeated delays and nontrivial CPP.

## 4. Exact state maintenance after a replacement

With m,V and the bank fixed, beta never changes. Replacing physical slot i changes only row i of K. The other rows refer to unchanged physical atoms and not to their fitted gains. Refresh that row through one correlation-field evaluation plus Gamma; rebuild/factor the small P-by-P normal system; compute all new scores. A rank-one inverse add/delete implementation is possible but not required at P=8; the reference uses the more conservative small Cholesky refit.

For two accepted replacements there are P+1 initial field calls and one row-refresh field call: P+2 total. Local Doppler passes are performed only after the structural steps, exactly as in GLOBAL20. Refreshing m or V would invalidate beta, K and the kernel state; no cheap persistent update across arbitrary decoder iterations is claimed.

Let D be the number of grid Dopplers and M=(L+1)D. Field construction costs O((P+1) D T log T); a refresh costs O(D T log T); each all-pair score pass costs O(P^2 M+PM), plus the small active-system construction. Persistent fields need (P+1)M complex numbers; FFT and active-response workspace are additional. The old reference materializes candidate response chunks and performs separate retained-slot solves. These complexity comparisons are for the reference structures, not a proof that every competent classical implementation has the old cost.

## 5. Why the mechanism is classical

For a finite bank, associate each atom with the augmented feature

a_j=[U_j m; vec(U_j V^(1/2)); sqrt(lambda)e_j],
t=[y;0;0].

Then a_i^H a_j=(U_i m)^H(U_j m)+tr(U_i^H U_j V)+lambda delta_ij and ||t-sum_j h_j a_j||^2=Q(h,S). If an algebraic augmented system contains an identical physical atom twice, its ridge coordinates remain distinct slot labels; the final admissible support excludes duplicate retained atoms.

The fixed-q structural problem is therefore ordinary cardinality-constrained least squares in an augmented feature space. Keeping its Gram sensitivities and applying Schur add/delete updates does not add a new posterior mechanism. Calling C a cavity covariance or K an operator-belief field would not alter that reduction.

Closest inspected art: Leibovitz and Giryes, *Efficient Least Residual Greedy Algorithms for Sparse Recovery*, IEEE TSP 68:3707-3722 (2020), arXiv:2004.06661, section II. It explicitly develops inverse-Gram addition/removal, FOLS, OLSR/IOLSR, dictionary-vector state updates and transform-structured operators. The exact joint all-pair maximization here is not asserted to be their identical selection schedule. Its closure follows directly from the same classical add/delete lemmas.

JCCD-VALSE, arXiv:2107.07101, already combines LDPC soft information, continuous channel parameters, and support/model-order inference. Data-aided evolving-grid SBL for SP-AFDM, arXiv:2607.18881, already revises geometry using detected data; its inspected Mod[Demod] interface is not the current TF LDPC-APP interface. Tipping and Faul (AISTATS 2003) supplies older sequential evidence addition/deletion ancestry, but its marginal criterion is not the present ridge profile.

No exact same AFDM/CPP implementation was established in the inspection. That leaves a possible application/computational specialization, not evidence of the stronger new core inference mechanism requested.

## 6. Counterexamples and limitations

**Candidate first, slot second is not exact.** Let the current dictionary be [e1,e2], target y=[1,2,1.1,1]^T, ridge .01, and candidate atoms a=e3 and b=(e1+e4)/sqrt(2). The active normal matrix has condition number one. Adding a gives improvement 1.198020, while adding b gives .990289; an add-first rule chooses a. But the best complete exchanges improve the objective by .207921 and .990099 respectively. The new atom's ability to take over an existing contribution is essential to the replacement cost. As ridge tends to zero and y3^2=1+epsilon, the ratio of the shortcut's improvement to the true best exchange can approach zero.

**Active summaries are not global evidence.** An exact CPP fixture gives identical active correlations and residual norms for two observations with different omitted-delay responses. This refutes inferring the missing direction solely from those summaries. It does not claim the full observations or all TF states are identical, and does not prove a global scan lower bound.

**Uninformative means:** if m=0 then b=beta=0 and this quadratic cannot create a data-driven nonzero gain. A richer code-coupled mechanism could in principle exploit information outside this frozen mean-based criterion. The current production audit has not shown this is the dominant limitation of its saved informative checkpoints.

**Numerical conditioning:** an intentionally extreme zero-variance, ridge=1e-12, nearly duplicate-path fixture has condition about 8.96e13 and unguarded score error .0475 even with positive Schur complements. Positive slack alone is not a numerical certificate. The delivered high-level reference falls back to the old control above condition 1e8 or on numerical failures, counting abandoned work. That threshold is an engineering guard, not a rigorous rounding-error bound. Equality must still be qualified on production arrays and near-tie cases.

The exact arithmetic guarantee concerns the declared working objective, grid, duplicate mask, tolerance/order and downstream map. It does not guarantee global physical-path optimality, correct codeword decisions, calibrated posteriors, or inference performance beyond GLOBAL20.
