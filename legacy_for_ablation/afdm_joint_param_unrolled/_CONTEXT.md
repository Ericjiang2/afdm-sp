# CONTEXT — afdm_joint_param_unrolled

## 📍 我在哪里（层级路径）
- L0 全局根: ./ (my-vault根目录)
- L1 领域:   ./01_Projects/          (_CONTEXT.md)
- L2 项目:   ./01_Projects/afdm_end_to_end/  (_CONTEXT.md)
- L3 本项目: ./01_Projects/afdm_end_to_end/OTFS-channel-estimation/afdm_joint_param_unrolled/  ← 你在这里

## 🔗 上级汇报路径
parent_domain: afdm_end_to_end
parent_context: ../../_CONTEXT.md
global_index:   ../../../_Projects_Index.json

## 📦 本项目基本信息
id: afdm-joint-param-unrolled
name: AFDM Joint Param Unrolled Receiver
status: active
owner: User
created: 2026-03-07
last_updated: 2026-03-20

## 📝 项目描述
AFDM（Affine Frequency Division Multiplexing）端到端联合参数学习接收机研究项目。

### 核心研究方向
1. **联合参数学习接收机**: 将信道估计、数据检测、参数调优统一在端到端可学习框架中
2. **启发式诊断基础设施**: Oracle Sweep + Heuristic Breakpoint Diagnosis（阶段八）
3. **多阶段迭代优化**: 从阶段一至阶段八的渐进式架构升级

### 主要技术栈
- **信号模型**: AFDM 调制/解调、时频域信道模型
- **学习架构**: Unrolled Neural Networks（展开神经网络）
- **参数学习**: Learnable heuristics（lambda、alpha、beta、gamma 等）
- **基准方法**: OMP、Turbo、OAMP、DeepTurbo 等传统/神经混合方法

### 当前阶段（阶段八）
诊断优先的基础设施研究，回答三个核心问题：
1. 当前 fixed anchor 是否已接近 oracle
2. 真正有 oracle gap 的 heuristic 属于哪一类（support/refit/detector/outer-loop）
3. 学参数增益不明显的原因分析

## 📂 关键文件

### 核心模块
| 文件 | 用途 |
|------|------|
| `afdm_joint_param.py` | Stage6 联合参数学习接收机 |
| `afdm_traditional_param.py` | Stage7 严格传统参数联合接收机 |
| `afdm_joint_unrolled.py` | 展开式神经网络接收机 |
| `afdm_models.py` | 基础模型定义 |
| `afdm_layers.py` | 自定义神经网络层 |
| `afdm_env.py` | AFDM 环境/信道模拟 |
| `afdm_baselines.py` | 基准方法实现 |
| `afdm_trainer.py` | 训练器基类 |

### 训练与验证
| 文件 | 用途 |
|------|------|
| `train_joint_param.py` | Stage6 训练入口 |
| `train_traditional_param.py` | Stage7 训练入口 |
| `train_joint_unrolled.py` | 展开网络训练入口 |
| `verify_joint_param.py` | Stage6 验证入口 |
| `verify_traditional_param.py` | Stage7 验证入口 |
| `compare_joint_families.py` | 家族对比分析 |

### 诊断工具（阶段八）
| 文件 | 用途 |
|------|------|
| `diagnose_joint_heuristics.py` | 统一启发式诊断脚本 |
| `evaluate_stage8_stage6_heuristics.py` | Stage8/Stage6 启发式评估 |

### 实现方案文档
| 文件 | 阶段 | 内容 |
|------|------|------|
| `实现方案_阶段八_OracleSweepAndHeuristicDiagnosis.md` | 阶段八 | Oracle Sweep + 启发式断点诊断 |
| `实现方案_阶段七_TraditionalParamJoint.md` | 阶段七 | 严格传统参数联合接收机 |
| `实现方案_阶段六_ParamLearnedJointReceiver.md` | 阶段六 | 参数学习联合接收机 |
| `实现方案_阶段四_DeepTurbo.md` | 阶段四 | DeepTurbo 实现 |
| `实现方案_阶段三_OAMPNet.md` | 阶段三 | OAMP-Net 实现 |
| `实现方案_阶段二_TurboRefiner.md` | 阶段二 | Turbo + Refiner 架构 |

### 研究日志
| 文件 | 阶段 | 内容 |
|------|------|------|
| `研究日志_阶段八_OracleSweepAndHeuristicDiagnosis.md` | 阶段八 | Oracle Sweep 实验记录 |
| `研究日志_阶段七_TraditionalParamJoint.md` | 阶段七 | 传统参数联合实验记录 |
| `研究日志_阶段六_ParamLearnedJointReceiver.md` | 阶段六 | 参数学习实验记录 |
| `研究日志_阶段一_问题诊断与架构升级.md` | 阶段一 | 问题诊断与架构升级 |
| `实验总览_阶段五至阶段七_基线冻结.md` | 阶段五-七 | 基线冻结总览 |

## 📊 输出目录
- `outputs_joint_param_smoke/` - Stage6 smoke 测试输出
- `outputs_joint_param_ablation*/` - Stage6 消融实验输出
- `outputs_traditional_param*/` - Stage7 实验输出
- `outputs_joint_heuristic_diagnosis*/` - 阶段八启发式诊断输出
- `outputs_stage8_stage6_heuristics*/` - Stage8/Stage6 启发式评估输出

## ⚠️ AI自检（每次接手必做）
请验证以下路径实际存在，不存在则提醒用户更新：
- parent_context: ../../_CONTEXT.md
- global_index: ../../../_Projects_Index.json

## 🤖 AI接手规则（必须遵守）
1. 先读本文件，再读研究日志了解当前进度
2. 所有记录只追加，不覆盖，不删除历史
3. 每次会话更新 `last_updated`
4. 不确定的操作先用中文提问确认，再执行

## 🗂️ 文档导航
| 文件 | 用途 |
|------|------|
| `../../_CONTEXT.md` | 父级项目上下文（afdm_end_to_end） |
| `_Log.md` | 工作日志 |
| `docs/QA_Log.md` | Q&A 记录 |
| `docs/Debug_Log.md` | 调试记录 |
| `docs/Knowledge.md` | 知识点整理 |
| `docs/Results.md` | 实验结果汇总 |
| `docs/Code_Analysis.md` | 代码解析 |
