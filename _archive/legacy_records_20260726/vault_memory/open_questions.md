# 待解决问题列表

**最后更新**: 2026-03-08

---

## 高优先级

### 1. 软信息接口验证
**问题**: 改造后的 LMMSE 层输出是否正确？
**验证方法**:
- 运行 test_soft_info.py
- 检查猜错 Bit 的 v_x 是否显著偏大
**预期**: 若接口正确，高错误率符号应有高不确定性

### 2. NMSE Error Floor
**问题**: 为什么 DNN-CE 的 NMSE 卡在 0.20？
**诊断**: SP 自干扰 + Fractional Doppler 泄漏
**下一步**: 需要迭代式消干扰架构

---

## 中优先级

### 3. Teacher 蒸馏
**问题**: 如何利用 Joint OMP+MP 的强 posterior？
**方案**: 蒸馏 LLR、符号 posterior、信道 support mask

### 4. 训练策略优化
**问题**: 当前 loss 是否足够？
**改进方向**:
- 观测一致性损失
- Intermediate supervision
- Curriculum learning around latent ambiguity

---

## 低优先级

### 5. 代码重构
**问题**: 是否需要重构为 EP-Turbo 架构？
**依赖**: 第一阶段验证成功后

---

## 问题追踪

| 问题 | 创建日期 | 状态 |
|------|----------|------|
| 软信息接口验证 | 2026-03-08 | 🔄 进行中 |
| NMSE Error Floor | 2026-03-08 | 📋 待处理 |
| Teacher 蒸馏 | 2026-03-08 | 📋 待处理 |