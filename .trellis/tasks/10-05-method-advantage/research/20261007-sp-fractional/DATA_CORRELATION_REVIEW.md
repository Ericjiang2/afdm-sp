# DATA-CORRELATION-THEORY-01 独立数学审查

结论：**PASS（现有恒等式、反例及候选坐标公式）**。未发现阻断数学错误。该结论不证明当前 AFDM 的误码由 mean-field 因子化引起，不证明候选的实际收益、低成本实现或科学门通过。

- 审查时间：2026-10-08T03:02:16.847465+00:00
- 主笔记：`DATA_CORRELATION_GAP.md`
- 主笔记 SHA-256：`8b8b1093c0e213e8693664b6d84dc0a29b4624f8e0339801afae16d32f93e168`
- 审查会话：`/root/trajectory_identity_review_live`；实际 model/reasoning metadata 不可核验，不声称指定模型或跨模型验证。
- 复用前次已读 receiver/data_step；本次补读 `moments.py` 的 SourceMoments、prepare_source、expected_quadratic、gain_statistics。仅写本报告，没有代码修改、生产 import、SSH 或新仿真。

## 数学核对

**1. shared gain 与 conditional gain 的 KL 差值正确。** 写 `Z_d=∫p_h exp(ℓ_d)dh`。对任意同一 q_h，逐 d 恒等式为 `log Z_d=E_qh ℓ_d−KL(q_h||p_h)+KL(q_h||p(h|y,d,ν))`。对 q_d 平均并减去 data KL，再取 shared 族的最优 q_h，即得到笔记的非负差。在线性复 Gaussian likelihood 和 proper Gaussian prior 下，`q_h*∝p_h exp(E_qd ℓ_d)` 仍是完整 proper Gaussian，故没有把无法实现的 unrestricted 优化冒充当前 Gaussian 最优解。q_d 退化为单点时差值为零；一般只有 q_d 支持上的 conditional posteriors 与同一 q_h* 几乎处处一致时才为零。Schur 消元优化 shared q_h，不等于保留 h–d 条件依赖；差值也不是 BER gap。

**2. 正确 BPSK 模型及风险反例成立。** 在 y=0，`−a²(s₁+s₂)²/(2 Var(w))=−J−J s₁s₂`，因此 `Var(w)=a²/J` 的常数正确。两个二元 entropy 的展开是 `2 log2−m²−m⁴/6+O(m⁶)`；沿 `(m,−m)` 加上 `Jm²`，得到文中增量。J>1 时存在足够小的非零 m 使目标严格提高，非零内部解满足 `artanh(m)=Jm`。J=1 时二次项消失、四次项为负，不在该不稳定结论范围内。精确 posterior 的两边缘均为 1/2，任一边缘的期望 log loss 比 uniform 多 `−(1/2)log(1−m²)>0`，但任何确定性硬判的条件平均 bit error 都仍为 1/2。该反例是固定 y=0 的条件风险不蕴含证明，不是正概率区域或整体平均 BER 恶化的证明；笔记现有边界正确。

**3. QPSK bit-product Hessian 的交叉项正确。** 将固定 q_h 的目标写为 `F=const+linear(s)+Σ_k H_b((1+s_k)/2)−(a²/σ²)sᵀKs`，其中 `K=G_R−diag(diag(G_R))`。去掉 G_R 对角来自 QPSK 的固定模长：对角均值平方被 variance 项抵消。由此 Hessian 恰为 `−diag(1/(1−s_k²))−2a²K/σ²`。Hermitian G 的实表示 G_R 是实对称的，但删对角的 K 不保证半正定。坐标严格凹不能推出联合凹；两 bit Hessian 的特征值为 `−1±J`，J>1 时出现正曲率。对 symbol probability 的零和切空间扰动，混合偏导确为 `−2 Re(δm_i*G_ijδm_j)/σ²`。这也避免了仅凭 bit-product 非线性参数化便断言全部概率域曲率的跳步。

**4. 16 态 pair block 的坐标公式正确。** 固定其余 block、q_h、ν，跨 block 二次项只依赖其他 block 均值，线性项合并为 `r_B^c=r_B−G_B,−B m_−B`。剩余 block 目标为能量期望减 `KL(q_B||p_B)`，其归一化 Gibbs 分布正是所给 16 态 softmax。更直接地，`F_B(q_B)=constant+log Z_B−KL(q_B||q_B*)`，所以该更新在固定其他状态时是唯一内部最优，旧独立分布包含在允许的 16 态族中。G_BB 对角时 block 分解回单符号更新；非对角时一般不能分解。并行更新所有 blocks 不受单块证明保证，笔记已明确限定。当前四元 QPSK target 的线性实部在 I/Q 上可分，从均匀初始化出发的几何 log 阻尼保持该分解，因此四元存储本身不产生跨符号相关。

**5. C_d 进入 R 的方向正确，当前 diagonal 接口确会丢项。** 对 `A=H_i*H_j`，`E[x*Ax]=m_x*Am_x+tr(A C_d)`，而 `tr(A C_d)=Σ_uv A_vu C_uv`。因此 pair 的附加量是 `c_uv A_vu+c_uv* A_uv`，没有共轭方向颠倒。固定 gain 的 residual 同理包含 `tr(G C_d)`。当前 `SourceMoments` 只保存逐符号 variance，`prepare_source` 仅计算 variance FFT，`_cross_source` 只按 delay 差读取这一对角统计；把 pair 的边缘 variance 送回该接口不会恢复上述非对角项。在线性、非 widely-linear 的当前 likelihood 下，这些二次统计使用 covariance 即可，未额外要求 pseudo-covariance。后续若改数据族，不能只改 softmax 而沿用旧目标检查器宣称完整 ELBO。

## 对 1911.12538v1 的比较范围

本次核验本地 PDF 和文本 SHA-256 均与 `.provenance.json` 相符：PDF 为 `821d82e0736dd727cd22aa0c68db391e6f737bfb99fb2e6379a8a40997569346`；文本为 `e66754bb34b9f6d6e70b77ea03a53c516e38970a8773c174900c37cb88bfc161`。另打开[固定 v1 原文](https://arxiv.org/pdf/1911.12538v1)，读取 §III 的上下文并请求第 3 页截图；页眉确认为 28 Nov 2019。式 (21) 后确实把混合导数记为零，再据 Hessian 对角推出全局凹及全局最优收敛。主笔记对该段实际文字的描述准确。

固定其他 factors 后得到负的单坐标二阶导数，不会消掉共同 ELBO 中的 bilinear mean coupling。仅凭“mean-field”或 G 为 PSD 不能支持混合导数为零。故主笔记的有限结论——**该段论证不能直接当作本项目的全局保证**——成立。

本次只证明一般耦合线性模型的反例和交叉项；**没有构造满足该文全部 OTFS 信道/参数约束的具体反例**，也没有验证其相应 G 的特殊结构是否在另行限制下消去耦合。因此不能将本报告改写为“已证伪该文所有 OTFS 条件下的定理”，更不能外推到未读的期刊终版、更正或实验结果。建议对外使用主笔记时把这句范围限制显式接在原文比较段后，并使用带 `v1` 的链接；这是表述强化，不是阻断数学问题。

本次也只读了 [Plummer、Pati、Bhattacharya 2007.06715](https://arxiv.org/abs/2007.06715) 的摘要：该摘要已明确双节点 Ising、非凸区间及 sequential/parallel 动力学的系统分析。因此本笔记不将 mean-field 非凸性或两节点分叉作为首次发现，边界恰当。未为此扩大到全文优先权或通信领域全面 novelty 审查。

## 有价值的下一步与验证范围

最有价值的下一步是把 pair covariance 的非对角 trace 项接回**实际 CPP/DAFT 坐标**，证明完整矩恢复与计算成本，再确定只依赖观测/模型的配对预算。配对得分或 softmax 很便宜，不意味着所有 gain/ν/residual 统计的更新也便宜。新的 FFT 成本推导若单列文件，应独立核对索引、共轭、FFT 归一化与 diagonal 退化；本报告不预先背书尚未审阅的式子，也不要求此时新增仿真。

本次结论来自逐式推导、边界/退化情况检查、指定源码和固定版本原文核查。没有重新计算已有轨迹，没有通过微型数值例子冒充 AFDM 实验，也没有修改原 scientific gate。


## PAIR_COVARIANCE_FFT.md 补充审查（2026-10-08T03:06:37.764885+00:00）

结论：**PASS（项目实际整数 delay、q_h 与 Doppler 因子独立的范围）**。FFT 恒等式、方向及操作量上界成立；以下两处假设/缓存依赖建议补清，没有新增实验门。没有运行数值程序，也未将代数复杂度当成完整接收机计时。

审查对象 SHA-256：`0ed702f16bc5c09bdcec87a133d6c358b6103788ddd6e2c02f58362df7666d5f`。本次补读 `physical.py` 的实际 daft 实现以及 `moments.py` 的 CPP、gain-column、gram_matvec/gram_diagonal；未重新审生命周期或运行生产函数。

1. **CPP wrap 和 basis 成立。** 令 x=t−l<0，则 inverse-DAFT chirp 在 x+N 的额外项是 `−2πic1(2Nx+N²)`，与 CPP 的正项精确相消；DFT 的额外项为 `exp(2πiu)=1`。因此延迟 basis 可统一写成原始整数 x 的式子，不需要 `2Nc1` 整数条件。单个 basis 的幅度为 `N^(−1/2)`，来自物理 daft 的 `sqrt(N)*ifft`，不能误用未单位化 IFFT basis。

2. **W 分组和 IFFT 归一化成立。** `v_li,u conj(v_lj,v)` 的 t 依赖分为 `α_ij(t)` 与 `exp(2πit(u−v)/N)`，常数相位恰为文中 W 指数；每个乘积自带 1/N，所以一次默认 IFFT 已包含全部归一化。仅 bin 的 `(u−v)` 可模 N；c2 的平方差保留原 u/v。一般 i≠j 的 K 是复数，正反 covariance entries 不能合并成未经证明的 `2Re`。C Hermitian 使 `K_ji=conj(K_ij)`，可只保留一个方向。

3. **diagonal 退化与同路径 trace 成立。** C 对角时 W 只有 k=0，值为未归一化 `FFT(variance)[(li−lj) mod N]`，因而 IFFT 得常数 1/N 后乘 α，精确回到当前 `_cross_source`。稀疏相关时，同一路径 K_ii(t) 是时变非负 variance，一般不常数；`T_li U` 是置换、单位模相位与 unitary DAFT 的乘积，所以总和为 `tr C`。同路径 gain Gram diagonal 与同路径 expected residual 可继续用 energy；把逐 t K_ii 换成常数则不成立。边界 li=lj 也只能保证 K_ij=K_ii，不保证时域常数。

4. **接回路径统计的共轭方向成立。** source cross kernel 使用 `E[response_i conj(response_j)]`；production gain Gram 的 `(i,j)` 使用相反方向 `_cross_source(j,i)`。新 K 保持这个约定，expected residual 中的 S_ij、Doppler 势以及 gain Gram 可以共享同一正确二阶矩。新增统计不直接改变固定 m_d 的 matched vector；若后续 pair update 改变了 m_d，当然仍须更新均值响应和 matched，不能把“不受 covariance 直接影响”误读为永不更新。

5. **G_uv 的独立 Z 公式成立。** 展开 `E[H_i*H_j]_uv=Σ_t conj(v_li,u(t)) ψ_ij(t) v_lj,v(t)`，得到 t 相位 `conj(α_ij) exp(−2πit(u−v)/N)`，外部常数相位与 W 相反，所以是 `FFT(ψ_ij conj(α_ij))/N`。gain 权重确为 `E[conj(h_i)h_j]=S_ji`，不是 S_ij。随机 Doppler 的同路径因子必须为 `ψ_ii=1`，不能使用 `|φ_i|²`；所以同一路径仍精确给出 δ_uv。该 Z 与 W 依赖不同，不能交换缓存。

6. **复杂度是合理上界，但不是已验证性能。** 每个 path pair 的稀疏分组 O(K)、清零及相位 O(N)、IFFT O(N log N)，再加一次 variance FFT，得到所述 `O(P²(K+N log N))` 上界。流式 scratch 的 O(N+K) 应按文中“额外”理解，原有均值/路径状态与保留输出另计；保存所有 kernels 的 O(P²N+K) 成立。Z 建造 `O(P²N log N)` 与 Q 次查询 `O(P²Q)` 是另一个独立成本。K 很小时还可能有更优实现，但本审查不要求展开。相比现有 diagonal kernel 的逐路径线性工作，新 FFT 常数和 log N 成本可能较大；避免 N² 对象不等于更快或通过成本门。N² 候选选择仍未解决的边界已正确保留。

### 两处需要在落地前明确的文字

- 将 delay 类型明确写为 `l_i∈{0,…,N−1}`。随机 ν 的 `G_uv=Σ S_ji E[H_i*H_j]_uv` 还沿用了 `q(h,ν)=q_h(h)∏_i q_i(ν_i)`；若 h 与 ν 相关，S_ji 不能移到 Doppler 期望外。point ν 时这个条件自动满足；目前生产工作分布亦满足。这是补写已用假设，不是要求新模型。
- 将“C_d 每次改变都需更新上述量”具体化为依赖关系：C_d 改变需更新 W/K 和相关 source statistics；Z 不依赖 C_d，ν 改变通过 ψ 影响 Z，gain 通过 S 影响 G 的加权；N/c1/c2/delay 变化会影响各变换。精确依赖可避免不必要重建，但不能以此绕过当前 SourceMoments owner 合同；正式实现仍需明确缓存所有权，并计入实际重建、拒绝 proposal 和保存成本。

前文建议的 CPP/DAFT 稀疏 covariance 代数缺口到这里已补上；尚未完成的是数值实现验证、有限候选/配对规则和完整成本评估。这些边界仍应与纯数学 PASS 分开记录。


## 最终文字修订核验（2026-10-08T03:13:08.610974+00:00）

**PASS，前述文字建议全部关闭。** 已读回两个主文件的修订段落：文献链接固定 v1，并明确一般反例未严格匹配原文 OTFS 特例；FFT 假设显式包含整数 delay、q_h 与 q_ν 独立及路径间 ν 独立；缓存说明正确区分 C_d→W/K、ν→Z、gain→S 加权，并保留 owner 合同。核心恒等式未改变，无新增数学问题。

本次最终审查绑定：

- `DATA_CORRELATION_GAP.md`：`9c2a7b92a140f045430129052ab19385d0dc84f1794bd00dff94be4f71f301b6`
- `PAIR_COVARIANCE_FFT.md`：`2216d68a7185b94936c57e52e1655286249e323c58a3fc4d66873e05f2ac0cd9`

主会话后续将接口限制到 disjoint pairs，是上述“稀疏 PSD C”范围的子集。非负 diagonal、唯一无重复端点、每个 2×2 Hermitian pair block 的 `|c_uv|²≤v_u v_v` 足以验证整体 PSD；这不扩张为任意 sparse graph 的 PSD 检验。此处仅确认代数边界，没有审阅尚未收到的实现或数值 protocol。

按主会话补充请求完成了只读源码定位并已回传：核心扩展点为 `moments.py:51,165,182`，共用统计消费者为 `189,202,214,226`；与数据 C 无关的原 data operators 为 `247,261,274`。参考 fixture 位于 `verify.py:44,89,257` 与本地封口 `evidence/artifact/execution/MATH-01/`，10 个旧输入/数组/报告文件已确认存在。工程 runner 的合同/计数机制见 receiver `protocol.py:93`、`runtime.py:42,236`、`collapsed_diagnostic.py:88,133,374,457`；旧 dispatch 仅作为结构参考，不能复用其旧 stage 名和额度。服务器明确规则位于项目 `CLAUDE.md:87,101,108,115,125`。该查找复用了当前代理；收到的模型 404 信息不被改写为指定 lookup 模型已成功运行。全过程没有 SSH 或科学模块 import。
