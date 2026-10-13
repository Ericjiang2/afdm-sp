# 🤖 AI 接手强制维护协议 (README_AI)

作为被唤醒的 OpenClaw/Claude 助手，在回答用户的任何新问题并得出结论后，你**必须**遵循以下规则将对话成果归档：

1. **识别问题与分类写入**：
   - 包含一问一答的交互/理论溯源 -> 优先追加至 `docs/QA_Log.md` (采用 Q: A: 格式)
   - 纯粹的数学推导、公式演算 -> 追加至 `docs/Knowledge.md`
   - 代码结构变动分析、模块演进 -> 追加至 `docs/Code_Analysis.md`
   - 定位并修复 Bug 的流水账 -> 追加至 `docs/Debug_Log.md`
   - 带实验参数和性能图表的数据记录 -> 追加至 `docs/Results.md`

2. **不可覆盖 (Append Only)**：
   在向 markdown 文件写入记录时，除非涉及重构文档结构，否则应**在文件末尾追加 (Append)**，千万不能把旧的实验记录删掉。

3. **同步元数据与主索引**：
   写完底层日志后，不要忘记向上"冒泡"：
   - 在 `_QA_Index.md` 增加一条对应的最新索引概要。
   - 在 `_Log.md` 中简短记录当天的里程碑（如适用）。
   - 最后，修改本层级的 `_Log.meta.json` (更新 `last_entry_time`, `entries_count`, `last_entry_id`) !

4. **路径免疫原则**：
   本项目随时可能改变文件夹层级而被移动。因此，**项目的唯一身份标识是 `_Log.meta.json` 里的 `project_id`**，`parent_path` 全部采用如 `../` 的相对路径。如果你发现上级结构断链，请立即请求全局索引重建修复。
