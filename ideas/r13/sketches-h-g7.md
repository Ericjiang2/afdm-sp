# 第 13 轮阶段 B 干净上下文草图集：`G7` — B1-G7 终端免均衡单抽头接收的多用户下行 MIMO-AFDM ISAC 总功率球预编码与强弱目标消遮蔽

- **隔离方式**：独立空目录 `~/.cache/idea-funnel/afdm-20261126-h-r13/clean_room` 下 `--sandbox --disable-slash-commands` 无历史单轮调用，仅喂 `G7` 单行缺口数字、被引论文要点、`[放宽TWC]` 标尺与防伪红线，零历史/零跨缺口信息。

## 会话 `g7-s1`（模型：`gemini-4-hydrogen-high`，耗时 `162.0s`，草图数 `3`）

### 草图 1：矩阵自由对偶预条件与块变互补啁啾通感预编码
① 思路一句话：用时间-DAFT 精确 FFT 正/伴随算子与 $2Nc_1\ell_p$ 仿射带分离循环 Dirichlet 谱预条件子驱动矩阵自由对偶 FISTA 消除分数多普勒截断地板，并在功率球 $\|S[q]\|_F^2 \le P_{\text{blk}}$ 内耦合块变互补相位 $\Lambda_{c_2}^{(q)}$ 与强目标空-DAFT 泄漏惩罚以消除跨块 ICI 假峰。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：`Li & Masouros TWC'18` 逐格解把信道当成对角阵，但 AFDM 下多径 $\ell_p$ 经 $\Lambda_{c_1}$ 与 CPP 相位 $e^{-j2\pi c_1(N^2-2N(\ell_p-n))}$ 耦合分数多普勒 Dirichlet 核，产生以 $2Nc_1\ell_p$ 为中心的跨格展开与全图长拖尾（致直套 SER 达 56.46%）；而 `Tang TWC'26` 在 DAFT 域做 $k_\nu=1$ 截断忽略了 Dirichlet 核慢衰减旁瓣（产生高 SNR 误码地板），且固定 $\Lambda_{c_2}$ 重复啁啾使 $+23\text{ dB}$ 强目标的块内快时间 ICI 跨 $Q$ 块同相累加产生邻格假峰。
③ 最接近已知做法：`Tang TWC'26`（DAFT 域 $k_\nu=1$ 截断对偶单纯形 QP）与 `Liu arXiv:2607.05119`（块均衡 + 高斯感知流）；本文去掉截断与块均衡，改用时域 $P_k$ 抽头移位加权+FFT 精确算子（$O(N_t K P_{\max} N\log N)$）、依赖 $2Nc_1>2\nu_{\max}+1$ 分离条件的块循环谱预条件子 $M_{\text{circ}}=(I_K\otimes F_N)\tilde{\Sigma}_{c_1}(I_K\otimes F_N^H)$，以及跨块 Golay/CAZAC 调制 $\Lambda_{c_2}^{(q)}$ 联动因果强目标泄漏算子 $\lambda_r\|\mathbf{a}_t^H(\hat{\theta}_s)S[q]\Phi_{c_1,\hat{\ell}_s,\hat{\nu}_s}\|_F^2$（若 $c_1=0$ 则路径在频域坍缩重合，预条件子失效）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64,128$、$Q=8$、QPSK/16-QAM 缓存信道与 $+23\text{ dB}$ 强/$0\text{ dB}$ 弱目标（$\Delta\ell=3,\Delta m=2.3$）上对照：(i) `A-only`（只跑无截断预条件对偶 FISTA、固定 $\Lambda_{c_2}$ 与 $\lambda_r=0$）测得通信 SER 逼近 QP 上限但全图 CFAR 出现 ICI 假峰且 WeakSINR 仍低；(ii) `B-only`（只加 $\Lambda_{c_2}^{(q)}$ 与 $\lambda_r$ 惩罚于 `Tang` $k_\nu=1$ 或 $F_N\to A$ 基线）测得假峰被压但 SER 卡在截断/失配地板；(iii) 验证 $c_1=0$ 时条件数与收敛步数退化，且 $N=64\to 512$ 耗时与精确 QP 对比。
⑤ 预期账本数字：QPSK `SER ≈ 0.04%–0.10%`（无截断地板，16-QAM 同步收敛至近似最优），`WeakSINR ≈ 25–28 dB` 且全图盲搜 CFAR 虚警假峰清零；单块对偶迭代 $O(N_t K P_{\max} N\log N)$，预期 $N=64/128$ 耗时降至 `~6 / 14 ms`（相对精确稠密 QP `191 / 693 ms` 提速 `>30x`，跨 $N=64..512$ 保持 `15x–100x`）。

### 草图 2：跨块步进啁啾脊旋转与长椭球零空间通感预编码
① 思路一句话：跨 $Q$ 块步进改变啁啾率 $c_1^{(q)}$ 旋转 AFDM 模糊函数脊线以破坏强目标跨块 ICI 相干叠加，同时用锚定于 $2Nc_1^{(q)}\ell_p$ 的低秩长椭球波序列（DPSS）精确折叠强目标 Dirichlet 拖尾并借 Woodbury-ADMM 在 $O(N\log N)$ 内完成原生球约束 CI 求解。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：OFDM 下模糊函数脊线正交固定，无 $c_1^{(q)}$ 调控自由度，强目标在 $\Delta\ell=3$ 处的快时间多普勒拖尾无法通过调频斜率在块间去相干；同时强目标与多径通信的分数多普勒 Dirichlet 核在 DAFT 域呈全长耦合而非稀疏带状，直接用局部窄窗清零或 $F_N \to A$ 逐格 CI 均会漏过远端旁瓣能量并引发严重多径/多用户 ICI（SER 飙升至 56.46%）。
③ 最接近已知做法：`Peishi Li et al. TWC'25`（OFDM 静态载波强目标旁瓣抑制作用于慢时协方差，未建模块内快时间多普勒 ICI）与传统窄带低秩干扰零空间投影；本方法独有地利用 AFDM 剪切斜率 $\Delta\nu \approx -2Nc_1^{(q)}\Delta\ell$ 的跨块 $c_1^{(q)}$ 步进旋转，并以秩 $R\approx\lceil 2\nu_{\max}\rceil+4\approx 6$ 的 DPSS 基 $U_s^{(q)}\in\mathbb{C}^{N\times R}$ 在 CPP 边界相位修正下构造强目标全长泄漏投影 $P_{\perp,s}^{(q)}=I-U_s^{(q)}(U_s^{(q)})^H$，与通道仿射移位 DPSS 因子共同化为「循环+低秩」结构（$c_1^{(q)}\equiv 0$ 时脊线旋转与仿射路径锚定同步坍缩）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在同批缓存信道与强弱双目标数据上运行消融：(i) `A-only`（固定单 $c_1$，仅用 DPSS 通道分解 + Woodbury-ADMM 求 QPSK/16-QAM CI 球投影）检验无地板通信性能与强目标残余跨块假峰；(ii) `B-only`（启用步进 $c_1^{(q)}$ 与 $P_{\perp,s}^{(q)}$，但通信退回 `Tang` $k_\nu=1$ 截断解）检验强目标 ICI 消伪对 WeakSINR 的贡献与通信残留误码地板；(iii) 检查全图盲搜 CFAR 检出率及 $N=64\to 512$ 时 Woodbury 内核线性扩展斜率。
⑤ 预期账本数字：QPSK `SER ≈ 0.05%–0.12%`（16-QAM 无内环畸变地板），`WeakSINR ≈ 24–27.5 dB`，全图 CFAR 零假峰稳定检出 $\Delta\ell=3,\Delta m=2.3$ 弱目标；单步 Woodbury-FFT 求逆复杂度 $O((KP_{\max}R)^2 + N_t K N\log N)$，预期 $N=64/128$ 耗时 `~8 / 18 ms`（较稠密 QP 提速 `20x–38x`，$N=512$ 下提速 `>80x`）。

### 草图 3：去斜优超强目标旁瓣环与光滑包络球面预编码
① 思路一句话：以全强目标旁瓣环（无弱目标真值先验）四阶加权积分旁瓣（WISL）为目标，经啁啾去斜二维 FFT 优超（MM）合成跨块互补抗 ICI 波形，并将 QPSK/16-QAM CI 约束化为 Moreau-Yosida 光滑包络以预条件共轭梯度配精确 KKT 球缩放联合求解。
② 为什么母方法 $F_N \to A$ 直套失灵（点名具体 AFDM 结构耦合）：OFDM 下的 `Li et al. TWC'25` WISL-MM 依赖纯 Toeplitz 时频移不变性，直接 $F_N \to A$ 搬运至 AFDM 后，$\Lambda_{c_1}$ 二次相位与 CPP 边值相移破坏了核的移不变 Toeplitz 结构，使 2D-FFT 快速优超失效；同时 `Tang TWC'26` 串接随机感知流会产生高随机距离-多普勒基底，而直接把硬 CI 不等式塞进四阶感知优化又会退化为不可扩的稠密 QCQP（$N=128$ 即达 $693\text{ ms}$）。
③ 最接近已知做法：`Li et al. TWC'25`（OFDM 四阶 WISL-MM 旁瓣整形）与广义半光滑/光顺罚函数 SLP；本方案推导出 AFDM 啁啾剪切坐标 $(\ell,\nu)\mapsto(2Nc_1\ell+\nu)$ 下的精确去斜-重调频 2D-FFT 紧致二次优超矩阵 $\mathbf{Q}_q^{(t)}$（$O(QN\log N)$ 隐式评估强目标旁瓣环四阶耦合，自动生成块间相干消伪调制），并在同一光滑无约束球流形上联合 Moreau 包络 $\frac{1}{2\mu}\|\Pi_{\mathcal{C}_{\text{CI}}^\circ}(\mathcal{H}(S[q])-\gamma d[q])\|_F^2$ 用 $c_1$ 仿射带预条件 CG 与一维解析 KKT 径向缩放精确落入 $\|S[q]\|_F^2\le P_{\text{blk}}$（$c_1=0$ 时去斜剪切映射与仿射带预条件结构退化）。
④ 最便宜 15 分钟检验（含 A-only / B-only）：对 $Q=8,16$、$N=64,128$ 跑因果闭环（仅利用第一阶段高门限检出的强峰 $(\hat{\theta}_s,\hat{\ell}_s,\hat{\nu}_s)$ 构建旁瓣环 $\Omega_{\text{SL}}$）：(i) `A-only`（关闭 WISL-MM 即 $\mathbf{Q}_q=0$，只运行 Moreau-PCG 球面 CI 预编码）验证无截断通信 SER 及雷达 WeakSINR 坍塌；(ii) `B-only`（保留去斜 2D-FFT WISL-MM，但通信降级为 `Li TWC'18` $F_N\to A$ 直套或 $k_\nu=1$ 投影）验证旁瓣环压低后单抽头终端 SER 仍严重恶化；(iii) 统计全图 CFAR 虚警率与跨 $N=64..512$ 的真实运行时间曲线。
⑤ 预期账本数字：QPSK `SER ≈ 0.05%–0.15%`（16-QAM 单抽头精确解调无地板），`WeakSINR ≈ 26–28 dB`（逼近正交补全上限 `27.86 dB` 且全图 CFAR 零盲搜漏警/假峰）；单次 MM-PCG 迭代 $O(Q N_t K P_{\max} N\log N)$，预期 $N=64/128$ 整块耗时 `~10 / 22 ms`（较稠密 QP `191/693 ms` 提速 `19x–31x`，跨 $N=64..512$ 均稳超 `10x`）。

---

## 会话 `g7-s2`（模型：`gemini-4-hydrogen-high`，耗时 `178.3s`，草图数 `3`）

### 草图 1：仿射条带预处理 ADMM 与互补啁啾零相关成型
① 思路一句话：用精确无截断时域-DAFT 算子 $\mathcal{H}_q = (\mathbf{I}_K \otimes A_q)\mathcal{H}_q^{\text{TD}}(\mathbf{I}_{N_t}\otimes A_q^H)$ 配合 $2Nc_1[q]\ell_p \pm k_{\text{pre}}$ 仿射条带循环带状 Cholesky 预处理分裂 ADMM（模块 A）求解 $\|S[q]\|_F^2 \le P_{\text{blk}}$ 下的 QPSK/16-QAM 统一单抽头 CI 线性不等式，并在 ADMM 近端步同步嵌入 FFT 加速的局部时延-多普勒零相关区惩罚 $\rho_s \sum_{\delta\in\Omega_{\text{ZCZ}}} \|\mathcal{R}_\delta(S[q])\|_F^2$ 与跨块跳变 $(c_1[q], c_2[q])$（模块 B），算力 $O(K N_t P_{\max} N\log N + N_t^2 L_z N\log N)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：$F_N \to A$ 直套假定信道在 DAFT 域格点对角解耦，但 $c_1 \neq 0$ 时每条路径经 $2Nc_1\ell_p$ 仿射移位跨格散射、CPP 相位 $e^{-j2\pi c_1(N^2+2Nn)}$ 引起边界相位扭转，且分数多普勒 $\nu_p$ 产生 $O(1/\Delta u)$ 拖尾的 Dirichlet 核 $\mathcal{D}_N(\cdot-\nu_p)$（$k_\nu=1$ 截断必然留下误码地板）；同时固定单啁啾会使 $+23\text{ dB}$ 强目标块内快时间 ICI 跨 $Q$ 块同相叠出 $\Delta\ell=3$ 假峰。
③ 最接近已知做法：Tang 等 TWC'26（仅 SISO 纯通信，$k_\nu=1$ 截断对偶单纯形 QP）与 Li 等 TWC'25（OFDM 局域 WISL 成型，未处理快时间 ICI 与 AFDM 啁啾跳变耦合）；本方案以未截断精确算子+条带预处理消除 SER 地板并借跨块 $(c_1[q],c_2[q])$ 跳频打散强目标 ICI 相干叠加。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64, Q=8, N_t=6, K=3, P_k=3, \text{SNR}=18\text{ dB}$ 且含 $+23\text{ dB}/0\text{ dB}$ 邻近目标 $(\Delta\ell=3,\Delta m=2.3)$ 下对比：`A-only`（去 ZCZ 正则与啁啾跳变）仅解出 $\text{SER}\approx 0.05\%$ 与 $\ge 15\times$ 提速，但 `WeakSINR` 停在 $\sim 6\text{--}8\text{ dB}$；`B-only`（在 Tang $k_\nu=1$ 截断 QP 上加 ZCZ 与跳变）保留 $\sim 8\%$ SER 地板与高耗时；另设 $c_1=0$ 消融验证条带预处理退化及强目标 ICI 旁瓣重现（单部件收益均 $<80\%$）。
⑤ 预期账本数字：破壁账预计 QPSK `SER` $0.05\text{--}0.12\%$、16-QAM `<0.5%`，`WeakSINR` $25.5\text{--}27.2\text{ dB}$（统一全图 CFAR $P_{fa}=10^{-4}$ 下 $P_d \ge 0.98$ 且零跨块假峰）；算力账预计单块耗时 $10\text{--}16\text{ ms}$ ($N=64$) / $22\text{--}34\text{ ms}$ ($N=128$)，相对精确稠密 QP ($191/693\text{ ms}$) 跨 $N=64..512$ 保持 $O(N\log N)$ 准线性扩展并提速 $12\text{--}45\times$。

### 草图 2：半光滑牛顿与 DPSS 连续多普勒零空间正交预编码
① 思路一句话：利用有效约束激活集的稀疏性构建对偶半光滑牛顿-共轭梯度（SSN-CG）求解器（模块 A），在牛顿线性步中用精确 $O(N\log N)$ AFDM 算子做矩阵向量乘、以沿 $2Nc_1[q]\ell_p$ 仿射条带解析求逆的 $K\times K$ 块 Woodbury 矩阵作预处理器；感知侧基于 Slepian 离散长球面序列（DPSS）将连续带限 $|\nu|\le\nu_{\max}$ 时延-多普勒模糊核压缩为秩 $R\approx 2\nu_{\max}+3$ 的正交补子空间基，并配合跨块 Golay-啁啾参考基迫使 CI 扰动与该 DPSS-啁啾子空间正交（模块 B），单块复杂度 $O(N_{\text{it}} K N_t L_z N\log N)$。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：当 $c_1 \neq 0$ 时，信道脉冲不再是频域逐格标量而变为多条斜率由 $2Nc_1\ell_p$ 决定的倾斜仿射条带叠加 Dirichlet 散射核，$F_N\to A$ 直套失去子载波正交性导致 `SER=56.46%`；且若感知正则不耦合 $c_1[q]$ 与连续多普勒核的倾斜时频结构，跨块随机数据扰动会将 $+23\text{ dB}$ 目标能量泄漏至所有慢时间多普勒格（将 `WeakSINR` 压至 $\sim 5\text{ dB}$）。
③ 最接近已知做法：Liu & Schober arXiv:2607.05119（依赖终端 $N\times N$ 块均衡且高斯感知流抬高随机旁瓣基底）与典型线性约束 CI-SLP；本方案以激活集二阶超线性 SSN-CG 替代稠密 QP，并用低秩 DPSS-啁啾子空间正交化替代显式 $O(N^2)$ 模糊函数约束。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在同阶段 A 配置 ($N=64/128, Q=8, +23\text{ dB}$ 掩蔽场景) 上跑 3 组对照：`A-only`（SSN-CG 无 DPSS-啁啾正交化）可复现 `0.043%` SER 与二阶快收敛，但 `WeakSINR` 仅 $5\text{--}8\text{ dB}$；`B-only`（$k_\nu=1$ 截断 QP 配 DPSS 正交化）受限于 Dirichlet 截断而保留 $\sim 7\text{--}12\%$ SER 地板且求解仍为立方阶；$c_1=0$ 消融验证倾斜 DPSS-啁啾基底坍缩为纯频域基底且 Woodbury 条带退化（双部件缺一收益均 $<80\%$）。
⑤ 预期账本数字：破壁账预计 QPSK `SER` $0.04\text{--}0.08\%$、16-QAM `<0.4%`，`WeakSINR` $26.0\text{--}27.5\text{ dB}$（CFAR 等虚警真目标定位零假峰）；算力账预计 SSN 5–8 步收敛，单块耗时 $8\text{--}14\text{ ms}$ ($N=64$) / $18\text{--}28\text{ ms}$ ($N=128$)，跨 $N=64..512$ 相对稠密 QP 提速 $15\text{--}60\times$。

### 草图 3：球面黎曼 L-BFGS 与双块互补互质啁啾跳变
① 思路一句话：在满足总功率球 $\|S[q]\|_F^2 \le P_{\text{blk}}$ 的黎曼流形上对平滑边界间隔 CI 损失直接执行原域 L-BFGS 优化，并借 AFDM CPP 相位 $e^{-j2\pi c_1(N^2+2Nn)}$ 消去后时域严格循环带状特性，以 $(\mathbf{I}_K\otimes\Lambda_{c_2}F_N)(\rho\mathbf{I}+\tilde{\mathbf{H}}_{\text{FIR}}\tilde{\mathbf{H}}_{\text{FIR}}^H)^{-1}(\mathbf{I}_K\otimes F_N^H\Lambda_{c_2}^H)$ 作 $O(K^3\ell_{\max}^2 N + KN\log N)$ 精确无迭代 Hessian 逆预处理器（模块 A）；感知侧以相邻双块 $(2r, 2r+1)$ 为耦合单位，联合最小化零阶与一阶慢时间泰勒矩互补旁瓣 $\|\mathbf{r}_{2r}(\Delta\ell)+\mathbf{r}_{2r+1}(\Delta\ell)\|_2^2 + \gamma\|\mathbf{r}'_{2r}(\Delta\ell)+\mathbf{r}'_{2r+1}(\Delta\ell)\|_2^2$ 并施以跨块互质啁啾斜率 $c_1[q]$ 跳变（模块 B）。
② 为什么母方法 F_N → A 直套失灵（点名具体 AFDM 结构耦合）：$F_N\to A$ 直套既忽略 CPP 相位补偿与 $2Nc_1\ell_p$ 移位构成的跨格耦合结构，也无法在单个块外抵消脉冲旁瓣；而不引入互质 $c_1[q]$ 跳变时，双块互补对在面对快时间多普勒 $\nu_{\text{strong}}\neq 0$ 时仍会在 DAFT 域同一 $2Nc_1\ell_{\text{strong}}$ 偏置脊线上相干残留。
③ 最接近已知做法：单块光滑边界 CI 球面优化与标准 Golay 互补序列对设计；本方案把原域功率球收缩与后 CPP 精确带状逆预处理结合，并将 Golay 互补从“固定序列”推广为随用户比特动态演化的“双块斜率互补+互质 $c_1[q]$ 抗 ICI 联合体”。
④ 最便宜 15 分钟检验（含 A-only / B-only）：在 $N=64/128, Q=8..16$ 场景下验证：`A-only`（仅原域球面 L-BFGS 无双块互补与 $c_1[q]$ 跳变）获 $<0.1\%$ SER 与 $>20\times$ 提速，但单块随机旁瓣使 `WeakSINR` 止步于 $\sim 5.5\text{--}8.5\text{ dB}$；`B-only`（仅双块互补+互质 $c_1[q]$ 配 $k_\nu=1$ 截断 QP 或 Liu'2607 单抽头接收）产生 $8\%\text{--}56\%$ SER 崩溃；$c_1[q]\equiv 0$ 消融验证互质抗 ICI 机制失效并在 $\Delta\ell=3$ 处重新触发强目标假峰（单部件收益均 $<80\%$）。
⑤ 预期账本数字：破壁账预计 QPSK `SER` $0.06\text{--}0.15\%$、16-QAM `<0.6%`，`WeakSINR` $24.8\text{--}26.8\text{ dB}$（双块互补压低 $\Delta m=2.3$ 处泄漏并消除跨块假峰）；算力账预计双块联合求解均摊单块耗时 $7\text{--}12\text{ ms}$ ($N=64$) / $16\text{--}26\text{ ms}$ ($N=128$)，跨 $N=64..512$ 稳定实现 $16\text{--}65\times$ 提速。

---
