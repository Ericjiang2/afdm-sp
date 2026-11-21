# Genie 支撑审计：B 与约束 MCRB 的差距是否主要来自支撑获取（FROZEN 2026-10-16）

状态：**FROZEN（2026-10-16）**，在加入本行的 commit 中冻结。用户选择："按 r1 冻结"。冻结后改动只能以带编号的修订（A*）或
实现说明（I*）追加，且须在任何正式运行帧之前。
任务：`.trellis/tasks/10-16-tcom-genie-support`（父任务 09-22-tf-production-gap-audit）。
用户决定（2026-10-16）：建本子任务；两个 genie 臂（时延集合 GS-set + 含重数 GS-multi）；NMSE 用帧 0..499，FER 用帧 0..1999。
本协议没有新数学（MCRB 与 NMSE 公式沿用已验收卡 res-20261016-02 的协议 §2），因此不做 Codex 推导审阅；代码只用数值 gate 验证。

## 0. 摘要

- **被检验的事后主张**（res-20261016-02，事后分解，未预注册）：B = F0+CSTATE 最终信道估计高于约束 MCRB 4.9–11.5 dB，
  其中 6.5–8 dB 时 59–86% 的 NMSE 来自漏检的弱路径时延，已找到的时延上只高 1–3 dB；即差距主要在支撑获取，不在 refit。
- **干预**：把真时延告诉接收机，其余照旧——Doppler 与增益由生产 refit 目标函数（`twofft.time_refine` 的同一 VP 目标）重新拟合，
  检测器、LDPC 译码、两轮调度全部不变，再译码。两个臂：
  - **GS-set**：真时延**集合**（每个不同时延一个槽，与生产 refit 的"一时延一槽"结构相同）。直接对应"漏检时延"这一主张。
  - **GS-multi**：真时延**多重集**（P = 8 个槽，同时延多径各占一槽）= headroom ladder 的 A1 臂。与 MCRB 的 genie 模型
    （时延与 P 已知）完全同构。
- **分解**：B → GS-set（时延获取）→ GS-multi（同时延重数）→ MCRB（给定支撑后的 refit/检测残差）。
- **成本**：约 11 core-hours（CPU），上限 16。

## 1. 臂的定义（接收机代码原样导入，只替换 refit 的时延表）

共同部分：`native_twofft.receive(obs, system, code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint')`，
经 `tf_production_gap_audit_20260922/interventions._instrumented` 以 `refine_override` 钩入；`pilot_front` 照常运行。
refit 用 `headroom_ladder_20261008/arms.refine_fixed_delays`（`time_refine` 的逐行副本，唯一改动是时延表由外部给定）：

- 每个槽的 Doppler 初值：同一时延上已获取路径的 Doppler（按 |g| 降序依次分配）；该时延上没有已获取路径的槽，用同一目标函数
  在 [−3, 3]、步长 .25 的网格上顺序粗扫。然后与生产相同的逐坐标有界一维搜索（±.75，xatol .002，maxiter 16，2 轮）。
- 增益：同一 soft ridge 解 (BᴴB + Γ + σ²I)h = Bᴴy；检测器 `scalar_joint` 的 joint 增益（先验 CN(0, I/P)，P = 槽数）。
- 第 1 轮 refit 的输入是第 0 轮输出（时延不变，所有槽都有初值）。
- **GS-set** 时延表：真 l_i 去重，按真每时延能量 Σ_{l_i = d}|g_i|² 降序（模仿生产按获取能量排序；排序只影响坐标下降次序）。
- **GS-multi** 时延表：`arms.make_a1_refine(truth['l_i'])` 原样（生成器顺序，重数保留）。
- **不接 CSTATE 分支**（CSTATE 的作用是修改时延支撑，给定 genie 支撑时不是被检验对象）。GS 臂最终 syndrome ≠ 0 的比例只作描述。
- 不给真 Doppler、真增益、真数据；genie 信息只有时延表（GS-set 还用到每时延能量的排序）。

被比较的已有臂（不重跑，读账本）：B（P1 账本 0..1999 的 FER；CRB 行 0..499 的 `nmse['B-final']`）、A3（P1 账本，真 H，
TF 检测器，增益固定）、MCRB（CRB 行 `bounds['mcrb']['c']`，约束版）。

**估计量**：GS-*-final = 第 1 轮 `r1_delays, r1_dopplers, r1_gains`（检测器最终增益），与 CRB 卡的 F0-final / B-final 同口径；
`r1_ce_gains` 版本只写进 JSON。NMSE 用 `crb.channel_nmse`（CRB 协议 §2.4，精确，gate G1/G2 已验证）。

## 2. 设计

| 因素 | 取值 |
|---|---|
| 帧 | P1 帧（熵 2261fde3…、domain TCRF、gen_fixed 场景开关不变）；FER：0..1999；NMSE 对 MCRB：0..499 |
| 场景 / ρ / SNR | U、G / .3、.5 / 4.5, 5.0, …, 8.0 dB |
| 臂 | GS-set、GS-multi（每个 (场景, ρ, SNR, 帧) 都跑两臂） |
| 配对 | 同一帧的信道/比特/噪声在臂、ρ、SNR 之间共享；B、A3、MCRB 按 (场景, ρ‰, SNR centi-dB, 帧) 键连接 |

## 3. 统计与判定（预注册）

记某 (场景, ρ, SNR) 上全部帧的均值 m_X = mean_f NMSE_X,f，m_M = mean_f b_f（约束 MCRB）。bootstrap 均为帧配对重抽
（同一组重抽帧同时用于所有臂与界），NMSE 2000 次，FER 20000 次，种子固定写入 JSON；95% CI 取 nearest-rank 分位数。
判定区间 = 6.5, 7.0, 7.5, 8.0 dB（事后主张所在的区间）；全部 8 个点都报告。

- **H-S1（主；时延获取占差距多数）**：差距消除比例 f_set = (m_B − m_GSset) / (m_B − m_M)，帧 0..499。
  - 某格 SUPPORTED：判定区间 4 个点的 CI 下限都 ≥ .5；REFUTED：4 个点的 CI 上限都 < .5；否则 INCONCLUSIVE。
  - 总体：4/4 格 SUPPORTED 才写"支撑获取（漏检时延）是 B 到 MCRB 差距的主要部分"；否则逐格报告。
- **H-S2（主；给定完整支撑后 refit 接近 MCRB）**：r_multi = 10 log10(m_GSmulti / m_M)，CI [lo, hi]，沿用 CRB 卡标签：
  BELOW（hi < 0）、EFFICIENT（hi ≤ 1 dB）、NEAR（1 < hi ≤ 3 dB）、GAP（hi > 3 dB）。
  - 某格 SUPPORTED：判定区间 4 个点 hi 都 ≤ 3 dB；REFUTED：4 个点 lo 都 > 3 dB；否则 INCONCLUSIVE。
  - "refit 在 MCRB 3 dB 以内"只在 SUPPORTED 的格、且只对判定区间写；措辞规则同 CRB 协议 §5。
- **H-S3（FER，描述 + 一条异常停止规则）**：帧 0..1999，FER 1e-2 交叉点 x（复用 `p1_agg.crossing` 与 `p2b_agg.crossing_calibration`，
  删失点按 P1 规则标记）。报告 x_B − x_GSset、x_GSset − x_GSmulti、x_GSmulti − x_A3 及配对 CI；B − A3 已知为 .12–.55 dB。
  - **异常停止**：若某格 x_GSmulti − x_B 的 CI 下限 > 0（给真支撑反而比 B 差），先停下报告用户，不写卡。
- **只作描述**：
  - 三段 dB 分解 r_B − r_set、r_set − r_multi、r_multi（及 GS-set 对 MCRB 的标签）；
  - 与事后数字的对照：事后"已找到时延上高 1–3 dB" vs r_set；事后漏检份额 59–86% vs f_set；
  - f_multi = (m_B − m_GSmulti)/(m_B − m_M)；4.5–6.0 dB 的同样统计；
  - 按 B 译码成功/失败分层的 NMSE 比值（条件化，无界保证）；NMSE > −5 dB 的帧比例；GS 臂 syndrome ≠ 0 比例；
  - `r1_ce_gains` 版本、无约束 MCRB 版本。
- 多重比较不校正：每条主判定都是 4 个点的合取，偏保守。

## 4. Gate（任一不过即停，报告用户）

- **S1 refit 副本恒等**：帧 0..19 × 4 格 × {4.5, 8.0} dB，捕获生产 F0 两轮 refit 的实际输入；以生产选出的时延表
  （去重、按获取能量排序、≤ 8）调用 `refine_fixed_delays`，与 `twofft.time_refine` 的输出比较：时延相同，
  max|Δν|、max|Δh|/max|h| ≤ 1e-12，n_missing_slots = 0。
- **S2 A3 复现**：本任务驱动里的 GS 入口函数，注入真 (l, ν, g)、refit 关闭（返回真 Channel）、gain_mode='fixed'，
  在帧 0..19 全部 640 个 (场景, ρ, SNR, 帧) 上 decoded_sha256 与 P1 账本 A3 逐个相等。
- **S3 帧配对**：同一驱动的观测上重跑生产 F0，640 个 cell 的 decoded_sha256 与 P1 账本 F0 相等。
- **S4 genie 注入（每行断言）**：r0、r1 的输出时延表与所给时延表逐元素相等；两轮 refit 都有记录；ν ∈ [−3, 3]，h 有限。
- **S5 连接**：帧 < 500 的每个 GS 行都有对应 CRB 行，σ² 完全相等，‖H‖² 相对差 ≤ 1e-12；GS 臂用真路径时 NMSE ≤ 1e-12。
- **S6 计时**：20 帧冒烟的实测外推 ≤ 16 core-hours，否则停下报告。

## 5. 执行与留痕

1. 用户批准 → 冻结 commit（本文件状态改 FROZEN + 用户原话）。
2. 写驱动 `experiments/tcom_genie_support_20261016/{gs_driver.py, gs_gates.py, gs_agg.py, launch_*.sh}`，复用
   `tcom_channel_crb_20261016/{crb.py, p1ctx.py}`。冻结接收机目录 `sp_afdm_native_joint_reviewed_20260921` 只在 deinlab
   （`twofft.py`、`arms.py`、`interventions.py` 的 md5 与本地副本相同），所以 S1–S6 全在 deinlab 跑（S1–S3 用帧 0..19，S6 为 20 帧冒烟）。
3. Gate 全过 → commit `before genie-support run`。
4. deinlab：CPU 单线程分片（每 job 1 线程，共 ≤ 空闲核 − 16），tmux `g_gs`，只写 `/data/guoyikun/`；运行前 `nproc`/`uptime` 记录负载。
5. 行文件 gzip 留远程，md5 写本地 `out/main/REMOTE_ROWS_MD5.txt`；聚合在远程跑（需要 P1 与 CRB 行），小结果 JSON/MD 回传。
6. commit `after genie-support run`；写 draft 卡 `res-YYYYMMDD-NN`（与 res-20261016-02 互链；若 H-S1/H-S2 结论改变其解释，
   写显式 supersession 建议，由用户决定）；更新 STATE.md 与 research-assets/index.md。

## 6. 局限（预先写明）

- GS-set 仍用真每时延能量排序；排序只改坐标下降次序，不改目标函数。
- GS-multi 的同时延多槽初值来自已获取 Doppler 或粗扫，可能陷入局部极小；这算作 refit 的一部分误差。
- 增益是正则化估计（ridge + 检测器先验 1/P），CRB 只约束局部无偏估计器；"BELOW"按 CRB 协议解释，不另作机理。
- 帧、码、N、调制、σ² 已知、信道律都与 P1 相同；NMSE 只有 500 帧。

## 修订 A1（事后，2026-10-16，用户决定）：GS+CSTATE 臂

**标注：本修订在看到正式运行的 FER 结果之后加入（H-S3 停止规则 4/4 格触发），是事后分析，不是预注册检验。**
用户原话："First add a labelled post hoc amendment: a GS+CSTATE20 arm (branch iff GS syndrome != 0) on frames 0..1999,
so FER compares like with like against B. Then write the card."
§3 的 H-S1、H-S2 判定与 H-S3 停止规则的结果保持不变，按原文报告。

- **臂 GS+C**：重跑 GS-set（与正式运行同一代码），若其最终 syndrome ≠ 0，则从 GS-set 的第 1 轮状态调用与 B 完全相同的
  `run_validation._branch(..., arrays, 'CSTATE20')`（一轮新的编码轮次，几何重开最多改 2 个槽），否则最终结果 = GS-set。
  GS-multi 不重复（全部信道 8 个时延互异，两臂等价）。CSTATE 可以把时延改离真值；最终时延集合是否仍等于真集合只作记录。
- **帧**：0..1999（FER），0..499（NMSE，对 MCRB，与 CRB 行配对）。
- **统计（只作描述，无标签）**：x(B) − x(GS+C)、x(GS+C) − x(A3)、x(GS-set) − x(GS+C) 的 FER 1e-2 交叉点差与配对 bootstrap CI
  （与 §3 H-S3 同法，20000 权重）；GS+C 最终估计（触发时为分支路径 + 检测器增益）对 MCRB 的 r 与 f；触发率；保留真时延集合的比例。
- **Gate**：A1-G1 每行重跑的 GS-set decoded_sha256 与正式运行 GS-set 相等（逐行断言，不等即中止）；
  A1-G2 同一分支辅助函数接在生产 F0 状态上，帧 0..19 的 640 个 cell 复现 P1 账本 B 的 decoded_sha256；
  A1-G3 20 帧冒烟外推 ≤ 10 core-hours。
- 代码：`experiments/tcom_genie_support_20261016/{gs_cstate.py, gs_cstate_agg.py, launch_a1.sh}`（新文件，不改已运行的脚本）。
