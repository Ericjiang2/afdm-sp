# Independent Adversarial Proof Check: `theory-astra-v1.tex`

- **Reviewer model:** Gemini 4 Neon (extra-high reasoning effort)
- **Date:** 2026-11-19
- **Object reviewed:** `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v1.tex` (lines 1–779)
- **Author self-check & brief consulted:** `astra-proofs-raw-20261119.md` (tail), `astra-proofs-brief.md`
- **Code & protocol verified against:** `experiments/sp_afdm_frozen_20260920/src/physical.py`, `experiments/sp_afdm_native_joint_20260921/src/twofft.py`, `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py`, `experiments/tf_cstate_validation_20260922/{compact_state.py,geometry_validation.py}`, `experiments/cstate_codelay_sbl_stage3_20261118/codelay.py`, `experiments/cstate_first_step_attribution/PROTOCOL.md`, `experiments/tf_e3_sbl_20261017/sbl_rx.py`, and cited result cards `res-20261118-03`, `res-20261118-06`, `res-20261119-01` through `res-20261119-04`.
- **Independence:** `claude-proof-check-20261119.md` was not read. Repository was treated strictly read-only aside from this file.

---

## 1. Verdict Summary

**Issue counts:** `0` critical, `2` major, `5` minor.

| Statement | `.tex` lines | Verdict | Basis |
|---|---|---|---|
| **Proposition 1** (Co-delay Dirichlet structure & cross-delay bound) | 131–189 | **proved with minor fix** | Identities (141) and bound (150) are exact; standing assumptions omit the explicit delay domain $\ell_i \in \{0,\dots,L\}$ needed for $d \ne 0 \implies d \not\equiv 0 \pmod N$. |
| **Proposition 2(a)** (Score-difference identity) | 264–299 | **proved as stated** | Every step of $K = A - B_{\rm fit} = m_{\rm D} - m_{\rm C}$ and $B_{\rm fit} \ge 0$ follows cleanly (fresh candidate labels $c,w \notin S$ are implicit in "labeled support"). |
| **Proposition 2(b)** (Coincidence and equal split) | 301–328 | **proved as stated** | Parallelogram split and continuity of $Q_{\rm D}(\delta)^{-1}$ via $Q_{\rm D}(\delta) \succeq \lambda I$ are complete and exact. |
| **Proposition 2(c)** (Sum-mode split reward & finite-spacing $L(r)$) | 330–428 | **proved with minor fix** | Eqs. (340), (354–356), (362–364), and the $O(\lambda)$ limit as $\lambda \downarrow 0$ are proved; post-proof discussion (lines 424–428) states an unproved, under-specified $m > 2$ "sufficient construction", and the `afdmprop` environment closes at line 262 before parts (a)–(d). |
| **Proposition 2(d)** (Sufficient finite-spacing window under Berkson premise) | 430–538 | **gap** | Algebraic formulas (444) and (466)–(475) and the single-frame `\textbf{Gap.}` are sound; however, the link from the stated Berkson premise to the residual-averaged-quadratic hypothesis is unbridged (thermal noise $n$ conditioned on decoder-generated $(\bar x, v)$ and other paths are omitted), and lines 499–504 leave $Y_{\rm sig}, \eta, \mathcal G_g$ undefined and mishandle $h_R$ when $S \setminus \{j\} \ne \emptyset$. |
| **Corollary 1** (Fixed-prior contrast curvature & marginal variance) | 541–585 | **proved with minor fix** | Curvature formula, $1/\alpha$ coincidence limit (even with full $\Gamma_{\rm F}$ and other atoms), rank-one variance law (560), and no-FER/ARD-ordering caveat are exact; minor cleanup needed to state explicitly when $\Gamma$ is specialized to an exact co-delay block vs. arbitrary PSD and how non-diagonal $\mathcal P$ transforms under rephasing. |
| **Proposition 3** (Compact exchange exactness & complexity) | 588–710 | **gap** | Exact for $\Gamma_{\rm F}, \Gamma_{\rm C}, \Gamma_{\rm D}$, and both the CPP convolution proof and complexity orders are solid; however, the stated general class omits two hypotheses directly used on lines 628–629 ($\Gamma_{S \cup \{a\}} \succeq 0$ on the augmented support and $\Gamma_{aa} = u$), admitting a $3\times 3$ counterexample with $d_a = 0$ (division by zero). |
| **Remarks** (Fractional delay; Modulation independence; Numerical selection; In-memory checks; Empirical relation) | 200–251, 712–779 | **proved with minor fix** | All mathematical claims (including the unimodular iff theorem and OTFS formula) and empirical citations check out; minor notation/typography slips ($\delta$ undefined at line 244, `\times` omitted in scientific notation, 0.01 ceiling-vs-rounding mismatch on lines 728–738 vs. raw summary). |

---

## 2. Numbered Issue List

### Issue 1 — [MAJOR] Prop 3 general statement omits augmented-PSD ($\Gamma_{S\cup\{a\}} \succeq 0$) and diagonal ($\Gamma_{aa} = u$) hypotheses; counterexample gives $d_a = 0$
- **Lines:** 591–595, 604, 628–629
- **Problem:** Prop 3 is stated for any "uncertainty model whose entries on a trial are the corresponding principal submatrix of the labeled augmented model" (adding that $\Gamma_{\rm F}, \Gamma_{\rm C}, \Gamma_{\rm D}$ satisfy this). Section 1.1 (lines 126–127) only imposes PSD on each $P$-element trial support. Yet the proof uses two strictly stronger assumptions that are never stated for the general model:
  1. Line 628 uses $\Gamma_{aa} = u$ to obtain $(Q_+)_{aa} = E + u + \lambda$ and $d_a = E + u + \lambda - k_a^H t_a$ (line 604).
  2. Line 629 asserts $Q_+ \succeq \lambda I$ to guarantee $d_a > 0$, which requires the **augmented** $(P+1)\times(P+1)$ matrix $\Gamma_{S\cup\{a\}}$ to be Hermitian PSD — trial-wise PSD on every $P$-element subset does **not** imply augmented PSD.
  - **Counterexample:** Take $P = 2$, $E = 0$, $u = 2$, $\lambda = 2$, and
    $$\Gamma_{S \cup \{a\}} = 2\begin{pmatrix} 1 & 1 & 1 \\ 1 & 1 & -1 \\ 1 & -1 & 1 \end{pmatrix}.$$
    Every $2\times 2$ trial principal submatrix is PSD (eigenvalues $\{0, 4\}$) with diagonal $u = 2$, and the principal-submatrix premise holds. However, $\Gamma_{S\cup\{a\}}$ has eigenvalue $-2$, so $Q_+ = \Gamma_{S\cup\{a\}} + 2I_3$ is singular and **$d_a = 0$**, causing division by zero in eq. (611–615). (Confirmed numerically below.)
  - Note: All three concrete models ($\Gamma_{\rm F}, \Gamma_{\rm C}, \Gamma_{\rm D}$) satisfy both missing conditions, so the error is purely in the stated generality of Prop 3, not in the concrete exchange identities.
- **Minimal fix:** Amend lines 591–593 to require that on every labeled augmented support $S \cup \{a\}$ ($a$ a fresh label), the augmented uncertainty matrix $\Gamma_{S \cup \{a\}}$ is Hermitian positive semidefinite with diagonal $\Gamma_{aa} = u$ (or replace $u$ in $d_a$ by $\Gamma_{aa}$), and each $P$-slot trial uses its principal submatrix.

### Issue 2 — [MAJOR] Prop 2(d) Berkson premise does not deduce the residual-averaged-quadratic hypothesis, and the averaged-quadratic proof omits definitions and mishandles decoupled $S \setminus \{j\}$
- **Lines:** 452–462, 499–504 (and 527–537)
- **Problem:**
  1. **Unbridged Berkson-to-residual link:** Lines 452–454 invoke "the Berkson working premise that the centered soft-symbol error is independent of the omitted-path residual driving the soft detector." The proof (lines 488–504) never deduces eq. (457) or the conditional-mean-zero residual assumption from this premise. Even for the second interpretation (profiling the residual-averaged quadratic), Berkson independence of $\epsilon$ from the omitted-path residual is **not sufficient**: in the physical model (line 76), the residual $\eta = Y - (H_s \phi_j + H_w \phi_w)$ also contains the thermal noise $n$ and any other physical paths. Because the frozen $(\bar x, v)$ was computed by a detector running on $Y$ (which includes $n$), conditioning on $(\bar x, v, H_s, H_w)$ does not force $\mathbb E[\phi_i^H n \mid \bar x, v, H_s, H_w] = 0$. The `\textbf{Gap.}` paragraph (lines 527–537) honestly flags single-frame noise variance and detector absorption of the omitted path, but leaves the impression that the averaged-quadratic interpretation follows from Berkson independence alone. Also, $\mathbb E[\|\eta\|^2 \mid \bar x, v, H_s, H_w] < \infty$ is implicitly needed for the averaged quadratic to exist.
  2. **Undefined $Y_{\rm sig}, \eta$ and $h_R$ slip in lines 499–504:** The proof writes $Y = Y_{\rm sig} + \eta$ without defining either symbol. If other decoupled retained atoms $R = S \setminus \{j\}$ are present (allowed by lines 431–434), taking $Y_{\rm sig} = H_s \phi_j + H_w \phi_w$ means zero conditional-mean projections on the three columns $\phi_j, \phi_c, \phi_w$ (lines 459–462) do **not** make "the linear term in $h$ the same as for $Y_{\rm sig}$" on the $h_R$ coordinates (the $h_R$ terms cancel between $S_c$ and $S_w$ by decoupling, not by matching $Y_{\rm sig}$).
- **Minimal fix:** (a) Define $Y_{\rm sig} := H_s \phi_j + H_w \phi_w$ and $\eta := Y - Y_{\rm sig}$ explicitly; (b) state plainly that the Berkson working premise motivates — rather than by itself implies — the direct hypothesis $\mathbb E[\phi_i^H \eta \mid \bar x, v, H_s, H_w] = 0$ for $i \in \{j, c, w\}$ with $\mathbb E[\|\eta\|^2 \mid \bar x, v, H_s, H_w] < \infty$ (which additionally requires zero conditional-mean projection of thermal noise $n$ and any other physical paths); (c) in lines 499–504, state that decoupling splits the averaged quadratic into an $R$-block (identical for $S_c, S_w$ and both $g$) plus the $\{j, t\}$-block, on which zero conditional-mean projections on $\phi_j, \phi_c, \phi_w$ reduce the linear term to that of $Y_{\rm sig}$.

### Issue 3 — [MINOR] Delay domain $\ell_i \in \{0, 1, \dots, L\}$ (and $\nu_i \in \mathbb R$) is not explicitly stated in the standing assumptions
- **Lines:** 30, 57–74, 148–155, 178, 214–219
- **Problem:** Section 1.1 assumes $0 \le L < N$ and calls $L$ "maximum integer delay" in the table, but never formally constrains path parameters to $\ell_i \in \{0, 1, \dots, L\}$ and $\nu_i \in \mathbb R$. Proof line 178 ("For $d \ne 0$, the delay range ensures $d \not\equiv 0 \pmod N$") and Remark line 214 (vanishing diagonal of $T_{\ell_j} T_{\ell_i}^H$ for $\ell_i \ne \ell_j$) fail if $\ell_j - \ell_i \in N\mathbb Z \setminus \{0\}$ (e.g., $\ell_i = 0, \ell_j = N$ with constant $v$ gives $|\mathcal E_{ij}| = u > 0 = \|v - (u/N)\mathbf 1\|_1$).
- **Minimal fix:** Add "Every path has integer delay $\ell_i \in \{0, 1, \dots, L\}$ and real Doppler $\nu_i \in \mathbb R$" at lines 58–59.

### Issue 4 — [MINOR] Unproved/under-specified $m > 2$ "sufficient construction" and prematurely closed `afdmprop` environment in Prop 2
- **Lines:** 255–262, 424–428
- **Problem:**
  1. Lines 424–428 state that for a co-delay block of size $m > 2$, "the corresponding sufficient construction is to preserve the exact operator on its designated invariant sum subspace and bound the restriction to its orthogonal contrast subspace below by $c_0 u I$." Neither "designated invariant sum subspace" nor sufficiency for $m > 2$ is defined or proved. Specifically, if $m = 3$ and only two atoms coalesce while the third sits at a distinct Doppler, the exact $3\times 3$ block has rank $2$ at coincidence; preserving the 2-atom split reward requires preserving the exact operator on the full $(m-1)$-dimensional range at coincidence, not merely a 1D sum direction.
  2. `\begin{afdmprop}...\end{afdmprop}` closes at line 262 with only a prose overview, placing parts (a)–(d) and post-proof discussion paragraphs outside the theorem environment, which blurs formal claims vs. remarks.
- **Minimal fix:** Place the formal statements of parts (a)–(d) inside the proposition environment (or separate propositions), and clarify lines 424–428 as a design prescription specifying that the preserved invariant subspace must contain the range of the exact block at the targeted coincidence (or prove the general-$m$ statement explicitly).

### Issue 5 — [MINOR] Prop 2(d) isolation wording ("removed with exactly that effect") and undefined $\mathcal G_g$ notation
- **Lines:** 431–434, 441–446, 451, 497
- **Problem:**
  1. Line 433–434 says other retained coordinates "are decoupled from it and from the two trial candidates, or have already been removed with exactly that effect." Eliminating *coupled* retained atoms via Schur complement modifies $T$, $q_g$, and $b_i$; only absent ($S = \{j\}$) or normal-equation-decoupled ($B_R^H \phi_i = 0$ and $\ell_i \notin \{\ell_k : k \in R\}$ for $i \in \{j, c, w\}$) coordinates leave eq. (444) intact.
  2. $\mathcal G_g(c)$ (line 444) and $\mathcal G_g(w)$ (line 497) are used without formal definition $\mathcal G_g(t) := J_g^*(S) - J_g^*(S \cup \{t\})$ (and without writing $m_g = \mathcal G_g(c) - \mathcal G_g(w)$) and do not appear in the notation table.
  3. Line 451 writes "its delay is distinct" without repeating "from $S$".
- **Minimal fix:** Replace lines 433–434 with "$S = \{j\}$, or all coordinates in $R = S \setminus \{j\}$ satisfy $B_R^H \phi_i = 0$ and $\ell_i \notin \{\ell_k : k \in R\}$ for $i \in \{j, c, w\}$"; define $\mathcal G_g(t) := J_g^*(S) - J_g^*(S \cup \{t\})$ before eq. (444) (and add it to the notation table); write "distinct from $S$" at line 451.

### Issue 6 — [MINOR] Corollary 1 implicitly specializes $\Gamma$ and omits the coordinate-frame note for non-diagonal $\mathcal P$
- **Lines:** 543–561
- **Problem:** Line 545 introduces an arbitrary PSD $\Gamma$ and an arbitrary PD $\mathcal P \succ 0$. Line 547 then writes "$p^H \mathcal K p = p^H \mathcal P p + \beta\|B_S p\|^2 + \beta u(1-\zeta)$" for "the phase-aligned exact co-delay pair" without explicitly stating that $\Gamma$ agrees with the exact co-delay block on that pair (e.g., $\Gamma_{\rm C}$ or $\Gamma_{\rm F}$), and without noting that if $\mathcal P$ is non-diagonal, $(\mathcal P, B_S, \Gamma, p)$ must share the phase-aligned coordinates (equivalently $p = (1, -e^{-i\theta})^T/\sqrt2$ on the pair in original coordinates, where $D_N(\delta) = \zeta e^{i\theta}$). Line 555 then reverts to general PSD $\Gamma$ for eq. (560) at fixed $\mathcal P, \beta$.
- **Minimal fix:** State at line 547 "When $\Gamma$ agrees with the exact co-delay block on a pair (e.g., $\Gamma_{\rm C}$ or $\Gamma_{\rm F}$), expressed in the phase-aligned coordinates of Proposition~\ref{prop:af-split}(c) (with $\mathcal P$ transformed congruently if non-diagonal), ..." and at line 555 "For any PSD $\Gamma$ and fixed $\mathcal P, \beta$, adding $r p p^H$ to $\Gamma$...".

### Issue 7 — [MINOR] Notation, wording, and rounding-presentation slips across remarks and proofs
- **Lines:** 180–181, 214, 236, 244, 267, 331, 727–738
- **Problem:**
  1. Line 244 (Modulation-independence remark): uses $\delta$ in the OTFS formula without defining $\delta = \nu_j - \nu_i$ in that section (the notation table defines $\delta = \nu_c - \nu_j$).
  2. Lines 180, 181, 236: write $\widehat v[d]$ instead of $\widehat v[d \bmod N]$ as in eq. (143) (well-defined by $N$-periodicity of eq. (137), but inconsistent).
  3. Line 214: "Different integer shifts have no common diagonal in the relative shift" is awkward; clearer: "the relative cyclic shift $T_{\ell_j} T_{\ell_i}^H$ has zero diagonal" (again using $\ell_i \in \{0,\dots,L\}$, $L < N$).
  4. Line 267 (Prop 2(a)): $c, w$ should be stated explicitly as fresh labels not in $S$.
  5. Line 331 (Prop 2(c)): when $\zeta = 0$, the reciprocal rephasing phase is non-unique (any phase yields $u\zeta = 0$).
  6. Lines 727–738 (In-memory algebra checks): scientific notation omits `\times` (`1.21\,10^{-15}` instead of `1.21\times 10^{-15}`); also reports ceiling-rounded figures (`2.24e-16`, `8.90e-17`, `1.12e-16`) as exact discrepancies ("agreed ... to", "largest discrepancy ... was") where `astra-proofs-raw-20261119.md` (lines 791–792) reports `2.23e-16`, `8.89e-17`, `1.11e-16`.
- **Minimal fix:** Define $\delta = \nu_j - \nu_i$ at line 243; standardize $\widehat v[d \bmod N]$; clarify line 214 and fresh labels $c,w \notin S$; add `\times` and align rounding ("at most" or standard rounded values) in lines 727–738.

---

## 3. Conventions vs. Code & Scope Audit

| Convention / Requirement | `.tex` definition | Code / Protocol reference | Status |
|---|---|---|---|
| $D_N(z)$ normalization & phase | $\frac1N \sum_{t=0}^{N-1} e^{2\pi i z t / N}$ (line 135) | `physical.py:dkernel` (`exp(1j*pi*(n-1)*t/n)*sinc(t)/sinc(t/n)` with $t$ wrapped to $[-n/2, n/2)$) | **Exact match** (all $z \in \mathbb R$, incl. $z \in N\mathbb Z$) |
| Chirp shift $2Nc_1 d$ & prefactor | $d = \ell_j - \ell_i$, $z = \nu_j - \nu_i + 2Nc_1 d$, prefactor $e^{2\pi i c_1(\ell_i^2 - \ell_j^2)}$ (lines 139–143) | `physical.py:projected_variance` (lines 15–17), `geometry_reopen_variant.py:_gamma_cross` (lines 65–67) | **Exact match** |
| $u = \sum v$ and $\widehat v$ | $u = \sum_{n=0}^{N-1} v_n$, $\widehat v[k] = \sum_{n=0}^{N-1} v_n e^{-2\pi i n k / N}$ (lines 86, 137) | `np.sum(v)`, `np.fft.fft(v)` (`physical.py`, `geometry_reopen_variant.py`, `codelay.py`) | **Exact match** |
| CPP phase & column domain | Wrapped $k=t-\ell<0$: multiplier $e^{2\pi i c_1(N^2 + 2Nk)}$ ($=1$ under $N$ even, $2Nc_1 \in \mathbb Z$), time-domain columns $\phi_i = U_i \bar x$ (lines 68–73, 654–666) | `twofft.py:TimePathOps.responses_time`, `geometry_reopen_variant.py:_responses`, `compact_state.py:CPPField` (lines 31–32) all match time-domain $U_i \bar x$ and CPP factor. **Domain note:** `physical.py:regressors` (line 27) applies an extra outer forward DAFT $\mathcal A$, returning AF-domain $\mathcal A U_i \bar x$; by unitarity of $\mathcal A$, $B^H B$, $B^H Y$, and $\Gamma_{\rm F}$ are identical in both domains. | **Exact match** (up to unitary $\mathcal A$ in `physical.py:regressors`) |
| Normal system $Q, b, J^*$ | $Q_{g,S} = B_S^H B_S + \Gamma_{g,S} + \lambda I$, $b_S = B_S^H Y$, $J_g^*(S) = \|Y\|^2 - b_S^H Q_{g,S}^{-1} b_S$ (lines 117–122) | `geometry_reopen_variant.py:_system` (lines 79–84), `PROTOCOL.md` (lines 29–31), `compact_state.py` (lines 58–96) | **Exact match** |
| EM-SBL precision & $\beta$ update | $\mathcal K = \mathcal P + \beta(B_S^H B_S + \Gamma)$; post-corollary note (lines 580–583) notes $\Sigma_{ii} + |\hat h_i^{\rm post}|^2$, next noise precision, and pruning | `sbl_rx.py:sbl_em` (lines 100–103, 129–141): $\Gamma$ enters both E-step precision `A = beta*(B^H B + Gamma) + diag(1/gamma)` and M-step `beta_new` (`mu^H Gamma mu` and `tr((B^H B + Gamma) Sigma)`) | **Exact match** |
| Numerical tolerances & `codelay.py` complexity | $10^{-6}$ duplicate tolerance, $10^8$ condition fallback, $10^{-10}(1+|J_{\rm old}^*|)$ guard, $10^{-7}(1+|J_{\rm trial}^*|)$ winner check, dense $O(PM)$ allocation in frozen `codelay.py` (lines 705–706, 713–721) | `geometry_validation.py` (lines 270–271, 323, 349, 362), `geometry_reopen_variant.py` (lines 98, 173, 257), `codelay.py` (lines 15–18) | **Exact match** |
| **Scope check** | Prop 2(d) stated as a sufficient inner region (lines 260–261, 430, 476, 536–537); Corollary 1 explicitly disclaims any ARD, channel-error, or FER ordering theorem (lines 578–584); Empirical remark matches result cards `res-20261118-03`, `06`, `res-20261119-01`..`04` (`13,600` keys, `155` differing bit-hashes, post-hoc absorption + direct-term shortfall, uncertain doublet FER). | Brief requirements & result cards | **Pass** (no FER/ARD ordering claim; no exact boundary overclaim) |

---

## 4. Independent Numerical Verification

All checks were run with `/opt/anaconda3/bin/python` using an independent script outside the repository (`/tmp/agy_proof_check/verify_all.py`, seed `20261119`).

| Check | Setup | Max absolute error |
|---|---|---|
| **Prop 1:** full eq. (141) vs. explicit $\operatorname{tr}(U_i^H U_j \operatorname{diag}(v))$ built from `physical.regressors` (heteroscedastic $v \ge 0$, fractional Dopplers, negative $d$, resonant cross-delay pair $z=0$ and $z=N$) | $N=16, a_1=3$ ($u=24.28$)<br>$N=32, a_1=5$ ($u=40.98$)<br>$N=64, a_1=-7$ ($u=81.78$) | `2.370e-14` (`9.761e-16` $\cdot u$)<br>`3.390e-14` (`8.273e-16` $\cdot u$)<br>`2.141e-13` (`2.618e-15` $\cdot u$) |
| **Prop 1:** eq. (141) vs. time-domain $U_i = M_{\nu_i} T_{\ell_i} \mathcal A^H$ | $N=16 / 32 / 64$ | `3.780e-14` / `3.874e-14` / `9.996e-13` |
| **Prop 1:** eq. (141) vs. `physical.projected_variance` | $N=16 / 32 / 64$ | `5.539e-14` / `1.829e-13` / `6.945e-13` |
| **Prop 1:** co-delay identity $\Gamma_{ij} = u D_N(\nu_j - \nu_i)$ (heteroscedastic $v$) | $N=16 / 32 / 64$ | `1.513e-14` / `3.285e-14` / `4.452e-14` |
| **Prop 1:** `physical.dkernel` vs. $\frac1N \sum_t e^{2\pi i z t/N}$ | $N=16 / 32 / 64$ | `2.281e-15` / `4.463e-15` / `8.492e-15` |
| **Prop 1:** cross-delay bound eq. (150) & lines 195–198 $N=1024$ bounds | All off-delay pairs; $|d|=2,10,102$ | `0` violations; exact bounds `0.079579 < 0.080`, `0.007256 < 0.0073`, `0.000977 < 0.00098` |
| **Prop 1 Remark:** OTFS co-delay formula (lines 244–245) | $N=48$ ($m_0=6, k_0=8$), heteroscedastic $v$, $\ell=5$, fractional $\delta$ | `1.404e-14` |
| **Prop 2(a):** $K = A - B_{\rm fit}$ and $K = m_{\rm D} - m_{\rm C}$ via `geometry_reopen_variant._system` | 50 random complex trials ($N=32, P=4$) | `1.177e-14` (`K - (A - B_fit)`); `0.000e+00` (`K - (m_D - m_C)`) |
| **Prop 2(b):** coincidence convergence at $\delta = 10^{-8}$ | $N=32, P=3$ | `|h_Dj - H0/2| = 1.827e-09`, `|h_Dc - H0/2| = 4.121e-09`, `|A - u|H0|^2/2| = 3.691e-09` (exact at $\delta=0$: `< 1e-14`) |
| **Prop 2(c):** fixed-$H$ saving eq. (340), Sherman–Morrison split reward eq. (354–356), finite-spacing $L(r)$ eq. (362–364) | Isolated & coupled ($\Gamma_{\rm F}$) supports; multiple $(g_+, g_-)$ incl. `C-hi` and $a < 0$; $\delta \in \{0.15, 0.35, 0.75, 1.0\}$; $r \in \{0, u\zeta, u, 3.5u\}$ | Fixed-$H$: `3.553e-15`<br>Split reward: `4.830e-15`<br>$L(r)$: `8.112e-15` |
| **Prop 2(d):** isolated admission gain eq. (444) ($\kappa \ne D$ and $\kappa = D$) & endpoint ties at $r_w = \theta_{\rm D}(\zeta), \theta_{\rm C}(\zeta)$ | $\delta \in \{0, 0.25, 0.5, 0.85, 1.0\}$ | $\mathcal G_g(c)$: `8.527e-14`<br>Endpoint tie: `5.684e-14` |
| **Corollary 1:** fixed-prior curvature, coincidence $1/\alpha$ limit (with other atoms + full $\Gamma_{\rm F}$), rank-one variance update eq. (560) | General Hermitian PD $\mathcal P$, $\beta \in \{0.4, 2.5\}$, $\alpha \in \{0.2, 1.7, 12\}$, $r \in \{0, 0.3u, u, 4u\}$ | Curvature: `1.030e-13`<br>$1/\alpha$ limit: `6.812e-13`<br>Eq. (560): `4.163e-17` |
| **Prop 3:** `compact_state.exchange_scores` vs. direct Cholesky refit (`_system`) across $\Gamma_{\rm F}, \Gamma_{\rm C}, \Gamma_{\rm D}$ | $P=1$ & $P=4$, $M=55$ bank including exact duplicates of deleted slot $i$ (no-ops) and of retained slot $j \ne i$ | $\Gamma_{\rm F}$: `1.421e-14`<br>$\Gamma_{\rm C}$: `7.105e-15`<br>$\Gamma_{\rm D}$: `7.105e-15` |
| **Prop 3:** `CPPField.correlate` vs. explicit $\phi_a^H Y$ | Integer $2Nc_1$ & non-integer $2Nc_1$ | `1.568e-14` / `1.137e-14` |
| **Issue 1 counterexample:** non-PSD augmented $\Gamma_{S \cup \{a\}}$ with all $2\times 2$ submatrices PSD, $\Gamma_{aa}=u=2, \lambda=2$ | $P=2, E=0$ | `d_a = 0.000e+00` (exact zero Schur complement) |

---

## 5. What Is Genuinely New vs. Standard Results

Stated plainly:

- **Standard / off-the-shelf ingredients:**
  - Forming the errors-in-variables / expected-Gram normal matrix $B_S^H B_S + \Gamma_{\rm F} + \lambda I$ from second-order moments of $\epsilon = x - \bar x$ is textbook stochastic-design / errors-in-variables least squares.
  - Completing the square for $K = A - B_{\rm fit}$ (Prop 2(a)), $2\times 2$ Schur-complement elimination (Prop 2(d)), rank-one Sherman–Morrison updates for profiled quadratics and Gaussian covariances (Prop 2(c), Corollary 1), add-then-delete rank-one exchange downdating (Prop 3 eq. (611–615)), and FFT linear convolution for matched-filter banks are all standard linear algebra and signal processing.

- **Genuinely domain-specific / new contributions:**
  1. **Closed-form AFDM projected uncertainty and its waveform characterization (Prop 1 + Remarks):** The exact factorization $(\Gamma_{\rm F})_{ij} = e^{2\pi i c_1(\ell_i^2 - \ell_j^2)} D_N(\nu_j - \nu_i + 2Nc_1(\ell_j - \ell_i)) \widehat v[(\ell_j - \ell_i) \bmod N]$ for heteroscedastic APP variances under AFDM synthesis, proving that the co-delay block depends on $v$ *only* through its scalar sum $u = \sum_n v_n$, bounding the discarded cross-delay residual $\mathcal E$ via both chirp-shifted Dirichlet decay (pinpointing the $a_1 d + \Delta\nu = 0$ resonance) and $\|v - (u/N)\mathbf 1\|_1$, and characterizing heteroscedastic co-delay exactness across unitary syntheses via the unimodular/time-flat iff condition $|W_{tn}|^2 = 1/N$ (explicitly contrasting AFDM/OFDM against rectangular-pulse OTFS, where delay-row variance sums leak into the co-delay block).
  2. **Spectral decoupling of the co-delay acquisition vs. estimation mechanisms (Prop 2(b)–(c) + Corollary 1):** While each step is elementary Sherman–Morrison algebra, assembling the sum-mode ($s$) vs. contrast-mode ($p$) decomposition cleanly isolates why scalar $\Gamma_{\rm D}$ induces an $O(u)$ duplicate-path acquisition reward at coincidence (collapsed to $O(\lambda)$ by exact $g_+ = 2u$ regardless of $g_-$) while exact $\Gamma_{\rm C}$ collapses unresolved-contrast curvature ($g_- \to 0$, marginal variance $1/\alpha$ under isotropic prior) and why a contrast-only ridge $r p p^H$ leaves coincidence acquisition invariant while quantifying both the fixed-prior variance drop $1/(1+\beta r v_p)$ and the finite-spacing doublet penalty $L(r)$.
  3. **AFDM-specific exact-exchange boundary (Prop 3):** Folding the AFDM CPP-extended chirp shift into one linear-convolution correlation field per active column (valid for fractional Dopplers) and identifying the exact structural condition (principal submatrix of an augmented PSD model) that distinguishes exact fast exchange ($\Gamma_{\rm F}, \Gamma_{\rm C}, \Gamma_{\rm D}$) from support-recomputed spectral projectors.
