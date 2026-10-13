# 终端先验×方差控制合同

前置：strong-terminal-oracles-v1的96T/96D及外部192raw PASS。三个固定H为EST、SUPPORT_ORACLE和TRUE_H；不改变原完整接收前缀。每个H补齐三种组合：RETAIN/PHYSICAL、ZERO/ORIGINAL、ZERO/PHYSICAL。RETAIN/ORIGINAL引用既有原始状态，组成完整2×2设计。

已知物理噪声方差使用原观测接口sigma2=10^(-7/10)；ORIGINAL是原sigma2_terminal，不重估。先验ZERO为显式零数组，仍走有限字母BP同一分支。固定温度2、20 BP迭代、LDPC maxiter50和clip20。288T后288D，1200秒/8GiB/单CPU线程。已核查前作业终止，campaign已分配约6.28GiB，低于本轮200GB上限。

每个新臂验证输入哈希、实际消费先验、BP内部complex128 H哈希、边数、原始外信息及APP恒等关系、算子次数与自身LLR译码身份；576份新raw回读。不得以新参数改变旧基准，保留所有32块。报告各H的四格配对结果与交互，不以最优格选择宣称统计收益。

该设计区分原方差与先验的作用，不自动识别残差方差偏差原因，也不是创新方法。H_true只指本次既有物理生成H，不代表完整G1传播已通过。方法、确认与论文闭合另有任务。
