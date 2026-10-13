# TAIL-01 有限离散尾补全可行性合同（待独立审查与冻结）

本合同只读原 G1 物理 CPP 真信道及已审计 ridge `.1` 完整接收状态，32物理块×7/8dB，取 `dals[0]`/`dals[8]`（t1/t9）。工程块0/20包含在32块。0新完整接收、CE、BP、LDPC、FER，0连续κ搜索；真值只用于oracle层及全部层的外部风险评分。原raw、source、ridge核心和检测输出不修改。运行上限2h、20GiB、单线程deinlab。正式运行需先通过独立审查及主会话冻结本合同、脚本/输入SHA。

## 输入与三层配对

原 ridge 每状态的固定24个整数原子 `S={(support_delays[i],support_dopplers[i])}`、当前 `g_solution` 为**实际核心** `z`；`g_previous`、保存终端H/译码均不替代它。九个DA-LS状态的S须逐项相同。**真核心** `g*_S` 仅为同一原S24上真物理H的Frobenius投影，不增加真路径上的未选整数原子。三层共用S、同一固定预测器规则，仅换下列输入/中心：

1. `oracle_true_core_mixed_true_centre`：核心 `g*_S`，在原S含有且恰好对应**唯一**物理路径的delay用 `round(k_real)` 真整数中心；不存在或多路径delay用该状态实际中心回退。
2. `oracle_actual_core_mixed_true_centre`：原 ridge `g_solution` 完全原样，中心同上。
3. `deploy_actual_core_actual_centre`：原 ridge `g_solution` 完全原样；每个选中delay选现有S原子中 `|z|` 最大的k，精确平局取最小k，所有零值亦取最小k。无真值参与中心或输出。

两oracle臂**只是部分真中心混合诊断**，不是完整真中心、部署性能或上界；逐状态保存唯一/缺失/多路径delay数及中心替换覆盖。缺失/多路径不按真值筛除补全，仍用实际中心；误选delay仍可产生错误尾。每层分别以**同一核心且F=0**为其配对baseline；真核心+补全绝不与原ridge baseline混算收益。实际层S系数位对位不变。

## 有限尾域、物理相位与F

固定尾域 `T = { (l,k): l∈unique(S.delay), k∈[-5,5] } \ S`。每个原S整数原子从T逐项剔除，S与T不相交；不补未选delay，也不称全N泄漏消失。允许不同delay与k给出相同row shift，因为物理stride `2Nc1=5`，仍须保留完整 `U(l,k)` 的delay相位；不得按shift合并。真实H在S与S∪T的正交投影残差、有限尾可覆盖能量 `E_S−E_{S∪T}` 必须逐物理块保存，同时揭露W5外/未选delay残差。

在每选中delay内，把该delay的**所有现有**S k当输入core，不假定三正确主瓣。令整数中心c、`r=k−c`、`κ∈[-.5,.5]`。系数固定定义为

`a_N(r,κ) = (1/N) Σ_{n=0}^{N−1} exp(2πi(κ−r)n/N)`，

即 `FFT_N[exp(2πiκn/N)]` 的第 `r mod N` 项，配完整物理原子 `U(l,c+r)`。用128点Gauss–Legendre均匀κ求 `R_SS=E[aaᴴ]`、`R_TS=E[a_Ta_Sᴴ]`，固定名义 `q=.01`，`F=R_TS(R_SS+.01I)^{-1}`。它是单位路径功率/零均值独立核心误差的**理想先验基线**，非实际DA-LS误差协方差；不从目标真增益缩放q、不用保存V，不扫q/κ/尾窗/阈值。逐delay输出 `g_hat_T=Fz_l`；核矩阵/中心由现有S和冻结规则生成，不消费目标真κ。F=0 baseline始终保留。分析须记录 F生成/矩阵求解次数与新增非零尾原子/响应动作；固定估计自由度不等于固定检测成本。

生产符号准入：已本地验证 `physical_channel_matrix` G1 CPP真H与 `reconstruct_H_torch` 完整整数U，N31、stride5、delay3、ν=1.3的bin0/1/2对FFT的r−1/0/+1投影最大误差 `1.34e−15`。正式脚本仍对保存G1 H逐原子直接Fro投影与物理路径FFT系数核对，且小N测试用直接时域CPP→DAFT对物理U与F响应；不能仅验证理想FFT或按row shift评分。

## 风险、四个合法端点与成本

每层在同一核心下分别评价补全/不补全：

- 完整 `H_NMSE=||H_true−H_hat||²_F/||H_true||²_F`，H_hat由完整物理整数U在S∪T合成。可用已验证的正交投影恒等式加速，但必须检验alias相位及小矩阵dense合成。
- 无噪真实 `(p+d)` 响应 `response_NMSE=||H_true(p+d)−H_hat(p+d)||²/||H_true(p+d)||²`；真实d只进入外部评分，不进入实际F/中心/核心。

总384个层内配对比较：32物理块×2SNR×t1/t9×3层。合法层主端点为每物理块跨7/8dB等权的四个配对差（补全减F=0）：t1/t9×H/response；如算区间，预定同一32物理簇、20,000次共同配对bootstrap、seed `202609150701`、Bonferroni四比较同时95%百分位区间 `[.00625,.99375]`，只作已暴露开发描述。oracle层只列分布/中心覆盖，不给独立样本CI或部署晋级。风险正向仅使下一步同预算方法设计可讨论，**不启动FER**；阴性只约束有限W5/当前核心/名义q，不否定全N尾预测。

运行/审计分别守卫**旧 ridge 生产**source-v4 manifest `50fb12...` 与**本次分析** CE source-v4 manifest `176cfd...`；它们的 `classical_joint_unrolled.py` 不相同，不能宣称同一源码。共享的原CPP/DAFT生成模块须逐文件SHA相同。守卫工程+开发ridge summaries/raw-audits、原G1物理A、脚本/合同SHA；逐状态绑定F与物理真H record，并将保存的ridge A按新分析runtime的完整物理U作用 `p+state.mu` 重算、逐列比较，再核 `A@g_solution` 与F=0核心物理U动作；保存生命周期 `state.H` 与本次CE解生成的H可能不同，该动作差异须留痕而不能冒充同一估计。小N dense H/alias Gram直接测试，工程至少一组同row shift异delay的U内积检查。**运行顺序先块0/20×7/8×t1/t9×三层的24个比较**；全部上述守卫PASS后写持久`engineering-rows.json`与`engineering-admission.json`，之后同一次预算继续剩余30物理块，不重复工程比较。检查24个S相同及ridge原g_solution逐位不变、S/T互斥、有限尾残差闭合。一次生产结果，随后只读原始状态重读审计（注明同进程自审弱）；计实际F构建、投影、A核重算、响应、bootstrap、运行墙时与峰值RSS。失败/工程结果原样保留，不修改冻结原始产物。

## 可证伪漏洞

G1真H是全bin未截断CPP；W5同选中delay有限T可能只覆盖其一小部分。实际S中可能有错误delay/中心，F会从受反馈污染的z生成假尾。真中心混合oracle用路径真值，不能作为合法接收输入；真核心oracle也只是原S投影，不能免费赠真路径三核心。理想q与实际相关、有偏DA-LS误差不匹配，故不能从理想92%尾MSE下降预测G1收益。尾输出扩大检测图/CE等效列成本；本轮只算H与无噪响应风险，不计算译码收益。
