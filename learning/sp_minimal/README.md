# sp_minimal — SP-AFDM 主线核心故事的最小复现与掌握

目标：对 TCOM 主线的核心故事建立所有权——能回答跑了什么、为什么是这个结果、对不对，以及审稿人会从哪里追问。

- 头条（已验收）：[res-20261015-02](../../research-assets/res-20261015-02.md)。F0+CSTATE（B）对比 F0、F1 强前端（C）与真 H（A3）。
- 机理（已验收）：[res-20261017-01](../../research-assets/res-20261017-01.md)（E-1：救回主要来自支撑交换，Γ 非对角项只在交换决策中起作用）；[res-20261017-02](../../research-assets/res-20261017-02.md)（E-2：标量 Γ 的劣势等于同时延幻影原子；真簇信道上禁令失效，两类信道都只有完整 Γ 最优）。
- 不作为复现对象：E-3（[res-20261017-03](../../research-assets/res-20261017-03.md)，SBL 中后果反转）以及 10-19 以后的 SBL／期望 Gram 线。它们是审稿弱点，只在出口答辩中出现，以届时的 STATE 为准。
- 本目录只用于学习：不改 `experiments/`、`afdm_sp_joint_unrolled/`；结果不进 STATE、`research-assets/` 或论文；不挂 Trellis 任务（沿用 AFWDM `learning/ce_minimal/` 的先例）。

方案于 2026-10-22 经 grilling 会话确定，八个决定见文末。

## 与 AFWDM ce_minimal 的关系

- **复用**：AFWDM 的 M0–M3（SISO AFDM、DAF 域单径、LS/LMMSE、估计 CSI 的 BER）在本线视为已学，直接引用其笔记，不重走。入口：`../../../AFWDM_AFDM_CP/learning/ce_minimal/README.md`。
- **对偶门控**：AFWDM M3b 把信道估计误差加进检测器的噪声项；本线 S3 把数据软符号的误差加进信道估计器，即 Γ。S3 开始前须完成 M3b：运行通过，并讲回一次。
- **种子位置不同**：AFWDM 把种子三（格子守恒、分数泄露）放到后面；本线的核心（同时延相干 ∝ D_N(Δν)）就长在种子三上，S4 是它的主场。

## 真程序（主线 P1 调用链，只读）

| 角色 | 文件 | 入口 |
|---|---|---|
| 帧生成（修正版） | `experiments/tcom_reference_frame_20261015/gen_fixed.py` | 开关 D1/D2/A1 |
| P1 驱动与臂定义 | `experiments/tcom_reference_frame_20261015/p1_driver.py` | `f0_family`、`f1_family`、`a3_arm` |
| 冻结上下文 | `experiments/headroom_ladder_20261008/driver.py` | `load_context` |
| F0 整机 | `experiments/sp_afdm_native_joint_20260921/src/native_twofft.py` | `receive(rounds=2, iterations=20)` |
| 导频前端 | `experiments/sp_afdm_frozen_20260920/src/receiver.py` | `pilot_front`（515 列字典选 40 原子） |
| LDPC 消息 | `afdm_sp_joint_unrolled/supplement_messages.py`（`experiments/upstream/` 下另有一份拷贝；运行时加载哪份由 `sys.path` 决定，S0 核对地图时用 `module.__file__` 确认） | `decoder_messages` |
| Γ 感知细化、联合检测 | `experiments/sp_afdm_native_joint_20260921/src/twofft.py` | `time_refine`、`scalar_joint` |
| 软符号矩 | `experiments/sp_afdm_frozen_20260920/src/messages.py` | `moments` |
| 物理算子与 Γ 闭式 | `experiments/sp_afdm_frozen_20260920/src/physical.py` | `regressors`、`projected_variance`、`fit` |
| CSTATE20 分支 | `experiments/tf_cstate_validation_20260922/run_validation.py`、`geometry_validation.py` | `_branch`、`exchange_scores` |
| 对角 Γ 消融 | `experiments/tf_cstate_e1_20261017/e1_driver.py` | `gamma_mode='diag'` |

约束：`native_twofft.receive` 只接受 N=1024、ρ=.5（生成端经 ρ shim 改 ρ），不能在 N=16 上跑整机，所以桥接在模块级做。导频为 √ρ·ZC，数据为 √(1−ρ)·QPSK，每符号总能量为 1。

## 语言与环境

- 用 Python（NumPy）。这是对指南 15.8"不要同时学两门编程语言"的**显式放宽**（2026-10-22 Eric 决定）：AFWDM 线继续用 MATLAB；本线只手写核心数学那几行，其余由 AI 写。S0 时 AI 给一页 MATLAB→NumPy 对照表（`notes/matlab_numpy.md`：`@`、`.conj().T`、`np.fft` 的归一化、0 起索引）。
- 环境：本地 conda `CE`（numpy 2.2.6 / scipy 1.16.1 / torch 2.9.1）。冻结管线要求 `OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS=1`、`CUDA_VISIBLE_DEVICES=''`。

## 路线（鸟在前，青蛙在后；每步只加一个复杂因素）

| 步 | 内容 | 我手写的核心 | 尺子 | 前置 | 状态 |
|---|---|---|---|---|---|
| S0 | 不写代码：F0+CSTATE 方法说明卡（17.3）；程序地图第 1 层；5 张参数卡（N、ρ、l_max_cap、P、c₁） | 说明卡每一行；地图核对 | 写不出的行转成问题清单；地图经一次断点运行核对 | 无 | |
| S1 | 鸟瞰：读 P1 的 F0／B／A3 曲线（地板、本方法、天花板）；本地跑 1 帧冻结管线 | 只读，加预测 | 本地 1 帧对存档行 `decoded_sha256`；版本不同可能不一致，记差异，不追 | S0 | |
| S2 | 叠加导频，单条已知径，只用导频 LS，数据当干扰 | 构造 y；LS 读出 | MSE = (\|h\|²(1−ρ)+σ²)/(Nρ)，高 SNR 平台为 (1−ρ)/(Nρ) | S0 | |
| S3 | 数据辅助重估：软符号旋钮 (μ, v)，均匀 v；残余数据误差进估计器，Q = aᴴa + Σv + σ² | 带 Γ 的估计器一行；旋钮到 (μ, v) 的映射 | v→0 退到噪声极限；v=1−ρ、μ=0 退回 S2；中间各点与理论 MSE 对上 | AFWDM M3b | |
| S4 | 两条同时延径加分数 Doppler：完整 Γ 对比对角 Γ | 用蒙特卡洛估计 Γ：E[(Uᵢe)ᴴ(Uⱼe)] | 与闭式 `physical.projected_variance` 对上；再换成逐符号 v，看不同时延项的量级 | S3 | |
| S5 | 单次支撑交换：P=2，强径 A 加弱径 B；候选 A′ 与 A 同时延、Doppler 差 δ，用它替换 B | 两种支撑下的目标函数 yᴴy − bᴴQ⁻¹b | 扫 v，统计完整 Γ 与对角 Γ 的交换接受率，和 E-2 D2 的方向对照 | S4；AI 可行性预检 | |
| 桥接 | 模块级对照：自己的 U、Γ、目标函数 vs `regressors`／`projected_variance`／`fit` 的 `evaluate`；从存档行里找一帧对角 Γ 插入幻影径的实例 | 只读 | 同输入数值一致（rel ≤ 1e-10） | S5 | |

S1 也是 10.6 健康检查第 3 项（喂真实信道看能否到天花板）在本项目上的样子。

**AI 预检（2026-10-22，冻结 `physical.py`，N=16，脚本未入库）**：U 在整数与分数 Doppler 下均为酉（误差 ≤ 4e-16）；S2 尺子 4 个点 sim/theory 为 0.996–1.007；S4 闭式与蒙特卡洛在三个算例上一致。S5 有意不预检，以免预知答案、污染预测；交付前由 AI 只报告"可行／不可行"。

## 脚本约定

1. **预测硬门**：每个 `sN_*.py` 顶部有 `PREDICTION = {...}`；为空或只写"不知道"时，脚本报错退出。至少写方向或数量级；猜不出，就按 13.2 退化到更小的情形再猜。
2. 跑完打印一行"预测 | 实测 | ✅/◐/❌"，直接贴进下方台账。
3. 手写部分标 `# TODO(Eric)`，其余由 AI 写。AI 交付 TODO 版之前，先用自己的填好副本跑通尺子；副本不进仓库。
4. **差异规则（跑前定死）**：尺子不过而代码已核对，就记为差异，按 5.2 三把切刀排查，不许调参调到通过。S5 尤其如此：玩具复现不了幻影径，本身就是一条要记录的结果。
5. **记号来源**：跨步引用旧量时写一行来源链（AFWDM 10-18 的教训），例如 `y → 导频 LS → ĥ_p（本段简记 z）`。

## 讲解方式

来自 AFWDM 复盘第 9 节，仍是可检验的学习假设：固定一个现象 → 列出候选解释 → 反推每个候选需要的条件 → 用已有规律评价 → 导出规则 → 换一个条件检验迁移。提示阶梯从 L1 开始（13.4）；"提示后能复述"与"独立完成"分开记。

| 种子 | 本线落点 |
|---|---|
| 算子对角化／稀疏化 | S2：U_(l,ν) 的结构、ZC 导频与 DAF 域；S4 的算子乘积 |
| 高斯二次型与贝叶斯后验 | S2 的 LS（LMMSE 引用 AFWDM M2）；S3 把未知数据误差积分成二次惩罚 hᴴΓh（errors-in-variables） |
| 格子守恒 | S4：同时延相干 ∝ D_N(Δν)；S5：固定槽位 P 下的交换 |

## 出口（三条都过才算完成）

1. **尺子**：S2–S5 全部通过，或差异已解释并记录；桥接对上。
2. **方法说明卡**：不看资料写满 17.3 的八行。
3. **模拟审稿**：从封存题库 `exam/sealed_questions.md`（12 题，sha256 `858ca8edd3c9bba3241aa39c51db8664e3b2deb887d4275d8f1f8ef07ede4eb9`，2026-10-22 封存）抽 10 题，独立答对 ≥ 8 题；提示后答出的单独记，不计入。评分前 AI 先按当时的 STATE 核对答案要点。出口前不读题库。

## 节奏

按指南第 7 节安排：S0 在第 1 周（对应"AFDM-SP 写说明卡"）；S1 在第 2 周（对应"程序第 1 层、健康检查、地板与天花板曲线"）；S2–S5 与第 3–7 周的程序第 2–4 层和种子评价同周推进；S3 等 AFWDM M3b 完成。与 AFWDM 冲突时按 15.6 的优先级处理，一周内主线不变（15.4）。

## 记录

| 日期 | 步 | 预测 → 结果（✅/◐/❌） | 卡点 / 理解欠账 |
|---|---|---|---|

## 方案决定（2026-10-22 grilling）

| 决定 | 选择 |
|---|---|
| 标靶 | 主线核心故事：res-20261015-02 头条，加 res-20261017-01/02 机理 |
| 起点 | 复用 AFWDM M0–M3；S3 以 AFWDM M3b 为门 |
| 语言 | Python 加 MATLAB→NumPy 对照表，显式放宽 15.8 |
| 软符号 | 可控旋钮 (μ, v)，不接检测器和译码器；闭环效应在 S1 读真管线 |
| S5 粒度 | 单次交换决策 |
| 出口 | 尺子、说明卡、封存题库模拟审稿 8/10 |
| 预测门 | 硬门：至少猜方向或数量级，"不知道"不算 |
| 题库 | 现在出、封存，记 sha256，出口时抽题 |
