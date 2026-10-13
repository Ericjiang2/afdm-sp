# REP-02 — 独立表示参考与分项误差

固定最终唯一整数支撑，复用解析Frobenius投影；独立路径逐个调用真实system.gen_h_daft生成单位原子，再用NumPy lstsq(rcond=1e-12)求密集参考。先验证完整复合并truth重建实际H_true，明确N、chirp位移、Python约定、接收机delay域一致性。独立是数值实现独立，不是另一物理模型。

真实1024×40样本：A0/A2均E_repr=0.001252842286673214，密集投影差2.5604980267954097e-13，rank=40。完整基底hash、奇异值、残差及独立密集LS费用已存。单元覆盖复抵消、域外真值、空S(E_repr=1)、实际生成器小系统；零真值比例显式undefined。重复非法整数支撑拒绝，合法唯一整数原子在注册域内为满秩；报告真实rank而非伪造秩亏案例。

分列原子阶段差集、actual channel error、actual-to-best-projection距离、实际BP阈值损失。实际H不一定处在给定S张成空间，不默认用Pythagoras相加；各比值分母不同亦不可相加。历史曾剪再入也不是最终因果损失。无干预只称关联。

证据同REP-01及mission-rep-math-review-20260906.md。所有密集参考在完整接收后执行，真值不进入A0/A2消费者。约640MiB的1024×40 complex128基底另有SVD/堆叠工作区，不将其费用当免费观察器。
