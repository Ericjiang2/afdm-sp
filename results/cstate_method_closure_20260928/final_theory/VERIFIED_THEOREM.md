# Final independent theorem verification and manuscript wording

## Theorem: one scalar contraction

Let $N\ge2$, $P\ge1$, and $U_1,\ldots,U_P\in\mathbb C^{N\times N}$ be unitary. For a **specified** family $\mathcal F$ of Hermitian positive-semidefinite matrices, define

\[
\Gamma_{ij}(V)=\operatorname{tr}(U_i^H U_jV),\qquad
R_{ij}=N^{-1}\operatorname{tr}(U_i^H U_j),\qquad s=\operatorname{tr}(V).
\]

Then $\Gamma(V)=sI_P$ for every $V\in\mathcal F$ if and only if $\operatorname{tr}(U_i^HU_jV)=0$ for every $i\ne j$ and every $V\in\mathcal F$. Equivalently, each off-diagonal trace functional vanishes on the real linear span of $\mathcal F$. In particular:

1. For the full isotropic family $\{vI_N:v\ge0\}$, the condition is $\operatorname{tr}(U_i^HU_j)=0$, equivalently $R=I_P$. Necessity for a smaller isotropic family requires at least one positive $v$.
2. For **all** covariances diagonal in one fixed orthonormal basis $B$, it is $\operatorname{diag}(B^HU_i^HU_jB)=0$. A smaller diagonal family imposes only its own span constraints.
3. For **all** Hermitian PSD covariances, it would require $U_i^HU_j=0$ for every $i\ne j$, which is impossible for $P\ge2$ unitary paths. For $P=1$, closure is exact for every covariance.

The zero or empty family makes the iff vacuous. No statement here asserts that actual receiver covariances reach all members of one of these full families.

### Proof

Unitarity gives $\Gamma_{ii}(V)=\operatorname{tr}(V)$; hence the matrix equality is exactly the collection of off-diagonal equalities. Trace is real-linear on Hermitian matrices, proving the span form. For isotropic $V=vI_N$, the off-diagonal value is $v\operatorname{tr}(U_i^HU_j)$. For $V=B\operatorname{diag}(v)B^H$, it is $\sum_kv_k(B^HU_i^HU_jB)_{kk}$; selecting $v=e_k$ proves necessity of each diagonal entry. For the full PSD family put $M=U_i^HU_j$ and $V=xx^H$, with **complex** $x$. Thus $x^HMx=0$ for every $x$. Testing $e_a$, $e_a+e_b$, and $e_a+i e_b$ gives $M_{aa}=0$, $M_{ab}+M_{ba}=0$, and $iM_{ab}-iM_{ba}=0$, so $M=0$, even though $M$ need not be Hermitian. But $U_i^HU_j$ is unitary and cannot vanish. This proves both directions and the edge cases without assuming Gaussianity or covariance reachability. ∎

## Corollary: frozen AFDM/CPP coordinates

Assume integer representative delays $0\le l<N$, sufficient CPP, the frozen unitary $A=\Lambda_2F\Lambda_1$ with $F_{kn}=N^{-1/2}e^{-2\pi i kn/N}$, and $U(l,\nu)=AD_\nu C_lS_lA^H$, where $D_\nu[n,n]=e^{+2\pi i n\nu/N}$ and $C_l$ is the frozen unit-modulus CPP wrap factor. Then

\[
R_{ij}=\mathbf 1_{\{l_i=l_j\}}D_N(\nu_j-\nu_i),\qquad
D_N(\delta)=\frac1N\sum_{n=0}^{N-1}e^{+2\pi i n\delta/N}.
\]

For equal delay, $\operatorname{diag}(U_i^HU_j)=D_N(\nu_j-\nu_i)\mathbf1_N$ **in the AF data coordinates**. Therefore, on an equal-delay pair and for every AF-diagonal $V\succeq0$, $\Gamma(V)=sR$ on that two-path block. Distinct representative delays give $R_{ij}=0$, but do **not** generally give $\Gamma_{ij}(V)=0$ for nonuniform AF-diagonal or arbitrary PSD $V$.

For a same-delay doublet set $\rho=D_N(\nu_2-\nu_1)$ and $r=|\rho|\in[0,1]$. Its normalized Gram is $R=\begin{psmallmatrix}1&\rho\\\rho^*&1\end{psmallmatrix}$, with eigenvalues $1\pm r$. Hence

\[
\min_{c\in\mathbb C}\|R-cI_2\|_2=\|R-I_2\|_2=r,
\qquad
\min_{c\in\mathbb C}\|\Gamma(V)-cI_2\|_2=sr
\]

for that AF-diagonal block. The first minimizer is $c=1$; the second is $c=s$ (including $s=0$). These are matrix spectral-norm statements, not errors for a particular gain vector, receiver trajectory, or FER. At $r=0$ the block closes exactly; at $r=1$ it is singular.

The exact finite-$N$ kernel, with removable points interpreted by the finite sum, is

\[
D_N(\delta)=e^{+\pi i(N-1)\delta/N}
\frac{\operatorname{sinc}(\delta)}{\operatorname{sinc}(\delta/N)},\qquad
\operatorname{sinc}(x)=\frac{\sin(\pi x)}{\pi x}.
\]

It is $N$-periodic and equals 1 at $\delta\in N\mathbb Z$. For fixed noninteger Doppler-bin separation $\delta$, $D_N(\delta)\to e^{+\pi i\delta}\operatorname{sinc}(\delta)$ and its magnitude tends to the positive $|\operatorname{sinc}(\delta)|$. A fixed nonzero integer $\delta$ instead gives zero once $N>|\delta|$. This fixed-bin limit must not be substituted for a regime $\delta=N\alpha$ with fixed $\alpha\notin\mathbb Z$, where $|D_N(N\alpha)|\le [N|\sin(\pi\alpha)|]^{-1}$.

### Corollary proof

In $U_i^HU_j$, the unitary outer $A$ cancels inside the trace. Unequal delays leave a weighted nonidentity cyclic shift, which has zero diagonal and trace. At equal delay, the same CPP factor cancels and the inner product is $S_l^HD_{\nu_j-\nu_i}S_l$. This is diagonal, with trace $ND_N(\nu_j-\nu_i)$. Conjugating it by $A$ makes each AF-coordinate diagonal entry its mean because every $|A_{kn}|^2=1/N$. For the doublet, diagonalize the Hermitian $R$; its two eigenvalues are $1\pm r$. Any scalar center has maximum distance at least half their separation, $r$, and their midpoint 1 attains it. Multiplying by $s\ge0$ yields the $\Gamma=sR$ formula. The positive-sign finite geometric sum gives the displayed Dirichlet expression and fixed-bin limit. ∎

## Manuscript-safe interpretation

This theorem tests compatibility of a particular scalar contraction with a declared covariance family and the frozen physical path operators. It neither proves a new inference convergence result nor predicts FER, decoder behavior, usefulness of retuning, or universal need for CSTATE. The distinct-delay pre-CSTATE geometry removes equal-delay coherence in normalized $R$, but nonuniform AF-coordinate variances can leave cross-delay terms in $\Gamma(V)$. The same-delay doublet lower bound measures normalized matrix mismatch; its unnormalized covariance-weighted version is $s|D_N(\delta)|$ only under the stated AF-diagonal block condition. Finite source-bound tests corroborate selected cases; the derivation above supplies the universal quantifiers.
