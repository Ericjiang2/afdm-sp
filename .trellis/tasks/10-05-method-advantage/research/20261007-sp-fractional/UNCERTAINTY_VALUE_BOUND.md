# Research: Doppler 不确定性的可证影响界与条件性价值尺度

- Query: 严格区分 mean-point 近似的全局算子界、局部 Fisher/Laplace 尺度及“首坐标不确定性可能已非主要瓶颈”的有限证据检验。
- Scope: internal；解析推导及已读源码相关性，无新数值计算。
- Date: 2026-10-07
- Active task / row: `.trellis/tasks/10-05-method-advantage` / `QUAD-DIAG-01`
- Ownership: 仅本文件；未修改代码/其他记录，未仿真、SSH 或重新启动生命周期。

## Findings

### 结论先行

**用真实均值作 point 时，Doppler 方差给出可证的全局 mean-operator 误差界；峰曲率本身不给这个方差上界。** 在固定 gain/data 因子及路径独立的当前 mean-field 模型中，该误差可以继续传播到 Gram、固定数据 logits 与 expected log-likelihood。单路径同路径 Gram 项完全不依赖 Doppler 分布，是一个重要的精确抵消。

`|h|² Var(ν)` 与噪声归一化后出现 `O(P/N)`，只能作为正确 slots、局部可辨识、有效高信息量、单一主模态、合适 Laplace 近似下的**每样本响应不确定性功率尺度**。它不是所有输入的价值上限、总体 likelihood 的消失界、完整 receiver 或 BER 界。

主会话给定背景：前 8 个保存的首坐标势局部曲率约 `8e3–2.36e4`，局部宽度约 `.0065–.011`；N=1024，SP dense pilot/data 功率为 `.5/.5`。这里不新增任何代入计算，不把局部宽度当成已测全局标准差，不推广到其余 slots 或迭代。

### 文件、代码模式与约束

| 已读文件 / 位置 | 相关事实 |
|---|---|
| `experiments/afdm_sp_fractional_20261007/moments.py:94,100` | `S=Cov(h)+μμ*`，φ 为各路径 Doppler 的特征矩。 |
| 同文件 `:140–151` | expected quadratic 的同路径项为 `tr(S)·source.energy`，交叉项用各路径 φ 乘积。 |
| 同文件 `:177–210` | Gram、Gram diagonal、mean adjoint 的精确工作模型实现。 |
| `experiments/afdm_sp_fractional_receiver_20261007/data_step.py:108–111` | `z=b−G(pilot+m)+diag(G)m`，QPSK target logits 为 `2 Re(z·symbol*)/σ²` 加固定先验。 |
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py:88,118,168` | full covariance gain update、顺序坐标更新、固定 data block；point 模式并非默认取连续因子的均值。 |
| 本目录 `QUADRATURE_CONCENTRATION.md`、`UNCERTAINTY_COMPRESSION_COST.md` | 已审局部宽度、全局矩误差及 fixed-state 算子误差；本轮不重审原公式。 |

Related specs / task constraints：原物理 DAFT/CPP、独立路径 Doppler 的工作因子化、full gain covariance、SP 未知数据与现数据步单调性合同不变；以下比较固定其余因子。没有声称加载了新规范。

### 1. Mean-point 的全局界：不需要单峰

令 `t_n=2πn/N`、`T=max_n t_n<2π`、`D(ν)=diag(exp(it_nν))`。设 ν 有有限二阶矩，均值 `νbar=Eν`、真实方差 v。当前支持 `[-3,3]` 为凸区间，故均值仍是合法 point。

实轴指数 Taylor 余项满足 `|exp(ix)−1−ix|≤x²/2`。对 `X=ν−νbar` 取期望，线性项因 EX=0 消失，所以

\[
\|E D(\nu)-D(\bar\nu)\|_2
=\max_n|E e^{it_n\nu}-e^{it_n\bar\nu}|
\le\min\{2,\tfrac12T^2v\}=:\delta.
\]

这是对真实分布的全局界，**即使分布多峰仍然成立**；多峰时 v 往往较大，界可能没有实用约束力。单峰假设仅在尝试用局部曲率估计 v 时出现。

若 point 使用 `ν0≠νbar`，则只能进一步用

\[
\|E D(\nu)-D(\nu_0)\|_2
\le\min\{2,\tfrac12T^2v+T|\nu_0-\bar\nu|\}.
\]

因此“围绕均值的方差小”不能自动证明当前 point backend 与边际化接近：其最优化点可能是另一个 mode，或对应另一条迭代路径。

#### 局部曲率与方差上界的区别

- 两个分离的窄峰可以各有极大曲率，而总方差由峰间距控制。均值甚至可落在低密度谷中；不能将任一峰的 `1/κ` 代入上界中的 v。
- 一个足够强、可证明的条件是**整个支持上** `V''(ν)≥κ>0`，其中 `q∝exp(−V)`。令 μ=Eν，在有限支持 `[a,b]` 上分部积分有 `E[(ν−μ)V'(ν)]=1−[(b−μ)q(b)−(a−μ)q(a)]≤1`；强凸性使左侧至少为 `κ Var(ν)`，故 `Var(ν)≤1/κ`。这要求全区间强对数凹，不能由记录的峰点曲率替代。
- 实际 Fourier 势通常不满足全区间强凹条件。可靠全局方差应来自已受控的全区间积分及尾质量，或其他确实有效的全局界。

### 2. 固定 mean-field 状态的 mean-operator 与 Gram 影响

记 A 为单位ary DAFT，T_i 为精确 CPP/延迟算子，`H_i(ν_i)=A D(ν_i)T_i A*`。令 `μ_i=E h_i`、`S_ij=E[h_i h_j*]`；当前因子化假设 gain 与各 ν_i 独立，各 ν_i 也相互独立。定义 `bar H_i=E H_i`、`H_i^0=H_i(Eν_i)`、`δ_i=min(2,T²v_i/2)`。

保持同一 μ、S，只将 ν 分布替换为其均值，则

\[
\|\bar H-H^0_{mean}\|_2
\le h_v:=\sum_i|\mu_i|\delta_i,
\qquad \bar H=\sum_i\mu_i\bar H_i.
\]

同路径始终满足 `H_i(ν_i)*H_i(ν_i)=I`，因此

\[
G=E[H^*H]=\sum_iS_{ii}I+\sum_{i\ne j}S_{ji}\bar H_i^*\bar H_j,
\quad
\|G-G^0\|_2\le g_v:=\sum_{i\ne j}|S_{ji}|(\delta_i+\delta_j).
\]

这里 `||bar H_i||≤1`、`||H_i^0||=1`，两算子乘积差用三角不等式即可；无需额外 δ_iδ_j 项。**P=1 时 G 与 G⁰ 完全相同**，不管 ν 是单峰还是多峰。若 S 非对角交叉权重较大，多路径 Gram 差仍可能显著；不能只看每个 v_i 或只用 gain mean 的平方替代完整 S。

### 3. 数据 logits 和 likelihood：界含能量与噪声权重

在同一固定数据因子下，记 `m=E d`、`v_d=Var(d)`、`x=pilot+m`、`b=bar H*y`、`d_G=diag(G)`。数据 target 的 `z=b−Gx+diag(d_G)m` 因 mean-point 替换产生

\[
\|\Delta z\|_2
\le h_v\|y\|+g_v(\|x\|+\|m\|)
\le h_v\|y\|+g_v(\|pilot\|+2\|m\|).
\]

QPSK 每个符号模为 `sqrt(P_data)`，因此逐行 target-logit 误差满足

\[
\lambda_n:=\max_a|\Delta L_n(a)|
\le\frac{2\sqrt{P_{data}}}{\sigma^2}|\Delta z_n|.
\]

可用上面的 2-范数界统一控制，但实际逐行 Δz 通常更有信息。对同一 target 的归一化 log probability，误差至多 2λ_n；bit LLR 是两个 logsumexp 的差，也至多改变 2λ_n。若还比较固定 β 的同一个几何 proposal，target 误差先乘该步 η。**这没有证明接受层、后续迭代或最终判决保持不变。**

固定 q_h、q_d 的 expected quadratic 为

\[
Q=\|y\|^2-2\Re(y^*\bar Hx)+x^*Gx+d_G^Tv_d.
\]

所以 expected log-likelihood 差满足

\[
|\Delta E\log p(y|h,\nu,d)|
\le\frac{2\|y\|\|x\|h_v+g_v(\|x\|^2+\sum_n v_{d,n})}{\sigma^2}.
\]

这是有限状态下可证的上界，不是其必然达到的量级。N 维信号能量与 `1/σ²` 可能放大很小的算子差；不能仅凭 δ_i 小宣称 logits 或整个 block 的 likelihood 差小。比较的是 likelihood 项/固定 data objective；把连续 qν 改成 Dirac 会改变其熵，不能把该界叫作完整连续 ELBO 差的界。

### 4. 另一种量：随机响应功率为 O(|h|²v)，不等于 mean bias

已知单路径 h、固定发送时域向量 s 时，

\[
E\|h(D(\nu)-D(\bar\nu))s\|^2
\le |h|^2v\sum_n t_n^2|s_n|^2
\le |h|^2T^2v\|s\|^2.
\]

这是随机响应相对 mean-point 的均方误差，来自 `2−2cos(tX)≤t²X²`。相反，**mean-operator bias 的平方**最多为 `|h|²T⁴v²||s||²/4`；一个是一阶 v 的随机功率，一个是二阶 v 的均值偏差功率，不能混写。

在当前路径独立/gain 独立于 ν 的因子化下，对固定 s，令 `bar H(h)=Σ_i h_i bar H_i`，则 ν 引起的中心化响应功率精确为

\[
V_\nu(s):=E_{h,\nu}\|(H(h,\nu)-\bar H(h))s\|^2
=\sum_iS_{ii}\sum_n|(T_iA^*s)_n|^2(1-|\phi_{i,n}|^2)
\le T^2\|s\|^2\sum_iS_{ii}v_i.
\]

不同 i 的中心化项因独立而消去，full gain covariance 未被擅自对角化。若 s 也按 q_d 随机、且与 channel 独立，可将 `||s||²` 换为其期望能量。此处是围绕 `bar H(h)` 的 ν 随机功率，不包含 mean-point bias、gain 本身的不确定性或模型错配。

定义每样本发送能量 `P_tx=E||s||²/N`，对比总噪声能量 Nσ²，得到全局条件界

\[
\frac{V_\nu}{N\sigma^2}
\le\frac{T^2P_{tx}}{\sigma^2}\sum_iS_{ii}v_i.
\]

右侧需要实际全局 v_i。这个量比“σν 看起来很小”更直接衡量响应功率，但仍不是判决增益或 BER 上界。

### 5. Fisher 信息与 Laplace 方差：只作有条件尺度

考虑**正确 delay、已知确定性 pilot 激励**的单路径参考模型

\[
y_t=hD(\nu)s_p+w,\quad w\sim\mathcal{CN}(0,\sigma^2I),\quad
\|s_p\|^2=NP_{pilot}.
\]

这是 pilot-only/正确条件化的局部信息模型。实际 SP 中“pilot 已知”不代表未知数据已消失；不能直接把实际观测当作这个模型。

若复 gain h 已知，由实参数 Gaussian score 得

\[
J_{\nu\nu}=\frac{2|h|^2}{\sigma^2}\sum_nt_n^2|s_{p,n}|^2.
\]

若复 gain 也未知，要投影掉其幅度与相位 nuisance 方向。令 `w_n=|s_p,n|²/||s_p||²`、`tbar=Σw_nt_n`，Schur complement 为

\[
J_{\nu|h}=\frac{2|h|^2}{\sigma^2}
\left[\sum_nt_n^2|s_{p,n}|^2-
\frac{(\sum_nt_n|s_{p,n}|^2)^2}{\sum_n|s_{p,n}|^2}\right]
=\frac{2N|h|^2P_{pilot}}{\sigma^2}\operatorname{Var}_w(t).
\]

只有 pilot 时域能量分布使 `Var_w(t)` 被远离零的常数控制时，才有 `J~N|h|²Ppilot/σ²`。例如能量集中于一个时刻时，该方差为零，ν 与未知 gain 相位不可辨识。AF 域 dense pilot 不自动保证这个投影后的时域信息条件。

这里 ν 是当前 `t_n=2πn/N` 所配的归一化 Doppler 参数；不能移用未归一化频率参数的 N³ 信息尺度。

**CRLB 是局部无偏估计方差的下界，不能用 `Var≤1/J`。** 若正确模型、正确 basin、内点真值、先验局部平滑正值、信息非退化、样本/有效 SNR 足够使单一主模态占优，且高阶余项和远处质量受控，Laplace/局部渐近近似才支持

\[
v_\nu\approx J_{\nu|h}^{-1}
=\frac{\sigma^2}{2NP_{pilot}|h|^2\operatorname{Var}_w(t)}.
\]

这不是有限输入的已证上界。多路径、未知 delay/数据或其他 nuisance 会进一步投影信息；接近共线、弱可辨识或错误 slots 时，上式常数可很差甚至不存在。

#### 何时产生 O(P/N) 的直觉

进一步假设每条路径都满足上述局部条件，gain posterior 足够集中使 `S_ii≈|h_i|²`，且有效 `Var_w,i(t)` 均为常数量级，则

\[
S_{ii}v_i\approx\frac{\sigma^2}{2NP_{pilot}\operatorname{Var}_{w,i}(t)},\qquad
\frac{V_\nu}{N\sigma^2}\ \text{的上界尺度}\ \sim
\frac{T^2P_{tx}}{2NP_{pilot}}\sum_i\frac1{\operatorname{Var}_{w,i}(t)}
=O\left(\frac{P_{tx}}{P_{pilot}}\frac PN\right).
\]

因此强、已正确定位且可辨识的路径可能只有很小的每样本 ν 不确定性功率。pilot/data `.5/.5` 固定功率比例不随 N 变化，但不能消除未知数据与 nuisance 条件。上述条件性尺度中，总 block 响应功率除以单样本噪声方差为 `V_ν/σ²=O(P)`；除以总噪声能量则为 `V_ν/(Nσ²)=O(P/N)`，两种归一化不可混写。固定状态 log-likelihood 差也不必随 N 消失；研究目标应区分每样本效应和整个 block 的效应。

这只能解释一个可检验假设，不能界定边际化的普遍价值上限。弱路径不满足高信息近似；S_ii 也未必接近 gain mean 的平方。低概率关键误差事件可能被平均功率掩盖，故即使该比例很小也没有 BER 结论。

### 6. 破坏“尖峰等于边际化无价值”的具体边界

- **多峰与错误 basin**：局部 κ 大可以与相隔很远的多峰共存。错误 F1 slot 的条件最优点也可极尖；给错误结构加一个小方差不会修复漏路径、错误 delay 或正确 basin 未被覆盖的问题。
- **gain–Doppler 相关**：若不假设独立，单路径还有
  `||E[hD(ν)]−E[h]D(Eν)||≤|E h|T²v/2+T sqrt(Var(h)·v)`。
  后一项由相关项的 Cauchy–Schwarz 界产生，可能是一阶标准差尺度。当前 mean-field 把它置零，不代表真实 posterior 没有它。
- **mean-field 方差偏小**：局部联合 Gaussian 的 precision 分块为 H 时，真实 ν 边缘方差为 `(Hνν−Hνh Hhh^(-1) Hhν)^(-1)`，mean-field ν 因子方差为 `Hνν^(-1)`。强相关时两者可相差任意大。首坐标 `E log likelihood` 的条件曲率不是实际边缘 posterior 信息的证书。
- **SP 未知数据与高维 q_d**：pilot-only Fisher 忽略未知 QPSK 的耦合、多解与错误决策反馈。条件化在错误或过于自信的 q_d 上可以产生尖而偏的 qν。N 行很小的局部误差也可累计成非小的 block 误差，或作用在很小的判决 margin 上。
- **迭代路径与 entropy**：固定状态的算子界不能控制后续 gain solve 的条件数、basin 切换、回溯接受层或最终 BER；也不能把连续因子和 Dirac 的熵直接相减，宣称完整 ELBO 差很小。

### 7. 一个现有证据检验：冻结状态的 mean-point 敏感度

**只检验“这 8 个已保存首坐标的 ν 方差在当时状态下影响小”，不检验全部 slots 或完整 receiver。** 未来若执行，只复用已保存势和同一更新状态，不生成观测、不重跑外层仿真；本轮仅提案。

1. 由已有全区间参考积分取得每个保存势的均值、全局方差及 φ 的数值估计；这些估计不称为真实值，代入严格算子上界时必须有可靠的积分与尾误差界。比较估计的全局方差与 `1/κ`，并估计 `max_n|φ_n−exp(it_n Eν)|`。若差异超出可靠误差范围、全局方差明显不由局部宽度描述，便反驳“尖峰已经足以证明小不确定性”的推理。
2. 在**同一连续更新的** μ、S、source、y 和其他 ν 因子上，仅将这一个 φ 换成 mean-point，计算 fixed-state Δz、逐行 target-logit 差、expected likelihood 差及每样本差，并报告该 slot 的 ν 中心化响应功率/噪声比例。不能跨 point/continuous 两条不同轨迹拼接状态。若相关状态未保存，明确缺项，不用另一条轨迹代填。
3. 用已有 target 的判决 margin 作无需 BER 假设的敏感度检查：若一行最大与次大 logit 的 gap 大于 `2λ_n`，则该 frozen target 的最大符号不变；bit LLR 绝对值大于 `2λ_n` 时符号也保持。实际发生 target 判决翻转或 likelihood/logit 改变不可忽略，就是“小方差在该状态下无实质影响”的反证。仅 margin 未覆盖表示证据不足，不代表错误率一定改变。

若 8 例都显示全局方差与局部宽度一致、mean-point 对 logits/likelihood 的实际改变小且 margin 稳健，则支持“这些首坐标的局部边际化收益可能有限”，从而有理由优先检查 slots/盆地；它**不证明 slots 已是主因**，更不能证明所有路径的不确定性都无价值。不要拿原 `1e-6` 求积数值阈值直接充当科学影响大小阈值；输出连续指标和 margin 覆盖证据即可，不另造未经约定的 BER 判断。

## External references

本轮未新增外部检索。实轴 Taylor 界、Gaussian score/Schur complement、全区间强凸方差界及功率界均在文中给出推导；Fisher、CRLB、Laplace 与 mean-field Gaussian 分块关系均作为经典方法使用，不提出新颖性主张。

## Caveats / Not Found

- 未读取或计算新的 raw，未新增实际数值；局部曲率/宽度、N 和 SP 功率背景来自主会话交接。
- 目前缺少这里提出的全局方差、冻结状态 logits/margin 与响应功率证据，不能直接确认“不确定性非主要瓶颈”。
- 全局算子界使用真实 v，当前工作模型的权重界使用固定 μ、S 和独立因子；CRLB/Laplace 只支持满足条件时的尺度，不能取代这些前提。
- 未修改 receiver、prior、q_d、slots、迭代/验收规则或任何他人文件。
