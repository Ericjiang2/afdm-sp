# 同家族兜底初查（gemini-4-hydrogen-high，2026-11-25，仅供初查不放行）

正在读取审稿口径、待审卡片与实测探针代码。
正在读取探针脚本剩余部分与领域文献参考清单。
正在按算子与领域双路检索最新相关文献。
正在读取本地文献地图并联网检索跨体制与 AFDM-ISAC 相关文献。
正在检查本地论文缓存并补充检索恒模等式约束与 AFDM-ISAC 精确查新。
正在检查本地缓存的全文 PDF 文本并检索 OTFS/MIMO 恒模符号级通感先例。
正在查找本地缓存文献全文、检索跨体制精确子流形先例并运行归档探针核验实测数字。
正在读取本地缓存文献摘要与标题以核对全文细节。
正在核对 `liu26_mu_mimo_afdm.txt` 与检索恒模等式子流形预编码的准确先例。
正在核对已缓存的 AFDM-ISAC 论文关键章节与仿真设定。
正在核对 AFDM-ISAC 综述与脉冲成形 AFDM 论文缓存全文，并检查本地 Python 可用性。
正在核查跨体制等式子流形约束先例及锚点论文参数出处。
对 [I-20261125-h01.md](file:///Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-h01.md) 及配套探针 [h_probe_h01_submanifold_isac.py](file:///Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation/ideas/probes/h_probe_h01_submanifold_isac.py) 的第 6 步初筛审查如下（注：本环境内 `/opt/anaconda3/bin/python` 受沙盒权限限制且默认 `python3` 无 `numpy`，以下对机制、正负号、维度与公平性的核查依据探针源码与数学推导完成，实测数值转引自卡片报告，尚未在本会话重跑验证）。

- 一句话结论：**值得进 L2 仿真（1b）**

- 固有重要性（抛开先例）：**高** — 针对多用户下行恒模 `MIMO AFDM-ISAC` 中“离散网格四次模糊函数惩罚压垮通信安全裕度”与“目标方向随随机数据起伏抬高连续离网多普勒旁瓣”这一核心双目标冲突，用等式子流形解耦与仿射多径去相关给出清晰几何边界（$N_t - 2 \ge 2K$），问题痛点与结构完整度均达到 *IEEE TWC / TCOM* 正刊门槛。
  > 价值判断依据：目前卡在 `Li TWC'25 / TVT'25` 的环面 `ALM-RCG`（压制宽区域时通信出现 `>1e-3` BER 平层且离网旁瓣受随机起伏制约）与 `Liu & Schober arXiv:2607.05119` 的线性 `WMMSE-MM`（高峰均比且恒模截幅后通信、感知双双恶化）；最朴素的“空间正交补通信 SLP + 目标啁啾叠加再恒模截幅”与“去掉目标等式仅做恒模环面”在探针口径下分别卡在高误码率或 `30+ dB` 感知暴跌；本质是把目标方向复波形从软约束惩罚项改为硬等式子流形，让剩余 $(N_t-2)$ 维光滑自由度全部服务通信相长干涉，并借助 `AFDM` 分离多径以避免有限恒模幅度下的深衰落撞墙。如需通俗复盘，可回复「白话」。

- 白话 + 一个类比（3–5 句）
  基站多根天线要同时干两件事：发射端每根天线每时刻幅度必须锁死恒定（不让功放失真），一面让多个高速移动用户不用做复杂信道均衡就能直接判别通信符号，一面朝雷达目标打出一束能把旁边弱小目标从强目标旁瓣里看清的探测波。旧办法是在整个发射相位空间上拿“罚分项”去按住近百个整数距离–多普勒格子，结果罚分和通信安全边距互相打架，不仅把通信逼出高误码地板，目标方向上的探测波还跟着通信数据逐块乱跳，整数格点缝隙照样鼓出旁瓣淹没弱目标。这张卡干脆反过来定规矩：每时刻强制规定目标方向上的天线合成信号必须严格等于一条事先定死的标准单啁啾波（占掉每时刻 $N_t$ 根天线相位中的 2 个实自由度），再用剩下的 $N_t-2$ 维光滑子流形专心把通信符号推进安全区，同时靠 `AFDM` 把同一用户的多条回声径错开，不让有限的天线能量在衰落坑里撞墙。

- 最接近的工作（≥5 篇，每篇一句，带链接或编号，注明读了全文还是摘要）
  1. `Rang Liu, Ming Li, A. L. Swindlehurst, N. Franchi & R. Schober, "Multiuser MIMO-AFDM Beamforming for ISAC in Doubly Dispersive Channels," arXiv:2607.05119, Jul. 2026`（**已读缓存全文主要章节** `liu26_mu_mimo_afdm.txt`）：唯一一篇多用户下行 `MIMO-AFDM ISAC` 波束成形，用块级 `WMMSE-MM` 满足平均扇区照射功率，但无恒模约束（高峰均比）、需用户端做 $N\times N$ 块均衡且未抑制距离–多普勒旁瓣。
  2. `Peishi Li, Ming Li, Rang Liu, Qian Liu & A. L. Swindlehurst, "MIMO-OFDM ISAC Waveform Design for Range-Doppler Sidelobe Suppression," IEEE TWC, 2025`（`10.1109/twc.2024.3503605`）及低复杂度版 `IEEE TVT, 2025`（`10.1109/tvt.2025.3570381`）（**仅读联网检索摘要与综述**）：在静态 `MIMO-OFDM` 环面上用 `MM-ADMM / ALM-RCG` 惩罚离散整数网格四次模糊函数，忽略双色散快时间多普勒且允许目标方向波形随数据块随机起伏，造成宽抑制区通信平层与连续离网多普勒旁瓣。
  3. `Shuntian Tang, Zesong Fei, Xinyi Wang, Dongkai Zhou, Zhiqiang Wei & C. Masouros, "A Novel Symbol Level Precoding based AFDM Transmission Framework" (IEEE TWC 2026 / arXiv:2508.12215)`（`10.1109/twc.2026.3692638`）及 `arXiv:2609.09644`（**已读缓存全文摘要、引言与 Table I/Sec. V** `tang26_slp_afdm.txt`）：仅研究单天线 SISO 纯通信下的总功率球约束 AFDM 符号级预编码，无多用户空域多天线、无逐天线恒模约束与雷达感知。
  4. `Peishi Li, Rang Liu, Qian Liu & Ming Li, "Delay-Doppler Sensing Performance Analysis for MIMO-OFDM ISAC Systems," arXiv:2609.00559, Sep. 2026`（**仅读联网检索摘要**）：严格证明静态多流 `MIMO-OFDM ISAC` 下即使单流用恒模符号（如 QPSK），多流叠加仍在目标方向产生随机起伏从而形成匹配滤波旁瓣地板（倒数滤波则放大噪声），但仅做二阶矩分析而未提出双色散恒模预编码算法。
  5. `Rang Liu, Ming Li, Qian Liu & A. L. Swindlehurst, "Dual-Functional Radar-Communication Waveform Design: A Symbol-Level Precoding Approach," IEEE JSTSP, vol. 15, no. 6, pp. 1316–1331, Nov. 2021`（**仅读联网检索摘要**）：在窄带无色散 `MIMO-DFRC` 中将逐天线恒模、相长干涉 SLP 与期望雷达波束图软匹配结合并用流形 ALM-RBFGS 求解，但未采用目标方向确定性波形硬等式降维为 $(N_t-2)$ 维子流形，也未处理双色散距离–多普勒旁瓣。
  6. `Yuanhan Ni, Fan Liu et al., IEEE TWC 2026`（`10.1109/twc.2026.3670065`，**已读缓存全文前 120 行** `ni26_ps_afdm_isac.txt`）、`Shiqi Cui et al., IEEE JSAC 2026`（`10.1109/jsac.2026.3752077`，**仅读缓存前 15 行摘要** `calib20261124_p04.txt`）与 `E. Gourar et al., arXiv:2607.01064`（**已读缓存前 160 行** `sensing_papr_2607_01064.txt`）：均属单天线 SISO `AFDM-ISAC` 模糊函数分析、PCS 整形或预留子载波降 PAPR，不涉及多用户下行 `MIMO` 符号级预编码与恒模子流形。

- 查新与直套判断：**跨体制已有但非平凡适配成立（1b）**
  1. **母方法直套 AFDM 崩盘**：`Li TWC'25 / TVT'25` 按逐频点对角通道近似直套双色散 AFDM（`NaivePort_Diag_ALMRCG_AFDM`），忽略 DAFT 仿射跨格移位与快时间多普勒，卡片报告 `24 dB` 处 BER 崩至 `26.7%–27.5%`。
  2. **补齐精确算子仍卡平层与离网旁瓣**：即便为 `ALM-RCG` 补齐精确快慢时间双色散算子与 `HiGHS` 时域 16 边形初值（`ExactFastDop_ALMRCG`），因四次离散格点惩罚跨 $N_s$ 块耦合且挤压 CI 安全裕度，卡片报告在压制 $|\Delta\ell|\le 5, |\Delta m|\le 4$ 时通信 BER 仍卡 `>1e-3` 平层，且在离散格点之间的离网弱目标（$\Delta\ell=4, \Delta m=2.35$）上 `PSLR/ISLR` 与弱目标 `SINR23` 明显劣于本卡。
  3. **降阶回静态/无啁啾体制反号退化**：在子流形等式及目标波形 $u_{\text{af,chirp}}^\star$ 完全一致的条件下将 `AFDM` 退化为 `OFDM`（`Ctrl_Submanifold_OFDM_SameChirp`, `c1=c2=0`），因 `OFDM` 无法拆分同用户多径，多径同频相干混叠造成深衰落，卡片报告相同雷达性能下通信 `ExSNR@1e-3` 退化 `+1.01 ~ +2.22 dB`。

- 为什么没人做或直套为何失效：**`(1b)`**
  - **机制依据**：据 [h_probe_h01_submanifold_isac.py](file:///Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation/ideas/probes/h_probe_h01_submanifold_isac.py) 源码核查，本卡令目标方向合成波 $u_{q,n}^\star = \sqrt{P_0/N_s}(\mathbf{A}^H\mathbf{e}_0)_n$ 跨 $q=0,\dots,N_s-1$ 块完全相同（`L508–510`），既清除了慢时间多普勒上的随机数据旁瓣基底（仅留 Hamming 窗自身 `-38.3 dB` 旁瓣），又利用 $2N_c c_1 = 3$ 与偶数 $N_c$ 互素及 CPP/CP 周期性令所有非零时延 $\ell \neq 0$ 的循环自相关严格为零，将 $N_s$ 块耦合四次优化拆解为独立的 $(N_t-2)N_c$ 维光滑子流形 max-min 相长干涉优化（切空间投影与 $2\times 2$ 牛顿回缩均为 $\mathcal{O}(N_t N_c)$ 闭式运算）。同时 `AFDM` 将多径搬移至互不重叠的仿射对角带，避免 $(N_t-2)$ 维有限自由度在多径深衰落频点撞墙。
  - **审稿审计发现的源码与数学瑕疵（需在 L2 修正，不影响 `(1b)` 放行）**：
    1. **正则性充分条件表述偏粗**：卡片第 36 行声称“$|u_{q,n}^\star|/a_{\text{cm}}=\sqrt{0.8 N_t} < N_t - 2$ 对一切 $N_t\ge 6$ 成立即可保证各阵元相位严格非共线”。严格而言，$\det(\mathbf{J}\mathbf{J}^T)=\frac{1}{2}\sum_{t<r}\sin^2(\theta_t-\theta_r)=0$ 的奇异点出现在阵元相位取反平行两方向且满足 $|u^\star|/a_{\text{cm}}\in\{N_t-2k : k=0,\dots,\lfloor N_t/2\rfloor\}$；例如若未来扩到 $N_t=20, P_0/P_T=0.8$，则 $\sqrt{0.8\times 20}=4 = 20 - 2\times 8$，理论上存在共线奇异点（在卡片所测 $N_t=8, 10$ 时 $\sqrt{6.4}, \sqrt{8}$ 非整数故确实无奇异点），正文需改写为“非同奇偶整数”条件。
    2. **基线饱和度与计时公平性待 L2 补强**：`solve_alm_rcg`（`L633–739`）固定了 `gamma_target=0.42*sqrt(E_bin)`、`rho<=160` 与 `20` 外轮且只跑 `w_isl in {600, 10000}`；`Prop_Submanifold` 的 `ms_conv` 计时（`L529`）未计入前期 `solve_exact_eq60_highs`（`L515`）LP 初值耗时。虽从卡片数值看双指标 Pareto 优势极大（`ISLR` 差 `9.2–15.6 dB` 且通信无平层），L2 仍需补测 `ALM-RCG` 权重扫描与无 LP 廉价初值。

- 真实系统里的影响：
  将多用户下行恒模 `MIMO AFDM-ISAC` 预编码从“高耦合慢收敛的离散网格四次惩罚求解”转变为“逐块可并行的 $(N_t-2)N_c$ 维子流形一阶光滑优化”，在不增加用户端均衡负担（仍可直接 PSK 硬判）下兼顾低峰均比功放效率与强弱目标探测（卡片报告原图间距弱目标 `Pd@1e-3` 达 `0.996`）。
  **成立前提**：(1) 阵列与用户数满足自由度阈值 $N_t - 2 \ge 2K$；(2) 目标为单一定向跟踪角度 $\theta_0$ 且目标慢时间多普勒在无模糊区间 $|\nu|\le 0.5$ 内（多目标同时定波形会收紧为 $N_t - 2M \ge 2K$）；(3) 基站具备较准确的下行双色散 CSI 且用户采用 PSK 调制。

- 最强的反对意见（一句）：
  硬等式 $\mathbf{a}_t^H(\theta_0)\mathbf{X}_{q,n,:}^T=u_{q,n}^\star$ 把雷达约束写死在单一已知角度 $\theta_0$ 且刚性占用每采样点 2 个实自由度，一旦推广到多目标/宽扇区探测（需锁多方向）、用户过载（$N_t-2<2K$）或基站下行 CSI 存在估计误差时，子流形可行域会被迅速挤干并重新出现误码地板。

- 顶刊痛点出处：**成立** — 锚点 1：`Peishi Li et al., IEEE TWC 2025`（`10.1109/twc.2024.3503605`，Eq. 55/60，Fig. 7–8 强弱目标差 `19 dB / 23 dB` 与 ROC 曲线）及 `IEEE TVT 2025`（`10.1109/tvt.2025.3570381`，Sec. III–IV `ALM-RCG`，Fig. 2 $N_t=10, K=4, N_c=32, N_s=16$）；锚点 2：`Shuntian Tang et al., IEEE TWC 2026`（`10.1109/twc.2026.3692638`，Table I $N=64, P=3, l_{\max}=2, v_{\max}=625\text{ km/h}\Rightarrow \alpha_{\max}=0.1544$）及 `Rang Liu et al., arXiv:2607.05119`（Sec. V $N_t=6\text{–}10, K=3, N=64, Q=16, N_{\text{cpp}}=10, \theta_0=40^\circ$），探针源码 `h_probe_h01_submanifold_isac.py` 严格守住了原论文参数范围，未拉偏参数自造地板；账本与门槛：**破壁账 够得着**（按第 10 轮 ISAC 双指标门槛，卡片报告通信不仅未退化反而消除 `>1e-3` BER 平层、`ExSNR@1e-3` 胜过全部恒模基线 `>7 dB`，同时二维 `PSLR/ISLR` 相比配齐快时间梯度的 `ExactFastDop_ALMRCG` 改善 `8.9–12.5 dB / 9.2–15.6 dB`，达标 `≥6–10 dB`；若同时主张算力提速，需在 L2 明确以已发表最快同精度 `ExactFastDop_ALMRCG` 为对手并计入端到端初值构建时间）。

- 如果要做，最便宜的一步检验是什么（含 `A+B` 必测的单部件消融与便宜构造基线）：
  在 `deinlab`（`≤16` 核、40 CPI 未见测试种子）先执行以下最小闭环检验，并在可运行 `numpy/scipy` 环境中重跑归档探针核实基准数：
  1. **双向单部件消融与静态 `DiD` 起跑线**：在已有的 `Abl_B_only_TorusOnly`（去等式子流形）与 `Ctrl_Submanifold_OFDM_SameChirp / Str`（去 AFDM 啁啾分集）基础上，补跑**静态无色散 `C=0` 起跑线**计算 `AFDM` 对 `OFDM` 的双重差分 `DiD`。
  2. **充分调参的 `ExactFastDop_ALMRCG` Pareto 扫参**：对 `w_isl` 做扫描（如 `{100, 600, 3000, 10000}`）并放宽 `rho_max` 与外轮上限，排除“调参后 `ALM-RCG` 可同时打平误码率与旁瓣”的质疑。
  3. **无 LP 廉价初值消融与边界/波束图核查**：测试把 `solve_exact_eq60_highs` 替换为廉价投影初值 `init_submanifold_phases(MF)` 后是否仍无地板并测端到端耗时；加测过载点（$N_t=6, K=4$）验证相变律 $N_t - 2 \ge 2K$，并输出全空间角域波束图 $P(\theta)$ 核验无杂波/用户方向异常旁瓣凸起。

