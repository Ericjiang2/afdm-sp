# E-3b 技术设计

## 1. 流程（每个键）

1. **第 1 级与第 1 轮**：导频 SBL，接着检测与译码，全部逐位沿用 E-3。
2. **第 2 级**：每个变体先跑 E-3 的 on-grid SBL（同一候选集、同一超参），得到输出原子，最多 24 个，按能量降序排列。
3. **连续 Doppler 细化**（新增步骤，每个变体各自进行）：
   - 目标函数：`value(paths) = geometry_reopen_variant._system(Y, xt, v_m, paths, c1, c2, ridge=σ², gamma_mode=g_m).value`。各变体的参数如下：
     - L-hard：xt 由硬判决数据构造，v_m = 0；
     - L-diag：xt 由软均值构造，v_m = v，g_m = 'diag'；
     - L-cov：xt 由软均值构造，v_m = v，g_m = 'full'；
     - L-genie：xt 由真数据构造，v_m = 0。
     - v_m = 0 时 g_m 不起作用。
   - 搜索：做 P = 3 遍。每遍按能量降序遍历原子 k，固定其余原子，在 [ν_k − .5, ν_k + .5] ∩ [−3, 3] 内用有界一维搜索（`minimize_scalar` bounded，xatol = 1e-3，最多 16 次评估，与 CSTATE 局部细化同型）最小化 value。只有 value 严格下降才接受新值。
   - 时延不变，原子数不变。同时延原子可以靠近，也可以重合到 1e-6 以内；不加任何守卫，因为这正是要观察的对象。
   - 细化之后用同一 `_system` 的解 h 作为最终增益。
4. **第 2 轮**：`scalar_joint(gain_mode='fixed', prior=check)`，接 LDPC，读出 FER。

## 2. 变体与配对

- off-grid 变体有四个：hard-off、diag-off、cov-off、genie-off。
- on-grid 对照取自 E-3 行中同一个键的 L-hard、L-diag、L-cov、L-genie，不重跑。
- 键：U/G × ρ.3 × {6, …, 11} dB × 帧 4000..4199，共 2400 个，全部包含在 E-3 主跑键中。

## 3. 读数与冻结判据

记号：
- A_on = FER(L-cov) − FER(L-diag)，取自 E-3 行，同一批键；
- A_off = FER(cov-off) − FER(diag-off)；
- Δ = A_on − A_off。

所有量都用配对 cluster bootstrap 估计（cluster = (场景, 帧)，20000 次，seed 20261017，百分位 95% CI）。另报告 diag-off 对 cov-off 的精确单侧 McNemar，取 log10 p。

判定按以下顺序检查，取第一条成立者（互斥）：
1. **REVERSED**：CI_hi(A_off) < 0 且 CI_lo(Δ) > 0。细化后完整 Γ 反而更好，插值解释被支持。
2. **VANISHED**：CI(A_off) ⊂ [−.01, .01] 且 CI_lo(Δ) > 0。优势消失，插值解释被支持。
3. **REDUCED**：CI_lo(A_off) > 0 且 CI_lo(Δ) > 0。优势缩小但仍在，插值解释只解释了一部分。
4. **PERSISTS**：CI_lo(A_off) > 0 且 CI_lo(Δ) ≤ 0。优势不受细化影响，插值解释被否定。
5. **MIXED**：以上都不成立。

预注册读数（不参与判定）：
- 每个变体 on-grid 与 off-grid 的 FER，以及 FER 1e-2 穿越点；
- 同时延普查，口径同 E-3；另记录细化后同时延对的 |Δν| 分布，以及 |Δν| < .1 的近重合对比例；
- NMSE；
- 细化接受率；
- 成本。

## 4. 成本

- 估计：每键约 24 s（4 个变体，每个含 SBL 约 3.2 s 和细化约 2 s），2400 键约 16 core-h；在争用下乘 1.3 约 21 core-h。
- 上限 30 core-h，同时最多 24 个进程，保留 ≥ 16 核空闲。
- 运行方式：tmux 链 gate → run → agg → gzip/md5，无人值守，链内带成本检查（推算总量超过上限即停并写 STATUS）。

## 5. 门

- **G1 on-grid 一致**：重跑 20 个键的 E-3 on-grid 第 2 级，四个变体输出原子与 decoded sha 都应等于 E-3 行，用以确认 SBL 与管线未变。
- **G2 细化正确性**：
  - 合成单径分数 Doppler、v = 0 的情形下，细化后的 Doppler 误差 < 1e-3；
  - 每次细化 value 单调不增；
  - hard 与 genie 在 v_m = 0 时，`_system` 的 gamma 恒为 0。
- **G3 确定性**：同一输入跑两次，结果逐位一致。
- **G4 成本**：用 smoke 估计核时，结果应 ≤ 30。

## 6. 局限

- 连续一维坐标搜索不是 Luo 的 Taylor 更新，属于同类机制的简化。
- 细化只作用在 SBL 的输出原子上，不进入 EM 迭代内部。
- 只覆盖 ρ.3、两个场景、200 帧。
