# 第 13 轮阶段 B 干净上下文草图集：`G4` — B1-G4 0 dB IBO 重度饱和非线性功放下多用户 16-QAM 下行 MIMO-AFDM ISAC 预编码

- **隔离方式**：独立空目录 `~/.cache/idea-funnel/afdm-20261126-h-r13/clean_room` 下 `--sandbox --disable-slash-commands` 无历史单轮调用，仅喂 `G4` 单行缺口数字、被引论文要点、`[放宽TWC]` 标尺与防伪红线，零历史/零跨缺口信息。

## 会话 `g4-s1`（模型：`gemini-4-carbon-high`，耗时 `740.2s`，草图数 `3`）

### 草图 1：峰值圆盘跨块斜移调频与非对称盒分裂预编码
① 思路一句话：在 `0 dB IBO` 软限幅功放零失真输出凸圆盘 $\mathcal{B}_\infty(A_{\text{sat}})=\{|X_{n,t}^{(q)}|\le A_{\text{sat}}\}$ 内，耦合 **机制 A（时域峰值圆盘投影与 DAFT 域 16-QAM 非对称盒集 $\mathcal{C}(\gamma\mathbf{s}^{(q)})$ 分裂：内 4 点紧方盒、边 8 点半带、角 4 点外扩正象限以释放峰值裕度）** 与 **机制 B（$Q$ 块变斜率反 Dirichlet 调频参考簇 $U_{\text{ref},n}^{(q)}[t]=A_{\text{sat}}e^{j2\pi(c_1+\frac{r_q}{2N})t^2+j\frac{2\pi}{N}\pi_q(n)\Delta_M t}$，取 $r_q=s_q-2Nc_1$ 使 $\min_{1\le\tau\le\ell_{\max}}\|s_q\tau\|_{\mathbb{T}_N}\ge\lfloor\frac{N}{2\ell_{\max}+1}\rfloor$ 压低分数多普勒核旁瓣并跨块旋转滞后相位）**，用带移循环预处理 ADMM 求解，单步复杂度 $O(KP_kN_tN+(N_t+K)N\log N)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：母方法逐子载波建设性区域/盒约束预编码直套 `F_N → A` 假定频域信道对角，漏掉 AFDM 多径时延产生的 $2Nc_1\ell_{k,p}$ 跨格仿射移位、$\boldsymbol{\Gamma}_{\text{CPP},\ell_{k,p}}$ 啁啾边界相位与分数多普勒 Dirichlet 核扩散（致 SER 崩至 `89%`）；若设 $c_1=0$，参考斜率补偿 $r_q=s_q-2Nc_1$ 与 CPP 剪切项 $e^{-j4\pi c_1\tau t}$ 失配，多径频带坍缩重叠且带移预处理失效。
③ 最接近已知做法：`Rang Liu & Schober (arXiv:2607.05119)` 多用户线性 MIMO-AFDM ISAC 预编码（PAPR $\approx 10.3\text{ dB}$，`0 dB IBO` 下 SER 硬地板 `14.11%`）与 OFDM 符号级 16-QAM 建设性区域预编码（无 $2Nc_1\ell_{k,p}$ 跨格耦合及跨块抗分数多普勒强杂波调频参考）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 `B1-G4` 参数（$N_t=8,K=3,P_k=3,N=64,Q=8,\text{SNR}=26\text{ dB},+25\text{ dB}$ 强目标）下跑 30 步预处理 ADMM，对比 `A+B`、`A-only`（去机制 B 参考簇，仅做圆盘+非对称盒投影）、`B-only`（机制 B 参考簇与块线性通信预编码朴素叠加过 SEL）及跨块固定 $r_q\equiv r_0$ 对照（检验等虚警下跨块相干假峰）。
⑤ 预期账本数字：模型化硬件损伤账 + 破壁账（100% 频效零子载波损失）：`A+B` 预计 `16-QAM SER = 0.4%–0.9%`（较 `14.11%` 下降 `15×–35×`）、等虚警 `WeakSINR = 14.6–16.0 dB`（较 `13.08 dB` 提升 `+1.5~+2.9 dB`，较纯通信峰值投影 `9.11 dB` 提升 `+5.5~+6.9 dB`）；消融 `A-only` 的 `WeakSINR` 跌至 `9.1–10.0 dB`（感知增益 `< 0%`），`B-only` 的 `SER` 为 `11.8%–14.0%`（通信增益收回 `< 20%`）。

### 草图 2：仿射零空间因果跨块扁长球波模糊槽通感预编码
① 思路一句话：在零子载波预留（零 CSR 损失）下，将发射矩阵参数化为 $\mathbf{X}^{(q)}=\mathbf{X}_{\text{MN}}^{(q)}(\gamma\mathbf{s}^{(q)})+\mathcal{P}_{\ker(\mathcal{H}^{(q)})}(\mathbf{W}^{(q)})\in\mathcal{B}_\infty(A_{\text{sat}})$，耦合 **机制 A（无矩阵共轭梯度与圆盘交替投影的全局 $(N_t-K)N$ 维多径仿射带状零空间嵌入）** 与 **机制 B（对 CPP 剪切滞后积 $d_{\tau,n,n'}^{(q)}[t]=(X_{n,t}^{(q)})^*(\boldsymbol{\Gamma}_{\text{CPP},\tau}\boldsymbol{\Pi}^\tau\mathbf{x}_{n'}^{(q)})_t$ 在连续分数多普勒 $[-2\nu_{\max},2\nu_{\max}]$ 精确积分导出的低秩扁长球波 DPSS Toeplitz 核 $\mathbf{K}_{2\nu_{\max},0}$（有效秩 $R_0\approx 5$）及因果跨块相消记忆项 $\mathbf{m}_{\tau,n,n'}^{(q)}=\sum_{q'<q}\mathbf{K}_{2\nu_{\max},q-q'}\mathbf{d}_{\tau,n,n'}^{(q')}$ 四次上界化最小化 MM）**，单步复杂度 $O((\ell_{\max}R_0N_t^2+KP_kN_t)N+KN\log N)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：母方法逐载波空域零空间投影直套 `F_N → A` 忽略 $2Nc_1\ell_{k,p}$ 跨格移位带致多径串扰崩盘（`SER = 89.04%`），`Gourar CSR` 直套则牺牲 `20%` 频效且限单流 PSK；若设 $c_1=0$，滞后积中的 $c_1$-CPP 剪切相位 $e^{-j4\pi c_1\tau t}$ 消失致时延-多普勒模糊退化耦合，且信道 $\mathcal{H}^{(q)}$ 退化为逐频点分块对角深衰落而压缩圆盘可行尺度 $\gamma$。
③ 最接近已知做法：`Gourar et al. (arXiv:2609.14030)` 单天线 20% 啁啾子载波预留（CSR）随机搜索降 PAPR/旁瓣方法，以及单块无记忆 MIMO 雷达局部模糊函数四次 MM 优化（无 AFDM 全局仿射零空间嵌入及跨块因果 DPSS 相消记忆）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 `B1-G4` 参数下取前 $R_0=5$ 个 DPSS 特征锥构造四次 MM 跑 25 轮，对比 `A+B`、`A-only`（仅做仿射零空间峰值圆盘投影，关掉机制 B 模糊槽目标）、`B-only`（用逐 DAFT 格伪零空间或未限幅叠加跑机制 B 过 SEL）及置零跨块记忆 $\mathbf{m}_{\tau,n,n'}^{(q)}=\mathbf{0}$ 的单块独立版。
⑤ 预期账本数字：模型化硬件损伤账 + 破壁账（100% 频效、严格因果零前视）：`A+B` 预计 `16-QAM SER = 0.5%–1.1%`（较 `14.11%` 下降 `13×–28×`）、等虚警 `WeakSINR = 14.8–16.2 dB`（在 $|\tau|\le 4,|\nu|\le 1.5$ 形成 `<-38 dB` 跨块相消模糊槽，较 `13.08 dB` 提升 `+1.7~+3.1 dB`）；消融 `A-only` 的 `WeakSINR` 回落至 `9.1–9.8 dB`（感知增益 `< 0%`），`B-only` 的 `SER > 12.0%`（通信增益收回 `< 18%`）。

### 草图 3：啁啾前缀扩展频域酉流形分裂与鞍点对偶预编码
① 思路一句话：全程免除矩阵求逆，耦合 **机制 A（依托 AFDM 逆变换 $\mathbf{A}^H=\boldsymbol{\Lambda}_{c_1}^H\mathbf{F}_N^H\boldsymbol{\Lambda}_{c_2}^H$ 跨 $2Nc_1\ell_{k,p}$ 分散频带满足的全局 Kashin 不确定性条件，构造 $\ell_\infty/\ell_1$ 极范数 Chambolle-Pock 一阶鞍点算子 $\min_{\|\mathbf{X}^{(q)}\|_\infty\le A_{\text{sat}}}\max_{\boldsymbol{\Lambda}}\operatorname{Re}\langle\boldsymbol{\Lambda},\mathcal{H}^{(q)}(\mathbf{X}^{(q)})-\gamma\mathbf{s}^{(q)}\rangle-\delta\|\boldsymbol{\Lambda}\|_2$）** 与 **机制 B（经 $c_1$-CPP 精确扩展矩阵 $\mathbf{E}_{\text{CPP}}(c_1)\in\mathbb{C}^{(N+\ell_{\max})\times N}$ 将剪切互模糊转化为 $2N$ 点零填充 FFT 谱内积，引入多普勒切片酉流形辅助矩阵 $\mathbf{V}_{g,f}^{(q)}\in\mathcal{U}(N_t)$ 做 $8\times 8$ 极分解并施加慢时间正交相位编码 $\mathbf{D}_q=\operatorname{diag}(e^{j\frac{2\pi}{Q}qn})$）**，单步复杂度 $O(KP_kN_tN+(K+GN_t)N\log N+GNN_t^3)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：母方法（Kashin $\ell_\infty$ 通信预编码与 WeCAN 雷达谱分裂朴素串联 `A → B` 或 `F_N → A` 直套）既忽略 $\mathbf{E}_{\text{CPP}}(c_1)$ 边界啁啾相位 $e^{-j2\pi c_1(N^2-2Nm)}$ 致 $2N$-FFT 非周期相关在 $|\tau|\le\ell_{\max}$ 失配，又因串联叠加越界触发 SEL 二次削峰；若设 $c_1=0$，频选多径深衰落锁死单载波破坏全局 Kashin 峰值均摊条件，且丧失 $\mathbf{E}_{\text{CPP}}(c_1)$ 扩展谱结构。
③ 最接近已知做法：`Studer et al.` 峰值受限 MIMO 的 Kashin $\ell_\infty$ 原始-对偶通信预编码与 `Stoica et al.` MIMO 雷达 WeCAN $2N$-FFT 酉流形分裂波形设计（恒模纯雷达、无 $c_1$-CPP 扩展及慢时间跨块正交去假峰编码）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 `B1-G4` 参数及公平缓存信道矩阵下跨 $N\in\{64,128,256,512\}$（取 $G=5$ 个分数多普勒切片）运行免求逆鞍点-酉分裂迭代，对比 `A+B`、`A-only`（仅跑机制 A 鞍点圆盘通信预编码）、`B-only`（机制 B 的 CPP-WeCAN 波形与 Bussgang 线性预编码朴素叠加过 SEL）以及同精度块线性稠密求逆耗时。
⑤ 预期账本数字：模型化硬件损伤账 + 破壁账 + 算力账：`A+B` 在 $N=64$ 预计 `16-QAM SER = 0.5%–1.1%`（较 `14.11%` 下降 `13×–28×`）、等虚警 `WeakSINR = 14.5–15.9 dB`（较 `13.08 dB` 提升 `+1.4~+2.8 dB`），且跨 $N=64..512$ 较 $O(K^3N^3)$ 块通感预编码实测同精度提速 `12×–35×`；消融 `A-only` 的 `WeakSINR` 跌至 `9.1–10.1 dB`（感知增益 `< 0%`），`B-only` 的 `SER` 退回 `11.5%–13.9%`（通信增益收回 `< 22%`）。

---

## 会话 `g4-s2`（模型：`gemini-4-hydrogen-high`，耗时 `79.0s`，草图数 `3`）

### 草图 1：圆盘内符号级盒约束与仿射模糊抑制联合预编码
① 思路一句话：在时域凸圆盘 $\mathcal{B}=\{X\in\mathbb{C}^{N_t\times N}:|X_{n,t}|\le A_{\text{sat}}\}$ 上通过 ADMM 耦合（A）DAFT 域 16-QAM 分级凸盒/外点扩张保真约束与（B）基于因果前块 CFAR 粗估强目标邻域 $(\hat{\ell}_s,\hat{\nu}_s)$ 的仿射斜带互模糊旁瓣二次惩罚 $\sum_{(m,l)\in\Omega_{\text{aff}}(c_1)}\|\operatorname{diag}(w_{m,l})A\mathcal{S}_{\Delta m,\Delta l}(X)\|_F^2$，借 $N_t-K=5$ 空域冗余直接免削波成帧，并以逐块独立数据符号杜绝跨块假峰。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：OFDM 下 $F_N$ 将通信信道与雷达延迟轴正交解耦，$c_1=0$ 时逐格凸盒 SLP 的零空间能量仅沿固定子载波堆叠；而 AFDM 中 $A=\Lambda_{c_2}F_N\Lambda_{c_1}$ 配合 CPP 相位使时域峰值硬限幅误差沿 $2Nc_1\ell_p$ 跨格移位和分数多普勒 Dirichlet 核 $D_N(\nu_p)$ 向全局泄漏，纯通信投影会把形变能量精准倾倒至强目标的啁啾模糊脊线 $\Delta m \equiv -2Nc_1\hat{\ell}_s+\hat{\nu}_s$ 上淹没弱目标。
③ 最接近已知做法：Rang Liu & Schober (arXiv:2607.05119, 2026) 的线性 MIMO-AFDM ISAC 与传统 OFDM 符号级恒模预编码（CI-SLP）；本方法把非凸恒模环面放宽为物理精确的凸圆盘 $|X_{n,t}|\le A_{\text{sat}}$，并将线性均方波形匹配替换为针对强目标 $2Nc_1\ell$ 仿射耦合脊线的定向旁瓣抑制，全程利用 $A,A^H$ 快速 FFT 算子，复杂度由稠密 $(N_tN)^3$ 降至 $\mathcal{O}(I_{\text{ADMM}}N_tN\log N)$。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, N_t=8, K=3, \text{IBO}=0\text{ dB}$ 固定信道下跑 200 帧（30 步 ADMM，强目标坐标仅用上一块导频回波 CFAR 粗捕），对比 `A-only`（仅凸圆盘 + 16-QAM 盒约束，去掉仿射模糊惩罚）、`B-only`（仅线性 MMSE + 仿射模糊惩罚，事后接 SEL 与 $1/K_{\text{PA}}$）与 `A+B`，并跨 $N\in\{64,128,256,512\}$ 测单帧耗时对比直接 CVX/稠密 KKT 求逆。
⑤ 预期账本数字：相对基线 (a) `14.11% / 13.08 dB`，预期 `A+B` 达 `SER ≈ 0.35%–0.60%`（破壁 `23×–40×`）、`WeakSINR ≈ 14.4–14.9 dB`（逼近 `15.56 dB` 线性上限）；消融预期 `A-only` 得 `0.40% / 9.2 dB`（雷达增益 `< 0%`），`B-only` 得 `9.5% / 14.3 dB`（SER 增益收回 `< 35%`），$N=64..512$ 同精度加速 `≥ 15×`。

### 草图 2：跨格空时零空间消峰与强目标斜带旁瓣整形
① 思路一句话：针对线性通感预编码 $X^{(0)}$ 超出圆盘的稀疏尖峰集合 $\mathcal{T}_{\text{peak}}=\{(n,t):|X^{(0)}_{n,t}|>A_{\text{sat}}\}$，利用 $N_t>K$ 与多径局部抽头数 $\ell_{\max}\ll N$ 构建（A）时域带状 Chirp-Toeplitz 滑窗零空间逆算子 $\mathcal{P}_{\mathcal{N},\ell_{\max}}(r_{\text{clip}})$ 将削波残差补偿至通信零空间，再经（B）强目标仿射模糊核 $Q_{s\to w}(c_1)$ 最小特征补空间投影重分配空域补偿能量。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：母方法（如逐 DAFT 格 Bussgang RZF 或 OFDM 峰抵消子载波 TR）假定子载波信道逐点解耦，设 $c_1\ne 0$ 后 $A H_k A^H$ 因 $2Nc_1\ell_p$ 跨格移位、CPP 相位耦合及 Dirichlet 拖尾呈现全带强耦合（导致基线 b 的 SER 飙至 `89.04%`），无法逐格分离通信零空间；本方案绕开 DAFT 域全局稠密矩阵，直接在稀疏时域抽头 $(\ell_{\max}+1=5)$ 与啁啾调制核 $\Lambda_{c_1}$ 的带状乘积域构造局部零空间。
③ 最接近已知做法：Gourar et al. (arXiv:2607.01064, 2026) 的 20% 预留啁啾子载波（CSR）局部搜索；本方法不牺牲任何频谱效率（0% 子载波预留），用 $N_t-K=5$ 空域自由度取代频域子载波损失，并针对性引入强目标仿射模糊核 $Q_{s\to w}(c_1)$ 的正交补投影，单块仅需带状 Cholesky/CG 求解，复杂度为 $\mathcal{O}(N_t^3\ell_{\max}^2|\mathcal{T}_{\text{peak}}|+N_tN\log N)$。
④ 最便宜 15 分钟检验（含 A-only / B-only）：取基线 (a) 线性预编码输出的超圆盘残差做 5 轮滑窗阻尼投影（每块独立生成），分别测 `A-only`（仅通信零空间消峰、不投影 $Q_{s\to w}^\perp(c_1)$）、`B-only`（仅在 $X^{(0)}$ 内部做 $Q_{s\to w}^\perp(c_1)$ 旁瓣整形再硬限幅）与 `A+B`，同步测 $N=64..512$ 下带状逆与全局 $(N_tN)^3$ 零空间求逆的算力比。
⑤ 预期账本数字：预期 `A+B` 实现 `SER ≈ 0.8%–1.3%`、`WeakSINR ≈ 14.1–14.6 dB`（同时赢过基线 a `14.11% / 13.08 dB` 与纯通信投影的 `9.11 dB` 雷达塌陷）；消融预期 `A-only` 得 `0.9% / 10.6 dB`、`B-only` 得 `11.2% / 14.0 dB`（单部件对双目标改进贡献均 `< 70%`），$N=512$ 下相比全局稠密零空间投影提速 `≥ 25×`。

### 草图 3：穿透限幅算子的跨啁啾伴随抗饱和通感预失真
① 思路一句话：放弃避让饱和边界，直接将逐样点可微 SEL 映射 $g_{\text{SEL}}(X)=X\odot\min(1,A_{\text{sat}}/|X|)$ 串联在 DAFT 信道 $AH_k$ 前作为精确前向物理算子，通过解析 JVP/VJP（$\mathcal{O}(N_tN\log N)$）与 L-BFGS 联合优化 pre-clip 预编码矩阵，同时最小化（A）饱和后经 $2Nc_1\ell_p$ 与 Dirichlet 核混叠至 16-QAM 格点的确定性三阶互调误差及（B）限幅波形在因果粗估强目标向弱目标格点耦合带上的自模糊旁瓣能量。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：逐天线独立数字预失真（DPD）无法突破 $|x_{n,t}|\le A_{\text{sat}}$ 硬天花板，而传统 Bussgang $K_{\text{PA}}X+d$ 将饱和互调近似为各向同性白噪；在 `IBO=0 dB` 下，AFDM 的 $A=\Lambda_{c_2}F_N\Lambda_{c_1}$ 会把多天线强三阶互调沿着分数多普勒 Dirichlet 核主/旁瓣及 CPP 边界相干聚拢，恰好破坏免均衡用户的 16-QAM 外圈判决边界与弱目标检测脊线。
③ 最接近已知做法：Sui & Zilong Liu (IEEE TCOM 2026) 的接收端 Bussgang $1/K_{\text{PA}}$ 标定与现有端到端单天线非线性预失真；本方法首次把全空-啁啾多天线协同的三阶互调当作可控制自由度，在发射端穿过 $g_{\text{SEL}}(\cdot)$ 主动生成反相互调去抵消 $c_1\ne 0$ 造成的跨格 ICI/ISI 与强目标斜带旁瓣，无需改变接收机免均衡结构（保持单标量接收）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：固定 15 步解析 VJP-LBFGS（初值为基线 a 加块内独立随机空域零空间抖动以防周期假峰），消融 `A-only`（目标仅含穿透 SEL 后的用户 16-QAM 均方误差与接收缩放优化）、`B-only`（目标仅含穿透 SEL 后的雷达模糊旁瓣与能量最大化）与 `A+B`，并在 $N=64..512$ 验证快速 FFT 伴随算子对有限差分/稠密 Jacobian 的速度优势。
⑤ 预期账本数字：预期 `A+B` 允许部分样点主动进入饱和区推高平均发射功率，达 `SER ≈ 0.5%–1.0%`、`WeakSINR ≈ 14.6–15.1 dB`（较基线 a 通信误码降 `14×–28×`、弱目标 SINR 净涨 `1.5–2.0 dB`）；消融预期 `A-only` 得 `0.55% / 9.5 dB`、`B-only` 得 `12.8% / 14.7 dB`（单部件收回 `< 75%`），跨 $N=64..512$ 较稠密 Jacobian 提速 `≥ 20×`。

---
