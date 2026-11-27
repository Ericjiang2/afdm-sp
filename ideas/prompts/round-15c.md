# 第 15 轮 Phase 1C：左半场「第一性原理真 AFDM 占优（`[S档]`）」定向探索专轮（2026-11-26 勘误修订版）

> **背景与诚实预期（严禁背指标夸大！）**：
> 1. 经过 Phase 1A + 1B 约 35 道题实测，右半场（高机动双色散共性 `[A档]` 硬题）已有 6 道过审候选；而左半场**严格跨波形净赢的 `[S档]` 目前实测存活为 `0` 题**（`k01+k02` 对曲率扫描 `OFDM` 检出率仅领先 `+8.75 pp < 15 pp`，只能靠 `10.7×` 耗时比走算力账；`P-m-03-Adj` 在未知信道单帧盲捕获下 `SC-FDE` 误码率 `42.2%–45.2%` 反而显著优于现有 `AFDM` 的 `94.1%`，不计入左半场优势存量）。
> 2. **零存活完全合法**：真跨波形 `[S档]` 本就极稀缺。**本专轮最终 `0` 题存活是完全合法且受鼓励的诚实结果**——把候选逐一测透并记清死因，远好于凑数字或挑弱基线硬报存活。

规则栈：本文件 > [`../FUNNEL.md`](../FUNNEL.md)（11-26 双半场版） > [`round-15b.md`](round-15b.md)。

---

## 一、左半场立题与实测硬纪律

### 1. 先区分两类物理机制，再用「3 分钟四波形结构量数值预检」替代纯文字编故事
- **术语准确化**：
  - 支点 ①（斜脊耦合流形）与支点 ②（稀疏窗内多径分离 + 局部追快变相位）仍在线性酉变换模型内，`AFDM` 若能占优，靠的是**未知信道/杂波参数在啁啾基下的表示稀疏度或参数可分离性**高于纯频域基、纯时域基与矩形二维基；
  - 支点 ③（非线性/低比特量化/模约束硬件）才是映射本身的**非酉前端破缺**。
- **强制 3 分钟数值预检（禁靠三句话文字硬编）**：
  动笔跑蒙特卡洛前，必须先写一个 `≤ 3` 分钟小脚本，在四类波形（`AFDM`、`OFDM`、`SC-FDE`、`OTFS / Zak-OTFS`）上直接算出决定胜负的**模型层结构量**（如各自最优导频下的字典离峰相干度 $\mu_{\max}$、杂波/干扰子空间有效秩与保留自由度、无噪可辨识雅可比最小奇异值 $\sigma_{\min}$）。
  - *本轮已验证反例 1*：`P-k-N2`（`td_n2_afdm_pilot_sweep.py`）算离峰相干度即见 `OFDM` 等间隔正交梳 $\mu_{\max}=0.505$ 优于 `AFDM` 模 Golomb 导频 $\mu_{\max}=0.581$，实测 `OFDM` 净胜 `5.91 pp`；
  - *本轮已验证反例 2*：`R15-H3`（`teardown-h.md`）中 `8×` 模拟去啁啾配齐各波形精确抽取滤波字典 + `RELAX` 后，`OFDM / SC-FDE / OTFS` 检出率 `80%–90%` 直接追平 `AFDM`（`80%–83%`）；
  - *本轮已验证反例 3*：`P1B-H2` 刚经 `out_p1c_h2_feas_4wf.json` 严格同多普勒五波形复测，`OTFS_2D` 可行率（`80%/70%`）与旁瓣（`ISL -22.78 dB`）追平并略超 `AFDM`（`80%/75%, -20.74 dB`）；
  - *本轮已验证正例*：`25-m03` 分离多径 `[0,k,16]`（$k\ge 3$）中，`DAFT` 零数据干扰导频子带可独立解耦双端相噪，而等开销 `UW-SC` 因长数据间隙维纳漂移失锁（落后 `57×–2874×`）。
  - **数值预检中只要任一老波形结构量追平或反超 `AFDM`，当场丢弃换题，不跑长仿真。**

### 2. 对等调优预算与同信道硬红线（防反向偏置）
1. **各波形导频与网格调优预算严格对等**：
   - 严禁只给 `AFDM` 细扫多档 $c_1$ 和多种导频布局，却只给 `OFDM` 或 `SC-FDE` 测 1 种弱配置！
   - 若给 `AFDM` 搜索了 $M$ 组（导频布局 × $2Nc_1$）配置，则对 `OFDM`（等间隔正交梳、子带分簇、交织编码）、`SC-FDE`（**必同时覆盖集中 `UW-SC`、多段均匀分块 `K×L PTRS`、`DFT-s-OFDM` 三类**）、`OTFS / Zak-OTFS`（**必扫帧长 $N$ 的合法二维因子分解 $M_d \times K_\nu$ 及脉冲/展宽导频**）每家均须投入对等的候选调优，各取实测最强配置对决，并同装对称的零先验数据泄漏白化器与相同外环迭代轮数。
2. **严格同信道、同多普勒、同后 `RRC` 能量与 `BW99`**：
   - 全部波形必须在完全同一批连续时间 `OSR=8 RRC` 多径多普勒信道种子上配对运行，整突发含 `CP/CPP` 与滤波拖尾的期望发射能量极差 `< 0.5%`、`BW99` 极差 `< 3%`。

### 3. 单一固定准入线 + 配对 95% 置信下界硬门（取消模糊区间）
设 `Best_Other = Best of {OFDM, SC-FDE, OTFS, Zak-OTFS}`（各自取调优后最强配置），候选问题只在满足以下对应账本的**单一固定门槛（看配对 95% 置信区间下界，不看点估计）**时才准标为 `[S档候选]`：
- **性能（SNR）账**：在相同目标误码/误帧率处，`ΔSNR = SNR(Best_Other) − SNR(AFDM)` 的配对 95% 置信区间下界 **`≥ +1.50 dB`**；
- **错误/漏检地板破壁账**：高 SNR 区 `p_other ≥ 10.0%`，且配对差 `p_other − 5.0 × p_afdm` 的 95% 置信区间下界 **`> 0`**；
- **等虚警检测率账**：同一独立校准集锁死虚警率下，`ΔPd = Pd(AFDM) − Pd(Best_Other)` 的配对 95% 置信区间下界 **`≥ +15.0 pp`**；
- **同精度实时算力账**：达到不低于 `Best_Other` 的精度（悬崖点差 `≤ 0.20 dB` 或 `Pd` 不输）下，同机单核耗时比 `T(Best_Other) / T(AFDM)` 几何均值的 95% 置信区间下界 **`≥ 10.0×`**。

### 4. 运行时限、顾问职责与落盘隔离
- 时限 `2.5–3` 小时（或独立快筛 `8` 个不同切口后收尾）；`gpt-6.2-sol`（`high`）每会话上限 `4` 次，专职替 `OFDM / SC-FDE / OTFS / Zak-OTFS` 挑漏掉的最强配置并核查代码公平性。
- 零新卡、零改历史卡片与旧脚本；`deinlab` 单任务 `≤ 8–12` 核（`OMP_NUM_THREADS=1`，临时目录 `/data/guoyikun/tmp/funnel_${R}_r15c/`，跑毕清理）；探针存 `ideas/r15/td_${R}_p1c_<slug>.py`，JSON 存 `ideas/r15/out_p1c_<slug>.json`（含 `_argv` 与 `_config`），汇总写入 `ideas/r15/teardown-$R-p1c.md`（严禁覆盖 `teardown-$R.md` 与 `teardown-$R-p1b.md`），追加日志至 `ideas/runs-$R.md` 并 `git commit -- ideas/`。

---

## 二、四路独立工作树的互斥战区与禁撞清单

| runner | 专属探索支点与具体要求 | 禁撞已死/已占清单（必先核对） |
|---|---|---|
| **`k`**<br>（`afdm-funnel-k`） | **支点 ①：环境物理几何本身的时延–多普勒耦合流形 $\nu = g(\tau)$ & 有限长带限相变分界验证**<br>1. **运动学耦合散射/运动干扰流形**（LEO 过顶、高铁走廊、双基地运动杂波/同频运动干扰源，多普勒与时延由几何余弦锁在斜脊/曲脊上）：测试下行多用户预编码 + 斜脊杂波/干扰零空间设计，或上行几何耦合散射低开销估计，实测 `AFDM` 斜率对齐相对四波形满配（含 `OFDM` 一维斜率/曲率扫描与矩形 `OTFS`）能否跨过上述固定算力账（`≥10×`）或性能账（`≥1.50 dB`）；<br>2. **有限长带限（`OSR=8 RRC`）跨波形可辨识相变分界猜想 + 数值验证**（给出清晰的自由度/条件数分界猜想并在 `≥ 3` 组分数色散工况做蒙特卡洛核验，**不要求在 3 小时内硬凑形式化充要定理证明**）。 | `k01+k02` 原单流接收设定；已死 `25-k03`、`P-k-N1`、`P-k-N2`（含 Golomb 导频补测已结案）、`P-k-N3`；右半场共性题 `P-k-B1 / B2` |
| **`h`**<br>（`afdm-funnel-h`） | **支点 ③：非酉前端/发射硬件约束与双色散信道耦合（严禁重踩 `R15-H1..H4`！）**<br>1. *注*：`R15-H3`（`Zhu TWC'26` 宽带 `8×` 模拟去啁啾低速 ADC）已在 `teardown-h.md` 实测证伪（精确抽取滤波字典 + `RELAX` 下四波形同达 `80%–90%`），且 `P1B-H2` 同多普勒五波形可行域刚在 `out_p1c_h2_feas_4wf.json` 证实被 `OTFS_2D` 追平，**这两条立即停做归档，不得重开**；<br>2. 自主搜寻**尚未被“精确物理字典 + RELAX / STAP / DFT-s-OFDM”拉平**的非酉收发硬件耦合切口（如：未知双色散信道下低比特量化/饱和限幅前端对多径导频与数据互调的结构性非对称、多用户多天线恒模/离散相位预编码与盲/半盲信道获取闭环耦合等）——每个新切口动笔前**必须先写 2 行对比 `R15-H1..H4` 与 `m_new2 / m_new3`，说明为什么不会被 `DFT-s-OFDM` 低峰均比或 `Probit / Bussgang` 精确似然直接追平**，再跑 3 分钟四波形结构预检。 | **严禁重碰 `R15-H1..H4`（含 `R15-H3` 模拟去啁啾！）**、`P1B-H1..H10`（含刚证伪跨波形独占的 `H2`）、`B1-G1..G7`、`26-h01`、`25-h02` |
| **`m`**<br>（`afdm-funnel-m`） | **支点 ②：稀疏可分离窗多径解耦 × 快变损伤追踪 & 时频双域同时局部擦除**<br>1. **时域突发脉冲 × 频域窄带强干扰（双域同时局部污染）下的未知双色散估计与检测**：单有时域脉冲 `SC-FDE` 可避开，单有频域窄带干扰 `OFDM` 可置零；检验双域同时局部污染 + 未知多径频偏时斜向 `AFDM` 是否占优——**关键防坑：二维 `OTFS / Zak-OTFS` 同样铺满时频全平面，且跨子载波交织编码 `BICM-OFDM` 也能分散局部擦除！3 分钟预检必须从第一秒起同跑 `Zak-OTFS + 交织编码 OFDM + 多段 UW/PTRS SC-FDE + Nassar 联合因子图`**，写清并实测对 `OTFS` 与交织编码 `OFDM` 是否仍有真实优势；<br>2. *关于 `P-m-03-Adj` 的诚实界定*：现有未知信道盲捕获下 `SC-FDE 4×38`（`42.2%`）显著优于 `AFDM`（`94.1%`），仅在有实质新盲捕获机制能反超全套 `UW-SC / PTRS-SC / Zak-OTFS` 时才花 15 分钟快检，否则直接跳过探索其他快时变相位/频偏耦合切口。 | 单域脉冲 `C3 / C8 / C11 / C13`；已死 `26-m01 / 26-m04 / m_new1..3 / C1 / C2 / C4 / C6 / C7 / C9` |
| **`g`**<br>（`afdm-funnel-g`） | **支点 ④：`(tx, rx)` 跨突发/跨天线斜率分集（Multi-Slope Chirp Intersection）& 非对称低复杂度终端收发共设计**<br>1. **跨重传/双突发/多天线正负斜率交汇消解欠定导频模糊（$\pm c_1$ 几何交集）**：单短包紧导频装不下完整 $L_{\max}(2k_{\max}+1)$ 保护窗且包间本振跳相（如 `G2B` 暴露的痛点）时，检验在两包/双流上切换不同啁啾斜率（如 $+c_1$ 与 $-c_1$）能否用窄保护窗分别观测正交斜投影 $u_1=+2Nc_1\tau+\nu$ 与 $u_2=-2Nc_1\tau+\nu$ 交汇解出连续 $(\tau,\nu)$——**3 分钟预检必给 `OTFS / Zak-OTFS` 同等开放“两包切换不同网格纵横比 $M_1\times K_1 \neq M_2\times K_2$”、给 `OFDM / SC-FDE` 开放跨包跳梳/多段 `PTRS` 对照**，若 `OTFS` 换网格同样解开则当场判死换题！<br>2. **其他 `(tx, rx)` 帧结构/预编码跨波形结构不对称切口**（严禁靠 $N=2^m$ 整数分解死角卡 `OTFS`，必须允许 `OTFS` 取合理 $M\times K$；必带时域带状 `Cholesky` 与 `Block-MMSE-THP` 拆台）。 | 已死 `25-g02`、`G3-ftn`、`G4-64qam-pa`、`G1B-fdd`、`P1B-K1..K3`、第 5 轮 `丢弃 18`（异构后啁啾跨基导频泄漏）；右半场共性题 `G2B / G3B` 原固定斜率设定 |

---

## 三、启动与中途纠偏口令

### A. 若会话尚未启动（直接粘贴新版启动口令）

- **`runner k`**（目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner k。启动第 15 轮 Phase 1C（2.5-3 小时左半场真 AFDM 占优探索专轮）。先完整阅读勘误修订后的 ideas/prompts/round-15c.md、ideas/FUNNEL.md 及本目录 teardown-k.md、teardown-k-p1b.md。严守零新卡、零改旧卡与不覆盖旧拆台文件边界，注意 0 存活是完全合法的诚实结果：在「支点 ①：环境物理几何时延–多普勒耦合流形 & 有限长带限跨波形相变分界猜想+数值验证（不硬凑充要定理证明）」内，每题先跑 ≤3 分钟四波形结构量数值预检，严格保证 AFDM、OFDM、SC-FDE（含 UW/分块PTRS/DFT-s）、OTFS/Zak-OTFS 导频与网格调优预算对等，按 round-15c.md 单一固定门槛与配对 95% 置信下界判定，请 gpt-6.2-sol（上限 4 次）替老波形挑最强反制配置。脚本与 JSON 存 ideas/r15/td_k_p1c_*.py / out_p1c_*.json，汇总写入 ideas/r15/teardown-k-p1c.md，git commit -- ideas/ 后退出。`

- **`runner h`**（目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner h。启动第 15 轮 Phase 1C（2.5-3 小时左半场真 AFDM 占优探索专轮）。先完整阅读勘误修订后的 ideas/prompts/round-15c.md、ideas/FUNNEL.md 及本目录 teardown-h.md、teardown-h-p1b.md。注意 R15-H1..H4（含 R15-H3 模拟去啁啾低速 ADC）与 H2 同多普勒四波形可行域均已证伪封存，严禁重做；0 存活完全合法：在「支点 ③：尚未被精确物理字典+RELAX/DFT-s-OFDM/Probit 拉平的非酉前端或发射硬件约束与双色散耦合」内自主选切口，每题先写 2 行与 R15-H1..H4 的物理区别并跑 ≤3 分钟四波形对等调优数值预检，按单一固定门槛与配对 95% 置信下界判定，请 gpt-6.2-sol（上限 4 次）替老波形挑最强反制配置。脚本与 JSON 存 ideas/r15/td_h_p1c_*.py / out_p1c_*.json，汇总写入 ideas/r15/teardown-h-p1c.md，git commit -- ideas/ 后退出。`

- **`runner m`**（目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner m。启动第 15 轮 Phase 1C（2.5-3 小时左半场真 AFDM 占优探索专轮）。先完整阅读勘误修订后的 ideas/prompts/round-15c.md、ideas/FUNNEL.md，并只读参考 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/r15/teardown-m.md 与 teardown-m-p1b.md。注意 0 存活完全合法，且 P-m-03-Adj 目前未知信道盲捕获下 SC-FDE (42.2%) 优于 AFDM (94.1%) 不算左半场存量：在「支点 ②：时域脉冲×频域窄带双域同时局部污染下的未知双色散估计检测（首轮预检必同跑 Zak-OTFS + 交织编码 BICM-OFDM + 多段 UW/PTRS SC-FDE + Nassar 联合因子图）及稀疏窗多径解耦×快变损伤追踪」内，严格保证四波形导频调优预算对等，按单一固定门槛与配对 95% 置信下界判定，请 gpt-6.2-sol（上限 4 次）替老波形挑最强反制配置。脚本与 JSON 存 ideas/r15/td_m_p1c_*.py / out_p1c_*.json，汇总写入 ideas/r15/teardown-m-p1c.md，git commit -- ideas/ 后退出。`

- **`runner g`**（目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`；注：你的上半场与 1B 产物在主目录 `my-vault` 的 `ideas/r15/teardown-g*.md`，可只读参考）：
  `你是 runner g。启动第 15 轮 Phase 1C（2.5-3 小时左半场真 AFDM 占优探索专轮）。先完整阅读勘误修订后的 ideas/prompts/round-15c.md、ideas/FUNNEL.md，并只读参考 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/r15/teardown-g.md 与 teardown-g-p1b.md。严格在本独立工作树 afdm-funnel-g 内落盘，零新卡、零改旧卡，注意 0 存活是完全合法的诚实结果：在你负责的「支点 ④：(tx, rx) 跨重传/双突发/多天线正负斜率交汇消解欠定导频模糊（±c1 几何交集，3 分钟预检必给 OTFS/Zak-OTFS 同等开放跨包切换不同网格纵横比 M1×K1 != M2×K2、给 OFDM/SC-FDE 开放跨包跳梳与多段 PTRS 对照）及其他不依赖 N=2^m 分解死角的 (tx, rx) 跨波形结构不对称切口」内，每题先跑 ≤3 分钟四波形对等调优数值预检，按 round-15c.md 单一固定门槛与配对 95% 置信下界判定，请 gpt-6.2-sol（上限 4 次）替老波形挑最强反制配置。脚本与 JSON 存 ideas/r15/td_g_p1c_*.py / out_p1c_*.json，汇总写入 ideas/r15/teardown-g-p1c.md，git commit -- ideas/ 后退出。`

### B. 若会话已经在跑（直接把对应这一段贴进正在运行的对话框即可中途纠偏，无需强杀重启）

- **发给已开跑的 `runner h`（最紧急，防它重踩 `R15-H3` 模拟去啁啾）**：
  `中途规则勘误更新：ideas/prompts/round-15c.md 已重写同步到你当前工作树，请立即重新 read 一遍 ideas/prompts/round-15c.md 并严格按新版执行！重点变更：① 你刚跑完的 out_p1c_h2_feas_4wf.json 已证实同多普勒下 OTFS_2D 可行率与旁瓣追平 AFDM，直接把 H2 记为跨波形证伪归档；② 立刻停掉原口令里的「宽带模拟去啁啾低速 ADC」方向——你上半场 teardown-h.md 的 R15-H3 已经测过 8× 去啁啾下四波形同达 80-90%，严禁重碰 R15-H1..H4；③ 后续新切口必须对四波形投入对等的导频/网格调优预算（SC-FDE 必含 UW/分块PTRS/DFT-s，OTFS 必扫合法网格分解），先跑 ≤3 分钟结构量数值预检，按新版单一固定门槛+配对 95% CI 下界判定；0 存活完全合法，被老波形追平如实记死因即可。`

- **发给已开跑的 `runner k`（若已开跑）**：
  `中途规则勘误更新：ideas/prompts/round-15c.md 已重写同步到你当前工作树，请立即重新 read 一遍 ideas/prompts/round-15c.md 并按新版执行：① 分界方向改为「可检验分界猜想 + 有限长 OSR=8 RRC 数值相变验证」，不要花时间硬凑形式化充要定理证明；② 删掉纯文字三向破缺故事，改为动笔前先跑 ≤3 分钟四波形结构量数值预检，且四波形导频/网格搜索预算必须对等（SC-FDE 必含 UW/分块PTRS/DFT-s，OTFS/Zak-OTFS 必扫合法二维网格）；③ 统一按新版单一固定门槛 + 配对 95% CI 下界判定（如 k01+k02 检出率 +8.75 pp < 15 pp 不达检测率账，只能看 ≥10× 算力账）；0 存活完全合法，如实记死因即可。`

- **发给已开跑的 `runner m`（若已开跑）**：
  `中途规则勘误更新：ideas/prompts/round-15c.md 已重写同步到你当前工作树，请立即重新 read 一遍 ideas/prompts/round-15c.md 并按新版执行：① 修正 P-m-03-Adj 口径——未知信道盲捕获下目前单载波 42.2% 优于 AFDM 94.1%，除非有新盲捕获机制能反超全套 UW-SC/PTRS-SC 与 Zak-OTFS，否则 15 分钟内判死跳过；② 做「时域脉冲 × 频域窄带干扰同时存在」题时，因 OTFS/Zak-OTFS 同样铺满时频且交织编码 OFDM 也能分散局部擦除，3 分钟预检必须从头同跑 Zak-OTFS + 交织编码 BICM-OFDM + 多段 UW/PTRS SC-FDE + Nassar 联合因子图，保证四波形导频/网格调优预算对等；③ 按新版单一固定门槛 + 配对 95% CI 下界判定，0 存活完全合法。`
