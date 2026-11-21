# AFDM Transceiver Design for Underwater Acoustic Communication Systems

**Student:** Yikun Guo　|　**GUID:** 2840210g　|　**School:** Glasgow College, UESTC　|　**Supervisor:** Assoc. Prof. Yusha Liu　|　**Course:** UESTC4006P Individual Project 4　|　**Academic Year:** 2025/2026

---

## 摘要

水声（UWA）信道兼具长时延扩展与分数阶多普勒，传统 OFDM 难以兼顾频谱效率与抗多普勒。仿射频分复用（AFDM）经离散仿射傅里叶变换将双弥散信道折叠为啁啾域稀疏等效信道。本文采用叠加导频（SP），但其有色数据干扰在中高信噪比不随噪声衰减，使一次性 OMP+MP 接收机出现误码平台。为此提出一种复杂度可控的联合接收机：OMP 仅运行一次锁定支撑，此后仅迭代数据辅助最小二乘（DA-LS）与稀疏 MP，并引入一个 1041 参数的学习型支撑精化头修复 OMP 漏掉的分数多普勒泄漏原子。仿真表明，其在 25 dB 将误码率较一次性基线降低两到三个数量级，学习头再带来约 2 dB 增益，复杂度保持 $\mathcal{O}(PN^2)$。

**关键词**　仿射频分复用；叠加导频；水声通信；深度展开

---

## Abstract

Underwater acoustic (UWA) channels exhibit long delay spreads and fractional Doppler shifts that conventional OFDM cannot handle without sacrificing spectral efficiency. Affine Frequency Division Multiplexing (AFDM) folds such doubly-dispersive channels, through the discrete affine Fourier transform, into a sparse chirp-domain effective channel. We adopt a superimposed-pilot (SP) frame, whose colored data interference does not decay with noise and leaves a one-shot OMP+MP receiver with a high-SNR error floor. We propose a complexity-preserving joint receiver that runs OMP once and iterates only a data-aided least-squares (DA-LS) refit and sparse MP, plus a 1,041-parameter learned support-refinement head that repairs the fractional-Doppler leakage atoms OMP misses. It improves BER by two-to-three orders of magnitude over the one-shot baseline at 25 dB, with a further ≈2 dB from the head, at $\mathcal{O}(PN^2)$ complexity.

**Keywords**　Affine frequency division multiplexing; superimposed pilots; underwater acoustic communications; deep unfolding.

---

## 1. Introduction

Underwater acoustic (UWA) communications operate over a doubly-dispersive channel with delay spreads of several to tens of milliseconds and a relative Doppler of order $v/c \sim 10^{-3}$, three to four orders larger than a typical RF link. Conventional OFDM handles neither cleanly: a cyclic prefix covering the full delay spread is prohibitively costly in spectral efficiency, while a residual fractional Doppler breaks sub-carrier orthogonality beyond a single-tap equaliser's reach. Affine Frequency Division Multiplexing (AFDM) [1] folds every physical delay–Doppler path, through the discrete affine Fourier transform (DAFT), into a single sparse, full-diversity chirp-domain effective channel, which makes greedy OMP channel estimation [2], [6] tractable.

To preserve spectral efficiency at few-kilohertz UWA bandwidths, this work adopts a superimposed-pilot (SP) frame [9] in which every sub-carrier carries both data and pilot. The resulting unknown-data interference does not decay with noise, leaving a one-shot OMP + message-passing (MP) receiver estimation-limited at mid-to-high SNR. Instead of re-running OMP or inverting a dense LMMSE estimator each iteration, we estimate the support once, lock it, and iterate only a damped DA-LS gain refit and sparse MP-BP, augmented by a small learned head that repairs the structural Dirichlet side-lobe residual that on-grid OMP misses. The end-to-end signal chain is summarised in Fig. 1-1.

> 〔**Figure 1-1** — 系统总览图，**待绘制**：TX（SP 帧，数据+导频叠加）→ UWA 信道 → RX：OMP-once →〔learned head〕→ iterative (DA-LS + MP-BP) → 检测。〕

**Figure 1-1.** Block overview of the proposed SP-AFDM transceiver.

---

## 2. Literature Review

**AFDM and its channel-estimation primitives.** AFDM [1] is a chirp-based waveform whose two DAFT parameters $(c_1, c_2)$ align with the channel's delay–Doppler geometry, recovering the diversity of two-dimensional OTFS on a one-dimensional transform. Benzine *et al.* [2] recast AFDM channel estimation as sparse recovery under embedded-pilot (EP) guard intervals, importing OMP [6]. The EP frame keeps the pilot observation clean but at a spectral-efficiency cost that is hard to absorb at few-kilohertz UWA bandwidths.

**Superimposed pilots and joint estimation–detection.** The SP principle was developed for OFDM, where an equipowered training pattern is optimal under a spectral-efficiency constraint [9]; the lesson that survives the transfer to delay–Doppler waveforms is that pilot–data interference does not decay with noise and produces a high-SNR floor. The SP-AFDM line — Zheng *et al.* [3] and Cao *et al.* [4] (the latter adding an OMP front-end) — shows that an iterative loop is required, but both re-run the sparse step every iteration and contain no learning component, while a DNN-aided AFDM receiver [5] places the learned element at the detector rather than at support selection.

**Sparse UWA estimation, MP detection, and deep unfolding.** Compressive sensing is the natural channel-estimation primitive for sparse UWA channels [7]. The inner detector inherits the sparse delay–Doppler message-passing of Raviteja *et al.* [8], and the learned head sits in the deep-unfolding tradition [10].

**Identified gap.** No published AFDM receiver simultaneously (a) preserves the SP frame, (b) runs OMP only once and iterates only DA-LS + MP-BP, and (c) places a small learned module at the OMP support-refinement step under a UWA-style fractional-Doppler regime. This work occupies that intersection.

---

## 3. Methodology

### 3.1 AFDM signal model and the DAFT

AFDM transmits $N$ symbols along discrete chirp basis functions parameterised by $(c_1, c_2)$. The time-domain transmit waveform is the inverse DAFT,

$$
s[n] = \frac{1}{\sqrt{N}} \sum_{m=0}^{N-1} x[m]\, e^{\,j 2\pi\left(c_1 n^2 + \frac{mn}{N} + c_2 m^2\right)}, \qquad n = 0, \dots, N-1, \tag{3-1}
$$

which reduces to the inverse DFT (and AFDM to OFDM) when $c_1 = c_2 = 0$. The forward DAFT at the receiver yields the chirp-domain model

$$
\mathbf{y} = \mathbf{H}_{\mathrm{eff}}\, \mathbf{x} + \mathbf{n}, \qquad \mathbf{n} \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{N}), \tag{3-2}
$$

where $\mathbf{H}_{\mathrm{eff}} \in \mathbb{C}^{N \times N}$ is the effective channel. The coefficients $(c_1, c_2)$ are chosen so that each physical path produces a single compact pattern in $\mathbf{H}_{\mathrm{eff}}$, which makes OMP-type sparse recovery effective.

### 3.2 Doubly-dispersive channel and effective-channel sparsity

Each physical path $(\tau_p, v_p)$ maps onto the integer lattice through $l_p = \mathrm{round}(\tau_p f_s)$ and $k_p^{\mathrm{real}} = v_p f_c N / (c f_s)$, where $l_p$ is integer but $k_p^{\mathrm{real}}$ is generally fractional. The residual fractional Doppler is absorbed by a discrete-Dirichlet-kernel expansion of half-width $\kappa_{\mathrm{leak}}$, so path $p$ becomes $2\kappa_{\mathrm{leak}}+1$ virtual integer-bin taps with magnitude

$$
|\tilde h_{p,j}| = |h_p| \cdot \left| \frac{\sin\!\big(\pi (k_p^{\mathrm{real}} - k_p - j)\big)}{N\, \sin\!\big(\pi (k_p^{\mathrm{real}} - k_p - j)/N\big)} \right|, \qquad j \in \{-\kappa_{\mathrm{leak}}, \dots, \kappa_{\mathrm{leak}}\}. \tag{3-3}
$$

The side-lobes flanking each kernel peak are structurally predictable energy at deterministic integer offsets, which a single on-grid OMP pass cannot fully resolve — the residual that the learned head of Section 3.6 repairs. With only a few tens of non-negligible virtual taps, a sparse-recovery approach is justified.

### 3.3 Superimposed-pilot signal model

Every sub-carrier carries data and pilot under the SP frame

$$
\mathbf{x} = \sqrt{\rho_p}\, \mathbf{x}_p + \sqrt{1 - \rho_p}\, \mathbf{x}_d, \qquad \rho_p \in (0, 1), \tag{3-4}
$$

where $\mathbf{x}_p$ is a unit-energy Zadoff–Chu sequence ($r = 7$), $\mathbf{x}_d$ is QPSK, and $\rho_p = 0.5$. The pilot projection $\mathbf{x}_p^H \mathbf{y}$ separates into a pilot term, a structured data-interference term $\sqrt{1-\rho_p}\,\mathbf{x}_p^H \mathbf{H}_{\mathrm{eff}}\mathbf{x}_d$, and noise; the interference term's conditional second moment given the channel is

$$
\mathbb{E}\big[\,|\sqrt{1 - \rho_p}\, \mathbf{x}_p^H \mathbf{H}_{\mathrm{eff}} \mathbf{x}_d|^2 \,\big|\, \mathbf{H}_{\mathrm{eff}}\big] = (1 - \rho_p) \cdot \|\mathbf{H}_{\mathrm{eff}}^H \mathbf{x}_p\|^2 / N. \tag{3-5}
$$

It scales with the channel norm and does not shrink with SNR — the origin of the estimation-limited floor that the iterative receiver removes.

### 3.4 Sparse-baseline OMP dictionary

The dictionary $\mathbf{\Phi} \in \mathbb{C}^{N \times Q}$ spans the integer region $l \in \{0, \dots, l_{\max}-1\}$, $k \in \{-k_{\max}, \dots, k_{\max}\}$, so $Q = (2k_{\max}+1)\, l_{\max}$ with $l_{\max} = \lceil \tau_{\mathrm{spread}} f_s \rceil$ and $k_{\max} = \lceil v_{\max} f_c N / (c f_s) \rceil$. The Dirichlet expansion of Eq. (3-3) is applied post-OMP and does not enlarge it. At fixed $f_s$, $l_{\max}$ is constant in $N$ while $k_{\max} \propto N$, so $Q = \mathcal{O}(N)$ and one OMP pass to sparsity $P$ costs $\mathcal{O}(P N Q + P^4) = \mathcal{O}(P N^2)$. Because the dictionary is on-grid, the fractional-Doppler leakage is precisely what a single OMP pass misses.

### 3.5 Proposed OMP-once + iterative LS/MP-BP receiver

The receiver runs one OMP pass and then iterates only a data-aided least-squares (DA-LS) gain refit and sparse MP-BP detection on the chirp-domain factor graph. Algorithm 1 gives the full recipe, including the data-cancellation residual, the damped DA-LS update on the locked support, and the pilot-subtracted MP-BP observation; the per-message MP-BP updates are standard damped Gaussian belief propagation. OMP is run only once because the recovered support is already stable: the inter-pass support Jaccard exceeds 0.94 and recall against the Dirichlet oracle is $\approx 95\%$ (Section 4.3), so re-running OMP each iteration is a $\approx 5\times$ constant-factor overhead with no new information.

![](assets/fig_algorithm1.png)

### 3.6 Learned support-refinement head

OMP occasionally misses weak Dirichlet-leakage atoms (typically $\pm 1$-bin Doppler offsets) whose gains fall below the prune threshold. A 1,041-parameter deep-unfolding head, inserted between the single OMP pass and the iterative loop, scores the top off-support candidates and appends the highest-ranked $K_{\mathrm{add}}$ atoms (Fig. 3-1). Each candidate is described by a self-feature vector and per-active-atom pair features; a shared pair encoder (order-invariantly pooled) and a shared scorer produce a logit used as a deterministic top-$K_{\mathrm{add}}$ ranker, trained with a weighted BCE plus pairwise ranking-hinge loss ($\lambda_{\mathrm{rank}} = 0.5$). The head operates on OMP's own dictionary and stays within the same arithmetic class.

![](assets/fig_head_integration.png)

**Figure 3-1.** Integration of the learned support-refinement head: it is invoked after OMP-once and before the iterative LS/MP-BP loop, ranking off-support candidates and appending the top-$K_{\mathrm{add}}$ atoms to the support, replacing neither OMP-once nor the iterative loop.

---

## 4. Results

### 4.1 Simulation setup

The configuration is fixed for every experiment, at the oversampled rate $f_s = 4B$: $N = 1024$ sub-carriers, spacing $\Delta f = 15$ Hz, carrier $f_c = 12$ kHz, bandwidth $B = 4$ kHz, $f_s = 16$ kHz; $P = 8$ paths, delay spread $\tau_{\mathrm{spread}} = 10$ ms (exponential PDP, $\tau_{\mathrm{mean}} = 0.8$ ms), per-path velocity $v \sim \mathcal{N}(2, 0.5^2)$ m/s, Dirichlet half-width $\kappa_{\mathrm{leak}} = 2$ (5 virtual taps/path); QPSK with Gray demapping, pilot fraction $\rho_p = 0.5$, Zadoff–Chu pilot of root $r = 7$; $T_{\mathrm{out}} = 5$ outer and $T_{\mathrm{mp}} = 20$ inner iterations, OMP dictionary $(l_{\max}, k_{\max}, Q) = (160, 2, 800)$. All four receivers (Serial, ClassicalJoint, Learned, Oracle) consume identical $(\text{channel}, \text{data}, \text{noise})$ realisations per SNR under a paired-frame protocol; BERs are observed frequencies with Clopper–Pearson 95% confidence intervals, and learned-versus-classical significance uses a continuity-corrected paired McNemar test. The Oracle arm (PCSI + dense MMSE) is a reference, not an information-theoretic bound.

### 4.2 BER waterfall

Fig. 4-1 plots the paired-frame BER and channel-estimation NMSE. The Serial arm is estimation-limited from 15 dB (NMSE frozen at $\approx -11.3$ dB, BER $\approx 5 \times 10^{-2}$), confirming a support-recovery floor rather than a noise-limited regime. The ClassicalJoint arm descends monotonically and, by 25 dB, recovers two-to-three orders of magnitude of BER over Serial. The Learned head sits strictly below ClassicalJoint at every SNR, with pooled relative BER reductions of $-37.7\%$, $-40.2\%$, and $-37.6\%$ at 20/25/30 dB (paired McNemar $p < 10^{-6}$); at SNR $\leq 10$ dB the gain is within $\approx 3\%$. The iterative recipe converges by the fourth outer iteration, justifying $T_{\mathrm{out}} = 5$.

![](assets/fig_ber_waterfall.png)

**Figure 4-1.** Main BER waterfall (left) and channel-estimation NMSE (right) at $f_s = 4B$. The Serial arm saturates from 15 dB; the ClassicalJoint and Learned arms continue to descend, with Learned consistently below ClassicalJoint at high SNR.

### 4.3 Support recall and oracle headroom

Two analyses ground the learned gain. First, OMP-once recall against the Dirichlet-expanded oracle support is stable at $\approx 95\%$ across SNR, with $\approx 67$–$71\%$ of frames carrying $\geq 1$ missed atom — so the residual is structural, not noise-driven. Second, a top-$P$ physical-support oracle (OMP replaced by the true main-lobe atoms) is a valid ceiling, reaching censored-zero at 20/25 dB and sitting $8\sigma$ below the baseline at 15 dB; against it the learned head closes $61/81/98\%$ of the gap at 15/20/25 dB (Fig. 4-2), attributing its gain to Dirichlet side-lobe recovery rather than noise averaging.

![](assets/fig_oracle_headroom.png)

**Figure 4-2.** Top-$P$ physical-support-oracle headroom at 15/20/25 dB. The oracle bounds the achievable support-refinement gain; the learned head closes $61\%/81\%/98\%$ of the baseline-to-oracle gap.

### 4.4 Complexity

The receiver stays in the sparse $\mathcal{O}(P N^2)$ arithmetic class — the head adds only $\mathcal{O}(N^2)$, the same class as one OMP sweep. Table 4-1 reports per-frame complex-MAC counts at $N = 1024$: the learned receiver adds $\approx 1.5$ M MAC on the 18.6 M-MAC classical core ($\approx 8\%$), OMP remaining the dominant cost; both dense $\mathcal{O}(N^3)$ alternatives cost $\approx 145\times$ more, and re-OMP-per-iteration is $2.61\times$ ($\approx 5\times$ constant) more expensive without changing the class.

**Table 4-1.** Per-frame complexity at $N = 1024$.

| Recipe | Asymptotic | MAC/frame | Relative |
|---|---|---:|---:|
| Serial (OMP + 1 MP-BP) | $\mathcal{O}(P N^2)$ | $\approx 14.0$ M | $0.75\times$ |
| ClassicalJoint (OMP-once + $5\times$ LS/MP-BP) | $\mathcal{O}(P N^2)$ | $\approx 18.6$ M | $1.00\times$ |
| **Learned (proposed)** | $\mathcal{O}(P N^2)$ | $\approx 20.1$ M | $\approx 1.08\times$ |
| Re-OMP-per-iter | $\mathcal{O}(P N^2)$, $5\times$ const | $\approx 48.6$ M | $2.61\times$ |
| Dense LMMSE CE | $\mathcal{O}(N^3)$ | $\approx 2.7$ G | $\approx 145\times$ |

---

## 5. Conclusion and Future Work

This report presented a complexity-preserving joint OMP–MP receiver for AFDM under superimposed pilots, augmented by a 1,041-parameter learned support-refinement head. (i) Running OMP once and iterating only DA-LS + MP-BP recovers two-to-three orders of magnitude of BER over the one-shot baseline at 25 dB within the $\mathcal{O}(P N^2)$ class, justified by the $\approx 95\%$ support recall that makes re-running OMP redundant. (ii) The learned head adds a consistent $\approx 2$ dB paired separation at 20/25/30 dB ($-37.7/-40.2/-37.6\%$, $p < 10^{-6}$) at $\approx 8\%$ MAC overhead, and is silent at low SNR. (iii) Against a top-$P$ physical-support oracle it closes $61/81/98\%$ of the achievable gap at 15/20/25 dB, attributing the gain to Dirichlet side-lobe recovery rather than noise averaging.

**Future work.** Natural extensions are a multi-seed retraining variance study, a quantitative re-implementation of a published SP-AFDM estimator, a full broadband per-path MSML simulator, and an embedded-deployment cost study.

---

## References

[1] A. Bemani, N. Ksairi, and M. Kountouris, "Affine frequency division multiplexing for next generation wireless communications," *IEEE Trans. Wireless Commun.*, vol. 22, no. 11, pp. 8214–8229, 2023.
[2] W. Benzine, A. Bemani, N. Ksairi, and D. Slock, "Affine frequency division multiplexing for communications on sparse time-varying channels," in *Proc. IEEE Global Commun. Conf. (GLOBECOM)*, 2023, pp. 4921–4926.
[3] K. Zheng, M. Wen, T. Mao, L. Xiao, and Z. Wang, "Channel estimation for AFDM with superimposed pilots," *IEEE Trans. Veh. Technol.*, vol. 74, no. 2, pp. 3389–3394, 2025.
[4] Z. Cao, M. Wen, and Y. Huang, "Sparse channel estimation and data detection for AFDM with superimposed pilot scheme," in *Proc. IEEE Int. Conf. Commun. Technol. (ICCT)*, 2024, pp. 1540–1544.
[5] P. Huang, Q. Li, D. Huang, and J. Wang, "Channel estimation and symbol detection for AFDM over doubly selective fading channels," *Phys. Commun.*, vol. 69, p. 102597, 2025.
[6] J. A. Tropp and A. C. Gilbert, "Signal recovery from random measurements via orthogonal matching pursuit," *IEEE Trans. Inf. Theory*, vol. 53, no. 12, pp. 4655–4666, 2007.
[7] C. R. Berger, S. Zhou, J. C. Preisig, and P. Willett, "Sparse channel estimation for multicarrier underwater acoustic communication: From subspace methods to compressed sensing," *IEEE Trans. Signal Process.*, vol. 58, no. 3, pp. 1708–1721, 2010.
[8] P. Raviteja, K. T. Phan, Y. Hong, and E. Viterbo, "Interference cancellation and iterative detection for orthogonal time frequency space modulation," *IEEE Trans. Wireless Commun.*, vol. 17, no. 10, pp. 6501–6515, 2018.
[9] A. G. Orozco-Lugo, M. M. Lara, and D. C. McLernon, "Channel estimation using implicit training," *IEEE Trans. Signal Process.*, vol. 52, no. 1, pp. 240–254, 2004.
[10] V. Monga, Y. Li, and Y. C. Eldar, "Algorithm unrolling: Interpretable, efficient deep learning for signal and image processing," *IEEE Signal Process. Mag.*, vol. 38, no. 2, pp. 18–44, 2021.
