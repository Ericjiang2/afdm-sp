# Code Analysis — AFDM End-to-End Learning

代码解析。模块演进、设计决策、关键实现细节。

---

## 格式模板

```markdown
### [ID] YYYY-MM-DD | 主题

**背景:**

**代码位置:** [文件路径]

**关键逻辑:**
```python
# 代码片段
```

**设计决策:**

**演进历史:**

**注意事项:**

---
```

---

## 记录开始

### 主要代码文件概览

**端到端学习实现**:
- `example_af_lmmse.py` - LMMSE 基准实现
- `example_af_lmmse_sp.py` - LMMSE SP 版本
- `example_af_ete_unfold.py` - 端到端展开网络
- `example_af_ete_sp_full_unfold.py` - SP 全展开版本
- `example_af_sp_full_ete_aspp_single.py` - ASPP 单路径版本
- `example_af_6.py` - 基础版本

**训练和测试**:
- `train_phase_d.py` - 阶段 D 训练
- `smoke_test_turbo.py` - Turbo 烟雾测试
- `smoke_test_oamp.py` - OAMP 烟雾测试
- `smoke_test_refiner.py` - Refiner 烟雾测试
- `diag_sic_test.py` - SIC 诊断测试

**AFDM 子项目**:
- `afdm_joint_param_unrolled/` - 联合参数学习接收机
- `afdm_sp_joint_unrolled/` - SP 联合展开（当前活跃）
- `afdm_sp_refactored/` - SP 重构版本

**第三方参考**:
- `EP4IDD/` - EP 检测器参考
- `GCEPNet/` - GCEP 网络参考
- `GNN-based-MIMO-Detection/` - GNN MIMO 检测参考
- `OAMP-Net/` - OAMP-Net 参考

