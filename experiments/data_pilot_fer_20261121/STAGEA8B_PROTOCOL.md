# 阶段 A8b：`3.50 / 3.75 dB` 加密网格消除零错截底插值伪影的 1% FER 决定性复核——协议（`STAGEA8B_PROTOCOL.md`）

**状态**：FROZEN（已按外部 `gpt-6.2-sol` 静态审查 [out/stageA7_A8_A8b_sol_review.md](out/stageA7_A8_A8b_sol_review.md) 修复全部 4 项并通过 `test_stageA8b.py`，待运行远端 G1–G3 门控并提交 `Before data-pilot-fer stage A8b ...` 冻结）
**承接与触发原因**：
- [STAGEA8_READOUT.md](STAGEA8_READOUT.md) & [out/stageA7_A8_A8b_sol_review.md](out/stageA7_A8_A8b_sol_review.md)（Part A `PASS`）：`gpt-6.2-sol` 独立静态审查确认 Stage A7/A8 估计器零真值泄漏、分块三对角快速梯度精确覆盖全部循环带块、四分类 `SEARCH` 与 `GO` 判定逻辑严密；同时确认 Stage A8 在 4 档 SNR 网格 `(300, 400, 450, 500)` 上的残差 `+0.0145 dB`（“`98.5%` 回收率”）依赖 `4.0 dB` 零错 `10^{-4}` 截底插值。
- **独立审阅发现的关键刻度盲区**：
  1. 在缺乏 `(3.0, 4.0) dB` 内部采样点时，若不依赖对数插值而仅用 `4.0000 dB` 作保守上界，则 `4.4156 − 4.0000 = +0.4156 dB`（配对 95% 下界约 `+0.27 dB < 0.50 dB`），**不足以单独证明 `LB95 >= 0.50 dB`**；
  2. `stageA2.crossing` 将 `4.0 dB` 的 `0/400` 截底为 `10^{-4}`（`0.01%`），造成 `0/400`（`3.4664 dB`）与 `1/400`（`3.7438 dB`）之间高达 **`+0.28 dB` 的插值跳变**，对 `[3.4, 3.9] dB` 真实瀑布陡度零测量。
- **冻结前修订（响应 `out/stageA7_A8_A8b_sol_review.md` Part B 全部 4 项）**：
  1. **精确界定双臂差异**：明确说明 `ldop` 严格沿用归档 `stageA2.one_arm(..., 'ls')`（`g_order=None`，第 0 轮 `time_refine(..., rounds=0)` 内部用 `truth['g_i']` 排序时延后重解导频 LS 增益），而 `SBGdop` 传 `g_order=g_sbg`（全程零接触 `truth['g_i']`），故 `SBGdop − ldop` 度量无真值半盲第 0 轮初始化整体相对归档 `stageA2 ldop` 天花板的差距；纯搜索单因素对比由同构 `SBdop − SBGdop_dens` 给出。
  2. **统一 G3 公式并在代码内强约束全任务累计 `< 10.0` 核时**：代码与协议统一采用 `projected = raw_hours * 1.3 + 0.08`；`cmd_gate` 硬执行门控 `<= 0.08` 核时；`cmd_run` 读取实测 `gate_cpu_hours` 与前期已用 `7.0310` 核时，动态收紧 `effective_cap = min(2.45, 10.0 - 7.0310 - gate_cpu_hours - 0.05)` 并在运行循环与收尾双重硬拦截。
  3. **补齐报告字段与单测覆盖**：`RESULTS.md` 同步输出 Haldane 截底下的 `SBGdop_dens − ldop_dens` 敏感性结果，并按分场景 `U / G` 分别报告 `SBG` 截顶 MAE、离群率与相对 `ldop` 配对得失；`test_stageA8b.py` 新增单档 `(375,)` 降档选择与累计预算上限单测。
  4. **启动脚本加固**：`stageA8b_launch.sh` 将 `TMPDIR`、`XDG_CACHE_HOME` 与全部单线程环境变量提前至 `conda activate` 之前，并新增 `INT / TERM` 信号转发与子进程等待清理。

---

## 1. 核心问题与竞争假说

在不改动任何已冻结算法或超参（直接复用 `stageA7.estimate_sb_global` 与 `stageA6.one_arm_nu`）的前提下，将 $\rho = 0.10$ 的 SNR 网格从 `(300, 400, 450, 500)` 加密至 **`(300, 350, 375, 400, 450, 500)`**（在瀑布穿越区达 `0.25 dB` 分辨率），`SBGdop` 相对归档 `CD2` 的 1% info-FER 增益 95% 配对下界是否仍满足 $\ge 0.50\text{ dB}$（`GO`），以及 `SBGdop` 与同网格归档定义真多普勒上限 `ldop` 的真实 1% FER 差距是多少？

- **`H_tight_go`（紧贴上限恢复）**：`SBGdop` 在 `3.50 / 3.75 dB` 紧贴 `ldop`（差距 $\le 0.15\text{ dB}$），加密后 $C_{\mathrm{SBGdop\_dens}}(100) \le 3.70\text{ dB}$，主对比 $\mathrm{LB}_{95}(D_{\mathrm{dens}}) \ge 0.50\text{ dB}$（`GO`）。
- **`H_mod_go`（有效恢复但距 `ldop` 真实差距大于 `0.015 dB` 截底伪影）**：`SBGdop` 在 `3.60–3.78 dB` 穿越 1% FER，比同网格 `ldop` 晚 `0.15–0.30 dB`（揭示 A8 的 `+0.0145 dB` 系 `10^{-4}` 截底低估），但 $\mathrm{LB}_{95}(D_{\mathrm{dens}}) \ge 0.50\text{ dB}$ 依然成立（`GO`）。
- **`H_cliff_stop`（`3.5–3.9 dB` 门限悬崖推翻截底插值）**：`SBGdop` 在 `3.75 dB` 终态 FER 仍显著高于 `1%`，将真实穿越点推至 $\ge 3.80\text{ dB}$，导致 $\mathrm{LB}_{95}(D_{\mathrm{dens}}) < 0.50\text{ dB}$（`STOP`）。

---

## 2. 实验臂定义（零代码复制、零调参）

在每个新增观测键 `(frame, scenario, rho=100, snr)` 上，调用一次 `stage3.observed(ctx, base, rho, snr)`，在同一 `(raw, obs, truth)` 上依次运行：
1. **`SBGdop`**：调用已冻结 `stageA7.estimate_sb_global(stageA5, fgeom, p_t, r, vd, sigma2)`（`maxiter=65, ftol=1e-9`）+ `stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, nu_sbg, g_order=g_sbg)`（全程零接触真多普勒与真增益）；
2. **`ldop`（同帧归档定义真多普勒上限对照）**：调用 `stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, truth['k_real'], g_order=None)`（与 `stageA2` 归档 `ldop` 定义逐位一致，补齐 `stageA2` 缺失的 `350, 375` 档以构成严格同网格配对比较）。

合并既有冻结分片（零重跑，全部经清单 SHA-256 与逐分片 MD5 强校验）：
- `SBGdop_dens`：$\rho=100$ 取 `stageA8` `(300, 400, 450, 500)` $\cup$ 本轮新增档；$\rho=150$ 取 `stageA8` `(300, 400, 450, 500)`（注：$\rho=150$ 在 `4.0 dB` 实测 `U=2/400, G=5/400` 均非零错帧，本身未触发 `10^{-4}` 截底）；
- `ldop_dens`：$\rho=100$ 取 `stageA2` $\cup$ 本轮新增档；$\rho \in \{50, 150, 200\}$ 取 `stageA2`；
- `CD2`、`SBdop`、`PWdop`、`s050`、`s100`：与 Stage A8 完全一致取自冻结归档。

---

## 3. 数据网格与代码强约束预算门控

- **候选新增网格**（帧 `41000–41399` × `U/G`，固定 `rho = 100`）：
  1. 首选双加密档 `(350, 375)`（`3.50 dB` 与 `3.75 dB`，共 `1,600` 键）；
  2. 若 G3 成本外推 `raw_hours * 1.3 + 0.08` 超过有效运行上限，降档为单关键门限档 `(375,)`（`3.75 dB`，共 `800` 键）；
  3. 若仍超上限则停机汇报。
- **代码硬执行全任务 `< 10.0` 核时预算边界**：前期累计实耗 `7.0310` 核时（含开发集 `0.6960 h`、A7 `0.3856 h`、A8 `5.9434 h` 及回退键核验 `0.0060 h`）；`cmd_gate` 硬限 `<= 0.08` 核时；`cmd_run` 动态执行 `effective_cap = min(2.45, 10.0 - 7.0310 - gate_cpu_hours - 0.05)` 核时硬上限，保证全任务累计严格 `< 9.95 < 10.0` 核时。

---

## 4. 门禁 G1–G3（`out/stageA8b_gate.json`，全部通过方可冻结主跑）

- **G1（双臂顺序执行一致性检验）**：在 $\rho=100, \text{SNR} \in \{300, 400\}$ 的 4 个归档键（`41000 U 300`, `41001 G 300`, `41002 U 400`, `41003 G 400`）上调用 `eval_key_a8b`，验证同一次 `observed` 内顺序执行 `SBGdop` 与 `ldop` 后：(i) `SBGdop` 的整数计分字段 `syndrome / f0_errors / errors` 与 `stageA8` 原始分片完全相等且 `sbg_metric`、`max_err` 差 `< 1e-12`；(ii) `ldop` 的整数计分字段 `syndrome / f0_errors / errors` 与 `stageA2` 原始分片完全相等（`4/4`）。
- **G2（全部 7 份归档完整性校验）**：校验 `stageA`、`stageA2`、`stageA3`、`stageA5`、`sameframe_cd2`、`stageA6` 及 **`stageA8`** 的清单 SHA-256 与全部分片 MD5，并预加载验证网格完整性。
- **G3（隔离帧 `41400–41403` 成本外推 `raw_hours * 1.3 + 0.08 <= effective_cap`）**：在隔离帧 `41400–41403` 上对 `rho = 100, snr in {350, 375}` 各测 4 键（覆盖 `U/G`，共 8 键），按实测均值外推选定新增 SNR 档位，且门控自身 CPU `<= 0.08` 核时。

---

## 5. 冻结判读规则（跑后永不改标）

- **主估计量**（`stageA2.crossing` 1% info-FER，U/G 等权均值，`400` 物理帧联合配对自助法 `2,000` 次，`seed = 20261125`）：
  $$D_{\mathrm{dens}} = \min_{\rho \in \{100,150,200,250\}} C_{\mathrm{CD2}}(\rho) \;-\; \min_{\rho \in \{100,150\}} C_{\mathrm{SBGdop\_dens}}(\rho)$$
- **唯一互斥判定表（任务书第 2 条硬门槛）**：
  - **`GO`（值得继续）**：$\mathrm{LB}_{95}(D_{\mathrm{dens}}) \ge 0.50\text{ dB}$；
  - **`STOP`（不值得继续）**：$\mathrm{LB}_{95}(D_{\mathrm{dens}}) < 0.50\text{ dB}$。
- **描述性次要读数与稳健性审计**：
  1. 同加密网格下 $\rho=0.10$ 的真实天花板残差 $C_{\mathrm{SBGdop\_dens}}(100) - C_{\mathrm{ldop\_dens}}(100)$ 及其 95% 配对 CI；
  2. **去 `10^{-4}` 截底敏感性核验**：将零错截底从 `1e-4` 替换为样本量连续性修正 `0.5 / 400 = 1.25e-3`（Haldane 修正）重新计算 $D_{\mathrm{dens}}$ 与 $C_{\mathrm{SBGdop\_dens}}(100) - C_{\mathrm{ldop\_dens}}(100)$（同步写入 JSON 与 `RESULTS.md`），并报告完全不插值的经验括号区间；
  3. $\rho=0.10$ 在全 6 档的分场景 `U / G` 与合并 F0 错帧数、终态错帧数、分场景及合并 `SBG` 截顶 MAE、离群率与相对同帧 `ldop` 的分场景及合并逐键得失计数。

---

## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **agy（审阅代理，基于 `3.0 dB` 与 `4.0 dB` 的 F0/终态错帧计数对比，未接触任何 `3.50 / 3.75 dB` 数据）**：
  - `A8B-R1`：加密网格主判定仍为 `GO`（$\mathrm{LB}_{95}(D_{\mathrm{dens}}) \ge 0.50\text{ dB}$）：`.72`
  - `A8B-R2`：加密网格消除 `4.0 dB` 零错截底后，真实差距 $C_{\mathrm{SBGdop\_dens}}(100) - C_{\mathrm{ldop\_dens}}(100) > 0.05\text{ dB}$（即 Stage A8 的 `+0.0145 dB` 低估了真实残差）：`.70`

---

## 7. deinlab 执行规范

- 激活前先导出 `TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`、`CUDA_VISIBLE_DEVICES=""` 与 6 个单线程环境变量；随后 `conda activate AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），严禁写 `/tmp`、`/dev/shm`、`/home/guoyikun`；`tmux` 会话名 `g_a7_a8b`；工作进程 `32`。
- 原始分片留存远端 `out/stageA8b/raw/rows_shard*.jsonl.gz` 并写入 `out/stageA8b/REMOTE_ROWS_MD5.txt`；回传 `out/stageA8b_gate.json` 与 `out/stageA8b/{results.json,RESULTS.md,REMOTE_ROWS_MD5.txt,STATUS,run.log,run_cpu.txt}`。
