# Search shortlist: co-delay covariance novelty check (C1-C4)

- **Task**: `.trellis/tasks/10-17-codelay-novelty` (parent 09-22-tf-production-gap-audit)
- **Role**: concept-aware literature search only. 本文件不含新颖性判定; 判定由编排者做 (`novelty-verdict.md`).
- **Date**: 2026-10-17 (检索当日)
- **Scope**: external. 背景材料: `research-assets/res-20261017-01.md`, `res-20261017-02.md` (Interpretation / Limits).
- **Claims under test** (见 prd.md): C1 现象 (标量化数据不确定性 -> 同时延近重复幻影原子); C2 机制 (同时延原子间数据不确定性相干, Gamma_ij ~ Sigma_v * D_N(dnu)); C3 原则 (精确投影协方差是两类信道上唯一都最优的规则); C4 理论 (受限兼容定理, 等时延 doublet 特征值 1 +/- |D_N|).

## Evidence level used in this file

- **V** = 取得全文并读了与本任务相关的章节和关键词扫描结果 (不是通读全文; 每条注明读了哪里).
- **A** = 只读摘要. **S** = 只看检索片段/标题. **R** = 凭记忆 (只用于卷期页码类元数据, 已在条目内标出).
- 引文均为原文逐字, 每条 <= 15 词, 带章节或公式号 (编号取自所读版本, 期刊版可能不同).

## Tool status (影响覆盖面, 请编排者知悉)

- 本地 `search_papers.py`: 前几次查询正常 (arXiv + OpenAlex + Crossref). 之后 OpenAlex 当日免费额度耗尽 (HTTP 429 "budget used up"), 含 OpenAlex 的调用会挂起到超时; 改用 `--sources crossref arxiv` 后恢复.
- WebSearch/WebFetch 工具在本会话不可用. 用 `curl` 直取 arXiv abs/pdf/html, arXiv API, Semantic Scholar DOI 端点 (搜索端点 429), Crossref (无摘要).
- DuckDuckGo HTML 与 Brave HTML 各成功若干次后触发反爬 captcha, 此后不再尝试 (未绕过). 因此 B 区和 E 区的"自由文本网络搜索"偏少, 主要靠本地脚本 + arXiv.
- IEEE/SIAM/IOP 付费全文未取得的条目一律标 A 或 S.

---

## 1. Query log

### Area A: errors-in-variables / matrix uncertainty / support recovery

| # | Tool | Query | Hits scanned |
|---|---|---|---|
| A1 | search_papers.py (arxiv+open_alex+crossref), 4-query union | matrix uncertainty selector sparse regression errors in variables / corrected Lasso missing noisy covariates high dimensional / sparsity-cognizant total least squares / perturbed compressed sensing general deviants | 67 unique, top 25 |
| A2 | same | high-dimensional regression with noisy and missing data provable guarantees with nonconvexity / linear regression with an unknown error covariance conic programming errors-in-variables / errors-in-variables sparse regression correlated measurement error covariance support recovery false positives / Lasso measurement error correlated errors support selection inconsistency | ~60 unique, top 27 |
| A3 | same | matrix perturbation compressed sensing structured perturbation spurious support / total least squares sparse recovery structured errors covariance / sparse recovery with uncertain dictionary perturbation known covariance whitening / compressed sensing noisy sensing matrix additive error correlated columns support recovery | 63 unique, top 26 |
| A4 | search_papers.py (crossref+arxiv) | Bayesian total least squares sparse errors-in-variables variational / sparse Bayesian learning dictionary perturbation known covariance measurement matrix uncertainty / support recovery dictionary uncertainty correlated perturbation OMP / compressive sensing structured perturbation covariance weighted | top 16 |
| A5 | arXiv API (title/abstract field queries) | errors-in-variables + support recovery + sparse; matrix uncertainty + sparse; measurement error + design matrix + spurious; perturbed + dictionary + support + covariance + CS | ~11 hits (last two queries empty) |
| A6 | DuckDuckGo HTML | errors-in-variables Lasso spurious variables correlated measurement error design matrix support recovery false positives | 5 hits (3 further queries blocked by captcha) |
| A7 | arXiv title lookups | Rosenbaum-Tsybakov, Belloni et al., Datta-Zou, Herman-Strohmer, Rudelson-Zhou | ID resolution |

Full text obtained and read (relevant sections): arXiv 0812.2818, 1109.3714, 1412.5632, 1008.2996, 1206.0823, 0907.2955; keyword-scanned: 1112.4413, 1408.0241, 1510.07123.

### Area B: data-aided / decision-directed / soft-symbol CE with data in the regression matrix

| # | Tool | Query | Hits scanned |
|---|---|---|---|
| B1 | search_papers.py (arxiv+open_alex+crossref) | joint channel estimation and data detection sparse Bayesian learning iterative / expectation maximization channel estimation soft symbols covariance data uncertainty / soft-input channel estimation turbo equalization symbol variance / variational Bayes joint channel estimation detection sparse channel unknown data | 17 |
| B2 | same | decision-directed channel estimation soft decisions symbol uncertainty variance included in estimator / iterative channel estimation turbo equalization soft feedback estimation error covariance of data symbols / EM algorithm channel estimation unknown data symbols E[X^H X] second-order statistics of symbols / bilinear message passing joint channel estimation data detection variances of symbols | 32 |
| B3 | same, 4 queries on residual-interference / Gaussian-approximation wording | (call timed out after OpenAlex quota ran out; no output) | 0 |
| B4 | search_papers.py (crossref+arxiv) | soft decision directed channel estimation symbol covariance / sparse Bayesian learning joint channel estimation data detection unknown data symbols | 20 |
| B5 | same | expectation maximization channel estimation soft symbols conditional second moment of data symbols / variational Bayesian joint channel estimation detection sparse multipath data symbols uncertainty / sparse channel estimation soft decision feedback support detection tap selection erroneous decisions | 16 |
| B6 | arXiv API | 4 strict-AND queries (EM/VB/EP + soft symbols + sparse + OFDM) | 0 hits (queries too strict) |
| B7 | Brave / DDG | 3 free-text queries on E[X^H X] soft-symbol covariance and JSBL E-step | blocked (captcha), 0 |

Full text read (relevant sections): arXiv 1104.0419 (Yoon-Moon), 2305.15855 (Mehrotra et al.), 2309.08177 (Huang-Guo, keyword scan). Abstract only: Prasad-Murthy-Rao (no arXiv version found), Song-Singer-Sung, Nicoli et al., Thoota-Murthy.

### Area C: delay-Doppler SP data-aided CE and path detection

| # | Tool | Query | Hits scanned |
|---|---|---|---|
| C1 | search_papers.py (arxiv+open_alex+crossref) | superimposed pilot OTFS data-aided channel estimation iterative decoding / OTFS superimposed pilot channel estimation data interference cancellation soft symbols / off-grid sparse Bayesian learning OTFS channel estimation fractional Doppler / AFDM superimposed pilot iterative channel estimation data detection | 33 |
| C2 | same | OTFS spurious paths false alarm channel estimation fractional Doppler leakage / OTFS channel estimation ghost paths extra detected paths threshold / AFDM channel estimation fractional Doppler spurious path detection same delay / OTFS multiple Doppler paths same delay tap estimation sparse recovery | 28 |
| C3 | search_papers.py (crossref+arxiv) | OTFS AFDM redundant duplicate paths pruning channel estimation closely spaced Doppler same delay / delay-Doppler channel estimation paths sharing the same delay different Doppler shifts resolution / AFDM channel estimation inter-Doppler interference adjacent Doppler coherence Dirichlet / OTFS iterative channel estimation residual data interference spurious path false alarm threshold update | 18 |
| C4 | arXiv API | AFDM + superimposed + pilot; OTFS + superimposed + pilot + iterative; OTFS + data-aided + sparse; AFDM + CE + data-aided; AFDM + fractional + sparse Bayesian; AFDM multiscale multilag; OTFS structured sparse message passing (about 8 queries) | ~35 hits |

Full text read (relevant sections): arXiv 2501.15935 (Kanazawa), 2607.18881 (Luo), 2010.15066 (Mishra), 2101.05629 (Wei), 2404.10232 (Zheng), 2412.01498 (DA-OMP), 2610.09970 (Wang et al.).

### Area D: basis mismatch / off-grid spurious atoms

| # | Tool | Query | Hits scanned |
|---|---|---|---|
| D1 | search_papers.py (arxiv+open_alex+crossref) | sensitivity to basis mismatch in compressed sensing / off-grid compressed sensing spurious atoms near duplicate support splitting / grid refinement coherent dictionary off-grid support recovery ghost atoms / super-resolution sparse recovery highly coherent dictionary pairs of atoms spurious support | 32 |
| D2 | search_papers.py (crossref+arxiv) | band-excluded orthogonal matching pursuit coherent dictionary / coherence-pattern guided compressive sensing unresolved grids / Newtonized orthogonal matching pursuit frequency estimation continuum / redundant dictionary highly coherent atoms greedy pursuit selects neighboring atoms | 16 |
| D3 | Brave HTML | Sensitivity to basis mismatch (Chi Scharf Pezeshki Calderbank); Duval Peyre thin grids LASSO spurious spikes; off-grid Lasso splits one source into two adjacent grid atoms | 12 |
| D4 | DDG / arXiv API | 3 DDG queries blocked; 5 arXiv API queries (basis mismatch, spurious, off-grid, super-resolution) | ~4 irrelevant |

Full text read (relevant sections): Chi et al. (author-hosted PDF), arXiv 1503.08577, 1106.5177.

### Area E: wildcards (co-delay coherence, model order with correlated noise)

| # | Tool | Query | Hits scanned |
|---|---|---|---|
| E1 | search_papers.py (arxiv+open_alex+crossref) | Dirichlet kernel coherence OTFS delay-Doppler path response multiple paths same delay / OTFS channel estimation multiple paths with identical delay different Doppler resolvability / model order selection correlated noise sparse channel path detection false alarm / number of paths estimation OTFS information criterion spurious paths | 25 |
| E2 | search_papers.py (crossref+arxiv) | detection of number of signals colored noise overestimation white noise assumption / model order selection unknown noise covariance overestimate number of components / number of paths estimation colored noise sparse channel / sparse recovery non-white noise covariance weighted greedy pursuit support | 16 |
| E3 | Brave HTML | Wax-Kailath colored noise overestimate sources; Talebi-Pratt model order selection correlated noise; source enumeration colored noise whitening | 18 |
| (C3 above also covers same-delay / Dirichlet wording) | | | |

---

## 2. Ranked shortlist (15)

排序依据: 与 C1-C3 实质内容 (而非主题) 重叠的可能性, 同档内按 A -> B -> C -> D 区排列. 不代表新颖性结论.

### 1. Loh and Wainwright, "High-dimensional regression with noisy and missing data: Provable guarantees with nonconvexity"
- **ID**: Ann. Statist. 2012, DOI 10.1214/12-AOS1018; arXiv:1109.3714. **Evidence**: V (Sec. 1-3, Example 1, Theorem statements by keyword scan).
- **May collide with**: C2, C3 (correction by the exact error covariance); not C1.
- **Facts**: 观测 Z = X + W, W 的行 i.i.d., 零均值, 协方差 Sigma_w 已知且可为一般矩阵 (Eq. 2.8 的定义对一般 Sigma_w 成立; Corollary 1 的显式界取 Sigma_x = sigma_x^2 I, Sigma_w = sigma_w^2 I; 依赖数据扩展用 |||Sigma_w|||_op). 用 Gamma_hat = Z'Z/n - Sigma_w 与 gamma_hat = Z'y/n 代替 Lasso 的 Gram 与相关向量; n < p 时 Gamma_hat 非 PSD, 目标非凸, 加 l1 球约束. 保证形式为 l2 误差界; 仿真取 Sigma_w = sigma_w^2 I. 全文无 "忽略/标量化 Sigma_w 造成近重复支撑原子" 的分析.
- **对应关系 (供核对)**: E[W'W]/n = Sigma_w 是误差矩阵的列 Gram, 与 res-20261017-01/02 里的 Gamma 同一类对象; 区别在 LW 假设行独立同分布.
- > "rows wi drawn i.i.d. from a zero-mean distribution with known covariance Σw" (Sec. 2, Example 1)
- > "the subtracted matrix Σw may cause Γ̂add to have a large number of negative eigenvalues" (Sec. 2, after Eq. 2.8)

### 2. Zhu, Leus, Giannakis, "Sparsity-Cognizant Total Least-Squares for Perturbed Compressive Sampling"
- **ID**: IEEE Trans. Signal Process. 59(5), 2011, DOI 10.1109/TSP.2011.2109956; arXiv:1008.2996. **Evidence**: V (abstract, Sec. III, Sec. V weighted/structured S-TLS, Sec. VII Test Case 2 ROC).
- **May collide with**: C2, C3, and the "this is just basis mismatch" objection (D).
- **Facts**: 稀疏回归里回归矩阵带扰动 (含网格失配场景). S-TLS = min ||[E e]||_F^2 + lambda ||x||_1, 约束 (A+E)x = y + e. Sec. V 推广到 "weighted and structured" 版本: 扰动向量 eps 由 p 参数化, S(p) = S_0 + sum p_k S_k (仿射结构), 代价 eps' W eps (W = 已知协方差之逆), 并说明 Toeplitz/循环等结构. Sec. VII Test Case 2 用 P_d / P_fa ROC 比较 S-TLS 与 Lasso 的支撑恢复 (EIV 模型 (4), A 为 20 x 40 i.i.d. 高斯矩阵; 未检视扰动的协方差设置). 没有 "标量化 vs 精确协方差" 的对比, 没有近重复原子分析. 该仿射结构与数据辅助字典 [Xi_p x_hat] (x 带不确定性) 的参数化形式一致 (供核对).
- > "account for structured and correlated perturbations with known covariance matrix" (Sec. III, after Prop. 1)
- > "perturbations appear both in the data vector as well as in the regression matrix" (Abstract)

### 3. Rosenbaum and Tsybakov, "Sparse recovery under matrix uncertainty"
- **ID**: Ann. Statist. 38(5), 2620-2651, 2010, DOI 10.1214/10-AOS793; arXiv:0812.2818. **Evidence**: V (abstract, Sec. 1, Sec. 6, Sec. 7.1 numerical results).
- **May collide with**: C1 (general phenomenon "ignoring matrix uncertainty over-selects"); not C2/C3.
- **Facts**: 模型 Z = X + Xi; 提出 MU-selector, 只用 sup-范数界 delta: |Xi|_inf <= delta, 无协方差结构. Sec. 7.1 (censored matrix, 100 x 500 i.i.d. Gaussian X) 报告 Lasso/Dantzig 的支撑集远大于真值但包含真值. 没有把多余原子与误差相关性联系起来.
- > "Lasso and Dantzig selector turn out to be extremely unstable in recovering the sparsity pattern" (Abstract)
- > "sets of nonzero components steadily include the relevant set, they are much too large" (Sec. 7.1, Results)

### 4. Loh and Wainwright, "Support recovery without incoherence: A case for nonconvex regularization"
- **ID**: arXiv:1412.5632 (Ann. Statist. 45(6), 2017; 期刊卷期凭记忆 R, 未核对). **Evidence**: V (Sec. 2.3, Sec. 3.3 Corollary 2).
- **May collide with**: C3 (support recovery with the exact Sigma_w).
- **Facts**: Sec. 3.3 对 corrupted covariates 用 primal-dual witness 证明: 在对 Gamma_hat = Z'Z/n - Sigma_w 的不相干条件 (其 Eq. 28) 与样本量 n >= c k log p 下, 非凸驻点唯一且 supp(beta_hat) 含于 supp(beta*), 加 beta_min 条件则符号一致. Sigma_w 假设已知. 不相干条件作用在修正后的 Gram 上; 无 "忽略 Sigma_w" 对照.
- > "Σw = Cov(wi) is assumed to be known" (Sec. 2.3)
- > "stationary points of the modified (nonconvex) Lasso program (27) are also support-recovery consistent" (Sec. 3.3)

### 5. Chen and Caramanis, "Orthogonal Matching Pursuit with Noisy and Missing Data: Low and High Dimensional Results" (ICML 2013 title: "Noisy and Missing Data Regression: Distribution-Oblivious Support Recovery")
- **ID**: arXiv:1206.0823 (v2 2015). **Evidence**: V (abstract, Sec. 1, Sec. 4 before Algorithm 1, Sec. 6 simulations; Def. 4).
- **May collide with**: C3 (greedy support selection under covariate error; the stated direction is opposite), C2 (Sigma_w = E[W'W]).
- **Facts**: mod-OMP 用未修正的 Z 做原子选择 (h_i = Z_i' r, 残差用 Z_I), Sigma_w 只在最终系数估计里使用; 作者称支撑恢复"分布无关", 无需 Sigma_w 或 Sigma_x. 同文仿真 (Fig. 6) 称 Loh-Wainwright 的投影梯度法 ([8]) 在 sigma_w 被估成一半或两倍时支撑恢复显著变差 (标量 sigma_w). 高维支撑定理假设 Definition 4 的 Independent sub-Gaussian design (X, W, e 条目独立), 作者写明证明"似乎需要"该独立性, 并预期算法在列相关时仍可用; 我看到的相关仿真是 Fig. 7(b) 中 X 的列相关 ((Sigma_x)_ij = 0.2), 未发现 W 列相关的专门仿真 (关键词扫描, 非通读).
- > "our support-recovery algorithm requires no knowledge of even the statistics of the noise" (Abstract, arXiv abs page)
- > "performs well despite correlation in the columns of X and W" (Sec. 4, opening paragraph)

### 6. Mishra, Singh, Prasad, Budhiraja, "OTFS Channel Estimation and Data Detection Designs With Superimposed Pilots"
- **ID**: IEEE Trans. Wireless Commun. 2021, DOI 10.1109/TWC.2021.3110659; arXiv:2010.15066 (v1). **Evidence**: V (Sec. II, Sec. III-A, III-B, Appendix A).
- **May collide with**: C1, C2 (how data interference is modeled in SP-OTFS estimation).
- **Facts**: 整数延迟/Doppler, Q 个路径; Omega_d = [Gamma_1 x_d ... Gamma_Q x_d] 与数据辅助字典同构. Lemma 1: E{Omega_d Omega_d^H} = sigma_d^2 Q I_MN (行侧二阶矩). SP-NI 的 LMMSE 估计 (Eq. 23) 用 C_wd = (sum_i sigma_hi^2)(sigma_d^2 + sigma_w^2) I_MN (Eq. 22), 即对 h (独立增益, C_h 对角) 取平均后得到的标量白噪声. SP-I (迭代数据辅助) 的等效噪声 Eq. 48 同为标量. 只估增益, 不做路径检测/支撑选择; 未讨论列侧 (路径间) 相关.
- > "includes the effect of mutual interference between data and pilot symbols" (Sec. III-A, after Eq. 24)
- Eq. 22 (公式, 非引文): C_{w~d} = ( Σ_i σ²_{h_i} ) ( σ_d² + σ_w² ) I_{MN}

### 7. Kanazawa, Iimori, Pradhan, Malomsoky, Ishikawa, "Superimposed Pilot-Based OTFS: Will It Work?"
- **ID**: arXiv:2501.15935 (v1 27 Jan 2025, v3 24 Feb 2026); IEEE Trans. Veh. Technol. 2026 (arXiv journal-ref; 检索库另记 DOI 10.1109/TVT.2025.3608199). **Evidence**: V (Sec. III-C, IV-C, VI).
- **May collide with**: C1 (spurious paths from interference), C2 (scalar sigma_d^2).
- **Facts**: 路径检测为整数 (l,k) 上的功率阈值 (Eq. 22). 初始阈值 gamma_SP^(0) = 3 sqrt(N_p (sigma^2 + sigma_d^2)) (Eq. 24), sigma_d^2 = 数据平均功率 (标量); 迭代 r >= 1 后阈值取 3 sqrt(N_p sigma^2) (Eq. 25), 即不再计入残余数据不确定性. 软判决副本只用均值 sum_j P x_j (Eq. 32), 不用方差. 明文说阈值过低会"检测出不存在的路径"; 结论节称分数 Doppler 下固定阈值可能失败. 未提同时延路径或幻影.
- > "resulting in the detection of non-existing paths" (Sec. III-C, case 1)
- > "Non-integer Doppler shifts spread energy across delay-Doppler bins, and a fixed threshold can fail" (Sec. VI)

### 8. Luo, Guan, Ge, Jiang, Meng, Gonzalez, "Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System"
- **ID**: arXiv:2607.18881 (21 Jul 2026); "Accepted by IEEE TCOM" (arXiv comment, 作者自述). **Evidence**: V (Sec. II-III, Algorithm 1, Eq. 15-24).
- **May collide with**: C1, C2 (scalar equivalent noise in an SBL support decision).
- **Facts**: 叠加导频 AFDM, MMV off-grid SBL (D-GESBL), 数据辅助: 解码后的硬判决 x_hat_d = Mod[Demod(.)] 构造字典 Phi_hat (Eq. 17-19), 失配项 W_bar = (Psi_d - Psi_d_hat) H + W 近似为复高斯 CN(0, beta^{-1} I_N) (Eq. 24), beta 为带 Gamma 先验的标量精度; 目标数由 sum_n mu > eps_thr 阈值给出. 无同时延/近重复原子分析, 无协方差项. grid evolution 针对网格失配.
- > "contains both the additive Gaussian noise and the residual interference caused by data detection errors" (Sec. III-B)
- > "Following the commonly adopted equivalent Gaussian approximation in iterative inference frameworks" (Sec. III-B, before Eq. 24)

### 9. Wei, Yuan, Li, Yuan, Ng, "Off-grid Channel Estimation with Sparse Bayesian Learning for OTFS Systems"
- **ID**: IEEE Trans. Wireless Commun. 2022, DOI 10.1109/TWC.2022.3158616; arXiv:2101.05629 (v1). **Evidence**: V (Sec. I, III-A, IV-B Remark 1, Sec. VI-C/D).
- **May collide with**: C1, C2 (data in measurement matrix treated as independent Gaussian noise), plus a data-aided remark.
- **Facts**: 嵌入式单导频 + 保护带; 1D/2D off-grid SBL. 无保护带时, 测量矩阵中未知数据的影响被当作"模型误差", 假设为独立高斯并并入测量噪声 (引文 [10]). Remark 1: 迭代数据辅助 (硬估计代入测量矩阵再跑 Algorithm 1) 作为改进. Sec. VI-C 报告无保护带时 NMSE 损失约 1-2 dB, 且 on-grid 方法比 off-grid 方法对干扰更稳健. 未涉及路径检测的同时延幻影.
- > "assumed to behave as independent Gaussian noise and can be absorbed into the measurement noise" (Sec. III-A, before Eq. 13)
- > "unknown data symbols in the measurement matrix in (23) as the impact of noise" (Sec. IV-B, Remark 1)

### 10. Duval and Peyre, "Sparse Spikes Deconvolution on Thin Grids" (journal: "Sparse regularization on thin grids I: the Lasso")
- **ID**: arXiv:1503.08577; Inverse Problems 2017, DOI 10.1088/1361-6420/aa5e12. **Evidence**: V (abstract, Sec. 1 intro; Sec. 2.2 definition scan only).
- **May collide with**: C1 (named near-duplicate phenomenon; the "basis mismatch" reading), C3 (exact support characterisation).
- **Facts**: 在细网格上, 小噪声极限下 Lasso 和 C-BP 在每个真实尖峰两侧各检出一个相邻网格点, 支撑大小约为真值两倍 ("extended support" 由最小范数对偶证书刻画). 机制是网格/相干性而非数据不确定性; 无协方差修正.
- > "both methods estimate twice the number of spikes as the number of original spikes" (Abstract)
- > "spikes of m0 gets duplicated as the two nearest neighbors on the grid G" (Sec. 1)

### 11. Fannjiang and Liao, "Coherence Pattern-Guided Compressive Sensing with Unresolved Grids"
- **ID**: SIAM J. Imaging Sci. 5(1), 2012, DOI 10.1137/110838509; arXiv:1106.5177. **Evidence**: V (abstract, Sec. 1-2 intro and Algorithm 1; proofs not read).
- **May collide with**: C3 (fixed rules "ban near duplicates").
- **Facts**: 网格间距小于 Rayleigh 长度时感知矩阵高相干; Band Exclusion (BE) 让 OMP 选中一个原子后把其相干带内的邻居排除 (BOMP), 再加局部优化 (BLOOMP). 前提是目标"宽间隔"这一先验; 理论保证以 Bottleneck 距离衡量. 与 A2n 近重复禁令同类的固定规则, 但出发点是网格相干而非数据不确定性.
- > "the technique of band exclusion (BE) to modify the Orthogonal Matching Pursuit (OMP)" (Sec. 1)
- > "take advantage of the prior information of widely separated objects" (Sec. 2)

### 12. Prasad, Murthy, Rao, "Joint Approximately Sparse Channel Estimation and Data Detection in OFDM Systems Using Sparse Bayesian Learning"
- **ID**: IEEE Trans. Signal Process. 62(14), 2014, DOI 10.1109/TSP.2014.2329272 (卷期凭记忆 R). **Evidence**: A (abstract via OpenAlex; no full text obtained, no arXiv version found).
- **May collide with**: C2 (EM over unknown data symbols in an SBL support/estimation problem); question B.
- **Facts**: J-SBL / recursive J-SBL / KSBL, 联合稀疏信道估计与数据检测; 摘要称算法可在测量矩阵因未知数据符号而"部分未知"时恢复一组近似稀疏向量. OFDM 数据符号在音调上对角作用, 故其不确定性协方差在抽头域的形态与 delay-Doppler 不同 (此点未读全文核对, 属推测, 请编排者读正文).
- > "recover a group of approximately sparse vectors even when the measurement matrix is partially unknown" (Abstract)

### 13. Song, Singer, Sung, "Soft Input Channel Estimation for Turbo Equalization" (with Yoon and Moon's description of it)
- **ID**: IEEE Trans. Signal Process. 52(10), 2885-2894, Oct. 2004, DOI 10.1109/TSP.2004.834270. **Evidence**: A (abstract); the second quote is from Yoon-Moon (arXiv:1104.0419, V on that passage).
- **May collide with**: C2 (soft-symbol uncertainty enters the CE as an effective-noise term); question B.
- **Facts**: 软输入 MMSE 线性信道估计 (抽头不相关模型) 与软输入 RLS (修改代价函数). Yoon-Moon 称其"把软判决质量计入等效噪声" (标量方差追踪), 并指出自己的 Kalman 方案不假设新息序列自动白, 因为流水线各级软判决之间相关 (这是跨迭代级的相关, 不是原子间相关). 全部是 MSE 层面; 无支撑/路径检测.
- > "incorporating the quality of the soft decisions as part of effective noise" (Yoon-Moon, Sec. III-B)
- > "soft input recursive least squares algorithm is also developed by modifying the cost function" (Song et al., Abstract)

### 14. Wang, Pan, Ren, Li, Wang, "Model-Order-Adaptive Channel Estimation for AFDM Systems with Fractional Delay and Doppler"
- **ID**: arXiv:2610.09970 (7 Oct 2026; 未发表版本). **Evidence**: V (abstract, Sec. III extrema analysis by scan, Sec. IV-A false-alarm calibration, IV-B/IV-C path birth and pruning; not cover-to-cover).
- **May collide with**: C1, C3 (neighbouring AFDM atoms are correlated; neighbourhood exclusion; residual-reduction acceptance).
- **Facts**: 双导频 AFDM, 无数据符号; 基于 SAGE 的模型阶数自适应. 新路径由残差归一化峰值统计量对 CFAR 阈值 gamma_ord 接受 (Eq. 28, 60), 其中 "有效独立单元数 K_eff" 用来近似校正相邻 AFDM 原子相关时的虚警; 为避免重复检测, 已接受/已剪枝位置的邻域被排除 (半宽 K_acc, K_tabu); 条件剪枝移除"无支持或冗余"路径. 噪声模型为白噪声; 不含数据不确定性. 摘要还称分数时延使 AFDM 响应出现主极值位移和次极值.
- > "approximate false-alarm calibration when neighboring AFDM atoms are correlated" (Sec. IV-A, after Eq. 28)
- > "we exclude neighborhoods of accepted and pruned locations" (Sec. IV-B, path initialization)

### 15. Chi, Scharf, Pezeshki, Calderbank, "Sensitivity to Basis Mismatch in Compressed Sensing"
- **ID**: IEEE Trans. Signal Process. 59(5), 2182-2195, 2011, DOI 10.1109/TSP.2011.2112650 (author-hosted PDF preprint read). **Evidence**: V (abstract, intro, Remark on leakage; theorems not read).
- **May collide with**: the reviewer objection "this is basis mismatch" (D); not C1-C4 directly.
- **Facts**: 假设基与实际稀疏基失配 (源不在网格中心) 时, 稀疏表示泄漏到所有位置而不可压缩, 恢复误差随失配水平上升; 讨论 DFT 网格失配与 Doppler/延迟成像. 分析单位是重构误差, 不是"哪些原子被接受"; 没有"近重复原子"这一术语.
- > "there is mismatch between the assumed and the actual bases for sparsity" (Abstract)
- > "The few nonzero elements of θ leak in to all locations through Ψ" (Sec. IV)

---

## 3. Near misses checked (and why farther)

1. Belloni-Rosenbaum-Tsybakov (arXiv:1408.0241, JRSS-B 2016) and Rosenbaum-Tsybakov "Improved MU selector" (arXiv:1112.4413, 2013): 只用 sup-范数界 delta / 未知噪声水平, 无协方差结构; 仿真里"Dantzig Z (ignoring EIV)"只比偏差. 摘要级 + 关键词扫描 (V partial).
2. Datta-Zou CoCoLasso (arXiv:1510.07123, Ann. Statist. 2017): 已知一般 Sigma_A (仅要求有限协方差), 把 Z'Z/n - Sigma_A 投影到最近 PSD 矩阵, 渐近符号一致; 与 LW 同族, 行 i.i.d., 无幻影原子分析 (V partial).
3. Herman-Strohmer (arXiv:0907.2955, JSTSP 2010), Yang-Zhang-Xie (arXiv:1112.0071, TSP 2012), Krzakala-Mezard-Zdeborova (arXiv:1301.0901, ICASSP 2013): 最坏情形 l1 稳定性 / 结构扰动 / 贝叶斯最优 MSE; Herman-Strohmer 称扰动是"与信号相关的 multiplicative noise" (V partial, 其余 A). 无原子层面支撑分析.
4. Rudelson-Zhou (arXiv:1611.04701, EJS 2017) 与 Qiu-Chen-Chen (arXiv:2601.01351): 误差沿观测方向相关 / 误差协方差预白化是否提高 EIV 估计效率; 推断与效率, 不是支撑原子 (A).
5. 软判决信道估计族: Yoon-Moon (arXiv:1104.0419, TCOM 2011), Nicoli et al. (TSP 2007, DOI 10.1109/TSP.2007.893979), Valenti-Woerner (JSAC 2001), Wehinger-Mecklenbrauker (TSP 2006), Wautelet et al. (TCOM 2007), Thoota-Murthy (TCOM 2021): MSE / BER 层面, 多为标量方差或均值替换; 其中除 Yoon-Moon 外均仅 A/S, 未核对是否含 E[X'X] = X_bar'X_bar + Sigma 形式.
6. SP-OTFS/AFDM 其他数据辅助估计器: Zheng et al. (arXiv:2404.10232, TVT 2024: Lemma 1 E{Phi_d Phi_d^H} = sigma_d^2 (Q+1) I, 阈值法, 写明 "non-existent paths will be erroneously included due to data and noise"), Cao et al. (ICCT 2024, OMP + 迭代, A), Yuan et al. (WCL 2021, DOI 10.1109/LWC.2021.3088836, A), Huang-Guo (arXiv:2309.08177, 消息传递; 方差取平均), Mehrotra et al. (arXiv:2305.15855, EM 把 X_d 当参数, 非 E[X'X]): 均为标量或硬判决数据模型, 无同时延分析.
7. 分数 Doppler 下同延迟相邻 Doppler 原子被视为正常现象: Wang-Huang-Chen-Farhang DA-OMP (arXiv:2412.01498, "fractional Doppler values can be approximated by a few adjacent points near the on-grid peak"), Yin et al. (TWC 2024, DOI 10.1109/TWC.2024.3408458, inter-Doppler interference, A), Cao et al. AFDM multi-scale multi-lag (arXiv:2405.02660, A), Liu et al. (arXiv:2011.14757, A): 无数据不确定性; 但会被审稿人用来说"同延迟多原子本来就是分数 Doppler 表示".
8. 非白噪声下的模型阶数: Eguizabal et al. (IEEE SPL 2019, "Source Enumeration in the Presence of Colored Noise", V partial), Talebi-Pratt (TSP 2015, A), Chen-Reilly-Wong (ICASSP 1992, S), Wax-Kailath (IEEE Trans. ASSP 1985, S): 误差在观测 y 的噪声协方差里, 不在字典里; 只是"白噪声假设使成分数估计出错"的类比.
9. 离网/CFAR/BIC 支撑选择: NOMP (Mamandipoor et al., TSP 2016, DOI 10.1109/TSP.2016.2580523, S), OGSBI (Yang-Xie-Zhang, arXiv:1108.5838, A), Yang-Shao-Hou-Ma (arXiv:2605.00049, A, BIC 选 delay-Doppler 支撑维度), Peng (arXiv:2608.20295, A, 高相干字典的物理支撑置信集): 白噪声模型, 无数据不确定性.
10. 检索缺口见 Sec. 4.

---

## 4. Not found / coverage gaps (explicit)

- **A**: 在检到的 EIV/matrix-uncertainty 文献中, 没有任何一篇明确说"忽略或白化结构化 (相关) 误差协方差会产生近重复/相关的支撑原子, 而用精确误差协方差可消除". 最近的是 R-T (忽略 matrix uncertainty 使支撑集"much too large", 但误差独立/截断), Chen-Caramanis (标量 sigma_w 估偏使支撑恢复变差), Zhu et al. (已知协方差的 structured/correlated 扰动, 未做幻影分析), Duval-Peyre (相邻重复由网格引起).
- **B**: 没找到分析"把符号不确定性协方差近似为标量/对角"对 支撑或路径检测 (而非 MSE) 的影响的论文. 未取得 Prasad et al. 正文, 无法确认其 E-step 是否出现 X_bar'X_bar + Sigma 形式; Song et al. 仅摘要.
- **C**: 在读过的 SP-OTFS/AFDM 数据辅助工作 (Mishra, Kanazawa, Luo, Wei, Zheng, Huang-Guo, Mehrotra) 中, 数据干扰为标量 sigma_d^2 / 标量精度 beta / 硬判决替换, 或由阈值吸收; 无一报告"同时延幻影路径". 仅 Kanazawa 与 Zheng 明确写到干扰超过阈值会检出不存在的路径.
- **D**: "近重复伪原子"在 off-grid 稀疏恢复中已有名字和定理 (Duval-Peyre doubling), 但其机制是网格, 且不涉及数据不确定性.
- **E**: 没找到把 Dirichlet 核相干用于决定"同一延迟上路径个数"的数据辅助文献; AFDM 方面仅 Wang et al. (2610.09970) 与 Yin et al. (TWC 2024) 触及邻近 Doppler 原子相关性, 且无数据不确定性.
- **C4**: 未单独检索 (定理层面的"标量闭合充要条件"和 doublet 特征值 1 +/- |D_N|); 2x2 Gram 的特征值 1 +/- |mu| 属初等事实, 未检索到把它与数据不确定性标量闭合联系起来的论文.
- 受限于 captcha/配额, B 区与 E 区的自由文本检索偏少; IEEE 付费全文 (Prasad, Song, Nicoli, Chi 期刊版, Yuan WCL, Cao ICCT, Yin TWC) 未读.
- 以上均为"检索范围内未发现", 不能推出"无人做过".
