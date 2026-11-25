# 阶段 A6：半盲第 0 轮多普勒估计的端到端 FER 天花板检验——协议（`STAGEA6_PROTOCOL.md`）

**状态**：FROZEN（已按 Sol 静态审查 `out/stageA6_sol_review.md` 修复全部 5 项，待运行 G1–G3 门控并提交 `Before data-pilot-fer stage A6 ...`）
**承接**：
- [STAGEA5_READOUT.md](STAGEA5_READOUT.md)：给定真时延时，半盲高斯 ML 估计器 `SB` 在 4 dB、$\rho \in \{0.10, 0.15\}$ 达到 `0.0527 / 0.0430` bin（`PASS`），但存在弱径离群尾（`23.3% / 18.6%` 路径 $> 0.25$ bin）。
- [sameframe_cd2_20261125/READOUT.md](../sameframe_cd2_20261125/READOUT.md)：在帧 `41000–41399` 上，基线 `CD2` 最优 1% FER 交叉点为 `4.4156 dB`（$\rho=.20$），对照 `s050 = 3.4559 dB`、`s100 = 3.8391 dB`、`ldop = 3.4518 dB`（均在 $\rho=.10$）。

### 冻结前修订（响应 Sol 静态审查 `out/stageA6_sol_review.md`）
1. **归档网格直接复用冻结常量并提前预加载**：移除硬编码的 `CD2_SNRS`（修正 `350` 笔误为冻结的 `1100`），改为直接引用 `sameframe.PART1_SNRS`、`stageA2.SNRS`、`stageA3.SNRS`，并在 G1–G3 门控与主跑起工作进程前提前加载校验全部对照组网格完整性。
2. **消除第 0 轮路径排序对真增益的依赖**：`SBdop` / `PWdop` 调用 `stageA2.f0_true(C, obs, pert, 'ls')` 时将 `pert['g_i']` 替换为各自的估计增益 `g_sb` / `g_pw`（`twofft.time_refine(..., rounds=0)` 仅用 `g_i` 对 8 条独立真时延排序，随后的导频 LS 增益由接收机在 8 条径上联合求解），确保两臂完全不接触 `truth['g_i']`；仅在 G1 `ldop` 复现检验中传 `g_order=None` 以逐位复现 `stageA2`。
3. **截尾 `'+inf'` 解析与空子集渲染保护**：`_to_float_bound` 兼容 `'+inf'`/`'inf'`/`'-inf'`；`render_results_md` 对空子集占比安全输出 `N/A`，并在 `test_stageA6.py` 中补充对应单测。
4. **G2 直接覆盖主入口并补全 A5 存档核对**：G2 直接调用主跑函数 `eval_key` 验证 `stageA5` 复现；主跑启动同时校验 `stageA5` 归档并在 `a5_4db_subset_check` 中输出 A6 与 A5 存档均值及绝对差。
5. **启动脚本提前注册锁清理**：`stageA6_launch.sh` 在 `mkdir "$LOCKDIR"` 成功后立即注册 `EXIT` 清理 trap，避免切目录或激活环境异常时遗留锁。
6. **响应首轮 G3 成本门控（Eric 批准方案 1，发生于冻结提交之前）**：首轮 G3 28 键分层实测 5 档 `(250, 300, 400, 450, 500)` 外推 `41.45 > 40.0` 核时；因真多普勒上界 `ldop` 在 `3.0 dB` 的实测 FER 已达 `41.75%–78.50%`（远高于 `1%`），`2.5 dB` 不参与 1% FER 插值，经 Eric 批准维持 `40.0` 核时预算上限不变，在 §3 降档阶梯末尾新增 4 档 `(300, 400, 450, 500)`（外推约 `33.50 <= 40.0` 核时），其余模型、实验臂与判读规则不变。

---

## 1. 核心问题

在**已知真时延** $l_i$ 且第 0 轮多普勒采用 Stage A5 半盲高斯 ML 估计 `SB` 的条件下，端到端接收机（`SBdop`）在相同帧 `41000–41399`（U/G 均值）的 **1% info-FER 交叉点**能领先现行最强基线 `CD2` 多少 dB？

---

## 2. 实验臂（相对 Stage A3 的单因素改动，不修改任何冻结文件）

精确复用 `stageA3.one_arm` 的接收机链路，唯一改动是将注入给 `stageA2.f0_true(C, obs, pert, 'ls')` 的 `pert['k_real']` 从 `truth + sigma*z` 替换为该键实测的连续多普勒估计 $\hat{\nu}$；复增益保持 `stageA2.f0_true(..., 'ls')` 的导频最小二乘解；若 F0 校验子非零（`syndrome != 0`），按 `stageA3` 完全一致调用 `stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')`；全部译码错误均对照真实 `truth` 计分。

1. **`SBdop`（主臂）**：$\hat{\nu} = \text{stageA5.estimate\_sb}$ （从该键的 `stageA5.estimate_pw` 初值出发，输入为该键原始 `raw['y']`、`raw['pilot']`、`raw['data']` 方差 $v_d$、`raw['sigma2']` 与真时延 `truth['l_i']`，绝不使用真多普勒或真增益）。
2. **`PWdop`（诊断臂）**：$\hat{\nu} = \text{stageA5.estimate\_pw}$ （仅真时延 + 连续导频变量投影 LS，用于拆分"真时延 + 连续导频 LS"本身与"半盲协方差项"各自贡献的 FER 增益）。

---

## 3. 数据网格与归档复用

- **新跑网格**：帧 `41000–41399`（400 物理帧）× 场景 `U/G` × $\rho \in \{100, 150\}$ permille × 初始候选 SNR `{200, 250, 300, 400, 450, 500, 550}`（2.0–5.5 dB，7 档）。
- **预算与逐级降档规则（G3 门控执行）**：总 CPU 预算上限 **`40.0` 核时**（按实测分层耗时 × `1.3` 外推），工作进程 `<= 32`（固定 `32`）。按顺序尝试：
  1. 全部 7 档 `(200, 250, 300, 400, 450, 500, 550)`；
  2. 若超 `40.0` 核时，先删 `550` → 6 档 `(200, 250, 300, 400, 450, 500)`；
  3. 若仍超 `40.0` 核时，再删 `200` → 5 档 `(250, 300, 400, 450, 500)`；
  4. 若仍超 `40.0` 核时，再删 `250` → 4 档 `(300, 400, 450, 500)`（Eric 批准方案 1）；
  5. 若仍超则停机汇报。选定网格写入 `out/stageA6_gate.json` 并于冻结前记录。
- **不重跑已归档对照组**：`CD2`、`s050`、`s100`、`ldop`（及 `full`）直接读取 deinlab 上已冻结的 `sameframe_cd2_20261125`、`stageA`、`stageA2`、`stageA3` 原始分片，并在门控与读出阶段逐一核验其 `REMOTE_ROWS_MD5.txt` 清单 SHA-256 及每个分片文件的 MD5。

---

## 4. 门禁 G1–G3（`out/stageA6_gate.json`，全部通过方可启动主跑）

- **G1（`ldop` 精确复现）**：4 个来自 `stageA2` 的键上，令 $\hat{\nu} = \text{truth['k\_real']}$，`one_arm_nu` 的 `syndrome`、`f0_errors`、`errors` 与归档 `stageA2` 的 `ldop` 臂逐位完全一致（4/4）。
- **G2（`stageA5` 估计复现）**：4 个来自 `stageA5` 的键（`frames 41000–41099`, 4 dB, $\rho \in \{.10, .15\}$）上，调用 `stageA5.estimate_sb` 所得逐径 $|\hat{\nu}_i - \nu_i|$（及功率加权指标）与 `stageA5` 远端原始行 `abs_err['SB']` 的最大绝对差 `< 1e-6`（注：`stageA5` 原始行落盘了全部 8 径的精确 `abs_err['SB']` 与 `metric['SB']`）。
- **G3（分层成本外推 ×1.3，$\le 40.0$ 核时，$\le 32$ 进程）**：在隔离帧 `41400–41403` 上对全部 7 个 SNR 各测 4 键（覆盖 `U/G` × `rho 100/150`，共 28 键），按各 SNR 实测均值外推全网耗时 × `1.3`（加 `0.15` 核时 IO/分析余量），按 §3 降档规则选定符合 `<= 40.0` 核时的 SNR 网格。

---

## 5. 冻结判读规则（跑后永不改标）

- **交叉点定义**：`stageA2.crossing`（1% info-FER，log10 线性插值），U/G 等权平均；含截尾保守上下界处理（完全复用 `sameframe_cd2.analyze_partA` 与 `sameframe.crossing_bounds_stageA2`）。
- **主估计量**：
  $$D = \min_{\rho \in \{100,150,200,250\}} C_{\mathrm{CD2}}(\rho) \;-\; \min_{\rho \in \{100,150\}} C_{\mathrm{SBdop}}(\rho)$$
- **联合配对自助法**：按 400 个物理帧（`41000–41399`）联合重采样（`2,000` 次，`seed = 20261125`），与 `sameframe_cd2.analyze_partA` 权重矩阵生成序列完全一致，取 95% 百分位区间（截尾时用保守秩次区间）。
- **唯一互斥判定表**：
  - **`GO`**：95% CI 下界 $\ge 0.5\text{ dB}$（下一步：放开未知时延）
  - **`STOP`**：95% CI 上界 $< 0.3\text{ dB}$（终止第 0 轮多普勒线，转写论文）
  - **`ERIC`**：其余情况（交由 Eric 裁决）
- **描述性次要读数**：
  1. `SBdop`、`PWdop` 各 $\rho$ 的 U/G 与均值 1% FER 交叉点；
  2. 带 95% CI 的对照差值：`SBdop − s050`、`SBdop − ldop`、`CD2 − PWdop`（及 `PWdop − SBdop`）；
  3. `SBdop`（与 `PWdop`）在各 SNR 下的第 0 轮多普勒误差（及 4 dB 下对 `41000–41099` 200 抽样子集与 Stage A5 的一致性核对）；
  4. `SBdop` 的 F0 失败键中存在离群路径（$> 0.25$ bin）的占比（分别报告：任意径离群、弱径离群（功率低于中位数）、仅弱径离群、强径离群，并与 F0 成功键对照）；
  5. 单键 `SB`（及 `PW`）CPU 耗时均值/中位/p95。

---

## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **Claude**：
  - `A6-C1`（主判定）：`GO` .45 / `ERIC` .45 / `STOP` .10
  - `A6-C2`（交叉点）：`SBdop` 最优 1% FER 交叉点落在 `[3.50, 3.80] dB`：.55
- **agy（Gemini 4 Neon）**：
  - `A6-G1`（主判定）：`GO` .50 / `ERIC` .42 / `STOP` .08
  - `A6-G2`（交叉点）：`SBdop` 最优 1% FER 交叉点落在 `[3.50, 3.80] dB`：.60

---

## 7. deinlab 执行规范

- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，日志首行打印 `sys.executable`）。
- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp`、`/dev/shm` 或 `/home/guoyikun`；`tmux` 会话名 `g_a6`；工作进程 `32`。
- 原始逐键分片（`out/stageA6/raw/rows_shard*.jsonl.gz`）留远端并记录 MD5 到 `out/stageA6/REMOTE_ROWS_MD5.txt`；本地回传 `out/stageA6_gate.json`、`out/stageA6/{results.json,RESULTS.md,REMOTE_ROWS_MD5.txt,STATUS,run.log,run_cpu.txt}`。
