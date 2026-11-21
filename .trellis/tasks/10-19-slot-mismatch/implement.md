# implement.md — 槽位失配确认实验（三阶段、两道门）

> 写于 2026-11-18（Claude，按 Eric 当日批准的分工）。需求与约束以 `prd.md` 为准；本文件只写执行顺序、门控与停止点。
> 执行方 Sol = Codex `gpt-6.2-sol`；每次 `codex exec` / `codex exec resume` 显式写 `-m gpt-6.2-sol`，每轮结束核对日志 `model:` 行。
> Claude Code 不执行本文件中的任何实验、门控或运行。

## 角色

| 角色 | 做什么 | 不做什么 |
|---|---|---|
| Sol（`gpt-6.2-sol`） | 第 1–3 阶段全部执行：协议修订、代码、门控、冒烟、主跑、汇总、草稿卡 | 不冻结协议、不选范围、不改骨架、不验收卡 |
| Astra（`gpt-6.2-astra`） | Gate 1 前：从 11-11 推导链给 Q2 先验定量预测；可选：审计判定规则 | 不提方向、不改问题、不评叙事 |
| Claude | Gate 1：方向层设计评审 + 分歧表 | 不执行实验 / CSV 行 |
| Eric | Gate 1 冻结并选范围与预算；Gate 2 验收 | — |

## Phase 1（Sol）：协议修订、门控、冒烟与成本 → 提交并停止

简报：`research/codex-sol-phase1-brief.md`。

1. **协议修订**（改 `experiments/slot_mismatch_20261019/PROTOCOL.md`，保持 DRAFT；旧版由 git 历史保留）
   - 帧改为 10000–10999；在协议中写明核实方法与结果（检索全部已有实验驱动/输出的帧范围，含 deinlab 输出目录），未核实不得写"未用"。
   - Q2 改为同批单元配对：主估计量定义在 s=8 与 s=12 均触发的同一单元上（frame 聚类 bootstrap）；总体 D_s 作次要。
     协议须讨论该条件化带来的选择偏差，以及"F0_s 本身随 s 变化"如何进入解释。
   - 主线臂为 `CODELAY`（res-20261118-03 的闭式实现）；`FULL` 作可选对照（只在完整范围或抽样子集上跑）；标量 Γ 臂（A2）保留。
   - σ̂² 未知单格：Sol 提出 σ̂² 估计器（只用接收端可得量），写明它影响的位置（岭 λ、Γ、检测器）与单格的格点和判定规则。
   - 重审格点（SNR 范围、ρ、场景）与 P1 / res-20261118-03 的可比性；判定带宽（Q1 ±.25 dB，Q2 .5/.8）按预期 CI 宽度复核，需要改就改并说明理由。
2. **research-checkpoint 时刻 1（冻结前）条目**，写进协议：
   - 竞争假设与逐臂预测：至少 H-displace（挤占）、H-intrinsic（幻影内在有害 / 排序错误）、以及"预占"类替代解释
     （s=12 的 F0 已保留部分弱真径，使可救回机会减少，差距因此缩小但与挤占无关）。每个假设对 R(CODELAY_s)、R(A2_s)、D_s、
     A2 幻影首编辑占比给方向预测。10-19 试跑（同批 .90、交换 1.00、check 1–3）作为已知先验写明。
   - 设计有效性问题：s=12 实际槽位不足；触发集合随 s 变化；配对条件化偏差；family T 中信道律随 P 改变的混杂；σ̂² 单格的可解释性。
   - Premortem：列出最可能让结果无法回答 Q2 的 3–5 种情况及缓解。
   - 预测台账：在 `research-assets/prediction-ledger.md` 新开一节，给 Q1、Q2、σ̂² 单格的概率（Sol 自己的预测，标明作者与日期）。
3. **门控**（任何主跑帧之前；输出到 `experiments/slot_mismatch_20261019/out/gate_<date>/`）
   - G1：`max_paths=8` 变体与冻结 `native_twofft.receive` 在 ≥32 个 P1 帧上逐位一致（译码比特与全部 r0/r1 数组），与冻结文件的 diff 只有 max_paths 参数。
   - G2：`CODELAY_8` 与 A2_8 在 ≥32 个历史触发键上复现已存决策（`CODELAY` 对 res-20261118-03 存档、A2 对 E-2 R 族 decoded sha）。
   - G3：生成器 P_paths=8 逐位复现 P1 帧（≥16）；P_paths=6/10 时路径数 = P、单帧路径功率归一、时延 ≤102，记录重抽率。
   - G4：记录的槽位数 = min(s, 去重提名时延数)。
   - G5（新）：σ̂² 估计器在 ≥32 帧上的偏差与离散度描述（不调参）。
   - 已有 10-19 变体文件（`native_twofft_variant.py`、`geometry_guard_edits_variant.py`、`sm_driver.py`）可复用，但必须对当前冻结版本重新过门。
4. **冒烟与成本**：deinlab（先 `nvidia-smi`，CPU 运行，单线程 BLAS，tmux `g_` 前缀，写 `/data/guoyikun/...`），每个 family ≥12 键计时；
   给出**最小范围**（建议：Q2 主比较 s∈{8,12} + Q1 s∈{6,8,10,12} 的少数关键格 + σ̂² 单格）与**完整范围**（协议全格）的核心时与墙钟估计，各附成本上限建议。
5. **提交并停止**：按项目 commit checklist 提交（只提交本阶段改动的文件，带 `_argv`/`_config` 的汇总 JSON），在 `implement.md` 末尾"执行记录"追加一段：
   做了什么、门控结果、成本表、未决问题。**不启动主跑。**

## Gate 1：冻结与范围决定

1. Astra：按 `research/astra-q2-prediction-brief.md` 给出 Q2 先验定量预测（可选：判定规则审计）→ `research/astra-q2-prediction.md`。
   必须在 Eric 冻结之前、且在 Astra 看到任何新帧数据之前完成。
2. Claude：方向层设计评审 → `research/claude-design-review.md`，内容：这是否是论文 Sec. V-D/E 需要的问题；Q2 每种判定
   （DISPLACE / MIXED / INTRINSIC / NO-BASELINE）对骨架 v1.1 第 2、4 点因果句的改写选项；最小与完整范围各自能支撑的论文句子。
3. 分歧表：Sol 协议预测 / Astra 推导预测 / Claude 预测（台账已有 10-19 版本）三方逐项并列，标出分歧 → `research/gate1-divergence.md`。
4. Eric：冻结协议（协议头改 FROZEN + 冻结 commit）、选范围（最小/完整）与成本上限。冻结后判定规则永不重标。

## Phase 2（Sol）：主跑（冻结后）

- 先提交 `before slot-mismatch main run`。
- 一条无人值守链：分片启动 → 每片完成写回执 → 汇总；累计核心时超过冻结的成本上限即停止。
- 链末尾在 `out/main_<date>/` 写一行终态：`DONE <shards> <core-hours>` 或 `STOPPED <reason> <core-hours>`。不轮询、不中途改参数。
- 原始行留 deinlab（gzip + md5 清单）；小文件回传本地 `out/`。完成后提交 `after slot-mismatch main run`。

## Phase 3（Sol）：报告与草稿卡

- `out/RESULTS.md` 三层：观察 / 冻结判定（逐条对照协议）/ 未检验解释（H/M/L）。
- 预测台账打分（Sol、Astra、Claude 三方的条目都打）。
- 草稿结果卡 `research-assets/res-YYYYMMDD-NN.md`（status draft），含远程大文件路径 + md5。
- STATE.md 只加一行入口（研究第 2 项），不改骨架、不改已接受卡。提交。

## Gate 2：Eric 验收

- Eric 验收或退回草稿卡；若 Q2 结果要求改写骨架因果句，由 Eric 决定改法（显式 supersession，不静默改写）。
- 验收后 Sol 或后续会话关闭任务，留一句"留下的东西在哪里、还有什么未了结"。

## 执行记录

（Sol 每阶段结束在此追加。）

### 2026-11-18 · Phase 1 · Sol

[协议草案](../../../experiments/slot_mismatch_20261019/PROTOCOL.md)已改为 10000–10999、共同触发配对和 CODELAY 主线，并加入单格未知噪声、三项竞争假设、判定带、事前验尸和预测概率。deinlab 与本地分别检查 11,968 和 1,078 个已有输出文件，无帧冲突。[预测台账](../../../research-assets/prediction-ledger.md)和[门控回执](../../../experiments/slot_mismatch_20261019/out/gate_20261118/gate_summary.json)均已落盘。

G1 40/40 译码比特和每键 28 个 r0/r1 数组逐位一致。G2 CODELAY 与 A2 各复现 32/32。G3 的 P=8 复现 16/16，P=6/10 各 16 帧均满足路径数、功率和时延上限。G3 首次比较误纳入墙钟字段，保留失败回执后仅剔除该字段重验。G4 槽位计数 640/640。G5 在 32 帧 × 8 点上估计/真值均值为 1.004–1.009，标准差为 .137–.266，无截断。冒烟共 208 键，全部使用历史帧和单线程 CPU。

| 候选范围 | 键数 | 核时（原估 / 加 30%） | 24 核预计墙钟（加 30%） | 建议成本上限 |
| --- | ---: | ---: | ---: | ---: |
| 最小 | 30,000 | 9.90 / 12.88 | 32 分钟 | 15 核时 |
| 完整 | 104,000 | 26.23 / 34.09 | 85 分钟 | 40 核时 |

Gate 1 待审查共同触发与 F0 预占如何约束论文因果表述、确定是否需要完整的双向失配格点，以及未知噪声估计的单帧波动是否适合该单格检验。范围与预算待定。主实验帧未运行，协议仍为 DRAFT，模型日志为 `gpt-6.2-sol`。

### 2026-11-18 · Gate 1 freeze · Sol

按 Eric 的 [Accept 1–5](research/gate1-divergence.md#4-eric-的决定2026-11-18) 冻结完整范围和 40 核时上限。协议逐字纳入获批条款，台账补入 Astra、Claude 的预测和 Q2 打分规则。任务在 Phase 1 已标为 `in_progress`。

按门控原始回执恢复 `qualify_archives_v2.py`（MD5 `ea10cd894984090e1fa61e8223d80798`），把续跑代码归回 `qualify_resume_v2.py`（MD5 `202d3065481e99593797c14d24890dd4`）。两份代码的 SHA-256 均与各自回执一致。已删除 deinlab `/data/guoyikun/tmp/slot-gates-6441bba6/`，包含门控脚本、E-2 清单副本、回执副本、日志和 tmux 运行目录。

### 2026-11-18 · Phase 2 launch · Sol

冻结提交 `9b633ce9df020158d51621600d7b6eab3b65395d`，跑前提交 `f71c05a1`。[帧复核](../../../experiments/slot_mismatch_20261019/out/qualification_20261118/pre_main_freshness.json)确认本地 1,082 个与 deinlab 11,971 个输出文件均无冲突。deinlab 以 `tmux` 会话 `g_slotmm` 启动冻结版，24 个单线程 CPU worker、完整 104,000 键、40 核时上限。首分片 `000` 于 2026-11-18T10:07:26+00:00 启动（PID `1182352`，已确认 `FIRST_SHARD`）。确认启动后停止观察。

终态路径 `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019/out/main_20261118/STATUS`。

### 2026-11-18 · Phase 3 readout

- `DONE 200 30.723700`. All 200 archived gzip MD5s and all 104,000 keys verified. Returned configuration, completion and shard receipts, and the raw MD5 list. The three readout scripts analyzed the archive on one CPU thread through `deinlab-vpn`, with no new receiver evaluations. The results JSON pins the readout scripts and manifest.
- Frozen Q2 is MIXED (`D12/D8 = 0.763 [0.716, 0.811]`). M cap 10 and 12 are ROBUST and cap 6 is DEGRADED in all four cells. T6 has two ROBUST and two INCONCLUSIVE cells. T10 is DEGRADED in all four. N is DEGRADED at both caps. Independent checks reproduced the 39 point crossings, 22 contrasts and Q2 joint counts, and confirmed the source pins and frozen classifications.
- Report at `experiments/slot_mismatch_20261019/out/RESULTS.md`. Nine ledger rows scored. Draft `res-20261118-04` awaits Gate 2 and Eric's decision on the proposed skeleton wording.
