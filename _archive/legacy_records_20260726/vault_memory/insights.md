# 重要洞察和结论

**最后更新**: 2026-03-08

---

## AFDM-SP-UWA 核心洞察

### 1. 为什么 DNN 失败？

**根本原因**: 接收机因子图拆分方式不对

- 把"双线性联合推断"（同时含未知信道 H 和未知数据 x_d）
- 拆成了"一次性 CE → 一次性 LMMSE → 一次性 SIC → 再 CE"
- 在 full-domain SP、无 guard、强 fractional Doppler 条件下，这个拆分会天然产生高 SNR error floor

### 2. 为什么 2-Stage SIC 收益很弱？

**Error propagation**:
```
y_clean = y - Ĥ₁x̂₁
        = Hx_p + H(x_d - x̂₁) + (H - Ĥ₁)x̂₁ + w
```

- 符号估计误差 + 信道估计误差 = 结构化残差
- SIC 只用点估计，没有传递不确定性
- Detector 还是原始 inp_y 上的一次性 LMMSE

### 3. 核心教训

**不要只传 x̂，要传 (μ_x, v_x, LLR) 三元组**

- μ_x: 软符号均值
- v_x: 软符号方差
- LLR: 每 bit 的外信息

当某个符号不确定时，不应该强行 subtract，要把"不确定性"显式送进下一轮 CE。

---

## 架构选型建议

| 方案 | 适用场景 | 推荐度 |
|------|----------|--------|
| Joint Bilinear EP-Turbo | 联合 CE+Detection | ⭐⭐⭐⭐⭐ |
| EP-Net/GEPNet | 已知 H 的 Detection | ⭐⭐⭐⭐ |
| OAMP-Net | 已知 H 的 Detection | ⭐⭐⭐ |
| 2-Stage SIC+LMMSE | 当前实现 | ⭐⭐ |

---

## 通用研究方法论

1. **诊断优先**: 先理解问题本质，再动手改代码
2. **物理一致性**: 检验软信息是否符合物理直觉
3. **对比分析**: 传统算法作为 Teacher，蒸馏关键 posterior