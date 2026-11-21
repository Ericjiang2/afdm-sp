你是 idea 漏斗的本地 runner。按协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md` 在本项目的 `ideas/` 跑一轮，完整遵守协议（含其中的 Model roles 表）；先读 `ideas/FUNNEL.md`、其中列的必读文件和 `ideas/cards/` 里全部卡片。

范围：不限锚点和视角，本地能做的都可以做；优先做云端做不了的（要 ssh deinlab 的检验、要调外部模型的、要用本机 skills 的）。另外负责已有的待办卡 I-20261121-02、08、09、10。不改 c 开头的卡（云端的），除非是导入后的统一筛选和放行。

外部模型调用（都在项目根目录运行；P 为填好锚点和视角的提示）：
- `P=$(sed 's/{anchor}/<锚点或"自选">/; s/{lens}/<视角或"自选">/' ideas/prompts/external-idea.md)`
- Gemini Neon 出题：`~/.local/bin/agy -p "$P" --model gemini-4-neon-high --mode plan --add-dir ~/projects/personal-ai-workflow/skills/idea-funnel --print-timeout 0`（只读；一次要几分钟，放后台）
- Astra 出题：`printf '%s' "$P" | codex --search exec --sandbox read-only -m gpt-6.2-astra -`
- Astra 推导或审计、Sol 跑小代码：`codex exec --sandbox read-only -m <gpt-6.2-astra|gpt-6.2-sol> -`（提示走 stdin）
- Hydrogen 两两比较或白话：`~/.local/bin/agy -p "<提示>" --model gemini-4-hydrogen-high --mode plan --print-timeout 0`
- Claude 评审 GPT 出的卡：`devin -p --model claude-opus-5-5-high "<提示>"`

每个循环：
1. 你自己深想一个 idea（协议第 1 步），同时在后台并行让 Gemini Neon 和 Astra 各独立深想一个。按 Model roles 分配：Neon 拿跨领域类比、方法迁移、玩具设定或锚点 D；Astra 拿推导型的题，给它指定锚点；你自己定题定调。外部输出不是 DROPPED 的，用 `python3 ~/projects/personal-ai-workflow/skills/idea-funnel/scripts/funnel.py new ideas --runner l --generator <模型> --title ... --anchor ...` 建卡并原样填入；自己的卡 `--generator` 写你的模型名。DROPPED 的记进 runs.md。
2. 每攒 5 张做一次统一筛选（协议第 3 步）：先导入云端已推送的卡（`~/projects/personal-ai-workflow/skills/idea-funnel/scripts/import_branch.sh /Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/repo.git funnel/<日期>-c ideas`，分支还不存在就跳过）；你两两比较排一次；再把在筛卡片一次性交给 Hydrogen 做两两比较排序（多数卡是 Gemini 出的就改用 Sol）。分歧大的都留下。
3. L1 查新可交给 Gemini Neon；L2 推导和估算交给 Astra；L2 小检验 ≤ 1 CPU 核时，可以 ssh deinlab，必须遵守项目 CLAUDE.md 的远程规则（不写 /tmp、tmux 用 g_ 前缀、conda AFDM）。不启动长仿真，不用 GPU。
4. 放行：Claude 或 Gemini 出的候选卡交 Astra，GPT 出的交 Claude（devin -p）；同一评审的候选合成一次调用。按协议记录评审者、模型和结论。进 L3 的卡，把"白话与类比"一节交 Hydrogen 改写成更白的话（只改这一节，事实不变）。
5. 运行 `funnel.py board ideas`，只 `git commit` 本项目的 `ideas/`（不 push）。

预算：本轮最多 15 个深想 idea，外部模型出的也算在内（Eric 可改这一行）；停止条件按 FUNNEL.md（10 张彼此不同的 L3 / 预算 / 连续 8 个无产出）。
结束时在 `ideas/runs.md` 写本轮一行（各模型出了几个、各自存活几个），用简体中文向 Eric 汇报：深想了几个、丢弃和淘汰的原因（分组）、L3 卡各一句、停放卡及其需要的检验和代价、用掉的预算。
