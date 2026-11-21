```latex
\section{Projected symbol uncertainty and exact support exchange}
\label{sec:projected-uncertainty}

% Requires amsmath, amssymb, and amsthm.
\theoremstyle{plain}
\newtheorem{afdmprop}{Proposition}
\newtheorem{afdmcor}{Corollary}
\theoremstyle{remark}
\newtheorem*{afdmremark}{Remark}

\subsection{Notation and standing assumptions}

\begin{center}
\small
\begin{tabular}{@{}p{.31\linewidth}p{.63\linewidth}@{}}
\hline
Symbol & Meaning \\ \hline
$N,L,c_1,c_2$ &
Block length, maximum integer delay, and the two AFDM chirp parameters. \\
$\mathcal A,F,\Lambda_c$ &
Unitary discrete affine Fourier transform (DAFT), unitary discrete Fourier
transform (DFT), and diagonal chirp matrix. \\
$x,\bar x,\epsilon,V$ &
Transmitted affine-frequency symbol vector, its frozen soft mean, its error
$x-\bar x$, and the working covariance of that error. \\
$v,u,E,\lambda$ &
Symbol variances, their sum, soft-mean energy $\|\bar x\|^2$, and gain-fit
ridge $\lambda=\sigma^2>0$. \\
$\ell_i,\nu_i,U_i,\phi_i$ &
Delay in samples, Doppler in bins, symbol-to-time path operator, and
mean-response column $\phi_i=U_i\bar x$. \\
$Y,S,B_S,h$ &
Time-domain observation, a labeled support, its mean-response matrix,
and its complex path gains. \\
$D_N,\widehat v$ &
Positive-sign normalized Doppler kernel and negative-sign unnormalized
DFT of the variance vector. \\
$\Gamma_{\rm F},\Gamma_{\rm C},\Gamma_{\rm D}$ &
Full projected uncertainty, its co-delay blocks (\textsc{Codelay}),
and its scalar diagonal. \\
$Q_{g,S},b_S,\hat h_{g,S},J_g^*(S)$ &
Normal matrix, right-hand side, fitted gains, and minimum score on $S$
for uncertainty model $g$. Lower scores are preferred. \\
$j,c,w,\delta,\zeta$ &
Retained anchor, co-delay candidate, missing-delay candidate,
spacing $\nu_c-\nu_j$, and coherence magnitude $|D_N(\delta)|$. \\
$s,p,g_+,g_-$ &
Phase-aligned unit sum and contrast directions of a pair, and their
uncertainty penalties. \\
$P,G_\nu,M,H_{\rm fft}$ &
Number of occupied slots, grid Dopplers per delay, bank size
$(L+1)G_\nu$, and padded correlation-transform length. \\
\hline
\end{tabular}
\end{center}

Use time and symbol indices $0,\ldots,N-1$. Assume $N$ is even,
$0\le L<N$, the chirp-periodic prefix (CPP) has length at least $L$,
and $a_1=2Nc_1\in\mathbb Z$. The frozen transform conventions are
\[
 F_{kt}=N^{-1/2}e^{-2\pi\mathrm{i}kt/N},\qquad
 (\Lambda_c)_{tt}=e^{2\pi\mathrm{i}ct^2},\qquad
 \mathcal A=\Lambda_{c_2}F\Lambda_{c_1}.
\]
The synthesis matrix is $\mathcal A^H$. Let
$(T_\ell z)[t]=z[(t-\ell)\bmod N]$ and
$(M_\nu z)[t]=e^{2\pi\mathrm{i}\nu t/N}z[t]$.
For a wrapped index $k=t-\ell<0$, the frozen CPP multiplier is
$e^{2\pi\mathrm{i}c_1(N^2+2Nk)}=1$, since
$c_1(N^2+2Nk)=a_1N/2+a_1k\in\mathbb Z$. Thus
\[
 U_i=M_{\nu_i}T_{\ell_i}\mathcal A^H,\qquad
 B_S=[\,\phi_i\,]_{i\in S},\qquad \phi_i=U_i\bar x .
\]
All three factors of $U_i$ are unitary. A physical observation has the form
$Y=\sum_i h_i^{\rm true}U_ix+n$, with noise variance $\sigma^2$ per
time sample. All scores below condition on the same observed $Y$ and the
same frozen soft information.

Write $x=x_{\rm pilot}+x_{\rm data}$ and
$\bar x=x_{\rm pilot}+\mu$, where $\mu$ is the data mean supplied by the
symbol a posteriori probabilities (APPs). The APP second-order closure is
\[
 \mathbb E_{\rm app}\epsilon=0,\qquad
 \mathbb E_{\rm app}[\epsilon\epsilon^H]=V=\operatorname{diag}(v),
 \qquad v_n\ge0,\qquad u=\sum_n v_n,\qquad E=\|\bar x\|^2.
\]
This is a working symbol law at a frozen receiver state. In particular,
it supplies no independence assumption about the detection residual used
to produce that state.

For path labels on any trial support, define
\[
 \begin{split}
 (\Gamma_{\rm F})_{ij}
   &=\operatorname{tr}(U_i^HU_jV),\\
 (\Gamma_{\rm C})_{ij}
   &=\mathbf 1_{\{\ell_i=\ell_j\}}(\Gamma_{\rm F})_{ij},\qquad
 \Gamma_{\rm D}=uI .
 \end{split}
\]
The first identity follows by expanding
$\mathbb E_{\rm app}[(U_i\epsilon)^H(U_j\epsilon)]$. In particular,
$\Gamma_{\rm F}\succeq0$ because its quadratic form at $h$ is
$\mathbb E_{\rm app}\|\sum_i h_iU_i\epsilon\|^2$.
The co-delay matrix is positive semidefinite because it is a direct sum
of principal blocks of $\Gamma_{\rm F}$.

For $g\in\{{\rm D},{\rm C},{\rm F}\}$, minimize
\[
 J_g(h;S)=\|Y-B_Sh\|^2+h^H(\Gamma_{g,S}+\lambda I)h .
\]
For the full model the first two terms after expanding this expression,
apart from the ridge, are exactly the APP-averaged squared residual.
Put
\[
 Q_{g,S}=B_S^HB_S+\Gamma_{g,S}+\lambda I,\qquad b_S=B_S^HY .
\]
Since $Q_{g,S}\succeq\lambda I$, completing the complex quadratic gives
\begin{align}
 \hat h_{g,S}&=Q_{g,S}^{-1}b_S, &
 J_g^*(S)&=\|Y\|^2-b_S^HQ_{g,S}^{-1}b_S, \label{eq:af-profile}\\
 J_g(h;S)-J_g^*(S)
   &=(h-\hat h_{g,S})^HQ_{g,S}(h-\hat h_{g,S}). \label{eq:af-square}
\end{align}
The same notation applies to any explicitly specified positive semidefinite
uncertainty penalty.

\subsection{The co-delay block}

\begin{afdmprop}[Co-delay Dirichlet structure and cross-delay error]
\label{prop:af-block}
Under the standing AFDM and APP assumptions, let
\[
 D_N(z)=\frac1N\sum_{t=0}^{N-1}e^{2\pi\mathrm{i}zt/N},
 \qquad
 \widehat v[k]=\sum_{n=0}^{N-1}v_ne^{-2\pi\mathrm{i}nk/N}.
\]
For $d=\ell_j-\ell_i$ and $z=\nu_j-\nu_i+a_1d$,
\begin{equation}
 (\Gamma_{\rm F})_{ij}
 =e^{2\pi\mathrm{i}c_1(\ell_i^2-\ell_j^2)}
    D_N(z)\widehat v[d\bmod N].                       \label{eq:af-full}
\end{equation}
In particular, for every $v\ge0$ the diagonal is $u$, and every co-delay
entry equals $uD_N(\nu_j-\nu_i)$. The error
$\mathcal E=\Gamma_{\rm F}-\Gamma_{\rm C}$ vanishes on those blocks. For
$d\ne0$, with $\rho_z=\operatorname{dist}(z,N\mathbb Z)$,
\begin{equation}
 |\mathcal E_{ij}|
 \le
 \min\!\left\{1,\frac{1}{N\sin(\pi\rho_z/N)}\right\}
 \min\!\left\{u,\left\|v-\frac uN\mathbf1\right\|_1\right\},       \label{eq:af-cross-bound}
\end{equation}
where the first minimum is $1$ at $\rho_z=0$.
\end{afdmprop}

\begin{proof}
The $n$th synthesis column at time $k$ is
\[
 (\mathcal A^H)_{kn}
 =N^{-1/2}e^{-2\pi\mathrm{i}c_1k^2}
            e^{2\pi\mathrm{i}kn/N}e^{-2\pi\mathrm{i}c_2n^2}.
\]
It is periodic in the integer $k$ with period $N$, by the same
integrality calculation as for the CPP. We may therefore substitute
$k=t-\ell_i$ without reducing the quadratic phase modulo $N$.
Multiplying the conjugate of the $i$th path sample by the $j$th gives
\[
 \overline{(U_i)_{tn}}(U_j)_{tn}
 =\frac1N e^{2\pi\mathrm{i}c_1(\ell_i^2-\ell_j^2)}
           e^{2\pi\mathrm{i}zt/N}e^{-2\pi\mathrm{i}nd/N}.
\]
The $c_2$ phases cancel. Summing over $t$ and then over $n$ with weights
$v_n$ proves \eqref{eq:af-full}. At $d=0$, $\widehat v[0]=u$.
At $i=j$ also $D_N(0)=1$.

For $d\ne0$, the delay range ensures $d\not\equiv0\pmod N$.
The DFT of a constant vanishes at this index, so the triangle inequality
gives both $|\widehat v[d]|\le u$ and
$|\widehat v[d]|\le\|v-(u/N)\mathbf1\|_1$. The defining average gives
$|D_N(z)|\le1$. For $z\notin N\mathbb Z$, the finite geometric series gives
\[
 |D_N(z)|=\frac{|\sin(\pi z)|}{N|\sin(\pi z/N)|}
 \le\frac1{N\sin(\pi\rho_z/N)} .
\]
At $z\in N\mathbb Z$ all terms of the average equal one. Multiplication
of the two bounds proves \eqref{eq:af-cross-bound}.
\end{proof}

For constant variance, all cross-delay entries vanish. For integer
Doppler difference, the kernel vanishes precisely when
$z\in\mathbb Z\setminus N\mathbb Z$. Resonance matters on the frozen grid:
$a_1=5$, $d=1$ and $\nu_j-\nu_i=-5$ give
$|\mathcal E_{ij}|=|\widehat v[1]|$. By contrast, for $N=1024$,
$|\nu_j-\nu_i|\le6$ and $|d|=2,10,102$, the distance of the interval
$5d+[-6,6]$ from $1024\mathbb Z$ is respectively $4,44,504$.
The corresponding kernel bounds are below $0.080,0.0073,0.00098$.

\begin{afdmremark}[Fractional delay]
Replace $T_\ell$ by a specified unitary fractional-delay operator $T_\tau$.
Unitarity still gives $(\Gamma_{\rm F})_{ii}=\operatorname{tr}V=u$.
At a common fractional delay, however, the weight of the $n$th symbol
at time $t$ is $|(T_\tau\mathcal A^H)_{tn}|^2$. Unitarity fixes its
sum over $t$ but need not make it constant in $t$. The following criterion
gives exactly the additional property required for the co-delay formula.
Equation~\eqref{eq:af-full} for unequal delays also used the explicit
integer translation of the quadratic chirp.
\end{afdmremark}

\begin{afdmremark}[Which part is modulation independent]
Let $W$ be any complete unitary synthesis matrix on the same block and
take $U_i=M_{\nu_i}T_{\ell_i}W$. For $V=(u/N)I$, cyclic invariance of
the trace cancels $W$. Different integer shifts have no common diagonal
in the relative shift, whereas equal shifts give the trace of
$M_{\nu_j-\nu_i}$. Thus
\[
 (\Gamma_{\rm F})_{ij}
 =u\,\mathbf1_{\{\ell_i=\ell_j\}}D_N(\nu_j-\nu_i).
\]
For arbitrary diagonal $V$ and common delay $\ell$, the entry instead is
\[
 \sum_n v_n\sum_t |(T_\ell W)_{tn}|^2
             e^{2\pi\mathrm{i}(\nu_j-\nu_i)t/N}.
\]
It equals $uD_N(\nu_j-\nu_i)$ for every $v\ge0$ and every Doppler
difference if and only if $|W_{tn}|^2=1/N$ for all $t,n$.
Constant magnitude proves sufficiency. For necessity, select one
symbol with $v_n=1$ and set all other variances to zero. Equality at the
$N$ integer Doppler frequencies determines that column's time-energy
sequence by inverse DFT. It must be the uniform sequence. Translation
only permutes its entries.

Both AFDM and orthogonal frequency-division multiplexing (OFDM) have
time-flat synthesis columns. For ordinary OFDM, setting $c_1=c_2=0$
in \eqref{eq:af-full} gives $D_N(\nu_j-\nu_i)\widehat v[d]$:
there is no delay-dependent Doppler shift. For rectangular-pulse
orthogonal time-frequency space (OTFS) synthesis, write $N=m_0k_0$.
A column belonging to delay row $r$ has energy $1/k_0$ at times
$t\equiv r\pmod{m_0}$ and zero elsewhere. If $w_r$ is the sum of the
symbol variances in that row, summing those $k_0$ time samples gives
the common-delay entry
\[
 D_{k_0}(\delta)\sum_{r=0}^{m_0-1}
 w_r e^{2\pi\mathrm{i}\delta((r+\ell)\bmod m_0)/N}.
\]
The row totals can therefore matter even at fixed $u$. Among these three
specified syntheses, the shift $a_1d$ in \eqref{eq:af-full} is the
AFDM chirp contribution. The comparison makes no uniqueness claim over
all possible chirped bases.
\end{afdmremark}

\subsection{One-step support acquisition}

\begin{afdmprop}[Paired score, path splitting, and admission window]
\label{prop:af-split}
Fix $Y,\bar x,v$ and $\lambda>0$. Use the same deletion slot for both
candidates. The score identity in part (a) holds for any realized
observation. Parts (b) and (c) describe the profile at and near
coincidence. Part (d) gives a sufficient power-ratio region under the
additional residual and geometry assumptions stated there.
\end{afdmprop}

\paragraph{(a) Exact score difference.}
Let the surviving support $S$ have distinct delays. Candidate $c$ shares
the delay of exactly one survivor $j$, and $\ell_w$ is absent from $S$.
Write $S_c=S\cup\{c\}$, $S_w=S\cup\{w\}$, and
\[
 m_g=J_g^*(S_w)-J_g^*(S_c),\qquad g\in\{{\rm D},{\rm C}\}.
\]
A positive margin favors the repeat. Abbreviate
$\hat h_g=\hat h_{g,S_c}$ and define
\begin{align}
 A&=2\operatorname{Re}
       \{\overline{\hat h_{{\rm D},j}}
              (\Gamma_{\rm C})_{jc}\hat h_{{\rm D},c}\},\\
 B_{\rm fit}&=(\hat h_{\rm C}-\hat h_{\rm D})^H
                  Q_{{\rm C},S_c}(\hat h_{\rm C}-\hat h_{\rm D}),\\
 K&=J_{\rm C}^*(S_c)-J_{\rm D}^*(S_c).
\end{align}
Then
\begin{equation}
 K=A-B_{\rm fit}=m_{\rm D}-m_{\rm C},\qquad B_{\rm fit}\ge0 .
 \label{eq:af-score}
\end{equation}
If $m_{\rm D}>0$, restoring the co-delay block strictly reverses this
pairwise preference if and only if $K>m_{\rm D}$. Equality is a tie.

\begin{proof}
On $S_w$ all delays are distinct, so
$\Gamma_{{\rm C},S_w}=\Gamma_{{\rm D},S_w}=uI$ and the profiles agree.
On $S_c$ their difference consists of just the $(j,c)$ and $(c,j)$
entries. At the scalar optimizer the change of objective is exactly $A$.
Refitting with the co-delay normal matrix recovers exactly $B_{\rm fit}$
by \eqref{eq:af-square}. This proves both identities. Positive
definiteness gives $B_{\rm fit}\ge0$. Finally $m_{\rm C}=m_{\rm D}-K$,
which gives the strict and tie cases. In particular $A>m_{\rm D}$ is
necessary for reversal but refitting can make it insufficient.
\end{proof}

\paragraph{(b) Coincidence and the equal split.}
Fix $u>0$, the other atoms and $\nu_j$, and let $\delta\to0$.
Let $H_0$ be the aggregate $\hat h_{{\rm D},j}+\hat h_{{\rm D},c}$ of
the \emph{duplicated scalar fit at coincidence}. Then
\begin{equation}
 \hat h_{{\rm D},j},\hat h_{{\rm D},c}\longrightarrow H_0/2,
 \qquad
 A\longrightarrow \frac u2|H_0|^2 .                    \label{eq:af-A-limit}
\end{equation}
The limit is positive precisely when $H_0\ne0$.

\begin{proof}
At coincidence $\phi_c=\phi_j$. Given $H=h_j+h_c$, the data term
depends only on $H$, including when the other gains are fitted jointly.
The pair's scalar penalty, including its coordinate ridge, is
\[
 (u+\lambda)(|h_j|^2+|h_c|^2)
 =\frac{u+\lambda}{2}\bigl(|H|^2+|h_j-h_c|^2\bigr).
\]
Its unique minimum at fixed $H$ occurs at $h_j=h_c=H/2$.
The columns depend continuously on Doppler, and the inverse normal
matrix is continuous because its smallest eigenvalue is at least
$\lambda$. The fitted gains therefore converge to the coincident fit.
Substitute their limits and $(\Gamma_{\rm C})_{jc}\to u$ in $A$.
This proves \eqref{eq:af-A-limit}. An entering singleton fit generally
has a different gain from $H_0$, since it pays a different aggregate
penalty.
\end{proof}

\paragraph{(c) Sum-mode reward and finite-spacing contrast penalty.}
Rephase the second column and its gain reciprocally so that the
co-delay uncertainty entry is $u\zeta$. In these coordinates put
$s=(1,1)^T/\sqrt2$ and $p=(1,-1)^T/\sqrt2$, extended by zero outside
the pair. Consider a pair penalty with eigenvalues $g_+,g_-\ge0$ along
$s,p$. The exact co-delay values are $u(1+\zeta),u(1-\zeta)$, by
diagonalizing the $2\times2$ block with diagonal $u$ and off-diagonal
$u\zeta$. On the equal split at aggregate $H$, replacing the exact
uncertainty penalty changes its cost by a saving of
\begin{equation}
 \frac{u(1+\zeta)-g_+}{2}|H|^2 .                       \label{eq:af-fixed-H}
\end{equation}

At coincidence let $Q_0,\hat h_0$ denote the normal matrix and fit of
the parent support with singleton uncertainty $u$ at $j$. Assume the
remaining penalty block is preserved, each child has the parent's
uncertainty coupling to every other retained atom, and the whole child
penalty is positive semidefinite. These conditions include an isolated
pair. With $e_j$ the parent coordinate vector, set
\[
 a=u+\lambda-\frac{g_++\lambda}{2}.
\]
The fully profiled split reward is
\begin{equation}
 J_{\rm parent}^*-J_{\rm pair}^*
 =\frac{a|\hat h_{0,j}|^2}
        {1-a\,e_j^HQ_0^{-1}e_j}.                       \label{eq:af-profile-split}
\end{equation}
It is independent of $g_-$. At any fixed spacing, on a fixed trial
support with normal matrix $Q_{\rm pair}$ and fit $\hat h_{\rm pair}$,
adding $rpp^H$ to its penalty, $r\ge0$, raises its profiled score by
\begin{equation}
 L(r)=\frac{r|p^H\hat h_{\rm pair}|^2}
               {1+r\,p^HQ_{\rm pair}^{-1}p}.             \label{eq:af-dose}
\end{equation}
Equation~\eqref{eq:af-dose} allows the data Gram to couple the pair to
the rest of the support.

\begin{proof}
In the pair coordinates $s^Hh=H/\sqrt2$. The uncertainty plus ridge
cost within the pair is
\[
 \frac{g_++\lambda}{2}|H|^2+(g_-+\lambda)|p^Hh|^2.
\]
This proves \eqref{eq:af-fixed-H} on setting $p^Hh=0$ and comparing
uncertainty costs. At coincidence all data and external coupling terms
depend only on $H$. Since $g_-+\lambda>0$, profiling over contrast sets
$p^Hh=0$. The resulting normal matrix in parent coordinates is exactly
$Q_0-ae_je_j^H$, with the same right-hand side as the parent. It is
positive definite: it is the child quadratic restricted to the injective
map that sends $H$ to $(H/2,H/2)$. Congruence by $Q_0^{-1/2}$ now gives
$1-ae_j^HQ_0^{-1}e_j>0$.

For a positive definite $Q$ and a real $t$ with
$1+tq^HQ^{-1}q\ne0$, the Sherman--Morrison rank-one inverse identity is
\[
 (Q+tqq^H)^{-1}
 =Q^{-1}-\frac{tQ^{-1}qq^HQ^{-1}}{1+tq^HQ^{-1}q}.
\]
Multiplication by $Q+tqq^H$ verifies the identity. Apply it in
\eqref{eq:af-profile} with $(t,q)=(-a,e_j)$, then with $(t,q)=(r,p)$.
The second denominator is at least one. This gives
\eqref{eq:af-profile-split} and \eqref{eq:af-dose} with the displayed
signs.
\end{proof}

For scalar uncertainty $a=(u+\lambda)/2$. For exact sum curvature
$g_+=2u$, only $a=\lambda/2$ remains. Indeed
$Q_0\succeq\lambda I$ bounds the denominator in
\eqref{eq:af-profile-split} below by $1/2$ in the latter case. For a fixed
parent problem $\hat h_0$ stays bounded as $\lambda\downarrow0$: the null
space of the unregularized normal matrix is contained in $\ker B_S$,
so $b_S=B_S^HY$ has zero projection there. Diagonalizing that fixed
normal matrix proves boundedness on its remaining, positive eigenvalues.
The residual duplicate reward is consequently $O(\lambda)$.
For fixed $\lambda>0$ the duplicate formula is also the limit of
continuous columns and continuous penalties. At finite spacing,
\eqref{eq:af-dose} is strictly positive exactly when $r>0$ and the
original fit has nonzero contrast.

The associated pairwise admissibility conditions for preserving exact
sum curvature and imposing a uniform contrast floor are
\[
 g_+=u(1+\zeta),\qquad g_-\ge c_0u
 \quad\text{near }\zeta=1,\qquad c_0>0
 \text{ independent of spacing}.
\]
The scalar model misses the first condition near coincidence, and the
exact co-delay block misses the second. For $1-\zeta<1/2$, let
$\Pi_{\rm lo}=pp^H$. Adding $u\Pi_{\rm lo}$ to the exact pair gives
$g_-=u(2-\zeta)$. Replacing just its low eigenvalue by $u$
(the \textsc{C-hi} arm) gives $g_-=u$. Both retain the exact $g_+$.
They therefore share the co-delay acquisition score at coincidence
under the coupling premise above. Equation~\eqref{eq:af-dose}
quantifies their possible departures at finite spacing. For a larger
co-delay block the corresponding sufficient construction is to preserve
the exact operator on its designated invariant sum subspace and bound
the restriction to its orthogonal contrast subspace below by $c_0uI$.
This is a property of the support on which the subspaces were constructed.

\paragraph{(d) A sufficient finite-spacing window under the Berkson premise.}
Assume $E>0$ and put $T=E+u+\lambda$. First isolate the anchor in the
retained normal equations: all other retained coordinates are decoupled
from it and from the two trial candidates, or have already been removed
with exactly that effect. Use the original complex phases and define
\[
 \kappa=\phi_j^H\phi_c/E,\qquad D=D_N(\delta),\qquad
 q_{\rm D}=E\kappa,\qquad q_{\rm C}=E\kappa+uD .
\]
Here $\kappa$ is the coherence of this frame's mean waveform, whereas
$D$ is the operator coherence. Write $b_i=\phi_i^HY$ for the scalar
right-hand side of path $i$. If $b_c=\bar\kappa b_j$, the profiled
addition gain of $c$ on this isolated anchor is
\begin{equation}
 \mathcal G_g(c)
 =\frac{|T\kappa-q_g|^2\,|b_j/T|^2}{T-|q_g|^2/T},
 \qquad g\in\{{\rm D},{\rm C}\}.                         \label{eq:af-admission}
\end{equation}

For the power-ratio corollary impose the following additional premises.
The missing response is orthogonal to both mean columns $\phi_j,\phi_c$,
its delay is distinct, and $\kappa=D$. Let $H_s,H_w\ne0$ be the
physical gains of the strong and missing paths. Use the Berkson
working premise that the centered soft-symbol error is independent of
the omitted-path residual driving the soft detector. The ideal comparison
uses the signal projections
\begin{equation}
 b_j=EH_s,\qquad b_c=\bar D EH_s,\qquad b_w=EH_w.        \label{eq:af-ideal-projections}
\end{equation}
For a realized observation this requires zero remaining projections
on the three columns. A second precise interpretation is to profile
the \emph{residual-averaged quadratic} when the remaining projections
have conditional mean zero given the frozen design and true gains.

Set $r_w=|H_w|^2/|H_s|^2$ and define
\begin{align}
 \theta_{\rm D}(\zeta)
 &=\frac{\zeta^2(u+\lambda)^2}{T^2-\zeta^2E^2},&
 \theta_{\rm C}(\zeta)
 &=\frac{\zeta^2\lambda^2}{T^2-\zeta^2(E+u)^2}.
 \label{eq:af-window}
\end{align}
Under these premises the open window
\[
             \theta_{\rm C}(\zeta)<r_w<\theta_{\rm D}(\zeta)
\]
is a sufficient inner region of scalar acquisition failure: in the
specified pairwise comparison the scalar score prefers the repeat, and
the co-delay score prefers the missing path.

\begin{proof}
The two-column normal matrix has diagonal $T$ and upper off-diagonal
$q_g$. Eliminating the anchor gives candidate innovation
$b_c-\bar q_g b_j/T$ and positive Schur complement $T-|q_g|^2/T$.
Minimizing the remaining scalar quadratic gives the squared modulus of
the innovation divided by that complement. Substitution of
$b_c=\bar\kappa b_j$ proves \eqref{eq:af-admission}.

Under \eqref{eq:af-ideal-projections}, let
$(a_{\rm D},t_{\rm D})=(u+\lambda,E)$ and
$(a_{\rm C},t_{\rm C})=(\lambda,E+u)$.
Then $q_g=t_gD$ and $T-t_g=a_g$, giving
\[
 \mathcal G_g(c)=\frac{E^2|H_s|^2}{T}
                  \frac{\zeta^2a_g^2}{T^2-\zeta^2t_g^2}.
\]
The missing column has no coupling to the surviving anchor in either
normal matrix, so $\mathcal G_g(w)=E^2|H_w|^2/T$.
Both denominators in \eqref{eq:af-window} are positive. Cancelling
$E^2|H_s|^2/T$ gives the stated strict inequalities. For the averaged
quadratic, writing $Y=Y_{\rm sig}+\eta$ and expanding the squared norm
shows that zero conditional mean projections make the linear term in
$h$ the same as for $Y_{\rm sig}$. The remaining change is independent
of $h$ and of the trial support. This proves the specified averaged
interpretation as well.

For $0<\zeta\le1$, the function
$(T-t)^2/(T^2-\zeta^2t^2)$ is strictly decreasing on $0\le t<T$:
its derivative is
$-2T(T-t)(T-\zeta^2t)/(T^2-\zeta^2t^2)^2$.
Thus $\theta_{\rm C}<\theta_{\rm D}$ for $u>0$; for $u=0$ the window
is empty. Each endpoint is a tie in its respective score. In terms of
$R=1/r_w$ the window is
\[
 \frac{T^2-\zeta^2 E^2}{\zeta^2(u+\lambda)^2}
 <R<
 \frac{T^2-\zeta^2(E+u)^2}{\zeta^2\lambda^2}.
\]
At $\zeta=1$ it reduces to
$1+2E/(u+\lambda)<R<1+2(E+u)/\lambda$.
The scalar threshold increases with $\zeta^2$, since its derivative
with respect to $\zeta^2$ is
$(u+\lambda)^2T^2/(T^2-\zeta^2E^2)^2$. Its upper envelope is therefore
$(u+\lambda)/(2E+u+\lambda)$. At an integer spacing
$\delta\not\equiv0\pmod N$, $\zeta=0$ and both thresholds vanish.
\end{proof}

\textbf{Gap.} In a realized decoder-conditioned frame, Berkson
independence alone does not give \eqref{eq:af-ideal-projections}.
For example, even a centered independent noise projection can have
nonzero squared modulus. Also, a detector fitted without the missing
path can absorb part of its response into the soft symbols, violating
the working independence premise itself. Then $b_w-EH_w$ and
$b_c-\bar\kappa b_j$ enter the innovations before taking squared
moduli. A framewise guarantee requires their joint control, and a
global accepted edit must additionally beat other legal candidates and
the incumbent. The open window supplies neither a receiver-wide flip
boundary nor a necessary condition for a scalar phantom.

\subsection{Fixed-prior contrast curvature}

\begin{afdmcor}[Contrast curvature and marginal variance at a fixed prior]
\label{cor:af-prior}
Freeze a gain-prior precision $\mathcal P\succ0$, a noise precision
$\beta>0$, a dictionary $B_S$, and a positive semidefinite uncertainty
penalty $\Gamma$. The Gaussian estimation step has precision
$\mathcal K=\mathcal P+\beta(B_S^HB_S+\Gamma)$ and covariance
$\Sigma=\mathcal K^{-1}$. For the phase-aligned exact co-delay pair,
\[
 p^H\mathcal Kp
  =p^H\mathcal Pp+\beta\|B_Sp\|^2+\beta u(1-\zeta).
\]
Both nonprior terms vanish at coincidence. If $\mathcal P=\alpha I$
with $\alpha>0$, the contrast marginal variance at coincidence is
exactly $1/\alpha$. In contrast, a pair penalty $g_-\ge c_0u$ contributes
at least $\beta c_0u$ of uncertainty curvature. More generally, adding
$rpp^H$ to $\Gamma$ changes the marginal variance by the exact law
\begin{equation}
 v_p=p^H\Sigma p
 \quad\longmapsto\quad
 \frac{v_p}{1+\beta r v_p},\qquad r\ge0 .                \label{eq:af-variance}
\end{equation}
\end{afdmcor}

\begin{proof}
Take the quadratic form of $\mathcal K$ on $p$ and use the pair
eigenvalue from Proposition~\ref{prop:af-split}(c).
At exact coincidence $B_Sp=0$ because the columns agree.
Also $p^H\Gamma p=0$ for the exact uncertainty. Positive semidefiniteness
then gives $\Gamma p=0$ by taking its positive semidefinite square root.
Consequently $\mathcal Kp=\alpha p$ for the isotropic prior, which
justifies the marginal variance even in the presence of other atoms.
For a general prior, the marginal variance need not be the reciprocal
of the directional precision. Apply the rank-one inverse identity to
$\mathcal K+\beta rpp^H$ and take its quadratic form on $p$:
$v_p-\beta r v_p^2/(1+\beta rv_p)=v_p/(1+\beta rv_p)$.
\end{proof}

A smaller fixed-prior variance implies no ordering of automatic relevance
determination (ARD) updates, channel error, or frame error rate (FER).
For example, an iterative sparse Bayesian estimator updates the coordinate
prior variances using $\Sigma_{ii}+|\hat h_i^{\rm post}|^2$. A contrast
ridge can change both summands, the next noise precision, and the set of
coordinates surviving pruning. Equation~\eqref{eq:af-variance} compares
one marginal at a common prior and dictionary.

\subsection{Compact evaluation of every exchange}

\begin{afdmprop}[Exact compact exchange and arithmetic cost]
\label{prop:af-exchange}
Freeze $Y,\bar x,v,\lambda$, the $P$ occupied slots, and a rectangular
bank of $M=(L+1)G_\nu$ candidates. Use an uncertainty model whose entries
on a trial are the corresponding principal submatrix of the labeled
augmented model; $\Gamma_{\rm F},\Gamma_{\rm C},\Gamma_{\rm D}$ each
satisfy this condition. An appended coordinate has its own ridge even
when its physical column duplicates an existing column.

For the entering support $S$, suppress the fixed scorer subscript and
write $W_Q=Q_S^{-1}$, $\hat h= W_Qb_S$. For each bank atom $a$ put
\[
 \begin{aligned}
 k_a&=B_S^H\phi_a+\Gamma_{S,a},&
 b_a&=\phi_a^HY,&
 t_a&=W_Qk_a,\\
 d_a&=E+u+\lambda-k_a^Ht_a,&
 z_a&=b_a-k_a^H\hat h .
 \end{aligned}
\]
For a deletion of any entering slot $i$, the direct Cholesky profile on
the replacement support equals
\begin{equation}
 J^*(S-i+a)
 =
 J^*(S)-\frac{|z_a|^2}{d_a}
 +\frac{|\hat h_i-(t_a)_i z_a/d_a|^2}
        {(W_Q)_{ii}+|(t_a)_i|^2/d_a}.                   \label{eq:af-exchange}
\end{equation}
The equality holds in exact arithmetic for every slot and candidate
before the legality mask. It does not extend by this argument to a
spectral projector recomputed separately on every replacement support.
\end{afdmprop}

\begin{proof}
The augmented normal matrix and right-hand side are
\[
 Q_+=\begin{bmatrix}Q_S&k_a\\ k_a^H&E+u+\lambda\end{bmatrix},
 \qquad b_+=\begin{bmatrix}b_S\\ b_a\end{bmatrix}.
\]
The candidate diagonal follows from unitarity, $\|\phi_a\|^2=E$,
and $\Gamma_{aa}=u$. Since $Q_+\succeq\lambda I$, its Schur complement
$d_a$ is positive. Eliminating the old coordinates leaves the scalar
quadratic $J^*(S)-2\operatorname{Re}(\bar h_a z_a)+d_a|h_a|^2$.
Its minimizer is $z_a/d_a$. Back substitution and the block inverse give
\[
 J_+^*=J^*(S)-|z_a|^2/d_a,\qquad
 \hat h_{+,S}=\hat h-t_a z_a/d_a,\qquad
 (Q_+^{-1})_{S,S}=W_Q+t_at_a^H/d_a .
\]

Deleting $i$ means imposing $e_i^Hh=0$ in this augmented problem.
By \eqref{eq:af-square}, its cost increase is the minimum of
$\xi^HQ_+\xi$ subject to $e_i^H\xi=-\hat h_{+,i}$.
Cauchy--Schwarz applied to $Q_+^{-1/2}e_i$ and $Q_+^{1/2}\xi$ gives
the lower bound $|\hat h_{+,i}|^2/(Q_+^{-1})_{ii}$. It is attained at
$\xi=-Q_+^{-1}e_i\hat h_{+,i}/(Q_+^{-1})_{ii}$.
Substitution proves \eqref{eq:af-exchange}. The remaining variables
have exactly the normal equations of $S-i+a$ by the principal-submatrix
premise. Factoring those equations by Cholesky therefore gives the same
profile. This also proves equality with the E-1 calculation that deletes
$i$ first and then takes the candidate Schur complement.
\end{proof}

\paragraph{Computing the fields and counting operations.}
Let $x_{\rm t}=\mathcal A^H\bar x$. On $-L\le k<N$ define
\[
 x_{\rm ext}[k]=
 \begin{cases}
 x_{\rm t}[k],&k\ge0,\\
 e^{2\pi\mathrm{i}c_1(N^2+2Nk)}x_{\rm t}[k+N],&k<0.
 \end{cases}
\]
The field required for any $N$-vector $y$ is
\[
 \mathcal F_y(\ell,\nu)
 =\sum_{t=0}^{N-1}\overline{x_{\rm ext}[t-\ell]}\,
     e^{-2\pi\mathrm{i}\nu t/N}y[t]
 =\phi_{(\ell,\nu)}^Hy .
\]
For each fixed $\nu$, convolve the demodulated $y$ with
$k\mapsto\overline{x_{\rm ext}[N-1-k]}$, indexed from $0$ to $N+L-1$.
At output index $N-1+\ell$ its $t$th summand is exactly the summand
displayed above. Zero padding to $H_{\rm fft}\ge2N+L-1$ covers the
linear convolution, so the DFT convolution theorem recovers all legal
delays without aliasing. In particular,
\[
 b_a=\mathcal F_Y(a),\qquad
 (k_a)_i=\overline{\mathcal F_{\phi_i}(a)}+\Gamma_{ia}.
\]
This proves equality of the fast fields with the entries used by the
direct profile, including for noninteger Doppler.

With an FFT-efficient $H_{\rm fft}=O(N+L)$ and ordinary dense
linear algebra, the arithmetic costs are as follows.
\begin{itemize}
\item The $P+1$ initial correlation fields cost
$O((P+1)G_\nu H_{\rm fft}\log H_{\rm fft})$. Forming the active mean
Gram and factoring the normal matrix cost $O(NP^2+P^3)$.
The initial inverse DAFT costs $O(N\log N)$.
\item Once the fields exist, multiplying $W_Q$ by the matrix
$[k_a]_a$ costs $O(P^2M)$. Column reductions and all $PM$ scalar
replacement scores cost $O(PM)$. The stored cross fields, right-hand
side field, and inverse require $O(PM+M+P^2)$ words, in addition to
active responses, FFT workspace, and any saved trace.
These are score-evaluation costs. An implementation that fully sorts
the $PM$ scores also incurs its sorting cost.
\item With the soft state and grid frozen, a single exchange changes
only the row of $[k_a]_a$ belonging to the replaced atom. The bank
right-hand sides remain fixed. Refreshing that row before a further
pass costs one field, $O(G_\nu H_{\rm fft}\log H_{\rm fft})$, plus
its uncertainty row. The implementation refits the small active system.
\item For the full model \eqref{eq:af-full} uses one variance FFT,
$O(N\log N)$, and $O(PM)$ rectangular entries. For \textsc{Codelay},
each active row has precisely $G_\nu$ same-delay bank entries. Thus
only $PG_\nu$ Dirichlet evaluations are needed for this rectangular
block, with no variance FFT. Computing $u$ costs $O(N)$ if it is not
already supplied. The frozen implementation still allocates and masks
a dense $P$-by-$M$ block, so its entry-handling cost can be $O(PM)$.
\end{itemize}
With $P=8,L=102,G_\nu=25$, this gives $M=2575$, $20{,}600$ exchange
scores per pass, and $200$ rectangular co-delay kernel evaluations.
The $200$ excludes the small active block and subsequent refits.

\begin{afdmremark}[Numerical selection]
The frozen E-1 selector excludes a candidate within $10^{-6}$ Doppler
bin of another retained atom at the same delay. Thus exact coincidence
in Proposition~\ref{prop:af-split} is an algebraic limit. The compact
wrapper falls back to the direct route when the active condition number
exceeds $10^8$ or specified numerical failures occur. Its strict
acceptance guard is a decrease exceeding $10^{-10}(1+|J_{\rm old}^*|)$;
the separate check on a proposed winner compares compact and direct
scores at $10^{-7}(1+|J_{\rm trial}^*|)$. Neither tolerance is a
uniform forward-error bound for \eqref{eq:af-exchange}.
\end{afdmremark}

\begin{afdmremark}[In-memory algebra checks]
On a 32-sample synthetic block, direct basis-column evaluation using
the frozen path operator agreed with \eqref{eq:af-full} to maximum
entrywise error $1.21\,10^{-15}u$, including a resonant cross-delay
pair. Maximum absolute discrepancies in the score decomposition,
profiled duplicate reward, finite-spacing contrast increment, and
fixed-prior marginal variance were respectively
$1.12\,10^{-16}$, $1.70\,10^{-16}$, $1.57\,10^{-16}$, and
$8.35\,10^{-17}$ or less. The isolated admission gain and the
weak-gain tie at its theoretical endpoint agreed with direct solves
to $2.50\,10^{-16}$ and $2.24\,10^{-16}$, respectively. The CPP
observation field agreed with explicit inner products to
$8.90\,10^{-17}$. Across three slots, twenty candidates, and all
three uncertainty models, the largest discrepancy between the compact
score and a direct E-1 Cholesky refit was $1.12\,10^{-16}$ over all
$180$ comparisons. These are algebra checks on synthetic inputs.
\end{afdmremark}

\begin{afdmremark}[Relation to empirical results]
Proposition~\ref{prop:af-block} identifies exactly what the co-delay
implementation retains and discards. It is consistent with the observed
zero discordant frame-error decisions in $13{,}600$ paired keys and
with the $155$ differing decoded-bit hashes among joint failures.
Neither count follows from the entrywise bound
(\texttt{res-20261118-03}).

Proposition~\ref{prop:af-split}(a,b) identifies the measured score
term that can reverse a repeated-delay addition after a fixed deletion.
The frequency with which this also changes the globally accepted action
comes from the first-step attribution and ablation experiments
(\texttt{res-20261118-01}, \texttt{res-20261017-01}).
Part (d) supplies the isolated scalar reward used in the semi-blind
replay. The forced-miss sweep supported co-delay suppression inside
the window and rejected the proposed scalar flip location and
population-curve transport. Its post hoc decomposition found attenuation
of the missing-path projection, with a direct-term shortfall also
contributing (\texttt{res-20261118-06}, \texttt{res-20261119-01}).

Proposition~\ref{prop:af-split}(c) and Corollary~\ref{cor:af-prior}
identify two different measured quantities: the acquisition reward
for duplicating a path and the estimation curvature along its unresolved
contrast. This distinction accounts for how a contrast penalty can
leave a coincident acquisition score unchanged while changing a
fixed-prior covariance. The iterative sparse Bayesian performance
ordering and the resolution loss on genuine finite-spacing doublets
remain experimental findings. The FER cost in the doublet test was
uncertain (\texttt{res-20261119-02}, \texttt{res-20261119-03},
\texttt{res-20261119-04}).

Proposition~\ref{prop:af-exchange} explains how compact and direct
implementations can evaluate the same grid objective. The rescue
fraction, slot-cap dependence, and single-core runtime advantage over
a different receiver also depend on the outer receiver and on the
tested population (\texttt{res-20261017-01}, \texttt{res-20261118-04},
\texttt{res-20261118-03}).
\end{afdmremark}
```

**Gaps**

- 命题 2(d) 的单帧推广缺少对残差投影的控制。即使软符号误差满足 Berkson 独立性，单帧噪声投影也可以非零。正文分别证明了理想投影下的成对比较，以及条件均值为零时先平均目标函数、再优化的结论。真实接收机的翻转位置仍由实测决定。
- 三个命题及固定先验推论在各自列出的前提下均已给出证明。命题 3 的精确性要求更换支撑后保留原矩阵的对应子块，因此不能直接套用于每个候选支撑都重新计算谱投影的实现。

**Numerical checks**

- 完整协方差闭式与冻结路径算子的逐列计算相比，最大误差除以总方差 \(u\) 为 \(1.21\times10^{-15}\)。
- 评分差、复制奖励、有限间隔对比方向惩罚、固定先验方差四项恒等式的最大绝对误差依次为 \(1.11\times10^{-16}\)、\(1.69\times10^{-16}\)、\(1.56\times10^{-16}\)、\(8.34\times10^{-17}\)。后面三项使用同一个秩一矩阵求逆公式。[Sherman–Morrison 公式](https://nhigham.com/2020/09/29/what-is-the-sherman-morrison-woodbury-formula/)
- 幻影候选增益和窗口端点平局的最大绝对误差分别为 \(2.50\times10^{-16}\) 和 \(2.23\times10^{-16}\)。快速相关与显式内积的最大绝对误差为 \(8.89\times10^{-17}\)。三种协方差模型共 180 个换槽评分，与直接 Cholesky 重拟合的最大绝对误差为 \(1.11\times10^{-16}\)。所有检查均在内存中完成，仓库未写入。

model: `gpt-6.2-astra`（已由本次会话元数据确认）