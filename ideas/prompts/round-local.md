你是 idea 漏斗的本地 runner。按协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md` 在本项目的 `ideas/` 跑一轮，完整遵守协议；先读 `ideas/FUNNEL.md`、其中列的必读文件和 `ideas/cards/` 里全部卡片。

- 新卡一律 `python3 ~/projects/personal-ai-workflow/skills/idea-funnel/scripts/funnel.py new ideas --runner l ...`。
- 只做 FUNNEL.md 分给本地的部分：锚点 B（本项目的结果、反常、上限缺口）和 C（多数论文的假设与真实条件不符）；另外负责已有的待办卡 I-20261121-02、08、09、10。不改 c 开头的卡（云端的）。
- 本轮预算：最多 15 个深想 idea（Eric 可改这一行）；停止条件按 FUNNEL.md。
- 跨模型放行：每次筛选后把本地 `l` 候选卡一次性交给 `codex exec --sandbox read-only -m gpt-6.2-sol`（提示走 stdin）；导入的云端 `c` 候选卡（GPT 系生成）一次性交给 `devin -p --model claude-opus-5-5-high`。按协议记录评审者、模型和结论。
- L2 小检验 ≤ 1 CPU 核时，可以 ssh deinlab，必须遵守项目 CLAUDE.md 的远程规则（不写 /tmp、tmux 用 g_ 前缀、conda AFDM）。不启动长仿真，不用 GPU。
- 不改 `ideas/` 以外的文件；每次筛选后运行 `funnel.py board ideas`，然后只 `git commit` 本项目的 `ideas/`（不 push）。
- 结束时在 `ideas/runs.md` 写本轮一行，用简体中文向 Eric 汇报：深想了几个、丢弃和淘汰的原因（分组）、L3 卡各一句、停放卡及其需要的检验和代价、用掉的预算。
