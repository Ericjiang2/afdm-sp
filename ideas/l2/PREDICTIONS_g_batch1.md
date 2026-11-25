# L2 Runner `g` 第 1 批：跑前判据与预测（2026-11-22 02:20 写，正式运行前冻结；runner `g`，`gemini-4-carbon`）

本文件仅装 runner `g` 第 1 次筛选选入第 1 批 L2 的三张卡：`I-20261122-g03`、`I-20261122-g01`、`I-20261122-g05`。
脚本：`ideas/l2/g_l2_batch1.py`，输出目录：`ideas/l2/out_g1/`（`deinlab` 路径 `/data/guoyikun/00inbox/AFDM-channel-estimation/ideas/l2/out_g1/`）。所有校准集与留出评估集种子严格分离，未修改任何冻结接收机代码。

---

## 1. 卡 `I-20261122-g03`（`explore`：1 比特接收强直达径下波形过零密度对偶与条件 Probit 得分）

### 设定与对照臂（含 `gpt-6.2-sol` 审查点名的两条关键基线）
- **观测模型**：复基带 1 比特零门限量化 $r_n = \mathrm{sign}(\Re y_n) + j\,\mathrm{sign}(\Im y_n)$，强直达径位于 $(\ell_0=0,\nu_0=0)$、随机相位 $g_0=e^{j\phi_0}$，输入直达径干噪比 $\mathrm{CNR} = 1/\sigma^2 \in \{15, 20, 25, 30, 35\}\text{ dB}$（每实维噪声标准差 $\sigma_0=\sigma/\sqrt{2}$）。
- **连续参数弱回波**：时延 $\tau_w \sim \mathrm{Unif}[8.0, 60.0]$（精确带限 Dirichlet 分数时延插值核，含跨抽头 sinc 泄漏），多普勒 $\nu_w \sim \mathrm{Unif}([-2.5,-0.6]\cup[0.6,2.5])\text{ bin}$，随机相位，弱强径功率比 $\mathrm{WSR} = 20\log_{10}|g_w/g_0| \in \{-18, -22, -26, -30, -34\}\text{ dB}$（主网格 $N=1024$；另测 $N=4096, \mathrm{CNR}=30\text{ dB}, \mathrm{WSR}\in\{-26,-30,-34,-38\}\text{ dB}$ 检验帧长标度）。
- **全平面恒虚警标定与留出集**：搜索平面为 $\ell\in\{4,\dots,64\}\times \nu\in\{-3.0,-2.75,\dots,+3.0\}$（共 $61\times 25=1525$ 格）。
  - **独立空假设标定集**：每个 `(N, CNR, arm)` 独立跑 `400` 帧纯强径+热噪声（`seeds 10000..10399`），取全图最大值第 99 分位数标定全图虚警率 $P_{\mathrm{FA}}=10^{-2}$。
  - **独立留出评估集**：`300` 帧配对样本（`seeds 20000..20299`），6 条臂共享同一信息比特、直达径相位、弱目标连续几何与热噪声；当且仅当全图峰值越过该臂 $P_{\mathrm{FA}}=10^{-2}$ 门限且峰值位置满足 $|\hat{\ell}-\tau_w|\le 1.0$ 且 $|\hat{\nu}-\nu_w|\le 0.5\text{ bin}$ 记为真命中（`Hit = 1`）。
- **六条配对对照臂**：
  1. `sc_qpsk_probit`：未扰码恒模 QPSK 单载波（0 dB PAPR）+ 二维 Newton 盲估 $\hat{\eta}_0$ + 精确逆 Mills 比 Probit 得分；
  2. `sc_cphase_probit`（Sol 点名基线 1）：带已知逐样点连续随机相位扰码的恒模单载波 $|x_n|\equiv 1$（0 dB 离散 PAPR，反正弦过零密度 $p_U(0)=1/\pi$）+ 同一盲估 Probit 得分；
  3. `afdm_bussgang`：`AFDM` + 标准 Bussgang 线性强径最小二乘对消；
  4. `afdm_cmean`（Sol 点名基线 2）：`AFDM` + 盲估 $\hat{\eta}_0$ + 未加权精确条件均值对消 $e_n = r_n - [(2\Phi(\Re\hat{u}_n)-1)+j(2\Phi(\Im\hat{u}_n)-1)]$（分离奇次谐波零化与逆 Mills 精度加权）；
  5. `afdm_probit`：`AFDM` + 盲估 $\hat{\eta}_0$ + 精确逆 Mills 比 Probit 得分（已知发射波形主方案）；
  6. `afdm_semiblind_probit`：通信视距半盲臂——`AFDM` 承载真实 `(3,6)` 率 $1/2$ LDPC 码字（`ctx.code`，含 4% 已知导频符号估初相），接收端先直接从 1 比特观测 $\mathbf{r}$ 经 `ctx.native.decoder_messages` 译码重构强径波形 $\hat{\mathbf{x}}$，再做盲估 Probit 弱径检测。

### 实现门与主判据
- **实现门**：(1) 在 `200` 帧全新空假设检验集（`seeds 10400..10599`）上，`afdm_probit` 与 `afdm_bussgang` 的实测全图虚警率落在 `[0.00, 0.035]`；(2) `CNR = 25 dB` 下 `afdm_semiblind_probit` 的强径 LDPC 译码成功率 $\ge 98\%$。
- **主判据**（核心池化区：`CNR in {20, 25, 30} dB` $\times$ `WSR in {-22, -26, -30} dB`，共 `2700` 个配对帧格；按帧 2000 次自助采样算 95% CI）：
  - **通过（PASS）**：`afdm_probit` 相对 `afdm_bussgang` 的池化真命中率提升点估计 $\ge +25\text{ pp}$ 且 95% CI 下界 $> +20\text{ pp}$，同时在 `CNR = 30 dB` 下达到 50% 真命中率所需的最小弱强比 `MDR_50` 改善 $\ge 4.0\text{ dB}$，且 `afdm_semiblind_probit` 保留 `afdm_probit` 池化真命中率的 $\ge 90\%$。*机制归因收紧规则*：同步报告 `afdm_probit - sc_cphase_probit` 与 `afdm_probit - afdm_cmean`；若 `sc_cphase_probit` 解除离散 QPSK 失明并落在 `afdm_probit` 下方 `1.5–3.5 dB`（对应反正弦对高斯 $p_U(0)$ 比值 $\sqrt{\pi}$）、或 `afdm_cmean` 与 `afdm_probit` 差距 `< 0.5 dB`，放行前须按实测将卡片核心论断精确收紧为“门限过零密度 $p_U(0)$ 与条件奇次谐波零化（高斯多载波相对连续相位恒模仍赢约 2.5 dB，离散星座恒模指数失明）”。
  - **淘汰（KILL）**：池化 `Hit(afdm_probit) - Hit(afdm_bussgang)` 点估计 $< +15\text{ pp}$，或 `CNR = 30 dB` 处 `MDR_50` 改善 $< 3.0\text{ dB}$，或半盲强径译码成功率 $< 80\%$。
- **跑前预测**：`PASS = 0.75, KILL = 0.15, UNDETERMINED = 0.10`；预计 `CNR=30 dB` 处 `MDR_50`：`afdm_bussgang` 约 `-21 dB`，`sc_qpsk_probit` 失效（`> -18 dB`），`sc_cphase_probit` 约 `-26.5 dB`，`afdm_cmean` 约 `-28.8 dB`，`afdm_probit` 与 `afdm_semiblind_probit` 约 `-29.0 dB`。

---

## 2. 卡 `I-20261122-g01`（`adjacent`：短 CP 叠加导频 OFDM 感知跨块假峰与块相位编码 vs 连续模板投影）

### 设定与对照臂
- 参数：$f_s=16\text{ kHz}$，$M=16$ 连续块，$K=64, C=16$，强径每样点信噪比 $4.5\text{ dB}$，扫 $\rho\in\{0.20, 0.30, 0.40\}$，两类强径越界时延模式 `d_clean`（$\ell_s=28, d=12$）与 `d_gen`（$\ell_s\in\{21,22,23,25,26,27,29,30,31\}$ 非整除偏移 + 随机分数多普勒 $\nu_s\in[-20,20]\text{ Hz}$），两档多普勒搜索半宽 $F\in\{31.25\text{ Hz}, 45.0\text{ Hz}\}$，弱径位于前缀内（一半落在假峰邻域 $\ell_w=d$、一半在 $\{4,\dots,15\}$ 均匀抽样）且 $\mathrm{WSR}\in\{-14,-16,-18,-20\}\text{ dB}$。
- **独立标定与留出**：每个 `(rho, delay_mode, F, arm)` 用 `500` 帧纯强径标定前缀内搜索盒 1% 全图虚警门限（`seeds 30000..30499`），在 `400` 帧独立留出集（`seeds 31000..31399`）上配对测试四臂：(1) `rep_naive`（重复导频循环相关）；(2) `rep_1sic`（重复导频 + 估强径一次物理导频回波相减）；(3) `rep_joint_lin`（Sol 点名基线：重复导频 + 跨块连续导频线性卷积模板正交投影消元）；(4) `phase_code`（发射端 $q_m=(-1)^{m(m+1)/2}$ 整块相位编码）。

### 实现门与主判据
- **实现门**：无噪声单帧校验下，`rep_naive` 在 $\ell_s=28,\nu_s=0$ 处 $d=12$ 假峰幅度与强径比值实测对上 $12/64 = 0.1875$（误差 $<10^{-3}$），`phase_code` 原位假峰 $<10^{-10}$。
- **主判据**（主工况池：$F=31.25\text{ Hz}, \rho\in\{0.20,0.30\}, \mathrm{WSR}\in\{-16,-18\}\text{ dB}$，含 `d_clean` 与 `d_gen`）：
  - **通过（PASS）**：`phase_code` 的真命中率同时高于 `rep_1sic` 与 `rep_joint_lin`，且配对差 `Hit(phase_code) - max(Hit(rep_1sic), Hit(rep_joint_lin))` 的 95% CI 上界 $\ge +10.0\text{ pp}$、下界 $> +3.0\text{ pp}$。
  - **淘汰（KILL）**：上述配对差 95% CI 上界 $< +10.0\text{ pp}$（接收端跨块连续导频模板已消除重复导频假峰，无需改发射端波形）。
- **跑前预测**：`PASS = 0.30, KILL = 0.55, UNDETERMINED = 0.15`（预计 `rep_naive` 因假峰抬高 CFAR 门限而严重漏检，但 `rep_joint_lin` 凭高相干导频信噪比能消掉绝大部分跨块导频假峰，可能吃掉发射端相位编码增益）。

---

## 3. 卡 `I-20261122-g05`（`core`：双水听器 $M=2$ 精确带状 Woodbury 半盲 EM 对比 `c16` 导频合并与短时分导频）

### 设定与对照臂
- **帧集**：全新双边多普勒场景 `G` 帧 `49000..49149`（`150` 帧，此前从未被任何实验读取；`smoke` 单独用帧 `48999`），生产配置 `ctx.system`（$N=1024, f_s=16\text{ kHz}, 2Nc_1=5, P=8$）。
- **双水听器信道**：阵元 1 取原帧复增益 $\mathbf{g}_1$，阵元 2 按复高斯相关系数 $\varrho\in\{0.0, 0.5, 0.85\}$ 生成同逐径功率期望的 $\mathbf{g}_2 = \varrho\mathbf{g}_1 + \sqrt{1-\varrho^2}\mathbf{g}_\perp$（帧总径功率逐阵元归一）。
- **两部分实验与五条配对臂**：
  - **Part A（真时延第 0 轮多普勒功率加权未截尾 MAE）**：固定每阵元 $\mathrm{SNR}=4.0\text{ dB}$，扫 $\rho\in\{0.03, 0.05, 0.10\} \times \varrho\in\{0.0, 0.5, 0.85\}$，另加一组“总接收功率拉齐单通道 4 dB（即每阵元 $\mathrm{SNR}=1.0\text{ dB}, \rho=0.05, \varrho=0.0$）”检验纯子空间消数据增益。
  - **Part B（未知时延盲捕获 + 双阵元 LMMSE-LDPC 10 轮迭代接收误帧率 FER）**：$\varrho=0.0$，扫每阵元 $\mathrm{SNR}\in\{2.0, 3.0, 4.0\}\text{ dB}$（02:35 正式运行前基于单帧 `48999` 冒烟读数将瀑布窗从 `{1,2,3}` 移至 `{2,3,4} dB` 以避开 `1 dB` 全败天花板，评估帧 `49000..49149` 零接触；同时将全部未知时延臂统一升级为 8 步双通道正交匹配追踪 S-OMP 以确保 `c16` 基线绝对公平），配对对比 $\rho=0.05$ 下的五条臂及常规高导频 $\rho=0.25$ 下的 `c16_pilot_varpro`！
  - **五条配对臂**：(1) `c16_pilot_varpro`（双通道联合纯导频 VarPro）；(2) `short_tdm_joint`（Sol 点名基线：同帧长同总能量预算下，将 $\rho N$ 导频能量集中为帧首尾两段短时分已知标记联合估多普勒与增益，数据段零叠加导频）；(3) `alt_notrace`（漏掉 $\mathbf{S}^{-1}$ 迹修正的朴素交替消元，负面对照）；(4) `woodbury_em`（含 $\sigma^2\mathbf{S}^{-1}$ 全部 29 条循环对角精确迹修正的时域 Woodbury EM，未知时延下含 1 次正交补/残差时延补捕）；(5) `true_H`（真信道双阵元 LMMSE-LDPC 检测上限，分离估计损失与检测损失）。

### 实现门与主判据
- **实现门**：(1) 帧 `48999` 上时域算子与 `physical.Channel.apply` 相对误差 `< 1e-12`；(2) `true_H` 误帧数随信噪比单调不增。
- **主判据**：
  - **通过（PASS）**：(1) Part A 中 $M=2, \rho=0.05, \mathrm{SNR}_{\mathrm{elem}}=4.0\text{ dB}$ 在 $\varrho=0.0$ 与 $\varrho=0.5$ 下，`woodbury_em` 的功率加权多普勒 MAE 点估计 $\le 0.040\text{ bin}$（95% CI 上界 $\le 0.045\text{ bin}$），且比 `c16_pilot_varpro` 和 `short_tdm_joint` 均低 $\ge 2.0$ 倍；并且 (2) Part B 未知时延编码接收中（3 档 SNR 合并 450 帧次），$\rho=0.05$ 的 `woodbury_em` 总错帧数显著低于同 $\rho=0.05$ 的 `c16_pilot_varpro` 与 `short_tdm_joint`（配对差 95% CI 下界 $> 0$），且相对常规高导频 $\rho=0.25$ 的 `c16_pilot_varpro` 兑现显著净误帧优势（配对差 95% CI 下界 $> +10$ 帧次，或折合 $\ge 0.4\text{ dB}$）。
  - **淘汰（KILL）**：Part A 中 $\rho=0.05, \varrho=0.0, 4.0\text{ dB}$ 下 `woodbury_em` 多普勒 MAE $> 0.045\text{ bin}$，或 Part B 未知时延编码误帧率未显著优于 `short_tdm_joint` 或 $\rho=0.25$ 的 `c16_pilot_varpro`。
- **跑前预测**：`PASS = 0.60, KILL = 0.25, UNDETERMINED = 0.15`；预计 $\rho=0.05, \varrho=0.0, 4\text{ dB}$ 真时延 MAE：`c16_pilot_varpro` 约 `.095 bin`，`short_tdm_joint` 因 26 点短窗多径数据串扰与整周错判 $> .12\text{ bin}$，`alt_notrace` 约 `.11\text{ bin}`，`woodbury_em` 约 `.028–.036\text{ bin}`（$\varrho=0.85$ 退化至 `.055\text{ bin}`）。
