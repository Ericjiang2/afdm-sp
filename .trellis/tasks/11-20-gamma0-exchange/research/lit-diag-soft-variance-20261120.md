# Literature check: who uses diagonal/scalar soft-variance (D) in data-aided channel estimation? (2026-11-20)

Scope: reading only (arXiv full text via `pdftotext`, project notes). No simulations. Searches used no personal names.

## 0. Labels

- **N** = soft means or hard decisions in the dictionary, no uncertainty term derived from the symbol variance `v` (noise treated as constant/white, estimated or prior).
- **D** = uncertainty term that is scalar or diagonal and derived from `v` (or from the prior symbol power). Two sub-types, because they behave differently in support exchange:
  - **D-obs**: observation-space noise inflation with plug-in channel, e.g. `sigma^2 + sum|h_hat|^2 v` per sample. It does not penalise the coordinate being optimised.
  - **D-coord**: ridge on the Gram, `E[Phi^H Phi] = Phi_bar^H Phi_bar + u I` (our `u||h||^2` / A2 arm). This is the sub-type that rewards splitting a path.
- **F** = exact second moment projected onto the atoms (`Gamma_ij = tr(U_i^H U_j diag(v))`, or `A^H diag(|mu|^2+v) A` for an elementwise model). Keeps cross-atom coherence.
- Frequency-domain elementwise models (`y_k = H_k x_k`, `H = A beta`): the classical `E[x x^H] = mu mu^H + diag(v)` is diagonal in *subcarrier* coordinates, which is **F** in *tap/atom* coordinates (`A^H diag(.) A`). It equals D-coord only when `v` is constant and the atoms are orthogonal. This is my reading of the algebra (not a quoted claim); the rows below that use it say so.
- "Verified" = I read the equation in the full text (this session, or the 2026-11-18 notes for rows marked *prior*). "Partial" = read the relevant equations but not the whole paper.

## 1. Table

| # | Paper | Waveform | Fractional Doppler? | Support search / SBL? | N / D / F | Where (eq. / section) | Verified full text |
|---|---|---|---|---|---|---|---|
| **A. Off-grid (fractional) parameters AND support search/SBL AND data-aided** | | | | | | | |
| A1 | Y. Luo, Guan, Ge, Jiang, Meng, González G., "Data-aided CE and sensing with SBL for AFDM-ISAC", IEEE TCOM 74, 12485, 2026, doi 10.1109/TCOMM.2026.3720419 ([arXiv 2607.18881](https://arxiv.org/abs/2607.18881)) | AFDM, superimposed pilot, ULA | yes (off-grid, grid evolution) | SBL (D-GAMP-GESBL variant) | **N** (hard remap; observation noise isotropic `beta^-1 I_N`, estimated, not from `v`) | Alg. 1 l. 11; Eqs. (14), (17); Sec. III-B noise model | yes (*prior*, LaTeX source 11-18) |
| A2 | Wei, Yuan, Li, Yuan, Ng, "Off-grid CE with SBL for OTFS", IEEE TWC 2022 ([arXiv 2101.05629](https://arxiv.org/abs/2101.05629)) | OTFS | yes (off-grid SBL, 1D/2D) | SBL, on-grid index + off-grid hyperparameters | **N** in the data-aided extension: estimated symbols `x_hat` substituted into the measurement matrix | Remark 1 (Sec. IV), Eq. (23); Sec. VI-D, Fig. 9 (BPSK, sum-product detector) | yes |
| A3 | Mehrotra, Srivastava et al., "Data-aided CSI estimation using affine-precoded superimposed pilots in OTFS MIMO" ([arXiv 2305.15855](https://arxiv.org/abs/2305.15855)) | OTFS MIMO, AP-SIP | yes (fractional Doppler grid `G_tau x G_nu`) | SBL (EM, "DA-BL") | **N** for the channel E-step: `X_d` is an EM parameter updated by hard ML; noise covariance `R_v = blkdiag(R_w,d, R_w,p)` is noise-only. Mirror image: *channel* uncertainty enters the detector as `Xi I` (D-like, in the data direction) | Eqs. (29)-(30), (36)-(38), (40)-(42), Alg. 2 | yes (key sections); journal version not checked |
| A4 | Halder, Murthy, "CE and data detection in DS-spread channels" ([arXiv 2508.21373](https://arxiv.org/abs/2508.21373)) | OFDM/OTFS/OCDM/ODSS (UWA, delay-scale) | yes (off-grid delay and scale) | VB (FVB/SVB), path-based; OMP baseline | **N**: ICED uses detected symbols as virtual pilots; `w_E = [w_p; w]` is noise only | Sec. VII, Eqs. (56)-(57) | yes |
| A5 | Prasad, Murthy, Rao, "Joint approximately sparse CE and data detection in OFDM using SBL", IEEE TSP 2014 (IISc manuscript) | OFDM | no (integer taps) | SBL / EM (J-SBL, RJ-SBL, JK-SBL) | **N**: data `X` is an EM *parameter*, hard ML; posterior `Sigma` uses `X^(r)` only; *channel* covariance `C = F Sigma F^H` enters the detector | Eqs. (38), (40), (47) | yes |
| A6 | Wan, Zhu, Cheng, Xu, "Joint CFO, gridless CE and data detection for UWA OFDM" ([arXiv 2107.07101](https://arxiv.org/abs/2107.07101)) | OFDM (UWA) | continuous delay (gridless); Doppler only as one common residual CFO | VALSE (gridless line-spectral estimation, sparse prior) | **F**: per-subcarrier precision weight `E|d|^2 = |mu|^2+v`, pseudo-measurement noise `sigma^2/(|mu|^2+v)`, then gridless fit `h = A(theta) beta` with `diag(sigma_tilde^2)` | Eqs. (33)-(34), (35); product variance (20b), (21) | yes |
| **B. Fractional Doppler via basis/oversampling or known path parameters (no support search)** | | | | | | | |
| B1 | Huang, Guo, Zhang, Zakharov, "Message passing-based joint CE and detection for OTFS with superimposed pilots" ([arXiv 2309.08177](https://arxiv.org/abs/2309.08177)) | OTFS, SP | via GCE-BEM | no (BEM coefficients) | **F-weights**: `c_hat = d x_hat^* / (|x_hat|^2 + v_x)`, variance `v_d/(|x_hat|^2+v_x)`; diagonal messages (mean-field) | Eqs. (73)-(77) | partial |
| B2 | Ranasinghe, Ge, de Abreu, Guan, "Low-complexity JCEDD for AFDM with oversampling" ([arXiv 2410.05088](https://arxiv.org/abs/2410.05088)) | AFDM | yes (TD oversampling, path delay/Doppler known from prior RPE) | no (only path gains `h_p`) | **D-obs** (scalar Gaussian approximation): belief variance carries `sigma_x^2 |gamma|^2` and `sigma_h^2 sigma_x^2` terms | Eqs. (20), (27), (28); footnote 5 | yes |
| B3 | Li, Xiao, Tang, ... Slock, "JCE and signal detection for AFDM with time-domain pilot arrangement" (Eurecom, 2025) | AFDM, DPS-BEM | yes (BEM) | no | EP with Dirac-mixture moment matching; D/F not determined | abstract + structure only | **no** |
| B4 | Yogesh, Mattu, Chockalingam, "Iterative CE/detection for DZT-OTFS with superimposed pilot frames" (IISc) | DZT-OTFS | yes (fractional delay-Doppler per path, peak search) | no (per-path search, frame averaging) | **N** (detected data subtracted; no variance) | iteration Steps 1-2 (Fig. 2) | partial |
| **C. Integer delay-Doppler grid, SP / data-aided (D is exact or irrelevant here)** | | | | | | | |
| C1 | Mishra et al., "OTFS CE and data detection with superimposed pilots", IEEE TWC 2021 ([arXiv 2010.15066](https://arxiv.org/abs/2010.15066)) | OTFS SP | no (integer) | threshold / dictionary | **D-const (prior)**: `((sum sigma_h^2) sigma_d^2 + sigma_w^2) I`, constant, from prior power; hard decisions fill `Omega_d` | Eqs. (22), (46)-(48), (51) | yes (*prior*, 11-18 note) |
| C2 | Zheng, Wen et al., "CE for AFDM with superimposed pilots", IEEE TVT 2025 ([arXiv 2404.10232v1](https://arxiv.org/abs/2404.10232)) | AFDM SP | no (integer) | threshold + interference cancellation | **D-const (prior)**, Lemma 2 Eq. (18); data cancelled via `y - H_eff x_d` (Eq. 24) | as listed | yes (*prior*, arXiv v1 only) |
| C3 | Kanazawa et al., "Superimposed pilot-based OTFS: will it work?" ([arXiv 2501.15935v3](https://arxiv.org/abs/2501.15935), v3 Feb 2026) | OTFS SP, coded | no; v3 still lists fractional-Doppler thresholds as an open problem | threshold | **N** (threshold `3 sqrt(N_p(sigma^2+sigma_d^2))`, later `3 sqrt(N_p sigma^2)`) | Eqs. (24)-(25); conclusion | yes (*prior*; v3 re-grepped today) |
| C4 | Wang, Shen, Xing, An, Hanzo, "Joint Bayesian CE and data detection for OTFS in LEO", IEEE TCOM 2022 | OTFS | no (integer DD grid) | SBL / VBI | **F** (full expected Gram); uncertainty part is diagonal on the integer grid | Eqs. (59)-(60), App. B | yes (*prior*) |
| C5 | Ouchikh et al., ICASSP 2022 | OTFS SP | no | VB-EM | D-obs (observation whitening), per the 11-18 note | — | *prior*, not re-read |
| C6 | Thoota, Murthy, "Massive MIMO-OFDM with low-res ADCs: CRB, sparse CE, soft symbol decoding" (IISc preprint) | MIMO-OFDM | no (integer delay taps) | SBL / VB | **N**: `Phi` built from posterior *means* of decoded symbols | Alg. 4 l. 16, Eq. (25); iterative-algorithm section | partial |
| **D. Classical turbo / decision-directed CE (no sparse support search)** | | | | | | | |
| D1 | Yoon, Moon, "Soft-decision-driven CE for pipelined turbo receivers", IEEE TCOM 2011 ([arXiv 1104.0419](https://arxiv.org/abs/1104.0419)) | MIMO-OFDM | no | no (Kalman/LMMSE on taps) | **D-obs**: `Q_n = diag(sum_t (p_n(t,t) + |h_hat_t|^2) sigma_s^2(n,j,t))`; exact because TX streams are independent (my reading). Ignoring it costs MSE increasing in `sigma_s^2` | Eqs. (21)-(22), (27)-(28), mismatch analysis (41)-(46) | yes |
| D2 | Osinsky et al., "Data-aided LS CE in massive MIMO turbo receiver" ([arXiv 2003.09317](https://arxiv.org/abs/2003.09317)) | MIMO-OFDM | no | no | **D = F** (one scalar `h` per subcarrier): `E[x x^H] = E x E x^H + diag(E|x|^2 - |Ex|^2)`, rank-one inverse; later replaced by a fitted scalar `sigma^2 ~ C * mean(v)` | Eqs. (2)-(3), Sec. V | yes |
| D3 | Verenzuela et al., MICED ([arXiv 2104.14797](https://arxiv.org/abs/2104.14797)) | massive MIMO uplink | no | no | **D** scalar per UE: data-estimate error variance `(1 - sigma^2)` inside the interference correlation `Psi` | Eq. (21), "analysis with Gaussian symbols" subsection | partial |
| D4 | Nassirpour, Nguyen, Nguyen, "VB inference for time-varying massive MIMO: estimation and detection" ([arXiv 2505.10673](https://arxiv.org/abs/2505.10673)) | MIMO | no | VB (no path support) | **D = F** per user: `Sigma = (<gamma><|x|^2> I + ...)^-1`, `<A^H A> = <A>^H <A> + D` | Eqs. (19), (27)-(28) | partial |
| D5 | Liu, Crussière, Hélard, data-aided CE for TDS-OFDM ([arXiv 1201.0686](https://arxiv.org/abs/1201.0686)) | TDS-OFDM | no | no | **N**: soft symbol `X_hat` as normalised LS regressor; error enters only a scalar `sigma_W''^2 = sigma_W'^2 + sigma_I^2` | Eqs. (21)-(25) | partial |
| **E. Pilot-only fractional-Doppler SBL/OMP (data not in the dictionary; context)** | | | | | | | |
| E1 | Q. Luo et al. ([arXiv 2610.41997](https://arxiv.org/abs/2610.41997)); Cao et al., WCNC'26 ([arXiv 2602.10438](https://arxiv.org/abs/2602.10438)); Priya, Hong, Viterbo ([arXiv 2608.12524](https://arxiv.org/abs/2608.12524)); Li et al. IoV-AFDM SBL ([arXiv 2512.14776](https://arxiv.org/abs/2512.14776)) | AFDM / OTFS | yes | SBL / two-stage | not applicable (guard interval or dedicated frame; residual data leakage = scalar white noise `rho`) | per 11-18 note; 2512.14776 checked for pilot structure only | yes (*prior*) / partial |

Not re-read (cited as in the 11-18 notes only): Yin TWC'24 (integer grid, no data in dictionary), Nannuru.

### Unverified (abstract or secondary source only; no classification assigned)

| Paper | Why it matters | Status |
|---|---|---|
| Valenti, Woerner, "Iterative CE and decoding of PSA turbo codes over flat-fading channels", IEEE JSAC 19(9), 2001 | origin of hard/soft decision feedback CE; scalar flat fading | abstract only; PDF blocked |
| Song, Singer, Sung, "Soft input CE for turbo equalization", IEEE TSP 52(10), 2004 | soft-decision quality as effective noise in a Kalman update | known only through Yoon-Moon's description ("quality of the soft decisions as part of effective noise") |
| Fang, Rugini, Leus, "Block transmissions over doubly selective channels: iterative CE and turbo equalization", EURASIP JASP 2010 (and TSP 2008) | closest classical case: OFDM + BEM (Doppler harmonics) + turbo soft decisions | abstract only; both hosts blocked (TLS / bot wall) |
| Kocian, Fleury, TCOM 2003; Cozzo, Hughes, TCOM 2003 | EM/SAGE soft-symbol receivers (Gemini's suggestions in the positioning note) | abstract only; not audited |
| Ma, Ping, "Data-aided CE in large antenna systems", IEEE TSP 62(12), 2014 | cited by Osinsky as the weighted soft-LS reference | abstract only |
| Zheng et al., GLOBECOM 2025 (AFDM SP, message passing); Ku-Chen-Huang TWC 2011; He et al. (HKU) EM-OFDM-BEM | AFDM SP with iterative MP; EM with BEM marginalised | no full text found |

## 2. Verdict

1. **No paper found uses D-coord (`u I`, `u||h||^2`) with soft variances in a fractional-Doppler support search or SBL.** In that regime data-aided estimators are N (A1 Y. Luo, A2 Wei, A3 Mehrotra, A4 Halder-Murthy) or use exact second-moment weights (A6 Wan, B1 Huang-Guo; F-type).
2. **Closest to our setting: A1** (same waveform, SP, off-grid SBL, but hard decisions and an estimated isotropic noise `beta^-1 I_N` that is not derived from `v` and does not scale with `||h||^2`; cf. our L-hard 5.70 vs L-diag 23.71 same-delay pairs, res-20261017-03).
3. **D is the textbook form wherever atoms are orthogonal** (D1-D4; C1/C2 via prior power; C4 as F reducing to diagonal), and there it is exact: the same fact as our D1 boundary. In frequency-domain elementwise models the usual `diag(|mu|^2+v)` is F in atom coordinates, not D.
4. **F is not new in principle** (A6 gridless delay, B1 BEM). Frame the contribution as the AFDM co-delay closed form plus the support-exchange failure of D-coord, not "first to keep the second moment".
5. **Strongest honest answer:** "No published fractional-Doppler estimator we know of does D; they use hard decisions or exact weights. D-coord is what one gets by lifting the textbook orthogonal-grid recipe (D1-D4, C1/C2) onto a hard-decision receiver (A1-A4) to use soft information. We show that natural upgrade fails in support exchange and give the minimal exact fix."

## 3. Correction to an existing note, and open uncertainties

- **Correction (`novelty-positioning-20261118.md`, "known" table):** Prasad-Murthy-Rao TSP'14 is listed as a source of `E[X^H X] = X_bar^H X_bar + Sigma_x`. In the J-SBL paper I read, data is a hard-decision EM parameter and `Sigma` (Eq. 38) has no `Sigma_x`. Cite D2 (Eqs. 2-3), A6 (Eq. 33), B1 (Eqs. 73-74) or Wang'22 for that claim instead. Kocian-Fleury and Cozzo-Hughes remain unaudited.
- Fang-Rugini-Leus (OFDM + Doppler BEM + soft turbo CE) is the most likely classical precedent for F/D on Doppler atoms and I could not read it. Read it before submission (IEEE Xplore / TU Delft host).
- Zheng TVT'25 journal version (fractional Doppler?) and the Zheng GLOBECOM'25 message-passing AFDM paper are unread; C2 rests on arXiv v1.
- Wang TCOM'22 Eqs. (59)-(60) and Ouchikh ICASSP'22 were not re-read today; both classifications come from the 11-18 notes.
- A6/B1 are message-passing/EP: exact second-moment weights, but posterior correlation among atoms is dropped by the diagonal-message approximation. I label them F-weights, not full F; the cross-atom bookkeeping per module is not verified.
- B3 (Eurecom, EP with Dirac-mixture) and several arXiv-only items have no journal version checked; venues for A3, A6, B1, B2, C6, D2-D5 are as stated on arXiv.
- Search was not exhaustive (IEEE Xplore paywalled, Google Scholar not queried directly); a data-aided fractional-Doppler SBL paper that carries `v` in a coordinate-space ridge could still exist outside the 25 papers above.
