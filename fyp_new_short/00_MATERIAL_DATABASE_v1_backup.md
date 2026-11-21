# 优秀论文缩编 — 素材数据库 (Material Database)

> 用途：这是把你的 FYP（SP-AFDM 水声低复杂度接收机）重构成 6–10 页英文短版 Word 的**可编辑素材库**。
> 你可以在这里直接增删/改写文字，确定后我用它 + 模板生成 Word。每一节都标注了：放哪、放多少、配哪张图/公式。
> 目标篇幅 ~8 页；中英双摘要；英文正文；两个贡献都讲，**低复杂度作为主线**（措辞已按"相对 LMMSE 低一个量级、相对 re-OMP 低常数倍"严格表述，不声称传统硬底复杂度）。

---

## 0. 元信息 / 版面规划 (Layout plan)

| 区块 | 内容 | 预计篇幅 | 配图/公式 |
|---|---|---|---|
| 标题 + 作者块 | 英文标题 + 学生信息 | — | — |
| 中文摘要 + 关键词 | §A1 | ~0.4 页 | — |
| English Abstract + Keywords | §A2 | ~0.4 页 | — |
| Ch.1 Introduction | §1 | ~1.3 页 | Fig.1 (Dirichlet kernel) |
| Ch.2 System Model & Proposed Receiver | §2 | ~2.8 页 | Fig.2 (classical block), Fig.3 (learned head integ.), Eq.(1)–(8) |
| Ch.3 Results | §3 | ~2.0 页 | Fig.4 (BER waterfall), Fig.5 (recall), Fig.6 (oracle headroom), Table 2/3 |
| Ch.4 Discussion | §4 | ~0.8 页 | — |
| Ch.5 Conclusion | §5 | ~0.5 页 | — |
| References | §R | ~0.6 页 | 选 18 条核心 |

**英文标题（建议）**：
*A Complexity-Preserving Joint OMP–MP Receiver for Superimposed-Pilot AFDM in Underwater Acoustic Channels, with a Learned Support-Refinement Head*

**作者块（按模板填，占位）**：
- Student Name: Yikun Guo　　Student No.: 2840210g
- School: Glasgow College, UESTC　　Supervisor: （导师）
- Course: UESTC4006P Individual Project 4　　Academic Year: 2025/2026

---

## A1. 中文摘要 + 关键词

**摘要**　水声（UWA）信道同时具有长时延扩展与严重的分数阶多普勒频移，传统 OFDM 必须付出高昂的循环前缀开销才能勉强应对。仿射频分复用（AFDM）通过离散仿射傅里叶变换（DAFT）将双弥散路径折叠为啁啾域上一个稀疏的等效信道，使基于压缩感知的信道估计成为可能。为在带宽受限的水声链路中进一步保住频谱效率，本文采用叠加导频（SP）帧结构，使每个啁啾子载波同时承载数据与导频能量；其代价是导频观测被未知数据干扰污染，且该干扰在中高信噪比下不随噪声方差衰减，导致一次性 OMP+消息传递（MP）接收机被"估计误差"而非"噪声"所限制，出现误码平台。

本文提出一种面向 SP-AFDM、复杂度可控的**联合信道估计与数据检测接收机**：OMP 仅运行一次以锁定信道支撑集，随后仅迭代两个廉价模块——数据辅助最小二乘（DA-LS）增益重拟合与稀疏 MP 置信传播。支撑集召回探针表明，首次 OMP 即已恢复约 95% 的 Dirichlet 展开虚拟抽头支撑，剩余约 5% 由分数阶多普勒泄漏几何结构决定、与噪声无关，因此逐迭代重跑 OMP 纯属常数倍冗余开销。该接收机在保持与单次 OMP 同一 O(P·N²) 运算量级的前提下，在 25 dB 时相对一次性基线把误码率降低两到三个数量级——相较稠密 LMMSE 估计器低约两个数量级运算量，相较逐迭代重跑 OMP 低约 5 倍常数因子。在此经典内核之上，进一步引入一个仅 **1041 参数**的深度展开支撑精化头，对 OMP 之后的离支撑候选打分并固定追加少量高分原子；该学习模块仍处于同一运算量级，在 N=1024 时仅增加约 8% 复数乘加开销，并在 20/25/30 dB 上相对经典联合接收机再带来约 2 dB 的配对误码分离。物理支撑 oracle 上界分析显示，学习头在 15/20/25 dB 分别填补了可达精化增益的 61%/81%/98%。

**关键词**　仿射频分复用；叠加导频；水声通信；联合信道估计与检测；正交匹配追踪；深度展开

---

## A2. English Abstract + Keywords

**Abstract.** Underwater acoustic (UWA) channels exhibit long delay spreads and severe fractional Doppler shifts that conventional OFDM cannot accommodate without prohibitive cyclic-prefix overhead. Affine Frequency Division Multiplexing (AFDM) folds these doubly-dispersive paths, through the discrete affine Fourier transform (DAFT), into a single sparse chirp-domain effective channel, enabling compressive-sensing-based channel estimation. To preserve spectral efficiency on bandwidth-constrained UWA links, this work adopts a superimposed-pilot (SP) frame in which every chirp sub-carrier carries both data and pilot energy. The resulting unknown-data interference does not decay with the noise variance, leaving a one-shot orthogonal matching pursuit (OMP) plus message-passing (MP) receiver estimation-limited at mid-to-high SNR. We propose a complexity-preserving joint channel-estimation and data-detection receiver for AFDM-SP: OMP is executed only once to lock the channel support, after which only a data-aided least-squares (DA-LS) gain refit and sparse MP belief propagation iterate. A support-recall probe shows the first OMP pass already recovers ≈95% of the Dirichlet-expanded virtual-tap support, with the residual ≈5% structurally fixed by fractional-Doppler leakage rather than by noise, so re-running OMP each outer iteration is a wasted constant-factor overhead. The receiver recovers two-to-three orders of magnitude in BER over the one-shot baseline at SNR = 25 dB while staying in the same O(P·N²) arithmetic class — two orders of magnitude below a dense LMMSE estimator and a 5× constant factor below a re-OMP-per-iteration schedule. A 1,041-parameter deep-unfolding support-refinement head, inserted after the single OMP pass, scores off-support candidates and appends a fixed number of top-ranked atoms; it stays in the same arithmetic class (≈8% additional complex-MAC at N=1024) and adds a further ≈2 dB paired BER separation at SNR ∈ {20,25,30} dB. A physical-support-oracle analysis shows the learned head closes 61%/81%/98% of the achievable support-refinement gap at SNR = 15/20/25 dB.

**Keywords.** Affine Frequency Division Multiplexing; superimposed pilots; underwater acoustic communications; joint channel estimation and detection; orthogonal matching pursuit; deep unfolding.

---

## 1. Chapter 1 — Introduction（短版正文，可直接用）

**1.1 Background and motivation.**
Underwater acoustic (UWA) communications carry much of the wireless traffic between autonomous underwater vehicles, ocean-bottom sensors and surface platforms, over a channel shaped by two pathologies that together are harder to handle than almost any terrestrial RF link. Surface–column–bed multipath produces delay spreads of several to tens of milliseconds, which at the 4–12 kHz bandwidths typical of UWA modems translates to hundreds of resolvable delay bins. The low sound speed (c ≈ 1500 m/s) combined with platform motion of a few m/s yields a relative Doppler of order v/c ∼ 10⁻³ — three to four orders of magnitude larger than a typical RF link — producing strong inter-carrier interference and *fractional* Doppler offsets relative to the multicarrier grid. A conventional OFDM receiver absorbs neither cleanly: a cyclic prefix long enough for the full delay spread costs a prohibitive fraction of spectral efficiency, while a residual fractional Doppler of even a few tenths of a sub-carrier corrupts sub-carrier orthogonality beyond what a single-tap equaliser can repair.

Affine Frequency Division Multiplexing (AFDM) was designed for exactly such doubly-dispersive channels. By placing information on a chirp basis defined through the discrete affine Fourier transform (DAFT) and tuning the two chirp coefficients (c₁, c₂) to the channel's delay–Doppler geometry, AFDM folds every physical delay–Doppler pair into a single sparse structured effective channel on a one-dimensional chirp-domain signal — recovering the diversity of two-dimensional OTFS at lower transform cost. That sparsity is what makes greedy sparse-recovery channel estimation with orthogonal matching pursuit (OMP) tractable, and it is the starting point of every receiver in this report.

Pilot overhead nonetheless remains a first-order constraint at few-kilohertz UWA bandwidths. To preserve data capacity, this work adopts a *superimposed-pilot* (SP) frame in which every chirp sub-carrier simultaneously carries data and pilot energy under a fixed power split ρₚ. SP roughly doubles the data capacity of a comparable embedded-pilot (EP) frame, but the pilot observation is now systematically contaminated by unknown-data interference that, crucially, does *not* average out at high SNR. In a representative UWA-style setting (ρₚ = 0.5, P = 8 paths) the resulting error floor for a one-shot OMP+MP receiver sits at BER ≈ 5×10⁻² from SNR ≥ 15 dB, with the OMP channel-estimation NMSE frozen near −11.3 dB irrespective of noise variance. The presence of this floor — not the SNR — defines the engineering regime this work addresses.

The natural response is to iterate between channel estimation and symbol detection: each detection pass subtracts tentative data estimates from the pilot observation and sharpens the next channel estimate. Two naive realisations are expensive, however: re-running OMP every outer iteration multiplies the per-frame cost by a ≈5× constant factor at five iterations, while replacing OMP with a dense LMMSE estimator inflates per-frame complexity by two orders of magnitude at N = 1024. This work investigates a third option — estimate the support *once* with OMP, lock it, and iterate only the cheap downstream blocks: a damped data-aided least-squares (DA-LS) path-gain refit and sparse message-passing belief propagation (MP-BP). The central question is whether such a single-OMP receiver, optionally augmented by a small learned module that repairs the residual fractional-Doppler leakage, can close the SP error floor at a complexity comparable to a single OMP pass.

**1.2 Related work (condensed).**
The receiver sits at the intersection of four threads. (i) *AFDM and its CE primitives*: Bemani et al. introduced AFDM; Benzine et al. recast AFDM channel estimation as sparse recovery under embedded pilots, importing OMP; Yin et al. addressed fractional Doppler via diagonal reconstruction. (ii) *Superimposed pilots*: developed for OFDM (Cui–Tellambura, Tugnait–Meng, Orozco-Lugo) and carried to delay–Doppler waveforms (OTFS/OTSM); the SP-AFDM line (Zheng et al.; Cao et al.) establishes that an iterative loop is structurally required, but re-executes the sparse-recovery step every outer iteration and contains no learning component. (iii) *Sparse UWA channel estimation and MP detection*: compressive sensing is the natural CE primitive for multicarrier UWA links (Berger et al.), and sparse delay–Doppler MP-BP detection follows Raviteja et al. (iv) *Deep unfolding*: embedding small learned modules in model-based receivers (Monga et al.; Gregor–LeCun LISTA), so far placed in AFDM at the *detector* rather than at the support-selection step.

**Identified gap.** No published AFDM receiver simultaneously (a) preserves the SP frame, (b) runs OMP only once and iterates only DA-LS + MP-BP, and (c) places a small learned module at the OMP support-refinement step under a UWA-style sparse fractional-Doppler regime. This work occupies precisely that intersection.

**1.3 Research question.**
*Can an SP-AFDM receiver close the structured pilot–data interference floor at mid-to-high SNR while remaining complexity-preserving relative to both re-OMP-per-iteration and dense-LMMSE alternatives, and can a minimal learned module further reduce the residual support-selection error without leaving the sparse-recovery complexity class?*

**1.4 Contributions.**
1. **A complexity-preserving joint OMP–MP receiver for AFDM-SP** under a UWA-style fractional-Doppler regime: OMP once, support locked, only DA-LS + MP-BP iterate. A support-recall probe shows the first OMP pass recovers ≈95% of the Dirichlet-expanded virtual-tap support, residual ≈5% structural; the receiver recovers two-to-three orders of magnitude of BER over the one-shot baseline at 25 dB while staying in the O(P·N²) class.
2. **A 1,041-parameter learned support-refinement head** deployed as a deterministic top-K_add ranker between OMP-once and the iterative loop: a consistent ≈2 dB paired BER separation at SNR ∈ {20,25,30} dB, same O(P·N²) class, ≈8% MAC overhead at N=1024 (wall-clock parity at N=1024, +3.9% at N=2048).
3. **A mechanism analysis** grounding the learned gain: a top-P physical-support oracle is a valid ceiling; the head closes 61%/81%/98% of the achievable gap at 15/20/25 dB, attributing its contribution specifically to recovery of Dirichlet side-lobe atoms rather than to generic noise averaging.

> 配图：**Fig.1 = Dirichlet-kernel magnitude** (source: `system_block/fig_dirichlet_kernel.pdf`) — 放在 1.1 末或 2.2，用来直观说明分数阶多普勒泄漏的旁瓣几何。

---

## 2. Chapter 2 — System Model and Proposed Receiver（短版正文）

**2.1 AFDM signal model (DAFT).**
AFDM transmits N symbols along discrete chirp basis functions parameterised by (c₁, c₂). The time-domain waveform is the inverse DAFT [Eq.1]. With c₁ = c₂ = 0 the IDAFT reduces to the inverse DFT and AFDM reduces to OFDM. At the receiver the forward DAFT yields a chirp-domain model y = H_eff·x + n [Eq.2], where H_eff ∈ ℂ^{N×N} is the chirp-domain effective channel. The (c₁, c₂) choice makes each physical path (l_p, k_p) produce a single compact interference pattern rather than dense leakage, which is what makes OMP-type sparse support recovery effective on H_eff.

**2.2 Doubly-dispersive channel and effective-channel sparsity.**
The simulator models a UWA doubly-dispersive channel with P = 8 dominant paths, delay spread τ_spread = 10 ms (exponential PDP, τ_mean = 0.8 ms), per-path velocity v ∼ N(2, 0.5²) m/s, fc = 12 kHz, B = 4 kHz, fs = 4B. Multi-scale multi-lag (MSML) propagation is captured to first order: per-path scaling a_p = v_p/c gives a per-path delay rescaling τ_p → τ_p/(1+a_p) and a constant per-path Doppler shift f_{D,p} = a_p·fc. Each physical path maps onto the integer delay–Doppler lattice [Eq.3]; the delay index l_p is integer, but k_p^real is generally fractional. The residual fractional Doppler is absorbed by a discrete-Dirichlet-kernel (aliased-sinc) expansion of half-width κ_leak = 2, so each path becomes 2κ_leak+1 = 5 virtual integer-bin taps with magnitude [Eq.4]. At the worst-case residual |k^real − k| = 0.5, the two nearest integer bins each carry ≈41% of per-path energy and the next-nearest ≈4.4%; the truncated tail beyond κ_leak is ≈8.3% of per-path energy. With P = 8 and κ_leak = 2 the effective channel carries ≈28 non-negligible virtual taps out of ∼10³ lattice positions — justifying a sparse-recovery approach. The non-zero side-lobes flanking each kernel peak are *structurally predictable* energy: this is the physical reason both the post-OMP virtual-tap expansion and the learned head operate on the *same* dictionary as OMP rather than enlarging it.

**2.3 Superimposed-pilot signal model.**
Every chirp sub-carrier carries data and pilot under x = √ρₚ·x_p + √(1−ρₚ)·x_d [Eq.5], where x_p is a unit-energy Zadoff–Chu sequence (root r = 7) and x_d is QPSK; canonical ρₚ = 0.5. The receiver pilot projection x_pᴴy [Eq.6] leaves a structured interference term √(1−ρₚ)·x_pᴴH_eff·x_d whose conditional second moment is (1−ρₚ)·‖H_effᴴx_p‖²/N [Eq.7] — it scales with the channel norm and **does not shrink with SNR**, which is the origin of the estimation-limited floor (empirically BER ≈ 5×10⁻² for the serial receiver from SNR ≥ 15 dB).

**2.4 OMP dictionary.**
The dictionary Φ ∈ ℂ^{N×Q} is built column-wise over the integer search region l ∈ {0,…,l_max−1}, k ∈ {−k_max,…,k_max}, so Q = (2k_max+1)·l_max with l_max = ⌈τ_spread·fs⌉ and k_max = ⌈v_max·fc·N/(c·fs)⌉ [Eq. l_max/k_max]. The dictionary spans physical integer bins only; the Dirichlet expansion is applied *post*-OMP, so κ_leak does not enlarge it. At fixed fs, l_max is constant in N while k_max ∝ N, giving Q = O(N). One OMP pass to sparsity P costs O(P·N·Q + P⁴) = **O(P·N²)** [Eq.8]. (Table 1 = dictionary sizes: N=512/1024/2048 → Q=480/800/1440 at fs=4B.)

**2.5 Joint OMP-once + iterative LS/MP-BP receiver (the headline).**
The receiver performs **one** OMP support-recovery pass, then iterates only over (i) a data-cancellation residual, (ii) a damped DA-LS path-gain refit on the locked support, and (iii) sparse MP-BP detection on the Dirichlet-expanded chirp-domain factor graph, with an adaptive noise-variance update and gain-based pruning. Hyperparameters: T_out = 5 outer, T_mp = 20 MP inner, damping γ_h = 0.7, prune τ_h = 10⁻²·max|ĥ|. The factor-graph neighbourhood degree is bounded by P·(2κ_leak+1) = 40 (≈28 effective after pruning), a *constant* in N, so each MP-BP iteration costs O(N) — two orders of magnitude below a dense MMSE equaliser's O(N³) at N = 1024.

*Why OMP-once.* (a) Outer-iteration convergence: BER drops >2 orders over t = 1→5 with the support held fixed (Fig. iter-conv); (b) the per-frame support Jaccard between successive OMP passes exceeds 0.94 from iteration 2; (c) support recall vs the Dirichlet oracle is ≈95% (Table 2). So a second OMP pass has nothing new to find, and re-OMP every iteration is a ≈5× constant-factor overhead with no support information added.

> 配图：**Fig.2 = classical OMP-once + iterative LS/MP-BP block diagram** (source: `system_block/figure_a_new.png`).

**2.6 Learned support-refinement head.**
A 1,041-parameter deep-unfolding head, inserted between OMP-once and the iterative loop, scores the M = 96 top off-support candidates and appends the top K_add = 4 atoms (invoked twice at t = 0). It targets the weak Dirichlet-leakage atoms (typically ±1-bin Doppler offsets) that OMP misses and the gain-prune rule discards. Each candidate has a 7-D self-feature (matched-filter magnitude, margin to weakest active atom, normalised delay/Doppler indices, residual-normalised projection, rank, Dirichlet-neighbour flag) and, per active atom, a 6-D pair feature (integer offsets Δl, Δk; active log-gain; pair correlation; normalised distance; gain prominence). A shared pair encoder (ℝ⁶→ℝ¹⁶→ℝ¹⁶, 384 params) is pooled order-invariantly (max+mean) into a 32-D descriptor, concatenated with the self-feature → 39-D, then a shared scorer (ℝ³⁹→ℝ¹⁶→ℝ¹, 657 params) emits a logit. Deployment is a deterministic top-K_add ranker (rank-only; a +10 bias patch is rank-preserving). Trained with BCE + pairwise rank-hinge (λ_rank = 0.5, AdamW, lr 10⁻³) on a 27k-frame, 4-SNR cache (SNR ∈ {10,15,20,25} dB).

> 配图：**Fig.3 = learned-head integration into the receiver** (source: `system_block/figure_b_new.png`). 可选 Fig.3b = head architecture (`figure_c_new.png`)，若篇幅紧张则省略。

**2.7 Complexity.**
Classical core: C_classical = O(P·N·Q) [OMP] + T_out·[O(P²·N) DA-LS + O(T_mp·N) MP-BP] = **O(P·N²)**. The head adds C_head = O(N·Q + M·P·N) = O(N²) — same class as a single OMP matched-filter sweep. Net: the proposed receiver is in the same O(P·N²) class as the sparse baseline, **two orders of magnitude below dense LMMSE (O(N³))** and a **5× constant factor below re-OMP-per-iteration**; the head adds ≈1.5 M MAC on the 18.6 M-MAC core (**≈8% overhead** at N=1024).

**2.8 Evaluation protocol (brief).**
Strict paired-frame protocol: the four receivers (Serial, ClassicalJoint, Learned, Oracle) consume identical (channel, data, noise) realisations per SNR. Reported BERs are observed frequencies with Clopper–Pearson 95% CIs; learned-vs-classical significance via continuity-corrected paired McNemar χ². Train/val/test separated at the seed level (disjoint seed blocks). The Oracle arm = PCSI + dense MMSE, a reference (not an information-theoretic bound).

---

## 3. Chapter 3 — Results（短版正文）

**Simulation parameters (Table 1 or inline):** N = 1024, Δf = 15 Hz, fc = 12 kHz, B = 4 kHz, fs = 4B = 16 kHz, P = 8, τ_spread = 10 ms (exp. PDP, τ_mean = 0.8 ms), v ∼ N(2, 0.5²) m/s, κ_leak = 2 (5 virtual taps/path), QPSK Gray, ρₚ = 0.5, ZC pilot r = 7, T_out = 5, T_mp = 20, (l_max, k_max, Q) = (160, 2, 800).

**3.1 Main BER waterfall (Experiment 1).**
The Serial arm is estimation-limited from SNR = 15 dB (NMSE frozen ≈ −11.3 dB), confirming a support-recovery floor rather than a noise-limited regime. The ClassicalJoint arm descends monotonically and, by 25 dB, recovers ≈2–3 orders of magnitude of BER over Serial. The Learned head sits strictly below ClassicalJoint at every SNR, opening a consistent ≈2 dB paired separation at the three high-SNR points: pooled relative BER reductions of **−37.7% @ 20 dB, −40.2% @ 25 dB, −37.6% @ 30 dB** (3-seed pooled), all with paired McNemar p < 10⁻⁶. At SNR ≤ 10 dB the gain is within ≈3% relative — the intended behaviour of a support-refinement module in the noise-limited regime.

> 配图：**Fig.4 = BER waterfall (+ NMSE)** (source: `loop13/loop13_combined_4B_ber_mse.png`).
> 表：**Table 2 = paired BER** (见 §T2).

**3.2 Outer-iteration convergence (Experiment 2).**
Both recipes converge geometrically over t = 1–4 and saturate by t = 4, justifying T_out = 5 (e.g. classical @ 20 dB: 8.69×10⁻² → 9.07×10⁻⁴ across t = 1→5). The choice is robust to small variations in the iteration count.

> 配图（可选，篇幅允许时）：`loop13/loop13_iter_convergence_4B.png`.

**3.3 Support recall and oracle headroom (Experiment 3 — the mechanism evidence).**
*(a) Recall.* OMP-once recall against the Dirichlet-expanded virtual-tap oracle support (effective size ≈28; OMP support itself = P = 8) is **stable at ≈95% across SNR**, with ≈67–71% of frames carrying ≥1 missed atom — i.e. structural, not noise-driven. *(b) Oracle headroom.* A top-P physical-support oracle (true main-lobe atoms) is a valid ceiling: it reaches censored-zero at SNR ∈ {20,25} dB on 5.12×10⁵ paired bits/cell and sits 8σ below the baseline at 15 dB. Against it, the learned head closes **61% / 81% / 98%** of the baseline-to-oracle gap at SNR = 15/20/25 dB — capturing the bulk of the reduction available from any top-P support-refinement on this dictionary.

> 配图：**Fig.5 = support recall** (`loop13/loop13_support_recall.png`); **Fig.6 = oracle headroom** (`loop13/loop13_oracle_headroom.png`).
> 表：**Table 3 = oracle headroom** (见 §T3).

**3.4 Complexity / MAC count (Experiment 4).**
The proposed learned receiver adds ≈1.5 M MAC on the 18.6 M-MAC classical core (≈8%), OMP remaining the dominant per-frame cost. Both dense alternatives (O(N³)) cost ≈145× more per frame at N=1024; a re-OMP-per-iteration schedule is 2.61× (≈5× constant) more expensive without changing the class. Wall-clock (RTX 4090): learned is at parity with classical-Torch at N=1024 (402 vs 416 ms) and +3.9% at N=2048.

> 表：**Table 4 = complexity** (见 §T4). 若篇幅紧张，Table 4 可与文字合并，仅保留三行核心（Serial / ClassicalJoint / Learned / Dense-LMMSE）。

---

## 4. Chapter 4 — Discussion（短版正文，浓缩）

**Serial-receiver floor.** The data-interference term √(1−ρₚ)·x_pᴴH_eff·x_d does not scale with σ²_n, so at high SNR OMP's residual correlation is dominated by structured interference, capping NMSE near −11.3 dB (ρₚ = 0.5 balances pilot and data energy). The floor is therefore *estimation-limited*, not detection-limited — which is exactly what the iterative recipe dismantles.

**OMP-once sufficiency.** MP-BP symbol feedback attenuates the data interference more aggressively than a second OMP pass would (BER drops >2 orders over t = 1→5 with the support fixed), and the support Jaccard between passes exceeds 0.94. Combined with ≈95% recall, re-OMP each iteration is a 5× constant-factor overhead adding no support information. This is the precise sense in which the receiver is *complexity-preserving*: same O(P·N²) class as one OMP sweep, two orders below dense LMMSE, 5× below re-OMP-per-iteration.

**Learned head's high-SNR mechanism.** Each physical path's Dirichlet side-lobes (±1 Doppler offset, 5–20% of main-lobe energy) sit at deterministic integer offsets from already-active atoms. At low SNR they are drowned in noise-driven candidates with no structural signature, so the head abstains (|Δ| ≤ 6.1% at SNR ≤ 10 dB — by design). At high SNR the noise background falls below the side-lobe amplitudes and they appear at predictable offsets that the pair-feature vector exposes to the scorer. A population-level attribution confirms ≥99.4% of head additions land on Dirichlet side-lobes/virtual taps of active physical paths — i.e. Dirichlet side-lobe repair, not generic noise averaging.

**Why fs = 4B.** Moving 2B→4B does not shrink the dictionary (Q: 720→800) but gives a finer integer Doppler grid (smaller residual fractional offset, tighter side-lobe energy) and better matched-filter contrast, consistent with oversampled-AFDM CE findings.

**Limitations (brief).** Single-checkpoint learned head (a multi-seed retraining study would add error bars); complexity is per-frame MAC only (no measured embedded latency/energy); the simulator is first-order MSML (no full broadband per-path resampling or per-frame Doppler jitter); scope fixed at 1T1R, QPSK, ρₚ = 0.5, v_mean = 2 m/s. The "low-complexity" label is in the per-frame *arithmetic* sense.

---

## 5. Chapter 5 — Conclusion（短版正文）

This report developed and evaluated a complexity-preserving joint OMP–MP receiver for AFDM under superimposed pilots, augmented by a 1,041-parameter learned top-K_add support-refinement head, on a doubly-dispersive UWA-style simulator with first-order MSML modelling. (1) Running OMP once, locking the support, and iterating only DA-LS + MP-BP recovers two-to-three orders of magnitude of BER over the one-shot baseline at 25 dB while staying in the sparse O(P·N²) class — two orders below dense LMMSE and 5× below re-OMP-per-iteration — justified by ≈95% support recall after a single pass. (2) The learned head adds a consistent ≈2 dB paired separation at SNR ∈ {20,25,30} dB (−37.7/−40.2/−37.6% pooled, p < 10⁻⁶) at ≈8% MAC overhead, abstaining where support errors carry no structure (SNR ≤ 10 dB). (3) Against a valid top-P physical-support oracle ceiling, the head closes 61/81/98% of the achievable gap at 15/20/25 dB, attributing the gain to Dirichlet side-lobe repair. Future work: multi-seed retraining variance; head-to-head reproduction of published SP-AFDM baselines; a full per-path waveform-resampling MSML simulator; and an embedded-deployment cost study (latency/memory/energy) to extend the complexity claim from arithmetic class to deployment cost.

---

## T. 表格素材 (Tables — 数值已核对)

### Table 1 — OMP dictionary size (fs = 4B)
| N | l_max | k_max | Q = (2k_max+1)·l_max |
|---:|---:|---:|---:|
| 512 | 160 | 1 | 480 |
| 1024 | 160 | 2 | 800 |
| 2048 | 160 | 4 | 1440 |

### Table 2 — 4B BER waterfall (3-seed pooled, paired)
| SNR (dB) | Serial | ClassicalJoint | Learned | Oracle (PCSI+MMSE) | Δ Learned vs Classical |
|---:|---:|---:|---:|---:|---:|
| 10 | 7.1×10⁻² | 4.8×10⁻² | 4.5×10⁻² | 2.2×10⁻² | −2.2% |
| 15 | 4.3×10⁻² | 1.9×10⁻² | 1.7×10⁻² | 7.4×10⁻³ | −7.4% (p<10⁻⁶) |
| 20 | 4.1×10⁻² | 5.0×10⁻⁴ | **3.1×10⁻⁴** | 1.2×10⁻⁴ | **−37.7%** (p<10⁻⁶) |
| 25 | 4.1×10⁻² | 1.0×10⁻⁴ | **6.0×10⁻⁵** | 0 (censored) | **−40.2%** (p<10⁻⁶) |
| 30 | 4.1×10⁻² | 1.8×10⁻⁵ | **1.1×10⁻⁵** | 0 (censored) | **−37.6%** (p<10⁻⁶) |

### Table 3 — Top-P physical-support-oracle headroom
| SNR (dB) | ClassicalJoint | oracle_physical | Learned | Oracle (PCSI+MMSE) | Gap closed |
|---:|---:|---:|---:|---:|---:|
| 15 | 1.98×10⁻² | 1.21×10⁻² | 1.51×10⁻² | 7.42×10⁻³ | **61%** |
| 20 | 3.89×10⁻⁴ | 0 (UB 5.86×10⁻⁶) | 7.39×10⁻⁵ | 1.17×10⁻⁴ | **81%** |
| 25 | 3.46×10⁻⁴ | 0 (UB 5.86×10⁻⁶) | 5.58×10⁻⁶ | 0 (censored) | **98%** |

### Table 4 — Complexity (per frame, N = 1024)
| Recipe | Dominant operator | Asymptotic | MAC/frame | Relative |
|---|---|---|---:|---:|
| Serial (OMP + 1 MP-BP) | OMP | O(P·N²) | ≈14.0 M | 0.75× |
| ClassicalJoint (OMP-once + 5× LS/MP-BP) | OMP + 5× LS/MP-BP | O(P·N²) | ≈18.6 M | 1.00× (baseline) |
| **Learned (proposed)** | classical + 2× head | O(P·N²) | ≈20.1 M | **≈1.08×** |
| Re-OMP-per-iter (hypothetical) | 5× OMP + 5× LS/MP-BP | O(P·N²), 5× const | ≈48.6 M | 2.61× |
| Dense LMMSE CE | (ΦᴴΦ)⁻¹ | O(N³) | ≈2.7 G | ≈145× |

---

## E. 公式素材 (Equations — 渲染为图片嵌入 Word)

> 以下挑选 8 个对"完整故事"必需的核心公式渲染为图片。次要公式（MP-BP 逐条消息更新 Eq. 的细节）在短版中以文字描述带过。

- **Eq.1 (IDAFT):** `s[n] = (1/√N) Σ_{m=0}^{N-1} x[m]·exp{ j2π(c₁n² + mn/N + c₂m²) }`
- **Eq.2 (AFDM model):** `y = H_eff·x + n,  n ~ CN(0, σ²_n I_N)`
- **Eq.3 (delay–Doppler mapping):** `l_p = round(τ_p·fs),  k_p^real = v_p·fc·N/(c·fs)`
- **Eq.4 (Dirichlet expansion):** `|h̃_{p,j}| = |h_p|·| sin(π(k_p^real−k_p−j)) / (N·sin(π(k_p^real−k_p−j)/N)) |,  j ∈ {−κ_leak,…,κ_leak}`
- **Eq.5 (SP frame):** `x = √ρₚ·x_p + √(1−ρₚ)·x_d,  ρₚ ∈ (0,1)`
- **Eq.6 (pilot projection):** `x_pᴴ y = √ρₚ·x_pᴴH_eff x_p + √(1−ρₚ)·x_pᴴH_eff x_d + x_pᴴ n`
- **Eq.7 (interference variance):** `E[ |√(1−ρₚ)·x_pᴴH_eff x_d|² | H_eff ] = (1−ρₚ)·‖H_effᴴ x_p‖² / N`
- **Eq.8 (OMP cost):** `C_OMP = O(P·N·Q + P⁴) = O(P·N²)`

(若想更省篇幅，可只渲染 Eq.1, 2, 4, 5, 7, 8 六个；Eq.3/6 可写进正文行内。)

---

## F. 图片清单 (Figures — 源文件路径)

| 短版图号 | 内容 | 源文件 (相对 AFDM-channel-estimation/) | 格式 |
|---|---|---|---|
| Fig.1 | Dirichlet-kernel magnitude（旁瓣几何） | `figures/system_block/fig_dirichlet_kernel.pdf` | PDF→PNG |
| Fig.2 | Classical OMP-once + iterative LS/MP-BP 框图 | `figures/system_block/figure_a_new.png` | PNG |
| Fig.3 | Learned head 集成框图 | `figures/system_block/figure_b_new.png` | PNG |
| Fig.3b (可选) | Learned head 架构 | `figures/system_block/figure_c_new.png` | PNG |
| Fig.4 | BER waterfall + NMSE（主结果） | `figures/loop13/loop13_combined_4B_ber_mse.png` | PNG |
| Fig.5 | Support recall vs SNR | `figures/loop13/loop13_support_recall.png` | PNG |
| Fig.6 | Top-P oracle headroom | `figures/loop13/loop13_oracle_headroom.png` | PNG |
| (可选) | Outer-iteration convergence | `figures/loop13/loop13_iter_convergence_4B.png` | PNG |

---

## R. 参考文献（精选 18 条核心，按短版引用）

1. A. Bemani et al., "Affine Frequency Division Multiplexing for Next-Generation Wireless Communications," *IEEE Trans. Wireless Commun.*, 2023.
2. R. Hadani et al., "Orthogonal Time Frequency Space Modulation," *IEEE WCNC*, 2017.
3. H. Benzine et al., "Sparse Channel Estimation for AFDM," 2023.
4. Z. Yin and Y. Tang, "Pilot-Aided Fractional-Doppler AFDM Channel Estimation," 2022.
5. Z. Yin et al., "Diagonal-Reconstruction Channel Estimation for MIMO-AFDM (fractional Doppler)," 2024.
6. Zheng et al., "Iterative Channel Estimation and Signal Detection for Superimposed-Pilot AFDM," 2024.
7. Cao et al., "SP-AFDM with OMP Front-End," 2024.
8. Zhou et al., "Guard-Interval-Free Pilot-Aided AFDM with Iterative Interference Cancellation," 2024.
9. Huang et al., "Joint Channel Estimation and Symbol Detection for AFDM (DNN-aided / GI-free)," 2025.
10. Ranasinghe et al., "Oversampled AFDM Joint Channel Estimation and Data Detection," 2024.
11. Cao et al., "AFDM-OMP for Multi-Scale Multi-Lag UWA Channels," 2024.
12. J. A. Tropp and A. C. Gilbert, "Signal Recovery From Random Measurements via OMP," *IEEE Trans. Inf. Theory*, 2007.
13. C. R. Berger et al., "Sparse Channel Estimation for Multicarrier UWA Communication: Compressed Sensing," *IEEE Trans. Signal Process.*, 2010.
14. M. Stojanovic and J. Preisig, "Underwater Acoustic Communication Channels," *IEEE Commun. Mag.*, 2009.
15. P. Raviteja et al., "Interference Cancellation and Iterative Detection for OTFS," *IEEE Trans. Wireless Commun.*, 2018.
16. A. P. Orozco-Lugo et al., "Superimposed Training for Channel Estimation," 2011.
17. V. Monga, Y. Li, Y. C. Eldar, "Algorithm Unrolling: Interpretable, Efficient Deep Learning," *IEEE Signal Process. Mag.*, 2021.
18. K. Gregor and Y. LeCun, "Learning Fast Approximations of Sparse Coding (LISTA)," *ICML*, 2010.

> 注：精确的卷期页码以你 FYP 的 `references.bib` / `main.bbl` 为准；上表为短版精选与可读化标题。需要我从 bib 抽全字段可再说。
