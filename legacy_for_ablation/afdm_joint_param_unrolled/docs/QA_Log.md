# QA Log — afdm_joint_param_unrolled

## 格式说明

```markdown
## Q[ID] 问题标题

**提问时间**: YYYY-MM-DD
**提问者**: User/AI
**状态**: 待回答 / 已回答 / 已解决

### 问题描述
...

### 答案
...

### 后续行动
- [ ] 行动1
- [ ] 行动2
```

---

## Q001 项目框架改造确认

**提问时间**: 2026-03-20
**提问者**: AI
**状态**: 已解决

### 问题描述
为已有项目添加层级上下文框架，需要确认：
1. 项目路径是否正确
2. 父级上下文如何设置
3. 是否保留原有文件

### 答案
1. 项目路径: `01_Projects/afdm_end_to_end/OTFS-channel-estimation/afdm_joint_param_unrolled`
2. 父级上下文指向 L2: `../../_CONTEXT.md`（afdm_end_to_end）
3. 原有文件零修改，仅新增框架文件

### 后续行动
- [x] 创建 _CONTEXT.md
- [x] 创建 _README_AI.md
- [x] 创建 _QA_Index.md
- [x] 创建 _Log.md
- [x] 创建 docs/ 目录

