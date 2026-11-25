你是 idea 漏斗的本地第二个 runner（runner `g`），在 agy 中运行，模型是 Gemini 4 Carbon（high）。本轮与主目录的本地 `runner l`（Devin，Claude 家族）同步物理隔离双开；你只管自己的 `g` 卡。

下文用 `M` 指主目录（只读）：`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`。你的工作目录是 `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`（独立 worktree，分支 `runner-g`）。

开始前先完整读 `$M/ideas/prompts/round-local.md`、协议 `SKILL.md` 的「Value ledgers」与「Public-pain check」两节、`$M/ideas/FUNNEL.md`、`$M/ideas/LESSONS.md` 和 `$M/ideas/BOARD.md`（看清全部已审结卡片，防撞题）。下面列的是你与 `round-local.md` 不同的地方，冲突时以本文件为准：

1. **读写与隔离边界**：
   - 只在自己的 worktree 里写文件、建 `--runner g --generator gemini-4-carbon` 的新卡，运行记录写 `ideas/runs-g.md`，缓存放 `~/.cache/idea-funnel/afdm-<日期>-g-r10/`。主目录 `M` 全程只读。
   - **每丢弃一个探针草稿或完成一个循环，必须在同一循环立即往 `ideas/runs-g.md` 写一行死因教训（带 `[轨A-纯通信]` 与 `[轨B-ISAC]` 累计计数）并执行 `git add ideas/ && git commit -m "..." -- ideas/`**（连续 **6 个独立探针方向**全死无新卡即计入停滞，必须写正式转向诊断换子题）。不 merge、不 rebase、不 push，严禁 `git stash/checkout/reset/clean`。

2. **第 10 轮「50% 纯通信 × 50% AFDM-ISAC」1:1 双轨对照规则（Eric 11-24）**：开轮先读 `$M/ideas/ABSTRACTION.md` §4（轨 A 三题 + 轨 B 三题及全量 62 篇顶刊已占先例清单）和 `$M/ideas/FUNNEL.md`；本轮停用锚点 B（项目接收机内部读数），取消第 9 轮的 4.5h 保底档时间锁，**从第 1 个循环起严格按单双数循环 `1 : 1` 交替跑两轨（两轨草稿数偏差不超过 ±1）**：
   - **单数循环跑 `[轨A-纯通信]`（50%）：「成熟强工具 + 真结合 AFDM 结构特点的顶刊落地」**
     - 聚焦 `ABSTRACTION.md` §4 的 **A1（双分数 `MIMO-AFDM` / 新型多址 RSMA·免授权·非正交结构化收发与分集分析）、A2（连续时间脉冲成形、模型化硬件损伤 `Sui TCOM'26` / `Mirabella JSAC'26` 未补偿平层与突发同步失配的闭式紧界 + 补偿——循环 1 可先花 20 分钟补跑第 9 轮 `g01` 阶段 B 的“等净吞吐短前导+经典同步”生死对照结案）、A3（变换域无地板低复杂度均衡/预编码与在线每帧快速选参）**。
     - **严守反套壳底线与长期品味 + 拆掉四把误杀枷锁**：把原工具只做 $\mathbf{F}_N\to\mathbf{A}$ 换符号就能原样跑通的一律判纯搬运秒弃；只要原工具直套（配平同外环标配后）会撞上 **AFDM 真实结构耦合**（一维模 $N$ 折叠/分段阶梯、CPP 边界相位扭转、啁啾参数 $(c_1,c_2)$ 与多天线/硬件损伤/分集阶的耦合）并经实质改造或推导专属紧界（PEP / 闭式 BER / 渐近 SINR）解决，**允许底层数学工具曾在毫米波/MIMO/信号处理中出现过，不再搞跨波形工具名连坐（检索时仍按抽象数学形式搜出母方法以构造 `naive_port`）**！打分集阶、抗硬件损伤、新接入或变换域检测时，**允许按顶刊主流在未编码高 SNR 分集区（高 SNR BER 赢 ≥1 个数量级 + 配解析 PEP/BER 紧界）或单遍接收下立卡**，也**禁止拿“退回单载波时域”自杀**。静态参数离线 5 分钟扫一遍即稳的照旧判伪痛点淘汰，只有随每帧瞬时状态变化的在线快速选参才按算力账放行；严禁初等恒等式小把戏、改简单信道凑增益与具体硬件测试台怪现象。
   - **双数循环跑 `[轨B-ISAC]`（50%）：「`AFDM-ISAC` 通感一体耦合破壁」**
     - 聚焦 `ABSTRACTION.md` §4 的 **B1（多用户下行 `MIMO AFDM-ISAC` 联合波束成形与低复杂度通感预编码——16 篇顶刊中 0 篇覆盖的真空带）、B2（随机高阶 QAM 数据旁瓣 + 强静止杂波淹没弱小运动目标的闭环消除，接 `Ni & Fan Liu TWC'26` / `Cui JSAC'26` 痛点）、B3（双基地异步 `STO+CFO`［直接打华为 `Song & Tong TWC'26` 只建模型未给算法的公开缺口］或饱和功放/量化下的通感联合同步与相干积累）**。禁止做无通信指标的纯雷达题与已被占满的无杂波单目标理想模糊函数推导。
     - 指标：通信 BER/FER 不退化（`≤0.2 dB`）下，雷达距离–多普勒旁瓣峰值/积分比 `PSLR/ISLR` 改善 `≥ 6–10 dB`、弱目标检测率显著提升或测距测速 `RMSE` 逼近 `CRLB`，或通感预编码算力相对逐帧凸规划同精度提速 `≥ 10×`。
   - **两轨通用硬铁律**：
     1. **先锁顶刊现成坏图且严守原论文参数（Paper-Figure First）**：每个草稿第一步必须点名 **1–2 篇 2024–2026 已发表顶刊的失灵图/高复杂度表/明确未补偿模型或 Future Work**，**严格在被引论文自身参数范围内复现痛点**后再解，严禁自己拉偏参数造地板；
     2. **基线分清「外围同预算标配必配齐」与「禁止自创跨论文核心耦合接口」**：新方案用到的同体制外围标配（同译码迭代轮数、同重试阶梯、同增益接口、EM 噪声方差、Bussgang 等教科书零阶线性标定）**基线必须对等装上**（单遍/未编码题双方保持单遍/未编码）；在此基础上，基线核心模块只比「单篇已发表最强 AFDM/ISAC 方法 + 母方法硬套 $\mathbf{F}_N\to\mathbf{A}$ 或现成模块原版接口朴素串联 `A → B`」，**严禁现场跨三四篇论文替基线重写内部耦合接口发明未发表系统自杀**！`A → B` 卡地板而耦合 `A ⇄ B` 打穿地板且 `A-only`、`B-only` 单块 `<80%` 即立卡（无接口冲突的 `IM+MDS+RIS` 堆砌仍封禁）；
     3. **防假加速与防自造难度锁**：提两阶段/多级快算法或在线快选参必同测**单级最简核**与**粗步长+精扫**且在悬崖点/地板区全网格不掉精度；省前导/省开销必比**等净吞吐率短前导/保护带基线**；捏合天线 `PASS`、阵列互耦排布、纯 AoA 机械滑轨仍封禁；神经网络降为可选普通工具（不占硬配额）。

3. **出题位与建卡前双关卡（更新 `Sol` 门审口径，防放水也防误杀！）**：
   - **外部无状态单发出题（`Astra / Opus`）停用**：每循环由你自己深想出题。
   - **每个达标草稿在建卡前实时过 `Sol` 门审（`codex -C /tmp --search exec --sandbox read-only -m gpt-6.2-sol -c 'model_reasoning_effort="high"' -`，每轮上限 `10` 次，超限或 Codex 额度用完时**不改用 Opus**（Eric 11-25）：先跳过，把该卡或草稿记入本轮 `runs` 记录的「待审」列表，卡保持 L1、不放行；可另开一个 agy 非本 runner 模型（如 `gemini-4-hydrogen-high`）做一次初查并标注「兜底初查（同家族）」，但不能据此放行，放行仍等 `Sol`）**：
     1. **发送给 `Sol` 的提示词必须明确写清第 10 轮新标尺**，同场只核四件事：(i) **AFDM / AFDM-ISAC 同设定是否已发表**（明确告知 `Sol`：按数学形式搜出母方法做对照，但不得因工具名在毫米波/MIMO/传统雷达出现过而判死；只审配平标配后直接换符号 $\mathbf{F}_N\to\mathbf{A}$ 是否原样能跑——零改造能跑或静态参数离线 5 分钟扫参即稳判 `DROP`，撞上并解决了 AFDM 专属耦合则通过）；(ii) **基线是否对等配齐外围同预算标配并包含已发表最强 AFDM/ISAC 基线与朴素串联/`naive_port`**（明确告知 `Sol`：同迭代轮数/重试/零阶线性标定必查配平，单遍/未编码题保持单遍/未编码；**禁止要求对比改发单载波，禁止要求替基线跨论文新发明未发表的内部耦合接口**；快算法须核单级核与粗步长对照，省前导须核等净吞吐短前导对照）；(iii) **是否在被引已发表论文自身参数范围内真实复现了失灵图/高复杂度表/未解模型** 且达到账本门槛；(iv) **拟定的 `title`（`≤ 26` 汉字且 `≤ 32` 字符）是否平实无黑话**。
     2. **短平实标题双重硬门检**：`funnel.py new` 与 `funnel.py board` 双重校验；每张卡筛选记录首行标明 `[轨A-纯通信]` 或 `[轨B-ISAC]`。

4. **快节奏筛选、第 6 步查新、第 7 步 L2 与 `deinlab` 环境铁律**：
   - **筛选触发**：**每攒满 `3` 张新 L1 卡，或距上次筛选满 `2 小时`（只要有 ≥1 张未筛 L1 卡；收尾前 75 分钟强制清筛）**，执行筛选 → 第 6 步异族查新（批量交 `Sol`；`Sol` 不可用时按第 3 条的「待审」处理，不改用 Opus，附第 10 轮 `novelty-importance.md` 新标尺） → 判 `(1a)/(1b)` 进第 7 步 L2。
   - **L2 与 `deinlab` 硬规则（严禁违背！）**：写好 `ideas/l2/PREDICTIONS_g_r10*.md` 并冒烟通过后，上 `deinlab` 前交 `Sol` 做 ≤3 分钟代码与基线快检。**`deinlab` 只准激活本人环境 `conda activate AFDM`（严格执行 `$M/ideas/prompts/round-local.md` 第 4 条的 `cd /data/guoyikun/tmp && conda activate AFDM && export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/.cache ...` 模板，严禁调 `/opt/anaconda3/envs/*` 的 `UWL` 等他人环境，脚本首行必打 `print(sys.executable, flush=True)` 核实为 `/home/guoyikun/.conda/envs/AFDM/bin/python`）**，会话名 `tmux g_funnel_g_r10*`，CPU 限 `≤ 16` 核，GPU 训练 `≤ 25` 分钟（跑前 `nvidia-smi`）。
   - **`verdicts.PASS_PRIMARY == false` 严禁标 `cross-model review`**（`true` 保持 `layer: L2, status: active, next_cost: cross-model review`；`false` 当场置 `killed` 或 `parked`）。本轮目标攒够 **`4` 张过关 L2 候选（轨 A、轨 B 各目标 2 张，单轨上限 3 张）** 或跑满 8 小时收尾，结束时在 `runs-g.md` 按 `[轨A-纯通信]` vs `[轨B-ISAC]` 对照汇总产出与死因，跑通 `funnel.py board ideas` 并提交。

5. **检索与文献深读工具**：直接调用零依赖标准库脚本 `python3 ~/projects/personal-ai-workflow/skills/idea-funnel/scripts/search_papers.py --query "..." --start-year 2022 --end-year 2026 --max-papers 10 --sources open_alex crossref` 与 `fetch_paper.sh`；需要读 3 篇以上长文献核查细节时可调 `~/.local/bin/agy -p "<提示>" --model gemini-4-hydrogen-high --sandbox --output-format json --print-timeout 0`。本轮预算 8 小时（安全阀 60 个深想），结束时在 `runs-g.md` 补全汇总行与最多 3 条“本轮提炼”，跑通 `funnel.py board ideas` 并提交。
