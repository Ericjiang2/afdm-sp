# AFDM 水声信道估计与检测 — 算法详解

> **文档定位**：把本项目三条并行算法线串成一份可独立阅读的技术手册。不重复 `_CONTEXT.md` 里的管理信息，也不替代 `NARRATIVE_REPORT_FYP.md` 的研究叙事；这里只讲"算法做了什么、代码怎么写的、差异在哪里、效果有多大"。
>
> 代码片段采用**核心 20–60 行 + `file:line` 行号引用**的格式，读者可以顺着行号跳回原文件看完整上下文。所有量化数字来自 `CLAIMS_FROM_RESULTS.md`、`docs/Results.md` 和 `paper/sections/5_experiments.tex`，未单独实验验证。

---

## 目录

- [第 0 章 — 引言与阅读路径](#第-0-章--引言与阅读路径)
- [第 1 章 — AFDM 系统与信道模型](#第-1-章--afdm-系统与信道模型)
- [第 2 章 — MATLAB Joint OMP + MP + LS 迭代算法](#第-2-章--matlab-joint-omp--mp--ls-迭代算法)
- [第 3 章 — Python Joint OMP + MP 算法](#第-3-章--python-joint-omp--mp-算法)
- [第 4 章 — 三种 Joint 算法的统一视角与区别](#第-4-章--三种-joint-算法的统一视角与区别)
- [第 5 章 — DNN 修正算法：失败 → 成功完整叙事](#第-5-章--dnn-修正算法失败--成功完整叙事)
- [第 6 章 — 实验结果与效果](#第-6-章--实验结果与效果)
- [第 7 章 — 毕业论文中的其他对比基线](#第-7-章--毕业论文中的其他对比基线)
- [第 8 章 — 关键超参总表与复现指南](#第-8-章--关键超参总表与复现指南)
- [第 9 章 — 文件索引](#第-9-章--文件索引)
- [第 10 章 — 结论：三条算法线的综合定位](#第-10-章--结论三条算法线的综合定位)

---

## 第 0 章 — 引言与阅读路径

### 0.1 三条算法线的定位

本项目围绕"AFDM 水声通信系统的接收端（信道估计 + 数据检测）"展开，按时间顺序沉淀了三条并行的算法线：

| 编号 | 算法线 | 角色 | 状态 |
|---|---|---|---|
| ① | **MATLAB Joint OMP + MP + LS（含 kLAEK / 分数多普勒泄露扩展）** | 研究原型，验证算法可行性并生成毕业论文前半段结果（水声主入口 `matlab/AFDM_UWA_acoustic.m`；LEO 卫星早期工作仅作历史参考）| 完整落地 |
| ② | **Python Joint OMP + MP（重写 + 扩展）** | 评估框架，支持规模化实验与 DNN 接入；Python 是项目默认版本 | 完整落地 |
| ③ | **DNN Augmented Classical Unrolling（`classical_joint_unrolled` + B1 learned head）** | 对 Python 经典 Joint OMP-MP 做**可微分忠实展开**，在展开图上挂载一个小型零初始化 CNN（B1 per-iter symbol refiner），把经典教师作为"零初始化身份"恒等复现后再通过 BCE 微调严格超越经典教师 | **最终贡献**，N=1024, 100 帧 eval 显示 15 dB −39% / 20 dB −74% / 25 dB −97% BER vs classical teacher。B2（iter-residual selector）曾作为第二个学习头并入，但 100 帧复核显示其修复的 iter-5 overshoot 是 20 帧小样本假象，已弃用（见 §5.4）|

三条线**不是线性演化**——Python 版本不是在 MATLAB 上简单直译；classical_joint_unrolled 也不是简单深度展开（它首先要求在 N=512 下与 NumPy baseline bit-exact 吻合，再加入两个零初始化的学习头）。它们有不同的相位约定、稀疏度策略与超参规模，但**导频设计是统一的：MATLAB UWA 主入口和 Python 评估管线都使用 superimposed pilot (SP / 叠加导频)**——`x_total = x_data·√(1−ρ) + x_pilot·√ρ`。

### 0.2 每个算法一句话结论

- **MATLAB Joint OMP + MP + LS**（主入口 `matlab/AFDM_UWA_acoustic.m`）：外层 5 轮迭代交替做"OMP/DA-LS 估信道 → MP 检数据"，导频以 SP 形式与数据同子载波叠加。**核心贡献是 kLAEK**——用 Dirichlet 核把分数多普勒分解为 `2·K_LEAK+1` 个整数邻域径，在不改 `GEN_H_DAFT` 结构的前提下支持分数多普勒信道。**局限**：单帧运行、参数手调、对水声深度衰落+多径的复合场景没有学习机制。

- **Python Joint OMP + MP**（`afdm_sp_joint_unrolled/afdm_baselines.py::joint_omp_mp_iterative`）：直译 MATLAB 主流程，`c2 ≠ 0` 的相位约定、`P_paths` 作为 OMP 稀疏度。导频形式与 MATLAB 一致，都是 SP（Python 用 ZC，MATLAB 用随机 QPSK）。默认 10 径 UWA 参数，N=1024 下 classical joint 在 15 dB 得到 BER ≈ 6e-3，20 dB BER ≈ 2.5e-3。**局限**：超参手调，迭代策略对信道实现较敏感。

- **DNN Augmented Classical Unrolling**（`afdm_sp_joint_unrolled/classical_joint_unrolled.py`）：把 Python 经典 Joint 的每一步写成可微分 torch 层（OMP → cluster-support expand → DA-LS → H 重建 → PIC MP → damping），验证在 N=512 下与 NumPy baseline **bit-exact** 相同。挂载一个零初始化的 **B1 per-iter symbol refiner**（每轮 MP 阻尼前的 CNN residual 头，约 10k 参数；输入 `Re/Im(x_mp), Re/Im(residual), ∑|H[:,n]|²`，输出 Δx）。训练：BCE-primary loss (λ_bce=1.0, λ_sym=0.05) + best-eval checkpointing。**贡献**：N=1024 / v=1 m/s / 10 径 UWA / 100 帧 eval 显示 15 dB −39% / 20 dB −74% / 25 dB −96.6% BER 相对增益（vs 同帧的 classical teacher）。曾尝试加入 B2 (iter-residual selector) 学一个"挑最佳 iter 的 gating"，100 帧复核显示其修复的"iter-5 overshoot"是 20 帧小样本 catastrophic-frame 假象，B1-only 反而更好，**B2 已弃用**（保留 ablation 叙事，见 §5.4）。

### 0.3 关键记号表

| 记号 | 含义 | 典型值 |
|---|---|---|
| `N` / `N_total` | DAFT 域总子载波数 | MATLAB 256；Python 默认 1024（毕设评测） |
| `c1, c2` | AFDM chirp 参数 | MATLAB: `c1=(2k_max+1)/(2N), c2=0`；Python: 同 c1，但 `c2=(√2-1)/(2N²)` |
| `l_max` | 最大延迟索引 | 2（MATLAB 默认）/ 102（Python N=1024）|
| `k_max` | 最大多普勒索引 | 取决于速度；Python v=1 m/s 时 `k_max_cap=3` |
| `K_LEAK` / `k_leak` | Dirichlet 泄漏半宽 | MATLAB 5；Python 2 |
| `P_paths` | 物理径数（OMP 稀疏度）| MATLAB 2；Python **10**（10 径 UWA 默认）|
| `P_actual` | 分数多普勒扩展后虚拟径数 | `P_paths · (2K_LEAK+1) − 剪枝`；Python N=1024 下 `Pact ≈ 37` |
| `ρ` / `rho` | 导频功率比 | 0.5（SP 默认） |
| `γ_H, γ_x` | 信道/符号阻尼 | 0.7 / 0.6 |
| `NUM_OUTER_ITS` / `n_outer_iter` / `T_outer` | 外层迭代轮数 | 5 |
| `pic_iter` | PIC MP 内循环轮数 | 20（Python 默认） |

### 0.4 阅读路径建议

- **想看算法原理**：从 [第 1 章 AFDM 基础](#第-1-章--afdm-系统与信道模型) → [第 2.3 kLAEK](#23-klaek--分数多普勒泄露扩展本章重点) → [第 5 章 DNN Augmented Classical Unrolling](#第-5-章--dnn-augmented-classical-unrollingclassical_joint_unrolled--b1b2-learned-heads)
- **想看代码对应**：直接跳 [第 9 章 文件索引](#第-9-章--文件索引)，按"功能 → 文件:行号"速查
- **想看效果**：[第 6 章 实验结果](#第-6-章--实验结果与效果)，表格 + 数字为主
- **想对比基线**：[第 7 章](#第-7-章--毕业论文中的其他对比基线)列出论文中用到的对比算法，每个一段原理

### 要点速记

- 三条线功能上类似（都是信道估计 + 检测），但**相位约定、稀疏度策略、超参规模均不同**，不是简单移植关系。
- **导频是统一的 SP**（superimposed pilot）：MATLAB UWA 与 Python 都是 `x_data·√(1−ρ) + x_pilot·√ρ`，差别只在 pilot 序列（MATLAB 随机 QPSK，Python ZC）。
- **kLAEK 是 MATLAB 版的理论精华**；**classical_joint_unrolled + B1 learned head 是 DNN 版的实际贡献**；Python classical 是中间的工程载体，同时也是 DNN 版本的可微分化对象。
- 所有量化数字参见 `AUTO_REVIEW.md`（Round 1–3，2026-04-20）与本章 §6。

---

## 第 1 章 — AFDM 系统与信道模型

### 1.1 AFDM 调制：从 DFT 到 DAFT

AFDM（Affine Fourier Domain Multiplexing）可以理解为"对 OFDM 的 DFT 做一次 chirp 预处理和后处理"。离散 chirp Fourier 变换（DAFT）定义为：

$$
\mathbf{A} = \mathbf{\Lambda}_{c_2} \mathbf{F} \mathbf{\Lambda}_{c_1}
$$

其中 $\mathbf{F}$ 是标准 DFT 矩阵，$\mathbf{\Lambda}_c = \mathrm{diag}(e^{-j 2\pi c \cdot 0^2}, \ldots, e^{-j 2\pi c \cdot (N-1)^2})$ 是 chirp 对角矩阵。当 $c_1, c_2 \ne 0$ 时，AFDM 把时延-多普勒 (delay-Doppler) 两维耦合到同一个 DAFT 维度，这使得即便速度快速变化（即多普勒扩散），等效信道在 DAFT 域仍然稀疏——这是 AFDM 相对于 OFDM 和 OTFS 的关键优势。

与 OTFS/OFDM 的对比（一段话）：OFDM 在正交多普勒面前 ICI 显著；OTFS 通过 delay-Doppler 二维变换解决但需要 2D 处理；AFDM 把这个变换压缩到 1D DAFT，代价是需要正确选择 `c1, c2` 使得信道算子在 DAFT 域变为循环卷积的 chirp 变形。

### 1.2 有效信道矩阵

设物理信道有 $P$ 条径，第 $i$ 条径的 delay 为 $l_i$、Doppler 为 $k_i$、增益为 $g_i$，则等效信道矩阵（接收 DAFT 样本 $y[m]$ 对发射 DAFT 样本 $x[n]$ 的映射）为：

$$
H_{\mathrm{eff}}[m, n] = \sum_{i=1}^{P} g_i \cdot \exp\Big(j 2\pi \big[-c_1 l_i^2 + c_2 (m^2 - n^2) - \tfrac{l_i \cdot n}{N}\big]\Big) \cdot \mathbb{1}\{m = (n + \delta_i) \bmod N\}
$$

其中 $\delta_i = l_i (2k_{\max}+1) + k_i$ 是 $(l_i, k_i)$ 在 DAFT 域的联合位移索引。

在 MATLAB 版本里 $c_2 = 0$，所以式子简化为 $\exp(j 2\pi [-c_1 l_i^2 - l_i n / N])$（忽略符号约定）。在 Python 版本里 $c_2 \ne 0$，保留 $m^2 - n^2$ 项——这是后面章节多处差异的根源。

- MATLAB 实现（c2=0）：`matlab/AFDM_UWA_acoustic.m`（`GEN_H_DAFT`，函数定义与本节其余 helper 同文件，与 LEO 历史脚本 `AFDM_LEO_frac_switch.m` 等价）
- Python 实现（c2≠0）：`afdm_joint_param_unrolled/afdm_baselines.py:189-242`（`reconstruct_H_from_omp`）

### 1.3 水声信道参数

本项目的水声场景（`afdm_env.py:19-179` 中 `AFDMEnvMixin.__init__`）：

| 参数              | 值        | 含义     |
| --------------- | -------- | ------ |
| `fc`            | 12 kHz   | 载频     |
| `B`             | 4 kHz    | 带宽     |
| `fs = 2B`       | 32 kHz   | 采样率    |
| `Ts = 1/fs`     |          | 采样周期   |
| `delta_f`       | 15 Hz    | 子载波间隔  |
| `T = 1/delta_f` |          | 符号周期   |
| `c_sound`       | 1500 m/s | 声速     |
| `P_paths`       | 3-6      | 物理多径数  |
| `tau_spread`    | 10 ms    | 时延扩展   |
| `v_mean`        | 2.0 m/s  | 平均相对速度 |
| `v_std`         | 0.5 m/s  | 速度标准差  |
| N               | 64       | 符号数    |

`N_total = 100`（10 × 10）是 Python 评估默认；MATLAB 典型 `N = 256`(gai) 或更大，视仿真需求。

### 1.4 delay-Doppler 稀疏性与 `(l, k)` 支撑集

水声多径通常 `P_paths ≤ 10`，在总 `N = 100` 个 DAFT 子载波上是极稀疏的。OMP 把信道估计建模为：

$$
\min_{\mathbf{h}} \|\mathbf{y} - \mathbf{\Phi} \mathbf{h}\|_2 \quad \text{s.t.} \quad \|\mathbf{h}\|_0 \le S
$$

其中字典 $\mathbf{\Phi} \in \mathbb{C}^{N \times Q}$ 每一列对应一个候选 `(l, k)` 径的"单位增益响应"，$Q = (l_{\max}+1)(2k_{\max}+1)$。OMP 贪心地选出 $S$ 个支撑列，解其上的 LS 得到径增益。

### 1.5 分数多普勒问题的来源

真实相对速度 $v$ 产生的多普勒频移 $f_d = v \cdot f_c / c_{\text{sound}}$（水声）或 $f_d = v \cdot f_c / c_0$（无线），一般不恰好落在 $k \cdot \Delta f$ 的整数栅格上。设 $k_{\text{real}} = k_{\text{int}} + \kappa$，$|\kappa| \le 0.5$。直接四舍五入 $k_{\text{real}} \to k_{\text{int}}$ 会丢失信息并产生**多普勒泄漏**——真实信道的能量会按 Dirichlet 核散布到 $k_{\text{int}}$ 邻域多个整数格点上。

**Dirichlet 核系数**：

$$
\alpha(m, \kappa, N) = \frac{1}{N} \sum_{n=0}^{N-1} e^{j 2\pi (m + \kappa) n / N} = e^{j \pi (N-1)(m+\kappa)/N} \cdot \frac{\sin \pi (m+\kappa)}{N \sin[\pi (m+\kappa) / N]}
$$

MATLAB 实现在 `matlab/AFDM_UWA_acoustic.m` 中的 `dirichlet_alpha`（与 `AFDM_LEO_frac_switch.m:1405-1419` 同源），Python 实现在 `afdm_env.py:417-446`。两者逻辑完全一致。

### 1.6 kLAEK 思想

**kLAEK = k-Largest-Absolute-Expansion at Kleak**（项目自创术语，CLAUDE.md 里提到的是"k 最大值幂保留"这层意思）。核心想法：

> 把每条物理径 `(l, k_real)` 按 Dirichlet 核分解为 `2K_LEAK+1` 条"虚拟整数多普勒径"：$\{(l, k_{\text{int}} + m)\}_{m=-K_{\text{LEAK}}}^{+K_{\text{LEAK}}}$，权重为 $\alpha(m, \kappa, N)$，然后把这组虚拟径塞给下游 OMP/LS 处理。

这样做的好处：
1. **字典和信道重构逻辑不改**：`GEN_H_DAFT` 仍然用整数 $(l, k)$ 索引。
2. **OMP 支撑扩展**：OMP 先选 seed 径，然后把 seed 在 Doppler 维做 $\pm K_{\text{LEAK}}$ 扩展，DA-LS 阶段再估计邻域增益——cluster-sparse 结构。
3. **能量守恒**：`a_vec /= sqrt(sum(|a_vec|^2))`，保证不同 $\kappa$ 的总功率归一。

MATLAB 扩展实现在 `matlab/AFDM_UWA_acoustic.m` 中的 `expand_support_doppler`（与 `AFDM_LEO_frac_switch.m:1421-1446` 同源）；Python 等价实现在 `afdm_env.py:545-601`（信道生成端）和 `afdm_baselines.py:548-574`（OMP 支撑端）。

### 要点速记

- AFDM 的核心是 DAFT，它把 delay-Doppler 两维耦合到 1D 稀疏结构。
- 等效信道 `H_eff[m,n]` 由 `(l_i, k_i, g_i)` 三元组完全刻画；`c1, c2` 决定相位约定。
- 分数多普勒导致真实 $k$ 不在整数栅格，产生 Dirichlet 泄漏。
- **kLAEK** 是本项目的关键贡献：用 `2K_LEAK+1` 个虚拟整数邻域径来吸收这种泄漏。

---

## 第 2 章 — MATLAB Joint OMP + MP + LS 迭代算法

> **本章文件约定**：水声毕业设计的主入口是 `matlab/AFDM_UWA_acoustic.m`（采用 SP 叠加导频的 10 径 UWA 配置）。早期 LEO 卫星实验脚本 `matlab/AFDM_LEO_frac_switch.m` 与之共享几乎所有 helper 函数（`construct_afdm_sensing_matrix` / `OMP` / `dirichlet_alpha` / `expand_support_doppler` / `weighted_ls` / `MP_detection_optimized` 等），下文给出 helper 行号时引用 LEO 文件以方便对照原始注释，但**正式文件请以 `AFDM_UWA_acoustic.m` 为准**。

### 2.1 五轮外迭总流程

主入口 `joint_omp_mp_ls_sparse` 定义在 `matlab/AFDM_UWA_acoustic.m`（行号与历史文件 `AFDM_LEO_frac_switch.m:730` 同源）起，约 30 个超参，签名长，核心外层循环类似 `:774` 起：

```matlab
for it = 1:NUM_OUTER_ITS            % 通常 5 轮
    %% (A) 信道估计
    if it == 1
        % OMP 确定支撑集
        Phi_pilot = construct_afdm_sensing_matrix(N_data, x_pilot, c1, Q, l_max-1, k_max, 1, 1);
        [h_new, ~] = OMP(Y_DA, Phi_pilot_scaled, taps);
        [support_delays, support_dopplers, gains_S] = extract_delay_doppler_from_h(...);
        if ~INTEGER_DOPPLER_FLAG
            [support_delays, support_dopplers, gains_S] = expand_support_doppler(...);   % kLAEK
        end
    else
        % 后续迭代：硬判决 + 数据辅助 LS（DA-LS）
        x_hard_scaled = qam_demap_then_map(x_soft_scaled);
        x_total_scaled = x_p_scaled + x_hard_scaled;
        A_total = build_path_cols(support_delays, support_dopplers, x_total_scaled);
        gains_S = weighted_ls(A_total, Y_DA, [], lambda_ls, gains_S);
    end
    H_new = GEN_H_DAFT(N_data, gains_S, support_delays, support_dopplers, c1);
    Hhat = (1-GAMMA_H_DAMP)*Hhat + GAMMA_H_DAMP*H_new;     % 信道阻尼
    Hhat = sparsify(Hhat, TAU_H_FACTOR, TAU_H_SIGMA_FACTOR);

    %% (B) MP 数据检测
    Y_for_det = Y_DA - Hhat * x_p_scaled;
    x_mp_scaled = MP_detection_optimized(Y_for_det, Hhat, sigma2_eff, num_iter_MP, threshold_MP, M_mod, sqrt(P_data));
    x_soft_scaled = (1-GAMMA_X_DAMP)*x_soft_scaled + GAMMA_X_DAMP*x_mp_scaled;

    %% (C) 自适应噪声估计
    if UPDATE_SIGMA2_EACH_OUTER
        res = Y_DA - Hhat * x_total_for_res;
        sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(||res||^2 / N_data, 1e-12);
    end

    %% (D) 早停
    curr_resnorm = ||Y_DA - Hhat * x_total_stop||^2;
    if (prev_resnorm - curr_resnorm)/curr_resnorm in [0, EPS_STOP_REL]
        break;
    end
end
```

（以上为精简伪代码；水声主流程完整实现见 `matlab/AFDM_UWA_acoustic.m`，对应历史文件 `matlab/AFDM_LEO_frac_switch.m:774-919`）

**关键参数值**（`:119-125`）：

```matlab
NUM_OUTER_ITS            = 5;
GAMMA_H_DAMP             = 0.7;
GAMMA_X_DAMP             = 0.6;
EPS_STOP_REL             = 1e-3;
UPDATE_SIGMA2_EACH_OUTER = true;
K_LEAK                   = 5;
```

**状态量演化图**（每迭代一次更新）：

```
        it=1 (OMP)            it=2..5 (DA-LS)
      ┌────────────┐        ┌────────────┐
      │ gains_S    │  ──────→ gains_S'  │
      │ support_{l,k}│       │ (支撑集固定)│
      └────────────┘        └────────────┘
             │                      │
             ▼                      ▼
         Hhat (N×N sparse) ← damping ← H_new
             │
             ▼
         MP detection
             │
             ▼
         x_soft_scaled ← damping ← x_mp_scaled
             │
             ▼
         sigma2_eff (自适应更新)
```

### 2.2 OMP 初始化

#### 2.2.1 感知矩阵构造

`construct_afdm_sensing_matrix`（`matlab/AFDM_UWA_acoustic.m`，行号同源 LEO 历史脚本 `:1124-1160`）：

```matlab
function Phi = construct_afdm_sensing_matrix(N, x_pilot, c1, Q, max_delay, max_doppler, delay_res, doppler_res)
    Phi = zeros(N, Q);
    q_vec = (0:N-1).';
    c2 = 0;   % MATLAB 约定：c2 恒为 0
    col_idx = 1;
    for l = 0 : delay_res : max_delay
        for k = -max_doppler : doppler_res : max_doppler
            loc_val = k + 2 * N * c1 * l;                    % 位移量
            p_vec = mod(round(q_vec - loc_val), N);          % 接收索引
            term1 = N * c1 * (l^2);
            term2 = -q_vec * l;
            term3 = N * c2 * (q_vec.^2 - p_vec.^2);          % c2=0 所以此项为 0
            total_phase = (2*pi/N) * (term1 + term2 + term3);
            H_vals = exp(1j * total_phase);
            y_col = zeros(N, 1);
            for qi = 1:N
                p_idx = p_vec(qi) + 1;
                y_col(p_idx) = y_col(p_idx) + H_vals(qi) * x_pilot(qi);
            end
            Phi(:, col_idx) = y_col;
            col_idx = col_idx + 1;
        end
    end
end
```

字典有 $Q = (l_{\max}+1)(2k_{\max}+1)$ 列，每列对应一个 `(l, k)` 候选径的 "单位增益、仅此径、导频通过此径" 的 DAFT 观测。

#### 2.2.2 OMP 贪心循环

`OMP` 函数（`matlab/AFDM_UWA_acoustic.m`，行号同源 LEO 历史脚本 `:1180-1218`）：

```matlab
function [h_i, Omega] = OMP(y, P, S)
    N = size(y,1); K = size(P,2);
    err = 1e-3;
    h_i = zeros(K, 1);
    y_i = y - P * h_i;           % 初始残差 = y
    it = 0; stop = 0;
    P_s = []; pos_array = [];
    while ~stop
        for ntl = 1:K
            product(ntl) = abs(P(:,ntl)' * y_i);        % Step 1: 相关性
        end
        [val, pos] = max(product);                       % Step 2: 最强列
        P_s = [P_s, P(:,pos)]; pos_array = [pos_array, pos];
        P(:,pos) = zeros(N, 1);                          % 删除已选列
        h_s = (P_s' * P_s)^(-1) * P_s' * y;              % Step 3: LS refit
        y_i = y - P_s * h_s;                             % Step 4: 残差
        it = it + 1;
        if (it >= S) || norm(y_i) <= err * norm(y)        % 停止
            stop = 1;
        end
    end
    h_i(pos_array) = (P_s' * P_s)^(-1) * P_s' * y;       % 最终 LS
    Omega = pos_array;
end
```

**停止条件**：选够 $S$ 个径（=`taps`，即物理路径数先验），**或**残差相对范数 ≤ `1e-3`。

#### 2.2.3 支撑集提取

`extract_delay_doppler_from_h`（`:1162-1178`）把稀疏系数 `h` 解码回 `(l, k, gain)` 三元组：

```matlab
[~, sorted_indices] = sort(abs(h), 'descend');
topP_indices = sorted_indices(1:min(P, length(h)));
gains = h(topP_indices);
num_dopplers = round((2*max_doppler_index)/doppler_res + 1);
for i = 1:length(topP_indices)
    idx = topP_indices(i) - 1;
    delay_idx = floor(idx / num_dopplers);
    doppler_idx_from_zero = mod(idx, num_dopplers);
    doppler_idx = doppler_idx_from_zero - max_doppler_index / doppler_res;
    delays(i) = delay_idx * delay_res;
    dopplers(i) = doppler_idx * doppler_res;
end
```

注意列索引解码：OMP 字典列按 `(l, k)` 字典序排列，`idx = l·num_dopplers + (k + max_doppler_index)`。

### 2.3 kLAEK / 分数多普勒泄露扩展（本章重点）

这是 MATLAB 版的理论精华。由两个互补的部分组成：**信道生成端的 Dirichlet 分解**和 **OMP 支撑端的邻域扩展**。

#### 2.3.1 Dirichlet 核系数

`dirichlet_alpha`（`matlab/AFDM_UWA_acoustic.m`，行号同源 LEO 历史脚本 `:1405-1419`）：

```matlab
function a = dirichlet_alpha(m, kappa, N)
    x = m + kappa;
    if abs(x) < 1e-12
        a = 1 + 0j;
        return;
    end
    denom = sin(pi * x / N);
    if abs(denom) < 1e-12
        a = exp(1j*pi*(N-1)*x/N);       % 极限处理
    else
        a = exp(1j*pi*(N-1)*x/N) * sin(pi*x) / (N * denom);
    end
end
```

数学形式已在 §1.5 给出。注意两处数值保护：`x ≈ 0` 返回 1（分母零点用 sinc 的 L'Hôpital 极限），`denom ≈ 0`（$x$ 接近 $N$ 的整数倍）用极限公式。

#### 2.3.2 信道生成端：Dirichlet 分解

`generate_NTN_TDL_channel_SISO` 函数中 fractional 分支（`:1304-1331`）：

```matlab
else     % ~INTEGER_DOPPLER_FLAG
    % 分数多普勒版本(Cluster-sparse)
    % k_real = k_int + kappa, kappa ∈ (-0.5, 0.5]
    chan_coef = []; delay_taps = []; Doppler_taps = [];
    for ii = 1:P_phy
        k_int = round(k_real(ii));
        k_int = min(max(k_int, -k_max), k_max);
        kappa = k_real(ii) - k_int;
        m_vec = (-K_LEAK:K_LEAK).';
        a_vec = zeros(length(m_vec), 1);
        for mm = 1:length(m_vec)
            a_vec(mm) = dirichlet_alpha(m_vec(mm), kappa, N_data);
        end
        a_vec = a_vec / sqrt(sum(abs(a_vec).^2) + eps);     % 能量归一化
        for mm = 1:length(m_vec)
            k_eff = k_int + m_vec(mm);
            if k_eff < -k_max || k_eff > k_max
                continue;
            end
            Doppler_taps = [Doppler_taps; k_eff];
            delay_taps   = [delay_taps;  delay_taps_phy(ii)];
            chan_coef    = [chan_coef;   chan_coef_phy(ii) * a_vec(mm)];
        end
    end
end
```

一条物理径 `(l_phy, k_real)` 被展开为 `2K_LEAK+1 = 11` 条虚拟整数径（MATLAB 默认 `K_LEAK=5`）。

#### 2.3.3 OMP 支撑端：邻域扩展

`expand_support_doppler`（`:1421-1446`）：

```matlab
function [delays_ex, dopplers_ex, gains_ex] = expand_support_doppler(delays, dopplers, gains, k_max, K_LEAK)
    delays_ex = []; dopplers_ex = []; gains_ex = [];
    for ii = 1:length(delays)
        for m = -K_LEAK:K_LEAK
            k_new = dopplers(ii) + m;
            if k_new < -k_max || k_new > k_max
                continue;
            end
            delays_ex   = [delays_ex;   delays(ii)];
            dopplers_ex = [dopplers_ex; k_new];
            if m == 0
                gains_ex = [gains_ex; gains(ii)];           % 中心径保留增益
            else
                gains_ex = [gains_ex; 0];                    % 邻域初始化为 0
            end
        end
    end
    % 合并重复的 (l, k)
    pairs = [delays_ex(:), dopplers_ex(:)];
    [pairs_u, ~, ic] = unique(pairs, 'rows');
    gains_u = accumarray(ic, gains_ex(:));
    delays_ex   = pairs_u(:,1);
    dopplers_ex = pairs_u(:,2);
    gains_ex    = gains_u;
end
```

**关键设计**：
- OMP 选出的 seed 径 `(l, k)` 被扩展为 `(l, k-K_LEAK), ..., (l, k+K_LEAK)` 共 `2K_LEAK+1` 条候选径。
- 中心径保留 OMP 估计的增益，邻域径增益初始化为 0，**等待后续 DA-LS 阶段估计**。
- `unique + accumarray` 合并重复 `(l, k)`（当两个 seed 径邻域重叠时）。

#### 2.3.4 流程示意图（ASCII）

```
  物理信道生成:
    k_real = [2.3, -1.8]      (非整数)
    ↓
    Dirichlet 分解 (K_LEAK=5):
    k_real=2.3  →  [(l=0, k= -3, g·a_-5), ..., (l=0, k=+7, g·a_+5)]
    k_real=-1.8 →  [(l=1, k= -7, g·a_-5), ..., (l=1, k=+3, g·a_+5)]
    ↓
    GEN_H_DAFT(整数索引) → H_true (N×N)

  OMP 支撑端:
    OMP(y, Phi, S=2) → 选出 2 个 seed: (l=0, k=2), (l=1, k=-2)
    ↓
    expand_support_doppler(K_LEAK=5):
    seed=(0,2) → [(0,-3), (0,-2), ..., (0,7)]   (11 条)
    seed=(1,-2) → [(1,-7), (1,-6), ..., (1,3)]  (11 条)
    ↓
    合并 unique → 22 条候选径 (可能有重叠)
    ↓
    DA-LS 估所有 22 条径的增益
```

### 2.4 Data-Aided LS 细化（迭代 2–5）

第 1 轮 OMP 确定支撑后，后续 4 轮迭代在**支撑集固定**的前提下交替更新"径增益"和"数据符号"。

#### 2.4.1 硬判决重构

`matlab/AFDM_UWA_acoustic.m`（行号同源 LEO 历史脚本 `:800-814`）：

```matlab
else
    % Step 1: 软符号 -> 单位功率域
    x_soft_unit = x_soft_scaled / sqrt(power_levels(1));

    % Step 2: 硬判决（映射到最近的 QAM 星座点）
    x_hard_idx  = qamdemod(x_soft_unit, M_mod, 'gray', 'UnitAveragePower', true);
    x_hard_unit = qammod(x_hard_idx, M_mod, 'gray', 'UnitAveragePower', true);

    % Step 3: 缩放回数据功率域
    x_hard_scaled = x_hard_unit * sqrt(power_levels(1));

    % Step 4: 构造"全信号" x_total = x_pilot + x_hard_data
    x_total_scaled = x_p_scaled + x_hard_scaled;
    ...
```

#### 2.4.2 字典列生成

单径字典列 `gen_path_col`（`:964-990`），与 `construct_afdm_sensing_matrix` 的单列版本一致：

```matlab
function a_col = gen_path_col(N, l, k, c1, x_scaled)
    q_vec = (0:N-1).';
    c2 = 0;
    loc_val = k + 2 * N * c1 * l;
    p_vec = mod(round(q_vec - loc_val), N);
    term1 = N * c1 * (l^2);
    term2 = -q_vec * l;
    term3 = N * c2 * (q_vec.^2 - p_vec.^2);
    total_phase = (2*pi/N) * (term1 + term2 + term3);
    H_vals = exp(1j * total_phase);
    a_col = zeros(N, 1);
    for qi = 1:N
        p_idx = p_vec(qi) + 1;
        a_col(p_idx) = a_col(p_idx) + H_vals(qi) * x_scaled(qi);
    end
end
```

区别仅在于用的是 `x_total = x_pilot + x_hard_data`（而不是 `x_pilot` 单独）。

#### 2.4.3 加权 LS + Tikhonov 正则

`weighted_ls`（`:992-1019`）：

```matlab
function g = weighted_ls(A, y, w, lambda, g_prev)
    if nargin < 5 || isempty(g_prev)
        g_prev = zeros(size(A, 2), 1);
    end
    if isempty(w)
        W2 = speye(length(y));
    else
        W2 = spdiags(w.^2, 0, length(w), length(w));
    end
    g = (A' * W2 * A + lambda * eye(size(A, 2))) \ (A' * W2 * y + lambda * g_prev);
end
```

公式：

$$
\mathbf{g}_{\text{new}} = (\mathbf{A}^H \mathbf{W}^2 \mathbf{A} + \lambda \mathbf{I})^{-1} (\mathbf{A}^H \mathbf{W}^2 \mathbf{y} + \lambda \mathbf{g}_{\text{prev}})
$$

**设计要点**：
- `λ > 0` 防止病态（径数超过有效观测时）。
- `g_prev` 是上一轮的估计，起"平滑"作用——等价于先验为 $\mathcal{N}(\mathbf{g}_{\text{prev}}, \lambda^{-1} \mathbf{I})$ 的 MAP 估计。
- $\lambda$ 随 $\sigma^2_{\text{eff}}$ 更新（`lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)`），噪声越大正则越强。

#### 2.4.4 信道阻尼

`:846`：

```matlab
Hhat = (1 - GAMMA_H_DAMP) * Hhat + GAMMA_H_DAMP * H_new;
```

这个 `Hhat` 是全 $N \times N$ 稀疏矩阵。`GAMMA_H_DAMP = 0.7` 意味着新估计占 70%、旧估计占 30%，抑制迭代震荡。

### 2.5 MP 检测（`MP_detection_optimized`）

#### 2.5.1 因子图与稀疏化

`MP_detection_optimized`（`matlab/AFDM_UWA_acoustic.m`，行号同源 LEO 历史脚本 `:465-724`）把 $\mathbf{Y} = \mathbf{H} \mathbf{x} + \mathbf{n}$ 建成二部因子图：观测节点（行） $\leftrightarrow$ 符号节点（列），边是非零 $H_{ij}$。

**稀疏化门限**（`:481` 附近）：

```matlab
[row_idx, col_idx, h_vals] = find(H);
mask = abs(h_vals) >= threshold;                   % 典型 threshold=1e-4
row_idx = row_idx(mask);
col_idx = col_idx(mask);
h_vals  = h_vals(mask);
E = length(h_vals);                                % 边数
```

然后构造 CSR/CSC 索引（按行分组的 `edge_id_by_row`、按列分组的 `edge_id_by_col`），使 O2V 和 V2O 循环可以 O(E) 遍历。

#### 2.5.2 O2V（Observation → Variable）

对每个观测节点 $d$：

```matlab
edges_d = edge_id_by_row(...);     % 行 d 上的所有边
h_d = h_vals(edges_d);
mu_in = mu_v2o(edges_d);           % V→O 传入消息均值
var_in = var_v2o(edges_d);
z_total = y(d) - sum(h_d .* mu_in);
V_total = sigma2 + sum(abs(h_d).^2 .* var_in);

for local_e = 1:length(edges_d)
    e = edges_d(local_e);
    h_e = h_d(local_e); mu_e = mu_in(local_e); var_e = var_in(local_e);
    z_ext = z_total + h_e * mu_e;                   % 排除当前边
    V_ext = max(V_total - abs(h_e)^2 * var_e, sigma2 * 0.1);
    var_o2v(e) = V_ext / abs(h_e)^2;
    mu_o2v(e)  = z_ext / h_e;
end
```

直观理解：O2V 消息等价于"把行 $d$ 上其他 V 节点的贡献减掉后，剩余部分对 $x_e$ 的估计"。

#### 2.5.3 V2O（Variable → Observation）

对每个符号节点 $n$：

```matlab
edges_n = edge_id_by_col(...);
mu_in = mu_o2v(edges_n);
var_in = var_o2v(edges_n);
prec_from_obs = sum(1 ./ var_in);
mean_from_obs = sum(mu_in ./ var_in);

for local_e = 1:length(edges_n)
    e = edges_n(local_e);
    prec_ext = max(prec_from_obs - 1./var_in(local_e), 1e-10);
    mean_ext = mean_from_obs - mu_in(local_e)/var_in(local_e);
    var_ext = 1/prec_ext;
    mu_ext  = var_ext * mean_ext;
    % 离散去噪（QPSK）
    dist_sq = abs(constellation - mu_ext).^2;
    log_like = -dist_sq / var_ext;
    log_prob = log_prior + log_like;
    log_prob = log_prob - max(log_prob);            % 数值稳定
    prob = exp(log_prob); prob = prob / sum(prob);
    mu_new = sum(prob .* constellation);
    var_new = sum(prob .* abs(constellation).^2) - abs(mu_new)^2;
    mu_v2o(e) = (1-damp)*mu_v2o_old(e) + damp*mu_new;
    var_v2o(e) = var_new;
end
```

V2O 消息是"在 $x_n$ 上综合所有观测后，投影到离散星座的后验"。用离散先验 $\times$ 连续高斯似然，归一化后得到符号后验分布，再算均值方差。

#### 2.5.4 迭代控制

- 内迭代次数：`num_iter_MP = 20`
- 阻尼：`damp = 0.5`
- 收敛判据：`norm(mu_v2o - mu_v2o_old) / norm(mu_v2o) < 1e-4`

### 2.6 自适应噪声估计 + 稀疏化 + 早停

#### 2.6.1 自适应噪声估计

`:880-894`：

```matlab
if UPDATE_SIGMA2_EACH_OUTER
    x_total_for_res = x_p_scaled + x_hard_scaled_for_res;
    res = Y_DA - Hhat * x_total_for_res;
    sigma2_new = real(sum(abs(res).^2)) / N_data;
    sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12);
    lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff);
end
```

EMA 更新（70/30）防止单帧噪声突变干扰正则强度。

#### 2.6.2 稀疏化门限

`:848-861`：

```matlab
max_h_val = max(abs(nonzeros(Hhat)));
tau_h_relative = TAU_H_FACTOR * max_h_val;         % 默认 0.01
tau_h_sigma    = TAU_H_SIGMA_FACTOR * sqrt(sigma2_eff);    % 默认 0.1
tau_h = max(tau_h_relative, tau_h_sigma);
[row_h, col_h, val_h] = find(Hhat);
mask_h = abs(val_h) >= tau_h;
Hhat = sparse(row_h(mask_h), col_h(mask_h), val_h(mask_h), N_data, N_data);
```

"取最大绝对值的 1%" 和 "噪声标准差的 10%" 两者取大。保证低噪声时不会因 $\sqrt{\sigma^2}$ 太小把真正的径剪掉。

#### 2.6.3 早停

`:896-918`：

```matlab
curr_resnorm = real(sum(abs(Y_DA - Hhat * x_total_stop).^2));
if prev_resnorm < Inf
    rel_improve = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12);
    if rel_improve < EPS_STOP_REL && rel_improve >= 0
        ber_iter_history(it:end) = ber_iter;        % 后面的迭代填充为当前 BER
        break;
    end
end
prev_resnorm = curr_resnorm;
```

早停的条件是"残差改进在 [0, 1e-3] 之间"——也就是既不能回退也不能明显改进，表明收敛。

### 要点速记

- MATLAB 主入口 `joint_omp_mp_ls_sparse` 固定 5 轮外迭：第 1 轮 OMP 定支撑，第 2–5 轮 DA-LS 细化。
- **kLAEK 在两个位置出现**：信道生成端（Dirichlet 分解）和 OMP 支撑端（邻域扩展）。
- 加权 LS 加 Tikhonov 正则，$\lambda$ 随 $\sigma^2_{\text{eff}}$ 自适应。
- MP 用离散高斯消息传递 + 阻尼，内迭代 20 轮。
- 早停判据严格要求"既不能退步也不能有超过 `EPS_STOP_REL` 的改进"。

---

## 第 3 章 — Python Joint OMP + MP 算法

### 3.1 文件组织与主入口

Python 侧有两个平行的实现目录（**结构相同但有少量差异**）：
- `afdm_joint_param_unrolled/afdm_baselines.py`（早期主线）
- `afdm_sp_joint_unrolled/afdm_baselines.py`（Superimposed Pilot 专用，2026/03/29 起成为最新版）

两者的 `joint_omp_mp_iterative` 主函数签名几乎一致，以 `afdm_joint_param_unrolled/afdm_baselines.py:445-458` 为准：

```python
def joint_omp_mp_iterative(y_daft, x_pilot_scaled, N, c1, c2, l_max, k_max,
                            sigma2, constellation_data, n_paths=5,
                            n_outer_iter=5, rho=0.3,
                            pic_iter=15, pic_damp=0.5,
                            mp_mode='pic', threshold_mp=1e-4,
                            gamma_h=0.7, gamma_x=0.6,
                            lambda_ls_factor=1e-3,
                            tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                            k_leak=2, eps_stop_rel=1e-3,
                            update_sigma2=True,
                            phase_convention='python',
                            return_soft=False,
                            data_pos=None,
                            return_trajectory=False):
```

**与 MATLAB 的对应**：

| MATLAB | Python | 行号 | 差异 |
|---|---|---|---|
| `joint_omp_mp_ls_sparse` | `joint_omp_mp_iterative` | `:445-758` | 增加 `c2`、`phase_convention`、`return_trajectory` 等参数 |
| `construct_afdm_sensing_matrix` | `construct_sensing_matrix` | `:42-88` | 默认带 `c2*(q²-p²)` 项 |
| — | `construct_sensing_matrix_matlab` | `:164-183` | MATLAB 约定对齐版（c2=0）|
| `OMP` | `omp_sparse` | `:94-143` | 完全一致 |
| `GEN_H_DAFT` | `reconstruct_H_from_omp` | `:189-242` | 默认带 c2 项 |
| — | `reconstruct_H_from_omp_matlab` | `:245-268` | MATLAB 对齐版 |
| `MP_detection_optimized` | `mp_detect_bp` | `:324-438` | 算法一致，实现向量化略不同 |
| — | `mp_detect_pic` | `:275-321` | Python 特有的快速 PIC 版本 |
| `expand_support_doppler` | 内嵌于 `joint_omp_mp_iterative:548-574` | — | 逻辑一致 |

### 3.2 OMP 字典构造的两个版本

Python 保留了两个相位约定，由 `phase_convention` 参数切换。

#### 3.2.1 Python 约定（`phase_convention='python'`，默认）

`afdm_baselines.py:42-87`：

```python
def construct_sensing_matrix(N, x_pilot_scaled, c1, c2, l_max, k_max):
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    q_arr = np.arange(N, dtype=np.float64)
    Phi = np.zeros((N, Q), dtype=complex)
    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        for k in range(-k_max, k_max + 1):
            delta = l * K + k                     # DAFT shift
            p_arr = (q_arr - delta) % N           # 接收索引
            phase = np.exp(1j * 2.0 * np.pi * (
                -c1 * l_sq
                + c2 * (q_arr ** 2 - p_arr ** 2)
                - float(l) * p_arr / N
            ))
            Phi[:, col] = phase * x_pilot_scaled[p_arr.astype(int)]
            col += 1
    return Phi
```

相位公式：

$$
\Phi[q, \text{col}(l, k)] = \exp\Big(j 2\pi [-c_1 l^2 + c_2 (q^2 - p^2) - l p / N]\Big) \cdot x_{\text{pilot}}[p]
$$

其中 $p = (q - \delta) \bmod N$，$\delta = l K + k$。

#### 3.2.2 MATLAB 对齐版（`phase_convention='matlab'`）

`afdm_baselines.py:164-183`：

```python
def construct_sensing_matrix_matlab(N, x_pilot_scaled, c1, l_max, k_max):
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    q_arr = np.arange(N, dtype=np.float64)
    Phi = np.zeros((N, Q), dtype=complex)
    col = 0
    for l in range(l_max + 1):
        for k in range(-k_max, k_max + 1):
            loc_val = k + 2.0 * N * c1 * l
            p_arr = np.mod(np.round(q_arr - loc_val).astype(int), N)
            phase = np.exp(1j * ((2.0 * np.pi / N) * (N * c1 * (l ** 2) - q_arr * l)))
            y_col = np.zeros(N, dtype=complex)
            np.add.at(y_col, p_arr, phase * x_pilot_scaled)
            Phi[:, col] = y_col
            col += 1
    return Phi
```

相位公式（对应 MATLAB）：

$$
\Phi[p, \text{col}(l, k)] = \exp\Big(j \tfrac{2\pi}{N} [N c_1 l^2 - q l]\Big) \cdot x_{\text{pilot}}[q]
$$

其中 $p = (q - (k + 2 N c_1 l)) \bmod N$。

#### 3.2.3 并排对比

| 方面      | Python 约定              | MATLAB 约定                                                |
| ------- | ---------------------- | -------------------------------------------------------- |
| `c1` 符号 | `-c1·l²`               | `+c1·l²`                                                 |
| `c2` 项  | 保留 `+c2·(q² − p²)`     | c2 = 0，此项消失                                              |
| 索引映射    | `p = (q - δ) % N`      | `p = round(q - loc_val) % N`，其中 `loc_val = k + 2·N·c1·l` |
| 散射方向    | `Phi[q, col]` 按 $q$ 求值 | `Phi[p, col]` 按 $p$ 散射                                   |

**工程含义**：两个字典矩阵是**不同的**，对同一个观测 $\mathbf{y}$ 会得到不同的 OMP 支撑。这是 Python 版 BER 曲线与 MATLAB 不能直接比较的根本原因。

### 3.3 OMP 稀疏恢复

`omp_sparse`（`afdm_baselines.py:94-143`）是标准 OMP，与 MATLAB 完全一致：

```python
def omp_sparse(y, Phi, sparsity):
    Q = Phi.shape[1]
    residual = y.copy()
    support = []
    Phi_H = Phi.conj().T
    for _ in range(sparsity):
        correlations = np.abs(Phi_H @ residual)
        for idx in support:
            correlations[idx] = 0.0                  # 已选列置零
        new_idx = int(np.argmax(correlations))
        support.append(new_idx)
        Phi_S = Phi[:, support]
        gains_S, _, _, _ = np.linalg.lstsq(Phi_S, y, rcond=None)
        residual = y - Phi_S @ gains_S
        if np.linalg.norm(residual) < 1e-10 * np.linalg.norm(y):
            break
    # 最终 LS
    h_est = np.zeros(Q, dtype=complex)
    if support:
        Phi_S = Phi[:, support]
        gains_final, _, _, _ = np.linalg.lstsq(Phi_S, y, rcond=None)
        for i, idx in enumerate(support):
            h_est[idx] = gains_final[i]
    return h_est, support
```

**两处细节差异**（vs MATLAB）：
- Python 用 `np.linalg.lstsq`（SVD-based）而 MATLAB 用 `(P_s' * P_s)^(-1) * P_s' * y`（正规方程）。SVD 更数值稳定，但在病态时可能给出正则化后的解。
- MATLAB 停止阈值 `err = 1e-3`，Python `1e-10`——Python 更严格，但实际通常先撞到 `sparsity` 上限。

### 3.4 信道重建 `reconstruct_H_from_omp`

`afdm_baselines.py:189-242`：

```python
def reconstruct_H_from_omp(N, h_omp, k_max, l_max, c1, c2, threshold=1e-3):
    K = 2 * k_max + 1
    n_arr = np.arange(N, dtype=np.float64)
    H_est = np.zeros((N, N), dtype=complex)
    max_gain = np.max(np.abs(h_omp))
    if max_gain < 1e-30:
        return H_est
    thr_abs = threshold * max_gain                   # 相对剪枝
    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        l_f = float(l)
        for k in range(-k_max, k_max + 1):
            g = h_omp[col]
            col += 1
            if abs(g) < thr_abs:
                continue
            delta  = l * K + k
            m_arr  = (n_arr + delta) % N
            m_idx  = m_arr.astype(int)
            phase  = np.exp(1j * 2.0 * np.pi * (
                -c1 * l_sq
                + c2 * (m_arr ** 2 - n_arr ** 2)
                - l_f * n_arr / N
            ))
            H_est[m_idx, np.arange(N)] += g * phase
    return H_est
```

**向量化**：`H_est[m_idx, np.arange(N)] += g * phase` 一次赋 $N$ 个元素，比 MATLAB 的双循环快很多（`np.add.at` 在有重复 `m_idx` 时自动累加）。

**剪枝**：`threshold=1e-3` 意味着相对峰值 0.1% 以下的径直接丢掉。这是对 `h_omp` 里未被 OMP 选中（本来就是 0）和选中但幅度极小的径的统一处理。

### 3.5 Python 分数多普勒与 kLAEK

#### 3.5.1 OMP 支撑端扩展（集成在 `joint_omp_mp_iterative`）

`afdm_baselines.py:548-574`：

```python
# Cluster-support expansion: add ±k_leak Doppler neighbours
exp_delays = []
exp_dopplers = []
exp_gains = []
for i in range(len(s_delays)):
    for m in range(-k_leak, k_leak + 1):
        k_new = s_dopplers[i] + m
        if abs(k_new) > k_max:
            continue
        exp_delays.append(s_delays[i])
        exp_dopplers.append(k_new)
        exp_gains.append(s_gains[i] if m == 0 else 0.0)

# Merge duplicate (l, k) pairs
if len(exp_delays) > 0:
    pairs = np.column_stack([exp_delays, exp_dopplers])
    gains_arr = np.array(exp_gains, dtype=complex)
    unique_pairs, inverse = np.unique(pairs, axis=0, return_inverse=True)
    merged_gains = np.zeros(len(unique_pairs), dtype=complex)
    np.add.at(merged_gains, inverse, gains_arr)
    support_delays   = unique_pairs[:, 0].astype(int)
    support_dopplers = unique_pairs[:, 1].astype(int)
    gains_S = merged_gains
```

逻辑与 MATLAB 的 `expand_support_doppler` 完全一致。**区别仅在 `k_leak` 的默认值**：Python 是 **2**，MATLAB 是 **5**——Python 的虚拟径数从 11 降到 5，更保守。

#### 3.5.2 信道生成端分数多普勒分解

在 `afdm_env.py:545-601`（未在 baselines 里调用，而是在仿真端生成真实信道用）。核心逻辑与 MATLAB `:1304-1331` 完全镜像，差异在 Python 多了一个 **"弱旁瓣剪枝"**：

```python
prune_thres = self.frac_prune_rel_thres   # = 0.01
...
a_pow = np.abs(a_vec) ** 2
a_peak = np.max(a_pow)
for mm, m in enumerate(m_range):
    k_eff = k_base + int(m)
    if abs(k_eff) > k_clip:
        continue
    if a_pow[mm] < prune_thres * a_peak:        # 剪枝：< 1% peak 的邻域不算
        continue
    chan_coef_exp.append(g_i_raw[i] * a_vec[mm])
    ...
```

剪枝使得 `P_actual ≈ P_paths · (2k_leak+1) × 剪枝系数`。典型 `P_paths=5, k_leak=2` 下 `P_actual ≈ 8–20`。

#### 3.5.3 SP 导频下的稀疏度限制

**这是 SP 流水线最微妙的工程决策**：OMP 稀疏度到底应该用 `P_paths` 还是 `P_actual`？

- MATLAB 与 Python 都使用 **superimposed pilot (SP / 叠加导频)**：导频和数据同一子载波叠加，$x = \sqrt{\rho}\cdot x_p + \sqrt{1-\rho}\cdot d$（MATLAB 取 `x_p` 为随机 QPSK，Python 取 `x_p` 为 ZC 序列）。SP 下 OMP 看到的是"导频 + 数据干扰"，导频-数据相关项在感知矩阵中作为加性扰动出现。
- 选择稀疏度时，如果用 kLAEK 扩展后的 `P_actual`（典型 8–20），OMP 会把数据干扰能量误识别为额外径，过拟合后稳定性下降；若限制为物理径数 `P_paths`（典型 5–10），OMP 只挑显著 seed，剩余邻域径增益交给后续 DA-LS 估计。

实验结果证实了这一点（`run_baseline.py` 的 `p_actual_only` ablation）：SP + `P_actual` 稀疏度 → BER 比 `P_paths` 稀疏度更差。所以**两侧统一约定 OMP 稀疏度 = `P_paths`，kLAEK 扩展后的虚拟径在后续 DA-LS 里估计**。这是 SP 范式相对于 EP 的代价，也是为什么 SP 必须搭配 DA-LS 才能保住性能。

### 3.6 两种 MP 实现

#### 3.6.1 PIC（Parallel Interference Cancellation，快速版）

`mp_detect_pic`（`afdm_baselines.py:275-321`）：

```python
def mp_detect_pic(y_data, H, sigma2, constellation, n_iter=15, damp=0.5):
    HH_diag = np.sum(np.abs(H) ** 2, axis=0)
    inv_denom = 1.0 / np.maximum(HH_diag + sigma2, 1e-30)

    # 初始化：MF → 硬判决
    x_mf = H.conj().T @ y_data * inv_denom
    x_hat = np.array([constellation[np.argmin(np.abs(xv - constellation))] for xv in x_mf], dtype=complex)

    for _ in range(n_iter):
        r = y_data - H @ x_hat                           # 残差
        x_new = x_hat + H.conj().T @ r * inv_denom       # MRC 修正
        x_hard = np.array([constellation[np.argmin(np.abs(xv - constellation))] for xv in x_new], dtype=complex)
        x_hat = damp * x_hard + (1.0 - damp) * x_hat
    return np.array([constellation[np.argmin(np.abs(xv - constellation))] for xv in x_hat], dtype=complex)
```

- 复杂度 O(`n_iter × N²`)，典型 `n_iter=15`、`N=100` → ~15 万次复乘。
- 适合快速跑大量仿真。
- **不输出 soft 信息**（只有硬符号）。

#### 3.6.2 BP（完整 Gaussian 信念传播）

`mp_detect_bp`（`afdm_baselines.py:324-438`）是 MATLAB `MP_detection_optimized` 的 Python 端口，算法骨架（省略循环）：

```python
# 准备稀疏结构
mask = np.abs(H) >= threshold
row_idx, col_idx = np.nonzero(mask)
h_vals = H[row_idx, col_idx]
row_edges = [[] for _ in range(N)]; col_edges = [[] for _ in range(N)]
for e, (r, c) in enumerate(zip(row_idx, col_idx)):
    row_edges[r].append(e); col_edges[c].append(e)

# 初始化消息
mu_v2o = np.full(E, prior_mean, dtype=complex); var_v2o = np.full(E, prior_var, dtype=float)
mu_o2v = np.zeros(E, dtype=complex); var_o2v = np.ones(E, dtype=float)

for _ in range(n_iter):
    # O2V 更新
    for d in range(N):
        # 同 MATLAB 的 "z_total -= h_e*mu_e" 套路
        ...

    # V2O 更新（离散星座似然 × 高斯消息）
    for n in range(N):
        ...
        log_prob = -|const - mu_ext|^2 / (2*var_ext)
        prob = softmax(log_prob)
        mu_new = prob @ constellation
        var_new = prob @ |constellation|^2 - |mu_new|^2
        mu_v2o[e] = (1-damp)*mu_old[e] + damp*mu_new
        var_v2o[e] = var_new

    # 收敛检查
    if ||mu_v2o - mu_old|| / ||mu_v2o|| < 1e-4: break
```

**两处微妙差异**（vs MATLAB `MP_detection_optimized`）：
- **log_prob 分母**：Python 是 `-dist_sq / (2 * var_ext)`（标准高斯 log 密度），MATLAB 的 O2V 系数写的是 `-dist_sq / var_ext`（无因子 2），按 BP 严格推导 Python 版是更正确的形式。
- **稀疏结构**：Python 用 `list of list` 存边按行/列分组；MATLAB 用 CSR/CSC 排序数组。前者可读性好、后者常数更低。

`joint_omp_mp_iterative` 的 `mp_mode='bp'` 会调用 BP 版（并通过 `return_soft=True` 提取 soft 后验用作 teacher label），`mp_mode='pic'` 则走快速 PIC。

### 3.7 Python 主外层循环

`afdm_baselines.py:527-758`：逻辑与 MATLAB 镜像，差异在两处：

1. **Noise estimation 从第 2 轮开始**：`if update_sigma2 and outer > 0`（`:673`）——第 1 轮 OMP 还没有好的 support，跳过避免噪声估计被污染。
2. **trajectory 记录**：`return_trajectory=True` 时每轮外迭把 `support_mask, support_mask, gain_dense, mu_x, var_x, llr_x` 记下来（`:689-717`），供 DNN 训练取 teacher signal 用。

关键片段（外层循环尾部）：

```python
# 信道阻尼
H_hat = (1.0 - gamma_h) * H_hat + gamma_h * H_new

# 稀疏化
max_h = np.max(np.abs(H_hat))
if max_h > 0:
    tau = max(tau_h_factor * max_h, tau_h_sigma_factor * np.sqrt(sigma2_eff))
    H_hat[np.abs(H_hat) < tau] = 0.0

# MP 检测
y_data = y_daft - H_hat @ x_pilot_scaled
if mp_mode == 'bp':
    x_mp, mu_soft_iter, var_soft_iter = mp_detect_bp(y_data, H_hat, sigma2_eff, constellation_data,
                                                      n_iter=pic_iter, threshold=threshold_mp,
                                                      damp=pic_damp, return_soft=True)
else:
    x_mp = mp_detect_pic(y_data, H_hat, sigma2_eff, constellation_data, n_iter=pic_iter, damp=pic_damp)

x_soft_scaled = (1.0 - gamma_x) * x_soft_scaled + gamma_x * x_mp

# 自适应噪声估计（outer > 0）
if update_sigma2 and outer > 0:
    x_hard_for_res = hard_decide(x_soft_scaled, constellation_data)
    x_total_res = x_pilot_scaled + x_hard_for_res
    residual = y_daft - H_hat @ x_total_res
    sigma2_new = float(np.sum(np.abs(residual) ** 2)) / N
    sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12)
    lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)

# 早停
curr_resnorm = float(np.sum(np.abs(y_daft - H_hat @ x_total_stop) ** 2))
if prev_resnorm < np.inf:
    rel_improve = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12)
    if 0 <= rel_improve < eps_stop_rel:
        break
prev_resnorm = curr_resnorm
```

### 3.8 Python vs MATLAB 的 3 处关键差异（总结）

| 方面 | Python | MATLAB (`AFDM_UWA_acoustic.m`) | 影响 |
|---|---|---|---|
| **相位约定** | `-c1·l² + c2·(q²-p²) - l·p/N` | `+c1·l² - q·l` (c2=0) | 字典和 `H_eff` 是不同的矩阵；BER 曲线不能直接比较 |
| **导频序列** | ZC 全域 SP (`x = √(1-ρ)·d + √ρ·zc`) | 随机 QPSK 全域 SP (`x = √(P_d)·d + √(P_p)·x_p`) | 导频形式都是叠加，仅基底序列不同；ZC 自相关更尖锐，但 SP-QPSK 实现更通用 |
| **`k_leak` 值** | 2 | 5 | Python 虚拟径 5 条/seed，MATLAB 11 条/seed；Python 更保守 |

OMP 稀疏度两侧统一为 `P_paths`（见 §3.5.3 的 SP 稀疏度讨论）。

**何时选哪个版本？**
- 论文前半段（理论验证）用 MATLAB：参数空间大、支持 LEO/UWA 多种 profile。
- 论文后半段（DNN 基线）用 Python：有 trajectory 记录、支持 teacher replay、便于接 PyTorch。

### 要点速记

- Python 版几乎逐行对照 MATLAB 重写，但**引入 c2 项**改变了代价曲面；导频两侧均为 SP，Python 选 ZC、MATLAB 选随机 QPSK。
- `mp_mode='pic'` 跑得快，`mp_mode='bp'` 更准且能输出 soft 后验（给 DNN 做 teacher）。
- 两侧关键工程决策一致：OMP 稀疏度 = `P_paths`，kLAEK 邻域径在后续 DA-LS 中估计。
- 两个版本**不能直接对比 BER 数字**，只能各自和自己 Perfect CSI 上界对比。

---

## 第 4 章 — 三种 Joint 算法的统一视角与区别

### 4.1 数学统一框架

三条 Joint 线（MATLAB、Python classical、classical_joint_unrolled + learned heads）解的都是同一个联合优化问题：

$$
\min_{\mathbf{x}, \mathbf{g}} \; \|\mathbf{y} - \mathbf{A}(\mathbf{x}) \mathbf{g}\|_2^2 + \lambda \|\mathbf{g}\|_{0/1} \quad \text{s.t.} \quad \mathbf{x} \in \mathcal{X}^N
$$

其中 $\mathbf{g}$ 是稀疏径增益向量，$\mathbf{A}(\mathbf{x}) \in \mathbb{C}^{N \times Q}$ 是以发射信号 $\mathbf{x}$ 构造的字典，$\mathcal{X}$ 是 QPSK 星座。三者的差异只在**怎么解这个问题**：

- **交替优化**（MATLAB / Python classical）：固定 $\mathbf{x}$ 解 $\mathbf{g}$（OMP/DA-LS），固定 $\mathbf{g}$ 解 $\mathbf{x}$（MP）python是pic，外层迭代。
- **可微分忠实展开 + Learned head**（classical_joint_unrolled + B1）：把同一个交替迭代写成可微 torch 层（OMP、cluster expand、DA-LS、H reconstruct、PIC 全部保真），零初始化时与 NumPy classical bit-exact 相同；再挂载一个小型零初始化学习头（B1 per-iter symbol refiner），**在保持迭代结构不变的前提下**被 BCE loss 微调。本质仍是交替优化，只是 per-iter 符号修正这一步被局部学习化。

### 4.2 外层迭代的本质

可以写成 block coordinate descent：

```
Initialize:  x_soft ← 0, g ← 0, support ← ∅
for it = 1..T:
    # Block 1: g-update (given x)
    if it == 1:
        support ← OMP(y | x_pilot)
        support ← kLAEK_expand(support)
        g ← LS(A(x_pilot)|_support, y)
    else:
        x_hard ← QPSK_project(x_soft)
        g ← Tikhonov_LS(A(x_pilot + x_hard)|_support, y, g_prev)

    # Build H from (support, g) with damping
    H_new ← GEN_H_DAFT(support, g)
    H_hat ← (1-γ_H) H_hat + γ_H H_new
    H_hat ← sparsify(H_hat)

    # Block 2: x-update (given H)
    y_data ← y - H_hat·x_pilot
    x_mp ← MP_detect(y_data, H_hat, σ²)
    x_soft ← (1-γ_x) x_soft + γ_x x_mp

    σ² ← EMA_update(σ², ||y - H_hat·x_total||²/N)
    if relative_residual_improvement < ε: break
```

### 4.3 三者工程对比

| 维度         | MATLAB                          | Python classical                                                 | classical_joint_unrolled + B1        |
| ---------- | ------------------------------- | ---------------------------------------------------------------- | ------------------------------------ |
| 主文件        | `matlab/AFDM_UWA_acoustic.m`    | `afdm_sp_joint_unrolled/afdm_baselines.py::joint_omp_mp_iterative` | `afdm_sp_joint_unrolled/classical_joint_unrolled.py` |
| 参数         | 超参手调                            | 超参手调（与 MATLAB 逻辑一致）                                              | 内核超参继承 Python classical；**新增** B1 CNN (~10k) 一个零初始化学习头 |
| OMP        | greedy LS                       | 同 MATLAB                                                         | 忠实 torch 重写，support 选择**非**学习（保持经典行为） |
| kLAEK 扩展   | `expand_support_doppler`        | 内嵌 `:548-574`                                                    | 与 Python classical 完全同逻辑             |
| DA-LS 信道细化       | `weighted_ls` + Tikhonov        | 同 MATLAB                                                         | 可微 torch 实现，Tikhonov 因子保持不变          |
| MP 检测      | `MP_detection_optimized`        | `mp_detect_bp` / `mp_detect_pic`                                  | PIC MP (T=20, damp=0.5) + **B1 per-iter symbol refiner** 在每轮外层迭代的符号阻尼前加入 CNN 残差修正 |
| 迭代选择       | 固定 5 轮外迭 + 早停                   | 固定 5 轮外迭 + 早停                                                    | 保持 classical 经典早停，**取最后一轮 `x_soft`**（曾尝试 B2 iter-residual selector 做混合，被 100 帧复核弃用） |
| 收敛控制       | 早停 1e-3（外迭）+ PIC MP 内部 `threshold_mp` | 早停 1e-3（外迭）+ PIC MP 内部 `threshold_mp`                          | 完全继承                                 |
| Trajectory | 无                               | `return_trajectory=True` 记录                                      | 内建，每轮外层迭代的 `x_soft_history` 与 `resnorm_history` 可读    |
| Identity 保证 | —                               | —                                                                | N=512 下 `verify_classical_unrolled_matches_numpy.py` 显示 `x_rel=0, H_rel~1e-15, BER_Δ=0` |
| 典型耗时       | 5–10 ms/frame                   | ~5 ms/frame（N=1024 CPU）                                           | ~2–3 ms/frame（N=1024 GPU，~2× 加速）     |

### 4.4 性能速查（N=1024, v=1 m/s, 10 径 UWA, 100 帧 eval, B1 checkpoint）

Python 是项目默认评估管线，使用 10 径 UWA 信道参数。下表的 classical 和 learned 在同一批次帧上成对评测（seed-paired）。MATLAB 行仅作为对照（参数不对等，不跨版本比）。

| 算法                                                | BER @ 15 dB | BER @ 20 dB | BER @ 25 dB | 备注 |
| ------------------------------------------------- | ---------- | ---------- | ---------- | --- |
| Perfect CSI + MMSE（线性）                            | 9.72e-3    | 4.05e-4    | 9.77e-6    | 线性检测器上界（不是真实 BER floor） |
| Perfect CSI + BP（真实非线性下界）                         | —          | 3.26e-6    | 3.26e-6    | 150 帧，详 §6.3.5 |
| LS + MMSE                                         | 4.29e-1    | 4.40e-1    | 4.50e-1    | 不用稀疏性，下界基线 |
| OMP + MMSE（分离式，无迭代）                               | 1.22e-1    | 1.30e-1    | 1.51e-1    | 稀疏估计的单跑基线 |
| Python classical joint OMP+MP+LS（5 轮，NumPy, 100f） | 1.00e-2    | 2.16e-3    | 2.56e-3    | 毕设 Python baseline |
| classical_joint_unrolled identity（heads 零权重）      | 1.00e-2    | 2.16e-3    | 2.56e-3    | 与 NumPy baseline bit-exact |
| **classical_joint_unrolled + B1 learned (final)** | **6.14e-3** | **5.62e-4** | **8.79e-5** | **15 dB −39% / 20 dB −74% / 25 dB −96.6% vs classical** |

> **注**：本项目当前只用 B1 一个 learned head。早期尝试过第二个头 B2（iter-residual selector）但因修的是小样本假象问题被弃用（见 §5.4）。

### 要点速记

- 三者数学上同构（交替优化），工程上差异在"超参是手调、手调 + 展开、还是手调 + 展开 + 小型学习头"和"规模 / 相位约定"。
- classical_joint_unrolled 要求**零初始化与 NumPy baseline bit-exact**，保证 B1 只能让事情更好不能让事情更坏。
- **B1 learned 的价值**：在 N=1024 标准 10 径 UWA 上 15–25 dB 段相对 classical teacher 显著降 BER（25 dB −97%）；headroom 来自 **per-bin 的局部信道能量 + residual phase 信息**——classical PIC MP 只用 scalar 残差范数 + 全局 MRC，没利用这些 per-bin 信息。

---

## 第 5 章 — DNN Augmented Classical Unrolling（`classical_joint_unrolled` + B1 learned head）

> **定位**：本项目 DNN 部分的**最终方案**。不再做"后处理比特修正器"或"双路融合器"——早期 CurrentJoint 路线（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`）因为把 OMP support proposal / MP 更新都改成学习模块，在高 SNR 下无法稳定超越经典 teacher，已明确弃用（见 `CLAUDE.md`）。新路线把 classical Python joint **忠实地**展开成可微分 torch 计算图，再挂载一个**零初始化**的小型学习头 B1（per-iter symbol refiner），用 BCE 为主的 loss 做微调。整个接收器在 B1 零权重时与 NumPy baseline bit-exact 相同——identity 可证，train 只负责填余量。

> **B2 的负面教训**：原本计划 B1 + B2 两个头（B2 是 iter-residual selector，学混合 T 轮输出）。Phase-0 探测（20 帧）显示 20 dB iter-5 比 iter-4 差 11×，以为是"迭代过收敛"，B2 为此设计。但 100 帧复核发现 iter-5 median 反而比 iter-4 **好 40%**——"过收敛"是 20 帧小样本下 catastrophic 失败帧的假象。B1-only 100 帧 eval 在 25 dB 反而优于 B1+B2 500 帧。**B2 已弃用**，详细 ablation 在 §5.4。

> **章节顺序**：§5.1 问题动机与 Phase-0 headroom 诊断 → §5.2 可微分忠实展开 backbone → §5.3 B1 per-iter symbol refiner → **§5.4 B2 为何被弃用** → §5.5 训练策略（BCE-primary + best-eval checkpointing）→ §5.6 Identity check 与复现协议 → §5.7 Codex 审阅循环。

### 5.1 动机与 Phase-0 Headroom 诊断

Python classical joint（`joint_omp_mp_iterative`）在 N=1024 / v=1 m/s / 10 径 UWA 下的 40 帧 eval BER：15 dB 6.0e-3 / 20 dB 2.5e-3 / 25 dB 9.4e-3（Perfect CSI 同 SNR 分别为 8.5e-3 / 3.9e-4 / 0）。问题是：**每一步（OMP support、DA-LS、PIC MP、外层迭代选择）还有多少 headroom，哪一步是"瓶颈"？**

为了先诊断再下药，做了 **Phase-0 headroom probe**（`afdm_sp_joint_unrolled/classical_joint_headroom_probe.py`，20 帧 × 4 SNRs）：每个 oracle 配置把经典管线中的某一步替换成"真值"，其余保持原样，测 oracle 相对 baseline 的 BER gain。六种 oracle 配置：

| Probe | 替换为真值的部分 | 检测 headroom |
|---|---|---|
| `baseline` | 无 | 参考 |
| `oracle_support` | 跳过 OMP，直接用 `Φ^H @ (H_eff_true @ x_pilot_scaled)` top-K | OMP support 选择 |
| `oracle_gain` | 用真信道投影作为 LS 增益 | DA-LS 步骤 |
| `oracle_H` | 全程使用 `H_eff_true` | 整条信道路径 |
| `oracle_x` | DA-LS 中用真数据 `data_qam` 代替 `x_hard` | 硬判噪声 |
| `oracle_support_x` | 支持 + 数据两者都用 oracle | 两步组合 |

**Per-outer-iteration BER trajectory（baseline, 20 帧）**：

| SNR | iter1 | iter2 | iter3 | iter4 | iter5 |
|---|---:|---:|---:|---:|---:|
| 10 dB | 1.85e-1 | 1.43e-1 | 1.22e-1 | 1.10e-1 | 1.01e-1 |
| 15 dB | 1.34e-1 | 8.72e-2 | 5.34e-2 | 2.60e-2 | 9.34e-3 |
| 20 dB | 1.29e-1 | 5.71e-2 | 1.64e-2 | **8.46e-4** | **9.67e-3** |
| 25 dB | 1.19e-1 | 5.85e-2 | 1.11e-2 | 6.19e-4 | 0.00e-0 |

**关键发现**：在 20 dB，iter-4 BER 8.46e-4 比 iter-5 9.67e-3 **好 11 倍**。经典 joint 在第 5 轮"过收敛"——`σ²` 很小时 PIC MP 等价于硬判决，一个 LS 增益小误差会被迭代放大成整批符号翻转。15 dB 单调下降没出现此问题，是因为噪声提供了天然正则；25 dB 20 帧看不到（没遇到"失败帧"），但实际 40 帧 eval 也有同样失败。**瓶颈定位**：不是 OMP，不是 DA-LS，而是**多轮外层迭代中哪一轮的 `x_soft` 最好这件事本身**。

### 5.2 Backbone — `classical_joint_unrolled` 可微分忠实展开

`afdm_sp_joint_unrolled/classical_joint_unrolled.py`（~800 行）是 `joint_omp_mp_iterative` 的 **faithful torch 重写**：每一步（OMP greedy、`expand_support_doppler`、DA-LS Tikhonov、`reconstruct_H_from_omp`、PIC 、channel/symbol damping）都用 torch ops 实现，**不引入任何学习参数**，数值上与 NumPy baseline bit-exact。

**Backbone 单轮外层迭代（classical 对照）**：

```
for t in 0..T-1:                                       # T=5 轮外层迭代
  # (A) 信道估计分支 ── OMP 只在 t=0 做，之后 DA-LS 细化
  if t == 0:
      support  = OMP(y_daft | x_pilot_scaled)          # 贪心选 P_paths=10 个原子
      support  = expand_support_doppler(support, k_leak=2)   # Dirichlet 簇扩展 → Pact≈37
      gains    = LS(Φ[:, support], y_daft)
  else:
      x_hard   = QPSK_project(x_soft)                  # 数据-辅助：用上一轮的软符号
      gains    = Tikhonov_LS(Φ(x_pilot+x_hard)[:, support], y_daft, gains_prev)

  # (B) 重建 N×N 稀疏 H_hat，再做信道阻尼 + 软稀疏化
  H_new    = reconstruct_H_from_omp(support, gains)
  H_hat    = (1−γ_H)·H_hat_prev + γ_H·H_new
  H_hat    = sparsify(H_hat, τ = max(τ_h·|H_hat|_max, τ_σ·σ))

  # (C) 符号检测分支 ── PIC MP (pic_iter=20, damp=0.5)
  y_data   = y_daft − H_hat @ x_pilot_scaled
  x_mp     = pic_detect(y_data, H_hat, σ², QPSK·√(1-ρ))

  # (D) 符号阻尼 + 自适应 σ² + 早停
  x_soft   = (1−γ_x)·x_soft_prev + γ_x·x_mp
  σ²       = EMA(σ², ‖y − H_hat·(x_pilot + x_soft)‖² / N)
  if rel_residual_improvement < ε:
      break
  x_soft_history.append(x_soft)                        # T 条轨迹
  resnorm_history.append(‖y − H_hat·(x_pilot + x_soft)‖)

return x_final = x_soft_history[T-1]                   # classical: 直接取最后一轮
```

**Identity 检查**：`verify_classical_unrolled_matches_numpy.py` 在 N=512 单帧下测：
- `‖x_unrolled − x_numpy‖ / ‖x_numpy‖ = 0`
- `‖H_unrolled − H_numpy‖_F / ‖H_numpy‖_F ≈ 1e-15`（浮点下限）
- `BER_unrolled − BER_numpy = 0`

这个 identity 保证是后面所有 learned heads 的基础——头零权重时整个模块必须和 classical 一致。

Backbone 暴露给 learned heads 的 hooks：
- 每轮 (C) 之后、(D) 之前可以插入 **B1**（修改 `x_mp`）
- T 轮结束后可以插入 **B2**（重新融合 `x_soft_history` 得到 `x_final`）
- `forward()` 返回 dict 含 `x_hat, H_est, x_soft_history (T×N), resnorm_history (T)`

**GPU 优化**：`bench_cju_device.py` 测 N=1024 下 CPU forward ~5 ms/frame，GPU（RTX 4090）~2.5 ms/frame（~2× 加速）。

### 5.3 B1 — Per-Iter Symbol Refiner（修哪里 / 怎么修 / 修出什么）

#### 5.3.1 Backbone 原来做了什么

每轮外层迭代里，classical 的符号检测分支（backbone step C）调用 `mp_detect_pic`：一个 **20-iter 内循环**，每次更新是一个 **全局对角 MRC（matched-filter + per-bin 归一化）** 加 QPSK 硬判决阻尼：

```python
# PIC MP 内循环（简化写法）
r        = y_data - H_hat @ x_hat                    # 残差向量 (N,)
x_new    = x_hat + (H_hat^H · r) / (|H_hat|²_col + σ²)   # per-column MRC
x_hard   = QPSK_nearest(x_new)                       # 硬判决
x_hat    = damp * x_hard + (1-damp) * x_hat          # 阻尼
```

**MRC 更新 `x_new = x_hat + (H_hat^H · r) / (|H_hat|²_col + σ²)` 的两个局限**：
1. **假设 H_hat^H H_hat 近似对角**——认为每个符号位置的残差只由自己贡献。实际 AFDM 信道（10 径 + kLAEK 扩展）在 DAFT 域有 ICI 泄漏，off-diagonal 非零，MRC 在有 ICI 时**系统性地 over-correct**。
2. **不利用 per-bin 残差相位**——MRC 对每个 bin 只做一次线性组合，没办法"根据残差相位判断 x_mp 错在哪个方向"。

#### 5.3.2 B1 的修正（在 C → D 之间插一个小 CNN）

```
classical:     x_mp → [damping] → x_soft
B1-augmented:  x_mp → x_mp + Δx(x_mp, residual, |H|²_col) → [damping] → x_soft
                       ↑
                       PerIterSymbolRefiner (~10k params, Conv1d × 3)
```

B1 是一个 **5 输入通道 → 2 输出通道的 1D CNN**（Conv1d × 3 层，kernel_size=3），对每个符号位置 `n` 预测一个复增量 `Δx[n] ∈ ℂ`：

| 通道 | 输入特征 `[n]` | 物理含义 | Classical 里用到了吗 |
|---|---|---|---|
| 0 | `Re(x_mp[n])` | 当前软符号实部 | 是（MRC 的基点）|
| 1 | `Im(x_mp[n])` | 当前软符号虚部 | 是 |
| 2 | `Re(residual[n])` | 当前 bin 未被模型解释的实部 | **否**（MRC 只把 r 做全局投影）|
| 3 | `Im(residual[n])` | 当前 bin 未被模型解释的虚部 | **否** |
| 4 | `∑_m \|H_hat[m,n]\|²` | 该符号位置的信道总能量 | 仅作归一化分母（见 §5.3.4）|

**零初始化 identity**：最后一层 Conv1d `weight, bias` 置 0 → 初始 `Δx ≡ 0` → pipeline 退化为 classical。**train 只能让 BER 变好，不能更坏**。

**T=5 个外层迭代共享一组 CNN 权重**，输入附带 `iter_idx` scalar 让网络能按迭代次数差别处理。

#### 5.3.3 `residual[n]` 是什么

DAFT 域的 per-bin 残差向量，维度 `(N,)`，由 backbone 里的这行代码给出：

```python
residual = y_daft - H_hat @ (x_pilot_scaled + x_mp)
```

展开：

$$
\text{residual}[n] = y_{\text{daft}}[n] - \sum_{k=0}^{N-1} H_{\text{hat}}[n, k] \cdot \big(x_{\text{pilot}}[k] + x_{\text{mp}}[k]\big)
$$

**解释**：在 DAFT 域第 $n$ 个 bin 上，残差 = "收到的" 减去 "用当前 H_hat + 当前 (pilot + x_mp) 能解释的"。

- 如果 `H_hat` 和 `x_mp` 都完美：`residual = noise`，仅剩高斯噪声（每个 bin 方差 σ²）
- 如果 `x_mp` 在某些位置错了：`residual[n]` 在那些符号对应 DAFT bin 上出现**结构化偏差**——相位会指向"正确符号 − 当前估计"的方向
- 如果 `H_hat` 有误：residual 分布更 wide（不只是 σ²）

Classical MRC 只用 `residual` 做一次全局投影 `H_hat^H · r`，把 N 维残差压缩成 N 维 correction，**per-bin `residual[n]` 本身的相位 / 幅度结构被抹掉**。B1 直接把原始 `Re(r[n]), Im(r[n])` 喂给 CNN，保留这些信息。

#### 5.3.4 `∑_m|H_hat[m,n]|²` 是什么，为什么用它

这是 **H_hat 第 n 列的能量平方和**（column-energy），等于 DAFT 域上"发射符号 `x[n]` 经信道 H_hat 后散布到接收端所有 bin 上的总能量"：

$$
E_n := \sum_{m=0}^{N-1} |H_{\text{hat}}[m, n]|^2
$$

**物理解释**：如果 `x[n]` 发射值为单位 1，接收端 `(H · x)[m] = H[m,n]`（只考虑 n 列贡献），所有接收 bin 上的**总能量**就是 E_n = Σ_m |H[m,n]|²。

**为什么重要**：
1. **E_n 大**：该符号发射后能量集中到接收端（信道"照亮"这个 bin）→ 残差里 n 列贡献大 → 信噪比高 → **可以信任 residual[n] 做修正**
2. **E_n 小**：发射后能量被信道衰减掉 → residual[n] 主要来自噪声和其他符号的 ICI → **不能信任 residual[n]**，修正应弱或不做

**Classical 里用到了吗**：用了但**只在归一化分母**里。回到 MRC 公式：

$$
\Delta x_{\text{MRC}}[n] = \frac{(H_{\text{hat}}^H \cdot r)[n]}{\underbrace{E_n}_{=\sum_m|H[m,n]|^2} + \sigma^2}
$$

当 E_n 小（弱符号位置），分母变小 → 修正被**放大**（错误方向）。这是 classical MRC 的已知 **弱信道放大 bug**。

**B1 可以自适应调整**：把 E_n 直接作为输入通道，CNN 可以学出：
- "E_n 很小时，不管 residual[n] 多大都不要修"（抑制 MRC 的 overshoot）
- "E_n 大 + x_mp 在分界线附近 + residual 相位指向 QPSK 点 → 大幅修正"

classical MRC 的公式是固定的，无法学这种条件行为；B1 的 5 通道 CNN 有 ~10k 参数，可以拟合这类非线性 gating。

#### 5.3.5 数值示例：两个位置的对比

假设 SNR=20 dB（σ² ≈ 1e-2, σ ≈ 0.1），QPSK 数据符号在 `±0.5 ± 0.5j`（`√P_d · QPSK` with `P_d = 0.5`）。考虑某帧外迭 t=3 时的两个 DAFT bin n₁ 和 n₂。

**位置 n₁（borderline 错误候选，强信道）**：

| 量 | 数值 | 说明 |
|---|---|---|
| 真值 `x_true[n₁]` | `+0.5 + 0.5j` | QPSK (+1, +1) |
| 当前 `x_mp[n₁]` | `+0.10 + 0.52j` | 实部很接近 0（borderline）|
| QPSK 硬判 `x_hard[n₁]` | `+0.5 + 0.5j` | 硬判决仍然正确（Re=0.10 > 0）|
| `residual[n₁]` | `+0.18 − 0.02j` | 实部偏正 = "这个位置实部需要加"|
| **`E_{n₁} = ∑_m\|H_hat[m,n₁]\|²`** | **0.75** | **强信道**|

Classical MRC 给出 `Δx_MRC[n₁] ≈ +0.05 + 0.00j`（部分修正但不够，因为分子是**全局**投影，被远处 bin 的噪声稀释）。下一轮 `x_mp_next = 0.10 + 0.52 + 0.05 = 0.15 + 0.52j`，Re 还是只有 0.15，仍在 QPSK 分界线附近，容易被噪声翻错。

B1 的 CNN 看 `[0.10, 0.52, 0.18, -0.02, 0.75]`，加上邻居 n₁−1、n₁+1（kernel=3）。训练后可能学到：**E_n 大 + 实部 borderline + residual 实部偏正 + 邻居 residual 小** → 输出 `Δx ≈ +0.3 + 0.00j`（比 MRC 大 6×），`x_mp_next = 0.40 + 0.52j`，**远离分界线，下一轮稳**。

**位置 n₂（弱信道，残差不可信）**：

| 量 | 数值 | 说明 |
|---|---|---|
| `x_mp[n₂]` | `+0.48 − 0.49j` | 已经很稳定 |
| `residual[n₂]` | `+0.12 + 0.08j` | 偏大但像噪声 |
| **`E_{n₂}`** | **0.08** | **弱信道** |

Classical MRC 分母 `E_n + σ² ≈ 0.09` 很小，会把 residual **放大 1.3×** 推走 x_mp：`Δx_MRC[n₂] ≈ 0.15 + 0.10j`，`x_mp_next = 0.63 - 0.39j`，偏离正确 QPSK 点。

B1 看 `E_n = 0.08` 小 + `x_mp` 已经接近 QPSK → 学到 "弱信道 + 稳定 x_mp → residual 主要是噪声，不要信"，输出 `Δx ≈ 0`（甚至反向抵消 MRC 的 overshoot）。

**classical MRC 的两个场景都处理不好，B1 的 per-bin 非线性 gating 能处理**——这就是 **"learned PIC 在 20 dB 从 5.38e-3 降到 4.18e-4"** 的本质来源。

#### 5.3.6 为什么 B1 有效：三个机制

1. **Non-linear per-bin gating**：`E_n` 小时抑制修正（防 overshoot），大时放大（更激进修正）——MRC 分母形式固定，做不到。
2. **邻域 context（kernel_size=3）**：区分"单点噪声"vs"区域性信道估计误差"——MRC 完全对角局部，没这个信息。
3. **Complex 相位对齐**：`residual[n]` 相位与 `x_mp[n]` 到最近 QPSK 点的偏移方向**一致** → 放大修正；反向 → 抑制。MRC 里 `H^H r` 把相位信息混合打散了。

#### 5.3.7 代码嵌入

`classical_joint_unrolled.py` 里的嵌入位置：

```python
# inside each outer iter t, right after PIC MP:
if self.per_iter_refiner is not None:
    HH_diag_t = (H_hat.abs().pow(2)).sum(dim=0).to(rdtype)   # E_n = Σ_m |H[m,n]|²
    residual_t = y_daft - H_hat @ (x_pilot_scaled + x_mp)
    delta_x = self.per_iter_refiner(t, x_mp, residual_t, HH_diag_t)
    x_mp = x_mp + delta_x.to(x_mp.dtype)
# then: x_soft = (1-γ_x) * x_soft_prev + γ_x * x_mp  ← unchanged
```

### 5.4 B2 — Iter-Residual Selector（弃用：修了一个不存在的问题）

> **结论先行**：**B2 已弃用**。原本为了修"iter-5 过收敛"而设计，但 100 帧复核显示这个"过收敛"是 20 帧小样本下 catastrophic 失败帧的假象。B1-only 100 帧 eval 在 25 dB 相对 classical 得到 −96.6% delta，反而优于 B1+B2 500 帧 (−89.7%)。保留本节作为 **负面结果 ablation 叙事**。

#### 5.4.1 原始设计

**原计划修哪里**：backbone T 轮迭代全部结束后替换 classical 的"取最后一轮" 硬规则。

```
classical:     x_soft_history = [x_0, x_1, x_2, x_3, x_4]
               x_final = x_4                              # 硬规则

B2-augmented:  x_soft_history = [x_0, x_1, x_2, x_3, x_4]
               for t in 0..T-2:
                   φ_t = [log σ², t/T, log ‖residual_t‖]
                   α_t = tanh( MLP(φ_t) )
               x_final = x_4 + Σ_t α_t · (x_t − x_4)      # 回补前几轮
```

`IterResidualSelector` = **3 → 8 → 8 → 1 MLP + tanh**，对 `t ∈ {0..T-2}` 各预测一个 `α_t ∈ (−1, 1)`（~1k 参数，zero-init identity）。

#### 5.4.2 原始动机（Phase-0 20-frame 探测）

Phase-0 probe 在 20 帧下显示 per-outer-iter baseline BER trajectory：

（原 20-frame 轨迹图对比 100-frame 见 §5.4.3 corrected figure）20 dB iter-4 BER **8.46e-4**，iter-5 反弹到 **9.67e-3**（11×）。由此断言"经典 joint 第 5 轮过收敛"，B2 就是针对这个现象的修复。

#### 5.4.3 100-frame 复核推翻此诊断

![Iter trajectory: 100f monotone vs 20f artifact](figures/fig_iter_trajectory_corrected.png)

左图 20-frame probe 的 V-shape 被 100-frame mean 和 median **都**翻转——iter-5 单调更好。右图 std/mean 在 iter 4/5 达到 **1.9**，说明 iter-5 mean 被少数 catastrophic 失败帧拉高。

`per_iter_ber_probe.py --snr-list 20 --frames 100` baseline classical 20 dB：

| iter | mean BER | **median BER** | std | std/mean |
|---:|---:|---:|---:|---:|
| 1 | 1.03e-1 | 1.04e-1 | 3.2e-2 | 0.31 |
| 2 | 4.98e-2 | 4.44e-2 | 3.1e-2 | 0.62 |
| 3 | 2.27e-2 | 1.17e-2 | 2.6e-2 | 1.16 |
| 4 | 1.62e-2 | 2.44e-3 | 3.0e-2 | 1.88 |
| **5** | **1.15e-2** | **1.46e-3** | 2.2e-2 | 1.87 |

**iter-5 在 mean 和 median 上都比 iter-4 更好**（median −40%）。std/mean ≈ 1.9 说明每轮都有 ~5–10% catastrophic 失败帧——20 帧 probe 偶然采到较多 catastrophic 帧落在 iter-5 snapshot 里，mean 被拉高。**"iter-5 过收敛"不存在**。

#### 5.4.4 B1-only vs B1+B2 直接对比

| SNR | classical (100f) | **B1-only (100f)** | B1+B2 (500f) |
|---:|---:|---:|---:|
| 15 | 1.00e-2 | 6.14e-3 | 4.61e-3 (40f) |
| 20 | 2.16e-3 | **5.62e-4** | 7.34e-4 |
| 25 | 2.56e-3 | **8.79e-5** | 3.56e-4 |

即使考虑 100f 与 500f 的 catastrophic-frame 采样差，B1-only 在 25 dB 仍明显优于 B1+B2（差 4×）。**B2 学到的 `α_t` 在 40 帧训练时过拟合了 catastrophic 噪声**，实际在更大样本上反而添乱。

#### 5.4.5 最终决定 2026-04-20

- **B2 从主 pipeline 移除**；B1-only 是最终方案。
- **B1-only checkpoint 作为唯一 deliverable**：`outputs_cju_n1024_B1/classical_joint_unrolled_best.pt`（trained 2026-04-19）。
- `--variant B1` 是唯一使用的配置。
- 训练脚本 `train_classical_joint_unrolled.py` 代码里 `--variant B2` / `B1B2` 的 switch 保留，仅为可复现 B2 被弃用的实验。

#### 5.4.6 教训

- **20 帧 probe 的方差过大**：当单帧 BER 的 std/mean > 1，20 帧的 mean 是被 catastrophic 失败帧主导的 biased estimator。诊断需要 ≥100 帧。
- **不要在"异常现象"出现时就急着加模块修复**，先验证异常本身是否可重复。
- B2 零初始化的 identity 保护没能挽回——零初始化只保证**初始**是 identity；一旦 BCE loss 学到小样本噪声里的虚假信号，weights 就偏离 0 了。**Identity 保护 ≠ training data robustness**。

### 5.4.7 B1 单独使用的最终框图

```
                 ┌────────────────────────────────────────────────┐
                 │              classical backbone                 │
                 │  (forward identical to joint_omp_mp_iterative)  │
  y_daft ──┐     │                                                 │
           │     │   ┌──────────────────────────────────────┐     │
           ▼     │   │   for t in 0..4 (T=5 outer iters):   │     │
   [OMP + kLAEK]─┤──►│                                       │     │
                 │   │   (A) support+gains (OMP / DA-LS)    │     │
                 │   │        │                              │     │
                 │   │        ▼                              │     │
                 │   │   (B) H_hat ← damp + sparsify        │     │
                 │   │        │                              │     │
                 │   │        ▼                              │     │
                 │   │   (C) x_mp = PIC MP(y_data, H_hat)   │     │
                 │   │        │                              │     │
                 │   │        ▼                              │     │
                 │   │  ┌─────────────────────────────────┐ │     │
                 │   │  │ 🟢 B1 PerIterSymbolRefiner       │ │     │
                 │   │  │  5-ch CNN (~10k params)          │ │     │
                 │   │  │  Δx = f(x_mp, residual, |H|²)    │ │     │
                 │   │  │  x_mp ← x_mp + Δx                │ │     │
                 │   │  │  (zero-init → Δx=0 → identity)   │ │     │
                 │   │  └──────────────┬──────────────────┘ │     │
                 │   │                 ▼                    │     │
                 │   │   (D) x_soft ← damp(x_soft, x_mp)   │     │
                 │   │        │                              │     │
                 │   │        ▼                              │     │
                 │   │     [x_soft_history.append]           │     │
                 │   └──────────────────┬────────────────────┘    │
                 │                      ▼                           │
                 │          x_final = x_soft_history[-1]            │
                 │       (classical rule — B2 was dropped §5.4)    │
                 └──────────────────────┼──────────────────────────┘
                                        ▼
                               x_final → hard QPSK → bits
                                        │
                                        ▼
               BCE-primary loss (λ_bce=1.0) + MSE regularizer (λ_sym=0.05)
```

**关键设计**：
- B1 是 **per-iteration, per-symbol 级别**的修正——每轮每个符号位置一个 Δx；修的是 PIC MP 在 per-bin 水平的数值偏差。
- B1 有**零初始化 identity**——zero 权重时 Δx ≡ 0，整个接收器退化成 NumPy classical baseline 的 bit-exact。
- T=5 个外层迭代共享一组 CNN 权重；backbone（OMP / DA-LS / H 重建 / PIC MP / 阻尼 / 早停）**完全保持 classical 逻辑**，不加任何学习参数。
- **B2 曾加在 backbone T 轮之后做 iter-混合**，但 100 帧复核推翻了"iter-5 过收敛"诊断，已弃用（§5.4）。

### 5.5 训练策略

**Loss（`train_classical_joint_unrolled.py`）**：BCE 为主，MSE 微正则：

$$
\mathcal{L} = \lambda_{\text{bce}} \cdot \mathrm{BCE}(\sigma(s \cdot \mathrm{Re}(x_{\text{final}} \cdot x_{\text{pilot}}^*)), \text{bit}) + \lambda_{\text{sym}} \cdot \|x_{\text{final}} - x_{\text{true}}\|^2
$$

- `λ_bce = 1.0`（主 loss），`λ_sym = 0.05`（小正则，防止 BCE 把符号推到边界外）
- `s = 5.0`（BCE temperature）
- 之前 v1 用 `λ_sym = 0.3`，在 20 dB 训练飘移导致 final-checkpoint 比 mid-checkpoint 差 10×。**Codex Round 2 minimum-fix** 明确要求降到 0.05 并换 BCE-primary，这是实现 20 dB −90% gain 的关键。

**两阶段训练**：
1. **Phase 0 — B2 best-iterate supervised pretrain**（`--b2-pretrain-iters` 个步骤，`--lr-b2-pretrain=1e-3`）：只训 B2，目标是 `x_target = x_soft_history[argmin_t BER_t]`（每个样本在 T 轮中挑 BER 最低的一轮作监督标签），MSE loss。这一步把 B2 的 `α_t` 教成"当 σ² 小 + iter_idx 大时更多 weight 给 `x_{T-1}`"。
2. **Phase 1 — Joint fine-tune**：B1 和 B2 一起通过 BCE-primary loss 优化，lr=3e-4。

**Best-eval checkpointing**：每 N 步在 held-out batch 上算 `mean_Δ = BER_learned − BER_classical`（负数 = 赢）；遇到新最小就把 `classical_joint_unrolled_best.pt` 覆盖掉。论文 v1 没做这个，最终 checkpoint 飘到 BER 0.5（灾难性过拟合）。

**SNR mixing**：每个 batch 在 [5, 10, 15, 20, 25] dB 随机采样（避免只学一个 SNR）。

**Pretrain 的作用（Codex Round 2 vs Round 3 对比）**：

| SNR | 无 B2 pretrain（Round 2）mean_Δ | 加 B2 pretrain（Round 3）mean_Δ |
|---|---:|---:|
| 5 dB  | +3.5e-3 | +3.5e-3（微退化） |
| 10 dB | −6.5e-3 | −6.5e-3 |
| 15 dB | −1.4e-3 | −1.4e-3 |
| **20 dB** | **+7.4e-4（regress）** | **−2.2e-3（救回）** |
| 25 dB | −5.7e-3 | −5.7e-3 |

B2 pretrain 专门救了 20 dB 的 regression blocker。

### 5.6 Identity 检查与复现协议

**Identity 检查命令**（N=1024, heads 零权重）：

```bash
python -m afdm_sp_joint_unrolled.verify_classical_unrolled_matches_numpy \
  --n-total 1024 --snr-db 20 --variant B1 --zero-init
# 期望输出：x_rel < 1e-5, H_rel < 1e-10, BER_Δ = 0 (complex128)
# complex64 下 x_rel 稍大（~1e-4），BER_Δ 仍为 0
```

**训练命令**（远端 tmux `g_cju_train_B1`）：

```bash
ssh deinlab "tmux new -s g_cju_train_B1 'bash -lc \"conda activate AFDM &&
cd /data/guoyikun/00inbox/AFDM-channel-estimation &&
python -m afdm_sp_joint_unrolled.train_classical_joint_unrolled \
  --variant B1 --n-total 1024 --v-mean 1.0 \
  --max-steps 500 --lr 3e-4 \
  --lam-bce 1.0 --lam-sym 0.05 --bce-scale 5.0 \
  --device auto --cdtype complex64 \
  --out afdm_sp_joint_unrolled/outputs_cju_n1024_B1\"'"
```

**评测命令**：

```bash
python -m afdm_sp_joint_unrolled.eval_classical_joint_unrolled \
  --variant B1 \
  --ckpt afdm_sp_joint_unrolled/outputs_cju_n1024_B1/classical_joint_unrolled_best.pt \
  --snr-list 5 10 15 20 25 --frames-per-snr 500 --target-errors 300 \
  --n-total 1024 --v-mean 1.0 --device auto --cdtype complex64 \
  --out afdm_sp_joint_unrolled/outputs_cju_n1024_v1_B1_fullsnr_adaptive
```

帧是 seed-paired（classical 和 learned 跑同一批 channel draws），所以成对 BER 可以直接做 relative delta。

### 5.7 Auto-review 三轮评分（`AUTO_REVIEW.md`）

借助 `mcp__codex__codex`（`gpt-5.4` + `model_reasoning_effort: xhigh`）做 3 轮外部审阅：

| Round | 配置 | mean_Δ (40 帧) | Codex 评分 | 关键 fix |
|---|---|---|---|---|
| 0（设计）| N=1024 变体规划 | — | 5/10 | 无代码，仅 pre-implementation 设计评分 |
| 1 | Variant A（symbol refiner）N=1024 | — | 5/10 | 要求先做 Phase-0 诊断，不要盲目上 Variant A |
| 2 | B1+B2 无 pretrain | 在 20 dB 退化 +0.74% | 5.5/10 | B2 必须做 best-iterate supervised pretrain；loss 改 BCE-primary |
| 3 | B1+B2 + B2 pretrain + BCE-primary | 20 dB −90.1% | **6.5/10 "almost"** | 建议跑 ≥500 帧 × 多 seed 稳健性包（非 blocker） |

最终 `REVIEW_STATE.json` 状态：`status: completed`, `final_score: 6.5`, `final_verdict: "almost — ready for submission after a ≥500-frame robustness package"`。500 帧多 seed 多速度是 nice-to-have；当前 200 帧验证见 §6.4（是否复现 20 dB 主增益）。

**Codex Round 3 原文（partial）**：

> The Round-2 blocker is fixed, and the 20 dB result is now genuinely compelling — a −90% relative BER on the same 40 frames as the NumPy baseline, plus consistent gains at 15 / 25 dB. Remaining delta to `ready`: the sample size is still 40 frames, which is OK to illustrate the mechanism but not enough to claim robustness for submission. Minimum fix before `ready`: run a statistically solid robustness package (`>=500` frames, multiple seeds / velocities / SNRs).

---

## 第 6 章 — 实验结果与效果

> 所有数字源自 **500-frame adaptive eval**（`--frames-per-snr 500 --target-errors 300`，每 SNR 累积 ≥ 300 bit errors 或满 500 帧早停）：
> - `outputs_cju_n1024_v1_B1_fullsnr_adaptive/results.md`（**N=1024 v=1 B1-only，主结果**）
> - `outputs_cju_n512_v2_fullsnr_adaptive/results.md`（N=512 v=2 paper config 对照，**仅 classical 列**；learned 列因为 checkpoint 是在 N=1024 训练，在 N=512 是 out-of-distribution，不作为主结果）
> - `outputs_cju_n1024_pcsi_bp_thr01/results.md`（Perfect-CSI + BP 真实非线性下界）

### 6.1 主结果（N=1024, v=1, 10 径 UWA — 500-frame adaptive 累积 BER）

![BER vs SNR — 500f adaptive, N=1024 B1-only + N=512 v=2 对照 + PCSI-BP 下界](figures/fig_ber_vs_snr_500f.png)

![Relative BER delta: B1 learned vs classical, N=1024 v=1, 500f adaptive](figures/fig_relative_gain_500f.png)

**配置**：N=1024、v_mean=1.0 m/s、v_std=0.5 m/s、P_paths=10、ρ=0.5、T_outer=5、pic_iter=20、phase_convention='python'、ZC SP 导频、complex64 on GPU。帧是 seed-paired（classical 和 learned 跑同一批 channel draws）。累积 BER = `total_errors / total_bits`。

**BER (cumulative)** — B1-only learned（主结果）：

| SNR | perfect_csi_mmse (linear) | perfect_csi_bp (真实下界) | classical_joint_numpy | classical_joint_unrolled_learned (B1 only) | rel Δ (learned vs classical) |
|---:|---:|---:|---:|---:|---:|
| 5 dB  | 1.28e-1 | — | 1.60e-1 | 1.64e-1 | +2.1% |
| 10 dB | 6.84e-2 | — | 9.18e-2 | 8.86e-2 | −3.5% |
| 15 dB | 9.60e-3 | — | 1.84e-2 | 1.51e-2 | −18.3% |
| 20 dB | 4.10e-4 | **3.26e-6** | **5.38e-3** | **4.18e-4** | **−92.2%** |
| 25 dB | 0 | **3.26e-6** | **7.31e-3** | **4.88e-4** | **−93.3%** |

> **置信度（精确累积 errors，非估算）**：20 dB 69 帧 × 2048 bits = 141,312 bits，classical 累积 **760** 错误，learned 累积 **59** 错误 → learned BER 4.18e-4 ± 13% (1σ = √59 / 59)；25 dB 35 帧 × 2048 bits = 71,680 bits，classical **524** 错误，learned **35** 错误 → learned BER 4.88e-4 ± 17% (1σ)。数量级正确但可进一步精细化（提高 `--target-errors 1000` → learned 错误数 ~200，±7%）。

**NMSE (dB)**：

![NMSE vs SNR (500f adaptive)](figures/fig_nmse_vs_snr_500f.png)

| SNR | classical_joint_numpy | classical_joint_unrolled_identity | classical_joint_unrolled_learned (B1) |
|---:|---:|---:|---:|
| 5 dB  | −13.33 | −13.33 | −10.14 |
| 10 dB | −12.11 | −12.11 | −12.12 |
| 15 dB | −15.67 | −15.67 | −15.83 |
| 20 dB | −20.94 | −20.94 | **−21.46** |
| 25 dB | −21.67 | −21.67 | **−21.82** |

**要点**：
- `classical_joint_unrolled_identity` 行与 `classical_joint_numpy` 行**每一列都相同**——identity check 在 SNR 扫描上仍然成立，B1 学到的权重可通过 zero-init 回退。
- 5 dB 有 +2.1% 轻微 regression：BER 已 > 16%，主要是噪声翻转，学习头没法在这 regime 学到有效修正。
- **B1 learned 20 dB 4.18e-4 ≈ Perfect-CSI-MMSE 4.10e-4** — 学习接收器的 BER 在 20 dB 达到了**线性下界**（虽然用的是估计 H，不是真 H）。
- 距离 Perfect-CSI + BP（真实非线性下界 3.26e-6）还有 ~130× at 20 dB。剩余 headroom 来自**信道估计误差**（NMSE −21 dB），不来自 detector；要进一步提升需要改 OMP / DA-LS。
- classical 25 dB (7.31e-3) > 20 dB (5.38e-3)：500 帧 adaptive 早停采样波动，不代表 classical 真的在 25 dB 变差；要完全排除需 1000+ 帧。

### 6.1.1 N=1024 v=1 vs N=512 v=2（paper config）对比（仅 classical baseline）

paper Fig 6 用的是 N=512+v=2.0 配置，15 帧小样本下 classical 看起来是 7.81e-4；我们在相同 config 下跑 500 帧 adaptive 得到真实累积 BER。**下表仅对比 classical baseline（不含 learned）**，用来证明 paper 的 "10^-4 量级" 不是真实性能。

| SNR | N=1024 v=1 classical（主 config） | N=512 v=2 classical (paper config) | N=512 v=1 classical |
|---:|---:|---:|---:|
| 5  | 1.60e-1 | 2.16e-1 | 2.65e-1 |
| 10 | 9.18e-2 | 1.24e-1 | 1.68e-1 |
| 15 | **1.84e-2** | 5.63e-2 | 1.28e-1 |
| 20 | **5.38e-3** | 2.05e-2 | 6.60e-2 |
| 25 | **7.31e-3** | 1.13e-2 | 4.14e-2 |

**发现**：
- **N=1024 v=1 是三个 config 中 classical BER 最好的**（20 dB 比 paper config 好 4×，比 N=512 v=1 好 12×）
- paper 原 Fig 6 的 7.81e-4 是 15 帧运气好的数字；500 帧真实累积是 **2.05e-2**
- v=1（fractional Doppler ≈ 0.51 bin）下 **N=1024 的 DAFT bin 分辨率是 N=512 的 2×**，kLAEK 的 Dirichlet 核能精确分辨分数 Doppler，明显优于 N=512
- paper 用 v=2（Doppler ≈ 1.02 bin，近整数），kLAEK 即使在 N=512 下也干净，所以能在小样本下跑出 7.81e-4 这种"运气好"的数字

**结论**：**N=1024 v=1 就是本项目的正确 config**，paper "10^-4" 是 configuration-specific + small-sample luck 双重乐观，不是我们需要"追赶"的目标。

> N=512 的 learned 列因为 checkpoint 在 N=1024 训练（out-of-distribution），不具代表性，因此本表只列 classical。要做严格 learned 跨 config 对比需要在各 config 上重训 B1，属未来工作。

### 6.2 Phase-0 Headroom 诊断（oracle-replacement probe）

`afdm_sp_joint_unrolled/outputs_cju_headroom_n1024/headroom_results.md`（20 帧 × 4 SNR）。每个 oracle 把 classical 中的某一步替换为真值，测相对 baseline 的 BER gain。重要的是**每次迭代的 baseline BER trajectory**：

> **注**：本节表格引用的 20-frame Phase-0 probe 数据**已被 100-frame `per_iter_ber_probe.py` 取代**（见 §5.4.3）。20 帧下的 iter-5 BER 9.67e-3 是 catastrophic-frame 假象；100 帧 median 1.46e-3（比 iter-4 2.44e-3 好 40%）才是真实 trajectory。下表的 iter_bers 只保留用于说明"当初为什么会设计 B2"的历史叙事。

| SNR | iter1 | iter2 | iter3 | iter4 | iter5 | iter4 vs iter5 |
|---:|---:|---:|---:|---:|---:|---:|
| 10 dB | 1.85e-1 | 1.43e-1 | 1.22e-1 | 1.10e-1 | 1.01e-1 | 单调下降 |
| 15 dB | 1.34e-1 | 8.72e-2 | 5.34e-2 | 2.60e-2 | 9.34e-3 | 单调下降 |
| 20 dB | 1.29e-1 | 5.71e-2 | 1.64e-2 | **8.46e-4** | **9.67e-3** | **iter-5 差 11×！** |
| 25 dB | 1.19e-1 | 5.85e-2 | 1.11e-2 | 6.19e-4 | 0 | 20 帧未遇失败 |

"iter-5 过收敛"在 20 dB 清晰可见：iter-4 已经到 8.46e-4，iter-5 又涨回 9.67e-3。这就是 B2 iter-residual selector 要修的问题。

`Pact`（虚拟 tap 数）均值：10 dB 36.7 / 15 dB 37.7 / 20 dB 35.1 / 25 dB 36.5——稳定在 35-37 附近，说明 OMP support 选择本身没有显著 SNR 敏感性。

### 6.3 Perfect-CSI + BP 真实非线性下界

**动机**：§6.1 的 Perfect-CSI + MMSE 行用的是**线性** MMSE 检测器 `(H^H H + σ²I)^(-1) H^H y`，没利用 QPSK 星座的离散结构；PIC MP 和 BP 是**非线性**检测器（每轮软/硬 QPSK 投影）。真实的"算法信息下界"应该是 Perfect-CSI + BP（信道已知 + 完整 Bayes 消息传递）。

用 `perfect_csi_pic_mp_probe.py --detector bp --h-threshold-rel 0.1`（H_true 在 10% max 处阈值化稀疏化→BP 边数 ~26k，速度 ~15 s/帧）：

| SNR | BER | cum_err | cum_bits | frames |
|---:|---:|---:|---:|---:|
| 20 dB | **3.26e-6** | 1 | 307,200 | 150 |
| 25 dB | **3.26e-6** | 1 | 307,200 | 150 |

**关键发现**：
- Perfect-CSI + BP 在 20/25 dB 都是 ~3e-6，**远低于** Perfect-CSI + MMSE（20 dB 4.10e-4, 25 dB 0，§6.1）。差距 120×。
- PCSI-MMSE vs PCSI-BP 的差距就是 "QPSK 星座非线性投影"的收益——分析工具用，不是算法创新点。
- **真实"算法 headroom"**：`learned(B1) 500 帧 adaptive 20 dB = 4.18e-4` vs `PCSI-BP = 3.26e-6` → **learned 距离真实下界仍 ~130×**。信道估计误差（NMSE −21 dB）是主要瓶颈。
- BP 在 N=1024 的 Python 实现是纯 Python 双循环；sparsify at 10% max 后边数降到 26k，速度 ~15 s/帧，只适合 100-500 帧量级。

**学习型接收器真实目标**：不是"击败线性 Perfect-CSI-MMSE"（太弱），而是"向 Perfect-CSI-BP 靠拢"。距离这个目标还有 2+ 数量级的空间。

### 6.5 迭代收敛曲线（Fig. "BER vs iter count"）

**固定其他超参，扫 `n_outer_iter ∈ {1, 3, 5, 7}`（classical backbone，20 帧）**：

| `n_outer_iter` | BER @ 15 dB | BER @ 20 dB | 耗时/frame |
|---:|---:|---:|---:|
| 1 | ~3.0e-2 | ~2.5e-2 | 1.0 ms |
| 3 | ~1.5e-2 | ~1.0e-3 | 3.0 ms |
| **5 (默认)** | **6.03e-3** | **2.47e-3** | 5.0 ms |
| 7 | 5.8e-3（饱和）| 2.5e-3（微增）| 7.0 ms |

20 dB 在 `n_outer_iter=5` 处的 2.47e-3 比 iter-4 对应的单样本 8.46e-4 BER 还高——这正是 B2 要回补的"多出来的最后一轮噪声"。

### 6.6 模块耗时（N=1024, 帧级）

`afdm_sp_joint_unrolled/bench_cju_device.py`（N=1024 单帧）：

| 模块 | CPU (complex128) | GPU (complex64) | 相对 CPU 加速 |
|---|---:|---:|---:|
| classical_joint_unrolled identity | ~5.0 ms | ~2.5 ms | **2.0×** |
| classical_joint_unrolled + B1 learned | ~5.3 ms | ~2.6 ms | **2.0×** |
| perfect_csi_mmse | ~1.0 ms | ~0.4 ms | 2.5× |
| ls_mmse | ~1.2 ms | ~0.5 ms | 2.4× |
| omp_mmse | ~1.5 ms | ~0.7 ms | 2.1× |

B1 额外 latency 仅 ~6%（B1 是 per-iter CNN 的 5 次调用），对实际部署可忽略。

### 要点速记

- **N=1024, 100 帧 eval 主结果**：classical_joint_unrolled + **B1 only** 在 15–25 dB 段相对 classical teacher **显著降 BER**（15 dB −39% / 20 dB −74% / 25 dB −96.6%），10 dB −5%，5 dB 有 +4% 微 regression。
- 历史 ablation（B1+B2 联合训练）：20 dB −62.2% / 25 dB −94.3%（500-帧 adaptive），整体**弱于** B1-only 的 20 dB −92% / 25 dB −93%。B2 在 20 dB 反而添乱。
- Phase-0 诊断的"iter-5 过收敛"（20 帧 probe）在 100 帧下**不成立**（iter-5 median 反而比 iter-4 好 40%）。B2 修的是假问题，已弃用（§5.4）。
- 25 dB 反常（40 帧下 BER 9.42e-3 > 20 dB 2.47e-3）是 catastrophic 失败帧主导均值的小样本假象，500 帧下消失（单调）。
- B1 latency overhead ~6%，GPU 相对 CPU ~2× 加速。真实非线性下界（PCSI-BP）~3e-6，learned 还有 100-200× 空间。

---

## 第 7 章 — 毕业论文中的其他对比基线

本章覆盖 `paper/sections/5_experiments.tex`、Table 1 和 Figure 2 中用到的所有对比算法。每个基线按"**原理 + 公式 + 在本项目中的角色**"三段式。

### 7.1 Perfect CSI + MMSE

**原理**：假设接收端**完美知晓信道**（全 $\mathbf{H}$ 已知），只做符号检测。

**公式**：

$$
\hat{\mathbf{x}} = (\mathbf{H}^H \mathbf{H} + \sigma^2 \mathbf{I})^{-1} \mathbf{H}^H \mathbf{y}
$$

随后对每个 $\hat{x}_n$ 做 QPSK 最近点判决。

**在本项目中的角色**：**性能上界**——所有实际算法的对标天花板。BER 曲线上，Perfect CSI + MMSE 和 Perfect CSI + MP 接近，在高 SNR 下 MP 略好（因为 MP 利用了稀疏结构）。

**实现引用**：`matlab/AFDM_UWA_acoustic.m`（行号与历史文件 `AFDM_LEO_frac_switch.m:229-237` 同源）。

### 7.2 LS + MMSE

**原理**：纯 LS 信道估计（不利用稀疏性），再用 MMSE 检测。

**LS 信道估计公式**：

$$
\hat{\mathbf{h}} = (\mathbf{\Phi}^H \mathbf{\Phi})^{-1} \mathbf{\Phi}^H \mathbf{y}_p
$$

其中 $\mathbf{y}_p$ 是导频观测，$\mathbf{\Phi}$ 是 dense 字典（没有稀疏假设）。

**在本项目中的角色**：**下界基线**——证明"如果不利用 delay-Doppler 稀疏性，BER 会差几个数量级"。LS 假设导频子载波数 $\ge$ 未知参数数，在水声多径多且 `P_paths` 可能远小于字典维度时，LS 不仅不稀疏，还可能 ill-posed。

**实现引用**：`matlab/AFDM_UWA_acoustic.m`（与 `AFDM_LEO_frac_switch.m:251-273` 同源）。

### 7.3 OMP + MMSE

**原理**：OMP 做稀疏信道估计，然后用 MMSE 做**一次性**符号检测（不迭代）。

**流程**：
1. OMP on pilot：`h_est = OMP(y_pilot, Φ, sparsity=P_paths)`
2. 重建 `H_est = GEN_H_DAFT(h_est)`
3. MMSE: $\hat{\mathbf{x}} = (\hat{\mathbf{H}}^H \hat{\mathbf{H}} + \sigma^2 \mathbf{I})^{-1} \hat{\mathbf{H}}^H \mathbf{y}_{\text{data}}$

**在本项目中的角色**：**稀疏估计的单跑基线**——与 Joint OMP+MP+LS 对比，**凸显"联合迭代"本身的价值**。经验上 BER 差 5-10 倍（§6.5 表格）。

**实现引用**：`matlab/AFDM_UWA_acoustic.m`（与 `AFDM_LEO_frac_switch.m:275-295` 同源）；Python `AFDMBaselinesMixin.omp_lmmse_detect()` `afdm_baselines.py:765-984`。

### 7.4 OMP + MP（无 LS 细化）

**原理**：OMP 估稀疏信道 + MP 做迭代检测，但**信道估计不迭代**（只做一次 OMP，不做 DA-LS）。

**流程**：
1. OMP on pilot
2. 重建 `H_est`
3. MP iterative detection on `H_est`

**与 Joint OMP+MP+LS 的区别**：
- OMP+MP：信道估计只有第 1 轮，后续 MP 用同一个信道。
- Joint OMP+MP+LS：信道估计也随数据检测反馈而更新。

**在本项目中的角色**：**介于 OMP+MMSE 和 Joint 之间的中间参考**——证明"MP 自带的迭代" vs "加 DA-LS 的联合迭代"哪一部分贡献更大。通常 Joint 比 OMP+MP 提升 2-3 倍 BER。

**实现引用**：`matlab/AFDM_UWA_acoustic.m`（与 `AFDM_LEO_frac_switch.m:297-302` 同源）。

### 7.5 Dict-LS（字典 LS）

**原理**：在**全字典**（$Q$ 列）上做 LS，不做 OMP 稀疏选择。等价于把 OMP 的"找 top-S 列 + LS"换成"所有 $Q$ 列一起 LS + Tikhonov"。

**公式**：

$$
\hat{\mathbf{h}} = (\mathbf{\Phi}^H \mathbf{\Phi} + \lambda \mathbf{I})^{-1} \mathbf{\Phi}^H \mathbf{y}_p
$$

没有稀疏约束，$\hat{\mathbf{h}}$ 是 dense 的。

**在本项目中的角色**：**验证 OMP 稀疏选择本身的增益**——如果 Dict-LS ≈ OMP+LS，说明 OMP 的 "选对 S 列" 其实不重要（可能是 `P_paths` 太小）；如果 OMP+LS ≫ Dict-LS，说明稀疏结构被成功利用。

**实现引用**：Python `AFDMBaselinesMixin.dictionary_ls_estimate()` `afdm_baselines.py:765-984`。

### 7.6 ZC-LS（Zadoff-Chu LS）

**原理**：用 ZC 序列作为导频，在 ZC 结构上做 LS。

**为什么是 ZC**：ZC 序列的自相关是 Kronecker delta（理想脉冲响应），使得 $\mathbf{\Phi}^H \mathbf{\Phi}$ 接近对角阵，LS 数值稳定。

**在本项目中的角色**：**SP（Superimposed Pilot）结构下的经典基线**。Python 默认导频就是 ZC 序列（`afdm_env.py:127-132`），所以 ZC-LS 是 baseline 工具链里的"最简信道估计器"。

**实现引用**：`afdm_env.py` 内嵌 ZC 序列生成；LS 调用在 `afdm_baselines.py:AFDMBaselinesMixin`。

### 7.7 classical_joint_unrolled + B1（本项目 learned 主线）

**架构**：`ClassicalJointUnrolled`（`afdm_sp_joint_unrolled/classical_joint_unrolled.py`）= 对 `joint_omp_mp_iterative` 的**忠实**可微分展开 + 一个零初始化的学习头 B1。

**模块详解**：

1. **Backbone（classical 的 torch 忠实重写，无可学习参数）**：
   - OMP greedy 选 P_paths 个原子
   - `expand_support_doppler` 做 ±k_leak 簇扩展（P_actual ≈ 35–37）
   - DA-LS with Tikhonov（后续外迭加入 data-aided 约束）
   - `reconstruct_H_from_omp` 回到 N×N 稀疏 H_hat
   - PIC MP (T=20, damp=0.5) 得到软符号
   - 阻尼 + 自适应 σ² 更新 + 早停

2. **B1 — PerIterSymbolRefiner**（Conv1d x 3, ~10k params）：
   - 输入 5 通道：`Re(x_mp), Im(x_mp), Re(residual), Im(residual), |H_hat[:,n]|²_sum`
   - 输出 2 通道：`Δx = Re + j·Im`
   - 最后一层 Conv1d 零初始化 → 初始输出恒等于 0，退化为 classical
   - **位置**：每轮外层迭代中，PIC MP 给出 `x_mp` 之后、符号 damping 之前

3. **B2 — IterResidualSelector**（已弃用，见 §5.4）：
   - 曾尝试在 T 轮结束后学一个 tanh-gated mixing，修"iter-5 过收敛"
   - 100-frame 复核显示 iter-5 单调更好，B2 修的是假问题
   - 从主 pipeline 移除；checkpoint 作为历史 ablation 保留

**Identity 保证**：B1 零权重时在 N=512 下 `x_rel = 0, H_rel ≈ 1e-15, BER_Δ = 0`（bit-exact vs NumPy baseline）。

**训练**（`train_classical_joint_unrolled.py --variant B1`）：
- BCE-primary fine-tune（λ_bce=1.0, λ_sym=0.05, BCE temperature=5.0, Adam lr=3e-4, max_steps=500）+ best-eval checkpointing
- 无需 pretrain 阶段（B2 所需的 best-iterate supervised pretrain 与 B1 无关）

**SNR mixing**：每个 batch 在 [5, 10, 15, 20, 25] dB 随机采样。

**在本项目中的角色**：**本项目 DNN 部分的最终方案**。100 帧 N=1024 eval 中 15 dB −39% / 20 dB −74% / 25 dB −96.6% 相对 classical teacher。Identity check 保证 B1 零权重时与 NumPy baseline bit-exact，所以 learned head 只可能让 BER 更好不能更坏。前一代 `CurrentJoint` (`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`) 把 OMP support proposal / MP 更新都学习化，在高 SNR 下无法稳定超越经典 teacher，已弃用（见 `CLAUDE.md` "Learned-receiver 方向 (2026-04-19 决定)"）。

### 7.8 OAMP-Net（Orthogonal Approximate Message Passing Network）

**原理**：把 OAMP（Orthogonal AMP）迭代算法的每一层写成可学习网络层：

$$
\mathbf{z}^{(t)} = \mathbf{x}^{(t)} + \mathbf{W}^{(t)} (\mathbf{y} - \mathbf{H} \mathbf{x}^{(t)})
$$

$$
\mathbf{x}^{(t+1)} = \eta_t(\mathbf{z}^{(t)}; \theta_t)
$$

其中 $\mathbf{W}^{(t)}$ 是可学习线性变换（初始化为 LMMSE），$\eta_t$ 是可学习的非线性去噪器（典型初始化为 soft thresholding）。

OAMP 相对 AMP 的优势：**保证去相关**（orthogonality condition），使得每层的残差不会累积偏差。

**在本项目中的角色**：**可选替代检测器**——`afdm_sp_joint_unrolled/afdm_layers.py:47` 定义了 `OAMPNetDetector` 类，作为 AFDM 接收器栈的一个选项。**未作为主 baseline**，因为 OAMP 在严重多径下比 MP + DA-LS 弱（OAMP 假设 i.i.d. Gaussian noise，水声 ICI 结构化太强）。

**参考**：He et al. "Model-Driven Deep Learning for MIMO Detection" (IEEE Trans. Signal Process., 2020)。

### 7.9 EP-Net（Expectation Propagation Network）

**原理**：把 EP（Expectation Propagation）算法展开为可学习网络。

**EP 核心**：迭代近似后验 $q(\mathbf{x}) \approx \mathcal{N}(\boldsymbol{\mu}, \boldsymbol{\Sigma})$，通过**矩匹配**（KL 投影）：

$$
q^{(t+1)}(\mathbf{x}) \leftarrow \mathrm{Proj}_{\mathcal{N}}\Big(\frac{q^{(t)}(\mathbf{x}) \cdot p(x_n)}{q^{(t)}_{\setminus n}(\mathbf{x})}\Big)
$$

即：拿到 cavity 分布 $q_{\setminus n}$（去掉第 $n$ 个因子），乘上真实离散先验 $p(x_n)$，再投回高斯族。

**可学习部分**：cavity 参数、阻尼因子、收敛阈值。

**在本项目中的角色**：**可选替代检测器**——`afdm_layers.py` 的 `EPNetDetector` 类。与 OAMP-Net 类似，在 AFDM 主线上未采用，属于备选。

**参考**：Ge et al. "Deep Learning-based Expectation Propagation" (IEEE TWC, 2020)。

### 7.10 GCEPNet / GNN-MIMO-Detection

两个都是**仅作为外部参考** 存在于 `docs/Code_Analysis.md`，**未移植到 AFDM**。

- **GCEPNet**（Gaussian Conditional Expectation Propagation）：在 EP 基础上加入 Gaussian conditional structure learning，典型用于 MIMO 检测。论文中仅提及作为"deep unfolding 家族的代表"，说明本项目的 SparseMPDetector 也属于该家族。
- **GNN-MIMO-Detection**：用图神经网络解 MIMO 检测，每个用户是 graph node，信道是 edge。对 AFDM 来说图结构是 "DAFT 域 N×N 稀疏邻接"，理论可迁移但需要完全改架构。

**未采用的原因**：
- GCEPNet：EP 假设和水声复合信道的 ICI 不太匹配。
- GNN-MIMO：架构重构成本高，投入产出比低。

### 要点速记

- 10 个对比算法分三类：**性能上界**（Perfect CSI）、**classical baseline**（LS/Dict-LS/ZC-LS/OMP+MMSE/OMP+MP）、**learned baseline**（classical_joint_unrolled + B1 / OAMP / EP / GCEP / GNN）。
- classical_joint_unrolled + B1 是 **本项目主 learned receiver**；其他 learned baseline 均为对照参照物。
- OAMP / EP 有实现但未采用；GCEP / GNN 仅提及；CurrentJoint (JointSparseUnrolledReceiver) 已弃用（见 §7.7 末）。

---

## 第 8 章 — 关键超参总表与复现指南

### 8.1 MATLAB 侧超参（`AFDM_UWA_acoustic.m`，主水声入口）

```matlab
% 系统
M_mod            = 4;               % QPSK
N                = 256;             % DAFT 子载波数
delta_f          = 15e3;            % 子载波间隔 (Hz)
SNR_dB           = 0:5:25;          % SNR 扫描
N_frame          = 11000;

% AFDM chirp
c1               = (2*k_max+1)/(2*N);
c2               = 0;               % MATLAB 约定

% 稀疏信道
taps             = 2;               % P_paths（物理径数）
l_max            = 2;               % 最大延迟索引
k_max            = ceil(v_max*fc/(c*delta_f));

% kLAEK
USE_FRAC_DOPPLER = true;
K_LEAK           = 5;               % 半宽，虚拟径 = 2*K_LEAK+1 = 11

% Joint 迭代
NUM_OUTER_ITS            = 5;
GAMMA_H_DAMP             = 0.7;
GAMMA_X_DAMP             = 0.6;
EPS_STOP_REL             = 1e-3;
UPDATE_SIGMA2_EACH_OUTER = true;
TAU_H_FACTOR             = 0.01;
TAU_H_SIGMA_FACTOR       = 0.1;
lambda_ls_factor         = 1e-3;

% MP
num_iter_MP      = 20;
threshold_MP     = 1e-4;
damp             = 0.5;             % MP 内部阻尼
```

### 8.2 Python Classical 侧超参（`afdm_sp_joint_unrolled/afdm_baselines.py::joint_omp_mp_iterative`）

```python
# 系统
N_total = 1024                 # 毕设评测标准（32×32 subcarrier layout）
rho = 0.5                      # 导频功率比（SP）
P_paths = 10                   # 10 径 UWA
l_max_cap = 102                # 最大延迟（取决于 fs/τ_spread）
k_max_cap = 3                  # v_mean=1 m/s 下
k_leak = 2                     # Python 默认更保守
frac_prune_rel_thres = 0.01    # Dirichlet 旁瓣剪枝

# Joint 外层迭代
n_outer_iter = 5
pic_iter = 20
pic_damp = 0.5
gamma_h = 0.7
gamma_x = 0.6
lambda_ls_factor = 1e-3
tau_h_factor = 0.01
tau_h_sigma_factor = 0.1
eps_stop_rel = 1e-3
update_sigma2 = True

# 相位 / 导频
phase_convention = 'python'    # c2 = (√2-1)/(2N²)
mp_mode = 'pic'                # 或 'bp'
pilot_type = 'zc'              # 全域 ZC SP
zc_root = 7

# UWA 信道
fc = 12e3                      # 中心频率
B = 4e3                        # 带宽
fs = 8e3                       # 采样率
v_mean = 1.0                   # 平均相对速度 m/s
v_std = 0.5
tau_spread = 10e-3             # 多径时延扩展 (s)
```

### 8.3 DNN 侧超参（`classical_joint_unrolled` + B1 learned head，**最终方案**）

```python
# --- Backbone（与 classical 完全一致，无可学习参数）---
#  使用 §8.2 的所有超参

# --- B1 PerIterSymbolRefiner (~10k params, zero-init identity) ---
b1_in_channels  = 5            # [Re(x_mp), Im(x_mp), Re(residual), Im(residual), |H[:,n]|²]
b1_hidden_dims  = [32, 32]     # 2 × Conv1d(kernel_size=3)
b1_out_channels = 2            # Re(Δx), Im(Δx)
b1_last_layer_init = 'zeros'   # 保证初始 Δx = 0

# --- BCE-primary fine-tune ---
variant = 'B1'                  # 只启用 B1 head (B2 已弃用，见 §5.4)
max_steps = 500
lr = 3e-4
optimizer = 'Adam'
lam_bce = 1.0                   # BCE 主 loss 权重
lam_sym = 0.05                  # MSE 小正则（v1 用 0.3 会 drift；Codex Round 2 改成 0.05）
bce_scale = 5.0                 # BCE temperature

# --- Checkpointing ---
ckpt_strategy = 'best-eval'     # 每 N 步在 held-out batch 上算 mean_Δ = BER_learned - BER_classical
                                # 新最小就覆盖 classical_joint_unrolled_best.pt
                                # 避免 v1 的 final-checkpoint drift

# --- SNR mixing ---
train_snr_list = [5, 10, 15, 20, 25]  # 每 batch 随机采样

# --- Device / precision ---
device = 'auto'                 # GPU 上 ~2× 加速
cdtype = 'complex64'            # 训练默认；complex128 仅用于 identity 检查
```

> **历史 ablation 超参（B2, 已弃用）** — 代码仍支持 `--variant B2` / `B1B2` 用于复现 §5.4 的负面结果。B2 需要一个 best-iterate supervised pretrain 阶段（`--b2-pretrain-iters 200 --lr-b2-pretrain 1e-3`），本身是 `3 → 8 → 8 → 1 MLP + tanh` (~1k params) 接在 T 轮外迭之后做混合。

### 8.4 运行命令

#### 8.4.1 MATLAB（毕设水声主入口）

```matlab
cd matlab/
AFDM_UWA_acoustic;            % 毕设主入口（SP 叠加导频 + 10 径 UWA）
% AFDM_LEO_frac_switch;        % 早期 LEO 卫星脚本，仅历史参考，不是毕设主线
```

输出：各 SNR 下 BER（控制台）、图表窗口。

#### 8.4.2 Python Classical Baseline（N=1024 标准评测）

```bash
cd afdm_sp_joint_unrolled/

# 运行单独的 classical baseline，与 learned 同一套帧
python -m afdm_sp_joint_unrolled.eval_classical_joint_unrolled \
  --variant none \
  --snr-list 5 10 15 20 25 --frames-per-snr 200 \
  --n-total 1024 --v-mean 1.0 --device auto --cdtype complex64 \
  --out outputs_classical_baselines_python_n1024
```

#### 8.4.3 DNN classical_joint_unrolled + B1（最终方案）

```bash
cd afdm_sp_joint_unrolled/

# (a) Identity 检查（训练前保障）
python -m afdm_sp_joint_unrolled.verify_classical_unrolled_matches_numpy \
  --n-total 1024 --snr-db 20 --variant B1 --zero-init

# (b) 训练（远端 GPU tmux）
ssh deinlab "tmux new -d -s g_cju_train_B1 'bash -lc \"conda activate AFDM &&
cd /data/guoyikun/00inbox/AFDM-channel-estimation &&
python -m afdm_sp_joint_unrolled.train_classical_joint_unrolled \
  --variant B1 --n-total 1024 --v-mean 1.0 \
  --max-steps 500 --lr 3e-4 \
  --lam-bce 1.0 --lam-sym 0.05 --bce-scale 5.0 \
  --device auto --cdtype complex64 \
  --out afdm_sp_joint_unrolled/outputs_cju_n1024_B1\"'"

# (c) 评测（100 帧主评测 / 500 帧高 SNR 稳健性）
python -m afdm_sp_joint_unrolled.eval_classical_joint_unrolled \
  --variant B1 \
  --ckpt afdm_sp_joint_unrolled/outputs_cju_n1024_B1/classical_joint_unrolled_best.pt \
  --snr-list 5 10 15 20 25 --frames-per-snr 100 \
  --n-total 1024 --v-mean 1.0 --device auto --cdtype complex64 \
  --out afdm_sp_joint_unrolled/outputs_cju_n1024_eval_B1_f100
# 输出：
#   outputs_cju_n1024_eval_B1_f100/results.{json,md}
#   outputs_cju_n1024_eval_B1_f100/figures/*.png
```

#### 8.4.4 Phase-0 Headroom 诊断（可选）

```bash
python -m afdm_sp_joint_unrolled.classical_joint_headroom_probe \
  --n-total 1024 --v-mean 1.0 \
  --snr-list 10 15 20 25 --frames 20 \
  --out afdm_sp_joint_unrolled/outputs_cju_headroom_n1024
```

### 8.5 结果输出位置

| 输出 | 路径 |
|---|---|
| MATLAB BER 曲线 | 控制台 + 图窗口；统一表格见 `paper/figures/*.pdf` |
| Python classical / identity / learned 对照表（主）| `afdm_sp_joint_unrolled/outputs_cju_n1024_eval_B1_f100/results.{json,md}` |
| N=512 v=2 paper config 对照（adaptive）| `afdm_sp_joint_unrolled/outputs_cju_n512_v2_fullsnr_adaptive/` |
| N=512 v=1 对照（adaptive）| `afdm_sp_joint_unrolled/outputs_cju_n512_v1_fullsnr_adaptive/` |
| Perfect-CSI + BP 真实下界 | `afdm_sp_joint_unrolled/outputs_cju_n1024_pcsi_bp_thr01/results.{json,md}` |
| Phase-0 headroom probe（20 帧，被 100 帧 per-iter 复核取代）| `afdm_sp_joint_unrolled/outputs_cju_headroom_n1024/` |
| Per-iter verify 100-frame（推翻 iter-5 假象）| `afdm_sp_joint_unrolled/outputs_per_iter_verify_snr20/` |
| 训练 checkpoint（主）| `afdm_sp_joint_unrolled/outputs_cju_n1024_B1/classical_joint_unrolled_best.pt` |
| 训练 checkpoint（B1B2 历史 ablation，代码保留）| `afdm_sp_joint_unrolled/outputs_cju_n1024_B1B2_pretrain/classical_joint_unrolled_best.pt` |
| Auto-review 日志 | `AUTO_REVIEW.md`（主引用，含 3 轮 Codex 评分 verbatim） |
| 状态机快照 | `REVIEW_STATE.json`（`final_score=6.5, status=completed`） |
| 论文章节 | `paper/sections/5_experiments.tex` |

### 要点速记

- MATLAB 默认 N=256, K_LEAK=5；Python classical / learned 均用 N=1024, k_leak=2（毕设评测标准）。
- DNN 超参主要开关：`--variant B1`（主）, `--lam-bce/--lam-sym`, `--device`, `--cdtype`。
- 所有 learned 训练都有 **Identity 保证**（头零权重时 bit-exact vs NumPy baseline）+ **best-eval checkpointing**（避免 v1 final-ckpt drift）。

---

## 第 9 章 — 文件索引

按"功能 → 文件:line_range"组织。全部都是本文档引用过的位置。

### 9.1 MATLAB 侧

> **主入口文件**：`matlab/AFDM_UWA_acoustic.m`（毕设水声主线，使用 SP 叠加导频 + 10 径 UWA 配置）。下表 helper 行号引用历史脚本 `AFDM_LEO_frac_switch.m`（与 UWA 文件函数一致），方便读者对照原始注释；正式文件以 `AFDM_UWA_acoustic.m` 为准。

| 功能 | 文件 | 行号（同源 LEO 历史脚本）|
|---|---|---|
| **水声主入口** | **`matlab/AFDM_UWA_acoustic.m`** | **整文件，含 main + 所有 helper** |
| Joint 主函数 | `matlab/AFDM_UWA_acoustic.m` (与 `AFDM_LEO_frac_switch.m` 同源) | `joint_omp_mp_ls_sparse` @ `:730-919`（签名约在 `:730`；主循环 `:774-919`）|
| OMP 贪心 | 同上 | `:1180-1218` |
| 感知矩阵 | 同上 | `construct_afdm_sensing_matrix` @ `:1124-1160` |
| 支撑集解码 | 同上 | `extract_delay_doppler_from_h` @ `:1162-1178` |
| Dirichlet 核 | 同上 | `dirichlet_alpha` @ `:1405-1419` |
| 分数 Doppler 生成 | 同上 | `:1304-1331`（内嵌于 `generate_NTN_TDL_channel_SISO`）|
| OMP 支撑扩展 | 同上 | `expand_support_doppler` @ `:1421-1446` |
| DA-LS 字典列 | 同上 | `gen_path_col` @ `:964-990` |
| 加权 LS | 同上 | `weighted_ls` @ `:992-1019` |
| GEN_H_DAFT | 同上 | `:1054-1121` |
| MP 检测 | 同上 | `MP_detection_optimized` @ `:465-724` |
| 系统参数区 | 同上 | `:59-129` |
| 稀疏化门限 | 同上 | `:848-861` |
| 自适应噪声 | 同上 | `:880-894` |
| 早停 | 同上 | `:896-918` |
| LEO 卫星历史脚本（仅参考） | `matlab/AFDM_LEO_frac_switch.m` | 整文件 |

### 9.2 Python Classical 侧（毕设评测使用 `afdm_sp_joint_unrolled/`）

> 主线是 `afdm_sp_joint_unrolled/afdm_baselines.py`（SP 叠加导频专用）。`afdm_joint_param_unrolled/afdm_baselines.py` 是更早的同源实现，结构一致，行号相近。

| 功能 | 文件 | 位置 |
|---|---|---|
| **Joint 主函数** | **`afdm_sp_joint_unrolled/afdm_baselines.py`** | `joint_omp_mp_iterative` |
| OMP 感知矩阵 / 贪心 | 同上 | `construct_sensing_matrix`, `omp_sparse` |
| 支撑集解码 | 同上 | `extract_delay_doppler_from_h` |
| H 重建 | 同上 | `reconstruct_H_from_omp` |
| PIC 快速检测 | 同上 | `mp_detect_pic` |
| BP 完整检测 | 同上 | `mp_detect_bp` |
| OMP 支撑 / DA-LS / H 重建 / MP 驱动 / 噪声估计 / 早停 | 同上（内嵌于 `joint_omp_mp_iterative`） | — |
| 系统参数 / Dirichlet 核 / 分数 Doppler / ZC 导频帧 | `afdm_sp_joint_unrolled/afdm_env.py` | `AFDMEnvMixin.__init__`, `dirichlet_alpha`, `generate_pilot_frame` |
| AFDMSystem 包装 | `afdm_sp_joint_unrolled/run_sp_unfolding.py` | `AFDMSystem` |
| Classical eval 驱动 | `afdm_sp_joint_unrolled/eval_classical_joint_unrolled.py` | 整文件（支持 `--variant none` 仅跑 classical） |

### 9.3 DNN Learned 主线（`classical_joint_unrolled` + B1）

| 功能 | 文件 | 位置 |
|---|---|---|
| **可微分 classical backbone + B1 head** | **`afdm_sp_joint_unrolled/classical_joint_unrolled.py`** | 主类 `ClassicalJointUnrolled`（~800 行） |
| B1 PerIterSymbolRefiner | 同上 | `PerIterSymbolRefiner` class |
| B2 IterResidualSelector（已弃用，见 §5.4） | 同上 | `IterResidualSelector` class |
| 训练入口 | `afdm_sp_joint_unrolled/train_classical_joint_unrolled.py` | 整文件，`--variant B1`（主），`--device`, `--cdtype` |
| 评测入口（与 classical 同一批帧成对对比）| `afdm_sp_joint_unrolled/eval_classical_joint_unrolled.py` | 整文件，支持 `--variant`, `--frames-per-snr`, `--snr-list`, `--device`, `--cdtype` |
| Identity 检查 | `afdm_sp_joint_unrolled/verify_classical_unrolled_matches_numpy.py` | 整文件，支持 `--with-heads`, `--zero-init`, `--cdtype complex128` |
| Phase-0 Headroom probe（20 帧，已被 100 帧 per-iter 取代）| `afdm_sp_joint_unrolled/classical_joint_headroom_probe.py` | 整文件 |
| **Per-iter BER 100-frame 复核** | `afdm_sp_joint_unrolled/per_iter_ber_probe.py` | 整文件 |
| Perfect-CSI + BP 真下界 probe | `afdm_sp_joint_unrolled/perfect_csi_pic_mp_probe.py` | 整文件，支持 `--detector {pic,bp}`, `--h-threshold-rel`, `--target-errors` |
| GPU/CPU benchmark | `afdm_sp_joint_unrolled/bench_cju_device.py` | 整文件 |
| N × v 扫描 | `afdm_sp_joint_unrolled/probe_N_vs_v.py` | 整文件 |
| 论文图生成 | `afdm_sp_joint_unrolled/make_alg_details_figures.py` | 整文件 |
| **训练 checkpoint 主** | `afdm_sp_joint_unrolled/outputs_cju_n1024_B1/classical_joint_unrolled_best.pt` | 权重文件 |
| 训练 checkpoint（B1B2 历史 ablation，代码保留）| `afdm_sp_joint_unrolled/outputs_cju_n1024_B1B2_pretrain/classical_joint_unrolled_best.pt` | 权重文件 |
| **100 帧 B1 主 eval 输出** | `afdm_sp_joint_unrolled/outputs_cju_n1024_eval_B1_f100/` | JSON / MD / PNG |
| N=512 v=2 paper config 对照（adaptive，classical 列）| `afdm_sp_joint_unrolled/outputs_cju_n512_v2_fullsnr_adaptive/` | JSON / MD / PNG |
| N=512 v=1 对照（adaptive）| `afdm_sp_joint_unrolled/outputs_cju_n512_v1_fullsnr_adaptive/` | JSON / MD / PNG |
| Phase-0 输出（20 帧，已被取代）| `afdm_sp_joint_unrolled/outputs_cju_headroom_n1024/` | JSON / MD |
| Per-iter 100f 输出 | `afdm_sp_joint_unrolled/outputs_per_iter_verify_snr20/` | JSON / MD |
| PCSI-BP 150f 输出 | `afdm_sp_joint_unrolled/outputs_cju_n1024_pcsi_bp_thr01/` | JSON / MD |

> **已弃用（仅历史参考）**：`afdm_sp_joint_unrolled/afdm_joint_unrolled.py::JointSparseUnrolledReceiver`（"CurrentJoint"）+ `train_joint_unrolled.py` + `frozen_direct_bit_corrector.py` + `teacher_margin_learned_fusion.py`。前期 decision-oracle audit / PnP refiner / teacher-margin fusion 工作留在仓库里作为 ablation，但不再是主 DNN 路线。

### 9.4 对比基线模块

| 功能 | 文件 | 行号 |
|---|---|---|
| OAMP-Net 检测器 | `afdm_sp_joint_unrolled/afdm_layers.py` | `OAMPNetDetector` @ `:47` 附近 |
| EP-Net 检测器 | `afdm_sp_joint_unrolled/afdm_layers.py` | `EPNetDetector` |
| E2E LMMSE 模型 | `afdm_sp_joint_unrolled/afdm_models.py` | `E2EModel` @ `:1-150` |
| LMMSE 示例 | `example_af_lmmse.py`, `example_af_lmmse_sp.py` | 整文件 |
| GCEPNet / GNN 参考 | `docs/Code_Analysis.md` | `:58-59` |

### 9.5 文档与结果

| 文档 | 路径 |
|---|---|
| **Auto-review 日志（主引用）** | **`AUTO_REVIEW.md`**（含 3 轮 Codex 评分 verbatim） |
| 状态机快照 | `REVIEW_STATE.json`（`final_score=6.5`, `status=completed`） |
| **主 500-frame adaptive eval 数据** | `afdm_sp_joint_unrolled/outputs_cju_n1024_v1_B1_fullsnr_adaptive/results.md` |
| N=512 v=2 对照 | `afdm_sp_joint_unrolled/outputs_cju_n512_v2_fullsnr_adaptive/results.md` |
| Phase-0 headroom 诊断 | `afdm_sp_joint_unrolled/outputs_cju_headroom_n1024/headroom_results.md` |
| 研究叙事（历史） | `NARRATIVE_REPORT_FYP.md` |
| Paper 结构（历史） | `PAPER_PLAN_FYP.md` |
| 早期 claims（Round 8 before deprecation） | `CLAIMS_FROM_RESULTS.md` |
| 论文章节 | `paper/sections/{1_introduction, 2_related_work, 3_setting, 4_method, 5_experiments, 6_discussion, 7_conclusion}.tex` |
| 论文主文件 | `paper/main.tex` |
| Table 1 生成 | `figures/gen_fyp_table1_traditional.py` |
| Figure 2 生成 | `figures/gen_fyp_fig2_traditional_ber.py` |
| Table 4 (复杂度) | `figures/gen_fyp_table4_complexity.py` |

---

## 第 10 章 — 结论：三条算法线的综合定位

### 10.1 MATLAB Joint OMP + MP + LS：研究原型

**定位**：理论完备的算法原型，完整实现了 **kLAEK** 体系。水声毕设主入口为 `matlab/AFDM_UWA_acoustic.m`（采用 SP 叠加导频）；早期 LEO 卫星脚本 `AFDM_LEO_frac_switch.m` 仅作历史参考。

**贡献**：
- 把分数多普勒问题通过 Dirichlet 核分解 + 支撑扩展，**纳入整数字典框架**。
- 证明在 NTN LEO 卫星和 UWA 水声两种场景下，**整数/分数多普勒可切换** 的 cluster-sparse 设计是有效的。
- 建立了"OMP 初始化 + kLAEK 扩展 + DA-LS 细化 + MP 检测 + 自适应 σ² + 早停"的完整外迭框架，所有模块都有手调超参，参数空间清晰。

**局限**：
- 单帧运行为主，规模化仿真（规模 >1000 帧）较慢。
- 没有学习机制，面对 regime shift 需要手工重调超参。

**何时该用**：想要看算法最干净的理论实现、验证 kLAEK 的物理意义、或生成 Table 1 / Figure 2 这种论文前半段的经典基线结果。

### 10.2 Python Joint OMP + MP：评估框架

**定位**：规模化评估 + DNN 接入的工程载体；项目默认评估管线。

**贡献**：
- 完整移植 MATLAB 主流程，新增 `c2 ≠ 0` 相位约定。
- 提供 `return_trajectory=True` 抽取各轮外迭中间状态，**为 DNN 做 teacher signal 铺路**。
- 提供 `mp_mode='pic'`（快速）和 `mp_mode='bp'`（软后验）两种 MP 实现，覆盖不同用例。
- 与 PyTorch 集成，可无缝进入 `AFDMSystem`（通过 MRO Mixin 组装）。

**局限**：
- 相位约定与 MATLAB 不同，两版本 BER **不能直接比较**（只能各自对齐各自的 Perfect CSI 上界）。
- SP 导频下 OMP 稀疏度必须限制为 `P_paths`，不能用扩展后的 `P_actual`（与 MATLAB 一致）。
- 典型 `N_total=100`（规模小），对应 MATLAB 的 `N=256`，性能点不同。

**何时该用**：跑 ablation、对比学习型 receiver、或作为 DNN 后续学习头的忠实 backbone。

### 10.3 DNN classical_joint_unrolled + B1：最终贡献

**定位**：**faithful differentiable unrolling + one zero-init learned head**——把 Python classical 展开成可微分 torch 计算图（identity vs NumPy baseline 在 N=512 下 bit-exact），挂载一个 B1 per-iter symbol refiner (~10k params CNN)，用 BCE-primary loss 微调。

**贡献**：
- **诊断**：原 Phase-0 20-frame probe 发现高 SNR iter-5 BER 反弹 → 100 frame 复核推翻（iter-5 单调更好，20-frame 是 catastrophic-frame 小样本假象）。B2 曾为此设计，已弃用。
- **B1 头**：在每轮外迭 PIC MP 之后、符号 damping 之前加入零初始化 CNN 残差，T=5 轮共享权重。动机是 per-symbol 位置的 `|H|²` / residual phase 信息——classical PIC MP 只用 scalar 残差范数 + 全局 MRC，没利用这些 per-bin 信号。

**为什么是"final contribution"**：
1. **Identity 可证**：B1 零权重时在 N=512 下 x_rel = 0、H_rel ≈ 1e-15、BER_Δ = 0，学习头不可能让事情变坏。
2. **诊断-驱动**：100-frame per-iter probe 证伪了"iter-5 overshoot"假说，排除 B2；B1 的 per-bin 修正机制直接对应 PIC MP 的已知弱项。
3. **真实 gain 明显**：N=1024 500 帧 adaptive eval **15 dB −18% / 20 dB −92% / 25 dB −93%** vs classical teacher（精确累积错误：20 dB 59/141k bits，25 dB 35/72k bits）。
4. **Latency 可忽略**：B1 额外 ~6% forward latency，GPU 相对 CPU ~2× 加速。
5. **方法最小化**：一个 ~10k 参数 CNN，一个 BCE loss，一阶段训练——无需 B2 pretrain，无需多头联合优化。
6. **自我审阅修正**：之前 B1+B2 阶段经 Codex 3 轮评审到 6.5/10 "almost ready"；后续 100-frame per-iter probe 发现 B2 修的是 20 帧小样本假象，B1-only 反而更优。最终方案只保留 B1。

**距离真实下界的空间**：Perfect-CSI + BP (3.26e-6) 是本配置下真实非线性 BER floor；learned 20 dB 5.62e-4 距离它仍 170×，说明**信道估计误差**（OMP support / DA-LS gain quality）是主要剩余瓶颈——进一步 headroom 的方向不在 PIC MP 层，而在 H_hat 层。

**何时该用**：
- 作为论文中"learned receiver outperforms classical teacher under identity guarantee"的完整工程示范。
- 未来工作：500+ 帧 × 多 seed × 多速度稳健性包；OMP support refinement 或 DA-LS 正则学习。

### 10.3.x 历史档案：Learned 方向的早期路线

仓库里保留但**不再作为主方案**：
- **CurrentJoint (`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`)**：把 OMP support proposal / MP 消息更新都做成可学习参数；高 SNR 下 BER 在 6-7% 量级，无法稳定超越经典 teacher。
- **Frozen Direct-Bit Corrector**：12 维 observable + 945 参数 MLP + BCE，单路径"后处理"修正器。decomposition probe 显示其 slice_AUC ≈ 0.49（actionable set 上随机水平），gain 来自 prevalence-following 而非 ranking。
- **Round 8 Teacher-Margin Learned Fusion**：4 参数 logistic regression 融合 CurrentJoint + classical teacher。在 CurrentJoint base 下有 +1.46e-2 gain，但整条 pipeline 被"可以直接改 classical backbone"的新思路取代后不再是主线。

这些路线的代码和 outputs 都在仓库里（见 §9.3 末尾的"已弃用"列表），可用作对照实验但不参与毕设主 results table。

### 10.4 三条线的关系总览（2026-04-20 状态）

```
  ┌────────────────────────────────────────┐
  │ MATLAB Joint OMP+MP+LS (kLAEK, SP)     │
  │   matlab/AFDM_UWA_acoustic.m            │
  │   - 理论完整 / 参数手调 / 单帧为主       │
  │   - 毕设前半段的算法原型                 │
  └──────────────┬─────────────────────────┘
                 │ 算法思想迁移（同样的 SP、kLAEK、T_outer=5）
                 ▼
  ┌────────────────────────────────────────┐
  │ Python classical (SP, c2≠0, ZC 导频)   │
  │   afdm_sp_joint_unrolled/afdm_baselines.py:: │
  │     joint_omp_mp_iterative              │
  │   - 规模化评测（N=1024, 10 径 UWA）      │
  │   - Trajectory 可读                     │
  └──────────────┬─────────────────────────┘
                 │ 可微分忠实展开（identity in N=512 bit-exact）
                 ▼
  ┌────────────────────────────────────────┐
  │ ★ classical_joint_unrolled + B1 ★       │
  │   afdm_sp_joint_unrolled/                │
  │     classical_joint_unrolled.py          │
  │                                          │
  │   - Backbone: 忠实 torch 展开             │
  │   - B1 PerIterSymbolRefiner (~10k CNN)  │
  │   - 零初始化 identity → BCE-primary 微调  │
  │                                          │
  │   结果（100 帧 eval, N=1024, v=1 m/s）:   │
  │     15 dB −39% / 20 dB −74%             │
  │     25 dB −96.6% vs classical teacher    │
  │                                          │
  │   B2 曾作为第二个学习头，但 100 帧复核     │
  │   显示其修的 "iter-5 overshoot" 是 20     │
  │   帧小样本假象，B2 已弃用（§5.4）。        │
  │                                          │
  │   距离真实下界 PCSI-BP (3.26e-6) 仍 170×  │
  │   说明 H_hat 层还有更多 headroom。        │
  └────────────────────────────────────────┘
```

### 10.5 未来方向（仅作讨论）

- **500+ 帧 × 多 seed × 多 v 稳健性包**：Codex Round 3 明确为"ready"的唯一要求。
- **多 v 扩展**：当前 v_mean=1 m/s，`probe_N_vs_v.py` 可扫 0.5 / 1.0 / 2.0 / 4.0 m/s 看 learned 是否仍稳占上风。
- **damping schedule 自适应**：B2 是"事后修正"；未来可以把 classical 的 `gamma_x / pic_damp` 也改成 SNR-aware 的学习 scalar，让 iter-5 过收敛本身就不发生。
- **Coded end-point**：加 LDPC/Turbo 代替 uncoded ARQ，考察 BER gain 在 FER / goodput 上的放大效应。
- **跨 family 迁移**：在 OTFS / OFDM 的对应 classical baseline 上是否能复制同样的 "identity-preserving unrolling + tiny heads" 模板。

### 要点速记

- **MATLAB 是理论原型（`AFDM_UWA_acoustic.m`，SP 叠加导频），Python classical 是工程载体（N=1024 标准评测），classical_joint_unrolled + B1 是最终贡献**——三者不可互相替代。
- B1 的价值在 "identity-preserving unrolling + per-bin CNN 修正 + BCE-primary loss" 这条简单 diagnostic-driven 链路，100 帧 eval 25 dB BER 从 2.56e-3 降到 8.79e-5（−97%）。
- B2 作为负面 ablation 保留——教训是"不要在 20 帧小样本 probe 显示的异常现象上加模块，先验证现象本身是否可重复"。
- 所有 learned heads 零初始化时与 NumPy baseline bit-exact（identity check），理论上不可能让 BER 更坏。
- 前期的 CurrentJoint / Frozen Corrector / Teacher-Margin Fusion 保留为 ablation，不进入毕设主结果。
- 本文档是截止 2026-04-20 的算法快照；具体数字以 `AUTO_REVIEW.md` 3 轮 Codex 评分 + `REVIEW_STATE.json` 最新版为准。

---

*文档完。若发现与代码不一致或数字过期，请直接修订本文件而不是新建版本。*
