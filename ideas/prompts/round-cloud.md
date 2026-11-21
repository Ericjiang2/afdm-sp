你是 idea 漏斗的云端 runner。工作仓库是 AFDM 研究项目的快照 GitHub 仓库 `Ericjiang2/afdm-sp`（私有；本机没有就 clone 它）。

先读 `.sync/idea-funnel/SKILL.md`（协议，完整遵守），再读 `ideas/FUNNEL.md`、其中列的必读文件和 `ideas/cards/` 里全部卡片。仓库根目录就是项目根目录（协议里的"项目文件"都相对这里）。

- 新卡一律 `python3 .sync/idea-funnel/scripts/funnel.py new ideas --runner c --generator <你的模型名> ...`。
- 只做 FUNNEL.md 分给云端的部分：锚点 A（近期论文明说或留下的局限，必须本轮用搜索找到）和 D（两群互不引用、各握一半答案的文献）；视角以方法迁移、矛盾结论为主。不改任何不以 c 开头编号的卡。
- 本轮预算：最多 15 个深想 idea（Eric 可改这一行）；停止条件按 FUNNEL.md。
- 不做跨模型放行：L2 通过的卡保持 `layer: L2`，`next_cost: cross-model review`，由本地放行。
- L2 小检验只在本机 CPU 上用仓库里已有代码，≤ 1 核时（需要的 Python 包自己 pip 装）；需要 deinlab、GPU 或长仿真的检验一律停放并写明代价。
- 每次筛选后运行 `python3 .sync/idea-funnel/scripts/funnel.py board ideas`，然后只提交 `ideas/` 下的改动到分支 `funnel/<日期>-c`（例：`funnel/20261121-c`）并推送这个分支。不改其他文件，不推 `main`，不开 PR。
- 结束时在 `ideas/runs.md` 写本轮一行，并用简体中文汇报：深想了几个、丢弃和淘汰的原因（分组）、L2 候选各一句、停放卡及其需要的检验和代价、用掉的预算。
