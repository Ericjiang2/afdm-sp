# 查新与"为什么没人做"审查：线 A（离群/门限）与线 B（共同多普勒）

- 评审：Gemini 4 Neon（xhigh），agy 会话 `9baf3742-1e18-4936-9630-96a955826889`，2026-11-21；提示 `ideas/prompts/novelty-importance.md`（协议第 7 步）。
- 用到的 skill：`paper-search`（OpenAlex / arXiv / Crossref / Semantic Scholar；DBLP 报错，S2 一次 429）、`scoop-check`，另加网页检索；全文读了 Graff & Humphreys 2024、Wang 2026、Xiong & Liu 2023、Huang 2024、Wu、Mishra、Zheng、Hu & Fu、Cao 2024；其余标为只看摘要。

## 结论（Gemini）
- 线 A：不值得做；部分被做过（ZZB 代替 CRB 做导频/功率分配已有 Graff 2024、Sun TCOM 2023、Xiong 2023；SP-OTFS 用 EXIT 定 ρ 有 Liu TCOM 2024）；属 (2) 发现了但不重要：ρ 是一维旋钮，扫一遍、多留 5% 只亏 0.18 dB，真实系统用前导码绕开第 0 轮捕获。
- 线 B：不值得做（方法层）；已被做过（Li JOE 2008、Berger TSP 2010、Yang JOE 2026 的"先公共重采样、再残余稀疏估计"）；但 c25 的信道律问题必须修，否则水声审稿人会质疑整个第 0 轮多普勒难题。

## Claude 的核对（对照项目文件）
1. 成立：卡 01 第 25 行把"现有最优 .25（4.95 dB）对理想第 0 轮 .10（3.45 dB）差 1.5 dB"写成门限视角能改变的量。1.51 dB 是 STAGEA2 的"第 0 轮给真信道"上界，不是换一条选 ρ 的规则能拿到的；只换规则，对现有接收机是 0 dB。
2. 成立：STAGEA3 第 16 行确有"同样平均误差下，高斯误差比导频真实误差伤害大"（.157 对 .160 bin，6.36 dB 对 ∞）。
3. 成立：c25 第 45 行已更正为 fs = 16 kHz、1 bin ≈ 1.95 m/s。
4. 说过头：Gemini 称 c29"在 ρ = .10、5 dB 下最终误帧率降到 0/100"，据此说线 A 的悬崖"很大程度上是仿真产物"。`l2/out6/c29_summary.json`：两臂都给真时延，ρ = .10、s = 0 时逐径最终失败 1/100、共同 0/100；共同多普勒救回的是第 0 轮（失败 90 → 27）和 F0 两轮（13 → 0），不是最终误帧率。"不给真时延、按物理信道律、完整接收机"下悬崖是否还在，没测过，正是 Gemini 自己给的最便宜检验。
5. 未核：只看摘要的引用（Liu TCOM 2024、Sun TCOM 2023、Berger 2010 的方法细节等）没有逐篇核原文；Berger 2010、Li 2008、Qarabaqi 2013、Tu 2012 是水声领域熟知的文献，方向描述与 Claude 的了解一致。

## 按协议第 7 步的处理
- 线 A（01、c35、c48、c73；c60 早已淘汰）：(2) → 停放。可留作现稿里解释低 ρ 失效的诊断材料。
- 线 B 方法（c29）：(2)，已被做过 → 停放，作为 c25 检验里的对照臂保留。
- c25（前提）：保留在"前提检查：需要你定"；Gemini 的最便宜检验并入 c25 的下一步。

---

## Gemini 原文
> **检索说明**：本次查新按要求使用 `paper-search`（经 `/Users/guoyikun/.local/share/researchstudio/venv/bin/python` 检索 OpenAlex、arXiv、Crossref、Semantic Scholar，共去重召回线 A 151 篇、线 B 162 篇及水声叠加导频补充 56 篇；其中 DBLP 接口返回空 JSON 报错，Semantic Scholar 在线 A 首次检索触发 HTTP 429，已由 OpenAlex/arXiv/Crossref 与网页检索补齐）并按 `scoop-check` 四轴框架对高重叠候选拉取全文核对；同时核查了项目内 [STAGEA_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)、[STAGEA2_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)、[STAGEA3_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)、[STAGEA4_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md) 与 [afdm_env.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/afdm_env.py#L285-L360)，未修改任何项目文件。

---

## 线 A：低导频失败是第 0 轮的"离群/门限"问题，不是精度问题

涉及卡片：[I-20261121-01.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-01.md)、[I-20261121-c35.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c35.md)、[I-20261121-c48.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c48.md)、[I-20261121-c60.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c60.md)、[I-20261121-c73.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c73.md)。

- **一句话结论**：**不值得做**（作为独立研究主线不值得做；谁真卡住了：只在"用无编码线性 SINR 闭式公式硬定叠加导频比例 ρ、且不做实测扫描"的论文写法里存在偏差；最朴素替代——单参数扫描 ρ 并向安全侧多留 5% 导频余量——在项目实测里只损失 0.18 dB，且真实水声系统靠前导码直接绕开该难题；所谓 ZZB 门限原理在通信/雷达/GNSS 领域已被广泛使用，并没有提供能撬动 1.5 dB 上界的新结构。最多降级为现有论文里解释低 ρ 失效的半页诊断注记）。

- **白话 + 一个类比**：
  剥掉"Ziv–Zakai 界""局部 CRB""离群重尾"这些术语，这条线说的其实是一句工程常识：**给叠加导频分太少功率时，第 0 轮找弱径会偶尔彻底找歪（跳到假峰），一旦歪了后面迭代救不回来，所以不能只按"平均估计方差"算最小导频比例，要留够"不找歪"的门槛**。就像给登山队配头灯电池：如果只算"平均亮度降 10% 能多背半斤干粮"，最优方案会把灯调得很暗；但真进夜路，亮度跌破某个阈值就会踩空摔下悬崖，所以理性做法根本不是去解一个复杂的悬崖概率积分来省那半斤干粮，而是直接把头灯开在安全余量之上（或者进山前先打一发照明弹——对应工程里的前导码）。卡 [c48](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c48.md)、[c60](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c60.md)、[c73](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c73.md) 则是围绕"头灯不够亮时怎么办"做的几个常规小修补：把刻度画细一点、把不可能的方向遮掉（已淘汰）、找两个人同时看取通过验算的。

- **最接近的工作**：
  1. **A. M. Graff & T. E. Humphreys (2024, IEEE TWC / [arXiv:2403.12905](https://arxiv.org/abs/2403.12905)) — *Ziv-Zakai-Optimal OFDM Resource Allocation for Time-of-Arrival Estimation*（读了全文）**：明确指出局部 CRB 忽略低 SNR 下自相关旁瓣引起的门限跳变，证明以全局 ZZB 为目标优化 OFDM 导频功率与位置分配是凸问题并在 SDR 上实测验证；差在它优化的是正交 OFDM 定位导频的频域分布，不是叠加导频的导频/数据总功率比 ρ 与编码迭代接收机。
  2. **J. Sun, S. Ma, G. Xu, S. Li (IEEE TCOM, vol. 71, no. 6, pp. 3752–3762, 2023, [doi:10.1109/TCOMM.2023.3265113](https://doi.org/10.1109/TCOMM.2023.3265113)) — *Trade-Off Between Positioning and Communication for Millimeter Wave Systems With Ziv-Zakai Bound*（只看了摘要及 Graff 2024 文献 [23] 引述）**：直接用 ZZB 约束替代 CRB，优化定位（导频）与通信数据之间的总功率分配以最大化数据速率；差在它是毫米波通信-定位一体化（IPAC）权衡，不涉及叠加导频的数据干扰耦合与编码迭代译码回路。
  3. **R. Wang, C. Pan, H. Ren, H. Wu, J. Wang (2026, [arXiv:2603.09293](https://arxiv.org/abs/2603.09293)) — *Tensor Train Decomposition-based Channel Estimation for MIMO-AFDM Systems with Fractional Delay and Doppler*（读了全文）**：已经在分数时延与分数多普勒 MIMO-AFDM 信道估计里推导了全局 ZZB 并对比 CRB 刻画低 SNR 门限崩溃；差在它采用分离的时-仿射频域嵌入导频（T-AF），无叠加数据干扰，也不反过来优化 ρ。
  4. **Y. Xiong & F. Liu (IEEE SPL 2023 / [arXiv:2310.02963](https://arxiv.org/abs/2310.02963)，读了全文)** 及 **J. Shi, Y. Xiong, F. Liu et al. (GLOBECOM 2025, [doi:10.1109/globecom59602.2025.11432465](https://doi.org/10.1109/globecom59602.2025.11432465)，只看了摘要)**：用全局 ZZB 优化测距波形与多普勒模糊分辨率，核心结论就是低 SNR 下应优先保检测/抗旁瓣离群而非追求 CRB 分辨率；差在对象是雷达/测距波形设计，而非叠加导频通信接收机。
  5. **Y. Liu, Y. L. Guan, D. González G. (IEEE TCOM, vol. 72, no. 1, pp. 601–617, Jan. 2024，只看了摘要与 Huang 2024 [36] 引述)** 及 **F. Huang et al. (IEEE TVT 2024 / [arXiv:2309.08177](https://arxiv.org/abs/2309.08177)，读了全文)**、**Y. Wu et al. ([arXiv:2202.10035](https://arxiv.org/abs/2202.10035)，读了全文)**、**H. B. Mishra et al. (IEEE TWC 2022 / [arXiv:2010.15066](https://arxiv.org/abs/2010.15066)，读了全文)**、**K. Zheng et al. (IEEE TVT 2024 / [arXiv:2404.10232](https://arxiv.org/abs/2404.10232)，读了全文)**：这是最直接的 SP-OTFS / SP-AFDM 同行。全文核实表明它们确实都用第一轮有效 SINR（或线性的 MMSE 迭代平衡点，如 Hu & Fu [arXiv:2608.13809](https://arxiv.org/abs/2608.13809)，读了全文）求最优 ρ，其中 Liu 等 TCOM 2024 结合了 EXIT 图分析编码 Turbo 收敛门限；差在它们采用线性 BEM 或整数网格，不存在连续多普勒非线性搜峰的 ZZB 旁瓣跳变。
  6. **J.-H. Won, B. Eissfeller et al. (IEEE TAES 2012, [doi:10.1109/taes.2012.6237591](https://doi.org/10.1109/taes.2012.6237591)，只看了摘要)** 与 **A. Serbes & K. A. Qaraqe (IEEE TAES 2022, [doi:10.1109/TAES.2022.3166063](https://doi.org/10.1109/TAES.2022.3166063)，只看了摘要)**：前者分析 GNSS（如 GPS L1C 的 75% 导频 / 25% 数据叠加信号）如何按捕获与跟踪门限而非数据解调 SNR 定导频/数据功率分配；后者给出频率估计 ML 门限区与离群崩溃的闭式渐近式（承接 Rife & Boorstyn 1974）。差在分别为单径连续导航跟踪和单音 AWGN 频率估计，未耦合多径稀疏搜索与单帧 LDPC 迭代译码。

- **查新判断**：**部分被做过（Scoop-Check 判定：Level 2 — High Overlap）**。
  - 按 `scoop-check` 四轴拆解：**核心机理**（用 ZZB/离群概率替代局部 CRB 做导频或功率分配）已被 Graff & Humphreys (2024)、Sun et al. (TCOM 2023)、Xiong & Liu (SPL 2023) 做过；**关键洞察**（低 SNR 失效由旁瓣离群/捕获门限主导，CRB 盲区）是 50 年经典结论且已落地到 AFDM（Wang et al. 2026）与 GNSS 导频功率分配（Won et al. 2012）；**迭代接收机低导频收敛悬崖**已有 EXIT 图分析框架（Liu et al. TCOM 2024）。
  - 唯一未见的窄增量（Delta）：Unlike Graff & Humphreys (2024) / Sun et al. (2023) (which apply ZZB optimization to orthogonal OFDM/mmWave positioning pilots) and Huang (2024) / Liu (2024) (which set SP-OTFS ρ via linear-BEM SINR), applying a parametric multipath delay-Doppler ZZB / outlier-probability constraint specifically to choose ρ and guide Round-0 sparse search in a coded iterative SP-AFDM receiver has not been published as one package — 但这块 Delta 极窄，且三张配套第 0 轮搜索卡本身无独立新意（[c48](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c48.md) 是常规 0.25 细网格且相对 0.5 网格增益 1.5 pp 不显著，[c60](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c60.md) 已被淘汰，[c73](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c73.md) 是校验子双路分集）。

- **为什么没人做**：**(2) 发现了但不重要**（次要叠加分析代价）。
  - **工程实践与标准证据**：真实水声调制解调器（WHOI Micro-Modem、NATO JANUS 标准、Li/Zhou/Stojanovic JOE 2008）与蜂窝/Wi-Fi 标准（5G NR PSS/SSS + DMRS、802.11 STF/LTF）根本不把第 0 轮非线性时延-多普勒捕获埋在强数据干扰底下的叠加导频里，而是用**独立高能量前导码**（LFM/HFM 扫频或序列）在零数据干扰下把捕获概率拉满，再在多块帧上摊薄开销。硬在低 ρ 叠加导频里做盲捕获，本质上是先人为制造了一个 $-9.5\text{ dB}$ 导频-数据干信比（ρ = 0.10 时即便噪声为零，导频也淹没在 9 倍数据干扰下），再去解它。
  - **文献与本项目数据证据**：即便限定在叠加导频系统里，ρ 只是一个**一维标量旋钮**，且性能曲线呈强不对称盆底——在项目 [STAGEA_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA_READOUT.md) 中，基线最优在 ρ = 0.25（4.95 dB），保守多给 5% 导频到 ρ = 0.30 也只劣化 **0.18 dB**（5.13 dB），而左侧跌落悬崖一扫便知。正如 Huang 等 (TVT 2024, Sec. V-B) 原文直言：*"in practical applications, the value of ρ_F is usually pre-set as a fixed value"*。此外，多径+非高斯数据干扰+贪心 OMP+LDPC 迭代下的全局 ZZB 很难紧致（Wang 等 `2603.09293` Fig. 3b 显示低 SNR 下非叠加导频的多普勒 MSE 仍远高于 ZZB；Xiong & Liu `2310.02963` Remark 3 也指出某设计 SNR 下的 ZZB 最优波形在该 SNR 下未必是 MSE 最优），花大功夫推导全局 ZZB 来定一个一维常数，性价比远不如直接做 6 个点的 1D 扫描并留 1–2 dB 余量。

- **真实系统里的影响**：
  - **核对卡片数字与前提**：主卡 [I-20261121-01.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-01.md) 引用的**"现有最优 ρ = 0.25（4.95 dB）与理想第 0 轮 ρ = 0.10（3.45 dB）相差 1.5 dB"存在严重口径混淆**！从纯数据功率开销算，$10\log_{10}(0.90/0.75) = \mathbf{0.79\text{ dB}}$（ρ 从 0.25 降到 0.20 仅省 **0.28 dB**，降到 0.05 最多省 **1.03 dB**）；1.51 dB 的大头来自 [STAGEA2_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md) 给全真信道带来的"零估计误差红利"，**仅靠换用 ZZB 规则选 ρ 对现有接收机带来的 SNR 增益是 0 dB**（它最多避免有人盲信错误公式去选 ρ = 0.10）。
  - **配套搜索改进的真实量级**：[c48](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c48.md)（1.84× F0 算力换 5.5 pp，但比 0.5 网格仅 1.5 pp 不显著）与 [c73](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c73.md)（2× 总算力换 3.94 pp）折算到瀑布区 SNR 仅约 0.2–0.4 dB。
  - **跨线致命前提风险**：[STAGEA3_READOUT.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md) 显示同等平均误差下导频离群误差的伤害反而小于高斯误差（0.157 bin 穿越 6.36 dB，而高斯 0.160 bin 崩到 ∞）；更重要的是，一旦按线 B 的 [I-20261121-c25.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 修正失真的"每径独立大速度"信道模型并在前端做公共多普勒补偿，[I-20261121-c29.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md) 实测在 ρ = 0.10、5 dB 下最终误帧率直接降到 0/100——也就是说，**线 A 看到的剧烈多普勒门限悬崖本身很大程度上是未做公共多普勒补偿的仿真产物**。
  - **会改变什么决定**：在真实水声系统里几乎不改变任何设计决定；在纯学术 SP-AFDM 论文里，最多决定"不要套用无编码 BEM 的 SINR 公式直接定 ρ"。

- **最强的反对意见**：
  用全局 ZZB 替代局部 CRB/SINR 优化导频功率分配已在 OFDM、毫米波和雷达领域发过顶刊，而叠加导频的 ρ 只是一个保守多留 5% 仅亏 0.18 dB 的一维旋钮，且单靠换定比例规则拿不到那 1.5 dB 上界，工程上更直接用前导码绕开了该问题。

- **如果要做，最便宜的一步检验是什么**：
  按 [I-20261121-01.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-01.md) 已有 ρ 扫描数据（**零新仿真，纯解析计算 < 10 分钟**），在**同一套接收机和信道参数**下算出匹配的第一轮 SINR 最优 ρ 与单径 ZZB/离群概率预测的 ρ_min，和实测编码 1% FER 最优 ρ = 0.25 并排对比；只有当"匹配 SINR 公式给出的 ρ 导致实测 FER 崩溃（损失 > 1 dB）且简易离群概率界能跨 SNR/信道直接压中悬崖位置"时，才值得把它保留为现有论文里的半页诊断小节（而非另起主线）。

---

## 线 B：第 0 轮先估一个共同多普勒，而不是逐径估

涉及卡片：[I-20261121-c25.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md)（前提）、[I-20261121-c29.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md)（方法）。

- **一句话结论**：**不值得做**（作为方法创新线完全不值得做——谁真卡住了：水声通信界早在 2008 年就用"先公共重采样、再残余处理"解决了这一问题，卡住的只是本项目自己未做公共补偿的仿真脚本；最朴素替代——水声教科书标准两步法（公共重采样 + 小窗稀疏残余估计）——零额外损失且覆盖宽带时间伸缩；这里没有任何新原理，1/2.6 只是多径功率汇集的教科书 $\sum\sqrt{w_i}$ 统计信噪比增益。**但 [c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 暴露的物理前提漏洞必须作为内部纠偏项立刻修掉，否则现有论文会被水声审稿人以信道模型失真直接拒稿**）。

- **白话 + 一个类比**：
  剥掉术语后，这条线分两半：前一半（[c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md)）是在**捉自己仿真代码的虫**——船在海里开，同一条船发出的声波走不同路径到达接收机，水平距离远时各路径的相对速度几乎一样，只有撞到波浪海面的路径有点小偏差，但现有代码 [afdm_env.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/afdm_env.py#L333) 硬给每条径随机抽了相差很大的独立速度。后一半（[c29](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md)）是在**重新发明水声通信的教科书标准做法**——全车人一起坐大巴往前开，测车速当然该把所有人的回波合在一起先测一个整车速度，再管车窗外偶尔晃动的少数人，而不是把能量拆成十份分别猜十个人的速度；而水声领域从 2008 年起几乎所有多载波接收机早就这么干了。

- **最接近的工作**：
  1. **B. Li, S. Zhou, M. Stojanovic, L. Freitag, P. Willett (IEEE JOE, vol. 33, no. 2, pp. 198–209, Apr. 2008, [doi:10.1109/JOE.2008.920471](https://doi.org/10.1109/JOE.2008.920471)，只看了摘要与方法综述)** — *Multicarrier Communication Over Underwater Acoustic Channels With Nonuniform Doppler Shifts*：奠基性的水声两步多普勒补偿架构——先用全部能量估一个公共多普勒伸缩因子并重采样，再估残余频偏；差在针对的是前导+零子载波 ZP-OFDM 而非叠加导频 AFDM。
  2. **C. R. Berger, S. Zhou, J. C. Preisig, P. Willett (IEEE TSP, vol. 58, no. 3, pp. 1708–1721, Mar. 2010, [doi:10.1109/tsp.2009.2038424](https://doi.org/10.1109/tsp.2009.2038424)，只看了摘要与方法综述)** — *Sparse Channel Estimation for Multicarrier Underwater Acoustic Communication: From Subspace Methods to Compressed Sensing*：**几乎完全做过同一件事**——先做公共多普勒重采样去除平台公共运动，再在小残余多普勒字典上用 OMP/BP 稀疏估计存在独立多普勒偏移的少数路径；差在波形是水声 OFDM 而非叠加导频 AFDM。
  3. **P. Qarabaqi & M. Stojanovic (IEEE JOE, vol. 38, no. 4, pp. 701–717, Oct. 2013, [doi:10.1109/joe.2013.2278787](https://doi.org/10.1109/joe.2013.2278787)，只看了摘要与方法综述)** — *Statistical Characterization and Computationally Efficient Modeling of a Class of Underwater Acoustic Communication Channels*：已经把水声多普勒明确物理分解为平台公共运动、收发漂移与海面起伏引入的触面路径附加散射/多普勒，正是 [c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 的物理出处；差在不涉及 AFDM 接收机。
  4. **Y. Yang, L. Ma, S. Liu et al. (IEEE JOE, vol. 51, no. 1, pp. 641–658, 2026, [doi:10.1109/JOE.2025.3599256](https://doi.org/10.1109/JOE.2025.3599256)，只看了摘要)** — *Underwater Acoustic OTFS With Nonuniform Doppler Shifts: Modeling and Off-Grid Block-Sparse Channel Estimation Algorithm*：在新型时延-多普勒波形（UWA-OTFS）上同样先做时域公共重采样，再针对残余非均匀/逐径多普勒做离网格块稀疏 OMP+MLE 估计，并用海试数据验证；差在波形是 OTFS 而非叠加导频 AFDM。
  5. **R. Cao, Y. Zhong, J. Lyu, D. Wang, L. Fu (IEEE GLOBECOM 2024 / [arXiv:2405.02660v2](https://arxiv.org/abs/2405.02660)，读了全文)** — *AFDM Channel Estimation in Multi-Scale Multi-Lag Channels*：将 AFDM 引入水声多尺度多时延（MSML）信道，明确讨论单尺度重采样后残留其他路径伸缩误差的问题，并给出基于 MSML 字典的 AFDM-OMP；差在它采用独立导频子载波且未做"公共多普勒 + 稀疏触面偏移"模型选择。
  6. **K. Tu, T. M. Duman, M. Stojanovic, J. G. Proakis (IEEE JOE 2012/2013, [doi:10.1109/joe.2012.2221812](https://doi.org/10.1109/joe.2012.2221812)，只看了摘要)** 与 **S. Beygi, S. Yerramalli, U. Mitra (IEEE SPL 2012 / IEEE TSP 2015, [doi:10.1109/TSP.2015.2449266](https://doi.org/10.1109/TSP.2015.2449266)，只看了摘要)**：前者在 SPACE08/MACE10/KAM08 海试上直接回答了"何时单公共重采样够用、何时需多支路逐径重采样"；后者给出 MSML 信道的最优贝叶斯单公共重采样与低秩残余估计。另有 **A. Amar, G. Avrashi, M. Stojanovic (IEEE TSP 2017, [doi:10.1109/TSP.2016.2630039](https://doi.org/10.1109/TSP.2016.2630039)，只看了摘要)** 做公共残余频偏低复杂度估计，及 **D. A. Cuji & M. Stojanovic (IEEE JOE 2026, [doi:10.1109/joe.2025.3648608](https://doi.org/10.1109/joe.2025.3648608)，只看了摘要)** 用阵列波束成形分离不同多普勒路径。

- **查新判断**：**已被做过（Scoop-Check 判定：Level 1–2 — Full to High Overlap）**。
  - 按 `scoop-check` 四轴拆解：**物理洞察**（水平水声信道多径以平台公共多普勒为主、仅触面径有小偏移）已被 Qarabaqi & Stojanovic (JOE 2013) 与 Tu 等海试论文确立；**核心机理**（先汇集能量估公共多普勒，再处理少量残余/逐径偏移）是 Li 等 (JOE 2008)、Berger 等 (TSP 2010)、Zhou & Wang (2014 专著) 与 Yang 等 (UWA-OTFS, JOE 2026) 的标准流水线；**应用域**同样是水声多载波通信。
  - 无法写出站得住脚的论文级 Delta：把"先公共多普勒、再少量残余偏移"搬到叠加导频 AFDM 第 0 轮，在审稿人眼里属于把水声教科书标准前置步骤补回到一个漏写它的基线里，不是创新。

- **为什么没人做**：
  - 广义方案（先估公共多普勒再估残余）**不是没人做，而是所有人都在做**。
  - 至于卡片里唯一没在 AFDM 里见过的细枝末节——"在不做时域重采样的前提下，在叠加导频第 0 轮专门做'共同多普勒 + 少数触面径偏移'的显式模型选择"——没人单做的原因是 **(2) 发现了但不重要**（证据如下）：
    1. 真实水声系统里，只要平台有 2 m/s 运动（$a \approx 1.33\times 10^{-3}$），在 $T = 64\text{–}128\text{ ms}$ 内就会造成宽带时间伸缩（采样点漂移 0.7–1.4 个抽头），工程上（WHOI Micro-Modem、Li 等 2008、Yang 等 2026）必须**先在时域用前导码做公共重采样**，根本不会把它留到基带第 0 轮当窄带频偏来估。
    2. 核对本项目实际参数后，残余偏移比 [c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 正文算的还小一倍：[c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 正文按 $f_s = 8\text{ kHz}, N = 1024$（1 bin = 0.977 m/s）算得几何差分 0.0026–0.023 bin，但本轮 P1 U/G 帧实际用 $f_s = 16\text{ kHz}, N = 1024$（1 bin = 1.953 m/s，见 [c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md#L45) 更正），同几何下的径间频差仅 **0.0013–0.011 bin**，海试实测 0.6 Hz 海面重力波偏移也仅 **0.038 bin**。而 [c29](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md#L44-L45) 实测显示纯公共估计在径间标准差 s ≤ 0.1 bin 时已完胜逐径估计且误帧率为 0，[c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md#L45)（l08/l10）也算过即便 $\Delta v = 0.5\text{ m/s}$ 残余 ICI 代价也仅 0.26 dB——所以在水平千米链路下，公共重采样后残余已小到不必做"触面径分类模型选择"；而在短距陡角/高海况（s ≥ 0.3 bin）下，文献已直接采用小窗稀疏字典（Berger 2010 / Yang 2026）或多支路重采样（Tu 2012）。

- **真实系统里的影响**：
  - **对算法创新的影响**：几乎为零（真实系统早已通过前端公共重采样收割了这笔收益）。
  - **对卡片数字前提的核对**：[c29](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md) 声称的 "1/2.7 误差"（实测 0.0938 → 0.0349 bin，1/2.68）有三个关键前提漏洞：(a) 实测是在**真时延、单 SNR = 5 dB、纯单公共多普勒**下跑的，并未实现"再估少数触面径偏移"；(b) 正如复审指出的，公共臂搜的是全多普勒网格，而逐径臂只在已选整数格附近局部搜索，2.68 倍里混进了"避免选错整数格"而非纯粹的能量汇集增益；(c) 一旦径间频差到 s = 0.3 bin，纯公共估计误帧率反超逐径 4 倍以上（18% vs 4%）。
  - **真正改变的项目决定（极关键）**：[c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 迫使整个项目立刻决定**论文的物理场景定位**——如果继续沿用 [afdm_env.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/afdm_env.py#L333) 的逐径独立速度 $v_i \sim |\mathcal{N}(2, 0.5^2)|$ 且不先去公共多普勒，论文只能勉强限定为"高海况/陡角度/多运动体场景（或重采样失败后的残余场景）"，否则水声审稿人会质疑整个第 0 轮多普勒难题（包括半盲估计器需求）都是由不现实的信道模型人为放大的。

- **最强的反对意见**：
  "先估公共多普勒消除平台运动、再处理少数路径残余多普勒"是水声多载波通信近二十年的教科书标准流程（Li 2008、Berger 2010、Yang 2026），这条线只是暴露了本项目仿真器漏做公共重采样且逐径独立抽速的模型瑕疵，不能包装成新方法。

- **如果要做，最便宜的一步检验是什么**：
  **不要再立项做新方法**，只做一次低成本的模型校准检验（沿用 [c29](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c29.md) 同款 100 帧脚本，约 0.2 核时）：按 [c25](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c25.md) 真实物理设定（公共多普勒置零/重采样后，7 条非触面径给 0.01 bin 几何差、3 条触面径给 0.05–0.15 bin 海面偏移，且**不给真时延、由完整接收机自行搜径**），测一遍现有接收机与"公共粗估 + 现有接收机"的 1% FER 穿越点——如果这样一来 ρ = 0.15 下的第 0 轮多普勒瓶颈直接消失，就应立刻修正主线的信道假设和问题定义，避免在虚假前提上继续投入半盲估计器研发。

---

如需把以上两条线的方向判读进一步压成更短的日常口语版，可以回复「白话」。