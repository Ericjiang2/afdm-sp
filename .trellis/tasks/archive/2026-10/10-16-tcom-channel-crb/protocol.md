# F0+CSTATE 主线的信道估计下界参照：约束 ECRB 族（MCRB 为主）对比实际信道 NMSE（FROZEN 2026-10-16）

状态：**FROZEN（2026-10-16）**，在加入本行的 commit 中冻结。用户原话："全部采纳并冻结"（§8 的 E1–E5 按建议采纳）。
r1（344f9d10）经 Codex 单次审阅（`codex-derivation-review-20261016.md`：2 BLOCKER、4 MAJOR），r2（8da3504b）已全部采纳（§10）。
代码只用数值 gate 验证，不另做 Codex review（用户分工）。
任务：`.trellis/tasks/10-16-tcom-channel-crb`（父任务 09-22-tf-production-gap-audit）。
用户决定（2026-10-16）：新建本子任务；不用 Van Trees BCRB，参照界取 ECRB 族（按帧条件 CRB 再对信道律平均）。

## 0. 摘要

- **目的**：TCOM 三层参照里只缺信道估计误差的下界。本协议在 P1 的同一批帧上计算按帧条件下界，并与 F0 的导频估计、
  F0 最终估计、B = F0+CSTATE 最终 refit 的信道 NMSE 对比。
- **界**：主下界 MCRB（数据随机、已对数据平均的修正 CRB，D'Andrea 等 1994），在增益单位功率约束的流形上计算
  （约束 CRB）。辅助参照：DA-CRB（逐帧真数据已知）、PI-CRB（只用导频，数据当协方差冻结的高斯干扰）、
  GD-CRB（高斯数据模型的完整 Slepian–Bangs，子集）。全部在 genie 时延、P = 8 已知的条件下计算，再对帧平均（ECRB）。
- **主统计**：全部帧上 mean NMSE 与 mean bound 之比（dB），帧配对 bootstrap CI。译码成功帧上的结果只作描述。
- **成本**：约 5 core-hours（CPU），上限 10。

## 1. 参数化与适用范围

### 1.1 观测模型（与生产代码一致）

生成器（`experiments/tcom_reference_frame_20261015/gen_fixed.py`，P1 的场景 U、G：D1 + D2 + A1）给出 P = 8 条路径
(l_i, ν_i, g_i)：l_i 为整数采样时延（0..102），ν_i = k_real 为连续（分数）多普勒（单位：bin），g_i 复增益，Σ|g_i|² = 1。
接收机的物理模型 `physical.Channel`（`experiments/sp_afdm_frozen_20260920/src/physical.py`，与 deinlab reviewed 版逐字相同）：

  y = A T(θ) A^H x + w，  T(θ) = Σ_i g_i T_i，  (T_i s)[k] = φ_{l_i}[k] · e^{j2πkν_i/N} · s[(k − l_i) mod N]，

A 为 DAFT（酉矩阵），φ_l[k] = e^{j2πc_1(N² + 2N(k−l))}（k < l，CPP 相位），否则为 1。
x = x_p + d，x_p = √ρ · zc（DAFT 域），d = √(1−ρ) · QPSK(LDPC 码字)，w ~ CN(0, σ²I)（实、虚部方差各 σ²/2），
σ² = 10^{−SNR/10}。A1 下时延互异时 ‖H‖_F² = N。生成器的 y = noiseless + σ·noise，noiseless = H_phys(x_p + d)；Gate G1 验证
`Channel(真值)` 与 noiseless 一致。

数据统计：MCRB 只需 E d = 0 与 E dd^H = (1−ρ)I，且数据律不依赖 θ。对线性码 + 均匀信息比特 + Gray QPSK，这等价于
生成矩阵没有全零列、没有两列相同（对偶距离 ≥ 3 ⇒ 码字比特两两独立、均匀）。Gate G7 直接检查生成矩阵。

### 1.2 为什么不用 Van Trees BCRB

标准（不加权）Van Trees 公式要求参数空间上的先验密度在边界处为 0、先验 Fisher 信息有限，且有环境空间的 Lebesgue 密度。
本生成器在这一参数化下不满足：场景 G 的 ν_i = 1.62 cos θ_i 是 arcsine 密度，端点非正则；场景 U 的多普勒是折叠正态，
在 0 处密度不为 0，且还受截断（clip）和时延接受-拒绝的影响；归一化后的增益只在单位球面上有密度。
所以**标准 Van Trees 公式在此参数化下不适用**（不是说 Bayesian 界为 0）。对所有估计器都成立的 Bayesian 基准可以用
Weiss–Weinstein 类界（需按真实先验与信道损失重新表述），本协议不做，列为局限。
本协议用 ECRB：对每个实现 θ 计算条件 CRB，再对信道律平均。E_θ[MSE(θ)] ≥ E_θ[CRB(θ)] 只对在每个 θ 处（局部）无偏的
估计器成立。

### 1.3 未知参数、约束与 genie 条件

θ = (ν_1..ν_P, Re g_1..Re g_P, Im g_1..Im g_P) ∈ R^{3P}，P = 8，约束 c(θ) = Σ_i |g_i|² − 1 = 0（A1 下每帧精确成立）。
时延 l_i 与路径数 P 给定（genie）。忽略 genie 信息的估计器在 genie 实验里仍然可用，所以只要它在该固定时延子模型里满足
所需的局部无偏性，genie 界就约束它的风险；时延的离散性不影响这一论证。

**约束 CRB**（Gorman–Hero 1990；Stoica–Ng 1998）：取 U ∈ R^{3P×(3P−1)}，列为 ∇c(θ) = [0_P, 2Re g, 2Im g] 的正交补的标准正交基，
CRB_c(J) = U (U^T J U)^{-1} U^T。它对在约束流形上局部无偏的估计器成立，且 CRB_c ⪯ J^{-1}（更多估计器、更低的界）。
**主结果全部用约束版本**；无约束版本 J^{-1} 只写进 JSON。

## 2. 推导

导数算子（时域）：∂T/∂Re g_i = T_i，∂T/∂Im g_i = jT_i，∂T/∂ν_i = g_i D T_i，D = diag(j2πk/N)，k = 0..N−1（多普勒乘在输出样点上）。
DAFT 域 H = A T A^H，导数为 A(∂T)A^H。对输入 u，回归矩阵（显式构造）：

  B(u) = [R'(u) diag(g), R(u), j R(u)]，R(u) = `Channel(N,c1,c2,l,ν,1).regressors(u)`，R'(u) = 同上 `derivative=True`

（生产代码返回的是**单位增益**的列，ν 列必须再乘 g_i）。

### 2.1 Gram 矩阵 K（解析）

K_ab = tr((∂_a H)^H ∂_b H) = tr((∂_a T)^H ∂_b T)。l_i ≠ l_j 时 T_i^H T_j 是非恒等循环移位乘对角阵，对角线为 0，迹恰为 0；
l_i = l_j 时两者的 CPP 相位逐点相同、模为 1，相消（含 D 的权重）。记 Δ = ν_j − ν_i：
- tr(T_i^H T_j) = δ(l_i = l_j) Σ_k e^{j2πkΔ/N}
- tr((D T_i)^H T_j) = δ(l_i = l_j) Σ_k (−j2πk/N) e^{j2πkΔ/N}
- tr((D T_i)^H D T_j) = δ(l_i = l_j) Σ_k (2πk/N)² e^{j2πkΔ/N}
（直接求和，N = 1024，无可去奇点问题。）乘以参数系数（g_i^*、g_j、j 等）。‖H‖_F² = Σ_{ij} g_i^* g_j tr(T_i^H T_j)。

### 2.2 四种 FIM（复圆高斯，σ² = E|w_k|²）

- **DA（真数据已知，逐帧）**：J_DA(x) = (2/σ²) Re[B(x)^H B(x)]。
- **MCRB（主）**：J_M = E_d[J_DA(x_p + d)] = (2/σ²) Re[B(x_p)^H B(x_p) + (1−ρ) K]（只有导频–数据交叉项为 0，
  路径/参数之间的交叉项全部保留）。缺失信息恒等式给出 J_true ⪯ J_M，故真实 CRB ⪰ J_M^{-1}；约束版本同理。
  前提：数据律不依赖 θ、J 正定、期望存在。
- **PI（辅助参照）**：J_PI = 2 Re[B(x_p)^H C^{-1} B(x_p)]，C = (1−ρ) H H^H + σ²I 在评估点冻结。它是一个人工高斯族
  （协方差不随 θ 变）的精确 CRB，**对实际信道实验里的任何估计器（包括 F0）都没有一般的下界保证**；只作参照位置。
- **GD（辅助参照，子集）**：J_GD = J_PI + [tr(C^{-1} ∂_a C C^{-1} ∂_b C)]_{ab}（系数为 1），∂_a C = (1−ρ)(∂_a H H^H + H ∂_a H^H)。
  它是高斯数据模型的精确 CRB；与 QPSK 模型的 CRB 没有一般的大小关系。
- E_d[J_DA^{-1}] ⪰ J_M^{-1}（矩阵求逆凸）；但 DA 的平均只对"在每个已揭示数据下条件无偏"的估计器成立，所以 DA 只作描述。

### 2.3 信道矩阵层面的界

对 h(θ) = vec H(θ) 局部无偏的估计器，函数 CRB 给出精确的 E‖Ĥ − H‖_F² ≥ tr(G CRB G^H) = tr(CRB · Re K)
（G = ∂h/∂θ^T，G^H G = K，CRB 实对称）。注意 θ̂ 的局部无偏不推出非线性 H(θ̂) 的无偏，因此本界针对的是对 H 局部无偏的估计器。
NMSE 界：b = tr(CRB_c(J) Re K) / ‖H‖_F²。

**闭式恒等（gate G4）**：若 R_x 换成 I，则 J = (2/σ²) Re K，且 U^T Re K U 满秩时
b_c = (3P − 1)σ² / (2‖H‖_F²)、无约束 b = 3Pσ² / (2‖H‖_F²)（P = 8、‖H‖_F² = N 时 23σ²/(2N)；SNR 6 dB 约 −25.5 dB）。
MCRB 与它只差导频项的非白化修正。粗略量级：PI 参照 ≈ 3P((1−ρ) + σ²)/(2ρN)（6 dB：ρ .3 约 −14.3 dB，ρ .5 约 −17.5 dB）。
这些只是量级预期，不是判定。

**奇异情形**：若 cond(U^T J U) > 1e10（同时延近重合多普勒、零增益等），该帧记为 flagged，不进入界的均值，计数单独报告；
任何 (场景, ρ, SNR) 中 flagged > 1% 时停下报告用户，不用伪逆替代。

### 2.4 估计器的 NMSE（精确，不依赖接收机模型）

估计 (l̂_a, ν̂_a, ĝ_a)（任意条数、任意时延）与真值合并成一组路径 {c_a, l_a, ν_a}（真值系数取负号），
‖Ĥ − H‖_F² = Σ_{ab} c_a^* c_b tr(T_a^H T_b)（§2.1 同一公式）。NMSE = ‖Ĥ − H‖_F² / ‖H‖_F²。时延估错的路径自然计为误差。

## 3. 比较对象（接收机原样调用，只读取已有中间量）

| 估计 | 来源（`native_twofft.receive` / `run_validation._branch` 的输出） | 主对照 | 辅助 |
|---|---|---|---|
| F0-pilot（主） | 第 0 轮 `time_refine`（mu = 0，只用导频）：`r0_delays, r0_dopplers, r0_ce_gains` | MCRB | PI |
| F0-front（次） | `pilot_front` 的 40 个整数网格原子（另调一次，不影响解码） | MCRB | PI |
| F0-final | 第 1 轮检测器最终增益：`r1_delays, r1_dopplers, r1_gains`（`r1_ce_gains` 次） | MCRB | DA |
| B-final（主） | 触发时：`result.paths` + 检测器最终增益 `detector['gains']`（`result.gains` 次）；未触发时 = F0-final | MCRB | DA |

## 4. 设计

| 因素 | 取值 |
|---|---|
| 帧 | P1 的帧 0..499（同熵 2261fde3…、domain TCRF、同生成器与开关），信道/比特/噪声在 ρ、SNR 之间共享 |
| 场景 | U、G（P1 定义） |
| ρ | .3、.5 |
| SNR | 4.5, 5.0, ..., 8.0 dB |
| 臂 | F0（含 F0-front 的一次额外调用）、B（仅在 F0 失败时触发 CSTATE20） |
| 界 | MCRB、DA、PI：全部 16000 个 (场景, ρ, SNR, 帧)；GD：帧 0..99（3200 个） |

复用 P1 帧的理由：NMSE 可以逐帧对上已验收的 P1 FER 账本；本协议的结论是描述性的估计效率，不检验 B 对 F0 的增益。

## 5. 统计与标签（预注册）

- **主统计（无条件，全部帧）**：每个 (场景, ρ, SNR)，r = 10 log10(mean_f NMSE_f / mean_f b_f)，b 为约束 MCRB；
  帧配对 bootstrap（2000 次，同一组重抽帧同时用于分子和分母）95% CI [lo, hi]。flagged 帧从分子、分母同时去掉。
- **标签**（每个 SNR 点；两组预注册配对：F0-pilot 对 MCRB；B-final 对 MCRB）：
  - BELOW：hi < 0。按 CRB 的逆否命题，这说明该估计器在一组正概率的 θ 上不是局部无偏的；不另作机理解释；
  - EFFICIENT：不是 BELOW 且 hi ≤ 1 dB；NEAR：1 < hi ≤ 3 dB；GAP：hi > 3 dB。
- **论文措辞规则**："在 [a, b] dB 内距 MCRB X dB 以内" 只在该区间每个 SNR 点的 hi ≤ X 时才写；否则列出成立的 SNR 子区间。
  均值受粗差帧主导，卡片同时报告 NMSE > −5 dB 的帧比例。
- **只作描述（不贴标签，不作界的主张）**：
  - 译码成功帧上的同一比值（条件化改变了实验，失去 CRB 保证）；失败帧上的 NMSE 分布；
  - 逐帧比值 NMSE_f / b_f 的中位数（CRB 约束的是期望，不是单帧；有效无偏估计的单帧中位比值也可 < 1）；
  - F0-pilot 与 PI、GD 的位置；F0-final 与 DA；DA 与 MCRB、PI 与 GD 的差距；无约束版本；
  - 救援对信道的影响：B 触发的帧上配对差 10log10 NMSE(B-final) − 10log10 NMSE(F0-final) 的中位数与 CI、改善的帧比例。

## 6. Gate（数值恒等或蒙特卡洛核对；任一不过即停，报告用户）

MC 标准误统一用对 MC 抽样的 bootstrap（200 次）估计矩阵相对 Frobenius 误差的标准误。

- **G1 模型**：每场景 50 帧，‖noiseless − Channel(真值).apply(x_p + d)‖ / ‖noiseless‖ ≤ 1e-10；估计器取真值时 NMSE ≤ 1e-12；
  每帧 |Σ|g_i|² − 1| ≤ 1e-12。
- **G2 解析迹**：N = 64 随机小例（含同时延两条路径）与 3 个生产帧（N = 1024，稠密 H 用 `Channel.apply` 逐列作用于单位向量构造），
  §2.1 的 K、‖H‖_F² 和 §2.4 的 ‖Ĥ − H‖_F² 与稠密计算相对误差 ≤ 1e-9；R'(u) diag(g) 与中心差分的相对误差 ≤ 1e-6，
  且在步长 1e-5、1e-6、1e-7 下稳定（相互差 ≤ 1e-5）。
- **G3 Fisher 信息蒙特卡洛**（N = 64，P = 3，含一对同时延路径，20000 次）：
  (a) DA：对数似然中心差分得到的 score 的样本均值 ≈ 0（每分量 |均值| ≤ 4 SE），样本协方差 vs J_DA（全矩阵、含各块）；
  (b) MCRB：随机码字数据下 J_DA 的样本均值 vs J_M；
  (c) GD：高斯数据模型精确对数似然（−ln det C − (y−μ)^H C^{-1}(y−μ)）差分 score 的样本协方差 vs J_GD；
  (d) 只有协方差项的 GD 情形（x_p = 0）同样核对；
  (e) 噪声实、虚部的样本方差各为 σ²/2（相对误差 ≤ 3%）。
  (a)–(d) 的相对 Frobenius 误差 ≤ max(3 × MC SE, 3%)。
- **G4 闭式恒等**：R_x 换成 I 时 b_c = (3P−1)σ²/(2‖H‖_F²)、b = 3Pσ²/(2‖H‖_F²)，相对误差 ≤ 1e-10（生产帧与小例各测）。
  （G4 与实现共用 K，故只防代数错误，不单独防因子 2；因子 2 由 G3、G5、G5b 把关。）
- **G5 可达性**：N = 64，SNR 30 dB，数据已知，从真值起做 Gauss–Newton 的 ML，5000 次：θ 的经验 MSE 迹与无约束 DA-CRB 迹之比、
  H 层 NMSE 与 H 层 DA 界之比都在 [0.9, 1.1]。
- **G5b 独立锚点**：单路径、已知多普勒、单复增益的 LS：E|ĝ − g|² = σ²/‖b‖²（MC 20000 次，相对误差 ≤ 3%），
  并与实现给出的 2×2 实 FIM 求逆后的迹一致（≤ 1e-10）。
- **G6 复现**：重跑的 F0、B 在全部 16000 个格上的 `decoded_sha256` 与 P1 账本逐一相同（不同即停）。
- **G7 数据统计**：LDPC 生成矩阵无全零列、无两列相同（对偶距离 ≥ 3），并在 2000 个码字上核对 E dd^H 的经验值。
- **G8 奇异**：试跑的 20 帧中 flagged 帧比例；任何格超过 1% 即停（§2.3）。

## 7. 执行顺序、成本与 commit 节点

1. 协议冻结 commit（含 FROZEN 行）。
2. 实现 `experiments/tcom_channel_crb_20261016/{crb.py, crb_gates.py, crb_driver.py, crb_agg.py}`；本地跑 G2–G5b、G7，
   deinlab 跑 G1、G6、G8 的小样本（20 帧）和单格计时；commit "before CRB run"（含 gate 输出与计时）。
3. deinlab 正式运行（tmux `g_crb`，≤ 30 分片单线程，整机留 ≥ 16 核），rows 留远程（gzip + md5）；
   `crb_results.json` 带 `_argv`、`_config`，回传小文件；commit "after CRB run"。
4. draft 卡 + STATE/index 更新，commit。
成本预估：F0 + B ≈ .35 s/格，MCRB/DA/PI ≈ .1 s/格 → 16000 格约 2 core-hours；GD 子集约 3 s/格 → 约 2.7 core-hours。
上限 10 core-hours；若计时显示 GD 超支，把 GD 帧数减到 50，并在开跑前记录。

## 8. 待用户决定

| ID | 决定 | 建议 |
|---|---|---|
| E1 | 帧：复用 P1 帧 0..499，还是新熵 | 复用；可逐帧对上 P1 账本，结论是描述性的 |
| E2 | 标签阈值 1 dB / 3 dB，主统计为全部帧的均值比（§5） | 采用 |
| E3 | GD 只在帧 0..99 报告 | 采用（约 2.7 core-hours） |
| E4 | "最终估计"取检测器最终增益（`r1_gains` / `detector['gains']`），CE 增益作次要 | 采用；它是检测器最后实际使用的信道 |
| E5 | 主界取增益单位功率约束下的约束 MCRB（Codex BLOCKER 5），无约束版只进 JSON | 采用；约束版对更多估计器成立，差约 10log10(23/24) ≈ −0.18 dB |

## 9. 局限（写进卡片）

- genie 时延与已知 P；界只针对 ν、g。时延错误在 NMSE 里计为误差，但界里没有对应项。
- CRB 只约束对 H（局部）无偏的估计器；ECRB 是条件界的平均，不是对所有估计器成立的 Bayesian 界（那需要 Weiss–Weinstein 类界）。
- PI、GD 用高斯数据替代 QPSK，都不是实际实验的下界；只有 MCRB（约束版）对实际模型是严格下界。
- 一个调制、一种码、N = 1024、单天线、σ² 已知；信道律同 P1。

## 10. r1 → r2 修订对照（Codex 单次审阅）

| Codex | 级别 | 采纳 |
|---|---|---|
| 1 回归列不含 g | OK + fix | §2 显式 B(u) = [R' diag(g), R, jR] |
| 3 数据律前提 | OK + fix | §1.1 写明前提，G7 检查生成矩阵与 E dd^H |
| 4 PI 的解释 | MAJOR | PI 改为辅助参照，无下界保证；主对照一律用 MCRB |
| 5 单位功率约束 | BLOCKER | §1.3 约束 CRB（U(U^TJU)^{-1}U^T），G4 加 (3P−1) 恒等，决定 E5 |
| 6 函数无偏与奇异 | MAJOR | §2.3 改为函数 CRB 的精确表述；奇异帧 flag + 1% 停止规则（G8） |
| 7 Van Trees 措辞 | MAJOR | §1.2 改为"标准公式在此参数化下不适用"，WWB 列为局限 |
| 8 DA 平均的条件无偏 | OK + fix | §2.2 写明，DA 只作描述 |
| 9 中位数比值与条件化 | BLOCKER | §5 主统计改为全部帧均值比 + 配对 bootstrap；中位数、成功帧只作描述；BELOW 只作逆否命题解释 |
| 10 gate 锚点 | MAJOR | 加 G5b、G3(d)(e)、score 均值、步长稳定性、MC SE 定义；G2 逐列构造稠密 H |

r1 的推导常数另由本会话 scratch 数值检查确认（`scratch_derivation_check.py`，N = 64：导数差分 7e-11、解析 K 4e-11、
闭式恒等精确、DA score 协方差 MC 2.3%、已知数据 GN-ML 的 θ MSE / CRB = 1.003）。

## 11. 协议修订（冻结后、任何正式数据之前）

- **A1（2026-10-16，用户决定"修订 A1：精确 R_d"；G7 失败之后、正式运行之前）编码数据的精确二阶统计。**
  G7 发现冻结 LDPC 生成矩阵有 3 对相同的列（编码比特 66/932、878/1566、2046/2047；8b6eef84）。按 `qpsk_map`
  （前 1024 比特为 I、后 1024 比特为 Q），它们分别使符号对 (66, 932)、(878, 542)、(1022, 1023) 相关：
  E[d_s d_t^*] = (1−ρ)/2 · u(i) conj(u(j))（u = 1 表示 I 分量，u = j 表示 Q 分量），其余非对角项为 0，对角项仍为 1−ρ。
  （8b6eef84 的 commit 信息说实际码字下 J_M 与 iid 版差 0.18%，这一归因有误：修订后的 G3b 显示精确 R_d 与 iid 的 J_M 只差
  5.8e-5，0.18% 是 2000 个码字平均的 MC 噪声，对两种 J_M 几乎相同。）修订：
  1. MCRB 改用由生成矩阵算出的精确 R_d = E dd^H：J_M = (2/σ²) Re[B(x_p)^H B(x_p) + (1−ρ)K + Σ_{s≠t} R_d[t,s] B(e_s)^H B(e_t)]
     （E[B(d)^H B(d)] = Σ_{s,t} E[d_s^* d_t] B(e_s)^H B(e_t)，对角部分即 (1−ρ)K）。由此 MCRB 对实际数据律仍是严格的。
     PI、GD 的高斯替代仍用 (1−ρ)I（它们本来就是辅助参照）。
  2. G7 改为：(a) 由生成矩阵算出的每个非零非对角项与 2000 个码字的经验值相差 ≤ 4 个 MC 标准差；
     (b) 其余非对角项经验值的 rms 与 MC 标准差 (1−ρ)/√2000 之比在 [0.95, 1.05]；(c) 经验对角项均值 = 1−ρ（≤ 1e-12）。
  3. G3b（实际码字）改为对精确 J_M 核对，判定规则不变；另报对 iid J_M 的偏差。
  判定规则（§5）与其余 gate 不变。
- **实现说明 I1（2026-10-16，用户决定"加 I1 后开跑"；看过 20 帧 smoke 之后、正式运行之前；只加描述量，不改任何配对、标签或判定）。**
  smoke 显示 F0-pilot（`r0_ce_gains`）的 NMSE 在所有 SNR 上恒为约 −3 dB（ρ .3）/ −6 dB（ρ .5）：`time_refine` 在 mu = 0 时
  解 (BᴴB + Γ + σ²I)h = Bᴴy，Γ ≈ 数据方差的投影，增益被按设计收缩约 p/(p + v)（内部约定 p = ρ/(2(1−ρ))、v = .5），
  所以它是有偏的中间量。预注册配对"F0-pilot 对 MCRB"保持不变（标签照报）。新增两项只报告的描述量：
  1. **F0-pilot-LS**：在 F0 导频阶段的几何（`r0_delays, r0_dopplers`）上做只用导频的无偏 LS 增益
     ĝ = argmin ‖y − R(pilot) g‖²（数据当零均值噪声）；与 MCRB、PI 的比值只作描述。
  2. **漏检时延能量占比**：真值路径中时延不在估计时延集合里的那部分 ‖H_miss‖_F² / ‖H‖_F²（§2.1 的精确迹），对每个估计器报告均值。
  卡片须写明这两项是看过 smoke 后加入的。
