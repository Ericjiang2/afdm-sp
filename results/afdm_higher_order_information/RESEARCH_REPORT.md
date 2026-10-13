# AFDM 高阶信息与 LLR 判别积分：研究裁决

本轮支持一个严格限定的理论结论：在独立 QPSK、Gaussian 双径和正噪声的控制模型中，匹配二阶矩的 Gaussian 近似确实丢失了可辨识的路径间距信息。但实际 G0 归一化生成器存在完全不可辨识的平台，当前低成本四阶估计器和自适应积分候选也没有显示稳定优势。保留具体证明与失效边界；本轮不提出新的生产性能或论文首创主张。

执行范围来自本轮 Mission 的 `PLAN.md`，逐项状态只由同前缀 CSV 管理。源码在 `experiments/afdm_higher_order_information/`，全部研究结果和不可覆盖的尝试在本目录。旧研究、生产接收机及论文已接受主张保持原样。

## 数学对象与已证结论

控制模型令 Doppler 半间距为 `delta>=0`（bin），`q=delta²`，总路径功率为 `tau>0`，噪声方差为 `sigma2>0`；中心、总功率、噪声均作为 nuisance 参数。在共同已知整数 delay、单位化等模 DAFT 和独立单位功率 QPSK 下，令 `t_n=2*pi*n/N`、`T_ab=|r_0|²(|r_a|²-|r_b|²)`，有

`E[rr^H]=(tau+sigma2)I`，

`E[T_ab]=(1-1/N)tau²[cos²(delta*t_a)-cos²(delta*t_b)]`。

在碰撞点，`dE[T_ab]/dq=kappa=(1-1/N)tau²(t_b²-t_a²)`，而 `E[T_ab]=0` 对 nuisance 邻域恒成立。有限星座 Gaussian 混合的正噪声保证单侧平方可积得分与导数交换，因此

`I_eff,qq(0+) >= kappa²/Var_0(T_ab)>0`。

这里已经投影掉 nuisance；对应的单 Gaussian 二阶模型对 q 的信息为零。证明包括共同 delay/CPP 的适用不变性、有限非零方差和奇异 nuisance 切空间处理，见 `THEORY.md`。这不等于未知多路径生产模型的可辨识性。

同一正则控制族内，局部最有利 nuisance 路径满足 `KL~I_eff*q²/2~delta⁴`。独立整帧重复 R 的非平凡局部检出尺度是 `R^(−1/4)`。它不是单帧 N 的标度、全局唯一性或有限样本估计误差保证。多个 lag 和跨 SNR 共享底层信道不能增加独立 R。

真实先验为固定球面基变量的几何相关推前 `h=D^(1/2)z/sqrt(z^H D^(1/2)R_G0 D^(1/2)z)`。必须保留 D、R 和物理响应 B 的完整导数。N=16、整数中心、共同零 delay、当前删弱门限下，

`delta_star=N/pi*atan[0.1*sin(pi/N)/(1+0.1*cos(pi/N))]=0.09047461579...`。

`0<=delta<delta_star` 内 G0 只保留同一个整数原子，归一化后仅剩均匀随机全局相位，输出分布与间距无关，原始及有效信息严格为零。G1 复用这些潜在 gains 而不消去 Gram 零空间时，delta>0 可具有无限二阶矩；这否定了该支路上的有限矩推导，**并不证明概率分布或 Fisher 信息本身不存在**。正定光滑分支只给出另行检验有效信息的充分条件，未宣称实际先验普遍正信息。

## 十项目标与证据

| 目标 | 实际交付与边界 | 证据入口 |
|---|---|---|
| 控制四阶矩 | 解析证明；N4全部256输入与N8全部65536输入，共96项对照，最大误差1.54e−14；反例保留 | `THEORY_RESULTS.md`、`theory_moments_v1/` |
| 有效信息与规模 | 8192独立帧；原始信息257.71、同样本投影161.78；独立校准后核验163.34，批次SE6.85；单侧差分和KL加密 | `theory_information_v1/`、`SCALING.md` |
| 真实先验 | 12几何dense Gram误差2.22e−16；120矩案例中114有限矩通过684项加密检查，6个G1无限矩反例 | `PRIOR_BRIDGE_RESULTS.md`、`prior_v2/` |
| 输入依赖 | 一般二/四阶张量、已知pilot、improper cavity和合法小码枚举；自身incoming不变；大型LDPC未枚举 | `INPUTS.md`、`theory_inputs_v1/` |
| 高阶特征与估计 | 独立训练/校准/评估；28672观测、18条件、180方法记录全部保留；显式未知nuisance、先验失配与不可辨识 | `ESTIMATION_RESULT.md`、`estimation_v1/` |
| LLR理论 | log比值误差界、共同节点条件IID方差、独立pilot及正确pi/rho；负相关和无限方差反例 | `LLR.md`、`test_llr.py` |
| LLR公平比较 | 48案例、2304消息；所有参考收敛；固定共同Sobol与共同/独立IID基线；零新节点的独立保存数据复算 | `LLR_SUMMARY.json`、`llr_v1/`、`llr_recount_v1/` |
| 旧生产联系 | 6条N1024旧观测、3共享簇；6条均可计算统计，0条满足控制模型；17输入前后哈希一致 | `bridge_v1/` |
| 一手近邻 | 实读7份正文，逐命题区分经典工具与本轮特定对象；未完成系统性首创证明 | `LITERATURE.md`、`LITERATURE_SOURCES.json` |
| 综合与交付 | 本报告、可复现来源、费用与失败记录；最终独立审查和交工单由Mission REVIEW行单独记录 | `EVIDENCE_AUDIT.json`、同前缀review/handoff |

上表的实验包文档指 `../../experiments/afdm_higher_order_information/` 下同名文件。信息值是Monte Carlo结果，精确证明和数值标准误分开。三项T的联合**线性矩信息下界**为4.998；不能把它除以完整似然信息后的比例当成严格的信息保留率，因为没有计算完整特征分布的Fisher信息。

## 方法结果与分支裁决

当前四特征 GMM 对 q 和 delta 使用完全相同的11781个物理候选，两者结果完全一致。Gaussian未知nuisance的6个条件中，R=16相对R=1的半间距RMSE改善3项、退化3项；delta=.2的两种条件在R=16时检测仅0/64、3/64。高噪声G0平台的噪声参数边界率为98.4%—100%。这些是完整开发结果，不支持稳定估计优势；输出一个数值间距不代表真实G0平台被识别。

LLR候选为独立64节点pilot拟合、随后使用正确权重的防御混合重要性采样。比较的是同一积分对象，pilot及所有候选响应计入费用。Gaussian/QPSK下候选与固定共同Sobol均需4096预算才达门限，平均完整消息成本分别15.741与15.288毫秒，Sobol误差更小。Gaussian-outside下，固定共同Sobol在1024预算达标约1.806毫秒，候选需4096预算约6.240毫秒。sphere/QPSK候选在最大预算仍未达标；sphere/Gaussian-outside两者均4096达标，未见候选优势。所有保存参考下，48个分组的通过/失败分类均稳定。小幅计时差不作为稳健速度排序。

因此保留控制模型的信息缺失定理、合法输入推广和实际归一化边界；把当前T族收窄为证明与诊断构造；停止对当前GMM及该proposal候选作性能提升宣称。高阶统计、q坐标、GMM、有效得分投影、共同采样和正权本身均为经典工具，不作为首创。新的具体数学结果是否足以构成论文贡献仍须更完整的领域近邻论证。

## 费用、失败与复现

全部登记阶段（包括失败尝试）合计墙钟171.669秒、CPU170.163秒，登记新开发观测36876个，检查时输出约495.5MB。LLR参考计算149.551秒，完整消息合计11.866秒；其余成本见各stage。登记墙钟从记录器入口起算，包含注册、哈希、快照、计算和写盘，**不含解释器启动与入口依赖预加载**，不是部署时延。

失败保留两类：`prior_v1` 因首次载入Torch改变线程池清单被记录为invalid_partial；预加载修正后用`prior_v2`完成；一次估计启动因源码未提交被准入检查拒绝，生成观测为0，随后补交源码才正式运行。6个无限矩案例是数学结论，不是被删除的失败样本。当前49项新包测试与编译检查通过；169项旧源码/终态/CSV基线哈希不变；全部stage快照及完整终态工件哈希校验无差异。

原始NPZ与source_snapshot保留在本地stage目录，Git保存注册、终态及其SHA-256。无需重新仿真即可运行保存数据复算与哈希核验。重新生成研究必须使用新stage名字；先提交任何源码修改，设置五个数值线程环境变量为1和`CUDA_VISIBLE_DEVICES=''`，再使用 `/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_higher_order_information.<module>`：

- `theory_study --mode moments|information|inputs --stage <新名字>`，理论三项分别运行。
- `prior_study --stage <新名字>`；`bridge --stage <新名字>`。
- `estimation --stage <新名字>`；`llr_study --stage <新名字>`。
- `llr_recount --stage <新名字>`，只读已保存LLR数据，0新节点和观测。

各阶段受累计100000观测、2GB输出与预登记截止限制；不能无条件批量重跑。训练4096独立帧；估计校准384个16帧组；估计评估384个16帧外生组跨3种先验共享，R=1复用首帧。LLR的12条观测来自3个共享外生draw，48案例及算法重复不增加独立信道分母。全程新增生产receiver、decoder、确认流调用均为0。
