# Derivation Package: 保存轨迹中的优化目标与判决风险

## Target

TRAJECTORY-DIAG-01：从已封口 DEV 的全部迭代记录恢复同一可比较的优化目标，
描述其与误比特、真实符号 log loss 的关系。识别下一步研究问题；不选择可部署的
oracle 停止轮数，不把开发曲线作为独立确认。本文件在轨迹风险计算前冻结口径。

## Status

COHERENT AS STATED，待独立身份/边界审查。经典变分恒等式，无首创声明。

## Invariant Object

给定 point 多普勒向量 ν、固定路径数 P 与 delay，研究工作模型的条件下界
F(q_d,q_h,ν)=E log p(y|d,h,ν)−KL(q_d||p_d)−KL(q_h||p_h)。
所有比较保持同一条 observation、噪声、prior 与坐标；不把 data-block surrogate
单独当作跨迭代完整目标。ν 在这里是优化参数，不为 Dirac 分布定义微分熵。

## Assumptions

- 复数 proper Gaussian 工作先验 p_h=CN(0,I/P)，q_h=CN(m,C)，C 正定且完整。
- q_d 为独立四元 QPSK 概率，p_d 均匀；噪声 CN(0,σ²I)。真实生成先验不必等于工作先验。
- 使用旧四个 blocks、两个 SNR、N1024 的已封口记录。P=8；以原件检查，不改归一化。
- 每个 sweep 的 gain 状态固定于其三个 data steps；普通点法取 gain_after_doppler，
  collapsed 取该 sweep 最后坐标的完整 winner。此后未再更新 gain。
- 只分析已保存 sweep 末状态：8×(20+5+5)=240 个；不补造中间 data-step 概率。

## Notation

D 是原 DataStepper 保存的最后 new_objective；它包含 −E||y−H(p+d)||²/σ²
与 −KL(q_d||p_d)。N 为符号数，P 为 gain 维数，m/C 为当时的完整 gain 因子。
L_{n,a}=log q_d(d_n=a)，真值符号编号为 a_n=2 b_n+b_{N+n}。

## Derivation Strategy

从完整条件下界出发，补上 data surrogate 缺少的 Gaussian gain KL；随后分别
计算对观测的拟合下界与对保存真值的预测风险。二者不能互相代替。

## Derivation Map

1. 复 Gaussian KL 的解析恒等式 → 可比较的 F。
2. 已保存 normalized log q → bit marginal LLR、BER、symbol log loss。
3. 全轨迹描述 → 区分优化与风险；不推出新停止策略或因果瓶颈。

## Main Derivation

**恒等式 1（复 Gaussian KL）。**

KL(q_h||p_h)=P tr(C)+P||m||²−P−P log(P)−log det(C)。

因而忽略同一 observation 不变的 −N log(πσ²) 后，

F=D+log det(C)+P+P log(P)−P tr(C)−P||m||²。

这是指定工作分布的精确恒等式；不把它称为真实模型 likelihood 或真实 posterior。
q_h 随 sweep 变化时，单看 D 的差值不能代替 F 的差值。不同 gain 维数若出现，
本协议失败，不通过删除常数来拼接比较。C 的 logdet 用标准库复数 Cholesky
恢复并检查正定、Hermitian 和重构误差；不调用生产求解器。

**恒等式 2（bit marginals）。** QPSK 顺序是 (00,01,10,11)：

LLR_I=logaddexp(L_0,L_1)−logaddexp(L_2,L_3)，
LLR_Q=logaddexp(L_0,L_2)−logaddexp(L_1,L_3)。

按 all-I then all-Q 拼接，LLR<0 判 1。采用稳定 logaddexp；不截断/重置概率。
每 observation 分母 2048，symbol log loss 为 −Σ_n L_{n,a_n}/N；
同时记录 q_d entropy per symbol、每次相邻 sweep 的纠正与引入错误。
完整保留每条轨迹及 SNR 汇总；对所有已保存 sweep 使用相同公式，不挑最优点展示。

**命题边界。** 若一次更新的全部坐标步骤都增加同一 F，则 F 不降；
BER/log loss 不属于这个命题的结论。此处先数值核对实际 F 轨迹，不以算法名
保证它必然单调。若观察到 F 增而风险变差，结论仅是该保存轨迹上的目标–风险分离。

## Remarks and Interpretation

原 point 第五 sweep 可与两条局部法第五 sweep 描述性比较，以区分“减少轮数”
和“改变搜索”的混合因素；这不是重新运行一个完整五轮接收机。
仅记录保存的累计 sweep seconds，明确排除获取/初始化/最终导出/保存，不能当作
端到端五轮成本或据此通过性能–成本门。

## Boundaries and Non-Claims

数据已被本轮方法开发反复使用；结果属于 post-hoc 诊断。不能据真实误码曲线选择
每样本停止点并报告为 observation-only 算法；不能声称错 delay、漏路径或 posterior
因子化已被因果归因。后续方法必须独立冻结、准入与确认。原 DEV 科学门不改。

## Open Risks

原件缺失、gain 状态错位、log q 映射不一致会使分析无效。预检必须验证 manifest/
receiver seal 的完整身份；所有终态 LLR/hard/errors 对已封口输出复核。
新分析仅用标准库读取小矩阵和保存 logits，不运行 Channel、receiver、优化或新仿真。
