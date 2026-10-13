# Proof Skeleton — AFDM FYP Report

**Note**: this is an engineering report, not a theory paper. The "proofs" are the analytical complexity arguments, modelling derivations, and statistical procedures. There are no `\begin{theorem}` blocks; all derivations are inline in §2 or in the Appendix.

## 1. Inventory of derivations to verify

| ID | Where | Statement (informal) | Quantifiers / scope |
|----|-------|----------------------|---------------------|
| **D1** | §2.4 eq:Qlinear | $Q = (2k_{\max}+1)\ell_{\max} = O(N)$ under fixed-$f_s$ | as $N \to \infty$, fixed $\tau_{\text{spread}}, v_{\max}, f_c, f_s$ |
| **D2** | §2.4 alt-conv | $Q = O(N)$ under fixed-$\Delta f$ ($f_s = N\Delta f$) | as $N \to \infty$, fixed $\tau_{\text{spread}}, v_{\max}, f_c, \Delta f$ |
| **D3** | §2.4 eq:omp_cost | $C_{\text{OMP}} = O(P\cdot N \cdot Q) = O(P \cdot N^2)$ | per frame, target sparsity $P$, dictionary $Q = O(N)$ |
| **D4** | §2.7 eq:classcomplex | $C_{\text{classical}} = O(P \cdot N^2)$ per frame | $T_{\text{out}}, T_{\text{mp}}, P, k_{\text{leak}}$ all constant in $N$ |
| **D5** | §2.7 eq:headcomplex | $C_{\text{head}} = O(M N + M P^2 N) = O(M P^2 N)$ | $M, P, K_{\text{add}}$ constant in $N$ |
| **D6** | §2.5 line 168 | MP-BP iteration cost $O(N)$ per iter | sparse factor graph with $P(2k_{\text{leak}}+1) \approx 28$ edges/row |
| **D7** | §2.5 line 168 | Dense MMSE costs $O(N^3)$ per frame | full $N\times N$ matrix inverse |
| **D8** | §2.6 lines 262-269 | Force-topk bias patch ($b_{\text{learned}} \approx -8 \to b_{\text{patch}} = +10$) is selection-invariant under argtopk | finite $\Delta b$ added uniformly to all $M$ logits |
| **D9** | §2.2 eq:dirichlet | Fractional-Doppler residual decomposes into $2k_{\text{leak}}+1$ virtual integer-bin taps via Dirichlet kernel of half-width $k_{\text{leak}} = 2$ | per physical path; assumes $k_{\text{leak}}$ bin truncation has negligible tail |
| **D10** | §2.3 eq:pilot_projection | Pilot projection $x_p^H y$ yields a structured-interference term $\sqrt{1-\rho_p}\, x_p^H H_{\text{eff}} x_d$ that does not vanish with SNR | linear algebra under model eq:afdm_model |
| **D11** | App B eq for CP | Two-sided 95% Clopper-Pearson CI is $[F^{-1}_{k,n-k+1}(0.025), F^{-1}_{k+1,n-k}(0.975)]$ via Beta inverse CDF | $k$ bit-errors out of $n$ Bernoulli bits, exact-binomial inversion |
| **D12** | App D | Continuity-corrected McNemar $\chi^2 = (|n_{10}-n_{01}|-1)^2/(n_{10}+n_{01})$ with one-df asymptotic chi-square distribution under $H_0$: same bit-wise error probability | requires sufficient discordant pairs and pair-level independence |
| **D13** | App C | Recall against Dirichlet-expanded oracle support $S_{\text{oracle}}$: $\text{recall} = |\tilde{S}_{\text{OMP}} \cap S_{\text{oracle}}| / |S_{\text{oracle}}|$ with $\tilde{S}_{\text{OMP}}$ being the Dirichlet-expansion of OMP support into virtual-tap lattice | bookkeeping; $|S_{\text{OMP}}|=P=8$ vs $|S_{\text{oracle}}|\approx 28$ |

## 2. Dependency DAG

```
D9 (Dirichlet expansion)
   ↓
D6 (MP-BP O(N) per iter, uses sparse-edge count from D9)
   ↓
D4 (Classical complexity, sums OMP + DA-LS + MP-BP)
   ↑
D3 (OMP cost, uses Q = O(N) from D1/D2)
   ↑
D1, D2 (Q = O(N) under two scaling conventions, independent)

D5 (Head complexity) — independent of D1-D4 except for the M·N term

D8 (Force-topk invariance) — independent

D10 (Pilot interference floor) — independent of complexity chain

D11, D12, D13 (Statistical procedures) — independent of derivations chain
```

No cycles detected.

## 3. Assumption ledger (key implicit assumptions)

| Derivation | Stated assumptions | Implicit / unverified assumptions |
|------------|--------------------|-----------------------------------|
| D1 | $f_s$ held fixed as $N \to \infty$; $\tau_{\text{spread}}, v_{\max}, f_c$ constant | Big-$O$ is uniform in $N$; constant absorbed factors do not depend on $\tau, v, f_c$ explicitly stated |
| D2 | $\Delta f$ held fixed as $N \to \infty$; $f_s = N\Delta f$ scales linearly | Same as D1; unstated whether the same $O(\cdot)$ constant works for both conventions |
| D3 | $P$ held fixed in $N$; LS solve is $O(s^2)$ for $s\le P$, dominated by matched-filter step | LS-step constant absorbed; numerical conditioning of $\Phi_S^\dagger$ ignored |
| D4 | $P, T_{\text{out}}, T_{\text{mp}}, k_{\text{leak}}$ all constants in $N$ | What does "constant" mean for $P$? In real UWA $P$ may scale with bandwidth |
| D5 | $M, K_{\text{add}}, P$ constant in $N$; pair_mlp / scorer are O(1) per evaluation in 16-dim ops | The $P^2 \cdot N$ term — see micro-claim MC-5 |
| D6 | Sparse factor graph; $\approx 28$ edges per row | Edge count constant in $N$; the messages converge (no convergence proof, just iteration cap $T_{\text{mp}}$) |
| D7 | Dense MMSE = full $N\times N$ inversion | Could be $O(N^{2.376})$ with Strassen-type tricks but $O(N^3)$ is the standard |
| D8 | $\Delta b = +18$ added uniformly to all candidate logits; argtopk uses pure rank | Tie-breaking rule for ties under argtopk not specified |
| D9 | $k_p^{\text{real}} - k_p \in [-0.5, 0.5]$ (fractional-Doppler residual after rounding); truncation to $\pm k_{\text{leak}} = \pm 2$ has negligible tail | Truncation tail bound not given; energy outside $[-2, 2]$ assumed negligible |
| D10 | Linear model in $\mbx$; pilot $x_p$ deterministic Zadoff-Chu | $H_{\text{eff}}$ linear in channel; treats $H_{\text{eff}}\,x_d$ as residual interference but not formally bounded |
| D11 | Bits are i.i.d. Bernoulli($p$) draws with same $p$ | Bits within a frame are correlated through the channel (same $H_{\text{eff}}$ realization) — the i.i.d. assumption is not literally true |
| D12 | $H_0$: bits have same per-bit error probability under both receivers; pair-level independence; $n_{10}+n_{01}$ large enough for $\chi^2_1$ asymptotic | Pair-level independence is **not given** — bits within a frame share the channel realization, so within-frame discordant pairs are correlated |
| D13 | $\tilde{S}_{\text{OMP}}$ is the Dirichlet-expansion of physical OMP support into the virtual-tap lattice | $\tilde{S}_{\text{OMP}}$ is computed deterministically from the same Dirichlet kernel as $S_{\text{oracle}}$; bookkeeping is unambiguous |

## 4. Typed symbol table

| Symbol | Type | Domain |
|--------|------|--------|
| $N \equiv N_{\text{sub}}$ | scalar (positive integer), parameter | $N \to \infty$ for asymptotic claims; $N = 1024$ for concrete numbers |
| $P \equiv P_{\text{path}}$ | scalar (positive integer) | physical paths; $P = 8$ in experiments |
| $k_{\text{leak}}$ | scalar (positive integer) | $k_{\text{leak}} = 2$ in experiments |
| $\ell_{\max}$ | scalar (positive integer) | $\lceil \tau_{\text{spread}} f_s \rceil$ |
| $k_{\max}$ | scalar (positive integer) | $\lceil v_{\max} f_c N / (c f_s) \rceil$ |
| $Q$ | scalar (positive integer) | $(2 k_{\max} + 1) \ell_{\max}$, dictionary size |
| $M$ | scalar (positive integer) | $M = 96$, candidate budget for the head |
| $K_{\text{add}}$ | scalar (positive integer) | top-$K$ atoms appended by head |
| $H_{\text{eff}}$ | matrix in $\mathbb{C}^{N \times N}$ | chirp-domain effective channel |
| $h_p$ | scalar in $\mathbb{C}$ | per-path complex gain |
| $\rho_p$ | scalar in $(0,1)$ | pilot power fraction; $\rho_p = 0.5$ |
| $b_{\text{learned}}, b_{\text{patch}}$ | scalar | scorer output bias; $-8 \to +10$ |
| $\Delta b$ | scalar | $b_{\text{patch}} - b_{\text{learned}} = 18$ |
| $s_i, z_i$ | scalar | logit and pre-bias logit per candidate $i$ |
| $n_{10}, n_{01}$ | non-negative integers | discordant pair counts |
| $k, n$ | non-negative integers | observed bit-errors / total bits |

## 5. Limit-order map

| Statement | Limit | Uniformity |
|-----------|-------|------------|
| D1: $Q = O(N)$ under fixed-$f_s$ | $N \to \infty$ | Constants depend on $\tau_{\text{spread}}, v_{\max}, f_c, f_s$ — *not* uniform across these |
| D2: $Q = O(N)$ under fixed-$\Delta f$ | $N \to \infty$ | Constants depend on $\tau_{\text{spread}}, v_{\max}, f_c, \Delta f$ |
| D3: $C_{\text{OMP}} = O(P N^2)$ | $N \to \infty$, $P$ fixed | Not uniform in $P$ |
| D4: $C_{\text{classical}} = O(P N^2)$ | $N \to \infty$ | Same as D3, also depends on $T_{\text{out}}, T_{\text{mp}}, k_{\text{leak}}$ |
| D5: $C_{\text{head}} = O(M P^2 N)$ | $N \to \infty$ | Not uniform in $M, P$ |

## 6. Micro-claim inventory (high-impact only)

### MC-1: Q = O(N) under fixed-fs
- **Context**: $\ell_{\max} = \lceil \tau_{\text{spread}} f_s \rceil$, $k_{\max} = \lceil v_{\max} f_c N / (c f_s) \rceil$.
- **Goal**: $Q = (2k_{\max}+1)\ell_{\max} \in O(N)$ as $N \to \infty$.
- **Rule**: $\ell_{\max} = O(1)$ since $f_s$ fixed; $k_{\max} = O(N)$; product is $O(N)$.
- **Side-conditions**: $f_s, \tau, v_{\max}, f_c$ all positive constants in $N$. ✓

### MC-2: OMP cost = O(P·N·Q)
- **Context**: Each iteration of OMP solves $\arg\max_j |\Phi_j^H r|$ (cost $O(N\cdot Q)$ for matched-filter eval) plus an $s\times s$ LS problem (cost $O(s^2)$). Total iterations: $P$.
- **Goal**: Total cost $\sum_{s=1}^{P} (NQ + s^2) = O(P N Q + P^3) = O(P N Q)$ assuming $P^3 = o(NQ)$.
- **Side-condition**: $P^3 \le c \cdot NQ$ for some constant $c$ — verified since $P = 8$ and $NQ \ge N \approx 10^3$.

### MC-5: Head O(M·P²·N) — **derivation needs scrutiny**
- **Context**: pair_mlp on $M\cdot P$ pairs (P up to 28 virtual taps); scorer on $M$ vectors.
- **Stated formula**: $C_{\text{head}} = O(M N + M P^2 N) = O(M P^2 N)$.
- **Issue**: Where does $P^2$ come from? 
  - $M\cdot N$ term — the M dictionary-column projections $\Phi_i^H r$, each cost $O(N)$. ✓
  - $M\cdot P^2 \cdot N$ term — what costs $P^2 N$? The pair-feature $|\Phi_i^H \Phi_s|$ takes $O(N)$ per pair, with $M\cdot P$ pairs, giving $O(M P N)$ — *not* $O(M P^2 N)$.
  - Possibly the $P^2$ comes from a separate component (e.g. a $P\times P$ LS conditioning step in the head pipeline), or it is a typo for $P$.
- **Action**: Reviewer should check whether the formula's $P^2$ term is correctly derived or is a transcription error.

### MC-8: argtopk monotone-translation invariance
- **Context**: $s_i' = s_i + \Delta b$ for all $i \in \{1, \dots, M\}$, fixed $\Delta b \in \mathbb{R}$.
- **Goal**: $\arg\text{topk}(s_1', \dots, s_M') = \arg\text{topk}(s_1, \dots, s_M)$.
- **Rule**: Order is preserved under uniform translation: $s_i' > s_j' \Leftrightarrow s_i > s_j$.
- **Side-condition**: Tie-breaking rule is not specified — if `argtopk` breaks ties by index, both inputs produce identical output regardless of $\Delta b$. ✓

### MC-9: Dirichlet kernel formula
- **Context**: $\tilde{h}_{p,j} = h_p \cdot \sin(\pi(k^{\text{real}} - k - j)) / [N \sin(\pi(k^{\text{real}} - k - j)/N)]$.
- **Goal**: This is the standard discrete-time Dirichlet kernel for a length-$N$ DFT.
- **Rule**: Sum of $\tilde{h}_{p,j}$ over $j$ should approximate $h_p$ (Parseval).
- **Side-condition**: The sum over the $\pm k_{\text{leak}}$ truncation captures the dominant energy. The text claims "negligible tail" without bound.

### MC-12: McNemar χ² validity
- **Context**: bit-level paired comparison; $n_{10}, n_{01}$ over many bits per frame, many frames.
- **Goal**: $\chi^2_{\text{MN}} \overset{H_0}{\sim} \chi^2_1$.
- **Rule**: Standard McNemar — requires (i) discordant pairs sufficient ($n_{10}+n_{01} \ge \sim 25$ rule of thumb), (ii) discordant pairs are independent.
- **Side-conditions**: 
  - (i) text reports $p < 10^{-6}$ → very large discordant counts → asymptotic OK ✓
  - (ii) **bits within a frame share the channel realization** → bit-level pairs are NOT independent within a frame. This is an INSUFFICIENT_ASSUMPTION issue: the test as applied assumes pair-level independence that does not hold, which can inflate the χ² statistic relative to a frame-level test. The text does not discuss this.

## 7. Observed UNCLEAR / potentially problematic spots

| ID | Location | Issue type | Description |
|----|----------|------------|-------------|
| U1 | §2.7 eq:headcomplex | DIMENSION_TRACKING | $C_{\text{head}} = O(M P^2 N)$ — $P^2$ factor not traceable to a derivation step in the text |
| U2 | App D McNemar | INSUFFICIENT_ASSUMPTION | Bit-level pair independence assumed but not satisfied (within-frame correlation); could overstate significance |
| U3 | §2.2 eq:dirichlet | INTEGRABILITY_GAP | Truncation tail outside $\pm k_{\text{leak}}$ assumed negligible without bound |
| U4 | §2.4 D1 vs D2 | CONSTANT_DEPENDENCE_HIDDEN | $O(\cdot)$ constants depend on $f_s$ vs $\Delta f$ choice; text does not flag uniformity scope |
| U5 | §2.6 line 245 | UNCLEAR | "positive-class rate $\approx 3\%$" — $3 \times 96 / 28 \approx 10$, not 3% of 96 = ~3 positives per frame; reconcile |
| U6 | §2.4 line 100 | NORMALIZATION_MISMATCH | The fixed-$\Delta f$ derivation gives $k_{\max} = \lceil v_{\max} f_c / (c \Delta f) \rceil$ — note that the original formula (eq:kmax) divides by $f_s$, not $\Delta f$. Need to verify the algebra of ratio $f_c\cdot N / (c \cdot N \Delta f) = f_c/(c \Delta f)$ — this appears correct algebraically. |
