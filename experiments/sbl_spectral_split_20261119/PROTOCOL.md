# DRAFT — SBL 谱分解检验（Phase 1，2026-11-19，未冻结）

> Sol 第一阶段可以修订本稿，但每处修改须写明理由。冻结前须完成：Claude 预测登记（§6，本稿已写）、另一模型的设计评审、Eric 冻结。

## 1. 背景与已知事实
- **E-3c 管线**：stage 1 → 第一轮 APP → 候选集（筛出的 256 个原子，加上 stage 1 保留下来的每个时延的全部 25 个 Doppler 原子）→ stage-2 EM-SBL（100 次迭代）→ `_system` 连续细化 → 译码。
- **已知结果**（1200 键）：

  | 臂 | 构造 | FER |
  |---|---|---:|
  | `diag-off` | 标量 | .03250 |
  | `cov-off` | 完整 Γ | .15750 |
  | `cov+ridge` | Γ + `sum(v)·I`，**SBL 与细化两处都加** | .04250 |

- **β 的更新含 Γ**（`sbl_rx.sbl_em`）：`1/β = (‖Y − Bμ‖² + μᴴΓμ + tr((BᴴB+Γ)Σ))/N`。所以加岭有两条作用途径：一是改变各方向的精度，二是抬高噪声估计。比较"两半"时必须控制加进去的总量。
- **细化阶段多为单原子时延**：单个原子的 D 特征值恒为 1。若在这一阶段做谱拆分，岭会自动全部落进"可分辨"一半，造成假象。所以先定位阶段，谱拆分只在 SBL 阶段做。
- **旁证**：res-20261018-03 否定了 Berkson 过收缩的解读；res-20261018-04 显示原子固定后改用各向同性终端求解反而更差。两者都指向 EM 的原子选择，但都不是对本问题的直接检验。

## 2. 构造
- 对每把候选集中的时延 ℓ，取它的原子集 S_ℓ（k_ℓ 个），令 `D_ℓ = Γ[S_ℓ, S_ℓ] / sum(v)`。按 Prop 1，D_ℓ 的对角恰为 1，门控检验误差 ≤ 1e-12。
- 对 D_ℓ 做特征分解，以阈值 **τ = .5** 划分：
  - `Π_lo,ℓ`：特征值 < τ 的子空间，即亚分辨/差模方向，秩记为 r_ℓ；
  - `Π_hi,ℓ = I − Π_lo,ℓ`：可分辨方向。
- 各种岭都按时延分块对角拼起来，在 EM 开始时一次构造，原子被剪掉时与 Γ 用同样的下标同步缩减。u = `sum(v)`。

| 臂 | SBL 中的 Γ | 细化中的岭 | 作用 |
|---|---|---|---|
| R0 `diag-off` | u·I（标量） | σ²（diag 模式） | 参照，与 E-3c 一致 |
| R1 `cov-off` | Γ | σ² | 参照 |
| R2 `cov+ridge` | Γ + u·I | σ² + u | 参照（两处都加） |
| S0 `ridge-sbl` | Γ + u·I | σ² | 只在 SBL 加 |
| T0 `ridge-ref` | Γ（复用 R1 的 SBL 输出） | σ² + u | 只在细化加 |
| S-lo | Γ + u·Π_lo | σ² | 亚分辨一半 |
| S-hi | Γ + u·Π_hi | σ² | 可分辨一半 |
| S-isolo | Γ + u·(r_ℓ/k_ℓ)·I_ℓ | σ² | 与 S-lo 逐块同迹的各向同性对照 |
| S-isohi | Γ + u·((k_ℓ−r_ℓ)/k_ℓ)·I_ℓ | σ² | 与 S-hi 逐块同迹的各向同性对照 |

恒等关系（门控检验）：
- S-lo 的岭 + S-hi 的岭 = S0 的岭；
- S-isolo + S-isohi 同样等于 S0 的岭；
- S-lo 与 S-isolo 逐块同迹，S-hi 与 S-isohi 逐块同迹。

**加长迭代对照**：R1、S0、S-lo、S-hi 在 max_iter = 400 下，只跑预定子集，即帧 4000–4049（600 键）。

**每臂记录**：
- β 终值、迭代次数、是否收敛、EM 结束时与输出时的原子数、输出原子中的同时延对数；
- 加入的迹，以及 D_ℓ 特征值落在 [.25, .75] 的个数（阈值模糊区）；
- 译码 FER、NMSE。

## 3. 判定（冻结后不重标）
物理帧簇 bootstrap，20,000 次，seed 20261119，簇的定义与 E-3c 相同。分母为非正的抽样比例 > .01 时，相应分数记为不可评估。

**阶段（Q1）**：
- 定义 G = FER(R1) − FER(R2)，s = [FER(R1) − FER(S0)]/G，t = [FER(R1) − FER(T0)]/G。
- STAGE = SBL：s 的区间下界 ≥ .5，且 t 的区间上界 ≤ .25。
- STAGE = REFINEMENT：反过来。
- 其余为 SHARED 或 INCONCLUSIVE。

**谱拆分（Q2）**，仅当 s 的区间下界 ≥ .5 时评估：
- 定义 G_s = FER(R1) − FER(S0)，f_X = [FER(R1) − FER(X)]/G_s，X ∈ {S-lo, S-hi, S-isolo, S-isohi}。
- 方向效应：Δ_lo = FER(S-isolo) − FER(S-lo)，Δ_hi = FER(S-isohi) − FER(S-hi)，均为配对差。
- 判定按以下顺序，取第一条成立的：
  1. SUB-RES-DIRECTION：f_lo 的下界 ≥ .5，f_hi 的上界 ≤ .25，且 Δ_lo 的下界 > 0；
  2. SUB-RES-AMOUNT：f_lo 的下界 ≥ .5，f_hi 的上界 ≤ .25，但 Δ_lo 的下界 ≤ 0；
  3. RESOLVABLE：f_hi 的下界 ≥ .5，且 f_lo 的上界 ≤ .25；
  4. NON-ADDITIVE：f_lo 和 f_hi 的上界都 ≤ .25；
  5. SHARED：f_lo 和 f_hi 的下界都 ≥ .25；
  6. 其余为 INCONCLUSIVE。

**机制结论**（命题："EM 中差模/亚分辨方向正则不足造成 SBL 反转"）：
- 重放支持：STAGE = SBL，且 SUB-RES-DIRECTION。
- 否定：出现以下任一情况——
  - STAGE = REFINEMENT；
  - 谱拆分可评估且 f_lo 的上界 ≤ .25；
  - 谱拆分可评估且 Δ_lo 的上界 ≤ 0（与同迹各向同性相比，方向没有带来好处）。
- 其余：未确立。
- 即使得到"重放支持"，也只是在已用过的旧键上的支持；要写"统一"，还需在新帧上做前瞻确认。

**次要（只报告，不判定）**：
- 加长迭代下，s 与 f 的顺序和类别是否保持；
- 各臂的 β、原子数、同时延对数、收敛率；
- 各单元格的 FER。

## 4. 竞争假设与各臂预言（research-checkpoint 1.1）

| 假设 | S0 对 T0 | S-lo 对 S-hi | S-lo 对 S-isolo | 诊断量 |
|---|---|---|---|---|
| H1 亚分辨方向（EM 剪枝失败） | S0 救回 | S-lo ≈ S0，S-hi ≈ R1 | S-lo 更好 | S-lo 的同时延对数和未收敛数下降 |
| H2 总量 / β（噪声估计被抬高） | S0 救回 | f_lo > f_hi，大致按迹的比例 | S-lo ≈ S-isolo | β 随加入的迹单调下降 |
| H3 可分辨方向（物理方向的收缩） | S0 救回 | S-hi ≈ S0，S-lo ≈ R1 | — | — |
| H4 终端增益求解 | T0 救回 | 不评估 | — | — |
| H5 非可加（需要两半同时加） | S0 救回 | 两半都 ≈ R1 | — | — |

各假设的预言两两可分。H1 与 H2 的分辨只靠 S-lo 对 S-isolo 这一个对比，所以这一对的统计功效是关键（见 §5 第 2 条）。

## 5. 设计有效性（1.2）与事前验尸（1.3）
1. **单因素对比**：
   - S0 与 T0 只差岭加在哪个阶段；
   - S-lo 与 S-hi 只差方向，但总量也不同，所以另设同迹对照；
   - S-lo 与 S-isolo 只差方向、总量相同。
2. **杠杆**：G 已知为 .115（1200 键，E-3c）；G_s 未知。若 G_s 太小，分数的区间会很宽。另一个问题：25 原子块中 r_ℓ/k_ℓ 预计约 .7，S-isolo ≈ .7u·I 已经接近完整岭，H1 与 H2 的差异可能很小，Δ_lo 有可能落入 INCONCLUSIVE。可接受：这样的结果会写作"方向效应未确立"，不会写成否定。
3. **统计单位**：物理帧簇，与 E-3c 相同。
4. **代理量的含义**：u·Π_lo 是"按 D 的谱定义的差模岭"，不是 Astra 简报里按组均值定义的那一种；τ = .5 是约定值，所以要报告模糊区的特征值个数。
5. **事前验尸**：若结果与预期相反（S-hi 承担救回），最可能的原因是 τ 的划分把部分接近可分辨的方向放进了"高"一侧。此时看模糊区的个数：若它占有显著份额，结论写作"对 τ 敏感"。若 STAGE = REFINEMENT，与 res-04 的旁证相冲，须先排查 T0 是否真的复用了 R1 的 SBL 输出（门控 G2 检查这一点）。

## 6. Claude 的预测（本稿提交时写定）
- R0、R1、R2 与 E-3c 逐位一致：.95
- STAGE = SBL：.55；REFINEMENT：.15；其余：.30
- 在可评估前提下：f_lo 的下界 ≥ .5：.55；f_hi 的下界 ≥ .5：.20
- 机制结论：重放支持 .25；否定 .40；未确立 .35
- 与 §6.1 先验（.35）的关系：.35 对应"S-lo 复现大部分救回且 S-hi 无效"，没有阶段因素和同迹对照。加上这两道条件后，降到 .25。

## 7. 冻结前修订（按 [Astra 设计评审](../../.trellis/tasks/09-22-tf-production-gap-audit/research/astra-design-review-20261119.md)，2026-11-19；本节优先于 §3）
Astra 数值核对：25 原子网格上低秩为 18/25，.5 两侧的特征值为 .3463 和 1.5549，有明显间隙；两个原子间隔 .25/.5/.75 时，较小特征值为 .0997/.3634/.6999。

1. **估计对象收窄为"初始网格谱岭"**：投影在 EM 开始时一次构造，剪枝时按主子矩阵缩减，不重建。所有结论都只针对这个干预，不宣称是"剪枝时刻的活跃子空间"。u = 0 时岭为 0，D 直接由 Doppler 核构造（只用于普查）。
2. **不作的主张**：
   - 同迹各向同性只是**名义预算对照**，不能识别 β 中介；
   - 本设计不能区分"低特征空间的特异性"与"投影和各向同性的谱形差异"。

   要做这两种归因，需要共同 β 轨迹或同谱对照，本次不做，结论措辞相应收窄。
3. **判定改为不相交的规则**（取代 §3 中谱拆分与机制结论两部分；阶段判定保留，补交互项）：
   - **阶段**：报告 s、t，以及交互项 I = 1 − s − t（含区间）。
     - STAGE = SBL：s 的下界 ≥ .5，且 t 的上界 ≤ .25；
     - STAGE = REFINEMENT：反过来；
     - SHARED：s、t 的下界都 ≥ .25；
     - 其余为 INCONCLUSIVE。
   - **每一半单独分类**（X ∈ {lo, hi}）：
     - f_X 的下界 ≥ .5 → 承担；
     - f_X 的上界 ≤ .25 → 单独不足；
     - 其余 → 不确定。
   - **形状对比**（X ∈ {lo, hi}），Δ_X = FER(同迹各向同性) − FER(投影岭)，配对：
     - 下界 > 0 → 投影形状更优；
     - 区间整个落在 [−.01, +.01] 内 → 1 pp 内等效；
     - 上界 < 0 → 各向同性更优；
     - 其余 → 不确定。
   - **对"EM 中差模正则不足"这一候选的结论**：
     - **干预层面支持**：STAGE = SBL，lo 承担、hi 单独不足，且 Δ_lo 显示投影形状更优；
     - **"仅低半"故事不成立**：STAGE = REFINEMENT，或 lo 单独不足；后者不排除低模与高模共同起作用；
     - **其余**：未确立。

   不显著不再算否定。主判定只看 100 次迭代的管线。
4. **预测改写**（按新规则，冻结前写定）：
   - 干预层面支持：.25；
   - "仅低半"故事不成立：.35；
   - 未确立：.40。

## Phase 1 execution details and revision reasons

| Change from the task DRAFT | Reason |
|---|---|
| Label this copy as the Phase 1 experiment DRAFT and rebase the relative review link. | Identify the runner protocol and keep the review link valid from its new directory. |
| Use the frozen same-delay Doppler kernel for the census when `u = 0` and add zero ridge. | Carry through §7 of the reviewed task DRAFT and avoid an undefined division at zero variance. G2 synthetic checks that zero variance leaves the census defined and adds no penalty. |
| Join the 100-iteration R0/R1/R2 outcomes by the exact four-field E-3c key after verifying the immutable archive. | All 24 shards matched the local MD5 manifest and all 3,600 reference rows provide β, iterations, convergence, EM and output atom counts, co-delay pairs, FER and NMSE. The live R1 SBL fit needed by T0 is still included in the projection. |
| Record initial candidate-set EM ridge trace and refinement ridge trace separately at their respective atom counts. Count eigenvalues in [.25, .75] and all eigenvalues of the full-Γ candidate blocks once per key. Attach the key-level census to all arms and pool by eigenvalue across smoke keys. | EM and refinement operate on different atom sets. The two traces resolve the DRAFT's unspecified measurement stage, and the common census describes the split used to construct the ridges. |
| Check the SBL component and refinement component against their own targets, and verify refinement normal-equation closure independently. | E-3c's consistency check assumes identical uncertainty components on both sides. Several spectral-test arms deliberately use different components. |
| Gate the Phase 1 executable to G1's 20 seeded main keys with R0/R1/R2 at 100 iterations, and to the 12 E-3c smoke keys for new arms. Test G2 on synthetic inputs and smoke, and G3 by exact comparison after removing timings at both budgets. | This preserves main-key blindness and qualifies the changed receiver and both iteration budgets without interpreting smoke FER or NMSE. |
| Project core-hours from shared preparation once per key per budget, the six new arms at 100 plus T0's live R1 SBL dependency, and the four declared arms at 400. Multiply by 1.3. At a projection above 30 core-hours, reduce the extended subset to frames 4000–4024 and recalculate. | This accounts for work that a reference-row join cannot remove and implements the brief's budget rule. The selected subset and any reduction are recorded in the Phase 1 receipt. |
