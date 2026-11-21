# 独立评审：full soft-Gram 增益块的五个争议问题

先说明：Codex 的原文没有单独提供，我把五个问题的提法当作它的立场来审计。我没有使用工具，以下判断只依据所附代码、推导和观测事实。

## 总体判断

**Gemini 说对的三点：**
- diag 对照太弱；
- "VEM/CAVI"一类标签需要加限定；
- 耗时差里含有诊断开销。

**Gemini 越界或出错的地方：**
- Q1 断言"上游在物理子空间意义上根本没有缺陷"，证据不足。
- Q2 把"非均匀复制"定为代数漏洞，实际是先验错配，不是算法不变性的问题。
- Q3 断言多出的开销主要是诊断、真实增幅"远低于 29%"，没有 profiling 依据，且漏算了 Gram 矩阵 $B^HB$ 的构造成本。
- Q5 的"等价性定理""oracle-consistent benchmark""15%/500 簇标准"均没有依据。

**Gemini 的事实误读：**
- 它说 full-Γ 上游上的 diag 臂"第一步就产生 0.99 相对物理信道偏差"。所附材料中 .976126/.990782 是 duplicate-invariance qualification 的数字，即复制表示与原表示之间的首步物理差异，与上游无关。
- 它引用的 NMSE（.024835/.026482/.028158）和 symbol MSE 不在所给事实中，我无法核实。即使属实，也没有给出 CI。

**Codex 式的反对意见基本成立。** 下文在若干处补充它没有覆盖的数学点。

---

## Q1：修好下游能否锁定"近重复原子 + 标量 Onsager"为原故障？0/200 能否证明上游无缺陷？

**有界表述**

在这 200 个 informed 旧 key 上，可以说"排序翻转依赖于 native 增益更新族与上游输出的交互"，而且证据较强：
- native fixed 是 4/15，标量上游反而更好。也就是说，把标量上游的 $(\hat S, h_0)$ 当作固定信道时并不差。
- 打开 native 增益更新后变为 40/11，恶化发生在增益更新环节。
- 整体换成局部 full 求解后两者都是 0/200，上游间 logloss 只差约 $10^{-4}$。

但证据**不能**把原因定位到近重复原子、off-diagonal 或 Onsager。

**关键理由 1：new full 与 native point 不是单变量差异。** 两者至少在五处不同：

1. 预条件方式：native 用标量 $v_q=1/(s_v\|\bar x_b\|^2)$，new full 用矩阵 $Q^{-1}$。
2. 驱动量：native 是由阻尼残差 $s$ 驱动的增量步（$s$ 内含 Onsager 项 $\bar{\tau}$ 和输出阻尼）。new full 直接用 $Y$ 一步求解，并丢弃 $h_{t-1}$。
3. 阻尼：native 用阻尼后的 $B_b, h_b$；new full 用无阻尼的当前 $B$。
4. 不确定性修正：native 只有标量修正 $-h_b s_v n v_x$；new full 用 $\Gamma(v_{\rm pre})$。
5. 唯一对齐的只是先验 $1/P$。

任何一项都可能是原因。

**关键理由 2：上游缺陷有直接反例。** 设真支撑包含 $p^\ast$ 但 $p^\ast\notin\hat S$。任何在 $\hat S$ 上的增益拟合都满足

$$\|Y-B_{\hat S}h\|\ \ge\ \|(I-\Pi_{B_{\hat S}})\,g^\ast U_{p^\ast}\bar x\| .$$

这部分残差是结构化干扰。在 7/8 dB 下它可能被噪声掩盖，在高 SNR 下会形成 error floor。所以单一 SNR 下的 0/200 不能排除漏径或错 Doppler。

**关键理由 3：近重复是否存在，尚未测量。** 平均 $P$ 为 23.91 和 23.345，多数恰好等于 24（疑似 cap）。基数信息无法说明共线结构。

**关键理由 4：0/200 的统计含义有限。** 样本来自 50 个共享帧簇，且是 informed 选择。0/200 不是 population FER，也不是 noninferiority（事实中已声明）。

**一个可检验的机制假设（置信度 M，未检验）。** 对角或标量预条件的梯度步，在复制簇的"和方向"上有效步长约放大 $k$ 倍。以同一二次目标的 Jacobi 步为例：

$$h'\leftarrow h'+\mathrm{diag}(Q')^{-1}(b'-Q'h')\ \Rightarrow\ Dh'_{\rm new}=g+\frac{k\,[(b-Mg)_p-\alpha g_p]}{m_p+k\alpha},$$

而原表示下的对应量是 $g+\frac{(b-Mg-\alpha g)_p}{m_p+\alpha}$。当 $m_p\gg k\alpha$ 时步长约放大 $k$ 倍，稳定性取决于阻尼 $\omega$ 与 $k$ 的乘积。native 并不是 Jacobi（还有 Onsager 和 $s$ 记忆），所以这只能作为生成假设的依据。

**未决经验假设**
- 标量上游的支撑里是否真的含有同 delay、高 $|R_{pq}|$ 的簇；
- 这些簇是否与 native point 的失败 key 对应；
- 更高 SNR 下 new full 是否出现 floor。

---

## Q2：$\alpha'=k\alpha$ 是人为漏洞，还是正确的匹配条件？

**有界表述**

这是正确的匹配条件。更一般地说，精确 Gaussian MAP（及其后验协方差）在任何保持诱导先验的线性重参数化下都是等变的。diag 臂和 native 标量步不具备这一性质。

**推导（对任意精确复制都成立，包括非均匀）**

设 $D\in\{0,1\}^{P\times P'}$，每列是某个 $e_{\pi(j)}$，并且 $U'_j=U_{\pi(j)}$。于是 $B'=BD$，$\Gamma'=D^H\Gamma D$。取先验 $h'\sim\mathcal{CN}(0,\Lambda')$，物理量 $g=Dh'$。在约束 $Dh'=g$ 下：

$$\min_{Dh'=g} h'^H\Lambda'^{-1}h' = g^H(D\Lambda'D^H)^{-1}g ,$$

最小点为 $h'=\Lambda'D^H(D\Lambda'D^H)^{-1}g$。均匀情形下，这个最小点正是等分，这也说明 $h_0$ 等分初始化是正确的。

因此，$h'$ 空间中的 MAP 等价于 $g$ 空间中先验为 $\mathcal{CN}(0,D\Lambda'D^H)$ 的 MAP。分两种情形：

- **均匀复制，$\Lambda'=I/(kP)$：** $D\Lambda'D^H=I/P$，即 $\alpha'=k\alpha$。不变性精确成立。
- **非均匀复制 $k_p$，标量 $\Lambda'=I/P'$：** 诱导先验为 $\mathrm{diag}(k_p)/P'\neq I/P$。物理估计会变，但变化来自**先验被重新加权**（复制越多的簇得到越大的先验方差），不是求解本身破坏了不变性。若改用 $\Lambda'=\mathrm{blkdiag}(I_{k_p}/(k_pP))$，不变性依然精确成立。

Gemini 说"$\alpha' I$ 无法同时提公因子"，是把先验错配误判成了算法缺陷。

**为什么整条迭代轨迹不变（point 模式）**

当 $v_h=0$ 时，符号步只通过物理量依赖 $h$：
- $Bh$，
- $h^HRh$（`TimePathOps.power` 用的是物理 $R$），
- 基于 $h_b$ 的 adjoint。

阻尼是线性的。所以只要每一步物理 $g$ 相同，归纳法成立。joint 模式下的 $P\,v_h$ 项不具备这一性质。

**不能推广的地方：近重复，$U_2=U_1+\varepsilon E$**

此时不存在 $D$，没有不变性可言，只有连续性：
- 由 $Q(\varepsilon)\succeq\alpha I$ 得 $\|Q^{-1}\|\le 1/\alpha$，所以 $h(\varepsilon)$ 和物理 $H(\varepsilon)$ 连续，$\varepsilon\to0$ 时趋于合并后的解。
- 连续性模量随 $1/\alpha$ 恶化。$\alpha=\sigma^2P$，所以高 SNR 下模量更差。
- 差分方向 $v_-=(e_1-e_2)/\sqrt2$ 上，$v_-^HMv_-=\tfrac12\|(U_1-U_2)\bar x\|^2+\tfrac12\mathrm{tr}((U_1-U_2)^H(U_1-U_2)\mathrm{diag}\,v)=O(\varepsilon^2)$。Gemini 写的 $O(\varepsilon\|M\|)$ 是松的上界。
- 当 $O(\varepsilon^2)\cdot$数据能量 $\gtrsim\alpha$ 时，数据会把两个原子分辨成两条物理路径。这时问题已经变成模型选择（是否真有两条路径），不再是表示问题。

**未决经验假设**
- 实际支撑中近重复对的 $\varepsilon$ 落在哪个区间；
- 上游 SBL 的功率分配与工作先验 $I/P$ 的错配有多大。工作先验根本不使用 SBL 的 $\gamma$，这本身就是两个上游之间一个未受控的差异。

---

## Q3：新增 FFT 能否复用？哪些开销可以剥离？

**额外 FFT 不能直接复用。**
- 新增的是 `np.fft.fft(v_pre)`：对实值方差向量做普通 DFT。
- native 的两次变换是 `daft(x,…,True)`（均值符号的 chirp-IDAFT）和 adjoint 的 DAFT。

输入不同（$v$ 对 $\bar x$），变换也不同（无 chirp 对有 chirp）。另外，native 只使用标量 $v_x=\bar v$，迭代中没有任何已算好的 $v$ 谱可以拿来用。

**合法的降本途径（各自都是需要单独验证的近似或实现变体）：**

1. **只算需要的 lag。** `fft(v)[δ mod n]` 只在支撑的 delay 差集合 $\mathcal D$ 上被取用。直接求和代价为 $O(N|\mathcal D|)$；也可以用 rfft。这一项是精确的。
2. **标量方差近似。** 若 $v\equiv\bar v$，则 $\mathrm{fft}(v)[\delta]=N\bar v\,\mathbb 1[\delta=0]$，从而

   $$\Gamma=(\textstyle\sum v)\,R,$$

   这里 $R$ 就是 `TimePathOps.R`，已经预计算好，因此**完全不需要 FFT**。这一形式与 native 的标量 $v_x$ 表示一致，但它是近似，结果是否不变需要测试。初始迭代中 $v$ 均匀，这个等式恰好成立。

**可以剥离的开销：**
- 协方差求解，即 `solve(Q,I)`；
- `eigvalsh(Gamma)`；
- 两个残差范数计算；
- `allclose` 断言；
- 计时和 dict 构造；
- 计算后未使用的 `rh`。

Cholesky 若改用 `cho_solve` 同时承担求解，就不是冗余。

**不可剥离的开销：**
- $\Gamma$（或其 lag 子集）；
- $B^HB$ 的构造，代价 $O(NP^2)$；
- $P\times P$ 求解，代价 $O(P^3)$。

**复杂度上目前能说的只有渐近式。** 每次迭代：
- native：$O(N\log N+NP)$；
- new：$O(N\log N+NP^2+P^3)$。

当 $P\approx24$ 时，$NP^2$ 项可能大于 FFT 项，而它不在"61 vs 41 FFT"的统计里。因此"增幅主要来自诊断""剥离后远低于 29%"都没有依据。

目前不能说：
- 剥离后的耗时；
- 端到端优劣（上游 SBL 耗时未计入）；
- 任何加速预测。

这些需要分项 profiling 才能回答。

---

## Q4："精确 VEM/CAVI 增益步""Hybrid AMP-VEM"这些称谓有多大依据？是否必须传播协方差？

**依据强（代数 + 代码均支持）的表述：**

"在给定的分解式符号工作分布（使用 pre-update 矩 $\bar x,v_{\rm pre}$）下，该步是声明的二次代理的精确最小化。"

需要注意，这一点**不依赖 Gaussian 假设**：
- $\mathbb E\|y-B(x)h\|^2$ 只依赖 $\mathbb E[xx^H]$；
- 对于分解式 $q$，有 $\mathbb E[xx^H]=\bar x\bar x^H+\mathrm{diag}(v)$；
- QPSK 有限字母表的 $v=p_d-|\mu|^2$ 是精确的二阶矩。

**"精确 VEM 增益步"只能有条件地使用。** 它与 VEM 有三处偏离：

- **(a) 更新顺序。** 符号步先执行并使用 $h_{t-1}$；增益步再使用 $q_{t-1}$。这是 Jacobi 式并行更新，不是 Gauss–Seidel 坐标上升，没有 ELBO 单调性。
- **(b) $q(x)$ 的来源。** $q(x)$ 来自 AMP marginal，而 AMP marginal 不是任何 ELBO 关于 $q(x)$ 的坐标最优更新。mean-field 下的 $q(x)$ 更新应当是干扰抵消形式，没有 Onsager 项。
- **(c) 观测重用。** 同一个观测被重复使用。

合适的称呼是"使用 AMP 提供的软矩的 EM 式 M-step"。这类似 EM-GAMP 的启发式用法，但那里 EM 更新的是超参数。

**"CAVI"不成立。** CAVI 要求维护 $q(h)=\mathcal{CN}(Q^{-1}b,\sigma^2Q^{-1})$，并在 $x$ 的更新中使用 $\mathbb E_q[hh^H]$。均值恰好与 VEM point 一致，但协方差从未进入符号步。

**"整套 Hybrid AMP-VEM"只能当描述性标签，不能隐含一致性或保证。** 原因：
- 符号步中的 $\bar\tau=v_x\|h\|_R^2$ 只校正了 $x$ 自身引起的相关。
- $h_{\rm full}$ 直接是 $Y$ 的函数，它对残差的依赖没有被任何 Onsager 项校正。
- 没有 state evolution、不动点刻画，也没有 ELBO。

准确的说法是"native P-BiG-AMP 符号步 + 局部 expected-Gram 增益拟合的启发式混合调度"。

**native joint 优于 point，不足以推出"new full 必须传播协方差"。** 理由：

1. native point 本身就是推导出的算法的不一致截断：增益仍从残差更新，却强制 $v_h=0$。joint > point 说明的是"在 native 族内恢复内部一致性有益"，不能平移到另一个更新族。
2. 在 new full 中传播 $\Sigma_h=\sigma^2Q^{-1}$ 需要新的推导。符号似然中会多出 $x^H\big(\sum_{pq}\Sigma_{h,pq}U_p^HU_q\big)x$ 这一项，它与现有 Onsager/$v_p$ 项之间可能重复计数。
3. FER 已经处于 0/200 的天花板。协方差传播的潜在价值在 LLR 校准上（目前可能偏于过度自信），应当用 reliability/logloss 来检验，而不是 FER。

结论：协方差传播是一个合理的候选轴，不是必需项。

---

## Q5：定理、benchmark、换主线标准，以及漏径反例与工程价值的区分

**"上下游二阶耦合可迁移 / 等价性定理"：不成立。**
- 唯一可以严格陈述的定理是 Q2 中的精确复制等变性。它是精确 Gaussian MAP 的一般性质，几乎肯定不是新结论。
- "上游净化 ⇔ 下游二阶求解"在数据上就不等价：full-Γ + native joint 的 logloss 为 .219107，new full 为 .1899，CI 排除 0。
- native point 在 full-Γ 上游下仍有 11 次失败，说明"净化后标量步就足够"也不成立。
- 漏径反例（Q1）表明，下游最多能吸收**冗余**（精确复制 + 连续性），吸收不了**遗漏**或错位。

**"oracle-consistent benchmark"：不成立。** new full 不使用任何真值，也不构成性能界，它只是另一个启发式接收机。真正的 genie 基准应当是 genie-symbol 增益拟合或 genie-channel 检测。

**15% / 500 簇 / 换主线标准：均无依据。**
- 阈值没有预注册，也没有 power 计算。
- "在低 SNR 临界工况采样"改变了 estimand。
- 上游 SBL 耗时未计入，"标量 SBL + new full 端到端更便宜"无法评估。
- 换主线属于方向决策，应由你决定。

如果要扩展样本，应先预注册：
- 主终点：簇级配对 logloss 差，以及在预期事件率足够的 SNR 下的 FER；
- 判定 margin；
- 基于现有 discordance 率的样本量。

具体数字我不替你编。

**两类问题应分开处理：**
- **漏径反例**：作为适用域边界写明（冗余可吸收，遗漏不可吸收），需要 SNR sweep 或 floor 检验来确认。
- **工程价值**：在这批 informed 筛选样本上，配对 logloss 降低约 .029，CI 排除 0；FER 差 −.010，区间 [−.025, 0]，未显著；instrumented 检测耗时约 +48%。
- **新颖性**：expected-Gram M-step 是软符号数据辅助估计里的常规构造。在做文献核查之前，应默认没有新颖性。

工程价值和新颖性互不支撑。

---

## Full-BHB + Diag-Γ 是否是最佳的下一个测试？

**不是。它的定义存在结构性歧义。**

由 `projected_variance` 得 $\mathrm{diag}\,\Gamma=(\sum v)I$（代码中有断言），所以

$$Q_{\rm diag\text-\Gamma}=B^HB+\big(\textstyle\sum v+\sigma^2P\big)I,$$

也就是用软符号均值做的 ridge 回归，再把 ridge 加大 $\sum v$。

它与 full 的差别在哪里：
- 当 $v$ 均匀时，差别恰好是 $(\sum v)(R-I)$，只出现在**同 delay 原子对**（fractional-Doppler 泄漏）上。
- 跨 delay 的项来自 $v$ 的非均匀性。我的推测（置信度 M）是：对一般的非均匀 $v$，这部分量级通常比 $\sum v$ 小 $O(1/\sqrt N)$。

它能说明什么：
- 只能回答"在局部代理族内，同 delay 簇的相关不确定性项是否影响 logloss"。

它不能说明什么，以及为什么：
- **它自身破坏复制等变性。** 对一个 $k$ 重复制簇：full 给出 $\Gamma$ 块 $=(\sum v)J_k$，diag-Γ 给出 $(\sum v)I_k$。在等分时，物理增益受到的不确定性惩罚从 $(\sum v)|g|^2$ 降到 $(\sum v)|g|^2/k$；差分方向则被额外加了 ridge。
  - 如果结果退化：这只说明 diag-Γ 不好，**不能**推出"Γ 非对角项是抑制 native 失稳所不可或缺的"。
  - 如果结果不变：仍然保留了对角的 $\sum v$，所以也不能推出"只有 $B^HB$ 起作用"。
- 它不能回答 Q1 的因果问题（native 为何失败）。
- 由于 0/200 天花板，FER 基本没有分辨力，主终点只能是配对 logloss。

**更有判别力的安排：**

1. **Q1 的机理问题（零新运行，优先做）。** 在已保存的两种上游支撑上，逐 key 计算同 delay 对的 $\max|R_{pq}|$ 和初始 $\lambda_{\min}$（归一化 $B^HB$），与 native point/joint 的失败做交叉。这一步决定"近重复"假设是否值得继续。
2. **若假设成立：精确复制注入。** 对 full-Γ 上游支撑做 prior-preserving 的均匀 2× 复制，native 部分保持不变。检查 native point/joint 的失败是否显著上升、new full 是否保持不变。这是精确干预，没有近似。它能确立"冗余足以触发 native 失稳"（在本样本上），但仍需配合第 1 步才能说明标量上游确实含有这类冗余。
3. **若关心 Γ 的作用：用梯度式消融代替 diag-Γ。** 设 $\{B^HB+\alpha I,\ B^HB+(\sum v)R+\alpha I,\ \text{full}\}$ 三臂：
   - 前两臂对比，隔离整个 $\Gamma$ 的作用；
   - 后两臂对比，隔离 $v$ 非均匀性的作用；
   - 第二臂恰好也是免 FFT 的候选（Q3）。
   
   另加一个从 $h_{t-1}$ 出发的 Jacobi 对照，以检验"矩阵求解 vs 对角预条件"。这正对应 Q1 中假设的步长放大机制，而且比现有的一次性 diag 臂公平。

**选择哪条线（机理解释，还是接收机工程）属于方向决策，由你定。** 不论选哪条，都应在运行前冻结主终点、判定阈值和"阴性结果不自动扩样本"这条规则。
