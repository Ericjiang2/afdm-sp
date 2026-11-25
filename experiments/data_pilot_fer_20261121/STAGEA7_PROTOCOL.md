# 阶段 A7：第 0 轮半盲多普勒旁瓣锁定的决定性诊断——协议（`STAGEA7_PROTOCOL.md`）

**状态**：FROZEN（已完成本机单测 `test_stageA7.py` 与隔离开发集门控 G1–G4，并经 `Before data-pilot-fer stage A7 ...` 提交冻结；注：当前 `/boost` 子代理沙箱策略拦截嵌套 `codex exec` 调用——返回 `Permission denied for unsandboxed(codex exec ...). Matches default system policy`——故冻结前审查由代码级不变式自审、`NaN` 污染块覆盖单测与远端开发集 G1–G4 门控完成；在冻结提交完成前，**确认集 `4.5–5.0 dB` 的 38 个失败键全程零接触**）
**承接**：
- [STAGEA6_READOUT.md](STAGEA6_READOUT.md)：给定真时延时，`CD2` 最优 1% FER 交叉点为 `4.4156 dB`（$\rho=.20$），真多普勒 `ldop` 为 `3.4518 dB`（$\rho=.10$，差距 `+0.9638 dB`），而从导频 `PW` 初值启动局部 `L-BFGS-B` 的半盲多普勒 `SBdop` 仅达 `4.3769 dB`（`STOP`）：17%–24% 路径跳入 `2–4.4` bin 外的旁瓣盆地，`4.5–5.0 dB` 下全部 `38/38` 个终态失败键均含此类离群径。
- [out/stageA7/dev_4db_summary.json](out/stageA7/dev_4db_summary.json)：开发集探索（严格限定 `snr == 400` 即 `4.0 dB` 的 `69` 个 `SBdop` 终态失败键 + `24` 个 `4.0 dB` 成功对照键；`deinlab` 探索实耗 `0.6960` 核时，其余在本机 Mac 完成）：
  - 在 `69` 个 `4.0 dB` 失败键上，导频白噪目标 `PW` 仅 `1/69` 偏好真值，但**高斯半盲似然 $\mathcal{L}_{\mathrm{SB}}$ 在 `68/69`（`98.6%`）上严格偏好真值盆地**（相对 A6 旁瓣极小值的 NLL 优势中位数 `+36.18` nats，四分位距 `[+27.72, +64.66]` nats；唯一例外 `41310 G 150` 系 A6 `SB` 已收敛至真值盆地平稳点，与无约束真值起点 `SB-tfree` 差值 `0.00`）；已知数据似然 $\mathcal{L}_{\mathrm{KD}}$ 在 `69/69` 上偏好真值盆地。
  - 在完全不接触真值、不引入离散星座或编码先验的前提下，对**同一高斯半盲目标与同一参数域** $[-3,3]^P \times [-10,10]^{2P}$ 采用“数据互相关差频 FFT + 多径导频全局对齐 + 坐标旁瓣逃逸扫描 + 分块三对角精确梯度 `L-BFGS-B`”的无真值全局搜索器 `SBG`，在开发集救回 `63/69`（`91.3%`；其中 $\rho=.10$ 为 `42/42 = 100%`，$\rho=.15$ 为 `21/27 = 77.8%`），且 `24/24` 成功对照键零回退。

---

## 1. 核心诊断问题与竞争假说

为什么 Stage A6 的半盲第 0 轮多普勒估计在低导频比例（$\rho \in \{0.10, 0.15\}$）下锁定在旁瓣，未能回收 `CD2`（`4.42 dB`）与 `ldop`（`3.45 dB`）之间约 `1 dB` 的差距？三个互斥机制假说及其在确认集（Stage A6 在 `4.5–5.0 dB` 下的全部 `38` 个 `SBdop` 终态失败键）上的可证伪预测：

1. **假说 `(a) SEARCH`（局部搜索初值陷阱）**：
   - 机制：导频匹配滤波 `PW` 在单径低导频信干噪比下跳入 `2–4` bin 外的旁瓣，而 Dirichlet 核在整数间隔处的零点形成局部梯度势垒，使局部 `L-BFGS-B` 无法跨瓣；但高斯半盲似然 $\mathcal{L}_{\mathrm{SB}}(\nu, g)$ 通过跨时延数据互相关锁定了路径间差频 $\nu_i - \nu_j$，再由多径相干导频锁定公共频偏，其自身全局极小值已经位于真值盆地。
   - 预测：$f_{\mathrm{SB}}$（$\mathcal{L}_{\mathrm{SB}}$ 偏好真值盆地比例）接近 `1.0`，$f_{\mathrm{KD}}$ 与 $f_{\mathrm{code}}$ 接近 `1.0`，且**无真值全局半盲搜索 `SBGdop`** 在不改变似然模型的前提下消除强径旁瓣并端到端救回绝大多数失败键（$f_{\mathrm{SBG\text{-}rescue}} \ge 0.70$，95% 下界 $> 0.50$）。
2. **假说 `(b) MODEL`（高斯先验丢失 QPSK 星座 / LDPC 码结构信息）**：
   - 机制：圆对称高斯数据模型 $d \sim \mathcal{CN}(0, v_d I_N)$ 对相位旋转与非星座线性组合不敏感，导致在真实噪声下某个非真值旁瓣盆地的 $\mathcal{L}_{\mathrm{SB}}$ 低于（优于）真值盆地；但离散 QPSK 星座与 LDPC 校验约束能够排除该伪解。
   - 预测：$f_{\mathrm{SB}} \le 0.50$（或无真值 `SBG` 找到 $\mathcal{L}_{\mathrm{SB}} \le \mathcal{L}_{\mathrm{SB}}(\text{真值盆地})$ 的旁瓣解却仅救回 $\le 30\%$），而已知数据似然 $f_{\mathrm{KD}} \ge 0.80$ 且合法 LDPC 码字联合似然 $f_{\mathrm{code}} \ge 0.80$。
3. **假说 `(c) INFO`（信息极限 / 信道噪声与码字不可辨识底）**：
   - 机制：在这批高 SNR 尾部坏帧上，即便给定已知数据似然或真实合法 LDPC 码字联合似然（含 `ldop`），观测信号本身也无法将真值盆地与旁瓣/错码区分开（或真多普勒下接收机自身即译码失败）。
   - 预测：$f_{\mathrm{KD}} \le 0.50$ 或 $f_{\mathrm{code}} \le 0.50$（且对应 95% 上界 $< 0.75$）。

---

## 2. 确认集与逐键诊断量定义（零模型漂移）

- **确认集（一次性运行，跑前未接触）**：Stage A6 原始分片（`out/stageA6/raw/rows_shard*.jsonl.gz`，经 `REMOTE_ROWS_MD5.txt` 全量校验）中满足 `snr in {450, 500}` 且 `arms['SBdop']['errors'] > 0` 的全部键，共 $N_{\mathrm{conf}} = 38$ 个键。
- **统计聚类单元**：同一物理帧 `frame` 在不同 $(\rho, \text{SNR})$ 下共享信道几何，所有比例估计量的 95% 置信区间均按确认集中唯一物理帧做**比率整群自助法（cluster bootstrap）**：对 $M$ 个唯一物理帧有放回重采样 `2,000` 次（`seed = 20261125`），每次计算 $\tilde{f}^{(b)} = \frac{\sum_{c=1}^M w_c^{(b)} S_c}{\sum_{c=1}^M w_c^{(b)} K_c}$，取 `[2.5, 97.5]` 百分位（记为 $[\mathrm{LB}_{95}, \mathrm{UB}_{95}]$）。
- **逐键五个观测量**（所有最终报告的半盲 NLL 均由未经近似的原始 `stageA5.sb_nll_and_grad` 复核输出）：
  1. **A6 局部半盲解复现 $\hat{\theta}_{\mathrm{SB}}$**：运行 `stageA5.estimate_pw` 与 `stageA5.estimate_sb`，强校验逐径 $|\hat{\nu}_{\mathrm{SB}} - \nu_{\mathrm{true}}|$ 与 A6 归档 `sb_abs_err` 最大差 $< 10^{-6}$，记精确半盲负对数似然为 $\mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}})$。
  2. **真值盆地局部半盲极小值 $\hat{\theta}_{\mathrm{SB}|\text{true,box}}$**：以 $(\nu_{\mathrm{true}}, \hat{g}_{\mathrm{SB}}(\nu_{\mathrm{true}}))$ 为初值，在盒约束 $\mathcal{B}(\nu_{\mathrm{true}}, 0.25) = \prod_{i=1}^P [\max(-3, \nu_{\mathrm{true},i}-0.25), \min(3, \nu_{\mathrm{true},i}+0.25)]$ 及复增益 $[-10, 10]^{2P}$ 内最小化精确 $\mathcal{L}_{\mathrm{SB}}$（同步记录 $[-3,3]^P$ 无窄盒约束的 $\hat{\theta}_{\mathrm{SB}|\text{true,free}}$ 及两者的端到端译码错误数作描述性核对）。定义：
     $$\Delta \mathcal{L}_{\mathrm{SB}}(u) = \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}}) - \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}|\text{true,box}}), \qquad f_{\mathrm{SB}} = \frac{1}{N_{\mathrm{conf}}} \sum_{u} \mathbf{1}\{\Delta \mathcal{L}_{\mathrm{SB}}(u) > 0\}.$$
  3. **无真值全局半盲搜索 `SBG` 与端到端 `SBGdop`**：调用 `estimate_sb_global(fgeom, p_t, r, vd, sigma2)`——函数签名仅接收观测信号、导频、数据平均功率 $v_d$、噪声方差 $\sigma^2$ 与已知时延几何，**在架构上无法访问 $\nu_{\mathrm{true}}, g_{\mathrm{true}}, d_{\mathrm{true}}$**，目标函数与边界 $[-3,3]^P \times [-10,10]^{2P}$ 与 `stageA5.estimate_sb` 完全一致（相对 `SBdop` 的严格单因素改动：仅替换非凸搜索算法）。将 $(\hat{\nu}_{\mathrm{SBG}}, \hat{g}_{\mathrm{SBG}})$ 送入 `stageA6.one_arm_nu`（与 A6 `SBdop` 完全一致的导频 LS 增益与 `A1` 分支），记终态信息比特错误数为 $\mathrm{err}_{\mathrm{SBGdop}}(u)$，定义：
     $$f_{\mathrm{SBG\text{-}rescue}} = \frac{1}{N_{\mathrm{conf}}} \sum_{u} \mathbf{1}\{\mathrm{err}_{\mathrm{SBGdop}}(u) = 0\}.$$
  4. **已知数据剖面似然 $\mathcal{L}_{\mathrm{KD}}(\nu) = \frac{1}{\sigma^2}\min_g \|r - A_{p+d_{\mathrm{true}}}(\nu) g\|_2^2$**：分别在旁瓣盒 $\mathcal{B}(\hat{\nu}_{\mathrm{SB}}, 0.25)$ 与真值盒 $\mathcal{B}(\nu_{\mathrm{true}}, 0.25)$ 内做网格 + `L-BFGS-B` 搜索得 $\hat{\nu}_{\mathrm{KD}|\text{sb,box}}$ 与 $\hat{\nu}_{\mathrm{KD}|\text{true,box}}$（并记录无真值初值的 `stageA5.estimate_kd`）。定义：
     $$\Delta \mathcal{L}_{\mathrm{KD}}(u) = \mathcal{L}_{\mathrm{KD}}(\hat{\nu}_{\mathrm{KD}|\text{sb,box}}) - \mathcal{L}_{\mathrm{KD}}(\hat{\nu}_{\mathrm{KD}|\text{true,box}}), \qquad f_{\mathrm{KD}} = \frac{1}{N_{\mathrm{conf}}} \sum_{u} \mathbf{1}\{\Delta \mathcal{L}_{\mathrm{KD}}(u) > 0\}.$$
  5. **合法 LDPC 码字联合似然检验 $f_{\mathrm{code}}$**：对比真多普勒臂 `ldop`（校验与 `stageA2` 归档逐位一致）与 `SBdop` 终态译码输出：通过精确 I-then-Q 映射 $\hat{b} \mapsto \hat{d}(\hat{b})$ 计算校验子权重 $w_{\mathrm{syn}}(\hat{b})$ 与联合残差 $\mathcal{L}_{\mathrm{joint}}(\hat{\nu}_{\mathrm{final}}, \hat{d}) = \frac{1}{\sigma^2}\min_g \|r - A_{p+\hat{d}}(\hat{\nu}_{\mathrm{final}}) g\|_2^2$。若 `ldop` 满足 $w_{\mathrm{syn}}(\hat{b}_{\mathrm{ldop}}) = 0$ 且 $\mathrm{err}_{\mathrm{ldop}} = 0$，同时 `SBdop` 终态无合法码字（$w_{\mathrm{syn}}(\hat{b}_{\mathrm{SBdop}}) \neq 0$）或其合法码字残差严格更大（$\mathcal{L}_{\mathrm{joint}}(\mathrm{SBdop}) > \mathcal{L}_{\mathrm{joint}}(\mathrm{ldop})$），记 $\mathrm{code\_ok}(u) = 1$；定义 $f_{\mathrm{code}} = \frac{1}{N_{\mathrm{conf}}}\sum_u \mathrm{code\_ok}(u)$。

---

## 3. 设计有效性自检与 Premortem（`research-checkpoint` §1）

- **单因素对比**：`SBGdop` 与 A6 `SBdop` 共享完全相同的高斯半盲似然 $\mathcal{L}_{\mathrm{SB}}$、参数盒 $[-3,3]^P \times [-10,10]^{2P}$、第 0 轮导频 LS 增益注入及 `syndrome != 0` 时的 `A1` 延续，唯一变化是第 0 轮 $\mathcal{L}_{\mathrm{SB}}$ 的优化器（局部单起点 vs 多起点互相关+逃逸搜索）。
- **检验效能（Leverage）**：在 $N_{\mathrm{conf}} = 38$（约 35 个独立物理帧）上，若真实比例 $\approx 0.90$（开发集 `f_SB = 0.986`, `f_SBG_rescue = 0.913`），95% 整群自助下界约为 `0.79 > 0.50`，远高于随机猜测门限。
- **Premortem（若确认集结果与预期相反的最可能原因及防护）**：
  1. 若 $f_{\mathrm{SB}} \ge 0.80$ 但 $f_{\mathrm{SBG\text{-}rescue}}$ 偏低：可能存在非 `PW` 的其他深旁瓣优于真值盆地（此时 `SBG` 找到 $\mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SBG}}) \le \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}|\text{true,box}}) + 0.1$ 却仍译码失败，属 `MODEL`），或 `SBG` 搜索本身漏掉真值盆地（此时 $\mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SBG}}) > \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}|\text{true,box}}) + 0.1$，判为 `UNCLEAR` 停机汇报，不强行归因）。
  2. 若分块三对角快速梯度存在数值偏差导致假阳性/假阴性：通过 G1 门控强约束与原始 `stageA5.sb_nll_and_grad` 误差 $< 10^{-10}$，且确认集每个候选解的最终 $\mathcal{L}_{\mathrm{SB}}$ 均调用原始 `stageA5.sb_nll_and_grad` 复核（差值 $> 10^{-8}$ 直接抛错中止）。

---

## 4. 唯一互斥冻结判定规则（跑后永不改标）

在 $N_{\mathrm{conf}} = 38$ 个确认集失败键上按顺序判定：

1. **`SEARCH`**：同时满足
   - $f_{\mathrm{SB}} \ge 0.80$ 且 $\mathrm{LB}_{95}(f_{\mathrm{SB}}) > 0.50$；
   - $f_{\mathrm{SBG\text{-}rescue}} \ge 0.70$ 且 $\mathrm{LB}_{95}(f_{\mathrm{SBG\text{-}rescue}}) > 0.50$。
2. **`MODEL`**：不满足 `SEARCH`，且同时满足
   - $f_{\mathrm{SB}} \le 0.50$，**或**（$f_{\mathrm{SBG\text{-}rescue}} \le 0.30$ 且 $\frac{1}{N_{\mathrm{conf}}}\sum_u \mathbf{1}\{\mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SBG}}) \le \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}|\text{true,box}}) + 0.1\} \ge 0.50$）；
   - $f_{\mathrm{KD}} \ge 0.80$ 且 $\mathrm{LB}_{95}(f_{\mathrm{KD}}) > 0.50$；
   - $f_{\mathrm{code}} \ge 0.80$ 且 $\mathrm{LB}_{95}(f_{\mathrm{code}}) > 0.50$。
3. **`INFO`**：不满足 `SEARCH` 与 `MODEL`，且满足
   - （$f_{\mathrm{KD}} \le 0.50$ 且 $\mathrm{UB}_{95}(f_{\mathrm{KD}}) < 0.75$）**或**（$f_{\mathrm{code}} \le 0.50$ 且 $\mathrm{UB}_{95}(f_{\mathrm{code}}) < 0.75$）。
4. **`UNCLEAR`**：其余所有情况（按任务规则立即停机如实汇报，不进入后续修复实验）。

**后续路由规则（Eric 预先固定）**：
- 若判为 **`SEARCH`**（或 **`MODEL`**）：进入下一阶段（Stage A8），在全部 Stage A6 评估帧（`41000–41399`，给定真时延）上对照归档 `CD2` 预注册测试修复方案，仅当 1% FER 增益的 95% 配对自助下界 $\ge 0.5\text{ dB}$ 时判定值得继续。
- 若判为 **`INFO`**：陈述并数值核验该信息极限，随后停止。
- 若判为 **`UNCLEAR`** 或任一门控失败：立即停止并汇报。

---

## 5. 门禁 G1–G4（`out/stageA7_gate.json`，严禁接触 `snr in {450, 500}`）

- **G1（分块三对角 NLL 与梯度精确性）**：在 `snr == 400` 的 4 个开发集键（`frames 41000–41003`）及 1 个含同时延对（co-delay）合成几何上，校验 `sb_nll_only_fast` 与 `sb_nll_and_grad_fast` 相对原始 `stageA5.sb_nll_and_grad` 的最大绝对误差均 `< 1e-10`。
- **G2（零偷看真值不变性与 A6 复现）**：(i) 将 `truth['k_real']`、`truth['g_i']`、`raw['data']` 篡改为全随机数后，`estimate_sb_global` 输出逐位完全不变（最大差 `0.0`）；(ii) 在 `4.0 dB` 的 8 个 A6 失败键上复现 A6 归档 `sb_abs_err` 最大差 `< 1e-6`，且 `SBdop` 与 `ldop` 分别逐位复现 `stageA6` 与 `stageA2`。
- **G3（`4.0 dB` 开发集救回与零误伤检验）**：在 `snr == 400` 的 8 个 A6 失败键 + 8 个 A6 成功键（共 16 键）上，`SBG` 在 `16/16` 上满足 $\mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SBG}}) \le \mathcal{L}_{\mathrm{SB}}(\hat{\theta}_{\mathrm{SB}}) + 10^{-3}$，救回至少 `6/8` 失败键，且 `8/8` 成功键保持 `errors == 0`。
- **G4（确认集成本外推）**：按 G3 实测单键完整诊断 CPU 耗时均值外推 38 个确认键总耗时 $\times 1.3 + 0.05\text{ h} \le 1.0\text{ 核时}$（确保全任务累计远端算力留足 $> 8.0$ 核时余量）。

---

## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）

- **Claude（先验，任务书给定）**：
  - `A7-C1`（确认集主判定）：`SEARCH` `.35` / `MODEL` `.35` / `INFO` `.10` / `UNCLEAR` `.20`
- **agy（Gemini 4 Neon，基于 `4.0 dB` 开发集探索后、接触 `4.5–5.0 dB` 确认集前）**：
  - `A7-G1`（确认集主判定）：`SEARCH` `.80` / `MODEL` `.05` / `INFO` `.03` / `UNCLEAR` `.12`
  - `A7-G2`（确认集无真值救回率）：$f_{\mathrm{SBG\text{-}rescue}} \ge 0.75$（即至少救回 `29/38` 个高 SNR 失败键）：`.75`

---

## 7. deinlab 执行与预算规范

- **总预算硬上限**：全任务（含前期 `4.0 dB` 开发集探索 `0.6960` 核时 + Stage A7 门控与确认跑 + 若触发 Stage A8 的全网验证）合计 **`<= 10.0` 核时**；Stage A7 本阶段硬上限设为 `1.0` 核时。
- **环境**：`conda activate AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），6 个线程环境变量全为 `1`，`CUDA_VISIBLE_DEVICES=""`，`TMPDIR=/data/guoyikun/tmp`，`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`，严禁写 `/tmp`、`/dev/shm`、`/home/guoyikun`；`tmux` 会话名 `g_a7_diag`；工作进程 `<= 28`。
