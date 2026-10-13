# v3 STAT-01：工作统计一致性推导与源码审计

## Target / Status

目标为给定当前状态、固定字典与工作协方差时的局部投影评分及sigma单位审计。状态 **COHERENT AS STATED for working objective**，不声称实际coded条件似然已精确建模。

## Invariant Object / Assumptions / Notation

固定y、当前已缩放数据均值d_bar、已缩放方差V_d，u_bar=s_p+d_bar，Phi_i=G_i u_bar。工作目标J(S)=min_g (y-Phi_S g)^H C^-1 (y-Phi_S g)，C正定且本次候选比较不更新。C=H_hat V_d H_hat^H+sigma2 I；sigma2为方差单位。V_d对角是假设/近似，不是实际coded数据条件独立结论。

## Strategy / Derivation Map

1. 固定正定C作白化。
2. 当前子空间正交投影分离候选新方向。
3. 一维复LS得目标下降恒等式。
4. 回到原始观测，展开sigma拟合残差及全部交叉项。

## Main Derivation

[恒等式] C=LL^H，W=L^-1，W^H W=C^-1。令z=Wy，A=W Phi_S，P_A为其列空间投影，r=(I-P_A)z，v=(I-P_A)W Phi_i。

[恒等式，条件v非零] 新列只增加方向v，min_a ||r-va||² 的解为a=v^H r/(v^H v)，所以J(S)-J(S∪i)=|v^H r|²/(v^H v)。支持秩不足须报告；v=0不能除零并制造正收益。该恒等式不要求Gaussian分布，但只对固定C/Phi成立。

[边界] 若OLS先投影，原子与噪声协方差必须同投影，并在有效子空间求逆；不能将OLS残差配未投影的原子归一化。ridge完整目标另含惩罚，不能直接引用无惩罚的下降式。外层H、数据均值、C更新时，此局部恒等式不提供外层收敛保证。

[精确向量恒等式] e=y-H_hat(s_p+d_bar)=(H-H_hat)(s_p+d_bar)+H(d-d_bar)+n。
[恒等式] ||e||²/N为三项各自均方加三对2Re内积/N。同y产生的H_hat、d_bar会与n相关。测试中特意令H_hat=H、d_bar=d+n（H=I），残差为零而热噪声能量非零，数据误差与噪声的负交叉项恰好抵消。由此不能将拟合残差均方无条件解释为热噪声方差，也不能无条件套N-K自由度修正。

## Source Mapping

- `projected_gls.projected_add_statistics`：实际QR/白化/秩掩码，实现固定C局部下降；`common_score.prepare_common_scores`保留旧混合评分作为明确对照。
- `classical_joint_unrolled.residual_data_covariance`：输入已经缩放的有限符号方差，不重复乘1-rho。
- `feedback_diagnostics.compare_frozen_state`：未加权、统一方差、动态方差在同状态各自目标下比较，不比较不同目标绝对值判断优越。
- `classical_joint_unrolled.forward`：sigma2_new=||y-H_hat(pilot+x_hard_res)||²/N；soft模式的x_hard_res实际为再次有限符号软均值。sigma2_eff=0.7旧值+0.3 max(sigma2_new,1e-12)。这是平滑残差尺度，有下限；不是纯热噪声估计。
- SIGMA终端乘子作用方差sigma2，并重置原末端BP初态；不再平方乘子。

## Remarks / Non-claims

实际LDPC P非零已在COLOR修订中精确处理。当前接收工作C不含全部码间相关、伪协方差、参数估计不确定性或消息复用相关性；不得称其为完整coded条件统计一致似然。局部计算一致和生成模型完整性是两个不同命题。本轮没有偷偷将接收器换成增广实GLS/Kelly。

## Verification / Open Risks

严格良态独立NumPy重拟合检查c128相对误差<=1e-10、c64<=1e-4通过；相同精度下残差向量与能量闭合通过。既有共线/秩边界/空支持/无效C测试亦通过。无额外jitter修复无效C。

原f_mean的48个快照SHA与外生输入hash全匹配，9阶段共432状态审计完成；直接读取其probabilities、mu、finite_variance，恢复高置信错误子组的预测方差和实际误差。未重跑接收机、也未重求既有三目标的解。此轨迹明确不是B0，不能与新B0当同轨迹做阶段因果比较。详细数值见mission/evidence/STAT-01-feedback-audit.json；本文件不将其作为部署收益。

历史f_mean描述性恢复：outer1/3/6/9高置信错误码元数分别18/1803/2697/2921；这些错误子组实际误差和/预测方差和分别11.83/18.22/21.75/22.90。是同轨迹观测及条件子组，不将码元数当独立样本、不据此估计sigma对FER的直接因果效应。
