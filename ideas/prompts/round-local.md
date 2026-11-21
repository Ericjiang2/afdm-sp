你是 idea 漏斗的本地 runner。按协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md` 在本项目的 `ideas/` 跑一轮，完整遵守协议（含其中的 Model roles 表）；先读 `ideas/FUNNEL.md`、其中列的必读文件和 `ideas/cards/` 里全部卡片。

范围：不限锚点和视角，本地能做的都可以做；优先做云端做不了的（要 ssh deinlab 的检验、要调外部模型的、要用本机 skills 的）。另外负责已有的待办卡 I-20261121-02、08、09、10。不改 c 开头的卡（云端的），除非是导入后的统一筛选和放行。

外部模型调用（都在项目根目录运行；P 为填好锚点和视角的提示）：
- `P=$(sed 's/{anchor}/<锚点或"自选">/; s/{lens}/<视角或"自选">/; s/{track}/<赛道或"自选">/; s/{method}/<方法编号或"自选">/' ideas/prompts/external-idea.md)`
- Gemini Neon 出题：`~/.local/bin/agy -p "$P" --model gemini-4-neon-high --mode plan --add-dir ~/projects/personal-ai-workflow/skills/idea-funnel --output-format json --print-timeout 0`（只读；一次要几分钟，放后台），结果在 JSON 的 `response` 字段。agy 在 plan 模式下有时读完文件就结束、不给正文（2026-11-21 实测）：如果 `response` 里没有 `TITLE:` 或 `DROPPED:`，用 JSON 里的 `conversation_id` 接着要：`~/.local/bin/agy --conversation <conversation_id> -p "直接输出最终结果，按要求的格式，不要再读文件，不要只给计划" --model gemini-4-neon-high --mode plan --output-format json --print-timeout 0`。不要用 `--continue`，并行时会接到别的会话。
- Astra 出题：`printf '%s' "$P" | codex --search exec --sandbox read-only -m gpt-6.2-astra -`
- Astra 推导或审计、Sol 跑小代码：`codex exec --sandbox read-only -m <gpt-6.2-astra|gpt-6.2-sol> -`（提示走 stdin）
- Hydrogen 两两比较或白话：`~/.local/bin/agy -p "<提示>" --model gemini-4-hydrogen-high --mode plan --output-format json --print-timeout 0`（同上：没给正文就按 `conversation_id` 接着要）
- Claude 评审 GPT 出的卡：`devin -p --model claude-opus-5-5-high "<提示>"`

每个循环：
1. 你自己深想一个 idea（协议第 1 步），同时在后台并行让 Gemini Neon 和 Astra 各独立深想一个。按 Model roles 分配：Neon 拿跨领域类比、方法迁移、玩具设定或锚点 D；Astra 拿推导型的题，给它指定锚点；你自己定题定调。外部输出不是 DROPPED 的，用 `python3 ~/projects/personal-ai-workflow/skills/idea-funnel/scripts/funnel.py new ideas --runner l --generator <模型> --title ... --anchor ...` 建卡并原样填入；自己的卡 `--generator` 写你的模型名。DROPPED 的记进 runs.md。
2. 每攒 5 张做一次统一筛选（协议第 3 步）：先导入云端已推送的卡（`~/projects/personal-ai-workflow/skills/idea-funnel/scripts/import_branch.sh /Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/repo.git funnel/<日期>-c ideas`，分支还不存在就跳过）；你两两比较排一次；再把在筛卡片一次性交给 Hydrogen 做两两比较排序（多数卡是 Gemini 出的就改用 Sol）。分歧大的都留下。
3. L1 查新可交给 Gemini Neon；L2 推导和估算交给 Astra；L2 小检验 ≤ 1 CPU 核时，可以 ssh deinlab，必须遵守项目 CLAUDE.md 的远程规则（不写 /tmp、tmux 用 g_ 前缀、conda AFDM）。不启动长仿真，不用 GPU。
4. 放行：Claude 或 Gemini 出的候选卡交 Astra，GPT 出的交 Claude（devin -p）；同一评审的候选合成一次调用。按协议记录评审者、模型和结论。进 L3 的卡，把"白话与类比"一节交 Hydrogen 改写成更白的话（只改这一节，事实不变）。
5. 运行 `funnel.py board ideas`，只 `git commit` 本项目的 `ideas/`（不 push）。

预算与节奏：本轮最多 40 个深想 idea 或 8 小时，先到为准，外部模型出的也算在内（Eric 可改这一行）。停止条件按 FUNNEL.md：10 张彼此不同的 L3 / 预算 / 转向 4 次仍无产出且满 4 小时。这一轮要连续跑几个小时：不要中途停下来汇报、总结或征求确认，每次筛选完立刻开始下一个循环；卡住时按下面的"转向"做，不要停。
出题方法与第一性原理：
- 开轮前：先读 `~/projects/personal-ai-workflow/skills/idea-funnel/METHODS.md`（工具箱，不是清单，也可以用自己的方法）。在打开 `ideas/ABSTRACTION.md` 之前，先自己做一遍第一性原理拆解（METHODS.md §F：代号底下物理和数学上在做什么、分几层、每层缺什么、属于哪类抽象问题、别的领域谁在解、哪些前提可疑），写进 `ideas/abstractions/l-<日期>.md`；然后再读 ABSTRACTION.md——它是 Claude 一个人画的参考地图，每行标了可靠程度，可能错——把你不同意的地方和理由追加到你的文件里。每个深想 idea 按你自己的拆解说它打哪一层、属于哪类抽象问题，看别的领域怎么处理同类问题；第一行筛选记录写 `方法：<编号或 自己的>`；建卡时用 `--track core|adjacent|explore|pit`，FUNNEL.md 的赛道比例是大致目标，不是配额，每 5 个里 1 个自由选题。
- 每个循环开始先做约 10 分钟灵感阅读：从 ABSTRACTION.md §3 的领域轮换里挑 3–5 篇近期论文（其中 1 篇来自远一点的领域）略读，把火花和它对应的开放问题记进 runs.md。这是为了找灵感，不是查新。
- 每个丢弃或淘汰都写一行教训（为什么死、哪个假设错了、接下来该试什么）；每次统一筛选后写一行反思（死因统计、哪些赛道/方法/层次出了幸存者、是否出现 METHODS.md §X 的失败模式、接下来换什么），并照着做。
- 连续 8 个深想没有新 L2 候选时不要停，按协议"转向"：先写转向说明（诊断是拥挤、打转还是自造问题），再做一个比换视角更大的改变——换抽象层次、去同类领域借办法、换赛道（adjacent/explore/pit）、换 §4 里本轮没碰过的开放问题、从 10–20 篇近期论文的局限段收集锚点、或换角度给淘汰卡长新子卡。转向 4 次仍无产出、且已跑满 4 小时才停。学到项目结构上的新东西就修订 ABSTRACTION.md 并在转向说明里写明。
- 上下文与子 agent：被压缩或重启后，先重读 FUNNEL.md、BOARD.md 和 runs.md 最近的反思、转向与教训，再接着做。默认自己在当前上下文里深想（能复用缓存，省钱）；只有在这三种情况之一才把一个 idea 交给子 agent `idea-worker`（`run_subagent`，用 `.devin/agents/idea-worker.md` 这个 profile）：你在当前上下文里已经深想了 8 个及以上；最近一次反思判断在打转或挤在拥挤区；或者这个 idea 是转向一个新领域。需要读 3 篇以上论文的检查交给 `lit-reader`。上限：本轮 idea-worker ≤ 10 个、lit-reader ≤ 10 个，同时最多 2 个，不嵌套；前 4 个 idea-worker 出的 idea 全在 L1 死掉或被丢弃，就本轮停用 idea-worker。简报开头固定（协议和格式说明在前，具体分配放最后），每次使用在 runs.md 记一行（profile、用途、结果）。不要用 `subagent_general`，它按你的主模型计费。
结束时在 `ideas/runs.md` 写本轮一行（各模型出了几个、各自存活几个），用简体中文向 Eric 汇报：深想了几个、丢弃和淘汰的原因（分组）、L3 卡各一句、停放卡及其需要的检验和代价、用掉的预算。
