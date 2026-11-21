# S4 软信息接口准备（不放行S4）

实际绑定链：loop9_cache_features._fast_bp → mp_detect_bp_torch；外环使用其高斯聚合mu/var，最后E1额外BP→demap_llr→LDPC。

四种量必须分开采集：BP逐边E×4 extrinsic概率；BP节点Gaussian mu_post/var_post；阻尼后x与sigma²/列功率经_qpsk_soft_decision产生的外环N×4概率；最后额外BP映射后的截断bit LLR。当前Gaussian聚合不是有限星座矩。

BP边投影exp(-dist²/(2v))，外环反馈exp(-dist²/v)，其v均按复数总方差构造。factor2必须作为显式温度对照，采集时不改算术。BP只阻尼mu_v2o而未同样阻尼var_v2o；外环又阻尼x，不能把阻尼均值/旧方差称为同一后验。BP内部complex128，外环回转complex64，均记录。

建议默认None观察接口：mp_detect_bp_torch(...diagnostic_observer)、_qpsk_soft_decision(...diagnostic_observer)、forward(...diagnostic_soft_observer)。区分dals_feedback、noise_feedback和final_soft_bp；小批次记录完整边信息，常规仅节点统计。真符号只在外部观察器闭包打分，不能进入BP输入。loop9实际shim须明确转发参数。

QPSK顺序[++,+−,−+,−−]，类别=2*Ibit+Qbit。稳定log-softmax计算符号NLL，Brier采用四类平方误差求和。有限矩mu=sum(a*p)，v=sum(|a|²*p)-|mu|²；Pd=.5时v∈[0,.5]，均值实虚∈[-.5,.5]。按帧聚类，分箱比较预测v与实测|truth-mu|²；记录零/负/截断数量。Gaussian圆形覆盖注明近似，离散最高概率集合另报实际概率质量。bit概率sigmoid(-LLR)与符号概率分开。

所有mu/v已含数据功率缩放。后续若使用H diag(v) H^H，不再乘(1-rho)。当前只完成接口研究，尚未采集可靠性数据或选择软反馈机制。
