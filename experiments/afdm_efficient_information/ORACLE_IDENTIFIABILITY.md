# 已知 nuisance oracle 与候选歧义补充合同

ORACLE-01/IDENT-01 只读取已完成 `inference_control_v1` / `inference_actual_v1` 的保存工件，补齐原 PLAN 的 oracle 上限对照和 C09 歧义比例。输入 registration/attempt SHA-256 在 `ORACLE_IDENTIFIABILITY_CONFIG.json` 固定；每个消费的 raw 和原注册模型在运行中前后校验。大 NPZ 不复制到新 source snapshot。共享300秒，0新观测、0新科学节点/积分规则；不用接收机或 decoder。原程序、判决、候选、模型和raw保持不变。

## 数学边界

对每个固定同 nuisance 的 null/alt 对，理想真密度似然比 `L=sum_r(log p_alt-log p_null)` 的 Neyman–Pearson 检验在给定真实 size alpha 下最大化功效（原子需要边界随机化）。任意在复合 null 下满足相同总体 level 的部署检验也在此简单 null 下有效，因此理想、已知参数和备择的 NP 功效是对应上界。这是理论结论。

本补充读取控制完整 mixture 的保存 logpdf，实际读取已经加密合格的 order24 logpdf。从原独立 null 校准组确定第 `ceil((m+1)(1-alpha))` 个 LLR 次序统计量，严格大于才拒绝。独立未来 null 组的错误概率对校准随机性取边际至多 alpha；这不保证给定这一次已实现阈值的条件 level。有限校准没有求得理想准确 size 阈值，实际积分也不是解析真密度。因此本次**经验 oracle 功效不是认证上界**，不能用它封顶另一方法的经验功效。保存 LLR mean/SE 只作 MC KL 诊断，不能变成认证信息上界。

控制的每个q>0与相同(mu,tau,noise)的q=0配对，共48对；实际每个delta=.24与同(mu,logtau,lognoise)的.18配对，共8对。所有原R均保留，共112个pair/R。原所有方法使用同一evaluation组，按null/alt角色逐组保存both/oracle-only/original-only/neither和拒绝率差SE，共1408配对行。不同备择复用同一null数据，不能将这些重复行合并当独立试验。

已知 eta 的 MLE 仅在同一原物理兴趣参数候选域、固定真实eta的子集内最大化保存 likelihood；共152个原condition/R。真 nuisance 只进入明确标注的oracle，未提供给原部署方法。原ID排序first-argmax保持；报告目标原生坐标和物理delta误差、边界率。与所有原方法的976行配对误差也保留，原方法目标不可辨识时paired error为null，不用任意tie-break伪造性能。

## 三类歧义不混用

1. **结构不可辨识**只沿用既有解析证据：控制old_T/powers的完整功率特征分布不依赖mu；控制二阶Gaussian工作族不依赖q/mu。后者不是完整物理mixture的性质。其余方法的全分布结构可辨识性标为`not_established`，不由有限likelihood样本相等推出。
2. **冻结评分准则等价**：moment目标 `Q_i/R=z^T Pz+c_i-2z^T w_i`，精确按原行向量惯例取`w_i=(m_i^T P)^T`、`c_i=m_i^T w_i`，即代码的`means @ inverse`。P在数学构造中对称，但此处不强行再次对称化保存的浮点数组。保存normalized means与precision后，相同(w,c)意味着相同实数系数多项式，对所有观测z成立。等价只针对存储系数定义的准则，实际浮点求值还可有舍入。代码给出严格系数类、类ID及精确相等矩阵；不把它自动当物理分布等价。
3. **有限数据argmin多解/近似并列**：原976行每组完整目标矩阵，exact集合使用`Q_i-minQ==0`。near集合使用预登记 `Q_i-minQ <= 64*float64_eps*max(1,max_i abs(Q_i))`。它是机器数值分辨诊断，不是统计置信集合；对目标加常数会改变相对尺度阈值，本次固定原目标不再归一化。联合候选数、不同兴趣参数数、不同nuisance向量数以及每坐标数分开保存；多解率给Wilson95，数量分布完整保留。所有原选中ID必须与first-argmin精确一致，否则报错。

moment系数的near关系逐分量比较 `abs(a-b)<=64*eps*max(1,abs(a),abs(b))`。它对称但不具传递性，只保存nearby矩阵和每个候选的近邻集合，**不取连通闭包、不命名为近等价类**。数值容差在生成前冻结；不按结果调大到统计尺度。

## 原校准与数据分区

从保存的calibration/evaluation slices恢复原R-prefix，实际full-observation数组含训练段，因此减去calibration起始offset再索引likelihood；控制offset=0。逐原方法重建全部校准条件、rank和最终max阈值，核对原非随机判决，不重拟合。二阶控制alpha硬币判决直接读原raw并核对计数，不再生成随机数。保存完整likelihood生成的reference目标与原calibration/evaluation目标须在1e-10绝对误差内一致，该容差仅为来源一致性检查，与机器ties容差分开。

## 冻结输出 schema `oracle-identifiability/1`

- `oracle_{control,actual}.npz`：`candidates(C,4)`、`pair_indices(P,2)`、`repeats(K)`；`calibration_llr(K,P,m)`、`evaluation_null_llr/evaluation_alt_llr(K,P,n)`、`null_rejected/alt_rejected(K,P,n)`、`cutoffs/ranks(K,P)`。
- `oracle_pairs.json`：112行，family/source_stage/pair_id/null_condition/alt_condition/null_theta/alt_theta/repeats/reference_method；`cutoff/rank/alpha/calibration_groups/calibration_marginal_error_bound`；`false_alarm/power={count,groups,rate,wilson95}`；`null_llr/alt_llr={mean,standard_error}`；scope/KL范围文字。
- `paired_cases.json`：1408行，family/pair_id/repeats/role/condition/null_condition/alt_condition/method；`groups/both_reject/oracle_only/original_only/neither`；`oracle/original`同bernoulli schema，`oracle_minus_original={mean,standard_error}`。角色null/alt是原数据条件，原方法不接收备择信息。
- `known_eta_mle_{family}.npz`：candidates/repeats、`selected_indices(K,C,n)`、`allowed_candidate_mask(C,C)`。
- `known_eta_mle_cases.json`：152行，family/source_stage/condition/repeats/public_truth/groups/allowed_candidate_ids；`target_coordinate_rmse/bias`、`delta_rmse/bias`、`delta_mse={mean,standard_error}`、`interest_boundary`同bernoulli schema；tie_break/scope。
- `mle_paired_cases.json`：976行，family/condition/repeats/method；`oracle_delta_rmse/original_delta_rmse/original_target_identifiable`；`oracle_minus_original_squared_error={mean,standard_error}`或null。
- `ambiguity_{family}_{method}_R{R}_c{ID}.npz`：original `selected_indices(n)`、`row_tolerance(n)`；每个prefix `exact/tolerance` 的 `_set(n,C)`、`_joint_counts/_interest_counts/_nuisance_counts(n)`、`_coordinate_counts(n,4)`。
- `ambiguity_cases.json`：976行，family/source_stage/method/repeats/condition/source_file/public_truth；`structural_status`与`original_unidentifiable_coordinates`；exact/tolerance各含`joint_multiple/interest_multiple/nuisance_multiple`与四个`coordinate_multiple`，均为bernoulli schema；`joint_count_distribution/interest_count_distribution/nuisance_count_distribution`为`[{candidates,groups}]`；groups/selected_indices_unchanged/maximum_row_tolerance/interpretation。
- `moment_equivalence_{family}_{method}.npz`：9个moment方法，`coefficient_rows(C,d+1)`、`exact_class_ids(C)`、`exact_equal_matrix/nearby_matrix(C,C)`。对应 `moment_equivalence.json` 存 family/method/source_file/structural_status/exact_classes/nearby_candidate_sets/exact_class_count/criterion/scope/nearby_scope。
- `input_audit.json`：每族的绑定记录、全部消费文件哈希、继承reference资格、原行数与pair数。`results.json`固定各类总行数，0新观测/节点/科学规则、0receiver/decoder、失败数、来源目标/校准最大误差及时间。protocol记录源码、环境、完整wall和新raw哈希。

测试仅确定性fixtures：同eta配对、实际offset/Rprefix、calibration不接收test标签、exact/near与目标/nuisance区别、非传递near、precision零空间准则等价、原ID不变、来源篡改明确失败。资格测试不是新研究采样。

正式入口（由主会话提交后GO）：`python -m experiments.afdm_efficient_information.oracle_identifiability --stage oracle_identifiability_v1`。所有数值模块在顶层预加载；只使用numpy和旧校准数学函数，不调用actual prior或新积分器，因此无需`frozen_components()`。仍使用统一单数值线程环境。
