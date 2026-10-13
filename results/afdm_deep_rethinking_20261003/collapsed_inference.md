# 保留原双线性的直接数据推断：条件高斯消元之后，真正的新问题在哪里

2026-10-03；只读推导与定向文献核查。没有运行新实验、服务器任务或创建 CSV。使用 scientific-brainstorming / scientific-critical-thinking；本文件是候选方向研究，不是新算法性能结论。

**最值得推进的对象：把信道增益精确积分掉，直接近似数据侧的非线性似然因子。** 它保留原双线性，也不需要把整个联合后验压成一个全局仿射模型。真正尚未解决的创新点，不是“发现一个 logdet”，而是利用 AFDM 的路径算子，把这个因子转为低成本、合法且准确的数据软消息。

旧结果排除了某些解释：先验切换的扰动通常被原 joint 大幅消减；方向性缺口未被识别为实际 FER 根因；小模型原 joint 并非普遍过度自信；全局均值处的单个仿射近似留下明显双线性余项。这些结果支持更换近似对象，不支持宣称已找到唯一根因。

## 1. 从原问题出发，不再丢弃乘积

固定几何 θ，写 U_p=U_p(θ)，x=pilot+d，H(h)=Σ_p h_p U_p。假设真正入站模型为

h∼CN(m₀,C₀), w∼CN(0,σ²I), y=B_x h+w,
B_x=[U₁x,…,U_Px], C₀≻0。

m₀/C₀ 是外生先验或由明确独立因子产生的消息，不是把同一 y 的信道后验换名再用。以下 conditional h|x,y 是当前似然内部的解析消元，因而合法地依赖 y；没有作为第二次独立证据输入。

定义

G(x)=B_xᴴB_x，b(x)=B_xᴴy，K(x)=C₀⁻¹+G(x)/σ²，
C(x)=K(x)⁻¹，m(x)=C(x)[C₀⁻¹m₀+b(x)/σ²]。

则 h|x,y 精确为 CN(m(x),C(x))。即使完整 h,d 后验多模态或非 proper，这个固定 x 的条件后验仍然是 proper Gaussian。

零均值先验时，忽略与 x 无关的常数，精确对数似然是

ℓ(x)=−||y||²/σ² + b(x)ᴴK(x)⁻¹b(x)/σ⁴ − log det K(x)。

等价形式：

p(y|x)=CN(0,σ²I+B_xC₀B_xᴴ)。

一般 m₀ 下设 r=y−B_xm₀，用 r 替换上式 y/b 并保留相应 x 依赖项即可；严格表达为 −rᴴ(σ²I+B_xC₀B_xᴴ)⁻¹r−logdet(σ²I+B_xC₀B_xᴴ)。

**G、b 是给定 x 时计算该似然所需的低维统计量，不是一次压缩 y 后对所有未知 x 都通用的充分统计量。** 它们仍随 x 变化；全体数据的指数搜索尚未消失。

### 与 profile/variable projection 的准确区别

最小化 ||y−B_xh||²/σ²+(h−m₀)ᴴC₀⁻¹(h−m₀)，消去 h，得到 profiled MAP cost。精确积分再多出 logdet K(x)（以及常数）。前者只问“这个 x 下最佳 h 拟合得多好”，后者还计算“支持这种解释的增益体积有多大”。这个区别由 Gaussian 积分决定，不是惩罚项调参。

但不能断言所有 x 的 logdet 都变：P=1、无叠加导频且恒模数据时，G=||x||²固定，logdet 确实是常数。多路径交叉项和叠加导频引入的能量/相关变化，才决定该体积项是否有辨识价值。最低成本的首个反证应覆盖这个常数退化例，而不是只选 logdet 有利的例子。

## 2. 最有用的闭式结果：精确数据 score

把 x 暂时延拓到 Cᴺ，采用 Wirtinger 导数 g=∂ℓ/∂x*。由 Fisher identity：

∂ℓ(x)/∂x*=E_{h|x,y}[∂ log p(y|x,h)/∂x*]
              =σ⁻² E[H(h)ᴴ(y−H(h)x)|x,y]。

代入条件一、二阶矩：

**g(x)=σ⁻²{H(m)ᴴ[y−H(m)x]−D_C x}，**

D_C=Σ_{p,q} C_{q,p} U_pᴴU_q，C_{q,p}=E[(h_q−m_q)(h_p−m_p)*|x,y]。

D_C 是 Hermitian PSD，因为 vᴴD_Cv=E||H(h−m)v||²≥0。这里的 C 下标次序不可颠倒。m,C 本来依赖 x；Fisher identity 已包含这些依赖的总效应，不需要再把 ∂m/∂x 加一遍。

这个结果比“信道估计后固定 H 检测”多出具有明确来源的 −D_Cx。它也不等于原 scalar AMP 恰好漏了这一项：原算法已有增益不确定性与 Onsager，本式的意义是提供一个**整个原似然的精确局部导数参照**，用于判断哪部分近似造成实际数据消息误差。

完整 bilinear likelihood 先积分、再求导，没有做 y≈Bδh+Hδd 的仿射替代，因此不存在那一轮中待忽略的 δhδd 余项。然而得到精确 score 并不等于得到精确符号后验或 LLR；“从 score 到离散软消息”才是下一步。

### 曲率为何不能偷换为一个恒正的 Hessian

对实数化参数，Louis identity 给

−∇²ℓ = E[−∇² log p(y,h|x)|x,y] − Cov(∇ log p(y,h|x)|x,y)。

第二项是减号。因此“条件平均 Hessian”可以当 PSD 预条件器，但不是精确边缘似然 Hessian。边缘问题可以非凸。把这一项丢掉再宣传凸化/必然收敛，会重演上一轮的问题。单个 score step 的稳定性、固定预算的逼近误差，需直接检验。

## 3. AFDM 真正可利用的结构与成本

在项目实际约定 U_p=A T_p Aᴴ 下，T_p 是带 CPP 和分数 Doppler 相位的循环单项矩阵：每行仅一个非零项。故 T_pᴴT_q 仍是带相位的单项矩阵；这一事实不需要把分数 Doppler截成整数，也不需要宣称所有参数下 CPP 都能无边界地套一个简单 Weyl 公式。

给定 x：

- 一次 IDAFT 得到 t=Aᴴx，P 个移位/相位乘法构造 B_time；G 和 b 在 time 域计算。
- G 构造 O(NP²)，条件 Cholesky O(P³)。y 的 IDAFT可在帧内缓存。
- D_Cx=A[Σ_pq C_qp T_pᴴT_q]t：O(NP²) 单项算子累计，再一次 DAFT，无需 N×N dense covariance。
- H(m)及其伴随同样可在 time 域 O(NP)累计；将两项合并后只需输出 score 的一次 DAFT。

因此一次精确 collapsed score 可达到 **O(N logN+NP²+P³)**，存储 O(NP+P²)（流式可再减少）。这不是 O(P³) 全算法；P² 个相位乘加和 Gram 都应计费。对 P=8，这条成本很可能值得报价，但本轮没有 benchmark。

潜在方法贡献位于：**原似然的解析导数 + CPP 精确二次路径收缩 + 数据因子消息化**的统一实现与误差控制。Woodbury、Fisher identity 和 P×P solve 本身均为经典工具。

### 精确单符号条件分数作为不用全码本的参照

改变一个符号 x'=x+δe_j，定义 V_j=[U₁e_j,…,U_Pe_j]。有

G'=G+δBᴴV_j+δ*V_jᴴB+|δ|²V_jᴴV_j，
b'=b+δ*V_jᴴy。

因此四个 QPSK 值可精确评估 p(d_j=a|d_{−j},y)；这是条件概率，不是把其他数据积分掉的 marginal。它无需候选 bank，但逐坐标扫描仍有成本。BᴴV_j 的全 j 缓存与 CPP 变换需额外计费；不能武断声称所有 N 个坐标只需一次 P×P 分解。

最稳妥用途是**便宜的误差定位工具**：比较原检测器输出与 exact single-coordinate collapsed ratios，区分点信道近似、周围符号冻结以及全局消息近似的各自误差。若成为算法，它必须替换既有一次主更新，而不能追加扫描后再称天然高效。

## 4. 为什么它和旧 CAVI 有实质差别，又为什么不能直接宣称创新

旧方法取 q(h)∏q_j(d_j)。现在可取

q(d,h)=q(d)p(h|d,y)。

其 KL 精确等于 KL(q(d)||p(d|y))。任意分离族 q(d)q(h) 则满足

KL(q(d)q(h)||p(d,h|y))
 = KL(q(d)||p(d|y)) + E_{q(d)} KL(q(h)||p(h|d,y))。

第二项是共享一个 q(h) 的额外代价；条件化消元直接去掉它，而不是给 q(h)补某几个交叉矩。它解释了 collapsed family 的自然性。

这也不证明当前 scalar AMP 正在最小化上式，或该项就是其 FER 误差。旧 `.mission/20261001_23-33-35-afdm-innovation-space/bilinear/DERIVATION.md` 已有精确积分、logdet、条件分支、全矩、CAVI与 bit/observation cavity；本项目也已有 exact oracle。因此本轮不能把这些恒等式再记成新发现。新增可研究部分是**不依赖指数/截断分支 bank 的可扩展 collapsed data factor**。

## 5. 四条候选路线，按当前可解释性与可实现性排序

### 路线 A，优先：解析 collapsed score 的固定预算数据更新

将当前一个数据更新替换为：当前 x→精确 m(x),C(x)→精确 g(x)→结构化预条件→星座近端/软投影。全程使用原非线性 likelihood，P 维信道仅内部消元；几何与现有轮数先保持。

优点：与过去 affine-Schur 失败对象明确不同，机制简单，易对实际原算法做 equal-budget 替换。难点：单点软投影不是合法 marginal，须从一个明确 relaxed objective 或 factor approximation 推出，而非把 g 任意变为 LLR。若只给 MAP 数据点，其论文主张也必须限于 MAP/优化，不能虚称软信息正确。

**最低成本验证**：先对现成 N=2/3 oracle 的每个固定 x 做有限差分 score核验；然后比较四类 single-symbol score：精确 collapsed、只profile、条件mean-H plug-in、原 scalar消息。检验 logdet/−D_Cx 改变的符号次序是否确实更接近 exact marginal，而不是只让自身目标下降。首轮不跑 FER，不增加轮数；若差距主要来自其他符号多模态，应转路线 B。

### 路线 B，最有潜力但更难：学习 Gaussian 平滑 collapsed 因子，而不是学习整个接收机

设接收因子的合法入站 Gaussian cavity 为 CN(x;r,V)，定义

Z_y(r,V)=∫p(y|x)CN(x;r,V)dx。

它保留原 nonlinear likelihood；以下（proper Gaussian cavity、实数化可统一处理 improper输出）是精确恒等式：

m_tilt=r+V ∂log Z_y/∂r*。

接收因子需要的 soft response 是**平滑后的 score**，不是路线 A 的 point score。若训练一个小模型仅近似 log Z 的修正或其 score，再由同一 scalar potential 导出均值/响应，可把数学任务限定为“一个可检验的近似积分”。协方差/伪协方差用相应一、二阶响应计算，code factor仍独立。

可输入解析特征：K、条件m/C、Gram谱、当前 data状态的局部解析score/能量、入站V，以及 CPP 路径参数的置换等变表示。只输入 P×P G与P维b不够：不同 N 维 x/算子导数可共享G,b，却有不同逐符号score。必须保留逐符号局部特征；不能宣传全状态被压成P维。

“低维学习”应指仅预测谱系数、正定预条件器、积分残差或少数控制参数，并用共享局部算子生成 N 维输出。只学习 preconditioner 可以改善优化轨迹，但不自动修复平滑积分/LLR。若目标是严格 posterior消息，训练对象应是 tilted moment/score，区别不能混写。

消息闭合条件：接收因子不包含 LDPC indicator；code只通过入站消息出现。对Gaussian site，用 tilted输出与 cavity做规范参数相减；对bit site验证自身入边不变性。正定性、Jacobian对称/积分一致性、尺度/路径置换等变性可成为 architecture约束。它仍是近似EC/EP，没有全局收敛保证。

**最低成本验证**：利用已有tiny exact oracle生成独立 cavity分布的 exact tilted moments，训练极小谱/积分修正器，比较解析point、解析smooth参照、学习smooth三者的留出误差；保持同样1次替换/固定depth，不加候选bank。若只能拟合训练N/几何、或学习后不满足合法site，则不进入主线。当前仅提出目标，没有训练。

### 路线 C，第二缺陷源：先支持/几何选点，再软推断的不可逆压缩

固定θ后的精确collapse只解决增益，真实目标还含

p(y|d)=∫p(y|d,θ)p(θ)dθ。

当前接收器先把 θ压成某个选中的 support/Doppler点；后续 gain/data再准确也只能解该条件模型。另一模式的 likelihood质量已经被删除。这个压缩比“增益协方差少了一个方向”更可能对应难帧，但尚未有因果证据。

可选低成本自然近似是对一个已获得局部几何盆地做 **marginal evidence curvature修正**，把同一盆地的连续Doppler积分体积带入数据因子；不能对多盆地使用一个 Hessian 就声称恢复遗漏模式，path permutation对称也须商掉。混合相邻delay hypotheses若显式扩张候选数量，已越过本轮不靠bank堆算力的原则，暂不作为主方案。

**最低成本验证**：复用已保存 score landscape先检查是否多盆地，不能把旧最小二乘分数直接softmax冒充posterior。仅在tiny真实物理模型上先对连续几何积分和固定几何准确marginal作比较：若固定几何的oracle已保留大部分错误，则增益/data改造不是主要着力点；若几何积分改善且单盆地曲率占主导，才推一个不扩bank的Laplace/response机制。

### 路线 D，结构性但受pilot限制：先识别可辨识商空间，再处理离散规范自由度

pilot=0且h先验圆对称时，(h,d)→(g⁻¹h,gd)，g∈{1,i,−1,−i}保留 likelihood；数据绝对相位可能不可辨识，关系/乘积可辨识。无pilot exact bit marginal=0是正确后验，不能拿强制选一个相位模式的尖锐LLR当性能。

有pilot时要检查 d'=g(pilot+d)−pilot 是否仍在星座/码本；通常不成立，不能把blind旋转对称硬搬到当前superimposed pilot。LDPC是否保留旋转也须检查Gray bit映射诱导的置换与补码是否保持 H_code b=0；通常不能无条件假定。

若确有近对称，仅4个群轨道的解析处理可能比一般大bank自然；但四次似然仍是四倍工作，不能借“群”字免账。优先作为**不变性诊断/网络约束**：对真正对称的no-pilot极限，要求输出/score等变；pilot存在则要求按已知pilot破缺。最便宜检查是对既有oracle确认具体码和pilot的合法群，而非直接加四分支检测。

## 6. 最近邻核查与新颖性边界

定向访问日期：2026-10-03。本轮没有付费库全文访问或系统性全领域排重；以下区分原文阅读与元数据确认。

| 文献/原始链接 | 本轮核验层级 | 对本提案的约束 |
|---|---|---|
| Parker & Schniter, [Parametric Bilinear Generalized Approximate Message Passing](https://arxiv.org/html/1508.07575v2), IEEE JSTSP 2016, [DOI](https://doi.org/10.1109/JSTSP.2016.2539123) | 原文HTML摘要、章节结构与iid大系统假设；标量方程差异复用既有项目阅读记录 | 原算法本来就处理bilinear与gain uncertainty；其iid随机三阶tensor近似并非确定CPP算子的自动定理。直接collapse因子的区别在积分顺序和消息近似，不在首次联合估计。 |
| Golub & Pereyra, [Separable nonlinear least squares: the variable projection method and its applications](https://doi.org/10.1088/0266-5611/19/2/201), Inverse Problems 2003 | Crossref题名、作者、DOI元数据；未下载全文 | 线性参数消元是经典。profile与marginal的区别由本文件Gaussian积分直接推导；不冒称本文已逐式讨论当前AFDM式。 |
| Hensman, Rattray & Lawrence, [Fast Variational Inference in the Conjugate Exponential Family](https://arxiv.org/html/1206.5162v2), NeurIPS 2012 | 原文HTML摘要、§2/§3及collapsed/KL-corrected讨论 | 先消元/收紧变分bound与信息几何加速已有通用理论；不能把去掉一个variational block命名为新推断原理。其特定CEG边缘化次序等价不能不加条件套到带离散码和连续几何的全部模型。 |
| Opper & Winther, [Expectation Consistent Approximate Inference](https://www.jmlr.org/papers/v6/opper05a.html), JMLR 2005 | 原始记录摘要，本项目已有原文阅读 | 两个可处理子结构间moment matching是旧原理；路线B的潜在贡献需是AFDM因子的特殊可计算近似与可验证误差。 |
| Ghavami & Naraghi-Pour, [MIMO Detection With Imperfect Channel State Information Using Expectation Propagation](https://doi.org/10.1109/TVT.2017.2683527), IEEE TVT 66(9):8129–8138, 2017 | Crossref题名、作者、卷页/DOI确认；全文公式本轮未核实 | “不完美CSI+EP soft detection”不是空白。必须后续对其channel-error模型、候选依赖covariance和moment更新逐式比较；目前不能宣布该文已有/未有本collapsed CPP score。 |
| Ranasinghe et al., [Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels](https://arxiv.org/html/2405.16945v4), TWC 2025 | 本项目上一轮原文核查记录，本轮未重复全文 | AFDM bilinear软消除、Gaussian消息、联合channel/data已是直接近邻。不能只因使用DAFT与Bayes就声称创新。 |

检索过程曾误试arXiv 1508.07579（实际为粒子物理论文），已剔除；API按题名核实正确号1508.07575。若干旧URL 404、Crossref并发检索429后改用确切DOI/API记录；未把失败请求当证据。

## 7. 对主线的建议

**先用路线A的精确collapsed score作为最小数学参照，判断当前data消息究竟在哪个近似环节失真；若单点条件化不足，再推进路线B的平滑因子/学习积分。** 这比继续给全局线性化补矩阵更直接：原bilinear积分正确，只近似真正困难的数据边缘化，并把近似误差定位到一个明确对象。

本轮可以诚实提出的论文潜力是：CPP-aware exact marginal-score contractions、无需候选bank的近似tilted-message实现、以及其相对现有P-BiG-AMP的同预算误差/性能证据。三者目前只有第一项的推导在此给出，后两项尚待构造与验证。不要将有限差分通过、logdet存在、学到一个步长、或更低自身objective单独包装为新主方法。
