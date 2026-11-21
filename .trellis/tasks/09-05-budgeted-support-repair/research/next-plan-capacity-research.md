# 下一轮容量修正：单一主方案与验收研究

状态：仅计划研究。用户本轮未授权新实验；本文不启动代码实现、校准、服务器任务或新预算。现有结果来自 S4 `s4-interim-report.md`、`fixed-capacity-contract.md`；接口依据当前 `classical_joint_unrolled.py`、`budgeted_support_eval.py`、`decision_harvest.py`。

## 1. 已有结果能说明什么

旧展开条目数提名：A2 28/192 → V(T1) 17/192，三个流均改善。这是含模拟真值容量的正向开发信号，不是部署结论。

保守固定上限40、K_prop=8：平均实际活跃24.19；A2(T1) 124/192、M(T2) 129/192、V(T2) 145/192。

- M(T2)−A2(T1) 是该支撑/先验域下的温度均值干预。
- V(T2)−M(T2) 是该温度下增加冻结协方差 GLS 的干预；总错误相差16，具体 win/harm 必须读取逐帧记录，不能由总数假定全部是新增损害。
- 缺 V(T1)，因此不能判断该固定骨架下 V 本身失败，还是温度与协方差交互造成失败。
- 旧28与固定124同时变化了提名数量、扩展后支撑、实际容量、prior拟合域；把全部差距归因于“未用满40”超出证据。温度不混入这两个 baseline，因为它们都是T1。
- 当前保守方案是合法容量约束，却已显示是低性能适配。不能继续用它证明新方法优越；也不能据此否定所有同容量软反馈。

## 2. 推荐唯一主方案：直接选择最终字典原子，取消接收器二次扩展

先固定 `K_active_cap=40`，OMP/F2P 最终原子上限也40；不是重新做五容量搜索。选择40是针对已观察保守映射失效的**下一轮工程假设**，不是声称D_cal已经证明这个新策略最优。

保持模拟器物理路径数8、分数多普勒截断扩展 k_leak=2、字典 l/k范围不变。仅接收器不再为已选整数原子增加邻居。字典本来就覆盖展开后的整数原子，OMP/F2P 可直接选择其中任何列；不需要把已选列再次视作物理路径中心。

最小可执行配置可复用现有 `expand_cluster_support(...,k_leak=0)`：它只解码、合并现有提名列，不加入邻居。**只能改 receiver cfg.k_leak，不能改生成器 system.k_leak**。更清晰的配置命名是 `receiver_support_mode=direct_dictionary_atoms`；落到现有算子仍只一个实现。

两处 OMP 同为40：`budgeted_support_eval.run_frame` 的外部 Hhat0 OMP，以及 `ClassicalJointConfig.n_paths` 对应的 Torch OMP/F2P cap。后者保持 rounds2、M96、add≤4、protect2；初始字典原子不超过40，F2P临时union≤48，最终剪枝/重拟合复用原代码。最终 `K_active=len(S)` ≤40。应标记为 `A2_direct_atoms40`，不能叫原历史 A2 完全相同算法。

这一路径无需新搜索评分、新保护规则或第二次prune。没有修改物理信道模型，代价主要是更大的初始 OMP/LS与相应prior域，必须重新实测完整耗时。

### 对三种方案的裁决

| 方案 | 价值与基线地位 | 本轮计划选择 |
|---|---|---|
| ① 最终字典原子cap下OMP；可选现有F2P；不二次扩展 | OMP是清晰经典锚点；F2P是现有修复骨架的有限原子适配。能力需实测，不能仅凭名义cap称最强。OLS是经典强对照，但当前主路径未发现可直接调用的OLS初始化，不应用新OLS实现阻塞最小检查 | **唯一主线**：先OMP与F2P的T1基线，再选定壳上的V(T1)。不同时搜索OMP/OLS/簇三种新机制 |
| ② 原F2P→扩展→共用pilot-LS prune/refit | 可利用簇结构，但引入第二个模型选择步骤；初始零增益邻居需先LS才可公平排名。支持更充分使用cap，但不是免费/自动强基线 | 暂不开发。仅①容量骨架仍不能成立、且误差证据指向有价值的簇信息时，回到设计审议 |
| ③ 按实际新增union容量接纳整簇 | 比worst-case除5精确，但候选顺序、容量耗尽和“跳过/首拒即停”都是新策略；大簇挤出后续候选造成偏置，需要重新解释完整动作目标 | 暂不开发。它是新的支撑搜索机制，不是单纯配置修正；目前S3排序证据不足 |

不能把①里“无修复OMP”自动视为弱基线；如果同容量同预算优于A2适配，应选它作最低比较锚点。不能在②用更大的中间支持/额外LS后忽略成本，或在③从多个接受规则中择优再声称零调参。

## 3. 精确接口与不变量

- `fixed_nomination_cap(active_cap,k_leak,k_max)` 目前 width=min(2*k_leak+1,2*k_max+1)。接收器k_leak=0时自然得到K_prop=40，不需再写映射函数。
- `budgeted_support_eval.run_frame` 目前用cfg.k_leak调用上式，外部OMP与cfg.n_paths都使用nomination。需保证该cfg字段在 prior loader 选域之前设置；否则可能装K_prop8缓存再跑K_prop40。
- `ClassicalJointUnrolled.forward` t=0 末尾扩展返回后，已有 `active_support_cap` gate。继续验证unique(l,k)、gains同长、≤40；不得用截前40列代替规则。
- `CandActiveRelHead.apply_f2p_refinement` 复用现有最终pilot-LS、protect2、剪枝及refit。cap40没有旧cap1的protect超限边界，仍记录保护集合和最终大小。
- M/V只在t>0改变soft feedback / gain solve。相同骨架下两臂t=0输入、raw/repaired/final support与初始H必须相同；之后由于估计反馈不同，H和概率可以不同。
- 固定部署臂禁用 oracle_support、diagnostic truth override、off_support_corr/H_corr；真实H/数据仍只进模拟、标签与评估。

②若未来被批准：现F2P只返回(S,g)，并不返回protected-added metadata。不能从最终增益猜保护对象。应抽取**单一共享的 final prune/refit primitive**，显式接收support/LS gains/protected column IDs/cap；主F2P和扩展后适配共用它。扩展后的protected含义必须冻结（仅原保护中心，还是其整簇）；整簇保护可超cap，需报错/协议决策，不得静默放宽。初始扩展邻居gain=0，直接按该值剪掉等同虚设簇；扩展union先LS带来的N×K、K²/K³成本以及最终refit全部计入。不能从剪枝前后pilot residual下降推断完整receiver FER单调。

③若未来被批准：使用现有expand_cluster_support生成候选簇，再统计去重union的实际增量；不得自己另写不同裁剪/合并规则。必须先冻结装不下时skip还是stop、是否允许拆簇、排序是否按收益/新原子数、同分tie规则；这些都是方法自由度，应计入搜索并独立评估。

## 4. V(T1)补项：必要性与优先级

若要解释当前弱骨架上“V为何反转”，**V(T1)是最小必要缺项**：已有A2(T1)=124、M(T2)=129、V(T2)=145，补一个V(T1)即可形成温度×入口2×2，不需要扩大温度网格。

建议在获批下一轮后，以原固定40/K_prop8/source/prior、原192开发帧补此单臂；它是封口归因检查，不能用结果选新温度、不能称独立确认。做之前核对已执行run配置，确保不存在已跑V(T1)却尚未汇总的数据。

- V(T1)仍退化：支持“该弱支撑域下，协方差入口至少在T1/T2都不合格”，仍不证明容量充分的壳也无效。
- V(T1)改善而V(T2)退化：支持温度×协方差交互；说明基线logits的NLL最优T不能无条件迁移到V。此时停止用T2解释V，先在新壳固定T1检查。
- 无明显差异/样本精度不足：登记未知，不扩网格追加种子追显著。

**它不是新容量实现/审查的前置依赖**。主线①可并行准备工程契约。新壳第一批直接锁T1，避免重新同时修改温度与容量；先看V(T1)的可实现信号，再决定是否需要重新校准温度。当前用户仅要求计划，本项尚不运行。

## 5. 新壳下一轮最小步骤与验收门槛

### P0：冻结协议与预算（先于任何实验）

固定direct_atoms40、T1、coded SNR8、生成器不变、Dcal新子集/manifest、192已有Ddev仅开发的身份。先清理资源账本和新阶段预算授权；已有S1限额缺口不借用其他阶段余额。登记所有候选/条件支线，最多主壳两个初始化（OMP/F2P）及选定壳的V，不启动五容量×五温度矩阵。

验收：配置能独立说明生成器k_leak2 vs receiver扩展0，nomination40 vs active40、prior域、输入分割、停止条件、预算。缺任何关键项就停在计划。

### P1：容量/支撑工程契约

下列为需执行的契约测试，不是本次已通过结果：

1. 多于8个唯一真字典原子的无噪声小系统：直接原子选择可以超过旧K_prop8，接收支持≤40；与接收器扩展0解码的明确列集一致。不能把同一算法重算当独立参考。
2. 对一组显式整数列与复增益，k_leak0的reconstruct_H与直接单位字典算子线性组合一致；覆盖边界k、重复输入、复增益抵消。
3. 固定接收输入y/pilot，修改/移除P_actual，外部与Torch OMP cap都不变；仅评估真值字段变化，部署输出不变。
4. generator配置/hash固定，receiver expansion0不改变H_true/data/noise/y；避免将更容易的整数/不泄漏信道冒充容量修复。
5. baseline/V(T1)初始三层支撑一致，所有轮active≤40，F2P临时union有独立最大值记录；非法cap/重复越界列明确失败。
6. 默认legacy不受新配置影响；T1旧算术与CUDA回放精确契约继续保留。禁用观察器不能改变输出。

失败去向：工程失败主线暂停，定位后修复；不进入FER比较、不增配置掩盖失败。

### P2：只在对应Dcal域建立prior，先检验可用基线

新nomination40需要对应initial-OMP prior；已有nomination8先验不能当同域。复用decision_harvest/fine-prior，保留完整真标签。相同Dcal输入下分别评估OMP40与F2P40的T1；以预先冻结的FER→info errors→较低完整成本顺序选定初始化，独立validation只评估不调参。

这样可能选OMP而不是A2，应如实改主壳名称；不需要为了保住A2标题开发第二次簇剪枝。prior是iid-QPSK域，coded validation检验其转移，不能把prior fit误标coded。若选择OMP，prior/scorer成本不应再计入它的在线路径。

验收：候选容量配置无真值、Dcal匹配/完整标签、配对输入完整；报告FER/BER、实际支撑/边数、未占用容量、NMSE、失败、成本。**不强制追平旧28/192**（旧oracle信息与更大实际支持不可比），但F2P若明显劣于同预算直接OMP，禁止拿F2P当唯一“强A2”继续比较。两者都无法形成有意义接收性能时，记录“≤40原子约束下壳仍不足”，回审容量约束；不能默默把cap涨80。

### P3：冻结壳后，隔离V(T1)

只比较同一选定初始化的mean(T1)与V(T1)。先独立Dcal-validation完整闭环，再既有Ddev三流3×64定位；所有pairing/分母完整。报告逐流FER、paired win/harm、概率可靠性、support匹配与误差传播案例。NLL改善不是FER放行条件，NMSE改善也不是。

验收分三类：三流一致且配对伤害可控的FER正向信号→候选成立、尚非G1；反复退化→停止V扩参、保留负证据；幅度小/区间宽→不足，是否增加开发样本须在新预算和预登记批次内另行判断。禁止因为结果弱再试T0.5/1/2/4或cluster策略择优。

### P4：只有壳与V有价值才进入正式预算/确认准备

重做新壳的device-ready完整时延：GPU独占、同步、统一线程、≥1000测量帧+10warmup、≥10blocks，比较mean/P95的+10%约束。先前并发耗时、legacy 1024帧host-source计时均不能代替。若成本不合格，停止该候选或提交明确优化方案，不在本轮同时搜索多个近似逆/早停。

S5前仍需 B1/外部C族范围、正式功效/统计、护栏与D_test封存。①工程成功或192开发帧改善都不能自动越过这些门槛。

## 6. 不做的搜索与明确失败去向

本轮计划不同时开发OLS新实现、扩展后保护剪枝、收益/新增容量簇排序；不重新扫五cap；不把T作为每种壳的自由网格；不继续G入口调lambda；不通过改变生成器pruning/物理P来“恢复”baseline。

推荐顺序：**补齐旧壳V(T1)归因缺项（可并行）→direct_atoms40的可用基线→同壳V(T1)→完整预算与S5**。主线①失败时回到研究边界：若容量壳不足，审议允许容量/簇表示；若壳可用但V失败，接受当前软协方差无可部署价值；若只样本不充分，标INCONCLUSIVE。②/③只有明确新证据与单独设计决定才进入，不能作为默认自动兜底。
