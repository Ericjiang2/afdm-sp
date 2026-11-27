# 第 16 轮（8 小时通宵轮）：`2 左 + 2 右` 双半场推进（左半场新 `[S- · 64开]` 补挖+解算 × 右半场 Phase 2 攻坚）

> **本轮核心决策（Eric 2026-11-26 23:35 拍板）**：
> 1. **左半场准入标尺正式定为两级（破除“必须四家全维度通杀才算赢”的误杀，同时死守不收 `55开` 换皮）**：
>    - **最高档 `[S+ · 四家全胜]`**：`AFDM` 单挑同时净赢满配 `{OFDM, SC-FDE, OTFS, Zak-OTFS}` 四家跨过固定主账本门槛。
>    - **保底准入档 `[S- · 硬赢 OFDM + 对 OTFS 整体 64 开]`（左半场正式准入底线）**：
>      1. **必过门 A（硬赢满配 `OFDM`）**：解决 `OFDM` 真物理硬伤，配对 95% CI 下界跨过单一固定门槛（同目标误码/误帧 `ΔSNR ≥ +1.50 dB`，或高 SNR 地板 `p_OFDM ≥ 10.0%` 且 `p_OFDM − 5.0×p_AFDM > 0`，或等虚警 `ΔPd ≥ +15.0 pp`，或同精度单核耗时比 `≥ 10.0×`）；
>      2. **必过门 B（对满配 `OTFS / Zak-OTFS` 整体 `64开` 占优，严禁 `55开`）**：
>         - *整体不输底线*：核心工作区多工况平均主精度不输满配 `OTFS / Zak-OTFS`（配对均值亏损 `≤ 0.20 dB` 或 `ΔPd ≥ -2.0 pp`，允许局部边缘参数点互有胜负，但核心工况胜平率 `≥ 60%` 且无崩盘死角；同台必跑满配 `SC-FDE / DFT-s-OFDM` 如实划清适用边界，不得被简单 `DFT-s-OFDM` 在全部考核维度上无代价反超）；
>         - *至少 1 项硬量化净赢（配对 95% CI 不跨零）*：① 核心工作区主精度净赢 `OTFS/Zak-OTFS`（`ΔSNR ≥ +0.75 dB`，或 `p_OTFS ≥ 5%` 下误差降 `≥ 2.0×`，或等虚警 `ΔPd ≥ +8.0 pp`）；**或** ② 主精度持平下，单帧端到端计算耗时快 **`≥ 3.0×`**；**或** ③ 在标准资源块帧长 $N$（如 3GPP `12×N_RB`）或动态色散纵横比 $(L_{\max}, k_{\max})$ 下，相比受 $M_d \times K_\nu = N$ 整数网格约束的 `OTFS/Zak-OTFS` 省导频+保护开销 **`≥ 15%`**（同码率同误码净吞吐高 `≥ 12%`）、后 `RRC` `BW99` 窄 **`≥ 15%`**、99.9% 发射 `PAPR` 低 **`≥ 2.0 dB`**、或同分集跨块时延短 **`≥ 4×`**。
> 2. **四路 8 小时通宵分兵（`50% 左半场 [g + k] : 50% 右半场 [h + m]`，每路自带无阻塞兜底，通宵零停机）**：
>    - **左半场 2 路（`g` + `k`）**：前半程按新 `[S- · 64开]` 标尺把左半场认证题库扩充扎实（防左半场缺题），后半程直接挑本路头号左半场存活题进入 **Phase 2（锁 `H-<id>.py` 评测台 → 多方案解算 → 1 条闭式解析支点 → `--mode holdout`）**！
>    - **右半场 2 路（`h` + `m`）**：直接领走已过 Phase 1 拆台的头号双色散共性 `[A档]` 硬题（`h` 攻 **`P-k-B1` `6→4` 150% 过载单帧免授权双色散上行**，备选 `P1B-H6` 双端 `-40 dB` 旁瓣通感设计；`m` 攻 **`P-m-15b-02` 2-RX 零导频盲双色散强同频干扰消除**，备选 `G2B-harq-mimo-ir` 跨 20 帧跳相 HARQ），跑通 **30 年去波形词查新门 → 锁 `H-<id>.py` → 多方案解算 + `evolve_cli.py` → 1 条闭式解析支点 → `--mode holdout`** 全链路！

规则优先级：本文件 > [`../FUNNEL.md`](../FUNNEL.md)（11-26 23:35 版） > [`round-15.md`](round-15.md) > [`round-15c.md`](round-15c.md)。

---

## 一、四路共享工程与防伪硬纪律（8 小时通宵必守）

1. **物理同台与对等调优硬契约**：
   - 全部波形跑在完全相同的连续时间 `OSR=8 RRC (β=0.25)` 多径多普勒信道种子上；除明确考核 `BW99` 压缩比的场景（须锁死相等符号速率与净比特率）外，整突发含 `CP/CPP` 与滤波拖尾的发射能量极差 `< 0.5%`、`BW99` 极差 `< 3.0%`。
   - 四波形导频/网格调优预算严格对等：给 `AFDM` 搜索 $M$ 组配置，则对 `OFDM`（等距梳、非均匀/分簇子带、交织编码 `BICM`）、`SC-FDE`（集中/首尾 `UW-SC`、多段 `K×L PTRS`、`DFT-s-OFDM`）、`OTFS / Zak-OTFS`（合法 $M_d \times K_\nu$ 分解 + 脉冲/Golomb/斜管/旋转晶格扩展导频）投入同等搜索预算，同装对称零先验数据泄漏协方差白化器与等迭代轮数。
2. **第二级（Phase 2）四步标准交付件**：
   - **Step 2.0（右半场必做，≤ 45 分钟）**：① 用去掉 `AFDM / OTFS` 限定词的纯信号处理 / `LTV-OFDM` / `MIMO` / `blind interference cancellation` / `overloaded grant-free` 关键词调 `search_papers.py` 做 **1995–2026 全历史查新**，核查至少 5 篇最接近经典与近作，把漏掉的最强经典母方法补入 `Best_Steelman` 实测——若经典法把净空间吃剩 `< 1.0×` 门槛，诚实记 `KILLED_BY_PRIOR_ART` 并立即切入本路预设【备选认证题】，绝不硬撑；② 核验 `AFDM` 原生最优导频同台不输满配 `OFDM / SC-FDE`（差 `≤ 0.25 dB / 2.0 pp`）。
   - **Step 2.1（锁死共享信道边界评测台 `ideas/harnesses/H-<id>.py`，≤ 60 分钟）**：统一暴露 `(encode_tx, decode_rx)` 接口，内置 `Pub`、`Best_Steelman`、`Oracle` 及 `--mode dev`（公开供设计与调参）与 `--mode holdout`（更换 `PDP`、径数扰动、全新封存种子 `+50000` 并强制统计单帧 `MACs` 与单核耗时——**搜索与调参期严禁运行 `--mode holdout`，全轮只准在收尾终验跑 1 次！**）。经 `gpt-6.2-sol` 核查无偏后记录脚本 `MD5`，此后不改评测台（仅漏基线可单点增补重跑全部方案）。
   - **Step 2.2（病理推理 + ≥ 4 套不同结构方案冲锋 + `evolve_cli.py`）**：先写 5 行数学病理解剖，再在 `--mode dev` 上并发实测 `≥ 4` 套不同结构机制（凡涉及离散导频图样/扩频码本/斜率排程/恒模相位的子核，必对比无约束局部爬山或 `evolve_cli.py`），配对 95% CI 下界跨过所属账本固定门槛。
   - **Step 2.3（1 条零拟合参数闭式解析支点）**：推导并在 `≥ 3` 组有限长分数色散 `OSR=8 RRC` 工况下数值核验 **1 条零拟合参数闭式理论式**（如可辨识秩/相变准则、贝叶斯/确定性 `CRLB`、高 SNR `PEP` 分集阶、渐近 `SINR` 或状态演化不动点），曲线误差 `≤ 0.5 dB` 或相变点相对误差 `≤ 20%`。
   - **Step 2.4（`--mode holdout` 一次性终验 + `Sol` 双拍对抗审计 + 提交）**：跑 1 次 `--mode holdout` 存 `ideas/r16/holdout_<id>.json`，请 `gpt-6.2-sol` 做双拍 `kill-argument` 审查（先写 `≤ 200` 字最强拒稿信，再逐行核对代码与 JSON 裁决），完整报告写入 `ideas/r16/stage2-${R}-<id>.md`，更新 `ideas/runs-${R}.md` 并 `git commit -- ideas/`。
3. **算力、外部模型与隔离护栏（4 路同跑 `deinlab` 必守！）**：
   - **各走独立 worktree**（`afdm-funnel-g`、`afdm-funnel-k`、`afdm-funnel-h`、`afdm-funnel-m`），严禁跨工作树写文件，严禁 `git add .`（只准显式提交 `ideas/` 下本轮新建/追加文件，不改旧卡 `ideas/cards/` 与 `r15` 历史文件）。
   - **`deinlab` 配额**：`/home/guoyikun/.conda/envs/AFDM/bin/python`，必设 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1`，**单 runner 并发上限 `≤ 12` 核**（四路合计 `≤ 48 / 128` 核），远端工作目录 `/data/guoyikun/tmp/funnel_${R}_r16/`（跑毕清理），tmux 名 `g_funnel_${R}_r16*`。
   - **顾问调用**：Codex MCP 已退役严禁调用；一律用 `codex exec -m gpt-6.2-sol --sandbox read-only`（stdin 喂入），**每 runner 8 小时上限 `≤ 6` 次批量调用**（若遇配额耗尽不阻塞，记日志改本地自审继续推进）。

---

## 二、四路互斥任务矩阵

| runner | 半场与角色 | 前半程任务（0 – 3.5h） | 后半程任务（3.5h – 8.0h） | 保底切换路线（防空转） |
|---|---|---|---|---|
| **`g`**<br>`afdm-funnel-g` | **左半场主力 ①**<br>支点 ④ + 标准帧长网格失配 & 双域损伤低算力 `64开` | **按新 `[S- · 64开]` 标尺认证 2–3 道左半场新题**（写 `ideas/r16/teardown-g-r16.md`）：<br>① 跨重传/双突发/双天线 $\pm c_1$ 正负斜率交汇消解紧导频模糊（对照跨包换网格 `OTFS` + 跳梳 `OFDM` + `PTRS-SC`）；<br>② 3GPP 标准 PRB 帧长（如 $N=72, 108, 132, 180$）或帧间动态 $(L_{\max}, k_{\max})$ 下，`AFDM` 在线整数调 $2Nc_1$ 相对受 $M_d\times K_\nu=N$ 整数分解限制的 `OTFS/Zak-OTFS` 是否硬赢 `OFDM` 且对 `OTFS` 取得 `≥15%` 净吞吐/开销或 `≥3×` 算力 `64开`；<br>③ 双域局部干扰+相噪下的一维带状低复杂度联合迭代检测（测对二维 `Zak-OTFS` 是否有 `≥3×` 算力或非二进帧长 `64开`）。 | 取本路认证出的**头号 `[S+/S-]` 左半场题**直进 **Phase 2**：锁 `ideas/harnesses/H-g-<slug>.py` → 测 `≥ 4` 套 `(encode_tx, decode_rx)` 结构方案（离散排程/导频跑 `evolve_cli.py`）→ 补 **1 条零拟合参数闭式解析支点** → 跑 `--mode holdout` + `Sol` 双拍终审，产出 `ideas/r16/stage2-g-<slug>.md`。 | 若前 `3.5h` 测满 `6–8` 个左半场切口仍 `0` 过 `[S-]`，如实落盘死因后无缝转攻本路已认证右半场王牌 **`G2B-harq-mimo-ir`**（`4×4 MIMO` 跨 20 帧跳相 Raptor-IR HARQ，`+7.83 dB` 缺口）跑完整 Phase 2！ |
| **`k`**<br>`afdm-funnel-k` | **左半场主力 ②**<br>支点 ① 几何耦合流形 & 带限走廊 | **按新 `[S- · 64开]` 标尺收口补测 + 扩充 1–2 道左半场题**（写 `ideas/r16/teardown-k-r16.md`，只读参考主目录与本工作树 `r15` 产物）：<br>① 为已认证的 **`k01+k02`（弯曲双基地杂波脊通感）** 补齐满配 `OTFS` 与旋转晶格/斜管 `Zak-OTFS` 同台对照（核实 `Ridge-AFDM` 在硬赢 20-EM `OFDM` `10.7×` 耗时 + `+1.74 dB` 基础上，对 `Zak-OTFS` 在计算耗时、`BW99`、任意曲率流形自由度上的精确 `64开` 账单）；<br>② 完成带限稠密走廊散射（`P-k-C1` `Diffuse P=24` vs `Newton-OMP SC-FDE` / `BEM-OFDM` / 斜管 `Zak-OTFS`）及 1–2 个新支点 ① 切口（如 `Sol` 建议的双支对称反射 $\nu_\pm = \pm\mu(\tau-\tau_0)$ 多斜率分辨或机载/高铁下行耦合流形预编码）的 `[S-]` 认证。 | 取本路**最强左半场存活题**（若 `P-k-C1` 稠密走廊或新切口稳过 `[S+/S-]` 优先攻新题；否则深攻 `k01+k02` 升级版）跑完整 **Phase 2**：锁 `ideas/harnesses/H-k-<slug>.py` → 冲击新收发联合算法（把曲率/横向微多普勒容限、通信 `SER` 与实时复杂度推到极致）→ 补 **1 条零拟合参数闭式预测误差/杂波零空间自由度公式** → 跑 `--mode holdout` + `Sol` 双拍终审，产出 `ideas/r16/stage2-k-<slug>.md`。 | `k01+k02` 已实测稳过对 `OFDM` `10.7×` 算力与 `+1.74 dB` 门槛，天然构成零空转左半场 Phase 2 保底靶标。 |
| **`h`**<br>`afdm-funnel-h` | **右半场攻坚 ①**<br>过载免授权接入 / 通感旁瓣联合设计 | **直进右半场 Phase 2（主攻 `P-k-B1`：`6` 单天线用户 `→ 4` 接收天线 `150%` 空间过载单帧 `N=128` 紧导频双色散免授权接入，高 SNR 地板 `41.82% → 0%`）**：<br>1. `0–0:45`：跑 **1995–2026 去波形词（`overloaded MIMO`, `grant-free NOMA`, `bilinear channel estimation`, `LTV-OFDM`）全历史查新门**，只读参考 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation/ideas/r15/td_k_p1b_gfra_killcheck.py`，核查经典双线性 `BiG-AMP / Subspace / 扩频多址` 先例并核验 `AFDM` 同台不输满配 `OFDM / SC-FDE`；<br>2. `0:45–1:45`：搭建并经 `Sol` 审定锁死 MD5 的共享评测台 `ideas/harnesses/H-b1-overloaded-gfra.py`。 | `1:45–8:00`：**病理推理 + 多结构方案冲锋 + 闭式支点 + Holdout**：<br>解剖为什么 `MMSE-EP / SOMP / SBL` 在 150% 过载下卡死 `41.8%` 而已知支撑达 `0%`；设计 `≥ 4` 套 `(encode_tx 非正交导频/签名字典 + decode_rx 空时仿射联合稀疏活跃检测与双线性消息传递)` 方案（签名字典/导频排布必跑 `evolve_cli.py` 对照），将高 SNR 地板打穿 `≥ 5×–10×`；推导 **1 条零拟合参数过载双色散可辨识秩/高 SNR `PEP` 闭式支点**；跑 `--mode holdout` + `Sol` 双拍终审，写入 `ideas/r16/stage2-h-b1.md`。 | 若 `P-k-B1` 在 Step 2.0 被 30 年旧文献先例完全覆盖（净余量 `<1.0×`），记清文献 DOI 后立即切回本工作树已认证的 `[轨B-ISAC]` **`P1B-H6`（双端联合 `-30/-40 dB` 超低距离多普勒旁瓣通感设计）** 跑完整 Phase 2！ |
| **`m`**<br>`afdm-funnel-m` | **右半场攻坚 ②**<br>2-RX 零导频盲双色散强干扰消除 | **直进右半场 Phase 2（主攻 `P-m-15b-02 / C15`：`N_r=2` 双接收天线零导频协作下的未知双色散同频强干扰盲对消，满配空时 `IRC / WL-LMMSE / CMA / 子空间` 全卡 `50.35%` 误码死锁 vs 零空间真值 `0%`）**：<br>1. `0–0:45`：跑 **1995–2026 去波形词（`blind co-channel interference cancellation`, `SIMO doubly dispersive`, `time-varying subspace IRC`, `joint channel and interference estimation`）全历史查新门**，只读参考 `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/r15/teardown-m-p1b.md` 对应脚本，把漏掉的最强经典盲分离/多项式矩阵 `PEVD` 或半盲 `EM` 基线补入复测，并核验 `AFDM` 原生导频同台不输满配 `OFDM / SC-FDE`；<br>2. `0:45–1:45`：搭建并经 `Sol` 审定锁死 MD5 的共享评测台 `ideas/harnesses/H-m15b02-blind-ic.py`。 | `1:45–8:00`：**病理推理 + 多结构方案冲锋 + 闭式支点 + Holdout**：<br>针对双色散干扰在单帧内跨时频二维耦合破坏传统逐频点空域秩-1 假设的病根，并发实测 `≥ 4` 套结构化双色散盲/半盲干扰子空间剥离与期望信号双线性恢复方案，打穿 `50%` 死锁地板；推导 **1 条零拟合参数双接收天线双色散干扰可消性自由度条件或渐近残留干噪比 `SINR` 闭式公式**（`≥ 3` 工况核对 `≤ 0.5 dB`）；跑 `--mode holdout` + `Sol` 双拍终审，写入 `ideas/r16/stage2-m-blind-ic.md`。 | 若 `P-m-15b-02` 在 Step 2.0 被 30 年盲分离旧文献击穿（净余量 `<1.0×`），记清文献 DOI 后立即切去已认证的 **`G2B-harq-mimo-ir`**（只读参考主目录 `ideas/r15/td_g_p1b_harq_mimo_ir.py`，`+7.83 dB` 缺口）跑完整 Phase 2！ |

---

## 三、睡前一键粘贴口令（4 个 8 小时会话）

### 1. 左半场第 1 路：`runner g`
- **工作目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`
- **粘贴口令**：
```text
你是 runner g。现在启动第 16 轮（8 小时通宵轮：左半场新 [S- · 64开] 标准补挖认证 + 头号存活题 Phase 2 解算）。先完整阅读 ideas/prompts/round-16.md 与更新后的 ideas/FUNNEL.md，并只读参考 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/r15/teardown-g.md 与 teardown-g-p1b.md。严格在本工作树 afdm-funnel-g 内工作，deinlab 限 ≤12 核、OMP_NUM_THREADS=1、临时目录 /data/guoyikun/tmp/funnel_g_r16/，gpt-6.2-sol（codex exec --sandbox read-only）全轮上限 ≤6 次：
1. 前 3.5 小时执行第一级左半场定向认证（汇总写入 ideas/r16/teardown-g-r16.md）：按 Eric 最新校准的 [S- 保底准入线]——「正面硬赢满配 OFDM 过固定门槛 + 对满配 OTFS/Zak-OTFS 核心工作区整体不输且至少在精度(≥0.75dB/2×)、计算耗时(≥3×)、导频保护开销(≥15%)、BW99/PAPR/跨块时延之一取得配对 95% CI 不跨零的 64开净赢（严禁 55开换皮）」，在支点 ④ 跨重传/双流 ±c1 正负斜率交汇、标准 PRB 非二进帧长/动态色散纵横比适配、双域局部干扰低复杂度接收中快筛 5–8 个切口（每题先跑 ≤3 分钟四波形对等调优结构预检，0 过线完全合法）；
2. 后 4.5 小时直进 Phase 2：取你认证出的头号左半场存活题（若前 3.5h 0 过线，则无缝转攻你昨晚认证的右半场王牌 G2B-harq-mimo-ir 跨 20 帧跳相 4×4 MIMO HARQ，先做 30 年去波形词查新门），搭建经 Sol 审定锁 MD5 的共享评测台 ideas/harnesses/H-g-<slug>.py（含 --mode dev 与封存 --mode holdout，搜索期严禁跑 holdout），并发实测 ≥4 套不同结构 (encode_tx, decode_rx) 方案（离散排程/导频子核跑 evolve_cli.py 对照），补齐 1 条零拟合参数闭式解析支点（≥3 工况误差 ≤0.5 dB），收尾跑 1 次 --mode holdout 与 Sol 双拍对抗审计，完整报告写入 ideas/r16/stage2-g-<slug>.md，追加 ideas/runs-g.md，清理远端临时目录并 git commit -- ideas/ 后退出。
```

### 2. 左半场第 2 路：`runner k`
- **工作目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`
- **粘贴口令**：
```text
你是 runner k。现在启动第 16 轮（8 小时通宵轮：左半场新 [S- · 64开] 标准补测扩充 + 头号左半场题 Phase 2 解算）。先完整阅读 ideas/prompts/round-16.md 与更新后的 ideas/FUNNEL.md，并只读参考本工作树及主目录 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/r15/ 下的 teardown-k*.md 与相关脚本。严格在本独立工作树 afdm-funnel-k 内落盘提交，deinlab 限 ≤12 核、OMP_NUM_THREADS=1、临时目录 /data/guoyikun/tmp/funnel_k_r16/，gpt-6.2-sol（codex exec --sandbox read-only）全轮上限 ≤6 次：
1. 前 2.5 小时按新 [S- · 硬赢满配 OFDM + 对满配 OTFS/Zak-OTFS 整体 64开、禁 55开] 标尺完成两项左半场认证（汇总写入 ideas/r16/teardown-k-r16.md）：① 为 k01+k02（弯曲双基地杂波脊通感）补齐满配矩形 OTFS 与旋转晶格/斜管 Zak-OTFS 同台配对实测，核实其在硬赢 20-EM OFDM (10.7× 耗时 + 1.74 dB) 之外对 Zak-OTFS 的精确 64开优势项（耗时、BW99、曲率流形自由度）；② 完成带限稠密走廊散射 P-k-C1（对比 Newton-OMP SC-FDE、BEM-OFDM、斜管/旋转晶格 Zak-OTFS）及 1–2 个支点 ① 新切口（如双支对称反射 ±μ 多斜率分辨或下行耦合流形预编码）的四波形对等拆台；
2. 后 5.5 小时直进 Phase 2：取本路最强左半场过线题（新题稳过 [S+/S-] 则优先攻新题，否则深攻 k01+k02 升级版），搭建经 Sol 审定锁 MD5 的共享评测台 ideas/harnesses/H-k-<slug>.py（严守搜索期禁碰 --mode holdout），并发实测 ≥4 套 (encode_tx, decode_rx) 方案打赢全套钢人，推导并在 ≥3 组有限长 OSR=8 RRC 工况核验 1 条零拟合参数闭式理论支点（预测误差下界 / 杂波零空间自由度或相变界），收尾跑 1 次 --mode holdout 与 Sol 双拍对抗审计，写入 ideas/r16/stage2-k-<slug>.md，追加 ideas/runs-k.md，清理远端临时目录并 git commit -- ideas/ 后退出。
```

### 3. 右半场第 1 路：`runner h`
- **工作目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`
- **粘贴口令**：
```text
你是 runner h。现在启动第 16 轮（8 小时通宵轮：右半场认证硬题 Phase 2 全链路攻坚）。先完整阅读 ideas/prompts/round-16.md 与更新后的 ideas/FUNNEL.md。鉴于左半场支点 ③ 已连测 9 题 0 存活触发换道纪律，本轮你主攻已过 Phase 1 拆台的右半场头号通信硬题 P-k-B1（6 单天线用户 → 4 接收天线 150% 空间过载单帧 N=128 紧导频双色散免授权接入，满配 MMSE-EP/SOMP/SBL 地板 41.82% vs 真支撑 0%；只读参考 /Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation/ideas/r15/td_k_p1b_gfra_killcheck.py；备选为你本工作树已认证的 [轨B-ISAC] P1B-H6 双端 -30/-40 dB 旁瓣通感联合设计）。严格在本工作树 afdm-funnel-h 内落盘，deinlab 限 ≤12 核、OMP_NUM_THREADS=1、临时目录 /data/guoyikun/tmp/funnel_h_r16/，gpt-6.2-sol（codex exec --sandbox read-only）全轮上限 ≤6 次：
1. Step 2.0（≤45 分钟）：先用去掉 AFDM/OTFS 的纯信号处理关键词（overloaded MIMO, grant-free NOMA, bilinear channel estimation, LTV-OFDM）做 1995–2026 全历史查新门，把漏掉的最强经典双线性/扩频多址方法补入复测，并核验 AFDM 原生导频同台不输满配 OFDM/SC-FDE（若 P-k-B1 被经典文献吃剩 <1.0× 门槛，记清 DOI 立即切入备选 P1B-H6）；
2. Step 2.1（≤60 分钟）：搭建经 Sol 审定锁死 MD5 的共享信道边界评测台 ideas/harnesses/H-b1-overloaded-gfra.py（含 --mode dev 与封存 --mode holdout，搜索调参期严禁调用 holdout）；
3. Step 2.2–2.4（剩余 ~6 小时）：对 150% 过载双线性死锁做数学病理解剖，在 --mode dev 上并发实测 ≥4 套不同结构 (encode_tx 导频/非正交签名字典 + decode_rx 联合稀疏活跃检测与双线性消息传递) 方案（离散签名字典/导频图样必跑 evolve_cli.py 对照），配对 95% CI 下界将高 SNR 地板打穿 ≥5×–10×；推导并在 ≥3 组分数色散工况核验 1 条零拟合参数闭式支点（过载双色散可辨识秩条件或高 SNR PEP/CRLB）；最后跑 1 次 --mode holdout 与 Sol 双拍对抗审计，写入 ideas/r16/stage2-h-b1.md，追加 ideas/runs-h.md，清理远端临时目录并 git commit -- ideas/ 后退出。
```

### 4. 右半场第 2 路：`runner m`
- **工作目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`
- **粘贴口令**：
```text
你是 runner m。现在启动第 16 轮（8 小时通宵轮：右半场认证硬题 Phase 2 全链路攻坚）。先完整阅读 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-16.md 与更新后的 FUNNEL.md。鉴于左半场支点 ② 已测完 S1–S8，本轮你主攻自己 Phase 1B 认证通过的右半场硬题 P-m-15b-02 / C15（N_r=2 双接收天线零导频协作下的未知双色散同频强干扰盲对消，满配空时 IRC/WL-LMMSE/CMA/子空间全卡 50.35% 误码死锁 vs 零空间真值 0%；只读参考主目录 ideas/r15/teardown-m-p1b.md 对应脚本；备选为主目录 ideas/r15/td_g_p1b_harq_mimo_ir.py 的 G2B 跨 20 帧跳相 4×4 MIMO HARQ）。严格在本工作树 afdm-funnel-m 内落盘，deinlab 限 ≤12 核、OMP_NUM_THREADS=1、临时目录 /data/guoyikun/tmp/funnel_m_r16/，gpt-6.2-sol（codex exec --sandbox read-only）全轮上限 ≤6 次：
1. Step 2.0（≤45 分钟）：先用去掉 AFDM/OTFS 的纯信号处理关键词（blind co-channel interference cancellation, SIMO doubly dispersive, time-varying subspace IRC, polynomial PEVD, joint channel and interference estimation）做 1995–2026 全历史查新门，把漏掉的最强经典盲/半盲分离基线补入复测，并核验期望链路采用 AFDM 原生导频时同台不输满配 OFDM/SC-FDE（若被 30 年旧文献吃剩 <1.0× 门槛，记清 DOI 立即切入备选 G2B-harq-mimo-ir）；
2. Step 2.1（≤60 分钟）：搭建经 Sol 审定锁死 MD5 的共享评测台 ideas/harnesses/H-m15b02-blind-ic.py（含 --mode dev 与封存 --mode holdout，搜索调参期严禁调用 holdout）；
3. Step 2.2–2.4（剩余 ~6 小时）：针对单帧双色散干扰破坏逐频点秩-1 空域假设的病根，在 --mode dev 上并发实测 ≥4 套结构化双色散盲零空间/半盲双线性联合恢复方案打穿 50% 地板；推导并在 ≥3 组分数色散工况核验 1 条零拟合参数闭式支点（双天线双色散干扰可消自由度边界或渐近残留 SINR 闭式公式，误差 ≤0.5 dB）；最后跑 1 次 --mode holdout 与 Sol 双拍对抗审计，写入 ideas/r16/stage2-m-blind-ic.md，追加 ideas/runs-m.md，清理远端临时目录并 git commit -- ideas/ 后退出。
```
