读取漏斗状态及簇 C、簇 D 的卡片、脚本与实测数据。
读取 c49 实际脚本及簇 B 的全部卡片、脚本与实测汇总。
读取簇 A 全部文件、支撑脚本及文献基线地图。
读取 c50 脚本、CPP 信道算子源码及相关参考卡以核实物理建模细节。
核查信道物理算子源码并联网检索四个机制簇的文献先例。
核查时域响应算子源码、本地预印本核对报告及补充文献信息。
核实底层时域算子与 c19 训练集、c43 链式前作及槽位重试实现。
以下严格按第 8 步双拍对抗终审（`kill-argument`）协议及 [FUNNEL.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md) 铁律，对 4 个独立机制簇的 4 张代表卡（含同簇并入子卡）给出跨模型终审裁决。**总览结论：4 张代表卡均不够独立成一篇 IEEE TCOM / TWC 新论文（`0 PASS / 4 KILL`），其中簇 B（`c44/c47/c24/c50`）的核心数据辅助重捕获算子与公平基线读数、簇 D（`c25`）的适用域边界、簇 A（`c11/c17`）的检测器校准定位均有明确工程价值，分别按精确条目回收至在研主线或现稿对应章节。**

---

### 1. 代表卡 `I-20261122-c46`（簇 C：跨帧捕获 + 低导频数据辅助跟踪链；并入 `c31`, `c42`）

#### 1. 查新与固有重要性判定
- **固有重要性（抛开先例）**：**中**——在几何缓变的连续突发传输中用首帧捕获配合低导频数据辅助跟踪可压低平均导频功率（25% → 11.25%），具系统吞吐价值，但高度依赖“12 帧内时延与径幅冻结”的强缓变假设，不解决单帧低导频悬崖（头号靶 #0）。
- **最接近工作（≥4 篇/标准）与差别**：
  1. **M. Stojanovic**, *"OFDM for Underwater Acoustic Communications: Adaptive Synchronization and Sparse Channel Estimation,"* *Proc. IEEE ICASSP*, 2008（及 *OCEANS* 2006）：已建立水声多载波“首块训练捕获 + 后续块利用判决符号做稀疏信道与多普勒自适应跟踪”的标准架构。
  2. **P. C. Carrascosa & M. Stojanovic**, *"Adaptive Channel Estimation and Data Detection for Underwater Acoustic MIMO–OFDM Systems,"* *IEEE J. Oceanic Eng.*, vol. 35, no. 3, pp. 635–646, Jul. 2010：系统验证首块初始化 + 后续块判决导向（decision-directed）跨块跟踪大幅削减训练开销，并在真实浅海信道检验。
  3. **Y. Luo et al.**, *"Data-Aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System,"* *IEEE Trans. Commun.*, vol. 74, pp. 12485–12500, 2026（`arXiv:2607.18881`）与 **H. B. Mishra et al.**, *"OTFS Channel Estimation and Data Detection Designs With Superimposed Pilots,"* *IEEE Trans. Wireless Commun.*, vol. 21, no. 4, pp. 2258–2274, Apr. 2022：均在 SP-AFDM/SP-OTFS 中以判决数据符号叠加导频构成满功率参考字典重估稀疏多径。（注：题面提及的 `arXiv:2604.07308` / `arXiv:2607.09184` 经联网核查未在公开索引解析到有效条目，不作虚引。）
  4. **3GPP TS 38.211 (NR Front-Loaded + Additional DMRS) / IEEE 802.11bd Midamble / GNSS 捕获–跟踪环路**：高密度首帧捕获 + 低密度跟踪 + 失锁重捕获是物理层教科书级帧结构。
  - **差别评估**：唯一表面差异是叠加导频下“捕获帧（$\rho=.25$）也载数据、跟踪帧降 $\rho=.10$”；但这只是把已知捕获–跟踪功率分配平移到 SP-AFDM，既无 AFDM 一维仿射折叠/CPP 独有的新数学难题，也未做过先例直套对比。
- **分类**：**`(2)` 硬套 / 已有跨帧判决导向跟踪机制的直接移植**。

#### 2. 第一拍：最强拒稿信（Hostile Rejection Memo，189 字）
> 本文把通信与水声领域沿用近二十年的“首帧高导频捕获 + 后续帧判决导向跟踪”直接套在 SP-AFDM 上，无任何波形特有理论突破。更严重的是实验验证存在多处致命硬伤：其一，仿真代码用真实误比特数门控校验漏检并直读真实发射符号做重估，掩盖误差传播；其二，信道在 12 帧内锁死所有径的时延与幅度、仅扰动多普勒，严重失真；其三，对比基线（$\rho=.25$）被迫逐帧冷启动、未配同等跨帧跟踪或单帧重捕获，制造了虚假优势。建议直接拒稿。

#### 3. 第二拍：对照源码与实测数据的逐点核实
- **源码级硬伤 1（真值门控漏检 + 直读真符号）**：
  - [c_l2_c46_chain.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py#L42-L43) 与 [L56-L57](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py#L56-L57) 写明 `ok = (not br[1]) and br[0] == 0`、`ok = (not r[1]) and r[0] == 0`，运行时直接偷读真实误比特数 `r[0]` 屏蔽潜在漏检错帧，且整个 `c46` 输出（[combined.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c46/combined.json)）甚至未记录漏检计数。
  - [c_l2_c42_da.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c42_da.py#L27-L28) 的 `refine2()` 直接取 `raw['data']` 合成满功率参考信号，未走真实的“译码→重编码→重调制”闭环；且第 34 行停止门限 `thr * float(obs['sigma2'])` 依赖已知真实 $\sigma^2$，主链还硬编码了离线标定因子 `K = 2.5`。
- **源码级硬伤 2（跨帧信道过度理想化）**：
  - [c_l2_c46_chain.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py#L33-L35) 在 12 帧（按项目参数约 `0.77–1.54 s`）内完全锁死所有 8 条径的整数时延 `base[0]` 与径幅 `base[2]`，只对多普勒加 `U(-0.2, 0.2)` bin/帧游走和随机相位；忽略宽带时延漂移与径生灭。
- **基线不对等与跨卡反证**：
  - [c_l2_c46_chain.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py#L36-L40) 中 `base25` / `base25r` 每帧强制冷启动、未配任何跨帧跟踪或 `refine2` 重估。即便如此，[combined.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c46/combined.json#L31-L39) 显示 `5.0 dB` 下 `trkr`（`0.318%`）与冷启动 `base25r`（`0.318%`）已完全打平，全 4 点合并 `base25r - trk`（CI `[-0.068, +0.795]` pp）跨 0，仅靠冷启动加 8→12→16 槽重试才挤出 `base25r - trkr = +0.545 pp`（CI `[+0.159, +0.932]`）。
  - 跨卡对照更致命：同在 `4.5/5.0 dB`，[out_c46/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c46/summary.json#L20-L28) 的跨帧 `trkr` 稳态 FER 为 `2.02%`（4.5 dB: `3.73%`），反观单帧无跨帧记忆的 [out_c47r20/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r20/summary.json#L11-L20)（$\rho=.20$ + `reacq_ens`）仅 `0.25%`（4.5 dB: `0.50%`），[out_c47r25/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r25/summary.json#L11-L20)（$\rho=.25$ + `reacq2`）仅 `0.875%`——`c46` 的胜出完全依赖拿未装备同级工具的弱冷启动基线作靶子。
- **并入子卡核查（`c31`, `c42`）**：[I-20261122-c31.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c31.md) 主臂 `warm_ok` 败于硬基线、第 2 批 `warm` CI `[-0.4, +3.6]` 未决；[I-20261122-c42.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c42.md) 与 [out_c42/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c42/summary.json#L55-L58) 测得满功率译对帧重估命中率 `45.8% → 91.8%`、条件 FER 追平真几何（`3.8%/0% vs 5.1%/0%`），属常规判决导向重估工程读数且含相同真值门控捷径，均无独立幸存点。

`VERDICT [I-20261122-c46]: KILL — 查新属 (2) 经典捕获-跟踪跨帧架构平移，源码含真值门控/直读真符号、锁死时延径幅及不对等冷启动基线；仅将 c42 满功率重估命中率读数（45.8%→91.8%）作为现稿讨论节“连续传输扩展”一句话备忘，整簇（c46/c31/c42）关闭。`

---

### 2. 代表卡 `I-20261122-c49`（簇 D：超搜索窗回声的数据辅助残差抵消；并入前提诊断卡 `I-20261122-c25`）

#### 1. 查新与固有重要性判定
- **固有重要性（抛开先例）**：**中**——真实长时延水声信道中超出保护间隔/搜索窗的回声确会引发严重性能恶化，但必须建立在真实跨帧线性卷积物理模型下才有工程意义。
- **最接近工作（≥4 篇）与差别**：
  1. **D. Kim & G. L. Stüber**, *"Residual ISI Cancellation for OFDM with Applications to HDTV Broadcasting,"* *IEEE J. Sel. Areas Commun.*, vol. 16, no. 8, pp. 1590–1599, Oct. 1998：经典超循环前缀残余 ISI 迭代抵消（RISIC），明确处理上一帧尾干扰（IBI）消除与本帧循环重构。
  2. **K. Yeo, K. Pelekanakis, & M. Chitre**, *"Time-Domain Equalization for Underwater Acoustic OFDM Systems with Insufficient Cyclic Prefix,"* *Proc. MTS/IEEE OCEANS*, 2011（及 **C. R. Berger et al.**, *IEEE TSP* 2010）：面向水声超保护间隔多径的时域 IBI/ISI 抵消与稀疏估计。
  3. **Y. Luo et al.** (*IEEE TCOM*, 2026, `arXiv:2607.18881`) / **H. B. Mishra et al.** (*IEEE TWC*, 2022)：叠加导频下的迭代数据辅助残差多径估计与干扰消除。
  4. **本项目已终审淘汰卡 [I-20261121-l12.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-l12.md) 与 [I-20261122-l05.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-l05.md)**：已实测直接放宽搜索窗至 400 抽头并换非 chirp 随机相位导频（或前导给时延）即可消解主要窗宽损失，两卡均已因机制已知判 `KILL`。
  - **差别评估**：`c49` 在错误假设单帧循环延拓的理想化玩具模型上做“窗外 OMP 找径并减除”；若修正为真实超 CPP 跨帧线性卷积，机制即落回 Kim–Stüber RISIC + 判决导向稀疏回声估计。
- **分类**：**`(2)` 经典超保护间隔残差抵消的简化移植（且叠加致命物理建模错误）**。

#### 2. 第一拍：最强拒稿信（Hostile Rejection Memo，193 字）
> 本文存在根本性物理建模“逆罪”（inverse crime）：系统真实 CPP 仅 102 样点，作者却用单帧循环延拓算子在 122–400 抽头注入并用同一循环字典抵消“窗外回声”，完全抹掉了超 CPP 必然产生的上一帧块间干扰（IBI）与本帧前段截断失配（最多达帧长 29%），导致 `58.4%→18.6%` 增益在真实线性卷积信道上无法成立。若真发了 400 抽头 CPP，直接扩窗+随机导频更优且已被本组 l05 淘汰；方法亦未超 Kim–Stüber RISIC 范畴。拒稿。

#### 3. 第二拍：对照源码与实测数据的逐点核实
- **致命物理建模错误（单帧循环延拓 vs 真实超 CPP 线性卷积）**：
  - 查 [c_l2_c25_echo.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c25_echo.py#L18-L24) 与底层 [physical.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_20260920/src/physical.py#L20-L27)、[L109-L114](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_20260920/src/physical.py#L109-L114)：项目真实搜索窗与 CPP 上限为 `l_max_cap = 102`，但 `inject()` 对 `l ∈ [122, 400]` 直接调用 `TimePathOps(c).responses_time(X)`，对任意 `l` 执行**整帧循环移位 `(idx - l) % N` 加完整 chirp 周期前缀相位**！
  - [c_l2_c49_canc.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c49_canc.py#L21-L31) 的 `cancel()` 又用**完全相同的单帧循环算子**构造 `8,700` 列字典（`348 × 25`）去匹配并减除。
  - 在真实 `L_CPP = 102` 的线性卷积信道中，回声时延 `l ∈ [122, 400]` 的前 `l - 102` 个样点（最多 `298/1024 = 29.1%` 帧长）接收的是**上一帧尾部符号（IBI，且无 chirp 周期折返相位）**，而非本帧尾部循环延拓。将 `c_l2_c49_canc.py` 直接用于真实物理信道时，不仅匹配相关能量损失近三成，第 31 行减除循环延拓本帧尾部还会在前 `l - 102` 样点**凭空注入同等功率的人造假干扰**，同时完全留着真实 IBI 未消！即便按 Kim–Stüber 方式利用已译出的上一帧 $x_{t-1}$ 做跨帧 IBI 消除 + 截断线性尾部抵消，算法结构与性能也需从零重写，且会引入跨帧误差传播与上一帧译错失效问题。因此 [out_c49/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c49/summary.json#L20-L23) 的 `58.4% → 18.6%`（`canc_blind: 11.9%`）及 `99.5%` 命中率仅在“循环注入+循环抵消”的自洽玩具模型里成立。
- **两难死局与朴素基线反杀**：
  - 若辩称“物理上发了 400 抽头长 CPP、只是收端不扩窗”，则发端已白白背了 `28.1%`（约 `1.0 dB`）前缀税，收端直接换随机相位导频并放宽窗长至 400 抽头即可——[I-20261122-l05.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-l05.md#L67) 实测随机导频在 `l_cap = 400, 6 dB` 错帧仅 `4/200 = 2.0%`，而 [out_c49/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c49/summary.json#L45) 在同 `6 dB, β=0.1` 的 `canc` 仍高达 `8.75%`，且 `c49` 需构建 `8,700` 列巨型字典（原前端的 `17×`，作者自述被迫拆三片慢跑）。
- **关于前提诊断卡 `I-20261122-c25` 的单独裁决**：
  - [I-20261122-c25.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c25.md)（[out_c25/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c25/summary.json#L8-L16)：`clean 1.25%` → `β=0.05: 21.6%` / `β=0.10: 82.25%`）揭示的“生成器因 `l_max_cap = 102` 重抽 48.6% 自然样本，且窗外未建模强回声会导致 FER 剧烈恶化”这一边界事实属实（且真实超 CPP 含 IBI 只会更严重），但 48.6% 重抽早已登记在 `res-20261015-02` 与 [ABSTRACTION.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/ABSTRACTION.md#L70)，且 [FUNNEL.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md#L29) 与 `pit` 规则（以及 `I-20261121-l12` 的终审先例）明确规定：**`c25` 仅作为一句论文适用域与局限注记回收，不应与 `c49` 绑定留作 `REVISE / PARK`**。

`VERDICT [I-20261122-c49]: KILL — c49 存在严重物理建模逆罪（真实 CPP=102 却用单帧循环延拓注入并抵消 122–400 抽头回声，漏掉跨帧线性卷积 IBI），长 CPP 下劣于扩窗+随机导频、真实超 CPP 下则落入 (2) 经典 RISIC；将 c25 的前提诊断事实（48.6% 重抽与窗外能量敏感性）与 I-20261121-l12 合并回收为现稿局限节适用域注记，整簇（c49/c25）关闭。`

---

### 3. 代表卡 `I-20261122-c47`（簇 B：校验触发的判决导向整帧重捕获与最优 $\rho$ 下移；并入 `c44`, `c48`, `c24`, `c50`）

#### 1. 查新与固有重要性判定
- **固有重要性（抛开先例）**：**中（作为在研主线核心算子价值高；作为独立第二篇论文价值低）**——校验失败后用导频 + 译码后验均值从零做整帧 OMP 重捕获，在项目现有接收机上把默认 $\rho=.25$ 基线 FER 从 `4.625%` 压到 `0.875%–1.125%`、径数超槽从 `29.5%` 压到 `3.5%`，工程收益非常实在；但它是对现稿局部 2 径编辑 `A1` 的直接升级，而非独立新理论问题。
- **最接近工作（≥4 篇）与差别**：
  1. **K. Zheng, M. Wen, T. Mao, L. Xiao, & Z. Wang**, *"Channel Estimation for AFDM With Superimposed Pilots,"* `arXiv:2404.10232`（*IEEE TVT* 2025）：已提出 SP-AFDM 下基于迭代数据辅助的信道重估与导频功率配比分析。
  2. **Y. Luo, Y. L. Guan, Y. Ge, Y. Jiang, L. Meng, & D. González G.**, *"Data-Aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System,"* *IEEE Trans. Commun.*, vol. 74, pp. 12485–12500, 2026（`arXiv:2607.18881`）：已用叠加导频 + 检测符号构造满功率字典做整帧全局稀疏重估与离格精修（自动定阶，本就不局限于 2 径局部修改）。
  3. **H. B. Mishra, P. Singh, A. K. Prasad, & R. Budhiraja**, *"OTFS Channel Estimation and Data Detection Designs With Superimposed Pilots,"* *IEEE Trans. Wireless Commun.*, vol. 21, no. 4, pp. 2258–2274, Apr. 2022（及 **Kanazawa et al.**, `arXiv:2501.15935`）：已系统分析 SP 迭代数据辅助接收机下的最优导频比 $\rho$ 随接收机迭代能力下移的规律。
  4. **项目在研主线（[FUNNEL.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md#L23) 与 [STATE.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/STATE.md#L24)）**：Eric 已于 11-20 定稿现论文中心为“**译码失败后继续迭代还是重搜、各需多少时间**”，且 `11-21-data-pilot-fer` 已在攻低导频第 0 轮捕获。
  - **差别评估**：`c44` 相对现稿 `A1` 把局部 2 径交换换成整帧 OMP 重捕获并由校验子裁决，但在 SP 文献中用“导频+数据估计”做全局稀疏重估本就是常态；[I-20261122-c47.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c47.md#L33) 更明文自认“**无新机制；是 c44 的工作点扫描**”。
- **分类**：**`(3)` 直接撞 `FUNNEL.md` 在研主线 + `(2)` 全局数据辅助重估与一维 $\rho$ 扫描属文献常规做法**。

#### 2. 第一拍：最强拒稿信（Hostile Rejection Memo，188 字）
> 本文无独立成文的新原理：在 SP-AFDM 中用“导频 + 译码后验均值”做整帧 OMP 重捕获（c44）及据此重扫最优导频比 $\rho$（c47），既与 Y. Luo (TCOM'26)、Zheng (TVT'25) 及 Mishra (TWC'22) 的数据辅助全局重估/功率分配高度重合，又直接撞本组现稿“译码失败后重搜策略与时间权衡”主线。实验上，c47 的最优 $\rho$ 下移仅靠 2/800 对 9/800 的极小样本支撑，且在 `reacq2` 上置信区间跨零、$\rho=.15$ 额外乘 1.5 倍噪声失公平；c50 缺固定 12 槽基线。应并入现稿而非单独立项。

#### 3. 第二拍：对照源码与实测数据的逐点核实
- **统计脆弱性与公平性漏洞（`c47`）**：
  - 对照 [out_c47r20/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r20/summary.json#L11-L20)、[out_c47r25/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r25/summary.json#L11-L20) 与 [out_c47r25/paired.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r25/paired.json#L2-L47)：
    - 预注册主臂 `reacq_ens` 虽给出 `r25 - r20 = +0.875 pp`（CI `[+0.247, +1.625]`），但绝对错帧数仅是 **9/800 vs 2/800**（且 `5.0 dB` 两者均为 `0/400`，完全由 `4.5 dB` 单点驱动）。
    - 同批数据的 `reacq`（1 次重捕获）仅差 1 帧（`9/800` vs `8/800`）；**`reacq2`（2 次重捕获）为 `7/800` vs `5/800`，配对差 `+0.25 pp`（CI `[-0.50, +1.00]` 跨 0）**；事后臂 `ladder` 差 `+0.625 pp`（CI `[0.0, +1.25]` 下界触 0）。结论对臂选择极不稳健。
    - [PREDICTIONS_c20261122_c47.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_c20261122_c47.md#L3) 与 [out_c47r15/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r15/summary.json#L4) 对 $\rho=.15$ 单独设 `K = 1.5`（$\rho=.20/.25$ 为 `K = 1.0`），旋钮不公平，且即使如此 `r25 - r15` 在 `reacq_ens`（CI `[-0.75, +1.125]`）和 `reacq2`（CI `[-0.125, +1.25]`）上均跨 0。
- **单帧头号靶未破 + 缺时间帕累托账（`c44`）**：
  - [c_l2_c44_reacq.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c44_reacq.py#L21-L52) 工程实现干净（无真值门控，全部由校验子裁决，`undetected = 0`；但第 34 行 `mu_of()` 直接读取 `ctx.system.rho` 而非显式传 `RHO/1000`，复用时需防隐式耦合）。
  - 但 [out_c44/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c44/summary.json#L11-L19) 显示：在 $\rho=.10$ 单帧下，`reacq2 = 17.125%`、`reacq_ens = 15.625%`，仍大幅落后于甚至未配重捕获的 $\rho=.25$ 硬基线（`5.625%`），更远逊于配齐重捕获的公平 $\rho=.25$ 基线（`0.875%–1.125%`）；且脚本未上报 2575 列 OMP + 多次重跑全链的 CPU 毫秒账，无法脱离现稿主线的“重搜时间帕累托”独立评估。
- **并入子卡核查（`c50`, `c24`, `c48`）**：
  - [c_l2_c50_p10.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c50_p10.py#L27-L36) 与 [out_c50/summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c50/summary.json#L10-L16) 虽给出亮眼读数（`cap8 29.5%` → `sel 10.375%` → `reacq 3.5%` → `both 2.75%`，自动找回平均 `9.2` 径），但**遗漏了最直接的朴素基线——同帧固定 12 槽 `cap12`**（[I-20261122-c24.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c24.md#L43) 已在 `5.0/5.5 dB` 证实 `cap12 = 3.3%` 远优于 `sel = 7.9%`），且参照臂 `p8`（`5.625%`）未带重捕获导致 `both < p8` 不对等。
  - [I-20261122-c48.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c48.md#L40-L43) 显示单一参考 `hard`（`15.75%`）对 `mu`（`16.9%`）CI `[-0.25, +2.6]` 未分开，`pilot` 对照（`27.0% vs 27.1%`）仅证实收益来自数据辅助，而 `ens_all`（`12.4%`）是以失败帧 `3×` 算力换取常规多假设多样性，无独立成文点。
  - **重要回收价值**：`c44` 的“校验失败后以导频+后验均值做整帧 OMP 重捕获”作为**现稿主线的新增候选重搜算子**极有价值（在 $\rho=.25$ 把 `4.625%` 压至 `1.125%/0.875%`，在 $P=10$ 径数超槽把 `29.5%` 压至 `3.5%`），应直接并入现稿重搜算子家族并补齐 CPU 时间帕累托与 `cap12` 对照。

`VERDICT [I-20261122-c47]: KILL — 查新属 (3) 直撞 FUNNEL.md 现稿主线（“译码失败后继续迭代还是重搜、各需多少时间”）且算子本身属 (2) 已有 SP 数据辅助全局重估，c47 统计脆弱（2/800 vs 9/800、reacq2 跨 0、ρ=.15 方差倍增不公）、c50 缺 cap12 基线，不够另起新论文；强制将 c44 整帧 OMP 重捕获算子、c47 公平基线更新读数（ρ=.25: 4.625%→1.125%/0.875%）及 c24/c50 槽位失配读数回收至现稿主线重搜算子对比与 10-19-slot-mismatch 任务，整簇（c47/c44/c48/c24/c50）在漏斗关闭。`

---

### 4. 代表卡 `I-20261122-c19`（簇 A：校验子与残差双特征驱动的 3 权重逐帧噪声方差倍数门控；并入 `c08`, `c11`, `c17`）

#### 1. 查新与固有重要性判定
- **固有重要性（抛开先例）**：**低**——在协议已知当前 $\rho$ 的正常接收机里，按 $\rho$ 离线查一张 4 行常数表 $\alpha(\rho)$ 就能零额外开销获得与门控相同甚至更好的性能；且即便校完，低 $\rho=.10$ 仍输硬基线 $\rho=.25$ 约 `1.5–2 dB`，不改变系统工作点。
- **最接近工作（≥4 篇）与差别**：
  1. **L. M. A. Jalloul, S. P. Alex, & M. M. Mansour**, *"Soft-Output MIMO Detectors with Channel Estimation Error,"* *IEEE Signal Process. Lett.*, vol. 22, no. 7, pp. 993–997, Jul. 2015：系统给出计入信道估计误差方差的软输出 LLR 缩放与等效噪声方差校准公式。
  2. **J. P. Vila & P. Schniter**, *"Expectation-Maximization Gaussian-Mixture Approximate Message Passing,"* *IEEE Trans. Signal Process.*, vol. 61, no. 19, pp. 4658–4672, Oct. 2013（EM-GAMP）与 **SURE-AMP**：在迭代消息传递中直接由残差能量自标定等效噪声方差，无需离格训练权重。
  3. **H. He, C.-K. Wen, S. Jin, & G. Y. Li**, *"Model-Driven Deep Learning for MIMO Detection,"* *IEEE Trans. Signal Process.*, vol. 68, pp. 1702–1715, 2020（`arXiv:1907.09439`, OAMP-Net2）与 **Yuan et al.**（`arXiv:2611.14877`, AFDM 无保护带迭代消息传递等效噪声方差自更新）：均覆盖少量可学展开标量或残差驱动的等效方差更新。
  4. **项目已有决定与先验实验（[FUNNEL.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md#L23) 与 [STATE.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/STATE.md#L27-L28)）**：Eric 已于 11-21 明确把“未知噪声方差”定为**留作论文附注**（已有闭合 Stein 估噪读数 `experiments/sigma2_stein_20261121/READOUT.md`），不另开主线。
  - **差别评估**：只是把“校验子反推 LLR 缩放”与“残差功率 / 已知 $\sigma^2$”做 3 参数对数线性网格拟合；不是真盲噪声估计，也不超越已知 $\rho$ 下的零成本离线查表。
- **分类**：**`(2)` 已知等效噪声方差/LLR 温度校准且朴素离线查表 $\alpha(\rho)$ 已解（同时撞 `FUNNEL.md` 未知噪声附注边界与杀卡准则 2）**。

#### 2. 第一拍：最强拒稿信（Hostile Rejection Memo，189 字）
> 本文宣称的“物理特征驱动轻量跨 $\rho$ 门控”是个伪痛点与伪盲方案。源码显示主权重特征 `r = residual / sigma2`（$w_2=1.0$）仍强依赖已知真实热噪声方差 $\sigma^2$，本质只是已知 $\sigma^2$ 下的残差温度因子，并非盲估噪。更致命的是，通信协议中 $\rho$ 本就为接收机所知，零开销离线查表 $\alpha(\rho)$ 在 $\rho=.10$ 实测 `4.25%` 甚至击败付出双倍 F0 算力的门控（`5.00%`），在 $\rho=.25$ 亦优于门控（`4.625% vs 4.75%`），且连逐帧 Genie 上限也只差 1 pp。无独立发表价值，拒稿。

#### 3. 第二拍：对照源码与实测数据的逐点核实
- **源码核实：并非真盲噪声估计，强依赖真实 `obs['sigma2']` 与双倍算力**：
  - [c_l2_c19_gate.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c19_gate.py#L19-L23) 调用 `b16.resid_factor(C['ctx'], obs, arr)[1]`，而 [c_l2_c16_resid.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c16_resid.py#L18-L19) 第 19 行返回的正是 **`r / obs['sigma2']`**（而且第 16 行同样直接读取协议已知的 `1 - system.rho`）。
  - [out_c19/train_summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19/train_summary.json#L3-L6) 学到权重 `w = [0.2, 0.25, 1.0]`，即 $k \approx 1.22\,k_s^{0.25}\cdot (r_{\text{res}}/\sigma^2)$，主项就是用真实 $\sigma^2$ 归一化的残差功率比，传回 [c_l2_c13_blind.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c13_blind.py#L36) 后令 $\sigma_{\text{eff}}^2 = k\sigma^2 \approx 1.22\,k_s^{0.25}\,r_{\text{res}}$——本质退化为常规残差方差替代，但必须先完整跑一遍原链路 F0 提取特征，再对 `kg != 1` 的帧重跑第二遍 F0。
- **对比零成本离线查表 $\alpha(\rho)$ 零净增益（命中杀卡准则 2）**：
  - [out_c19/test_summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19/test_summary.json#L7-L70)：
    - $\rho = 0.10$：固定 `×2.5`（`sig250`）FER = **`4.25%`**，门控 `gate` = **`5.00%`**（`gate - sig250 = +0.75 pp`, CI `[0.0, +1.625]`），门控不仅白付 100% 帧双遍 F0 算力（`kg_hist["1"] = 0`），性能反而更差。
    - $\rho = 0.25$：固定 `×1.0`（`base`）FER = **`4.625%`**，门控 `gate` = **`4.75%`**（`+0.125 pp`, CI `[-0.375, +0.75]`），且 `459/800`（57.4%）帧白跑第二遍 `k = 1.5`。
  - [out_c19g/test_summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19g/test_summary.json#L7-L102)：
    - 缺失了真正公平的按 $\rho$ 查表基线（如 $\rho=.15$ 固定 `k=1.5`），仅放了错配的 `sig250` 作稻草人；实际 `out_c47r15` 同 4.5/5.0 dB 上固定 `K=1.5` 的 `base` 已是 `7.375%`，优于此处门控的 `8.375%`（且门控 `636/800` 帧都挤在 `k=1.5`）；$\rho=.20$ 上门控 `5.25%` 甚至略输单特征 `synd`（`4.75%`）；$\rho=.25$ 上 `6.125%` 再次差于 `base`（`5.875%`）。
  - 天花板锁死：[out_c19/train_summary.json](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19/train_summary.json#L12-L33) 中逐帧白送最优倍数的 `genie_any_k` 在 $\rho=.10$ 为 `3.0%`（相对固定 `×2.5` 的 `4.0%` 仅余 `1.0 pp`）、在 $\rho=.25$ 为 `5.75%`（相对固定 `×1.0` 的 `6.75%` 仅余 `1.0 pp`）；且 [I-20261122-c24.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c24.md#L47) 已注明该 3 权重换到 12 槽上会直接抵消收益，泛化脆弱。
- **并入子卡核查（`c08`, `c11`, `c17`）**：
  - [I-20261122-c08.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c08.md) 已被前提卡 [I-20261122-c11.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c11.md) 证伪归因（5 接口标量等价于把检测器等效噪声报大，且直接 `σ²×2.5` 胜出 `3.0 pp`）。
  - [I-20261122-c17.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261122-c17.md) 给出了整簇唯一有价值的系统内机理读数：`σ²×2.5` 的增益 100% 来自**检测器输入**（前端份额 0、重估份额 0、检测器份额 1.00，其中末轮占 0.86、首轮占 0.59），即本质是低导频下的检测器 LLR 置信度校准；但这仅是单接收机内部消融事实，无独立成文价值。

`VERDICT [I-20261122-c19]: KILL — 查新属 (2) 已有信道估计误差等效噪声/LLR 温度校准且撞 FUNNEL.md “未知噪声方差留作论文附注”与杀卡准则 2；源码证实主特征 r/sigma2 依赖已知真实 sigma2 并非真盲估计，实测在已知 ρ 下不敌零成本离线查表 α(ρ)（ρ=.10: 5.00% vs 4.25%；ρ=.25: 4.75% vs 4.625%）且付双倍 F0 算力、Genie 上限亦仅余 1 pp；将 c11/c17 的机理定位读数（低 ρ 失配 100% 落在检测器 LLR 置信度校准、前端与重估对 σ² 不敏感）回收至 11-21-data-pilot-fer 与现稿“未知噪声方差/检测器接口”附注，整簇（c19/c08/c11/c17）关闭。`

---

### 终审汇总表

| 代表卡（并入同簇子卡） | 机制簇 | 固有重要性 | 查新分类 | 终审裁决 | 精确回收去向 |
|---|---|---|---|---|---|
| `I-20261122-c46` (`c31`, `c42`) | 簇 C：跨帧捕获+低导频跟踪 | 中 | `(2)` 经典捕获-跟踪平移 | **KILL** | 仅留 `c42` 译对帧重估命中率读数（`45.8%→91.8%`）作现稿连续传输讨论一句备忘 |
| `I-20261122-c49` (`c25`) | 簇 D：窗外回声抵消与超窗诊断 | 中 | `(2)` 经典 RISIC + 物理逆罪 | **KILL** | `c25` 48.6% 重抽与超窗敏感性事实并入 `I-20261121-l12`，写进现稿局限节适用域声明 |
| `I-20261122-c47` (`c44`, `c48`, `c24`, `c50`) | 簇 B：校验触发整帧重捕获与 $\rho$ 下移 | 中（主线算子高） | `(3)` 撞现稿主线 + `(2)` 常规全局重估 | **KILL** | **重点回收**：`c44` 整帧 DA-OMP 重捕获算子、`c47` 公平基线更新（`ρ=.25: 4.625%→1.125%/0.875%`）及 `c24/c50` 径数超槽读数并入现稿“失败后重搜与时间帕累托”主线与 `10-19-slot-mismatch` |
| `I-20261122-c19` (`c08`, `c11`, `c17`) | 簇 A：3 权重逐帧方差倍数门控 | 低 | `(2)` 离线查表已解 + 撞附注边界 | **KILL** | `c11/c17` 检测器置信度校准定位读数（检测器份额 `1.00`、前端/重估 `0`）回收至 `11-21-data-pilot-fer` 与现稿未知噪声附注 |
