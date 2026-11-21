# FROZEN — 统一协方差 Γ_U = Γ + u·Π_lo 的前瞻检验（2026-11-19 冻结，Claude 代办；冻结记录见任务目录 research/freeze-20261119.md）

> Claude 起草（Eric 2026-11-19 上午批准运行："Yes, run it"）。Sol 第一阶段可以修订本稿，但每处须写明理由。冻结前须完成：
> Claude 预测登记（§7，本稿已写）、Astra 设计评审（research-checkpoint 1.5）、Sol 第一阶段门控与杠杆读数。冻结由 Claude 代办。

## 0. 要检验的命题
**候选统一**（[res-20261119-02](../../research-assets/res-20261119-02.md) 解释层，置信度 M，未检验）：
- 同延块的精确协方差是 u·D，它的谱在可分辨（和模）方向上大，在亚分辨（差模）方向上接近零。
- 同一个谱事实对应两种方向相反的失败：
  - **CSTATE 离散支撑搜索**：标量 uI 对和模罚得不够，于是产生幻影奖励（[res-20261118-06](../../research-assets/res-20261118-06.md)、[res-20261119-01](../../research-assets/res-20261119-01.md)）；
  - **超完备 EM-SBL**：精确 Γ 对差模几乎不罚，于是出现反转（res-20261119-02，旧键重放）。
- **统一模型** Γ_U = Γ + u·Π_lo：和模保留精确值，差模被抬到至少 u。
- **预言**：同一份协方差放进两条管线，两种失败都不出现。

**对 res-20261119-02 的更正**：
- 卡片写"在 SBL 中应不差于标量"，与重放自己的数字不符：S-lo 为 .0558，R0 为 .0325，只救回差距的约 81%。
- 本检验的 SBL 预言改为"救回大部分差距"。标量在 SBL 中仍可能是最好的。
- 统一是解释层面的主张：一个谱事实解释两种失败，并给出一个两边都不失败的协方差。它不是"Γ_U 在每条管线里都最优"。

## 1. Γ_U 的构造（两条管线共用的定义）
- 对接收机在某一估计步开始时形成协方差的原子集 S：
  - 令 `D_ℓ(S) = Γ_cd[S_ℓ, S_ℓ] / u`，即同延原子之间的 Doppler 核，对角恰为 1；u = `sum(v)`；
  - `Π_lo,ℓ` 取 D_ℓ 中特征值 < τ = .5 的特征向量；
  - `Γ_U(S) = Γ(S) + u · ⊕_ℓ Π_lo,ℓ`。
- Γ(S) 是该管线原有的精确协方差：SBL 用 E-3c 的完整 Γ；CSTATE 用闭式 `CODELAY`（经验上与 FULL 相同，0:0 / 13,600 键）。
- 投影在每个估计步开始时构造，步内固定：
  - **EM-SBL**：在 EM 开始时于初始候选网格上构造一次，剪枝时取主子矩阵。与重放的 S-lo 完全相同（旧协议 §7.1）。
  - **连续 Doppler 细化**（SBL 一侧的 `_system` 细化、CSTATE 的 local passes 与 final refit）：在每一遍开始时于当前原子集上构造，这一遍内固定。这样可以避免特征值穿过 τ 时目标函数不连续。
  - **CSTATE 离散交换打分**：按每个试验支撑分别构造。每个试验本身就是不同的原子集，不存在连续性问题。
- 单原子时延：Π_lo 为空，Γ_U = Γ。
- Sol 可以带理由修改步的边界，但必须保留门控："u ≡ 0 或 τ = 0 时，与对应参照臂逐位一致"。

## 2. 帧、键与管线
- **新帧** 4400–4599（共 200 帧）。
  - 任何仿真之前，Sol 先核对所有既有归档都没有用过这一段，并记录核对方法。
  - 若用过，取下一个未用的 200 帧整块（4600–4799，……）。
- **SBL 一侧**：E-3c 管线（stage 1 → 第一轮 APP → 候选 → EM-SBL 100 次迭代 → `_system` 细化 → 译码）。网格 U/G × ρ .3 × 6–11 dB × 200 帧，共 2,400 键。
- **CSTATE 一侧**：Stage 3 的 F0+CSTATE 管线（[res-20261118-03](../../research-assets/res-20261118-03.md)）。网格 U/G × ρ {.3, .5} × {5, 5.5, 6, 7, 8, 9, 10, 11} dB，ρ .5 另加 6.5 dB，× 200 帧，共 6,800 键。下游 native `scalar_joint` 不变。
- **统计单位**：物理帧簇（200 簇）。bootstrap 20,000 次，seed 20261120。

## 3. 实验臂
**SBL 一侧**

| 臂 | EM-SBL 中的协方差 | 细化 | 作用 |
|---|---|---|---|
| R0 | u·I | u·I + σ²I | 标量参照 |
| R1 | Γ | Γ + σ²I | 精确参照 |
| S-lo | Γ + u·Π_lo | 同 R1 | 复现重放臂 |
| S-hi | Γ + u·Π_hi | 同 R1 | 复现重放臂 |
| S-isolo | Γ + u·(r_ℓ/k_ℓ)·I_ℓ | 同 R1 | 形状对照（与 S-lo 逐块同迹） |
| **U2** | Γ + u·Π_lo | Γ_U + σ²I（按 §1 每遍构造） | **统一模型用于全部步骤** |

**CSTATE 一侧**（交换打分、local passes 与 final refit 都用同一种协方差）

| 臂 | 协方差 | 作用 |
|---|---|---|
| F0 | — | 基线 |
| A2 | 标量（`gamma_mode='diag'`，同样的 schedule） | 标量参照 |
| CD | `CODELAY` | 精确参照（= FULL） |
| **U** | Γ_U（在 `CODELAY` 上加 u·Π_lo） | **统一模型** |

## 4. 主判定（冻结后不重标）
**定义**
- **SBL**：G_B = FER(R1) − FER(R0)；救回比例 φ_X = [FER(R1) − FER(X)] / G_B。
- **CSTATE**（全网格配对）：Δ_UC = FER(U) − FER(CD)，Δ_UA = FER(U) − FER(A2)。
- 分母为非正的抽样比例超过 .01 时，相应比例记为不可评估。

**交叉前提**（两种失败必须在新帧上重现，否则统一结论不可评估）
- 失败 1：G_B 的下界 > 0（精确 Γ 在 SBL 中更差）；
- 失败 2：FER(A2) − FER(CD) 的下界 > 0（标量在 CSTATE 中更差）。

**V1 亚分辨机制的前瞻复现**（SBL）
- 每一半单独分类：φ_X 下界 ≥ .5 → 承担；上界 ≤ .25 → 单独不足；其余 → 不确定。
- 形状：Δ_lo = FER(S-isolo) − FER(S-lo)，配对。下界 > 0 → 投影更优；区间整个在 [−.01, +.01] 内 → 等效；上界 < 0 → 各向同性更优；其余 → 不确定。
- 结论：
  - lo 承担、hi 单独不足、投影更优 → **前瞻干预层面支持**；
  - lo 单独不足 → **重放未复现**；
  - 其余 → 未确立。

**V2 统一臂在 SBL 中**：φ_U2 下界 ≥ .5 → 救回；上界 ≤ .25 → 未救回；其余 → 不确定。

**V3 统一臂与 CODELAY 等价**（CSTATE，边界 m = .5 pp）
- Δ_UC 的区间整个在 [−m, +m] 内 → **等价**；
- 下界 > +m → **更差**；
- 上界 < −m → 更好；
- 其余 → 不确定。

**V4 统一臂优于标量**（CSTATE）：Δ_UA 上界 < 0 → **优于**；下界 ≥ 0 → **不优于**；其余 → 不确定。

**统一结论**
- **前瞻支持**：两个交叉前提都成立，且 V2 救回、V3 等价、V4 优于。
- **不成立**：V2 未救回，或 V3 更差，或 V4 不优于。
- 交叉前提不成立 → 不可评估；其余 → 未确立。
- 即使前瞻支持，也只能写"Γ_U 在两条管线中都不出现各自的失败"，不写"最优"。U2 与 R0 之间剩下的差距照实报告。

## 5. 次要（只报告，不判定）
- U2 − S-lo（细化中加 Π_lo 的效应）；S-lo − R0 与 U2 − R0（与标量之间剩下的差距）。
- 输出同时延对数、β、迭代次数、收敛率。
- CSTATE 每单元格的 FER，以及 10⁻² 穿越点。
- 交换中第一步编辑的类型（加在已有时延上 / 新时延）占比，A2、CD、U 三臂对比；这个量不需要真值。若真值分类的代价 ≤ 1 核时，另报幻影份额（按 res-20261118-06 的定义）。
- 普查：
  - CSTATE 试验支撑中 Π_lo 非空的比例；
  - U 与 CD 在交换决策上不同的键数，以及其中含真实近同延径对（同一时延、Doppler 差 < .5 bin）的键数。

## 6. 竞争假设、设计有效性与事前验尸（research-checkpoint 1.1–1.3）

| 假设 | SBL：φ_lo / φ_hi / Δ_lo | SBL：φ_U2 | CSTATE：U 对 CD | U 对 A2 |
|---|---|---|---|---|
| **H-U** 统一谱下限 | ≥ .5 / ≤ .25 / > 0 | ≥ .5 | 等价 | 优于 |
| H-replay 重放结果是旧键上的偶然 | 缩到 < .5 | < .5 | 等价 | 优于 |
| H-amount 只看加入的总量 | 都高 / 中 / ≈ 0 | ≥ .5 | 等价 | 优于 |
| H-conflict-C Π_lo 压住真实的近同延径对 | — | — | 更差 | 弱于 CD |
| H-conflict-R 细化中的 Π_lo 有害 | — | < φ_lo | — | — |

- **单因素**：
  - S-lo 与 S-isolo 只差形状，迹相同；
  - U 与 CD 只差加入的 u·Π_lo；
  - U2 与 S-lo 只差细化中的 Π_lo。
- **杠杆**：
  - SBL：重放中 G_B = .125，φ_lo = .81。若前瞻值收缩到 .65，2,400 键下的下界估计仍 ≥ .5。Sol 第一阶段须按旧行用簇 bootstrap 估一次 φ_lo 的区间半宽：先在 1,200 旧键上算，再按 √2 外推。
  - CSTATE：Sol 须从既有归档（E-1 / split-prosp 的 A1 与 A2 配对）读出同类网格上 A2 − A1 的 FER 差与区间。若预期差距 < 1 pp，V4 可能落入"不确定"，冻结前写明。
  - Δ_UC：Π_lo 只在近同延试验上起作用，预期不一致键极少，区间应很窄。
- **事前验尸**：
  - (a) U 在 CSTATE 中更差。最可能是真实的近同延径对被压，用普查中的真值计数判断；也可能是 local passes 里冻结投影的处理有问题，用门控排查。
  - (b) V2 未救回但 S-lo 救回：细化中的 Π_lo 有害，属于 H-conflict-R。此时统一结论按规则判为"不成立"，不改判。
  - (c) 重放未复现：属于 H-replay。卡片 res-20261119-02 的解释层须随之降级。

## 7. Claude 的预测（本稿提交时写定）
| 事件 | 概率 |
|---|---:|
| 交叉前提两个都成立 | .85 |
| V1 中 lo 承担（下界 ≥ .5） | .70 |
| V1 中 hi 单独不足 | .75 |
| V1 中形状为投影更优 | .45 |
| V1 前瞻干预层面支持 | .35 |
| V2 救回 | .60 |
| V3 等价 | .80 |
| V4 优于（以失败 2 成立为条件） | .85 |
| **统一结论前瞻支持** | **.40** |
| 统一结论不成立 | .25 |

## 8. 预算与执行
- **第一阶段**（Sol，≤ 3 核时）：
  - 实现两条管线的新臂；
  - 门控 G1–G3（见 [design.md](../../.trellis/tasks/11-19-unified-cov-prospective/design.md)）；
  - 杠杆读数与成本预估；
  - 只用旧键和 smoke 键，新帧保持盲。
- **主跑**（≤ 25 核时）：按冒烟计时 × 1.3 预估。若超过 25 核时，SBL 一侧先缩到帧 4400–4549（1,800 键），再重新预估。
- deinlab 只用 CPU，每进程单线程，最多 32 个进程，tmux `g_unified`，输出写入实验自己的 `out/`。
- 判定代码先在合成输入上测过，冻结时提交；主跑结束后直接运行，不再改动。

## 9. CSTATE 镜像拆分（Claude，2026-11-19 上午，在任何新帧仿真之前写定）
**理由**：
- V3 只在近同延试验上起作用。`CODELAY` 下近同延候选本来就被压住，所以 U 与 CD 等价几乎是构造上必然的，只能算相容性检查。
- 要真正检验"一个谱事实、两种相反的失败"，须在 CSTATE 中做 SBL 谱拆分的镜像：从标量出发，只把某一半换成精确值。

**机制推导**（解释层，未检验）：
- 幻影奖励来自"把已有强径的增益平分到两个几乎重合的原子上"：
  - 标量下，平分后不确定度罚项减半（u·|h|²/2 对 u·|h|²），所以有奖励；
  - 精确 Γ 下，和模的罚是 u(1+|D|)，平分不再省罚。
- 所以 CSTATE 的失败在和模（可分辨一半），SBL 的失败在差模（亚分辨一半）。

**新增两臂**（构造与 U 相同：按每个试验支撑、每个同延块在 τ = .5 处拆分，连续步内固定投影）：
| 臂 | 协方差 | 谱解释的预言 |
|---|---|---|
| C-hi | u·[Π_lo + Π_hi D Π_hi]（亚分辨一半用标量，可分辨一半用精确值） | ≈ CD，幻影被压 |
| C-lo | u·[Π_hi + Π_lo D Π_lo]（可分辨一半用标量，亚分辨一半用精确值） | ≈ A2，幻影仍在 |

（C-hi 与 U 只差 u·Π_lo D Π_lo，后者的特征值 < .5。）

**V5 镜像判定**：
- 令 ψ_X = [FER(A2) − FER(X)] / [FER(A2) − FER(CD)]，要求交叉前提 2 成立；
- 每一半单独分类：下界 ≥ .5 → 承担；上界 ≤ .25 → 单独不足；
- **镜像支持**：C-hi 承担，且 C-lo 单独不足；
- **镜像相反**：C-lo 承担，且 C-hi 单独不足；
- 其余为未确立。

**统一结论改为两层**：
- (i) **谱解释前瞻支持**：V1 前瞻干预层面支持，且 V5 镜像支持；
- (ii) **统一协方差相容**：V2 救回、V3 等价、V4 优于。

两层分别报告；只有 (i) 与 (ii) 都成立，才写"一个谱事实解释两种失败，并给出两边都不失败的协方差"。

**竞争假设补充**：
- H-cross：压幻影需要完整的精确耦合，两半都要，所以 C-hi 与 C-lo 都只部分救回；
- H-diff：压幻影来自精确的差模，所以 C-lo 救回、C-hi 不救回。

**预测**（本节写定时）：
| 事件 | 概率 |
|---|---:|
| C-hi 承担 | .70 |
| C-lo 单独不足 | .65 |
| V5 镜像支持 | .55 |
| (i) 谱解释前瞻支持（V1 与 V5 同时成立） | .25 |

**次要**：A2、CD、U、C-hi、C-lo 五臂的第一步编辑中加在已有时延上的比例。预言 C-lo ≈ A2 偏高，C-hi ≈ CD 偏低。

## 10. 冻结前修订（按 [Astra 设计评审](../../.trellis/tasks/11-19-unified-cov-prospective/research/astra-design-review.md) 与 §9 合并；本节优先于 §4、§9 中的冲突部分）
写于 2026-11-19 上午，在任何新帧仿真之前。

1. **结论分三层，先判前提**：
   - 先判两个交叉前提。任一不成立或不可评估 → 相应结论不可评估。
   - 另在两条管线的公共子网格（ρ .3，6–11 dB）上报告两个交叉差值的符号（次要）。
   - **(i) 谱解释（机制）前瞻支持**：两个交叉前提成立，V1 前瞻干预层面支持，且 V5 镜像支持。
   - **(ii) 统一协方差相容（操作层面）**：V2 救回、V3 不劣、V4 优于。
   - **(iii) 全称"一个谱事实解释两种失败，并给出两边都不失败的协方差"**：(i) 与 (ii) 同时成立。这是交并检验，各分量按自身水平检验，不做 Bonferroni 校正，但功效会下降。
   - 任一分量为"未确立"时，相应层也是未确立；不把未确立写成否定。
2. **V1 的范围**：只是干预对比（初始迹相同），不主张特征空间特异性或 β 中介；同谱替代子空间与共同 β 轨迹都不做。形状判定只看方向（下界 > 0 → 投影更优；上界 < 0 → 各向同性更优；其余 → 不确定），量级另行描述性报告。
3. **新增预设伤害对比 H-conflict-R**：H = FER(U2) − FER(S-lo)，配对。下界 > 0 → 细化中的 Π_lo 有害；上界 < 0 → 有益；其余 → 不确定。只报告，不进入 (i)–(iii)。
4. **V3 改为不劣检验**：
   - 边界 m = min(.5 pp, .25 × 归档中 A2 − CD 的全网格 FER 差)，由 Sol 第一阶段的杠杆读数 (b) 定出后在冻结时写死。
   - **不劣**：上界 ≤ +m；**劣于**：下界 > +m；其余 → 不确定。
   - **稀有事件规则**：U 与 CD 之间有通过/失败翻转的帧簇少于 5 个时，不用 bootstrap。改用 Δ_upper = CP95_upper(c_U, 200) × max(1, 各簇中 U 独有失败键数的最大值) / 每簇键数，其中 c_U 是至少有一个 U 独有失败键的簇数。这里假定未观察到的簇的翻转量不超过已观察到的最大值。这一规则也适用于 V5 中的 C-hi 与 CD。
5. **V5 主读数的选择规则**（由旧数据的杠杆决定，冻结时写死）：
   - 若按归档估计，全网格上 ψ 的 95% 半宽 ≤ .25，V5 用 FER 层面（§9 定义）；
   - 否则 V5 改用单元层面的读数（下一条），FER 层面降为次要。
6. **单元层面镜像读数**（V5-adm；规则 5 选中时为主读数，否则为次要）：
   - **单元**：新帧上 F0 失败、CSTATE 触发，且 A2 第一次交换选中的编辑是一个"投影活跃"的同延候选，即该候选与同一时延的已有原子构成的块有特征值 < τ。
   - **比较**：从同一保存状态出发，固定 A2 选中的删除槽，对五臂 X ∈ {A2, CD, U, C-hi, C-lo} 分别计算这个指定幻影候选的实测 Schur 净增益，以及最好的新时延候选的增益（不用真值）。
   - **读数**：偏好率 P_X = 幻影增益 > 新时延增益的单元占比，按帧簇 bootstrap。
   - **定义**：π_X = [P_A2 − P_X] / [P_A2 − P_CD]，按 §9 的规则对 C-hi、C-lo 分类，得出镜像支持 / 相反 / 未确立。
   - **覆盖**：单元数 < 100 时记为不可评估。
7. **构造与门控的补充**（交给 Sol）：
   - **逐阶段写明投影的构造支撑**：EM 用初始候选网格，剪枝后取主子矩阵，与重放兼容；每一遍连续细化用该遍开始时的原子集；每个离散试验用该试验支撑。
   - 投影改变时，在任何接受或拒绝比较之前，先用新投影重算当前解的目标值。每一遍固定投影的细化内部检查目标单调下降。
   - R1 的细化写明为完整 Γ + σ²I。这样把 U2 的细化投影置空时，才真正还原 S-lo。
   - u = 0 时直接用 Doppler 核，或跳过零岭。
   - **G2 新增**：在孤立的接纳定律切片上，按 Astra 的闭式公式核对 A2、CD、U、C-hi、C-lo 五种协方差下的幻影净奖励，δ = .25 和 .5 bin。实测时分别优化两个支撑求解，对比闭式值，相对误差 ≤ 1e-8。
8. **限制写明**：P1 各径时延互不相同，CSTATE 中不存在真实的近同延径对，所以 H-conflict-C 在 P1 上不可检验；真值计数的普查只作描述。谱下限 u·max(D, I) 这一竞争的统一形式不在本次检验范围内，记为未解决。
9. **SBL 的功效**：
   - Astra 估计，2,400 键时 Δ_lo 的期望半宽为 .50 pp；效应减半时功效约 68%。
   - 若按冒烟计时，SBL 一侧 300 帧（4400–4699，3,600 键）的预估主跑总成本 ≤ 25 核时，就用 300 帧；否则用 200 帧。4600–4699 未被使用须同样核对。

## Phase 1 revisions and reasons

| Change from the approved task DRAFT at `89313c87` | Reason |
|---|---|
| Rebase card and task links to this experiment directory. | The source DRAFT lives under the Trellis task. |
| Spell out the scalar R0 normal matrix penalty u·I + σ²I and the R1, S-lo, S-hi and S-isolo refinement system as the full Γ plus σ²I. U2 adds the fixed projector to that system and re-evaluates the incumbent when a new pass starts. Its final gain solve uses the last pass's objective. | Frozen E-3b/E-3c refinement represents noise by the ridge and full covariance by a separate argument. This is the executable baseline for the projector-empty reduction. |
| Evaluate D directly from the closed-form co-delay Doppler kernel and skip the ridge at zero uncertainty. In CSTATE, solve each trial's full normal equations with its own projector, and rebuild it on entry to each local pass and to final refit. | The projector can change the retained members' block in a trial. It cannot be represented by a candidate-wise cross term. Separate continuous passes may use different objectives. |
| Use a verified historical split-prospective K smoke key for A2 parity and its eight saved K smoke keys for G3 and timing. | These are already observed on the same F0+A2/A1 entry points. The Stage 3 archive has F0, FULL and CODELAY. |
| Use the frozen paired cluster bootstrap helper and mark a nonpositive point denominator unevaluable even if the resampling-failure threshold alone would permit the interval. | The estimated rescue fraction is undefined or has the wrong denominator sign. Valid intervals use the DRAFT's 1% rule. |
| Project SBL with one shared preparation and one S-lo/U2 EM fit per key. Project CSTATE with one F0 per key and triggered branch costs weighted by the Stage 3 whole-grid syndrome rate. | Sharing follows the actual harness and the smoke trigger rate can differ from the prospective grid's. |
| Keep the Phase 1 copy on the approved §3/§4/§8 scope. Later task-DRAFT §9 and §10 revisions remain in the Trellis task for the subsequent handoff. | The execution brief fixes the Phase 1 arm inventory, verdicts and projections. This copy remains a DRAFT. |


## Phase 1b implementation notes and reasons

| Decision | Reason |
|---|---|
| Apply §§9–10 to the implementation and verdicts. Keep the revision history above and keep this protocol in DRAFT. | §10 takes precedence where the first-pass rules differ. Its layer conjunction records support or lack of establishment after the premises. |
| Use the initial grid for SBL EM, the principal submatrix after pruning, the entering support for each continuous pass, the trial support for each CSTATE exchange score, and the final CSTATE support for refit. SBL R1 uses full Γ + σ²I. | These are the explicit construction supports for comparing objectives and reproducing the replay. Recompute the incumbent on each new fixed objective and check per-pass descent with an independent endpoint re-evaluation. |
| For fixed projector P, form C-hi with (I−P)Γ_CD(I−P) + uP and C-lo with PΓ_CD P + u(I−P), using actual trial Dopplers in Γ_CD. Share trial-independent data-column products across spectral arms. | Doppler movement within a pass can change Γ_CD while P stays fixed. The two-sided sandwich keeps the defined subspace penalty even when the updated covariance and fixed projector do not commute. |
| Use the A2 first legal selected proposal, whether accepted or rejected, and classify a new delay against the entering support. For both candidate classes, compute net gain from the same deletion-slot anchor with the surviving paths. | §10.6 defines a selection-conditioned comparison. The common anchor and two candidate classes make the comparison reproducible from saved first-exchange scores. |
| Use the larger projected half-width of ψ_C-hi and ψ_C-lo in §10.5, and retain the C-hi/CD non-inferiority readout alongside the mirror ratio. | V5 needs both halves. The C-hi/CD comparison uses the same rare-event rule as U/CD. |
| Test A2 against up to eight triggered, same-harness split-prospective K rows. Take the first two eligible archive keys in each scenario/pilot cell, breaking ties by frame and SNR. | This uses the expanded archive scope specified for G1 and covers all four cells. |
| Use 200 archived Stage 3 frames (4000–4199) to project leverage on the full 34-key-per-frame grid. Replay all six arms only on archived F0-triggered keys and fold in the archived F0 outcome for all six arms elsewhere. | This yields an empirical frame-cluster half-width at the target sample size and a direct count of eligible V5-adm units, within the Phase 1b CPU cap. |
| Estimate the two main schedules using CPU smoke timings for both receiver legs, Stage 3's whole-grid trigger rate, and full-six-arm old-trigger replay timing for incremental V5-adm work. | This accounts separately for the diagnostic and avoids extrapolating triggered branch costs to every key. |

**Phase 1b readout, 2026-11-19.** The pre-freeze margin is **0.500 pp**. The split-prospective archive and the exact old Stage 3 A2−CD
replay both reach the cap. The two old FER-ratio half-widths were 0.0000 and 0.0231, so the §10.5 choice is **FER primary**, with V5-adm
secondary and 894 eligible units projected per 200 frames. V5-adm resamples physical frames represented in its conditional unit population.
The C-hi/CD rare-event bound is reported alongside the §9 ratio verdict because §10.4 specifies a bound on the FER difference.
The §10.9 choice is **200 SBL frames, 4400–4599**. The 200-frame SBL option costs 18.252 core-hours, with 19.438 total.
The 300-frame option costs 27.377 SBL and 28.564 total core-hours. The expanded P1 block 4400–4699 remains blind.
[Phase 1b qualification receipts](out/phase1b_20261119/RESULTS.md)
