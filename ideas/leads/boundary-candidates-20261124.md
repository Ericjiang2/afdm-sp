# 分界账候选线索核查（2026-11-24，Claude Code 主会话，非 runner）

来源：第 7 轮 lit-reader 表 (b)（`runs.md` 第 603 行）与第 8 轮第 3 个 lit-reader（`runs.md` 第 639 行，即 r8 草稿 8）。目的：在下次开放分界账前，先查清这两处"文献结论打架"是否已有统一解释。只做文献核查（摘要与题录级，未读全文），未跑探针，未建卡。

## 线索 1：叠加导频对时分复用导频，胜负随衰落速度翻转

- 公共痛点：**过**。不止 Keykhosravi 一篇（arXiv:2503.17565，FTN 双选信道，衰落率约 1e-3 时叠加导频胜复用导频）。
- 先例：**翻转边界本身已有人系统刻画**。
  - Coldrey & Bohlin，"Training-Based MIMO Systems—Part I: Performance Comparison"，IEEE TSP 2007：用可达速率下界比较叠加导频与常规导频，结论为叠加导频在接收天线多或相干时间短时占优，相干长度超过几个符号时退化为常规方案。Part II 指出数据辅助重估对叠加导频的收益更大。
  - Asyhari & ten Brink，"Orthogonal or Superimposed Pilots? A Rate-Efficient Channel Estimation Strategy for Stationary MIMO Fading Channels"，IEEE TWC 16(5), 2017, DOI 10.1109/TWC.2017.2665467（ISWCS 2014 会议版）：在时间选择、带限平稳衰落下按可达速率给出两者随信噪比、衰落速度、发射天线数的胜负区域，并指出"高信噪比慢衰落选正交、反之选叠加"的通行说法并不普遍成立。
- 判读：作为纯分界题已被占。唯一可能的残留是"双色散（时延 + 多普勒）、编码迭代、数据辅助重估"下边界是否移动——那等于把 Asyhari–ten Brink 的判据直套到双色散。**最便宜的致命检验**：把多普勒扩展当作衰落带宽代入其判据，看能否预言 Keykhosravi 在 4e-3 / 4e-4 两点的胜负；能预言就判 `(2)` 淘汰。
- 顺带：现稿用叠加导频，Coldrey–Bohlin 与 Asyhari–ten Brink 可作为"为什么选叠加导频"的引文支撑（交论文自查，不建卡）。

## 线索 2：多水听器 turbo 均衡，"逐通道估信道 + 合并"对"直接多通道自适应"排序矛盾

- 公共痛点：**过**（Choi–Riedl–Singer–Preisig，JOE 2011；Yang & Zheng，JOE 2016，DOI 10.1109/JOE.2015.2398731，报告信道估计式胜；同组 OCEANS 2016 单通道对比）。
- 先例：**差异的来源已有分析**。
  - Choi 等 2011 已在理论上分析两类 turbo 均衡在信道估计误差与自适应滤波误差下的行为。
  - Blair（MIT/WHOI 学位论文，Preisig 指导，"Analysis of and techniques for adaptive equalization for underwater acoustic communication"）专门研究两类方法性能差异的成因（含真实与估计信道阶数之差、超额均方误差分解）。
  - Pelekanakis & Chitre（2015）：快变信道下信道估计式 DFE 系数收敛更快。
- 判读：机理（参数数目与估计误差放大）已有分析；"随通道数与训练长度的交叉律"是否已有闭式没有查到全文确认，但 Blair 论文最可能已覆盖。另属多天线接收（`g` 的范围），且是单载波水声场景，离 AFDM 主线较远。**建议丢弃**，除非下次有人读 Blair 论文全文后确认没有交叉律。

## 结论

两条都过了公共痛点门，但都已被先例基本占住；目前**没有一张现成可用的分界账卡**。下次开放分界账时，不要从这两条起步。

参考：
- https://research.chalmers.se/en/publication/19026
- https://pureportal.coventry.ac.uk/en/publications/orthogonal-or-superimposed-pilots-a-rate-efficient-channel-estima/
- https://arxiv.org/abs/2503.17565
- https://researchconnect.stonybrook.edu/en/publications/adaptive-linear-turbo-equalization-over-doubly-selective-channels/
- https://dspace.mit.edu/handle/1721.1/68436
- https://arl.nus.edu.sg/wp-content/publications/PelekanakisChitre2015RobustEqualization.pdf
