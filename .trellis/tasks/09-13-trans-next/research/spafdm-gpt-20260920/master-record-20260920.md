# SP-AFDM 项目研究总记录（2026-09-20）

> 目的：把本轮围绕 coded SP-AFDM、分数多普勒、I1、V1–V4 以及最新 architecture verdict 的研究过程，按“研究问题 → 理论澄清 → 方法尝试 → 判别实验 → 当前结论 → 下一步”串成一条线。它不是投稿稿件，而是项目 Master Research Record。

## 0. 项目真正的问题

基本模型：

\[
x=p+d,\qquad y=H(	heta)(p+d)+w.
\]

SP 让 channel estimation 与 data detection/decoding 天然耦合：估计 H 需要 d，检测 d 又需要 H。因此 iterative CE–Detection–Decoding / Turbo 结构是问题本身自然导出的，I1 也因此一直是强基线。

当前最准确的总目标不是“把 channel NMSE 做低”，而是：

\[
oxed{	ext{在完整计算预算下，怎样低成本获得、保留和利用对最终通信判决有价值的联合 code/channel 信息？}}
\]

整个 V1–V4 的演化，本质上是在不断把这个问题问得更准确。

---

## 1. 理论地基：fractional Doppler 到底意味着什么

对应文件：`theory_chapter(2).pdf`。

AFDM 单路径 operator：

\[
U(l,
u)=AC_l\Delta_
u\Pi_lA^H,
\]

多径信道：

\[
H=\sum_r h_rU(l_r,
u_r).
\]

后续正 chirp/正 Doppler 与早期理论稿负 chirp/负 Doppler 是符号约定差异，已经通过独立 dense construction 数值核对。

关键结论一：完整整数基展开是精确的：

\[
U(l,
u)=\sum_{q=0}^{N-1}c_q(
u)U(l,q),\qquad \sum_q|c_q(
u)|^2=1.
\]

所以 fractional Doppler 并不等于“必须连续估计”。真正的近似来自有限支撑截断，而不是 integer basis 本身。physical path 数、integer coefficient 数、effective shift、shift collision、operator orthogonality 必须严格区分。

关键结论二：SP data interference 不能简单理解成“fractional Doppler 导致 colored Gaussian noise”。对 realized multipath，它可以 colored；单个 unitary fractional path 在 isotropic data 下也可以 white。white 不等于 Gaussian，ensemble-white 也不等于每帧 realization white。

关键结论三：fractional tail 不能直接当独立白噪声。若 H=H_R+H_T，则 H_Tp 是 coherent pilot-model error，H_Rd 与 H_Td 一般相关；Frobenius orthogonality 不能推出接收端统计独立。

---

## 2. soft information 如何真正进入 CE：Gamma 的正确位置

对冻结 working distribution q(d)：

\[
\mu=E_q[d],\qquad V=\operatorname{Cov}_q(d),
\]

有精确 complete-data quadratic：

\[
E_q\|y-H(g)(p+d)\|^2
=\|y-\Phi_\mu g\|^2+g^H\Gamma g,
\]

\[
\Gamma_{ij}=\operatorname{tr}(U_i^HU_jV).
\]

在 integer monomial atoms、effective shifts 不碰撞、V 对角时：

\[
\Gamma=\operatorname{tr}(V)I.
\]

这说明一个重要研究原则：高维 soft statistic 是否值得获取，必须看它经过真实 receiver consumer 后还剩多少自由度。以后做 deep learning / learned covariance 时必须先过这一关。

---

## 3. 为什么“channel 更准”不是论文最终目标

理论稿定义了 SP-induced observation mismatch：

\[
\mathcal J_H(G)=E\|(H-G)(p+d)\|^2.
\]

它一般不同于 Frobenius error，且固定 pilot 带来方向敏感项。更重要的是，channel NMSE、residual、likelihood、FER 不是可互换指标；即使某个表示误差下降，也不意味着 finite-iteration BP/Turbo FER 单调下降。

这推动研究从“近似 H”转向“保护真正通信 inference object”。

---

## 4. V1：从 channel fidelity 转向 likelihood fidelity

对应文件：`research_report(2).pdf`，标题 *Likelihood-Preserving Compression for Coded SP-AFDM*。

对冻结 channel operator，codeword score 可写成：

\[
s(d)=rac{2\Re(d^Hz)-d^HRd}{\sigma^2}+\log\pi(d),
\]

其中 R=H^HH，z=H^H(y-Hp)。V1 的核心转折是：通信判决真正依赖 likelihood structure，而不是 H 的 Frobenius fidelity。

V1 得到 common fractional offset 的漂亮结构：H_delta^H H_delta 对共同 offset 不变，因此 dense fractional channel 可能对应 sparse likelihood interaction。

但 V1 没成为论文主线：好的 common-offset 情形可被经典 derotation 解释，matched-filter-domain sparsity 也已有 prior art；而 certificate 本身的计算成本没有证明优于 full computation。

V1 留下的真正资产是：

\[
oxed{	ext{应该保护 likelihood / task-relevant object，而不是盲目优化 channel matrix。}}
\]

---

## 5. V2：MAP preservation 不等于 soft/CE fidelity

对应文件：`research_report (1)(2).pdf`，标题 *From MAP Preservation to Posterior-Moment Fidelity in Coded SP-AFDM*。

V2 发现：一个 list 可以含正确 MAP，但仍丢掉大量 posterior mass。singleton list 会把 covariance 和 Gamma 压成 0，进而改变 CE refit。

因此：

\[
oxed{	ext{MAP 正确}
ot\Rightarrow	ext{posterior moments / CE update 正确。}}
\]

V2 建立了 list posterior 的 mass/TV/covariance 精确分解，也说明 projected moments 可以从 candidate responses 直接形成，不必存 N×N covariance。

但 V2 的关键未闭合点是：怎样廉价、可信地知道 list 外还有多少重要 posterior mass？proxy confidence 在 full coupled SP-AFDM likelihood 下可能严重失真，worst-case transfer bound 又太保守。

---

## 6. V3：完整 posterior fidelity 也不是 CE consumer 的必要条件

对应文件：`method_design_report(2).pdf`，标题 *Joint Code–Channel Ambiguity in SP-AFDM*。

V3 直接看 CE normal equation。对每个 codeword：

\[
K_d=\Phi_d^H\Phi_d,\qquad b_d=\Phi_d^Hy,
\]

对 q：

\[
A_q=E_q[K_d]+\lambda I,\qquad g_q=A_q^{-1}(E_q[b_d]+\lambda g_0).
\]

得到 consumer-specific identity：

\[
g_q-g_P=A_P^{-1}E_P[r_d(g_q)].
\]

这说明 global posterior fidelity 是充分条件，但不是某个 CE optimizer 的必要条件。甚至存在最多 2S+1 个 words 的 coreset，在固定 state 下精确保留同一个 CE optimizer。

V3 还测试了 sampled complement、channel marginalization/profile、two-hypothesis search、multistart EM、pilot design、coreset。没有哪个方法同时满足 novelty、complete cost 和稳定优势。

最重要实验转折：longer-code check 中，list-based failures 几乎全部来自 transmitted word 根本没进入 candidate set。因此：

\[
oxed{	ext{主要瓶颈开始从 in-list scoring 转向 hypothesis acquisition。}}
\]

---

## 7. V4：让大 list 的 soft scoring 变便宜

对应文件：`proposed_method(1).pdf`；投稿型压缩表达为 `manuscript(1).pdf` + `supplement(1).pdf`。

V4 当时的逻辑是：既然 small list 会漏真值，就扩大 list；但大 list 的 channel-marginalized evaluation 很贵，因此做 certified computation-adaptive evaluation。

对 candidate d，以完整 fractional path regressor Phi_d 和 gain prior g~CN(0,C_g) 做 marginalization。按 observation rows sequential conditioning：

\[
F_t=F_{t-1}+rac{|e_t|^2}{v_t}+\lograc{v_t}{\sigma^2}.
\]

增量非负，所以：

\[
0\le F_t\le F_{t+1}\le F_N.
\]

若 partial cost 已经超过 incumbent，则 candidate 不可能成为 finite-list MAP，可提前停止。

进一步维护：

\[
Z_K=\sum_{completed}e^{-F_N(d)},\qquad U_P=\sum_{stopped}e^{-F_t(d)},
\]

得到：

\[
\epsilon_B\le ar\epsilon_B=rac{U_P}{Z_K+U_P}.
\]

从而控制 finite-list MAP、discarded posterior mass、bit probability/LLR interval、posterior channel mean。

V4 的数学和 finite-list contract 本身是扎实的：held-out 实验中与 full 256-list MAP 完全一致，平均 row work 可明显下降；hard pruning 的反例也证明 MAP 一样时 soft posterior 仍可能被严重破坏。

但 V4 只控制 list 内 pruning error delta，不控制未生成 codeword 的 acquisition error eta。总遗漏是 eta+(1-eta)delta。

更现实的问题来自 full-size I1 attachment：front end 和 OSD proposal/transforms 的成本远大于 scorer 本身，因此 component speedup 几乎没有转成 complete-receiver speedup。

这引出了当前最重要的 reviewer 生死问题：

\[
oxed{	ext{为什么要显式大 codeword list，而不是把同样预算继续投入 BP/EP/MP？}}
\]

---

## 8. 最新 architecture verdict：大 list 不能再作为默认 premise

对应文件：`SP_AFDM_Research_Verdict(1).md`。这是当前最高优先级结论。

最新 paired reference experiment 从同一个 5-round LMMSE/BP/soft-CE checkpoint 出发，比较 MP continuation、EP、restart、two-word-conditioned branches、OSD-64/256、full/certified list evaluation、refresh 后再 OSD。

在 common 20 ms time-to-result budget 下，小系统 reference 中 MP/EP/branch 均优于 stale OSD-256 endpoint。它不能证明 population dominance，但已经足以否定“expanded stale list 应该是默认 receiver architecture”。

更关键的是：OSD-64 的失败全部来自 candidate omission；OSD-256 绝大多数失败也一样。把 stale bank 从 64 扩到 256 只救很少 frame，而 refresh iterative receiver 后再做小 list 更有作用。

因此：

\[
oxed{	ext{acquisition 比 fixed-bank evaluation accuracy 更重要。}}
\]

此外，新 vectorized batch full evaluator 在新的 B=1024 timing fixture 上常比 sequential certificate 更快。说明：

\[
oxed{	ext{row saving}
eq	ext{wall-clock saving}.}
\]

V4 的 theorem 保留，但“默认使用 certified sequential evaluator”的工程结论已经降级。

---

## 9. 更深的 consumer 修正：marginal gain mean 也未必够

最新 verdict 进一步指出，对 bilinear joint receiver：

\[
s_B=\sum_d w_d\Phi_dm_d
\]

一般不等于把 data mean 和 gain mean 分别取平均后再代入模型。差别来自 code/channel cross-moment。

已经构造 exact witness：两个 codeword 权重各 1/2、conditional gains 相反，因此 marginal gain mean 为 0，但真实 joint predicted signal 仍很大；简单 collapse 到均值会把 joint information 全部消掉。

因此真正值得保护的 consumer 可能是：

\[
oxed{	ext{joint modes / joint prediction / cross-moments}}
\]

而不是单独一个 channel mean。

V4 的 discarded-mass budget仍可扩展去约束 joint prediction 和 residual-energy expectation，这些数学资产应继续保留。

---

## 10. 当前最合理的新架构

当前 lead 不是“large-list V4 receiver”，而是：

\[
oxed{	ext{computation-adaptive, mode-preserving iterative receiver}}
\]

正常帧继续 I1/BP/MP/EP；只有出现可观测 stagnation 时，才低成本产生极少量 complete codeword hypotheses（例如 1–2 个，开发上限很小），分别 refit channel 并建立独立 branch。

complete word 的真正潜在价值不是“组成大 list”，而是提供一个 code-consistent nonlocal joint move：一次同时改变一组 correlated bits 和对应 channel state，帮助跳出单一 iterative basin。

branch 应保持自己的 channel / detector / decoder messages，不应过早平均成单一状态。

V4 此时只是可选 evaluator：仅当 bank 已经便宜地产生、scoring 真的是 complete cost 中的重要部分、且 downstream consumer 真的需要 soft certificate 时才启用。对于很小 bank，当前证据甚至更支持 vectorized full evaluation。

---

## 11. 当前 claim 状态

| 命题 | 状态 |
|---|---|
| 完整 fractional Doppler 可由 integer AFDM operator basis 精确表示 | 已证明 |
| fractional Doppler 必然产生 colored noise | 否定 |
| 大 N 自动 Gaussianize 未知 QPSK interference | 否定 |
| fractional tail 可当独立白噪声 | 否定 |
| ordinary OMP correlation = exact refitted evidence | 一般否定 |
| diagonal variance 必然产生高维 CE correction | 否定；特定条件下退化 scalar ridge |
| 更低 channel NMSE 必然更低 FER | 否定 |
| likelihood fidelity 比 channel fidelity 更接近最终通信任务 | 已确认 |
| MAP preservation 足以保证 CE soft information | 否定 |
| global posterior fidelity 是单个 CE optimizer 的必要条件 | 否定 |
| longer-code list failure 主要来自 in-list misranking | 当前证据否定，acquisition 更主导 |
| V4 finite-list MAP/mass certificate | 已证明并验证 |
| large-list + V4 是默认最合理 SP-AFDM 架构 | 当前否定 |
| V4 row saving 等于 whole-receiver speedup | 否定 |
| marginal gain mean 足以代表 joint code/channel information | 否定 |
| small mode-preserving branch 已经是 Trans-ready 方法 | 未闭合 |
| matched complete-cost 下 small branch 是否优于 strongest MP/EP | 未解决 |

---

## 12. 下一阶段真正要闭合的三个生死问题

第一，同一个 frozen I1 warm checkpoint 下，必须按 identical additional wall-clock / complete cost 比较：original continuation、stronger MP/BP、structured EP、restart、decoder postprocessing、small word-conditioned branches、full OSD rescue、V4 rescue。不能用不公平的“相同 decoder calls”替代 complete-cost frontier。

第二，需要一个 receiver 可观察、廉价、可冻结的 stagnation trigger。候选包括 syndrome/hard-decision repetition、channel-update norm plateau、observed objective stagnation、decoder entropy plateau 等。不能使用 true error 作为 oracle trigger。

第三，要明确 actual consumer：最终 small-mode output 是用于 branch-conditioned feedback、joint prediction、CE optimizer，还是 soft bits。不同 consumer 需要不同 guarantee。当前最值得继续的是 mode-preserving joint feedback，而不是简单压成一个 marginal gain mean。

---

## 13. 后续可能方向

最优先是 small-mode acquisition + scheduling；其次是 proposal–evaluation co-design，让 physical marginal score 在 candidate generation 过程中直接参与扩展/淘汰，而不是先生成 256/1024 words 再评分；再往后可以考虑 mixture EP / branch-conditioned BP 等 multi-modal message passing。

如果 production test 显示 model mismatch、wrong support、off-grid geometry 才是主要失败原因，则应回到 structured SBL / parametric path acquisition / integer-continuous hybrid representation，而不是继续优化 list。

深度学习只有在解决明确瓶颈时才值得引入，例如学习 stagnation trigger、action policy、cheap mode proposal、consumer-specific sufficient statistics 或 model-based deep unfolding。不能为了“AI”而加网络。

---

## 14. 文件角色与优先级

`theory_chapter(2).pdf`：理论地基。  
`research_report(2).pdf`：V1，likelihood compression。  
`research_report (1)(2).pdf`：V2，posterior/moment fidelity。  
`method_design_report(2).pdf`：V3，consumer-specific inference 与 acquisition barrier。  
`proposed_method(1).pdf`：V4，certified finite-list evaluator。  
`manuscript(1).pdf` + `supplement(1).pdf`：V4 投稿型阶段稿。  
`SP_AFDM_Research_Verdict(1).md`：当前 architecture-level 最高优先级结论。

判断优先级：最新 verdict > V4 架构判断 > V3 > V2 > V1；但旧文件里的 theorem、counterexample、negative evidence 仍全部保留。

推荐阅读顺序不是按历史时间，而是：Verdict → manuscript → V4 proposed_method → V3 → V2 → V1 → theory chapter → supplement。

脑中应形成这一条演化线：

\[
oxed{H	ext{-fidelity}ightarrow likelihood	ext{-fidelity}ightarrow posterior	ext{-fidelity}ightarrow consumer	ext{-fidelity}ightarrow hypothesis\ acquisitionightarrow mode	ext{-preserving adaptive inference}.}
\]

---

## 15. 当前一句话研究目标

\[
oxed{	extbf{Affordable acquisition and preservation of useful joint code/channel states under a complete computational budget.}}
\]

V4 不再是整篇论文的必然终点，但它的 exact fractional-path scoring、monotone partial likelihood、finite-bank probability bounds，以及可扩展到 joint prediction/residual 的 certificate，仍然是后续 receiver 可以复用的重要数学资产。
