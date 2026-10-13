# 连续变分更新独立数学审查

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`；CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。仅审查条件公式与指定文献对照，不是 Mission 最终 REVIEW。

被审 `CONTINUOUS_VARIATIONAL_UPDATE.md` 最终 SHA256：`076c277553f938a577f8eb69b1759d54798f67c96a4070714a85b6321818d0f9`。审查沿用 proof-checker；独立性 medium，runtime 模型标识不可见，不猜测名称。没有数值计算、求积、RNG、仿真或 SSH。

## 结论

**数学 PASS**：式 (6)–(19) 在声明的独立工作先验、固定整数 delay、真实 CPP 和 mean-field 因子族内成立。两处边界表述已经由主线程修订并经补审确认；没有剩余必须修复的数学错误。

这不是精确生产 posterior、连续求积精度、CAVI 实现或接收性能的通过结论。保留有用的既有方法到 SP-AFDM 的适配候选；有 antecedent 本身不是否决理由，也不能把适配前的通用原理重新计作首创。

## Findings (fixed)

本代理只写本报告；以下原文修订由主线程完成。

- File：`CONTINUOUS_VARIATIONAL_UPDATE.md` §8 单径检查。Issue：`p=cAe0` 经非零 delay 后，`L_1 p` 支撑在 `n=l_1`，并非 n=0，式 (11) 不一定返回原先验。Fix：已加 `l_1=0` 条件；补审通过。另一种正确写法是直接要求 `L_1 p=ce0`，但无需再改。
- File：同文 §4 式 (11) 后。Issue：有限 Fourier 多项式不一定以 N 为最小周期，活跃谐波可给更小周期，常数情形更退化。Fix：已改为“具有周期 N，最小周期可因活跃谐波而更小”；补审通过。

## Findings (not fixed)

无剩余数学错误。连续积分、数据更新调度、生产先验支撑、获取及 LDPC 接口等原文已明确列为未解决问题；本次不把它们伪装成已实现的完整算法。

## 独立公式核验

| 公式 | 核验与边界 |
|---|---|
| (6) | 令 r=n-l。r<0 时 CPP 的 `exp[2πic1(N²+2Nr)]` 恰好消掉 IDAFT 在 r+N 处的额外 chirp；Fourier 的额外 `exp(2πik)` 为 1。无须 `2Nc1` 为整数；必须保持整数 delay 与前缀覆盖。 |
| (7) | 行乘积 `L_i[n,k] conj(L_j[n,k])` 的 Fourier 部分为 `exp[-2πi(l_i-l_j)k/N]`，故使用前向 FFT 的索引 `l_i-l_j`；c1 项为 `2n(l_i-l_j)-l_i²+l_j²`。c2 消去。`K_ii=mean(v)`，不同 delay 的 isotropic cross term 为零；相同 delay 不得删。 |
| (8)–(9) | 输出能量交叉项使用 `E[h_i conj(h_j)]=S_ij` 与 `R_ij`，各 pair 的共轭合成 `2 Re`。同路径的两侧共享同一个 ν，所以自项为 `S_ii tr M`，不乘 `|phi_i|²`。 |
| (10)–(11) | 从期望平方误差取所有含 i 的共轭 pair，得到 `m_i s_i conj(Y)-sum_{j!=i}S_ij R_ij conj(phi_j)`，符号及 `2/sigma²` 正确。先验项必须是原 `pi_i` 或正确的联合 prior 期望，不能用同一 y 的窄窗口重复当独立 prior。 |
| (12) | 正权求积定义合法有限概率分布，保持 characteristic kernel 的正定性；不保证等于原连续积分。固定节点的另一个离散模型与连续变分模型必须区分，动态求积不自动保持连续 ELBO 单调性。 |
| (13)–(14) | `Gamma_ij=E[B_i^H B_j]` 使用 `R_ji`，与 (8) 的 `R_ij` 正好反向。Gaussian prior 下配平方得到所写联合 C、m；完整 C_ij 必须保留。`C0>0` 保证精度矩阵可逆。 |
| (15) | 展开坐标 d_k 后，`e_k=(r-Gp)_k-sum_{j!=k}G_kj mu_j`。故 `r-G xbar+diag(G) mu` 扣除的是未知数据均值的 self contribution，保留已知 pilot。QPSK 等模可删 `g_k|a|²` 常数，但不能把 e 中的 g_k 也删掉。 |
| (16)–(17) | `H^H H` 的 pair 是 `conj(h_i)h_j`，对应 `S_ji`；伴随顺序是 `Pi_i^H` 后接输出索引上的 `conj(c_i)c_j conj(phi_i)phi_j`。r 使用 `conj(m_i)`。两个索引方向不能统一替换成同一个 S 下标。 |
| (18) | 第一项等于对随机 h 的平方范数期望，第二项为 `S_ii(I-Wbar_i^H Wbar_i)`，因 `|phi_i|<=1` 为 PSD。两者合起来补回同路径自项；省掉第二项是独立副本错误。 |
| (19) | `conj(L_i[n,k])L_j[n,k]` 给出 `Delta=l_j-l_i`、常量相位 `c1(l_i²-l_j²)` 和 `exp[-2πi Delta k/N]`。所以 xi 的正号和最后一次前向 FFT 都正确，gain 系数仍为 S_ji。精确对角元为实非负；完整 G 仍可依赖 c2。 |

式 (11) 的指数是有界有限 Fourier 和，配合正常化原 prior 给有限正 Z；它不是一般的单 von Mises 密度。其意义是指定 q 下的 `E log p` 坐标最优，不是 `log E p` 或完整有限 QPSK 边缘似然。QPSK soft factor 的非零 pseudo-covariance不影响 proper-noise 复线性平方范数只需 M 的结论，也不意味着 posterior proper/Gaussian。

顺序 ν sweep 在冻结 q(d)、q(h) 时，可按 delta-phi 更新其他路径系数，pair 工作为 O(NP²)；所有连续积分仍另计 O(N sum Q_i)。joint gain 解另需 O(P³)。一次 Gram matvec 和 diagonal 生成可以便宜，不表示逐符号顺序 sweep 同样便宜；原文对 Jacobi/CAVI 的区别和未证明收敛性表述正确。

## 先验与极限

生产 G0-normalized gain 与几何耦合，G1 必须原样复用该 gain；连续 CN×q(ν) 一般不能满足归一化曲面支撑，reverse KL 的支撑障碍成立。硬 LDPC codeword prior 与普通非退化独立符号因子也有同类障碍。这里的 Gaussian gain / independent-symbol 工作模型可以合法研究，但不能标作原生产先验的精确 VB。

`m=0,C` 对角时 a_i 全零；P=1 时该坐标不直接含 C_ii、V；修订后的零 delay 时间脉冲例返回 ν prior；Dirac geometry 时 (18) 修正消失，再取 C=0 恢复确定信道 H^H H。这些是正确的可证伪极限，不能据此保证实际初始化收敛或支持获取成功。

## VALSE 原文定点核查

已读保存的 `raw/1604.03744v2.clean.txt` 中 III-A 式 (16)–(17) 与 III-B 的 J 定义、式 (20)，未重搜全领域。文本 SHA256：`82dd43ce4e9d3120aaadaa6032c622160c8827532fe926d12eb9f52be793cf7e`。

- 式 (16) 明确 `q(theta_i) ∝ p(theta_i) exp Re(eta_i^H a(theta_i))`；式 (17) 同时含 residual×mean-weight 项及完整 cross-covariance 修正 `C_{l,i}`。连续多谐波变分频率更新和增益交叉协方差不是本项目首创。
- J 定义明确 `J_ii=M`，非对角才取 expected steering 的内积；这已经保留同一路径 self energy，并非普遍使用 mean steering Gram。式 (20) 是对应的联合 Gaussian weight 更新。
- 原文说明频率因子通常没有解析 steering expectation，并使用 von Mises 混合近似；不能把 (16) 本身误读为精确单 VM 闭式。
- `LITERATURE.md` 对这些事实的描述正确。SP-AFDM 中 `R_ij=s_i conj(s_j)+K_ij` 的共享未知数据和真实 CPP 仍需具体处理，不能只把 VALSE 的已知原子改名；但这种有用适配可继续评估，无需因已有谱系而直接丢弃。

本核查支持降低 firstness 声明，不支持否定或确认实际收益。完整物理 F1、同 prior 的 point-geometry 控制、适用的 Bayesian 基线和全成本比较仍是后续价值判别。

## Verification

- 公式与边界：PASS，含两处修订复核。
- 文献定点核查：VALSE (16)–(17)、J 自项与 (20) 和当前非首创声明一致。
- Lint / TypeCheck：本报告为 Markdown，不适用；代码静态检查另见 `MATH_ADMISSION.md`。
- 数值 Tests：未运行；没有科学执行、SSH 或提交。数学静态 PASS 不是 runtime PASS。
- 所有权：仅本报告；未修改被审原文、源码、CSV、STATE、既有证据或 spec。当前工作没有新增可执行规范需要同步。
