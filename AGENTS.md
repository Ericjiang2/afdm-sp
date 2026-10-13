<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

- 流程从简：只做必要检查，避免重复审查和过度文档化，尽快执行并汇报结果；服务器规则照常严格遵守。

## 子代理上下文复用（2026-09-09 用户要求）

- 主会话负责一次性加载 Trellis 生命周期、当前任务及服务器规则。子代理不重复运行 trellis-start、get_context.py、task.py current，不重新分类或创建任务。
- 每次分派提供紧凑交接：任务/CSV 路径、子任务目标、文件所有权、验收条件、必需约束与待读文件。已注入内容不再读一遍；缺少具体约束时只补读对应文件或向主会话索取。
- 同一子代理优先复用；follow-up 只发送变化、证据与下一步，子代理保留已读上下文。新代理仍须获得必要代码规范和科学/服务器安全边界，不把未读取的内容谎报为已加载。
- 后续简单查找、搜索和代码查看交给 gpt-6-luna / xhigh；实现和正式审查使用 gpt-6-sol / high，除非用户对具体任务另有明确指定。已有代理按当前工作收尾，保留前任代码、结果、审计记录；不因换模型重新仿真。

## GitHub 只读镜像（2026-10-13）

- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `trans/tcom-main` 已提交的本目录，排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 按需同步：仅当用户明确说「推 GitHub / 同步镜像」时，先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得主动推送，不得把 vault 本身推到该仓库。
