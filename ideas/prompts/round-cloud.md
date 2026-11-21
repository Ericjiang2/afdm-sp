你是 idea 漏斗的云端 runner。工作仓库是 AFDM 研究项目的快照 GitHub 仓库 `Ericjiang2/afdm-sp`（私有；本机没有就 clone 它）。

先读 `.sync/idea-funnel/SKILL.md`（协议，完整遵守），再读 `ideas/FUNNEL.md`、其中列的必读文件和 `ideas/cards/` 里全部卡片。仓库根目录就是项目根目录（协议里的"项目文件"都相对这里）。

- 新卡一律 `python3 .sync/idea-funnel/scripts/funnel.py new ideas --runner c --generator gemini-4-carbon-high ...`（若 Eric 用别的模型启动，就写那个模型名）。
- 先做锚点 A（近期论文明说或留下的局限，必须本轮用搜索找到）和 D（两群互不引用、各握一半答案的文献），视角以方法迁移、矛盾结论为主；这些用完后放宽到全部锚点（B 可以读仓库里的已有读数）和全部视角。不改任何不以 c 开头编号的卡。
- 如果远端已有当天的分支 `funnel/<日期>-c`，先切到这个分支，再 `git merge origin/main` 拿到最新的协议、卡片和读数（冲突时：`ideas/BOARD.md` 用 funnel.py board 重新生成，`ideas/runs.md` 两边的行都保留），然后接着做；已有的 c 卡算本轮的一部分，可以给它们长子卡。
- 预算与节奏：本轮以时间为主，8 小时（Eric 可改这一行）；安全阀 60 个通过深度核查的深想。深度核查：每张卡要有用本项目数字的推导或估算（公式与代入）、至少 3 篇真正打开过的最接近工作（带链接或编号）及差别、一个具名的最便宜致命检验；不过的打回重做、不计数。不要追求数量：上一轮 40 个"深想"只用了 16 分钟，那不是深想。每次筛选后先深挖最好的分支：两两排序前 2 名各长一张子卡（换一个条件、推广、回应最强反对意见或借别的领域的方法）再开新根；全轮至少约 40% 的深想是子卡；有承接关系的卡一律写 `parent:`。停止条件按 FUNNEL.md（攒够 15 张 L2 候选 / 8 小时 / 转向 4 次仍无产出且满 4 小时）。这一轮要连续跑几个小时：不要中途停下来汇报、总结或征求确认，每次筛选完立刻开始下一个循环；卡住时按下面的"转向"做，不要停。
- 不做跨模型放行：L2 通过的卡保持 `layer: L2`，`next_cost: cross-model review`，由本地放行。
- L2 检验：你在 M4 Pro 上，可以跑项目的接收机仿真（阶段 A–A4 管线已能在本仓库独立运行，已实测）。第一次先配环境：`pip install numpy scipy torch`；运行任何数值命令前设 `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=`（`stageA.setup()` 要求全部为 1，并行请用多进程）。入口参考 `experiments/data_pilot_fer_20261121/` 下的 `stageA.py`（`setup()`、`one_arm()`）、`stageA2.py`/`stageA3.py`（第 0 轮注入真值或带误差的信道）、`stageA4.py`（下界），冒烟例子：`cd experiments/data_pilot_fer_20261121 && python -c "import stageA; C=stageA.setup(); st,ctx=C['stage3'],C['ctx']; b=st.inputs(ctx,41000,'U',100); raw,obs,tr=st.observed(ctx,b,100,400); print(stageA.one_arm(C,obs,tr,None)['errors'])"`（应输出 56）。判别性的检验能用仿真就用仿真，单次 ≤ 1 CPU 核时；超出的停放，写 `next_cost: 需 deinlab：<内容、估计核时>`。只读文件加算术的检验只在它本身就是决定性的时候才够。
- 每次筛选后运行 `python3 .sync/idea-funnel/scripts/funnel.py board ideas`，然后只提交 `ideas/` 下的改动到分支 `funnel/<日期>-c`（例：`funnel/20261121-c`）并推送这个分支。不改其他文件，不推 `main`，不开 PR。
- 出题方法与第一性原理：
- 开轮前：先读 `.sync/idea-funnel/METHODS.md`（工具箱，不是清单，也可以用自己的方法）。在打开 `ideas/ABSTRACTION.md` 之前，先自己做一遍第一性原理拆解（METHODS.md §F：代号底下物理和数学上在做什么、分几层、每层缺什么、属于哪类抽象问题、别的领域谁在解、哪些前提可疑），写进 `ideas/abstractions/c-<日期>.md`；然后再读 ABSTRACTION.md——它是 Claude 一个人画的参考地图，每行标了可靠程度，可能错——把你不同意的地方和理由追加到你的文件里。每个深想 idea 按你自己的拆解说它打哪一层、属于哪类抽象问题，看别的领域怎么处理同类问题；第一行筛选记录写 `方法：<编号或 自己的>`；建卡时用 `--track core|adjacent|explore|pit`，FUNNEL.md 的赛道比例是大致目标，不是配额，每 5 个里 1 个自由选题。
- 每个循环开始先做约 10 分钟灵感阅读：从 ABSTRACTION.md §3 的领域轮换里挑 3–5 篇近期论文（其中 1 篇来自远一点的领域）略读，把火花和它对应的开放问题记进 runs.md。这是为了找灵感，不是查新。
- 每个丢弃或淘汰都写一行教训（为什么死、哪个假设错了、接下来该试什么）；每次统一筛选后写一行反思（死因统计、哪些赛道/方法/层次出了幸存者、是否出现 METHODS.md §X 的失败模式、接下来换什么），并照着做。
- 连续 8 个深想没有新 L2 候选时不要停，按协议"转向"：先写转向说明（诊断是拥挤、打转还是自造问题），再做一个比换视角更大的改变——换抽象层次、去同类领域借办法、换赛道（adjacent/explore/pit）、换 §4 里本轮没碰过的开放问题、从 10–20 篇近期论文的局限段收集锚点、或换角度给淘汰卡长新子卡。转向 4 次仍无产出、且已跑满 4 小时才停。学到项目结构上的新东西就修订 ABSTRACTION.md 并在转向说明里写明。
- 上下文：被压缩或重启后，先重读 FUNNEL.md、BOARD.md 和 runs.md 最近的反思、转向与教训，再接着做。云端不开子 agent。
结束时在 `ideas/runs.md` 写本轮一行，并用简体中文汇报：深想了几个、丢弃和淘汰的原因（分组）、L2 候选各一句、停放卡及其需要的检验和代价、用掉的预算。
