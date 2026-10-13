# Claude Code Skills 使用手册

**创建日期**: 2026-03-21
**适用版本**: Claude Code CLI

---

## 技能总览

| 技能名称 | 用途 | 触发词 |
|---------|------|--------|
| `restructure-doc` | 将长篇未整理文档拆解重组进框架系统 | "帮我整理这个文档" / "restructure" |
| `context-pack` | 从项目提取精准上下文，打包给网页 AI | "帮我打包问题" / "context-pack" |

---

## 1. restructure-doc｜文档整理技能

### 什么时候用
- 你写了一个很长的研究日志/随手记，想整理进项目的框架系统
- 文档散落在各处，想统一归档到 `docs/` 目录
- 旧文档需要提取关键信息，但不想删除原文

### 核心原则
> **原始文档永远保留，整理版是新增，不是替换**

### 使用步骤

#### Step 1: 触发技能
```
你: 帮我整理这个文档
AI: 好的，请回答几个问题...
```

#### Step 2: 回答四个问题
| 问题 | 示例回答 |
|------|----------|
| **Q1** 文档路径或内容？ | `研究日志_阶段八.md` 或直接粘贴内容 |
| **Q2** 文档背景？ | "阶段八的实验记录，3月20日写的，记录Oracle Sweep结果" |
| **Q3** 整理目标？ | A-完整保留 / B-提取关键 / C-只取某类 |
| **Q4** 有错误内容？ | "第3节的结果已经过时，不要整理进去" |

#### Step 3: 确认文档地图
AI 会输出文档结构分析：
```
文档地图：
[块-01] 行1-45   | 类型: Knowledge | 主题: LMMSE原理推导
[块-02] 行46-80  | 类型: CodeAnalysis | 主题: 矩阵维度问题
...
```

你可以：
- 说"**全部确认**" → 跳过逐块确认
- 说"**块-02改成Debug类**" → 调整分类
- 说"**块-05跳过**" → 不整理某块

#### Step 4: 分批写入
AI 每次处理 1-2 块，生成标准格式后问你"OK?"，确认后才写入。

#### Step 5: 处理原文档
AI 会问：
- **A** - 移动到 `docs/_Archive/`（推荐）
- **B** - 加标注 `[已整理至框架，日期]`，原地保留
- **C** - 不动

### 整理后的文件去向

| 内容类型 | 目标文件 | 条目编号示例 |
|---------|----------|-------------|
| 技术原理、公式推导 | `docs/Knowledge.md` | `kn-0321-01` |
| 代码分析、架构设计 | `docs/Code_Analysis.md` | `ca-0321-02` |
| 问题记录、决策讨论 | `docs/QA_Log.md` | `qa-0321-03` |
| 实验结果、性能数据 | `docs/Results.md` | `rs-0321-01` |
| Bug记录、调试过程 | `docs/Debug_Log.md` | `bg-0321-01` |
| 随手记、草稿 | `docs/_Raw_Notes.md` | 无编号 |

### 示例对话
```
你: 帮我整理这个文档
   [粘贴 研究日志_阶段八_OracleSweepAndHeuristicDiagnosis.md]

AI: Q1: 文档路径或内容？
    Q2: 这份文档背景？
    Q3: 整理目标？（A/B/C）
    Q4: 有错的内容？

你: Q1: 就是粘贴的内容
    Q2: 阶段八实验记录，3月20日写的
    Q3: B - 提取关键信息
    Q4: 没有

AI: [输出文档地图]

你: 全部确认

AI: [处理块-01，展示整理后的格式]
    这样写OK吗？

你: OK

AI: [写入 Knowledge.md]
    [处理块-02...]

    整理完成！原始文档怎么处理？（A/B/C）

你: A

AI: [移动到 docs/_Archive/]
    完成！新增条目：
    - Knowledge.md: 2条
    - Code_Analysis.md: 1条
    - Results.md: 1条
```

---

## 2. context-pack｜问题打包技能

### 什么时候用
- 遇到问题需要问网页 AI（Claude.ai / ChatGPT）
- 项目代码太多，手动复制粘贴太麻烦
- 想让网页 AI 分析代码，但怕遗漏关键上下文

### 核心原则
> **零幻觉，所有内容必须来自实际文件**

### 使用步骤

#### Step 1: 触发技能
```
你: 帮我打包问题
AI: 好的，请回答几个问题...
```

#### Step 2: 回答三个问题
| 问题 | 示例回答 |
|------|----------|
| **Q1** 你的问题？ | "Stage6 的 BER 比预期高，怀疑是 alpha 参数设置问题" |
| **Q2** 怀疑哪个模块？ | "afdm_joint_param.py 里的 ParamLearnedJointReceiver" |
| **Q3** 期望网页AI做什么？ | A-找bug / B-解释逻辑 / C-优化方案 / D-验证论文 / E-其他 |

#### Step 3: 确认提取清单
AI 会列出要提取的内容：
```
必须提取：
  [ ] afdm_joint_param.py 的 ParamLearnedJointReceiver 类
  [ ] alpha 参数的定义和默认值
  [ ] forward() 方法中 alpha 的使用位置

可选提取：
  [ ] 相关的 diagnose() 方法

不需要：
  [ ] 画图部分
  [ ] 其他模型文件
```

你可以补充或去掉某些项。

#### Step 4: AI 读取文件并生成 Pack
AI 会：
1. 读取实际文件
2. 标注每段代码的来源（文件名+行号）
3. 生成架构摘要（调用链、关键参数）
4. 写入 `context_pack/[关键词]-[日期]-pack.md`

#### Step 5: 使用 Pack 文件
AI 输出：
```
打包完成 ✅

文件：context_pack/stage6-alpha-ber-0321-pack.md
大小：约 1200 字

使用方式：
1. 打开上面的文件
2. 复制 "--- 直接复制以下全部内容 ---" 之间的内容
3. 粘贴到 Claude.ai / ChatGPT
4. 直接发送

提取来源：
  afdm_joint_param.py 行45-120 ✅
  afdm_joint_param.py 行200-250 ✅
  [未找到: alpha_config.py] ⚠️
```

### Pack 文件结构
```markdown
---
# [直接复制以下全部内容发给网页AI]
---

## 背景
我在做 AFDM 联合参数学习接收机研究，使用 Python + PyTorch。

## 我的问题
Stage6 的 BER 比预期高，怀疑是 alpha 参数设置问题...

## 项目结构（涉及本问题的部分）
调用链：
  train_joint_param.py
    └─ ParamLearnedJointReceiver.forward()
         └─ alpha 在 outer loop 中的使用

关键参数：
  alpha_default = 0.5
  alpha_range = [0.1, 0.9]

## 相关代码（实际代码，含来源标注）
```python
# 来源: afdm_joint_param.py, 行45-67, 2026-03-20
class ParamLearnedJointReceiver(nn.Module):
    def __init__(self, ...):
        self.alpha = nn.Parameter(torch.tensor(0.5))
    ...
```

## 已知信息 / 我的分析
已经尝试过调整 alpha 初始化，但没有明显改善...

## 我需要你做的
请分析 alpha 参数在 outer loop 中的作用机制，
指出可能导致 BER 偏高的原因，给出调参建议。

---
# [复制到这里结束]
---
```

### 示例对话
```
你: 帮我打包问题

AI: Q1: 你的问题是什么？
    Q2: 怀疑哪个模块？
    Q3: 期望网页AI做什么？

你: Q1: Stage6 的 BER 比预期高，怀疑是 alpha 参数
    Q2: afdm_joint_param.py 里的 ParamLearnedJointReceiver
    Q3: A - 找bug

AI: 为了回答你的问题，我需要提取：

    必须提取：
      [ ] ParamLearnedJointReceiver 类定义
      [ ] alpha 参数相关代码
      [ ] forward() 方法

    可选提取：
      [ ] diagnose() 方法

    这样够吗？

你: 再加一个 verify_joint_param.py 的调用方式

AI: 好的，开始提取...
    [读取文件...]

    打包完成！
    文件：context_pack/stage6-alpha-debug-0321-pack.md

    使用方式：...

你: [打开文件，复制内容，粘贴到 Claude.ai]

    [网页AI给出分析结果]

你: 记录这个结论

AI: [用 log-append 写入 docs/QA_Log.md]
```

---

## 对比：两个技能的使用场景

| 场景 | 用哪个技能 | 为什么 |
|------|-----------|--------|
| 写了一篇很长的研究日志，想归档 | `restructure-doc` | 整理进框架，方便后续查阅 |
| 代码报错了，想问网页AI | `context-pack` | 提取精准上下文，发给网页AI |
| 实验记录太乱，想分类整理 | `restructure-doc` | 拆解到不同 docs/ 文件 |
| 想让AI解释一段复杂代码 | `context-pack` | 打包代码+上下文给AI分析 |
| 旧文档里有知识点要提取 | `restructure-doc` | 提取到 Knowledge.md |
| 需要跨文件分析一个问题 | `context-pack` | 自动提取相关文件 |

---

## 通用提示

### 快捷键
- 任何时候说"**详细点**"，AI 会展开说明
- 说"**跳过确认**"，可以加速流程（适合简单场景）
- 说"**回退**"，可以回到上一步

### 与现有框架的配合
```
restructure-doc 整理后的内容 → 写入 docs/*.md
                                 ↓
context-pack 提取上下文 ←──── 从 docs/*.md 读取
                                 ↓
                            打包给网页 AI
```

### 命名规范
- **日期格式**: 0321（月日）或 20260321（年月日）
- **关键词**: 用英文小写，连字符分隔，如 `stage6-alpha-ber`
- **条目编号**: 类型前缀-日期-序号，如 `kn-0321-01`

---

## 故障排除

### Q: restructure-doc 整理错了怎么办？
A: 原始文档还在（移动到了 `docs/_Archive/` 或加了标注），可以重新整理。

### Q: context-pack 提取的文件不全？
A: 在 Step 3 确认清单时，手动补充需要的文件路径。

### Q: Pack 文件发给网页 AI 后回答不好？
A: 可能是上下文不够，尝试：
1. 重新打包，增加更多相关文件
2. 在 Q3 选择不同的期望（如从"找bug"改为"解释逻辑"）
3. 手动补充一些背景信息到 Pack 文件

---

**最后更新**: 2026-03-21
**文档版本**: v1.0
