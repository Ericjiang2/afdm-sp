# 第 14 轮规则：3 小时清仓收口专轮（Eric 2026-11-26 拍板定稿）

> **状态（11-26 11:51 更新）**：OpenAI Codex 额度已恢复；主会话已完成 `26-h01`、`k01 + k02`、`k03`、`25-m04` 全部 5 张卡的第 8 步 `gpt-6.2-astra` 双拍终审（**`26-h01` 与 `k01+k02` 正式 `PASS` 升入 `L3`**，`k03` 切至 `[放宽TWC]`、`25-m04` 切至纯被动感知后均完成 `Astra` 指定修订，详见 [`r13-candidate-dedup-matrix-20261126.md`](../reviews/r13-candidate-dedup-matrix-20261126.md)）。现在 `g / h / m` 可直接启动！

本轮硬时限 **3 小时**，定位为**纯清仓收口专轮**：全库现有在途与已过关候选去重后已覆盖 **10 篇互不相同的正刊槽位（轨 A 5 : 轨 B 5，见 [`r13-candidate-dedup-matrix-20261126.md`](../reviews/r13-candidate-dedup-matrix-20261126.md)）**，且第 13 轮已实证「理想离散纯通信 `A1+A3`」与「`[高要求] B2+B3`」枯竭。因此本轮 **`g / h / m` 只收口名下指定在途卡，`runner k` 本轮轮空停机，全员严禁新开任何子问题、新探针方向或新建卡片**。

规则栈：本文件 > [`round-12.md`](round-12.md) 第一节第 3 条（`Sol` 两级快检：`GO` / `GO_WITH_NONBLOCKING` / `BLOCK_FOR_FIX`） > [`round-agy-extra.md`](round-agy-extra.md) > [`../FUNNEL.md`](../FUNNEL.md)。

---

## 一、本轮铁律（清完即停，零新题）

1. **严禁开新题、做完即退**：每个会话只按第二节顺序完成名下指定收口项，写回对应卡面与 `ideas/runs-$R.md`（末尾新开 `# 第 14 轮（3h 清仓收口专轮，2026-11-26）`），跑通 `funnel.py board ideas` 并 `git commit -- ideas/` 后**立即退出**。
2. **资源与并发纪律**：`deinlab` 单任务并发严格 **`≤ 8` 核**（`OMP_NUM_THREADS=1`），环境锁 `/home/guoyikun/.conda/envs/AFDM/bin/python`；同一 runner 内多个 L2 任务严格串行；严禁改用 Opus 替代 `Sol`，严禁跳过阻断级 `Sol` 裸跑 L2。
3. **随机信道启动门防误杀规则（自本轮起生效）**：凡在随机瑞利/多径抽样上设置 `< 1% SER` 等基线健康门，样本量不得少于 `≥ 64` 帧（优先 `≥ 128` 帧并先在独立开发集核实均值与重尾标准误），严禁用 `16` 帧重尾均值做一票熔断。
4. **时间硬护栏**：启动起算 `T+2:15` 为新启动 `deinlab` 正式 L2 的最晚截止线；若某卡用完本轮分配的 `Sol` 次数仍为 `BLOCK_FOR_FIX`，不硬拖、不超调，如实标 `status: parked` 写清剩余阻断项提交退出，绝不超过 `T+2:55`。

---

## 二、各 runner 清仓任务明细与 `Sol` 配额

| runner | 本轮状态与总配额 | 按序执行的收口任务与验收标准 |
|---|---|---|
| **`g`** | 运行（约 `1.5h`）<br>**`Sol ≤ 2` 次** | 接续第 12 轮暂停状态（远程 `/data/guoyikun/tmp/funnel_g_r12/`）：<br>**① [`I-20261125-g01`](../cards/I-20261125-g01.md)（`v8b` 第 8 步两窗断联消融，配 `1` 次 `Sol`）**：对已冻结并通过冒烟的 `g_l2_r12_g01_cut.py` 与 `PREDICTIONS_g_r12_g01_cut.md` 调 **1 次**两级 `Sol`（提示词专门要求核对两点：`cut_chordal_prec0` 判决算子只切两窗之间联系且两窗内部协方差逐元 `0.0` 不变；被 `try...except` 隔离的诊断失败显式写入 `diagnostic_failure_summary`）。获 `GO` / `GO_WITH_NONBLOCKING` 即上 `deinlab`（`≤ 8` 核）跑出 `diag_g_r12_g01_cut.json` 并据实更新卡面（不过 `3.0×` 则撤回跨窗折返归因、保留同脉冲窗内跨格全协方差白化收益与第 11 轮 `PASS_PRIMARY = true` 整机倍率，标 `next_cost: cross-model review`）；若仍判 `BLOCK_FOR_FIX`，当场置 `status: parked` 交主会话，不再接着修。<br>**② [`I-20261125-g02`](../cards/I-20261125-g02.md)（`v4b` 正式 L2 收官，配 `1` 次 `Sol`）**：对已冻结并通过冒烟的 `g_l2_r11_g02.py` 与 `PREDICTIONS_g_r11_g02.md` 调 **1 次**两级 `Sol`。获 `GO` / `GO_WITH_NONBLOCKING` 即与 `g01` 串行上 `deinlab`（`≤ 8` 核）跑出 `summary_g_r11_g02.json`（`PASS_PRIMARY === true` 升 `layer: L2, status: active, next_cost: cross-model review`；`false` 按红线 4/5 结案）；若仍判 `BLOCK_FOR_FIX`，当场置 `status: parked` 停手。 |
| **`h`** | 运行（约 `30–45m`）<br>**`Sol ≤ 1` 次** | **唯一任务 [`I-20261125-h02`](../cards/I-20261125-h02.md)（`P_4` 第 8 步决定性检验，配 `1` 次 `Sol`）**：对已冻结并通过远程冒烟的 `h_l2_r12_h02_p4.py` 与 `PREDICTIONS_h_r12_h02_p4.md` 调 **1 次**两级 `Sol`（输出至 `ideas/reviews/r12-sol-prel2-h02-p4-20261126.md`）。获 `GO` / `GO_WITH_NONBLOCKING` 即上 `deinlab`（`≤ 8` 核，约 `10 min`）生成 `ideas/l2/out_h_r12_h02_p4/diag_h_r12_h02_p4.json`，严格按冻结路由更新 `I-20261125-h02.md`（若 `LITERAL_REFUTES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT` 成立，彻底撤回正文各节「通感冲突 / 重测迫使雷达放弃长窗」主张，只保留通信与盲跟踪优势，完整保留第 11/12 轮两次冻结裁决）；若判 `BLOCK_FOR_FIX` 则标 `status: parked` 停手。（注：`I-20261126-h01` 已通过 `Astra` 第 8 步 `PASS` 升入 `L3`，**严禁改动 `26-h01`**。） |
| **`m`** | 运行（约 `2.5h`）<br>**`Sol ≤ 4` 次** | 按下列 1→2→3 顺序串行清完三张在途卡：<br>**① [`I-20261126-m04`](../cards/I-20261126-m04.md)（`v3` 正式 L2 收官，配 `1` 次 `Sol`）**：对已在本地修清 `B1/B7` 的 `l2_m_r13_m04_blind_cov_afdm_isac.py` 与 `PREDICTIONS_m_r13_m04.md` 调 **1 次**两级 `Sol` 差异复核；获 `GO` / `GO_WITH_NONBLOCKING` 即上 `deinlab`（`≤ 8` 核，约 `3–5 min`）跑未触碰正式种子 `2034000000+`，按结果升 `L2 active`（`next_cost: cross-model review`）或结案。<br>**② [`I-20261126-m01`](../cards/I-20261126-m01.md)（Eric 11-26 特批扩宽 `Narasimhan` 辅助启动门样本量重跑未触碰正式种子，配 `1` 次 `Sol`）**：完整保留第 13 轮熔断产物 `out_m_r13_m01/summary_m_r13_m01.json` 不覆盖；新建 `l2_m_r14_m01_wideband_iqi.py`（或输出至 `out_m_r14_m01/summary_m_r14_m01.json`）与 `PREDICTIONS_m_r14_m01.md`——**先在独立开发种子（`850000+`，`≥ 160` 帧）实测 `G_R1_Narasimhan_OFDM` 移动 QPSK `25 dB` 真实均值与标准误**，仅将启动门 `G_R1_Narasimhan_OFDM`（及必要时 `G_ZeroIQI_Health`）的样本量从 `16` 帧扩至 **`≥ 128–160` 帧**、切换全新互斥启动门种子 `2032050000+`（若 160 帧总体均值贴近 `0.85%–1.0%`，用单侧 95% 下界 `< 1.0%` 加点估计 `< 1.25%` 合理防重尾误杀），**本法与对手算法、全部主判据 `P1_Rivals / P2_SingleMech` 门槛及一帧未跑过的 `640` 个正式目标种子 `2032100000..2032600059` 一字不改**！过 **1 次**两级 `Sol` 差异快检后上 `deinlab`（`≤ 8` 核，约 `12 min`）跑完。<br>**③ [`I-20261125-m03`](../cards/I-20261125-m03.md)（三径时延留出范围检验，配 `1–2` 次 `Sol`）**：不改动冻结接收机 `l2_m_r12_m03_modtest.py`（保持 MD5 `7d174070e3b640583e8ec0e03d948cd1`），在 `l2_m_r12_m03_delay_holdout.py` 与 `PREDICTIONS_m_r12_m03_delay_holdout.md` 中修清 [`r12-sol-prel2-m03-holdout-20261126.md`](../reviews/r12-sol-prel2-m03-holdout-20261126.md) 的 2 项阻断与 2 项非阻断：① 改为按固定时延层 `k` 估计配对差方差与倍率协方差并在独立开发集复核红线 5 样本量；② 在留出脚本导入 `m3` 后用仅在捕获 `np.linalg.LinAlgError` 时回退 `scipy.linalg.svd(..., lapack_driver="gesvd")` 并计数的包装器替换 `m3.np.linalg.svd`（确保正常收敛帧含 `k=7` 逐比特差仍为 `0.0`，同时彻底消除种子 `11020055, k=15` 中断并跑通全部 60 帧 `Adj_R4` 开发定样）。过两级 `Sol` 后上 `deinlab` 跑完正式留出检验，按冻结规则更新 `I-20261125-m03.md` 主张范围（保持 `layer: L2`）。 |
| **`k`** | **轮空停机** | 本轮不启动（`k01, k02, k03` 已在主库进入第 8 步终审流，`[高要求] B2+B3` 已于第 13 轮完成转向耗尽结案）。 |

---

## 三、主会话并行收尾项（额度恢复后 5 分钟跑完）

Codex 额度恢复后，主会话直接运行已落盘的 3 条独立第二拍 `gpt-6.2-astra`（`high`）裁决命令，生成：
1. `ideas/reviews/r13-astra-h01-killarg-20261126.md`（对应 [`I-20261126-h01`](../cards/I-20261126-h01.md)）
2. `ideas/reviews/r13-astra-k01k02-regate-killarg-20261126.md`（对应 [`I-20261125-k01`](../cards/I-20261125-k01.md) + [`I-20261125-k02`](../cards/I-20261125-k02.md)）
3. `ideas/reviews/r13-astra-k03m04-killarg-20261126.md`（对应收窄后的 [`I-20261125-k03`](../cards/I-20261125-k03.md) + [`I-20261125-m04`](../cards/I-20261125-m04.md)）

待 `g / h / m` 本轮收口完毕合流后，对新过关的 `25-g02`、`26-m01`、`26-m04`（及完成决定性检验的 `25-g01`、`25-h02`、`25-m03`）做最后一批第 8 步放行，汇总最终 L3 清单交 Eric 选头号题。

---

## 四、三会话一键启动口令（补充/切换 Codex 额度后，复制到对应 worktree 直接开跑；`k` 不开）

- **runner `g`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner g。现在执行第 14 轮（3 小时清仓收口专轮）。完整阅读 ideas/prompts/round-14.md、ideas/prompts/round-12.md（第一节第 3 条两级 Sol 规则）、ideas/cards/I-20261125-g01.md 和 ideas/cards/I-20261125-g02.md。严格按 round-14.md 第二节先过 1 次两级 Sol（专核两窗内部协方差逐元 0.0 不变与隔离诊断异常显式落盘）并上 deinlab 完结 g01 v8b 两窗断联消融，再串行过 1 次两级 Sol 并上 deinlab 完结 g02 v4b 正式 L2（任一卡若再被 Sol 判 BLOCK_FOR_FIX 即标 parked 停手、不再接着修；严禁开新题，做完写 runs-g.md、跑 funnel.py board ideas 提交后立即退出）。`

- **runner `h`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner h。现在执行第 14 轮（3 小时清仓收口专轮）。完整阅读 ideas/prompts/round-14.md、ideas/prompts/round-12.md（第一节第 3 条两级 Sol 规则）、ideas/cards/I-20261125-h02.md 和 ideas/l2/PREDICTIONS_h_r12_h02_p4.md。严格按 round-14.md 第二节对 h02 的 P_4 脚本过 1 次两级 Sol 后上 deinlab 跑完正式 P_4 并按冻结路由更新 h02 卡面（保留前两轮冻结裁决；26-h01 已升入 L3 严禁触碰；严禁开新题，做完写 runs-h.md、跑 funnel.py board ideas 提交后立即退出）。`

- **runner `m`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner m。现在执行第 14 轮（3 小时清仓收口专轮）。完整阅读 ideas/prompts/round-14.md、ideas/prompts/round-12.md（第一节第 3 条两级 Sol 规则）、ideas/cards/I-20261126-m04.md、ideas/cards/I-20261126-m01.md、ideas/cards/I-20261125-m03.md 和 ideas/reviews/r12-sol-prel2-m03-holdout-20261126.md。严格按 round-14.md 第二节串行清完三张卡（Sol 总上限 4 次）：① 26-m04 v3 过 1 次两级 Sol 后上 deinlab 跑正式 L2；② 按特批扩宽 26-m01 的 Narasimhan 辅助启动门至 >=128-160 帧（先在独立开发集核实，保留第 13 轮熔断 JSON 不覆盖，算法、主判据与未触碰的 640 个正式目标种子 2032100000+ 一字不改），过 1 次两级 Sol 后跑完正式 L2；③ 不改冻结接收机 l2_m_r12_m03_modtest.py（保持 MD5 不变），修清 25-m03 三径时延留出脚本的按层方差与 SVD gesvd 异常回退包装器，过两级 Sol 后上 deinlab 跑完留出检验更新主张范围（严禁开新题，做完写 runs-m.md、跑 funnel.py board ideas 提交后立即退出）。`
