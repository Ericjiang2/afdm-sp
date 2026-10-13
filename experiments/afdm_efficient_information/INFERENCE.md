# 冻结公共网格上的未知干扰参数推断

每个方法接收相同独立观测组，在同一公共物理参数网格上构造目标矩阵 `Q(Y,theta)`。真实参数只用于生成、定义独立校准条件及外部评分，不进入部署特征、候选筛选或模型选择。每个 R 使用同一组的前 R 帧。

多项式与四维得分方法以训练集冻结的共用残差协方差加权样本特征均值。候选响应均值在推断前构建一次并缓存。控制族使用有限 QPSK Gaussian mixture 的精确多项式均值；固定仿射回归的均值由同一仿射映射给出。实际族使用独立候选训练均值，另有独立 mean-validation，不称精确均值。高维或退化协方差使用显式 SVD/eigenvalue 秩阈值，无 jitter。全常数特征产生全零无信息目标。

检测统计量为 `D=min_(theta in null) Q-min_(all theta) Q`，联合估计为全网格 argmin，置信候选集合为 `Q(theta)-min Q <= c`。这对所有 nuisance 同时取 profile，无已知 nuisance oracle。控制 q 与 delta=sqrt(q) 只重命名同一候选 ID，不产生另一个算法或坐标收益。

独立校准的 m 个分数采用第 `ceil((m+1)(1-alpha))` 个次序统计量。若该秩大于 m，直接拒绝配置。检测阈值取每个公共 null nuisance 条件阈值的最大值；集合阈值取每个公共 true candidate gap 阈值的最大值。固定训练数据后，每个真实公共条件的新组与该条件校准组交换对称，因此严格大于阈值的错误概率至多 alpha（ties 保守）；再取最大阈值仍成立。保证对独立校准随机性与未来组取边际，不是给定某一次已实现阈值的条件保证，也不涉及网格外连续参数。非空集合含 argmin；其投影 hull 仅为离散候选集合宽度，不称连续参数置信区间。边界不使用 Wilks 或常规 Gaussian Wald。

控制 exact 方法是完整有限输入 likelihood；second Gaussian 的协方差仅为 `(tau+sigma²)I`，对 q/mu 无信息，独立 alpha coin 作为检验基线，q/mu 误差明确 unavailable。old_T 与 powers 在该控制族没有中心 mu 信息，mu 误差也 unavailable。实际族 Gaussian 基线必须使用真实二阶矩，不能沿用控制族的 scalar 协方差或无信息断言。

每个条件报告独立 eval group 数、false-alarm/power、Wilson 95% 区间、目标与联合参数 RMSE/bias、边界率、离散集合覆盖/宽度、所有失败。不同方法与 R 共享组，因此跨方法或 R 的行不视为独立实验。训练/候选响应构建/教师/校准/推断费用分开记录；检测、估计、集合共用目标矩阵，没有重复 likelihood。限定 N4、有限网格与 bounded CPU，未调用 receiver/decoder。
