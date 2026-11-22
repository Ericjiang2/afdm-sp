# Claude 查新 + 重要性审查：I-20261122-l17（2026-11-22，本地第 3 轮；claude -p --no-session-persistence --model opus，代替无额度的 Astra；提示 ~/.cache/idea-funnel/afdm-20261122-l3/nov_l17_claude.prompt）

# 卡 I-20261122-l17 审查：查新与重要性

**一句话结论：不值得。** 卡片两条定律的数字，一半来自它算错了锚点论文的估计器，另一半来自它借用了水声项目的帧长；按真实做法和 LEO 的 OFDM 参数重算，剩下的都能从已有文献直接推出来。

## 白话 + 类比

两颗卫星像两只麦克风，旁边有个大喇叭在喊。做法是把一只麦克风的声音对齐后反相相减，抵掉大喇叭。卡片说了两件事。第一，你想听的人也在说话，会干扰"该减多少"这个估计。第二，相减之后，这个人的声音自己也被减了一份，变成"原声 + 一个晚到又变调、音量相同的回声"，简单的线性滤波器处理这种回声很吃力。剥掉术语，这两件事都是常识：前者是"调对消器时目标信号混在训练数据里"，雷达界从 1980 年代就在研究；后者是"两径等强回声信道里线性均衡器吃亏"，教科书上就有。卡片自称两者拼起来以后"任何波形都绕不开"，这句在 LEO 的实际参数下不成立（理由见下）。

## 最接近的工作

1. **Tancovici 等，arXiv 2611.06719（2026-11）**。读的是全文 HTML，正文到第 VI 节为原文，参考文献只部分核对。
   - 卡片引的原句存在，在第 VI 节最后一句："Desired-user synchronization, signal-preserving combining, and equalization where needed remain future work." 第 I 节还写了 "equalization needed when intersymbol interference is present [18]" 和 "Residual INR alone does not establish desired-signal preservation or achievable rate"。也就是说，作者已经预见到置零以后要做均衡，卡片的定律 2 在定性层面已被锚点论文指出。
   - **关键差别：锚点的权重不是最小二乘标量回归，而是先按支路噪声白化、再取最小特征值的向量**（原文："generalized Rayleigh-quotient minimizer … minimum-eigenvalue rule after branch-noise whitening"）。卡片的定律 1 整个建立在 $\hat w_{LS}=\mathbf y_2'^H\mathbf y_1/\|\mathbf y_2'\|^2$ 上，估计器搞错了。
2. **Widrow 等，1982，信号对消（signal cancellation）**。只看了摘要和检索片段。训练数据含期望信号会导致对消器把期望信号也消掉，文中已给出"从自适应数据中去掉信号分量"的修法。卡片的"一步导频去偏"就属于这一类。
3. **Krolik & Swingler，IEEE TSP 1994**。只看了摘要。用同一批数据既算权重又出输出，信号会被部分对消、估计有偏，文中给出了偏置校正版本。这就是卡片定律 1 里"偏置 + 去偏"的通用形式。
4. **Haimovich、Pugh、Berin，"Training and signal cancellation in adaptive radar"**。只看了摘要。采样矩阵求逆（SMI）在训练含目标时对消尤其严重；**基于特征分析的对消器对训练含目标更稳健**。这正好对应锚点用的最小特征值规则：锚点选的估计器本来就是对这个问题更稳的一类。
5. **Farrell，SMI 类滤波器（检索到的只是作者主页上的摘要，原文未读）**。不含期望信号的协方差效果更好；用导频辅助或判决引导的变体，在含信号的数据上也能接近不含信号的性能。卡片的"导频去偏"修法在这里已有。
6. **Fante & Vaccaro，"Wideband cancellation of interference in a GPS receive array"，IEEE TAES 2000**，以及 MITRE 的后续报告。只看了摘要和目录。空时对消会改变阵列对期望信号的频率响应，让期望信号失真；加约束的算法可以避免。"置零会让期望信号变成色散信道"在 GPS 抗干扰里是早有的认识。
7. **Bottomley & Jamal，VTC 1995，"Adaptive Arrays and MLSE Equalization"；Bottomley 等 1999 多通道 MLSE**。只看到引用信息。先用阵列抑制干扰、再用 MLSE（最大似然序列检测）对付多径，正是卡片"置零后用非线性均衡"的接收机结构，GSM 的 IRC（干扰抑制合并）+ MLSE 就这么做。
8. **Cioffi 等，MMSE-DFE Part I/II，IEEE TCOM 1995**。本次未重读，凭已知内容。在有谱零点的信道上，线性 MMSE 吃亏、MMSE-DFE 加编码能逼近容量。卡片的 $\mathrm{SINR}=S-1$ 就是等增益两径信道上的标准积分 $\frac1{2\pi}\int\frac{d\theta}{1+\gamma_0|1-e^{j\theta}|^2}=1/\sqrt{1+4\gamma_0}$，我用数值代入核对过。
9. **Surabhi、Augustine、Chockalingam，IEEE TWC 2019，未编码 OTFS 的分集**。只看了摘要。即使用最大似然检测，渐近分集也只有 1。双色散信道上固定波形做不到"满分集"已有分析，但这篇没有专门讲线性 LMMSE。
10. **Jia 等，arXiv 2601.15557（2026，分布式抗干扰博弈）**。只看了摘要。多星分布式抗干扰的模型里有期望用户（按可达速率做博弈），但用的是空间协方差模型，不涉及时延–多普勒对齐，也不涉及置零后的回声信道。
11. **Sun 等，arXiv 2607.25562**（卡片已列）。只看了摘要。多星无蜂窝 OTFS 联合估计与检测，用户全部协作，没有未知干扰。

## 查新判断：部分被做过，可以说是拆开以后都已被做过

- **定律 1（训练时期望用户在发造成的偏置地板）：主要数字是估计器搞错的结果。** 我用 numpy 做了一个只算不写的小算例（$N_v=1024$，期望用户在干扰对齐的位置上两支路互不相关，200 次平均）：

  | 期望用户 SNR（两支路） | INR | 锚点的最小特征值规则 | 卡片的 LS 规则 |
  |---|---|---|---|
  | 15 / 15 dB | 20 dB | −13.9 dB | **+5.9 dB** |
  | 15 / 15 dB | 30 dB | −15.3 dB | −2.6 dB |
  | 15 / 9 dB | 20 dB | −1.3 dB | −4.0 dB |
  | 无期望用户 | 20 dB | −27.5 dB | −16.8 dB |

  表中数值为残余 INR，相对热噪声。可以读出三点：
  - 在卡片的主场景（两支路期望用户功率相等）下，锚点估计器**没有偏置地板**。残余 −13.9 dB，接近卡片自己写的"无偏地板" −12 dB；那只是把锚点公式 (18) 里的噪声换成"噪声 + 期望用户"。卡片宣称的 +6.1 dB 损失属于 LS，与锚点无关。
  - LS 即使没有期望用户也有衰减偏置（−16.8 dB 对 −27.5 dB），这是经典的"自变量含误差"偏置，锚点正是为此才用最小特征值规则。
  - 真实存在的偏置只出现在两支路期望用户功率不等时（15/9 dB 下 −1.3 dB）。这是"非白噪声下特征对消器有偏"，修法是用总支路功率白化或导频辅助（Farrell / Widrow 一类），属于已知结论。
- **定律 2（平衡几何下线性均衡的信干噪比只按 √SNR 增长，"任何固定波形都绕不开"）：积分是教科书内容，而"绕不开"依赖一个错用的参数。** 卡片里 $\delta\nu=0.75$ bin 用的是本项目水声 `ctx.system` 的长帧（$N=1024$，$T=64$ ms），或 1 ms 帧。LEO NR-NTN 用 15/30 kHz 子载波，卡片自己给的差分多普勒 750 Hz 只相当于 **0.05 / 0.025 个子载波**。按卡片自己的 1-tap 公式，$\kappa=1$ 时 ICI 地板约为 $(1+0.992)/0.008\approx 250$（约 24 dB），不是 0–3.7 dB。这时 OFDM 每个子载波看到的是一个随时间缓慢变化的梳状信道，编码 OFDM 用逐子载波的软信息就能拿到卡片自己写的 $C_{opt}$（同一个 Jensen 积分）。所以 √SNR 增长只落在"扩频类波形 + 一次性线性 LMMSE"上，而这恰好是 Cioffi 1995 的原结论。
- **选星对准则（c）基本不是一个可调的旋钮。** 下面是我的推断，没有算例支持：$\kappa=\sqrt{\rho_s/\rho_I}$。期望用户和干扰源相距 3–10 km、卫星在 550 km 以上时，两者到两颗星的增益比几乎一样，所以无论选哪一对星，$\kappa\approx1$ 都是常态。要让 $\kappa=0.5$，得靠每颗星的波束在用户和干扰源之间有 6 dB 的方向分辨，而不是"挑一对功率不平衡的星"。

## 为什么没人做：(2) 发现了，但已是常识或不重要

按"判断前写三句白话"的规矩：
- **谁真卡住了**：锚点论文目前只到"残余干扰有多小"，作者自己写明要保住信号、需要时要均衡。但能用的估计器（特征对消器 / 导频辅助）和接收机结构（IRC + MLSE、DFE、turbo）都已有现成做法，没有人卡在"不知道怎么做"。
- **最朴素的合理做法丢多少**：锚点估计器 + NR 子载波间隔的编码 OFDM，在卡片的主场景下既没有偏置地板，也没有 √SNR 墙。卡片宣称的 3.9–6.1 dB 和 4.4–7.25 dB，分别来自错误的估计器和错误的帧长。
- **是不是原理性的**：不是。两半都是已知机制，拼在一起也没有产生已有文献推不出、又能改变选星对或接收机结构的定量结论。唯一勉强剩下的是一个 2×2 的小推导："估计偏置要 $\rho_s\ne\rho_I$ 才出现，回声最坏在 $\kappa=1$"，两者此消彼长。它不值得为它单独跑检验，而且离本项目主线（未知稀疏时延–多普勒信道上的编码接收）很远。

如果要把这条判断讲得更白，可以说「白话」。

## 若硬要做（不推荐）

- **必须有的对照臂**：锚点的最小特征值估计器（不能用 LS 当基线）；NR 子载波间隔（15/30 kHz）下的编码 OFDM + 逐子载波软信息。
- **最可能否掉它的一点**：上面两条一放进去，D1 和 D2 两条否决线大概率同时触发。我的算例已经替 D1 给出了方向性证据（等功率下没有偏置）。

另外两点说明：算例里 LS 的偏置是 +5.9 dB，卡片写的是 3.025（约 4.8 dB），差别可能来自归一化方式，不影响结论。所有文献只读到摘要或目录的，我已逐篇标出；Haimovich 那篇的发表年份没有核实，所以没写。

VERDICT I-20261122-l17: KILL — 偏置地板是把锚点的最小特征值估计器错算成 LS 的结果；"任何固定波形都绕不开"依赖错用的水声长帧多普勒，在 LEO 的 OFDM 参数下不成立；剩下的部分都是已知的特征对消器偏置和两径信道线性均衡结论。

Sources:
- [arXiv 2611.06719 abs](https://arxiv.org/abs/2611.06719) / [HTML](https://arxiv.org/html/2611.06719)
- [Widrow et al. 1982, signal cancellation](https://isl.stanford.edu/people/widrow/papers/j1982signalcancellation.pdf)
- [Haimovich et al., Training and signal cancellation in adaptive radar](https://researchwith.njit.edu/en/publications/training-and-signal-cancellation-in-adaptive-radar/)
- [Krolik & Swingler 1994](https://scholars.duke.edu/individual/pub687267)
- [Farrell profile (SMI desired-signal-absent covariance)](https://biomedicaloptics.spiedigitallibrary.org/profile/Jeffrey.Farrell-43358)
- [Fante & Vaccaro 2000](https://www.bohrium.com/paper-details/wideband-cancellation-of-interference-in-a-gps-receive-array/812458380244287488-2511)；[MITRE GPS crosscorrelation](https://www.mitre.org/news-insights/publication/effect-adaptive-array-processing-gps-signal-crosscorrelation)
- [Bottomley MLSE+IRC patent context](https://patents.google.com/patent/US5796788)
- [Surabhi et al., OTFS diversity](https://ar5iv.arxiv.org/html/1808.07747)
- [Jia et al. 2601.15557](https://arxiv.org/html/2601.15557v3)
- [Sun et al. 2607.25562](https://arxiv.org/html/2607.25562v1)
- [Jia et al. 2510.08824](https://arxiv.org/html/2510.08824v1)
