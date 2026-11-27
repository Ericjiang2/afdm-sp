# 第 17 轮（左半场纯血补强专轮）：修补两处漏斗机制偏差，深挖 `[S+ / S-（硬赢 OFDM + 对 OTFS 64开）]`

> **为什么开本专轮（复盘第 16 轮暴露的两处漏斗机制偏差，Eric 2026-11-27 10:01 拍板修正）**：
> 1. **修正偏差 ①（解除左半场第一级对 `AFDM` 的单边捆手脚，开放 $(c_1, c_2)$ 双参数与专属收发构造对等打擂）**：
>    - 第 15C/16 轮前半程把“第一级零新设计”机械套进左半场，变成拿**没做专属设计的裸单脉冲 `AFDM_imp`（且全程锁死 $c_2 = 0$）**去打 `Sol` 替 `OTFS / SC-FDE / OFDM` 精心定制的非均匀多簇、恒模 `CP-ZC` 块导频与旋转晶格，一输就判死，连给 `AFDM` 设计专属 `(tx, rx)` 的机会都没给。
>    - **新规**：左半场探索从第一分钟起，**允许并要求 `AFDM` 动用其区别于固定网格 `OTFS` 的完整原生自由度**——特别是 **$(c_1, c_2)$ 双啁啾参数联合设计（$c_1$ 调控时延–多普勒倾角坍缩，$c_2 \neq 0$ 在不扩大信道支撑的前提下连续调控跨符号二次相位耦合、未编码全分集、发射 `PAPR` 与多流/多用户相位解耦）+ `AFDM` 专属导频图样 + 一维三对角/带状快速接收机**；同时给 `OFDM / SC-FDE / OTFS / Zak-OTFS` 分配**严格相等的候选配置调优次数 $M$**（如两边各调优 `4–6` 套最强配置），在“定制 `AFDM` vs 定制老波形”的公平对称条件下核验 `[S+ / S-]`！
> 2. **修正偏差 ②（彻底砍掉“右半场保底退路”，严禁 20 分钟速刷负例溜号）**：
>    - 第 16 轮挂了“若左半场 `0` 过线即可转做右半场王牌题”，导致 `g`（17 分钟）与 `m`（36 分钟）速刷朴素负例后立刻切去好拿分的右半场。
>    - **新规**：**本专轮 100% 锁定左半场，零右半场退路！** 每一个候选切口在判死淘汰前，必须写明并实测：**「Step A：朴素 `AFDM` 为何被老波形追平 → Step B：针对该病根动用 $(c_1, c_2)$ 双参数或啁啾一维带状结构做了哪 `≥ 2` 种专属 `(tx, rx)` 改造 → Step C：改造后与对等调优预算的老波形配对实测读数」**。只有真把专属自由度用尽仍不过 `[S-]` 才准淘汰换下一题；全程若诚实测透仍 `0` 存活，直接交高质量死因报告收尾，绝不转做右半场题。

规则栈：本文件 > [`../FUNNEL.md`](../FUNNEL.md)（11-27 修正版） > [`round-16.md`](round-16.md)。

---

## 一、准入硬标尺（保持昨晚拍板的 `[S+ / S-]` 两级标准零放水）

- **最高档 `[S+ · 四家全胜]`**：`AFDM` 专属方案同时净赢对等调优后的 `{OFDM, SC-FDE, OTFS, Zak-OTFS}` 四家跨过固定主账本门槛（配对 95% CI 下界）。
- **保底准入档 `[S- · 硬赢 OFDM + 对 OTFS 整体 64 开]`（必须同时过门 A 与门 B，配对 95% CI 下界）**：
  1. **门 A（硬赢满配 `OFDM`）**：`ΔSNR ≥ +1.50 dB`，或高 SNR 地板 `p_OFDM ≥ 10.0%` 且 `p_OFDM − 5.0×p_AFDM > 0`，或同 `1%` 期望虚警校准 `ΔPd ≥ +15.0 pp`，或主精度不输（差 `≤ 0.20 dB / 2.0 pp`）下单核耗时比 **`≥ 10.0×`**；
  2. **门 B（对满配 `OTFS / Zak-OTFS` 整体 `64开`，严禁 `55开` 换皮）**：核心工作区多工况平均主精度**整体不输**（均值亏损 `≤ 0.20 dB` 或 `ΔPd ≥ -2.0 pp`，核心工况胜平率 `≥ 60%`；同台跑满配 `SC-FDE / DFT-s-OFDM` 交代适用边界，不得被简单 `DFT-s-OFDM` 全维度无代价反超），**且至少命中 1 项配对 95% CI 不跨零的硬净赢**：核心区主精度净赢（`ΔSNR ≥ +0.75 dB` 或 `p_OTFS ≥ 5%` 下误差降 `≥ 2.0×` 或 `ΔPd ≥ +8.0 pp`），**或** 同精度单帧单核耗时快 **`≥ 3.0×`**，**或** 省导频+保护开销 **`≥ 15%`**（同码率同误码净吞吐高 `≥ 12%`）、后 `RRC` `BW99` 窄 **`≥ 15%`**、99.9% 发射 `PAPR` 低 **`≥ 2.0 dB`**、或同分集跨块时延短 **`≥ 4×`**。

---

## 二、硬件防烫与隔离死规（MacBook Air 必守！）

1. **本机零重算（刚抓过的发热红线）**：本机是无风扇 MacBook Air，**严禁在本机运行任何耗时 `> 3` 秒的 Python 计算（含临时 `python -c` 探针、特征分解、`evolve_cli` 本地重算）**；任何本机 `< 3` 秒极小脚本命令最前端必须显式挂齐 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`；一切数值预检、调优与蒙特卡洛 **100% 放上 `deinlab`**（`/home/guoyikun/.conda/envs/AFDM/bin/python`，必设上述四个 `=1` 单线程开关，单 runner `≤ 12` 核，远端目录 `/data/guoyikun/tmp/funnel_${R}_r17/`，跑毕清理）。
2. **工作树隔离与顾问预算**：各在独立工作树 `afdm-funnel-{k,g,h,m}` 落盘 `ideas/r17/`（不改 `r15 / r16 / cards` 历史文件）；`codex exec -m gpt-6.2-sol --sandbox read-only` 每会话上限 `≤ 5` 次（专职挑双方调优预算不对等、漏掉的老波形同自由度反制如 `OTFS` 预相位/旋转晶格、以及因果混杂）。
3. **两步直通结构（`4–6` 小时专轮）**：
   - **前半程（深挖认证，无右半场退路）**：深挖 `2–4` 个切口（每切口做满 `Step A 病根 → Step B ≥2 套 AFDM 专属 (c1,c2)/(tx,rx) 构造 → Step C 四波形对等调优配对实测`），写入 `ideas/r17/teardown-${R}-r17.md`；
   - **后半程（若挖出稳过 `[S+/S-]` 的真题，原地直进 Phase 2 闭环）**：锁 `H-${R}-<slug>.py` 评测台 → 补 1 条零拟合参数闭式解析支点 → 单次封存 `--mode holdout` + `Sol` 双拍对抗终审，写入 `ideas/r17/stage2-${R}-<slug>.md`；若深挖到底仍 `0` 过线，不凑数、不切右半场，经 `Sol` 复核死因无误后如实提交 `teardown-${R}-r17.md` 收工。

---

## 三、四路纯左半场正交战区（直击此前未测的真自由度盲区）

| runner | 专属左半场深挖战区 | 必测的对等老波形反制（防假赢） |
|---|---|---|
| **`k`**<br>`afdm-funnel-k` | **【头号必做】`k01+k02` 纯波形因果归因正交实验 + 在线曲脊选秩闭环，外加 1–2 个斜脊耦合新切口**<br>1. **直击昨晚 `Sol` Call 6 唯一核心悬念**：固定已锁评测台 `H-k-curved-bistatic-isac.py` 物理信道，构造严格的 **`(发射波形: Ridge-AFDM c1=μ0/2N vs 等带宽 OFDM-216 c1=0 vs SubZak-27×8) × (接收第一阶段初估: 非二次逐块/跨块窄带 BEM 追踪 vs 二次 κ 搜索)` 正交对照**（严格配平 2–4 遍曲脊 `Slepian` 重追踪迭代预算与单核计时！），量出：当 `OFDM` 也拥有非二次初估后，`Ridge-AFDM` 靠 $2Nc_1=\mu_0$ 将单块杂波压入三对角带，究竟赢在**盲初估可辨识度（`Pd / SER`）**还是赢在**达到同检出率的单核计算耗时（`≥3×–10×`）**？<br>2. **接入第 16 轮闭式 Slepian 相变律的在线无真值选秩 $\hat K \in \{4,5,6,7\}$**，检验能否在不抬高空场景虚警下打通强宽带 `DevR2` 检出，并在全新封存种子上完成 `Sol` 双拍终审闭环；<br>3. 若时间充裕，再深挖 1 个斜脊/走廊耦合 `(c1, c2)` 联合设计新切口。 | 必给 `OFDM-216` 与 `SubZak-27×8` 配上与 `AFDM` 同等灵活度的**非二次逐块局部多普勒/BEM 初估 + 同遍数曲脊重追踪**（严禁再让外族卡在 11 点二次曲率初始化上！） |
| **`g`**<br>`afdm-funnel-g` | **$(c_1, c_2)$ 双啁啾自由度战区 ①：$c_2 \neq 0$ 二次预啁啾在短包未编码/轻编码分集、低 `PAPR` 功放与索引/子块调制中的结构红利**<br>昨晚 8 切口全把 $c_2$ 设为 `0`。本轮专门动用 `OTFS` 固定网格后不具备的**连续/无理数/逐子块 $c_2$ 相位自由度**（参考 `Bemani TWC'23` 全分集条件、`Tao/Yin/Sui` 预啁啾 `AFDM-IM / PAPR`）：<br>1. 探索分数多径多普勒下，通过联合设计 $(c_1, c_2)$（含逐子块/逐符号定制 $c_2$ 相位序列 + `evolve_cli.py`）在**单遍或 2 步轻量接收（不挂 4 轮长 LDPC 抹平分集）+ 过采样 `Rapp PA` 削峰**下，能否同时压低数据+导频整帧 `PAPR`（`≥ 2 dB`）并保住高 SNR 分集斜率；<br>2. 探索 `AFDM` 索引调制 / 稀疏激活子载波 + $c_2$ 相位解耦对决 `OTFS-IM` 与 `OFDM-IM`。 | 必给 `OTFS / Zak-OTFS` 分配同等次数的**二维网格搜索 + 发射前酉相位旋转/Walsh-Hadamard 预编码 + `CP-ZC` 导频**对等调优预算，给 `SC-FDE` 配 `DFT-s-OFDM + PTRS` |
| **`m`**<br>`afdm-funnel-m` | **$(c_1, c_2)$ 双啁啾自由度战区 ②：多用户/双流异构 $(c_{1,u}, c_{2,u})$ 相位斜率正交码本 & 通感同频干扰分离**<br>昨晚 `S7` 只用了同斜率 $c_1$ 分簇，被同分簇 `OFDM_3NonUnif` 追平。本轮开放**不同用户/不同天线流分配互异 $(c_{1,u}, c_{2,u})$ 啁啾参数对**（利用 $|\langle \mathbf{a}_{c_{1,u},c_{2,u}}, \mathbf{a}_{c_{1,v},c_{2,v}}\rangle| = N^{-1/2}$ 全频带恒包络互不相干性，结合 `evolve_cli.py` 优选参数集与导频掩码）：<br>1. 测试高多普勒深选衰多用户异步/免授权上行或双基地通感多发站正交波形分离，检验异构 $(c_{1,u}, c_{2,u})$ 相比同斜率 `AFDM` 与分簇 `OFDM` 能否消除频率选衰死角（过门 A）且比二维 `Zak-OTFS` 在碰撞率、峰均比或接收复杂度上稳拿 `64开`（过门 B）；<br>2. 严查第 5 轮 `丢弃 18` 跨基导频泄漏坑——必须用定制干扰抵消或正交子空间设计真正解决跨斜率泄漏，解决不了如实判死。 | 必给 `OFDM` 开放多根 `ZC-CDMA / OCDM` 扩频多址对照，给 `Zak-OTFS` 开放多网格/旋转晶格多址对照，给 `SC-FDE` 开放 `IFDMA / DFT-s` 跳频对照 |
| **`h`**<br>`afdm-funnel-h` | **一维三对角/窄带带状结构战区 ③：分数多普勒高阶 `16/64-QAM` 下 `AFDM` 一维紧凑带状非线性检测 vs 二维 `Zak-OTFS` 块循环耦合的实时算力 `64开`**<br>0. 启动先用 2 分钟将本工作树第 16 轮未提交的 `ideas/r16/*b1*` 与 `runs-h.md` 显式归档提交（`git commit`），不混入第 17 轮；<br>1. 昨晚 `m` 在 `S6` 只测了 $N \le 180$ 线性 `CG-LMMSE`（两者同为 FFT `1.0×`）。但在 $N=256, 512$、分数时延+分数多普勒、高阶 `16/64-QAM` **非线性软检测（如带状树搜索 `K-Best`、带状 Cholesky `EP / VAMP`、流式滑窗马尔可夫检测）**下，`AFDM` 信道矩阵沿一维周期带聚集，而 `Zak-OTFS` 是二维块循环矩阵（二维邻域耦合度 $B_d \times B_\nu$ 树宽呈平方膨胀）！实测在严格同误码率（瀑布点差 `≤ 0.20 dB`）下，`AFDM` 定制一维稀疏带状 `EP/K-Best`（配合 $(c_1, c_2)$ 调优压窄有效带宽）能否同时硬赢 `OFDM`（高多普勒地板 `≥5×` 或耗时 `≥10×`）且在单核耗时上快过最快定制二维 `Zak-OTFS` 检测器 **`≥ 3.0×`**！ | 必给 `Zak-OTFS` 实现对等优化的**二维稀疏消息传递 `2D-MP / 2D-EP / 频域预条件 VAMP`**（严禁故意给 `Zak-OTFS` 用 $O(N^3)$ 稠密求逆凑假加速比！），给 `SC-FDE` 测时域带状 `EP/MMSE-DFE` 划清多载波频分复用/通感适用边界 |

---

## 四、一键复制启动口令（可按需单开最稳的 `k`，或四路齐开）

### 1. `runner k`（最推荐优先跑：30–60 分钟即可摸清 `k01+k02` 纯波形归因底牌并闭环）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`
```text
你是 runner k。现在启动第 17 轮（左半场纯血补强专轮，4–6 小时，100% 锁定左半场，零右半场退路）。先完整阅读 ideas/prompts/round-17-left.md、更新后的 ideas/FUNNEL.md 及你上一轮的 ideas/r16/stage2-k-curved-bistatic-isac.md 与 sol_r16_call6_kill_defense.md。严守硬件防烫死规：本机严禁运行任何 >3 秒的 Python 计算，任何本机极小命令前必加 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1，一切探针与仿真 100% 放 deinlab（≤12 核，/data/guoyikun/tmp/funnel_k_r17/），gpt-6.2-sol 全轮上限 ≤5 次，产物全部落盘 ideas/r17/（严禁改动 r16 封存文件）：
1. 头号任务（直击 Sol Call 6 核心未决点 P_1 & P_3）：在全新开发集种子上构造严格的「(发射波形: Ridge-AFDM c1=μ0/2N vs 等带宽 OFDM-216 c1=0 vs SubZak-27×8) × (第一阶段盲初估: 允许非二次弯曲的逐块/跨块窄带 BEM 追踪 vs 11 点二次搜索)」正交对照，严格配平 2–4 遍曲脊 Slepian 重追踪与符号重均衡预算及单核计时，查清当 OFDM/SubZak 也装上非二次盲初估后，Ridge-AFDM 的单块三对角杂波压缩究竟在盲初估检出率/SER 还是在同检出率单核耗时（≥3×–10×）上保持真跨波形净赢；
2. 同时接入你第 16 轮闭式 Slepian 相变公式的在线无真值残余展宽选秩 K_hat ∈ {4,5,6,7}（检验能否在不抬高空校准虚警下修复强宽带曲率工况失检）并补齐可核验的五倍通信误码差配对置信区间导出；
3. 若正交对照坐实 [S+/S-] 跨波形因果净赢，冻结新评测脚本与预注册判据，在全新独立封存种子（+100000）上单次终验并过 Sol 双拍对抗终审，写入 ideas/r17/stage2-k-curved-causal-closure.md；若剩余时间充裕，再按 round-17-left.md 测 1 个斜脊耦合 (c1, c2) 双参数新切口写入 ideas/r17/teardown-k-r17.md，清理远端临时目录并 git commit -- ideas/ 后退出。
```

### 2. `runner g`（$(c_1, c_2)$ 双啁啾分集 / 低 `PAPR` / 索引调制战区）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`
```text
你是 runner g。现在启动第 17 轮（左半场纯血补强专轮，4–6 小时，100% 锁定左半场，彻底取消右半场保底退路！）。先完整阅读 ideas/prompts/round-17-left.md 与更新后的 ideas/FUNNEL.md。严守本机防烫死规：本机严禁运行任何 >3 秒 Python 计算（含 evolve_cli 评估函数必须通过 ssh 在 deinlab 跑），任何本机小命令前必加 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1，数值计算 100% 放 deinlab（≤12 核，/data/guoyikun/tmp/funnel_g_r17/），gpt-6.2-sol 全轮上限 ≤5 次，产物存 ideas/r17/：
1. 针对你上一轮 8 切口全程锁死 c2=0 且仅测朴素 AFDM_imp 的盲区，本轮专门深挖 OTFS 固定网格不具备的「(c1, c2) 双啁啾自由度（c2 != 0 无理数/分数/逐子块二次相位预啁啾）+ 专属导频/索引调制」，重点检验短包未编码/轻编码分集区 + 过采样 Rapp PA 削峰约束下的高 SNR 分集/误码与整帧 PAPR 联合优势（及 AFDM-IM vs OTFS-IM / OFDM-IM）；
2. 每切口判死前必须完成「Step A 朴素失败诊断 → Step B ≥2 套动用 (c1,c2) 的专属 (tx,rx) 改造（离散序列/相位调 evolve_cli.py） → Step C 与投入严格相等调优次数 M 的定制 OFDM / DFT-s+PTRS / CP-ZC+酉预编码 OTFS 配对实测」，写入 ideas/r17/teardown-g-r17.md；
3. 一旦挖出稳过 [S+/S-]（硬赢 OFDM + 对 OTFS 整体 64开）的真题，原地直进 Phase 2（锁 H-g-<slug>.py → 零拟合参数闭式支点 → 单次封存 holdout + Sol 双拍终审，写 stage2-g-<slug>.md）；若深挖到底仍 0 过线，经 Sol 核实无误杀后如实交死因报告并 git commit -- ideas/ 退出，绝不转做右半场题。
```

### 3. `runner m`（异构 $(c_{1,u}, c_{2,u})$ 多用户/通感码本分离战区）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`
```text
你是 runner m。现在启动第 17 轮（左半场纯血补强专轮，4–6 小时，100% 锁定左半场，彻底取消右半场保底退路！）。先完整阅读 ideas/prompts/round-17-left.md 与更新后的 ideas/FUNNEL.md。严守本机防烫死规：本机严禁运行任何 >3 秒 Python 计算（含临时 python -c 探针与 evolve_cli 评估），任何本机小命令前必加 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1，全部数值计算 100% 放 deinlab（≤12 核，/data/guoyikun/tmp/funnel_m_r17/），gpt-6.2-sol 全轮上限 ≤5 次，产物存 ideas/r17/：
1. 针对上一轮 S7 仅用同斜率 c1 分簇被同分簇 OFDM 追平的根因，本轮专门深挖「多用户/多发站异构 (c_{1,u}, c_{2,u}) 双啁啾斜率–二次相位联合码本与跨基干扰结构化消除」（高多普勒深频率选衰异步上行或双基地多发站通感分离），每切口必走满「Step A 病根（含跨斜率泄漏定量分析）→ Step B ≥2 套动用 (c_{1,u}, c_{2,u}) + 联合检测的专属 (tx,rx) 设计（参数集用 evolve_cli.py 优化）→ Step C 与等调优次数 M 的 ZC-CDMA/OCDM OFDM、多网格/旋转晶格 Zak-OTFS、跳频 DFT-s 对决」，写入 ideas/r17/teardown-m-r17.md；
2. 若挖出稳过 [S+/S-] 真题，原地直进 Phase 2（锁评测台 → 零拟合参数闭式支点 → 单次封存 holdout + Sol 双拍终审，写 stage2-m-<slug>.md）；若深挖到底仍 0 过线，经 Sol 核实无误杀后如实交死因报告并 git commit -- ideas/ 退出，绝不转做右半场题。
```

### 4. `runner h`（高阶调制分数多普勒下 `AFDM` 一维紧凑带状非线性检测 vs 二维 `Zak-OTFS` 实时算力 `64开` 战区）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`
```text
你是 runner h。现在启动第 17 轮（左半场纯血补强专轮，4–6 小时，100% 锁定左半场，彻底取消右半场保底退路！）。严守本机防烫死规：本机严禁运行任何 >3 秒 Python 计算（含临时 python -c 探针！），任何本机小命令前必加 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1，全部数值计算 100% 放 deinlab（≤12 核，/data/guoyikun/tmp/funnel_h_r17/），gpt-6.2-sol 全轮上限 ≤5 次：
0. 若本工作树仍有上一轮未提交的 ideas/r16/*b1* 与 runs-h.md，先用 1 分钟显式归档提交（git add ideas/r16/ ideas/runs-h.md && git commit -m "ideas(r16): archive runner h P-k-B1 Phase 2 and Sol REVISE controls" -- ideas/r16/ ideas/runs-h.md），再完整阅读同步后的 ideas/prompts/round-17-left.md 与 ideas/FUNNEL.md（若尚未同步，从 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/ 只读参考）；
1. 本轮深挖「N=256/512 分数时延+分数多普勒 + 高阶 16/64-QAM 非线性检测下，AFDM 一维周期窄带耦合结构（定制一维带状树搜索 K-Best / 带状 Cholesky EP / 流式马尔可夫检测 + (c1,c2) 调优）相对二维块循环耦合 Zak-OTFS 的同精度实时算力 64开优势（目标：硬赢高多普勒 OFDM 地板 ≥5× 或耗时 ≥10×，且在瀑布点精度差 ≤0.20 dB 下比对等优化的稀疏 2D-EP / 2D-MP / 频域预条件 VAMP Zak-OTFS 单核快 ≥3.0×，严禁给 Zak 用稠密 O(N^3) 凑数！）」，每切口必走满 Step A→B→C 写入 ideas/r17/teardown-h-r17.md；
2. 若挖出稳过 [S+/S-] 真题，原地直进 Phase 2（锁评测台 → 零拟合参数闭式支点 → 单次封存 holdout + Sol 双拍终审，写 stage2-h-<slug>.md）；若深挖到底仍 0 过线，经 Sol 核实无误杀后如实交死因报告并 git commit -- ideas/ 退出，绝不转做右半场题。
```
