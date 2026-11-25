# 低导频第 0 轮多普勒余量再判（以 CD2 为新基线）与安静计时面板协议（`sameframe_cd2_20261125`）

**状态**：FROZEN（已按 Sol 静态审查意见修复全部 5 项，冻结提交后启动）
**承接**：[sameframe_hg_20261124/READOUT.md](../sameframe_hg_20261124/READOUT.md)。此前 P1 对 `HG` 为 `INCONCLUSIVE`（`+0.7333 [+0.4549, +1.0396] dB`），而 P2 表明两遍局部交换 `CD2` 在黄帧 `5400–5799` 上已追平并微幅超过 `HG`（`−0.1246 dB`），因此当前正确基线转为 `CD2`。

---

## 1. 核心问题

1. **Part A（主裁决 `P1'`，低导频帧 `41000–41399`）**：以两遍局部交换 `CD2` 为基线后，在低导频比例下，更优第 0 轮多普勒估计（代理 `s100`：真时延 + 高斯多普勒误差 $\sigma = 0.10$ bin，实测第 0 轮均值 $|\Delta\nu|\approx 0.080$ bin，导频 LS 增益）是否仍留有 $\ge 0.5$ dB 的 1% FER 余量？同时在同帧补测 `CD2e8` 并与已归档的 `HG`/`HGint`/`s050`/`ldop`/`full`/`delay`/`base` 联合配对比较。
2. **Part B（安静单核计时面板，描述性无裁决，论文表格用）**：在 `HG`/`CD2` 共同最优点 $(\rho=0.20, 4.5\text{ dB})$ 与历史连续点 $(\rho=0.30, 5.0\text{ dB})$ 上，于 `taskset` 绑定单空闲核上以统一决策就绪边界实测 `CD`、`CD2`、`CD2e8`、`HG`（含 `HG1`）、`HGint` 的单触发延迟、第二遍比例、全帧摊销耗时及相对 `CD` 比值。

---

## 2. 实验设计与代码复用（不改任何冻结文件）

所有逻辑直接复用已有模块：`experiments/sameframe_hg_20261124/sameframe.py`（`load_stage_runtime`、`run_cd_two_pass`、`load_stageA_base`、`verify_manifest`、`_select_balanced_keys`、`_spawn_map`、`_run_sharded_phase`、`_write_gzip_jsonl_atomic`、`crossing_bounds_stageA2`）、`experiments/huang_steelman_20261124/hs_arms.py`（`run_hg_arm`、`fine_grid`、`coarse_grid`、`load_archived_rho_sweep`）、`experiments/data_pilot_fer_20261121/{stageA,stageA2,stageA3}.py`。

### Part A（帧 `41000–41399`，场景 U/G）
- **网格**：$\rho \in \{100, 150, 200, 250\}$ permille，`SNR = stageA.SNRS`（3..12 dB 共 13 点）；总计 41,600 键，其中归档 `stageA` `arms.base.syndrome != 0` 的触发键共 **13,735** 键。
- **逐键规则**：
  - 未触发键（`arms.base.syndrome == 0`）：不重跑，直接取 `arms.base.f0_errors`。
  - 触发键：重跑 `f0_state`，断言实时 `syndrome == arms.base.syndrome` 与 `f0_errors == arms.base.f0_errors`；随后运行 `CD2`（`arm_spec='A1'`，第 1 遍断言 `errors == arms.base.errors`；若第 1 遍 `syndrome != 0` 则按与 `HG` 相同的 `r1_*` 消息更新跑第 2 遍，校验通过提前停止）与 `CD2e8`（运行时 `A1e8` 克隆包装，`max_edits=8`，同两遍早停规则）。均禁用静默回退（`numerical_fallback=True` 或非有限值直接抛错）。
- **同帧归档对照（不重跑，全部 MD5 校验）**：
  - `stageA`（`base`/`delay`）、`stageA2`（`full`/`ldop`）、`stageA3`（`s025`/`s050`/`s100`/`s200`）、`sameframe_hg_20261124` Part 1（`HG`/`HG1`/`HGint`，清单 SHA-256 `7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f`）。
- **代理局限说明（跑前写定）**：`s100`/`s050` 为**带真时延**的高斯多普勒注入；Stage A3 已表明真实导频多普勒误差比同均值高斯误差温和，而未知时延下的真实半盲估计又会带来额外损失，故 `s100` 是结构化代理而非端到端估计器。

### Part B（安静单核计时面板，黄帧 `5400–5799`，不设裁决）
- **两组工况**（均从 `rho_sweep_20261119` 按帧号升序抽取）：
  1. **最优点面板**（$\rho=0.20, 4.5\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `199/400 (49.75%)`、G `227/400 (56.75%)`。
  2. **连续性面板**（$\rho=0.30, 5.0\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `88/400 (22.00%)`、G `110/400 (27.50%)`。
- **计时臂与顺序**：5 臂 `('CD', 'CD2', 'CD2e8', 'HG', 'HGint')`（同时由 `HG` 第 1 遍免费记录 `HG1`）；按场景 U/G 分别维护轮换位置 `scenario_pos[s] % 5`，使两场景内每臂在 5 个顺序位各出现 10 次。
- **计时边界与一致性**：统一采用 `hs_arms` 的**决策就绪边界**（从分支消息准备/入口开始，到最终 `syndrome_weight` 结束立即停表；真值计分与哈希置于停表之后）。每个计时键逐位核验 `decoded_sha` 与归档一致（`F0`/`CD` 核 `rho_sweep`，`HG`/`HG1`/`HGint` 核 `huang_steelman`，`CD2`/`CD2e8` 核 `sameframe_hg` Part 2）。
- **隔离与绑核**：启动 Python 前扫描 `/proc/stat` 选出最空闲单核并用 `taskset -c <CPU>` 绑定运行，记录启动前空闲利用率和起止系统负载。原始逐键计时写入远端 `out/raw/timing_rows.jsonl` 并记录 MD5。

---

## 3. 门禁与预算（G1–G3，写入 `out/gate.json`）

- **G1（Part A F0 复现）**：20 个 `stageA` 触发键（4 个 $\rho$ 各 5 键，覆盖 U/G 与高/低 SNR），实时 `f0_state` 与归档 `syndrome`/`f0_errors` 20/20 一致。
- **G2（Part A `CD2` 首遍复现 + 两遍/多换冒烟）**：20 个低导频 `stageA` 触发键上，`CD2` 第 1 遍逐键复现 `stageA` `arms.base.errors`（20/20）；验证 `CD2` 与 `CD2e8` 均实际触发了第 1 遍早停与第 2 遍续跑路径，且全程无 `numerical_fallback` 与非有限值。
- **G3（分层成本外推，×1.3 余量，$\le 6.0$ 核时）**：在 Part A 全部 8 个 $(\rho, \text{SNR 层})$ 各抽 4 键（共 32 键，U/G 平衡、内分位点）实测 `f0 + CD2 + CD2e8` CPU 时间，按精确触发键数（13,735）加权求和，加上 Part B 计时预留（`0.18 h`）及读写汇总余量（`0.12 h`），乘 `1.3×`。
  - **预算顺序**：若含 `CD2e8` 外推 $\le 6.0$ 核时则全量运行；若超限则首先从 Part A 去掉 `CD2e8` 重算（Part B 仍保留全部 5 臂以保证论文计时表完整）；若仍超 `6.0` 核时则立即停机（`GATE_STATUS=FAIL_BUDGET`）并向 Eric 汇报。运行中硬停上限为累计 `6.0` 核时（触发写 `STATUS=STOPPED_BUDGET`）。

---

## 4. 冻结判读规则（跑后永不改标）

### 主检验 `P1'`（帧 `41000–41399`）
- **穿越点**：沿用 `stageA2.crossing(fer, snrs)` 在各臂自有 SNR 网格计算 1% 信息位 FER 穿越点，U/G 算术平均。
- **估计量**：$D' = \min_{\rho \in \{100,150,200,250\}} c_{\mathrm{CD2}}(\rho) - \min_{\rho \in \{100,150,200\}} c_{\mathrm{s100}}(\rho)$（正值表示 `s100` 优于 `CD2`，即仍剩多普勒余量）。
- **自助法**：物理帧配对重采样（`2,000` 次，**`seed = 20261125`**），联合重采样 `stageA`、`stageA2`、`stageA3`、`sameframe_hg` Part 1 与本实验 Part A；取 **95% 百分位区间**（`[2.5, 97.5]`；若出现截断抽样则用保守最近秩界并汇报 `censored_draw_fraction`）。
- **唯一互斥判定表**：
  - `DOPPLER-LINE`：95% CI 下界 $\ge 0.5$ dB
  - `STOP-LINE`：95% CI 上界 $< 0.5$ dB
  - `INCONCLUSIVE`：其余情况

### 次要读数（描述性）
- Part A：同口径下 `CD2e8 − s100`（若保留）、`CD2 − s050`、`CD2 − ldop`、`CD2 − full`、`CD2 − delay`、`CD2 − base`、`CD2 − HG`、`CD2e8 − HG`、`CD2e8 − CD2`；全部臂的逐 $\rho$ 穿越点表与各自最优 $\rho$；`CD2`/`CD2e8` 的第 2 遍救回率与平均换径次数。
- Part B：两组工况下 5 臂（含 `HG1`）单触发均值/中位数/p95、第 2 遍比例、分场景摊销全帧均值耗时，以及相对 `CD` 的均值比、配对中位比与 `CD` 更快占比。

---

## 5. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **Claude**：
  - `CD2-C1`（`P1'` 判定）：`DOPPLER-LINE` .25 / `INCONCLUSIVE` .50 / `STOP-LINE` .25（点估计约 `0.6 dB`）
  - `CD2-C2`（计时）：`CD2` 两遍单触发均值耗时低于 `HG` 均值耗时：.80（按主工作点 $\rho=.20, 4.5\text{ dB}$ 计分，并在读出中同时报告 $\rho=.30, 5.0\text{ dB}$）
- **agy（Gemini 4 Neon）**：
  - `CD2-G1`（`P1'` 判定）：`DOPPLER-LINE` .20 / `INCONCLUSIVE` .65 / `STOP-LINE` .15
  - `CD2-G2`（计时）：`CD2` 两遍单触发均值耗时低于 `HG` 均值耗时（主工作点 $\rho=.20, 4.5\text{ dB}$）：.90

---

## 6. deinlab 执行规范

- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，每份日志第 1 行打印 `sys.executable`）。
- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp` 或 `/home/guoyikun`。
- 并发与会话：Part A 使用 `24` 进程（$\le 32$，兼顾 16 核漏斗），Part B `taskset` 绑定单空闲核；`tmux` 会话名 `g_cd2`。
- 产物留存：大原始分片（`out/raw/partA_shard*.jsonl.gz`、`out/raw/timing_rows.jsonl`）留在 deinlab，MD5 写入本地 `out/REMOTE_ROWS_MD5.txt`；本地保存小汇总（`gate.json`、`results.json`（含 `_argv`/`_config`）、`timing_summary.json`、`RESULTS.md`、`READOUT.md`、`STATUS` 与日志）。
