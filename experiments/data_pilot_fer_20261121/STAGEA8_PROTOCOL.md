# 阶段 A8：无真值全局半盲第 0 轮多普勒估计（`SBGdop`）的全帧 1% FER 恢复检验——协议（`STAGEA8_PROTOCOL.md`）

**状态**：FROZEN（承接 Stage A7 确认集 `SEARCH` 判定，完成单测 `test_stageA8.py` 与远端隔离门控 G1–G3 后经 `Before data-pilot-fer stage A8 ...` 提交冻结；注：`/boost` 子代理沙箱策略同样拦截 `codex exec`，由代码级一致性单测与 G1–G3 门控完成冻结前核验）
**承接**：
- [STAGEA7_READOUT.md](STAGEA7_READOUT.md)：在 Stage A6 高 SNR（`4.5–5.0 dB`）全部 `38` 个终态失败键上，高斯半盲似然 `38/38`（`100%`）偏好真值盆地（中位优势 `+74.32` nats），且不改模型、零偷看真值的全局半盲搜索 `SBGdop` 救回 **`38/38`（`100%`）**，冻结判定为 **`SEARCH`**。
- 任务书第 2 条预注册路由：既已确认为 `(a) SEARCH`，在全部 Stage A6 评估帧（`41000–41399`，给定真时延）上对照归档 `CD2` 测试该修复方案；**仅当 1% info-FER 增益的 95% 配对自助下界 $\ge 0.5\text{ dB}$ 时判定值得继续（`GO`）**。

---

## 1. 核心问题与竞争假说

在全部 `400` 个物理帧（`41000–41399` × `U/G`）全网格上，将 Stage A6 的局部梯度半盲估计器 `stageA5.estimate_sb` 替换为 Stage A7 已冻结的无真值全局半盲估计器 `stageA7.estimate_sb_global`（其余接收机链路、高斯半盲似然、参数边界 $[-3,3]^P \times [-10,10]^{2P}$ 与真时延输入完全不变），端到端接收机 **`SBGdop`** 的最优 1% info-FER 交叉点能领先归档最强基线 `CD2`（`4.4156 dB`）多少 dB？

- **`H_recover`（主假说）**：`SBGdop` 在消除 `PW` 强径与中强径旁瓣后无明显误伤回退，在 $\rho \in \{0.10, 0.15\}$ 上逼近 `s050`/`ldop`（`3.45–3.75 dB`），使 $D = \min C_{\mathrm{CD2}} - \min C_{\mathrm{SBGdop}}$ 的 95% 配对下界 $\ge 0.50\text{ dB}$（`GO`）。
- **`H_partial`（部分恢复但未过 0.5 dB 下界）**：`SBGdop` 显著优于 `SBdop`，但在 `4.0 dB` 仍残留 `>1%` 的弱径/噪声边缘错误，致交叉点停在 `3.85–4.10 dB`，95% 下界 $< 0.50\text{ dB}$（`STOP`）。
- **`H_regress`（全局搜索引入误伤回退）**：在原已成功的帧上跳入噪声伪峰导致净回退，$D$ 接近 0 或为负（`STOP`）。

---

## 2. 实验臂（相对 Stage A6 `SBdop` 的严格单因素改动，零重复实现）

直接 `import stageA6` 与 `import stageA7`，不修改任何已冻结文件：
- **`SBGdop`（唯一新跑臂）**：对每个观测键调用 `nu_sbg, g_sbg = stageA7.estimate_sb_global(stageA5, fgeom, p_t, r, vd, sigma2)`（参数 `maxiter=65, ftol=1e-9` 与 Stage A7 完全一致，零调参），随后调用 `stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, nu_sbg, g_order=g_sbg)`。
- **全部对照组取自经 SHA-256 与分片 MD5 全量核验的冻结归档（零重跑）**：
  - `CD2`（`sameframe_cd2_20261125` + `stageA`）；
  - `SBdop`、`PWdop`（`stageA6` 远端原始分片，实现全网 `6,400` 键一对一配对救回/误伤审计）；
  - `s050`、`s100`（`stageA3`），`ldop`、`full`（`stageA2`）。

---

## 3. 数据网格与总预算门控

- **候选网格**：帧 `41000–41399`（400 物理帧）× `U/G` × $\rho \in \{100, 150\}$ × 候选 SNR：
  1. 首选全 Stage A6 网格 `(300, 400, 450, 500)`（4 档，共 `6,400` 键）；
  2. 若 G3 分层成本外推（$\times 1.3 + 0.15\text{ h}$）超出本阶段上限，降档删 `500` → `(300, 400, 450)`（3 档，共 `4,800` 键）；
  3. 若仍超预算则停机汇报。
- **硬预算约束**：全任务累计远端预算上限 `10.0` 核时；前期开发集探索（`0.6960 h`）+ Stage A7 门控与确认跑（`0.3856 h`）已用 **`1.0816` 核时**（剩余 `8.9184` 核时）。设 G3 与主跑合计预算上限：G3 预留 `<= 0.25` 核时，Stage A8 主跑硬上限设为 **`8.20` 核时**（确保全任务总核时严格 `<= 9.55 < 10.0` 核时）。

---

## 4. 门禁 G1–G3（`out/stageA8_gate.json`，全部通过方可启动主跑）

- **G1（`ldop` 精确复现）**：4 个来自 `stageA2` 的键上，`stageA6.one_arm_nu(..., truth['k_real'], g_order=None)` 与归档 `stageA2` `ldop` 逐位一致（4/4）。
- **G2（`stageA7` 逐位一致性复现）**：4 个来自 `out/stageA7/results.json` 的键上，`stageA8.eval_key` 输出的 `sbg_metric`、`sbg_max_err` 与 `stageA7` 存档绝对差 `< 1e-12`，且 `SBGdop` 的 `syndrome`、`f0_errors`、`errors` 完全相等（4/4）。
- **G3（隔离帧 `41400–41403` 分层成本外推 $\times 1.3 \le 8.20$ 核时）**：在隔离帧 `41400–41403` 上对 4 个 SNR `(300, 400, 450, 500)` 各测 4 键（覆盖 `U/G` × `rho 100/150`，共 16 键），按实测各 SNR 单键总 CPU 均值外推全网耗时 $\times 1.3 + 0.15\text{ h} \le 8.20\text{ 核时}$，选定 SNR 网格。

---

## 5. 冻结判读规则（跑后永不改标）

- **交叉点与自助法**：完全复用 `stageA6`（`stageA2.crossing` 1% info-FER，U/G 等权平均，截尾保守上下界，`400` 物理帧联合配对自助法 `2,000` 次重采样，`seed = 20261125`）。
- **主估计量**：
  $$D = \min_{\rho \in \{100,150,200,250\}} C_{\mathrm{CD2}}(\rho) \;-\; \min_{\rho \in \{100,150\}} C_{\mathrm{SBGdop}}(\rho)$$
- **唯一互斥判定表（任务书第 2 条硬门槛）**：
  - **`GO`（值得继续）**：95% 配对自助下界 $\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$；
  - **`STOP`（不值得继续）**：$\mathrm{LB}_{95}(D) < 0.50\text{ dB}$（同时在读出中标明是否满足 $\mathrm{UB}_{95}(D) < 0.30\text{ dB}$ 以与 Stage A6 对照）。
- **描述性次要读数**：
  1. `SBGdop` 各 $\rho$ 的分场景 `U/G` 与均值 1% FER 交叉点；
  2. 带 95% 配对 CI 的次要对比：`SBdop − SBGdop`（纯全局搜索相对 A6 局部搜索增益）、`SBGdop − ldop`、`SBGdop − s050`、`SBGdop − s100`、`PWdop − SBGdop`；
  3. 全网格逐 $(\rho, \text{SNR})$ 单元的多普勒截顶 MAE、离群率（$>0.25$ bin）、F0 FER、终态 FER，以及相对归档 `SBdop` 的**逐键配对救回计数（`SBdop 败 -> SBGdop 成`）与误伤计数（`SBdop 成 -> SBGdop 败`）**；
  4. 单键 `SBG` CPU 耗时均值/中位/p95。

---

## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **agy（Gemini 4 Neon，基于 `4.0 dB` 开发集与 Stage A7 确认集，未接触全帧 `SBGdop` 结果）**：
  - `A8-G1`（主判定 `GO`，即 $\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$）：`.78`
  - `A8-G2`（`SBGdop` 最优 1% FER 交叉点 $\le 3.75\text{ dB}$）：`.75`
  - `A8-G3`（直接搜索增益 `min SBdop − min SBGdop` 的 95% 配对下界 $\ge 0.50\text{ dB}$）：`.75`

---

## 7. deinlab 执行规范

- `conda activate AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），6 个线程环境变量全为 `1`，`CUDA_VISIBLE_DEVICES=""`，`TMPDIR=/data/guoyikun/tmp`，`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`，严禁写 `/tmp`、`/dev/shm`、`/home/guoyikun`；`tmux` 会话名 `g_a7_fix`；工作进程 `32`。
- 原始逐键分片留存远端 `out/stageA8/raw/rows_shard*.jsonl.gz` 并写入 `out/stageA8/REMOTE_ROWS_MD5.txt`；回传 `out/stageA8_gate.json` 与 `out/stageA8/{results.json,RESULTS.md,REMOTE_ROWS_MD5.txt,STATUS,run.log,run_cpu.txt}`。
