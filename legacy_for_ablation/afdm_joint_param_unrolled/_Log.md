# Log — afdm_joint_param_unrolled

## 格式说明

每个日志条目格式：

```
## YYYY-MM-DD HH:MM [类型] 标题

**状态**: 进行中/已完成/已归档
**涉及文件**: `file1.py`, `file2.py`
**关联**: [[相关文档]]

### 工作内容
...

### 关键结论
...

### 下一步
...
```

## 类型标记
- `[PROGRESS]` - 进展更新
- `[DECISION]` - 决策记录
- `[BUG]` - Bug 修复
- `[REFACTOR]` - 代码重构
- `[EXPERIMENT]` - 实验记录
- `[ANALYSIS]` - 结果分析
- `[SETUP]` - 项目设置/框架

---

## 2026-03-20 19:58 [SETUP] 项目框架初始化

**状态**: 已完成
**涉及文件**: `_CONTEXT.md`, `_README_AI.md`, `_QA_Index.md`, `_Log.md`, `_Log.meta.json`, `docs/*`
**关联**: [[改造前已有文档]]

### 工作内容
为已有代码项目 `afdm_joint_param_unrolled` 添加层级上下文框架。这是改造项目（retrofit），所有原有文件保持不动，仅新增框架文件。

### 原有文件（未修改）
- Python 代码: `afdm_*.py`, `train_*.py`, `verify_*.py` 等
- 现有文档: 9 个阶段文档（实现方案 + 研究日志）
- 输出目录: `outputs_*` 等
- 脚本: `.sh`, `requirements.txt` 等

### 新增框架文件
- `_CONTEXT.md` - 项目上下文
- `_README_AI.md` - AI 工作规则
- `_QA_Index.md` - Q&A 索引
- `_Log.md` - 工作日志（本文件）
- `_Log.meta.json` - 日志元数据
- `docs/QA_Log.md` - 详细 Q&A
- `docs/Debug_Log.md` - 调试记录
- `docs/Knowledge.md` - 知识点
- `docs/Results.md` - 实验结果
- `docs/Code_Analysis.md` - 代码解析
- `docs/_Raw_Notes.md` - 原始笔记

### 项目状态
当前处于阶段八（Stage 8）: Oracle Sweep + Heuristic Breakpoint Diagnosis
- 已完成 smoke 测试
- 等待正式诊断运行（200 帧 × 3 SNR）

### 下一步
1. 继续阶段八正式诊断实验
2. 分析 oracle sweep 结果
3. 确定下一轮优化方向

