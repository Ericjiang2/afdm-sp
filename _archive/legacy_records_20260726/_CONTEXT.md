# CONTEXT — afdm-e2e-main

## 📍 我在哪里（层级路径）
- L0 全局根: ./ (my-vault根目录)
- L1 领域:   ./01_Projects/          (_CONTEXT.md)
- L2 项目:   ./01_Projects/afdm_end_to_end/  (_CONTEXT.md)
- L3 本项目: ./01_Projects/afdm_end_to_end/OTFS-channel-estimation/  ← 你在这里

## 🔗 上级汇报路径
parent_domain: afdm_end_to_end
parent_context: ../_CONTEXT.md
global_index:   ../../../_Projects_Index.json

## 📦 本项目基本信息
id: afdm-e2e-main
name: AFDM End-to-End Learning - Main Workspace
status: active
owner: User
created: 2026-03-27
last_updated: 2026-03-27

## 📝 项目描述
AFDM（Affine Frequency Division Multiplexing）端到端深度学习主工作空间。
本目录是从 OTFS-channel-estimation 仓库 fork 而来，用于探索 AFDM 端到端学习的多个子方向。

### 核心研究方向
1. **afdm_sp_joint_unrolled/** - 当前活跃方向：SP 联合展开检测器
2. **afdm_joint_param_unrolled/** - 联合参数学习接收机（阶段八，支撑文件夹）
3. **afdm_sp_refactored/** - SP 重构版本
4. 其他 afdm_* 目录 - 各种实验方向

### 技术栈
- **信号模型**: AFDM 调制/解调、时频域信道模型
- **学习架构**: Unrolled Neural Networks（展开神经网络）
- **基准方法**: LMMSE、OMP、Turbo、OAMP、DeepTurbo

## 📌 代码版本状态

```yaml
current_version: v0.1-main
active_branches:
  - v0.1-main (主线，初始框架)
archived: []
version_map: docs/Code_Versions.md
version_detail: docs/Code_Changes.md
```

**分支命名规范**:
- `v{大版本}.{小版本}-main` - 主线版本
- `v{大版本}.{小版本}-alt-{标签}` - 备用探索方向
- `v{大版本}.{小版本}-backup` - 归档备份

## 📂 子模块
- afdm_joint_param_unrolled: ./afdm_joint_param_unrolled/ (联合参数学习接收机，阶段八)
- afdm_sp_joint_unrolled: ./afdm_sp_joint_unrolled/ (当前活跃方向：SP联合展开)
- afdm_sp_refactored: ./afdm_sp_refactored/ (SP重构版本)

**第三方参考代码**（非afdm开头）:
- EP4IDD: ./EP4IDD/ (参考实现)
- GCEPNet: ./GCEPNet/ (参考实现)
- GNN-based-MIMO-Detection: ./GNN-based-MIMO-Detection/ (参考实现)
- OAMP-Net: ./OAMP-Net/ (参考实现)
- code: ./code/ (基础代码)
- matlab: ./matlab/ (MATLAB参考)

## ⚠️ AI自检（每次接手必做）
请验证以下路径实际存在，不存在则提醒用户更新：
- parent_context: ../_CONTEXT.md
- global_index: ../../../_Projects_Index.json

## 🤖 AI接手规则（必须遵守）
1. 先读本文件，再读 _README_AI.md，再读 _QA_Index.md 最近10条
2. 所有记录只追加，不覆盖，不删除历史
3. 写完任何条目后，同步更新 _QA_Index.md 和 _Log.meta.json
4. 不确定的操作先用中文提问确认，再执行
5. 汇总/上报时，更新 parent_context 对应的 _CONTEXT.md 的 last_updated

## 🗂️ 文档导航
| 文件 | 用途 |
|------|------|
| _QA_Index.md | 你每次读这个作为入口 |
| _Log.md | 项目总日志（代码/实验/进展） |
| docs/QA_Log.md | 问答完整记录 |
| docs/Debug_Log.md | DEBUG记录 |
| docs/Knowledge.md | 知识点 |
| docs/Results.md | 实验结果分析 |
| docs/Code_Analysis.md | 代码解析 |
| docs/Code_Versions.md | 版本演化地图 |
| docs/Code_Changes.md | 改动详细记录 |
