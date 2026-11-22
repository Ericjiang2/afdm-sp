# Claude opus 查新初筛（第 6 步：l30）——本地第 4 轮，2026-11-22

模型：claude opus（`claude -p --no-session-persistence --model opus`；Gemini 出的卡本应交 gpt-6.2-sol，Codex 无额度后改派，属跨家族）。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s10b-claude.prompt`。以下为原文。

# 线 A（l30）：接收端按符号做 GF(2) 换基再交给 OSD

**先说明检索条件**：两个指定 skill 的脚本没跑成。本机 Python 调用和写 `/tmp` 都被权限拦下了，所以 paper-search 的多源检索和 scoop-check 的分步落盘都没执行。替代做法是：用网页检索做了 14 组查询，再按 scoop-check 的四个维度（问题设定、核心机制、关键洞见、应用领域）人工判重叠。下面每篇都注明读了全文还是只看了摘要。我没有修改任何文件。

**三句判断**：
- **谁真卡住了**：只有一种接收机——单个短码字跨满秩数（层数）的多天线，在过载或强相关信道下做 BICM 加 OSD。但标准里的秩自适应（接收端上报能撑几层，3GPP TS 38.214 里的秩指示 RI 上报）本来就是为了不在这种信道上跑满秩。
- **最朴素做法亏多少**：最朴素的做法是降一层、换高一阶调制，或者在每个信道块用一个固定的换基矩阵（二进制 integer-forcing 的做法）。卡片两个都没比，所以真实损失是多少未知。
- **是不是原理**："解得准的是和，不是各个分量"是 integer-forcing / 物理层网络编码已有的原理。本卡新增的只是一个结构观察：OSD 的信息集不必是坐标比特，可以是每个符号各自的一组线性无关异或。

---

## 一句话结论

**不值得做（省去 L2）。** 唯一能翻案的是下面"最便宜一步检验"里那个约 0.1 核时的同速率对照。我预期它过不了，但它便宜到可以在 Eric 想留这张卡时跑一次。

## 固有重要性（抛开先例）：中

- **为什么不是低**：问题真实存在（短包多天线的近最大似然译码），结构也干净。OSD 的选基从"比特置换"推广到"每个符号块各自的 GL_m(F₂) 可逆变换"，代价只是把 G 的对应列右乘 W_t，发射端零改动。
- **为什么到不了高**：
  - 增益只出现在过载或强相关、单码字、满秩数的工作点上，而标准用秩自适应回避了这个点。
  - 适用范围被卡在 m ≤ 12：4×4 16-QAM 是 m = 16，每个符号要枚举 65536 个点。
  - "拟阵贪心全局最优"优化的是"各新坐标边缘熵之和"这个代理量。OSD 真正需要的是"信息集里错误重量 ≤ 阶数"的概率，这个取决于联合错误分布，代理量不等于它。拟阵贪心本身是教科书定理（Rado–Edmonds）。

## 白话 + 类比

- **白话**：多天线信号互相叠加时，接收机常常很确定"比特 1 和比特 3 相同还是相反"，却说不准各自是几。BICM 只许交"每一位单独多大把握"，这条"和"的线索就丢了。本卡的做法是：每个符号挑出 8 个最有把握、彼此线性无关的异或组合当新坐标，并告诉译码器换成这套坐标去解。码是线性的，换坐标等于把生成矩阵对应的列乘一个 8×8 二元矩阵。
- **类比**：你不知道两枚硬币各是正是反，但确定"它们一正一反"。与其交两张都写"不确定"的答卷，不如交一张"它们不同"（几乎确定）加一张"第一枚是正"（不确定）。
- **剥掉术语以后**：剩下的是"解你有把握的和，而不是分量"。这在网络信息论里是 2006–2010 年就有的常识（物理层网络编码、integer-forcing）。新的只有一点：OSD 允许每个符号用不同的组合，而且整段数据可以只是一个交织后的码字。

## 最接近的工作

1. **Zhan, Nazer, Erez, Gastpar, "Integer-Forcing Linear Receivers," IEEE TIT 2014**（[arXiv:1003.5966](https://arxiv.org/abs/1003.5966)）【读摘要】
   - 做了什么：接收端解码字的整数线性组合，组合矩阵 A 要求满秩、按信道选。洞见完全相同："组合比单路可靠"。
   - 差在哪：每根天线是同一个码的独立码字；A 按整个块固定，只看 H。
2. **Hong & Caire 一线，"Low-Complexity Integer-Forcing Methods for Block Fading MIMO MAC"**（[arXiv:1711.07977](https://arxiv.org/abs/1711.07977)）【读了全文第 I–IV 节原文，后半只看到模型摘要】
   - 做了什么：二进制 LDPC 加模 2 组合，用 BP 译码。原文写明 "the resulting integer linear transformation A must be the same for all blocks"。
   - 差在哪：A 只取决于 H，不随接收样本 y_t 变；不用 OSD；每路是独立码字。
3. **Chae et al., "Multilevel Coding Scheme for Integer-Forcing MIMO Receivers With Binary Codes," IEEE TWC 2017**（[DOI 10.1109/TWC.2017.2711002](https://unpaywall.org/10.1109%2FTWC.2017.2711002)）【只看了摘要】
   - 做了什么：二进制线性码配自然映射、多级译码，把 integer-forcing 落到 GF(2)。
   - 差在哪：要求发射端多级编码，属于改发射端。
4. **Allahkaram, Monteiro, Chatzigeorgiou, "Symbol-Level Noise-Guessing Decoding with Antenna Sorting for URLLC Massive MIMO"**（[arXiv:2305.13113](https://arxiv.org/abs/2305.13113)）【读了全文第 I–V 节】
   - 做了什么：一个码字跨所有天线（原文 "one MIMO burst … contains one codeword only"），在符号级排错误图样。
   - 差在哪：ZF 后逐路独立处理，不利用跨天线相关；只考虑 Nr ≫ Nt；用的是高码率随机码。
5. **Chatzigeorgiou & Monteiro, "Symbol-Level GRAND for High-Order Modulation"**（[arXiv:2207.07748](https://arxiv.org/abs/2207.07748)），以及 **An & Médard, ORBGRAND 免软解映射**（[arXiv:2207.11991](https://arxiv.org/abs/2207.11991)）【读摘要】
   - 做了什么：按符号似然或符号可靠度排猜测顺序。
   - 差在哪：单天线；没有换基这一步。
6. **非二进制 LDPC 的 FFT-BP**（Davey–MacKay 1998；Barnault–Declercq 2003；[arXiv:1008.4370](https://arxiv.org/abs/1008.4370)），以及非二进制 LDPC 与 MIMO 联合符号消息（[arXiv:1310.4347](https://arxiv.org/abs/1310.4347)、[arXiv:1211.5067](https://arxiv.org/abs/1211.5067)）【读摘要】
   - 做了什么：对符号后验做 Walsh–Hadamard 变换，得到所有奇偶泛函的偏置，正是本卡的 WHT 这一步；联合方案保留整份符号后验。
   - 差在哪：要求发射端用非二进制码。
7. **Yue et al., "NOMA Joint Decoding based on SO-OSD"**（[arXiv:2110.15010](https://arxiv.org/abs/2110.15010)）【读摘要】
   - 做了什么：短 BCH 加软输出 OSD 做多用户联合译码。
   - 差在哪：输入仍是坐标比特的 LLR。
8. **Agrell & Alvarado，BICM 容量的 Hadamard 分析**（[arXiv:1001.4521](https://arxiv.org/abs/1001.4521)、[arXiv:1202.6404](https://arxiv.org/abs/1202.6404)）【读摘要】
   - 做了什么：用 WHT 分析标号。
   - 差在哪：只用于发射端的离线分析。

**另外两点核查**：
- 卡片引用的 `arXiv:2609.33830`（SOGRAND-AM）检索可见，但作者名单没核到；`arXiv:2605.02296` 可见；`arXiv:2608.04068` 没核到。
- 格基约减辅助检测这条：QPSK 下幺模矩阵 T 模 2 后仍在 GL_m(F₂) 里，所以它天然给出一个"按块固定、只看 H"的 GF(2) 基。这一点是我的推导，没找到明写它的文献。

## 查新判断：部分被做过（scoop-check 口径约 Level 3，中等重叠）

- **已有的部分**：
  - "解组合而不是分量，组合矩阵要满秩、按可靠度选"：integer-forcing、物理层网络编码、二进制 integer-forcing。
  - "符号后验做 WHT 得到奇偶可靠度"：非二进制 LDPC 的 FFT-BP。
  - 贪心选基：教科书。
- **没找到先例的部分**：在单个交织码字里，让 OSD/GRAND 的信息集用每个符号各自的、由 (y_t, H_t) 决定的 GF(2) 基。integer-forcing 做不到这一点，因为它要求组合本身仍是码字，所以 A 必须全块一致；OSD 直接操作 G，没有这个约束。这是一个干净但小的差别。
- **差别陈述**：二进制 integer-forcing 要求每根天线发同码的独立码字，并只按 H 固定一个块级组合矩阵；本卡保留单个交织码字，让 OSD 的信息集逐符号按 (y_t, H_t) 换基。代价是它只适用于 OSD/GRAND 这类直接操作 G 的短码译码器。
- **"从未意识到"是夸大**：卡片说"接收端可在线做 GL_m 局部基极化，社区从未意识到"，这个说法过头了。

## 为什么没人做：(2) 发现了但不重要

- **秩自适应**：LTE/NR 的 RI 上报、Wi-Fi 的空间流数选择，本来就是为了避免在病态（过载或强相关）信道上跑满秩。卡片三个工况里有两个（4×2 过载、ρ = 0.85 的 4×4）正好落在系统会主动降秩的区域，违反 FUNNEL「真实默认参数底线」。
- **短包场景用不到空间复用**：URLLC 和控制信道追求可靠性，通常走低秩或单层分集。PDCCH 是单端口发送，配 Polar 码。"短码 + OSD + 空间复用"不是一个现成的工作点。这一条对 URLLC 的部分是工程惯例判断，我没有逐条核标准原文。
- **换基没有落脚处**：标准里的译码器是 BP 和 SCL，不是 OSD，按符号换基接不进去。
- **iid 4×4 这个唯一"正常秩"的点**：BLER 从 14/120 降到 8/120，按两比例检验 z ≈ 1.34、p ≈ 0.18，不显著（卡片没给配对结果）。而且 OSD-1 反而变差。

## 真实系统里的影响

- **最多能改变什么决定**："这个信道撑不撑得起再多一层"的秩选择门限。
- **量级未知**：
  - 卡片的数字都是单个 SNR 点上的 BLER，没有 10⁻² BLER 处的 dB 位移。
  - 用的是理想信道状态信息，每点 120 帧。
  - 没和"降一层 + 高一阶调制、同 8 比特/信道使用"比。
- **前提核对**：
  - 41.7% → 17.5% 的前提是过载 4×2 QPSK。同速率的现实替代是 2×2 秩 2 16-QAM，卡片没测。
  - 回收 80–92% 的互信息损失这个数字也在过载点上。
  - 与联合 ML 的 0.8% 相比，剩余差距仍然很大，说明候选生成仍是瓶颈。

## 关于你点名的四个问题

**(b) 基线漏了哪些**：
1. 秩自适应臂：同总能量、同速率，取各秩数中最好的 BICM。这是最关键的一条。
2. 块级固定 GF(2) 基：LLL 模 2，或对整块平均的 WHT。用来量"按符号自适应"本身值多少。
3. 符号级 OSD：信息集按符号选，测试图样把整个符号翻成次优星座点，天然覆盖"b1 和 b3 一起翻"。
4. 精确 APP 与 max-log 的核对，以及等复杂度下的更高阶 OSD 或多信息集 OSD。

**(c) 新比特之间的相关会不会让 OSD 失效**：会。OSD 的信息集选择和测试图样排序都假设各位置独立出错。同一符号里的新坐标在出错上是相关的：首个泛函错了，其余也容易错。联合重打分只修正最后挑哪个候选，修不了候选是怎么生成的；卡片在 OSD-1 上变差就是这个症状。卡片提的"链式条件 LLR"条件在硬判决上，可 OSD 一旦翻转前面的位，后面的条件可靠度就不再成立，这个补法不自洽。

**(d) 这个工作点有没有人在乎**：短包近最大似然译码有人做，但几乎都在单天线、或 Nr ≫ Nt 的大规模 MIMO（如上面第 4 篇）里。过载或强相关下的单码字空间复用短包，我没找到真实系统需求的证据。

## 最强的反对意见

"组合比分量可靠"是 integer-forcing 已有的洞见；增益只出现在秩自适应本来就会回避的工作点上；剩下的"按符号自适应 + 单码字 OSD"是一个窄的增量，而且没比同速率的降秩方案。

## 如果要做，最便宜的一步检验

约 0.1 核时，同总能量、同 8 比特/信道使用、真实导频估计，每点 ≥ 1000 帧配对，在 ρ = 0.85 的 4×4 和 iid 4×4 上比四臂：

| 臂 | 内容 |
|---|---|
| (a) | 秩 4 QPSK 和秩 2 16-QAM 中较好的那个，BICM + OSD-2 |
| (b) | 秩 4 QPSK，WHT 换基 + OSD-2 |
| (c) | 秩 4 QPSK，按块固定基（LLL 模 2）+ OSD-2 |
| (d) | 秩 4 QPSK，符号级 OSD-2 |

**否决线**（在 10⁻² BLER 处，任一条成立就淘汰）：
- (b) 净赢 (a) 不到 1 dB。
- (c) 收回了 (b) 增益的 80% 以上。这时它等于"二进制 integer-forcing 的基搬进 OSD"。
- (d) 打平或胜过 (b)。

---

需要的话说「白话」，我把上面的重要性判断换成不带术语的版本。

Sources:
- [Integer-Forcing Linear Receivers (arXiv:1003.5966)](https://arxiv.org/abs/1003.5966)
- [Low-Complexity Integer-Forcing Methods for Block Fading MIMO MAC (arXiv:1711.07977)](https://arxiv.org/abs/1711.07977)
- [Multilevel Coding Scheme for IF MIMO Receivers With Binary Codes (TWC 2017)](https://unpaywall.org/10.1109%2FTWC.2017.2711002)
- [Symbol-Level Noise-Guessing Decoding with Antenna Sorting for URLLC mMIMO (arXiv:2305.13113)](https://arxiv.org/abs/2305.13113)
- [Symbol-Level GRAND for High-Order Modulation (arXiv:2207.07748)](https://arxiv.org/abs/2207.07748)
- [Soft decoding without soft demapping with ORBGRAND (arXiv:2207.11991)](https://arxiv.org/abs/2207.11991)
- [Fourier Domain Decoding of Non-Binary LDPC (arXiv:1008.4370)](https://arxiv.org/abs/1008.4370)
- [M-ary Detection and q-ary Decoding in Large-Scale MIMO (arXiv:1310.4347)](https://arxiv.org/abs/1310.4347)
- [Approaching the Capacity of Large-Scale MIMO via NB-LDPC (arXiv:1211.5067)](https://arxiv.org/abs/1211.5067)
- [NOMA Joint Decoding based on SO-OSD (arXiv:2110.15010)](https://arxiv.org/abs/2110.15010)
- [On the BICM Capacity (arXiv:1001.4521)](https://arxiv.org/abs/1001.4521)
- [Signal Shaping for BICM at Low SNR (arXiv:1202.6404)](https://arxiv.org/abs/1202.6404)
- [Soft-Output GRAND-Aided Macrosymbol (arXiv:2609.33830)](https://arxiv.org/pdf/2609.33830)
- [Semantic Ordered Statistics Decoding (arXiv:2605.02296)](https://arxiv.org/pdf/2605.02296)
