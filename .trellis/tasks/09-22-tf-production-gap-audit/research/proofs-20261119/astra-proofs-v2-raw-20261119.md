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
\begin{tabular}{@{}p{.30\linewidth}p{.65\linewidth}@{}}
\hline
Symbol & Meaning \\ \hline
$N,L,c_1,c_2,a_1$ &
Block length, maximum integer delay, chirp parameters, and
$a_1=2Nc_1$. \\
$\mathcal A,F,\Lambda_c$ &
Discrete affine Fourier transform (DAFT), discrete Fourier transform
(DFT), and diagonal chirp matrix. \\
$\mathsf S_\ell,M_\nu,U_i$ &
Delay with chirp-periodic prefix (CPP), Doppler modulation, and
symbol-to-time operator of path $i$. \\
$x,\bar x,\epsilon,V$ &
Transmitted symbol vector, frozen soft mean, error $x-\bar x$,
and working error covariance. \\
$v,u,E,\lambda$ &
Symbol variances, total variance $\sum_n v_n$, mean energy
$\|\bar x\|^2$, and gain-fit ridge $\sigma^2>0$. \\
$Y,S,B_S,h$ &
Time-domain observation, support of labelled coordinates,
mean-response matrix, and complex gains. \\
$\ell_i,\nu_i,\phi_i,b_i$ &
Delay, Doppler, mean response $U_i\bar x$, and projection $\phi_i^HY$. \\
$D_N,\widehat v$ &
Positive-sign normalized Doppler kernel and negative-sign
unnormalized DFT of $v$. \\
$\Gamma_{\rm F},\Gamma_{\rm C},\Gamma_{\rm D}$ &
Full projected uncertainty, its co-delay blocks
(\textsc{Codelay}), and scalar diagonal uncertainty. \\
$Q_{g,S},b_S,\hat h_{g,S},J_g^*(S)$ &
Normal matrix, right-hand side, fitted gains, and minimum score
for model $g$ on $S$. Lower scores are preferred. \\
$j,c,w,\delta$ &
Retained anchor, co-delay candidate, missing-delay candidate,
and pair spacing $\nu_c-\nu_j$. \\
$D,\zeta,\kappa,T$ &
Pair kernel $D_N(\delta)$, its magnitude $|D|$, waveform coherence
$\phi_j^H\phi_c/E$ for $E>0$, and diagonal $E+u+\lambda$. \\
$s,p,g_+,g_-$ &
Phase-aligned unit sum and contrast directions, and their pair
uncertainty eigenvalues. \\
$\mathcal G_g(a),m_g,\theta_g$ &
Profiled gain from adding candidate $a$, repeat-versus-missing
margin, and ideal missing-to-strong power threshold. \\
$\mathcal P,\beta,\mathcal K,\Sigma,\alpha$ &
Gain-prior precision, noise precision, posterior precision,
posterior covariance, and scalar precision for $\mathcal P=\alpha I$. \\
$P,G_\nu,M,H_{\rm fft}$ &
Occupied slots, bank Dopplers per delay, bank size $(L+1)G_\nu$,
and padded correlation-transform length. \\
\hline
\end{tabular}
\end{center}

Time and symbol indices run from $0$ to $N-1$, where $N$ is a positive
integer. Every path has integer delay $\ell_i\in\{0,\ldots,L\}$,
$0\le L<N$, and real Doppler $\nu_i$. The prefix length is at least
$L$. The chirp parameters $c_1,c_2$ are real. The transform conventions
are
\[
 F_{kt}=N^{-1/2}e^{-2\pi\mathrm{i}kt/N},\qquad
 (\Lambda_c)_{tt}=e^{2\pi\mathrm{i}ct^2},\qquad
 \mathcal A=\Lambda_{c_2}F\Lambda_{c_1}.
\]
For $k=t-\ell$, define
\[
 (\mathsf S_\ell y)[t]=
 \begin{cases}
 y[k],& k\ge0,\\
 e^{2\pi\mathrm{i}c_1(N^2+2Nk)}y[k+N],& k<0,
 \end{cases}
 \qquad
 (M_\nu y)[t]=e^{2\pi\mathrm{i}\nu t/N}y[t].
\]
Then
\[
 U_i=M_{\nu_i}\mathsf S_{\ell_i}\mathcal A^H,\qquad
 \phi_i=U_i\bar x,\qquad B_S=[\,\phi_i\,]_{i\in S}.
\]
The delay is a permutation with unit-modulus multipliers, so all three
factors of $U_i$ are unitary. On the frozen even-$N$ grid with
$a_1\in\mathbb Z$, $c_1(N^2+2Nk)=a_1N/2+a_1k$ is an integer.
These grid assumptions justify replacing the CPP delay by a plain
cyclic shift and treating the unreduced synthesis chirp as
$N$-periodic. More generally, $a_1\in\mathbb Z$ and $a_1N\in2\mathbb Z$
suffice for this simplification, including on an odd block. The
closed form and bounds below use the CPP operator as defined above.

A physical observation has the form
$Y=\sum_i h_i^{\rm true}U_ix+n$, with noise variance $\sigma^2$ per
time sample. Write $x=x_{\rm pilot}+x_{\rm data}$ and
$\bar x=x_{\rm pilot}+\mu$, where $\mu$ is the data mean supplied by the
symbol a posteriori probabilities (APPs). At a frozen receiver state
the working second-order symbol law is
\[
 \mathbb E_{\rm app}\epsilon=0,\qquad
 \mathbb E_{\rm app}[\epsilon\epsilon^H]
 =V=\operatorname{diag}(v),\qquad v_n\ge0,\qquad
 u=\sum_n v_n,\qquad E=\|\bar x\|^2 .
\]
This law specifies symbol moments. It imposes no independence between
the soft state and the detection residual that produced it.

On labelled path coordinates define
\[
 (\Gamma_{\rm F})_{ij}=\operatorname{tr}(U_i^HU_jV),\qquad
 (\Gamma_{\rm C})_{ij}
   =\mathbf1_{\{\ell_i=\ell_j\}}(\Gamma_{\rm F})_{ij},\qquad
 \Gamma_{\rm D}=uI .
\]
The full entry equals
$\mathbb E_{\rm app}[(U_i\epsilon)^H(U_j\epsilon)]$. Its quadratic
form at $h$ is $\mathbb E_{\rm app}\|\sum_i h_iU_i\epsilon\|^2$,
so $\Gamma_{\rm F}\succeq0$. Grouping coordinates by delay expresses
$\Gamma_{\rm C}$ as a direct sum of principal blocks of
$\Gamma_{\rm F}$, hence $\Gamma_{\rm C}\succeq0$ as well.

For $g\in\{{\rm D},{\rm C},{\rm F}\}$ define
\[
 J_g(h;S)=\|Y-B_Sh\|^2+h^H(\Gamma_{g,S}+\lambda I)h,\qquad
 Q_{g,S}=B_S^HB_S+\Gamma_{g,S}+\lambda I,\qquad b_S=B_S^HY .
\]
For $g={\rm F}$ the data term plus the uncertainty term is exactly the
APP-averaged squared residual. Since $Q_{g,S}\succeq\lambda I$,
completing the complex quadratic gives
\begin{align}
 \hat h_{g,S}&=Q_{g,S}^{-1}b_S,&
 J_g^*(S)&=\|Y\|^2-b_S^HQ_{g,S}^{-1}b_S, \label{eq:af-profile}\\
 J_g(h;S)-J_g^*(S)
   &=(h-\hat h_{g,S})^HQ_{g,S}(h-\hat h_{g,S}).
   \label{eq:af-square}
\end{align}
The same identities apply to any explicitly specified penalty whose
normal matrix is positive definite.

\subsection{The co-delay block}

\begin{afdmprop}[Co-delay Dirichlet structure and cross-delay error]
\label{prop:af-block}
Under the standing assumptions, put
\[
 D_N(z)=\frac1N\sum_{t=0}^{N-1}e^{2\pi\mathrm{i}zt/N},\qquad
 \widehat v[k]=\sum_{n=0}^{N-1}v_ne^{-2\pi\mathrm{i}nk/N}.
\]
For $d=\ell_j-\ell_i$, $\Delta\nu=\nu_j-\nu_i$, and
$z=\Delta\nu+a_1d$,
\begin{equation}
 (\Gamma_{\rm F})_{ij}
 =e^{2\pi\mathrm{i}c_1(\ell_i^2-\ell_j^2)}
      D_N(z)\widehat v[d\bmod N].                         \label{eq:af-full}
\end{equation}
This identity holds for every real $c_1$ and every block length $N$
with the stated CPP. The diagonal is $u$, and every co-delay entry is
$uD_N(\Delta\nu)$. Thus $\Gamma_{\rm F}-\Gamma_{\rm C}$ vanishes on
each co-delay block. For $d\ne0$ and
$\rho_z=\operatorname{dist}(z,N\mathbb Z)$,
\begin{equation}
 |(\Gamma_{\rm F}-\Gamma_{\rm C})_{ij}|
 \le
 \min\!\left\{1,\frac1{N\sin(\pi\rho_z/N)}\right\}
 \min\!\left\{u,\left\|v-\frac uN\mathbf1\right\|_1\right\},
 \label{eq:af-cross-bound}
\end{equation}
where the first factor is defined to be $1$ at $\rho_z=0$.
\end{afdmprop}

\begin{proof}
Let
\[
 f_n(k)=N^{-1/2}e^{-2\pi\mathrm{i}c_1k^2}
        e^{2\pi\mathrm{i}kn/N}e^{-2\pi\mathrm{i}c_2n^2},
 \qquad k\in\mathbb Z .
\]
On $0\le k<N$, this is the $n$th synthesis column. For $-L\le k<0$,
\[
 e^{2\pi\mathrm{i}c_1(N^2+2Nk)} f_n(k+N)=f_n(k),
\]
because $(k+N)^2-k^2=N^2+2Nk$ and $e^{2\pi\mathrm{i}n}=1$.
Thus $(U_i)_{tn}=e^{2\pi\mathrm{i}\nu_it/N}f_n(t-\ell_i)$ on every
sample, including those supplied by the prefix. Taking the product
gives
\[
 \overline{(U_i)_{tn}}(U_j)_{tn}
 =N^{-1}e^{2\pi\mathrm{i}c_1(\ell_i^2-\ell_j^2)}
          e^{2\pi\mathrm{i}zt/N}e^{-2\pi\mathrm{i}nd/N}.
\]
The $c_2$ phases cancel. Summing over $t$ and then over $n$ with
weights $v_n$ proves \eqref{eq:af-full}. At $d=0$,
$\widehat v[0]=u$, and at $i=j$, $D_N(0)=1$.

For $d\ne0$, $|d|\le L<N$ gives $d\not\equiv0\pmod N$. A constant
sequence has zero DFT at this index. The triangle inequality
therefore bounds $|\widehat v[d\bmod N]|$ by both $u$ and
$\|v-(u/N)\mathbf1\|_1$. The defining average gives $|D_N(z)|\le1$.
For $z\notin N\mathbb Z$, the geometric series gives
\[
 |D_N(z)|=\frac{|\sin(\pi z)|}{N|\sin(\pi z/N)|}
          \le\frac1{N\sin(\pi\rho_z/N)} .
\]
At $z\in N\mathbb Z$ the defining average equals one. Multiplying the
bounds proves \eqref{eq:af-cross-bound}.
\end{proof}

For constant variance, all cross-delay entries vanish. The kernel
vanishes precisely at $z\in\mathbb Z\setminus N\mathbb Z$. An integer
Doppler difference makes $z$ an integer when $a_1d$ is an integer.
On the frozen bank, $N=1024$, $a_1=5$, $L=102$, and
$\nu\in[-3,3]$, so $|\Delta\nu|\le6$. Among nonzero delay offsets
only $|d|=1$ permits resonance. For example, $d=1$, $\Delta\nu=-5$
gives $|(\Gamma_{\rm F}-\Gamma_{\rm C})_{ij}|=|\widehat v[1]|$.
For $|d|=2,10,102$, the distances of $5d+[-6,6]$ from
$1024\mathbb Z$ are respectively $4,44,504$, giving kernel bounds
below $0.080,0.0073,0.00098$. The smallest distance over all
$2\le|d|\le102$ occurs at $|d|=2$, so the bound $0.080$ applies
throughout that range.

\begin{afdmremark}[Fractional delay]
Replace $\mathsf S_\ell$ by a specified unitary fractional-delay
operator $\mathsf S_\tau$. Unitarity preserves the diagonal
$\operatorname{tr}V=u$. At a common fractional delay the weights are
$|(\mathsf S_\tau\mathcal A^H)_{tn}|^2$. For arbitrary diagonal $V$,
the co-delay formula holds for every Doppler difference exactly when
each column of the \emph{delayed} synthesis matrix has constant
squared magnitude $1/N$. Selecting a single nonzero $v_n$ and
inverting its $N$ integer-frequency samples proves necessity;
substitution proves sufficiency. Time-flatness before a fractional
delay alone does not establish this property. For $V=(u/N)I$, trace
invariance under unitary conjugation gives $uD_N(\Delta\nu)$ at a
common delay for any such $\mathsf S_\tau$. The unequal-delay formula
in \eqref{eq:af-full} uses integer translation of the quadratic chirp.
\end{afdmremark}

\begin{afdmremark}[Which part is modulation independent]
Let $W$ be any complete unitary synthesis matrix with integer delays
implemented by cyclic shifts, possibly with the CPP phases above. For
$V=(u/N)I$, cyclic invariance of the trace cancels $W$. At unequal
delays the relative shift
$\mathsf S_{\ell_j}\mathsf S_{\ell_i}^H$ has zero diagonal, since
$0<|\ell_j-\ell_i|<N$. At equal delays it is the identity. Hence
\[
 (\Gamma_{\rm F})_{ij}
 =u\,\mathbf1_{\{\ell_i=\ell_j\}} D_N(\Delta\nu).
\]
For arbitrary diagonal $V$ at a common integer delay $\ell$, the entry is
\[
 \sum_n v_n\sum_t |(\mathsf S_\ell W)_{tn}|^2
                         e^{2\pi\mathrm{i}\Delta\nu t/N}.
\]
It equals $uD_N(\Delta\nu)$ for every $v\ge0$ and every $\Delta\nu$
if and only if $|W_{tn}|^2=1/N$ for all $t,n$. Indeed the delay only
permutes squared magnitudes, and selecting one symbol variance at a
time identifies each column's time-energy sequence by inverse DFT.

Both affine frequency-division multiplexing (AFDM) and ordinary
orthogonal frequency-division multiplexing (OFDM) have time-flat
synthesis columns. For OFDM, $c_1=c_2=0$ in \eqref{eq:af-full} gives
$D_N(\Delta\nu)\widehat v[d\bmod N]$. For rectangular-pulse orthogonal
time-frequency space (OTFS) synthesis, write $N=m_0k_0$. A column
belonging to delay row $q$ has energy $1/k_0$ at times
$t\equiv q\pmod{m_0}$ and zero elsewhere. If $w_q$ is the sum of
variances in that row, summing the $k_0$ time samples gives the
common-delay entry
\[
 D_{k_0}(\Delta\nu)\sum_{q=0}^{m_0-1}
       w_q e^{2\pi\mathrm{i}\Delta\nu((q+\ell)\bmod m_0)/N}.
\]
The row totals can therefore matter at fixed $u$. Among these three
specified syntheses, the shift $a_1d$ in \eqref{eq:af-full} is the
AFDM chirp contribution.
\end{afdmremark}

\subsection{One-step support acquisition}

\begin{afdmprop}[Paired score, path splitting, and ideal pairwise admission]
\label{prop:af-split}
Use the same deletion slot for both candidates. Let the surviving
support $S$ have distinct delays. The candidates $c,w\notin S$ are
fresh coordinates. Candidate $c$ shares the delay of exactly one
survivor $j$, and the delay of $w$ is absent from $S$. Write
$S_c=S\cup\{c\}$, $S_w=S\cup\{w\}$, and $g\in\{{\rm D},{\rm C}\}$.
For each frozen observation and soft state define
\[
 \mathcal G_g(a)=J_g^*(S)-J_g^*(S\cup\{a\}),\qquad
 m_g=J_g^*(S_w)-J_g^*(S_c)=\mathcal G_g(c)-\mathcal G_g(w).
\]
A positive margin favors the repeat.

\medskip\noindent
\textup{\textbf{(a) Exact score difference.}}
On $S_c$ put
\begin{align*}
 A&=2\operatorname{Re}\!
   \left\{\overline{(\hat h_{{\rm D},S_c})_j}
         (\Gamma_{\rm C})_{jc}(\hat h_{{\rm D},S_c})_c\right\},\\
 \Delta_{\rm fit}
   &=(\hat h_{{\rm C},S_c}-\hat h_{{\rm D},S_c})^H Q_{{\rm C},S_c}
                       (\hat h_{{\rm C},S_c}-\hat h_{{\rm D},S_c}),\\
 \Delta J&=J_{\rm C}^*(S_c)-J_{\rm D}^*(S_c).
\end{align*}
Then
\begin{equation}
 \Delta J=A-\Delta_{\rm fit}=m_{\rm D}-m_{\rm C},
 \qquad \Delta_{\rm fit}\ge0.                              \label{eq:af-score}
\end{equation}
If $m_{\rm D}>0$, the co-delay score strictly reverses this preference
if and only if $\Delta J>m_{\rm D}$. Equality is a tie.

\medskip\noindent
\textup{\textbf{(b) Coincidence and the equal split.}}
Fix $u>0$, $Y$, the soft state, the other atoms, and $\nu_j$, and
let $\delta=\nu_c-\nu_j\to0$. Let $H_0$ be the aggregate of the two
gains in the duplicated scalar fit at coincidence. Then
\begin{equation}
 (\hat h_{{\rm D},S_c})_j,\;(\hat h_{{\rm D},S_c})_c
       \longrightarrow H_0/2,\qquad
 A\longrightarrow \frac u2|H_0|^2 .                      \label{eq:af-A-limit}
\end{equation}
The last limit is positive precisely when $H_0\ne0$.

\medskip\noindent
\textup{\textbf{(c) Sum-mode reward and finite-spacing contrast penalty.}}
Write $D=D_N(\delta)=\zeta e^{\mathrm{i}\vartheta}$. Rephase the
second column by $e^{-\mathrm{i}\vartheta}$ and its gain reciprocally.
At $\zeta=0$ any phase may be chosen. In these coordinates the
uncertainty off-diagonal is $u\zeta$. Put
$s=(1,1)^T/\sqrt2$, $p=(1,-1)^T/\sqrt2$ on the pair and extend
both by zero elsewhere. Consider a pair penalty with eigenvalues
$g_+,g_-\ge0$ along $s,p$. The exact co-delay pair has eigenvalues
$u(1+\zeta),u(1-\zeta)$. On an equal split of aggregate $H$,
replacing its pair uncertainty by the specified penalty saves
\begin{equation}
 \frac{u(1+\zeta)-g_+}{2}|H|^2 .                          \label{eq:af-fixed-H}
\end{equation}

At coincidence let $Q_0$ and $\hat h_0$ be the parent normal matrix
and fit with singleton uncertainty $u$ at $j$. Assume $Q_0\succ0$.
Assume also that the remaining uncertainty block is preserved, each
child has the parent's uncertainty coupling to every other retained
coordinate, and the whole child uncertainty matrix is Hermitian
positive semidefinite. Under the child assumptions, $Q_0\succ0$ is
automatic for $g_+\le2u+\lambda$. With $e_j$ the parent coordinate
vector and $\omega=u+\lambda-(g_++\lambda)/2$, the profiled split
reward is
\begin{equation}
 J_{\rm parent}^*-J_{\rm pair}^*
 =\frac{\omega|(\hat h_0)_j|^2}
        {1-\omega e_j^HQ_0^{-1}e_j}.                      \label{eq:af-profile-split}
\end{equation}
It is independent of $g_-$. At any fixed spacing, let $Q_{\rm pair}$
and $\hat h_{\rm pair}$ denote the normal matrix and optimum of a
fixed trial. Adding $rpp^H$, $r\ge0$, raises its profiled score by
\begin{equation}
 \Delta_\perp(r)=
 \frac{r|p^H\hat h_{\rm pair}|^2}
      {1+r\,p^HQ_{\rm pair}^{-1}p}.                        \label{eq:af-dose}
\end{equation}
The data Gram may couple the pair to the rest of the support.

\medskip\noindent
\textup{\textbf{(d) Exact characterisation of the idealised pairwise
comparison under ideal projection.}}
Use the original complex phases. Assume $E>0$ and put
\[
 T=E+u+\lambda,\qquad \kappa=\phi_j^H\phi_c/E,\qquad
 q_{\rm D}=E\kappa,\qquad q_{\rm C}=E\kappa+uD .
\]
Here $\kappa$ is determined by the frozen mean waveform; $D$ is the
operator kernel. Let $R=S\setminus\{j\}$. The isolation premise is
that, after Schur elimination of $R$, the two trial normal systems
in coordinate orders $(j,c)$ and $(j,w)$ have respectively the
following matrices and right-hand sides:
\[
 \left(
 \begin{bmatrix} T&q_g\\ \bar q_g&T\end{bmatrix},
 \binom{b_j}{b_c}
 \right),\qquad
 \left(
 \begin{bmatrix} T&0\\0&T\end{bmatrix},
 \binom{b_j}{b_w}
 \right), \qquad b_i=\phi_i^HY .
\]
For the conditional-mean interpretation below, use the corresponding
conditional-mean right-hand sides. The premise holds, for example,
if $R$ is empty or normal-equation-decoupled from $j,c,w$, and the
stated anchor--candidate entries hold. If $b_c=\bar\kappa b_j$, then
\begin{equation}
 \mathcal G_g(c)=
 \frac{|T\kappa-q_g|^2\,|b_j/T|^2}{T-|q_g|^2/T}.
 \label{eq:af-admission}
\end{equation}

For the power-ratio comparison assume also
$\phi_w^H\phi_j=\phi_w^H\phi_c=0$ and $\kappa=D$. Let
$H_s,H_w\ne0$ be the physical strong-path and missing-path gains.
Define
\[
 Y_{\rm sig}=H_s\phi_j+H_w\phi_w,\qquad \eta=Y-Y_{\rm sig}.
\]
Use either of the following projection premises.
\begin{enumerate}
\item For the realised comparison,
$\phi_i^H\eta=0$ for $i\in\{j,c,w\}$.
\item For the conditional comparison, condition on the frozen design
and true gains, denoted by $\mathscr D$, including $\bar x,v,H_s,H_w$
and the path columns. Assume
$\mathbb E[\|\eta\|^2\mid\mathscr D]<\infty$ and
$\mathbb E[\phi_i^H\eta\mid\mathscr D]=0$ for $i\in\{j,c,w\}$.
Compare the minima of the conditional expected quadratics
$\min_h\mathbb E[J_g(h;S_a)\mid\mathscr D]$.
\end{enumerate}
In the first comparison the relevant projections, and in the second
comparison their conditional means, are respectively
\begin{equation}
 EH_s,\qquad \bar D EH_s,\qquad EH_w
 \quad\text{on }j,c,w.                                    \label{eq:af-ideal-projections}
\end{equation}
The Berkson working model, in which the centered soft-symbol error is
independent of the omitted-path residual driving the soft detector,
motivates the ideal-projection premises. It implies neither premise.
In particular, the detector computes $\bar x$ from the same $Y$;
centering the thermal noise before conditioning does not establish
zero conditional-mean noise projections given that design.

Set $r_w=|H_w|^2/|H_s|^2$ and
\begin{align}
 \theta_{\rm D}(\zeta)
 &=\frac{\zeta^2(u+\lambda)^2}{T^2-\zeta^2E^2},&
 \theta_{\rm C}(\zeta)
 &=\frac{\zeta^2\lambda^2}{T^2-\zeta^2(E+u)^2}.
 \label{eq:af-window}
\end{align}
Under either specified comparison, the scalar score strictly prefers
$c$ and the co-delay score strictly prefers $w$ if and only if
\[
                 \theta_{\rm C}(\zeta)<r_w<\theta_{\rm D}(\zeta).
\]
An endpoint gives a tie for its respective score.
\end{afdmprop}

\begin{proof}[Proof of \textup{(a)}]
On $S_w$ all delays are distinct, so both penalties are $uI$ and
the profiles agree. On $S_c$ the penalties differ only at $(j,c)$
and $(c,j)$. Evaluating the changed objective at $\hat h_{{\rm D},S_c}$
gives the increment $A$. Refitting recovers exactly $\Delta_{\rm fit}$
by \eqref{eq:af-square}. Positive definiteness gives
$\Delta_{\rm fit}\ge0$. This proves \eqref{eq:af-score};
$m_{\rm C}=m_{\rm D}-\Delta J$ gives the strict and tie cases.
In particular, $A>m_{\rm D}$ is necessary for reversal, but refitting
can make it insufficient.
\end{proof}

\begin{proof}[Proof of \textup{(b)}]
At coincidence $\phi_j=\phi_c$. For fixed $H=h_j+h_c$, the data term
depends on the pair only through $H$, including when the other gains
are jointly fitted. The pair's scalar uncertainty and coordinate
ridge sum to
\[
 (u+\lambda)(|h_j|^2+|h_c|^2)
 =\frac{u+\lambda}{2}\bigl(|H|^2+|h_j-h_c|^2\bigr).
\]
The unique minimizing split is $h_j=h_c=H/2$. The columns are
continuous in Doppler, and the inverse normal matrix is continuous
because its smallest eigenvalue is at least $\lambda$. The gains
therefore converge to the duplicated fit at coincidence. Substituting
their limits and $(\Gamma_{\rm C})_{jc}\to u$ in $A$ proves
\eqref{eq:af-A-limit}. A singleton pays a different aggregate penalty,
so its fitted gain need not be $H_0$.
\end{proof}

\begin{proof}[Proof of \textup{(c)}]
Diagonalizing the pair with diagonal $u$ and off-diagonal $u\zeta$
gives the stated exact eigenvalues. Since $s^Hh=H/\sqrt2$, the
within-pair uncertainty plus ridge cost is
\[
 \frac{g_++\lambda}{2}|H|^2+(g_-+\lambda)|p^Hh|^2 .
\]
Setting $p^Hh=0$ and comparing pair costs gives
\eqref{eq:af-fixed-H}. At coincidence the data and the external
couplings depend on the pair only through $H$. Since $g_-+\lambda>0$,
profiling sets $p^Hh=0$. The child normal matrix restricted to the
injective equal-split map $H\mapsto(H/2,H/2)$, with the other
coordinates unchanged, is
\[
 Q_{\rm red}=Q_0-\omega e_je_j^H .
\]
The right-hand side is the parent's. The child normal matrix is
positive definite, so $Q_{\rm red}\succ0$. If $g_+\le2u+\lambda$,
then $\omega\ge0$ and $Q_0=Q_{\rm red}+\omega e_je_j^H\succ0$.
For the full stated range of $g_+$, the premise $Q_0\succ0$ permits
congruence by $Q_0^{-1/2}$, giving
$1-\omega e_j^HQ_0^{-1}e_j>0$.

For $Q\succ0$ and real $\gamma$ with $1+\gamma z^HQ^{-1}z\ne0$,
the Sherman--Morrison identity is
\[
 (Q+\gamma zz^H)^{-1}
 =Q^{-1}-\frac{\gamma Q^{-1}zz^HQ^{-1}}{1+\gamma z^HQ^{-1}z}.
\]
Multiplication by $Q+\gamma zz^H$ verifies the identity. Apply it to
\eqref{eq:af-profile} first with $(\gamma,z)=(-\omega,e_j)$ and then
with $(\gamma,z)=(r,p)$. The second denominator is at least one.
This proves \eqref{eq:af-profile-split} and \eqref{eq:af-dose}.
\end{proof}

For scalar uncertainty $\omega=(u+\lambda)/2$. For exact sum
curvature $g_+=2u$ at coincidence, $\omega=\lambda/2$. In this case
restricting the child uncertainty alone to the equal split yields
the parent uncertainty, which is therefore positive semidefinite.
Thus $Q_0\succeq\lambda I$ and the denominator of
\eqref{eq:af-profile-split} is at least $1/2$. For a fixed parent
design and uncertainty, $\hat h_0$ stays bounded as
$\lambda\downarrow0$. Indeed, the null space of the unregularized
normal matrix is contained in $\ker B_S$, hence $b_S=B_S^HY$ has
zero projection onto it. Diagonalization on the remaining positive
eigenvalues proves boundedness. The residual duplicate reward is
consequently $O(\lambda)$ for that parent problem.

At fixed $\lambda>0$, the duplicate formula is the limit for
continuous columns and penalties. At finite spacing,
\eqref{eq:af-dose} is strictly positive exactly when $r>0$ and the
original fit has nonzero contrast. The pairwise design conditions
for preserving exact sum curvature and imposing a uniform contrast
floor are
\[
 g_+=u(1+\zeta),\qquad g_-\ge c_0u
 \quad\text{near }\zeta=1,\qquad c_0>0
 \text{ independent of spacing}.
\]
For $u>0$, the scalar model misses the first condition near
coincidence and the exact co-delay pair misses the second. For
$1-\zeta<1/2$, adding $upp^H$ to the exact pair gives
$g_-=u(2-\zeta)$. Replacing only the low eigenvalue by $u$
(the \textsc{C-hi} arm) gives $g_-=u$. Both retain the exact $g_+$.
Under the coupling premise of part (c), both therefore share the
exact co-delay acquisition score at coincidence.
Equation~\eqref{eq:af-dose} gives their possible departures at
finite spacing.

For a co-delay block of size $m>2$, the corresponding
\emph{design prescription} is to specify the targeted coincidence
and a preserved invariant subspace containing the range of the
exact block at that coincidence. Preserve the exact action on
that subspace and impose a floor $c_0uI$ on its orthogonal
complement, keeping the decomposition invariant. In particular,
when only two atoms coalesce and another resolved direction remains
in the range, the prescribed subspace includes that direction.
The prescription is support-specific; it asserts no general
$m$-atom profiled-score identity.

\begin{proof}[Proof of \textup{(d)}]
On either trial, minimization over $h_R$ subtracts the common
quantity $b_R^HQ_{g,R}^{-1}b_R$ from the constant term when $R$ is
nonempty, and leaves the Schur-complemented matrix and right-hand
side in the statement. The $R$ block is the same in both trials
and for both scorers since the delays in $R$ are distinct. The
anchor-only problem is obtained by setting the candidate gain to
zero. Eliminating the anchor in the repeat trial leaves innovation
$b_c-\bar q_g b_j/T$ and positive scalar curvature $T-|q_g|^2/T$.
Thus
\[
 \mathcal G_g(c)
 =\frac{|b_c-\bar q_g b_j/T|^2}{T-|q_g|^2/T}.
\]
Substitution of $b_c=\bar\kappa b_j$ gives
\eqref{eq:af-admission}. The missing trial has zero off-diagonal,
so $\mathcal G_g(w)=|b_w|^2/T$.

For the realised ideal projections, orthogonality gives
$\phi_j^HY_{\rm sig}=EH_s$,
$\phi_c^HY_{\rm sig}=\bar\kappa EH_s$, and
$\phi_w^HY_{\rm sig}=EH_w$. Zero residual projections and
$\kappa=D$ give \eqref{eq:af-ideal-projections}.

For the conditional comparison, set
$\bar b_I=\mathbb E[b_I\mid\mathscr D]$ for any coordinate list $I$.
The conditional expected objective on $I$ is
\[
 \mathbb E[\|Y\|^2\mid\mathscr D]
       -2\operatorname{Re}(h^H\bar b_I)+h^HQ_{g,I}h .
\]
The finite second-moment premise makes this expression well defined.
Profile over $h_R$ in this averaged quadratic. Its constant now
contains $-\bar b_R^HQ_{g,R}^{-1}\bar b_R$, common to the two trials
and the baseline. It cancels in their differences even if
$\mathbb E[B_R^H\eta\mid\mathscr D]\ne0$. On the two remaining
coordinates, the stated reduced right-hand sides and the three
zero conditional-mean projections give
\eqref{eq:af-ideal-projections}. Hence the preceding scalar
minimization applies to these mean projections. The order here is
conditional averaging followed by minimization.

To evaluate either ideal comparison, put $t_{\rm D}=E$ and
$t_{\rm C}=E+u$. Then $q_g=t_gD$ and
\[
 \mathcal G_g(c)
 =\frac{E^2|H_s|^2}{T}
   \frac{\zeta^2(T-t_g)^2}{T^2-\zeta^2t_g^2},
 \qquad
 \mathcal G_g(w)=\frac{E^2|H_w|^2}{T},
\]
where in the conditional case the gains refer to the averaged
objectives. Both denominators are positive since $t_g<T$ and
$\zeta\le1$. Thus the sign of the pairwise margin is the sign of
$\theta_g(\zeta)-r_w$. This proves both directions of the open-window
characterisation and the endpoint ties.

For $0<\zeta\le1$, the derivative of
$(T-t)^2/(T^2-\zeta^2t^2)$ on $0\le t<T$ is
\[
 \frac{-2T(T-t)(T-\zeta^2t)}{(T^2-\zeta^2t^2)^2}<0.
\]
Hence $\theta_{\rm C}<\theta_{\rm D}$ when $u>0$; for $u=0$ the
window is empty. In reciprocal power ratio, the window for
$\zeta>0$ is
\[
 \frac{T^2-\zeta^2E^2}{\zeta^2(u+\lambda)^2}
 <r_w^{-1}<
 \frac{T^2-\zeta^2(E+u)^2}{\zeta^2\lambda^2}.
\]
At $\zeta=1$ this reduces to
$1+2E/(u+\lambda)<r_w^{-1}<1+2(E+u)/\lambda$.
The derivative of $\theta_{\rm D}$ with respect to $\zeta^2$ is
$(u+\lambda)^2T^2/(T^2-\zeta^2E^2)^2$, giving the upper envelope
$(u+\lambda)/(2E+u+\lambda)$. At an integer spacing
$\delta\not\equiv0\pmod N$, $\zeta=0$ and both thresholds vanish.
\end{proof}

\noindent\textbf{Gap.}
Without control of the residual projections, the window is neither
sufficient nor necessary for the stated reversal on a realised
frame. The quantities $b_w-EH_w$ and $b_c-\bar\kappa b_j$ enter
before squaring, and the anchor projection can also differ from
$EH_s$. Even a centered noise projection can have nonzero squared
modulus. A detector fitted without the missing path can absorb part
of its response into $\bar x$. There is a separate waveform mismatch
even when $b_c=\bar\kappa b_j$: the repeat innovation is
$(b_j/T)\overline{T\kappa-q_g}$, with factors
\[
 T\kappa-q_{\rm D}=(u+\lambda)\kappa,\qquad
 T\kappa-q_{\rm C}=\lambda\kappa+u(\kappa-D).
\]
Thus $\kappa=D$ removes a term that can remain on a real frame.
The $\lambda^2$ numerator of the ideal co-delay threshold does not
give a bound on that term. A framewise guarantee would need joint
control of the actual innovations and geometry; a globally accepted
edit must also beat the incumbent and the other legal candidates.

\subsection{Fixed-prior contrast curvature}

\begin{afdmcor}[Contrast curvature and marginal variance at a fixed prior]
\label{cor:af-prior}
Freeze a gain-prior precision $\mathcal P\succ0$, noise precision
$\beta>0$, dictionary $B_S$, and Hermitian positive semidefinite
uncertainty $\Gamma$. The Gaussian estimation step has
\[
 \mathcal K=\mathcal P+\beta(B_S^HB_S+\Gamma),\qquad
 \Sigma=\mathcal K^{-1}.
\]
Suppose the principal pair block of $\Gamma$ agrees with the exact
co-delay block, as it does for $\Gamma_{\rm C}$ and $\Gamma_{\rm F}$
on a co-delay pair. Express $B_S,\Gamma,\mathcal P$ and $p$ in the
same phase-aligned gain coordinates of
Proposition~\ref{prop:af-split}(c). In particular, if the column
rephasing is $B_S\mapsto B_S C_\vartheta$, with $C_\vartheta$
diagonal unitary, the prior in those coordinates is
$C_\vartheta^H\mathcal P C_\vartheta$, and the same congruence
applies to $\Gamma$. Then
\[
 p^H\mathcal Kp=p^H\mathcal Pp+\beta\|B_Sp\|^2+\beta u(1-\zeta).
\]
Both nonprior terms vanish at coincidence. If
$\mathcal P=\alpha I$, $\alpha>0$, the contrast marginal variance
there equals $1/\alpha$. A pair block with a contrast eigenvalue
$g_-\ge c_0u$ contributes at least $\beta c_0u$ of uncertainty
curvature.

For any Hermitian $\Gamma\succeq0$ at fixed $\mathcal P,\beta,B_S$,
adding $rpp^H$ to $\Gamma$ changes the marginal variance by
\begin{equation}
 v_p=p^H\Sigma p
 \quad\longmapsto\quad
 \frac{v_p}{1+\beta r v_p},\qquad r\ge0 .
 \label{eq:af-variance}
\end{equation}
\end{afdmcor}

\begin{proof}
The contrast is zero outside the pair, so its quadratic form in
$\Gamma$ uses only that principal block. The exact contrast eigenvalue
there is $u(1-\zeta)$. At coincidence $B_Sp=0$ because the columns
agree, and $p^H\Gamma p=0$. Positive semidefiniteness gives
$\|\Gamma^{1/2}p\|^2=0$, hence $\Gamma p=0$ even with other retained
atoms. Under the isotropic prior, $\mathcal Kp=\alpha p$, so
$p^H\Sigma p=1/\alpha$. For a general prior the marginal variance
need not equal the reciprocal directional precision. Applying the
rank-one inverse identity to $\mathcal K+\beta rpp^H$ gives
\[
 p^H(\mathcal K+\beta rpp^H)^{-1}p
 =v_p-\frac{\beta r v_p^2}{1+\beta r v_p}
 =\frac{v_p}{1+\beta r v_p}.
\]
\end{proof}

A smaller fixed-prior variance implies no ordering of automatic
relevance determination (ARD) updates, channel error, or frame
error rate (FER). For example, an iterative sparse Bayesian
estimator updates coordinate prior variances using
$\Sigma_{ii}+|\hat h_i^{\rm post}|^2$. A contrast ridge can change
both summands, the next noise precision, and the coordinates
surviving pruning. Equation~\eqref{eq:af-variance} compares one
marginal at a common prior and dictionary.

\subsection{Compact evaluation of every exchange}

\begin{afdmprop}[Exact compact exchange and arithmetic cost]
\label{prop:af-exchange}
Freeze $Y,\bar x,v,\lambda$, an entering support $S$ of $P$ occupied
coordinates, and a rectangular bank of $M=(L+1)G_\nu$ physical
candidates. For each candidate append a \emph{fresh coordinate} $a$,
even if its physical delay and Doppler duplicate those of an occupied
coordinate. On every labelled augmentation $S\cup\{a\}$ assume a
coordinate-indexed Hermitian positive semidefinite uncertainty matrix
such that
\begin{enumerate}
\item its $S$ principal block is the fixed entering matrix $\Gamma_S$,
and its appended diagonal is $\Gamma_{aa}=u$;
\item each trial obtained by deleting one coordinate uses the
corresponding principal submatrix of this same augmentation.
\end{enumerate}
Every coordinate carries its own ridge. The models
$\Gamma_{\rm F},\Gamma_{\rm C},\Gamma_{\rm D}$ satisfy these
conditions. In particular, for distinct coordinates at identical
physical parameters the full and co-delay off-diagonals are $u$,
whereas the scalar off-diagonal is zero. Spectral projectors
recomputed separately on each trial do not in general satisfy the
principal-submatrix condition.

Suppress the fixed scorer subscript and let
$W_Q=Q_S^{-1}$, $\hat h_S=W_Qb_S$. For each appended coordinate set
\[
 k_a=B_S^H\phi_a+\Gamma_{S,a},\qquad
 b_a=\phi_a^HY,\qquad
 y_a=W_Qk_a,\qquad
 d_a=E+u+\lambda-k_a^Hy_a,\qquad
 z_a=b_a-k_a^H\hat h_S .
\]
For deletion of any entering coordinate $i$, write
$S-i+a=(S\setminus\{i\})\cup\{a\}$. Then $d_a>0$ and the direct
Cholesky profile on this support equals
\begin{equation}
 J^*(S-i+a)=J^*(S)-\frac{|z_a|^2}{d_a}
 +\frac{|(\hat h_S)_i-(y_a)_i z_a/d_a|^2}
        {(W_Q)_{ii}+|(y_a)_i|^2/d_a}.                     \label{eq:af-exchange}
\end{equation}
The identity holds in exact arithmetic before applying the legality
mask, including for physically duplicate candidates.
\end{afdmprop}

\begin{proof}
The augmented normal system is
\[
 Q_+=\begin{bmatrix}Q_S&k_a\\k_a^H&E+u+\lambda\end{bmatrix},
 \qquad b_+=\binom{b_S}{b_a}.
\]
Unitarity gives $\|\phi_a\|^2=E$, and the appended uncertainty
diagonal is $u$ by hypothesis. Positive semidefiniteness of the
\emph{augmented} uncertainty gives $Q_+\succeq\lambda I$.
Consequently its Schur complement $d_a$ is positive. Eliminating
the old coordinates leaves
\[
 J^*(S)-2\operatorname{Re}(\bar h_a z_a)+d_a|h_a|^2 .
\]
The minimizer is $z_a/d_a$. Back substitution and the block inverse
give
\[
 J_+^*=J^*(S)-|z_a|^2/d_a,\qquad
 \hat h_{+,S}=\hat h_S-y_a z_a/d_a,\qquad
 (Q_+^{-1})_{S,S}=W_Q+y_ay_a^H/d_a .
\]

Deleting $i$ imposes $e_i^Hh=0$ in the augmented problem. By
\eqref{eq:af-square}, its cost increase is the minimum of
$\xi^HQ_+\xi$ subject to $e_i^H\xi=-\hat h_{+,i}$.
Cauchy--Schwarz on $Q_+^{-1/2}e_i$ and $Q_+^{1/2}\xi$ bounds this
minimum below by $|\hat h_{+,i}|^2/(Q_+^{-1})_{ii}$. The bound is
attained at
$\xi=-Q_+^{-1}e_i\hat h_{+,i}/(Q_+^{-1})_{ii}$. Substitution proves
\eqref{eq:af-exchange}. By principal-submatrix consistency, the
remaining variables have exactly the replacement trial's normal
equations. Direct Cholesky fitting and the E-1 implementation that
deletes $i$ first and then takes the candidate Schur complement
therefore give the same profile.
\end{proof}

\paragraph{Computing the fields and counting operations.}
Let $x_{\rm t}=\mathcal A^H\bar x$. On $-L\le k<N$ define
\[
 x_{\rm ext}[k]=
 \begin{cases}
 x_{\rm t}[k],&k\ge0,\\
 e^{2\pi\mathrm{i}c_1(N^2+2Nk)}x_{\rm t}[k+N],&k<0 .
 \end{cases}
\]
For any $N$-vector $y$ the required field is
\[
 \mathcal F_y(\ell,\nu)=
 \sum_{t=0}^{N-1}\overline{x_{\rm ext}[t-\ell]}\,
       e^{-2\pi\mathrm{i}\nu t/N}y[t]=\phi_{(\ell,\nu)}^Hy .
\]
For each $\nu$, convolve the demodulated $y$ with
$k\mapsto\overline{x_{\rm ext}[N-1-k]}$, indexed from $0$ to $N+L-1$.
At output $N-1+\ell$, the $t$th summand is the summand above. Zero
padding to $H_{\rm fft}\ge2N+L-1$ covers the linear convolution.
The DFT convolution theorem therefore gives all legal delays without
aliasing, including at noninteger Doppler. In particular,
\[
 b_a=\mathcal F_Y(a),\qquad
 (k_a)_i=\overline{\mathcal F_{\phi_i}(a)}+\Gamma_{ia}.
\]

For the three stated models, with a fast Fourier transform
(FFT)-efficient $H_{\rm fft}=O(N+L)$ and ordinary dense linear
algebra, the costs are as follows.
\begin{itemize}
\item The $P+1$ initial correlation fields cost
$O((P+1)G_\nu H_{\rm fft}\log H_{\rm fft})$.
Forming the active mean Gram and factoring the normal matrix costs
$O(NP^2+P^3)$. The initial inverse DAFT costs $O(N\log N)$.
\item Multiplication of $W_Q$ by $[k_a]_a$ costs $O(P^2M)$.
Column reductions and all $PM$ scalar replacement scores cost
$O(PM)$. The cross fields, right-hand side field, and inverse
require $O(PM+M+P^2)$ words in addition to active responses, FFT
workspace, and any saved trace. An implementation that sorts all
$PM$ scores also incurs its sorting cost.
\item With soft state and grid frozen, a single exchange changes
only the replaced atom's row of $[k_a]_a$. The bank right-hand
sides remain fixed. Refreshing the row before another pass costs
one field, $O(G_\nu H_{\rm fft}\log H_{\rm fft})$, plus its
uncertainty row. The implementation refits the small active system.
\item For the full model, \eqref{eq:af-full} uses one variance FFT
at $O(N\log N)$ and $O(PM)$ rectangular entries. For
\textsc{Codelay}, each active row has $G_\nu$ same-delay bank
entries. The rectangular block therefore needs $PG_\nu$ Dirichlet
evaluations and no variance FFT. Computing $u$ costs $O(N)$ if it
is not supplied. The frozen implementation allocates and masks a
dense $P$-by-$M$ block, so entry handling can still cost $O(PM)$.
\end{itemize}
For $P=8$, $L=102$, and $G_\nu=25$, this gives $M=2575$,
$20{,}600$ exchange scores per pass, and $200$ rectangular co-delay
kernel evaluations, excluding the small active block and subsequent
refits.

\begin{afdmremark}[Numerical selection]
The frozen E-1 selector excludes a candidate within $10^{-6}$ Doppler
bin of another retained atom at the same delay. Exact coincidence
in Proposition~\ref{prop:af-split} is therefore an algebraic limit.
The compact wrapper falls back to the direct route when the active
condition number exceeds $10^8$ or a specified fallback condition
is encountered. Strict acceptance requires a decrease exceeding
$10^{-10}(1+|J_{\rm old}^*|)$. The separate winner check compares
the compact and direct scores with tolerance
$10^{-7}(1+|J_{\rm compact,winner}^*|)$; a mismatch raises an
assertion and aborts the run. These tolerances give no uniform
forward-error bound for \eqref{eq:af-exchange}.
\end{afdmremark}

\begin{afdmremark}[In-memory algebra checks]
On the recorded 32-sample synthetic block, the maximum entrywise
error of \eqref{eq:af-full} against direct basis-column evaluation,
divided by $u$, was $1.21\times10^{-15}$, including a resonant
cross-delay pair. The maximum absolute discrepancies for the score
decomposition, profiled duplicate reward, finite-spacing contrast
increment, and fixed-prior marginal variance were respectively
$1.11\times10^{-16}$, $1.69\times10^{-16}$, $1.56\times10^{-16}$,
and $8.34\times10^{-17}$. The isolated admission gain and the tie at
the theoretical endpoint gave $2.50\times10^{-16}$ and
$2.23\times10^{-16}$, respectively. The CPP observation field
differed from explicit inner products by at most $8.89\times10^{-17}$.
Across three slots, twenty candidates, and all three uncertainty
models, the largest absolute difference between the compact score
and a direct E-1 Cholesky refit was $1.11\times10^{-16}$ over
$180$ comparisons.
\end{afdmremark}

\begin{afdmremark}[Relation to empirical results]
Proposition~\ref{prop:af-block} identifies the entries retained and
discarded by \textsc{Codelay}. The observed zero discordant frame-error
decisions in $13{,}600$ paired keys and the $155$ differing decoded-bit
hashes among joint failures are empirical counts. Neither follows from
the entrywise bound (\texttt{res-20261118-03}).

Proposition~\ref{prop:af-split}(a,b) identifies the measured score
term that can reverse a repeated-delay addition after a fixed
deletion. The frequency of a change to the globally accepted action
comes from the first-step attribution and ablation experiments
(\texttt{res-20261118-01}, \texttt{res-20261017-01}).
Part (d) supplies the isolated scalar admission reward used in
the semi-blind replay. The forced-miss sweep supported co-delay
suppression inside the ideal window and rejected the proposed scalar
flip location and population-curve transport. The larger observed
failure region and the post hoc finding of missing-path projection
attenuation, with a direct-term shortfall also contributing, are
empirical (\texttt{res-20261118-06}, \texttt{res-20261119-01}).

Proposition~\ref{prop:af-split}(c) and Corollary~\ref{cor:af-prior}
distinguish the acquisition reward for duplicating a path from the
estimation curvature along its unresolved contrast. On the frozen
bank the nearest distinct same-delay candidate to an on-grid anchor
is $0.25$ bin away, where $|D_{1024}(0.25)|\simeq0.900$.
The observed equality of \textsc{C-hi} and co-delay pass/fail
decisions on the tested keys ($\psi_{\rm C\text{-}hi}=1.000$) is a
finite-grid result. Deducing it from \eqref{eq:af-dose} would require
comparing the increments with the actual decision margins. The
iterative sparse Bayesian performance ordering and the resolution
loss on genuine finite-spacing doublets also remain experimental
findings; the FER cost in the doublet test was uncertain
(\texttt{res-20261119-02}, \texttt{res-20261119-03},
\texttt{res-20261119-04}).

Proposition~\ref{prop:af-exchange} explains how compact and direct
implementations evaluate the same grid objective. The rescue
fraction, slot-cap dependence, and single-core runtime advantage over
a different receiver also depend on the outer receiver and tested
population (\texttt{res-20261017-01}, \texttt{res-20261118-04},
\texttt{res-20261118-03}).
\end{afdmremark}
```

## 修订记录

| 审阅编号 | 位置 | 修改 |
|---|---|---|
| C#1、A#3 | 基本假设、命题 1 | 明定 \(\ell_i\in\{0,\ldots,L\}\)、\(L<N\)、\(\nu_i\in\mathbb R\)。用前缀相位的延拓恒等式证明闭式对任意实数 \(c_1\) 和正整数 \(N\) 成立。单独给出可省略前缀相位、直接使用循环移位的整性条件。 |
| C#2 | 命题 1 后的数值例 | 补上冻结候选库的 \(\nu\in[-3,3]\)。在允许的非零时延差中，只有 \(\lvert d\rvert=1\) 可能共振；其余时延差的最坏核上界出现在 \(\lvert d\rvert=2\)。 |
| C#3 | 分数时延注记 | 时域等模条件施加于**经过分数时延后的**合成列。保留了常方差时由迹不变性得到的共同分数时延结论。 |
| C#4 | 命题 2(c) 及证明 | 增加 \(Q_0\succ0\) 前提，并从受限子问题的正定性证明 \(g_+\le2u+\lambda\) 时该前提自动成立。 |
| C#5、A#4.1 | 命题 2(c) 后的大块讨论 | 采用设计规定。先指定目标重合情形，保留子空间须包含该处精确块的整个值域；只对其正交补施加惩罚下界。 |
| C#6 | 数值选择及实证注记 | 区分重合极限和最近的 \(0.25\) 格点。明确 \(\psi_{\rm C\text{-}hi}=1.000\) 来自实测，并指出若要推出全部判决相同，尚需比较有限间隔的评分增量与实际判决余量。 |
| C#7 | 命题 2(d) 后的 `Gap` | 给出保留复相位的新息公式。共延模型中控制新息的因子为 \(\lambda\kappa+u(\kappa-D)\)，因此实际波形相干度偏离 \(D\) 时，理想阈值的 \(\lambda^2\) 分子不能控制额外项。 |
| C#8、A#2 | 命题 2(d) 的声明、证明及 `Gap` | 将窗口改为理想两两比较的充要条件。定义 \(Y_{\rm sig}\)、\(\eta\) 和条件信息；分别证明单帧零投影、先平均目标再拟合两种情形。补上有限二阶矩，并展示保留坐标 \(h_R\) 的公共项如何抵消。说明 Berkson 独立性不能推出所需条件投影。 |
| C#9、A#5 | 命题 2 开头及 2(d) | 定义加入候选的收益 \(\mathcal G_g(a)\) 及其与 \(m_g\) 的关系。明确写出消去 \(R\) 后两个 \(2\times2\) 系统的矩阵及右端，并说明 \(w\) 的时延在整个 \(S\) 中缺失。 |
| C#10 | 符号表及全文 | 补入 \(\kappa,T,\theta_g,\mathcal G_g,\mathcal K,\Sigma,\beta,\alpha\)。区分了时延算子与标量 \(T\)、评分变化与后验精度、拟合收益与字典矩阵，以及分裂系数与候选坐标。 |
| C#11、A#1 | 命题 3 的声明及证明 | 明定每个增广矩阵按坐标索引、为 Hermitian 半正定、满足 \(\Gamma_{aa}=u\)，且进入支撑与各试验支撑均取对应主子矩阵。由增广正定性推出 \(d_a>0\)。说明三个具体模型在重复物理路径上的取值，以及逐试验重算谱投影的限制。 |
| C#12 | 数值选择注记 | 胜者核对容差按紧凑算法给出的胜者分数缩放。超过容差会触发断言并终止，与条件数触发的直接算法回退分开表述。 |
| C#13、A#7.6 | 内存代数检查注记 | 九项误差逐项对回原始计算记录，恢复原记录的末位和有效数字，统一使用 `\times`。 |
| A#4.2 | 命题 2 | 将 (a)–(d) 的完整前提与结论放进同一个命题环境，四份证明各自标明对应部分。 |
| A#6 | 固定先验推论 | 明确精确曲率公式要求 \(\Gamma\) 的对应主子块等于精确共延块。给出非对角先验在相位对齐坐标中的合同变换。秩一方差更新仍适用于任意半正定 \(\Gamma\)。 |
| A#7.1–5 | 命题 1 的注记、命题 2(a,c) | 统一普通路径对的多普勒差 \(\Delta\nu\) 与方差变换索引 \(d\bmod N\)；说明不同时延的相对移位对角为零、\(c,w\) 是新坐标，以及 \(\zeta=0\) 时对齐相位任选。 |

## 剩余缺口

命题 2(d) 推广到真实单帧仍缺少对残差投影和 \(\kappa-D\) 的联合控制。因此，理想窗口对真实帧上的两两翻转**既不充分，也不必要**。若要进一步判断接收机最终接受哪个编辑，还需要同原支撑及其他合法候选比较。正文已在对应位置标为 `\textbf{Gap.}`。

本次另作了两项只读内存核对。奇数块长 \(N=15\)、非整数 \(2Nc_1=2.2\) 时，前缀闭式对直接计算的误差除以 \(u\) 为 \(5.09\times10^{-17}\)。保留坐标的平均投影非零时，两种评分模型的直接拟合与消元公式最大绝对差为 \(9.44\times10^{-16}\)。正文的九项历史误差沿用原始记录。本次未编译排版，仓库未写入。

model: `gpt-6.2-astra`（已由本次会话元数据确认）