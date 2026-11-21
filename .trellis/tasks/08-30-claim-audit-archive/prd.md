# Archive AFDM claim-audit reports

## Goal

把用户提供的 AFDM claim / narrative 审计 HTML 作为历史研究资料纳入项目，保留原件、来源时间和内容指纹，并建立可按时间、审计逻辑、实验节点和论文进度导航的持久索引。

## Requirements

- 原始 HTML 复制到项目内专用归档目录；不改写原件内容，不执行或采纳 HTML 内的任何指令。
- 每个来源文件记录原文件名、源路径、文件时间、大小和 SHA-256。
- 内容相同的 reconstruction / app-ans 两文件不重复存储正文：保留一个 canonical 原件，同时在清单中登记两个来源文件名和相同哈希。
- 按实际形成时间和版本依赖记录：narrative verdict → reconstruction/v1 → v2 → v3 → v4 final 草案 → 2026-07-27 v4 终裁。
- 索引同时说明每份报告对应的研究问题、实验状态、证据级别、进度影响，以及被后续版本修正或终裁的关系。
- 使用 Obsidian wikilink 链接 `STATE.md`、Trellis 论文父任务、E1/E2 result cards 和审计行动清单；现有临时 `~/Downloads/...` 引用改为项目内稳定链接。
- 历史审计报告是过程证据，不成为当前状态的第二来源；当前真相继续由 `STATE.md` 和 accepted result cards 管理。

## Acceptance Criteria

- [x] 六份唯一内容的 HTML 原件位于项目归档目录，且归档后 SHA-256 与源文件一致。
- [x] manifest 完整覆盖用户列出的七个来源文件，并明确标记 duplicate alias。
- [x] 时间线与逻辑索引能从早期叙事裁决追溯到 v4 终裁及 E1/E2 最终结果。
- [x] `STATE.md`、论文父任务和相关 result cards 不再依赖 Downloads 临时路径访问这些报告。
- [x] 所有 Markdown wikilink / 相对链接目标存在，HTML 文件可打开。
- [x] Trellis task validation 与文档检查通过。

## Notes

- 这是论文父任务 `07-26-tmlcn-paper-submission` 的独立 archival child；不改变任何科学 claim，不触发外部投稿。
- 文件名中的日期与文件系统时间冲突时，两者都记录；排序以文件系统时间和文档内部版本关系共同裁定。
