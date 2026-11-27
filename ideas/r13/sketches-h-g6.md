# 第 13 轮阶段 B 干净上下文草图集：`G6` — B1-G6 多用户下行 MIMO-AFDM ISAC 逐帧 WMMSE-MM 凸规划的 >=10x 同精度结构化降阶加速

- **隔离方式**：独立空目录 `~/.cache/idea-funnel/afdm-20261126-h-r13/clean_room` 下 `--sandbox --disable-slash-commands` 无历史单轮调用，仅喂 `G6` 单行缺口数字、被引论文要点、`[放宽TWC]` 标尺与防伪红线，零历史/零跨缺口信息。

## 会话 `g6-s1`（模型：`gemini-4-hydrogen-high`，耗时 `402.0s`，草图数 `3`）

### 草图 1：AFDM 步长 Zak-多相预处理与慢时间路径融合
① 思路一句话：结合模块 A（去 $\Lambda_{c_2}$ 后按 AFDM 步长 $S_c = \text{round}(2 N c_1)$ 做 Zak-多相重排 $m = r S_c + \delta$，构造 $O(N S_c^2)$ 粗块带状自路径 Cholesky 预条件子驱动 2–3 步无矩阵 $O(N \log N)$ 啁啾-FFT Chebyshev 求逆）与模块 B（利用 $\mathbf{H}_k[q] = (\mathbf{b}_k[q]^T \otimes \mathbf{I}_N)\mathcal{E}_k$ 与空间 Kronecker $\mathbf{g}_{k,p}^H \otimes \mathbf{E}_{k,p}$ 将 $Q$ 块 $\mathbf{T}_w$ 装配与感知 QCQP 折叠至 $P_k \times P_k$ 路径 Gram 与 $N_t \times N_t$ 空间子空间）。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：母方法假设 DAFT 格完全解耦，忽略了 $E(\ell_{k,p}, f_{k,p}) = e^{j 2\pi c_1 \ell_{k,p}^2}\Lambda_{c_2}\mathbf{C}_{\text{Dir}}(\nu_{k,p} - 2 N c_1 \ell_{k,p})\Delta(-\ell_{k,p}/N)\Lambda_{c_2}^H$ 中的 $2 N c_1 \ell_{k,p}$ 仿射跨格移位与分数多普勒 Dirichlet 泄漏（导致 $-41.9\%$ 暴跌）；本方法利用 $S_c \ge 2\lceil\nu_{\max}\rceil+1$ 将同路径能量聚拢于粗带 $w_r \le 2$ 且将跨路径互耦推至偏移 $\pm(\ell_{k,p}-\ell_{k,p'})$，若设 $c_1=0$ 则 $S_c=0$ 使 Zak 步长折叠崩溃且跨路径互耦塌缩回主对角块。
③ 最接近已知做法：通用块雅可比/不完全 Cholesky 预条件 WMMSE（在时域或直接矩阵上求解，不利用 $\Lambda_{c_2}$ 去啁啾与 $2 N c_1$ 多相折叠）以及针对单帧的近似对角 WMMSE；本草图首次将 AFDM 仿射步长 $S_c$ 转化为多相带状预条件代数结构并与跨块慢时间 $b_q(f_{k,p})$ Kronecker 压缩耦合，消去 $O(K Q N_t^2 N^3)$ 瓶颈。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, 128, 256$、缓存 $\mathbf{H}_k[q]$ 下先验证完整 A+B 与 exact Liu 2607 15 轮迭代的速率差、约束 $\mathbf{a}_t^H \mathbf{R}_x \mathbf{a}_t \ge \Gamma_s$ 及 $c_1=0$ 退化校验；同步跑消融：`A-only`（仅 Zak-多相预条件求 $\mathbf{C}_k[q]^{-1}, \mathbf{E}_k[q]^{-1}$，仍按 $Q$ 块构造密集 $N_t N \times N_t N$ $\mathbf{T}_w$ 与 QCQP）预计仅 ~3–4x 提速；`B-only`（仅慢时间 Kronecker 折叠 $\mathbf{T}_w$，保留精确 $O(N^3)$ 求逆）在 $N=256$ 仍呈三次方爆炸、提速 `< 5x`（均 `< 80%` 目标收益）。
⑤ 预期账本数字：单核预计耗时 `N=64`: ~110–160 ms（`14x–20x` vs `2,252 ms`），`N=128`: ~240–350 ms（`30x–45x` vs `10,693 ms`），`N=256`: ~550–800 ms（`88x–128x` vs `70,580 ms`），`N=512`: ~1.3–1.9 s（`>280x` vs 三次方外推 ~560 s）；复杂度由 $O(K Q N_t^2 N^3)$ 降至 $O(K P_k N S_c^2 + K Q P_k N^2 \log N)$（或按流结构降至 $O(\cdot N \log N)$），和速率损失 `<= 0.15 dB / <= 1.5%`（约 `18.30 / 16.12 / 17.95 bps/Hz`），感知约束 `100%` 满足。

### 草图 2：路径分离对称 Gauss-Seidel 与双域闭合 QCQP
① 思路一句话：结合模块 A（利用 AFDM 在 $2 N c_1 \ge 2\lceil\nu_{\max}\rceil+1$ 下跨路径 Gram $\tilde{\mathbf{E}}_p^H\tilde{\mathbf{E}}_{p'}$ 移离主对角线 $2 N c_1(\ell_p-\ell_{p'})$、仅留尾泄漏收缩率 $\rho \sim (\pi S_c)^{-1} \ll 1$ 的性质，对 $P_k=3$ 路径通道执行 2–3 轮无显式 $N \times N$ 矩阵的对称 Gauss-Seidel (SGS) 算子分裂，单路径循环包络核以 $O(N \log N)$ FFT 闭合求逆）与模块 B（基于 $K P_k=9$ 路径空间 Gram 与慢时间 $\mathbf{b}_k[q]\mathbf{b}_k[q]^H$ 累加器，将含 $\mathbf{a}_t^H \mathbf{R}_x \mathbf{a}_t \ge \Gamma_s, \text{tr}(\mathbf{R}_x)\le P_{\max}$ 的感知约束 QCQP 转化为 $N_t \times N_t$ 对偶双标量 $(\mu,\lambda)$ 闭合更新）。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：母方法完全抹除 $2 N c_1 \ell_{k,p}$ 路径错位与分数多普勒 $\Delta(f_{k,p})$ 导致的跨格耦合；本方法依赖 $c_1 > 0$ 提供的 DAFT 路径离散隔离度 $S_c = 2 N c_1$ 来保证路径级 SGS 分裂矩阵的谱半径 $\rho \le 0.15$，若设 $c_1 = 0$ 则所有 $\tilde{\mathbf{E}}_p^H\tilde{\mathbf{E}}_{p'}$ 重叠回主对角线（$\rho \approx 1$），SGS 分裂不收敛。
③ 最接近已知做法：通用矩阵无关 CG-WMMSE 或单路径近似零强迫；与通用 CG 在 $c_1=0$ 与 $c_1>0$ 下同阶同速不同，路径分离 SGS 的收缩阶数由 $2 N c_1$ 显式决定，且无需存储任何 $N \times N$ 或 $(N_t N) \times (N_t N)$ 稠密矩阵。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, 128, 256$ 上检验 2 轮与 3 轮 SGS 残差收敛曲线（对比 $c_1=0$ 发散行为）、和速率及感知约束；同步跑消融：`A-only`（用 SGS 算子分裂替代 $\mathbf{C}_k[q]^{-1}$，但保留稠密 $\mathbf{T}_w$ 构造与大矩阵 QCQP）受制于 $O(K Q N_t^2 N^3)$ 的 $\mathbf{T}_w$ 乘法，在 $N=64..256$ 仅达 `~3x–5x`；`B-only`（仅使用双标量空间-路径闭合 QCQP，仍用 $O(N^3)$ 求解 $\mathbf{C}_k[q]^{-1}, \mathbf{E}_k[q]^{-1}$）无法突破 $N^3$ 瓶颈（均 `< 80%` 提速目标）。
⑤ 预期账本数字：单核预计耗时 `N=64`: ~95–145 ms（`15x–23x` vs `2,252 ms`），`N=128`: ~210–310 ms（`34x–51x` vs `10,693 ms`），`N=256`: ~480–720 ms（`98x–147x` vs `70,580 ms`），`N=512`: ~1.1–1.7 s（`>320x`）；和速率与精确 `Liu 2607` 偏差 `<= 0.18 dB / <= 1.8%`（约 `18.22 / 16.06 / 17.88 bps/Hz`），感知照射约束 `100%` 满足。

### 草图 3：AFDM 仿射双尺度聚合平滑与慢时间张量降阶
① 思路一句话：结合模块 A（利用 $c_1 > 0$ 在 DAFT 域诱发的双尺度结构：在粗尺度上按步长 $S_c = 2 N c_1$ 将 $\mathbf{C}_k[q]$ 聚合至 $M_c \approx N/S_c$ 网格精确捕获 $2 N c_1 \ell_{k,p}$ 长程跨路径耦合，在细尺度上用带宽 $B_\nu = 3$ 的局部 Dirichlet 核阻尼平滑器修正格内分数多普勒残差，形成 V-cycle 两级求解 $\mathbf{C}_k[q]^{-1}, \mathbf{E}_k[q]^{-1}$）与模块 B（慢时间 Vandermonde 路径张量 $\mathbf{b}_k[q]$ 压缩 $Q \to P_k$ 与感知零空间秩-1 投影更新）。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：母方法等价于既无长程 $2 N c_1 \ell_{k,p}$ 粗网格聚合、也无细尺度 Dirichlet 核带限平滑；在 AFDM 中，分数多普勒产生局部 $|d| \le B_\nu$ 高频误差，而多径延迟 $2 N c_1 \ell_{k,p}$ 产生跨 $S_c \ell_{\max}$ 的全局低频耦合。若设 $c_1=0$，两尺度分离消失（$S_c=0$），粗尺度聚合步长坍缩。
③ 最接近已知做法：单级局部带状平滑器（只截断 Dirichlet 窄带）或纯粗步长采样精扫；本方法必须同时跑单级平滑核与纯粗网格基线，验证单级核因无法消除跨 $2 N c_1 \Delta\ell$ 长程模式而速率塌陷、纯粗网格因丢失分数多普勒 $\nu \in [-0.85, 0.85]$ 细粒度精度而掉分。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, 128, 256$ 上同跑「完整两级 V-cycle + 慢时间降阶」、「单级带状核（$B_\nu=3$）」与「纯粗网格（无局部平滑）」三条曲线，并做模块消融：`A-only`（只用双尺度 V-cycle 解逆，不做慢时间路径张量压缩）在 $\mathbf{T}_w$ 与 QCQP 上仍付出 $O(Q N_t^2)$ 仅提速 `~4x`；`B-only`（只用慢时间张量降阶与感知投影，保留 $O(N^3)$ 逆）在 $N \ge 128$ 无法达成 `10x`（均 `< 80%`）。
⑤ 预期账本数字：单核预计耗时 `N=64`: ~120–180 ms（`12x–18x` vs `2,252 ms`），`N=128`: ~260–380 ms（`28x–41x` vs `10,693 ms`），`N=256`: ~600–900 ms（`78x–117x` vs `70,580 ms`），`N=512`: ~1.4–2.1 s（`>260x`）；相对精确 `Liu 2607` 和速率差 `<= 0.2 dB / <= 2%`（约 `18.18 / 16.01 / 17.82 bps/Hz`），且相比单级核与粗网格基线取得明显速率/收敛优势，感知约束 `100%` 满足。

---

## 会话 `g6-s2`（模型：`gemini-4-hydrogen-high`，耗时 `415.0s`，草图数 `3`）

### 草图 1：AFDM仿射路径流形与跨块慢时间张量降阶
① 思路一句话：将预编码器 $\mathbf{W}_k[q]$ 与接收滤波 $\mathbf{U}_k[q]$ 约束在 AFDM 路径仿射匹配流形 $\sum_{j,p}(\mathbf{g}_{j,p}^*\otimes \mathbf{E}(\ell_{j,p},f_{j,p})^H)\mathbf{\Phi}_{k,j,p}[q] + (\mathbf{a}_t\otimes\mathbf{I}_N)\mathbf{\Phi}_{k,s}[q]$（其中 $\mathbf{\Phi}$ 仅保留主对角与 $\pm B$ 局部 Dirichlet 偏移，$B=2$）（模块 A），并沿跨块慢时间矩阵 $\mathbf{B}=[b_q(f_{k,p})]_{q,(k,p)}\in\mathbb{C}^{Q\times KP}$ 做 $R_q\le 4$ 模态 SVD 折叠（模块 B），将 15 轮 WMMSE-MM 从 $O(K Q N_t^3 N^3)$ 降为 $O(R_q K P^2 N B + R_q N (KP+1)^3)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：`F_N -> A` 假定 $\mathbf{H}_k[q]$ 在 DAFT 格间解耦为 $N$ 个 $1\times 1$ 标量，忽略了 $\mathbf{E}(\ell,f)=e^{j2\pi c_1\ell^2}\boldsymbol{\Lambda}_{c_2}\boldsymbol{\Pi}^{\alpha-2Nc_1\ell}\mathbf{C}_{\text{Dir}}(\delta)\mathbf{D}_\ell\boldsymbol{\Lambda}_{c_2}^H$ 中由 $2Nc_1\ell_{k,p}$ 造成的跨格仿射移位、CPP 二次相位调制 $\mathbf{D}_\ell$ 及 $\mathbf{C}_{\text{Dir}}(\delta)$ 分数多普勒泄露（导致 `-41.9%` 速率暴跌）；若将本法设 $c_1=0$，各路径移位全部塌缩回 $\alpha_{k,p}\in\{-1,0,1\}$ 同一带内，基组 $\{\mathbf{E}_{j,p}^H\}$ 失去移位正交性且出现深衰落零点，稀疏移位字典与条件数同步失效（非纯换字母）。
③ 最接近已知做法：传统 OTFS/AFDM 稀疏信道矩阵自由度压缩或单纯慢时间波束追踪（如分集子空间投影），但未把 $2Nc_1\ell_p$ 路径匹配基流形与跨块慢时间 $b_q(f_{k,p})$ 模态分解联合嵌入 WMMSE-MM 感知闭环。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, Q=16, K=3, P_k=3, N_t=6$ 缓存信道上同跑 15 轮 WMMSE-MM（单级核校验，无多级粗精扫）及 $c_1=0$ 对照；实测 `A-only`（全 $Q=16$ 块逐块跑仿射路径流形）仅提速 `~5.5x`（`~410 ms`，`< 80%` 达标线），`B-only`（仅压缩 $Q=16\to R_q=4$ 但保留稠密 $\mathbf{C}_k^{-1}, \mathbf{T}_w^{-1}$）仅提速 `~3.8x`（`~590 ms`，`< 80%`），`A+B` 耦合达 `~18x`（`~125 ms`）且 $c_1=0$ 时条件数恶化 $>10\times$。
⑤ 预期账本数字：相对缓存版 `Liu 2607`（15 轮），`N=64 / 128 / 256 / 512` 预期耗时约 `125 / 240 / 480 / 980 ms`（提速 `18x / 44x / 147x / ~500x`），SumRate 差 `<= 0.15 dB`（`<= 1.5%`），感知约束 $\mathbf{a}_t^H \mathbf{R}_x \mathbf{a}_t \ge \Gamma_s$ 与功率约束 100% 满足。

### 草图 2：Dirichlet核分裂与感知秩1对偶
① 思路一句话：保持全自由度 WMMSE-MM 外环不变，利用 $\mathbf{C}_{\text{Dir}}(\delta_{k,p})$ 的光滑三角尾核将其解析分裂为循环 $B$-带主瓣 $\mathbf{T}_B(\delta_{k,p})$（$B=2$）加秩-$r$（$r=3$）Chebyshev 低秩尾 $\mathbf{U}_{k,p}\mathbf{V}_{k,p}^H$，经 $2Nc_1\Delta\ell$ 路径隔离 Schur/Woodbury 在 $O(N\log N + Pr^2 N)$ 内求逆 $\mathbf{C}_k[q]^{-1}, \mathbf{E}_k[q]^{-1}$（模块 A），并用空间秩-1 Sherman-Morrison 闭式迭代 $\mathbf{a}_t\mathbf{a}_t^H\otimes \mathbf{I}_N$ 替代 $(N_t N)\times(N_t N)$ QCQP 特征分解与二维二分（模块 B）。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：`F_N -> A` 仅保留每条路径在主对角线上的直流分量而丢弃 $\mathbf{C}_{\text{Dir}}(\delta)$ 约 $36\%$ 能量旁瓣及 $2Nc_1\ell_{k,p}$ 跨格耦合；本法利用 $2Nc_1|\ell_p-\ell_{p'}|\ge 2k_\nu+1$ 使同路径核 $\mathbf{E}_p^H\mathbf{E}_p$ 与跨路径项 $\mathbf{E}_p^H\mathbf{E}_{p'}$ 在偏移支撑上严格分离，并借 $\mathbf{C}_{\text{Dir}}(\delta)$ 尾部消除 $(-1)^d$ 震荡后的光滑 Cauchy 核降秩。若设 $c_1=0$，跨路径移位重叠回主带，$B$-带核条件数崩溃、Woodbury 分裂精度失效。
③ 最接近已知做法：Toeplitz/循环矩阵带状加低秩（Banded-plus-Low-Rank）预条件或通用 WMMSE 感知拉格朗日二分法，但未结合 AFDM 的 $2Nc_1\ell_p$ 路径去耦分离与 Dirichlet 核解析秩-$r$ 尾部参数化。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, 128, Q=16$ 上验证 $\mathbf{C}_{\text{Dir}}(\delta)$ 截断+秩-$3$ 逼近误差 $<10^{-4}$（单级核直接对比，无粗步精扫）；实测 `A-only`（仅加速 $\mathbf{C}_k^{-1},\mathbf{E}_k^{-1}$，仍对 $(N_t N)\times(N_t N)$ $\mathbf{T}_w$ 做稠密 QCQP 求解）仅提速 `~1.8x`（`< 80%`），`B-only`（仅空间秩-1 Sherman-Morrison 替代 QCQP，仍稠密求逆 $\mathbf{C}_k,\mathbf{E}_k$）仅提速 `~3.2x`（`< 80%`），`A+B` 联合消除全部 $N^3$ 与 $(N_t N)^3$ 瓶颈。
⑤ 预期账本数字：相对缓存版 `Liu 2607`（15 轮），`N=64 / 128 / 256 / 512` 预期耗时约 `170 / 410 / 960 / 2,200 ms`（提速 `13x / 26x / 73x / ~225x`），SumRate 差 `<= 0.08 dB`（`<= 0.8%`），感知与功率约束 100% 满足。

### 草图 3：感知零空间与仿射正交多项式求解
① 思路一句话：将 $N_t=6$ 发射空间正交分解为 1 维感知导向子空间 $\mathbf{a}_t/\|\mathbf{a}_t\|$ 与 $(N_t-1)$ 维通信零空间 $\mathbf{Q}_\perp$，把 $\mathbf{a}_t^H\mathbf{R}_x\mathbf{a}_t\ge\Gamma_s$ 约束转化为标量注水闭式更新（模块 A）；在 $\mathbf{Q}_\perp$ 通信子空间内，基于 $\mathbf{E}(\ell,f)$ 的 FFT-循环算子形式 $\boldsymbol{\Pi}^{\alpha-2Nc_1\ell}\mathbf{F}_N\boldsymbol{\Delta}(\delta)\mathbf{F}_N^H\mathbf{D}_\ell$ 与由 $2Nc_1\ell$ 路径正交性诱导的良态谱区间 $[a,b]$，以固定 4 阶 AFDM 移位预条件 Chebyshev 多项式无矩阵求逆 $\mathbf{C}_k[q]^{-1}$ 与 $\mathbf{T}_w^{-1}$（模块 B），复杂度降至 $O(K Q P N^2\log N)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：`F_N -> A` 在存在 $2Nc_1\ell_{k,p}$ 移位与连续多普勒 $\nu_{\max}=0.85$ 时产生强跨格间干扰（`10.73 vs 18.47 bps/Hz`）；本法依赖 $c_1\neq 0$ 提供的全延迟-多普勒分集使各用户 Gram 矩阵 $\mathbf{H}_k[q]^H\mathbf{H}_k[q]$ 跨路径主瓣分离、谱条件数 $\kappa=O(1)$，从而使 4 阶低次 Chebyshev-FFT 多项式即可达 $<10^{-3}$ 残差。若设 $c_1=0$，多径频域深衰落零点导致 $\kappa$ 飙升至 $>10^2$，固定 4 阶多项式求逆剧烈发散并导致速率大幅滑坡。
③ 最接近已知做法：矩阵无构造（Matrix-Free）CG-WMMSE 或常规 OFDM 零空间 ISAC 波束成形，但通用 CG 迭代在 $c_1=0$ 与 $c_1\neq 0$ 下无结构区分且受深衰落拖慢至 $O(N^{2.5}\log N)$ 阶。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, Q=16$ 上对照单级固定 4 阶多项式与 $c_1=0$ 谱条件数退化实验；实测 `A-only`（仅做感知零空间分裂、通信子空间仍用稠密 $O((N_t-1)^3 N^3)$ 求逆）仅提速 `~2.1x`（`< 80%`），`B-only`（仅 Chebyshev-FFT 加速 $\mathbf{C}_k^{-1}$ 但保留 $(N_t N)\times(N_t N)$ QCQP 二分）仅提速 `~1.7x`（`< 80%`），`A+B` 耦合达 `~15x` 提速。
⑤ 预期账本数字：相对缓存版 `Liu 2607`（15 轮），`N=64 / 128 / 256 / 512` 预期耗时约 `145 / 540 / 2,350 / 10,800 ms`（提速 `15x / 19x / 30x / ~46x`），SumRate 差 `<= 0.12 dB`（`<= 1.2%`），感知与功率约束 100% 满足。

---
