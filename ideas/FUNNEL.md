# Idea funnel：AFDM-channel-estimation（SP-AFDM 编码接收机，目标 TCOM）

协议：`~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md`（任何 agent 先读它）。看板：[BOARD.md](BOARD.md)（自动生成）。运行记录：[runs.md](runs.md)。

## 领域与目标
叠加导频 AFDM（及 OTFS 等时延–多普勒波形）的编码接收机与信道估计。要找的是原理级、能改变设计决定、够 Trans（TCOM/TWC）的研究问题；也接受能独立成文的诊断性问题。与当前论文（下方"已在做"）重复的不算。

## 出题前必读
- 当前状态与开放线索：[STATE.md](../STATE.md)（"接续入口"与"待办与开放线索"两段）。
- 已否定方向：[否定结果台账](../.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)。
- 已接受结论：[research-assets/index.md](../research-assets/index.md)；预测与打分：[prediction-ledger.md](../research-assets/prediction-ledger.md)。
- 已在做 / Eric 已定（不要重提）：现稿路线"译码失败后继续迭代还是重搜、各需多少时间"（Eric 11-20）；`11-21-data-pilot-fer` 任务（第 0 轮真值上限阶梯 A/A2/A3/A4）；未知噪声方差留作论文附注（Eric 11-21）；16-QAM 线对本文关闭（Eric 11-20）；"精确同延协方差是论文原理"已关闭（Eric 11-20）。

## 轮次与预算（不写则用协议默认值）
- target_ready: 10（攒够这么多张彼此不同的 L3 就停一轮；同根子卡算一张）
- stall_limit: 8（先按协议"放宽"——换视角和锚点、给幸存卡长子卡、从近期论文的局限段收集锚点、换角度重看淘汰卡——之后连续这么多个仍无新 L2 候选才停）
- screen_every: 5；l2_per_screen: 3
- round_budget: 每个 runner 每轮最多 40 个深想 idea 或 8 小时（先到为准；外部模型替本地出的也算）。粗估每个深想 idea 2–5 美元，一轮每边约 80–200 美元，未实测；Eric 改 prompts 里那一行即可调。
- cloud_target: 15（云端不能放行，攒够 15 张 L2 候选就停，交本地放行）
- l2_cap: 30 分钟 agent 时间，≤ 1 CPU 核时，不用 GPU，只用已有代码
- 跨模型放行：Claude 系生成时用 `codex exec --sandbox read-only -m gpt-6.2-sol`（提示走 stdin）或 `devin -p --model <GPT 系模型>`，每次筛选一次批量调用

## 在哪里跑（本地与云端并行）
- runner：本地 `l`（启动提示 [prompts/round-local.md](prompts/round-local.md)），云端 `c`（[prompts/round-cloud.md](prompts/round-cloud.md)）。
- 分工：本地不限锚点和视角，优先做云端做不了的（ssh deinlab 的检验、调外部模型、本机 skills），并负责已有待办卡（I-20261121-02、08、09、10）；本地每个循环还让 Gemini Neon 与 Astra 各独立深想一个（[prompts/external-idea.md](prompts/external-idea.md)）。云端不能调外部模型、不能上 deinlab、没有本机 skills：先做锚点 A、D 和方法迁移、矛盾结论视角，用完后放宽到全部锚点（B 可读仓库里的已有读数）和全部视角。重复的在统一筛选里合并；出题时两边互不看对方未筛选的卡。
- 模型分工：按协议的 Model roles 表——本地主 runner Claude Opus 5.5（定题定调）；Gemini 4 Neon 出跨领域类比和世界知识类题、做查新；GPT-6.2 Astra 出推导型题、做 L2 推导与放行审计；Gemini 4 Hydrogen 做两两比较初排和 L3 卡白话。云端 runner 用 GPT 系（`--model gpt-6-2-astra-high`）。
- 跨模型放行只在本地做：每张卡交给和它的 `generator` 不同家族的评审（Claude 出的交 `codex exec --sandbox read-only -m gpt-6.2-sol`，GPT 出的交 `devin -p --model claude-opus-5-5-high`）。
- cloud_repo：现有镜像 `Ericjiang2/afdm-sp` 的 `funnel/*` 分支（云端只写 `ideas/`；Eric 11-21 同意，镜像推送由 Claude 负责）。
- 镜像跟 vault `main`（11-21 起）；每轮开始前由 Claude 运行 `sync.sh`。同步时协议和脚本会复制到镜像的 `.sync/idea-funnel/`，云端从那里读。
- 只能在本地做的：ssh deinlab 的任何运行；跨模型放行；Eric 的批示与转 Trellis 任务。
