# Collapsed gain 数理核验协议

2026-10-07，COLLAPSED-MATH-01。先核公式、实际CPP与缓存一致性，尚不接入receiver。
沿用当前独立工作prior和数学笔记，不改变任何旧结果/生产逻辑/已有判决。

## 源码边界

共用已有gain-statistics Cholesky求解；旧gain_update与新collapsed调用同一实现，
保持旧数值运算顺序/检查/计数，新增logdet仅在需要时读取现有Cholesky。
在canonical PathMoments/source上提供固定source的candidate单列统计接口，
不得复制CPP/非均匀方差公式或把别的owner的source强塞进新op。
固定source/其余ν期间，Schur的A、b_−、factor与需要的A^−1只准备一次；
候选显式返回R列/b_i、s/t、J、m/C及全部实际费用；只有offset=0的9个候选请求并计算
解析导数，其余36候选不计算导数。候选评估不修改接收状态。
数理diagnostic复用现有protocol.run、runtime.preload与证据保存；不另造receiver harness。

## 输入、工作量与固定网格

仅使用原MATH-01：
`/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0/artifact/execution/MATH-01`。
输入为attempt.json与N8/N16/N1024各自inputs.npz、arrays.npz、checks.json，共10文件，逐SHA绑定。
这些是旧确定性数学fixtures，不是新的通信样本。

每个N使用两条原delay，ν取保存doppler_nodes的第一列，组成P=2案例；
另取第一条路径组成P=1案例。共6案例。沿用保存pilot/y/data_mean/data_variance，
不把原Pd=.55改成receiver的.5；noise σ²固定.7，C0=I/P。

每案例每条坐标均从同一基点独立出发，offset固定为
`[-2e-4,-1e-4,0,1e-4,2e-4]`；共45次Schur候选，全部执行，不能按结果增删/加密。
若保存基点或任一探测点越出[-3,3]则明确失败，不截断或临时换点。
每candidate与一次全量canonical PathMoments/gain_statistics/共同gain solver参考比较；
参考source归属自己的op，不共享一列公式制造自洽。完整参考45次，全部计费。

另外独立物理参考只针对P=2的原基点，按冻结Channel逐basis流式作用，
累加数据variance trace及均值matched/Gram；N1024不构建稠密N×N矩阵。
每N共2N次basis Channel.apply和2次均值响应，共2096个basis调用与6个均值响应。
P=1复用已生成的第一列物理统计，不额外物理调用。保存独立统计和实际计数。

## 验收与保存

1. 基点R/f对独立Channel参考；候选R列/b、完整m/C、full reduced score与Schur score
   （含固定其余块常数）、reduced ELBO直接trace/entropy形式逐项一致。
2. 对每条坐标在0点计算解析导数，并用h=1e-4与2e-4两种中心差分的full参考值核验。
   两层固定执行，不按误差挑层。共9个解析导数、18个差分对；复用45候选参考值。
3. 每candidate核Hermitian、precision residual、s≥P（仅有限精度允许下述容差），
   full C保持原非对角结构；P=1目标退化为|b|²/s−log s。
4. 每candidate以公共c=π(N−1)/N做一次明确矩阵旋转D，另调用共同gain solver求解
   旋转后的系统，共45次gauge solve（在45次完整canonical参考之外另计），核R/f、m/C和score的
   协变/不变关系；这属于坐标代数检查，不冒称新增物理观测或新的独立物理参考。
5. N8/N16/N1024各做一项等权局部Gaussian Fisher/MF方差比检查，比较独立2×2逆
   与(N+1)/(2(2N−1))；明确不是实际SP后验方差。
6. 一次执行3个原组件fixtures：
   `DataAndGainContracts.test_full_gain_covariance_solves_original_precision`、
   `DataAndGainContracts.test_incremental_coefficients_equal_fresh_canonical_recalculation`、
   `DataAndGainContracts.test_actual_objective_and_equation8_for_each_accepted_step`。
   保留fixture运算/拒绝步证据，与45个数学候选分账。

归一化误差统一定义||actual−reference||/max(1,||reference||)。
值/矩/不变量容差N8/N16为1e-10，N1024为1e-9；precision residual为1e-10。
两层差分均要求归一化误差≤1e-5；s下界容差为1e-10·max(1,P)。
任何失败保留全部已做工作和partial，不改容差，不重试，不自动进入receiver开发。
不得把参考结果反馈给候选、缓存选择或阈值。candidate/core本身不读参考。
Schur块准备、初始统计、full C的多右端identity求解等额外工作均按实际单列，
其确切次数随源码固定进最终配置，不藏在45次参考求解内。

stage CPU/wall各≤120秒，完整进程≤150秒及10秒退出宽限；单CPU、CUDA隐藏、
RSS≤4GiB、输出≤128MiB。0新observations、0新independent blocks、0receiver、
0decoder、0backend完整执行。fixture/物理basis/求解/导数/变换和保存各自实际计费。
source commit、隔离snapshot、imports、10输入、配置和launcher经独立字节准入后只运行一次。
所有远端写入/cache/tmp在/data/guoyikun，完成后按原规则回传/hash/独立raw核验。
