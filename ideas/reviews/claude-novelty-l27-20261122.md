# Claude opus 查新初筛（第 6 步：l27）——本地第 4 轮第 1 次筛选（第 9 次统一筛选），2026-11-22

模型：claude opus（`claude -p --no-session-persistence --model opus`；原定 gpt-6.2-sol，Codex 无额度后改派，Gemini 出的卡交 Claude 属跨家族）。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s9b-claude.prompt`。以下为原文。

## 线 A（卡片 l27）：未编码 QPSK 离散先验 + Stein 校准 + 带状 VAMP + 轻量展开

**一句话结论：不值得做（省去 L2）。** 唯一值得留下的是一个约 0.5 核时的小检验：在项目自己的 F0 上，把第 0 轮在译码前多迭代几次。它作为 `11-21-data-pilot-fer` 的一条对照臂，不单独立卡（理由同 c02 被杀）。

先说两处方法上的偏差：
- **`paper-search` 的检索脚本被权限拦下，我没有重试。** 查新改用网页搜索，按 scoop-check 的步骤手动做：拆新意、三类查询、读最接近的几篇、逐轴打分。scoop-check 要求的逐步落盘文件没有写。
- **全文只读了 Mishra 2022 一篇**，读的是 §IV-A/B 的公式页。另有两篇读了约 40% 全文；其余只看了摘要或检索摘要，下面逐条注明。

---

**固有重要性（抛开先例）：低。** 问题本身有价值：项目冻结读数显示，ρ = .25 的扫描最优点 4.95 dB 与 ρ = .10 第 0 轮给真信道的 3.45 dB 之间有 1.5 dB 的真缺口。但解法的每一块都是教科书部件，拼在一起是一篇接收机工程文章，算不上原理。

卡里最像原理的是"β = 0 爆、β = 1 缩"。可是在精确后验下，β = 1 的软 EM 本来就无偏：对 y 取期望，E[E[x|y]* y] = E[x* y]，这是塔性质。所以卡里测到的 0.84 倍收缩，说明的是 `scalar_joint` 给出的软符号不是校准好的后验，不是 EM 有缺陷。修法属于 Onsager / 外信息校正这一类，是已知的。

能回收的诊断账本有三项（都只在卡的小探针上，未在项目帧上复现）：
- 真信道不动点处 β = 0 / 1 / 校准三个读数（|g| = 1.60 / 0.84 / 约 1.0，20 帧）；
- ρ = .05 时 `TrueH_VAMP`（固定真信道、不重估增益）在 3.5 / 4.0 dB 误帧率 .05 / .00。而 STAGEA2 记录 F0 在 ρ = .05 给全真信道也失败，原因是检测器联合重估增益失稳。两者对上了：ρ = .05 的失败点在增益重估这一步；
- QPSK 局部 Fisher 信息的数值表，可补 `STAGEA4_PROTOCOL.md` 第 18 行"QPSK 没单独算"的空格。

**白话 + 类比。** 导频太弱，接收机第一眼认不清回声，就先"猜一遍数据"，再拿猜出来的数据当额外导频重认回声，来回几轮。这就是叠加导频领域的标准迭代接收机，OTFS 上 2021–2022 年已有人做（见下）。卡里的三处新意分别是：
- 猜的时候利用"符号只落在四个点上"。项目的 `scalar_joint` 本来就带 QPSK 离散先验；
- 对"猜得不准的部分"给一个修正系数，就是那个 β；
- 换一个更好的线性检测器，再学几个调度参数。

类比：考试时先凭直觉把题做一遍，再用这遍答案反推题意，重做。剥掉术语后，基本只剩"译码前多迭代几轮，并把软符号的置信度算对"。

**最接近的工作**

1. **Mishra, Singh, Prasad, Budhiraja, IEEE TWC 21(4) 2022**（[arXiv:2010.15066](https://arxiv.org/pdf/2010.15066)；读了摘要和 §IV-A/B 公式页）。这是叠加导频 OTFS 的 SP-I 设计：信道估计与未编码消息传递检测交替迭代。式 (43)–(47) 用硬判决 x̂ = argmax 构造数据辅助导频矩阵，再做 LMMSE。式 (48) 用各向同性的误差协方差 2Σσ²ₕσ²_d I 吸收判决误差。论文还优化了导频与数据的功率分配。
   - 与卡的差别：整数网格、已知径位置，迭代里只重估增益，不重估多普勒和支撑；误差项很粗，没有逐符号方差。
   - 这一篇已经占了卡的问题框架："低功率叠加导频 + 译码前用未编码检测结果迭代重估信道 + 优化 ρ"。
2. **Yuan, Li, Wei, Yuan, Ng, IEEE WCL 10(9) 2021**（[检索摘要](https://cris.fau.de/publications/262977477)；只看了摘要）。单导频粗估后，用和积算法检测的数据迭代细化信道，误码率逼近真信道。被引为第一个叠加导频 OTFS 数据辅助估计器。与卡的差别：同为未编码迭代，未处理分数多普勒与支撑重搜。
3. **Zheng, Wen 等, "Joint Channel Estimation and Data Detection for AFDM With Superimposed Pilots", 2025**（[BIT 记录](https://pure.bit.edu.cn/zh/publications/joint-channel-estimation-and-data-detection-for-afdm-with-superim/)，前作 [arXiv:2404.10232](https://arxiv.org/html/2404.10232v1)；只看了摘要）。AFDM 上的迭代联合估计检测，自述只在数据功率低时胜过嵌入导频。与卡的差别：同场景同思路，没有方差校准，也没有和扫描最优 ρ 正面比。
4. **"Learning-Aided Iterative Receiver for Superimposed Pilots", [arXiv:2507.10074](https://arxiv.org/html/2507.10074v1)**（读了约 40% 全文，其余是子代理的摘要）。编码系统，译码器在环（LDPC），软均值回送做信道细化，没有符号方差项；只有细化估计器是学来的（CNN），ρ 固定为 0.3。与卡的差别：多入多出 OFDM，不扫低 ρ，没有展开。
5. **Song, Singer, Sung, "Soft input channel estimation for turbo equalization", IEEE TSP 2004；Otnes & Tüchler, IEEE TWC 3(6) 2004**（[dblp](https://dblp.org/rec/journals/twc/OtnesT04)）；**Nicoli, Ferrara, Spagnolini, "Soft-iterative channel estimation", IEEE TSP 2007**（[polimi 记录](https://re.public.polimi.it/handle/11311/255396)）。都只看了摘要或检索摘要，下面的细节来自我自己的记忆，没对全文核过。软输入信道估计要不要带符号方差项、用先验 / 外信息 / 后验哪种软符号、软迭代估计的均方误差分析，这条线 2004–2007 年已系统研究过。它对应卡的 (b)：β = 0 时只用软均值做最小二乘会放大增益，带方差项的 EM 形式是标准推导。
6. **Kamilov, Rangan, Fletcher, Unser, adaptive GAMP, IEEE TIT 2014**（[arXiv:1207.3859](https://arxiv.org/pdf/1207.3859.pdf)；读了摘要）；**Guo & Davies, SURE-AMP, TSP 2015**（[arXiv:1409.0440](https://arxiv.org/pdf/1409.0440)；读了摘要）。前者在 AMP 内部一边迭代一边做参数的最大似然估计，证明能收敛到真值；后者用 Stein 无偏风险估计逐层调去噪器参数。这是"Stein 校准迭代内参数"的数学先例，卡把它搬进了 VarPro 的 M 步。
7. **Çirpan & Tsatsanis, "ML blind channel estimation in the presence of Doppler shifts", IEEE TSP 47(6) 1999**（[ITU 记录](https://research.itu.edu.tr/en/publications/maximum-likelihood-blind-channel-estimation-in-the-presence-of-do/)；只看了摘要）。盲联合估计多普勒与信道，随机最大似然解用的是改进 Baum-Welch（一种 EM），给了 CRB；面向短突发。**Scherb, Kühn, Kammeyer, Asilomar 2004**（[pdf](https://www.ant.uni-bremen.de/sixcms/media.php/102/4494/Asilomar_2004_scherb.pdf)；PDF 没能解析，只看了检索摘要）推导了有限字母表（编码 / 未编码）的半盲 CRLB，对照的是 de Carvalho–Slock 的高斯 / 确定性模型。卡的声称 (1)"离散星座比高斯多带信道信息"是这条线的已知结论，在单载波同步文献里也是常识（Steendam–Moeneclaey 2001，卡自己也引了）。

**查新判断：部分被做过，按 scoop-check 判 Level 2（高重叠）。** 对 Mishra 2022：问题框架、"迭代数据辅助"这一机制、"数据辅助消导频与数据互扰"这一洞见三轴都对上，只差领域（AFDM、分数多普勒、支撑重搜）。

差量一句话：不同于 Mishra 2022 在整数网格、已知径位置下用硬判决只重估增益，本卡在连续分数多普勒与未知支撑下，用带方差校准的软符号重估多普勒和支撑，并且对照扫描最优 ρ。这个差量真实存在，但属于"把已知做法推广到更难的信道"，量级是工程增量。

再对照项目自己：F0 每个外轮已经用译码器的后验均值和方差做 `time_refine`，求解 (BᴴB + Γ(v) + σ²I)h = BᴴY，这就是 β = 1 的软 EM M 步；`scalar_joint` 在第 0 轮已经是"QPSK 离散先验 + 增益"的双线性 AMP。卡相对 F0 的实际增量只有两点：第 0 轮在译码前让 `time_refine ↔ scalar_joint` 多转几圈；改 Γ 的权重。

**为什么没人做：(2) 发现了但不值得单独成文。**
- 未编码迭代重估：Mishra、Yuan、Zheng 都在做。
- 软符号带不带方差项、用哪种软信息：2004 年前后已有定论。精确 EM 自带方差项且无偏，所以没人会把"给方差项乘一个系数"当贡献写。
- VAMP 换标量 AMP：卡自己的真信道臂上两者误帧率相同（.95/.45/.10 对 .90/.45/.10），盲迭代里的差异出自 20 帧噪声，4 dB 时 VAMP 反而更差（.35 对 .30）。这与项目 11-09 的否定记录一致：OAMP 形式的线性估计器在固定信道下救回的帧少了 5 个，耗时是 13 倍。两者场景不同（11-09 是高 SNR 下译码失败后的补救、信道固定、没有估计环），但结论同向：检测器的形式不是瓶颈。
- 浅层展开学 6–8 个标量，本质是自动调阻尼和温度，学术增量很小。

**真实系统里的影响。** 能改变的决定是叠加导频 AFDM 的导频比例：从 ρ ≈ .25 降到 .10，上限 1.5 dB。这个奖池是项目 STAGEA2 的真值上限，属于 `11-21-data-pilot-fer` 已在追的同一个奖池（规则 3）。卡的数字前提不成立：
- **基线偏弱。** 卡自写的 `BaseF0` 在 ρ = .25、5.0 dB 时误帧率 .333，而项目 F0 在 4.95 dB 已到 1%。基线至少差半个 dB 以上，"领先 1 dB"不能收（规则 18）。
- **测试环境对不上。** 卡的 `TrueH` 在 ρ = .10、4 dB 时误帧率 .10；项目 STAGEA2 在同一 ρ 下给真信道，1% 穿越点是 3.45 dB。卡的仿真环境或检测器至少比项目差约 1 dB，卡里所有数字都不能和 4.95 / 3.45 并排比。
- **离 1% 很远。** 卡最好的盲迭代臂在 4 dB 误帧率 .35（Blind_VAMP）或 .067（Turbo50，30 帧里错 2 帧），离 1% 都很远，"≤ 4.15 dB"没有证据。
- **0.019 bin 是真值处的局部界。** 到不了盲捕获的吸引域（规则 15）。

**最强的反对意见。** 卡里新的部分就是第 0 轮译码前多转几圈、再给 Γ 乘个权重。这是 Mishra / Yuan / Zheng 已有的调度旋钮，精确 EM 本来也不需要这个校正；它的全部增益证据，都来自一个比项目 F0 弱半个 dB 以上的自写基线，和一个真信道性能都对不上项目的测试环境。

**如果要做，最便宜的一步。** 只用项目现有代码，不写新模块，约 0.5–1 核时：

- **帧与工况**：stageA 原帧 41000–41199（U/G），ρ = .10 / .12，3.5–4.5 dB。
- **四臂，计算量配平**：
  1. F0 原样，2 个外轮；
  2. F0 加 1 个译码器在环的外轮，共 3 轮。这是决定取舍的对照：同样的算力，花在译码辅助上还是花在未编码内迭代上（规则 6）；
  3. F0 第 0 轮译码前插 K = 3 次 `time_refine ↔ scalar_joint` 内迭代，β = 1；
  4. 同 (3)，β = σ²/v_r。
- **预注册判据**：(3)/(4) 的 1% 穿越点若在 ρ ≤ .12 下都高于 4.15 dB，或不比 (2) 好 0.2 dB 以上，直接关闭；(4) 不比 (3) 好就说明 Stein 校准无用。

读数只并入 `11-21-data-pilot-fer` 阶段 B 当候选算子，不单独立卡。另外，ρ = .05 时"固定真信道能过、重估增益就失稳"这一点，可以在阶段 B 顺手加一条臂确认。

Sources:
- [Mishra et al., arXiv:2010.15066](https://arxiv.org/pdf/2010.15066) · [dblp TWC 2022](https://dblp.dagstuhl.de/rec/journals/twc/MishraSPB22.html)
- [Yuan et al., WCL 2021](https://cris.fau.de/publications/262977477)
- [Zheng et al., AFDM SP joint CE/DD 2025](https://pure.bit.edu.cn/zh/publications/joint-channel-estimation-and-data-detection-for-afdm-with-superim/) · [arXiv:2404.10232](https://arxiv.org/html/2404.10232v1)
- [arXiv:2507.10074](https://arxiv.org/html/2507.10074v1) · [arXiv:2601.22523](https://arxiv.org/html/2601.22523v1)
- [Otnes & Tüchler TWC 2004 (dblp)](https://dblp.org/rec/journals/twc/OtnesT04) · [Nicoli et al. TSP 2007](https://re.public.polimi.it/handle/11311/255396) · [Yoon & Moon arXiv:1104.0419](https://arxiv.org/pdf/1104.0419)
- [Kamilov et al. arXiv:1207.3859](https://arxiv.org/pdf/1207.3859.pdf) · [Guo & Davies arXiv:1409.0440](https://arxiv.org/pdf/1409.0440)
- [Çirpan & Tsatsanis TSP 1999](https://research.itu.edu.tr/en/publications/maximum-likelihood-blind-channel-estimation-in-the-presence-of-do/) · [Scherb et al. Asilomar 2004](https://www.ant.uni-bremen.de/sixcms/media.php/102/4494/Asilomar_2004_scherb.pdf) · [de Carvalho & Slock](https://www.eurecom.fr/en/publication/82)
