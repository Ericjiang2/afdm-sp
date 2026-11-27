# 第 19 轮（方案 1 修订版：2 路分段收口 + 2 路低轨卫星开荒）

> **本轮核心决策（Eric 2026-11-28 拍板方案 1；Claude 同日按第 18 轮证据修订，Gemini 原版见提交 `f725250e5`）**：
> 1. **已结案边界（零回头路）**：
>    - **左半场永久封关**（`P-k-C1` 走廊斜脊帕累托 `KILL`；其"实时预算内唯一可用"的收窄结论已并入 `k01+k02`，见 `cards/I-20261125-k01.md` 末条）。
>    - **单链路基带解调/信道估计神经网络关闭**（第 18 轮：带 Viterbi/Turbo 反馈的传统接收机反超端到端与簇先验网络；白盒等变网络被调对噪声参数的零参数 `EM-SBL` 复现）。
>    - **晴空单径 LOS 馈电的透明弯管返向链路叙事停放**；`r18-h-bentpipe` 整个候选按 `PROBLEMS.md` 第三节已停放，**只有两条复活条件同时满足才可重开**（本轮 `h` 先做这项核对）。
> 2. **待选池（本轮不新增投入，除非下表写明）**：`k01+k02 v2`（收窄版，`P_3` 部分闭合）、`G2B-harq-mimo-ir`（三疑点已清，**跨重传查新按 Eric 11-28 指示暂缓**）、`P-m-15b-02 v2`（只有已知期望信道分支过门；盲分支卡在 Stage-0 捕获）。
> 3. **四路分工（纯时间预算 `4–6` 小时，不设张数指标）**：
>
> | runner | 模型 | 任务 | 关键闸门 |
> |---|---|---|---|
> | `g` | `Neon xhigh` | `K3` **分段收口**：先在开发集上与**调好参的**经典钢人比，过门才锁台和跑封存集 | 闸门 G1 不过 → 写成"基线校准"教训后退出 |
> | `h` | `Neon xhigh` | 先核对 bentpipe 的两条**复活条件**；成立才收口 `dualhop-nc-relay`，不成立就转去修 `m15b02` 盲分支 | 复活条件是硬前提 |
> | `k` | `Carbon high` | 先做 ≤90 分钟 `k01+k02` 的 `P_3` 完整交叉（只归因、不判生死），再开荒 1 个低轨卫星 / NTN 纯传统题 | 线索 A 先复现再立项 |
> | `m` | `Carbon high` | 低轨多波束预编码的等变图网络摊销，45 分钟止损（耗时 + 查新双判据），不过转纯传统卫星题 | 唯一神经位 |
>
> **相对 Gemini 原版的改动**：① 新增全轮硬门 R1–R5（下文 §一.4）；② `g` 由"直接转正 K3"改为分段：K3 比的是 λ 没调好的旧基线，必须先赢调好参的经典钢人；③ `h` 由"直接收口双跳中继"改为先核对复活条件（Eric 11-27 已停放该候选；原版漏写了 IBO 3 dB 时真值两段式反超 V2，也没提 DPD/ACLR），并删去"在开发集上微调重捕门限压尾帧过线"；④ `k` 加 `P_3` 交叉，并注明线索 A 证据弱；⑤ `m` 止损统一为 45 分钟（原 FUNNEL 写 30 分钟），并加查新止损与跨时隙热启动钢人。

规则栈：本文件 > [`../FUNNEL.md`](../FUNNEL.md)（11-28 版） > [`round-18.md`](round-18.md)（共享统计门、预注册锁与 GPU 规范）。

---

## 一、全轮共享铁律

1. **硬件与 `deinlab` 资源红线**：
   - **本机 MacBook Air 严禁运行任何 `> 3` 秒的 Python 计算**；本机极小命令前必设 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`。
   - **纯传统三路（`g, h, k`）**：100% 在 `deinlab` 纯 CPU（`CUDA_VISIBLE_DEVICES=""`，单路 `≤ 10` 核，必设 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`），临时目录 `/data/guoyikun/tmp/funnel_${R}_r19/`，禁写 `/tmp` 与 `/home/guoyikun`，长任务进 `tmux g_funnel_${R}_r19`，跑完清理。需要跨天保留的小文件放 `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/r19_${R}_<slug>/out/`，报告里记远程路径与 MD5。
   - **唯一 GPU 路（`m`，仅当通过 45 分钟止损门）**：起卡前必跑 `nvidia-smi`（已用显存 `> 18 GB` 且利用率 `> 90%` 则避让）；进程入口前 5 行必设 `torch.cuda.set_per_process_memory_fraction(0.25, 0)`；CPU 辅助 `≤ 8` 核单线程 BLAS；训练+评测 GPU 驻留 `≤ 25` 分钟；`tmux g_funnel_m_r19`。
2. **封存集隔离与溯源**：严禁重跑或修改任何历史 `holdout*.json`。产物存 `ideas/r19/`（新评测台存 `ideas/harnesses/H-<id>.py`）。唯一一次 `--mode holdout` 之前，先把冻结评测台、冻结候选与预注册清单（含与一切历史区间互斥的新种子区间）`git commit`（严禁 `--amend`，严禁 `git add .`），holdout 日志首行打印这些文件的实时 `SHA256` 与 UTC 时间。
3. **主账本统计门与 `Sol` 预算**：沿用 `round-18.md` §一.3（性能账 `ΔSNR ≥ +1.50 dB & CI95_lo ≥ +1.00 dB`；破壁账对手 `≥ 10%`、点估 `≥ 5.0×` 且 `CI95_lo(p_rival − 3.5 p_cand) > 0`；传统算力账同精度快 `≥ 5.0×`、`CI95_lo ≥ 4.0×`；神经摊销账 `cpu_1core_ms` 与 `MACs` 均快 `≥ 20.0×`、`CI95_lo ≥ 15.0×`，零重训 OOD 亏损 `≤ 3.0%`/`≤ 0.50 dB` 且保住 `≥ 15.0×`）。每路 `gpt-6.2-sol`（`codex exec --sandbox read-only`）`≤ 5` 次。
4. **第 18 轮教训转成的新硬门 R1–R5（全路必守，写进各自 PRE_REG）**：
   - **R1 基线调参到边界**：锁台前，最强经典钢人的关键超参（噪声/正则 λ、迭代次数、门限、步长）在开发集上扫描；**最优点落在网格边上就继续外扩**，扫描表写进 PRE_REG。（第 18 轮 `g`：λ 写死 `0.25` 造出 17× 的"神经优势"，调到 `2.50`——还是网格边——只剩 `1.3×`。）
   - **R2 物理适用域先行**：每一跳信道、功放工作点（IBO、ACLR/EVM、是否有 DPD）、视距/非视距、预补偿后的残余量，先给出 3GPP 或文献出处再锁台。（第 18 轮 `h`：三次补现实约束，优势逐次收缩。）
   - **R3 对等迭代反馈**：经典钢人与本方案拿到同样轮数的译码/数据辅助反馈（Viterbi、Turbo、软符号重估）。（第 18 轮 `m`：NN-1、NN-2 都在对手装上 Viterbi 反馈后反转。）
   - **R4 归因先于封存集**：主张归功于某个模块（学习模块、新先验、新算子），就先在开发集上做"换成经典对应物"的单因子对照，过了再碰 holdout。（第 18 轮 `g`：holdout96 用掉之后才发现会退化。）
   - **R5 开发集闸门先于锁台**：每条主路线在 PRE_REG 里写一道开发集闸门（用主账本同一门槛）；**闸门不过就不锁台、不跑 holdout**，写报告、提交、退出。

---

## 二、四路一键发车口令（全部新开会话，按标注选模型）

### 1. `runner g` —— 新开会话 · 模型 **`Neon xhigh`**（`K3` 分段收口）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`
```text
你是 runner g。先读本工作树的 ideas/r18/cov0_classical_nn1.md、ideas/r18/steelman_nn1.md、ideas/FUNNEL.md、ideas/prompts/round-19.md（重点 §一.4 的 R1–R5）与 CLAUDE.md。R18c 结论：arm3 的增益可被零参数经典流程 K3（λ=2.50 的 EM-SBL 软 Top-20 + C2 经典剥离器）基本复现（ID 30 dB 2.56% vs 1.17%，NTN-TDL OOD 1.51% vs 1.46%）。但 K3 比的 19 个传统钢人用的是写死 λ=0.25 或零参数初值，K3 的"7× 破地板"主要是在打没调好的基线；而且 λ=2.50 本身就在调参网格的边上。本轮任务：分段判断 K3 是否值得成卡。纯时间预算 ≤4.5 小时；100% 纯 CPU（CUDA_VISIBLE_DEVICES=""，≤10 核，OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1），临时目录 /data/guoyikun/tmp/funnel_g_r19/，tmux g_funnel_g_r19；本机严禁 >3 秒计算；禁重跑 r18 封存集；禁 git commit --amend；gpt-6.2-sol ≤5 次；产物存 ideas/r19/。

1. 【Step 1：只在开发集上，≤2 小时】
   a. 去波形词查新（1995–2026：semi-blind MIMO-OFDM doubly-selective channel estimation、data-interference-aware / self-interference noise variance SBL、soft support initialization、bilinear EP / turbo semi-blind），列出最接近的 3–5 篇并注明公式或章节位置，写 ideas/r19/step20_k3_prior_art.md。若已有工作覆盖"数据自干扰方差校准的 SBL 初始化 + 剥离/GN + EP"这一整套，直接按闸门不过处理。
   b. 推导零调参的解析 λ_analytic（由导频/数据功率比与盲估热噪声 σ̂_w² 导出），在 dev64 上与调参版对比；同时把 λ 网格外扩到 {2.5, 4, 6, 10} 看最优点是否还在边上（R1）。
   c. 写 ideas/r19/PRE_REG_k3_gate.md 并 commit，再跑：在全新开发集种子（与历史全部区间互斥）上，对比 K3 与**调好参的**经典钢人：①升级版 Arm 1c（SBL+GN，Top-4 硬截断，λ 用 λ* 或其自身扫描最优）；②R15 OMP+EM（噪声/正则按 R1 扫描）；③C1/C2；并做 2×2×2 单因子归因（λ_analytic vs 朴素 σ̂_w² × 软 Top-20 vs 硬 Top-4 × 抛物面牛顿+留一剪枝 vs 普通 GN）。报 SER、H0 NMSE、逐链路找径率、单核耗时、MACs，配对 bootstrap。
   d. 【闸门 G1（写进 PRE_REG）】K3 对"调好参的最强经典钢人"须过主账本：破壁账点估 ≥5× 且 CI95_lo(p_rival − 3.5 p_cand) > 0，或性能账 ≥+1.50 dB 且 CI95_lo ≥ +1.00 dB。
      - 不过：写 ideas/r19/k3_closure.md，结论写成"R18 的 17% 传统地板是噪声方差未校准的产物，调好 λ 的标准 SBL 初始化即可消除"，列出该教训对后续评测台的要求，追加 runs-g.md，commit，退出。不锁台、不跑 holdout。
      - 过：进入 Step 2。
2. 【Step 2：仅当 G1 通过】推导并用独立 MC 在 ≥3 组连续 OSR=8 RRC 工况（含 NTN-TDL）核验 1 条零拟合参数闭式结论（误差 ≤0.5 dB），存 ideas/r19/verify_theory_k3.py/.json；构建经 Sol 审定锁 MD5 的 ideas/harnesses/H-g-mimo-sbl-peel.py（同台 NTN-OFDM 与 AFDM，谁优如实写谁；内置上面全部调好参的钢人与 2×2×2 消融臂、全盲 σ̂_w²、batch=1 单核耗时与实迹 MACs）；新 holdout 种子取 20268000000+（与历史全部区间互斥），含同分布、3GPP TR 38.811 NTN-TDL-A/B + 1.25× 多普勒 + 滚降失配 OOD，以及 1 个 16-QAM 或更低导频开销的边界切片；冻结 commit、日志首行打印 SHA256 后单次运行 holdout，过 Sol Beat 1–2 零引导双拍终审，写 ideas/r19/stage2-g-mimo-sbl-peel.md，清理远端临时目录，新建 commit 后退出。
```

### 2. `runner h` —— 新开会话 · 模型 **`Neon xhigh`**（先核对复活条件，再二选一）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`
```text
你是 runner h。先读本工作树的 ideas/r18/physcheck_bentpipe.md、ideas/r18/postinv_bentpipe.md、ideas/r18/dleq_bentpipe.md、ideas/r18/audit_m15b02_closure.md、ideas/FUNNEL.md、ideas/prompts/round-19.md（重点 §一.4 的 R1–R5）、ideas/PROBLEMS.md 第三节 r18-h-bentpipe 行（Eric 11-27 已停放，写明了两条复活条件）与 CLAUDE.md。纯时间预算 ≤4.5 小时；100% 纯 CPU（CUDA_VISIBLE_DEVICES=""，≤10 核，OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1），临时目录 /data/guoyikun/tmp/funnel_h_r19/，tmux g_funnel_h_r19；本机严禁 >3 秒计算；禁重跑 r18 任何封存集；禁 git commit --amend；gpt-6.2-sol ≤5 次；产物存 ideas/r19/。

1. 【Step 1：bentpipe 复活条件核对，≤45 分钟，不改任何冻结文件】
   a. 用现有探针在开发集上算 IBO 0 / 1 / 3 dB 时中继功放输出波形（OFDM 与 AFDM，Rapp p_s=2、a_phi=0.60，与锁死评测台一致）的 ACLR 和 EVM。
   b. 查 3GPP TS 38.106（NCR 射频要求）的 ACLR/EVM 限值，并查车载 / 高铁 / 无人机 AF 中继和直放站是否普遍做 DPD、是否会工作在 IBO ≤1 dB；每条结论给出处。
   c. 写 ideas/r19/revival_check_bentpipe.md，逐条判定两条复活条件：①存在不做 DPD、工作于 IBO ≤1 dB、且满足或豁免带外指标的真实中继类别；②IBO 0 dB 波形的 ACLR 与该类别的指标一致。commit。
2. 【Step 2A：仅当两条复活条件都成立 → 收口 dualhop-nc-relay】
   - 1995–2026 双跳非线性 AF 中继查新（nonlinear amplify-and-forward relay、Wiener–Hammerstein two-hop identification、vehicular / UAV mobile relay PA nonlinearity、Local-Area NCR NLOS backhaul），写 ideas/r19/step20_dualhop_prior_art.md；
   - 构建锁死评测台 ideas/harnesses/H-h-dualhop-nc-relay.py：基线池纳入 E_a（真 H_dl/H_ul 块 MMSE + 异方差逆映射 + 上行 EP）、E_b（公开级联分解 + 块 MMSE + 逆映射），**新增中继侧 DPD 线性化臂**（R2）；每帧保存 rx_stats，接入实迹 MACs 计数，内置 workers=1、batch=1 四工况单核计时；适用域外边界（晴空 LOS 回传、IBO ≥3 dB 且信道已知时 E_a 反超 V2）写进报告正文；
   - 尾帧门限（≤1.50%）只能在锁台前的 PRE_REG 里按开发集离散度写死，**不得为了过线在开发集上反复微调重捕门限**；
   - 冻结 commit、Sol 1 次锁前核查后，用新种子单次跑 holdout（日志首行打印 SHA256），Sol Beat 1–2 双拍终审，写 ideas/r19/stage2-h-dualhop-nc-relay.md。
3. 【Step 2B：复活条件任一不成立 → 转修 P-m-15b-02 盲分支】
   - 背景（audit_m15b02_closure.md）：盲分支 V2_BlindH1Sig 对三个同条件盲对手点估 4.5–12×，但 5× CI 门只在 H1 通过；192 帧里 55 帧 Stage-0 没锁住（最终 H1 NMSE 停在 −15 到 −17 dB，H3 的 Stage-0 初估只有 −5.88 dB），拖尾 14.6%。
   - 只改 Stage-0 捕获（多起点，或用期望用户导频做粗初始化），其余冻结；写 ideas/r19/PRE_REG_m15b02_stage0.md 并 commit 后在开发集上调；闸门（R5）：开发集上盲分支对三个盲对手在 ≥3/4 工况过配对 5× CI 门且拖尾 ≤5%；不过就写报告退出。
   - 过闸门：新种子单次确认（与 r16/r18 全部区间互斥，日志首行打印 SHA256），Sol 双拍终审，写 ideas/r19/stage2-m15b02-blind.md。
4. 两条路线都要：清理远端临时目录，追加 runs-h.md，新建 commit 后退出。
```

### 3. `runner k` —— 新开会话 · 模型 **`Carbon (High)`**（`P_3` 交叉 + 低轨卫星纯传统开荒）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`
```text
你是 runner k。先读 ideas/FUNNEL.md、ideas/prompts/round-19.md（重点 §一.4 的 R1–R5）、ideas/r16/stage2-k-curved-bistatic-isac.md 第 8 节、ideas/r16/sol_r16_v2_call5_final_audit.md 与 CLAUDE.md。纯时间预算 5–6 小时；禁用神经网络与 GPU（CUDA_VISIBLE_DEVICES=""），100% 在 deinlab ≤10 核 CPU，OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1，临时目录 /data/guoyikun/tmp/funnel_k_r19/，tmux g_funnel_k_r19；本机严禁 >3 秒计算；禁 git commit --amend；gpt-6.2-sol ≤5 次；产物存 ideas/r19/。

0. 【Step 0：k01+k02 的 P_3 完整交叉，≤90 分钟，只做归因、不判生死】
   - Sol 终审指出 P_3 只部分闭合：缺"啁啾开关 × 接收链"的完整交叉。用 r16 现成候选（不改冻结文件），在与 r16 全部区间互斥的新开发集种子上做 2×2：发射端 {c1 = c1*, c1 = 0} × 接收链 {AFDM 斜脊接收链, 逐块簇护卫 OFDM 接收链}；尽量对齐 BW99 与有效导频数，对不齐的地方逐项写明。报 Pd（等校准虚警）、SER、耗时，给出"波形主效应"和"接收链主效应"的配对 CI。
   - 写 ideas/r19/p3_crossing_k01k02.md 并 commit。结论只作为 k01 卡的归因证据，不改任何已有裁决。
1. 【Step 1：低轨卫星 / 3GPP NTN 选题、查新与拆台，≤60 分钟决定方向】
   - 硬底线：卫星/NTN 建模默认已完成星历与终端定位的公共大频偏/大时延预补偿，残余多普勒和时延必须由终端速度、波束几何和导频周期按 3GPP（TR 38.811 / 38.821、TS 38.211）推出并写明出处（R2）；同台评测 NTN-OFDM / DFT-s-OFDM 与 AFDM，谁优如实写谁。
   - 线索 A（超奈奎斯特残余多普勒下用多簇"角度–多普勒余弦耦合"解开整周模糊的信道外推）：**证据很弱**——m 的 probe_nn3_comb4_torus_varpro.py 只跑了 10 次、只打印不存档，分布外 10/10、分布内只有 5/10。先查新（kinematic Doppler unwrapping、super-Nyquist channel prediction、velocity ambiguity resolution / Chinese remainder Doppler、spatial–Doppler consistency channel prediction），再用 ≥96 次试验、存档 JSON 的 ≤15 分钟拆台探针复现，确认 Oracle/DiagSupp 相对满配且按 R1 调好参的传统钢人有 ≥ 主账本门槛的净空间，才可立项。
   - 线索 A 撞车或空间不足，自主转向线索 B（例：双低轨卫星双连接下的反向残余多普勒 + 大差分时延异步联合接收；NTN 多波束同频边缘异步干扰；星地双基地通感），同样先查新、再拆台。
2. 【Step 2：锁台 + ≥4 套纯传统方案对决 + 零拟合闭式定理 + 单次 holdout】
   - 先写 PRE_REG（含 R1 钢人扫参表、R3 对等反馈说明、R5 开发集闸门），开发集闸门不过就写报告退出；
   - 过闸门：搭建经 Sol 审定锁 MD5 的 ideas/harnesses/H-k-<slug>.py（连续时间 OSR=8 RRC 分数信道、进程级防真值泄露、能量与 BW99 对齐、内置已发表最强方法与满配教科书钢人、batch=1 单核耗时与实迹 MACs）；≥4 套纯传统方案对比（导频/帧排布子问题可用 evolve_cli.py）；推导并用独立 MC 在 ≥3 组工况核验 1 条零拟合闭式结论（误差 ≤0.5 dB 或相变边界误差 ≤20%）；冻结 commit、日志首行打印 SHA256、Sol 锁前核查后单次运行 holdout（含 3GPP NTN-TDL/CDL 工况），Sol Beat 1–2 双拍终审，写 ideas/r19/stage2-k-<slug>.md；未达标如实判死。
3. 清理远端临时目录，追加 runs-k.md，新建 commit 后退出。
```

### 4. `runner m` —— 新开会话 · 模型 **`Carbon (High)`**（低轨多波束预编码摊销 + 45 分钟双判据止损）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`
```text
你是 runner m。第 18 轮已确证单链路基带解调/估计不是神经网络的生态位。本轮是唯一神经探索位：改攻 3GPP TR 38.821 低轨卫星多波束 / 星地多用户下行高维非凸预编码与资源分配的置换等变图网络实时摊销，专打 ≥20× 算力摊销账，带 45 分钟双判据止损。先读 ideas/FUNNEL.md、ideas/prompts/round-19.md（重点 §一.4 的 R1–R5）与 CLAUDE.md。纯时间预算 5–6 小时；本机严禁 >3 秒计算；GPU 规范见 round-19.md §一.1；CPU ≤8 核且 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1；临时目录 /data/guoyikun/tmp/funnel_m_r19/；tmux g_funnel_m_r19；禁 git commit --amend；gpt-6.2-sol ≤5 次；产物存 ideas/r19/。

1. 【第一关：45 分钟止损门（两条判据任一触发就停神经线）】
   - 物理设定：3GPP TR 38.821 低轨多波束全频复用下行（例如星上 M=64–128 馈源/阵元服务 K=16–24 个同频终端），带逐馈源饱和非线性功放或逐阵元峰值功率约束、长 RTT 信道老化鲁棒约束，或离散跳波束 / 混合移相的非凸耦合；严禁选可被 K×K Woodbury 降维成毫秒级小矩阵求逆的线性总功率 WMMSE（R2：参数给出处）。
   - 判据 ①（查新）：2018–2026 无线/卫星图网络与展开式预编码查新（含 Shen TSP'21 WMMSE-GNN、Zhang JSAC'23、最新 LEO 多波束学习预编码）。若同一设定已有已发表方法做到 ≥20× 同精度加速，且你提不出可检验的差异点，就停。
   - 判据 ②（耗时）：在 deinlab 单核（batch=1，OMP=1）写出最快的传统非凸求解器钢人：向量化 + 解析梯度 + **跨时隙热启动**（用上一时隙解初始化；低轨信道在相邻时隙间变化慢，热启动通常大幅减少迭代），步长、迭代数、收敛门限按 R1 扫描；另跑多起点充分收敛参考上限。同精度（和速率差 ≤2% 或 ≤0.20 dB）下最快钢人单核中位耗时 <15 ms，就不存在 ≥20× 摊销空间——严禁写慢循环凑假提速。
   - 任一判据触发：把实测数据写进 ideas/r19/killtest_m_sat_precod.md，commit，剩余时间转第 3 步纯传统卫星开荒。
2. 【主路线（两条判据都通过才执行）】
   - 写 PRE_REG（R1 扫参表、R4 归因计划、R5 开发集闸门），commit；
   - 搭建经 Sol 审定锁 MD5 的 ideas/harnesses/H-m-sat-multibeam-gnn.py（进程隔离；统一计量 batch=1 单核 cpu_1core_ms 与全层+物理投影的精确 MACs/slot；封存 holdout 必含零重训 OOD：训练未见的用户数 K'=1.25K、非均匀热点簇分布、未见仰角/莱斯 K 因子与功放回退点）；
   - 设计波束/馈源 × 用户双边置换–相位等变轻量图网络或物理展开 FP-GNN，三臂归因（Arm 1 热启动最快传统钢人全迭代曲线；Arm 2 已发表 WMMSE-GNN 基线 + 等参数无等变 MLP/CNN；Arm 3 本方案及去物理算子/去等变消融，R4 要求在开发集上先做完）；
   - 严验：①距收敛传统钢人和速率 ≤2.0%（≤0.20 dB）且单核耗时与 MACs 点估均快 ≥20.0×（CI95_lo ≥15.0×）；②等变结构相对等参数 MLP 净贡献 ≥50%；③零重训 OOD 亏损 ≤3.0%（≤0.50 dB）且保住 ≥15.0×；④1 条零拟合参数的等变/对偶闭式性质数值核验；
   - 冻结 commit、日志首行打印 SHA256 后单次运行 holdout，Sol 双拍终审，写 ideas/r19/stage2-m-sat-multibeam-gnn.md。
3. 【备选：纯传统卫星开荒（止损触发时执行，禁用神经网络与 GPU）】围绕低轨卫星 / 3GPP NTN 物理层（守星历预补偿底线并按 R2 推残余量；与 runner k 错开，优先考察双低轨卫星异步双连接的反向残余多普勒 + 大差分时延联合接收、星上多波束同频非线性互调干扰的结构化抵消，或 NTN 星地双基地通感杂波抑制），走完整纯传统闭环：查新 → PRE_REG（R1/R3/R5）→ 开发集闸门 → 锁 ideas/harnesses/H-m-<slug>.py → ≥4 套纯传统方案 + 零拟合闭式结论（≤0.5 dB）→ 单次 holdout + Sol 双拍终审，写 ideas/r19/stage2-m-<slug>.md。
4. 清理远端临时目录，追加 runs-m.md，新建 commit 后退出。
```

---

## 三、发车前（Claude / Eric）

1. 把本文件与 `FUNNEL.md` 同步到四个工作树（各 runner 分支只同步 `ideas/FUNNEL.md`、`ideas/prompts/round-19.md`、`ideas/PROBLEMS.md`，不动它们的 `r18/` 产物）。
2. 按 `CLAUDE.md` 跑镜像 `sync.sh`（vault 改动先 commit）。
3. 四个 runner 都用新会话、按上表选模型发车。
