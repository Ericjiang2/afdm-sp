# Claude opus 查新初筛（第 6 步：l29）——本地第 4 轮，2026-11-22

模型：claude opus（`claude -p --no-session-persistence --model opus`；Gemini 出的卡本应交 gpt-6.2-sol，Codex 无额度后改派，属跨家族）。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s10-claude.prompt`。以下为原文。

查新检索和数值核查都已做完，现在等后台代理把两篇锚点论文全文核对完，结果一到就写最终报告。

## 线 A（l29）：用调频斜率让各径"撞在一起"还是"全部分开"，由翻转码率决定

**一句话结论：不值得做（省去 L2）。**

**固有重要性（抛开先例）：中。**
- 拿"码率决定该保留子信道强弱差、还是该抹平"去指导波形设计，本身是个够格的原理。但这个原理在 OFDM 对单载波的框架里已经发过 Trans（Wang–Ma–Giannakis, TCOM 2004）。
- 搬到 AFDM 后，换的只是酉基的名字。
- 可以回收的东西：
  - 碰撞赫芬达尔指数恒等式 Var_m(G_mm) = H(s) − Σ|h_p|⁴；
  - 2–3 径时逐符号 SINR 被展宽的读数（对齐基 [3.5, 14.5] dB，分离基 / OFDM 被压平到约 [7.4, 9.1] dB）。
- 这两项适合作为一条附注，并入 `l09`（跨波形公平比较）。

### 白话 + 类比
- 线性 MMSE 均衡后，每个符号各分到一个信噪比，总量由信道决定，酉基只决定怎么分：
  - "对齐"让分配有贫有富，相当于 OFDM；
  - "分离"让分配人人一样，相当于单载波频域均衡 / 扩展 OFDM。
- 低码率的纠错码善于"劫富济贫"，不均匀反而赚；高码率的码怕穷人，均匀更好。
- 类比：一个团队的总工资固定，团队弱项能互补时（低码率），可以拉开差距；一个人掉链子就全盘失败时（高码率），平均分更稳。
- 剥掉术语后，这就是 2002–2004 年 "coded OFDM vs SC-FDE" 的老结论，只是把"OFDM 还是单载波"换成了"AFDM 的 c1 取哪个值"。

### 最接近的工作
1. **Wang, Ma, Giannakis, "OFDM or single-carrier block transmissions?", IEEE TCOM 52(3), 2004**（读了摘要）。原文结论是：码率高（如 3/4）时选 ZP 单载波，码率低（如 1/2）时选编码 OFDM。卡片第 (2) 条的方向和"3/4 附近翻转"在这里已经有了；差别只在于卡片把它放到了双色散信道和调频斜率上。
2. **Falconer 等, "Frequency domain equalization for single-carrier broadband wireless systems", IEEE Commun. Mag. 2002；802.16 教程 2001**（只看了摘要和片段）。结论是：编码线性 SC-FDE 在高码率、高 SNR 下优于编码 OFDM。工程界早就知道这一点。
3. **Palomar, Cioffi, Lagunas, IEEE TSP 51(9), 2003**（摘要 + 我对该文的已有了解）。目标函数是 Schur 凹时选对角传输，Schur 凸时乘一个酉旋转、把各路 MSE 抹平。卡片第 (1) 条"把 MSE 向量推到 Schur 序的两端"就是这个框架。卡片新加的只有两点：一是酉基限制在单参数的调频子群里，二是目标换成有限星座下互信息对 MSE 的函数 φ_M。
4. **Lozano–Tulino–Verdú, TIT 2006（mercury/waterfilling）；Xiao–Zheng–Ding, TSP 2011；Palomar arXiv:0904.4900**（摘要）。有限星座在高 SNR 会饱和，强信道"装不下"更多比特，所以最优解从对角走向酉旋转。翻转码率的物理原因（饱和）就是这里讲的。
5. **Carmon–Shamai–Weissman, TIT 2015, arXiv:1306.5781**（摘要）。在 i.i.d. 有限星座下比较 OFDM 和单载波的可达速率，结论是最优单载波常常优于 OFDM，并给出了"互信息对 log-SNR 是凹函数"一类的结果。它讨论的是最优接收，不是线性 MMSE，也没有给码率阈值。
6. **DVB-T2 旋转星座 / 信号空间分集**（UPV 论文 Gozálvez 等，只看了片段）。二维旋转把衰落平均掉，增益主要出现在码率高于 1/2 时，低码率时收益变弱。这是同一现象在二维旋转上的版本，有标准级的工程证据。
7. **Martone, "A multicarrier system based on the fractional Fourier transform for time-frequency-selective channels", IEEE TCOM 2001**（摘要）。思路是选一个 chirp 角度让双选信道尽量变成对角，也就是"对齐"准则的老祖先。
8. **Li 等, "Chirp parameter selection for AFDM with MMSE equalization", IEEE TCOM 2024**（摘要）。研究 MMSE 下 c1 如何影响 BER，用的是无编码 BER 准则。
9. **Li, Yuan 等, "Performance analysis of coded OTFS…", TWC 2021；arXiv:2311.15595（编码 AFDM）**（摘要）。结论是可分辨径越多，分集增益越大、编码增益越小。编码以后"分得越开越好"不再成立，这在 OTFS/AFDM 里也已经有人指出。
10. **Yin, Wu, Cavallaro, Studer：大规模 MIMO 里共轭梯度（CG）检测优于 Neumann 级数**（GLOBECOM 2014 / ISCAS 2015，摘要）。卡片第 (3) 条"Neumann 会发散、共轭梯度不会"是教科书内容。另外，2610.10872 原文自己就写了 "NE does not converge for a small fraction of channel realizations"。

### 两篇锚点论文核对（问题 b）
两篇都存在，作者、日期和卡片一致。我读了 2610.10872 的 HTML 全文；2607.20227 只逐字读到约 60%，第 V 节没有核到。

- **2610.10872**：
  - 选子群的准则原句是 "choose the subgroup S to maximize the diagonal component of the channel energy"。
  - 这个准则是为了让单抽头 / Neumann 均衡器便宜（对角占优），不是为了 BER 最优。
  - 评估是无编码 4-QAM、完美 CSI，主信道为两径、Rician K = 10，另有 TDL-D。
  - 全文没有编码，没有共轭梯度，没有导频。
- **2607.20227**：
  - 用无编码 BER 的简化代理指标选 c1（Eq. 21/28），原文说 "smaller P_e indicates weaker effective coupling"。
  - 它允许多径峰重叠，不要求路径分离（Eq. 44，Remark 5），也不引用 2610.10872。
  - 卡片说它"将 c1 推向路径分离、均衡每符号 MSE"，在我读到的部分里找不到依据。
- **结论**：卡片所说的"两篇正面矛盾"不成立。两篇都是无编码评估，一篇优化的是均衡复杂度，一篇优化的是无编码 BER 代理。"统一两派"是卡片自己构造出来的。

### 我做的数值核查
- **翻转点复现**：QPSK 的 φ_M 拐点我复现出 3.37 dB、R = 0.749，和卡片一致。
- **但"精确翻转码率"只在各符号 MSE 差别很小时成立。** 我对 QPSK 做了扫描：保持平均 MSE 不变，比较"两点散开"和"完全抹平"的互信息，看交叉码率怎么随散布变化：

  | 逐符号 SINR 的跨度 | 交叉码率 |
  |---|---|
  | 2.7–4.0 dB | 0.747 |
  | −0.3–6.8 dB | 0.704 |
  | −5.7–11.6 dB | 0.585 |

- 对齐基的实际跨度约 11 dB，正好落在拐点规则失准的区域。所以 R* 只是一个小散布下的近似，不是统一准则；实际的分界取决于整个 SINR 分布，而不是一个码率常数。

### 查新判断：部分被做过，核心已被做过
- **(1) 用酉基把 MSE 推到两端**：Palomar 2003 已有。限制到调频子群、只用功率谱来选基，有 Martone 2001 和 2610.10872 在前。
- **(2) 码率决定对齐还是分离，翻转在 3/4 附近**：Wang–Ma–Giannakis 2004、Falconer 2002 已有，DVB-T2 旋转星座是同类工程证据。机理（有限星座饱和导致 Jensen 方向翻转）由 Lozano 2006 和 Xiao 2011 给出。"拐点处 φ_M″ = 0"这个具体式子我没找到有人写出来过，但它是一行计算，而且如上所述在大散布下不准。
- **(3) Neumann 发散换共轭梯度、路径碰撞后单导频降秩**：前者是教科书内容，且锚点自己承认 Neumann 不总收敛；后者正是 Bemani 等人要求 c1 让各径分开的原因（为了可辨识）。
- **剩下的增量**：赫芬达尔恒等式加一组 AFDM 上的数值，不足以单独成文。

### 为什么没人在 AFDM 上做：(2) 发现了但不重要
- **结论早已知道**：OFDM 对 SC-FDE 的编码交叉是 20 年前的标准结论。5G NR 同时有 OFDM 和 DFT-s-OFDM，但选哪个看的是覆盖和 PAPR，不看码率。这说明这笔增益在工程上不足以驱动波形切换。
- **实际接收机会抹掉增益**：卡片自己承认充分迭代的 turbo 接收机会让增益消失。LTE 上行的研究也显示，turbo 均衡在高码率下能补回大约 1 dB 的 SC-FDMA 差距（AAU 研究）。
- **还有隐藏的开销税（(3) 的成分）**：对齐基会让单冲激嵌入导频失效，必须换成叠加导频。叠加导频有数据自干扰，这正是本项目第 0 轮的已知瓶颈，所以这笔税不是零。

### 问题 (c)：几轮干扰抵消后还剩多少
- 卡片明确说充分迭代后收益消失。
- 5G/6G 基站接收机普遍有多轮迭代或 SIC 的余量，增益大概率只剩下"单次 LMMSE 低功耗终端"这一个角落。
- 我没有做迭代臂的实测，这一点是推断。

### 真实系统里的影响
- **会改变的决定**：按 MCS 切换 c1（对齐或分离）。
- **增益量级**：
  - 0.7–2.5 dB 只出现在 2–3 径、共线几何（k_p ∝ l_p）、16/64-QAM、白送真信道、N = 64/256、用互信息折算（不是实测 FER）的条件下；
  - 8 径随机多普勒 + QPSK R = 1/2 时只有 0.06–0.08 dB。
- **按 FUNNEL「参数与适用范围」**：大增益只在共线几何这个窄角落成立，需要降一档（LESSONS 规则 5）。
- **前提**：完美 CSI、只做一次 LMMSE、需要慢变时延–多普勒几何的 CSIT，三者同时成立才有这个量级。2610.10872 的主场景 K = 10 强直射径下，"对齐"本身就接近 OFDM 加多普勒预补偿，而 5G NTN 已经在做这件事。

### 最强的反对意见
"对齐"就是在调频基里做 OFDM，"分离"就是做 SC-FDE。码率决定谁赢是 TCOM 2004 的结论，Jensen 机理是 Palomar 和 Lozano 的结果；卡片声称的"精确翻转码率"在它自己的 11 dB SINR 散布下会偏移到约 0.6；两篇锚点也并不矛盾。

### 如果非要做，最便宜的一步
- 不跑 L2。
- 若想救，只花 10 分钟在 SC-FDE / OFDM 链路抽象（MIESM）文献里确认"拐点式"有没有被写出来；即使没有，也只能当 `l09` 的一段附注。
- 卡片里锚点 A2 的描述应该改正。

---

**过程说明**：
- `paper-search` 和 `scoop-check` 的 Python 脚本在当前权限模式下需要批准、没能运行。我按 `scoop-check` 的结构，用网页搜索代替做了检索。
- 第 1、2、4–6、8–10 篇只看了摘要或片段，第 3 篇另外依赖我对该文的已有了解；锚点论文读的是 HTML 全文，2607.20227 第 V 节未核。
- 数值核查（拐点复现、散布对交叉码率的影响）是本地的一次性计算，没有写入任何项目文件。

需要更浅的版本可以说「白话」。

Sources:
- [arXiv:2610.10872](https://arxiv.org/abs/2610.10872) · [HTML](https://arxiv.org/html/2610.10872v1)
- [arXiv:2607.20227](https://arxiv.org/abs/2607.20227) · [HTML](https://arxiv.org/html/2607.20227v1)
- [Wang–Ma–Giannakis 2004 (UMN)](https://experts.umn.edu/en/publications/ofdm-or-single-carrier-block-transmissions/) · [dblp](https://dblp.dagstuhl.de/rec/journals/tcom/WangMG04.html)
- [Carmon–Shamai–Weissman arXiv:1306.5781](https://arxiv.org/abs/1306.5781v1)
- [Palomar–Cioffi–Lagunas 2003 PDF](https://palomar.home.ece.ust.hk/papers/2003/TransSP2003_convexJTRbf.pdf)
- [Xiao–Zheng–Ding TSP 2011](https://www.lehigh.edu/~xiaoc/Pub/Xiao_Zheng_Ding_TSP11.pdf) · [Palomar arXiv:0904.4900](https://web3.arxiv.org/pdf/0904.4900)
- [Falconer SC-FDE overview](https://typeset.io/pdf/broadband-wireless-using-single-carrier-and-frequency-domain-rn8doxc3ri.pdf) · [802.16.3 contribution](https://www.ieee802.org/16/tg3/contrib/802163p-01_31r2.pdf)
- [Rotated constellations in DVB-NGH (UPV)](https://riunet.upv.es/bitstream/10251/54638/3/Gozalvez%2c%20D%20-%20Rotated%20Constellations%20in%20DVB-NGH.pdf)
- [Martone 2001 record](https://manuscript.isc.ac/Inventory/49/1504883.htm)
- [Li et al. chirp selection with MMSE (EURECOM)](https://www.eurecom.edu/en/publication/8017)
- [Coded OTFS arXiv:2010.13008](https://arxiv.org/abs/2010.13008) · [Coded AFDM arXiv:2311.15595](https://arxiv.org/pdf/2311.15595)
- [Yin et al. CG detection GLOBECOM 2014](https://www.csl.cornell.edu/~studer/papers/14GLOBECOM-cg.pdf) · [ISCAS 2015](https://www.csl.cornell.edu/%7Estuder/papers/15ISCAS-cg.pdf)
- [SC-FDMA vs OFDMA 802.16m contribution](https://www.ieee802.org/16/tgm/contrib/C80216m-08_146.pdf) · [AAU turbo equalization SC-FDMA](https://vbn.aau.dk/ws/files/19119881/improvingSCFDMA.pdf)
