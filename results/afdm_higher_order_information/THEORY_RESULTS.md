# 控制模型与输入依赖：已执行结果

证明分别位于新实验包的 `THEORY.md`、`INPUTS.md` 和 `SCALING.md`。这里列数值核验，不能用这些数字替代证明。

| 核验 | 实际范围与结果 | 证据 |
|---|---|---|
| 四阶矩 | N4 的全部 256 输入与 N8 的全部 65536 输入；delay=0/N−1、两中心、四间距、不同 lag，共96项；最大误差1.54e−14以内 | `theory_moments_v1/` |
| 失效反例 | 非等模酉矩阵 I 的交叉功率为1而非0.75；合法 repetition 输入为0.22398而非0.75 | 同目录 `counterexamples.json` |
| 信息 | 8192独立整帧，前4096投影校准、后4096核验；原始信息257.71，批次SE8.29；校准后在后半样本上的有效信息163.34，批次SE6.85 | `theory_information_v1/` |
| 精确矩下界 | 三特征联合下界4.998；该值来自有限输入与Gaussian八阶矩解析消元，明显小于完整似然信息 | `information_summary.json` |
| 单侧得分 | 与独立直接协方差/Cholesky有限混合对照，log-density最大差8.89e−15；步长0.01→0.00003时得分差分RMSE3.502→0.01427 | `one_sided_differences.json` |
| KL | 补偿积分在 q=0.001 时，固定nuisance的KL/q²为121.95±5.39(SE)，校准投影路径为80.52±3.34；后者接近同一核验集score平方均值的一半81.67 | `KL_scaling.json` |
| 输入扩展 | uniform、已知首符号、非均匀improper cavity、合法8-bit repetition code；一般矩张量最大对照误差2.67e−14，自身incoming改变的差异均为0 | `theory_inputs_v1/` |

非均匀输入的时间输入伪协方差范数0.25666，二阶矩的q导数范数1.18780；repetition码的q导数范数10.09007。由此不能把无导频独立QPSK下“二阶信息为零”的结论复制到一般cavity。单个已知首符号这个特例恰好还原该功率统计，不能据此说所有导频都无影响。

三个理论stage总墙钟约1.462秒，新增观测仅信息stage的8192帧。信息数值积分是Monte Carlo，保留全部批次不确定性；经验特征协方差与精确协方差仍有明显差异，说明高阶统计的有限样本噪声不可忽视。精确下界来自解析矩，未用经验方差冒充证明。

R^(−1/4)是该控制模型中独立整帧重复的局部检出尺度；不是单帧N标度、估计器误差保证或全局唯一性。真实G0平台内KL严格为零，另见 `PRIOR_BRIDGE_RESULTS.md`。大型LDPC联合依赖不在本轮枚举范围内。

原始NPZ保存在每个stage本地目录；Git保留注册、终态和raw哈希。正式运行使用提交后的源码，环境及费用见对应 `environment.json` / `attempt.json`。三个stage均终态complete；没有receiver/decoder调用。
