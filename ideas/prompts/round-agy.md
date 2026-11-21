你是 idea 漏斗的本地 runner，这次在 Antigravity IDE 里运行，模型是 Gemini 4 Carbon（high）。先完整读 `ideas/prompts/round-local.md` 并照做；下面是和它不同的地方，冲突时以本文件为准。

1. 身份：你属于 Gemini 家族。自己建的卡写 `--generator gemini-4-carbon`。在 `ideas/runs.md` 新开一行"本地第 2 轮（agy，Gemini 4 Carbon high）"，写实际开始时间；8 小时预算从这时算。缓存目录用 `~/.cache/idea-funnel/afdm-<日期>-l2/`。

2. 先收尾上一轮的遗留（runs.md 里 21:00 那条），再开新循环：
   - Codex 已换账号，可以用了。重跑三个空掉的调用，提示都在 `~/.cache/idea-funnel/afdm-20261121-l/`：`gate10_astra.prompt`（l02 第三次放行）、`gate12_astra.prompt`（c06 的 Astra 放行）、`c7-astra.prompt`（l09 的子卡）。命令：`codex exec --sandbox read-only -m gpt-6.2-astra - < <提示文件> > <同名 .out>`，放后台。
   - 把 `gate12_claude.out`（c06 → PASS，要求改三处，并附 cap 16 对照臂）写回卡 c06；c06 要 Claude 和 Astra 两家都过才升 L3。
   - 用 `c7-neon.json` 的 `response` 建前提卡（`--generator gemini-4-neon`，track pit）。
   - 新卡沿用 `python3 ~/.cache/idea-funnel/afdm-20261121-l/mkcard.py ideas <文本文件> <模型> "<记录>" [--parent <id>]`，或 `funnel.py new`。

3. 出题位（每个循环）：你自己深想一个；外部出题者必须是别的家族：
   - GPT：每个循环一个，默认 Sol，题目要严格推导时换 Astra（命令见 round-local.md）。
   - Claude：用 Eric 的订阅额度，省着用：每 3 个循环一个，或者第 6 条的防同质自查触发时再加一个；`printf '%s' "$P" | claude -p --no-session-persistence --effort high`（`P` 照 round-local.md 用 `external-idea.md` 填好）。不用 Claude 做评审。
   - 不再调 Gemini 出题（`carbon-idea`、agy Neon 出题都不用），因为你自己就是 Gemini。

4. 评审改派（你自己的卡是 Gemini 卡，Gemini 不能评 Gemini）：
   - 你自己的卡：第 7 步查新和第 8 步放行都交 Astra，合成一次 codex 调用（用 `novelty-importance.md`，保留最后的"放行"一节，把其中的"GPT 家族"读作"Gemini 家族"）。
   - GPT（Sol、Astra）出的卡：两步都交 Neon，一次 agy 调用（照 round-local.md）。
   - Claude 出的卡：查新交 Neon，放行交 Astra。
   - 两两排序：多数卡是你出的，按协议改用 Sol（`codex exec --sandbox read-only -m gpt-6.2-sol -`），不用 Hydrogen。
   - 进 L3 的卡，"白话与类比"仍交 Hydrogen 改写（只改写，不评判）。
   - 每次筛选每个评审只调用一次。
   - Astra 或 Neon 没额度时照 round-local.md 的"外部模型没额度时不要停"：跳过、标 `未审核`、记进 `待审` 清单；兜底评审用 `agy -p` 调 Neon（新上下文，每次筛选最多 2 次）。你自己的卡用 Neon 兜底是同家族，只能 KILL 或 REVISE，不能升 L3。

5. 这里没有 Devin 子 agent（`.devin/agents/` 和 `run_subagent` 都用不了）：默认在当前上下文里自己深想。round-local.md 里本该开 `idea-worker` 的三种情况，改为多调一次外部出题者，换一个脑子；要读 3 篇以上论文的检查，交 `~/.local/bin/agy -p "<提示>" --model gemini-4-hydrogen-high --sandbox --output-format json --print-timeout 0`。

6. 云端 runner 已停（Devin 额度用完），云端分支 `funnel/20261121-c` 的卡已全部导入，统一筛选时不用再导入。你是唯一的 runner：round-local.md 里"优先做云端做不了的"和"不改 c 开头的卡"两条作废，全部锚点和视角都归你，c 开头的卡（多是停放的）也可以由你补检验、改状态。只有一个 runner，又是 Gemini，出的题更容易越来越像：每次筛选的反思里查一次，最近 5 张存活卡是否都出自你自己；如果是，下一个循环让外部出题者（GPT 或 Claude）选题，你只做检验。

7. 其他照旧：命令都在项目根目录跑；ssh deinlab 遵守项目 CLAUDE.md 的远程规则（不写 /tmp、tmux 用 g_ 前缀、conda AFDM、先看负载）；只 `git commit` 本项目的 `ideas/`，不 push；中途不停下来汇报，卡住就按协议"转向"。被压缩或重启后，先读本文件，再读 round-local.md 和 runs.md 最近的状态快照。
