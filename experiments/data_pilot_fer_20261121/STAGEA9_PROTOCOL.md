# 阶段 A9：未知时延条件下半盲联合时延-多普勒-增益恢复（`SBJ`）能否保住第 0 轮增益——协议（`STAGEA9_PROTOCOL.md`）

**状态**：PENDING-GATE-AND-BEFORE-COMMIT（静态审查见 [out/stageA9_sol_review.md](out/stageA9_sol_review.md)；须待远端门控 G1–G3 通过并完成 `Before` 提交后方才正式冻结生效，确认实验在新帧 `41500–41819` 上仅运行一次，跑后严禁改标）

**背景与承接**：
- [STAGEA7_READOUT.md](STAGEA7_READOUT.md)、[STAGEA8_READOUT.md](STAGEA8_READOUT.md)、[STAGEA8B_READOUT.md](STAGEA8B_READOUT.md) 与 [../sameframe_cd2_20261125/READOUT.md](../sameframe_cd2_20261125/READOUT.md)：在给定真实整数时延 $l_i$ 的前提下，无真值全局半盲多普勒搜索 `SBGdop` 在 $\rho = 0.10$ 达到 `3.7111 dB`（1% info-FER），以 **`+0.7045 dB`**（95% 配对帧自助法 CI `[+0.5615, +0.7977] >= 0.50 dB`）击败完全无真值的 `CD2`（最优 $\rho = 0.20$ 处 `4.4156 dB`）。
- **核心瓶颈**：当不给定真实时延 $l_i$ 时，在 $\rho = 0.10$（仅 10% 导频能量、90% 未知数据能量）下，`CD2` 自身的导频前端 `pilot_front` 仅在整数多普勒 `{-2..2}` 上搜索导频相关，丢弃了 90% 数据能量，导致 `CD2` 在 $\rho = 0.10$ 恶化至 `7.97 dB`（真时延配旧导频多普勒亦仅达 `6.36 dB`）。
- **阶段 A9 核心问题**：完全移除真实时延 $l_i$（估计器仅接收观测字典 `obs = {'y', 'pilot', 'sigma2'}` 及静态系统常数），第 0 轮半盲增益能否存活并满足相对同帧最优 $\rho$ `CD2` 的 **1% info-FER 增益 95% 配对置信下界 $\ge 0.50\text{ dB}$（`GO`）**？

---

## 1. 数据集严格物理隔离（零数据污染）

1. **开发探索集**：`frames 40500–40579`（仓库历史零接触，用于算法设计、单核耗时摸底与 SNR 括号确认；探索完成后永久锁死规则）；
2. **门控 G1 对照帧**：`frames 41000–41003`（仅用于校验冻结上游与内部算子等价性）；
3. **门控 G3 成本外推帧**：`frames 40900–40903`（4 个独立隔离帧 × `U/G` = 每格 8 次观测，与开发集和确认集均零重叠）；
4. **最终确认集（冻结后仅跑一次）**：**`frames 41500–41819`**（`320` 个全新物理帧 × `U/G` 双场景 = 每格 `640` 次观测，每分片 `8` 帧 × `40` 分片；仓库全历史与开发/门控全程 **100% 零接触**；在其上同步重跑无真值 `CD2`）。

---

## 2. 无真值半盲联合算法（`SBJ`）与实验臂定义

### 2.1 严格仅观测输入与译码后计分不变量
所有 Stage A9 估计器与触发分支仅接受 `obs = {'y', 'pilot', 'sigma2'}` 与静态常数表 `tabs`（由 `N=1024, l_max=102, c1, c2` 预构建），严禁传入 `raw`、`truth` 或显式 `rho`。正式逐键调度入口 `eval_key_arms` 先仅凭 `obs` 完成全部激活实验臂的估计与译码比特决策，最后统一读取 `truth` 计算误码数与真时延命中诊断。利用 `driver.py:observe` 的精确恒等式：
$$P_{\mathrm{pil,obs}} = \frac{1}{N}\|p_{\mathrm{obs}}\|_2^2 = \frac{\rho}{2(1-\rho)}, \qquad s = \frac{1}{\sqrt{P_{\mathrm{pil,obs}} + 0.5}} = \sqrt{2(1-\rho)}$$
仅从 `obs` 还原单位总功率尺度下的 DAFT 时域观测 $r = \mathrm{IDAFT}(s\cdot y_{\mathrm{obs}})$、导频 $p_t = \mathrm{IDAFT}(s\cdot p_{\mathrm{obs}})$、数据方差 $v_d = 0.5 s^2 = 1-\rho$ 与噪声方差 $\sigma^2 = s^2 \sigma^2_{\mathrm{obs}}$。

### 2.2 触发式接收机架构与五条实验臂
所有接收机共享完全相同的标准两轮 `F0` 前端（`stage3.e1.f0_state(ctx, obs)`）：
- 若 `F0` 已满足校验子 `syndrome == 0`，所有实验臂直接输出 `F0` 译码比特（零额外触发开销）；
- 仅当 `F0` 触发（`syndrome != 0`，与 `CD2`、`HG` 完全相同的触发集与计时起点）时，各臂在完全相同的 `obs` 上执行各自的无真值恢复分支，且 `CD2`、`Ctrl` 与 `SBJ` 各档位共享完全相同的双遍 `CODELAY` 续跑数值回退与有限性检查（`_run_cd2_continuation_notruth`）：

1. **`CD2`（主基线，无真值）**：在 `F0` 终态 `arrays_f0` 上运行最多 2 遍条件 `CODELAY` 几何重开续跑（第 1 遍 `syndrome == 0` 立即早停，否则执行第 2 遍）。评估网格：$\rho \in \{100, 150, 200, 250\}$。
2. **`Ctrl`（单因子对照：`CD2` 自身时延前端 + `SBG` 多普勒，无真值）**：严格保留 `CD2` 第 0 轮信道估计输出的时延支撑与顺序 `l_cd = arrays_f0['r0_delays']`，在 `l_cd` 上运行双路旁瓣逃逸 + 循环分块 Takahashi `L-BFGS-B` 全局半盲多普勒估计（`sbg_ctrl_fast`），将 `nu_sbg` 经严格保序权重 `g_order_preserve` 注入 `f0_injected_no_pf`（第 0 轮 `rounds=0` 用同一公式重解导频 LS 增益，第 1 轮与 2 遍 `CD2` 续跑与基线完全相同；门控 G1b 显式将 `CD2` 原第 0 轮多普勒 `arrays_f0['r0_dopplers']` 注回该路径，验证逐位复现 `CD2` 的第 0/1 轮状态及终态译码结果）。评估网格：$\rho \in \{100, 200\}$。
3. **`SBJ`（主无真值接收机：双束半盲联合时延-多普勒-增益恢复）**：
   - **连续多普勒导频图 + 内部无卷绕数据互相关滞后谱**：在全部整数时延 $l \in \{0,\dots,102\}$ 上计算 `0.05` bin 步长的连续多普勒导频相关谱 $Z_{\mathrm{pil}}(l,\nu)$，并在 $k \in [l_{\max}, N)$ 上经单次批量 FFT 计算全部滞后 $d \in \{1,\dots,102\}$ 的数据自相关峰值与多普勒差；
   - **未建模路径对角方差保底与双束种子规则**：在 $m < P$（$P=8$）前向生长阶段使用 $r_{\mathrm{tot\_var}} = \max(\sigma^2 + 0.25 v_d, \frac{1}{N}\|r\|_2^2 - \frac{1}{N}\|p_t\|_2^2)$ 作为带状高斯协方差对角保底；当 `n_beams = 2` 时，第 2 束在已评估的候选双径对中选取与第 1 束双径时延不交（`set(cand) & set(seed0) == empty`）的最低 NLL 对；若已评估的候选对中不存在与第 1 束不交的对，则回退至与第 1 束双径集合不同的次优已评估对（`set(cand) != set(seed0)`）；生长途中在 $m=2, 5, 8$ 采用经 `fftshift` 单调频移抛物线插值与精确逆滞后相位修正（$c_{ji} = c_{ij}^* e^{-j \frac{2\pi}{N}(l_i - l_j)\Delta\nu_{ij}}$）的闭式互相关 + 相干导频对齐更新参数；
   - **弱径排除原位单轮交换与全长循环精修**：对最优束最弱 3 条路径执行 1 轮排除当前原时延（`l != sel_l[slot]`）的候选换径后，执行双路旁瓣逃逸 + 全 1024 点循环分块 Takahashi `L-BFGS-B` 精修，随后送入第 0 轮（`syndrome == 0` 早停）$\to$ 第 1 轮（`syndrome == 0` 早停）$\to$ 共享 2 遍 `CD2` 续跑。评估网格：$\rho \in \{100, 150\}$。
4. **`SBJ_lite`（增益-成本曲线达标锚点：单束 + 1 轮交换，目标每触发 CPU $\le \mathrm{HG} \approx 640\text{ ms}$）**：`n_beams = 1, n_seed_pairs = 10, cand_top_k = 5, swap_rounds = 1, post_escape = False, include_pw = False, final_maxiter = 10`。评估网格：$\rho \in \{100, 150\}$（Tier-2 回退时仅评估 $\rho = 100$）。
5. **`SBJ_ultra`（增益-成本曲线超低开销锚点：单束零交换）**：`n_beams = 1, n_seed_pairs = 7, cand_top_k = 4, swap_rounds = 0, escape_peaks = 1, post_escape = False, final_maxiter = 8`。评估网格：$\rho \in \{100\}$。

---

## 3. 确认集 SNR 网格（强制全穿越点 $\le 0.50\text{ dB}$ 括号约束）与累计预算封顶

### 3.1 候选确认网格方案（单位：`centi-dB`，相邻步长全部 $\le 50$ 即 $\le 0.50\text{ dB}$）
- **方案 Tier-1（完整五臂确认网格，首选）**：
  - `CD2`：$\rho=100$ `(550, 600, 650, 700, 750, 800, 850, 900)`；$\rho=150$ `(375, 425, 475, 525, 575)`；$\rho=200$ `(375, 400, 425, 450, 500)`；$\rho=250$ `(400, 450, 500, 550)`。
  - `Ctrl`：$\rho=100$ `(450, 500, 550, 600, 650, 700, 750, 800, 850)`；$\rho=200$ `(375, 400, 425, 450, 500)`。
  - `SBJ`：$\rho = 100$ `(325, 350, 375, 400, 425, 475)`；$\rho = 150$ `(325, 375, 425, 475)`。
  - `SBJ_lite`：$\rho = 100$ `(325, 350, 400, 450, 500)`；$\rho = 150$ `(325, 375, 425, 475)`。
  - `SBJ_ultra`：$\rho = 100$ `(350, 400, 450, 500, 550)`。
- **方案 Tier-2（紧凑回退方案 1）**：仅省去 `SBJ_lite` 的 $\rho = 150$ 网格，其余与 Tier-1 完全相同。
- **方案 Tier-3（核心增益-成本回退方案 2）**：省去 `SBJ_lite` 的 $\rho = 150$ 与 `SBJ_ultra` 网格，完整保留 `CD2`、`Ctrl`、`SBJ` 与 `SBJ_lite@100`。
- *(冻结前 G3 门控拦截与修订记录：首版 400 帧 81 格方案在隔离帧 `40900–40903` 上实测单帧 `99.41 s`，外推 `13.87 h > 8.90 h` 预算上限被 G3 正常拦截 `FAIL_BUDGET`，其 `0.1265` 核时已永久记入 `out/stageA9/cpu_ledger.jsonl` 且未接触任何 `41500+` 确认帧；据此在冻结前将确认集定为 `320` 帧 `41500–41819` 并将 `CD2@150`、`CD2@250` [如 `[4.50, 4.75]` 扩为 `[4.50, 5.00] dB`]、`SBJ@150` 等非主峰网格由 `0.25 dB` 收紧为 `0.50 dB` 步长，主对比峰 `SBJ@100` `3.25..4.25 dB` 与 `CD2@200` `3.75..4.50 dB` 仍保持 `0.25 dB` 步长，全表相邻间距严格 $\le 0.50\text{ dB}$。)*

### 3.2 全任务统一防漏账本、进程组监督与累计 `<= 20.0` 核时硬封顶
- 前期 `deinlab` 开发探索累计实耗固定为 **`PRIOR_DEV_HOURS = 10.65` 核时**；
- `gate`、`run`、`timing` 强制绑定同一规范账本路径 `out/stageA9/cpu_ledger.jsonl`（禁止命令行分离账本，`run` 与 `timing` 显式校验 `ledger_path` 与 `gate` 一致）：启动脚本在单一锁下于启动前预登记 `attempt_id` 与预留额度（`STARTED`），通过 `setsid` + `timeout --foreground` 将 `/usr/bin/time`、`timeout`、Python 及全部子进程纳入同一进程组，注册 `SIGTERM -> SystemExit(143)` 并在退出时整组回收后对账（取 Python `rusage` 与外层 `time` 实耗最大值；若发生未捕获硬崩溃则按预留额度入账）；
- `cmd_gate` 硬上限设为 `0.35` 核时，按并发数扣除轮询与汇总余量 `12 * W + 20` 秒（确保 4 帧隔离测试在 Tier-1 偏慢时仍能完整测完并独立判定 Tier-2 / Tier-3 回退方案，实际仅按实耗约 `0.05 h` 记入账本）；
- `cmd_run` 读取 `PRIOR_DEV_HOURS + sum(prior_attempts)`，扣除安静计时预留 `0.22 h` 与安全余量 `0.10 h` 得到 `effective_run_cap`，在分片运行中按并发数扣除 `12 * W + 60` 秒（`W=32` 时为 `444s`）轮询与自助法分析余量实时拦截，并在完成汇总写盘前再次核验累计总核时 `< 20.00` 核时；`cmd_timing` 在触发筛选循环与正式计时循环中均实时核验剩余预算；
- G3 在 4 个隔离帧 `40900–40903` 上统一用 `time.process_time()` 度量 Tier-1、Tier-2、Tier-3 的单帧平均 CPU 秒数，按 **`raw_hours = mean_cpu_sec_per_frame * 320 / 3600`**（等价于 4 帧总耗时 × `80`）计算 `projected_hours = raw_hours * 1.25 + 0.06 <= effective_run_cap`。

---

## 4. 门控 G1–G3（`out/stageA9_gate.json`，全部通过方可冻结确认运行）

1. **G1（边界、触发覆盖与算子逐位等价检验，在归档帧 `41000–41003` 上执行，强制要求覆盖 $\ge 2$ 个实际触发键）**：
   - **G1a（实际调度入口真值篡改不变量）**：在同一 `obs` 上两次调用正式逐键调度器 `eval_key_arms`（激活 `CD2, Ctrl, SBJ, SBJ_lite, SBJ_ultra`），第二次传入完全篡改的伪造 `truth`，验证全部实验臂（含已触发键）的 `decoded_sha`、校验子、`triggered` 与估计支撑/多普勒 **100% 逐位一致**；
   - **G1b（`Ctrl` 单因子全状态回注逐位恒等检验 + `f0_injected_no_pf` 位精确等价）**：一方面验证 `f0_injected_no_pf` 与 `stageA2.f0_true(..., 'ls')` 全部第 0/1 轮数组逐位一致；另一方面将 `CD2` 自身第 0 轮多普勒 `arrays_f0['r0_dopplers']` 注回 `Ctrl` 路径，验证第 0 轮输出、第 1 轮完整续跑输入数组（`r1_delays, r1_dopplers, r1_gains, r1_decoded, r1_app, r1_check`）、最终续跑遍数 `passes_used`、校验子 `syndrome` 与最终译码比特 `decoded` **100% 逐位完全复现基线 `CD2`**；
   - **G1c（循环分块快速梯度精确性）**：验证 `cyclic_nll_and_grad(..., use_c64=False)` 与 `stageA5.sb_nll_and_grad` 的 NLL 与全部 $3P$ 维梯度最大绝对误差 `< 1e-10`。
2. **G2（12 份冻结上游代码 MD5 强校验）**。
3. **G3（隔离帧 `40900–40903` 同口径 CPU 成本外推与方案锁定）**。

---

## 5. 安静单核计时面板（`stageA9.py timing`）

启动脚本在当前允许亲和核集合（`sched_getaffinity`）内读取 `/sys/devices/system/cpu/cpu*/topology/thread_siblings_list`，采样 `/proc/stat` 校验同物理核全部超线程（SMT siblings）最大繁忙率 `< 5%`（硬上限 `< 10%`）后以 `taskset -c <idle_cpu>` 绑定单核；`cmd_timing` 在确认集 `41500–41819` 上按确定性顺序抽取 `rho100_snr400` 与 `rho200_snr450` 两个面板（各 `40` 个触发键：`20 U + 20 G`），对 `CD`、`CD2`、`HG`（无真值续跑实现 `_run_hg_continuation_notruth`，与其余各臂完全一致在 `syndrome_weight` 决策就绪处停表，预热时与 `hs_arms.run_hg_arm` 做逐位等价校验）、`Ctrl`、`SBJ_ultra`、`SBJ_lite`、`SBJ` 七条触发分支同步测量 `time.process_time()`（主指标：每触发纯 CPU 毫秒）与 `perf_counter()`，报告 `mean / median / p95` CPU 毫秒及 **`mean` 与 `p95` 相对 `CD2`、`HG` 的倍数**，读取确认集全 `320` 帧实测分场景 `U / G` 触发率分别计算分场景与等权全帧摊销 CPU 耗时，并写入 `RESULTS.md` 增益–成本曲线表。

---

## 6. 冻结统计判读规则（跑后严禁改标）

- **主对比统计量**（`stageA2.crossing` 1% info-FER，先分别求 `U` 与 `G` 穿越点再取等权均值 $\bar{C} = \frac{1}{2}(C_U + C_G)$，`320` 物理帧配对自助法 `2,000` 次抽样，`seed = 20261125`）：
  $$D = \min_{\rho \in \{100,150,200,250\}} \bar{C}_{\mathrm{CD2}}(\rho) \;-\; \min_{\rho \in \{100,150\}} \bar{C}_{\mathrm{SBJ}}(\rho)$$
- **同量括号与全候选 $\rho$ 封堵检查（任务书第 3 条）**：
  - 对每个 `(arm, rho)`，分别检验 `U` 与 `G` 的 1% FER 穿越点是否均被间距 $\le 0.50\text{ dB}$ 的相邻实测 SNR 点严格夹住，并用完全相同的量构造等权均值无插值经验括号 $[\frac{1}{2}(L_U + L_G), \frac{1}{2}(U_U + U_G)]$（宽度 $\le 0.50\text{ dB}$）；
  - 某实验臂跨 $\rho$ 最小穿越点视为“已有效括号化”（`min_bracketed = True`），当且仅当：(i) 所选最优 $\rho^*$ 的 `U` 与 `G` 均满足 $\le 0.50\text{ dB}$ 括号；且 (ii) 该实验臂任何其他参评 $\rho$ 均未出现“首档 SNR 即 $\le 1\%$（`starts_at_or_below_1pct`，即潜在更优但低于网格下界）”或“宽度 $> 0.50\text{ dB}$ 的括号下界低于最优 $\bar{C}(\rho^*)$”。对标准及 Haldane 零错修正下的全部主/次对比、单臂表与分场景表，任何未夹住项均统一将无穷界规范化为 `"-inf"` / `"+inf"`（严格通过 `json.dumps(..., allow_nan=False)`）且仅报保守区间界，不报单点插值；
- **唯一互斥主裁决（任务书第 1 条硬门槛）**：
  - **`INCONCLUSIVE_UNBRACKETED`**：`CD2` 或 `SBJ` 的跨 $\rho$ 最小穿越点不满足上述 `min_bracketed` 检查（直接停机汇报，严禁宣称 `GO`）；
  - **`GO`**：两侧均满足 `min_bracketed == True`，且 95% 配对自助法置信下界满足有限且 **$\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$**；
  - **`STOP`**：两侧均满足 `min_bracketed == True`，且 **$\mathrm{LB}_{95}(D) < 0.50\text{ dB}$**（含因重抽样删失使第 2.5 百分位下界落为 $-\infty$ 的情形，因 $-\infty < 0.50\text{ dB}$ 不满足 `GO` 条件，统一判为 `STOP`）。
- **Haldane 零错截底敏感性**：以 `0.5 / 320 = 1.5625e-3` 替换 `10^{-4}` 重算主对比、全部单因子对照与增益–成本次要对比，并按修正后选出的最优 $\rho$ 重新核验括号，完整写入 `results.json` 与 `RESULTS.md`。

---

## 7. 跑前概率预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **Claude（任务书给定先验，探索前固定）**：
  - `A9-C1`：主裁决 `GO`（$\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$）：**`.40`**
- **agy（执行代理，基于开发集探索后、未接触任何 `41500–41819` 确认帧前给出）**：
  - `A9-G1`：主裁决 `GO`（$\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$ 且全穿越点满足 $\le 0.50\text{ dB}$ 括号）：**`.68`**
  - `A9-G2`：单因子对照 `Ctrl`（`CD2` 时延前端 + `SBG` 多普勒）跨 $\rho$ 最优穿越点相对最优 $\rho$ `CD2` 的增益点估计 $< 0.20\text{ dB}$：**`.85`**
  - `A9-G3`：安静单核计时中 `SBJ_lite` 每触发平均 CPU 耗时 $\le \mathrm{HG}$ 平均 CPU 耗时（且在 $\rho=0.20, 4.5\text{ dB}$ 面板 $\le 640\text{ ms}$），同时 `SBJ_lite` 相对 `CD2` 点估计增益 $\ge +0.45\text{ dB}$：**`.78`**
