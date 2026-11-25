# 第 6 步异族查新与重要性初筛：g17 / g18 / g19 / g20（2026-11-22）

四条线都不建议作为漏斗原理级新卡进第 7 步 L2。只有线 A 在项目里有实际价值，但它应该交给 `11-21-data-pilot-fer` 当阶段 B 的候选前端，由你决定是否并入。

| 线 | 结论 | 固有重要性 | 查新 | 裁定 |
|---|---|---|---|---|
| A g17 | 有条件值得做，但不走漏斗 L2 | 中 | 部分被做过：算子与 SAGE 一致，只差应用场景 | 漏斗按 (2)；转主线任务由你定 |
| B g18 | 不值得做（省去 L2） | 低 | 部分被做过：三块都有先例，组合是常规拼法 | (2) |
| C g19 | 不值得单独跑 L2 | 作论文低；作前提纠偏低到中 | 卡 02 和 STAGEA2 读数已基本覆盖 | (2)，诊断公式留作笔记 |
| D g20 | 不值得做（省去 L2） | 低 | 部分被做过：逐帧按可靠度选置换已有先例 | (2) |

**核对范围。** 只读，没改任何文件。文献全部只读了摘要或检索摘录，没有读全文。下文标"卡引，未打开"的条目，我没有核实过原文。
- 4 张卡、初排意见、`FUNNEL.md` 和旧卡 02/c32 都读了原文。
- `twofft.py:51-66` 逐行代入核对过。
- g17 的探针代码不在仓库里（全仓库 `*.py` 搜不到 snowball），所以卡面的 FER 数字我无法复现。

---

## 线 A：`I-20261122-g17` 单帧叠加导频"雪球解卷积"

**一句话结论：有条件值得做。** 但它不是原理级新题。算子已被 SAGE/EM 一脉占据，漏斗内按 (2) 处理。工程价值是真的，应作为 `11-21-data-pilot-fer` 阶段 B 的候选前端，由你决定是否并入。

**固有重要性（抛开先例）：中。**
- **谁卡住了：** 单帧 SP-AFDM/OTFS 编码接收机在 ρ≤0.12 时，第 0 轮多普勒误差约 0.16 bin，只能退回 ρ=0.25（项目实测 4.95 dB）。
- **最朴素做法损失多少：** 白送真值的上限余量只有 1.51 [1.34, 1.67] dB。卡面主张的 0.8–1.1 dB 落在上限以内，增益是实打实的，但有封顶。
- **是不是原理：不是。** 这是本次查新最关键的发现：
  - 卡里的白化新息满足 $\mathbf{y}-\mathbf{T}\hat{\mathbf{x}} = (\mathbf{C}-v_d\mathbf{T}\mathbf{T}^H)\mathbf{u} = \gamma_{\rm rem}\mathbf{u}$。
  - 所以"Rao 得分"的第一项就是 $\langle \mathbf{U}_{\ell,\nu}\hat{\mathbf{x}},\ \mathbf{y}-\mathbf{T}\hat{\mathbf{x}}\rangle/\gamma$。白话说：先用已找到的径把发射波形做 LMMSE 软重构，扣掉这些径后得到残差，再拿候选径作用在软参考上的波形去和残差做互相关。这正是 SAGE/CLEAN 的逐径步骤。
  - 从 Fisher 恒等式也能看出来：边际似然的得分等于 EM 完全数据得分的条件期望。
  - 所谓"满秩扰动坍缩为秩一"，只是"一阶导数对 $g_m$ 是线性的"，并不是结构上的巧思。

**白话 + 类比。** 先用微弱的导频锁住最强的那条回声。用它把未知数据粗略还原出来，当作一份更亮的"参考信号"。从接收信号里扣掉已知回声，再拿这份参考去找下一条，越找越清楚。这就像嘈杂会场里先听清嗓门最大的人，把他的声音减掉，再去听下一个。射电天文的 CLEAN 和通信里的 SAGE 都是这么做的。卡里的新意不在算子，而在把它用在"单帧、低导频、第 0 轮、尚未译码"这个具体场景。

**最接近的工作（全部只读摘要或检索摘录）：**
1. Fleury et al., *Channel Parameter Estimation in Mobile Radio Environments Using the SAGE Algorithm*, IEEE JSAC 17(3), 1999（[记录](https://tuklas.up.edu.ph/Record/UP-99796217609333397)）。逐径 E 步把残差分给单条径，再做全局时延/多普勒相关搜索。本卡的单步与它相同，区别只在参考信号是软数据重构。
2. Shutin & Fleury, *Sparse Variational Bayesian SAGE*, IEEE TSP 2011, DOI 10.1109/TSP.2011.2140106（[PDF](https://vbn.aau.dk/files/61155739/Sparse_Variational_Bayesian_SAGE_Algorithm.pdf)）。SAGE 加稀疏先验，并且不需要已知径数。这条直接对应初排点名的"停止准则不能泄漏 P=8"。
3. *Joint Detection and Super-Resolution Estimation of Multipath Signal Parameters Using IARD*（[arXiv:1503.01898](https://arxiv.org/pdf/1503.01898)）。固定其他分量，对新分量做假设检验来决定是否加入，本质就是逐径 Rao/得分检验。本卡没有它的停止理论。
4. Mamandipoor, Ramasamy & Madhow, *Newtonized OMP*, IEEE TSP 2016（[arXiv:1509.01942](https://arxiv.org/abs/1509.01942)）。贪心加径、连续频率 Newton 精修、循环重扫和 CFAR 停止。本卡的"留一法全局重扫"就是这一套。
5. Zhu et al., *Generalized NOMP*（[arXiv:2307.00491](https://arxiv.org/pdf/2307.00491)）。用 Rao 检验做贪心线谱检测，与卡上"Rao 得分"的检测角色相同。
6. *A Monte-Carlo Implementation of the SAGE Algorithm for Joint Soft Multiuser and Channel Parameter Estimation*（[arXiv:0906.3816](https://arxiv.org/pdf/0906.3816)）。SAGE 内用软数据做参考，联合估时延和增益（没有估多普勒）。"软数据当参考逐径估"这一步已被做过。
7. de Carvalho & Slock, 高斯符号模型下半盲最大似然与 CRB（[EURECOM 82](https://www.eurecom.fr/en/publication/82)、[arXiv:1710.01605](https://www.arxiv.org/abs/1710.01605)）。高斯半盲边际似然本身是 1990 年代的经典工作。
8. Kanazawa et al., *Superimposed Pilot-Based OTFS – Will it Work?*（[arXiv:2501.15935](https://arxiv.org/html/2501.15935v2)）。编码 SP-OTFS 迭代接收，没有第 0 轮半盲逐径提取。应用层面的空白属实。

**查新判断：部分被做过。** 单步算子和贪心/循环框架与 SAGE + NOMP 一致。检索中没有找到"单帧 SP 双色散、ρ≈0.1、第 0 轮用高斯 LMMSE 软参考做全局连续多普勒逐径提取"的工作（摘要级检索）。

**为什么没人做：应用层空白，漏斗内按 (2)。** 空白的原因多半是 SP-AFDM 社区习惯用消息传递，没有借 SAGE 那一套。这不是"没人发现"的原理空白。照 `FUNNEL.md` 杀卡准则 4，它不能以原理级新颖性进 L2。

**真实系统里的影响。** 如果成立，导频比例可以从 0.25 降到约 0.10，同总能量下约赢 1 dB。这会改主线阶段 B 的前端选择。前提有三点存疑：
- 探针代码不在仓库，数字无法复核。
- 10 帧 0 错只能说明 FER < 26%（95% 上界）。
- 8 条瑞利径在 3.8 dB 下"漏径 0.0000"偏乐观，需要先查口径（是否按功率加权、弱径怎么计）。

**最强的反对意见。** 审稿人只要写出 $\mathbf{y}-\mathbf{T}\hat{\mathbf{x}}=\gamma\mathbf{u}$ 这一行，就能把"Rao 得分秩一分解"还原成 SAGE 加 LMMSE 软参考。

**如果进 L2（建议在主线任务里跑，而不是漏斗）。**
- 最便宜的致命一步：在 200 个未见帧上，ρ=0.10、SNR 3.6–4.6 dB，配对比较三条臂：
  - `base` 全 ρ 扫描取最优；
  - **朴素 SAGE/CLEAN 臂**：残差 y−T x̂（x̂ 取 LMMSE），每径做全局二维栅格搜索加抛物线插值，循环精修，用 CFAR 或 Rao 检验停止，不得用 P=8；
  - g17。
- 先看 SAGE 臂能否把穿越点压到 ≤ 4.15 dB。能的话，项目这一块就到手了，与新不新无关。如果 g17 ≈ SAGE，就撤掉"Rao"叙事。
- 补测等功率、不做逐帧单位范数归一的瑞利信道。
- 若要推到 ρ<0.10，同时加一条 g19 截断版检测器变体臂（见线 C）。

---

## 线 B：`I-20261122-g18` Zak-OTFS 收发异核解耦

**一句话结论：不值得做（省去 L2）。**

**固有重要性（抛开先例）：低。**
- **谁卡住了：** 临界采样 Zak-OTFS 做 64-QAM 时，用局域脉冲（Gaussian/MM）会被发射 Gram 矩阵的病态条件数拖累，用 Sinc 又有导频旁瓣问题。这是真实存在的取舍。
- **最朴素做法损失多少：** 直接发射正交脉冲（Sinc/GS），再给导频读出单独配一个低旁瓣接收窗，数字接收机本来就可以对同一份采样做任意多路滤波。这样就能拿走大部分增益。
- **是不是原理：不是。** 所谓"克罗内克奇异谱塌缩定律"，就是非正交 Gabor 系统 Gram 条件数差的老结论。[arXiv:2602.07350](https://arxiv.org/html/2602.07350v1) 做 Löwdin/IOTA 正交化，正是为了这个问题。卡面"击败白送真信道的 `MM_opt`"混了变量：比较双方的发射脉冲不同，赢的是发射条件数，不是信道估计。另外，这个赛道本身很窄：只有 Zak-OTFS、64-QAM，评估是未编码、168 符号的帧，与本项目 SP-AFDM 也不相干。

**白话 + 类比。** 拍照用锐利镜头保证画面清晰，找光源时另外套一块柔光滤镜，免得光晕干扰。两件事本来就可以分开做，不必用同一支镜头硬扛。卡里把这个常识包装成了"破解 Balian–Low 宿命"。

**最接近的工作（全部只读摘要或检索摘录）：**
1. Wei, Yuan, Li, Yuan & Ng, *Transmitter and Receiver Window Designs for OTFS*, IEEE TCOM 69(4), 2021（[arXiv:2010.13005](https://arxiv.org/pdf/2010.13005)）。发射端没有 CSI 时，在接收端用 Dolph–Chebyshev 窗提高有效信道稀疏度来帮信道估计。"接收端单独加窗服务信道估计"已被做过。
2. Wei et al., *Performance Analysis and Window Design for Channel Estimation of OTFS*（[arXiv:2101.11770](https://arxiv.org/abs/2101.11770)）。接收窗降低了信道估计误差地板。
3. *A Hybrid I/O Relation Estimation Scheme for Zak-OTFS Receivers*（[arXiv:2510.09215](https://arxiv.org/html/2510.09215v1)）。明确指出 Sinc 利于检测、Gaussian 利于估计；引用了 identical/matched/channel-matched 等不同接收滤波下的闭式 I/O 关系；读出区外用模型方法补齐，在 Veh-A 上比纯无模型方法赢约 3.5 dB。这与本卡的"散射盒跨核转换"高度重合。
4. Das, Jesbin & Chockalingam, *A Gaussian-Sinc Pulse Shaping Filter for Zak-OTFS*（[arXiv:2502.03904](https://arxiv.org/abs/2502.03904)）。已经在单一脉冲内调和检测与估计的取舍。
5. Matz, Schafhuber, Gröchenig, Hartmann & Hlawatsch, *Analysis, Optimization, and Implementation of Low-Interference Wireless Multicarrier Systems*, IEEE TWC 2007（[TU Wien](https://repositum.tuwien.at/handle/20.500.12708/168583)）。BFDM 用收发不同的双正交脉冲对，双色散信道下"收发异核"的老祖宗。
6. Schniter, *Low-Complexity Equalization of OFDM in Doubly Selective Channels*, IEEE TSP 2004（[摘录](https://typeset.io/pdf/low-complexity-equalization-of-ofdm-in-doubly-selective-mb10s396g5.pdf)）。只在接收端加窗，把信道矩阵压成带状。
7. Kokke et al., EUSIPCO 2023，只在接收端设计的失配脉压滤波：给定 SNR 损失，最大化旁瓣抑制（[TU Delft](https://repository.tudelft.nl/file/File_53643acc-0863-47bb-9bb5-3860313bc217)）。雷达单边失配切趾是标准做法。

**查新判断：部分被做过。** 正交发射、接收端为估计单独加窗、读出区外用子空间或模型重构，三块各有先例。检索中没有找到"Zak-OTFS 导频支路专用 MM 窗"这个确切组合，但这是常规组合。

**为什么没人做：(2)。** 组合太顺手，相邻工作（2510.09215、Wei 2021）已经各自做了大半。

**真实系统里的影响。** 对本项目没有影响。对 Zak-OTFS 社区，"发射保持正交、局域化交给接收端"这条准则已有 2510.09215 表述过。

**最强的反对意见。** 补上初排点名的 `gs_oracleH` 臂后，`asym_gs_mm` 多半接近 `gs_oracleH`，剩下的只是"GS 发射下更好的导频读出"，而这正是 2510.09215 已做的事。

**如果进 L2。** 同为 GS 发射，配对比较 `gs_oracleH`、`asym_gs_mm` 和 2510.09215 式混合估计器，用编码 64-QAM。若 `asym` 相对混合估计器的增益不到 1 dB，就淘汰。

---

## 线 C：`I-20261122-g19` BiG-AMP 冷启动反号（pit）

**一句话结论：不值得单独跑 L2。** 卡 02 加上 STAGEA2 读数自己的探索性检查已经实质覆盖了它，按 (2) 处理。诊断公式留作笔记。可以在下次 g17 或阶段 B 运行时，顺带加一条近乎零成本的检测器变体臂。

**固有重要性。**
- **作为论文：低。** 修法是一行代码，正是 FUNNEL 里反感的"初等小把戏"。
- **作为前提纠偏：低到中。** 它只改白送真值上限表里 ρ=0.05 那一格，原因有三：
  - STAGEA2 的冻结判读取 ρ≤0.20 的最小值，落在 0.10，不受影响。
  - STAGEA2 读数里已经写明"ρ=.05 那一列测到的是检测器的问题"。
  - 卡 02 已经写了"理想第 0 轮下最优导频比例 ≤ .05"。

**相对卡 02 的真实增量只有两点：**
1. **ldop 下 `fixed` 也会失败。** 不给真增益、只用导频 LS 增益时，`fixed` 在 3.6 dB 是 10/10 失败（卡面自报）。卡 02 只在给真增益的 `full` 下测过 `fixed`。所以"冻结增益"在 ρ=0.05 并不是完整的规避手段。
2. **给出了代数式。** 我对照 `twofft.py:51-66` 核对：`rh = h + vq*(Bb^H st − hb*sv*n*vx)`，其中 vq=1/(sv·‖x̂‖²)。第 0 拍 x̂ 等于导频，代入 v_d=0.5、v_p=0.5ρ/(1−ρ)，得到 vq·sv·n·vx = (1−ρ)/ρ，所以 r_h ≈ ((2ρ−1)/ρ)·h。式子成立。

**但卡面的理论定性有误（同意初排意见）。** 这一项是 BiG-AMP 标准的自校正项 (1 − Σν^x/Σ|x̂|²)，用的是本拍的 ν^s，不是"非因果的 Onsager 项"。只要 Σν^x > Σ|x̂|²，这个系数就会变负，不限于第一拍。这类有限规模下的发散，BiG-AMP 原文用自适应阻尼处理过，GAMP 在非零均值算子下也有 mean-removal 修法。还有一点：把系数截断到 [0,1] 后，第 0 拍的 r_h 正好等于导频 LS 解，与 `sj_causal` 的第 0 拍完全相同。所以一行截断很可能就打平 `sj_causal`。

**白话 + 类比。** 秤没归零就开始称重。开机第一拍，算法替一个根本不存在的"回声"做了扣除。导频越弱，扣得越狠，ρ=0.05 时把信道直接乘了 −18。把秤归零（系数截断）就好了。

**最接近的工作：**
1. Parker, Schniter & Cevher, *Bilinear Generalized AMP*, IEEE TSP 2014（[arXiv:1310.2632](https://arxiv.org/pdf/1310.2632)，摘要）。自适应阻尼一节指出有限维下可能发散，并按代价函数调阻尼。这就是初排点名的"Parker 步长拒绝"基线。
2. Vila, Schniter, Rangan, Krzakala & Zdeborová, *Adaptive Damping and Mean Removal for GAMP*, ICASSP 2015（[arXiv:1412.2005](https://arxiv.org/pdf/1412.2005)，摘要）。处理非零均值、病态算子导致的 GAMP 发散。导频正是 x̂ 的大确定性均值。
3. Parker & Schniter, P-BiG-AMP, IEEE JSTSP 2016, DOI 10.1109/jstsp.2016.2539123（卡引，未打开）。即 `twofft.py` 的原型。
4. Rangan, Schniter, Fletcher & Sarkar, AMP 在任意矩阵下的收敛, IEEE TIT 2019, DOI 10.1109/tit.2019.2913109（卡引，未打开）。
5. Ranasinghe et al., *Joint Channel, Data, and Radar Parameter Estimation for AFDM*（[arXiv:2405.16945](https://arxiv.org/pdf/2405.16945)，摘要）。AFDM 中的 PBiGaBP 联合估计，导频不低。
6. 项目内部：卡 `I-20261121-02`（已在 `full` 下定性 ρ=0.05 失败是检测器问题，L2 淘汰）；卡 `I-20261121-c32`（证伪"纯全局相位简并"，指出第 0 轮增益膨胀和 43% BER 毒化）；`STAGEA2_READOUT.md` 第 25–33 行。

**查新判断：已被覆盖。** 现象和定性被卡 02 和 STAGEA2 覆盖；修法属于 BiG-AMP/GAMP 已知的稳定化手段（阻尼、mean-removal、截断）。

**先例裁定：按 (2) 省去 L2。** 建议只向你报一句论文边界：

> STAGEA2 中 ρ=0.05 的"∞"来自 `twofft` 联合增益更新的自校正系数 (2ρ−1)/ρ 为负，既不是相位歧义，也不是信息不足；读数里"锁不住相位歧义"的说法应改正。

**真实系统里的影响。** 只有当某个可实现的前端（例如 g17）真要把 ρ 压到 0.10 以下时，检测器默认的 `gain_mode` 才需要换。上限可能从 3.45 dB 降到 3.1–3.3 dB，但这是卡面推测，没有测过。

**最强的反对意见。** 一行截断就能修好，而且卡 02 早已定性。

**如果顺带检验（≤ 0.2 核时，嵌进下一次运行）。** ρ∈{0.05, 0.08}，跑 ldop 和 delay 两条臂，每格 100 帧。配对比较 `joint`、`fixed`、截断到 [0,1]、前 5 拍 `fixed` 后切 `joint`、`sj_causal`。只要任一行级修法打平 `sj_causal`，就只留一行附注。

---

## 线 D：`I-20261122-g20` WHT 自同构合成

**一句话结论：不值得做（省去 L2）。**

**固有重要性（抛开先例）：低。**
- **谁卡住了：** 非均匀可靠度下，随机选自同构的 AED 效率差，这是真问题。
- **最朴素做法损失多少：** 在 N=128 的 BEC 上，高斯消元 ML 本身就是可部署的译码器；删余加 AWGN 下，OSD order-2/3 是现成的强基线。卡面"单次 SC 近 ML"的净收益不清楚。
- **是不是原理：不是。** 用 WHT 算 $\mathbb{F}_2^m$ 上的二元自相关是教科书内容。场景也站不住：
  - 5G 里被 URLLC 抢占的是 eMBB 的 LDPC 数据，不是控制信道的 Polar。
  - 把 CA-Polar 换成 RM 本身就是发射改动。
  - 这是项目外的编码选题，它要改变的那个部署决定实际上并不存在。

**白话 + 类比。** 折纸时有一些格子被涂脏了，换个对折方向，让上下两页各自分到能消化的脏格数量，再对折。卡里的办法是每帧看一眼哪些格子脏，用一次快速变换算出所有对折方向各会碰撞多少脏格，挑最均衡的那个方向。"看本帧可靠度、当场挑置换"这个思路，2018 年已有人做过。

**最接近的工作（全部只读摘要或检索摘录）：**
1. Hashemi, Doan, Mondelli & Gross, *Decoding Reed–Muller and Polar Codes by Successive Factor Graph Permutations*, ISTC 2018（[arXiv:1807.03912](https://arxiv.org/abs/1807.03912)）。逐层、当场按 LLR 可靠度 Σ|α_i| 选置换（只在循环移位里选），单次 SC 解码。这是最直接的先例；本卡的差别只在候选集（全部 GL 方向对比循环移位）和选择准则（容量裕度配平对比可靠度和）。
2. Doan, Hashemi, Mondelli & Gross, 把逐层置换用到 RM 码的递归列表译码（[arXiv:2109.02122](https://arxiv.org/abs/2109.02122)）。
3. Ivanov & Urbanke, *Permutation-based Decoding of Reed–Muller Codes in Binary Erasure Channel*, ISIT 2019, DOI 10.1109/ISIT.2019.8849214（[EPFL](https://infoscience.epfl.ch/record/271631)）。BEC 上 Plotkin 递归列表译码加置换，接近 MAP。
4. *Enhanced Recursive Reed–Muller Erasure Decoding*（[arXiv:1601.06908](https://ar5iv.arxiv.org/html/1601.06908)）。Plotkin 递归加双传递置换群，不做高斯消元，复杂度低于平方，接近容量。直接覆盖卡上的 BEC 部分。
5. Kamenev, Kameneva, Kurmaev & Maevskiy, *A New Permutation Decoding Method for Reed–Muller Codes*（[arXiv:1901.04433](https://www.arxiv.org/pdf/1901.04433)）。
6. Geiselhart et al., AED, IEEE TCOM 2021（[arXiv:2012.07635](https://arxiv.org/abs/2012.07635)）；Qu, Tasbihi & Kschischang（[arXiv:2409.03700](https://arxiv.org/html/2409.03700v1)）。都是与信道无关的随机采样基线。

**查新判断：部分被做过。** "逐帧按接收可靠度当场选置换，再做单次 SC"已有 Hashemi SP；BEC 上的递归置换译码也有。本卡的增量（扩大候选集、换选择准则、用 WHT 一次评估全部方向）属于对 SP 的渐进改进。

**为什么没人做：(2)。** 卡自己还有记账硬伤（初排已点出）：
- BEC 上 `Pol-SCL8` 优于 `Oracle-ML-Pol` 不可能出现，说明 ML 平局记为失败，而 SC/SCL 平局靠猜。
- 40% 删余下 8 dB 为 0/150、12 dB 反成 0.100，曲线不单调，需要先排错。

**真实系统里的影响。** 不改任何现实中的部署决定（理由同上）。

**最强的反对意见。** Hashemi SP 已经在逐帧、逐层按 LLR 选置换；N=128 的现实基线是 OSD 或高斯消元 ML，不是随机 AED。

**如果进 L2。** 统一平局记账后，同算力配对比较：把 Hashemi SP 准则扩展到全部 GL 候选、OSD-2、AED-8、WHT-Bal-1/8。若本卡相对"扩展版 SP"的增益不到 0.5 dB，就淘汰。

---

**跨卡提醒。** g19 只在 g17 要把 ρ 推到 0.10 以下时才有用。所以与其单独给 g19 跑 L2，不如把截断版检测器作为 g17 或阶段 B 运行里的一条变体臂。

需要的话说「白话」，我把任一条线的结论翻成大白话版。
