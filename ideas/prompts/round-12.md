# 第 12 轮规则：2.5 小时清场专轮（Eric 2026-11-25 19:38 拍板定稿）

本轮硬时限 **2.5 小时**，定位为**纯清场专轮**：**先把第 11 轮留下的 7 张在途卡（`g01, g02, k02, k03, m04, m03, h02`）彻底清干净，严禁在本轮新开任何子问题、新草稿或新建任何卡片**。清场结束后立即衔接已备好的第 13 轮（8 小时满跑开荒轮，见 [`round-13.md`](round-13.md)，朝跨轮累计 ~10 张 L3 候选推进）。

规则优先级：本文件 > [`round-agy-extra.md`](round-agy-extra.md) > [`../FUNNEL.md`](../FUNNEL.md)。

---

## 一、本轮核心纪律（与第 11 轮相比的变化）

1. **零新题、做完即退（为兄弟会话让核，为第 13 轮留净工作树）**：
   - 每个 runner **只执行第二节分配给自己名下的 1–2 张在途卡收口任务**，不写新的第一性原理拆解文件，不做新子问题缺口测量。
   - 自己的收口任务全部跑完、写回卡面、在 `ideas/runs-$R.md` 末尾新开 `# 第 12 轮（2.5h 清场专轮，2026-11-25）` 段记清结果与 MD5、跑通 `funnel.py board ideas` 并 `git commit -- ideas/` 后，**立即提前结束退出**（不要因为还有剩余时间去开半截新题）。
   - 时间硬护栏：从启动时刻 `T+0:00` 计，**`T+1:50` 为启动 `deinlab` 正式 L2 的最晚截止线**；超时仍未过 `Sol` 阻断门者保持当前层如实落盘停跑，绝不拖过 `T+2:25`。
2. **资源与命名隔离（防撞第 11 轮与后续第 13 轮）**：
   - `deinlab` 单任务并发仍严格 **`≤ 8` 核**（`OMP_NUM_THREADS=1`），环境锁 `/home/guoyikun/.conda/envs/AFDM/bin/python`（日志首行必打印核实 `sys.executable`），跑前查 `uptime` / `nvidia-smi`。
   - tmux 会话名统一 `g_funnel_$R_r12*`，`deinlab` 输出目录 `/data/guoyikun/tmp/funnel_$R_r12/`，本机缓存 `~/.cache/idea-funnel/afdm-20261125-$R-r12/`。
   - 本轮清场每会话 `Sol`（`gpt-6.2-sol` high）调用上限 **`6` 次**（严禁改用 Opus，严禁跳过阻断级 `Sol` 裸跑 L2）。
3. **`Sol` 的 L2 前快检分两级（Eric 11-25 定；第 12 轮与第 13 轮通用）**：
   - 提示词要求 `Sol` 把每条发现显式标为 **阻断级（Blocking）** 或 **非阻断级（Non-blocking）** 并附代码行号/判决路径依据；末尾结论行只能写三者之一：`GO` / `GO_WITH_NONBLOCKING` / `BLOCK_FOR_FIX`。
   - **阻断级**（必须修完、再过一次 `Sol` 获 `GO` 或 `GO_WITH_NONBLOCKING` 才能上 `deinlab`）：
     ① 会改变 `PASS_PRIMARY` 或任何主判据取值的错误；
     ② 真值或侧信息泄漏；
     ③ 对手不公平（轮数、初始化、开销、带宽、门限规则不对等，或对手未过自身无损/收敛健康检查）；
     ④ 预注册判据与脚本实现不一致、种子与开发集/前跑重叠、或统计口径错误（含未满足红线 5 的 95% CI 半宽 `≤ 25%` 门槛距离与置信下限判定）；
     ⑤ **缺同模型、同前端及单一机制配对对照**——本法与对手用了不同的信道模型、前端、后端或迭代预算时，必须另有一组只差待归因因素的配对对照；卡面把收益归因于某个具体机制时，必须有一组只去掉该机制、其余全保留的配对消融。
   - **非阻断级**（runner 当场修掉、在 `runs-$R.md` 和卡面逐条记下改了什么，**直接上 `deinlab` 跑 L2，不再花一次 `Sol`**）：文档与注释笔误、不进主判决的诊断字段或描述性读数、日志格式、命名。拿不准一律按阻断级处理，runner 不得自行把阻断级降级。
4. 其余防伪红线（红线 1 原图无地板点复现、红线 2 零泄漏对称初启、红线 3 统一评分等虚警与双向消融 `< 80%`、红线 4 `PASS_PRIMARY == false` 当场结案、红线 5 预注册估样本量与置信下限判定）全部照旧严格执行。

---

## 二、四个 runner 的清场任务表（严格按序执行，清完即停）

| runner | 组别 | 清场任务（按先后顺序） | 细则与结案标准 |
|---|---|---|---|
| **`g`** | `[放宽TWC]` | **① `g01` 第 8 步断联消融**<br>**② `g02` 正式 L2 收官** | **① [`I-20261125-g01`](../cards/I-20261125-g01.md)**：按 [`g01` 终审](../reviews/r11-astra-g01-killarg-20261125.md) `P_3–P_4`，在独立新种子上跑前冻结 `PREDICTIONS_g_r12_g01_cut.md`（满足红线 5 样本量半宽门），固定波形、观测、脉冲模型、盲估噪声、搜索预算与检测器，**保留右保护窗内部与帧首弱用户导频窗内部全部跨格、跨天线相关，只移除连接这两窗之间的协方差块及其共轭转置**，过 1 次两级 `Sol` 快检后上 `deinlab` 配对报告弱用户 BER 比及 95% CI。下限过门槛则坐实跨窗折返归因；不过则撤回折返归因、保留同脉冲跨格加权收益与原 `PASS_PRIMARY = true` 整机倍率，卡标 `next_cost: cross-model review`。<br>**② [`I-20261125-g02`](../cards/I-20261125-g02.md)**：对已修齐正定早退与缓存对齐的 `g_l2_r11_g02.py` 与 `PREDICTIONS_g_r11_g02.md` 走 1 次两级 `Sol` 快检，获 `GO` / `GO_WITH_NONBLOCKING` 后上 `deinlab`（8 核，约 6 分钟）跑正式 L2；`PASS_PRIMARY === true` 升 `layer: L2, status: active, next_cost: cross-model review`，`false` 按红线 4/5 结案。 |
| **`k`** | `[高要求]` | **① `k02` 第 8 步配对诊断**<br>**② `k03` 正式 L2 收官** | **① [`I-20261125-k02`](../cards/I-20261125-k02.md)**：按 [`k02` 终审](../reviews/r11-astra-k02-killarg-20261125.md) `P_5`，跑前冻结 `PREDICTIONS_k_r12_k02_p5.md`（新鲜 `-11 dB` 配对场景、独立无目标集校准并验证 1% 全图虚警、满足红线 5），**原样复用父卡 `k01` 曲脊特权前端，接入子卡普通块导频 OFDM 的完整后端（含整帧符号更新与第二次投影）**，过 1 次两级 `Sol` 快检后上 `deinlab`，报告反馈前后误符率（核实恢复父卡 `~0.4%` 初始化）及相对 `ridge_afdm_st` 的全图定位率差。单列为机制诊断（保留前两次冻结裁决），按结果更新卡面第 22 行表述并标 `next_cost: cross-model review`。<br>**② [`I-20261125-k03`](../cards/I-20261125-k03.md)**：修清 `Sol #11` 剩余 2 项阻断问题（`afdm_tang_cpp` 兼顾单径非零 `STO` 与多径静态 `G0` 无截断定时并入 `G1` + 扩至 `≥ 160–200` 场景独立开发校准集重锁样本量与半宽门），过 1 次两级 `Sol` 快检后上 `deinlab` 跑正式 L2；`PASS_PRIMARY === true` 升 `layer: L2, status: active, next_cost: cross-model review`，`false` 按红线 4/5 结案。 |
| **`m`** | `[放宽TWC]` | **① `m04` 正式 L2 收官**<br>**② `m03` 修改方法后的新种子检验** | **① [`I-20261125-m04`](../cards/I-20261125-m04.md)**：`Sol` 第 16 次复核（`v7`）主门与 19 项虚警全绿，仅余 2 处非阻断项（`PREDICTIONS_m_r11_m04.md` 第 5 行概述补 `max(1,…)`；非门控 `R0` `Pc=0/1` 去掉 `R2` 同分布 `pfa_bb_pass` 标签）。核实主判据样本量满足红线 5：若仅修此 2 处非阻断项即可满足，当场修完记入 `runs-m.md` 与卡面后**直接上 `deinlab` 8 核跑正式 L2（免重调 `Sol`）**；若为满足红线 5 改动了样本量或判决逻辑，须过 1 次两级 `Sol` 快检再上机。`PASS_PRIMARY === true` 升 `layer: L2, status: active, next_cost: cross-model review`，`false` 按红线 4/5 结案。<br>**② [`I-20261125-m03`](../cards/I-20261125-m03.md)**（Eric 11-25 明确批准跑；**因新加了 `R4` 共模分离部件，卡面、`runs-m.md` 与预注册文件一律标为「修改方法后的新种子检验」，严禁标为「确证」**）：允许在全部盲臂的 `R4` 零训练帧单帧初始化（`blind_single_frame_init`）中**对称补入与 `R5` 同构的零参数共模线性漂移分离（`nu_raw = nu_cm + nu_rel`）**；跑前在独立开发集按红线 5 估离散度并扩样使各主判据 95% CI 半宽 `≤ 25%` 门槛距离，冻结新预注册 `PREDICTIONS_m_r12_m03_modtest.md`（原门槛数值一字不降，统一按配对 95% CI 下限判定），切换与 `m02/m03` 零重叠全新种子（`+100000`）；过 1 次两级 `Sol` 快检后上 `deinlab` 跑完。过则置 `status: active, next_cost: cross-model review`（卡面筛选记录写明为「修改方法后的新种子检验通过」）；不过即置 `status: killed` 结案（`m01→m02→m03` 链到此终结）。 |
| **`h`** | `[高要求]` | **① `h02` 最后一次确证** | **① [`I-20261125-h02`](../cards/I-20261125-h02.md)**（Eric 11-25 选 b）：切换全新零重叠种子（`+100000`，即 `300000 / 400000 / 500000` 起），**只把对手 `Liu26_PerBinWMMSE_Aged_AFDM` 的 WMMSE 迭代从 4 轮放开至收敛（20 轮，先在 ≥30 个独立开发集场景确认静态 `< 1%` 收敛）**，其余全部代码、判据、样本量与静态 `< 1%` 卫生门一字不改，冻结新预注册 `PREDICTIONS_h_r12_h02_conf.md`；过 1 次两级 `Sol` 快检后上 `deinlab`（8 核，约 3–5 分钟）跑完。过则置 `status: active, next_cost: cross-model review`；不过即置 `status: killed` 结案。跑完提交后立即退出。 |

---

## 三、四会话一键启动口令（复制到各自 worktree 的 agy 会话直接开跑）

- **runner `g`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner g。完整阅读 ideas/prompts/round-12.md、ideas/reviews/r11-astra-g01-killarg-20261125.md、ideas/cards/I-20261125-g01.md 和 ideas/cards/I-20261125-g02.md，严格按 round-12.md 执行 2.5 小时清场专轮（先完结 g01 两窗断联消融，再完结 g02 正式 L2；严禁开新题，两项做完写 runs-g.md、跑 funnel.py board ideas 提交后立即退出）。`
- **runner `k`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner k。完整阅读 ideas/prompts/round-12.md、ideas/reviews/r11-astra-k02-killarg-20261125.md、ideas/cards/I-20261125-k02.md 和 ideas/cards/I-20261125-k03.md，严格按 round-12.md 执行 2.5 小时清场专轮（先完结 k02 父卡曲脊前端接子卡完整后端全图配对诊断，再修清 k03 剩余 2 项跑正式 L2；严禁开新题，做完写 runs-k.md、跑 funnel.py board ideas 提交后立即退出）。`
- **runner `m`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner m。完整阅读 ideas/prompts/round-12.md、ideas/cards/I-20261125-m04.md 和 ideas/cards/I-20261125-m03.md，严格按 round-12.md 执行 2.5 小时清场专轮（先按两级 Sol 规则完结 m04 正式 L2，再按批准的 R4 对称共模分离+红线 5 扩样跑完 m03 的「修改方法后的新种子检验」——因加了新部件，卡面与记录严格标为修改方法后的新种子检验、不称确证；严禁开新题，做完写 runs-m.md、跑 funnel.py board ideas 提交后立即退出）。`
- **runner `h`**（工作目录 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`）：
  `你是 runner h。完整阅读 ideas/prompts/round-12.md 和 ideas/cards/I-20261125-h02.md，严格按 round-12.md 执行 2.5 小时清场专轮（新种子 +100000、仅将对手 Liu26 WMMSE 放开至 20 轮收敛，过两级 Sol 快检后跑完 h02 最后一次确证；严禁开新题，做完写 runs-h.md、跑 funnel.py board ideas 提交后立即退出）。`
