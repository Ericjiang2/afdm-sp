# TASK L：Delta_e 区别，原文跟查

2026-10-13。Caveman。**Verdict＝narrowed。** [I] “预测多算能否挽救”已有直接先例；“receiver按预测成功概率分配迭代”也已有。尚存候选区别：**共同SP联合循环前缀上，比较两条完整continuation的净FER改善，再分配CE-detection inner预算**。不是Δ减法新，不是online新。TCOM成立还需机制＋强benefit-aware参照下的实用增量；目前未获结果。

**口径：**[F] 原文事实；[D] 自推；[I] 判断；[S] 投稿/证据建议。`blocked`＝本工具未取得可读正文，**不等于确认paywall、无open copy、无该机制**。`section`＝已读指定相关章节；不冒称全文审计。仅本笔记写入；无SSH、仿真/分析运行、git。

本轮依据 [collaboration plan](collab-plan-b-20261013.md) 的L职责。分工文件途中更新了后续IMPL职责；本轮仍按用户显式TASK L只读边界。沿用comm-lit-review：本地paper库未找到对应PDF；external优先publisher/author institution，secondary仅作检索lead。两web入口核查；IEEE/若干repository反复fetch受阻。

## 1. Coverage，先分清已知与未解

| Item | Paper coverage | 本轮真正核到 | 尚未核到 |
|---|---|---|---|
| Liu / Guan / González，TCOM72(1)，2024，601–617，DOI10.1109/TCOMM.2023.3323710 | **blocked**；相关NTU原始技术说明＝**section** | SP＋BEM／pilot-power优化＋CE/detection/decoding soft loop | 论文algorithm、iteration/stopping细则；不能断言fixed或无adaptive |
| Huang / Ritcey，TWC4(5)，2005，2549–2558，DOI10.1109/TWC.2005.853977 | **blocked**；secondary abstract已读，未当primary正文 | 作者自己的2007book chapter参考表确认2005论文；secondary称SDM online convergence后CE | SDM式、阈值、block/iteration实现；primary per-frame结论仍open |
| Alves / Guimarães / Pinto，IET Commun.9，2015，1730–1737，DOI10.1049/iet-com.2015.0151 | **section**：§§3–4.3、Table2；HTML可读、图片公式部分blocked | η的正文定义、LLR来源、threshold/false-alarm模型、降档与CE位置 | Eq26/27图片未逐symbol核；不杜撰求和索引/H0原始写法 |
| Akyildiz / Mahdavifar，arXiv2603.20385v1，2026-03-20 | **section**：III-A–D、Eq9–16、Alg1、IV | 直接rescue label、cost-risk停止、训练loss、作用对象 | 无已核peer-reviewed venue；不叫TCOM既刊论文 |
| Lee / Yang，TCOM58(10)，2010，2759–2764，DOI10.1109/TCOMM.2010.082710.090533 | **blocked**；author metadata＋secondary abstract | author网页PDF入口实际跳IEEE5567014；未找到可读open全文 | 决定再equalize的exact metric；不能叫syndrome stall复现 |
| 新近邻：Niemi，Iterative deep learning receiver，Helsinki MSc，2022 | **section / indexed excerpts**：author-repository abstract、Ch4/4.1、Ch6；live PDF blocked | SCNN预测所需receiver iterations，可提前放弃不可解输入 | 全文未连续读；thesis，非peer-reviewed journal |
| 新近邻：EP4364367A1，A radio receiver with an iterative neural network…，2024 | **section**：Description Fig3–4、stopping/training procedures | 剩余iterations预测＋required LDPC success probability | 专利disclosure非实证论文；无已核finite-sample FER guarantee |

## 2. Liu：same-class，但control未解

**[F] Primary related technology。** [NTU原始技术说明，Technology段](https://www.ntu.edu.sg/innovates/tech-portal/tech-offers/detail/system-and-method-for-orthogonal-time-frequency-space-communication)：优化SP power ratio与BEM order以改善SINR；粗CE后detection/demapping/decoding；a-posteriori/extrinsic LLR反馈迭代CE与detection。作者publication由 [NTU lab目录，item103](https://www.ntu.edu.sg/ancl/achievements) 确认。此是机构技术说明，**不是所问论文全文的替代品**。

**Control回答：**

- CE re-estimation in loop：**related technology确认有**；不能把DD/code-aided CE当新机制。
- BEM order/pilot power adaptation：**优化存在**；与每frame按decoder-state升inner iteration预算不同。未知具体online粒度。
- per-frame iteration control / stopping / CE activation schedule：**论文unknown**。DOI、NTU-Pure mirror、题名/DOI/PDF检索未取到正文；不能从官方简述未提便认定没有。

**[I] Shares：**SP＋BEM＋coded软反馈联合链；initial粗估计→refinement并非ours。**Exact remaining difference，暂定：**使用同一receiver在相同prefix上两个inner-budget continuations的terminal FER差来触发升档，并验证可靠性约束。是否与Liu具体algorithm冲突仍需正文；目前只可称候选区别。

**[S] 禁写：**“现有SP receivers都fixed iterations”“Liu未做adaptive”。论文方法/算法/仿真预算章节未核，不给section/eq造号。

## 3. Huang & Ritcey：online convergence-before-CE，不可降为普通fixed schedule

**[F] Primary metadata：**作者自己的 [2007 Wiley chapter，References，Huang & Ritcey 2005c](https://onlinelibrary.wiley.com/doi/10.1002/9781118256114.ch59) 确认题名、TWC、September2005、2549–2558；chapter正文也未取得。不是拿另一本书的目录冒称读过SIED算法。

**[reported abstract，primary未核]** [所问论文abstract mirror](https://www.researchgate.net/publication/3433292_Joint_iterative_channel_estimation_and_decoding_for_bit-interleaved_coded_modulation_over_correlated_fading_channels)：decoder先至当前stage convergence，再反馈CE；convergence由online SDM检测。无可读full text。**这些技术内容本轮只达secondary abstract，不能列为primary-verified方程事实。**

**per-frame还是fixed？[I]** 若该abstract准确，是输入依赖的online gate，不能概括成固定“每k轮重估一次”。但实际block粒度、SDM阈值及CE间隔重设办法仍unknown；此轮不能给无条件primary-confirmed per-frame verdict。

**[I] Shares，按abstract条件判断：**用decoder状态决定何时把额外工作放到CE，避免不可靠feedback；“CE有时不值得马上做”早有。**Remaining：**SIED报告的是convergence gate；当前候选是比较低预算最终continuation与立即升档continuation的净frame-error改善。**未核到SIED是否还有预测benefit/成本条件；不能排除。**

**[S] 投稿前需补：**SIED正文中SDM/CE-switch算法。不给它自造syndrome rule，也不借secondary描述声称已复现。

## 4. Alves：statistic、false alarm、direction、CE位置

**[F]** [Publisher全文相关section](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-com.2015.0151)，§3、§4.1–4.3、Eq27–30、Table2：

- FLPSCV开始时联合处理符号、CIR和noise variance；CIR/NV估计是其side product。
- η＝**soft-symbol observation reconstruction的empirical mean-square residual**；soft mean来自decoder extrinsic LLR（Eq27正文）。不是syndrome，也不是terminal FER predictor。
- Table2直接给`γ=μ0+σ0 Q⁻¹(1−P_FA)`，`η<γ`时 **FLPSCV→BCJR**。μ0/σ0为H0条件下η的mean/SD；Gaussian近似决定threshold。
- BCJR接收前面FLPSCV得到的CIR/NV。pre-switch的CE在turbo处理内；不能据此说post-switch每轮仍执行同样joint CE。

**[D] Threshold意义：**标准Gaussian下，`Q⁻¹(1−α)=Φ⁻¹(α)`，故低η触发是H0分布下的lower-tail test。控制的是错误切换事件，不是对任何frame的`Pr(final error)≤δ`。

**[F] 假设 / calibration：**§4.2/4.2.1使用perfect-interleaving、若干uncorrelated项、channel-error covariance简化，RLS估计error variance λ。**[I]** estimated moments＋重复查询不自动给distribution-free/global FER控制。此非贬低该文；是保证对象不同。

**Shares：[I]** channel/soft-feedback质量→online选择计算模式；有风险threshold，不只是经验early-stop。**Remaining：[I]** Alves从昂贵joint Bayesian processing **降档** 到BCJR，用CE-quality surrogate；候选从低inner budget **升档**，用两continuations最终FER差。区别是estimand/action/系统，不是升降方向本身有大创新。

**Coverage caveat：[F]** Eq26/27等为图片；本轮image endpoints未得到可读图，浏览器surface不可用。上述η定义来自正文，γ/决策来自可读Table2；未抄未见的exact summation/H0符号。

## 5. Benefit prediction：最决定性的prior，不是普通failure prediction

### 5.1 Akyildiz & Mahdavifar 2026：直接预测rescue

**[F]** [Author preprint，III-A/B，Eq9–12、Alg1](https://arxiv.org/html/2603.20385v1)：frame内LC-OSD checkpoint控制；保留当前best codeword，决定停止返回或继续TEP search。目标为expected effort＋λ·frame error。Eq12 label：**full-search正确且当前错误**；预测该continuation-needed事件。规则：`λ p_j≤Δ_j`则stop，Δ_j为到下一checkpoint的TEP成本。非CE loop；无hard FER constraint。

**[D] 与ours的严格关系。** 令Ystop/Yfull为返回当前/完整搜索的error indicator：

```text
R(z)=Pr(Ystop=1,Yfull=0 | z)   # rescue
H(z)=Pr(Ystop=0,Yfull=1 | z)   # harm
qstop(z)−qfull(z)=R(z)−H(z).
Akyildiz Eq12 target = R(z)，不是单纯Pr(Yfull=1 | z)。
```

条件独立并非此identity前提；共享paired outcome定义即可。原文running-best **metric**随search单调；**[D] metric下降不证明correctness单调**。若H=0，Δ就是其rescue概率的同构对象；不能用“我们预测action value，他只预测失败”区分。

**[F/D] 概率口径还有细节：**原文III-D Eq15用asymmetric／remaining-effort-weighted CE，另有monotonic regularizer。若忽略regularizer、记正类weight=a，负类conditional平均weight=b(z)，loss-optimal sigmoid为

```text
s*(z)=a R(z) / [a R(z)+b(z)(1−R(z))]。
```

这是自推，不是该文的校准定理。**[I]** raw sigmoid不必等于calibrated R；retuned cost-risk score依然是已有benefit prediction，不能因它未做proper probability calibration便重命名为首次action-value预测。

**Remaining：[I]** 两个**未来receiver continuations**（all20 vs now-switch40），非当前best返回 vs继续同一search；可能非嵌套、rescue/harm双向；SP CE-feedback环境；target FER操作约束。**Δ减法、cost-risk λ、paired training labels、适当calibration都不是独立新概念。**

### 5.2 新近邻：iterative neural receiver，预测剩余工作量

**[F]** Roope Niemi，*Iterative deep learning receiver*，Helsinki MSc，2022-05-12。[Author-repository PDF indexed abstract、Ch4/4.1、Ch6](https://helda.helsinki.fi/server/api/core/bitstreams/5088b4e7-aa8e-4251-86e5-8291619377af/content)：SCNN用iterative DeepRx输出预测所需iterations；训练数据逐iteration送LDPC；可在预测超max预算时提前stop。**section/indexed excerpts only**，live PDF fetch blocked；不冒称读过整篇，不称journal paper。

**[F] 更可读的primary disclosure：** [EP4364367A1](https://patents.google.com/patent/EP4364367A1/en)，Description Fig3–4后的stopping/training procedures：模型状态＋LLRs→remaining iterations；以required LDPC success probability（例.95）定义停止；无望在max内成功可放弃。用各state到first successful LDPC的剩余轮数造labels。**Patent section**，非peer-reviewed性能证据；success-probability target不是已证finite-sample FER bound。

**[D] 为何更近：**单条同算法trajectory若到first certified success即退出，T＝first-success time，则

```text
q(B|z)=Pr(T>B | z)；q(B1|z)−q(B2|z)=Pr(B1<T≤B2 | z)，B2>B1。
```

预测所需轮数的conditional分布已经编码“多给预算的挽救概率”。**Remaining：[I]** ours改变joint CE-detection每outer round的inner effort，产生**两条分支trajectory**；不能仅从旧trajectory的first-success time读出counterfactual。该区别需真的建模/测到，不是r feature换名。

### 5.3 新近邻：直接比较两种CE procedure的预计改善

**[F]** [US20260163760A1，2026-06-11，公开文本](https://patents.justia.com/patent/20260163760)，Description Fig5/ref505；Claims4、7：比较additional-RE CE与DMRS-only CE的预计parameter值，差值达到threshold后作为CE capability/selection依据；parameter例为SNR。**section**：原始专利文本的公开reproduction；Google Patents本轮fetch失败。

**Shares：[I]** receiver里“预测多投入CE相对另一procedure的改善”，不是只评当前quality。**Remaining：[I]** 参数/SNR改善＋capability/signalling，非逐frame turbo CE-detection inner iteration升档的terminal FER效应，也非所问FER-constrained控制。不是exact anticipation；足以反驳“CE action value无人预测”的宽claim。专利单列，不能当TCOM实验benchmark。

### 5.4 辅助检索，未升级成决定性事实

- **Andalibi / Nguyen / Salt，IET Commun.6(11):1502–1510，2012，DOI10.1049/iet-com.2010.0858，SAICE。** primary publisher／author thesis fetch失败；secondary abstract称MI criterion决定decoder soft信息何时可用于CE。**blocked / secondary abstract lead**；不引用其“guarantee”当已核定理。值得比单纯stopping更优先补读。[Publisher入口](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-com.2010.0858)。
- **Shepherd / Brännström / Reed，Fidelity charts and stopping/termination criteria for iterative multiuser detection，2006 conference。** [Author-institution abstract](https://research.chalmers.se/en/publication/523289) 已核fidelity／LLR-variance／stopping；full text blocked。**abstract**；未确认rescue estimand，不凑成更近的counterfactual-value先例。
- General “will more iterations help / continued search / expected improvement”检索混入LLM decoding、training early stop、BO code design；剔除。不能把training patience当receiver run-time policy。未穷尽所有decoder families。

## 6. Lee & Yang：exact metric仍缺，不能拿名字替代baseline定义

**[F] Primary author入口：** [CSDL publications，item47](https://www.csdl-lab.postech.ac.kr/international-journals) 的`[Abstract][PDF]`只有同一个 [IEEE5567014 link](https://ieeexplore.ieee.org/document/5567014/)，不是独立open PDF。POSTECH OASIS handles25500/1222 fetch也失败；题名、DOI、author、PDF检索未找到可读open copy。**coverage blocked。**

**[reported abstract，primary未核]** [Abstract mirror](https://www.researchgate.net/publication/224173441_Scheduling_for_an_Adaptive_Number_of_Iterations_in_Turbo_Equalizers_Combined_with_LDPC_Decoders) 描述：从convergence行为导出metrics/criteria，决定是否再执行equalization。**Exact metric unknown**。syndrome、LLR variance、MI increment、expected error reduction，哪一种都不能代填。

**Shares / Remaining：[I]** abstract层面的概念覆盖“追加一次昂贵equalization是否值得”；Δ-based SP budget分支可能更窄。未核exact metric，故不能宣称其没有benefit prediction，也不能把generic syndrome-stall叫Lee复现。

## 7. Distinction verdict与投稿措辞

| Claim层级 | Verdict [I] |
|---|---|
| 首次per-frame adaptive receiver effort | **no**；Alves＋公开neural receiver disclosure已覆盖宽概念 |
| 首次预测additional effort能否rescue | **no**；Akyildiz Eq12明确先例，remaining-iterations也编码该价值 |
| 用risk差值而非一个failure score | **narrowed**；净effect estimand更准，但减法identity和risk-cost decision本身经典 |
| SP joint loop两个未来inner-budget分支的净FER效应＋FER-constrained升档 | **候选仍存；partial coverage，不能first claim**；Liu/SIED/Lee正文未排除同机制 |
| 上述候选足以TCOM | **未证**；须specific SP机制／可迁移action ranking／超过强benefit-aware controls的完整cost收益 |

**[D/I] FER约束不是靠写`s.t.`便新。** finite-policy class允许frame-independent randomization时，`min E[C] s.t. E[Y]≤δ`是线性优化；适当feasibility条件下，存在cost＋λ·risk的supporting dual。hard constraint与Lagrange trade-off仍有**校准/保证/部署**区别，但不能把已有λ-risk stopping误称从未考虑FER。Global FER证书也不自动成为每state/action的conditional guarantee。

**[S] 我接受的TCOM区别一句——仅结果成立后写：**

> 针对短码、已知support的SP joint CE-detection receiver，本文从共同反馈前缀预测额外inner预算相对低预算continuation的净FER改善Δ_e，并在预设FER约束下分配单次升档预算，获得超过调优fixed schedules与benefit-aware adaptive controls的完整接收机计算收益。

**为什么不是单纯receiver换名：[I]** 需要证明SP软反馈误差使“低预算会失败”和“升档可挽救”分离；两分支可能有harm；轻量state可预测net difference；该信息在相同cost/risk机会下改善动作。若harm≈0且direct-rescue classifier同样有效，只能主张SP场景中有效的经典benefit控制，不能把“net Δ”撑作新原理。

**投稿与freeze前的literature concerns；仅意见，不改protocol：**

1. **L-C01 / high：closest-control覆盖。** R3的B3是failure-predictor、B4是q20-triggered promotion；二者不自动覆盖Akyildiz的direct-rescue target。最紧对照是同features/数据/λ或threshold调优的`Pr(Y20=1,Ye=0|z)` predictor；与signedΔ对比。五臂paired labels足够，无新receiver arm。是否加进当前manifest由Claude决定。
2. **L-C02 / high：primary缺口。** Liu/SIED/Lee未读控制章节；只允许“本次已读来源未见exact combination”，禁止“不存在/first”。paper最终related-work前补原文。
3. **L-C03 / medium：保证对象。** Alves false-alarm、EP required success probability、Aky cost-biased rescue score、ours global FER certificate，四者不同；正确对比，不能随意叫calibrated guarantee。
4. **L-C04 / medium：action value措辞。** `Δ_e=Pr(rescue)−Pr(harm)`；若写“rescue probability”，需明说假定harm=0或称net rescue value。已有新颖性修订 [NV correction](aprime-novelty-20261013.md):57–59把Δ简称rescue；建议改其科学措辞，**本轮未改该文件**。

**最终：[I] narrowed，非veto，也非novelty放行。** action-value概念不新；剩余是特定SP联合反馈动作的有用机制与可靠性约束下的实用增量。若只证明比固定20/40便宜、未胜benefit-aware prior-style controller，regular TCOM中心仍弱。
