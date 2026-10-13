# 合法输入、pilot、improper cavity 与码约束

本文件给出 THEORY 控制 Gaussian 增益模型的一般输入扩展。**状态：COHERENT AFTER REFRAMING / EXTRA ASSUMPTION**：均匀独立 QPSK 简式只保留为一个特例；输入分布必须是声明的合法外部 cavity，与生成当前观测的增益、噪声独立。若依赖当前观测，这些是条件于冻结消息的工作模型，不自动等于真实数据分布。

令 `x=p+d`，p 是已知 pilot（或固定 pilot 符号），`v=B x`，B 包含共同 delay/CPP。统一对象是有限合法输入分布下的边缘观测概率。定义原始矩

`S_nm=E[v_n v_m*]`，`Q_nm=E[|v_n|²|v_m|²]`。

不论 x 是否有均值、是否 improper、是否相关，只要相应四阶矩有限且独立于 Gaussian 增益和噪声，就有恒等式

`E rr^H = C odot S + sigma2 I`，

对不同 n,m：

`E[|r_n|²|r_m|²] = tau²[1+cos²(delta(t_n-t_m))]Q_nm + tau sigma2(S_nn+S_mm)+sigma2²`。

当 n=m，公式换为 `2tau² Q_nn+4tau sigma2 S_nn+2sigma2²`。这是两个重合噪声 Wick 配对，不能直接把非对角公式代入。

因此一般情形

`E T_ab = tau²{[1+cos²(delta t_a)]Q_0a-[1+cos²(delta t_b)]Q_0b}+tau sigma2(S_aa-S_bb)`。

在 q=0，该表达一般不为零，其 nuisance 导数一般也不为零。使用 T 家族时要重算均值、完整协方差和 nuisance 方向；原模型中的自动正交性不再成立。另一方面，若 S 存在相应非零非对角元素，二阶矩对 q 的导数可非零，不能仍宣称 Gaussian 二阶近似信息为零。

一般四阶矩的完整求法是保留**原始**张量 `M_ijkl=E[x_i x_j* x_k x_l*]`，并作

`Q_nm=sum_ijkl B_ni B_nj* B_mk B_ml* M_ijkl`。

这包括 pilot 均值、非零三阶中心矩、pseudo covariance 与码依赖。若只在零均值、独立中心变量 z 的子情形，才可写

`E[z_i z_j* z_k z_l*]=C_ij C_kl+C_il C_kj+P_ik P_jl*+kappa_i 1{i=j=k=l}`，

其中 `P_ij=E z_i z_j`，`kappa_i=E|z_i|⁴-2 C_ii²-|P_ii|²`。非零均值时仅把均值加到这三个二阶配对上会漏掉三阶项，故实现直接枚举 raw tensor。

非均匀 QPSK 两个比特具有不同边缘概率时，`Var(Re d)` 与 `Var(Im d)` 一般不同，中心 pseudo variance `E[(d-E d)²]` 非零。后续高阶计算必须保留它；但 h proper 且均值为零，使无条件 r 的 pseudo covariance 为零，这不等于输入可按 proper Gaussian 替代。

合法 cavity 对目标比特 j 的因子为

`pi_-j(b) proportional 1{H b=0 mod2} product_(k!=j) exp[L_k(1-2b_k)/2]`。

改变 L_j 时该分布严格不变。自己的 incoming 必须从**因子乘积**里排除；仅从最后的 posterior LLR 减一项，不能修复一个已经重复使用同 y 的先验。若已知严格正 site f_j 和 `posterior proportional cavity*f_j` 的真实分解，可以除 site 后重归一化；site 为零或该分解未知时，不能由 APP 凭空恢复 cavity。

注册小例共四类：uniform/no pilot；首个 DAFT 符号固定为已知 `(1+j)/sqrt(2)`；8 个独立不等外部比特 LLR；8-bit 二流 repetition 线性码（I 四位相等、Q 四位相等，4 个合法码字）。每类保留实际支持和 raw tensor，用独立路径矩阵和 Gaussian Wick 交叉验证，并改变自己的 incoming 核对不变性。最后一类是合法码约束反例，不代表大型 LDPC 的完整联合依赖已经枚举。

生产反馈存在同观测复用与多轮依赖。本文件不证明任意 decoder 输出就是独立于 y 的 cavity，也不以真值码字或潜在 PDP 构造部署先验。具体能迁移的条件由 BRIDGE 逐项核对。
