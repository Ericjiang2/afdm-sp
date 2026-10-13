# 实际归一化先验上的完整推断范围

`inference_actual.py` 使用实际 G0、共同 rounded delay=0 的条件 PDP-marginal prior。16 个公共候选为 delta=.18/.24、mu=.34/.36、tau=.8/1.2、sigma²=.7/1.1；原生优化坐标为 `(delta,mu,logtau,logsigma²)`。零假设为 delta=.18，备择为 .24，是内点局部分离实验，不能作为 collision q-DQM 检验。

四组几何的有效 Gram 最小特征值均大于 .4，active atoms 相同，每点 ±1e-4 stencil 内离散分支稳定。候选之间的 PDP cutoff limits 分别为 [68,72]、[69,73]、[68,73]、[68,73]，因此整格不是单一 PDP 分支；likelihood 在每个公共点单独积分其合法条件 PDP law。局部 regular score 的理论不自动给出跨候选的全局光滑性。

训练/mean-validation/校准/评估分别为每候选 256/128/32组×4帧/64组×4帧，合计12288新独立观测。独立 mean-validation 只记录均值差与SE，不调参。评估 R=1/4 共用组的前缀。未知 nuisance 的 profile、split校准、离散集合解释与 `INFERENCE.md` 相同。

比较 old_T、powers、phase、固定实际教师四维输出、固定 Gaussian 控制教师四维输出、实际积分 likelihood、真实二阶矩匹配的 Gaussian 工作 likelihood。控制教师四维输出在这里仅是冻结的观测特征，候选响应均值由实际训练分布生成；没有声称它在不同 chirp、先验、基点上仍是精确 score。实际教师上游未收敛行完整保留并在下游披露。

`actual_signal_covariance` 给出 tau E[vvᴴ]；独立均匀 QPSK 经 unitary DAFT 满足 E[ssᴴ]=I，所以观测 covariance 为 diag(diag(tau E[vvᴴ]))+sigma²I。通常对角随几何改变，不能采用控制族 scalar I；Gaussian 仍仅匹配二阶矩，不是实际 likelihood。资格测试用完整256个QPSK枚举和独立 dense Cholesky 验证该协方差与密度。

积分 order12 与24计算所有候选/校准/测试观测对，逐项保存 log-density error 和资格 mask。order48检查每个条件/校准或测试 split 预登记前4行、候选0/3/8/15，共128×4个对；不声称覆盖剩余对。门限固定 .001。order24 的检测/估计另作数值敏感性对照，复用原观测，不增加样本；报告候选 argmin 分歧。任何失败对、组、候选均保留，不以放宽门限或删除样本获得“exact”结论。
