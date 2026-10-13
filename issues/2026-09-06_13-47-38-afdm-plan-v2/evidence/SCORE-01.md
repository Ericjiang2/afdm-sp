# SCORE-01 冻结数值先验评分表

common_score.prepare_common_scores 在同一 y/Phi/C/S/有序候选上同时保存普通LS残差、T_old/q_old、D/q_perp、pi/sh2与完整三列分数。旧新两列都调用现有 assemble_lambda_percand；无prior列直接等于D。prepare_geometry_scores只调用一次原 _resid_geom 和 lookup，传入该次残差/数值prior，不用GLS gain重新lookup，不重训prior。

OLS保留输入dtype/device，旧白化CPU complex128，GLS保留输入dtype/device及对应秩阈值，装配/排名float64明确记录。prior逐列复制并哈希，禁止广播、无效概率、非正方差、非有限值。rank失败与active冲突使用共同eligibility mask，不补池；原历史A2完全不改。HOLD、空池、全active、全rank分别记录，拒绝项D/新分数保持None，不能填0伪排名。数学空S需显式prior；部署空S geometry拒绝，不编造bin。

rank_candidates直接排序登记float64分数，完全同分按冻结ordinal，不添加epsilon。hash覆盖dtype/shape/bytes；输出可用allow_nan=False序列化。共同prior数值与表内各分数逐ID对齐。

验收：test_common_score 6项 + test_projected_gls 4项，共10项通过；编译通过。集成测试调用真实 _resid_geom、whitened_suffstats、assemble_lambda_percand，并与原 make_genie_lambda 实际输出比较，complex64/128及有色C覆盖。白C复数反例T=(2/101,1)、D=(2,1)、q_perp=(1/101,1)通过；空S旧/新装配相同；near-tie不会被float32舍入抹掉。

本行完成评分组件集成，不声称共同候选已在receiver生成边界消费、完整事务或最终BP已使用GLS；这些仍由GATE/WIRE-05验收。J2全接口承诺保持pending。复用原函数，未另写评分公式，未修改历史接收算法。
