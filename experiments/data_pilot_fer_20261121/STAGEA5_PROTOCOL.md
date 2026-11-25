# 阶段 A5：半盲第 0 轮多普勒估计器代理检验——协议（`STAGEA5_PROTOCOL.md`）

**状态**：FROZEN（已按 Sol 静态审查 `out/stageA5_sol_review.md` 修复全部 4 项，待运行 G1–G4 并提交 `Before data-pilot-fer stage A5 ...`）
**承接**：[STAGEA4_READOUT.md](STAGEA4_READOUT.md)（`SB-REACHABLE`：4 dB 下半盲高斯 CRB 为 `.040/.037` bin）与 [sameframe_cd2_20261125/READOUT.md](../sameframe_cd2_20261125/READOUT.md)（以 `CD2` 为基线后 `P1'` 为 `INCONCLUSIVE`，对 `s100` 余量 `+0.58 [+0.32, +0.84] dB`）。

### 冻结前修订（响应 Sol 静态审查 `out/stageA5_sol_review.md`）
1. **统计单元改为 100 个物理帧聚类自助法**：因同帧 `U/G` 共用底层随机种子（`p1_driver.py:43`），`analyze_stageA5` 与 §4 统一按 **100 个物理帧（`41000–41099`）**联合重采样，每帧绑定 `U/G` 及全部 $\rho$。
2. **明确 `PW`/`KD` 的变量投影（variable projection）目标**：明确每次评估候选 $\nu_p$ 均重新拟合最小二乘增益 $g_{\mathrm{LS}}(\nu)$ 以最小化 $\min_g \|r - A(\nu) g\|^2$（与代码及任务要求完全一致）。
3. **对齐 G2 帧号与 CPU 限额检查余量**：G2 统一使用隔离帧 `41200`（不触碰评估帧 `41000–41099`）；主跑 CPU 监控轮询间隔缩短至 `5s`、预留余量扩大至 `360s`（24 进程单次轮询增量上限 120 核秒 < 360 核秒）。
4. **对齐远端分片路径与冻结依赖校验**：§6 明确远端逐键原始行路径为 `out/stageA5/raw/rows_shard*.jsonl.gz`；代码钉死 `stageA.py` / `stageA4.py` MD5 并在 git 环境下校验 `--freeze-commit` 对应 blob 一致。
5. **响应 G3 门控失败的 `SB` 求解器修正（未触碰主评估帧 `41000–41099`）**：原 2 轮固定增益坐标搜索 + 仅导频 GLS 增益更新在首轮 G3 门控（隔离帧 `41200–41209`，$\rho=.30$，12 dB）中失败（`mean_sb = 0.03453`，`SB/SB-CRB = 1.841 > 1.5`，单键 `14.9 s`），而 `G1` 协方差精度为 `1.51e-16`、`G2` 中位方差比为 `0.921`。根因在于固定复增益做单径 $\nu_p$ 一维扫描受限于未中心化时间索引导致的强相位-多普勒耦合（$\rho \approx 0.866$），且仅用均值残差的 GLS 抛弃了协方差项 $\log\det C + e^H C^{-1} e$ 中关于复增益 $g$ 的信息。现保持**完全相同的半盲高斯似然目标函数** $\mathrm{NLL}(\nu, g) = \log\det C + e^H C^{-1} e$ 与**完全相同的 `PW` 初值**，改用解析精确梯度联合 `L-BFGS-B` 同时优化全部 $3P$ 个实参数 $(\nu, \operatorname{Re} g, \operatorname{Im} g)$（`nu ∈ [-3, 3]`，`maxiter=80`，`ftol=1e-10`），与 `stageA4.fims` 的 $3P$ 维半盲 Fisher 矩阵严格同构；隔离 G3 样本实测 `ratio = 1.143 <= 1.5`（接近真值初始化 MLE 的 `1.129`）且单键提速约 2×。

---

## 1. 核心问题

在**已知真时延** $l_i$ 条件下，实际可运行的半盲高斯最大似然第 0 轮多普勒估计器（`SB`），在低导频比例 $\rho \in \{0.10, 0.15\}$、$\text{SNR} = 4\text{ dB}$ 下，其功率加权平均绝对误差能否达到 $\le 0.08\text{ bin}$（Stage A3 中保住约 60% 收益的代理门槛）？

---

## 2. 信号模型与三种估计器（复用 `stageA4.model` 约定，不改冻结文件）

原始单位下（与 `stageA4.model` 一致至 $10^{-15}$）：
$$r = \mathrm{daft}(y, \text{inverse}) = T x_t + w, \qquad x_t = \mathrm{daft}(p + d, \text{inverse}), \qquad T = \sum_{i=1}^{P} g_i\,\mathrm{diag}(c_i(\nu_i))\,P_{l_i}$$
其中 $c_i[k] = \mathrm{cp}_i(k)\exp(j 2\pi k \nu_i / N)$ 与 `stageA4.model` 完全一致，$v_d = \mathrm{mean}(|d|^2) = 1-\rho$，噪声方差 $\sigma^2 = \text{raw['sigma2']}$。三条估计器均已知真时延 $l_i$，复增益 $g_i$ 为干扰参数（不使用真值 $g_i$ 或 $\nu_i$）：

1. **`PW`（纯导频，把数据当白噪声）**：
   - 初始化：逐径在 `[-3, 3]` 上以 `0.05` 步长（121 点）做单径导频匹配滤波最大化 $|a_i(\nu)^H r|^2$，其中列向量 $a_i(\nu)[k] = c_i(\nu)[k]\,p_t[(k-l_i)\bmod N]$。随后用初始 $\nu$ 求多径最小二乘增益 $g_{\mathrm{LS}}$，按 $|g_{\mathrm{LS},i}|$ 从大到小排坐标搜索顺序（绝不偷看真增益）。
   - 坐标搜索：2 轮扫描，每径在当前 $\nu_i$ 的 $\pm 0.5$ 窗内（裁至 `[-3, 3]`）以 `0.05` 步长粗搜，随后在最优格点 $\pm 0.05$ 内有界精搜（`scipy.optimize.minimize_scalar(..., method='bounded', xatol=0.005)`）；**每评估一个候选 $\nu_i$ 均以精确最小二乘变量投影（variable projection）重新消除全部路径复增益 $g_{\mathrm{LS}}(\nu)$**，最小化 $\min_g \|r - A(\nu) g\|^2$。结束时输出 $g_{\mathrm{PW}} = \arg\min_g \|r - A(\nu_{\mathrm{PW}}) g\|^2$。
2. **`SB`（半盲高斯最大似然）**：
   - 初值：直接从 `PW` 的 $(\nu_{\mathrm{PW}}, g_{\mathrm{PW}})$ 出发（绝不偷看真值）。
   - 目标函数：最小化精确高斯负对数似然 $\mathrm{NLL}(\nu, g) = \log\det C + e^H C^{-1} e$，其中 $C = v_d T T^H + \sigma^2 I$（利用 $T$ 每行仅 8 个非零元的精确稀疏对角和构造，经 Cholesky 分解与 `zpotri` 计算精确逆与解析梯度，与稠密公式一致至 $10^{-14}$），$e = r - T p_t$。
   - 求解器：使用解析精确梯度 $\nabla_{(\nu, \operatorname{Re} g, \operatorname{Im} g)} \mathrm{NLL}$ 运行有界拟牛顿法 `scipy.optimize.minimize(..., method='L-BFGS-B', jac=True, options={'maxiter': 80, 'ftol': 1e-10, 'gtol': 1e-6})`，同时联合优化全部 $3P = 24$ 个实参数（$\nu_i \in [-3, 3]$，$\operatorname{Re} g_i, \operatorname{Im} g_i \in [-10, 10]$）。
3. **`KD`（已知数据天花板，健全性对照）**：
   - 同样坐标搜索与变量投影结构（用全信号 $x_t = \mathrm{daft}(p+d, \text{inverse})$ 匹配滤波初始化，按 $|g_{\mathrm{LS},i}|$ 降序 2 轮 $\pm 0.5$ 窗、`0.05` 步长 + 有界精搜 `xatol=1e-4`），每候选点精确最小化 $\min_g \|r - A_{\mathrm{full}}(\nu) g\|^2$。

### 评价指标（与 A3/A4 一致）
$$M(\hat{\nu}, \nu, g) = \frac{\sum_{i=1}^{P} |g_i|^2 \min(|\hat{\nu}_i - \nu_i|,\; 0.375)}{\sum_{i=1}^{P} |g_i|^2}$$
（逐径误差超过 `0.375` bin 截顶；同时单独统计离群路径比例 $|\hat{\nu}_i - \nu_i| > 0.25$ bin。）

---

## 3. 数据网格与门禁（`out/stageA5_gate.json`）

- **数据网格**：帧 `41000–41099` × 场景 `U/G`（共 **200 个信道抽样**，与 Stage A4 相同）；$\rho \in \{100, 150, 200\}$ permille；主判 SNR = `400`（4 dB）；若 G4 外推（×1.3）在 6 核时预算内允许，则同时跑 `300, 400, 500`（3/4/5 dB），否则仅跑 `400`。输入经 `stageA.setup()` 产生：`raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s, rho), rho, snr)`，取 `raw['y'], raw['pilot'], raw['data'], raw['sigma2'], truth['l_i'], truth['k_real'], truth['g_i']`。
- **门禁 G1–G4（全部通过才允许启动主跑）**：
  - **G1（优化器精确性 + `C` 构造一致性）**：4 个无噪声已知数据键上，从 `truth['k_real'] + 0.1` bin 出发，`KD` 恢复真多普勒的最大误差 $< 10^{-3}$ bin；同时验证快速对角 `C` 与 `stageA4.model` 稠密 $v_d T T^H + \sigma^2 I$ 相对误差 $< 10^{-13}$。
  - **G2（`KD` 12 dB 蒙特卡洛 vs `known` CRB）**：隔离单键（`U`, $\rho=.10$, 12 dB, frame `41200`）100 次独立加噪，8 条径的 $\mathrm{Var}(\hat{\nu}_i - \nu_i) / \mathrm{CRB}_{\mathrm{known}, i}$（取自 `stageA4.fims`）中位数须落在 **`[0.7, 1.5]`**。
  - **G3（`SB` 良性工况验证）**：隔离帧 `41200–41209` × `U/G`（20 抽样），$\rho = .30$，12 dB，实测 `SB` 均值指标 $\le 1.5 \times$ 该 20 抽样 `SB-CRB` 对应指标均值（取自 `stageA4.fims` / `stageA4.metric`）。
  - **G4（成本外推 ×1.3，$\le 6.0$ 核时，$\le 32$ 进程）**：在隔离帧测 `PW + SB + KD` 单键 CPU 耗时，优先检查 `SNRS=(300,400,500)` × 1.3 $\le 6.0$ 核时；若超出则降为 `SNRS=(400,)` × 1.3 $\le 6.0$ 核时；若仍超出则停机汇报。

---

## 4. 冻结判读规则（跑后永不改标）

- **主估计量**：$E = \min_{\rho \in \{0.10, 0.15\}} \overline{M}_{\mathrm{SB}}(\rho, 4\text{ dB})$（200 个信道上的均值）。
- **自助法**：因同帧 `U/G` 共用随机种子，按 **100 个物理帧（`41000–41099`）**做 **2,000 次配对聚类自助重采样**（`seed = 20261125`；每帧联合绑定 `U/G` 及全部 $\rho$，覆盖全部 200 个抽样），每次重采样上先算两档 $\rho$ 均值再取 $\min$，取 **95% 百分位区间** `[2.5, 97.5]`。
- **唯一互斥判定表**：
  - **`PASS`**：95% CI 上界 $\le 0.08$ bin（下一步：引入未知时延估计，再进端到端 FER）
  - **`FAIL`**：95% CI 下界 $> 0.08$ bin（终止第 0 轮多普勒线，转写论文）
  - **`BORDERLINE`**：其余情况（CI 横跨 `0.08`，由 Eric 决定）
- **描述性次要读数**：各 $\rho$ 下 `PW` / `SB` / `KD` 均值与中位数；效率比 `SB mean / SB-CRB` 与 `PW mean / pilot_white-CRB`（同 200 抽样取自 `stageA4`）；离群路径占比（$|\hat{\nu}_i - \nu_i| > 0.25$ bin）；`PW` 对比 Stage A 现有导频估计器实际误差（`.157/.108/.082`）。

---

## 5. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **Claude**：
  - `A5-C1`（判定）：`PASS` .30 / `BORDERLINE` .35 / `FAIL` .35
  - `A5-C2`（效率）：4 dB、$\rho=.10$ 下 `SB` 效率（`SB mean / SB-CRB`）落在 `[1.3, 2.5]`：.60
- **agy（Gemini 4 Neon）**：
  - `A5-G1`（判定）：`PASS` .40 / `BORDERLINE` .30 / `FAIL` .30
  - `A5-G2`（效率）：4 dB、$\rho=.10$ 下 `SB` 效率落在 `[1.3, 2.5]`：.55

---

## 6. deinlab 执行规范

- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，日志首行打印 `sys.executable`）。
- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp` 或 `/home/guoyikun`；`tmux` 会话名 `g_a5`；工作进程 `24`（$\le 32$）。
- 原始逐键分片（`out/stageA5/raw/rows_shard*.jsonl.gz`）留远端并记录各分片 MD5 到 `out/stageA5/REMOTE_ROWS_MD5.txt`；本地回传 `stageA5_gate.json`、`out/stageA5/results.json`（含 `_argv`/`_config`）、`RESULTS.md`、`STATUS` 与日志。
